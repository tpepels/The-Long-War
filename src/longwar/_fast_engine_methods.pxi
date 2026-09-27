    def __cinit__(self):
        _fe___cinit__(self)

    def __init__(self, engine):
        _fe___init__(self, engine)

    cpdef FastState from_game_state(self, state):
        return _fe_from_game_state(self, state)

    cdef inline int hand_size(self, FastState state, int player) noexcept:
        return _fe_hand_size(self, state, player)

    cdef int position_strength_fast(self, FastState state, int slot) noexcept:
        return _fe_position_strength_fast(self, state, slot)

    cpdef int position_strength(self, FastState state, int player, int front, int rank):
        return _fe_position_strength(self, state, player, front, rank)

    cdef int front_strength_fast(self, FastState state, int player, int front) noexcept:
        return _fe_front_strength_fast(self, state, player, front)

    cdef inline bint frontline_only_resolution(
        self,
        FastState state,
        int front,
    ) noexcept:
        return _fe_frontline_only_resolution(self, state, front)

    cdef inline int resolution_front_strength_fast(
        self,
        FastState state,
        int player,
        int front,
    ) noexcept:
        return _fe_resolution_front_strength_fast(self, state, player, front)

    cdef inline bint breakthrough_active(
        self,
        FastState state,
        int player,
        int front,
    ) noexcept:
        return _fe_breakthrough_active(self, state, player, front)

    cdef inline bint tie_control_active(
        self,
        FastState state,
    ) noexcept:
        return _fe_tie_control_active(self, state)

    cpdef int front_strength(self, FastState state, int player, int front):
        return _fe_front_strength(self, state, player, front)

    cdef inline bint slot_complete(self, FastState state, int slot) noexcept:
        return _fe_slot_complete(self, state, slot)

    cdef inline bint subject_protected(self, FastState state, int slot) noexcept:
        return _fe_subject_protected(self, state, slot)

    cdef inline bint story_locked(self, FastState state, int player) noexcept:
        return _fe_story_locked(self, state, player)

    cdef inline bint can_draw_fast(self, FastState state, int player) noexcept:
        return _fe_can_draw_fast(self, state, player)

    cpdef bint can_draw(self, FastState state, int player):
        return _fe_can_draw(self, state, player)

    cdef inline int local_front_discount_fast(
        self,
        FastState state,
        int player,
        int front,
    ) noexcept:
        return _fe_local_front_discount_fast(self, state, player, front)

    cdef inline int first_narrative_discount_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        return _fe_first_narrative_discount_fast(self, state, player)

    cdef inline int adjacent_discount_fast(
        self,
        FastState state,
        int player,
        int target_front,
    ) noexcept:
        return _fe_adjacent_discount_fast(self, state, player, target_front)

    cdef inline int command_cost_fast(
        self,
        FastState state,
        uint64_t action,
    ) noexcept:
        return _fe_command_cost_fast(self, state, action)

    cpdef int command_cost(self, FastState state, uint64_t action):
        return _fe_command_cost(self, state, action)

    cdef inline void spend_command_fast(
        self,
        FastState state,
        int player,
        int amount,
    ) noexcept:
        _fe_spend_command_fast(self, state, player, amount)

    cdef inline void gain_command_fast(
        self,
        FastState state,
        int player,
        int amount,
    ) noexcept:
        _fe_gain_command_fast(self, state, player, amount)

    cdef inline int complete_mask(self, FastState state, int player) noexcept:
        return _fe_complete_mask(self, state, player)

    cdef void recover_recent_link_fast(self, FastState state, int player) noexcept:
        _fe_recover_recent_link_fast(self, state, player)

    cdef void resolve_completion_effect_fast(
        self,
        FastState state,
        int player,
        int card,
        int front,
    ):
        _fe_resolve_completion_effect_fast(self, state, player, card, front)

    cdef void resolve_new_completions_fast(
        self,
        FastState state,
        int player,
        int before_mask,
    ):
        _fe_resolve_new_completions_fast(self, state, player, before_mask)

    cdef inline bint opponent_blocks_card_move_into_front(
        self,
        FastState state,
        int player,
        int front,
    ) noexcept:
        return _fe_opponent_blocks_card_move_into_front(self, state, player, front)

    cdef inline bint card_move_destination_legal(
        self,
        FastState state,
        int controller,
        int source,
        int dest,
    ) noexcept:
        return _fe_card_move_destination_legal(self, state, controller, source, dest)

    cdef inline bint player_has_empty_front(
        self,
        FastState state,
        int player,
    ) noexcept:
        return _fe_player_has_empty_front(self, state, player)

    cdef inline bint adjacent_hero_formation(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        return _fe_adjacent_hero_formation(self, state, player, slot)

    cdef inline bint maneuver_source_legal(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        return _fe_maneuver_source_legal(self, state, player, slot)

    cdef inline bint maneuver_destination_legal(
        self,
        FastState state,
        int slot,
    ) noexcept:
        return _fe_maneuver_destination_legal(self, state, slot)

    cdef void enqueue_effect(
        self,
        FastState state,
        int kind,
        int player,
        int card=-1,
        int source=-1,
        int aux=-1,
        uint16_t source_mask=0,
        uint16_t dest_mask=0,
        int flags=0,
    ) except *:
        _fe_enqueue_effect(self, state, kind, player, card, source, aux, source_mask, dest_mask, flags)

    cdef void pop_pending_effect(self, FastState state) noexcept:
        _fe_pop_pending_effect(self, state)

    cdef inline bint slot_is_empty(self, FastState state, int slot) noexcept:
        return _fe_slot_is_empty(self, state, slot)

    cdef int legal_pending_effect_actions(
        self,
        FastState state,
        uint64_t* actions,
    ) except -1:
        return _fe_legal_pending_effect_actions(self, state, actions)

    cdef int legal_actions_into(
        self,
        FastState state,
        uint64_t* actions,
    ) except -1:
        return _fe_legal_actions_into(self, state, actions)

    cpdef list legal_actions(self, FastState state):
        return _fe_legal_actions(self, state)

    cdef inline void append_discard(self, FastState state, int player, int card, bint battle_count=True) noexcept:
        _fe_append_discard(self, state, player, card, battle_count)

    cdef inline void return_to_hand(self, FastState state, int player, int card) noexcept:
        _fe_return_to_hand(self, state, player, card)

    cdef bint remove_from_discard(
        self,
        FastState state,
        int player,
        int card,
    ) noexcept:
        return _fe_remove_from_discard(self, state, player, card)

    cdef inline void take_from_hand(self, FastState state, int player, int card, int hidden_kind) noexcept:
        _fe_take_from_hand(self, state, player, card, hidden_kind)

    cdef inline bint front_has_subject(self, FastState state, int player, int front) noexcept:
        return _fe_front_has_subject(self, state, player, front)

    cdef inline int preferred_slot(self, FastState state, int player, int front) noexcept:
        return _fe_preferred_slot(self, state, player, front)

    cdef void remove_link(self, FastState state, int player, int slot):
        _fe_remove_link(self, state, player, slot)

    cdef inline void return_bond_to_hand_from_slot(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        _fe_return_bond_to_hand_from_slot(self, state, player, slot)

    cdef void compact_ongoing_stories(
        self,
        FastState state,
        int player,
    ) noexcept:
        _fe_compact_ongoing_stories(self, state, player)

    cdef void reveal_scheme(self, FastState state, int controller, int front, int actor, int trigger_slot=-1):
        _fe_reveal_scheme(self, state, controller, front, actor, trigger_slot)

    cdef void resolve_scheme_event(self, FastState state, int actor, int event, int front, int trigger_slot=-1):
        _fe_resolve_scheme_event(self, state, actor, event, front, trigger_slot)

    cdef bint strat_trigger_matches(self, FastState state, int controller, int card, int event, int actor, int played_card=-1, int pos=-1) noexcept:
        return _fe_strat_trigger_matches(self, state, controller, card, event, actor, played_card, pos)

    cdef void resolve_strat_event(self, FastState state, int event, int actor, int played_card=-1, int pos=-1):
        _fe_resolve_strat_event(self, state, event, actor, played_card, pos)

    cdef bint pre_story_cancel(self, FastState state, int actor):
        return _fe_pre_story_cancel(self, state, actor)

    cdef void move_slot(self, FastState state, int source, int dest) noexcept:
        _fe_move_slot(self, state, source, dest)

    cdef void swap_slots(self, FastState state, int a, int b) noexcept:
        _fe_swap_slots(self, state, a, b)

    cdef void resolve_plot(self, FastState state, int actor, int card, int pos, int dest):
        _fe_resolve_plot(self, state, actor, card, pos, dest)

    cdef void discard_ongoing_narrative(
        self,
        FastState state,
        int controller,
        int story_slot,
    ) noexcept:
        _fe_discard_ongoing_narrative(self, state, controller, story_slot)

    cdef uint16_t named_formation_mask(
        self,
        FastState state,
        int player,
        int exclude=-1,
    ) noexcept:
        return _fe_named_formation_mask(self, state, player, exclude)

    cdef uint16_t adjacent_formation_mask(
        self,
        FastState state,
        int player,
        int slot,
        bint named_only=False,
    ) noexcept:
        return _fe_adjacent_formation_mask(self, state, player, slot, named_only)

    cdef uint16_t adjacent_empty_mask(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        return _fe_adjacent_empty_mask(self, state, player, slot)

    cdef bint force_in_all_fronts(self, FastState state, int player) noexcept:
        return _fe_force_in_all_fronts(self, state, player)

    cdef bint discard_has_type(
        self,
        FastState state,
        int player,
        int card_type,
    ) noexcept:
        return _fe_discard_has_type(self, state, player, card_type)

    cdef void queue_recover_from_discard(
        self,
        FastState state,
        int player,
        int card_type,
        bint optional=False,
    ) except *:
        _fe_queue_recover_from_discard(self, state, player, card_type, optional)

    cdef void queue_free_maneuver(
        self,
        FastState state,
        int player,
        uint16_t source_mask,
        bint optional=True,
        bint allow_unnamed=False,
    ) except *:
        _fe_queue_free_maneuver(self, state, player, source_mask, optional, allow_unnamed)

    cdef void queue_move_to_mask(
        self,
        FastState state,
        int player,
        uint16_t source_mask,
        uint16_t dest_mask,
        bint optional=True,
    ) except *:
        _fe_queue_move_to_mask(self, state, player, source_mask, dest_mask, optional)

    cdef void gain_command_from_narrative(
        self,
        FastState state,
        int player,
        int amount,
    ) except *:
        _fe_gain_command_from_narrative(self, state, player, amount)

    cdef void resolve_named_narratives(
        self,
        FastState state,
        int named_player,
        int named_slot,
    ) except *:
        _fe_resolve_named_narratives(self, state, named_player, named_slot)

    cdef void resolve_retreat_narratives(
        self,
        FastState state,
        int player,
        int retreated_slot,
    ) except *:
        _fe_resolve_retreat_narratives(self, state, player, retreated_slot)

    cdef void resolve_force_pair_narratives(
        self,
        FastState state,
        int force_player,
    ) noexcept:
        _fe_resolve_force_pair_narratives(self, state, force_player)

    cdef void resolve_maneuver_into_empty_narratives(
        self,
        FastState state,
        int player,
        int vacated_slot,
    ) except *:
        _fe_resolve_maneuver_into_empty_narratives(self, state, player, vacated_slot)

    cdef void resolve_force_move_triggers(
        self,
        FastState state,
        int player,
        int old_slot,
        int new_slot,
    ) except *:
        _fe_resolve_force_move_triggers(self, state, player, old_slot, new_slot)

    cdef void resolve_maneuver_triggers(
        self,
        FastState state,
        int player,
        int vacated_slot,
        int arrived_slot,
        bint moved_into_empty,
    ) except *:
        _fe_resolve_maneuver_triggers(self, state, player, vacated_slot, arrived_slot, moved_into_empty)

    cdef void resolve_plot_target_scheme(self, FastState state, int actor, int pos):
        _fe_resolve_plot_target_scheme(self, state, actor, pos)

    cdef void reshuffle_discard_into_deck(
        self,
        FastState state,
        int player,
    ) noexcept:
        _fe_reshuffle_discard_into_deck(self, state, player)

    cdef void draw(self, FastState state, int player, int count) noexcept:
        _fe_draw(self, state, player, count)

    cdef void draw_for_battle(
        self,
        FastState state,
        int player,
        int count,
    ) noexcept:
        _fe_draw_for_battle(self, state, player, count)

    cdef void queue_battle_draws(
        self,
        FastState state,
        int player,
        int count,
    ) noexcept:
        _fe_queue_battle_draws(self, state, player, count)

    cdef void start_turn_fast(self, FastState state, int player) noexcept:
        _fe_start_turn_fast(self, state, player)

    cpdef initialize_opening_turn(
        self,
        FastState state,
        int active_player,
        bint opening_bonus=True,
    ):
        return _fe_initialize_opening_turn(self, state, active_player, opening_bonus)

    cdef inline void clear_pass_sequence_fast(
        self,
        FastState state,
    ) noexcept:
        _fe_clear_pass_sequence_fast(self, state)

    cdef void resume_pending_flow(self, FastState state):
        _fe_resume_pending_flow(self, state)

    cdef void finish_operation_fast(self, FastState state, int actor):
        _fe_finish_operation_fast(self, state, actor)

    cdef inline uint32_t next_shuffle_seed(self, uint32_t seed) noexcept:
        return _fe_next_shuffle_seed(self, seed)

    cdef void clear_story_targets_at_slot(
        self,
        FastState state,
        int slot,
    ) noexcept:
        _fe_clear_story_targets_at_slot(self, state, slot)

    cdef void discard_slot_components(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        _fe_discard_slot_components(self, state, player, slot)

    cdef uint16_t succession_destinations(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        return _fe_succession_destinations(self, state, player, slot)

    cdef void finish_pending_drive_off(
        self,
        FastState state,
        int player,
        int slot,
    ) noexcept:
        _fe_finish_pending_drive_off(self, state, player, slot)

    cdef void drive_off_slot(
        self,
        FastState state,
        int player,
        int slot,
    ) except *:
        _fe_drive_off_slot(self, state, player, slot)

    cdef void retreat_slot(
        self,
        FastState state,
        int player,
        int source,
        int destination,
    ) except *:
        _fe_retreat_slot(self, state, player, source, destination)

    cdef inline bint front_has_capture_bond(
        self,
        FastState state,
        int player,
        int front,
    ) noexcept:
        return _fe_front_has_capture_bond(self, state, player, front)

    cdef void discard_incomplete_formations(self, FastState state) noexcept:
        _fe_discard_incomplete_formations(self, state)

    cdef void resolve_retreats(
        self,
        FastState state,
        int losses0,
        int losses1,
        int drive0,
        int drive1,
    ) except *:
        _fe_resolve_retreats(self, state, losses0, losses1, drive0, drive1)

    cdef void discard_battle_stratagems(self, FastState state) noexcept:
        _fe_discard_battle_stratagems(self, state)

    cdef inline void clear_battle_temporary_strength(
        self,
        FastState state,
    ) noexcept:
        _fe_clear_battle_temporary_strength(self, state)

    cdef inline int command_recovery_fast(
        self,
        int battle,
    ) noexcept:
        return _fe_command_recovery_fast(self, battle)

    cdef int command_recovery_for_battle(
        self,
        int battle,
    ):
        return _fe_command_recovery_for_battle(self, battle)

    cdef void finish_start_battle(
        self,
        FastState state,
        int starter,
    ) noexcept:
        _fe_finish_start_battle(self, state, starter)

    cdef void begin_next_battle_fast(
        self,
        FastState state,
        int starter,
    ) except *:
        _fe_begin_next_battle_fast(self, state, starter)

    cdef void queue_pre_resolution_choice(
        self,
        FastState state,
    ) except *:
        _fe_queue_pre_resolution_choice(self, state)

    cdef void compare_battle_fronts(self, FastState state) noexcept:
        _fe_compare_battle_fronts(self, state)

    cdef void advance_retreat_resolution(self, FastState state) except *:
        _fe_advance_retreat_resolution(self, state)

    cdef bint resolve_one_battle_end_narrative(
        self,
        FastState state,
    ) except *:
        return _fe_resolve_one_battle_end_narrative(self, state)

    cdef void clear_resolution_state(self, FastState state) noexcept:
        _fe_clear_resolution_state(self, state)

    cdef void finish_battle_recovery(self, FastState state) except *:
        _fe_finish_battle_recovery(self, state)

    cdef void advance_battle_resolution(self, FastState state) except *:
        _fe_advance_battle_resolution(self, state)

    cdef void score_battle(self, FastState state) except *:
        _fe_score_battle(self, state)

    cdef void pass_action(self, FastState state, int player):
        _fe_pass_action(self, state, player)

    cdef uint16_t asha_mask_for_suppression(
        self,
        FastState state,
        int defender,
        int front,
        int original_target,
    ) noexcept:
        return _fe_asha_mask_for_suppression(self, state, defender, front, original_target)

    cdef void suppress_with_interception(
        self,
        FastState state,
        int controller,
        int target,
    ) except *:
        _fe_suppress_with_interception(self, state, controller, target)

    cdef void apply_pending_effect(self, FastState state, uint64_t action) except *:
        _fe_apply_pending_effect(self, state, action)

    cdef void queue_veyra_force_on_play(
        self,
        FastState state,
        int player,
        int destination,
    ) except *:
        _fe_queue_veyra_force_on_play(self, state, player, destination)

    cdef void queue_veyra_name_on_play(
        self,
        FastState state,
        int player,
        int destination,
    ) except *:
        _fe_queue_veyra_name_on_play(self, state, player, destination)

    cdef void apply_fast(self, FastState state, uint64_t action):
        _fe_apply_fast(self, state, action)

    cpdef FastState next_state(self, FastState state, uint64_t action):
        return _fe_next_state(self, state, action)

    cpdef apply(self, FastState state, uint64_t action):
        return _fe_apply(self, state, action)

    cdef InfoHash128 state_hash_fast(self, FastState state) noexcept:
        return _fe_state_hash_fast(self, state)

    cpdef tuple state_hash(self, FastState state):
        return _fe_state_hash(self, state)

    cdef int _information_state_encode(
        self,
        FastState state,
        int player,
        unsigned char* buf,
        InfoHash128* h,
    ) noexcept:
        return _fe__information_state_encode(self, state, player, buf, h)

    cdef InfoHash128 information_hash_fast(
        self,
        FastState state,
        int player,
    ) noexcept:
        return _fe_information_hash_fast(self, state, player)

    cpdef tuple information_hash(self, FastState state, int player):
        return _fe_information_hash(self, state, player)

    cdef bytes information_key_fast(self, FastState state, int player):
        return _fe_information_key_fast(self, state, player)

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
