# Canonical V2 mechanic helpers.
#
# This layer interprets the compiled integer effect records populated by
# _fast_engine_cards.pxi. It never parses printed card text and never
# special-cases card identities.

cdef inline bint _v2_slot_bonded(FastState state, int slot) noexcept:
    return state.force[slot] >= 0 and state.bond[slot] >= 0


cdef inline bint _v2_slot_named(FastState state, int slot) noexcept:
    return (
        state.force[slot] >= 0
        and state.bond[slot] >= 0
        and state.name[slot] >= 0
    )


cdef inline int _v2_mode_for_force(FastEngine self, int card) noexcept:
    return V2_MODE_FORCE if card >= 0 and self.card_type[card] == CARD_HERO else V2_MODE_DEFAULT


cdef inline int _v2_mode_for_name(FastEngine self, int card) noexcept:
    return V2_MODE_NAME if card >= 0 and self.card_type[card] == CARD_HERO else V2_MODE_DEFAULT


cdef inline uint32_t _v2_card_class_mask(FastEngine self, int card) noexcept:
    return 0 if card < 0 else self.class_mask[card]


cdef uint32_t _v2_slot_class_mask(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef uint32_t mask = 0
    cdef int card, mode, i
    cdef V2EffectSpec* effect
    card = state.force[slot]
    if card >= 0:
        mask |= self.class_mask[card]
    card = state.bond[slot]
    if card >= 0:
        mask |= self.class_mask[card]
    card = state.name[slot]
    if card >= 0:
        mask |= self.class_mask[card]
        if not (state.suppression_mask[slot] & SUPPRESS_NAME_TEXT):
            mode = _v2_mode_for_name(self, card)
            for i in range(self.v2_effect_count[card][mode]):
                effect = &self.v2_effects[card][mode][i]
                if (
                    effect.op == V2_OP_ADD_CLASS
                    and (
                        not (effect.flags & V2_FLAG_REQUIRES_NAMED)
                        or _v2_slot_named(state, slot)
                    )
                ):
                    mask |= effect.class_mask
    return mask


cdef inline bint _v2_slot_has_any_class(
    FastEngine self,
    FastState state,
    int slot,
    uint32_t classes,
) noexcept:
    return classes == 0 or bool(_v2_slot_class_mask(self, state, slot) & classes)


cdef bint _v2_front_has_class(
    FastEngine self,
    FastState state,
    int player,
    int front,
    uint32_t classes,
) noexcept:
    cdef int rank, slot
    for rank in range(RANK_COUNT):
        slot = slot_index(player, front, rank)
        if state.force[slot] >= 0 and _v2_slot_has_any_class(
            self, state, slot, classes
        ):
            return True
    return False


cdef inline bint _v2_force_rank_allowed(
    FastEngine self,
    int force,
    int rank,
) noexcept:
    return (
        force >= 0
        and bool(self.allowed_rank_mask[force] & (1 << rank))
    )


cdef bint _v2_slot_effect_condition(
    FastEngine self,
    FastState state,
    int slot,
    V2EffectSpec* effect,
) noexcept:
    cdef int rank = rank_from_slot(slot)
    cdef int player = owner_from_slot(slot)
    cdef int front = front_from_slot(slot)
    cdef int other, other_player_id, other_rank
    if effect.rank_mask and not (effect.rank_mask & (1 << rank)):
        return False
    if effect.flags & V2_FLAG_REQUIRES_NAMED and not _v2_slot_named(state, slot):
        return False
    if effect.flags & V2_FLAG_REQUIRES_BONDED and not _v2_slot_bonded(state, slot):
        return False
    if effect.class_mask and not _v2_slot_has_any_class(
        self, state, slot, effect.class_mask
    ):
        return False
    if effect.class_mask2:
        # "another friendly X in this Front"
        for other_rank in range(RANK_COUNT):
            other = slot_index(player, front, other_rank)
            if (
                other != slot
                and state.force[other] >= 0
                and _v2_slot_has_any_class(
                    self, state, other, effect.class_mask2
                )
            ):
                break
        else:
            if effect.op == V2_OP_SELF_STRENGTH:
                return False
    if effect.flags & V2_FLAG_REQUIRES_OPPOSING_EXHAUSTED:
        other_player_id = other_player(player)
        for other_rank in range(RANK_COUNT):
            other = slot_index(other_player_id, front, other_rank)
            if state.force[other] >= 0 and state.exhausted[other]:
                break
        else:
            return False
    return True


cdef inline bint _v2_effect_is_live_timing(
    FastState state,
    int slot,
    V2EffectSpec* effect,
) noexcept:
    cdef int rank = rank_from_slot(slot)
    if effect.timing == V2_TIMING_CONTINUOUS:
        return True
    if effect.timing == V2_TIMING_BONDED:
        return _v2_slot_bonded(state, slot)
    if effect.timing == V2_TIMING_WHILE_NAMED:
        return _v2_slot_named(state, slot)
    if effect.timing == V2_TIMING_FRONT:
        return rank == RANK_FRONT
    if effect.timing == V2_TIMING_MIDDLE:
        return rank == RANK_MIDDLE
    if effect.timing == V2_TIMING_REAR:
        return rank == RANK_REAR
    if effect.timing == V2_TIMING_EXHAUSTED:
        return bool(state.exhausted[slot])
    if effect.timing == V2_TIMING_TIRELESS:
        return True
    if effect.timing == V2_TIMING_MOBILE:
        return True
    return False


cdef bint _v2_component_has_live_op(
    FastEngine self,
    FastState state,
    int slot,
    int card,
    int mode,
    int op,
    int suppression_bit=0,
) noexcept:
    cdef int i
    cdef V2EffectSpec* effect
    if card < 0:
        return False
    if suppression_bit and (state.suppression_mask[slot] & suppression_bit):
        return False
    for i in range(self.v2_effect_count[card][mode]):
        effect = &self.v2_effects[card][mode][i]
        if (
            effect.op == op
            and _v2_effect_is_live_timing(state, slot, effect)
            and _v2_slot_effect_condition(self, state, slot, effect)
        ):
            return True
    return False


cdef bint _v2_force_is_mobile(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int force = state.force[slot]
    return _v2_component_has_live_op(
        self,
        state,
        slot,
        force,
        _v2_mode_for_force(self, force),
        V2_OP_MANEUVER_UNNAMED,
        0,
    )


cdef bint _v2_force_is_tireless(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int force = state.force[slot]
    cdef int bond = state.bond[slot]
    cdef int name = state.name[slot]
    if _v2_component_has_live_op(
        self, state, slot, force, _v2_mode_for_force(self, force),
        V2_OP_TIRELESS, 0
    ):
        return True
    if _v2_component_has_live_op(
        self, state, slot, bond, V2_MODE_DEFAULT,
        V2_OP_TIRELESS, SUPPRESS_BOND_TEXT
    ):
        return True
    if _v2_component_has_live_op(
        self, state, slot, name, _v2_mode_for_name(self, name),
        V2_OP_TIRELESS, SUPPRESS_NAME_TEXT
    ):
        return True

    # Adjacent positional TIRELESS support from another formation.
    cdef int player = owner_from_slot(slot)
    cdef int front = front_from_slot(slot)
    cdef int rank = rank_from_slot(slot)
    cdef int source, card, mode, i
    cdef V2EffectSpec* effect
    for source in range(
        player * POSITIONS_PER_PLAYER,
        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
    ):
        if state.force[source] < 0:
            continue
        for card, mode, suppression_bit in (
            (state.force[source], _v2_mode_for_force(self, state.force[source]), 0),
            (state.bond[source], V2_MODE_DEFAULT, SUPPRESS_BOND_TEXT),
            (state.name[source], _v2_mode_for_name(self, state.name[source]), SUPPRESS_NAME_TEXT),
        ):
            if card < 0 or (
                suppression_bit and state.suppression_mask[source] & suppression_bit
            ):
                continue
            for i in range(self.v2_effect_count[card][mode]):
                effect = &self.v2_effects[card][mode][i]
                if effect.op != V2_OP_TIRELESS or not _v2_effect_is_live_timing(
                    state, source, effect
                ):
                    continue
                if effect.target == V2_TARGET_DIRECTLY_AHEAD:
                    if (
                        front_from_slot(source) == front
                        and rank_from_slot(source) == rank + 1
                    ):
                        return True
                elif effect.target == V2_TARGET_DIRECTLY_BEHIND:
                    if (
                        front_from_slot(source) == front
                        and rank_from_slot(source) + 1 == rank
                    ):
                        return True
    return False


cdef inline int _v2_card_type_bit_for_play(
    FastEngine self,
    int kind,
    int card,
) noexcept:
    if kind == TYPE_FORCE:
        return 8 if card >= 0 and self.card_type[card] == CARD_HERO else 1
    if kind == TYPE_BOND:
        return 2
    if kind == TYPE_NAME:
        return 16 if card >= 0 and self.card_type[card] == CARD_HERO else 4
    if kind == TYPE_TACTIC:
        return 32
    if kind == TYPE_NARRATIVE or kind == TYPE_ONGOING_NARRATIVE:
        return 64
    if kind == TYPE_STRATAGEM:
        return 128
    # Orders intentionally have no existing selector bit; "any" Taxes still
    # match them through the 255 wildcard.
    return 0


cdef inline bint _v2_card_type_mask_matches(
    uint8_t mask,
    int bit,
) noexcept:
    return mask == 255 or (bit != 0 and bool(mask & bit))
