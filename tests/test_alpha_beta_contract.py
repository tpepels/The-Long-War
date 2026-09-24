from dataclasses import dataclass
from math import inf

import pytest

from longwar.algorithms.alpha_beta import AlphaBetaSearch, SearchBudget
from longwar.game.model import Phase


@dataclass
class _State:
    name: str = "root"
    active_player: int = 0
    phase: Phase = Phase.BATTLE

    def clone(self):
        return _State(self.name, self.active_player, self.phase)

    def copy_from(self, other):
        self.name, self.active_player, self.phase = other.name, other.active_player, other.phase


class _GraphEngine:
    def apply(self, state, action, *, validate):
        state.name = action
        state.active_player = 1 - state.active_player


class _Evaluator:
    def __init__(self, sign):
        self.sign = sign

    def _strategic_state_value(self, engine, state, player):
        return self.sign * {"a1": 5, "a2": 1, "b1": 4, "b2": 2}[state.name]


class _GraphSearch(AlphaBetaSearch):
    @staticmethod
    def state_key(state):
        return state.name

    def ordered_actions(self, state, actor, *, width):
        return {"root": ["a", "b"], "a": ["a1", "a2"], "b": ["b1", "b2"]}[state.name]


@pytest.mark.parametrize("sign", [1, -1])
def test_descendant_cutoff_bound_is_not_cached_as_exact(sign):
    search = _GraphSearch(_GraphEngine(), _Evaluator(sign), candidate_width=2)
    state = _State(active_player=0 if sign == 1 else 1)
    table = {}
    options = dict(root_player=0, depth=2, budget=SearchBudget(100), transposition=table, scratch=[])
    # Every child cuts off; the parent finishes its loop but is still a bound.
    bound = search.search(state, alpha=10 if sign == 1 else -inf,
                          beta=inf if sign == 1 else -10, **options)
    assert bound == sign * 5
    assert (2, 0, "root") not in table
    exact = search.search(state, alpha=-inf, beta=inf, **options)
    assert exact == sign * 2


def test_python_state_key_includes_search_relevant_flags():
    from pathlib import Path
    import json
    from longwar.cards import load_card_file
    from longwar.game import GameEngine

    root = Path(__file__).resolve().parents[1]
    engine = GameEngine(load_card_file(root / "cards/cards.json"))
    deck = json.loads((root / "decks/reference.json").read_text())["cards"]
    state = engine.new_game(deck, deck, seed=1, first_player=0)
    key = AlphaBetaSearch.state_key(state)
    for field, value in (
        ("cleanup_pending", True),
        ("cleanup_next_starter", 0),
        ("cleanup_next_chooser", 1),
    ):
        changed = state.clone()
        setattr(changed, field, value)
        assert AlphaBetaSearch.state_key(changed) != key

    hero_spent = state.clone()
    hero_spent.hero_used[0] = not state.hero_used[0]
    assert AlphaBetaSearch.state_key(hero_spent) != key
