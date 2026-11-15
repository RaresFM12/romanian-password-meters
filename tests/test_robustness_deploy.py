import numpy as np
import pandas as pd
from ropw import analyse, robustness, deployment
from ropw.config import load_config
from ropw.metrics import score_level

CFG = load_config("config/case_study.yaml")
analyse.setup(CFG)


def _merged(n=60):
    rng = np.random.default_rng(0)
    cats = ["RO-word-num"] * 20 + ["EN-word-num"] * 20 + ["RANDOM"] * 20
    g = rng.integers(1000, 10**9, n).astype(float)
    cen = np.array([c == "RANDOM" for c in cats])
    g[cen] = np.nan
    df = pd.DataFrame({"id": [f"p{i}" for i in range(n)], "category": cats,
                       "cluster_id": list(range(n)), "g_star": g, "censored": cen})
    base = np.where(np.isnan(g), 1e11, g) * rng.uniform(0.5, 2, n)
    for m in analyse.ZX_METERS:
        df[f"{m}__guesses"] = base
        df[f"{m}__score"] = score_level(df[f"{m}__guesses"].to_numpy())
        df[f"{m}__pt"] = df[f"{m}__guesses"] * 0.5
    return df


def test_key_results_row():
    row = robustness.key_results(_merged(), CFG)
    assert {"rho_pkg", "rho_ro_plus", "dor_pkg", "dor_ro_plus", "gap_pkg"} <= set(row)
    row2 = robustness.key_results(_merged(), CFG, weak_threshold=1e8)
    assert row2["n_weak_open"] >= row["n_weak_open"]


def test_bundle_kb_is_number():
    for m in deployment.MAIN:
        kb = deployment.bundle_kb(m)
        assert isinstance(kb, float) and kb >= 0
