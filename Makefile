.PHONY: install native-build browser-build web-protocol verify verify-algorithms test test-fast test-integration simulate balance experiments full-lab pages browser-parity

# Make is a small human-facing lifecycle surface.
# Variations belong in *_ARGS or the underlying runner, not new targets.

WORKERS ?= 8
PYTEST ?= python -m pytest -n $(WORKERS)

install:
	python -m pip install -e '.[dev]'

# Required after changing .pyx/.pxi files.
native-build:
	python tools/build_native_protocol.py
	python tools/build_heuristic_weights.py
	python setup.py build_ext --inplace

browser-build:
	python tools/build_native_protocol.py --check
	python tools/build_heuristic_weights.py --check
	python tools/build_browser_runtime.py

web-protocol:
	python tools/build_web_protocol.py

test:
	$(PYTEST) -q --durations=10

test-fast:
	$(PYTEST) -q --tb=short -m "not algorithm and not integration"

test-integration:
	$(PYTEST) -q -m integration --durations=10

browser-parity:
	@python tools/build_native_protocol.py --check
	@python tools/build_heuristic_weights.py --check
	@python tools/build_web_protocol.py --check
	@mkdir -p artifacts/logs
	@echo "Browser/native parity..."
	@rm -f artifacts/logs/browser-parity.log
	@{ \
		python tools/check_web_static.py && \
		python tools/build_pages.py && \
		python tools/check_web_static.py --dist dist && \
		python tools/build_browser_contract.py --output artifacts/browser-engine-contract.json && \
		node tools/check_browser_engine.mjs --contract artifacts/browser-engine-contract.json; \
	} > artifacts/logs/browser-parity.log 2>&1 || { \
		echo "Browser/native parity: FAILED"; \
		python -c 'from pathlib import Path; p=Path("artifacts/logs/browser-parity.log"); lines=p.read_text(errors="replace").splitlines()[-60:]; print("\n".join((line[:500] + ("..." if len(line) > 500 else "")) for line in lines))'; \
		exit 1; \
	}
	@echo "Browser/native parity: OK (log: artifacts/logs/browser-parity.log)"

verify:
	python tools/build_native_protocol.py --check
	python tools/build_heuristic_weights.py --check
	python tools/build_web_protocol.py --check
	python -m ruff check src tools tests --select F821,F822,F823
	python tools/run_experiments.py validate-data
	$(MAKE) test-fast
	$(MAKE) browser-parity

verify-algorithms:
	$(PYTEST) -q --tb=short -m "algorithm"
	python tools/run_experiments.py validate

SIMULATE_ARGS ?= --games 25 --seed 99 --jobs $(WORKERS) --agent-a heuristic --agent-b heuristic
simulate:
	python tools/simulate.py $(SIMULATE_ARGS)

# Canonical Balance Lab: planning-capable ISMCTS evidence, generated locally
# and committed for GitHub Pages. Override BALANCE_ARGS for larger/special runs.
BALANCE_PRESET ?= quick
BALANCE_ARGS ?= --agent ismcts --games 24 --jobs $(WORKERS) --publish-lab --skip-card-screen
balance:
	python tools/run_experiments.py balance --preset $(BALANCE_PRESET) $(BALANCE_ARGS)

EXPERIMENT ?= strength-bench
EXPERIMENT_ARGS ?=
experiments: verify-algorithms
	systemd-inhibit --what=sleep:idle:handle-lid-switch --why="The Long War experiments" --mode=block \
		python tools/run_experiments.py $(EXPERIMENT) $(EXPERIMENT_ARGS)

FULL_LAB_ARGS ?=
full-lab:
	systemd-inhibit --what=sleep:idle:handle-lid-switch --why="The Long War full Balance Lab" --mode=block \
		python tools/full_lab.py $(FULL_LAB_ARGS)

pages:
	python tools/build_web_protocol.py --check
	python tools/build_pages.py
	python tools/build_rulebook_pdf.py
