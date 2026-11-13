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
  chunks.push(JSON.stringify(toRecord(id, factory.check(password))));
  if (chunks.length >= 1000) {
    process.stdout.write(chunks.join('\n') + '\n');
    chunks.length = 0;
  }
}
if (chunks.length) process.stdout.write(chunks.join('\n') + '\n');
