import pytest

from ropw.config import REPO_ROOT
from ropw.meters.block import EXPECTED_COUNT, Block
from ropw.meters.policy import char_classes, policy_score

BLOCKLIST = REPO_ROOT / "data/lexicon/meter/common.txt"

def test_policy_normal():
    assert policy_score("Andrei1999!") == 4
    assert policy_score("Parola12") == 4
    assert policy_score("parola12") == 0
    assert policy_score("Ab1!") == 0
    assert policy_score("parolaparola") == 0

def test_policy_strict():
    assert policy_score("Andrei1999!xy", strict=True) == 4
    assert policy_score("Andrei1999!", strict=True) == 0
    assert policy_score("Abcdefgh1234", strict=True) == 0

def test_length_counts_nfc_codepoints():

    assert policy_score("fetiță!1A") == 4

    assert policy_score("fetiță!1A") == 4

def test_diacritic_letter_counts_by_case():
    assert char_classes("Ăă") == {"upper", "lower"}
    assert char_classes("ș") == {"lower"}
    assert char_classes("Ț") == {"upper"}

@pytest.mark.skipif(not BLOCKLIST.exists(),
                    reason="blocklist not exported (run bridge/export_common.mjs)")
def test_block_count_and_scores():
    b = Block()
    assert len(b.blocklist) == EXPECTED_COUNT
    assert b.score("password") == 0
    assert b.score("123456") == 0
    assert b.score("Password") == 0
    assert b.score("VacantaLaMare1!") == 4

def test_block_count_guard(tmp_path):
    short = tmp_path / "x.txt"
    short.write_text("password\n123456\n", encoding="utf-8")
    with pytest.raises(ValueError):
        Block(short)
    b = Block(short, check_count=False)
    assert b.score("password") == 0 and b.score("unique-xyz") == 4
