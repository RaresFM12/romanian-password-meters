"""Audit of @zxcvbn-ts/language-ro and cross-language overlap with the Romance packages.

Reproduces the numbers quoted in research-plan.md, section 2.3.

Usage:
    python3 -I audit_language_ro.py [path-to-zxcvbn-ts-checkout]

If no path is given, the current master of github.com/zxcvbn-ts/zxcvbn is
downloaded into a temporary directory. Record the commit hash printed at the
end next to any numbers you quote.
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

ARCHIVE = "https://github.com/zxcvbn-ts/zxcvbn/archive/refs/heads/master.tar.gz"
ROMANCE = ["it", "es-es", "fr", "pt-br"]
RO_DIACRITICS = "ăâîșțşţ"


def fold(word: str) -> str:
    """ASCII-fold: comma-below and cedilla s/t first, then strip all combining marks."""
    word = word.translate(str.maketrans("şţșț", "stst"))
    decomposed = unicodedata.normalize("NFKD", word)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def load(root: Path, lang: str, name: str) -> list[str]:
    path = root / "packages" / "languages" / lang / "src" / f"{name}.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def checkout(arg: str | None) -> Path:
    if arg:
        return Path(arg)
    tmp = Path(tempfile.mkdtemp(prefix="zxcvbn-ts-"))
    with urllib.request.urlopen(ARCHIVE) as resp:
        data = resp.read()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        try:
            tar.extractall(tmp, filter="data")  # Python >= 3.12 (and backports)
        except TypeError:
            tar.extractall(tmp)
    return next(tmp.iterdir())


def main() -> None:
    root = checkout(sys.argv[1] if len(sys.argv) > 1 else None)
    print(f"source: {root}")

    # 1. language-ro contents
    print("\n== @zxcvbn-ts/language-ro ==")
    for name in ["commonWords", "firstnames", "lastnames", "wikipedia", "wordSequences"]:
        print(f"{name}: {len(load(root, 'ro', name))}")

    words = load(root, "ro", "commonWords")
    present = set(words)
    rank = {w: i for i, w in enumerate(words)}
    cedilla_to_comma = str.maketrans("şţ", "șț")
    both = [(w, w.translate(cedilla_to_comma)) for w in words
            if ("ş" in w or "ţ" in w) and w.translate(cedilla_to_comma) in present]
    ascii_dups = [w for w in words
                  if any(c in w for c in RO_DIACRITICS) and fold(w) in present and fold(w) != w]
    print(f"entries with cedilla ş/ţ: {sum(1 for w in words if 'ş' in w or 'ţ' in w)}")
    print(f"entries with comma-below ș/ț: {sum(1 for w in words if 'ș' in w or 'ț' in w)}")
    print(f"cedilla/comma duplicate pairs: {len(both)}  e.g. {both[:5]}")
    print(f"diacritic entries whose ASCII form is also present: {len(ascii_dups)}")
    print(f"unique entries after folding: {len({fold(w) for w in words})} of {len(words)}")
    for w in ["vacanţă", "vacanță", "vacanta", "crăciun", "craciun", "şi", "și"]:
        print(f"  rank of {w!r}: {rank.get(w)}")

    # 2. does the core normalise anything?
    core = root / "packages" / "libraries" / "main" / "src"
    hits = [p for p in core.rglob("*.ts") if ".spec." not in p.name
            and any(k in p.read_text(encoding="utf-8") for k in ("normalize(", "NFD", "NFKD", "diacritic"))]
    print(f"\ncore files mentioning Unicode normalisation/diacritics: {len(hits)} {hits}")

    # 3. overlap with sister languages (exact folded strings)
    print("\n== overlap with Romance packages (ASCII-folded exact matches) ==")
    ro_all = {fold(w) for w in words}
    ro_top = {fold(w) for w in words[:10000]}
    ro_names = {fold(w) for w in load(root, "ro", "firstnames")}
    union: set[str] = set()
    for lang in ROMANCE + ["en"]:
        lw = {fold(w) for w in load(root, lang, "commonWords")}
        ln = {fold(w) for w in load(root, lang, "firstnames")}
        if lang != "en":
            union |= lw
        print(f"{lang:6s} commonWords∩RO(all)={len(lw & ro_all):5d}  "
              f"∩RO(top10k)={len(lw & ro_top):5d}  firstnames∩RO={len(ln & ro_names):4d}")
    en = {fold(w) for w in load(root, "en", "commonWords")}
    print(f"IT+ES+FR+PT union ∩ RO(top10k) = {len(union & ro_top)}  ({len(union & ro_top) / 100:.0f}%)")
    print(f"EN ∩ RO(top10k) = {len(en & ro_top)}  ({len(en & ro_top) / 100:.0f}%)")
    print(f"RO top10k in neither = {len(ro_top - en - union)}")

    print("\n== sister package sizes ==")
    for lang in ROMANCE:
        sizes = {n: len(load(root, lang, n)) for n in ["commonWords", "firstnames", "lastnames", "wikipedia"]}
        print(lang, sizes)


if __name__ == "__main__":
    main()
