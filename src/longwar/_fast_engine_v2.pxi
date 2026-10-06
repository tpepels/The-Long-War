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
    if effect.flags & V2_FLAG_REQUIRES_OPPOSING_SUPPLY:
        if not _v2_front_has_opposing_supply(self, state, player, front):
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



cdef bint _v2_component_provides_supply(
    FastEngine self,
    FastState state,
    int slot,
    int card,
    int mode,
    int suppression_bit,
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
            effect.op == V2_OP_SUPPLY
            and _v2_effect_is_live_timing(state, slot, effect)
        ):
            return True
    return False


cdef bint _v2_slot_provides_supply(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int force = state.force[slot]
    cdef int bond = state.bond[slot]
    cdef int name = state.name[slot]
    if force < 0:
        return False
    if _v2_component_provides_supply(
        self, state, slot, force, _v2_mode_for_force(self, force), 0
    ):
        return True
    if _v2_component_provides_supply(
        self, state, slot, bond, V2_MODE_DEFAULT, SUPPRESS_BOND_TEXT
    ):
        return True
    if _v2_component_provides_supply(
        self, state, slot, name, _v2_mode_for_name(self, name), SUPPRESS_NAME_TEXT
    ):
        return True
    return False


cdef bint _v2_front_has_opposing_supply(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int opponent = other_player(player)
    cdef int rank, slot
    for rank in range(RANK_COUNT):
        slot = slot_index(opponent, front, rank)
        if _v2_slot_provides_supply(self, state, slot):
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


cdef bint _v2_source_grants_tireless_to(
    FastEngine self,
    FastState state,
    int source,
    int target,
    int card,
    int mode,
    int suppression_bit,
) noexcept:
    cdef int i
    cdef V2EffectSpec* effect
    if card < 0:
        return False
    if suppression_bit and (state.suppression_mask[source] & suppression_bit):
        return False
    for i in range(self.v2_effect_count[card][mode]):
        effect = &self.v2_effects[card][mode][i]
        if (
            effect.op != V2_OP_TIRELESS
            or not _v2_effect_is_live_timing(state, source, effect)
            or not _v2_slot_effect_condition(self, state, source, effect)
        ):
            continue
        if effect.target == V2_TARGET_SELF and source == target:
            return True
        if (
            effect.target == V2_TARGET_DIRECTLY_AHEAD
            and front_from_slot(source) == front_from_slot(target)
            and rank_from_slot(source) == rank_from_slot(target) + 1
        ):
            return True
        if (
            effect.target == V2_TARGET_DIRECTLY_BEHIND
            and front_from_slot(source) == front_from_slot(target)
            and rank_from_slot(source) + 1 == rank_from_slot(target)
        ):
            return True
    return False


cdef bint _v2_force_is_tireless(
    FastEngine self,
    FastState state,
    int slot,
) noexcept:
    cdef int player = owner_from_slot(slot)
    cdef int source, force, bond, name
    for source in range(
        player * POSITIONS_PER_PLAYER,
        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
    ):
        if state.force[source] < 0:
            continue
        force = state.force[source]
        if _v2_source_grants_tireless_to(
            self, state, source, slot, force,
            _v2_mode_for_force(self, force), 0
        ):
            return True
        bond = state.bond[source]
        if _v2_source_grants_tireless_to(
            self, state, source, slot, bond,
            V2_MODE_DEFAULT, SUPPRESS_BOND_TEXT
        ):
            return True
        name = state.name[source]
        if _v2_source_grants_tireless_to(
            self, state, source, slot, name,
            _v2_mode_for_name(self, name), SUPPRESS_NAME_TEXT
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


cdef inline bint _v2_slot_has_temporary_negative(
    FastState state,
    int slot,
) noexcept:
    return (
        state.negative_one_markers[slot] > 0
        or state.negative_two_markers[slot] > 0
        or bool(
            state.suppression_mask[slot]
            & (
                SUPPRESS_BOND_STRENGTH
                | SUPPRESS_BOND_TEXT
                | SUPPRESS_NAME_TEXT
                | SUPPRESS_ACTION_TURN
                | SUPPRESS_ACTION_BATTLE
                | SUPPRESS_LIMITED_BATTLE
            )
        )
    )


cdef uint32_t _v2_source_class_mask(
    FastEngine self,
    FastState state,
    int player,
    V2EffectSpec* effect,
) noexcept:
    cdef int slot
    cdef uint32_t mask = 0
    for slot in range(
        player * POSITIONS_PER_PLAYER,
        player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
    ):
        if state.force[slot] < 0:
            continue
        if not front_is_active(state.battle, front_from_slot(slot)):
            continue
        if effect.rank_mask and not (
            effect.rank_mask & (1 << rank_from_slot(slot))
        ):
            continue
        if effect.class_mask and not _v2_slot_has_any_class(
            self, state, slot, effect.class_mask
        ):
            continue
        mask |= <uint32_t>(1 << slot)
    return mask


cdef bint _v2_front_contains_class_mask(
    FastEngine self,
    FastState state,
    int player,
    int front,
    uint32_t classes,
) noexcept:
    if classes == 0:
        return True
    return _v2_front_has_class(self, state, player, front, classes)


cdef uint32_t _v2_target_mask(
    FastEngine self,
    FastState state,
    int player,
    int origin,
    V2EffectSpec* effect,
) noexcept:
    cdef int opponent = other_player(player)
    cdef int slot, front, rank, candidate, rear
    cdef uint32_t mask = 0
    cdef uint32_t classes
    cdef int target = effect.target

    if target == V2_TARGET_NONE:
        return 0
    if target == V2_TARGET_SELF:
        if origin >= 0 and state.force[origin] >= 0:
            return <uint32_t>(1 << origin)
        return 0
    if target == V2_TARGET_DIRECTLY_AHEAD:
        if origin < 0:
            return 0
        rank = rank_from_slot(origin)
        if rank <= RANK_FRONT:
            return 0
        candidate = slot_index(
            owner_from_slot(origin),
            front_from_slot(origin),
            rank - 1,
        )
        if state.force[candidate] >= 0:
            return <uint32_t>(1 << candidate)
        return 0
    if target == V2_TARGET_DIRECTLY_BEHIND:
        if origin < 0:
            return 0
        rank = rank_from_slot(origin)
        if rank >= RANK_REAR:
            return 0
        candidate = slot_index(
            owner_from_slot(origin),
            front_from_slot(origin),
            rank + 1,
        )
        if state.force[candidate] >= 0:
            return <uint32_t>(1 << candidate)
        return 0
    if target == V2_TARGET_OPPOSITE:
        if origin < 0:
            return 0
        candidate = slot_index(
            opponent,
            front_from_slot(origin),
            rank_from_slot(origin),
        )
        if state.force[candidate] >= 0:
            return <uint32_t>(1 << candidate)
        return 0

    for slot in range(SLOT_COUNT):
        front = front_from_slot(slot)
        rank = rank_from_slot(slot)
        if not front_is_active(state.battle, front):
            continue

        if target == V2_TARGET_FRIENDLY_ANY_CLASS:
            if (
                owner_from_slot(slot) == player
                and state.force[slot] >= 0
                and _v2_slot_has_any_class(
                    self, state, slot, effect.class_mask
                )
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_FRIENDLY_SAME_FRONT:
            if (
                origin >= 0
                and owner_from_slot(slot) == player
                and front == front_from_slot(origin)
                and state.force[slot] >= 0
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OTHER_FRIENDLY_SAME_FRONT:
            if (
                origin >= 0
                and slot != origin
                and owner_from_slot(slot) == player
                and front == front_from_slot(origin)
                and state.force[slot] >= 0
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OTHER_FRIENDLY_HUMAN_SAME_FRONT:
            if (
                origin >= 0
                and slot != origin
                and owner_from_slot(slot) == player
                and front == front_from_slot(origin)
                and state.force[slot] >= 0
                and (_v2_slot_class_mask(self, state, slot) & (1 << 6))
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_UNBONDED_FRIENDLY_SAME_FRONT:
            if (
                origin >= 0
                and owner_from_slot(slot) == player
                and front == front_from_slot(origin)
                and state.force[slot] >= 0
                and state.bond[slot] < 0
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_SELF_OR_DIRECTLY_AHEAD:
            if origin >= 0 and owner_from_slot(slot) == player:
                if slot == origin and state.force[slot] >= 0:
                    mask |= <uint32_t>(1 << slot)
                elif (
                    front == front_from_slot(origin)
                    and rank + 1 == rank_from_slot(origin)
                    and state.force[slot] >= 0
                ):
                    mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_SELF_VERTICAL_FRIEND:
            if (
                origin >= 0
                and owner_from_slot(slot) == player
                and front == front_from_slot(origin)
                and abs(rank - rank_from_slot(origin)) == 1
                and state.force[slot] >= 0
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_ANY:
            if owner_from_slot(slot) == opponent and state.force[slot] >= 0:
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_ANY_CLASS:
            if (
                owner_from_slot(slot) == opponent
                and state.force[slot] >= 0
                and _v2_slot_has_any_class(
                    self, state, slot, effect.class_mask
                )
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_NAMED_ANY:
            if owner_from_slot(slot) == opponent and _v2_slot_named(state, slot):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_BONDED_ANY:
            if owner_from_slot(slot) == opponent and _v2_slot_bonded(state, slot):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_BONDED_SAME_FRONT:
            if (
                origin >= 0
                and owner_from_slot(slot) == opponent
                and front == front_from_slot(origin)
                and _v2_slot_bonded(state, slot)
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_REAR:
            if (
                owner_from_slot(slot) == opponent
                and rank == RANK_REAR
                and state.force[slot] >= 0
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_SAME_FRONT:
            if (
                origin >= 0
                and owner_from_slot(slot) == opponent
                and front == front_from_slot(origin)
                and state.force[slot] >= 0
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_SAME_FRONT_WITHOUT_NEGATIVE_STRENGTH:
            if (
                origin >= 0
                and owner_from_slot(slot) == opponent
                and front == front_from_slot(origin)
                and state.force[slot] >= 0
                and state.negative_one_markers[slot] == 0
                and state.negative_two_markers[slot] == 0
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_FRONT_WITH_FRIENDLY_CLASS:
            if (
                owner_from_slot(slot) == opponent
                and state.force[slot] >= 0
                and _v2_front_contains_class_mask(
                    self, state, player, front, effect.class_mask2
                )
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_CLASS_FRONT_WITH_FRIENDLY_CLASS:
            if (
                owner_from_slot(slot) == opponent
                and state.force[slot] >= 0
                and _v2_slot_has_any_class(
                    self, state, slot, effect.class_mask
                )
                and _v2_front_contains_class_mask(
                    self, state, player, front, effect.class_mask2
                )
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_PREPARED_ANY:
            if (
                owner_from_slot(slot) == opponent
                and state.force[slot] < 0
                and (state.bond[slot] >= 0 or state.name[slot] >= 0)
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_PREPARED_SAME_FRONT:
            if (
                origin >= 0
                and owner_from_slot(slot) == opponent
                and front == front_from_slot(origin)
                and state.force[slot] < 0
                and (state.bond[slot] >= 0 or state.name[slot] >= 0)
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_OPPOSING_PREPARED_FRONT_WITH_FRIENDLY_CLASS:
            if (
                owner_from_slot(slot) == opponent
                and state.force[slot] < 0
                and (state.bond[slot] >= 0 or state.name[slot] >= 0)
                and _v2_front_contains_class_mask(
                    self, state, player, front, effect.class_mask2
                )
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_PREPARED_COMPONENT_SAME_FRONT:
            if (
                origin >= 0
                and owner_from_slot(slot) == player
                and front == front_from_slot(origin)
                and state.force[slot] < 0
                and (state.bond[slot] >= 0 or state.name[slot] >= 0)
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_PREPARED_NAME_SAME_FRONT:
            if (
                origin >= 0
                and owner_from_slot(slot) == player
                and front == front_from_slot(origin)
                and state.force[slot] < 0
                and state.name[slot] >= 0
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_FRIENDLY_EXHAUSTED_FRONT_WITH_FRIENDLY_CLASS:
            if (
                owner_from_slot(slot) == player
                and state.force[slot] >= 0
                and state.exhausted[slot]
                and _v2_front_contains_class_mask(
                    self, state, player, front, effect.class_mask
                )
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_FRIENDLY_FRONT_OF_SOURCE_CLASS:
            if (
                owner_from_slot(slot) == player
                and state.force[slot] >= 0
                and _v2_slot_has_temporary_negative(state, slot)
                and _v2_front_contains_class_mask(
                    self, state, player, front, effect.class_mask
                )
            ):
                mask |= <uint32_t>(1 << slot)

        elif target == V2_TARGET_FRIENDLY_PAIR_SAME_FRONT_WITH_CLASS:
            if (
                owner_from_slot(slot) == player
                and state.force[slot] >= 0
                and _v2_front_contains_class_mask(
                    self, state, player, front, effect.class_mask
                )
            ):
                mask |= <uint32_t>(1 << slot)

    # Movement effects targeting an opposing formation must also have a legal
    # destination one row toward Rear.
    if effect.op == V2_OP_MOVE and effect.flags & V2_FLAG_DIRECTION_REAR:
        for slot in range(SLOT_COUNT):
            if not (mask & (<uint32_t>1 << slot)):
                continue
            rank = rank_from_slot(slot)
            if rank >= RANK_REAR:
                mask &= <uint32_t>(~(<uint32_t>1 << slot))
                continue
            rear = slot_index(
                owner_from_slot(slot),
                front_from_slot(slot),
                rank + 1,
            )
            if not _fe_card_move_destination_legal(
                self, state, player, slot, rear
            ):
                mask &= <uint32_t>(~(<uint32_t>1 << slot))
    return mask


cdef bint _v2_stratagem_visible_from_effect(
    FastEngine self,
    FastState state,
    int player,
    int origin,
    V2EffectSpec* effect,
) noexcept:
    cdef int opponent = other_player(player)
    cdef int front, source
    cdef uint8_t strat_mask
    if state.stratagem[opponent] < 0 or state.stratagem_revealed[opponent]:
        return False
    strat_mask = state.stratagem_front_mask[opponent]
    if strat_mask == 0:
        return False

    if effect.area == V2_AREA_ANY_ACTIVE:
        if effect.class_mask == 0:
            return True
        return _v2_source_class_mask(self, state, player, effect) != 0

    if effect.area == V2_AREA_SAME_FRONT:
        if origin >= 0:
            return bool(strat_mask & (1 << front_from_slot(origin)))
        return False

    if effect.area == V2_AREA_SAME_OR_ADJACENT:
        if origin < 0:
            return False
        front = front_from_slot(origin)
        return bool(
            strat_mask
            & (
                (1 << front)
                | (1 << (front - 1) if front > 0 else 0)
                | (1 << (front + 1) if front < FRONT_COUNT - 1 else 0)
            )
        )

    if effect.area == V2_AREA_SOURCE_SAME_OR_ADJACENT:
        for source in range(
            player * POSITIONS_PER_PLAYER,
            player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
        ):
            if (
                state.force[source] < 0
                or (
                    effect.class_mask
                    and not _v2_slot_has_any_class(
                        self, state, source, effect.class_mask
                    )
                )
            ):
                continue
            front = front_from_slot(source)
            if strat_mask & (
                (1 << front)
                | (1 << (front - 1) if front > 0 else 0)
                | (1 << (front + 1) if front < FRONT_COUNT - 1 else 0)
            ):
                return True
    return False


cdef bint _v2_effect_can_resolve(
    FastEngine self,
    FastState state,
    int player,
    int origin,
    V2EffectSpec* effect,
) noexcept:
    cdef uint32_t mask
    cdef int slot, dest, front, rank
    if effect.op in (
        V2_OP_GAIN_COMMAND,
        V2_OP_STEAL_COMMAND,
        V2_OP_OPTIONAL_EXTRA_PAYMENT_DRAW,
        V2_OP_REORDER_TOP,
        V2_OP_DRAW_PUT_TOP,
        V2_OP_RECOVER,
        V2_OP_SET_STRATAGEM_FROM_HAND,
        V2_OP_PLAY_BOND_FROM_HAND,
    ):
        return True

    if effect.op in (
        V2_OP_LOOK_HAND,
        V2_OP_DRAW,
        V2_OP_DRAW_DISCARD,
        V2_OP_PICK_TOP_TO_HAND_BOTTOM_REST,
    ):
        if effect.class_mask:
            return _v2_source_class_mask(
                self, state, player, effect
            ) != 0
        return True

    if effect.op in (V2_OP_LOOK_STRATAGEM, V2_OP_DISRUPT_STRATAGEM):
        return _v2_stratagem_visible_from_effect(
            self, state, player, origin, effect
        )

    if effect.op == V2_OP_TAX and effect.front_mode == V2_FRONT_CHOOSE_ACTIVE:
        return active_front_mask_for_battle(state.battle) != 0

    if effect.op == V2_OP_MOVE and effect.target == V2_TARGET_SELF:
        if origin < 0 or state.force[origin] < 0:
            return False
        for dest in range(
            player * POSITIONS_PER_PLAYER,
            player * POSITIONS_PER_PLAYER + POSITIONS_PER_PLAYER,
        ):
            if (
                abs(front_from_slot(dest) - front_from_slot(origin))
                + abs(rank_from_slot(dest) - rank_from_slot(origin))
                <= max(1, effect.steps)
                and dest != origin
                and _fe_card_move_destination_legal(
                    self, state, player, origin, dest
                )
            ):
                return True
        return False

    if effect.op == V2_OP_SWAP and effect.target == V2_TARGET_FRIENDLY_PAIR_SAME_FRONT_WITH_CLASS:
        mask = _v2_target_mask(self, state, player, origin, effect)
        for slot in range(SLOT_COUNT):
            if not (mask & (<uint32_t>1 << slot)):
                continue
            front = front_from_slot(slot)
            rank = rank_from_slot(slot)
            if rank > RANK_FRONT:
                dest = slot_index(player, front, rank - 1)
                if mask & (<uint32_t>1 << dest):
                    return True
            if rank < RANK_REAR:
                dest = slot_index(player, front, rank + 1)
                if mask & (<uint32_t>1 << dest):
                    return True
        return False

    if effect.target != V2_TARGET_NONE:
        return _v2_target_mask(
            self, state, player, origin, effect
        ) != 0

    return True


cdef inline int _v2_pending_aux(int mode, int effect_index) noexcept:
    return (
        (mode << V2_PENDING_MODE_SHIFT)
        | (effect_index & V2_PENDING_EFFECT_MASK)
    )


cdef inline int _v2_pending_mode(int aux) noexcept:
    return aux >> V2_PENDING_MODE_SHIFT


cdef inline int _v2_pending_effect_index(int aux) noexcept:
    return aux & V2_PENDING_EFFECT_MASK


cdef inline V2EffectSpec* _v2_pending_effect(
    FastEngine self,
    FastState state,
) noexcept:
    cdef int card = state.pending_card[0]
    cdef int aux = state.pending_aux[0]
    return &self.v2_effects[
        card
    ][
        _v2_pending_mode(aux)
    ][
        _v2_pending_effect_index(aux)
    ]


cdef void _v2_enqueue_effect(
    FastEngine self,
    FastState state,
    int player,
    int card,
    int mode,
    int effect_index,
    int origin=-1,
    int source_flags=0,
) except *:
    _fe_enqueue_effect(
        self,
        state,
        EFFECT_V2_TARGET,
        player,
        card,
        origin,
        _v2_pending_aux(mode, effect_index),
        0,
        0,
        source_flags,
        card,
    )
