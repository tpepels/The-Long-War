from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal


DrawMode = Literal["automatic", "paid"]


@dataclass(frozen=True, slots=True)
class GameRules:
    """Immutable rules configuration shared by every engine consumer.

    Tools select a rules profile; they do not re-declare individual game rules.
    Card-specific rules remain in the card data. The engine is the only layer
    allowed to interpret either source into legal actions and transitions.
    """

    opening_hand_size: int = 10
    draw_action_enabled: bool = True
    completion_draw_names: tuple[str, ...] = ()
    deck_size: int = 30
    recycle_between_battles: bool = True

    command_enabled: bool = False
    starting_command: int = 20
    battle_command_gain: int = 10
    command_cap: int = 20
    cycle_command_cost: int = 1
    cycle_enabled: bool = True

    reshuffle_on_empty: bool = False
    automatic_draw: bool = False
    paid_draw_enabled: bool = False
    paid_draw_command_cost: int = 1

    pass_final_operation: bool = False
    pass_requires_both_acted: bool = False
    first_passer_starts_next_battle: bool = False
    completion_command_refund: int = 0
    public_stratagems: bool = False

    def __post_init__(self) -> None:
        if self.deck_size < 1:
            raise ValueError("deck_size must be positive")
        if not 1 <= self.opening_hand_size <= self.deck_size:
            raise ValueError(
                "opening_hand_size must be between 1 and deck_size"
            )
        if min(
            self.starting_command,
            self.battle_command_gain,
            self.command_cap,
            self.cycle_command_cost,
            self.paid_draw_command_cost,
            self.completion_command_refund,
        ) < 0:
            raise ValueError("Command settings must be non-negative")
        if self.starting_command > self.command_cap:
            raise ValueError("starting_command cannot exceed command_cap")
        if self.automatic_draw and self.paid_draw_enabled:
            raise ValueError(
                "automatic_draw and paid_draw_enabled are mutually exclusive"
            )
        if self.paid_draw_enabled and not self.command_enabled:
            raise ValueError("paid_draw_enabled requires Command mode")

    @classmethod
    def standard(cls) -> "GameRules":
        return cls()

    @classmethod
    def force_candidate(cls, draw_mode: DrawMode) -> "GameRules":
        if draw_mode not in {"automatic", "paid"}:
            raise ValueError(f"Unknown Force draw mode: {draw_mode}")
        return cls(
            opening_hand_size=10,
            draw_action_enabled=False,
            deck_size=34,
            recycle_between_battles=False,
            command_enabled=True,
            starting_command=20,
            battle_command_gain=10,
            command_cap=20,
            cycle_enabled=False,
            reshuffle_on_empty=True,
            automatic_draw=draw_mode == "automatic",
            paid_draw_enabled=draw_mode == "paid",
            paid_draw_command_cost=1,
            pass_final_operation=True,
            pass_requires_both_acted=True,
            first_passer_starts_next_battle=True,
            completion_command_refund=1,
            public_stratagems=True,
        )

    def with_overrides(self, **changes: object) -> "GameRules":
        return replace(self, **changes)

    def as_dict(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }
