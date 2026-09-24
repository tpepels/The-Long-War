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
            "games", "agents", "wins", "win_rates", "first_player_win_rate",
            "mean_turns", "max_turns", "game_fingerprint", "seed", "config",
            "simulation_variant", "online_config", "strategic_config", "ismcts_config",
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

    fp = int(simulation["first_player_wins"])
    fp_rate = fp / games
    fp_ci = wilson_interval(fp, games)
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
        held = int(stats.get("turns_in_hand", 0))
        held_pass = int(stats.get("held_on_pass", 0))
        play_rate = stats.get("play_rate_per_draw")
        dead = stats.get("unplayable_turn_rate")
        dead_pass = stats.get("dead_on_pass_rate")
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
    for card_id, stats in telemetry["cards"].items():
        card = meta[card_id]
        played_n = int(stats.get("games_played", 0))
        played_w = int(stats.get("wins_when_played", 0))
        drawn_n = int(stats.get("games_drawn", 0))
        drawn_w = int(stats.get("wins_when_drawn", 0))
        played_ci = wilson_interval(played_w, played_n)
        drawn_ci = wilson_interval(drawn_w, drawn_n)

        draws = int(stats.get("draws", 0))
        plays = int(stats.get("plays", 0))
        held = int(stats.get("turns_in_hand", 0))
        held_pass = int(stats.get("held_on_pass", 0))
        play_rate = stats.get("play_rate_per_draw")
        dead = stats.get("unplayable_turn_rate")
        dead_pass = stats.get("dead_on_pass_rate")
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
                "Unplayable substantially more often than cards in the same rules family.",
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
                "Still unplayable on Pass substantially more often than its rules family.",
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

        if high_count >= 2:
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
        if has_strong and has_weak:
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
            "evidence_strong": evidence_strong,
            "delayed_utility": delayed_utility,
            "playability_family": family,
            "family_play_rate_median": family_play_rate,
            "family_unplayable_turn_rate_median": family_dead,
            "family_dead_on_pass_rate_median": family_dead_pass,
            "draws": draws,
            "plays": plays,
            "turns_in_hand": held,
            "playable_turns": int(stats.get("playable_turns", 0)),
            "unplayable_turns": int(stats.get("unplayable_turns", 0)),
            "held_on_pass": held_pass,
            "dead_on_pass": int(stats.get("dead_on_pass", 0)),
            "games_drawn": drawn_n,
            "games_played": played_n,
            "play_rate_per_draw": play_rate,
            "unplayable_turn_rate": dead,
            "dead_on_pass_rate": dead_pass,
            "mean_immediate_front_swing": swing,
            "mean_immediate_control_swing": stats.get("mean_immediate_control_swing"),
            "front_swing_z_within_type": swing_z,
            "win_rate_when_drawn": stats.get("win_rate_when_drawn"),
            "win_rate_when_drawn_95": list(drawn_ci),
            "win_rate_when_played": stats.get("win_rate_when_played"),
            "win_rate_when_played_95": list(played_ci),
            "flags": flags,
        })

    combo_stats = telemetry.get("legend_combinations", {})
    combo_strengths = [
        float(s["mean_strength_at_completion"])
        for s in combo_stats.values()
        if s.get("mean_strength_at_completion") is not None and int(s.get("completions", 0)) >= 10
    ]
    legends: list[dict[str, Any]] = []
    for key, stats in combo_stats.items():
        seen = int(stats.get("games_seen", 0))
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
        legends.append({
            "id": key,
            "title": " — ".join(meta[x]["title"] for x in (subject, link, name)),
            "completions": int(stats.get("completions", 0)),
            "games_seen": seen,
            "mean_strength_at_completion": strength,
            "completion_strength_z": strength_z,
            "win_rate_when_seen": stats.get("win_rate_when_seen"),
            "win_rate_when_seen_95": list(ci),
            "flags": flags,
        })

    for flag in global_flags:
        counts[flag["severity"]] += 1

    cards.sort(key=lambda r: (-sum(2 if f["severity"] == "high" else 1 for f in r["flags"]), r["title"]))
    legends.sort(key=lambda r: (-sum(2 if f["severity"] == "high" else 1 for f in r["flags"]), -r["games_seen"], r["title"]))

    return {
        "schema_version": 1,
        "game_fingerprint": simulation.get("game_fingerprint"),
        "simulation_variant": simulation.get("simulation_variant"),
        "source": {"games": games, "agents": simulation["agents"], "wins": simulation["wins"]},
        "global": {
            "first_player_win_rate": fp_rate,
            "first_player_win_rate_95": list(fp_ci),
            "mean_actions": simulation["mean_turns"],
            "max_actions": simulation["max_turns"],
            "passes": telemetry["passes"],
            "battles": telemetry["battles"],
            "flags": global_flags,
        },
        "summary": {
            "cards_analyzed": len(cards),
            "legends_observed": len(legends),
            "flags_high": counts["high"],
            "flags_watch": counts["watch"],
            "flags_diagnostic": counts["diagnostic"],
            "card_levels": dict(Counter(row["balance_level"] for row in cards)),
        },
        "cards": cards,
        "legends": legends,
        "methodology": {
            "win_intervals": "Wilson score interval, 95%",
            "notes": [
                "Conditional win rates are observational rather than causal values.",
                "Board-swing z-scores are computed within card type; cards explicitly marked as delayed utility are not graded on immediate swing.",
                "Playability flags compare each card with the median of its rules family (Subject, Bond, Name, Story, or Veiled Story), so normal structural gating is not mistaken for an individual card defect.",
                "Flags identify cases for inspection; they are not automatic nerf/buff instructions.",
                "Counterfactual and MCCFR reports are merged when explicitly run; neither is required for routine health analysis.",
            ],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    g = report["global"]
    s = report["summary"]
    low, high = g["first_player_win_rate_95"]
    lines = [
        "# The Long War — Balance Health Report",
        "",
        f"Games: **{report['source']['games']}** · Agents: **{' vs '.join(report['source']['agents'])}**  ",
        f"First-player win: **{100*g['first_player_win_rate']:.1f}%** "
        f"(95% Wilson {100*low:.1f}%–{100*high:.1f}%)  ",
        f"High flags: **{s['flags_high']}** · Watch flags: **{s['flags_watch']}** · Diagnostic associations: **{s.get('flags_diagnostic', 0)}**",
        "",
        "## Flagged cards",
        "",
    ]
    for row in [r for r in report["cards"] if r["flags"]]:
        lines.append(f"- **{row['title']}** ({row['type']}): " + ", ".join(f["code"] for f in row["flags"]))
    lines += ["", "## Flagged Subject–Bond–Name sequences", ""]
    for row in [r for r in report["legends"] if r["flags"]][:30]:
        lines.append(f"- **{row['title']}**: " + ", ".join(f["code"] for f in row["flags"]))
    lines += [
        "",
        "## Interpretation",
        "",
        "These flags are diagnostics, not balance verdicts. Wilson intervals reduce small-sample overconfidence; optional counterfactual or MCCFR validation can be run when a stable candidate merits deeper analysis.",
        "",
    ]
    return "\n".join(lines)
