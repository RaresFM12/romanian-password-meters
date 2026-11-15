import csv
import unicodedata
from collections import deque
from .config import REPO_ROOT
from .normalize import to_ascii

METER = REPO_ROOT / "data/lexicon/meter"

# port of zxcvbn-czech data-scripts/build_frequency_lists.py
MIN_TOKEN_LENGTH = 3
BRUTAL_MIN_LENGTH = 5
MIN_GUESSES_BEFORE_GROWING_SEQUENCE = 1000

CZ_SOURCE_LISTS = ["ro_common_clean", "ro_names_ext", "ro_places", "ro_cultural",
                   "ro_expressions", "ro_calendar", "ro_leaked"]


def is_rare_and_short(token, rank):
    return len(token) < MIN_TOKEN_LENGTH or rank >= 10 ** len(token)


def has_only_one_char(token):
    return len(set(token)) == 1


def has_comma_or_double_quote(token):
    return "," in token or '"' in token


def is_brutal_better(token, rank, minimum_rank):
    if rank < MIN_GUESSES_BEFORE_GROWING_SEQUENCE:
        return False
    if len(token) < BRUTAL_MIN_LENGTH:
        return False
    short = token[:-1]
    if short in minimum_rank:
        return rank > minimum_rank[short] * 22 + MIN_GUESSES_BEFORE_GROWING_SEQUENCE
    return False


def parse_list(tokens):
    kept = deque()
    for i, token in enumerate(tokens):
        rank = i + 1
        if is_rare_and_short(token, rank):
            continue
        if has_only_one_char(token):
            continue
        if has_comma_or_double_quote(token):
            continue
        kept.append(token)
    return kept


def filter_lists(lists):
    queues = {name: parse_list(tokens) for name, tokens in lists.items()}
    result = {name: [] for name in lists}
    minimum_rank = {}
    rank = 0
    more = True
    while more:
        rank += 1
        more = False
        for name in sorted(queues):
            q = queues[name]
            token = None
            while q:
                t = q.popleft()
                if t in minimum_rank or is_brutal_better(t, rank, minimum_rank):
                    continue
                token = t
                break
            if token is not None:
                minimum_rank[token] = rank
                result[name].append(token)
                more = True
    return result


def prune(tokens):
    return [(t, i + 1) for i, t in enumerate(filter_lists({"x": list(tokens)})["x"])]


def _fold_dedup(path):
    seen = set()
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    rows.sort(key=lambda r: int(r["rank"]))
    for r in rows:
        t = "".join(c for c in to_ascii(r["item"]).lower()
                    if unicodedata.category(c) != "Cf")
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_cz_lists():
    lists = {}
    for name in CZ_SOURCE_LISTS:
        src = METER / (name + ".tsv")
        if not src.exists():
            raise FileNotFoundError(str(src) + " missing; build the meter lists first")
        lists[name] = _fold_dedup(src)
    pruned = filter_lists(lists)
    sizes = {}
    for name, tokens in pruned.items():
        out = METER / ("cz_" + name + ".tsv")
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["item", "rank", "freq"])
            for i, token in enumerate(tokens, start=1):
                w.writerow([token, i, i])
        sizes["cz_" + name] = len(tokens)
    return sizes


if __name__ == "__main__":
    for name, n in build_cz_lists().items():
        print(name, n)
