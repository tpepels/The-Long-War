from __future__ import annotations

import pytest

from longwar.health import (
    aggregate_simulations_for_health,
    analyze_simulation,
    wilson_interval,
)


def test_wilson_interval_contains_half_for_even_sample() -> None:
    low, high = wilson_interval(50, 100)
    assert low is not None and high is not None
    assert low < 0.5 < high


def test_health_flags_dead_card_and_strong_outcome() -> None:
    cards = {
        "schema_version": 1,
        "cards": [
            {
                "id": "test-card",
                "title": "Test Card",
                "type": "name",
                "strength": 1,
                "unique": True,
                "text": "",
                "rules": {},
                "balance": {},
            },
            {
                "id": "baseline-card",
                "title": "Baseline Card",
                "type": "name",
                "strength": 2,
                "unique": True,
                "text": "",
                "rules": {},
                "balance": {},
            },
        ],
    }
    simulation = {
        "games": 200,
        "agents": ["heuristic", "heuristic"],
        "wins": [100, 100],
        "first_player_wins": 100,
        "mean_turns": 30.0,
        "max_turns": 42,
        "telemetry": {
            "passes": {},
            "battles": {},
            "cards": {
                "test-card": {
                    "draws": 200,
                    "plays": 50,
                    "turns_in_hand": 400,
                    "playable_turns": 100,
                    "unplayable_turns": 300,
                    "held_on_pass": 100,
                    "dead_on_pass": 60,
                    "mean_immediate_front_swing": 1.0,
                    "mean_immediate_control_swing": 0.0,
                    "games_drawn": 180,
                    "wins_when_drawn": 90,
                    "games_played": 120,
                    "wins_when_played": 90,
                    "play_rate_per_draw": 0.25,
                    "unplayable_turn_rate": 0.75,
                    "dead_on_pass_rate": 0.60,
                    "win_rate_when_drawn": 0.50,
                    "win_rate_when_played": 0.75,
                },
                "baseline-card": {
                    "draws": 200,
                    "plays": 150,
                    "turns_in_hand": 400,
                    "playable_turns": 360,
                    "unplayable_turns": 40,
                    "held_on_pass": 100,
                    "dead_on_pass": 10,
                    "mean_immediate_front_swing": 1.0,
                    "mean_immediate_control_swing": 0.0,
                    "games_drawn": 180,
                    "wins_when_drawn": 90,
                    "games_played": 120,
                    "wins_when_played": 60,
                    "play_rate_per_draw": 0.75,
                    "unplayable_turn_rate": 0.10,
                    "dead_on_pass_rate": 0.10,
                    "win_rate_when_drawn": 0.50,
                    "win_rate_when_played": 0.50,
                },
            },
            "formation_combinations": {},
        },
    }
    report = analyze_simulation(simulation, cards)
    codes = {flag["code"] for flag in report["cards"][0]["flags"]}
    assert {"low_conversion", "dead_draw", "dead_on_pass", "positive_outcome_association"} <= codes



def test_delayed_utility_is_not_judged_by_immediate_swing() -> None:
    card_rows = []
    telemetry_cards = {}
    for index, swing in enumerate([0.0, 3.0, 3.0, 3.0, 3.0]):
        card_id = f"link-{index}"
        card_rows.append({
            "id": card_id,
            "title": f"Link {index}",
            "type": "link",
            "unique": False,
            "text": "",
            "rules": {},
            "balance": {"delayed_utility": index == 0},
        })
        telemetry_cards[card_id] = {
            "draws": 200,
            "plays": 120,
            "turns_in_hand": 300,
            "playable_turns": 240,
            "unplayable_turns": 60,
            "held_on_pass": 80,
            "dead_on_pass": 20,
            "mean_immediate_front_swing": swing,
            "mean_immediate_control_swing": 0.5,
            "games_drawn": 180,
            "wins_when_drawn": 90,
            "games_played": 120,
            "wins_when_played": 60,
            "play_rate_per_draw": 2 / 3,
            "unplayable_turn_rate": 0.2,
            "dead_on_pass_rate": 0.25,
            "win_rate_when_drawn": 0.5,
            "win_rate_when_played": 0.5,
        }

    report = analyze_simulation(
        {
            "games": 200,
            "agents": ["heuristic", "heuristic"],
            "wins": [100, 100],
            "first_player_wins": 100,
            "mean_turns": 30.0,
            "max_turns": 42,
            "telemetry": {
                "passes": {},
                "battles": {},
                "cards": telemetry_cards,
                "formation_combinations": {},
            },
        },
        {"schema_version": 1, "cards": card_rows},
    )

    delayed = next(row for row in report["cards"] if row["id"] == "link-0")
    assert delayed["delayed_utility"] is True
    assert "board_swing_outlier" not in {
        flag["code"] for flag in delayed["flags"]
    }

def test_combo_outcome_association_is_diagnostic_not_balance_failure() -> None:
    cards = {
        "schema_version": 1,
        "cards": [
            {"id": "subject", "title": "Subject", "type": "subject", "strength": 4, "unique": False, "classes": ["human"], "role": "swordsman", "text": "", "rules": {}, "balance": {}},
            {"id": "bond", "title": "Bond", "type": "link", "unique": False, "classes": ["oath"], "text": "", "rules": {"strength_bonus": 1}, "balance": {}},
            {"id": "name", "title": "Name", "type": "name", "strength": 2, "unique": True, "classes": ["human"], "text": "", "rules": {}, "balance": {}},
        ],
    }
    neutral = {
        "draws": 200, "plays": 100, "turns_in_hand": 300,
        "playable_turns": 240, "unplayable_turns": 60,
        "held_on_pass": 80, "dead_on_pass": 20,
        "mean_immediate_front_swing": 1.0,
        "mean_immediate_control_swing": 0.0,
        "games_drawn": 150, "wins_when_drawn": 75,
        "games_played": 100, "wins_when_played": 50,
        "play_rate_per_draw": 0.5, "unplayable_turn_rate": 0.2,
        "dead_on_pass_rate": 0.25, "win_rate_when_drawn": 0.5,
        "win_rate_when_played": 0.5,
    }
    report = analyze_simulation(
        {
            "games": 200,
            "agents": ["heuristic", "heuristic"],
            "wins": [100, 100],
            "first_player_wins": 100,
            "mean_turns": 30.0,
            "max_turns": 42,
            "telemetry": {
                "passes": {},
                "battles": {},
                "cards": {key: dict(neutral) for key in ("subject", "bond", "name")},
                "formation_combinations": {
                    "subject | bond | name": {
                        "games_seen": 100,
                        "wins_when_seen": 80,
                        "win_rate_when_seen": 0.8,
                        "completions": 20,
                        "mean_strength_at_completion": 9.0,
                    }
                },
            },
        },
        cards,
    )
    combo = report["formations"][0]
    assert combo["flags"][0]["code"] == "combo_positive_association"
    assert combo["flags"][0]["severity"] == "diagnostic"
    assert report["summary"]["flags_high"] == 0
    assert report["summary"]["flags_diagnostic"] == 1
    assert report["summary"]["formations_observed"] == 1

def test_health_keeps_unobserved_canonical_cards_explicit() -> None:
    cards = {
        "schema_version": 1,
        "cards": [
            {
                "id": "observed-card",
                "title": "Observed Card",
                "type": "force",
                "strength": 3,
                "unique": False,
                "text": "",
                "rules": {},
                "balance": {},
            },
            {
                "id": "unobserved-card",
                "title": "Unobserved Card",
                "type": "bond",
                "unique": False,
                "text": "",
                "rules": {},
                "balance": {},
            },
        ],
    }
    report = analyze_simulation(
        {
            "games": 10,
            "agents": ["heuristic", "heuristic"],
            "wins": [5, 5],
            "first_player_wins": 5,
            "mean_turns": 20.0,
            "max_turns": 30,
            "telemetry": {
                "passes": {},
                "battles": {},
                "cards": {
                    "observed-card": {
                        "draws": 10,
                        "plays": 4,
                        "turns_in_hand": 15,
                        "playable_turns": 10,
                        "unplayable_turns": 5,
                        "held_on_pass": 3,
                        "dead_on_pass": 1,
                        "games_drawn": 8,
                        "wins_when_drawn": 4,
                        "games_played": 4,
                        "wins_when_played": 2,
                        "play_rate_per_draw": 0.5,
                        "unplayable_turn_rate": 1 / 3,
                        "dead_on_pass_rate": 1 / 3,
                        "mean_immediate_front_swing": 1.0,
                        "mean_immediate_control_swing": 0.0,
                        "win_rate_when_drawn": 0.5,
                        "win_rate_when_played": 0.5,
                    },
                },
                "formation_combinations": {},
            },
        },
        cards,
    )

    assert report["summary"]["cards_analyzed"] == 2
    assert report["summary"]["cards_observed"] == 1
    assert report["summary"]["cards_unobserved"] == 1
    rows = {row["id"]: row for row in report["cards"]}
    assert rows["observed-card"]["observed"] is True
    assert rows["unobserved-card"]["observed"] is False
    assert rows["unobserved-card"]["balance_level"] == "unobserved"
    assert rows["unobserved-card"]["balance_label"] == "Unobserved"
    assert rows["unobserved-card"]["balance_direction"] == "unobserved"
    assert rows["unobserved-card"]["draws"] == 0
    assert rows["unobserved-card"]["play_rate_per_draw"] is None
    assert rows["unobserved-card"]["win_rate_when_played_95"] == [None, None]

def test_health_aggregation_sums_raw_counts_before_deriving_rates() -> None:
    base = {
        "agents": ["heuristic", "heuristic"],
        "game_fingerprint": "rules-a",
        "simulation_variant": {"base_hand_size": 10},
        "max_turns": 40,
    }
    first = {
        **base,
        "games": 2,
        "censored_games": 0,
        "wins": [1, 1],
        "first_player_wins": 1,
        "mean_turns": 20.0,
        "telemetry": {
            "passes": {"events": 4, "mean_hand_size": 6.0},
            "battles": {"count": 5, "mean_actions": 8.0, "continuing_battles": 3},
            "cards": {
                "card-a": {
                    "draws": 10,
                    "plays": 4,
                    "turns_in_hand": 20,
                    "playable_turns": 15,
                    "unplayable_turns": 5,
                    "held_on_pass": 4,
                    "dead_on_pass": 1,
                    "immediate_front_swing_total": 8.0,
                    "immediate_control_swing_total": 2.0,
                    "games_drawn": 4,
                    "decisive_games_drawn": 4,
                    "wins_when_drawn": 2,
                    "games_played": 2,
                    "decisive_games_played": 2,
                    "wins_when_played": 1,
                }
            },
            "formation_combinations": {},
        },
    }
    second = {
        **base,
        "games": 1,
        "censored_games": 1,
        "wins": [0, 0],
        "first_player_wins": 0,
        "mean_turns": 40.0,
        "telemetry": {
            "passes": {"events": 2, "mean_hand_size": 3.0},
            "battles": {"count": 2, "mean_actions": 10.0, "continuing_battles": 2},
            "cards": {
                "card-a": {
                    "draws": 6,
                    "plays": 3,
                    "turns_in_hand": 12,
                    "playable_turns": 9,
                    "unplayable_turns": 3,
                    "held_on_pass": 2,
                    "dead_on_pass": 1,
                    "immediate_front_swing_total": 9.0,
                    "immediate_control_swing_total": 3.0,
                    "games_drawn": 2,
                    "decisive_games_drawn": 0,
                    "wins_when_drawn": 0,
                    "games_played": 2,
                    "decisive_games_played": 0,
                    "wins_when_played": 0,
                }
            },
            "formation_combinations": {},
        },
    }

    aggregate = aggregate_simulations_for_health([first, second])
    stats = aggregate["telemetry"]["cards"]["card-a"]

    assert aggregate["games"] == 3
    assert aggregate["decisive_games"] == 2
    assert aggregate["censored_games"] == 1
    assert aggregate["wins"] == [1, 1]
    assert aggregate["mean_turns"] == pytest.approx(80 / 3)
    assert stats["draws"] == 16
    assert stats["plays"] == 7
    assert stats["games_drawn"] == 6
    assert stats["decisive_games_drawn"] == 4
    assert stats["games_played"] == 4
    assert stats["decisive_games_played"] == 2
    assert stats["play_rate_per_draw"] == pytest.approx(4 / 6)
    assert stats["win_rate_when_drawn"] == pytest.approx(0.5)
    assert stats["win_rate_when_played"] == pytest.approx(0.5)
    assert stats["mean_immediate_front_swing"] == pytest.approx(17 / 7)
    assert aggregate["telemetry"]["passes"]["mean_hand_size"] == pytest.approx(5.0)
    assert aggregate["telemetry"]["battles"]["mean_actions"] == pytest.approx(60 / 7)

