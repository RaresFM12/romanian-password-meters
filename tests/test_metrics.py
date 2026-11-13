import numpy as np
from scipy import stats

from ropw import metrics as mx

def test_levels():
    g = [1, 1005, 2000, 1_000_005, 2e8, 2e10]
    assert list(mx.score_level(g)) == [0, 1, 1, 2, 3, 4]

def test_reference_level_censored_is_4():
    g = [1e4, 1e12]
    cen = [False, True]
    assert list(mx.reference_level(g, cen)) == [1, 4]

def test_spearman_equals_scipy():
    rng = np.random.default_rng(0)
    m = rng.random(50)
    r = rng.random(50)
    assert np.isclose(mx.spearman(m, r), stats.spearmanr(m, r).statistic)

def test_weighted_spearman_reduces_to_spearman():
    rng = np.random.default_rng(1)
    m = rng.random(40)
    r = rng.random(40)
    w = np.ones(40)
    assert np.isclose(mx.weighted_spearman(m, r, w), mx.spearman(m, r), atol=1e-9)

def test_weighted_spearman_hand_example():

    assert np.isclose(mx.weighted_spearman([1, 2, 3], [1, 3, 2], [1, 1, 2]), 1 / 3)

def test_censoring_ties_at_top():

    ref = mx._ref_with_censoring([10.0, 20.0, 999.0, 888.0], [False, False, True, True])
    assert ref[2] == ref[3] == 200.0

    m = [1.0, 2.0, 3.0, 3.0]
    assert np.isclose(mx.spearman(m, [10.0, 20.0, 999.0, 888.0],
                                  [False, False, True, True]), 1.0)

def test_dor_and_sur():
    scores = [0, 1, 3, 4, 2]
    weak = [True, True, True, True, False]

    assert np.isclose(mx.dor(scores, weak), 0.5)
    notfound = [True, True, False, False, True]

    assert np.isclose(mx.sur(scores, notfound), 2 / 3)

def test_dor_nan_when_no_weak():
    assert np.isnan(mx.dor([3, 4], [False, False]))

def test_weak_mask():
    g = [1e3, 1e7, 5e5]
    cen = [False, False, True]
    assert list(mx.weak_mask(g, cen, 1e6)) == [True, False, False]

def test_confusion_and_reclassification():
    cm = mx.confusion_matrix([0, 4, 2], [0, 4, 3])
    assert cm[0, 0] == 1 and cm[4, 4] == 1 and cm[2, 3] == 1 and cm.sum() == 3

    rc = mx.reclassification(score_a=[0, 4], score_b=[2, 2], ref_level=[2, 4])
    assert rc["closer"] == 0.5 and rc["farther"] == 0.5 and rc["same"] == 0.0

def test_log_error():
    out = mx.log_error([1e5, 1e8], [1e4, 1e8], [True, True])
    assert np.isclose(out["mean_signed"], 0.5)
    assert np.isclose(out["mean_abs"], 0.5)

def test_spreads_and_eta():
    assert mx.score_spread([1, 3, 2]) == 2
    assert np.isclose(mx.estimate_spread([1e4, 1e6]), 2.0)
    assert np.isclose(mx.eta(8.0, 5.0, 7.0, 5.0), 1.0)

def test_floor_attribution():

    out = list(mx.floor_attribution([1e5, 1e9]))
    assert out == ["floor", "knowledge"]
