from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, IntEnum

from ..protocol import ObservationKind, ObservationZone, PendingResume, PLAYER_COUNT


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


class ConstraintKind(str, Enum):
    AFFECT_FRONT = "affect_front"
    MANEUVER = "maneuver"
    SPECIFIC_MANEUVER = "specific_maneuver"


def other_player(player: int) -> int:
    if not 0 <= player < PLAYER_COUNT:
        raise ValueError(f"invalid player index: {player}")
    return (player + 1) % PLAYER_COUNT


RANK_INDEX = {Rank.FRONT: 0, Rank.REAR: 1}
FRONT_COUNT = len(Front)
RANK_COUNT = len(Rank)
POSITIONS_PER_PLAYER = FRONT_COUNT * RANK_COUNT
TOTAL_POSITION_COUNT = PLAYER_COUNT * POSITIONS_PER_PLAYER


RANK_BY_INDEX = tuple(Rank)


def decode_slot_index(slot: int) -> tuple[int, "Position"]:
    if not 0 <= slot < TOTAL_POSITION_COUNT:
        raise ValueError(f"invalid slot index: {slot}")
    player, local = divmod(slot, POSITIONS_PER_PLAYER)
    front_index, rank_index = divmod(local, RANK_COUNT)
    return player, Position(Front(front_index), RANK_BY_INDEX[rank_index])


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
    maneuver_direction: str | None = None
    maneuvered_in_operation: bool = False

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
class NarrativeState:
    card_id: str
    ongoing: bool = True
    fronts: tuple[Front, ...] = ()
    target_player: int | None = None
    target_position: Position | None = None
    direction: str | None = None
    triggered_this_battle: bool = False
    triggered_players_mask: int = 0


@dataclass
class OperationConstraint:
    source_card: str
    player: int
    kind: ConstraintKind
    source_owner: int
    front: Front | None = None
    direction: str | None = None
    source_position: Position | None = None
    activate_turn: int = 0
    expires_after_operation: bool = True
    persists_between_battles: bool = False
    zero_cost: bool = False
    draw_after_satisfied: int = 0
    discard_source_narrative: bool = False
    expires_end_of_activated_turn: bool = False


@dataclass
class StratagemState:
    card_id: str
    fronts: tuple[Front, ...] = ()
    direction: str | None = None
    targets: tuple[tuple[int, Position], ...] = ()
    revealed: bool = False


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
    kind: ObservationKind
    viewer: int
    owner: int
    card_id: str
    zone: ObservationZone
    delta: int = 0
    reason: str = ""


def empty_board() -> list[list[list[Slot]]]:
    return [
        [
            [Slot() for _ in range(RANK_COUNT)]
            for _ in range(FRONT_COUNT)
        ]
        for _ in range(PLAYER_COUNT)
    ]


def empty_narratives() -> list[list[NarrativeState]]:
    return [[] for _ in range(PLAYER_COUNT)]


def empty_stratagems() -> list[StratagemState | None]:
    return [None for _ in range(PLAYER_COUNT)]


def zero_per_player() -> list[int]:
    return [0 for _ in range(PLAYER_COUNT)]


def false_per_player() -> list[bool]:
    return [False for _ in range(PLAYER_COUNT)]


def none_per_player() -> list[None]:
    return [None for _ in range(PLAYER_COUNT)]


def empty_hands_per_player() -> list[list[str]]:
    return [[] for _ in range(PLAYER_COUNT)]


def empty_known_hidden() -> list[list[dict[str, int]]]:
    return [
        [{} for _ in range(PLAYER_COUNT)]
        for _ in range(PLAYER_COUNT)
    ]


@dataclass
class GameState:
    players: list[PlayerState]
    board: list[list[list[Slot]]] = field(default_factory=empty_board)
    narratives: list[list[NarrativeState]] = field(default_factory=empty_narratives)
    stratagems: list[StratagemState | None] = field(default_factory=empty_stratagems)
    stratagem_used: list[int] = field(default_factory=zero_per_player)
    hero_used: list[int] = field(default_factory=zero_per_player)
    active_player: int = 0
    battle: int = 1
    phase: Phase = Phase.BATTLE
    discarded_this_battle: list[int] = field(default_factory=zero_per_player)
    command_spent_this_battle: list[int] = field(default_factory=zero_per_player)
    command_refunded_this_battle: list[int] = field(default_factory=zero_per_player)
    battle_start_command: list[int] = field(default_factory=zero_per_player)
    battle_start_hand_size: list[int] = field(default_factory=zero_per_player)
    cards_drawn_this_battle: list[int] = field(default_factory=zero_per_player)
    completion_count_this_battle: list[int] = field(default_factory=zero_per_player)
    # Kept under the historical field name for artifact compatibility; these
    # are now Actions rather than one-operation turns.
    operations_this_battle: list[int] = field(default_factory=zero_per_player)
    actions_this_turn: int = 0
    closing_turns_remaining: int = 0
    maneuvers_this_battle: list[int] = field(default_factory=zero_per_player)
    cards_played_this_turn_front_mask: list[int] = field(
        default_factory=zero_per_player
    )
    cards_played_this_battle_front_mask: list[int] = field(
        default_factory=zero_per_player
    )
    narratives_played_this_battle: list[int] = field(
        default_factory=zero_per_player
    )
    deck_reshuffles: list[int] = field(default_factory=zero_per_player)
    reshuffle_card_totals: list[int] = field(default_factory=zero_per_player)
    reshuffle_hand_card_totals: list[int] = field(default_factory=zero_per_player)
    opening_hands: list[list[str]] = field(default_factory=empty_hands_per_player)
    pending_draw_discard_for: int | None = None
    pending_draw_count: int = 0
    pending_draw_finish_operation: bool = False
    pending_effects: list[dict[str, object]] = field(default_factory=list)
    pending_resume: PendingResume | None = None
    pending_resume_player: int | None = None
    free_maneuver_available: list[bool] = field(default_factory=false_per_player)
    free_maneuver_source: list[str | None] = field(default_factory=none_per_player)
    constraints: list[OperationConstraint] = field(default_factory=list)
    battle_resolution: dict[str, object] | None = None
    last_battle_snapshot: dict[str, object] | None = None
    pass_order: list[int] = field(default_factory=list)
    winner: int | None = None
    turn_number: int = 1
    shuffle_seed: int = 0
    observations: list[ObservationEvent] = field(default_factory=list)
    known_hidden_hand: list[list[dict[str, int]]] = field(
        default_factory=empty_known_hidden
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
                        maneuver_direction=slot.maneuver_direction,
                        maneuvered_in_operation=slot.maneuvered_in_operation,
                    )
                    for slot in front
                ]
                for front in side
            ]
            for side in self.board
        ]
        narratives = [
            [
                NarrativeState(
                    card_id=narrative.card_id,
                    ongoing=narrative.ongoing,
                    fronts=tuple(narrative.fronts),
                    target_player=narrative.target_player,
                    target_position=narrative.target_position,
                    direction=narrative.direction,
                    triggered_this_battle=narrative.triggered_this_battle,
                    triggered_players_mask=narrative.triggered_players_mask,
                )
                for narrative in side
            ]
            for side in self.narratives
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
                    revealed=stratagem.revealed,
                )
            )
            for stratagem in self.stratagems
        ]
        return GameState(
            players=players,
            board=board,
            narratives=narratives,
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
            actions_this_turn=self.actions_this_turn,
            closing_turns_remaining=self.closing_turns_remaining,
            maneuvers_this_battle=list(self.maneuvers_this_battle),
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
            pending_effects=[dict(effect) for effect in self.pending_effects],
            pending_resume=self.pending_resume,
            pending_resume_player=self.pending_resume_player,
            free_maneuver_available=list(self.free_maneuver_available),
            free_maneuver_source=list(self.free_maneuver_source),
            constraints=[
                OperationConstraint(
                    source_card=item.source_card,
                    player=item.player,
                    kind=item.kind,
                    source_owner=item.source_owner,
                    front=item.front,
                    direction=item.direction,
                    source_position=item.source_position,
                    activate_turn=item.activate_turn,
                    expires_after_operation=item.expires_after_operation,
                    persists_between_battles=item.persists_between_battles,
                    zero_cost=item.zero_cost,
                    draw_after_satisfied=item.draw_after_satisfied,
                    discard_source_narrative=item.discard_source_narrative,
                    expires_end_of_activated_turn=item.expires_end_of_activated_turn,
                )
                for item in self.constraints
            ],
            battle_resolution=(
                None
                if self.battle_resolution is None
                else {
                    key: (list(value) if isinstance(value, list) else value)
                    for key, value in self.battle_resolution.items()
                }
            ),
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
                [dict(self.known_hidden_hand[v][o]) for o in range(PLAYER_COUNT)]
                for v in range(PLAYER_COUNT)
            ],
        )

    def copy_from(self, source: "GameState") -> "GameState":
        for index in range(PLAYER_COUNT):
            target_player = self.players[index]
            source_player = source.players[index]
            target_player.deck[:] = source_player.deck
            target_player.hand[:] = source_player.hand
            target_player.discard[:] = source_player.discard
            target_player.passed = source_player.passed
            target_player.command = source_player.command

        for player in range(PLAYER_COUNT):
            for front in range(FRONT_COUNT):
                for rank in range(RANK_COUNT):
                    target_slot = self.board[player][front][rank]
                    source_slot = source.board[player][front][rank]
                    target_slot.force = source_slot.force
                    target_slot.bond = source_slot.bond
                    target_slot.name = source_slot.name
                    target_slot.temporary_strength = source_slot.temporary_strength
                    target_slot.maneuvers_this_battle = source_slot.maneuvers_this_battle
                    target_slot.maneuver_direction = source_slot.maneuver_direction
                    target_slot.maneuvered_in_operation = (
                        source_slot.maneuvered_in_operation
                    )

            self.narratives[player][:] = [
                NarrativeState(
                    card_id=narrative.card_id,
                    ongoing=narrative.ongoing,
                    fronts=tuple(narrative.fronts),
                    target_player=narrative.target_player,
                    target_position=narrative.target_position,
                    direction=narrative.direction,
                    triggered_this_battle=narrative.triggered_this_battle,
                    triggered_players_mask=narrative.triggered_players_mask,
                )
                for narrative in source.narratives[player]
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
                    revealed=source_stratagem.revealed,
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
        self.actions_this_turn = source.actions_this_turn
        self.closing_turns_remaining = source.closing_turns_remaining
        self.maneuvers_this_battle[:] = source.maneuvers_this_battle
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
        for index in range(PLAYER_COUNT):
            self.opening_hands[index][:] = source.opening_hands[index]
        self.pending_draw_discard_for = source.pending_draw_discard_for
        self.pending_draw_count = source.pending_draw_count
        self.pending_draw_finish_operation = source.pending_draw_finish_operation
        self.pending_effects[:] = [dict(effect) for effect in source.pending_effects]
        self.pending_resume = source.pending_resume
        self.pending_resume_player = source.pending_resume_player
        self.free_maneuver_available[:] = source.free_maneuver_available
        self.free_maneuver_source[:] = source.free_maneuver_source
        self.constraints[:] = [
            OperationConstraint(
                source_card=item.source_card,
                player=item.player,
                kind=item.kind,
                source_owner=item.source_owner,
                front=item.front,
                direction=item.direction,
                source_position=item.source_position,
                activate_turn=item.activate_turn,
                expires_after_operation=item.expires_after_operation,
                persists_between_battles=item.persists_between_battles,
                zero_cost=item.zero_cost,
                draw_after_satisfied=item.draw_after_satisfied,
                discard_source_narrative=item.discard_source_narrative,
            )
            for item in source.constraints
        ]
        self.battle_resolution = (
            None
            if source.battle_resolution is None
            else {
                key: (list(value) if isinstance(value, list) else value)
                for key, value in source.battle_resolution.items()
            }
        )
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
        for viewer in range(PLAYER_COUNT):
            for owner in range(PLAYER_COUNT):
                self.known_hidden_hand[viewer][owner].clear()
                self.known_hidden_hand[viewer][owner].update(
                    source.known_hidden_hand[viewer][owner]
                )
        return self

    def slot(self, player: int, position: Position) -> Slot:
        return self.board[player][int(position.front)][RANK_INDEX[position.rank]]

    def ongoing_narratives(self, player: int) -> list[NarrativeState]:
        return self.narratives[player]

    def observe_hidden_delta(
        self,
        *,
        viewer: int,
        owner: int,
        card_id: str,
        zone: ObservationZone,
        delta: int,
        reason: str,
    ) -> None:
        if delta == 0:
            return
        zone = ObservationZone(zone)
        if zone is ObservationZone.HAND:
            counter = self.known_hidden_hand[viewer][owner]
            updated = counter.get(card_id, 0) + delta
            if updated > 0:
                counter[card_id] = updated
            else:
                counter.pop(card_id, None)
        self.observations.append(
            ObservationEvent(
                turn_number=self.turn_number,
                kind=ObservationKind.HIDDEN_KNOWLEDGE,
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
        zone: ObservationZone,
        reason: str,
    ) -> None:
        zone = ObservationZone(zone)
        self.observations.append(
            ObservationEvent(
                turn_number=self.turn_number,
                kind=ObservationKind.REVEAL,
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
        zone: ObservationZone = ObservationZone.HAND,
    ) -> Counter[str]:
        zone = ObservationZone(zone)
        if zone is ObservationZone.HAND:
            return Counter(self.known_hidden_hand[viewer][owner])

        counts: Counter[str] = Counter()
        for event in self.observations:
            if (
                event.kind is ObservationKind.HIDDEN_KNOWLEDGE
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
        zone: ObservationZone = ObservationZone.HAND,
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
        zone: ObservationZone = ObservationZone.HAND,
    ) -> int:
        return self.known_hidden_counter(viewer, owner, zone).get(card_id, 0)
