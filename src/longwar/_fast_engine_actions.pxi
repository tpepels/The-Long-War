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
                    elif choice == STORY_CHOICE_NAMED_FORMATION:
                        for local in range(8):
                            slot = player * 8 + local
                            if _fe_slot_complete(self, state, slot):
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
            if _fe_maneuver_destination_legal(self, state, dest):
                n = _append_action(
                    actions,
                    n,
                    encode_action(TYPE_MANEUVER, -1, source, dest, player),
                )
        if front < 3:
            dest = slot_index(player, front + 1, rank)
            if _fe_maneuver_destination_legal(self, state, dest):
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

    can_pass = (
        state.operations_this_battle[0] > 0
        and state.operations_this_battle[1] > 0
    )
    if can_pass or n == 0:
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
