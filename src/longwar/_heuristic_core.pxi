# Heuristic/search tuning. These are policy preferences, not game rules.
DEF HEUR_TERMINAL_WIN_SCORE = 10000.0
DEF HEUR_FRESH_BATTLE_INITIATIVE = 0.70

DEF HEUR_INCOMPLETE_ONE_CARD_LIABILITY = 0.55
DEF HEUR_INCOMPLETE_TWO_CARD_LIABILITY = 1.60

DEF HEUR_CLOSE_FRONT_MARGIN = 3
DEF HEUR_EXPOSED_FRONT_MARGIN = 4
DEF HEUR_COMFORTABLE_FRONT_MARGIN = 5
DEF HEUR_FRONT_MARGIN_CLAMP = 10
DEF HEUR_CLOSE_FRONT_BONUS = 1.25
DEF HEUR_REAR_PERSISTENCE_VALUE = 4.0
DEF HEUR_FRONTLINE_PERSISTENCE_VALUE = 0.75
DEF HEUR_OVERKILL_MARGIN_WEIGHT = 0.45
DEF HEUR_MARGIN_WEIGHT = 0.75
DEF HEUR_FRONT_CONTROL_WEIGHT = 7.0

DEF HEUR_HAND_CARD_WEIGHT = 1.25
DEF HEUR_FORCE_HAND_CAP = 3
DEF HEUR_FORCE_HAND_WEIGHT = 0.35
DEF HEUR_NO_FORCE_PENALTY = 2.0

DEF HEUR_COMMAND_DELTA_WEIGHT = 0.45
DEF HEUR_COLLAPSE_VULNERABILITY_BUFFER = 3
DEF HEUR_COLLAPSE_VULNERABILITY_WEIGHT = 1.20
DEF HEUR_COLLAPSE_OUTCOME_SCORE = 250.0
DEF HEUR_PROJECTED_COMMAND_WEIGHT = 0.35

DEF HEUR_PASSED_BASE_PENALTY = 1.5
DEF HEUR_PASSED_HAND_CAP = 7.0
DEF HEUR_PASSED_HAND_WEIGHT = 0.55
DEF HEUR_PASSED_EXPOSURE_WEIGHT = 1.1
DEF HEUR_RESPONDING_BASE_BONUS = 1.0
DEF HEUR_RESPONDING_HAND_CAP = 5.0
DEF HEUR_RESPONDING_HAND_WEIGHT = 0.4
DEF HEUR_RESPONDING_REACH_WEIGHT = 0.9
DEF HEUR_INCOMPLETE_LIABILITY_WEIGHT = 1.10

DEF HEUR_NAMED_FORMATION_WEIGHT = 1.5
DEF HEUR_NARRATIVE_WEIGHT = 0.75
DEF HEUR_STRATAGEM_WEIGHT = 0.45
DEF HEUR_COMPLETION_OPTION_WEIGHT = 0.45
DEF HEUR_NO_OPTION_SCORE = -32768

DEF HEUR_PROGRESS_ONE_COMPONENT = 0.35
DEF HEUR_PROGRESS_TWO_COMPONENTS = 1.35
DEF HEUR_PROGRESS_COMPLETE = 2.25

DEF HEUR_HAND_FORCE_BASE = 0.45
DEF HEUR_HAND_FORCE_NEED = 0.95
DEF HEUR_HAND_COMPONENT_BASE = 0.35
DEF HEUR_HAND_NAME_NEED = 1.05
DEF HEUR_HAND_BOND_NEED = 0.95
DEF HEUR_HAND_NARRATIVE = 0.40
DEF HEUR_HAND_STRATAGEM = 0.30
DEF HEUR_DISCARDED_FORCE_AVAILABILITY = 0.35

DEF HEUR_STRATEGIC_FORMATION_PROGRESS = 0.85
DEF HEUR_STRATEGIC_HAND_CONSTRUCTION = 0.30
DEF HEUR_STRATEGIC_DECK_SIZE = 0.18
DEF HEUR_STRATEGIC_FUTURE_SETS = 0.55
DEF HEUR_STRATEGIC_FORCE_AVAILABILITY = 0.40
DEF HEUR_STRATEGIC_AFFORDABLE_HAND = 0.12

DEF HEUR_ROLLOUT_COLLAPSE_IMMEDIATE_BUFFER = 1
DEF HEUR_ROLLOUT_COLLAPSE_NEAR_BUFFER = 3
DEF HEUR_ROLLOUT_PASS_IMMEDIATE = 1.50
DEF HEUR_ROLLOUT_PASS_NEAR = 0.55
DEF HEUR_ROLLOUT_PASS_NORMAL = 0.20
DEF HEUR_ROLLOUT_DISCARD = 1.0
DEF HEUR_ROLLOUT_MANEUVER = 0.90
DEF HEUR_ROLLOUT_FORCE = 1.35
DEF HEUR_ROLLOUT_FORCE_PREPARED_BONUS = 0.90
DEF HEUR_ROLLOUT_BOND = 1.0
DEF HEUR_ROLLOUT_BOND_ON_FORCE = 0.80
DEF HEUR_ROLLOUT_BOND_WITH_NAME = 0.35
DEF HEUR_ROLLOUT_NAME = 1.05
DEF HEUR_ROLLOUT_NAME_ON_FORCE = 0.85
DEF HEUR_ROLLOUT_NAME_WITH_BOND = 0.65
DEF HEUR_ROLLOUT_NARRATIVE = 0.75
DEF HEUR_ROLLOUT_ONGOING_NARRATIVE = 0.70
DEF HEUR_ROLLOUT_STRATAGEM = 0.65

DEF HEUR_ORDER_DISCARD_CONSTRUCTION = 0.55
DEF HEUR_ORDER_BOND_ON_FORCE = 0.85
DEF HEUR_ORDER_BOND_PREPARED = 0.25
DEF HEUR_ORDER_NAME_ON_FORCE = 0.90
DEF HEUR_ORDER_NAME_PREPARED = 0.30
DEF HEUR_ORDER_ONGOING_NARRATIVE = 0.20
DEF HEUR_ORDER_STRATAGEM = 0.20
DEF HEUR_ORDER_MANEUVER = 0.15


cdef class NativeHeuristicEvaluator:
    """Compiled heuristic policy, independent of game transitions/search."""

    cdef FastEngine engine

    def __init__(self, FastEngine engine):
        self.engine = engine

    cdef double incomplete_liability_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        """Cards in incomplete formations are lost if the Battle ends now."""
        cdef int local, slot, components
        cdef double value = 0.0
        for local in range(POSITIONS_PER_PLAYER):
            slot = player * POSITIONS_PER_PLAYER + local
            components = (
                (1 if state.force[slot] >= 0 else 0)
                + (1 if state.bond[slot] >= 0 else 0)
                + (1 if state.name[slot] >= 0 else 0)
            )
            if components == 1:
                value += HEUR_INCOMPLETE_ONE_CARD_LIABILITY
            elif components == 2:
                value += HEUR_INCOMPLETE_TWO_CARD_LIABILITY
        return value

    cdef double evaluate_fast(self, FastState state, int player) noexcept:
        cdef int opponent = other_player(player)
        cdef int front, margin, raw_margin, controls=0, enemy_controls=0
        cdef int hand_delta, named_delta=0, narrative_delta=0, strat_delta=0
        cdef int exposed=0, reachable=0, slot, name_card, before, after, best
        cdef int card, own_forces=0, own_board_forces=0, hero_force=0
        cdef int own_losses=0, opponent_losses=0
        cdef int own_front_slot, own_rear_slot, opp_front_slot, opp_rear_slot
        cdef int recovery=0, own_recovery=0, opponent_recovery=0
        cdef int own_after_loss=0, opponent_after_loss=0
        cdef int own_projected=0, opponent_projected=0
        cdef int current_delta=0, projected_delta=0
        cdef int own_vulnerability=0, opponent_vulnerability=0
        cdef double own_liability=0.0, opponent_liability=0.0
        cdef double score = 0.0, option = 0.0

        if state.phase == PHASE_COMPLETE:
            if state.winner < 0:
                return 0.0
            return HEUR_TERMINAL_WIN_SCORE if state.winner == player else -HEUR_TERMINAL_WIN_SCORE

        # The first player of a fresh Battle gets the first operation after
        # the normal start-of-turn draw. This is the concrete value of being
        # the first player to Pass in the previous Battle.
        if (
            state.operations_this_battle[0] == 0
            and state.operations_this_battle[1] == 0
            and state.pass_len == 0
        ):
            score += HEUR_FRESH_BATTLE_INITIATIVE if state.active_player == player else -HEUR_FRESH_BATTLE_INITIATIVE

        for front in range(FRONT_COUNT):
            raw_margin = (
                _fe_front_strength_fast(self.engine, state, player, front)
                - _fe_front_strength_fast(self.engine, state, opponent, front)
            )
            margin = raw_margin

            if raw_margin > 0:
                controls += 1
                opponent_losses += 1
                if raw_margin <= HEUR_CLOSE_FRONT_MARGIN:
                    score += HEUR_CLOSE_FRONT_BONUS
                if raw_margin <= HEUR_EXPOSED_FRONT_MARGIN:
                    exposed += 1

                # A lost Front drives off a Rear Named Formation and only
                # Retreats a Frontline Named Formation. Value persistence,
                # not just current Strength.
                opp_front_slot = slot_index(opponent, front, RANK_FRONT)
                opp_rear_slot = slot_index(opponent, front, RANK_REAR)
                if _fe_slot_complete(self.engine, state, opp_rear_slot):
                    score += HEUR_REAR_PERSISTENCE_VALUE
                if _fe_slot_complete(self.engine, state, opp_front_slot):
                    score += HEUR_FRONTLINE_PERSISTENCE_VALUE

                # Margin beyond a comfortable buffer has no core scoring
                # value. Keep a little value for resilience, but strongly
                # prefer Strength that can change another Front result.
                if raw_margin > HEUR_COMFORTABLE_FRONT_MARGIN:
                    score -= HEUR_OVERKILL_MARGIN_WEIGHT * (raw_margin - HEUR_COMFORTABLE_FRONT_MARGIN)

            elif raw_margin < 0:
                enemy_controls += 1
                own_losses += 1
                if raw_margin >= -HEUR_CLOSE_FRONT_MARGIN:
                    score -= HEUR_CLOSE_FRONT_BONUS
                if raw_margin >= -HEUR_EXPOSED_FRONT_MARGIN:
                    reachable += 1

                own_front_slot = slot_index(player, front, RANK_FRONT)
                own_rear_slot = slot_index(player, front, RANK_REAR)
                if _fe_slot_complete(self.engine, state, own_rear_slot):
                    score -= HEUR_REAR_PERSISTENCE_VALUE
                if _fe_slot_complete(self.engine, state, own_front_slot):
                    score -= HEUR_FRONTLINE_PERSISTENCE_VALUE

                if raw_margin < -HEUR_COMFORTABLE_FRONT_MARGIN:
                    score += HEUR_OVERKILL_MARGIN_WEIGHT * ((-raw_margin) - HEUR_COMFORTABLE_FRONT_MARGIN)
            else:
                reachable += 1

            if margin > HEUR_FRONT_MARGIN_CLAMP:
                margin = HEUR_FRONT_MARGIN_CLAMP
            elif margin < -HEUR_FRONT_MARGIN_CLAMP:
                margin = -HEUR_FRONT_MARGIN_CLAMP
            score += HEUR_FRONTLINE_PERSISTENCE_VALUE * margin

        score += HEUR_FRONT_CONTROL_WEIGHT * (controls - enemy_controls)

        hand_delta = state.hand_len[player] - state.hand_len[opponent]
        score += HEUR_CLOSE_FRONT_BONUS * hand_delta

        for card in range(self.engine.n_cards):
            if self.engine.card_type[card] == CARD_FORCE:
                if self.engine.hero[card]:
                    if (
                        not state.hero_used[player]
                        and state.hand[player][card] > 0
                    ):
                        hero_force = 1
                else:
                    own_forces += state.hand[player][card]
        own_forces += hero_force
        if own_forces > HEUR_FORCE_HAND_CAP:
            own_forces = HEUR_FORCE_HAND_CAP
        score += HEUR_FORCE_HAND_WEIGHT * own_forces

        for slot in range(player * POSITIONS_PER_PLAYER, (player + 1) * POSITIONS_PER_PLAYER):
            if state.force[slot] >= 0:
                own_board_forces += 1
        if own_forces == 0 and own_board_forces == 0:
            score -= HEUR_NO_FORCE_PENALTY

        current_delta = state.command[player] - state.command[opponent]
        score += HEUR_COMMAND_DELTA_WEIGHT * current_delta

        # Collapse is checked on current Command before recovery. With the
        # zero-Command rule, preserving even 1 Command can decide whether a
        # side survives long enough to receive the next recovery.
        own_vulnerability = (
            self.engine.command_collapse_threshold + HEUR_COLLAPSE_VULNERABILITY_BUFFER
            - state.command[player]
        )
        if own_vulnerability < 0:
            own_vulnerability = 0
        opponent_vulnerability = (
            self.engine.command_collapse_threshold + HEUR_COLLAPSE_VULNERABILITY_BUFFER
            - state.command[opponent]
        )
        if opponent_vulnerability < 0:
            opponent_vulnerability = 0
        score += HEUR_COLLAPSE_VULNERABILITY_WEIGHT * (
            opponent_vulnerability - own_vulnerability
        )

        own_after_loss = state.command[player] - own_losses
        if own_after_loss < 0:
            own_after_loss = 0
        opponent_after_loss = state.command[opponent] - opponent_losses
        if opponent_after_loss < 0:
            opponent_after_loss = 0

        if (
            (
                own_after_loss <= self.engine.command_collapse_threshold
                or opponent_after_loss <= self.engine.command_collapse_threshold
            )
            and own_after_loss != opponent_after_loss
        ):
            if own_after_loss < opponent_after_loss:
                score -= HEUR_COLLAPSE_OUTCOME_SCORE
            else:
                score += HEUR_COLLAPSE_OUTCOME_SCORE
        else:
            # Front losses have already been applied to projected Command.
            # Recovery is relevant only after surviving the Collapse check.
            recovery = _fe_command_recovery_fast(self.engine, state.battle)
            own_recovery = recovery
            if own_recovery < self.engine.command_recovery_floor:
                own_recovery = self.engine.command_recovery_floor
            opponent_recovery = recovery
            if opponent_recovery < self.engine.command_recovery_floor:
                opponent_recovery = self.engine.command_recovery_floor
            own_projected = own_after_loss + own_recovery
            opponent_projected = (
                opponent_after_loss + opponent_recovery
            )
            if own_projected > self.engine.command_cap:
                own_projected = self.engine.command_cap
            if opponent_projected > self.engine.command_cap:
                opponent_projected = self.engine.command_cap

            projected_delta = own_projected - opponent_projected
            score += HEUR_PROJECTED_COMMAND_WEIGHT * (projected_delta - current_delta)

        if (
            state.phase == PHASE_BATTLE
            and state.passed[player] != state.passed[opponent]
        ):
            if state.passed[player]:
                score -= (
                    HEUR_PASSED_BASE_PENALTY
                    + min(HEUR_PASSED_HAND_CAP, HEUR_PASSED_HAND_WEIGHT * state.hand_len[opponent])
                    + HEUR_PASSED_EXPOSURE_WEIGHT * exposed
                )
            else:
                score += (
                    HEUR_RESPONDING_BASE_BONUS
                    + min(HEUR_RESPONDING_HAND_CAP, HEUR_RESPONDING_HAND_WEIGHT * state.hand_len[player])
                    + HEUR_RESPONDING_REACH_WEIGHT * reachable
                )

            # Once one Pass is pending, the Battle can end on the current
            # turn. Incomplete formations are then discarded before Retreat,
            # so two-card preparations become genuine short-term liabilities.
            own_liability = self.incomplete_liability_fast(state, player)
            opponent_liability = self.incomplete_liability_fast(
                state,
                opponent,
            )
            score += HEUR_INCOMPLETE_LIABILITY_WEIGHT * (opponent_liability - own_liability)

        for slot in range(player * POSITIONS_PER_PLAYER, (player + 1) * POSITIONS_PER_PLAYER):
            if _fe_slot_complete(self.engine, state, slot):
                named_delta += 1
        for slot in range(opponent * POSITIONS_PER_PLAYER, (opponent + 1) * POSITIONS_PER_PLAYER):
            if _fe_slot_complete(self.engine, state, slot):
                named_delta -= 1
        score += HEUR_NAMED_FORMATION_WEIGHT * named_delta

        for front in range(self.engine.ongoing_narrative_limit):
            if state.narrative[player * NARRATIVE_SLOTS_PER_PLAYER + front] >= 0:
                narrative_delta += 1
            if state.narrative[opponent * NARRATIVE_SLOTS_PER_PLAYER + front] >= 0:
                narrative_delta -= 1
        score += HEUR_FRONTLINE_PERSISTENCE_VALUE * narrative_delta

        strat_delta = (
            (1 if state.stratagem[player] >= 0 else 0)
            - (1 if state.stratagem[opponent] >= 0 else 0)
        )
        score += HEUR_STRATAGEM_WEIGHT * strat_delta

        for slot in range(player * POSITIONS_PER_PLAYER, (player + 1) * POSITIONS_PER_PLAYER):
            if state.force[slot] < 0 or state.name[slot] >= 0:
                continue
            before = _fe_position_strength_fast(self.engine, state, slot)
            best = HEUR_NO_OPTION_SCORE
            for name_card in range(self.engine.n_cards):
                if state.hand[player][name_card] == 0:
                    continue
                if self.engine.card_type[name_card] != CARD_NAME:
                    if (
                        not self.engine.hero[name_card]
                        or state.hero_used[player]
                    ):
                        continue
                state.name[slot] = name_card
                after = _fe_position_strength_fast(self.engine, state, slot)
                if after - before > best:
                    best = after - before
                state.name[slot] = -1
            if best > 0:
                option += HEUR_COMPLETION_OPTION_WEIGHT * best
        score += option

        return score

    cdef double formation_progress_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int local, slot, components
        cdef double value = 0.0
        for local in range(POSITIONS_PER_PLAYER):
            slot = player * POSITIONS_PER_PLAYER + local
            components = (
                (1 if state.force[slot] >= 0 else 0)
                + (1 if state.bond[slot] >= 0 else 0)
                + (1 if state.name[slot] >= 0 else 0)
            )
            if components == 1:
                value += HEUR_PROGRESS_ONE_COMPONENT
            elif components == 2:
                value += HEUR_PROGRESS_TWO_COMPONENTS
            elif components == 3:
                value += HEUR_PROGRESS_COMPLETE
        return value

    cdef double hand_construction_value_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef bint needs_force=False, needs_bond=False, needs_name=False
        cdef int local, slot, card, count, typ
        cdef double value=0.0, force_value=0.0, name_value=0.0
        for local in range(POSITIONS_PER_PLAYER):
            slot = player * POSITIONS_PER_PLAYER + local
            if state.force[slot] < 0 and (
                state.bond[slot] >= 0 or state.name[slot] >= 0
            ):
                needs_force = True
            if state.bond[slot] < 0 and (
                state.force[slot] >= 0 or state.name[slot] >= 0
            ):
                needs_bond = True
            if state.name[slot] < 0 and (
                state.force[slot] >= 0 or state.bond[slot] >= 0
            ):
                needs_name = True

        for card in range(self.engine.n_cards):
            count = state.hand[player][card]
            if count == 0:
                continue
            typ = self.engine.card_type[card]
            if typ == CARD_FORCE:
                force_value = HEUR_HAND_FORCE_BASE + (HEUR_HAND_FORCE_NEED if needs_force else 0.0)
                if self.engine.hero[card]:
                    if state.hero_used[player]:
                        continue
                    name_value = HEUR_HAND_COMPONENT_BASE + (HEUR_HAND_NAME_NEED if needs_name else 0.0)
                    value += count * (
                        force_value
                        if force_value >= name_value
                        else name_value
                    )
                else:
                    value += count * force_value
            elif typ == CARD_BOND:
                value += count * (HEUR_HAND_COMPONENT_BASE + (HEUR_HAND_BOND_NEED if needs_bond else 0.0))
            elif typ == CARD_NAME:
                value += count * (HEUR_HAND_COMPONENT_BASE + (HEUR_HAND_NAME_NEED if needs_name else 0.0))
            elif typ == CARD_NARRATIVE:
                value += count * HEUR_HAND_NARRATIVE
            elif typ == CARD_STRATAGEM:
                value += count * HEUR_HAND_STRATAGEM
        return value

    cdef int future_formation_sets_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int card, count, forces=0, bonds=0, names=0, heroes=0
        cdef int value, candidate
        for card in range(self.engine.n_cards):
            count = state.hand[player][card] + state.deck_counts[player][card]
            if self.engine.card_type[card] == CARD_FORCE:
                if self.engine.hero[card]:
                    heroes += count
                else:
                    forces += count
            elif self.engine.card_type[card] == CARD_BOND:
                bonds += count
            elif self.engine.card_type[card] == CARD_NAME:
                names += count
        value = forces
        if bonds < value:
            value = bonds
        if names < value:
            value = names
        if heroes > 0 and not state.hero_used[player]:
            candidate = forces + 1
            if bonds < candidate:
                candidate = bonds
            if names < candidate:
                candidate = names
            if candidate > value:
                value = candidate

            candidate = forces
            if bonds < candidate:
                candidate = bonds
            if names + 1 < candidate:
                candidate = names + 1
            if candidate > value:
                value = candidate
        return value

    cdef double future_force_availability_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int card, i, immediate=0, discarded=0
        cdef bint hero_available=False, discarded_hero=False
        for card in range(self.engine.n_cards):
            if self.engine.card_type[card] == CARD_FORCE:
                if self.engine.hero[card]:
                    if (
                        not state.hero_used[player]
                        and (
                            state.hand[player][card]
                            + state.deck_counts[player][card]
                        ) > 0
                    ):
                        hero_available = True
                else:
                    immediate += (
                        state.hand[player][card]
                        + state.deck_counts[player][card]
                    )
        for i in range(state.discard_len[player]):
            card = state.discard[player][i]
            if self.engine.card_type[card] == CARD_FORCE:
                if self.engine.hero[card]:
                    if not state.hero_used[player]:
                        discarded_hero = True
                else:
                    discarded += 1
        return (
            immediate
            + (1.0 if hero_available else 0.0)
            + HEUR_DISCARDED_FORCE_AVAILABILITY * (
                discarded + (1 if discarded_hero else 0)
            )
        )

    cdef int affordable_hand_count_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int card, total=0
        for card in range(self.engine.n_cards):
            if (
                state.hand[player][card]
                and self.engine.card_command_cost[card] <= state.command[player]
            ):
                total += state.hand[player][card]
        return total

    cdef double strategic_evaluate_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int opponent = other_player(player)
        cdef double value = self.evaluate_fast(state, player)
        if state.phase == PHASE_COMPLETE:
            return value

        value += HEUR_STRATEGIC_FORMATION_PROGRESS * (
            self.formation_progress_fast(state, player)
            - self.formation_progress_fast(state, opponent)
        )
        value += HEUR_STRATEGIC_HAND_CONSTRUCTION * (
            self.hand_construction_value_fast(state, player)
            - self.hand_construction_value_fast(state, opponent)
        )

        value += HEUR_STRATEGIC_DECK_SIZE * (
            state.deck_len[player] - state.deck_len[opponent]
        )
        value += HEUR_INCOMPLETE_ONE_CARD_LIABILITY * (
            self.future_formation_sets_fast(state, player)
            - self.future_formation_sets_fast(state, opponent)
        )
        value += HEUR_STRATEGIC_FORCE_AVAILABILITY * (
            self.future_force_availability_fast(state, player)
            - self.future_force_availability_fast(state, opponent)
        )
        value += HEUR_STRATEGIC_AFFORDABLE_HAND * (
            self.affordable_hand_count_fast(state, player)
            - self.affordable_hand_count_fast(state, opponent)
        )

        return value

    cdef double battle_boundary_evaluate_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        # Battle resolution already applied cleanup and Retreat, checked
        # Command Collapse, and recovered only if the war survived. The
        # resulting state is the correct strategic leaf.
        return self.strategic_evaluate_fast(state, player)

    cdef double pass_score_fast(
        self,
        FastState state,
        int player,
        FastState child,
    ):
        child.copy_from_fast(state)
        _fe_pass_action(self.engine, child, player)

        # If this signal ends the Battle, the exact transition has already
        # resolved cleanup and Retreat, checked Collapse, applied surviving
        # recovery, and set next initiative.
        if child.phase != PHASE_BATTLE or child.battle != state.battle:
            return self.battle_boundary_evaluate_fast(child, player)

        # Otherwise evaluate the actual post-signal state. This also handles
        # the experimental free flag, which deliberately leaves the same
        # player on turn until they take their normal operation.
        return self.evaluate_fast(child, player)

    cdef bint action_needs_command_guard_probe_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
    ) noexcept:
        """Whether an action can reach the configured Collapse boundary."""
        cdef int cost = _fe_command_cost_fast(self.engine, state, action)
        cdef int margin = (
            state.command[player] - self.engine.command_collapse_threshold
        )
        return margin <= 0 or cost >= margin

    cdef bint action_exhausts_command_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
        FastState child,
    ):
        """True when this action avoidably leaves one side at Collapse Command."""
        cdef int opponent = other_player(player)
        child.copy_from_fast(state)
        _fe_apply_fast(self.engine, child, action)
        if child.phase == PHASE_COMPLETE and child.winner == player:
            return False
        return (
            child.command[player] <= self.engine.command_collapse_threshold
            and child.command[opponent] > self.engine.command_collapse_threshold
        )

    cpdef tuple command_preserving_action_codes(self, FastState state):
        """Return legal native actions after the final Command blunder shield."""
        cdef uint64_t actions[MAX_ACTIONS]
        cdef uint64_t safe[MAX_ACTIONS]
        cdef FastState child = FastState()
        cdef int n = _fe_legal_actions_into(self.engine, state, &actions[0])
        cdef int actor = state.active_player
        cdef int i, safe_n = 0

        if n <= 1:
            return ([actions[i] for i in range(n)], 0)

        for i in range(n):
            if (
                not self.action_needs_command_guard_probe_fast(
                    state, actor, actions[i]
                )
                or not self.action_exhausts_command_fast(
                    state, actor, actions[i], child
                )
            ):
                safe[safe_n] = actions[i]
                safe_n += 1

        if safe_n == 0:
            return ([actions[i] for i in range(n)], 0)
        return ([safe[i] for i in range(safe_n)], n - safe_n)

    cdef double rollout_prior_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
    ) noexcept:
        """Cheap stochastic-rollout prior; never copies or advances state."""
        cdef int kind = action_kind(action)
        cdef int pos = action_pos(action)
        cdef double weight = HEUR_ROLLOUT_BOND

        if kind == TYPE_PASS:
            if (
                state.command[player]
                <= self.engine.command_collapse_threshold + HEUR_ROLLOUT_COLLAPSE_IMMEDIATE_BUFFER
            ):
                return HEUR_ROLLOUT_PASS_IMMEDIATE
            if (
                state.command[player]
                <= self.engine.command_collapse_threshold + HEUR_COLLAPSE_VULNERABILITY_BUFFER
            ):
                return HEUR_ROLLOUT_PASS_NEAR
            return HEUR_ROLLOUT_PASS_NORMAL
        if kind == TYPE_DISCARD:
            return HEUR_ROLLOUT_DISCARD
        if kind == TYPE_MANEUVER:
            return HEUR_ROLLOUT_MANEUVER
        if kind == TYPE_FORCE:
            weight = HEUR_ROLLOUT_FORCE
            if pos >= 0 and (
                state.bond[pos] >= 0 or state.name[pos] >= 0
            ):
                weight += HEUR_ROLLOUT_FORCE_PREPARED_BONUS
            return weight
        if kind == TYPE_BOND:
            weight = HEUR_ROLLOUT_BOND
            if pos >= 0 and state.force[pos] >= 0:
                weight += HEUR_ROLLOUT_BOND_ON_FORCE
            if pos >= 0 and state.name[pos] >= 0:
                weight += HEUR_ROLLOUT_BOND_WITH_NAME
            return weight
        if kind == TYPE_NAME:
            weight = HEUR_ROLLOUT_BOND5
            if pos >= 0 and state.force[pos] >= 0:
                weight += HEUR_ROLLOUT_NAME_ON_FORCE
            if pos >= 0 and state.bond[pos] >= 0:
                weight += HEUR_ROLLOUT_NAME_WITH_BOND
            return weight
        if kind == TYPE_NARRATIVE:
            return HEUR_ROLLOUT_NARRATIVE
        if kind == TYPE_ONGOING_NARRATIVE:
            return HEUR_ROLLOUT_ONGOING_NARRATIVE
        if kind == TYPE_STRATAGEM:
            return HEUR_ROLLOUT_STRATAGEM
        return 1.0

    cdef double action_order_score_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
        FastState child,
    ):
        cdef int kind = action_kind(action)
        cdef int pos = action_pos(action)
        cdef int force_count=0, card, front, margin_before=0, margin_after=0
        cdef double score

        if kind == TYPE_PASS:
            return self.pass_score_fast(state, player, child)

        if kind == TYPE_DISCARD:
            child.copy_from_fast(state)
            card = action_card(action)
            _fe_take_from_hand(self.engine, child, player, card, 0)
            score = self.evaluate_fast(child, player)
            score += HEUR_ORDER_DISCARD_CONSTRUCTION * self.hand_construction_value_fast(
                child,
                player,
            )
            return score

        child.copy_from_fast(state)
        _fe_apply_fast(self.engine, child, action)
        score = self.evaluate_fast(child, player)

        if kind == TYPE_BOND:
            if state.force[pos] >= 0:
                score += HEUR_ORDER_BOND_ON_FORCE
            else:
                score += HEUR_ORDER_BOND_PREPARED
        elif kind == TYPE_NAME:
            if state.force[pos] >= 0:
                score += HEUR_ORDER_NAME_ON_FORCE
            else:
                score += HEUR_ORDER_NAME_PREPARED
        elif kind == TYPE_ONGOING_NARRATIVE:
            score += HEUR_ORDER_ONGOING_NARRATIVE
        elif kind == TYPE_STRATAGEM:
            score += HEUR_ORDER_STRATAGEM
        elif kind == TYPE_MANEUVER:
            score += HEUR_ORDER_MANEUVER

        return score

    cpdef double evaluate(self, FastState state, int player):
        return self.evaluate_fast(state, player)

    cpdef double strategic_evaluate(self, FastState state, int player):
        return self.strategic_evaluate_fast(state, player)

    cpdef double battle_boundary_evaluate(
        self,
        FastState state,
        int player,
    ):
        return self.battle_boundary_evaluate_fast(state, player)

    cpdef double hand_construction_value(
        self,
        FastState state,
        int player,
    ):
        return self.hand_construction_value_fast(state, player)

    cpdef double score_action(
        self,
        FastState state,
        int player,
        uint64_t action,
    ):
        cdef FastState scratch = FastState()
        return self.action_order_score_fast(
            state,
            player,
            action,
            scratch,
        )
