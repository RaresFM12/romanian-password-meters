"""Load and validate the experiment configuration.

One YAML file holds every parameter (see config/case_study.yaml). Nothing in the
code hard-codes a size, threshold or seed; it all comes through here.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

_REQUIRED_TOP = {
    "scale", "seeds", "categories", "families", "twins", "open_class",
    "generator", "reference", "scoring", "policy", "breach", "stats", "meters",
}


def load_config(path: str | Path) -> dict[str, Any]:
    """Read a config file and check that the required sections are present."""
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    with path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    missing = _REQUIRED_TOP - cfg.keys()
    if missing:
        raise ValueError(f"{path.name}: missing sections {sorted(missing)}")
    _check_invariants(cfg)
    cfg["_path"] = str(path)
    return cfg


def _check_invariants(cfg: dict[str, Any]) -> None:
    """Catch config mistakes early, before any step runs."""
    fam = cfg["families"]
    if fam["with_st"] + fam["with_circumflex"] + fam["with_breve_i"] != fam["total"]:
        raise ValueError("families: band counts do not sum to total")

    shares = cfg["generator"]["diacritic_shares"]
    if abs(sum(shares.values()) - 1.0) > 1e-9:
        raise ValueError("generator.diacritic_shares must sum to 1")

    cs = cfg["generator"]["case_style"]
    if abs(sum(cs.values()) - 1.0) > 1e-9:
        raise ValueError("generator.case_style must sum to 1")

    split = cfg["breach"]["split"]
    if abs(sum(split.values()) - 1.0) > 1e-9:
        raise ValueError("breach.split must sum to 1")

    if len(cfg["scoring"]["score_thresholds"]) != 4:
        raise ValueError("scoring.score_thresholds must have 4 values")

    for pair in cfg["twins"]:
        for cat in pair:
            if cat not in cfg["categories"]:
                raise ValueError(f"twins reference unknown category {cat}")

    for cat in cfg["open_class"]:
        if cat not in cfg["categories"]:
            raise ValueError(f"open_class references unknown category {cat}")


def _main() -> None:
    ap = argparse.ArgumentParser(description="Validate a config file.")
    ap.add_argument("--config", default="config/case_study.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    total = sum(cfg["categories"].values())
    print(f"{cfg['_path']}: ok  scale={cfg['scale']}  "
          f"categories={len(cfg['categories'])}  passwords={total}")


if __name__ == "__main__":
    _main()
