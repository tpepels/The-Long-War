from __future__ import annotations

import pytest

from longwar.health import analyze_simulation, simulation_summary
from tools import build_lab_report, build_mccfr_suite


def test_health_preserves_source_fingerprint() -> None:
    report = analyze_simulation(
        {
            "game_fingerprint": "old-engine",
            "simulation_variant": {"rules_profile": "standard"},
            "games": 2, "agents": ["random", "random"], "wins": [1, 1],
            "first_player_wins": 1, "mean_turns": 20, "max_turns": 25,
            "telemetry": {"cards": {}, "passes": {}, "battles": {}},
        },
        {"cards": []},
    )
    assert report["game_fingerprint"] == "old-engine"
    assert report["simulation_variant"] == {"rules_profile": "standard"}


@pytest.mark.parametrize("fingerprint", [None, "old-engine"])
def test_lab_rejects_stale_or_unidentified_health(monkeypatch, fingerprint) -> None:
    artifacts = {
        "balance-health.json": {"game_fingerprint": fingerprint},
        "balance-report.json": {"game_fingerprint": "current-engine"},
    }
    monkeypatch.setattr(build_lab_report, "current_game_fingerprint", lambda: "current-engine")
    monkeypatch.setattr(build_lab_report, "load", artifacts.get)
    with pytest.raises(SystemExit, match="current balance-health.json"):
        build_lab_report.main()


def test_lab_rejects_stale_static_report(monkeypatch) -> None:
    artifacts = {
        "balance-health.json": {"game_fingerprint": "current-engine"},
        "balance-report.json": {"game_fingerprint": "old-engine"},
    }
    monkeypatch.setattr(build_lab_report, "current_game_fingerprint", lambda: "current-engine")
    monkeypatch.setattr(build_lab_report, "load", artifacts.get)
    with pytest.raises(SystemExit, match="current balance-report.json"):
        build_lab_report.main()


def test_lab_accepts_named_standard_provenance() -> None:
    assert build_lab_report.canonical_variant({
        "simulation_variant": {
            "rules_profile": "standard",
            "card_file": "cards/cards.json",
        },
    })


def test_lab_accepts_complete_custom_standard_provenance() -> None:
    variant = {
        "rules_profile": "custom",
        "base_hand_size": 10,
        "draw_action_enabled": False,
        "completion_draw_names": [],
        "recycle_between_battles": False,
        "reshuffle_on_empty": True,
        "command_enabled": True,
        "starting_command": 20,
        "battle_command_gain": 10,
        "command_cap": 20,
        "cycle_command_cost": None,
        "cycle_enabled": False,
        "automatic_draw": True,
        "paid_draw_enabled": False,
        "paid_draw_command_cost": None,
        "paid_draw_consumes_operation": True,
        "automatic_draw_hand_limit": None,
        "battle_end_hand_limit": None,
        "pass_final_operation": True,
        "pass_requires_both_acted": True,
        "first_passer_starts_next_battle": True,
        "completion_command_refund": 1,
        "public_stratagems": True,
        "card_file": "cards/cards.json",
    }
    assert build_lab_report.canonical_variant({"simulation_variant": variant})


@pytest.mark.parametrize("variant", [
    {"rules_profile": "force-automatic"},
    {"rules_profile": "custom", "automatic_draw": True},
    {"rules_profile": "standard", "card_file": "cards/noncanonical.json"},
])
def test_lab_rejects_experimental_health_with_current_source(monkeypatch, variant):
    artifacts = {
        "balance-health.json": {"game_fingerprint": "current", "simulation_variant": variant},
        "balance-report.json": {"game_fingerprint": "current"},
    }
    monkeypatch.setattr(build_lab_report, "current_game_fingerprint", lambda: "current")
    monkeypatch.setattr(build_lab_report, "load", artifacts.get)
    with pytest.raises(SystemExit, match="current balance-health.json"):
        build_lab_report.main()


def test_report_builders_share_simulation_summary_and_preserve_provenance() -> None:
    data = {
        "games": 2, "seed": 37, "game_fingerprint": "current-engine",
        "ismcts_config": {"iterations": 100000, "exploration": 0.3},
        "simulation_variant": {"rules_profile": "standard"},
        "telemetry": {"policy_sources": {"search": 12}},
    }
    assert build_lab_report.simulation_summary is simulation_summary
    assert build_mccfr_suite.simulation_summary is simulation_summary
    summary = simulation_summary(data)
    assert summary["seed"] == 37
    assert summary["game_fingerprint"] == "current-engine"
    assert summary["ismcts_config"] == data["ismcts_config"]
    assert summary["simulation_variant"] == data["simulation_variant"]
    assert summary["policy_sources"] == {"search": 12}
