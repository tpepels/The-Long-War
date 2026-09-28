cdef inline uint32_t _fe_next_shuffle_seed(FastEngine self, uint32_t seed) noexcept:
    return seed * <uint32_t>1664525 + <uint32_t>1013904223

cdef void _fe_clear_story_targets_at_slot(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int ix
    for ix in range(SCHEME_COUNT):
        if state.scheme_target_slot[ix] == slot:
            state.scheme_target_slot[ix] = -1

cdef void _fe_discard_slot_components(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int card
    if state.subject[slot] >= 0:
        _fe_clear_story_targets_at_slot(self, state, slot)
    card = state.subject[slot]
    if card >= 0:
        _fe_append_discard(self, state, player, card, False)
    card = state.link[slot]
    if card >= 0:
        _fe_append_discard(self, state, player, card, False)
    card = state.name[slot]
    if card >= 0:
        _fe_append_discard(self, state, player, card, False)
    state.subject[slot] = -1
    state.link[slot] = -1
    state.name[slot] = -1
    state.temporary[slot] = 0
    state.maneuver_count[slot] = 0

cdef uint16_t _fe_succession_destinations(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int front = front_from_slot(slot)
    cdef int rank = rank_from_slot(slot)
    cdef int dest
    cdef uint16_t mask = 0
    if front > 0:
        dest = slot_index(player, front - 1, rank)
        if (
            state.subject[dest] >= 0
            and state.link[dest] >= 0
            and state.name[dest] < 0
        ):
            mask |= <uint16_t>(1 << dest)
    if front < 3:
        dest = slot_index(player, front + 1, rank)
        if (
            state.subject[dest] >= 0
            and state.link[dest] >= 0
            and state.name[dest] < 0
        ):
            mask |= <uint16_t>(1 << dest)
    return mask

cdef void _fe_finish_pending_drive_off(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    """Finish a drive-off after any replacement choice has resolved."""
    cdef int force = state.subject[slot]
    cdef int bond = state.link[slot]
    cdef int name = state.name[slot]

    if force >= 0:
        _fe_clear_story_targets_at_slot(self, state, slot)
        _fe_append_discard(self, state, player, force, False)

    if bond >= 0:
        if self.driven_bond_stays[bond]:
            state.subject[slot] = -1
            if name >= 0:
                _fe_return_to_hand(self, state, player, name)
            state.name[slot] = -1
            state.temporary[slot] = 0
            state.maneuver_count[slot] = 0
            return
        if self.driven_bond_returns[bond]:
            _fe_return_to_hand(self, state, player, bond)
        else:
            _fe_append_discard(self, state, player, bond, False)

    if name >= 0:
        if self.driven_name_returns[name]:
            _fe_return_to_hand(self, state, player, name)
        else:
            _fe_append_discard(self, state, player, name, False)

    state.subject[slot] = -1
    state.link[slot] = -1
    state.name[slot] = -1
    state.temporary[slot] = 0
    state.maneuver_count[slot] = 0

cdef void _fe_drive_off_slot(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) except *:
    """Drive off one formation, pausing for Eira's succession if legal."""
    cdef int name = state.name[slot]
    cdef uint16_t destinations
    if name >= 0 and self.succession_name[name]:
        destinations = _fe_succession_destinations(self, state, player, slot)
        if destinations:
            _fe_enqueue_effect(self, 
                state,
                EFFECT_SUCCESSION,
                player,
                -1,
                slot,
                -1,
                0,
                destinations,
                EFFECT_OPTIONAL,
            )
            return
    _fe_finish_pending_drive_off(self, state, player, slot)

cdef void _fe_discard_retreat_sagas(
    FastEngine self,
    FastState state,
    int front,
) noexcept:
    cdef int controller, story_slot, ix, card
    for controller in range(2):
        story_slot = self.ongoing_story_limit - 1
        while story_slot >= 0:
            ix = controller * 4 + story_slot
            card = state.scheme[ix]
            if (
                card >= 0
                and self.narrative_no_maneuver_away[card]
                and state.scheme_front_mask[ix] & (1 << front)
            ):
                _fe_discard_ongoing_narrative(
                    self, state, controller, story_slot
                )
            story_slot -= 1


cdef void _fe_retreat_slot(
    FastEngine self,
    FastState state,
    int player,
    int source,
    int destination,
) except *:
    """Move a formation by Retreat and queue printed after-Retreat effects."""
    cdef int bond = state.link[source]
    cdef int name = state.name[source]
    cdef int front = front_from_slot(destination)
    cdef int source_front = front_from_slot(source)
    cdef int rank = rank_from_slot(destination)
    cdef bint was_named = _fe_slot_complete(self, state, source)
    cdef int other, other_bond
    cdef uint16_t destinations

    _fe_move_slot(self, state, source, destination)
    if was_named:
        _fe_discard_retreat_sagas(self, state, source_front)
    _fe_resolve_retreat_narratives(self, state, player, destination)

    if bond >= 0 and self.retreat_command_gain[bond] > 0:
        _fe_gain_command_fast(self, 
            state,
            player,
            self.retreat_command_gain[bond],
        )

    if (
        name >= 0
        and (
            self.retreat_sideways_name[name]
            or self.neris_retreat_name[name]
        )
    ):
        destinations = _fe_adjacent_empty_mask(self, 
            state, player, destination
        )
        _fe_queue_move_to_mask(self, 
            state,
            player,
            <uint16_t>(1 << destination),
            destinations,
            True,
        )

    # Covered the Withdrawal of triggers from an adjacent formation in
    # the same Rear rank after the Retreat has resolved.
    if front > 0:
        other = slot_index(player, front - 1, rank)
        other_bond = state.link[other]
        if (
            state.subject[other] >= 0
            and other_bond >= 0
            and self.covered_withdrawal_bond[other_bond]
        ):
            _fe_queue_free_maneuver(self, 
                state, player, <uint16_t>(1 << other), True
            )
    if front < 3:
        other = slot_index(player, front + 1, rank)
        other_bond = state.link[other]
        if (
            state.subject[other] >= 0
            and other_bond >= 0
            and self.covered_withdrawal_bond[other_bond]
        ):
            _fe_queue_free_maneuver(self, 
                state, player, <uint16_t>(1 << other), True
            )

cdef inline bint _fe_front_has_capture_bond(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int rank, slot, bond
    for rank in range(2):
        slot = slot_index(player, front, rank)
        if not _fe_slot_complete(self, state, slot):
            continue
        bond = state.link[slot]
        if bond >= 0 and self.capture_retreating_bond[bond]:
            return True
    return False

cdef void _fe_discard_incomplete_formations(FastEngine self, FastState state) noexcept:
    cdef int player, slot
    for player in range(2):
        for slot in range(player * 8, player * 8 + 8):
            if (
                state.subject[slot] >= 0
                or state.link[slot] >= 0
                or state.name[slot] >= 0
            ) and not _fe_slot_complete(self, state, slot):
                _fe_discard_slot_components(self, state, player, slot)

cdef void _fe_discard_battle_stratagems(FastEngine self, FastState state) noexcept:
    cdef int player, card
    for player in range(2):
        card = state.stratagem[player]
        if card >= 0:
            _fe_append_discard(self, state, player, card, False)
        state.stratagem[player] = -1
        state.stratagem_revealed[player] = 0
        state.stratagem_front_mask[player] = 0
        state.stratagem_direction[player] = 0
        state.stratagem_target_mask[player] = 0

cdef inline void _fe_clear_battle_temporary_strength(
    FastEngine self,
    FastState state,
) noexcept:
    cdef int slot
    for slot in range(SLOT_COUNT):
        state.temporary[slot] = 0

cdef inline int _fe_command_recovery_fast(
    FastEngine self,
    int battle,
) noexcept:
    cdef int index = battle - 1
    if index < 0:
        return 0
    if index >= self.command_recovery_len:
        return self.command_recovery_tail
    return self.command_recovery_values[index]

cdef int _fe_command_recovery_for_battle(
    FastEngine self,
    int battle,
):
    return _fe_command_recovery_fast(self, battle)

cdef void _fe_finish_start_battle(
    FastEngine self,
    FastState state,
    int starter,
) noexcept:
    cdef int p
    state.pending_resume = RESUME_NONE
    state.pending_resume_player = -1
    state.cleanup_pending = 0
    state.phase = PHASE_BATTLE
    for p in range(2):
        state.battle_start_hand_size[p] = state.hand_len[p]
    _fe_start_turn_fast(self, state, starter)

cdef void _fe_begin_next_battle_fast(
    FastEngine self,
    FastState state,
    int starter,
) except *:
    cdef int offset, player, slot, name
    cdef uint16_t destinations
    state.cleanup_pending = 0
    state.phase = PHASE_BATTLE
    state.pending_resume = RESUME_START_BATTLE
    state.pending_resume_player = starter

    # Resolve start-of-Battle repositioning before the first normal turn.
    for offset in range(2):
        player = starter if offset == 0 else 1 - starter
        for slot in range(player * 8, player * 8 + 8):
            if not _fe_slot_complete(self, state, slot):
                continue
            name = state.name[slot]
            if name < 0 or not self.battle_start_move_name[name]:
                continue
            destinations = _fe_adjacent_empty_mask(self, state, player, slot)
            _fe_queue_move_to_mask(self, 
                state,
                player,
                <uint16_t>(1 << slot),
                destinations,
                True,
            )

    if state.pending_len == 0:
        _fe_finish_start_battle(self, state, starter)
