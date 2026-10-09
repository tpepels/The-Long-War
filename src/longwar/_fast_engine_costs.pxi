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


cdef inline uint8_t _v2_cost_action_type_mask(
    FastEngine self,
    int kind,
    int card,
) noexcept:
    if card < 0:
        return 0
    if kind == TYPE_FORCE:
        return 8 if self.card_type[card] == CARD_HERO else 1
    if kind == TYPE_BOND:
        return 2
    if kind == TYPE_NAME:
        return 16 if self.card_type[card] == CARD_HERO else 4
    if kind == TYPE_TACTIC:
        return 32
    if kind == TYPE_NARRATIVE or kind == TYPE_ONGOING_NARRATIVE:
        return 64
    if kind == TYPE_STRATAGEM:
        return 128
    return 0


cdef inline bint _v2_cost_action_affects_front(
    FastEngine self,
    uint64_t action,
    int front,
) noexcept:
    cdef int kind = action_kind(action)
    cdef int card = action_card(action)
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int selected_front
    cdef uint32_t extra = action_extra(action)
    if front < 0:
        return False
    if kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME:
        return pos >= 0 and front_from_slot(pos) == front
    if kind == TYPE_TACTIC or kind == TYPE_ORDER:
        if pos >= 0 and front_from_slot(pos) == front:
            return True
        if dest >= 0 and front_from_slot(dest) == front:
            return True
        selected_front = <int>(extra & V2_PLAY_FRONT_MASK) - 1
        return selected_front == front
    if kind == TYPE_ABILITY:
        if extra & V2_ABILITY_NARRATIVE_FLAG:
            return True
        return pos >= 0 and front_from_slot(pos) == front
    if kind == TYPE_MANEUVER:
        return (
            (pos >= 0 and front_from_slot(pos) == front)
            or (dest >= 0 and front_from_slot(dest) == front)
        )
    if kind == TYPE_NARRATIVE:
        return (
            (pos >= 0 and front_from_slot(pos) == front)
            or (dest >= 0 and front_from_slot(dest) == front)
        )
    if kind == TYPE_ONGOING_NARRATIVE:
        return (
            card >= 0
            and self.narrative_choice_kind[card] == NARRATIVE_CHOICE_FRONT
            and bool(extra & (<uint32_t>1 << front))
        )
    if kind == TYPE_STRATAGEM:
        return pos >= 0 and bool(pos & (1 << front))
    return False


cdef inline bint _v2_is_card_play_kind(int kind) noexcept:
    return (
        kind == TYPE_FORCE
        or kind == TYPE_BOND
        or kind == TYPE_NAME
        or kind == TYPE_TACTIC
        or kind == TYPE_ORDER
        or kind == TYPE_NARRATIVE
        or kind == TYPE_ONGOING_NARRATIVE
        or kind == TYPE_STRATAGEM
    )


cdef inline void _v2_remove_tax_marker_at(
    FastState state,
    int index,
) noexcept:
    cdef int i
    if index < 0 or index >= state.tax_len:
        return
    for i in range(index, state.tax_len - 1):
        state.tax_owner[i] = state.tax_owner[i + 1]
        state.tax_target_player[i] = state.tax_target_player[i + 1]
        state.tax_front[i] = state.tax_front[i + 1]
        state.tax_amount[i] = state.tax_amount[i + 1]
        state.tax_card_type_mask[i] = state.tax_card_type_mask[i + 1]
        state.tax_expires_turn[i] = state.tax_expires_turn[i + 1]
    state.tax_len -= 1


cdef inline void _v2_remove_slot_discount_at(
    FastState state,
    int index,
) noexcept:
    cdef int i
    if index < 0 or index >= state.discount_len:
        return
    for i in range(index, state.discount_len - 1):
        state.discount_owner[i] = state.discount_owner[i + 1]
        state.discount_target_player[i] = state.discount_target_player[i + 1]
        state.discount_slot[i] = state.discount_slot[i + 1]
        state.discount_amount[i] = state.discount_amount[i + 1]
        state.discount_minimum[i] = state.discount_minimum[i + 1]
        state.discount_card_type_mask[i] = state.discount_card_type_mask[i + 1]
        state.discount_expires_turn[i] = state.discount_expires_turn[i + 1]
    state.discount_len -= 1


cdef void _v2_consume_cost_markers(
    FastEngine self,
    FastState state,
    int player,
    uint64_t action,
) noexcept:
    """Consume one-shot V2 cost markers after a legal action has paid its cost."""
    cdef int kind = action_kind(action)
    cdef int card = action_card(action)
    cdef int pos = action_pos(action)
    cdef int i
    cdef uint8_t type_mask = _v2_cost_action_type_mask(self, kind, card)
    cdef bint card_play = _v2_is_card_play_kind(kind)
    cdef bint matches

    i = state.tax_len - 1
    while i >= 0:
        if (
            state.tax_expires_turn[i] >= 0
            and state.turn_number > state.tax_expires_turn[i]
        ):
            _v2_remove_tax_marker_at(state, i)
            i -= 1
            continue
        matches = (
            card_play
            and state.tax_target_player[i] == player
            and _v2_cost_action_affects_front(
                self, action, state.tax_front[i]
            )
            and (
                state.tax_card_type_mask[i] == 0
                or state.tax_card_type_mask[i] == 255
                or (
                    type_mask != 0
                    and state.tax_card_type_mask[i] & type_mask
                )
            )
        )
        if matches:
            _v2_remove_tax_marker_at(state, i)
        i -= 1

    i = state.discount_len - 1
    while i >= 0:
        if (
            state.discount_expires_turn[i] >= 0
            and state.turn_number > state.discount_expires_turn[i]
        ):
            _v2_remove_slot_discount_at(state, i)
            i -= 1
            continue
        matches = (
            (kind == TYPE_FORCE or kind == TYPE_BOND or kind == TYPE_NAME)
            and pos >= 0
            and state.discount_target_player[i] == player
            and state.discount_slot[i] == pos
            and (
                state.discount_card_type_mask[i] == 0
                or state.discount_card_type_mask[i] == 255
                or (
                    type_mask != 0
                    and state.discount_card_type_mask[i] & type_mask
                )
            )
        )
        if matches:
            _v2_remove_slot_discount_at(state, i)
        i -= 1


cdef inline bint _v2_cost_tactic_targets_slot(
    uint64_t action,
    int target,
) noexcept:
    if action_kind(action) != TYPE_TACTIC or target < 0:
        return False
    return action_pos(action) == target or action_dest(action) == target


cdef inline int _v2_cost_reduce(
    int cost,
    int amount,
    int minimum,
) noexcept:
    cdef int candidate
    if amount <= 0:
        return cost
    candidate = cost - amount
    if candidate < minimum:
        candidate = minimum
    return candidate if candidate < cost else cost


cdef inline int _v2_cost_apply_effect(
    FastEngine self,
    FastState state,
    int player,
    uint64_t action,
    int source_owner,
    int source_slot,
    int source_card,
    V2EffectSpec* effect,
    int phase,
    int cost,
) noexcept:
    cdef int kind = action_kind(action)
    cdef int card = action_card(action)
    cdef int pos = action_pos(action)
    cdef int dest = action_dest(action)
    cdef int source_front = front_from_slot(source_slot) if source_slot >= 0 else -1
    cdef int source_rank = rank_from_slot(source_slot) if source_slot >= 0 else -1
    cdef int target_slot = -1
    cdef int target_front = -1
    cdef int before = cost
    cdef int amount = effect.amount
    cdef int minimum = effect.minimum
    cdef uint8_t action_type = _v2_cost_action_type_mask(self, kind, card)
    cdef bint matches = False

    if phase == 0:
        if source_owner == player:
            return cost
        if effect.op == V2_OP_ACTION_TAX and kind == TYPE_ABILITY and source_slot >= 0:
            if effect.target == V2_TARGET_OPPOSITE and pos >= 0:
                target_slot = slot_index(
                    player,
                    source_front,
                    source_rank,
                )
                matches = pos == target_slot
        elif effect.op == V2_OP_FRONT_CARD_TAX:
            if (
                action_type
                and (effect.card_type_mask == 0 or effect.card_type_mask & action_type)
                and pos >= 0
            ):
                matches = front_from_slot(pos) == source_front
        elif effect.op == V2_OP_PREPARED_ATTACH_TAX and kind == TYPE_EFFECT:
            if (
                state.pending_kind[0] == EFFECT_V2_TARGET
                and _v2_pending_effect(self, state).op == V2_OP_ATTACH_PREPARED
                and dest >= 0
            ):
                matches = front_from_slot(dest) == source_front
        elif effect.op == V2_OP_TACTIC_TAX and kind == TYPE_TACTIC and source_slot >= 0:
            if effect.target == V2_TARGET_SELF:
                matches = _v2_cost_tactic_targets_slot(action, source_slot)
            elif effect.target == V2_TARGET_DIRECTLY_BEHIND and source_rank < RANK_REAR:
                target_slot = slot_index(
                    source_owner,
                    source_front,
                    source_rank + 1,
                )
                matches = _v2_cost_tactic_targets_slot(action, target_slot)
            elif effect.target == V2_TARGET_OTHER_FRIENDLY_SAME_FRONT:
                target_slot = dest if dest >= 0 else pos
                matches = (
                    target_slot >= 0
                    and owner_from_slot(target_slot) == source_owner
                    and front_from_slot(target_slot) == source_front
                    and target_slot != source_slot
                )
        if matches and amount > 0:
            cost += amount

    else:
        if source_owner != player:
            return cost
        if effect.op == V2_OP_GLOBAL_DISCOUNT:
            matches = (
                action_type
                and bool(effect.card_type_mask & action_type)
            )
            if matches:
                cost = _v2_cost_reduce(cost, amount, minimum)
        elif effect.op == V2_OP_GLOBAL_DISCOUNT_SPLIT:
            if action_type and effect.card_type_mask & action_type:
                cost = _v2_cost_reduce(cost, amount, minimum)
            elif action_type and effect.card_type_mask2 & action_type:
                cost = _v2_cost_reduce(
                    cost, effect.amount2, effect.minimum2
                )
        elif effect.op == V2_OP_CLASS_PLAY_DISCOUNT:
            matches = (
                action_type
                and card >= 0
                and bool(self.class_mask[card] & effect.class_mask)
            )
            if matches:
                cost = _v2_cost_reduce(cost, amount, minimum)
        elif effect.op == V2_OP_FRONT_PRESENCE_DISCOUNT:
            if (
                action_type
                and (effect.card_type_mask == 0 or effect.card_type_mask & action_type)
                and pos >= 0
            ):
                target_front = front_from_slot(pos)
                if _v2_front_has_class(
                    self, state, player, target_front, effect.class_mask
                ):
                    cost = _v2_cost_reduce(cost, amount, minimum)
        elif effect.op == V2_OP_FRONT_TACTIC_DISCOUNT:
            if (
                kind == TYPE_TACTIC
                and source_front >= 0
                and _v2_cost_action_affects_front(self, action, source_front)
            ):
                cost = _v2_cost_reduce(cost, amount, minimum)
        elif effect.op == V2_OP_SLOT_DISCOUNT:
            if (
                source_slot >= 0
                and pos == source_slot
                and action_type
                and (effect.card_type_mask == 0 or effect.card_type_mask & action_type)
            ):
                cost = _v2_cost_reduce(cost, amount, minimum)
        elif effect.op == V2_OP_TACTIC_FRONT_PRESENCE_DISCOUNT and kind == TYPE_TACTIC:
            for target_front in range(FRONT_COUNT):
                if (
                    _v2_cost_action_affects_front(self, action, target_front)
                    and _v2_front_has_class(
                        self, state, player, target_front, effect.class_mask
                    )
                ):
                    cost = _v2_cost_reduce(cost, amount, minimum)
                    break
        elif effect.op == V2_OP_MANEUVER_COST_CLASS and kind == TYPE_MANEUVER:
            if (
                pos >= 0
                and _v2_slot_has_any_class(
                    self, state, pos, effect.class_mask
                )
                and amount < cost
            ):
                cost = amount if amount > 0 else 0

    if cost < before:
        _fe_record_command_diag(
            self,
            COMMAND_DIAG_DISCOUNT,
            COMMAND_DETAIL_CARD_EFFECT,
            player,
            source_card,
            before - cost,
            before,
        )
    return cost


cdef inline int _v2_cost_apply_component(
    FastEngine self,
    FastState state,
    int player,
    uint64_t action,
    int source_slot,
    int source_card,
    int mode,
    int suppression_bit,
    int phase,
    int cost,
) noexcept:
    cdef int i
    cdef V2EffectSpec* effect
    if source_card < 0:
        return cost
    if suppression_bit and state.suppression_mask[source_slot] & suppression_bit:
        return cost
    for i in range(self.v2_effect_count[source_card][mode]):
        effect = &self.v2_effects[source_card][mode][i]
        if not _v2_effect_is_live_timing(state, source_slot, effect):
            continue
        cost = _v2_cost_apply_effect(
            self,
            state,
            player,
            action,
            owner_from_slot(source_slot),
            source_slot,
            source_card,
            effect,
            phase,
            cost,
        )
    return cost


cdef int _v2_adjust_command_cost(
    FastEngine self,
    FastState state,
    int player,
    uint64_t action,
    int cost,
) noexcept:
    cdef int phase, source_slot, source_owner, card, mode, i, ix
    cdef V2EffectSpec* effect
    for phase in range(2):
        for source_slot in range(SLOT_COUNT):
            if state.force[source_slot] < 0:
                continue
            card = state.force[source_slot]
            mode = _v2_mode_for_force(self, card)
            cost = _v2_cost_apply_component(
                self, state, player, action, source_slot, card, mode,
                0, phase, cost,
            )
            card = state.bond[source_slot]
            if card >= 0:
                cost = _v2_cost_apply_component(
                    self, state, player, action, source_slot, card,
                    V2_MODE_DEFAULT, SUPPRESS_BOND_TEXT, phase, cost,
                )
            card = state.name[source_slot]
            if card >= 0:
                cost = _v2_cost_apply_component(
                    self, state, player, action, source_slot, card,
                    _v2_mode_for_name(self, card), SUPPRESS_NAME_TEXT,
                    phase, cost,
                )

        # Ongoing Narrative cost effects have no board source. Their current
        # canonical cost mechanics are all continuous and controller-scoped.
        for source_owner in range(PLAYER_COUNT):
            for i in range(self.ongoing_narrative_limit):
                ix = source_owner * NARRATIVE_SLOTS_PER_PLAYER + i
                card = state.narrative[ix]
                if card < 0:
                    continue
                for mode in range(self.v2_effect_count[card][V2_MODE_DEFAULT]):
                    effect = &self.v2_effects[card][V2_MODE_DEFAULT][mode]
                    if effect.timing != V2_TIMING_CONTINUOUS:
                        continue
                    cost = _v2_cost_apply_effect(
                        self, state, player, action, source_owner, -1,
                        card, effect, phase, cost,
                    )

        # Temporary V2 marker scaffolding is part of the native state contract.
        # Consume it in cost calculation so ACTION-created effects can share
        # the same ordering as persistent card text.
        if phase == 0:
            for i in range(state.tax_len):
                if (
                    state.tax_target_player[i] == player
                    and (
                        state.tax_expires_turn[i] < 0
                        or state.turn_number <= state.tax_expires_turn[i]
                    )
                    and _v2_cost_action_affects_front(
                        self, action, state.tax_front[i]
                    )
                ):
                    card = action_card(action)
                    mode = _v2_cost_action_type_mask(
                        self, action_kind(action), card
                    )
                    if (
                        state.tax_card_type_mask[i] == 0
                        or state.tax_card_type_mask[i] == 255
                        or state.tax_card_type_mask[i] & mode
                    ):
                        cost += state.tax_amount[i]
        else:
            if action_pos(action) >= 0:
                for i in range(state.discount_len):
                    if (
                        state.discount_target_player[i] == player
                        and state.discount_slot[i] == action_pos(action)
                        and (
                            state.discount_expires_turn[i] < 0
                            or state.turn_number <= state.discount_expires_turn[i]
                        )
                    ):
                        card = action_card(action)
                        mode = _v2_cost_action_type_mask(
                            self, action_kind(action), card
                        )
                        if (
                            state.discount_card_type_mask[i] == 0
                            or state.discount_card_type_mask[i] == 255
                            or state.discount_card_type_mask[i] & mode
                        ):
                            cost = _v2_cost_reduce(
                                cost,
                                state.discount_amount[i],
                                state.discount_minimum[i],
                            )
    return cost if cost > 0 else 0


cdef inline int _v2_ability_command_cost(
    FastEngine self,
    uint64_t action,
) noexcept:
    cdef int card = action_card(action)
    cdef int aux = <int>action_extra(action)
    cdef int mode, effect_index
    if card < 0:
        return 0
    if aux & V2_ABILITY_NARRATIVE_FLAG:
        aux &= ~V2_ABILITY_NARRATIVE_FLAG
    mode = _v2_pending_mode(aux)
    effect_index = _v2_pending_effect_index(aux)
    if (
        mode < V2_MODE_DEFAULT or mode > V2_MODE_NAME
        or effect_index < 0
        or effect_index >= self.v2_effect_count[card][mode]
    ):
        return 0
    return self.v2_effects[card][mode][effect_index].activation_cost


cdef inline int _fe_command_cost_fast(
    FastEngine self,
    FastState state,
    uint64_t action,
) noexcept:
    cdef int kind, card, pos, target_front=-1, cost, discount, rear, support, strat
    cdef int selected, i, controller, dest, direction, before_cost, saved
    cdef int target_rank=-1, supply_slot=-1, supply_discount=0, supply_minimum_cost=0
    cdef int source_card=-1, local_source=-1, local_discount=0, discount_detail=0
    cdef int discount_minimum_cost=0, local_minimum_cost=0
    cdef uint32_t extra
    cdef int player = state.active_player
    kind = action_kind(action)
    if kind == TYPE_PASS or kind == TYPE_END_TURN or kind == TYPE_CYCLE:
        return 0
    if kind == TYPE_EFFECT:
        if (
            state.pending_len > 0
            and state.pending_kind[0] == EFFECT_V2_TARGET
            and _v2_pending_effect(self, state).op == V2_OP_ATTACH_PREPARED
        ):
            return _v2_adjust_command_cost(self, state, player, action, 0)
        return 0
    if kind == TYPE_ABILITY:
        return _v2_adjust_command_cost(
            self, state, player, action, _v2_ability_command_cost(self, action)
        )
    if kind == TYPE_MANEUVER:
        pos = action_pos(action)
        dest = action_dest(action)
        direction = (
            DIRECTION_LEFT if front_from_slot(dest) < front_from_slot(pos) else DIRECTION_RIGHT
        )
        for i in range(state.constraint_len):
            if (
                state.constraint_player[i] == player
                and state.constraint_activate_turn[i] != CONSTRAINT_ACTIVATE_NEXT_TURN
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
                    and state.stratagem_revealed[controller]
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
            return _v2_adjust_command_cost(
                self, state, player, action, cost if cost > 0 else 0
            )
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
        return _v2_adjust_command_cost(
            self, state, player, action, self.maneuver_command_cost
        )
    card = action_card(action)
    if card < 0:
        return 0
    # The printed Hero seal has independent Force (top) and Name (bottom)
    # prices. Normal cards use a single printed Command price.
    if self.card_type[card] == CARD_HERO and kind == TYPE_NAME:
        cost = self.hero_name_command_cost[card]
    else:
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

    # Canonical V2 taxes are applied before canonical V2 discounts. Supply
    # then participates as the final positional reduction, with its own
    # printed minima.
    cost = _v2_adjust_command_cost(self, state, player, action, cost)
    if (
        (kind == TYPE_BOND or kind == TYPE_NAME)
        and pos >= 0
        and target_front >= 0
        and cost > 0
    ):
        target_rank = rank_from_slot(pos)
        if target_rank < RANK_REAR:
            supply_slot = slot_index(player, target_front, target_rank + 1)
            supply_discount = _v2_slot_supply_amount(self, state, supply_slot)
            if supply_discount > 0:
                before_cost = cost
                cost -= supply_discount
                supply_minimum_cost = 1 if kind == TYPE_NAME else 0
                if cost < supply_minimum_cost:
                    cost = supply_minimum_cost
                saved = before_cost - cost
                if saved > 0:
                    _fe_record_command_diag(
                        self, COMMAND_DIAG_DISCOUNT, COMMAND_DETAIL_SUPPLY_DISCOUNT,
                        player, -1, saved, before_cost,
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
    cdef int effect, amount
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
            _v2_apply_becomes_named_effects(
                self,
                state,
                player,
                state.name[slot],
                _v2_mode_for_name(self, state.name[slot]),
                slot,
            )
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
