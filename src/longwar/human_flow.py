from __future__ import annotations

from collections import Counter
from typing import Any

from .game.actions import Action, Discard, Pass, PlayForce
from .game.engine import GameEngine
from .game.model import Front, GameState, Phase
from .protocol import CardField, CardType, DesignField, PLAYER_COUNT


class HumanFlowDiagnostics:
    """Human-facing diagnostics for structural rules experiments."""

    def __init__(self) -> None:
        self.opening_force_distribution: Counter[int] = Counter()
        self.opening_role_counts: Counter[str] = Counter()
        self.opening_rank_counts: Counter[str] = Counter()
        self.opening_players = 0
        self.opening_force_total = 0

        self.decisions = 0
        self.force_hand_total = 0
        self.hand_size_total = 0
        self.no_playable_force_decisions = 0
        self._no_force_streak = [0] * PLAYER_COUNT
        self.longest_no_force_streak = 0
        self.first_force_operations: list[int] = []
        self._first_force_seen = [False] * PLAYER_COUNT

        self.battles = 0
        self.player_battles = 0
        self.cards_drawn_total = 0
        self.deck_seen_fraction_total = 0.0
        self.completion_events_total = 0
        self.command_spent_total = 0
        self._current_deck_sizes = [1, 1]

        self.pass_events = 0
        self.first_signal_events = 0
        self.early_first_signal_events = 0
        self.signal_hand_total = 0
        self.signal_operations_total = 0

        self.pre_draw_discards = 0

        self.reshuffles = 0
        self.reshuffled_cards_total = 0
        self.reshuffle_hand_cards_total = 0

    def merge(self, other: "HumanFlowDiagnostics") -> None:
        """Merge completed-match diagnostics from an independent worker."""
        self.opening_force_distribution.update(other.opening_force_distribution)
        self.opening_role_counts.update(other.opening_role_counts)
        self.opening_rank_counts.update(other.opening_rank_counts)
        self.first_force_operations.extend(other.first_force_operations)
        self.longest_no_force_streak = max(
            self.longest_no_force_streak,
            other.longest_no_force_streak,
        )
        for name in (
            "opening_players", "opening_force_total", "decisions",
            "force_hand_total", "hand_size_total", "no_playable_force_decisions",
            "battles", "player_battles", "cards_drawn_total",
            "deck_seen_fraction_total", "completion_events_total",
            "command_spent_total", "pass_events", "first_signal_events",
            "early_first_signal_events", "signal_hand_total",
            "signal_operations_total", "pre_draw_discards", "reshuffles",
            "reshuffled_cards_total", "reshuffle_hand_cards_total",
        ):
            setattr(self, name, getattr(self, name) + getattr(other, name))

    def start_game(self, engine: GameEngine, state: GameState) -> None:
        self._no_force_streak = [0] * PLAYER_COUNT
        self._first_force_seen = [False] * PLAYER_COUNT
        self._current_deck_sizes = [
            len(player.hand) + len(player.deck) + len(player.discard)
            for player in state.players
        ]
        opening_hands = state.opening_hands
        if not any(opening_hands):
            opening_hands = [
                list(player.hand[: engine.opening_hand_size])
                for player in state.players
            ]

        for hand in opening_hands:
            forces = [
                engine.cards[card_id]
                for card_id in hand
                if engine.cards[card_id][CardField.TYPE] == CardType.FORCE
            ]
            count = len(forces)
            self.opening_players += 1
            self.opening_force_total += count
            self.opening_force_distribution[count] += 1
            for card in forces:
                self.opening_role_counts[str(card.get(CardField.ROLE, "unknown"))] += 1
                design = engine.card_mechanics[card["id"]]
                force_design = design.get(DesignField.FORCE) or design
                rank = force_design.get(DesignField.DEPLOY_RANK) or design.get(DesignField.DEPLOY_RANK)
                self.opening_rank_counts[str(rank or "unrestricted")] += 1

    def before_action(
        self,
        engine: GameEngine,
        state: GameState,
        actor: int,
        action: Action,
    ) -> None:
        if state.phase is not Phase.BATTLE:
            return
        if state.pending_draw_discard_for is not None:
            if isinstance(action, Discard):
                self.pre_draw_discards += 1
            return

        legal = engine.legal_actions(state)
        consumes_operation = engine.action_consumes_operation(
            state,
            actor,
            action,
        )

        if consumes_operation:
            force_count = sum(
                engine.cards[card_id][CardField.TYPE] == CardType.FORCE
                for card_id in state.players[actor].hand
            )
            playable_force = any(
                isinstance(candidate, PlayForce) for candidate in legal
            )
            self.decisions += 1
            self.force_hand_total += force_count
            self.hand_size_total += len(state.players[actor].hand)
            if playable_force:
                self._no_force_streak[actor] = 0
            else:
                self.no_playable_force_decisions += 1
                self._no_force_streak[actor] += 1
                self.longest_no_force_streak = max(
                    self.longest_no_force_streak,
                    self._no_force_streak[actor],
                )

        if isinstance(action, PlayForce) and not self._first_force_seen[actor]:
            self._first_force_seen[actor] = True
            self.first_force_operations.append(
                state.operations_this_battle[actor] + 1
            )

        if (
            isinstance(action, Pass)
            and state.actions_this_turn == 0
            and state.closing_turns_remaining == 0
        ):
            actions_before = state.operations_this_battle[actor]
            self.pass_events += 1
            self.signal_hand_total += len(state.players[actor].hand)
            self.signal_operations_total += actions_before
            # Compatibility counters: every recorded Pass is the sole Battle
            # Pass under the playtest rules.
            self.first_signal_events += 1
            if actions_before <= 1:
                self.early_first_signal_events += 1

    def after_action(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
        actor: int,
        action: Action,
    ) -> None:
        for player in range(PLAYER_COUNT):
            reshuffles = state.deck_reshuffles[player] - before.deck_reshuffles[player]
            if reshuffles <= 0:
                continue
            self.reshuffles += reshuffles
            self.reshuffled_cards_total += (
                state.reshuffle_card_totals[player]
                - before.reshuffle_card_totals[player]
            )
            self.reshuffle_hand_cards_total += (
                state.reshuffle_hand_card_totals[player]
                - before.reshuffle_hand_card_totals[player]
            )

        battle_resolved = (
            before.phase is Phase.BATTLE
            and (
                state.phase is Phase.COMPLETE
                or state.battle != before.battle
            )
        )
        if not battle_resolved:
            return

        snapshot = state.last_battle_snapshot
        if not snapshot or snapshot.get("battle") != before.battle:
            return

        self.battles += 1
        self.player_battles += PLAYER_COUNT
        cards_drawn = [int(value) for value in snapshot["cards_drawn"]]
        start_hands = [int(value) for value in snapshot["battle_start_hand_size"]]
        completion_counts = [int(value) for value in snapshot["completion_count"]]
        command_spent = [int(value) for value in snapshot["command_spent"]]
        self.cards_drawn_total += sum(cards_drawn)
        self.completion_events_total += sum(completion_counts)
        self.command_spent_total += sum(command_spent)
        for player in range(PLAYER_COUNT):
            self.deck_seen_fraction_total += min(
                1.0,
                (start_hands[player] + cards_drawn[player])
                / self._current_deck_sizes[player],
            )

        self._no_force_streak = [0] * PLAYER_COUNT
        self._first_force_seen = [False] * PLAYER_COUNT

    def summary(self) -> dict[str, Any]:
        opening_zero = self.opening_force_distribution.get(0, 0)
        opening_zero_or_one = opening_zero + self.opening_force_distribution.get(1, 0)
        return {
            "opening_players": self.opening_players,
            "opening_force_distribution": {
                str(key): value
                for key, value in sorted(self.opening_force_distribution.items())
            },
            "opening_force_role_counts": dict(sorted(self.opening_role_counts.items())),
            "opening_force_rank_counts": dict(sorted(self.opening_rank_counts.items())),
            "opening_zero_force_rate": self._ratio(opening_zero, self.opening_players),
            "opening_zero_or_one_force_rate": self._ratio(
                opening_zero_or_one,
                self.opening_players,
            ),
            "mean_opening_forces": self._ratio(
                self.opening_force_total,
                self.opening_players,
            ),
            "decisions": self.decisions,
            "mean_forces_in_hand": self._ratio(
                self.force_hand_total,
                self.decisions,
            ),
            "mean_hand_size_during_battle": self._ratio(
                self.hand_size_total,
                self.decisions,
            ),
            "no_playable_force_decision_rate": self._ratio(
                self.no_playable_force_decisions,
                self.decisions,
            ),
            "longest_no_playable_force_streak": self.longest_no_force_streak,
            "mean_first_force_action": self._ratio(
                sum(self.first_force_operations),
                len(self.first_force_operations),
            ),
            # Compatibility alias for pre-overhaul artifact readers.
            "mean_first_force_operation": self._ratio(
                sum(self.first_force_operations),
                len(self.first_force_operations),
            ),
            "first_force_samples": len(self.first_force_operations),
            "battles": self.battles,
            "player_battles": self.player_battles,
            "mean_cards_drawn_per_player_battle": self._ratio(
                self.cards_drawn_total,
                self.player_battles,
            ),
            "mean_deck_seen_fraction_per_player_battle": self._ratio(
                self.deck_seen_fraction_total,
                self.player_battles,
            ),
            "completion_events_per_player_battle": self._ratio(
                self.completion_events_total,
                self.player_battles,
            ),
            "mean_command_spent_per_player_battle": self._ratio(
                self.command_spent_total,
                self.player_battles,
            ),
            "pass_events": self.pass_events,
            "mean_hand_size_at_pass": self._ratio(
                self.signal_hand_total,
                self.pass_events,
            ),
            "mean_actions_before_pass": self._ratio(
                self.signal_operations_total,
                self.pass_events,
            ),
            # Compatibility aliases for historical signal-era artifacts.
            "signal_events": self.pass_events,
            "first_signal_events": self.first_signal_events,
            "early_first_signal_events": self.early_first_signal_events,
            "early_first_signal_rate": self._ratio(
                self.early_first_signal_events,
                self.first_signal_events,
            ),
            "mean_hand_size_at_signal": self._ratio(
                self.signal_hand_total,
                self.pass_events,
            ),
            "mean_operations_before_signal": self._ratio(
                self.signal_operations_total,
                self.pass_events,
            ),
            "pre_draw_discards": self.pre_draw_discards,
            "mean_pre_draw_discards_per_player_battle": self._ratio(
                self.pre_draw_discards,
                self.player_battles,
            ),
            "reshuffles": self.reshuffles,
            "mean_cards_recycled_per_reshuffle": self._ratio(
                self.reshuffled_cards_total,
                self.reshuffles,
            ),
            "mean_hand_cards_when_reshuffling": self._ratio(
                self.reshuffle_hand_cards_total,
                self.reshuffles,
            ),
        }

    @staticmethod
    def _ratio(numerator: float, denominator: float) -> float | None:
        if denominator == 0:
            return None
        return numerator / denominator
