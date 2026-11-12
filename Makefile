# Case study pipeline. See docs/case-study-implementation-guide.md.
# Every step reads config/$(CONFIG).yaml; switch scale with CONFIG=full.

PY := /opt/homebrew/bin/python3.12
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
CONFIG ?= case_study

.PHONY: setup test data generate meters reference-check analyse figures all clean

setup: $(VENV)/.stamp        ## create the venv and install pinned deps
$(VENV)/.stamp: requirements.txt
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	touch $@

test: setup                  ## run the Python test suite
	$(PYTHON) -m pytest -q

data:                        ## fetch public sources (C02); breach files are supplied by hand
	$(PYTHON) -m ropw.fetch_sources --config config/$(CONFIG).yaml

generate:                    ## build lexicons and the synthetic datasets (C04, C05)
	$(PYTHON) -m ropw.generate --config config/$(CONFIG).yaml

meters:                      ## run every meter over every dataset (C12)
	$(PYTHON) -m ropw.run_meters --config config/$(CONFIG).yaml

reference-check:             ## validate the student-supplied guess-number file (C13)
	$(PYTHON) -m ropw.reference --config config/$(CONFIG).yaml

analyse:                     ## metrics, experiments, tests (C14-C16)
	$(PYTHON) -m ropw.analyse --config config/$(CONFIG).yaml

figures:                     ## all figures (C17)
	$(PYTHON) -m ropw.figures --config config/$(CONFIG).yaml

all: generate meters reference-check analyse figures  ## full pipeline (needs the reference file)

clean:
	rm -rf results/tables/* results/figures/* results/private/*

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-16s %s\n", $$1, $$2}'
