from __future__ import annotations

from longwar.health import analyze_simulation, wilson_interval


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
            "legend_combinations": {},
        },
    }
    report = analyze_simulation(simulation, cards)
    codes = {flag["code"] for flag in report["cards"][0]["flags"]}
    assert {"low_conversion", "dead_draw", "dead_on_pass", "positive_outcome_association"} <= codes
