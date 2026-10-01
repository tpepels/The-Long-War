cdef FastState _fe_from_game_state(FastEngine self, state):
    cdef FastState fast = FastState()
    cdef int p, i, f, r, slot, code, viewer, owner
    cdef object card_id, py_slot, story, strat, counter, constraint, before_collapse
    phase_map = {
        "battle": PHASE_BATTLE,
        "complete": PHASE_COMPLETE,
    }

    for p in range(2):
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
            fast.stratagem_revealed[p] = 1
            for front_choice in strat.fronts:
                fast.stratagem_front_mask[p] |= 1 << int(front_choice)
            if strat.direction == "left":
                fast.stratagem_direction[p] = 1
            elif strat.direction == "right":
                fast.stratagem_direction[p] = 2
            for target_choice in strat.targets:
                fast.stratagem_target_mask[p] |= (
                    1
                    << slot_index(
                        int(target_choice[0]),
                        int(target_choice[1].front),
                        0 if target_choice[1].rank.value == "front" else 1,
                    )
                )

        for f in range(4):
            for r in range(2):
                slot = slot_index(p, f, r)
                py_slot = state.board[p][f][r]
                if py_slot.force is not None:
                    fast.force[slot] = self.id_to_code[py_slot.force]
                if py_slot.bond is not None:
                    fast.bond[slot] = self.id_to_code[py_slot.bond]
                if py_slot.name is not None:
                    fast.name[slot] = self.id_to_code[py_slot.name]
                fast.temporary[slot] = py_slot.temporary_strength
                fast.maneuver_count[slot] = int(py_slot.maneuvers_this_battle)
                fast.maneuvered_in_operation[slot] = bool(
                    py_slot.maneuvered_in_operation
                )
                if py_slot.maneuver_direction == "left":
                    fast.maneuver_direction[slot] = 1
                elif py_slot.maneuver_direction == "right":
                    fast.maneuver_direction[slot] = 2

        for i, story in enumerate(state.stories[p][:self.ongoing_story_limit]):
            fast.narrative[p * 4 + i] = self.id_to_code[story.card_id]
            fast.narrative_revealed[p * 4 + i] = 1
            fast.narrative_used[p * 4 + i] = bool(story.triggered_this_battle)
            fast.narrative_trigger_mask[p * 4 + i] = int(story.triggered_players_mask)
            if story.direction == "left":
                fast.narrative_direction[p * 4 + i] = 1
            elif story.direction == "right":
                fast.narrative_direction[p * 4 + i] = 2
            for front_choice in story.fronts:
                fast.narrative_front_mask[p * 4 + i] |= 1 << int(front_choice)
            if story.target_position is not None and story.target_player is not None:
                fast.narrative_target_slot[p * 4 + i] = slot_index(
                    int(story.target_player),
                    int(story.target_position.front),
                    0 if story.target_position.rank.value == "front" else 1,
                )

    fast.active_player = state.active_player
    fast.battle = state.battle
    fast.phase = phase_map[state.phase.value]
    fast.winner = -1 if state.winner is None else state.winner
    fast.turn_number = state.turn_number
    fast.shuffle_seed = state.shuffle_seed
    fast.pass_len = len(state.pass_order)
    fast.pass_closing_turns_remaining = int(state.pass_closing_turns_remaining)
    fast.cleanup_pending = (
        state.pending_draw_discard_for is not None
    )
    fast.pending_draw_count = int(state.pending_draw_count)
    fast.pending_draw_finish_operation = bool(
        state.pending_draw_finish_operation
    )
    resume_map = {
        None: RESUME_NONE,
        "finish_operation": RESUME_FINISH_OPERATION,
        "battle_resolution": RESUME_BATTLE_RESOLUTION,
        "start_battle": RESUME_START_BATTLE,
    }
    fast.pending_resume = resume_map.get(state.pending_resume, RESUME_NONE)
    fast.pending_resume_player = (
        -1 if state.pending_resume_player is None else int(state.pending_resume_player)
    )
    fast.free_maneuver_available[0] = bool(state.free_maneuver_available[0])
    fast.free_maneuver_available[1] = bool(state.free_maneuver_available[1])
    for p in range(2):
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
            "affect_front": CONSTRAINT_AFFECT_FRONT,
            "maneuver": CONSTRAINT_MANEUVER,
            "specific_maneuver": CONSTRAINT_SPECIFIC_MANEUVER,
        }.get(constraint.kind.value, CONSTRAINT_NONE)
        fast.constraint_player[i] = int(constraint.player)
        fast.constraint_source_card[i] = self.id_to_code[constraint.source_card]
        fast.constraint_source_owner[i] = int(constraint.source_owner)
        fast.constraint_front[i] = (
            -1 if constraint.front is None else int(constraint.front)
        )
        fast.constraint_direction[i] = (
            1 if constraint.direction == "left"
            else 2 if constraint.direction == "right"
            else 0
        )
        fast.constraint_source_slot[i] = (
            -1
            if constraint.source_position is None
            else slot_index(
                int(constraint.player),
                int(constraint.source_position.front),
                0 if constraint.source_position.rank.value == "front" else 1,
            )
        )
        fast.constraint_activate_turn[i] = int(constraint.activate_turn)
        fast.constraint_flags[i] = (
            (CONSTRAINT_EXPIRES_AFTER_OPERATION if constraint.expires_after_operation else 0)
            | (CONSTRAINT_PERSISTS_BATTLE if constraint.persists_between_battles else 0)
            | (CONSTRAINT_ZERO_COST if constraint.zero_cost else 0)
            | (CONSTRAINT_DRAW_ON_SATISFY if constraint.draw_after_satisfied else 0)
            | (CONSTRAINT_DISCARD_SOURCE_STORY if constraint.discard_source_story else 0)
        )
        fast.constraint_len += 1
    resolution_state = state.battle_resolution
    if resolution_state is not None:
        fast.resolution_stage = int(resolution_state.get("stage", RESOLUTION_NONE))
        lost_masks = resolution_state.get("lost_masks", (0, 0))
        drive_masks = resolution_state.get("drive_masks", (0, 0))
        protected_masks = resolution_state.get("protected_masks", (0, 0))
        recovery_losses = resolution_state.get("recovery_losses", (0, 0))
        for p in range(2):
            fast.resolution_lost_mask[p] = int(lost_masks[p])
            fast.resolution_drive_mask[p] = int(drive_masks[p])
            fast.resolution_protected_mask[p] = int(protected_masks[p])
            fast.resolution_recovery_losses[p] = int(recovery_losses[p])
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

    for viewer in range(2):
        for owner in range(2):
            counter = state.known_hidden_counter(viewer, owner, "hand")
            for card_id, count in counter.items():
                fast.known_hidden[viewer][owner][self.id_to_code[card_id]] = count

    snapshot = state.last_battle_snapshot
    if snapshot is not None:
        fast.last_battle_valid = 1
        fast.last_battle = int(snapshot.get("battle", 0))
        front_scores = snapshot.get("front_scores", ())
        for f in range(min(4, len(front_scores))):
            fast.last_front_scores[f][0] = int(front_scores[f][0])
            fast.last_front_scores[f][1] = int(front_scores[f][1])
        front_results = snapshot.get("front_results", ())
        for f in range(min(4, len(front_results))):
            if front_results[f] == 0:
                fast.last_lost_mask[1] |= <uint8_t>(1 << f)
            elif front_results[f] == 1:
                fast.last_lost_mask[0] |= <uint8_t>(1 << f)
        for p in range(2):
            fast.last_command_start[p] = int(
                snapshot.get("command_start", (0, 0))[p]
            )
            fast.last_command_spent[p] = int(
                snapshot.get("command_spent", (0, 0))[p]
            )
            fast.last_command_refunded[p] = int(
                snapshot.get("command_refunded", (0, 0))[p]
            )
            before_collapse = snapshot.get(
                "command_before_collapse",
                snapshot.get("command_before_recovery", (0, 0)),
            )
            fast.last_command_before_recovery[p] = int(before_collapse[p])
            fast.last_recovery_loss[p] = int(
                snapshot.get("recovery_loss", (0, 0))[p]
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
        fast.last_pass_len = min(2, len(pass_snapshot))
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
):
    """Clone one packed root and replace only zones hidden from the viewer."""
    cdef FastState fast = FastState()
    cdef int opponent, i, code
    cdef object card_id

    if viewer < 0 or viewer > 1:
        raise ValueError("viewer must be 0 or 1")
    opponent = 1 - viewer
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

    return fast


cdef dict _fe_export_state(FastEngine self, FastState state):
    cdef int p, f, r, i, card, viewer, owner, ix
    cdef int lost0 = 0
    cdef int lost1 = 0
    cdef object last_snapshot = None

    if state.last_battle_valid:
        lost0 = popcount16(state.last_lost_mask[0] & 15)
        lost1 = popcount16(state.last_lost_mask[1] & 15)
        last_snapshot = {
            "battle": state.last_battle,
            "front_scores": [
                [
                    state.last_front_scores[f][0],
                    state.last_front_scores[f][1],
                ]
                for f in range(4)
            ],
            "front_results": [
                (
                    1
                    if state.last_lost_mask[0] & (1 << f)
                    else 0
                    if state.last_lost_mask[1] & (1 << f)
                    else None
                )
                for f in range(4)
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
            "command_before_recovery": [
                state.last_command_before_recovery[0],
                state.last_command_before_recovery[1],
            ],
            "command_before_collapse": [
                state.last_command_before_recovery[0],
                state.last_command_before_recovery[1],
            ],
            "recovery_loss": [
                state.last_recovery_loss[0],
                state.last_recovery_loss[1],
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
            "battle"
            if state.phase == PHASE_BATTLE
            else "complete"
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
            for p in range(2)
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
                        "temporary_strength": (
                            state.temporary[slot_index(p, f, r)]
                        ),
                        "maneuvers_this_battle": (
                            state.maneuver_count[slot_index(p, f, r)]
                        ),
                        "maneuvered_in_operation": bool(
                            state.maneuvered_in_operation[slot_index(p, f, r)]
                        ),
                        "maneuver_direction": (
                            "left"
                            if state.maneuver_direction[slot_index(p, f, r)] == 1
                            else "right"
                            if state.maneuver_direction[slot_index(p, f, r)] == 2
                            else None
                        ),
                    }
                    for r in range(2)
                ]
                for f in range(4)
            ]
            for p in range(2)
        ],
        "stories": [
            [
                {
                    "card_id": self.card_ids[state.narrative[p * 4 + i]],
                    "front_mask": state.narrative_front_mask[p * 4 + i],
                    "triggered_this_battle": bool(state.narrative_used[p * 4 + i]),
                    "triggered_players_mask": state.narrative_trigger_mask[p * 4 + i],
                    "direction": (
                        "left"
                        if state.narrative_direction[p * 4 + i] == 1
                        else "right"
                        if state.narrative_direction[p * 4 + i] == 2
                        else None
                    ),
                    "target_slot": (
                        None
                        if state.narrative_target_slot[p * 4 + i] < 0
                        else state.narrative_target_slot[p * 4 + i]
                    ),
                }
                for i in range(self.ongoing_story_limit)
                if state.narrative[p * 4 + i] >= 0
            ]
            for p in range(2)
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
                }
            )
            for p in range(2)
        ],
        "stratagem_used": [
            bool(state.stratagem_used[0]),
            bool(state.stratagem_used[1]),
        ],
        "hero_used": [
            bool(state.hero_used[0]),
            bool(state.hero_used[1]),
        ],
        "discarded_this_battle": [
            state.discarded_this_battle[0],
            state.discarded_this_battle[1],
        ],
        "command_spent_this_battle": [
            state.command_spent_this_battle[0],
            state.command_spent_this_battle[1],
        ],
        "command_refunded_this_battle": [
            state.command_refunded_this_battle[0],
            state.command_refunded_this_battle[1],
        ],
        "battle_start_command": [
            state.battle_start_command[0],
            state.battle_start_command[1],
        ],
        "battle_start_hand_size": [
            state.battle_start_hand_size[0],
            state.battle_start_hand_size[1],
        ],
        "cards_drawn_this_battle": [
            state.cards_drawn_this_battle[0],
            state.cards_drawn_this_battle[1],
        ],
        "completion_count_this_battle": [
            state.completion_count_this_battle[0],
            state.completion_count_this_battle[1],
        ],
        "operations_this_battle": [
            state.operations_this_battle[0],
            state.operations_this_battle[1],
        ],
        "maneuvers_this_battle": [
            state.player_maneuver_count[0],
            state.player_maneuver_count[1],
        ],
        "cards_played_this_turn_front_mask": [
            state.cards_played_this_turn_front_mask[0],
            state.cards_played_this_turn_front_mask[1],
        ],
        "cards_played_this_battle_front_mask": [
            state.cards_played_this_battle_front_mask[0],
            state.cards_played_this_battle_front_mask[1],
        ],
        "narratives_played_this_battle": [
            state.narratives_played_this_battle[0],
            state.narratives_played_this_battle[1],
        ],
        "deck_reshuffles": [
            state.deck_reshuffles[0],
            state.deck_reshuffles[1],
        ],
        "reshuffle_card_totals": [
            state.reshuffle_card_totals[0],
            state.reshuffle_card_totals[1],
        ],
        "reshuffle_hand_card_totals": [
            state.reshuffle_hand_card_totals[0],
            state.reshuffle_hand_card_totals[1],
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
            "finish_operation"
            if state.pending_resume == RESUME_FINISH_OPERATION
            else "battle_resolution"
            if state.pending_resume == RESUME_BATTLE_RESOLUTION
            else "start_battle"
            if state.pending_resume == RESUME_START_BATTLE
            else None
        ),
        "pending_resume_player": (
            None if state.pending_resume_player < 0 else state.pending_resume_player
        ),
        "free_maneuver_available": [
            bool(state.free_maneuver_available[0]),
            bool(state.free_maneuver_available[1]),
        ],
        "free_maneuver_source": [
            None
            if state.free_maneuver_source[p] < 0
            else self.card_ids[state.free_maneuver_source[p]]
            for p in range(2)
        ],
        "constraints": [
            {
                "source_card": self.card_ids[state.constraint_source_card[i]],
                "player": state.constraint_player[i],
                "kind": (
                    "affect_front"
                    if state.constraint_kind[i] == CONSTRAINT_AFFECT_FRONT
                    else "maneuver"
                    if state.constraint_kind[i] == CONSTRAINT_MANEUVER
                    else "specific_maneuver"
                ),
                "source_owner": state.constraint_source_owner[i],
                "front": (
                    None
                    if state.constraint_front[i] < 0
                    else state.constraint_front[i]
                ),
                "direction": (
                    "left"
                    if state.constraint_direction[i] == 1
                    else "right"
                    if state.constraint_direction[i] == 2
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
                "discard_source_story": bool(
                    state.constraint_flags[i] & CONSTRAINT_DISCARD_SOURCE_STORY
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
                "recovery_losses": [state.resolution_recovery_losses[0], state.resolution_recovery_losses[1]],
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
        "pass_closing_turns_remaining": state.pass_closing_turns_remaining,
        "known_hidden_hand": [
            [
                {
                    self.card_ids[card]:
                        state.known_hidden[viewer][owner][card]
                    for card in range(self.n_cards)
                    if state.known_hidden[viewer][owner][card]
                }
                for owner in range(2)
            ]
            for viewer in range(2)
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
        "pass_closing_turns_remaining": state.pass_closing_turns_remaining,
        "discarded_this_battle": [state.discarded_this_battle[0], state.discarded_this_battle[1]],
        "command": [state.command[0], state.command[1]],
        "operations_this_battle": [state.operations_this_battle[0], state.operations_this_battle[1]],
        "pending_draw_discard_for": state.active_player if state.cleanup_pending else None,
        "pending_draw_count": state.pending_draw_count,
        "pending_draw_finish_operation": bool(state.pending_draw_finish_operation),
        "hands": [
            {self.card_ids[card]: state.hand[p][card] for card in range(self.n_cards) if state.hand[p][card]}
            for p in range(2)
        ],
        "decks": [
            [self.card_ids[state.deck[p][i]] for i in range(state.deck_len[p])]
            for p in range(2)
        ],
        "discards": [
            [self.card_ids[state.discard[p][i]] for i in range(state.discard_len[p])]
            for p in range(2)
        ],
        "board": [
            [
                (
                    None if state.force[slot_index(p, f, r)] < 0 else self.card_ids[state.force[slot_index(p, f, r)]],
                    None if state.bond[slot_index(p, f, r)] < 0 else self.card_ids[state.bond[slot_index(p, f, r)]],
                    None if state.name[slot_index(p, f, r)] < 0 else self.card_ids[state.name[slot_index(p, f, r)]],
                    state.temporary[slot_index(p, f, r)],
                )
                for f in range(4) for r in range(2)
            ]
            for p in range(2)
        ],
        "schemes": [
            [
                None if state.narrative[p * 4 + f] < 0 else (self.card_ids[state.narrative[p * 4 + f]], bool(state.narrative_revealed[p * 4 + f]))
                for f in range(4)
            ]
            for p in range(2)
        ],
        "stratagems": [
            None if state.stratagem[p] < 0 else (self.card_ids[state.stratagem[p]], bool(state.stratagem_revealed[p]))
            for p in range(2)
        ],
        "stratagem_used": [bool(state.stratagem_used[0]), bool(state.stratagem_used[1])],
        "hero_used": [bool(state.hero_used[0]), bool(state.hero_used[1])],
    }
