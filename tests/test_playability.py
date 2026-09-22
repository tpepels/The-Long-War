from __future__ import annotations

import pytest

from longwar.playability import build_playability_report, render_markdown


def simulation(*, fingerprint: str = "rules-a") -> dict:
    return {
        "games": 10,
        "mean_turns": 30.0,
        "game_fingerprint": fingerprint,
        "telemetry": {
            "actions": {
                "ChooseFirst": 5,
                "Draw": 10,
                "Pass": 50,
                "PlayLink": 25,
                "PlayName": 10,
                "PlayPlot": 5,
                "PlayScheme": 10,
                "PlaySubject": 50,
                "SetStratagem": 15,
            },
            "battles": {"count": 25},
            "passes": {
                "events": 50,
                "mean_hand_size": 4.0,
                "mean_dead_cards": 1.0,
                "first_passer_battle_win_rate": 0.4,
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
            "legend_combinations": {
                "a | b | c": {"completions": 10}
            },
            "decisions": {
                "heuristic": {
                    "decisions": 100,
                    "mean_candidate_count": 12.0,
                }
            },
        },
    }


def test_build_playability_report_derives_human_pacing_metrics() -> None:
    report = build_playability_report([simulation()])

    assert report["scope"] == {
        "simulation_reports": 1,
        "games": 10,
        "battles": 25,
    }
    assert report["match_pacing"]["mean_battles_per_match"] == 2.5
    assert report["match_pacing"]["two_battle_matches"] == 5
    assert report["match_pacing"]["three_battle_matches"] == 5
    assert report["match_pacing"]["mean_cards_played_per_match"] == 11.5

    battle = report["battle_pacing"]
    assert battle["mean_action_events_per_battle"] == 7.0
    assert battle["mean_normal_turn_actions_per_battle"] == 6.4
    assert battle["mean_cards_played_per_battle"] == 4.6
    assert battle["mean_complete_legends_created_per_battle"] == 0.4

    assert report["draw"]["opportunity_use_rate"] == 0.2
    assert report["stratagem"]["opportunity_use_rate"] == 0.3
    assert report["hand_pressure"]["dead_card_share_at_pass"] == 0.25
    assert report["hand_pressure"]["unplayable_card_turn_share"] == 0.25
    assert report["passing"]["first_passer_battle_win_rate"] == 0.4
    assert report["decision_load"]["mean_legal_candidates_per_heuristic_decision"] == 12.0

    markdown = render_markdown(report)
    assert "Cards played per Battle" in markdown
    assert "Draw opportunity used" in markdown
    assert "AI self-play measures structural pacing" in markdown


def test_playability_report_refuses_to_mix_rulesets() -> None:
    with pytest.raises(ValueError, match="different game fingerprints"):
        build_playability_report(
            [simulation(fingerprint="rules-a"), simulation(fingerprint="rules-b")]
        )
