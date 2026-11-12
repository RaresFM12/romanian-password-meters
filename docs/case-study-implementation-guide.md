# Case Study Implementation Guide ("Studiu de caz pe date inițiale")

This guide is for a Claude Code session that will implement the case study, one git commit per step.
Read all of it before the first commit.

## 0. What the assignment asks for

> Run the experiments on a smaller dataset to illustrate the methodology and the potential of the approach.
> This needs data collection, the code of the approach, and data that show its effectiveness (metrics,
> empirical evidence, expert interpretation). **Deliverables:** the experiment code and a chapter
> "Case study" in the research report.

So the case study is the **full pipeline of the experimental design, run at reduced scale**. It is not a new design.
Every rule, threshold and definition comes from the design documents below. Only the dataset sizes change (Section 2).

## 1. Sources of truth (in priority order)

1. `Experimental_Modelling_and_Evaluation_Design.docx` (this repo). This is the version shown to the professor.
   If anything conflicts, it wins. Read it with python-docx. macOS `textutil` drops the equations, so they are
   restated in Section 4 of this guide.
2. `../tmp/ch6_build/chapter6_long.md` (parent folder). This is the detailed version of the same design, with
   the nesting requirements, the Czech recipe and the ablation. Use it for detail, never against (1).
3. `../research-plan.md` (v2.4). Use it for resources, the Romanian spelling background (§2.5) and the
   extension design (§7). RQ6 / Romance work is **out of scope**.
4. `../scripts/preliminary/*`: earlier audit scripts (language-ro duplicates, spelling probes, floor check).

Rules for the implementing session:

- **Do not change a design decision.** If something cannot be done as specified, write it in
  `docs/deviations.md` (what, why, effect on the results) and go on with the closest faithful option.
- **Commit after each step in Section 6**, only when its acceptance checks pass. Use short lowercase messages
  in the student's style (e.g. `add synthetic generator`), plus the attribution trailer the session's settings
  require. **Never push** unless the student asks.
- **Never commit breach-derived data** (passwords, lists or tables that contain real leaked passwords) or large
  third-party dumps. Commit only aggregates (counts, rates, correlations).
- **The attack-based reference is out of scope for this guide.** The student produces it separately and hands
  over one file with a fixed format (Step C13). Do not write code that generates attack candidates.
- **Ethics:** the supervisor and the university approved RockYou and the Romanian breach-derived passwords.
  The data files are placed by the student in `data/breach/` (gitignored).

## 2. Case-study scale

Every category is cut to 10% of the full design. The only exception is RANDOM: at 200 passwords, test T7 could
not pass even with zero failures (0.99^200 = 0.134 > 0.05/12), so it keeps 600 (0.99^600 = 0.0024 < 0.0042).

| Category | Full design | Case study |
|---|---|---|
| RO-word, RO-word-num, RO-word-year, RO-name-num, RO-phrase | 2,000 each | 200 each |
| RO-name-sym, RO-place, RO-leet | 1,500 each | 150 each |
| RO-translit, RO-inflected, RO-cultural, RO-passphrase | 1,000 each | 100 each |
| EN-word-num, EN-name-num, EN-phrase (twins) | 3 × 2,000 | 3 × 200 |
| RANDOM | 2,000 | **600** |
| RO-diacritic families | 1,000 (600 / 200 / 200) | 100 (60 / 20 / 20) → at least 460 strings |
| **Total** | ≈ 31,100 | ≈ **3,510** |

Also needed:

- **Seeds:** main seed `20261111`, plus two extra seeds `1` and `2` for the robustness datasets.
- **Real passwords:** a seeded 10% sample of the unique passwords in the validation share V, each with its
  occurrence count.

**What this scale means statistically (state it in the chapter):** at n = 200, a 95% interval for Spearman ≈ 0.5
is about ±0.11, not ±0.035. Most DOR tests will have fewer than 100 weak passwords and are therefore
**undecided** by the design's own rule. All twelve tests T1–T12 are computed with the final code, but in the
case study they are reported as **illustrative**. The confirmatory decision is made on the full dataset.

All parameters live in **one file**, `config/case_study.yaml`, and no number is hard-coded anywhere else. The full
design is `config/full.yaml`, the same file with the sizes of the "Full design" column, so moving from the case
study to the full study is a config switch.

## 3. Environment

- **Python:** 3.12 from `/opt/homebrew/bin/python3.12` in `.venv/` (the system python is 3.9). Pin exact
  versions in `requirements.txt`: numpy, pandas, pyarrow, scipy, statsmodels, matplotlib, pyyaml, pytest,
  python-docx.
- **Node:** v26 is installed. `bridge/package.json` pins **exact** versions and `package-lock.json` is committed:
  `@zxcvbn-ts/core 4.2.0`, `@zxcvbn-ts/language-common 4.1.3`, `@zxcvbn-ts/language-en 4.1.1`,
  `@zxcvbn-ts/language-ro 4.1.2`, `zxcvbn 4.4.2`, and `esbuild` (any current version, pinned) for E8.
- **R:** only as a test oracle for weighted Spearman: `brew install r`, then `install.packages("wCorr")`.
  The R output is saved once as a JSON fixture and committed, so the tests do not need R.
- **pandoc:** `brew install pandoc`, used for the chapter in C20.
- **Disk:** about 67 GB are free. The dexonline dump and the corpora fit, but keep `data/raw/` out of git.

## 4. Definitions to implement exactly

Here N is NFC normalisation, G*(p) is the reference guess number, g_m(p) is the estimate of meter m, and
score_m(p) is its 0–4 score.

- **Equality of passwords:** two strings are the same password when their NFC forms are equal. Cedilla ş ţ and
  comma-below ș ț stay different.
- **Reference:** G_a(p) = first position i ≤ B_a with N(c_a(i)) = N(p). G*(p) = min over the five attackers.
  Not found means censored.
  - Budgets: B = 10^10 for A-EN, A-RO, A-ALL and A-JTR, and B = 10^9 for A-PCFG.
  - "Cut at 10^9" variant: treat every guess number above 10^9 as censored for all attackers.
- **zxcvbn estimate:** g(p) = min over splits of ( k! · ∏ g(μ_t) + D^(k−1) ), with D = 10^4.
  - Product term = k! · ∏ g(μ_t) over the chosen sequence.
- **Score levels:** the thresholds are T = (10^3+5, 10^6+5, 10^8+5, 10^10+5). The level of a number x is the
  number of thresholds with x ≥ T_i.
  - The same mapping turns G* into the **reference level**. A password not found gets level 4. In the
    "cut at 10^9" variant, levels 3 and 4 are merged.
- **Floor vs missing knowledge:** a dangerous error (weak password with score ≥ 3) is a **floor** error if the
  product term alone has level ≤ 2. Otherwise it is **missing knowledge**.
- **Weak:** G* ≤ 10^6. Robustness thresholds: 10^4 and 10^8.
- **DOR_m(P)** = #{p ∈ W(P) : score_m(p) ≥ 3} / |W(P)|.
- **SUR_m(P)** = #{p ∈ P not found : score_m(p) ≤ 1} / #{p ∈ P not found}.
- **Spearman ρ** between log10 g_m and log10 G*, with censored passwords **tied at the top**. Encode them as
  log10(B_max) + 1; ranks use average ties.
  - Kendall τ is a cross-check.
  - **Weighted Spearman** follows the R package wCorr (`weightedCorr(..., method = "Spearman")`). Port it from
    the wCorr source, not from memory, and test it against the R fixture. `scipy.stats.weightedtau` is a
    different metric: do not use it.
  - Weights: 1 for synthetic passwords, occurrence count in V for real passwords, and 1/G* only as a
    sensitivity check.
- **Error size:** mean |log10 g_m − log10 G*| and mean signed (log10 g_m − log10 G*), over found passwords only.
- **Reclassification (meter A → meter B):** for each password, compare |score − ref level| under A and under B.
  Report the shares that move closer, move farther and stay the same.
- **Spelling spreads:** Δs_m(F) = max score − min score over family F. Δx_m(F) is the same with log10 g_m.
  A family is consistent if Δs = 0.
- **η_m(v)** = [log10 g_m(v) − log10 g_m(u)] − [log10 G*(v) − log10 G*(u)], where u is the ASCII spelling of the
  same word. Computed only when both v and u are found.
- **M-POLICY score:** pass → 4, fail → 0.
  - Normal rule: length ≥ 8 and at least 3 of {lower, upper, digit, symbol}.
  - Strict rule: length ≥ 12 and all 4 classes.
  - Length is counted in Unicode code points after NFC. A non-ASCII letter counts as lower or upper by its case.
- **M-BLOCK score:** 0 if lowercase(NFC(p)) is in the `language-common` password list (49,233 entries; assert
  this count), otherwise 4.
- **M-POLICY and M-BLOCK** enter DOR, SUR and the confusion matrix, never correlations.

## 5. Repository layout (target)

```
romanian-password-meters/
├── README.md                     # updated: how to run, what is private
├── Makefile                      # setup, data, generate, meters, reference-check, analyse, figures, all
├── requirements.txt
├── config/{case_study,full}.yaml
├── docs/
│   ├── case-study-implementation-guide.md   # this file
│   ├── research-plan.md                     # copy of ../research-plan.md (README already points here)
│   ├── deviations.md
│   └── report/                              # chapter source + build script
├── data/
│   ├── sources.yaml              # every external source: URL, access date, sha256, licence
│   ├── raw/                      # downloads (gitignored)
│   ├── breach/                   # student-supplied breach files + everything derived from them (gitignored)
│   ├── lexicon/generator/        # generator seed lists (gitignored if the licence forbids redistribution)
│   ├── lexicon/meter/            # meter lists; hand-built ones committed with provenance README
│   ├── synthetic/                # generated datasets (committed: no real passwords)
│   └── reference/                # guess-number file from the student (synthetic part committed, real part not)
├── bridge/                       # Node: package.json, lock, zx.mjs, zx_orig.mjs, configs/, vendor/ (D variants)
├── packages/zxcvbn-ro-extended/  # the Romanian extension (ESM JavaScript, same layout as a zxcvbn-ts language package)
├── scripts/preliminary/          # copied from ../scripts/preliminary
├── src/ropw/                     # normalize, lexicon, generate, breach, meters/, reference, metrics, stats, experiments/, figures
├── tests/                        # pytest + node:test
└── results/
    ├── tables/  figures/         # committed (aggregates only)
    └── private/                  # anything with real passwords (gitignored)
```

Add to `.gitignore`: `.venv/`, `data/raw/`, `data/breach/` (already present), `results/private/`,
`bridge/node_modules/`, and `data/reference/*real*`.

## 6. Commit-by-commit plan

Each step lists **what to build** and its **acceptance checks**. Do not commit until the checks pass.

### C01: scaffold

Build:
- The layout from Section 5.
- `requirements.txt`, the `.venv` setup in `make setup`, and the `.gitignore` additions.
- `config/case_study.yaml` and `config/full.yaml` with every parameter of Sections 2 and 4, plus the generator
  parameters of C05.
- Copy `../research-plan.md` to `docs/research-plan.md` and `../scripts/preliminary/` to `scripts/preliminary/`.
- An empty `docs/deviations.md`.
- Update the README (structure, `make all`, privacy rule).

Checks:
- `make setup` works from a clean clone.
- `pytest` runs (no tests yet is fine).

### C02: source registry and downloads

Build:
- `data/sources.yaml` and `scripts/fetch_sources.py`. The script downloads the public sources into `data/raw/`
  and records URL, date, size, sha256 and licence.
- Generator and attacker side sources (design Table 2):
  - dexonline database dump (lexemes and inflected forms; data under GPL).
  - CoRoLa frequency list. If it cannot be downloaded within a day, rank by the Leipzig Romanian corpus
    frequencies instead and log this in `deviations.md`. Leipzig is already a generator source, so no
    separation rule is broken.
  - Leipzig corpora (Romanian and English; news or web, about 1M sentences).
  - GeoNames `RO.zip`.
  - Romanian Wikipedia name-list and culture-list pages, through the MediaWiki API.
  - BNC frequency list (Kilgarriff).
  - US SSA baby names `names.zip`.
- Meter-side sources:
  - INS SIRUTA (data.gov.ro).
  - Official Romanian first-name statistics, if a public table exists. Otherwise log a deviation.
- The breach files are **not downloaded**. The script only checks that the files the student placed in
  `data/breach/` exist and records their sha256 in a private manifest.

Checks:
- Running the script twice gives the same checksums.
- Each source has a licence entry.

### C03: normalisation (`src/ropw/normalize.py`)

Build:
- `nfc(s)`.
- A 1:1 fold table, both cases: ă â → a, î → i, ș ş → s, ț ţ → t, with the uppercase forms.
- `to_cedilla(s)` (ș ț → ş ţ) and `to_digraph(s)` (ș → sh, ț → tz, other signs dropped).
- `to_pre1993(s)`: every â → î, except in words of the `român` family (român, române, românesc, România,
  românește …).
- `to_ascii(s)` and `nfd(s)`.
- Export the fold and variant tables to `packages/zxcvbn-ro-extended/src/tables.json`. Python is the single
  source of truth for both sides.

Checks (tests reproduce design Table 4 exactly):
- `fetiță` → cedilla `fetiţă`, ASCII `fetita`, digraph `fetitza`; NFD has 8 code units.
- `pâine` → ASCII `paine`, pre-1993 `pîine`, pre-1993 ASCII `piine`; NFD has 6 code units.
- `român` keeps â in pre-1993.
- `nfc(nfd(x)) == x`.
- The fold changes neither the length nor the indices.

### C04: generator seed lists (`src/ropw/lexicon.py --side generator`)

Build:
- Ranked TSV files (`item`, `rank`, `freq`) in `data/lexicon/generator/`:
  - RO lexemes: dexonline lexemes ranked by CoRoLa (or Leipzig) frequency.
  - RO inflected forms: from dexonline, non-lemma forms, plus diminutives and vocatives present there.
  - RO first names: from Wikipedia.
  - RO phrases: frequent 2–4-word sequences from Leipzig RO.
  - RO places: GeoNames populated places and counties, ranked by population.
  - RO cultural: clubs, brands and slang from the Wikipedia list pages.
  - EN words: BNC.
  - EN names: SSA, summed over years.
  - EN phrases: Leipzig EN n-grams.
- Store everything in NFC, lowercase, without invisible characters.

Checks:
- **No file under `data/lexicon/meter/` or any npm package is read.** Enforce this in code: a manifest of input
  paths per build, plus a test that the generator manifest and the meter manifest are disjoint.
- Every list has at least 50,000 entries, or documents why it is shorter (then fewer rank bands are used).

### C05: synthetic generator (`src/ropw/generate.py`)

Build the generator from design §2.2 and Tables 3–4. Output: `data/synthetic/case_seed{S}.csv` with the columns
`id, password, category, language, base, base_rank, band, case_style, suffix, spelling, family_id, pair_id,
cluster_id`.

**Rank bands:** 1–100, 101–1,000, 1,001–10,000 and 10,001–50,000. Pick a band uniformly, then an item
uniformly inside it. Shorter lists use fewer bands. Twins use the same band.

**Fixed parameters (put them in the config):**
- Case style: lower 50%, initial upper 40%, all upper 10%. For phrases, "initial upper" means CamelCase,
  e.g. `TeIubescMult`.
- Years: uniform over 1950–2026.
- Digit suffix: 1–4 digits. Half are drawn uniformly from the fixed list `1 2 7 12 13 21 22 23 69 77 99 00 01
  007 100 111 123 321 666 1234`. The other half are random, with length uniform over 1–4.
- Symbols: `! @ # $ % & * ? . _`.
- Optional parts (digits, symbol) appear with probability 0.5 each.
- Diacritic words: ASCII 80%, correct 10%, cedilla 5%, digraph 5%. Cedilla and digraph apply only to words
  that contain ș or ț. For other words the shares are rescaled to ASCII 8/9 and correct 1/9.
- RO-leet: the base is a word, a name or a phrase (1/3 each). Substitutions: a → @/4, e → 3, i → 1/!, o → 0,
  s → $/5, t → 7. Each eligible character is substituted with probability 0.5, with at least one substitution.
  Optional suffix.
- RO-passphrase: 3 or 4 words (50/50), joined by a space or nothing (50/50).

**Twins:** pairs (RO-word-num, EN-word-num), (RO-name-num, EN-name-num), (RO-phrase, EN-phrase). Each twin uses
the same band, case style and suffix, and phrase twins have the same word count. Store a shared `pair_id`.

**Families:** 60 words with ș or ț, 20 with â but neither ș nor ț (and outside the `român` family), and 20 with
only ă or î. Each word is written in every applicable spelling of Table 4: lowercase, no suffix, one `family_id`
per word.

**`cluster_id`:** connected components over the links "same folded base item", "same pair_id" and "same
family_id". This is the bootstrap cluster.

**RANDOM:** 95 printable ASCII characters (0x20–0x7E), length uniform over 8–16, from the seeded RNG.

Also write `data/synthetic/targets_all.txt`: the unique NFC strings of all three seeds plus the real-password
sample (the real ones go to `results/private/`). This is the file the student needs to produce the reference.

Checks:
- Same seed gives a byte-identical file.
- The counts match Section 2.
- Twins share band, suffix and word count.
- Family sizes are at least 460 in total.
- No empty or duplicate `id`.
- Report the overlap of passwords across categories (allowed, but listed).

### C06: Node bridge, baseline meters (`bridge/`)

Build:
- `zx.mjs <config>` reads JSONL `{id, password}` on stdin and writes one JSONL line per password:
  `{id, guesses, log10, score, k, product_term, sequence: [{pattern, token, i, j, guesses, dictionaryName,
  rank, l33t, reversed}], ms}`.
- Configs `M-ZX-EN` and `M-ZX-RO-PKG`.
  - Every zxcvbn-ts meter loads `language-common` + `language-en` dictionaries, the common adjacency graphs and
    the English translations.
  - RO-PKG adds the `language-ro` dictionaries.
  - `useLevenshteinDistance` stays at its default.
- **Read the API from `node_modules/@zxcvbn-ts/core/dist/*.d.ts` and the package README.** Version 4 builds a
  factory object from options and custom matchers. Do not guess from older (v2/v3) examples.
- `zx_orig.mjs` runs `zxcvbn` 4.4.2 (M-ZX-ORIG) with the same output format.
- `src/ropw/meters/zx_bridge.py` streams a dataset through one long-lived Node process per meter.

Checks:
- `product_term + 10000^(k−1)` equals `guesses` (relative tolerance 1e−9) for every password with k ≥ 1. If it
  does not, read the core scoring source, document the exact formula in `deviations.md` and adjust
  `product_term`.
- Reproduce the research plan §2.4 table (same rounding):

  | Password | M-ZX-EN | M-ZX-RO-PKG |
  |---|---|---|
  | `vacanta` | 1.0e5, score 1 | 1.2e4, score 1 |
  | `Andrei1999!` | 1.0e8, score 3 | 1.0e8, score 3 |
  | `TeIubescMult` | 1.4e10, score 4 | 1.2e8, score 3; product term 1.8e7 |
  | `VacantaLaMare1!` | 1.1e13, score 4 | 1.1e12, score 4 |

### C07: M-POLICY and M-BLOCK (`src/ropw/meters/policy.py`, `block.py`)

Build:
- The two meters exactly as in Section 4.
- Export the `language-common` password list once, with a small Node script, to `data/lexicon/meter/common.txt`.

Checks:
- The list has 49,233 entries.
- Unit tests on hand-written examples, both policy variants.

### C08: meter-side Romanian lists (`src/ropw/lexicon.py --side meter`)

All files go to `data/lexicon/meter/`, each in rank order, NFC, with a provenance note in
`data/lexicon/meter/README.md`.

**Required lists:**
- `ro_common_clean`: built from `language-ro` commonWords.
  - Entries with invisible characters (317) get a cleaned copy **next to** the original.
  - Every spelling in a fold group gets the best (lowest) rank of its group. No spelling is deleted.
- `ro_names_ext`: `language-ro` first names, plus official statistics (if available), plus hand-built
  diminutives and vocatives (Andu, Ionuț, Mihăiță, Alex …).
- `ro_places`: SIRUTA localities, plus the 41 counties and București, plus the county codes.
- `ro_calendar`: holidays and calendar terms (Crăciun, Paște, Revelion, Mărțișor …).
- `ro_cultural`: hand-built clubs, brands, TV, slang and endearments.
- `ro_expressions`: hand-built single-token expressions (teiubesc, lamultiani, hairomania, noroc …).
- `ro_leaked`: meter share M ranked by count. Produced in C09 and kept private.

Hand-built lists: draft them, keep each under about 500 entries, record how they were made, and **ask the
student to review them before committing**. Do not read any generator list while drafting.

**Required reports:**
- Re-run the audit and confirm 48,511 entries, 2,425 cedilla/comma pairs and 317 entries with invisible
  characters (as in `scripts/preliminary/audit_language_ro.py`).
- `results/tables/list_overlap.csv`: pairwise overlap (count, containment both ways, Jaccard) between every
  generator, meter and attacker list, after folding.

Checks:
- The meter manifest is disjoint from the generator manifest.
- The meter manifest is disjoint from the attacker wordlist files (the student lists those paths in
  `data/reference/attacker_inputs.txt`).

### C09: real passwords (`src/ropw/breach.py`; outputs only in `data/breach/` and `results/private/`)

Build:
- **Filter:** keep a password if it contains a Romanian word of at least 5 letters that is not English, a
  Romanian name, or a Romanian diacritic (ă â î ș ş ț ţ). The vocabularies are the dexonline lexemes after
  folding, minus BNC words, plus the generator name list (log this choice in `deviations.md`).
- **Precision sample:** 300 filtered passwords, seeded, written to `results/private/precision_sample.csv` with
  an empty `is_romanian` column. **The student labels them.** Claude never fills this column. Precision and its
  Wilson interval are computed after labelling.
- **Split by occurrence:** each occurrence goes to M / A / V with probabilities 0.4 / 0.3 / 0.3 (seeded
  multinomial per password count). Write the M, A and V count tables.
- **RockYou adjustment:** write an attacker-side RockYou count table with the M and V occurrences subtracted,
  for the student's reference step.
- **Reuse groups on V:** ≥ 1,000, 100–999, 10–99, 2–9, 1.
- **Profile of V (aggregate only, committed):** length, character classes, and how diacritics are written
  (correct, cedilla, dropped, sh/tz, pre-1993).
- **Case-study sample:** 10% of V's unique passwords (seeded), stratified by reuse group, with counts.

Checks:
- Total occurrences are preserved by the split.
- No file containing passwords appears in `git status`.

### C10: the Romanian extension (`packages/zxcvbn-ro-extended/`, configs in `bridge/configs/`)

Build eight resource groups. Each can be switched on or off in the config:

| # | Group | Content |
|---|---|---|
| G1 | normalisation | custom matcher `roFolded`: NFC with an index map back to the typed string; 1:1 fold; substring lookup in the folded versions of all active Romanian lists, with pre-1993 variants added at the same rank. Scoring: rank × the core's uppercase factor × 2 if the token contains a typed diacritic, else × 1 |
| G2 | sh/tz matcher | custom matcher `roDigraph`: rewrites sh → s and tz → t with an index map; accepted only if the span contains at least one digraph and the rewritten span is an entry of a folded Romanian list; factor × 2 |
| G3 | cleaned word list | `ro_common_clean` |
| G4 | names | `ro_names_ext` |
| G5 | places | `ro_places` |
| G6 | cultural + expressions | `ro_cultural`, `ro_expressions`, `ro_calendar` |
| G7 | leaked | `ro_leaked` (meter share M) |
| G8 | matchers + layouts + leet | mobile phone `07` + 8 digits; CNP structure (13 digits, first digit 1–8, valid date in positions 2–7); plate shapes (`B` + 2–3 digits + 3 letters, county code + 2 digits + 3 letters); Romanian Standard and Legacy (QWERTZ) adjacency graphs **added to** the existing graphs; the leet table **extended** with substitutions observed in M |

Matcher rules:
- Each matcher's guess estimate is documented in its source with a one-line justification.
- Check first whether the core date matcher already covers `dd.mm.yyyy`, `ddmmyyyy` and `dd-mm-yy`. Add a date
  matcher only for formats it misses.
- Before writing the custom matchers, read in the installed core how custom matchers declare matching, scoring
  and feedback. Test that a custom match really enters the optimal sequence (e.g. `Ionutz99` under G2).

Nesting requirements (keep them, or the comparison breaks):
1. No original entry is removed or given a worse rank.
2. The folded and digraph matchers are **added next to** the normal dictionary matcher.
3. Graphs and leet tables are extended, never replaced.
4. M-ZX-RO+ **also contains M-ZX-RO-CZ's pruned lists unchanged** (C11). Pruning renumbers ranks, so without
   them RO+ could give a higher estimate than RO-CZ.

Meters:
- `M-ZX-RO+` = RO-PKG + G1…G8 + the RO-CZ lists.
- `RO-PKG+norm` (for E6) = RO-PKG + G1 + G2 only.
- Ablations: RO-PKG + Gi alone, and RO+ − Gi, for i = 1…8 (16 configs, generated by a script).

Checks:
- `node:test` unit tests for each matcher, including:
  - `fetiță` typed as NFD matches the same word as NFC;
  - `ashley` is not split by G2;
  - `Ionutz99` and `pîine` are recognised;
  - a valid and an invalid CNP;
  - a plate and a phone number.

### C11: the Czech method on Romanian (M-ZX-RO-CZ)

Build:
- Read the pruning scripts in the local copy `../papers/_build/p4repo/zxcvbn-czech/data-scripts/` and port them
  exactly: drop words of 1–2 characters; drop a word when a shorter word plus brute force is cheaper. Do not
  invent rules. If a rule is unclear, write what you implemented in `deviations.md`.
- RO-CZ = RO-PKG + the **new** lists (G4–G7) stored in ASCII (folded) and pruned, the same layouts and matchers
  (G8), **no** normalisation and **no** digraph matcher, and no cleaned common-word list. The input password is
  not folded.
- D variants: `bridge/vendor/core-D{1000,100,10}/` are copies of the pinned core dist with only the D constant
  changed (`MIN_GUESSES_BEFORE_GROWING_SEQUENCE`). A test diffs each copy against the original and allows
  exactly that one change.
- Configs: RO-CZ at D = 10^4 (main) and D = 10^3 (secondary). RO+ at D ∈ {10^3, 10^2, 10} (E5, exploratory).

Checks:
- Re-measure the bundle-size check of the Czech repo (900 KB target), for reference only.

### C12: run all meters (`make meters`)

Build:
- Output: `results/meters/{dataset}/{meter}.parquet`. Real-password results go to `results/private/`.
- Meters: POLICY (both variants), BLOCK, ORIG, EN, RO-PKG, RO-CZ (two values of D), RO+ (four values of D),
  RO-PKG+norm, and the 16 ablations, on the three seeds and the real sample.
- **Nesting check on every password:** g must not increase along EN → RO-PKG → RO-CZ → RO+, nor along
  RO-PKG → ablation → RO+. Write violations to `results/tables/nesting_violations.csv`. Expect zero or very few;
  explain every one.

Checks:
- Row counts equal the dataset sizes.
- No NaN.
- The bridge output is the same on two runs (ignoring `ms`).

### C13: reference interface (student-supplied data, `src/ropw/reference.py`)

The student delivers `data/reference/guess_numbers.csv` (synthetic part committed, real part in
`results/private/`) with the columns:

```
password (NFC), attacker ∈ {A-EN, A-RO, A-ALL, A-JTR, A-PCFG, A-RO-novariants},
guess_number (integer ≥ 1, empty if not found), censored (bool), budget (integer), run ∈ {small, full}
```

plus `data/reference/probes.csv` (`attacker, probe, expected_position`) for the known-position check.

`reference.py`:
- Validates the schema.
- Computes G* (A-MIN over the five main attackers), the cut-at-10^9 variant and a no-leaked-data variant. The
  student marks which runs used no leaked data with a `no_leak` flag.
- Runs the design §7.2 checks, written to `results/tables/reference_checks.csv`:
  - no RANDOM password is found;
  - the probes are found at their position, or at an earlier identical candidate;
  - the small and full runs agree up to 10^8;
  - the share of passwords for which each attacker gives the minimum.

Checks: **analysis steps refuse to run if a check fails.**

### C14: metrics (`src/ropw/metrics.py`)

Build:
- Every definition of Section 4: ρ, τ, weighted ρ, DOR, SUR, levels, confusion matrix, reclassification, error
  size, Δs, Δx, η, floor attribution.

Checks:
- Hand-computed tiny cases.
- Spearman equals `scipy.stats.spearmanr`.
- Weighted Spearman equals the R wCorr fixture (generate 5 random weighted datasets once in R, save them as
  JSON, commit them).

### C15: statistics (`src/ropw/stats.py`)

Build:
- **Cluster bootstrap:** B = 10,000, seeded, resampling `cluster_id`. Paired comparisons use the same resample.
- **Wilson intervals** for proportions.
- **One-sided bootstrap p-value** for H1 "θ > 0": (1 + #{θ*_b ≤ 0}) / (B + 1).
- **CMH:** statsmodels `StratifiedTable`, strata = pair × rank band, without continuity correction. One-sided p =
  p/2 when the pooled odds ratio is > 1, else 1 − p/2.
- **Binomial:** `scipy.stats.binomtest`.
- **Wilcoxon:** `scipy.stats.wilcoxon(alternative="greater")`.
- **Holm:** `statsmodels.stats.multitest.multipletests(method="holm")` over T1–T12.

Tests (design Table 8):

| Test | θ or statistic (H1) |
|---|---|
| T1 | mean over the 3 pairs of [ρ_EN-twin − ρ_RO-twin] for M-ZX-EN > 0 |
| T2 | DOR_RO > DOR_EN for M-ZX-EN (CMH) |
| T3 | gap_EN − gap_PKG > 0, with gap = DOR_RO-twins − DOR_EN-twins |
| T4 | as T2 for M-ZX-RO-PKG |
| T5 | ρ_RO+ − ρ_PKG > 0 on the pooled open-class categories (all RO except RO-place and RO-cultural, and without the families) |
| T6 | share of EN twins moved farther from their reference level (PKG → RO+) < 0.01; θ = 0.01 − share |
| T7 | binomtest(k, n_RANDOM, 0.01, "less"), k = # RANDOM with score_RO+ < score_PKG |
| T8 | ρ_RO+ − ρ_CZ > 0 on RO-translit ∪ RO-inflected |
| T9 | binomtest(#families with Δs > 0 under PKG, n, 0.10, "greater") |
| T10 | Wilcoxon of η over digraph spellings under PKG |
| T11 | Wilcoxon of η over pre-1993 ASCII spellings under PKG |
| T12 | θ = 0.5 · mean Δx_PKG − mean Δx_PKG+norm > 0 |

Decision rules:
- T2, T3 and T4 are **undecided** if any group in the test has fewer than 100 weak passwords.
- Output: `results/tables/main_tests.csv` with `test, hypothesis, n, estimate, ci_low, ci_high, p_raw, p_holm,
  decision ∈ {pass, fail, undecided}, label = "illustrative"`.

### C16: experiments E1–E8 (`src/ropw/experiments/`)

Build one module per experiment, as in design §6 (with the meters of Table 7). Each module writes CSV tables to
`results/tables/eN_*.csv`.

- **E1:** guessing curves and the reference checks.
- **E2:** Δρ per twin pair.
- **E3:** DOR by category and meter, the language gap, and the floor vs knowledge split.
- **E4:** PKG, CZ and RO+ by category and pooled; the controls; CZ at D = 10^3.
- **E5:** add-one and remove-one ablations with CIs, and the D sweep (DOR and SUR). No formal test.
- **E6:** Δs, Δx and η by spelling form; accuracy on RO-translit and RO-inflected.
- **E7:** weighted ρ and DOR by reuse group on the real sample, and the diacritic profile. Unique passwords not
  found within 10^8: the claim passes if the lower bound of the 95% CI is > 10%.
- **E8:** gzip size of an esbuild bundle per meter, and median ms per password (warm, over the main dataset).

Robustness (design §7.3), behind flags, written to `results/tables/robustness_*.csv`:
- each attacker separately;
- the cut at 10^9;
- A-RO without variants;
- weak threshold 10^4 and 10^8;
- seeds 1 and 2;
- spelling shares reweighted to the V profile;
- the no-leaked-data reference.

Every robustness table states whether each main conclusion holds.

### C17: figures (`src/ropw/figures.py`)

Build the 11 figures of design §9.1 (the corrected list: Figure 2 uses EN, RO-PKG, RO-CZ and RO+; Figure 3 adds
POLICY and BLOCK; Figure 5 shows both add-one and remove-one).

Rules from §9.3:
- fixed colours per language group;
- fixed meter order;
- log10 axis for guesses;
- 95% CIs;
- n in every caption;
- synthetic and real results never in one panel.

Output: PDF and PNG with the same data, file names `figNN_short-name.{pdf,png}`.

Checks (§9.5):
- Every plotted value is read from a results table, and a test compares them.
- Fail on a missing category, a duplicate row or an unknown meter name.

### C18: one-command run

Build:
- `make all` = data → generate → meters → reference-check → analyse → figures.
- Write `results/run_manifest.json` with versions (Python, Node and npm packages, git commit), seeds, config
  hash and input checksums.

Checks:
- From a clean clone plus the private files, `make all` rebuilds every table and figure byte-identically,
  except timing.

### C19: worked examples and expert sheet

Build:
- `results/tables/worked_examples.csv`, for the chapter's concrete examples. For each meter: segments, score,
  log10 g, G*, level, and floor or knowledge. Examples:
  - `vacanta`, `vacanță`, `vacanţă`, `vacanta2001`;
  - `TeIubescMult`, `VacantaLaMare1!`;
  - `Andrei1999`, `Michael1999`;
  - `Ionutz99`, `fetitza`, `pîine`, `piine`;
  - `Steaua1986`;
  - one RANDOM password.
- `results/expert_review.xlsx` (or `.csv`): the 20 most-misjudged structures (design figure 6) with every meter's
  score and G*, and an empty "expert comment" column. **The student gives it to the supervisor or a security
  practitioner.** The chapter quotes only comments actually received. Never invent expert opinions.

### C20: the case-study chapter (`docs/report/`)

Build:
- `case_study.md` → `Case_Study.docx` with pandoc, reusing the Lab 3–4 / design styles (pass the design docx
  with `--reference-doc`). Also export to PDF.
- About 10 pages, English, simple language, little math (the student's preference). Every number is pulled from
  `results/tables/`; none is typed by hand.

Outline:
1. Purpose and scope: what is illustrated; full vs case-study scale (Section 2 table); tests are illustrative.
2. Data collected: sources and sizes; list overlap; the real-password filter precision; the profile of V.
3. Implementation: components and how they map to the design; tests; nesting-check result.
4. Reference quality (E1): guessing curves, the §7.2 checks, attacker diversity.
5. Results: E2 language effect; E3 dangerous errors (floor vs knowledge); E4 extension vs RO-PKG and the Czech
   method; E5 ablation; E6 spellings; E7 real passwords.
6. Worked examples (the table from C19, explained in plain words).
7. Interpretation: supervisor or expert comments, if received, plus comparison with the literature (Ur et al.,
   Golla & Dürmuth, Doucek et al.).
8. Deployment cost (E8).
9. Limitations of the case study and what changes at full scale.
10. Reproducibility: `make all`, versions, what is private.

Checks:
- The student reads it before it is committed.
- The chapter's numbers match the tables (script check).

## 7. Order, dependencies and what the student must do

```
C01 → C02 → C03 → C04 → C05 ─┬→ C06 → C07 → C08 → C09 → C10 → C11 → C12 ─┐
                             └→ (student: reference file from targets_all.txt) → C13 ┴→ C14 → C15 → C16 → C17 → C18 → C19 → C20
```

The student's manual tasks:
- Place the breach files in `data/breach/` (before C02 and C09).
- Produce the guess-number file and the probes (after C05; needed by C13).
- List the attacker input files in `data/reference/attacker_inputs.txt` (C08 check).
- Label the 300-password precision sample (C09).
- Review the hand-built lists (C08).
- Give the expert sheet to the supervisor (C19).
- Read the chapter (C20).

C14 and C15 can be written and tested before the reference file arrives: use a synthetic toy reference in the
tests only, never in `results/`.

## 8. Final checklist before the case study is handed in

- [ ] All checks of C01–C20 pass, and `pytest` plus `node --test` are green.
- [ ] `docs/deviations.md` lists every departure from the design, with its effect.
- [ ] No breach-derived file is tracked (`git ls-files | grep -iE 'breach|private'` gives only `.gitignore` lines).
- [ ] `results/tables/main_tests.csv` labels every test "illustrative".
- [ ] The figures follow §9.3, and the chapter's numbers match the tables.
- [ ] Nothing is pushed unless the student asked.
