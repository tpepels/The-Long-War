cdef void _fe_queue_pre_resolution_choice(
    FastEngine self,
    FastState state,
) except *:
    cdef int cursor = state.resolution_cursor
    cdef int controller, slot, front, rear, force, bond
    cdef int opponent, target
    cdef uint16_t mask, target_mask

    # They Let Them Through - each controller may swap the two formations
    # in one Front before Strength is compared.
    if cursor < PRE_RESOLUTION_CONTROLLER_END:
        controller = cursor
        state.resolution_cursor += 1
        force = state.stratagem[controller]
        if force >= 0 and self.feigned_retreat_strat[force]:
            mask = 0
            for front in range(FRONT_COUNT):
                slot = slot_index(controller, front, RANK_FRONT)
                rear = slot_index(controller, front, RANK_REAR)
                if (
                    state.force[slot] >= 0
                    and state.force[rear] >= 0
                ):
                    mask |= <uint16_t>(1 << slot)
                    mask |= <uint16_t>(1 << rear)
            if mask:
                _fe_enqueue_effect(self, 
                    state,
                    EFFECT_SWAP,
                    controller,
                    -1,
                    -1,
                    -1,
                    mask,
                    mask,
                    EFFECT_OPTIONAL | EFFECT_SAME_FRONT_PAIR,
                )
        return

    # Tala - optional voluntary Retreat before comparison.
    if cursor < PRE_RESOLUTION_RETREAT_END:
        slot = cursor - PRE_RESOLUTION_CONTROLLER_END
        state.resolution_cursor += 1
        if (
            state.force[slot] >= 0
            and _fe_slot_complete(self, state, slot)
            and rank_from_slot(slot) == RANK_FRONT
            and state.name[slot] >= 0
            and self.voluntary_retreat_name[state.name[slot]]
        ):
            rear = slot_index(
                owner_from_slot(slot),
                front_from_slot(slot),
                1,
            )
            if _fe_slot_is_empty(self, state, rear):
                _fe_enqueue_effect(self, 
                    state,
                    EFFECT_RETREAT,
                    owner_from_slot(slot),
                    -1,
                    slot,
                    rear,
                    0,
                    0,
                    EFFECT_OPTIONAL,
                )
        return

    # Grey/Dust Riders choose the Front where their Strength contributes.
    if cursor < PRE_RESOLUTION_CONTRIBUTION_END:
        slot = cursor - PRE_RESOLUTION_RETREAT_END
        state.resolution_cursor += 1
        force = state.force[slot]
        if force >= 0 and self.skirmisher_contribution[force]:
            _fe_enqueue_effect(self, 
                state,
                EFFECT_FRONT_CONTRIBUTION,
                owner_from_slot(slot),
                -1,
                slot,
                -1,
                0,
                0,
                0,
            )
        return

    # Thornbow/Rovan suppression and First Spear first strike.
    if cursor < PRE_RESOLUTION_SUPPRESSION_END:
        slot = cursor - PRE_RESOLUTION_CONTRIBUTION_END
        state.resolution_cursor += 1
        force = state.force[slot]
        if force < 0:
            return
        controller = owner_from_slot(slot)
        opponent = other_player(controller)
        front = front_from_slot(slot)
        target = -1
        if self.suppress_rear_force[force]:
            rear = slot_index(opponent, front, RANK_REAR)
            if state.force[rear] >= 0:
                target = rear
        elif self.first_strike_force[force]:
            target = slot_index(opponent, front, RANK_FRONT)
            if (
                state.force[target] < 0
                or self.strength[state.force[target]]
                >= self.strength[force]
            ):
                target = -1
        if target >= 0:
            _fe_enqueue_effect(self, 
                state,
                EFFECT_SUPPRESS,
                controller,
                -1,
                slot,
                -1,
                0,
                <uint16_t>(1 << target),
                EFFECT_OPTIONAL,
            )
        return

    # Held the Line for - sacrifice this formation to suppress one opposing
    # formation in the same Front.
    if cursor < PRE_RESOLUTION_SACRIFICE_END:
        slot = cursor - PRE_RESOLUTION_SUPPRESSION_END
        state.resolution_cursor += 1
        if state.force[slot] < 0:
            return
        bond = state.bond[slot]
        if bond < 0 or not self.sacrifice_bond[bond]:
            return
        controller = owner_from_slot(slot)
        opponent = other_player(controller)
        front = front_from_slot(slot)
        target_mask = 0
        target = slot_index(opponent, front, RANK_FRONT)
        if state.force[target] >= 0:
            target_mask |= <uint16_t>(1 << target)
        target = slot_index(opponent, front, RANK_REAR)
        if state.force[target] >= 0:
            target_mask |= <uint16_t>(1 << target)
        if target_mask:
            _fe_enqueue_effect(self, 
                state,
                EFFECT_SACRIFICE,
                controller,
                -1,
                slot,
                -1,
                0,
                target_mask,
                EFFECT_OPTIONAL,
            )
        return

    state.resolution_stage = RESOLUTION_COMPARE
    state.resolution_cursor = 0

cdef void _fe_project_front_losses_fast(
    FastEngine self,
    FastState state,
    uint16_t* lost0,
    uint16_t* lost1,
) noexcept:
    """Project Front losses under the canonical comparison rules."""
    cdef int front, a, b, controller, strat, mask
    cdef int combined0, combined1
    cdef bint tie_control = _fe_tie_control_active(self, state)

    lost0[0] = 0
    lost1[0] = 0
    for front in range(FRONT_COUNT):
        a = _fe_resolution_front_strength_fast(self, state, 0, front)
        b = _fe_resolution_front_strength_fast(self, state, 1, front)
        if a < b:
            lost0[0] |= <uint16_t>(1 << front)
        elif b < a:
            lost1[0] |= <uint16_t>(1 << front)
        elif tie_control:
            if (
                _fe_slot_complete(self, state, slot_index(0, front, RANK_FRONT))
                != _fe_slot_complete(self, state, slot_index(1, front, RANK_FRONT))
            ):
                if _fe_slot_complete(
                    self, state, slot_index(0, front, RANK_FRONT)
                ):
                    lost1[0] |= <uint16_t>(1 << front)
                else:
                    lost0[0] |= <uint16_t>(1 << front)

    # The Center Must Hold replaces the two individual results.
    for controller in range(PLAYER_COUNT):
        strat = state.stratagem[controller]
        if strat < 0 or not self.strat_combine_fronts[strat]:
            continue
        mask = state.stratagem_front_mask[controller] & FRONT_MASK
        if popcount16(mask) != COMBINED_FRONT_SELECTION_COUNT:
            continue
        combined0 = 0
        combined1 = 0
        for front in range(FRONT_COUNT):
            if mask & (1 << front):
                combined0 += _fe_resolution_front_strength_fast(
                    self, state, 0, front
                )
                combined1 += _fe_resolution_front_strength_fast(
                    self, state, 1, front
                )
        lost0[0] &= <uint16_t>(~mask)
        lost1[0] &= <uint16_t>(~mask)
        if combined0 < combined1:
            lost0[0] |= <uint16_t>mask
        elif combined1 < combined0:
            lost1[0] |= <uint16_t>mask


cdef void _fe_compare_battle_fronts(FastEngine self, FastState state) noexcept:
    cdef int front, a, b, p, strat, protected, protected_card, card
    cdef int controller, mask
    cdef int losses0, losses1
    cdef uint16_t projected_lost0=0, projected_lost1=0

    # Record the effective comparison Strength displayed in the Battle
    # snapshot, then use the shared rule primitive for the actual outcomes.
    for front in range(FRONT_COUNT):
        a = _fe_resolution_front_strength_fast(self, state, 0, front)
        b = _fe_resolution_front_strength_fast(self, state, 1, front)
        state.last_front_scores[front][0] = a
        state.last_front_scores[front][1] = b

    _fe_project_front_losses_fast(
        self,
        state,
        &projected_lost0,
        &projected_lost1,
    )
    state.resolution_lost_mask[0] = <uint8_t>projected_lost0
    state.resolution_lost_mask[1] = <uint8_t>projected_lost1
    state.resolution_drive_mask[0] = 0
    state.resolution_drive_mask[1] = 0

    # Breakthrough replacements.
    for front in range(FRONT_COUNT):
        if (
            state.resolution_lost_mask[0] & (1 << front)
            and state.force[slot_index(0, front, RANK_REAR)] < 0
            and _fe_breakthrough_active(self, state, 1, front)
        ):
            state.resolution_drive_mask[0] |= <uint8_t>(1 << front)
        if (
            state.resolution_lost_mask[1] & (1 << front)
            and state.force[slot_index(1, front, RANK_REAR)] < 0
            and _fe_breakthrough_active(self, state, 0, front)
        ):
            state.resolution_drive_mask[1] |= <uint8_t>(1 << front)

    for controller in range(PLAYER_COUNT):
        strat = state.stratagem[controller]
        if strat >= 0 and self.strat_no_retreat[strat]:
            mask = state.stratagem_front_mask[controller] & FRONT_MASK
            state.resolution_drive_mask[0] |= (
                state.resolution_lost_mask[0] & mask
            )
            state.resolution_drive_mask[1] |= (
                state.resolution_lost_mask[1] & mask
            )

    strat = state.stratagem[0]
    if strat >= 0 and self.strat_encirclement[strat]:
        if (state.resolution_lost_mask[1] & ENCIRCLEMENT_LEFT_MASK) == ENCIRCLEMENT_LEFT_MASK:
            state.resolution_drive_mask[1] |= <uint8_t>(1 << ENCIRCLEMENT_LEFT_TARGET_FRONT)
        if (state.resolution_lost_mask[1] & ENCIRCLEMENT_RIGHT_MASK) == ENCIRCLEMENT_RIGHT_MASK:
            state.resolution_drive_mask[1] |= <uint8_t>(1 << ENCIRCLEMENT_RIGHT_TARGET_FRONT)
    strat = state.stratagem[1]
    if strat >= 0 and self.strat_encirclement[strat]:
        if (state.resolution_lost_mask[0] & ENCIRCLEMENT_LEFT_MASK) == ENCIRCLEMENT_LEFT_MASK:
            state.resolution_drive_mask[0] |= <uint8_t>(1 << ENCIRCLEMENT_LEFT_TARGET_FRONT)
        if (state.resolution_lost_mask[0] & ENCIRCLEMENT_RIGHT_MASK) == ENCIRCLEMENT_RIGHT_MASK:
            state.resolution_drive_mask[0] |= <uint8_t>(1 << ENCIRCLEMENT_RIGHT_TARGET_FRONT)

    # Preserve the effective Front outcomes before retreat/cleanup clears the
    # live resolution masks. These can differ from the raw Strength comparison
    # because Stratagems such as The Ground Was Held and The Center Must Hold
    # replace tied or per-Front results.
    state.last_lost_mask[0] = state.resolution_lost_mask[0] & FRONT_MASK
    state.last_lost_mask[1] = state.resolution_lost_mask[1] & FRONT_MASK

    losses0 = popcount16(state.resolution_lost_mask[0] & FRONT_MASK)
    losses1 = popcount16(state.resolution_lost_mask[1] & FRONT_MASK)
    state.resolution_front_loss_command_penalty[0] = (
        losses0 * self.lost_front_command_penalty
    )
    state.resolution_front_loss_command_penalty[1] = (
        losses1 * self.lost_front_command_penalty
    )

    for front in range(FRONT_COUNT):
        if state.resolution_lost_mask[0] & (1 << front):
            protected = 0
            protected_card = -1
            for rank in range(RANK_COUNT):
                card = state.force[slot_index(0, front, rank)]
                if card >= 0 and self.front_loss_protected_front[card]:
                    protected = self.lost_front_command_penalty
                    protected_card = card
            if protected and state.resolution_front_loss_command_penalty[0] > 0:
                protected = min(
                    protected,
                    state.resolution_front_loss_command_penalty[0],
                )
                state.resolution_front_loss_command_penalty[0] -= protected
                _fe_record_command_diag(
                    self, COMMAND_DIAG_FRONT_LOSS_PROTECTION,
                    COMMAND_DETAIL_FRONT_LOSS_PROTECTED_FRONT,
                    0, protected_card, protected, protected,
                )
        if state.resolution_lost_mask[1] & (1 << front):
            protected = 0
            protected_card = -1
            for rank in range(RANK_COUNT):
                card = state.force[slot_index(1, front, rank)]
                if card >= 0 and self.front_loss_protected_front[card]:
                    protected = self.lost_front_command_penalty
                    protected_card = card
            if protected and state.resolution_front_loss_command_penalty[1] > 0:
                protected = min(
                    protected,
                    state.resolution_front_loss_command_penalty[1],
                )
                state.resolution_front_loss_command_penalty[1] -= protected
                _fe_record_command_diag(
                    self, COMMAND_DIAG_FRONT_LOSS_PROTECTION,
                    COMMAND_DETAIL_FRONT_LOSS_PROTECTED_FRONT,
                    1, protected_card, protected, protected,
                )

    strat = state.stratagem[0]
    if strat >= 0 and self.strat_front_loss_protection[strat]:
        protected = min(
            state.resolution_front_loss_command_penalty[0],
            self.strat_front_loss_protection[strat]
            * self.lost_front_command_penalty,
        )
        state.resolution_front_loss_command_penalty[0] -= protected
        if protected:
            _fe_record_command_diag(
                self, COMMAND_DIAG_FRONT_LOSS_PROTECTION,
                COMMAND_DETAIL_FRONT_LOSS_STRATAGEM,
                0, strat, protected, protected,
            )
    strat = state.stratagem[1]
    if strat >= 0 and self.strat_front_loss_protection[strat]:
        protected = min(
            state.resolution_front_loss_command_penalty[1],
            self.strat_front_loss_protection[strat]
            * self.lost_front_command_penalty,
        )
        state.resolution_front_loss_command_penalty[1] -= protected
        if protected:
            _fe_record_command_diag(
                self, COMMAND_DIAG_FRONT_LOSS_PROTECTION,
                COMMAND_DETAIL_FRONT_LOSS_STRATAGEM,
                1, strat, protected, protected,
            )

    _fe_discard_incomplete_formations(self, state)
    state.resolution_stage = RESOLUTION_RETREATS
    state.resolution_cursor = 0

cdef void _fe_advance_retreat_resolution(FastEngine self, FastState state) except *:
    cdef int player, front, front_slot, rear_slot, force
    cdef uint16_t destinations

    while state.resolution_cursor < PLAYER_COUNT * FRONT_COUNT:
        player = state.resolution_cursor // FRONT_COUNT
        front = state.resolution_cursor % FRONT_COUNT
        if not (
            state.resolution_lost_mask[player] & (1 << front)
        ):
            state.resolution_cursor += 1
            continue

        front_slot = slot_index(player, front, RANK_FRONT)
        rear_slot = slot_index(player, front, RANK_REAR)

        # Snapshot persistent Rear effects before that formation is driven
        # off. Upper drive-mask bits are temporary sideways-retreat markers.
        force = state.force[rear_slot]
        if force >= 0 and (self.card_capabilities[force] & CAP_AFTER_FRONTLINE_RETREAT_SIDEWAYS_FORCE):
            state.resolution_drive_mask[player] |= <uint8_t>(
                1 << (front + FRONT_COUNT)
            )

        if _fe_slot_complete(self, state, front_slot) and force >= 0:
            if self.rear_force_prevents_frontline_retreat[force]:
                state.resolution_protected_mask[player] |= <uint8_t>(
                    1 << front
                )
            elif (
                (self.card_capabilities[force] & CAP_OPTIONAL_SELF_DRIVE_PREVENT_FRONTLINE_RETREAT_FORCE)
                and not (
                    state.resolution_protected_mask[player]
                    & (1 << (front + FRONT_COUNT))
                )
            ):
                # Mark offered before pausing so declining cannot requeue it.
                state.resolution_protected_mask[player] |= <uint8_t>(
                    1 << (front + FRONT_COUNT)
                )
                _fe_enqueue_effect(self, 
                    state,
                    EFFECT_PROTECT_RETREAT,
                    player,
                    -1,
                    rear_slot,
                    front_slot,
                    0,
                    0,
                    EFFECT_OPTIONAL,
                )
                return

        if _fe_slot_complete(self, state, rear_slot):
            _fe_drive_off_slot(self, state, player, rear_slot)
            if state.pending_len > 0:
                return

        if not _fe_slot_complete(self, state, front_slot):
            state.resolution_cursor += 1
            continue

        if state.resolution_protected_mask[player] & (1 << front):
            state.resolution_cursor += 1
            continue

        if state.resolution_drive_mask[player] & (1 << front):
            _fe_drive_off_slot(self, state, player, front_slot)
            if state.pending_len > 0:
                return
            state.resolution_cursor += 1
            continue

        # Mark this Front complete before after-Retreat effects pause play.
        state.resolution_cursor += 1
        _fe_retreat_slot(self, state, player, front_slot, rear_slot)

        if _fe_front_has_capture_bond(self, state, other_player(player), front):
            _fe_return_bond_to_hand_from_slot(self, 
                state, player, rear_slot
            )

        if state.resolution_drive_mask[player] & (1 << (front + FRONT_COUNT)):
            destinations = _fe_adjacent_empty_mask(self, 
                state, player, rear_slot
            )
            _fe_queue_move_to_mask(self, 
                state,
                player,
                <uint16_t>(1 << rear_slot),
                destinations,
                True,
            )

        if state.pending_len > 0 or state.cleanup_pending:
            return

    state.resolution_stage = RESOLUTION_NARRATIVES
    state.resolution_cursor = 0

cdef bint _fe_resolve_one_battle_end_narrative(
    FastEngine self,
    FastState state,
) except *:
    cdef int player, narrative_slot, ix, card, kind, front
    cdef int target_slot, gain
    cdef uint8_t front_mask
    cdef bint condition, won
    for player in range(PLAYER_COUNT):
        for narrative_slot in range(self.ongoing_narrative_limit):
            ix = player * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
            card = state.narrative[ix]
            if card < 0:
                continue
            kind = self.narrative_end_kind[card]
            if kind == NARR_END_NONE:
                continue

            condition = False
            won = False
            front_mask = state.narrative_front_mask[ix]
            front = -1
            for target_slot in range(FRONT_COUNT):
                if front_mask & (1 << target_slot):
                    front = target_slot
                    break

            if kind == NARR_END_NOT_LOST and front >= 0:
                condition = not (
                    state.resolution_lost_mask[player]
                    & (1 << front)
                )
                won = bool(
                    state.resolution_lost_mask[other_player(player)]
                    & (1 << front)
                )
            elif kind == NARR_END_WON and front >= 0:
                won = bool(
                    state.resolution_lost_mask[other_player(player)]
                    & (1 << front)
                )
                condition = won
            elif kind == NARR_END_TARGET_SURVIVES:
                target_slot = state.narrative_target_slot[ix]
                condition = (
                    target_slot >= 0
                    and state.force[target_slot] >= 0
                )

            gain = self.narrative_end_gain[card]
            if condition and gain:
                _fe_gain_command_from_narrative(self,
                    state, player, card, gain
                )
            if condition and self.narrative_end_draw[card]:
                _fe_queue_battle_draws(self, state, player, 1)
            if (
                condition
                and won
                and self.narrative_end_recover_bond[card]
            ):
                _fe_queue_recover_from_discard(self, 
                    state, player, CARD_BOND, True
                )

            # These cards all end at Battle end whether or not their
            # condition succeeded.
            if self.narrative_end_discard[card]:
                _fe_discard_ongoing_narrative(self, 
                    state, player, narrative_slot
                )
            return True
    return False

cdef void _fe_clear_resolution_state(FastEngine self, FastState state) noexcept:
    cdef int slot
    state.resolution_stage = RESOLUTION_NONE
    state.resolution_cursor = 0
    state.resolution_lost_mask[0] = 0
    state.resolution_lost_mask[1] = 0
    state.resolution_drive_mask[0] = 0
    state.resolution_drive_mask[1] = 0
    state.resolution_protected_mask[0] = 0
    state.resolution_protected_mask[1] = 0
    state.resolution_front_loss_command_penalty[0] = 0
    state.resolution_front_loss_command_penalty[1] = 0
    state.resolution_suppressed_mask = 0
    state.resolution_starter = -1
    for slot in range(SLOT_COUNT):
        state.resolution_contribution_front[slot] = -1

cdef void _fe_resolve_battle_end_operation_constraints(
    FastEngine self,
    FastState state,
) except *:
    cdef int controller, narrative_slot, ix, card, winner = -1
    if popcount16(state.resolution_lost_mask[1]) >= 3:
        winner = 0
    elif popcount16(state.resolution_lost_mask[0]) >= 3:
        winner = 1

    for controller in range(PLAYER_COUNT):
        narrative_slot = self.ongoing_narrative_limit - 1
        while narrative_slot >= 0:
            ix = controller * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
            card = state.narrative[ix]
            if card >= 0 and self.narrative_three_front_next_maneuver[card]:
                if winner >= 0:
                    _fe_add_constraint(
                        state,
                        CONSTRAINT_MANEUVER,
                        winner,
                        card,
                        controller,
                        -1,
                        0,
                        -1,
                        state.turn_number,
                        (
                            CONSTRAINT_EXPIRES_AFTER_OPERATION
                            | CONSTRAINT_PERSISTS_BATTLE
                        ),
                    )
                # Printed "Then discard this Omen" is unconditional at
                # Battle end; only the obligation is conditional.
                _fe_discard_ongoing_narrative(
                    self, state, controller, narrative_slot
                )
            narrative_slot -= 1


cdef void _fe_drop_nonpersistent_constraints(
    FastState state,
) noexcept:
    cdef int i = state.constraint_len - 1
    while i >= 0:
        if not (state.constraint_flags[i] & CONSTRAINT_PERSISTS_BATTLE):
            _fe_remove_constraint_at(state, i)
        i -= 1


cdef void _fe_finish_battle_recovery(FastEngine self, FastState state) except *:
    cdef int p, base_recovery, actual, target, starter, front

    _fe_resolve_battle_end_operation_constraints(self, state)
    _fe_drop_nonpersistent_constraints(state)

    base_recovery = _fe_command_recovery_for_battle(self, state.battle)
    for p in range(PLAYER_COUNT):
        # Lost Fronts reduce current Command after Battle-end effects and
        # before Collapse. The per-Front amount is a rule parameter; card
        # protections have already reduced the resulting penalty.
        # Apply Battle-end losses in full. Command may fall below the
        # Collapse threshold here; that overrun is part of the Collapse
        # comparison and must not be discarded by clamping.
        state.command[p] -= state.resolution_front_loss_command_penalty[p]

        # Battle-end card effects can draw/refund after resolution began;
        # snapshot those counters only once every such effect is done.
        state.last_command_spent[p] = state.command_spent_this_battle[p]
        state.last_command_refunded[p] = state.command_refunded_this_battle[p]
        state.last_cards_drawn[p] = state.cards_drawn_this_battle[p]
        state.last_completion_count[p] = state.completion_count_this_battle[p]
        # Collapse is checked after Front-loss Command attrition and before
        # any recovery.
        state.last_command_before_collapse[p] = state.command[p]
        state.last_front_loss_command_penalty[p] = (
            state.resolution_front_loss_command_penalty[p]
        )
        state.last_recovery_actual[p] = 0
        state.last_command_remaining[p] = state.command[p]
        state.last_deck_remaining[p] = state.deck_len[p]
        state.last_hand_size[p] = state.hand_len[p]

    if (
        state.command[0] <= self.command_collapse_threshold
        or state.command[1] <= self.command_collapse_threshold
    ):
        state.phase = PHASE_COMPLETE
        if state.command[0] < state.command[1]:
            state.winner = 1
        elif state.command[1] < state.command[0]:
            state.winner = 0
        else:
            # Exact simultaneous exhaustion is broken by the commitment that
            # opened the Battle-ending sequence: the first passer collapses.
            # Standard and experimental Pass endings always record that player
            # in pass_order[0].
            if state.pass_len > 0:
                state.winner = other_player(state.pass_order[0])
            else:
                state.winner = -1
        state.cleanup_pending = 0
        state.pending_resume = RESUME_NONE
        state.pending_resume_player = -1
        _fe_clear_resolution_state(self, state)
        return

    # Only a continuing war receives recovery.
    # Front losses have already reduced current Command; they do not reduce
    # recovery a second time.
    for p in range(PLAYER_COUNT):
        actual = base_recovery
        if actual < self.command_recovery_floor:
            actual = self.command_recovery_floor
        state.last_recovery_actual[p] = actual
        state.command[p] += actual
        if state.command[p] > self.command_cap:
            state.command[p] = self.command_cap
        state.last_command_remaining[p] = state.command[p]

    starter = state.resolution_starter
    state.battle += 1
    state.cleanup_pending = 0
    state.pass_len = 0
    state.pass_closing_turns_remaining = 0
    state.pass_order[0] = -1
    state.pass_order[1] = -1

    for p in range(PLAYER_COUNT):
        state.passed[p] = 0
        state.discarded_this_battle[p] = 0
        state.operations_this_battle[p] = 0
        state.cards_played_this_turn_front_mask[p] = 0
        state.cards_played_this_battle_front_mask[p] = 0
        state.narratives_played_this_battle[p] = 0
        state.command_spent_this_battle[p] = 0
        state.command_refunded_this_battle[p] = 0
        state.cards_drawn_this_battle[p] = 0
        state.completion_count_this_battle[p] = 0
        state.stratagem_used[p] = 0
        state.hero_used[p] = 0
        state.free_maneuver_available[p] = 0
        state.free_maneuver_source[p] = -1
        state.player_maneuver_count[p] = 0
        for front in range(self.ongoing_narrative_limit):
            state.narrative_used[p * NARRATIVE_SLOTS_PER_PLAYER + front] = 0
            state.narrative_trigger_mask[p * NARRATIVE_SLOTS_PER_PLAYER + front] = 0
        for front in range(POSITIONS_PER_PLAYER):
            state.maneuver_count[p * POSITIONS_PER_PLAYER + front] = 0
            state.maneuver_direction[p * POSITIONS_PER_PLAYER + front] = DIRECTION_NONE

        target = self.hand_limit - state.hand_len[p]
        if target > 0:
            _fe_draw(self, state, p, target)
        state.battle_start_command[p] = state.command[p]

    _fe_clear_resolution_state(self, state)
    state.pending_resume = RESUME_NONE
    state.pending_resume_player = -1
    _fe_begin_next_battle_fast(self, state, starter)

cdef void _fe_advance_battle_resolution(FastEngine self, FastState state) except *:
    # Any choice queued here must return control to this state machine.
    state.pending_resume = RESUME_BATTLE_RESOLUTION
    state.pending_resume_player = -1

    while True:
        if state.cleanup_pending or state.pending_len > 0:
            return

        if state.resolution_stage == RESOLUTION_PREPARE:
            _fe_queue_pre_resolution_choice(self, state)
            if state.pending_len > 0:
                return
            continue

        if state.resolution_stage == RESOLUTION_COMPARE:
            _fe_compare_battle_fronts(self, state)
            continue

        if state.resolution_stage == RESOLUTION_RETREATS:
            _fe_advance_retreat_resolution(self, state)
            if state.pending_len > 0 or state.cleanup_pending:
                return
            continue

        if state.resolution_stage == RESOLUTION_NARRATIVES:
            if _fe_resolve_one_battle_end_narrative(self, state):
                if state.pending_len > 0 or state.cleanup_pending:
                    return
                continue
            # Printed Battle-end effects resolve while the Battle's public
            # Stratagems and temporary Strength still exist. Only after all
            # such effects are complete do Battle-only effects leave play.
            _fe_discard_battle_stratagems(self, state)
            _fe_clear_battle_temporary_strength(self, state)
            state.resolution_stage = RESOLUTION_RECOVERY
            continue

        if state.resolution_stage == RESOLUTION_RECOVERY:
            _fe_finish_battle_recovery(self, state)
            return

        state.pending_resume = RESUME_NONE
        state.pending_resume_player = -1
        return

cdef void _fe_score_battle(FastEngine self, FastState state) except *:
    """Start resumable Battle-end resolution."""
    cdef int p, slot

    state.last_battle_valid = 1
    state.last_battle = state.battle
    state.last_pass_len = state.pass_len
    for p in range(PLAYER_COUNT):
        state.last_pass_order[p] = (
            state.pass_order[p] if p < state.pass_len else -1
        )
        state.last_command_start[p] = state.battle_start_command[p]
        state.last_command_spent[p] = state.command_spent_this_battle[p]
        state.last_command_refunded[p] = state.command_refunded_this_battle[p]
        state.last_battle_start_hand_size[p] = state.battle_start_hand_size[p]
        state.last_cards_drawn[p] = state.cards_drawn_this_battle[p]
        state.last_completion_count[p] = state.completion_count_this_battle[p]
        state.last_operations[p] = state.operations_this_battle[p]

    state.resolution_starter = (
        state.pass_order[0]
        if state.pass_len > 0
        else state.active_player
    )
    state.resolution_stage = RESOLUTION_PREPARE
    state.resolution_cursor = 0
    state.resolution_suppressed_mask = 0
    state.resolution_lost_mask[0] = 0
    state.resolution_lost_mask[1] = 0
    state.resolution_drive_mask[0] = 0
    state.resolution_drive_mask[1] = 0
    state.resolution_protected_mask[0] = 0
    state.resolution_protected_mask[1] = 0
    state.resolution_front_loss_command_penalty[0] = 0
    state.resolution_front_loss_command_penalty[1] = 0
    for slot in range(SLOT_COUNT):
        state.resolution_contribution_front[slot] = -1

    _fe_advance_battle_resolution(self, state)

cdef void _fe_pass_action(FastEngine self, FastState state, int player):
    cdef int opponent = other_player(player)
    cdef bint already_signalled = bool(state.passed[player])
    cdef uint64_t pass_action = encode_action(TYPE_PASS, -1, -1, -1, player)

    # In standard play the signal is the Pass operation. The experimental
    # free-flag variant records the same public state without consuming the
    # operation or its constraints.
    if self.pass_signal_costs_operation:
        _fe_consume_operation_constraints(self, state, player, pass_action)

    if not already_signalled:
        state.passed[player] = 1
        state.pass_order[state.pass_len] = player
        state.pass_len += 1
        if state.pass_len == 1 and self.pass_closing_rounds > 0:
            state.pass_closing_turns_remaining = PLAYER_COUNT * self.pass_closing_rounds
        if self.pass_signal_costs_operation:
            _fe_resolve_strat_event(self, state, EVENT_PASS, player)

    if state.passed[0] and state.passed[1]:
        _fe_score_battle(self, state)
        if self.pass_signal_costs_operation:
            state.turn_number += 1
        return

    if not self.pass_signal_costs_operation and not already_signalled:
        # Raising a Battle Flag is free and leaves the player in the same turn.
        return

    # A repeated signal is only legal when this already-signalled player has
    # no normal operation. It yields the turn and counts toward a closing
    # window just like any other completed turn.
    if (
        already_signalled
        and self.pass_closing_rounds > 0
        and state.pass_closing_turns_remaining > 0
    ):
        state.pass_closing_turns_remaining -= 1
        if state.pass_closing_turns_remaining == 0:
            state.turn_number += 1
            _fe_score_battle(self, state)
            return

    _fe_start_turn_fast(self, state, opponent)
    state.turn_number += 1
