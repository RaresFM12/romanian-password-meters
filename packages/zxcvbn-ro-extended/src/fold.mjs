import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const T = JSON.parse(readFileSync(join(here, 'tables.json'), 'utf-8'));

export const FOLD = T.fold;
export const DIGRAPH = T.digraph;
const ROMAN_STEM = T.roman_stem;

export function fold(s) {
  const nfc = s.normalize('NFC');
  let out = '';
  for (const ch of nfc) out += FOLD[ch] ?? ch;
  return out;
}

export function hasDiacritic(s) {
  const nfc = s.normalize('NFC');
  for (const ch of nfc) if (ch in FOLD) return true;
  return false;
}

export function toPre1993(s) {
  const nfc = s.normalize('NFC');
  const ph = '';
  const protectedStr = nfc.split(ROMAN_STEM).join(ph);
  const converted = protectedStr.replace(/â/g, 'î').replace(/Â/g, 'Î');
  return converted.split(ph).join(ROMAN_STEM);
}

const COMBINING = /\p{Mn}|\p{Mc}/u;

export function foldWithMap(password) {
  const cps = [...password];
  const groups = [];
  for (let idx = 0; idx < cps.length; idx += 1) {
    const ch = cps[idx];
    if (COMBINING.test(ch) && groups.length) {
      groups[groups.length - 1].src += ch;
    } else {
      groups.push({ src: ch, start: idx });
    }
  }
  let folded = '';
  const starts = [];
  for (const g of groups) {
    const composed = g.src.normalize('NFC');
    let f = '';
    for (const c of composed) f += FOLD[c] ?? c;
    folded += f.toLowerCase();
    starts.push(g.start);
  }
  return { folded, starts, n: cps.length };
}

const ONE_UPPER = /[A-Z]/;
const ONE_LOWER = /[a-z]/;
const ALL_LOWER = /^[^A-Z]+$/;
const START_UPPER = /^[A-Z][^A-Z]+$/;
const END_UPPER = /^[^A-Z]+[A-Z]$/;
const ALL_UPPER = /^[^a-z]+$/;

function nCk(n, k) {
  if (k > n) return 0;
  if (k === 0) return 1;
  let r = 1;
  for (let d = 1; d <= k; d += 1) { r *= n; r /= d; n -= 1; }
  return Math.round(r);
}

export function uppercaseVariations(token) {
  const word = token.replace(/[^A-Za-z]/g, '');
  if (word === '' || ALL_LOWER.test(word) || word.toLowerCase() === word) return 1;
  if (START_UPPER.test(word) || END_UPPER.test(word) || ALL_UPPER.test(word)) return 2;
  const u = [...word].filter((c) => ONE_UPPER.test(c)).length;
  const l = [...word].filter((c) => ONE_LOWER.test(c)).length;
  let variations = 0;
  for (let i = 1; i <= Math.min(u, l); i += 1) variations += nCk(u + l, i);
  return variations;
}
