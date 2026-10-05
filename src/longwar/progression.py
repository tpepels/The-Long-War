from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, median
from typing import Any, Iterable

from .game.actions import (
    Action,
    EffectChoice,
    Maneuver,
    Pass,
    PlayBond,
    PlayForce,
    PlayName,
    PlayNarrative,
    PlayStratagem,
    action_key,
)
from .game.engine import GameEngine, all_positions
from .game.model import ConstraintKind, Front, GameState, Phase, Position, RANK_COUNT
from .protocol import (
    CardField,
    CommandDiagnosticDetail,
    CommandDiagnosticKind,
    PLAYER_COUNT,
)


CARD_ACTIONS = (PlayForce, PlayBond, PlayName, PlayNarrative, PlayStratagem)
OPERATION_ACTIONS = CARD_ACTIONS + (Maneuver,)
CONSTRAINT_CLASSES = {"necessity"}


def _new_hero_mode() -> dict[str, Any]:
    return {
        "force_plays": 0,
        "name_plays": 0,
        "force_completions": 0,
        "name_completions": 0,
        "force_front_swing_total": 0.0,
        "name_front_swing_total": 0.0,
        "force_control_swing_total": 0.0,
        "name_control_swing_total": 0.0,
        "force_battle_end_presence": 0,
        "name_battle_end_presence": 0,
        "by_battle": defaultdict(Counter),
    }


class ProgressionTelemetry:
    """Compact, mechanics-only match-progression telemetry.

    This class deliberately records what the engine exposes. Constraint-rule
    cards may be present in a state without being counted as an active
    constraint: effect-active telemetry requires an explicit engine state
    marker, and does not infer rules from prose.
    """

    def __init__(self) -> None:
        self._game_index = -1
        self._simulation_game_index: int | None = None
        self._game_seed: int | None = None
        self._first_player: int | None = None
        self._action_index = 0
        self._current_action = 0
        self._battle_action = 0
        self._battle_number = 1
        self._collapse_threshold: int | None = None

        self._next_formation_id = 1
        self._formation_at: dict[tuple[int, Position], int] = {}
        self._formations: dict[int, dict[str, Any]] = {}

        self._battle_events: Counter[str] = Counter()
        self._battle_operation_trace: list[dict[str, Any]] = []
        self._battle_snapshots: list[dict[str, Any]] = []
        self._battle_records: list[dict[str, Any]] = []
        self._match_records: list[dict[str, Any]] = []
        self._game_battle_record_start = 0
        self._sample_traces: list[dict[str, Any]] = []
        self._last_controllers: tuple[int, ...] | None = None
        self._last_control_balance: int | None = None
        self._last_lead_sign: int | None = None
        self._battle_control_changes = 0
        self._battle_control_balance_changes = 0
        self._battle_lead_changes = 0

        self._choice_legal: list[int] = []
        self._choice_card: list[int] = []
        self._choice_maneuver: list[int] = []
        self._forced_decisions = 0
        self._forced_maneuvers = 0
        self._constraint_source_decisions = 0
        self._constraint_active_decisions = 0
        self._constraint_effect_choice_decisions = 0
        self._constraint_source_effect_choice_decisions = 0
        self._effect_choice_decisions = 0
        self._constraint_active_supported = False
        self._constraint_active_streak = 0
        self._constraint_active_streaks: list[int] = []
        self._constraint_source_active: Counter[str] = Counter()
        self._constraint_kind_active: Counter[str] = Counter()
        self._constraint_satisfied: Counter[str] = Counter()
        self._constraint_impossible: Counter[str] = Counter()
        self._constraint_expired = 0
        self._constraint_options_removed: list[int] = []
        self._constraint_options_added: list[int] = []
        self._constraint_forced_maneuver_decisions = 0
        self._constraint_forced_front_decisions = 0
        self._constraint_carried_between_battles = 0
        self._constraint_future_operations_affected = 0
        self._pass_contexts: list[dict[str, Any]] = []

        self._command_spend: Counter[str] = Counter()
        self._command_spend_by_battle: dict[str, Counter[str]] = defaultdict(Counter)
        self._command_gained = 0
        self._free_operations = 0
        self._free_maneuvers = 0
        self._discount_actions = 0
        self._discount_command = 0
        self._command_by_source: dict[str, Counter[str]] = defaultdict(Counter)
        self._command_effects_by_source: dict[str, Counter[str]] = defaultdict(Counter)

        self._hero_modes: dict[str, dict[str, Any]] = defaultdict(_new_hero_mode)

        self._draw_queues: dict[tuple[int, str], list[tuple[int, int, int]]] = defaultdict(list)
        self._reshuffled_pending: list[Counter[str]] = [Counter() for _ in range(PLAYER_COUNT)]
        self._card_actions_to_play: dict[str, list[int]] = defaultdict(list)
        self._card_turns_to_play: dict[str, list[int]] = defaultdict(list)
        self._card_held_boundaries: Counter[str] = Counter()
        self._card_discarded_unplayed: Counter[str] = Counter()
        self._card_drawn_after_reshuffle: Counter[str] = Counter()
        self._card_unplayed_match_end: Counter[str] = Counter()
        self._card_plays_by_battle: dict[str, Counter[str]] = defaultdict(Counter)
        self._formation_age_at_battle_end: list[int] = []

    def merge(self, other: "ProgressionTelemetry") -> None:
        """Merge completed-match telemetry from an independent worker."""
        if self._collapse_threshold is None:
            self._collapse_threshold = other._collapse_threshold
        elif (
            other._collapse_threshold is not None
            and self._collapse_threshold != other._collapse_threshold
        ):
            raise ValueError("Cannot merge progression telemetry from different collapse thresholds")
        if self._constraint_active_streak:
            self._constraint_active_streaks.append(self._constraint_active_streak)
            self._constraint_active_streak = 0
        self._constraint_active_streaks.extend(other._constraint_active_streaks)
        if other._constraint_active_streak:
            self._constraint_active_streaks.append(other._constraint_active_streak)

        game_offset = self._game_index + 1
        for row in other._match_records:
            merged = dict(row)
            merged["game"] = game_offset + int(row.get("game", 0))
            self._match_records.append(merged)
        for row in other._battle_records:
            merged = dict(row)
            merged["game"] = game_offset + int(row.get("game", 0))
            self._battle_records.append(merged)
        for row in other._pass_contexts:
            merged = dict(row)
            merged["game"] = game_offset + int(row.get("game", 0))
            self._pass_contexts.append(merged)
        self._game_index += other._game_index + 1

        for row in other._formations.values():
            merged = dict(row)
            merged["id"] = self._next_formation_id
            merged["game"] = game_offset + int(row.get("game", 0))
            self._formations[self._next_formation_id] = merged
            self._next_formation_id += 1

        if len(self._sample_traces) < 240:
            for row in other._sample_traces[: 240 - len(self._sample_traces)]:
                merged = dict(row)
                if "game" in merged:
                    merged["game"] = game_offset + int(merged["game"])
                self._sample_traces.append(merged)

        for name in ("_choice_legal", "_choice_card", "_choice_maneuver",
                     "_constraint_options_removed", "_constraint_options_added",
                     "_formation_age_at_battle_end"):
            getattr(self, name).extend(getattr(other, name))

        for name in (
            "_forced_decisions", "_forced_maneuvers",
            "_constraint_source_decisions", "_constraint_active_decisions",
            "_constraint_effect_choice_decisions",
            "_constraint_source_effect_choice_decisions", "_effect_choice_decisions",
            "_constraint_expired", "_constraint_forced_maneuver_decisions",
            "_constraint_forced_front_decisions", "_constraint_carried_between_battles",
            "_constraint_future_operations_affected", "_command_gained",
            "_free_operations", "_free_maneuvers", "_discount_actions",
            "_discount_command",
        ):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        self._constraint_active_supported = (
            self._constraint_active_supported or other._constraint_active_supported
        )

        for name in (
            "_constraint_source_active", "_constraint_kind_active",
            "_constraint_satisfied", "_constraint_impossible", "_command_spend",
            "_card_held_boundaries", "_card_discarded_unplayed",
            "_card_drawn_after_reshuffle", "_card_unplayed_match_end",
        ):
            getattr(self, name).update(getattr(other, name))
        for source, counts in other._command_by_source.items():
            self._command_by_source[source].update(counts)
        for source, counts in other._command_effects_by_source.items():
            self._command_effects_by_source[source].update(counts)

        for battle, counts in other._command_spend_by_battle.items():
            self._command_spend_by_battle[battle].update(counts)
        for battle, counts in other._card_plays_by_battle.items():
            self._card_plays_by_battle[battle].update(counts)
        for card_id, values in other._card_actions_to_play.items():
            self._card_actions_to_play[card_id].extend(values)
        for card_id, values in other._card_turns_to_play.items():
            self._card_turns_to_play[card_id].extend(values)

        scalar_hero_fields = (
            "force_plays", "name_plays", "force_completions", "name_completions",
            "force_front_swing_total", "name_front_swing_total",
            "force_control_swing_total", "name_control_swing_total",
            "force_battle_end_presence", "name_battle_end_presence",
        )
        for card_id, source in other._hero_modes.items():
            target = self._hero_modes[card_id]
            for field in scalar_hero_fields:
                target[field] += source[field]
            for battle, counts in source["by_battle"].items():
                target["by_battle"][battle].update(counts)

    def start_game(
        self,
        engine: GameEngine,
        state: GameState,
        *,
        simulation_game_index: int | None = None,
        seed: int | None = None,
        first_player: int | None = None,
    ) -> None:
        threshold = int(engine.rules.command_collapse_threshold)
        if self._collapse_threshold is None:
            self._collapse_threshold = threshold
        elif self._collapse_threshold != threshold:
            raise ValueError("Progression telemetry cannot mix collapse thresholds")
        if self._constraint_active_streak:
            self._constraint_active_streaks.append(self._constraint_active_streak)
            self._constraint_active_streak = 0
        self._game_index += 1
        self._simulation_game_index = (
            None if simulation_game_index is None else int(simulation_game_index)
        )
        self._game_seed = None if seed is None else int(seed)
        self._first_player = None if first_player is None else int(first_player)
        self._constraint_active_supported = (
            self._constraint_active_supported
            or hasattr(state, "constraints")
        )
        self._game_battle_record_start = len(self._battle_records)
        self._action_index = 0
        self._current_action = 0
        self._battle_action = 0
        self._battle_number = state.battle
        self._formation_at = {}
        self._battle_events = Counter()
        self._battle_operation_trace = []
        self._battle_snapshots = []
        self._last_controllers = None
        self._last_control_balance = None
        self._last_lead_sign = None
        self._battle_control_changes = 0
        self._battle_control_balance_changes = 0
        self._battle_lead_changes = 0
        self._draw_queues = defaultdict(list)
        self._reshuffled_pending = [Counter() for _ in range(PLAYER_COUNT)]

        for player in range(PLAYER_COUNT):
            for card_id in state.players[player].hand:
                self.record_draw(player, card_id, state)
        self._initialize_formations(engine, state)

    def record_draw(self, player: int, card_id: str, state: GameState) -> None:
        entry = (self._current_action, int(state.turn_number), int(state.battle))
        self._draw_queues[(player, card_id)].append(entry)
        pending = self._reshuffled_pending[player]
        if pending.get(card_id, 0) > 0:
            self._card_drawn_after_reshuffle[card_id] += 1
            pending[card_id] -= 1
            if pending[card_id] <= 0:
                del pending[card_id]

    def note_reshuffle(self, player: int, card_ids: Iterable[str]) -> None:
        self._reshuffled_pending[player].update(card_ids)

    def before_action(
        self,
        engine: GameEngine,
        state: GameState,
        actor: int,
        action: Action,
        legal_actions: Iterable[Action],
        pass_context: dict[str, Any] | None = None,
    ) -> None:
        if state.phase is not Phase.BATTLE:
            return
        if state.pending_draw_discard_for is not None:
            self._current_action = self._action_index
            return

        self._current_action = self._action_index + 1
        legal = list(legal_actions)
        consumes_operation = engine.action_consumes_operation(
            state,
            actor,
            action,
        )
        constraint_sources = self._constraint_rule_sources(engine, state)
        active_constraints = self._active_operation_constraints(state, actor)
        constraint_active = bool(active_constraints)
        unconstrained_legal = legal
        if active_constraints and consumes_operation:
            unconstrained = state.clone()
            unconstrained.constraints.clear()
            unconstrained_legal = engine.legal_actions(unconstrained)

            before_count = len(unconstrained_legal)
            after_count = len(legal)
            self._constraint_options_removed.append(max(0, before_count - after_count))
            self._constraint_options_added.append(max(0, after_count - before_count))
            self._constraint_future_operations_affected += 1

            for item in active_constraints:
                source = str(item.source_card)
                kind = item.kind.value
                self._constraint_source_active[source] += 1
                self._constraint_kind_active[kind] += 1
                satisfiable = any(
                    self._constraint_matches_action(item, candidate)
                    for candidate in legal
                )
                if satisfiable:
                    if self._constraint_matches_action(item, action):
                        self._constraint_satisfied[kind] += 1
                else:
                    self._constraint_impossible[kind] += 1

            if (
                len(legal) == 1
                and isinstance(legal[0], Maneuver)
                and any(
                    item.kind in {
                        ConstraintKind.MANEUVER,
                        ConstraintKind.SPECIFIC_MANEUVER,
                    }
                    for item in active_constraints
                )
            ):
                self._constraint_forced_maneuver_decisions += 1
            if any(
                item.kind is ConstraintKind.AFFECT_FRONT
                for item in active_constraints
            ):
                self._constraint_forced_front_decisions += 1
        effect_resolution = (
            isinstance(action, EffectChoice)
            or (
                bool(legal)
                and all(isinstance(candidate, EffectChoice) for candidate in legal)
            )
        )
        self._battle_operation_trace.append({
            "player": int(actor),
            "action": action_key(action),
            "category": (
                "effect_choice"
                if effect_resolution
                else "pass"
                if isinstance(action, Pass)
                else "maneuver"
                if isinstance(action, Maneuver)
                else "card"
                if isinstance(action, CARD_ACTIONS)
                else type(action).__name__
            ),
            "operation": consumes_operation,
            "forced": len(legal) == 1,
            "legal_actions": len(legal),
            "playable_card_actions": sum(
                isinstance(candidate, CARD_ACTIONS)
                for candidate in legal
            ),
            "maneuver_actions": sum(
                isinstance(candidate, Maneuver)
                for candidate in legal
            ),
            "command_before": int(state.players[actor].command),
            "hand_before": len(state.players[actor].hand),
            "deck_before": len(state.players[actor].deck),
        })
        if effect_resolution:
            self._effect_choice_decisions += 1
            self._battle_events["effect_choices"] += 1
            if len(legal) == 1:
                self._battle_events["forced_effect_choices"] += 1
            self._constraint_source_effect_choice_decisions += int(
                bool(constraint_sources)
            )
            self._constraint_effect_choice_decisions += int(
                self._constraint_active_supported and constraint_active
            )
            if self._constraint_active_supported and constraint_active:
                self._constraint_active_streak += 1
            elif self._constraint_active_streak:
                self._constraint_active_streaks.append(self._constraint_active_streak)
                self._constraint_active_streak = 0
            return

        if consumes_operation:
            self._battle_action += 1
            card_actions = [
                candidate
                for candidate in legal
                if isinstance(candidate, CARD_ACTIONS)
            ]
            maneuver_actions = [
                candidate
                for candidate in legal
                if isinstance(candidate, Maneuver)
            ]
            self._choice_legal.append(len(legal))
            self._choice_card.append(len(card_actions))
            self._choice_maneuver.append(len(maneuver_actions))
            self._forced_decisions += int(len(legal) == 1)
            self._forced_maneuvers += int(
                len(legal) == 1 and isinstance(legal[0], Maneuver)
            )
            self._constraint_source_decisions += int(bool(constraint_sources))
            if self._constraint_active_supported:
                self._constraint_active_decisions += int(constraint_active)
            if self._constraint_active_supported and constraint_active:
                self._constraint_active_streak += 1
            elif self._constraint_active_streak:
                self._constraint_active_streaks.append(
                    self._constraint_active_streak
                )
                self._constraint_active_streak = 0

        if isinstance(action, CARD_ACTIONS):
            card_id = action.card_id
            queue = self._draw_queues.get((actor, card_id), [])
            if queue:
                drawn_action, drawn_turn, _drawn_battle = queue.pop(0)
                self._card_actions_to_play[card_id].append(
                    max(0, self._current_action - drawn_action)
                )
                self._card_turns_to_play[card_id].append(
                    max(0, int(state.turn_number) - drawn_turn)
                )
            self._card_plays_by_battle[card_id][self._battle_key(state.battle)] += 1

        if pass_context is not None:
            alternatives_count = int(pass_context.get("legal_alternatives", 0))
            pass_context.update({
                "game": self._game_index,
                "simulation_game_index": self._simulation_game_index,
                "seed": self._game_seed,
                "first_player": self._first_player,
                "command_remaining": pass_context.get(
                    "command_remaining", state.players[actor].command
                ),
                "constraint_active": constraint_active,
                "constraint_rule_sources": constraint_sources,
                "mechanical_category": (
                    "no_alternative"
                    if alternatives_count == 0
                    else "one_alternative"
                    if alternatives_count == 1
                    else "multiple_alternatives"
                ),
                "final_front_balance": None,
            })
            self._pass_contexts.append(pass_context)

        snapshot = self._snapshot(
            engine,
            state,
            actor=actor,
            legal_count=len(legal),
            constraint_active=constraint_active,
            constraint_sources=constraint_sources,
        )
        self._battle_snapshots.append(snapshot)
        if self._game_index < 3 and len(self._sample_traces) < 240:
            self._sample_traces.append(snapshot)

        controllers = tuple(snapshot["front_controllers"])
        if self._last_controllers is not None:
            self._battle_control_changes += sum(
                before != after
                for before, after in zip(self._last_controllers, controllers)
            )
        self._last_controllers = controllers

        control_balance = snapshot["controlled_fronts"][0] - snapshot["controlled_fronts"][1]
        if (
            self._last_control_balance is not None
            and control_balance != self._last_control_balance
        ):
            self._battle_control_balance_changes += 1
        self._last_control_balance = control_balance

        lead_sign = self._sign(snapshot["total_strength"][0] - snapshot["total_strength"][1])
        if self._last_lead_sign not in (None, 0) and lead_sign not in (0, self._last_lead_sign):
            self._battle_lead_changes += 1
        if lead_sign != 0:
            self._last_lead_sign = lead_sign

        if isinstance(action, PlayForce):
            self._battle_events["forces_played"] += 1
        elif isinstance(action, PlayBond):
            self._battle_events["bonds_played"] += 1
        elif isinstance(action, PlayName):
            self._battle_events["names_played"] += 1
        if isinstance(action, CARD_ACTIONS):
            self._battle_events["cards_played"] += 1
        if isinstance(action, Maneuver):
            self._battle_events["maneuvers"] += 1

    def after_action(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
        actor: int,
        action: Action,
    ) -> None:
        if before.phase is Phase.BATTLE:
            self._record_command_flow(engine, before, state, actor, action)
            self._record_hero_action(engine, before, state, actor, action)

        battle_resolved = (
            before.phase is Phase.BATTLE
            and (state.phase is Phase.COMPLETE or state.battle != before.battle)
        )
        battle_end_ages = (
            [
                self._current_action - self._formations[formation_id]["created_action"]
                for formation_id in set(self._formation_at.values())
            ]
            if battle_resolved
            else []
        )
        new_completions = self._reconcile_formations(
            engine,
            before,
            state,
            actor,
            action,
            battle_resolved=battle_resolved,
        )
        self._battle_events["completed_formations"] += new_completions

        self._record_unplayed_discards(before, state, action)

        if battle_resolved:
            self._record_held_across_boundary(before, state)
            self._formation_age_at_battle_end.extend(battle_end_ages)
            self._record_battle_end(engine, before, state)
            self._constraint_carried_between_battles += len(state.constraints)
            self._reset_battle(state)

        if before.phase is Phase.BATTLE and not isinstance(action, EffectChoice):
            before_active = self._active_operation_constraints(before, actor)
            after_keys = {
                self._constraint_identity(item)
                for item in state.constraints
            }
            self._constraint_expired += sum(
                self._constraint_identity(item) not in after_keys
                for item in before_active
            )

        self._action_index = self._current_action

    def finish_game(
        self,
        state: GameState | None = None,
        *,
        censored: bool = False,
    ) -> None:
        if state is not None:
            for player in range(PLAYER_COUNT):
                for card_id, count in Counter(state.players[player].hand).items():
                    self._card_unplayed_match_end[card_id] += count
            self._match_records.append({
                "game": self._game_index,
                "simulation_game_index": self._simulation_game_index,
                "seed": self._game_seed,
                "first_player": self._first_player,
                "resolved_battles": (
                    len(self._battle_records) - self._game_battle_record_start
                ),
                "final_battle": int(state.battle),
                "final_command": [int(player.command) for player in state.players],
                "censored": bool(censored),
            })

    @staticmethod
    def _battle_record_view(row: dict[str, Any]) -> dict[str, Any]:
        """Return a summary-safe view of a Battle record.

        Battle telemetry is append-only: new diagnostic fields must not make
        older retained records or focused unit fixtures invalid. Missing
        diagnostics stay unknown (None) rather than being interpreted as false.
        """
        view = dict(row)
        view.setdefault("game", 0)
        view.setdefault("simulation_game_index", None)
        view.setdefault("seed", None)
        view.setdefault("first_player", None)
        if "actions_taken" not in view:
            view["actions_taken"] = view.get("operations_taken", [0, 0])
        view.setdefault("operations_taken", view["actions_taken"])
        if "action_trace" not in view:
            view["action_trace"] = view.get("operation_trace", [])
        view.setdefault("operation_trace", view["action_trace"])
        if "paid_actions" not in view:
            view["paid_actions"] = view.get("paid_operations", 0)
        view.setdefault("paid_operations", view["paid_actions"])
        if "free_actions" not in view:
            view["free_actions"] = view.get("free_operations", 0)
        view.setdefault("free_operations", view["free_actions"])
        if "paid_card_actions" not in view:
            view["paid_card_actions"] = view.get("paid_card_operations", 0)
        view.setdefault("paid_card_operations", view["paid_card_actions"])
        if "free_card_actions" not in view:
            view["free_card_actions"] = view.get("free_card_operations", 0)
        view.setdefault("free_card_operations", view["free_card_actions"])
        view.setdefault("pass_diagnostics", [])
        view.setdefault("paid_maneuvers", 0)
        view.setdefault("effect_choices", 0)
        view.setdefault("forced_effect_choices", 0)
        if "no_paid_action" not in view:
            view["no_paid_action"] = view.get("no_paid_operation")
        view.setdefault("no_paid_operation", view["no_paid_action"])
        view.setdefault("board_changed", None)
        view.setdefault("board_changed_during_battle", None)
        view.setdefault("board_changed_during_resolution", None)
        view.setdefault("strength_changed", None)
        view.setdefault("strength_changed_during_battle", None)
        view.setdefault("strength_changed_during_resolution", None)
        view.setdefault("command_changed_before_collapse", None)
        view.setdefault("command_changed", None)
        view.setdefault("forced_passes", 0)
        view.setdefault("passes_with_no_playable_alternative", 0)
        if "command_after_recovery" not in view:
            view["command_after_recovery"] = view.get("next_battle_command")
        view.setdefault(
            "command_before_collapse",
            view.get("command_remaining"),
        )
        return view

    @staticmethod
    def _match_record_view(row: dict[str, Any]) -> dict[str, Any]:
        """Keep match-summary metadata append-only for retained evidence."""
        view = dict(row)
        view.setdefault("game", 0)
        view.setdefault("simulation_game_index", None)
        view.setdefault("seed", None)
        view.setdefault("first_player", None)
        view.setdefault("censored", False)
        view.setdefault("resolved_battles", 0)
        return view

    def summary(self) -> dict[str, Any]:
        lifecycles = list(self._formations.values())
        forces = len(lifecycles)
        ever_bonded = sum(row["bond_action"] is not None for row in lifecycles)
        ever_named = sum(row["name_action"] is not None for row in lifecycles)
        bonded = [row for row in lifecycles if row["bond_action"] is not None]
        completed = [row for row in lifecycles if row["completion_action"] is not None]
        removed_incomplete = [
            row for row in lifecycles
            if row["removed_action"] is not None and row["completion_action"] is None
        ]
        removed_incomplete_during_battle = list(removed_incomplete)
        # Compatibility field for older dashboards. Canonical playtest rules
        # never clear an incomplete formation merely because a Battle ends.
        cleared_incomplete_at_battle_end: list[dict[str, Any]] = []

        force_to_bond = [
            row["bond_action"] - row["created_action"]
            for row in bonded
        ]
        force_to_name = [
            row["name_action"] - row["created_action"]
            for row in lifecycles
            if row["name_action"] is not None
        ]
        bond_to_name = [
            row["name_action"] - row["bond_action"]
            for row in lifecycles
            if row["name_action"] is not None and row["bond_action"] is not None
            and row["name_action"] >= row["bond_action"]
        ]
        completion_age = [
            row["completion_action"] - row["created_action"]
            for row in completed
        ]
        removal_age = [
            row["removed_action"] - row["created_action"]
            for row in lifecycles
            if row["removed_action"] is not None
        ]

        battle_records = [
            self._battle_record_view(row)
            for row in self._battle_records
        ]
        by_battle = self._summarize_battles(battle_records)
        match_records = [
            self._match_record_view(row)
            for row in self._match_records
        ]
        final_battles = [row["final_battle"] for row in match_records]
        censored_final_battles = [
            row["final_battle"] for row in match_records if row["censored"]
        ]
        battle_reach = {}
        for battle in (1, 2, 3, 4, 8, 12):
            reached = sum(row["final_battle"] >= battle for row in match_records)
            battle_reach[str(battle)] = {
                "matches": reached,
                "rate": self._ratio(reached, len(match_records)),
            }
        threshold = (
            int(self._collapse_threshold)
            if self._collapse_threshold is not None
            else 0
        )
        rows_by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in battle_records:
            rows_by_game[int(row.get("game", 0))].append(row)

        low_positive_streaks: list[int] = []
        longest_low_positive_by_game: dict[int, int] = {}
        for game, game_rows in rows_by_game.items():
            current = 0
            longest = 0
            for row in sorted(game_rows, key=lambda item: int(item["battle"])):
                commands = row.get("command_before_collapse") or []
                low_positive = (
                    len(commands) == 2
                    and all(1 <= int(value) <= 3 for value in commands)
                )
                if low_positive:
                    current += 1
                    longest = max(longest, current)
                elif current:
                    low_positive_streaks.append(current)
                    current = 0
            if current:
                low_positive_streaks.append(current)
            longest_low_positive_by_game[game] = longest

        stall_rows = [
            row
            for row in battle_records
            if (
                any(value <= threshold for value in row["command_start"])
                or bool((row.get("collapse_comparison") or {}).get("triggered"))
            )
        ]
        match_by_game = {
            int(row["game"]): row
            for row in match_records
        }
        low_command_games = []
        for game, game_rows in sorted(rows_by_game.items()):
            game_rows = sorted(game_rows, key=lambda row: int(row["battle"]))
            diagnostic_rows = [
                row
                for row in game_rows
                if (
                    any(value <= threshold for value in row["command_start"])
                    or bool((row.get("collapse_comparison") or {}).get("triggered"))
                )
            ]
            if not diagnostic_rows:
                continue

            match = match_by_game.get(game, {})
            identity_row = diagnostic_rows[0]
            low_command_games.append({
                "game": game,
                "simulation_game_index": match.get(
                    "simulation_game_index",
                    identity_row.get("simulation_game_index"),
                ),
                "seed": match.get("seed", identity_row.get("seed")),
                "first_player": match.get(
                    "first_player",
                    identity_row.get("first_player"),
                ),
                "censored": bool(match.get("censored", False)),
                "final_battle": match.get("final_battle"),
                "resolved_battles": match.get("resolved_battles"),
                "diagnostic_battles": len(diagnostic_rows),
                "first_low_command_battle": min(
                    int(row["battle"]) for row in diagnostic_rows
                ),
                "both_at_collapse_point_battle_starts": sum(
                    all(value <= threshold for value in row["command_start"])
                    for row in diagnostic_rows
                ),
                "battles_with_no_paid_action": sum(
                    bool(row.get("no_paid_action", row.get("no_paid_operation")))
                    for row in diagnostic_rows
                ),
                "battles_with_no_paid_operation": sum(
                    bool(row.get("no_paid_action", row.get("no_paid_operation")))
                    for row in diagnostic_rows
                ),
                "battles_with_no_board_change": sum(
                    row.get("board_changed") is False
                    for row in diagnostic_rows
                ),
                "battles_with_no_strength_change": sum(
                    row.get("strength_changed") is False
                    for row in diagnostic_rows
                ),
            })

        censored_game_diagnostics = []
        for match in match_records:
            if not match.get("censored"):
                continue
            game = int(match.get("game", 0))
            game_rows = sorted(
                rows_by_game.get(game, []),
                key=lambda row: int(row.get("battle", 0)),
            )
            tail = game_rows[-8:]
            censored_game_diagnostics.append({
                "game": game,
                "simulation_game_index": match.get("simulation_game_index"),
                "seed": match.get("seed"),
                "first_player": match.get("first_player"),
                "final_battle": match.get("final_battle"),
                "resolved_battles": match.get("resolved_battles"),
                "final_command": match.get("final_command"),
                "low_command_battles": sum(
                    any(value <= threshold for value in row["command_start"])
                    for row in game_rows
                ),
                "both_at_collapse_point_battle_starts": sum(
                    all(value <= threshold for value in row["command_start"])
                    for row in game_rows
                ),
                "battles_with_no_paid_action": sum(
                    bool(row.get("no_paid_action", row.get("no_paid_operation")))
                    for row in game_rows
                ),
                "battles_with_no_paid_operation": sum(
                    bool(row.get("no_paid_action", row.get("no_paid_operation")))
                    for row in game_rows
                ),
                "battles_with_no_board_change": sum(
                    row.get("board_changed") is False
                    for row in game_rows
                ),
                "battles_with_no_strength_change": sum(
                    row.get("strength_changed") is False
                    for row in game_rows
                ),
                "battles_with_no_command_change": sum(
                    row.get("command_changed") is False
                    for row in game_rows
                ),
                "last_battles": [
                    {
                        "battle": int(row.get("battle", 0)),
                        "command_start": row.get("command_start"),
                        "command_after_recovery": row.get(
                            "command_after_recovery",
                            row.get("next_battle_command"),
                        ),
                        "no_paid_action": row.get(
                            "no_paid_action", row.get("no_paid_operation")
                        ),
                        # Historical alias.
                        "no_paid_operation": row.get(
                            "no_paid_action", row.get("no_paid_operation")
                        ),
                        "board_changed": row.get("board_changed"),
                        "strength_changed": row.get("strength_changed"),
                        "command_changed": row.get("command_changed"),
                    }
                    for row in tail
                ],
            })

        low_command_stalls = {
            "collapse_threshold": threshold,
            "diagnostic_battles": len(stall_rows),
            "both_at_collapse_point": sum(
                all(value <= threshold for value in row["command_before_collapse"])
                for row in battle_records
            ),
            "simultaneous_collapse_terminations": sum(
                bool((row.get("collapse_comparison") or {}).get("triggered"))
                and bool((row.get("collapse_comparison") or {}).get("equal"))
                and not bool((row.get("collapse_comparison") or {}).get("continued"))
                and (row.get("collapse_comparison") or {}).get("winner") is not None
                for row in battle_records
            ),
            "unequal_collapse_terminations": sum(
                bool((row.get("collapse_comparison") or {}).get("triggered"))
                and not bool((row.get("collapse_comparison") or {}).get("equal"))
                and (row.get("collapse_comparison") or {}).get("winner") is not None
                for row in battle_records
            ),
            "collapse_point_battle_starts": sum(
                any(value <= threshold for value in row["command_start"])
                for row in battle_records
            ),
            "both_at_collapse_point_battle_starts": sum(
                all(value <= threshold for value in row["command_start"])
                for row in battle_records
            ),
            "battles_with_no_paid_action": sum(
                bool(row.get("no_paid_action", row.get("no_paid_operation")))
                for row in stall_rows
            ),
            # Historical alias.
            "battles_with_no_paid_operation": sum(
                bool(row.get("no_paid_action", row.get("no_paid_operation")))
                for row in stall_rows
            ),
            "battles_with_no_board_change": sum(
                row.get("board_changed") is False
                for row in stall_rows
            ),
            "battles_with_no_strength_change": sum(
                row.get("strength_changed") is False
                for row in stall_rows
            ),
            "battles_with_no_command_change": sum(
                row.get("command_changed") is False
                for row in stall_rows
            ),
            "forced_passes": sum(
                int(row.get("forced_passes", 0))
                for row in stall_rows
            ),
            "passes_with_no_playable_alternative": sum(
                int(row.get("passes_with_no_playable_alternative", 0))
                for row in stall_rows
            ),
            "low_positive_streak_length": self._distribution(
                low_positive_streaks,
                histogram=True,
            ),
            "longest_low_positive_streak": max(
                longest_low_positive_by_game.values(), default=0
            ),
            "games": low_command_games,
            "battle_records": [
                {
                    key: row.get(key)
                    for key in (
                        "game",
                        "simulation_game_index",
                        "seed",
                        "first_player",
                        "battle",
                        "command_start",
                        "command_remaining",
                        "recovery_base",
                        "fronts_lost",
                        "front_loss_command_penalty",
                        "recovery_actual",
                        "command_before_collapse",
                        "command_after_recovery",
                        "collapse_comparison",
                        "actions_taken",
                        "operations_taken",
                        "action_trace",
                        "operation_trace",
                        "actions",
                        "cards_played",
                        "maneuvers",
                        "paid_actions",
                        "paid_operations",
                        "free_actions",
                        "free_operations",
                        "paid_card_actions",
                        "paid_card_operations",
                        "free_card_actions",
                        "free_card_operations",
                        "paid_maneuvers",
                        "effect_choices",
                        "forced_effect_choices",
                        "no_paid_action",
                        "no_paid_operation",
                        "pass_diagnostics",
                        "hand_remaining",
                        "deck_remaining",
                        "board_changed",
                        "board_changed_during_battle",
                        "board_changed_during_resolution",
                        "strength_changed",
                        "strength_changed_during_battle",
                        "strength_changed_during_resolution",
                        "command_changed_before_collapse",
                        "command_changed",
                        "board_start_signature",
                        "board_end_signature",
                        "post_resolution_board_signature",
                        "next_battle_board_signature",
                        "strength_start",
                        "strength_end",
                        "post_resolution_strength_by_front",
                        "next_battle_strength_by_front",
                    )
                }
                for row in stall_rows
            ],
        }

        match_length = {
            "matches": len(match_records),
            "censored_matches": sum(row["censored"] for row in match_records),
            "resolved_battles_per_match": self._distribution(
                row["resolved_battles"] for row in match_records
            ),
            "final_battle_number": self._distribution(final_battles),
            "censored_final_battle_number": self._distribution(
                censored_final_battles
            ),
            "battle_reach": battle_reach,
            "battle_8_plus_count": sum(
                row["battle"] >= 8 for row in battle_records
            ),
            "battle_12_plus_count": sum(
                row["battle"] >= 12 for row in battle_records
            ),
            "collapse_point_start_battles": sum(
                any(value <= threshold for value in row["command_start"])
                for row in battle_records
            ),
            "censored_at_collapse_point_matches": sum(
                row["censored"]
                and len(row.get("final_command") or []) == 2
                and any(value <= threshold for value in row["final_command"])
                for row in match_records
            ),
            "decisive_battle_one_endings": sum(
                not row["censored"] and row["final_battle"] == 1
                for row in match_records
            ),
            "decisive_battle_one_ending_rate": self._ratio(
                sum(
                    not row["censored"] and row["final_battle"] == 1
                    for row in match_records
                ),
                len(match_records),
            ),
            "battles_with_no_paid_action": sum(
                bool(row.get("no_paid_action", row.get("no_paid_operation")))
                for row in battle_records
            ),
            # Historical alias.
            "battles_with_no_paid_operation": sum(
                bool(row.get("no_paid_action", row.get("no_paid_operation")))
                for row in battle_records
            ),
            "battles_with_no_board_change": sum(
                row.get("board_changed") is False for row in battle_records
            ),
            "battles_with_no_strength_change": sum(
                row.get("strength_changed") is False for row in battle_records
            ),
        }
        pass_rows = [
            row for row in self._pass_contexts
            if not row.get("forced_yield", False)
        ]
        pass_outcomes = {
            "ahead": self._signal_outcome_group(
                pass_rows, lambda row: row["total_margin"] > 0
            ),
            "tied": self._signal_outcome_group(
                pass_rows, lambda row: row["total_margin"] == 0
            ),
            "behind": self._signal_outcome_group(
                pass_rows, lambda row: row["total_margin"] < 0
            ),
        }
        # Historical artifact readers used first_signal_outcomes. Keep the
        # three meaningful Front-balance groups as a compatibility alias; the
        # old playable-alternative groups are impossible under forced Pass.
        first_signal_outcomes = dict(pass_outcomes)

        command_end = [
            value
            for record in battle_records
            for value in record["command_remaining"]
        ]
        command_before_collapse = [
            value
            for record in battle_records
            for value in record["command_before_collapse"]
        ]
        resource = {
            "command_spend": dict(sorted(self._command_spend.items())),
            "command_spend_by_battle": {
                battle: dict(sorted(counts.items()))
                for battle, counts in sorted(self._command_spend_by_battle.items())
            },
            "command_gained_or_refunded": self._command_gained,
            "free_actions": self._free_operations,
            "free_operations": self._free_operations,
            "free_maneuvers": self._free_maneuvers,
            "discount_actions": self._discount_actions,
            "discount_command_saved": self._discount_command,
            "command_by_source": {
                source: {
                    "triggers": int(counts.get("triggers", 0)),
                    "command_gained": int(counts.get("command_gained", 0)),
                    "command_refunded": 0,
                    "nominal_command_gain": int(
                        counts.get("nominal_command_gain", 0)
                    ),
                    "discount_saved": int(counts.get("discount_saved", 0)),
                    "free_actions": int(counts.get("free_operations", 0)),
                    "free_operations": int(counts.get("free_operations", 0)),
                    "front_loss_command_avoided": int(
                        counts.get("front_loss_command_avoided", 0)
                    ),
                    "effects": dict(
                        sorted(self._command_effects_by_source[source].items())
                    ),
                }
                for source, counts in sorted(self._command_by_source.items())
            },
            "command_remaining_at_battle_end": self._distribution(command_end),
            "command_before_collapse": self._distribution(command_before_collapse),
            "command_at_pass": self._distribution(
                row["command_remaining"] for row in pass_rows
            ),
            "command_at_first_signal": self._distribution(
                row["command_remaining"] for row in pass_rows
            ),
            "passes_with_paid_alternatives": sum(
                row.get("paid_alternatives", 0) > 0 for row in pass_rows
            ),
            "passes_avoiding_command_exhaustion": sum(
                bool(row.get("signal_avoids_command_exhaustion"))
                for row in pass_rows
            ),
            "pass_avoids_command_exhaustion_rate": self._ratio(
                sum(
                    bool(row.get("signal_avoids_command_exhaustion"))
                    for row in pass_rows
                ),
                len(pass_rows),
            ),
            # Historical signal-era aliases.
            "first_signals_with_paid_alternatives": sum(
                row.get("paid_alternatives", 0) > 0 for row in pass_rows
            ),
            "first_signals_avoiding_command_exhaustion": sum(
                bool(row.get("signal_avoids_command_exhaustion"))
                for row in pass_rows
            ),
            "first_signal_avoids_command_exhaustion_rate": self._ratio(
                sum(
                    bool(row.get("signal_avoids_command_exhaustion"))
                    for row in pass_rows
                ),
                len(pass_rows),
            ),
            "pass_command_buckets": {
                "0": sum(row["command_remaining"] == 0 for row in pass_rows),
                "1-3": sum(1 <= row["command_remaining"] <= 3 for row in pass_rows),
                "4+": sum(row["command_remaining"] >= 4 for row in pass_rows),
            },
            "first_signal_command_buckets": {
                "0": sum(row["command_remaining"] == 0 for row in pass_rows),
                "1-3": sum(1 <= row["command_remaining"] <= 3 for row in pass_rows),
                "4+": sum(row["command_remaining"] >= 4 for row in pass_rows),
            },
            "command_end_buckets": {
                "<0": sum(value < 0 for value in command_end),
                "0": sum(value == 0 for value in command_end),
                "1-3": sum(1 <= value <= 3 for value in command_end),
                "4-6": sum(4 <= value <= 6 for value in command_end),
                "7+": sum(value >= 7 for value in command_end),
            },
            "command_before_collapse_buckets": {
                "<0": sum(value < 0 for value in command_before_collapse),
                "0": sum(value == 0 for value in command_before_collapse),
                "1-3": sum(1 <= value <= 3 for value in command_before_collapse),
                "4-6": sum(4 <= value <= 6 for value in command_before_collapse),
                "7+": sum(value >= 7 for value in command_before_collapse),
            },
        }

        battlefield = {
            "battles": len(battle_records),
            "occupied_positions": self._distribution(
                [row["mean_total_occupied"] for row in battle_records]
            ),
            "occupied_positions_per_player": self._distribution(
                [
                    value
                    for row in battle_records
                    for value in row["mean_occupied_per_player"]
                ]
            ),
            "active_fronts": self._distribution(
                [row["mean_active_fronts"] for row in battle_records]
            ),
            "developed_fronts": self._distribution(
                [row["mean_developed_fronts"] for row in battle_records]
            ),
            "contested_fronts": self._distribution(
                [row["mean_contested_fronts"] for row in battle_records]
            ),
            "uncontested_fronts": self._distribution(
                [row["mean_uncontested_fronts"] for row in battle_records]
            ),
            "empty_fronts": self._distribution(
                [row["mean_empty_fronts"] for row in battle_records]
            ),
            "tied_fronts": self._distribution(
                [row["mean_tied_fronts"] for row in battle_records]
            ),
            "controlled_fronts_per_player": self._distribution(
                [
                    value
                    for row in battle_records
                    for value in row["mean_controlled_fronts"]
                ]
            ),
            "complete_formations": self._distribution(
                [row["mean_complete_formations"] for row in battle_records]
            ),
            "partial_formations": self._distribution(
                [row["mean_partial_formations"] for row in battle_records]
            ),
            "total_strength_per_player": self._distribution(
                [
                    value
                    for row in battle_records
                    for value in row["mean_total_strength_per_player"]
                ]
            ),
            "strength_by_front": {
                str(front + 1): self._distribution([
                    row["mean_strength_by_front"][player][front]
                    for row in battle_records
                    for player in range(PLAYER_COUNT)
                ])
                for front in range(4)
            },
            "strength_concentration": self._distribution(
                [
                    value
                    for row in battle_records
                    for value in row["mean_strength_concentration"]
                    if value is not None
                ]
            ),
        }

        contestability = {
            "front_control_changes_per_battle": self._distribution(
                [row["front_control_changes"] for row in battle_records]
            ),
            "control_balance_changes_per_battle": self._distribution(
                [row["control_balance_changes"] for row in battle_records]
            ),
            "lead_changes_per_battle": self._distribution(
                [row["lead_changes"] for row in battle_records]
            ),
            "actions_per_battle": self._distribution(
                [row["actions"] for row in battle_records]
            ),
            "maximum_abs_margin": self._distribution(
                [row["maximum_abs_margin"] for row in battle_records]
            ),
            "midpoint_abs_margin": self._distribution(
                [row["midpoint_abs_margin"] for row in battle_records]
            ),
            "final_abs_margin": self._distribution(
                [row["final_abs_margin"] for row in battle_records]
            ),
            "durable_lead_action": self._distribution(
                [
                    row["durable_lead_action"]
                    for row in battle_records
                    if row["durable_lead_action"] is not None
                ]
            ),
            "actions_remaining_after_durable_lead": self._distribution(
                [
                    row["actions_remaining_after_durable_lead"]
                    for row in battle_records
                    if row["actions_remaining_after_durable_lead"] is not None
                ]
            ),
            "no_control_change_after_midpoint_rate": self._ratio(
                sum(row["no_control_change_after_midpoint"] for row in battle_records),
                len(battle_records),
            ),
            "pass_outcomes": pass_outcomes,
            "first_signal_outcomes": first_signal_outcomes,
        }

        choice = {
            "decisions": len(self._choice_legal),
            "legal_action_count": self._distribution(self._choice_legal, histogram=True),
            "card_play_option_count": self._distribution(self._choice_card, histogram=True),
            "maneuver_option_count": self._distribution(self._choice_maneuver, histogram=True),
            "exactly_one_legal_action": self._forced_decisions,
            "exactly_one_legal_action_rate": self._ratio(
                self._forced_decisions, len(self._choice_legal)
            ),
            "forced_maneuvers": self._forced_maneuvers,
            "forced_maneuver_rate": self._ratio(
                self._forced_maneuvers, len(self._choice_legal)
            ),
            "constraint_rule_source_decisions": self._constraint_source_decisions,
            "constraint_rule_source_rate": self._ratio(
                self._constraint_source_decisions, len(self._choice_legal)
            ),
            "constraint_active_decisions": self._constraint_active_decisions,
            "constraint_active_supported": self._constraint_active_supported,
            "constraint_active_rate": (
                self._ratio(
                    self._constraint_active_decisions, len(self._choice_legal)
                )
                if self._constraint_active_supported
                else None
            ),
            "constraint_effect_choice_decisions": self._constraint_effect_choice_decisions,
            "constraint_source_effect_choice_decisions": self._constraint_source_effect_choice_decisions,
            "effect_resolution_decisions": self._effect_choice_decisions,
            "constraint_duration_decisions": self._distribution(
                self._constraint_active_streaks
                + ([self._constraint_active_streak] if self._constraint_active_streak else [])
            ),
            "constraint_sources": dict(sorted(self._constraint_source_active.items())),
            "constraint_kinds": dict(sorted(self._constraint_kind_active.items())),
            "constraint_satisfied": dict(sorted(self._constraint_satisfied.items())),
            "constraint_impossible": dict(sorted(self._constraint_impossible.items())),
            "constraint_expired": self._constraint_expired,
            "constraint_options_removed": self._distribution(
                self._constraint_options_removed
            ),
            "constraint_options_added": self._distribution(
                self._constraint_options_added
            ),
            "constraint_forced_maneuver_decisions": self._constraint_forced_maneuver_decisions,
            "constraint_forced_front_decisions": self._constraint_forced_front_decisions,
            "constraint_carried_between_battles": self._constraint_carried_between_battles,
            "constraint_future_actions_affected": self._constraint_future_operations_affected,
            "constraint_future_operations_affected": self._constraint_future_operations_affected,
            "pass_mechanical_categories": dict(sorted(Counter(
                row["mechanical_category"] for row in self._pass_contexts
            ).items())),
            "signal_mechanical_categories": dict(sorted(Counter(
                row["mechanical_category"] for row in self._pass_contexts
            ).items())),
        }

        return {
            "match_length": match_length,
            "formation_lifecycle": {
                "forces": forces,
                "forces_ever_bonded": ever_bonded,
                "forces_ever_named": ever_named,
                "bonded_formations": len(bonded),
                "completed_formations": len(completed),
                "incomplete_removed_before_completion": len(removed_incomplete_during_battle),
                "incomplete_removed_during_battle": len(removed_incomplete_during_battle),
                # Compatibility field retained for older artifact readers.
                # Under the persistent-board rules normal Battle resolution
                # never clears incomplete formations.
                "incomplete_cleared_at_battle_end": 0,
                "incomplete_at_battle_end": sum(
                    sum(record["incomplete_at_end"]) for record in battle_records
                ),
                "partial_at_battle_end_per_player": self._distribution(
                    [
                        value
                        for record in battle_records
                        for value in record["incomplete_at_end"]
                    ]
                ),
                "force_to_bond_rate": self._ratio(ever_bonded, forces),
                "force_to_name_rate": self._ratio(ever_named, forces),
                "bond_to_name_rate": self._ratio(
                    sum(
                        row["name_action"] is not None
                        for row in bonded
                    ),
                    len(bonded),
                ),
                "force_to_bond_actions": self._distribution(force_to_bond),
                "bond_to_name_actions": self._distribution(bond_to_name),
                "force_to_name_actions": self._distribution(force_to_name),
                "completion_age_actions": self._distribution(completion_age),
                "removal_age_actions": self._distribution(removal_age),
                "battle_end_age_actions": self._distribution(
                    self._formation_age_at_battle_end
                ),
            },
            "battlefield_development": battlefield,
            "contestability": contestability,
            "mechanical_choice": choice,
            "resources": resource,
            "low_command_stalls": low_command_stalls,
            "censored_games": censored_game_diagnostics,
            "cards": self._card_lifecycle_summary(),
            "hero_modes": self._hero_summary(),
            "by_battle": by_battle,
            "sample_traces": self._sample_traces,
            "definitions": {
                "lifecycle_action": (
                    "Formation timing counts Battle decision actions, including effect choices, "
                    "but excludes mandatory discard-before-draw substeps."
                ),
                "formation_identity": (
                    "A formation lifecycle is anchored to its Force. Explicit Maneuvers "
                    "and moves preserve that identity; reconciliation then matches unchanged "
                    "positions, component signatures, and Force multisets without creating "
                    "new lifecycles for movement. If a simultaneous mass move leaves fully "
                    "identical formations indistinguishable, identity is matched deterministically "
                    "in stable board order while aggregate creation/removal counts are preserved."
                ),
                "battle_end_formation_state": (
                    "Complete and partial formation counts at Battle end describe the "
                    "persistent battlefield. Normal Battle resolution does not clear "
                    "complete, incomplete, or prepared battlefield stacks."
                ),
                "partial_formation": "A board position with a Force that is not yet both Bonded and Named.",
                "active_front": "A rules-active Front for that Battle, whether occupied or empty.",
                "developed_front": "An active Front containing at least one Force for either player.",
                "contested_front": "An active Front containing at least one Force for both players.",
                "front_control_change": "One active Front's controller changes between consecutive Action decisions.",
                "durable_lead": (
                    "Earliest recorded decision state after which the same player's non-zero "
                    "total-Strength lead keeps the same sign through every later recorded state. "
                    "The Long War has no overall Battle winner, so this is a persistence measure, "
                    "not an outcome or winner claim."
                ),
                "low_command_stall": (
                    "Collapse-point Command means at least one player starts at the configured "
                    "collapse point. At the pre-recovery Collapse check, signed Command is "
                    "compared without clamping. Lower Command collapses; exact equal exhaustion "
                    "is terminal and the player who Passed in that Battle loses. Low-positive streaks "
                    "track surviving Battles that remain close to Collapse."
                ),
                "first_signal_result": (
                    "Compatibility name for the sole forced Pass event. There is no overall "
                    "Battle winner, so Pass outcome groups use final active-Front balance: "
                    "Fronts won minus Fronts lost by the passer."
                ),
                "constraint_rule_source": (
                    "A necessity-classed card or card with an explicit constraint rule block "
                    "is present in play. This does not mean its restriction is implemented or active."
                ),
                "constraint_active": (
                    "Only reported when the engine exposes an explicit active-constraint marker. "
                    "If unsupported, the Balance Lab reports this metric as not instrumented rather than 0%."
                ),
                "effect_resolution_decision": (
                    "Pending EffectChoice resolution is counted separately and excluded from ordinary "
                    "Action-choice, forced-choice and card-playability statistics."
                ),
                "card_draw_to_play": (
                    "Physical card copies are not engine-identified, so duplicate copies are "
                    "paired draw-to-play in FIFO order for timing aggregates."
                ),
                "drawn_after_reshuffle": (
                    "A card copy was in that player's discard pile when it was reshuffled, "
                    "then a matching copy was subsequently drawn. Duplicate copies are matched by count."
                ),
                "held_across_battle_boundary": (
                    "Hand survival across a Battle boundary is a multiset intersection by card id; "
                    "identical duplicate copies are not physically distinguishable."
                ),
                "discarded_without_play": (
                    "A card moved from hand into discard without being the card action just played. "
                    "Battlefield removals do not count because they did not leave the hand."
                ),
                "unplayed_at_match_end": (
                    "Copies still in hand when the match ends. Cards remaining unseen in the deck are not counted."
                ),
                "battle_index": "Battle 1, 2 and 3 are separate; Battles 4-7 and 8+ are separated so zero-resource late-game stalls cannot dominate the normal late-war bucket.",
                "match_length": (
                    "Battle reach uses the final Battle number observed in each match. "
                    "Censored matches count as having reached their current Battle but not as having resolved it."
                ),
                "command_gained_or_refunded": (
                    "Command gained after an Action beyond its actual paid cost. "
                    "Between-Battle recovery is excluded and remains visible in the Battle-indexed trajectory."
                ),
                "command_by_source": (
                    "Source-attributed real-transition events. command_gained is the realized "
                    "increase after the Command cap; nominal_command_gain is the authored amount; "
                    "discount_saved is Command not paid; free_actions is the current key for "
                    "zero-Command Actions and free_operations is its compatibility alias; "
                    "front_loss_command_avoided is the Front-loss "
                    "penalty prevented. "
                    "The current card schema has no distinct refund primitive, so command_refunded "
                    "is explicitly 0 and authored regain effects are included in command_gained."
                ),
                "eventual_completion_rate_for_forces_deployed": (
                    "Among Force lifecycles created in that Battle number, the share "
                    "that eventually become complete Force-Bond-Name formations later in the match."
                ),
                "forced_maneuver": (
                    "A decision whose complete legal action set contains exactly one action, and that action is Maneuver."
                ),
            },
        }

    def _initialize_formations(self, engine: GameEngine, state: GameState) -> None:
        for player in range(PLAYER_COUNT):
            for position in all_positions():
                slot = state.slot(player, position)
                if slot.force is not None:
                    self._create_formation(engine, state, player, position, created_action=0)

    def _create_formation(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
        position: Position,
        *,
        created_action: int,
    ) -> int:
        slot = state.slot(player, position)
        formation_id = self._next_formation_id
        self._next_formation_id += 1
        bond_action = created_action if slot.bond is not None else None
        name_action = created_action if slot.name is not None else None
        completion_action = (
            created_action if slot.force is not None and slot.bond is not None and slot.name is not None
            else None
        )
        self._formations[formation_id] = {
            "id": formation_id,
            "game": self._game_index,
            "player": player,
            "force": slot.force,
            "created_battle": int(state.battle),
            "created_action": created_action,
            "bond_action": bond_action,
            "name_action": name_action,
            "completion_action": completion_action,
            "removed_action": None,
            "removed_reason": None,
        }
        self._formation_at[(player, position)] = formation_id
        if completion_action is not None:
            self._record_formation_completion(engine, state, player, position, formation_id)
        return formation_id

    def _reconcile_formations(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
        actor: int,
        action: Action,
        *,
        battle_resolved: bool,
    ) -> int:
        before_map = dict(self._formation_at)
        after_slots = {
            (player, position): state.slot(player, position)
            for player in range(PLAYER_COUNT)
            for position in all_positions()
            if state.slot(player, position).force is not None
        }
        assigned: dict[tuple[int, Position], int] = {}
        used: set[int] = set()

        def assign(source_key: tuple[int, Position], dest_key: tuple[int, Position]) -> None:
            formation_id = before_map.get(source_key)
            slot = after_slots.get(dest_key)
            if formation_id is None or slot is None or formation_id in used or dest_key in assigned:
                return
            before_slot = before.slot(*source_key)
            if before_slot.force == slot.force:
                assigned[dest_key] = formation_id
                used.add(formation_id)

        if isinstance(action, Maneuver):
            src = (actor, action.source)
            dst = (actor, action.destination)
            assign(src, dst)
            assign(dst, src)
        elif isinstance(action, EffectChoice) and action.source and action.destination:
            src = (action.source.player, action.source.position)
            dst = (action.destination.player, action.destination.position)
            assign(src, dst)
            assign(dst, src)
        elif isinstance(action, PlayBond) and action.move_destination is not None:
            assign((actor, action.position), (actor, action.move_destination))

        for key, formation_id in before_map.items():
            if formation_id in used or key in assigned or key not in after_slots:
                continue
            before_slot = before.slot(*key)
            if before_slot.force == after_slots[key].force:
                assigned[key] = formation_id
                used.add(formation_id)

        remaining_ids = [
            formation_id for formation_id in before_map.values()
            if formation_id not in used
        ]
        remaining_keys = [key for key in after_slots if key not in assigned]

        for formation_id in list(remaining_ids):
            source_key = next(
                (key for key, value in before_map.items() if value == formation_id),
                None,
            )
            if source_key is None:
                continue
            before_slot = before.slot(*source_key)
            signature = (before_slot.force, before_slot.bond, before_slot.name)
            candidates = [
                key for key in remaining_keys
                if (
                    after_slots[key].force,
                    after_slots[key].bond,
                    after_slots[key].name,
                ) == signature
            ]
            if candidates:
                key = candidates[0]
                assigned[key] = formation_id
                used.add(formation_id)
                remaining_keys.remove(key)

        remaining_ids = [
            formation_id for formation_id in before_map.values()
            if formation_id not in used
        ]
        for formation_id in remaining_ids:
            force = self._formations[formation_id]["force"]
            candidates = [key for key in remaining_keys if after_slots[key].force == force]
            if not candidates:
                continue
            key = candidates[0]
            assigned[key] = formation_id
            used.add(formation_id)
            remaining_keys.remove(key)

        for formation_id in before_map.values():
            if formation_id in used:
                continue
            row = self._formations[formation_id]
            if row["removed_action"] is None:
                row["removed_action"] = self._current_action
                row["removed_reason"] = "effect_or_card"

        self._formation_at = dict(assigned)
        new_completions = 0
        for key in remaining_keys:
            player, position = key
            formation_id = self._create_formation(
                engine,
                state,
                player,
                position,
                created_action=self._current_action,
            )
            if self._formations[formation_id]["completion_action"] is not None:
                new_completions += 1
            assigned[key] = formation_id
        self._formation_at = dict(assigned)

        for (player, position), formation_id in self._formation_at.items():
            slot = state.slot(player, position)
            row = self._formations[formation_id]
            if row["bond_action"] is None and slot.bond is not None:
                row["bond_action"] = self._current_action
                self._battle_events["force_to_bond"] += 1
            if row["name_action"] is None and slot.name is not None:
                row["name_action"] = self._current_action
                self._battle_events["force_to_name"] += 1
                if row["bond_action"] is not None:
                    self._battle_events["bond_to_name"] += 1
            if (
                row["completion_action"] is None
                and slot.force is not None
                and slot.bond is not None
                and slot.name is not None
            ):
                row["completion_action"] = self._current_action
                new_completions += 1
                self._record_formation_completion(
                    engine, state, player, position, formation_id
                )
        return new_completions

    def _record_formation_completion(
        self,
        engine: GameEngine,
        state: GameState,
        player: int,
        position: Position,
        formation_id: int,
    ) -> None:
        slot = state.slot(player, position)
        force_card = engine.cards.get(slot.force or "", {})
        name_card = engine.cards.get(slot.name or "", {})
        if force_card.get("hero"):
            self._hero_modes[slot.force]["force_completions"] += 1
        if name_card.get("hero"):
            self._hero_modes[slot.name]["name_completions"] += 1

    def _record_command_flow(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
        actor: int,
        action: Action,
    ) -> None:
        if before.pending_draw_discard_for is not None:
            return
        try:
            actual_cost = int(engine.command_cost_for_action(before, action))
        except (ValueError, TypeError):
            actual_cost = max(0, before.players[actor].command - state.players[actor].command)

        bucket = self._battle_key(before.battle)
        category = None
        if isinstance(action, CARD_ACTIONS):
            category = "card_play"
        elif isinstance(action, Maneuver):
            category = "maneuver"
        elif isinstance(action, EffectChoice):
            category = "effect_choice"

        if category is not None:
            self._command_spend[category] += actual_cost
            self._command_spend_by_battle[bucket][category] += actual_cost

        battle_transition = (
            state.phase is Phase.COMPLETE or state.battle != before.battle
        )
        if self._battle_operation_trace:
            trace = self._battle_operation_trace[-1]
            if (
                trace.get("player") == int(actor)
                and trace.get("action") == action_key(action)
            ):
                before_board = [
                    [
                        before.slot(player, position).force,
                        before.slot(player, position).bond,
                        before.slot(player, position).name,
                    ]
                    for player in range(PLAYER_COUNT)
                    for position in all_positions()
                ]
                after_board = [
                    [
                        state.slot(player, position).force,
                        state.slot(player, position).bond,
                        state.slot(player, position).name,
                    ]
                    for player in range(PLAYER_COUNT)
                    for position in all_positions()
                ]
                before_strength = [
                    [
                        engine.front_strength(before, player, front)
                        for front in Front
                    ]
                    for player in range(PLAYER_COUNT)
                ]
                after_strength = [
                    [
                        engine.front_strength(state, player, front)
                        for front in Front
                    ]
                    for player in range(PLAYER_COUNT)
                ]
                is_operation = isinstance(action, OPERATION_ACTIONS)
                trace.update({
                    "command_cost": actual_cost,
                    "paid_action": is_operation and actual_cost > 0,
                    "free_action": is_operation and actual_cost == 0,
                    "card_action": isinstance(action, CARD_ACTIONS),
                    # Compatibility aliases for pre-overhaul traces.
                    "paid_operation": is_operation and actual_cost > 0,
                    "free_operation": is_operation and actual_cost == 0,
                    "card_operation": isinstance(action, CARD_ACTIONS),
                    "maneuver": isinstance(action, Maneuver),
                    "pass": isinstance(action, Pass),
                    "effect_choice": isinstance(action, EffectChoice),
                    "forced_effect_choice": (
                        isinstance(action, EffectChoice)
                        and bool(trace.get("forced"))
                    ),
                    "command_after_transition": int(state.players[actor].command),
                    "command_delta_transition": (
                        int(state.players[actor].command)
                        - int(before.players[actor].command)
                    ),
                    "battle_transition": battle_transition,
                    "board_changed_transition": before_board != after_board,
                    "strength_changed_transition": (
                        before_strength != after_strength
                    ),
                    "hand_after": len(state.players[actor].hand),
                    "deck_after": len(state.players[actor].deck),
                })

        if isinstance(action, OPERATION_ACTIONS) and actual_cost > 0:
            self._battle_events["paid_operations"] += 1
        if isinstance(action, OPERATION_ACTIONS) and actual_cost == 0:
            self._free_operations += 1
            self._battle_events["free_operations"] += 1
        if isinstance(action, Maneuver) and actual_cost == 0:
            self._free_maneuvers += 1
            self._battle_events["free_maneuvers"] += 1

        printed = actual_cost
        card_id = action.card_id if isinstance(action, CARD_ACTIONS) else None
        if card_id is not None:
            printed = int(engine.cards.get(card_id, {}).get(CardField.COMMAND_COST, actual_cost))
        elif isinstance(action, Maneuver):
            printed = int(engine.maneuver_command_cost)
        saved = max(0, printed - actual_cost)
        if saved:
            self._discount_actions += 1
            self._discount_command += saved
            self._battle_events["discount_actions"] += 1

        diagnostics = list(engine.last_command_diagnostics())
        gained_from_diagnostics = 0
        discount_sources: list[str] = []
        for event in diagnostics:
            source = event.get("source_card") or "<engine>"
            stats = self._command_by_source[source]
            stats["triggers"] += 1
            detail = str(
                event.get("detail") or CommandDiagnosticDetail.OTHER.value
            )
            self._command_effects_by_source[source][detail] += 1
            amount = int(event.get("amount", 0) or 0)
            nominal = int(event.get("nominal_amount", amount) or 0)
            if event.get("kind") == CommandDiagnosticKind.GAIN:
                stats["command_gained"] += amount
                stats["nominal_command_gain"] += nominal
                gained_from_diagnostics += amount
            elif event.get("kind") == CommandDiagnosticKind.DISCOUNT:
                stats["discount_saved"] += amount
                if (
                    detail == CommandDiagnosticDetail.FREE_MANEUVER
                    and isinstance(action, EffectChoice)
                    and amount > 0
                ):
                    stats["free_operations"] += 1
                if amount > 0:
                    discount_sources.append(source)
            elif event.get("kind") == CommandDiagnosticKind.FRONT_LOSS_PROTECTION:
                stats["front_loss_command_avoided"] += amount

        if isinstance(action, OPERATION_ACTIONS) and actual_cost == 0:
            source = discount_sources[0] if discount_sources else "<engine>"
            self._command_by_source[source]["free_operations"] += 1

        gained = gained_from_diagnostics
        if gained:
            self._command_gained += gained
            self._battle_events["command_gained"] += gained

    def _record_hero_action(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
        actor: int,
        action: Action,
    ) -> None:
        if not isinstance(action, (PlayForce, PlayName)):
            return
        card = engine.cards.get(action.card_id, {})
        if not card.get("hero"):
            return
        mode = "force" if isinstance(action, PlayForce) else "name"
        stats = self._hero_modes[action.card_id]
        stats[f"{mode}_plays"] += 1
        stats["by_battle"][self._battle_key(before.battle)][mode] += 1
        before_margins = list(engine.front_margins(before, actor))
        after_margins = list(engine.front_margins(state, actor))
        stats[f"{mode}_front_swing_total"] += sum(after_margins) - sum(before_margins)
        before_control = sum(x > 0 for x in before_margins) - sum(x < 0 for x in before_margins)
        after_control = sum(x > 0 for x in after_margins) - sum(x < 0 for x in after_margins)
        stats[f"{mode}_control_swing_total"] += after_control - before_control

    def _record_unplayed_discards(
        self,
        before: GameState,
        state: GameState,
        action: Action,
    ) -> None:
        played_id = action.card_id if isinstance(action, CARD_ACTIONS) else None
        for player in range(PLAYER_COUNT):
            added_to_discard = (
                Counter(state.players[player].discard)
                - Counter(before.players[player].discard)
            )
            removed_from_hand = (
                Counter(before.players[player].hand)
                - Counter(state.players[player].hand)
            )
            unplayed = added_to_discard & removed_from_hand
            if (
                played_id is not None
                and player == before.active_player
                and unplayed.get(played_id, 0)
            ):
                unplayed[played_id] -= 1
                if unplayed[played_id] <= 0:
                    del unplayed[played_id]
            for card_id, count in unplayed.items():
                self._card_discarded_unplayed[card_id] += count
                queue = self._draw_queues.get((player, card_id), [])
                for _ in range(min(count, len(queue))):
                    queue.pop(0)

    def _record_held_across_boundary(self, before: GameState, state: GameState) -> None:
        if state.phase is Phase.COMPLETE:
            return
        for player in range(PLAYER_COUNT):
            survived = Counter(before.players[player].hand) & Counter(state.players[player].hand)
            for card_id, count in survived.items():
                self._card_held_boundaries[card_id] += count

    def _record_battle_end(
        self,
        engine: GameEngine,
        before: GameState,
        state: GameState,
    ) -> None:
        rows = list(self._battle_snapshots)
        if not rows:
            return
        final = rows[-1]
        middle = rows[len(rows) // 2]
        snapshot = state.last_battle_snapshot or {}
        front_scores = snapshot.get("front_scores", [])

        durable_index = None
        strength_differences = [
            row["total_strength"][0] - row["total_strength"][1]
            for row in rows
        ]
        for index, value in enumerate(strength_differences):
            lead_sign = self._sign(value)
            if lead_sign == 0:
                continue
            if all(
                self._sign(later) == lead_sign
                for later in strength_differences[index:]
            ):
                durable_index = index
                break

        midpoint = len(rows) // 2
        no_change_after_midpoint = all(
            rows[index]["front_controllers"] == rows[midpoint]["front_controllers"]
            for index in range(midpoint, len(rows))
        )

        final_command = [
            max(
                0,
                int(before.battle_start_command[player])
                - int(before.command_spent_this_battle[player])
                + int(before.command_refunded_this_battle[player]),
            )
            for player in range(PLAYER_COUNT)
        ]

        incomplete_end = [
            self._count_partial(before, player)
            for player in range(PLAYER_COUNT)
        ]
        complete_end = [
            self._count_complete(before, player)
            for player in range(PLAYER_COUNT)
        ]

        battle_passes = [
            row for row in self._pass_contexts
            if row["game"] == self._game_index and row["battle"] == before.battle
        ]
        pass_row = next(
            (row for row in battle_passes if not row.get("forced_yield", False)),
            None,
        )

        recovery_base = int(engine.command_recovery_for_battle(before.battle))
        fronts_lost = [
            int(value) for value in snapshot.get("fronts_lost", (0, 0))
        ]
        front_loss_command_penalty = [
            int(value) for value in snapshot.get("front_loss_command_penalty", fronts_lost)
        ]
        recovery_actual = [
            int(value)
            for value in snapshot.get(
                "recovery_actual",
                (
                    [0, 0]
                    if state.phase is Phase.COMPLETE
                    else [
                        max(
                            int(engine.rules.command_recovery_floor),
                            recovery_base,
                        )
                        for _player in range(PLAYER_COUNT)
                    ]
                ),
            )
        ]
        command_before_collapse = [
            int(value)
            for value in snapshot.get("command_before_collapse", final_command)
        ]
        command_before_collapse = list(command_before_collapse)
        command_after_recovery = [
            int(value)
            for value in snapshot.get(
                "command_remaining",
                [int(player.command) for player in state.players],
            )
        ]
        threshold = int(engine.rules.command_collapse_threshold)
        collapse_comparison = {
            "threshold": threshold,
            "commands": command_before_collapse,
            "triggered": any(value <= threshold for value in command_before_collapse),
            "equal": command_before_collapse[0] == command_before_collapse[1],
            "winner": state.winner if state.phase is Phase.COMPLETE else None,
            "continued": state.phase is not Phase.COMPLETE,
        }
        pass_diagnostics = [
            {
                "player": int(row["player"]),
                "pass": not bool(row.get("forced_yield", False)),
                # Historical alias retained in serialized diagnostics.
                "first_signal": bool(row.get("first_signal", True)),
                "command": int(row["command_remaining"]),
                "legal_alternatives": int(row.get("legal_alternatives", 0)),
                "playable_card_actions": int(row.get("playable_card_actions", 0)),
                "maneuver_actions": int(row.get("maneuver_actions", 0)),
                "paid_alternatives": int(row.get("paid_alternatives", 0)),
                "command_exhausting_alternatives": int(
                    row.get("command_exhausting_alternatives", 0)
                ),
                "signal_avoids_command_exhaustion": bool(
                    row.get("signal_avoids_command_exhaustion", False)
                ),
                "forced": int(row.get("legal_alternatives", 0)) == 0,
            }
            for row in battle_passes
        ]
        post_resolution_board_signature = [
            [
                state.slot(player, position).force,
                state.slot(player, position).bond,
                state.slot(player, position).name,
            ]
            for player in range(PLAYER_COUNT)
            for position in all_positions()
        ]
        post_resolution_strength_by_front = [
            [
                engine.front_strength(state, player, front)
                for front in Front
            ]
            for player in range(PLAYER_COUNT)
        ]
        next_board_signature = (
            None
            if state.phase is Phase.COMPLETE
            else post_resolution_board_signature
        )
        next_strength_by_front = (
            None
            if state.phase is Phase.COMPLETE
            else post_resolution_strength_by_front
        )

        record = {
            "game": self._game_index,
            "simulation_game_index": self._simulation_game_index,
            "seed": self._game_seed,
            "first_player": self._first_player,
            "battle": int(before.battle),
            "actions": len(rows),
            "actions_taken": [
                int(value)
                for value in snapshot.get(
                    "operations",
                    before.operations_this_battle,
                )
            ],
            "operations_taken": [
                int(value)
                for value in snapshot.get(
                    "operations",
                    before.operations_this_battle,
                )
            ],
            "action_trace": list(self._battle_operation_trace),
            "operation_trace": list(self._battle_operation_trace),
            "maneuvers": self._battle_events["maneuvers"],
            "paid_actions": self._battle_events["paid_operations"],
            "paid_operations": self._battle_events["paid_operations"],
            "free_actions": self._battle_events["free_operations"],
            "free_operations": self._battle_events["free_operations"],
            "paid_card_actions": sum(
                bool(row.get("paid_action", row.get("paid_operation")))
                and row.get("category") == "card"
                for row in self._battle_operation_trace
            ),
            "paid_card_operations": sum(
                bool(row.get("paid_action", row.get("paid_operation")))
                and row.get("category") == "card"
                for row in self._battle_operation_trace
            ),
            "free_card_actions": sum(
                bool(row.get("free_action", row.get("free_operation")))
                and row.get("category") == "card"
                for row in self._battle_operation_trace
            ),
            "free_card_operations": sum(
                bool(row.get("free_action", row.get("free_operation")))
                and row.get("category") == "card"
                for row in self._battle_operation_trace
            ),
            "paid_maneuvers": sum(
                bool(row.get("paid_operation")) and row.get("category") == "maneuver"
                for row in self._battle_operation_trace
            ),
            "effect_choices": self._battle_events["effect_choices"],
            "forced_effect_choices": self._battle_events["forced_effect_choices"],
            "forces_played": self._battle_events["forces_played"],
            "bonds_played": self._battle_events["bonds_played"],
            "names_played": self._battle_events["names_played"],
            "completed_formations": self._battle_events["completed_formations"],
            "incomplete_at_end": incomplete_end,
            "complete_at_end": complete_end,
            "mean_total_occupied": mean(sum(row["occupied"]) for row in rows),
            "mean_occupied_per_player": [
                mean(row["occupied"][player] for row in rows)
                for player in range(PLAYER_COUNT)
            ],
            "mean_active_fronts": mean(row["active_fronts"] for row in rows),
            "mean_developed_fronts": mean(row["developed_fronts"] for row in rows),
            "mean_contested_fronts": mean(row["contested_fronts"] for row in rows),
            "mean_uncontested_fronts": mean(row["uncontested_fronts"] for row in rows),
            "mean_empty_fronts": mean(row["empty_fronts"] for row in rows),
            "mean_tied_fronts": mean(row["tied_fronts"] for row in rows),
            "mean_controlled_fronts": [
                mean(row["controlled_fronts"][player] for row in rows)
                for player in range(PLAYER_COUNT)
            ],
            "mean_complete_formations": mean(sum(row["complete_formations"]) for row in rows),
            "mean_partial_formations": mean(sum(row["partial_formations"]) for row in rows),
            "mean_total_strength_per_player": [
                mean(row["total_strength"][player] for row in rows)
                for player in range(PLAYER_COUNT)
            ],
            "mean_strength_by_front": [
                [
                    mean(row["strength_by_front"][player][front] for row in rows)
                    for front in range(4)
                ]
                for player in range(PLAYER_COUNT)
            ],
            "mean_strength_concentration": [
                self._mean_optional([row["strength_concentration"][player] for row in rows])
                for player in range(PLAYER_COUNT)
            ],
            "front_control_changes": self._battle_control_changes,
            "control_balance_changes": self._battle_control_balance_changes,
            "lead_changes": self._battle_lead_changes,
            "maximum_abs_margin": max(abs(sum(row["front_margins"])) for row in rows),
            "midpoint_abs_margin": abs(sum(middle["front_margins"])),
            "final_abs_margin": abs(sum(final["front_margins"])),
            "durable_lead_action": (
                None if durable_index is None else rows[durable_index]["action"]
            ),
            "actions_remaining_after_durable_lead": (
                None if durable_index is None else len(rows) - 1 - durable_index
            ),
            "no_control_change_after_midpoint": no_change_after_midpoint,
            "command_start": [int(value) for value in before.battle_start_command],
            "command_spent": [int(value) for value in before.command_spent_this_battle],
            "command_refunded": [int(value) for value in before.command_refunded_this_battle],
            "command_remaining": final_command,
            "recovery_base": recovery_base,
            "fronts_lost": fronts_lost,
            "front_loss_command_penalty": front_loss_command_penalty,
            "recovery_actual": recovery_actual,
            "command_before_collapse": command_before_collapse,
            "command_after_recovery": command_after_recovery,
            "collapse_comparison": collapse_comparison,
            "next_battle_command": (
                None
                if state.phase is Phase.COMPLETE
                else [int(player.command) for player in state.players]
            ),
            "board_start_signature": rows[0]["board_signature"],
            "board_end_signature": final["board_signature"],
            "post_resolution_board_signature": post_resolution_board_signature,
            "next_battle_board_signature": next_board_signature,
            "strength_start": rows[0]["strength_by_front"],
            "strength_end": final["strength_by_front"],
            "post_resolution_strength_by_front": post_resolution_strength_by_front,
            "next_battle_strength_by_front": next_strength_by_front,
            "board_changed": (
                rows[0]["board_signature"]
                != final["board_signature"]
            ),
            "board_changed_during_battle": (
                rows[0]["board_signature"]
                != final["board_signature"]
            ),
            "board_changed_during_resolution": (
                final["board_signature"]
                != post_resolution_board_signature
            ),
            "strength_changed": (
                rows[0]["strength_by_front"]
                != final["strength_by_front"]
            ),
            "strength_changed_during_battle": (
                rows[0]["strength_by_front"]
                != final["strength_by_front"]
            ),
            "strength_changed_during_resolution": (
                final["strength_by_front"]
                != post_resolution_strength_by_front
            ),
            "command_changed_before_collapse": (
                [int(value) for value in before.battle_start_command]
                != final_command
            ),
            "command_changed": (
                [int(value) for value in before.battle_start_command]
                != command_after_recovery
            ),
            "no_paid_action": self._battle_events["paid_operations"] == 0,
            "no_paid_operation": self._battle_events["paid_operations"] == 0,
            "hand_remaining": [len(player.hand) for player in before.players],
            "deck_remaining": [len(player.deck) for player in before.players],
            "mean_legal_actions": mean(
                row["legal_actions"] for row in rows
            ),
            "constraint_source_decisions": sum(
                bool(row["constraint_rule_sources"]) for row in rows
            ),
            "constraint_active_decisions": sum(
                bool(row["constraint_active"]) for row in rows
            ),
            "cards_played": self._battle_events["cards_played"],
            "pass_events": len(battle_passes),
            "pass_diagnostics": pass_diagnostics,
            "forced_passes": sum(row["forced"] for row in pass_diagnostics),
            "passes_with_no_playable_alternative": sum(
                row["playable_card_actions"] == 0
                and row["maneuver_actions"] == 0
                for row in pass_diagnostics
            ),
            "pass_command": (
                None if pass_row is None else pass_row["command_remaining"]
            ),
            "pass_unplayable_cards": (
                None if pass_row is None else pass_row.get("unplayable_cards_remaining", 0)
            ),
            "pass_structurally_dead_cards": (
                None if pass_row is None else pass_row.get("structurally_dead_cards", 0)
            ),
            "pass_unaffordable_cards": (
                None if pass_row is None else pass_row.get("unaffordable_cards", 0)
            ),
            "pass_legal_alternatives": (
                None if pass_row is None else pass_row.get("legal_alternatives", 0)
            ),
            "pass_playable_card_actions": (
                None if pass_row is None else pass_row.get("playable_card_actions", 0)
            ),
            "pass_maneuver_actions": (
                None if pass_row is None else pass_row.get("maneuver_actions", 0)
            ),
            # Historical signal-era aliases.
            "first_signal_command": (
                None if pass_row is None else pass_row["command_remaining"]
            ),
            "first_signal_unplayable_cards": (
                None if pass_row is None else pass_row.get("unplayable_cards_remaining", 0)
            ),
            "first_signal_structurally_dead_cards": (
                None if pass_row is None else pass_row.get("structurally_dead_cards", 0)
            ),
            "first_signal_unaffordable_cards": (
                None if pass_row is None else pass_row.get("unaffordable_cards", 0)
            ),
            "first_signal_legal_alternatives": (
                None if pass_row is None else pass_row.get("legal_alternatives", 0)
            ),
            "first_signal_playable_card_actions": (
                None if pass_row is None else pass_row.get("playable_card_actions", 0)
            ),
            "first_signal_maneuver_actions": (
                None if pass_row is None else pass_row.get("maneuver_actions", 0)
            ),
            "free_maneuvers": self._battle_events["free_maneuvers"],
            "command_gained": self._battle_events["command_gained"],
        }
        self._battle_records.append(record)

        front_balances = self._front_result_balances(front_scores)
        for pass_row in self._pass_contexts:
            if (
                pass_row["game"] == self._game_index
                and pass_row["battle"] == before.battle
                and not pass_row.get("forced_yield", False)
                and pass_row["final_front_balance"] is None
                and front_balances is not None
            ):
                pass_row["final_front_balance"] = front_balances[pass_row["player"]]

        for player in range(PLAYER_COUNT):
            for position in all_positions():
                slot = before.slot(player, position)
                if slot.force is None:
                    continue
                force_card = engine.cards.get(slot.force, {})
                name_card = engine.cards.get(slot.name or "", {})
                if force_card.get("hero"):
                    self._hero_modes[slot.force]["force_battle_end_presence"] += 1
                if name_card.get("hero"):
                    self._hero_modes[slot.name]["name_battle_end_presence"] += 1

    def _reset_battle(self, state: GameState) -> None:
        if self._constraint_active_streak:
            self._constraint_active_streaks.append(self._constraint_active_streak)
            self._constraint_active_streak = 0
        self._battle_number = int(state.battle)
        self._battle_action = 0
        self._battle_events = Counter()
        self._battle_operation_trace = []
        self._battle_snapshots = []
        self._last_controllers = None
        self._last_control_balance = None
        self._last_lead_sign = None
        self._battle_control_changes = 0
        self._battle_control_balance_changes = 0
        self._battle_lead_changes = 0

    def _snapshot(
        self,
        engine: GameEngine,
        state: GameState,
        *,
        actor: int,
        legal_count: int,
        constraint_active: bool,
        constraint_sources: list[str],
    ) -> dict[str, Any]:
        occupied = [
            sum(state.slot(player, position).occupied for position in all_positions())
            for player in range(PLAYER_COUNT)
        ]
        complete = [self._count_complete(state, player) for player in range(PLAYER_COUNT)]
        partial = [self._count_partial(state, player) for player in range(PLAYER_COUNT)]
        rule_active_mask = engine.rules.active_front_mask_for_battle(
            state.battle
        )
        forces_by_front = [
            [
                (
                    sum(
                        state.board[player][int(front)][rank].force is not None
                        for rank in range(RANK_COUNT)
                    )
                    if rule_active_mask & (1 << int(front))
                    else 0
                )
                for front in Front
            ]
            for player in range(PLAYER_COUNT)
        ]
        rules_active_fronts = sum(
            bool(rule_active_mask & (1 << int(front)))
            for front in Front
        )
        developed_fronts = sum(
            forces_by_front[0][int(front)] + forces_by_front[1][int(front)] > 0
            for front in Front
            if rule_active_mask & (1 << int(front))
        )
        contested_fronts = sum(
            forces_by_front[0][int(front)] > 0
            and forces_by_front[1][int(front)] > 0
            for front in Front
            if rule_active_mask & (1 << int(front))
        )
        raw_margins = list(engine.front_margins(state, 0))
        margins = [
            raw_margins[int(front)]
            if rule_active_mask & (1 << int(front))
            else 0
            for front in Front
        ]
        controllers = [
            self._sign(value)
            if rule_active_mask & (1 << index)
            else 0
            for index, value in enumerate(margins)
        ]
        strengths = [
            [
                (
                    engine.front_strength(state, player, front)
                    if rule_active_mask & (1 << int(front))
                    else 0
                )
                for front in Front
            ]
            for player in range(PLAYER_COUNT)
        ]
        totals = [sum(values) for values in strengths]
        concentration = [
            (max(values) / total if total > 0 else None)
            for values, total in zip(strengths, totals)
        ]
        return {
            "game": self._game_index,
            "simulation_game_index": self._simulation_game_index,
            "seed": self._game_seed,
            "first_player": self._first_player,
            "battle": int(state.battle),
            "action": self._battle_action,
            "actor": actor,
            "cards_played_so_far": self._battle_events["cards_played"],
            "command": [player.command for player in state.players],
            "hand": [len(player.hand) for player in state.players],
            "deck": [len(player.deck) for player in state.players],
            "occupied": occupied,
            "complete_formations": complete,
            "partial_formations": partial,
            # "active" is a rules term: active Fronts are determined by the
            # Battle number, regardless of whether either player has deployed
            # there. "developed" means an active Front containing at least one
            # Force.
            "available_fronts": rules_active_fronts,  # compatibility alias
            "active_fronts": rules_active_fronts,
            "developed_fronts": developed_fronts,
            "contested_fronts": contested_fronts,
            "uncontested_fronts": developed_fronts - contested_fronts,
            "empty_fronts": rules_active_fronts - developed_fronts,
            "front_margins": margins,
            "front_controllers": controllers,
            "controlled_fronts": [
                sum(
                    value > 0
                    for front, value in zip(Front, margins)
                    if rule_active_mask & (1 << int(front))
                ),
                sum(
                    value < 0
                    for front, value in zip(Front, margins)
                    if rule_active_mask & (1 << int(front))
                ),
            ],
            "tied_fronts": sum(
                value == 0
                for front, value in zip(Front, margins)
                if rule_active_mask & (1 << int(front))
            ),
            "total_strength": totals,
            "strength_by_front": strengths,
            "strength_concentration": concentration,
            "board_signature": [
                [
                    state.slot(player, position).force,
                    state.slot(player, position).bond,
                    state.slot(player, position).name,
                ]
                for player in range(PLAYER_COUNT)
                for position in all_positions()
            ],
            "legal_actions": legal_count,
            "constraint_active": constraint_active,
            "constraint_rule_sources": constraint_sources,
        }

    def _constraint_rule_sources(
        self,
        engine: GameEngine,
        state: GameState,
    ) -> list[str]:
        card_ids: set[str] = set()
        for player in range(PLAYER_COUNT):
            for narrative in state.narratives[player]:
                if narrative.ongoing:
                    card_ids.add(narrative.card_id)
            stratagem = state.stratagems[player]
            if stratagem is not None:
                card_ids.add(stratagem.card_id)
            for position in all_positions():
                slot = state.slot(player, position)
                card_ids.update(
                    card_id for card_id in (slot.force, slot.bond, slot.name)
                    if card_id is not None
                )
        result = []
        for card_id in sorted(card_ids):
            card = engine.cards.get(card_id, {})
            blocks = card.get("rule_blocks") or []
            classes = set(card.get("classes") or [])
            if classes & CONSTRAINT_CLASSES or any(
                block.get("kind") == "constraint" for block in blocks
            ):
                result.append(card_id)
        return result

    @staticmethod
    def _active_operation_constraints(
        state: GameState,
        actor: int,
    ) -> list[Any]:
        return [
            item
            for item in state.constraints
            if item.player == actor and state.turn_number >= item.activate_turn
        ]

    @staticmethod
    def _constraint_identity(item: Any) -> tuple[Any, ...]:
        return (
            item.source_card,
            item.player,
            item.kind,
            item.source_owner,
            item.front,
            item.direction,
            item.source_position,
            item.activate_turn,
        )

    @staticmethod
    def _constraint_matches_action(item: Any, action: Action) -> bool:
        if item.kind is ConstraintKind.MANEUVER:
            return isinstance(action, Maneuver)
        if item.kind is ConstraintKind.SPECIFIC_MANEUVER:
            if not isinstance(action, Maneuver):
                return False
            if item.source_position is not None and action.source != item.source_position:
                return False
            if item.direction == "left":
                return int(action.destination.front) < int(action.source.front)
            if item.direction == "right":
                return int(action.destination.front) > int(action.source.front)
            return True
        if item.kind is not ConstraintKind.AFFECT_FRONT or item.front is None:
            return False
        front = item.front
        if isinstance(action, (PlayForce, PlayBond, PlayName)):
            return action.position.front == front
        if isinstance(action, Maneuver):
            return action.source.front == front or action.destination.front == front
        if isinstance(action, (PlayNarrative, PlayStratagem)):
            if front in action.fronts:
                return True
            return any(
                target.position.front == front
                for target in action.targets
            )
        return False

    def _card_lifecycle_summary(self) -> dict[str, Any]:
        ids = (
            set(self._card_actions_to_play)
            | set(self._card_turns_to_play)
            | set(self._card_held_boundaries)
            | set(self._card_discarded_unplayed)
            | set(self._card_drawn_after_reshuffle)
            | set(self._card_unplayed_match_end)
            | set(self._card_plays_by_battle)
            | {card_id for (_player, card_id) in self._draw_queues}
        )
        return {
            card_id: {
                "draw_to_play_actions": self._distribution(
                    self._card_actions_to_play.get(card_id, [])
                ),
                "draw_to_play_turns": self._distribution(
                    self._card_turns_to_play.get(card_id, [])
                ),
                "held_across_battle_boundaries": self._card_held_boundaries[card_id],
                "discarded_without_play": self._card_discarded_unplayed[card_id],
                "drawn_after_reshuffle": self._card_drawn_after_reshuffle[card_id],
                "unplayed_at_match_end": self._card_unplayed_match_end[card_id],
                "plays_by_battle": dict(sorted(
                    self._card_plays_by_battle.get(card_id, {}).items()
                )),
            }
            for card_id in sorted(ids)
        }

    def _hero_summary(self) -> dict[str, Any]:
        result = {}
        for card_id, stats in sorted(self._hero_modes.items()):
            force = int(stats["force_plays"])
            name = int(stats["name_plays"])
            total = force + name
            result[card_id] = {
                "force_plays": force,
                "name_plays": name,
                "force_usage_rate": self._ratio(force, total),
                "name_usage_rate": self._ratio(name, total),
                "force_completions": int(stats["force_completions"]),
                "name_completions": int(stats["name_completions"]),
                "mean_force_front_swing": self._ratio(
                    stats["force_front_swing_total"], force
                ),
                "mean_name_front_swing": self._ratio(
                    stats["name_front_swing_total"], name
                ),
                "mean_force_control_swing": self._ratio(
                    stats["force_control_swing_total"], force
                ),
                "mean_name_control_swing": self._ratio(
                    stats["name_control_swing_total"], name
                ),
                "force_battle_end_presence": int(stats["force_battle_end_presence"]),
                "name_battle_end_presence": int(stats["name_battle_end_presence"]),
                "by_battle": {
                    battle: dict(sorted(counts.items()))
                    for battle, counts in sorted(stats["by_battle"].items())
                },
            }
        return result

    def _summarize_battles(
        self,
        battle_records: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        rows_source = (
            self._battle_records
            if battle_records is None
            else battle_records
        )
        for row in rows_source:
            groups[self._battle_key(row["battle"])].append(row)
        result = {}
        for key in ("1", "2", "3", "4-7", "8+"):
            rows = groups.get(key, [])
            if not rows:
                result[key] = {"battles": 0}
                continue
            result[key] = {
                "battles": len(rows),
                "forces_played": self._mean_field(rows, "forces_played"),
                "bonds_played": self._mean_field(rows, "bonds_played"),
                "names_played": self._mean_field(rows, "names_played"),
                "completed_formations": self._mean_field(rows, "completed_formations"),
                "incomplete_formations_end": mean(
                    sum(row["incomplete_at_end"]) for row in rows
                ),
                "occupied_positions": self._mean_field(rows, "mean_total_occupied"),
                "active_fronts": self._mean_field(rows, "mean_active_fronts"),
                "developed_fronts": self._mean_field(rows, "mean_developed_fronts"),
                "contested_fronts": self._mean_field(rows, "mean_contested_fronts"),
                "front_control_changes": self._mean_field(rows, "front_control_changes"),
                "cards_played": self._mean_field(rows, "cards_played"),
                "command_start": mean(
                    value for row in rows for value in row["command_start"]
                ),
                "command_spent": mean(
                    value for row in rows for value in row["command_spent"]
                ),
                "command_refunded": mean(
                    value for row in rows for value in row["command_refunded"]
                ),
                "command_remaining": mean(
                    value for row in rows for value in row["command_remaining"]
                ),
                "command_before_collapse": mean(
                    value for row in rows for value in row["command_before_collapse"]
                ),
                "next_battle_command": self._mean_optional([
                    value
                    for row in rows
                    for value in (row["next_battle_command"] or [])
                ]),
                "hand_size": mean(
                    value for row in rows for value in row["hand_remaining"]
                ),
                "deck_size": mean(
                    value for row in rows for value in row["deck_remaining"]
                ),
                "legal_actions": self._mean_field(rows, "mean_legal_actions"),
                "constraint_rule_source_decisions": self._mean_field(
                    rows, "constraint_source_decisions"
                ),
                "constraint_active_decisions": self._mean_field(
                    rows, "constraint_active_decisions"
                ),
                "constraint_rule_source_rate": self._ratio(
                    sum(row["constraint_source_decisions"] for row in rows),
                    sum(row["actions"] for row in rows),
                ),
                "constraint_active_rate": self._ratio(
                    sum(row["constraint_active_decisions"] for row in rows),
                    sum(row["actions"] for row in rows),
                ),
                "pass_command": self._mean_optional([
                    row.get("pass_command", row.get("first_signal_command")) for row in rows
                ]),
                "first_signal_command": self._mean_optional([
                    row.get("pass_command", row.get("first_signal_command")) for row in rows
                ]),
                "pass_unplayable_cards": self._mean_optional([
                    row.get("pass_unplayable_cards", row.get("first_signal_unplayable_cards")) for row in rows
                ]),
                "first_signal_unplayable_cards": self._mean_optional([
                    row.get("pass_unplayable_cards", row.get("first_signal_unplayable_cards")) for row in rows
                ]),
                "pass_structurally_dead_cards": self._mean_optional([
                    row.get("pass_structurally_dead_cards", row.get("first_signal_structurally_dead_cards")) for row in rows
                ]),
                "first_signal_structurally_dead_cards": self._mean_optional([
                    row.get("pass_structurally_dead_cards", row.get("first_signal_structurally_dead_cards")) for row in rows
                ]),
                "pass_unaffordable_cards": self._mean_optional([
                    row.get("pass_unaffordable_cards", row.get("first_signal_unaffordable_cards")) for row in rows
                ]),
                "first_signal_unaffordable_cards": self._mean_optional([
                    row.get("pass_unaffordable_cards", row.get("first_signal_unaffordable_cards")) for row in rows
                ]),
                "pass_legal_alternatives": self._mean_optional([
                    row.get("pass_legal_alternatives", row.get("first_signal_legal_alternatives")) for row in rows
                ]),
                "first_signal_legal_alternatives": self._mean_optional([
                    row.get("pass_legal_alternatives", row.get("first_signal_legal_alternatives")) for row in rows
                ]),
                "pass_playable_card_actions": self._mean_optional([
                    row.get("pass_playable_card_actions", row.get("first_signal_playable_card_actions")) for row in rows
                ]),
                "first_signal_playable_card_actions": self._mean_optional([
                    row.get("pass_playable_card_actions", row.get("first_signal_playable_card_actions")) for row in rows
                ]),
                "pass_maneuver_actions": self._mean_optional([
                    row.get("pass_maneuver_actions", row.get("first_signal_maneuver_actions")) for row in rows
                ]),
                "first_signal_maneuver_actions": self._mean_optional([
                    row.get("pass_maneuver_actions", row.get("first_signal_maneuver_actions")) for row in rows
                ]),
                "free_maneuvers": self._mean_field(rows, "free_maneuvers"),
                "command_gained": self._mean_field(rows, "command_gained"),
                "eventual_completion_rate_for_forces_deployed": self._ratio(
                    sum(
                        row["completion_action"] is not None
                        for row in self._formations.values()
                        if self._battle_key(row["created_battle"]) == key
                    ),
                    sum(
                        1
                        for row in self._formations.values()
                        if self._battle_key(row["created_battle"]) == key
                    ),
                ),
                "command_end_buckets": {
                    "<0": sum(value < 0 for row in rows for value in row["command_remaining"]),
                    "0": sum(value == 0 for row in rows for value in row["command_remaining"]),
                    "1-3": sum(1 <= value <= 3 for row in rows for value in row["command_remaining"]),
                    "4-6": sum(4 <= value <= 6 for row in rows for value in row["command_remaining"]),
                    "7+": sum(value >= 7 for row in rows for value in row["command_remaining"]),
                },
                "command_before_collapse_buckets": {
                    "<0": sum(value < 0 for row in rows for value in row["command_before_collapse"]),
                    "0": sum(value == 0 for row in rows for value in row["command_before_collapse"]),
                    "1-3": sum(1 <= value <= 3 for row in rows for value in row["command_before_collapse"]),
                    "4-6": sum(4 <= value <= 6 for row in rows for value in row["command_before_collapse"]),
                    "7+": sum(value >= 7 for row in rows for value in row["command_before_collapse"]),
                },
            }
        return result

    def _signal_outcome_group(self, rows: list[dict[str, Any]], predicate) -> dict[str, Any]:
        selected = [row for row in rows if predicate(row)]
        resolved = [
            row for row in selected
            if row["final_front_balance"] is not None
        ]
        balances = [
            int(row["final_front_balance"])
            for row in resolved
        ]
        return {
            "events": len(selected),
            "resolved": len(resolved),
            "mean_final_front_balance": (
                mean(balances) if balances else None
            ),
            "positive_final_front_balance_rate": self._ratio(
                sum(value > 0 for value in balances),
                len(balances),
            ),
        }

    @staticmethod
    def _front_result_balances(front_scores: Any) -> list[int] | None:
        if not front_scores:
            return None
        balances = [0, 0]
        for pair in front_scores:
            left = int(pair[0])
            right = int(pair[1])
            if left > right:
                balances[0] += 1
                balances[1] -= 1
            elif right > left:
                balances[1] += 1
                balances[0] -= 1
        return balances

    @staticmethod
    def _count_complete(state: GameState, player: int) -> int:
        return sum(state.slot(player, position).complete for position in all_positions())

    @staticmethod
    def _count_partial(state: GameState, player: int) -> int:
        return sum(
            state.slot(player, position).force is not None
            and not state.slot(player, position).complete
            for position in all_positions()
        )

    @staticmethod
    def _battle_key(battle: int) -> str:
        if battle <= 3:
            return str(battle)
        if battle <= 7:
            return "4-7"
        return "8+"

    @staticmethod
    def _sign(value: int | float) -> int:
        return 1 if value > 0 else -1 if value < 0 else 0

    @staticmethod
    def _ratio(numerator: float, denominator: float) -> float | None:
        return None if denominator == 0 else numerator / denominator

    @staticmethod
    def _mean_optional(values: list[float | None]) -> float | None:
        present = [value for value in values if value is not None]
        return mean(present) if present else None

    @staticmethod
    def _mean_field(rows: list[dict[str, Any]], field: str) -> float | None:
        return mean(float(row[field]) for row in rows) if rows else None

    @classmethod
    def _distribution(
        cls,
        values: Iterable[int | float],
        *,
        histogram: bool = False,
    ) -> dict[str, Any]:
        data = sorted(float(value) for value in values)
        if not data:
            return {
                "count": 0,
                "mean": None,
                "median": None,
                "p25": None,
                "p75": None,
                "p90": None,
                "min": None,
                "max": None,
                **({"histogram": {}} if histogram else {}),
            }

        def percentile(fraction: float) -> float:
            if len(data) == 1:
                return data[0]
            position = (len(data) - 1) * fraction
            lower = int(position)
            upper = min(lower + 1, len(data) - 1)
            weight = position - lower
            return data[lower] * (1 - weight) + data[upper] * weight

        result = {
            "count": len(data),
            "mean": mean(data),
            "median": median(data),
            "p25": percentile(0.25),
            "p75": percentile(0.75),
            "p90": percentile(0.90),
            "min": data[0],
            "max": data[-1],
        }
        if histogram:
            buckets = Counter(
                "10+" if value >= 10 else str(int(value))
                for value in data
            )
            result["histogram"] = dict(
                sorted(
                    buckets.items(),
                    key=lambda item: (item[0] == "10+", int(item[0].rstrip("+"))),
                )
            )
        return result
