import pandas as pd

from ropw import reference as ref

def _toy():

    rows = [

        ("vacanta123", "A-EN", 5_000_000, False, 1e10, "full"),
        ("vacanta123", "A-RO", 40_000, False, 1e10, "full"),
        ("vacanta123", "A-PCFG", 900_000, False, 1e9, "full"),
        ("vacanta123", "A-RO", 40_000, False, 1e10, "small"),

        ("xQ7#pL9@", "A-EN", None, True, 1e10, "full"),
        ("xQ7#pL9@", "A-RO", None, True, 1e10, "full"),
        ("xQ7#pL9@", "A-PCFG", None, True, 1e9, "full"),
    ]
    cols = ["password", "attacker", "guess_number", "censored", "budget", "run"]
    return pd.DataFrame(rows, columns=cols)

def test_compute_reference_takes_minimum():
    r = ref.compute_reference(_toy())
    row = r[r["password"] == "vacanta123"].iloc[0]
    assert row["g_star"] == 40_000 and row["min_attacker"] == "A-RO"
    rnd = r[r["password"] == "xQ7#pL9@"].iloc[0]
    assert bool(rnd["censored"]) and pd.isna(rnd["g_star"])

def test_cut_variant_censors_above_threshold():
    r = ref.compute_reference(_toy(), cut=1e4)
    assert bool(r[r["password"] == "vacanta123"].iloc[0]["censored"])

def test_checks_pass_on_clean_reference():
    df = _toy()
    r = ref.compute_reference(df)
    checks = ref.reference_checks(df, r, None, random_passwords={"xQ7#pL9@"})
    assert checks.set_index("check").loc["random_never_found", "passed"]
    assert checks.set_index("check").loc["small_full_agree_1e8", "passed"]

def test_random_found_fails_check():
    df = _toy()
    df["censored"] = df["censored"].astype(bool)
    df.loc[df["password"] == "xQ7#pL9@", "censored"] = False
    df.loc[(df["password"] == "xQ7#pL9@") & (df["attacker"] == "A-EN"), "guess_number"] = 123
    r = ref.compute_reference(df)
    checks = ref.reference_checks(df, r, None, random_passwords={"xQ7#pL9@"})
    assert not checks.set_index("check").loc["random_never_found", "passed"]
