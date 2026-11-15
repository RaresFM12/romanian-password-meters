import argparse
import csv
import glob
import pandas as pd
from .config import REPO_ROOT
from .normalize import nfc, to_ascii, to_cedilla, to_digraph, to_pre1993, to_pre1993_ascii

GEN = REPO_ROOT / "data/lexicon/generator"
OUT = REPO_ROOT / "data/reference/wordlists"
BREACH = REPO_ROOT / "data/breach"
TOP_WORDS = 5000


def read_items(name):
    path = GEN / (name + ".tsv")
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            out.append(r["item"])
    return out


def ro_variants(word):
    forms = [nfc(word), to_ascii(word), to_cedilla(word), to_digraph(word),
             to_pre1993(word), to_pre1993_ascii(word)]
    for f in list(forms):
        if not f.isascii():
            forms += [f[:1].upper() + f[1:], f.upper()]
    out = []
    for f in forms:
        if f and f not in out:
            out.append(f)
    return out


def phrase_forms(phrase):
    out = []
    for p in (phrase, phrase.replace(" ", "")):
        out += [f for f in ro_variants(p) if f not in out]
    return out


def read_breach(filename):
    path = BREACH / filename
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line:
                out.append(line)
    return out


def write_list(path, words):
    seen = set()
    lines = []
    for w in words:
        w = nfc(w)
        if w and w not in seen:
            seen.add(w)
            lines.append(w)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return len(lines)


def build():
    # generator lists before RockYou, as in ro.txt, so twins face the same attackers
    rockyou = "rockyou_attacker.txt"
    if not (BREACH / rockyou).exists():
        raise FileNotFoundError("data/breach/rockyou_attacker.txt missing; run make breach")
    en = read_items("en_words") + read_items("en_names")
    for p in read_items("en_phrases"):
        en += [p, p.replace(" ", "")]
    en += read_breach(rockyou)

    ro = []
    for name in ("ro_words", "ro_inflected", "ro_names", "ro_places", "ro_cultural"):
        for w in read_items(name):
            ro += ro_variants(w)
    for p in read_items("ro_phrases"):
        ro += phrase_forms(p)
    ro += read_breach("ro_attacker_share.txt")

    # robustness: the same Romanian lists without any spelling variant
    ro_novar = []
    for name in ("ro_words", "ro_inflected", "ro_names", "ro_places", "ro_cultural"):
        ro_novar += [nfc(w) for w in read_items(name)]
    for p in read_items("ro_phrases"):
        ro_novar += [p, p.replace(" ", "")]
    ro_novar += read_breach("ro_attacker_share.txt")
    top_novar = []
    for w in read_items("ro_words"):
        if nfc(w) not in top_novar:
            top_novar.append(nfc(w))
        if len(top_novar) == TOP_WORDS:
            break

    top = []
    for w in read_items("ro_words"):
        a = to_ascii(w)
        if a not in top:
            top.append(a)
        if len(top) == TOP_WORDS:
            break
    top_en = read_items("en_words")[:TOP_WORDS]

    sizes = {
        "en": write_list(OUT / "en.txt", en),
        "ro": write_list(OUT / "ro.txt", ro),
        "all": write_list(OUT / "all.txt", ro + en),
        "ro_top": write_list(OUT / "ro_top.txt", top),
        "all_top": write_list(OUT / "all_top.txt", top + top_en),
        "ro_novar": write_list(OUT / "ro_novar.txt", ro_novar),
        "ro_novar_top": write_list(OUT / "ro_novar_top.txt", top_novar),
    }
    inputs = ["data/lexicon/generator/" + n + ".tsv" for n in
              ("en_words", "en_names", "en_phrases", "ro_words", "ro_inflected",
               "ro_names", "ro_places", "ro_cultural", "ro_phrases")]
    inputs += ["data/breach/" + rockyou, "data/breach/ro_attacker_share.txt"]
    with open(REPO_ROOT / "data/reference/attacker_inputs.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(inputs) + "\n")
    return sizes


def build_targets():
    vals = set()
    for f in glob.glob(str(REPO_ROOT / "data/synthetic/case_seed*.csv")):
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        vals |= {nfc(p) for p in df["password"]}
    vfile = REPO_ROOT / "results/private/validation.csv"
    if vfile.exists():
        with open(vfile, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                vals.add(nfc(r["password"]))
    out = REPO_ROOT / "data/synthetic/targets_all.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(vals)) + "\n")
    return len(vals)


def _main():
    argparse.ArgumentParser().parse_args()
    sizes = build()
    for name, n in sizes.items():
        print(name + ".txt", n, "words")
    print("targets_all.txt", build_targets(), "unique passwords (synthetic + validation)")
    if not (BREACH / "rockyou.txt").exists():
        print("note: put rockyou.txt in data/breach/ to add it to en.txt and all.txt")


if __name__ == "__main__":
    _main()
