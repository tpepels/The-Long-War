from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine
from longwar.game.actions import action_key


fast_search = pytest.importorskip("longwar._fast_search")
FastEngine = fast_search.FastEngine

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.algorithm


def setup(deck_file: str = "reference.json"):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / deck_file).read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    return engine, deck, FastEngine(engine)


def public_snapshot(state):
    return {
        "phase": state.phase.value,
        "battle": state.battle,
        "active_player": state.active_player,
        "winner": state.winner,
        "players": [
            {
                "deck": list(player.deck),
                "hand": sorted(player.hand),
                "discard": list(player.discard),
                "passed": player.passed,
                "command": player.command,
            }
            for player in state.players
        ],
        "board": [
            [
                [
                    {
                        "force": slot.force,
                        "bond": slot.bond,
                        "name": slot.name,
                        "temporary_strength": slot.temporary_strength,
                    }
                    for slot in front
                ]
                for front in side
            ]
            for side in state.board
        ],
        "stories": [
            [{"card_id": story.card_id} for story in side]
            for side in state.stories
        ],
        "stratagems": [
            None if stratagem is None else {"card_id": stratagem.card_id}
            for stratagem in state.stratagems
        ],
        "stratagem_used": list(state.stratagem_used),
        "hero_used": list(state.hero_used),
        "pending_final_operation_for": state.pending_final_operation_for,
        "pending_draw_discard_for": state.pending_draw_discard_for,
        "pass_order": list(state.pass_order),
    }


def native_public_snapshot(native, fast_state):
    exported = native.export_state(fast_state)
    return {
        "phase": exported["phase"],
        "battle": exported["battle"],
        "active_player": exported["active_player"],
        "winner": exported["winner"],
        "players": [
            {
                **player,
                "hand": sorted(player["hand"]),
            }
            for player in exported["players"]
        ],
        "board": exported["board"],
        "stories": exported["stories"],
        "stratagems": exported["stratagems"],
        "stratagem_used": exported["stratagem_used"],
        "hero_used": exported["hero_used"],
        "pending_final_operation_for": exported["pending_final_operation_for"],
        "pending_draw_discard_for": exported["pending_draw_discard_for"],
        "pass_order": exported["pass_order"],
    }


def assert_fast_matches(engine, native, state, fast_state):
    assert native_public_snapshot(native, fast_state) == public_snapshot(state)

    if state.phase.value != "complete":
        assert {
            native.action_key(action)
            for action in native.legal_actions(fast_state)
        } == {
            action_key(action)
            for action in engine.legal_actions(state)
        }

    for player in (0, 1):
        for front in Front:
            assert native.front_strength(
                fast_state,
                player,
                int(front),
            ) == engine.front_strength(state, player, front)


@pytest.mark.parametrize(
    "deck_file",
    (
        "reference.json",
        "avaros-line.json",
        "mara-rear.json",
        "sera-support.json",
    ),
)
def test_packed_state_matches_canonical_engine_on_random_games(
    deck_file: str,
) -> None:
    engine, deck, native = setup(deck_file)
    rng = random.Random(94117)
    checked = 0

    for seed in range(4):
        state = engine.new_game(
            deck,
            deck,
            seed=seed,
            first_player=seed % 2,
        )
        fast_state = native.from_game_state(state)

        for _ in range(80):
            assert_fast_matches(engine, native, state, fast_state)
            checked += 1
            if state.phase.value == "complete":
                break

            actions = engine.legal_actions(state)
            action = rng.choice(actions)
            key = action_key(action)
            fast_action = next(
                candidate
                for candidate in native.legal_actions(fast_state)
                if native.action_key(candidate) == key
            )
            engine.apply(state, action, validate=False)
            native.apply(fast_state, fast_action)

    assert checked >= 100


def test_native_state_hash_distinguishes_draw_order() -> None:
    engine, deck, native = setup()
    state = engine.new_game(
        deck,
        deck,
        seed=9901,
        first_player=0,
        opening_bonus=False,
    )
    packed = native.from_game_state(state)
    baseline = native.state_hash(packed)

    changed = state.clone()
    changed.players[0].deck[-1], changed.players[0].deck[-2] = (
        changed.players[0].deck[-2],
        changed.players[0].deck[-1],
    )
    changed_packed = native.from_game_state(changed)

    assert native.state_hash(changed_packed) != baseline
