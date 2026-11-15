import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makePhoneMatcher, makeCnpMatcher, makePlateMatcher } from '../src/patterns.mjs';

const phone = new (makePhoneMatcher().Matching)();
const cnp = new (makeCnpMatcher().Matching)();
const plate = new (makePlateMatcher().Matching)();

test('phone matcher finds 07 + 8 digits', () => {
  const m = phone.match({ password: 'x0721234567y' });
  assert.equal(m.length, 1);
  assert.equal(m[0].token, '0721234567');
});

test('cnp matcher needs a valid date', () => {
  assert.equal(cnp.match({ password: '1920511234567' }).length, 1);
  assert.equal(cnp.match({ password: '1991311234567' }).length, 0);
});

test('plate matcher finds county+digits+letters', () => {
  assert.ok(plate.match({ password: 'B123ABC' }).some((h) => h.token === 'B123ABC'));
  assert.ok(plate.match({ password: 'CJ12ABC' }).some((h) => h.token === 'CJ12ABC'));
});

test('no false matches on a normal word', () => {
  assert.equal(phone.match({ password: 'vacanta' }).length, 0);
  assert.equal(plate.match({ password: 'vacanta' }).length, 0);
});
