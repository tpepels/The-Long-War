cdef inline int _fe_hand_size(FastEngine self, FastState state, int player) noexcept:
    return state.hand_len[player]


cdef bint _v2_opposite_suppresses_bond_strength(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int opponent = other_player(owner_from_slot(slot))
    cdef int source = slot_index(
        opponent,
        front_from_slot(slot),
        rank_from_slot(slot),
    )
    cdef int card, mode, i
    cdef V2EffectSpec* effect
    if state.force[source] < 0:
        return False
    card = state.force[source]
    mode = _v2_mode_for_force(self, card)
    for i in range(self.v2_effect_count[card][mode]):
        effect = &self.v2_effects[card][mode][i]
        if (
            effect.op == V2_OP_SUPPRESS_BOND_STRENGTH
            and effect.target == V2_TARGET_OPPOSITE
            and _v2_effect_is_live_timing(state, source, effect)
        ):
            return True
    card = state.bond[source]
    if card >= 0 and not (state.suppression_mask[source] & SUPPRESS_BOND_TEXT):
        for i in range(self.v2_effect_count[card][V2_MODE_DEFAULT]):
            effect = &self.v2_effects[card][V2_MODE_DEFAULT][i]
            if (
                effect.op == V2_OP_SUPPRESS_BOND_STRENGTH
                and effect.target == V2_TARGET_OPPOSITE
                and _v2_effect_is_live_timing(state, source, effect)
            ):
                return True
    card = state.name[source]
    mode = _v2_mode_for_name(self, card)
    if card >= 0 and not (state.suppression_mask[source] & SUPPRESS_NAME_TEXT):
        for i in range(self.v2_effect_count[card][mode]):
            effect = &self.v2_effects[card][mode][i]
            if (
                effect.op == V2_OP_SUPPRESS_BOND_STRENGTH
                and effect.target == V2_TARGET_OPPOSITE
                and _v2_effect_is_live_timing(state, source, effect)
            ):
                return True
    return False


cdef int _v2_component_strength_effects(
    FastEngine self,
    FastState state,
    int slot,
    int card,
    int mode,
    int suppression_bit,
) noexcept:
    cdef int result = 0
    cdef int i
    cdef V2EffectSpec* effect
    if card < 0:
        return 0
    if suppression_bit and (state.suppression_mask[slot] & suppression_bit):
        return 0
    for i in range(self.v2_effect_count[card][mode]):
        effect = &self.v2_effects[card][mode][i]
        if (
            effect.op != V2_OP_SELF_STRENGTH
            and effect.op != V2_OP_COMPONENT_STRENGTH
        ):
            continue
        if not _v2_effect_is_live_timing(state, slot, effect):
            continue
        if not _v2_slot_effect_condition(self, state, slot, effect):
            continue
        if (
            effect.target2 == V2_TARGET_DIRECTLY_BEHIND
            and (
                rank_from_slot(slot) >= RANK_REAR
                or state.force[
                    slot_index(
                        owner_from_slot(slot),
                        front_from_slot(slot),
                        rank_from_slot(slot) + 1,
                    )
                ] < 0
            )
        ):
            continue
        result += effect.amount
    return result


cdef int _v2_support_bonus(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int rank = rank_from_slot(slot)
    cdef int source, card, mode, i
    cdef int result = 0
    cdef V2EffectSpec* effect
    if rank >= RANK_REAR:
        return 0
    source = slot_index(
        owner_from_slot(slot),
        front_from_slot(slot),
        rank + 1,
    )
    if state.force[source] < 0:
        return 0

    card = state.force[source]
    mode = _v2_mode_for_force(self, card)
    for i in range(self.v2_effect_count[card][mode]):
        effect = &self.v2_effects[card][mode][i]
        if (
            effect.op == V2_OP_SUPPORT
            and _v2_effect_is_live_timing(state, source, effect)
            and _v2_slot_effect_condition(self, state, source, effect)
        ):
            result += effect.amount

    card = state.bond[source]
    if card >= 0 and not (state.suppression_mask[source] & SUPPRESS_BOND_TEXT):
        for i in range(self.v2_effect_count[card][V2_MODE_DEFAULT]):
            effect = &self.v2_effects[card][V2_MODE_DEFAULT][i]
            if (
                effect.op == V2_OP_SUPPORT
                and _v2_effect_is_live_timing(state, source, effect)
                and _v2_slot_effect_condition(self, state, source, effect)
            ):
                result += effect.amount

    card = state.name[source]
    mode = _v2_mode_for_name(self, card)
    if card >= 0 and not (state.suppression_mask[source] & SUPPRESS_NAME_TEXT):
        for i in range(self.v2_effect_count[card][mode]):
            effect = &self.v2_effects[card][mode][i]
            if (
                effect.op == V2_OP_SUPPORT
                and _v2_effect_is_live_timing(state, source, effect)
                and _v2_slot_effect_condition(self, state, source, effect)
            ):
                result += effect.amount
    return result


cdef int _v2_local_aura_bonus(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int player = owner_from_slot(slot)
    cdef int front = front_from_slot(slot)
    cdef int source, card, mode, i
    cdef int result = 0
    cdef uint32_t target_classes = _v2_slot_class_mask(self, state, slot)
    cdef V2EffectSpec* effect
    for source in range(
        player * POSITIONS_PER_PLAYER,
        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
    ):
        if (
            state.force[source] < 0
            or front_from_slot(source) != front
        ):
            continue

        card = state.force[source]
        mode = _v2_mode_for_force(self, card)
        for i in range(self.v2_effect_count[card][mode]):
            effect = &self.v2_effects[card][mode][i]
            if (
                effect.op == V2_OP_LOCAL_CLASS_AURA
                and _v2_effect_is_live_timing(state, source, effect)
                and (not effect.class_mask or target_classes & effect.class_mask)
                and not (
                    source == slot and effect.flags & V2_FLAG_EXCLUDE_SELF
                )
            ):
                result += effect.amount

        card = state.bond[source]
        if card >= 0 and not (state.suppression_mask[source] & SUPPRESS_BOND_TEXT):
            for i in range(self.v2_effect_count[card][V2_MODE_DEFAULT]):
                effect = &self.v2_effects[card][V2_MODE_DEFAULT][i]
                if (
                    effect.op == V2_OP_LOCAL_CLASS_AURA
                    and _v2_effect_is_live_timing(state, source, effect)
                    and (not effect.class_mask or target_classes & effect.class_mask)
                    and not (
                        source == slot and effect.flags & V2_FLAG_EXCLUDE_SELF
                    )
                ):
                    result += effect.amount

        card = state.name[source]
        mode = _v2_mode_for_name(self, card)
        if card >= 0 and not (state.suppression_mask[source] & SUPPRESS_NAME_TEXT):
            for i in range(self.v2_effect_count[card][mode]):
                effect = &self.v2_effects[card][mode][i]
                if (
                    effect.op == V2_OP_LOCAL_CLASS_AURA
                    and _v2_effect_is_live_timing(state, source, effect)
                    and (not effect.class_mask or target_classes & effect.class_mask)
                    and not (
                        source == slot and effect.flags & V2_FLAG_EXCLUDE_SELF
                    )
                ):
                    result += effect.amount
    return result


cdef int _v2_narrative_strength_bonus(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int player = owner_from_slot(slot)
    cdef int ix, card, i
    cdef int result = 0
    cdef uint32_t classes = _v2_slot_class_mask(self, state, slot)
    cdef bint named = _v2_slot_named(state, slot)
    cdef bint bonded = _v2_slot_bonded(state, slot)
    cdef bint contains_hero = (
        (state.force[slot] >= 0 and self.card_type[state.force[slot]] == CARD_HERO)
        or (state.name[slot] >= 0 and self.card_type[state.name[slot]] == CARD_HERO)
    )
    cdef V2EffectSpec* effect
    for ix in range(
        player * NARRATIVE_SLOTS_PER_PLAYER,
        player * NARRATIVE_SLOTS_PER_PLAYER + self.ongoing_narrative_limit,
    ):
        card = state.narrative[ix]
        if card < 0:
            continue
        for i in range(self.v2_effect_count[card][V2_MODE_DEFAULT]):
            effect = &self.v2_effects[card][V2_MODE_DEFAULT][i]
            if effect.timing != V2_TIMING_CONTINUOUS:
                continue
            if effect.op == V2_OP_CLASS_STRENGTH_AURA:
                if effect.class_mask and not (classes & effect.class_mask):
                    continue
                if effect.flags & V2_FLAG_REQUIRES_BONDED and not bonded:
                    continue
                result += effect.amount
            elif effect.op == V2_OP_STATUS_STRENGTH_AURA:
                if (
                    (effect.flags & V2_FLAG_STATUS_HERO and contains_hero)
                    or (effect.flags & V2_FLAG_STATUS_NAMED and named)
                ):
                    result += effect.amount
    return result


cdef inline bint _fe_frontline_is_flanked(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    """Paper game: a neighboring enemy Frontline exploits an empty friendly line.

    This is a positional -1 penalty, never an Exhaustion marker, and cannot
    stack from both sides. Inactive Fronts and battlefield edges do not flank.
    """
    cdef int player = owner_from_slot(slot)
    cdef int front = front_from_slot(slot)
    cdef int adjacent
    if (
        rank_from_slot(slot) != RANK_FRONT
        or state.force[slot] < 0
        or not front_is_active(state.battle, front)
        or _v2_force_flank_protected(self, state, slot)
    ):
        return False
    for adjacent in (front - 1, front + 1):
        if (
            adjacent < 0 or adjacent >= FRONT_COUNT
            or not front_is_active(state.battle, adjacent)
        ):
            continue
        if (
            state.force[slot_index(player, adjacent, RANK_FRONT)] < 0
            and state.force[slot_index(other_player(player), adjacent, RANK_FRONT)] >= 0
        ):
            return True
    return False


cdef int _v2_position_strength_no_reserve(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int force = state.force[slot]
    cdef int bond, name, value
    if force < 0:
        return 0

    value = self.strength[force]
    value += state.temporary[slot]
    value -= state.negative_one_markers[slot]
    if state.conditions[slot] & COND_SHAKEN:
        value -= 2
    if state.conditions[slot] & COND_DEPLETED:
        value -= 1
    value -= 2 * state.negative_two_markers[slot]
    value -= 3 * state.negative_three_markers[slot]
    if _fe_frontline_is_flanked(self, state, slot):
        value -= 1

    value += _v2_component_strength_effects(
        self, state, slot, force, _v2_mode_for_force(self, force), 0
    )

    bond = state.bond[slot]
    if bond >= 0:
        if (
            not (state.suppression_mask[slot] & SUPPRESS_BOND_STRENGTH)
            and not _v2_opposite_suppresses_bond_strength(self, state, slot)
        ):
            value += self.bond_strength_modifier[bond]
        value += _v2_component_strength_effects(
            self, state, slot, bond, V2_MODE_DEFAULT, SUPPRESS_BOND_TEXT
        )

    name = state.name[slot]
    if name >= 0:
        value += self.name_strength[name]
        value += _v2_component_strength_effects(
            self, state, slot, name, _v2_mode_for_name(self, name),
            SUPPRESS_NAME_TEXT
        )

    value += _v2_support_bonus(self, state, slot)
    value += _v2_local_aura_bonus(self, state, slot)
    value += _v2_narrative_strength_bonus(self, state, slot)
    return value if value > 0 else 0


cdef int _v2_reserve_bonus(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int rank = rank_from_slot(slot)
    cdef int player = owner_from_slot(slot)
    cdef int front = front_from_slot(slot)
    cdef int ahead, opposing, card, mode, i
    cdef int result = 0
    cdef V2EffectSpec* effect
    if rank == RANK_FRONT:
        return 0
    ahead = slot_index(player, front, rank - 1)
    if state.force[ahead] < 0:
        return 0
    opposing = slot_index(other_player(player), front, rank - 1)
    if (
        state.force[opposing] < 0
        or _v2_position_strength_no_reserve(self, state, ahead)
        >= _v2_position_strength_no_reserve(self, state, opposing)
    ):
        return 0

    card = state.force[slot]
    mode = _v2_mode_for_force(self, card)
    for i in range(self.v2_effect_count[card][mode]):
        effect = &self.v2_effects[card][mode][i]
        if (
            effect.op == V2_OP_RESERVE
            and _v2_effect_is_live_timing(state, slot, effect)
            and _v2_slot_effect_condition(self, state, slot, effect)
        ):
            result += effect.amount

    card = state.bond[slot]
    if card >= 0 and not (state.suppression_mask[slot] & SUPPRESS_BOND_TEXT):
        for i in range(self.v2_effect_count[card][V2_MODE_DEFAULT]):
            effect = &self.v2_effects[card][V2_MODE_DEFAULT][i]
            if (
                effect.op == V2_OP_RESERVE
                and _v2_effect_is_live_timing(state, slot, effect)
                and _v2_slot_effect_condition(self, state, slot, effect)
            ):
                result += effect.amount

    card = state.name[slot]
    mode = _v2_mode_for_name(self, card)
    if card >= 0 and not (state.suppression_mask[slot] & SUPPRESS_NAME_TEXT):
        for i in range(self.v2_effect_count[card][mode]):
            effect = &self.v2_effects[card][mode][i]
            if (
                effect.op == V2_OP_RESERVE
                and _v2_effect_is_live_timing(state, slot, effect)
                and _v2_slot_effect_condition(self, state, slot, effect)
            ):
                result += effect.amount
    return result


cdef int _fe_position_strength_fast(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int value
    if state.force[slot] < 0:
        return 0
    value = _v2_position_strength_no_reserve(self, state, slot)
    value += _v2_reserve_bonus(self, state, slot)
    return value if value > 0 else 0


cdef int _fe_position_strength(
    FastEngine self,
    FastState state,
    int player,
    int front,
    int rank,
):
    return _fe_position_strength_fast(
        self, state, slot_index(player, front, rank)
    )


cdef int _fe_front_strength_fast(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int rank, value = 0
    for rank in range(RANK_COUNT):
        value += _fe_position_strength_fast(
            self, state, slot_index(player, front, rank)
        )
    return value


cdef inline int _fe_resolution_front_strength_fast(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int rank, slot, value = 0
    for rank in range(RANK_COUNT):
        slot = slot_index(player, front, rank)
        if (
            state.force[slot] >= 0
            and not (
                state.resolution_suppressed_mask
                & (<uint32_t>1 << slot)
            )
        ):
            value += _fe_position_strength_fast(self, state, slot)
    return value


cdef inline bint _fe_tie_control_active(
    FastEngine self,
    FastState state,
) noexcept:
    # V2 tie-changing Stratagems are handled at comparison time, when their
    # printed reveal condition can be tested per Front.
    return False


cdef int _fe_front_strength(
    FastEngine self,
    FastState state,
    int player,
    int front,
):
    return _fe_front_strength_fast(self, state, player, front)


cdef inline bint _fe_slot_complete(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    return _v2_slot_named(state, slot)


cdef inline bint _fe_formation_protected(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    # V2 protection is expressed by explicit Tactic/marker prevention rules,
    # not a generic formation-protected status.
    return False


cdef inline bint _fe_narrative_locked(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    return False


cdef inline bint _fe_can_draw_fast(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    return state.deck_len[player] > 0 or state.discard_len[player] > 0


cdef bint _fe_can_draw(
    FastEngine self,
    FastState state,
    int player,
):
    return _fe_can_draw_fast(self, state, player)
