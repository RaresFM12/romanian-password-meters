import argparse
import csv
import io
import json
import unicodedata
from . import ro_handbuilt as hb
from .config import REPO_ROOT
from .normalize import fold, nfc, to_comma

SIRUTA_TYPES = {"judetul", "municipiul", "orasul", "oras", "comuna", "sat",
                "satul", "regiunea", "sectorul"}

METER = REPO_ROOT / "data/lexicon/meter"
GEN = REPO_ROOT / "data/lexicon/generator"
TABLES = REPO_ROOT / "results/tables"
LANG_RO = "npm:@zxcvbn-ts/language-ro@4.1.2"
HB = "src/ropw/ro_handbuilt.py"

MANIFEST = {}


def _strip_format(w):
    return "".join(c for c in w if unicodedata.category(c) != "Cf")


def _audit_fold(w):
    w = w.translate(str.maketrans("şţșț", "stst"))
    return "".join(c for c in unicodedata.normalize("NFKD", w)
                   if not unicodedata.combining(c)).lower()


def _read_src(name):
    path = METER / ("_src_" + name + ".txt")
    if not path.exists():
        raise FileNotFoundError(str(path) + " missing; run bridge/export_ro.mjs")
    return [l.rstrip("\n") for l in open(path, encoding="utf-8")]


def write_meter_tsv(name, rows, inputs):
    rows = sorted(rows, key=lambda r: r[1])
    METER.mkdir(parents=True, exist_ok=True)
    with open(METER / (name + ".tsv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["item", "rank", "freq"])
        for item, rank, freq in rows:
            w.writerow([item, rank, freq])
    MANIFEST[name] = inputs
    return len(rows)


def build_common_clean():
    words = _read_src("commonwords")
    group_best = {}
    for i, w in enumerate(words):
        key = fold(_strip_format(w))
        group_best[key] = min(group_best.get(key, i), i)
    rows = []
    seen = set()
    for i, w in enumerate(words):
        best = group_best[fold(_strip_format(w))]
        for variant in dict.fromkeys([w, _strip_format(w)]):
            if variant and variant not in seen:
                seen.add(variant)
                rows.append((variant, best + 1, i + 1))
    return write_meter_tsv("ro_common_clean", rows, [LANG_RO + ":commonWords-ro"])


def build_names_ext():
    names = _read_src("firstnames")
    items = [nfc(w) for w in names] + [nfc(d) for d in hb.DIMINUTIVES]
    return write_meter_tsv("ro_names_ext", _ranked(items),
                           [LANG_RO + ":firstnames-ro", HB + ":DIMINUTIVES"])


def _ranked(items):
    out = []
    seen = set()
    for w in items:
        w = nfc(w)
        if w and w not in seen:
            seen.add(w)
            out.append((w, len(out) + 1, len(out) + 1))
    return out


def build_calendar():
    return write_meter_tsv("ro_calendar", _ranked(hb.CALENDAR), [HB + ":CALENDAR"])


def build_cultural():
    return write_meter_tsv("ro_cultural", _ranked(hb.CULTURAL), [HB + ":CULTURAL"])


def build_expressions():
    return write_meter_tsv("ro_expressions", _ranked(hb.EXPRESSIONS), [HB + ":EXPRESSIONS"])


def _is_name(w):
    return len(w) >= 3 and all(c.isalpha() or c == "-" for c in w)


def build_places():
    items = [name for name, _ in hb.COUNTIES]
    inputs = [HB + ":COUNTIES"]
    siruta = REPO_ROOT / "data/raw/siruta/siruta.csv"
    if siruta.exists():
        txt = siruta.read_bytes().decode("cp1250", errors="replace")
        reader = csv.reader(io.StringIO(txt), delimiter=";")
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            name = nfc(row[1].strip()).lower()
            words = name.split()
            if words and fold(words[0]) in SIRUTA_TYPES:
                words = words[1:]
            if not words:
                continue
            joined = "".join(words)
            for cand in [joined] + words:
                if _is_name(cand):
                    # SIRUTA is cp1250 (cedilla only): correct spelling first
                    items.append(to_comma(cand))
                    items.append(cand)
        inputs.append("data/raw/siruta/siruta.csv")
    return write_meter_tsv("ro_places", _ranked(items), inputs)


def write_audit():
    words = _read_src("commonwords")
    present = set(words)
    ced2comma = str.maketrans("şţ", "șț")
    pairs = [w for w in words
             if ("ş" in w or "ţ" in w) and w.translate(ced2comma) in present]
    fmt = [w for w in words if any(unicodedata.category(c) == "Cf" for c in w)]
    # zxcvbn's rank of a word is its position in the list + 1
    rank = {w: i + 1 for i, w in enumerate(words)}
    audit = {
        "entries": len(words),
        "cedilla_comma_pairs": len(pairs),
        "format_char_entries": len(fmt),
        "unique_after_fold": len({_audit_fold(w) for w in words}),
        "rank_vacanta_cedilla": rank.get("vacanţă"),
        "rank_vacanta_comma": rank.get("vacanță"),
        "rank_vacanta_ascii": rank.get("vacanta"),
    }
    TABLES.mkdir(parents=True, exist_ok=True)
    with open(TABLES / "language_ro_audit.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        for k, v in audit.items():
            w.writerow([k, v])
    return audit


def _folded_set(path):
    with open(path, encoding="utf-8", newline="") as f:
        return {fold(_strip_format(r["item"])) for r in csv.DictReader(f, delimiter="\t")}


def write_overlap():
    lists = {}
    for p in sorted(GEN.glob("*.tsv")):
        lists["gen:" + p.stem] = _folded_set(p)
    for p in sorted(METER.glob("*.tsv")):
        lists["meter:" + p.stem] = _folded_set(p)
    names = list(lists)
    TABLES.mkdir(parents=True, exist_ok=True)
    rows = 0
    with open(TABLES / "list_overlap.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["list_a", "list_b", "a_size", "b_size", "intersection",
                    "contain_a_in_b", "contain_b_in_a", "jaccard"])
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                sa = lists[a]
                sb = lists[b]
                inter = len(sa & sb)
                union = len(sa | sb)
                w.writerow([a, b, len(sa), len(sb), inter,
                            round(inter / len(sa), 4) if sa else 0,
                            round(inter / len(sb), 4) if sb else 0,
                            round(inter / union, 4) if union else 0])
                rows += 1
    return rows


def build_all():
    sizes = {
        "ro_common_clean": build_common_clean(),
        "ro_names_ext": build_names_ext(),
        "ro_calendar": build_calendar(),
        "ro_cultural": build_cultural(),
        "ro_expressions": build_expressions(),
        "ro_places": build_places(),
    }
    (METER / "manifest.json").write_text(
        json.dumps({"inputs": MANIFEST, "sizes": sizes}, indent=2, ensure_ascii=False)
        + "\n", encoding="utf-8")
    return sizes


def _main():
    argparse.ArgumentParser().parse_args()
    sizes = build_all()
    audit = write_audit()
    overlap_rows = write_overlap()
    for name, n in sizes.items():
        print(name, n)
    print("audit:", audit)
    print("overlap rows:", overlap_rows)


if __name__ == "__main__":
    _main()
