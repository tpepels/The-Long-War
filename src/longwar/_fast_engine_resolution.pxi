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
    if cursor < 2:
        controller = cursor
        state.resolution_cursor += 1
        force = state.stratagem[controller]
        if force >= 0 and self.feigned_retreat_strat[force]:
            mask = 0
            for front in range(4):
                slot = slot_index(controller, front, 0)
                rear = slot_index(controller, front, 1)
                if (
                    state.subject[slot] >= 0
                    and state.subject[rear] >= 0
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
    if cursor < 18:
        slot = cursor - 2
        state.resolution_cursor += 1
        if (
            state.subject[slot] >= 0
            and _fe_slot_complete(self, state, slot)
            and rank_from_slot(slot) == 0
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
    if cursor < 34:
        slot = cursor - 18
        state.resolution_cursor += 1
        force = state.subject[slot]
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
    if cursor < 50:
        slot = cursor - 34
        state.resolution_cursor += 1
        force = state.subject[slot]
        if force < 0:
            return
        controller = owner_from_slot(slot)
        opponent = 1 - controller
        front = front_from_slot(slot)
        target = -1
        if self.suppress_rear_force[force]:
            rear = slot_index(opponent, front, 1)
            if state.subject[rear] >= 0:
                target = rear
        elif self.first_strike_force[force]:
            target = slot_index(opponent, front, 0)
            if (
                state.subject[target] < 0
                or self.strength[state.subject[target]]
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
    if cursor < 66:
        slot = cursor - 50
        state.resolution_cursor += 1
        if state.subject[slot] < 0:
            return
        bond = state.link[slot]
        if bond < 0 or not self.sacrifice_bond[bond]:
            return
        controller = owner_from_slot(slot)
        opponent = 1 - controller
        front = front_from_slot(slot)
        target_mask = 0
        target = slot_index(opponent, front, 0)
        if state.subject[target] >= 0:
            target_mask |= <uint16_t>(1 << target)
        target = slot_index(opponent, front, 1)
        if state.subject[target] >= 0:
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

cdef void _fe_compare_battle_fronts(FastEngine self, FastState state) noexcept:
    cdef int front, a, b, p, strat, protected, card
    cdef int controller, mask, combined0, combined1
    cdef int losses0, losses1
    cdef bint tie_control = _fe_tie_control_active(self, state)

    state.resolution_lost_mask[0] = 0
    state.resolution_lost_mask[1] = 0
    state.resolution_drive_mask[0] = 0
    state.resolution_drive_mask[1] = 0

    for front in range(4):
        a = _fe_resolution_front_strength_fast(self, state, 0, front)
        b = _fe_resolution_front_strength_fast(self, state, 1, front)
        state.last_front_scores[front][0] = a
        state.last_front_scores[front][1] = b
        if a < b:
            state.resolution_lost_mask[0] |= <uint8_t>(1 << front)
        elif b < a:
            state.resolution_lost_mask[1] |= <uint8_t>(1 << front)
        elif tie_control:
            if (
                _fe_slot_complete(self, state, slot_index(0, front, 0))
                != _fe_slot_complete(self, state, slot_index(1, front, 0))
            ):
                if _fe_slot_complete(self, 
                    state, slot_index(0, front, 0)
                ):
                    state.resolution_lost_mask[1] |= <uint8_t>(
                        1 << front
                    )
                else:
                    state.resolution_lost_mask[0] |= <uint8_t>(
                        1 << front
                    )

    # The Center Must Hold replaces the two individual results.
    for controller in range(2):
        strat = state.stratagem[controller]
        if strat < 0 or not self.strat_combine_fronts[strat]:
            continue
        mask = state.stratagem_front_mask[controller] & 15
        if popcount16(mask) != 2:
            continue
        combined0 = 0
        combined1 = 0
        for front in range(4):
            if mask & (1 << front):
                combined0 += _fe_resolution_front_strength_fast(self, 
                    state, 0, front
                )
                combined1 += _fe_resolution_front_strength_fast(self, 
                    state, 1, front
                )
        state.resolution_lost_mask[0] &= <uint8_t>(~mask)
        state.resolution_lost_mask[1] &= <uint8_t>(~mask)
        if combined0 < combined1:
            state.resolution_lost_mask[0] |= <uint8_t>mask
        elif combined1 < combined0:
            state.resolution_lost_mask[1] |= <uint8_t>mask

    # Breakthrough replacements.
    for front in range(4):
        if (
            state.resolution_lost_mask[0] & (1 << front)
            and state.subject[slot_index(0, front, 1)] < 0
            and _fe_breakthrough_active(self, state, 1, front)
        ):
            state.resolution_drive_mask[0] |= <uint8_t>(1 << front)
        if (
            state.resolution_lost_mask[1] & (1 << front)
            and state.subject[slot_index(1, front, 1)] < 0
            and _fe_breakthrough_active(self, state, 0, front)
        ):
            state.resolution_drive_mask[1] |= <uint8_t>(1 << front)

    for controller in range(2):
        strat = state.stratagem[controller]
        if strat >= 0 and self.strat_no_retreat[strat]:
            mask = state.stratagem_front_mask[controller] & 15
            state.resolution_drive_mask[0] |= (
                state.resolution_lost_mask[0] & mask
            )
            state.resolution_drive_mask[1] |= (
                state.resolution_lost_mask[1] & mask
            )

    strat = state.stratagem[0]
    if strat >= 0 and self.strat_encirclement[strat]:
        if (state.resolution_lost_mask[1] & 7) == 7:
            state.resolution_drive_mask[1] |= <uint8_t>(1 << 1)
        if (state.resolution_lost_mask[1] & 14) == 14:
            state.resolution_drive_mask[1] |= <uint8_t>(1 << 2)
    strat = state.stratagem[1]
    if strat >= 0 and self.strat_encirclement[strat]:
        if (state.resolution_lost_mask[0] & 7) == 7:
            state.resolution_drive_mask[0] |= <uint8_t>(1 << 1)
        if (state.resolution_lost_mask[0] & 14) == 14:
            state.resolution_drive_mask[0] |= <uint8_t>(1 << 2)

    # Preserve the effective Front outcomes before retreat/cleanup clears the
    # live resolution masks. These can differ from the raw Strength comparison
    # because Stratagems such as The Ground Was Held and The Center Must Hold
    # replace tied or per-Front results.
    state.last_lost_mask[0] = state.resolution_lost_mask[0] & 15
    state.last_lost_mask[1] = state.resolution_lost_mask[1] & 15

    losses0 = popcount16(state.resolution_lost_mask[0] & 15)
    losses1 = popcount16(state.resolution_lost_mask[1] & 15)
    state.resolution_recovery_losses[0] = losses0
    state.resolution_recovery_losses[1] = losses1

    for front in range(4):
        if state.resolution_lost_mask[0] & (1 << front):
            protected = 0
            for p in range(2):
                card = state.subject[slot_index(0, front, p)]
                if card >= 0 and self.recovery_protected_front[card]:
                    protected = 1
            if protected and state.resolution_recovery_losses[0] > 0:
                state.resolution_recovery_losses[0] -= 1
        if state.resolution_lost_mask[1] & (1 << front):
            protected = 0
            for p in range(2):
                card = state.subject[slot_index(1, front, p)]
                if card >= 0 and self.recovery_protected_front[card]:
                    protected = 1
            if protected and state.resolution_recovery_losses[1] > 0:
                state.resolution_recovery_losses[1] -= 1

    strat = state.stratagem[0]
    if strat >= 0 and self.strat_recovery_loss_reduction[strat]:
        state.resolution_recovery_losses[0] -= min(
            state.resolution_recovery_losses[0],
            self.strat_recovery_loss_reduction[strat],
        )
    strat = state.stratagem[1]
    if strat >= 0 and self.strat_recovery_loss_reduction[strat]:
        state.resolution_recovery_losses[1] -= min(
            state.resolution_recovery_losses[1],
            self.strat_recovery_loss_reduction[strat],
        )

    _fe_discard_incomplete_formations(self, state)
    state.resolution_stage = RESOLUTION_RETREATS
    state.resolution_cursor = 0

cdef void _fe_advance_retreat_resolution(FastEngine self, FastState state) except *:
    cdef int player, front, front_slot, rear_slot, force
    cdef uint16_t destinations

    while state.resolution_cursor < 8:
        player = state.resolution_cursor // 4
        front = state.resolution_cursor % 4
        if not (
            state.resolution_lost_mask[player] & (1 << front)
        ):
            state.resolution_cursor += 1
            continue

        front_slot = slot_index(player, front, 0)
        rear_slot = slot_index(player, front, 1)

        # Snapshot persistent Rear effects before that formation is driven
        # off. Upper drive-mask bits are temporary Neris markers.
        force = state.subject[rear_slot]
        if force >= 0 and self.neris_rear_force[force]:
            state.resolution_drive_mask[player] |= <uint8_t>(
                1 << (front + 4)
            )

        if _fe_slot_complete(self, state, front_slot) and force >= 0:
            if self.rear_force_prevents_frontline_retreat[force]:
                state.resolution_protected_mask[player] |= <uint8_t>(
                    1 << front
                )
            elif (
                self.optional_alda_protect_force[force]
                and not (
                    state.resolution_protected_mask[player]
                    & (1 << (front + 4))
                )
            ):
                # Mark offered before pausing so declining cannot requeue it.
                state.resolution_protected_mask[player] |= <uint8_t>(
                    1 << (front + 4)
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

        if _fe_front_has_capture_bond(self, state, 1 - player, front):
            _fe_return_bond_to_hand_from_slot(self, 
                state, player, rear_slot
            )

        if state.resolution_drive_mask[player] & (1 << (front + 4)):
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

    _fe_discard_battle_stratagems(self, state)
    _fe_clear_battle_temporary_strength(self, state)
    state.resolution_stage = RESOLUTION_NARRATIVES
    state.resolution_cursor = 0

cdef bint _fe_resolve_one_battle_end_narrative(
    FastEngine self,
    FastState state,
) except *:
    cdef int player, story_slot, ix, card, kind, front
    cdef int target_slot, gain
    cdef uint8_t front_mask
    cdef bint condition, won
    for player in range(2):
        for story_slot in range(self.ongoing_story_limit):
            ix = player * 4 + story_slot
            card = state.scheme[ix]
            if card < 0:
                continue
            kind = self.narrative_end_kind[card]
            if kind == NARR_END_NONE:
                continue

            condition = False
            won = False
            front_mask = state.scheme_front_mask[ix]
            front = -1
            for target_slot in range(4):
                if front_mask & (1 << target_slot):
                    front = target_slot
                    break

            if kind == NARR_END_NOT_LOST and front >= 0:
                condition = not (
                    state.resolution_lost_mask[player]
                    & (1 << front)
                )
                won = bool(
                    state.resolution_lost_mask[1 - player]
                    & (1 << front)
                )
            elif kind == NARR_END_WON and front >= 0:
                won = bool(
                    state.resolution_lost_mask[1 - player]
                    & (1 << front)
                )
                condition = won
            elif kind == NARR_END_TARGET_SURVIVES:
                target_slot = state.scheme_target_slot[ix]
                condition = (
                    target_slot >= 0
                    and state.subject[target_slot] >= 0
                )

            gain = self.narrative_end_gain[card]
            if condition and gain:
                _fe_gain_command_from_narrative(self, 
                    state, player, gain
                )
            if condition and self.narrative_end_draw[card]:
                _fe_queue_battle_draws(self, state, player, 1)
            if (
                condition
                and won
                and self.narrative_end_recover_bond[card]
            ):
                _fe_queue_recover_from_discard(self, 
                    state, player, CARD_LINK, True
                )

            # These cards all end at Battle end whether or not their
            # condition succeeded.
            if self.narrative_end_discard[card]:
                _fe_discard_ongoing_narrative(self, 
                    state, player, story_slot
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
    state.resolution_recovery_losses[0] = 0
    state.resolution_recovery_losses[1] = 0
    state.resolution_suppressed_mask = 0
    state.resolution_starter = -1
    for slot in range(SLOT_COUNT):
        state.resolution_contribution_front[slot] = -1

cdef void _fe_resolve_battle_end_operation_constraints(
    FastEngine self,
    FastState state,
) except *:
    cdef int controller, story_slot, ix, card, winner = -1
    if popcount16(state.resolution_lost_mask[1]) >= 3:
        winner = 0
    elif popcount16(state.resolution_lost_mask[0]) >= 3:
        winner = 1

    for controller in range(2):
        story_slot = self.ongoing_story_limit - 1
        while story_slot >= 0:
            ix = controller * 4 + story_slot
            card = state.scheme[ix]
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
                    self, state, controller, story_slot
                )
            story_slot -= 1


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
    for p in range(2):
        # Battle-end card effects can draw/refund after resolution began;
        # snapshot those counters only once every such effect is done.
        state.last_command_spent[p] = state.command_spent_this_battle[p]
        state.last_command_refunded[p] = state.command_refunded_this_battle[p]
        state.last_cards_drawn[p] = state.cards_drawn_this_battle[p]
        state.last_completion_count[p] = state.completion_count_this_battle[p]
        state.last_command_before_recovery[p] = state.command[p]
        state.last_recovery_loss[p] = state.resolution_recovery_losses[p]
        actual = base_recovery - state.resolution_recovery_losses[p]
        if actual < self.command_recovery_floor:
            actual = self.command_recovery_floor
        state.last_recovery_actual[p] = actual
        state.command[p] += actual
        if state.command[p] > self.command_cap:
            state.command[p] = self.command_cap
        state.last_command_remaining[p] = state.command[p]
        state.last_deck_remaining[p] = state.deck_len[p]
        state.last_hand_size[p] = state.hand_len[p]

    if (
        state.command[0] < self.command_collapse_threshold
        or state.command[1] < self.command_collapse_threshold
    ):
        if state.command[0] < state.command[1]:
            state.phase = PHASE_COMPLETE
            state.winner = 1
        elif state.command[1] < state.command[0]:
            state.phase = PHASE_COMPLETE
            state.winner = 0
        if state.phase == PHASE_COMPLETE:
            state.cleanup_pending = 0
            state.pending_resume = RESUME_NONE
            state.pending_resume_player = -1
            _fe_clear_resolution_state(self, state)
            return

    starter = state.resolution_starter
    state.battle += 1
    state.cleanup_pending = 0
    state.pass_len = 0
    state.pass_order[0] = -1
    state.pass_order[1] = -1

    for p in range(2):
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
        state.player_maneuver_count[p] = 0
        for front in range(self.ongoing_story_limit):
            state.scheme_used[p * 4 + front] = 0
            state.scheme_trigger_mask[p * 4 + front] = 0
        for front in range(8):
            state.maneuver_count[p * 8 + front] = 0
            state.maneuver_direction[p * 8 + front] = 0

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
    for p in range(2):
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
    state.resolution_recovery_losses[0] = 0
    state.resolution_recovery_losses[1] = 0
    for slot in range(SLOT_COUNT):
        state.resolution_contribution_front[slot] = -1

    _fe_advance_battle_resolution(self, state)

cdef void _fe_pass_action(FastEngine self, FastState state, int player):
    cdef int opponent = 1 - player
    cdef uint64_t pass_action = encode_action(TYPE_PASS, -1, -1, -1, player)

    # Pass is one of the three canonical operations. It can only remain
    # legal while an active requirement is impossible, but once chosen it
    # still consumes that player's "next operation" requirements.
    _fe_consume_operation_constraints(self, state, player, pass_action)

    state.passed[player] = 1
    state.pass_order[state.pass_len] = player
    state.pass_len += 1
    _fe_resolve_strat_event(self, state, EVENT_PASS, player)

    if state.pass_len >= 2:
        _fe_score_battle(self, state)
    else:
        # A first Pass hands the opponent a completely normal turn.
        _fe_start_turn_fast(self, state, opponent)

    state.turn_number += 1
