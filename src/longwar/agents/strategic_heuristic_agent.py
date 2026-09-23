from __future__ import annotations

from dataclasses import dataclass
from math import inf
from statistics import mean

from ..belief import BeliefSampler, DeckPrior
from ..game.actions import Action, Draw, Pass
from ..game.engine import GameEngine, all_positions
from ..game.model import GameState, Phase
from .heuristic_agent import HeuristicAgent, ScoredAction


class _SearchLimit(RuntimeError):
    pass


@dataclass
class _SearchBudget:
    limit: int
    nodes: int = 0

    def visit(self) -> None:
        self.nodes += 1
        if self.nodes > self.limit:
            raise _SearchLimit


class StrategicHeuristicAgent(HeuristicAgent):
    """Belief-sampled adversarial search on top of the public heuristic.

    A root decision is evaluated against several hidden-state determinizations.
    For each sampled state, both players search adversarially with alpha-beta
    pruning rather than following a greedy rollout. Iterative deepening makes
    the node budget predictable: if a deeper iteration is interrupted, the
    agent keeps the last fully completed depth.

    The true opponent hand is never inspected. BeliefSampler supplies each
    plausible hidden state from information available to the acting player.
    """

    def __init__(
        self,
        engine: GameEngine,
        seed: int,
        *,
        priors: tuple[DeckPrior, DeckPrior] | None = None,
        belief_samples: int = 3,
        rollout_plies: int = 5,
        candidate_width: int = 6,
        node_budget: int = 20_000,
        exploration: float = 0.0,
    ):
        super().__init__(seed=seed, exploration=exploration)
        if belief_samples <= 0:
            raise ValueError("belief_samples must be positive")
        if rollout_plies <= 0:
            raise ValueError("rollout_plies must be positive")
        if candidate_width <= 0:
            raise ValueError("candidate_width must be positive")
        if node_budget <= 0:
            raise ValueError("node_budget must be positive")
        self.belief = BeliefSampler(engine, priors=priors)
        self.belief_samples = belief_samples
        self.rollout_plies = rollout_plies
        self.candidate_width = candidate_width
        self.node_budget = node_budget

    def choose(self, engine: GameEngine, state: GameState) -> Action:
        root_player = state.active_player
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
                "completed_depth": 0,
                "search_nodes": 0,
                "search_budget": self.node_budget,
                "evaluated_candidates": 1,
            }
            return actions[0]

        ordered_root = self._ordered_actions(
            engine,
            state,
            root_player,
            width=self.candidate_width,
        )
        candidates = list(ordered_root)

        # Pass and paid Draw are strategically unusual: their value is often
        # mostly beyond the immediate board. Never let beam pruning remove them.
        for action in actions:
            if isinstance(action, (Pass, Draw)) and action not in candidates:
                candidates.append(action)

        # Fallback scores are valid even if the node budget is too small to
        # complete depth 1.
        scores = {
            action: self._score_action(engine, state, root_player, action)
            for action in candidates
        }
        samples = [
            self.belief.sample(state, root_player, self.rng)
            for _ in range(self.belief_samples)
        ]

        budget = _SearchBudget(self.node_budget)
        completed_depth = 0
        transposition: dict[tuple[object, ...], float] = {}

        for depth in range(1, self.rollout_plies + 1):
            depth_scores: dict[Action, list[float]] = {
                action: [] for action in candidates
            }

            # Principal-variation ordering: after each complete iteration,
            # search the currently best root move first at the next depth.
            root_order = sorted(
                candidates,
                key=lambda action: (
                    -scores[action],
                    self._action_sort_key(action),
                ),
            )

            try:
                for sampled in samples:
                    for action in root_order:
                        child = sampled.clone()
                        engine.apply(child, action, validate=False)
                        value = self._alphabeta(
                            engine,
                            child,
                            root_player=root_player,
                            depth=depth - 1,
                            alpha=-inf,
                            beta=inf,
                            budget=budget,
                            transposition=transposition,
                        )
                        depth_scores[action].append(value)
            except _SearchLimit:
                break

            scores = {
                action: mean(values)
                for action, values in depth_scores.items()
            }
            completed_depth = depth

        ranked = [
            ScoredAction(action, scores[action])
            for action in candidates
        ]
        ranked.sort(
            key=lambda item: (
                -item.score,
                self._action_sort_key(item.action),
            )
        )
        selected = ranked[0]
        second = ranked[1].score if len(ranked) > 1 else selected.score
        self.last_decision = {
            "candidate_count": len(actions),
            "selected_score": selected.score,
            "score_gap": selected.score - second,
            "selected_action": type(selected.action).__name__,
            "policy_source": "strategic_heuristic",
            "belief_samples": self.belief_samples,
            "rollout_plies": self.rollout_plies,
            "completed_depth": completed_depth,
            "search_nodes": min(budget.nodes, self.node_budget),
            "search_budget": self.node_budget,
            "evaluated_candidates": len(candidates),
        }
        return selected.action

    def _alphabeta(
        self,
        engine: GameEngine,
        state: GameState,
        *,
        root_player: int,
        depth: int,
        alpha: float,
        beta: float,
        budget: _SearchBudget,
        transposition: dict[tuple[object, ...], float],
    ) -> float:
        budget.visit()

        if state.phase is Phase.COMPLETE or depth <= 0:
            return self._strategic_state_value(engine, state, root_player)

        cache_key = (
            depth,
            root_player,
            self._state_key(state),
        )
        cached = transposition.get(cache_key)
        if cached is not None:
            return cached

        actor = state.active_player
        actions = self._ordered_actions(
            engine,
            state,
            actor,
            width=self.candidate_width,
        )
        if not actions:
            return self._strategic_state_value(engine, state, root_player)

        maximizing = actor == root_player
        value = -inf if maximizing else inf
        cutoff = False

        for action in actions:
            child = state.clone()
            engine.apply(child, action, validate=False)
            child_value = self._alphabeta(
                engine,
                child,
                root_player=root_player,
                depth=depth - 1,
                alpha=alpha,
                beta=beta,
                budget=budget,
                transposition=transposition,
            )

            if maximizing:
                value = max(value, child_value)
                alpha = max(alpha, value)
            else:
                value = min(value, child_value)
                beta = min(beta, value)

            if beta <= alpha:
                cutoff = True
                break

        # Only cache exact values. A cutoff gives a bound, not an exact score.
        if not cutoff:
            transposition[cache_key] = value
        return value

    def _ordered_actions(
        self,
        engine: GameEngine,
        state: GameState,
        actor: int,
        *,
        width: int,
    ) -> list[Action]:
        actions = engine.legal_actions(state)
        if len(actions) <= width:
            return sorted(
                actions,
                key=lambda action: (
                    -self._score_action(engine, state, actor, action),
                    self._action_sort_key(action),
                ),
            )

        ranked = sorted(
            actions,
            key=lambda action: (
                -self._score_action(engine, state, actor, action),
                self._action_sort_key(action),
            ),
        )
        selected = list(ranked[:width])

        # Preserve long-horizon resource/tempo choices even if their one-ply
        # score is weak.
        for action in ranked[width:]:
            if isinstance(action, (Pass, Draw)) and action not in selected:
                selected.append(action)
        return selected

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

        # Reward progress toward complete formations, including Bonds/Names
        # prepared before their Force. This is where the one-ply evaluator is
        # weakest.
        value += 0.85 * (
            self._formation_progress(state, player)
            - self._formation_progress(state, opponent)
        )
        value += 0.30 * (
            self._hand_construction_value(engine, state, player)
            - self._hand_construction_value(engine, state, opponent)
        )

        if not engine.recycle_between_battles:
            value += 0.18 * (
                len(state.players[player].deck)
                - len(state.players[opponent].deck)
            )
            value += 0.55 * (
                self._future_formation_sets(engine, state, player)
                - self._future_formation_sets(engine, state, opponent)
            )
            value += 0.40 * (
                self._future_force_availability(engine, state, player)
                - self._future_force_availability(engine, state, opponent)
            )

        if engine.command_enabled:
            # Command saved now remains useful in later Battles. The public
            # evaluator already values current Command; this smaller term
            # specifically values future playable-card capacity.
            value += 0.12 * (
                self._affordable_hand_count(engine, state, player)
                - self._affordable_hand_count(engine, state, opponent)
            )

        return value

    @staticmethod
    def _formation_progress(state: GameState, player: int) -> float:
        value = 0.0
        for position in all_positions():
            slot = state.slot(player, position)
            components = sum(
                component is not None
                for component in (slot.subject, slot.link, slot.name)
            )
            if components == 1:
                value += 0.35
            elif components == 2:
                value += 1.35
            elif components == 3:
                value += 2.25
        return value

    @staticmethod
    def _affordable_hand_count(
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> int:
        if not engine.command_enabled:
            return len(state.players[player].hand)
        command = state.players[player].command
        return sum(
            int(engine.cards[card_id].get("command_cost", 0)) <= command
            for card_id in state.players[player].hand
        )

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

    @staticmethod
    def _action_sort_key(action: Action) -> str:
        return repr(action)

    @staticmethod
    def _state_key(state: GameState) -> tuple[object, ...]:
        players = tuple(
            (
                tuple(player.deck),
                tuple(sorted(player.hand)),
                tuple(player.discard),
                player.victories,
                player.passed,
                player.command,
                player.free_cycle,
            )
            for player in state.players
        )
        board = tuple(
            (
                slot.subject,
                slot.link,
                slot.name,
                slot.temporary_strength,
            )
            for side in state.board
            for front in side
            for slot in front
        )
        schemes = tuple(
            None if scheme is None else (scheme.card_id, scheme.revealed)
            for side in state.schemes
            for scheme in side
        )
        stratagems = tuple(
            None if stratagem is None else (stratagem.card_id, stratagem.revealed)
            for stratagem in state.stratagems
        )
        return (
            state.phase.value,
            state.active_player,
            state.battle,
            state.chooser,
            state.winner,
            state.shuffle_seed,
            players,
            board,
            schemes,
            stratagems,
            tuple(state.stratagem_used),
            tuple(state.draw_used),
            tuple(state.discarded_this_battle),
            tuple(state.pass_order),
            tuple(state.operations_this_battle),
            state.pending_final_operation_for,
        )
