from __future__ import annotations

from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.counterfactual import build_experiment_card_data, build_samples
from longwar.game import GameEngine
from longwar.targeted_counterfactual import (
    _play_online_outcome,
    _subset_samples,
    run_targeted_online_validation,
    select_targets,
)

ROOT = Path(__file__).resolve().parents[1]


def broad_fixture():
    return {
        "cards": [
            {
                "id": "a",
                "title": "A",
                "delta_win_probability": 0.02,
                "ci95": [-0.02, 0.06],
                "level": "green",
                "confidence_excludes_zero": False,
            },
            {
                "id": "b",
                "title": "B",
                "delta_win_probability": 0.09,
                "ci95": [0.02, 0.15],
                "level": "red",
                "confidence_excludes_zero": True,
            },
        ],
        "pairs": [
            {
                "cards": ["a", "b"],
                "title": "A × B",
                "interaction_delta": -0.06,
                "ci95": [-0.13, 0.01],
                "level": "yellow",
                "confidence_excludes_zero": False,
            },
        ],
        "triples": [],
    }


def test_selector_prefers_supported_and_large_signals() -> None:
    selected = select_targets(
        broad_fixture(),
        max_cards=1,
        max_pairs=1,
        max_triples=0,
        minimum_abs_effect=0.05,
    )
    assert [(row.kind, row.cards) for row in selected] == [
        ("card", ("b",)),
        ("pair", ("a", "b")),
    ]


def test_selector_can_force_top_target_for_ci_smoke() -> None:
    broad = broad_fixture()
    broad["cards"][0]["delta_win_probability"] = 0.0
    broad["cards"][0]["level"] = "green"
    broad["cards"][1]["delta_win_probability"] = 0.0
    broad["cards"][1]["level"] = "green"
    broad["cards"][1]["confidence_excludes_zero"] = False
    broad["pairs"] = []

    selected = select_targets(
        broad,
        max_cards=1,
        max_pairs=0,
        max_triples=0,
        minimum_abs_effect=0.5,
        force_top=True,
    )
    assert len(selected) == 1
    assert selected[0].kind == "card"


def test_targeted_samples_preserve_broad_required_cards_and_seed() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    generation = {"seed": 37, "required_cards": ["namar", "followed"]}
    broad = {"contexts": 3, "games_per_context": 3, "seed": 37, "sample_generation": generation}
    expected = build_samples(data, contexts=3, games_per_context=3, **generation)
    actual = _subset_samples(data, broad, contexts=2, games_per_context=2)
    assert actual == [row for row in expected if row.context_id < 2 and row.sample_id % 3 < 2]


def test_targeted_samples_require_reproducible_source_metadata() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    with pytest.raises(ValueError, match="rerun the broad"):
        _subset_samples(data, {"contexts": 1, "games_per_context": 1, "seed": 37}, contexts=1, games_per_context=1)


def test_targeted_sweep_uses_each_card_context_and_reports_uncertainty(monkeypatch) -> None:
    import longwar.targeted_counterfactual as targeted

    data = load_card_file(ROOT / "cards" / "cards.json")
    generation = {"seed": 104766, "required_cards": ["namar"]}
    broad = {
        "contexts": 2, "games_per_context": 2, "seed": 37,
        "cards": [{
            "id": "namar", "title": "Namar", "delta_win_probability": 1.0,
            "ci95": [-1.0, 1.0], "level": "yellow", "sample_generation": generation,
        }],
    }
    seen = []

    def outcome(engine, sample, focal_deck, **kwargs):
        seen.append(sample)
        return int("namar" in focal_deck)

    monkeypatch.setattr(targeted, "_play_online_outcome", outcome)
    report = run_targeted_online_validation(
        data, broad, contexts=1, games_per_context=1, online_iterations=1,
        online_depth=1, max_cards=1, max_pairs=0, max_triples=0,
    )
    expected = build_samples(data, contexts=2, games_per_context=2, **generation)[0]
    assert seen == [expected, expected]
    assert report["cards"][0]["sample_generation"] == generation
    assert report["cards"][0]["confirmation"] == "direction_agrees"
    assert report["cards"][0]["online"]["confidence_excludes_zero"] is False


def test_targeted_play_uses_the_agents_opening_mulligans(monkeypatch) -> None:
    import longwar.targeted_counterfactual as targeted
    from longwar.agents.heuristic_agent import HeuristicAgent

    data = load_card_file(ROOT / "cards" / "cards.json")
    sample = build_samples(
        data, contexts=1, games_per_context=1, seed=37, required_cards=["namar"],
    )[0]
    engine = GameEngine(build_experiment_card_data(data))
    original_new_game = engine.new_game
    starts = []

    def new_game(*args, **kwargs):
        starts.append(kwargs)
        return original_new_game(*args, **kwargs)

    monkeypatch.setattr(engine, "new_game", new_game)
    monkeypatch.setattr(targeted, "OnlineMCCFRAgent", lambda engine, seed, **kwargs: HeuristicAgent(seed))
    _play_online_outcome(
        engine, sample, list(sample.focal_deck), target_cards=("namar",),
        online_iterations=1, online_depth=1,
    )
    assert starts[0]["opening_bonus"] is False
    assert "mulligan_indices" in starts[1]
    assert len(starts[1]["mulligan_indices"]) == 2
