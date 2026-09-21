from __future__ import annotations

import argparse
import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.counterfactual import run_counterfactual_experiment

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contexts", type=int, default=3)
    parser.add_argument("--games-per-context", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260921)
    parser.add_argument("--agent", choices=["heuristic", "random"], default="heuristic")
    parser.add_argument("--bootstrap-resamples", type=int, default=2000)
    parser.add_argument("--no-pairs", action="store_true")
    parser.add_argument("--no-triples", action="store_true")
    parser.add_argument(
        "--cards",
        nargs="*",
        default=None,
        help="Optional subset of canonical card ids",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/counterfactual-balance.json"),
    )
    args = parser.parse_args()

    data = load_card_file(ROOT / "cards" / "cards.json")
    report = run_counterfactual_experiment(
        data,
        contexts=args.contexts,
        games_per_context=args.games_per_context,
        seed=args.seed,
        agent_name=args.agent,
        include_pairs=not args.no_pairs,
        include_legend_triples=not args.no_triples,
        bootstrap_resamples=args.bootstrap_resamples,
        card_ids=args.cards,
    )

    output = resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Policy: {report['policy']}")
    print(f"Samples: {report['samples']}")
    print(f"Conditions/sample: {report['conditions_evaluated_per_sample']}")
    print(f"Total matches: {report['total_matches']}")
    print(f"Cards: {len(report['cards'])}")
    print(f"Pairs: {len(report['pairs'])}")
    print(f"Legend triples: {len(report['triples'])}")
    if report["cards"]:
        top = report["cards"][0]
        print(
            "Largest card effect: "
            f"{top['title']} {top['delta_win_probability']:+.3f} "
            f"CI [{top['ci95'][0]:+.3f}, {top['ci95'][1]:+.3f}]"
        )
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
