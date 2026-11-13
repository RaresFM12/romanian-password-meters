import numpy as np
from scipy import stats

DEFAULT_THRESHOLDS = (1005.0, 1000005.0, 100000005.0, 10000000005.0)


def score_level(guesses, thresholds=DEFAULT_THRESHOLDS):
    g = np.asarray(guesses, dtype=float)[:, None]
    t = np.asarray(thresholds, dtype=float)[None, :]
    return (g >= t).sum(axis=1).astype(int)


def reference_level(g_star, censored, thresholds=DEFAULT_THRESHOLDS):
    lvl = score_level(g_star, thresholds)
    lvl = np.where(np.asarray(censored, dtype=bool), 4, lvl)
    return lvl.astype(int)


def _ref_with_censoring(g_star, censored):
    g = np.asarray(g_star, dtype=float).copy()
    cen = np.asarray(censored, dtype=bool)
    if cen.any():
        if (~cen).any():
            finite_max = g[~cen].max()
        else:
            finite_max = 1.0
        g[cen] = finite_max * 10.0
    return g


def _ref(g_star, censored):
    if censored is None:
        return g_star
    return _ref_with_censoring(g_star, censored)


def spearman(meter_guesses, g_star, censored=None):
    m = np.asarray(meter_guesses, dtype=float)
    return float(stats.spearmanr(m, _ref(g_star, censored)).statistic)


def kendall(meter_guesses, g_star, censored=None):
    m = np.asarray(meter_guesses, dtype=float)
    return float(stats.kendalltau(m, _ref(g_star, censored)).statistic)


def _weighted_rank(x, w):
    x = np.asarray(x, dtype=float)
    w = np.asarray(w, dtype=float)
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    ws = w[order]
    ranks = np.empty(len(x), dtype=float)
    i = 0
    below = 0.0
    n = len(xs)
    while i < n:
        j = i
        while j < n and xs[j] == xs[i]:
            j += 1
        eqw = ws[i:j].sum()
        ranks[order[i:j]] = below + 0.5 * eqw
        below += eqw
        i = j
    return ranks


def _weighted_pearson(a, b, w):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    w = np.asarray(w, dtype=float)
    total = w.sum()
    am = (w * a).sum() / total
    bm = (w * b).sum() / total
    cov = (w * (a - am) * (b - bm)).sum() / total
    va = (w * (a - am) ** 2).sum() / total
    vb = (w * (b - bm) ** 2).sum() / total
    return float(cov / np.sqrt(va * vb))


def weighted_spearman(meter_guesses, g_star, weights, censored=None):
    m = np.asarray(meter_guesses, dtype=float)
    r = _ref(g_star, censored)
    w = np.asarray(weights, dtype=float)
    return _weighted_pearson(_weighted_rank(m, w), _weighted_rank(r, w), w)


def dor(scores, weak_mask):
    s = np.asarray(scores)
    wk = np.asarray(weak_mask, dtype=bool)
    if wk.sum() == 0:
        return float("nan")
    return float((s[wk] >= 3).mean())


def sur(scores, notfound_mask):
    s = np.asarray(scores)
    nf = np.asarray(notfound_mask, dtype=bool)
    if nf.sum() == 0:
        return float("nan")
    return float((s[nf] <= 1).mean())


def weak_mask(g_star, censored, weak_threshold=1e6):
    g = np.asarray(g_star, dtype=float)
    cen = np.asarray(censored, dtype=bool)
    return (~cen) & (g <= weak_threshold)


def confusion_matrix(scores, ref_levels):
    s = np.asarray(scores, dtype=int)
    r = np.asarray(ref_levels, dtype=int)
    m = np.zeros((5, 5), dtype=int)
    for si, ri in zip(s, r):
        m[si, ri] += 1
    return m


def reclassification(score_a, score_b, ref_level):
    a = np.abs(np.asarray(score_a, dtype=int) - np.asarray(ref_level, dtype=int))
    b = np.abs(np.asarray(score_b, dtype=int) - np.asarray(ref_level, dtype=int))
    n = len(a)
    return {
        "closer": float((b < a).sum() / n),
        "farther": float((b > a).sum() / n),
        "same": float((b == a).sum() / n),
    }


def log_error(meter_guesses, g_star, found_mask):
    fm = np.asarray(found_mask, dtype=bool)
    m = np.log10(np.asarray(meter_guesses, dtype=float)[fm])
    r = np.log10(np.asarray(g_star, dtype=float)[fm])
    d = m - r
    return {"mean_abs": float(np.abs(d).mean()), "mean_signed": float(d.mean())}


def score_spread(scores_in_family):
    s = np.asarray(scores_in_family, dtype=int)
    return int(s.max() - s.min())


def estimate_spread(guesses_in_family):
    g = np.log10(np.asarray(guesses_in_family, dtype=float))
    return float(g.max() - g.min())


def eta(log_g_v, log_g_u, log_G_v, log_G_u):
    return float((log_g_v - log_g_u) - (log_G_v - log_G_u))


def floor_attribution(product_term, thresholds=DEFAULT_THRESHOLDS):
    lvl = score_level(product_term, thresholds)
    return np.where(lvl <= 2, "floor", "knowledge")
