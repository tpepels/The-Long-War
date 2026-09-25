from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pytest

from longwar.cards import load_card_file
from longwar.game import Front, GameEngine, Position, Rank
from longwar.game.model import StoryState, StratagemState
from longwar.mccfr import (
    _search_information_set_key,
    action_key,
    information_set_id,
    information_set_key,
)
from longwar.mccfr_core import (
    ACCELERATED,
    CFRNode,
    _python_external_sampling_traverse,
)
from longwar.mccfr_verification import (
    KuhnState,
    all_deals,
    kuhn_actions,
    kuhn_actor,
    kuhn_infoset,
    kuhn_next,
    kuhn_terminal,
    kuhn_terminal_utility,
)


def legacy_information_set_id(state, player: int) -> str:
    payload = json.dumps(
        information_set_key(state, player),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


ROOT = Path(__file__).resolve().parents[1]


def make_engine_and_state():
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)
    state = engine.new_game(deck, deck, seed=41, first_player=0)
    return engine, state


def test_fast_information_key_preserves_exported_id() -> None:
    engine, state = make_engine_and_state()

    own = state.slot(0, Position(Front.FIRST, Rank.FRONT))
    own.force = "the-fifty-men"
    own.bond = "followed"
    own.name = "namar"

    state.stories[0].append(StoryState("the-lamps-went-dark"))
    state.stratagems[0] = StratagemState("the-tide-rose")
    state.stratagem_used[0] = True

    assert information_set_id(state, 0) == legacy_information_set_id(state, 0)
    assert information_set_id(state, 1) == legacy_information_set_id(state, 1)

    assert _search_information_set_key(state, 0) == information_set_id(state, 0)
    assert _search_information_set_key(state, 1) == information_set_id(state, 1)


def _run_kuhn(traverse, *, seed: int = 7331, rounds: int = 80):
    rng = random.Random(seed)
    nodes = {}
    deals = all_deals()

    for index in range(rounds):
        state = KuhnState(deals[index % len(deals)])
        for traverser in (0, 1):
            traverse(
                state,
                traverser,
                depth=0,
                max_depth=None,
                nodes=nodes,
                rng=rng,
                is_terminal=kuhn_terminal,
                terminal_utility=kuhn_terminal_utility,
                current_player=kuhn_actor,
                legal_actions=kuhn_actions,
                action_key=lambda action: action,
                information_set_id=kuhn_infoset,
                next_state=kuhn_next,
            )
    return nodes


@pytest.mark.skipif(not ACCELERATED, reason="native extension not built")
def test_cython_traversal_matches_python_fallback() -> None:
    from longwar.mccfr_core import external_sampling_traverse

    fast = _run_kuhn(external_sampling_traverse)
    slow = _run_kuhn(_python_external_sampling_traverse)

    assert set(fast) == set(slow)
    for key in fast:
        assert fast[key].visits == slow[key].visits
        assert fast[key].average_visits == slow[key].average_visits
        assert fast[key].regret_sum == pytest.approx(slow[key].regret_sum)
        assert fast[key].strategy_sum == pytest.approx(slow[key].strategy_sum)


@pytest.mark.skipif(not ACCELERATED, reason="native extension not built")
def test_cython_node_regret_matching_matches_expected() -> None:
    node = CFRNode(
        regret_sum={"a": 4.0, "b": -2.0, "c": 2.0},
        strategy_sum={"a": 0.0, "b": 0.0, "c": 0.0},
    )
    assert node.strategy(["a", "b", "c"]) == pytest.approx(
        {"a": 2.0 / 3.0, "b": 0.0, "c": 1.0 / 3.0}
    )


def test_longwar_action_keys_are_unique_across_live_states() -> None:
    engine, _ = make_engine_and_state()
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    rng = random.Random(441)

    checked = 0
    for seed in range(6):
        state = engine.new_game(deck, deck, seed=seed, first_player=seed % 2)
        for _ in range(35):
            actions = engine.legal_actions(state)
            keys = [action_key(action) for action in actions]
            assert len(keys) == len(set(keys))
            checked += 1
            if state.phase.value == "complete":
                break
            engine.apply(state, rng.choice(actions), validate=False)

    assert checked >= 80
