from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from typing import Any

from .mccfr_core import CFRNode, external_sampling_traverse

CARDS = (0, 1, 2)  # J, Q, K
ACTIONS = ("p", "b")
KNOWN_P0_VALUE = -1.0 / 18.0


@dataclass(frozen=True)
class KuhnState:
    cards: tuple[int, int]
    history: str = ""


def kuhn_terminal(state: KuhnState) -> bool:
    return state.history in {"pp", "bp", "bb", "pbp", "pbb"}


def kuhn_actor(state: KuhnState) -> int:
    return len(state.history) % 2


def kuhn_actions(state: KuhnState) -> tuple[str, str]:
    if kuhn_terminal(state):
        return ()
    return ACTIONS


def kuhn_infoset(state: KuhnState, player: int) -> str:
    return f"{player}:{state.cards[player]}:{state.history}"


def kuhn_next(state: KuhnState, action: str) -> KuhnState:
    return KuhnState(state.cards, state.history + action)


def kuhn_utility_p0(state: KuhnState) -> float:
    history = state.history
    p0_wins = state.cards[0] > state.cards[1]
    if history == "pp":
        return 1.0 if p0_wins else -1.0
    if history == "bp":
        return 1.0
    if history == "pbp":
        return -1.0
    if history in {"bb", "pbb"}:
        return 2.0 if p0_wins else -2.0
    raise ValueError(f"Non-terminal Kuhn history: {history}")


def kuhn_terminal_utility(state: KuhnState, traverser: int) -> float:
    value = kuhn_utility_p0(state)
    return value if traverser == 0 else -value


def all_deals() -> tuple[tuple[int, int], ...]:
    return tuple(itertools.permutations(CARDS, 2))


def average_policy(nodes: dict[str, CFRNode]) -> dict[str, dict[str, float]]:
    return {
        info_id: node.average_strategy(ACTIONS)
        for info_id, node in nodes.items()
    }


def train_kuhn_external_sampling(
    *,
    iterations: int,
    seed: int,
) -> dict[str, CFRNode]:
    rng = random.Random(seed)
    nodes: dict[str, CFRNode] = {}
    deals = all_deals()

    for _ in range(iterations):
        state = KuhnState(rng.choice(deals))
        for traverser in (0, 1):
            external_sampling_traverse(
                state,
                traverser,
                depth=0,
                max_depth=None,
                nodes=nodes,
                rng=rng,
                is_terminal=kuhn_terminal,
                terminal_utility=kuhn_terminal_utility,
                current_player=kuhn_actor,
                legal_actions=kuhn_actions,
                action_key=lambda action: action,
                information_set_id=kuhn_infoset,
                next_state=kuhn_next,
            )
    return nodes


def expected_value(
    policy: dict[str, dict[str, float]],
    *,
    pure_p0: dict[str, str] | None = None,
    pure_p1: dict[str, str] | None = None,
) -> float:
    def recurse(state: KuhnState) -> float:
        if kuhn_terminal(state):
            return kuhn_utility_p0(state)

        actor = kuhn_actor(state)
        info_id = kuhn_infoset(state, actor)
        pure = pure_p0 if actor == 0 else pure_p1
        if pure is not None:
            return recurse(kuhn_next(state, pure[info_id]))

        strategy = policy.get(info_id, {"p": 0.5, "b": 0.5})
        return sum(
            strategy[action] * recurse(kuhn_next(state, action))
            for action in ACTIONS
        )

    return sum(recurse(KuhnState(deal)) for deal in all_deals()) / 6.0


def player_infosets(player: int) -> tuple[str, ...]:
    histories = ("", "pb") if player == 0 else ("p", "b")
    return tuple(
        f"{player}:{card}:{history}"
        for card in CARDS
        for history in histories
    )


def pure_strategies(player: int):
    infosets = player_infosets(player)
    for choices in itertools.product(ACTIONS, repeat=len(infosets)):
        yield dict(zip(infosets, choices))


def exploitability(
    policy: dict[str, dict[str, float]],
) -> tuple[float, float, float]:
    best_p0 = max(
        expected_value(policy, pure_p0=strategy)
        for strategy in pure_strategies(0)
    )
    worst_for_p0 = min(
        expected_value(policy, pure_p1=strategy)
        for strategy in pure_strategies(1)
    )
    nash_conv = best_p0 - worst_for_p0
    return nash_conv / 2.0, best_p0, worst_for_p0


def verify_kuhn(
    *,
    iterations: int = 50_000,
    seed: int = 20260921,
    max_value_error: float = 0.03,
    max_exploitability: float = 0.06,
) -> dict[str, Any]:
    nodes = train_kuhn_external_sampling(iterations=iterations, seed=seed)
    policy = average_policy(nodes)
    value = expected_value(policy)
    exp, best_p0, worst_for_p0 = exploitability(policy)
    value_error = abs(value - KNOWN_P0_VALUE)
    passed = value_error <= max_value_error and exp <= max_exploitability

    return {
        "benchmark": "Kuhn poker",
        "algorithm": "shared external_sampling_traverse",
        "iterations": iterations,
        "seed": seed,
        "known_p0_value": KNOWN_P0_VALUE,
        "learned_p0_value": value,
        "absolute_value_error": value_error,
        "exploitability": exp,
        "best_response_p0_value": best_p0,
        "best_response_p1_as_p0_value": worst_for_p0,
        "thresholds": {
            "max_value_error": max_value_error,
            "max_exploitability": max_exploitability,
        },
        "information_sets": len(nodes),
        "passed": passed,
        "policy": policy,
    }
