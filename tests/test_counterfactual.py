from __future__ import annotations

import json
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.counterfactual import (
    ExperimentSample,
    _play_focal_outcome,
    _severity,
    baseline_card,
    baseline_id,
    build_experiment_card_data,
    build_samples,
    estimate,
    generate_context_decks,
    pair_contrast,
    replace_cards,
    run_counterfactual_card_sweep,
    run_counterfactual_experiment,
    triple_contrast,
)
from longwar.game import GameEngine

ROOT = Path(__file__).resolve().parents[1]


def data():
    return load_card_file(ROOT / "cards" / "cards.json")


def test_experimental_baselines_are_valid_and_type_matched() -> None:
    card_data = data()
    experiment = build_experiment_card_data(card_data)
    index = {card["id"]: card for card in experiment["cards"]}

    for card in card_data["cards"]:
        baseline = index[baseline_id(card["id"])]
        assert baseline["type"] == card["type"]
        assert baseline["experimental"] is True
        assert baseline["command_cost"] == card["command_cost"]

    assert baseline_card(index["the-fifty-men"])["strength"] == 4
    assert baseline_card(index["followed"])["rules"] == {
        "strength_bonus": 1,
        "named_strength_bonus": 2,
    }
    assert baseline_card(index["namar"])["strength"] == 2
    assert baseline_card(index["he-never-came"])["rules"] == {}
    assert baseline_card(index["the-storm-broke"])["rules"] == {
        "stratagem": {
            "trigger": {"event": "never", "actor": "either"},
        }
    }


def test_non_command_experiment_baselines_allow_cards_without_command_cost() -> None:
    card_data = data()
    for card in card_data["cards"]:
        card.pop("command_cost")

    experiment = build_experiment_card_data(card_data)
    assert all("command_cost" not in card for card in experiment["cards"])
    GameEngine(experiment, command_enabled=False)


def test_replacement_changes_exactly_one_matching_slot_and_remains_legal() -> None:
    card_data = data()
    contexts = generate_context_decks(
        card_data,
        count=1,
        seed=4,
        required_cards=["namar"],
    )
    original = contexts[0]
    replaced = replace_cards(original, ["namar"])

    differences = [
        (before, after)
        for before, after in zip(original, replaced)
        if before != after
    ]
    assert differences == [("namar", baseline_id("namar"))]

    engine = GameEngine(build_experiment_card_data(card_data))
    engine.validate_deck(replaced)


def test_contexts_are_legal_and_cover_the_expanded_pool() -> None:
    card_data = data()
    engine = GameEngine(card_data)
    ids = {card["id"] for card in card_data["cards"]}
    contexts = generate_context_decks(card_data, count=8, seed=17)

    assert len(contexts) == 8
    covered: set[str] = set()
    for deck in contexts:
        engine.validate_deck(deck)
        assert len(deck) == 30
        covered.update(deck)
    assert ids <= covered


def test_required_counterfactual_cards_appear_in_every_context() -> None:
    card_data = data()
    required = {"maela", "guarded", "the-crows-returned"}
    contexts = generate_context_decks(
        card_data,
        count=4,
        seed=23,
        required_cards=required,
    )
    assert all(required <= set(deck) for deck in contexts)


def test_alternative_heroes_must_be_evaluated_separately() -> None:
    card_data = data()
    with pytest.raises(ValueError, match="more than one Hero"):
        generate_context_decks(
            card_data,
            count=1,
            seed=29,
            required_cards=[
                "mara-queen-of-cinders",
                "sera-mother-of-white-hands",
            ],
        )


def test_samples_are_reproducible_and_balance_focal_seat() -> None:
    card_data = data()
    first = build_samples(card_data, contexts=2, games_per_context=3, seed=88)
    second = build_samples(card_data, contexts=2, games_per_context=3, seed=88)

    assert first == second
    assert [sample.focal_player for sample in first] == [0, 1, 0, 1, 0, 1]


def test_factorial_contrasts_have_expected_signs() -> None:
    assert pair_contrast(1, 0, 0, 0) == 1
    assert pair_contrast(1, 1, 1, 1) == 0

    assert triple_contrast(
        1, 0, 0, 0, 0, 0, 0, 0
    ) == 1
    assert triple_contrast(
        1, 1, 1, 1, 1, 1, 1, 1
    ) == 0


def test_paired_estimate_is_deterministic_and_reports_sample_count() -> None:
    values = [1, 0, 1, -1, 0, 1]
    first = estimate(values, seed=123, bootstrap_resamples=500)
    second = estimate(values, seed=123, bootstrap_resamples=500)

    assert first == second
    assert first.samples == len(values)
    assert first.mean == pytest.approx(sum(values) / len(values))
    assert first.ci95[0] <= first.mean <= first.ci95[1]


def test_estimate_uses_sample_standard_error() -> None:
    assert estimate([-1.0, 1.0], seed=1).standard_error == pytest.approx(1.0)


@pytest.mark.parametrize("values", [[1.0], [1.0, 1.0], [0.0] * 24])
def test_degenerate_smoke_samples_do_not_claim_certainty(values) -> None:
    effect = estimate(values, seed=1)
    assert effect.ci95[0] < effect.ci95[1]
    assert effect.ci95[0] <= 0 <= effect.ci95[1]
    assert effect.ci_method == "bounded_hoeffding_degenerate_sample"
    severity = _severity(effect)
    assert severity["confidence_excludes_zero"] is False
    assert severity["level"] not in {"red", "orange", "dark_green"}


def test_invalid_bootstrap_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="bootstrap_resamples must be positive"):
        estimate([1.0, -1.0], seed=1, bootstrap_resamples=0)


def test_triples_compute_required_pair_conditions_without_pair_output(monkeypatch) -> None:
    import longwar.counterfactual as counterfactual

    conditions = []

    def outcome(engine, sample, focal_deck, **kwargs):
        replaced = frozenset(card.removeprefix("__cf_baseline__") for card in focal_deck if card.startswith("__cf_baseline__"))
        conditions.append(replaced)
        return int(not replaced)

    monkeypatch.setattr(counterfactual, "_play_focal_outcome", outcome)
    report = run_counterfactual_experiment(
        data(), contexts=1, games_per_context=1, seed=37,
        card_ids=["the-fifty-men", "followed", "namar"],
        include_pairs=False, include_legend_triples=True,
    )
    assert len(set(conditions)) == 8
    assert report["total_matches"] == 8
    assert report["pairs"] == []
    assert report["triples"][0]["interaction_delta"] == 1
    assert report["triples"][0]["ci95"] == [-4.0, 4.0]


def test_per_card_sweep_keeps_each_seed_and_required_deck_cards(monkeypatch) -> None:
    import longwar.counterfactual as counterfactual

    monkeypatch.setattr(counterfactual, "_play_focal_outcome", lambda *args, **kwargs: 0)
    report = run_counterfactual_card_sweep(
        data(), contexts=1, games_per_context=1, seed=41,
        card_ids=["namar", "followed"], bootstrap_resamples=99,
    )
    rows = {row["id"]: row for row in report["cards"]}
    assert rows["namar"]["sample_generation"] == {"seed": 41, "required_cards": ["namar"]}
    assert rows["followed"]["sample_generation"] == {"seed": 41 + 104729, "required_cards": ["followed"]}
    assert report["bootstrap_resamples"] == 99


def test_context_decks_do_not_depend_on_required_card_iteration_order() -> None:
    cards = ["namar", "followed", "the-fifty-men"]
    assert generate_context_decks(data(), count=2, seed=7, required_cards=cards) == generate_context_decks(data(), count=2, seed=7, required_cards=reversed(cards))


def test_scheme_baseline_preserves_scheme_commitment() -> None:
    card_data = data()
    index = {card["id"]: card for card in card_data["cards"]}
    baseline = baseline_card(index["the-lamps-went-dark"])

    assert baseline["type"] == "plot"
    assert baseline["story_form"] == "omen"
    assert baseline["veiled"] is True
    assert baseline["rules"]["scheme"]["trigger"] == "never"
    assert baseline["rules"]["scheme"]["face_down_front_bonus"] == 1



def test_stratagem_baseline_preserves_hidden_free_commitment() -> None:
    card_data = data()
    index = {card["id"]: card for card in card_data["cards"]}
    baseline = baseline_card(index["the-storm-broke"])

    assert baseline["type"] == "stratagem"
    assert baseline["rules"]["stratagem"]["trigger"]["event"] == "never"


def test_hero_baseline_preserves_hero_deck_constraint() -> None:
    card_data = data()
    index = {card["id"]: card for card in card_data["cards"]}
    baseline = baseline_card(index["avaros-the-bronze-king"])

    assert baseline["hero"] is True
    assert baseline["unique"] is True
    assert baseline["role"] == "swordsman"
    assert "hero" in baseline["classes"]
    assert baseline["strength"] == 6


def test_counterfactual_mulligan_preview_excludes_opening_bonus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    card_data = data()
    deck = generate_context_decks(card_data, count=1, seed=41)[0]
    engine = GameEngine(build_experiment_card_data(card_data))
    sample = ExperimentSample(
        sample_id=0,
        context_id=0,
        focal_player=0,
        game_seed=1701,
        focal_deck=tuple(deck),
        opponent_deck=tuple(deck),
    )

    original_new_game = engine.new_game
    opening_bonus_calls: list[bool] = []

    def checked_new_game(*args, **kwargs):
        opening_bonus_calls.append(bool(kwargs.get("opening_bonus", True)))
        return original_new_game(*args, **kwargs)

    monkeypatch.setattr(engine, "new_game", checked_new_game)
    _play_focal_outcome(
        engine,
        sample,
        list(deck),
        agent_name="heuristic",
    )

    assert opening_bonus_calls[:2] == [False, True]
