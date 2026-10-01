from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite

from .game.actions import Action, Pass
from .game.engine import GameEngine
from .game.model import GameState, Phase
from .protocol import CardField, CardType


MULLIGAN_FORCE_BASE_SCORE = 5.0
MULLIGAN_FORCE_STRENGTH_WEIGHT = 0.08
MULLIGAN_BOND_SCORE = 3.2
MULLIGAN_NAME_SCORE = 3.0
MULLIGAN_ONGOING_NARRATIVE_SCORE = 3.7
MULLIGAN_IMMEDIATE_NARRATIVE_SCORE = 2.6
MULLIGAN_FIRST_STRATAGEM_SCORE = 3.2
MULLIGAN_EXTRA_STRATAGEM_SCORE = 2.0
MULLIGAN_STRATAGEM_CONGESTION_THRESHOLD = 3
MULLIGAN_STRATAGEM_CONGESTION_PENALTY = 0.35
MULLIGAN_UNKNOWN_CARD_SCORE = 2.5

HEURISTIC_DEFAULTS: dict[str, float] = {
    "terminal_win_score": 10000.0,
    "fresh_battle_initiative": 0.70,
    "incomplete_one_card_liability": 0.55,
    "incomplete_two_card_liability": 1.60,
    "close_front_margin": 3,
    "exposed_front_margin": 4,
    "comfortable_front_margin": 5,
    "front_margin_clamp": 10,
    "close_front_bonus": 1.25,
    "rear_persistence_value": 4.0,
    "frontline_persistence_value": 0.75,
    "overkill_margin_weight": 0.45,
    "margin_weight": 0.75,
    "front_control_weight": 7.0,
    "hand_card_weight": 1.25,
    "force_hand_cap": 3,
    "force_hand_weight": 0.35,
    "no_force_penalty": 2.0,
    "command_delta_weight": 0.45,
    "collapse_vulnerability_buffer": 3,
    "collapse_vulnerability_weight": 1.20,
    "projected_command_weight": 0.35,
    "passed_base_penalty": 1.5,
    "passed_hand_cap": 7.0,
    "passed_hand_weight": 0.55,
    "passed_exposure_weight": 1.1,
    "responding_base_bonus": 1.0,
    "responding_hand_cap": 5.0,
    "responding_hand_weight": 0.4,
    "responding_reach_weight": 0.9,
    "incomplete_liability_weight": 1.10,
    "named_formation_weight": 1.5,
    "narrative_weight": 0.75,
    "stratagem_weight": 0.45,
    "completion_option_weight": 0.45,
    "no_option_score": -32768,
    "progress_one_component": 0.35,
    "progress_two_components": 1.35,
    "progress_complete": 2.25,
    "hand_force_base": 0.45,
    "hand_force_need": 0.95,
    "hand_component_base": 0.35,
    "hand_name_need": 1.05,
    "hand_bond_need": 0.95,
    "hand_narrative": 0.40,
    "hand_stratagem": 0.30,
    "discarded_force_availability": 0.35,
    "strategic_formation_progress": 0.85,
    "strategic_hand_construction": 0.30,
    "strategic_deck_size": 0.18,
    "strategic_future_sets": 0.55,
    "strategic_force_availability": 0.40,
    "strategic_affordable_hand": 0.12,
    "rollout_collapse_immediate_buffer": 1,
    "rollout_collapse_near_buffer": 3,
    "rollout_pass_immediate": 1.50,
    "rollout_pass_near": 0.55,
    "rollout_pass_normal": 0.20,
    "rollout_discard": 1.0,
    "rollout_maneuver": 0.90,
    "rollout_force": 1.35,
    "rollout_force_prepared_bonus": 0.90,
    "rollout_bond": 1.0,
    "rollout_bond_on_force": 0.80,
    "rollout_bond_with_name": 0.35,
    "rollout_name": 1.05,
    "rollout_name_on_force": 0.85,
    "rollout_name_with_bond": 0.65,
    "rollout_narrative": 0.75,
    "rollout_ongoing_narrative": 0.70,
    "rollout_stratagem": 0.65,
    "order_discard_construction": 0.55,
    "order_bond_on_force": 0.85,
    "order_bond_prepared": 0.25,
    "order_name_on_force": 0.90,
    "order_name_prepared": 0.30,
    "order_ongoing_narrative": 0.20,
    "order_stratagem": 0.20,
    "order_maneuver": 0.15,
}
HEURISTIC_KEYS: tuple[str, ...] = tuple(HEURISTIC_DEFAULTS)
HEURISTIC_INTEGER_KEYS = frozenset({
    "close_front_margin",
    "collapse_vulnerability_buffer",
    "comfortable_front_margin",
    "exposed_front_margin",
    "force_hand_cap",
    "front_margin_clamp",
    "no_option_score",
    "rollout_collapse_immediate_buffer",
    "rollout_collapse_near_buffer",
})


@dataclass(frozen=True, slots=True)
class HeuristicWeights:
    """Immutable policy values copied once into native C storage."""

    values: tuple[float, ...] = tuple(
        float(HEURISTIC_DEFAULTS[key]) for key in HEURISTIC_KEYS
    )

    def __post_init__(self) -> None:
        if len(self.values) != len(HEURISTIC_KEYS):
            raise ValueError(
                f"expected {len(HEURISTIC_KEYS)} heuristic values, got {len(self.values)}"
            )
        for key, value in zip(HEURISTIC_KEYS, self.values, strict=True):
            if not isfinite(value):
                raise ValueError(f"heuristic weight {key} must be finite")
            if key in HEURISTIC_INTEGER_KEYS and value != int(value):
                raise ValueError(f"heuristic weight {key} must be integral")

    @classmethod
    def standard(cls) -> "HeuristicWeights":
        return cls()

    def as_dict(self) -> dict[str, float]:
        return dict(zip(HEURISTIC_KEYS, self.values, strict=True))

    def with_overrides(self, **changes: float) -> "HeuristicWeights":
        unknown = sorted(set(changes) - set(HEURISTIC_KEYS))
        if unknown:
            raise ValueError("unknown heuristic weights: " + ", ".join(unknown))
        values = self.as_dict()
        values.update({key: float(value) for key, value in changes.items()})
        return type(self)(tuple(values[key] for key in HEURISTIC_KEYS))

    def fingerprint(self) -> str:
        payload = json.dumps(
            self.as_dict(), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


DEFAULT_HEURISTIC_WEIGHTS = HeuristicWeights.standard()


def coerce_heuristic_weights(
    value: HeuristicWeights | Mapping[str, float] | None,
) -> HeuristicWeights:
    """Normalize experiment/user overrides once, outside search hot paths."""
    if value is None:
        return DEFAULT_HEURISTIC_WEIGHTS
    if isinstance(value, HeuristicWeights):
        return value
    if isinstance(value, Mapping):
        return DEFAULT_HEURISTIC_WEIGHTS.with_overrides(
            **{str(key): float(weight) for key, weight in value.items()}
        )
    raise TypeError(
        "heuristic_weights must be HeuristicWeights, a mapping, or None"
    )


def command_preserving_actions(
    engine: GameEngine,
    state: GameState,
    actions: list[Action] | None = None,
) -> tuple[list[Action], int]:
    """Filter only actions that immediately resolve the war as a loss.

    Reaching the Collapse threshold during an unfinished Battle is legal and
    may be strategically correct because later refunds, gains, or Front play
    can still change the Battle-end Command result.
    """
    legal = list(engine.legal_actions(state) if actions is None else actions)
    if len(legal) <= 1:
        return legal, 0

    actor = state.active_player
    preserving: list[Action] = []
    losing: list[Action] = []

    for action in legal:
        can_end_now = (
            state.pass_closing_turns_remaining == 1
            or (
                isinstance(action, Pass)
                and len(state.pass_order) == 1
                and not state.players[actor].passed
            )
        )
        if not can_end_now:
            preserving.append(action)
            continue

        child = state.clone()
        engine.apply(child, action, validate=False)
        immediate_loss = (
            child.phase is Phase.COMPLETE
            and child.winner is not None
            and child.winner != actor
        )
        if immediate_loss:
            losing.append(action)
        else:
            preserving.append(action)

    if not preserving:
        return legal, 0
    return preserving, len(losing)


def opening_mulligan_indices(
    engine: GameEngine,
    hand: list[str],
    *,
    maximum: int | None = None,
) -> tuple[int, ...]:
    """Opening-hand policy, separate from game rules and search algorithms."""
    if maximum is None:
        maximum = engine.rules.mulligan_max_cards
    if maximum <= 0 or not hand:
        return ()

    types = [
        engine.cards[card_id][CardField.TYPE]
        for card_id in hand
    ]
    stratagem_count = types.count(CardType.STRATAGEM)

    scored: list[tuple[float, int]] = []
    seen_stratagems = 0
    for index, card_id in enumerate(hand):
        card = engine.cards[card_id]
        card_type = card[CardField.TYPE]

        if card_type == CardType.FORCE:
            score = MULLIGAN_FORCE_BASE_SCORE + MULLIGAN_FORCE_STRENGTH_WEIGHT * float(card.get(CardField.STRENGTH, 0))
        elif card_type == CardType.BOND:
            score = MULLIGAN_BOND_SCORE
        elif card_type == CardType.NAME:
            score = MULLIGAN_NAME_SCORE
        elif card_type == CardType.NARRATIVE:
            score = (
                MULLIGAN_ONGOING_NARRATIVE_SCORE
                if card.get(CardField.ONGOING, False)
                else MULLIGAN_IMMEDIATE_NARRATIVE_SCORE
            )
        elif card_type == CardType.STRATAGEM:
            seen_stratagems += 1
            score = (
                MULLIGAN_FIRST_STRATAGEM_SCORE
                if seen_stratagems == 1
                else MULLIGAN_EXTRA_STRATAGEM_SCORE
            )
            if stratagem_count >= MULLIGAN_STRATAGEM_CONGESTION_THRESHOLD:
                score -= MULLIGAN_STRATAGEM_CONGESTION_PENALTY
        else:
            score = MULLIGAN_UNKNOWN_CARD_SCORE
        scored.append((score, index))

    scored.sort(key=lambda item: (item[0], item[1]))
    return tuple(sorted(index for _, index in scored[:maximum]))


class HeuristicEvaluator:
    """Thin adapter to the single compiled heuristic implementation."""

    def __init__(
        self,
        weights: HeuristicWeights | None = None,
        *,
        sampled_opponent_resources: bool = False,
    ) -> None:
        self.weights = weights or DEFAULT_HEURISTIC_WEIGHTS
        self.sampled_opponent_resources = bool(sampled_opponent_resources)
        self._cached_engine: GameEngine | None = None
        self._cached_evaluator = None

    def _packed(self, engine: GameEngine, state: GameState):
        native = engine._native_core()
        if (
            not self.sampled_opponent_resources
            and self.weights == DEFAULT_HEURISTIC_WEIGHTS
        ):
            evaluator = engine._native_heuristic()
        elif self._cached_engine is engine and self._cached_evaluator is not None:
            evaluator = self._cached_evaluator
        else:
            from .native_engine import create_heuristic_evaluator
            evaluator = create_heuristic_evaluator(
                native,
                self.weights,
                sampled_opponent_resources=self.sampled_opponent_resources,
            )
            self._cached_engine = engine
            self._cached_evaluator = evaluator
        return native, evaluator, native.from_game_state(state)

    def evaluate(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        return self._state_value(engine, state, player)

    def _state_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        _native, evaluator, packed = self._packed(engine, state)
        return float(evaluator.evaluate(packed, player))

    def _score_action(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
        action: Action,
    ) -> float:
        native, evaluator, packed = self._packed(engine, state)
        native_action = engine._native_action(packed, action)
        return float(
            evaluator.score_action(
                packed,
                player,
                native_action,
            )
        )

    def _hand_construction_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        _native, evaluator, packed = self._packed(engine, state)
        return float(evaluator.hand_construction_value(packed, player))


class StrategicEvaluator(HeuristicEvaluator):
    """Long-horizon heuristic adapter used by search algorithms."""

    def _strategic_state_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        _native, evaluator, packed = self._packed(engine, state)
        return float(evaluator.strategic_evaluate(packed, player))
