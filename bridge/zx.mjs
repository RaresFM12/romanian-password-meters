import readline from 'node:readline';
import { buildFactory, toRecord } from './meters.mjs';

const configName = process.argv[2];
if (!configName) {
  process.stderr.write('usage: node zx.mjs <config-name>\n');
  process.exit(2);
}
const factory = buildFactory(configName);

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
const chunks = [];
for await (const line of rl) {
  if (!line.trim()) continue;
  const { id, password } = JSON.parse(line);
  // calcTime has a 1 ms resolution
  const t0 = performance.now();
  const result = factory.check(password);
  const rec = toRecord(id, result);
  rec.ms = performance.now() - t0;
  chunks.push(JSON.stringify(rec));
  if (chunks.length >= 1000) {
    process.stdout.write(chunks.join('\n') + '\n');
    chunks.length = 0;
  }
}
if (chunks.length) process.stdout.write(chunks.join('\n') + '\n');
