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


def test_python_state_key_tracks_every_game_state_field() -> None:
    """Guard against a repeat of the cache-key gap that let
    cleanup_pending/cleanup_next_starter/cleanup_next_chooser be silently
    ignored: every GameState field must be referenced by state_key(), or be
    declared exempt here with a reason a reviewer can check.

    A field is only safe to exempt if it is never read by legal_actions,
    by apply()'s transition/branching logic, or by StrategicEvaluator's
    reachable evaluation call graph (evaluate_fast, strategic_evaluate_fast
    and everything they call) in a way that changes a returned value -
    write-only telemetry/UI fields qualify; anything else does not.
    """
    import dataclasses
    import inspect

    from longwar.game.model import GameState

    exempt = {
        "command_spent_this_battle": "write-only telemetry counter",
        "command_refunded_this_battle": "write-only telemetry counter",
        "completion_command_refunded_this_battle": "write-only telemetry counter",
        "battle_start_command": "write-only telemetry, only surfaced via last_battle_snapshot reporting",
        "battle_start_hand_size": "write-only telemetry, only surfaced via last_battle_snapshot reporting",
        "cards_drawn_this_battle": "write-only telemetry counter",
        "completion_count_this_battle": "write-only telemetry counter",
        "deck_reshuffles": "write-only telemetry counter",
        "reshuffle_card_totals": "write-only telemetry counter",
        "reshuffle_hand_card_totals": "write-only telemetry counter",
        "opening_hands": "recorded once for UI/reporting, never read back by legality/evaluation",
        "last_battle_snapshot": "diagnostic snapshot dict, not read by legality or StrategicEvaluator",
        "observations": "append-only display log, never read by legality/evaluation",
        "known_hidden_hand": (
            "used only by the ISMCTS information-set hash (a separate cache "
            "key), not by legal_actions or StrategicEvaluator"
        ),
        "players": "nested PlayerState fields verified individually above and by construction",
        "board": "nested Slot fields (subject/link/name/temporary_strength) all represented above",
        "schemes": "nested SchemeState fields (card_id/revealed) all represented above",
        "stratagems": "nested StratagemState fields (card_id/revealed) all represented above",
    }

    all_field_names = {f.name for f in dataclasses.fields(GameState)}
    stale = set(exempt) - all_field_names
    assert not stale, f"Exemption set references fields GameState no longer has: {stale}"

    source = inspect.getsource(AlphaBetaSearch.state_key)
    missing = [
        f.name
        for f in dataclasses.fields(GameState)
        if f.name not in exempt and f"state.{f.name}" not in source
    ]
    assert not missing, (
        f"GameState field(s) {missing} are not referenced by state_key() and "
        "are not declared exempt in this test. Add them to state_key() if "
        "they can affect legal actions, search values, or candidate "
        "ordering; otherwise add them to the exemption set with a reason."
    )
