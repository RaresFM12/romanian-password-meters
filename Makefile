
PY := /opt/homebrew/bin/python3.12
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
CONFIG ?= case_study

.PHONY: setup test data generate breach blocklist meter-lists meters wordlists attack \
	cores reference-check analyse literature deployment robustness figures manifest all clean help

setup: $(VENV)/.stamp        ## create the venv and install pinned deps
$(VENV)/.stamp: requirements.txt
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	touch $@

test: setup                  ## run the Python and JavaScript tests
	$(PYTHON) -m pytest -q
	cd packages/zxcvbn-ro-extended && node --test test/*.test.mjs

data:                        ## fetch public sources; FULL=1 also fetches dexonline
	$(PYTHON) -m ropw.fetch_sources --config config/$(CONFIG).yaml $(if $(FULL),--include-large,)

generate:                    ## build generator lexicons + synthetic datasets
	$(PYTHON) -m ropw.lexicon_build --config config/$(CONFIG).yaml
	$(PYTHON) -m ropw.generate --config config/$(CONFIG).yaml

breach:                      ## Romanian filter + 40/30/30 split of RockYou (needs data/breach/rockyou-withcount.txt)
	$(PYTHON) -m ropw.breach --config config/$(CONFIG).yaml

blocklist: data/lexicon/meter/common.txt  ## export the M-BLOCK common-password list
data/lexicon/meter/common.txt:
	node bridge/export_common.mjs $@

meter-lists: blocklist       ## build meter RO lists + Czech lists
	node bridge/export_ro.mjs data/lexicon/meter
	$(PYTHON) -m ropw.lexicon_build_meter
	$(PYTHON) -m ropw.czech

cores:                       ## vendored zxcvbn cores (D variants, fixed reference year)
	bridge/make_cores.sh $$($(PYTHON) -c "from ropw.config import load_config; print(load_config('config/$(CONFIG).yaml')['scoring']['reference_year'])")

meters: cores meter-lists    ## run every meter over every dataset
	$(PYTHON) -m ropw.run_meters --config config/$(CONFIG).yaml --all-seeds --extras --real

wordlists:                   ## attacker wordlists + targets_all.txt
	$(PYTHON) -m ropw.export_wordlists

attack: wordlists            ## run the attackers (hashcat --stdout, John, pcfg_cracker), about 70 min at 1e9
	scripts/run_attackers.sh $(CONFIG)

reference-check:             ## validate the guess-number file (design section 7.2 checks)
	$(PYTHON) -m ropw.reference --config config/$(CONFIG).yaml

analyse:                     ## metrics, experiments, tests
	$(PYTHON) -m ropw.analyse --config config/$(CONFIG).yaml

literature:                  ## Golla & Duermuth online protocol on RockYou (top 10,000)
	$(PYTHON) -m ropw.literature_check --config config/$(CONFIG).yaml

deployment:                  ## bundle size + timing per meter (E8)
	$(PYTHON) -m ropw.deployment --config config/$(CONFIG).yaml

robustness:                  ## robustness variations (section 7.3)
	$(PYTHON) -m ropw.robustness --config config/$(CONFIG).yaml

figures:                     ## all figures
	$(PYTHON) -m ropw.figures --config config/$(CONFIG).yaml

manifest:                    ## write results/run_manifest.json
	$(PYTHON) -m ropw.manifest --config config/$(CONFIG).yaml

all: generate breach meters attack reference-check analyse literature deployment robustness figures manifest  ## full pipeline

clean:
	rm -rf results/tables/*.csv results/figures/* results/meters/* results/private/*

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n", $$1, $$2}'
