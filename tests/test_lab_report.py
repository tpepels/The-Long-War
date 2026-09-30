from __future__ import annotations

import json

import pytest

from longwar.health import analyze_simulation, simulation_summary
from longwar.rules import GameRules
from tools import build_lab_report, build_mccfr_suite


def standard_variant(**extra):
    variant = build_lab_report.serialized_rule_metadata(GameRules.standard())
    variant["card_file"] = "cards/cards.json"
    variant.update(extra)
    return variant


def test_health_preserves_source_fingerprint() -> None:
    provenance = {"command_cap": 20}
    report = analyze_simulation(
        {
            "game_fingerprint": "old-engine",
            "simulation_variant": provenance,
            "games": 2,
            "agents": ["random", "random"],
            "wins": [1, 1],
            "first_player_wins": 1,
            "mean_turns": 20,
            "max_turns": 25,
            "telemetry": {"cards": {}, "passes": {}, "battles": {}},
        },
        {"cards": []},
    )
    assert report["game_fingerprint"] == "old-engine"
    assert report["simulation_variant"] == provenance


@pytest.mark.parametrize("fingerprint", [None, "old-engine"])
def test_lab_rejects_stale_or_unidentified_health(monkeypatch, fingerprint) -> None:
    artifacts = {
        "balance-health.json": {"game_fingerprint": fingerprint},
        "balance-report.json": {"game_fingerprint": "current-engine"},
    }
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: "current-engine",
    )
    monkeypatch.setattr(build_lab_report, "load", artifacts.get)
    with pytest.raises(SystemExit, match="current balance-health.json"):
        build_lab_report.main()


def test_lab_rejects_stale_static_report(monkeypatch) -> None:
    artifacts = {
        "balance-health.json": {"game_fingerprint": "current-engine"},
        "balance-report.json": {"game_fingerprint": "old-engine"},
    }
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: "current-engine",
    )
    monkeypatch.setattr(build_lab_report, "load", artifacts.get)
    with pytest.raises(SystemExit, match="current balance-report.json"):
        build_lab_report.main()


def test_lab_accepts_complete_explicit_standard_provenance() -> None:
    assert build_lab_report.canonical_variant({
        "simulation_variant": standard_variant(),
    })


def test_lab_rejects_profile_labels_instead_of_explicit_rules() -> None:
    assert not build_lab_report.canonical_variant({
        "simulation_variant": {
            "rules_profile": "standard",
            "card_file": "cards/cards.json",
        },
    })


def test_lab_rejects_incomplete_or_nonstandard_provenance() -> None:
    incomplete = {"command_cap": 20, "card_file": "cards/cards.json"}
    assert not build_lab_report.canonical_variant({
        "simulation_variant": incomplete,
    })

    changed = standard_variant(starting_command=19)
    assert not build_lab_report.canonical_variant({
        "simulation_variant": changed,
    })

    old_floor = standard_variant(command_recovery_floor=0)
    assert not build_lab_report.canonical_variant({
        "simulation_variant": old_floor,
    })

    wrong_cards = standard_variant(card_file="cards/noncanonical.json")
    assert not build_lab_report.canonical_variant({
        "simulation_variant": wrong_cards,
    })


def test_lab_rejects_experimental_health_with_current_source(monkeypatch) -> None:
    artifacts = {
        "balance-health.json": {
            "game_fingerprint": "current",
            "simulation_variant": standard_variant(starting_command=19),
        },
        "balance-report.json": {"game_fingerprint": "current"},
    }
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: "current",
    )
    monkeypatch.setattr(build_lab_report, "load", artifacts.get)
    with pytest.raises(SystemExit, match="current balance-health.json"):
        build_lab_report.main()


def test_report_builders_share_simulation_summary_and_preserve_provenance() -> None:
    provenance = standard_variant()
    data = {
        "games": 2,
        "decisive_games": 1,
        "censored_games": 1,
        "censor_rate": 0.5,
        "seed": 37,
        "game_fingerprint": "current-engine",
        "experiment_fingerprint": "current-runner",
        "ismcts_config": {"iterations": 100000, "exploration": 0.3},
        "simulation_variant": provenance,
        "telemetry": {"policy_sources": {"search": 12}},
    }
    assert build_lab_report.simulation_summary is simulation_summary
    assert build_mccfr_suite.simulation_summary is simulation_summary
    summary = simulation_summary(data)
    assert summary["seed"] == 37
    assert summary["decisive_games"] == 1
    assert summary["censored_games"] == 1
    assert summary["censor_rate"] == 0.5
    assert summary["game_fingerprint"] == "current-engine"
    assert summary["experiment_fingerprint"] == "current-runner"
    assert summary["ismcts_config"] == data["ismcts_config"]
    assert summary["simulation_variant"] == provenance
    assert summary["policy_sources"] == {"search": 12}



def test_lab_report_surfaces_progression_from_current_selfplay(tmp_path, monkeypatch) -> None:
    fingerprint = "current-engine"
    progression = {
        "by_battle": {
            "1": {
                "battles": 1,
                "command_remaining": 14.0,
                "first_pass_command": 12.0,
                "occupied_positions": 3.0,
                "active_fronts": 2.0,
                "contested_fronts": 1.0,
                "completed_formations": 0.5,
                "incomplete_formations_end": 2.0,
                "eventual_completion_rate_for_forces_deployed": 0.4,
                "cards_played": 6.0,
                "legal_actions": 7.0,
                "hand_size": 7.0,
                "deck_size": 17.0,
                "command_start": 20.0,
            },
            "2": {"battles": 0},
            "3": {
                "battles": 1,
                "command_remaining": 7.0,
                "first_pass_command": 6.0,
                "occupied_positions": 5.0,
                "active_fronts": 3.0,
                "contested_fronts": 2.0,
                "completed_formations": 1.5,
                "incomplete_formations_end": 1.0,
                "eventual_completion_rate_for_forces_deployed": 0.7,
                "cards_played": 5.0,
                "legal_actions": 5.0,
                "hand_size": 6.0,
                "deck_size": 8.0,
                "command_start": 11.0,
            },
        },
        "formation_lifecycle": {"forces": 2},
    }
    artifacts = {
        "balance-health.json": {
            "game_fingerprint": fingerprint,
            "cards": [],
            "formations": [],
        },
        "balance-report.json": {
            "game_fingerprint": fingerprint,
            "card_static_marginals": [],
            "all_static_formations": [],
        },
        "heuristic-selfplay.json": {
            "game_fingerprint": fingerprint,
            "simulation_variant": standard_variant(),
            "games": 1,
            "agents": ["heuristic", "heuristic"],
            "wins": [1, 0],
            "telemetry": {"progression": progression},
        },
    }
    monkeypatch.setattr(build_lab_report, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: fingerprint,
    )
    for name, payload in artifacts.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    build_lab_report.main()

    report = json.loads(
        (tmp_path / "lab-report.json").read_text(encoding="utf-8")
    )
    assert report["progression"] == progression
    assert "raw_telemetry" not in report
    assert report["dashboard_telemetry"] == {}
    trajectory = report["progression_trajectory"]
    assert trajectory["observed_buckets"] == ["1", "3"]
    assert trajectory["early_battle"] == "1"
    assert trajectory["late_battle"] == "3"
    assert trajectory["metrics"]["command_remaining"] == {
        "early": 14.0,
        "late": 7.0,
        "delta": -7.0,
    }
    assert trajectory["metrics"]["occupied_positions"]["delta"] == 2.0
    assert trajectory["metrics"][
        "eventual_completion_rate_for_forces_deployed"
    ]["delta"] == pytest.approx(0.3)
    assert report["all_formations"] == []

def test_progression_trajectory_handles_missing_or_single_bucket() -> None:
    assert build_lab_report.progression_trajectory(None) is None
    assert build_lab_report.progression_trajectory({"by_battle": {}}) is None

    result = build_lab_report.progression_trajectory({
        "by_battle": {
            "1": {
                "battles": 2,
                "command_remaining": 13.5,
            },
            "2": {"battles": 0},
        }
    })
    assert result is not None
    assert result["observed_buckets"] == ["1"]
    assert result["early_battle"] == result["late_battle"] == "1"
    assert result["metrics"]["command_remaining"]["delta"] == 0.0
    assert result["metrics"]["contested_fronts"]["delta"] is None

def test_mccfr_suite_excludes_censored_games_from_seat_swapped_rate() -> None:
    forward = {
        "games": 10,
        "censored_games": 2,
        "wins": [5, 3],
    }
    reverse = {
        "games": 10,
        "censored_games": 1,
        "wins": [5, 4],
    }

    result = build_mccfr_suite.seat_swapped_evaluation(forward, reverse)

    assert result["games"] == 20
    assert result["decisive_games"] == 17
    assert result["censored_games"] == 3
    assert result["censor_rate"] == pytest.approx(3 / 20)
    assert result["seat_swapped_mccfr_win_rate"] == pytest.approx(9 / 17)

def test_mccfr_suite_profiles_match_current_canonical_decks() -> None:
    assert {profile_id for profile_id, _label, _path in build_mccfr_suite.PROFILES} == {
        "mobility",
        "elite",
        "narrative",
        "control",
        "momentum",
        "necessity",
    }
    assert len(build_mccfr_suite.PROFILES) == 6

def test_lab_can_promote_observationally_unobserved_card_with_causal_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    fingerprint = "current-engine"
    artifacts = {
        "balance-health.json": {
            "game_fingerprint": fingerprint,
            "simulation_variant": standard_variant(),
            "cards": [{
                "id": "card-a",
                "title": "Card A",
                "balance_level": "unobserved",
                "balance_label": "Unobserved",
                "balance_direction": "unobserved",
                "observed": False,
            }],
            "formations": [],
        },
        "balance-report.json": {
            "game_fingerprint": fingerprint,
            "card_static_marginals": [],
            "all_static_formations": [],
        },
        "counterfactual-balance.json": {
            "game_fingerprint": fingerprint,
            "cards": [{
                "id": "card-a",
                "samples": 12,
                "level": "yellow",
                "direction": "strong",
                "delta_win_probability": 0.08,
                "ci95": [0.01, 0.15],
            }],
        },
    }
    monkeypatch.setattr(build_lab_report, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: fingerprint,
    )
    for name, payload in artifacts.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    build_lab_report.main()
    report = json.loads((tmp_path / "lab-report.json").read_text())
    card = report["health"]["cards"][0]

    assert card["observed"] is False
    assert card["observational_balance_level"] == "unobserved"
    assert card["balance_level"] == "yellow"
    assert card["balance_label"] == "Watch"
    assert card["balance_direction"] == "heuristic_counterfactual_screen"
    assert card["balance_evidence_source"] == "heuristic_screen"
    assert card["counterfactual"]["direction"] == "strong"

def test_broad_counterfactual_is_only_a_screen_until_online_confirmation(
    tmp_path,
    monkeypatch,
) -> None:
    fingerprint = "current-engine"
    base_artifacts = {
        "balance-health.json": {
            "game_fingerprint": fingerprint,
            "simulation_variant": standard_variant(),
            "cards": [{
                "id": "card-a",
                "title": "Card A",
                "balance_level": "green",
                "balance_label": "Looks healthy",
                "balance_direction": "neutral",
                "observed": True,
            }],
            "formations": [],
        },
        "balance-report.json": {
            "game_fingerprint": fingerprint,
            "card_static_marginals": [],
            "all_static_formations": [],
        },
        "counterfactual-balance.json": {
            "game_fingerprint": fingerprint,
            "cards": [{
                "id": "card-a",
                "samples": 12,
                "level": "red",
                "direction": "stronger_than_baseline",
                "delta_win_probability": 0.2,
                "ci95": [0.08, 0.3],
                "confidence_excludes_zero": True,
            }],
        },
    }
    monkeypatch.setattr(build_lab_report, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: fingerprint,
    )
    for name, payload in base_artifacts.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    build_lab_report.main()
    screened = json.loads((tmp_path / "lab-report.json").read_text())["health"]["cards"][0]
    assert screened["balance_level"] == "yellow"
    assert screened["balance_evidence_source"] == "heuristic_screen"

    targeted = {
        "game_fingerprint": fingerprint,
        "cards": [{
            "cards": ["card-a"],
            "confirmation": "confirmed",
            "online": {
                "samples": 8,
                "level": "red",
                "direction": "stronger_than_baseline",
                "effect": 0.16,
                "ci95": [0.04, 0.27],
            },
        }],
    }
    (tmp_path / "targeted-online-counterfactual.json").write_text(
        json.dumps(targeted),
        encoding="utf-8",
    )
    build_lab_report.main()
    confirmed = json.loads((tmp_path / "lab-report.json").read_text())["health"]["cards"][0]
    assert confirmed["balance_level"] == "red"
    assert confirmed["balance_evidence_source"] == "online_mccfr"


def test_lab_uses_aggregate_selfplay_for_matchup_and_detailed_progression_source(
    tmp_path,
    monkeypatch,
) -> None:
    fingerprint = "current-engine"
    aggregate = {
        "game_fingerprint": fingerprint,
        "simulation_variant": standard_variant(),
        "games": 60,
        "decisive_games": 58,
        "censored_games": 2,
        "censor_rate": 2 / 60,
        "agents": ["heuristic", "heuristic"],
        "wins": [29, 29],
        "win_rates": [0.5, 0.5],
        "first_player_win_rate": 0.5,
        "mean_turns": 40.0,
        "max_turns": 500,
        "_label": "Six canonical same-deck self-play aggregate",
        "telemetry": {
            "passes": {},
            "battles": {},
            "cards": {},
            "formation_combinations": {},
        },
    }
    progression = {
        "by_battle": {"1": {"battles": 10, "command_remaining": 14.0}},
        "formation_lifecycle": {"forces": 20},
    }
    detailed = {
        "game_fingerprint": fingerprint,
        "simulation_variant": standard_variant(),
        "games": 10,
        "decisive_games": 9,
        "censored_games": 1,
        "agents": ["heuristic", "heuristic"],
        "wins": [5, 4],
        "_label": "Mobility / Open Bonds self-play",
        "progression_scope": "Detailed progression reference.",
        "telemetry": {"progression": progression},
    }
    artifacts = {
        "balance-health.json": {
            "game_fingerprint": fingerprint,
            "cards": [],
            "formations": [],
        },
        "balance-report.json": {
            "game_fingerprint": fingerprint,
            "card_static_marginals": [],
            "all_static_formations": [],
        },
        "heuristic-selfplay.json": aggregate,
        "progression-selfplay.json": detailed,
    }
    monkeypatch.setattr(build_lab_report, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: fingerprint,
    )
    for name, payload in artifacts.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    build_lab_report.main()
    report = json.loads((tmp_path / "lab-report.json").read_text())

    assert report["matchups"]["heuristic_selfplay"]["games"] == 60
    assert report["progression"] == progression
    assert "raw_telemetry" not in report
    assert report["dashboard_telemetry"] == {}
    assert report["progression_source"] == {
        "label": "Mobility / Open Bonds self-play",
        "scope": "Detailed progression reference.",
        "games": 10,
        "decisive_games": 9,
        "censored_games": 1,
    }



def test_lab_report_keeps_same_fingerprint_agent_recovery_comparisons(
    tmp_path,
    monkeypatch,
) -> None:
    fingerprint = "current-engine"
    artifacts = {
        "balance-health.json": {
            "game_fingerprint": fingerprint,
            "cards": [],
            "formations": [],
        },
        "balance-report.json": {
            "game_fingerprint": fingerprint,
            "card_static_marginals": [],
            "all_static_formations": [],
        },
        "balance-comparisons.json": {
            "schema_version": 1,
            "game_fingerprint": fingerprint,
            "profiles": {
                "heuristic--recovery-12-3": {
                    "agent": "heuristic",
                    "recovery_start": 12,
                    "recovery_decrement": 3,
                },
                "ismcts--recovery-10-2": {
                    "agent": "ismcts",
                    "recovery_start": 10,
                    "recovery_decrement": 2,
                },
                "ismcts--recovery-12-3": {
                    "agent": "ismcts",
                    "recovery_start": 12,
                    "recovery_decrement": 3,
                    "recovery_floor": 1,
                },
            },
        },
    }
    monkeypatch.setattr(build_lab_report, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: fingerprint,
    )
    for name, payload in artifacts.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    build_lab_report.main()
    report = json.loads((tmp_path / "lab-report.json").read_text())
    assert set(report["balance_comparisons"]["profiles"]) == {
        "heuristic--recovery-12-3",
        "ismcts--recovery-10-2",
        "ismcts--recovery-12-3",
    }
    assert (
        report["balance_comparisons"]["profiles"]["ismcts--recovery-12-3"][
            "recovery_floor"
        ]
        == 1
    )


def test_lab_report_rejects_stale_agent_recovery_comparisons(
    tmp_path,
    monkeypatch,
) -> None:
    fingerprint = "current-engine"
    artifacts = {
        "balance-health.json": {
            "game_fingerprint": fingerprint,
            "cards": [],
            "formations": [],
        },
        "balance-report.json": {
            "game_fingerprint": fingerprint,
            "card_static_marginals": [],
            "all_static_formations": [],
        },
        "balance-comparisons.json": {
            "schema_version": 1,
            "game_fingerprint": "old-engine",
            "profiles": {"heuristic--current": {}},
        },
    }
    monkeypatch.setattr(build_lab_report, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(
        build_lab_report,
        "current_game_fingerprint",
        lambda: fingerprint,
    )
    for name, payload in artifacts.items():
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")

    build_lab_report.main()
    report = json.loads((tmp_path / "lab-report.json").read_text())
    assert report["balance_comparisons"] is None
    assert "balance-comparisons.json" in report["stale_evidence"]


def test_progression_trajectory_uses_battle_eight_plus_when_observed() -> None:
    result = build_lab_report.progression_trajectory({
        "by_battle": {
            "1": {"battles": 2, "command_remaining": 14.0},
            "4-7": {"battles": 1, "command_remaining": 6.0},
            "8+": {"battles": 3, "command_remaining": 1.0},
        }
    })
    assert result is not None
    assert result["observed_buckets"] == ["1", "4-7", "8+"]
    assert result["early_battle"] == "1"
    assert result["late_battle"] == "8+"
    assert result["metrics"]["command_remaining"] == {
        "early": 14.0,
        "late": 1.0,
        "delta": -13.0,
    }


def test_lab_builder_does_not_grade_stale_optional_legacy_fallbacks_as_current_evidence():
    source = (build_lab_report.ROOT / "tools" / "build_lab_report.py").read_text(
        encoding="utf-8"
    )
    assert 'current("mccfr-policy.json", track_stale=False)' in source
    assert 'track_stale=(key == "canonical_selfplay")' in source
    assert 'solver_strength = current("solver-strength.json")' in source
    assert '"narrative_ablation": narrative_ablation' in source
