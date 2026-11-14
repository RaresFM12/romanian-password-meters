import csv
import re
from collections import Counter
import numpy as np
from .config import REPO_ROOT
from .normalize import fold, nfc

GEN = REPO_ROOT / "data/lexicon/generator"
PRIVATE = REPO_ROOT / "results/private"
TABLES = REPO_ROOT / "results/tables"

RO_DIACRITICS = set("ăâîșțşţĂÂÎȘȚŞŢ")
ALPHA = re.compile(r"[a-z]+")
REUSE_GROUPS = [(1000, None), (100, 999), (10, 99), (2, 9), (1, 1)]


def _folded_items(path):
    with open(path, encoding="utf-8", newline="") as f:
        return {fold(nfc(r["item"])).lower() for r in csv.DictReader(f, delimiter="\t")}


class RomanianFilter:
    def __init__(self):
        self.ro = _folded_items(GEN / "ro_words.tsv")
        self.en = _folded_items(GEN / "en_words.tsv")
        self.names = _folded_items(GEN / "ro_names.tsv")

    def is_romanian(self, password):
        p = nfc(password)
        if any(c in RO_DIACRITICS for c in p):
            return True
        for tok in ALPHA.findall(fold(p).lower()):
            if len(tok) >= 5 and tok in self.ro and tok not in self.en:
                return True
            if tok in self.names:
                return True
        return False


def load_counts(path):
    counts = Counter()
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2 and parts[0].isdigit():
                counts[nfc(parts[1])] += int(parts[0])
            else:
                counts[nfc(line)] += 1
    return dict(counts)


def split_occurrences(counts, seed, shares=(0.40, 0.30, 0.30)):
    rng = np.random.default_rng(seed)
    out = {}
    for pw, c in counts.items():
        m, a, v = rng.multinomial(c, shares)
        out[pw] = (int(m), int(a), int(v))
    return out


def reuse_group(count):
    for lo, hi in REUSE_GROUPS:
        if count >= lo and (hi is None or count <= hi):
            if hi is None:
                return str(lo) + "+"
            return str(lo) + "-" + str(hi)
    return "0"


def profile(counts):
    n_pw = len(counts)
    n_occ = sum(counts.values())
    lengths = [len(p) for p in counts]
    classes = Counter()
    with_diac = 0
    for p in counts:
        pf = nfc(p)
        has = {"lower": False, "upper": False, "digit": False, "symbol": False}
        for ch in pf:
            if ch.isdigit():
                has["digit"] = True
            elif ch.isalpha():
                if ch.isupper():
                    has["upper"] = True
                else:
                    has["lower"] = True
            else:
                has["symbol"] = True
        for k, v in has.items():
            if v:
                classes[k] += 1
        if any(c in RO_DIACRITICS for c in pf):
            with_diac += 1
    mean_length = round(sum(lengths) / n_pw, 2) if n_pw else 0
    return {
        "passwords": n_pw,
        "occurrences": n_occ,
        "mean_length": mean_length,
        "class_counts": dict(classes),
        "with_diacritics": with_diac,
    }


def precision_sample(counts, seed, n=300):
    rng = np.random.default_rng(seed)
    pws = sorted(counts)
    idx = rng.choice(len(pws), size=min(n, len(pws)), replace=False)
    return [pws[i] for i in sorted(idx)]


def case_study_sample(validation, seed, frac=0.10):
    rng = np.random.default_rng(seed)
    by_group = {}
    for pw, c in validation.items():
        by_group.setdefault(reuse_group(c), []).append(pw)
    out = {}
    for group, pws in by_group.items():
        pws = sorted(pws)
        k = max(1, round(len(pws) * frac))
        for i in sorted(rng.choice(len(pws), size=min(k, len(pws)), replace=False)):
            out[pws[i]] = validation[pws[i]]
    return out


BREACH_DIR = REPO_ROOT / "data/breach"
BREACH_FILE = BREACH_DIR / "rockyou.txt"
METER = REPO_ROOT / "data/lexicon/meter"


def _write_lines(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def run(seed=42):
    if not BREACH_FILE.exists():
        print("no data/breach/rockyou.txt; supply it first")
        return
    filt = RomanianFilter()
    counts = {}
    order = {}
    idx = 0
    with open(BREACH_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            pw = nfc(line.rstrip("\n"))
            if pw and filt.is_romanian(pw):
                if pw not in counts:
                    counts[pw] = 0
                    order[pw] = idx
                counts[pw] += 1
            idx += 1
    print("romanian passwords found:", len(counts))

    split = split_occurrences(counts, seed)
    meter = sorted((pw for pw, (m, a, v) in split.items() if m > 0), key=lambda p: order[p])
    attacker = [pw for pw, (m, a, v) in split.items() if a > 0]
    validation = {pw: v for pw, (m, a, v) in split.items() if v > 0}
    exclude = set(meter) | set(validation)

    with open(METER / "ro_leaked.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["item", "rank", "freq"])
        for i, pw in enumerate(meter, start=1):
            w.writerow([pw, i, counts[pw]])

    _write_lines(BREACH_DIR / "ro_attacker_share.txt", attacker)

    out = []
    with open(BREACH_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            pw = nfc(line.rstrip("\n"))
            if pw and pw not in exclude:
                out.append(line.rstrip("\n"))
    _write_lines(BREACH_DIR / "rockyou_attacker.txt", out)

    PRIVATE.mkdir(parents=True, exist_ok=True)
    with open(PRIVATE / "validation.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["password", "count"])
        for pw, c in validation.items():
            w.writerow([pw, c])
    sample = precision_sample(counts, seed)
    with open(PRIVATE / "precision_sample.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["password", "is_romanian"])
        for pw in sample:
            w.writerow([pw, ""])

    TABLES.mkdir(parents=True, exist_ok=True)
    prof = profile(validation)
    with open(TABLES / "breach_profile.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in prof.items():
            w.writerow([k, v])
    print("meter share:", len(meter), "attacker share:", len(attacker),
          "validation:", len(validation))
    print("wrote ro_leaked.tsv, ro_attacker_share.txt, rockyou_attacker.txt,",
          "validation.csv (private), precision_sample.csv (private), breach_profile.csv")


def _main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    run(ap.parse_args().seed)


if __name__ == "__main__":
    _main()
