# Meter-side Romanian lists (guide C08)

These feed the Romanian-aware meter (M-ZX-RO+). They are **separate from the
generator lists** (guide 6.2.1): the generator uses dexonline, Leipzig, GeoNames
and Wikipedia; the meter uses the language-ro package, the hand-built source and
SIRUTA. The `.tsv` files here are regenerable and gitignored; rebuild with:

```
node bridge/export_ro.mjs data/lexicon/meter      # export language-ro lists
python -m ropw.lexicon_build_meter                # build the meter TSVs + reports
```

| List | Source | Notes |
|------|--------|-------|
| `ro_common_clean` | `@zxcvbn-ts/language-ro` commonWords (48,511) | Format chars stripped (317 entries); every spelling kept at its fold-group's best rank; no spelling deleted. |
| `ro_names_ext` | language-ro firstnames (857) + hand-built diminutives/vocatives | `ropw.ro_handbuilt.DIMINUTIVES`. |
| `ro_calendar` | hand-built holidays | `ropw.ro_handbuilt.CALENDAR`. |
| `ro_cultural` | hand-built clubs, brands, endearments | `ropw.ro_handbuilt.CULTURAL`. |
| `ro_expressions` | hand-built single-token expressions | `ropw.ro_handbuilt.EXPRESSIONS`. |
| `ro_places` | the 41 counties + Bucharest + codes; SIRUTA localities when supplied | `ropw.ro_handbuilt.COUNTIES`; add `data/raw/siruta/siruta.csv` for localities. |
| `ro_leaked` | Romanian breach share M | Built in C09, kept private, never committed. |

Hand-built lists live in `src/ropw/ro_handbuilt.py` — **review them there** before
relying on the results. Reports: `results/tables/language_ro_audit.csv` and
`results/tables/list_overlap.csv`.
