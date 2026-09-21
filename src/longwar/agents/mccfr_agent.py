from __future__ import annotations

import random
from typing import Any

from ..game.actions import Action
from ..game.engine import GameEngine
from ..game.model import GameState
from ..mccfr import action_key, information_set_id
from .heuristic_agent import HeuristicAgent


class MCCFRAgent:
    """Policy agent backed by an exported MCCFR information-set table."""

    def __init__(
        self,
        seed: int,
        policy: dict[str, Any],
        *,
        deterministic: bool = False,
        fallback: str = "heuristic",
    ):
        if policy.get("schema_version") != 1:
            raise ValueError("Unsupported MCCFR policy schema")
        self.rng = random.Random(seed)
        self.policy = policy
        self.deterministic = deterministic
        self.fallback_name = fallback
        self.fallback_agent = HeuristicAgent(seed=seed, exploration=0.0)
        self.last_decision: dict[str, float | int | str] = {}

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        actions = engine.legal_actions(state)
        if len(actions) == 1:
            self.last_decision = {
                "candidate_count": 1,
                "selected_score": 1.0,
                "score_gap": 1.0,
                "selected_action": type(actions[0]).__name__,
                "policy_source": "forced",
            }
            return actions[0]

        info_id = information_set_id(state, state.active_player)
        entry = self.policy.get("infosets", {}).get(info_id)

        if entry is None:
            action = self.fallback_agent.choose(engine, state)
            self.last_decision = dict(self.fallback_agent.last_decision)
            self.last_decision["policy_source"] = f"fallback:{self.fallback_name}"
            return action

        probabilities = entry.get("average_strategy") or entry.get("current_strategy") or {}
        action_map = {action_key(action): action for action in actions}
        filtered = {
            key: float(probabilities.get(key, 0.0))
            for key in action_map
        }
        total = sum(max(0.0, value) for value in filtered.values())

        if total <= 0:
            action = self.fallback_agent.choose(engine, state)
            self.last_decision = dict(self.fallback_agent.last_decision)
            self.last_decision["policy_source"] = f"fallback:{self.fallback_name}"
            return action

        normalized = {
            key: max(0.0, value) / total
            for key, value in filtered.items()
        }

        ranked = sorted(
            normalized.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
        if self.deterministic:
            selected_key = ranked[0][0]
        else:
            selected_key = self._sample(normalized)

        best = ranked[0][1]
        second = ranked[1][1] if len(ranked) > 1 else 0.0
        self.last_decision = {
            "candidate_count": len(actions),
            "selected_score": normalized[selected_key],
            "score_gap": best - second,
            "selected_action": type(action_map[selected_key]).__name__,
            "policy_source": "mccfr",
        }
        return action_map[selected_key]

    def _sample(self, probabilities: dict[str, float]) -> str:
        threshold = self.rng.random()
        cumulative = 0.0
        last = next(iter(probabilities))
        for key, probability in probabilities.items():
            last = key
            cumulative += probability
            if threshold <= cumulative:
                return key
        return last
