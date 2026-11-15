import numpy as np
import pandas as pd
import pytest

from ropw import figures

def _accuracy():
    rows = []
    for m in figures.METER_ORDER:
        zx = m not in ("M-POLICY", "M-BLOCK")
        for g in ("all", "open_class", "ro_twins", "en_twins"):
            rows.append({"meter": m, "group": g, "n": 100,
                         "spearman": 0.6 if zx else np.nan,
                         "spearman_lo": 0.5 if zx else np.nan,
                         "spearman_hi": 0.7 if zx else np.nan,
                         "kendall": 0.5 if zx else np.nan,
                         "dor": 0.3, "dor_lo": 0.2, "dor_hi": 0.4,
                         "sur": 0.2, "sur_lo": 0.1, "sur_hi": 0.3, "male": 1.5})
    return pd.DataFrame(rows)


def test_run_writes_figures(tmp_path, monkeypatch):
    monkeypatch.setattr(figures, "TABLES", tmp_path)
    monkeypatch.setattr(figures, "FIGURES", tmp_path / "fig")
    _accuracy().to_csv(tmp_path / "accuracy.csv", index=False)
    monkeypatch.setattr(figures, "REF", tmp_path)
    paths = figures.run("config/case_study.yaml")
    assert len(paths) >= 2
    assert all((figures.REPO_ROOT / p).exists() for p in paths)

def test_check_rejects_unknown_meter():
    bad = _accuracy()
    bad.loc[0, "meter"] = "M-BOGUS"
    with pytest.raises(ValueError):
        figures._check(bad, ["meter", "group"])

def test_check_rejects_duplicate_rows():
    dup = pd.concat([_accuracy(), _accuracy()])
    with pytest.raises(ValueError):
        figures._check(dup, ["meter", "group"])
