# Producing the attacker reference

The reference (design Section 3.2 and Table 6) is built by one script:

```
.venv/bin/python -m ropw.export_wordlists     # wordlists + targets_all.txt
scripts/run_attackers.sh case_study           # the five attackers + A-RO-NOVAR (about 70 minutes)
scripts/run_attackers.sh case_study A-ALL     # run only some attackers again
make reference-check                          # the Section 7.2 checks
```

`hashcat --stdout` works on this Mac: only hashcat's cracking mode hangs (the Metal
backend), and producing candidates needs no GPU. So the rule attacks use hashcat as
the design says, and John the Ripper is used for A-JTR.

## What each attacker guesses

Each attacker is one fixed stream of candidates, made of stages one after the other.
The stream is cut at the budget (`reference.run_budget` in the config: 10^9 for the
case study, 10^10 for the full study).

| Attacker | Stages |
|---|---|
| A-EN | hashcat `best66.rule` on `en.txt`, then `OneRuleToRuleThemAll.rule` on `en.txt` |
| A-RO | hashcat `best66.rule` on `ro.txt`; two-word combinations of the top 5,000 Romanian words (`hashcat -a 1`); 3-4-word PRINCE chains of the same words, without and with spaces (John, at most 5% of the budget each); `OneRuleToRuleThemAll` on `ro.txt` |
| A-ALL | as A-RO on `all.txt` (Romanian list first); combinations and PRINCE on the top 5,000 Romanian and English words |
| A-JTR | John: Jumbo rules on `all.txt` (60% of the budget), PRINCE on the first 100,000 words (20%), then incremental mode |
| A-RO-NOVAR | robustness only: as A-RO on `ro_novar.txt` (each word only in its generator spelling) |
| A-PCFG | pcfg_cracker (in `$PCFG_DIR`, default `~/tools/pcfg_cracker`) trained on `data/breach/pcfg_training.txt` (RockYou without the meter and validation shares, one line per account, written by `ropw.breach`); budget `min(run_budget, 10^9)`. `scripts/pcfg_stdout.py` sends the banner to stderr, so stdout has only guesses |

Wordlists (`data/reference/wordlists/`, built by `ropw.export_wordlists`):
- `en.txt`: the English generator lists (BNC words, SSA names, Leipzig phrases),
  then RockYou without the meter and validation shares. This is the same order as
  `ro.txt` (generator lists, then breach data): hashcat applies every rule to one
  word before the next word, so a list placed after 14.5 million RockYou lines would
  be reached about 10^9 guesses later, and the English twins would look stronger
  than the Romanian ones only because of the order of the list;
- `ro.txt`: every Romanian generator word followed by its spelling variants (ASCII,
  cedilla, sh/tz, pre-1993, pre-1993 ASCII), names, places, clubs, phrases (with
  and without spaces), and the attacker share A of the Romanian breach passwords;
- `all.txt`: `ro.txt` then `en.txt`.

English phrases are in `en.txt` with and without spaces, like the Romanian ones, and
every diacritic spelling also capitalised and in capitals (the rules only change ASCII
letters).

## How a guess number is measured

The candidates go through `awk`, which prints `line:candidate` for every target it
sees. The first line of a target is its guess number. The wordlists are NFC and the
rules work on bytes, so a rule never creates a non-NFC string: exact matching
against the NFC targets is the same as matching after NFC (Equation 1).

## The checks (design 7.2)

- **Stages and length.** Each John call has its own session file (two John processes
  sharing `~/.john/john.rec` made one of them exit at once, silently). Every stage writes
  its exit code to `<attacker>.<run>.status` (0, or 141/120 when `head` stops it) and
  every run its length to `<attacker>.<run>.count`; `ropw.guess_numbers` refuses a run
  with a failed stage or fewer candidates than the budget. A stage that `head` stops
  before it starts also reports 141, so the status file cannot tell a stage that was cut
  from one that was never reached: at 10^9, A-ALL's `best66` stage alone produces
  978 million candidates, so A-ALL is `best66` plus the first 22 million combinations, and
  its PRINCE and OneRule stages are not reached (at the design budget of 10^10 they are).

- **Probes.** Before the full run, a small run (the first 10^8 guesses) reads the
  candidates at 150 random positions. 50 of the usable ones (valid UTF-8, no duplicate),
  drawn at random with a fixed seed, are the probes (`data/reference/probes.csv`). The full run searches for the targets and the
  probes; each probe must be found at its position, or earlier if the same candidate
  appears earlier.
- **Repeatability.** The small run also records its matches; small and full runs must
  give the same guess numbers up to 10^8.
- **Random passwords** must never be found; **attacker diversity** is reported in
  `results/tables/attacker_shares.csv`.

`ropw.analyse` refuses to run when one of these checks fails (use `--force` only for an
exploratory look).

## Files written

- `data/reference/found/<attacker>.{small,full}.found` (matches, gitignored)
- `data/reference/guess_numbers.csv`, `runs.json`, `probes.csv`
- `data/reference/attack_manifest.txt` (date, budget, tool versions, sha256 of the rule
  files and wordlists)
