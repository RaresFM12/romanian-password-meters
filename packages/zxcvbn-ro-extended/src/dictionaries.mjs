import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fold, toPre1993 } from './fold.mjs';

export function loadTsv(path) {
  const lines = readFileSync(path, 'utf-8').split('\n');
  lines.shift();
  const rows = [];
  for (const line of lines) {
    if (!line) continue;
    const [item, rank, freq] = line.split('\t');
    rows.push({ item, rank: Number(rank), freq: Number(freq) });
  }
  rows.sort((a, b) => a.rank - b.rank);
  return rows;
}

function addFolded(foldedBest, item, rank) {
  for (const form of [item, toPre1993(item)]) {
    const key = fold(form).toLowerCase();
    if (!foldedBest.has(key) || rank < foldedBest.get(key)) foldedBest.set(key, rank);
  }
}

// zxcvbn ranks a word by its array position, so arrays are in rank order
export function buildRoDictionaries(meterDir, lists) {
  const dictionary = {};
  const foldedBest = new Map();
  for (const name of lists) {
    const rows = loadTsv(join(meterDir, `${name}.tsv`));
    dictionary[name] = rows.map((r) => r.item);
    for (const r of rows) addFolded(foldedBest, r.item, r.rank);
  }
  return { dictionary, foldedBest };
}

export function addFoldedArrays(foldedBest, arrays) {
  for (const words of arrays) {
    words.forEach((w, i) => addFolded(foldedBest, String(w), i + 1));
  }
  return foldedBest;
}
