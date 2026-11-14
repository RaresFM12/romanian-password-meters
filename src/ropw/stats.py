import numpy as np
from scipy import stats as sps
from statsmodels.stats.contingency_tables import StratifiedTable
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint


def cluster_bootstrap(clusters, stat_fn, b=10000, seed=0):
    rng = np.random.default_rng(seed)
    clusters = np.asarray(clusters)
    _, inv = np.unique(clusters, return_inverse=True)
    k = inv.max() + 1
    idx_by = [np.where(inv == c)[0] for c in range(k)]
    thetas = np.empty(b, dtype=float)
    for i in range(b):
        pick = rng.integers(0, k, size=k)
        rows = np.concatenate([idx_by[p] for p in pick])
        thetas[i] = stat_fn(rows)
    return thetas


def bootstrap_ci(thetas, alpha=0.05):
    lo = float(np.nanpercentile(thetas, 100 * alpha / 2))
    hi = float(np.nanpercentile(thetas, 100 * (1 - alpha / 2)))
    return lo, hi


def bootstrap_pvalue_gt0(thetas):
    thetas = np.asarray(thetas, dtype=float)
    return float((1 + np.sum(thetas <= 0)) / (len(thetas) + 1))


def wilson_interval(k, n, alpha=0.05):
    lo, hi = proportion_confint(k, n, alpha=alpha, method="wilson")
    return float(lo), float(hi)


def cmh_test(tables):
    st = StratifiedTable([np.asarray(t, dtype=float) for t in tables])
    res = st.test_null_odds(correction=False)
    orr = float(st.oddsratio_pooled)
    p_two = float(res.pvalue)
    if orr > 1:
        p_greater = p_two / 2
    else:
        p_greater = 1 - p_two / 2
    return {
        "statistic": float(res.statistic),
        "p_two_sided": p_two,
        "oddsratio_pooled": orr,
        "p_one_sided_greater": float(p_greater),
    }


def binom_test(k, n, p, alternative="two-sided"):
    return float(sps.binomtest(k, n, p, alternative=alternative).pvalue)


def wilcoxon_greater(diffs):
    d = np.asarray(diffs, dtype=float)
    d = d[d != 0]
    if len(d) == 0:
        return 1.0
    return float(sps.wilcoxon(d, alternative="greater").pvalue)


def holm(pvalues, alpha=0.05):
    pvalues = list(pvalues)
    reject, p_corr, _, _ = multipletests(pvalues, alpha=alpha, method="holm")
    return {
        "reject": [bool(x) for x in reject],
        "p_corrected": [float(x) for x in p_corr],
    }
