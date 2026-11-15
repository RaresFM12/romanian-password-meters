import argparse
import numpy as np
import pandas as pd
from . import metrics as mx
from . import stats as st
from .breach import reuse_group
from .config import REPO_ROOT, load_config
from .normalize import nfc

SYNTH = REPO_ROOT / "data/synthetic"
METERS = REPO_ROOT / "results/meters"
PRIVATE = REPO_ROOT / "results/private"
REF = REPO_ROOT / "data/reference"
TABLES = REPO_ROOT / "results/tables"

ZX_METERS = ["M-ZX-ORIG", "M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+"]
RATE_METERS = ["M-POLICY", "M-BLOCK"] + ZX_METERS
E6_METERS = ["M-ZX-EN", "M-ZX-RO-PKG", "RO-PKG+norm", "M-ZX-RO-CZ", "M-ZX-RO+"]
SPELLINGS = ["cedilla", "ascii", "digraph", "pre1993", "pre1993_ascii", "decomposed"]

WEAK = 1e6
BOOT = 10000
BOOT_CI = 1000
MIN_WEAK = 100
THRESHOLDS = mx.DEFAULT_THRESHOLDS
TWIN_PAIRS = [("RO-word-num", "EN-word-num"), ("RO-name-num", "EN-name-num"),
              ("RO-phrase", "EN-phrase")]
TOP_LEVEL = 4
MAX_NAN_SHARE = 0.05

HYPOTHESIS_TESTS = {"H1": ["T1"], "H2a": ["T2"], "H2b": ["T3", "T4"], "H3a": ["T5"],
                    "H3b": ["T6", "T7"], "H3c": ["T8"], "H5a": ["T9", "T10", "T11"],
                    "H5b": ["T12"]}


def setup(cfg, budget=None):
    global WEAK, BOOT, BOOT_CI, MIN_WEAK, THRESHOLDS, TWIN_PAIRS, TOP_LEVEL
    WEAK = float(cfg["scoring"]["weak_threshold"])
    BOOT = int(cfg["stats"]["bootstrap_resamples"])
    BOOT_CI = int(cfg["stats"].get("bootstrap_resamples_ci", 1000))
    MIN_WEAK = int(cfg["scoring"]["min_weak_for_test"])
    THRESHOLDS = tuple(float(t) for t in cfg["scoring"]["score_thresholds"])
    TWIN_PAIRS = [tuple(p) for p in cfg["twins"]]
    if budget is None:
        budget = cfg["reference"]["run_budget"]
    # below 1e10 an unfound password may be level 3, so levels 3 and 4 are merged
    TOP_LEVEL = 4 if budget >= THRESHOLDS[3] else 3


def read_reference(path):
    ref = pd.read_csv(path, dtype={"password": str, "min_attacker": str},
                      keep_default_na=False)
    ref["g_star"] = pd.to_numeric(ref["g_star"], errors="coerce")
    ref["censored"] = ref["censored"].astype(str).str.lower() == "true"
    return ref


def attach_meters(df, reference, meter_dir):
    df = df.copy()
    df["nfc"] = df["password"].map(nfc)
    ref = reference.rename(columns={"password": "nfc"})[["nfc", "g_star", "censored"]]
    merged = df.merge(ref, on="nfc", how="left")
    if merged["censored"].isna().any():
        n = int(merged["censored"].isna().sum())
        raise ValueError(str(n) + " passwords are not in the reference; "
                         "rebuild targets_all.txt and rerun the attackers")
    merged["censored"] = merged["censored"].astype(bool)
    for path in sorted(meter_dir.glob("*.parquet")):
        meter = path.stem
        cols = pd.read_parquet(path)
        check = df[["id", "nfc"]].merge(cols[["id", "nfc"]], on="id", how="left",
                                        suffixes=("", "_meter"))
        if (check["nfc"] != check["nfc_meter"]).any():
            raise ValueError(meter + ": meter results do not match the passwords; rerun the meters")
        if cols["score"].isna().any():
            raise ValueError(meter + ": missing scores")
        keep = [c for c in ("id", "score", "guesses", "product_term") if c in cols.columns]
        m = cols[keep].rename(columns={
            "score": meter + "__score", "guesses": meter + "__guesses",
            "product_term": meter + "__pt"})
        merged = merged.merge(m, on="id", how="left")
    return merged


def load_merged(seed, reference):
    df = pd.read_csv(SYNTH / ("case_seed" + str(seed) + ".csv"), dtype=str,
                     keep_default_na=False)
    df["cluster_id"] = df["cluster_id"].astype(int)
    return attach_meters(df, reference, METERS / ("seed" + str(seed)))


def has_meter(merged, meter):
    return (meter + "__score") in merged.columns


def has_guesses(merged, meter):
    col = meter + "__guesses"
    return col in merged.columns and merged[col].notna().any()


def _arrays(merged, weak_threshold=None):
    if weak_threshold is None:
        weak_threshold = WEAK
    g = merged["g_star"].to_numpy(float)
    cen = merged["censored"].to_numpy(bool)
    clusters = merged["cluster_id"].to_numpy()
    weak = mx.weak_mask(np.nan_to_num(g, nan=np.inf), cen, weak_threshold)
    return g, cen, clusters, weak


def cat_mask(merged, cats):
    if isinstance(cats, str):
        cats = [cats]
    return merged["category"].isin(cats).to_numpy()


def reference_level(merged):
    g = merged["g_star"].to_numpy(float)
    cen = merged["censored"].to_numpy(bool)
    lvl = mx.reference_level(np.nan_to_num(g, nan=np.inf), cen, THRESHOLDS)
    return np.minimum(lvl, TOP_LEVEL)


def meter_level(merged, meter):
    return np.minimum(merged[meter + "__score"].to_numpy().astype(int), TOP_LEVEL)


def rho(merged, meter, mask):
    g, cen, _, _ = _arrays(merged)
    gm = merged[meter + "__guesses"].to_numpy(float)
    idx = np.where(mask)[0]
    if len(idx) < 3:
        return np.nan
    return mx.spearman(gm[idx], g[idx], cen[idx])


def rho_boot(merged, meters, mask, b, seed):
    g, cen, clusters, _ = _arrays(merged)
    gms = [merged[m + "__guesses"].to_numpy(float) for m in meters]
    in_mask = np.asarray(mask, dtype=bool)

    def stat(rows):
        r = rows[in_mask[rows]]
        if len(r) < 5:
            return np.nan
        vals = [mx.spearman(gm[r], g[r], cen[r]) for gm in gms]
        return vals[0] if len(vals) == 1 else vals[0] - vals[1]

    return st.cluster_bootstrap(clusters, stat, b=b, seed=seed)


def nan_share(thetas):
    thetas = np.asarray(thetas, dtype=float)
    return float(np.mean(~np.isfinite(thetas))) if len(thetas) else 1.0


def ci(thetas):
    thetas = np.asarray(thetas, dtype=float)
    thetas = thetas[np.isfinite(thetas)]
    if len(thetas) < 10:
        return np.nan, np.nan
    return st.bootstrap_ci(thetas)


def p_gt0(thetas):
    thetas = np.asarray(thetas, dtype=float)
    return st.bootstrap_pvalue_gt0(thetas[np.isfinite(thetas)])


def weak_counts(merged, meter, mask, weak):
    s = merged[meter + "__score"].to_numpy()
    n = int((weak & mask).sum())
    k = int((s[weak & mask] >= 3).sum())
    return k, n


def cmh_language_gap(merged, meter):
    _, _, _, weak = _arrays(merged)
    s = merged[meter + "__score"].to_numpy()
    band = merged["band"].astype(str).to_numpy()
    cat = merged["category"].to_numpy()
    tables = []
    n_ro = 0
    n_en = 0
    for ro_cat, en_cat in TWIN_PAIRS:
        for b in np.unique(band[np.isin(cat, [ro_cat, en_cat])]):
            cells = []
            for c in (ro_cat, en_cat):
                m = (cat == c) & (band == b) & weak
                dangerous = int((s[m] >= 3).sum())
                cells.append([dangerous, int(m.sum()) - dangerous])
            n_ro += sum(cells[0])
            n_en += sum(cells[1])
            if sum(cells[0]) > 0 and sum(cells[1]) > 0:
                tables.append(cells)
    return tables, n_ro, n_en


def dor_gap(merged, meter, rows, weak):
    s = merged[meter + "__score"].to_numpy()[rows]
    cat = merged["category"].to_numpy()[rows]
    w = weak[rows]
    vals = []
    for ro_cat, en_cat in TWIN_PAIRS:
        mro = (cat == ro_cat) & w
        men = (cat == en_cat) & w
        if mro.sum() == 0 or men.sum() == 0:
            return np.nan
        vals.append((s[mro] >= 3).mean() - (s[men] >= 3).mean())
    return float(np.mean(vals))


def family_rows(merged):
    return merged[merged["family_id"].astype(str) != ""]


def spread_per_family(merged, meter, kind="score"):
    out = {}
    for fid, g in family_rows(merged).groupby("family_id"):
        if kind == "score":
            out[fid] = mx.score_spread(g[meter + "__score"].to_numpy())
        else:
            out[fid] = mx.estimate_spread(g[meter + "__guesses"].to_numpy(float))
    return out


def eta_for_spelling(merged, meter, spelling):
    etas = []
    for fid, g in family_rows(merged).groupby("family_id"):
        a = g[g["spelling"] == "ascii"]
        v = g[g["spelling"] == spelling]
        if len(a) and len(v):
            u = a.iloc[0]
            x = v.iloc[0]
            if not u["censored"] and not x["censored"]:
                etas.append(mx.eta(np.log10(x[meter + "__guesses"]), np.log10(u[meter + "__guesses"]),
                                   np.log10(x["g_star"]), np.log10(u["g_star"])))
    return np.array(etas, dtype=float)


def run_tests(merged, cfg):
    _, cen, clusters, weak = _arrays(merged)
    rows = []

    def add(test, hyp, n, estimate, lo, hi, p, method, undecided=False, extra="", thetas=None):
        share = nan_share(thetas) if thetas is not None else 0.0
        if share > MAX_NAN_SHARE:
            undecided = True
            extra = (extra + "; " if extra else "") + "failed resamples=" + str(round(share, 3))
        rows.append({"test": test, "hypothesis": hyp, "n": n, "estimate": estimate,
                     "ci_low": lo, "ci_high": hi, "p_raw": p, "method": method,
                     "undecided": undecided, "boot_nan_share": share, "extra": extra})

    if has_meter(merged, "M-ZX-EN"):
        g, _, _, _ = _arrays(merged)
        gm = merged["M-ZX-EN__guesses"].to_numpy(float)
        pair_masks = [(cat_mask(merged, en), cat_mask(merged, ro)) for ro, en in TWIN_PAIRS]

        def t1(rows_):
            vals = []
            for m_en, m_ro in pair_masks:
                re_ = rows_[m_en[rows_]]
                rr = rows_[m_ro[rows_]]
                if len(re_) < 5 or len(rr) < 5:
                    return np.nan
                vals.append(mx.spearman(gm[re_], g[re_], cen[re_])
                            - mx.spearman(gm[rr], g[rr], cen[rr]))
            return float(np.mean(vals))

        est = t1(np.arange(len(merged)))
        th = st.cluster_bootstrap(clusters, t1, b=BOOT, seed=1)
        lo, hi = ci(th)
        n = int(sum(m_en.sum() + m_ro.sum() for m_en, m_ro in pair_masks))
        add("T1", "H1", n, est, lo, hi, p_gt0(th), "cluster bootstrap", thetas=th)

    for test, hyp, meter in (("T2", "H2a", "M-ZX-EN"), ("T4", "H2b", "M-ZX-RO-PKG")):
        if not has_meter(merged, meter):
            continue
        tables, n_ro, n_en = cmh_language_gap(merged, meter)
        undecided = n_ro < MIN_WEAK or n_en < MIN_WEAK
        p = np.nan
        est = np.nan
        if tables:
            res = st.cmh_test(tables)
            p = res["p_one_sided_greater"]
            est = res["oddsratio_pooled"]
        add(test, hyp, n_ro + n_en, est, np.nan, np.nan, p, "CMH (pair x band)",
            undecided, "weak RO=" + str(n_ro) + ", weak EN=" + str(n_en))

    if has_meter(merged, "M-ZX-EN") and has_meter(merged, "M-ZX-RO-PKG"):
        def t3(rows_):
            return dor_gap(merged, "M-ZX-EN", rows_, weak) - dor_gap(merged, "M-ZX-RO-PKG", rows_, weak)

        est = t3(np.arange(len(merged)))
        th = st.cluster_bootstrap(clusters, t3, b=BOOT, seed=3)
        lo, hi = ci(th)
        n_min = min(int((cat_mask(merged, c) & weak).sum()) for pair in TWIN_PAIRS for c in pair)
        add("T3", "H2b", int(sum((cat_mask(merged, list(p)) & weak).sum() for p in TWIN_PAIRS)),
            est, lo, hi, p_gt0(th), "cluster bootstrap", n_min < MIN_WEAK,
            "smallest weak group=" + str(n_min), thetas=th)

    for test, hyp, base, cats in (("T5", "H3a", "M-ZX-RO-PKG", cfg["open_class"]),
                                  ("T8", "H3c", "M-ZX-RO-CZ", ["RO-translit", "RO-inflected"])):
        if not (has_meter(merged, "M-ZX-RO+") and has_meter(merged, base)):
            continue
        mask = cat_mask(merged, cats)
        est = rho(merged, "M-ZX-RO+", mask) - rho(merged, base, mask)
        th = rho_boot(merged, ["M-ZX-RO+", base], mask, BOOT, seed=int(test[1:]))
        lo, hi = ci(th)
        add(test, hyp, int(mask.sum()), est, lo, hi, p_gt0(th), "cluster bootstrap", thetas=th)

    ro_plus = has_meter(merged, "M-ZX-RO+") and has_meter(merged, "M-ZX-RO-PKG")

    if ro_plus:
        ref_lvl = reference_level(merged)
        en_mask = cat_mask(merged, [en for _, en in TWIN_PAIRS])
        a = np.abs(meter_level(merged, "M-ZX-RO-PKG") - ref_lvl)
        b = np.abs(meter_level(merged, "M-ZX-RO+") - ref_lvl)
        k = int(((b > a) & en_mask).sum())
        n = int(en_mask.sum())
        # exact test with n = number of clusters (conservative)
        n_units = int(len(np.unique(clusters[en_mask])))
        lo, hi = st.clopper_pearson(k, n)
        add("T6", "H3b", n, k / n, lo, hi, st.binom_test(k, n_units, 0.01, alternative="less"),
            "exact binomial on clusters (H1: share < 0.01)",
            extra=str(k) + " moved; " + str(n_units) + " clusters")

    if ro_plus:
        rnd = cat_mask(merged, "RANDOM")
        lower = merged["M-ZX-RO+__score"].to_numpy() < merged["M-ZX-RO-PKG__score"].to_numpy()
        k = int((lower & rnd).sum())
        n = int(rnd.sum())
        lo, hi = st.wilson_interval(k, n)
        add("T7", "H3b", n, k / n, lo, hi, st.binom_test(k, n, 0.01, alternative="less"),
            "exact binomial (H1: rate < 0.01)", extra=str(k) + "/" + str(n) + " lowered")

    if has_meter(merged, "M-ZX-RO-PKG"):
        spreads = spread_per_family(merged, "M-ZX-RO-PKG", "score")
        n = len(spreads)
        k = sum(1 for v in spreads.values() if v > 0)
        if n:
            lo, hi = st.wilson_interval(k, n)
            add("T9", "H5a", n, k / n, lo, hi, st.binom_test(k, n, 0.10, alternative="greater"),
                "exact binomial (H1: rate > 0.10)", extra=str(k) + "/" + str(n) + " inconsistent")

    for test, spelling in (("T10", "digraph"), ("T11", "pre1993_ascii")):
        if has_meter(merged, "M-ZX-RO-PKG"):
            etas = eta_for_spelling(merged, "M-ZX-RO-PKG", spelling)
            if len(etas):
                add(test, "H5a", len(etas), float(np.median(etas)), np.nan, np.nan,
                    st.wilcoxon_greater(etas), "Wilcoxon signed-rank (median shown)")

    if has_meter(merged, "RO-PKG+norm") and has_meter(merged, "M-ZX-RO-PKG"):
        sp_pkg = spread_per_family(merged, "M-ZX-RO-PKG", "estimate")
        sp_norm = spread_per_family(merged, "RO-PKG+norm", "estimate")
        fam_ids = sorted(sp_pkg)
        pkg_vals = np.array([sp_pkg[f] for f in fam_ids])
        norm_vals = np.array([sp_norm[f] for f in fam_ids])
        est = 0.5 * pkg_vals.mean() - norm_vals.mean()
        rng = np.random.default_rng(12)
        th = np.empty(BOOT)
        for i in range(BOOT):
            idx = rng.integers(0, len(fam_ids), len(fam_ids))
            th[i] = 0.5 * pkg_vals[idx].mean() - norm_vals[idx].mean()
        lo, hi = ci(th)
        add("T12", "H5b", len(fam_ids), float(est), lo, hi, p_gt0(th), "bootstrap over families",
            thetas=th)

    tests = pd.DataFrame(rows)
    if len(tests) == 0:
        return tests
    tests = tests.sort_values("test", key=lambda c: c.str[1:].astype(int)).reset_index(drop=True)
    # Holm over all 12 tests; an undecided test keeps its place with p = 1
    p_for_holm = []
    for _, r in tests.iterrows():
        if r["undecided"] or pd.isna(r["p_raw"]):
            p_for_holm.append(1.0)
        else:
            p_for_holm.append(float(r["p_raw"]))
    p_for_holm += [1.0] * (12 - len(p_for_holm))
    holm = st.holm(p_for_holm, alpha=cfg["stats"]["holm_alpha"])
    tests["p_holm"] = holm["p_corrected"][:len(tests)]
    tests["reject"] = holm["reject"][:len(tests)]
    decisions = []
    for _, r in tests.iterrows():
        if r["undecided"] or pd.isna(r["p_raw"]):
            decisions.append("undecided")
        elif r["reject"]:
            decisions.append("pass")
        else:
            decisions.append("fail")
    tests["decision"] = decisions
    tests["label"] = cfg["stats"]["tests_are"]
    return tests


def hypothesis_table(tests):
    decision = dict(zip(tests["test"], tests["decision"]))
    rows = []
    for hyp, needed in HYPOTHESIS_TESTS.items():
        d = [decision.get(t, "missing") for t in needed]
        if all(x == "pass" for x in d):
            verdict = "supported"
        elif "fail" in d:
            verdict = "not supported"
        else:
            verdict = "undecided"
        rows.append({"hypothesis": hyp, "tests": " ".join(needed),
                     "decisions": " ".join(d), "verdict": verdict})
    return pd.DataFrame(rows)


def groups_of(merged, cfg):
    groups = {"all": np.ones(len(merged), bool),
              "open_class": cat_mask(merged, cfg["open_class"]),
              "ro_twins": cat_mask(merged, [ro for ro, _ in TWIN_PAIRS]),
              "en_twins": cat_mask(merged, [en for _, en in TWIN_PAIRS])}
    for cat in sorted(merged["category"].unique()):
        groups[cat] = cat_mask(merged, cat)
    return groups


def accuracy_table(merged, cfg, weak_threshold=None):
    g, cen, _, weak = _arrays(merged, weak_threshold)
    groups = groups_of(merged, cfg)
    ci_groups = {"all", "open_class", "ro_twins", "en_twins"}
    rows = []
    for meter in [m for m in RATE_METERS if has_meter(merged, m)]:
        scores = merged[meter + "__score"].to_numpy()
        for gname, mask in groups.items():
            k_dor, n_weak = weak_counts(merged, meter, mask, weak)
            nf = mask & cen
            n_nf = int(nf.sum())
            k_sur = int((scores[nf] <= 1).sum())
            row = {"meter": meter, "group": gname, "n": int(mask.sum()),
                   "n_weak": n_weak, "n_not_found": n_nf,
                   "spearman": np.nan, "spearman_lo": np.nan, "spearman_hi": np.nan,
                   "kendall": np.nan,
                   "dor": k_dor / n_weak if n_weak else np.nan, "dor_lo": np.nan, "dor_hi": np.nan,
                   "sur": k_sur / n_nf if n_nf else np.nan, "sur_lo": np.nan, "sur_hi": np.nan,
                   "male": np.nan, "male_signed": np.nan}
            if has_guesses(merged, meter) and mask.sum() > 2:
                gm = merged[meter + "__guesses"].to_numpy(float)
                row["spearman"] = mx.spearman(gm[mask], g[mask], cen[mask])
                row["kendall"] = mx.kendall(gm[mask], g[mask], cen[mask])
                found = mask & (~cen)
                if found.sum() > 0:
                    err = mx.log_error(gm[found], g[found], np.ones(int(found.sum()), bool))
                    row["male"] = err["mean_abs"]
                    row["male_signed"] = err["mean_signed"]
                if gname in ci_groups:
                    th = rho_boot(merged, [meter], mask, BOOT_CI, seed=0)
                    row["spearman_lo"], row["spearman_hi"] = ci(th)
            if n_weak:
                row["dor_lo"], row["dor_hi"] = st.wilson_interval(k_dor, n_weak)
            if n_nf:
                row["sur_lo"], row["sur_hi"] = st.wilson_interval(k_sur, n_nf)
            rows.append(row)
    return pd.DataFrame(rows)


def dor_by_category(merged):
    _, _, _, weak = _arrays(merged)
    rows = []
    for meter in [m for m in RATE_METERS if has_meter(merged, m)]:
        for cat in sorted(merged["category"].unique()):
            k, n = weak_counts(merged, meter, cat_mask(merged, cat), weak)
            lo, hi = st.wilson_interval(k, n) if n else (np.nan, np.nan)
            rows.append({"meter": meter, "category": cat, "n_weak": n,
                         "dor": k / n if n else np.nan, "dor_lo": lo, "dor_hi": hi})
    return pd.DataFrame(rows)


def twin_table(merged):
    _, _, _, weak = _arrays(merged)
    rows = []
    for meter in [m for m in ZX_METERS if has_meter(merged, m)]:
        for ro_cat, en_cat in TWIN_PAIRS:
            k_ro, n_ro = weak_counts(merged, meter, cat_mask(merged, ro_cat), weak)
            k_en, n_en = weak_counts(merged, meter, cat_mask(merged, en_cat), weak)
            r_ro = rho(merged, meter, cat_mask(merged, ro_cat))
            r_en = rho(merged, meter, cat_mask(merged, en_cat))
            rows.append({"meter": meter, "pair": ro_cat + " / " + en_cat,
                         "rho_ro": r_ro, "rho_en": r_en, "delta_rho": r_en - r_ro,
                         "n_weak_ro": n_ro, "n_weak_en": n_en,
                         "dor_ro": k_ro / n_ro if n_ro else np.nan,
                         "dor_en": k_en / n_en if n_en else np.nan})
    out = pd.DataFrame(rows)
    out["dor_gap"] = out["dor_ro"] - out["dor_en"]
    return out


def floor_attribution(merged, meters=None, weak_threshold=None):
    _, _, _, weak = _arrays(merged, weak_threshold)
    if meters is None:
        meters = [m for m in ZX_METERS if has_meter(merged, m)]
    rows = []
    for meter in meters:
        scores = merged[meter + "__score"].to_numpy()
        pt = merged[meter + "__pt"].to_numpy(float)
        dangerous = weak & (scores >= 3)
        cause = mx.floor_attribution(pt, THRESHOLDS)
        for cat in sorted(merged["category"].unique()):
            m = dangerous & cat_mask(merged, cat)
            if m.sum() == 0:
                continue
            rows.append({"meter": meter, "category": cat, "dangerous": int(m.sum()),
                         "floor": int((cause[m] == "floor").sum()),
                         "knowledge": int((cause[m] == "knowledge").sum())})
    return pd.DataFrame(rows, columns=["meter", "category", "dangerous", "floor", "knowledge"])


def spelling_consistency(merged, meter):
    rows = []
    for fid, g in family_rows(merged).groupby("family_id"):
        rows.append({"family_id": fid,
                     "delta_score": mx.score_spread(g[meter + "__score"].to_numpy()),
                     "delta_log": mx.estimate_spread(g[meter + "__guesses"].to_numpy(float))})
    return pd.DataFrame(rows)


def spelling_table(merged):
    fam = family_rows(merged)
    rows = []
    for meter in [m for m in E6_METERS if has_meter(merged, m)]:
        spreads_s = spread_per_family(merged, meter, "score")
        spreads_x = spread_per_family(merged, meter, "estimate")
        rows.append({"meter": meter, "spelling": "family", "n": len(spreads_s),
                     "score_changed": np.mean([v > 0 for v in spreads_s.values()]),
                     "mean_abs_dlog": np.mean(list(spreads_x.values())),
                     "eta_median": np.nan, "eta_n": 0})
        correct = fam[fam["spelling"] == "correct"].set_index("family_id")
        for sp in SPELLINGS:
            v = fam[fam["spelling"] == sp].set_index("family_id")
            if len(v) == 0:
                continue
            c = correct.loc[v.index]
            ds = v[meter + "__score"].to_numpy() != c[meter + "__score"].to_numpy()
            dlog = np.log10(v[meter + "__guesses"].to_numpy(float)) - \
                np.log10(c[meter + "__guesses"].to_numpy(float))
            etas = eta_for_spelling(merged, meter, sp) if sp != "ascii" else np.array([])
            rows.append({"meter": meter, "spelling": sp, "n": len(v),
                         "score_changed": float(ds.mean()),
                         "mean_abs_dlog": float(np.abs(dlog).mean()),
                         "eta_median": float(np.median(etas)) if len(etas) else np.nan,
                         "eta_n": len(etas)})
    return pd.DataFrame(rows)


def confusion_tables(merged, cfg):
    mask = cat_mask(merged, cfg["open_class"])
    ref = reference_level(merged)[mask]
    frames = []
    for meter in ["M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+"]:
        if not has_meter(merged, meter):
            continue
        cm = mx.confusion_matrix(meter_level(merged, meter)[mask], ref)
        df = pd.DataFrame(cm, columns=["ref" + str(j) for j in range(5)])
        df.insert(0, "meter_score", range(5))
        df.insert(0, "meter", meter)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def reclassification_table(merged):
    ref = reference_level(merged)
    rows = []
    for ma, mb in (("M-ZX-RO-PKG", "M-ZX-RO+"), ("M-ZX-RO-CZ", "M-ZX-RO+"),
                   ("M-ZX-RO-PKG", "M-ZX-RO-CZ")):
        if not (has_meter(merged, ma) and has_meter(merged, mb)):
            continue
        for cat in ["all"] + sorted(merged["category"].unique()):
            mask = np.ones(len(merged), bool) if cat == "all" else cat_mask(merged, cat)
            rc = mx.reclassification(meter_level(merged, ma)[mask],
                                     meter_level(merged, mb)[mask], ref[mask])
            rows.append({"group": cat, "from": ma, "to": mb, "n": int(mask.sum()), **rc})
    return pd.DataFrame(rows)


def pipeline_sanity(merged):
    rows = []
    for _, en_cat in TWIN_PAIRS:
        r = rho(merged, "M-ZX-EN", cat_mask(merged, en_cat)) if has_meter(merged, "M-ZX-EN") else np.nan
        rows.append({"check": "M-ZX-EN rho >= 0.5 on " + en_cat, "value": r,
                     "passed": bool(np.isfinite(r) and r >= 0.5)})
    return pd.DataFrame(rows)


def ablation_table(merged, cfg):
    open_mask = cat_mask(merged, cfg["open_class"])
    _, _, _, weak = _arrays(merged)
    rows = []
    for meter in sorted(c[:-len("__guesses")] for c in merged.columns
                        if c.endswith("__guesses") and c[:2] in ("A+", "A-")):
        start = "M-ZX-RO-PKG" if meter.startswith("A+") else "M-ZX-RO+"
        if not has_meter(merged, start):
            continue
        d_rho = rho(merged, meter, open_mask) - rho(merged, start, open_mask)
        lo, hi = ci(rho_boot(merged, [meter, start], open_mask, BOOT_CI, seed=5))
        k1, n1 = weak_counts(merged, meter, open_mask, weak)
        k0, n0 = weak_counts(merged, start, open_mask, weak)
        rows.append({"meter": meter, "group": meter[2:],
                     "kind": "add to RO-PKG" if meter.startswith("A+") else "remove from RO+",
                     "rho_open": rho(merged, meter, open_mask), "delta_rho": d_rho,
                     "delta_rho_lo": lo, "delta_rho_hi": hi,
                     "dor_open": k1 / n1 if n1 else np.nan,
                     "delta_dor": (k1 / n1 - k0 / n0) if n1 else np.nan})
    return pd.DataFrame(rows)


def d_sweep_table(merged, cfg):
    _, cen, _, weak = _arrays(merged)
    meters = [m for m in ("M-ZX-RO+", "M-ZX-RO-CZ") if has_meter(merged, m)]
    meters += sorted(c[:-len("__score")] for c in merged.columns
                     if c.endswith("__score") and "-D" in c and c.startswith("M-ZX"))
    rows = []
    for meter in meters:
        s = merged[meter + "__score"].to_numpy()
        for gname, mask in (("all", np.ones(len(merged), bool)),
                            ("open_class", cat_mask(merged, cfg["open_class"]))):
            rows.append({"meter": meter, "group": gname,
                         "rho": rho(merged, meter, mask),
                         "dor": mx.dor(s[mask], weak[mask]), "sur": mx.sur(s[mask], cen[mask])})
    return pd.DataFrame(rows)


def misjudged_structures(merged, gn, top=20):
    ref = reference_level(merged)
    df = merged[merged["category"] != "RANDOM"].copy()
    df["ref_level"] = ref[merged["category"].to_numpy() != "RANDOM"]
    suffix = df["suffix"].astype(str)
    kind = np.where(suffix == "", "none",
                    np.where(suffix.str.fullmatch(r"(19[5-9]\d|20[0-2]\d)\W?"), "year",
                             np.where(suffix.str.fullmatch(r"\d+"), "digits", "digits+symbol")))
    df["structure"] = df["category"] + " | " + df["spelling"] + " | " + df["case_style"] + " | " + kind
    df["error"] = np.abs(np.minimum(df["M-ZX-RO-PKG__score"], TOP_LEVEL) - df["ref_level"])
    a_ro = gn[(gn["attacker"] == "A-RO") & (gn["run"] == "full")].set_index("password")["guess_number"]
    rows = []
    for s, g in df.groupby("structure"):
        if len(g) < 3:
            continue
        ex = g.iloc[0]
        row = {"structure": s, "n": len(g), "mean_error": g["error"].mean(),
               "example": ex["password"], "ref_level": int(ex["ref_level"]),
               "a_ro_guess_number": a_ro.get(ex["nfc"], np.nan)}
        for m in RATE_METERS:
            if has_meter(merged, m):
                row[m] = int(ex[m + "__score"])
        rows.append(row)
    out = pd.DataFrame(rows).sort_values(["mean_error", "n"], ascending=False)
    return out.head(top)


def guessing_curves(merged, gn, budget=1e10):
    df = merged[merged["category"] != "RO-diacritic"]
    groups = {"Romanian": df["language"] == "ro", "English": df["language"] == "en",
              "RANDOM": df["language"] == "random"}
    full = gn[gn["run"] == "full"]
    curves = {"A-MIN": None}
    for a in sorted(full["attacker"].unique()):
        curves[a] = full[full["attacker"] == a].set_index("password")["guess_number"]
    rows = []
    for name, series in curves.items():
        for gname, gmask in groups.items():
            if series is None:
                vals = df.loc[gmask.to_numpy(), "g_star"].to_numpy(float)
            else:
                vals = series.reindex(df.loc[gmask.to_numpy(), "nfc"]).to_numpy(float)
            # the curves stop at the attack budget
            for x in np.arange(0, np.log10(budget) + 0.01, 0.25):
                rows.append({"attacker": name, "group": gname, "log10_guesses": x,
                             "n": len(vals), "cracked": float(np.mean(vals <= 10 ** x))})
    return pd.DataFrame(rows)


def real_tables(reference, cfg):
    path = PRIVATE / "real_sample.csv"
    if not path.exists():
        return None, None, None
    df = pd.read_csv(path, dtype={"password": str, "id": str}, keep_default_na=False)
    df["count"] = df["count"].astype(int)
    df["total"] = df["total"].astype(int)
    df["category"] = "REAL"
    df["cluster_id"] = np.arange(len(df))
    merged = attach_meters(df, reference, PRIVATE / "meters_real")
    merged["reuse"] = merged["total"].map(reuse_group)
    g, cen, _, weak = _arrays(merged)
    w = merged["count"].to_numpy(float)
    rows = []
    for meter in [m for m in RATE_METERS if has_meter(merged, m)]:
        for grp in ["all"] + sorted(merged["reuse"].unique()):
            mask = np.ones(len(merged), bool) if grp == "all" else (merged["reuse"] == grp).to_numpy()
            k, n = weak_counts(merged, meter, mask, weak)
            row = {"meter": meter, "reuse_group": grp, "n": int(mask.sum()),
                   "occurrences": int(w[mask].sum()), "n_weak": n,
                   "dor": k / n if n else np.nan, "dor_lo": np.nan, "dor_hi": np.nan,
                   "weighted_spearman": np.nan}
            if n:
                row["dor_lo"], row["dor_hi"] = st.wilson_interval(k, n)
            if has_guesses(merged, meter) and mask.sum() > 2:
                gm = merged[meter + "__guesses"].to_numpy(float)
                row["weighted_spearman"] = mx.weighted_spearman(gm[mask], g[mask], w[mask], cen[mask])
            rows.append(row)
    dist = []
    for meter in [m for m in RATE_METERS if has_meter(merged, m)]:
        s = merged[meter + "__score"].to_numpy()
        for grp in ["all"] + sorted(merged["reuse"].unique()):
            mask = np.ones(len(merged), bool) if grp == "all" else (merged["reuse"] == grp).to_numpy()
            row = {"meter": meter, "reuse_group": grp, "n": int(mask.sum())}
            for k in range(5):
                row["score" + str(k)] = float(np.mean(s[mask] == k)) if mask.sum() else np.nan
            dist.append(row)
    uniq = (merged["total"] == 1).to_numpy()
    not_found = uniq & ~((~cen) & (np.nan_to_num(g, nan=np.inf) <= 1e8))
    k, n = int(not_found.sum()), int(uniq.sum())
    lo, hi = st.wilson_interval(k, n) if n else (np.nan, np.nan)
    claim = pd.DataFrame([{"n_unique": n, "not_found_1e8": k, "share": k / n if n else np.nan,
                           "ci_low": lo, "ci_high": hi, "passes": bool(lo > 0.10)}])
    return pd.DataFrame(rows), claim, pd.DataFrame(dist)


def precision_table():
    path = PRIVATE / "precision_sample.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    labels = df["is_romanian"].str.strip().str.lower()
    done = labels.isin(["1", "0", "yes", "no", "y", "n", "true", "false"])
    k = int(labels[done].isin(["1", "yes", "y", "true"]).sum())
    n = int(done.sum())
    lo, hi = st.wilson_interval(k, n) if n else (np.nan, np.nan)
    return pd.DataFrame([{"labelled": n, "of": len(df), "romanian": k,
                          "precision": k / n if n else np.nan, "ci_low": lo, "ci_high": hi}])


def checks_passed():
    path = TABLES / "reference_checks.csv"
    if not path.exists():
        return False
    checks = pd.read_csv(path)
    return bool(checks["passed"].astype(str).str.lower().eq("true").all())


def run(config, force=False):
    cfg = load_config(config)
    setup(cfg)
    gstar = REF / "reference_gstar.csv"
    if not gstar.exists():
        print("no reference_gstar.csv; run reference-check first")
        return False
    if not checks_passed() and not force:
        print("the reference checks failed (results/tables/reference_checks.csv);"
              " fix the reference or run with --force for an exploratory analysis")
        return False
    reference = read_reference(gstar)
    merged = load_merged(cfg["seeds"]["main"], reference)
    gn = pd.read_csv(REF / "guess_numbers.csv", dtype={"password": str}, keep_default_na=False)
    gn["guess_number"] = pd.to_numeric(gn["guess_number"], errors="coerce")
    TABLES.mkdir(parents=True, exist_ok=True)

    tables = {
        "accuracy": accuracy_table(merged, cfg),
        "dor_by_category": dor_by_category(merged),
        "twins": twin_table(merged),
        "floor_attribution": floor_attribution(merged),
        "spelling": spelling_table(merged),
        "spelling_consistency": spelling_consistency(merged, "M-ZX-RO-PKG"),
        "confusion": confusion_tables(merged, cfg),
        "reclassification": reclassification_table(merged),
        "pipeline_sanity": pipeline_sanity(merged),
        "ablation": ablation_table(merged, cfg),
        "d_sweep": d_sweep_table(merged, cfg),
        "misjudged_structures": misjudged_structures(merged, gn),
        "guessing_curves": guessing_curves(merged, gn, cfg["reference"]["run_budget"]),
    }
    tests = run_tests(merged, cfg)
    tables["main_tests"] = tests
    tables["hypotheses"] = hypothesis_table(tests)
    precision = precision_table()
    if precision is not None:
        tables["real_precision"] = precision
        if precision.loc[0, "labelled"] < precision.loc[0, "of"]:
            print("note: the precision sample is not fully labelled yet ("
                  + str(precision.loc[0, "labelled"]) + "/" + str(precision.loc[0, "of"]) + ")")
    real, claim, dist = real_tables(reference, cfg)
    if real is not None:
        tables["real_accuracy"] = real
        tables["real_frequency_claim"] = claim
        tables["real_score_distribution"] = dist
    for name, df in tables.items():
        df.to_csv(TABLES / (name + ".csv"), index=False)
    if not tables["pipeline_sanity"]["passed"].all():
        print("WARNING: the pipeline sanity check (design 7.2) failed;"
              " see results/tables/pipeline_sanity.csv before using the results")
    if TOP_LEVEL == 3:
        print("note: attack budget below 1e10, reference levels 3 and 4 are merged")
    print(tests[["test", "hypothesis", "n", "estimate", "p_raw", "p_holm", "decision"]].to_string(index=False))
    print(tables["hypotheses"].to_string(index=False))
    print("wrote", ", ".join(tables))
    return True


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    ap.add_argument("--force", action="store_true",
                    help="analyse even when a reference check failed (exploratory only)")
    args = ap.parse_args()
    raise SystemExit(0 if run(args.config, args.force) else 1)


if __name__ == "__main__":
    _main()
