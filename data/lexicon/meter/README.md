# Meter-side Romanian lists

These feed the Romanian-aware meter (M-ZX-RO+). They are **separate from the
generator lists** (design section 2.1): the generator uses dexonline, Leipzig, GeoNames
and Wikipedia; the meter uses the language-ro package, the hand-built source and
SIRUTA. The `.tsv` files here are regenerable and gitignored; rebuild with:

```
node bridge/export_ro.mjs data/lexicon/meter      # export language-ro lists
python -m ropw.lexicon_build_meter                # build the meter TSVs + reports
python -m ropw.czech                              # the pruned cz_ copies (M-ZX-RO-CZ)
```

| List | Source | Notes |
|------|--------|-------|
| `ro_common_clean` | `@zxcvbn-ts/language-ro` commonWords (48,511) | Format chars stripped (317 entries); every spelling kept at its fold-group's best rank; no spelling deleted. |
| `ro_names_ext` | language-ro firstnames (857) + hand-built diminutives/vocatives | `ropw.ro_handbuilt.DIMINUTIVES`. |
| `ro_calendar` | hand-built holidays | `ropw.ro_handbuilt.CALENDAR`. |
| `ro_cultural` | hand-built clubs, brands, endearments | `ropw.ro_handbuilt.CULTURAL`. |
| `ro_expressions` | hand-built single-token expressions | `ropw.ro_handbuilt.EXPRESSIONS`. |
| `ro_places` | the 41 counties + Bucharest and the SIRUTA localities (comma-below spelling, then the cedilla spelling) | `ropw.ro_handbuilt.COUNTIES` + `data/raw/siruta/siruta.csv`; no 2-letter county codes. |
| `ro_leaked` | Romanian breach share M | Built by `ropw.breach`, kept private, never committed. |

Hand-built lists live in `src/ropw/ro_handbuilt.py` — **review them there** before
relying on the results. Reports: `results/tables/language_ro_audit.csv` and
`results/tables/list_overlap.csv`.
