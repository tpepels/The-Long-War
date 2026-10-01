# Heuristic/search tuning is runtime policy configuration copied into C storage.
include "_heuristic_weights.generated.pxi"


cdef class NativeHeuristicEvaluator:
    """Compiled heuristic policy, independent of game transitions/search."""

    cdef FastEngine engine
    cdef double weights[HEUR_WEIGHT_COUNT]

    def __init__(self, FastEngine engine, weights=None):
        cdef int i
        cdef double value
        cdef object raw
        self.engine = engine
        _heuristic_load_defaults(&self.weights[0])
        if weights is None:
            return
        raw = getattr(weights, "values", weights)
        if len(raw) != HEUR_WEIGHT_COUNT:
            raise ValueError(
                f"expected {HEUR_WEIGHT_COUNT} heuristic values, got {len(raw)}"
            )
        for i in range(HEUR_WEIGHT_COUNT):
            value = float(raw[i])
            if value != value:
                raise ValueError("heuristic values must not be NaN")
            self.weights[i] = value

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
                value += self.weights[HW_INCOMPLETE_ONE_CARD_LIABILITY]
            elif components == 2:
                value += self.weights[HW_INCOMPLETE_TWO_CARD_LIABILITY]
        return value

    cdef double battle_end_urgency_fast(
        self,
        FastState state,
    ) noexcept:
        """Return 0..1 pressure from the configured Battle-ending rule."""
        cdef int remaining
        if state.phase != PHASE_BATTLE or state.pass_len <= 0:
            return 0.0
        if self.engine.pass_closing_rounds <= 0:
            return 1.0
        remaining = state.pass_closing_turns_remaining
        if remaining <= 1:
            return 1.0
        return 1.0 / remaining

    cdef int projected_front_loss_command_penalty_fast(
        self,
        FastState state,
        int player,
        uint16_t lost_mask,
    ) noexcept:
        """Project configured lost-Front Command loss using active protection."""
        cdef int front, rank, card, strat, protected
        cdef int penalty = (
            popcount16(lost_mask & FRONT_MASK)
            * self.engine.lost_front_command_penalty
        )
        if penalty <= 0:
            return 0

        for front in range(FRONT_COUNT):
            if not (lost_mask & (1 << front)):
                continue
            for rank in range(RANK_COUNT):
                card = state.force[slot_index(player, front, rank)]
                if card >= 0 and self.engine.front_loss_protected_front[card]:
                    protected = self.engine.lost_front_command_penalty
                    if protected > penalty:
                        protected = penalty
                    penalty -= protected
                    break

        strat = state.stratagem[player]
        if (
            penalty > 0
            and strat >= 0
            and self.engine.strat_front_loss_protection[strat]
        ):
            protected = (
                self.engine.strat_front_loss_protection[strat]
                * self.engine.lost_front_command_penalty
            )
            if protected > penalty:
                protected = penalty
            penalty -= protected
        return penalty

    cdef double evaluate_fast(self, FastState state, int player) noexcept:
        cdef int opponent = other_player(player)
        cdef int front, margin, raw_margin, controls=0, enemy_controls=0
        cdef int hand_delta, named_delta=0, narrative_delta=0, strat_delta=0
        cdef int exposed=0, reachable=0, slot, name_card, before, after
        cdef double best
        cdef int card, own_forces=0, own_board_forces=0, hero_force=0
        cdef int own_losses=0, opponent_losses=0
        cdef uint16_t own_lost_mask=0, opponent_lost_mask=0
        cdef int own_front_slot, own_rear_slot, opp_front_slot, opp_rear_slot
        cdef int recovery=0, own_recovery=0, opponent_recovery=0
        cdef int own_after_loss=0, opponent_after_loss=0
        cdef int own_projected=0, opponent_projected=0
        cdef int current_delta=0, projected_delta=0
        cdef int own_vulnerability=0, opponent_vulnerability=0
        cdef double own_liability=0.0, opponent_liability=0.0
        cdef double score = 0.0, option = 0.0, battle_end_urgency = 0.0

        if state.phase == PHASE_COMPLETE:
            if state.winner < 0:
                return 0.0
            return self.weights[HW_TERMINAL_WIN_SCORE] if state.winner == player else -self.weights[HW_TERMINAL_WIN_SCORE]

        # The first player of a fresh Battle gets the first operation after
        # the normal start-of-turn draw. This is the concrete value of being
        # the first player to Pass in the previous Battle.
        if (
            state.operations_this_battle[0] == 0
            and state.operations_this_battle[1] == 0
            and state.pass_len == 0
        ):
            score += self.weights[HW_FRESH_BATTLE_INITIATIVE] if state.active_player == player else -self.weights[HW_FRESH_BATTLE_INITIATIVE]

        for front in range(FRONT_COUNT):
            raw_margin = (
                _fe_front_strength_fast(self.engine, state, player, front)
                - _fe_front_strength_fast(self.engine, state, opponent, front)
            )
            margin = raw_margin

            if raw_margin > 0:
                controls += 1
                opponent_lost_mask |= <uint16_t>(1 << front)
                if raw_margin <= self.weights[HW_CLOSE_FRONT_MARGIN]:
                    score += self.weights[HW_CLOSE_FRONT_BONUS]
                if raw_margin <= self.weights[HW_EXPOSED_FRONT_MARGIN]:
                    exposed += 1

                # A lost Front drives off a Rear Named Formation and only
                # Retreats a Frontline Named Formation. Value persistence,
                # not just current Strength.
                opp_front_slot = slot_index(opponent, front, RANK_FRONT)
                opp_rear_slot = slot_index(opponent, front, RANK_REAR)
                if _fe_slot_complete(self.engine, state, opp_rear_slot):
                    score += self.weights[HW_REAR_PERSISTENCE_VALUE]
                if _fe_slot_complete(self.engine, state, opp_front_slot):
                    score += self.weights[HW_FRONTLINE_PERSISTENCE_VALUE]

                # Margin beyond a comfortable buffer has no core scoring
                # value. Keep a little value for resilience, but strongly
                # prefer Strength that can change another Front result.
                if raw_margin > self.weights[HW_COMFORTABLE_FRONT_MARGIN]:
                    score -= self.weights[HW_OVERKILL_MARGIN_WEIGHT] * (raw_margin - self.weights[HW_COMFORTABLE_FRONT_MARGIN])

            elif raw_margin < 0:
                enemy_controls += 1
                own_lost_mask |= <uint16_t>(1 << front)
                if raw_margin >= -self.weights[HW_CLOSE_FRONT_MARGIN]:
                    score -= self.weights[HW_CLOSE_FRONT_BONUS]
                if raw_margin >= -self.weights[HW_EXPOSED_FRONT_MARGIN]:
                    reachable += 1

                own_front_slot = slot_index(player, front, RANK_FRONT)
                own_rear_slot = slot_index(player, front, RANK_REAR)
                if _fe_slot_complete(self.engine, state, own_rear_slot):
                    score -= self.weights[HW_REAR_PERSISTENCE_VALUE]
                if _fe_slot_complete(self.engine, state, own_front_slot):
                    score -= self.weights[HW_FRONTLINE_PERSISTENCE_VALUE]

                if raw_margin < -self.weights[HW_COMFORTABLE_FRONT_MARGIN]:
                    score += self.weights[HW_OVERKILL_MARGIN_WEIGHT] * ((-raw_margin) - self.weights[HW_COMFORTABLE_FRONT_MARGIN])
            else:
                reachable += 1

            if margin > self.weights[HW_FRONT_MARGIN_CLAMP]:
                margin = <int>self.weights[HW_FRONT_MARGIN_CLAMP]
            elif margin < -self.weights[HW_FRONT_MARGIN_CLAMP]:
                margin = -<int>self.weights[HW_FRONT_MARGIN_CLAMP]
            score += self.weights[HW_FRONTLINE_PERSISTENCE_VALUE] * margin

        own_losses = self.projected_front_loss_command_penalty_fast(
            state, player, own_lost_mask
        )
        opponent_losses = self.projected_front_loss_command_penalty_fast(
            state, opponent, opponent_lost_mask
        )

        score += self.weights[HW_FRONT_CONTROL_WEIGHT] * (controls - enemy_controls)

        hand_delta = state.hand_len[player] - state.hand_len[opponent]
        score += self.weights[HW_CLOSE_FRONT_BONUS] * hand_delta

        for card in range(self.engine.n_cards):
            if self.engine.card_type[card] == CARD_FORCE:
                if self.engine.hero[card]:
                    if (
                        state.hero_used[player] < self.engine.hero_play_limit_per_battle
                        and state.hand[player][card] > 0
                    ):
                        hero_force = 1
                else:
                    own_forces += state.hand[player][card]
        own_forces += hero_force
        if own_forces > self.weights[HW_FORCE_HAND_CAP]:
            own_forces = <int>self.weights[HW_FORCE_HAND_CAP]
        score += self.weights[HW_FORCE_HAND_WEIGHT] * own_forces

        for slot in range(player * POSITIONS_PER_PLAYER, (player + 1) * POSITIONS_PER_PLAYER):
            if state.force[slot] >= 0:
                own_board_forces += 1
        if own_forces == 0 and own_board_forces == 0:
            score -= self.weights[HW_NO_FORCE_PENALTY]

        current_delta = state.command[player] - state.command[opponent]
        score += self.weights[HW_COMMAND_DELTA_WEIGHT] * current_delta

        # Collapse is checked on current Command before recovery. With the
        # zero-Command rule, preserving even 1 Command can decide whether a
        # side survives long enough to receive the next recovery.
        own_vulnerability = (
            self.engine.command_collapse_threshold + self.weights[HW_COLLAPSE_VULNERABILITY_BUFFER]
            - state.command[player]
        )
        if own_vulnerability < 0:
            own_vulnerability = 0
        opponent_vulnerability = (
            self.engine.command_collapse_threshold + self.weights[HW_COLLAPSE_VULNERABILITY_BUFFER]
            - state.command[opponent]
        )
        if opponent_vulnerability < 0:
            opponent_vulnerability = 0
        score += self.weights[HW_COLLAPSE_VULNERABILITY_WEIGHT] * (
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
                score -= self.weights[HW_COLLAPSE_OUTCOME_SCORE]
            else:
                score += self.weights[HW_COLLAPSE_OUTCOME_SCORE]
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
            score += self.weights[HW_PROJECTED_COMMAND_WEIGHT] * (projected_delta - current_delta)

        if (
            state.phase == PHASE_BATTLE
            and state.passed[player] != state.passed[opponent]
        ):
            battle_end_urgency = self.battle_end_urgency_fast(state)
            if state.passed[player]:
                score -= battle_end_urgency * (
                    self.weights[HW_PASSED_BASE_PENALTY]
                    + min(self.weights[HW_PASSED_HAND_CAP], self.weights[HW_PASSED_HAND_WEIGHT] * state.hand_len[opponent])
                    + self.weights[HW_PASSED_EXPOSURE_WEIGHT] * exposed
                )
            else:
                score += battle_end_urgency * (
                    self.weights[HW_RESPONDING_BASE_BONUS]
                    + min(self.weights[HW_RESPONDING_HAND_CAP], self.weights[HW_RESPONDING_HAND_WEIGHT] * state.hand_len[player])
                    + self.weights[HW_RESPONDING_REACH_WEIGHT] * reachable
                )

            # Permanent Pass can close immediately; closing-window variants
            # scale this liability by the remaining forced-end distance.
            own_liability = self.incomplete_liability_fast(state, player)
            opponent_liability = self.incomplete_liability_fast(
                state,
                opponent,
            )
            score += (
                battle_end_urgency
                * self.weights[HW_INCOMPLETE_LIABILITY_WEIGHT]
                * (opponent_liability - own_liability)
            )

        for slot in range(player * POSITIONS_PER_PLAYER, (player + 1) * POSITIONS_PER_PLAYER):
            if _fe_slot_complete(self.engine, state, slot):
                named_delta += 1
        for slot in range(opponent * POSITIONS_PER_PLAYER, (opponent + 1) * POSITIONS_PER_PLAYER):
            if _fe_slot_complete(self.engine, state, slot):
                named_delta -= 1
        score += self.weights[HW_NAMED_FORMATION_WEIGHT] * named_delta

        for front in range(self.engine.ongoing_narrative_limit):
            if state.narrative[player * NARRATIVE_SLOTS_PER_PLAYER + front] >= 0:
                narrative_delta += 1
            if state.narrative[opponent * NARRATIVE_SLOTS_PER_PLAYER + front] >= 0:
                narrative_delta -= 1
        score += self.weights[HW_NARRATIVE_WEIGHT] * narrative_delta

        strat_delta = (
            (1 if state.stratagem[player] >= 0 else 0)
            - (1 if state.stratagem[opponent] >= 0 else 0)
        )
        score += self.weights[HW_STRATAGEM_WEIGHT] * strat_delta

        for slot in range(player * POSITIONS_PER_PLAYER, (player + 1) * POSITIONS_PER_PLAYER):
            if state.force[slot] < 0 or state.name[slot] >= 0:
                continue
            before = _fe_position_strength_fast(self.engine, state, slot)
            best = self.weights[HW_NO_OPTION_SCORE]
            for name_card in range(self.engine.n_cards):
                if state.hand[player][name_card] == 0:
                    continue
                if self.engine.card_type[name_card] != CARD_NAME:
                    if (
                        not self.engine.hero[name_card]
                        or state.hero_used[player] >= self.engine.hero_play_limit_per_battle
                    ):
                        continue
                state.name[slot] = name_card
                after = _fe_position_strength_fast(self.engine, state, slot)
                if after - before > best:
                    best = after - before
                state.name[slot] = -1
            if best > 0:
                option += self.weights[HW_COMPLETION_OPTION_WEIGHT] * best
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
                value += self.weights[HW_PROGRESS_ONE_COMPONENT]
            elif components == 2:
                value += self.weights[HW_PROGRESS_TWO_COMPONENTS]
            elif components == 3:
                value += self.weights[HW_PROGRESS_COMPLETE]
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
                force_value = self.weights[HW_HAND_FORCE_BASE] + (self.weights[HW_HAND_FORCE_NEED] if needs_force else 0.0)
                if self.engine.hero[card]:
                    if state.hero_used[player] >= self.engine.hero_play_limit_per_battle:
                        continue
                    name_value = self.weights[HW_HAND_COMPONENT_BASE] + (self.weights[HW_HAND_NAME_NEED] if needs_name else 0.0)
                    value += count * (
                        force_value
                        if force_value >= name_value
                        else name_value
                    )
                else:
                    value += count * force_value
            elif typ == CARD_BOND:
                value += count * (self.weights[HW_HAND_COMPONENT_BASE] + (self.weights[HW_HAND_BOND_NEED] if needs_bond else 0.0))
            elif typ == CARD_NAME:
                value += count * (self.weights[HW_HAND_COMPONENT_BASE] + (self.weights[HW_HAND_NAME_NEED] if needs_name else 0.0))
            elif typ == CARD_NARRATIVE:
                value += count * self.weights[HW_HAND_NARRATIVE]
            elif typ == CARD_STRATAGEM:
                value += count * self.weights[HW_HAND_STRATAGEM]
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
        if heroes > 0 and state.hero_used[player] < self.engine.hero_play_limit_per_battle:
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
                        state.hero_used[player] < self.engine.hero_play_limit_per_battle
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
                    if state.hero_used[player] < self.engine.hero_play_limit_per_battle:
                        discarded_hero = True
                else:
                    discarded += 1
        return (
            immediate
            + (1.0 if hero_available else 0.0)
            + self.weights[HW_DISCARDED_FORCE_AVAILABILITY] * (
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

        value += self.weights[HW_STRATEGIC_FORMATION_PROGRESS] * (
            self.formation_progress_fast(state, player)
            - self.formation_progress_fast(state, opponent)
        )
        value += self.weights[HW_STRATEGIC_HAND_CONSTRUCTION] * (
            self.hand_construction_value_fast(state, player)
            - self.hand_construction_value_fast(state, opponent)
        )

        value += self.weights[HW_STRATEGIC_DECK_SIZE] * (
            state.deck_len[player] - state.deck_len[opponent]
        )
        value += self.weights[HW_STRATEGIC_FUTURE_SETS] * (
            self.future_formation_sets_fast(state, player)
            - self.future_formation_sets_fast(state, opponent)
        )
        value += self.weights[HW_STRATEGIC_FORCE_AVAILABILITY] * (
            self.future_force_availability_fast(state, player)
            - self.future_force_availability_fast(state, opponent)
        )
        value += self.weights[HW_STRATEGIC_AFFORDABLE_HAND] * (
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
        """Whether this operation can actually reach a Battle-end Collapse."""
        cdef int kind = action_kind(action)
        if state.pass_closing_turns_remaining == 1:
            return True
        return (
            state.pass_len == 1
            and kind == TYPE_PASS
            and not state.passed[player]
        )

    cdef bint action_exhausts_command_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
        FastState child,
    ):
        """True only when this exact action resolves the war as a loss."""
        child.copy_from_fast(state)
        _fe_apply_fast(self.engine, child, action)
        return (
            child.phase == PHASE_COMPLETE
            and child.winner >= 0
            and child.winner != player
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
        cdef double weight = self.weights[HW_ROLLOUT_BOND]

        if kind == TYPE_PASS:
            if (
                state.command[player]
                <= self.engine.command_collapse_threshold + self.weights[HW_ROLLOUT_COLLAPSE_IMMEDIATE_BUFFER]
            ):
                return self.weights[HW_ROLLOUT_PASS_IMMEDIATE]
            if (
                state.command[player]
                <= self.engine.command_collapse_threshold + self.weights[HW_ROLLOUT_COLLAPSE_NEAR_BUFFER]
            ):
                return self.weights[HW_ROLLOUT_PASS_NEAR]
            return self.weights[HW_ROLLOUT_PASS_NORMAL]
        if kind == TYPE_DISCARD:
            return self.weights[HW_ROLLOUT_DISCARD]
        if kind == TYPE_MANEUVER:
            return self.weights[HW_ROLLOUT_MANEUVER]
        if kind == TYPE_FORCE:
            weight = self.weights[HW_ROLLOUT_FORCE]
            if pos >= 0 and (
                state.bond[pos] >= 0 or state.name[pos] >= 0
            ):
                weight += self.weights[HW_ROLLOUT_FORCE_PREPARED_BONUS]
            return weight
        if kind == TYPE_BOND:
            weight = self.weights[HW_ROLLOUT_BOND]
            if pos >= 0 and state.force[pos] >= 0:
                weight += self.weights[HW_ROLLOUT_BOND_ON_FORCE]
            if pos >= 0 and state.name[pos] >= 0:
                weight += self.weights[HW_ROLLOUT_BOND_WITH_NAME]
            return weight
        if kind == TYPE_NAME:
            weight = self.weights[HW_ROLLOUT_NAME]
            if pos >= 0 and state.force[pos] >= 0:
                weight += self.weights[HW_ROLLOUT_NAME_ON_FORCE]
            if pos >= 0 and state.bond[pos] >= 0:
                weight += self.weights[HW_ROLLOUT_NAME_WITH_BOND]
            return weight
        if kind == TYPE_NARRATIVE:
            return self.weights[HW_ROLLOUT_NARRATIVE]
        if kind == TYPE_ONGOING_NARRATIVE:
            return self.weights[HW_ROLLOUT_ONGOING_NARRATIVE]
        if kind == TYPE_STRATAGEM:
            return self.weights[HW_ROLLOUT_STRATAGEM]
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
            score += self.weights[HW_ORDER_DISCARD_CONSTRUCTION] * self.hand_construction_value_fast(
                child,
                player,
            )
            return score

        child.copy_from_fast(state)
        _fe_apply_fast(self.engine, child, action)
        score = self.evaluate_fast(child, player)

        if kind == TYPE_BOND:
            if state.force[pos] >= 0:
                score += self.weights[HW_ORDER_BOND_ON_FORCE]
            else:
                score += self.weights[HW_ORDER_BOND_PREPARED]
        elif kind == TYPE_NAME:
            if state.force[pos] >= 0:
                score += self.weights[HW_ORDER_NAME_ON_FORCE]
            else:
                score += self.weights[HW_ORDER_NAME_PREPARED]
        elif kind == TYPE_ONGOING_NARRATIVE:
            score += self.weights[HW_ORDER_ONGOING_NARRATIVE]
        elif kind == TYPE_STRATAGEM:
            score += self.weights[HW_ORDER_STRATAGEM]
        elif kind == TYPE_MANEUVER:
            score += self.weights[HW_ORDER_MANEUVER]

        return score

    cpdef tuple weight_values(self):
        cdef int i
        return tuple(self.weights[i] for i in range(HEUR_WEIGHT_COUNT))

    cpdef double battle_end_urgency(self, FastState state):
        return self.battle_end_urgency_fast(state)

    cpdef int projected_front_loss_command_penalty(
        self,
        FastState state,
        int player,
        int lost_mask,
    ):
        return self.projected_front_loss_command_penalty_fast(
            state,
            player,
            <uint16_t>lost_mask,
        )

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
