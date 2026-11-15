import argparse
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED = ["scale", "seeds", "categories", "families", "twins", "open_class",
            "generator", "reference", "scoring", "policy", "breach", "stats", "meters"]


def load_config(path):
    path = Path(path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key in REQUIRED:
        if key not in cfg:
            raise ValueError("missing section: " + key)
    check(cfg)
    cfg["_path"] = str(path)
    return cfg


def check(cfg):
    fam = cfg["families"]
    if fam["with_st"] + fam["with_circumflex"] + fam["with_breve_i"] != fam["total"]:
        raise ValueError("family counts do not add up to total")
    if abs(sum(cfg["generator"]["diacritic_shares"].values()) - 1.0) > 1e-9:
        raise ValueError("diacritic shares must sum to 1")
    if abs(sum(cfg["generator"]["case_style"].values()) - 1.0) > 1e-9:
        raise ValueError("case style must sum to 1")
    if abs(sum(cfg["breach"]["split"].values()) - 1.0) > 1e-9:
        raise ValueError("breach split must sum to 1")
    if len(cfg["scoring"]["score_thresholds"]) != 4:
        raise ValueError("need 4 score thresholds")
    for pair in cfg["twins"]:
        for cat in pair:
            if cat not in cfg["categories"]:
                raise ValueError("unknown twin category: " + cat)
    for cat in cfg["open_class"]:
        if cat not in cfg["categories"]:
            raise ValueError("unknown open_class category: " + cat)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config/case_study.yaml")
    args = p.parse_args()
    cfg = load_config(args.config)
    print(cfg["_path"], "ok  scale=" + cfg["scale"],
          "passwords=" + str(sum(cfg["categories"].values())))
