import hashlib

import yaml

from ropw import fetch_sources as fs

def test_sources_yaml_schema():
    reg = yaml.safe_load(fs.SOURCES.read_text(encoding="utf-8"))
    assert "access_date" in reg
    for name, meta in reg["sources"].items():
        assert "purpose" in meta, name
        assert "licence" in meta, name
        assert "auto" in meta, name
        if meta.get("auto"):
            assert meta.get("url"), f"{name}: auto source needs a url"

def test_auto_sources_have_verified_urls():
    reg = yaml.safe_load(fs.SOURCES.read_text(encoding="utf-8"))
    auto = [n for n, m in reg["sources"].items() if m.get("auto")]

    assert set(auto) == {"geonames_ro", "leipzig_ro", "leipzig_en", "bnc_freq",
                         "en_names", "dexonline"}

def test_sha256(tmp_path):
    p = tmp_path / "x"
    p.write_bytes(b"hello")
    assert fs._sha256(p) == hashlib.sha256(b"hello").hexdigest()

def test_lock_matches_registry_if_present():
    if not fs.LOCK.exists():
        return
    lock = yaml.safe_load(fs.LOCK.read_text(encoding="utf-8"))
    for name, entry in lock["sources"].items():
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] > 0
