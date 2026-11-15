from ropw.export_wordlists import phrase_forms, ro_variants


def test_variants_start_with_the_word_and_are_ordered():
    v = ro_variants("fetiță")
    assert v[0] == "fetiță"
    assert v == ro_variants("fetiță")
    assert v[:4] == ["fetiță", "fetita", "fetiţă", "fetitza"]
    assert "Fetiță" in v and "FETIȚĂ" in v


def test_phrase_forms_include_no_space_form():
    assert "teiubesc" in phrase_forms("te iubesc")


def test_english_phrases_get_a_no_space_form(tmp_path, monkeypatch):
    from ropw import export_wordlists as ew
    gen = tmp_path / "gen"
    gen.mkdir()
    for name, items in {"en_phrases": ["of the"], "ro_phrases": ["te iubesc"],
                        "ro_words": ["casă"], "en_words": ["house"]}.items():
        (gen / (name + ".tsv")).write_text("item\trank\tfreq\n" + "".join(
            i + "\t1\t1\n" for i in items), encoding="utf-8")
    breach = tmp_path / "breach"
    breach.mkdir()
    (breach / "rockyou_attacker.txt").write_text("123456\n", encoding="utf-8")
    (breach / "ro_attacker_share.txt").write_text("", encoding="utf-8")
    monkeypatch.setattr(ew, "GEN", gen)
    monkeypatch.setattr(ew, "BREACH", breach)
    monkeypatch.setattr(ew, "OUT", tmp_path / "out")
    monkeypatch.setattr(ew, "REPO_ROOT", tmp_path)
    (tmp_path / "data/reference").mkdir(parents=True)
    ew.build()
    en = (tmp_path / "out/en.txt").read_text(encoding="utf-8").split("\n")
    assert "ofthe" in en and "of the" in en
    assert en.index("house") < en.index("123456")
    allw = (tmp_path / "out/all.txt").read_text(encoding="utf-8").split("\n")
    assert allw.index("casă") < allw.index("123456")
    ro = (tmp_path / "out/ro.txt").read_text(encoding="utf-8").split("\n")
    novar = (tmp_path / "out/ro_novar.txt").read_text(encoding="utf-8").split("\n")
    assert "casa" in ro and "casă" in novar and "casa" not in novar
