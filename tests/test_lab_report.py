from __future__ import annotations

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
    provenance = {"automatic_draw": True}
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
    incomplete = {"automatic_draw": True, "card_file": "cards/cards.json"}
    assert not build_lab_report.canonical_variant({
        "simulation_variant": incomplete,
    })

    changed = standard_variant(automatic_draw=False)
    assert not build_lab_report.canonical_variant({
        "simulation_variant": changed,
    })

    wrong_cards = standard_variant(card_file="cards/noncanonical.json")
    assert not build_lab_report.canonical_variant({
        "simulation_variant": wrong_cards,
    })


def test_lab_rejects_experimental_health_with_current_source(monkeypatch) -> None:
    artifacts = {
        "balance-health.json": {
            "game_fingerprint": "current",
            "simulation_variant": standard_variant(automatic_draw=False),
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
        "seed": 37,
        "game_fingerprint": "current-engine",
        "ismcts_config": {"iterations": 100000, "exploration": 0.3},
        "simulation_variant": provenance,
        "telemetry": {"policy_sources": {"search": 12}},
    }
    assert build_lab_report.simulation_summary is simulation_summary
    assert build_mccfr_suite.simulation_summary is simulation_summary
    summary = simulation_summary(data)
    assert summary["seed"] == 37
    assert summary["game_fingerprint"] == "current-engine"
    assert summary["ismcts_config"] == data["ismcts_config"]
    assert summary["simulation_variant"] == provenance
    assert summary["policy_sources"] == {"search": 12}
