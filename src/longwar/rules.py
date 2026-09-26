from __future__ import annotations

from dataclasses import dataclass, replace
@dataclass(frozen=True, slots=True)
class GameRules:
    """Immutable rules configuration shared by every engine consumer.

    Tools may override values for experiments; they do not create alternate
    named rules modes.
    Card-specific rules remain in the card data. The engine is the only layer
    allowed to interpret either source into legal actions and transitions.
    """

    opening_hand_size: int = 10
    starting_command: int = 20
    command_cap: int = 20
    command_recovery_schedule: tuple[int, ...] = (10, 7, 5, 4, 3, 2, 1)
    command_collapse_threshold: int = 5
    maneuver_command_cost: int = 1
    hand_limit: int = 10
    ongoing_narrative_limit: int = 2
    def __post_init__(self) -> None:
        for name, field in self.__dataclass_fields__.items():
            value = getattr(self, name)
            if isinstance(field.default, bool):
                if type(value) is not bool:
                    raise ValueError(f"{name} must be boolean")
            elif isinstance(field.default, int):
                if type(value) is not int:
                    raise ValueError(f"{name} must be an integer")
        if (
            not isinstance(self.command_recovery_schedule, tuple)
            or any(type(value) is not int or value < 0 for value in self.command_recovery_schedule)
        ):
            raise ValueError("command_recovery_schedule must be a tuple of non-negative integers")
        if not self.command_recovery_schedule:
            raise ValueError("command_recovery_schedule must not be empty")
        if self.opening_hand_size < 1:
            raise ValueError("opening_hand_size must be positive")
        if min(
            self.starting_command,
            self.command_cap,
            self.command_collapse_threshold,
            self.maneuver_command_cost,
            self.hand_limit,
            self.ongoing_narrative_limit,
        ) < 0:
            raise ValueError("Command settings must be non-negative")
        if self.starting_command > self.command_cap:
            raise ValueError("starting_command cannot exceed command_cap")

    @classmethod
    def standard(cls) -> "GameRules":
        return cls()

    def with_overrides(self, **changes: object) -> "GameRules":
        return replace(self, **changes)

    def as_dict(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }
