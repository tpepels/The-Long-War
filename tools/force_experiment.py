from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_force_draw_experiment.py"
VALIDATION_ROOT = ROOT / "artifacts" / "force-validation"
BENCH_ROOT = ROOT / "artifacts" / "force-benchmark"


def run_command(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    printable = " ".join(command)
    print(f"$ {printable}", flush=True)
    return subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def require_cython() -> None:
    try:
        import longwar._alphabeta_accel  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Cython alpha-beta extension is not available.\n"
            "Run: make force-setup"
        ) from exc
    print("Cython alpha-beta extension: OK")


def normalized_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload = copy.deepcopy(payload)

    strategic = payload.get("strategic_config", {})
    strategic.pop("backend_requested", None)

    telemetry = payload.get("telemetry", {})
    telemetry.pop("search_backends", None)

    return payload


def parity_case(mode: str, *, seed: int) -> None:
    print(f"\nBackend parity: {mode} draw")
    python_dir = VALIDATION_ROOT / f"{mode}-python"
    cython_dir = VALIDATION_ROOT / f"{mode}-cython"

    common = [
        "--preset",
        "quick",
        "--games",
        "2",
        "--jobs",
        "1",
        "--mode",
        mode,
        "--deck",
        "reference",
        "--belief-samples",
        "2",
        "--depth",
        "3",
        "--width",
        "4",
        "--node-budget",
        "3000",
        "--seed",
        str(seed),
    ]

    run_command(
        [
            sys.executable,
            str(RUNNER),
            *common,
            "--backend",
            "python",
            "--output-dir",
            str(python_dir),
        ]
    )
    run_command(
        [
            sys.executable,
            str(RUNNER),
            *common,
            "--backend",
            "cython",
            "--output-dir",
            str(cython_dir),
        ]
    )

    filename = f"{mode}-reference.json"
    python_payload = normalized_payload(python_dir / filename)
    cython_payload = normalized_payload(cython_dir / filename)

    if python_payload != cython_payload:
        left = VALIDATION_ROOT / f"{mode}-normalized-python.json"
        right = VALIDATION_ROOT / f"{mode}-normalized-cython.json"
        left.parent.mkdir(parents=True, exist_ok=True)
        left.write_text(json.dumps(python_payload, indent=2) + "\n", encoding="utf-8")
        right.write_text(json.dumps(cython_payload, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(
            f"Backend parity FAILED for {mode}.\n"
            f"Normalized outputs written to:\n  {left}\n  {right}"
        )

    print(f"Backend parity {mode}: OK")


def validate() -> None:
    print("The Long War — Force/draw experiment validation")
    print("=" * 52)
    require_cython()

    print("\nFocused rules and strategic-search tests")
    run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_force_draw_candidate.py",
            "tests/test_strategic_heuristic.py",
        ]
    )

    parity_case("automatic", seed=26092334)
    parity_case("paid", seed=26092334)

    print("\nVALIDATION PASSED")
    print("Rules tests passed and Python/Cython produced identical fixed-seed simulations.")


def benchmark(games: int) -> None:
    require_cython()
    BENCH_ROOT.mkdir(parents=True, exist_ok=True)

    timings: dict[str, float] = {}
    for backend in ("python", "cython"):
        output = BENCH_ROOT / backend
        command = [
            sys.executable,
            str(RUNNER),
            "--preset",
            "deep",
            "--games",
            str(games),
            "--jobs",
            "1",
            "--mode",
            "automatic",
            "--deck",
            "reference",
            "--backend",
            backend,
            "--output-dir",
            str(output),
        ]
        print(f"\nBenchmarking {backend} backend...")
        start = time.perf_counter()
        run_command(command)
        timings[backend] = time.perf_counter() - start

    py = timings["python"]
    cy = timings["cython"]
    print("\nBenchmark")
    print(f"Python : {py:.2f}s")
    print(f"Cython : {cy:.2f}s")
    if cy > 0:
        print(f"Speedup: {py / cy:.2f}x")


def run_experiment(args: argparse.Namespace) -> None:
    command = [
        sys.executable,
        str(RUNNER),
        "--preset",
        args.preset,
        "--jobs",
        str(args.jobs),
        "--backend",
        args.backend,
        "--mode",
        args.mode,
        "--deck",
        args.deck,
    ]
    if args.games is not None:
        command.extend(["--games", str(args.games)])
    if args.output_dir is not None:
        command.extend(["--output-dir", str(args.output_dir)])
    run_command(command)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Single entry point for the Force-rich draw experiment."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "validate",
        help="Run focused tests plus exact Python/Cython simulation parity.",
    )

    bench = sub.add_parser(
        "bench",
        help="Benchmark Python and Cython on the same deep-search cell.",
    )
    bench.add_argument("--games", type=int, default=3)

    run = sub.add_parser(
        "run",
        help="Run the local draw experiment.",
    )
    run.add_argument("--preset", choices=("quick", "deep", "max"), default="deep")
    run.add_argument("--games", type=int)
    run.add_argument("--jobs", type=int, default=4)
    run.add_argument("--backend", choices=("auto", "cython", "python"), default="cython")
    run.add_argument("--mode", choices=("both", "automatic", "paid"), default="both")
    run.add_argument("--deck", choices=("all", "reference", "avaros", "mara", "sera"), default="all")
    run.add_argument("--output-dir", type=Path)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "validate":
        validate()
    elif args.command == "bench":
        benchmark(args.games)
    elif args.command == "run":
        run_experiment(args)
    else:
        raise AssertionError(args.command)


if __name__ == "__main__":
    main()
