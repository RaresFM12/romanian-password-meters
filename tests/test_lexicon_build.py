import json

from ropw import lexicon_build as lb

def test_tuple_field_parses_mysql_values():
    s = ("(1,'aa','aa','aa',NULL,5),"
         "(3,'aaleni\\'an','aalenian','aalenian',NULL,0)")
    assert list(lb.tuple_field(s, 2)) == ["aa", "aalenian"]

def test_tuple_field_handles_commas_and_escapes():
    s = "(1,'a,b','keep\\'me',5),(2,'x','also,ok',NULL)"
    assert list(lb.tuple_field(s, 2)) == ["keep'me", "also,ok"]

def test_clean_and_is_word():
    assert lb.clean("  În‎GER ") == "înger"
    assert lb.is_word("vacanță", lb.RO_LETTERS)
    assert not lb.is_word("ab3", lb.RO_LETTERS)
    assert not lb.is_word("x", lb.RO_LETTERS)

def test_clean_title():
    assert lb._clean_title("Aurel (prenume)") == "aurel"
    assert lb._clean_title("Categorie:Ceva") == "ceva"
    assert lb._clean_title("Ștefan cel Mare") == "ștefan"

def test_inflected_heuristic():
    words = [("puiule", 10), ("casă", 5), ("fraților", 3), ("masa", 2)]
    got = {w for w, _ in lb.ro_inflected_from_words(words)}
    assert "puiule" in got and "fraților" in got
    assert "casă" not in got

def test_generator_manifest_separation():
    path = lb.GEN / "manifest.json"
    if not path.exists():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for inputs in manifest["inputs"].values():
        for p in inputs:
            assert "lexicon/meter" not in p, p
            assert "node_modules" not in p and "packages/" not in p, p
            assert p.startswith("data/raw/"), p
