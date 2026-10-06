cdef InfoHash128 _fe_state_hash_fast(FastEngine self, FastState state) noexcept:
    """128-bit hash of all rule/search-relevant perfect-state data."""
    cdef InfoHash128 h
    cdef int p, i, card, slot, ix
    _info_hash_init(&h)
    _info_hash_feed(&h, <uint8_t>(state.phase + 1))
    _info_hash_feed_u16(&h, <uint16_t>state.battle)
    _info_hash_feed(&h, <uint8_t>(state.active_player + 1))
    _info_hash_feed(&h, <uint8_t>(state.winner + 1))
    _info_hash_feed_u32(&h, <uint32_t>state.turn_number)
    _info_hash_feed(&h, state.actions_this_turn)
    _info_hash_feed(&h, state.closing_turns_remaining)
    _info_hash_feed_u32(&h, <uint32_t>state.shuffle_seed)

    for p in range(PLAYER_COUNT):
        _info_hash_feed_u16(&h, state.deck_len[p])
        for i in range(state.deck_len[p]):
            _info_hash_feed(&h, <uint8_t>(state.deck[p][i] + 1))
        for card in range(self.n_cards):
            _info_hash_feed(&h, state.hand[p][card])
        _info_hash_feed(&h, state.hand_len[p])
        _info_hash_feed_u16(&h, state.discard_len[p])
        for i in range(state.discard_len[p]):
            _info_hash_feed(
                &h,
                <uint8_t>(state.discard[p][i] + 1),
            )
        _info_hash_feed(&h, state.passed[p])
        _info_hash_feed_u16(&h, <uint16_t>state.command[p])
        _info_hash_feed(&h, state.hero_used[p])
        _info_hash_feed_u16(
            &h,
            state.operations_this_battle[p],
        )
        _info_hash_feed(&h, state.cards_played_this_turn_front_mask[p])
        _info_hash_feed(&h, state.cards_played_this_battle_front_mask[p])
        _info_hash_feed(&h, state.narratives_played_this_battle[p])
        for card in range(self.n_cards):
            _info_hash_feed(
                &h,
                state.known_hidden[0][p][card],
            )
            _info_hash_feed(
                &h,
                state.known_hidden[1][p][card],
            )

    _info_hash_feed(&h, state.pass_len)
    for i in range(state.pass_len):
        _info_hash_feed(&h, <uint8_t>(state.pass_order[i] + 1))
    for p in range(PLAYER_COUNT):
        _info_hash_feed(&h, state.discarded_this_battle[p])

    for slot in range(SLOT_COUNT):
        _info_hash_feed(&h, <uint8_t>(state.force[slot] + 1))
        _info_hash_feed(&h, <uint8_t>(state.bond[slot] + 1))
        _info_hash_feed(&h, <uint8_t>(state.name[slot] + 1))
        _info_hash_feed(&h, state.exhausted[slot])
        _info_hash_feed_u16(
            &h,
            <uint16_t>state.temporary[slot],
        )
        _info_hash_feed(&h, state.negative_one_markers[slot])
        _info_hash_feed(&h, state.negative_two_markers[slot])
        _info_hash_feed_u16(&h, state.suppression_mask[slot])
        _info_hash_feed(&h, state.force_ability_used[slot])
        _info_hash_feed(&h, state.bond_ability_used[slot])
        _info_hash_feed(&h, state.name_ability_used[slot])
        _info_hash_feed(&h, state.name_suppression_immune[slot])
        _info_hash_feed(&h, state.maneuver_count[slot])
        _info_hash_feed(&h, state.maneuvered_in_operation[slot])

    for ix in range(NARRATIVE_COUNT):
        _info_hash_feed(&h, <uint8_t>(state.narrative[ix] + 1))
        _info_hash_feed(&h, state.narrative_front_mask[ix])
        _info_hash_feed(&h, state.narrative_used[ix])
        _info_hash_feed(&h, state.narrative_direction[ix])
        _info_hash_feed(&h, state.narrative_trigger_mask[ix])
        _info_hash_feed(&h, <uint8_t>(state.narrative_target_slot[ix] + 1))
    for p in range(PLAYER_COUNT):
        _info_hash_feed(&h, <uint8_t>(state.stratagem[p] + 1))
        _info_hash_feed(&h, state.stratagem_revealed[p])
        _info_hash_feed(&h, state.stratagem_known_to_mask[p])
        _info_hash_feed(&h, state.stratagem_front_mask[p])
        _info_hash_feed(&h, state.stratagem_direction[p])
        _info_hash_feed_u32(&h, state.stratagem_target_mask[p])
        _info_hash_feed(&h, state.stratagem_used[p])

    _info_hash_feed(&h, state.tax_len)
    for i in range(state.tax_len):
        _info_hash_feed(&h, state.tax_owner[i])
        _info_hash_feed(&h, state.tax_target_player[i])
        _info_hash_feed(&h, state.tax_front[i])
        _info_hash_feed(&h, state.tax_amount[i])
        _info_hash_feed(&h, state.tax_card_type_mask[i])
        _info_hash_feed_u32(&h, <uint32_t>state.tax_expires_turn[i])
    _info_hash_feed(&h, state.discount_len)
    for i in range(state.discount_len):
        _info_hash_feed(&h, state.discount_owner[i])
        _info_hash_feed(&h, state.discount_target_player[i])
        _info_hash_feed(&h, state.discount_slot[i])
        _info_hash_feed(&h, state.discount_amount[i])
        _info_hash_feed(&h, state.discount_minimum[i])
        _info_hash_feed(&h, state.discount_card_type_mask[i])
        _info_hash_feed_u32(&h, <uint32_t>state.discount_expires_turn[i])

    _info_hash_feed(&h, state.cleanup_pending)
    _info_hash_feed(&h, state.pending_draw_count)
    _info_hash_feed(&h, state.pending_draw_finish_operation)
    _info_hash_feed(&h, state.pending_len)
    for i in range(state.pending_len):
        _info_hash_feed(&h, state.pending_kind[i])
        _info_hash_feed(&h, <uint8_t>(state.pending_player[i] + 1))
        _info_hash_feed(&h, <uint8_t>(state.pending_card[i] + 1))
        _info_hash_feed(&h, <uint8_t>(state.pending_source[i] + 1))
        _info_hash_feed(&h, <uint8_t>(state.pending_aux[i] + 1))
        _info_hash_feed_u32(&h, state.pending_source_mask[i])
        _info_hash_feed_u32(&h, state.pending_dest_mask[i])
        _info_hash_feed(&h, state.pending_flags[i])
    _info_hash_feed(&h, state.pending_resume)
    _info_hash_feed(&h, <uint8_t>(state.pending_resume_player + 1))
    _info_hash_feed(&h, state.free_maneuver_available[0])
    _info_hash_feed(&h, state.free_maneuver_available[1])
    _info_hash_feed_u16(&h, state.player_maneuver_count[0])
    _info_hash_feed_u16(&h, state.player_maneuver_count[1])
    for slot in range(SLOT_COUNT):
        _info_hash_feed(&h, state.maneuver_direction[slot])
    _info_hash_feed(&h, state.constraint_len)
    for i in range(state.constraint_len):
        _info_hash_feed(&h, state.constraint_kind[i])
        _info_hash_feed(&h, <uint8_t>(state.constraint_player[i] + 1))
        _info_hash_feed(&h, <uint8_t>(state.constraint_source_card[i] + 1))
        _info_hash_feed(&h, <uint8_t>(state.constraint_source_owner[i] + 1))
        _info_hash_feed(&h, <uint8_t>(state.constraint_front[i] + 1))
        _info_hash_feed(&h, state.constraint_direction[i])
        _info_hash_feed(&h, <uint8_t>(state.constraint_source_slot[i] + 1))
        _info_hash_feed_u32(&h, <uint32_t>state.constraint_activate_turn[i])
        _info_hash_feed(&h, state.constraint_flags[i])
    _info_hash_feed(&h, state.resolution_stage)
    _info_hash_feed(&h, state.resolution_lost_mask[0])
    _info_hash_feed(&h, state.resolution_lost_mask[1])
    _info_hash_feed(&h, state.resolution_drive_mask[0])
    _info_hash_feed(&h, state.resolution_drive_mask[1])
    _info_hash_feed(&h, state.resolution_protected_mask[0])
    _info_hash_feed(&h, state.resolution_protected_mask[1])
    _info_hash_feed_u16(
        &h, <uint16_t>state.resolution_front_loss_command_penalty[0]
    )
    _info_hash_feed_u16(
        &h, <uint16_t>state.resolution_front_loss_command_penalty[1]
    )
    _info_hash_feed_u32(&h, state.resolution_suppressed_mask)
    _info_hash_feed(&h, state.resolution_cursor)
    _info_hash_feed(&h, <uint8_t>(state.resolution_starter + 1))
    for slot in range(SLOT_COUNT):
        _info_hash_feed(&h, <uint8_t>(state.resolution_contribution_front[slot] + 1))
    return h

cdef tuple _fe_state_hash(FastEngine self, FastState state):
    cdef InfoHash128 h = _fe_state_hash_fast(self, state)
    return (h.a, h.b)

cdef int _fe__information_state_encode(
    FastEngine self,
    FastState state,
    int player,
    unsigned char* buf,
    InfoHash128* h,
) noexcept:
    """Single canonical observable-state encoding for imperfect-info AI."""
    cdef int n=0, i, owner, slot, card, narrative_slot, narrative_count
    cdef int opponent = other_player(player)
    cdef int pending_draw = (
        state.active_player + 1
        if state.cleanup_pending
        else 0
    )

    # Binary information-key format. Bump this whenever the byte layout changes.
    # v15 adds public persistent per-Force Exhaustion state.
    # v13 widens in-progress Front-loss Command penalties to 16 bits.
    # v12 widened observable deck/discard counts to 16 bits so every legal
    # deck size is representable.
    # v11 added public/owner-visible Stratagem reveal state.
    # v10 added two-Action turn state and the forced closing-turn countdown.
    _info_emit(buf, &n, h, INFORMATION_KEY_VERSION)
    _info_emit(buf, &n, h, <uint8_t>player)
    _info_emit(buf, &n, h, <uint8_t>(state.phase + 1))
    _info_emit_u16(buf, &n, h, <uint16_t>state.battle)
    _info_emit(buf, &n, h, <uint8_t>(state.active_player + 1))
    _info_emit_u16(
        buf, &n, h, <uint16_t>(state.turn_number & 0xFFFF)
    )
    _info_emit_u16(
        buf, &n, h, <uint16_t>((state.turn_number >> 16) & 0xFFFF)
    )
    _info_emit(buf, &n, h, state.actions_this_turn)
    _info_emit(buf, &n, h, state.closing_turns_remaining)

    for i in range(PLAYER_COUNT):
        _info_emit(buf, &n, h, state.passed[i])

    _info_emit(buf, &n, h, state.pass_len)
    for i in range(state.pass_len):
        _info_emit(
            buf,
            &n,
            h,
            <uint8_t>(state.pass_order[i] + 1),
        )

    for i in range(PLAYER_COUNT):
        _info_emit(buf, &n, h, state.discarded_this_battle[i])
        _info_emit_u16(
            buf,
            &n,
            h,
            <uint16_t>state.command[i],
        )
        _info_emit(buf, &n, h, state.hero_used[i])
        _info_emit_u16(
            buf,
            &n,
            h,
            state.operations_this_battle[i],
        )
        _info_emit(buf, &n, h, state.cards_played_this_turn_front_mask[i])
        _info_emit(buf, &n, h, state.cards_played_this_battle_front_mask[i])
        _info_emit(buf, &n, h, state.narratives_played_this_battle[i])

    _info_emit(buf, &n, h, <uint8_t>pending_draw)
    _info_emit(buf, &n, h, state.pending_draw_count)
    _info_emit(buf, &n, h, state.pending_draw_finish_operation)
    _info_emit(buf, &n, h, state.pending_len)
    for i in range(state.pending_len):
        _info_emit(buf, &n, h, state.pending_kind[i])
        _info_emit(buf, &n, h, <uint8_t>(state.pending_player[i] + 1))
        _info_emit(buf, &n, h, <uint8_t>(state.pending_card[i] + 1))
        _info_emit(buf, &n, h, <uint8_t>(state.pending_source[i] + 1))
        _info_emit(buf, &n, h, <uint8_t>(state.pending_aux[i] + 1))
        _info_emit_u32(buf, &n, h, state.pending_source_mask[i])
        _info_emit_u32(buf, &n, h, state.pending_dest_mask[i])
        _info_emit(buf, &n, h, state.pending_flags[i])
    _info_emit(buf, &n, h, state.pending_resume)
    _info_emit(buf, &n, h, <uint8_t>(state.pending_resume_player + 1))
    _info_emit(buf, &n, h, state.free_maneuver_available[0])
    _info_emit(buf, &n, h, state.free_maneuver_available[1])
    _info_emit_u16(buf, &n, h, state.player_maneuver_count[0])
    _info_emit_u16(buf, &n, h, state.player_maneuver_count[1])
    for i in range(SLOT_COUNT):
        _info_emit(buf, &n, h, state.maneuver_direction[i])
    _info_emit(buf, &n, h, state.constraint_len)
    for i in range(state.constraint_len):
        _info_emit(buf, &n, h, state.constraint_kind[i])
        _info_emit(buf, &n, h, <uint8_t>(state.constraint_player[i] + 1))
        _info_emit(buf, &n, h, <uint8_t>(state.constraint_source_card[i] + 1))
        _info_emit(buf, &n, h, <uint8_t>(state.constraint_source_owner[i] + 1))
        _info_emit(buf, &n, h, <uint8_t>(state.constraint_front[i] + 1))
        _info_emit(buf, &n, h, state.constraint_direction[i])
        _info_emit(buf, &n, h, <uint8_t>(state.constraint_source_slot[i] + 1))
        _info_emit_u16(
            buf, &n, h,
            <uint16_t>(state.constraint_activate_turn[i] & 0xFFFF)
        )
        _info_emit_u16(
            buf, &n, h,
            <uint16_t>((state.constraint_activate_turn[i] >> 16) & 0xFFFF)
        )
        _info_emit(buf, &n, h, state.constraint_flags[i])
    _info_emit(buf, &n, h, state.resolution_stage)
    _info_emit(buf, &n, h, state.resolution_lost_mask[0])
    _info_emit(buf, &n, h, state.resolution_lost_mask[1])
    _info_emit(buf, &n, h, state.resolution_drive_mask[0])
    _info_emit(buf, &n, h, state.resolution_drive_mask[1])
    _info_emit(buf, &n, h, state.resolution_protected_mask[0])
    _info_emit(buf, &n, h, state.resolution_protected_mask[1])
    _info_emit_u16(
        buf, &n, h,
        <uint16_t>state.resolution_front_loss_command_penalty[0]
    )
    _info_emit_u16(
        buf, &n, h,
        <uint16_t>state.resolution_front_loss_command_penalty[1]
    )
    _info_emit_u32(buf, &n, h, state.resolution_suppressed_mask)
    _info_emit(buf, &n, h, state.resolution_cursor)
    _info_emit(buf, &n, h, <uint8_t>(state.resolution_starter + 1))
    for i in range(SLOT_COUNT):
        _info_emit(buf, &n, h, <uint8_t>(state.resolution_contribution_front[i] + 1))

    for owner in range(PLAYER_COUNT):
        for slot in range(owner * POSITIONS_PER_PLAYER, owner * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER):
            _info_emit(
                buf,
                &n,
                h,
                <uint8_t>(state.force[slot] + 1),
            )
            _info_emit(
                buf,
                &n,
                h,
                <uint8_t>(state.bond[slot] + 1),
            )
            _info_emit(
                buf,
                &n,
                h,
                <uint8_t>(state.name[slot] + 1),
            )
            _info_emit(buf, &n, h, state.exhausted[slot])
            _info_emit_u16(
                buf,
                &n,
                h,
                <uint16_t>state.temporary[slot],
            )
            _info_emit(buf, &n, h, state.negative_one_markers[slot])
            _info_emit(buf, &n, h, state.negative_two_markers[slot])
            _info_emit_u16(buf, &n, h, state.suppression_mask[slot])
            _info_emit(buf, &n, h, state.force_ability_used[slot])
            _info_emit(buf, &n, h, state.bond_ability_used[slot])
            _info_emit(buf, &n, h, state.name_ability_used[slot])
            _info_emit(buf, &n, h, state.name_suppression_immune[slot])
            _info_emit(buf, &n, h, state.maneuver_count[slot])
            _info_emit(
                buf,
                &n,
                h,
                state.maneuvered_in_operation[slot],
            )

    # Ongoing Narratives are public. A face-down Stratagem's existence and
    # selections are public, but its identity is hidden from the opponent
    # until it is revealed.
    for owner in range(PLAYER_COUNT):
        narrative_count = 0
        for narrative_slot in range(self.ongoing_narrative_limit):
            if state.narrative[owner * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot] >= 0:
                narrative_count += 1
        _info_emit(buf, &n, h, <uint8_t>narrative_count)
        for narrative_slot in range(self.ongoing_narrative_limit):
            card = state.narrative[owner * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot]
            if card >= 0:
                _info_emit(buf, &n, h, <uint8_t>(card + 1))
                _info_emit(
                    buf,
                    &n,
                    h,
                    state.narrative_front_mask[owner * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot],
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    state.narrative_used[owner * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot],
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    state.narrative_direction[owner * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot],
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    state.narrative_trigger_mask[owner * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot],
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    <uint8_t>(
                        state.narrative_target_slot[owner * NARRATIVE_SLOTS_PER_PLAYER + narrative_slot] + 1
                    ),
                )

    for owner in range(PLAYER_COUNT):
        card = state.stratagem[owner]
        if card < 0:
            _info_emit(buf, &n, h, 0)
        else:
            if (
                owner == player
                or state.stratagem_revealed[owner]
                or (state.stratagem_known_to_mask[owner] & (1 << player))
            ):
                _info_emit(buf, &n, h, <uint8_t>(card + 1))
            else:
                # 255 is outside the valid card-code range (MAX_CARDS <= 127)
                # and means "a face-down Stratagem exists".
                _info_emit(buf, &n, h, 255)
            _info_emit(buf, &n, h, state.stratagem_revealed[owner])
            _info_emit(buf, &n, h, state.stratagem_known_to_mask[owner])
            _info_emit(buf, &n, h, state.stratagem_front_mask[owner])
            _info_emit(buf, &n, h, state.stratagem_direction[owner])
            _info_emit_u32(buf, &n, h, state.stratagem_target_mask[owner])

    for owner in range(PLAYER_COUNT):
        _info_emit(buf, &n, h, state.stratagem_used[owner])

    # Tax and one-shot discount markers are public board state.
    _info_emit(buf, &n, h, state.tax_len)
    for i in range(state.tax_len):
        _info_emit(buf, &n, h, state.tax_owner[i])
        _info_emit(buf, &n, h, state.tax_target_player[i])
        _info_emit(buf, &n, h, state.tax_front[i])
        _info_emit(buf, &n, h, state.tax_amount[i])
        _info_emit(buf, &n, h, state.tax_card_type_mask[i])
        _info_emit_u32(buf, &n, h, <uint32_t>state.tax_expires_turn[i])
    _info_emit(buf, &n, h, state.discount_len)
    for i in range(state.discount_len):
        _info_emit(buf, &n, h, state.discount_owner[i])
        _info_emit(buf, &n, h, state.discount_target_player[i])
        _info_emit(buf, &n, h, state.discount_slot[i])
        _info_emit(buf, &n, h, state.discount_amount[i])
        _info_emit(buf, &n, h, state.discount_minimum[i])
        _info_emit(buf, &n, h, state.discount_card_type_mask[i])
        _info_emit_u32(buf, &n, h, <uint32_t>state.discount_expires_turn[i])

    # Own hidden resources are visible to the acting player.
    for card in range(self.n_cards):
        _info_emit(buf, &n, h, state.hand[player][card])
    for card in range(self.n_cards):
        _info_emit(buf, &n, h, state.deck_counts[player][card])

    _info_emit_u16(buf, &n, h, state.discard_len[player])
    for i in range(state.discard_len[player]):
        _info_emit(
            buf,
            &n,
            h,
            <uint8_t>(state.discard[player][i] + 1),
        )

    # Opponent hidden resources are represented only by observable counts
    # and cards explicitly known to this player.
    _info_emit(buf, &n, h, state.hand_len[opponent])
    for card in range(self.n_cards):
        _info_emit(
            buf,
            &n,
            h,
            state.known_hidden[player][opponent][card],
        )
    _info_emit_u16(buf, &n, h, state.deck_len[opponent])
    _info_emit_u16(buf, &n, h, state.discard_len[opponent])
    for i in range(state.discard_len[opponent]):
        _info_emit(
            buf,
            &n,
            h,
            <uint8_t>(state.discard[opponent][i] + 1),
        )
    return n

cdef InfoHash128 _fe_information_hash_fast(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    cdef InfoHash128 h
    cdef int n
    _info_hash_init(&h)
    n = _fe__information_state_encode(self, 
        state,
        player,
        NULL,
        &h,
    )
    return h

cdef tuple _fe_information_hash(FastEngine self, FastState state, int player):
    cdef InfoHash128 h = _fe_information_hash_fast(self, state, player)
    return (h.a, h.b)

cdef bytes _fe_information_key_fast(FastEngine self, FastState state, int player):
    cdef unsigned char buf[3 * MAX_CARDS + 2 * MAX_DECK + 1024]
    cdef int n = _fe__information_state_encode(self, 
        state,
        player,
        &buf[0],
        NULL,
    )
    return <bytes>PyBytes_FromStringAndSize(<char*>buf, n)

cdef bytes _fe_information_key(FastEngine self, FastState state, int player):
    return _fe_information_key_fast(self, state, player)

cdef str _fe_information_id(FastEngine self, FastState state, int player):
    return hashlib.sha256(_fe_information_key_fast(self, state, player)).hexdigest()

cdef inline str _fe_rank_key(int rank):
    if rank == RANK_FRONT:
        return "front"
    if rank == RANK_MIDDLE:
        return "middle"
    if rank == RANK_REAR:
        return "rear"
    raise ValueError("Unknown rank code")

cdef str _fe_action_key(FastEngine self, uint64_t action):
    cdef int kind = action_kind(action)
    cdef int card = action_card(action)
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int player = action_player(action)
    cdef int choice, mask, slot, front
    cdef uint32_t extra = action_extra(action)
    cdef object key, fronts, targets

    if kind == TYPE_PASS:
        return "pass"
    if kind == TYPE_END_TURN:
        return "end-turn"
    if kind == TYPE_DISCARD:
        return f"discard:{self.card_ids[card]}"
    if kind == TYPE_CYCLE:
        choice = <int>extra - 1
        if choice < 0 or choice >= self.n_cards:
            raise ValueError("Invalid Cycle second card")
        if self.card_ids[card] <= self.card_ids[choice]:
            return f"cycle:{self.card_ids[card]}:{self.card_ids[choice]}"
        return f"cycle:{self.card_ids[choice]}:{self.card_ids[card]}"
    if kind == TYPE_EFFECT:
        choice = <int>extra
        if choice == EFFECT_FREE_MANEUVER:
            key = "effect:free-maneuver"
        elif choice == EFFECT_MOVE:
            key = "effect:move"
        elif choice == EFFECT_SWAP:
            key = "effect:swap"
        elif choice == EFFECT_RECOVER:
            key = "effect:recover"
        elif choice == EFFECT_FRONT_CONTRIBUTION:
            key = "effect:front-contribution"
        elif choice == EFFECT_SUPPRESS:
            key = "effect:suppress"
        elif choice == EFFECT_SACRIFICE:
            key = "effect:sacrifice"
        elif choice == EFFECT_INTERCEPT:
            key = "effect:intercept"
        elif choice == EFFECT_RETREAT:
            key = "effect:retreat"
        elif choice == EFFECT_PROTECT_RETREAT:
            key = "effect:protect-retreat"
        elif choice == EFFECT_TRANSFER_COMPONENT:
            key = "effect:transfer-component"
        elif choice == EFFECT_SUCCESSION:
            key = "effect:succession"
        else:
            key = f"effect:unknown-{choice}"
        if card < 0 and pos < 0 and dest < 0:
            return key + ":skip"
        if card >= 0:
            key += f":card:{self.card_ids[card]}"
        if pos >= 0:
            key += (
                f":source:{owner_from_slot(pos)},"
                f"{front_from_slot(pos)},"
                f"{_fe_rank_key(rank_from_slot(pos))}"
            )
        if choice == EFFECT_FRONT_CONTRIBUTION and dest >= 0:
            key += f":front:{dest}"
        elif dest >= 0:
            key += (
                f":destination:{owner_from_slot(dest)},"
                f"{front_from_slot(dest)},"
                f"{_fe_rank_key(rank_from_slot(dest))}"
            )
        return key
    if kind == TYPE_MANEUVER:
        return (
            f"maneuver:{front_from_slot(pos)}:"
            f"{_fe_rank_key(rank_from_slot(pos))}:"
            f"{front_from_slot(dest)}:"
            f"{_fe_rank_key(rank_from_slot(dest))}"
        )
    if kind == TYPE_FORCE:
        return (
            f"force:{self.card_ids[card]}:{front_from_slot(pos)}:"
            f"{_fe_rank_key(rank_from_slot(pos))}"
        )
    if kind == TYPE_BOND:
        key = (
            f"bond:{self.card_ids[card]}:{front_from_slot(pos)}:"
            f"{_fe_rank_key(rank_from_slot(pos))}"
        )
        if dest >= 0:
            key += (
                f":move:{front_from_slot(dest)}:"
                f"{_fe_rank_key(rank_from_slot(dest))}"
            )
        if extra:
            key += f":extra:{self.bond_optional_extra_cost[card]}"
        return key
    if kind == TYPE_NAME:
        return (
            f"name:{self.card_ids[card]}:{front_from_slot(pos)}:"
            f"{_fe_rank_key(rank_from_slot(pos))}"
        )
    if kind == TYPE_ONGOING_NARRATIVE:
        key = f"narrative:{self.card_ids[card]}:ongoing:{pos}"
        choice = self.narrative_choice_kind[card]
        if choice == NARRATIVE_CHOICE_FRONT:
            fronts = ""
            for front in range(FRONT_COUNT):
                if extra & (1 << front):
                    if fronts:
                        fronts += ","
                    fronts += str(front)
            key += f":fronts:{fronts}"
        elif (
            choice == NARRATIVE_CHOICE_NAMED_FORMATION
            or choice == NARRATIVE_CHOICE_NAMED_DIRECTION
        ) and dest >= 0:
            key += (
                f":targets:{owner_from_slot(dest)},"
                f"{front_from_slot(dest)},"
                f"{_fe_rank_key(rank_from_slot(dest))}"
            )
            if choice == NARRATIVE_CHOICE_NAMED_DIRECTION:
                key += (
                    f":direction:{'left' if extra == 1 else 'right'}"
                )
        return key
    if kind == TYPE_STRATAGEM:
        key = f"stratagem:{self.card_ids[card]}"
        choice = self.strat_choice_kind[card]
        if (
            choice == STRAT_CHOICE_FRONT
            or choice == STRAT_CHOICE_ADJACENT_FRONTS
            or choice == STRAT_CHOICE_EDGE_FRONT
        ) and pos >= 0:
            fronts = ""
            for front in range(FRONT_COUNT):
                if pos & (1 << front):
                    if fronts:
                        fronts += ","
                    fronts += str(front)
            key += f":fronts:{fronts}"
        if (
            choice == STRAT_CHOICE_DIRECTION
            or choice == STRAT_CHOICE_WHEEL
        ) and dest >= 0:
            key += f":direction:{'left' if dest == 0 else 'right'}"
        if (
            choice == STRAT_CHOICE_WHEEL
            or choice == STRAT_CHOICE_RESERVES
        ) and extra:
            targets = []
            for slot in range(SLOT_COUNT):
                if extra & (<uint32_t>1 << slot):
                    targets.append(
                        f"{owner_from_slot(slot)},"
                        f"{front_from_slot(slot)},"
                        f"{_fe_rank_key(rank_from_slot(slot))}"
                    )
            key += ":targets:" + ";".join(targets)
        return key
    if kind == TYPE_NARRATIVE:
        if extra and self.narrative_discard_count[card] == 1:
            return (
                f"narrative:{self.card_ids[card]}:discard:"
                f"{self.card_ids[<int>extra - 1]}"
            )
        if dest >= 0:
            return (
                f"narrative:{self.card_ids[card]}:"
                f"{player}:{front_from_slot(pos)}:"
                f"{_fe_rank_key(rank_from_slot(pos))};"
                f"{player}:{front_from_slot(dest)}:"
                f"{_fe_rank_key(rank_from_slot(dest))}"
            )
        if pos >= 0:
            return (
                f"narrative:{self.card_ids[card]}:"
                f"{player}:{front_from_slot(pos)}:"
                f"{_fe_rank_key(rank_from_slot(pos))}"
            )
        return f"narrative:{self.card_ids[card]}:"
    raise ValueError("Unknown fast action")
