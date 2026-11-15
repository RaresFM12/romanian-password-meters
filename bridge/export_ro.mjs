import { writeFileSync } from 'node:fs';
import * as ro from '@zxcvbn-ts/language-ro';

const r = ro.default || ro;
const dir = process.argv[2];
if (!dir) {
  process.stderr.write('usage: node export_ro.mjs <out-dir>\n');
  process.exit(2);
}
for (const [key, file] of [['commonWords-ro', 'commonwords'], ['firstnames-ro', 'firstnames']]) {
  const list = r.dictionary[key];
  writeFileSync(`${dir}/_src_${file}.txt`, list.join('\n') + '\n', 'utf-8');
  process.stderr.write(`${key}: ${list.length} -> _src_${file}.txt\n`);
}
