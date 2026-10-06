cdef uint32_t _v2_class_mask(object values) except *:
    cdef uint32_t mask = 0
    cdef object value
    cdef dict bits = {
        "archer": 1 << 0,
        "builder": 1 << 1,
        "captain": 1 << 2,
        "guard": 1 << 3,
        "healer": 1 << 4,
        "heir": 1 << 5,
        "human": 1 << 6,
        "king": 1 << 7,
        "raider": 1 << 8,
        "rider": 1 << 9,
        "scout": 1 << 10,
        "seer": 1 << 11,
        "ship": 1 << 12,
        "skirmisher": 1 << 13,
        "spearman": 1 << 14,
        "steward": 1 << 15,
        "stronghold": 1 << 16,
        "veteran": 1 << 17,
    }
    if values is None:
        return 0
    for value in values:
        if value not in bits:
            raise ValueError(f"Unknown V2 classification: {value}")
        mask |= <uint32_t>bits[value]
    return mask


cdef uint8_t _v2_rank_mask(object values) except *:
    cdef uint8_t mask = 0
    cdef object value
    if values is None:
        return 0
    if isinstance(values, str):
        values = [values]
    for value in values:
        if value == "front":
            mask |= 1 << RANK_FRONT
        elif value == "middle":
            mask |= 1 << RANK_MIDDLE
        elif value == "rear":
            mask |= 1 << RANK_REAR
        else:
            raise ValueError(f"Unknown V2 rank: {value}")
    return mask


cdef uint8_t _v2_card_type_mask(object values) except *:
    cdef uint8_t mask = 0
    cdef object value
    if values is None:
        return 0
    if isinstance(values, str):
        values = [values]
    for value in values:
        if value == "any":
            return 255
        elif value == "force":
            mask |= 1
        elif value == "bond":
            mask |= 2
        elif value == "name":
            mask |= 4
        elif value == "hero_force":
            mask |= 8
        elif value == "hero_name":
            mask |= 16
        elif value == "tactic":
            mask |= 32
        elif value == "narrative":
            mask |= 64
        elif value == "stratagem":
            mask |= 128
        else:
            raise ValueError(f"Unknown V2 card-type selector: {value}")
    return mask


cdef void _v2_compile_effect(
    V2EffectSpec* out,
    object effect,
) except *:
    cdef dict op_map = {
        "action_tax": V2_OP_ACTION_TAX,
        "add_class": V2_OP_ADD_CLASS,
        "add_strength_marker": V2_OP_ADD_STRENGTH_MARKER,
        "attach_prepared": V2_OP_ATTACH_PREPARED,
        "choose_class_strength": V2_OP_CHOOSE_CLASS_STRENGTH,
        "choose_strength_targets": V2_OP_CHOOSE_STRENGTH_TARGETS,
        "class_play_discount": V2_OP_CLASS_PLAY_DISCOUNT,
        "class_strength_aura": V2_OP_CLASS_STRENGTH_AURA,
        "class_strength_markers": V2_OP_CLASS_STRENGTH_MARKERS,
        "component_strength": V2_OP_COMPONENT_STRENGTH,
        "discard_draw": V2_OP_DISCARD_DRAW,
        "disrupt_stratagem": V2_OP_DISRUPT_STRATAGEM,
        "draw": V2_OP_DRAW,
        "draw_discard": V2_OP_DRAW_DISCARD,
        "draw_put_top": V2_OP_DRAW_PUT_TOP,
        "front_card_tax": V2_OP_FRONT_CARD_TAX,
        "front_presence_discount": V2_OP_FRONT_PRESENCE_DISCOUNT,
        "front_tactic_discount": V2_OP_FRONT_TACTIC_DISCOUNT,
        "gain_command": V2_OP_GAIN_COMMAND,
        "global_discount": V2_OP_GLOBAL_DISCOUNT,
        "global_discount_split": V2_OP_GLOBAL_DISCOUNT_SPLIT,
        "grant_name_suppression_immunity": V2_OP_GRANT_NAME_SUPPRESSION_IMMUNITY,
        "hidden_buff_after_marker": V2_OP_HIDDEN_BUFF_AFTER_MARKER,
        "hidden_buff_all": V2_OP_HIDDEN_BUFF_ALL,
        "hidden_buff_moved_source": V2_OP_HIDDEN_BUFF_MOVED_SOURCE,
        "hidden_buff_on_tactic": V2_OP_HIDDEN_BUFF_ON_TACTIC,
        "hidden_buff_targets": V2_OP_HIDDEN_BUFF_TARGETS,
        "hidden_cancel_tactic": V2_OP_HIDDEN_CANCEL_TACTIC,
        "hidden_draw_discard": V2_OP_HIDDEN_DRAW_DISCARD,
        "hidden_protect_lost_fronts": V2_OP_HIDDEN_PROTECT_LOST_FRONTS,
        "hidden_spy_on_stratagem": V2_OP_HIDDEN_SPY_ON_STRATAGEM,
        "hidden_tie_named_wins": V2_OP_HIDDEN_TIE_NAMED_WINS,
        "local_class_aura": V2_OP_LOCAL_CLASS_AURA,
        "look_hand": V2_OP_LOOK_HAND,
        "look_stratagem": V2_OP_LOOK_STRATAGEM,
        "maneuver_cost_class": V2_OP_MANEUVER_COST_CLASS,
        "maneuver_unnamed": V2_OP_MANEUVER_UNNAMED,
        "move": V2_OP_MOVE,
        "move_then_front_bonus": V2_OP_MOVE_THEN_FRONT_BONUS,
        "name_suppression_immunity": V2_OP_NAME_SUPPRESSION_IMMUNITY,
        "next_slot_discount": V2_OP_NEXT_SLOT_DISCOUNT,
        "optional_extra_payment_draw": V2_OP_OPTIONAL_EXTRA_PAYMENT_DRAW,
        "pick_top_to_hand_bottom_rest": V2_OP_PICK_TOP_TO_HAND_BOTTOM_REST,
        "play_bond_from_hand": V2_OP_PLAY_BOND_FROM_HAND,
        "prepared_attach_tax": V2_OP_PREPARED_ATTACH_TAX,
        "prepared_pay_or_return": V2_OP_PREPARED_PAY_OR_RETURN,
        "prevent_negative_marker": V2_OP_PREVENT_NEGATIVE_MARKER,
        "prevent_tactic_strength_reduction": V2_OP_PREVENT_TACTIC_STRENGTH_REDUCTION,
        "recover": V2_OP_RECOVER,
        "redirect_tactic": V2_OP_REDIRECT_TACTIC,
        "remove_exhaustion": V2_OP_REMOVE_EXHAUSTION,
        "remove_negative_marker": V2_OP_REMOVE_NEGATIVE_MARKER,
        "remove_strength_marker": V2_OP_REMOVE_STRENGTH_MARKER,
        "reorder_top": V2_OP_REORDER_TOP,
        "reserve": V2_OP_RESERVE,
        "return_prepared": V2_OP_RETURN_PREPARED,
        "self_strength": V2_OP_SELF_STRENGTH,
        "set_stratagem_from_hand": V2_OP_SET_STRATAGEM_FROM_HAND,
        "slot_discount": V2_OP_SLOT_DISCOUNT,
        "stratagem_visibility": V2_OP_STRATAGEM_VISIBILITY,
        "status_strength_aura": V2_OP_STATUS_STRENGTH_AURA,
        "supply": V2_OP_SUPPLY,
        "support": V2_OP_SUPPORT,
        "suppress_action": V2_OP_SUPPRESS_ACTION,
        "suppress_bond": V2_OP_SUPPRESS_BOND,
        "suppress_bond_strength": V2_OP_SUPPRESS_BOND_STRENGTH,
        "suppress_component": V2_OP_SUPPRESS_COMPONENT,
        "suppress_limited": V2_OP_SUPPRESS_LIMITED,
        "suppress_name": V2_OP_SUPPRESS_NAME,
        "swap": V2_OP_SWAP,
        "tactic_front_presence_discount": V2_OP_TACTIC_FRONT_PRESENCE_DISCOUNT,
        "tactic_tax": V2_OP_TACTIC_TAX,
        "tax": V2_OP_TAX,
        "tireless": V2_OP_TIRELESS,
        "trigger_draw": V2_OP_TRIGGER_DRAW,
        "trigger_draw_discard": V2_OP_TRIGGER_DRAW_DISCARD,
        "trigger_gain_command": V2_OP_TRIGGER_GAIN_COMMAND,
        "trigger_look_stratagem": V2_OP_TRIGGER_LOOK_STRATAGEM,
    }
    cdef dict timing_map = {
        "play": V2_TIMING_PLAY,
        "action": V2_TIMING_ACTION,
        "becomes_named": V2_TIMING_BECOMES_NAMED,
        "bonded": V2_TIMING_BONDED,
        "continuous": V2_TIMING_CONTINUOUS,
        "hidden": V2_TIMING_HIDDEN,
        "trigger": V2_TIMING_TRIGGER,
        "while_named": V2_TIMING_WHILE_NAMED,
        "front": V2_TIMING_FRONT,
        "middle": V2_TIMING_MIDDLE,
        "rear": V2_TIMING_REAR,
        "exhausted": V2_TIMING_EXHAUSTED,
        "tireless": V2_TIMING_TIRELESS,
        "mobile": V2_TIMING_MOBILE,
    }
    cdef dict target_map = {
        None: V2_TARGET_NONE,
        "self": V2_TARGET_SELF,
        "directly_ahead": V2_TARGET_DIRECTLY_AHEAD,
        "directly_behind": V2_TARGET_DIRECTLY_BEHIND,
        "friendly_any_class": V2_TARGET_FRIENDLY_ANY_CLASS,
        "friendly_same_front": V2_TARGET_FRIENDLY_SAME_FRONT,
        "opponent_all": V2_TARGET_OPPONENT_ALL,
        "opponent_random": V2_TARGET_OPPONENT_RANDOM,
        "opposing_any": V2_TARGET_OPPOSING_ANY,
        "opposing_any_class": V2_TARGET_OPPOSING_ANY_CLASS,
        "opposing_bonded_any": V2_TARGET_OPPOSING_BONDED_ANY,
        "opposing_bonded_same_front": V2_TARGET_OPPOSING_BONDED_SAME_FRONT,
        "opposing_class_front_with_friendly_class": V2_TARGET_OPPOSING_CLASS_FRONT_WITH_FRIENDLY_CLASS,
        "opposing_component_same_front": V2_TARGET_OPPOSING_COMPONENT_SAME_FRONT,
        "opposing_front_with_friendly_class": V2_TARGET_OPPOSING_FRONT_WITH_FRIENDLY_CLASS,
        "opposing_named_any": V2_TARGET_OPPOSING_NAMED_ANY,
        "opposing_prepared_any": V2_TARGET_OPPOSING_PREPARED_ANY,
        "opposing_prepared_front_with_friendly_class": V2_TARGET_OPPOSING_PREPARED_FRONT_WITH_FRIENDLY_CLASS,
        "opposing_prepared_same_front": V2_TARGET_OPPOSING_PREPARED_SAME_FRONT,
        "opposing_rear": V2_TARGET_OPPOSING_REAR,
        "opposing_same_front": V2_TARGET_OPPOSING_SAME_FRONT,
        "opposing_same_front_without_negative_strength": V2_TARGET_OPPOSING_SAME_FRONT_WITHOUT_NEGATIVE_STRENGTH,
        "opposite": V2_TARGET_OPPOSITE,
        "other_friendly_human_same_front": V2_TARGET_OTHER_FRIENDLY_HUMAN_SAME_FRONT,
        "other_friendly_same_front": V2_TARGET_OTHER_FRIENDLY_SAME_FRONT,
        "prepared_component_same_front": V2_TARGET_PREPARED_COMPONENT_SAME_FRONT,
        "prepared_name_same_front": V2_TARGET_PREPARED_NAME_SAME_FRONT,
        "same_front": V2_TARGET_SAME_FRONT,
        "self_or_directly_ahead": V2_TARGET_SELF_OR_DIRECTLY_AHEAD,
        "self_vertical_friend": V2_TARGET_SELF_VERTICAL_FRIEND,
        "unbonded_friendly_same_front": V2_TARGET_UNBONDED_FRIENDLY_SAME_FRONT,
    }
    cdef dict area_map = {
        None: V2_AREA_NONE,
        "any_active": V2_AREA_ANY_ACTIVE,
        "same_front": V2_AREA_SAME_FRONT,
        "same_or_adjacent": V2_AREA_SAME_OR_ADJACENT,
        "source_same_or_adjacent": V2_AREA_SOURCE_SAME_OR_ADJACENT,
    }
    cdef dict front_map = {
        None: V2_FRONT_NONE,
        "this": V2_FRONT_THIS,
        "choose_active": V2_FRONT_CHOOSE_ACTIVE,
    }
    cdef dict duration_map = {
        None: V2_DURATION_NONE,
        "turn": V2_DURATION_TURN,
        "battle": V2_DURATION_BATTLE,
        "continuous": V2_DURATION_CONTINUOUS,
    }
    cdef dict expires_map = {
        None: V2_EXPIRES_NONE,
        "on_match": V2_EXPIRES_ON_MATCH,
        "before_next_turn": V2_EXPIRES_BEFORE_NEXT_TURN,
    }
    cdef dict trigger_map = {
        None: V2_TRIGGER_NONE,
        "enemy_plays_tactic_same_front": V2_TRIGGER_ENEMY_PLAYS_TACTIC_SAME_FRONT,
        "enemy_sets_stratagem_same_front": V2_TRIGGER_ENEMY_SETS_STRATAGEM_SAME_FRONT,
        "friendly_other_targeted_same_front": V2_TRIGGER_FRIENDLY_OTHER_TARGETED_SAME_FRONT,
        "other_friendly_named_same_front": V2_TRIGGER_OTHER_FRIENDLY_NAMED_SAME_FRONT,
        "play_narrative": V2_TRIGGER_PLAY_NARRATIVE,
    }
    cdef dict reveal_map = {
        None: V2_REVEAL_NONE,
        "after_front_results": V2_REVEAL_AFTER_FRONT_RESULTS,
        "before_strength_comparison": V2_REVEAL_BEFORE_STRENGTH_COMPARISON,
        "enemy_sets_stratagem_near_scout": V2_REVEAL_ENEMY_SETS_STRATAGEM_NEAR_SCOUT,
        "friendly_becomes_named": V2_REVEAL_FRIENDLY_BECOMES_NAMED,
        "friendly_rider_moves": V2_REVEAL_FRIENDLY_RIDER_MOVES,
        "friendly_targeted_by_tactic": V2_REVEAL_FRIENDLY_TARGETED_BY_TACTIC,
        "friendly_targeted_near_archer": V2_REVEAL_FRIENDLY_TARGETED_NEAR_ARCHER,
        "front_would_tie": V2_REVEAL_FRONT_WOULD_TIE,
        "leadership_front_strength_comparison": V2_REVEAL_LEADERSHIP_FRONT_STRENGTH,
        "outer_front_strength_comparison": V2_REVEAL_OUTER_FRONT_STRENGTH,
        "raider_or_skirmisher_marks_enemy": V2_REVEAL_RAIDER_MARKS_ENEMY,
    }
    cdef dict condition_map = {
        None: V2_CONDITION_NONE,
        "command_lower": V2_CONDITION_COMMAND_LOWER,
        "other_named_human": V2_CONDITION_OTHER_NAMED_HUMAN,
    }
    cdef object value
    memset(out, 0, sizeof(V2EffectSpec))
    out.op = op_map[effect["op"]]
    out.timing = timing_map[effect["timing"]]
    out.target = target_map.get(effect.get("target"), V2_TARGET_NONE)
    out.target2 = target_map.get(effect.get("destination"), V2_TARGET_NONE)
    out.area = area_map.get(effect.get("area"), V2_AREA_NONE)
    out.front_mode = front_map.get(effect.get("front"), V2_FRONT_NONE)
    out.duration = duration_map.get(effect.get("duration"), V2_DURATION_NONE)
    out.expires = expires_map.get(effect.get("expires"), V2_EXPIRES_NONE)
    out.trigger = trigger_map.get(effect.get("trigger"), V2_TRIGGER_NONE)
    out.reveal = reveal_map.get(effect.get("reveal"), V2_REVEAL_NONE)
    out.condition = condition_map.get(effect.get("condition"), V2_CONDITION_NONE)
    out.amount = int(effect.get("amount", 0))
    out.amount2 = int(effect.get("amount2", 0))
    out.count = int(effect.get("count", 0))
    out.steps = int(effect.get("steps", 0))
    out.minimum = int(effect.get("minimum", 0))
    out.activation_cost = int(effect.get("activation_cost", 0))
    out.draw_count = int(effect.get("draw", 0))
    out.discard_count = int(effect.get("discard", 0))
    out.max_targets = int(effect.get("max_targets", 0))
    value = effect.get("requires_ranks")
    if value is None and effect.get("requires_rank") is not None:
        value = [effect.get("requires_rank")]
    out.rank_mask = _v2_rank_mask(value)
    out.card_type_mask = _v2_card_type_mask(
        effect.get("card_types", effect.get("card_type"))
    )

    # Primary class mask is the subject/condition; secondary is target/support.
    value = effect.get("classes")
    if value is None:
        value = effect.get("requires_any_class")
    if value is None:
        value = effect.get("required_any_class")
    if value is None:
        value = effect.get("source_classes")
    out.class_mask = _v2_class_mask(value)

    value = effect.get("target_classes")
    if value is None and effect.get("required_friendly_class") is not None:
        value = [effect.get("required_friendly_class")]
    if value is None and effect.get("requires_other_friendly_class") is not None:
        value = [effect.get("requires_other_friendly_class")]
    out.class_mask2 = _v2_class_mask(value)

    if effect.get("all"):
        out.flags |= V2_FLAG_ALL
    if effect.get("same_front"):
        out.flags |= V2_FLAG_SAME_FRONT
    if effect.get("requires_named"):
        out.flags |= V2_FLAG_REQUIRES_NAMED
    if effect.get("requires_bonded"):
        out.flags |= V2_FLAG_REQUIRES_BONDED
    if effect.get("outer_front"):
        out.flags |= V2_FLAG_OUTER_FRONT
    if effect.get("exclude_source"):
        out.flags |= V2_FLAG_EXCLUDE_SOURCE
    if effect.get("exclude_leader"):
        out.flags |= V2_FLAG_EXCLUDE_LEADER
    if effect.get("exclude_self"):
        out.flags |= V2_FLAG_EXCLUDE_SELF
    if effect.get("requires_opposing_exhausted_same_front"):
        out.flags |= V2_FLAG_REQUIRES_OPPOSING_EXHAUSTED
    if effect.get("direction") == "rear":
        out.flags |= V2_FLAG_DIRECTION_REAR
    if effect.get("component") == "bond":
        out.flags |= V2_FLAG_COMPONENT_BOND
    for value in effect.get("statuses", []):
        if value == "hero":
            out.flags |= V2_FLAG_STATUS_HERO
        elif value == "named":
            out.flags |= V2_FLAG_STATUS_NAMED


cdef void _fe___cinit__(FastEngine self) except *:
    self.force_count = 0
    self.bond_count = 0
    self.name_count = 0
    self.narrative_count = 0
    self.stratagem_count = 0
    self.tactic_count = 0
    self.hero_count = 0
    self.name_mode_count = 0
    memset(self.card_type, 0, sizeof(self.card_type))
    memset(self.card_command_cost, 0, sizeof(self.card_command_cost))
    memset(self.strength, 0, sizeof(self.strength))
    memset(self.name_strength, 0, sizeof(self.name_strength))
    memset(self.bond_strength_modifier, 0, sizeof(self.bond_strength_modifier))
    memset(self.hero, 0, sizeof(self.hero))
    memset(self.class_mask, 0, sizeof(self.class_mask))
    memset(self.allowed_rank_mask, 0, sizeof(self.allowed_rank_mask))
    memset(self.v2_effect_count, 0, sizeof(self.v2_effect_count))
    memset(self.v2_effects, 0, sizeof(self.v2_effects))

    # Legacy tables stay inert while old mechanics are removed from callers.
    memset(self.card_capabilities, 0, sizeof(self.card_capabilities))
    memset(self.placement_rank, 0xff, sizeof(self.placement_rank))
    memset(self.force_text_effect, 0, sizeof(self.force_text_effect))
    memset(self.force_text_amount, 0, sizeof(self.force_text_amount))
    memset(self.can_maneuver_unnamed, 0, sizeof(self.can_maneuver_unnamed))
    memset(self.maneuver_requires_open_bond, 0, sizeof(self.maneuver_requires_open_bond))
    memset(self.bond_maneuver_adjacent_hero, 0, sizeof(self.bond_maneuver_adjacent_hero))
    memset(self.bond_blocks_opponent_card_move, 0, sizeof(self.bond_blocks_opponent_card_move))
    memset(self.bond_guarded_from_opponent_card_move, 0, sizeof(self.bond_guarded_from_opponent_card_move))
    memset(self.first_maneuver_free, 0, sizeof(self.first_maneuver_free))
    memset(self.first_maneuver_free_empty_front, 0, sizeof(self.first_maneuver_free_empty_front))
    memset(self.local_catchup_discount_name, 0, sizeof(self.local_catchup_discount_name))
    memset(self.local_catchup_minimum_cost_name, 0, sizeof(self.local_catchup_minimum_cost_name))
    memset(self.first_front_card_battle_discount_name, 0, sizeof(self.first_front_card_battle_discount_name))
    memset(self.first_front_card_battle_minimum_cost_name, 0, sizeof(self.first_front_card_battle_minimum_cost_name))
    memset(self.first_narrative_battle_discount_force, 0, sizeof(self.first_narrative_battle_discount_force))
    memset(self.first_narrative_battle_minimum_cost_force, 0, sizeof(self.first_narrative_battle_minimum_cost_force))
    memset(self.narrative_maneuver_empty_gain, 0, sizeof(self.narrative_maneuver_empty_gain))
    memset(self.narrative_trigger, 0, sizeof(self.narrative_trigger))
    memset(self.narrative_trigger_gain, 0, sizeof(self.narrative_trigger_gain))
    memset(self.narrative_trigger_discard, 0, sizeof(self.narrative_trigger_discard))
    memset(self.immobile_force, 0, sizeof(self.immobile_force))
    memset(self.cannot_swap_target, 0, sizeof(self.cannot_swap_target))
    memset(self.catchup_zero_cost, 0, sizeof(self.catchup_zero_cost))
    memset(self.completion_discount_cost, 0xff, sizeof(self.completion_discount_cost))
    memset(self.frontline_force_discount, 0, sizeof(self.frontline_force_discount))
    memset(self.frontline_force_minimum_cost, 0, sizeof(self.frontline_force_minimum_cost))
    memset(self.frontline_force_discount_requires_named, 0, sizeof(self.frontline_force_discount_requires_named))
    memset(self.front_loss_protected_front, 0, sizeof(self.front_loss_protected_front))
    memset(self.driven_bond_stays, 0, sizeof(self.driven_bond_stays))
    memset(self.driven_bond_returns, 0, sizeof(self.driven_bond_returns))
    memset(self.driven_name_returns, 0, sizeof(self.driven_name_returns))
    memset(self.retreat_command_gain, 0, sizeof(self.retreat_command_gain))
    memset(self.capture_retreating_bond, 0, sizeof(self.capture_retreating_bond))
    memset(self.combat_frontline_only, 0, sizeof(self.combat_frontline_only))
    memset(self.completion_free_maneuver_self, 0, sizeof(self.completion_free_maneuver_self))
    memset(self.after_maneuver_free_adjacent, 0, sizeof(self.after_maneuver_free_adjacent))
    memset(self.completion_swap_adjacent, 0, sizeof(self.completion_swap_adjacent))
    memset(self.skirmisher_contribution, 0, sizeof(self.skirmisher_contribution))
    memset(self.after_empty_follow_move, 0, sizeof(self.after_empty_follow_move))
    memset(self.after_swap_free_other, 0, sizeof(self.after_swap_free_other))
    memset(self.suppress_rear_force, 0, sizeof(self.suppress_rear_force))
    memset(self.first_strike_force, 0, sizeof(self.first_strike_force))
    memset(self.sacrifice_bond, 0, sizeof(self.sacrifice_bond))
    memset(self.intercept_name, 0, sizeof(self.intercept_name))
    memset(self.retreat_sideways_name, 0, sizeof(self.retreat_sideways_name))
    memset(self.battle_start_move_name, 0, sizeof(self.battle_start_move_name))
    memset(self.voluntary_retreat_name, 0, sizeof(self.voluntary_retreat_name))
    memset(self.after_empty_extra_move_force, 0, sizeof(self.after_empty_extra_move_force))
    memset(self.reactive_maneuver_name, 0, sizeof(self.reactive_maneuver_name))
    memset(self.recover_bond_on_completion_name, 0, sizeof(self.recover_bond_on_completion_name))
    memset(self.recover_narrative_on_completion_name, 0, sizeof(self.recover_narrative_on_completion_name))
    memset(self.narrative_secondary, 0, sizeof(self.narrative_secondary))
    memset(self.narrative_end_kind, 0, sizeof(self.narrative_end_kind))
    memset(self.narrative_end_gain, 0, sizeof(self.narrative_end_gain))
    memset(self.narrative_end_draw, 0, sizeof(self.narrative_end_draw))
    memset(self.narrative_end_recover_bond, 0, sizeof(self.narrative_end_recover_bond))
    memset(self.narrative_end_discard, 0, sizeof(self.narrative_end_discard))
    memset(self.feigned_retreat_strat, 0, sizeof(self.feigned_retreat_strat))
    memset(self.strat_maneuver_cost, 0xff, sizeof(self.strat_maneuver_cost))
    memset(self.strat_unnamed_maneuver, 0, sizeof(self.strat_unnamed_maneuver))
    memset(self.strat_tie_control, 0, sizeof(self.strat_tie_control))
    memset(self.strat_front_loss_protection, 0, sizeof(self.strat_front_loss_protection))
    memset(self.strat_combine_fronts, 0, sizeof(self.strat_combine_fronts))
    memset(self.strat_refuse_flank, 0, sizeof(self.strat_refuse_flank))
    memset(self.strat_encirclement, 0, sizeof(self.strat_encirclement))
    memset(self.strat_directional_maneuver, 0, sizeof(self.strat_directional_maneuver))
    memset(self.on_bond_bonus, 0, sizeof(self.on_bond_bonus))
    memset(self.aura, 0, sizeof(self.aura))
    memset(self.aura_rank, 0xff, sizeof(self.aura_rank))
    memset(self.force_mod_amount, 0, sizeof(self.force_mod_amount))
    memset(self.force_mod_discard_min, 0, sizeof(self.force_mod_discard_min))
    memset(self.force_mod_adj_named, 0, sizeof(self.force_mod_adj_named))
    memset(self.bond_bonus, 0, sizeof(self.bond_bonus))
    memset(self.bond_named_bonus, 0, sizeof(self.bond_named_bonus))
    memset(self.bond_discard_per, 0, sizeof(self.bond_discard_per))
    memset(self.bond_discard_max, 0, sizeof(self.bond_discard_max))
    memset(self.bond_opposing, 0, sizeof(self.bond_opposing))
    memset(self.bond_protect, 0, sizeof(self.bond_protect))
    memset(self.bond_move_on_play, 0, sizeof(self.bond_move_on_play))
    memset(self.bond_optional_extra_cost, 0, sizeof(self.bond_optional_extra_cost))
    memset(self.bond_optional_draw_count, 0, sizeof(self.bond_optional_draw_count))
    memset(self.narrative_discard_count, 0, sizeof(self.narrative_discard_count))
    memset(self.narrative_discard_gain_command, 0, sizeof(self.narrative_discard_gain_command))
    memset(self.name_rank_bonus_rank, 0xff, sizeof(self.name_rank_bonus_rank))
    memset(self.name_rank_bonus_amount, 0, sizeof(self.name_rank_bonus_amount))
    memset(self.narrative_play_effect, 0, sizeof(self.narrative_play_effect))
    memset(self.ongoing_narrative, 0, sizeof(self.ongoing_narrative))
    memset(self.narrative_choice_kind, 0, sizeof(self.narrative_choice_kind))
    memset(self.strat_choice_kind, 0, sizeof(self.strat_choice_kind))
    memset(self.strat_trigger_event, 0, sizeof(self.strat_trigger_event))
    memset(self.strat_actor, 0, sizeof(self.strat_actor))
    memset(self.strat_role_mask, 0, sizeof(self.strat_role_mask))
    memset(self.strat_rank_mask, 0, sizeof(self.strat_rank_mask))
    memset(self.strat_reveal_effect, 0, sizeof(self.strat_reveal_effect))
    memset(self.strat_reveal_amount, 0, sizeof(self.strat_reveal_amount))
    memset(self.strat_cancel_narrative, 0, sizeof(self.strat_cancel_narrative))
    memset(self.strat_role_mod, 0, sizeof(self.strat_role_mod))
    memset(self.strat_rank_mod, 0, sizeof(self.strat_rank_mod))
    memset(self.strat_controller_rank_mod, 0, sizeof(self.strat_controller_rank_mod))
    memset(self.strat_named_mod, 0, sizeof(self.strat_named_mod))
    memset(self.strat_unnamed_mod, 0, sizeof(self.strat_unnamed_mod))
    memset(self.strat_narrative_lock, 0, sizeof(self.strat_narrative_lock))
    memset(self.strat_global_narrative_lock, 0, sizeof(self.strat_global_narrative_lock))
    memset(self.narrative_first_card_front_constraint, 0, sizeof(self.narrative_first_card_front_constraint))
    memset(self.narrative_no_maneuver_away, 0, sizeof(self.narrative_no_maneuver_away))
    memset(self.narrative_forced_named_direction, 0, sizeof(self.narrative_forced_named_direction))
    memset(self.narrative_three_front_next_maneuver, 0, sizeof(self.narrative_three_front_next_maneuver))
    memset(self.narrative_front_requires_named, 0, sizeof(self.narrative_front_requires_named))
    memset(self.strat_no_maneuver_away, 0, sizeof(self.strat_no_maneuver_away))
    memset(self.strat_first_maneuver_direction, 0, sizeof(self.strat_first_maneuver_direction))
    memset(self.strat_next_operation_front, 0, sizeof(self.strat_next_operation_front))
    memset(self.bond_momentum_direction, 0, sizeof(self.bond_momentum_direction))


cdef void _fe___init__(FastEngine self, engine) except *:
    cdef int code, mode, index
    cdef object card_id, card, design, effect, mode_name, mode_effects, rows
    cdef dict type_map = {
        CardType.FORCE: CARD_FORCE,
        CardType.BOND: CARD_BOND,
        CardType.NAME: CARD_NAME,
        CardType.HERO: CARD_HERO,
        CardType.TACTIC: CARD_TACTIC,
        CardType.NARRATIVE: CARD_NARRATIVE,
        CardType.STRATAGEM: CARD_STRATAGEM,
    }
    cdef dict mode_map = {
        "force": V2_MODE_FORCE,
        "name": V2_MODE_NAME,
    }
    cdef object rules = engine.rules

    self.card_ids = tuple(engine.cards)
    self.n_cards = len(self.card_ids)
    if self.n_cards > MAX_CARDS:
        raise ValueError(f"The native engine supports at most {MAX_CARDS} card identities")
    self.id_to_code = {card_id: i for i, card_id in enumerate(self.card_ids)}

    self.opening_hand_size = int(rules.opening_hand_size)
    self.command_cap = int(rules.command_cap)
    self.command_recovery_start = int(rules.command_recovery_start)
    self.command_recovery_decrement = int(rules.command_recovery_decrement)
    self.command_recovery_floor = int(rules.command_recovery_floor)
    self.command_collapse_threshold = int(rules.command_collapse_threshold)
    self.lost_front_command_penalty = int(rules.lost_front_command_penalty)
    self.actions_per_turn = int(rules.actions_per_turn)
    self.closing_turns_after_pass = int(rules.closing_turns_after_pass)
    self.turn_draw_count = int(rules.turn_draw_count)
    self.maneuver_command_cost = int(rules.maneuver_command_cost)
    self.hand_limit = int(rules.hand_limit)
    self.ongoing_narrative_limit = int(rules.ongoing_narrative_limit)
    self.hero_force_play_limit_per_battle = int(rules.hero_force_play_limit_per_battle)
    self.hero_name_play_limit_per_battle = int(rules.hero_name_play_limit_per_battle)
    self.stratagem_play_limit_per_battle = int(rules.stratagem_play_limit_per_battle)
    self.command_diag_capture = False
    self.command_diag_len = 0

    for code, card_id in enumerate(self.card_ids):
        card = engine.cards[card_id]
        self.card_type[code] = type_map[card[CardField.TYPE]]
        self.card_command_cost[code] = int(card.get(CardField.COMMAND_COST, 0))
        self.class_mask[code] = <uint32_t>engine.card_mechanics[card_id]["_class_mask"]
        rows = card.get(CardField.ALLOWED_ROWS)
        self.allowed_rank_mask[code] = (
            _v2_rank_mask(rows) if rows else ((1 << RANK_COUNT) - 1)
        )

        if self.card_type[code] == CARD_FORCE:
            self.force_codes[self.force_count] = code
            self.force_count += 1
            self.strength[code] = int(card.get(CardField.STRENGTH, 0))
        elif self.card_type[code] == CARD_BOND:
            self.bond_codes[self.bond_count] = code
            self.bond_count += 1
            self.bond_strength_modifier[code] = int(card.get(CardField.STRENGTH_MODIFIER, 0))
        elif self.card_type[code] == CARD_NAME:
            self.name_codes[self.name_count] = code
            self.name_count += 1
            self.name_mode_codes[self.name_mode_count] = code
            self.name_mode_count += 1
            self.name_strength[code] = int(card.get(CardField.STRENGTH_MODIFIER, 0))
        elif self.card_type[code] == CARD_HERO:
            self.hero[code] = 1
            self.hero_codes[self.hero_count] = code
            self.hero_count += 1
            self.name_mode_codes[self.name_mode_count] = code
            self.name_mode_count += 1
            self.strength[code] = int(card.get(CardField.FORCE_STRENGTH, 0))
            self.name_strength[code] = int(card.get(CardField.NAME_STRENGTH_MODIFIER, 0))
        elif self.card_type[code] == CARD_TACTIC:
            self.tactic_codes[self.tactic_count] = code
            self.tactic_count += 1
        elif self.card_type[code] == CARD_NARRATIVE:
            self.narrative_codes[self.narrative_count] = code
            self.narrative_count += 1
            self.ongoing_narrative[code] = 1
        elif self.card_type[code] == CARD_STRATAGEM:
            self.stratagem_codes[self.stratagem_count] = code
            self.stratagem_count += 1

        design = engine.card_mechanics[card_id]
        mode_effects = design.get("effects", [])
        if len(mode_effects) > 2:
            raise ValueError(f"{card_id}: native V2 mode supports at most two effects")
        self.v2_effect_count[code][V2_MODE_DEFAULT] = len(mode_effects)
        for index, effect in enumerate(mode_effects):
            _v2_compile_effect(&self.v2_effects[code][V2_MODE_DEFAULT][index], effect)

        for mode_name, mode_effects in design.get("modes", {}).items():
            mode = mode_map[mode_name]
            if len(mode_effects) > 2:
                raise ValueError(f"{card_id}.{mode_name}: native V2 mode supports at most two effects")
            self.v2_effect_count[code][mode] = len(mode_effects)
            for index, effect in enumerate(mode_effects):
                _v2_compile_effect(&self.v2_effects[code][mode][index], effect)
