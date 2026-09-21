from __future__ import annotations

import json

import pytest
from pathlib import Path

from longwar.cards import load_card_file
from longwar.game import GameEngine
from longwar.simulate import simulate_games

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.integration


def test_random_games_finish() -> None:
    data = load_card_file(ROOT / "cards" / "cards.json")
    deck = json.loads(
        (ROOT / "decks" / "reference.json").read_text(encoding="utf-8")
    )["cards"]
    engine = GameEngine(data)

    report = simulate_games(engine, deck, deck, games=25, seed=99)

    assert sum(report.wins) == 25
    assert 0 <= report.first_player_wins <= 25
    assert report.max_turns < 500
