from __future__ import annotations

import json
from typing import Any

from .agents.heuristic_agent import HeuristicAgent
from .game.actions import (
    Action,
    BoardTarget,
    Discard,
    Maneuver,
    Pass,
    PlayBond,
    PlayForce,
    PlayName,
    PlayStory,
    PlayStratagem,
    action_key,
)
from .game.engine import GameEngine, all_positions
from .game.model import Front, Phase, Position, Rank


FRONT_NAMES = {
    Front.FIRST: "Front 1",
    Front.SECOND: "Front 2",
    Front.THIRD: "Front 3",
    Front.FOURTH: "Front 4",
}
RANK_NAMES = {
    Rank.FRONT: "Frontline",
    Rank.REAR: "Rear",
}


class PlaySession:
    """JSON adapter around the canonical packed Cython game engine."""

    def __init__(
        self,
        card_data_json: str,
        deck_json: str,
        mode: str = "hotseat",
        seed: int = 1,
        paced_ai: bool = False,
    ):
        if mode not in {"hotseat", "computer"}:
            raise ValueError(f"Unsupported play mode: {mode}")

        card_data = json.loads(card_data_json)
        deck_payload = json.loads(deck_json)
        deck = (
            list(deck_payload["cards"])
            if isinstance(deck_payload, dict)
            else list(deck_payload)
        )

        self.engine = GameEngine(card_data)
        self.cards = self.engine.cards
        self.deck = deck
        self.mode = mode
        self.seed = int(seed)
        self.paced_ai = paced_ai
        self.human_players = {0, 1} if mode == "hotseat" else {0}
        self.log: list[str] = []
        self.opening_player: int | None = None
        self.last_action: dict[str, Any] | None = None
        self.action_serial = 0

        # Preview state exposes reproducible opening hands before mulligans.
        self.state = self.engine.new_game(
            deck,
            deck,
            seed=self.seed,
            first_player=None,
            opening_bonus=False,
        )
        self.setup_complete = False
        self.mulligan_player = 0
        self.mulligan_choices: dict[int, tuple[int, ...]] = {}

        self.agents: dict[int, Any] = {}
        if mode == "computer":
            self.agents[1] = HeuristicAgent(
                self.seed + 20_001,
                exploration=0.0,
            )

    def snapshot_json(self, viewer: int | None = None) -> str:
        return json.dumps(self.snapshot(viewer), separators=(",", ":"))

    def act_json(self, key: str, viewer: int) -> str:
        return json.dumps(self.act(key, viewer), separators=(",", ":"))

    def mulligan_json(self, indices: list[int], viewer: int) -> str:
        return json.dumps(
            self.mulligan(indices, viewer),
            separators=(",", ":"),
        )

    def ai_step_json(self) -> str:
        return json.dumps(self.ai_step(), separators=(",", ":"))

    def ai_step(self) -> dict[str, Any]:
        if not self.setup_complete:
            raise ValueError("Complete the opening mulligan first")
        if self.mode == "hotseat":
            raise ValueError("AI stepping requires an AI opponent")
        if (
            self.state.phase is not Phase.COMPLETE
            and self.state.active_player not in self.human_players
        ):
            actor = self.state.active_player
            self._apply_with_log(
                self.agents[actor].choose(self.engine, self.state)
            )
        return self.snapshot(0)

    def mulligan(self, indices: list[int], viewer: int) -> dict[str, Any]:
        if self.setup_complete:
            raise ValueError("The mulligan is already complete")
        if viewer not in self.human_players:
            raise ValueError("That player is not human-controlled")
        if viewer != self.mulligan_player:
            raise ValueError("It is not that player's mulligan")

        normalized = tuple(sorted(int(index) for index in indices))
        if len(normalized) > 2 or len(set(normalized)) != len(normalized):
            raise ValueError("Choose at most two distinct cards")
        hand = self.state.players[viewer].hand
        if any(index < 0 or index >= len(hand) for index in normalized):
            raise ValueError("Mulligan selection is outside the opening hand")

        self.mulligan_choices[viewer] = normalized

        if self.mode == "hotseat" and viewer == 0:
            self.mulligan_player = 1
            return self.snapshot(None)

        if self.mode != "hotseat":
            agent = self.agents[1]
            self.mulligan_choices[1] = (
                agent.choose_mulligan(
                    self.engine,
                    self.state.players[1].hand,
                )
                if hasattr(agent, "choose_mulligan")
                else ()
            )

        self._finish_mulligans()
        return self.snapshot(None if self.mode == "hotseat" else 0)

    def _finish_mulligans(self) -> None:
        choices = (
            self.mulligan_choices.get(0, ()),
            self.mulligan_choices.get(1, ()),
        )
        self.state = self.engine.new_game(
            self.deck,
            self.deck,
            seed=self.seed,
            first_player=None,
            mulligan_indices=choices,
        )
        self.setup_complete = True
        self.opening_player = self.state.active_player

        self.log.append(
            f"Battle I begins. Player {self.state.active_player + 1} goes first. "
            "The first turn begins normally with the start-of-turn draw."
        )
        self._run_ai_until_human()

    def act(self, key: str, viewer: int) -> dict[str, Any]:
        if not self.setup_complete:
            raise ValueError("Complete the opening mulligan first")
        if viewer not in self.human_players:
            raise ValueError("That player is not human-controlled")
        if self.state.phase is Phase.COMPLETE:
            raise ValueError("The match is already complete")
        if self.state.active_player != viewer:
            raise ValueError("It is not that player's turn")

        legal = self.engine.legal_actions(self.state)
        action = next(
            (item for item in legal if action_key(item) == key),
            None,
        )
        if action is None:
            raise ValueError("That action is no longer legal")

        self._apply_with_log(action)
        self._run_ai_until_human()
        if self.mode == "hotseat":
            return self.snapshot(None)
        return self.snapshot(0)

    def snapshot(self, viewer: int | None = None) -> dict[str, Any]:
        state = self.state
        if viewer is not None and viewer not in (0, 1):
            raise ValueError("viewer must be 0, 1, or null")

        display_active = (
            self.mulligan_player
            if not self.setup_complete
            else state.active_player
        )
        display_phase = (
            "mulligan"
            if not self.setup_complete
            else state.phase.value
        )

        players = [
            {
                "passed": ps.passed,
                "hand_count": len(ps.hand),
                "deck_count": len(ps.deck),
                "command": ps.command,
                "hero_used": bool(state.hero_used[player]),
                "discard": list(ps.discard),
            }
            for player, ps in enumerate(state.players)
        ]

        board: list[list[dict[str, Any]]] = [[], []]
        for owner in range(2):
            for position in all_positions():
                slot = state.slot(owner, position)
                board[owner].append(
                    {
                        "front": int(position.front),
                        "front_name": FRONT_NAMES[position.front],
                        "rank": position.rank.value,
                        "rank_name": RANK_NAMES[position.rank],
                        "force": slot.force,
                        "bond": slot.bond,
                        "name": slot.name,
                        "complete": slot.complete,
                        "strength": self.engine.position_strength(
                            state,
                            owner,
                            position,
                        ),
                    }
                )

        stories = [
            [
                {
                    "card_id": story.card_id,
                    "ongoing": story.ongoing,
                }
                for story in state.stories[owner][
                    : self.engine.ongoing_story_limit
                ]
            ]
            for owner in range(2)
        ]

        stratagems = [
            (
                None
                if state.stratagems[owner] is None
                else {"card_id": state.stratagems[owner].card_id}
            )
            for owner in range(2)
        ]

        front_strengths = [
            [
                self.engine.front_strength(state, player, front)
                for front in Front
            ]
            for player in range(2)
        ]
        front_control = []
        for front in Front:
            p0 = front_strengths[0][int(front)]
            p1 = front_strengths[1][int(front)]
            front_control.append(
                0 if p0 > p1 else 1 if p1 > p0 else None
            )

        hand: list[str] = []
        legal_actions: list[dict[str, Any]] = []
        if not self.setup_complete:
            if (
                viewer is not None
                and viewer == self.mulligan_player
                and viewer in self.human_players
            ):
                hand = list(state.players[viewer].hand)
        elif (
            viewer is not None
            and viewer in self.human_players
            and state.phase is not Phase.COMPLETE
            and (
                self.mode != "hotseat"
                or viewer == state.active_player
            )
        ):
            hand = list(state.players[viewer].hand)
            if viewer == state.active_player:
                legal_actions = [
                    self._action_view(action)
                    for action in self.engine.legal_actions(state)
                ]

        return {
            "mode": self.mode,
            "seed": self.seed,
            "opening_player": self.opening_player,
            "battle": state.battle,
            "phase": display_phase,
            "active_player": display_active,
            "winner": state.winner,
            "viewer": viewer,
            "needs_reveal": (
                self.mode == "hotseat"
                and viewer is None
                and (
                    not self.setup_complete
                    or state.phase is not Phase.COMPLETE
                )
            ),
            "mulligan_available": (
                not self.setup_complete
                and viewer is not None
                and viewer == self.mulligan_player
            ),
            "mulligan_limit": 2,
            "players": players,
            "board": board,
            "stories": stories,
            "story_limit": self.engine.ongoing_story_limit,
            "stratagems": stratagems,
            "stratagem_used": list(state.stratagem_used),
            "hero_used": list(state.hero_used),
            "pass_order": list(state.pass_order),
            "pending_draw_discard_for": state.pending_draw_discard_for,
            "needs_ai": (
                self.setup_complete
                and state.phase is not Phase.COMPLETE
                and state.active_player not in self.human_players
            ),
            "last_action": self._last_action_view(viewer),
            "front_strengths": front_strengths,
            "front_control": front_control,
            "hand": hand,
            "legal_actions": legal_actions,
            "log": self.log[-40:],
        }

    def _run_ai_until_human(self) -> None:
        if not self.setup_complete or self.paced_ai:
            return
        safety = 0
        while (
            self.state.phase is not Phase.COMPLETE
            and self.state.active_player not in self.human_players
        ):
            safety += 1
            if safety > 200:
                raise RuntimeError("AI loop exceeded 200 actions")
            actor = self.state.active_player
            action = self.agents[actor].choose(
                self.engine,
                self.state,
            )
            self._apply_with_log(action)

    def _apply_with_log(self, action: Action) -> None:
        actor = self.state.active_player
        battle_before = self.state.battle
        label = self._describe_action(action, actor)
        payload = self._action_view(action)

        self.engine.apply(self.state, action)
        self.log.append(label)
        self.action_serial += 1
        self.last_action = {
            **payload,
            "id": self.action_serial,
            "actor": actor,
            "public_label": label,
            "private_label": payload["label"],
            "events": [],
        }

        if self.state.phase is Phase.COMPLETE:
            self.log.append(
                f"Player {self.state.winner + 1} wins the war."
            )
        elif self.state.battle != battle_before:
            self.log.append(
                f"Battle {self._roman(self.state.battle)} begins. "
                f"Player {self.state.active_player + 1} starts."
            )

    def _last_action_view(
        self,
        viewer: int | None,
    ) -> dict[str, Any] | None:
        del viewer
        if self.last_action is None:
            return None
        return {
            key: value
            for key, value in self.last_action.items()
            if key
            not in {
                "key",
                "reason",
                "public_label",
                "private_label",
            }
        }

    def _action_view(self, action: Action) -> dict[str, Any]:
        card_id = getattr(action, "card_id", None)
        payload: dict[str, Any] = {
            "key": action_key(action),
            "kind": type(action).__name__,
            "card_id": card_id,
            "command_cost": self.engine.command_cost_for_action(
                self.state,
                action,
            ),
            "label": self._describe_action(
                action,
                self.state.active_player,
                private=True,
            ),
            "reason": self._legal_reason(action),
            "position": None,
            "source": None,
            "destination": None,
            "ongoing_slot": None,
            "targets": [],
        }

        if isinstance(action, (PlayForce, PlayBond, PlayName)):
            payload["position"] = self._position_payload(
                action.position
            )
        elif isinstance(action, Maneuver):
            payload["source"] = self._position_payload(action.source)
            payload["destination"] = self._position_payload(
                action.destination
            )
        elif isinstance(action, PlayStory):
            payload["ongoing_slot"] = action.ongoing_slot
            payload["targets"] = [
                {
                    "player": target.player,
                    **self._position_payload(target.position),
                }
                for target in action.targets
            ]

        return payload

    @staticmethod
    def _position_payload(position: Position) -> dict[str, Any]:
        return {
            "front": int(position.front),
            "front_name": FRONT_NAMES[position.front],
            "rank": position.rank.value,
            "rank_name": RANK_NAMES[position.rank],
        }

    def _describe_action(
        self,
        action: Action,
        actor: int,
        *,
        private: bool = False,
    ) -> str:
        del private
        prefix = f"Player {actor + 1}"

        if isinstance(action, Pass):
            return f"{prefix} Passes."
        if isinstance(action, Discard):
            return (
                f"{prefix} discards "
                f"{self.cards[action.card_id]['title']} before drawing."
            )
        if isinstance(action, Maneuver):
            return (
                f"{prefix} Maneuvers a Named Formation from "
                f"{FRONT_NAMES[action.source.front]} "
                f"{RANK_NAMES[action.source.rank]} to "
                f"{FRONT_NAMES[action.destination.front]} "
                f"{RANK_NAMES[action.destination.rank]}."
            )
        if isinstance(action, PlayForce):
            return (
                f"{prefix} plays {self.cards[action.card_id]['title']} "
                f"as a Force in {FRONT_NAMES[action.position.front]} "
                f"{RANK_NAMES[action.position.rank]}."
            )
        if isinstance(action, PlayBond):
            return (
                f"{prefix} plays the Bond "
                f"{self.cards[action.card_id]['title']} in "
                f"{FRONT_NAMES[action.position.front]} "
                f"{RANK_NAMES[action.position.rank]}."
            )
        if isinstance(action, PlayName):
            return (
                f"{prefix} plays {self.cards[action.card_id]['title']} "
                f"as the Name in {FRONT_NAMES[action.position.front]} "
                f"{RANK_NAMES[action.position.rank]}."
            )
        if isinstance(action, PlayStory):
            title = self.cards[action.card_id]["title"]
            if action.ongoing_slot is not None:
                return (
                    f"{prefix} plays {title} as an ongoing Story."
                )
            if not action.targets:
                return f"{prefix} plays the Story {title}."
            targets = ", ".join(
                self._target_label(target)
                for target in action.targets
            )
            return (
                f"{prefix} plays the Story {title} targeting {targets}."
            )
        if isinstance(action, PlayStratagem):
            return (
                f"{prefix} plays "
                f"{self.cards[action.card_id]['title']} as their Stratagem."
            )
        return repr(action)

    def _legal_reason(self, action: Action) -> str:
        if isinstance(action, Pass):
            return (
                "Normally both players must have completed at least one "
                "operation before Pass is available, unless you have no other "
                "legal operation. Two consecutive Passes end the Battle; any "
                "intervening operation clears the earlier Pass."
            )
        if isinstance(action, Discard):
            return (
                "Your hand is already at the 10-card limit. Discard one card, "
                "then make the normal start-of-turn draw."
            )
        if isinstance(action, Maneuver):
            return (
                "Move this Named Formation one adjacent Front in the same rank "
                "for 1 Command."
            )
        if isinstance(action, PlayForce):
            return "This position can receive this Force."
        if isinstance(action, PlayBond):
            return (
                "This position has no Bond. A Bond may be prepared before "
                "its Force."
            )
        if isinstance(action, PlayName):
            return (
                "This position has no Name. A Name may be prepared before "
                "its Force or Bond."
            )
        if isinstance(action, PlayStory):
            if action.ongoing_slot is not None:
                return (
                    "You have an open ongoing Story slot. Each player may "
                    "have at most 2 ongoing Stories."
                )
            return "The Story has all targets required by its rules text."
        if isinstance(action, PlayStratagem):
            return (
                "You have not played a Stratagem this Battle. Pay its printed "
                "Command cost; it is public and uses your operation."
            )
        return "Legal according to the canonical game engine."

    @staticmethod
    def _target_label(target: BoardTarget) -> str:
        return (
            f"Player {target.player + 1} "
            f"{FRONT_NAMES[target.position.front]} "
            f"{RANK_NAMES[target.position.rank]}"
        )

    @staticmethod
    def _roman(value: int) -> str:
        return {
            1: "I",
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
            6: "VI",
            7: "VII",
            8: "VIII",
            9: "IX",
            10: "X",
        }.get(value, str(value))
