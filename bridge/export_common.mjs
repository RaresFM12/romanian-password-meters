import { writeFileSync } from 'node:fs';
import * as common from '@zxcvbn-ts/language-common';

const c = common.default || common;
const list = c.dictionary['passwords-common'];
const out = process.argv[2];
if (!out) {
  process.stderr.write('usage: node export_common.mjs <out-path>\n');
  process.exit(2);
}
writeFileSync(out, list.join('\n') + '\n', 'utf-8');
process.stderr.write(`wrote ${list.length} passwords to ${out}\n`);
