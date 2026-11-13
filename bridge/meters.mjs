import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import pkg from '@zxcvbn-ts/core';
import * as common from '@zxcvbn-ts/language-common';
import * as en from '@zxcvbn-ts/language-en';
import * as ro from '@zxcvbn-ts/language-ro';
import { buildRoDictionaries, RO_LISTS } from '../packages/zxcvbn-ro-extended/src/dictionaries.mjs';
import { makeFoldedMatcher, makeDigraphMatcher } from '../packages/zxcvbn-ro-extended/src/matchers.mjs';

const { ZxcvbnFactory } = pkg;
const C = common.default || common;
const E = en.default || en;
const R = ro.default || ro;

const BASE = { graphs: C.adjacencyGraphs, translations: E.translations };
const METER_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'data/lexicon/meter');
const CZ_LISTS = ['cz_ro_names_ext', 'cz_ro_places', 'cz_ro_cultural', 'cz_ro_expressions'];

function roFactory({ dictLists = [], foldLists = [], norm = false, digraph = false }) {
  const extra = buildRoDictionaries(METER_DIR, dictLists);
  const folded = buildRoDictionaries(METER_DIR, foldLists);
  const dictionary = { ...C.dictionary, ...E.dictionary, ...R.dictionary, ...extra.dictionary };
  const custom = {};
  if (norm) custom.roFolded = makeFoldedMatcher(folded.foldedBest);
  if (digraph) custom.roDigraph = makeDigraphMatcher(folded.foldedBest);
  return new ZxcvbnFactory({ ...BASE, dictionary }, custom);
}

export function buildFactory(name) {
  switch (name) {
    case 'M-ZX-EN':
      return new ZxcvbnFactory({ ...BASE, dictionary: { ...C.dictionary, ...E.dictionary } });
    case 'M-ZX-RO-PKG':
      return new ZxcvbnFactory({ ...BASE, dictionary: { ...C.dictionary, ...E.dictionary, ...R.dictionary } });
    case 'M-ZX-RO+':
      return roFactory({ dictLists: [...RO_LISTS, ...CZ_LISTS], foldLists: RO_LISTS, norm: true, digraph: true });
    case 'RO-PKG+norm':
      return roFactory({ dictLists: [], foldLists: ['ro_common_clean'], norm: true, digraph: true });
    case 'M-ZX-RO-CZ':
      return roFactory({
        dictLists: ['cz_ro_names_ext', 'cz_ro_places', 'cz_ro_cultural', 'cz_ro_expressions'],
        foldLists: [], norm: false, digraph: false,
      });
    default:
      throw new Error(`unknown meter config: ${name}`);
  }
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
