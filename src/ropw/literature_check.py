import argparse
import numpy as np
import pandas as pd
from . import metrics as mx
from .breach import COUNTS_FILE, parse_count_line
from .config import REPO_ROOT, load_config
from .meters.zx_bridge import run_bridge

TABLES = REPO_ROOT / "results/tables"
TOP = 10000
SAMPLE = 1000
REPEATS = 100
REPORTED = {"M-ZX-ORIG": 0.989}
METERS = ["M-ZX-ORIG", "M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO+"]


def most_common(n=TOP):
    pws = []
    counts = []
    with open(COUNTS_FILE, encoding="utf-8", errors="replace") as f:
        for line in f:
            pw, c = parse_count_line(line)
            if pw:
                pws.append(pw)
                counts.append(c)
            if len(pws) == n:
                break
    return pws, np.array(counts, dtype=float)


def run(config):
    load_config(config)
    if not COUNTS_FILE.exists():
        print("no data/breach/rockyou-withcount.txt; skip")
        return None
    # Golla and Duermuth [2], online scenario: 1,000 passwords sampled uniformly from
    # the 10,000 most common RockYou passwords; reference = frequency; weights = counts
    pws, counts = most_common()
    items = [("p" + str(i), pw) for i, pw in enumerate(pws)]
    rng = np.random.default_rng(2018)
    samples = [rng.choice(len(pws), size=SAMPLE, replace=False) for _ in range(REPEATS)]
    rows = []
    for meter in METERS:
        recs = run_bridge(meter, items)
        guesses = np.array([recs[i]["guesses"] for i, _ in items], dtype=float)
        rhos = [mx.weighted_spearman(guesses[s], -counts[s], counts[s]) for s in samples]
        rows.append({"meter": meter, "sample_size": SAMPLE, "repeats": REPEATS,
                     "weighted_spearman_mean": float(np.mean(rhos)),
                     "weighted_spearman_p2_5": float(np.percentile(rhos, 2.5)),
                     "weighted_spearman_p97_5": float(np.percentile(rhos, 97.5)),
                     "weighted_spearman_all_10000": mx.weighted_spearman(guesses, -counts, counts),
                     "reported_by_golla_durmuth": REPORTED.get(meter, np.nan)})
        print(meter, round(float(np.mean(rhos)), 4))
    out = pd.DataFrame(rows)
    TABLES.mkdir(parents=True, exist_ok=True)
    out.to_csv(TABLES / "literature_check.csv", index=False)
    return out


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    run(ap.parse_args().config)


if __name__ == "__main__":
    _main()
