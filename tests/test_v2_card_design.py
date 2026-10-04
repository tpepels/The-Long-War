from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "cards" / "v2" / "cards.json").read_text(encoding="utf-8"))
CARDS = DATA["cards"]
DECKS = json.loads((ROOT / "cards" / "v2" / "playtest-decks.json").read_text(encoding="utf-8"))["decks"]
EXPECTED_COUNTS = {"force":30,"bond":22,"name":20,"hero":11,"tactic":14,"stratagem":11,"narrative":12}


def effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return [*card["modes"]["force"]["effects"], *card["modes"]["name"]["effects"]]
    return card.get("effects", [])


def force_mode_effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return card["modes"]["force"]["effects"]
    return card.get("effects", [])


def test_v2_pool_shape_and_decks() -> None:
    assert len(CARDS) == 120
    assert Counter(card["type"] for card in CARDS) == EXPECTED_COUNTS
    known = {card["id"]: card for card in CARDS}
    assert len(DECKS) == 6
    for deck in DECKS:
        assert sum(item["copies"] for item in deck["cards"]) == 34
        for item in deck["cards"]:
            card = known[item["id"]]
            assert item["copies"] <= (1 if card.get("unique") else 4)


def test_formation_vocabulary_and_timings_are_explicit() -> None:
    states = DATA["formation_states"]
    assert "Force" in states["bonded"] and "Bond" in states["bonded"]
    assert "Force + Bond + Name" in states["named"]
    assert "state, not a trigger" in states["bonded_state"]
    assert "state, not a trigger" in states["named_state"]
    assert "BECOMES NAMED" in states["becomes_named"]

    buried = {"play", "action", "reaction", "bonded", "while_named"}
    for card in CARDS:
        if card["type"] in {"force", "bond"}:
            for effect in card["effects"]:
                assert effect["timing"] in buried
                if effect["timing"] != "play":
                    assert effect.get("exposed")
        elif card["type"] == "hero":
            for effect in card["modes"]["force"]["effects"]:
                assert effect["timing"] in buried
                if effect["timing"] != "play":
                    assert effect.get("exposed")

    assert not any(effect["timing"] == "once_per_battle" for card in CARDS for effect in effects(card))
    assert not any(effect["timing"] == "resolution" for card in CARDS for effect in effects(card))


def test_once_per_battle_always_modifies_real_timing() -> None:
    for card in CARDS:
        for effect in effects(card):
            if effect.get("limit") == "once_per_battle":
                assert effect["timing"] in {"action", "reaction", "trigger"}, (card["title"], effect)


def test_limited_uses_are_not_automatic_strength_buttons() -> None:
    automatic = re.compile(
        r"^(?:This formation|This Bond|[A-Z][^.]*) (?:gets|has|contributes) [+-]\d+ "
        r"(?:additional )?Strength this Battle\.?$",
        re.I,
    )
    for card in CARDS:
        for effect in effects(card):
            if effect.get("limit") == "once_per_battle":
                assert not automatic.match(effect["text"]), (card["title"], effect["text"])


def test_card_family_mechanical_grammar() -> None:
    for card in CARDS:
        if card["type"] == "tactic":
            assert all(e["timing"] == "play" and e["scope"] == "opponent" for e in card["effects"])
        if card["type"] == "stratagem":
            assert all(e["timing"] == "hidden" and e["scope"] == "self" for e in card["effects"])
        if card["type"] == "narrative":
            assert all(e["timing"] in {"continuous", "action"} and e["scope"] == "self" for e in card["effects"])


def test_classification_vocabulary_is_complete_and_small() -> None:
    allowed = set(DATA["classification_vocabulary"])
    grouped = {name for names in DATA["classification_groups"].values() for name in names}
    assert grouped == allowed
    for card in CARDS:
        assert len(card.get("classes", [])) <= 3
        assert set(card.get("classes", [])) <= allowed
        assert set(card.get("references", [])) <= allowed


def test_movement_and_row_locks_remain_minor() -> None:
    movement = [c for c in CARDS if re.search(r"\b(?:move|moves|maneuver|maneuvers)\b", c.get("text", ""), re.I)]
    assert len(movement) <= DATA["design_limits"]["max_movement_cards"]
    restricted = [c for c in CARDS if c["type"] == "force" and c.get("placement")]
    assert len(restricted) <= DATA["design_limits"]["max_hard_row_restricted_forces"]


class Markup(HTMLParser):
    def __init__(self, markup: str):
        super().__init__(convert_charrefs=True)
        self.elements: list[dict] = []
        self.stack: list[dict] = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "text": "", "ancestors": self.stack.copy()}
        self.elements.append(node)
        if tag not in {"base", "br", "hr", "img", "input", "meta", "link"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        if self.stack:
            assert self.stack[-1]["tag"] == tag
            self.stack.pop()

    def handle_data(self, data):
        for node in self.stack:
            node["text"] += data

    def all(self, class_name: str, within=None) -> list[dict]:
        return [
            node for node in self.elements
            if class_name in node["attrs"].get("class", "").split()
            and (within is None or within in node["ancestors"])
        ]

    def one(self, class_name: str) -> dict:
        found = self.all(class_name)
        assert len(found) == 1, (class_name, len(found))
        return found[0]


def render_cards(cards: list[dict]) -> list[Markup]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js required for card renderer tests")
    script = r"""
const fs=require("node:fs");
global.window={location:{href:"https://example.test/cards-v2.html"}};
global.document={currentScript:null,getElementById:()=>null};
eval(fs.readFileSync("web/v2-heraldry.js","utf8"));
eval(fs.readFileSync("web/cards-v2.js","utf8"));
if(typeof window.V2Cards?.cardArticle!=="function")throw new Error("renderer export missing");
const input=JSON.parse(fs.readFileSync(0,"utf8"));
process.stdout.write(JSON.stringify(input.map(card=>window.V2Cards.cardArticle(card))));
"""
    result = subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        input=json.dumps(cards),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return [Markup(item) for item in json.loads(result.stdout)]


def test_renderer_preserves_all_rules_and_uses_symbolic_stack_edge() -> None:
    rendered = render_cards(CARDS)
    live_timings = {"action", "reaction", "bonded", "while_named"}

    for card, output in zip(CARDS, rendered, strict=True):
        assert output.one("v2-card")["attrs"]["data-card-id"] == card["id"]
        assert output.one("card-title")["text"] == card["title"]
        cost = output.one("cost-gem")
        cost_numbers = output.all("glyph-number", within=cost)
        assert len(cost_numbers) == 1
        assert cost_numbers[0]["text"] == str(card["command_cost"])
        assert [node["text"] for node in output.all("effect-text")] == [e["text"] for e in effects(card)]

        formation = card["type"] in {"force", "bond", "name", "hero"}
        assert bool(output.all("stack-edge")) is formation
        assert bool(output.all("event-crown")) is (not formation)

        if formation:
            edge = output.one("stack-edge")
            assert edge["attrs"].get("data-edge-layout") == "single-row"
            assert len(output.all("class-sigil", within=edge)) == len(card.get("classes", []))
            source = force_mode_effects(card) if card["type"] in {"force", "bond", "hero"} else []
            live = [e for e in source if e["timing"] in live_timings]
            assert len(output.all("edge-mechanic", within=edge)) == len(live)
            assert not output.all("edge-fallback", within=edge), card["id"]
        else:
            assert output.one("event-family")["text"] == card["type"].title()

        values = card.get("classes") or card.get("references") or []
        if values:
            class_line = output.one("class-line")["text"].lower()
            for value in values:
                assert value.replace("_", " ").replace("-", " ") in class_line


def test_every_current_live_buried_effect_has_icon_grammar() -> None:
    rendered = render_cards([c for c in CARDS if c["type"] in {"force", "bond", "hero"}])
    assert all(not output.all("edge-fallback") for output in rendered)


def test_v2_symbol_vocabulary_covers_every_classification() -> None:
    heraldry = (ROOT / "web" / "v2-heraldry.js").read_text(encoding="utf-8")
    for name in DATA["classification_vocabulary"]:
        assert f"{name}:" in heraldry, name
    assert "function classification(name)" in heraldry
    assert "function row(position)" in heraldry
    assert "function command(value" in heraldry


def test_v2_visual_contract_is_not_powerpoint_layout() -> None:
    css = (ROOT / "web" / "cards-v2.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    assert 'data-edge-layout="single-row"' in js
    assert "classificationIcons(card)" in js
    assert "use-socket" in js
    assert "isFormationCard(card)?stackEdge(card):eventCrown(card)" in js
    assert ".motif-field>svg,.motif-field>img{display:none!important}" in css
    assert ".effect-block+.effect-block" in css
    assert ".class-body-item" in css
    assert "COMMAND" not in js
    assert "function block(effect)function" not in js
    assert "const STACK_CASESconst STACK_CASES" not in js


def test_recovered_family_art_remains_the_only_art_layer() -> None:
    css = (ROOT / "web" / "cards-v2.css").read_text(encoding="utf-8")
    for asset in (
        "force-march.png", "bond-bound-spears.png", "name-tattered-banner.png",
        "hero-helmet-laurel.png", "tactic-archer-volley.png",
        "stratagem-war-map.png", "narrative-roadside-memorial.png",
    ):
        assert asset in css
        assert (ROOT / "web" / "art" / "v2" / asset).is_file()


def test_card_lab_loads_versioned_data() -> None:
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    assert 'cards-v2-redesign.json?v=' in js
    assert 'v2-playtest-decks.json?v=' in js
    assert 'cache:"no-cache"' in js
