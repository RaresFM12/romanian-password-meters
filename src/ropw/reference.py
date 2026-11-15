import argparse
import numpy as np
import pandas as pd
from .config import REPO_ROOT, load_config

REF = REPO_ROOT / "data/reference"
TABLES = REPO_ROOT / "results/tables"
SYNTH = REPO_ROOT / "data/synthetic"

MAIN_ATTACKERS = ["A-EN", "A-RO", "A-ALL", "A-JTR", "A-PCFG"]
REQUIRED = {"password", "attacker", "guess_number", "censored", "budget", "run"}
MAX_SHARE = 0.95


def load_reference(path):
    df = pd.read_csv(path, dtype={"password": str}, keep_default_na=False)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError("reference file missing columns: " + str(sorted(missing)))
    df["guess_number"] = pd.to_numeric(df["guess_number"], errors="coerce")
    df["censored"] = df["censored"].astype(str).str.lower() == "true"
    df["budget"] = pd.to_numeric(df["budget"])
    return df


def compute_reference(df, attackers=None, run="full", cut=None):
    if attackers is None:
        attackers = MAIN_ATTACKERS
    sub = df[(df["run"] == run) & (df["attacker"].isin(attackers))].copy()
    found = sub[(~sub["censored"]) & sub["guess_number"].notna()].copy()
    if cut is not None:
        found = found[found["guess_number"] <= cut]
    best = found.groupby("password")["guess_number"].min()
    at_min = found[found["guess_number"] == found["password"].map(best)]
    # ties credit every attacker at the minimum
    who = at_min.groupby("password")["attacker"].apply(lambda s: "+".join(sorted(s)))
    rows = []
    for pw in sub["password"].unique():
        if pw in best.index:
            rows.append({"password": pw, "g_star": float(best[pw]), "censored": False,
                         "min_attacker": who[pw]})
        else:
            rows.append({"password": pw, "g_star": np.nan, "censored": True,
                         "min_attacker": ""})
    return pd.DataFrame(rows, columns=["password", "g_star", "censored", "min_attacker"])


def attacker_shares(ref):
    found = ref[~ref["censored"]]
    counts = {}
    for who in found["min_attacker"]:
        for a in who.split("+"):
            counts[a] = counts.get(a, 0) + 1
    n = len(found)
    rows = [{"attacker": a, "gives_minimum": c, "share": c / n if n else np.nan}
            for a, c in sorted(counts.items())]
    return pd.DataFrame(rows, columns=["attacker", "gives_minimum", "share"])


def reference_checks(df, ref, probes, random_passwords, small_budget=1e8):
    checks = []

    rnd_found = ref[(ref["password"].isin(random_passwords)) & (~ref["censored"])]
    checks.append(("random_never_found", len(rnd_found) == 0,
                   str(len(rnd_found)) + " RANDOM passwords were found"))

    if probes is None or len(probes) == 0 or "measured_position" not in probes.columns:
        checks.append(("probes_found_at_position", False, "no measured probes"))
    else:
        measured = pd.to_numeric(probes["measured_position"], errors="coerce")
        good = measured.notna() & (measured <= probes["expected_position"])
        checks.append(("probes_found_at_position", bool(good.all()),
                       str(int((~good).sum())) + " of " + str(len(probes)) + " probes off"))

    small = df[df["run"] == "small"].set_index(["password", "attacker"])["guess_number"]
    full = df[df["run"] == "full"].set_index(["password", "attacker"])["guess_number"]
    attackers_small = set(df[df["run"] == "small"]["attacker"])
    attackers_full = set(df[df["run"] == "full"]["attacker"])
    if not attackers_full or attackers_small != attackers_full:
        checks.append(("small_full_agree", False,
                       "small run missing for " + str(sorted(attackers_full - attackers_small))))
    else:
        disagree = 0
        for idx in small.index.intersection(full.index):
            s = small[idx]
            f = full[idx]
            s_in = pd.notna(s) and s <= small_budget
            f_in = pd.notna(f) and f <= small_budget
            if s_in != f_in or (s_in and s != f):
                disagree += 1
        checks.append(("small_full_agree", disagree == 0,
                       str(disagree) + " disagreements up to " + format(small_budget, ".0e")))

    shares = attacker_shares(ref)
    top = float(shares["share"].max()) if len(shares) else 1.0
    missing = [a for a in MAIN_ATTACKERS if a not in attackers_full]
    detail = "top attacker gives " + str(round(top * 100)) + "% of minima"
    if missing:
        detail += "; not run: " + ", ".join(missing)
    checks.append(("attacker_diversity", top < MAX_SHARE, detail))

    return pd.DataFrame(checks, columns=["check", "passed", "detail"])


def _random_passwords():
    out = set()
    for csv in SYNTH.glob("case_seed*.csv"):
        df = pd.read_csv(csv, dtype=str, keep_default_na=False)
        out |= set(df[df["category"] == "RANDOM"]["password"])
    return out


def run(config):
    cfg = load_config(config)
    gn = REF / "guess_numbers.csv"
    if not gn.exists():
        print("reference file", gn, "not supplied; analysis will skip until it exists")
        return False
    df = load_reference(gn)
    ref = compute_reference(df, attackers=cfg["reference"]["attackers_main"])
    probes = None
    if (REF / "probes.csv").exists():
        probes = pd.read_csv(REF / "probes.csv", dtype={"probe": str}, keep_default_na=False)
    checks = reference_checks(df, ref, probes, _random_passwords(),
                              cfg["reference"]["smoke_budget"])
    TABLES.mkdir(parents=True, exist_ok=True)
    checks.to_csv(TABLES / "reference_checks.csv", index=False)
    attacker_shares(ref).to_csv(TABLES / "attacker_shares.csv", index=False)
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
