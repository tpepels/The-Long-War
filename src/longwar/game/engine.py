from __future__ import annotations

import random
from typing import Any

from ..cards import card_index, load_card_file, validate_card_data
from ..decks import InvalidDeckDefinition, validate_deck_definition
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
    FRONT_COUNT,
    Slot,
    StoryState,
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
        starting_command: int = 20,
        command_cap: int = 20,
    ):
        validate_card_data(card_data)
        if rules is None:
            rules = GameRules(
                opening_hand_size=opening_hand_size,
                starting_command=starting_command,
                command_cap=command_cap,
            )

        self.rules = rules
        self.card_data = card_data
        self.cards = card_index(card_data)

        self.opening_hand_size = rules.opening_hand_size
        self.starting_command = rules.starting_command
        self.command_cap = rules.command_cap
        self.command_recovery_schedule = rules.command_recovery_schedule
        self.command_collapse_threshold = rules.command_collapse_threshold
        self.maneuver_command_cost = rules.maneuver_command_cost
        self.hand_limit = rules.hand_limit
        self.ongoing_narrative_limit = rules.ongoing_narrative_limit

        missing_costs = [
            card_id
            for card_id, card in self.cards.items()
            if not isinstance(card.get("command_cost"), int)
        ]
        if missing_costs:
            raise ValueError(
                "Every card requires command_cost: "
                + ", ".join(sorted(missing_costs))
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
        """Validate the canonical deck-construction rules."""
        try:
            validate_deck_definition(deck, self.cards)
        except InvalidDeckDefinition as exc:
            raise InvalidDeck(str(exc)) from exc

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
                    command=self.starting_command,
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
                self.starting_command,
                self.starting_command,
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
            target.passed = bool(source["passed"])
            target.command = int(source["command"])

            for front in range(FRONT_COUNT):
                for rank in range(2):
                    source_slot = data["board"][player][front][rank]
                    target_slot = state.board[player][front][rank]
                    target_slot.force = source_slot["force"]
                    target_slot.bond = source_slot["bond"]
                    target_slot.name = source_slot["name"]
                    target_slot.temporary_strength = int(
                        source_slot["temporary_strength"]
                    )
                    target_slot.maneuvers_this_battle = int(
                        source_slot.get("maneuvers_this_battle", 0)
                    )

            synced_stories: list[StoryState] = []
            for story in data["stories"][player]:
                target_slot = story.get("target_slot")
                target_player = None
                target_position = None
                if target_slot is not None:
                    target_player = 0 if target_slot < 8 else 1
                    local = target_slot if target_slot < 8 else target_slot - 8
                    target_position = Position(
                        Front(local // 2),
                        Rank.FRONT if local % 2 == 0 else Rank.REAR,
                    )
                synced_stories.append(
                    StoryState(
                        card_id=story["card_id"],
                        ongoing=True,
                        fronts=tuple(
                            Front(front)
                            for front in range(FRONT_COUNT)
                            if int(story.get("front_mask", 0)) & (1 << front)
                        ),
                        target_player=target_player,
                        target_position=target_position,
                    )
                )
            state.stories[player][:] = synced_stories

            stratagem = data["stratagems"][player]
            if stratagem is None:
                state.stratagems[player] = None
            else:
                targets: list[tuple[int, Position]] = []
                target_mask = int(stratagem.get("target_mask", 0))
                for target_slot in range(16):
                    if not target_mask & (1 << target_slot):
                        continue
                    target_player = 0 if target_slot < 8 else 1
                    local = target_slot if target_slot < 8 else target_slot - 8
                    targets.append(
                        (
                            target_player,
                            Position(
                                Front(local // 2),
                                Rank.FRONT if local % 2 == 0 else Rank.REAR,
                            ),
                        )
                    )
                direction_code = int(stratagem.get("direction", 0))
                state.stratagems[player] = StratagemState(
                    card_id=stratagem["card_id"],
                    fronts=tuple(
                        Front(front)
                        for front in range(FRONT_COUNT)
                        if int(stratagem.get("front_mask", 0)) & (1 << front)
                    ),
                    direction=(
                        "left"
                        if direction_code == 1
                        else "right"
                        if direction_code == 2
                        else None
                    ),
                    targets=tuple(targets),
                )

        state.stratagem_used[:] = data["stratagem_used"]
        state.hero_used[:] = data["hero_used"]
        state.active_player = int(data["active_player"])
        state.battle = int(data["battle"])
        state.phase = Phase(data["phase"])
        state.discarded_this_battle[:] = data["discarded_this_battle"]
        state.command_spent_this_battle[:] = data["command_spent_this_battle"]
        state.command_refunded_this_battle[:] = data["command_refunded_this_battle"]
        state.battle_start_command[:] = data["battle_start_command"]
        state.battle_start_hand_size[:] = data["battle_start_hand_size"]
        state.cards_drawn_this_battle[:] = data["cards_drawn_this_battle"]
        state.completion_count_this_battle[:] = data["completion_count_this_battle"]
        state.operations_this_battle[:] = data["operations_this_battle"]
        state.cards_played_this_turn_front_mask[:] = (
            data["cards_played_this_turn_front_mask"]
        )
        state.cards_played_this_battle_front_mask[:] = (
            data["cards_played_this_battle_front_mask"]
        )
        state.narratives_played_this_battle[:] = (
            data["narratives_played_this_battle"]
        )
        state.deck_reshuffles[:] = data["deck_reshuffles"]
        state.reshuffle_card_totals[:] = data["reshuffle_card_totals"]
        state.reshuffle_hand_card_totals[:] = data["reshuffle_hand_card_totals"]
        state.pending_draw_discard_for = data["pending_draw_discard_for"]
        state.pending_draw_count = int(data["pending_draw_count"])
        state.pending_draw_finish_operation = bool(data["pending_draw_finish_operation"])
        state.last_battle_snapshot = data["last_battle_snapshot"]
        state.pass_order[:] = data["pass_order"]
        state.winner = data["winner"]
        state.turn_number = int(data["turn_number"])
        state.shuffle_seed = int(data["shuffle_seed"])

        hidden = data["known_hidden_hand"]
        for viewer in range(2):
            for owner in range(2):
                target = state.known_hidden_hand[viewer][owner]
                updated = hidden[viewer][owner]
                for card_id in sorted(target.keys() | updated.keys()):
                    delta = updated.get(card_id, 0) - target.get(card_id, 0)
                    if delta:
                        state.observe_hidden_delta(
                            viewer=viewer,
                            owner=owner,
                            card_id=card_id,
                            zone="hand",
                            delta=delta,
                            reason="engine_transition",
                        )
                target.clear()
                target.update(updated)

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
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        candidate = self._native_action(fast_state, action)
        native.apply(fast_state, candidate)
        self._sync_from_native(state, fast_state)

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
        if slot.force is None or slot.name is not None:
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
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        return (
            tuple(
                int(native.front_strength(fast_state, 0, front))
                for front in range(FRONT_COUNT)
            ),
            tuple(
                int(native.front_strength(fast_state, 1, front))
                for front in range(FRONT_COUNT)
            ),
        )

    def front_margins(
        self,
        state: GameState,
        player: int,
    ) -> tuple[int, ...]:
        totals = self.front_strength_matrix(state)
        opponent = 1 - player
        return tuple(
            totals[player][front] - totals[opponent][front]
            for front in range(FRONT_COUNT)
        )
