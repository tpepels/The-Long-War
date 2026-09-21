from __future__ import annotations

import argparse
import json
from pathlib import Path

from longwar.mccfr_verification import verify_kuhn

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/mccfr-verification.json"),
    )
    args = parser.parse_args()

    report = verify_kuhn(iterations=args.iterations, seed=args.seed)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Benchmark: {report['benchmark']}")
    print(f"Iterations: {report['iterations']}")
    print(f"Known P0 value: {report['known_p0_value']:.6f}")
    print(f"Learned P0 value: {report['learned_p0_value']:.6f}")
    print(f"Absolute value error: {report['absolute_value_error']:.6f}")
    print(f"Exploitability: {report['exploitability']:.6f}")
    print(f"Information sets: {report['information_sets']}")
    print(f"VERIFIED: {report['passed']}")
    print(f"Wrote {output.relative_to(ROOT)}")

    if not report["passed"]:
        raise SystemExit("MCCFR verification failed")


if __name__ == "__main__":
    main()
