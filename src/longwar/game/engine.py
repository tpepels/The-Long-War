from __future__ import annotations

import random
from collections import Counter
from itertools import combinations
from typing import Any, Iterable

from ..cards import card_index, load_card_file
from .actions import (
    Action,
    BoardTarget,
    ChooseFirst,
    Draw,
    Pass,
    PlayLink,
    PlayName,
    PlayPlot,
    PlayScheme,
    PlaySubject,
    SetStratagem,
)
from .model import (
    Front,
    GameState,
    Phase,
    PlayerState,
    Position,
    Rank,
    SchemeState,
    Slot,
    StratagemState,
)


class IllegalAction(ValueError):
    pass


class InvalidDeck(ValueError):
    pass


LINE_DEFENSE_BONUS = 1

ROLE_POSITION_RULES = {
    "swordsman": {"front_bonus": 1},
    "spearman": {"front_with_rear_bonus": 1},
    "archer": {"rear_with_front_bonus": 2},
    "ship": {"rear_bonus": 1},
    "stronghold": {"rear_bonus": 1},
}

# Search visits these tiny collections tens of thousands of times. Build the
# immutable Position objects once rather than recreating them inside every
# legal-action and evaluation pass.
FRONTS = tuple(Front)
FRONTLINE_POSITIONS = tuple(Position(front, Rank.FRONT) for front in FRONTS)
REAR_POSITIONS = tuple(Position(front, Rank.REAR) for front in FRONTS)
POSITIONS_BY_FRONT = tuple(
    (FRONTLINE_POSITIONS[int(front)], REAR_POSITIONS[int(front)])
    for front in FRONTS
)
ALL_POSITIONS = tuple(
    position
    for pair in POSITIONS_BY_FRONT
    for position in pair
)
SHUFFLE_MULTIPLIER = 1_664_525
SHUFFLE_INCREMENT = 1_013_904_223
SHUFFLE_MASK = 0xFFFF_FFFF


def _shuffle_cards(cards: list[str], seed: int) -> int:
    """Deterministically reshuffle cards while keeping search clones reproducible."""
    seed &= SHUFFLE_MASK
    for index in range(len(cards) - 1, 0, -1):
        seed = (
            SHUFFLE_MULTIPLIER * seed + SHUFFLE_INCREMENT
        ) & SHUFFLE_MASK
        other = seed % (index + 1)
        cards[index], cards[other] = cards[other], cards[index]
    return seed


ADJACENT_POSITIONS = {
    position: tuple(
        candidate
        for candidate in (
            (
                Position(Front(int(position.front) - 1), position.rank)
                if int(position.front) > 0
                else None
            ),
            (
                Position(Front(int(position.front) + 1), position.rank)
                if int(position.front) < len(FRONTS) - 1
                else None
            ),
        )
        if candidate is not None
    )
    for position in ALL_POSITIONS
}


def all_positions() -> tuple[Position, ...]:
    return ALL_POSITIONS


class GameEngine:
    def __init__(
        self,
        card_data: dict[str, Any],
        *,
        opening_hand_size: int = 10,
        draw_action_enabled: bool = True,
        completion_draw_names: Iterable[str] = (),
        deck_size: int = 30,
        recycle_between_battles: bool = True,
    ):
        if deck_size < 1:
            raise ValueError("deck_size must be positive")
        if not 1 <= opening_hand_size <= deck_size:
            raise ValueError("opening_hand_size must be between 1 and deck_size")
        self.card_data = card_data
        self.cards = card_index(card_data)
        self.opening_hand_size = opening_hand_size
        self.draw_action_enabled = draw_action_enabled
        self.completion_draw_names = frozenset(completion_draw_names)
        self.deck_size = deck_size
        self.recycle_between_battles = recycle_between_battles
        invalid_completion_names = [
            card_id
            for card_id in self.completion_draw_names
            if card_id not in self.cards or self.cards[card_id]["type"] != "name"
        ]
        if invalid_completion_names:
            raise ValueError(
                "completion_draw_names must contain only Name ids: "
                + ", ".join(sorted(invalid_completion_names))
            )

        # Flatten immutable dispatch metadata used at every search node.
        self._card_types = {
            card_id: card["type"]
            for card_id, card in self.cards.items()
        }
        self._subject_required_rank = {
            card_id: card.get("rules", {}).get("placement", {}).get("rank")
            for card_id, card in self.cards.items()
            if card["type"] == "subject"
        }
        self._name_attach_effect = {
            card_id: card.get("rules", {}).get("on_name_attached")
            for card_id, card in self.cards.items()
            if card["type"] == "name"
        }
        self._plot_effects = {
            card_id: card.get("rules", {}).get("effect")
            for card_id, card in self.cards.items()
            if card["type"] == "plot"
        }
        self._veiled_story_ids = {
            card_id
            for card_id, card in self.cards.items()
            if card["type"] == "plot" and card.get("veiled", False)
        }

        # Strength-related runtime metadata. These tuples mirror the validated
        # card data but avoid nested dict decoding inside every search leaf.
        self._subject_strength: dict[str, int] = {}
        self._subject_role: dict[str, str] = {}
        self._subject_role_values: dict[str, tuple[int, int, int, int]] = {}
        self._subject_conditions: dict[
            str,
            tuple[tuple[int, str | None, int | None, bool], ...],
        ] = {}
        self._subject_adjacent_aura: dict[str, int] = {}
        self._subject_aura_rank: dict[str, str | None] = {}

        self._link_runtime: dict[
            str,
            tuple[int, int, int, int, int, bool],
        ] = {}
        self._name_runtime: dict[str, tuple[int, str | None, int]] = {}
        self._scheme_front_bonus: dict[str, int] = {}
        self._stratagem_continuous: dict[
            str,
            tuple[
                dict[str, int],
                dict[str, int],
                dict[str, int],
                int,
                int,
                bool,
            ],
        ] = {}

        for card_id, card in self.cards.items():
            card_type = card["type"]
            rules = card.get("rules", {})
            if card_type == "subject":
                role = card["role"]
                role_rules = ROLE_POSITION_RULES.get(role, {})
                self._subject_strength[card_id] = int(card["strength"])
                self._subject_role[card_id] = role
                self._subject_role_values[card_id] = (
                    int(role_rules.get("front_bonus", 0)),
                    int(role_rules.get("front_with_rear_bonus", 0)),
                    int(role_rules.get("rear_bonus", 0)),
                    int(role_rules.get("rear_with_front_bonus", 0)),
                )
                self._subject_conditions[card_id] = tuple(
                    (
                        int(modifier["amount"]),
                        modifier.get("when", {}).get("rank"),
                        (
                            int(modifier.get("when", {})["own_discard_at_least"])
                            if "own_discard_at_least" in modifier.get("when", {})
                            else None
                        ),
                        bool(
                            modifier.get("when", {}).get(
                                "adjacent_subject_has_name",
                                False,
                            )
                        ),
                    )
                    for modifier in rules.get("strength_modifiers", [])
                )
                self._subject_adjacent_aura[card_id] = int(
                    rules.get("adjacent_strength_aura", 0)
                )
                self._subject_aura_rank[card_id] = rules.get(
                    "aura_requires_rank"
                )

            elif card_type == "link":
                discard_bonus = rules.get("discard_strength_bonus") or {}
                self._link_runtime[card_id] = (
                    int(rules.get("strength_bonus", 0)),
                    int(rules.get("named_strength_bonus", 0)),
                    int(discard_bonus.get("per_card", 0)),
                    int(discard_bonus.get("maximum", 0)),
                    int(rules.get("opposing_front_modifier", 0)),
                    bool(rules.get("protect_subject_from_opponent_plot", False)),
                )

            elif card_type == "name":
                rank_bonus = rules.get("rank_strength_bonus") or {}
                self._name_runtime[card_id] = (
                    int(card["strength"]),
                    rank_bonus.get("rank"),
                    int(rank_bonus.get("amount", 0)),
                )

            elif card_type == "plot" and card.get("veiled", False):
                scheme = rules.get("scheme", {})
                self._scheme_front_bonus[card_id] = int(
                    scheme.get("face_down_front_bonus", 0)
                )

            elif card_type == "stratagem":
                continuous = rules.get("stratagem", {}).get("continuous", {})
                self._stratagem_continuous[card_id] = (
                    dict(continuous.get("role_strength_modifiers", {})),
                    dict(continuous.get("rank_strength_modifiers", {})),
                    dict(
                        continuous.get(
                            "controller_rank_strength_modifiers",
                            {},
                        )
                    ),
                    int(continuous.get("named_subject_modifier", 0)),
                    int(continuous.get("unnamed_subject_modifier", 0)),
                    bool(continuous.get("disable_line_defense", False)),
                )

        self._pass_action = Pass()
        self._draw_action = Draw()
        self._choose_first_actions = (ChooseFirst(0), ChooseFirst(1))
        self._subject_action_templates = {
            card_id: tuple(
                PlaySubject(card_id, position)
                for position in ALL_POSITIONS
                if required_rank is None or position.rank.value == required_rank
            )
            for card_id, required_rank in self._subject_required_rank.items()
        }
        self._link_action_templates = {
            card_id: tuple(
                PlayLink(card_id, position)
                for position in ALL_POSITIONS
            )
            for card_id, card_type in self._card_types.items()
            if card_type == "link"
        }
        self._name_action_templates = {}
        for card_id in self._name_attach_effect:
            actions: list[PlayName] = []
            move_optional = self._name_attach_effect[card_id] == "move_adjacent_optional"
            for position in ALL_POSITIONS:
                actions.append(PlayName(card_id, position, None))
                if move_optional:
                    actions.extend(
                        PlayName(card_id, position, destination)
                        for destination in ADJACENT_POSITIONS[position]
                    )
            self._name_action_templates[card_id] = tuple(actions)

        self._scheme_action_templates = {
            card_id: tuple(PlayScheme(card_id, front) for front in FRONTS)
            for card_id in self._veiled_story_ids
        }
        self._stratagem_actions = {
            card_id: SetStratagem(card_id)
            for card_id, card_type in self._card_types.items()
            if card_type == "stratagem"
        }

        self._plot_target_action_templates: dict[
            tuple[str, int],
            tuple[PlayPlot, ...],
        ] = {}
        self._plot_move_action_templates: dict[
            tuple[str, int],
            tuple[PlayPlot, ...],
        ] = {}
        for card_id, effect in self._plot_effects.items():
            if card_id in self._veiled_story_ids:
                continue
            for actor in (0, 1):
                if effect in {"discredit_subject", "return_name_or_weaken"}:
                    target_player = 1 - actor
                    self._plot_target_action_templates[(card_id, actor)] = tuple(
                        PlayPlot(
                            card_id,
                            (BoardTarget(target_player, position),),
                        )
                        for position in ALL_POSITIONS
                    )
                elif effect == "move_subject":
                    self._plot_move_action_templates[(card_id, actor)] = tuple(
                        PlayPlot(
                            card_id,
                            (
                                BoardTarget(actor, source),
                                BoardTarget(actor, destination),
                            ),
                        )
                        for source in ALL_POSITIONS
                        for destination in ALL_POSITIONS
                        if destination != source
                    )

    @classmethod
    def from_file(cls, path: str) -> "GameEngine":
        return cls(load_card_file(path))

    def validate_deck(self, deck: list[str]) -> None:
        if len(deck) != self.deck_size:
            raise InvalidDeck(
                f"A deck must contain exactly {self.deck_size} cards, got {len(deck)}"
            )

        counts = Counter(deck)
        hero_count = 0
        for card_id, count in counts.items():
            if card_id not in self.cards:
                raise InvalidDeck(f"Unknown card: {card_id}")
            card = self.cards[card_id]
            maximum = 1 if card["unique"] else 2
            if count > maximum:
                raise InvalidDeck(
                    f"{card['title']} appears {count} times; maximum is {maximum}"
                )
            if card.get("hero", False):
                hero_count += count

        if hero_count != 1:
            raise InvalidDeck(
                f"A deck must contain exactly one Hero, got {hero_count}"
            )

    def new_game(
        self,
        deck_a: list[str],
        deck_b: list[str],
        *,
        seed: int = 0,
        first_player: int | None = None,
        mulligan_indices: tuple[tuple[int, ...], tuple[int, ...]] = ((), ()),
        opening_bonus: bool = True,
    ) -> GameState:
        self.validate_deck(deck_a)
        self.validate_deck(deck_b)
        return self._new_game_with_rng(
            deck_a,
            deck_b,
            rng=random.Random(seed),
            shuffle_seed=(seed ^ 0x9E37_79B9) & SHUFFLE_MASK,
            first_player=first_player,
            mulligan_indices=mulligan_indices,
            opening_bonus=opening_bonus,
        )

    def _new_game_with_rng(
        self,
        deck_a: list[str],
        deck_b: list[str],
        *,
        rng: random.Random,
        shuffle_seed: int,
        first_player: int | None = None,
        mulligan_indices: tuple[tuple[int, ...], tuple[int, ...]] = ((), ()),
        opening_bonus: bool = True,
    ) -> GameState:
        """Construct a game from already-validated decks with a reusable RNG."""
        decks = [list(deck_a), list(deck_b)]
        rng.shuffle(decks[0])
        rng.shuffle(decks[1])

        players = [
            PlayerState(deck=decks[player], hand=[])
            for player in range(2)
        ]
        state = GameState(players=players, shuffle_seed=shuffle_seed)

        for player in range(2):
            self._draw(state, player, self.opening_hand_size)
            self._apply_mulligan(
                state,
                player,
                mulligan_indices[player],
                rng,
            )

        state.active_player = (
            rng.randrange(2)
            if first_player is None
            else first_player
        )
        # Acting first exposes the first commitment. Battle I compensates that
        # information disadvantage with one additional opening card. Preview
        # states may opt out because mulligans happen before this card is drawn.
        if opening_bonus:
            self._draw(state, state.active_player, 1)
        return state

    def _apply_mulligan(
        self,
        state: GameState,
        player: int,
        indices: tuple[int, ...],
        rng: random.Random,
    ) -> None:
        if len(indices) > 2 or len(set(indices)) != len(indices):
            raise ValueError("A mulligan may contain at most two distinct hand indices")
        hand = state.players[player].hand
        if any(index < 0 or index >= len(hand) for index in indices):
            raise ValueError("Mulligan index outside opening hand")

        returned = [hand[index] for index in sorted(indices)]
        for index in sorted(indices, reverse=True):
            del hand[index]
        state.players[player].deck.extend(returned)
        rng.shuffle(state.players[player].deck)
        self._draw(state, player, len(returned))

    def legal_actions(self, state: GameState) -> list[Action]:
        if state.phase is Phase.COMPLETE:
            return []

        if state.phase is Phase.CHOOSE_FIRST:
            if state.active_player != state.chooser:
                raise RuntimeError("Chooser must be the active player")
            return list(self._choose_first_actions)

        player = state.active_player
        if state.players[player].passed:
            raise RuntimeError("A passed player cannot become active")

        actions: list[Action] = [self._pass_action]
        if (
            self.draw_action_enabled
            and not state.draw_used[player]
            and state.players[player].deck
        ):
            actions.append(self._draw_action)

        for card_id in dict.fromkeys(state.players[player].hand):
            card_type = self._card_types[card_id]

            if card_type == "subject":
                actions.extend(self._subject_actions(state, player, card_id))
            elif card_type == "link":
                actions.extend(self._link_actions(state, player, card_id))
            elif card_type == "name":
                actions.extend(self._name_actions(state, player, card_id))
            elif card_type == "plot":
                if card_id in self._veiled_story_ids:
                    actions.extend(self._scheme_actions(state, player, card_id))
                elif not self._immediate_story_locked(state, player):
                    actions.extend(self._plot_actions(state, player, card_id))
            elif card_type == "stratagem":
                if (
                    not state.stratagem_used[player]
                    and state.stratagem(player) is None
                ):
                    actions.append(self._stratagem_actions[card_id])

        return actions

    def apply(
        self,
        state: GameState,
        action: Action,
        *,
        validate: bool = True,
    ) -> None:
        if validate:
            legal = self.legal_actions(state)
            if action not in legal:
                raise IllegalAction(f"Illegal action: {action!r}")

        if isinstance(action, ChooseFirst):
            state.active_player = action.player
            state.chooser = None
            state.phase = Phase.BATTLE
            state.turn_number += 1
            return

        actor = state.active_player

        if isinstance(action, Pass):
            self._pass(state, actor)
            return

        if isinstance(action, Draw):
            if not self.draw_action_enabled:
                raise IllegalAction("Draw is disabled for this rules variant")
            self._draw(state, actor, 1)
            state.draw_used[actor] = True
            self._advance_turn(state)
            state.turn_number += 1
            return

        completion_before = (
            self._complete_formation_counts(state, actor)
            if self.completion_draw_names
            and isinstance(action, (PlaySubject, PlayLink, PlayName))
            else None
        )

        if isinstance(action, PlaySubject):
            self._take_from_hand(state, actor, action.card_id)
            slot = state.slot(actor, action.position)
            slot.subject = action.card_id
            self._resolve_triggered_schemes(
                state,
                actor=actor,
                event="opponent_plays_subject",
                front=action.position.front,
                position=action.position,
            )
            self._resolve_stratagem_event(
                state,
                event="subject_played",
                actor=actor,
                card_id=action.card_id,
                position=action.position,
            )

        elif isinstance(action, PlayLink):
            self._take_from_hand(state, actor, action.card_id)
            slot = state.slot(actor, action.position)
            slot.link = action.card_id
            if slot.subject is not None:
                subject = self.cards[slot.subject]
                bonus = subject.get("rules", {}).get("on_link_attached", {}).get(
                    "temporary_strength", 0
                )
                slot.temporary_strength += int(bonus)
            self._resolve_triggered_schemes(
                state,
                actor=actor,
                event="opponent_plays_link",
                front=action.position.front,
                position=action.position,
            )

        elif isinstance(action, PlayName):
            self._take_from_hand(state, actor, action.card_id)
            slot = state.slot(actor, action.position)
            slot.name = action.card_id
            self._on_name_attached(
                state,
                actor,
                action.position,
                move_to=action.move_to,
            )
            self._resolve_stratagem_event(
                state,
                event="name_played",
                actor=actor,
                card_id=action.card_id,
                position=action.move_to or action.position,
            )

        elif isinstance(action, PlayPlot):
            self._take_from_hand(state, actor, action.card_id)
            plot_targets = tuple(action.targets)
            cancelled = self._resolve_pre_story_stratagem(state, actor=actor)
            if not cancelled:
                self._resolve_plot(state, actor, action)
                self._resolve_plot_target_schemes(
                    state,
                    actor=actor,
                    targets=plot_targets,
                )
            self._discard_card(state, actor, action.card_id)

        elif isinstance(action, PlayScheme):
            self._take_from_hand(
                state,
                actor,
                action.card_id,
                hidden_kind="scheme",
            )
            state.schemes[actor][int(action.front)] = SchemeState(action.card_id)

        elif isinstance(action, SetStratagem):
            self._take_from_hand(
                state,
                actor,
                action.card_id,
                hidden_kind="stratagem",
            )
            state.stratagems[actor] = StratagemState(action.card_id)
            state.stratagem_used[actor] = True
            return

        else:
            raise TypeError(f"Unhandled action type: {type(action)!r}")

        if completion_before is not None:
            self._reward_new_completion_draws(
                state,
                actor,
                completion_before,
            )

        self._advance_turn(state)
        state.turn_number += 1

    def position_strength(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> int:
        slot = state.slot(player, position)
        if slot.subject is None:
            return 0

        subject = self.cards[slot.subject]
        value = int(subject["strength"]) + slot.temporary_strength

        if position.rank is Rank.FRONT and not self._line_defense_disabled(state):
            value += LINE_DEFENSE_BONUS

        value += self._role_strength_bonus(
            state,
            player,
            position,
            subject,
        )
        value += self._support_strength_bonus(
            state,
            player,
            position,
        )
        value += self._adjacent_aura_bonus(
            state,
            player,
            position,
        )

        for modifier in subject.get("rules", {}).get("strength_modifiers", []):
            if self._condition_matches(state, player, position, modifier.get("when", {})):
                value += int(modifier["amount"])

        link_rules: dict[str, Any] = {}
        if slot.link is not None:
            link = self.cards[slot.link]
            link_rules = link.get("rules", {})
            value += int(link_rules.get("strength_bonus", 0))

        if slot.name is not None:
            name = self.cards[slot.name]
            name_rules = name.get("rules", {})
            value += int(name["strength"])

            rank_bonus = name_rules.get("rank_strength_bonus")
            if (
                rank_bonus
                and position.rank.value == rank_bonus.get("rank")
            ):
                value += int(rank_bonus.get("amount", 0))

            if slot.link is not None:
                value += int(link_rules.get("named_strength_bonus", 0))
                discard_bonus = link_rules.get("discard_strength_bonus")
                if discard_bonus:
                    per_card = int(discard_bonus.get("per_card", 1))
                    maximum = int(discard_bonus.get("maximum", 0))
                    value += min(
                        state.discarded_this_battle[player] * per_card,
                        maximum,
                    )

        value += self._stratagem_strength_modifier(
            state,
            player,
            position,
            subject,
            named=slot.name is not None,
        )
        return max(0, value)

    def name_attachment_strength_gain(
        self,
        state: GameState,
        player: int,
        position: Position,
        name_id: str,
    ) -> int:
        """Exact Strength gain from hypothetically attaching a Name."""
        slot = state.slot(player, position)
        if slot.subject is None or slot.name is not None:
            return 0

        continuous_rules = []
        line_defense_disabled = False
        for controller in range(2):
            stratagem = state.stratagem(controller)
            if stratagem is None or not stratagem.revealed:
                continue
            runtime = self._stratagem_continuous[stratagem.card_id]
            continuous_rules.append((controller, runtime))
            if runtime[5]:
                line_defense_disabled = True

        before = self._position_strength_search(
            state,
            player,
            position,
            continuous_rules,
            line_defense_disabled,
        )
        original_name = slot.name
        try:
            slot.name = name_id
            after = self._position_strength_search(
                state,
                player,
                position,
                continuous_rules,
                line_defense_disabled,
            )
        finally:
            slot.name = original_name
        return after - before

    def front_strength_matrix(
        self,
        state: GameState,
    ) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """Compute all six Front totals with precompiled rule metadata."""
        continuous_rules = []
        line_defense_disabled = False
        for controller in range(2):
            stratagem = state.stratagem(controller)
            if stratagem is None or not stratagem.revealed:
                continue
            runtime = self._stratagem_continuous[stratagem.card_id]
            continuous_rules.append((controller, runtime))
            if runtime[5]:
                line_defense_disabled = True

        totals = [[0, 0, 0], [0, 0, 0]]
        for player in range(2):
            opponent = 1 - player
            for front in FRONTS:
                front_position, rear_position = POSITIONS_BY_FRONT[int(front)]
                value = self._position_strength_search(
                    state,
                    player,
                    front_position,
                    continuous_rules,
                    line_defense_disabled,
                )
                value += self._position_strength_search(
                    state,
                    player,
                    rear_position,
                    continuous_rules,
                    line_defense_disabled,
                )

                scheme = state.scheme(player, front)
                if scheme is not None and not scheme.revealed:
                    value += self._scheme_front_bonus[scheme.card_id]

                for enemy_position in POSITIONS_BY_FRONT[int(front)]:
                    enemy_slot = state.slot(opponent, enemy_position)
                    if enemy_slot.complete:
                        value += self._link_runtime[enemy_slot.link][4]

                totals[player][int(front)] = value

        return (
            (totals[0][0], totals[0][1], totals[0][2]),
            (totals[1][0], totals[1][1], totals[1][2]),
        )

    def front_margins(
        self,
        state: GameState,
        player: int,
    ) -> tuple[int, int, int]:
        totals = self.front_strength_matrix(state)
        opponent = 1 - player
        return (
            totals[player][0] - totals[opponent][0],
            totals[player][1] - totals[opponent][1],
            totals[player][2] - totals[opponent][2],
        )

    def _position_strength_search(
        self,
        state: GameState,
        player: int,
        position: Position,
        continuous_rules: list[tuple[int, Any]],
        line_defense_disabled: bool,
    ) -> int:
        slot = state.slot(player, position)
        subject_id = slot.subject
        if subject_id is None:
            return 0

        value = self._subject_strength[subject_id] + slot.temporary_strength
        rank_value = position.rank.value
        is_front = position.rank is Rank.FRONT

        if is_front and not line_defense_disabled:
            value += LINE_DEFENSE_BONUS

        (
            front_bonus,
            front_with_rear_bonus,
            rear_bonus,
            rear_with_front_bonus,
        ) = self._subject_role_values[subject_id]
        if is_front:
            value += front_bonus
            if front_with_rear_bonus:
                rear = state.slot(player, REAR_POSITIONS[int(position.front)])
                if rear.subject is not None:
                    value += front_with_rear_bonus
        else:
            value += rear_bonus
            if rear_with_front_bonus:
                frontline = state.slot(
                    player,
                    FRONTLINE_POSITIONS[int(position.front)],
                )
                if frontline.subject is not None:
                    value += rear_with_front_bonus

        if is_front:
            rear = state.slot(player, REAR_POSITIONS[int(position.front)])
            if (
                rear.subject is not None
                and self._subject_role[rear.subject] == "healer"
            ):
                value += 2

        for adjacent in ADJACENT_POSITIONS[position]:
            adjacent_subject = state.slot(player, adjacent).subject
            if adjacent_subject is None:
                continue
            aura = self._subject_adjacent_aura[adjacent_subject]
            if not aura:
                continue
            required_rank = self._subject_aura_rank[adjacent_subject]
            if required_rank is None or adjacent.rank.value == required_rank:
                value += aura

        for (
            amount,
            required_rank,
            discard_at_least,
            adjacent_subject_has_name,
        ) in self._subject_conditions[subject_id]:
            if required_rank is not None and rank_value != required_rank:
                continue
            if (
                discard_at_least is not None
                and len(state.players[player].discard) < discard_at_least
            ):
                continue
            if adjacent_subject_has_name and not any(
                state.slot(player, adjacent).subject is not None
                and state.slot(player, adjacent).name is not None
                for adjacent in ADJACENT_POSITIONS[position]
            ):
                continue
            value += amount

        named = slot.name is not None
        if slot.link is not None:
            (
                base_bonus,
                named_bonus,
                discard_per_card,
                discard_maximum,
                _opposing_modifier,
                _protected,
            ) = self._link_runtime[slot.link]
            value += base_bonus
            if named:
                value += named_bonus
                if discard_per_card:
                    value += min(
                        state.discarded_this_battle[player] * discard_per_card,
                        discard_maximum,
                    )

        if named:
            name_strength, bonus_rank, rank_bonus = self._name_runtime[slot.name]
            value += name_strength
            if bonus_rank is not None and rank_value == bonus_rank:
                value += rank_bonus

        role = self._subject_role[subject_id]
        for controller, runtime in continuous_rules:
            (
                role_modifiers,
                rank_modifiers,
                controller_rank_modifiers,
                named_modifier,
                unnamed_modifier,
                _disable_line_defense,
            ) = runtime
            value += int(role_modifiers.get(role, 0))
            value += int(rank_modifiers.get(rank_value, 0))
            if controller == player:
                value += int(controller_rank_modifiers.get(rank_value, 0))
            value += named_modifier if named else unnamed_modifier

        return max(0, value)

    def front_strength(self, state: GameState, player: int, front: Front) -> int:
        front_position, rear_position = POSITIONS_BY_FRONT[int(front)]
        value = (
            self.position_strength(state, player, front_position)
            + self.position_strength(state, player, rear_position)
        )

        scheme = state.scheme(player, front)
        if scheme is not None and not scheme.revealed:
            scheme_rules = self.cards[scheme.card_id].get("rules", {}).get("scheme", {})
            value += int(scheme_rules.get("face_down_front_bonus", 0))

        opponent = 1 - player
        for enemy_position in POSITIONS_BY_FRONT[int(front)]:
            enemy_slot = state.slot(opponent, enemy_position)
            if not enemy_slot.complete:
                continue
            enemy_link = self.cards[enemy_slot.link]
            value += int(
                enemy_link.get("rules", {}).get("opposing_front_modifier", 0)
            )

        return value

    def _revealed_stratagem_rules(
        self,
        state: GameState,
    ) -> Iterable[tuple[int, dict[str, Any]]]:
        for controller in range(2):
            stratagem = state.stratagem(controller)
            if stratagem is None or not stratagem.revealed:
                continue
            rules = self.cards[stratagem.card_id].get("rules", {}).get(
                "stratagem", {}
            )
            yield controller, rules

    def _line_defense_disabled(self, state: GameState) -> bool:
        return any(
            bool(rules.get("continuous", {}).get("disable_line_defense"))
            for _, rules in self._revealed_stratagem_rules(state)
        )

    def _stratagem_strength_modifier(
        self,
        state: GameState,
        player: int,
        position: Position,
        subject: dict[str, Any],
        *,
        named: bool,
    ) -> int:
        value = 0
        role = subject.get("role")
        rank = position.rank.value
        for controller, rules in self._revealed_stratagem_rules(state):
            continuous = rules.get("continuous", {})
            value += int(
                continuous.get("role_strength_modifiers", {}).get(role, 0)
            )
            value += int(
                continuous.get("rank_strength_modifiers", {}).get(rank, 0)
            )
            if controller == player:
                value += int(
                    continuous.get(
                        "controller_rank_strength_modifiers", {}
                    ).get(rank, 0)
                )
            if named:
                value += int(continuous.get("named_subject_modifier", 0))
            else:
                value += int(continuous.get("unnamed_subject_modifier", 0))
        return value

    def _role_strength_bonus(
        self,
        state: GameState,
        player: int,
        position: Position,
        subject: dict[str, Any],
    ) -> int:
        role = subject.get("role")
        rules = ROLE_POSITION_RULES.get(role, {})
        value = 0

        if position.rank is Rank.FRONT:
            value += int(rules.get("front_bonus", 0))
            if rules.get("front_with_rear_bonus"):
                rear = state.slot(player, REAR_POSITIONS[int(position.front)])
                if rear.subject is not None:
                    value += int(rules["front_with_rear_bonus"])
        else:
            value += int(rules.get("rear_bonus", 0))
            if rules.get("rear_with_front_bonus"):
                frontline = state.slot(
                    player,
                    FRONTLINE_POSITIONS[int(position.front)],
                )
                if frontline.subject is not None:
                    value += int(rules["rear_with_front_bonus"])

        return value

    def _support_strength_bonus(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> int:
        if position.rank is not Rank.FRONT:
            return 0

        rear = state.slot(player, REAR_POSITIONS[int(position.front)])
        if rear.subject is None:
            return 0

        supporter = self.cards[rear.subject]
        if supporter.get("role") == "healer":
            return 2
        return 0

    def _adjacent_aura_bonus(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> int:
        value = 0
        for adjacent in self._adjacent_positions(position):
            slot = state.slot(player, adjacent)
            if slot.subject is None:
                continue
            source = self.cards[slot.subject]
            aura = int(source.get("rules", {}).get("adjacent_strength_aura", 0))
            if not aura:
                continue
            required_rank = source.get("rules", {}).get("aura_requires_rank")
            if required_rank is not None and adjacent.rank.value != required_rank:
                continue
            value += aura
        return value

    def _condition_matches(
        self,
        state: GameState,
        player: int,
        position: Position,
        condition: dict[str, Any],
    ) -> bool:
        rank = condition.get("rank")
        if rank is not None and position.rank.value != rank:
            return False

        discard_at_least = condition.get("own_discard_at_least")
        if (
            discard_at_least is not None
            and len(state.players[player].discard) < int(discard_at_least)
        ):
            return False

        if condition.get("adjacent_subject_has_name"):
            if not any(
                state.slot(player, adjacent).subject is not None
                and state.slot(player, adjacent).name is not None
                for adjacent in self._adjacent_positions(position)
            ):
                return False

        return True

    def _subject_actions(
        self,
        state: GameState,
        player: int,
        card_id: str,
    ) -> Iterable[Action]:
        for action in self._subject_action_templates[card_id]:
            if state.slot(player, action.position).subject is None:
                yield action

    def _link_actions(
        self,
        state: GameState,
        player: int,
        card_id: str,
    ) -> Iterable[Action]:
        for action in self._link_action_templates[card_id]:
            slot = state.slot(player, action.position)
            if slot.link is None:
                yield action

    def _name_actions(
        self,
        state: GameState,
        player: int,
        card_id: str,
    ) -> Iterable[Action]:
        for action in self._name_action_templates[card_id]:
            slot = state.slot(player, action.position)
            if slot.name is not None:
                continue
            if action.move_to is not None:
                if slot.subject is None:
                    continue
                if state.slot(player, action.move_to).occupied:
                    continue
            yield action

    def _plot_actions(
        self,
        state: GameState,
        player: int,
        card_id: str,
    ) -> Iterable[Action]:
        effect = self._plot_effects[card_id]

        if effect in {"discredit_subject", "return_name_or_weaken"}:
            for action in self._plot_target_action_templates[(card_id, player)]:
                target = action.targets[0]
                slot = state.slot(target.player, target.position)
                if slot.subject is None:
                    continue
                if self._subject_protected_from_opponent_plot(slot):
                    continue
                yield action
            return

        if effect == "move_subject":
            for action in self._plot_move_action_templates[(card_id, player)]:
                source = action.targets[0].position
                destination = action.targets[1].position
                source_slot = state.slot(player, source)
                if source_slot.subject is None:
                    continue
                if state.slot(player, destination).occupied:
                    continue
                required_rank = self._subject_required_rank.get(source_slot.subject)
                if (
                    required_rank is not None
                    and destination.rank.value != required_rank
                ):
                    continue
                yield action
            return

        if effect is None:
            yield PlayPlot(card_id)
            return

        raise NotImplementedError(f"Unsupported plot effect: {effect}")

    def _scheme_actions(
        self,
        state: GameState,
        player: int,
        card_id: str,
    ) -> Iterable[Action]:
        for action in self._scheme_action_templates[card_id]:
            if state.schemes[player][int(action.front)] is None:
                yield action

    def _immediate_story_locked(
        self,
        state: GameState,
        player: int,
    ) -> bool:
        for controller, rules in self._revealed_stratagem_rules(state):
            if controller != player:
                continue
            if rules.get("continuous", {}).get(
                "controller_immediate_story_lock"
            ):
                return True
        return False

    def _stratagem_trigger_matches(
        self,
        state: GameState,
        *,
        controller: int,
        rules: dict[str, Any],
        event: str,
        actor: int,
        card_id: str | None = None,
        position: Position | None = None,
    ) -> bool:
        trigger = rules.get("trigger", {})
        if trigger.get("event") != event:
            return False

        actor_scope = trigger.get("actor", "either")
        if actor_scope == "opponent" and actor == controller:
            return False
        if actor_scope == "controller" and actor != controller:
            return False

        roles = trigger.get("roles")
        if roles is not None:
            if card_id is None or self.cards[card_id].get("role") not in roles:
                return False

        ranks = trigger.get("ranks")
        if ranks is not None:
            if position is None or position.rank.value not in ranks:
                return False

        return True

    def _reveal_stratagem(
        self,
        state: GameState,
        controller: int,
        *,
        reason: str,
    ) -> dict[str, Any]:
        stratagem = state.stratagem(controller)
        if stratagem is None:
            return {}
        if not stratagem.revealed:
            stratagem.revealed = True
            state.observe_reveal(
                viewer=1 - controller,
                owner=controller,
                card_id=stratagem.card_id,
                zone="stratagem",
                reason=reason,
            )
        return self.cards[stratagem.card_id].get("rules", {}).get(
            "stratagem", {}
        )

    def _resolve_stratagem_event(
        self,
        state: GameState,
        *,
        event: str,
        actor: int,
        card_id: str | None = None,
        position: Position | None = None,
    ) -> None:
        for controller in (actor, 1 - actor):
            stratagem = state.stratagem(controller)
            if stratagem is None or stratagem.revealed:
                continue
            rules = self.cards[stratagem.card_id].get("rules", {}).get(
                "stratagem", {}
            )
            if not self._stratagem_trigger_matches(
                state,
                controller=controller,
                rules=rules,
                event=event,
                actor=actor,
                card_id=card_id,
                position=position,
            ):
                continue

            revealed = self._reveal_stratagem(
                state,
                controller,
                reason=f"{event}_triggered",
            )
            effect = revealed.get("reveal_effect", {})
            if effect.get("effect") == "penalize_trigger_subject":
                if position is not None:
                    slot = state.slot(actor, position)
                    if slot.subject is not None:
                        slot.temporary_strength -= int(effect.get("amount", 0))

    def _resolve_pre_story_stratagem(
        self,
        state: GameState,
        *,
        actor: int,
    ) -> bool:
        controller = 1 - actor
        stratagem = state.stratagem(controller)
        if stratagem is None or stratagem.revealed:
            return False
        rules = self.cards[stratagem.card_id].get("rules", {}).get(
            "stratagem", {}
        )
        if not self._stratagem_trigger_matches(
            state,
            controller=controller,
            rules=rules,
            event="immediate_story_played",
            actor=actor,
        ):
            return False
        revealed = self._reveal_stratagem(
            state,
            controller,
            reason="immediate_story_played_triggered",
        )
        return bool(revealed.get("reveal_effect", {}).get("cancel_story"))

    def _reveal_unrevealed_stratagems_at_battle_end(
        self,
        state: GameState,
    ) -> None:
        for controller in range(2):
            stratagem = state.stratagem(controller)
            if stratagem is not None and not stratagem.revealed:
                self._reveal_stratagem(
                    state,
                    controller,
                    reason="battle_end",
                )

    def _resolve_plot(
        self,
        state: GameState,
        actor: int,
        action: PlayPlot,
    ) -> None:
        effect = self.cards[action.card_id].get("rules", {}).get("effect")

        if effect == "discredit_subject":
            target = action.targets[0]
            slot = state.slot(target.player, target.position)
            if slot.link is not None:
                self._remove_link(state, target.player, target.position)
            elif slot.subject is not None:
                slot.temporary_strength -= 2
            return

        if effect == "return_name_or_weaken":
            target = action.targets[0]
            slot = state.slot(target.player, target.position)
            if slot.name is not None:
                self._remove_name(
                    state,
                    target.player,
                    target.position,
                    to_hand=True,
                )
            elif slot.subject is not None:
                slot.temporary_strength -= 2
            return

        if effect == "move_subject":
            source, destination = action.targets
            self._move_subject_with_attachments(
                state,
                actor,
                source.position,
                destination.position,
                adjacent_only=False,
            )
            return

        if effect is None:
            return

        raise NotImplementedError(f"Unsupported plot effect: {effect}")

    def _resolve_triggered_schemes(
        self,
        state: GameState,
        *,
        actor: int,
        event: str,
        front: Front,
        position: Position | None = None,
    ) -> None:
        for controller in (actor, 1 - actor):
            scheme = state.scheme(controller, front)
            if scheme is None:
                continue
            rules = self.cards[scheme.card_id].get("rules", {}).get("scheme", {})
            if rules.get("trigger") != event:
                continue
            if actor == controller:
                continue
            if rules.get("requires_own_subject") and not self._front_has_subject(
                state, controller, front
            ):
                continue
            self._reveal_and_resolve_scheme(
                state,
                controller=controller,
                front=front,
                actor=actor,
                position=position,
            )

    def _resolve_plot_target_schemes(
        self,
        state: GameState,
        *,
        actor: int,
        targets: tuple[BoardTarget, ...],
    ) -> None:
        opponent = 1 - actor
        targeted_fronts = {
            target.position.front
            for target in targets
            if target.player == opponent
        }
        for front in sorted(targeted_fronts, key=int):
            scheme = state.scheme(opponent, front)
            if scheme is None:
                continue
            rules = self.cards[scheme.card_id].get("rules", {}).get("scheme", {})
            if rules.get("trigger") != "opponent_plot_targets_your_card":
                continue
            if rules.get("requires_own_subject") and not self._front_has_subject(
                state, opponent, front
            ):
                continue
            self._reveal_and_resolve_scheme(
                state,
                controller=opponent,
                front=front,
                actor=actor,
            )

    def _resolve_pass_schemes(
        self,
        state: GameState,
        *,
        actor: int,
    ) -> None:
        opponent = 1 - actor
        for front in FRONTS:
            scheme = state.scheme(opponent, front)
            if scheme is None:
                continue
            rules = self.cards[scheme.card_id].get("rules", {}).get("scheme", {})
            if rules.get("trigger") != "opponent_passes":
                continue
            if rules.get("requires_own_subject") and not self._front_has_subject(
                state, opponent, front
            ):
                continue
            self._reveal_and_resolve_scheme(
                state,
                controller=opponent,
                front=front,
                actor=actor,
            )

    def _reveal_and_resolve_scheme(
        self,
        state: GameState,
        *,
        controller: int,
        front: Front,
        actor: int,
        position: Position | None = None,
    ) -> None:
        scheme = state.scheme(controller, front)
        if scheme is None:
            return

        if not scheme.revealed:
            scheme.revealed = True
            state.observe_reveal(
                viewer=1 - controller,
                owner=controller,
                card_id=scheme.card_id,
                zone="scheme",
                reason="scheme_triggered",
            )

        card_id = scheme.card_id
        rules = self.cards[card_id].get("rules", {}).get("scheme", {})
        effect = rules.get("effect")
        amount = int(rules.get("amount", 0))

        if effect == "penalize_played_subject":
            if position is not None:
                slot = state.slot(actor, position)
                if slot.subject is not None:
                    slot.temporary_strength -= amount

        elif effect == "discard_played_link":
            if position is not None:
                slot = state.slot(actor, position)
                if slot.link is not None:
                    self._remove_link(state, actor, position)

        elif effect == "reinforce_front":
            target = self._preferred_subject_position(state, controller, front)
            if target is not None:
                state.slot(controller, target).temporary_strength += amount

        elif effect in (None, "none"):
            pass

        else:
            raise NotImplementedError(f"Unsupported Scheme effect: {effect}")

        state.schemes[controller][int(front)] = None
        self._discard_card(state, controller, card_id)

    def _front_has_subject(
        self,
        state: GameState,
        player: int,
        front: Front,
    ) -> bool:
        return self._preferred_subject_position(state, player, front) is not None

    @staticmethod
    def _preferred_subject_position(
        state: GameState,
        player: int,
        front: Front,
    ) -> Position | None:
        frontline, rear = POSITIONS_BY_FRONT[int(front)]
        if state.slot(player, frontline).subject is not None:
            return frontline
        if state.slot(player, rear).subject is not None:
            return rear
        return None

    def _subject_protected_from_opponent_plot(self, slot: Slot) -> bool:
        if slot.link is None or slot.name is None:
            return False
        link = self.cards[slot.link]
        return bool(
            link.get("rules", {}).get("protect_subject_from_opponent_plot")
        )

    def _on_name_attached(
        self,
        state: GameState,
        player: int,
        position: Position,
        *,
        move_to: Position | None = None,
    ) -> None:
        slot = state.slot(player, position)
        if slot.name is None:
            return
        name = self.cards[slot.name]
        effect = name.get("rules", {}).get("on_name_attached")

        if effect == "reveal_enemy_scheme":
            owner = 1 - player
            enemy_scheme = state.scheme(owner, position.front)
            if enemy_scheme is not None and not enemy_scheme.revealed:
                enemy_scheme.revealed = True
                state.observe_reveal(
                    viewer=player,
                    owner=owner,
                    card_id=enemy_scheme.card_id,
                    zone="scheme",
                    reason="revealed_by_name",
                )

        if effect == "move_adjacent_optional" and move_to is not None:
            self._move_subject_with_attachments(state, player, position, move_to, adjacent_only=True)

    def _move_subject_with_attachments(
        self,
        state: GameState,
        player: int,
        source: Position,
        destination: Position,
        *,
        adjacent_only: bool,
    ) -> None:
        source_slot = state.slot(player, source)
        destination_slot = state.slot(player, destination)
        if source_slot.subject is None:
            raise IllegalAction("Source has no Subject")
        if destination_slot.occupied:
            raise IllegalAction("Destination is occupied")
        if adjacent_only and destination not in self._adjacent_positions(source):
            raise IllegalAction("Destination is not adjacent")

        subject = self.cards[source_slot.subject]
        required_rank = subject.get("rules", {}).get("placement", {}).get("rank")
        if required_rank is not None and destination.rank.value != required_rank:
            raise IllegalAction("Subject cannot occupy that rank")

        self._copy_slot(source_slot, destination_slot)
        self._clear_slot(source_slot)

    def _return_link_to_hand(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> None:
        slot = state.slot(player, position)
        link_id = slot.link
        if link_id is None:
            raise IllegalAction("Position has no Link")
        if slot.name is not None:
            raise IllegalAction("Cannot return a Link while a Name is attached")

        slot.link = None
        self._return_public_card_to_hand(
            state,
            player,
            link_id,
            reason="link_returned",
        )

    def _move_link(
        self,
        state: GameState,
        player: int,
        source: Position,
        destination: Position,
    ) -> None:
        source_slot = state.slot(player, source)
        destination_slot = state.slot(player, destination)

        if source_slot.link is None:
            raise IllegalAction("Source has no Link")
        if destination_slot.subject is None:
            raise IllegalAction("Destination has no Subject")
        if destination_slot.link is not None:
            raise IllegalAction("Destination already has a Link")

        destination_slot.link = source_slot.link
        destination_slot.name = source_slot.name
        source_slot.link = None
        source_slot.name = None

    def _remove_link(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> None:
        slot = state.slot(player, position)
        link_id = slot.link
        name_id = slot.name
        slot.link = None
        slot.name = None

        if link_id is not None:
            self._discard_card(state, player, link_id)
        if name_id is not None:
            self._return_public_card_to_hand(
                state,
                player,
                name_id,
                reason="link_removed",
            )

    def _remove_name(
        self,
        state: GameState,
        player: int,
        position: Position,
        *,
        to_hand: bool,
    ) -> str:
        slot = state.slot(player, position)
        name_id = slot.name
        if name_id is None:
            raise IllegalAction("Position has no Name")

        slot.name = None

        if to_hand:
            self._return_public_card_to_hand(
                state,
                player,
                name_id,
                reason="name_returned",
            )
        else:
            self._discard_card(state, player, name_id)

        return name_id

    def _discard_subject(
        self,
        state: GameState,
        player: int,
        position: Position,
    ) -> None:
        slot = state.slot(player, position)
        subject_id = slot.subject
        link_id = slot.link
        name_id = slot.name

        self._clear_slot(slot)

        if subject_id is not None:
            self._discard_card(state, player, subject_id)
        if link_id is not None:
            self._discard_card(state, player, link_id)
        if name_id is not None:
            self._discard_card(state, player, name_id)

    def _pass(self, state: GameState, player: int) -> None:
        state.players[player].passed = True
        state.pass_order.append(player)
        self._resolve_stratagem_event(
            state,
            event="pass",
            actor=player,
        )
        self._resolve_pass_schemes(state, actor=player)

        opponent = 1 - player
        if state.players[opponent].passed:
            self._score_battle(state)
        else:
            state.active_player = opponent

        state.turn_number += 1

    def _score_battle(self, state: GameState) -> None:
        front_scores = {
            front: (
                self.front_strength(state, 0, front),
                self.front_strength(state, 1, front),
            )
            for front in Front
        }

        controls = [0, 0]
        for score_a, score_b in front_scores.values():
            if score_a > score_b:
                controls[0] += 1
            elif score_b > score_a:
                controls[1] += 1

        if controls[0] >= 2:
            winner = 0
        elif controls[1] >= 2:
            winner = 1
        else:
            totals = [
                sum(scores[player] for scores in front_scores.values())
                for player in range(2)
            ]
            if totals[0] > totals[1]:
                winner = 0
            elif totals[1] > totals[0]:
                winner = 1
            else:
                winner = state.pass_order[0]

        state.players[winner].victories += 1
        loser = 1 - winner

        self._reveal_unrevealed_stratagems_at_battle_end(state)
        self._discard_battlefield(state)

        if state.players[winner].victories >= 2:
            state.phase = Phase.COMPLETE
            state.winner = winner
            state.chooser = None
            return

        state.battle += 1
        state.discarded_this_battle = [0, 0]
        state.stratagem_used = [False, False]
        state.draw_used = [False, False]
        state.pass_order.clear()
        if self.recycle_between_battles:
            self._recycle_non_hand_cards(state)
        else:
            self._refill_from_remaining_deck(state)
        for player in range(2):
            state.players[player].passed = False

        state.phase = Phase.CHOOSE_FIRST
        state.chooser = loser
        state.active_player = loser

    def _refill_from_remaining_deck(self, state: GameState) -> None:
        for player in range(2):
            player_state = state.players[player]
            self._draw(
                state,
                player,
                max(0, self.opening_hand_size - len(player_state.hand)),
            )

    def _recycle_non_hand_cards(self, state: GameState) -> None:
        seed = state.shuffle_seed
        for player in range(2):
            player_state = state.players[player]
            pool = list(player_state.deck)
            pool.extend(player_state.discard)
            player_state.discard.clear()
            seed = _shuffle_cards(pool, seed)
            player_state.deck[:] = pool
            self._draw(
                state,
                player,
                max(0, self.opening_hand_size - len(player_state.hand)),
            )
        state.shuffle_seed = seed

    def _complete_formation_counts(
        self,
        state: GameState,
        player: int,
    ) -> Counter[tuple[str, str, str]]:
        return Counter(
            (slot.subject, slot.link, slot.name)
            for position in ALL_POSITIONS
            for slot in [state.slot(player, position)]
            if slot.complete
        )

    def _reward_new_completion_draws(
        self,
        state: GameState,
        player: int,
        before: Counter[tuple[str, str, str]],
    ) -> None:
        after = self._complete_formation_counts(state, player)
        for combo, count in (after - before).items():
            name_id = combo[2]
            if name_id in self.completion_draw_names:
                self._draw(state, player, count)

    def _discard_battlefield(self, state: GameState) -> None:
        for player in range(2):
            for position in ALL_POSITIONS:
                slot = state.slot(player, position)
                for card_id in (slot.subject, slot.link, slot.name):
                    if card_id is not None:
                        state.players[player].discard.append(card_id)
                self._clear_slot(slot)

            for front in FRONTS:
                scheme = state.schemes[player][int(front)]
                if scheme is not None:
                    state.players[player].discard.append(scheme.card_id)
                    state.schemes[player][int(front)] = None

            stratagem = state.stratagem(player)
            if stratagem is not None:
                state.players[player].discard.append(stratagem.card_id)
                state.stratagems[player] = None

    def _advance_turn(self, state: GameState) -> None:
        opponent = 1 - state.active_player
        if not state.players[opponent].passed:
            state.active_player = opponent

    def _take_from_hand(
        self,
        state: GameState,
        player: int,
        card_id: str,
        *,
        hidden_kind: str | None = None,
    ) -> None:
        viewer = 1 - player
        if hidden_kind is None:
            if state.known_hidden_count(viewer, player, card_id, "hand") > 0:
                state.observe_hidden_delta(
                    viewer=viewer,
                    owner=player,
                    card_id=card_id,
                    zone="hand",
                    delta=-1,
                    reason="public_play_from_known_hand",
                )
        else:
            # A face-down play reveals that a card left the hand, but not
            # which eligible identity it was. Relax only knowledge that is no
            # longer guaranteed after that hidden play.
            known = state.known_hidden_counter(viewer, player, "hand")
            for known_id, count in list(known.items()):
                if count > 0 and self._can_be_hidden_play(
                    known_id,
                    hidden_kind,
                ):
                    state.observe_hidden_delta(
                        viewer=viewer,
                        owner=player,
                        card_id=known_id,
                        zone="hand",
                        delta=-1,
                        reason=f"possible_face_down_{hidden_kind}_play",
                    )

        state.players[player].hand.remove(card_id)

    def _can_be_hidden_play(
        self,
        card_id: str,
        hidden_kind: str,
    ) -> bool:
        card = self.cards[card_id]
        if hidden_kind == "scheme":
            return card["type"] == "plot" and bool(card.get("veiled", False))
        if hidden_kind == "stratagem":
            return card["type"] == "stratagem"
        raise ValueError(f"Unknown hidden play kind: {hidden_kind}")

    def _return_public_card_to_hand(
        self,
        state: GameState,
        player: int,
        card_id: str,
        *,
        reason: str,
    ) -> None:
        state.players[player].hand.append(card_id)
        state.observe_hidden_delta(
            viewer=1 - player,
            owner=player,
            card_id=card_id,
            zone="hand",
            delta=1,
            reason=reason,
        )

    def _discard_card(self, state: GameState, player: int, card_id: str) -> None:
        state.players[player].discard.append(card_id)
        state.discarded_this_battle[player] += 1

    def _draw(self, state: GameState, player: int, count: int) -> None:
        player_state = state.players[player]
        for _ in range(min(count, len(player_state.deck))):
            player_state.hand.append(player_state.deck.pop())

    @staticmethod
    def _adjacent_positions(position: Position) -> tuple[Position, ...]:
        return ADJACENT_POSITIONS[position]

    @staticmethod
    def _clear_slot(slot: Slot) -> None:
        slot.subject = None
        slot.link = None
        slot.name = None
        slot.temporary_strength = 0

    @staticmethod
    def _copy_slot(source: Slot, destination: Slot) -> None:
        destination.subject = source.subject
        destination.link = source.link
        destination.name = source.name
        destination.temporary_strength = source.temporary_strength
