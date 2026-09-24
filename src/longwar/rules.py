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
    paid_draw_consumes_operation: bool = True
    automatic_draw_hand_limit: int | None = None
    battle_end_hand_limit: int | None = None

    pass_final_operation: bool = False
    pass_requires_both_acted: bool = False
    first_passer_starts_next_battle: bool = False
    completion_command_refund: int = 0
    public_stratagems: bool = False

    def __post_init__(self) -> None:
        for name, field in self.__dataclass_fields__.items():
            value = getattr(self, name)
            if isinstance(field.default, bool):
                if type(value) is not bool:
                    raise ValueError(f"{name} must be boolean")
            elif isinstance(field.default, int) or name.endswith("hand_limit"):
                if value is None and name.endswith("hand_limit"):
                    continue
                if type(value) is not int:
                    raise ValueError(f"{name} must be an integer")
        if not isinstance(self.completion_draw_names, tuple) or any(
            not isinstance(card_id, str) or not card_id
            for card_id in self.completion_draw_names
        ):
            raise ValueError("completion_draw_names must be a tuple of card ids")
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
        for name, value in (
            ("automatic_draw_hand_limit", self.automatic_draw_hand_limit),
            ("battle_end_hand_limit", self.battle_end_hand_limit),
        ):
            if value is not None and value < 1:
                raise ValueError(f"{name} must be positive when enabled")
        if self.automatic_draw_hand_limit is not None and not self.automatic_draw:
            raise ValueError(
                "automatic_draw_hand_limit requires automatic_draw"
            )

    @classmethod
    def standard(cls) -> "GameRules":
        return cls()

    @staticmethod
    def profile_names() -> tuple[str, ...]:
        return ("standard", "force-automatic", "force-paid", "force-paid-free",
                "force-auto-discard9", "force-auto-discard7", "force-auto-cap10")

    @classmethod
    def from_profile(cls, name: str) -> "GameRules":
        if name == "standard":
            return cls.standard()
        if name in {"force-automatic", "force-paid"}:
            return cls.force_candidate(name.removeprefix("force-"))
        if name in cls.profile_names():
            return cls.force_experiment(name.removeprefix("force-"))
        raise ValueError(f"Unknown rules profile: {name}")

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


    @classmethod
    def force_experiment(cls, variant: str) -> "GameRules":
        """Named Force-flow experiment variants.

        control: current automatic Draw.
        paid-free: paid Draw costs Command but keeps the operation.
        auto-discard9/7: automatic Draw plus strategic Battle-end cleanup.
        auto-cap10: automatic Draw only while hand size is below 10.
        """
        if variant == "control":
            return cls.force_candidate("automatic")
        if variant == "paid-free":
            return cls.force_candidate("paid").with_overrides(
                paid_draw_consumes_operation=False,
            )
        if variant == "auto-discard9":
            return cls.force_candidate("automatic").with_overrides(
                battle_end_hand_limit=9,
            )
        if variant == "auto-discard7":
            return cls.force_candidate("automatic").with_overrides(
                battle_end_hand_limit=7,
            )
        if variant == "auto-cap10":
            return cls.force_candidate("automatic").with_overrides(
                automatic_draw_hand_limit=10,
            )
        raise ValueError(f"Unknown Force experiment variant: {variant}")

    def with_overrides(self, **changes: object) -> "GameRules":
        return replace(self, **changes)

    def as_dict(self) -> dict[str, object]:
        return {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }
