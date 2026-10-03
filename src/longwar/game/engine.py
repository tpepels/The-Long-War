from __future__ import annotations

import random
from typing import Any

from ..cards import card_index, compile_card_mechanics, load_card_file, validate_card_data
from ..decks import InvalidDeckDefinition, validate_deck_definition
from ..rules import GameRules
from ..protocol import CardField, Direction, DirectionCode, ObservationZone, PendingResume, PLAYER_COUNT
from ..native_engine import create_fast_engine, create_heuristic_evaluator
from .actions import Action, Cycle, Discard, EffectChoice, Pass, action_from_key, action_key
from .model import (
    ConstraintKind,
    Front,
    GameState,
    ObservationEvent,
    OperationConstraint,
    Phase,
    PlayerState,
    Position,
    Rank,
    FRONT_COUNT,
    POSITIONS_PER_PLAYER,
    RANK_COUNT,
    TOTAL_POSITION_COUNT,
    Slot,
    NarrativeState,
    decode_slot_index,
    other_player,
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
SHUFFLE_SEED_MIX = 0x9E37_79B9


def all_positions() -> tuple[Position, ...]:
    """Stable board-position enumeration used by UI/telemetry helpers."""
    return ALL_POSITIONS


class GameEngine:
    """Python-facing facade over the single canonical Cython game engine.

    Rules and card metadata are configured here, but legality, Strength,
    transitions, card effects, passing, drawing, battle resolution and hidden
    information updates execute only in the canonical native engine backend.

    GameState remains a readable Python view for telemetry, UI adapters,
    belief sampling and tests. It is synchronized from packed Cython state
    after every real transition.
    """

    def __init__(
        self,
        card_data: dict[str, Any],
        *,
        rules: GameRules | None = None,
    ):
        validate_card_data(card_data)
        if rules is None:
            rules = GameRules.standard()

        self.rules = rules
        self.card_data = card_data
        self.cards = card_index(card_data)
        self.card_mechanics = {
            card_id: compile_card_mechanics(card)
            for card_id, card in self.cards.items()
        }

        missing_costs = [
            card_id
            for card_id, card in self.cards.items()
            if not isinstance(card.get(CardField.COMMAND_COST), int)
        ]
        if missing_costs:
            raise ValueError(
                "Every card requires command_cost: "
                + ", ".join(sorted(missing_costs))
            )

        self._native_core_instance = self._build_native_core()
        self._native_heuristic_instance = None
        self._last_command_diagnostics: list[dict[str, Any]] = []

    def __getattr__(self, name: str):
        """Expose GameRules fields without mirroring configuration values."""
        rules = self.__dict__.get("rules")
        if rules is not None and (
            name in GameRules.__dataclass_fields__
            or isinstance(getattr(type(rules), name, None), property)
        ):
            return getattr(rules, name)
        raise AttributeError(name)

    @classmethod
    def from_file(cls, path: str) -> "GameEngine":
        return cls(load_card_file(path))

    def _build_native_core(self):
        return create_fast_engine(self)

    def _native_core(self):
        return self._native_core_instance

    def _native_heuristic(self):
        evaluator = self._native_heuristic_instance
        if evaluator is None:
            evaluator = create_heuristic_evaluator(self._native_core_instance)
            self._native_heuristic_instance = evaluator
        return evaluator

    def command_recovery_for_battle(self, battle: int) -> int:
        """Return the configured base Command recovery for one Battle."""
        return int(self._native_core_instance.command_recovery_for_battle(battle))

    def action_consumes_operation(
        self,
        state: GameState,
        actor: int,
        action: Action,
    ) -> bool:
        """Return whether this transition consumes one of the turn's Actions."""
        if state.phase is not Phase.BATTLE:
            return False
        if state.pending_draw_discard_for is not None:
            return False
        if isinstance(action, (Pass, Discard, EffectChoice)):
            return False
        return isinstance(action, (Cycle,)) or not isinstance(action, (Discard, EffectChoice))

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
            shuffle_seed=(seed ^ SHUFFLE_SEED_MIX) & SHUFFLE_MASK,
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
        for player in range(PLAYER_COUNT):
            hand = [
                decks[player].pop()
                for _ in range(min(self.opening_hand_size, len(decks[player])))
            ]

            indices = mulligan_indices[player]
            if (
                len(indices) > self.rules.mulligan_max_cards
                or len(set(indices)) != len(indices)
            ):
                raise ValueError(
                    "A mulligan may contain at most "
                    f"{self.rules.mulligan_max_cards} distinct hand indices"
                )
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

        active_player = rng.randrange(PLAYER_COUNT) if first_player is None else first_player
        native = self._native_core_instance
        fast_state = native.from_game_state(state)
        native.initialize_opening_turn(fast_state, active_player, opening_bonus)
        self._sync_from_native(state, fast_state)
        return state

    def _sync_from_native(self, state: GameState, fast_state) -> None:
        data = self._native_core_instance.export_state(fast_state)

        for player in range(PLAYER_COUNT):
            source = data["players"][player]
            target = state.players[player]
            target.deck[:] = source["deck"]
            target.hand[:] = source["hand"]
            target.discard[:] = source["discard"]
            target.passed = bool(source["passed"])
            target.command = int(source["command"])

            for front in range(FRONT_COUNT):
                for rank in range(RANK_COUNT):
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
                    target_slot.maneuvered_in_operation = bool(
                        source_slot.get("maneuvered_in_operation", False)
                    )
                    target_slot.maneuver_direction = source_slot.get(
                        "maneuver_direction"
                    )

            synced_narratives: list[NarrativeState] = []
            for narrative in data["narratives"][player]:
                target_slot = narrative.get("target_slot")
                target_player = None
                target_position = None
                if target_slot is not None:
                    target_player, target_position = decode_slot_index(
                        int(target_slot)
                    )
                synced_narratives.append(
                    NarrativeState(
                        card_id=narrative["card_id"],
                        ongoing=True,
                        fronts=tuple(
                            Front(front)
                            for front in range(FRONT_COUNT)
                            if int(narrative.get("front_mask", 0)) & (1 << front)
                        ),
                        target_player=target_player,
                        target_position=target_position,
                        direction=narrative.get("direction"),
                        triggered_this_battle=bool(
                            narrative.get("triggered_this_battle", False)
                        ),
                        triggered_players_mask=int(
                            narrative.get("triggered_players_mask", 0)
                        ),
                    )
                )
            state.narratives[player][:] = synced_narratives

            stratagem = data["stratagems"][player]
            if stratagem is None:
                state.stratagems[player] = None
            else:
                targets: list[tuple[int, Position]] = []
                target_mask = int(stratagem.get("target_mask", 0))
                for target_slot in range(TOTAL_POSITION_COUNT):
                    if not target_mask & (1 << target_slot):
                        continue
                    targets.append(decode_slot_index(target_slot))
                direction_code = int(stratagem.get("direction", 0))
                state.stratagems[player] = StratagemState(
                    card_id=stratagem["card_id"],
                    fronts=tuple(
                        Front(front)
                        for front in range(FRONT_COUNT)
                        if int(stratagem.get("front_mask", 0)) & (1 << front)
                    ),
                    direction=(
                        Direction.LEFT.value
                        if direction_code == DirectionCode.LEFT
                        else Direction.RIGHT.value
                        if direction_code == DirectionCode.RIGHT
                        else None
                    ),
                    targets=tuple(targets),
                    revealed=bool(stratagem.get("revealed", False)),
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
        state.actions_this_turn = int(data.get("actions_this_turn", 0))
        state.closing_turns_remaining = int(
            data.get("closing_turns_remaining", 0)
        )
        state.maneuvers_this_battle[:] = data.get(
            "maneuvers_this_battle", [0] * PLAYER_COUNT
        )
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
        state.pending_effects[:] = data.get("pending_effects", [])
        pending_resume = data.get("pending_resume")
        state.pending_resume = (
            None if pending_resume is None else PendingResume(pending_resume)
        )
        state.pending_resume_player = data.get("pending_resume_player")
        state.free_maneuver_available[:] = data.get(
            "free_maneuver_available", [False] * PLAYER_COUNT
        )
        state.free_maneuver_source[:] = data.get(
            "free_maneuver_source", [None] * PLAYER_COUNT
        )
        constraints: list[OperationConstraint] = []
        for item in data.get("constraints", []):
            source_slot = item.get("source_slot")
            source_position = None
            if source_slot is not None:
                local = int(source_slot) % POSITIONS_PER_PLAYER
                source_position = Position(
                    Front(local // RANK_COUNT),
                    Rank.FRONT if local % RANK_COUNT == 0 else Rank.REAR,
                )
            front = item.get("front")
            constraints.append(
                OperationConstraint(
                    source_card=str(item["source_card"]),
                    player=int(item["player"]),
                    kind=ConstraintKind(str(item["kind"])),
                    source_owner=int(item["source_owner"]),
                    front=None if front is None else Front(int(front)),
                    direction=item.get("direction"),
                    source_position=source_position,
                    activate_turn=int(item.get("activate_turn", 0)),
                    expires_after_operation=bool(
                        item.get("expires_after_operation", True)
                    ),
                    persists_between_battles=bool(
                        item.get("persists_between_battles", False)
                    ),
                    zero_cost=bool(item.get("zero_cost", False)),
                    draw_after_satisfied=int(
                        item.get("draw_after_satisfied", 0)
                    ),
                    discard_source_narrative=bool(
                        item.get("discard_source_narrative", False)
                    ),
                )
            )
        state.constraints[:] = constraints
        state.battle_resolution = data.get("battle_resolution")
        state.last_battle_snapshot = data["last_battle_snapshot"]
        state.pass_order[:] = data["pass_order"]
        state.winner = data["winner"]
        state.turn_number = int(data["turn_number"])
        state.shuffle_seed = int(data["shuffle_seed"])

        hidden = data["known_hidden_hand"]
        for viewer in range(PLAYER_COUNT):
            for owner in range(PLAYER_COUNT):
                target = state.known_hidden_hand[viewer][owner]
                updated = hidden[viewer][owner]
                for card_id in sorted(target.keys() | updated.keys()):
                    delta = updated.get(card_id, 0) - target.get(card_id, 0)
                    if delta:
                        state.observe_hidden_delta(
                            viewer=viewer,
                            owner=owner,
                            card_id=card_id,
                            zone=ObservationZone.HAND,
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
        self._last_command_diagnostics = list(
            native.apply_with_command_diagnostics(fast_state, candidate)
        )
        self._sync_from_native(state, fast_state)

    def last_command_diagnostics(self) -> tuple[dict[str, Any], ...]:
        """Command economy events emitted by the last real transition."""
        return tuple(self._last_command_diagnostics)

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
        opponent = other_player(player)
        return tuple(
            totals[player][front] - totals[opponent][front]
            for front in range(FRONT_COUNT)
        )
