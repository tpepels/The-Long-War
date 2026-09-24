.PHONY: install dev-setup native-build browser-build verify verify-cards verify-algorithms balance-quick balance-deep test test-fast test-algorithm test-integration check check-mccfr check-native-mccfr benchmark-mccfr mccfr-smoke verify-mccfr simulate-smoke pages browser-parity search-check ismcts-validate alpha-bench mcts-bench search-bench ismcts-match strength-bench overnight-search experiment-suite cardflow-quick cardflow-run cardflow-max

# Supported daily workflow. Keep native builds explicit after .pyx/.pxi changes.
verify: verify-cards test-fast browser-parity

verify-cards:
	python tools/run_experiments.py validate-data

verify-algorithms: test-algorithm
	python tools/run_experiments.py validate

balance-quick:
	python tools/run_experiments.py balance --preset quick

balance-deep:
	python tools/run_experiments.py balance --preset deep

install:
	python -m pip install -e '.[dev]'

test:
	python -m pytest -q --durations=10

test-fast:
	python -m pytest -q -m "not algorithm and not integration" --durations=10

test-algorithm:
	python -m pytest -q -m algorithm --durations=10

test-integration:
	python -m pytest -q -m integration --durations=10

check: test-fast test-integration browser-parity
	python tools/balance_report.py
	python tools/simulate.py --games 50 --seed 1701 --agent-a heuristic --agent-b heuristic
	python tools/analyze_telemetry.py --simulation artifacts/simulation-report.json
	python tools/build_pages.py

check-mccfr: check-native-mccfr test-algorithm verify-mccfr mccfr-smoke

check-native-mccfr:
	python -c "from longwar.mccfr_core import ACCELERATED, BACKEND; print(f'MCCFR backend: {BACKEND}'); assert ACCELERATED"

benchmark-mccfr:
	python tools/benchmark_mccfr.py --iterations 1000 --depth 2

mccfr-smoke:
	python tools/train_mccfr.py --iterations 5 --depth 2 --output artifacts/mccfr-smoke.json
	python tools/simulate.py --games 5 --seed 4401 --agent-a mccfr --policy-a artifacts/mccfr-smoke.json --agent-b heuristic --output artifacts/mccfr-smoke-match.json

verify-mccfr:
	python tools/verify_mccfr.py --iterations 30000

simulate-smoke:
	python tools/simulate.py --games 25 --seed 99 --agent-a heuristic --agent-b heuristic

pages:
	python tools/build_pages.py

browser-parity:
	python tools/build_pages.py
	python tools/build_browser_contract.py --output artifacts/browser-engine-contract.json
	node tools/check_browser_engine.mjs --contract artifacts/browser-engine-contract.json

browser-build:
	python tools/build_browser_runtime.py


# Local development and native-search workflow.
dev-setup:
	python -m pip install -e '.[dev]'

# Requires dev-setup once. This only recompiles native extensions in place.
native-build:
	python setup.py build_ext --inplace

search-check:
	python tools/run_experiments.py validate

ismcts-validate:
	python -m pytest -q tests/test_ismcts.py tests/test_ismcts_validation.py tests/test_fast_search_state.py tests/test_architecture_boundaries.py

alpha-bench:
	python tools/run_experiments.py bench

MCTS_BENCH_ARGS ?=
SEARCH_BENCH_ARGS ?=
ISMCTS_MATCH_GAMES ?= 24
ISMCTS_MATCH_JOBS ?= 8
ISMCTS_MATCH_SECONDS ?= 2
ISMCTS_MATCH_ARGS ?=
STRENGTH_BENCH_GAMES ?= 24
STRENGTH_BENCH_JOBS ?= 8
STRENGTH_BENCH_SECONDS ?= 2
STRENGTH_BENCH_ARGS ?=
OVERNIGHT_SEARCH_GAMES ?= 48
OVERNIGHT_SEARCH_JOBS ?= 8
OVERNIGHT_SEARCH_SECONDS ?= 2
OVERNIGHT_SEARCH_ARGS ?=

mcts-bench:
	python tools/run_experiments.py mcts-bench $(MCTS_BENCH_ARGS)

search-bench:
	python tools/run_experiments.py search-bench $(SEARCH_BENCH_ARGS)

# Decision-grade ISMCTS A/B: 24 games per deck/orientation =
# 192 games total, 96 independent mirrored deal pairs.
ismcts-match:
	python tools/run_experiments.py ismcts-match \
		--games $(ISMCTS_MATCH_GAMES) \
		--jobs $(ISMCTS_MATCH_JOBS) \
		--time-budget-seconds $(ISMCTS_MATCH_SECONDS) \
		$(ISMCTS_MATCH_ARGS)

strength-bench:
	python tools/run_experiments.py strength-bench \
		--games $(STRENGTH_BENCH_GAMES) \
		--jobs $(STRENGTH_BENCH_JOBS) \
		--time-budget-seconds $(STRENGTH_BENCH_SECONDS) \
		$(STRENGTH_BENCH_ARGS)

# Unattended structural ISMCTS battery. The runner checkpoints after every experiment.
overnight-search: verify-algorithms
	systemd-inhibit --what=sleep:idle:handle-lid-switch --why="The Long War overnight search experiments" --mode=block \
		python tools/run_experiments.py overnight-search \
		--games $(OVERNIGHT_SEARCH_GAMES) \
		--jobs $(OVERNIGHT_SEARCH_JOBS) \
		--time-budget-seconds $(OVERNIGHT_SEARCH_SECONDS) \
		$(OVERNIGHT_SEARCH_ARGS)

experiment-suite:
	python tools/run_experiments.py suite

# Card-flow experiment convenience targets.
cardflow-quick:
	python tools/run_experiments.py run --preset quick --backend cython --jobs 8

cardflow-run:
	python tools/run_experiments.py run --preset deep --backend cython --jobs 8

cardflow-max:
	python tools/run_experiments.py run --preset max --backend cython --jobs 8
