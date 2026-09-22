from __future__ import annotations

import json
import random
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Phase, Position, Rank
from longwar.game.model import StratagemState

ROOT = Path(__file__).resolve().parents[1]


def setup():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    return GameEngine(data), deck


def assert_matrix_matches_scalar(engine: GameEngine, state) -> None:
    matrix = engine.front_strength_matrix(state)
    for player in (0, 1):
        for front in Front:
            assert matrix[player][int(front)] == engine.front_strength(
                state,
                player,
                front,
            )


def test_batched_front_strength_matches_scalar_engine_across_play() -> None:
    engine, deck = setup()
    rng = random.Random(91827)

    checked = 0
    for seed in range(8):
        state = engine.new_game(deck, deck, seed=seed, first_player=seed % 2)
        for _ in range(45):
            assert_matrix_matches_scalar(engine, state)
            checked += 1
            if state.phase is Phase.COMPLETE:
                break
            actions = engine.legal_actions(state)
            action = rng.choice(actions)
            engine.apply(state, action, validate=False)

    assert checked >= 120


def test_name_option_delta_matches_full_strength_recalculation() -> None:
    engine, deck = setup()
    state = engine.new_game(deck, deck, seed=91, first_player=0)
    state.stratagems[1] = StratagemState("the-wooden-gift", revealed=True)

    bonds = ["followed", "swore-to", "defied", "carried", "avenged"]
    names = ["namar", "iria", "oren", "teyra"]

    for rank in (Rank.FRONT, Rank.REAR):
        position = Position(Front.CENTER, rank)
        slot = state.slot(0, position)
        slot.subject = "the-fifty-men"
        for bond_id in bonds:
            slot.link = bond_id
            slot.name = None
            for discarded in (0, 2, 5):
                state.discarded_this_battle[0] = discarded
                before = engine.position_strength(state, 0, position)
                for name_id in names:
                    predicted = engine.name_attachment_strength_gain(
                        state,
                        0,
                        position,
                        name_id,
                    )
                    slot.name = name_id
                    after = engine.position_strength(state, 0, position)
                    slot.name = None
                    assert predicted == after - before
