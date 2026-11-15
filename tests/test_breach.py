import numpy as np
import pytest

from ropw import breach
from ropw.config import REPO_ROOT

_HAS_LISTS = (REPO_ROOT / "data/lexicon/generator/ro_words.tsv").exists()

@pytest.mark.skipif(not _HAS_LISTS, reason="generator lists not built")
def test_filter_detects_romanian():
    f = breach.RomanianFilter(ro_forms={"vacanță", "iubire", "iubesc", "iubita", "parola", "te", "mea",
                                         "dragostea", "password"})
    assert f.is_romanian("vacanță123")
    assert f.is_romanian("iubire2020")
    assert f.is_romanian("teiubesc")
    assert f.is_romanian("iubitamea")
    assert f.is_romanian("parolamea123")
    assert not f.is_romanian("password123")
    assert not f.is_romanian("qwerty")

def test_split_preserves_occurrences():
    counts = {"a": 1000, "b": 7, "c": 1, "vacanta123": 55}
    split = breach.split_occurrences(counts, seed=3)
    for pw, c in counts.items():
        assert sum(split[pw]) == c

def test_split_is_deterministic():
    counts = {"x": 500, "y": 3}
    assert breach.split_occurrences(counts, 1) == breach.split_occurrences(counts, 1)

def test_reuse_group():
    assert breach.reuse_group(5000) == "1000+"
    assert breach.reuse_group(300) == "100-999"
    assert breach.reuse_group(1) == "1-1"

def test_profile_aggregates_only():
    counts = {"Vacanta1!": 10, "iubire": 3, "parolă": 2}
    p = breach.profile(counts)
    assert p["passwords"] == 3 and p["occurrences"] == 15
    assert p["with_diacritics"] == 1
    assert "digit" in p["class_counts"]

def test_case_study_sample_stratified():
    rng = np.random.default_rng(0)
    validation = {f"pw{i}": int(c) for i, c in enumerate(rng.integers(1, 50, 200))}
    sample = breach.case_study_sample(validation, seed=7, frac=0.10)
    assert 0 < len(sample) < len(validation)
    assert all(k in validation for k in sample)
    assert sample == breach.case_study_sample(validation, seed=7, frac=0.10)

def test_precision_sample_is_unlabeled():
    counts = {f"pw{i}": 1 for i in range(500)}
    sample = breach.precision_sample(counts, seed=1, n=300)
    assert len(sample) == 300 and len(set(sample)) == 300


def test_parse_count_line_keeps_spaces_in_password():
    assert breach.parse_count_line("  290729 123456\n") == ("123456", 290729)
    assert breach.parse_count_line("      2  pw\n") == (" pw", 2)


def test_attacker_rockyou_uses_attacker_counts(monkeypatch):
    rows = [("123456", 100), ("iubire", 50), ("qwerty", 40), ("dragoste", 30), ("abc", 1)]
    monkeypatch.setattr(breach, "read_rockyou", lambda: iter(rows))
    split = {"iubire": (20, 10, 20), "dragoste": (30, 0, 0)}
    order = {"iubire": 1, "dragoste": 3}
    out = breach.attacker_rockyou({"iubire", "dragoste"}, split, order)
    # iubire moves down to its attacker count (10); dragoste has no attacker occurrence
    assert out == ["123456", "qwerty", "iubire", "abc"]
