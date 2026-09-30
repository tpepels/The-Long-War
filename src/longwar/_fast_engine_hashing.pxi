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
    _info_hash_feed_u32(&h, <uint32_t>state.shuffle_seed)

    for p in range(2):
        _info_hash_feed(&h, state.deck_len[p])
        for i in range(state.deck_len[p]):
            _info_hash_feed(&h, <uint8_t>(state.deck[p][i] + 1))
        for card in range(self.n_cards):
            _info_hash_feed(&h, state.hand[p][card])
        _info_hash_feed(&h, state.hand_len[p])
        _info_hash_feed(&h, state.discard_len[p])
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
    for p in range(2):
        _info_hash_feed(&h, state.discarded_this_battle[p])

    for slot in range(SLOT_COUNT):
        _info_hash_feed(&h, <uint8_t>(state.force[slot] + 1))
        _info_hash_feed(&h, <uint8_t>(state.bond[slot] + 1))
        _info_hash_feed(&h, <uint8_t>(state.name[slot] + 1))
        _info_hash_feed_u16(
            &h,
            <uint16_t>state.temporary[slot],
        )
        _info_hash_feed(&h, state.maneuver_count[slot])
        _info_hash_feed(&h, state.maneuvered_in_operation[slot])

    for ix in range(SCHEME_COUNT):
        _info_hash_feed(&h, <uint8_t>(state.narrative[ix] + 1))
        _info_hash_feed(&h, state.narrative_revealed[ix])
        _info_hash_feed(&h, state.narrative_front_mask[ix])
        _info_hash_feed(&h, state.narrative_used[ix])
        _info_hash_feed(&h, state.narrative_direction[ix])
        _info_hash_feed(&h, state.narrative_trigger_mask[ix])
        _info_hash_feed(&h, <uint8_t>(state.narrative_target_slot[ix] + 1))
    for p in range(2):
        _info_hash_feed(&h, <uint8_t>(state.stratagem[p] + 1))
        _info_hash_feed(&h, state.stratagem_revealed[p])
        _info_hash_feed(&h, state.stratagem_front_mask[p])
        _info_hash_feed(&h, state.stratagem_direction[p])
        _info_hash_feed_u16(&h, state.stratagem_target_mask[p])
        _info_hash_feed(&h, state.stratagem_used[p])

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
        _info_hash_feed_u16(&h, state.pending_source_mask[i])
        _info_hash_feed_u16(&h, state.pending_dest_mask[i])
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
    _info_hash_feed(&h, state.resolution_recovery_losses[0])
    _info_hash_feed(&h, state.resolution_recovery_losses[1])
    _info_hash_feed_u16(&h, state.resolution_suppressed_mask)
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
    cdef int n=0, i, owner, slot, card, story_slot, story_count
    cdef int opponent = 1 - player
    cdef int pending_draw = (
        state.active_player + 1
        if state.cleanup_pending
        else 0
    )

    _info_emit(buf, &n, h, 7)
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

    for i in range(2):
        _info_emit(buf, &n, h, state.passed[i])

    _info_emit(buf, &n, h, state.pass_len)
    for i in range(state.pass_len):
        _info_emit(
            buf,
            &n,
            h,
            <uint8_t>(state.pass_order[i] + 1),
        )

    for i in range(2):
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
        _info_emit_u16(buf, &n, h, state.pending_source_mask[i])
        _info_emit_u16(buf, &n, h, state.pending_dest_mask[i])
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
    _info_emit(buf, &n, h, state.resolution_recovery_losses[0])
    _info_emit(buf, &n, h, state.resolution_recovery_losses[1])
    _info_emit_u16(buf, &n, h, state.resolution_suppressed_mask)
    _info_emit(buf, &n, h, state.resolution_cursor)
    _info_emit(buf, &n, h, <uint8_t>(state.resolution_starter + 1))
    for i in range(SLOT_COUNT):
        _info_emit(buf, &n, h, <uint8_t>(state.resolution_contribution_front[i] + 1))

    for owner in range(2):
        for slot in range(owner * 8, owner * 8 + 8):
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
            _info_emit_u16(
                buf,
                &n,
                h,
                <uint16_t>state.temporary[slot],
            )
            _info_emit(buf, &n, h, state.maneuver_count[slot])
            _info_emit(
                buf,
                &n,
                h,
                state.maneuvered_in_operation[slot],
            )

    # Ongoing Stories and Stratagems are public in the canonical rules.
    for owner in range(2):
        story_count = 0
        for story_slot in range(self.ongoing_story_limit):
            if state.narrative[owner * 4 + story_slot] >= 0:
                story_count += 1
        _info_emit(buf, &n, h, <uint8_t>story_count)
        for story_slot in range(self.ongoing_story_limit):
            card = state.narrative[owner * 4 + story_slot]
            if card >= 0:
                _info_emit(buf, &n, h, <uint8_t>(card + 1))
                _info_emit(
                    buf,
                    &n,
                    h,
                    state.narrative_front_mask[owner * 4 + story_slot],
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    state.narrative_used[owner * 4 + story_slot],
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    state.narrative_direction[owner * 4 + story_slot],
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    state.narrative_trigger_mask[owner * 4 + story_slot],
                )
                _info_emit(
                    buf,
                    &n,
                    h,
                    <uint8_t>(
                        state.narrative_target_slot[owner * 4 + story_slot] + 1
                    ),
                )

    for owner in range(2):
        card = state.stratagem[owner]
        if card < 0:
            _info_emit(buf, &n, h, 0)
        else:
            _info_emit(buf, &n, h, <uint8_t>(card + 1))
            _info_emit(buf, &n, h, state.stratagem_front_mask[owner])
            _info_emit(buf, &n, h, state.stratagem_direction[owner])
            _info_emit_u16(buf, &n, h, state.stratagem_target_mask[owner])

    for owner in range(2):
        _info_emit(buf, &n, h, state.stratagem_used[owner])

    # Own hidden resources are visible to the acting player.
    for card in range(self.n_cards):
        _info_emit(buf, &n, h, state.hand[player][card])
    for card in range(self.n_cards):
        _info_emit(buf, &n, h, state.deck_counts[player][card])

    _info_emit(buf, &n, h, state.discard_len[player])
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
    _info_emit(buf, &n, h, state.deck_len[opponent])
    _info_emit(buf, &n, h, state.discard_len[opponent])
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
    if kind == TYPE_DISCARD:
        return f"discard:{self.card_ids[card]}"
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
                f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
            )
        if choice == EFFECT_FRONT_CONTRIBUTION and dest >= 0:
            key += f":front:{dest}"
        elif dest >= 0:
            key += (
                f":destination:{owner_from_slot(dest)},"
                f"{front_from_slot(dest)},"
                f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
            )
        return key
    if kind == TYPE_MANEUVER:
        return (
            f"maneuver:{front_from_slot(pos)}:"
            f"{'front' if rank_from_slot(pos) == 0 else 'rear'}:"
            f"{front_from_slot(dest)}:"
            f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
        )
    if kind == TYPE_SUBJECT:
        return (
            f"force:{self.card_ids[card]}:{front_from_slot(pos)}:"
            f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
        )
    if kind == TYPE_LINK:
        key = (
            f"bond:{self.card_ids[card]}:{front_from_slot(pos)}:"
            f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
        )
        if dest >= 0:
            key += (
                f":move:{front_from_slot(dest)}:"
                f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
            )
        if extra:
            key += f":extra:{self.bond_optional_extra_cost[card]}"
        return key
    if kind == TYPE_NAME:
        return (
            f"name:{self.card_ids[card]}:{front_from_slot(pos)}:"
            f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
        )
    if kind == TYPE_SCHEME:
        key = f"story:{self.card_ids[card]}:ongoing:{pos}"
        choice = self.story_choice_kind[card]
        if choice == STORY_CHOICE_FRONT:
            fronts = ""
            for front in range(4):
                if extra & (1 << front):
                    if fronts:
                        fronts += ","
                    fronts += str(front)
            key += f":fronts:{fronts}"
        elif (
            choice == STORY_CHOICE_NAMED_FORMATION
            or choice == STORY_CHOICE_NAMED_DIRECTION
        ) and dest >= 0:
            key += (
                f":targets:{owner_from_slot(dest)},"
                f"{front_from_slot(dest)},"
                f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
            )
            if choice == STORY_CHOICE_NAMED_DIRECTION:
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
            for front in range(4):
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
                        f"{'front' if rank_from_slot(slot) == 0 else 'rear'}"
                    )
            key += ":targets:" + ";".join(targets)
        return key
    if kind == TYPE_PLOT:
        if extra and self.story_discard_count[card] == 1:
            return (
                f"story:{self.card_ids[card]}:discard:"
                f"{self.card_ids[<int>extra - 1]}"
            )
        if dest >= 0:
            return (
                f"story:{self.card_ids[card]}:"
                f"{player}:{front_from_slot(pos)}:"
                f"{'front' if rank_from_slot(pos) == 0 else 'rear'};"
                f"{player}:{front_from_slot(dest)}:"
                f"{'front' if rank_from_slot(dest) == 0 else 'rear'}"
            )
        if pos >= 0:
            return (
                f"story:{self.card_ids[card]}:"
                f"{player}:{front_from_slot(pos)}:"
                f"{'front' if rank_from_slot(pos) == 0 else 'rear'}"
            )
        return f"story:{self.card_ids[card]}:"
    raise ValueError("Unknown fast action")
