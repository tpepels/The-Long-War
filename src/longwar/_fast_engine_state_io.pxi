cdef FastState _fe_from_game_state(FastEngine self, state):
    cdef FastState fast = FastState()
    cdef int p, i, f, r, slot, code, viewer, owner
    cdef object card_id, py_slot, narrative, strat, counter, constraint, before_collapse
    phase_map = {
        Phase.BATTLE: PHASE_BATTLE,
        Phase.COMPLETE: PHASE_COMPLETE,
    }

    for p in range(PLAYER_COUNT):
        if max(
            len(state.players[p].deck),
            len(state.players[p].hand),
            len(state.players[p].discard),
        ) > MAX_DECK:
            raise ValueError(
                f"Player {p}: a card zone exceeds native capacity {MAX_DECK}"
            )
        fast.deck_len[p] = len(state.players[p].deck)
        for i, card_id in enumerate(state.players[p].deck):
            code = self.id_to_code[card_id]
            fast.deck[p][i] = code
            fast.deck_counts[p][code] += 1
        fast.hand_len[p] = len(state.players[p].hand)
        for card_id in state.players[p].hand:
            fast.hand[p][self.id_to_code[card_id]] += 1
        fast.discard_len[p] = len(state.players[p].discard)
        for i, card_id in enumerate(state.players[p].discard):
            fast.discard[p][i] = self.id_to_code[card_id]

        fast.passed[p] = state.players[p].passed
        fast.command[p] = state.players[p].command
        fast.operations_this_battle[p] = state.operations_this_battle[p]
        fast.player_maneuver_count[p] = state.maneuvers_this_battle[p]
        fast.cards_played_this_turn_front_mask[p] = state.cards_played_this_turn_front_mask[p]
        fast.cards_played_this_battle_front_mask[p] = state.cards_played_this_battle_front_mask[p]
        fast.narratives_played_this_battle[p] = state.narratives_played_this_battle[p]
        fast.command_spent_this_battle[p] = state.command_spent_this_battle[p]
        fast.command_refunded_this_battle[p] = state.command_refunded_this_battle[p]
        fast.battle_start_command[p] = state.battle_start_command[p]
        fast.battle_start_hand_size[p] = state.battle_start_hand_size[p]
        fast.cards_drawn_this_battle[p] = state.cards_drawn_this_battle[p]
        fast.completion_count_this_battle[p] = state.completion_count_this_battle[p]
        fast.deck_reshuffles[p] = state.deck_reshuffles[p]
        fast.reshuffle_card_totals[p] = state.reshuffle_card_totals[p]
        fast.reshuffle_hand_card_totals[p] = state.reshuffle_hand_card_totals[p]
        fast.discarded_this_battle[p] = state.discarded_this_battle[p]
        fast.stratagem_used[p] = state.stratagem_used[p]
        fast.hero_used[p] = state.hero_used[p]

        strat = state.stratagems[p]
        if strat is not None:
            fast.stratagem[p] = self.id_to_code[strat.card_id]
            fast.stratagem_revealed[p] = bool(strat.revealed)
            fast.stratagem_known_to_mask[p] = int(strat.known_to_mask)
            for front_choice in strat.fronts:
                fast.stratagem_front_mask[p] |= 1 << int(front_choice)
            if strat.direction == Direction.LEFT:
                fast.stratagem_direction[p] = DIRECTION_LEFT
            elif strat.direction == Direction.RIGHT:
                fast.stratagem_direction[p] = DIRECTION_RIGHT
            for target_choice in strat.targets:
                fast.stratagem_target_mask[p] |= (
                    1
                    << slot_index(
                        int(target_choice[0]),
                        int(target_choice[1].front),
                        RANK_FRONT if target_choice[1].rank is Rank.FRONT else RANK_MIDDLE if target_choice[1].rank is Rank.MIDDLE else RANK_REAR,
                    )
                )

        for f in range(FRONT_COUNT):
            for r in range(RANK_COUNT):
                slot = slot_index(p, f, r)
                py_slot = state.board[p][f][r]
                if py_slot.force is not None:
                    fast.force[slot] = self.id_to_code[py_slot.force]
                if py_slot.bond is not None:
                    fast.bond[slot] = self.id_to_code[py_slot.bond]
                if py_slot.name is not None:
                    fast.name[slot] = self.id_to_code[py_slot.name]
                fast.exhausted[slot] = bool(py_slot.exhausted)
                fast.temporary[slot] = py_slot.temporary_strength
                fast.negative_one_markers[slot] = sum(
                    1 for marker in py_slot.negative_strength_markers if int(marker) == -1
                )
                fast.negative_two_markers[slot] = sum(
                    1 for marker in py_slot.negative_strength_markers if int(marker) == -2
                )
                fast.negative_three_markers[slot] = sum(
                    1 for marker in py_slot.negative_strength_markers if int(marker) == -3
                )
                fast.suppression_mask[slot] = int(py_slot.suppression_mask)
                fast.force_ability_used[slot] = bool(py_slot.force_ability_used)
                fast.bond_ability_used[slot] = bool(py_slot.bond_ability_used)
                fast.name_ability_used[slot] = bool(py_slot.name_ability_used)
                fast.name_suppression_immune[slot] = bool(py_slot.name_suppression_immune)
                fast.maneuver_count[slot] = int(py_slot.maneuvers_this_battle)
                fast.maneuvered_in_operation[slot] = bool(
                    py_slot.maneuvered_in_operation
                )
                if py_slot.maneuver_direction == Direction.LEFT:
                    fast.maneuver_direction[slot] = DIRECTION_LEFT
                elif py_slot.maneuver_direction == Direction.RIGHT:
                    fast.maneuver_direction[slot] = DIRECTION_RIGHT

        for i, narrative in enumerate(state.narratives[p][:self.ongoing_narrative_limit]):
            fast.narrative[p * NARRATIVE_SLOTS_PER_PLAYER + i] = self.id_to_code[narrative.card_id]
            fast.narrative_used[p * NARRATIVE_SLOTS_PER_PLAYER + i] = bool(narrative.triggered_this_battle)
            fast.narrative_trigger_mask[p * NARRATIVE_SLOTS_PER_PLAYER + i] = int(narrative.triggered_players_mask)
            if narrative.direction == Direction.LEFT:
                fast.narrative_direction[p * NARRATIVE_SLOTS_PER_PLAYER + i] = DIRECTION_LEFT
            elif narrative.direction == Direction.RIGHT:
                fast.narrative_direction[p * NARRATIVE_SLOTS_PER_PLAYER + i] = DIRECTION_RIGHT
            for front_choice in narrative.fronts:
                fast.narrative_front_mask[p * NARRATIVE_SLOTS_PER_PLAYER + i] |= 1 << int(front_choice)
            if narrative.target_position is not None and narrative.target_player is not None:
                fast.narrative_target_slot[p * NARRATIVE_SLOTS_PER_PLAYER + i] = slot_index(
                    int(narrative.target_player),
                    int(narrative.target_position.front),
                    RANK_FRONT if narrative.target_position.rank is Rank.FRONT else RANK_MIDDLE if narrative.target_position.rank is Rank.MIDDLE else RANK_REAR,
                )

    fast.active_player = state.active_player
    fast.battle = state.battle
    fast.phase = phase_map[state.phase]
    fast.winner = -1 if state.winner is None else state.winner
    fast.turn_number = state.turn_number
    fast.shuffle_seed = state.shuffle_seed
    fast.actions_this_turn = int(state.actions_this_turn)
    fast.turn_draw_pending = bool(state.turn_draw_pending)
    fast.closing_turns_remaining = int(state.closing_turns_remaining)
    fast.pass_len = len(state.pass_order)
    fast.cleanup_pending = (
        state.pending_draw_discard_for is not None
    )
    fast.pending_draw_count = int(state.pending_draw_count)
    fast.pending_draw_finish_operation = bool(
        state.pending_draw_finish_operation
    )
    resume_map = {
        None: RESUME_NONE,
        PendingResume.FINISH_OPERATION: RESUME_FINISH_OPERATION,
        PendingResume.BATTLE_RESOLUTION: RESUME_BATTLE_RESOLUTION,
        PendingResume.START_BATTLE: RESUME_START_BATTLE,
    }
    fast.pending_resume = resume_map.get(state.pending_resume, RESUME_NONE)
    fast.pending_resume_player = (
        -1 if state.pending_resume_player is None else int(state.pending_resume_player)
    )
    for p in range(PLAYER_COUNT):
        fast.free_maneuver_available[p] = bool(
            state.free_maneuver_available[p]
        )
        card_id = state.free_maneuver_source[p]
        fast.free_maneuver_source[p] = (
            -1 if card_id is None else self.id_to_code[card_id]
        )
    for i, effect_state in enumerate(state.pending_effects[:MAX_PENDING_EFFECTS]):
        fast.pending_kind[i] = int(effect_state.get("kind", EFFECT_NONE))
        fast.pending_player[i] = int(effect_state.get("player", -1))
        fast.pending_card[i] = int(effect_state.get("card", -1))
        fast.pending_command_source[i] = int(
            effect_state.get("command_source", -1)
        )
        fast.pending_source[i] = int(effect_state.get("source", -1))
        fast.pending_aux[i] = int(effect_state.get("aux", -1))
        fast.pending_source_mask[i] = int(effect_state.get("source_mask", 0))
        fast.pending_dest_mask[i] = int(effect_state.get("dest_mask", 0))
        fast.pending_flags[i] = int(effect_state.get("flags", 0))
        fast.pending_len += 1
    for i, constraint in enumerate(state.constraints[:MAX_CONSTRAINTS]):
        fast.constraint_kind[i] = {
            ConstraintKind.AFFECT_FRONT: CONSTRAINT_AFFECT_FRONT,
            ConstraintKind.MANEUVER: CONSTRAINT_MANEUVER,
            ConstraintKind.SPECIFIC_MANEUVER: CONSTRAINT_SPECIFIC_MANEUVER,
        }.get(constraint.kind, CONSTRAINT_NONE)
        fast.constraint_player[i] = int(constraint.player)
        fast.constraint_source_card[i] = self.id_to_code[constraint.source_card]
        fast.constraint_source_owner[i] = int(constraint.source_owner)
        fast.constraint_front[i] = (
            -1 if constraint.front is None else int(constraint.front)
        )
        fast.constraint_direction[i] = (
            DIRECTION_LEFT if constraint.direction == Direction.LEFT
            else DIRECTION_RIGHT if constraint.direction == Direction.RIGHT
            else DIRECTION_NONE
        )
        fast.constraint_source_slot[i] = (
            -1
            if constraint.source_position is None
            else slot_index(
                int(constraint.player),
                int(constraint.source_position.front),
                RANK_FRONT if constraint.source_position.rank is Rank.FRONT else RANK_MIDDLE if constraint.source_position.rank is Rank.MIDDLE else RANK_REAR,
            )
        )
        fast.constraint_activate_turn[i] = int(constraint.activate_turn)
        fast.constraint_flags[i] = (
            (CONSTRAINT_EXPIRES_AFTER_OPERATION if constraint.expires_after_operation else 0)
            | (CONSTRAINT_PERSISTS_BATTLE if constraint.persists_between_battles else 0)
            | (CONSTRAINT_ZERO_COST if constraint.zero_cost else 0)
            | (CONSTRAINT_DRAW_ON_SATISFY if constraint.draw_after_satisfied else 0)
            | (CONSTRAINT_DISCARD_SOURCE_NARRATIVE if constraint.discard_source_narrative else 0)
            | (CONSTRAINT_EXPIRES_END_OF_ACTIVATED_TURN if constraint.expires_end_of_activated_turn else 0)
        )
        fast.constraint_len += 1
    resolution_state = state.battle_resolution
    if resolution_state is not None:
        fast.resolution_stage = int(resolution_state.get("stage", RESOLUTION_NONE))
        lost_masks = resolution_state.get("lost_masks", (0, 0))
        drive_masks = resolution_state.get("drive_masks", (0, 0))
        protected_masks = resolution_state.get("protected_masks", (0, 0))
        front_loss_command_penalty = resolution_state.get("front_loss_command_penalty", (0, 0))
        for p in range(PLAYER_COUNT):
            fast.resolution_lost_mask[p] = int(lost_masks[p])
            fast.resolution_drive_mask[p] = int(drive_masks[p])
            fast.resolution_protected_mask[p] = int(protected_masks[p])
            fast.resolution_front_loss_command_penalty[p] = int(front_loss_command_penalty[p])
        fast.resolution_suppressed_mask = int(
            resolution_state.get("suppressed_mask", 0)
        )
        contribution = resolution_state.get("contribution_front", ())
        for i in range(min(SLOT_COUNT, len(contribution))):
            fast.resolution_contribution_front[i] = int(contribution[i])
        fast.resolution_cursor = int(resolution_state.get("cursor", 0))
        fast.resolution_starter = int(resolution_state.get("starter", -1))
    for i, p in enumerate(state.pass_order):
        fast.pass_order[i] = p

    for viewer in range(PLAYER_COUNT):
        for owner in range(PLAYER_COUNT):
            counter = state.known_hidden_counter(viewer, owner, ObservationZone.HAND)
            for card_id, count in counter.items():
                fast.known_hidden[viewer][owner][self.id_to_code[card_id]] = count

    if len(state.tax_markers) > MAX_TAX_MARKERS:
        raise ValueError("Too many V2 Tax markers for native state")
    for i, marker in enumerate(state.tax_markers[:MAX_TAX_MARKERS]):
        fast.tax_owner[i] = int(marker.owner)
        fast.tax_target_player[i] = int(marker.target_player)
        fast.tax_front[i] = int(marker.front)
        fast.tax_amount[i] = int(marker.amount)
        fast.tax_card_type_mask[i] = _v2_card_type_mask(marker.card_types)
        fast.tax_expires_turn[i] = (
            -1 if marker.expires_turn is None else int(marker.expires_turn)
        )
        fast.tax_len += 1

    if len(state.slot_discounts) > MAX_SLOT_DISCOUNTS:
        raise ValueError("Too many V2 slot discounts for native state")
    for i, discount in enumerate(state.slot_discounts[:MAX_SLOT_DISCOUNTS]):
        fast.discount_owner[i] = int(discount.owner)
        fast.discount_target_player[i] = int(discount.target_player)
        fast.discount_slot[i] = slot_index(
            int(discount.target_player),
            int(discount.position.front),
            RANK_FRONT if discount.position.rank is Rank.FRONT
            else RANK_MIDDLE if discount.position.rank is Rank.MIDDLE
            else RANK_REAR,
        )
        fast.discount_amount[i] = int(discount.amount)
        fast.discount_minimum[i] = int(discount.minimum)
        fast.discount_card_type_mask[i] = _v2_card_type_mask(discount.card_types)
        fast.discount_expires_turn[i] = (
            -1 if discount.expires_turn is None else int(discount.expires_turn)
        )
        fast.discount_len += 1

    snapshot = state.last_battle_snapshot
    if snapshot is not None:
        fast.last_battle_valid = 1
        fast.last_battle = int(snapshot.get("battle", 0))
        front_scores = snapshot.get("front_scores", ())
        for f in range(min(FRONT_COUNT, len(front_scores))):
            fast.last_front_scores[f][0] = int(front_scores[f][0])
            fast.last_front_scores[f][1] = int(front_scores[f][1])
        front_results = snapshot.get("front_results", ())
        for f in range(min(FRONT_COUNT, len(front_results))):
            if front_results[f] == 0:
                fast.last_lost_mask[1] |= <uint8_t>(1 << f)
            elif front_results[f] == 1:
                fast.last_lost_mask[0] |= <uint8_t>(1 << f)
        for p in range(PLAYER_COUNT):
            fast.last_command_start[p] = int(
                snapshot.get("command_start", (0, 0))[p]
            )
            fast.last_command_spent[p] = int(
                snapshot.get("command_spent", (0, 0))[p]
            )
            fast.last_command_refunded[p] = int(
                snapshot.get("command_refunded", (0, 0))[p]
            )
            fast.last_command_before_collapse[p] = int(
                snapshot.get("command_before_collapse", (0, 0))[p]
            )
            fast.last_front_loss_command_penalty[p] = int(
                snapshot.get("front_loss_command_penalty", (0, 0))[p]
            )
            fast.last_recovery_actual[p] = int(
                snapshot.get("recovery_actual", (0, 0))[p]
            )
            fast.last_command_remaining[p] = int(
                snapshot.get("command_remaining", (0, 0))[p]
            )
            fast.last_deck_remaining[p] = int(
                snapshot.get("deck_remaining", (0, 0))[p]
            )
            fast.last_hand_size[p] = int(
                snapshot.get("hand_size", (0, 0))[p]
            )
            fast.last_battle_start_hand_size[p] = int(
                snapshot.get("battle_start_hand_size", (0, 0))[p]
            )
            fast.last_cards_drawn[p] = int(
                snapshot.get("cards_drawn", (0, 0))[p]
            )
            fast.last_completion_count[p] = int(
                snapshot.get("completion_count", (0, 0))[p]
            )
            fast.last_operations[p] = int(
                snapshot.get("operations", (0, 0))[p]
            )
        pass_snapshot = snapshot.get("pass_order", ())
        fast.last_pass_len = min(PLAYER_COUNT, len(pass_snapshot))
        for i in range(fast.last_pass_len):
            fast.last_pass_order[i] = int(pass_snapshot[i])

    return fast


cdef FastState _fe_determinize_hidden_zones(
    FastEngine self,
    FastState base,
    int viewer,
    object viewer_deck,
    object opponent_hand,
    object opponent_deck,
    object opponent_stratagem,
):
    """Clone one packed root and replace every zone hidden from the viewer."""
    cdef FastState fast = FastState()
    cdef int opponent, i, code
    cdef object card_id

    if viewer < 0 or viewer >= PLAYER_COUNT:
        raise ValueError(f"viewer must be in range(0, {PLAYER_COUNT})")
    opponent = other_player(viewer)
    if len(viewer_deck) != base.deck_len[viewer]:
        raise ValueError("viewer deck sample changed observable deck size")
    if len(opponent_hand) != base.hand_len[opponent]:
        raise ValueError("opponent hand sample changed observable hand size")
    if len(opponent_deck) != base.deck_len[opponent]:
        raise ValueError("opponent deck sample changed observable deck size")

    fast.copy_from_fast(base)

    for code in range(MAX_CARDS):
        fast.deck_counts[viewer][code] = 0
        fast.deck_counts[opponent][code] = 0
        fast.hand[opponent][code] = 0

    for i in range(MAX_DECK):
        fast.deck[viewer][i] = -1
        fast.deck[opponent][i] = -1

    fast.deck_len[viewer] = len(viewer_deck)
    for i, card_id in enumerate(viewer_deck):
        code = self.id_to_code[card_id]
        fast.deck[viewer][i] = code
        fast.deck_counts[viewer][code] += 1

    fast.hand_len[opponent] = len(opponent_hand)
    for card_id in opponent_hand:
        fast.hand[opponent][self.id_to_code[card_id]] += 1

    fast.deck_len[opponent] = len(opponent_deck)
    for i, card_id in enumerate(opponent_deck):
        code = self.id_to_code[card_id]
        fast.deck[opponent][i] = code
        fast.deck_counts[opponent][code] += 1

    if fast.stratagem[opponent] >= 0 and not fast.stratagem_revealed[opponent]:
        if opponent_stratagem is None:
            raise ValueError("hidden opponent Stratagem requires a sampled identity")
        fast.stratagem[opponent] = self.id_to_code[opponent_stratagem]
    elif opponent_stratagem is not None:
        raise ValueError("sampled opponent Stratagem supplied for a public/empty slot")

    return fast


cdef dict _fe_export_state(FastEngine self, FastState state):
    cdef int p, f, r, i, card, viewer, owner, ix
    cdef int lost0 = 0
    cdef int lost1 = 0
    cdef object last_snapshot = None

    if state.last_battle_valid:
        lost0 = popcount16(state.last_lost_mask[0] & FRONT_MASK)
        lost1 = popcount16(state.last_lost_mask[1] & FRONT_MASK)
        last_snapshot = {
            "battle": state.last_battle,
            "front_scores": [
                [
                    state.last_front_scores[f][0],
                    state.last_front_scores[f][1],
                ]
                for f in range(FRONT_COUNT)
            ],
            "front_results": [
                (
                    1
                    if state.last_lost_mask[0] & (1 << f)
                    else 0
                    if state.last_lost_mask[1] & (1 << f)
                    else None
                )
                for f in range(FRONT_COUNT)
            ],
            "fronts_lost": [lost0, lost1],
            "command_start": [
                state.last_command_start[0],
                state.last_command_start[1],
            ],
            "command_spent": [
                state.last_command_spent[0],
                state.last_command_spent[1],
            ],
            "command_refunded": [
                state.last_command_refunded[0],
                state.last_command_refunded[1],
            ],
            "command_before_collapse": [
                state.last_command_before_collapse[0],
                state.last_command_before_collapse[1],
            ],
            "front_loss_command_penalty": [
                state.last_front_loss_command_penalty[0],
                state.last_front_loss_command_penalty[1],
            ],
            "recovery_actual": [
                state.last_recovery_actual[0],
                state.last_recovery_actual[1],
            ],
            "command_remaining": [
                state.last_command_remaining[0],
                state.last_command_remaining[1],
            ],
            "deck_remaining": [
                state.last_deck_remaining[0],
                state.last_deck_remaining[1],
            ],
            "hand_size": [
                state.last_hand_size[0],
                state.last_hand_size[1],
            ],
            "battle_start_hand_size": [
                state.last_battle_start_hand_size[0],
                state.last_battle_start_hand_size[1],
            ],
            "cards_drawn": [
                state.last_cards_drawn[0],
                state.last_cards_drawn[1],
            ],
            "completion_count": [
                state.last_completion_count[0],
                state.last_completion_count[1],
            ],
            "operations": [
                state.last_operations[0],
                state.last_operations[1],
            ],
            "pass_order": [
                state.last_pass_order[i]
                for i in range(state.last_pass_len)
            ],
        }

    return {
        "phase": (
            Phase.BATTLE.value
            if state.phase == PHASE_BATTLE
            else Phase.COMPLETE.value
        ),
        "battle": state.battle,
        "active_player": state.active_player,
        "winner": None if state.winner < 0 else state.winner,
        "turn_number": state.turn_number,
        "shuffle_seed": state.shuffle_seed,
        "players": [
            {
                "deck": [
                    self.card_ids[state.deck[p][i]]
                    for i in range(state.deck_len[p])
                ],
                "hand": [
                    self.card_ids[card]
                    for card in range(self.n_cards)
                    for _ in range(state.hand[p][card])
                ],
                "discard": [
                    self.card_ids[state.discard[p][i]]
                    for i in range(state.discard_len[p])
                ],
                "passed": bool(state.passed[p]),
                "command": state.command[p],
            }
            for p in range(PLAYER_COUNT)
        ],
        "board": [
            [
                [
                    {
                        "force": (
                            None
                            if state.force[slot_index(p, f, r)] < 0
                            else self.card_ids[
                                state.force[slot_index(p, f, r)]
                            ]
                        ),
                        "bond": (
                            None
                            if state.bond[slot_index(p, f, r)] < 0
                            else self.card_ids[
                                state.bond[slot_index(p, f, r)]
                            ]
                        ),
                        "name": (
                            None
                            if state.name[slot_index(p, f, r)] < 0
                            else self.card_ids[
                                state.name[slot_index(p, f, r)]
                            ]
                        ),
                        "exhausted": bool(
                            state.exhausted[slot_index(p, f, r)]
                        ),
                        "temporary_strength": (
                            state.temporary[slot_index(p, f, r)]
                        ),
                        "negative_strength_markers": (
                            [-1] * state.negative_one_markers[slot_index(p, f, r)]
                            + [-2] * state.negative_two_markers[slot_index(p, f, r)]
                            + [-3] * state.negative_three_markers[slot_index(p, f, r)]
                        ),
                        "suppression_mask": state.suppression_mask[slot_index(p, f, r)],
                        "force_ability_used": bool(state.force_ability_used[slot_index(p, f, r)]),
                        "bond_ability_used": bool(state.bond_ability_used[slot_index(p, f, r)]),
                        "name_ability_used": bool(state.name_ability_used[slot_index(p, f, r)]),
                        "name_suppression_immune": bool(state.name_suppression_immune[slot_index(p, f, r)]),
                        "maneuvers_this_battle": (
                            state.maneuver_count[slot_index(p, f, r)]
                        ),
                        "maneuvered_in_operation": bool(
                            state.maneuvered_in_operation[slot_index(p, f, r)]
                        ),
                        "maneuver_direction": (
                            Direction.LEFT.value
                            if state.maneuver_direction[slot_index(p, f, r)] == DIRECTION_LEFT
                            else Direction.RIGHT.value
                            if state.maneuver_direction[slot_index(p, f, r)] == DIRECTION_RIGHT
                            else None
                        ),
                    }
                    for r in range(RANK_COUNT)
                ]
                for f in range(FRONT_COUNT)
            ]
            for p in range(PLAYER_COUNT)
        ],
        "narratives": [
            [
                {
                    "card_id": self.card_ids[state.narrative[p * NARRATIVE_SLOTS_PER_PLAYER + i]],
                    "front_mask": state.narrative_front_mask[p * NARRATIVE_SLOTS_PER_PLAYER + i],
                    "triggered_this_battle": bool(state.narrative_used[p * NARRATIVE_SLOTS_PER_PLAYER + i]),
                    "triggered_players_mask": state.narrative_trigger_mask[p * NARRATIVE_SLOTS_PER_PLAYER + i],
                    "direction": (
                        Direction.LEFT.value
                        if state.narrative_direction[p * NARRATIVE_SLOTS_PER_PLAYER + i] == DIRECTION_LEFT
                        else Direction.RIGHT.value
                        if state.narrative_direction[p * NARRATIVE_SLOTS_PER_PLAYER + i] == DIRECTION_RIGHT
                        else None
                    ),
                    "target_slot": (
                        None
                        if state.narrative_target_slot[p * NARRATIVE_SLOTS_PER_PLAYER + i] < 0
                        else state.narrative_target_slot[p * NARRATIVE_SLOTS_PER_PLAYER + i]
                    ),
                }
                for i in range(self.ongoing_narrative_limit)
                if state.narrative[p * NARRATIVE_SLOTS_PER_PLAYER + i] >= 0
            ]
            for p in range(PLAYER_COUNT)
        ],
        "stratagems": [
            (
                None
                if state.stratagem[p] < 0
                else {
                    "card_id": self.card_ids[state.stratagem[p]],
                    "front_mask": state.stratagem_front_mask[p],
                    "direction": state.stratagem_direction[p],
                    "target_mask": state.stratagem_target_mask[p],
                    "revealed": bool(state.stratagem_revealed[p]),
                    "known_to_mask": state.stratagem_known_to_mask[p],
                }
            )
            for p in range(PLAYER_COUNT)
        ],
        "stratagem_used": [
            bool(state.stratagem_used[p])
            for p in range(PLAYER_COUNT)
        ],
        "hero_used": [
            int(state.hero_used[p])
            for p in range(PLAYER_COUNT)
        ],
        "discarded_this_battle": [
            state.discarded_this_battle[p]
            for p in range(PLAYER_COUNT)
        ],
        "command_spent_this_battle": [
            state.command_spent_this_battle[p]
            for p in range(PLAYER_COUNT)
        ],
        "command_refunded_this_battle": [
            state.command_refunded_this_battle[p]
            for p in range(PLAYER_COUNT)
        ],
        "battle_start_command": [
            state.battle_start_command[p]
            for p in range(PLAYER_COUNT)
        ],
        "battle_start_hand_size": [
            state.battle_start_hand_size[p]
            for p in range(PLAYER_COUNT)
        ],
        "cards_drawn_this_battle": [
            state.cards_drawn_this_battle[p]
            for p in range(PLAYER_COUNT)
        ],
        "completion_count_this_battle": [
            state.completion_count_this_battle[p]
            for p in range(PLAYER_COUNT)
        ],
        "operations_this_battle": [
            state.operations_this_battle[p]
            for p in range(PLAYER_COUNT)
        ],
        "actions_this_turn": state.actions_this_turn,
        "turn_draw_pending": bool(state.turn_draw_pending),
        "closing_turns_remaining": state.closing_turns_remaining,
        "maneuvers_this_battle": [
            state.player_maneuver_count[p]
            for p in range(PLAYER_COUNT)
        ],
        "cards_played_this_turn_front_mask": [
            state.cards_played_this_turn_front_mask[p]
            for p in range(PLAYER_COUNT)
        ],
        "cards_played_this_battle_front_mask": [
            state.cards_played_this_battle_front_mask[p]
            for p in range(PLAYER_COUNT)
        ],
        "narratives_played_this_battle": [
            state.narratives_played_this_battle[p]
            for p in range(PLAYER_COUNT)
        ],
        "deck_reshuffles": [
            state.deck_reshuffles[p]
            for p in range(PLAYER_COUNT)
        ],
        "reshuffle_card_totals": [
            state.reshuffle_card_totals[p]
            for p in range(PLAYER_COUNT)
        ],
        "reshuffle_hand_card_totals": [
            state.reshuffle_hand_card_totals[p]
            for p in range(PLAYER_COUNT)
        ],
        "pending_draw_discard_for": (
            state.active_player if state.cleanup_pending else None
        ),
        "pending_draw_count": state.pending_draw_count,
        "pending_draw_finish_operation": bool(
            state.pending_draw_finish_operation
        ),
        "pending_effects": [
            {
                "kind": state.pending_kind[i],
                "player": state.pending_player[i],
                "card": state.pending_card[i],
                "command_source": state.pending_command_source[i],
                "source": state.pending_source[i],
                "aux": state.pending_aux[i],
                "source_mask": state.pending_source_mask[i],
                "dest_mask": state.pending_dest_mask[i],
                "flags": state.pending_flags[i],
            }
            for i in range(state.pending_len)
        ],
        "pending_resume": (
            PendingResume.FINISH_OPERATION.value
            if state.pending_resume == RESUME_FINISH_OPERATION
            else PendingResume.BATTLE_RESOLUTION.value
            if state.pending_resume == RESUME_BATTLE_RESOLUTION
            else PendingResume.START_BATTLE.value
            if state.pending_resume == RESUME_START_BATTLE
            else None
        ),
        "pending_resume_player": (
            None if state.pending_resume_player < 0 else state.pending_resume_player
        ),
        "free_maneuver_available": [
            bool(state.free_maneuver_available[p])
            for p in range(PLAYER_COUNT)
        ],
        "free_maneuver_source": [
            None
            if state.free_maneuver_source[p] < 0
            else self.card_ids[state.free_maneuver_source[p]]
            for p in range(PLAYER_COUNT)
        ],
        "constraints": [
            {
                "source_card": self.card_ids[state.constraint_source_card[i]],
                "player": state.constraint_player[i],
                "kind": (
                    ConstraintKind.AFFECT_FRONT.value
                    if state.constraint_kind[i] == CONSTRAINT_AFFECT_FRONT
                    else ConstraintKind.MANEUVER.value
                    if state.constraint_kind[i] == CONSTRAINT_MANEUVER
                    else ConstraintKind.SPECIFIC_MANEUVER.value
                ),
                "source_owner": state.constraint_source_owner[i],
                "front": (
                    None
                    if state.constraint_front[i] < 0
                    else state.constraint_front[i]
                ),
                "direction": (
                    Direction.LEFT.value
                    if state.constraint_direction[i] == DIRECTION_LEFT
                    else Direction.RIGHT.value
                    if state.constraint_direction[i] == DIRECTION_RIGHT
                    else None
                ),
                "source_slot": (
                    None
                    if state.constraint_source_slot[i] < 0
                    else state.constraint_source_slot[i]
                ),
                "activate_turn": state.constraint_activate_turn[i],
                "expires_after_operation": bool(
                    state.constraint_flags[i] & CONSTRAINT_EXPIRES_AFTER_OPERATION
                ),
                "persists_between_battles": bool(
                    state.constraint_flags[i] & CONSTRAINT_PERSISTS_BATTLE
                ),
                "zero_cost": bool(
                    state.constraint_flags[i] & CONSTRAINT_ZERO_COST
                ),
                "draw_after_satisfied": (
                    1
                    if state.constraint_flags[i] & CONSTRAINT_DRAW_ON_SATISFY
                    else 0
                ),
                "discard_source_narrative": bool(
                    state.constraint_flags[i] & CONSTRAINT_DISCARD_SOURCE_NARRATIVE
                ),
                "expires_end_of_activated_turn": bool(
                    state.constraint_flags[i] & CONSTRAINT_EXPIRES_END_OF_ACTIVATED_TURN
                ),
            }
            for i in range(state.constraint_len)
        ],
        "battle_resolution": (
            None
            if state.resolution_stage == RESOLUTION_NONE
            else {
                "stage": state.resolution_stage,
                "lost_masks": [state.resolution_lost_mask[0], state.resolution_lost_mask[1]],
                "drive_masks": [state.resolution_drive_mask[0], state.resolution_drive_mask[1]],
                "protected_masks": [state.resolution_protected_mask[0], state.resolution_protected_mask[1]],
                "front_loss_command_penalty": [state.resolution_front_loss_command_penalty[0], state.resolution_front_loss_command_penalty[1]],
                "suppressed_mask": state.resolution_suppressed_mask,
                "contribution_front": [state.resolution_contribution_front[i] for i in range(SLOT_COUNT)],
                "cursor": state.resolution_cursor,
                "starter": state.resolution_starter,
            }
        ),
        "pass_order": [
            state.pass_order[i]
            for i in range(state.pass_len)
        ],
        "tax_markers": [
            {
                "owner": state.tax_owner[i],
                "target_player": state.tax_target_player[i],
                "front": state.tax_front[i],
                "amount": state.tax_amount[i],
                "card_type_mask": state.tax_card_type_mask[i],
                "expires_turn": (
                    None if state.tax_expires_turn[i] < 0
                    else state.tax_expires_turn[i]
                ),
            }
            for i in range(state.tax_len)
        ],
        "slot_discounts": [
            {
                "owner": state.discount_owner[i],
                "target_player": state.discount_target_player[i],
                "slot": state.discount_slot[i],
                "amount": state.discount_amount[i],
                "minimum": state.discount_minimum[i],
                "card_type_mask": state.discount_card_type_mask[i],
                "expires_turn": (
                    None if state.discount_expires_turn[i] < 0
                    else state.discount_expires_turn[i]
                ),
            }
            for i in range(state.discount_len)
        ],
        "known_hidden_hand": [
            [
                {
                    self.card_ids[card]:
                        state.known_hidden[viewer][owner][card]
                    for card in range(self.n_cards)
                    if state.known_hidden[viewer][owner][card]
                }
                for owner in range(PLAYER_COUNT)
            ]
            for viewer in range(PLAYER_COUNT)
        ],
        "last_battle_snapshot": last_snapshot,
    }

cdef dict _fe_debug_snapshot(FastEngine self, FastState state):
    cdef int p, f, r, slot, i, card
    return {
        "phase": state.phase,
        "battle": state.battle,
        "active_player": state.active_player,
        "winner": state.winner,
        "turn_number": state.turn_number,
        "passed": [bool(state.passed[0]), bool(state.passed[1])],
        "pass_order": [state.pass_order[i] for i in range(state.pass_len)],
        "discarded_this_battle": [state.discarded_this_battle[0], state.discarded_this_battle[1]],
        "command": [state.command[0], state.command[1]],
        "operations_this_battle": [state.operations_this_battle[0], state.operations_this_battle[1]],
        "actions_this_turn": state.actions_this_turn,
        "turn_draw_pending": bool(state.turn_draw_pending),
        "closing_turns_remaining": state.closing_turns_remaining,
        "pending_draw_discard_for": state.active_player if state.cleanup_pending else None,
        "pending_draw_count": state.pending_draw_count,
        "pending_draw_finish_operation": bool(state.pending_draw_finish_operation),
        "hands": [
            {self.card_ids[card]: state.hand[p][card] for card in range(self.n_cards) if state.hand[p][card]}
            for p in range(PLAYER_COUNT)
        ],
        "decks": [
            [self.card_ids[state.deck[p][i]] for i in range(state.deck_len[p])]
            for p in range(PLAYER_COUNT)
        ],
        "discards": [
            [self.card_ids[state.discard[p][i]] for i in range(state.discard_len[p])]
            for p in range(PLAYER_COUNT)
        ],
        "board": [
            [
                (
                    None if state.force[slot_index(p, f, r)] < 0 else self.card_ids[state.force[slot_index(p, f, r)]],
                    None if state.bond[slot_index(p, f, r)] < 0 else self.card_ids[state.bond[slot_index(p, f, r)]],
                    None if state.name[slot_index(p, f, r)] < 0 else self.card_ids[state.name[slot_index(p, f, r)]],
                    state.temporary[slot_index(p, f, r)],
                )
                for f in range(FRONT_COUNT) for r in range(RANK_COUNT)
            ]
            for p in range(PLAYER_COUNT)
        ],
        "narratives": [
            [
                None if state.narrative[p * NARRATIVE_SLOTS_PER_PLAYER + f] < 0 else (self.card_ids[state.narrative[p * NARRATIVE_SLOTS_PER_PLAYER + f]], True)
                for f in range(FRONT_COUNT)
            ]
            for p in range(PLAYER_COUNT)
        ],
        "stratagems": [
            None if state.stratagem[p] < 0 else (self.card_ids[state.stratagem[p]], bool(state.stratagem_revealed[p]))
            for p in range(PLAYER_COUNT)
        ],
        "stratagem_used": [bool(state.stratagem_used[0]), bool(state.stratagem_used[1])],
        "hero_used": [bool(state.hero_used[0]), bool(state.hero_used[1])],
    }
