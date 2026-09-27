from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from longwar.belief import (
    BeliefSampler,
    CardPoolDeckPrior,
    DeckHypothesis,
    HypothesisDeckPrior,
)
from longwar.cards import load_card_file
from longwar.decks import validate_deck_definition
from longwar.game import Front, GameEngine, Position, Rank
from longwar.game.model import StoryState, StratagemState


ROOT = Path(__file__).resolve().parents[1]
CENTER = Position(Front.SECOND, Rank.FRONT)


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "mobility-open-bonds.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(
        deck,
        deck,
        seed=77,
        first_player=0,
        opening_bonus=False,
    )
    return engine, deck, state


def test_card_pool_prior_always_satisfies_force_and_name_minimums() -> None:
    engine, _reference, _state = setup()
    prior = CardPoolDeckPrior(engine, deck_size=34)

    for seed in range(32):
        sampled = prior.sample_deck(Counter(), random.Random(seed))
        force_count = sum(
            engine.cards[card_id]["type"] == "force"
            for card_id in sampled
        )
        name_count = sum(
            engine.cards[card_id]["type"] == "name"
            for card_id in sampled
        )
        assert len(sampled) == 34
        assert force_count >= 14
        assert name_count >= 6
        validate_deck_definition(sampled, engine.cards)


def test_card_pool_prior_samples_multiple_legal_deck_compositions() -> None:
    engine, _reference, _state = setup()
    prior = CardPoolDeckPrior(engine, deck_size=34)
    samples = {
        tuple(sorted(prior.sample_deck(Counter(), random.Random(seed))))
        for seed in range(8)
    }
    assert len(samples) > 1


def test_hypothesis_prior_conditions_on_observed_public_cards() -> None:
    engine, reference, _state = setup()
    alternative = list(reference)
    alternative.remove("the-grey-riders")
    alternative.append("the-fifty-men")
    prior = HypothesisDeckPrior(
        engine,
        [
            DeckHypothesis(tuple(reference), weight=1, label="reference"),
            DeckHypothesis(tuple(alternative), weight=1, label="alternative"),
        ],
    )

    posterior = prior.posterior(Counter({"the-grey-riders": 2}))
    assert [hypothesis.label for hypothesis, _ in posterior] == ["reference"]


def test_belief_sample_preserves_all_public_zones() -> None:
    engine, _reference, state = setup()
    opponent = 1

    slot = state.slot(opponent, CENTER)
    slot.force = "the-fifty-men"
    slot.bond = "followed"
    slot.name = "namar"
    state.stories[opponent] = [StoryState("the-long-march")]
    state.stratagems[opponent] = StratagemState("the-ground-was-held")

    sampler = BeliefSampler(engine)
    sampled = sampler.sample(state, 0, random.Random(11))

    sampled_slot = sampled.slot(opponent, CENTER)
    assert (sampled_slot.force, sampled_slot.bond, sampled_slot.name) == (
        "the-fifty-men",
        "followed",
        "namar",
    )
    assert [story.card_id for story in sampled.stories[opponent]] == [
        "the-long-march"
    ]
    assert sampled.stratagems[opponent] is not None
    assert sampled.stratagems[opponent].card_id == "the-ground-was-held"
    assert sampled.players[opponent].discard == state.players[opponent].discard


def test_belief_sampler_reports_no_hidden_story_or_stratagem_zones() -> None:
    engine, _reference, state = setup()
    state.stories[1] = [StoryState("the-long-march")]
    state.stratagems[1] = StratagemState("the-ground-was-held")

    diagnostics = BeliefSampler(engine).diagnostics(state, 0)

    assert diagnostics.hidden_schemes == 0
    assert diagnostics.hidden_stratagems == 0


def test_belief_samples_vary_only_hidden_hand_and_deck_partition() -> None:
    engine, _reference, state = setup()
    sampler = BeliefSampler(engine)

    hands = {
        tuple(
            sorted(
                sampler.sample(
                    state,
                    0,
                    random.Random(seed),
                ).players[1].hand
            )
        )
        for seed in range(8)
    }
    assert len(hands) > 1


def test_known_hidden_hand_card_is_preserved() -> None:
    engine, _reference, state = setup()
    opponent = 1
    known = state.players[opponent].hand[0]
    state.observe_hidden_delta(
        viewer=0,
        owner=opponent,
        card_id=known,
        zone="hand",
        delta=1,
        reason="test",
    )

    sampled = BeliefSampler(engine).sample(state, 0, random.Random(31))

    assert known in sampled.players[opponent].hand


def test_belief_reuse_context_changes_when_public_story_changes() -> None:
    engine, _reference, state = setup()
    sampler = BeliefSampler(engine)

    before = sampler.reuse_context(state, 0)
    state.stories[1].append(StoryState("the-long-march"))
    after = sampler.reuse_context(state, 0)

    assert before != after


def test_card_pool_prior_excludes_unobserved_experimental_cards() -> None:
    from longwar.counterfactual import build_experiment_card_data, baseline_id

    engine, _reference, _state = setup()
    experiment_engine = GameEngine(
        build_experiment_card_data(
            load_card_file(ROOT / "cards" / "cards.json"),
            ["namar"],
        )
    )
    prior = CardPoolDeckPrior(experiment_engine, deck_size=34)
    sampled = prior.sample_deck(Counter(), random.Random(7))

    assert not any(card_id.startswith("__cf_baseline__") for card_id in sampled)
    assert baseline_id("namar") not in sampled


def test_card_pool_prior_allows_multiple_distinct_heroes() -> None:
    engine, _reference, _state = setup()
    prior = CardPoolDeckPrior(engine, deck_size=34)
    required = Counter(
        {
            "avaros-the-bronze-king": 1,
            "kael-the-roadless": 1,
        }
    )

    sampled = prior.sample_deck(required, random.Random(17))
    heroes = [
        card_id
        for card_id in sampled
        if engine.cards[card_id].get("hero", False)
    ]

    assert "avaros-the-bronze-king" in heroes
    assert "kael-the-roadless" in heroes
    assert len(heroes) == len(set(heroes))
    assert len(sampled) == 34
    validate_deck_definition(sampled, engine.cards)


def test_card_pool_prior_uses_explicit_deck_size_not_engine_rules() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)
    prior = CardPoolDeckPrior(engine, deck_size=40)

    sampled = prior.sample_deck(Counter(), random.Random(31415))

    assert prior.deck_size == 40
    assert len(sampled) == 40
    validate_deck_definition(sampled, engine.cards)
