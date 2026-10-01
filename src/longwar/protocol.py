from __future__ import annotations

from enum import StrEnum


PLAYER_COUNT = 2


class CardType(StrEnum):
    FORCE = "force"
    BOND = "bond"
    NAME = "name"
    NARRATIVE = "narrative"
    STRATAGEM = "stratagem"


class AgentKind(StrEnum):
    RANDOM = "random"
    HEURISTIC = "heuristic"
    STRATEGIC_HEURISTIC = "strategic_heuristic"
    ISMCTS = "ismcts"
    MCCFR = "mccfr"
    ONLINE_MCCFR = "online_mccfr"


class GameMode(StrEnum):
    HOTSEAT = "hotseat"
    REMOTE = "remote"
    COMPUTER = "computer"


class Direction(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class PolicySource(StrEnum):
    FORCED = "forced"
    HEURISTIC = "heuristic"
    STRATEGIC_HEURISTIC = "strategic_heuristic"
    ISMCTS = "ismcts"
    MCCFR = "mccfr"
    ONLINE_MCCFR = "online_mccfr"
    FALLBACK = "fallback"
    GUARD_FALLBACK = "guard_fallback"


class ActionKind(StrEnum):
    PASS = "pass"
    DISCARD = "discard"
    EFFECT_CHOICE = "effect_choice"
    MANEUVER = "maneuver"
    PLAY_FORCE = "play_force"
    PLAY_BOND = "play_bond"
    PLAY_NAME = "play_name"
    PLAY_NARRATIVE = "play_narrative"
    PLAY_STRATAGEM = "play_stratagem"


class ActionKeyToken(StrEnum):
    PASS = "pass"
    DISCARD = "discard"
    EFFECT = "effect"
    MANEUVER = "maneuver"
    FORCE = "force"
    BOND = "bond"
    NAME = "name"
    NARRATIVE = "narrative"
    STRATAGEM = "stratagem"
    SKIP = "skip"
    CARD = "card"
    SOURCE = "source"
    DESTINATION = "destination"
    FRONT = "front"
    FRONTS = "fronts"
    DIRECTION = "direction"
    TARGETS = "targets"
    MOVE = "move"
    EXTRA = "extra"
    DISCARD_FIELD = "discard"
    ONGOING = "ongoing"


class ForceRole(StrEnum):
    SWORDSMAN = "swordsman"
    SPEARMAN = "spearman"
    ARCHER = "archer"
    HEALER = "healer"
    SHIP = "ship"
    STRONGHOLD = "stronghold"
    SKIRMISHER = "skirmisher"


class NarrativeForm(StrEnum):
    LEGEND = "legend"
    MYTH = "myth"
    SAGA = "saga"
    OMEN = "omen"
    PROPHECY = "prophecy"
    WARNING = "warning"
    CONSPIRACY = "conspiracy"


class RuleBlockKind(StrEnum):
    PROPERTY = "property"
    TIMING = "timing"
    TRIGGER = "trigger"
    EFFECT = "effect"
    CONTINUOUS = "continuous"
    CONSTRAINT = "constraint"
    COST = "cost"
    REPLACEMENT = "replacement"


class DesignToken(StrEnum):
    AFTER_RETREAT = "after_retreat"
    ALL_RESERVES_FORWARD = "all_reserves_forward"
    BATTLE_TURNS_DIRECTION = "battle_turns_direction"
    BOND_RETURNS_TO_HAND_WHEN_FORCE_DRIVEN_OFF = "bond_returns_to_hand_when_force_driven_off"
    BREAKTHROUGH = "breakthrough"
    BREAKTHROUGH_IF_OPPONENT_NO_REAR_FORCE = "breakthrough_if_opponent_no_rear_force"
    CAPTURE = "capture"
    CARD_FOR_COMMAND = "card_for_command"
    CATCH_UP_DISCOUNT = "catch_up_discount"
    CHOSEN_FORMATION_STILL_ON_BATTLEFIELD = "chosen_formation_still_on_battlefield"
    CHOSEN_FRONT = "chosen_front"
    CHOSEN_FRONT_INSTEAD_OF_OWN = "chosen_front_instead_of_own"
    CHOSEN_FRONT_NOT_LOST = "chosen_front_not_lost"
    CHOSEN_FRONT_WON = "chosen_front_won"
    CHOSEN_NAMED_FORMATION = "chosen_named_formation"
    COMBINE_TWO_ADJACENT_FRONTS = "combine_two_adjacent_fronts"
    COMPLETION_DISCOUNT = "completion_discount"
    COMPLETION_REFUND = "completion_refund"
    DRAW_1 = "draw_1"
    DRAW_2 = "draw_2"
    DRIVE_OFF_SELF_PREVENT_FRONTLINE_RETREAT = "drive_off_self_prevent_frontline_retreat"
    ENCIRCLEMENT = "encirclement"
    FEIGNED_RETREAT = "feigned_retreat"
    FIRST_CARD_IN_FRONT_EACH_BATTLE_DISCOUNT_1_MIN_1 = "first_card_in_front_each_battle_discount_1_min_1"
    FIRST_FRIENDLY_MANEUVER_INTO_EMPTY_EACH_BATTLE = "first_friendly_maneuver_into_empty_each_battle"
    FIRST_NARRATIVE_EACH_BATTLE_DISCOUNT_1_MIN_1 = "first_narrative_each_battle_discount_1_min_1"
    FIRST_STRIKE = "first_strike"
    FREE_MANEUVER_ADJACENT_FRIENDLY_NAMED_FORMATION = "free_maneuver_adjacent_friendly_named_formation"
    FREE_MANEUVER_SELF = "free_maneuver_self"
    FRIENDLY_FORMATION_BECOMES_NAMED = "friendly_formation_becomes_named"
    FRIENDLY_NAMED_FORMATION_RETREATS = "friendly_named_formation_retreats"
    FRONTLINE_FORCE_DISCOUNT_1_MIN_1 = "frontline_force_discount_1_min_1"
    FRONTLINE_ONLY_COMPARISON = "frontline_only_comparison"
    HERO_RETINUE = "hero_retinue"
    HIGH_COST_BATTLE_INVESTMENT = "high_cost_battle_investment"
    INHERITED_BOND = "inherited_bond"
    INTERCEPTION = "interception"
    LOCAL_CATCH_UP_DISCOUNT = "local_catch_up_discount"
    NAME = "name"
    NAME_RETURNS_TO_HAND_WHEN_FORMATION_DRIVEN_OFF = "name_returns_to_hand_when_formation_driven_off"
    NO_RETREAT_FRONT = "no_retreat_front"
    OPEN_BOND = "open_bond"
    OPPONENT_HAS_FORCE_IN_BOTH_RANKS_SAME_FRONT = "opponent_has_force_in_both_ranks_same_front"
    OPPONENT_MANEUVERS_INTO_ADJACENT_FRONT = "opponent_maneuvers_into_adjacent_front"
    OPPOSING_FORMATION_BECOMES_NAMED = "opposing_formation_becomes_named"
    OPTIONAL_EXTRA_PAYMENT = "optional_extra_payment"
    OPTIONAL_IGNORE_OPPOSING_REAR_STRENGTH = "optional_ignore_opposing_rear_strength"
    OPTIONAL_MOVE_ADJACENT_FRIENDLY_INTO_VACATED_POSITION = "optional_move_adjacent_friendly_into_vacated_position"
    OPTIONAL_MOVE_ADJACENT_FRIENDLY_TO_VACATED_POSITION = "optional_move_adjacent_friendly_to_vacated_position"
    OPTIONAL_MOVE_FORMATION_ADJACENT_EMPTY_POSITION = "optional_move_formation_adjacent_empty_position"
    OPTIONAL_MOVE_ONE_MORE_FRONT_IF_EMPTY = "optional_move_one_more_front_if_empty"
    OPTIONAL_SIDEWAYS_REAR_MOVE = "optional_sideways_rear_move"
    OPTIONAL_SWAP_ADJACENT_FRIENDLY_FORMATION = "optional_swap_adjacent_friendly_formation"
    OPTIONAL_ZERO_COST_FRIENDLY_NAMED_MANEUVER = "optional_zero_cost_friendly_named_maneuver"
    OPTIONAL_ZERO_COST_MANEUVER_SWAPPED_FORMATION = "optional_zero_cost_maneuver_swapped_formation"
    OPTIONAL_ZERO_COST_MANEUVER_THAT_FORMATION = "optional_zero_cost_maneuver_that_formation"
    OWN_FRONT_WINS_AND_OPPOSING_FRONTLINE_NAMED_RETREATS = "own_front_wins_and_opposing_frontline_named_retreats"
    PROTECT_LOST_FRONT_HERE = "protect_lost_front_here"
    PROTECT_LOST_FRONTS = "protect_lost_fronts"
    REAR_REBUILD_COST_REDUCTION = "rear_rebuild_cost_reduction"
    REFUSE_FLANK = "refuse_flank"
    RETREAT_COMMAND_COMPENSATION = "retreat_command_compensation"
    RETREAT_SIDEWAYS = "retreat_sideways"
    RETURN_HERO_TO_HAND_IF_DRIVEN_OFF = "return_hero_to_hand_if_driven_off"
    RETURN_ONE_BOND_FROM_DISCARD_TO_HAND = "return_one_bond_from_discard_to_hand"
    RETURN_ONE_NARRATIVE_FROM_DISCARD_TO_HAND = "return_one_narrative_from_discard_to_hand"
    RETURN_RETREATING_FORMATION_BOND_TO_OWNER_HAND = "return_retreating_formation_bond_to_owner_hand"
    SACRIFICE = "sacrifice"
    SKIRMISH = "skirmish"
    START_BATTLE_REPOSITION = "start_battle_reposition"
    THIS_FORMATION = "this_formation"
    TIE_CONTROL = "tie_control"
    VOLUNTARY_RETREAT_IF_REAR_EMPTY = "voluntary_retreat_if_rear_empty"
    WHEEL_LINE = "wheel_line"


CARD_TYPES = frozenset(item.value for item in CardType)
FORCE_ROLES = frozenset(item.value for item in ForceRole)
NARRATIVE_FORMS = frozenset(item.value for item in NarrativeForm)
RULE_BLOCK_KINDS = frozenset(item.value for item in RuleBlockKind)
DIRECTIONS = frozenset(item.value for item in Direction)
