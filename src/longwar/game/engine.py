from __future__ import annotations

import random
from collections import Counter
from typing import Any, Iterable

from ..cards import card_index, load_card_file
from ..rules import GameRules
from .actions import Action, action_from_key, action_key
from .model import (
    Front,
    GameState,
    ObservationEvent,
    Phase,
    PlayerState,
    Position,
    Rank,
    SchemeState,
    Slot,
    StratagemState,
)


class IllegalAction(ValueError):
    pass


class InvalidDeck(ValueError):
    pass


FRONTS = tuple(Front)
FRONTLINE_POSITIONS = tuple(Position(front, Rank.FRONT) for front in FRONTS)
REAR_POSITIONS = tuple(Position(front, Rank.REAR) for front in FRONTS)
POSITIONS_BY_FRONT = tuple(
    (FRONTLINE_POSITIONS[int(front)], REAR_POSITIONS[int(front)])
    for front in FRONTS
)
ALL_POSITIONS = tuple(position for pair in POSITIONS_BY_FRONT for position in pair)
ADJACENT_POSITIONS = {
    position: tuple(
        candidate
        for candidate in (
            (
                Position(Front(int(position.front) - 1), position.rank)
                if int(position.front) > 0
                else None
            ),
            (
                Position(Front(int(position.front) + 1), position.rank)
                if int(position.front) < len(FRONTS) - 1
                else None
            ),
        )
        if candidate is not None
    )
    for position in ALL_POSITIONS
}
SHUFFLE_MASK = 0xFFFF_FFFF


def all_positions() -> tuple[Position, ...]:
    """Stable board-position enumeration used by UI/telemetry helpers."""
    return ALL_POSITIONS


class GameEngine:
    """Python-facing facade over the single canonical Cython game engine.

    Rules and card metadata are configured here, but legality, Strength,
    transitions, card effects, passing, drawing, battle resolution and hidden
    information updates execute only in longwar._fast_search.FastEngine.

    GameState remains a readable Python view for telemetry, UI adapters,
    belief sampling and tests. It is synchronized from packed Cython state
    after every real transition.
    """

    def __init__(
        self,
        card_data: dict[str, Any],
        *,
        rules: GameRules | None = None,
        opening_hand_size: int = 10,
        draw_action_enabled: bool = True,
        completion_draw_names: Iterable[str] = (),
        deck_size: int = 30,
        recycle_between_battles: bool = True,
        command_enabled: bool = False,
        starting_command: int = 20,
        battle_command_gain: int = 10,
        command_cap: int = 20,
        cycle_command_cost: int = 1,
        reshuffle_on_empty: bool = False,
        automatic_draw: bool = False,
        paid_draw_enabled: bool = False,
        paid_draw_command_cost: int = 1,
        paid_draw_consumes_operation: bool = True,
        automatic_draw_hand_limit: int | None = None,
        battle_end_hand_limit: int | None = None,
        cycle_enabled: bool = True,
        pass_final_operation: bool = False,
        pass_requires_both_acted: bool = False,
        first_passer_starts_next_battle: bool = False,
        completion_command_refund: int = 0,
        public_stratagems: bool = False,
    ):
        if rules is None:
            rules = GameRules(
                opening_hand_size=opening_hand_size,
                draw_action_enabled=draw_action_enabled,
                completion_draw_names=tuple(completion_draw_names),
                deck_size=deck_size,
                recycle_between_battles=recycle_between_battles,
                command_enabled=command_enabled,
                starting_command=starting_command,
                battle_command_gain=battle_command_gain,
                command_cap=command_cap,
                cycle_command_cost=cycle_command_cost,
                reshuffle_on_empty=reshuffle_on_empty,
                automatic_draw=automatic_draw,
                paid_draw_enabled=paid_draw_enabled,
                paid_draw_command_cost=paid_draw_command_cost,
                paid_draw_consumes_operation=paid_draw_consumes_operation,
                automatic_draw_hand_limit=automatic_draw_hand_limit,
                battle_end_hand_limit=battle_end_hand_limit,
                cycle_enabled=cycle_enabled,
                pass_final_operation=pass_final_operation,
                pass_requires_both_acted=pass_requires_both_acted,
                first_passer_starts_next_battle=first_passer_starts_next_battle,
                completion_command_refund=completion_command_refund,
                public_stratagems=public_stratagems,
            )

        self.rules = rules
        self.card_data = card_data
        self.cards = card_index(card_data)

        self.opening_hand_size = rules.opening_hand_size
        self.draw_action_enabled = rules.draw_action_enabled
        self.completion_draw_names = frozenset(rules.completion_draw_names)
        self.deck_size = rules.deck_size
        self.recycle_between_battles = rules.recycle_between_battles
        self.command_enabled = rules.command_enabled
        self.starting_command = rules.starting_command
        self.battle_command_gain = rules.battle_command_gain
        self.command_cap = rules.command_cap
        self.cycle_command_cost = rules.cycle_command_cost
        self.reshuffle_on_empty = rules.reshuffle_on_empty
        self.automatic_draw = rules.automatic_draw
        self.paid_draw_enabled = rules.paid_draw_enabled
        self.paid_draw_command_cost = rules.paid_draw_command_cost
        self.paid_draw_consumes_operation = rules.paid_draw_consumes_operation
        self.automatic_draw_hand_limit = rules.automatic_draw_hand_limit
        self.battle_end_hand_limit = rules.battle_end_hand_limit
        self.cycle_enabled = rules.cycle_enabled
        self.pass_final_operation = rules.pass_final_operation
        self.pass_requires_both_acted = rules.pass_requires_both_acted
        self.first_passer_starts_next_battle = rules.first_passer_starts_next_battle
        self.completion_command_refund = rules.completion_command_refund
        self.public_stratagems = rules.public_stratagems

        if self.command_enabled:
            missing_costs = [
                card_id
                for card_id, card in self.cards.items()
                if not isinstance(card.get("command_cost"), int)
            ]
            if missing_costs:
                raise ValueError(
                    "Command mode requires command_cost on every card: "
                    + ", ".join(sorted(missing_costs))
                )

        invalid_completion_names = [
            card_id
            for card_id in self.completion_draw_names
            if card_id not in self.cards or self.cards[card_id]["type"] != "name"
        ]
        if invalid_completion_names:
            raise ValueError(
                "completion_draw_names must contain only Name ids: "
                + ", ".join(sorted(invalid_completion_names))
            )

        self._native_core_instance = self._build_native_core()
        self._native_heuristic_instance = None

    @classmethod
    def from_file(cls, path: str) -> "GameEngine":
        return cls(load_card_file(path))

    def _build_native_core(self):
        try:
            from .._fast_search import FastEngine
        except ImportError as exc:
            raise RuntimeError(
                "The canonical Cython game engine is not built. "
                "Run: python -m pip install -e '.[dev]'"
            ) from exc
        return FastEngine(self)

    def _native_core(self):
        return self._native_core_instance

    def _native_heuristic(self):
        evaluator = self._native_heuristic_instance
        if evaluator is None:
            try:
                from .._fast_search import NativeHeuristicEvaluator
            except ImportError as exc:
                raise RuntimeError(
                    "The canonical Cython heuristic evaluator is not built. "
                    "Run: python -m pip install -e '.[dev]'"
                ) from exc
            evaluator = NativeHeuristicEvaluator(self._native_core_instance)
            self._native_heuristic_instance = evaluator
        return evaluator

    def validate_deck(self, deck: list[str]) -> None:
        if len(deck) != self.deck_size:
            raise InvalidDeck(
                f"A deck must contain exactly {self.deck_size} cards, got {len(deck)}"
            )

        counts = Counter(deck)
        hero_count = 0
        for card_id, count in counts.items():
            if card_id not in self.cards:
                raise InvalidDeck(f"Unknown card: {card_id}")
            card = self.cards[card_id]
            maximum = 1 if card["unique"] else 2
            if count > maximum:
                raise InvalidDeck(
                    f"{card['title']} appears {count} times; maximum is {maximum}"
                )
            if card.get("hero", False):
                hero_count += count

        if hero_count != 1:
            raise InvalidDeck(
                f"A deck must contain exactly one Hero, got {hero_count}"
            )

    def new_game(
        self,
        deck_a: list[str],
        deck_b: list[str],
        *,
        seed: int = 0,
        first_player: int | None = None,
        mulligan_indices: tuple[tuple[int, ...], tuple[int, ...]] = ((), ()),
        opening_bonus: bool = True,
    ) -> GameState:
        self.validate_deck(deck_a)
        self.validate_deck(deck_b)
        return self._new_game_with_rng(
            deck_a,
            deck_b,
            rng=random.Random(seed),
            shuffle_seed=(seed ^ 0x9E37_79B9) & SHUFFLE_MASK,
            first_player=first_player,
            mulligan_indices=mulligan_indices,
            opening_bonus=opening_bonus,
        )

    def _new_game_with_rng(
        self,
        deck_a: list[str],
        deck_b: list[str],
        *,
        rng: random.Random,
        shuffle_seed: int | None = None,
        first_player: int | None = None,
        mulligan_indices: tuple[tuple[int, ...], tuple[int, ...]] = ((), ()),
        opening_bonus: bool = True,
    ) -> GameState:
        """Shuffle/deal the initial view; opening-turn semantics run in Cython."""
        decks = [list(deck_a), list(deck_b)]
        rng.shuffle(decks[0])
        rng.shuffle(decks[1])

        players: list[PlayerState] = []
        for player in range(2):
            hand = [
                decks[player].pop()
                for _ in range(min(self.opening_hand_size, len(decks[player])))
            ]

            indices = mulligan_indices[player]
            if len(indices) > 2 or len(set(indices)) != len(indices):
                raise ValueError("A mulligan may contain at most two distinct hand indices")
            if any(index < 0 or index >= len(hand) for index in indices):
                raise ValueError("Mulligan index outside opening hand")

            returned = [hand[index] for index in sorted(indices)]
            for index in sorted(indices, reverse=True):
                del hand[index]
            if returned:
                decks[player].extend(returned)
                rng.shuffle(decks[player])
                hand.extend(
                    decks[player].pop()
                    for _ in range(min(len(returned), len(decks[player])))
                )

            players.append(
                PlayerState(
                    deck=decks[player],
                    hand=hand,
                    command=self.starting_command if self.command_enabled else 0,
                )
            )

        state = GameState(
            players=players,
            shuffle_seed=(
                int(shuffle_seed)
                if shuffle_seed is not None
                else rng.randrange(0x1_0000_0000)
            ),
            battle_start_command=[
                self.starting_command if self.command_enabled else 0,
                self.starting_command if self.command_enabled else 0,
            ],
        )
        state.opening_hands = [
            list(state.players[0].hand),
            list(state.players[1].hand),
        ]
        state.battle_start_hand_size = [
            len(state.players[0].hand),
            len(state.players[1].hand),
        ]

        active_player = rng.randrange(2) if first_player is None else first_player
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        native.initialize_opening_turn(fast_state, active_player, opening_bonus)
        self._sync_from_native(state, fast_state)
        return state

    def _sync_from_native(self, state: GameState, fast_state) -> None:
        data = self._native_core_instance.export_state(fast_state)

        for player in range(2):
            source = data["players"][player]
            target = state.players[player]
            target.deck[:] = source["deck"]
            target.hand[:] = source["hand"]
            target.discard[:] = source["discard"]
            target.victories = int(source["victories"])
            target.passed = bool(source["passed"])
            target.command = int(source["command"])
            target.free_cycle = bool(source["free_cycle"])

            for front in range(3):
                for rank in range(2):
                    source_slot = data["board"][player][front][rank]
                    target_slot = state.board[player][front][rank]
                    target_slot.subject = source_slot["subject"]
                    target_slot.link = source_slot["link"]
                    target_slot.name = source_slot["name"]
                    target_slot.temporary_strength = int(source_slot["temporary_strength"])

                scheme = data["schemes"][player][front]
                state.schemes[player][front] = (
                    None
                    if scheme is None
                    else SchemeState(
                        card_id=scheme["card_id"],
                        revealed=bool(scheme["revealed"]),
                    )
                )

            stratagem = data["stratagems"][player]
            state.stratagems[player] = (
                None
                if stratagem is None
                else StratagemState(
                    card_id=stratagem["card_id"],
                    revealed=bool(stratagem["revealed"]),
                )
            )

        state.stratagem_used[:] = data["stratagem_used"]
        state.draw_used[:] = data["draw_used"]
        state.active_player = int(data["active_player"])
        state.battle = int(data["battle"])
        state.phase = Phase(data["phase"])
        state.discarded_this_battle[:] = data["discarded_this_battle"]
        state.command_spent_this_battle[:] = data["command_spent_this_battle"]
        state.command_refunded_this_battle[:] = data["command_refunded_this_battle"]
        state.completion_command_refunded_this_battle[:] = data[
            "completion_command_refunded_this_battle"
        ]
        state.battle_start_command[:] = data["battle_start_command"]
        state.battle_start_hand_size[:] = data["battle_start_hand_size"]
        state.cards_drawn_this_battle[:] = data["cards_drawn_this_battle"]
        state.completion_count_this_battle[:] = data["completion_count_this_battle"]
        state.operations_this_battle[:] = data["operations_this_battle"]
        state.deck_reshuffles[:] = data["deck_reshuffles"]
        state.reshuffle_card_totals[:] = data["reshuffle_card_totals"]
        state.reshuffle_hand_card_totals[:] = data["reshuffle_hand_card_totals"]
        state.pending_final_operation_for = data["pending_final_operation_for"]
        state.cleanup_pending = bool(data["cleanup_pending"])
        state.cleanup_next_starter = data["cleanup_next_starter"]
        state.cleanup_next_chooser = data["cleanup_next_chooser"]
        state.last_battle_snapshot = data["last_battle_snapshot"]
        state.pass_order[:] = data["pass_order"]
        state.chooser = data["chooser"]
        state.winner = data["winner"]
        state.turn_number = int(data["turn_number"])
        state.shuffle_seed = int(data["shuffle_seed"])

        hidden = data["known_hidden_hand"]
        for viewer in range(2):
            for owner in range(2):
                target = state.known_hidden_hand[viewer][owner]
                target.clear()
                target.update(hidden[viewer][owner])

    def _native_action(self, fast_state, action: Action):
        target = action_key(action)
        native = self._native_core_instance
        for candidate in native.legal_actions(fast_state):
            if native.action_key(candidate) == target:
                return candidate
        raise IllegalAction(f"Illegal action: {action!r}")

    def legal_actions(self, state: GameState) -> list[Action]:
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        return [
            action_from_key(native.action_key(candidate))
            for candidate in native.legal_actions(fast_state)
        ]

    def command_cost_for_action(self, state: GameState, action: Action) -> int:
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        candidate = self._native_action(fast_state, action)
        return int(native.command_cost(fast_state, candidate))

    def apply(
        self,
        state: GameState,
        action: Action,
        *,
        validate: bool = True,
    ) -> None:
        del validate
        before_battle = state.battle
        hidden_stratagems = [
            (owner, stratagem.card_id)
            for owner, stratagem in enumerate(state.stratagems)
            if stratagem is not None and not stratagem.revealed
        ]

        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        candidate = self._native_action(fast_state, action)
        native.apply(fast_state, candidate)
        self._sync_from_native(state, fast_state)

        # ObservationEvent is a presentation/history adapter, not game state.
        # At Battle resolution the canonical core reveals then clears hidden
        # Stratagems in one transition, so retain that public reveal in the
        # Python log for UI/tests.
        battle_resolved = (
            state.phase is Phase.COMPLETE
            or state.battle != before_battle
        )
        if battle_resolved:
            for owner, card_id in hidden_stratagems:
                state.observations.append(
                    ObservationEvent(
                        turn_number=state.turn_number,
                        kind="reveal",
                        viewer=1 - owner,
                        owner=owner,
                        card_id=card_id,
                        zone="stratagem",
                        reason="battle_end",
                    )
                )

    def can_draw(self, state: GameState, player: int) -> bool:
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        return bool(native.can_draw(fast_state, player))

    def position_strength(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> int:
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        return int(
            native.position_strength(
                fast_state,
                player,
                int(position.front),
                0 if position.rank is Rank.FRONT else 1,
            )
        )

    def name_attachment_strength_gain(
        self,
        state: GameState,
        player: int,
        position: Position,
        name_id: str,
    ) -> int:
        slot = state.slot(player, position)
        if slot.subject is None or slot.name is not None:
            return 0
        before = self.position_strength(state, player, position)
        clone = state.clone()
        clone.slot(player, position).name = name_id
        after = self.position_strength(clone, player, position)
        return after - before

    def front_strength(
        self,
        state: GameState,
        player: int,
        front: Front,
    ) -> int:
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        return int(native.front_strength(fast_state, player, int(front)))

    def front_strength_matrix(
        self,
        state: GameState,
    ) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        return (
            tuple(int(native.front_strength(fast_state, 0, front)) for front in range(3)),
            tuple(int(native.front_strength(fast_state, 1, front)) for front in range(3)),
        )

    def front_margins(
        self,
        state: GameState,
        player: int,
    ) -> tuple[int, int, int]:
        totals = self.front_strength_matrix(state)
        opponent = 1 - player
        return tuple(
            totals[player][front] - totals[opponent][front]
            for front in range(3)
        )
