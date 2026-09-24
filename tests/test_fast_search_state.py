from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

import pytest

from longwar.agents.heuristic_agent import HeuristicAgent
from longwar.cards import load_card_file
from longwar.game import Front, GameEngine
from longwar.rules import GameRules
from longwar.mccfr import action_key, information_set_id

fast_search = pytest.importorskip("longwar._fast_search")
FastEngine = fast_search.FastEngine
NativeHeuristicEvaluator = fast_search.NativeHeuristicEvaluator
stable_information_id_from_fast_key = (
    fast_search.stable_information_id_from_fast_key
)

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.algorithm


def setup(deck_file: str = "reference.json"):
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / deck_file).read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    return engine, deck, FastEngine(engine)


def python_snapshot(state):
    phase = {"battle": 0, "choose_first": 1, "complete": 2}[state.phase.value]
    return {
        "phase": phase,
        "battle": state.battle,
        "active_player": state.active_player,
        "chooser": -1 if state.chooser is None else state.chooser,
        "winner": -1 if state.winner is None else state.winner,
        "turn_number": state.turn_number,
        "victories": [state.players[0].victories, state.players[1].victories],
        "passed": [state.players[0].passed, state.players[1].passed],
        "pass_order": list(state.pass_order),
        "discarded_this_battle": list(state.discarded_this_battle),
        "command": [state.players[0].command, state.players[1].command],
        "free_cycle": [state.players[0].free_cycle, state.players[1].free_cycle],
        "operations_this_battle": list(state.operations_this_battle),
        "pending_final_operation_for": state.pending_final_operation_for,
        "cleanup_pending": state.cleanup_pending,
        "cleanup_next_starter": state.cleanup_next_starter,
        "cleanup_next_chooser": state.cleanup_next_chooser,
        "hands": [dict(Counter(player.hand)) for player in state.players],
        "decks": [list(player.deck) for player in state.players],
        "discards": [list(player.discard) for player in state.players],
        "board": [
            [
                (
                    state.board[player][front][rank].subject,
                    state.board[player][front][rank].link,
                    state.board[player][front][rank].name,
                    state.board[player][front][rank].temporary_strength,
                )
                for front in range(3)
                for rank in range(2)
            ]
            for player in range(2)
        ],
        "schemes": [
            [
                None
                if state.schemes[player][front] is None
                else (
                    state.schemes[player][front].card_id,
                    state.schemes[player][front].revealed,
                )
                for front in range(3)
            ]
            for player in range(2)
        ],
        "stratagems": [
            None
            if state.stratagems[player] is None
            else (
                state.stratagems[player].card_id,
                state.stratagems[player].revealed,
            )
            for player in range(2)
        ],
        "stratagem_used": list(state.stratagem_used),
        "hero_used": list(state.hero_used),
        "draw_used": list(state.draw_used),
    }


def assert_fast_matches(
    engine,
    fast_engine,
    state,
    fast_state,
    *,
    check_information: bool = True,
):
    assert fast_engine.debug_snapshot(fast_state) == python_snapshot(state)

    if state.phase.value != "complete":
        py_keys = {action_key(action) for action in engine.legal_actions(state)}
        fast_keys = {
            fast_engine.action_key(action)
            for action in fast_engine.legal_actions(fast_state)
        }
        assert fast_keys == py_keys

    for player in (0, 1):
        if check_information:
            assert stable_information_id_from_fast_key(
                fast_engine,
                fast_engine.information_key(fast_state, player),
            ) == information_set_id(state, player)

        for front in Front:
            assert fast_engine.front_strength(
                fast_state,
                player,
                int(front),
            ) == engine.front_strength(state, player, front)

    evaluator = HeuristicAgent(seed=0, exploration=0.0)
    native_evaluator = NativeHeuristicEvaluator(fast_engine)
    for player in (0, 1):
        assert native_evaluator.evaluate(
            fast_state,
            player,
        ) == pytest.approx(
            evaluator.evaluate(engine, state, player)
        )


@pytest.mark.parametrize(
    "deck_file",
    (
        "reference.json",
        "avaros-line.json",
        "mara-rear.json",
        "sera-support.json",
    ),
)
def test_primitive_search_state_matches_reference_engine_on_random_games(
    deck_file: str,
):
    engine, deck, fast_engine = setup(deck_file)
    rng = random.Random(94117)
    checked = 0

    for seed in range(8):
        state = engine.new_game(
            deck,
            deck,
            seed=seed,
            first_player=seed % 2,
        )
        fast_state = fast_engine.from_game_state(state)

        for _ in range(55):
            assert_fast_matches(engine, fast_engine, state, fast_state)
            checked += 1
            if state.phase.value == "complete":
                break

            actions = engine.legal_actions(state)
            action = rng.choice(actions)
            target_key = action_key(action)
            fast_action = next(
                candidate
                for candidate in fast_engine.legal_actions(fast_state)
                if fast_engine.action_key(candidate) == target_key
            )

            engine.apply(state, action, validate=False)
            fast_engine.apply(fast_state, fast_action)

    assert checked >= 150


def force_candidate_engine(*, automatic: bool) -> tuple[GameEngine, list[str], object]:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (
            ROOT / "decks" / "reference.json"
        ).read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(
        data,
        rules=GameRules.force_candidate(
            "automatic" if automatic else "paid"
        ),
    )
    return engine, deck, FastEngine(engine)


@pytest.mark.legacy_rule_experiment
@pytest.mark.parametrize("automatic", (False, True))
def test_packed_state_matches_force_candidate_random_games(
    automatic: bool,
) -> None:
    engine, deck, fast_engine = force_candidate_engine(automatic=automatic)
    rng = random.Random(26092377 + int(automatic))
    checked = 0

    for seed in range(4):
        state = engine.new_game(
            deck,
            deck,
            seed=26092400 + seed,
            first_player=seed % 2,
        )
        fast_state = fast_engine.from_game_state(state)

        for _ in range(80):
            assert_fast_matches(
                engine,
                fast_engine,
                state,
                fast_state,
                check_information=False,
            )
            checked += 1
            if state.phase.value == "complete":
                break

            actions = engine.legal_actions(state)
            action = rng.choice(actions)
            target_key = action_key(action)
            fast_action = next(
                candidate
                for candidate in fast_engine.legal_actions(fast_state)
                if fast_engine.action_key(candidate) == target_key
            )

            engine.apply(state, action, validate=False)
            fast_engine.apply(fast_state, fast_action)

    assert checked >= 120


def test_native_state_hash_distinguishes_draw_order() -> None:
    engine, deck, native = setup("reference.json")
    state = engine.new_game(deck, deck, seed=9901, first_player=0)
    packed = native.from_game_state(state)
    baseline = native.state_hash(packed)

    changed = state.clone()
    if len(changed.players[0].deck) >= 2:
        changed.players[0].deck[-1], changed.players[0].deck[-2] = (
            changed.players[0].deck[-2],
            changed.players[0].deck[-1],
        )
    changed_packed = native.from_game_state(changed)
    assert native.state_hash(changed_packed) != baseline
