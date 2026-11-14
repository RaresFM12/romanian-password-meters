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
