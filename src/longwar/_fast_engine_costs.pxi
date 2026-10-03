cdef inline void _fe_record_command_diag(
    FastEngine self,
    int kind,
    int detail,
    int player,
    int source_card,
    int amount,
    int nominal_amount,
) noexcept:
    cdef int i
    if not self.command_diag_capture or self.command_diag_len >= MAX_COMMAND_DIAG_EVENTS:
        return
    i = self.command_diag_len
    self.command_diag_kind[i] = kind
    self.command_diag_detail[i] = detail
    self.command_diag_player[i] = player
    self.command_diag_card[i] = source_card
    self.command_diag_amount[i] = amount
    self.command_diag_nominal[i] = nominal_amount
    self.command_diag_len += 1

cdef inline int _fe_local_front_discount_source_fast(
    FastEngine self,
    FastState state,
    int player,
    int front,
    int* source_card,
    int* minimum_cost,
) noexcept:
    cdef int rank, slot, name, discount = 0
    cdef uint8_t bit = <uint8_t>(1 << front)
    source_card[0] = -1
    minimum_cost[0] = 0
    for rank in range(RANK_COUNT):
        slot = slot_index(player, front, rank)
        if state.force[slot] < 0:
            continue
        name = state.name[slot]
        if name < 0:
            continue
        if (
            self.local_catchup_discount_name[name]
            and state.command[player] < state.command[other_player(player)]
            and not (state.cards_played_this_turn_front_mask[player] & bit)
            and self.local_catchup_discount_name[name] > discount
        ):
            discount = self.local_catchup_discount_name[name]
            source_card[0] = name
            minimum_cost[0] = self.local_catchup_minimum_cost_name[name]
        if (
            self.first_front_card_battle_discount_name[name]
            and _fe_slot_complete(self, state, slot)
            and not (state.cards_played_this_battle_front_mask[player] & bit)
            and self.first_front_card_battle_discount_name[name] > discount
        ):
            discount = self.first_front_card_battle_discount_name[name]
            source_card[0] = name
            minimum_cost[0] = self.first_front_card_battle_minimum_cost_name[name]
    return discount

cdef inline int _fe_first_narrative_discount_source_fast(
    FastEngine self,
    FastState state,
    int player,
) noexcept:
    cdef int front, slot, force
    if state.narratives_played_this_battle[player]:
        return -1
    for front in range(FRONT_COUNT):
        slot = slot_index(player, front, RANK_REAR)
        force = state.force[slot]
        if (
            force >= 0
            and self.first_narrative_battle_discount_force[force]
        ):
            return force
    return -1

cdef inline int _fe_command_cost_fast(
    FastEngine self,
    FastState state,
    uint64_t action,
) noexcept:
    cdef int kind, card, pos, target_front=-1, cost, discount, rear, support, strat
    cdef int selected, i, controller, dest, direction, before_cost, saved
    cdef int source_card=-1, local_source=-1, local_discount=0, discount_detail=0
    cdef int discount_minimum_cost=0, local_minimum_cost=0
    cdef uint32_t extra
    cdef int player = state.active_player
    kind = action_kind(action)
    if kind == TYPE_PASS or kind == TYPE_END_TURN or kind == TYPE_CYCLE or kind == TYPE_EFFECT:
        return 0
    if kind == TYPE_MANEUVER:
        pos = action_pos(action)
        dest = action_dest(action)
        direction = (
            DIRECTION_LEFT
            if front_from_slot(dest) < front_from_slot(pos)
            else DIRECTION_RIGHT
            if front_from_slot(dest) > front_from_slot(pos)
            else DIRECTION_NONE
        )
        for i in range(state.constraint_len):
            if (
                state.constraint_player[i] == player
                and state.turn_number >= state.constraint_activate_turn[i]
                and state.constraint_kind[i] == CONSTRAINT_SPECIFIC_MANEUVER
                and state.constraint_flags[i] & CONSTRAINT_ZERO_COST
                and state.constraint_source_slot[i] == pos
                and state.constraint_direction[i] == direction
            ):
                _fe_record_command_diag(
                    self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_FREE_MANEUVER,
                    player, state.constraint_source_card[i], self.maneuver_command_cost,
                    self.maneuver_command_cost,
                )
                return 0
        if state.player_maneuver_count[player] == 0:
            for controller in range(PLAYER_COUNT):
                strat = state.stratagem[controller]
                if (
                    strat >= 0
                    and self.strat_first_maneuver_direction[strat]
                ):
                    _fe_record_command_diag(
                        self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_STRATAGEM_MANEUVER,
                        player, strat, self.maneuver_command_cost, self.maneuver_command_cost,
                    )
                    return 0
        if state.free_maneuver_available[player]:
            _fe_record_command_diag(
                self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_FREE_MANEUVER,
                player, state.free_maneuver_source[player],
                self.maneuver_command_cost, self.maneuver_command_cost,
            )
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
                _fe_record_command_diag(
                    self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_FREE_MANEUVER,
                    player, card, self.maneuver_command_cost, self.maneuver_command_cost,
                )
                return 0
            card = state.bond[action_pos(action)]
            if (
                card >= 0
                and self.first_maneuver_free[card]
                and _fe_adjacent_hero_formation(self, state, player, action_pos(action))
            ):
                _fe_record_command_diag(
                    self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_FREE_MANEUVER,
                    player, card, self.maneuver_command_cost, self.maneuver_command_cost,
                )
                return 0
            card = state.name[action_pos(action)]
            if (
                card >= 0
                and self.first_maneuver_free_empty_front[card]
                and _fe_player_has_empty_front(self, state, player)
            ):
                _fe_record_command_diag(
                    self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_FREE_MANEUVER,
                    player, card, self.maneuver_command_cost, self.maneuver_command_cost,
                )
                return 0
        strat = state.stratagem[player]
        if strat >= 0 and self.strat_maneuver_cost[strat] >= 0:
            cost = self.strat_maneuver_cost[strat]
            saved = self.maneuver_command_cost - cost
            if saved > 0:
                _fe_record_command_diag(
                    self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_STRATAGEM_MANEUVER,
                    player, strat, saved, self.maneuver_command_cost,
                )
            return cost if cost > 0 else 0
        if (
            strat >= 0
            and self.strat_directional_maneuver[strat]
            and _fe_slot_complete(self, state, action_pos(action))
        ):
            if (
                state.stratagem_direction[player] == DIRECTION_LEFT
                and front_from_slot(action_dest(action)) < front_from_slot(action_pos(action))
            ) or (
                state.stratagem_direction[player] == DIRECTION_RIGHT
                and front_from_slot(action_dest(action)) > front_from_slot(action_pos(action))
            ):
                _fe_record_command_diag(
                    self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_STRATAGEM_MANEUVER,
                    player, strat, self.maneuver_command_cost, self.maneuver_command_cost,
                )
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

    if self.catchup_zero_cost[card] and state.command[player] < state.command[other_player(player)]:
        before_cost = cost
        cost = 0
        if before_cost > 0:
            _fe_record_command_diag(
                self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_CATCHUP_DISCOUNT,
                player, card, before_cost, before_cost,
            )
    elif (
        self.completion_discount_cost[card] >= 0
        and kind == TYPE_NAME
        and pos >= 0
        and state.force[pos] >= 0
        and state.bond[pos] >= 0
    ):
        before_cost = cost
        cost = self.completion_discount_cost[card]
        saved = before_cost - cost
        if saved > 0:
            _fe_record_command_diag(
                self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_COMPLETION_DISCOUNT,
                player, card, saved, before_cost,
            )

    if kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME:
        target_front = front_from_slot(pos)
    if kind == TYPE_NARRATIVE or kind == TYPE_ONGOING_NARRATIVE:
        source_card = _fe_first_narrative_discount_source_fast(self, state, player)
        if source_card >= 0:
            before_cost = cost
            cost -= self.first_narrative_battle_discount_force[source_card]
            discount_minimum_cost = (
                self.first_narrative_battle_minimum_cost_force[source_card]
            )
            if cost < discount_minimum_cost:
                cost = discount_minimum_cost
            saved = before_cost - cost
            if saved > 0:
                _fe_record_command_diag(
                    self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_NARRATIVE_DISCOUNT,
                    player, source_card, saved, before_cost,
                )
    if target_front >= 0 and cost > 0:
        source_card = -1
        discount_detail = 0
        discount = 0
        discount_minimum_cost = 0
        local_source = -1
        local_minimum_cost = 0
        local_discount = _fe_local_front_discount_source_fast(
            self,
            state,
            player,
            target_front,
            &local_source,
            &local_minimum_cost,
        )
        if local_discount > discount:
            discount = local_discount
            discount_minimum_cost = local_minimum_cost
            source_card = local_source
            discount_detail = COMMAND_DETAIL_LOCAL_FRONT_DISCOUNT
        if kind == TYPE_FORCE and rank_from_slot(pos) == RANK_FRONT:
            rear = slot_index(player, target_front, RANK_REAR)
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
                discount_minimum_cost = self.frontline_force_minimum_cost[support]
                source_card = support
                discount_detail = COMMAND_DETAIL_FRONTLINE_DISCOUNT
        if discount:
            before_cost = cost
            cost -= discount
            if cost < discount_minimum_cost:
                cost = discount_minimum_cost
            if cost < 0:
                cost = 0
            saved = before_cost - cost
            if saved > 0:
                _fe_record_command_diag(
                    self, COMMAND_DIAG_DISCOUNT, discount_detail,
                    player, source_card, saved, before_cost,
                )
    return cost if cost > 0 else 0

cdef int _fe_command_cost(FastEngine self, FastState state, uint64_t action):
    return _fe_command_cost_fast(self, state, action)

cdef inline void _fe_spend_command_fast(
    FastEngine self,
    FastState state,
    int player,
    int amount,
) noexcept:
    if amount < 0:
        amount = 0
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
    int detail,
) noexcept:
    cdef int before = state.command[player]
    cdef int realized
    state.command[player] += amount
    if state.command[player] > self.command_cap:
        state.command[player] = self.command_cap
    realized = state.command[player] - before
    state.command_refunded_this_battle[player] += realized
    _fe_record_command_diag(
        self, COMMAND_DIAG_GAIN, detail, player, source_card, realized, amount
    )

cdef inline int _fe_complete_mask(FastEngine self, FastState state, int player) noexcept:
    cdef int local, slot, mask=0
    for local in range(POSITIONS_PER_PLAYER):
        slot = player * POSITIONS_PER_PLAYER + local
        if _fe_slot_complete(self, state, slot):
            mask |= 1 << local
    return mask

cdef void _fe_recover_recent_bond_fast(FastEngine self, FastState state, int player) noexcept:
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
            self, state, player, amount, card, COMMAND_DETAIL_COMPLETION_GAIN
        )
    elif effect == COMPLETE_DRAW:
        _fe_queue_battle_draws(self, state, player, amount)
    elif effect == COMPLETE_REVEAL_NARRATIVE:
        enemy_ix = other_player(player) * NARRATIVE_SLOTS_PER_PLAYER + front
        if state.narrative[enemy_ix] >= 0:
            state.narrative_revealed[enemy_ix] = 1
    elif effect == COMPLETE_RECOVER_BOND:
        _fe_recover_recent_bond_fast(self, state, player)

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
    for local in range(POSITIONS_PER_PLAYER):
        if not (new_mask & (1 << local)):
            continue
        slot = player * POSITIONS_PER_PLAYER + local
        front = local // RANK_COUNT
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
                _fe_queue_free_maneuver(
                    self, state, player, <uint32_t>(1 << slot),
                    True, False, state.name[slot]
                )
            if self.completion_swap_adjacent[state.name[slot]]:
                _fe_enqueue_effect(self, 
                    state,
                    EFFECT_SWAP,
                    player,
                    -1,
                    -1,
                    -1,
                    <uint32_t>(1 << slot),
                    _fe_adjacent_formation_mask(self, 
                        state, player, slot, False
                    ),
                    EFFECT_OPTIONAL,
                )
            if self.recover_bond_on_completion_name[state.name[slot]]:
                _fe_queue_recover_from_discard(self, 
                    state, player, CARD_BOND, False
                )
            if self.recover_narrative_on_completion_name[state.name[slot]]:
                _fe_queue_recover_from_discard(self, 
                    state, player, CARD_NARRATIVE, False
                )
        for other in range(other_player(player) * POSITIONS_PER_PLAYER, (other_player(player) + 1) * POSITIONS_PER_PLAYER):
            if (
                front_from_slot(other) == front
                and state.name[other] >= 0
                and state.force[other] >= 0
                and (self.card_capabilities[state.name[other]] & CAP_OPPOSING_NAMED_SAME_FRONT_FREE_MANEUVER)
            ):
                state.free_maneuver_available[other_player(player)] = 1
                state.free_maneuver_source[other_player(player)] = state.name[other]
        _fe_resolve_named_narratives(self, state, player, slot)
