from dataclasses import dataclass
from math import inf
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.algorithm

from longwar.algorithms.alpha_beta import (
    AlphaBetaSearch,
    SearchBudget,
    SearchLimit,
    action_completed_turn,
)
from longwar.game.engine import GameEngine
from longwar.game.model import Phase


@dataclass
class _State:
    name: str = "root"
    active_player: int = 0
    phase: Phase = Phase.BATTLE
    turn_number: int = 0
    actions_this_turn: int = 0
    pending_effects: tuple[str, ...] = ()
    pending_draw_discard_for: int | None = None

    def clone(self):
        return _State(
            self.name,
            self.active_player,
            self.phase,
            self.turn_number,
            self.actions_this_turn,
            self.pending_effects,
            self.pending_draw_discard_for,
        )

    def copy_from(self, other):
        self.name = other.name
        self.active_player = other.active_player
        self.phase = other.phase
        self.turn_number = other.turn_number
        self.actions_this_turn = other.actions_this_turn
        self.pending_effects = other.pending_effects
        self.pending_draw_discard_for = other.pending_draw_discard_for


class _TransitionContractEngine:
    def transition_completed_turn(self, before, after, action):
        return GameEngine.transition_completed_turn(
            self,
            before,
            after,
            action,
        )


class _GraphEngine(_TransitionContractEngine):
    rules = SimpleNamespace(actions_per_turn=1)

    def apply(self, state, action, *, validate):
        state.name = action
        state.turn_number += 1
        state.actions_this_turn = 0
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


class _TwoActionEngine(_TransitionContractEngine):
    rules = SimpleNamespace(actions_per_turn=2)

    def apply(self, state, action, *, validate):
        if state.name == "root":
            state.name = "mid"
            state.turn_number += 1
            state.actions_this_turn = 1
            # Action 1 keeps control with the same player.
            return
        if state.name == "mid":
            state.name = "leaf"
            state.turn_number += 1
            state.actions_this_turn = 0
            state.active_player = 1 - state.active_player
            return
        raise AssertionError(f"unexpected state/action: {state.name}/{action}")


class _TwoActionSearch(AlphaBetaSearch):
    @staticmethod
    def state_key(state):
        return state.name

    def ordered_actions(self, state, actor, *, width):
        return {
            "root": ["action-1"],
            "mid": ["end-turn"],
        }.get(state.name, [])


class _TwoActionEvaluator:
    def _strategic_state_value(self, engine, state, player):
        return {"mid": -100.0, "leaf": 7.0}.get(state.name, 0.0)


def test_search_budget_never_counts_rejected_node() -> None:
    budget = SearchBudget(2)

    budget.visit()
    budget.visit()
    with pytest.raises(SearchLimit):
        budget.visit()

    assert budget.nodes == 2


def test_alpha_beta_depth_counts_completed_turns_not_raw_actions():
    search = _TwoActionSearch(
        _TwoActionEngine(),
        _TwoActionEvaluator(),
        candidate_width=2,
    )
    state = _State()
    value = search.search(
        state,
        root_player=0,
        depth=1,
        alpha=-inf,
        beta=inf,
        budget=SearchBudget(20),
        transposition={},
        scratch=[],
    )

    # Depth 1 must include Action 1 and the same player's EndTurn, reaching
    # the next player's decision. Raw-action depth would stop at "mid".
    assert value == 7.0


class _PendingChoiceEngine(_TransitionContractEngine):
    rules = SimpleNamespace(actions_per_turn=2)

    def apply(self, state, action, *, validate):
        if state.name == "root":
            # Action 1 queues a choice for the opponent. The Action has not
            # finished, so neither the action serial nor strategic turn depth
            # advances yet.
            state.name = "pending"
            state.active_player = 1
            state.pending_effects = ("intercept",)
            return
        if state.name == "pending":
            # Resolving the choice finishes Action 1 and returns control to
            # the original actor for Action 2.
            state.name = "mid"
            state.active_player = 0
            state.pending_effects = ()
            state.turn_number += 1
            state.actions_this_turn = 1
            return
        if state.name == "mid":
            state.name = "leaf"
            state.active_player = 1
            state.turn_number += 1
            state.actions_this_turn = 0
            return
        raise AssertionError(f"unexpected state/action: {state.name}/{action}")


class _PendingChoiceSearch(AlphaBetaSearch):
    @staticmethod
    def state_key(state):
        return state.name

    def ordered_actions(self, state, actor, *, width):
        return {
            "root": ["card"],
            "pending": ["effect-choice"],
            "mid": ["action-2"],
        }.get(state.name, [])


def test_pending_opponent_choice_is_not_a_completed_turn() -> None:
    engine = _PendingChoiceEngine()
    state = _State()
    child = state.clone()
    engine.apply(child, "card", validate=False)

    assert child.active_player != state.active_player
    assert not action_completed_turn(engine, state, child, "card")


def test_alpha_beta_pending_opponent_choice_does_not_consume_turn_depth():
    search = _PendingChoiceSearch(
        _PendingChoiceEngine(),
        _TwoActionEvaluator(),
        candidate_width=2,
    )
    state = _State()
    value = search.search(
        state,
        root_player=0,
        depth=1,
        alpha=-inf,
        beta=inf,
        budget=SearchBudget(20),
        transposition={},
        scratch=[],
    )

    assert value == 7.0


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
    from longwar.game.model import Front, Position, Rank
    root = Path(__file__).resolve().parents[1]
    engine = GameEngine(load_card_file(root / "cards/cards.json"))
    deck = json.loads((root / "decks/mobility-open-bonds.json").read_text())["cards"]
    state = engine.new_game(
        deck,
        deck,
        seed=1,
        first_player=0,
        opening_bonus=False,
    )
    key = AlphaBetaSearch.state_key(state)

    pending_draw = state.clone()
    pending_draw.pending_draw_discard_for = 0
    assert AlphaBetaSearch.state_key(pending_draw) != key

    hero_spent = state.clone()
    hero_spent.hero_used[0] = not state.hero_used[0]
    assert AlphaBetaSearch.state_key(hero_spent) != key

    passed = state.clone()
    passed.players[0].passed = True
    passed.pass_order = [0]
    passed.closing_turns_remaining = 2
    assert AlphaBetaSearch.state_key(passed) != key

    acted = state.clone()
    acted.actions_this_turn = 1
    assert AlphaBetaSearch.state_key(acted) != key

    exhausted = state.clone()
    exhausted.slot(
        0,
        Position(Front.FIRST, Rank.FRONT),
    ).exhausted = True
    assert AlphaBetaSearch.state_key(exhausted) != key

    revealed = state.clone()
    from longwar.game.model import StratagemState
    revealed.stratagems[0] = StratagemState(
        "the-ground-was-held",
        revealed=True,
    )
    hidden = state.clone()
    hidden.stratagems[0] = StratagemState(
        "the-ground-was-held",
        revealed=False,
    )
    assert AlphaBetaSearch.state_key(revealed) != AlphaBetaSearch.state_key(hidden)

    from longwar.game.model import ConstraintKind, OperationConstraint

    persistent_for_turn = state.clone()
    persistent_for_turn.constraints = [
        OperationConstraint(
            source_card="the-long-march",
            player=0,
            kind=ConstraintKind.MANEUVER,
            source_owner=0,
            expires_end_of_activated_turn=False,
        )
    ]
    expires_this_turn = state.clone()
    expires_this_turn.constraints = [
        OperationConstraint(
            source_card="the-long-march",
            player=0,
            kind=ConstraintKind.MANEUVER,
            source_owner=0,
            expires_end_of_activated_turn=True,
        )
    ]
    assert AlphaBetaSearch.state_key(
        persistent_for_turn
    ) != AlphaBetaSearch.state_key(expires_this_turn)


def test_python_state_key_tracks_every_game_state_field() -> None:
    """Every GameState field must be referenced by state_key(), or be
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
        "free_maneuver_source": (
            "diagnostic attribution only: identifies which card granted an "
            "already-free Maneuver, but does not affect legality, cost, or evaluation"
        ),
        "players": "nested PlayerState fields verified individually above and by construction",
        "board": "nested Slot fields (force/bond/name/exhausted/temporary_strength and Maneuver state) are represented above",
        "narratives": "nested NarrativeState card ids are represented above",
        "stratagems": "nested StratagemState card ids are represented above",
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
