cdef uint16_t _fe_asha_mask_for_suppression(
    FastEngine self,
    FastState state,
    int defender,
    int front,
    int original_target,
) noexcept:
    cdef int rank, slot, name
    cdef uint16_t mask = 0
    for rank in range(2):
        slot = slot_index(defender, front, rank)
        if slot == original_target or not self.slot_complete(state, slot):
            continue
        name = state.name[slot]
        if name >= 0 and self.intercept_name[name]:
            mask |= <uint16_t>(1 << slot)
    return mask

cdef void _fe_suppress_with_interception(
    FastEngine self,
    FastState state,
    int controller,
    int target,
) except *:
    cdef int defender = owner_from_slot(target)
    cdef int front = front_from_slot(target)
    cdef uint16_t interceptors = self.asha_mask_for_suppression(
        state, defender, front, target
    )
    if interceptors:
        self.enqueue_effect(
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
        state.resolution_suppressed_mask |= <uint16_t>(1 << target)

cdef void _fe_apply_pending_effect(FastEngine self, FastState state, uint64_t action) except *:
    cdef int kind = state.pending_kind[0]
    cdef int player = state.pending_player[0]
    cdef int card = action_card(action)
    cdef int source = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int trigger_source = state.pending_source[0]
    cdef int aux = state.pending_aux[0]
    cdef bint skip = card < 0 and source < 0 and dest < 0
    cdef bint was_empty
    cdef int before_mask, moved

    self.pop_pending_effect(state)

    if kind == EFFECT_FREE_MANEUVER:
        if not skip:
            was_empty = state.subject[dest] < 0
            self.swap_slots(state, source, dest)
            state.maneuver_count[dest] += 1
            if state.free_maneuver_available[player]:
                state.free_maneuver_available[player] = 0
            self.resolve_maneuver_triggers(
                state, player, source, dest, was_empty
            )
    elif kind == EFFECT_MOVE:
        if not skip:
            self.move_slot(state, source, dest)
            self.resolve_force_move_triggers(state, player, source, dest)
    elif kind == EFFECT_SWAP:
        if not skip:
            self.swap_slots(state, source, dest)
            self.resolve_force_move_triggers(state, player, source, dest)
            self.resolve_force_move_triggers(state, player, dest, source)
    elif kind == EFFECT_RECOVER:
        if not skip and card >= 0 and self.remove_from_discard(state, player, card):
            self.return_to_hand(state, player, card)
    elif kind == EFFECT_FRONT_CONTRIBUTION:
        if not skip and source >= 0 and dest >= 0:
            state.resolution_contribution_front[source] = dest
    elif kind == EFFECT_SUPPRESS:
        if not skip and dest >= 0:
            self.suppress_with_interception(state, player, dest)
    elif kind == EFFECT_SACRIFICE:
        if not skip and source >= 0 and dest >= 0:
            self.discard_slot_components(state, player, source)
            self.suppress_with_interception(state, player, dest)
    elif kind == EFFECT_INTERCEPT:
        if skip:
            if aux >= 0:
                state.resolution_suppressed_mask |= <uint16_t>(1 << aux)
        elif source >= 0:
            state.resolution_suppressed_mask |= <uint16_t>(1 << source)
    elif kind == EFFECT_RETREAT:
        if not skip and source >= 0 and dest >= 0:
            self.retreat_slot(state, player, source, dest)
    elif kind == EFFECT_PROTECT_RETREAT:
        if source < 0:
            source = trigger_source
        if source >= 0:
            state.resolution_protected_mask[player] |= <uint8_t>(
                1 << (front_from_slot(source) + 4)
            )
        if not skip and source >= 0:
            state.resolution_protected_mask[player] |= <uint8_t>(
                1 << front_from_slot(source)
            )
            self.drive_off_slot(state, player, source)
    elif kind == EFFECT_TRANSFER_COMPONENT:
        if not skip and source >= 0 and dest >= 0 and card >= 0:
            before_mask = self.complete_mask(state, player)
            if state.link[source] == card and state.link[dest] < 0:
                state.link[source] = -1
                state.link[dest] = card
            elif state.name[source] == card and state.name[dest] < 0:
                state.name[source] = -1
                state.name[dest] = card
            self.resolve_new_completions_fast(state, player, before_mask)
    elif kind == EFFECT_SUCCESSION:
        if not skip and trigger_source >= 0 and dest >= 0:
            moved = state.name[trigger_source]
            if moved >= 0:
                before_mask = self.complete_mask(state, player)
                state.name[trigger_source] = -1
                state.name[dest] = moved
                self.resolve_new_completions_fast(state, player, before_mask)
        self.finish_pending_drive_off(state, player, trigger_source)

    self.resume_pending_flow(state)

cdef void _fe_queue_veyra_force_on_play(
    FastEngine self,
    FastState state,
    int player,
    int destination,
) except *:
    cdef int front = front_from_slot(destination)
    cdef int rank = rank_from_slot(destination)
    cdef int source
    cdef uint16_t sources = 0
    if front > 0:
        source = slot_index(player, front - 1, rank)
        if state.subject[source] < 0 and (
            (state.link[source] >= 0 and state.link[destination] < 0)
            or (state.name[source] >= 0 and state.name[destination] < 0)
        ):
            sources |= <uint16_t>(1 << source)
    if front < 3:
        source = slot_index(player, front + 1, rank)
        if state.subject[source] < 0 and (
            (state.link[source] >= 0 and state.link[destination] < 0)
            or (state.name[source] >= 0 and state.name[destination] < 0)
        ):
            sources |= <uint16_t>(1 << source)
    if sources:
        self.enqueue_effect(
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

cdef void _fe_queue_veyra_name_on_play(
    FastEngine self,
    FastState state,
    int player,
    int destination,
) except *:
    cdef int front = front_from_slot(destination)
    cdef int rank = rank_from_slot(destination)
    cdef int source
    cdef uint16_t sources = 0
    if state.subject[destination] < 0 or state.link[destination] >= 0:
        return
    if front > 0:
        source = slot_index(player, front - 1, rank)
        if (
            state.subject[source] >= 0
            and state.link[source] >= 0
            and state.name[source] < 0
        ):
            sources |= <uint16_t>(1 << source)
    if front < 3:
        source = slot_index(player, front + 1, rank)
        if (
            state.subject[source] >= 0
            and state.link[source] >= 0
            and state.name[source] < 0
        ):
            sources |= <uint16_t>(1 << source)
    if sources:
        self.enqueue_effect(
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

cdef void _fe_apply_fast(FastEngine self, FastState state, uint64_t action):
    cdef int kind = action_kind(action)
    cdef int card = action_card(action)
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int actor = state.active_player
    cdef int front, before_mask = 0, cost = 0, source, target, local, choice
    cdef uint32_t extra = action_extra(action)
    cdef bint cancelled, prepared_before, veyra_name_ready

    if kind == TYPE_PASS:
        self.pass_action(state, actor)
        return

    if kind == TYPE_EFFECT:
        self.apply_pending_effect(state, action)
        return

    if kind == TYPE_DISCARD:
        if not state.cleanup_pending:
            raise ValueError("Discard is only legal before a mandatory draw")
        self.take_from_hand(state, actor, card, 0)
        self.append_discard(state, actor, card, False)
        state.cleanup_pending = 0
        if state.pending_draw_count > 0:
            state.pending_draw_count -= 1
        self.draw_for_battle(state, actor, 1)
        if state.pending_draw_count > 0:
            self.queue_battle_draws(
                state,
                actor,
                state.pending_draw_count,
            )
            if state.cleanup_pending:
                return
        if not state.cleanup_pending:
            self.resume_pending_flow(state)
        return

    state.pending_resume = RESUME_FINISH_OPERATION
    state.pending_resume_player = actor
    cost = self.command_cost_fast(state, action)
    self.spend_command_fast(state, actor, cost)

    if kind == TYPE_MANEUVER:
        target = 1 if state.subject[dest] < 0 else 0
        self.swap_slots(state, pos, dest)
        state.maneuver_count[dest] += 1
        if state.free_maneuver_available[actor]:
            state.free_maneuver_available[actor] = 0
        self.resolve_force_pair_narratives(state, actor)
        self.resolve_maneuver_triggers(state, actor, pos, dest, bool(target))
        self.resume_pending_flow(state)
        return

    if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
        before_mask = self.complete_mask(state, actor)
        front = front_from_slot(pos)
        state.cards_played_this_turn_front_mask[actor] |= 1 << front
        state.cards_played_this_battle_front_mask[actor] |= 1 << front
    if (kind == TYPE_SUBJECT or kind == TYPE_NAME) and card >= 0 and self.hero[card]:
        state.hero_used[actor] = 1

    if kind == TYPE_SUBJECT:
        prepared_before = state.link[pos] >= 0 or state.name[pos] >= 0
        self.take_from_hand(state, actor, card, 0)
        state.subject[pos] = card
        if self.late_banner_force[card] and prepared_before:
            self.queue_free_maneuver(
                state, actor, <uint16_t>(1 << pos), True, True
            )
        if self.veyra_force[card]:
            self.queue_veyra_force_on_play(state, actor, pos)
        self.resolve_force_pair_narratives(state, actor)
        front = front_from_slot(pos)
        self.resolve_scheme_event(state, actor, EVENT_SUBJECT, front, pos)
        self.resolve_strat_event(state, EVENT_SUBJECT, actor, card, pos)

    elif kind == TYPE_LINK:
        self.take_from_hand(state, actor, card, 0)
        state.link[pos] = card
        if state.subject[pos] >= 0:
            state.temporary[pos] += self.on_link_bonus[state.subject[pos]]
        if dest >= 0:
            source = pos
            self.move_slot(state, source, dest)
            pos = dest
            self.resolve_force_move_triggers(state, actor, source, dest)
            self.resolve_force_pair_narratives(state, actor)
        if extra and self.bond_optional_draw_count[card] > 0:
            self.queue_battle_draws(
                state,
                actor,
                self.bond_optional_draw_count[card],
            )
        front = front_from_slot(pos)
        self.resolve_scheme_event(state, actor, EVENT_LINK, front, pos)

    elif kind == TYPE_NAME:
        veyra_name_ready = (
            self.veyra_name[card]
            and state.subject[pos] >= 0
            and state.link[pos] < 0
        )
        self.take_from_hand(state, actor, card, 0)
        state.name[pos] = card
        if veyra_name_ready:
            self.queue_veyra_name_on_play(state, actor, pos)
        if self.name_effect[card] == NAME_REVEAL_SCHEME:
            front = front_from_slot(pos)
            if state.scheme[(1 - actor) * 4 + front] >= 0:
                state.scheme_revealed[(1 - actor) * 4 + front] = 1
        elif self.name_effect[card] == NAME_MOVE_ADJACENT and dest >= 0:
            source = pos
            self.move_slot(state, source, dest)
            pos = dest
            self.resolve_force_move_triggers(state, actor, source, dest)
        self.resolve_strat_event(state, EVENT_NAME, actor, card, pos)

    elif kind == TYPE_PLOT:
        self.take_from_hand(state, actor, card, 0)
        state.narratives_played_this_battle[actor] += 1
        if extra and self.story_discard_count[card] == 1:
            target = <int>extra - 1
            if target >= 0 and state.hand[actor][target] > 0:
                self.take_from_hand(state, actor, target, 0)
                self.append_discard(state, actor, target, True)
                self.gain_command_fast(
                    state,
                    actor,
                    self.story_discard_gain_command[card],
                )
        cancelled = self.pre_story_cancel(state, actor)
        if not cancelled:
            self.resolve_plot(state, actor, card, pos, dest)
            self.resolve_plot_target_scheme(state, actor, pos)
        self.append_discard(state, actor, card, True)

    elif kind == TYPE_SCHEME:
        self.take_from_hand(state, actor, card, 0)
        state.narratives_played_this_battle[actor] += 1
        state.scheme[actor * 4 + pos] = card
        state.scheme_revealed[actor * 4 + pos] = 1
        state.scheme_front_mask[actor * 4 + pos] = <uint8_t>(extra & 15)
        state.scheme_target_slot[actor * 4 + pos] = dest

    elif kind == TYPE_STRATAGEM:
        self.take_from_hand(state, actor, card, 0)
        state.stratagem[actor] = card
        state.stratagem_revealed[actor] = 1
        state.stratagem_front_mask[actor] = (
            <uint8_t>pos if pos >= 0 else 0
        )
        state.stratagem_direction[actor] = (
            <uint8_t>(dest + 1) if dest >= 0 else 0
        )
        state.stratagem_target_mask[actor] = <uint16_t>(extra & 0xFFFF)
        state.stratagem_used[actor] = 1

        choice = self.strat_choice_kind[card]
        if choice == STRAT_CHOICE_WHEEL and dest >= 0:
            for source in range(actor * 8, actor * 8 + 8):
                if not (extra & (<uint32_t>1 << source)):
                    continue
                local = local_slot(source)
                front = local >> 1
                if dest == 0:
                    target = slot_index(actor, front - 1, local & 1)
                else:
                    target = slot_index(actor, front + 1, local & 1)
                self.move_slot(state, source, target)
                self.resolve_force_move_triggers(
                    state, actor, source, target
                )
            self.resolve_force_pair_narratives(state, actor)
        elif choice == STRAT_CHOICE_RESERVES:
            for front in range(4):
                source = slot_index(actor, front, 1)
                if extra & (<uint32_t>1 << source):
                    target = slot_index(actor, front, 0)
                    self.move_slot(state, source, target)
                    self.resolve_force_move_triggers(
                        state, actor, source, target
                    )
            self.resolve_force_pair_narratives(state, actor)

        self.resume_pending_flow(state)
        return

    if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
        self.resolve_new_completions_fast(state, actor, before_mask)

    self.resume_pending_flow(state)

cdef FastState _fe_next_state(FastEngine self, FastState state, uint64_t action):
    cdef FastState child = state.clone_fast()
    self.apply_fast(child, action)
    return child

cdef _fe_apply(FastEngine self, FastState state, uint64_t action):
    self.apply_fast(state, action)
