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
from longwar.game import BoardTarget, Front, GameEngine, PlayPlot, Position, Rank
from longwar.game.model import GameState, PlayerState
from longwar.mccfr import information_set_id

ROOT = Path(__file__).resolve().parents[1]
CENTER = Position(Front.CENTER, Rank.FRONT)


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=77, first_player=0)
    return engine, deck, state


def test_card_pool_prior_samples_multiple_legal_deck_compositions() -> None:
    engine, reference, _ = setup()
    prior = CardPoolDeckPrior(engine)
    samples = [
        prior.sample_deck(Counter(), random.Random(seed))
        for seed in range(12)
    ]

    for deck in samples:
        engine.validate_deck(deck)
    assert len({tuple(sorted(deck)) for deck in samples}) > 1
    assert any(Counter(deck) != Counter(reference) for deck in samples)


def test_hypothesis_prior_conditions_on_observed_cards() -> None:
    engine, reference, _ = setup()
    alternative = list(reference)
    alternative.remove("he-never-came")
    alternative.append("they-chose-another")
    engine.validate_deck(alternative)

    prior = HypothesisDeckPrior(
        engine,
        [
            DeckHypothesis(tuple(reference), weight=1.0, label="reference"),
            DeckHypothesis(tuple(alternative), weight=1.0, label="alternative"),
        ],
    )
    posterior = prior.posterior(Counter({"he-never-came": 1}))

    assert len(posterior) == 1
    assert posterior[0][0].label == "reference"
    assert posterior[0][1] == 1.0


def test_belief_sample_preserves_viewer_information_set_without_true_decklist() -> None:
    engine, _, state = setup()
    sampler = BeliefSampler(engine)
    original_info = information_set_id(state, 0)

    sampled = sampler.sample(state, 0, random.Random(5))

    assert information_set_id(sampled, 0) == original_info
    engine.validate_deck(sampled.players[1].hand + sampled.players[1].deck)
    assert sampled.players[0].hand == state.players[0].hand
    assert Counter(sampled.players[0].deck) == Counter(state.players[0].deck)


def test_belief_sampler_does_not_read_actual_opponent_hidden_partition() -> None:
    engine, _, first = setup()
    second = first.clone()

    second.players[1].hand[0], second.players[1].deck[0] = (
        second.players[1].deck[0],
        second.players[1].hand[0],
    )
    assert information_set_id(first, 0) == information_set_id(second, 0)

    sampler = BeliefSampler(engine)
    a = sampler.sample(first, 0, random.Random(991))
    b = sampler.sample(second, 0, random.Random(991))

    assert a.players[1].hand == b.players[1].hand
    assert a.players[1].deck == b.players[1].deck


def test_belief_sampler_keeps_remembered_returned_card_in_hand() -> None:
    engine, reference, _ = setup()

    p0_deck = list(reference)
    for card_id in ("the-fifty-men", "followed", "namar"):
        p0_deck.remove(card_id)
    p1_deck = list(reference)
    p1_deck.remove("he-never-came")
    state = GameState(
        players=[
            PlayerState(deck=p0_deck, hand=[]),
            PlayerState(deck=p1_deck, hand=["he-never-came"]),
        ],
        active_player=1,
    )
    slot = state.slot(0, CENTER)
    slot.subject = "the-fifty-men"
    slot.link = "followed"
    slot.name = "namar"

    engine.apply(
        state,
        PlayPlot(
            "he-never-came",
            (BoardTarget(0, CENTER),),
        ),
    )
    sampler = BeliefSampler(engine)

    for seed in range(8):
        sampled = sampler.sample(state, 1, random.Random(seed))
        assert "namar" in sampled.players[0].hand


def test_belief_samples_vary_across_random_seeds() -> None:
    engine, _, state = setup()
    sampler = BeliefSampler(engine)
    hands = {
        tuple(sorted(sampler.sample(state, 0, random.Random(seed)).players[1].hand))
        for seed in range(8)
    }
    assert len(hands) > 1
