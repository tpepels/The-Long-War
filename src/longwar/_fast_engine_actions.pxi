cdef inline bint _fe_opponent_blocks_card_move_into_front(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int opponent = 1 - player
    cdef int rank, slot, bond
    for rank in range(2):
        slot = slot_index(opponent, front, rank)
        bond = state.link[slot]
        if bond >= 0 and self.bond_blocks_opponent_card_move[bond]:
            return True
    return False

cdef inline bint _fe_card_move_destination_legal(
    FastEngine self,
    FastState state,
    int controller,
    int source,
    int dest,
) noexcept:
    cdef int force = state.subject[source]
    cdef int owner = owner_from_slot(source)
    cdef int bond = state.link[source]
    if force < 0 or self.immobile_force[force]:
        return False
    if owner_from_slot(dest) != owner:
        return False
    if (
        controller != owner
        and bond >= 0
        and self.bond_guarded_from_opponent_card_move[bond]
    ):
        return False
    if (
        state.subject[dest] >= 0
        or state.link[dest] >= 0
        or state.name[dest] >= 0
    ):
        return False
    if (
        abs(front_from_slot(source) - front_from_slot(dest)) == 1
        and _fe_opponent_blocks_card_move_into_front(self, 
            state, owner, front_from_slot(dest)
        )
    ):
        return False
    return True

cdef inline bint _fe_player_has_empty_front(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    cdef int front
    for front in range(4):
        if (
            state.subject[slot_index(player, front, 0)] < 0
            and state.subject[slot_index(player, front, 1)] < 0
        ):
            return True
    return False

cdef inline bint _fe_adjacent_hero_formation(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int local = local_slot(slot)
    cdef int front = local >> 1
    cdef int rank = local & 1
    cdef int adjacent, force, name
    if front > 0:
        adjacent = slot_index(player, front - 1, rank)
        force = state.subject[adjacent]
        name = state.name[adjacent]
        if force >= 0 and (
            self.hero[force]
            or (name >= 0 and self.hero[name])
        ):
            return True
    if front < 3:
        adjacent = slot_index(player, front + 1, rank)
        force = state.subject[adjacent]
        name = state.name[adjacent]
        if force >= 0 and (
            self.hero[force]
            or (name >= 0 and self.hero[name])
        ):
            return True
    return False

cdef inline bint _fe_maneuver_source_legal(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int force, bond, strat
    force = state.subject[slot]
    if force < 0 or self.immobile_force[force]:
        return False
    if _fe_slot_complete(self, state, slot):
        return True
    if self.can_maneuver_unnamed[force]:
        if not self.maneuver_requires_open_bond[force]:
            return True
        if state.link[slot] >= 0 and state.name[slot] < 0:
            return True
    bond = state.link[slot]
    if (
        bond >= 0
        and self.bond_maneuver_adjacent_hero[bond]
        and _fe_adjacent_hero_formation(self, state, player, slot)
    ):
        return True
    strat = state.stratagem[player]
    return strat >= 0 and self.strat_unnamed_maneuver[strat]

cdef inline bint _fe_maneuver_destination_legal(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int force = state.subject[slot]
    if force >= 0:
        return (
            not self.immobile_force[force]
            and not self.cannot_swap_target[force]
        )
    return state.link[slot] < 0 and state.name[slot] < 0


cdef void _fe_remove_constraint_at(
    FastState state,
    int index,
) noexcept:
    cdef int i
    if index < 0 or index >= state.constraint_len:
        return
    for i in range(index, state.constraint_len - 1):
        state.constraint_kind[i] = state.constraint_kind[i + 1]
        state.constraint_player[i] = state.constraint_player[i + 1]
        state.constraint_source_card[i] = state.constraint_source_card[i + 1]
        state.constraint_source_owner[i] = state.constraint_source_owner[i + 1]
        state.constraint_front[i] = state.constraint_front[i + 1]
        state.constraint_direction[i] = state.constraint_direction[i + 1]
        state.constraint_source_slot[i] = state.constraint_source_slot[i + 1]
        state.constraint_activate_turn[i] = state.constraint_activate_turn[i + 1]
        state.constraint_flags[i] = state.constraint_flags[i + 1]
    state.constraint_len -= 1
    if state.constraint_len >= 0:
        i = state.constraint_len
        state.constraint_kind[i] = CONSTRAINT_NONE
        state.constraint_player[i] = -1
        state.constraint_source_card[i] = -1
        state.constraint_source_owner[i] = -1
        state.constraint_front[i] = -1
        state.constraint_direction[i] = 0
        state.constraint_source_slot[i] = -1
        state.constraint_activate_turn[i] = 0
        state.constraint_flags[i] = 0


cdef void _fe_add_constraint(
    FastState state,
    int kind,
    int player,
    int source_card,
    int source_owner,
    int front=-1,
    int direction=0,
    int source_slot=-1,
    int activate_turn=0,
    int flags=CONSTRAINT_EXPIRES_AFTER_OPERATION,
) except *:
    cdef int i = state.constraint_len
    if i >= MAX_CONSTRAINTS:
        raise RuntimeError("Native operation-constraint capacity exceeded")
    state.constraint_kind[i] = kind
    state.constraint_player[i] = player
    state.constraint_source_card[i] = source_card
    state.constraint_source_owner[i] = source_owner
    state.constraint_front[i] = front
    state.constraint_direction[i] = direction
    state.constraint_source_slot[i] = source_slot
    state.constraint_activate_turn[i] = activate_turn
    state.constraint_flags[i] = flags
    state.constraint_len += 1


cdef inline int _fe_action_direction(uint64_t action) noexcept:
    cdef int source, dest
    if action_kind(action) != TYPE_MANEUVER:
        return 0
    source = action_pos(action)
    dest = action_dest(action)
    if source < 0 or dest < 0:
        return 0
    if front_from_slot(dest) < front_from_slot(source):
        return 1
    if front_from_slot(dest) > front_from_slot(source):
        return 2
    return 0


cdef inline bint _fe_action_affects_front(
    FastEngine self,
    uint64_t action,
    int front,
) noexcept:
    cdef int kind = action_kind(action)
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef uint32_t extra = action_extra(action)
    if front < 0:
        return False
    if kind == TYPE_SUBJECT or kind == TYPE_LINK or kind == TYPE_NAME:
        return pos >= 0 and front_from_slot(pos) == front
    if kind == TYPE_MANEUVER:
        return (
            (pos >= 0 and front_from_slot(pos) == front)
            or (dest >= 0 and front_from_slot(dest) == front)
        )
    if kind == TYPE_SCHEME:
        return bool(extra & (<uint32_t>1 << front))
    if kind == TYPE_STRATAGEM:
        return pos >= 0 and bool(pos & (1 << front))
    return False


cdef inline bint _fe_constraint_satisfied(
    FastEngine self,
    FastState state,
    int index,
    uint64_t action,
) noexcept:
    cdef int kind = state.constraint_kind[index]
    if kind == CONSTRAINT_AFFECT_FRONT:
        return _fe_action_affects_front(
            self, action, state.constraint_front[index]
        )
    if kind == CONSTRAINT_MANEUVER:
        return action_kind(action) == TYPE_MANEUVER
    if kind == CONSTRAINT_SPECIFIC_MANEUVER:
        return (
            action_kind(action) == TYPE_MANEUVER
            and action_pos(action) == state.constraint_source_slot[index]
            and _fe_action_direction(action) == state.constraint_direction[index]
        )
    return False


cdef bint _fe_basic_maneuver_locks_allow(
    FastEngine self,
    FastState state,
    int player,
    int source,
    int dest,
) noexcept:
    cdef int controller, story_slot, ix, card, front
    front = front_from_slot(source)
    if front_from_slot(dest) == front:
        return True

    # Ongoing Sagas can pin Named Formations in their chosen Front.
    if _fe_slot_complete(self, state, source):
        for controller in range(2):
            for story_slot in range(self.ongoing_story_limit):
                ix = controller * 4 + story_slot
                card = state.scheme[ix]
                if (
                    card >= 0
                    and self.narrative_no_maneuver_away[card]
                    and state.scheme_front_mask[ix] & (1 << front)
                ):
                    return False

    # There Was No Road Back pins every formation in the chosen Front.
    for controller in range(2):
        card = state.stratagem[controller]
        if (
            card >= 0
            and self.strat_no_maneuver_away[card]
            and state.stratagem_front_mask[controller] & (1 << front)
        ):
            return False
    return True


cdef bint _fe_had_been_ordered_allows(
    FastEngine self,
    FastState state,
    int player,
    int source,
    int dest,
) noexcept:
    cdef int bond = state.link[source]
    cdef int direction, front, rank, preferred
    if (
        bond < 0
        or not self.bond_momentum_direction[bond]
        or state.maneuver_count[source] == 0
    ):
        return True
    direction = state.maneuver_direction[source]
    if direction == 0 or _fe_action_direction(
        encode_action(TYPE_MANEUVER, -1, source, dest, player)
    ) == direction:
        return True
    front = front_from_slot(source)
    rank = rank_from_slot(source)
    if direction == 1:
        if front == 0:
            return True
        preferred = slot_index(player, front - 1, rank)
    else:
        if front == 3:
            return True
        preferred = slot_index(player, front + 1, rank)
    if (
        _fe_maneuver_destination_legal(self, state, preferred)
        and _fe_basic_maneuver_locks_allow(
            self, state, player, source, preferred
        )
    ):
        return False
    return True


cdef bint _fe_any_maneuver_in_direction(
    FastEngine self,
    FastState state,
    int player,
    int direction,
) noexcept:
    cdef int local, source, front, rank, dest
    for local in range(8):
        source = player * 8 + local
        if not _fe_maneuver_source_legal(self, state, player, source):
            continue
        front = local >> 1
        rank = local & 1
        if direction == 1:
            if front == 0:
                continue
            dest = slot_index(player, front - 1, rank)
        else:
            if front == 3:
                continue
            dest = slot_index(player, front + 1, rank)
        if (
            _fe_maneuver_destination_legal(self, state, dest)
            and _fe_basic_maneuver_locks_allow(
                self, state, player, source, dest
            )
            and _fe_had_been_ordered_allows(
                self, state, player, source, dest
            )
        ):
            return True
    return False


cdef bint _fe_maneuver_allowed_by_continuous(
    FastEngine self,
    FastState state,
    int player,
    int source,
    int dest,
) noexcept:
    cdef int controller, card, requested, direction
    cdef bint need_left=False, need_right=False
    cdef bint left_possible=False, right_possible=False

    if not _fe_basic_maneuver_locks_allow(
        self, state, player, source, dest
    ):
        return False
    if not _fe_had_been_ordered_allows(
        self, state, player, source, dest
    ):
        return False

    if state.player_maneuver_count[player] > 0:
        return True

    for controller in range(2):
        card = state.stratagem[controller]
        if card < 0 or not self.strat_first_maneuver_direction[card]:
            continue
        requested = state.stratagem_direction[controller]
        if requested == 1:
            need_left = True
        elif requested == 2:
            need_right = True

    if need_left:
        left_possible = _fe_any_maneuver_in_direction(
            self, state, player, 1
        )
    if need_right:
        right_possible = _fe_any_maneuver_in_direction(
            self, state, player, 2
        )

    direction = (
        1
        if front_from_slot(dest) < front_from_slot(source)
        else 2
    )
    if left_possible and not right_possible:
        return direction == 1
    if right_possible and not left_possible:
        return direction == 2
    # If both requirements are satisfiable but conflict, the rulebook permits
    # choosing one satisfiable requirement. If neither can be satisfied,
    # ordinary Maneuvers remain legal.
    return True


cdef int _fe_filter_operation_constraints(
    FastEngine self,
    FastState state,
    int player,
    uint64_t* actions,
    int n,
    bint* enforced,
) noexcept:
    cdef int i, j, kept, active_count=0, satisfied_count
    cdef bint satisfiable[MAX_CONSTRAINTS]
    cdef bint all_possible
    cdef uint64_t action

    enforced[0] = False
    memset(satisfiable, 0, sizeof(satisfiable))

    for j in range(state.constraint_len):
        if (
            state.constraint_player[j] != player
            or state.turn_number < state.constraint_activate_turn[j]
        ):
            continue
        for i in range(n):
            if _fe_constraint_satisfied(self, state, j, actions[i]):
                satisfiable[j] = True
                active_count += 1
                break

    if active_count == 0:
        return n

    # First prefer operations satisfying every currently satisfiable
    # requirement simultaneously.
    kept = 0
    for i in range(n):
        action = actions[i]
        all_possible = True
        for j in range(state.constraint_len):
            if not satisfiable[j]:
                continue
            if not _fe_constraint_satisfied(self, state, j, action):
                all_possible = False
                break
        if all_possible:
            actions[kept] = action
            kept += 1
    if kept > 0:
        enforced[0] = True
        return kept

    # No operation can satisfy them all. Canonical rule: choose one
    # satisfiable requirement. Therefore expose the union of operations that
    # satisfy at least one of them.
    kept = 0
    for i in range(n):
        action = actions[i]
        satisfied_count = 0
        for j in range(state.constraint_len):
            if (
                satisfiable[j]
                and _fe_constraint_satisfied(self, state, j, action)
            ):
                satisfied_count += 1
        if satisfied_count:
            actions[kept] = action
            kept += 1
    if kept > 0:
        enforced[0] = True
        return kept
    return n


cdef void _fe_enqueue_effect(
    FastEngine self,
    FastState state,
    int kind,
    int player,
    int card=-1,
    int source=-1,
    int aux=-1,
    uint16_t source_mask=0,
    uint16_t dest_mask=0,
    int flags=0,
) except *:
    cdef int i = state.pending_len
    if i >= MAX_PENDING_EFFECTS:
        raise RuntimeError("Pending card-effect capacity exceeded")
    state.pending_kind[i] = kind
    state.pending_player[i] = player
    state.pending_card[i] = card
    state.pending_source[i] = source
    state.pending_aux[i] = aux
    state.pending_source_mask[i] = source_mask
    state.pending_dest_mask[i] = dest_mask
    state.pending_flags[i] = flags
    state.pending_len += 1
    if state.pending_len == 1:
        state.active_player = player

cdef void _fe_pop_pending_effect(FastEngine self, FastState state) noexcept:
    cdef int i
    if state.pending_len == 0:
        return
    for i in range(1, state.pending_len):
        state.pending_kind[i - 1] = state.pending_kind[i]
        state.pending_player[i - 1] = state.pending_player[i]
        state.pending_card[i - 1] = state.pending_card[i]
        state.pending_source[i - 1] = state.pending_source[i]
        state.pending_aux[i - 1] = state.pending_aux[i]
        state.pending_source_mask[i - 1] = state.pending_source_mask[i]
        state.pending_dest_mask[i - 1] = state.pending_dest_mask[i]
        state.pending_flags[i - 1] = state.pending_flags[i]
    state.pending_len -= 1
    if state.pending_len > 0:
        state.active_player = state.pending_player[0]

cdef inline bint _fe_slot_is_empty(FastEngine self, FastState state, int slot) noexcept:
    return (
        state.subject[slot] < 0
        and state.link[slot] < 0
        and state.name[slot] < 0
    )

cdef int _fe_legal_pending_effect_actions(
    FastEngine self,
    FastState state,
    uint64_t* actions,
) except -1:
    cdef int n = 0
    cdef int kind, player, source, dest, front, rank, card, i, j
    cdef uint16_t source_mask, dest_mask
    cdef uint8_t flags
    if state.pending_len == 0:
        return 0
    kind = state.pending_kind[0]
    player = state.pending_player[0]
    source = state.pending_source[0]
    source_mask = state.pending_source_mask[0]
    dest_mask = state.pending_dest_mask[0]
    flags = state.pending_flags[0]

    if flags & EFFECT_OPTIONAL:
        n = _append_action(
            actions, n, encode_action(TYPE_EFFECT, -1, -1, -1, player, kind)
        )

    if kind == EFFECT_FREE_MANEUVER:
        for source in range(player * 8, player * 8 + 8):
            if not (source_mask & (1 << source)):
                continue
            if flags & EFFECT_ALLOW_UNNAMED:
                if (
                    state.subject[source] < 0
                    or self.immobile_force[state.subject[source]]
                ):
                    continue
            elif not _fe_maneuver_source_legal(self, 
                state, player, source
            ):
                continue
            front = front_from_slot(source)
            rank = rank_from_slot(source)
            if front > 0:
                dest = slot_index(player, front - 1, rank)
                if _fe_maneuver_destination_legal(self, state, dest):
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
            if front < 3:
                dest = slot_index(player, front + 1, rank)
                if _fe_maneuver_destination_legal(self, state, dest):
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_MOVE:
        for source in range(SLOT_COUNT):
            if not (source_mask & (1 << source)) or state.subject[source] < 0:
                continue
            for dest in range(SLOT_COUNT):
                if not (dest_mask & (1 << dest)):
                    continue
                if _fe_card_move_destination_legal(self, 
                    state, player, source, dest
                ):
                    n = _append_action(
                        actions,
                        n,
                        encode_action(
                            TYPE_EFFECT,
                            -1,
                            source,
                            dest,
                            player,
                            kind,
                        ),
                    )
    elif kind == EFFECT_SWAP:
        for source in range(player * 8, player * 8 + 8):
            if not (source_mask & (1 << source)) or state.subject[source] < 0:
                continue
            for dest in range(player * 8, player * 8 + 8):
                if dest == source:
                    continue
                if source_mask == dest_mask and dest < source:
                    continue
                if not (dest_mask & (1 << dest)) or state.subject[dest] < 0:
                    continue
                if flags & EFFECT_ADJACENT_PAIR:
                    if rank_from_slot(source) != rank_from_slot(dest) or abs(front_from_slot(source) - front_from_slot(dest)) != 1:
                        continue
                if flags & EFFECT_SAME_FRONT_PAIR:
                    if front_from_slot(source) != front_from_slot(dest) or rank_from_slot(source) == rank_from_slot(dest):
                        continue
                if self.immobile_force[state.subject[source]] or self.immobile_force[state.subject[dest]]:
                    continue
                if self.cannot_swap_target[state.subject[source]] or self.cannot_swap_target[state.subject[dest]]:
                    continue
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_RECOVER:
        for i in range(state.discard_len[player]):
            card = state.discard[player][i]
            if state.pending_aux[0] == CARD_LINK and self.card_type[card] != CARD_LINK:
                continue
            if state.pending_aux[0] == CARD_PLOT and self.card_type[card] != CARD_PLOT:
                continue
            n = _append_action(actions, n, encode_action(TYPE_EFFECT, card, -1, -1, player, kind))
    elif kind == EFFECT_FRONT_CONTRIBUTION:
        source = state.pending_source[0]
        if source >= 0 and state.subject[source] >= 0:
            front = front_from_slot(source)
            for dest in range(max(0, front - 1), min(3, front + 1) + 1):
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_SUPPRESS:
        for dest in range(SLOT_COUNT):
            if dest_mask & (1 << dest) and state.subject[dest] >= 0:
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, -1, dest, player, kind))
    elif kind == EFFECT_SACRIFICE:
        source = state.pending_source[0]
        if source >= 0 and state.subject[source] >= 0:
            for dest in range(SLOT_COUNT):
                if dest_mask & (1 << dest) and state.subject[dest] >= 0:
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_INTERCEPT:
        for source in range(player * 8, player * 8 + 8):
            if source_mask & (1 << source) and _fe_slot_complete(self, state, source):
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, -1, player, kind))
    elif kind == EFFECT_RETREAT:
        source = state.pending_source[0]
        dest = state.pending_aux[0]
        if source >= 0 and dest >= 0 and _fe_slot_complete(self, state, source) and _fe_slot_is_empty(self, state, dest):
            n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_PROTECT_RETREAT:
        source = state.pending_source[0]
        if source >= 0 and state.subject[source] >= 0:
            n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, state.pending_aux[0], player, kind))
    elif kind == EFFECT_TRANSFER_COMPONENT:
        for source in range(player * 8, player * 8 + 8):
            if not (source_mask & (1 << source)):
                continue
            for dest in range(player * 8, player * 8 + 8):
                if state.pending_aux[0] >= 0:
                    if dest != state.pending_aux[0]:
                        continue
                elif not (dest_mask & (1 << dest)):
                    continue
                if state.link[source] >= 0 and state.link[dest] < 0:
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, state.link[source], source, dest, player, kind))
                if state.name[source] >= 0 and state.name[dest] < 0:
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, state.name[source], source, dest, player, kind))
    elif kind == EFFECT_SUCCESSION:
        source = state.pending_source[0]
        for dest in range(player * 8, player * 8 + 8):
            if dest_mask & (1 << dest) and state.subject[dest] >= 0 and state.link[dest] >= 0 and state.name[dest] < 0:
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    return n

cdef int _fe_legal_actions_into(
    FastEngine self,
    FastState state,
    uint64_t* actions,
) except -1:
    cdef int n = 0
    cdef int player, card, slot, local, front, rank, source, dest, req, opponent, effect
    cdef int i, kept, can_pass, available, story_slot, choice, direction
    cdef uint32_t eligible_mask, subset
    cdef uint64_t action
    cdef bint constraint_enforced = False

    if state.phase == PHASE_COMPLETE:
        return 0

    player = state.active_player

    # A turn that starts at the hand limit must discard before its
    # automatic draw. This substep is not the turn's operation.
    if state.cleanup_pending:
        for card in range(self.n_cards):
            if state.hand[player][card] > 0:
                n = _append_action(
                    actions,
                    n,
                    encode_action(TYPE_DISCARD, card, -1, -1, player),
                )
        return n
    if state.pending_len > 0:
        return _fe_legal_pending_effect_actions(self, state, actions)

    opponent = 1 - player

    for card in range(self.n_cards):
        if state.hand[player][card] == 0:
            continue

        if self.card_type[card] == CARD_SUBJECT:
            if not self.hero[card] or not state.hero_used[player]:
                req = self.placement_rank[card]
                for local in range(8):
                    slot = player * 8 + local
                    if state.subject[slot] >= 0:
                        continue
                    rank = local & 1
                    if req >= 0 and req != rank:
                        continue
                    n = _append_action(
                        actions,
                        n,
                        encode_action(TYPE_SUBJECT, card, slot, -1, player),
                    )

                # Heroes are dual-use Force/Name cards. Playing either mode
                # consumes the one-Hero-from-hand allowance for the Battle.
                if self.hero[card]:
                    for local in range(8):
                        slot = player * 8 + local
                        if state.name[slot] < 0:
                            n = _append_action(
                                actions,
                                n,
                                encode_action(TYPE_NAME, card, slot, -1, player),
                            )

        elif self.card_type[card] == CARD_LINK:
            for local in range(8):
                slot = player * 8 + local
                if state.link[slot] >= 0:
                    continue
                n = _append_action(
                    actions,
                    n,
                    encode_action(TYPE_LINK, card, slot, -1, player),
                )
                if self.bond_optional_extra_cost[card] > 0:
                    n = _append_action(
                        actions,
                        n,
                        encode_action(
                            TYPE_LINK,
                            card,
                            slot,
                            -1,
                            player,
                            1,
                        ),
                    )
                if (
                    self.bond_move_on_play[card]
                    and state.subject[slot] >= 0
                    and not self.immobile_force[state.subject[slot]]
                ):
                    front = local >> 1
                    rank = local & 1
                    if front > 0:
                        dest = slot_index(player, front - 1, rank)
                        if _fe_card_move_destination_legal(self, 
                            state, player, slot, dest
                        ):
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_LINK,
                                    card,
                                    slot,
                                    dest,
                                    player,
                                ),
                            )
                    if front < 3:
                        dest = slot_index(player, front + 1, rank)
                        if _fe_card_move_destination_legal(self, 
                            state, player, slot, dest
                        ):
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_LINK,
                                    card,
                                    slot,
                                    dest,
                                    player,
                                ),
                            )

        elif self.card_type[card] == CARD_NAME:
            for local in range(8):
                slot = player * 8 + local
                if state.name[slot] >= 0:
                    continue
                n = _append_action(
                    actions,
                    n,
                    encode_action(TYPE_NAME, card, slot, -1, player),
                )

        elif self.card_type[card] == CARD_PLOT:
            if self.veiled[card]:
                # Ongoing Narratives may carry a public Front or formation
                # association selected when the card is played.
                choice = self.story_choice_kind[card]
                for story_slot in range(self.ongoing_story_limit):
                    if state.scheme[player * 4 + story_slot] >= 0:
                        continue
                    if choice == STORY_CHOICE_FRONT:
                        for front in range(4):
                            if (
                                self.narrative_front_requires_named[card]
                                and not (
                                    _fe_slot_complete(
                                        self, state, slot_index(player, front, 0)
                                    )
                                    or _fe_slot_complete(
                                        self, state, slot_index(player, front, 1)
                                    )
                                )
                            ):
                                continue
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_SCHEME,
                                    card,
                                    story_slot,
                                    -1,
                                    player,
                                    <uint32_t>(1 << front),
                                ),
                            )
                    elif (
                        choice == STORY_CHOICE_NAMED_FORMATION
                        or choice == STORY_CHOICE_NAMED_DIRECTION
                    ):
                        for local in range(8):
                            slot = player * 8 + local
                            if _fe_slot_complete(self, state, slot):
                                if choice == STORY_CHOICE_NAMED_DIRECTION:
                                    for direction in range(2):
                                        n = _append_action(
                                            actions,
                                            n,
                                            encode_action(
                                                TYPE_SCHEME,
                                                card,
                                                story_slot,
                                                slot,
                                                player,
                                                <uint32_t>(direction + 1),
                                            ),
                                        )
                                else:
                                    n = _append_action(
                                        actions,
                                        n,
                                        encode_action(
                                            TYPE_SCHEME,
                                            card,
                                            story_slot,
                                            slot,
                                            player,
                                        ),
                                    )
                    else:
                        n = _append_action(
                            actions,
                            n,
                            encode_action(
                                TYPE_SCHEME,
                                card,
                                story_slot,
                                -1,
                                player,
                            ),
                        )
            else:
                effect = self.plot_effect[card]
                if effect == PLOT_DISCREDIT or effect == PLOT_RETURN_NAME:
                    for local in range(8):
                        slot = opponent * 8 + local
                        if (
                            state.subject[slot] >= 0
                            and not _fe_subject_protected(self, state, slot)
                        ):
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_PLOT,
                                    card,
                                    slot,
                                    -1,
                                    opponent,
                                ),
                            )
                elif effect == PLOT_MOVE_SUBJECT:
                    for source in range(player * 8, player * 8 + 8):
                        if state.subject[source] < 0:
                            continue
                        for dest in range(player * 8, player * 8 + 8):
                            if (
                                dest == source
                                or state.subject[dest] >= 0
                                or state.link[dest] >= 0
                                or state.name[dest] >= 0
                            ):
                                continue
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_PLOT,
                                    card,
                                    source,
                                    dest,
                                    player,
                                ),
                            )
                else:
                    n = _append_action(
                        actions,
                        n,
                        encode_action(TYPE_PLOT, card, -1, -1, player),
                    )
                    if self.story_discard_count[card] == 1:
                        for i in range(self.n_cards):
                            if state.hand[player][i] <= 0:
                                continue
                            if i == card and state.hand[player][i] < 2:
                                continue
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_PLOT,
                                    card,
                                    -1,
                                    -1,
                                    player,
                                    <uint32_t>(i + 1),
                                ),
                            )

        elif self.card_type[card] == CARD_STRATAGEM:
            if (
                not state.stratagem_used[player]
                and state.stratagem[player] < 0
            ):
                choice = self.strat_choice_kind[card]
                if choice == STRAT_CHOICE_FRONT:
                    for front in range(4):
                        n = _append_action(
                            actions,
                            n,
                            encode_action(
                                TYPE_STRATAGEM,
                                card,
                                1 << front,
                                -1,
                                player,
                            ),
                        )
                elif choice == STRAT_CHOICE_ADJACENT_FRONTS:
                    for front in range(3):
                        n = _append_action(
                            actions,
                            n,
                            encode_action(
                                TYPE_STRATAGEM,
                                card,
                                3 << front,
                                -1,
                                player,
                            ),
                        )
                elif choice == STRAT_CHOICE_EDGE_FRONT:
                    for front in (0, 3):
                        n = _append_action(
                            actions,
                            n,
                            encode_action(
                                TYPE_STRATAGEM,
                                card,
                                1 << front,
                                -1,
                                player,
                            ),
                        )
                elif choice == STRAT_CHOICE_DIRECTION:
                    for direction in range(2):
                        n = _append_action(
                            actions,
                            n,
                            encode_action(
                                TYPE_STRATAGEM,
                                card,
                                -1,
                                direction,
                                player,
                            ),
                        )
                elif choice == STRAT_CHOICE_WHEEL:
                    for direction in range(2):
                        eligible_mask = 0
                        for local in range(8):
                            source = player * 8 + local
                            if state.subject[source] < 0:
                                continue
                            front = local >> 1
                            rank = local & 1
                            if direction == 0:
                                if front == 0:
                                    continue
                                dest = slot_index(player, front - 1, rank)
                            else:
                                if front == 3:
                                    continue
                                dest = slot_index(player, front + 1, rank)
                            if _fe_card_move_destination_legal(self, 
                                state, player, source, dest
                            ):
                                eligible_mask |= <uint32_t>(1 << source)
                        subset = eligible_mask
                        while True:
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_STRATAGEM,
                                    card,
                                    -1,
                                    direction,
                                    player,
                                    subset,
                                ),
                            )
                            if subset == 0:
                                break
                            subset = (subset - 1) & eligible_mask
                elif choice == STRAT_CHOICE_RESERVES:
                    eligible_mask = 0
                    for front in range(4):
                        source = slot_index(player, front, 1)
                        dest = slot_index(player, front, 0)
                        if (
                            state.subject[source] >= 0
                            and not self.immobile_force[state.subject[source]]
                            and state.subject[dest] < 0
                            and state.link[dest] < 0
                            and state.name[dest] < 0
                        ):
                            eligible_mask |= <uint32_t>(1 << source)
                    subset = eligible_mask
                    while True:
                        n = _append_action(
                            actions,
                            n,
                            encode_action(
                                TYPE_STRATAGEM,
                                card,
                                -1,
                                -1,
                                player,
                                subset,
                            ),
                        )
                        if subset == 0:
                            break
                        subset = (subset - 1) & eligible_mask
                else:
                    n = _append_action(
                        actions,
                        n,
                        encode_action(
                            TYPE_STRATAGEM,
                            card,
                            -1,
                            -1,
                            player,
                        ),
                    )

    # Maneuver moves to an empty position or swaps with another formation.
    # A prepared-only Bond/Name position is occupied but is not a formation.
    for local in range(8):
        source = player * 8 + local
        if not _fe_maneuver_source_legal(self, state, player, source):
            continue
        front = local >> 1
        rank = local & 1
        if front > 0:
            dest = slot_index(player, front - 1, rank)
            if (
                _fe_maneuver_destination_legal(self, state, dest)
                and _fe_maneuver_allowed_by_continuous(
                    self, state, player, source, dest
                )
            ):
                n = _append_action(
                    actions,
                    n,
                    encode_action(TYPE_MANEUVER, -1, source, dest, player),
                )
        if front < 3:
            dest = slot_index(player, front + 1, rank)
            if (
                _fe_maneuver_destination_legal(self, state, dest)
                and _fe_maneuver_allowed_by_continuous(
                    self, state, player, source, dest
                )
            ):
                n = _append_action(
                    actions,
                    n,
                    encode_action(TYPE_MANEUVER, -1, source, dest, player),
                )

    available = state.command[player]
    kept = 0
    for i in range(n):
        action = actions[i]
        if _fe_command_cost_fast(self, state, action) <= available:
            actions[kept] = action
            kept += 1
    n = kept
    n = _fe_filter_operation_constraints(
        self, state, player, actions, n, &constraint_enforced
    )

    can_pass = (
        state.operations_this_battle[0] > 0
        and state.operations_this_battle[1] > 0
    )
    if (can_pass and not constraint_enforced) or n == 0:
        for i in range(n, 0, -1):
            actions[i] = actions[i - 1]
        actions[0] = encode_action(TYPE_PASS, -1, -1, -1, 0)
        n += 1

    return n

cdef list _fe_legal_actions(FastEngine self, FastState state):
    cdef uint64_t actions[MAX_ACTIONS]
    cdef int n = _fe_legal_actions_into(self, state, &actions[0])
    cdef int i
    return [actions[i] for i in range(n)]
