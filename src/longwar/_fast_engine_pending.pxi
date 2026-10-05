cdef uint32_t _fe_asha_mask_for_suppression(
    FastEngine self,
    FastState state,
    int defender,
    int front,
    int original_target,
) noexcept:
    cdef int rank, slot, name
    cdef uint32_t mask = 0
    for rank in range(RANK_COUNT):
        slot = slot_index(defender, front, rank)
        if slot == original_target or not _fe_slot_complete(self, state, slot):
            continue
        name = state.name[slot]
        if name >= 0 and self.intercept_name[name]:
            mask |= <uint32_t>(1 << slot)
    return mask

cdef void _fe_suppress_with_interception(
    FastEngine self,
    FastState state,
    int controller,
    int target,
) except *:
    cdef int defender = owner_from_slot(target)
    cdef int front = front_from_slot(target)
    cdef uint32_t interceptors = _fe_asha_mask_for_suppression(self, 
        state, defender, front, target
    )
    if interceptors:
        _fe_enqueue_effect(self, 
            state,
            EFFECT_INTERCEPT,
            defender,
            -1,
            target,
            target,
            interceptors,
            0,
            EFFECT_OPTIONAL,
        )
    else:
        state.resolution_suppressed_mask |= <uint32_t>(1 << target)

cdef void _fe_apply_pending_effect(FastEngine self, FastState state, uint64_t action) except *:
    cdef int kind = state.pending_kind[0]
    cdef int player = state.pending_player[0]
    cdef int card = action_card(action)
    cdef int source = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int trigger_source = state.pending_source[0]
    cdef int command_source = state.pending_command_source[0]
    cdef int aux = state.pending_aux[0]
    cdef bint skip = card < 0 and source < 0 and dest < 0
    cdef bint was_empty
    cdef int before_mask, moved

    _fe_pop_pending_effect(self, state)

    if kind == EFFECT_FREE_MANEUVER:
        if not skip:
            was_empty = state.force[dest] < 0
            moved = 1 if front_from_slot(dest) < front_from_slot(source) else 2
            _fe_swap_slots(self, state, source, dest)
            state.maneuver_count[dest] += 1
            state.maneuvered_in_operation[dest] = 1
            state.maneuver_direction[dest] = moved
            state.player_maneuver_count[player] += 1
            if state.free_maneuver_available[player]:
                state.free_maneuver_available[player] = 0
                state.free_maneuver_source[player] = -1
            _fe_record_command_diag(
                self,
                COMMAND_DIAG_DISCOUNT,
                COMMAND_DETAIL_FREE_MANEUVER,
                player,
                command_source,
                self.maneuver_command_cost,
                self.maneuver_command_cost,
            )
            _fe_resolve_maneuver_triggers(
                self, state, player, source, dest, was_empty
            )
    elif kind == EFFECT_MOVE:
        if not skip:
            _fe_move_slot(self, state, source, dest)
            _fe_resolve_force_move_triggers(self, state, player, source, dest)
    elif kind == EFFECT_SWAP:
        if not skip:
            _fe_swap_slots(self, state, source, dest)
            _fe_resolve_force_move_triggers(self, state, player, source, dest)
            _fe_resolve_force_move_triggers(self, state, player, dest, source)
    elif kind == EFFECT_RECOVER:
        if not skip and card >= 0 and _fe_remove_from_discard(self, state, player, card):
            _fe_return_to_hand(self, state, player, card)
    elif kind == EFFECT_FRONT_CONTRIBUTION:
        if not skip and source >= 0 and dest >= 0:
            state.resolution_contribution_front[source] = dest
    elif kind == EFFECT_SUPPRESS:
        if not skip and dest >= 0:
            _fe_suppress_with_interception(self, state, player, dest)
    elif kind == EFFECT_SACRIFICE:
        if not skip and source >= 0 and dest >= 0:
            _fe_discard_slot_components(self, state, player, source)
            _fe_suppress_with_interception(self, state, player, dest)
    elif kind == EFFECT_INTERCEPT:
        if skip:
            if aux >= 0:
                state.resolution_suppressed_mask |= <uint32_t>(1 << aux)
        elif source >= 0:
            state.resolution_suppressed_mask |= <uint32_t>(1 << source)
    elif kind == EFFECT_RETREAT:
        if not skip and source >= 0 and dest >= 0:
            _fe_retreat_slot(self, state, player, source, dest)
    elif kind == EFFECT_PROTECT_RETREAT:
        if source < 0:
            source = trigger_source
        if source >= 0:
            state.resolution_protected_mask[player] |= <uint8_t>(
                1 << (front_from_slot(source) + FRONT_COUNT)
            )
        if not skip and source >= 0:
            state.resolution_protected_mask[player] |= <uint8_t>(
                1 << front_from_slot(source)
            )
            _fe_drive_off_slot(self, state, player, source)
    elif kind == EFFECT_TRANSFER_COMPONENT:
        if not skip and source >= 0 and dest >= 0 and card >= 0:
            before_mask = _fe_complete_mask(self, state, player)
            if state.bond[source] == card and state.bond[dest] < 0:
                state.bond[source] = -1
                state.bond[dest] = card
            elif state.name[source] == card and state.name[dest] < 0:
                state.name[source] = -1
                state.name[dest] = card
            _fe_resolve_new_completions_fast(self, state, player, before_mask)
    elif kind == EFFECT_SUCCESSION:
        if not skip and trigger_source >= 0 and dest >= 0:
            moved = state.name[trigger_source]
            if moved >= 0:
                before_mask = _fe_complete_mask(self, state, player)
                state.name[trigger_source] = -1
                state.name[dest] = moved
                _fe_resolve_new_completions_fast(self, state, player, before_mask)
        _fe_finish_pending_drive_off(self, state, player, trigger_source)

    _fe_resume_pending_flow(self, state)

cdef void _fe_queue_take_adjacent_prepared_component_on_force_play(
    FastEngine self,
    FastState state,
    int player,
    int destination,
) except *:
    cdef int front = front_from_slot(destination)
    cdef int rank = rank_from_slot(destination)
    cdef int source
    cdef uint32_t sources = 0
    if front > 0:
        source = slot_index(player, front - 1, rank)
        if state.force[source] < 0 and (
            (state.bond[source] >= 0 and state.bond[destination] < 0)
            or (state.name[source] >= 0 and state.name[destination] < 0)
        ):
            sources |= <uint32_t>(1 << source)
    if front < FRONT_COUNT - 1:
        source = slot_index(player, front + 1, rank)
        if state.force[source] < 0 and (
            (state.bond[source] >= 0 and state.bond[destination] < 0)
            or (state.name[source] >= 0 and state.name[destination] < 0)
        ):
            sources |= <uint32_t>(1 << source)
    if sources:
        _fe_enqueue_effect(self, 
            state,
            EFFECT_TRANSFER_COMPONENT,
            player,
            -1,
            -1,
            destination,
            sources,
            0,
            EFFECT_OPTIONAL,
        )

cdef void _fe_queue_take_adjacent_open_bond_on_name_play(
    FastEngine self,
    FastState state,
    int player,
    int destination,
) except *:
    cdef int front = front_from_slot(destination)
    cdef int rank = rank_from_slot(destination)
    cdef int source
    cdef uint32_t sources = 0
    if state.force[destination] < 0 or state.bond[destination] >= 0:
        return
    if front > 0:
        source = slot_index(player, front - 1, rank)
        if (
            state.force[source] >= 0
            and state.bond[source] >= 0
            and state.name[source] < 0
        ):
            sources |= <uint32_t>(1 << source)
    if front < FRONT_COUNT - 1:
        source = slot_index(player, front + 1, rank)
        if (
            state.force[source] >= 0
            and state.bond[source] >= 0
            and state.name[source] < 0
        ):
            sources |= <uint32_t>(1 << source)
    if sources:
        _fe_enqueue_effect(self, 
            state,
            EFFECT_TRANSFER_COMPONENT,
            player,
            -1,
            -1,
            destination,
            sources,
            0,
            EFFECT_OPTIONAL,
        )


cdef void _fe_discard_narrative_by_card(
    FastEngine self,
    FastState state,
    int controller,
    int card,
) noexcept:
    cdef int narrative_slot, ix
    for narrative_slot in range(self.ongoing_narrative_limit):
        ix = controller * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
        if state.narrative[ix] == card:
            _fe_discard_ongoing_narrative(
                self, state, controller, narrative_slot
            )
            return


cdef void _fe_first_card_front_constraint_triggers(
    FastEngine self,
    FastState state,
    int actor,
    int front,
) except *:
    cdef int controller, narrative_slot, ix, card, mask
    for controller in range(PLAYER_COUNT):
        narrative_slot = 0
        while narrative_slot < self.ongoing_narrative_limit:
            ix = controller * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
            card = state.narrative[ix]
            if card < 0:
                narrative_slot += 1
                continue
            if (
                not self.narrative_first_card_front_constraint[card]
                or not (state.narrative_front_mask[ix] & (1 << front))
                or state.narrative_trigger_mask[ix] & (1 << actor)
            ):
                narrative_slot += 1
                continue

            state.narrative_trigger_mask[ix] |= <uint8_t>(1 << actor)
            _fe_add_constraint(
                state,
                CONSTRAINT_AFFECT_FRONT,
                actor,
                card,
                controller,
                front,
                0,
                -1,
                state.turn_number + NEXT_OPERATION_TURN_OFFSET,
                CONSTRAINT_EXPIRES_AFTER_OPERATION,
            )
            mask = state.narrative_trigger_mask[ix]
            if mask == ALL_PLAYERS_MASK:
                _fe_discard_ongoing_narrative(
                    self, state, controller, narrative_slot
                )
                continue
            narrative_slot += 1


cdef void _fe_consume_operation_constraints(
    FastEngine self,
    FastState state,
    int actor,
    uint64_t action,
) except *:
    cdef int i, flags, card, owner
    cdef bint satisfied
    i = state.constraint_len - 1
    while i >= 0:
        if (
            state.constraint_player[i] != actor
            or state.turn_number < state.constraint_activate_turn[i]
            or not (
                state.constraint_flags[i]
                & CONSTRAINT_EXPIRES_AFTER_OPERATION
            )
        ):
            i -= 1
            continue
        flags = state.constraint_flags[i]
        card = state.constraint_source_card[i]
        owner = state.constraint_source_owner[i]
        satisfied = _fe_constraint_satisfied(self, state, i, action)
        _fe_remove_constraint_at(state, i)
        if satisfied and flags & CONSTRAINT_DRAW_ON_SATISFY:
            _fe_queue_battle_draws(self, state, actor, 1)
        if flags & CONSTRAINT_DISCARD_SOURCE_NARRATIVE:
            _fe_discard_narrative_by_card(self, state, owner, card)
        i -= 1


cdef void _fe_apply_fast(FastEngine self, FastState state, uint64_t action):
    cdef int kind = action_kind(action)
    cdef int card = action_card(action)
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int actor = state.active_player
    cdef int front, before_mask = 0, cost = 0, source, target, local, choice, second_card, strat
    cdef uint32_t extra = action_extra(action)
    cdef bint cancelled, prepared_before, take_adjacent_open_bond_ready

    # A new Action starts a fresh Maneuver-resolution chain. Effect choices
    # and mandatory hand-limit cleanup steps continue the current Action.
    if kind != TYPE_EFFECT and kind != TYPE_DISCARD:
        memset(
            state.maneuvered_in_operation,
            0,
            sizeof(state.maneuvered_in_operation),
        )

    if kind == TYPE_PASS:
        _fe_pass_action(self, state, actor)
        return

    if kind == TYPE_END_TURN:
        # Ending a turn is not an Action and never starts Battle closing.
        state.turn_number += 1
        _fe_finish_turn_fast(self, state, actor)
        return

    if kind == TYPE_EFFECT:
        _fe_apply_pending_effect(self, state, action)
        return

    if kind == TYPE_DISCARD:
        if not state.cleanup_pending:
            raise ValueError("Discard is only legal for hand-limit cleanup")
        _fe_take_from_hand(self, state, actor, card, 0)
        _fe_append_discard(self, state, actor, card, False)
        if state.hand_len[actor] > self.hand_limit:
            return
        state.cleanup_pending = 0
        if state.pending_draw_count > 0:
            _fe_queue_battle_draws(
                self,
                state,
                actor,
                state.pending_draw_count,
            )
            if state.cleanup_pending:
                return
        _fe_resume_pending_flow(self, state)
        return

    state.pending_resume = RESUME_FINISH_OPERATION
    state.pending_resume_player = actor

    # A self-only continuous Stratagem may remain hidden until its mechanic is
    # actually used. Reveal it before resolving the Maneuver whose legality or
    # Command cost depends on that secret identity.
    if kind == TYPE_MANEUVER:
        strat = state.stratagem[actor]
        if strat >= 0 and not state.stratagem_revealed[actor]:
            if self.strat_maneuver_cost[strat] >= 0:
                state.stratagem_revealed[actor] = 1
            elif (
                self.strat_directional_maneuver[strat]
                and (
                    (
                        state.stratagem_direction[actor] == DIRECTION_LEFT
                        and front_from_slot(dest) < front_from_slot(pos)
                    )
                    or (
                        state.stratagem_direction[actor] == DIRECTION_RIGHT
                        and front_from_slot(dest) > front_from_slot(pos)
                    )
                )
            ):
                state.stratagem_revealed[actor] = 1

    cost = _fe_command_cost_fast(self, state, action)
    _fe_spend_command_fast(self, state, actor, cost)

    if kind == TYPE_CYCLE:
        second_card = <int>extra - 1
        if (
            card < 0
            or second_card < 0
            or second_card >= self.n_cards
            or state.hand[actor][card] <= 0
            or state.hand[actor][second_card] <= 0
            or (card == second_card and state.hand[actor][card] < 2)
        ):
            raise ValueError("Cycle requires two cards currently in hand")
        _fe_take_from_hand(self, state, actor, card, HIDDEN_KNOWN_SINGLE_CARD)
        _fe_append_discard(self, state, actor, card, True)
        _fe_take_from_hand(
            self, state, actor, second_card, HIDDEN_KNOWN_SINGLE_CARD
        )
        _fe_append_discard(self, state, actor, second_card, True)
        _fe_queue_battle_draws(self, state, actor, 1)
        _fe_consume_operation_constraints(self, state, actor, action)
        _fe_resume_pending_flow(self, state)
        return

    if kind == TYPE_MANEUVER:
        target = 1 if state.force[dest] < 0 else 0
        choice = 1 if front_from_slot(dest) < front_from_slot(pos) else 2
        _fe_swap_slots(self, state, pos, dest)
        state.maneuver_count[dest] += 1
        state.maneuvered_in_operation[dest] = 1
        state.maneuver_direction[dest] = choice
        state.player_maneuver_count[actor] += 1
        if state.free_maneuver_available[actor]:
            state.free_maneuver_available[actor] = 0
            state.free_maneuver_source[actor] = -1
        _fe_resolve_force_pair_narratives(self, state, actor)
        _fe_resolve_maneuver_triggers(self, state, actor, pos, dest, bool(target))
        _fe_consume_operation_constraints(self, state, actor, action)
        _fe_resume_pending_flow(self, state)
        return

    if kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME:
        before_mask = _fe_complete_mask(self, state, actor)
        front = front_from_slot(pos)
        state.cards_played_this_turn_front_mask[actor] |= 1 << front
        state.cards_played_this_battle_front_mask[actor] |= 1 << front
    if kind == TYPE_FORCE and card >= 0 and self.hero[card]:
        state.hero_used[actor] |= 1
    elif kind == TYPE_NAME and card >= 0 and self.hero[card]:
        state.hero_used[actor] |= 2

    if kind == TYPE_FORCE:
        prepared_before = state.bond[pos] >= 0 or state.name[pos] >= 0
        _fe_take_from_hand(self, state, actor, card, 0)
        state.force[pos] = card
        if (self.card_capabilities[card] & CAP_PREPARED_ON_PLAY_FREE_MANEUVER_FORCE) and prepared_before:
            _fe_queue_free_maneuver(
                self, state, actor, <uint32_t>(1 << pos),
                True, True, card
            )
        if (self.card_capabilities[card] & CAP_ON_PLAY_TAKE_ADJACENT_PREPARED_COMPONENT_FORCE):
            _fe_queue_take_adjacent_prepared_component_on_force_play(self, state, actor, pos)
        _fe_resolve_force_pair_narratives(self, state, actor)
        front = front_from_slot(pos)
        _fe_resolve_strat_event(self, state, EVENT_FORCE, actor, card, pos)

    elif kind == TYPE_BOND:
        _fe_take_from_hand(self, state, actor, card, 0)
        state.bond[pos] = card
        if state.force[pos] >= 0:
            state.temporary[pos] += self.on_bond_bonus[state.force[pos]]
        if dest >= 0:
            source = pos
            _fe_move_slot(self, state, source, dest)
            pos = dest
            _fe_resolve_force_move_triggers(self, state, actor, source, dest)
            _fe_resolve_force_pair_narratives(self, state, actor)
        if extra and self.bond_optional_draw_count[card] > 0:
            _fe_queue_battle_draws(self, 
                state,
                actor,
                self.bond_optional_draw_count[card],
            )
        front = front_from_slot(pos)

    elif kind == TYPE_NAME:
        take_adjacent_open_bond_ready = (
            (self.card_capabilities[card] & CAP_ON_PLAY_TAKE_ADJACENT_OPEN_BOND_NAME)
            and state.force[pos] >= 0
            and state.bond[pos] < 0
        )
        _fe_take_from_hand(self, state, actor, card, 0)
        state.name[pos] = card
        if take_adjacent_open_bond_ready:
            _fe_queue_take_adjacent_open_bond_on_name_play(self, state, actor, pos)
        _fe_resolve_strat_event(self, state, EVENT_NAME, actor, card, pos)

    elif kind == TYPE_NARRATIVE:
        _fe_take_from_hand(self, state, actor, card, 0)
        state.narratives_played_this_battle[actor] += 1
        if extra and self.narrative_discard_count[card] == 1:
            target = <int>extra - 1
            if target >= 0 and state.hand[actor][target] > 0:
                _fe_take_from_hand(self, state, actor, target, 0)
                _fe_append_discard(self, state, actor, target, True)
                _fe_gain_command_fast(self,
                    state,
                    actor,
                    self.narrative_discard_gain_command[card],
                    card,
                    COMMAND_DETAIL_DISCARD_GAIN,
                )
        cancelled = _fe_pre_narrative_cancel(self, state, actor)
        if not cancelled:
            _fe_resolve_narrative(self, state, actor, card, pos, dest)
            _fe_append_discard(self, state, actor, card, True)

    elif kind == TYPE_ONGOING_NARRATIVE:
        _fe_take_from_hand(self, state, actor, card, 0)
        state.narratives_played_this_battle[actor] += 1
        state.narrative[actor * NARRATIVE_SLOTS_PER_PLAYER + pos] = card
        state.narrative_front_mask[actor * NARRATIVE_SLOTS_PER_PLAYER + pos] = (
            <uint8_t>(extra & FRONT_MASK)
            if self.narrative_choice_kind[card] == NARRATIVE_CHOICE_FRONT
            else 0
        )
        state.narrative_target_slot[actor * NARRATIVE_SLOTS_PER_PLAYER + pos] = dest
        if self.narrative_choice_kind[card] == NARRATIVE_CHOICE_NAMED_DIRECTION:
            state.narrative_direction[actor * NARRATIVE_SLOTS_PER_PLAYER + pos] = <uint8_t>extra
        if self.narrative_forced_named_direction[card]:
            _fe_add_constraint(
                state,
                CONSTRAINT_SPECIFIC_MANEUVER,
                actor,
                card,
                actor,
                -1,
                <int>extra,
                dest,
                CONSTRAINT_ACTIVATE_NEXT_TURN,
                (
                    CONSTRAINT_EXPIRES_AFTER_OPERATION
                    | CONSTRAINT_PERSISTS_BATTLE
                    | CONSTRAINT_ZERO_COST
                    | CONSTRAINT_DRAW_ON_SATISFY
                    | CONSTRAINT_DISCARD_SOURCE_NARRATIVE
                    | CONSTRAINT_EXPIRES_END_OF_ACTIVATED_TURN
                ),
            )

    elif kind == TYPE_STRATAGEM:
        _fe_take_from_hand(self, state, actor, card, 0)
        state.stratagem[actor] = card
        state.stratagem_revealed[actor] = 0
        state.stratagem_front_mask[actor] = (
            <uint8_t>pos if pos >= 0 else 0
        )
        state.stratagem_direction[actor] = (
            <uint8_t>(dest + 1) if dest >= 0 else 0
        )
        state.stratagem_target_mask[actor] = <uint32_t>extra
        state.stratagem_used[actor] += 1

        if self.strat_next_operation_front[card] and pos >= 0:
            front = 0
            while front < FRONT_COUNT and not (pos & (1 << front)):
                front += 1
            if front < FRONT_COUNT:
                _fe_add_constraint(
                    state,
                    CONSTRAINT_AFFECT_FRONT,
                    actor,
                    card,
                    actor,
                    front,
                    0,
                    -1,
                    state.turn_number + NEXT_OPERATION_TURN_OFFSET,
                    CONSTRAINT_EXPIRES_AFTER_OPERATION,
                )
                _fe_add_constraint(
                    state,
                    CONSTRAINT_AFFECT_FRONT,
                    other_player(actor),
                    card,
                    actor,
                    front,
                    0,
                    -1,
                    state.turn_number + NEXT_OPERATION_TURN_OFFSET,
                    CONSTRAINT_EXPIRES_AFTER_OPERATION,
                )

        choice = self.strat_choice_kind[card]

        # Immediate effects and hidden mechanics that constrain both players
        # cannot remain identity-secret while changing the public legal-action
        # contract. Their own effect therefore reveals the Stratagem as it
        # becomes active. Resolution-only and self-only future effects remain
        # face-down until they are actually used.
        if (
            choice == STRAT_CHOICE_WHEEL
            or choice == STRAT_CHOICE_RESERVES
            or self.strat_next_operation_front[card]
            or self.strat_no_maneuver_away[card]
            or self.strat_first_maneuver_direction[card]
        ):
            state.stratagem_revealed[actor] = 1

        if choice == STRAT_CHOICE_WHEEL and dest >= 0:
            for source in range(actor * POSITIONS_PER_PLAYER, actor * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
                if not (extra & (<uint32_t>1 << source)):
                    continue
                local = local_slot(source)
                front = local // RANK_COUNT
                if dest == 0:
                    target = slot_index(actor, front - 1, local % RANK_COUNT)
                else:
                    target = slot_index(actor, front + 1, local % RANK_COUNT)
                _fe_move_slot(self, state, source, target)
                _fe_resolve_force_move_triggers(self, 
                    state, actor, source, target
                )
            _fe_resolve_force_pair_narratives(self, state, actor)
        elif choice == STRAT_CHOICE_RESERVES:
            for front in range(FRONT_COUNT):
                source = slot_index(actor, front, RANK_REAR)
                if extra & (<uint32_t>1 << source):
                    target = slot_index(actor, front, RANK_FRONT)
                    _fe_move_slot(self, state, source, target)
                    _fe_resolve_force_move_triggers(self, 
                        state, actor, source, target
                    )
            _fe_resolve_force_pair_narratives(self, state, actor)

        # A Stratagem is an Action and can satisfy a pre-existing
        # "next Action must affect Front X" obligation. Constraints created
        # by this Stratagem activate on the following Action and therefore
        # are deliberately not consumed here.
        _fe_consume_operation_constraints(self, state, actor, action)
        _fe_resume_pending_flow(self, state)
        return

    if kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME:
        _fe_resolve_new_completions_fast(self, state, actor, before_mask)
        _fe_first_card_front_constraint_triggers(
            self, state, actor, front_from_slot(pos)
        )

    _fe_consume_operation_constraints(self, state, actor, action)
    _fe_resume_pending_flow(self, state)

cdef FastState _fe_next_state(FastEngine self, FastState state, uint64_t action):
    cdef FastState child = state.clone_fast()
    _fe_apply_fast(self, child, action)
    return child

cdef _fe_apply(FastEngine self, FastState state, uint64_t action):
    _fe_apply_fast(self, state, action)
