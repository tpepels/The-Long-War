from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, IntEnum


class Front(IntEnum):
    FIRST = 0
    SECOND = 1
    THIRD = 2
    FOURTH = 3


class Rank(str, Enum):
    FRONT = "front"
    REAR = "rear"


class Phase(str, Enum):
    BATTLE = "battle"
    COMPLETE = "complete"


RANK_INDEX = {Rank.FRONT: 0, Rank.REAR: 1}
FRONT_COUNT = 4
RANK_COUNT = 2
POSITIONS_PER_PLAYER = FRONT_COUNT * RANK_COUNT


@dataclass(frozen=True, order=True)
class Position:
    front: Front
    rank: Rank


@dataclass
class Slot:
    force: str | None = None
    bond: str | None = None
    name: str | None = None
    temporary_strength: int = 0
    maneuvers_this_battle: int = 0

    @property
    def occupied(self) -> bool:
        return any(
            component is not None
            for component in (self.force, self.bond, self.name)
        )

    @property
    def complete(self) -> bool:
        return (
            self.force is not None
            and self.bond is not None
            and self.name is not None
        )

    @property
    def named(self) -> bool:
        return self.complete

@dataclass
class StoryState:
    card_id: str
    ongoing: bool = True
    fronts: tuple[Front, ...] = ()
    target_player: int | None = None
    target_position: Position | None = None


@dataclass
class StratagemState:
    card_id: str
    fronts: tuple[Front, ...] = ()
    direction: str | None = None
    targets: tuple[tuple[int, Position], ...] = ()


@dataclass
class PlayerState:
    deck: list[str]
    hand: list[str]
    discard: list[str] = field(default_factory=list)
    passed: bool = False
    command: int = 0


@dataclass(frozen=True)
class ObservationEvent:
    turn_number: int
    kind: str
    viewer: int
    owner: int
    card_id: str
    zone: str
    delta: int = 0
    reason: str = ""


def empty_board() -> list[list[list[Slot]]]:
    return [
        [[Slot(), Slot()] for _ in range(FRONT_COUNT)],
        [[Slot(), Slot()] for _ in range(FRONT_COUNT)],
    ]


def empty_stories() -> list[list[StoryState]]:
    return [[], []]


def empty_stratagems() -> list[StratagemState | None]:
    return [None, None]


@dataclass
class GameState:
    players: list[PlayerState]
    board: list[list[list[Slot]]] = field(default_factory=empty_board)
    stories: list[list[StoryState]] = field(default_factory=empty_stories)
    stratagems: list[StratagemState | None] = field(default_factory=empty_stratagems)
    stratagem_used: list[bool] = field(default_factory=lambda: [False, False])
    hero_used: list[bool] = field(default_factory=lambda: [False, False])
    active_player: int = 0
    battle: int = 1
    phase: Phase = Phase.BATTLE
    discarded_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    command_spent_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    command_refunded_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    battle_start_command: list[int] = field(default_factory=lambda: [0, 0])
    battle_start_hand_size: list[int] = field(default_factory=lambda: [0, 0])
    cards_drawn_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    completion_count_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    operations_this_battle: list[int] = field(default_factory=lambda: [0, 0])
    cards_played_this_turn_front_mask: list[int] = field(
        default_factory=lambda: [0, 0]
    )
    cards_played_this_battle_front_mask: list[int] = field(
        default_factory=lambda: [0, 0]
    )
    narratives_played_this_battle: list[int] = field(
        default_factory=lambda: [0, 0]
    )
    deck_reshuffles: list[int] = field(default_factory=lambda: [0, 0])
    reshuffle_card_totals: list[int] = field(default_factory=lambda: [0, 0])
    reshuffle_hand_card_totals: list[int] = field(default_factory=lambda: [0, 0])
    opening_hands: list[list[str]] = field(default_factory=lambda: [[], []])
    pending_draw_discard_for: int | None = None
    pending_draw_count: int = 0
    pending_draw_finish_operation: bool = False
    last_battle_snapshot: dict[str, object] | None = None
    pass_order: list[int] = field(default_factory=list)
    winner: int | None = None
    turn_number: int = 1
    shuffle_seed: int = 0
    observations: list[ObservationEvent] = field(default_factory=list)
    known_hidden_hand: list[list[dict[str, int]]] = field(
        default_factory=lambda: [[{}, {}], [{}, {}]]
    )

    def clone(self) -> "GameState":
        players = [
            PlayerState(
                deck=list(player.deck),
                hand=list(player.hand),
                discard=list(player.discard),
                passed=player.passed,
                command=player.command,
            )
            for player in self.players
        ]
        board = [
            [
                [
                    Slot(
                        force=slot.force,
                        bond=slot.bond,
                        name=slot.name,
                        temporary_strength=slot.temporary_strength,
                        maneuvers_this_battle=slot.maneuvers_this_battle,
                    )
                    for slot in front
                ]
                for front in side
            ]
            for side in self.board
        ]
        stories = [
            [
                StoryState(
                    card_id=story.card_id,
                    ongoing=story.ongoing,
                    fronts=tuple(story.fronts),
                    target_player=story.target_player,
                    target_position=story.target_position,
                )
                for story in side
            ]
            for side in self.stories
        ]
        stratagems = [
            (
                None
                if stratagem is None
                else StratagemState(
                    card_id=stratagem.card_id,
                    fronts=tuple(stratagem.fronts),
                    direction=stratagem.direction,
                    targets=tuple(stratagem.targets),
                )
            )
            for stratagem in self.stratagems
        ]
        return GameState(
            players=players,
            board=board,
            stories=stories,
            stratagems=stratagems,
            stratagem_used=list(self.stratagem_used),
            hero_used=list(self.hero_used),
            active_player=self.active_player,
            battle=self.battle,
            phase=self.phase,
            discarded_this_battle=list(self.discarded_this_battle),
            command_spent_this_battle=list(self.command_spent_this_battle),
            command_refunded_this_battle=list(self.command_refunded_this_battle),
            battle_start_command=list(self.battle_start_command),
            battle_start_hand_size=list(self.battle_start_hand_size),
            cards_drawn_this_battle=list(self.cards_drawn_this_battle),
            completion_count_this_battle=list(self.completion_count_this_battle),
            operations_this_battle=list(self.operations_this_battle),
            cards_played_this_turn_front_mask=list(
                self.cards_played_this_turn_front_mask
            ),
            cards_played_this_battle_front_mask=list(
                self.cards_played_this_battle_front_mask
            ),
            narratives_played_this_battle=list(
                self.narratives_played_this_battle
            ),
            deck_reshuffles=list(self.deck_reshuffles),
            reshuffle_card_totals=list(self.reshuffle_card_totals),
            reshuffle_hand_card_totals=list(self.reshuffle_hand_card_totals),
            opening_hands=[list(hand) for hand in self.opening_hands],
            pending_draw_discard_for=self.pending_draw_discard_for,
            pending_draw_count=self.pending_draw_count,
            pending_draw_finish_operation=self.pending_draw_finish_operation,
            last_battle_snapshot=(
                None
                if self.last_battle_snapshot is None
                else dict(self.last_battle_snapshot)
            ),
            pass_order=list(self.pass_order),
            winner=self.winner,
            turn_number=self.turn_number,
            shuffle_seed=self.shuffle_seed,
            observations=list(self.observations),
            known_hidden_hand=[
                [dict(self.known_hidden_hand[v][o]) for o in range(2)]
                for v in range(2)
            ],
        )

    def copy_from(self, source: "GameState") -> "GameState":
        for index in range(2):
            target_player = self.players[index]
            source_player = source.players[index]
            target_player.deck[:] = source_player.deck
            target_player.hand[:] = source_player.hand
            target_player.discard[:] = source_player.discard
            target_player.passed = source_player.passed
            target_player.command = source_player.command

        for player in range(2):
            for front in range(FRONT_COUNT):
                for rank in range(RANK_COUNT):
                    target_slot = self.board[player][front][rank]
                    source_slot = source.board[player][front][rank]
                    target_slot.force = source_slot.force
                    target_slot.bond = source_slot.bond
                    target_slot.name = source_slot.name
                    target_slot.temporary_strength = source_slot.temporary_strength
                    target_slot.maneuvers_this_battle = source_slot.maneuvers_this_battle

            self.stories[player][:] = [
                StoryState(
                    card_id=story.card_id,
                    ongoing=story.ongoing,
                    fronts=tuple(story.fronts),
                    target_player=story.target_player,
                    target_position=story.target_position,
                )
                for story in source.stories[player]
            ]

            source_stratagem = source.stratagems[player]
            self.stratagems[player] = (
                None
                if source_stratagem is None
                else StratagemState(
                    card_id=source_stratagem.card_id,
                    fronts=tuple(source_stratagem.fronts),
                    direction=source_stratagem.direction,
                    targets=tuple(source_stratagem.targets),
                )
            )

        self.stratagem_used[:] = source.stratagem_used
        self.hero_used[:] = source.hero_used
        self.active_player = source.active_player
        self.battle = source.battle
        self.phase = source.phase
        self.discarded_this_battle[:] = source.discarded_this_battle
        self.command_spent_this_battle[:] = source.command_spent_this_battle
        self.command_refunded_this_battle[:] = source.command_refunded_this_battle
        self.battle_start_command[:] = source.battle_start_command
        self.battle_start_hand_size[:] = source.battle_start_hand_size
        self.cards_drawn_this_battle[:] = source.cards_drawn_this_battle
        self.completion_count_this_battle[:] = source.completion_count_this_battle
        self.operations_this_battle[:] = source.operations_this_battle
        self.cards_played_this_turn_front_mask[:] = (
            source.cards_played_this_turn_front_mask
        )
        self.cards_played_this_battle_front_mask[:] = (
            source.cards_played_this_battle_front_mask
        )
        self.narratives_played_this_battle[:] = (
            source.narratives_played_this_battle
        )
        self.deck_reshuffles[:] = source.deck_reshuffles
        self.reshuffle_card_totals[:] = source.reshuffle_card_totals
        self.reshuffle_hand_card_totals[:] = source.reshuffle_hand_card_totals
        for index in range(2):
            self.opening_hands[index][:] = source.opening_hands[index]
        self.pending_draw_discard_for = source.pending_draw_discard_for
        self.pending_draw_count = source.pending_draw_count
        self.pending_draw_finish_operation = source.pending_draw_finish_operation
        self.last_battle_snapshot = (
            None
            if source.last_battle_snapshot is None
            else dict(source.last_battle_snapshot)
        )
        self.pass_order[:] = source.pass_order
        self.winner = source.winner
        self.turn_number = source.turn_number
        self.shuffle_seed = source.shuffle_seed
        self.observations[:] = source.observations
        for viewer in range(2):
            for owner in range(2):
                self.known_hidden_hand[viewer][owner].clear()
                self.known_hidden_hand[viewer][owner].update(
                    source.known_hidden_hand[viewer][owner]
                )
        return self

    def slot(self, player: int, position: Position) -> Slot:
        return self.board[player][int(position.front)][RANK_INDEX[position.rank]]

    def ongoing_stories(self, player: int) -> list[StoryState]:
        return self.stories[player]

    def observe_hidden_delta(
        self,
        *,
        viewer: int,
        owner: int,
        card_id: str,
        zone: str,
        delta: int,
        reason: str,
    ) -> None:
        if delta == 0:
            return
        if zone == "hand":
            counter = self.known_hidden_hand[viewer][owner]
            updated = counter.get(card_id, 0) + delta
            if updated > 0:
                counter[card_id] = updated
            else:
                counter.pop(card_id, None)
        self.observations.append(
            ObservationEvent(
                turn_number=self.turn_number,
                kind="hidden_knowledge",
                viewer=viewer,
                owner=owner,
                card_id=card_id,
                zone=zone,
                delta=delta,
                reason=reason,
            )
        )

    def observe_reveal(
        self,
        *,
        viewer: int,
        owner: int,
        card_id: str,
        zone: str,
        reason: str,
    ) -> None:
        self.observations.append(
            ObservationEvent(
                turn_number=self.turn_number,
                kind="reveal",
                viewer=viewer,
                owner=owner,
                card_id=card_id,
                zone=zone,
                reason=reason,
            )
        )

    def known_hidden_counter(
        self,
        viewer: int,
        owner: int,
        zone: str = "hand",
    ) -> Counter[str]:
        if zone == "hand":
            return Counter(self.known_hidden_hand[viewer][owner])

        counts: Counter[str] = Counter()
        for event in self.observations:
            if (
                event.kind == "hidden_knowledge"
                and event.viewer == viewer
                and event.owner == owner
                and event.zone == zone
            ):
                counts[event.card_id] += event.delta
                if counts[event.card_id] <= 0:
                    del counts[event.card_id]
        return counts

    def known_hidden_cards(
        self,
        viewer: int,
        owner: int,
        zone: str = "hand",
    ) -> list[str]:
        counts = self.known_hidden_counter(viewer, owner, zone)
        return [
            card_id
            for card_id, count in sorted(counts.items())
            for _ in range(count)
        ]

    def known_hidden_count(
        self,
        viewer: int,
        owner: int,
        card_id: str,
        zone: str = "hand",
    ) -> int:
        return self.known_hidden_counter(viewer, owner, zone).get(card_id, 0)
