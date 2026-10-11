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
    bint prevent_affliction=False,
) except *:
    if not _fe_attack_legal(self, state, source, target, kind):
        raise ValueError("Illegal basic Attack")
    state.used_attack[source] = 1
    # Empowered applies to one Attack, whether or not screening was present.
    state.conditions[source] &= ~COND_EMPOWERED
    if prevent_affliction:
        return
    if kind == ATTACK_ARCHER:
        _fe_afflict(state, target, 0)  # Exhaust
    elif kind == ATTACK_SKIRMISHER or kind == ATTACK_RIDER:
        _fe_afflict(state, target, COND_SHAKEN)
    else:
        _fe_afflict(state, target, COND_DEPLETED)


# The trigger is checked after the original basic Attack completes.
# Legality is evaluated from the prospective defending player's viewpoint;
# no strategic turn or Action is consumed by this temporary perspective.
cdef inline bint _fe_archer_counterattack_legal(
    FastEngine self, FastState state, int owner, int source, int target
) noexcept:
    cdef int before = state.active_player
    cdef bint legal
    state.active_player = owner
    legal = _fe_attack_legal(self, state, source, target, ATTACK_ARCHER)
    state.active_player = before
    return legal


cdef bint _fe_archer_counterattack_eligible(
    FastEngine self, FastState state, int owner, int front
) noexcept:
    cdef int card = state.stratagem[owner]
    cdef int rank, source, target, enemy = other_player(owner)
    cdef V2EffectSpec* effect
    if (
        card < 0
        or state.stratagem_revealed[owner]
        or not (state.stratagem_front_mask[owner] & (1 << front))
        or self.v2_effect_count[card][V2_MODE_DEFAULT] == 0
    ):
        return False
    effect = &self.v2_effects[card][V2_MODE_DEFAULT][0]
    if effect.op != V2_OP_HIDDEN_ARCHER_COUNTERATTACK:
        return False
    for rank in range(RANK_COUNT):
        source = slot_index(owner, front, rank)
        if state.force[source] < 0 or state.used_attack[source]:
            continue
        for target in range(
            enemy * POSITIONS_PER_PLAYER,
            (enemy + 1) * POSITIONS_PER_PLAYER,
        ):
            if _fe_archer_counterattack_legal(
                self, state, owner, source, target
            ):
                return True
    return False


cdef void _fe_queue_archer_counterattack_response(
    FastEngine self, FastState state, int attacker, int front
) except *:
    cdef int owner = other_player(attacker)
    if state.stratagem[owner] < 0 or state.stratagem_revealed[owner]:
        return
    # All face-down plans yield an identical private response step.
    # Ineligibility is represented by a forced decline, not a skipped prompt.
    _fe_enqueue_effect(
        self, state, EFFECT_STRAT_ARCHER_REVEAL, owner,
        -1, -1, front, 0, 0, EFFECT_OPTIONAL,
    )


# One hidden plan, one response to a targeted Tactic or Attack. The front
# belongs to the *defending* Force (Rider Attacks may cross adjacent Fronts).
cdef inline bint _fe_no_step_back_eligible(
    FastEngine self, FastState state, int owner, int target
) noexcept:
    cdef int card
    if (
        target < 0 or target >= SLOT_COUNT
        or owner_from_slot(target) != owner or state.force[target] < 0
        or not front_is_active(state.battle, front_from_slot(target))
    ):
        return False
    card = state.stratagem[owner]
    if (
        card < 0 or state.stratagem_revealed[owner]
        or not (state.stratagem_front_mask[owner] & (
            1 << front_from_slot(target)
        ))
        or self.v2_effect_count[card][V2_MODE_DEFAULT] == 0
    ):
        return False
    return (
        self.v2_effects[card][V2_MODE_DEFAULT][0].op
        == V2_OP_HIDDEN_NO_STEP_BACK
    )


cdef inline void _fe_discard_revealed_no_step_back(
    FastEngine self, FastState state, int owner
) except *:
    cdef int card = state.stratagem[owner]
    if card < 0:
        return
    state.stratagem_revealed[owner] = 1
    _fe_append_discard(self, state, owner, card, True)
    state.stratagem[owner] = -1
    state.stratagem_known_to_mask[owner] = 0
    state.stratagem_revealed[owner] = 0
    state.stratagem_front_mask[owner] = 0
    state.stratagem_direction[owner] = 0
    state.stratagem_target_mask[owner] = 0
