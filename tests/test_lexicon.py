import numpy as np

from ropw.lexicon import SeedList

BANDS = [[1, 100], [101, 1000], [1001, 10000], [10001, 50000]]

def test_load_sorts_by_rank(tmp_path):
    p = tmp_path / "s.tsv"
    p.write_text("item\trank\tfreq\nb\t2\t5\na\t1\t9\nc\t3\t1\n", encoding="utf-8")
    sl = SeedList.load(p)
    assert sl.items == ["a", "b", "c"]
    assert sl.size == 3

def test_usable_bands_truncate_for_short_list():
    sl = SeedList.from_items("x", [f"w{i}" for i in range(500)])
    bands = sl.usable_bands(BANDS)
    assert bands == [(1, 100), (101, 500)]

def test_full_list_uses_all_bands():
    sl = SeedList.from_items("x", [f"w{i}" for i in range(50000)])
    assert sl.usable_bands(BANDS) == [(1, 100), (101, 1000), (1001, 10000), (10001, 50000)]

def test_sample_in_band_range():
    sl = SeedList.from_items("x", [f"w{i}" for i in range(1000)])
    rng = np.random.default_rng(0)
    for _ in range(200):
        item, rank = sl.sample(rng, (101, 1000))
        assert 101 <= rank <= 1000
        assert item == f"w{rank - 1}"

def test_filter_preserves_order():
    sl = SeedList.from_items("x", ["abc", "fetiță", "pâine", "casa"])
    only_diac = sl.filter(lambda w: any(c in w for c in "ăâîșț"))
    assert only_diac.items == ["fetiță", "pâine"]
