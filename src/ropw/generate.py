import argparse
import numpy as np
import pandas as pd
from .config import REPO_ROOT, load_config
from .lexicon import SeedList
from .normalize import (fold, nfc, nfd, to_ascii, to_cedilla, to_digraph,
                        to_pre1993, to_pre1993_ascii)

COLUMNS = ["id", "password", "category", "language", "base", "base_rank", "band",
           "case_style", "suffix", "spelling", "family_id", "pair_id", "cluster_id"]

ST = "șțȘȚşţŞŢ"
CIRC = "âÂ"
BREVI = "ăîĂÎ"
DIAC = ST + CIRC + BREVI


def has_st(w):
    return any(c in w for c in ST)


def has_circ(w):
    return any(c in w for c in CIRC)


def has_brevi(w):
    return any(c in w for c in BREVI)


def has_diac(w):
    return any(c in w for c in DIAC)


def _is_roman_family(w):
    return "roman" in fold(w).lower()


def apply_case(word, style):
    if style == "lower":
        return word.lower()
    if style == "all_upper":
        return word.upper()
    if style == "initial_upper":
        return word[:1].upper() + word[1:].lower()
    return word


def apply_phrase_case(words, style):
    if style == "lower":
        return "".join(w.lower() for w in words)
    if style == "all_upper":
        return "".join(w.upper() for w in words)
    return "".join(w[:1].upper() + w[1:].lower() for w in words)


def apply_spelling(word, spelling):
    if spelling in ("none", "correct"):
        return nfc(word)
    if spelling == "ascii":
        return to_ascii(word)
    if spelling == "cedilla":
        return to_cedilla(word)
    if spelling == "digraph":
        return to_digraph(word)
    if spelling == "pre1993":
        return to_pre1993(word)
    if spelling == "pre1993_ascii":
        return to_pre1993_ascii(word)
    if spelling == "decomposed":
        return nfd(word)
    raise ValueError(spelling)


def _draw_case(rng, cfg):
    cs = cfg["generator"]["case_style"]
    r = rng.random()
    if r < cs["lower"]:
        return "lower"
    if r < cs["lower"] + cs["initial_upper"]:
        return "initial_upper"
    return "all_upper"


def _draw_spelling(rng, word):
    if not has_diac(word):
        return "none"
    r = rng.random()
    if has_st(word):
        if r < 0.80:
            return "ascii"
        if r < 0.90:
            return "correct"
        if r < 0.95:
            return "cedilla"
        return "digraph"
    if r < 8 / 9:
        return "ascii"
    return "correct"


def _draw_year(rng, cfg):
    lo, hi = cfg["generator"]["year_range"]
    return str(int(rng.integers(lo, hi + 1)))


def _draw_digits(rng, cfg):
    g = cfg["generator"]["digit_suffix"]
    if rng.random() < g["common_fraction"]:
        common = g["common"]
        return str(common[int(rng.integers(0, len(common)))])
    length = int(rng.integers(1, 5))
    return "".join(str(int(rng.integers(0, 10))) for _ in range(length))


def _draw_symbol(rng, cfg):
    sy = cfg["generator"]["symbols"]
    return sy[int(rng.integers(0, len(sy)))]


def _optional_suffix(rng, cfg, digits=True, symbol=True):
    p = cfg["generator"]["optional_part_prob"]
    out = ""
    if digits and rng.random() < p:
        out += _draw_digits(rng, cfg)
    if symbol and rng.random() < p:
        out += _draw_symbol(rng, cfg)
    return out


def _leetify(cased, rng, cfg):
    sub = cfg["generator"]["leet"]["substitutions"]
    p = cfg["generator"]["leet"]["per_char_prob"]
    eligible = [i for i, ch in enumerate(cased) if ch.lower() in sub]
    out = list(cased)
    done = 0
    for i in eligible:
        if rng.random() < p:
            opts = sub[cased[i].lower()]
            out[i] = opts[int(rng.integers(0, len(opts)))]
            done += 1
    if eligible and done == 0:
        i = eligible[int(rng.integers(0, len(eligible)))]
        opts = sub[cased[i].lower()]
        out[i] = opts[int(rng.integers(0, len(opts)))]
    return "".join(out)


def _row(**kw):
    row = {c: "" for c in COLUMNS}
    row.update(kw)
    return row


class Generator:
    def __init__(self, cfg, seeds, seed):
        self.cfg = cfg
        self.s = seeds
        self.rng = np.random.default_rng(seed)
        self.bands = cfg["generator"]["rank_bands"]
        self.rows = []
        self.counter = {}

    def _id(self, category):
        n = self.counter.get(category, 0)
        self.counter[category] = n + 1
        return category + "-" + str(n).zfill(5)

    def _sample_banded(self, sl):
        bands = sl.usable_bands(self.bands)
        bi = int(self.rng.integers(0, len(bands)))
        item, rank = sl.sample(self.rng, bands[bi])
        return item, rank, bi

    def _word_like(self, category, sl, language, n, suffix_kind):
        for _ in range(n):
            item, rank, bi = self._sample_banded(sl)
            style = _draw_case(self.rng, self.cfg)
            if language == "ro":
                spelling = _draw_spelling(self.rng, item)
            else:
                spelling = "none"
            core = apply_case(apply_spelling(item, spelling), style)
            suffix = self._suffix(suffix_kind)
            self.rows.append(_row(
                id=self._id(category), password=core + suffix, category=category,
                language=language, base=item, base_rank=rank, band=bi,
                case_style=style, suffix=suffix, spelling=spelling))

    def _suffix(self, kind):
        if kind == "none":
            return ""
        if kind == "digits":
            return _draw_digits(self.rng, self.cfg)
        if kind == "year":
            return _draw_year(self.rng, self.cfg)
        if kind == "year_symbol":
            return _draw_year(self.rng, self.cfg) + _draw_symbol(self.rng, self.cfg)
        if kind == "opt":
            return _optional_suffix(self.rng, self.cfg)
        if kind == "req_digits":
            return _draw_digits(self.rng, self.cfg)
        raise ValueError(kind)

    def _twin_word(self, ro_cat, en_cat, ro, en, n, name=False):
        for i in range(n):
            ro_bands = ro.usable_bands(self.bands)
            en_bands = en.usable_bands(self.bands)
            bi = int(self.rng.integers(0, min(len(ro_bands), len(en_bands))))
            ro_item, ro_rank = ro.sample(self.rng, ro_bands[bi])
            en_item, en_rank = en.sample(self.rng, en_bands[bi])
            style = _draw_case(self.rng, self.cfg)
            if name and self.rng.random() < 0.5:
                suffix = self._suffix("year")
            else:
                suffix = self._suffix("digits")
            pid = ro_cat + "~" + en_cat + "-" + str(i).zfill(5)
            ro_spell = _draw_spelling(self.rng, ro_item)
            self.rows.append(_row(
                id=self._id(ro_cat),
                password=apply_case(apply_spelling(ro_item, ro_spell), style) + suffix,
                category=ro_cat, language="ro", base=ro_item, base_rank=ro_rank,
                band=bi, case_style=style, suffix=suffix, spelling=ro_spell, pair_id=pid))
            self.rows.append(_row(
                id=self._id(en_cat),
                password=apply_case(en_item, style) + suffix,
                category=en_cat, language="en", base=en_item, base_rank=en_rank,
                band=bi, case_style=style, suffix=suffix, spelling="none", pair_id=pid))

    def _twin_phrase(self, ro_groups, en_groups, n):
        shared = sorted(set(ro_groups) & set(en_groups) & {2, 3, 4})
        for i in range(n):
            k = shared[int(self.rng.integers(0, len(shared)))]
            ro_sl = ro_groups[k]
            en_sl = en_groups[k]
            ro_bands = ro_sl.usable_bands(self.bands)
            en_bands = en_sl.usable_bands(self.bands)
            bi = int(self.rng.integers(0, min(len(ro_bands), len(en_bands))))
            ro_item, ro_rank = ro_sl.sample(self.rng, ro_bands[bi])
            en_item, en_rank = en_sl.sample(self.rng, en_bands[bi])
            style = _draw_case(self.rng, self.cfg)
            suffix = _optional_suffix(self.rng, self.cfg)
            pid = "RO-phrase~EN-phrase-" + str(i).zfill(5)
            self.rows.append(_row(
                id=self._id("RO-phrase"),
                password=apply_phrase_case(ro_item.split(), style) + suffix,
                category="RO-phrase", language="ro", base=ro_item, base_rank=ro_rank,
                band=bi, case_style=style, suffix=suffix, spelling="none", pair_id=pid))
            self.rows.append(_row(
                id=self._id("EN-phrase"),
                password=apply_phrase_case(en_item.split(), style) + suffix,
                category="EN-phrase", language="en", base=en_item, base_rank=en_rank,
                band=bi, case_style=style, suffix=suffix, spelling="none", pair_id=pid))

    def _passphrase(self, n):
        words = self.s["ro_words"]
        for _ in range(n):
            k = 3 if self.rng.random() < 0.5 else 4
            picks = [self._sample_banded(words)[0] for _ in range(k)]
            joiner = " " if self.rng.random() < 0.5 else ""
            pw = joiner.join(w.lower() for w in picks)
            self.rows.append(_row(
                id=self._id("RO-passphrase"), password=pw, category="RO-passphrase",
                language="ro", base=joiner.join(picks), base_rank=-1, band="",
                case_style="lower", suffix="", spelling="none"))

    def _leet(self, n):
        pools = {"word": self.s["ro_words"], "name": self.s["ro_names"]}
        for _ in range(n):
            r = self.rng.random()
            if r < 1 / 3:
                kind = "word"
            elif r < 2 / 3:
                kind = "name"
            else:
                kind = "phrase"
            if kind == "phrase":
                item, rank, bi = self._sample_banded(self.s["ro_phrases_flat"])
                style = _draw_case(self.rng, self.cfg)
                cased = apply_phrase_case(item.split(), style)
            else:
                item, rank, bi = self._sample_banded(pools[kind])
                style = _draw_case(self.rng, self.cfg)
                cased = apply_case(to_ascii(item), style)
            suffix = _optional_suffix(self.rng, self.cfg)
            pw = _leetify(cased, self.rng, self.cfg) + suffix
            self.rows.append(_row(
                id=self._id("RO-leet"), password=pw, category="RO-leet", language="ro",
                base=item, base_rank=rank, band=bi, case_style=style, suffix=suffix,
                spelling="leet"))

    def _translit(self, n):
        pool = self.s["ro_words"].filter(has_st)
        names = self.s["ro_names"].filter(has_st)
        for _ in range(n):
            sl = pool if (self.rng.random() < 0.5 or names.size == 0) else names
            item, rank, bi = self._sample_banded(sl)
            style = _draw_case(self.rng, self.cfg)
            suffix = _optional_suffix(self.rng, self.cfg)
            pw = apply_case(to_digraph(item), style) + suffix
            self.rows.append(_row(
                id=self._id("RO-translit"), password=pw, category="RO-translit",
                language="ro", base=item, base_rank=rank, band=bi, case_style=style,
                suffix=suffix, spelling="digraph"))

    def _inflected(self, n):
        sl = self.s["ro_inflected"]
        for _ in range(n):
            item, rank, bi = self._sample_banded(sl)
            style = _draw_case(self.rng, self.cfg)
            spelling = _draw_spelling(self.rng, item)
            suffix = _optional_suffix(self.rng, self.cfg)
            pw = apply_case(apply_spelling(item, spelling), style) + suffix
            self.rows.append(_row(
                id=self._id("RO-inflected"), password=pw, category="RO-inflected",
                language="ro", base=item, base_rank=rank, band=bi, case_style=style,
                suffix=suffix, spelling=spelling))

    def _random(self, n):
        lo = self.cfg["generator"]["random"]["charset_lo"]
        hi = self.cfg["generator"]["random"]["charset_hi"]
        a, b = self.cfg["generator"]["random"]["length_range"]
        for _ in range(n):
            length = int(self.rng.integers(a, b + 1))
            pw = "".join(chr(int(self.rng.integers(lo, hi + 1))) for _ in range(length))
            self.rows.append(_row(
                id=self._id("RANDOM"), password=pw, category="RANDOM",
                language="random", base=pw, base_rank=-1, band="",
                case_style="none", suffix="", spelling="none"))

    def _families(self):
        fam = self.cfg["families"]
        words = self.s["ro_words"]
        st = words.filter(lambda w: has_st(w)).items[:fam["with_st"]]
        circ = words.filter(
            lambda w: has_circ(w) and not has_st(w) and not _is_roman_family(w)
        ).items[:fam["with_circumflex"]]
        brevi = words.filter(
            lambda w: has_brevi(w) and not has_st(w) and not has_circ(w)
        ).items[:fam["with_breve_i"]]
        if (len(st) < fam["with_st"] or len(circ) < fam["with_circumflex"]
                or len(brevi) < fam["with_breve_i"]):
            raise ValueError("ro_words lacks enough diacritic words for the families")
        plans = []
        for w in st:
            plans.append((w, ["correct", "cedilla", "ascii", "digraph", "decomposed"]))
        for w in circ:
            plans.append((w, ["correct", "ascii", "pre1993", "pre1993_ascii", "decomposed"]))
        for w in brevi:
            plans.append((w, ["correct", "ascii", "decomposed"]))
        for fi, (word, spellings) in enumerate(plans):
            fid = "fam-" + str(fi).zfill(4)
            for sp in spellings:
                self.rows.append(_row(
                    id=self._id("RO-diacritic"), password=apply_spelling(word, sp),
                    category="RO-diacritic", language="ro", base=word, base_rank=-1,
                    band="", case_style="none", suffix="", spelling=sp, family_id=fid))

    def build(self):
        c = self.cfg["categories"]
        ph_ro = _group_phrases(self.s["ro_phrases"])
        ph_en = _group_phrases(self.s["en_phrases"])
        self.s["ro_phrases_flat"] = self.s["ro_phrases"]

        self._twin_word("RO-word-num", "EN-word-num",
                        self.s["ro_words"], self.s["en_words"], c["RO-word-num"])
        self._twin_word("RO-name-num", "EN-name-num",
                        self.s["ro_names"], self.s["en_names"], c["RO-name-num"], name=True)
        self._twin_phrase(ph_ro, ph_en, c["RO-phrase"])
        self._word_like("RO-word", self.s["ro_words"], "ro", c["RO-word"], "none")
        self._word_like("RO-word-year", self.s["ro_words"], "ro", c["RO-word-year"], "year")
        self._word_like("RO-name-sym", self.s["ro_names"], "ro", c["RO-name-sym"], "year_symbol")
        self._word_like("RO-place", self.s["ro_places"], "ro", c["RO-place"], "opt")
        self._leet(c["RO-leet"])
        self._translit(c["RO-translit"])
        self._inflected(c["RO-inflected"])
        self._word_like("RO-cultural", self.s["ro_cultural"], "ro", c["RO-cultural"], "req_digits")
        self._passphrase(c["RO-passphrase"])
        self._random(c["RANDOM"])
        self._families()

        df = pd.DataFrame(self.rows, columns=COLUMNS)
        df["cluster_id"] = _cluster_ids(df)
        return df


def _group_phrases(sl):
    groups = {}
    for item in sl.items:
        groups.setdefault(len(item.split()), []).append(item)
    return {k: SeedList(sl.name + "-" + str(k), v) for k, v in groups.items()}


def _cluster_ids(df):
    n = len(df)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    specs = [
        ("base", lambda v: fold(v).lower() if v and v != "-1" else None),
        ("pair_id", lambda v: v or None),
        ("family_id", lambda v: v or None),
    ]
    for col, keyfn in specs:
        groups = {}
        for i, v in enumerate(df[col].tolist()):
            if col == "base" and df["category"].iloc[i] in ("RANDOM", "RO-passphrase"):
                continue
            k = keyfn(v)
            if k is None:
                continue
            key = col + ":" + k
            if key in groups:
                union(groups[key], i)
            else:
                groups[key] = i

    roots = [find(i) for i in range(n)]
    remap = {}
    out = []
    for r in roots:
        if r not in remap:
            remap[r] = len(remap)
        out.append(remap[r])
    return out


def write_targets(df, extra, path):
    vals = set()
    for p in df["password"].tolist():
        vals.add(nfc(p))
    for x in extra:
        vals.add(nfc(x))
    path.write_text("\n".join(sorted(vals)) + "\n", encoding="utf-8")


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    gen_dir = REPO_ROOT / "data/lexicon/generator"
    seeds = {
        "ro_words": SeedList.load(gen_dir / "ro_words.tsv"),
        "ro_names": SeedList.load(gen_dir / "ro_names.tsv"),
        "ro_phrases": SeedList.load(gen_dir / "ro_phrases.tsv"),
        "ro_places": SeedList.load(gen_dir / "ro_places.tsv"),
        "ro_cultural": SeedList.load(gen_dir / "ro_cultural.tsv"),
        "ro_inflected": SeedList.load(gen_dir / "ro_inflected.tsv"),
        "en_words": SeedList.load(gen_dir / "en_words.tsv"),
        "en_names": SeedList.load(gen_dir / "en_names.tsv"),
        "en_phrases": SeedList.load(gen_dir / "en_phrases.tsv"),
    }
    out = REPO_ROOT / "data/synthetic"
    for s in [cfg["seeds"]["main"]] + list(cfg["seeds"]["extra"]):
        df = Generator(cfg, dict(seeds), s).build()
        df.to_csv(out / ("case_seed" + str(s) + ".csv"), index=False, lineterminator="\n")
        print("seed", s, len(df), "passwords")


if __name__ == "__main__":
    _main()
