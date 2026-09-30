from __future__ import annotations

from dataclasses import dataclass, replace
@dataclass(frozen=True, slots=True)
class GameRules:
    """Immutable rules configuration shared by every engine consumer.

    Tools may override values for experiments; they do not create alternate
    named rules modes.
    Card-specific mechanics remain in card design_rules. The engine is the
    only layer allowed to interpret them into legal actions and transitions.
    """

    opening_hand_size: int = 10
    starting_command: int = 20
    command_cap: int = 20
    # Current balance candidate. The model is intentionally arithmetic:
    # max(0, start - decrement * (Battle - 1)).
    command_recovery_start: int = 12
    command_recovery_decrement: int = 3
    command_recovery_floor: int = 1
    command_collapse_threshold: int = 0
    maneuver_command_cost: int = 1
    hand_limit: int = 10
    ongoing_narrative_limit: int = 2
    def __post_init__(self) -> None:
        for name, rule_field in self.__dataclass_fields__.items():
            value = getattr(self, name)
            if isinstance(rule_field.default, bool):
                if type(value) is not bool:
                    raise ValueError(f"{name} must be boolean")
            elif isinstance(rule_field.default, int):
                if type(value) is not int:
                    raise ValueError(f"{name} must be an integer")
                if value < 0:
                    raise ValueError(f"{name} must be non-negative")

        if self.opening_hand_size < 1:
            raise ValueError("opening_hand_size must be positive")
        if self.starting_command > self.command_cap:
            raise ValueError("starting_command cannot exceed command_cap")

    @classmethod
    def standard(cls) -> "GameRules":
        return cls()

    def command_recovery_for_battle(self, battle: int) -> int:
        if battle < 1:
            raise ValueError("battle must be at least 1")
        return max(
            0,
            self.command_recovery_start
            - self.command_recovery_decrement * (battle - 1),
        )

    def with_overrides(self, **changes: object) -> "GameRules":
        return replace(self, **changes)

    def as_dict(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }

    def simulation_metadata(self) -> dict[str, object]:
        """Stable artifact provenance for the complete match-rule schema."""
        return self.as_dict()
