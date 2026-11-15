import argparse
import numpy as np
import pandas as pd
import matplotlib
from .config import REPO_ROOT, load_config

matplotlib.use("Agg")
import matplotlib.pyplot as plt

TABLES = REPO_ROOT / "results/tables"
FIGURES = REPO_ROOT / "results/figures"
REF = REPO_ROOT / "data/reference"

METER_ORDER = ["M-POLICY", "M-BLOCK", "M-ZX-ORIG", "M-ZX-EN",
               "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+"]
METER_COLOR = {
    "M-POLICY": "#9aa0a6", "M-BLOCK": "#bdc1c6", "M-ZX-ORIG": "#8ab4f8",
    "M-ZX-EN": "#4285f4", "M-ZX-RO-PKG": "#f9ab00", "M-ZX-RO-CZ": "#e8710a",
    "M-ZX-RO+": "#34a853", "RO-PKG+norm": "#a142f4",
}
ZX_MAIN = ["M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+"]
LANG_COLOR = {"Romanian": "#4285f4", "English": "#f9ab00", "RANDOM": "#9aa0a6"}
GROUP_NAME = {"open_class": "Romanian (open class)", "ro_twins": "Romanian twins",
              "en_twins": "English twins"}
KNOWN_METERS = set(METER_ORDER) | {"RO-PKG+norm", "M-POLICY-STRICT"}


def _save(fig, number, name):
    FIGURES.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("png", "pdf"):
        p = FIGURES / ("fig" + str(number).zfill(2) + "_" + name + "." + ext)
        fig.savefig(p, bbox_inches="tight", dpi=150)
        try:
            paths.append(str(p.relative_to(REPO_ROOT)))
        except ValueError:
            paths.append(str(p))
    plt.close(fig)
    return paths


def _check(df, keys, meter_col="meter"):
    unknown = set(df[meter_col]) - KNOWN_METERS
    if unknown:
        raise ValueError("unknown meter names: " + str(unknown))
    if df.duplicated(keys).any():
        raise ValueError("duplicate rows for " + str(keys))


def _errbar(vals, lo, hi):
    vals = np.asarray(vals, float)
    low = np.clip(np.nan_to_num(vals - np.asarray(lo, float), nan=0.0), 0, None)
    high = np.clip(np.nan_to_num(np.asarray(hi, float) - vals, nan=0.0), 0, None)
    return [low, high]


def fig_scatter(merged):
    meters = [m for m in ZX_MAIN if m + "__guesses" in merged.columns]
    fig, axes = plt.subplots(1, len(meters), figsize=(3.6 * len(meters), 3.6), sharey=True)
    found = ~merged["censored"].to_numpy(bool)
    lang = merged["language"].map({"ro": "Romanian", "en": "English", "random": "RANDOM"})
    for ax, m in zip(np.atleast_1d(axes), meters):
        for name, color in LANG_COLOR.items():
            sel = found & (lang == name).to_numpy()
            ax.scatter(np.log10(merged["g_star"].to_numpy(float)[sel]),
                       np.log10(merged[m + "__guesses"].to_numpy(float)[sel]),
                       s=4, alpha=0.3, color=color, label=name + " (n=" + str(int(sel.sum())) + ")")
        ax.set_title(m)
        ax.set_xlabel("log10 reference guess number (A-MIN)")
    np.atleast_1d(axes)[0].set_ylabel("log10 meter estimate")
    np.atleast_1d(axes)[0].legend(fontsize=7, markerscale=3)
    fig.suptitle("Meter estimate against the reference (found passwords; RANDOM is never found)")
    fig.tight_layout()
    return _save(fig, 1, "scatter-estimate-reference")


def fig_spearman(acc, number=2, name="spearman-by-meter", groups=("open_class", "ro_twins", "en_twins")):
    meters = [m for m in ZX_MAIN if m in set(acc["meter"])]
    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.8 / len(meters)
    x = np.arange(len(groups))
    for i, m in enumerate(meters):
        sub = acc[acc["meter"] == m].set_index("group").reindex(list(groups))
        ax.bar(x + i * width, sub["spearman"], width, color=METER_COLOR[m], label=m,
               yerr=_errbar(sub["spearman"], sub["spearman_lo"], sub["spearman_hi"]), capsize=3)
    n = acc[acc["meter"] == meters[0]].set_index("group").reindex(list(groups))["n"]
    ax.set_xticks(x + width * (len(meters) - 1) / 2)
    ax.set_xticklabels([GROUP_NAME.get(g, g) + "\n(n=" + str(int(k)) + ")" for g, k in zip(groups, n)])
    ax.set_ylabel("Spearman rho with A-MIN")
    ax.set_ylim(min(0, float(np.nanmin(acc["spearman_lo"].to_numpy(float))) - 0.05), 1)
    ax.set_title("Rank correlation, 95% cluster-bootstrap CI")
    ax.legend(fontsize=8)
    return _save(fig, number, name)


def fig_dor(dor):
    meters = [m for m in ["M-POLICY", "M-BLOCK", "M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO-CZ", "M-ZX-RO+"]
              if m in set(dor["meter"])]
    cats = sorted(c for c in dor["category"].unique()
                  if dor[dor["category"] == c]["n_weak"].max() >= 5)
    fig, ax = plt.subplots(figsize=(11, 4.5))
    width = 0.8 / len(meters)
    x = np.arange(len(cats))
    for i, m in enumerate(meters):
        sub = dor[dor["meter"] == m].set_index("category").reindex(cats)
        ax.bar(x + i * width, sub["dor"], width, color=METER_COLOR[m], label=m,
               yerr=_errbar(sub["dor"], sub["dor_lo"], sub["dor_hi"]), capsize=2)
    n = dor[dor["meter"] == meters[0]].set_index("category").reindex(cats)["n_weak"]
    ax.set_xticks(x + width * (len(meters) - 1) / 2)
    ax.set_xticklabels([c + "\n(" + str(int(k)) + " weak)" for c, k in zip(cats, n)],
                       rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("dangerous overestimation rate")
    ax.set_ylim(0, 1)
    ax.set_title("Weak passwords (found within 1e6 guesses) rated 3 or 4, 95% Wilson CI\n"
                 "(categories with at least 5 weak passwords)")
    ax.legend(fontsize=7, ncol=3)
    return _save(fig, 3, "dor-by-category")


def fig_confusion(confusion):
    meters = [m for m in ["M-ZX-EN", "M-ZX-RO-PKG", "M-ZX-RO+"] if m in set(confusion["meter"])]
    fig, axes = plt.subplots(1, len(meters), figsize=(4 * len(meters), 3.6))
    for ax, m in zip(np.atleast_1d(axes), meters):
        cm = confusion[confusion["meter"] == m][["ref" + str(j) for j in range(5)]].to_numpy()
        # below a 1e10 budget levels 3 and 4 are merged: the last row and column are always 0
        k = 4 if cm[4, :].sum() == 0 and cm[:, 4].sum() == 0 else 5
        cm = cm[:k, :k]
        labels = [str(j) for j in range(k)]
        if k == 4:
            labels[3] = "3-4"
        ax.imshow(cm, cmap="Blues")
        ax.set_title(m + " (n=" + str(int(cm.sum())) + ")")
        ax.set_xticks(range(k), labels)
        ax.set_yticks(range(k), labels)
        ax.set_xlabel("reference level")
        ax.set_ylabel("meter score")
        for i in range(k):
            for j in range(k):
                ax.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=7)
    fig.suptitle("Score against reference level, open-class Romanian passwords")
    fig.tight_layout()
    return _save(fig, 4, "confusion-matrices")


def fig_ablation(abl):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharex=True)
    for ax, kind in zip(axes, ["add to RO-PKG", "remove from RO+"]):
        sub = abl[abl["kind"] == kind].sort_values("delta_rho")
        ax.barh(sub["group"], sub["delta_rho"], color="#34a853",
                xerr=_errbar(sub["delta_rho"], sub["delta_rho_lo"], sub["delta_rho_hi"]), capsize=3)
        ax.axvline(0, color="black", lw=0.8)
        ax.set_title(kind)
        ax.set_xlabel("change in Spearman rho, open-class Romanian")
    fig.suptitle("Resource ablation (95% paired cluster-bootstrap CI)")
    fig.tight_layout()
    return _save(fig, 5, "ablation")


def fig_misjudged(mis):
    cols = ["structure", "n", "mean_error", "example", "ref_level"] + \
        [m for m in METER_ORDER if m in mis.columns] + ["a_ro_guess_number"]
    show = mis[cols].copy()
    show["mean_error"] = show["mean_error"].round(2)
    show["a_ro_guess_number"] = show["a_ro_guess_number"].map(
        lambda v: "not found" if pd.isna(v) else format(v, ".2e"))
    header = [c.replace("M-ZX-", "").replace("M-", "") for c in cols]
    fig, ax = plt.subplots(figsize=(16, 0.24 * len(show) + 0.6))
    ax.axis("off")
    t = ax.table(cellText=show.astype(str).values, colLabels=header, loc="upper center",
                 cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(6.5)
    t.auto_set_column_width(list(range(len(cols))))
    ax.set_title("The 20 structures with the largest |M-ZX-RO-PKG score - reference level| "
                 "(scores of one example password)", fontsize=9)
    return _save(fig, 6, "misjudged-structures")


def fig_spelling(sp):
    meters = [m for m in ["M-ZX-EN", "M-ZX-RO-PKG", "RO-PKG+norm", "M-ZX-RO-CZ", "M-ZX-RO+"]
              if m in set(sp["meter"])]
    forms = [f for f in ["cedilla", "ascii", "digraph", "pre1993", "pre1993_ascii", "decomposed"]
             if f in set(sp["spelling"])]
    fig, ax = plt.subplots(figsize=(9, 4))
    width = 0.8 / len(meters)
    x = np.arange(len(forms))
    for i, m in enumerate(meters):
        sub = sp[sp["meter"] == m].set_index("spelling").reindex(forms)
        ax.bar(x + i * width, sub["score_changed"], width, color=METER_COLOR[m], label=m)
    n = sp[sp["meter"] == meters[0]].set_index("spelling").reindex(forms)["n"]
    ax.set_xticks(x + width * (len(meters) - 1) / 2)
    ax.set_xticklabels([f + "\n(n=" + str(int(k)) + ")" for f, k in zip(forms, n)])
    ax.set_ylabel("share with a different score\nthan the correct spelling")
    ax.set_ylim(0, 1)
    ax.set_title("Spelling consistency before and after normalisation")
    ax.legend(fontsize=7)
    return _save(fig, 7, "spelling-consistency")


def fig_bundle(dep, acc):
    a = acc[acc["group"] == "open_class"].set_index("meter")
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for _, r in dep.iterrows():
        m = r["meter"]
        if m in a.index and pd.notna(a.loc[m, "spearman"]):
            ax.scatter(r["bundle_kb"], a.loc[m, "spearman"], color=METER_COLOR.get(m, "#000"), s=60)
            ax.annotate(m, (r["bundle_kb"], a.loc[m, "spearman"]), fontsize=7,
                        xytext=(4, 2), textcoords="offset points")
    ax.axvline(900, color="grey", ls="--", lw=0.8)
    ax.text(905, ax.get_ylim()[0], "900 KB (Czech target)", fontsize=7, va="bottom")
    ax.set_xlabel("code and word lists of the meter (KB, gzip)")
    ax.set_ylabel("Spearman rho, open-class Romanian")
    ax.set_title("Deployment cost against accuracy")
    return _save(fig, 8, "bundle-vs-accuracy")


def fig_real(real):
    # unique passwords only: a reused password may be in the meter's leaked list by construction
    sub = real[real["reuse_group"] == "1-1"]
    zx = [m for m in ZX_MAIN if m in set(sub["meter"])]
    rate = [m for m in ["M-POLICY", "M-BLOCK"] + ZX_MAIN if m in set(sub["meter"])]
    s = sub.set_index("meter")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].bar(zx, s.loc[zx, "weighted_spearman"], color=[METER_COLOR[m] for m in zx])
    axes[0].set_ylabel("Spearman rho")
    axes[0].set_ylim(0, 1)
    axes[1].bar(rate, s.loc[rate, "dor"], color=[METER_COLOR[m] for m in rate],
                yerr=_errbar(s.loc[rate, "dor"], s.loc[rate, "dor_lo"], s.loc[rate, "dor_hi"]), capsize=3)
    axes[1].set_ylabel("dangerous overestimation rate")
    axes[1].set_ylim(0, 1)
    for ax in axes:
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.suptitle("Real passwords used by one account (validation sample, n=" + str(int(s["n"].max()))
                 + ", " + str(int(s["n_weak"].max())) + " weak)")
    fig.tight_layout()
    return _save(fig, 9, "real-passwords")


def fig_guessing_curves(curves):
    attackers = ["A-MIN"] + sorted(a for a in curves["attacker"].unique() if a != "A-MIN")
    fig, axes = plt.subplots(1, len(attackers), figsize=(3.2 * len(attackers), 3.4), sharey=True)
    for ax, a in zip(np.atleast_1d(axes), attackers):
        for g, color in LANG_COLOR.items():
            sub = curves[(curves["attacker"] == a) & (curves["group"] == g)]
            if len(sub):
                ax.plot(sub["log10_guesses"], sub["cracked"], color=color,
                        label=g + " (n=" + str(int(sub["n"].iloc[0])) + ")")
        ax.set_title(a)
        ax.set_xlabel("log10 guesses")
    np.atleast_1d(axes)[0].set_ylabel("share of passwords cracked")
    np.atleast_1d(axes)[0].legend(fontsize=7)
    fig.tight_layout()
    return _save(fig, 10, "guessing-curves")


def fig_error_attribution(floor):
    meters = [m for m in ZX_MAIN if m in set(floor["meter"])]
    if not meters:
        return []
    fig, axes = plt.subplots(1, len(meters), figsize=(3.8 * len(meters), 4), sharey=True)
    for ax, m in zip(np.atleast_1d(axes), meters):
        sub = floor[floor["meter"] == m]
        ax.bar(sub["category"], sub["floor"], color="#e8710a", label="floor")
        ax.bar(sub["category"], sub["knowledge"], bottom=sub["floor"], color="#4285f4",
               label="missing knowledge")
        ax.set_title(m + " (" + str(int(sub["dangerous"].sum())) + " errors)")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=7)
    np.atleast_1d(axes)[0].set_ylabel("dangerous overestimations")
    np.atleast_1d(axes)[0].legend(fontsize=7)
    fig.tight_layout()
    return _save(fig, 11, "error-attribution")


def _table(name):
    p = TABLES / (name + ".csv")
    if not p.exists():
        return None
    df = pd.read_csv(p, keep_default_na=True)
    return df if len(df) else None


def run(config):
    cfg = load_config(config)
    acc = _table("accuracy")
    if acc is None:
        print("no accuracy.csv; run analyse first")
        return []
    _check(acc, ["meter", "group"])
    paths = []
    paths += fig_spearman(acc)
    dor = _table("dor_by_category")
    if dor is not None:
        _check(dor, ["meter", "category"])
        paths += fig_dor(dor)
    for name, fn in [("confusion", fig_confusion), ("ablation", fig_ablation),
                     ("misjudged_structures", fig_misjudged), ("spelling", fig_spelling),
                     ("guessing_curves", fig_guessing_curves),
                     ("floor_attribution", fig_error_attribution)]:
        df = _table(name)
        if df is not None:
            paths += fn(df)
    dep = _table("deployment")
    if dep is not None:
        paths += fig_bundle(dep, acc)
    real = _table("real_accuracy")
    if real is not None:
        paths += fig_real(real)
    gstar = REF / "reference_gstar.csv"
    if gstar.exists():
        from . import analyse
        merged = analyse.load_merged(cfg["seeds"]["main"], analyse.read_reference(gstar))
        paths += fig_scatter(merged)
    for p in paths:
        print("wrote", p)
    return paths


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    run(ap.parse_args().config)


if __name__ == "__main__":
    _main()
