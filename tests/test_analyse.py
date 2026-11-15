import numpy as np
import pandas as pd
from ropw import analyse
from ropw.config import load_config
from ropw.metrics import score_level

CFG = load_config("config/case_study.yaml")
analyse.setup(CFG)


def _merged(n=120):
    rng = np.random.default_rng(0)
    cats = (["RO-word"] * 20 + ["RO-translit"] * 20 + ["RANDOM"] * 20
            + ["RO-diacritic"] * 20 + ["EN-word-num"] * 20 + ["RO-word-num"] * 20)
    g_star = rng.integers(1_000, 10**9, n).astype(float)
    censored = np.array([c == "RANDOM" for c in cats])
    g_star[censored] = np.nan
    lang = ["en" if c.startswith("EN") else ("random" if c == "RANDOM" else "ro") for c in cats]
    fam = [""] * 60 + ["fam" + str(i % 4) for i in range(20)] + [""] * 40
    spell = [""] * 60 + (["ascii", "digraph", "pre1993_ascii", "correct", "decomposed"] * 4) + [""] * 40
    df = pd.DataFrame({
        "id": ["p" + str(i) for i in range(n)],
        "password": ["pw" + str(i) for i in range(n)],
        "category": cats, "language": lang, "band": ["0"] * n,
        "cluster_id": list(range(n)), "family_id": fam, "spelling": spell,
        "g_star": g_star, "censored": censored,
    })
    base = np.where(np.isnan(g_star), 1e11, g_star) * rng.uniform(0.5, 2, n)
    for meter in analyse.ZX_METERS + ["RO-PKG+norm"]:
        f = 0.8 if meter in ("M-ZX-RO+", "RO-PKG+norm") else 1.0
        df[meter + "__guesses"] = base * f
        df[meter + "__score"] = score_level(df[meter + "__guesses"].to_numpy())
        df[meter + "__pt"] = df[meter + "__guesses"] * 0.5
    for meter in ("M-POLICY", "M-BLOCK"):
        df[meter + "__score"] = rng.integers(0, 5, n)
        df[meter + "__guesses"] = np.nan
    return df


def test_accuracy_table_shape():
    acc = analyse.accuracy_table(_merged(), CFG)
    assert {"meter", "group", "spearman", "dor", "sur", "n", "male_signed"} <= set(acc.columns)
    assert acc[acc["meter"] == "M-POLICY"]["spearman"].isna().all()
    assert acc[acc["meter"] == "M-ZX-EN"]["spearman"].notna().any()


def test_run_tests_produces_holm_and_decisions():
    t = analyse.run_tests(_merged(), CFG)
    assert len(t) >= 1
    assert {"n", "ci_low", "ci_high", "p_holm", "decision"} <= set(t.columns)
    assert set(t["decision"]) <= {"pass", "fail", "undecided"}
    assert (t["label"] == "illustrative").all()


def test_holm_uses_all_twelve_tests():
    t = analyse.run_tests(_merged(), CFG)
    ok = t[t["p_raw"].notna() & ~t["undecided"]]
    i = ok["p_raw"].idxmin()
    assert ok.loc[i, "p_holm"] >= min(1.0, 12 * ok.loc[i, "p_raw"]) - 1e-12


def test_t6_is_a_real_test():
    t = analyse.run_tests(_merged(), CFG).set_index("test")
    assert 0 < t.loc["T6", "p_raw"] <= 1


def test_dor_tests_undecided_with_few_weak():
    t = analyse.run_tests(_merged(), CFG).set_index("test")
    for test in ("T2", "T3", "T4"):
        if test in t.index:
            assert t.loc[test, "decision"] == "undecided"


def test_hypothesis_needs_all_tests():
    tests = pd.DataFrame({"test": ["T3", "T4", "T5"], "hypothesis": ["H2b", "H2b", "H3a"],
                          "decision": ["pass", "fail", "pass"]})
    h = analyse.hypothesis_table(tests).set_index("hypothesis")
    assert h.loc["H2b", "verdict"] == "not supported"
    assert h.loc["H3a", "verdict"] == "supported"


def test_spelling_consistency():
    sc = analyse.spelling_consistency(_merged(), "M-ZX-RO-PKG")
    assert set(sc.columns) == {"family_id", "delta_score", "delta_log"}
    assert len(sc) == 4
