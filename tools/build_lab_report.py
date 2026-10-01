from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from longwar.fingerprint import current_game_fingerprint
from longwar.health import simulation_summary
from longwar.rules import GameRules

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"

_DASHBOARD_OMIT_KEYS = frozenset({
    "game_outcomes",
    "failed_game_outcomes",
    "recent_actions",
})


def compact_dashboard_payload(value: Any) -> Any:
    """Remove bulky per-game diagnostics from data embedded in the dashboard."""
    if isinstance(value, dict):
        return {
            key: compact_dashboard_payload(item)
            for key, item in value.items()
            if key not in _DASHBOARD_OMIT_KEYS
        }
    if isinstance(value, list):
        return [compact_dashboard_payload(item) for item in value]
    return value


def load(name: str) -> dict[str, Any] | None:
    path = ARTIFACTS / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def serialized_rule_metadata(rules: GameRules) -> dict[str, object]:
    """Serialize the complete canonical rule schema for artifact provenance."""
    return rules.simulation_metadata()


def canonical_variant(data: dict[str, Any]) -> bool:
    """A source fingerprint alone cannot distinguish an experimental ruleset."""
    variant = data.get("simulation_variant")
    if not variant:
        return True  # Static/causal/policy artifacts have no simulation variant.

    card_file = variant.get("card_file")
    if card_file and (ROOT / card_file).resolve() != (ROOT / "cards/cards.json").resolve():
        return False

    expected = serialized_rule_metadata(GameRules.standard())
    if any(key not in variant for key in expected):
        return False
    return all(variant[key] == value for key, value in expected.items())


TRAJECTORY_FIELDS = (
    "command_start",
    "command_remaining",
    "command_before_collapse",
    "first_signal_command",
    "occupied_positions",
    "active_fronts",
    "contested_fronts",
    "completed_formations",
    "incomplete_formations_end",
    "eventual_completion_rate_for_forces_deployed",
    "cards_played",
    "legal_actions",
    "hand_size",
    "deck_size",
)


def progression_trajectory(
    progression: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Compare the first and latest observed Battle buckets without grading them."""
    if not progression:
        return None
    by_battle = progression.get("by_battle") or {}
    observed = [
        key
        for key in ("1", "2", "3", "4-7", "8+")
        if int((by_battle.get(key) or {}).get("battles", 0) or 0) > 0
    ]
    if not observed:
        return None

    early_key = observed[0]
    late_key = observed[-1]
    early = by_battle[early_key]
    late = by_battle[late_key]
    metrics: dict[str, dict[str, float | int | None]] = {}
    for field in TRAJECTORY_FIELDS:
        early_value = early.get(field)
        late_value = late.get(field)
        delta = None
        if early_value is not None and late_value is not None:
            delta = float(late_value) - float(early_value)
        metrics[field] = {
            "early": early_value,
            "late": late_value,
            "delta": delta,
        }

    return {
        "observed_buckets": observed,
        "early_battle": early_key,
        "late_battle": late_key,
        "metrics": metrics,
    }


def main() -> None:
    game_fingerprint = current_game_fingerprint()
    stale_files: set[str] = set()

    def current(
        name: str,
        *,
        track_stale: bool = True,
    ) -> dict[str, Any] | None:
        data = load(name)
        if data is None:
            return None
        if data.get("game_fingerprint") != game_fingerprint:
            if track_stale:
                stale_files.add(name)
            return None
        if not canonical_variant(data):
            if track_stale:
                stale_files.add(name)
            return None
        return data

    # Derived health reports carry the source simulation's fingerprint. They
    # need the same freshness check as their underlying match telemetry.
    health = current("balance-health.json")
    static = current("balance-report.json")
    selfplay = current("balance-selfplay.json")
    progression_selfplay = current("progression-selfplay.json")
    progression_profiles_artifact = compact_dashboard_payload(
        current("progression-profiles.json")
    )
    mccfr_suite = current("mccfr-suite.json")
    verification = current("mccfr-verification.json")
    solver_strength = current("solver-strength.json")
    counterfactual = current("counterfactual-balance.json")
    targeted = current("targeted-online-counterfactual.json")
    run_summary = current("balance-run-summary.json")
    narrative_ablation = load("narrative-command-ablation.json")
    if (
        narrative_ablation is not None
        and narrative_ablation.get("game_fingerprint") != game_fingerprint
    ):
        stale_files.add("narrative-command-ablation.json")
        narrative_ablation = None

    balance_comparisons = compact_dashboard_payload(
        load("balance-comparisons.json")
    )
    if (
        balance_comparisons is not None
        and balance_comparisons.get("game_fingerprint") != game_fingerprint
    ):
        stale_files.add("balance-comparisons.json")
        balance_comparisons = None

    if health is None:
        raise SystemExit("A current balance-health.json is required; regenerate its source simulation and health report")
    if static is None:
        raise SystemExit("A current balance-report.json is required; regenerate the static report")

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
        "unobserved": -1,
        "dark_green": 0,
        "green": 1,
        "yellow": 2,
        "orange": 3,
        "red": 4,
    }
    for card in health.get("cards", []):
        card["static"] = static_by_card.get(card["id"])
        card["observational_balance_level"] = card["balance_level"]
        card["balance_evidence_source"] = "observational"
        causal = causal_by_card.get(card["id"])
        card["counterfactual"] = causal
        card["targeted_online"] = targeted_by_card.get(card["id"])
        card["screening_balance_level"] = (
            causal.get("level") if causal is not None else None
        )
        card["strategic_validation"] = (
            card["targeted_online"].get("confirmation")
            if card["targeted_online"] is not None
            else None
        )

        # The broad heuristic A/B sweep is a screen, not strong-play
        # confirmation. It may promote an otherwise healthy card to Watch, but
        # red/orange causal claims require targeted online-MCCFR evidence.
        if causal is not None and int(causal.get("samples", 0)) >= 12:
            causal_level = causal.get("level", "green")
            if (
                causal_level in {"yellow", "orange", "red"}
                and level_rank.get(card["balance_level"], 1)
                < level_rank["yellow"]
            ):
                card["balance_level"] = "yellow"
                card["balance_label"] = "Watch"
                card["balance_direction"] = "heuristic_counterfactual_screen"
                card["balance_evidence_source"] = "heuristic_screen"

        online = card["targeted_online"]
        if online is not None:
            confirmation = online.get("confirmation")
            online_samples = int(online.get("online", {}).get("samples", 0))
            online_level = online.get("online", {}).get("level", "green")
            if (
                confirmation in {"confirmed", "reversed"}
                and online_samples >= 8
            ):
                # A statistically resolved online result is strategic evidence
                # whether it agrees with the screen or reverses it.
                if level_rank.get(online_level, 1) > level_rank.get(
                    card["balance_level"],
                    1,
                ):
                    card["balance_level"] = online_level
                    card["balance_label"] = {
                        "red": "Critical",
                        "orange": "Needs balancing",
                        "yellow": "Watch",
                        "green": "Looks healthy",
                        "dark_green": "Well-supported healthy",
                    }[online_level]
                direction = online.get("online", {}).get(
                    "direction",
                    card["balance_direction"],
                )
                card["balance_direction"] = (
                    f"strategic_reversal:{direction}"
                    if confirmation == "reversed"
                    else direction
                )
                card["balance_evidence_source"] = "online_mccfr"
            elif (
                confirmation in {"direction_agrees", "inconclusive"}
                and causal is not None
                and causal.get("level") in {"yellow", "orange", "red"}
                and level_rank.get(card["balance_level"], 1)
                < level_rank["yellow"]
            ):
                card["balance_level"] = "yellow"
                card["balance_label"] = "Watch"
                card["balance_direction"] = "strategic_validation_inconclusive"
                card["balance_evidence_source"] = "heuristic_screen"

    matchup_files = {
        "canonical_selfplay": "balance-selfplay.json",
        "heuristic_selfplay": "heuristic-selfplay.json",
        "heuristic_vs_random": "heuristic-vs-random.json",
        "random_vs_heuristic": "random-vs-heuristic.json",
        "mccfr_vs_heuristic": "mccfr-vs-heuristic.json",
        "heuristic_vs_mccfr": "heuristic-vs-mccfr.json",
        "online_mccfr_vs_heuristic": "online-mccfr-vs-heuristic.json",
    }
    matchups = {
        key: simulation_summary(
            current(
                filename,
                track_stale=(key == "canonical_selfplay"),
            )
        )
        for key, filename in matchup_files.items()
    }
    raw_telemetry = (
        progression_selfplay.get("telemetry")
        if progression_selfplay is not None
        else None
    )
    progression = (
        raw_telemetry.get("progression")
        if raw_telemetry is not None
        else None
    )
    dashboard_telemetry = (
        {
            key: compact_dashboard_payload(raw_telemetry[key])
            for key in ("passes", "battles", "actions", "decisions")
            if key in raw_telemetry
        }
        if raw_telemetry is not None
        else None
    )
    progression_profiles = {}
    if progression_profiles_artifact is not None:
        for key, profile in progression_profiles_artifact.get("profiles", {}).items():
            row = dict(profile)
            row["trajectory"] = progression_trajectory(row.get("progression"))
            progression_profiles[key] = row

    trajectory = progression_trajectory(progression)
    progression_source = (
        {
            "label": progression_selfplay.get("_label"),
            "scope": progression_selfplay.get("progression_scope"),
            "games": progression_selfplay.get("games"),
            "decisive_games": progression_selfplay.get("decisive_games"),
            "censored_games": progression_selfplay.get("censored_games"),
        }
        if progression_selfplay is not None
        else None
    )

    card_titles = {
        card["id"]: card["title"]
        for card in health.get("cards", [])
    }
    observed_formations = {
        row["id"]: row
        for row in health.get("formations", [])
    }
    all_formations: list[dict[str, Any]] = []
    for row in static.get("all_static_formations", []):
        key = " | ".join((row["force"], row["bond"], row["name"]))
        observed = observed_formations.get(key)
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
                    for part in (row["force"], row["bond"], row["name"])
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
        merged.setdefault("force", row["force"])
        merged.setdefault("bond", row["bond"])
        merged.setdefault("name", row["name"])
        all_formations.append(merged)

    report = {
        "schema_version": 1,
        "game_fingerprint": game_fingerprint,
        "stale_evidence": sorted(stale_files),
        "health": health,
        "static": static,
        "matchups": matchups,
        "mccfr_suite": mccfr_suite,
        "verification": verification,
        "solver_strength": solver_strength,
        "counterfactual": counterfactual,
        "targeted_counterfactual": targeted,
        "run_summary": run_summary,
        "narrative_ablation": narrative_ablation,
        "balance_comparisons": balance_comparisons,
        "dashboard_telemetry": dashboard_telemetry,
        "progression": progression,
        "progression_trajectory": trajectory,
        "progression_source": progression_source,
        "progression_profiles": progression_profiles,
        "all_formations": all_formations,
    }

    output = ARTIFACTS / "lab-report.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        display_output = output.relative_to(ROOT)
    except ValueError:
        display_output = output
    print(f"Wrote {display_output}")


if __name__ == "__main__":
    main()
