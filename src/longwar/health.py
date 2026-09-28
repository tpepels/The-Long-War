from __future__ import annotations

from collections import Counter, defaultdict
from math import sqrt
from statistics import mean, median, pstdev
from typing import Any


def simulation_summary(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Summarize a simulation for report builders without losing provenance."""
    if data is None:
        return None
    telemetry = data.get("telemetry", {})
    result = {
        key: data.get(key)
        for key in (
            "games", "agents", "wins", "decisive_games",
            "censored_games", "failed_games", "censor_rate", "failure_rate",
            "win_rates", "first_player_win_rate",
            "mean_turns", "max_turns", "game_fingerprint",
            "experiment_fingerprint", "experiment_fingerprints", "seed", "config",
            "simulation_variant", "heuristic_config", "online_config",
            "strategic_config", "ismcts_config",
        )
    }
    result.update({
        key: telemetry.get(key)
        for key in (
            "passes", "battles", "actions", "decisions", "policy_sources",
            "online_resolution",
        )
    })
    return result


CARD_AGGREGATE_FIELDS = (
    "draws",
    "plays",
    "turns_in_hand",
    "playable_turns",
    "unplayable_turns",
    "affordable_turns",
    "unaffordable_turns",
    "structurally_unplayable_turns",
    "held_on_pass",
    "dead_on_pass",
    "affordable_on_pass",
    "unaffordable_on_pass",
    "structurally_dead_on_pass",
    "immediate_front_swing_total",
    "immediate_control_swing_total",
    "games_drawn",
    "decisive_games_drawn",
    "wins_when_drawn",
    "games_played",
    "decisive_games_played",
    "wins_when_played",
)

COMBO_AGGREGATE_FIELDS = (
    "completions",
    "strength_at_completion_total",
    "games_seen",
    "decisive_games_seen",
    "wins_when_seen",
)


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    return None if denominator == 0 else numerator / denominator


def _weighted_section(
    simulations: list[dict[str, Any]],
    *,
    section: str,
    count_field: str,
    fields: tuple[str, ...],
) -> dict[str, Any]:
    count = sum(
        int(simulation.get("telemetry", {}).get(section, {}).get(count_field, 0) or 0)
        for simulation in simulations
    )
    result: dict[str, Any] = {count_field: count}
    for field in fields:
        weighted = 0.0
        weight = 0
        for simulation in simulations:
            row = simulation.get("telemetry", {}).get(section, {})
            value = row.get(field)
            row_count = int(row.get(count_field, 0) or 0)
            if value is None or row_count <= 0:
                continue
            weighted += float(value) * row_count
            weight += row_count
        result[field] = weighted / weight if weight else None
    return result


def aggregate_simulations_for_health(
    simulations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge simulation telemetry from one ruleset using raw sufficient statistics."""
    if not simulations:
        raise ValueError("At least one simulation is required")

    fingerprints = {
        simulation.get("game_fingerprint")
        for simulation in simulations
        if simulation.get("game_fingerprint") is not None
    }
    if len(fingerprints) > 1:
        raise ValueError("Cannot aggregate simulations from different game fingerprints")

    experiment_fingerprints = sorted({
        str(simulation["experiment_fingerprint"])
        for simulation in simulations
        if simulation.get("experiment_fingerprint") is not None
    })

    agents = {
        tuple(simulation.get("agents", ()))
        for simulation in simulations
    }
    if len(agents) > 1:
        raise ValueError("Cannot aggregate health across different agent matchups")

    cards: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )
    combos: dict[str, dict[str, float]] = defaultdict(
        lambda: defaultdict(float)
    )

    for simulation in simulations:
        telemetry = simulation.get("telemetry", {})
        for card_id, stats in telemetry.get("cards", {}).items():
            for field in CARD_AGGREGATE_FIELDS:
                if field.startswith("decisive_") and field not in stats:
                    legacy_field = field.removeprefix("decisive_")
                    cards[card_id][field] += float(
                        stats.get(legacy_field, 0) or 0
                    )
                else:
                    cards[card_id][field] += float(stats.get(field, 0) or 0)

        for combo_id, stats in telemetry.get(
            "formation_combinations", {}
        ).items():
            for field in COMBO_AGGREGATE_FIELDS:
                if field == "decisive_games_seen" and field not in stats:
                    combos[combo_id][field] += float(
                        stats.get("games_seen", 0) or 0
                    )
                else:
                    combos[combo_id][field] += float(stats.get(field, 0) or 0)

    card_rows: dict[str, dict[str, Any]] = {}
    for card_id, raw in cards.items():
        row = {field: raw[field] for field in CARD_AGGREGATE_FIELDS}
        for field in (
            "draws",
            "plays",
            "turns_in_hand",
            "playable_turns",
            "unplayable_turns",
            "affordable_turns",
            "unaffordable_turns",
            "structurally_unplayable_turns",
            "held_on_pass",
            "dead_on_pass",
            "affordable_on_pass",
            "unaffordable_on_pass",
            "structurally_dead_on_pass",
            "games_drawn",
            "decisive_games_drawn",
            "wins_when_drawn",
            "games_played",
            "decisive_games_played",
            "wins_when_played",
        ):
            row[field] = int(row[field])
        row["plays_per_draw"] = _safe_ratio(row["plays"], row["draws"])
        row["play_rate_per_draw"] = _safe_ratio(
            row["games_played"], row["games_drawn"]
        )
        row["unplayable_turn_rate"] = _safe_ratio(
            row["unplayable_turns"], row["turns_in_hand"]
        )
        row["structural_unplayable_turn_rate"] = _safe_ratio(
            row["structurally_unplayable_turns"], row["affordable_turns"]
        )
        row["resource_blocked_turn_rate"] = _safe_ratio(
            row["unaffordable_turns"], row["turns_in_hand"]
        )
        row["dead_on_pass_rate"] = _safe_ratio(
            row["dead_on_pass"], row["held_on_pass"]
        )
        row["structural_dead_on_pass_rate"] = _safe_ratio(
            row["structurally_dead_on_pass"], row["affordable_on_pass"]
        )
        row["resource_blocked_on_pass_rate"] = _safe_ratio(
            row["unaffordable_on_pass"], row["held_on_pass"]
        )
        row["mean_immediate_front_swing"] = _safe_ratio(
            row["immediate_front_swing_total"], row["plays"]
        )
        row["mean_immediate_control_swing"] = _safe_ratio(
            row["immediate_control_swing_total"], row["plays"]
        )
        row["win_rate_when_drawn"] = _safe_ratio(
            row["wins_when_drawn"], row["decisive_games_drawn"]
        )
        row["win_rate_when_played"] = _safe_ratio(
            row["wins_when_played"], row["decisive_games_played"]
        )
        card_rows[card_id] = row

    combo_rows: dict[str, dict[str, Any]] = {}
    for combo_id, raw in combos.items():
        row = {field: raw[field] for field in COMBO_AGGREGATE_FIELDS}
        for field in (
            "completions",
            "games_seen",
            "decisive_games_seen",
            "wins_when_seen",
        ):
            row[field] = int(row[field])
        row["mean_strength_at_completion"] = _safe_ratio(
            row["strength_at_completion_total"], row["completions"]
        )
        row["win_rate_when_seen"] = _safe_ratio(
            row["wins_when_seen"], row["decisive_games_seen"]
        )
        combo_rows[combo_id] = row

    games = sum(int(simulation.get("games", 0)) for simulation in simulations)
    censored_games = sum(
        int(simulation.get("censored_games", 0) or 0)
        for simulation in simulations
    )
    failed_games = sum(
        int(simulation.get("failed_games", 0) or 0)
        for simulation in simulations
    )
    completed_games = games - failed_games
    decisive_games = completed_games - censored_games
    wins = [
        sum(int(simulation.get("wins", [0, 0])[player]) for simulation in simulations)
        for player in range(2)
    ]
    first_player_wins = sum(
        int(simulation.get("first_player_wins", 0) or 0)
        for simulation in simulations
    )
    mean_turns = _safe_ratio(
        sum(
            float(simulation.get("mean_turns", 0.0))
            * (
                int(simulation.get("games", 0))
                - int(simulation.get("failed_games", 0) or 0)
            )
            for simulation in simulations
        ),
        completed_games,
    ) or 0.0

    passes = _weighted_section(
        simulations,
        section="passes",
        count_field="events",
        fields=(
            "mean_hand_size",
            "mean_command_remaining",
            "mean_deck_remaining",
            "command_exhausted_rate",
            "mean_dead_cards",
            "mean_structurally_dead_cards",
            "mean_unaffordable_cards",
            "mean_affordable_cards",
            "mean_playable_cards_remaining",
            "mean_legal_alternatives",
            "mean_playable_card_actions",
            "mean_maneuver_actions",
            "no_alternative_rate",
            "playable_alternative_rate",
            "mean_actions_before_pass",
            "first_pass_rate",
        ),
    )
    battles = _weighted_section(
        simulations,
        section="battles",
        count_field="count",
        fields=(
            "mean_actions",
            "mean_total_strength",
            "mean_abs_total_margin",
        ),
    )
    battles["continuing_battles"] = sum(
        int(
            simulation.get("telemetry", {})
            .get("battles", {})
            .get("continuing_battles", 0)
            or 0
        )
        for simulation in simulations
    )

    first = simulations[0]
    return {
        "games": games,
        "completed_games": completed_games,
        "decisive_games": decisive_games,
        "censored_games": censored_games,
        "failed_games": failed_games,
        "censor_rate": _safe_ratio(censored_games, games) or 0.0,
        "failure_rate": _safe_ratio(failed_games, games) or 0.0,
        "agents": list(next(iter(agents))),
        "wins": wins,
        "win_rates": [
            (_safe_ratio(win, decisive_games) or 0.0)
            for win in wins
        ],
        "first_player_wins": first_player_wins,
        "first_player_win_rate": (
            _safe_ratio(first_player_wins, decisive_games) or 0.0
        ),
        "mean_turns": mean_turns,
        "max_turns": max(int(simulation.get("max_turns", 0)) for simulation in simulations),
        "game_fingerprint": next(iter(fingerprints), None),
        "experiment_fingerprint": (
            experiment_fingerprints[0]
            if len(experiment_fingerprints) == 1
            else None
        ),
        "experiment_fingerprints": experiment_fingerprints,
        "simulation_variant": first.get("simulation_variant"),
        "telemetry": {
            "passes": passes,
            "battles": battles,
            "cards": card_rows,
            "formation_combinations": combo_rows,
        },
    }


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if trials <= 0:
        return (None, None)
    p = successes / trials
    d = 1.0 + (z * z) / trials
    c = (p + (z * z) / (2.0 * trials)) / d
    h = z * sqrt((p * (1.0 - p) / trials) + (z * z) / (4.0 * trials * trials)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _z(value: float | None, values: list[float]) -> float | None:
    if value is None or len(values) < 2:
        return None
    sd = pstdev(values)
    return 0.0 if sd == 0 else (value - mean(values)) / sd


def _playability_family(card: dict[str, Any]) -> str:
    if card["type"] == "plot":
        return "veiled_story" if card.get("veiled", False) else "story"
    if card["type"] == "link":
        return "bond"
    return str(card["type"])


def _flag(code: str, severity: str, message: str, value: float | None = None) -> dict[str, Any]:
    row = {"code": code, "severity": severity, "message": message}
    if value is not None:
        row["value"] = value
    return row


def analyze_simulation(simulation: dict[str, Any], card_data: dict[str, Any]) -> dict[str, Any]:
    telemetry = simulation["telemetry"]
    meta = {card["id"]: card for card in card_data["cards"]}
    games = int(simulation["games"])
    censored_games = int(simulation.get("censored_games", 0))
    failed_games = int(simulation.get("failed_games", 0))
    decisive_games = max(0, games - censored_games - failed_games)

    fp = int(simulation["first_player_wins"])
    fp_rate = fp / decisive_games if decisive_games else 0.0
    fp_ci = wilson_interval(fp, decisive_games)
    global_flags: list[dict[str, Any]] = []
    if fp_ci[0] is not None:
        if fp_ci[0] > 0.55 or fp_ci[1] < 0.45:
            global_flags.append(_flag("first_player_bias", "high", "95% interval lies outside the 45–55% design band.", fp_rate))
        elif fp_ci[0] > 0.50 or fp_ci[1] < 0.50:
            global_flags.append(_flag("first_player_signal", "watch", "95% interval excludes 50%.", fp_rate))

    swings: dict[str, list[float]] = defaultdict(list)
    for card_id, stats in telemetry["cards"].items():
        value = stats.get("mean_immediate_front_swing")
        if value is not None and int(stats.get("plays", 0)) >= 20:
            swings[meta[card_id]["type"]].append(float(value))

    family_values: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"play_rate": [], "dead": [], "dead_pass": []}
    )
    for card_id, stats in telemetry["cards"].items():
        card = meta[card_id]
        family = _playability_family(card)
        draws = int(stats.get("draws", 0))
        held = int(stats.get("affordable_turns", stats.get("turns_in_hand", 0)))
        held_pass = int(stats.get("affordable_on_pass", stats.get("held_on_pass", 0)))
        play_rate = stats.get("play_rate_per_draw")
        dead = stats.get("structural_unplayable_turn_rate", stats.get("unplayable_turn_rate"))
        dead_pass = stats.get("structural_dead_on_pass_rate", stats.get("dead_on_pass_rate"))
        if draws >= 100 and play_rate is not None:
            family_values[family]["play_rate"].append(float(play_rate))
        if held >= 200 and dead is not None:
            family_values[family]["dead"].append(float(dead))
        if held_pass >= 40 and dead_pass is not None:
            family_values[family]["dead_pass"].append(float(dead_pass))

    family_baselines = {
        family: {
            metric: (median(values) if values else None)
            for metric, values in metrics.items()
        }
        for family, metrics in family_values.items()
    }

    counts: Counter[str] = Counter()
    cards: list[dict[str, Any]] = []
    telemetry_cards = telemetry.get("cards", {})
    for card in card_data["cards"]:
        card_id = card["id"]
        stats = telemetry_cards.get(card_id, {})
        observed = any(
            int(stats.get(field, 0) or 0) > 0
            for field in (
                "draws",
                "plays",
                "turns_in_hand",
                "games_drawn",
                "games_played",
            )
        )
        played_n = int(
            stats.get("decisive_games_played", stats.get("games_played", 0))
        )
        played_w = int(stats.get("wins_when_played", 0))
        drawn_n = int(
            stats.get("decisive_games_drawn", stats.get("games_drawn", 0))
        )
        drawn_w = int(stats.get("wins_when_drawn", 0))
        played_ci = wilson_interval(played_w, played_n)
        drawn_ci = wilson_interval(drawn_w, drawn_n)

        draws = int(stats.get("draws", 0))
        plays = int(stats.get("plays", 0))
        held = int(stats.get("affordable_turns", stats.get("turns_in_hand", 0)))
        held_pass = int(stats.get("affordable_on_pass", stats.get("held_on_pass", 0)))
        play_rate = stats.get("play_rate_per_draw")
        dead = stats.get("structural_unplayable_turn_rate", stats.get("unplayable_turn_rate"))
        dead_pass = stats.get("structural_dead_on_pass_rate", stats.get("dead_on_pass_rate"))
        swing = stats.get("mean_immediate_front_swing")
        swing_z = _z(float(swing) if swing is not None else None, swings[card["type"]])
        delayed_utility = bool(card.get("balance", {}).get("delayed_utility"))
        flags: list[dict[str, Any]] = []

        family = _playability_family(card)
        baseline = family_baselines.get(family, {})
        family_play_rate = baseline.get("play_rate")
        family_dead = baseline.get("dead")
        family_dead_pass = baseline.get("dead_pass")

        if draws >= 100 and play_rate is not None and family_play_rate is not None:
            if play_rate >= 0.90 and play_rate >= family_play_rate + 0.12:
                flags.append(_flag(
                    "auto_play",
                    "watch",
                    "Played unusually often compared with cards in the same rules family.",
                    float(play_rate),
                ))
            elif play_rate <= 0.35 and play_rate <= family_play_rate - 0.15:
                flags.append(_flag(
                    "low_conversion",
                    "watch",
                    "Played unusually rarely compared with cards in the same rules family.",
                    float(play_rate),
                ))

        if (
            held >= 200
            and dead is not None
            and family_dead is not None
            and dead >= 0.30
            and dead >= family_dead + 0.15
        ):
            severity = "high" if dead >= family_dead + 0.25 else "watch"
            flags.append(_flag(
                "dead_draw",
                severity,
                "Structurally unplayable while affordable substantially more often than cards in the same rules family.",
                float(dead),
            ))

        if (
            held_pass >= 40
            and dead_pass is not None
            and family_dead_pass is not None
            and dead_pass >= 0.25
            and dead_pass >= family_dead_pass + 0.15
        ):
            flags.append(_flag(
                "dead_on_pass",
                "watch",
                "Structurally unplayable at Pass while affordable substantially more often than its rules family.",
                float(dead_pass),
            ))

        if (
            not delayed_utility
            and plays >= 80
            and swing_z is not None
            and abs(swing_z) >= 1.75
        ):
            flags.append(_flag(
                "board_swing_outlier",
                "watch",
                "Immediate Front swing is an outlier within this card type.",
                swing_z,
            ))

        if played_n >= 100 and played_ci[0] is not None:
            if played_ci[0] > 0.56:
                flags.append(_flag(
                    "positive_outcome_association",
                    "diagnostic",
                    "Observational win association when played; inspect with paired counterfactual evidence before treating this as card strength.",
                    float(stats["win_rate_when_played"]),
                ))
            elif played_ci[1] < 0.44:
                flags.append(_flag(
                    "negative_outcome_association",
                    "diagnostic",
                    "Observational win association when played; inspect with paired counterfactual evidence before treating this as card weakness.",
                    float(stats["win_rate_when_played"]),
                ))

        for flag in flags:
            counts[flag["severity"]] += 1

        high_count = sum(flag["severity"] == "high" for flag in flags)
        watch_count = sum(flag["severity"] == "watch" for flag in flags)
        evidence_strong = draws >= 150 and played_n >= 100 and held >= 200

        if not observed:
            balance_level = "unobserved"
            balance_label = "Unobserved"
        elif high_count >= 2:
            balance_level = "red"
            balance_label = "Critical"
        elif high_count >= 1 or watch_count >= 2:
            balance_level = "orange"
            balance_label = "Needs balancing"
        elif watch_count == 1:
            balance_level = "yellow"
            balance_label = "Watch"
        elif evidence_strong:
            balance_level = "dark_green"
            balance_label = "Well-supported healthy"
        else:
            balance_level = "green"
            balance_label = "Looks healthy"

        strong_signals = {
            "auto_play",
            "board_swing_outlier",
        }
        weak_signals = {
            "low_conversion",
            "dead_draw",
            "dead_on_pass",
        }
        codes = {flag["code"] for flag in flags}
        has_strong = bool(codes & strong_signals)
        has_weak = bool(codes & weak_signals)
        if not observed:
            balance_direction = "unobserved"
        elif has_strong and has_weak:
            balance_direction = "mixed"
        elif has_strong:
            balance_direction = "strong"
        elif has_weak:
            balance_direction = "weak"
        else:
            balance_direction = "neutral"

        cards.append({
            "id": card_id,
            "title": card["title"],
            "type": card["type"],
            "strength": card.get("strength"),
            "text": card.get("text", ""),
            "unique": bool(card.get("unique", False)),
            "hero": bool(card.get("hero", False)),
            "hero_name_strength": card.get("hero_name_strength"),
            "classes": list(card.get("classes", [])),
            "role": card.get("role"),
            "story_form": card.get("story_form"),
            "veiled": bool(card.get("veiled", False)),
            "balance_level": balance_level,
            "balance_label": balance_label,
            "balance_direction": balance_direction,
            "observed": observed,
            "evidence_strong": evidence_strong,
            "delayed_utility": delayed_utility,
            "playability_family": family,
            "family_play_rate_median": family_play_rate,
            "family_unplayable_turn_rate_median": family_dead,
            "family_dead_on_pass_rate_median": family_dead_pass,
            "draws": draws,
            "plays": plays,
            "turns_in_hand": int(stats.get("turns_in_hand", 0)),
            "playable_turns": int(stats.get("playable_turns", 0)),
            "unplayable_turns": int(stats.get("unplayable_turns", 0)),
            "affordable_turns": int(stats.get("affordable_turns", 0)),
            "unaffordable_turns": int(stats.get("unaffordable_turns", 0)),
            "structurally_unplayable_turns": int(stats.get("structurally_unplayable_turns", 0)),
            "held_on_pass": int(stats.get("held_on_pass", 0)),
            "affordable_on_pass": int(stats.get("affordable_on_pass", 0)),
            "unaffordable_on_pass": int(stats.get("unaffordable_on_pass", 0)),
            "dead_on_pass": int(stats.get("dead_on_pass", 0)),
            "structurally_dead_on_pass": int(stats.get("structurally_dead_on_pass", 0)),
            "games_drawn": int(stats.get("games_drawn", 0)),
            "decisive_games_drawn": drawn_n,
            "games_played": int(stats.get("games_played", 0)),
            "decisive_games_played": played_n,
            "play_rate_per_draw": play_rate,
            "unplayable_turn_rate": stats.get("unplayable_turn_rate"),
            "structural_unplayable_turn_rate": dead,
            "resource_blocked_turn_rate": stats.get("resource_blocked_turn_rate"),
            "dead_on_pass_rate": stats.get("dead_on_pass_rate"),
            "structural_dead_on_pass_rate": dead_pass,
            "resource_blocked_on_pass_rate": stats.get("resource_blocked_on_pass_rate"),
            "mean_immediate_front_swing": swing,
            "mean_immediate_control_swing": stats.get("mean_immediate_control_swing"),
            "front_swing_z_within_type": swing_z,
            "win_rate_when_drawn": stats.get("win_rate_when_drawn"),
            "win_rate_when_drawn_95": list(drawn_ci),
            "win_rate_when_played": stats.get("win_rate_when_played"),
            "win_rate_when_played_95": list(played_ci),
            "flags": flags,
        })

    combo_stats = telemetry.get("formation_combinations", {})
    combo_strengths = [
        float(s["mean_strength_at_completion"])
        for s in combo_stats.values()
        if s.get("mean_strength_at_completion") is not None and int(s.get("completions", 0)) >= 10
    ]
    formations: list[dict[str, Any]] = []
    for key, stats in combo_stats.items():
        games_seen = int(stats.get("games_seen", 0))
        seen = int(
            stats.get("decisive_games_seen", games_seen)
        )
        wins = int(stats.get("wins_when_seen", 0))
        ci = wilson_interval(wins, seen)
        strength = stats.get("mean_strength_at_completion")
        strength_z = _z(float(strength) if strength is not None else None, combo_strengths)
        flags: list[dict[str, Any]] = []

        if seen >= 50 and ci[0] is not None:
            if ci[0] > 0.60:
                flags.append(_flag(
                    "combo_positive_association",
                    "diagnostic",
                    "Observational three-card win association; inspect with paired interaction evidence before treating this as a balance defect.",
                    float(stats["win_rate_when_seen"]),
                ))
            elif ci[1] < 0.40:
                flags.append(_flag(
                    "combo_negative_association",
                    "diagnostic",
                    "Observational three-card win association; inspect with paired interaction evidence before treating this as a balance defect.",
                    float(stats["win_rate_when_seen"]),
                ))

        if int(stats.get("completions", 0)) >= 30 and strength_z is not None and strength_z >= 2.0:
            flags.append(_flag("combo_strength_outlier", "watch", "Three-card sequence Strength is at least two standard deviations high.", strength_z))

        for flag in flags:
            counts[flag["severity"]] += 1

        subject, link, name = key.split(" | ")
        formations.append({
            "id": key,
            "title": " — ".join(meta[x]["title"] for x in (subject, link, name)),
            "completions": int(stats.get("completions", 0)),
            "games_seen": games_seen,
            "decisive_games_seen": seen,
            "mean_strength_at_completion": strength,
            "completion_strength_z": strength_z,
            "win_rate_when_seen": stats.get("win_rate_when_seen"),
            "win_rate_when_seen_95": list(ci),
            "flags": flags,
        })

    for flag in global_flags:
        counts[flag["severity"]] += 1

    cards.sort(key=lambda r: (-sum(2 if f["severity"] == "high" else 1 for f in r["flags"]), r["title"]))
    formations.sort(key=lambda r: (-sum(2 if f["severity"] == "high" else 1 for f in r["flags"]), -r["games_seen"], r["title"]))

    return {
        "schema_version": 1,
        "game_fingerprint": simulation.get("game_fingerprint"),
        "experiment_fingerprint": simulation.get("experiment_fingerprint"),
        "experiment_fingerprints": simulation.get("experiment_fingerprints", []),
        "simulation_variant": simulation.get("simulation_variant"),
        "source": {
            "games": games,
            "decisive_games": decisive_games,
            "censored_games": censored_games,
            "censor_rate": (censored_games / games if games else 0.0),
            "agents": simulation["agents"],
            "wins": simulation["wins"],
        },
        "global": {
            "first_player_win_rate": fp_rate,
            "first_player_win_rate_95": list(fp_ci),
            "decisive_games": decisive_games,
            "censored_games": censored_games,
            "censor_rate": (censored_games / games if games else 0.0),
            "mean_actions": simulation["mean_turns"],
            "max_actions": simulation["max_turns"],
            "passes": telemetry["passes"],
            "battles": telemetry["battles"],
            "flags": global_flags,
        },
        "summary": {
            "cards_analyzed": len(cards),
            "cards_observed": sum(bool(row["observed"]) for row in cards),
            "cards_unobserved": sum(not row["observed"] for row in cards),
            "formations_observed": len(formations),
            "flags_high": counts["high"],
            "flags_watch": counts["watch"],
            "flags_diagnostic": counts["diagnostic"],
            "card_levels": dict(Counter(row["balance_level"] for row in cards)),
        },
        "cards": cards,
        "formations": formations,
        "methodology": {
            "win_intervals": "Wilson score interval, 95%",
            "notes": [
                "Conditional win rates are observational rather than causal values.",
                "Board-swing z-scores are computed within card type; cards explicitly marked as delayed utility are not graded on immediate swing.",
                "Card deadness flags use only normal operation decisions and compare structural illegality while the card is affordable; pending effect-resolution choices and simple Command shortfall are measured separately.",
                "Flags identify cases for inspection; they are not automatic nerf/buff instructions.",
                "Every canonical card remains in the report. Cards with no observed self-play exposure are labelled Unobserved rather than healthy.",
                "Counterfactual and MCCFR reports are merged when explicitly run; neither is required for routine health analysis.",
            ],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    g = report["global"]
    s = report["summary"]
    low, high = g["first_player_win_rate_95"]
    first_player_line = (
        f"First-player win: **{100*g['first_player_win_rate']:.1f}%** "
        f"(95% Wilson {100*low:.1f}%–{100*high:.1f}%)  "
        if low is not None and high is not None
        else "First-player win: **n/a** (no decisive games)  "
    )
    lines = [
        "# The Long War — Balance Health Report",
        "",
        f"Games: **{report['source']['games']}** · decisive: **{g['decisive_games']}** · "
        f"censored: **{g['censored_games']}** ({100*g['censor_rate']:.1f}%) · "
        f"Agents: **{' vs '.join(report['source']['agents'])}**  ",
        f"Card exposure: **{s.get('cards_observed', s['cards_analyzed'])}/{s['cards_analyzed']} observed** · "
        f"**{s.get('cards_unobserved', 0)} unobserved**  ",
        first_player_line,
        f"High flags: **{s['flags_high']}** · Watch flags: **{s['flags_watch']}** · Diagnostic associations: **{s.get('flags_diagnostic', 0)}**",
        "",
        "## Flagged cards",
        "",
    ]
    for row in [r for r in report["cards"] if r["flags"]]:
        lines.append(f"- **{row['title']}** ({row['type']}): " + ", ".join(f["code"] for f in row["flags"]))
    lines += ["", "## Flagged Force–Bond–Name formations", ""]
    for row in [r for r in report["formations"] if r["flags"]][:30]:
        lines.append(f"- **{row['title']}**: " + ", ".join(f["code"] for f in row["flags"]))
    lines += [
        "",
        "## Interpretation",
        "",
        "These flags are diagnostics, not balance verdicts. Wilson intervals reduce small-sample overconfidence; optional counterfactual or MCCFR validation can be run when a stable candidate merits deeper analysis.",
        "",
    ]
    return "\n".join(lines)
