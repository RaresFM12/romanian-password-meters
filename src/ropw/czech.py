import csv
from .config import REPO_ROOT
from .normalize import to_ascii

METER = REPO_ROOT / "data/lexicon/meter"

MIN_TOKEN_LENGTH = 3
BRUTAL_MIN_LENGTH = 5
MIN_GUESSES_BEFORE_GROWING_SEQUENCE = 1000

CZ_SOURCE_LISTS = ["ro_names_ext", "ro_places", "ro_cultural", "ro_expressions", "ro_leaked"]


def is_rare_and_short(token, rank):
    return len(token) < MIN_TOKEN_LENGTH or rank >= 10 ** len(token)


def is_brutal_better(token, rank, minimum_rank):
    if rank < MIN_GUESSES_BEFORE_GROWING_SEQUENCE:
        return False
    if len(token) < BRUTAL_MIN_LENGTH:
        return False
    short = token[:-1]
    if short in minimum_rank:
        return rank > minimum_rank[short] * 22 + MIN_GUESSES_BEFORE_GROWING_SEQUENCE
    return False


def prune(tokens):
    minimum_rank = {}
    out = []
    rank = 0
    for token in tokens:
        rank += 1
        if is_rare_and_short(token, rank):
            continue
        if is_brutal_better(token, rank, minimum_rank):
            continue
        if token not in minimum_rank:
            minimum_rank[token] = rank
        out.append((token, rank))
    return out


def _fold_dedup(path):
    seen = set()
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            t = to_ascii(r["item"]).lower()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    return out


def build_cz_lists():
    sizes = {}
    for name in CZ_SOURCE_LISTS:
        src = METER / (name + ".tsv")
        if not src.exists():
            continue
        pruned = prune(_fold_dedup(src))
        out = METER / ("cz_" + name + ".tsv")
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["item", "rank", "freq"])
            for i, (token, rank) in enumerate(pruned, start=1):
                w.writerow([token, i, rank])
        sizes["cz_" + name] = len(pruned)
    return sizes


if __name__ == "__main__":
    for name, n in build_cz_lists().items():
        print(name, n)
