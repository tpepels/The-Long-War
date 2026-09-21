from __future__ import annotations

import random
from dataclasses import dataclass

from .belief import BeliefSampler
from .game.actions import Action
from .game.engine import GameEngine
from .game.model import GameState, Phase
from .mccfr import MCCFRTrainer, action_key, information_set_id


@dataclass(frozen=True)
class OnlineResolveResult:
    player: int
    iterations: int
    belief_samples: int
    information_sets: int
    root_information_set: str
    root_average_visits: int
    strategy: dict[str, float]
    action_count: int

    @property
    def root_coverage(self) -> float:
        return 1.0 if self.root_average_visits > 0 else 0.0


class OnlineMCCFRResolver:
    """Depth-limited MCCFR re-solving from the current information set.

    Each iteration samples a fresh hidden-state determinization from the
    player's belief, while all samples share the same root information set.
    The local regret table is discarded after the decision.
    """

    def __init__(
        self,
        engine: GameEngine,
        decklists: tuple[list[str], list[str]],
        *,
        seed: int = 1701,
        iterations: int = 16,
        max_depth: int = 2,
        leaf_scale: float = 100.0,
    ):
        if iterations <= 0:
            raise ValueError("iterations must be positive")
        self.engine = engine
        self.decklists = (list(decklists[0]), list(decklists[1]))
        self.iterations = iterations
        self.max_depth = max_depth
        self.leaf_scale = leaf_scale
        self.rng = random.Random(seed)
        self.belief = BeliefSampler(engine, self.decklists)

    def solve(
        self,
        state: GameState,
        *,
        player: int | None = None,
    ) -> OnlineResolveResult:
        if state.phase is Phase.COMPLETE:
            raise ValueError("Cannot resolve a completed game")
        viewer = state.active_player if player is None else player
        if viewer != state.active_player:
            raise ValueError("Online resolver currently solves only the acting player")

        legal = self.engine.legal_actions(state)
        keys = [action_key(action) for action in legal]
        root_id = information_set_id(state, viewer)

        trainer_seed = self.rng.randrange(0, 2**31)
        belief_seed = self.rng.randrange(0, 2**31)
        belief_rng = random.Random(belief_seed)
        trainer = MCCFRTrainer(
            self.engine,
            self.decklists[0],
            self.decklists[1],
            seed=trainer_seed,
            max_depth=self.max_depth,
            leaf_scale=self.leaf_scale,
        )

        trainer.train_from_sampler(
            lambda: self.belief.sample(state, viewer, belief_rng),
            iterations=self.iterations,
        )

        node = trainer.nodes.get(root_id)
        if node is None:
            raise RuntimeError(
                "Online MCCFR did not visit the current root information set"
            )
        strategy = node.average_strategy(keys)
        if not strategy or sum(strategy.values()) <= 0:
            strategy = node.strategy(keys)

        return OnlineResolveResult(
            player=viewer,
            iterations=self.iterations,
            belief_samples=self.iterations,
            information_sets=len(trainer.nodes),
            root_information_set=root_id,
            root_average_visits=node.average_visits,
            strategy=strategy,
            action_count=len(legal),
        )
