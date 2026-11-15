import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildRoDictionaries, addFoldedArrays } from '../src/dictionaries.mjs';

test('foldedBest uses the rank column', () => {
  const dir = mkdtempSync(join(tmpdir(), 'ro-'));
  writeFileSync(join(dir, 'leak.tsv'), 'item\trank\tfreq\nandreea\t1\t1\nfetiță\t500\t1\n');
  const { dictionary, foldedBest } = buildRoDictionaries(dir, ['leak']);
  assert.deepEqual(dictionary.leak, ['andreea', 'fetiță']);
  assert.equal(foldedBest.get('fetita'), 500);
});

test('addFoldedArrays ranks by position', () => {
  const m = addFoldedArrays(new Map(), [['vacanță', 'casă']]);
  assert.equal(m.get('vacanta'), 1);
  assert.equal(m.get('casa'), 2);
});
