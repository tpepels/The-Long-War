from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any

from .game.actions import (
    Action,
    Pass,
    PlayBond,
    PlayForce,
    PlayName,
    PlayStory,
    PlayStratagem,
)
from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState, Phase


@dataclass
class CardStats:
    draws: int = 0
    plays: int = 0
    turns_in_hand: int = 0
    playable_turns: int = 0
    unplayable_turns: int = 0
    held_on_pass: int = 0
    dead_on_pass: int = 0
    immediate_front_swing_total: float = 0.0
    immediate_control_swing_total: float = 0.0
    games_drawn: int = 0
    wins_when_drawn: int = 0
    games_played: int = 0
    wins_when_played: int = 0


@dataclass
class ComboStats:
    completions: int = 0
    strength_at_completion_total: float = 0.0
    games_seen: int = 0
    wins_when_seen: int = 0


@dataclass
class DecisionStats:
    decisions: int = 0
    candidate_count_total: int = 0
    score_gap_total: float = 0.0
    search_nodes_total: int = 0
    completed_depth_total: int = 0
    decision_seconds_total: float = 0.0
    decision_seconds_max: float = 0.0
    timed_out_decisions: int = 0
    searched_decisions: int = 0
    searched_decision_seconds_total: float = 0.0
    ismcts_terminal_cutoffs: int = 0
    ismcts_battle_boundary_cutoffs: int = 0
    ismcts_depth_cutoffs: int = 0
    ismcts_rollout_actions: int = 0
    ismcts_searched_decisions: int = 0
    ismcts_root_reused_decisions: int = 0
    ismcts_tree_nodes_before_total: int = 0
    ismcts_tree_nodes_added_total: int = 0
    ismcts_root_prior_visits_total: int = 0
    ismcts_tree_nodes_discarded_total: int = 0
    ismcts_tree_capacity_cutoffs: int = 0
    ismcts_tree_resets: Counter[str] = field(default_factory=Counter)


class Telemetry:
    """Aggregate telemetry across simulated matches."""

    def __init__(self) -> None:
        self.cards: dict[str, CardStats] = defaultdict(CardStats)
        self.combos: dict[str, ComboStats] = defaultdict(ComboStats)
        self.action_counts: Counter[str] = Counter()
        self.pass_events: list[dict[str, Any]] = []
        self.battle_records: list[dict[str, Any]] = []
        self.decision_stats: dict[str, DecisionStats] = defaultdict(DecisionStats)
        self.policy_sources: Counter[str] = Counter()
        self.search_backends: Counter[str] = Counter()
        self.online_resolution = {
            "decisions": 0,
            "iterations_total": 0.0,
            "belief_samples_total": 0.0,
            "information_sets_total": 0.0,
            "root_coverage_total": 0.0,
            "known_hidden_total": 0.0,
        }
        self.online_prior_counts: Counter[str] = Counter()

        self._drawn_this_game: list[set[str]] = [set(), set()]
        self._played_this_game: list[set[str]] = [set(), set()]
        self._combos_this_game: list[set[str]] = [set(), set()]
        self._battle_actions: list[int] = [0, 0]
        self._deck_exhausted_this_game: list[bool] = [False, False]
        self._deck_exhausted_player_games = 0
        self._reshuffled_this_game: list[bool] = [False, False]
        self._reshuffle_player_games = 0
        self._reshuffles_total = 0
        self._battle_decisions = 0
        self._deck_empty_decisions = 0
        self._match_count = 0

    def start_game(self, state: GameState) -> None:
        self._drawn_this_game = [set(), set()]
        self._played_this_game = [set(), set()]
        self._combos_this_game = [set(), set()]
        self._battle_actions = [0, 0]
        self._deck_exhausted_this_game = [False, False]
        self._reshuffled_this_game = [False, False]

        for player in range(2):
            for card_id in state.players[player].hand:
                self._record_draw(player, card_id)

    def before_action(
        self,
        engine: GameEngine,
        state: GameState,
        actor: int,
        action: Action,
        decision_info: dict[str, Any] | None,
    ) -> GameState:
        before = state.clone()
        self.action_counts[type(action).__name__] += 1

        if state.phase is Phase.BATTLE and state.pending_draw_discard_for is None:
            self._battle_actions[actor] += 1
            self._battle_decisions += 1
            if not state.players[actor].deck:
                self._deck_empty_decisions += 1
                if not engine.can_draw(state, actor):
                    self._deck_exhausted_this_game[actor] = True
            legal = engine.legal_actions(state)
            playable_ids = {
                card_id
                for legal_action in legal
                for card_id in [self._action_card_id(legal_action)]
                if card_id is not None
            }
            for card_id, copies in Counter(state.players[actor].hand).items():
                stats = self.cards[card_id]
                stats.turns_in_hand += copies
                if card_id in playable_ids:
                    stats.playable_turns += copies
                else:
                    stats.unplayable_turns += copies

            if isinstance(action, Pass):
                first_pass = len(state.pass_order) == 0
                margins = self._front_margins(engine, state, actor)
                pass_record = {
                    "battle": state.battle,
                    "player": actor,
                    "first_pass": first_pass,
                    "hand_size": len(state.players[actor].hand),
                    "deck_remaining": len(state.players[actor].deck),
                    "command_remaining": state.players[actor].command,
                    "controlled_fronts": sum(margin > 0 for margin in margins),
                    "tied_fronts": sum(margin == 0 for margin in margins),
                    "total_margin": sum(margins),
                    "actions_taken_this_battle": self._battle_actions[actor],
                    "dead_cards": 0,
                }

                for card_id, copies in Counter(state.players[actor].hand).items():
                    stats = self.cards[card_id]
                    stats.held_on_pass += copies
                    if card_id not in playable_ids:
                        stats.dead_on_pass += copies
                        pass_record["dead_cards"] += copies

                self.pass_events.append(pass_record)

        card_id = self._action_card_id(action)
        if card_id is not None:
            self.cards[card_id].plays += 1
            self._played_this_game[actor].add(card_id)

        if decision_info:
            agent_name = str(decision_info.get("agent", "unknown"))
            stats = self.decision_stats[agent_name]
            stats.decisions += 1
            stats.candidate_count_total += int(
                decision_info.get("candidate_count", 0)
            )
            stats.score_gap_total += float(decision_info.get("score_gap", 0.0))
            search_nodes = int(decision_info.get("search_nodes", 0))
            stats.search_nodes_total += search_nodes
            stats.completed_depth_total += int(
                decision_info.get("completed_depth", 0)
            )
            decision_seconds = float(decision_info.get("decision_seconds", 0.0) or 0.0)
            stats.decision_seconds_total += decision_seconds
            stats.decision_seconds_max = max(
                stats.decision_seconds_max,
                decision_seconds,
            )
            stats.timed_out_decisions += int(
                bool(decision_info.get("search_timed_out", False))
            )
            if search_nodes > 0:
                stats.searched_decisions += 1
                stats.searched_decision_seconds_total += decision_seconds
            stats.ismcts_terminal_cutoffs += int(
                decision_info.get("ismcts_rollouts_stopped_terminal", 0)
            )
            stats.ismcts_battle_boundary_cutoffs += int(
                decision_info.get(
                    "ismcts_rollouts_stopped_battle_boundary",
                    0,
                )
            )
            stats.ismcts_depth_cutoffs += int(
                decision_info.get("ismcts_rollouts_stopped_depth", 0)
            )
            stats.ismcts_rollout_actions += int(
                decision_info.get("ismcts_rollout_actions", 0)
            )
            ismcts_iterations = int(
                decision_info.get("ismcts_iterations", 0)
            )
            if ismcts_iterations > 0:
                stats.ismcts_searched_decisions += 1
                stats.ismcts_root_reused_decisions += int(
                    bool(decision_info.get("ismcts_root_reused", False))
                )
                stats.ismcts_tree_nodes_before_total += int(
                    decision_info.get("ismcts_tree_nodes_before", 0)
                )
                stats.ismcts_tree_nodes_added_total += int(
                    decision_info.get("ismcts_tree_nodes_added", 0)
                )
                stats.ismcts_root_prior_visits_total += int(
                    decision_info.get("ismcts_root_prior_visits", 0)
                )
                stats.ismcts_tree_nodes_discarded_total += int(
                    decision_info.get("ismcts_tree_nodes_discarded", 0)
                )
                stats.ismcts_tree_capacity_cutoffs += int(
                    decision_info.get("ismcts_tree_capacity_cutoffs", 0)
                )
                reason = str(decision_info.get("ismcts_tree_reset_reason", "none"))
                if reason != "none":
                    stats.ismcts_tree_resets[reason] += 1
            search_backend = decision_info.get("search_backend")
            if search_backend is not None:
                self.search_backends[str(search_backend)] += 1
            policy_source = decision_info.get("policy_source")
            if policy_source is not None:
                self.policy_sources[str(policy_source)] += 1
            if policy_source == "online_mccfr":
                self.online_resolution["decisions"] += 1
                self.online_resolution["iterations_total"] += float(
                    decision_info.get("resolver_iterations", 0)
                )
                self.online_resolution["belief_samples_total"] += float(
                    decision_info.get("belief_samples", 0)
                )
                self.online_resolution["information_sets_total"] += float(
                    decision_info.get("resolver_information_sets", 0)
                )
                self.online_resolution["root_coverage_total"] += float(
                    decision_info.get("root_coverage", 0.0)
                )
                self.online_resolution["known_hidden_total"] += float(
                    decision_info.get("known_hidden_cards", 0)
                )
                prior = decision_info.get("belief_prior")
                if prior is not None:
                    self.online_prior_counts[str(prior)] += 1

        return before

    def after_action(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
        actor: int,
        action: Action,
    ) -> None:
        self._record_new_draws(before, state)
        for player in range(2):
            delta = state.deck_reshuffles[player] - before.deck_reshuffles[player]
            if delta > 0:
                self._reshuffles_total += delta
                self._reshuffled_this_game[player] = True

        card_id = self._action_card_id(action)
        if (
            card_id is not None
            and before.phase is Phase.BATTLE
            and before.pending_draw_discard_for is None
        ):
            before_margin = sum(self._front_margins(engine, before, actor))
            after_margin = sum(self._front_margins(engine, state, actor))
            before_control = self._control_balance(engine, before, actor)
            after_control = self._control_balance(engine, state, actor)
            stats = self.cards[card_id]
            stats.immediate_front_swing_total += after_margin - before_margin
            stats.immediate_control_swing_total += after_control - before_control

        self._record_new_completions(engine, before, state, actor)

        battle_resolved = (
            before.phase is Phase.BATTLE
            and (
                state.phase is Phase.COMPLETE
                or state.battle != before.battle
            )
        )
        if battle_resolved:
            self._record_battle(engine, before, state)
            self._battle_actions = [0, 0]

    def finish_game(self, winner: int) -> None:
        self._match_count += 1
        self._deck_exhausted_player_games += sum(self._deck_exhausted_this_game)
        self._reshuffle_player_games += sum(self._reshuffled_this_game)
        for player in range(2):
            for card_id in self._drawn_this_game[player]:
                stats = self.cards[card_id]
                stats.games_drawn += 1
                if player == winner:
                    stats.wins_when_drawn += 1

            for card_id in self._played_this_game[player]:
                stats = self.cards[card_id]
                stats.games_played += 1
                if player == winner:
                    stats.wins_when_played += 1

            for combo in self._combos_this_game[player]:
                stats = self.combos[combo]
                stats.games_seen += 1
                if player == winner:
                    stats.wins_when_seen += 1

    def summary(self) -> dict[str, Any]:
        cards: dict[str, Any] = {}
        for card_id, stats in sorted(self.cards.items()):
            payload = asdict(stats)
            payload["plays_per_draw"] = self._ratio(stats.plays, stats.draws)
            payload["play_rate_per_draw"] = self._ratio(
                stats.games_played,
                stats.games_drawn,
            )
            payload["unplayable_turn_rate"] = self._ratio(
                stats.unplayable_turns,
                stats.turns_in_hand,
            )
            payload["dead_on_pass_rate"] = self._ratio(
                stats.dead_on_pass,
                stats.held_on_pass,
            )
            payload["mean_immediate_front_swing"] = self._ratio(
                stats.immediate_front_swing_total,
                stats.plays,
            )
            payload["mean_immediate_control_swing"] = self._ratio(
                stats.immediate_control_swing_total,
                stats.plays,
            )
            payload["win_rate_when_drawn"] = self._ratio(
                stats.wins_when_drawn,
                stats.games_drawn,
            )
            payload["win_rate_when_played"] = self._ratio(
                stats.wins_when_played,
                stats.games_played,
            )
            cards[card_id] = payload

        combos: dict[str, Any] = {}
        for combo, stats in sorted(self.combos.items()):
            payload = asdict(stats)
            payload["mean_strength_at_completion"] = self._ratio(
                stats.strength_at_completion_total,
                stats.completions,
            )
            payload["win_rate_when_seen"] = self._ratio(
                stats.wins_when_seen,
                stats.games_seen,
            )
            combos[combo] = payload

        pass_summary = {
            "events": len(self.pass_events),
            "mean_hand_size": self._mean_field(self.pass_events, "hand_size"),
            "mean_command_remaining": self._mean_field(
                self.pass_events,
                "command_remaining",
            ),
            "mean_deck_remaining": self._mean_field(
                self.pass_events,
                "deck_remaining",
            ),
            "command_exhausted_rate": self._ratio(
                sum(
                    event["command_remaining"] == 0
                    for event in self.pass_events
                ),
                len(self.pass_events),
            ),
            "mean_dead_cards": self._mean_field(self.pass_events, "dead_cards"),
            "mean_actions_before_pass": self._mean_field(
                self.pass_events,
                "actions_taken_this_battle",
            ),
            "first_pass_rate": self._ratio(
                sum(event["first_pass"] for event in self.pass_events),
                len(self.pass_events),
            ),
        }

        continuing_battles = [
            record
            for record in self.battle_records
            if record["next_battle_hand_total"] is not None
        ]
        battles = {
            "count": len(self.battle_records),
            "mean_actions": self._mean_field(self.battle_records, "actions"),
            "mean_total_strength": self._mean_field(
                self.battle_records,
                "total_strength",
            ),
            "mean_abs_total_margin": self._mean_field(
                self.battle_records,
                "abs_total_margin",
            ),
            "continuing_battles": len(continuing_battles),
            "mean_next_battle_hand_size": self._ratio(
                sum(record["next_battle_hand_total"] for record in continuing_battles),
                2 * len(continuing_battles),
            ),
            "mean_next_battle_hand_shortfall": self._ratio(
                sum(record["next_battle_hand_shortfall"] for record in continuing_battles),
                2 * len(continuing_battles),
            ),
            "next_battle_player_shortfall_rate": self._ratio(
                sum(record["next_battle_players_below_target"] for record in continuing_battles),
                2 * len(continuing_battles),
            ),
        }

        command = {
            "mean_start_per_player": self._ratio(
                sum(record["command_start_total"] for record in self.battle_records),
                2 * len(self.battle_records),
            ),
            "mean_spent_per_player": self._ratio(
                sum(record["command_spent_total"] for record in self.battle_records),
                2 * len(self.battle_records),
            ),
            "mean_refunded_per_player": self._ratio(
                sum(record["command_refunded_total"] for record in self.battle_records),
                2 * len(self.battle_records),
            ),
            "mean_remaining_at_battle_end_per_player": self._ratio(
                sum(record["command_remaining_total"] for record in self.battle_records),
                2 * len(self.battle_records),
            ),
            "mean_next_battle_command_per_player": self._ratio(
                sum(
                    record["next_battle_command_total"]
                    for record in continuing_battles
                ),
                2 * len(continuing_battles),
            ),
        }

        decisions: dict[str, Any] = {}
        for agent, stats in sorted(self.decision_stats.items()):
            cutoff_total = (
                stats.ismcts_terminal_cutoffs
                + stats.ismcts_battle_boundary_cutoffs
                + stats.ismcts_depth_cutoffs
            )
            decisions[agent] = {
                "decisions": stats.decisions,
                "mean_candidate_count": self._ratio(
                    stats.candidate_count_total,
                    stats.decisions,
                ),
                "mean_score_gap": self._ratio(
                    stats.score_gap_total,
                    stats.decisions,
                ),
                "mean_search_nodes": self._ratio(
                    stats.search_nodes_total,
                    stats.decisions,
                ),
                "mean_completed_depth": self._ratio(
                    stats.completed_depth_total,
                    stats.decisions,
                ),
                "mean_decision_seconds": self._ratio(
                    stats.decision_seconds_total,
                    stats.decisions,
                ),
                "max_decision_seconds": stats.decision_seconds_max,
                "timed_out_decisions": stats.timed_out_decisions,
                "timeout_rate": self._ratio(
                    stats.timed_out_decisions,
                    stats.decisions,
                ),
                "searched_decisions": stats.searched_decisions,
                "mean_searched_decision_seconds": self._ratio(
                    stats.searched_decision_seconds_total,
                    stats.searched_decisions,
                ),
            }
            if stats.ismcts_searched_decisions:
                decisions[agent]["ismcts_tree_reuse"] = {
                    "searched_decisions": stats.ismcts_searched_decisions,
                    "root_reused_decisions": stats.ismcts_root_reused_decisions,
                    "root_reuse_rate": self._ratio(
                        stats.ismcts_root_reused_decisions,
                        stats.ismcts_searched_decisions,
                    ),
                    "tree_nodes_before_total": stats.ismcts_tree_nodes_before_total,
                    "tree_nodes_added_total": stats.ismcts_tree_nodes_added_total,
                    "root_prior_visits_total": stats.ismcts_root_prior_visits_total,
                    "tree_nodes_discarded_total": stats.ismcts_tree_nodes_discarded_total,
                    "tree_capacity_cutoffs": stats.ismcts_tree_capacity_cutoffs,
                    "tree_resets": dict(stats.ismcts_tree_resets),
                    "mean_tree_nodes_before": self._ratio(
                        stats.ismcts_tree_nodes_before_total,
                        stats.ismcts_searched_decisions,
                    ),
                    "mean_tree_nodes_added": self._ratio(
                        stats.ismcts_tree_nodes_added_total,
                        stats.ismcts_searched_decisions,
                    ),
                    "mean_root_prior_visits": self._ratio(
                        stats.ismcts_root_prior_visits_total,
                        stats.ismcts_searched_decisions,
                    ),
                }
            if cutoff_total:
                decisions[agent]["ismcts_rollout_cutoffs"] = {
                    "iterations": cutoff_total,
                    "terminal": stats.ismcts_terminal_cutoffs,
                    "battle_boundary": stats.ismcts_battle_boundary_cutoffs,
                    "depth": stats.ismcts_depth_cutoffs,
                    "terminal_rate": self._ratio(
                        stats.ismcts_terminal_cutoffs,
                        cutoff_total,
                    ),
                    "battle_boundary_rate": self._ratio(
                        stats.ismcts_battle_boundary_cutoffs,
                        cutoff_total,
                    ),
                    "depth_rate": self._ratio(
                        stats.ismcts_depth_cutoffs,
                        cutoff_total,
                    ),
                    "rollout_actions": stats.ismcts_rollout_actions,
                    "mean_rollout_actions_per_iteration": self._ratio(
                        stats.ismcts_rollout_actions,
                        cutoff_total,
                    ),
                }

        online_decisions = int(self.online_resolution["decisions"])
        online_summary = {
            "decisions": online_decisions,
            "mean_iterations": self._ratio(
                self.online_resolution["iterations_total"],
                online_decisions,
            ),
            "mean_belief_samples": self._ratio(
                self.online_resolution["belief_samples_total"],
                online_decisions,
            ),
            "mean_information_sets": self._ratio(
                self.online_resolution["information_sets_total"],
                online_decisions,
            ),
            "mean_root_coverage": self._ratio(
                self.online_resolution["root_coverage_total"],
                online_decisions,
            ),
            "mean_known_hidden_cards": self._ratio(
                self.online_resolution["known_hidden_total"],
                online_decisions,
            ),
            "belief_priors": dict(sorted(self.online_prior_counts.items())),
        }

        depletion = {
            "deck_empty_decision_rate": self._ratio(
                self._deck_empty_decisions,
                self._battle_decisions,
            ),
            "player_game_deck_exhaustion_rate": self._ratio(
                self._deck_exhausted_player_games,
                2 * self._match_count,
            ),
            "player_game_reshuffle_rate": self._ratio(
                self._reshuffle_player_games,
                2 * self._match_count,
            ),
            "mean_reshuffles_per_player_game": self._ratio(
                self._reshuffles_total,
                2 * self._match_count,
            ),
            "mean_deck_remaining_at_pass": self._mean_field(
                self.pass_events,
                "deck_remaining",
            ),
            "mean_deck_remaining_at_battle_end_per_player": self._ratio(
                sum(record["deck_remaining_total"] for record in self.battle_records),
                2 * len(self.battle_records),
            ),
            "mean_next_battle_deck_per_player": self._ratio(
                sum(
                    record["next_battle_deck_total"]
                    for record in continuing_battles
                ),
                2 * len(continuing_battles),
            ),
        }

        return {
            "actions": dict(sorted(self.action_counts.items())),
            "passes": pass_summary,
            "battles": battles,
            "command": command,
            "depletion": depletion,
            "cards": cards,
            "legend_combinations": combos,
            "decisions": decisions,
            "policy_sources": dict(sorted(self.policy_sources.items())),
            "search_backends": dict(sorted(self.search_backends.items())),
            "online_resolution": online_summary,
            "match_flow": {
                "matches": self._match_count,
            },
        }

    def _record_draw(self, player: int, card_id: str) -> None:
        self.cards[card_id].draws += 1
        self._drawn_this_game[player].add(card_id)

    def _record_new_draws(
        self,
        before: GameState,
        state: GameState,
    ) -> None:
        battle_changed = (
            before.phase is Phase.BATTLE
            and (
                state.phase is Phase.COMPLETE
                or state.battle != before.battle
            )
        )
        if battle_changed:
            for player in range(2):
                added = Counter(state.players[player].hand) - Counter(
                    before.players[player].hand
                )
                for card_id, count in added.items():
                    for _ in range(count):
                        self._record_draw(player, card_id)
            return

        for player in range(2):
            if state.deck_reshuffles[player] > before.deck_reshuffles[player]:
                added = Counter(state.players[player].hand) - Counter(
                    before.players[player].hand
                )
                for card_id, count in added.items():
                    for _ in range(count):
                        self._record_draw(player, card_id)
                continue

            count = len(before.players[player].deck) - len(state.players[player].deck)
            if count <= 0:
                continue
            drawn = list(reversed(before.players[player].deck[-count:]))
            for card_id in drawn:
                self._record_draw(player, card_id)

    def _record_new_completions(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
        actor: int,
    ) -> None:
        before_counts = Counter(
            self._complete_legend(before, actor, position)
            for position in all_positions()
        )
        after_entries = [
            (position, self._complete_legend(state, actor, position))
            for position in all_positions()
        ]
        after_counts = Counter(combo for _, combo in after_entries)

        new_counts = after_counts - before_counts
        for combo, count in new_counts.items():
            if combo is None:
                continue
            remaining = count
            for position, candidate in after_entries:
                if remaining <= 0:
                    break
                if candidate != combo:
                    continue
                combo_key = " | ".join(combo)
                stats = self.combos[combo_key]
                stats.completions += 1
                stats.strength_at_completion_total += engine.position_strength(
                    state,
                    actor,
                    position,
                )
                self._combos_this_game[actor].add(combo_key)
                remaining -= 1

    @staticmethod
    def _complete_legend(
        state: GameState,
        player: int,
        position,
    ) -> tuple[str, str, str] | None:
        slot = state.slot(player, position)
        if not slot.complete:
            return None
        return (slot.force, slot.bond, slot.name)

    def _record_battle(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
    ) -> None:
        snapshot = state.last_battle_snapshot or {}
        front_scores = snapshot.get("front_scores", [])
        front_results = snapshot.get("front_results", [])
        fronts_lost = snapshot.get("fronts_lost", [0, 0])

        next_hand_sizes = (
            None
            if state.phase is Phase.COMPLETE
            else [len(player.hand) for player in state.players]
        )
        next_command = (
            None
            if state.phase is Phase.COMPLETE
            else [player.command for player in state.players]
        )
        next_decks = (
            None
            if state.phase is Phase.COMPLETE
            else [len(player.deck) for player in state.players]
        )

        total_strength = sum(
            int(score)
            for pair in front_scores
            for score in pair
        )
        total_margin = sum(
            abs(int(pair[0]) - int(pair[1]))
            for pair in front_scores
        )

        self.battle_records.append(
            {
                "battle": before.battle,
                "front_scores": front_scores,
                "front_results": front_results,
                "fronts_lost": fronts_lost,
                "actions": sum(self._battle_actions),
                "actions_p0": self._battle_actions[0],
                "actions_p1": self._battle_actions[1],
                "total_strength": total_strength,
                "abs_total_margin": total_margin,
                "command_start_total": sum(before.battle_start_command),
                "command_spent_total": sum(before.command_spent_this_battle),
                "command_refunded_total": sum(before.command_refunded_this_battle),
                "command_remaining_total": sum(
                    int(value)
                    for value in snapshot.get(
                        "command_remaining",
                        [player.command for player in state.players],
                    )
                ),
                "deck_remaining_total": sum(
                    int(value)
                    for value in snapshot.get(
                        "deck_remaining",
                        [len(player.deck) for player in state.players],
                    )
                ),
                "players_with_empty_deck": sum(
                    not player.deck for player in before.players
                ),
                "next_battle_command_total": (
                    0 if next_command is None else sum(next_command)
                ),
                "next_battle_deck_total": (
                    0 if next_decks is None else sum(next_decks)
                ),
                "next_battle_hand_total": (
                    None if next_hand_sizes is None else sum(next_hand_sizes)
                ),
                "next_battle_hand_shortfall": (
                    None
                    if next_hand_sizes is None
                    else sum(
                        max(0, engine.hand_limit - size)
                        for size in next_hand_sizes
                    )
                ),
                "next_battle_players_below_target": (
                    None
                    if next_hand_sizes is None
                    else sum(size < engine.hand_limit for size in next_hand_sizes)
                ),
            }
        )

    @staticmethod
    def _action_card_id(action: Action) -> str | None:
        if isinstance(
            action,
            (PlayForce, PlayBond, PlayName, PlayStory, PlayStratagem),
        ):
            return action.card_id
        return None

    @staticmethod
    def _front_margins(
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> list[int]:
        opponent = 1 - player
        return [
            engine.front_strength(state, player, front)
            - engine.front_strength(state, opponent, front)
            for front in Front
        ]

    def _control_balance(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
    ) -> int:
        margins = self._front_margins(engine, state, player)
        return sum(margin > 0 for margin in margins) - sum(
            margin < 0 for margin in margins
        )

    @staticmethod
    def _ratio(numerator: float, denominator: float) -> float | None:
        if denominator == 0:
            return None
        return numerator / denominator

    @staticmethod
    def _mean_field(rows: list[dict[str, Any]], field: str) -> float | None:
        values = [float(row[field]) for row in rows]
        return mean(values) if values else None

    @staticmethod
    def _bool_rate(rows: list[dict[str, Any]], field: str) -> float | None:
        if not rows:
            return None
        return sum(bool(row[field]) for row in rows) / len(rows)
