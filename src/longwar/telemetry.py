from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from statistics import mean
from typing import Any

from .game.actions import (
    Action,
    EffectChoice,
    Maneuver,
    Pass,
    PlayBond,
    PlayForce,
    PlayName,
    PlayStory,
    PlayStratagem,
)
from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState, Phase
from .progression import ProgressionTelemetry
from .heuristics import command_preserving_actions


@dataclass
class CardStats:
    draws: int = 0
    plays: int = 0
    turns_in_hand: int = 0
    playable_turns: int = 0
    unplayable_turns: int = 0
    affordable_turns: int = 0
    unaffordable_turns: int = 0
    structurally_unplayable_turns: int = 0
    hero_allowance_blocked_turns: int = 0
    hero_command_blocked_turns: int = 0
    hero_structural_blocked_turns: int = 0
    held_on_pass: int = 0
    dead_on_pass: int = 0
    affordable_on_pass: int = 0
    unaffordable_on_pass: int = 0
    structurally_dead_on_pass: int = 0
    hero_allowance_blocked_on_pass: int = 0
    hero_command_blocked_on_pass: int = 0
    hero_structural_blocked_on_pass: int = 0
    immediate_front_swing_total: float = 0.0
    immediate_control_swing_total: float = 0.0
    games_drawn: int = 0
    decisive_games_drawn: int = 0
    wins_when_drawn: int = 0
    games_played: int = 0
    decisive_games_played: int = 0
    wins_when_played: int = 0


@dataclass
class ComboStats:
    completions: int = 0
    strength_at_completion_total: float = 0.0
    games_seen: int = 0
    decisive_games_seen: int = 0
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
    command_guard_decisions: int = 0
    command_guard_filtered_actions: int = 0
    command_guard_overrides: int = 0
    searched_decisions: int = 0
    searched_decision_seconds_total: float = 0.0
    ismcts_terminal_cutoffs: int = 0
    ismcts_battle_boundary_cutoffs: int = 0
    ismcts_depth_cutoffs: int = 0
    ismcts_rollout_actions: int = 0
    ismcts_decisive_rollout_probes: int = 0
    ismcts_decisive_rollout_actions: int = 0
    ismcts_anti_decisive_rollout_probes: int = 0
    ismcts_anti_decisive_rollout_filtered: int = 0
    ismcts_iterations_total: int = 0
    ismcts_setup_seconds_total: float = 0.0
    ismcts_search_seconds_total: float = 0.0
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
        self.progression = ProgressionTelemetry()
        self._progression_started = False

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

    def merge(self, other: "Telemetry") -> None:
        """Merge completed-match telemetry from an independent worker."""
        for card_id, source in other.cards.items():
            target = self.cards[card_id]
            for field_name in CardStats.__dataclass_fields__:
                setattr(
                    target,
                    field_name,
                    getattr(target, field_name) + getattr(source, field_name),
                )
        for combo_id, source in other.combos.items():
            target = self.combos[combo_id]
            for field_name in ComboStats.__dataclass_fields__:
                setattr(
                    target,
                    field_name,
                    getattr(target, field_name) + getattr(source, field_name),
                )
        self.action_counts.update(other.action_counts)
        self.pass_events.extend(other.pass_events)
        self.battle_records.extend(other.battle_records)

        for agent, source in other.decision_stats.items():
            target = self.decision_stats[agent]
            for field_name in DecisionStats.__dataclass_fields__:
                if field_name == "decision_seconds_max":
                    target.decision_seconds_max = max(
                        target.decision_seconds_max,
                        source.decision_seconds_max,
                    )
                elif field_name == "ismcts_tree_resets":
                    target.ismcts_tree_resets.update(source.ismcts_tree_resets)
                else:
                    setattr(
                        target,
                        field_name,
                        getattr(target, field_name) + getattr(source, field_name),
                    )

        self.policy_sources.update(other.policy_sources)
        self.search_backends.update(other.search_backends)
        for key in self.online_resolution:
            self.online_resolution[key] += other.online_resolution[key]
        self.online_prior_counts.update(other.online_prior_counts)
        self.progression.merge(other.progression)
        self._deck_exhausted_player_games += other._deck_exhausted_player_games
        self._reshuffle_player_games += other._reshuffle_player_games
        self._reshuffles_total += other._reshuffles_total
        self._battle_decisions += other._battle_decisions
        self._deck_empty_decisions += other._deck_empty_decisions
        self._match_count += other._match_count
        self._progression_started = self._progression_started or other._progression_started

    def start_game(
        self,
        state: GameState,
        engine: GameEngine | None = None,
        *,
        simulation_game_index: int | None = None,
        seed: int | None = None,
        first_player: int | None = None,
    ) -> None:
        self._drawn_this_game = [set(), set()]
        self._played_this_game = [set(), set()]
        self._combos_this_game = [set(), set()]
        self._battle_actions = [0, 0]
        self._deck_exhausted_this_game = [False, False]
        self._reshuffled_this_game = [False, False]
        self._progression_started = False

        if engine is not None:
            self.progression.start_game(
                engine,
                state,
                simulation_game_index=simulation_game_index,
                seed=seed,
                first_player=first_player,
            )
            self._progression_started = True

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
        legal: list[Action] = []
        if state.phase is Phase.BATTLE:
            legal = engine.legal_actions(state)
        if not self._progression_started:
            self.progression.start_game(engine, state)
            self._progression_started = True

        pass_record: dict[str, Any] | None = None
        effect_resolution = (
            isinstance(action, EffectChoice)
            or (
                bool(legal)
                and all(isinstance(candidate, EffectChoice) for candidate in legal)
            )
        )
        operation_decision = (
            state.phase is Phase.BATTLE
            and state.pending_draw_discard_for is None
            and not effect_resolution
        )
        if operation_decision:
            self._battle_actions[actor] += 1
            self._battle_decisions += 1
            if not state.players[actor].deck:
                self._deck_empty_decisions += 1
                if not engine.can_draw(state, actor):
                    self._deck_exhausted_this_game[actor] = True

            playable_ids = {
                card_id
                for legal_action in legal
                for card_id in [self._action_card_id(legal_action)]
                if card_id is not None
            }
            command = int(state.players[actor].command)
            hand = Counter(state.players[actor].hand)
            hero_block_reasons: dict[str, str] = {}
            for card_id, copies in hand.items():
                stats = self.cards[card_id]
                stats.turns_in_hand += copies
                cost = int(engine.cards.get(card_id, {}).get("command_cost", 0) or 0)
                affordable = command >= cost
                block_reason = None
                if (
                    card_id not in playable_ids
                    and engine.cards.get(card_id, {}).get("hero")
                ):
                    block_reason = self._hero_block_reason(
                        engine, state, actor, card_id
                    )
                    hero_block_reasons[card_id] = block_reason
                    if block_reason == "hero_allowance":
                        stats.hero_allowance_blocked_turns += copies
                        affordable = True
                    elif block_reason == "command":
                        stats.hero_command_blocked_turns += copies
                        affordable = False
                    else:
                        stats.hero_structural_blocked_turns += copies

                if affordable:
                    stats.affordable_turns += copies
                else:
                    stats.unaffordable_turns += copies
                if card_id in playable_ids:
                    stats.playable_turns += copies
                else:
                    stats.unplayable_turns += copies
                    # The one-Hero-from-hand allowance is not structural card
                    # illegality and must not create false dead-draw warnings.
                    if affordable and block_reason != "hero_allowance":
                        stats.structurally_unplayable_turns += copies

            if isinstance(action, Pass):
                new_signal = not state.players[actor].passed
                first_pass = new_signal and len(state.pass_order) == 0
                margins = self._front_margins(engine, state, actor)
                preserving, exhausting_alternatives = command_preserving_actions(
                    engine,
                    state,
                    legal,
                )
                exhausting_alternatives = int(exhausting_alternatives)
                paid_alternatives = sum(
                    not isinstance(candidate, Pass)
                    and engine.command_cost_for_action(state, candidate) > 0
                    for candidate in legal
                )
                pass_record = {
                    "battle": state.battle,
                    "player": actor,
                    "first_pass": first_pass,
                    "new_signal": new_signal,
                    "forced_yield": not new_signal,
                    "free_signal": (
                        new_signal
                        and not engine.rules.pass_signal_costs_operation
                    ),
                    "hand_size": len(state.players[actor].hand),
                    "deck_remaining": len(state.players[actor].deck),
                    "command_remaining": command,
                    "controlled_fronts": sum(margin > 0 for margin in margins),
                    "tied_fronts": sum(margin == 0 for margin in margins),
                    "lost_fronts": sum(margin < 0 for margin in margins),
                    "total_margin": sum(margins),
                    "actions_taken_this_battle": self._battle_actions[actor],
                    "playable_cards_remaining": len(playable_ids),
                    "legal_alternatives": sum(
                        not isinstance(candidate, Pass) for candidate in legal
                    ),
                    "paid_alternatives": paid_alternatives,
                    "command_exhausting_alternatives": exhausting_alternatives,
                    "pass_avoids_command_exhaustion": (
                        exhausting_alternatives > 0 and action in preserving
                    ),
                    "playable_card_actions": sum(
                        self._action_card_id(candidate) is not None
                        for candidate in legal
                    ),
                    "maneuver_actions": sum(
                        isinstance(candidate, Maneuver) for candidate in legal
                    ),
                    "dead_cards": 0,
                    "structurally_dead_cards": 0,
                    "unaffordable_cards": 0,
                    "affordable_cards": 0,
                }

                for card_id, copies in hand.items():
                    stats = self.cards[card_id]
                    stats.held_on_pass += copies
                    cost = int(engine.cards.get(card_id, {}).get("command_cost", 0) or 0)
                    affordable = command >= cost
                    block_reason = hero_block_reasons.get(card_id)
                    if block_reason == "hero_allowance":
                        affordable = True
                    elif block_reason == "command":
                        affordable = False
                    if affordable:
                        stats.affordable_on_pass += copies
                        pass_record["affordable_cards"] += copies
                    else:
                        stats.unaffordable_on_pass += copies
                        pass_record["unaffordable_cards"] += copies
                    if card_id not in playable_ids:
                        stats.dead_on_pass += copies
                        pass_record["dead_cards"] += copies
                        if block_reason == "hero_allowance":
                            stats.hero_allowance_blocked_on_pass += copies
                        elif block_reason == "command":
                            stats.hero_command_blocked_on_pass += copies
                        elif block_reason == "structural":
                            stats.hero_structural_blocked_on_pass += copies
                        if affordable and block_reason != "hero_allowance":
                            stats.structurally_dead_on_pass += copies
                            pass_record["structurally_dead_cards"] += copies

                pass_record["unplayable_cards_remaining"] = pass_record["dead_cards"]
                self.pass_events.append(pass_record)

        card_id = self._action_card_id(action)
        if card_id is not None:
            self.cards[card_id].plays += 1
            self._played_this_game[actor].add(card_id)

        self.progression.before_action(
            engine,
            state,
            actor,
            action,
            legal,
            pass_context=pass_record,
        )

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
            guarded_actions = int(
                decision_info.get("command_guard_filtered_actions", 0)
            )
            if guarded_actions > 0:
                stats.command_guard_decisions += 1
                stats.command_guard_filtered_actions += guarded_actions
            stats.command_guard_overrides += int(
                bool(
                    decision_info.get(
                        "command_guard_overrode_selection",
                        decision_info.get(
                            "command_guard_overrode_search",
                            False,
                        ),
                    )
                )
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
            stats.ismcts_decisive_rollout_probes += int(
                decision_info.get("ismcts_decisive_rollout_probes", 0)
            )
            stats.ismcts_decisive_rollout_actions += int(
                decision_info.get("ismcts_decisive_rollout_actions", 0)
            )
            stats.ismcts_anti_decisive_rollout_probes += int(
                decision_info.get("ismcts_anti_decisive_rollout_probes", 0)
            )
            stats.ismcts_anti_decisive_rollout_filtered += int(
                decision_info.get("ismcts_anti_decisive_rollout_filtered", 0)
            )
            ismcts_iterations = int(
                decision_info.get("ismcts_iterations", 0)
            )
            if ismcts_iterations > 0:
                stats.ismcts_iterations_total += ismcts_iterations
                stats.ismcts_setup_seconds_total += float(
                    decision_info.get("ismcts_setup_seconds", 0.0)
                )
                stats.ismcts_search_seconds_total += float(
                    decision_info.get("ismcts_search_seconds", 0.0)
                )
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
        self.progression.after_action(engine, before, state, actor, action)

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

    def finish_game(
        self,
        winner: int | None,
        state: GameState | None = None,
        *,
        censored: bool = False,
    ) -> None:
        self._match_count += 1
        self.progression.finish_game(state, censored=censored)
        self._deck_exhausted_player_games += sum(self._deck_exhausted_this_game)
        self._reshuffle_player_games += sum(self._reshuffled_this_game)
        for player in range(2):
            for card_id in self._drawn_this_game[player]:
                stats = self.cards[card_id]
                stats.games_drawn += 1
                if winner is not None:
                    stats.decisive_games_drawn += 1
                    if player == winner:
                        stats.wins_when_drawn += 1

            for card_id in self._played_this_game[player]:
                stats = self.cards[card_id]
                stats.games_played += 1
                if winner is not None:
                    stats.decisive_games_played += 1
                    if player == winner:
                        stats.wins_when_played += 1

            for combo in self._combos_this_game[player]:
                stats = self.combos[combo]
                stats.games_seen += 1
                if winner is not None:
                    stats.decisive_games_seen += 1
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
            payload["structural_unplayable_turn_rate"] = self._ratio(
                stats.structurally_unplayable_turns,
                stats.affordable_turns - stats.hero_allowance_blocked_turns,
            )
            payload["resource_blocked_turn_rate"] = self._ratio(
                stats.unaffordable_turns,
                stats.turns_in_hand,
            )
            payload["hero_allowance_blocked_turn_rate"] = self._ratio(
                stats.hero_allowance_blocked_turns,
                stats.turns_in_hand,
            )
            payload["hero_command_blocked_turn_rate"] = self._ratio(
                stats.hero_command_blocked_turns,
                stats.turns_in_hand,
            )
            payload["hero_structural_blocked_turn_rate"] = self._ratio(
                stats.hero_structural_blocked_turns,
                stats.turns_in_hand,
            )
            payload["dead_on_pass_rate"] = self._ratio(
                stats.dead_on_pass,
                stats.held_on_pass,
            )
            payload["structural_dead_on_pass_rate"] = self._ratio(
                stats.structurally_dead_on_pass,
                stats.affordable_on_pass - stats.hero_allowance_blocked_on_pass,
            )
            payload["resource_blocked_on_pass_rate"] = self._ratio(
                stats.unaffordable_on_pass,
                stats.held_on_pass,
            )
            payload["hero_allowance_blocked_on_pass_rate"] = self._ratio(
                stats.hero_allowance_blocked_on_pass,
                stats.held_on_pass,
            )
            payload["hero_command_blocked_on_pass_rate"] = self._ratio(
                stats.hero_command_blocked_on_pass,
                stats.held_on_pass,
            )
            payload["hero_structural_blocked_on_pass_rate"] = self._ratio(
                stats.hero_structural_blocked_on_pass,
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
                stats.decisive_games_drawn,
            )
            payload["win_rate_when_played"] = self._ratio(
                stats.wins_when_played,
                stats.decisive_games_played,
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
                stats.decisive_games_seen,
            )
            combos[combo] = payload

        signal_events = [
            event
            for event in self.pass_events
            if bool(event.get("new_signal", True))
        ]
        forced_yields = [
            event
            for event in self.pass_events
            if bool(event.get("forced_yield", False))
        ]
        free_signals = [
            event
            for event in signal_events
            if bool(event.get("free_signal", False))
        ]

        pass_summary = {
            "events": len(self.pass_events),
            "signal_events": len(signal_events),
            "forced_yield_events": len(forced_yields),
            "free_signal_events": len(free_signals),
            "mean_hand_size": self._mean_field(self.pass_events, "hand_size"),
            "mean_command_remaining": self._mean_field(
                self.pass_events,
                "command_remaining",
            ),
            "mean_command_at_signal": self._mean_field(
                signal_events,
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
            "mean_structurally_dead_cards": self._mean_field(
                self.pass_events, "structurally_dead_cards"
            ),
            "mean_unaffordable_cards": self._mean_field(
                self.pass_events, "unaffordable_cards"
            ),
            "mean_affordable_cards": self._mean_field(
                self.pass_events, "affordable_cards"
            ),
            "mean_playable_cards_remaining": self._mean_field(
                self.pass_events,
                "playable_cards_remaining",
            ),
            "mean_legal_alternatives": self._mean_field(
                self.pass_events,
                "legal_alternatives",
            ),
            "mean_playable_card_actions": self._mean_field(
                self.pass_events,
                "playable_card_actions",
            ),
            "mean_maneuver_actions": self._mean_field(
                self.pass_events,
                "maneuver_actions",
            ),
            "no_alternative_rate": self._ratio(
                sum(event["legal_alternatives"] == 0 for event in self.pass_events),
                len(self.pass_events),
            ),
            "playable_alternative_rate": self._ratio(
                sum(event["playable_card_actions"] > 0 for event in self.pass_events),
                len(self.pass_events),
            ),
            "signal_with_playable_alternative_rate": self._ratio(
                sum(event["playable_card_actions"] > 0 for event in signal_events),
                len(signal_events),
            ),
            "paid_alternative_rate": self._ratio(
                sum(event.get("paid_alternatives", 0) > 0 for event in self.pass_events),
                len(self.pass_events),
            ),
            "command_exhausting_alternative_rate": self._ratio(
                sum(
                    event.get("command_exhausting_alternatives", 0) > 0
                    for event in self.pass_events
                ),
                len(self.pass_events),
            ),
            "pass_avoids_command_exhaustion_rate": self._ratio(
                sum(
                    bool(event.get("pass_avoids_command_exhaustion"))
                    for event in self.pass_events
                ),
                len(self.pass_events),
            ),
            "mean_actions_before_pass": self._mean_field(
                self.pass_events,
                "actions_taken_this_battle",
            ),
            "first_pass_rate": self._ratio(
                sum(event["first_pass"] for event in self.pass_events),
                len(self.pass_events),
            ),
            "first_signal_rate": self._ratio(
                sum(event["first_pass"] for event in signal_events),
                len(signal_events),
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
                "command_guard_decisions": stats.command_guard_decisions,
                "command_guard_opportunity_rate": self._ratio(
                    stats.command_guard_decisions,
                    stats.decisions,
                ),
                "command_guard_filtered_actions": (
                    stats.command_guard_filtered_actions
                ),
                "command_guard_overrides": stats.command_guard_overrides,
                "command_guard_override_rate": self._ratio(
                    stats.command_guard_overrides,
                    stats.command_guard_decisions,
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
                    "iterations_total": stats.ismcts_iterations_total,
                    "setup_seconds_total": stats.ismcts_setup_seconds_total,
                    "search_seconds_total": stats.ismcts_search_seconds_total,
                    "simulations_per_second": self._ratio(
                        stats.ismcts_iterations_total,
                        stats.ismcts_search_seconds_total,
                    ),
                    "mean_setup_seconds": self._ratio(
                        stats.ismcts_setup_seconds_total,
                        stats.ismcts_searched_decisions,
                    ),
                    "mean_search_seconds": self._ratio(
                        stats.ismcts_search_seconds_total,
                        stats.ismcts_searched_decisions,
                    ),
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
                    "rollout_actions": stats.ismcts_rollout_actions,
                    "decisive_probes": stats.ismcts_decisive_rollout_probes,
                    "decisive_actions": stats.ismcts_decisive_rollout_actions,
                    "decisive_probe_hit_rate": self._ratio(
                        stats.ismcts_decisive_rollout_actions,
                        stats.ismcts_decisive_rollout_probes,
                    ),
                    "decisive_action_rate": self._ratio(
                        stats.ismcts_decisive_rollout_actions,
                        stats.ismcts_rollout_actions,
                    ),
                    "anti_decisive_probes": (
                        stats.ismcts_anti_decisive_rollout_probes
                    ),
                    "anti_decisive_filtered": (
                        stats.ismcts_anti_decisive_rollout_filtered
                    ),
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
            "formation_combinations": combos,
            "progression": self.progression.summary(),
            "decisions": decisions,
            "policy_sources": dict(sorted(self.policy_sources.items())),
            "search_backends": dict(sorted(self.search_backends.items())),
            "online_resolution": online_summary,
            "match_flow": {
                "matches": self._match_count,
            },
        }

    def _hero_block_reason(
        self,
        engine: GameEngine,
        state: GameState,
        actor: int,
        card_id: str,
    ) -> str:
        """Classify why a Hero in hand has no legal play.

        "hero_allowance" means restoring only the once-per-Battle Hero
        allowance makes the card legal at current Command. "command" means
        the card becomes legal only after also restoring Command. Everything
        else is structural, including placement and active constraints.
        """
        allowance_probe = state.clone()
        allowance_probe.hero_used[actor] = False
        allowance_legal = engine.legal_actions(allowance_probe)
        if any(
            self._action_card_id(candidate) == card_id
            for candidate in allowance_legal
        ):
            return "hero_allowance"

        command_probe = allowance_probe.clone()
        command_probe.players[actor].command = engine.rules.command_cap
        command_legal = engine.legal_actions(command_probe)
        if any(
            self._action_card_id(candidate) == card_id
            for candidate in command_legal
        ):
            return "command"
        return "structural"

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
                if state.deck_reshuffles[player] > before.deck_reshuffles[player]:
                    self.progression.note_reshuffle(
                        player,
                        before.players[player].discard,
                    )
                added = Counter(state.players[player].hand) - Counter(
                    before.players[player].hand
                )
                for card_id, count in added.items():
                    for _ in range(count):
                        self._record_draw(player, card_id)
                        self.progression.record_draw(player, card_id, state)
            return

        for player in range(2):
            if state.deck_reshuffles[player] > before.deck_reshuffles[player]:
                self.progression.note_reshuffle(
                    player,
                    before.players[player].discard,
                )
                added = Counter(state.players[player].hand) - Counter(
                    before.players[player].hand
                )
                for card_id, count in added.items():
                    for _ in range(count):
                        self._record_draw(player, card_id)
                        self.progression.record_draw(player, card_id, state)
                continue

            count = len(before.players[player].deck) - len(state.players[player].deck)
            if count <= 0:
                continue
            drawn = list(reversed(before.players[player].deck[-count:]))
            for card_id in drawn:
                self._record_draw(player, card_id)
                self.progression.record_draw(player, card_id, state)

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
                    max(
                        0,
                        int(before.battle_start_command[player])
                        - int(before.command_spent_this_battle[player])
                        + int(before.command_refunded_this_battle[player]),
                    )
                    for player in range(2)
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
