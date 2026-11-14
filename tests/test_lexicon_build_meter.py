import csv
import json

import pytest

from ropw import lexicon_build_meter as mb

_SRC = mb.METER / "_src_commonwords.txt"
pytestmark = pytest.mark.skipif(
    not _SRC.exists(),
    reason="language-ro not exported (run bridge/export_ro.mjs data/lexicon/meter)")

@pytest.fixture(scope="module")
def built():
    sizes = mb.build_all()
    audit = mb.write_audit()
    mb.write_overlap()
    return sizes, audit

def test_audit_matches_plan(built):
    _, audit = built
    assert audit["entries"] == 48511
    assert audit["cedilla_comma_pairs"] == 2425
    assert audit["format_char_entries"] == 317
    assert audit["unique_after_fold"] == 40907
    assert (audit["rank_vacanta_cedilla"], audit["rank_vacanta_comma"],
            audit["rank_vacanta_ascii"]) == (2896, 7691, 11901)

def test_common_clean_keeps_every_spelling(built):
    with (mb.METER / "ro_common_clean.tsv").open(encoding="utf-8") as fh:
        items = {r["item"] for r in csv.DictReader(fh, delimiter="\t")}

    for spelling in ("vacanţă", "vacanță", "vacanta"):
        assert spelling in items

def test_names_include_diminutives(built):
    with (mb.METER / "ro_names_ext.tsv").open(encoding="utf-8") as fh:
        items = {r["item"] for r in csv.DictReader(fh, delimiter="\t")}
    assert "andu" in items and "mihăiță" in items

def test_meter_disjoint_from_generator(built):
    meter = json.loads((mb.METER / "manifest.json").read_text(encoding="utf-8"))
    gen_path = mb.GEN / "manifest.json"
    meter_inputs = {p for ins in meter["inputs"].values() for p in ins}

    for p in meter_inputs:
        assert "lexicon/generator" not in p
    if gen_path.exists():
        gen = json.loads(gen_path.read_text(encoding="utf-8"))
        gen_inputs = {p for ins in gen["inputs"].values() for p in ins}
        assert meter_inputs.isdisjoint(gen_inputs)

def test_meter_disjoint_from_attackers(built):
    att = mb.REPO_ROOT / "data/reference/attacker_inputs.txt"
    if not att.exists():
        return
    attacker_paths = {l.strip() for l in att.read_text(encoding="utf-8").splitlines()
                      if l.strip()}
    meter = json.loads((mb.METER / "manifest.json").read_text(encoding="utf-8"))
    meter_inputs = {p for ins in meter["inputs"].values() for p in ins}
    assert meter_inputs.isdisjoint(attacker_paths)
