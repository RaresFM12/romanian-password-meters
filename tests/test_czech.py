import pytest

from ropw import czech
from ropw.config import REPO_ROOT
from ropw.meters.zx_bridge import run_bridge

_BRIDGE = (REPO_ROOT / "bridge/node_modules").exists()
_CZ = (REPO_ROOT / "data/lexicon/meter/cz_ro_cultural.tsv").exists()

def test_rare_and_short():
    assert czech.is_rare_and_short("ab", 5)
    assert czech.is_rare_and_short("abc", 1000)
    assert not czech.is_rare_and_short("abc", 500)

def test_brutal_better_readme_example():

    mr = {"republic": 688}
    assert czech.is_brutal_better("republica", 32852, mr)
    assert not czech.is_brutal_better("republic", 688, {})

def test_prune_drops_short_and_redundant():

    tokens = ["ab", "republic"] + [f"filler{i}" for i in range(1100)] + ["republica"]
    kept = {t for t, _ in czech.prune(tokens)}
    assert "ab" not in kept
    assert "republic" in kept
    assert "republica" not in kept

@pytest.mark.skipif(not (_BRIDGE and _CZ), reason="bridge or cz lists not built")
def test_ro_cz_does_not_handle_diacritics_but_ro_plus_does():
    items = [("w", "fetitza")]
    pkg = run_bridge("M-ZX-RO-PKG", items)["w"]["guesses"]
    cz = run_bridge("M-ZX-RO-CZ", items)["w"]["guesses"]
    rop = run_bridge("M-ZX-RO+", items)["w"]["guesses"]
    assert cz == pkg
    assert rop < cz

@pytest.mark.skipif(not (_BRIDGE and _CZ), reason="bridge or cz lists not built")
def test_ro_cz_improves_on_cultural():
    cz = run_bridge("M-ZX-RO-CZ", [("w", "Steaua1986")])["w"]["guesses"]
    pkg = run_bridge("M-ZX-RO-PKG", [("w", "Steaua1986")])["w"]["guesses"]
    assert cz < pkg


# zxcvbn-czech build_frequency_lists.py, written out literally
def _reference_filter(lists):
    import collections
    freq_lists = {}
    for name, toks in lists.items():
        dq = collections.deque()
        for i, t in enumerate(toks):
            rank = i + 1
            if czech.is_rare_and_short(t, rank) or len(set(t)) == 1 or "," in t or '"' in t:
                continue
            dq.append(t)
        freq_lists[name] = dq

    def first_uniq_token(freq_list, minimum_rank, rank):
        if len(freq_list) == 0:
            return None
        first = freq_list.popleft()
        if first in minimum_rank or czech.is_brutal_better(first, rank, minimum_rank):
            return first_uniq_token(freq_list, minimum_rank, rank)
        return first

    result = {name: [] for name in freq_lists}
    minimum_rank = {}
    rank = 0
    is_next = True
    while is_next:
        rank += 1
        is_next = False
        for name in sorted(freq_lists):
            token = first_uniq_token(freq_lists[name], minimum_rank, rank)
            if token:
                minimum_rank[token] = rank
                result[name].append(token)
                is_next = True
    return result


def test_filter_matches_zxcvbn_czech_reference():
    import random
    import sys
    sys.setrecursionlimit(20000)
    rng = random.Random(1)
    for _ in range(100):
        lists = {}
        for name in ("a", "b", "c"):
            toks = []
            for _ in range(rng.randint(0, 1500)):
                t = "".join(rng.choice("abcde") for _ in range(rng.randint(1, 7)))
                if t not in toks:
                    toks.append(t)
            lists[name] = toks
        assert czech.filter_lists(lists) == _reference_filter(lists)
