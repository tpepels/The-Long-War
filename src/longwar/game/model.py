from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, IntEnum


class Front(IntEnum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2


class Rank(str, Enum):
    FRONT = "front"
    REAR = "rear"


class Phase(str, Enum):
    BATTLE = "battle"
    CHOOSE_FIRST = "choose_first"
    COMPLETE = "complete"


RANK_INDEX = {Rank.FRONT: 0, Rank.REAR: 1}


@dataclass(frozen=True, order=True)
class Position:
    front: Front
    rank: Rank


@dataclass
class Slot:
    subject: str | None = None
    link: str | None = None
    name: str | None = None
    temporary_strength: int = 0

    @property
    def occupied(self) -> bool:
        return any(
            component is not None
            for component in (self.subject, self.link, self.name)
        )

    @property
    def complete(self) -> bool:
        return self.subject is not None and self.link is not None and self.name is not None


@dataclass
class SchemeState:
    card_id: str
    revealed: bool = False


@dataclass
class StratagemState:
    card_id: str
    revealed: bool = False


@dataclass
class PlayerState:
    deck: list[str]
    hand: list[str]
    discard: list[str] = field(default_factory=list)
    victories: int = 0
    passed: bool = False
    command: int = 0
    free_cycle: bool = False


@dataclass(frozen=True)
class ObservationEvent:
    turn_number: int
    kind: str
    viewer: int
    owner: int
    card_id: str
    zone: str
    delta: int = 0
    reason: str = ""


def empty_board() -> list[list[list[Slot]]]:
    return [
        [[Slot(), Slot()] for _ in range(3)],
        [[Slot(), Slot()] for _ in range(3)],
    ]


def empty_schemes() -> list[list[SchemeState | None]]:
    return [[None for _ in range(3)] for _ in range(2)]


def empty_stratagems() -> list[StratagemState | None]:
    return [None, None]


@dataclass
class GameState:
    players: list[PlayerState]
    board: list[list[list[Slot]]] = field(default_factory=empty_board)
    schemes: list[list[SchemeState | None]] = field(default_factory=empty_schemes)
    stratagems: list[StratagemState | None] = field(default_factory=empty_stratagems)
    stratagem_used: list[bool] = field(default_factory=lambda: [False, False])
    draw_used: list[bool] = field(default_factory=lambda: [False, False])
    active_player: int = 0
    battle: int = 1
    phase: Phase = Phase.BATTLE
    discarded_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    command_spent_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    command_refunded_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    completion_command_refunded_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    battle_start_command: list[int] = field(default_factory=lambda: [0, 0])
    battle_start_hand_size: list[int] = field(default_factory=lambda: [0, 0])
    cards_drawn_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    completion_count_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    operations_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    deck_reshuffles: list[int] = field(default_factory=lambda: [0, 0])
    reshuffle_card_totals: list[int] = field(default_factory=lambda: [0, 0])
    reshuffle_hand_card_totals: list[int] = field(default_factory=lambda: [0, 0])
    opening_hands: list[list[str]] = field(default_factory=lambda: [[], []])
    pending_final_operation_for: int | None = None
    last_battle_snapshot: dict[str, object] | None = None
    pass_order: list[int] = field(default_factory=list)
    chooser: int | None = None
    winner: int | None = None
    turn_number: int = 1
    shuffle_seed: int = 0
    observations: list[ObservationEvent] = field(default_factory=list)

    def clone(self) -> "GameState":
        """Fast structural copy used heavily by search.

        Card ids, enums and ObservationEvent objects are immutable, so only
        mutable containers and mutable state records need to be copied.
        Avoiding deepcopy here removes a large amount of MCCFR overhead while
        preserving full branch isolation.
        """
        players = [
            PlayerState(
                deck=list(player.deck),
                hand=list(player.hand),
                discard=list(player.discard),
                victories=player.victories,
                passed=player.passed,
                command=player.command,
                free_cycle=player.free_cycle,
            )
            for player in self.players
        ]
        board = [
            [
                [
                    Slot(
                        subject=slot.subject,
                        link=slot.link,
                        name=slot.name,
                        temporary_strength=slot.temporary_strength,
                    )
                    for slot in front
                ]
                for front in side
            ]
            for side in self.board
        ]
        schemes = [
            [
                None
                if scheme is None
                else SchemeState(card_id=scheme.card_id, revealed=scheme.revealed)
                for scheme in side
            ]
            for side in self.schemes
        ]
        stratagems = [
            None
            if stratagem is None
            else StratagemState(
                card_id=stratagem.card_id,
                revealed=stratagem.revealed,
            )
            for stratagem in self.stratagems
        ]
        return GameState(
            players=players,
            board=board,
            schemes=schemes,
            stratagems=stratagems,
            stratagem_used=list(self.stratagem_used),
            draw_used=list(self.draw_used),
            active_player=self.active_player,
            battle=self.battle,
            phase=self.phase,
            discarded_this_battle=list(self.discarded_this_battle),
            command_spent_this_battle=list(self.command_spent_this_battle),
            command_refunded_this_battle=list(self.command_refunded_this_battle),
            completion_command_refunded_this_battle=list(self.completion_command_refunded_this_battle),
            battle_start_command=list(self.battle_start_command),
            battle_start_hand_size=list(self.battle_start_hand_size),
            cards_drawn_this_battle=list(self.cards_drawn_this_battle),
            completion_count_this_battle=list(self.completion_count_this_battle),
            operations_this_battle=list(self.operations_this_battle),
            deck_reshuffles=list(self.deck_reshuffles),
            reshuffle_card_totals=list(self.reshuffle_card_totals),
            reshuffle_hand_card_totals=list(self.reshuffle_hand_card_totals),
            opening_hands=[list(hand) for hand in self.opening_hands],
            pending_final_operation_for=self.pending_final_operation_for,
            last_battle_snapshot=(
                None
                if self.last_battle_snapshot is None
                else dict(self.last_battle_snapshot)
            ),
            pass_order=list(self.pass_order),
            chooser=self.chooser,
            winner=self.winner,
            turn_number=self.turn_number,
            shuffle_seed=self.shuffle_seed,
            observations=list(self.observations),
        )

    def copy_from(self, source: "GameState") -> "GameState":
        """Overwrite this state from source while reusing allocated containers.

        MCCFR explores depth-first, so one scratch state per depth is enough.
        Reusing PlayerState, Slot and list objects avoids thousands of small
        allocations without changing branch isolation.
        """
        for index in range(2):
            target_player = self.players[index]
            source_player = source.players[index]
            target_player.deck[:] = source_player.deck
            target_player.hand[:] = source_player.hand
            target_player.discard[:] = source_player.discard
            target_player.victories = source_player.victories
            target_player.passed = source_player.passed
            target_player.command = source_player.command
            target_player.free_cycle = source_player.free_cycle

        for player in range(2):
            for front in range(3):
                for rank in range(2):
                    target_slot = self.board[player][front][rank]
                    source_slot = source.board[player][front][rank]
                    target_slot.subject = source_slot.subject
                    target_slot.link = source_slot.link
                    target_slot.name = source_slot.name
                    target_slot.temporary_strength = source_slot.temporary_strength

                source_scheme = source.schemes[player][front]
                target_scheme = self.schemes[player][front]
                if source_scheme is None:
                    self.schemes[player][front] = None
                elif target_scheme is None:
                    self.schemes[player][front] = SchemeState(
                        card_id=source_scheme.card_id,
                        revealed=source_scheme.revealed,
                    )
                else:
                    target_scheme.card_id = source_scheme.card_id
                    target_scheme.revealed = source_scheme.revealed

            source_stratagem = source.stratagems[player]
            target_stratagem = self.stratagems[player]
            if source_stratagem is None:
                self.stratagems[player] = None
            elif target_stratagem is None:
                self.stratagems[player] = StratagemState(
                    card_id=source_stratagem.card_id,
                    revealed=source_stratagem.revealed,
                )
            else:
                target_stratagem.card_id = source_stratagem.card_id
                target_stratagem.revealed = source_stratagem.revealed

        self.stratagem_used[:] = source.stratagem_used
        self.draw_used[:] = source.draw_used
        self.active_player = source.active_player
        self.battle = source.battle
        self.phase = source.phase
        self.discarded_this_battle[:] = source.discarded_this_battle
        self.command_spent_this_battle[:] = source.command_spent_this_battle
        self.command_refunded_this_battle[:] = source.command_refunded_this_battle
        self.completion_command_refunded_this_battle[:] = source.completion_command_refunded_this_battle
        self.battle_start_command[:] = source.battle_start_command
        self.battle_start_hand_size[:] = source.battle_start_hand_size
        self.cards_drawn_this_battle[:] = source.cards_drawn_this_battle
        self.completion_count_this_battle[:] = source.completion_count_this_battle
        self.operations_this_battle[:] = source.operations_this_battle
        self.deck_reshuffles[:] = source.deck_reshuffles
        self.reshuffle_card_totals[:] = source.reshuffle_card_totals
        self.reshuffle_hand_card_totals[:] = source.reshuffle_hand_card_totals
        for index in range(2):
            self.opening_hands[index][:] = source.opening_hands[index]
        self.pending_final_operation_for = source.pending_final_operation_for
        self.last_battle_snapshot = (
            None
            if source.last_battle_snapshot is None
            else dict(source.last_battle_snapshot)
        )
        self.pass_order[:] = source.pass_order
        self.chooser = source.chooser
        self.winner = source.winner
        self.turn_number = source.turn_number
        self.shuffle_seed = source.shuffle_seed
        self.observations[:] = source.observations
        return self

    def slot(self, player: int, position: Position) -> Slot:
        rank_index = 0 if position.rank is Rank.FRONT else 1
        return self.board[player][int(position.front)][rank_index]

    def scheme(self, player: int, front: Front) -> SchemeState | None:
        return self.schemes[player][int(front)]

    def stratagem(self, player: int) -> StratagemState | None:
        return self.stratagems[player]

    def observe_hidden_delta(
        self,
        *,
        viewer: int,
        owner: int,
        card_id: str,
        zone: str,
        delta: int,
        reason: str,
    ) -> None:
        if delta == 0:
            return
        self.observations.append(
            ObservationEvent(
                turn_number=self.turn_number,
                kind="hidden_knowledge",
                viewer=viewer,
                owner=owner,
                card_id=card_id,
                zone=zone,
                delta=delta,
                reason=reason,
            )
        )

    def observe_reveal(
        self,
        *,
        viewer: int,
        owner: int,
        card_id: str,
        zone: str,
        reason: str,
    ) -> None:
        self.observations.append(
            ObservationEvent(
                turn_number=self.turn_number,
                kind="reveal",
                viewer=viewer,
                owner=owner,
                card_id=card_id,
                zone=zone,
                reason=reason,
            )
        )

    def known_hidden_counter(
        self,
        viewer: int,
        owner: int,
        zone: str = "hand",
    ) -> Counter[str]:
        counts: Counter[str] = Counter()
        for event in self.observations:
            if (
                event.kind == "hidden_knowledge"
                and event.viewer == viewer
                and event.owner == owner
                and event.zone == zone
            ):
                counts[event.card_id] += event.delta
                if counts[event.card_id] <= 0:
                    del counts[event.card_id]
        return counts

    def known_hidden_cards(
        self,
        viewer: int,
        owner: int,
        zone: str = "hand",
    ) -> list[str]:
        counts = self.known_hidden_counter(viewer, owner, zone)
        return [
            card_id
            for card_id, count in sorted(counts.items())
            for _ in range(count)
        ]

    def known_hidden_count(
        self,
        viewer: int,
        owner: int,
        card_id: str,
        zone: str = "hand",
    ) -> int:
        return self.known_hidden_counter(viewer, owner, zone).get(card_id, 0)
