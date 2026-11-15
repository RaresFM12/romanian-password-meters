import argparse
import numpy as np
import pandas as pd
from .breach import case_study_sample
from .config import REPO_ROOT, load_config
from .meters.block import Block
from .meters.policy import Policy
from .meters.zx_bridge import BRIDGE, run_bridge
from .normalize import nfc

SYNTH = REPO_ROOT / "data/synthetic"
OUT = REPO_ROOT / "results/meters"
PRIVATE = REPO_ROOT / "results/private"
TABLES = REPO_ROOT / "results/tables"

RULE_METERS = ["M-POLICY", "M-POLICY-STRICT", "M-BLOCK"]
ZX_METERS = ["M-ZX-ORIG", "M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+", "RO-PKG+norm"]
NESTING_CHAIN = ["M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+"]
GROUPS = ["norm", "digraph", "clean", "names", "places", "cultural", "leaked", "patterns"]
ABLATION_METERS = ["A+" + g for g in GROUPS] + ["A-" + g for g in GROUPS]


def read_passwords(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


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


def evaluate_meter(meter, df, core=None, policy_cfg=None):
    res = _evaluate(meter, df, core, policy_cfg)
    # stored so the analysis can check the result belongs to this dataset
    res.insert(1, "nfc", [nfc(p) for p in df["password"]])
    return res


def _evaluate(meter, df, core=None, policy_cfg=None):
    if meter in ("M-POLICY", "M-POLICY-STRICT"):
        pol = Policy(strict=meter.endswith("STRICT"), cfg=policy_cfg)
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


def d_variants(cfg):
    out = [("M-ZX-RO+", d) for d in cfg["scoring"]["D_variants"]]
    out.append(("M-ZX-RO-CZ", cfg["meters"]["czech"]["D_secondary"]))
    return out


def run_extras(cfg, df, out_dir):
    for meter in ABLATION_METERS:
        evaluate_meter(meter, df).to_parquet(out_dir / (meter + ".parquet"), index=False)
        print("ablation", meter, "done")
    for base, d in d_variants(cfg):
        core = BRIDGE / ("vendor/core-D" + str(d) + "/index.mjs")
        if not core.exists():
            raise FileNotFoundError(str(core) + " missing; run bridge/make_dvariants.sh")
        res = evaluate_meter(base, df, core=str(core))
        res.to_parquet(out_dir / (base + "-D" + str(d) + ".parquet"), index=False)
        print("D-variant", base, "D=" + str(d), "done")


def check_nesting(results):
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


def run_dataset(df, out_dir, meters, cfg, label):
    out_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for meter in meters:
        res = evaluate_meter(meter, df, policy_cfg=cfg["policy"])
        results[meter] = res
        res.to_parquet(out_dir / (meter + ".parquet"), index=False)
        print(label, meter, len(res), "rows")
    viol = check_nesting(results)
    viol.insert(0, "dataset", label)
    return viol


def real_sample(cfg):
    path = PRIVATE / "validation.csv"
    if not path.exists():
        return None
    v = read_passwords(path)
    counts = {p: int(c) for p, c in zip(v["password"], v["count"])}
    totals = {p: int(t) for p, t in zip(v["password"], v["total"])}
    if cfg["seeds"]["real_sample"]:
        pws = case_study_sample(totals, cfg["seeds"]["real_sample"])
    else:
        pws = sorted(counts)
    df = pd.DataFrame({"id": ["real-" + str(i).zfill(6) for i in range(len(pws))],
                       "password": pws, "count": [counts[p] for p in pws],
                       "total": [totals[p] for p in pws]})
    df.to_csv(PRIVATE / "real_sample.csv", index=False)
    return df


def run(config, meters, all_seeds=False, extras=False, real=False):
    cfg = load_config(config)
    seeds = [cfg["seeds"]["main"]]
    if all_seeds:
        seeds += list(cfg["seeds"]["extra"])
    violations = []
    for seed in seeds:
        csv = SYNTH / ("case_seed" + str(seed) + ".csv")
        if not csv.exists():
            print("skip seed", seed, "(not generated)")
            continue
        df = read_passwords(csv)
        out_dir = OUT / ("seed" + str(seed))
        violations.append(run_dataset(df, out_dir, meters, cfg, "seed" + str(seed)))
        if extras and seed == cfg["seeds"]["main"]:
            run_extras(cfg, df, out_dir)
    if real:
        df = real_sample(cfg)
        if df is None:
            print("no results/private/validation.csv; skip the real passwords")
        else:
            violations.append(run_dataset(df, PRIVATE / "meters_real", meters, cfg, "real"))
    TABLES.mkdir(parents=True, exist_ok=True)
    nv = pd.concat(violations, ignore_index=True) if violations else pd.DataFrame()
    path = TABLES / "nesting_violations.csv"
    ran = ["seed" + str(seed) for seed in seeds] + (["real"] if real else [])
    if path.exists():
        old = pd.read_csv(path)
        if len(old) and "dataset" in old.columns:
            old = old[~old["dataset"].isin(ran)]
            nv = pd.concat([old, nv], ignore_index=True)
    nv.to_csv(path, index=False)
    print("nesting violations:", len(nv))


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    ap.add_argument("--meters", nargs="*", default=RULE_METERS + ZX_METERS)
    ap.add_argument("--all-seeds", action="store_true")
    ap.add_argument("--extras", action="store_true",
                    help="also run the ablation meters and D-variants (E4, E5)")
    ap.add_argument("--real", action="store_true", help="also run the real passwords (E7)")
    args = ap.parse_args()
    run(args.config, args.meters, args.all_seeds, args.extras, args.real)


if __name__ == "__main__":
    _main()
