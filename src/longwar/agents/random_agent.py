from __future__ import annotations

import random

from ..game.actions import Action, Pass
from ..game.engine import GameEngine
from ..game.model import GameState, Phase


class RandomAgent:
    def __init__(self, seed: int, *, pass_probability: float = 0.10):
        self.rng = random.Random(seed)
        self.pass_probability = pass_probability

    def choose_mulligan(
        self,
        engine: GameEngine,
        hand: list[str],
    ) -> tuple[int, ...]:
        del engine
        count = min(2, len(hand))
        return tuple(sorted(self.rng.sample(range(len(hand)), count)))

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        actions = engine.legal_actions(state)

        if state.phase is not Phase.BATTLE:
            return self.rng.choice(actions)

        pass_actions = [action for action in actions if isinstance(action, Pass)]
        non_pass = [action for action in actions if not isinstance(action, Pass)]
        if not non_pass:
            return pass_actions[0]
        if self.rng.random() < self.pass_probability and pass_actions:
            return pass_actions[0]
        return self.rng.choice(non_pass)
