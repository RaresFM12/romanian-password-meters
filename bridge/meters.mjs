import { dirname, join } from 'node:path';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import * as common from '@zxcvbn-ts/language-common';
import * as en from '@zxcvbn-ts/language-en';
import * as ro from '@zxcvbn-ts/language-ro';
import { buildRoDictionaries, addFoldedArrays } from '../packages/zxcvbn-ro-extended/src/dictionaries.mjs';
import { makeFoldedMatcher, makeDigraphMatcher } from '../packages/zxcvbn-ro-extended/src/matchers.mjs';
import { makePatternMatchers } from '../packages/zxcvbn-ro-extended/src/patterns.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const CORE = process.env.ZXCVBN_CORE || join(HERE, 'vendor/core-D10000/index.mjs');
if (!existsSync(CORE)) throw new Error(`${CORE} missing; run bridge/make_cores.sh`);
const core = await import(CORE);
const ZxcvbnFactory = core.ZxcvbnFactory ?? (core.default && core.default.ZxcvbnFactory);
const C = common.default || common;
const E = en.default || en;
const R = ro.default || ro;

const BASE = { graphs: C.adjacencyGraphs, translations: E.translations };
const METER_DIR = join(HERE, '..', 'data/lexicon/meter');

// each group also brings its cz_ copies, so EN <= PKG <= CZ <= RO+
const GROUP_LISTS = {
  clean: ['ro_common_clean'],
  names: ['ro_names_ext'],
  places: ['ro_places'],
  cultural: ['ro_cultural', 'ro_expressions', 'ro_calendar'],
  leaked: ['ro_leaked'],
};
const DICT_GROUPS = Object.keys(GROUP_LISTS);
export const ALL_GROUPS = ['norm', 'digraph', 'clean', 'names', 'places', 'cultural', 'leaked', 'patterns'];

function present(lists) {
  for (const n of lists) {
    if (!existsSync(join(METER_DIR, `${n}.tsv`))) throw new Error(`meter list ${n}.tsv missing`);
  }
  return lists;
}

function czLists(groups) {
  const out = [];
  for (const g of DICT_GROUPS) if (groups.has(g)) out.push(...GROUP_LISTS[g].map((n) => `cz_${n}`));
  return present(out);
}

function pkgDictionary(extra) {
  return { ...C.dictionary, ...E.dictionary, ...R.dictionary, ...extra };
}

function roFactory(groups) {
  const roLists = [];
  for (const g of DICT_GROUPS) if (groups.has(g)) roLists.push(...GROUP_LISTS[g]);
  const extra = buildRoDictionaries(METER_DIR, [...present(roLists), ...czLists(groups)]);
  const custom = {};
  if (groups.has('norm') || groups.has('digraph')) {
    const folded = buildRoDictionaries(METER_DIR, present(roLists)).foldedBest;
    addFoldedArrays(folded, Object.values(R.dictionary));
    if (groups.has('norm')) custom.roFolded = makeFoldedMatcher(folded);
    if (groups.has('digraph')) custom.roDigraph = makeDigraphMatcher(folded);
  }
  if (groups.has('patterns')) Object.assign(custom, makePatternMatchers());
  return new ZxcvbnFactory({ ...BASE, dictionary: pkgDictionary(extra.dictionary) }, custom);
}

function czFactory() {
  const groups = new Set(DICT_GROUPS);
  const extra = buildRoDictionaries(METER_DIR, czLists(groups));
  return new ZxcvbnFactory({ ...BASE, dictionary: pkgDictionary(extra.dictionary) }, makePatternMatchers());
}

export function buildFactory(name) {
  if (name === 'M-ZX-EN') {
    return new ZxcvbnFactory({ ...BASE, dictionary: { ...C.dictionary, ...E.dictionary } });
  }
  if (name === 'M-ZX-RO-PKG') return new ZxcvbnFactory({ ...BASE, dictionary: pkgDictionary({}) });
  if (name === 'M-ZX-RO-CZ') return czFactory();
  if (name === 'M-ZX-RO+') return roFactory(new Set(ALL_GROUPS));
  if (name === 'RO-PKG+norm') return roFactory(new Set(['norm', 'digraph']));
  if (name.startsWith('A+') || name.startsWith('A-')) {
    const g = name.slice(2);
    if (!ALL_GROUPS.includes(g)) throw new Error(`unknown resource group: ${g}`);
    if (name.startsWith('A+')) return roFactory(new Set([g]));
    return roFactory(new Set(ALL_GROUPS.filter((x) => x !== g)));
  }
  throw new Error(`unknown meter config: ${name}`);
}

export const factorial = (n) => {
  let f = 1;
  for (let i = 2; i <= n; i += 1) f *= i;
  return f;
};

export function toRecord(id, r) {
  const k = r.sequence.length;
  const productTerm = factorial(k) * r.sequence.reduce((a, s) => a * s.guesses, 1);
  const sequence = r.sequence.map((s) => ({
    pattern: s.pattern,
    token: s.token,
    i: s.i,
    j: s.j,
    guesses: s.guesses,
    dictionaryName: s.dictionaryName ?? null,
    rank: s.rank ?? null,
    l33t: Boolean(s.l33t),
    reversed: Boolean(s.reversed),
  }));
  return {
    id,
    guesses: r.guesses,
    log10: r.guessesLog10,
    score: r.score,
    k,
    product_term: productTerm,
    sequence,
    ms: r.calcTime,
  };
}
