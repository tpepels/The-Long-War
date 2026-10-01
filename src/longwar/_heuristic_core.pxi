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
            if not isfinite(value):
                raise ValueError("heuristic values must be finite")
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

    cdef void projected_lost_masks_fast(
        self,
        FastState state,
        uint16_t* lost0,
        uint16_t* lost1,
    ) noexcept:
        """Project effective Front losses using resolution comparison rules."""
        cdef int front, a, b, controller, strat, mask
        cdef int combined0, combined1
        cdef bint tie_control

        # Once comparison has completed, preserve the authoritative masks.
        if (
            state.resolution_stage == RESOLUTION_RETREATS
            or state.resolution_stage == RESOLUTION_NARRATIVES
            or state.resolution_stage == RESOLUTION_RECOVERY
        ):
            lost0[0] = state.resolution_lost_mask[0] & FRONT_MASK
            lost1[0] = state.resolution_lost_mask[1] & FRONT_MASK
            return

        lost0[0] = 0
        lost1[0] = 0
        tie_control = _fe_tie_control_active(self.engine, state)

        for front in range(FRONT_COUNT):
            a = _fe_resolution_front_strength_fast(
                self.engine, state, 0, front
            )
            b = _fe_resolution_front_strength_fast(
                self.engine, state, 1, front
            )
            if a < b:
                lost0[0] |= <uint16_t>(1 << front)
            elif b < a:
                lost1[0] |= <uint16_t>(1 << front)
            elif tie_control:
                if (
                    _fe_slot_complete(
                        self.engine,
                        state,
                        slot_index(0, front, RANK_FRONT),
                    )
                    != _fe_slot_complete(
                        self.engine,
                        state,
                        slot_index(1, front, RANK_FRONT),
                    )
                ):
                    if _fe_slot_complete(
                        self.engine,
                        state,
                        slot_index(0, front, RANK_FRONT),
                    ):
                        lost1[0] |= <uint16_t>(1 << front)
                    else:
                        lost0[0] |= <uint16_t>(1 << front)

        # Combined-Front Stratagems replace the individual results exactly as
        # Battle resolution does.
        for controller in range(PLAYER_COUNT):
            strat = state.stratagem[controller]
            if strat < 0 or not self.engine.strat_combine_fronts[strat]:
                continue
            mask = state.stratagem_front_mask[controller] & FRONT_MASK
            if popcount16(mask) != COMBINED_FRONT_SELECTION_COUNT:
                continue
            combined0 = 0
            combined1 = 0
            for front in range(FRONT_COUNT):
                if mask & (1 << front):
                    combined0 += _fe_resolution_front_strength_fast(
                        self.engine, state, 0, front
                    )
                    combined1 += _fe_resolution_front_strength_fast(
                        self.engine, state, 1, front
                    )
            lost0[0] &= <uint16_t>(~mask)
            lost1[0] &= <uint16_t>(~mask)
            if combined0 < combined1:
                lost0[0] |= <uint16_t>mask
            elif combined1 < combined0:
                lost1[0] |= <uint16_t>mask

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
        cdef int narrative_slot
        cdef int exposed=0, reachable=0, slot, name_card, before, after
        cdef double best
        cdef int card, own_forces=0, own_board_forces=0, hero_force=0
        cdef int remaining_hero_uses=0
        cdef int own_losses=0, opponent_losses=0
        cdef uint16_t own_lost_mask=0, opponent_lost_mask=0
        cdef uint16_t projected_lost0=0, projected_lost1=0
        cdef int own_front_slot, own_rear_slot, opp_front_slot, opp_rear_slot
        cdef int recovery=0, own_recovery=0, opponent_recovery=0
        cdef int own_after_loss=0, opponent_after_loss=0
        cdef int own_projected=0, opponent_projected=0
        cdef int current_delta=0, projected_delta=0
        cdef double own_vulnerability=0.0, opponent_vulnerability=0.0
        cdef double own_liability=0.0, opponent_liability=0.0
        cdef double passed_hand_value=0.0, responding_hand_value=0.0
        cdef double score = 0.0, option = 0.0

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

        self.projected_lost_masks_fast(
            state,
            &projected_lost0,
            &projected_lost1,
        )
        if player == 0:
            own_lost_mask = projected_lost0
            opponent_lost_mask = projected_lost1
        else:
            own_lost_mask = projected_lost1
            opponent_lost_mask = projected_lost0

        for front in range(FRONT_COUNT):
            # Tactical board value should describe the same comparison the
            # Battle resolver will use, not a separate displayed-Strength
            # approximation. Projected lost masks also include tie-control and
            # combined-Front replacement rules.
            raw_margin = (
                _fe_resolution_front_strength_fast(
                    self.engine, state, player, front
                )
                - _fe_resolution_front_strength_fast(
                    self.engine, state, opponent, front
                )
            )
            margin = raw_margin

            if opponent_lost_mask & (1 << front):
                controls += 1
                if (
                    raw_margin > 0
                    and raw_margin <= self.weights[HW_CLOSE_FRONT_MARGIN]
                ):
                    score += self.weights[HW_CLOSE_FRONT_BONUS]
                if (
                    raw_margin > 0
                    and raw_margin <= self.weights[HW_EXPOSED_FRONT_MARGIN]
                ):
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

            elif own_lost_mask & (1 << front):
                enemy_controls += 1
                if (
                    raw_margin < 0
                    and raw_margin >= -self.weights[HW_CLOSE_FRONT_MARGIN]
                ):
                    score -= self.weights[HW_CLOSE_FRONT_BONUS]
                if (
                    raw_margin < 0
                    and raw_margin >= -self.weights[HW_EXPOSED_FRONT_MARGIN]
                ):
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
            score += self.weights[HW_MARGIN_WEIGHT] * margin

        own_losses = self.projected_front_loss_command_penalty_fast(
            state, player, own_lost_mask
        )
        opponent_losses = self.projected_front_loss_command_penalty_fast(
            state, opponent, opponent_lost_mask
        )

        score += self.weights[HW_FRONT_CONTROL_WEIGHT] * (controls - enemy_controls)

        hand_delta = state.hand_len[player] - state.hand_len[opponent]
        score += self.weights[HW_HAND_CARD_WEIGHT] * hand_delta

        remaining_hero_uses = (
            self.engine.hero_play_limit_per_battle
            - state.hero_used[player]
        )
        if remaining_hero_uses < 0:
            remaining_hero_uses = 0
        for slot in range(self.engine.force_count):
            card = self.engine.force_codes[slot]
            if self.engine.hero[card]:
                hero_force += state.hand[player][card]
            else:
                own_forces += state.hand[player][card]
        if hero_force > remaining_hero_uses:
            hero_force = remaining_hero_uses
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

        # A mid-Battle board is not a terminal Collapse result. Battle-end
        # choices, Retreat effects and Narratives can still change Command.
        # Keep the projection soft; exact terminal utility comes only from the
        # authoritative Battle-resolution transition.
        if (
            (
                own_after_loss <= self.engine.command_collapse_threshold
                or opponent_after_loss <= self.engine.command_collapse_threshold
            )
            and own_after_loss != opponent_after_loss
        ):
            own_projected = own_after_loss
            opponent_projected = opponent_after_loss
        else:
            # Front losses have already been applied to projected Command.
            # Recovery is relevant only after surviving the projected check.
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
        score += self.weights[HW_PROJECTED_COMMAND_WEIGHT] * (
            projected_delta - current_delta
        )

        if (
            state.phase == PHASE_BATTLE
            and state.passed[player] != state.passed[opponent]
        ):
            # A first signal gives the unsignalled opponent an immediate option
            # to end the Battle by signalling too. That option is equally real
            # in permanent-Pass and fixed closing-window variants; the automatic
            # deadline being farther away does not make the opponent's immediate
            # closing leverage weaker. Keep post-signal exposure and incomplete
            # formation liability at full strength and let search model the
            # countdown itself through exact transitions.
            if state.passed[player]:
                passed_hand_value = (
                    self.weights[HW_PASSED_HAND_WEIGHT]
                    * state.hand_len[opponent]
                )
                if passed_hand_value > self.weights[HW_PASSED_HAND_CAP]:
                    passed_hand_value = self.weights[HW_PASSED_HAND_CAP]
                score -= (
                    self.weights[HW_PASSED_BASE_PENALTY]
                    + passed_hand_value
                    + self.weights[HW_PASSED_EXPOSURE_WEIGHT] * exposed
                )
            else:
                responding_hand_value = (
                    self.weights[HW_RESPONDING_HAND_WEIGHT]
                    * state.hand_len[player]
                )
                if responding_hand_value > self.weights[HW_RESPONDING_HAND_CAP]:
                    responding_hand_value = self.weights[HW_RESPONDING_HAND_CAP]
                score += (
                    self.weights[HW_RESPONDING_BASE_BONUS]
                    + responding_hand_value
                    + self.weights[HW_RESPONDING_REACH_WEIGHT] * reachable
                )

            own_liability = self.incomplete_liability_fast(state, player)
            opponent_liability = self.incomplete_liability_fast(
                state,
                opponent,
            )
            score += (
                self.weights[HW_INCOMPLETE_LIABILITY_WEIGHT]
                * (opponent_liability - own_liability)
            )

        for slot in range(player * POSITIONS_PER_PLAYER, (player + 1) * POSITIONS_PER_PLAYER):
            if _fe_slot_complete(self.engine, state, slot):
                named_delta += 1
        for slot in range(opponent * POSITIONS_PER_PLAYER, (opponent + 1) * POSITIONS_PER_PLAYER):
            if _fe_slot_complete(self.engine, state, slot):
                named_delta -= 1
        score += self.weights[HW_NAMED_FORMATION_WEIGHT] * named_delta

        for narrative_slot in range(self.engine.ongoing_narrative_limit):
            if (
                state.narrative[
                    player * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
                ]
                >= 0
            ):
                narrative_delta += 1
            if (
                state.narrative[
                    opponent * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
                ]
                >= 0
            ):
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
            for card in range(self.engine.name_mode_count):
                name_card = self.engine.name_mode_codes[card]
                if state.hand[player][name_card] == 0:
                    continue
                if (
                    self.engine.hero[name_card]
                    and state.hero_used[player]
                    >= self.engine.hero_play_limit_per_battle
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
        cdef int local, slot, card, count, typ, usable_count
        cdef int remaining_hero_uses = (
            self.engine.hero_play_limit_per_battle
            - state.hero_used[player]
        )
        cdef double value=0.0, force_value=0.0, name_value=0.0
        if remaining_hero_uses < 0:
            remaining_hero_uses = 0
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
                    if remaining_hero_uses <= 0:
                        continue
                    usable_count = count
                    if usable_count > remaining_hero_uses:
                        usable_count = remaining_hero_uses
                    remaining_hero_uses -= usable_count
                    name_value = self.weights[HW_HAND_COMPONENT_BASE] + (self.weights[HW_HAND_NAME_NEED] if needs_name else 0.0)
                    value += usable_count * (
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

    cdef void strategic_resource_features_fast(
        self,
        FastState state,
        int player,
        int* future_sets,
        double* force_availability,
        int* affordable,
    ) noexcept:
        """Compute long-horizon card-resource features in one identity scan."""
        cdef int card, typ, hand_count, count, i
        cdef int forces=0, bonds=0, names=0, heroes=0
        cdef int discarded_forces=0, discarded_heroes=0
        cdef int remaining_hero_uses, usable_heroes, force_heroes, name_heroes
        cdef int candidate, value, immediate_heroes, discarded_usable

        future_sets[0] = 0
        force_availability[0] = 0.0
        affordable[0] = 0
        remaining_hero_uses = (
            self.engine.hero_play_limit_per_battle
            - state.hero_used[player]
        )
        if remaining_hero_uses < 0:
            remaining_hero_uses = 0

        for card in range(self.engine.n_cards):
            hand_count = state.hand[player][card]
            count = hand_count + state.deck_counts[player][card]
            if (
                hand_count > 0
                and self.engine.card_command_cost[card] <= state.command[player]
            ):
                affordable[0] += hand_count

            typ = self.engine.card_type[card]
            if typ == CARD_FORCE:
                if self.engine.hero[card]:
                    heroes += count
                else:
                    forces += count
            elif typ == CARD_BOND:
                bonds += count
            elif typ == CARD_NAME:
                names += count

        usable_heroes = heroes
        if usable_heroes > remaining_hero_uses:
            usable_heroes = remaining_hero_uses

        # A Hero may fill either the Force or Name side of one formation.
        # Try every split of the small remaining Hero allowance and keep the
        # maximum number of complete future formation sets.
        value = 0
        for force_heroes in range(usable_heroes + 1):
            name_heroes = usable_heroes - force_heroes
            candidate = forces + force_heroes
            if bonds < candidate:
                candidate = bonds
            if names + name_heroes < candidate:
                candidate = names + name_heroes
            if candidate > value:
                value = candidate
        future_sets[0] = value

        immediate_heroes = usable_heroes
        force_availability[0] = forces + immediate_heroes

        for i in range(state.discard_len[player]):
            card = state.discard[player][i]
            if self.engine.card_type[card] != CARD_FORCE:
                continue
            if self.engine.hero[card]:
                discarded_heroes += 1
            else:
                discarded_forces += 1

        discarded_usable = remaining_hero_uses - immediate_heroes
        if discarded_usable < 0:
            discarded_usable = 0
        if discarded_heroes < discarded_usable:
            discarded_usable = discarded_heroes
        force_availability[0] += (
            self.weights[HW_DISCARDED_FORCE_AVAILABILITY]
            * (discarded_forces + discarded_usable)
        )

    cdef int future_formation_sets_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int future_sets=0, affordable=0
        cdef double force_availability=0.0
        self.strategic_resource_features_fast(
            state,
            player,
            &future_sets,
            &force_availability,
            &affordable,
        )
        return future_sets

    cdef double future_force_availability_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int future_sets=0, affordable=0
        cdef double force_availability=0.0
        self.strategic_resource_features_fast(
            state,
            player,
            &future_sets,
            &force_availability,
            &affordable,
        )
        return force_availability

    cdef int affordable_hand_count_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int future_sets=0, affordable=0
        cdef double force_availability=0.0
        self.strategic_resource_features_fast(
            state,
            player,
            &future_sets,
            &force_availability,
            &affordable,
        )
        return affordable

    cdef double strategic_evaluate_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int opponent = other_player(player)
        cdef int own_sets=0, opponent_sets=0
        cdef int own_affordable=0, opponent_affordable=0
        cdef double own_force_availability=0.0, opponent_force_availability=0.0
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
        self.strategic_resource_features_fast(
            state,
            player,
            &own_sets,
            &own_force_availability,
            &own_affordable,
        )
        self.strategic_resource_features_fast(
            state,
            opponent,
            &opponent_sets,
            &opponent_force_availability,
            &opponent_affordable,
        )
        value += self.weights[HW_STRATEGIC_FUTURE_SETS] * (
            own_sets - opponent_sets
        )
        value += self.weights[HW_STRATEGIC_FORCE_AVAILABILITY] * (
            own_force_availability - opponent_force_availability
        )
        value += self.weights[HW_STRATEGIC_AFFORDABLE_HAND] * (
            own_affordable - opponent_affordable
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
        cdef list values = []
        for i in range(HEUR_WEIGHT_COUNT):
            values.append(self.weights[i])
        return tuple(values)

    cpdef tuple projected_lost_masks(self, FastState state):
        cdef uint16_t lost0=0, lost1=0
        self.projected_lost_masks_fast(state, &lost0, &lost1)
        return (lost0, lost1)

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
