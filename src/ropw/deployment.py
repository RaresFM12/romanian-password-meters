import argparse
import gzip
import numpy as np
import pandas as pd
from .config import REPO_ROOT, load_config
from .meters.zx_bridge import run_bridge

SYNTH = REPO_ROOT / "data/synthetic"
METER = REPO_ROOT / "data/lexicon/meter"
TABLES = REPO_ROOT / "results/tables"
NODE = REPO_ROOT / "bridge/node_modules/@zxcvbn-ts"
EXT = REPO_ROOT / "packages/zxcvbn-ro-extended/src"

RO_LISTS = ["ro_common_clean", "ro_names_ext", "ro_places", "ro_cultural",
            "ro_expressions", "ro_calendar", "ro_leaked"]
CZ_LISTS = ["cz_" + n for n in RO_LISTS]
MAIN = ["M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+"]


def package_files(name):
    files = sorted((NODE / name / "dist").rglob("*.mjs"))
    if not files:
        raise FileNotFoundError("no files for package " + name)
    return files


def meter_files(meter):
    files = package_files("core") + package_files("language-common") + package_files("language-en")
    if meter == "M-ZX-EN":
        return files
    files += package_files("language-ro")
    if meter == "M-ZX-RO-PKG":
        return files
    files += [METER / (n + ".tsv") for n in CZ_LISTS]
    files += [EXT / n for n in ("patterns.mjs", "dictionaries.mjs", "fold.mjs", "tables.json")]
    if meter == "M-ZX-RO-CZ":
        return files
    files += [METER / (n + ".tsv") for n in RO_LISTS] + [EXT / "matchers.mjs"]
    return files


def list_bytes(path):
    # only what the meter reads: the words in rank order, plus the rank for the
    # Romanian lists (the folding matcher needs it; the cz_ ranks are positions)
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, quoting=3)
    df = df.sort_values("rank", key=lambda r: r.astype(int), kind="stable")
    if path.name.startswith("cz_"):
        lines = df["item"]
    else:
        lines = df["item"] + "\t" + df["rank"]
    return ("\n".join(lines) + "\n").encode("utf-8")


def bundle_kb(meter):
    blob = b""
    for p in meter_files(meter):
        if not p.exists():
            raise FileNotFoundError(str(p) + " missing; the size would be too small")
        blob += list_bytes(p) if p.suffix == ".tsv" else p.read_bytes()
    return round(len(gzip.compress(blob)) / 1024, 1)


def run(config):
    cfg = load_config(config)
    df = pd.read_csv(SYNTH / ("case_seed" + str(cfg["seeds"]["main"]) + ".csv"),
                     dtype=str, keep_default_na=False)
    items = list(zip(df["id"], df["password"]))
    base = bundle_kb("M-ZX-EN")
    rows = []
    for meter in MAIN:
        recs = run_bridge(meter, items)
        ms = np.array([r["ms"] for r in recs.values()], dtype=float)
        size = bundle_kb(meter)
        rows.append({"meter": meter, "bundle_kb": size, "bundle_kb_added": round(size - base, 1),
                     "median_ms": round(float(np.median(ms)), 4),
                     "p95_ms": round(float(np.percentile(ms, 95)), 3), "n": len(ms)})
    out = pd.DataFrame(rows)
    TABLES.mkdir(parents=True, exist_ok=True)
    out.to_csv(TABLES / "deployment.csv", index=False)
    print(out.to_string(index=False))
    print("reference: the Czech adaptation aims at a 900 KB library")
    return out


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    run(ap.parse_args().config)


if __name__ == "__main__":
    _main()
