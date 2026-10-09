"""Summarize same-run native benchmark ratios without hiding uncertainty."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def report(baseline: dict, candidate: dict) -> str:
    if baseline["fixture"] != candidate["fixture"]:
        raise ValueError("Benchmark fixtures differ")
    if baseline["iterations"] != candidate["iterations"]:
        raise ValueError("Benchmark iteration counts differ")
    left = baseline["measurements"]
    right = candidate["measurements"]
    if left.keys() != right.keys():
        raise ValueError("Benchmark workloads differ")
    lines = [
        "# Native search throughput comparison",
        "",
        f"Baseline: `{baseline['revision'][:12]}`",
        f"Candidate: `{candidate['revision'][:12]}`",
        f"Fixture: `{candidate['fixture']}`, seed {candidate['seed']}, "
        f"{candidate['repeats']} timed repeats per workload.",
        "",
        "| Workload | Baseline units/s | Candidate units/s | Candidate / baseline |",
        "|---|---:|---:|---:|",
    ]
    ratios = {}
    for name in left:
        before = float(left[name]["median_units_per_second"])
        after = float(right[name]["median_units_per_second"])
        ratio = after / before
        ratios[name] = ratio
        lines.append(
            f"| {name} | {before:,.0f} | {after:,.0f} | {ratio:.3f}x |"
        )
    lines += [
        "",
        "Measurements are sequential on one CI runner, not simultaneous; "
        "runner noise, thermal behavior and differing package builds affect "
        "individual ratios. They are evidence of relative throughput, not "
        "a correctness proof or an exact production latency prediction.",
        "",
    ]
    if any(ratio < 0.80 for ratio in ratios.values()):
        lines.append(
            "**Review:** One or more median throughputs are over 20% below "
            "baseline. Repeat in alternating build order before attributing "
            "a regression to the adapter."
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    candidate = json.loads(args.candidate.read_text())
    result = report(baseline, candidate)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(result + "\n")
    print(result)


if __name__ == "__main__":
    main()
