from ropw import guess_numbers as gn


def test_parse_found_keeps_first(tmp_path):
    p = tmp_path / "x.found"
    p.write_text("5:abc\n9:xyz\n7:abc\n", encoding="utf-8")
    found = gn.parse_found(p)
    assert found["abc"] == 5
    assert found["xyz"] == 9


def test_assemble_marks_censored(tmp_path, monkeypatch):
    targets = tmp_path / "targets.txt"
    targets.write_text("abc\nxyz\nqqq\n", encoding="utf-8")
    monkeypatch.setattr(gn, "TARGETS", targets)
    found = tmp_path / "a.found"
    found.write_text("3:abc\n50:xyz\n", encoding="utf-8")
    out = tmp_path / "gn.csv"
    n = gn.assemble([{"attacker": "A-RO", "run": "full", "budget": 1000, "found": str(found)}],
                    out_path=out)
    import csv
    rows = {r["password"]: r for r in csv.DictReader(open(out))}
    assert n == 3
    assert rows["abc"]["guess_number"] == "3" and rows["abc"]["censored"] == "False"
    assert rows["qqq"]["guess_number"] == "" and rows["qqq"]["censored"] == "True"
