# Heuristic/search tuning is runtime policy configuration copied into C storage.
include "_heuristic_weights.generated.pxi"


cdef class NativeHeuristicEvaluator:
    """Compiled heuristic policy, independent of game transitions/search."""

    cdef FastEngine engine
    cdef double weights[HEUR_WEIGHT_COUNT]
    cdef readonly bint sampled_opponent_resources

    def __init__(
        self,
        FastEngine engine,
        weights=None,
        bint sampled_opponent_resources=False,
    ):
        cdef int i
        cdef double value
        cdef object raw
        self.engine = engine
        self.sampled_opponent_resources = sampled_opponent_resources
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
        """Project effective Front losses through the canonical engine rule."""
        # Once comparison has completed, preserve the authoritative masks.
        if (
            state.resolution_stage == RESOLUTION_RETREATS
            or state.resolution_stage == RESOLUTION_NARRATIVES
            or state.resolution_stage == RESOLUTION_RECOVERY
        ):
            lost0[0] = state.resolution_lost_mask[0] & FRONT_MASK
            lost1[0] = state.resolution_lost_mask[1] & FRONT_MASK
            return
        _fe_project_front_losses_fast(
            self.engine,
            state,
            lost0,
            lost1,
        )

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
        cdef int exposed=0, reachable=0, opponent_exposed=0, opponent_reachable=0, slot
        cdef int own_forces=0, opponent_forces=0
        cdef int own_board_forces=0, opponent_board_forces=0
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
        cdef double passed_pressure=0.0, responding_pressure=0.0
        cdef double signal_pressure=0.0
        cdef double score = 0.0

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
                    opponent_reachable += 1

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
                    opponent_exposed += 1

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
                opponent_reachable += 1

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

        own_forces = self.usable_force_hand_count_fast(state, player)
        if own_forces > self.weights[HW_FORCE_HAND_CAP]:
            own_forces = <int>self.weights[HW_FORCE_HAND_CAP]
        score += self.weights[HW_FORCE_HAND_WEIGHT] * own_forces

        own_board_forces = self.board_force_count_fast(state, player)
        if own_forces == 0 and own_board_forces == 0:
            score -= self.weights[HW_NO_FORCE_PENALTY]

        # Public heuristic evaluation must not inspect hidden opponent card
        # identities. Belief/determinization search explicitly opts into
        # sampled opponent resources because those cards belong to the sampled
        # latent state being evaluated.
        if self.sampled_opponent_resources:
            opponent_forces = self.usable_force_hand_count_fast(
                state, opponent
            )
            if opponent_forces > self.weights[HW_FORCE_HAND_CAP]:
                opponent_forces = <int>self.weights[HW_FORCE_HAND_CAP]
            score -= self.weights[HW_FORCE_HAND_WEIGHT] * opponent_forces

            opponent_board_forces = self.board_force_count_fast(
                state, opponent
            )
            if opponent_forces == 0 and opponent_board_forces == 0:
                score += self.weights[HW_NO_FORCE_PENALTY]

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
        opponent_after_loss = state.command[opponent] - opponent_losses

        # A mid-Battle board is not a terminal Collapse result. Battle-end
        # choices, Retreat effects and Narratives can still change Command.
        # Keep the projection soft; exact terminal utility comes only from the
        # authoritative Battle-resolution transition. Preserve negative
        # projected Command, because overrun depth matters to Collapse.
        if (
            own_after_loss <= self.engine.command_collapse_threshold
            or opponent_after_loss <= self.engine.command_collapse_threshold
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
            # Under canonical permanent Pass, the first Pass gives the
            # unsignalled opponent a standing option to end the Battle with
            # their own Pass. Keep that exposure and incomplete-formation
            # liability at full strength. Research closing-window overrides
            # use the same immediate closing leverage; exact search handles
            # their countdown rather than weakening this pressure heuristically.
            if state.passed[player]:
                # The opponent is the responder. Build one shared public-state
                # value from the old passer-risk and responder-option terms,
                # then apply opposite signs to the two player perspectives.
                passed_hand_value = (
                    self.weights[HW_PASSED_HAND_WEIGHT]
                    * state.hand_len[opponent]
                )
                if passed_hand_value > self.weights[HW_PASSED_HAND_CAP]:
                    passed_hand_value = self.weights[HW_PASSED_HAND_CAP]
                responding_hand_value = (
                    self.weights[HW_RESPONDING_HAND_WEIGHT]
                    * state.hand_len[opponent]
                )
                if responding_hand_value > self.weights[HW_RESPONDING_HAND_CAP]:
                    responding_hand_value = self.weights[HW_RESPONDING_HAND_CAP]
                passed_pressure = (
                    self.weights[HW_PASSED_BASE_PENALTY]
                    + passed_hand_value
                    + self.weights[HW_PASSED_EXPOSURE_WEIGHT] * exposed
                )
                responding_pressure = (
                    self.weights[HW_RESPONDING_BASE_BONUS]
                    + responding_hand_value
                    + self.weights[HW_RESPONDING_REACH_WEIGHT]
                    * opponent_reachable
                )
                signal_pressure = 0.5 * (
                    passed_pressure + responding_pressure
                )
                score -= signal_pressure
            else:
                # The opponent is the passer and this player is the responder.
                passed_hand_value = (
                    self.weights[HW_PASSED_HAND_WEIGHT]
                    * state.hand_len[player]
                )
                if passed_hand_value > self.weights[HW_PASSED_HAND_CAP]:
                    passed_hand_value = self.weights[HW_PASSED_HAND_CAP]
                responding_hand_value = (
                    self.weights[HW_RESPONDING_HAND_WEIGHT]
                    * state.hand_len[player]
                )
                if responding_hand_value > self.weights[HW_RESPONDING_HAND_CAP]:
                    responding_hand_value = self.weights[HW_RESPONDING_HAND_CAP]
                passed_pressure = (
                    self.weights[HW_PASSED_BASE_PENALTY]
                    + passed_hand_value
                    + self.weights[HW_PASSED_EXPOSURE_WEIGHT]
                    * opponent_exposed
                )
                responding_pressure = (
                    self.weights[HW_RESPONDING_BASE_BONUS]
                    + responding_hand_value
                    + self.weights[HW_RESPONDING_REACH_WEIGHT] * reachable
                )
                signal_pressure = 0.5 * (
                    passed_pressure + responding_pressure
                )
                score += signal_pressure

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

        score += self.immediate_completion_value_fast(state, player)
        if self.sampled_opponent_resources:
            score -= self.immediate_completion_value_fast(state, opponent)

        return score

    cdef int usable_force_hand_count_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        """Count immediately allowance-usable Force cards in hand."""
        cdef int i, card, forces=0, heroes=0
        cdef int remaining_hero_uses = (
            self.engine.hero_force_play_limit_per_battle
            - state.hero_force_used[player]
        )
        if remaining_hero_uses < 0:
            remaining_hero_uses = 0

        for i in range(self.engine.force_count):
            card = self.engine.force_codes[i]
            if self.engine.hero[card]:
                heroes += state.hand[player][card]
            else:
                forces += state.hand[player][card]
        if heroes > remaining_hero_uses:
            heroes = remaining_hero_uses
        return forces + heroes

    cdef int board_force_count_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        cdef int slot, count=0
        for slot in range(
            player * POSITIONS_PER_PLAYER,
            (player + 1) * POSITIONS_PER_PLAYER,
        ):
            if state.force[slot] >= 0:
                count += 1
        return count

    cdef double immediate_completion_value_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        """Value affordable Names that can immediately complete a formation."""
        cdef int slot, card, name_card, before, after
        cdef double best, value = 0.0
        cdef uint64_t action

        for slot in range(
            player * POSITIONS_PER_PLAYER,
            (player + 1) * POSITIONS_PER_PLAYER,
        ):
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
                    and state.hero_name_used[player]
                    >= self.engine.hero_name_play_limit_per_battle
                ):
                    continue
                action = encode_action(
                    TYPE_NAME,
                    name_card,
                    slot,
                    -1,
                    player,
                )
                if (
                    _fe_command_cost_fast(self.engine, state, action)
                    > state.command[player]
                ):
                    continue
                state.name[slot] = name_card
                after = _fe_position_strength_fast(self.engine, state, slot)
                if after - before > best:
                    best = after - before
                state.name[slot] = -1
            if best > 0:
                value += self.weights[HW_COMPLETION_OPTION_WEIGHT] * best
        return value

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
            self.engine.hero_force_play_limit_per_battle
            - state.hero_force_used[player]
            + self.engine.hero_name_play_limit_per_battle
            - state.hero_name_used[player]
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
            self.engine.hero_force_play_limit_per_battle
            - state.hero_force_used[player]
            + self.engine.hero_name_play_limit_per_battle
            - state.hero_name_used[player]
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
        )
        if self.sampled_opponent_resources:
            value -= self.weights[HW_STRATEGIC_HAND_CONSTRUCTION] * (
                self.hand_construction_value_fast(state, opponent)
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
        value += self.weights[HW_STRATEGIC_FUTURE_SETS] * own_sets
        value += (
            self.weights[HW_STRATEGIC_FORCE_AVAILABILITY]
            * own_force_availability
        )
        value += self.weights[HW_STRATEGIC_AFFORDABLE_HAND] * own_affordable

        if self.sampled_opponent_resources:
            self.strategic_resource_features_fast(
                state,
                opponent,
                &opponent_sets,
                &opponent_force_availability,
                &opponent_affordable,
            )
            value -= self.weights[HW_STRATEGIC_FUTURE_SETS] * opponent_sets
            value -= (
                self.weights[HW_STRATEGIC_FORCE_AVAILABILITY]
                * opponent_force_availability
            )
            value -= (
                self.weights[HW_STRATEGIC_AFFORDABLE_HAND]
                * opponent_affordable
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
        _fe_apply_fast(
            self.engine,
            child,
            encode_action(TYPE_PASS, -1, -1, -1, player),
        )

        # If this signal ends the Battle, the exact transition has already
        # resolved cleanup and Retreat, checked Collapse, applied surviving
        # recovery, and set next initiative.
        if child.phase != PHASE_BATTLE or child.battle != state.battle:
            return self.battle_boundary_evaluate_fast(child, player)

        # Otherwise evaluate the actual canonical post-Pass state. Research
        # free-signal overrides are still handled by the same exact transition.
        return self.evaluate_fast(child, player)

    cdef bint action_needs_command_guard_probe_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
    ) noexcept:
        """Whether this operation can actually reach a Battle-end Collapse."""
        cdef int kind = action_kind(action)

        # Canonical permanent Pass: only the unsignalled player's Pass can
        # resolve the Battle immediately.
        if (
            state.pass_len == 1
            and kind == TYPE_PASS
            and not state.passed[player]
        ):
            return True

        return False

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

    cdef bint rollout_action_exhausts_command_fast(
        self,
        FastState state,
        int player,
        uint64_t action,
        FastState child,
    ):
        """Conservative low-Command guard used only by stochastic rollouts."""
        cdef int opponent = other_player(player)
        cdef int cost = _fe_command_cost_fast(self.engine, state, action)
        cdef int margin = (
            state.command[player] - self.engine.command_collapse_threshold
        )

        # Only actions capable of consuming the remaining Command margin need
        # an exact transition. Zero-cost play and safely affordable operations
        # remain available without copying the state.
        if cost <= 0 or cost < margin:
            return False

        child.copy_from_fast(state)
        _fe_apply_fast(self.engine, child, action)

        # Exact Battle-ending losses are always unsafe.
        if (
            child.phase == PHASE_COMPLETE
            and child.winner >= 0
            and child.winner != player
        ):
            return True

        # During an unfinished Battle, reaching the Collapse threshold is legal
        # and remains searchable in the tree. Random rollouts, however, should
        # not treat unilateral exhaustion as ordinary play when a preserving
        # alternative exists. Exact application above respects immediate
        # refunds/gains from the operation itself.
        return (
            child.phase == PHASE_BATTLE
            and child.battle == state.battle
            and child.command[player] <= self.engine.command_collapse_threshold
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

    cpdef tuple rollout_preserving_action_codes(self, FastState state):
        """Expose stochastic-rollout Command safety for regression tests."""
        cdef uint64_t actions[MAX_ACTIONS]
        cdef uint64_t safe[MAX_ACTIONS]
        cdef FastState child = FastState()
        cdef int n = _fe_legal_actions_into(self.engine, state, &actions[0])
        cdef int actor = state.active_player
        cdef int i, safe_n = 0

        if n <= 1:
            return ([actions[i] for i in range(n)], 0)

        for i in range(n):
            if not self.rollout_action_exhausts_command_fast(
                state,
                actor,
                actions[i],
                child,
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

    cpdef double immediate_completion_value(
        self,
        FastState state,
        int player,
    ):
        return self.immediate_completion_value_fast(state, player)

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
