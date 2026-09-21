.PHONY: install test test-fast test-algorithm test-integration check mccfr-smoke simulate-smoke pages

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

check: test-fast test-algorithm test-integration
	python tools/balance_report.py
	python tools/simulate.py --games 50 --seed 1701 --agent-a heuristic --agent-b heuristic
	python tools/analyze_telemetry.py --simulation artifacts/simulation-report.json
	python tools/build_pages.py

mccfr-smoke:
	python tools/train_mccfr.py --iterations 5 --depth 2 --output artifacts/mccfr-smoke.json
	python tools/simulate.py --games 5 --seed 4401 --agent-a mccfr --policy-a artifacts/mccfr-smoke.json --agent-b heuristic --output artifacts/mccfr-smoke-match.json

simulate-smoke:
	python tools/simulate.py --games 25 --seed 99 --agent-a heuristic --agent-b heuristic

pages:
	python tools/build_pages.py
