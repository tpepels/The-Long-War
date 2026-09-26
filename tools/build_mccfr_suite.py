from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from longwar.fingerprint import current_game_fingerprint
from longwar.health import simulation_summary

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

PROFILES = (
    ("reference", "Reference", "decks/mobility-open-bonds.json"),
    ("avaros", "Avaros Line", "decks/persistent-elite-heroes.json"),
    ("mara", "Mara Rear", "decks/narrative-command.json"),
    ("sera", "Sera Support", "decks/battlefield-control-stratagems.json"),
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    game_fingerprint = current_game_fingerprint()
    card_data = load(ROOT / "cards" / "cards.json")
    all_card_ids = {card["id"] for card in card_data["cards"]}
    covered: set[str] = set()
    profiles: list[dict[str, Any]] = []

    for profile_id, label, deck_path in PROFILES:
        deck = load(ROOT / deck_path)["cards"]
        deck_unique = set(deck)
        covered.update(deck_unique)

        policy = load(ARTIFACTS / f"mccfr-policy-{profile_id}.json")
        if policy.get("game_fingerprint") != game_fingerprint:
            raise SystemExit(f"Stale MCCFR policy for {profile_id}: rerun training for the current ruleset")
        forward = load(ARTIFACTS / f"mccfr-{profile_id}-vs-heuristic.json")
        reverse = load(ARTIFACTS / f"heuristic-vs-mccfr-{profile_id}.json")
        if (
            forward.get("game_fingerprint") != game_fingerprint
            or reverse.get("game_fingerprint") != game_fingerprint
        ):
            raise SystemExit(
                f"Stale MCCFR evaluation for {profile_id}: "
                "rerun evaluation for the current ruleset"
            )

        forward_games = int(forward.get("games", 0))
        reverse_games = int(reverse.get("games", 0))
        total_games = forward_games + reverse_games
        mccfr_wins = int(forward.get("wins", [0, 0])[0]) + int(
            reverse.get("wins", [0, 0])[1]
        )
        seat_swapped_rate = (
            mccfr_wins / total_games if total_games else None
        )

        profiles.append(
            {
                "id": profile_id,
                "label": label,
                "deck": deck_path,
                "deck_cards": len(deck),
                "deck_unique_cards": len(deck_unique),
                "policy": {
                    "algorithm": policy.get("algorithm"),
                    "iterations": policy.get("iterations"),
                    "traversals": policy.get("traversals"),
                    "max_depth": policy.get("max_depth"),
                    "information_sets": len(policy.get("infosets", {})),
                    "training_summary": policy.get("training_summary"),
                    "leaf_evaluator": policy.get("leaf_evaluator"),
                    "chance_sampling": policy.get("chance_sampling"),
                    "information_abstraction": policy.get("information_abstraction"),
                    "average_policy": policy.get("average_policy"),
                    "training_seed": policy.get("training_seed"),
                },
                "evaluation": {
                    "mccfr_vs_heuristic": simulation_summary(forward),
                    "heuristic_vs_mccfr": simulation_summary(reverse),
                    "seat_swapped_mccfr_win_rate": seat_swapped_rate,
                    "games": total_games,
                },
            }
        )

    payload = {
        "schema_version": 1,
        "game_fingerprint": game_fingerprint,
        "card_pool_size": len(all_card_ids),
        "covered_cards": len(covered),
        "coverage_fraction": len(covered) / len(all_card_ids),
        "missing_cards": sorted(all_card_ids - covered),
        "profiles": profiles,
    }

    output = ARTIFACTS / "mccfr-suite.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {output.relative_to(ROOT)} with "
        f"{len(profiles)} policies covering {len(covered)}/{len(all_card_ids)} cards"
    )


if __name__ == "__main__":
    main()
