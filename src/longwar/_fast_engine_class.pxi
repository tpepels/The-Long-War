# FastEngine is intentionally a thin compiled-data/public-API boundary.
# Internal game/search behavior lives in module-level _fe_* helpers so the
# extension type does not become a second implementation hierarchy.

cdef class FastEngine:
    cdef public object card_ids
    cdef public object id_to_code
    cdef int n_cards
    cdef int opening_hand_size
    cdef int command_cap
    cdef int16_t command_recovery_start
    cdef int16_t command_recovery_decrement
    cdef int16_t command_recovery_floor
    cdef int command_collapse_threshold
    cdef bint pass_signal_costs_operation
    cdef int pass_closing_rounds
    cdef int maneuver_command_cost
    cdef int hand_limit
    cdef int ongoing_story_limit
    cdef bint command_diag_capture
    cdef int command_diag_len
    cdef int16_t command_diag_kind[MAX_COMMAND_DIAG_EVENTS]
    cdef int16_t command_diag_detail[MAX_COMMAND_DIAG_EVENTS]
    cdef int16_t command_diag_player[MAX_COMMAND_DIAG_EVENTS]
    cdef int16_t command_diag_card[MAX_COMMAND_DIAG_EVENTS]
    cdef int16_t command_diag_amount[MAX_COMMAND_DIAG_EVENTS]
    cdef int16_t command_diag_nominal[MAX_COMMAND_DIAG_EVENTS]

    cdef int8_t card_type[MAX_CARDS]
    cdef int8_t card_command_cost[MAX_CARDS]
    cdef int8_t adjacent_command_discount[MAX_CARDS]
    cdef int8_t completion_effect[MAX_CARDS]
    cdef int8_t completion_amount[MAX_CARDS]
    cdef uint8_t complete_plot_protection[MAX_CARDS]
    cdef int8_t role[MAX_CARDS]
    cdef int8_t strength[MAX_CARDS]
    cdef int8_t name_strength[MAX_CARDS]
    cdef uint8_t hero[MAX_CARDS]
    cdef uint64_t card_capabilities[MAX_CARDS]
    cdef int8_t placement_rank[MAX_CARDS]
    cdef int8_t force_text_effect[MAX_CARDS]
    cdef int8_t force_text_amount[MAX_CARDS]
    cdef uint8_t can_maneuver_unnamed[MAX_CARDS]
    cdef uint8_t maneuver_requires_open_bond[MAX_CARDS]
    cdef uint8_t bond_maneuver_adjacent_hero[MAX_CARDS]
    cdef uint8_t bond_blocks_opponent_card_move[MAX_CARDS]
    cdef uint8_t bond_guarded_from_opponent_card_move[MAX_CARDS]
    cdef uint8_t rear_force_prevents_frontline_retreat[MAX_CARDS]
    cdef uint8_t force_breakthrough[MAX_CARDS]
    cdef uint8_t name_breakthrough[MAX_CARDS]
    cdef uint8_t first_maneuver_free[MAX_CARDS]
    cdef uint8_t first_maneuver_free_empty_front[MAX_CARDS]
    cdef uint8_t local_catchup_discount_name[MAX_CARDS]
    cdef uint8_t first_front_card_battle_discount_name[MAX_CARDS]
    cdef uint8_t first_narrative_battle_discount_force[MAX_CARDS]
    cdef int8_t narrative_maneuver_empty_gain[MAX_CARDS]
    cdef int8_t narrative_trigger[MAX_CARDS]
    cdef int8_t narrative_trigger_gain[MAX_CARDS]
    cdef uint8_t narrative_trigger_discard[MAX_CARDS]
    cdef uint8_t immobile_force[MAX_CARDS]
    cdef uint8_t cannot_swap_target[MAX_CARDS]
    cdef uint8_t catchup_zero_cost[MAX_CARDS]
    cdef int8_t completion_discount_cost[MAX_CARDS]
    cdef int8_t frontline_force_discount[MAX_CARDS]
    cdef uint8_t frontline_force_discount_requires_named[MAX_CARDS]
    cdef uint8_t recovery_protected_front[MAX_CARDS]
    cdef uint8_t driven_bond_stays[MAX_CARDS]
    cdef uint8_t driven_bond_returns[MAX_CARDS]
    cdef uint8_t driven_name_returns[MAX_CARDS]
    cdef int8_t retreat_command_gain[MAX_CARDS]
    cdef uint8_t capture_retreating_bond[MAX_CARDS]
    cdef uint8_t combat_frontline_only[MAX_CARDS]
    cdef uint8_t completion_free_maneuver_self[MAX_CARDS]
    cdef uint8_t after_maneuver_free_adjacent[MAX_CARDS]
    cdef uint8_t completion_swap_adjacent[MAX_CARDS]
    cdef uint8_t skirmisher_contribution[MAX_CARDS]
    cdef uint8_t after_empty_follow_move[MAX_CARDS]
    cdef uint8_t after_swap_free_other[MAX_CARDS]
    cdef uint8_t suppress_rear_force[MAX_CARDS]
    cdef uint8_t first_strike_force[MAX_CARDS]
    cdef uint8_t sacrifice_bond[MAX_CARDS]
    cdef uint8_t intercept_name[MAX_CARDS]
    cdef uint8_t retreat_sideways_name[MAX_CARDS]
    cdef uint8_t battle_start_move_name[MAX_CARDS]
    cdef uint8_t voluntary_retreat_name[MAX_CARDS]
    cdef uint8_t after_empty_extra_move_force[MAX_CARDS]
    cdef uint8_t reactive_maneuver_name[MAX_CARDS]
    cdef uint8_t recover_bond_on_completion_name[MAX_CARDS]
    cdef uint8_t recover_story_on_completion_name[MAX_CARDS]
    cdef uint8_t narrative_secondary[MAX_CARDS]
    cdef uint8_t narrative_end_kind[MAX_CARDS]
    cdef int8_t narrative_end_gain[MAX_CARDS]
    cdef uint8_t narrative_end_draw[MAX_CARDS]
    cdef uint8_t narrative_end_recover_bond[MAX_CARDS]
    cdef uint8_t narrative_end_discard[MAX_CARDS]
    cdef uint8_t feigned_retreat_strat[MAX_CARDS]
    cdef int8_t strat_maneuver_cost[MAX_CARDS]
    cdef uint8_t strat_unnamed_maneuver[MAX_CARDS]
    cdef uint8_t strat_tie_control[MAX_CARDS]
    cdef uint8_t strat_recovery_loss_reduction[MAX_CARDS]
    cdef uint8_t strat_no_retreat[MAX_CARDS]
    cdef uint8_t strat_combine_fronts[MAX_CARDS]
    cdef uint8_t strat_refuse_flank[MAX_CARDS]
    cdef uint8_t strat_encirclement[MAX_CARDS]
    cdef uint8_t strat_directional_maneuver[MAX_CARDS]
    cdef int8_t on_bond_bonus[MAX_CARDS]
    cdef int8_t aura[MAX_CARDS]
    cdef int8_t aura_rank[MAX_CARDS]
    cdef int8_t force_mod_amount[MAX_CARDS]
    cdef int8_t force_mod_discard_min[MAX_CARDS]
    cdef uint8_t force_mod_adj_named[MAX_CARDS]

    cdef int8_t bond_bonus[MAX_CARDS]
    cdef int8_t bond_named_bonus[MAX_CARDS]
    cdef int8_t bond_discard_per[MAX_CARDS]
    cdef int8_t bond_discard_max[MAX_CARDS]
    cdef int8_t bond_opposing[MAX_CARDS]
    cdef uint8_t bond_protect[MAX_CARDS]
    cdef uint8_t bond_move_on_play[MAX_CARDS]
    cdef int8_t bond_optional_extra_cost[MAX_CARDS]
    cdef int8_t bond_optional_draw_count[MAX_CARDS]
    cdef int8_t story_discard_count[MAX_CARDS]
    cdef int8_t story_discard_gain_command[MAX_CARDS]

    cdef int8_t name_rank_bonus_rank[MAX_CARDS]
    cdef int8_t name_rank_bonus_amount[MAX_CARDS]
    cdef int8_t name_effect[MAX_CARDS]

    cdef int8_t narrative_play_effect[MAX_CARDS]
    cdef uint8_t ongoing_narrative[MAX_CARDS]
    cdef uint8_t story_choice_kind[MAX_CARDS]
    cdef int8_t ongoing_reveal_trigger[MAX_CARDS]
    cdef int8_t ongoing_reveal_effect[MAX_CARDS]
    cdef int8_t ongoing_reveal_amount[MAX_CARDS]
    cdef uint8_t ongoing_reveal_requires_force[MAX_CARDS]
    cdef int8_t ongoing_reveal_face_bonus[MAX_CARDS]

    cdef uint8_t strat_choice_kind[MAX_CARDS]
    cdef int8_t strat_trigger_event[MAX_CARDS]
    cdef int8_t strat_actor[MAX_CARDS]
    cdef uint16_t strat_role_mask[MAX_CARDS]
    cdef uint8_t strat_rank_mask[MAX_CARDS]
    cdef int8_t strat_reveal_effect[MAX_CARDS]
    cdef int8_t strat_reveal_amount[MAX_CARDS]
    cdef uint8_t strat_cancel_story[MAX_CARDS]
    cdef int8_t strat_role_mod[MAX_CARDS][8]
    cdef int8_t strat_rank_mod[MAX_CARDS][2]
    cdef int8_t strat_controller_rank_mod[MAX_CARDS][2]
    cdef int8_t strat_named_mod[MAX_CARDS]
    cdef int8_t strat_unnamed_mod[MAX_CARDS]
    cdef uint8_t strat_story_lock[MAX_CARDS]
    cdef uint8_t strat_global_story_lock[MAX_CARDS]

    cdef uint8_t narrative_first_card_front_constraint[MAX_CARDS]
    cdef uint8_t narrative_no_maneuver_away[MAX_CARDS]
    cdef uint8_t narrative_forced_named_direction[MAX_CARDS]
    cdef uint8_t narrative_three_front_next_maneuver[MAX_CARDS]
    cdef uint8_t narrative_front_requires_named[MAX_CARDS]
    cdef uint8_t strat_no_maneuver_away[MAX_CARDS]
    cdef uint8_t strat_first_maneuver_direction[MAX_CARDS]
    cdef uint8_t strat_next_operation_front[MAX_CARDS]
    cdef uint8_t bond_momentum_direction[MAX_CARDS]

    def __cinit__(self):
        _fe___cinit__(self)

    def __init__(self, engine):
        _fe___init__(self, engine)

    cpdef FastState from_game_state(self, state):
        return _fe_from_game_state(self, state)

    cpdef FastState determinize_hidden_zones(
        self,
        FastState state,
        int viewer,
        object viewer_deck,
        object opponent_hand,
        object opponent_deck,
    ):
        return _fe_determinize_hidden_zones(
            self,
            state,
            viewer,
            viewer_deck,
            opponent_hand,
            opponent_deck,
        )

    cpdef int position_strength(self, FastState state, int player, int front, int rank):
        return _fe_position_strength(self, state, player, front, rank)

    cpdef int front_strength(self, FastState state, int player, int front):
        return _fe_front_strength(self, state, player, front)

    cpdef bint can_draw(self, FastState state, int player):
        return _fe_can_draw(self, state, player)

    cpdef int command_cost(self, FastState state, uint64_t action):
        return _fe_command_cost(self, state, action)

    cpdef int command_recovery_for_battle(self, int battle):
        return _fe_command_recovery_for_battle(self, battle)

    cpdef list legal_actions(self, FastState state):
        return _fe_legal_actions(self, state)

    cpdef initialize_opening_turn(
        self,
        FastState state,
        int active_player,
        bint opening_bonus=True,
    ):
        return _fe_initialize_opening_turn(self, state, active_player, opening_bonus)

    cpdef FastState next_state(self, FastState state, uint64_t action):
        return _fe_next_state(self, state, action)

    cpdef apply(self, FastState state, uint64_t action):
        return _fe_apply(self, state, action)

    cpdef list apply_with_command_diagnostics(self, FastState state, uint64_t action):
        cdef int i, kind, detail, card
        cdef object kind_name, detail_name, source
        cdef list events = []
        self.command_diag_len = 0
        self.command_diag_capture = True
        try:
            _fe_apply(self, state, action)
        finally:
            self.command_diag_capture = False
        for i in range(self.command_diag_len):
            kind = self.command_diag_kind[i]
            detail = self.command_diag_detail[i]
            card = self.command_diag_card[i]
            kind_name = (
                "gain" if kind == COMMAND_DIAG_GAIN else
                "discount" if kind == COMMAND_DIAG_DISCOUNT else
                "recovery_protection"
            )
            detail_name = {
                COMMAND_DETAIL_COMPLETION_GAIN: "completion_gain",
                COMMAND_DETAIL_NARRATIVE_GAIN: "narrative_gain",
                COMMAND_DETAIL_RETREAT_GAIN: "retreat_gain",
                COMMAND_DETAIL_DISCARD_GAIN: "discard_for_command",
                COMMAND_DETAIL_CATCHUP_DISCOUNT: "catchup_discount",
                COMMAND_DETAIL_COMPLETION_DISCOUNT: "completion_discount",
                COMMAND_DETAIL_NARRATIVE_DISCOUNT: "narrative_discount",
                COMMAND_DETAIL_LOCAL_FRONT_DISCOUNT: "local_front_discount",
                COMMAND_DETAIL_ADJACENT_DISCOUNT: "adjacent_discount",
                COMMAND_DETAIL_FRONTLINE_DISCOUNT: "frontline_discount",
                COMMAND_DETAIL_FREE_MANEUVER: "free_maneuver",
                COMMAND_DETAIL_STRATAGEM_MANEUVER: "stratagem_maneuver_discount",
                COMMAND_DETAIL_RECOVERY_PROTECTED_FRONT: "recovery_protected_front",
                COMMAND_DETAIL_RECOVERY_STRATAGEM: "recovery_stratagem",
            }.get(detail, "other")
            source = None if card < 0 else self.card_ids[card]
            events.append({
                "kind": kind_name,
                "detail": detail_name,
                "player": int(self.command_diag_player[i]),
                "source_card": source,
                "amount": int(self.command_diag_amount[i]),
                "nominal_amount": int(self.command_diag_nominal[i]),
            })
        return events

    cpdef tuple state_hash(self, FastState state):
        return _fe_state_hash(self, state)

    cpdef tuple information_hash(self, FastState state, int player):
        return _fe_information_hash(self, state, player)

    cpdef bytes information_key(self, FastState state, int player):
        return _fe_information_key(self, state, player)

    cpdef str information_id(self, FastState state, int player):
        return _fe_information_id(self, state, player)

    cpdef str action_key(self, uint64_t action):
        return _fe_action_key(self, action)

    cpdef dict export_state(self, FastState state):
        return _fe_export_state(self, state)

    cpdef dict debug_snapshot(self, FastState state):
        return _fe_debug_snapshot(self, state)
