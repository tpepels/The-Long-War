from __future__ import annotations

from enum import IntEnum, StrEnum


PLAYER_COUNT = 2
NARRATIVE_STORAGE_CAPACITY_PER_PLAYER = 4
STRATAGEM_ACTIVE_CAPACITY_PER_PLAYER = 1


class CardType(StrEnum):
    FORCE = "force"
    BOND = "bond"
    NAME = "name"
    HERO = "hero"
    TACTIC = "tactic"
    ORDER = "order"
    NARRATIVE = "narrative"
    STRATAGEM = "stratagem"


class AgentKind(StrEnum):
    RANDOM = "random"
    HEURISTIC = "heuristic"
    STRATEGIC_HEURISTIC = "strategic_heuristic"
    ISMCTS = "ismcts"
    MCCFR = "mccfr"
    ONLINE_MCCFR = "online_mccfr"


class RolloutPolicy(StrEnum):
    GREEDY = "greedy"
    CHEAP = "cheap"
    RANDOM = "random"
    DECISIVE = "decisive"


class RolloutPolicyCode(IntEnum):
    GREEDY = 0
    CHEAP = 1
    RANDOM = 2
    DECISIVE = 3


class SearchBackend(StrEnum):
    AUTO = "auto"
    CYTHON = "cython"
    PYTHON = "python"


MCCFR_POLICY_SCHEMA_VERSION = 5


class GameMode(StrEnum):
    HOTSEAT = "hotseat"
    REMOTE = "remote"
    COMPUTER = "computer"


class PlaySetupMode(StrEnum):
    COMPUTER = "computer"
    COMPUTER_CANONICAL = "computer-canonical"
    HOTSEAT = "hotseat"
    REMOTE_HOST = "remote-host"
    REMOTE_JOIN = "remote-join"


class Direction(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class DirectionCode(IntEnum):
    NONE = 0
    LEFT = 1
    RIGHT = 2


class SessionPhase(StrEnum):
    MULLIGAN = "mulligan"


class RequestType(StrEnum):
    NEW_GAME = "new_game"
    VIEW = "view"
    ACT = "act"
    AI_STEP = "ai_step"
    MULLIGAN = "mulligan"


class RemoteRole(StrEnum):
    HOST = "host"
    GUEST = "guest"


class RemoteSetupPhase(StrEnum):
    IDLE = "idle"
    CREATING = "creating"
    WAITING = "waiting"
    AWAIT_ANSWER = "await-answer"


class RemoteMessageType(StrEnum):
    COMMAND = "command"
    SNAPSHOT = "snapshot"
    ERROR = "error"


class PendingResume(StrEnum):
    FINISH_OPERATION = "finish_operation"
    BATTLE_RESOLUTION = "battle_resolution"
    START_BATTLE = "start_battle"


class ObservationKind(StrEnum):
    HIDDEN_KNOWLEDGE = "hidden_knowledge"
    REVEAL = "reveal"


class ObservationZone(StrEnum):
    HAND = "hand"


class EffectKind(StrEnum):
    ACTIVATE_ABILITY = "activate-ability"
    V2_TARGET = "v2-target"
    V2_CHOICE = "v2-choice"
    FREE_MANEUVER = "free-maneuver"
    MOVE = "move"
    SWAP = "swap"
    RECOVER = "recover"
    FRONT_CONTRIBUTION = "front-contribution"
    SUPPRESS = "suppress"
    SACRIFICE = "sacrifice"
    INTERCEPT = "intercept"
    RETREAT = "retreat"
    PROTECT_RETREAT = "protect-retreat"
    TRANSFER_COMPONENT = "transfer-component"
    SUCCESSION = "succession"


class CardClass(StrEnum):
    HERO = "hero"


class PolicySource(StrEnum):
    FORCED = "forced"
    HEURISTIC = "heuristic"
    STRATEGIC_HEURISTIC = "strategic_heuristic"
    ISMCTS = "ismcts"
    MCCFR = "mccfr"
    ONLINE_MCCFR = "online_mccfr"
    FALLBACK = "fallback"
    GUARD_FALLBACK = "guard_fallback"


class CommandDiagnosticKind(StrEnum):
    GAIN = "gain"
    DISCOUNT = "discount"
    FRONT_LOSS_PROTECTION = "front_loss_protection"


class CommandDiagnosticDetail(StrEnum):
    COMPLETION_GAIN = "completion_gain"
    NARRATIVE_GAIN = "narrative_gain"
    RETREAT_GAIN = "retreat_gain"
    DISCARD_FOR_COMMAND = "discard_for_command"
    CATCHUP_DISCOUNT = "catchup_discount"
    COMPLETION_DISCOUNT = "completion_discount"
    NARRATIVE_DISCOUNT = "narrative_discount"
    LOCAL_FRONT_DISCOUNT = "local_front_discount"
    ADJACENT_DISCOUNT = "adjacent_discount"
    FRONTLINE_DISCOUNT = "frontline_discount"
    FREE_MANEUVER = "free_maneuver"
    STRATAGEM_MANEUVER_DISCOUNT = "stratagem_maneuver_discount"
    FRONT_LOSS_PROTECTED_FRONT = "front_loss_protected_front"
    FRONT_LOSS_STRATAGEM = "front_loss_stratagem"
    OTHER = "other"


class ActionKind(StrEnum):
    PASS = "Pass"
    END_TURN = "EndTurn"
    CYCLE = "Cycle"
    DISCARD = "Discard"
    EFFECT_CHOICE = "EffectChoice"
    MANEUVER = "Maneuver"
    PLAY_FORCE = "PlayForce"
    PLAY_BOND = "PlayBond"
    PLAY_NAME = "PlayName"
    PLAY_NARRATIVE = "PlayNarrative"
    PLAY_STRATAGEM = "PlayStratagem"
    PLAY_TACTIC = "PlayTactic"
    PLAY_ORDER = "PlayOrder"
    ACTIVATE_ABILITY = "ActivateAbility"


class ActionKeyToken(StrEnum):
    PASS = "pass"
    END_TURN = "end-turn"
    CYCLE = "cycle"
    DISCARD = "discard"
    EFFECT = "effect"
    MANEUVER = "maneuver"
    FORCE = "force"
    BOND = "bond"
    NAME = "name"
    NARRATIVE = "narrative"
    STRATAGEM = "stratagem"
    TACTIC = "tactic"
    ORDER = "order"
    ABILITY = "ability"
    OPTION = "option"
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


class RuleBlockField(StrEnum):
    KIND = "kind"
    LABEL = "label"
    TEXT = "text"
    MODE = "mode"


class CardField(StrEnum):
    ID = "id"
    TITLE = "title"
    TYPE = "type"
    STRENGTH = "strength"
    COMMAND_COST = "command_cost"
    UNIQUE = "unique"
    HERO = "hero"
    HERO_NAME_STRENGTH = "hero_name_strength"
    FORCE_STRENGTH = "force_strength"
    NAME_STRENGTH_MODIFIER = "name_strength_modifier"
    STRENGTH_MODIFIER = "strength_modifier"
    ROLE = "role"
    CLASSES = "classes"
    TEXT = "text"
    DESIGN_RULES = "design_rules"
    RULE_BLOCKS = "rule_blocks"
    EXPERIMENTAL = "experimental"
    BASELINE_FOR = "baseline_for"
    NARRATIVE_FORM = "narrative_form"
    ONGOING = "ongoing"
    EFFECTS = "effects"
    MODES = "modes"
    ALLOWED_ROWS = "allowed_rows"
    DURATION = "duration"
    BOND_KIND = "bond_kind"
    DESIGN_TAGS = "design_tags"


class DesignField(StrEnum):
    AFTER_FRONTLINE_RETREAT = "after_frontline_retreat"
    AFTER_MANEUVER = "after_maneuver"
    AFTER_MANEUVER_INTO_EMPTY = "after_maneuver_into_empty"
    AFTER_MANEUVER_SWAP = "after_maneuver_swap"
    AFTER_SELF_MANEUVER = "after_self_maneuver"
    AFTER_SELF_RETREAT = "after_self_retreat"
    AMOUNT = "amount"
    AT_BATTLE_END = "at_battle_end"
    BONUS_IF_WON = "bonus_if_won"
    BUILD_AROUND = "build_around"
    CAN_MANEUVER_WHILE_UNNAMED = "can_maneuver_while_unnamed"
    CANNOT_BE_SWAP_TARGET = "cannot_be_swap_target"
    CHOOSE_DIRECTION = "choose_direction"
    CHOOSE_FRIENDLY_NAMED_FORMATION = "choose_friendly_named_formation"
    CHOSEN_EDGE_FRONT = "chosen_edge_front"
    CHOSEN_FRONT = "chosen_front"
    CHOSEN_FRONT_REQUIRES_FRIENDLY_NAMED_FORMATION = "chosen_front_requires_friendly_named_formation"
    CHOSEN_FRONTS = "chosen_fronts"
    COMBAT = "combat"
    COMMAND = "command"
    COMMAND_COST = "command_cost"
    CONDITION = "condition"
    CONTRIBUTION = "contribution"
    DEPLOY_RANK = "deploy_rank"
    DIRECTION_CHOICE = "direction_choice"
    DISCARD_CARDS = "discard_cards"
    DISCARD_SELF = "discard_self"
    DISCOUNT_AMOUNT = "discount_amount"
    DISCOUNTED_COST = "discounted_cost"
    DRAW_CARDS = "draw_cards"
    EFFECT = "effect"
    EXTRA_COST = "extra_cost"
    FIRST_MANEUVER_EACH_BATTLE_COST = "first_maneuver_each_battle_cost"
    FIRST_MANEUVER_EACH_PLAYER_MUST_USE_DIRECTION_IF_POSSIBLE = "first_maneuver_each_player_must_use_direction_if_possible"
    FIRST_SELF_MANEUVER_EACH_BATTLE_COST = "first_self_maneuver_each_battle_cost"
    FORCE = "force"
    FORMATIONS_CANNOT_MANEUVER_AWAY_FROM_CHOSEN_FRONT = "formations_cannot_maneuver_away_from_chosen_front"
    FRONT_RESOLUTION = "front_resolution"
    GAIN_COMMAND = "gain_command"
    HERO = "hero"
    IMMOBILE = "immobile"
    LATER_MANEUVERS_SAME_DIRECTION_IF_POSSIBLE = "later_maneuvers_same_direction_if_possible"
    LOST_FRONT = "lost_front"
    LOST_FRONTS_PROTECTED = "lost_fronts_protected"
    MANEUVER_COST = "maneuver_cost"
    MINIMUM_COST = "minimum_cost"
    NAME = "name"
    NAMED_ADDITIONAL_STRENGTH_BONUS = "named_additional_strength_bonus"
    NAMED_FORMATIONS_CANNOT_MANEUVER_AWAY = "named_formations_cannot_maneuver_away"
    NARRATIVE = "narrative"
    NEXT_BATTLE_FIRST_ACTION_MUST_BE_MANEUVER_IF_POSSIBLE = "next_battle_first_action_must_be_maneuver_if_possible"
    NEXT_ACTION_EACH_PLAYER_MUST_AFFECT_CHOSEN_FRONT_IF_POSSIBLE = "next_action_each_player_must_affect_chosen_front_if_possible"
    NEXT_ACTION_MUST_AFFECT_CHOSEN_FRONT_IF_POSSIBLE = "next_action_must_affect_chosen_front_if_possible"
    NEXT_TURN_FORCED_MANEUVER_IF_LEGAL = "next_turn_forced_maneuver_if_legal"
    ON_COMPLETION = "on_completion"
    ON_PLAY = "on_play"
    ON_PLAY_ONTO_FORCE = "on_play_onto_force"
    ONGOING = "ongoing"
    PER_PLAYER_FIRST_CARD_IN_FRONT_EACH_BATTLE = "per_player_first_card_in_front_each_battle"
    PERSISTENCE = "persistence"
    PLACEMENT = "placement"
    PREVENT_OPPONENT_CARD_EFFECT_MOVE_INTO_FRONT_FROM_ADJACENT = "prevent_opponent_card_effect_move_into_front_from_adjacent"
    PREVENT_OPPONENT_CARD_EFFECT_MOVEMENT = "prevent_opponent_card_effect_movement"
    PRINTED_ROLE_EFFECT = "printed_role_effect"
    ROLE = "role"
    SCOPE = "scope"
    SECONDARY = "secondary"
    STRATAGEM = "stratagem"
    STRENGTH = "strength"
    STRENGTH_BONUS = "strength_bonus"
    TIMING = "timing"
    TRIGGER = "trigger"
    UNNAMED_FORMATIONS_CAN_MANEUVER = "unnamed_formations_can_maneuver"


class DesignToken(StrEnum):
    ADJACENT_FRIENDLY_FORMATION_CONTAINS_HERO = "adjacent_friendly_formation_contains_hero"
    ADJACENT_FRIENDLY_FORMATION_RETREATS = "adjacent_friendly_formation_retreats"
    ADJACENT_FRIENDLY_NAMED_FORMATION_MANEUVERS_AWAY = "adjacent_friendly_named_formation_maneuvers_away"
    AFTER_RETREAT = "after_retreat"
    AFTER_RETREAT_RESOLVES = "after_retreat_resolves"
    ALL_RESERVES_FORWARD = "all_reserves_forward"
    BATTLE = "battle"
    BATTLE_END_BEFORE_STRENGTH_COMPARISON = "battle_end_before_strength_comparison"
    BATTLE_END_PLAYER_WON_AT_LEAST_THREE_FRONTS = "battle_end_player_won_at_least_three_fronts"
    BATTLE_TURNS_DIRECTION = "battle_turns_direction"
    BOND_IS_OPEN = "bond_is_open"
    BOND_RETURNS_TO_HAND_WHEN_FORCE_DRIVEN_OFF = "bond_returns_to_hand_when_force_driven_off"
    BOTH_PLAYERS = "both_players"
    BREAKTHROUGH = "breakthrough"
    BREAKTHROUGH_IF_OPPONENT_NO_REAR_FORCE = "breakthrough_if_opponent_no_rear_force"
    CAPTURE = "capture"
    CARD_FOR_COMMAND = "card_for_command"
    CATCH_UP_DISCOUNT = "catch_up_discount"
    CHOSEN_DIRECTION = "chosen_direction"
    CHOSEN_FORMATION_STILL_ON_BATTLEFIELD = "chosen_formation_still_on_battlefield"
    CHOSEN_FRONT = "chosen_front"
    CHOSEN_FRONT_INSTEAD_OF_OWN = "chosen_front_instead_of_own"
    CHOSEN_FRONT_NOT_LOST = "chosen_front_not_lost"
    CHOSEN_FRONT_WON = "chosen_front_won"
    CHOSEN_NAMED_FORMATION = "chosen_named_formation"
    CHOSEN_OPPOSING_FORMATION_DOES_NOT_CONTRIBUTE_THIS_RESOLUTION = "chosen_opposing_formation_does_not_contribute_this_resolution"
    COMBINE_TWO_ADJACENT_FRONTS = "combine_two_adjacent_fronts"
    COMPLETION_DISCOUNT = "completion_discount"
    COMPLETION_REFUND = "completion_refund"
    CONTROLLER_COMMAND_LOWER_THAN_OPPONENT = "controller_command_lower_than_opponent"
    CONTROLLER_HAS_FRONT_WITH_NO_FORCE = "controller_has_front_with_no_force"
    DRAW_CARDS = "draw_cards"
    DISCARD_OWN_FORCE_AND_ALL_ATTACHED_CARDS = "discard_own_force_and_all_attached_cards"
    DRIVE_OFF_OPPOSING_FRONTLINE_NAMED_INSTEAD_OF_RETREAT = "drive_off_opposing_frontline_named_instead_of_retreat"
    DRIVE_OFF_SELF_PREVENT_FRONTLINE_RETREAT = "drive_off_self_prevent_frontline_retreat"
    EMPTY_FRONT = "empty_front"
    EMPTY_FRONTLINE_SAME_FRONT = "empty_frontline_same_front"
    ENCIRCLEMENT = "encirclement"
    EVERY_BANNER_TURNED = "every_banner_turned"
    FEIGNED_RETREAT = "feigned_retreat"
    FIRST_CARD_IN_FRONT_EACH_BATTLE_DISCOUNT = "first_card_in_front_each_battle_discount"
    FIRST_FRIENDLY_MANEUVER_INTO_EMPTY_EACH_BATTLE = "first_friendly_maneuver_into_empty_each_battle"
    FIRST_NARRATIVE_EACH_BATTLE_DISCOUNT = "first_narrative_each_battle_discount"
    FIRST_STRIKE = "first_strike"
    FORCE_MOVES_OR_MANEUVERS = "force_moves_or_maneuvers"
    FORMATION_DRIVEN_OFF = "formation_driven_off"
    FREE_MANEUVER_ADJACENT_FRIENDLY_NAMED_FORMATION = "free_maneuver_adjacent_friendly_named_formation"
    FREE_MANEUVER_SELF = "free_maneuver_self"
    FRIENDLY_FORCE_IN_ALL_FOUR_FRONTS = "friendly_force_in_all_four_fronts"
    FRIENDLY_FORMATION_BECOMES_NAMED = "friendly_formation_becomes_named"
    FRIENDLY_NAMED_FORMATION_RETREATS = "friendly_named_formation_retreats"
    FRONT_TIED_AND_EXACTLY_ONE_SIDE_HAS_FRONTLINE_NAMED = "front_tied_and_exactly_one_side_has_frontline_named"
    FRONTLINE_FORCE_DISCOUNT = "frontline_force_discount"
    FRONTLINE_ONLY_COMPARISON = "frontline_only_comparison"
    FRONTLINE_PEOPLE = "frontline_people"
    FRONTLINE_STRENGTH_BONUS = "frontline_strength_bonus"
    FRONTLINE_STRENGTH_BONUS_IF_FORCE_BEHIND = "frontline_strength_bonus_if_force_behind"
    HAS_BOND_AND_NO_NAME = "has_bond_and_no_name"
    HERO_RETINUE = "hero_retinue"
    HIGH_COST_BATTLE_INVESTMENT = "high_cost_battle_investment"
    HIGHER_COMBINED_STRENGTH_WINS_BOTH = "higher_combined_strength_wins_both"
    IGNORE_REAR_FORMATIONS_WHEN_COMPARING_STRENGTH = "ignore_rear_formations_when_comparing_strength"
    INHERITED_BOND = "inherited_bond"
    INTERCEPTION = "interception"
    LINE_BEGUN_TO_MOVE = "line_begun_to_move"
    LOCAL_CATCH_UP_DISCOUNT = "local_catch_up_discount"
    LOSING_FRONTLINE_NAMED_DRIVEN_OFF_INSTEAD_OF_RETREATING = "losing_frontline_named_driven_off_instead_of_retreating"
    MIDDLE_OPPOSING_FRONTLINE_NAMED_DRIVEN_OFF_INSTEAD_OF_RETREATING = "middle_opposing_frontline_named_driven_off_instead_of_retreating"
    MOBILE_PEOPLE = "mobile_people"
    NAME_RETURNS_TO_HAND_WHEN_FORMATION_DRIVEN_OFF = "name_returns_to_hand_when_formation_driven_off"
    NAMED_PEOPLE = "named_people"
    NARRATIVE = "narrative"
    NEXT_MANEUVER_COST_ZERO_THIS_BATTLE = "next_maneuver_cost_zero_this_battle"
    NO_RETREAT_FRONT = "no_retreat_front"
    NO_ROAD_BACK = "no_road_back"
    OPEN_BOND = "open_bond"
    OPEN_BOND_PEOPLE = "open_bond_people"
    OPEN_BOND_TRANSFER = "open_bond_transfer"
    OPPONENT_EFFECT_WOULD_PREVENT_OTHER_FRIENDLY_FORMATION_CONTRIBUTION = "opponent_effect_would_prevent_other_friendly_formation_contribution"
    OPPONENT_HAS_FORCE_IN_BOTH_RANKS_SAME_FRONT = "opponent_has_force_in_both_ranks_same_front"
    OPPONENT_MANEUVERS_INTO_ADJACENT_FRONT = "opponent_maneuvers_into_adjacent_front"
    OPPOSING_FORMATION_BECOMES_NAMED = "opposing_formation_becomes_named"
    OPPOSING_FORMATION_IN_SAME_FRONT_BECOMES_NAMED = "opposing_formation_in_same_front_becomes_named"
    OPPOSING_FORMATION_MANEUVERS_INTO_SAME_FRONT = "opposing_formation_maneuvers_into_same_front"
    OPPOSING_FRONTLINE_FORCE_WITH_LOWER_PRINTED_STRENGTH = "opposing_frontline_force_with_lower_printed_strength"
    OPTIONAL_DRIVE_OFF_SELF_PREVENT_FRONTLINE_NAMED_RETREAT = "optional_drive_off_self_prevent_frontline_named_retreat"
    OPTIONAL_EXTRA_PAYMENT = "optional_extra_payment"
    OPTIONAL_IGNORE_OPPOSING_REAR_STRENGTH = "optional_ignore_opposing_rear_strength"
    OPTIONAL_MOVE_ADJACENT_FRIENDLY_INTO_VACATED_POSITION = "optional_move_adjacent_friendly_into_vacated_position"
    OPTIONAL_MOVE_ADJACENT_FRIENDLY_TO_VACATED_POSITION = "optional_move_adjacent_friendly_to_vacated_position"
    OPTIONAL_MOVE_FORMATION_ADJACENT_EMPTY_POSITION = "optional_move_formation_adjacent_empty_position"
    OPTIONAL_MOVE_INTO_VACATED_POSITION = "optional_move_into_vacated_position"
    OPTIONAL_MOVE_NAME_TO_ADJACENT_FRIENDLY_FORCE_WITH_BOND_NO_NAME = "optional_move_name_to_adjacent_friendly_force_with_bond_no_name"
    OPTIONAL_MOVE_ONE_MORE_FRONT_IF_EMPTY = "optional_move_one_more_front_if_empty"
    OPTIONAL_MOVE_THIS_BOND_TO_ADJACENT_FRIENDLY_FORCE_WITHOUT_BOND = "optional_move_this_bond_to_adjacent_friendly_force_without_bond"
    OPTIONAL_SIDEWAYS_REAR_MOVE = "optional_sideways_rear_move"
    OPTIONAL_SWAP_ADJACENT_FRIENDLY_FORMATION = "optional_swap_adjacent_friendly_formation"
    OPTIONAL_SWAP_FRIENDLY_FRONTLINE_AND_REAR_FORMATIONS_ONE_FRONT = "optional_swap_friendly_frontline_and_rear_formations_one_front"
    OPTIONAL_SWAP_TWO_ADJACENT_FRIENDLY_FORMATIONS_EXCLUDING_SELF = "optional_swap_two_adjacent_friendly_formations_excluding_self"
    OPTIONAL_TAKE_ADJACENT_OPEN_BOND = "optional_take_adjacent_open_bond"
    OPTIONAL_TAKE_ADJACENT_PREPARED_BOND_OR_NAME = "optional_take_adjacent_prepared_bond_or_name"
    OPTIONAL_ZERO_COST_FRIENDLY_NAMED_MANEUVER = "optional_zero_cost_friendly_named_maneuver"
    OPTIONAL_ZERO_COST_MANEUVER = "optional_zero_cost_maneuver"
    OPTIONAL_ZERO_COST_MANEUVER_EVEN_IF_UNNAMED = "optional_zero_cost_maneuver_even_if_unnamed"
    OPTIONAL_ZERO_COST_MANEUVER_SWAPPED_FORMATION = "optional_zero_cost_maneuver_swapped_formation"
    OPTIONAL_ZERO_COST_MANEUVER_THAT_FORMATION = "optional_zero_cost_maneuver_that_formation"
    OPTIONAL_ZERO_COST_MANEUVER_THIS_FORMATION = "optional_zero_cost_maneuver_this_formation"
    OPTIONAL_ZERO_COST_OTHER_FRIENDLY_NAMED_MANEUVER = "optional_zero_cost_other_friendly_named_maneuver"
    OWN_FRONT_WINS_AND_OPPOSING_FRONTLINE_NAMED_RETREATS = "own_front_wins_and_opposing_frontline_named_retreats"
    OWN_OR_ADJACENT_FRONT = "own_or_adjacent_front"
    PLAYED_ON_FORCE_WITH_BOND = "played_on_force_with_bond"
    PLAYER_WHO_WON_AT_LEAST_THREE_FRONTS = "player_who_won_at_least_three_fronts"
    POSITION_HAS_PREPARED_BOND_OR_NAME = "position_has_prepared_bond_or_name"
    PREPARED_POSITION = "prepared_position"
    PROTECT_LOST_FRONT_HERE = "protect_lost_front_here"
    PROTECT_LOST_FRONTS = "protect_lost_fronts"
    REAR_REBUILD_COST_REDUCTION = "rear_rebuild_cost_reduction"
    REAR_STRENGTH_BONUS = "rear_strength_bonus"
    REAR_STRENGTH_BONUS_IF_FORCE_AHEAD = "rear_strength_bonus_if_force_ahead"
    REFUSE_FLANK = "refuse_flank"
    REGAIN_COMMAND_FROM_NARRATIVE = "regain_command_from_narrative"
    RETREAT_COMMAND_COMPENSATION = "retreat_command_compensation"
    RETREAT_SIDEWAYS = "retreat_sideways"
    RETURN_HERO_TO_HAND_IF_DRIVEN_OFF = "return_hero_to_hand_if_driven_off"
    RETURN_ONE_BOND_FROM_DISCARD_TO_HAND = "return_one_bond_from_discard_to_hand"
    RETURN_ONE_NARRATIVE_FROM_DISCARD_TO_HAND = "return_one_narrative_from_discard_to_hand"
    RETURN_RETREATING_FORMATION_BOND_TO_OWNER_HAND = "return_retreating_formation_bond_to_owner_hand"
    SACRIFICE = "sacrifice"
    SKIRMISH = "skirmish"
    START_BATTLE_REPOSITION = "start_battle_reposition"
    STEADFAST_PEOPLE = "steadfast_people"
    SUCCESSION = "succession"
    SUPPORT_FORCE_AHEAD_STRENGTH_BONUS = "support_force_ahead_strength_bonus"
    SUPPRESS_OPPOSING_REAR_FORCE_FOR_RESOLUTION = "suppress_opposing_rear_force_for_resolution"
    TARGET_DOES_NOT_CONTRIBUTE_THIS_RESOLUTION = "target_does_not_contribute_this_resolution"
    THAT_SIDE_WINS_FRONT = "that_side_wins_front"
    THIS_FORMATION = "this_formation"
    THIS_FORMATION_DOES_NOT_CONTRIBUTE_INSTEAD = "this_formation_does_not_contribute_instead"
    THIS_FRONT = "this_front"
    TIE_CONTROL = "tie_control"
    UNTIL_EACH_PLAYER_COMPLETES_NEXT_ACTION_OR_BATTLE_ENDS = "until_each_player_completes_next_action_or_battle_ends"
    VANILLA = "vanilla"
    VOLUNTARY_RETREAT_IF_REAR_EMPTY = "voluntary_retreat_if_rear_empty"
    WHEEL_LINE = "wheel_line"
    WIDE_LINE = "wide_line"
    WIN_FRONT_AND_OPPONENT_REAR_HAS_NO_FORCE = "win_front_and_opponent_rear_has_no_force"
    WIN_MIDDLE_AND_BOTH_ADJACENT_FRONTS = "win_middle_and_both_adjacent_fronts"


CARD_TYPES = frozenset(item.value for item in CardType)
FORCE_ROLES = frozenset(item.value for item in ForceRole)
NARRATIVE_FORMS = frozenset(item.value for item in NarrativeForm)
RULE_BLOCK_KINDS = frozenset(item.value for item in RuleBlockKind)
DIRECTIONS = frozenset(item.value for item in Direction)
