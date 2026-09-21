from __future__ import annotations

from collections import Counter
from copy import deepcopy
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
        return self.subject is not None

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
    active_player: int = 0
    battle: int = 1
    phase: Phase = Phase.BATTLE
    discarded_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    pass_order: list[int] = field(default_factory=list)
    chooser: int | None = None
    winner: int | None = None
    turn_number: int = 1
    observations: list[ObservationEvent] = field(default_factory=list)

    def clone(self) -> "GameState":
        return deepcopy(self)

    def slot(self, player: int, position: Position) -> Slot:
        return self.board[player][int(position.front)][RANK_INDEX[position.rank]]

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
