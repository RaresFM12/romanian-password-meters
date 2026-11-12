# Preliminary measurements quoted in research-plan.md

- `audit_language_ro.py` — audits `@zxcvbn-ts/language-ro` (duplicates, encodings, ranks) and measures
  overlap with the Italian/Spanish/French/Portuguese packages (plan section 2.3).
  Run: `python3 -I audit_language_ro.py` (downloads the current zxcvbn-ts master into a temp dir).
- `zxcvbn_floor_check.mjs` — scores the example passwords of plan section 2.4 under M-ZX-EN
  (core + language-common + language-en) and M-ZX-RO-PKG (the same plus language-ro).
  Run from a directory where `npm install @zxcvbn-ts/core@4.2.0 @zxcvbn-ts/language-common@4.2.0 @zxcvbn-ts/language-en@4.2.0 @zxcvbn-ts/language-ro@4.1.2`
  has been done: `node zxcvbn_floor_check.mjs`.
- `check_diacritic_spellings.py` — checks how `language-ro` 4.1.2 covers the spellings of Romanian diacritic
  letters: both Unicode encodings of ș/ț, the sign dropped, `sh`/`tz` digraphs, pre-1993 î-forms and inflected forms;
  counts non-NFC entries and entries with invisible characters (plan section 2.3).
  Run: `python3 -I check_diacritic_spellings.py`.
  Result on 2026-10-19: no `sh`/`tz` spelling is present (`shefu`, `fetitza`, `ionutz`, `pisicutza`, `dragutza`),
  neither are `teiubesc`, `lamultiani`; `ionuţ` (cedilla) is missing from
  `firstnames` while `ionuț` is present; in `commonWords` the cedilla form often ranks far better than the
  comma-below form (`şefu` 2,821 vs `șefu` 10,132; `fetiţă` 2,920 vs `fetiță` 9,028); pre-1993 î-forms exist only
  for frequent words (`cînd` 3,936, `sînt` 2,411, `mîine` 18,196; `pîine` absent while `pâine` is 2,866);
  0 entries are not in NFC; 317 entries carry invisible formatting characters (e.g. U+200E before `în`).

Output on 2026-10-12 (zxcvbn-ts core 4.2.0, language-ro 4.1.2):

```
vacanta          EN 1.0e+5 s1 | EN+RO 1.2e+4 s1 vacanta
Andrei1999!      EN 1.0e+8 s3 | EN+RO 1.0e+8 s3 Andrei · 1999!
TeIubescMult     EN 1.4e+10 s4 | EN+RO 1.2e+8 s3 Te · Iubesc · Mult
VacantaLaMare1!  EN 1.1e+13 s4 | EN+RO 1.1e+12 s4 Vacanta · La · Mare · 1!
vacanță          EN 1.0e+7 s2 | EN+RO 7.7e+3 s1 vacanță
vacanţă          EN 1.0e+7 s2 | EN+RO 2.9e+3 s1 vacanţă
teiubesc         EN 1.9e+4 s1 | EN+RO 1.9e+4 s1 teiubesc
```
