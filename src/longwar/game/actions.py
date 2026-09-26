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
    fronts: tuple[Front, ...] = ()


@dataclass(frozen=True)
class PlayStratagem:
    card_id: str
    fronts: tuple[Front, ...] = ()
    direction: str | None = None
    targets: tuple[BoardTarget, ...] = ()


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
            key = f"story:{action.card_id}:ongoing:{action.ongoing_slot}"
            if action.fronts:
                key += ":fronts:" + ",".join(str(int(front)) for front in action.fronts)
            if action.targets:
                key += ":targets:" + ";".join(
                    f"{target.player},{int(target.position.front)},{target.position.rank.value}"
                    for target in action.targets
                )
            return key
        targets = ";".join(
            f"{target.player}:{int(target.position.front)}:"
            f"{target.position.rank.value}"
            for target in action.targets
        )
        return f"story:{action.card_id}:{targets}"
    if isinstance(action, PlayStratagem):
        key = f"stratagem:{action.card_id}"
        if action.fronts:
            key += ":fronts:" + ",".join(str(int(front)) for front in action.fronts)
        if action.direction is not None:
            key += f":direction:{action.direction}"
        if action.targets:
            key += ":targets:" + ";".join(
                f"{target.player},{int(target.position.front)},{target.position.rank.value}"
                for target in action.targets
            )
        return key

    raise TypeError(f"Unsupported action type: {type(action)!r}")


def _position(front: str, rank: str) -> Position:
    return Position(Front(int(front)), Rank(rank))


def action_from_key(key: str) -> object:
    """Inverse of the canonical action-key format."""
    if key == "pass":
        return Pass()
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
        card_id = parts[1]
        fronts: tuple[Front, ...] = ()
        direction: str | None = None
        targets: tuple[BoardTarget, ...] = ()
        index = 2
        while index < len(parts):
            label = parts[index]
            value = parts[index + 1]
            if label == "fronts":
                fronts = tuple(Front(int(front)) for front in value.split(",") if front)
            elif label == "direction":
                if value not in {"left", "right"}:
                    raise ValueError(f"Invalid direction in action key: {value}")
                direction = value
            elif label == "targets":
                parsed: list[BoardTarget] = []
                for encoded in value.split(";"):
                    if not encoded:
                        continue
                    player, front, rank = encoded.split(",")
                    parsed.append(BoardTarget(int(player), _position(front, rank)))
                targets = tuple(parsed)
            else:
                raise ValueError(f"Unknown Stratagem action field: {label}")
            index += 2
        return PlayStratagem(card_id, fronts, direction, targets)
    if parts[0] == "story":
        card_id = parts[1]
        if len(parts) >= 4 and parts[2] == "ongoing":
            slot = int(parts[3])
            fronts: tuple[Front, ...] = ()
            targets: tuple[BoardTarget, ...] = ()
            index = 4
            while index < len(parts):
                label = parts[index]
                value = parts[index + 1]
                if label == "fronts":
                    fronts = tuple(Front(int(front)) for front in value.split(",") if front)
                elif label == "targets":
                    parsed: list[BoardTarget] = []
                    for encoded in value.split(";"):
                        if not encoded:
                            continue
                        player, front, rank = encoded.split(",")
                        parsed.append(BoardTarget(int(player), _position(front, rank)))
                    targets = tuple(parsed)
                else:
                    raise ValueError(f"Unknown Narrative action field: {label}")
                index += 2
            return PlayStory(card_id, targets=targets, ongoing_slot=slot, fronts=fronts)
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
