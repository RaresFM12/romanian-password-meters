import argparse
import hashlib
import json
import subprocess
import sys
from .config import REPO_ROOT, load_config

RESULTS = REPO_ROOT / "results"


def _git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                             capture_output=True, text=True).stdout.strip()
        return out or None
    except Exception:
        return None


def _git_dirty():
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT,
                             capture_output=True, text=True).stdout
        return bool(out.strip())
    except Exception:
        return None


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


TRACKED = ["data/sources.lock.yaml", "data/reference/guess_numbers.csv",
           "data/reference/reference_gstar.csv", "data/reference/attack_manifest.txt",
           "data/reference/probes.csv", "results/private/real_sample.csv"]
TRACKED_GLOBS = ["data/synthetic/case_seed*.csv", "data/lexicon/generator/*.tsv",
                 "data/lexicon/meter/*.tsv", "data/lexicon/meter/*.txt",
                 "results/meters/*/*.parquet", "results/private/meters_real/*.parquet"]


def _hashes():
    paths = [REPO_ROOT / p for p in TRACKED]
    for g in TRACKED_GLOBS:
        paths += sorted(REPO_ROOT.glob(g))
    return {str(p.relative_to(REPO_ROOT)): _sha256(p) for p in paths if p.exists()}


def _npm_versions():
    lock = REPO_ROOT / "bridge/package-lock.json"
    if not lock.exists():
        return {}
    data = json.loads(lock.read_text(encoding="utf-8"))
    out = {}
    for key, meta in data.get("packages", {}).items():
        if key.startswith("node_modules/@zxcvbn-ts/") or key == "node_modules/zxcvbn":
            out[key.replace("node_modules/", "")] = meta.get("version")
    return out


def write_manifest(config):
    cfg = load_config(config)
    cfg_bytes = (REPO_ROOT / config).read_bytes()
    manifest = {
        "config": config,
        "config_sha256": hashlib.sha256(cfg_bytes).hexdigest(),
        "scale": cfg["scale"],
        "seeds": cfg["seeds"],
        "python": sys.version.split()[0],
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "reference_year": cfg["scoring"]["reference_year"],
        "files_sha256": _hashes(),
        "npm_packages": _npm_versions(),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    m = write_manifest(ap.parse_args().config)
    print("run_manifest.json: scale=" + m["scale"], "npm=" + str(len(m["npm_packages"])))


if __name__ == "__main__":
    _main()
