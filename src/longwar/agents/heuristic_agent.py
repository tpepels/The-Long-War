from __future__ import annotations

import random
from dataclasses import dataclass
from math import inf

from ..game.actions import (
    Action,
    ChooseFirst,
    Pass,
    PlayLink,
    PlayName,
    PlayScheme,
    SetStratagem,
)
from ..game.engine import GameEngine, all_positions
from ..game.model import Front, GameState, Phase


@dataclass(frozen=True)
class ScoredAction:
    action: Action
    score: float


class HeuristicAgent:
    """One-ply, public-information agent.

    The agent may inspect its own hand, all public battlefield information,
    public hand sizes, decks/discards sizes, Victory markers, and revealed
    state. It never evaluates the identities of cards in the opponent's hand.
    """

    def __init__(
        self,
        seed: int,
        *,
        exploration: float = 0.02,
    ):
        self.rng = random.Random(seed)
        self.exploration = exploration
        self.last_decision: dict[str, float | int | str] = {}

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        player = state.active_player
        actions = engine.legal_actions(state)

        if len(actions) == 1:
            self.last_decision = {
                "candidate_count": 1,
                "selected_score": 0.0,
                "score_gap": 0.0,
                "selected_action": type(actions[0]).__name__,
            }
            return actions[0]

        scored = [
            ScoredAction(action, self._score_action(engine, state, player, action))
            for action in actions
        ]
        # Randomize exact score ties with the agent's seeded RNG before
        # sorting. Otherwise semantically identical choices (notably hidden
        # Stratagem sets) are selected by card-id/repr ordering, which creates
        # fake play-rate differences in simulation telemetry.
        self.rng.shuffle(scored)
        scored.sort(key=lambda item: item.score, reverse=True)

        if self.exploration > 0 and self.rng.random() < self.exploration:
            # Explore among the best quarter rather than selecting nonsense.
            width = max(1, len(scored) // 4)
            selected = self.rng.choice(scored[:width])
        else:
            selected = scored[0]

        second = scored[1].score if len(scored) > 1 else selected.score
        self.last_decision = {
            "candidate_count": len(scored),
            "selected_score": selected.score,
            "score_gap": selected.score - second,
            "selected_action": type(selected.action).__name__,
        }
        return selected.action

    def evaluate(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        """Public-information state value used by search algorithms."""
        return self._state_value(engine, state, player)

    def _score_action(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
        action: Action,
    ) -> float:
        if isinstance(action, ChooseFirst):
            # Acting second provides information and preserves response value.
            # This is deliberately a small prior: future learned agents may
            # discover that specific decks want the initiative instead.
            return 0.5 if action.player != player else 0.0

        if isinstance(action, Pass):
            return self._score_pass(engine, state, player)

        clone = state.clone()
        engine.apply(clone, action)
        score = self._state_value(engine, clone, player)

        # The engine state already includes a Link's immediate Strength and a
        # face-down Scheme's Front bonus. Keep only small priors for option
        # value that a one-ply evaluator cannot see directly.
        if isinstance(action, PlayLink):
            score += 0.10

        if isinstance(action, PlayName):
            score += 0.35

        if isinstance(action, PlayScheme):
            score += 0.20

        if isinstance(action, SetStratagem):
            # Setting a Stratagem is a free pre-action deployment, so a
            # one-ply evaluator must credit the preserved normal action.
            score += 1.35

        return score

    def _score_pass(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        clone = state.clone()
        engine.apply(clone, Pass())

        # If passing resolves the Battle, the ordinary state evaluator can
        # directly value the resulting Victory marker / match result.
        if clone.phase is not Phase.BATTLE or clone.battle != state.battle:
            return self._state_value(engine, clone, player)

        margins = self._front_margins(engine, state, player)
        controls = sum(margin > 0 for margin in margins)
        tied = sum(margin == 0 for margin in margins)
        total_margin = sum(margins)

        opponent_hand = len(state.players[1 - player].hand)
        own_hand = len(state.players[player].hand)

        score = self._state_value(engine, state, player)

        if controls >= 2:
            positive_margins = [margin for margin in margins if margin > 0]
            weakest_control = min(positive_margins) if positive_margins else 0
            # Saving cards is valuable, but a large opposing hand represents
            # latent pressure. This approximates the Gwent-like pass decision.
            score += (
                10.0
                + 0.65 * total_margin
                + 0.9 * weakest_control
                + 0.8 * own_hand
                - 1.6 * opponent_hand
            )
        elif controls == 1 and tied >= 1 and total_margin >= 0:
            score -= 7.0 + 1.2 * opponent_hand
        else:
            score -= 25.0 + 1.5 * opponent_hand

        # Passing first wins a completely tied Battle under the current rules,
        # so do not treat a true zero board as catastrophically bad.
        if all(margin == 0 for margin in margins):
            score += 5.0

        return score

    def _state_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        opponent = 1 - player

        if state.phase is Phase.COMPLETE:
            if state.winner == player:
                return 10_000.0
            return -10_000.0

        victory_delta = (
            state.players[player].victories
            - state.players[opponent].victories
        )
        score = 80.0 * victory_delta

        margins = self._front_margins(engine, state, player)
        control_balance = sum(margin > 0 for margin in margins) - sum(
            margin < 0 for margin in margins
        )
        score += 11.0 * control_balance
        score += 0.85 * sum(max(-12, min(12, margin)) for margin in margins)

        # Hand count is public. The identities of the opponent's cards are not
        # inspected. Own-card option value is handled separately below.
        hand_delta = (
            len(state.players[player].hand)
            - len(state.players[opponent].hand)
        )
        score += 1.25 * hand_delta

        named_subject_delta = self._count_named_subjects(state, player) - self._count_named_subjects(
            state, opponent
        )
        score += 1.5 * named_subject_delta

        scheme_delta = sum(
            state.scheme(player, front) is not None for front in Front
        ) - sum(
            state.scheme(opponent, front) is not None for front in Front
        )
        score += 0.75 * scheme_delta

        stratagem_delta = int(state.stratagem(player) is not None) - int(
            state.stratagem(opponent) is not None
        )
        score += 0.45 * stratagem_delta

        # Open Links are valued using only the acting player's own hand. The
        # value is derived from the engine's real Strength calculation rather
        # than duplicated card fields, so balance changes remain consistent.
        score += self._own_name_option_value(engine, state, player)

        if state.players[player].passed and state.phase is Phase.BATTLE:
            score -= 2.0

        return score

    def _front_margins(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> list[int]:
        opponent = 1 - player
        return [
            engine.front_strength(state, player, front)
            - engine.front_strength(state, opponent, front)
            for front in Front
        ]

    @staticmethod
    def _count_named_subjects(state: GameState, player: int) -> int:
        return sum(
            state.slot(player, position).name is not None
            for position in all_positions()
        )

    def _own_name_option_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        hand_names = [
            card_id
            for card_id in state.players[player].hand
            if engine.cards[card_id]["type"] == "name"
        ]
        if not hand_names:
            return 0.0

        value = 0.0
        for position in all_positions():
            slot = state.slot(player, position)
            if slot.subject is None or slot.link is None or slot.name is not None:
                continue

            before = engine.position_strength(state, player, position)
            best_gain = -inf
            for name_id in hand_names:
                clone = state.clone()
                clone.slot(player, position).name = name_id
                after = engine.position_strength(clone, player, position)
                best_gain = max(best_gain, float(after - before))

            if best_gain > -inf:
                value += 0.45 * max(0.0, best_gain)

        return value
