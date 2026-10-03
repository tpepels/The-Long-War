from __future__ import annotations

from dataclasses import dataclass, replace

from .protocol import (
    NARRATIVE_STORAGE_CAPACITY_PER_PLAYER,
    STRATAGEM_ACTIVE_CAPACITY_PER_PLAYER,
)


@dataclass(frozen=True, slots=True)
class GameRules:
    """Immutable rules configuration shared by every engine consumer.

    Tools may override values for experiments; they do not create alternate
    named rules modes.
    Card-specific mechanics remain in card design_rules. The engine is the
    only layer allowed to interpret them into legal actions and transitions.
    """

    opening_hand_size: int = 10
    mulligan_max_cards: int = 2
    starting_command: int = 20
    command_cap: int = 20
    # Current balance candidate. The model is intentionally arithmetic:
    # max(0, start - decrement * (Battle - 1)).
    command_recovery_start: int = 12
    command_recovery_decrement: int = 3
    command_recovery_floor: int = 1
    command_collapse_threshold: int = 0
    lost_front_command_penalty: int = 1
    # A normal turn draws once, then takes up to two Actions. Pass is a
    # separate forced turn available only when no legal Action exists.
    actions_per_turn: int = 2
    # Deprecated compatibility surface. Pass no longer depends on a minimum
    # number of earlier operations; legality is determined by available Actions.
    pass_min_operations_before_signal: int = 0
    turn_draw_count: int = 1
    maneuver_command_cost: int = 1
    hand_limit: int = 10
    ongoing_narrative_limit: int = 2
    hero_force_play_limit_per_battle: int = 1
    hero_name_play_limit_per_battle: int = 1
    # Aggregate compatibility surface used by telemetry/reference rendering.
    hero_play_limit_per_battle: int = 2
    stratagem_play_limit_per_battle: int = 1

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
        if self.command_collapse_threshold > self.command_cap:
            raise ValueError(
                "command_collapse_threshold cannot exceed command_cap"
            )
        if (
            self.ongoing_narrative_limit
            > NARRATIVE_STORAGE_CAPACITY_PER_PLAYER
        ):
            raise ValueError(
                "ongoing_narrative_limit exceeds native Narrative capacity "
                f"({NARRATIVE_STORAGE_CAPACITY_PER_PLAYER})"
            )
        if (
            self.stratagem_play_limit_per_battle
            > STRATAGEM_ACTIVE_CAPACITY_PER_PLAYER
        ):
            raise ValueError(
                "stratagem_play_limit_per_battle exceeds active Stratagem "
                f"capacity ({STRATAGEM_ACTIVE_CAPACITY_PER_PLAYER})"
            )

    @classmethod
    def standard(cls) -> "GameRules":
        """Return the canonical ruleset used by normal play and AI."""
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
