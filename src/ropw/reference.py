import argparse
import numpy as np
import pandas as pd
from .config import REPO_ROOT, load_config

REF = REPO_ROOT / "data/reference"
TABLES = REPO_ROOT / "results/tables"
SYNTH = REPO_ROOT / "data/synthetic"

MAIN_ATTACKERS = ["A-EN", "A-RO", "A-ALL", "A-JTR", "A-PCFG"]
REQUIRED = {"password", "attacker", "guess_number", "censored", "budget", "run"}


def load_reference(path):
    df = pd.read_csv(path)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError("reference file missing columns: " + str(sorted(missing)))
    df["censored"] = df["censored"].astype(bool)
    return df


def compute_reference(df, attackers=None, run="full", cut=None):
    if attackers is None:
        attackers = MAIN_ATTACKERS
    sub = df[(df["run"] == run) & (df["attacker"].isin(attackers))].copy()
    found = sub[(~sub["censored"]) & sub["guess_number"].notna()].copy()
    if cut is not None:
        found = found[found["guess_number"] <= cut]
    if len(found):
        best = found.loc[found.groupby("password")["guess_number"].idxmin()]
    else:
        best = found
    best = best.set_index("password")
    rows = []
    for pw in sub["password"].unique():
        if pw in best.index:
            rows.append({"password": pw, "g_star": float(best.loc[pw, "guess_number"]),
                         "censored": False, "min_attacker": best.loc[pw, "attacker"]})
        else:
            rows.append({"password": pw, "g_star": np.nan, "censored": True,
                         "min_attacker": None})
    return pd.DataFrame(rows)


def reference_checks(df, ref, probes, random_passwords):
    checks = []

    rnd_found = ref[(ref["password"].isin(random_passwords)) & (~ref["censored"])]
    checks.append(("random_never_found", len(rnd_found) == 0,
                   str(len(rnd_found)) + " RANDOM passwords were found"))

    if probes is not None and len(probes):
        merged = probes.merge(
            df[df["run"] == "full"][["password", "attacker", "guess_number"]],
            left_on=["attacker", "probe"], right_on=["attacker", "password"], how="left")
        good = (merged["guess_number"] <= merged["expected_position"]).fillna(False)
        checks.append(("probes_found_at_position", bool(good.all()),
                       str(int((~good).sum())) + " probes off"))

    small = df[df["run"] == "small"].set_index(["password", "attacker"])["guess_number"]
    full = df[df["run"] == "full"].set_index(["password", "attacker"])["guess_number"]
    common = small.index.intersection(full.index)
    disagree = 0
    for idx in common:
        s = small[idx]
        f = full[idx]
        if pd.notna(s) and s <= 1e8 and s != f:
            disagree += 1
    checks.append(("small_full_agree_1e8", disagree == 0, str(disagree) + " disagreements <= 1e8"))

    share = ref[~ref["censored"]]["min_attacker"].value_counts(normalize=True)
    dominant = float(share.max()) if len(share) else 1.0
    checks.append(("attacker_diversity", dominant < 0.95,
                   "top attacker gives " + str(round(dominant * 100)) + "% of minima"))

    return pd.DataFrame(checks, columns=["check", "passed", "detail"])


def _random_passwords():
    out = set()
    for csv in SYNTH.glob("case_seed*.csv"):
        df = pd.read_csv(csv)
        out |= set(df[df["category"] == "RANDOM"]["password"])
    return out


def run(config):
    load_config(config)
    gn = REF / "guess_numbers.csv"
    if not gn.exists():
        print("reference file", gn, "not supplied; analysis will skip until it exists")
        return True
    df = load_reference(gn)
    ref = compute_reference(df)
    probes = pd.read_csv(REF / "probes.csv") if (REF / "probes.csv").exists() else None
    checks = reference_checks(df, ref, probes, _random_passwords())
    TABLES.mkdir(parents=True, exist_ok=True)
    checks.to_csv(TABLES / "reference_checks.csv", index=False)
    ref.to_csv(REF / "reference_gstar.csv", index=False)
    print(checks.to_string(index=False))
    passed = bool(checks["passed"].all())
    print("ALL CHECKS PASS" if passed else "CHECKS FAILED")
    return passed


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    args = ap.parse_args()
    raise SystemExit(0 if run(args.config) else 1)


if __name__ == "__main__":
    _main()
