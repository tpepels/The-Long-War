from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from longwar.fingerprint import current_game_fingerprint
from longwar.health import simulation_summary

from longwar.reference_decks import MCCFR_PROFILES as PROFILES

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def policy_coverage(simulation: dict[str, Any]) -> dict[str, Any]:
    sources = simulation.get("telemetry", {}).get("policy_sources", {})
    mccfr = int(sources.get("mccfr", 0) or 0)
    fallback = sum(
        int(count or 0)
        for source, count in sources.items()
        if str(source).startswith(("fallback:", "guard-fallback:"))
    )
    total = mccfr + fallback
    return {
        "sources": dict(sorted(sources.items())),
        "mccfr_decisions": mccfr,
        "heuristic_fallback_decisions": fallback,
        "mccfr_coverage_rate": mccfr / total if total else None,
        "heuristic_fallback_rate": fallback / total if total else None,
    }


def seat_swapped_evaluation(
    forward: dict[str, Any],
    reverse: dict[str, Any],
) -> dict[str, Any]:
    """Combine mirrored evaluations using decisive games only."""
    forward_games = int(forward.get("games", 0))
    reverse_games = int(reverse.get("games", 0))
    forward_censored = int(forward.get("censored_games", 0))
    reverse_censored = int(reverse.get("censored_games", 0))
    attempted_games = forward_games + reverse_games
    censored_games = forward_censored + reverse_censored
    decisive_games = max(0, attempted_games - censored_games)
    mccfr_wins = int(forward.get("wins", [0, 0])[0]) + int(
        reverse.get("wins", [0, 0])[1]
    )
    return {
        "seat_swapped_mccfr_win_rate": (
            mccfr_wins / decisive_games if decisive_games else None
        ),
        "games": attempted_games,
        "decisive_games": decisive_games,
        "censored_games": censored_games,
        "censor_rate": (
            censored_games / attempted_games if attempted_games else 0.0
        ),
    }


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

        policy_path = ARTIFACTS / f"mccfr-policy-{profile_id}.json"
        policy_bytes = policy_path.read_bytes()
        policy = json.loads(policy_bytes)
        policy_fingerprint = hashlib.sha256(policy_bytes).hexdigest()[:16]
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

        combined_evaluation = seat_swapped_evaluation(forward, reverse)

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
                    "policy_fingerprint": policy_fingerprint,
                },
                "evaluation": {
                    "mccfr_vs_heuristic": simulation_summary(forward),
                    "heuristic_vs_mccfr": simulation_summary(reverse),
                    "mccfr_vs_heuristic_policy_coverage": policy_coverage(forward),
                    "heuristic_vs_mccfr_policy_coverage": policy_coverage(reverse),
                    **combined_evaluation,
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
