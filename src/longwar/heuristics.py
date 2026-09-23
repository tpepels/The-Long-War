from __future__ import annotations

from math import inf

from .game.actions import (
    Action,
    ChooseFirst,
    Cycle,
    Draw,
    Pass,
    PlayLink,
    PlayName,
    PlayScheme,
    SetStratagem,
)
from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState, Phase


def opening_mulligan_indices(
    engine: GameEngine,
    hand: list[str],
    *,
    maximum: int = 2,
) -> tuple[int, ...]:
    """Choose weak opening cards using only the player's own hand.

    The score is about opening flexibility, not raw card power. Formation
    components can be prepared in any order, so Bonds and Names are no longer
    penalized for lacking an earlier component in the opening hand.
    """
    if maximum <= 0 or not hand:
        return ()

    types = [engine.cards[card_id]["type"] for card_id in hand]
    stratagem_count = types.count("stratagem")

    scored: list[tuple[float, int]] = []
    seen_stratagems = 0
    for index, card_id in enumerate(hand):
        card = engine.cards[card_id]
        card_type = card["type"]

        if card_type == "subject":
            score = 5.0 + 0.08 * float(card.get("strength", 0))
        elif card_type == "link":
            score = 3.2
        elif card_type == "name":
            score = 3.0
        elif card_type == "plot":
            score = 3.7 if card.get("veiled", False) else 2.6
        elif card_type == "stratagem":
            seen_stratagems += 1
            score = 3.2 if seen_stratagems == 1 else 2.0
            if stratagem_count >= 3:
                score -= 0.35
        else:
            score = 2.5
        scored.append((score, index))

    scored.sort(key=lambda item: (item[0], item[1]))
    return tuple(sorted(index for _, index in scored[:maximum]))


class HeuristicEvaluator:
    """Pure valuation policy.

    This layer may inspect state and card metadata, and it may ask the engine
    to evaluate hypothetical actions. It does not choose actions, manage
    randomness, sample beliefs, or implement search.
    """

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

        if isinstance(action, Draw):
            # Paid Draw is chiefly a recovery operation. Command cost is
            # already reflected in the cloned state.
            force_count = sum(
                engine.cards[card_id]["type"] == "subject"
                for card_id in state.players[player].hand
            )
            score -= 0.35 if engine.paid_draw_enabled else 0.8
            if force_count == 0:
                score += 1.4

        if isinstance(action, Cycle):
            # Cycle is deliberately useful only when it improves the actual
            # construction options in hand; it still spends the turn.
            score += (
                1.15
                * (
                    self._hand_construction_value(engine, clone, player)
                    - self._hand_construction_value(engine, state, player)
                )
                - 0.30
            )

        # The engine state already includes a Link's immediate Strength and a
        # face-down Scheme's Front bonus. Keep only small priors for option
        # value that a one-ply evaluator cannot see directly.
        if isinstance(action, PlayLink):
            slot = state.slot(player, action.position)
            score += 0.10 if slot.subject is not None else 1.35

        if isinstance(action, PlayName):
            slot = state.slot(player, action.position)
            score += 0.35 if slot.subject is not None else 1.50

        if isinstance(action, PlayScheme):
            score += 0.20

        if isinstance(action, SetStratagem):
            # In the legacy rules a Stratagem is a free pre-action deployment;
            # in Command mode it is an ordinary paid operation.
            preserved_action = 0.0 if engine.command_enabled else 1.35
            score += preserved_action + self._stratagem_option_value(
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
        pressure_scale = 0.45 if engine.pass_final_operation else 1.0

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
                - pressure_scale * 1.6 * opponent_hand
            )
        elif controls == 1 and tied >= 1 and total_margin >= 0:
            score -= 7.0 + pressure_scale * 1.2 * opponent_hand
        else:
            score -= 25.0 + pressure_scale * 1.5 * opponent_hand

        if engine.first_passer_starts_next_battle and not state.pass_order:
            score += 1.5

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

        own_forces = sum(
            engine.cards[card_id]["type"] == "subject"
            for card_id in state.players[player].hand
        )
        score += 0.35 * min(3, own_forces)
        if own_forces == 0 and not any(
            state.slot(player, position).subject is not None
            for position in all_positions()
        ):
            score -= 2.0

        if engine.command_enabled:
            command_delta = (
                state.players[player].command
                - state.players[opponent].command
            )
            score += 0.45 * command_delta
            score += 0.35 * (
                int(state.players[player].free_cycle)
                - int(state.players[opponent].free_cycle)
            )

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
            state.slot(player, position).subject is not None
            and state.slot(player, position).name is not None
            for position in all_positions()
        )

    def _hand_construction_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        needs_subject = needs_link = needs_name = False
        for position in all_positions():
            slot = state.slot(player, position)
            needs_subject = needs_subject or (
                slot.subject is None
                and (slot.link is not None or slot.name is not None)
            )
            needs_link = needs_link or (
                slot.link is None
                and (slot.subject is not None or slot.name is not None)
            )
            needs_name = needs_name or (
                slot.name is None
                and (slot.subject is not None or slot.link is not None)
            )

        value = 0.0
        for card_id in state.players[player].hand:
            card_type = engine.cards[card_id]["type"]
            if card_type == "subject":
                value += 0.45 + (0.95 if needs_subject else 0.0)
            elif card_type == "link":
                value += 0.35 + (0.95 if needs_link else 0.0)
            elif card_type == "name":
                value += 0.35 + (1.05 if needs_name else 0.0)
            elif card_type == "plot":
                value += 0.40
            elif card_type == "stratagem":
                value += 0.30
        return value

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

        if continuous.get("global_immediate_story_lock"):
            own_immediate_stories = sum(
                engine.cards[held_id].get("type") == "plot"
                and not engine.cards[held_id].get("veiled", False)
                for held_id in state.players[player].hand
            )
            value += 0.8 - 0.35 * own_immediate_stories

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
            if slot.subject is None or slot.name is not None:
                continue

            best_gain = max(
                float(
                    engine.name_attachment_strength_gain(
                        state,
                        player,
                        position,
                        name_id,
                    )
                )
                for name_id in hand_names
            )
            value += 0.45 * max(0.0, best_gain)

        return value


class StrategicEvaluator(HeuristicEvaluator):
    """Long-horizon additions used by adversarial search."""

    def _strategic_state_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        value = self._state_value(engine, state, player)
        if state.phase is Phase.COMPLETE:
            return value

        opponent = 1 - player

        # Reward progress toward complete formations, including Bonds/Names
        # prepared before their Force. This is where the one-ply evaluator is
        # weakest.
        value += 0.85 * (
            self._formation_progress(state, player)
            - self._formation_progress(state, opponent)
        )
        value += 0.30 * (
            self._hand_construction_value(engine, state, player)
            - self._hand_construction_value(engine, state, opponent)
        )

        if not engine.recycle_between_battles:
            value += 0.18 * (
                len(state.players[player].deck)
                - len(state.players[opponent].deck)
            )
            value += 0.55 * (
                self._future_formation_sets(engine, state, player)
                - self._future_formation_sets(engine, state, opponent)
            )
            value += 0.40 * (
                self._future_force_availability(engine, state, player)
                - self._future_force_availability(engine, state, opponent)
            )

        if engine.command_enabled:
            # Command saved now remains useful in later Battles. The public
            # evaluator already values current Command; this smaller term
            # specifically values future playable-card capacity.
            value += 0.12 * (
                self._affordable_hand_count(engine, state, player)
                - self._affordable_hand_count(engine, state, opponent)
            )

        return value

    @staticmethod
    def _formation_progress(state: GameState, player: int) -> float:
        value = 0.0
        for position in all_positions():
            slot = state.slot(player, position)
            components = sum(
                component is not None
                for component in (slot.subject, slot.link, slot.name)
            )
            if components == 1:
                value += 0.35
            elif components == 2:
                value += 1.35
            elif components == 3:
                value += 2.25
        return value

    @staticmethod
    def _affordable_hand_count(
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> int:
        if not engine.command_enabled:
            return len(state.players[player].hand)
        command = state.players[player].command
        return sum(
            int(engine.cards[card_id].get("command_cost", 0)) <= command
            for card_id in state.players[player].hand
        )

    @staticmethod
    def _future_force_availability(
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        immediate = state.players[player].hand + state.players[player].deck
        discard = state.players[player].discard
        return float(
            sum(engine.cards[card_id]["type"] == "subject" for card_id in immediate)
        ) + 0.35 * float(
            sum(engine.cards[card_id]["type"] == "subject" for card_id in discard)
        )

    @staticmethod
    def _future_formation_sets(
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> int:
        remaining = state.players[player].hand + state.players[player].deck
        counts = {"subject": 0, "link": 0, "name": 0}
        for card_id in remaining:
            card_type = engine.cards[card_id]["type"]
            if card_type in counts:
                counts[card_type] += 1
        return min(counts.values())
