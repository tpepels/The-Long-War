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
        engine.apply(clone, action, validate=False)
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
            # Add a public-information estimate so different Stratagems are
            # not treated as arbitrary ties.
            score += 1.35 + self._stratagem_option_value(
                engine,
                state,
                player,
                action.card_id,
            )

        return score

    def _score_pass(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        clone = state.clone()
        engine.apply(clone, Pass(), validate=False)

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
        own_controls = sum(margin > 0 for margin in margins)
        enemy_controls = sum(margin < 0 for margin in margins)
        control_balance = own_controls - enemy_controls

        # The objective is nonlinear: the second controlled Front is much
        # more valuable than adding still more Strength to a Front already
        # won. Keep raw margins deliberately saturated to discourage overkill.
        score += 10.0 * control_balance
        if own_controls >= 2:
            score += 14.0
        if enemy_controls >= 2:
            score -= 14.0
        score += 0.75 * sum(max(-10, min(10, margin)) for margin in margins)

        # Reward efficient coverage of close Fronts. A one-point lead is
        # strategically meaningful; the twentieth point of overkill is not.
        score += 1.25 * sum(
            1.0 if 0 < margin <= 3 else -1.0 if -3 <= margin < 0 else 0.0
            for margin in margins
        )

        # Hand count is public. The identities of the opponent's cards are not
        # inspected. Own-card option value is handled separately below.
        hand_delta = (
            len(state.players[player].hand)
            - len(state.players[opponent].hand)
        )
        score += 1.25 * hand_delta

        if state.phase is Phase.BATTLE:
            own_passed = state.players[player].passed
            opponent_passed = state.players[opponent].passed
            if own_passed != opponent_passed:
                if own_passed:
                    # Once we have Passed, close leads are exposed because the
                    # opponent can spend cards without another reply from us.
                    exposed_leads = sum(0 < margin <= 4 for margin in margins)
                    score -= (
                        1.5
                        + min(7.0, 0.55 * len(state.players[opponent].hand))
                        + 1.1 * exposed_leads
                    )
                else:
                    # If the opponent has Passed, we own all remaining tempo.
                    # Reward realistic catch-up opportunities, but not a huge
                    # hand when every Front is already far out of reach.
                    reachable_fronts = sum(-4 <= margin <= 0 for margin in margins)
                    score += (
                        1.0
                        + min(5.0, 0.4 * len(state.players[player].hand))
                        + 0.9 * reachable_fronts
                    )

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
        return list(engine.front_margins(state, player))

    @staticmethod
    def _count_named_subjects(state: GameState, player: int) -> int:
        return sum(
            state.slot(player, position).name is not None
            for position in all_positions()
        )

    def _stratagem_option_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
        card_id: str,
    ) -> float:
        """Estimate a hidden Stratagem using only information the player knows.

        The estimate is intentionally modest because the trigger may never
        occur. It mainly breaks obviously bad ties between Stratagem choices.
        """
        card = engine.cards[card_id]
        rules = card.get("rules", {}).get("stratagem", {})
        trigger = rules.get("trigger", {})
        continuous = rules.get("continuous", {})
        opponent = 1 - player
        value = 0.0

        role_modifiers = continuous.get("role_strength_modifiers", {})
        rank_modifiers = continuous.get("rank_strength_modifiers", {})
        controller_rank = continuous.get(
            "controller_rank_strength_modifiers",
            {},
        )

        for owner in (player, opponent):
            sign = 1.0 if owner == player else -1.0
            for position in all_positions():
                slot = state.slot(owner, position)
                if slot.subject is None:
                    continue
                subject = engine.cards[slot.subject]
                role = subject.get("role")
                value += 0.35 * sign * float(role_modifiers.get(role, 0))
                value += 0.35 * sign * float(
                    rank_modifiers.get(position.rank.value, 0)
                )
                if owner == player:
                    value += 0.35 * float(
                        controller_rank.get(position.rank.value, 0)
                    )
                if slot.name is not None:
                    value += 0.35 * sign * float(
                        continuous.get("named_subject_modifier", 0)
                    )
                else:
                    value += 0.35 * sign * float(
                        continuous.get("unnamed_subject_modifier", 0)
                    )

        if continuous.get("disable_line_defense"):
            own_front = sum(
                state.slot(player, position).subject is not None
                for position in all_positions()
                if position.rank.value == "front"
            )
            enemy_front = sum(
                state.slot(opponent, position).subject is not None
                for position in all_positions()
                if position.rank.value == "front"
            )
            value += 0.35 * float(enemy_front - own_front)

        event = trigger.get("event")
        actor = trigger.get("actor")
        roles = set(trigger.get("roles", ()))
        ranks = set(trigger.get("ranks", ()))

        # Own hand identities are available to the acting player and provide
        # a small estimate of whether we can cause a symmetric trigger.
        if event == "subject_played" and actor == "either":
            matching = 0
            for held_id in state.players[player].hand:
                held = engine.cards[held_id]
                if held.get("type") != "subject":
                    continue
                if roles and held.get("role") not in roles:
                    continue
                placement_rank = held.get("rules", {}).get("placement", {}).get("rank")
                if ranks and placement_rank is not None and placement_rank not in ranks:
                    continue
                matching += 1
            value += min(0.9, 0.3 * matching)

        reveal = rules.get("reveal_effect", {})
        if reveal.get("effect") == "penalize_trigger_subject":
            value += 0.55
        if reveal.get("cancel_story"):
            own_immediate_stories = sum(
                engine.cards[held_id].get("type") == "plot"
                and not engine.cards[held_id].get("veiled", False)
                for held_id in state.players[player].hand
            )
            # Cancellation is useful, but the continuing self-lock is costly
            # when our own hand contains immediate Stories.
            value += 0.75 - 0.35 * own_immediate_stories

        # Opponent hand identity is never inspected. A larger public hand only
        # raises the generic chance that an opponent-triggered condition fires.
        if actor == "opponent":
            value += min(0.45, 0.05 * len(state.players[opponent].hand))

        return value

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
            original_name = slot.name
            try:
                for name_id in hand_names:
                    # Evaluation is read-only from the caller's perspective.
                    # Temporarily attaching a Name avoids a full GameState
                    # clone for every candidate at every MCCFR leaf.
                    slot.name = name_id
                    after = engine.position_strength(state, player, position)
                    best_gain = max(best_gain, float(after - before))
            finally:
                slot.name = original_name

            if best_gain > -inf:
                value += 0.45 * max(0.0, best_gain)

        return value
