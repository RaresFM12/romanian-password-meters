# How Well Do Password Strength Meters Work for Romanian Passwords?

Research project evaluating password strength meters (zxcvbn-ts) on Romanian
passwords: diacritics (ă â î ș ț) and their encoding variants, Romanian
dictionaries, and whether the existing `@zxcvbn-ts/language-ro` package improves
accuracy. The proposed meter, M-ZX-RO+, adds spelling normalisation, an sh/tz matcher
and Romanian word lists, and is compared with English zxcvbn, the existing package and
the Czech adaptation of zxcvbn.

## The three deliverables

| Requirement | Where |
|---|---|
| 1. Modelling the experimental part (data, experiments, validation, comparison, mathematical model) | chapter of the research report; the full design is `docs/Experimental_Modelling_and_Evaluation_Design.docx` |
| 2. Case study on initial data: code + "Case study" chapter | the code in this repository, the datasets in `data/synthetic/` and the results in `results/`; the chapter is in the research report |
| 3. Preparing validation on a real dataset: "Related work" chapter, metrics where similar or better results are expected | chapter of the research report; the validation on RockYou is implemented as experiment E7 (`src/ropw/breach.py`, `analyse.py`, `literature_check.py`) |

Supporting documents:
- `docs/Experimental_Modelling_and_Evaluation_Design.docx` — the full design that the code follows (section and table numbers in the code refer to it).
- `docs/code-overview.md` — what every source file does.
- `docs/reference-runbook.md` — how the attack-based reference is produced.

## Layout
- `config/` — all parameters; `case_study.yaml` (reduced, used for the results) and `full.yaml` (full scale).
- `src/ropw/` — the Python pipeline (data, generator, meters, analysis, figures).
- `bridge/` — the Node bridge to zxcvbn-ts and the meter configurations.
- `packages/zxcvbn-ro-extended/` — the Romanian extension of zxcvbn-ts (folding, sh/tz and pattern matchers).
- `scripts/run_attackers.sh` — the attackers (hashcat, John the Ripper, pcfg_cracker).
- `data/synthetic/` — the three synthetic datasets (main seed 20261111, extra seeds 1 and 2).
- `results/tables/`, `results/figures/` — every result of the case study (aggregates only).
- `tests/` — 119 Python tests; `packages/zxcvbn-ro-extended/test/` — 15 JavaScript tests.

## Running
```
make setup      # create .venv (Python 3.12) and install pinned deps
make test       # Python and JavaScript tests
make all        # full pipeline, attackers included (about 1.5 hours)
make help       # every step
```
`make all CONFIG=full` runs the full study. RockYou with the number of accounts per
password must be in `data/breach/rockyou-withcount.txt` (SecLists); hashcat, John the
Ripper (jumbo) and pcfg_cracker (`~/tools/pcfg_cracker`) must be installed.

## Privacy
No real password, breach-derived list or per-password result is in git
(`data/breach/`, `data/reference/` outputs and `results/private/` are ignored). Only
aggregates (counts, rates, correlations) are committed.
