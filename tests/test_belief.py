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
from longwar.game import BoardTarget, Front, GameEngine, PlayPlot, Position, Rank, SetStratagem
from longwar.game.model import GameState, PlayerState, StratagemState
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
    prior = CardPoolDeckPrior(engine, deck_size=34)
    samples = [
        prior.sample_deck(Counter(), random.Random(seed))
        for seed in range(12)
    ]

    for deck in samples:
        validate_deck_definition(deck, engine.cards, exact_size=34)
    assert len({tuple(sorted(deck)) for deck in samples}) > 1
    assert any(Counter(deck) != Counter(reference) for deck in samples)


def test_hypothesis_prior_conditions_on_observed_cards() -> None:
    engine, reference, _ = setup()
    alternative = list(reference)
    alternative.remove("he-never-came")
    alternative.append("they-chose-another")
    validate_deck_definition(
        alternative,
        engine.cards,
        exact_size=len(reference),
    )

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
            PlayerState(deck=p0_deck, hand=[], command=engine.starting_command),
            PlayerState(deck=p1_deck, hand=["he-never-came"], command=engine.starting_command),
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


def test_card_pool_prior_excludes_unobserved_experimental_cards() -> None:
    from longwar.counterfactual import build_experiment_card_data, baseline_id

    engine, _, _ = setup()
    experiment_engine = GameEngine(
        build_experiment_card_data(
            load_card_file(ROOT / "cards" / "cards.json")
        )
    )
    prior = CardPoolDeckPrior(experiment_engine, deck_size=34)
    sampled = prior.sample_deck(Counter(), random.Random(7))

    assert not any(card_id.startswith("__cf_baseline__") for card_id in sampled)
    assert baseline_id("namar") not in sampled



def test_card_pool_prior_allows_multiple_distinct_heroes() -> None:
    engine, _, _ = setup()
    prior = CardPoolDeckPrior(engine, deck_size=34)
    required = Counter({
        "mara-queen-of-cinders": 1,
        "sera-mother-of-white-hands": 1,
    })

    sampled = prior.sample_deck(required, random.Random(17))
    heroes = [
        card_id
        for card_id in sampled
        if engine.cards[card_id].get("hero", False)
    ]

    assert "mara-queen-of-cinders" in heroes
    assert "sera-mother-of-white-hands" in heroes
    assert len(heroes) == len(set(heroes))
    validate_deck_definition(sampled, engine.cards, exact_size=34)


def test_belief_sampler_resamples_hidden_stratagem_identity_from_zone() -> None:
    engine, _, state = setup()
    opponent = 1

    hidden_card = None
    for zone_name in ("hand", "deck"):
        zone = getattr(state.players[opponent], zone_name)
        for index, card_id in enumerate(zone):
            if engine.cards[card_id]["type"] == "stratagem":
                hidden_card = zone.pop(index)
                break
        if hidden_card is not None:
            break

    if hidden_card is None:
        hidden_card = "the-storm-broke"
        state.players[opponent].deck.remove(hidden_card)

    state.stratagems[opponent] = StratagemState(hidden_card)
    state.stratagem_used[opponent] = True

    sampler = BeliefSampler(engine)
    diagnostics = sampler.diagnostics(state, 0)
    assert diagnostics.hidden_stratagems == 1

    sampled = sampler.sample(state, 0, random.Random(991))
    assert information_set_id(sampled, 0) == information_set_id(state, 0)
    assert sampled.stratagem(opponent) is not None
    assert engine.cards[sampled.stratagem(opponent).card_id]["type"] == "stratagem"


def test_belief_sampler_preserves_public_stratagem_identity() -> None:
    engine, _, state = setup()
    player = state.players[1]
    card_id = "the-storm-broke"

    if card_id in player.deck:
        player.deck.remove(card_id)
        player.hand.append(card_id)
    elif card_id not in player.hand:
        raise AssertionError("Expected Stratagem in opponent private zones")

    state.active_player = 1
    engine.apply(state, SetStratagem(card_id))
    sampler = BeliefSampler(engine)
    visible_id = information_set_id(state, 0)

    sampled = sampler.sample(state, 0, random.Random(313))

    assert information_set_id(sampled, 0) == visible_id
    assert sampled.stratagem(1) is not None
    assert sampled.stratagem(1).revealed is True
    assert sampled.stratagem(1).card_id == card_id
    assert sampler.diagnostics(state, 0).hidden_stratagems == 0


def test_card_pool_prior_uses_explicit_deck_size_not_engine_rules() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    engine = GameEngine(data)
    prior = CardPoolDeckPrior(engine, deck_size=40)

    sampled = prior.sample_deck(Counter(), random.Random(31415))

    assert prior.deck_size == 40
    assert len(sampled) == 40
    validate_deck_definition(sampled, engine.cards, exact_size=40)


def test_hypothesis_prior_conditions_on_hidden_card_type_evidence() -> None:
    engine, reference, state = setup()
    deck_size = len(reference)
    stratagems = {
        card for card in reference
        if engine.cards[card]["type"] == "stratagem"
    }
    without_stratagems = [card for card in reference if card not in stratagems]
    counts = Counter(without_stratagems)
    for card_id, card in engine.cards.items():
        if card["type"] == "stratagem" or card["unique"]:
            continue
        while counts[card_id] < 2 and len(without_stratagems) < deck_size:
            without_stratagems.append(card_id)
            counts[card_id] += 1
    assert len(without_stratagems) == deck_size
    validate_deck_definition(
        without_stratagems,
        engine.cards,
        exact_size=deck_size,
    )
    prior = HypothesisDeckPrior(engine, [
        DeckHypothesis(tuple(without_stratagems), weight=1000, label="impossible"),
        DeckHypothesis(tuple(reference), weight=1, label="compatible"),
    ])
    player = state.players[1]
    for zone in (player.hand, player.deck):
        if "the-storm-broke" in zone:
            zone.remove("the-storm-broke")
            break
    state.stratagems[1] = StratagemState("the-storm-broke")
    state.stratagem_used[1] = True
    sampler = BeliefSampler(engine, priors=(prior, prior))
    for seed in range(8):
        sampled = sampler.sample(state, 0, random.Random(seed))
        assert engine.cards[sampled.stratagem(1).card_id]["type"] == "stratagem"
        assert information_set_id(sampled, 0) == information_set_id(state, 0)


def test_card_pool_prior_reserves_observed_hidden_card_slots() -> None:
    engine, _, _ = setup()
    schemes = frozenset(card for card, data in engine.cards.items() if data.get("veiled"))
    stratagems = frozenset(card for card, data in engine.cards.items() if data["type"] == "stratagem")
    prior = CardPoolDeckPrior(engine, deck_size=34, card_weights={card: 0.001 for card in schemes | stratagems})
    for seed in range(12):
        sampled = prior.sample_deck(
            Counter(), random.Random(seed), hidden_requirements=((schemes, 3), (stratagems, 1)),
        )
        assert sum(card in schemes for card in sampled) >= 3
        assert sum(card in stratagems for card in sampled) >= 1
        validate_deck_definition(sampled, engine.cards, exact_size=34)
