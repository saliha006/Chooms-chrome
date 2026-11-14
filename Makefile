PY ?= .venv/bin/python

.PHONY: mock run rebaseline bench test

mock:
	$(PY) run.py --mock

run:
	$(PY) run.py

rebaseline:
	$(PY) -m perception.rebaseline

bench:
	$(PY) -m bench.benchmark

test:
	$(PY) -m pytest common perception bench reasoner
