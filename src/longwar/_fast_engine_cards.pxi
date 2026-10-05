cdef void _fe___cinit__(FastEngine self) except *:
    self.force_count = 0
    self.bond_count = 0
    self.name_count = 0
    self.narrative_count = 0
    self.stratagem_count = 0
    self.hero_count = 0
    self.name_mode_count = 0
    memset(self.card_type, 0, sizeof(self.card_type))
    memset(self.card_command_cost, 0, sizeof(self.card_command_cost))
    memset(self.completion_effect, 0, sizeof(self.completion_effect))
    memset(self.completion_amount, 0, sizeof(self.completion_amount))
    memset(self.complete_narrative_protection, 0, sizeof(self.complete_narrative_protection))
    memset(self.role, 0, sizeof(self.role))
    memset(self.strength, 0, sizeof(self.strength))
    memset(self.name_strength, 0, sizeof(self.name_strength))
    memset(self.hero, 0, sizeof(self.hero))
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
    memset(self.name_effect, 0, sizeof(self.name_effect))
    memset(self.narrative_play_effect, 0, sizeof(self.narrative_play_effect))
    memset(self.ongoing_narrative, 0, sizeof(self.ongoing_narrative))
    memset(self.narrative_choice_kind, 0, sizeof(self.narrative_choice_kind))
    memset(self.ongoing_reveal_trigger, 0, sizeof(self.ongoing_reveal_trigger))
    memset(self.ongoing_reveal_effect, 0, sizeof(self.ongoing_reveal_effect))
    memset(self.ongoing_reveal_amount, 0, sizeof(self.ongoing_reveal_amount))
    memset(self.ongoing_reveal_requires_force, 0, sizeof(self.ongoing_reveal_requires_force))
    memset(self.ongoing_reveal_face_bonus, 0, sizeof(self.ongoing_reveal_face_bonus))
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
    cdef int code
    cdef object rules = engine.rules
    self.card_ids = tuple(engine.cards)
    self.n_cards = len(self.card_ids)
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
    self.hero_force_play_limit_per_battle = int(
        rules.hero_force_play_limit_per_battle
    )
    self.hero_name_play_limit_per_battle = int(
        rules.hero_name_play_limit_per_battle
    )
    self.stratagem_play_limit_per_battle = int(
        rules.stratagem_play_limit_per_battle
    )
    self.command_diag_capture = False
    self.command_diag_len = 0
    if self.n_cards > MAX_CARDS:
        raise ValueError(f"The native engine supports at most {MAX_CARDS} card identities")
    if max(rules.starting_command, self.command_cap) > 32767:
        raise ValueError("Command settings exceed the native signed 16-bit capacity")
    self.id_to_code = {card_id: i for i, card_id in enumerate(self.card_ids)}

    type_map = {CardType.FORCE: CARD_FORCE, CardType.BOND: CARD_BOND, CardType.NAME: CARD_NAME, CardType.NARRATIVE: CARD_NARRATIVE, CardType.STRATAGEM: CARD_STRATAGEM}
    role_map = {
        ForceRole.SWORDSMAN.value: ROLE_SWORDSMAN,
        ForceRole.SPEARMAN.value: ROLE_SPEARMAN,
        ForceRole.ARCHER.value: ROLE_ARCHER,
        ForceRole.HEALER.value: ROLE_HEALER,
        ForceRole.SHIP.value: ROLE_SHIP,
        ForceRole.STRONGHOLD.value: ROLE_STRONGHOLD,
    }
    rank_map = {
        Rank.FRONT.value: RANK_FRONT,
        Rank.REAR.value: RANK_REAR,
    }
    force_text_map = {
        DesignToken.FRONTLINE_STRENGTH_BONUS.value: FORCE_TEXT_FRONT_BONUS,
        DesignToken.REAR_STRENGTH_BONUS.value: FORCE_TEXT_REAR_BONUS,
        DesignToken.SUPPORT_FORCE_AHEAD_STRENGTH_BONUS.value: FORCE_TEXT_SUPPORT_AHEAD,
        DesignToken.FRONTLINE_STRENGTH_BONUS_IF_FORCE_BEHIND.value: FORCE_TEXT_FRONT_IF_REAR,
        DesignToken.REAR_STRENGTH_BONUS_IF_FORCE_AHEAD.value: FORCE_TEXT_REAR_IF_FRONT,
    }
    for code, card_id in enumerate(self.card_ids):
        card = engine.cards[card_id]
        self.card_type[code] = type_map[card[CardField.TYPE]]
        if self.card_type[code] == CARD_FORCE:
            self.force_codes[self.force_count] = code
            self.force_count += 1
        elif self.card_type[code] == CARD_BOND:
            self.bond_codes[self.bond_count] = code
            self.bond_count += 1
        elif self.card_type[code] == CARD_NAME:
            self.name_codes[self.name_count] = code
            self.name_count += 1
        elif self.card_type[code] == CARD_NARRATIVE:
            self.narrative_codes[self.narrative_count] = code
            self.narrative_count += 1
        elif self.card_type[code] == CARD_STRATAGEM:
            self.stratagem_codes[self.stratagem_count] = code
            self.stratagem_count += 1
        self.role[code] = role_map.get(card.get(CardField.ROLE), ROLE_NONE)
        self.strength[code] = int(card.get(CardField.STRENGTH, 0))
        self.name_strength[code] = int(
            card.get(
                CardField.HERO_NAME_STRENGTH,
                card.get(CardField.STRENGTH, 0) if card[CardField.TYPE] == CardType.NAME else 0,
            )
        )
        self.hero[code] = bool(card.get(CardField.HERO, False))
        if self.hero[code]:
            self.hero_codes[self.hero_count] = code
            self.hero_count += 1
        if self.card_type[code] == CARD_NAME or self.hero[code]:
            self.name_mode_codes[self.name_mode_count] = code
            self.name_mode_count += 1
        design = engine.card_mechanics[card_id]
        self.card_capabilities[code] = <uint64_t>design.get(
            "_capability_bits",
            0,
        )
        force_design = design.get(DesignField.FORCE) or design

        self.narrative_first_card_front_constraint[code] = bool(
            design.get(DesignField.PER_PLAYER_FIRST_CARD_IN_FRONT_EACH_BATTLE)
            and design.get(DesignField.NEXT_ACTION_MUST_AFFECT_CHOSEN_FRONT_IF_POSSIBLE)
        )
        self.narrative_no_maneuver_away[code] = bool(
            design.get(DesignField.NAMED_FORMATIONS_CANNOT_MANEUVER_AWAY)
        )
        self.narrative_forced_named_direction[code] = bool(
            design.get(DesignField.CHOOSE_FRIENDLY_NAMED_FORMATION)
            and design.get(DesignField.CHOOSE_DIRECTION)
            and design.get(DesignField.NEXT_TURN_FORCED_MANEUVER_IF_LEGAL)
        )
        self.narrative_three_front_next_maneuver[code] = bool(
            design.get(DesignField.NEXT_BATTLE_FIRST_ACTION_MUST_BE_MANEUVER_IF_POSSIBLE)
        )
        self.narrative_front_requires_named[code] = bool(
            design.get(DesignField.CHOSEN_FRONT_REQUIRES_FRIENDLY_NAMED_FORMATION)
        )
        self.strat_no_maneuver_away[code] = bool(
            design.get(DesignField.FORMATIONS_CANNOT_MANEUVER_AWAY_FROM_CHOSEN_FRONT)
        )
        self.strat_first_maneuver_direction[code] = bool(
            design.get(DesignField.FIRST_MANEUVER_EACH_PLAYER_MUST_USE_DIRECTION_IF_POSSIBLE)
        )
        self.strat_next_operation_front[code] = bool(
            design.get(DesignField.NEXT_ACTION_EACH_PLAYER_MUST_AFFECT_CHOSEN_FRONT_IF_POSSIBLE)
        )
        self.bond_momentum_direction[code] = bool(
            design.get(DesignField.LATER_MANEUVERS_SAME_DIRECTION_IF_POSSIBLE)
        )
        self.card_command_cost[code] = int(card.get(CardField.COMMAND_COST, 0))

        if (
            design.get(DesignField.TRIGGER) == DesignToken.FRIENDLY_FORMATION_BECOMES_NAMED
            and design.get(DesignField.SCOPE) == DesignToken.THIS_FORMATION
        ):
            if design.get(DesignField.GAIN_COMMAND):
                self.completion_effect[code] = COMPLETE_GAIN_COMMAND
                self.completion_amount[code] = int(design[DesignField.GAIN_COMMAND])
            elif design.get(DesignField.DRAW_CARDS):
                self.completion_effect[code] = COMPLETE_DRAW
                self.completion_amount[code] = int(design[DesignField.DRAW_CARDS])
        if design.get(DesignField.COMMAND) == DesignToken.COMPLETION_REFUND:
            completion_design = design.get(DesignField.ON_COMPLETION) or {}
            if completion_design.get(DesignField.GAIN_COMMAND):
                self.completion_effect[code] = COMPLETE_GAIN_COMMAND
                self.completion_amount[code] = int(completion_design[DesignField.GAIN_COMMAND])

        placement = (
            force_design.get(DesignField.DEPLOY_RANK)
            or design.get(DesignField.DEPLOY_RANK)
        )
        self.placement_rank[code] = rank_map.get(placement, -1)
        printed_effect = force_design.get(DesignField.PRINTED_ROLE_EFFECT) or design.get(DesignField.PRINTED_ROLE_EFFECT)
        self.force_text_effect[code] = force_text_map.get(printed_effect, FORCE_TEXT_NONE)
        self.force_text_amount[code] = int(
            force_design.get(DesignField.AMOUNT, design.get(DesignField.AMOUNT, 0))
        )
        self.can_maneuver_unnamed[code] = bool(
            force_design.get(DesignField.CAN_MANEUVER_WHILE_UNNAMED)
            or design.get(DesignField.CAN_MANEUVER_WHILE_UNNAMED)
        )
        if design.get(DesignField.BUILD_AROUND) == DesignToken.OPEN_BOND:
            self.maneuver_requires_open_bond[code] = 1
        if design.get(DesignField.BUILD_AROUND) == DesignToken.HERO_RETINUE:
            self.bond_maneuver_adjacent_hero[code] = 1
        if design.get(DesignField.PREVENT_OPPONENT_CARD_EFFECT_MOVE_INTO_FRONT_FROM_ADJACENT):
            self.bond_blocks_opponent_card_move[code] = 1
        if design.get(DesignField.PREVENT_OPPONENT_CARD_EFFECT_MOVEMENT):
            self.bond_guarded_from_opponent_card_move[code] = 1
        if design.get(DesignField.FIRST_MANEUVER_EACH_BATTLE_COST) == 0:
            self.first_maneuver_free[code] = 1
        if design.get(DesignField.FIRST_SELF_MANEUVER_EACH_BATTLE_COST) == 0:
            self.first_maneuver_free_empty_front[code] = 1
        if design.get(DesignField.COMMAND) == DesignToken.LOCAL_CATCH_UP_DISCOUNT:
            self.local_catchup_discount_name[code] = int(
                design.get(DesignField.DISCOUNT_AMOUNT, 0)
            )
            self.local_catchup_minimum_cost_name[code] = int(
                design.get(DesignField.MINIMUM_COST, 0)
            )
        name_design = design.get(DesignField.NAME) or {}
        if name_design.get(DesignField.COMMAND) == DesignToken.FIRST_CARD_IN_FRONT_EACH_BATTLE_DISCOUNT:
            self.first_front_card_battle_discount_name[code] = int(
                name_design.get(DesignField.DISCOUNT_AMOUNT, 0)
            )
            self.first_front_card_battle_minimum_cost_name[code] = int(
                name_design.get(DesignField.MINIMUM_COST, 0)
            )
        if force_design.get(DesignField.NARRATIVE) == DesignToken.FIRST_NARRATIVE_EACH_BATTLE_DISCOUNT:
            self.first_narrative_battle_discount_force[code] = int(
                force_design.get(DesignField.DISCOUNT_AMOUNT, 0)
            )
            self.first_narrative_battle_minimum_cost_force[code] = int(
                force_design.get(DesignField.MINIMUM_COST, 0)
            )
        name_design = design.get(DesignField.NAME) or {}
        self.immobile_force[code] = bool(
            force_design.get(DesignField.IMMOBILE) or design.get(DesignField.IMMOBILE)
        )
        self.cannot_swap_target[code] = bool(
            force_design.get(DesignField.CANNOT_BE_SWAP_TARGET)
            or design.get(DesignField.CANNOT_BE_SWAP_TARGET)
        )
        if design.get(DesignField.COMMAND) == DesignToken.CATCH_UP_DISCOUNT:
            self.catchup_zero_cost[code] = 1
        if design.get(DesignField.COMMAND) == DesignToken.COMPLETION_DISCOUNT:
            self.completion_discount_cost[code] = int(
                design.get(DesignField.DISCOUNTED_COST, card.get(CardField.COMMAND_COST, 0))
            )
        if design.get(DesignField.PERSISTENCE) == DesignToken.REAR_REBUILD_COST_REDUCTION:
            self.frontline_force_discount[code] = int(
                design.get(DesignField.DISCOUNT_AMOUNT, 0)
            )
            self.frontline_force_minimum_cost[code] = int(
                design.get(DesignField.MINIMUM_COST, 0)
            )
            self.frontline_force_discount_requires_named[code] = 1
        if force_design.get(DesignField.COMMAND) == DesignToken.FRONTLINE_FORCE_DISCOUNT:
            self.frontline_force_discount[code] = int(
                force_design.get(DesignField.DISCOUNT_AMOUNT, 0)
            )
            self.frontline_force_minimum_cost[code] = int(
                force_design.get(DesignField.MINIMUM_COST, 0)
            )
        if force_design.get(DesignField.COMMAND) == DesignToken.PROTECT_LOST_FRONT_HERE:
            self.front_loss_protected_front[code] = 1
        if design.get(DesignField.PERSISTENCE) == DesignToken.INHERITED_BOND:
            self.driven_bond_stays[code] = 1
        if design.get(DesignField.PERSISTENCE) == DesignToken.BOND_RETURNS_TO_HAND_WHEN_FORCE_DRIVEN_OFF:
            self.driven_bond_returns[code] = 1
        if (
            design.get(DesignField.PERSISTENCE) == DesignToken.NAME_RETURNS_TO_HAND_WHEN_FORMATION_DRIVEN_OFF
            or (design.get(DesignField.NAME) or {}).get(DesignField.EFFECT) == DesignToken.RETURN_HERO_TO_HAND_IF_DRIVEN_OFF
        ):
            self.driven_name_returns[code] = 1
        if design.get(DesignField.PERSISTENCE) == DesignToken.RETREAT_COMMAND_COMPENSATION:
            self.retreat_command_gain[code] = int(design.get(DesignField.AMOUNT, 1))
        if (
            design.get(DesignField.COMBAT) == DesignToken.CAPTURE
            and design.get(DesignField.TRIGGER)
            == DesignToken.OWN_FRONT_WINS_AND_OPPOSING_FRONTLINE_NAMED_RETREATS
            and design.get(DesignField.TIMING) == DesignToken.AFTER_RETREAT
            and design.get(DesignField.EFFECT)
            == DesignToken.RETURN_RETREATING_FORMATION_BOND_TO_OWNER_HAND
        ):
            self.capture_retreating_bond[code] = 1
        if design.get(DesignField.COMBAT) == DesignToken.FRONTLINE_ONLY_COMPARISON:
            self.combat_frontline_only[code] = 1
        completion_design = design.get(DesignField.ON_COMPLETION) or {}
        if completion_design.get(DesignField.EFFECT) == DesignToken.OPTIONAL_SWAP_ADJACENT_FRIENDLY_FORMATION:
            self.completion_swap_adjacent[code] = 1
        name_completion = name_design.get(DesignField.ON_COMPLETION)
        if (
            isinstance(name_completion, dict)
            and name_completion.get(DesignField.EFFECT) == DesignToken.FREE_MANEUVER_SELF
        ):
            self.completion_free_maneuver_self[code] = 1
        if (force_design.get(DesignField.AFTER_MANEUVER) or {}).get(DesignField.EFFECT) == DesignToken.FREE_MANEUVER_ADJACENT_FRIENDLY_NAMED_FORMATION:
            self.after_maneuver_free_adjacent[code] = 1
        if name_design.get(DesignField.ON_COMPLETION) == DesignToken.RETURN_ONE_BOND_FROM_DISCARD_TO_HAND:
            self.recover_bond_on_completion_name[code] = 1
        if name_design.get(DesignField.ON_COMPLETION) == DesignToken.RETURN_ONE_NARRATIVE_FROM_DISCARD_TO_HAND:
            self.recover_narrative_on_completion_name[code] = 1
        front_resolution = design.get(DesignField.FRONT_RESOLUTION) or {}
        if front_resolution.get(DesignField.CONTRIBUTION) == DesignToken.CHOSEN_FRONT_INSTEAD_OF_OWN:
            self.skirmisher_contribution[code] = 1
        if (design.get(DesignField.AFTER_MANEUVER_INTO_EMPTY) or {}).get(DesignField.EFFECT) == DesignToken.OPTIONAL_MOVE_ADJACENT_FRIENDLY_TO_VACATED_POSITION:
            self.after_empty_follow_move[code] = 1
        if (design.get(DesignField.AFTER_MANEUVER_SWAP) or {}).get(DesignField.EFFECT) == DesignToken.OPTIONAL_ZERO_COST_MANEUVER_SWAPPED_FORMATION:
            self.after_swap_free_other[code] = 1
        if design.get(DesignField.COMBAT) == DesignToken.SKIRMISH:
            self.suppress_rear_force[code] = 1
        if design.get(DesignField.COMBAT) == DesignToken.FIRST_STRIKE:
            self.first_strike_force[code] = 1
        if design.get(DesignField.COMBAT) == DesignToken.SACRIFICE:
            self.sacrifice_bond[code] = 1
        if design.get(DesignField.COMBAT) == DesignToken.INTERCEPTION:
            self.intercept_name[code] = 1
        if design.get(DesignField.PERSISTENCE) == DesignToken.RETREAT_SIDEWAYS:
            self.retreat_sideways_name[code] = 1
        if design.get(DesignField.PERSISTENCE) == DesignToken.START_BATTLE_REPOSITION:
            self.battle_start_move_name[code] = 1
        if design.get(DesignField.PERSISTENCE) == DesignToken.VOLUNTARY_RETREAT_IF_REAR_EMPTY:
            self.voluntary_retreat_name[code] = 1
        if force_design.get(DesignField.AFTER_MANEUVER_INTO_EMPTY) == DesignToken.OPTIONAL_MOVE_ONE_MORE_FRONT_IF_EMPTY:
            self.after_empty_extra_move_force[code] = 1
        if name_design.get(DesignField.TRIGGER) == DesignToken.OPPONENT_MANEUVERS_INTO_ADJACENT_FRONT:
            self.reactive_maneuver_name[code] = 1
        if force_design.get(DesignField.COMBAT) == DesignToken.OPTIONAL_IGNORE_OPPOSING_REAR_STRENGTH:
            self.suppress_rear_force[code] = 1
        if design.get(DesignField.COMBAT) == DesignToken.TIE_CONTROL:
            self.strat_tie_control[code] = 1
        if design.get(DesignField.COMMAND) == DesignToken.HIGH_COST_BATTLE_INVESTMENT:
            self.strat_maneuver_cost[code] = int(design.get(DesignField.MANEUVER_COST, -1))
            self.strat_unnamed_maneuver[code] = bool(
                design.get(DesignField.UNNAMED_FORMATIONS_CAN_MANEUVER)
            )
        if design.get(DesignField.COMMAND) == DesignToken.PROTECT_LOST_FRONTS:
            self.strat_front_loss_protection[code] = max(
                0, int(design.get(DesignField.LOST_FRONTS_PROTECTED, 0))
            )
        if design.get(DesignField.STRATAGEM) == DesignToken.COMBINE_TWO_ADJACENT_FRONTS:
            self.strat_combine_fronts[code] = 1
        if design.get(DesignField.STRATAGEM) == DesignToken.REFUSE_FLANK:
            self.strat_refuse_flank[code] = 1
        if design.get(DesignField.STRATAGEM) == DesignToken.ENCIRCLEMENT:
            self.strat_encirclement[code] = 1
        if design.get(DesignField.STRATAGEM) == DesignToken.FEIGNED_RETREAT:
            self.feigned_retreat_strat[code] = 1
        if design.get(DesignField.STRATAGEM) == DesignToken.BATTLE_TURNS_DIRECTION:
            self.strat_directional_maneuver[code] = 1

        self.bond_bonus[code] = int(design.get(DesignField.STRENGTH_BONUS, 0))
        self.bond_named_bonus[code] = int(
            design.get(DesignField.NAMED_ADDITIONAL_STRENGTH_BONUS, 0)
        )
        on_play_bond = design.get(DesignField.ON_PLAY_ONTO_FORCE) or {}
        if on_play_bond.get(DesignField.EFFECT) == DesignToken.OPTIONAL_MOVE_FORMATION_ADJACENT_EMPTY_POSITION:
            self.bond_move_on_play[code] = 1
        if design.get(DesignField.COMMAND) == DesignToken.OPTIONAL_EXTRA_PAYMENT:
            self.bond_optional_extra_cost[code] = int(
                design.get(DesignField.EXTRA_COST, 0)
            )
            if design.get(DesignField.EFFECT) == DesignToken.DRAW_CARDS:
                self.bond_optional_draw_count[code] = int(
                    design.get(DesignField.DRAW_CARDS, 0)
                )
        if design.get(DesignField.COMMAND) == DesignToken.CARD_FOR_COMMAND:
            self.narrative_discard_count[code] = int(
                design.get(DesignField.DISCARD_CARDS, 0)
            )
            self.narrative_discard_gain_command[code] = int(
                design.get(DesignField.GAIN_COMMAND, 0)
            )

        self.ongoing_narrative[code] = bool(card.get(CardField.ONGOING, False))
        if (
            design.get(DesignField.PLACEMENT) == DesignToken.CHOSEN_FRONT
            or design.get(DesignField.CHOSEN_FRONT)
            or design.get(DesignField.CHOSEN_FRONT_REQUIRES_FRIENDLY_NAMED_FORMATION)
        ):
            self.narrative_choice_kind[code] = NARRATIVE_CHOICE_FRONT
        elif self.narrative_forced_named_direction[code]:
            self.narrative_choice_kind[code] = NARRATIVE_CHOICE_NAMED_DIRECTION
        elif (
            design.get(DesignField.PLACEMENT) == DesignToken.CHOSEN_NAMED_FORMATION
            or design.get(DesignField.CHOOSE_FRIENDLY_NAMED_FORMATION)
        ):
            self.narrative_choice_kind[code] = NARRATIVE_CHOICE_NAMED_FORMATION
        if design.get(DesignField.TRIGGER) == DesignToken.FIRST_FRIENDLY_MANEUVER_INTO_EMPTY_EACH_BATTLE:
            self.narrative_maneuver_empty_gain[code] = int(
                design.get(DesignField.GAIN_COMMAND, 0)
            )
        if design.get(DesignField.TRIGGER) == DesignToken.FRIENDLY_FORMATION_BECOMES_NAMED:
            self.narrative_trigger[code] = NARR_TRIGGER_FRIENDLY_NAMED
        elif design.get(DesignField.TRIGGER) == DesignToken.FRIENDLY_NAMED_FORMATION_RETREATS:
            self.narrative_trigger[code] = NARR_TRIGGER_FRIENDLY_RETREAT
        elif design.get(DesignField.TRIGGER) == DesignToken.OPPOSING_FORMATION_BECOMES_NAMED:
            self.narrative_trigger[code] = NARR_TRIGGER_OPPONENT_NAMED
        elif design.get(DesignField.TRIGGER) == DesignToken.OPPONENT_HAS_FORCE_IN_BOTH_RANKS_SAME_FRONT:
            self.narrative_trigger[code] = NARR_TRIGGER_OPPONENT_BOTH_RANKS
        self.narrative_trigger_gain[code] = int(
            design.get(DesignField.GAIN_COMMAND, 0)
        )
        self.narrative_trigger_discard[code] = bool(
            design.get(DesignField.DISCARD_SELF, False)
        )
        secondary = design.get(DesignField.SECONDARY)
        if secondary == DesignToken.OPTIONAL_ZERO_COST_MANEUVER_THAT_FORMATION:
            self.narrative_secondary[code] = NARR_SECONDARY_FREE_TRIGGERED
        elif secondary == DesignToken.OPTIONAL_SIDEWAYS_REAR_MOVE:
            self.narrative_secondary[code] = NARR_SECONDARY_SIDEWAYS_TRIGGERED
        elif secondary == DesignToken.OPTIONAL_ZERO_COST_FRIENDLY_NAMED_MANEUVER:
            self.narrative_secondary[code] = NARR_SECONDARY_FREE_ANY_NAMED
        elif secondary == DesignToken.OPTIONAL_MOVE_ADJACENT_FRIENDLY_INTO_VACATED_POSITION:
            self.narrative_secondary[code] = NARR_SECONDARY_MOVE_VACATED
        battle_end = design.get(DesignField.AT_BATTLE_END) or {}
        if battle_end.get(DesignField.CONDITION) == DesignToken.CHOSEN_FRONT_NOT_LOST:
            self.narrative_end_kind[code] = NARR_END_NOT_LOST
        elif battle_end.get(DesignField.CONDITION) == DesignToken.CHOSEN_FRONT_WON:
            self.narrative_end_kind[code] = NARR_END_WON
        elif battle_end.get(DesignField.CONDITION) == DesignToken.CHOSEN_FORMATION_STILL_ON_BATTLEFIELD:
            self.narrative_end_kind[code] = NARR_END_TARGET_SURVIVES
        self.narrative_end_gain[code] = int(battle_end.get(DesignField.GAIN_COMMAND, 0))
        self.narrative_end_draw[code] = int(
            battle_end.get(DesignField.DRAW_CARDS, 0)
        )
        self.narrative_end_recover_bond[code] = 1 if battle_end.get(DesignField.BONUS_IF_WON) == DesignToken.RETURN_ONE_BOND_FROM_DISCARD_TO_HAND else 0
        self.narrative_end_discard[code] = bool(battle_end.get(DesignField.DISCARD_SELF, False))
        if design.get(DesignField.STRATAGEM) == DesignToken.ALL_RESERVES_FORWARD:
            self.strat_choice_kind[code] = STRAT_CHOICE_RESERVES
        elif design.get(DesignField.STRATAGEM) == DesignToken.WHEEL_LINE:
            self.strat_choice_kind[code] = STRAT_CHOICE_WHEEL
        elif design.get(DesignField.CHOSEN_FRONTS) == 2:
            self.strat_choice_kind[code] = STRAT_CHOICE_ADJACENT_FRONTS
        elif design.get(DesignField.CHOSEN_EDGE_FRONT):
            self.strat_choice_kind[code] = STRAT_CHOICE_EDGE_FRONT
        elif design.get(DesignField.CHOSEN_FRONT):
            self.strat_choice_kind[code] = STRAT_CHOICE_FRONT
        elif design.get(DesignField.DIRECTION_CHOICE) or design.get(DesignField.CHOOSE_DIRECTION):
            self.strat_choice_kind[code] = STRAT_CHOICE_DIRECTION

