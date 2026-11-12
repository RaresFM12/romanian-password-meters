import numpy as np
import pytest

from ropw.config import load_config
from ropw.generate import Generator, write_targets
from ropw.lexicon import SeedList

def make_seeds():
    plain = [f"word{i}" for i in range(150)]
    st = [f"vacanță{i}" for i in range(60)]
    circ = [f"pâine{i}" for i in range(20)]
    brevi = [f"casă{i}" for i in range(20)]
    ro_words = st + circ + brevi + plain
    ro_names = [f"ștefan{i}" for i in range(20)] + [f"andrei{i}" for i in range(120)]
    ro_places = [f"orasul{i}" for i in range(120)]
    ro_cultural = [f"steaua{i}" for i in range(120)]
    ro_inflected = [f"puiule{i}" for i in range(60)] + [f"frați{i}" for i in range(60)]
    en_words = [f"summer{i}" for i in range(140)]
    en_names = [f"michael{i}" for i in range(140)]

    def phrases(stem):
        out = []
        for i in range(60):
            out.append(f"{stem}a{i} {stem}b{i}")
            out.append(f"{stem}a{i} {stem}b{i} {stem}c{i}")
            out.append(f"{stem}a{i} {stem}b{i} {stem}c{i} {stem}d{i}")
        return out

    mk = SeedList.from_items
    return {
        "ro_words": mk("ro_words", ro_words),
        "ro_names": mk("ro_names", ro_names),
        "ro_phrases": mk("ro_phrases", phrases("ro")),
        "ro_places": mk("ro_places", ro_places),
        "ro_cultural": mk("ro_cultural", ro_cultural),
        "ro_inflected": mk("ro_inflected", ro_inflected),
        "en_words": mk("en_words", en_words),
        "en_names": mk("en_names", en_names),
        "en_phrases": mk("en_phrases", phrases("en")),
    }

@pytest.fixture(scope="module")
def cfg():
    return load_config("config/case_study.yaml")

@pytest.fixture(scope="module")
def df(cfg):
    return Generator(cfg, make_seeds(), seed=20261111).build()

def test_category_counts(cfg, df):
    counts = df["category"].value_counts().to_dict()
    for cat, n in cfg["categories"].items():
        assert counts[cat] == n, f"{cat}: {counts.get(cat)} != {n}"

    assert counts["RO-diacritic"] == 460

def test_ids_unique_and_nonempty(df):
    assert df["id"].is_unique
    assert (df["id"].str.len() > 0).all()
    assert (df["password"].str.len() > 0).all()

def test_determinism(cfg):
    a = Generator(cfg, make_seeds(), seed=20261111).build()
    b = Generator(cfg, make_seeds(), seed=20261111).build()
    assert a.to_csv(index=False) == b.to_csv(index=False)
    c = Generator(cfg, make_seeds(), seed=1).build()
    assert a.to_csv(index=False) != c.to_csv(index=False)

def test_twins_share_structure(df):
    paired = df[df["pair_id"] != ""]
    for pid, grp in paired.groupby("pair_id"):
        assert len(grp) == 2
        ro = grp[grp["language"] == "ro"].iloc[0]
        en = grp[grp["language"] == "en"].iloc[0]
        assert ro["band"] == en["band"]
        assert ro["suffix"] == en["suffix"]
        assert ro["case_style"] == en["case_style"]
        if ro["category"] == "RO-phrase":
            assert len(ro["base"].split()) == len(en["base"].split())

def test_families_only_change_spelling(df):
    fams = df[df["family_id"] != ""]
    for fid, grp in fams.groupby("family_id"):
        assert grp["base"].nunique() == 1
        assert grp["spelling"].is_unique
        assert set(grp["spelling"]) <= {
            "correct", "cedilla", "ascii", "digraph",
            "pre1993", "pre1993_ascii", "decomposed"}

def test_family_spelling_counts(df):
    fams = df[df["family_id"] != ""]
    sizes = fams.groupby("family_id").size().value_counts().to_dict()
    assert sizes[5] == 80
    assert sizes[3] == 20

def test_random_is_printable_ascii(cfg, df):
    rnd = df[df["category"] == "RANDOM"]["password"]
    a, b = cfg["generator"]["random"]["length_range"]
    for pw in rnd:
        assert a <= len(pw) <= b
        assert all(0x20 <= ord(c) <= 0x7E for c in pw)

def test_clusters_group_related_rows(df):

    paired = df[df["pair_id"] != ""]
    for pid, grp in paired.groupby("pair_id"):
        assert grp["cluster_id"].nunique() == 1

    fams = df[df["family_id"] != ""]
    for fid, grp in fams.groupby("family_id"):
        assert grp["cluster_id"].nunique() == 1

def test_translit_uses_digraph(df):

    tr = df[df["category"] == "RO-translit"]["password"].str.lower()
    assert (tr.str.contains("sh") | tr.str.contains("tz")).all()

def test_write_targets_is_nfc_unique(df, tmp_path):
    out = tmp_path / "t.txt"
    write_targets(df, extra=["Extrapwd1"], path=out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(set(lines))
    assert "Extrapwd1" in lines
