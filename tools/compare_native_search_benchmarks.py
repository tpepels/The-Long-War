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


def paired_report(
    baseline: dict, candidate: dict,
    baseline_recheck: dict, candidate_recheck: dict
) -> str:
    """ABBA comparison separates steady-state effects from run-order noise."""
    for sample in (candidate, baseline_recheck, candidate_recheck):
        if sample["fixture"] != baseline["fixture"]:
            raise ValueError("Mismatched benchmark fixture")
        if sample["iterations"] != baseline["iterations"]:
            raise ValueError("Mismatched benchmark budget")
    names = baseline["measurements"]
    rows = [
        "# Alternating A-B-B-A native benchmark",
        "",
        f"Baseline `{baseline['revision'][:12]}`, "
        f"adapter `{candidate['revision'][:12]}`",
        "Same runner. Each of the four measurement passes includes five "
        "repeats of every workload.",
        "",
        "| Workload | First A→B ratio | Reverse B→A ratio | Geometric ratio |",
        "|---|---:|---:|---:|",
    ]
    for key in names:
        def rate(sample):
            return sample["measurements"][key]["median_units_per_second"]
        first = rate(candidate) / rate(baseline)
        reverse = rate(candidate_recheck) / rate(baseline_recheck)
        geometric = (first * reverse) ** 0.5
        rows.append(
            f"| {key} | {first:.3f}x | {reverse:.3f}x | {geometric:.3f}x |"
        )
    rows += [
        "",
        "A consistent slowdown in both orders is stronger evidence of an "
        "implementation regression than a slowdown only in the first order. "
        "This remains a microbenchmark, not a game-playing performance result.",
    ]
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--baseline-recheck", type=Path)
    parser.add_argument("--candidate-recheck", type=Path)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    candidate = json.loads(args.candidate.read_text())
    if args.baseline_recheck and args.candidate_recheck:
        b2 = json.loads(args.baseline_recheck.read_text())
        c2 = json.loads(args.candidate_recheck.read_text())
        result = paired_report(baseline, candidate, b2, c2)
    elif not args.baseline_recheck and not args.candidate_recheck:
        result = report(baseline, candidate)
    else:
        parser.error("provide both recheck paths")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(result + "\n")
    print(result)


if __name__ == "__main__":
    main()
