from __future__ import annotations

import pytest

from longwar.playability import build_playability_report, render_markdown


def simulation(*, fingerprint: str = "rules-a") -> dict:
    return {
        "games": 10,
        "censored_games": 2,
        "mean_turns": 30.0,
        "game_fingerprint": fingerprint,
        "telemetry": {
            "actions": {
                "Discard": 10,
                "Maneuver": 5,
                "Pass": 50,
                "PlayBond": 25,
                "PlayForce": 50,
                "PlayName": 10,
                "PlayStory": 15,
                "PlayStratagem": 15,
            },
            "battles": {"count": 25},
            "passes": {
                "events": 50,
                "signal_events": 50,
                "mean_hand_size": 4.0,
                "mean_dead_cards": 1.0,
                "first_signal_rate": 0.5,
            },
            "cards": {
                "example": {
                    "draws": 200,
                    "plays": 125,
                    "turns_in_hand": 400,
                    "playable_turns": 300,
                    "unplayable_turns": 100,
                    "held_on_pass": 200,
                    "dead_on_pass": 50,
                }
            },
            "formation_combinations": {
                "a | b | c": {"completions": 10}
            },
            "decisions": {
                "heuristic": {
                    "decisions": 100,
                    "mean_candidate_count": 12.0,
                }
            },
            "progression": {
                "match_length": {
                    "final_battle_number": {
                        "count": 10,
                        "mean": 3.0,
                    },
                    "battle_reach": {
                        "1": {"matches": 10, "rate": 1.0},
                        "2": {"matches": 9, "rate": 0.9},
                        "3": {"matches": 7, "rate": 0.7},
                        "4": {"matches": 3, "rate": 0.3},
                    },
                },
            },
        },
    }


def test_build_playability_report_derives_human_pacing_metrics() -> None:
    report = build_playability_report([simulation()])

    assert report["scope"] == {
        "simulation_reports": 1,
        "games": 10,
        "decisive_games": 8,
        "draws": 0,
        "censored_games": 2,
        "battles": 25,
    }
    match = report["match_pacing"]
    assert match["mean_battles_per_match"] == 2.5
    assert match["mean_resolved_battles_per_match"] == 2.5
    assert match["mean_final_battle_reached"] == 3.0
    assert match["battle_reach"]["3"] == {
        "matches": 7,
        "rate": pytest.approx(0.7),
    }
    assert match["mean_cards_played_per_match"] == 11.5

    battle = report["battle_pacing"]
    assert battle["mean_action_events_per_battle"] == 7.2
    assert battle["mean_action_events_per_player_battle"] == 3.6
    assert battle["mean_cards_played_per_battle"] == 4.6
    assert battle["mean_named_formations_created_per_battle"] == 0.4
    assert battle["mean_maneuvers_per_battle"] == 0.2

    assert report["draw"]["cards_drawn"] == 200
    assert report["stratagem"]["opportunity_use_rate"] == 0.3
    assert report["hand_pressure"]["dead_card_share_at_pass"] == 0.25
    assert report["hand_pressure"]["unplayable_card_turn_share"] == 0.25
    assert report["battle_end_signals"]["first_signal_share"] == 0.5
    assert report["decision_load"]["mean_legal_candidates_per_heuristic_decision"] == 12.0

    markdown = render_markdown(report)
    assert "Resolved Battles per match" in markdown
    assert "2 censored matches" in markdown
    assert "Cards played per Battle" in markdown
    assert "Maneuvers per Battle" in markdown
    assert "AI self-play measures structural pacing" in markdown


def test_playability_accepts_fully_censored_zero_battle_cell() -> None:
    censored = simulation()
    censored["games"] = 1
    censored["censored_games"] = 1
    censored["mean_turns"] = 500.0
    censored["telemetry"]["battles"]["count"] = 0
    censored["telemetry"]["actions"] = {
        name: 0 for name in censored["telemetry"]["actions"]
    }
    censored["telemetry"]["passes"] = {
        "events": 0,
        "signal_events": 0,
        "mean_hand_size": None,
        "mean_dead_cards": None,
        "first_signal_rate": None,
    }
    censored["telemetry"]["cards"] = {}
    censored["telemetry"]["formation_combinations"] = {}
    censored["telemetry"]["decisions"] = {}
    censored["telemetry"]["progression"] = {
        "match_length": {
            "final_battle_number": {"count": 0, "mean": None},
            "battle_reach": {"1": {"matches": 1, "rate": 1.0}},
        },
    }

    report = build_playability_report([simulation(), censored])

    assert report["scope"]["games"] == 11
    assert report["scope"]["censored_games"] == 3
    assert report["scope"]["battles"] == 25
    assert report["by_simulation"][1]["mean_cards_played_per_battle"] is None
    assert report["by_simulation"][1]["mean_action_events_per_battle"] is None
    assert report["match_pacing"]["battle_reach"]["1"]["matches"] == 11


def test_playability_allows_all_games_censored_before_first_resolution() -> None:
    censored = simulation()
    censored["games"] = 1
    censored["censored_games"] = 1
    censored["mean_turns"] = 500.0
    censored["telemetry"]["battles"]["count"] = 0
    censored["telemetry"]["actions"] = {
        name: 0 for name in censored["telemetry"]["actions"]
    }
    censored["telemetry"]["passes"] = {
        "events": 0,
        "signal_events": 0,
        "mean_hand_size": None,
        "mean_dead_cards": None,
        "first_signal_rate": None,
    }
    censored["telemetry"]["cards"] = {}
    censored["telemetry"]["formation_combinations"] = {}
    censored["telemetry"]["decisions"] = {}
    censored["telemetry"]["progression"] = {
        "match_length": {
            "final_battle_number": {"count": 0, "mean": None},
            "battle_reach": {"1": {"matches": 1, "rate": 1.0}},
        },
    }

    report = build_playability_report([censored])

    assert report["scope"] == {
        "simulation_reports": 1,
        "games": 1,
        "decisive_games": 0,
        "draws": 0,
        "censored_games": 1,
        "battles": 0,
    }
    assert report["battle_pacing"]["mean_cards_played_per_battle"] is None
    assert report["battle_end_signals"]["mean_signals_per_battle"] is None
    assert report["stratagem"]["opportunity_use_rate"] is None


def test_playability_report_refuses_to_mix_rulesets() -> None:
    with pytest.raises(ValueError, match="different game fingerprints"):
        build_playability_report(
            [simulation(fingerprint="rules-a"), simulation(fingerprint="rules-b")]
        )
