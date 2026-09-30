cdef inline int _fe_local_front_discount_fast(
    FastEngine self,
    FastState state,
    int player,
    int front,
) noexcept:
    cdef int rank, slot, name, discount = 0
    cdef uint8_t bit = <uint8_t>(1 << front)
    for rank in range(2):
        slot = slot_index(player, front, rank)
        if state.force[slot] < 0:
            continue
        name = state.name[slot]
        if name < 0:
            continue
        if (
            self.local_catchup_discount_name[name]
            and state.command[player] < state.command[1 - player]
            and not (state.cards_played_this_turn_front_mask[player] & bit)
        ):
            discount = max(
                discount,
                self.local_catchup_discount_name[name],
            )
        if (
            self.first_front_card_battle_discount_name[name]
            and _fe_slot_complete(self, state, slot)
            and not (state.cards_played_this_battle_front_mask[player] & bit)
        ):
            discount = max(
                discount,
                self.first_front_card_battle_discount_name[name],
            )
    return discount

cdef inline int _fe_first_narrative_discount_fast(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    cdef int front, slot, force
    if state.narratives_played_this_battle[player]:
        return 0
    for front in range(4):
        slot = slot_index(player, front, 1)
        force = state.force[slot]
        if (
            force >= 0
            and self.first_narrative_battle_discount_force[force]
        ):
            return 1
    return 0

cdef inline int _fe_adjacent_discount_fast(
    FastEngine self,
    FastState state,
    int player,
    int target_front,
) noexcept:
    cdef int local, slot, front, name, discount = 0
    for local in range(8):
        slot = player * 8 + local
        if not _fe_slot_complete(self, state, slot):
            continue
        front = local >> 1
        if abs(front - target_front) != 1:
            continue
        name = state.name[slot]
        if name >= 0 and self.adjacent_command_discount[name] > discount:
            discount = self.adjacent_command_discount[name]
    return discount

cdef inline int _fe_command_cost_fast(
    FastEngine self,
    FastState state,
    uint64_t action,
) noexcept:
    cdef int kind, card, pos, target_front=-1, cost, discount, rear, support, strat
    cdef int selected, i, controller, dest, direction
    cdef uint32_t extra
    cdef int player = state.active_player
    kind = action_kind(action)
    if kind == TYPE_PASS or kind == TYPE_EFFECT:
        return 0
    if kind == TYPE_MANEUVER:
        pos = action_pos(action)
        dest = action_dest(action)
        direction = (
            1 if front_from_slot(dest) < front_from_slot(pos) else 2
        )
        # A specific compelled Maneuver may explicitly be free.
        for i in range(state.constraint_len):
            if (
                state.constraint_player[i] == player
                and state.turn_number >= state.constraint_activate_turn[i]
                and state.constraint_kind[i] == CONSTRAINT_SPECIFIC_MANEUVER
                and state.constraint_flags[i] & CONSTRAINT_ZERO_COST
                and state.constraint_source_slot[i] == pos
                and state.constraint_direction[i] == direction
            ):
                return 0
        # The Line Had Begun to Move makes each player's first Maneuver
        # this Battle cost 0, regardless of whether its preferred direction
        # is currently satisfiable.
        if state.player_maneuver_count[player] == 0:
            for controller in range(2):
                strat = state.stratagem[controller]
                if (
                    strat >= 0
                    and self.strat_first_maneuver_direction[strat]
                ):
                    return 0
        if state.free_maneuver_available[player]:
            return 0
        if state.maneuver_count[action_pos(action)] == 0:
            card = state.force[action_pos(action)]
            if (
                card >= 0
                and self.first_maneuver_free[card]
                and (
                    not self.maneuver_requires_open_bond[card]
                    or (
                        state.bond[action_pos(action)] >= 0
                        and state.name[action_pos(action)] < 0
                    )
                )
            ):
                return 0
            card = state.bond[action_pos(action)]
            if (
                card >= 0
                and self.first_maneuver_free[card]
                and _fe_adjacent_hero_formation(self, 
                    state, player, action_pos(action)
                )
            ):
                return 0
            card = state.name[action_pos(action)]
            if (
                card >= 0
                and self.first_maneuver_free_empty_front[card]
                and _fe_player_has_empty_front(self, state, player)
            ):
                return 0
        strat = state.stratagem[player]
        if strat >= 0 and self.strat_maneuver_cost[strat] >= 0:
            return self.strat_maneuver_cost[strat]
        if (
            strat >= 0
            and self.strat_directional_maneuver[strat]
            and _fe_slot_complete(self, state, action_pos(action))
        ):
            if (
                state.stratagem_direction[player] == 1
                and front_from_slot(action_dest(action))
                < front_from_slot(action_pos(action))
            ):
                return 0
            if (
                state.stratagem_direction[player] == 2
                and front_from_slot(action_dest(action))
                > front_from_slot(action_pos(action))
            ):
                return 0
        return self.maneuver_command_cost
    card = action_card(action)
    if card < 0:
        return 0
    cost = self.card_command_cost[card]
    pos = action_pos(action)
    extra = action_extra(action)
    if (
        kind == TYPE_BOND
        and extra
        and self.bond_optional_extra_cost[card] > 0
    ):
        cost += self.bond_optional_extra_cost[card]
    if (
        kind == TYPE_STRATAGEM
        and self.strat_choice_kind[card] == STRAT_CHOICE_RESERVES
    ):
        selected = popcount16(extra)
        if selected > 1:
            cost += selected - 1

    if self.catchup_zero_cost[card] and state.command[player] < state.command[1 - player]:
        cost = 0
    elif (
        self.completion_discount_cost[card] >= 0
        and kind == TYPE_NAME
        and pos >= 0
        and state.force[pos] >= 0
        and state.bond[pos] >= 0
    ):
        cost = self.completion_discount_cost[card]

    if kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME:
        target_front = front_from_slot(pos)
    if kind == TYPE_NARRATIVE or kind == TYPE_ONGOING_NARRATIVE:
        discount = _fe_first_narrative_discount_fast(self, state, player)
        if discount:
            cost -= discount
            if cost < 1:
                cost = 1
    if target_front >= 0:
        discount = _fe_adjacent_discount_fast(self, state, player, target_front)
        if _fe_local_front_discount_fast(self, state, player, target_front) > discount:
            discount = _fe_local_front_discount_fast(self, 
                state, player, target_front
            )
        if kind == TYPE_FORCE and rank_from_slot(pos) == 0:
            rear = slot_index(player, target_front, 1)
            support = state.force[rear]
            if (
                support >= 0
                and self.frontline_force_discount[support] > discount
                and (
                    not self.frontline_force_discount_requires_named[support]
                    or _fe_slot_complete(self, state, rear)
                )
            ):
                discount = self.frontline_force_discount[support]
        if discount:
            cost -= discount
            if cost < 1 and not self.catchup_zero_cost[card]:
                cost = 1
    return cost

cdef int _fe_command_cost(FastEngine self, FastState state, uint64_t action):
    return _fe_command_cost_fast(self, state, action)

cdef inline void _fe_note_command_event(
    FastEngine self,
    int player,
    int source_card,
    object kind,
    int amount,
    object effect,
) except *:
    if not self.command_event_capture:
        return
    self.command_events.append({
        "player": int(player),
        "source_card": (
            None if source_card < 0 else self.card_ids[source_card]
        ),
        "kind": kind,
        "amount": int(amount),
        "effect": effect,
    })


cdef int _fe_discount_source_fast(
    FastEngine self,
    FastState state,
    uint64_t action,
    int actual_cost,
) noexcept:
    cdef int kind = action_kind(action)
    cdef int player = state.active_player
    cdef int card = action_card(action)
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int front, rank, slot, name, force, strat, controller, i
    cdef int best = 0
    cdef int value = 0
    cdef int source = -1
    cdef int direction

    if kind == TYPE_MANEUVER:
        if actual_cost >= self.maneuver_command_cost:
            return -1
        direction = 1 if front_from_slot(dest) < front_from_slot(pos) else 2
        for i in range(state.constraint_len):
            if (
                state.constraint_player[i] == player
                and state.turn_number >= state.constraint_activate_turn[i]
                and state.constraint_kind[i] == CONSTRAINT_SPECIFIC_MANEUVER
                and state.constraint_flags[i] & CONSTRAINT_ZERO_COST
                and state.constraint_source_slot[i] == pos
                and state.constraint_direction[i] == direction
            ):
                return state.constraint_source_card[i]
        if state.player_maneuver_count[player] == 0:
            for controller in range(2):
                strat = state.stratagem[controller]
                if (
                    strat >= 0
                    and self.strat_first_maneuver_direction[strat]
                ):
                    return strat
        if state.free_maneuver_available[player]:
            return -1
        if state.maneuver_count[pos] == 0:
            force = state.force[pos]
            if (
                force >= 0
                and self.first_maneuver_free[force]
                and (
                    not self.maneuver_requires_open_bond[force]
                    or (
                        state.bond[pos] >= 0
                        and state.name[pos] < 0
                    )
                )
            ):
                return force
            card = state.bond[pos]
            if (
                card >= 0
                and self.first_maneuver_free[card]
                and _fe_adjacent_hero_formation(self, state, player, pos)
            ):
                return card
            card = state.name[pos]
            if (
                card >= 0
                and self.first_maneuver_free_empty_front[card]
                and _fe_player_has_empty_front(self, state, player)
            ):
                return card
        strat = state.stratagem[player]
        if (
            strat >= 0
            and (
                self.strat_maneuver_cost[strat] >= 0
                or self.strat_directional_maneuver[strat]
            )
        ):
            return strat
        return -1

    if card < 0:
        return -1
    if (
        self.catchup_zero_cost[card]
        and state.command[player] < state.command[1 - player]
    ):
        return card
    if (
        self.completion_discount_cost[card] >= 0
        and kind == TYPE_NAME
        and pos >= 0
        and state.force[pos] >= 0
        and state.bond[pos] >= 0
    ):
        return card

    if kind == TYPE_NARRATIVE or kind == TYPE_ONGOING_NARRATIVE:
        if state.narratives_played_this_battle[player] == 0:
            for front in range(4):
                slot = slot_index(player, front, 1)
                force = state.force[slot]
                if (
                    force >= 0
                    and self.first_narrative_battle_discount_force[force]
                ):
                    return force

    if kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME:
        front = front_from_slot(pos)
        for i in range(8):
            slot = player * 8 + i
            if not _fe_slot_complete(self, state, slot):
                continue
            if abs((i >> 1) - front) == 1:
                name = state.name[slot]
                value = (
                    self.adjacent_command_discount[name]
                    if name >= 0 else 0
                )
                if value > best:
                    best = value
                    source = name
        for rank in range(2):
            slot = slot_index(player, front, rank)
            if state.force[slot] < 0 or state.name[slot] < 0:
                continue
            name = state.name[slot]
            value = 0
            if (
                self.local_catchup_discount_name[name]
                and state.command[player] < state.command[1 - player]
                and not (
                    state.cards_played_this_turn_front_mask[player]
                    & (<uint8_t>(1 << front))
                )
            ):
                value = self.local_catchup_discount_name[name]
            if (
                self.first_front_card_battle_discount_name[name]
                and _fe_slot_complete(self, state, slot)
                and not (
                    state.cards_played_this_battle_front_mask[player]
                    & (<uint8_t>(1 << front))
                )
                and self.first_front_card_battle_discount_name[name] > value
            ):
                value = self.first_front_card_battle_discount_name[name]
            if value > best:
                best = value
                source = name
        if kind == TYPE_FORCE and rank_from_slot(pos) == 0:
            slot = slot_index(player, front, 1)
            force = state.force[slot]
            if (
                force >= 0
                and self.frontline_force_discount[force] > best
                and (
                    not self.frontline_force_discount_requires_named[force]
                    or _fe_slot_complete(self, state, slot)
                )
            ):
                source = force
    return source


cdef void _fe_note_action_cost_events(
    FastEngine self,
    FastState state,
    uint64_t action,
    int actual_cost,
) except *:
    cdef int kind, card, nominal, selected, source, saved
    cdef uint32_t extra
    if not self.command_event_capture:
        return
    kind = action_kind(action)
    if kind == TYPE_PASS or kind == TYPE_EFFECT or kind == TYPE_DISCARD:
        return
    card = action_card(action)
    extra = action_extra(action)
    if kind == TYPE_MANEUVER:
        nominal = self.maneuver_command_cost
    elif card >= 0:
        nominal = self.card_command_cost[card]
        if (
            kind == TYPE_BOND
            and extra
            and self.bond_optional_extra_cost[card] > 0
        ):
            nominal += self.bond_optional_extra_cost[card]
        if (
            kind == TYPE_STRATAGEM
            and self.strat_choice_kind[card] == STRAT_CHOICE_RESERVES
        ):
            selected = popcount16(extra)
            if selected > 1:
                nominal += selected - 1
    else:
        nominal = actual_cost

    source = _fe_discount_source_fast(self, state, action, actual_cost)
    saved = nominal - actual_cost
    if saved > 0:
        _fe_note_command_event(
            self,
            state.active_player,
            source,
            "discount",
            saved,
            "command_discount",
        )
    if actual_cost == 0 and (
        kind == TYPE_MANEUVER
        or kind == TYPE_FORCE
        or kind == TYPE_BOND
        or kind == TYPE_NAME
        or kind == TYPE_NARRATIVE
        or kind == TYPE_ONGOING_NARRATIVE
        or kind == TYPE_STRATAGEM
    ):
        if source < 0 and card >= 0:
            source = card
        _fe_note_command_event(
            self,
            state.active_player,
            source,
            "free_operation",
            1,
            "zero_cost_operation",
        )


cdef inline void _fe_spend_command_fast(
    FastEngine self,
    FastState state,
    int player,
    int amount,
) noexcept:
    if amount > state.command[player]:
        amount = state.command[player]
    state.command[player] -= amount
    state.command_spent_this_battle[player] += amount

cdef inline void _fe_gain_command_fast(
    FastEngine self,
    FastState state,
    int player,
    int amount,
    int source_card,
    object effect,
) except *:
    cdef int before = state.command[player]
    cdef int realized
    state.command[player] += amount
    if state.command[player] > self.command_cap:
        state.command[player] = self.command_cap
    realized = state.command[player] - before
    state.command_refunded_this_battle[player] += realized
    _fe_note_command_event(
        self,
        player,
        source_card,
        "gain",
        realized,
        effect,
    )

cdef inline int _fe_complete_mask(FastEngine self, FastState state, int player) noexcept:
    cdef int local, slot, mask=0
    for local in range(8):
        slot = player * 8 + local
        if _fe_slot_complete(self, state, slot):
            mask |= 1 << local
    return mask

cdef void _fe_recover_recent_link_fast(FastEngine self, FastState state, int player) noexcept:
    cdef int i, j, card
    for i in range(state.discard_len[player] - 1, -1, -1):
        card = state.discard[player][i]
        if self.card_type[card] != CARD_BOND:
            continue
        for j in range(i, state.discard_len[player] - 1):
            state.discard[player][j] = state.discard[player][j + 1]
        state.discard_len[player] -= 1
        _fe_return_to_hand(self, state, player, card)
        return

cdef void _fe_resolve_completion_effect_fast(
    FastEngine self,
    FastState state,
    int player,
    int card,
    int front,
):
    cdef int effect, amount, enemy_ix
    if card < 0:
        return
    effect = self.completion_effect[card]
    amount = self.completion_amount[card]
    if effect == COMPLETE_GAIN_COMMAND:
        _fe_gain_command_fast(
            self, state, player, amount, card, "completion"
        )
    elif effect == COMPLETE_DRAW:
        _fe_queue_battle_draws(self, state, player, amount)
    elif effect == COMPLETE_REVEAL_NARRATIVE:
        enemy_ix = (1 - player) * 4 + front
        if state.narrative[enemy_ix] >= 0:
            state.narrative_revealed[enemy_ix] = 1
    elif effect == COMPLETE_RECOVER_BOND:
        _fe_recover_recent_link_fast(self, state, player)

cdef void _fe_resolve_new_completions_fast(
    FastEngine self,
    FastState state,
    int player,
    int before_mask,
):
    cdef int local, slot, front
    cdef int after_mask = _fe_complete_mask(self, state, player)
    cdef int new_mask = after_mask & ~before_mask
    if new_mask == 0:
        return
    for local in range(8):
        if not (new_mask & (1 << local)):
            continue
        slot = player * 8 + local
        front = local >> 1
        state.completion_count_this_battle[player] += 1
        _fe_resolve_completion_effect_fast(self, 
            state, player, state.force[slot], front
        )
        _fe_resolve_completion_effect_fast(self, 
            state, player, state.bond[slot], front
        )
        _fe_resolve_completion_effect_fast(self, 
            state, player, state.name[slot], front
        )
        if state.name[slot] >= 0:
            if self.completion_free_maneuver_self[state.name[slot]]:
                _fe_queue_free_maneuver(self, 
                    state, player, <uint16_t>(1 << slot), True
                )
            if self.completion_swap_adjacent[state.name[slot]]:
                _fe_enqueue_effect(self, 
                    state,
                    EFFECT_SWAP,
                    player,
                    -1,
                    -1,
                    -1,
                    <uint16_t>(1 << slot),
                    _fe_adjacent_formation_mask(self, 
                        state, player, slot, False
                    ),
                    EFFECT_OPTIONAL,
                )
            if self.recover_bond_on_completion_name[state.name[slot]]:
                _fe_queue_recover_from_discard(self, 
                    state, player, CARD_BOND, False
                )
            if self.recover_story_on_completion_name[state.name[slot]]:
                _fe_queue_recover_from_discard(self, 
                    state, player, CARD_NARRATIVE, False
                )
        for other in range((1 - player) * 8, (1 - player) * 8 + 8):
            if (
                front_from_slot(other) == front
                and state.name[other] >= 0
                and state.force[other] >= 0
                and (self.card_capabilities[state.name[other]] & CAP_OPPOSING_NAMED_SAME_FRONT_FREE_MANEUVER)
            ):
                state.free_maneuver_available[1 - player] = 1
        _fe_resolve_named_narratives(self, state, player, slot)
