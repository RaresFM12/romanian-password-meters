import argparse
import csv
import json
from pathlib import Path
import numpy as np
from .config import REPO_ROOT, load_config

REF = REPO_ROOT / "data/reference"
FOUND = REF / "found"
TARGETS = REPO_ROOT / "data/synthetic/targets_all.txt"
N_PROBES = 50
# 0 = finished; 141 / 120 = stopped by head (SIGPIPE)
OK_EXIT = {"0", "141", "120"}


def read_targets():
    with open(TARGETS, encoding="utf-8") as f:
        return [l.rstrip("\n") for l in f if l.rstrip("\n")]


def parse_found(path):
    first = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if ":" not in line:
                continue
            num, pw = line.split(":", 1)
            if num.isdigit() and pw not in first:
                first[pw] = int(num)
    return first


def write_positions(attacker, small, seed=3):
    rng = np.random.default_rng(seed + sum(ord(c) for c in attacker))
    pos = sorted(set(int(x) for x in rng.integers(1, small + 1, size=3 * N_PROBES)))
    FOUND.mkdir(parents=True, exist_ok=True)
    with open(FOUND / (attacker + ".positions"), "w") as f:
        f.write("\n".join(str(p) for p in pos) + "\n")


def pick_probes(attacker, seed=3):
    # 50 of the usable candidates, drawn at random so the probes cover the whole small run
    usable = []
    seen = set()
    with open(FOUND / (attacker + ".probe_candidates"), "rb") as f:
        for raw in f:
            num, _, cand = raw.rstrip(b"\n").partition(b":")
            try:
                text = cand.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if not text or "\r" in text or text in seen:
                continue
            seen.add(text)
            usable.append((text, int(num)))
    rng = np.random.default_rng(seed + 1 + sum(ord(c) for c in attacker))
    k = min(N_PROBES, len(usable))
    idx = sorted(rng.choice(len(usable), size=k, replace=False)) if k else []
    return [usable[i] for i in idx]


def write_probes(attackers):
    rows = []
    for a in attackers:
        for cand, pos in pick_probes(a):
            rows.append({"attacker": a, "probe": cand, "expected_position": pos})
    with open(REF / "probes.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["attacker", "probe", "expected_position"])
        w.writeheader()
        w.writerows(rows)
    words = read_targets()
    known = set(words)
    for r in rows:
        if r["probe"] not in known:
            known.add(r["probe"])
            words.append(r["probe"])
    with open(FOUND / "targets_with_probes.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(words) + "\n")
    return len(rows)


def check_run(attacker, run, budget):
    base = FOUND / (attacker + "." + run)
    status = Path(str(base) + ".status")
    count = Path(str(base) + ".count")
    if not status.exists() or not count.exists():
        raise ValueError(attacker + " " + run + ": no .status or .count file")
    for line in status.read_text().split("\n"):
        if line.strip():
            stage, code = line.split()
            if code not in OK_EXIT:
                raise ValueError(attacker + " " + run + ": stage " + stage
                                 + " failed with exit code " + code)
    n = int(count.read_text().strip())
    if n != budget:
        raise ValueError(attacker + " " + run + ": stream has " + str(n)
                         + " candidates, expected " + str(budget))


def assemble(records, out_path=None):
    if out_path is None:
        out_path = REF / "guess_numbers.csv"
    targets = read_targets()
    rows = []
    for rec in records:
        found = parse_found(REPO_ROOT / rec["found"])
        for pw in targets:
            gn = found.get(pw)
            if gn is not None and gn > rec["budget"]:
                raise ValueError(rec["attacker"] + ": guess number above the budget")
            rows.append({
                "password": pw,
                "attacker": rec["attacker"],
                "guess_number": gn if gn is not None else "",
                "censored": gn is None,
                "budget": rec["budget"],
                "run": rec["run"],
            })
    cols = ["password", "attacker", "guess_number", "censored", "budget", "run"]
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def measure_probes(records):
    path = REF / "probes.csv"
    with open(path, encoding="utf-8", newline="") as f:
        probes = list(csv.DictReader(f))
    full = {r["attacker"]: parse_found(REPO_ROOT / r["found"])
            for r in records if r["run"] == "full"}
    for p in probes:
        pos = full.get(p["attacker"], {}).get(p["probe"])
        p["measured_position"] = pos if pos is not None else ""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["attacker", "probe", "expected_position",
                                          "measured_position"])
        w.writeheader()
        w.writerows(probes)


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["positions", "probes", "assemble"])
    ap.add_argument("--attacker")
    ap.add_argument("--attackers", nargs="*", default=[])
    ap.add_argument("--small", type=int, default=10 ** 8)
    ap.add_argument("--config", default="config/case_study.yaml")
    args = ap.parse_args()
    if args.step == "positions":
        write_positions(args.attacker, args.small)
    elif args.step == "probes":
        print("probes:", write_probes(args.attackers))
    else:
        ref = load_config(args.config)["reference"]
        small = int(ref["smoke_budget"])
        records = []
        for a in args.attackers:
            budget = int(min(ref["run_budget"], ref["budgets"][a]))
            check_run(a, "small", small)
            check_run(a, "full", budget)
            records.append({"attacker": a, "run": "small", "budget": small,
                            "found": "data/reference/found/" + a + ".small.found"})
            records.append({"attacker": a, "run": "full", "budget": budget,
                            "found": "data/reference/found/" + a + ".full.found"})
        with open(REF / "runs.json", "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        n = assemble(records)
        measure_probes(records)
        print("wrote", REF / "guess_numbers.csv", "with", n, "rows")


if __name__ == "__main__":
    _main()
