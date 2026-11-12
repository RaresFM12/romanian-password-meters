import argparse
import datetime
import hashlib
import urllib.request
from pathlib import Path
import yaml
from .config import REPO_ROOT

RAW = REPO_ROOT / "data/raw"
BREACH = REPO_ROOT / "data/breach"
SOURCES = REPO_ROOT / "data/sources.yaml"
LOCK = REPO_ROOT / "data/sources.lock.yaml"
UA = "ropw-research/1.0 (academic; contact via repository)"


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        expected = resp.headers.get("Content-Length")
        with open(dest, "wb") as out:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
    if expected is not None and dest.stat().st_size != int(expected):
        raise OSError("truncated download: got " + str(dest.stat().st_size)
                      + " of " + expected + " bytes")


def fetch(include_large=False):
    reg = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    lock = {}
    if LOCK.exists():
        lock = yaml.safe_load(LOCK.read_text(encoding="utf-8")) or {}
    lock.setdefault("sources", {})
    failures = []

    for name, meta in reg["sources"].items():
        if not meta.get("auto") or not meta.get("url"):
            print("skip  ", name)
            continue
        if meta.get("large") and not include_large:
            print("defer ", name, "(large; use --include-large)")
            continue
        filename = meta["url"].split("/")[-1].split("?")[0] or (name + ".data")
        dest = RAW / name / filename
        if dest.exists():
            digest = _sha256(dest)
            print("cached", name, digest[:12])
        else:
            print("fetch ", name, meta["url"])
            try:
                _download(meta["url"], dest)
            except Exception as exc:
                if dest.exists():
                    dest.unlink()
                failures.append((name, str(exc)))
                print("FAIL  ", name, exc)
                continue
            digest = _sha256(dest)
        prev = lock["sources"].get(name, {})
        if prev.get("sha256") and prev["sha256"] != digest and not meta.get("mutable"):
            raise SystemExit("checksum changed for immutable source " + name)
        lock["sources"][name] = {
            "url": meta["url"],
            "sha256": digest,
            "bytes": dest.stat().st_size,
            "fetched_at": datetime.date.today().isoformat(),
            "mutable": bool(meta.get("mutable")),
        }

    lock["access_date"] = reg.get("access_date")
    LOCK.write_text(yaml.safe_dump(lock, sort_keys=True, allow_unicode=True), encoding="utf-8")
    if failures:
        print("failed sources (fetch by hand):")
        for name, exc in failures:
            print(" ", name, exc)
    return lock


def check_breach():
    if not BREACH.exists():
        print("breach: data/breach/ absent")
        return
    files = [p for p in BREACH.iterdir() if p.is_file() and p.name != "manifest.lock"]
    manifest = {p.name: _sha256(p) for p in files}
    (BREACH / "manifest.lock").write_text(yaml.safe_dump(manifest, sort_keys=True),
                                          encoding="utf-8")
    print("breach: recorded", len(manifest), "files")


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    ap.add_argument("--include-large", action="store_true")
    args = ap.parse_args()
    lock = fetch(include_large=args.include_large)
    check_breach()
    print("locked", len(lock["sources"]), "sources")


if __name__ == "__main__":
    _main()
