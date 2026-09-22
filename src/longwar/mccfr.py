from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from itertools import groupby
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
from .mccfr_core import (
    BACKEND,
    CFRNode,
    external_sampling_traverse,
    longwar_external_sampling_traverse,
)

try:
    from ._fast_search import (
        FastEngine as PrimitiveFastEngine,
        fast_external_sampling_traverse,
        stable_information_id_from_fast_key,
    )
except ImportError:
    PrimitiveFastEngine = None
    fast_external_sampling_traverse = None
    stable_information_id_from_fast_key = None


def _counter_view(cards: list[str]) -> list[list[Any]]:
    return [[card_id, count] for card_id, count in sorted(Counter(cards).items())]


def _position_view(position: Position) -> list[Any]:
    return [int(position.front), position.rank.value]


def _target_view(target: BoardTarget) -> list[Any]:
    return [target.player, *_position_view(target.position)]


@lru_cache(maxsize=8192)
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


def _counter_key(cards: list[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(Counter(cards).items()))


def _freeze_view(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze_view(item) for item in value)
    return value


def information_set_key(state: GameState, player: int) -> tuple[tuple[str, Any], ...]:
    """Hashable form of the public information state used during search.

    This deliberately avoids JSON construction and SHA-256 on every tree
    visit. Tuples serialize to the same JSON arrays as the previous list-based
    observation, so exported information-set ids remain stable.
    """
    opponent = 1 - player
    own = state.players[player]
    other = state.players[opponent]

    board = tuple(
        tuple(
            (
                int(position.front),
                position.rank.value,
                state.slot(owner, position).subject,
                state.slot(owner, position).link,
                state.slot(owner, position).name,
                state.slot(owner, position).temporary_strength,
            )
            for position in all_positions()
        )
        for owner in range(2)
    )
    schemes = tuple(
        tuple(
            _freeze_view(_scheme_view(state, player, owner, front))
            for front in Front
        )
        for owner in range(2)
    )

    return (
        ("viewer", player),
        ("phase", state.phase.value),
        ("battle", state.battle),
        ("active_player", state.active_player),
        ("chooser", state.chooser),
        ("victories", tuple(p.victories for p in state.players)),
        ("passed", tuple(p.passed for p in state.players)),
        ("pass_order", tuple(state.pass_order)),
        ("discarded_this_battle", tuple(state.discarded_this_battle)),
        ("board", board),
        ("schemes", schemes),
        (
            "stratagems",
            tuple(
                _freeze_view(_stratagem_view(state, player, owner))
                for owner in range(2)
            ),
        ),
        ("stratagem_used", tuple(state.stratagem_used)),
        ("own_hand", _counter_key(own.hand)),
        ("own_deck", _counter_key(own.deck)),
        ("own_discard", tuple(own.discard)),
        ("opponent_hand_count", len(other.hand)),
        (
            "known_opponent_hand",
            _counter_key(state.known_hidden_cards(player, opponent, "hand")),
        ),
        ("opponent_deck_count", len(other.deck)),
        ("opponent_discard", tuple(other.discard)),
    )


@lru_cache(maxsize=32768)
def _sorted_card_tuple(cards: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(cards))


def _sorted_card_multiset(cards: list[str]) -> tuple[str, ...]:
    """Cheap cached multiset representation for the internal search table."""
    return _sorted_card_tuple(tuple(cards))


def _search_information_set_key(state: GameState, player: int) -> tuple[Any, ...]:
    """Compact information key used only inside MCCFR traversal."""
    opponent = 1 - player
    own = state.players[player]
    other = state.players[opponent]

    board = tuple(
        tuple(
            (
                slot.subject,
                slot.link,
                slot.name,
                slot.temporary_strength,
            )
            for front in side
            for slot in front
        )
        for side in state.board
    )

    scheme_rows = []
    for owner in (0, 1):
        row = []
        for scheme in state.schemes[owner]:
            if scheme is None:
                row.append(None)
            elif owner == player or scheme.revealed:
                row.append((scheme.card_id, bool(scheme.revealed)))
            else:
                row.append(("hidden", False))
        scheme_rows.append(tuple(row))
    schemes = tuple(scheme_rows)

    stratagem_views = []
    for owner in (0, 1):
        stratagem = state.stratagems[owner]
        if stratagem is None:
            stratagem_views.append(None)
        elif owner == player or stratagem.revealed:
            stratagem_views.append(
                (stratagem.card_id, bool(stratagem.revealed))
            )
        else:
            stratagem_views.append(("hidden", False))

    known_opponent_hand: tuple[str, ...]
    if state.observations:
        known_opponent_hand = _sorted_card_multiset(
            state.known_hidden_cards(player, opponent, "hand")
        )
    else:
        known_opponent_hand = ()

    return (
        player,
        state.phase.value,
        state.battle,
        state.active_player,
        state.chooser,
        (
            state.players[0].victories,
            state.players[1].victories,
        ),
        (
            state.players[0].passed,
            state.players[1].passed,
        ),
        tuple(state.pass_order),
        (
            state.discarded_this_battle[0],
            state.discarded_this_battle[1],
        ),
        board,
        schemes,
        tuple(stratagem_views),
        (
            state.stratagem_used[0],
            state.stratagem_used[1],
        ),
        _sorted_card_multiset(own.hand),
        _sorted_card_multiset(own.deck),
        tuple(own.discard),
        len(other.hand),
        known_opponent_hand,
        len(other.deck),
        tuple(other.discard),
    )


def _counter_view_from_sorted(cards: tuple[str, ...]) -> list[list[Any]]:
    return [[card_id, sum(1 for _ in group)] for card_id, group in groupby(cards)]


def _search_key_observation(key: tuple[Any, ...]) -> dict[str, Any]:
    (
        player,
        phase,
        battle,
        active_player,
        chooser,
        victories,
        passed,
        pass_order,
        discarded_this_battle,
        compact_board,
        schemes,
        stratagems,
        stratagem_used,
        own_hand,
        own_deck,
        own_discard,
        opponent_hand_count,
        known_opponent_hand,
        opponent_deck_count,
        opponent_discard,
    ) = key

    board: list[Any] = []
    positions = all_positions()
    for owner_rows in compact_board:
        rows = []
        for position, slot in zip(positions, owner_rows):
            subject, link, name, temporary_strength = slot
            rows.append([
                int(position.front),
                position.rank.value,
                subject,
                link,
                name,
                temporary_strength,
            ])
        board.append(rows)

    def thaw(value: Any) -> Any:
        if isinstance(value, tuple):
            return [thaw(item) for item in value]
        return value

    return {
        "viewer": player,
        "phase": phase,
        "battle": battle,
        "active_player": active_player,
        "chooser": chooser,
        "victories": list(victories),
        "passed": list(passed),
        "pass_order": list(pass_order),
        "discarded_this_battle": list(discarded_this_battle),
        "board": board,
        "schemes": thaw(schemes),
        "stratagems": thaw(stratagems),
        "stratagem_used": list(stratagem_used),
        "own_hand": _counter_view_from_sorted(own_hand),
        "own_deck": _counter_view_from_sorted(own_deck),
        "own_discard": list(own_discard),
        "opponent_hand_count": opponent_hand_count,
        "known_opponent_hand": _counter_view_from_sorted(known_opponent_hand),
        "opponent_deck_count": opponent_deck_count,
        "opponent_discard": list(opponent_discard),
    }


def _stable_id_from_search_key(key: tuple[Any, ...]) -> str:
    payload = json.dumps(
        _search_key_observation(key),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _information_set_id_from_key(key: tuple[tuple[str, Any], ...]) -> str:
    payload = json.dumps(
        dict(key),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class InformationNodeStore(dict[object, CFRNode]):
    """Search table keyed by cheap tuples with lazy stable-id conversion."""

    def __init__(self) -> None:
        super().__init__()
        self._id_by_key: dict[object, str] = {}
        self._key_by_id: dict[str, object] = {}

    def stable_id(self, key: object) -> str:
        cached = self._id_by_key.get(key)
        if cached is not None:
            return cached
        if not isinstance(key, tuple):
            return str(key)
        if key and isinstance(key[0], int):
            stable = _stable_id_from_search_key(key)
        else:
            stable = _information_set_id_from_key(key)
        self._id_by_key[key] = stable
        self._key_by_id[stable] = key
        return stable

    def _key_for_stable_id(self, stable_id: str) -> object | None:
        cached = self._key_by_id.get(stable_id)
        if cached is not None:
            return cached
        for key in dict.keys(self):
            if self.stable_id(key) == stable_id:
                return key
        return None

    def __getitem__(self, key: object) -> CFRNode:
        if isinstance(key, str) and not dict.__contains__(self, key):
            internal = self._key_for_stable_id(key)
            if internal is None:
                raise KeyError(key)
            key = internal
        return dict.__getitem__(self, key)

    def get(self, key: object, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


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
    return _information_set_id_from_key(information_set_key(state, player))


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
        direct_traversal: bool = True,
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
        self.chance_rng = random.Random(seed ^ 0x5F3759DF)
        self.seed = seed
        self.max_depth = max_depth
        self.leaf_scale = leaf_scale
        self.direct_traversal = direct_traversal
        self.nodes = InformationNodeStore()
        self._primitive_nodes: dict[bytes, CFRNode] = {}
        self._primitive_engine = (
            PrimitiveFastEngine(engine)
            if (
                direct_traversal
                and PrimitiveFastEngine is not None
                and fast_external_sampling_traverse is not None
            )
            else None
        )
        self._used_primitive_training = False
        self.iterations = 0
        self._leaf_agent = HeuristicAgent(seed=seed, exploration=0.0)

    def train(self, iterations: int) -> TrainingSummary:
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        if self.deck_a is None or self.deck_b is None:
            raise ValueError("Root-deal training requires both concrete decklists")

        utility_sum = [0.0, 0.0]
        for _ in range(iterations):
            root = self.engine._new_game_with_rng(
                self.deck_a,
                self.deck_b,
                rng=self.chance_rng,
                first_player=self.chance_rng.randrange(2),
            )
            if self._primitive_engine is not None:
                fast_root = self._primitive_engine.from_game_state(root)
                for traverser in (0, 1):
                    utility_sum[traverser] += fast_external_sampling_traverse(
                        self._primitive_engine,
                        fast_root,
                        traverser,
                        max_depth=self.max_depth,
                        nodes=self._primitive_nodes,
                        rng=self.rng,
                        node_factory=CFRNode,
                        leaf_scale=self.leaf_scale,
                    )
                self._used_primitive_training = True
            else:
                for traverser in (0, 1):
                    utility_sum[traverser] += self._traverse(
                        root,
                        traverser,
                        depth=0,
                    )
            self.iterations += 1

        return TrainingSummary(
            iterations=self.iterations,
            traversals=self.iterations * 2,
            information_sets=(
                len(self._primitive_nodes)
                if self._used_primitive_training
                else len(self.nodes)
            ),
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
                    root,
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
                    root,
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

    def _search_child(
        self,
        current: GameState,
        action: Action,
        child_depth: int,
        scratch_by_depth: dict[int, GameState],
    ) -> GameState:
        child = scratch_by_depth.get(child_depth)
        if child is None:
            child = current.clone()
            scratch_by_depth[child_depth] = child
        else:
            child.copy_from(current)
        self.engine.apply(child, action, validate=False)
        return child

    def _traverse(
        self,
        state: GameState,
        traverser: int,
        *,
        depth: int,
    ) -> float:
        # The object-state traversal remains the correctness/reference path.
        # Offline deck training uses the primitive-array engine instead.
        # Keeping this path generic avoids maintaining two independent native
        # traversals over the mutable Python GameState representation.
        return self._traverse_generic(
            state,
            traverser,
            depth=depth,
            scratch_by_depth={},
        )

    def _traverse_generic(
        self,
        state: GameState,
        traverser: int,
        *,
        depth: int,
        scratch_by_depth: dict[int, GameState],
    ) -> float:
        depth_by_state_id = {id(state): depth}

        def next_state(current: GameState, action: Action) -> GameState:
            child_depth = depth_by_state_id[id(current)] + 1
            child = self._search_child(
                current,
                action,
                child_depth,
                scratch_by_depth,
            )
            depth_by_state_id[id(child)] = child_depth
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
            information_set_id=_search_information_set_key,
            next_state=next_state,
            leaf_value=self._leaf_value,
        )

    def _leaf_value(self, state: GameState, traverser: int) -> float:
        raw = self._leaf_agent.evaluate(self.engine, state, traverser)
        return math.tanh(raw / self.leaf_scale)

    def policy_payload(self) -> dict[str, Any]:
        infosets: dict[str, Any] = {}
        if self._used_primitive_training:
            if (
                self._primitive_engine is None
                or stable_information_id_from_fast_key is None
            ):
                raise RuntimeError("Primitive MCCFR export backend is unavailable")
            for internal_key, node in self._primitive_nodes.items():
                info_id = stable_information_id_from_fast_key(
                    self._primitive_engine,
                    internal_key,
                )
                raw_keys = sorted(node.regret_sum)
                serialized = {
                    key: self._primitive_engine.action_key(key)
                    for key in raw_keys
                }
                average = node.average_strategy(raw_keys)
                current = node.strategy(raw_keys)
                infosets[info_id] = {
                    "visits": node.visits,
                    "average_visits": node.average_visits,
                    "average_strategy": {
                        serialized[key]: average[key]
                        for key in raw_keys
                    },
                    "current_strategy": {
                        serialized[key]: current[key]
                        for key in raw_keys
                    },
                    "regret_sum": {
                        serialized[key]: node.regret_sum[key]
                        for key in raw_keys
                    },
                    "strategy_sum": {
                        serialized[key]: node.strategy_sum.get(key, 0.0)
                        for key in raw_keys
                    },
                }
        else:
            for internal_key, node in self.nodes.items():
                info_id = self.nodes.stable_id(internal_key)
                keys = sorted(node.regret_sum)
                infosets[info_id] = {
                    "visits": node.visits,
                    "average_visits": node.average_visits,
                    "average_strategy": node.average_strategy(keys),
                    "current_strategy": node.strategy(keys),
                    "regret_sum": {key: node.regret_sum[key] for key in keys},
                    "strategy_sum": {
                        key: node.strategy_sum.get(key, 0.0)
                        for key in keys
                    },
                }

        return {
            "schema_version": 1,
            "algorithm": "depth_limited_external_sampling_mccfr",
            "execution_backend": BACKEND,
            "traversal_backend": (
                "primitive_array_cython"
                if self._used_primitive_training
                else "generic_external_sampling"
            ),
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
