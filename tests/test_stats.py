import numpy as np

from ropw import stats as st

def test_wilson_known_value():
    lo, hi = st.wilson_interval(50, 100)
    assert np.isclose(lo, 0.4038, atol=1e-3)
    assert np.isclose(hi, 0.5962, atol=1e-3)

def test_cluster_bootstrap_is_deterministic():
    clusters = np.repeat(np.arange(20), 3)
    data = np.random.default_rng(0).random(60)
    fn = lambda rows: float(data[rows].mean())
    a = st.cluster_bootstrap(clusters, fn, b=200, seed=42)
    b = st.cluster_bootstrap(clusters, fn, b=200, seed=42)
    assert np.array_equal(a, b)
    lo, hi = st.bootstrap_ci(a)
    assert lo < data.mean() < hi

def test_bootstrap_pvalue_directions():
    assert np.isclose(st.bootstrap_pvalue_gt0(np.ones(999)), 1 / 1000)
    assert np.isclose(st.bootstrap_pvalue_gt0(-np.ones(999)), 1.0)

def test_cmh_one_sided():

    tables = [[[20, 10], [10, 20]], [[18, 12], [9, 21]]]
    out = st.cmh_test(tables)
    assert out["oddsratio_pooled"] > 1
    assert out["p_one_sided_greater"] < 0.05

def test_binom_matches_t7_example():

    p = st.binom_test(8, 2000, 0.01, alternative="less")
    assert p < 0.05 / 12

def test_wilcoxon_greater():
    diffs = [0.4, 0.9, 0.3, 1.2, 0.7, -0.1, 0.5]
    assert st.wilcoxon_greater(diffs) < 0.05
    assert np.isclose(st.wilcoxon_greater([0, 0, 0]), 1.0)

def test_holm():
    out = st.holm([0.01, 0.02, 0.03, 0.04], alpha=0.05)

    assert out["reject"] == [True, False, False, False]
    assert np.isclose(out["p_corrected"][0], 0.04)
