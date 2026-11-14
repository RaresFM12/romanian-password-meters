import argparse
import numpy as np
import pandas as pd
from .config import REPO_ROOT, load_config
from .meters.block import Block
from .meters.policy import Policy
from .meters.zx_bridge import BRIDGE, run_bridge

SYNTH = REPO_ROOT / "data/synthetic"
OUT = REPO_ROOT / "results/meters"
TABLES = REPO_ROOT / "results/tables"

ZX_METERS = ["M-ZX-ORIG", "M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+", "RO-PKG+norm"]
NESTING_CHAIN = ["M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+"]
GROUPS = ["norm", "digraph", "clean", "names", "places", "cultural", "leaked", "patterns"]
ABLATION_METERS = ["A+" + g for g in GROUPS] + ["A-" + g for g in GROUPS]
D_VARIANTS = [("M-ZX-RO+", 1000), ("M-ZX-RO+", 100), ("M-ZX-RO+", 10), ("M-ZX-RO-CZ", 1000)]


def _frame_from_recs(df, recs):
    rows = [recs[i] for i in df["id"]]
    return pd.DataFrame({
        "id": df["id"],
        "score": [r["score"] for r in rows],
        "guesses": [float(r["guesses"]) for r in rows],
        "log10": [r["log10"] for r in rows],
        "k": [r["k"] for r in rows],
        "product_term": [float(r["product_term"]) for r in rows],
    })


def evaluate_meter(meter, df, core=None):
    if meter in ("M-POLICY", "M-POLICY-STRICT"):
        pol = Policy(strict=meter.endswith("STRICT"))
        scores = [pol.score(p) for p in df["password"]]
        return pd.DataFrame({"id": df["id"], "score": scores, "guesses": np.nan,
                             "log10": np.nan, "k": pd.NA, "product_term": np.nan})
    if meter == "M-BLOCK":
        blk = Block()
        scores = [blk.score(p) for p in df["password"]]
        return pd.DataFrame({"id": df["id"], "score": scores, "guesses": np.nan,
                             "log10": np.nan, "k": pd.NA, "product_term": np.nan})
    recs = run_bridge(meter, list(zip(df["id"], df["password"])), core=core)
    return _frame_from_recs(df, recs)


def run_extras(seed):
    csv = SYNTH / ("case_seed" + str(seed) + ".csv")
    df = pd.read_csv(csv)
    out_dir = OUT / ("seed" + str(seed))
    out_dir.mkdir(parents=True, exist_ok=True)
    for meter in ABLATION_METERS:
        evaluate_meter(meter, df).to_parquet(out_dir / (meter + ".parquet"), index=False)
        print("ablation", meter, "done")
    for base, d in D_VARIANTS:
        core = str(BRIDGE / ("vendor/core-D" + str(d) + "/index.mjs"))
        res = evaluate_meter(base, df, core=core)
        res.to_parquet(out_dir / (base + "-D" + str(d) + ".parquet"), index=False)
        print("D-variant", base, "D=" + str(d), "done")


def check_nesting(results, ids):
    rows = []
    chain = [m for m in NESTING_CHAIN if m in results]
    for a, b in zip(chain, chain[1:]):
        ga = results[a].set_index("id")["guesses"]
        gb = results[b].set_index("id")["guesses"]
        viol = gb > ga * (1 + 1e-9)
        for pid in ga.index[viol.reindex(ga.index, fill_value=False)]:
            rows.append({"meter_a": a, "meter_b": b, "id": pid,
                         "guesses_a": ga[pid], "guesses_b": gb[pid]})
    return pd.DataFrame(rows, columns=["meter_a", "meter_b", "id", "guesses_a", "guesses_b"])


def run(config, meters, seeds=None):
    cfg = load_config(config)
    if seeds is None:
        seeds = [cfg["seeds"]["main"]]
    all_violations = []
    for seed in seeds:
        csv = SYNTH / ("case_seed" + str(seed) + ".csv")
        if not csv.exists():
            print("skip seed", seed, "(not generated)")
            continue
        df = pd.read_csv(csv)
        out_dir = OUT / ("seed" + str(seed))
        out_dir.mkdir(parents=True, exist_ok=True)
        results = {}
        for meter in meters:
            res = evaluate_meter(meter, df)
            results[meter] = res
            res.to_parquet(out_dir / (meter.replace("/", "_") + ".parquet"), index=False)
            print("seed", seed, meter, len(res), "rows")
        viol = check_nesting(results, list(df["id"]))
        viol.insert(0, "seed", seed)
        all_violations.append(viol)
    TABLES.mkdir(parents=True, exist_ok=True)
    if all_violations:
        nv = pd.concat(all_violations, ignore_index=True)
    else:
        nv = pd.DataFrame()
    nv.to_csv(TABLES / "nesting_violations.csv", index=False)
    print("nesting violations:", len(nv))


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    ap.add_argument("--meters", nargs="*",
                    default=["M-POLICY", "M-POLICY-STRICT", "M-BLOCK"] + ZX_METERS)
    ap.add_argument("--all-seeds", action="store_true")
    ap.add_argument("--extras", action="store_true",
                    help="also run the ablation meters and D-variants (E5)")
    args = ap.parse_args()
    cfg = load_config(args.config)
    seeds = [cfg["seeds"]["main"]] + list(cfg["seeds"]["extra"]) if args.all_seeds else None
    run(args.config, args.meters, seeds)
    if args.extras:
        run_extras(cfg["seeds"]["main"])


if __name__ == "__main__":
    _main()
