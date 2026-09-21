from __future__ import annotations

import argparse
import json
from pathlib import Path

from longwar.cards import load_card_file
from longwar.targeted_counterfactual import run_targeted_online_validation

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--broad",
        type=Path,
        default=Path("artifacts/counterfactual-balance.json"),
    )
    parser.add_argument("--contexts", type=int, default=2)
    parser.add_argument("--games-per-context", type=int, default=2)
    parser.add_argument("--online-iterations", type=int, default=4)
    parser.add_argument("--online-depth", type=int, default=2)
    parser.add_argument("--max-cards", type=int, default=2)
    parser.add_argument("--max-pairs", type=int, default=2)
    parser.add_argument("--max-triples", type=int, default=2)
    parser.add_argument("--minimum-abs-effect", type=float, default=0.05)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-top", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/targeted-online-counterfactual.json"),
    )
    args = parser.parse_args()

    card_data = load_card_file(ROOT / "cards" / "cards.json")
    broad = json.loads(resolve(args.broad).read_text(encoding="utf-8"))
    report = run_targeted_online_validation(
        card_data,
        broad,
        contexts=args.contexts,
        games_per_context=args.games_per_context,
        online_iterations=args.online_iterations,
        online_depth=args.online_depth,
        max_cards=args.max_cards,
        max_pairs=args.max_pairs,
        max_triples=args.max_triples,
        minimum_abs_effect=args.minimum_abs_effect,
        bootstrap_resamples=args.bootstrap_resamples,
        force_top=args.force_top,
    )

    output = resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Targets selected: {report['selection']['targets_selected']}")
    print(f"Samples/target: {report['samples']}")
    print(f"Online iterations: {report['online_iterations']}")
    print(f"Online depth: {report['online_depth']}")
    print(f"Total online matches: {report['total_matches']}")
    for row in report["targets"]:
        print(
            f"  {row['kind']} {row['title']}: "
            f"broad={row['broad']['effect']:+.3f} "
            f"online={row['online']['effect']:+.3f} "
            f"CI=[{row['online']['ci95'][0]:+.3f}, {row['online']['ci95'][1]:+.3f}] "
            f"{row['confirmation']}"
        )
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
