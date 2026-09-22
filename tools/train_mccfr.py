from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.mccfr import MCCFRTrainer
from longwar.mccfr_core import BACKEND

ROOT = Path(__file__).resolve().parents[1]


def load_deck(path: Path) -> list[str]:
    resolved = path if path.is_absolute() else ROOT / path
    return list(json.loads(resolved.read_text(encoding="utf-8"))["cards"])


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--leaf-scale", type=float, default=100.0)
    parser.add_argument("--deck-a", type=Path, default=Path("decks/reference.json"))
    parser.add_argument("--deck-b", type=Path, default=Path("decks/reference.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/mccfr-policy.json"))
    args = parser.parse_args()

    engine = GameEngine(load_card_file(ROOT / "cards" / "cards.json"))
    trainer = MCCFRTrainer(
        engine,
        load_deck(args.deck_a),
        load_deck(args.deck_b),
        seed=args.seed,
        max_depth=args.depth,
        leaf_scale=args.leaf_scale,
    )
    summary = trainer.train(args.iterations)
    payload = trainer.policy_payload()
    payload["training_seed"] = args.seed
    payload["training_summary"] = asdict(summary)

    output = resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"Seed: {args.seed}")
    print(f"Backend: {BACKEND}")
    print(f"Algorithm: {payload['algorithm']}")
    print(f"Iterations: {summary.iterations}")
    print(f"Traversals: {summary.traversals}")
    print(f"Information sets: {summary.information_sets}")
    print(f"Depth: {summary.max_depth}")
    print(f"Mean sampled utility P0: {summary.mean_sampled_utility_p0:.4f}")
    print(f"Mean sampled utility P1: {summary.mean_sampled_utility_p1:.4f}")
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
