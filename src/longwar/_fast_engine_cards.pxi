cdef void _fe___cinit__(FastEngine self) except *:
    self.command_recovery_len = 0
    memset(
        self.command_recovery_values,
        0,
        sizeof(self.command_recovery_values),
    )
    memset(self.card_type, 0, sizeof(self.card_type))
    memset(self.card_command_cost, 0, sizeof(self.card_command_cost))
    memset(self.adjacent_command_discount, 0, sizeof(self.adjacent_command_discount))
    memset(self.completion_effect, 0, sizeof(self.completion_effect))
    memset(self.completion_amount, 0, sizeof(self.completion_amount))
    memset(self.complete_plot_protection, 0, sizeof(self.complete_plot_protection))
    memset(self.role, 0, sizeof(self.role))
    memset(self.strength, 0, sizeof(self.strength))
    memset(self.name_strength, 0, sizeof(self.name_strength))
    memset(self.hero, 0, sizeof(self.hero))
    memset(self.placement_rank, 0xff, sizeof(self.placement_rank))
    memset(self.force_text_effect, 0, sizeof(self.force_text_effect))
    memset(self.force_text_amount, 0, sizeof(self.force_text_amount))
    memset(self.can_maneuver_unnamed, 0, sizeof(self.can_maneuver_unnamed))
    memset(self.maneuver_requires_open_bond, 0, sizeof(self.maneuver_requires_open_bond))
    memset(self.bond_maneuver_adjacent_hero, 0, sizeof(self.bond_maneuver_adjacent_hero))
    memset(self.bond_blocks_opponent_card_move, 0, sizeof(self.bond_blocks_opponent_card_move))
    memset(self.bond_guarded_from_opponent_card_move, 0, sizeof(self.bond_guarded_from_opponent_card_move))
    memset(self.rear_force_prevents_frontline_retreat, 0, sizeof(self.rear_force_prevents_frontline_retreat))
    memset(self.force_breakthrough, 0, sizeof(self.force_breakthrough))
    memset(self.name_breakthrough, 0, sizeof(self.name_breakthrough))
    memset(self.first_maneuver_free, 0, sizeof(self.first_maneuver_free))
    memset(self.first_maneuver_free_empty_front, 0, sizeof(self.first_maneuver_free_empty_front))
    memset(self.local_catchup_discount_name, 0, sizeof(self.local_catchup_discount_name))
    memset(self.first_front_card_battle_discount_name, 0, sizeof(self.first_front_card_battle_discount_name))
    memset(self.first_narrative_battle_discount_force, 0, sizeof(self.first_narrative_battle_discount_force))
    memset(self.narrative_maneuver_empty_gain, 0, sizeof(self.narrative_maneuver_empty_gain))
    memset(self.narrative_trigger, 0, sizeof(self.narrative_trigger))
    memset(self.narrative_trigger_gain, 0, sizeof(self.narrative_trigger_gain))
    memset(self.narrative_trigger_discard, 0, sizeof(self.narrative_trigger_discard))
    memset(self.immobile_force, 0, sizeof(self.immobile_force))
    memset(self.cannot_swap_target, 0, sizeof(self.cannot_swap_target))
    memset(self.catchup_zero_cost, 0, sizeof(self.catchup_zero_cost))
    memset(self.completion_discount_cost, 0xff, sizeof(self.completion_discount_cost))
    memset(self.frontline_force_discount, 0, sizeof(self.frontline_force_discount))
    memset(self.frontline_force_discount_requires_named, 0, sizeof(self.frontline_force_discount_requires_named))
    memset(self.recovery_protected_front, 0, sizeof(self.recovery_protected_front))
    memset(self.driven_bond_stays, 0, sizeof(self.driven_bond_stays))
    memset(self.driven_bond_returns, 0, sizeof(self.driven_bond_returns))
    memset(self.driven_name_returns, 0, sizeof(self.driven_name_returns))
    memset(self.retreat_command_gain, 0, sizeof(self.retreat_command_gain))
    memset(self.capture_retreating_bond, 0, sizeof(self.capture_retreating_bond))
    memset(self.combat_frontline_only, 0, sizeof(self.combat_frontline_only))
    memset(self.completion_free_maneuver_self, 0, sizeof(self.completion_free_maneuver_self))
    memset(self.after_maneuver_free_adjacent, 0, sizeof(self.after_maneuver_free_adjacent))
    memset(self.completion_swap_adjacent, 0, sizeof(self.completion_swap_adjacent))
    memset(self.iria_name, 0, sizeof(self.iria_name))
    memset(self.skirmisher_contribution, 0, sizeof(self.skirmisher_contribution))
    memset(self.after_empty_follow_move, 0, sizeof(self.after_empty_follow_move))
    memset(self.after_swap_free_other, 0, sizeof(self.after_swap_free_other))
    memset(self.kept_pace_bond, 0, sizeof(self.kept_pace_bond))
    memset(self.covered_withdrawal_bond, 0, sizeof(self.covered_withdrawal_bond))
    memset(self.teren_name, 0, sizeof(self.teren_name))
    memset(self.mara_name, 0, sizeof(self.mara_name))
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
    memset(self.neris_rear_force, 0, sizeof(self.neris_rear_force))
    memset(self.neris_retreat_name, 0, sizeof(self.neris_retreat_name))
    memset(self.veyra_force, 0, sizeof(self.veyra_force))
    memset(self.veyra_name, 0, sizeof(self.veyra_name))
    memset(self.recover_story_on_completion_name, 0, sizeof(self.recover_story_on_completion_name))
    memset(self.optional_alda_protect_force, 0, sizeof(self.optional_alda_protect_force))
    memset(self.late_banner_force, 0, sizeof(self.late_banner_force))
    memset(self.torren_name, 0, sizeof(self.torren_name))
    memset(self.banner_singers_force, 0, sizeof(self.banner_singers_force))
    memset(self.carried_oath_bond, 0, sizeof(self.carried_oath_bond))
    memset(self.succession_name, 0, sizeof(self.succession_name))
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
    memset(self.strat_recovery_loss_reduction, 0, sizeof(self.strat_recovery_loss_reduction))
    memset(self.strat_no_retreat, 0, sizeof(self.strat_no_retreat))
    memset(self.strat_combine_fronts, 0, sizeof(self.strat_combine_fronts))
    memset(self.strat_refuse_flank, 0, sizeof(self.strat_refuse_flank))
    memset(self.strat_encirclement, 0, sizeof(self.strat_encirclement))
    memset(self.strat_directional_maneuver, 0, sizeof(self.strat_directional_maneuver))
    memset(self.on_link_bonus, 0, sizeof(self.on_link_bonus))
    memset(self.aura, 0, sizeof(self.aura))
    memset(self.aura_rank, 0xff, sizeof(self.aura_rank))
    memset(self.subject_mod_amount, 0, sizeof(self.subject_mod_amount))
    memset(self.subject_mod_discard_min, 0, sizeof(self.subject_mod_discard_min))
    memset(self.subject_mod_adj_named, 0, sizeof(self.subject_mod_adj_named))
    memset(self.link_bonus, 0, sizeof(self.link_bonus))
    memset(self.link_named_bonus, 0, sizeof(self.link_named_bonus))
    memset(self.link_discard_per, 0, sizeof(self.link_discard_per))
    memset(self.link_discard_max, 0, sizeof(self.link_discard_max))
    memset(self.link_opposing, 0, sizeof(self.link_opposing))
    memset(self.link_protect, 0, sizeof(self.link_protect))
    memset(self.bond_move_on_play, 0, sizeof(self.bond_move_on_play))
    memset(self.bond_optional_extra_cost, 0, sizeof(self.bond_optional_extra_cost))
    memset(self.bond_optional_draw_count, 0, sizeof(self.bond_optional_draw_count))
    memset(self.story_discard_count, 0, sizeof(self.story_discard_count))
    memset(self.story_discard_gain_command, 0, sizeof(self.story_discard_gain_command))
    memset(self.name_rank_bonus_rank, 0xff, sizeof(self.name_rank_bonus_rank))
    memset(self.name_rank_bonus_amount, 0, sizeof(self.name_rank_bonus_amount))
    memset(self.name_effect, 0, sizeof(self.name_effect))
    memset(self.plot_effect, 0, sizeof(self.plot_effect))
    memset(self.veiled, 0, sizeof(self.veiled))
    memset(self.story_choice_kind, 0, sizeof(self.story_choice_kind))
    memset(self.scheme_trigger, 0, sizeof(self.scheme_trigger))
    memset(self.scheme_effect, 0, sizeof(self.scheme_effect))
    memset(self.scheme_amount, 0, sizeof(self.scheme_amount))
    memset(self.scheme_requires_subject, 0, sizeof(self.scheme_requires_subject))
    memset(self.scheme_face_bonus, 0, sizeof(self.scheme_face_bonus))
    memset(self.strat_choice_kind, 0, sizeof(self.strat_choice_kind))
    memset(self.strat_trigger_event, 0, sizeof(self.strat_trigger_event))
    memset(self.strat_actor, 0, sizeof(self.strat_actor))
    memset(self.strat_role_mask, 0, sizeof(self.strat_role_mask))
    memset(self.strat_rank_mask, 0, sizeof(self.strat_rank_mask))
    memset(self.strat_reveal_effect, 0, sizeof(self.strat_reveal_effect))
    memset(self.strat_reveal_amount, 0, sizeof(self.strat_reveal_amount))
    memset(self.strat_cancel_story, 0, sizeof(self.strat_cancel_story))
    memset(self.strat_role_mod, 0, sizeof(self.strat_role_mod))
    memset(self.strat_rank_mod, 0, sizeof(self.strat_rank_mod))
    memset(self.strat_controller_rank_mod, 0, sizeof(self.strat_controller_rank_mod))
    memset(self.strat_named_mod, 0, sizeof(self.strat_named_mod))
    memset(self.strat_unnamed_mod, 0, sizeof(self.strat_unnamed_mod))
    memset(self.strat_story_lock, 0, sizeof(self.strat_story_lock))
    memset(self.strat_global_story_lock, 0, sizeof(self.strat_global_story_lock))

cdef void _fe___init__(FastEngine self, engine) except *:
    cdef int code, r
    self.card_ids = tuple(engine.cards)
    self.n_cards = len(self.card_ids)
    self.opening_hand_size = int(engine.opening_hand_size)
    self.command_cap = int(engine.command_cap)
    self.command_recovery_schedule = tuple(engine.command_recovery_schedule)
    if len(self.command_recovery_schedule) > MAX_RECOVERY_SCHEDULE:
        raise ValueError(
            f"Command recovery schedule supports at most "
            f"{MAX_RECOVERY_SCHEDULE} entries"
        )
    self.command_recovery_len = len(self.command_recovery_schedule)
    for r in range(self.command_recovery_len):
        self.command_recovery_values[r] = int(
            self.command_recovery_schedule[r]
        )
    self.command_collapse_threshold = int(engine.command_collapse_threshold)
    self.maneuver_command_cost = int(engine.maneuver_command_cost)
    self.hand_limit = int(engine.hand_limit)
    self.ongoing_story_limit = int(engine.ongoing_narrative_limit)
    if self.n_cards > MAX_CARDS:
        raise ValueError(f"The native engine supports at most {MAX_CARDS} card identities")
    if max(engine.starting_command, self.command_cap) > 32767:
        raise ValueError("Command settings exceed the native signed 16-bit capacity")
    self.id_to_code = {card_id: i for i, card_id in enumerate(self.card_ids)}

    type_map = {"force": CARD_SUBJECT, "bond": CARD_LINK, "name": CARD_NAME, "story": CARD_PLOT, "stratagem": CARD_STRATAGEM}
    role_map = {"swordsman": ROLE_SWORDSMAN, "spearman": ROLE_SPEARMAN, "archer": ROLE_ARCHER, "healer": ROLE_HEALER, "ship": ROLE_SHIP, "stronghold": ROLE_STRONGHOLD}
    name_effect_map = {"move_adjacent_optional": NAME_MOVE_ADJACENT, "reveal_enemy_scheme": NAME_REVEAL_SCHEME}
    completion_effect_map = {
        "gain_command": COMPLETE_GAIN_COMMAND,
        "draw_card": COMPLETE_DRAW,
        "reveal_enemy_scheme": COMPLETE_REVEAL_SCHEME,
        "recover_recent_link": COMPLETE_RECOVER_LINK,
    }
    plot_effect_map = {"discredit_subject": PLOT_DISCREDIT, "return_name_or_weaken": PLOT_RETURN_NAME, "move_subject": PLOT_MOVE_SUBJECT}
    scheme_trigger_map = {"opponent_plays_subject": EVENT_SUBJECT, "opponent_plays_link": EVENT_LINK, "opponent_passes": EVENT_PASS, "opponent_plot_targets_your_card": EVENT_PLOT_TARGET}
    scheme_effect_map = {"penalize_played_subject": SCHEME_PENALIZE_SUBJECT, "discard_played_link": SCHEME_DISCARD_LINK, "reinforce_front": SCHEME_REINFORCE}
    strat_event_map = {"subject_played": EVENT_SUBJECT, "pass": EVENT_PASS, "immediate_story_played": EVENT_IMMEDIATE_STORY, "name_played": EVENT_NAME}
    actor_map = {"either": ACTOR_EITHER, "opponent": ACTOR_OPPONENT, "controller": ACTOR_CONTROLLER}
    rank_map = {"front": 0, "rear": 1}
    force_text_map = {
        "frontline_strength_bonus": FORCE_TEXT_FRONT_BONUS,
        "rear_strength_bonus": FORCE_TEXT_REAR_BONUS,
        "support_force_ahead_strength_bonus": FORCE_TEXT_SUPPORT_AHEAD,
        "frontline_strength_bonus_if_force_behind": FORCE_TEXT_FRONT_IF_REAR,
        "rear_strength_bonus_if_force_ahead": FORCE_TEXT_REAR_IF_FRONT,
    }

    for code, card_id in enumerate(self.card_ids):
        card = engine.cards[card_id]
        self.card_type[code] = type_map[card["type"]]
        self.role[code] = role_map.get(card.get("role"), ROLE_NONE)
        self.strength[code] = int(card.get("strength", 0))
        self.name_strength[code] = int(
            card.get(
                "hero_name_strength",
                card.get("strength", 0) if card["type"] == "name" else 0,
            )
        )
        self.hero[code] = bool(card.get("hero", False))
        rules = card.get("rules", {})
        design = card.get("design_rules") or {}
        force_design = design.get("force") or design
        self.card_command_cost[code] = int(card.get("command_cost", 0))
        self.adjacent_command_discount[code] = int(rules.get("adjacent_command_discount", 0))

        completion = rules.get("on_completion") or {}
        self.completion_effect[code] = completion_effect_map.get(completion.get("effect"), COMPLETE_NONE)
        self.completion_amount[code] = int(completion.get("amount", 1))
        if (
            design.get("trigger") == "friendly_formation_becomes_named"
            and design.get("scope") == "this_formation"
        ):
            if design.get("gain_command"):
                self.completion_effect[code] = COMPLETE_GAIN_COMMAND
                self.completion_amount[code] = int(design["gain_command"])
            elif design.get("draw_cards"):
                self.completion_effect[code] = COMPLETE_DRAW
                self.completion_amount[code] = int(design["draw_cards"])
        if design.get("command") == "completion_refund":
            completion_design = design.get("on_completion") or {}
            if completion_design.get("gain_command"):
                self.completion_effect[code] = COMPLETE_GAIN_COMMAND
                self.completion_amount[code] = int(completion_design["gain_command"])

        self.complete_plot_protection[code] = bool(rules.get("complete_protection_from_opponent_plot"))
        placement = (
            force_design.get("deploy_rank")
            or design.get("deploy_rank")
            or rules.get("placement", {}).get("rank")
        )
        self.placement_rank[code] = rank_map.get(placement, -1)
        printed_effect = force_design.get("printed_role_effect") or design.get("printed_role_effect")
        self.force_text_effect[code] = force_text_map.get(printed_effect, FORCE_TEXT_NONE)
        self.force_text_amount[code] = int(
            force_design.get("amount", design.get("amount", 0))
        )
        self.can_maneuver_unnamed[code] = bool(
            force_design.get("can_maneuver_while_unnamed")
            or design.get("can_maneuver_while_unnamed")
        )
        if design.get("build_around") == "open_bond":
            self.maneuver_requires_open_bond[code] = 1
        if design.get("build_around") == "hero_retinue":
            self.bond_maneuver_adjacent_hero[code] = 1
        if design.get("prevent_opponent_card_effect_move_into_front_from_adjacent"):
            self.bond_blocks_opponent_card_move[code] = 1
        if design.get("prevent_opponent_card_effect_movement"):
            self.bond_guarded_from_opponent_card_move[code] = 1
        lost_front = design.get("lost_front") or {}
        if lost_front.get("effect") == "drive_off_self_prevent_frontline_retreat":
            self.rear_force_prevents_frontline_retreat[code] = 1
        if design.get("first_maneuver_each_battle_cost") == 0:
            self.first_maneuver_free[code] = 1
        if design.get("first_self_maneuver_each_battle_cost") == 0:
            self.first_maneuver_free_empty_front[code] = 1
        if design.get("command") == "local_catch_up_discount":
            self.local_catchup_discount_name[code] = int(
                design.get("first_card_each_turn_discount", 1)
            )
        name_design = design.get("name") or {}
        if name_design.get("command") == "first_card_in_front_each_battle_discount_1_min_1":
            self.first_front_card_battle_discount_name[code] = 1
        if force_design.get("story") == "first_story_each_battle_discount_1_min_1":
            self.first_narrative_battle_discount_force[code] = 1
        if force_design.get("combat") == "breakthrough":
            self.force_breakthrough[code] = 1
        name_design = design.get("name") or {}
        if name_design.get("combat") == "breakthrough_if_opponent_no_rear_force":
            self.name_breakthrough[code] = 1
        self.immobile_force[code] = bool(
            force_design.get("immobile") or design.get("immobile")
        )
        self.cannot_swap_target[code] = bool(
            force_design.get("cannot_be_swap_target")
            or design.get("cannot_be_swap_target")
        )
        if design.get("command") == "catch_up_discount":
            self.catchup_zero_cost[code] = 1
        if design.get("command") == "completion_discount":
            self.completion_discount_cost[code] = int(
                design.get("discounted_cost", card.get("command_cost", 0))
            )
        if design.get("persistence") == "rear_rebuild_cost_reduction":
            self.frontline_force_discount[code] = 1
            self.frontline_force_discount_requires_named[code] = 1
        if force_design.get("command") == "frontline_force_discount_1_min_1":
            self.frontline_force_discount[code] = 1
        if force_design.get("command") == "lost_front_here_does_not_reduce_recovery":
            self.recovery_protected_front[code] = 1
        if design.get("persistence") == "inherited_bond":
            self.driven_bond_stays[code] = 1
        if design.get("persistence") == "bond_returns_to_hand_when_force_driven_off":
            self.driven_bond_returns[code] = 1
        if (
            design.get("persistence") == "name_returns_to_hand_when_formation_driven_off"
            or (design.get("name") or {}).get("effect") == "return_hero_to_hand_if_driven_off"
        ):
            self.driven_name_returns[code] = 1
        if design.get("persistence") == "retreat_command_compensation":
            self.retreat_command_gain[code] = int(design.get("amount", 1))
        if (
            design.get("combat") == "capture"
            and design.get("trigger")
            == "own_front_wins_and_opposing_frontline_named_retreats"
            and design.get("timing") == "after_retreat"
            and design.get("effect")
            == "return_retreating_formation_bond_to_owner_hand"
        ):
            self.capture_retreating_bond[code] = 1
        if design.get("combat") == "frontline_only_comparison":
            self.combat_frontline_only[code] = 1
        if design.get("trigger") == "opposing_formation_in_same_front_becomes_named":
            self.iria_name[code] = 1
        completion_design = design.get("on_completion") or {}
        if completion_design.get("effect") == "optional_swap_adjacent_friendly_formation":
            self.completion_swap_adjacent[code] = 1
        name_completion = name_design.get("on_completion")
        if (
            isinstance(name_completion, dict)
            and name_completion.get("effect") == "free_maneuver_self"
        ):
            self.completion_free_maneuver_self[code] = 1
        if (force_design.get("after_maneuver") or {}).get("effect") == "free_maneuver_adjacent_friendly_named_formation":
            self.after_maneuver_free_adjacent[code] = 1
        if name_design.get("on_completion") == "return_one_bond_from_discard_to_hand":
            self.recover_bond_on_completion_name[code] = 1
        if name_design.get("on_completion") == "return_one_story_from_discard_to_hand":
            self.recover_story_on_completion_name[code] = 1
        front_resolution = design.get("front_resolution") or {}
        if front_resolution.get("contribution") == "chosen_front_instead_of_own":
            self.skirmisher_contribution[code] = 1
        if (design.get("after_maneuver_into_empty") or {}).get("effect") == "optional_move_adjacent_friendly_to_vacated_position":
            self.after_empty_follow_move[code] = 1
        if (design.get("after_maneuver_swap") or {}).get("effect") == "optional_zero_cost_maneuver_swapped_formation":
            self.after_swap_free_other[code] = 1
        if design.get("trigger") == "adjacent_friendly_named_formation_maneuvers_away":
            self.kept_pace_bond[code] = 1
        if design.get("trigger") == "adjacent_friendly_formation_retreats":
            self.covered_withdrawal_bond[code] = 1
        if (design.get("after_maneuver") or {}).get("effect") == "optional_swap_two_adjacent_friendly_formations_excluding_self":
            self.teren_name[code] = 1
        if design.get("trigger") == "opposing_formation_maneuvers_into_same_front":
            self.mara_name[code] = 1
        if design.get("combat") == "skirmish":
            self.suppress_rear_force[code] = 1
        if design.get("combat") == "first_strike":
            self.first_strike_force[code] = 1
        if design.get("combat") == "sacrifice":
            self.sacrifice_bond[code] = 1
        if design.get("combat") == "interception":
            self.intercept_name[code] = 1
        if design.get("persistence") == "retreat_sideways":
            self.retreat_sideways_name[code] = 1
        if design.get("persistence") == "start_battle_reposition":
            self.battle_start_move_name[code] = 1
        if design.get("persistence") == "voluntary_retreat_if_rear_empty":
            self.voluntary_retreat_name[code] = 1
        if force_design.get("after_maneuver_into_empty") == "optional_move_one_more_front_if_empty":
            self.after_empty_extra_move_force[code] = 1
        if name_design.get("trigger") == "opponent_maneuvers_into_adjacent_front":
            self.reactive_maneuver_name[code] = 1
        if force_design.get("combat") == "optional_ignore_opposing_rear_strength":
            self.suppress_rear_force[code] = 1
        if force_design.get("effect") == "optional_drive_off_self_prevent_frontline_named_retreat":
            self.optional_alda_protect_force[code] = 1
        if force_design.get("after_frontline_retreat") == "optional_sideways_rear_move":
            self.neris_rear_force[code] = 1
        if name_design.get("after_self_retreat") == "optional_sideways_rear_move":
            self.neris_retreat_name[code] = 1
        if force_design.get("on_play") == "optional_take_adjacent_prepared_bond_or_name":
            self.veyra_force[code] = 1
        if name_design.get("on_play") == "optional_take_adjacent_open_bond":
            self.veyra_name[code] = 1
        if design.get("build_around") == "prepared_position":
            self.late_banner_force[code] = 1
        if design.get("after_self_maneuver") == "optional_zero_cost_other_friendly_named_maneuver":
            self.torren_name[code] = 1
        if design.get("trigger") == "regain_command_from_narrative":
            self.banner_singers_force[code] = 1
        if design.get("build_around") == "open_bond_transfer":
            self.carried_oath_bond[code] = 1
        if design.get("build_around") == "succession":
            self.succession_name[code] = 1
        if design.get("combat") == "tie_control":
            self.strat_tie_control[code] = 1
        if design.get("command") == "high_cost_battle_investment":
            self.strat_maneuver_cost[code] = int(design.get("maneuver_cost", -1))
            self.strat_unnamed_maneuver[code] = bool(
                design.get("unnamed_formations_can_maneuver")
            )
        if design.get("command") == "improve_recovery":
            self.strat_recovery_loss_reduction[code] = max(
                0, -int(design.get("lost_front_adjustment", 0))
            )
        if design.get("stratagem") == "no_retreat_front":
            self.strat_no_retreat[code] = 1
        if design.get("stratagem") == "combine_two_adjacent_fronts":
            self.strat_combine_fronts[code] = 1
        if design.get("stratagem") == "refuse_flank":
            self.strat_refuse_flank[code] = 1
        if design.get("stratagem") == "encirclement":
            self.strat_encirclement[code] = 1
        if design.get("stratagem") == "feigned_retreat":
            self.feigned_retreat_strat[code] = 1
        if design.get("stratagem") == "battle_turns_direction":
            self.strat_directional_maneuver[code] = 1

        self.on_link_bonus[code] = int(rules.get("on_link_attached", {}).get("temporary_strength", 0))
        self.aura[code] = int(rules.get("adjacent_strength_aura", 0))
        self.aura_rank[code] = rank_map.get(rules.get("aura_requires_rank"), -1)
        modifiers = rules.get("strength_modifiers", ())
        if modifiers:
            modifier = modifiers[0]
            condition = modifier.get("when", {})
            self.subject_mod_amount[code] = int(modifier.get("amount", 0))
            self.subject_mod_discard_min[code] = int(condition.get("own_discard_at_least", 0))
            self.subject_mod_adj_named[code] = bool(condition.get("adjacent_subject_has_name"))

        self.link_bonus[code] = int(
            design.get("strength_bonus", rules.get("strength_bonus", 0))
        )
        self.link_named_bonus[code] = int(
            design.get(
                "named_additional_strength_bonus",
                rules.get("named_strength_bonus", 0),
            )
        )
        discard_bonus = rules.get("discard_strength_bonus") or {}
        self.link_discard_per[code] = int(discard_bonus.get("per_card", 0))
        self.link_discard_max[code] = int(discard_bonus.get("maximum", 0))
        self.link_opposing[code] = int(rules.get("opposing_front_modifier", 0))
        self.link_protect[code] = bool(rules.get("protect_subject_from_opponent_plot"))
        on_play_bond = design.get("on_play_onto_force") or {}
        if on_play_bond.get("effect") == "optional_move_formation_adjacent_empty_position":
            self.bond_move_on_play[code] = 1
        if design.get("command") == "optional_extra_payment":
            self.bond_optional_extra_cost[code] = int(
                design.get("extra_cost", 0)
            )
            if design.get("effect") == "draw_2":
                self.bond_optional_draw_count[code] = 2
        if design.get("command") == "card_for_command":
            self.story_discard_count[code] = int(
                design.get("discard_cards", 0)
            )
            self.story_discard_gain_command[code] = int(
                design.get("gain_command", 0)
            )

        rank_bonus = rules.get("rank_strength_bonus") or {}
        self.name_rank_bonus_rank[code] = rank_map.get(rank_bonus.get("rank"), -1)
        self.name_rank_bonus_amount[code] = int(rank_bonus.get("amount", 0))
        self.name_effect[code] = name_effect_map.get(rules.get("on_name_attached"), NAME_NONE)

        self.plot_effect[code] = plot_effect_map.get(rules.get("effect"), PLOT_NONE)
        self.veiled[code] = bool(card.get("ongoing", False))
        if design.get("placement") == "chosen_front":
            self.story_choice_kind[code] = STORY_CHOICE_FRONT
        elif design.get("placement") == "chosen_named_formation":
            self.story_choice_kind[code] = STORY_CHOICE_NAMED_FORMATION
        if design.get("trigger") == "first_friendly_maneuver_into_empty_each_battle":
            self.narrative_maneuver_empty_gain[code] = int(
                design.get("gain_command", 0)
            )
        if design.get("trigger") == "friendly_formation_becomes_named":
            self.narrative_trigger[code] = NARR_TRIGGER_FRIENDLY_NAMED
        elif design.get("trigger") == "friendly_named_formation_retreats":
            self.narrative_trigger[code] = NARR_TRIGGER_FRIENDLY_RETREAT
        elif design.get("trigger") == "opposing_formation_becomes_named":
            self.narrative_trigger[code] = NARR_TRIGGER_OPPONENT_NAMED
        elif design.get("trigger") == "opponent_has_force_in_both_ranks_same_front":
            self.narrative_trigger[code] = NARR_TRIGGER_OPPONENT_BOTH_RANKS
        self.narrative_trigger_gain[code] = int(
            design.get("gain_command", 0)
        )
        self.narrative_trigger_discard[code] = bool(
            design.get("discard_self", False)
        )
        secondary = design.get("secondary")
        if secondary == "optional_zero_cost_maneuver_that_formation":
            self.narrative_secondary[code] = NARR_SECONDARY_FREE_TRIGGERED
        elif secondary == "optional_sideways_rear_move":
            self.narrative_secondary[code] = NARR_SECONDARY_SIDEWAYS_TRIGGERED
        elif secondary == "optional_zero_cost_friendly_named_maneuver":
            self.narrative_secondary[code] = NARR_SECONDARY_FREE_ANY_NAMED
        elif secondary == "optional_move_adjacent_friendly_into_vacated_position":
            self.narrative_secondary[code] = NARR_SECONDARY_MOVE_VACATED
        battle_end = design.get("at_battle_end") or {}
        if battle_end.get("condition") == "chosen_front_not_lost":
            self.narrative_end_kind[code] = NARR_END_NOT_LOST
        elif battle_end.get("condition") == "chosen_front_won":
            self.narrative_end_kind[code] = NARR_END_WON
        elif battle_end.get("condition") == "chosen_formation_still_on_battlefield":
            self.narrative_end_kind[code] = NARR_END_TARGET_SURVIVES
        self.narrative_end_gain[code] = int(battle_end.get("gain_command", 0))
        self.narrative_end_draw[code] = 1 if battle_end.get("secondary") == "draw_1" else 0
        self.narrative_end_recover_bond[code] = 1 if battle_end.get("bonus_if_won") == "return_one_bond_from_discard_to_hand" else 0
        self.narrative_end_discard[code] = bool(battle_end.get("discard_self", False))
        scheme = rules.get("scheme") or {}
        self.scheme_trigger[code] = scheme_trigger_map.get(scheme.get("trigger"), EVENT_NONE)
        self.scheme_effect[code] = scheme_effect_map.get(scheme.get("effect"), SCHEME_NONE)
        self.scheme_amount[code] = int(scheme.get("amount", 0))
        self.scheme_requires_subject[code] = bool(scheme.get("requires_own_subject"))
        self.scheme_face_bonus[code] = int(scheme.get("face_down_front_bonus", 0))

        if design.get("stratagem") == "all_reserves_forward":
            self.strat_choice_kind[code] = STRAT_CHOICE_RESERVES
        elif design.get("stratagem") == "wheel_line":
            self.strat_choice_kind[code] = STRAT_CHOICE_WHEEL
        elif design.get("chosen_fronts") == 2:
            self.strat_choice_kind[code] = STRAT_CHOICE_ADJACENT_FRONTS
        elif design.get("chosen_edge_front"):
            self.strat_choice_kind[code] = STRAT_CHOICE_EDGE_FRONT
        elif design.get("chosen_front"):
            self.strat_choice_kind[code] = STRAT_CHOICE_FRONT
        elif design.get("direction_choice"):
            self.strat_choice_kind[code] = STRAT_CHOICE_DIRECTION

        strat = rules.get("stratagem") or {}
        trigger = strat.get("trigger") or {}
        self.strat_trigger_event[code] = strat_event_map.get(trigger.get("event"), EVENT_NONE)
        self.strat_actor[code] = actor_map.get(trigger.get("actor", "either"), ACTOR_EITHER)
        for role_name in trigger.get("roles", ()):
            r = role_map.get(role_name, ROLE_NONE)
            self.strat_role_mask[code] |= (1 << r)
        for rank_name in trigger.get("ranks", ()):
            r = rank_map.get(rank_name, -1)
            if r >= 0:
                self.strat_rank_mask[code] |= (1 << r)
        reveal = strat.get("reveal_effect") or {}
        if reveal.get("effect") == "penalize_trigger_subject":
            self.strat_reveal_effect[code] = STRAT_REVEAL_PENALIZE
        self.strat_reveal_amount[code] = int(reveal.get("amount", 0))
        self.strat_cancel_story[code] = bool(reveal.get("cancel_story"))
        continuous = strat.get("continuous") or {}
        for role_name, amount in continuous.get("role_strength_modifiers", {}).items():
            r = role_map.get(role_name, ROLE_NONE)
            self.strat_role_mod[code][r] = int(amount)
        for rank_name, amount in continuous.get("rank_strength_modifiers", {}).items():
            self.strat_rank_mod[code][rank_map[rank_name]] = int(amount)
        for rank_name, amount in continuous.get("controller_rank_strength_modifiers", {}).items():
            self.strat_controller_rank_mod[code][rank_map[rank_name]] = int(amount)
        self.strat_named_mod[code] = int(continuous.get("named_subject_modifier", 0))
        self.strat_unnamed_mod[code] = int(continuous.get("unnamed_subject_modifier", 0))
        self.strat_story_lock[code] = bool(continuous.get("controller_immediate_story_lock"))
        self.strat_global_story_lock[code] = bool(continuous.get("global_immediate_story_lock"))
