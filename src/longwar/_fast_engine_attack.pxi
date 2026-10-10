# Core basic Attacks. The role classification selects the single basic Attack
# for a Force that has more than one eligible Attack classification.
cdef inline bint _fe_attack_legal(
    FastEngine self, FastState state, int source, int target, int kind,
) noexcept:
    cdef int player = state.active_player
    cdef int force, middle, own_front, other_front, rank
    cdef uint32_t classes
    if source < 0 or source >= SLOT_COUNT or target < 0 or target >= SLOT_COUNT:
        return False
    if owner_from_slot(source) != player or owner_from_slot(target) == player:
        return False
    if not front_is_active(state.battle, front_from_slot(source)):
        return False
    if not front_is_active(state.battle, front_from_slot(target)):
        return False
    force = state.force[source]
    if force < 0 or state.force[target] < 0 or state.used_attack[source]:
        return False
    if state.conditions[source] & COND_DEPLETED:
        return False
    # An attached Name (including a Hero as Name) contributes its classes.
    classes = _v2_slot_class_mask(self, state, source)
    own_front = front_from_slot(source)
    other_front = front_from_slot(target)
    rank = rank_from_slot(source)
    if kind == ATTACK_ARCHER:
        if not (classes & (1 << 0)) or own_front != other_front:
            return False
        if rank_from_slot(target) == RANK_MIDDLE:
            return (
                state.force[slot_index(other_player(player), own_front, RANK_FRONT)] < 0
                and _v2_component_has_live_op(
                    self, state, source, force, _v2_mode_for_force(self, force),
                    V2_OP_ARCHER_MIDDLE_OPEN_FRONT,
                )
            )
        if rank_from_slot(target) != RANK_REAR:
            return False
        middle = slot_index(other_player(player), own_front, RANK_MIDDLE)
        if state.force[middle] >= 0 and not (state.conditions[source] & COND_EMPOWERED):
            if (
                _v2_slot_class_mask(self, state, middle) & (1 << 3)
                and not (state.conditions[middle] & COND_DEPLETED)
                and (
                    not (state.conditions[middle] & COND_SHAKEN)
                    or _v2_component_has_live_op(
                        self, state, middle, state.force[middle],
                        _v2_mode_for_force(self, state.force[middle]),
                        V2_OP_RELIABLE_GUARD_SCREEN,
                    )
                )
            ):
                return False
        return True
    if kind == ATTACK_SKIRMISHER:
        return bool(classes & (1 << 13)) and own_front == other_front and rank_from_slot(target) == RANK_MIDDLE
    if kind == ATTACK_RAIDER:
        return (
            bool(classes & (1 << 8)) and own_front == other_front
            and rank_from_slot(target) in (RANK_MIDDLE, RANK_REAR)
            and state.force[slot_index(other_player(player), own_front, RANK_FRONT)] < 0
        )
    if kind == ATTACK_RIDER:
        return (
            bool(classes & (1 << 9))
            and rank in (RANK_FRONT, RANK_MIDDLE)
            and abs(other_front - own_front) == 1
            and rank_from_slot(target) == RANK_FRONT
            and _fe_frontline_is_flanked(self, state, target)
        )
    return False


cdef inline void _fe_afflict(
    FastState state, int target, int condition,
) noexcept:
    """Apply one affliction: Guarded consumes once; Inspired blocks Shaken."""
    if state.force[target] < 0:
        return
    if state.conditions[target] & COND_GUARDED:
        state.conditions[target] &= ~COND_GUARDED
        return
    if condition == COND_SHAKEN and state.conditions[target] & COND_INSPIRED:
        return
    if condition == 0:
        state.exhausted[target] = 1
    else:
        state.conditions[target] |= <uint8_t>condition


cdef void _fe_apply_attack(
    FastEngine self, FastState state, int source, int target, int kind,
) except *:
    if not _fe_attack_legal(self, state, source, target, kind):
        raise ValueError("Illegal basic Attack")
    state.used_attack[source] = 1
    # Empowered applies to one Attack, whether or not screening was present.
    state.conditions[source] &= ~COND_EMPOWERED
    if kind == ATTACK_ARCHER:
        _fe_afflict(state, target, 0)  # Exhaust
    elif kind == ATTACK_SKIRMISHER or kind == ATTACK_RIDER:
        _fe_afflict(state, target, COND_SHAKEN)
    else:
        _fe_afflict(state, target, COND_DEPLETED)
