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
  return rows;
}

export const RO_LISTS = [
  'ro_common_clean', 'ro_names_ext', 'ro_places',
  'ro_cultural', 'ro_expressions', 'ro_calendar',
];

export function buildRoDictionaries(meterDir, lists = RO_LISTS) {
  const dictionary = {};
  const foldedBest = new Map();
  function note(key, rank) {
    if (!foldedBest.has(key) || rank < foldedBest.get(key)) foldedBest.set(key, rank);
  }
  for (const name of lists) {
    const rows = loadTsv(join(meterDir, `${name}.tsv`));
    dictionary[name] = rows.map((r) => r.item);
    for (const r of rows) {
      const f = fold(r.item).toLowerCase();
      note(f, r.freq);
      const pre = fold(toPre1993(r.item)).toLowerCase();
      if (pre !== f) note(pre, r.freq);
    }
  }
  return { dictionary, foldedBest };
}
