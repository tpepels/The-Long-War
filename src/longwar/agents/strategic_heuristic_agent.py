from __future__ import annotations

from statistics import mean

from ..belief import BeliefSampler, DeckPrior
from ..game.actions import Action, Pass
from ..game.engine import GameEngine
from ..game.model import GameState, Phase
from .heuristic_agent import HeuristicAgent, ScoredAction


class StrategicHeuristicAgent(HeuristicAgent):
    """Belief-sampled shallow rollout on top of the public heuristic.

    The ordinary heuristic is deliberately one-ply. This agent keeps that
    evaluator, but tests a small set of promising root actions across sampled
    hidden states and rolls forward through likely replies. It never reads the
    true opponent hand: hidden cards come from BeliefSampler.
    """

    def __init__(
        self,
        engine: GameEngine,
        seed: int,
        *,
        priors: tuple[DeckPrior, DeckPrior] | None = None,
        belief_samples: int = 3,
        rollout_plies: int = 3,
        candidate_width: int = 8,
        exploration: float = 0.0,
    ):
        super().__init__(seed=seed, exploration=exploration)
        if belief_samples <= 0:
            raise ValueError("belief_samples must be positive")
        if rollout_plies <= 0:
            raise ValueError("rollout_plies must be positive")
        if candidate_width <= 0:
            raise ValueError("candidate_width must be positive")
        self.belief = BeliefSampler(engine, priors=priors)
        self.belief_samples = belief_samples
        self.rollout_plies = rollout_plies
        self.candidate_width = candidate_width

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        player = state.active_player
        actions = engine.legal_actions(state)
        if len(actions) == 1:
            self.last_decision = {
                "candidate_count": 1,
                "selected_score": 0.0,
                "score_gap": 0.0,
                "selected_action": type(actions[0]).__name__,
                "policy_source": "strategic_heuristic",
                "belief_samples": 0,
                "rollout_plies": self.rollout_plies,
                "evaluated_candidates": 1,
            }
            return actions[0]

        base = [
            ScoredAction(action, self._score_action(engine, state, player, action))
            for action in actions
        ]
        self.rng.shuffle(base)
        base.sort(key=lambda item: item.score, reverse=True)

        candidates = [item.action for item in base[: self.candidate_width]]
        # Passing has match-level resource consequences under Command and can
        # be strategically correct even when its immediate one-ply score is
        # poor. Always let the deeper pass evaluate it.
        for action in actions:
            if isinstance(action, Pass) and action not in candidates:
                candidates.append(action)

        scored: list[ScoredAction] = []
        for action in candidates:
            samples: list[float] = []
            for _ in range(self.belief_samples):
                sampled = self.belief.sample(state, player, self.rng)
                engine.apply(sampled, action, validate=False)
                self._roll_forward(
                    engine,
                    sampled,
                    root_player=player,
                    remaining_plies=self.rollout_plies - 1,
                )
                samples.append(
                    self._strategic_state_value(engine, sampled, player)
                )
            scored.append(ScoredAction(action, mean(samples)))

        self.rng.shuffle(scored)
        scored.sort(key=lambda item: item.score, reverse=True)
        selected = scored[0]
        second = scored[1].score if len(scored) > 1 else selected.score
        self.last_decision = {
            "candidate_count": len(actions),
            "selected_score": selected.score,
            "score_gap": selected.score - second,
            "selected_action": type(selected.action).__name__,
            "policy_source": "strategic_heuristic",
            "belief_samples": self.belief_samples,
            "rollout_plies": self.rollout_plies,
            "evaluated_candidates": len(candidates),
        }
        return selected.action

    def _roll_forward(
        self,
        engine: GameEngine,
        state: GameState,
        *,
        root_player: int,
        remaining_plies: int,
    ) -> None:
        del root_player  # reserved for future asymmetric rollout policies
        for _ in range(remaining_plies):
            if state.phase is Phase.COMPLETE:
                return
            actor = state.active_player
            actions = engine.legal_actions(state)
            if not actions:
                return
            action = max(
                actions,
                key=lambda candidate: self._score_action(
                    engine,
                    state,
                    actor,
                    candidate,
                ),
            )
            engine.apply(state, action, validate=False)

    def _strategic_state_value(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        value = self._state_value(engine, state, player)
        if state.phase is Phase.COMPLETE:
            return value

        opponent = 1 - player

        # In persistent-deck variants, cards committed or Cycled away this
        # Battle are unavailable later. Give modest value to future formation
        # material without overwhelming the actual Front objective.
        if not engine.recycle_between_battles:
            value += 0.18 * (
                len(state.players[player].deck)
                - len(state.players[opponent].deck)
            )
            value += 0.45 * (
                self._future_formation_sets(engine, state, player)
                - self._future_formation_sets(engine, state, opponent)
            )
            value += 0.35 * (
                self._future_force_availability(engine, state, player)
                - self._future_force_availability(engine, state, opponent)
            )
        return value

    @staticmethod
    def _future_force_availability(
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> float:
        immediate = state.players[player].hand + state.players[player].deck
        discard = state.players[player].discard
        return float(
            sum(engine.cards[card_id]["type"] == "subject" for card_id in immediate)
        ) + 0.35 * float(
            sum(engine.cards[card_id]["type"] == "subject" for card_id in discard)
        )

    @staticmethod
    def _future_formation_sets(
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> int:
        remaining = state.players[player].hand + state.players[player].deck
        counts = {"subject": 0, "link": 0, "name": 0}
        for card_id in remaining:
            card_type = engine.cards[card_id]["type"]
            if card_type in counts:
                counts[card_type] += 1
        return min(counts.values())
