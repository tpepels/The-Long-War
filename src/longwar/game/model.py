from __future__ import annotations

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
class PlayerState:
    deck: list[str]
    hand: list[str]
    discard: list[str] = field(default_factory=list)
    victories: int = 0
    passed: bool = False


def empty_board() -> list[list[list[Slot]]]:
    return [
        [[Slot(), Slot()] for _ in range(3)],
        [[Slot(), Slot()] for _ in range(3)],
    ]


def empty_schemes() -> list[list[SchemeState | None]]:
    return [[None for _ in range(3)] for _ in range(2)]


@dataclass
class GameState:
    players: list[PlayerState]
    board: list[list[list[Slot]]] = field(default_factory=empty_board)
    schemes: list[list[SchemeState | None]] = field(default_factory=empty_schemes)
    active_player: int = 0
    battle: int = 1
    phase: Phase = Phase.BATTLE
    discarded_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    pass_order: list[int] = field(default_factory=list)
    chooser: int | None = None
    winner: int | None = None
    turn_number: int = 1

    def clone(self) -> "GameState":
        return deepcopy(self)

    def slot(self, player: int, position: Position) -> Slot:
        return self.board[player][int(position.front)][RANK_INDEX[position.rank]]

    def scheme(self, player: int, front: Front) -> SchemeState | None:
        return self.schemes[player][int(front)]
