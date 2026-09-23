from __future__ import annotations

import json
from typing import Any

from .agents.heuristic_agent import HeuristicAgent
from .agents.online_mccfr_agent import OnlineMCCFRAgent
from .game.actions import (
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
from .game.engine import GameEngine, all_positions
from .game.model import Front, Phase, Position, Rank
from .mccfr import action_key


FRONT_NAMES = {
    Front.LEFT: "Left",
    Front.CENTER: "Center",
    Front.RIGHT: "Right",
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
    ):
        if mode not in {"hotseat", "heuristic", "online_mccfr"}:
            raise ValueError(f"Unsupported play mode: {mode}")

        card_data = json.loads(card_data_json)
        deck_payload = json.loads(deck_json)
        deck = list(deck_payload["cards"]) if isinstance(deck_payload, dict) else list(deck_payload)

        self.engine = GameEngine(card_data)
        self.cards = self.engine.cards
        self.deck = deck
        self.mode = mode
        self.seed = int(seed)
        self.human_players = {0, 1} if mode == "hotseat" else {0}
        self.log: list[str] = []

        # Preview state exposes the reproducible opening hands before mulligans.
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
        if mode == "heuristic":
            self.agents[1] = HeuristicAgent(self.seed + 20_001, exploration=0.0)
        elif mode == "online_mccfr":
            self.agents[1] = OnlineMCCFRAgent(
                self.engine,
                self.seed + 30_001,
                iterations=4,
                max_depth=2,
                deterministic=True,
            )

    def snapshot_json(self, viewer: int | None = None) -> str:
        return json.dumps(self.snapshot(viewer), separators=(",", ":"))

    def act_json(self, key: str, viewer: int) -> str:
        return json.dumps(self.act(key, viewer), separators=(",", ":"))

    def mulligan_json(self, indices: list[int], viewer: int) -> str:
        return json.dumps(self.mulligan(indices, viewer), separators=(",", ":"))

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
        self.log.append(
            f"Battle I begins. Player {self.state.active_player + 1} goes first "
            "and draws 1 additional opening card."
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
        action = next((item for item in legal if action_key(item) == key), None)
        if action is None:
            raise ValueError("That action is no longer legal")

        self._apply_with_log(action)
        self._run_ai_until_human()
        if self.mode == "hotseat":
            # A Stratagem is a free pre-action deployment. Keep the same
            # player's hand visible so they can still take their normal action.
            return self.snapshot(
                viewer if isinstance(action, SetStratagem) else None
            )
        return self.snapshot(0)

    def snapshot(self, viewer: int | None = None) -> dict[str, Any]:
        state = self.state
        if viewer is not None and viewer not in (0, 1):
            raise ValueError("viewer must be 0, 1, or null")

        display_active = self.mulligan_player if not self.setup_complete else state.active_player
        display_phase = "mulligan" if not self.setup_complete else state.phase.value

        players = []
        for ps in state.players:
            players.append({
                "victories": ps.victories,
                "passed": ps.passed,
                "hand_count": len(ps.hand),
                "deck_count": len(ps.deck),
                "discard": list(ps.discard),
            })

        board: list[list[dict[str, Any]]] = [[], []]
        for owner in range(2):
            for position in all_positions():
                slot = state.slot(owner, position)
                board[owner].append({
                    "front": int(position.front),
                    "front_name": FRONT_NAMES[position.front],
                    "rank": position.rank.value,
                    "rank_name": RANK_NAMES[position.rank],
                    "subject": slot.subject,
                    "link": slot.link,
                    "name": slot.name,
                    "complete": slot.complete,
                    "strength": self.engine.position_strength(state, owner, position),
                })

        schemes: list[list[dict[str, Any] | None]] = [[], []]
        for owner in range(2):
            for front in Front:
                scheme = state.scheme(owner, front)
                if scheme is None:
                    schemes[owner].append(None)
                elif viewer == owner or scheme.revealed:
                    schemes[owner].append({
                        "hidden": False,
                        "card_id": scheme.card_id,
                        "revealed": scheme.revealed,
                    })
                else:
                    schemes[owner].append({
                        "hidden": True,
                        "card_id": None,
                        "revealed": False,
                    })

        stratagems: list[dict[str, Any] | None] = []
        for owner in range(2):
            stratagem = state.stratagem(owner)
            if stratagem is None:
                stratagems.append(None)
            elif viewer == owner or stratagem.revealed:
                stratagems.append({
                    "hidden": False,
                    "card_id": stratagem.card_id,
                    "revealed": stratagem.revealed,
                })
            else:
                stratagems.append({
                    "hidden": True,
                    "card_id": None,
                    "revealed": False,
                })

        front_strengths = [
            [self.engine.front_strength(state, player, front) for front in Front]
            for player in range(2)
        ]
        front_control = []
        for front in Front:
            p0 = front_strengths[0][int(front)]
            p1 = front_strengths[1][int(front)]
            front_control.append(0 if p0 > p1 else 1 if p1 > p0 else None)

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
            and viewer == state.active_player
            and viewer in self.human_players
            and state.phase is not Phase.COMPLETE
        ):
            hand = list(state.players[viewer].hand)
            legal_actions = [self._action_view(action) for action in self.engine.legal_actions(state)]

        return {
            "mode": self.mode,
            "seed": self.seed,
            "battle": state.battle,
            "phase": display_phase,
            "active_player": display_active,
            "chooser": state.chooser if self.setup_complete else None,
            "winner": state.winner,
            "viewer": viewer,
            "needs_reveal": (
                self.mode == "hotseat"
                and viewer is None
                and (not self.setup_complete or state.phase is not Phase.COMPLETE)
            ),
            "mulligan_available": (
                not self.setup_complete
                and viewer is not None
                and viewer == self.mulligan_player
            ),
            "mulligan_limit": 2,
            "players": players,
            "board": board,
            "schemes": schemes,
            "stratagems": stratagems,
            "stratagem_used": list(state.stratagem_used),
            "draw_used": list(state.draw_used),
            "front_strengths": front_strengths,
            "front_control": front_control,
            "hand": hand,
            "legal_actions": legal_actions,
            "log": self.log[-40:],
        }

    def _run_ai_until_human(self) -> None:
        if not self.setup_complete:
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
            action = self.agents[actor].choose(self.engine, self.state)
            self._apply_with_log(action)

    def _apply_with_log(self, action: Action) -> None:
        actor = self.state.active_player
        battle_before = self.state.battle
        victories_before = [player.victories for player in self.state.players]
        observations_before = len(self.state.observations)
        label = self._describe_action(action, actor)

        self.engine.apply(self.state, action)
        self.log.append(label)

        for event in self.state.observations[observations_before:]:
            if event.kind != "reveal":
                continue
            if event.zone == "stratagem":
                self.log.append(
                    f"Stratagem revealed: {self.cards[event.card_id]['title']}."
                )
            else:
                self.log.append(
                    f"Veiled Story revealed: {self.cards[event.card_id]['title']}."
                )

        battle_winner = next(
            (
                player
                for player in range(2)
                if self.state.players[player].victories > victories_before[player]
            ),
            None,
        )
        if battle_winner is not None:
            self.log.append(
                f"Player {battle_winner + 1} wins Battle {self._roman(battle_before)}."
            )

        if self.state.phase is Phase.COMPLETE:
            self.log.append(f"Player {self.state.winner + 1} wins the match.")
        elif self.state.battle != battle_before:
            self.log.append(
                f"Battle {self._roman(self.state.battle)} begins. "
                f"Player {self.state.chooser + 1} chooses who starts."
            )

    def _action_view(self, action: Action) -> dict[str, Any]:
        card_id = getattr(action, "card_id", None)
        payload: dict[str, Any] = {
            "key": action_key(action),
            "kind": type(action).__name__,
            "card_id": card_id,
            "label": self._describe_action(action, self.state.active_player, private=True),
            "reason": self._legal_reason(action),
            "position": None,
            "front": None,
            "targets": [],
            "move_to": None,
            "choose_player": None,
        }

        if isinstance(action, (PlaySubject, PlayLink, PlayName)):
            payload["position"] = self._position_payload(action.position)
        if isinstance(action, PlayName) and action.move_to is not None:
            payload["move_to"] = self._position_payload(action.move_to)
        if isinstance(action, PlayScheme):
            payload["front"] = int(action.front)
        if isinstance(action, PlayPlot):
            payload["targets"] = [
                {"player": target.player, **self._position_payload(target.position)}
                for target in action.targets
            ]
        if isinstance(action, ChooseFirst):
            payload["choose_player"] = action.player
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
        prefix = f"Player {actor + 1}"
        if isinstance(action, Pass):
            return f"{prefix} Passes."
        if isinstance(action, Draw):
            return f"{prefix} draws 1 card."
        if isinstance(action, ChooseFirst):
            return f"{prefix} chooses Player {action.player + 1} to start the next Battle."
        if isinstance(action, PlaySubject):
            return (
                f"{prefix} plays {self.cards[action.card_id]['title']} "
                f"to {FRONT_NAMES[action.position.front]} {RANK_NAMES[action.position.rank]}."
            )
        if isinstance(action, PlayLink):
            return (
                f"{prefix} attaches the Bond {self.cards[action.card_id]['title']} "
                f"in {FRONT_NAMES[action.position.front]}."
            )
        if isinstance(action, PlayName):
            move = ""
            if action.move_to is not None:
                move = (
                    f" and moves that Subject and its attachments to "
                    f"{FRONT_NAMES[action.move_to.front]} {RANK_NAMES[action.move_to.rank]}"
                )
            return (
                f"{prefix} attaches {self.cards[action.card_id]['title']} "
                f"as the Name in {FRONT_NAMES[action.position.front]}{move}."
            )
        if isinstance(action, PlayScheme):
            if private:
                return (
                    f"Set {self.cards[action.card_id]['title']} face-down "
                    f"in {FRONT_NAMES[action.front]}."
                )
            return f"{prefix} sets a face-down Story in {FRONT_NAMES[action.front]}."
        if isinstance(action, SetStratagem):
            if private:
                return (
                    f"Set {self.cards[action.card_id]['title']} face-down "
                    "as your Stratagem."
                )
            return f"{prefix} sets a face-down Stratagem."
        if isinstance(action, PlayPlot):
            title = self.cards[action.card_id]["title"]
            if not action.targets:
                return f"{prefix} plays {title}."
            targets = ", ".join(self._target_label(target) for target in action.targets)
            return f"{prefix} plays {title} targeting {targets}."
        return repr(action)

    def _legal_reason(self, action: Action) -> str:
        if isinstance(action, Pass):
            return "Pass is always legal while you are still active in the Battle."
        if isinstance(action, Draw):
            return "Draw 1 card as your normal action. You may do this once per Battle."
        if isinstance(action, ChooseFirst):
            return "The previous Battle loser chooses who takes the first turn."
        if isinstance(action, PlaySubject):
            return "This is an empty legal Subject position."
        if isinstance(action, PlayLink):
            return "This Subject has no Bond yet."
        if isinstance(action, PlayName):
            return "This Subject has a Bond and no Name attached yet."
        if isinstance(action, PlayScheme):
            return "You have no Veiled Story in this Front."
        if isinstance(action, SetStratagem):
            return (
                "You have not set a Stratagem this Battle. Setting it is free "
                "and you still take your normal action."
            )
        if isinstance(action, PlayPlot):
            return "The Story has all targets required by its rules text."
        return "Legal according to the canonical game engine."

    @staticmethod
    def _target_label(target: BoardTarget) -> str:
        return (
            f"Player {target.player + 1} "
            f"{FRONT_NAMES[target.position.front]} {RANK_NAMES[target.position.rank]}"
        )

    @staticmethod
    def _roman(value: int) -> str:
        return {1: "I", 2: "II", 3: "III"}.get(value, str(value))
