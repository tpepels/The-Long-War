from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from longwar.belief import BeliefSampler
from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.mccfr import information_set_id

ROOT = Path(__file__).resolve().parents[1]


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=77, first_player=0)
    return engine, deck, state


def test_belief_sample_preserves_viewer_information_set_and_deck_multiset() -> None:
    engine, deck, state = setup()
    sampler = BeliefSampler(engine, (deck, deck))
    original_info = information_set_id(state, 0)

    sampled = sampler.sample(state, 0, random.Random(5))

    assert information_set_id(sampled, 0) == original_info
    assert Counter(sampled.players[1].hand + sampled.players[1].deck) == Counter(deck)
    assert sampled.players[0].hand == state.players[0].hand
    assert Counter(sampled.players[0].deck) == Counter(state.players[0].deck)


def test_belief_sampler_does_not_read_actual_opponent_hidden_partition() -> None:
    engine, deck, first = setup()
    second = first.clone()

    # Swap hidden cards between opponent hand and deck. Player 0 cannot observe
    # this, so a belief sampler must behave identically for both full states.
    second.players[1].hand[0], second.players[1].deck[0] = (
        second.players[1].deck[0],
        second.players[1].hand[0],
    )
    assert information_set_id(first, 0) == information_set_id(second, 0)

    sampler = BeliefSampler(engine, (deck, deck))
    a = sampler.sample(first, 0, random.Random(991))
    b = sampler.sample(second, 0, random.Random(991))

    assert a.players[1].hand == b.players[1].hand
    assert a.players[1].deck == b.players[1].deck


def test_belief_samples_vary_across_random_seeds() -> None:
    engine, deck, state = setup()
    sampler = BeliefSampler(engine, (deck, deck))
    hands = {
        tuple(sorted(sampler.sample(state, 0, random.Random(seed)).players[1].hand))
        for seed in range(8)
    }
    assert len(hands) > 1
