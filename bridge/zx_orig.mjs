import readline from 'node:readline';
import zp from 'zxcvbn';
import { factorial } from './meters.mjs';

const zxcvbn = zp.default || zp;

function toRecord(id, r) {
  const k = r.sequence.length;
  const productTerm = factorial(k) * r.sequence.reduce((a, s) => a * s.guesses, 1);
  const sequence = r.sequence.map((s) => ({
    pattern: s.pattern,
    token: s.token,
    i: s.i,
    j: s.j,
    guesses: s.guesses,
    dictionaryName: s.dictionary_name ?? null,
    rank: s.rank ?? null,
    l33t: Boolean(s.l33t),
    reversed: Boolean(s.reversed),
  }));
  return {
    id,
    guesses: r.guesses,
    log10: r.guesses_log10,
    score: r.score,
    k,
    product_term: productTerm,
    sequence,
    ms: r.calc_time,
  };
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
const chunks = [];
for await (const line of rl) {
  if (!line.trim()) continue;
  const { id, password } = JSON.parse(line);
  chunks.push(JSON.stringify(toRecord(id, zxcvbn(password))));
  if (chunks.length >= 1000) {
    process.stdout.write(chunks.join('\n') + '\n');
    chunks.length = 0;
  }
}
if (chunks.length) process.stdout.write(chunks.join('\n') + '\n');
