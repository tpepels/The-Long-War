from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from longwar.fingerprint import current_game_fingerprint

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
        "online_resolution": telemetry.get("online_resolution"),
        "online_config": data.get("online_config"),
    }


def main() -> None:
    game_fingerprint = current_game_fingerprint()
    stale_files: set[str] = set()

    def current(name: str) -> dict[str, Any] | None:
        data = load(name)
        if data is None:
            return None
        if data.get("game_fingerprint") != game_fingerprint:
            stale_files.add(name)
            return None
        return data

    # Static/card-health reports are generated in the current workflow. Dynamic
    # simulations and expensive solver/counterfactual artifacts must explicitly
    # match this ruleset before they may influence the lab.
    health = load("balance-health.json")
    static = load("balance-report.json")
    selfplay = current("heuristic-selfplay.json") or current("pages-selfplay.json")
    policy = current("mccfr-policy.json")
    mccfr_suite = current("mccfr-suite.json")
    verification = load("mccfr-verification.json")
    counterfactual = current("counterfactual-balance.json")
    targeted = current("targeted-online-counterfactual.json")

    if health is None:
        raise SystemExit("balance-health.json is required")
    if static is None:
        raise SystemExit("balance-report.json is required")

    static_by_card = {
        row["card"]: row
        for row in static.get("card_static_marginals", [])
    }
    causal_by_card = {
        row["id"]: row
        for row in (counterfactual or {}).get("cards", [])
    }
    targeted_by_card = {
        row["cards"][0]: row
        for row in (targeted or {}).get("cards", [])
        if row.get("cards")
    }
    level_rank = {
        "dark_green": 0,
        "green": 1,
        "yellow": 2,
        "orange": 3,
        "red": 4,
    }
    for card in health.get("cards", []):
        card["static"] = static_by_card.get(card["id"])
        card["observational_balance_level"] = card["balance_level"]
        causal = causal_by_card.get(card["id"])
        card["counterfactual"] = causal
        card["targeted_online"] = targeted_by_card.get(card["id"])
        if causal is not None and int(causal.get("samples", 0)) >= 12:
            causal_level = causal.get("level", "green")
            if level_rank.get(causal_level, 1) > level_rank.get(card["balance_level"], 1):
                card["balance_level"] = causal_level
                card["balance_label"] = {
                    "red": "Critical",
                    "orange": "Needs balancing",
                    "yellow": "Watch",
                    "green": "Looks healthy",
                    "dark_green": "Well-supported healthy",
                }[causal_level]
                card["balance_direction"] = causal.get("direction", card["balance_direction"])

        online = card["targeted_online"]
        if (
            online is not None
            and online.get("confirmation") == "confirmed"
            and int(online.get("online", {}).get("samples", 0)) >= 8
        ):
            online_level = online["online"].get("level", "green")
            if level_rank.get(online_level, 1) > level_rank.get(card["balance_level"], 1):
                card["balance_level"] = online_level
                card["balance_label"] = {
                    "red": "Critical",
                    "orange": "Needs balancing",
                    "yellow": "Watch",
                    "green": "Looks healthy",
                    "dark_green": "Well-supported healthy",
                }[online_level]
                card["balance_direction"] = online["online"].get(
                    "direction",
                    card["balance_direction"],
                )

    matchup_files = {
        "heuristic_selfplay": "heuristic-selfplay.json",
        "heuristic_vs_random": "heuristic-vs-random.json",
        "random_vs_heuristic": "random-vs-heuristic.json",
        "mccfr_vs_heuristic": "mccfr-vs-heuristic.json",
        "heuristic_vs_mccfr": "heuristic-vs-mccfr.json",
        "online_mccfr_vs_heuristic": "online-mccfr-vs-heuristic.json",
    }
    matchups = {
        key: simulation_summary(current(filename))
        for key, filename in matchup_files.items()
    }
    if matchups["heuristic_selfplay"] is None:
        matchups["heuristic_selfplay"] = simulation_summary(selfplay)

    mccfr: dict[str, Any] | None = None
    if policy is None and mccfr_suite and mccfr_suite.get("profiles"):
        policy = mccfr_suite["profiles"][0].get("policy")
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

    card_titles = {
        card["id"]: card["title"]
        for card in health.get("cards", [])
    }
    observed_legends = {
        row["id"]: row
        for row in health.get("legends", [])
    }
    all_legends: list[dict[str, Any]] = []
    for row in static.get("all_static_legends", []):
        key = " | ".join((row["subject"], row["link"], row["name"]))
        observed = observed_legends.get(key)
        if observed is not None:
            merged = dict(observed)
            merged["observed"] = True
            merged["static_strength"] = row["static_strength"]
            merged["static_z"] = row["z_score"]
        else:
            merged = {
                "id": key,
                "title": " — ".join(
                    card_titles.get(part, part)
                    for part in (row["subject"], row["link"], row["name"])
                ),
                "completions": 0,
                "games_seen": 0,
                "mean_strength_at_completion": None,
                "completion_strength_z": None,
                "win_rate_when_seen": None,
                "win_rate_when_seen_95": [None, None],
                "flags": [],
                "observed": False,
                "static_strength": row["static_strength"],
                "static_z": row["z_score"],
            }
        all_legends.append(merged)

    downloads = sorted(
        path.name
        for path in ARTIFACTS.glob("*.json")
        if path.name not in stale_files
    )

    report = {
        "schema_version": 1,
        "game_fingerprint": game_fingerprint,
        "stale_evidence": sorted(stale_files),
        "health": health,
        "static": static,
        "matchups": matchups,
        "mccfr": mccfr,
        "mccfr_suite": mccfr_suite,
        "verification": verification,
        "counterfactual": counterfactual,
        "targeted_counterfactual": targeted,
        "raw_telemetry": raw_telemetry,
        "all_legends": all_legends,
        "downloads": downloads,
    }

    output = ARTIFACTS / "lab-report.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
