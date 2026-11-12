import argparse
import csv
import gzip
import json
import re
import tarfile
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from .config import REPO_ROOT, load_config
from .normalize import nfc

GEN = REPO_ROOT / "data/lexicon/generator"
RAW = REPO_ROOT / "data/raw"

INVISIBLE = {ord(c): None for c in "​‌‍‎‏﻿­ "}
RO_LETTERS = set("abcdefghijklmnopqrstuvwxyzăâîșțşţ")
EN_LETTERS = set("abcdefghijklmnopqrstuvwxyz")
RO_RE = re.compile(r"[a-zăâîșțşţ]+")
EN_RE = re.compile(r"[a-z]+")

MANIFEST = {}


def clean(tok):
    return nfc(tok).translate(INVISIBLE).strip().lower()


def is_word(tok, letters, min_len=2):
    return len(tok) >= min_len and all(c in letters for c in tok)


def write_tsv(name, ranked, inputs):
    GEN.mkdir(parents=True, exist_ok=True)
    with open(GEN / (name + ".tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["item", "rank", "freq"])
        for i, (item, freq) in enumerate(ranked, start=1):
            w.writerow([item, i, freq])
    MANIFEST[name] = [str(p.relative_to(REPO_ROOT)) for p in inputs]
    return len(ranked)


def _rank(counter):
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def _leipzig_member(tar_path, suffix):
    with tarfile.open(tar_path, "r:gz") as tf:
        for m in tf.getnames():
            if m.endswith(suffix):
                return m
    raise FileNotFoundError(suffix + " not in " + tar_path.name)


def leipzig_words(tar_path, letters):
    member = _leipzig_member(tar_path, "-words.txt")
    counter = Counter()
    with tarfile.open(tar_path, "r:gz") as tf:
        for raw in tf.extractfile(member):
            parts = raw.decode("utf-8").rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            tok = clean(parts[1])
            if is_word(tok, letters):
                counter[tok] += int(parts[2])
    return _rank(counter)


def leipzig_ngrams(tar_path, token_re, max_sentences, top_per_len):
    member = _leipzig_member(tar_path, "-sentences.txt")
    by_len = {2: Counter(), 3: Counter(), 4: Counter()}
    with tarfile.open(tar_path, "r:gz") as tf:
        for i, raw in enumerate(tf.extractfile(member)):
            if i >= max_sentences:
                break
            text = raw.decode("utf-8").split("\t", 1)[-1].lower()
            toks = [t for t in token_re.findall(nfc(text)) if len(t) >= 2]
            for n in (2, 3, 4):
                for j in range(len(toks) - n + 1):
                    by_len[n][" ".join(toks[j:j + n])] += 1
    out = []
    for n in (2, 3, 4):
        kept = [(p, c) for p, c in by_len[n].items() if c >= 2]
        out.extend(sorted(kept, key=lambda kv: (-kv[1], kv[0]))[:top_per_len])
    return sorted(out, key=lambda kv: (-kv[1], kv[0]))


def geonames_places(zip_path):
    best = {}
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open("RO.txt") as f:
            for raw in f:
                col = raw.decode("utf-8").split("\t")
                if len(col) < 15:
                    continue
                fclass, fcode, pop = col[6], col[7], col[14]
                if fclass != "P" and fcode != "ADM1":
                    continue
                name = clean(col[1])
                if not is_word(name, RO_LETTERS):
                    continue
                best[name] = max(best.get(name, 0), int(pop or 0))
    return _rank(best)


def bnc_words(gz_path):
    counter = Counter()
    with gzip.open(gz_path, "rt", encoding="latin-1") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2 or parts[1].startswith("!!"):
                continue
            tok = clean(parts[1])
            if is_word(tok, EN_LETTERS):
                counter[tok] += int(parts[0])
    return _rank(counter)


def hadley_names(csv_path):
    acc = {}
    with open(csv_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = clean(row["name"])
            if is_word(name, EN_LETTERS):
                acc[name] = acc.get(name, 0.0) + float(row["percent"])
    ranked = sorted(acc.items(), key=lambda kv: (-kv[1], kv[0]))
    return [(name, int(round(score * 1e6))) for name, score in ranked]


INFLECTED_ENDINGS = ("ule", "ulă", "uța", "uțo", "uțu", "uțe", "ucă", "ică",
                     "ilor", "elor", "ii", "lor", "ților", "șilor",
                     "ează", "ând", "ării")


def ro_inflected_from_words(words):
    return [(w, f) for w, f in words if w.endswith(INFLECTED_ENDINGS)]


def tuple_field(values, idx):
    i = 0
    n = len(values)
    while True:
        while i < n and values[i] != "(":
            i += 1
        if i >= n:
            return
        i += 1
        field = 0
        result = None
        while i < n and values[i] != ")":
            if values[i] == "'":
                i += 1
                buf = []
                while i < n:
                    c = values[i]
                    if c == "\\":
                        buf.append(values[i + 1])
                        i += 2
                        continue
                    if c == "'":
                        i += 1
                        break
                    buf.append(c)
                    i += 1
                val = "".join(buf)
            else:
                start = i
                while i < n and values[i] not in ",)":
                    i += 1
                tok = values[start:i]
                if tok == "NULL":
                    val = None
                else:
                    val = tok
            if field == idx:
                result = val
            if i < n and values[i] == ",":
                i += 1
                field += 1
        i += 1
        yield result


def _dump_table_values(dump_path, table):
    prefix = "INSERT INTO `" + table + "` VALUES "
    with gzip.open(dump_path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith(prefix):
                yield line[len(prefix):].rstrip().rstrip(";")


def dexonline_sets(dump_path, keep):
    lemmas = set()
    for values in _dump_table_values(dump_path, "Lexeme"):
        for form in tuple_field(values, 2):
            if form:
                w = clean(form)
                if w in keep:
                    lemmas.add(w)
    inflected = set()
    for values in _dump_table_values(dump_path, "InflectedForm"):
        for form in tuple_field(values, 2):
            if form:
                w = clean(form)
                if w in keep and w not in lemmas:
                    inflected.add(w)
    return lemmas, inflected


WIKI_API = "https://ro.wikipedia.org/w/api.php"
PAREN = re.compile(r"\s*\(.*?\)\s*$")


def _wiki_get(params):
    full = dict(params)
    full["format"] = "json"
    url = WIKI_API + "?" + urllib.parse.urlencode(full)
    req = urllib.request.Request(url, headers={"User-Agent": "ropw-research/1.0"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wiki_category_titles(category, cmtype="page"):
    titles = []
    cont = {}
    while True:
        params = {"action": "query", "list": "categorymembers",
                  "cmtitle": "Categorie:" + category, "cmtype": cmtype, "cmlimit": "500"}
        params.update(cont)
        data = _wiki_get(params)
        for m in data.get("query", {}).get("categorymembers", []):
            titles.append(m["title"])
        if "continue" in data:
            cont = data["continue"]
            time.sleep(0.2)
        else:
            break
    return titles


def _clean_title(title):
    title = PAREN.sub("", title).split(":")[-1].strip()
    parts = title.split()
    if parts:
        return clean(parts[0])
    return ""


def _rank_by_corpus(names, freq):
    ranked = {n: freq.get(n, 0) for n in names if is_word(n, RO_LETTERS)}
    return sorted(ranked.items(), key=lambda kv: (-kv[1], kv[0]))


def build_wikipedia_lists(freq):
    sizes = {}
    name_titles = []
    for cat in ("Prenume masculine românești", "Prenume feminine românești",
                "Prenume românești"):
        name_titles += wiki_category_titles(cat)
    names = {_clean_title(t) for t in name_titles}
    names.discard("")
    sizes["ro_names"] = write_tsv("ro_names", _rank_by_corpus(names, freq),
                                  [RAW / "wikipedia_ro"])
    club_titles = []
    for cat in ("Cluburi de fotbal din România",
                "Cluburi participante în campionatul național de fotbal al României"):
        club_titles += wiki_category_titles(cat)
    clubs = {_clean_title(t) for t in club_titles}
    clubs.discard("")
    sizes["ro_cultural"] = write_tsv("ro_cultural", _rank_by_corpus(clubs, freq),
                                     [RAW / "wikipedia_ro"])
    return sizes


def build_all(cfg, wikipedia=True):
    leip_ro = RAW / "leipzig_ro/ron_news_2022_100K.tar.gz"
    leip_en = RAW / "leipzig_en/eng_news_2023_100K.tar.gz"
    geo = RAW / "geonames_ro/RO.zip"
    bnc = RAW / "bnc_freq/all.num.gz"
    names = RAW / "en_names/baby-names.csv"
    dump = RAW / "dexonline/dex-database.sql.gz"

    sizes = {}
    corpus = leipzig_words(leip_ro, RO_LETTERS)

    if dump.exists():
        keep = {w for w, _ in corpus}
        lemmas, inflected = dexonline_sets(dump, keep)
        ro_words = [(w, f) for w, f in corpus if w in lemmas]
        ro_inflected = [(w, f) for w, f in corpus if w in inflected]
        sizes["ro_words"] = write_tsv("ro_words", ro_words, [leip_ro, dump])
        sizes["ro_inflected"] = write_tsv("ro_inflected", ro_inflected, [leip_ro, dump])
    else:
        ro_words = corpus
        sizes["ro_words"] = write_tsv("ro_words", ro_words, [leip_ro])
        sizes["ro_inflected"] = write_tsv("ro_inflected",
                                          ro_inflected_from_words(ro_words), [leip_ro])

    sizes["ro_phrases"] = write_tsv("ro_phrases",
                                    leipzig_ngrams(leip_ro, RO_RE, 100000, 4000), [leip_ro])
    sizes["ro_places"] = write_tsv("ro_places", geonames_places(geo), [geo])
    sizes["en_words"] = write_tsv("en_words", bnc_words(bnc), [bnc])
    sizes["en_names"] = write_tsv("en_names", hadley_names(names), [names])
    sizes["en_phrases"] = write_tsv("en_phrases",
                                    leipzig_ngrams(leip_en, EN_RE, 100000, 4000), [leip_en])

    if wikipedia:
        freq = dict(corpus)
        try:
            sizes.update(build_wikipedia_lists(freq))
        except Exception as exc:
            print("wikipedia step skipped:", exc)

    (GEN / "manifest.json").write_text(
        json.dumps({"inputs": MANIFEST, "sizes": sizes}, indent=2) + "\n", encoding="utf-8")
    return sizes


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/case_study.yaml")
    ap.add_argument("--no-wikipedia", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    sizes = build_all(cfg, wikipedia=not args.no_wikipedia)
    for name, n in sizes.items():
        print(name, n)


if __name__ == "__main__":
    _main()
