function matcherFrom(name, finder, guesses) {
  class Matching {
    match({ password }) {
      return finder(password).map((hit) => ({
        pattern: name,
        i: hit.i,
        j: hit.j,
        token: hit.token,
        guesses: hit.guesses !== undefined ? hit.guesses : guesses,
      }));
    }
  }
  return {
    Matching,
    scoring: (m) => m.guesses,
    feedback: () => ({ warning: null, suggestions: [] }),
  };
}

function findRegex(password, re) {
  const out = [];
  let m;
  const r = new RegExp(re.source, re.flags.includes("g") ? re.flags : re.flags + "g");
  while ((m = r.exec(password)) !== null) {
    out.push({ i: m.index, j: m.index + m[0].length - 1, token: m[0] });
    if (m.index === r.lastIndex) r.lastIndex += 1;
  }
  return out;
}

export function makePhoneMatcher() {
  return matcherFrom("roPhone", (pw) => findRegex(pw, /07\d{8}/), 1e8);
}

function validDate(yy, mm, dd) {
  const month = Number(mm);
  const day = Number(dd);
  return month >= 1 && month <= 12 && day >= 1 && day <= 31;
}

export function makeCnpMatcher() {
  return matcherFrom("roCnp", (pw) => {
    const hits = findRegex(pw, /[1-8]\d{12}/);
    return hits.filter((h) => validDate(h.token.slice(1, 3), h.token.slice(3, 5), h.token.slice(5, 7)));
  }, 1e9);
}

export function makePlateMatcher() {
  return matcherFrom("roPlate", (pw) => findRegex(pw, /\b[A-Z]{1,2}\d{2,3}[A-Z]{3}\b/), 1e8);
}

export function makePatternMatchers() {
  return {
    roPhone: makePhoneMatcher(),
    roCnp: makeCnpMatcher(),
    roPlate: makePlateMatcher(),
  };
}
