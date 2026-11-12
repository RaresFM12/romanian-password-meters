"""How does @zxcvbn-ts/language-ro cover the different spellings of Romanian diacritic letters?

Checks a hand-picked set of probe strings (cedilla vs comma-below, sign dropped, sh/tz digraphs,
pre-1993 î-spellings, inflected forms) against the package's commonWords,
firstnames and wikipedia lists, and counts decomposed (non-NFC) entries and entries carrying invisible
formatting characters. Quoted in research-plan.md section 2.3 and the Lab 3-4 outline (chapter 3, 4.4).

Usage:
    python3 -I check_consonant_variants.py [path-to-extracted-language-ro-package]

If no path is given, language-ro 4.1.2 is downloaded from the npm registry into a temporary directory.
"""
from __future__ import annotations

import io
import json
import sys
import tarfile
import tempfile
import unicodedata
import urllib.request
from pathlib import Path

TARBALL = "https://registry.npmjs.org/@zxcvbn-ts/language-ro/-/language-ro-4.1.2.tgz"
LISTS = ["commonWords", "firstnames", "wikipedia"]

# Grouped so each row of the output reads as one spelling family.
PROBES = {
    "ș dropped / sh / cedilla / comma-below": ["sefu", "shefu", "şefu", "șefu"],
    "ț dropped / tz / cedilla / comma-below": ["fetita", "fetitza", "fetiţă", "fetiță"],
    "name with ț": ["ionut", "ionutz", "ionuţ", "ionuț"],
    "diminutive with ț": ["pisicuta", "pisicutza", "pisicuţa", "pisicuța", "dragut", "dragutza", "drăguț"],
    "â (1993 norm) / î (pre-1993 norm) / ASCII": ["pâine", "pîine", "paine", "piine", "când", "cînd", "cand", "cind",
                                                  "mâine", "mîine", "maine", "miine", "sunt", "sînt", "sint"],
    "inflected forms (t→ț, s→ș)": ["frati", "fraţi", "frați", "urs", "ursi", "urși", "brazi"],
    "vocative": ["puiule", "iubito", "iubitule", "scumpo"],
    "one-word expression": ["teiubesc", "lamultiani"],
}


def load(root: Path) -> dict[str, list[str]]:
    return {name: json.loads((root / "src" / f"{name}.json").read_text(encoding="utf-8")) for name in LISTS}


def main() -> None:
    if len(sys.argv) > 1:
        lists = load(Path(sys.argv[1]))
    else:
        with tempfile.TemporaryDirectory() as tmp:
            data = urllib.request.urlopen(TARBALL).read()
            with tarfile.open(fileobj=io.BytesIO(data)) as tar:
                tar.extractall(tmp, filter="data")
            lists = load(Path(tmp) / "package")

    # zxcvbn-ts rank = list position + 1; keep the first (best) position of each string.
    ranks = {name: {} for name in LISTS}
    for name, words in lists.items():
        for i, word in enumerate(words):
            ranks[name].setdefault(word, i + 1)

    for family, probes in PROBES.items():
        print(f"\n{family}")
        for word in probes:
            hits = [f"{name}#{ranks[name][word]}" for name in LISTS if word in ranks[name]]
            print(f"  {word:12} {', '.join(hits) if hits else '-- not in any list'}")

    words = lists["commonWords"]
    decomposed = sum(1 for w in words if w != unicodedata.normalize("NFC", w))
    invisible = sum(1 for w in words if any(unicodedata.category(c) in ("Cf", "Cc") for c in w))
    print(f"\ncommonWords: {len(words)} entries, {decomposed} not in NFC, {invisible} with invisible formatting characters")


if __name__ == "__main__":
    main()
