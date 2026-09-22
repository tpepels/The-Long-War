from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Sequence


@dataclass
class _PythonCFRNode:
    regret_sum: dict[str, float] = field(default_factory=dict)
    strategy_sum: dict[str, float] = field(default_factory=dict)
    visits: int = 0
    average_visits: int = 0

    def ensure_actions(self, keys: Sequence[str]) -> None:
        for key in keys:
            self.regret_sum.setdefault(key, 0.0)
            self.strategy_sum.setdefault(key, 0.0)

    def strategy(self, keys: Sequence[str]) -> dict[str, float]:
        self.ensure_actions(keys)
        positives = {key: max(0.0, self.regret_sum[key]) for key in keys}
        total = sum(positives.values())
        if total > 0:
            return {key: positives[key] / total for key in keys}
        probability = 1.0 / len(keys)
        return {key: probability for key in keys}

    def accumulate_average(
        self,
        strategy: dict[str, float],
        *,
        reach_weight: float = 1.0,
    ) -> None:
        for key, probability in strategy.items():
            self.strategy_sum[key] = (
                self.strategy_sum.get(key, 0.0)
                + reach_weight * probability
            )
        self.average_visits += 1

    def average_strategy(
        self,
        keys: Sequence[str] | None = None,
    ) -> dict[str, float]:
        keys = list(keys or self.strategy_sum)
        if not keys:
            return {}
        total = sum(max(0.0, self.strategy_sum.get(key, 0.0)) for key in keys)
        if total <= 0:
            return self.strategy(keys)
        return {
            key: max(0.0, self.strategy_sum.get(key, 0.0)) / total
            for key in keys
        }


def _python_sample_distribution(
    rng: random.Random,
    probabilities: dict[str, float],
) -> str:
    threshold = rng.random()
    cumulative = 0.0
    last = next(iter(probabilities))
    for key, probability in probabilities.items():
        last = key
        cumulative += probability
        if threshold <= cumulative:
            return key
    return last


def _python_external_sampling_traverse(
    state: Any,
    traverser: int,
    *,
    depth: int,
    max_depth: int | None,
    nodes: dict[Hashable, Any],
    rng: random.Random,
    is_terminal: Callable[[Any], bool],
    terminal_utility: Callable[[Any, int], float],
    current_player: Callable[[Any], int],
    legal_actions: Callable[[Any], Sequence[Any]],
    action_key: Callable[[Any], str],
    information_set_id: Callable[[Any, int], Hashable],
    next_state: Callable[[Any, Any], Any],
    leaf_value: Callable[[Any, int], float] | None = None,
    reach: tuple[float, float] = (1.0, 1.0),
) -> float:
    """Pure-Python fallback for two-player external-sampling MCCFR."""
    if is_terminal(state):
        return terminal_utility(state, traverser)

    if max_depth is not None and depth >= max_depth:
        if leaf_value is None:
            raise RuntimeError("Depth limit reached without a leaf evaluator")
        return leaf_value(state, traverser)

    actor = current_player(state)
    actions = list(legal_actions(state))
    if not actions:
        raise RuntimeError("Non-terminal state has no legal actions")

    keys = [action_key(action) for action in actions]
    if len(keys) != len(set(keys)):
        raise RuntimeError("Action serialization collision inside information set")

    info_id = information_set_id(state, actor)
    node = nodes.get(info_id)
    if node is None:
        node = _PythonCFRNode()
        nodes[info_id] = node
    node.ensure_actions(keys)
    node.visits += 1
    strategy = node.strategy(keys)
    action_by_key = dict(zip(keys, actions))

    if actor == traverser:
        action_utilities: dict[str, float] = {}
        node_utility = 0.0
        for key in keys:
            child_reach = [reach[0], reach[1]]
            child_reach[actor] *= strategy[key]
            utility = _python_external_sampling_traverse(
                next_state(state, action_by_key[key]),
                traverser,
                depth=depth + 1,
                max_depth=max_depth,
                nodes=nodes,
                rng=rng,
                is_terminal=is_terminal,
                terminal_utility=terminal_utility,
                current_player=current_player,
                legal_actions=legal_actions,
                action_key=action_key,
                information_set_id=information_set_id,
                next_state=next_state,
                leaf_value=leaf_value,
                reach=(child_reach[0], child_reach[1]),
            )
            action_utilities[key] = utility
            node_utility += strategy[key] * utility

        for key in keys:
            node.regret_sum[key] += action_utilities[key] - node_utility
        return node_utility

    node.accumulate_average(strategy, reach_weight=reach[actor])
    sampled_key = _python_sample_distribution(rng, strategy)
    child_reach = [reach[0], reach[1]]
    child_reach[actor] *= strategy[sampled_key]
    return _python_external_sampling_traverse(
        next_state(state, action_by_key[sampled_key]),
        traverser,
        depth=depth + 1,
        max_depth=max_depth,
        nodes=nodes,
        rng=rng,
        is_terminal=is_terminal,
        terminal_utility=terminal_utility,
        current_player=current_player,
        legal_actions=legal_actions,
        action_key=action_key,
        information_set_id=information_set_id,
        next_state=next_state,
        leaf_value=leaf_value,
        reach=(child_reach[0], child_reach[1]),
    )


try:
    from ._mccfr_accel import (
        CFRNode,
        external_sampling_traverse,
        sample_distribution,
    )
except ImportError:
    CFRNode = _PythonCFRNode
    sample_distribution = _python_sample_distribution
    external_sampling_traverse = _python_external_sampling_traverse
    ACCELERATED = False
    BACKEND = "python"
else:
    ACCELERATED = True
    BACKEND = "cython"


__all__ = [
    "ACCELERATED",
    "BACKEND",
    "CFRNode",
    "external_sampling_traverse",
    "sample_distribution",
]
