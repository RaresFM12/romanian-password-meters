import csv
import re
import unicodedata
from collections import Counter
import numpy as np
from .config import REPO_ROOT, load_config
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


MIN_WORD = 5
OTHER_LANGUAGES = [REPO_ROOT / "data/raw/freq_es/es_50k.txt",
                   REPO_ROOT / "data/raw/freq_pt/pt_50k.txt"]


def strip_accents(word):
    return "".join(c for c in unicodedata.normalize("NFKD", word) if not unicodedata.combining(c))


def other_language_words():
    words = set()
    for path in OTHER_LANGUAGES:
        if not path.exists():
            raise FileNotFoundError(str(path) + " missing; run make data")
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if parts:
                    words.add(strip_accents(parts[0]).lower())
    return words


class RomanianFilter:
    def __init__(self, ro_forms=None):
        if ro_forms is None:
            ro_forms = _folded_items(GEN / "ro_words.tsv") | _folded_items(GEN / "ro_inflected.tsv")
        self.ro = {fold(w).lower() for w in ro_forms if len(w) >= 2}
        self.en = _folded_items(GEN / "en_words.tsv") | other_language_words()
        en_names = _folded_items(GEN / "en_names.tsv")
        self.names = _folded_items(GEN / "ro_names.tsv") - self.en - en_names

    def is_romanian(self, password):
        p = nfc(password)
        if any(c in RO_DIACRITICS for c in p):
            return True
        for tok in ALPHA.findall(fold(p).lower()):
            if tok in self.en:
                continue
            if len(tok) >= 3 and tok in self.names:
                return True
            if self.is_romanian_run(tok):
                return True
        return False

    # the letters split completely into Romanian words, one of 5+ letters
    def is_romanian_run(self, tok):
        n = len(tok)
        ok = [set() for _ in range(n + 1)]
        ok[0].add(False)
        for i in range(n):
            if not ok[i]:
                continue
            for j in range(i + 2, n + 1):
                piece = tok[i:j]
                if piece in self.ro:
                    long_word = len(piece) >= MIN_WORD and piece not in self.en
                    for had in ok[i]:
                        ok[j].add(had or long_word)
        return True in ok[n]


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


def case_study_sample(totals, seed, frac=0.10):
    rng = np.random.default_rng(seed)
    by_group = {}
    for pw, c in totals.items():
        by_group.setdefault(reuse_group(c), []).append(pw)
    out = []
    for group in sorted(by_group):
        pws = sorted(by_group[group])
        k = max(1, round(len(pws) * frac))
        for i in sorted(rng.choice(len(pws), size=min(k, len(pws)), replace=False)):
            out.append(pws[i])
    return sorted(out)


BREACH_DIR = REPO_ROOT / "data/breach"
COUNTS_FILE = BREACH_DIR / "rockyou-withcount.txt"
BREACH_FILE = BREACH_DIR / "rockyou.txt"
METER = REPO_ROOT / "data/lexicon/meter"


def _write_lines(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def parse_count_line(line):
    # "  290729 123456": count, one space, password (which may itself start with spaces)
    t = line.rstrip("\n").lstrip(" ")
    num, _, pw = t.partition(" ")
    return pw, int(num)


def read_rockyou():
    # (password, number of accounts), most frequent first
    if COUNTS_FILE.exists():
        with open(COUNTS_FILE, encoding="utf-8", errors="replace") as f:
            for line in f:
                pw, c = parse_count_line(line)
                if pw:
                    yield pw, c
    elif BREACH_FILE.exists():
        with open(BREACH_FILE, encoding="utf-8", errors="replace") as f:
            for line in f:
                pw = line.rstrip("\n")
                if pw:
                    yield pw, 1
    else:
        raise SystemExit("no data/breach/rockyou-withcount.txt or rockyou.txt; supply it first")


def attacker_rockyou(romanian, split, order):
    # RockYou in frequency order, where a Romanian password counts only its
    # occurrences in the attacker share (and is left out when it has none)
    ro = sorted(((a, order[pw], pw) for pw, (m, a, v) in split.items() if a > 0),
                key=lambda x: (-x[0], x[1]))
    out = []
    k = 0
    for raw, c in read_rockyou():
        if nfc(raw) in romanian:
            continue
        while k < len(ro) and ro[k][0] > c:
            out.append(ro[k][2])
            k += 1
        out.append(raw)
    out += [x[2] for x in ro[k:]]
    return out


def write_pcfg_training(romanian, split, path):
    # one line per account: RockYou without the meter and validation shares,
    # so the grammar learns from how often each password is used
    done = set()
    with open(path, "w", encoding="utf-8") as f:
        for raw, c in read_rockyou():
            pw = nfc(raw)
            if pw in romanian:
                # two raw lines can have the same NFC form: write its share only once
                if pw in done:
                    continue
                done.add(pw)
                c = split[pw][1]
                raw = pw
            for _ in range(c):
                f.write(raw + "\n")


def write_precision_sample(sample):
    # never overwrite the hand labels of an earlier run
    path = PRIVATE / "precision_sample.csv"
    if path.exists():
        with open(path, encoding="utf-8", newline="") as f:
            old = list(csv.DictReader(f))
        if any(r["is_romanian"].strip() for r in old):
            if [r["password"] for r in old] != sample:
                path = PRIVATE / "precision_sample_new.csv"
                print("the precision sample changed; the labelled file is kept, new sample in", path)
            else:
                print("precision sample unchanged; the hand labels are kept")
                return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["password", "is_romanian"])
        for pw in sample:
            w.writerow([pw, ""])


def run(cfg):
    seed = cfg["breach"]["seed"]
    sp = cfg["breach"]["split"]
    shares = (sp["meter"], sp["attacker"], sp["validation"])
    filt = RomanianFilter()
    counts = {}
    order = {}
    for idx, (raw, c) in enumerate(read_rockyou()):
        pw = nfc(raw)
        if pw in counts or filt.is_romanian(pw):
            if pw not in counts:
                counts[pw] = 0
                order[pw] = idx
            counts[pw] += c
    print("romanian passwords found:", len(counts), "accounts:", sum(counts.values()))

    split = split_occurrences(counts, seed, shares)
    by_share = lambda k: sorted((pw for pw in split if split[pw][k] > 0),
                                key=lambda p: (-split[p][k], order[p]))
    meter = by_share(0)
    attacker = by_share(1)
    validation = {pw: split[pw][2] for pw in by_share(2)}

    # the meter ranks its leaked passwords by their count in the meter share
    with open(METER / "ro_leaked.tsv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["item", "rank", "freq"])
        for i, pw in enumerate(meter, start=1):
            w.writerow([pw, i, split[pw][0]])

    _write_lines(BREACH_DIR / "ro_attacker_share.txt", attacker)
    _write_lines(BREACH_DIR / "rockyou_attacker.txt", attacker_rockyou(set(counts), split, order))

    PRIVATE.mkdir(parents=True, exist_ok=True)
    with open(PRIVATE / "validation.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["password", "count", "total"])
        for pw, c in validation.items():
            w.writerow([pw, c, counts[pw]])
    write_pcfg_training(set(counts), split, BREACH_DIR / "pcfg_training.txt")
    write_precision_sample(precision_sample(counts, seed, cfg["breach"]["precision_sample"]))

    TABLES.mkdir(parents=True, exist_ok=True)
    prof = profile(validation)
    with open(TABLES / "breach_profile.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in prof.items():
            w.writerow([k, v])
    print("meter share:", len(meter), "attacker share:", len(attacker),
          "validation:", len(validation))
    # record the sha256 of the inputs and of what was just written
    from .fetch_sources import check_breach
    check_breach()


def _main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    run(load_config(ap.parse_args().config))


if __name__ == "__main__":
    _main()
