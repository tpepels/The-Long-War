from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable

from .agents.heuristic_agent import HeuristicAgent
from .game.actions import (
    Action,
    BoardTarget,
    ChooseFirst,
    Pass,
    PlayLink,
    PlayName,
    PlayPlot,
    PlayScheme,
    PlaySubject,
    SetStratagem,
)
from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState, Phase, Position, Rank
from .mccfr_core import CFRNode, external_sampling_traverse


def _counter_view(cards: list[str]) -> list[list[Any]]:
    return [[card_id, count] for card_id, count in sorted(Counter(cards).items())]


def _position_view(position: Position) -> list[Any]:
    return [int(position.front), position.rank.value]


def _target_view(target: BoardTarget) -> list[Any]:
    return [target.player, *_position_view(target.position)]


def action_key(action: Action) -> str:
    """Stable serialization used inside an information-set policy."""
    if isinstance(action, Pass):
        return "pass"
    if isinstance(action, ChooseFirst):
        return f"choose_first:{action.player}"
    if isinstance(action, PlaySubject):
        return f"subject:{action.card_id}:{int(action.position.front)}:{action.position.rank.value}"
    if isinstance(action, PlayLink):
        return f"link:{action.card_id}:{int(action.position.front)}:{action.position.rank.value}"
    if isinstance(action, PlayName):
        move = "stay"
        if action.move_to is not None:
            move = f"{int(action.move_to.front)}:{action.move_to.rank.value}"
        return (
            f"name:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}:{move}"
        )
    if isinstance(action, PlayScheme):
        return f"scheme:{action.card_id}:{int(action.front)}"
    if isinstance(action, SetStratagem):
        return f"stratagem:{action.card_id}"
    if isinstance(action, PlayPlot):
        targets = ";".join(
            f"{target.player}:{int(target.position.front)}:{target.position.rank.value}"
            for target in action.targets
        )
        return f"plot:{action.card_id}:{targets}"
    raise TypeError(f"Unsupported action type: {type(action)!r}")


def _scheme_view(state: GameState, viewer: int, owner: int, front: Front) -> Any:
    scheme = state.scheme(owner, front)
    if scheme is None:
        return None
    if owner == viewer or scheme.revealed:
        return [scheme.card_id, bool(scheme.revealed)]
    return ["hidden", False]


def _stratagem_view(state: GameState, viewer: int, owner: int) -> Any:
    stratagem = state.stratagem(owner)
    if stratagem is None:
        return None
    if owner == viewer or stratagem.revealed:
        return [stratagem.card_id, bool(stratagem.revealed)]
    return ["hidden", False]


def information_set_observation(state: GameState, player: int) -> dict[str, Any]:
    """Return the state abstraction visible to one player.

    Hidden opponent hand identities and both deck orders are deliberately
    excluded. The acting player's remaining deck is represented only as a
    multiset, which is inferable from a known deck list and observed own cards.
    """
    opponent = 1 - player
    own = state.players[player]
    other = state.players[opponent]

    board: list[Any] = []
    for owner in range(2):
        owner_rows = []
        for position in all_positions():
            slot = state.slot(owner, position)
            owner_rows.append(
                [
                    int(position.front),
                    position.rank.value,
                    slot.subject,
                    slot.link,
                    slot.name,
                    slot.temporary_strength,
                ]
            )
        board.append(owner_rows)

    schemes = [
        [
            _scheme_view(state, player, owner, front)
            for front in Front
        ]
        for owner in range(2)
    ]

    return {
        "viewer": player,
        "phase": state.phase.value,
        "battle": state.battle,
        "active_player": state.active_player,
        "chooser": state.chooser,
        "victories": [p.victories for p in state.players],
        "passed": [p.passed for p in state.players],
        "pass_order": list(state.pass_order),
        "discarded_this_battle": list(state.discarded_this_battle),
        "board": board,
        "schemes": schemes,
        "stratagems": [
            _stratagem_view(state, player, owner)
            for owner in range(2)
        ],
        "stratagem_used": list(state.stratagem_used),
        "own_hand": _counter_view(own.hand),
        "own_deck": _counter_view(own.deck),
        "own_discard": list(own.discard),
        "opponent_hand_count": len(other.hand),
        "known_opponent_hand": _counter_view(
            state.known_hidden_cards(player, opponent, "hand")
        ),
        "opponent_deck_count": len(other.deck),
        "opponent_discard": list(other.discard),
    }


def information_set_id(state: GameState, player: int) -> str:
    payload = json.dumps(
        information_set_observation(state, player),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class TrainingSummary:
    iterations: int
    traversals: int
    information_sets: int
    max_depth: int
    mean_sampled_utility_p0: float
    mean_sampled_utility_p1: float


class MCCFRTrainer:
    """Depth-limited external-sampling Monte Carlo CFR.

    Chance is sampled by shuffling/drawing a fresh complete state at the root
    of every iteration. On the traversing player's nodes every legal action is
    expanded; on the opponent's nodes one action is sampled from regret
    matching. This is the external-sampling MCCFR update. The explicit
    approximation is the depth limit: frontier states are evaluated by the
    public-information heuristic evaluator rather than recursively solving the
    rest of the match.
    """

    def __init__(
        self,
        engine: GameEngine,
        deck_a: list[str] | None,
        deck_b: list[str] | None,
        *,
        seed: int = 1701,
        max_depth: int = 3,
        leaf_scale: float = 100.0,
    ):
        if max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        self.engine = engine
        self.deck_a = list(deck_a) if deck_a is not None else None
        self.deck_b = list(deck_b) if deck_b is not None else None
        if self.deck_a is not None:
            self.engine.validate_deck(self.deck_a)
        if self.deck_b is not None:
            self.engine.validate_deck(self.deck_b)
        self.rng = random.Random(seed)
        self.seed = seed
        self.max_depth = max_depth
        self.leaf_scale = leaf_scale
        self.nodes: dict[str, CFRNode] = {}
        self.iterations = 0
        self._leaf_agent = HeuristicAgent(seed=seed, exploration=0.0)

    def train(self, iterations: int) -> TrainingSummary:
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        if self.deck_a is None or self.deck_b is None:
            raise ValueError("Root-deal training requires both concrete decklists")

        utility_sum = [0.0, 0.0]
        for _ in range(iterations):
            chance_seed = self.rng.randrange(0, 2**31)
            first_player = self.rng.randrange(2)
            root = self.engine.new_game(
                self.deck_a,
                self.deck_b,
                seed=chance_seed,
                first_player=first_player,
            )
            for traverser in (0, 1):
                utility_sum[traverser] += self._traverse(
                    root.clone(),
                    traverser,
                    depth=0,
                )
            self.iterations += 1

        return TrainingSummary(
            iterations=self.iterations,
            traversals=self.iterations * 2,
            information_sets=len(self.nodes),
            max_depth=self.max_depth,
            mean_sampled_utility_p0=utility_sum[0] / iterations,
            mean_sampled_utility_p1=utility_sum[1] / iterations,
        )

    def train_from_state(
        self,
        root: GameState,
        iterations: int,
    ) -> TrainingSummary:
        """Train repeatedly from one fully specified state.

        This is useful for deterministic algorithm tests and is also the
        primitive needed for future online re-solving. Both players are used
        as traverser on every iteration, exactly as in root-deal training.
        """
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        if root.phase is Phase.COMPLETE:
            raise ValueError("Cannot train from a terminal state")

        utility_sum = [0.0, 0.0]
        for _ in range(iterations):
            for traverser in (0, 1):
                utility_sum[traverser] += self._traverse(
                    root.clone(),
                    traverser,
                    depth=0,
                )
            self.iterations += 1

        return TrainingSummary(
            iterations=self.iterations,
            traversals=self.iterations * 2,
            information_sets=len(self.nodes),
            max_depth=self.max_depth,
            mean_sampled_utility_p0=utility_sum[0] / iterations,
            mean_sampled_utility_p1=utility_sum[1] / iterations,
        )

    def train_from_sampler(
        self,
        root_sampler: Callable[[], GameState],
        iterations: int,
    ) -> TrainingSummary:
        """Train from a freshly sampled compatible root each iteration.

        This is the online re-solving primitive: all sampled determinizations
        may differ in hidden information while sharing the acting player's
        root information set.
        """
        if iterations <= 0:
            raise ValueError("iterations must be positive")

        utility_sum = [0.0, 0.0]
        for _ in range(iterations):
            root = root_sampler()
            if root.phase is Phase.COMPLETE:
                raise ValueError("Root sampler returned a terminal state")
            for traverser in (0, 1):
                utility_sum[traverser] += self._traverse(
                    root.clone(),
                    traverser,
                    depth=0,
                )
            self.iterations += 1

        return TrainingSummary(
            iterations=self.iterations,
            traversals=self.iterations * 2,
            information_sets=len(self.nodes),
            max_depth=self.max_depth,
            mean_sampled_utility_p0=utility_sum[0] / iterations,
            mean_sampled_utility_p1=utility_sum[1] / iterations,
        )

    def _traverse(
        self,
        state: GameState,
        traverser: int,
        *,
        depth: int,
    ) -> float:
        def next_state(current: GameState, action: Action) -> GameState:
            child = current.clone()
            self.engine.apply(child, action)
            return child

        return external_sampling_traverse(
            state,
            traverser,
            depth=depth,
            max_depth=self.max_depth,
            nodes=self.nodes,
            rng=self.rng,
            is_terminal=lambda current: current.phase is Phase.COMPLETE,
            terminal_utility=lambda current, player: (
                1.0 if current.winner == player else -1.0
            ),
            current_player=lambda current: current.active_player,
            legal_actions=self.engine.legal_actions,
            action_key=action_key,
            information_set_id=information_set_id,
            next_state=next_state,
            leaf_value=self._leaf_value,
        )

    def _leaf_value(self, state: GameState, traverser: int) -> float:
        raw = self._leaf_agent.evaluate(self.engine, state, traverser)
        return math.tanh(raw / self.leaf_scale)

    def policy_payload(self) -> dict[str, Any]:
        infosets: dict[str, Any] = {}
        for info_id, node in self.nodes.items():
            keys = sorted(node.regret_sum)
            infosets[info_id] = {
                "visits": node.visits,
                "average_visits": node.average_visits,
                "average_strategy": node.average_strategy(keys),
                "current_strategy": node.strategy(keys),
                "regret_sum": {key: node.regret_sum[key] for key in keys},
            }

        return {
            "schema_version": 1,
            "algorithm": "depth_limited_external_sampling_mccfr",
            "iterations": self.iterations,
            "traversals": self.iterations * 2,
            "max_depth": self.max_depth,
            "leaf_evaluator": {
                "type": "heuristic_state_value",
                "transform": "tanh(value / leaf_scale)",
                "leaf_scale": self.leaf_scale,
            },
            "chance_sampling": "fresh root shuffle/draw and starting player per iteration",
            "mulligan_policy": "no mulligan during MCCFR root sampling",
            "information_abstraction": {
                "includes": [
                    "public battlefield and discard state",
                    "own hand identities",
                    "own remaining deck multiset",
                    "public hand/deck counts",
                    "own hidden Scheme identity",
                ],
                "excludes": [
                    "opponent hand identities",
                    "both deck orders",
                    "opponent unrevealed Scheme identity",
                    "full action history",
                ],
                "note": "This is an imperfect-recall state abstraction, not an exact perfect-recall game tree.",
            },
            "average_policy": "own-reach-weighted external-sampling average strategy",
            "infosets": infosets,
        }
