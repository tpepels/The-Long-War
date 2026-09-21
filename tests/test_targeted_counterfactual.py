from __future__ import annotations

from longwar.targeted_counterfactual import select_targets


def broad_fixture():
    return {
        "cards": [
            {
                "id": "a",
                "title": "A",
                "delta_win_probability": 0.02,
                "ci95": [-0.02, 0.06],
                "level": "green",
                "confidence_excludes_zero": False,
            },
            {
                "id": "b",
                "title": "B",
                "delta_win_probability": 0.09,
                "ci95": [0.02, 0.15],
                "level": "red",
                "confidence_excludes_zero": True,
            },
        ],
        "pairs": [
            {
                "cards": ["a", "b"],
                "title": "A × B",
                "interaction_delta": -0.06,
                "ci95": [-0.13, 0.01],
                "level": "yellow",
                "confidence_excludes_zero": False,
            },
        ],
        "triples": [],
    }


def test_selector_prefers_supported_and_large_signals() -> None:
    selected = select_targets(
        broad_fixture(),
        max_cards=1,
        max_pairs=1,
        max_triples=0,
        minimum_abs_effect=0.05,
    )
    assert [(row.kind, row.cards) for row in selected] == [
        ("card", ("b",)),
        ("pair", ("a", "b")),
    ]


def test_selector_can_force_top_target_for_ci_smoke() -> None:
    broad = broad_fixture()
    broad["cards"][0]["delta_win_probability"] = 0.0
    broad["cards"][0]["level"] = "green"
    broad["cards"][1]["delta_win_probability"] = 0.0
    broad["cards"][1]["level"] = "green"
    broad["cards"][1]["confidence_excludes_zero"] = False
    broad["pairs"] = []

    selected = select_targets(
        broad,
        max_cards=1,
        max_pairs=0,
        max_triples=0,
        minimum_abs_effect=0.5,
        force_top=True,
    )
    assert len(selected) == 1
    assert selected[0].kind == "card"
