cdef inline int _fe_hand_size(FastEngine self, FastState state, int player) noexcept:
    return state.hand_len[player]

cdef int _fe_position_strength_fast(FastEngine self, FastState state, int slot) noexcept:
    cdef int card = state.force[slot]
    cdef int player, local, front, rank, value, rear, frontslot, other, adj, bond, name, role, mod, strat, controller
    if card < 0:
        return 0
    player = owner_from_slot(slot)
    local = local_slot(slot)
    front = local >> 1
    rank = local & 1
    role = self.role[card]
    value = self.strength[card] + state.temporary[slot]

    # Printed card effects are explicit metadata; roles remain labels only.
    mod = self.force_text_effect[card]
    if mod == FORCE_TEXT_FRONT_BONUS and rank == 0:
        value += self.force_text_amount[card]
    elif mod == FORCE_TEXT_REAR_BONUS and rank == 1:
        value += self.force_text_amount[card]
    elif mod == FORCE_TEXT_FRONT_IF_REAR and rank == 0:
        rear = slot_index(player, front, 1)
        if state.force[rear] >= 0:
            value += self.force_text_amount[card]
    elif mod == FORCE_TEXT_REAR_IF_FRONT and rank == 1:
        frontslot = slot_index(player, front, 0)
        if state.force[frontslot] >= 0:
            value += self.force_text_amount[card]

    # Rear support effects add Strength to the Force directly ahead.
    if rank == 0:
        rear = slot_index(player, front, 1)
        other = state.force[rear]
        if (
            other >= 0
            and self.force_text_effect[other] == FORCE_TEXT_SUPPORT_AHEAD
        ):
            value += self.force_text_amount[other]

    # Roles and classifications are labels only. They never grant
    # intrinsic Strength; any such effect must come from explicit card
    # rules. The role code remains available for cards that refer to a
    # role by name (for example a Stratagem affecting Archers).

    if front > 0:
        adj = slot_index(player, front - 1, rank)
        other = state.force[adj]
        if other >= 0 and self.aura[other] and (self.aura_rank[other] < 0 or self.aura_rank[other] == rank):
            value += self.aura[other]
    if front < 3:
        adj = slot_index(player, front + 1, rank)
        other = state.force[adj]
        if other >= 0 and self.aura[other] and (self.aura_rank[other] < 0 or self.aura_rank[other] == rank):
            value += self.aura[other]

    mod = self.force_mod_amount[card]
    if mod:
        if self.force_mod_discard_min[card] and state.discard_len[player] < self.force_mod_discard_min[card]:
            pass
        elif self.force_mod_adj_named[card]:
            other = 0
            if (
                front > 0
                and state.force[slot_index(player, front - 1, rank)] >= 0
                and state.name[slot_index(player, front - 1, rank)] >= 0
            ):
                other = 1
            if (
                front < 3
                and state.force[slot_index(player, front + 1, rank)] >= 0
                and state.name[slot_index(player, front + 1, rank)] >= 0
            ):
                other = 1
            if other:
                value += mod
        else:
            value += mod

    bond = state.bond[slot]
    name = state.name[slot]
    if bond >= 0:
        value += self.bond_bonus[bond]
        if (
            self.bond_momentum_direction[bond]
            and state.maneuver_count[slot] > 0
        ):
            value += 2
        if name >= 0:
            value += self.bond_named_bonus[bond]
            if self.bond_discard_per[bond]:
                mod = state.discarded_this_battle[player] * self.bond_discard_per[bond]
                if mod > self.bond_discard_max[bond]:
                    mod = self.bond_discard_max[bond]
                value += mod
    if name >= 0:
        value += self.name_strength[name]
        if self.name_rank_bonus_rank[name] == rank:
            value += self.name_rank_bonus_amount[name]

    for controller in range(2):
        strat = state.stratagem[controller]
        if strat < 0 or not state.stratagem_revealed[controller]:
            continue
        value += self.strat_role_mod[strat][role]
        value += self.strat_rank_mod[strat][rank]
        if controller == player:
            value += self.strat_controller_rank_mod[strat][rank]
        if name >= 0:
            value += self.strat_named_mod[strat]
        else:
            value += self.strat_unnamed_mod[strat]

    return value if value > 0 else 0

cdef int _fe_position_strength(FastEngine self, FastState state, int player, int front, int rank):
    return _fe_position_strength_fast(self, state, slot_index(player, front, rank))

cdef int _fe_front_strength_fast(FastEngine self, FastState state, int player, int front) noexcept:
    cdef int value, narrative, enemy, slot, bond
    value = _fe_position_strength_fast(self, state, slot_index(player, front, 0))
    value += _fe_position_strength_fast(self, state, slot_index(player, front, 1))
    narrative = state.narrative[player * 4 + front]
    if narrative >= 0 and not state.narrative_revealed[player * 4 + front]:
        value += self.narrative_face_bonus[narrative]
    enemy = 1 - player
    for slot in (slot_index(enemy, front, 0), slot_index(enemy, front, 1)):
        if state.force[slot] >= 0 and state.bond[slot] >= 0 and state.name[slot] >= 0:
            bond = state.bond[slot]
            value += self.bond_opposing[bond]
    return value

cdef inline bint _fe_frontline_only_resolution(
    FastEngine self,
    FastState state,
    int front,
) noexcept:
    cdef int player, rank, force
    for player in range(2):
        for rank in range(2):
            force = state.force[slot_index(player, front, rank)]
            if force >= 0 and self.combat_frontline_only[force]:
                return True
    return False

cdef inline int _fe_resolution_front_strength_fast(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int strat = state.stratagem[player]
    cdef int mask = state.stratagem_front_mask[player]
    cdef int value = 0
    cdef int rank, slot, local, physical_front, chosen_front
    cdef int formation_bonus = 0
    cdef int enemy, bond
    cdef bint frontline_only = _fe_frontline_only_resolution(self, state, front)

    if (
        strat >= 0
        and self.strat_refuse_flank[strat]
        and (mask & (1 << front))
    ):
        return 0

    # Resolution choices can redirect a skirmisher's contribution and
    # suppress a specific formation without mutating its printed Strength.
    for local in range(8):
        slot = player * 8 + local
        if state.force[slot] < 0:
            continue
        if state.resolution_suppressed_mask & (<uint16_t>1 << slot):
            continue
        physical_front = local >> 1
        rank = local & 1
        chosen_front = state.resolution_contribution_front[slot]
        if chosen_front >= 0:
            if chosen_front != front:
                continue
        elif physical_front != front:
            continue
        if frontline_only and rank == 1:
            continue
        value += _fe_position_strength_fast(self, state, slot)

    # Preserve any explicit opposing-Bond modifier from the canonical
    # strength calculation.
    enemy = 1 - player
    for rank in range(2):
        slot = slot_index(enemy, front, rank)
        if _fe_slot_complete(self, state, slot):
            bond = state.bond[slot]
            if bond >= 0:
                value += self.bond_opposing[bond]

    if strat >= 0 and self.strat_refuse_flank[strat]:
        if (mask == 1 and front == 1) or (mask == 8 and front == 2):
            for rank in range(1 if frontline_only else 2):
                slot = slot_index(player, front, rank)
                if (
                    state.force[slot] >= 0
                    and not (
                        state.resolution_suppressed_mask
                        & (<uint16_t>1 << slot)
                    )
                ):
                    formation_bonus += 1
            value += formation_bonus
    return value

cdef inline bint _fe_breakthrough_active(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int rank, slot, force, name
    for rank in range(2):
        slot = slot_index(player, front, rank)
        force = state.force[slot]
        if force < 0:
            continue
        if self.force_breakthrough[force]:
            return True
        name = state.name[slot]
        if name >= 0 and self.name_breakthrough[name]:
            return True
    return False

cdef inline bint _fe_tie_control_active(
    FastEngine self,
    FastState state,
) noexcept:
    cdef int p, strat
    for p in range(2):
        strat = state.stratagem[p]
        if strat >= 0 and self.strat_tie_control[strat]:
            return True
    return False

cdef int _fe_front_strength(FastEngine self, FastState state, int player, int front):
    return _fe_front_strength_fast(self, state, player, front)

cdef inline bint _fe_slot_complete(FastEngine self, FastState state, int slot) noexcept:
    return (
        state.force[slot] >= 0
        and state.bond[slot] >= 0
        and state.name[slot] >= 0
    )

cdef inline bint _fe_subject_protected(FastEngine self, FastState state, int slot) noexcept:
    cdef int bond = state.bond[slot]
    cdef int name = state.name[slot]
    if bond >= 0 and name >= 0 and self.bond_protect[bond]:
        return True
    return (
        _fe_slot_complete(self, state, slot)
        and name >= 0
        and self.complete_plot_protection[name]
    )

cdef inline bint _fe_story_locked(FastEngine self, FastState state, int player) noexcept:
    cdef int controller, strat
    for controller in range(2):
        strat = state.stratagem[controller]
        if strat < 0 or not state.stratagem_revealed[controller]:
            continue
        if self.strat_global_story_lock[strat]:
            return True
        if controller == player and self.strat_story_lock[strat]:
            return True
    return False

cdef inline bint _fe_can_draw_fast(FastEngine self, FastState state, int player) noexcept:
    return (
        state.deck_len[player] > 0
        or state.discard_len[player] > 0
    )

cdef bint _fe_can_draw(FastEngine self, FastState state, int player):
    return _fe_can_draw_fast(self, state, player)
