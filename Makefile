.PHONY: install native-build browser-build verify verify-algorithms test test-fast test-integration simulate balance experiments pages browser-parity

# Make is a small human-facing lifecycle surface.
# Variations belong in *_ARGS or the underlying runner, not new targets.

install:
	python -m pip install -e '.[dev]'

# Required after changing .pyx/.pxi files.
native-build:
	python setup.py build_ext --inplace

browser-build:
	python tools/build_browser_runtime.py

test:
	python -m pytest -q --durations=10

test-fast:
	python -m pytest -q -m "not algorithm and not integration and not legacy_rule_experiment" --durations=10

test-integration:
	python -m pytest -q -m integration --durations=10

browser-parity:
	python tools/build_pages.py
	python tools/build_browser_contract.py --output artifacts/browser-engine-contract.json
	node tools/check_browser_engine.mjs --contract artifacts/browser-engine-contract.json

verify:
	python tools/run_experiments.py validate-data
	$(MAKE) test-fast
	$(MAKE) browser-parity

verify-algorithms:
	python -m pytest -q -m "algorithm and not legacy_rule_experiment" --durations=10
	python -m pytest -q tests/test_experiment_workflow.py -m "not integration"
	python tools/run_experiments.py validate

SIMULATE_ARGS ?= --games 25 --seed 99 --agent-a heuristic --agent-b heuristic
simulate:
	python tools/simulate.py $(SIMULATE_ARGS)

BALANCE_PRESET ?= quick
BALANCE_ARGS ?=
balance:
	python tools/run_experiments.py balance --preset $(BALANCE_PRESET) $(BALANCE_ARGS)

EXPERIMENT ?= suite
EXPERIMENT_ARGS ?=
experiments: verify-algorithms
	systemd-inhibit --what=sleep:idle:handle-lid-switch --why="The Long War experiments" --mode=block \
		python tools/run_experiments.py $(EXPERIMENT) $(EXPERIMENT_ARGS)

pages:
	python tools/build_pages.py
