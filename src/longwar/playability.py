from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

CARD_ACTIONS = (
    "PlayForce",
    "PlayBond",
    "PlayName",
    "PlayStory",
    "PlayStratagem",
)
CARD_LABELS = {
    "PlayForce": "Forces",
    "PlayBond": "Bonds",
    "PlayName": "Names",
    "PlayStory": "Stories",
    "PlayStratagem": "Stratagems",
}


def _ratio(a: float, b: float) -> float | None:
    return None if b == 0 else a / b


def build_playability_report(
    simulations: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate only playability metrics defined by the canonical war rules."""
    simulations = list(simulations)
    if not simulations:
        raise ValueError("At least one simulation report is required")

    fingerprints = {
        str(simulation["game_fingerprint"])
        for simulation in simulations
        if simulation.get("game_fingerprint")
    }
    if len(fingerprints) > 1:
        raise ValueError(
            "Simulation reports belong to different game fingerprints"
        )

    games = battles = draws = censored_games = pass_events = signal_events = decisions = 0
    final_battle_weight = final_battle_count = 0.0
    battle_reach: Counter[str] = Counter()
    match_actions = pass_hand_total = pass_dead_total = 0.0
    candidate_total = 0.0
    first_signal_events = 0.0
    actions: Counter[str] = Counter()
    card_totals: Counter[str] = Counter()
    combo_completions = 0
    by_simulation: list[dict[str, Any]] = []

    for index, simulation in enumerate(simulations):
        game_count = int(simulation["games"])
        telemetry = simulation["telemetry"]
        battle_count = int(telemetry["battles"]["count"])
        if game_count <= 0:
            raise ValueError(
                "Simulation reports must contain at least one attempted game"
            )

        run_actions = Counter(
            {
                name: int(count)
                for name, count in telemetry["actions"].items()
            }
        )
        cards_played = sum(
            run_actions[name]
            for name in CARD_ACTIONS
        )
        battle_actions = sum(run_actions.values())
        passes = telemetry["passes"]
        run_pass_events = int(passes["events"])
        run_signal_events = int(passes.get("signal_events", 0) or 0)

        run_censored = int(simulation.get("censored_games", 0) or 0)
        run_draws = int(simulation.get("draws", 0) or 0)
        games += game_count
        draws += run_draws
        censored_games += run_censored
        battles += battle_count
        match_actions += float(simulation["mean_turns"]) * game_count

        match_length = (
            telemetry.get("progression", {}).get("match_length", {})
        )
        final_battle = match_length.get("final_battle_number", {})
        final_count = int(final_battle.get("count", 0) or 0)
        if final_count:
            final_battle_weight += float(final_battle["mean"]) * final_count
            final_battle_count += final_count
        for key, row in match_length.get("battle_reach", {}).items():
            battle_reach[key] += int(row.get("matches", 0) or 0)
        actions.update(run_actions)
        pass_events += run_pass_events
        signal_events += run_signal_events
        pass_hand_total += (
            float(passes.get("mean_hand_size") or 0.0)
            * run_pass_events
        )
        pass_dead_total += (
            float(passes.get("mean_dead_cards") or 0.0)
            * run_pass_events
        )
        first_signal_events += (
            float(passes.get("first_signal_rate") or 0.0)
            * run_signal_events
        )

        for stats in telemetry.get("cards", {}).values():
            for field in (
                "draws",
                "plays",
                "turns_in_hand",
                "unplayable_turns",
                "held_on_pass",
                "dead_on_pass",
            ):
                card_totals[field] += int(stats.get(field, 0))

        combo_completions += sum(
            int(stats.get("completions", 0))
            for stats in telemetry.get("formation_combinations", {}).values()
        )

        heuristic = telemetry.get("decisions", {}).get("heuristic")
        if heuristic:
            run_decisions = int(heuristic.get("decisions", 0))
            decisions += run_decisions
            candidate_total += (
                float(
                    heuristic.get("mean_candidate_count") or 0.0
                )
                * run_decisions
            )

        by_simulation.append(
            {
                "label": str(
                    simulation.get("_label")
                    or f"simulation-{index + 1}"
                ),
                "games": game_count,
                "decisive_games": int(
                    simulation.get(
                        "decisive_games",
                        game_count - run_censored - run_draws,
                    )
                ),
                "draws": run_draws,
                "censored_games": run_censored,
                "mean_battles_per_match": (
                    battle_count / game_count
                ),
                "mean_resolved_battles_per_match": (
                    battle_count / game_count
                ),
                "mean_final_battle_reached": (
                    float(final_battle["mean"])
                    if final_count else None
                ),
                "mean_cards_played_per_battle": _ratio(
                    cards_played,
                    battle_count,
                ),
                "mean_cards_played_per_match": (
                    cards_played / game_count
                ),
                "mean_action_events_per_battle": _ratio(
                    battle_actions,
                    battle_count,
                ),
            }
        )

    cards_played = sum(actions[name] for name in CARD_ACTIONS)
    battle_actions = sum(actions.values())

    return {
        "schema_version": 2,
        "game_fingerprint": next(iter(fingerprints), None),
        "scope": {
            "simulation_reports": len(simulations),
            "games": games,
            "decisive_games": games - censored_games - draws,
            "draws": draws,
            "censored_games": censored_games,
            "battles": battles,
        },
        "match_pacing": {
            "mean_battles_per_match": battles / games,
            "mean_resolved_battles_per_match": battles / games,
            "mean_final_battle_reached": (
                final_battle_weight / final_battle_count
                if final_battle_count else None
            ),
            "battle_reach": {
                key: {
                    "matches": battle_reach[key],
                    "rate": battle_reach[key] / games,
                }
                for key in sorted(battle_reach, key=int)
            },
            "mean_action_events_per_match": match_actions / games,
            "mean_cards_played_per_match": cards_played / games,
        },
        "battle_pacing": {
            "mean_action_events_per_battle": _ratio(
                battle_actions,
                battles,
            ),
            "mean_action_events_per_player_battle": _ratio(
                battle_actions,
                2 * battles,
            ),
            "mean_cards_played_per_battle": _ratio(
                cards_played,
                battles,
            ),
            "mean_cards_played_per_player_battle": _ratio(
                cards_played,
                2 * battles,
            ),
            "mean_named_formations_created_per_battle": _ratio(
                combo_completions,
                battles,
            ),
            "mean_maneuvers_per_battle": _ratio(
                actions["Maneuver"],
                battles,
            ),
        },
        "card_mix": {
            CARD_LABELS[name]: {
                "count": actions[name],
                "share_of_card_plays": _ratio(
                    actions[name],
                    cards_played,
                ),
                "mean_per_battle": _ratio(actions[name], battles),
            }
            for name in CARD_ACTIONS
        },
        "draw": {
            "cards_drawn": card_totals["draws"],
            "mean_cards_drawn_per_battle": _ratio(
                card_totals["draws"],
                battles,
            ),
        },
        "stratagem": {
            "plays": actions["PlayStratagem"],
            "mean_per_battle": _ratio(
                actions["PlayStratagem"],
                battles,
            ),
            "opportunity_use_rate": _ratio(
                actions["PlayStratagem"],
                2 * battles,
            ),
        },
        "hand_pressure": {
            "mean_hand_size_at_pass": _ratio(
                pass_hand_total,
                pass_events,
            ),
            "mean_dead_cards_at_pass": _ratio(
                pass_dead_total,
                pass_events,
            ),
            "dead_card_share_at_pass": _ratio(
                card_totals["dead_on_pass"],
                card_totals["held_on_pass"],
            ),
            "unplayable_card_turn_share": _ratio(
                card_totals["unplayable_turns"],
                card_totals["turns_in_hand"],
            ),
            "card_play_rate_per_draw": _ratio(
                card_totals["plays"],
                card_totals["draws"],
            ),
        },
        "battle_end_signals": {
            "events": signal_events,
            "mean_signals_per_battle": _ratio(signal_events, battles),
            "first_signal_share": _ratio(
                first_signal_events,
                signal_events,
            ),
        },
        "decision_load": {
            "heuristic_decisions": decisions,
            "mean_legal_candidates_per_heuristic_decision": (
                _ratio(candidate_total, decisions)
            ),
        },
        "by_simulation": by_simulation,
    }


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _num(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def render_markdown(report: dict[str, Any]) -> str:
    scope = report["scope"]
    match = report["match_pacing"]
    battle = report["battle_pacing"]
    hand = report["hand_pressure"]
    rows = [
        "# AI playability statistics",
        "",
        (
            f"Source: **{scope['games']:,} matches / "
            f"{scope['battles']:,} resolved Battles** across "
            f"{scope['simulation_reports']} simulation reports "
            f"({scope.get('censored_games', 0):,} censored matches)."
        ),
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        (
            f"| Resolved Battles per match | "
            f"{_num(match['mean_resolved_battles_per_match'])} |"
        ),
        (
            f"| Final Battle reached | "
            f"{_num(match.get('mean_final_battle_reached'))} |"
        ),
        (
            f"| Cards played per match | "
            f"{_num(match['mean_cards_played_per_match'])} |"
        ),
        (
            f"| Cards played per Battle | "
            f"{_num(battle['mean_cards_played_per_battle'])} |"
        ),
        (
            f"| Cards played per player per Battle | "
            f"{_num(battle['mean_cards_played_per_player_battle'])} |"
        ),
        (
            f"| Action events per player per Battle | "
            f"{_num(battle['mean_action_events_per_player_battle'])} |"
        ),
        (
            f"| Maneuvers per Battle | "
            f"{_num(battle['mean_maneuvers_per_battle'])} |"
        ),
        (
            f"| Stratagem opportunity used | "
            f"{_pct(report['stratagem']['opportunity_use_rate'])} |"
        ),
        (
            f"| Hand size when passing | "
            f"{_num(hand['mean_hand_size_at_pass'])} |"
        ),
        (
            f"| Dead-card share at pass | "
            f"{_pct(hand['dead_card_share_at_pass'])} |"
        ),
        (
            f"| Card-in-hand turns unplayable | "
            f"{_pct(hand['unplayable_card_turn_share'])} |"
        ),
        (
            f"| Drawn cards eventually played | "
            f"{_pct(hand['card_play_rate_per_draw'])} |"
        ),
        (
            f"| First signal share | "
            f"{_pct(report['battle_end_signals']['first_signal_share'])} |"
        ),
        (
            f"| Mean legal candidates per heuristic decision | "
            f"{_num(report['decision_load']['mean_legal_candidates_per_heuristic_decision'])} |"
        ),
        "",
        "## Card mix per Battle",
        "",
        "| Type | Mean/Battle | Share |",
        "| --- | ---: | ---: |",
    ]
    for label, stats in report["card_mix"].items():
        rows.append(
            f"| {label} | {_num(stats['mean_per_battle'])} | "
            f"{_pct(stats['share_of_card_plays'])} |"
        )
    rows += [
        "",
        (
            "AI self-play measures structural pacing and resource pressure. "
            "It does not measure human reading time, comprehension, memory "
            "load, or enjoyment."
        ),
        "",
    ]
    return "\n".join(rows)
