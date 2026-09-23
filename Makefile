.PHONY: install test test-fast test-algorithm test-integration check check-mccfr check-native-mccfr benchmark-mccfr mccfr-smoke verify-mccfr simulate-smoke pages force-setup force-check force-bench force-quick force-run force-max

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

check: test-fast test-integration
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


# Force-rich draw experiment: local-only convenience targets.
force-setup:
	python -m pip install -e '.[dev]'

force-check:
	python tools/force_experiment.py validate

force-bench:
	python tools/force_experiment.py bench --jobs 8

force-quick:
	python tools/force_experiment.py run --preset quick --backend cython --jobs 8

force-run:
	python tools/force_experiment.py run --preset deep --backend cython --jobs 8

force-max:
	python tools/force_experiment.py run --preset max --backend cython --jobs 8
