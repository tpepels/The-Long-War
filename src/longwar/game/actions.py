from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from .model import Front, Position


@dataclass(frozen=True)
class BoardTarget:
    player: int
    position: Position


@dataclass(frozen=True)
class PlaySubject:
    card_id: str
    position: Position


@dataclass(frozen=True)
class PlayLink:
    card_id: str
    position: Position


@dataclass(frozen=True)
class PlayName:
    card_id: str
    position: Position
    move_to: Position | None = None


@dataclass(frozen=True)
class PlayPlot:
    card_id: str
    targets: tuple[BoardTarget, ...] = ()


@dataclass(frozen=True)
class PlayScheme:
    card_id: str
    front: Front


@dataclass(frozen=True)
class SetStratagem:
    card_id: str


@dataclass(frozen=True)
class Draw:
    pass


@dataclass(frozen=True)
class Pass:
    pass


@dataclass(frozen=True)
class ChooseFirst:
    player: int


Action: TypeAlias = PlaySubject | PlayLink | PlayName | PlayPlot | PlayScheme | SetStratagem | Draw | Pass | ChooseFirst
