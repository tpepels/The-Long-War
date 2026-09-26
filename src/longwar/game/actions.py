from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TypeAlias

from .model import Position, Rank


@dataclass(frozen=True)
class BoardTarget:
    player: int
    position: Position


@dataclass(frozen=True)
class PlayForce:
    card_id: str
    position: Position


@dataclass(frozen=True)
class PlayBond:
    card_id: str
    position: Position


@dataclass(frozen=True)
class PlayName:
    card_id: str
    position: Position


@dataclass(frozen=True)
class PlayStory:
    card_id: str
    targets: tuple[BoardTarget, ...] = ()
    ongoing_slot: int | None = None


@dataclass(frozen=True)
class PlayStratagem:
    card_id: str


@dataclass(frozen=True)
class Maneuver:
    source: Position
    destination: Position


@dataclass(frozen=True)
class Discard:
    card_id: str


@dataclass(frozen=True)
class Pass:
    pass


@dataclass(frozen=True)
class Draw:
    """Obsolete compatibility type; never legal in canonical rules."""


@dataclass(frozen=True)
class Cycle:
    """Obsolete compatibility type; never legal in canonical rules."""
    card_id: str


Action: TypeAlias = (
    PlayForce
    | PlayBond
    | PlayName
    | PlayStory
    | PlayStratagem
    | Maneuver
    | Discard
    | Pass
)


@lru_cache(maxsize=8192)
def action_key(action: object) -> str:
    """Stable canonical action serialization shared by engine, UI and AI."""
    if isinstance(action, Pass):
        return "pass"
    if isinstance(action, Discard):
        return f"discard:{action.card_id}"
    if isinstance(action, Maneuver):
        return (
            f"maneuver:{int(action.source.front)}:{action.source.rank.value}:"
            f"{int(action.destination.front)}:{action.destination.rank.value}"
        )
    if isinstance(action, PlayForce):
        return (
            f"force:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}"
        )
    if isinstance(action, PlayBond):
        return (
            f"bond:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}"
        )
    if isinstance(action, PlayName):
        return (
            f"name:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}"
        )
    if isinstance(action, PlayStory):
        if action.ongoing_slot is not None:
            return f"story:{action.card_id}:ongoing:{action.ongoing_slot}"
        targets = ";".join(
            f"{target.player}:{int(target.position.front)}:"
            f"{target.position.rank.value}"
            for target in action.targets
        )
        return f"story:{action.card_id}:{targets}"
    if isinstance(action, PlayStratagem):
        return f"stratagem:{action.card_id}"

    # Serialized compatibility only. These are never returned by legal_actions.
    if isinstance(action, Draw):
        return "draw"
    if isinstance(action, Cycle):
        return f"cycle:{action.card_id}"
    raise TypeError(f"Unsupported action type: {type(action)!r}")


def _position(front: str, rank: str) -> Position:
    return Position(Front(int(front)), Rank(rank))


def action_from_key(key: str) -> object:
    """Inverse of the canonical action-key format."""
    if key == "pass":
        return Pass()
    if key == "draw":
        return Draw()
    if key.startswith("cycle:"):
        return Cycle(key.split(":", 1)[1])
    if key.startswith("discard:"):
        return Discard(key.split(":", 1)[1])

    parts = key.split(":")
    if parts[0] == "force":
        return PlayForce(parts[1], _position(parts[2], parts[3]))
    if parts[0] == "bond":
        return PlayBond(parts[1], _position(parts[2], parts[3]))
    if parts[0] == "name":
        return PlayName(parts[1], _position(parts[2], parts[3]))
    if parts[0] == "maneuver":
        return Maneuver(
            _position(parts[1], parts[2]),
            _position(parts[3], parts[4]),
        )
    if parts[0] == "stratagem":
        return PlayStratagem(parts[1])
    if parts[0] == "story":
        card_id = parts[1]
        if len(parts) >= 4 and parts[2] == "ongoing":
            return PlayStory(card_id, ongoing_slot=int(parts[3]))
        payload = ":".join(parts[2:])
        targets: list[BoardTarget] = []
        if payload:
            for encoded in payload.split(";"):
                player, front, rank = encoded.split(":")
                targets.append(
                    BoardTarget(int(player), _position(front, rank))
                )
        return PlayStory(card_id, tuple(targets))
    raise ValueError(f"Unknown action key: {key}")
