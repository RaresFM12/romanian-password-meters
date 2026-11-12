"""C01: the two config files load and are internally consistent."""
import pytest

from ropw.config import load_config


@pytest.mark.parametrize("name", ["config/case_study.yaml", "config/full.yaml"])
def test_config_loads(name):
    cfg = load_config(name)
    assert cfg["scale"] in {"case_study", "full"}
    assert cfg["categories"]["RANDOM"] >= 1


def test_case_study_sizes():
    cfg = load_config("config/case_study.yaml")
    assert cfg["categories"]["RANDOM"] == 600, "RANDOM must stay 600 so T7 can pass"
    total = sum(cfg["categories"].values())
    assert 3000 < total < 4000, f"case-study total {total} out of expected range"


def test_full_sizes():
    cfg = load_config("config/full.yaml")
    assert cfg["categories"]["RO-word"] == 2000
    assert sum(cfg["categories"].values()) > 25000


def test_budgets_match_attackers():
    cfg = load_config("config/case_study.yaml")
    ref = cfg["reference"]
    assert set(ref["budgets"]) == set(ref["attackers_main"])
    assert ref["budgets"]["A-PCFG"] < ref["budgets"]["A-EN"]
