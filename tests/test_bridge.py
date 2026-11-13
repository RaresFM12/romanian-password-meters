import pytest

from ropw.config import REPO_ROOT
from ropw.meters.zx_bridge import run_bridge

pytestmark = pytest.mark.skipif(
    not (REPO_ROOT / "bridge/node_modules").exists(),
    reason="bridge not installed (run npm install in bridge/)")

PWS = ["vacanta", "Andrei1999!", "TeIubescMult", "VacantaLaMare1!"]
ITEMS = [(p, p) for p in PWS]

def _formula_holds(rec) -> bool:
    k = rec["k"]
    expected = rec["product_term"] + 10000 ** (k - 1)
    return abs(expected - rec["guesses"]) <= max(1.0, rec["guesses"] * 1e-9)

@pytest.mark.parametrize("cfg", ["M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-ORIG"])
def test_guesses_formula(cfg):
    recs = run_bridge(cfg, ITEMS)
    assert len(recs) == len(PWS)
    for rec in recs.values():
        assert _formula_holds(rec), rec

def test_plan_table_en():
    r = run_bridge("M-ZX-EN", ITEMS)
    assert r["vacanta"]["score"] == 1 and round(r["vacanta"]["log10"]) == 5
    assert r["Andrei1999!"]["score"] == 3
    assert r["TeIubescMult"]["score"] == 4
    assert r["VacantaLaMare1!"]["score"] == 4

def test_plan_table_ro_pkg():
    r = run_bridge("M-ZX-RO-PKG", ITEMS)
    assert r["vacanta"]["score"] == 1 and round(r["vacanta"]["log10"]) == 4
    assert r["Andrei1999!"]["score"] == 3

    assert r["TeIubescMult"]["score"] == 3 and r["TeIubescMult"]["k"] == 3
    assert 1.5e7 < r["TeIubescMult"]["product_term"] < 2.5e7
    assert r["VacantaLaMare1!"]["score"] == 4

def test_english_only_overrates_romanian():
    en = run_bridge("M-ZX-EN", [("w", "TeIubescMult")])["w"]
    ro = run_bridge("M-ZX-RO-PKG", [("w", "TeIubescMult")])["w"]
    assert en["guesses"] > ro["guesses"]
