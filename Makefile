.PHONY: install native-build browser-build verify verify-algorithms test test-fast test-integration simulate balance experiments full-lab pages browser-parity

# Make is a small human-facing lifecycle surface.
# Variations belong in *_ARGS or the underlying runner, not new targets.

WORKERS ?= 8
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python)
PYTEST ?= $(PYTHON) -m pytest -n $(WORKERS)

install:
	$(PYTHON) -m pip install -e '.[dev]'

# Required after changing .pyx/.pxi files.
native-build:
	$(PYTHON) tools/build_native_protocol.py
	$(PYTHON) tools/build_heuristic_weights.py
	$(PYTHON) tools/build_native_fingerprint.py
	$(PYTHON) setup.py build_ext --inplace
	$(PYTHON) -c 'from longwar.native_search import ismcts_backend; ismcts_backend(); print("Native source/binary fingerprint: OK")'

browser-build:
	$(PYTHON) tools/build_native_protocol.py --check
	$(PYTHON) tools/build_heuristic_weights.py --check
	$(PYTHON) tools/build_browser_runtime.py

test:
	$(PYTEST) -q --durations=10

test-fast:
	$(PYTEST) -q --tb=short -m "not algorithm and not integration"

test-integration:
	$(PYTEST) -q -m integration --durations=10

browser-parity:
	@$(PYTHON) tools/build_native_protocol.py --check
	@$(PYTHON) tools/build_heuristic_weights.py --check
	@$(PYTHON) tools/build_web_protocol.py --check
	@mkdir -p artifacts/logs
	@echo "Browser/native parity..."
	@rm -f artifacts/logs/browser-parity.log
	@{ \
		$(PYTHON) tools/check_web_static.py && \
		$(PYTHON) tools/build_pages.py && \
		$(PYTHON) tools/check_web_static.py --dist dist && \
		$(PYTHON) tools/build_browser_contract.py --output artifacts/browser-engine-contract.json && \
		node tools/check_browser_engine.mjs --contract artifacts/browser-engine-contract.json; \
	} > artifacts/logs/browser-parity.log 2>&1 || { \
		echo "Browser/native parity: FAILED"; \
		$(PYTHON) -c 'from pathlib import Path; p=Path("artifacts/logs/browser-parity.log"); lines=p.read_text(errors="replace").splitlines()[-60:]; print("\n".join((line[:500] + ("..." if len(line) > 500 else "")) for line in lines))'; \
		exit 1; \
	}
	@echo "Browser/native parity: OK (log: artifacts/logs/browser-parity.log)"

verify:
	$(MAKE) native-build
	$(PYTHON) tools/build_native_protocol.py --check
	$(PYTHON) tools/build_heuristic_weights.py --check
	$(PYTHON) tools/build_web_protocol.py --check
	$(PYTHON) -m ruff check src tools tests --select F821,F822,F823
	$(PYTHON) tools/run_experiments.py validate-data
	$(MAKE) test-fast
	$(MAKE) browser-parity

verify-algorithms:
	$(PYTEST) -q --tb=short -m "algorithm"
	$(PYTHON) tools/run_experiments.py validate

SIMULATE_ARGS ?= --games 25 --seed 99 --jobs $(WORKERS) --agent-a heuristic --agent-b heuristic
simulate:
	$(PYTHON) tools/simulate.py $(SIMULATE_ARGS)

# Canonical Balance Lab: planning-capable ISMCTS evidence, generated locally
# and committed for GitHub Pages. Override BALANCE_ARGS for larger/special runs.
BALANCE_PRESET ?= quick
BALANCE_ARGS ?= --agent ismcts --games 24 --jobs $(WORKERS) --publish-lab --skip-card-screen
balance:
	$(PYTHON) tools/run_experiments.py balance --preset $(BALANCE_PRESET) $(BALANCE_ARGS)

EXPERIMENT ?= strength-bench
EXPERIMENT_ARGS ?=
experiments: verify-algorithms
	systemd-inhibit --what=sleep:idle:handle-lid-switch --why="The Long War experiments" --mode=block \
		$(PYTHON) tools/run_experiments.py $(EXPERIMENT) $(EXPERIMENT_ARGS)

FULL_LAB_ARGS ?=
full-lab:
	systemd-inhibit --what=sleep:idle:handle-lid-switch --why="The Long War full Balance Lab" --mode=block \
		$(PYTHON) tools/full_lab.py $(FULL_LAB_ARGS)

pages:
	$(PYTHON) tools/build_web_protocol.py --check
	$(PYTHON) tools/build_pages.py
	$(PYTHON) tools/build_rulebook_pdf.py
