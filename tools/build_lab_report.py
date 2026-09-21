from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


def load(name: str) -> dict[str, Any] | None:
    path = ARTIFACTS / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def simulation_summary(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    telemetry = data.get("telemetry", {})
    return {
        "games": data.get("games"),
        "agents": data.get("agents"),
        "wins": data.get("wins"),
        "win_rates": data.get("win_rates"),
        "first_player_win_rate": data.get("first_player_win_rate"),
        "mean_turns": data.get("mean_turns"),
        "max_turns": data.get("max_turns"),
        "passes": telemetry.get("passes"),
        "battles": telemetry.get("battles"),
        "actions": telemetry.get("actions"),
        "decisions": telemetry.get("decisions"),
        "policy_sources": telemetry.get("policy_sources"),
    }


def main() -> None:
    health = load("balance-health.json")
    static = load("balance-report.json")
    selfplay = load("heuristic-selfplay.json") or load("pages-selfplay.json")
    policy = load("mccfr-policy.json")
    verification = load("mccfr-verification.json")

    if health is None:
        raise SystemExit("balance-health.json is required")
    if static is None:
        raise SystemExit("balance-report.json is required")

    static_by_card = {
        row["card"]: row
        for row in static.get("card_static_marginals", [])
    }
    for card in health.get("cards", []):
        card["static"] = static_by_card.get(card["id"])

    matchup_files = {
        "heuristic_selfplay": "heuristic-selfplay.json",
        "heuristic_vs_random": "heuristic-vs-random.json",
        "random_vs_heuristic": "random-vs-heuristic.json",
        "mccfr_vs_heuristic": "mccfr-vs-heuristic.json",
        "heuristic_vs_mccfr": "heuristic-vs-mccfr.json",
    }
    matchups = {
        key: simulation_summary(load(filename))
        for key, filename in matchup_files.items()
    }
    if matchups["heuristic_selfplay"] is None:
        matchups["heuristic_selfplay"] = simulation_summary(selfplay)

    mccfr: dict[str, Any] | None = None
    if policy is not None:
        mccfr = {
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
        }

    raw_telemetry = selfplay.get("telemetry") if selfplay is not None else None

    downloads = sorted(
        path.name
        for path in ARTIFACTS.glob("*.json")
    )

    report = {
        "schema_version": 1,
        "health": health,
        "static": static,
        "matchups": matchups,
        "mccfr": mccfr,
        "verification": verification,
        "raw_telemetry": raw_telemetry,
        "downloads": downloads,
    }

    output = ARTIFACTS / "lab-report.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
