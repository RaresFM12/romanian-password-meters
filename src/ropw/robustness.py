import argparse
import numpy as np
import pandas as pd
from . import analyse
from . import metrics as mx
from . import reference as refmod
from .config import REPO_ROOT, load_config

REF = REPO_ROOT / "data/reference"
TABLES = REPO_ROOT / "results/tables"


def key_results(merged, cfg, weak_threshold=None):
    open_mask = analyse.cat_mask(merged, cfg["open_class"])
    _, _, _, weak = analyse._arrays(merged, weak_threshold)
    row = {}
    for meter, short in (("M-ZX-RO-PKG", "pkg"), ("M-ZX-RO+", "ro_plus")):
        row["rho_" + short] = analyse.rho(merged, meter, open_mask)
        s = merged[meter + "__score"].to_numpy()
        row["dor_" + short] = mx.dor(s[open_mask], weak[open_mask])
    row["gap_pkg"] = analyse.dor_gap(merged, "M-ZX-RO-PKG", np.arange(len(merged)), weak)
    row["n_weak_open"] = int((weak & open_mask).sum())
    row["rho_ro_plus_higher"] = bool(row["rho_ro_plus"] > row["rho_pkg"])
    if row["n_weak_open"] < analyse.MIN_WEAK:
        row["dor_ro_plus_not_higher"] = "undecided"
    else:
        row["dor_ro_plus_not_higher"] = str(bool(row["dor_ro_plus"] <= row["dor_pkg"]))
    return row


def variation_rows(name, setting, merged, cfg, weak_threshold=None, budget=None):
    old_weak = analyse.WEAK
    old_boot = analyse.BOOT
    analyse.setup(cfg, budget=budget)
    if weak_threshold is not None:
        analyse.WEAK = float(weak_threshold)
    analyse.BOOT = analyse.BOOT_CI
    try:
        row = {"variation": name, "setting": setting, **key_results(merged, cfg, weak_threshold)}
        tests = analyse.run_tests(merged, cfg)
        for _, t in tests.iterrows():
            row[t["test"]] = t["decision"]
        hyp = analyse.hypothesis_table(tests)
        for _, h in hyp.iterrows():
            row[h["hypothesis"]] = h["verdict"]
    finally:
        analyse.setup(cfg)
        analyse.WEAK = old_weak
        analyse.BOOT = old_boot
    return row


def run(config):
    cfg = load_config(config)
    analyse.setup(cfg)
    gstar = REF / "reference_gstar.csv"
    gn_path = REF / "guess_numbers.csv"
    if not gstar.exists() or not gn_path.exists():
        print("need the reference first")
        return
    main_seed = cfg["seeds"]["main"]
    gn = refmod.load_reference(gn_path)
    attackers = cfg["reference"]["attackers_main"]
    run_budget = cfg["reference"]["run_budget"]
    rows = []

    base = analyse.load_merged(main_seed, analyse.read_reference(gstar))
    rows.append(variation_rows("main", "A-MIN, weak <= 1e6", base, cfg))

    for wt in cfg["scoring"]["weak_threshold_robust"]:
        rows.append(variation_rows("weak_threshold", "weak <= " + format(wt, ".0e"), base, cfg, wt))

    for a in sorted(gn[gn["run"] == "full"]["attacker"].unique()):
        ref = refmod.compute_reference(gn, attackers=[a])
        rows.append(variation_rows("single_attacker", a, analyse.load_merged(main_seed, ref), cfg))

    # A-RO replaced by the same attacker without spelling variants
    if "A-RO-NOVAR" in set(gn["attacker"]):
        novar = [("A-RO-NOVAR" if a == "A-RO" else a) for a in attackers]
        ref = refmod.compute_reference(gn, attackers=novar)
        rows.append(variation_rows("no_variants", "A-RO without spelling variants",
                                   analyse.load_merged(main_seed, ref), cfg))

    cut = cfg["reference"]["cut_variant"]
    if cut < run_budget:
        ref = refmod.compute_reference(gn, attackers=attackers, cut=cut)
        rows.append(variation_rows("cut", "all attackers cut at " + format(cut, ".0e"),
                                   analyse.load_merged(main_seed, ref), cfg, budget=cut))
    else:
        rows.append({"variation": "cut", "setting": "not applicable: the runs already stop at "
                     + format(run_budget, ".0e")})

    ref = analyse.read_reference(gstar)
    for seed in cfg["seeds"]["extra"]:
        if (analyse.METERS / ("seed" + str(seed)) / "M-ZX-RO+.parquet").exists():
            rows.append(variation_rows("seed", "dataset seed " + str(seed),
                                       analyse.load_merged(seed, ref), cfg))

    out = pd.DataFrame(rows)
    for h in analyse.HYPOTHESIS_TESTS:
        if h in out.columns:
            main = out.loc[0, h]
            out[h + "_same"] = out[h].map(lambda v: v == main if isinstance(v, str) else None)
    TABLES.mkdir(parents=True, exist_ok=True)
    out.to_csv(TABLES / "robustness.csv", index=False)
    print(out[["variation", "setting", "rho_pkg", "rho_ro_plus", "n_weak_open"]
              + [h for h in analyse.HYPOTHESIS_TESTS if h in out.columns]].to_string(index=False))
    print("\nnot run (need extra attacker runs or data): the reference without leaked data;"
          " spelling shares reweighted to the real set")


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    run(ap.parse_args().config)


if __name__ == "__main__":
    _main()
