// Unit tests for the Romanian custom matchers (guide C10). Run: node --test
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeFoldedMatcher, makeDigraphMatcher } from '../src/matchers.mjs';
import { fold, foldWithMap } from '../src/fold.mjs';

const best = new Map([
  ['fetita', 100], ['ionut', 50], ['paine', 30], ['piine', 30], ['vacanta', 10],
]);
const folded = new (makeFoldedMatcher(best).Matching)();
const digraph = new (makeDigraphMatcher(best).Matching)();

test('fold handles NFC and NFD identically', () => {
  assert.equal(fold('fetiță'), 'fetita');
  assert.equal(fold('fetiță'.normalize('NFD')), 'fetita');
});

test('roFolded matches a diacritic word (NFC)', () => {
  const m = folded.match({ password: 'fetiță' });
  assert.ok(m.some((x) => x.matchedWord === 'fetita' && x.i === 0));
});

test('roFolded matches the decomposed (NFD) form as the same word', () => {
  const nfd = 'fetiță'.normalize('NFD');
  const m = folded.match({ password: nfd });
  const hit = m.find((x) => x.matchedWord === 'fetita');
  assert.ok(hit, 'NFD form should match fetita');
  assert.equal(hit.i, 0);
  assert.equal(hit.j, nfd.length - 1); // spans the whole decomposed string
});

test('roFolded matches the pre-1993 spelling piine', () => {
  const m = folded.match({ password: 'piine' });
  assert.ok(m.some((x) => x.matchedWord === 'piine'));
});

test('roDigraph matches sh/tz spellings', () => {
  assert.ok(digraph.match({ password: 'fetitza' }).some((x) => x.matchedWord === 'fetita'));
  assert.ok(digraph.match({ password: 'Ionutz' }).some((x) => x.matchedWord === 'ionut'));
});

test('roDigraph does NOT split an English word like ashley', () => {
  // 'asley' is not a Romanian entry, so no digraph match is produced
  assert.equal(digraph.match({ password: 'ashley' }).length, 0);
});

test('foldWithMap keeps index alignment for composed input', () => {
  const { folded: f, starts, n } = foldWithMap('vacanta');
  assert.equal(f, 'vacanta');
  assert.deepEqual(starts, [0, 1, 2, 3, 4, 5, 6]);
  assert.equal(n, 7);
});
