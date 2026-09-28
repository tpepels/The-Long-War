from __future__ import annotations

from dataclasses import dataclass

from .game.model import GameState, Position


@dataclass
class GameScenario:
    """Small fluent builder for focused engine tests and design probes.

    Tests describe the semantic situation they need instead of reaching into
    unrelated GameState bookkeeping at every call site. The builder mutates the
    supplied state intentionally and returns itself for chaining.
    """

    state: GameState

    def battle(self, number: int) -> "GameScenario":
        self.state.battle = int(number)
        return self

    def active_player(self, player: int) -> "GameScenario":
        self.state.active_player = int(player)
        return self

    def command(self, player: int, value: int) -> "GameScenario":
        self.state.players[player].command = int(value)
        return self

    def commands(self, player_zero: int, player_one: int) -> "GameScenario":
        self.state.players[0].command = int(player_zero)
        self.state.players[1].command = int(player_one)
        return self

    def battle_start_commands(
        self,
        player_zero: int,
        player_one: int,
    ) -> "GameScenario":
        self.state.battle_start_command[:] = [
            int(player_zero),
            int(player_one),
        ]
        return self

    def operations(self, player_zero: int, player_one: int) -> "GameScenario":
        self.state.operations_this_battle[:] = [
            int(player_zero),
            int(player_one),
        ]
        return self

    def hand(self, player: int, *cards: str) -> "GameScenario":
        self.state.players[player].hand[:] = cards
        return self

    def clear_hands(self) -> "GameScenario":
        self.state.players[0].hand.clear()
        self.state.players[1].hand.clear()
        return self

    def formation(
        self,
        player: int,
        position: Position,
        *,
        force: str | None = None,
        bond: str | None = None,
        name: str | None = None,
    ) -> "GameScenario":
        slot = self.state.slot(player, position)
        slot.force = force
        slot.bond = bond
        slot.name = name
        return self

    def build(self) -> GameState:
        return self.state
