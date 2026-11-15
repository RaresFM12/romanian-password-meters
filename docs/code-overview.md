# Code overview

A map of every source file in the project, what it does, and how the pieces fit.
Companion to `docs/Experimental_Modelling_and_Evaluation_Design.docx` (the full design). Tests and `__init__.py` files are omitted.

## The pipeline at a glance

```
sources ──▶ generator lists ──▶ synthetic passwords ─┐
(fetch)     (lexicon_build)      (generate)            ├─▶ targets ──▶ ATTACKERS ──────▶ guess numbers
                                                       │      (hashcat, John, pcfg)     (reference)
breach ───▶ ro_leaked / validation (breach) ──────────┘                                       │
                                                                                              ▼
meter lists (lexicon_build_meter, czech) ──▶ METERS (bridge) ──▶ scores ──▶ ANALYSE ──▶ tables + figures
                                                                            (metrics,
                                                                             stats, tests)
```

Accuracy = agreement between what a meter predicts and what the attackers actually
needed. The generator, meters and attackers are built from separate files so no
meter knows the test set by construction.

## How to run it
```
make setup        # venv + pinned deps
make data         # download public sources (FULL=1 adds dexonline)
make generate     # generator lexicons + synthetic datasets
make breach       # Romanian filter + split of RockYou (needs data/breach/rockyou-withcount.txt)
make meters       # meter lists + run every meter, ablations, D variants, real sample
make attack       # attacker wordlists + all attackers -> data/reference/guess_numbers.csv
make reference-check analyse literature deployment robustness figures manifest
make all          # the whole chain
make test         # Python and JavaScript tests
```

---

## Configuration & core helpers

**`config/case_study.yaml`** — The single source of every parameter: category sizes
(reduced to ~3,510), generator settings, attacker budgets, score thresholds, the weak
threshold, and the breach split. Nothing is hard-coded elsewhere; code reads it all
from here. `config/full.yaml` is the same file at full scale (~31,100).

**`src/ropw/config.py`** — Loads a YAML config and validates it (shares sum to 1, four
thresholds, twins reference real categories). It defines `REPO_ROOT`, used everywhere
for absolute paths. If the config is inconsistent it raises before anything runs.

**`src/ropw/normalize.py`** — The single source of truth for Romanian spelling:
NFC/NFD, the 1:1 fold-to-ASCII table, and the variant generators (cedilla, sh/tz
digraph, pre-1993 î, their ASCII forms). It also exports those tables to JSON so the
JavaScript meter folds identically. Every other module imports its `nfc`/`fold`/`to_*`
functions.

## Data sources & lexicons

**`src/ropw/fetch_sources.py`** — Downloads the public corpora listed in
`data/sources.yaml` into `data/raw/`, records their sha256 in a lock file, and verifies
the download size. It never downloads breach data — it only hashes the breach files you
supply. It skips what it can't fetch (bot-blocked) and reports failures.

**`src/ropw/lexicon.py`** — Defines `SeedList`: a frequency-ranked word list loaded
from a TSV, with the rank-band logic the generator samples from. Shorter lists use
fewer bands automatically. It is shared by the generator and the breach filter.

**`src/ropw/lexicon_build.py`** — Builds the nine **generator** seed lists from the
downloaded sources: dexonline lemmas and inflected forms (ranked by Leipzig frequency),
GeoNames places, BNC English, SSA names, Leipzig phrases, and Wikipedia names/culture.
It contains the streaming MySQL-dump parser for dexonline. It records which input files
each list read, so a test can prove the generator never reads a meter list.

**`src/ropw/ro_handbuilt.py`** — Hand-authored Romanian lists that aren't derivable
from downloads: name diminutives, holidays, football clubs/brands/slang, single-token
expressions (`teiubesc`), and the 41 counties with codes. These are the lists to
review. They feed the meter side only.

**`src/ropw/lexicon_build_meter.py`** — Builds the **meter** Romanian lists from the
`language-ro` package plus the hand-built source: cleaned/deduplicated common words,
extended names, calendar, cultural, expressions, and places (parsing the cp1250 SIRUTA
register for localities). It also writes the `language-ro` audit (48,511 / 2,425 / 317)
and the pairwise list-overlap report. Its inputs are kept disjoint from the generator's
(the separation rule).

## Synthetic dataset

**`src/ropw/generate.py`** — The password generator: builds every category (words,
names, places, phrases, leet, translit, inflected, cultural, passphrases, RANDOM, EN
twins, diacritic families) from a fixed seed, so output is byte-identical on re-run. It
handles the twin pairing, the spelling families (Table 4), and the structure parameters
(case, suffixes, diacritic shares). It also computes the `cluster_id` used for the
cluster bootstrap.

## Real (breach) passwords

**`src/ropw/breach.py`** — Filters RockYou for Romanian passwords and sends each account
at random to the meter list (`ro_leaked`, 40%), the attacker share (30%) or the
validation set (30%). It writes the precision sample to label by hand (never
overwriting labels that are already there). It produces `rockyou_attacker.txt` (RockYou
in frequency order without the meter and validation shares, for the wordlists) and
`pcfg_training.txt` (the same passwords, one line per account, for A-PCFG), so the
attackers can't trivially find the validation set. Only the aggregate profile is committed; everything with passwords is
gitignored.

## The meters

**`bridge/meters.mjs`** — The heart of the meter side: builds each zxcvbn-ts meter (EN,
RO-PKG, RO-CZ, RO+, RO-PKG+norm, the ablations, D-variants). A Romanian meter is
M-ZX-RO-PKG plus a set of resource groups; each dictionary group brings its Romanian
lists *and* their pruned ASCII copies (`cz_*`), so EN ⪯ PKG ⪯ CZ ⪯ RO+ holds and an
ablation really removes a whole group. The folding and sh/tz matchers always know the
`language-ro` words too. M-ZX-RO-CZ has every `cz_*` list and the pattern matchers but
no diacritic handling. D-variants load a patched core via an env var.

**`bridge/zx.mjs`** — The streaming entry point: reads `{id, password}` lines on stdin,
runs them through the chosen meter config, and writes one JSON result per line. It is
what the Python bridge spawns. `bridge/zx_orig.mjs` is the same for the original zxcvbn
4.4.2 (M-ZX-ORIG), mapping its old field names.

**`bridge/export_common.mjs`** / **`bridge/export_ro.mjs`** — Tiny scripts that dump the
npm packages' word lists to text files: the 49,233 common passwords (for M-BLOCK) and
the `language-ro` common words + first names (for the meter builder). They exist because
the Python side can't read the npm package data directly. They run once as a build step.

**`packages/zxcvbn-ro-extended/src/fold.mjs`** — The JavaScript mirror of
`normalize.py`, reading the same `tables.json`. It provides `foldWithMap`, which folds a
password while keeping an index map back to the original — so a match found on the
folded string is reported at the right position, and NFC and NFD inputs both work. It
also replicates zxcvbn's uppercase-variation factor.

**`packages/zxcvbn-ro-extended/src/dictionaries.mjs`** — Loads the meter TSV lists
(`item, rank, freq`; `rank` is the rank the meter uses) into exact dictionaries (arrays in
rank order, because zxcvbn ranks a word by its position) and a folded lookup map
(folded word → best rank) for the folding matcher, with the pre-1993 spelling of each
word at the same rank. `addFoldedArrays` does the same for plain zxcvbn word arrays.

**`packages/zxcvbn-ro-extended/src/matchers.mjs`** — The two original-contribution
matchers: `roFolded` (recognises a word written with any diacritic spelling, including
decomposed) and `roDigraph` (recognises the sh/tz spellings like `Ionutz`). Each emits a
dictionary-style match scored as rank × uppercase × a small diacritic/digraph factor.
`roDigraph` only fires when a rewritten span is a real Romanian word, so it won't split
`ashley`.

**`packages/zxcvbn-ro-extended/src/patterns.mjs`** — The G8 pattern matchers: Romanian
mobile phones (`07`+8 digits), CNPs (13 digits with a valid date), and licence plates.
Each is a regex matcher with a documented guess estimate. They complete the designed
meter but rarely change scores, since zxcvbn already estimates such strings cheaply.

**`src/ropw/meters/policy.py`** — M-POLICY, the composition-rule baseline: pass → score
4, fail → 0, in a normal (≥8 chars, ≥3 classes) and strict (≥12, all 4) variant. Length
is counted in NFC code points and Romanian letters count by case. It produces no guess
estimate, so it only feeds the rate metrics.

**`src/ropw/meters/block.py`** — M-BLOCK, the NIST-blocklist baseline: score 0 if the
password is one of the 49,233 common passwords, else 4. It asserts the expected count on
load. This is the minimum NIST requires, and it does badly (dangerous-error rate 0.90 on the
open-class Romanian passwords). The password is lower-cased before the lookup.

**`src/ropw/meters/zx_bridge.py`** — The Python→Node bridge: spawns `zx.mjs` for a meter
config, streams the passwords through it, and returns the results matched by id. It
routes ablation configs (`A+`/`A-`) and the original-zxcvbn meter, and can point at a
patched core for the D-variants. This is the only place Python talks to the JavaScript
meters.

**`src/ropw/czech.py`** — The pruning of `zxcvbn-czech` (`build_frequency_lists.py`):
short/rare tokens and one-letter repeats dropped, all lists filtered together (a token
stays only in the list where it comes first, ranks compacted), and a word dropped when a
shorter word + one brute-forced letter is cheaper. A test compares it with the original
algorithm written out literally. It builds ASCII-folded, pruned copies of every Romanian
meter list for M-ZX-RO-CZ.

**`bridge/make_cores.sh`** — Copies of the zxcvbn cores that every meter loads
(`bridge/vendor/`): zxcvbn-ts with D = 10000/1000/100/10 and the original zxcvbn 4.4.2,
all with the reference year fixed (zxcvbn otherwise reads it from the clock). It checks
that every patch was applied. Run by `make cores`.

## Attacker reference

**`src/ropw/export_wordlists.py`** — Builds the attacker wordlists (`en`, `ro`, `all`,
and the top-5,000 lists for combinations/PRINCE) from the generator lists, RockYou and
the attacker share; each Romanian word is followed by its spelling variants in a fixed
order. It also writes `targets_all.txt` (synthetic + validation passwords, private).

**`scripts/run_attackers.sh`** — Runs the attackers of design Table 6 (hashcat
`--stdout` for A-EN/A-RO/A-ALL/A-RO-NOVAR, John for A-JTR, pcfg_cracker for A-PCFG,
trained on `data/breach/pcfg_training.txt`), the small run with the known-position
probes, and the full runs, then calls `guess_numbers`. See `reference-runbook.md`.

**`scripts/pcfg_stdout.py`** — Runs the pcfg_cracker guesser so that its guesses go to
stdout (and its banner to stderr).

**`src/ropw/guess_numbers.py`** — Helper steps of the script: the probe positions, the
probes read from the small run, and `guess_numbers.csv` (first position of every target
per attacker and run), plus the measured position of every probe.

**`src/ropw/reference.py`** — Validates the attacker reference: checks the schema,
computes A-MIN (ties credit every attacker at the minimum), and runs the §7.2 checks:
no random found, probes found at their measured position (or earlier, when the same
candidate occurs earlier in the stream), small = full run up to 10^8
(fails when there is no small run), and attacker diversity (`attacker_shares.csv`).
Analysis refuses to run until these pass.

## Running & analysis

**`src/ropw/run_meters.py`** — Runs every meter over the three synthetic datasets
(`--all-seeds`), the ablations and D-variants (`--extras`) and the real validation sample
(`--real`, written to `results/private/`), and checks the nesting EN → RO-PKG → RO-CZ →
RO+ for every password.

**`src/ropw/metrics.py`** — The metric definitions: Spearman (censored tied at top),
Kendall, weighted Spearman (wCorr), DOR, SUR, levels, confusion matrix, reclassification,
error size, spelling spreads, η, and floor attribution. Every number in the results
traces to a function here. It is the file to check that each metric matches the design's
formula.

**`src/ropw/stats.py`** — The statistical machinery: the cluster bootstrap, Wilson
intervals, the Cochran-Mantel-Haenszel test, exact binomial and Wilcoxon tests, and the
Holm correction. The twelve confirmatory tests are built on these. It is deliberately
thin wrappers around scipy/statsmodels so each test is auditable.

**`src/ropw/analyse.py`** — The experiments E1–E7: accuracy (with CIs, Kendall, signed
and absolute log error), DOR by category, the twin pairs, floor attribution for every
meter, spelling forms and η, confusion matrices, reclassification, ablation (with paired
CIs), D-sweep, the 20 most misjudged structures, guessing curves, the real passwords,
and the twelve tests T1–T12 with Holm over all twelve and a verdict per hypothesis.

**`src/ropw/deployment.py`** — E8: gzip size of the code and the word lists each meter
loads (words in rank order, plus the rank for the Romanian lists),
and the median and 95th-percentile time per password over the main dataset.

**`src/ropw/robustness.py`** — §7.3: the key results (ρ and DOR of RO-PKG and RO+,
the DOR gap) under a weak threshold of 10^4 and 10^8, each attacker alone, the cut at
10^9, and the two extra seeds, with a column saying whether each conclusion holds.

**`src/ropw/figures.py`** — The 11 figures of design §9.1, drawn only from the saved
tables (except the scatter, which plots the raw estimates), with fixed meter order and
colours, sample sizes and CIs on every panel, and the §9.5 output checks.

**`src/ropw/manifest.py`** — Writes `run_manifest.json`: the config hash, seeds,
Python/npm versions, and git commit, so a run is reproducible. It is the last step of
`make all`. It is how you prove which exact inputs produced the results.

## Where to look first when checking design fidelity

1. `metrics.py` — each metric's formula.
2. `analyse.py` — the twelve tests T1–T12 and every result table.
3. the design docx §5–§7, next to those two files.
