cdef inline uint32_t _fe_next_shuffle_seed(FastEngine self, uint32_t seed) noexcept:
    return seed * <uint32_t>1664525 + <uint32_t>1013904223

cdef void _fe_clear_narrative_targets_at_slot(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int ix
    for ix in range(NARRATIVE_COUNT):
        if state.narrative_target_slot[ix] == slot:
            state.narrative_target_slot[ix] = -1

cdef void _fe_discard_slot_components(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int card
    if state.force[slot] >= 0:
        _fe_clear_narrative_targets_at_slot(self, state, slot)
    card = state.force[slot]
    if card >= 0:
        _fe_append_discard(self, state, player, card, False)
    card = state.bond[slot]
    if card >= 0:
        _fe_append_discard(self, state, player, card, False)
    card = state.name[slot]
    if card >= 0:
        _fe_append_discard(self, state, player, card, False)
    state.force[slot] = -1
    state.exhausted[slot] = 0
    state.bond[slot] = -1
    state.name[slot] = -1
    state.temporary[slot] = 0
    state.maneuver_count[slot] = 0
    state.maneuvered_in_operation[slot] = 0

cdef uint32_t _fe_succession_destinations(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int dest
    cdef uint32_t adjacent = _fe_adjacent_formation_mask(
        self, state, player, slot, False
    )
    cdef uint32_t mask = 0
    for dest in range(
        player * POSITIONS_PER_PLAYER,
        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
    ):
        if (
            adjacent & (1 << dest)
            and state.bond[dest] >= 0
            and state.name[dest] < 0
        ):
            mask |= <uint32_t>(1 << dest)
    return mask

cdef void _fe_finish_pending_drive_off(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    """Finish a drive-off after any replacement choice has resolved."""
    cdef int force = state.force[slot]
    cdef int bond = state.bond[slot]
    cdef int name = state.name[slot]

    if force >= 0:
        _fe_clear_narrative_targets_at_slot(self, state, slot)
        _fe_append_discard(self, state, player, force, False)

    if bond >= 0:
        if self.driven_bond_stays[bond]:
            state.force[slot] = -1
            state.exhausted[slot] = 0
            if name >= 0:
                _fe_return_to_hand(self, state, player, name)
            state.name[slot] = -1
            state.temporary[slot] = 0
            state.maneuver_count[slot] = 0
            state.maneuvered_in_operation[slot] = 0
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

    state.force[slot] = -1
    state.exhausted[slot] = 0
    state.bond[slot] = -1
    state.name[slot] = -1
    state.temporary[slot] = 0
    state.maneuver_count[slot] = 0
    state.maneuvered_in_operation[slot] = 0

cdef void _fe_drive_off_slot(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) except *:
    """Drive off one formation, pausing for an optional succession effect if legal."""
    cdef int name = state.name[slot]
    cdef uint32_t destinations
    if name >= 0 and (self.card_capabilities[name] & CAP_SUCCESSION_ON_DRIVE_OFF_NAME):
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
    cdef int controller, narrative_slot, ix, card
    for controller in range(PLAYER_COUNT):
        narrative_slot = self.ongoing_narrative_limit - 1
        while narrative_slot >= 0:
            ix = controller * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
            card = state.narrative[ix]
            if (
                card >= 0
                and self.narrative_no_maneuver_away[card]
                and state.narrative_front_mask[ix] & (1 << front)
            ):
                _fe_discard_ongoing_narrative(
                    self, state, controller, narrative_slot
                )
            narrative_slot -= 1


cdef void _fe_retreat_slot(
    FastEngine self,
    FastState state,
    int player,
    int source,
    int destination,
) except *:
    """Move a formation by Retreat and queue printed after-Retreat effects."""
    cdef int bond = state.bond[source]
    cdef int name = state.name[source]
    cdef int front = front_from_slot(destination)
    cdef int source_front = front_from_slot(source)
    cdef int rank = rank_from_slot(destination)
    cdef bint was_named = _fe_slot_complete(self, state, source)
    cdef int other, other_bond
    cdef uint32_t destinations

    # Battle-resolution drive-off effects can leave a prepared/open component
    # in the Rear immediately before the Frontline Named Formation must
    # Retreat there (for example Stayed Behind For). A Retreat moves the
    # complete source stack, so the two component sets cannot coexist.
    # Explicitly discard the prepared destination components instead of
    # letting _fe_move_slot overwrite them and violate card conservation.
    if (
        state.force[destination] < 0
        and (
            state.bond[destination] >= 0
            or state.name[destination] >= 0
        )
    ):
        _fe_discard_slot_components(self, state, player, destination)

    _fe_move_slot(self, state, source, destination)
    if was_named:
        _fe_discard_retreat_sagas(self, state, source_front)
    _fe_resolve_retreat_narratives(self, state, player, destination)

    if bond >= 0 and self.retreat_command_gain[bond] > 0:
        _fe_gain_command_fast(self,
            state,
            player,
            self.retreat_command_gain[bond],
            bond,
            COMMAND_DETAIL_RETREAT_GAIN,
        )

    if (
        name >= 0
        and (
            self.retreat_sideways_name[name]
            or (self.card_capabilities[name] & CAP_AFTER_SELF_RETREAT_SIDEWAYS_NAME)
        )
    ):
        destinations = _fe_adjacent_empty_mask(self, 
            state, player, destination
        )
        _fe_queue_move_to_mask(self, 
            state,
            player,
            <uint32_t>(1 << destination),
            destinations,
            True,
        )

    # An adjacent-retreat trigger uses orthogonal position adjacency.
    destinations = _fe_adjacent_formation_mask(
        self, state, player, destination, False
    )
    for other in range(
        player * POSITIONS_PER_PLAYER,
        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
    ):
        if not (destinations & (1 << other)):
            continue
        other_bond = state.bond[other]
        if (
            other_bond >= 0
            and (self.card_capabilities[other_bond] & CAP_ADJACENT_RETREAT_FREE_MANEUVER)
        ):
            _fe_queue_free_maneuver(
                self, state, player, <uint32_t>(1 << other),
                True, False, other_bond
            )

cdef inline bint _fe_front_has_capture_bond(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int rank, slot, bond
    for rank in range(RANK_COUNT):
        slot = slot_index(player, front, rank)
        if not _fe_slot_complete(self, state, slot):
            continue
        bond = state.bond[slot]
        if bond >= 0 and self.capture_retreating_bond[bond]:
            return True
    return False

cdef void _fe_discard_battle_stratagems(FastEngine self, FastState state) noexcept:
    cdef int player, card
    for player in range(PLAYER_COUNT):
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

cdef inline bint _fe_forced_substep_pending(
    FastState state,
) noexcept:
    """Whether search must continue through a non-optional engine substep."""
    return state.pending_len > 0 or state.cleanup_pending


cdef inline bint _fe_transition_completed_turn(
    FastEngine self,
    FastState state,
    int turn_serial_before,
    int actions_before,
    int action_kind_code,
) noexcept:
    """Whether an applied transition completed one strategic turn."""
    return (
        action_kind_code == TYPE_PASS
        or action_kind_code == TYPE_END_TURN
        or (
            state.turn_number != turn_serial_before
            and actions_before + 1 >= self.actions_per_turn
        )
    )


cdef inline int _fe_command_recovery_fast(
    FastEngine self,
    int battle,
) noexcept:
    cdef int recovery
    if battle < 1:
        return 0
    recovery = (
        self.command_recovery_start
        - self.command_recovery_decrement * (battle - 1)
    )
    return recovery if recovery > 0 else 0

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
    for p in range(PLAYER_COUNT):
        state.battle_start_hand_size[p] = state.hand_len[p]
    _fe_start_turn_fast(self, state, starter)

cdef void _fe_begin_next_battle_fast(
    FastEngine self,
    FastState state,
    int starter,
) except *:
    cdef int offset, player, slot, name
    cdef uint32_t destinations
    state.cleanup_pending = 0
    state.phase = PHASE_BATTLE
    state.pending_resume = RESUME_START_BATTLE
    state.pending_resume_player = starter

    # Resolve start-of-Battle repositioning before the first normal turn.
    for offset in range(PLAYER_COUNT):
        player = starter if offset == 0 else 1 - starter
        for slot in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
            if not _fe_slot_complete(self, state, slot):
                continue
            name = state.name[slot]
            if name < 0 or not self.battle_start_move_name[name]:
                continue
            destinations = _fe_adjacent_empty_mask(self, state, player, slot)
            _fe_queue_move_to_mask(self, 
                state,
                player,
                <uint32_t>(1 << slot),
                destinations,
                True,
            )

    if state.pending_len == 0:
        _fe_finish_start_battle(self, state, starter)
