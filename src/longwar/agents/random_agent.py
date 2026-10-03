from __future__ import annotations

import random

from ..game.actions import Action
from ..game.engine import GameEngine
from ..game.model import GameState


class RandomAgent:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def choose_mulligan(
        self,
        engine: GameEngine,
        hand: list[str],
    ) -> tuple[int, ...]:
        count = min(engine.rules.mulligan_max_cards, len(hand))
        return tuple(sorted(self.rng.sample(range(len(hand)), count)))

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        # Pass is forced by the engine and therefore never competes with a
        # normal Action. EndTurn is an ordinary strategic choice and remains
        # part of the uniform legal-action sample.
        return self.rng.choice(engine.legal_actions(state))
