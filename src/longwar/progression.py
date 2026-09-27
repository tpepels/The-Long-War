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
    PlayStory,
    PlayStratagem,
)
from .game.engine import GameEngine, all_positions
from .game.model import Front, GameState, Phase, Position


CARD_ACTIONS = (PlayForce, PlayBond, PlayName, PlayStory, PlayStratagem)
OPERATION_ACTIONS = CARD_ACTIONS + (Maneuver,)
CONSTRAINT_CLASSES = {"necessity"}


class ProgressionTelemetry:
    """Compact, mechanics-only match-progression telemetry.

    This class deliberately records what the engine exposes. Constraint-rule
    cards may be present in a state without being counted as an active
    constraint: effect-active telemetry requires an explicit engine state
    marker, and does not infer rules from prose.
    """

    def __init__(self) -> None:
        self._game_index = -1
        self._action_index = 0
        self._current_action = 0
        self._battle_action = 0
        self._battle_number = 1

        self._next_formation_id = 1
        self._formation_at: dict[tuple[int, Position], int] = {}
        self._formations: dict[int, dict[str, Any]] = {}

        self._battle_events: Counter[str] = Counter()
        self._battle_snapshots: list[dict[str, Any]] = []
        self._battle_records: list[dict[str, Any]] = []
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
        self._pass_plus_one = 0
        self._constraint_source_decisions = 0
        self._constraint_active_decisions = 0
        self._constraint_effect_choice_decisions = 0
        self._effect_choice_decisions = 0
        self._constraint_active_streak = 0
        self._constraint_active_streaks: list[int] = []
        self._pass_contexts: list[dict[str, Any]] = []

        self._command_spend: Counter[str] = Counter()
        self._command_spend_by_battle: dict[str, Counter[str]] = defaultdict(Counter)
        self._command_gained = 0
        self._free_operations = 0
        self._free_maneuvers = 0
        self._discount_actions = 0
        self._discount_command = 0

        self._hero_modes: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
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
        )

        self._draw_queues: dict[tuple[int, str], list[tuple[int, int, int]]] = defaultdict(list)
        self._card_actions_to_play: dict[str, list[int]] = defaultdict(list)
        self._card_turns_to_play: dict[str, list[int]] = defaultdict(list)
        self._card_held_boundaries: Counter[str] = Counter()
        self._card_discarded_unplayed: Counter[str] = Counter()
        self._card_drawn_after_reshuffle: Counter[str] = Counter()
        self._card_unplayed_match_end: Counter[str] = Counter()
        self._card_plays_by_battle: dict[str, Counter[str]] = defaultdict(Counter)
        self._reshuffled_player = [False, False]
        self._formation_age_at_battle_end: list[int] = []

    def start_game(self, engine: GameEngine, state: GameState) -> None:
        self._game_index += 1
        self._action_index = 0
        self._current_action = 0
        self._battle_action = 0
        self._battle_number = state.battle
        self._formation_at = {}
        self._battle_events = Counter()
        self._battle_snapshots = []
        self._last_controllers = None
        self._last_control_balance = None
        self._last_lead_sign = None
        self._battle_control_changes = 0
        self._battle_control_balance_changes = 0
        self._battle_lead_changes = 0
        self._draw_queues = defaultdict(list)
        self._reshuffled_player = [False, False]

        for player in range(2):
            for card_id in state.players[player].hand:
                self.record_draw(player, card_id, state)
        self._initialize_formations(engine, state)

    def record_draw(self, player: int, card_id: str, state: GameState) -> None:
        entry = (self._current_action, int(state.turn_number), int(state.battle))
        self._draw_queues[(player, card_id)].append(entry)
        if self._reshuffled_player[player]:
            self._card_drawn_after_reshuffle[card_id] += 1

    def before_action(
        self,
        engine: GameEngine,
        state: GameState,
        actor: int,
        action: Action,
        legal_actions: Iterable[Action],
    ) -> None:
        self._current_action = self._action_index + 1
        if state.phase is not Phase.BATTLE:
            return

        legal = list(legal_actions)
        if state.pending_draw_discard_for is not None:
            return

        self._battle_action += 1
        card_actions = [candidate for candidate in legal if isinstance(candidate, CARD_ACTIONS)]
        maneuver_actions = [candidate for candidate in legal if isinstance(candidate, Maneuver)]
        pass_actions = [candidate for candidate in legal if isinstance(candidate, Pass)]
        alternatives = [candidate for candidate in legal if not isinstance(candidate, Pass)]
        constraint_sources = self._constraint_rule_sources(engine, state)
        constraint_active = self._constraint_effect_active(state)

        self._choice_legal.append(len(legal))
        self._choice_card.append(len(card_actions))
        self._choice_maneuver.append(len(maneuver_actions))
        self._forced_decisions += int(len(legal) == 1)
        self._forced_maneuvers += int(
            len(legal) == 1 and isinstance(legal[0], Maneuver)
        )
        self._pass_plus_one += int(bool(pass_actions) and len(alternatives) == 1)
        self._constraint_source_decisions += int(bool(constraint_sources))
        self._constraint_active_decisions += int(constraint_active)
        effect_choice_available = any(isinstance(x, EffectChoice) for x in legal)
        self._effect_choice_decisions += int(effect_choice_available)
        self._constraint_effect_choice_decisions += int(
            constraint_active and effect_choice_available
        )
        if constraint_active:
            self._constraint_active_streak += 1
        elif self._constraint_active_streak:
            self._constraint_active_streaks.append(self._constraint_active_streak)
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

        if isinstance(action, PlayForce):
            self._battle_events["forces_played"] += 1
        elif isinstance(action, PlayBond):
            self._battle_events["bonds_played"] += 1
        elif isinstance(action, PlayName):
            self._battle_events["names_played"] += 1
        if isinstance(action, CARD_ACTIONS):
            self._battle_events["cards_played"] += 1

        if isinstance(action, Pass):
            playable_ids = {
                candidate.card_id
                for candidate in card_actions
            }
            hand = Counter(state.players[actor].hand)
            unplayable_copies = sum(
                count for card_id, count in hand.items()
                if card_id not in playable_ids
            )
            margins = list(engine.front_margins(state, actor))
            self._pass_contexts.append({
                "game": self._game_index,
                "battle": state.battle,
                "player": actor,
                "first_pass": len(state.pass_order) == 0,
                "hand_size": len(state.players[actor].hand),
                "playable_cards_remaining": len(playable_ids),
                "unplayable_cards_remaining": unplayable_copies,
                "command_remaining": state.players[actor].command,
                "controlled_fronts": sum(value > 0 for value in margins),
                "tied_fronts": sum(value == 0 for value in margins),
                "lost_fronts": sum(value < 0 for value in margins),
                "total_margin": sum(margins),
                "legal_alternatives": len(alternatives),
                "playable_card_actions": len(card_actions),
                "maneuver_actions": len(maneuver_actions),
                "constraint_active": constraint_active,
                "constraint_rule_sources": constraint_sources,
                "mechanical_category": (
                    "no_alternative"
                    if not alternatives
                    else "one_alternative"
                    if len(alternatives) == 1
                    else "multiple_alternatives"
                ),
                "battle_won": None,
            })

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

        for player in range(2):
            if state.deck_reshuffles[player] > before.deck_reshuffles[player]:
                self._reshuffled_player[player] = True

        self._record_unplayed_discards(before, state, action)

        if battle_resolved:
            self._record_held_across_boundary(before, state)
            self._formation_age_at_battle_end.extend(battle_end_ages)
            self._record_battle_end(engine, before, state)
            self._reset_battle(state)

        self._action_index = self._current_action

    def finish_game(self, state: GameState | None = None) -> None:
        if state is not None:
            for player in range(2):
                for card_id, count in Counter(state.players[player].hand).items():
                    self._card_unplayed_match_end[card_id] += count

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

        by_battle = self._summarize_battles()
        first_pass = [row for row in self._pass_contexts if row["first_pass"]]
        first_pass_outcomes = {
            "ahead": self._pass_outcome_group(first_pass, lambda row: row["total_margin"] > 0),
            "tied": self._pass_outcome_group(first_pass, lambda row: row["total_margin"] == 0),
            "behind": self._pass_outcome_group(first_pass, lambda row: row["total_margin"] < 0),
            "with_playable_alternatives": self._pass_outcome_group(
                first_pass, lambda row: row["legal_alternatives"] > 0
            ),
            "no_alternative": self._pass_outcome_group(
                first_pass, lambda row: row["legal_alternatives"] == 0
            ),
        }

        command_end = [
            value
            for record in self._battle_records
            for value in record["command_remaining"]
        ]
        resource = {
            "command_spend": dict(sorted(self._command_spend.items())),
            "command_spend_by_battle": {
                battle: dict(sorted(counts.items()))
                for battle, counts in sorted(self._command_spend_by_battle.items())
            },
            "command_gained_or_refunded": self._command_gained,
            "free_operations": self._free_operations,
            "free_maneuvers": self._free_maneuvers,
            "discount_actions": self._discount_actions,
            "discount_command_saved": self._discount_command,
            "command_remaining_at_battle_end": self._distribution(command_end),
            "command_end_buckets": {
                "0": sum(value == 0 for value in command_end),
                "1-3": sum(1 <= value <= 3 for value in command_end),
                "4-6": sum(4 <= value <= 6 for value in command_end),
                "7+": sum(value >= 7 for value in command_end),
            },
        }

        battlefield = {
            "battles": len(self._battle_records),
            "occupied_positions": self._distribution(
                [row["mean_total_occupied"] for row in self._battle_records]
            ),
            "active_fronts": self._distribution(
                [row["mean_active_fronts"] for row in self._battle_records]
            ),
            "contested_fronts": self._distribution(
                [row["mean_contested_fronts"] for row in self._battle_records]
            ),
            "complete_formations": self._distribution(
                [row["mean_complete_formations"] for row in self._battle_records]
            ),
            "partial_formations": self._distribution(
                [row["mean_partial_formations"] for row in self._battle_records]
            ),
            "strength_concentration": self._distribution(
                [
                    value
                    for row in self._battle_records
                    for value in row["mean_strength_concentration"]
                    if value is not None
                ]
            ),
        }

        contestability = {
            "front_control_changes_per_battle": self._distribution(
                [row["front_control_changes"] for row in self._battle_records]
            ),
            "control_balance_changes_per_battle": self._distribution(
                [row["control_balance_changes"] for row in self._battle_records]
            ),
            "lead_changes_per_battle": self._distribution(
                [row["lead_changes"] for row in self._battle_records]
            ),
            "actions_per_battle": self._distribution(
                [row["actions"] for row in self._battle_records]
            ),
            "maximum_abs_margin": self._distribution(
                [row["maximum_abs_margin"] for row in self._battle_records]
            ),
            "midpoint_abs_margin": self._distribution(
                [row["midpoint_abs_margin"] for row in self._battle_records]
            ),
            "final_abs_margin": self._distribution(
                [row["final_abs_margin"] for row in self._battle_records]
            ),
            "durable_lead_action": self._distribution(
                [
                    row["durable_lead_action"]
                    for row in self._battle_records
                    if row["durable_lead_action"] is not None
                ]
            ),
            "actions_remaining_after_durable_lead": self._distribution(
                [
                    row["actions_remaining_after_durable_lead"]
                    for row in self._battle_records
                    if row["actions_remaining_after_durable_lead"] is not None
                ]
            ),
            "no_control_change_after_midpoint_rate": self._ratio(
                sum(row["no_control_change_after_midpoint"] for row in self._battle_records),
                len(self._battle_records),
            ),
            "first_pass_outcomes": first_pass_outcomes,
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
            "pass_plus_one_alternative": self._pass_plus_one,
            "pass_plus_one_alternative_rate": self._ratio(
                self._pass_plus_one, len(self._choice_legal)
            ),
            "constraint_rule_source_decisions": self._constraint_source_decisions,
            "constraint_rule_source_rate": self._ratio(
                self._constraint_source_decisions, len(self._choice_legal)
            ),
            "constraint_active_decisions": self._constraint_active_decisions,
            "constraint_active_rate": self._ratio(
                self._constraint_active_decisions, len(self._choice_legal)
            ),
            "constraint_effect_choice_decisions": self._constraint_effect_choice_decisions,
            "constraint_duration_decisions": self._distribution(
                self._constraint_active_streaks
                + ([self._constraint_active_streak] if self._constraint_active_streak else [])
            ),
            "effect_choice_decisions": self._effect_choice_decisions,
            "pass_mechanical_categories": dict(sorted(Counter(
                row["mechanical_category"] for row in self._pass_contexts
            ).items())),
        }

        return {
            "formation_lifecycle": {
                "forces": forces,
                "forces_ever_bonded": ever_bonded,
                "forces_ever_named": ever_named,
                "bonded_formations": len(bonded),
                "completed_formations": len(completed),
                "incomplete_removed_before_completion": len(removed_incomplete),
                "incomplete_at_battle_end": sum(
                    sum(record["incomplete_at_end"]) for record in self._battle_records
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
            "cards": self._card_lifecycle_summary(),
            "hero_modes": self._hero_summary(),
            "by_battle": by_battle,
            "sample_traces": self._sample_traces,
            "definitions": {
                "formation_identity": (
                    "A formation lifecycle is anchored to its Force. Explicit Maneuvers "
                    "and moves preserve that identity; reconciliation then matches unchanged "
                    "positions, component signatures, and Force multisets without creating "
                    "new lifecycles for movement."
                ),
                "partial_formation": "A board position with a Force that is not yet both Bonded and Named.",
                "active_front": "A Front containing at least one Force for either player.",
                "contested_front": "A Front containing at least one Force for both players.",
                "front_control_change": "One Front's controller changes between consecutive operation decisions.",
                "durable_lead": (
                    "Earliest recorded decision state where the eventual Battle winner has "
                    "a positive total-Strength lead that remains positive in every later recorded state."
                ),
                "constraint_rule_source": (
                    "A card marked by canonical rule metadata as necessity/order/constraint "
                    "is present in play. This does not mean its restriction is implemented or active."
                ),
                "constraint_active": (
                    "Requires an explicit engine-exposed active constraint marker. Telemetry "
                    "does not reconstruct hypothetical legality from card text."
                ),
                "card_draw_to_play": (
                    "Physical card copies are not engine-identified, so duplicate copies are "
                    "paired draw-to-play in FIFO order for timing aggregates."
                ),
                "battle_index": "Battle 1, 2 and 3 are separate; all later Battles aggregate into 4+.",
                "command_gained_or_refunded": (
                    "Command gained after an operation beyond its actual paid cost. "
                    "Between-Battle recovery is excluded and remains visible in the Battle-indexed trajectory."
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
        for player in range(2):
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
            for player in range(2)
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
                row["removed_reason"] = (
                    "battle_resolution" if battle_resolved else "effect_or_retreat"
                )

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

        if isinstance(action, OPERATION_ACTIONS) and actual_cost == 0:
            self._free_operations += 1
            self._battle_events["free_operations"] += 1
        if isinstance(action, Maneuver) and actual_cost == 0:
            self._free_maneuvers += 1
            self._battle_events["free_maneuvers"] += 1

        printed = actual_cost
        card_id = action.card_id if isinstance(action, CARD_ACTIONS) else None
        if card_id is not None:
            printed = int(engine.cards.get(card_id, {}).get("command_cost", actual_cost))
        elif isinstance(action, Maneuver):
            printed = int(engine.maneuver_command_cost)
        saved = max(0, printed - actual_cost)
        if saved:
            self._discount_actions += 1
            self._discount_command += saved
            self._battle_events["discount_actions"] += 1

        battle_transition = (
            state.phase is Phase.COMPLETE or state.battle != before.battle
        )
        expected_after = before.players[actor].command - actual_cost
        gained = (
            0
            if battle_transition
            else max(0, state.players[actor].command - expected_after)
        )
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
        for player in range(2):
            added = Counter(state.players[player].discard) - Counter(before.players[player].discard)
            if played_id is not None and player == before.active_player and added.get(played_id, 0):
                added[played_id] -= 1
                if added[played_id] <= 0:
                    del added[played_id]
            for card_id, count in added.items():
                self._card_discarded_unplayed[card_id] += count
                queue = self._draw_queues.get((player, card_id), [])
                for _ in range(min(count, len(queue))):
                    queue.pop(0)

    def _record_held_across_boundary(self, before: GameState, state: GameState) -> None:
        if state.phase is Phase.COMPLETE:
            return
        for player in range(2):
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
        winner = self._battle_winner(front_scores)

        durable_index = None
        if winner is not None:
            oriented = [
                (row["total_strength"][0] - row["total_strength"][1])
                * (1 if winner == 0 else -1)
                for row in rows
            ]
            for index, value in enumerate(oriented):
                if value > 0 and all(later > 0 for later in oriented[index:]):
                    durable_index = index
                    break

        midpoint = len(rows) // 2
        no_change_after_midpoint = all(
            rows[index]["front_controllers"] == rows[midpoint]["front_controllers"]
            for index in range(midpoint, len(rows))
        )

        final_command = [
            int(value)
            for value in snapshot.get(
                "command_remaining",
                [player.command for player in before.players],
            )
        ]

        incomplete_end = [
            self._count_partial(before, player)
            for player in range(2)
        ]
        complete_end = [
            self._count_complete(before, player)
            for player in range(2)
        ]

        record = {
            "game": self._game_index,
            "battle": int(before.battle),
            "actions": len(rows),
            "forces_played": self._battle_events["forces_played"],
            "bonds_played": self._battle_events["bonds_played"],
            "names_played": self._battle_events["names_played"],
            "completed_formations": self._battle_events["completed_formations"],
            "incomplete_at_end": incomplete_end,
            "complete_at_end": complete_end,
            "mean_total_occupied": mean(sum(row["occupied"]) for row in rows),
            "mean_active_fronts": mean(row["active_fronts"] for row in rows),
            "mean_contested_fronts": mean(row["contested_fronts"] for row in rows),
            "mean_complete_formations": mean(sum(row["complete_formations"]) for row in rows),
            "mean_partial_formations": mean(sum(row["partial_formations"]) for row in rows),
            "mean_strength_concentration": [
                self._mean_optional([row["strength_concentration"][player] for row in rows])
                for player in range(2)
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
            "next_battle_command": (
                None
                if state.phase is Phase.COMPLETE
                else [int(player.command) for player in state.players]
            ),
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
            "free_maneuvers": self._battle_events["free_maneuvers"],
            "command_gained": self._battle_events["command_gained"],
        }
        self._battle_records.append(record)

        for pass_row in self._pass_contexts:
            if (
                pass_row["game"] == self._game_index
                and pass_row["battle"] == before.battle
                and pass_row["first_pass"]
                and pass_row["battle_won"] is None
                and winner is not None
            ):
                pass_row["battle_won"] = pass_row["player"] == winner

        for player in range(2):
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
            for player in range(2)
        ]
        complete = [self._count_complete(state, player) for player in range(2)]
        partial = [self._count_partial(state, player) for player in range(2)]
        forces_by_front = [
            [
                sum(
                    state.board[player][int(front)][rank].force is not None
                    for rank in range(2)
                )
                for front in Front
            ]
            for player in range(2)
        ]
        active_fronts = sum(
            forces_by_front[0][int(front)] + forces_by_front[1][int(front)] > 0
            for front in Front
        )
        contested_fronts = sum(
            forces_by_front[0][int(front)] > 0 and forces_by_front[1][int(front)] > 0
            for front in Front
        )
        margins = list(engine.front_margins(state, 0))
        controllers = [self._sign(value) for value in margins]
        strengths = [
            [engine.front_strength(state, player, front) for front in Front]
            for player in range(2)
        ]
        totals = [sum(values) for values in strengths]
        concentration = [
            (max(values) / total if total > 0 else None)
            for values, total in zip(strengths, totals)
        ]
        return {
            "game": self._game_index,
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
            "active_fronts": active_fronts,
            "contested_fronts": contested_fronts,
            "uncontested_fronts": active_fronts - contested_fronts,
            "empty_fronts": len(tuple(Front)) - active_fronts,
            "front_margins": margins,
            "front_controllers": controllers,
            "controlled_fronts": [
                sum(value > 0 for value in margins),
                sum(value < 0 for value in margins),
            ],
            "tied_fronts": sum(value == 0 for value in margins),
            "total_strength": totals,
            "strength_by_front": strengths,
            "strength_concentration": concentration,
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
        for player in range(2):
            for story in state.stories[player]:
                if story.ongoing:
                    card_ids.add(story.card_id)
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
    def _constraint_effect_active(state: GameState) -> bool:
        marker = getattr(state, "active_constraints", None)
        return bool(marker)

    def _card_lifecycle_summary(self) -> dict[str, Any]:
        ids = (
            set(self._card_actions_to_play)
            | set(self._card_turns_to_play)
            | set(self._card_held_boundaries)
            | set(self._card_discarded_unplayed)
            | set(self._card_drawn_after_reshuffle)
            | set(self._card_unplayed_match_end)
            | set(self._card_plays_by_battle)
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

    def _summarize_battles(self) -> dict[str, Any]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self._battle_records:
            groups[self._battle_key(row["battle"])].append(row)
        result = {}
        for key in ("1", "2", "3", "4+"):
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
                    "0": sum(value == 0 for row in rows for value in row["command_remaining"]),
                    "1-3": sum(1 <= value <= 3 for row in rows for value in row["command_remaining"]),
                    "4-6": sum(4 <= value <= 6 for row in rows for value in row["command_remaining"]),
                    "7+": sum(value >= 7 for row in rows for value in row["command_remaining"]),
                },
            }
        return result

    def _pass_outcome_group(self, rows: list[dict[str, Any]], predicate) -> dict[str, Any]:
        selected = [row for row in rows if predicate(row)]
        resolved = [row for row in selected if row["battle_won"] is not None]
        return {
            "events": len(selected),
            "resolved": len(resolved),
            "battle_win_rate": self._ratio(
                sum(bool(row["battle_won"]) for row in resolved),
                len(resolved),
            ),
        }

    @staticmethod
    def _battle_winner(front_scores: Any) -> int | None:
        if not front_scores:
            return None
        wins = [0, 0]
        for pair in front_scores:
            if int(pair[0]) > int(pair[1]):
                wins[0] += 1
            elif int(pair[1]) > int(pair[0]):
                wins[1] += 1
        if wins[0] == wins[1]:
            return None
        return 0 if wins[0] > wins[1] else 1

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
        return str(battle) if battle <= 3 else "4+"

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
