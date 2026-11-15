import json
import os
import subprocess
from ..config import REPO_ROOT

BRIDGE = REPO_ROOT / "bridge"

_ZXTS = {"M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO+", "RO-PKG+norm", "M-ZX-RO-CZ"}
_ORIG = {"M-ZX-ORIG"}


def run_bridge(config, items, core=None):
    if config in _ORIG:
        script = "zx_orig.mjs"
        arg = config
    elif config in _ZXTS or config.startswith("A+") or config.startswith("A-"):
        script = "zx.mjs"
        arg = config
    else:
        raise ValueError("unknown meter config: " + config)

    payload = ""
    for i, p in items:
        payload += json.dumps({"id": i, "password": p}, ensure_ascii=False) + "\n"
    env = None
    if core:
        env = {**os.environ, "ZXCVBN_CORE": core}
    proc = subprocess.run(["node", script, arg], input=payload,
                          capture_output=True, text=True, cwd=BRIDGE, env=env)
    if proc.returncode != 0:
        raise RuntimeError("bridge " + config + " failed:\n" + proc.stderr)

    out = {}
    for line in proc.stdout.splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["id"]] = rec
    missing = {i for i, _ in items} - out.keys()
    if missing:
        raise RuntimeError("bridge " + config + ": " + str(len(missing)) + " ids missing")
    return out


def evaluate_frame(config, df, id_col="id", pw_col="password"):
    items = list(zip(df[id_col].tolist(), df[pw_col].tolist()))
    results = run_bridge(config, items)
    return [results[i] for i in df[id_col].tolist()]
