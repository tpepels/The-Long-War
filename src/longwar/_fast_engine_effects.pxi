cdef inline void _fe_append_discard(FastEngine self, FastState state, int player, int card, bint battle_count=True) noexcept:
    state.discard[player][state.discard_len[player]] = card
    state.discard_len[player] += 1
    if battle_count:
        state.discarded_this_battle[player] += 1

cdef inline void _fe_return_to_hand(FastEngine self, FastState state, int player, int card) noexcept:
    state.hand[player][card] += 1
    state.hand_len[player] += 1
    state.known_hidden[1 - player][player][card] += 1

cdef bint _fe_remove_from_discard(
    FastEngine self,
    FastState state,
    int player,
    int card,
) noexcept:
    cdef int i, j
    for i in range(state.discard_len[player] - 1, -1, -1):
        if state.discard[player][i] != card:
            continue
        for j in range(i, state.discard_len[player] - 1):
            state.discard[player][j] = state.discard[player][j + 1]
        state.discard_len[player] -= 1
        return True
    return False

cdef inline void _fe_take_from_hand(FastEngine self, FastState state, int player, int card, int hidden_kind) noexcept:
    cdef int viewer = 1 - player
    cdef int known
    if hidden_kind == 0:
        if state.known_hidden[viewer][player][card] > 0:
            state.known_hidden[viewer][player][card] -= 1
    else:
        for known in range(self.n_cards):
            if state.known_hidden[viewer][player][known] == 0:
                continue
            if hidden_kind == 1:
                if self.card_type[known] == CARD_NARRATIVE and self.ongoing_narrative[known]:
                    state.known_hidden[viewer][player][known] -= 1
            elif hidden_kind == 2:
                if self.card_type[known] == CARD_STRATAGEM:
                    state.known_hidden[viewer][player][known] -= 1
    state.hand[player][card] -= 1
    state.hand_len[player] -= 1

cdef inline bint _fe_front_has_force(FastEngine self, FastState state, int player, int front) noexcept:
    return state.force[slot_index(player, front, 0)] >= 0 or state.force[slot_index(player, front, 1)] >= 0

cdef inline int _fe_preferred_slot(FastEngine self, FastState state, int player, int front) noexcept:
    cdef int slot = slot_index(player, front, 0)
    if state.force[slot] >= 0:
        return slot
    slot = slot_index(player, front, 1)
    return slot if state.force[slot] >= 0 else -1

cdef void _fe_remove_bond(FastEngine self, FastState state, int player, int slot):
    cdef int bond = state.bond[slot]
    cdef int name = state.name[slot]
    state.bond[slot] = -1
    state.name[slot] = -1
    if bond >= 0:
        _fe_append_discard(self, state, player, bond, True)
    if name >= 0:
        _fe_return_to_hand(self, state, player, name)

cdef inline void _fe_return_bond_to_hand_from_slot(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    """Return only the Bond; Force and Name remain in place."""
    cdef int bond = state.bond[slot]
    if bond < 0:
        return
    state.bond[slot] = -1
    _fe_return_to_hand(self, state, player, bond)

cdef void _fe_compact_ongoing_narratives(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    """Keep packed Narrative storage aligned with GameState's compact list."""
    cdef int read_slot, write_slot, src, dst
    write_slot = 0
    for read_slot in range(self.ongoing_narrative_limit):
        src = player * NARRATIVE_SLOTS_PER_PLAYER + read_slot
        if state.narrative[src] < 0:
            continue
        if read_slot != write_slot:
            dst = player * NARRATIVE_SLOTS_PER_PLAYER + write_slot
            state.narrative[dst] = state.narrative[src]
            state.narrative_revealed[dst] = state.narrative_revealed[src]
            state.narrative_front_mask[dst] = state.narrative_front_mask[src]
            state.narrative_target_slot[dst] = state.narrative_target_slot[src]
            state.narrative_used[dst] = state.narrative_used[src]
            state.narrative_direction[dst] = state.narrative_direction[src]
            state.narrative_trigger_mask[dst] = state.narrative_trigger_mask[src]
            state.narrative[src] = -1
            state.narrative_revealed[src] = 0
            state.narrative_front_mask[src] = 0
            state.narrative_target_slot[src] = -1
            state.narrative_used[src] = 0
            state.narrative_direction[src] = DIRECTION_NONE
            state.narrative_trigger_mask[src] = 0
        write_slot += 1

cdef void _fe_reveal_ongoing_narrative(FastEngine self, FastState state, int controller, int front, int actor, int trigger_slot=-1):
    cdef int ix = controller * NARRATIVE_SLOTS_PER_PLAYER + front
    cdef int card = state.narrative[ix]
    cdef int effect, amount, target
    if card < 0:
        return
    state.narrative_revealed[ix] = 1
    effect = self.ongoing_reveal_effect[card]
    amount = self.ongoing_reveal_amount[card]
    if effect == ONGOING_EFFECT_PENALIZE_FORCE and trigger_slot >= 0 and state.force[trigger_slot] >= 0:
        state.temporary[trigger_slot] -= amount
    elif effect == ONGOING_EFFECT_DISCARD_BOND and trigger_slot >= 0 and state.bond[trigger_slot] >= 0:
        _fe_remove_bond(self, state, actor, trigger_slot)
    elif effect == ONGOING_EFFECT_REINFORCE:
        target = _fe_preferred_slot(self, state, controller, front)
        if target >= 0:
            state.temporary[target] += amount
    state.narrative[ix] = -1
    state.narrative_revealed[ix] = 0
    state.narrative_front_mask[ix] = 0
    state.narrative_target_slot[ix] = -1
    _fe_compact_ongoing_narratives(self, state, controller)
    _fe_append_discard(self, state, controller, card, True)

cdef void _fe_resolve_ongoing_narrative_event(FastEngine self, FastState state, int actor, int event, int front, int trigger_slot=-1):
    cdef int controller, ix, card
    for controller in (actor, 1 - actor):
        ix = controller * NARRATIVE_SLOTS_PER_PLAYER + front
        card = state.narrative[ix]
        if card < 0:
            continue
        if self.ongoing_reveal_trigger[card] != event or actor == controller:
            continue
        if self.ongoing_reveal_requires_force[card] and not _fe_front_has_force(self, state, controller, front):
            continue
        _fe_reveal_ongoing_narrative(self, state, controller, front, actor, trigger_slot)

cdef bint _fe_strat_trigger_matches(FastEngine self, FastState state, int controller, int card, int event, int actor, int played_card=-1, int pos=-1) noexcept:
    cdef int role, rank, scope
    if self.strat_trigger_event[card] != event:
        return False
    scope = self.strat_actor[card]
    if scope == ACTOR_OPPONENT and actor == controller:
        return False
    if scope == ACTOR_CONTROLLER and actor != controller:
        return False
    if self.strat_role_mask[card]:
        if played_card < 0:
            return False
        role = self.role[played_card]
        if not (self.strat_role_mask[card] & (1 << role)):
            return False
    if self.strat_rank_mask[card]:
        if pos < 0:
            return False
        rank = rank_from_slot(pos)
        if not (self.strat_rank_mask[card] & (1 << rank)):
            return False
    return True

cdef void _fe_resolve_strat_event(FastEngine self, FastState state, int event, int actor, int played_card=-1, int pos=-1):
    cdef int controller, card
    for controller in (actor, 1 - actor):
        card = state.stratagem[controller]
        if card < 0 or state.stratagem_revealed[controller]:
            continue
        if not _fe_strat_trigger_matches(self, state, controller, card, event, actor, played_card, pos):
            continue
        state.stratagem_revealed[controller] = 1
        if self.strat_reveal_effect[card] == STRAT_REVEAL_PENALIZE and pos >= 0 and state.force[pos] >= 0:
            state.temporary[pos] -= self.strat_reveal_amount[card]

cdef bint _fe_pre_narrative_cancel(FastEngine self, FastState state, int actor):
    cdef int controller = 1 - actor
    cdef int card = state.stratagem[controller]
    if card < 0 or state.stratagem_revealed[controller]:
        return False
    if not _fe_strat_trigger_matches(self, state, controller, card, EVENT_IMMEDIATE_NARRATIVE, actor):
        return False
    state.stratagem_revealed[controller] = 1
    return self.strat_cancel_narrative[card]

cdef void _fe_move_slot(FastEngine self, FastState state, int source, int dest) noexcept:
    cdef int ix
    for ix in range(NARRATIVE_COUNT):
        if state.narrative_target_slot[ix] == source:
            state.narrative_target_slot[ix] = dest
    for ix in range(state.constraint_len):
        if state.constraint_source_slot[ix] == source:
            state.constraint_source_slot[ix] = dest
    state.force[dest] = state.force[source]
    state.bond[dest] = state.bond[source]
    state.name[dest] = state.name[source]
    state.temporary[dest] = state.temporary[source]
    state.maneuver_count[dest] = state.maneuver_count[source]
    state.maneuvered_in_operation[dest] = state.maneuvered_in_operation[source]
    state.maneuver_direction[dest] = state.maneuver_direction[source]
    state.force[source] = -1
    state.bond[source] = -1
    state.name[source] = -1
    state.temporary[source] = 0
    state.maneuver_count[source] = 0
    state.maneuvered_in_operation[source] = 0
    state.maneuver_direction[source] = DIRECTION_NONE

cdef void _fe_swap_slots(FastEngine self, FastState state, int a, int b) noexcept:
    cdef int ix
    for ix in range(NARRATIVE_COUNT):
        if state.narrative_target_slot[ix] == a:
            state.narrative_target_slot[ix] = b
        elif state.narrative_target_slot[ix] == b:
            state.narrative_target_slot[ix] = a
    for ix in range(state.constraint_len):
        if state.constraint_source_slot[ix] == a:
            state.constraint_source_slot[ix] = b
        elif state.constraint_source_slot[ix] == b:
            state.constraint_source_slot[ix] = a
    cdef int8_t force = state.force[a]
    cdef int8_t bond = state.bond[a]
    cdef int8_t name = state.name[a]
    cdef int16_t temporary = state.temporary[a]
    cdef uint8_t maneuvers = state.maneuver_count[a]
    cdef uint8_t maneuvered_in_operation = state.maneuvered_in_operation[a]
    cdef int8_t maneuver_direction = state.maneuver_direction[a]
    state.force[a] = state.force[b]
    state.bond[a] = state.bond[b]
    state.name[a] = state.name[b]
    state.temporary[a] = state.temporary[b]
    state.maneuver_count[a] = state.maneuver_count[b]
    state.maneuvered_in_operation[a] = state.maneuvered_in_operation[b]
    state.maneuver_direction[a] = state.maneuver_direction[b]
    state.force[b] = force
    state.bond[b] = bond
    state.name[b] = name
    state.temporary[b] = temporary
    state.maneuver_count[b] = maneuvers
    state.maneuvered_in_operation[b] = maneuvered_in_operation
    state.maneuver_direction[b] = maneuver_direction

cdef void _fe_resolve_narrative(FastEngine self, FastState state, int actor, int card, int pos, int dest):
    cdef int effect = self.narrative_play_effect[card]
    cdef int owner
    if effect == NARRATIVE_DISCREDIT:
        owner = owner_from_slot(pos)
        if state.bond[pos] >= 0:
            _fe_remove_bond(self, state, owner, pos)
        elif state.force[pos] >= 0:
            state.temporary[pos] -= 2
    elif effect == NARRATIVE_RETURN_NAME:
        owner = owner_from_slot(pos)
        if state.name[pos] >= 0:
            card = state.name[pos]
            state.name[pos] = -1
            _fe_return_to_hand(self, state, owner, card)
        elif state.force[pos] >= 0:
            state.temporary[pos] -= 2
    elif effect == NARRATIVE_MOVE_FORCE:
        _fe_move_slot(self, state, pos, dest)
        _fe_resolve_force_move_triggers(self, state, actor, pos, dest)

cdef void _fe_discard_ongoing_narrative(
    FastEngine self,
    FastState state,
    int controller,
    int narrative_slot,
) noexcept:
    cdef int ix = controller * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
    cdef int card = state.narrative[ix]
    if card < 0:
        return
    state.narrative[ix] = -1
    state.narrative_revealed[ix] = 0
    state.narrative_front_mask[ix] = 0
    state.narrative_target_slot[ix] = -1
    state.narrative_used[ix] = 0
    state.narrative_direction[ix] = DIRECTION_NONE
    state.narrative_trigger_mask[ix] = 0
    _fe_compact_ongoing_narratives(self, state, controller)
    _fe_append_discard(self, state, controller, card, True)

cdef uint16_t _fe_named_formation_mask(
    FastEngine self,
    FastState state,
    int player,
    int exclude=-1,
) noexcept:
    cdef int slot
    cdef uint16_t mask = 0
    for slot in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
        if slot != exclude and _fe_slot_complete(self, state, slot):
            mask |= <uint16_t>(1 << slot)
    return mask

cdef uint16_t _fe_adjacent_formation_mask(
    FastEngine self,
    FastState state,
    int player,
    int slot,
    bint named_only=False,
) noexcept:
    cdef int front = front_from_slot(slot)
    cdef int rank = rank_from_slot(slot)
    cdef int other
    cdef uint16_t mask = 0
    if front > 0:
        other = slot_index(player, front - 1, rank)
        if state.force[other] >= 0 and (not named_only or _fe_slot_complete(self, state, other)):
            mask |= <uint16_t>(1 << other)
    if front < 3:
        other = slot_index(player, front + 1, rank)
        if state.force[other] >= 0 and (not named_only or _fe_slot_complete(self, state, other)):
            mask |= <uint16_t>(1 << other)
    return mask

cdef uint16_t _fe_adjacent_empty_mask(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int front = front_from_slot(slot)
    cdef int rank = rank_from_slot(slot)
    cdef int other
    cdef uint16_t mask = 0
    if front > 0:
        other = slot_index(player, front - 1, rank)
        if _fe_slot_is_empty(self, state, other):
            mask |= <uint16_t>(1 << other)
    if front < 3:
        other = slot_index(player, front + 1, rank)
        if _fe_slot_is_empty(self, state, other):
            mask |= <uint16_t>(1 << other)
    return mask

cdef bint _fe_force_in_all_fronts(FastEngine self, FastState state, int player) noexcept:
    cdef int front
    for front in range(FRONT_COUNT):
        if (
            state.force[slot_index(player, front, 0)] < 0
            and state.force[slot_index(player, front, 1)] < 0
        ):
            return False
    return True

cdef bint _fe_discard_has_type(
    FastEngine self,
    FastState state,
    int player,
    int card_type,
) noexcept:
    cdef int i, card
    for i in range(state.discard_len[player]):
        card = state.discard[player][i]
        if self.card_type[card] == card_type:
            return True
    return False

cdef void _fe_queue_recover_from_discard(
    FastEngine self,
    FastState state,
    int player,
    int card_type,
    bint optional=False,
) except *:
    if not _fe_discard_has_type(self, state, player, card_type):
        return
    _fe_enqueue_effect(self, 
        state,
        EFFECT_RECOVER,
        player,
        -1,
        -1,
        card_type,
        0,
        0,
        EFFECT_OPTIONAL if optional else 0,
    )

cdef void _fe_queue_free_maneuver(
    FastEngine self,
    FastState state,
    int player,
    uint16_t source_mask,
    bint optional=True,
    bint allow_unnamed=False,
    int source_card=-1,
) except *:
    cdef int flags = EFFECT_OPTIONAL if optional else 0
    if source_mask == 0:
        return
    if allow_unnamed:
        flags |= EFFECT_ALLOW_UNNAMED
    _fe_enqueue_effect(self, 
        state,
        EFFECT_FREE_MANEUVER,
        player,
        -1,
        -1,
        -1,
        source_mask,
        0,
        flags,
        source_card,
    )

cdef void _fe_queue_move_to_mask(
    FastEngine self,
    FastState state,
    int player,
    uint16_t source_mask,
    uint16_t dest_mask,
    bint optional=True,
) except *:
    if source_mask == 0 or dest_mask == 0:
        return
    _fe_enqueue_effect(self, 
        state,
        EFFECT_MOVE,
        player,
        -1,
        -1,
        -1,
        source_mask,
        dest_mask,
        (EFFECT_OPTIONAL if optional else 0) | EFFECT_CARD_MOVE,
    )

cdef void _fe_gain_command_from_narrative(
    FastEngine self,
    FastState state,
    int player,
    int source_card,
    int amount,
) except *:
    cdef int front, slot, force
    cdef uint16_t named
    if amount <= 0:
        return
    _fe_gain_command_fast(
        self, state, player, amount, source_card, COMMAND_DETAIL_NARRATIVE_GAIN
    )
    named = _fe_named_formation_mask(self, state, player)
    if named == 0:
        return
    for front in range(FRONT_COUNT):
        slot = slot_index(player, front, 1)
        force = state.force[slot]
        if force >= 0 and (self.card_capabilities[force] & CAP_NARRATIVE_COMMAND_GAIN_FREE_MANEUVER_FORCE):
            _fe_queue_free_maneuver(
                self, state, player, named, True, False, force
            )

cdef void _fe_resolve_named_narratives(
    FastEngine self,
    FastState state,
    int named_player,
    int named_slot,
) except *:
    cdef int controller, narrative_slot, ix, card, trigger, amount, secondary
    cdef uint16_t sources
    for controller in range(PLAYER_COUNT):
        narrative_slot = self.ongoing_narrative_limit - 1
        while narrative_slot >= 0:
            ix = controller * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
            card = state.narrative[ix]
            if card >= 0:
                trigger = self.narrative_trigger[card]
                if (
                    (controller == named_player and trigger == NARR_TRIGGER_FRIENDLY_NAMED)
                    or (
                        controller != named_player
                        and trigger == NARR_TRIGGER_OPPONENT_NAMED
                    )
                ):
                    amount = self.narrative_trigger_gain[card]
                    if amount:
                        _fe_gain_command_from_narrative(self, state, controller, card, amount)
                    secondary = self.narrative_secondary[card]
                    if secondary == NARR_SECONDARY_FREE_TRIGGERED and controller == named_player:
                        _fe_queue_free_maneuver(
                            self, state, controller,
                            <uint16_t>(1 << named_slot), True, False, card
                        )
                    elif secondary == NARR_SECONDARY_FREE_ANY_NAMED:
                        sources = _fe_named_formation_mask(self, state, controller)
                        _fe_queue_free_maneuver(
                            self, state, controller, sources, True, False, card
                        )
                    if self.narrative_trigger_discard[card]:
                        _fe_discard_ongoing_narrative(self, 
                            state, controller, narrative_slot
                        )
            narrative_slot -= 1

cdef void _fe_resolve_retreat_narratives(
    FastEngine self,
    FastState state,
    int player,
    int retreated_slot,
) except *:
    cdef int narrative_slot, ix, card, amount
    cdef uint16_t destinations
    narrative_slot = self.ongoing_narrative_limit - 1
    while narrative_slot >= 0:
        ix = player * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
        card = state.narrative[ix]
        if (
            card >= 0
            and self.narrative_trigger[card] == NARR_TRIGGER_FRIENDLY_RETREAT
        ):
            amount = self.narrative_trigger_gain[card]
            if amount:
                _fe_gain_command_from_narrative(self, state, player, card, amount)
            if self.narrative_secondary[card] == NARR_SECONDARY_SIDEWAYS_TRIGGERED:
                destinations = _fe_adjacent_empty_mask(self, state, player, retreated_slot)
                _fe_queue_move_to_mask(self, 
                    state,
                    player,
                    <uint16_t>(1 << retreated_slot),
                    destinations,
                    True,
                )
            if self.narrative_trigger_discard[card]:
                _fe_discard_ongoing_narrative(self, 
                    state, player, narrative_slot
                )
        narrative_slot -= 1

cdef void _fe_resolve_force_pair_narratives(
    FastEngine self,
    FastState state,
    int force_player,
) noexcept:
    cdef int controller = 1 - force_player
    cdef int front, narrative_slot, ix, card, amount
    cdef bint pair_exists = False
    for front in range(FRONT_COUNT):
        if (
            state.force[slot_index(force_player, front, 0)] >= 0
            and state.force[slot_index(force_player, front, 1)] >= 0
        ):
            pair_exists = True
            break
    if not pair_exists:
        return
    narrative_slot = self.ongoing_narrative_limit - 1
    while narrative_slot >= 0:
        ix = controller * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
        card = state.narrative[ix]
        if (
            card >= 0
            and self.narrative_trigger[card]
            == NARR_TRIGGER_OPPONENT_BOTH_RANKS
        ):
            amount = self.narrative_trigger_gain[card]
            if amount:
                _fe_gain_command_from_narrative(self, state, controller, card, amount)
            if self.narrative_secondary[card] == NARR_SECONDARY_FREE_ANY_NAMED:
                _fe_queue_free_maneuver(
                    self,
                    state,
                    controller,
                    _fe_named_formation_mask(self, state, controller),
                    True,
                    False,
                    card,
                )
            if self.narrative_trigger_discard[card]:
                _fe_discard_ongoing_narrative(self, 
                    state, controller, narrative_slot
                )
        narrative_slot -= 1

cdef void _fe_resolve_maneuver_into_empty_narratives(
    FastEngine self,
    FastState state,
    int player,
    int vacated_slot,
) except *:
    cdef int narrative_slot, ix, card, amount
    cdef uint16_t sources
    for narrative_slot in range(self.ongoing_narrative_limit):
        ix = player * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
        card = state.narrative[ix]
        if card < 0 or state.narrative_used[ix]:
            continue
        amount = self.narrative_maneuver_empty_gain[card]
        if amount <= 0:
            continue
        state.narrative_used[ix] = 1
        _fe_gain_command_from_narrative(self, state, player, card, amount)
        if self.narrative_secondary[card] == NARR_SECONDARY_MOVE_VACATED:
            sources = _fe_adjacent_formation_mask(self, 
                state, player, vacated_slot, False
            )
            _fe_queue_move_to_mask(self, 
                state,
                player,
                sources,
                <uint16_t>(1 << vacated_slot),
                True,
            )

cdef void _fe_resolve_force_move_triggers(
    FastEngine self,
    FastState state,
    int player,
    int old_slot,
    int new_slot,
) except *:
    cdef int bond, front, rank, other
    cdef uint16_t destinations = 0
    if new_slot < 0 or state.force[new_slot] < 0:
        return
    bond = state.bond[new_slot]
    if bond < 0 or state.name[new_slot] >= 0 or not (self.card_capabilities[bond] & CAP_TRANSFER_OPEN_BOND_AFTER_MOVE_BOND):
        return
    front = front_from_slot(new_slot)
    rank = rank_from_slot(new_slot)
    if front > 0:
        other = slot_index(player, front - 1, rank)
        if state.force[other] >= 0 and state.bond[other] < 0:
            destinations |= <uint16_t>(1 << other)
    if front < 3:
        other = slot_index(player, front + 1, rank)
        if state.force[other] >= 0 and state.bond[other] < 0:
            destinations |= <uint16_t>(1 << other)
    if destinations:
        _fe_enqueue_effect(self, 
            state,
            EFFECT_TRANSFER_COMPONENT,
            player,
            -1,
            -1,
            -1,
            <uint16_t>(1 << new_slot),
            destinations,
            EFFECT_OPTIONAL,
        )

cdef void _fe_resolve_maneuver_triggers(
    FastEngine self,
    FastState state,
    int player,
    int vacated_slot,
    int arrived_slot,
    bint moved_into_empty,
) except *:
    cdef int force = state.force[arrived_slot]
    cdef int name = state.name[arrived_slot]
    cdef int front = front_from_slot(arrived_slot)
    cdef int rank = rank_from_slot(arrived_slot)
    cdef int opponent = 1 - player
    cdef int other, other_name, bond
    cdef uint16_t sources, destinations, swap_mask

    _fe_resolve_force_move_triggers(self, 
        state, player, vacated_slot, arrived_slot
    )
    if not moved_into_empty:
        # The swapped formation also moved, even though it did not
        # initiate the Maneuver.
        _fe_resolve_force_move_triggers(self, 
            state, player, arrived_slot, vacated_slot
        )

    if moved_into_empty:
        _fe_resolve_maneuver_into_empty_narratives(self, 
            state, player, vacated_slot
        )
        if force >= 0 and self.after_empty_follow_move[force]:
            sources = _fe_adjacent_formation_mask(self, 
                state, player, vacated_slot, False
            )
            _fe_queue_move_to_mask(self, 
                state, player, sources, <uint16_t>(1 << vacated_slot), True
            )
        if force >= 0 and self.after_empty_extra_move_force[force]:
            destinations = _fe_adjacent_empty_mask(self, 
                state, player, arrived_slot
            )
            _fe_queue_move_to_mask(self, 
                state,
                player,
                <uint16_t>(1 << arrived_slot),
                destinations,
                True,
            )
        if _fe_slot_complete(self, state, arrived_slot):
            sources = _fe_adjacent_formation_mask(self, 
                state, player, vacated_slot, False
            )
            for other in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
                if not (sources & (1 << other)):
                    continue
                bond = state.bond[other]
                if bond >= 0 and (self.card_capabilities[bond] & CAP_FOLLOW_INTO_VACATED_AFTER_ADJACENT_MANEUVER):
                    _fe_queue_move_to_mask(self, 
                        state,
                        player,
                        <uint16_t>(1 << other),
                        <uint16_t>(1 << vacated_slot),
                        True,
                    )
    else:
        if force >= 0 and self.after_swap_free_other[force]:
            if state.force[vacated_slot] >= 0:
                _fe_queue_free_maneuver(
                    self, state, player, <uint16_t>(1 << vacated_slot),
                    True, False, force
                )

    if force >= 0 and self.after_maneuver_free_adjacent[force]:
        _fe_queue_free_maneuver(
            self,
            state,
            player,
            _fe_adjacent_formation_mask(
                self, state, player, arrived_slot, True
            ),
            True,
            False,
            force,
        )

    if name >= 0 and (self.card_capabilities[name] & CAP_AFTER_MANEUVER_SWAP_OTHER_FRIENDLIES):
        swap_mask = 0
        for other in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
            if other != arrived_slot and state.force[other] >= 0:
                swap_mask |= <uint16_t>(1 << other)
        if swap_mask:
            _fe_enqueue_effect(self, 
                state,
                EFFECT_SWAP,
                player,
                -1,
                -1,
                -1,
                swap_mask,
                swap_mask,
                EFFECT_OPTIONAL | EFFECT_ADJACENT_PAIR,
            )

    if name >= 0 and (self.card_capabilities[name] & CAP_AFTER_SELF_MANEUVER_FREE_OTHER_NAMED_IF_WIDE) and _fe_force_in_all_fronts(self, state, player):
        _fe_queue_free_maneuver(
            self,
            state,
            player,
            _fe_named_formation_mask(self, state, player, arrived_slot),
            True,
            False,
            name,
        )

    for other in range(opponent * POSITIONS_PER_PLAYER, opponent * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
        other_name = state.name[other]
        if other_name < 0 or state.force[other] < 0:
            continue
        if front_from_slot(other) == front and (self.card_capabilities[other_name] & CAP_OPPOSING_MANEUVER_SAME_FRONT_FREE_MANEUVER):
            _fe_queue_free_maneuver(
                self, state, opponent, <uint16_t>(1 << other),
                True, False, other_name
            )
        if (
            abs(front_from_slot(other) - front) == 1
            and self.reactive_maneuver_name[other_name]
        ):
            _fe_queue_free_maneuver(
                self, state, opponent, <uint16_t>(1 << other),
                True, False, other_name
            )

cdef void _fe_resolve_narrative_target_ongoing_narrative(FastEngine self, FastState state, int actor, int pos):
    cdef int opponent = 1 - actor
    cdef int front, ix, card
    if pos < 0 or owner_from_slot(pos) != opponent:
        return
    front = front_from_slot(pos)
    ix = opponent * NARRATIVE_SLOTS_PER_PLAYER + front
    card = state.narrative[ix]
    if card < 0 or self.ongoing_reveal_trigger[card] != EVENT_NARRATIVE_TARGET:
        return
    if self.ongoing_reveal_requires_force[card] and not _fe_front_has_force(self, state, opponent, front):
        return
    _fe_reveal_ongoing_narrative(self, state, opponent, front, actor, -1)

cdef void _fe_reshuffle_discard_into_deck(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    cdef int i, j, card
    cdef uint32_t seed
    if (
        state.deck_len[player] > 0
        or state.discard_len[player] == 0
    ):
        return
    state.deck_reshuffles[player] += 1
    state.reshuffle_card_totals[player] += state.discard_len[player]
    state.reshuffle_hand_card_totals[player] += state.hand_len[player]
    for i in range(state.discard_len[player]):
        card = state.discard[player][i]
        state.deck[player][state.deck_len[player]] = card
        state.deck_len[player] += 1
        state.deck_counts[player][card] += 1
    state.discard_len[player] = 0
    seed = state.shuffle_seed
    i = state.deck_len[player] - 1
    while i > 0:
        seed = _fe_next_shuffle_seed(self, seed)
        j = seed % (i + 1)
        card = state.deck[player][i]
        state.deck[player][i] = state.deck[player][j]
        state.deck[player][j] = card
        i -= 1
    state.shuffle_seed = seed

cdef void _fe_draw(FastEngine self, FastState state, int player, int count) noexcept:
    cdef int card
    while count > 0:
        if state.deck_len[player] == 0:
            _fe_reshuffle_discard_into_deck(self, state, player)
        if state.deck_len[player] == 0:
            break
        state.deck_len[player] -= 1
        card = state.deck[player][state.deck_len[player]]
        state.deck_counts[player][card] -= 1
        state.hand[player][card] += 1
        state.hand_len[player] += 1
        count -= 1

cdef void _fe_draw_for_battle(
    FastEngine self,
    FastState state,
    int player,
    int count,
) noexcept:
    cdef int before = state.hand_len[player]
    _fe_draw(self, state, player, count)
    state.cards_drawn_this_battle[player] += state.hand_len[player] - before

cdef void _fe_queue_battle_draws(
    FastEngine self,
    FastState state,
    int player,
    int count,
) noexcept:
    """Process draws one at a time and pause for discard at hand limit."""
    if count <= 0:
        return
    if state.cleanup_pending:
        state.pending_draw_count += count
        return
    state.pending_draw_count = 0
    while count > 0 and _fe_can_draw_fast(self, state, player):
        if state.hand_len[player] >= self.hand_limit:
            state.active_player = player
            state.cleanup_pending = 1
            state.pending_draw_count = count
            return
        _fe_draw_for_battle(self, state, player, 1)
        count -= 1

cdef void _fe_start_turn_fast(FastEngine self, FastState state, int player) noexcept:
    state.active_player = player
    memset(
        state.maneuvered_in_operation,
        0,
        sizeof(state.maneuvered_in_operation),
    )
    state.cards_played_this_turn_front_mask[player] = 0
    state.cleanup_pending = 0
    state.pending_draw_count = 0
    state.pending_draw_finish_operation = 0
    if state.phase == PHASE_BATTLE:
        _fe_queue_battle_draws(self, state, player, self.turn_draw_count)

cdef _fe_initialize_opening_turn(
    FastEngine self,
    FastState state,
    int active_player,
    bint opening_bonus=True,
):
    state.active_player = active_player
    if not opening_bonus:
        return
    _fe_start_turn_fast(self, state, active_player)

cdef inline void _fe_clear_pass_sequence_fast(
    FastEngine self,
    FastState state,
) noexcept:
    state.passed[0] = 0
    state.passed[1] = 0
    state.pass_len = 0
    state.pass_order[0] = -1
    state.pass_order[1] = -1


cdef void _fe_resume_pending_flow(FastEngine self, FastState state):
    cdef int resume, player
    if state.cleanup_pending:
        if state.pending_resume == RESUME_FINISH_OPERATION:
            state.pending_draw_finish_operation = 1
        return
    if state.pending_len > 0:
        state.active_player = state.pending_player[0]
        return
    resume = state.pending_resume
    player = state.pending_resume_player
    state.pending_resume = RESUME_NONE
    state.pending_resume_player = -1
    state.pending_draw_finish_operation = 0
    if resume == RESUME_FINISH_OPERATION and player >= 0:
        _fe_finish_operation_fast(self, state, player)
    elif resume == RESUME_BATTLE_RESOLUTION:
        _fe_advance_battle_resolution(self, state)
    elif resume == RESUME_START_BATTLE:
        _fe_finish_start_battle(self, state, player)

cdef void _fe_finish_operation_fast(FastEngine self, FastState state, int actor):
    cdef int opponent = 1 - actor
    state.operations_this_battle[actor] += 1

    # A fixed closing window counts turns completed after the first signal.
    if (
        state.pass_len > 0
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
