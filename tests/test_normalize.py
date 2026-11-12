"""C03: normalisation reproduces Table 4 of the design exactly."""
from ropw import normalize as nz


def test_fetita_family():
    w = "fetiță"
    assert nz.to_cedilla(w) == "fetiţă"
    assert nz.to_ascii(w) == "fetita"
    assert nz.to_digraph(w) == "fetitza"
    assert len(nz.nfd(w)) == 8


def test_paine_family():
    w = "pâine"
    assert nz.to_ascii(w) == "paine"
    assert nz.to_pre1993(w) == "pîine"
    assert nz.to_pre1993_ascii(w) == "piine"
    assert len(nz.nfd(w)) == 6


def test_roman_keeps_circumflex():
    assert nz.to_pre1993("român") == "român"
    assert nz.to_pre1993("românesc") == "românesc"
    assert nz.to_pre1993("România") == "România"
    # a non-family word with â still changes
    assert nz.to_pre1993("când") == "cînd"


def test_nfc_nfd_roundtrip():
    for w in ["fetiță", "pâine", "mâncând", "București", "șșțțââîî", "Ana are mere"]:
        assert nz.nfc(nz.nfd(w)) == nz.nfc(w)


def test_fold_preserves_length_and_indices():
    for w in ["fetiță", "pâine", "Șișești", "ȚĂRĂ", "mânând", "abc123!"]:
        folded = nz.fold(w)
        assert len(folded) == len(nz.nfc(w)), w
        assert folded.isascii(), w


def test_fold_merges_both_encodings():
    assert nz.fold("fetiță") == nz.fold("fetiţă") == "fetita"


def test_export_tables(tmp_path):
    import json
    out = nz.export_tables(tmp_path / "tables.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["fold"]["ș"] == "s"
    assert data["digraph"]["ț"] == "tz"
    assert data["cedilla"]["ș"] == "ş"
