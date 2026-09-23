from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

CARD_ACTIONS = (
    "PlaySubject",
    "PlayLink",
    "PlayName",
    "PlayPlot",
    "PlayScheme",
    "SetStratagem",
)
CARD_LABELS = {
    "PlaySubject": "Subjects",
    "PlayLink": "Bonds",
    "PlayName": "Names",
    "PlayPlot": "Stories",
    "PlayScheme": "Veiled Stories",
    "SetStratagem": "Stratagems",
}


def _ratio(a: float, b: float) -> float | None:
    return None if b == 0 else a / b


def build_playability_report(simulations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    simulations = list(simulations)
    if not simulations:
        raise ValueError("At least one simulation report is required")

    fingerprints = {
        str(simulation["game_fingerprint"])
        for simulation in simulations
        if simulation.get("game_fingerprint")
    }
    if len(fingerprints) > 1:
        raise ValueError("Simulation reports belong to different game fingerprints")

    games = battles = pass_events = first_pass_battles = decisions = 0
    continuing_battles = shortfall_players = 0
    match_actions = pass_hand_total = pass_dead_total = 0.0
    next_hand_total = next_shortfall_total = 0.0
    first_pass_wins = candidate_total = 0.0
    actions: Counter[str] = Counter()
    card_totals: Counter[str] = Counter()
    combo_completions = 0
    by_simulation = []

    for index, simulation in enumerate(simulations):
        game_count = int(simulation["games"])
        telemetry = simulation["telemetry"]
        battle_count = int(telemetry["battles"]["count"])
        if game_count <= 0 or battle_count <= 0:
            raise ValueError("Simulation reports must contain games and Battle telemetry")

        run_actions = Counter(
            {name: int(count) for name, count in telemetry["actions"].items()}
        )
        cards_played = sum(run_actions[name] for name in CARD_ACTIONS)
        battle_actions = sum(
            count for name, count in run_actions.items() if name != "ChooseFirst"
        )
        passes = telemetry["passes"]
        battle_stats = telemetry["battles"]
        run_pass_events = int(passes["events"])
        run_continuing = int(battle_stats.get("continuing_battles", 0))

        games += game_count
        battles += battle_count
        match_actions += float(simulation["mean_turns"]) * game_count
        actions.update(run_actions)
        pass_events += run_pass_events
        pass_hand_total += float(passes.get("mean_hand_size") or 0.0) * run_pass_events
        pass_dead_total += float(passes.get("mean_dead_cards") or 0.0) * run_pass_events
        first_pass_battles += battle_count
        first_pass_wins += (
            float(passes.get("first_passer_battle_win_rate") or 0.0) * battle_count
        )
        continuing_battles += run_continuing
        next_hand_total += (
            float(battle_stats.get("mean_next_battle_hand_size") or 0.0)
            * 2
            * run_continuing
        )
        next_shortfall_total += (
            float(battle_stats.get("mean_next_battle_hand_shortfall") or 0.0)
            * 2
            * run_continuing
        )
        shortfall_players += int(
            round(
                float(battle_stats.get("next_battle_player_shortfall_rate") or 0.0)
                * 2
                * run_continuing
            )
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
            for stats in telemetry.get("legend_combinations", {}).values()
        )

        heuristic = telemetry.get("decisions", {}).get("heuristic")
        if heuristic:
            run_decisions = int(heuristic.get("decisions", 0))
            decisions += run_decisions
            candidate_total += (
                float(heuristic.get("mean_candidate_count") or 0.0) * run_decisions
            )

        mean_battles = battle_count / game_count
        by_simulation.append(
            {
                "label": str(simulation.get("_label") or f"simulation-{index + 1}"),
                "games": game_count,
                "mean_battles_per_match": mean_battles,
                "three_battle_match_rate": mean_battles - 2.0,
                "mean_cards_played_per_battle": cards_played / battle_count,
                "mean_cards_played_per_match": cards_played / game_count,
                "draw_opportunity_use_rate": run_actions["Draw"] / (2 * battle_count),
                "mean_action_events_per_battle": battle_actions / battle_count,
            }
        )

    cards_played = sum(actions[name] for name in CARD_ACTIONS)
    normal_cards = cards_played - actions["SetStratagem"]
    battle_actions = sum(
        count for name, count in actions.items() if name != "ChooseFirst"
    )
    normal_turn_actions = battle_actions - actions["SetStratagem"]
    two_battle_matches = 3 * games - battles
    three_battle_matches = battles - 2 * games
    if min(two_battle_matches, three_battle_matches) < 0:
        raise ValueError("Battle counts do not match a first-to-two-Battles match")

    return {
        "schema_version": 1,
        "game_fingerprint": next(iter(fingerprints), None),
        "scope": {"simulation_reports": len(simulations), "games": games, "battles": battles},
        "match_pacing": {
            "mean_battles_per_match": battles / games,
            "two_battle_matches": two_battle_matches,
            "two_battle_match_rate": two_battle_matches / games,
            "three_battle_matches": three_battle_matches,
            "three_battle_match_rate": three_battle_matches / games,
            "mean_action_events_per_match": match_actions / games,
            "mean_cards_played_per_match": cards_played / games,
        },
        "battle_pacing": {
            "mean_action_events_per_battle": battle_actions / battles,
            "mean_normal_turn_actions_per_battle": normal_turn_actions / battles,
            "mean_normal_turn_actions_per_player_battle": normal_turn_actions / (2 * battles),
            "mean_cards_played_per_battle": cards_played / battles,
            "mean_cards_played_per_player_battle": cards_played / (2 * battles),
            "mean_normal_cards_played_per_battle": normal_cards / battles,
            "mean_complete_legends_created_per_battle": combo_completions / battles,
        },
        "card_mix": {
            CARD_LABELS[name]: {
                "count": actions[name],
                "share_of_card_plays": _ratio(actions[name], cards_played),
                "mean_per_battle": actions[name] / battles,
            }
            for name in CARD_ACTIONS
        },
        "draw": {
            "actions": actions["Draw"],
            "mean_per_battle": actions["Draw"] / battles,
            "opportunity_use_rate": actions["Draw"] / (2 * battles),
        },
        "stratagem": {
            "sets": actions["SetStratagem"],
            "mean_per_battle": actions["SetStratagem"] / battles,
            "opportunity_use_rate": actions["SetStratagem"] / (2 * battles),
        },
        "refill": {
            "continuing_battles": continuing_battles,
            "mean_next_battle_hand_size": _ratio(next_hand_total, 2 * continuing_battles),
            "mean_next_battle_hand_shortfall": _ratio(next_shortfall_total, 2 * continuing_battles),
            "next_battle_player_shortfall_rate": _ratio(shortfall_players, 2 * continuing_battles),
        },
        "hand_pressure": {
            "mean_hand_size_at_pass": _ratio(pass_hand_total, pass_events),
            "mean_dead_cards_at_pass": _ratio(pass_dead_total, pass_events),
            "dead_card_share_at_pass": _ratio(card_totals["dead_on_pass"], card_totals["held_on_pass"]),
            "unplayable_card_turn_share": _ratio(card_totals["unplayable_turns"], card_totals["turns_in_hand"]),
            "card_play_rate_per_draw": _ratio(card_totals["plays"], card_totals["draws"]),
        },
        "passing": {
            "events": pass_events,
            "mean_passes_per_battle": pass_events / battles,
            "first_passer_battle_win_rate": _ratio(first_pass_wins, first_pass_battles),
        },
        "decision_load": {
            "heuristic_decisions": decisions,
            "mean_legal_candidates_per_heuristic_decision": _ratio(candidate_total, decisions),
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
    refill = report["refill"]
    rows = [
        "# AI playability statistics",
        "",
        f"Source: **{scope['games']:,} matches / {scope['battles']:,} Battles** across {scope['simulation_reports']} simulation reports.",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Battles per match | {_num(match['mean_battles_per_match'])} |",
        f"| 3-Battle matches | {_pct(match['three_battle_match_rate'])} |",
        f"| Cards played per match | {_num(match['mean_cards_played_per_match'])} |",
        f"| Cards played per Battle | {_num(battle['mean_cards_played_per_battle'])} |",
        f"| Cards played per player per Battle | {_num(battle['mean_cards_played_per_player_battle'])} |",
        f"| Normal turn actions per player per Battle | {_num(battle['mean_normal_turn_actions_per_player_battle'])} |",
        f"| Draw opportunity used | {_pct(report['draw']['opportunity_use_rate'])} |",
        f"| Stratagem opportunity used | {_pct(report['stratagem']['opportunity_use_rate'])} |",
        f"| Hand size when passing | {_num(hand['mean_hand_size_at_pass'])} |",
        f"| Dead-card share at pass | {_pct(hand['dead_card_share_at_pass'])} |",
        f"| Card-in-hand turns unplayable | {_pct(hand['unplayable_card_turn_share'])} |",
        f"| Drawn cards eventually played | {_pct(hand['card_play_rate_per_draw'])} |",
        f"| Next-Battle hand size | {_num(refill['mean_next_battle_hand_size'])} |",
        f"| Next-Battle refill shortfall/player | {_num(refill['mean_next_battle_hand_shortfall'])} |",
        f"| Players below refill target | {_pct(refill['next_battle_player_shortfall_rate'])} |",
        f"| First passer wins Battle | {_pct(report['passing']['first_passer_battle_win_rate'])} |",
        f"| Mean legal candidates per heuristic decision | {_num(report['decision_load']['mean_legal_candidates_per_heuristic_decision'])} |",
        "",
        "## Card mix per Battle",
        "",
        "| Type | Mean/Battle | Share |",
        "| --- | ---: | ---: |",
    ]
    for label, stats in report["card_mix"].items():
        rows.append(f"| {label} | {_num(stats['mean_per_battle'])} | {_pct(stats['share_of_card_plays'])} |")
    rows += [
        "",
        "AI self-play measures structural pacing and resource pressure. It does not measure human reading time, comprehension, memory load, or enjoyment.",
        "",
    ]
    return "\n".join(rows)
