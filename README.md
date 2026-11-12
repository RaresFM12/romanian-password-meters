# How Well Do Password Strength Meters Work for Romanian Passwords?

Research project evaluating password strength meters (zxcvbn-ts) on Romanian
passwords: diacritics (ă â î ș ț) and their encoding variants, Romanian
dictionaries, and whether the existing `@zxcvbn-ts/language-ro` package improves
accuracy. This repository holds the **case study**: the full experimental design
run at reduced scale to illustrate the method.

## Documents
- `Experimental_Modelling_and_Evaluation_Design.docx` — the experimental design (the version reviewed by the supervisor).
- `docs/case-study-implementation-guide.md` — the step-by-step build plan (C01–C20).
- `docs/research-plan.md` — the full research plan (v2.4).
- `docs/deviations.md` — every departure from the design.

## Layout
- `config/` — all parameters; `case_study.yaml` (reduced) and `full.yaml` (full scale).
- `src/ropw/` — the Python pipeline.
- `bridge/` — the Node bridge to zxcvbn-ts and the meter configs.
- `packages/zxcvbn-ro-extended/` — the Romanian-aware extension.
- `data/` — lexicons and datasets. **`data/raw/`, `data/breach/` and anything derived from a breach are never committed.**
- `results/` — tables and figures (aggregates only; `results/private/` is gitignored).
- `scripts/preliminary/` — the earlier `language-ro` audit scripts.

## Running
```
make setup      # create .venv (Python 3.12) and install pinned deps
make test       # run the test suite
make all        # full pipeline (needs the reference file, see below)
```
Switch to the full study with `make all CONFIG=full`.

## The attack-based reference
The guess numbers from the five attackers are produced separately and placed in
`data/reference/guess_numbers.csv` (format in `docs/case-study-implementation-guide.md`,
step C13). Everything downstream of that file is built and run here.

## Privacy
No real password, breach-derived list or table ever enters git. Only aggregates
(counts, rates, correlations) are committed.

## Status
In progress (university research project, 2026).
