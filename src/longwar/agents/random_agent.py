from __future__ import annotations

import random

from ..game.actions import Action, Pass
from ..game.engine import GameEngine
from ..game.model import GameState, Phase


class RandomAgent:
    def __init__(self, seed: int, *, pass_probability: float = 0.10):
        self.rng = random.Random(seed)
        self.pass_probability = pass_probability

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        actions = engine.legal_actions(state)

        if state.phase is not Phase.BATTLE:
            return self.rng.choice(actions)

        non_pass = [action for action in actions if not isinstance(action, Pass)]
        if not non_pass:
            return Pass()
        if self.rng.random() < self.pass_probability:
            return Pass()
        return self.rng.choice(non_pass)
