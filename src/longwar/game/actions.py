from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TypeAlias

from ..protocol import ActionKeyToken, ActionKind, DIRECTIONS
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
    move_destination: Position | None = None
    extra_payment: int = 0


@dataclass(frozen=True)
class PlayName:
    card_id: str
    position: Position


@dataclass(frozen=True)
class PlayNarrative:
    card_id: str
    targets: tuple[BoardTarget, ...] = ()
    ongoing_slot: int | None = None
    fronts: tuple[Front, ...] = ()
    discard_card_id: str | None = None
    direction: str | None = None


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
class Cycle:
    first_card_id: str
    second_card_id: str


@dataclass(frozen=True)
class EndTurn:
    pass


@dataclass(frozen=True)
class Discard:
    card_id: str


@dataclass(frozen=True)
class EffectChoice:
    effect: str
    source: BoardTarget | None = None
    destination: BoardTarget | None = None
    card_id: str | None = None
    front: Front | None = None
    skip: bool = False


@dataclass(frozen=True)
class Pass:
    pass


Action: TypeAlias = (
    PlayForce
    | PlayBond
    | PlayName
    | PlayNarrative
    | PlayStratagem
    | Maneuver
    | Cycle
    | EndTurn
    | Discard
    | EffectChoice
    | Pass
)


_ACTION_KIND_BY_TYPE = {
    Pass: ActionKind.PASS,
    EndTurn: ActionKind.END_TURN,
    Cycle: ActionKind.CYCLE,
    Discard: ActionKind.DISCARD,
    EffectChoice: ActionKind.EFFECT_CHOICE,
    Maneuver: ActionKind.MANEUVER,
    PlayForce: ActionKind.PLAY_FORCE,
    PlayBond: ActionKind.PLAY_BOND,
    PlayName: ActionKind.PLAY_NAME,
    PlayNarrative: ActionKind.PLAY_NARRATIVE,
    PlayStratagem: ActionKind.PLAY_STRATAGEM,
}


def action_kind(action: object) -> ActionKind:
    """Stable protocol kind independent of Python class-name introspection."""
    try:
        return _ACTION_KIND_BY_TYPE[type(action)]
    except KeyError as exc:
        raise TypeError(f"Unsupported action type: {type(action)!r}") from exc


@lru_cache(maxsize=8192)
def action_key(action: object) -> str:
    """Stable canonical action serialization shared by engine, UI and AI."""
    if isinstance(action, Pass):
        return ActionKeyToken.PASS.value
    if isinstance(action, EndTurn):
        return ActionKeyToken.END_TURN.value
    if isinstance(action, Cycle):
        cards = sorted((action.first_card_id, action.second_card_id))
        return f"{ActionKeyToken.CYCLE.value}:{cards[0]}:{cards[1]}"
    if isinstance(action, Discard):
        return f"{ActionKeyToken.DISCARD.value}:{action.card_id}"
    if isinstance(action, EffectChoice):
        key = f"{ActionKeyToken.EFFECT.value}:{action.effect}"
        if action.skip:
            return key + f":{ActionKeyToken.SKIP.value}"
        if action.card_id is not None:
            key += f":{ActionKeyToken.CARD.value}:{action.card_id}"
        if action.source is not None:
            key += (
                f":{ActionKeyToken.SOURCE.value}:{action.source.player},"
                f"{int(action.source.position.front)},"
                f"{action.source.position.rank.value}"
            )
        if action.destination is not None:
            key += (
                f":{ActionKeyToken.DESTINATION.value}:{action.destination.player},"
                f"{int(action.destination.position.front)},"
                f"{action.destination.position.rank.value}"
            )
        if action.front is not None:
            key += f":{ActionKeyToken.FRONT.value}:{int(action.front)}"
        return key
    if isinstance(action, Maneuver):
        return (
            f"{ActionKeyToken.MANEUVER.value}:{int(action.source.front)}:{action.source.rank.value}:"
            f"{int(action.destination.front)}:{action.destination.rank.value}"
        )
    if isinstance(action, PlayForce):
        return (
            f"{ActionKeyToken.FORCE.value}:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}"
        )
    if isinstance(action, PlayBond):
        key = (
            f"{ActionKeyToken.BOND.value}:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}"
        )
        if action.move_destination is not None:
            key += (
                f":{ActionKeyToken.MOVE.value}:{int(action.move_destination.front)}:"
                f"{action.move_destination.rank.value}"
            )
        if action.extra_payment:
            key += f":{ActionKeyToken.EXTRA.value}:{action.extra_payment}"
        return key
    if isinstance(action, PlayName):
        return (
            f"{ActionKeyToken.NAME.value}:{action.card_id}:{int(action.position.front)}:"
            f"{action.position.rank.value}"
        )
    if isinstance(action, PlayNarrative):
        if action.ongoing_slot is not None:
            key = f"{ActionKeyToken.NARRATIVE.value}:{action.card_id}:{ActionKeyToken.ONGOING.value}:{action.ongoing_slot}"
            if action.fronts:
                key += f":{ActionKeyToken.FRONTS.value}:" + ",".join(str(int(front)) for front in action.fronts)
            if action.targets:
                key += f":{ActionKeyToken.TARGETS.value}:" + ";".join(
                    f"{target.player},{int(target.position.front)},{target.position.rank.value}"
                    for target in action.targets
                )
            if action.direction is not None:
                key += f":{ActionKeyToken.DIRECTION.value}:{action.direction}"
            return key
        if action.discard_card_id is not None:
            return f"{ActionKeyToken.NARRATIVE.value}:{action.card_id}:{ActionKeyToken.DISCARD_FIELD.value}:{action.discard_card_id}"
        targets = ";".join(
            f"{target.player}:{int(target.position.front)}:"
            f"{target.position.rank.value}"
            for target in action.targets
        )
        return f"{ActionKeyToken.NARRATIVE.value}:{action.card_id}:{targets}"
    if isinstance(action, PlayStratagem):
        key = f"{ActionKeyToken.STRATAGEM.value}:{action.card_id}"
        if action.fronts:
            key += f":{ActionKeyToken.FRONTS.value}:" + ",".join(str(int(front)) for front in action.fronts)
        if action.direction is not None:
            key += f":{ActionKeyToken.DIRECTION.value}:{action.direction}"
        if action.targets:
            key += f":{ActionKeyToken.TARGETS.value}:" + ";".join(
                f"{target.player},{int(target.position.front)},{target.position.rank.value}"
                for target in action.targets
            )
        return key

    raise TypeError(f"Unsupported action type: {type(action)!r}")


def _position(front: str, rank: str) -> Position:
    return Position(Front(int(front)), Rank(rank))


def action_from_key(key: str) -> object:
    """Inverse of the canonical action-key format."""
    if key == ActionKeyToken.PASS:
        return Pass()
    if key == ActionKeyToken.END_TURN:
        return EndTurn()
    if key.startswith(f"{ActionKeyToken.CYCLE.value}:"):
        _, first_card_id, second_card_id = key.split(":", 2)
        return Cycle(first_card_id, second_card_id)
    if key.startswith(f"{ActionKeyToken.DISCARD.value}:"):
        return Discard(key.split(":", 1)[1])

    parts = key.split(":")
    if parts[0] == ActionKeyToken.EFFECT:
        effect = parts[1]
        if len(parts) == 3 and parts[2] == ActionKeyToken.SKIP:
            return EffectChoice(effect, skip=True)
        source: BoardTarget | None = None
        destination: BoardTarget | None = None
        card_id: str | None = None
        front: Front | None = None
        index = 2
        while index < len(parts):
            label = parts[index]
            value = parts[index + 1]
            if label == ActionKeyToken.CARD:
                card_id = value
            elif label in {ActionKeyToken.SOURCE, ActionKeyToken.DESTINATION}:
                player, encoded_front, rank = value.split(",")
                target = BoardTarget(
                    int(player),
                    _position(encoded_front, rank),
                )
                if label == ActionKeyToken.SOURCE:
                    source = target
                else:
                    destination = target
            elif label == ActionKeyToken.FRONT:
                front = Front(int(value))
            else:
                raise ValueError(f"Unknown EffectChoice field: {label}")
            index += 2
        return EffectChoice(
            effect,
            source=source,
            destination=destination,
            card_id=card_id,
            front=front,
        )
    if parts[0] == ActionKeyToken.FORCE:
        return PlayForce(parts[1], _position(parts[2], parts[3]))
    if parts[0] == ActionKeyToken.BOND:
        position = _position(parts[2], parts[3])
        move_destination: Position | None = None
        extra_payment = 0
        index = 4
        while index < len(parts):
            label = parts[index]
            if label == ActionKeyToken.MOVE:
                move_destination = _position(parts[index + 1], parts[index + 2])
                index += 3
                continue
            if label == ActionKeyToken.EXTRA:
                extra_payment = int(parts[index + 1])
                index += 2
                continue
            raise ValueError(f"Unknown Bond action field: {label}")
        return PlayBond(parts[1], position, move_destination, extra_payment)
    if parts[0] == ActionKeyToken.NAME:
        return PlayName(parts[1], _position(parts[2], parts[3]))
    if parts[0] == ActionKeyToken.MANEUVER:
        return Maneuver(
            _position(parts[1], parts[2]),
            _position(parts[3], parts[4]),
        )
    if parts[0] == ActionKeyToken.STRATAGEM:
        card_id = parts[1]
        fronts: tuple[Front, ...] = ()
        direction: str | None = None
        targets: tuple[BoardTarget, ...] = ()
        index = 2
        while index < len(parts):
            label = parts[index]
            value = parts[index + 1]
            if label == ActionKeyToken.FRONTS:
                fronts = tuple(Front(int(front)) for front in value.split(",") if front)
            elif label == ActionKeyToken.DIRECTION:
                if value not in DIRECTIONS:
                    raise ValueError(f"Invalid direction in action key: {value}")
                direction = value
            elif label == ActionKeyToken.TARGETS:
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
    if parts[0] == ActionKeyToken.NARRATIVE:
        card_id = parts[1]
        if len(parts) >= 4 and parts[2] == ActionKeyToken.DISCARD_FIELD:
            return PlayNarrative(card_id, discard_card_id=parts[3])
        if len(parts) >= 4 and parts[2] == ActionKeyToken.ONGOING:
            slot = int(parts[3])
            fronts: tuple[Front, ...] = ()
            targets: tuple[BoardTarget, ...] = ()
            direction: str | None = None
            index = 4
            while index < len(parts):
                label = parts[index]
                value = parts[index + 1]
                if label == ActionKeyToken.FRONTS:
                    fronts = tuple(Front(int(front)) for front in value.split(",") if front)
                elif label == ActionKeyToken.DIRECTION:
                    if value not in DIRECTIONS:
                        raise ValueError(f"Invalid Narrative direction: {value}")
                    direction = value
                elif label == ActionKeyToken.TARGETS:
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
            return PlayNarrative(
                card_id,
                targets=targets,
                ongoing_slot=slot,
                fronts=fronts,
                direction=direction,
            )
        payload = ":".join(parts[2:])
        targets: list[BoardTarget] = []
        if payload:
            for encoded in payload.split(";"):
                player, front, rank = encoded.split(":")
                targets.append(
                    BoardTarget(int(player), _position(front, rank))
                )
        return PlayNarrative(card_id, tuple(targets))
    raise ValueError(f"Unknown action key: {key}")
