cdef inline bint _fe_opponent_blocks_card_move_into_front(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    # V2 has no generic movement lock. Any future lock must be represented by
    # an explicit compiled mechanic rather than a hidden role rule.
    return False


cdef inline bint _fe_card_move_destination_legal(
    FastEngine self,
    FastState state,
    int controller,
    int source,
    int dest,
) noexcept:
    cdef int force = state.force[source]
    cdef int owner = owner_from_slot(source)
    if force < 0:
        return False
    if not front_is_active(state.battle, front_from_slot(source)):
        return False
    if owner_from_slot(dest) != owner:
        return False
    if not front_is_active(state.battle, front_from_slot(dest)):
        return False
    if (
        state.force[dest] >= 0
        or state.bond[dest] >= 0
        or state.name[dest] >= 0
    ):
        return False
    # Allowed-row restrictions are hard occupancy restrictions and therefore
    # apply to card-effect MOVE as well as ordinary Maneuver.
    if not _v2_force_rank_allowed(self, force, rank_from_slot(dest)):
        return False
    return True

cdef inline bint _fe_player_has_empty_front(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    cdef int front, rank
    cdef bint occupied
    for front in range(FRONT_COUNT):
        if not front_is_active(state.battle, front):
            continue
        occupied = False
        for rank in range(RANK_COUNT):
            if state.force[slot_index(player, front, rank)] >= 0:
                occupied = True
                break
        if not occupied:
            return True
    return False

cdef inline bint _fe_front_has_named_formation(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int rank
    for rank in range(RANK_COUNT):
        if _fe_slot_complete(self, state, slot_index(player, front, rank)):
            return True
    return False

cdef inline bint _fe_adjacent_hero_formation(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int local = local_slot(slot)
    cdef int front = local // RANK_COUNT
    cdef int rank = local % RANK_COUNT
    cdef int adjacent, force, name
    if front > 0:
        adjacent = slot_index(player, front - 1, rank)
        force = state.force[adjacent]
        name = state.name[adjacent]
        if force >= 0 and (
            self.hero[force]
            or (name >= 0 and self.hero[name])
        ):
            return True
    if front < FRONT_COUNT - 1:
        adjacent = slot_index(player, front + 1, rank)
        force = state.force[adjacent]
        name = state.name[adjacent]
        if force >= 0 and (
            self.hero[force]
            or (name >= 0 and self.hero[name])
        ):
            return True
    if rank > RANK_FRONT:
        adjacent = slot_index(player, front, rank - 1)
        force = state.force[adjacent]
        name = state.name[adjacent]
        if force >= 0 and (self.hero[force] or (name >= 0 and self.hero[name])):
            return True
    if rank < RANK_REAR:
        adjacent = slot_index(player, front, rank + 1)
        force = state.force[adjacent]
        name = state.name[adjacent]
        if force >= 0 and (self.hero[force] or (name >= 0 and self.hero[name])):
            return True
    return False

cdef inline bint _fe_maneuver_source_legal(
    FastEngine self,
    FastState state,
    int player,
    int slot,
) noexcept:
    cdef int force
    if not front_is_active(state.battle, front_from_slot(slot)):
        return False
    force = state.force[slot]
    if force < 0:
        return False
    if state.exhausted[slot] and not _v2_force_is_tireless(
        self, state, slot
    ):
        return False
    return _v2_slot_named(state, slot) or _v2_force_is_mobile(
        self, state, slot
    )


cdef inline bint _fe_maneuver_destination_legal(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    return front_is_active(state.battle, front_from_slot(slot))

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
        state.constraint_direction[i] = DIRECTION_NONE
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
    int direction=DIRECTION_NONE,
    int source_slot=-1,
    int activate_turn=0,
    int flags=CONSTRAINT_EXPIRES_AFTER_OPERATION,
) except *:
    cdef int i = state.constraint_len
    if i >= MAX_CONSTRAINTS:
        raise RuntimeError("Native Action-constraint capacity exceeded")
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
    cdef int card
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int selected_front
    cdef uint32_t extra = action_extra(action)
    if front < 0:
        return False
    if kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME:
        return pos >= 0 and front_from_slot(pos) == front
    if kind == TYPE_TACTIC or kind == TYPE_ORDER:
        if pos >= 0 and front_from_slot(pos) == front:
            return True
        if dest >= 0 and front_from_slot(dest) == front:
            return True
        selected_front = <int>(extra & V2_PLAY_FRONT_MASK) - 1
        return selected_front == front
    if kind == TYPE_ABILITY:
        # Formation abilities affect their source Front. Narrative abilities
        # have no board-position source; their effect-specific choices are
        # resolved as forced substeps after the Action.
        if extra & V2_ABILITY_NARRATIVE_FLAG:
            return True
        return pos >= 0 and front_from_slot(pos) == front
    if kind == TYPE_MANEUVER:
        return (
            (pos >= 0 and front_from_slot(pos) == front)
            or (dest >= 0 and front_from_slot(dest) == front)
        )
    if kind == TYPE_NARRATIVE:
        return (
            (pos >= 0 and front_from_slot(pos) == front)
            or (dest >= 0 and front_from_slot(dest) == front)
        )
    if kind == TYPE_ONGOING_NARRATIVE:
        card = action_card(action)
        return (
            card >= 0
            and self.narrative_choice_kind[card] == NARRATIVE_CHOICE_FRONT
            and bool(extra & (<uint32_t>1 << front))
        )
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
    cdef int force = state.force[source]
    cdef int swapped_force = state.force[dest]
    if force < 0:
        return False
    if owner_from_slot(source) != player or owner_from_slot(dest) != player:
        return False
    if not _v2_force_rank_allowed(
        self, force, rank_from_slot(dest)
    ):
        return False
    # A Maneuver may swap with another own occupied position. If the target
    # contains a Force, that Force must also be legal in the source row.
    if (
        swapped_force >= 0
        and not _v2_force_rank_allowed(
            self, swapped_force, rank_from_slot(source)
        )
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
    return True


cdef bint _fe_any_maneuver_in_direction(
    FastEngine self,
    FastState state,
    int player,
    int direction,
) noexcept:
    cdef int local, source, front, rank, dest
    for local in range(POSITIONS_PER_PLAYER):
        source = player * POSITIONS_PER_PLAYER + local
        if not _fe_maneuver_source_legal(self, state, player, source):
            continue
        front = local // RANK_COUNT
        rank = local % RANK_COUNT
        if direction == DIRECTION_LEFT:
            if front == 0:
                continue
            dest = slot_index(player, front - 1, rank)
        else:
            if front == LAST_FRONT_INDEX:
                continue
            dest = slot_index(player, front + 1, rank)
        if (
            _fe_maneuver_destination_legal(self, state, dest)
            and _fe_basic_maneuver_locks_allow(
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
    return _fe_basic_maneuver_locks_allow(
        self, state, player, source, dest
    )

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
    if state.constraint_len == 0:
        return n
    memset(satisfiable, 0, sizeof(satisfiable))

    for j in range(state.constraint_len):
        if (
            state.constraint_player[j] != player
            or state.constraint_activate_turn[j] == CONSTRAINT_ACTIVATE_NEXT_TURN
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
    uint32_t source_mask=0,
    uint32_t dest_mask=0,
    int flags=0,
    int command_source=-1,
) except *:
    cdef int i = state.pending_len
    cdef int j
    cdef list queued_kinds
    if i >= MAX_PENDING_EFFECTS:
        queued_kinds = []
        for j in range(state.pending_len):
            queued_kinds.append(int(state.pending_kind[j]))
        raise RuntimeError(
            "Pending card-effect capacity exceeded: "
            f"battle={state.battle} turn={state.turn_number} "
            f"attempted_kind={kind} player={player} "
            f"queued_kinds={queued_kinds}"
        )
    state.pending_kind[i] = kind
    state.pending_player[i] = player
    state.pending_card[i] = card
    state.pending_command_source[i] = command_source
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
        state.pending_command_source[i - 1] = state.pending_command_source[i]
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
        state.force[slot] < 0
        and state.bond[slot] < 0
        and state.name[slot] < 0
    )

cdef int _fe_legal_pending_effect_actions(
    FastEngine self,
    FastState state,
    uint64_t* actions,
) except -1:
    cdef int n = 0
    cdef int kind, player, source, dest, front, rank, card, i, j
    cdef int option, source2, steps, mode, effect_index
    cdef uint32_t source_mask, dest_mask, target_mask
    cdef uint8_t flags
    cdef V2EffectSpec* v2_effect
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

    if kind == EFFECT_V2_TARGET:
        v2_effect = _v2_pending_effect(self, state)
        source = state.pending_source[0]

        if (
            v2_effect.op == V2_OP_MOVE
            and v2_effect.target == V2_TARGET_SELF
        ):
            steps = v2_effect.steps if v2_effect.steps > 0 else 1
            if source >= 0 and state.force[source] >= 0:
                for dest in range(
                    player * POSITIONS_PER_PLAYER,
                    player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
                ):
                    if dest == source:
                        continue
                    if (
                        abs(front_from_slot(dest) - front_from_slot(source))
                        + abs(rank_from_slot(dest) - rank_from_slot(source))
                        > steps
                    ):
                        continue
                    if _fe_card_move_destination_legal(
                        self, state, player, source, dest
                    ):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_EFFECT, -1, source, dest, player, kind
                            ),
                        )

        elif (
            v2_effect.op == V2_OP_SWAP
            and v2_effect.target
            == V2_TARGET_FRIENDLY_PAIR_SAME_FRONT_WITH_CLASS
        ):
            target_mask = _v2_target_mask(
                self, state, player, source, v2_effect
            )
            for source2 in range(
                player * POSITIONS_PER_PLAYER,
                player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
            ):
                if not (target_mask & (<uint32_t>1 << source2)):
                    continue
                for dest in range(source2 + 1, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
                    if not (target_mask & (<uint32_t>1 << dest)):
                        continue
                    if (
                        front_from_slot(source2) == front_from_slot(dest)
                        and abs(rank_from_slot(source2) - rank_from_slot(dest)) == 1
                        and _fe_basic_maneuver_locks_allow(
                            self, state, player, source2, dest
                        )
                    ):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_EFFECT, -1, source2, dest, player, kind
                            ),
                        )

        elif v2_effect.op == V2_OP_CHOOSE_STRENGTH_TARGETS:
            target_mask = _v2_target_mask(
                self, state, player, source, v2_effect
            )
            # "Up to two" includes choosing none.
            n = _append_action(
                actions, n,
                encode_action(TYPE_EFFECT, -1, -1, -1, player, kind),
            )
            for source2 in range(SLOT_COUNT):
                if not (target_mask & (<uint32_t>1 << source2)):
                    continue
                n = _append_action(
                    actions, n,
                    encode_action(
                        TYPE_EFFECT, -1, source2, -1, player, kind
                    ),
                )
                for dest in range(source2 + 1, SLOT_COUNT):
                    if target_mask & (<uint32_t>1 << dest):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_EFFECT, -1, source2, dest, player, kind
                            ),
                        )

        elif v2_effect.op == V2_OP_CHOOSE_CLASS_STRENGTH:
            if source >= 0:
                target_mask = _v2_target_mask(
                    self, state, player, source, v2_effect
                )
                for i in range(18):
                    for dest in range(SLOT_COUNT):
                        if (
                            target_mask & (<uint32_t>1 << dest)
                            and _v2_slot_class_mask(self, state, dest)
                            & (<uint32_t>1 << i)
                        ):
                            n = _append_action(
                                actions,
                                n,
                                encode_action(
                                    TYPE_EFFECT,
                                    -1,
                                    -1,
                                    -1,
                                    player,
                                    kind
                                    | ((i + 1) << V2_EFFECT_OPTION_SHIFT),
                                ),
                            )
                            break

        elif (
            v2_effect.op == V2_OP_TAX
            and v2_effect.front_mode == V2_FRONT_CHOOSE_ACTIVE
        ):
            for front in range(FRONT_COUNT):
                if front_is_active(state.battle, front):
                    n = _append_action(
                        actions,
                        n,
                        encode_action(
                            TYPE_EFFECT,
                            -1,
                            -1,
                            -1,
                            player,
                            kind
                            | ((front + 1) << V2_EFFECT_OPTION_SHIFT),
                        ),
                    )

        elif v2_effect.op == V2_OP_ATTACH_PREPARED:
            target_mask = _v2_target_mask(
                self, state, player, source, v2_effect
            )
            for source2 in range(
                player * POSITIONS_PER_PLAYER,
                player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
            ):
                if not (target_mask & (<uint32_t>1 << source2)):
                    continue
                if state.bond[source2] >= 0:
                    card = state.bond[source2]
                    for dest in range(
                        player * POSITIONS_PER_PLAYER,
                        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
                    ):
                        if (
                            state.force[dest] >= 0
                            and state.bond[dest] < 0
                            and front_from_slot(dest) == front_from_slot(source2)
                        ):
                            n = _append_action(
                                actions, n,
                                encode_action(
                                    TYPE_EFFECT, card, source2, dest, player, kind
                                ),
                            )
                if state.name[source2] >= 0:
                    card = state.name[source2]
                    for dest in range(
                        player * POSITIONS_PER_PLAYER,
                        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
                    ):
                        if (
                            state.force[dest] >= 0
                            and state.name[dest] < 0
                            and front_from_slot(dest) == front_from_slot(source2)
                        ):
                            n = _append_action(
                                actions, n,
                                encode_action(
                                    TYPE_EFFECT, card, source2, dest, player, kind
                                ),
                            )

        elif v2_effect.op == V2_OP_PLAY_BOND_FROM_HAND:
            target_mask = _v2_target_mask(
                self, state, player, source, v2_effect
            )
            for card in range(self.n_cards):
                if (
                    state.hand[player][card] == 0
                    or self.card_type[card] != CARD_BOND
                ):
                    continue
                for dest in range(SLOT_COUNT):
                    if (
                        target_mask & (<uint32_t>1 << dest)
                        and state.force[dest] >= 0
                        and state.bond[dest] < 0
                    ):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_EFFECT, card, source, dest, player, kind
                            ),
                        )

        elif v2_effect.op == V2_OP_SET_STRATAGEM_FROM_HAND:
            if state.stratagem[player] < 0:
                for card in range(self.n_cards):
                    if (
                        state.hand[player][card] > 0
                        and self.card_type[card] == CARD_STRATAGEM
                    ):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_EFFECT, card, source, -1, player, kind
                            ),
                        )

        elif v2_effect.op == V2_OP_RECOVER:
            for i in range(state.discard_len[player]):
                card = state.discard[player][i]
                if (
                    v2_effect.card_type_mask == 0
                    or _v2_card_type_mask_matches(
                        v2_effect.card_type_mask,
                        _v2_card_type_bit_for_play(
                            self,
                            (
                                TYPE_BOND
                                if self.card_type[card] == CARD_BOND
                                else TYPE_NARRATIVE
                                if self.card_type[card] == CARD_NARRATIVE
                                else TYPE_FORCE
                            ),
                            card,
                        ),
                    )
                ):
                    n = _append_action(
                        actions, n,
                        encode_action(
                            TYPE_EFFECT, card, -1, -1, player, kind
                        ),
                    )

        elif v2_effect.op == V2_OP_DISCARD_DRAW:
            for card in range(self.n_cards):
                if state.hand[player][card] > 0:
                    n = _append_action(
                        actions, n,
                        encode_action(
                            TYPE_EFFECT, card, -1, -1, player, kind
                        ),
                    )

        elif v2_effect.op in (
            V2_OP_REORDER_TOP,
            V2_OP_PICK_TOP_TO_HAND_BOTTOM_REST,
        ):
            # Three cards have six possible orders / pick+order outcomes.
            for option in range(1, 7):
                n = _append_action(
                    actions, n,
                    encode_action(
                        TYPE_EFFECT,
                        -1,
                        -1,
                        -1,
                        player,
                        kind | (option << V2_EFFECT_OPTION_SHIFT),
                    ),
                )

        elif v2_effect.op in (
            V2_OP_RETURN_PREPARED,
            V2_OP_PREPARED_PAY_OR_RETURN,
            V2_OP_SUPPRESS_COMPONENT,
        ):
            target_mask = _v2_target_mask(
                self, state, player, source, v2_effect
            )
            for dest in range(SLOT_COUNT):
                if not (target_mask & (<uint32_t>1 << dest)):
                    continue
                if state.bond[dest] >= 0:
                    n = _append_action(
                        actions, n,
                        encode_action(
                            TYPE_EFFECT,
                            state.bond[dest],
                            -1,
                            dest,
                            player,
                            kind
                            | (V2_OPTION_BOND << V2_EFFECT_OPTION_SHIFT),
                        ),
                    )
                if state.name[dest] >= 0:
                    n = _append_action(
                        actions, n,
                        encode_action(
                            TYPE_EFFECT,
                            state.name[dest],
                            -1,
                            dest,
                            player,
                            kind
                            | (V2_OPTION_NAME << V2_EFFECT_OPTION_SHIFT),
                        ),
                    )

        elif v2_effect.target != V2_TARGET_NONE:
            target_mask = _v2_target_mask(
                self, state, player, source, v2_effect
            )
            for dest in range(SLOT_COUNT):
                if target_mask & (<uint32_t>1 << dest):
                    n = _append_action(
                        actions, n,
                        encode_action(
                            TYPE_EFFECT, -1, source, dest, player, kind
                        ),
                    )

        else:
            # Automatic effect: expose exactly one forced non-Action
            # transition so search/UI state remains explicit and resumable.
            n = _append_action(
                actions, n,
                encode_action(TYPE_EFFECT, -1, source, -1, player, kind),
            )

    elif kind == EFFECT_FREE_MANEUVER:
        for source in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
            if not (source_mask & (1 << source)):
                continue
            if state.maneuvered_in_operation[source]:
                continue
            if flags & EFFECT_ALLOW_UNNAMED:
                if (
                    state.force[source] < 0
                    or self.immobile_force[state.force[source]]
                    or state.exhausted[source]
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
                if (
                    _fe_maneuver_destination_legal(self, state, dest)
                    and _fe_maneuver_allowed_by_continuous(
                        self, state, player, source, dest
                    )
                ):
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
            if front < FRONT_COUNT - 1:
                dest = slot_index(player, front + 1, rank)
                if (
                    _fe_maneuver_destination_legal(self, state, dest)
                    and _fe_maneuver_allowed_by_continuous(
                        self, state, player, source, dest
                    )
                ):
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
            if rank > RANK_FRONT:
                dest = slot_index(player, front, rank - 1)
                if _fe_maneuver_destination_legal(self, state, dest) and _fe_maneuver_allowed_by_continuous(self, state, player, source, dest):
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
            if rank < RANK_REAR:
                dest = slot_index(player, front, rank + 1)
                if _fe_maneuver_destination_legal(self, state, dest) and _fe_maneuver_allowed_by_continuous(self, state, player, source, dest):
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_MOVE:
        for source in range(SLOT_COUNT):
            if not (source_mask & (1 << source)) or state.force[source] < 0:
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
        for source in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
            if not (source_mask & (1 << source)) or state.force[source] < 0:
                continue
            for dest in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
                if dest == source:
                    continue
                if source_mask == dest_mask and dest < source:
                    continue
                if not (dest_mask & (1 << dest)) or state.force[dest] < 0:
                    continue
                if flags & EFFECT_ADJACENT_PAIR:
                    if (
                        abs(front_from_slot(source) - front_from_slot(dest))
                        + abs(rank_from_slot(source) - rank_from_slot(dest))
                        != 1
                    ):
                        continue
                if flags & EFFECT_SAME_FRONT_PAIR:
                    if front_from_slot(source) != front_from_slot(dest) or rank_from_slot(source) == rank_from_slot(dest):
                        continue
                if self.immobile_force[state.force[source]] or self.immobile_force[state.force[dest]]:
                    continue
                if self.cannot_swap_target[state.force[source]] or self.cannot_swap_target[state.force[dest]]:
                    continue
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_RECOVER:
        for i in range(state.discard_len[player]):
            card = state.discard[player][i]
            if state.pending_aux[0] == CARD_BOND and self.card_type[card] != CARD_BOND:
                continue
            if state.pending_aux[0] == CARD_NARRATIVE and self.card_type[card] != CARD_NARRATIVE:
                continue
            n = _append_action(actions, n, encode_action(TYPE_EFFECT, card, -1, -1, player, kind))
    elif kind == EFFECT_FRONT_CONTRIBUTION:
        source = state.pending_source[0]
        if source >= 0 and state.force[source] >= 0:
            front = front_from_slot(source)
            for dest in range(max(0, front - 1), min(3, front + 1) + 1):
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_SUPPRESS:
        for dest in range(SLOT_COUNT):
            if dest_mask & (1 << dest) and state.force[dest] >= 0:
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, -1, dest, player, kind))
    elif kind == EFFECT_SACRIFICE:
        source = state.pending_source[0]
        if source >= 0 and state.force[source] >= 0:
            for dest in range(SLOT_COUNT):
                if dest_mask & (1 << dest) and state.force[dest] >= 0:
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_INTERCEPT:
        for source in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
            if source_mask & (1 << source) and _fe_slot_complete(self, state, source):
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, -1, player, kind))
    elif kind == EFFECT_RETREAT:
        source = state.pending_source[0]
        dest = state.pending_aux[0]
        if source >= 0 and dest >= 0 and _fe_slot_complete(self, state, source) and _fe_slot_is_empty(self, state, dest):
            n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))
    elif kind == EFFECT_PROTECT_RETREAT:
        source = state.pending_source[0]
        if source >= 0 and state.force[source] >= 0:
            n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, state.pending_aux[0], player, kind))
    elif kind == EFFECT_TRANSFER_COMPONENT:
        for source in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
            if not (source_mask & (1 << source)):
                continue
            for dest in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
                if state.pending_aux[0] >= 0:
                    if dest != state.pending_aux[0]:
                        continue
                elif not (dest_mask & (1 << dest)):
                    continue
                if state.bond[source] >= 0 and state.bond[dest] < 0:
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, state.bond[source], source, dest, player, kind))
                if state.name[source] >= 0 and state.name[dest] < 0:
                    n = _append_action(actions, n, encode_action(TYPE_EFFECT, state.name[source], source, dest, player, kind))
    elif kind == EFFECT_SUCCESSION:
        source = state.pending_source[0]
        for dest in range(player * POSITIONS_PER_PLAYER, player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
            if dest_mask & (1 << dest) and state.force[dest] >= 0 and state.bond[dest] >= 0 and state.name[dest] < 0:
                n = _append_action(actions, n, encode_action(TYPE_EFFECT, -1, source, dest, player, kind))

    # A mandatory choice can become impossible after it was queued. The most
    # important case is multiple recover-from-discard triggers queued by one
    # transition: an earlier recovery can consume the last eligible card before
    # a later recovery reaches the front of the queue. Resolving that later
    # effect as a forced no-op is the rules-correct "do as much as possible"
    # outcome and keeps every non-terminal state actionable.
    if n == 0:
        n = _append_action(
            actions,
            n,
            encode_action(TYPE_EFFECT, -1, -1, -1, player, kind),
        )
    return n

cdef inline bint _fe_action_uses_only_active_fronts(
    FastEngine self,
    FastState state,
    uint64_t action,
) noexcept:
    """Reject any action/effect that selects or moves through an inactive Front."""
    cdef int kind = action_kind(action)
    cdef int card = action_card(action)
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int choice, slot, front, target_front
    cdef uint32_t extra = action_extra(action)
    cdef uint8_t active = active_front_mask_for_battle(state.battle)

    if kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME:
        if pos >= 0 and not (active & (1 << front_from_slot(pos))):
            return False
        if dest >= 0 and not (active & (1 << front_from_slot(dest))):
            return False
        return True

    if kind == TYPE_TACTIC or kind == TYPE_ORDER:
        if pos >= 0 and not (active & (1 << front_from_slot(pos))):
            return False
        if dest >= 0 and not (active & (1 << front_from_slot(dest))):
            return False
        front = <int>(extra & V2_PLAY_FRONT_MASK) - 1
        if front >= 0 and not (active & (1 << front)):
            return False
        return True

    if kind == TYPE_ABILITY:
        if extra & V2_ABILITY_NARRATIVE_FLAG:
            return True
        return (
            pos >= 0
            and bool(active & (1 << front_from_slot(pos)))
        )

    if kind == TYPE_MANEUVER:
        return (
            pos >= 0
            and dest >= 0
            and bool(active & (1 << front_from_slot(pos)))
            and bool(active & (1 << front_from_slot(dest)))
        )

    if kind == TYPE_NARRATIVE:
        if pos >= 0 and not (active & (1 << front_from_slot(pos))):
            return False
        if dest >= 0 and not (active & (1 << front_from_slot(dest))):
            return False
        return True

    if kind == TYPE_ONGOING_NARRATIVE:
        if card < 0:
            return True
        choice = self.narrative_choice_kind[card]
        if choice == NARRATIVE_CHOICE_FRONT:
            return (extra & <uint32_t>(~active & FRONT_MASK)) == 0
        if dest >= 0:
            return bool(active & (1 << front_from_slot(dest)))
        return True

    if kind == TYPE_STRATAGEM:
        if card < 0:
            return True
        choice = self.strat_choice_kind[card]
        if (
            choice == STRAT_CHOICE_FRONT
            or choice == STRAT_CHOICE_ADJACENT_FRONTS
            or choice == STRAT_CHOICE_EDGE_FRONT
        ):
            return pos < 0 or (pos & (~active & FRONT_MASK)) == 0
        if choice == STRAT_CHOICE_WHEEL:
            for slot in range(SLOT_COUNT):
                if not (extra & (<uint32_t>1 << slot)):
                    continue
                front = front_from_slot(slot)
                if not (active & (1 << front)):
                    return False
                target_front = front - 1 if dest == 0 else front + 1
                if (
                    target_front < 0
                    or target_front >= FRONT_COUNT
                    or not (active & (1 << target_front))
                ):
                    return False
        elif choice == STRAT_CHOICE_RESERVES:
            for slot in range(SLOT_COUNT):
                if (
                    extra & (<uint32_t>1 << slot)
                    and not (active & (1 << front_from_slot(slot)))
                ):
                    return False
        return True

    if kind == TYPE_EFFECT:
        choice = <int>(extra & V2_EFFECT_KIND_MASK)
        if pos >= 0 and not (active & (1 << front_from_slot(pos))):
            return False
        if dest >= 0:
            if choice == EFFECT_FRONT_CONTRIBUTION:
                if dest >= FRONT_COUNT or not (active & (1 << dest)):
                    return False
            elif not (active & (1 << front_from_slot(dest))):
                return False
        return True

    return True


cdef int _fe_legal_actions_into(
    FastEngine self,
    FastState state,
    uint64_t* actions,
) except -1:
    cdef int n = 0
    cdef int player, card, second_card, slot, local, front, rank, source, dest, req, opponent, effect
    cdef int i, kept, available, narrative_slot, choice, direction
    cdef int mode, effect_index, component_option, ix
    cdef uint32_t eligible_mask, subset, target_mask
    cdef uint64_t action
    cdef V2EffectSpec* v2_effect
    cdef bint constraint_enforced = False

    if state.phase == PHASE_COMPLETE:
        return 0

    player = state.active_player

    # Hand-limit overflow must be cleaned up before play continues.
    # This substep is not one of the turn's Actions.
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
        n = _fe_legal_pending_effect_actions(self, state, actions)
        kept = 0
        for i in range(n):
            if _fe_action_uses_only_active_fronts(self, state, actions[i]):
                actions[kept] = actions[i]
                kept += 1
        return kept

    opponent = other_player(player)

    for card in range(self.n_cards):
        if state.hand[player][card] == 0:
            continue

        if self.card_type[card] == CARD_FORCE:
            for local in range(POSITIONS_PER_PLAYER):
                slot = player * POSITIONS_PER_PLAYER + local
                rank = local % RANK_COUNT
                if (
                    state.force[slot] < 0
                    and _v2_force_rank_allowed(self, card, rank)
                ):
                    n = _append_action(
                        actions, n,
                        encode_action(TYPE_FORCE, card, slot, -1, player),
                    )

        elif self.card_type[card] == CARD_HERO:
            if (
                self.hero_force_play_limit_per_battle > 0
                and not (state.hero_used[player] & 1)
            ):
                for local in range(POSITIONS_PER_PLAYER):
                    slot = player * POSITIONS_PER_PLAYER + local
                    rank = local % RANK_COUNT
                    if (
                        state.force[slot] < 0
                        and _v2_force_rank_allowed(self, card, rank)
                    ):
                        n = _append_action(
                            actions, n,
                            encode_action(TYPE_FORCE, card, slot, -1, player),
                        )
            if (
                self.hero_name_play_limit_per_battle > 0
                and not (state.hero_used[player] & 2)
            ):
                for local in range(POSITIONS_PER_PLAYER):
                    slot = player * POSITIONS_PER_PLAYER + local
                    if state.name[slot] < 0:
                        n = _append_action(
                            actions, n,
                            encode_action(TYPE_NAME, card, slot, -1, player),
                        )

        elif self.card_type[card] == CARD_BOND:
            for local in range(POSITIONS_PER_PLAYER):
                slot = player * POSITIONS_PER_PLAYER + local
                if state.bond[slot] < 0:
                    n = _append_action(
                        actions, n,
                        encode_action(TYPE_BOND, card, slot, -1, player),
                    )

        elif self.card_type[card] == CARD_NAME:
            for local in range(POSITIONS_PER_PLAYER):
                slot = player * POSITIONS_PER_PLAYER + local
                if state.name[slot] < 0:
                    n = _append_action(
                        actions, n,
                        encode_action(TYPE_NAME, card, slot, -1, player),
                    )

        elif self.card_type[card] == CARD_NARRATIVE:
            for narrative_slot in range(self.ongoing_narrative_limit):
                if (
                    state.narrative[
                        player * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
                    ] < 0
                ):
                    n = _append_action(
                        actions, n,
                        encode_action(
                            TYPE_ONGOING_NARRATIVE,
                            card,
                            narrative_slot,
                            -1,
                            player,
                        ),
                    )
                    break

        elif self.card_type[card] == CARD_STRATAGEM:
            if (
                state.stratagem_used[player]
                < self.stratagem_play_limit_per_battle
                and state.stratagem[player] < 0
            ):
                for front in range(FRONT_COUNT):
                    if front_is_active(state.battle, front):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_STRATAGEM,
                                card,
                                1 << front,
                                -1,
                                player,
                            ),
                        )

        elif self.card_type[card] == CARD_TACTIC:
            if self.v2_effect_count[card][V2_MODE_DEFAULT] == 0:
                continue
            v2_effect = &self.v2_effects[card][V2_MODE_DEFAULT][0]
            if not _v2_effect_can_resolve(
                self, state, player, -1, v2_effect
            ):
                continue
            if (
                v2_effect.op == V2_OP_TAX
                and v2_effect.front_mode == V2_FRONT_CHOOSE_ACTIVE
            ):
                for front in range(FRONT_COUNT):
                    if front_is_active(state.battle, front):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_TACTIC,
                                card,
                                -1,
                                -1,
                                player,
                                <uint32_t>(front + 1),
                            ),
                        )
            elif v2_effect.op in (
                V2_OP_RETURN_PREPARED,
                V2_OP_PREPARED_PAY_OR_RETURN,
            ):
                target_mask = _v2_target_mask(
                    self, state, player, -1, v2_effect
                )
                for dest in range(SLOT_COUNT):
                    if not (target_mask & (<uint32_t>1 << dest)):
                        continue
                    if state.bond[dest] >= 0:
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_TACTIC,
                                card,
                                -1,
                                dest,
                                player,
                                <uint32_t>(
                                    V2_OPTION_BOND << V2_PLAY_COMPONENT_SHIFT
                                ),
                            ),
                        )
                    if state.name[dest] >= 0:
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_TACTIC,
                                card,
                                -1,
                                dest,
                                player,
                                <uint32_t>(
                                    V2_OPTION_NAME << V2_PLAY_COMPONENT_SHIFT
                                ),
                            ),
                        )
            elif v2_effect.target != V2_TARGET_NONE:
                target_mask = _v2_target_mask(
                    self, state, player, -1, v2_effect
                )
                for dest in range(SLOT_COUNT):
                    if target_mask & (<uint32_t>1 << dest):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_TACTIC, card, -1, dest, player
                            ),
                        )
            else:
                n = _append_action(
                    actions, n,
                    encode_action(TYPE_TACTIC, card, -1, -1, player),
                )

        elif self.card_type[card] == CARD_ORDER:
            if self.v2_effect_count[card][V2_MODE_DEFAULT] == 0:
                continue
            v2_effect = &self.v2_effects[card][V2_MODE_DEFAULT][0]
            if not _v2_effect_can_resolve(
                self, state, player, -1, v2_effect
            ):
                continue
            if (
                v2_effect.op == V2_OP_SWAP
                and v2_effect.target
                == V2_TARGET_FRIENDLY_PAIR_SAME_FRONT_WITH_CLASS
            ):
                target_mask = _v2_target_mask(
                    self, state, player, -1, v2_effect
                )
                for source in range(
                    player * POSITIONS_PER_PLAYER,
                    player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
                ):
                    if not (target_mask & (<uint32_t>1 << source)):
                        continue
                    for dest in range(
                        source + 1,
                        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
                    ):
                        if not (target_mask & (<uint32_t>1 << dest)):
                            continue
                        if (
                            front_from_slot(source) == front_from_slot(dest)
                            and abs(
                                rank_from_slot(source) - rank_from_slot(dest)
                            ) == 1
                            and _fe_basic_maneuver_locks_allow(
                                self, state, player, source, dest
                            )
                        ):
                            n = _append_action(
                                actions, n,
                                encode_action(
                                    TYPE_ORDER,
                                    card,
                                    source,
                                    dest,
                                    player,
                                ),
                            )
            elif v2_effect.target != V2_TARGET_NONE:
                target_mask = _v2_target_mask(
                    self, state, player, -1, v2_effect
                )
                for dest in range(SLOT_COUNT):
                    if target_mask & (<uint32_t>1 << dest):
                        n = _append_action(
                            actions, n,
                            encode_action(
                                TYPE_ORDER, card, -1, dest, player
                            ),
                        )
            else:
                n = _append_action(
                    actions, n,
                    encode_action(TYPE_ORDER, card, -1, -1, player),
                )

    # ACTION abilities on Forces and Names are real Actions. Their follow-up
    # choices resolve through the V2 pending-effect layer.
    for local in range(POSITIONS_PER_PLAYER):
        slot = player * POSITIONS_PER_PLAYER + local
        if state.force[slot] < 0:
            continue

        card = state.force[slot]
        mode = _v2_mode_for_force(self, card)
        for effect_index in range(self.v2_effect_count[card][mode]):
            v2_effect = &self.v2_effects[card][mode][effect_index]
            if v2_effect.timing != V2_TIMING_ACTION:
                continue
            if state.suppression_mask[slot] & (
                SUPPRESS_ACTION_TURN | SUPPRESS_ACTION_BATTLE
            ):
                continue
            if (
                v2_effect.once_per_battle
                and (
                    state.force_ability_used[slot]
                    or state.suppression_mask[slot]
                    & SUPPRESS_LIMITED_BATTLE
                )
            ):
                continue
            if not _v2_effect_can_resolve(
                self, state, player, slot, v2_effect
            ):
                continue
            n = _append_action(
                actions, n,
                encode_action(
                    TYPE_ABILITY,
                    card,
                    slot,
                    -1,
                    player,
                    <uint32_t>(
                        _v2_pending_aux(mode, effect_index)
                    ),
                ),
            )

        card = state.name[slot]
        if (
            card >= 0
            and not (
                state.suppression_mask[slot] & SUPPRESS_NAME_TEXT
            )
        ):
            mode = _v2_mode_for_name(self, card)
            for effect_index in range(self.v2_effect_count[card][mode]):
                v2_effect = &self.v2_effects[card][mode][effect_index]
                if v2_effect.timing != V2_TIMING_ACTION:
                    continue
                if state.suppression_mask[slot] & (
                    SUPPRESS_ACTION_TURN | SUPPRESS_ACTION_BATTLE
                ):
                    continue
                if (
                    v2_effect.once_per_battle
                    and (
                        state.name_ability_used[slot]
                        or state.suppression_mask[slot]
                        & SUPPRESS_LIMITED_BATTLE
                    )
                ):
                    continue
                if not _v2_effect_can_resolve(
                    self, state, player, slot, v2_effect
                ):
                    continue
                n = _append_action(
                    actions, n,
                    encode_action(
                        TYPE_ABILITY,
                        card,
                        slot,
                        -1,
                        player,
                        <uint32_t>(
                            _v2_pending_aux(mode, effect_index)
                        ),
                    ),
                )

    for narrative_slot in range(self.ongoing_narrative_limit):
        ix = player * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot
        card = state.narrative[ix]
        if card < 0:
            continue
        for effect_index in range(
            self.v2_effect_count[card][V2_MODE_DEFAULT]
        ):
            v2_effect = &self.v2_effects[
                card
            ][V2_MODE_DEFAULT][effect_index]
            if v2_effect.timing != V2_TIMING_ACTION:
                continue
            if (
                v2_effect.once_per_battle
                and state.narrative_used[ix]
            ):
                continue
            if not _v2_effect_can_resolve(
                self, state, player, -1, v2_effect
            ):
                continue
            n = _append_action(
                actions, n,
                encode_action(
                    TYPE_ABILITY,
                    card,
                    narrative_slot,
                    -1,
                    player,
                    <uint32_t>(
                        _v2_pending_aux(
                            V2_MODE_DEFAULT, effect_index
                        )
                        | V2_ABILITY_NARRATIVE_FLAG
                    ),
                ),
            )

    # Maneuver moves to an empty position or swaps with any own occupied
    # position, including a prepared-only Bond/Name position.
    for local in range(POSITIONS_PER_PLAYER):
        source = player * POSITIONS_PER_PLAYER + local
        if not _fe_maneuver_source_legal(self, state, player, source):
            continue
        front = local // RANK_COUNT
        rank = local % RANK_COUNT
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
        if front < FRONT_COUNT - 1:
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
        if rank > RANK_FRONT:
            dest = slot_index(player, front, rank - 1)
            if _fe_maneuver_destination_legal(self, state, dest) and _fe_maneuver_allowed_by_continuous(self, state, player, source, dest):
                n = _append_action(actions, n, encode_action(TYPE_MANEUVER, -1, source, dest, player))
        if rank < RANK_REAR:
            dest = slot_index(player, front, rank + 1)
            if _fe_maneuver_destination_legal(self, state, dest) and _fe_maneuver_allowed_by_continuous(self, state, player, source, dest):
                n = _append_action(actions, n, encode_action(TYPE_MANEUVER, -1, source, dest, player))

    # Cycling is one Action: discard any two cards, then draw one.
    if state.hand_len[player] >= 2:
        for card in range(self.n_cards):
            if state.hand[player][card] <= 0:
                continue
            for second_card in range(card, self.n_cards):
                if state.hand[player][second_card] <= 0:
                    continue
                if (
                    second_card == card
                    and state.hand[player][card] < 2
                ):
                    continue
                n = _append_action(
                    actions,
                    n,
                    encode_action(
                        TYPE_CYCLE,
                        card,
                        -1,
                        -1,
                        player,
                        <uint32_t>(second_card + 1),
                    ),
                )

    available = state.command[player]
    kept = 0
    for i in range(n):
        action = actions[i]
        if (
            _fe_action_uses_only_active_fronts(self, state, action)
            and _fe_command_cost_fast(self, state, action) <= available
        ):
            actions[kept] = action
            kept += 1
    n = kept
    n = _fe_filter_operation_constraints(
        self, state, player, actions, n, &constraint_enforced
    )

    # Pass is never voluntary. It exists only at the start of an ordinary
    # turn when no Action is legal and starts the fixed two-turn closing
    # sequence. EndTurn is separate: a player may always stop before using
    # both Actions, and a closing/no-second-Action turn ends without Passing.
    if n == 0:
        actions[0] = encode_action(
            TYPE_END_TURN
            if state.closing_turns_remaining > 0 or state.actions_this_turn > 0
            else TYPE_PASS,
            -1,
            -1,
            -1,
            player,
        )
        n = 1
    else:
        n = _append_action(
            actions,
            n,
            encode_action(TYPE_END_TURN, -1, -1, -1, player),
        )

    return n

cdef list _fe_legal_actions(FastEngine self, FastState state):
    cdef uint64_t actions[MAX_ACTIONS]
    cdef int n = _fe_legal_actions_into(self, state, &actions[0])
    cdef int i
    return [actions[i] for i in range(n)]
