from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TypeAlias

from .model import Front, Position, Rank


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
class Cycle:
    card_id: str


@dataclass(frozen=True)
class Discard:
    card_id: str


@dataclass(frozen=True)
class Pass:
    pass


@dataclass(frozen=True)
class ChooseFirst:
    player: int


Action: TypeAlias = PlaySubject | PlayLink | PlayName | PlayPlot | PlayScheme | SetStratagem | Draw | Cycle | Discard | Pass | ChooseFirst


@lru_cache(maxsize=8192)
def action_key(action: Action) -> str:
    """Stable action serialization shared by engines, UIs and algorithms."""
    if isinstance(action, Pass):
        return "pass"
    if isinstance(action, Draw):
        return "draw"
    if isinstance(action, ChooseFirst):
        return f"choose_first:{action.player}"
    if isinstance(action, PlaySubject):
        return (
            f"subject:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}"
        )
    if isinstance(action, PlayLink):
        return (
            f"link:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}"
        )
    if isinstance(action, PlayName):
        move = "stay"
        if action.move_to is not None:
            move = (
                f"{int(action.move_to.front)}:"
                f"{action.move_to.rank.value}"
            )
        return (
            f"name:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}:{move}"
        )
    if isinstance(action, PlayScheme):
        return f"scheme:{action.card_id}:{int(action.front)}"
    if isinstance(action, SetStratagem):
        return f"stratagem:{action.card_id}"
    if isinstance(action, PlayPlot):
        targets = ";".join(
            f"{target.player}:{int(target.position.front)}:"
            f"{target.position.rank.value}"
            for target in action.targets
        )
        return f"plot:{action.card_id}:{targets}"
    if isinstance(action, Cycle):
        return f"cycle:{action.card_id}"
    if isinstance(action, Discard):
        return f"discard:{action.card_id}"
    raise TypeError(f"Unsupported action type: {type(action)!r}")


def action_from_key(key: str) -> Action:
    """Inverse of :func:`action_key` for engine/API boundaries."""
    if key == "pass":
        return Pass()
    if key == "draw":
        return Draw()
    if key.startswith("cycle:"):
        return Cycle(key.split(":", 1)[1])
    if key.startswith("discard:"):
        return Discard(key.split(":", 1)[1])
    if key.startswith("choose_first:"):
        return ChooseFirst(int(key.split(":", 1)[1]))

    kind, card_id, *parts = key.split(":")
    if kind in {"subject", "link"}:
        front = Front(int(parts[0]))
        rank = Rank(parts[1])
        position = Position(front, rank)
        return (
            PlaySubject(card_id, position)
            if kind == "subject"
            else PlayLink(card_id, position)
        )
    if kind == "name":
        front = Front(int(parts[0]))
        rank = Rank(parts[1])
        position = Position(front, rank)
        if parts[2] == "stay":
            return PlayName(card_id, position, None)
        move_to = Position(Front(int(parts[2])), Rank(parts[3]))
        return PlayName(card_id, position, move_to)
    if kind == "scheme":
        return PlayScheme(card_id, Front(int(parts[0])))
    if kind == "stratagem":
        return SetStratagem(card_id)
    if kind == "plot":
        target_blob = ":".join(parts)
        if not target_blob:
            return PlayPlot(card_id, ())
        targets = []
        for encoded in target_blob.split(";"):
            player, front, rank = encoded.split(":")
            targets.append(
                BoardTarget(
                    int(player),
                    Position(Front(int(front)), Rank(rank)),
                )
            )
        return PlayPlot(card_id, tuple(targets))
    raise ValueError(f"Unknown action key: {key}")
