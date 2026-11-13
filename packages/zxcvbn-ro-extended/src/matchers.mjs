import { FOLD, foldWithMap, hasDiacritic, uppercaseVariations } from './fold.mjs';

const MIN_LEN = 3;

function foldChar(ch) {
  return FOLD[ch] ?? ch;
}

export function makeFoldedMatcher(foldedBest) {
  class Matching {
    match({ password }) {
      const cps = [...password];
      const { folded, starts, n } = foldWithMap(password);
      const m = folded.length;
      const matches = [];
      for (let a = 0; a < m; a += 1) {
        for (let b = a + MIN_LEN; b <= m; b += 1) {
          const sub = folded.slice(a, b);
          if (foldedBest.has(sub)) {
            const i = starts[a];
            const j = b < m ? starts[b] - 1 : n - 1;
            matches.push({
              pattern: 'roFolded', i, j,
              token: cps.slice(i, j + 1).join(''),
              matchedWord: sub, rank: foldedBest.get(sub),
              dictionaryName: 'ro-folded', reversed: false, l33t: false,
            });
          }
        }
      }
      return matches;
    }
  }
  function scoring(match) {
    let factor = 1;
    if (hasDiacritic(match.token)) factor = 2;
    return match.rank * uppercaseVariations(match.token) * factor;
  }
  function feedback() {
    return { warning: null, suggestions: [] };
  }
  return { Matching, scoring, feedback };
}

export function makeDigraphMatcher(foldedBest) {
  class Matching {
    match({ password }) {
      const chars = [...password];
      const low = chars.map((c) => c.toLowerCase());
      const matches = [];
      const n = chars.length;
      for (let i = 0; i < n; i += 1) {
        let rewritten = '';
        let hadDigraph = false;
        let k = i;
        while (k < n) {
          if (low[k] === 's' && low[k + 1] === 'h') { rewritten += 's'; hadDigraph = true; k += 2; }
          else if (low[k] === 't' && low[k + 1] === 'z') { rewritten += 't'; hadDigraph = true; k += 2; }
          else { rewritten += foldChar(low[k]); k += 1; }
          if (hadDigraph && rewritten.length >= MIN_LEN && foldedBest.has(rewritten)) {
            matches.push({
              pattern: 'roDigraph', i, j: k - 1,
              token: chars.slice(i, k).join(''),
              matchedWord: rewritten, rank: foldedBest.get(rewritten),
              dictionaryName: 'ro-digraph', reversed: false, l33t: false,
            });
          }
        }
      }
      return matches;
    }
  }
  function scoring(match) {
    return match.rank * uppercaseVariations(match.token) * 2;
  }
  function feedback() {
    return { warning: null, suggestions: [] };
  }
  return { Matching, scoring, feedback };
}
