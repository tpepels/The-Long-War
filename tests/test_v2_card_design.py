from __future__ import annotations

import copy
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

def test_v2_pool_is_120_cards() -> None:
    assert len(CARDS) == 120
    assert Counter(card["type"] for card in CARDS) == EXPECTED_COUNTS

def test_bonded_named_and_transition_are_explicit() -> None:
    states = DATA["formation_states"]
    assert "Force" in states["bonded"] and "Bond" in states["bonded"]
    assert "Force + Bond + Name" in states["named"]
    assert "state, not a trigger" in states["bonded_state"]
    assert "state, not a trigger" in states["named_state"]
    assert "BECOMES NAMED" in states["becomes_named"]

def test_buried_source_effects_declare_supported_timings_and_design_hints() -> None:
    allowed = {"play","action","reaction","bonded","while_named"}
    for card in CARDS:
        if card["type"] in {"force","bond"}:
            for effect in card["effects"]:
                assert effect["timing"] in allowed, card["title"]
                if effect["timing"] != "play":
                    assert effect.get("exposed"), card["title"]

def test_hero_force_mode_obeys_force_grammar() -> None:
    allowed = {"play","action","reaction","bonded","while_named"}
    for card in CARDS:
        if card["type"] == "hero":
            for effect in card["modes"]["force"]["effects"]:
                assert effect["timing"] in allowed, card["title"]
                if effect["timing"] != "play":
                    assert effect.get("exposed"), card["title"]

def test_names_are_visible_and_resolution_stays_clean() -> None:
    allowed = {"becomes_named","action","reaction","trigger","continuous","while_named"}
    for card in CARDS:
        if card["type"] == "name":
            assert all(e["timing"] in allowed for e in card["effects"])
    assert not any(e["timing"] == "resolution" for card in CARDS for e in effects(card))

def test_tactics_are_hostile_stratagems_and_narratives_are_self_support() -> None:
    for card in CARDS:
        if card["type"] == "tactic":
            assert all(e["timing"] == "play" and e["scope"] == "opponent" for e in card["effects"])
        if card["type"] == "stratagem":
            assert all(e["timing"] == "hidden" and e["scope"] == "self" for e in card["effects"])
        if card["type"] == "narrative":
            assert all(e["timing"] in {"continuous","action"} and e["scope"] == "self" for e in card["effects"])

def test_classifications_are_layered_and_top_line_stays_small() -> None:
    allowed = set(DATA["classification_vocabulary"])
    grouped = {x for values in DATA["classification_groups"].values() for x in values}
    assert grouped == allowed
    for card in CARDS:
        assert len(card.get("classes", [])) <= 3
        assert set(card.get("classes", [])) <= allowed
        assert set(card.get("references", [])) <= allowed

def test_core_packages_have_testable_depth() -> None:
    carriers=Counter(); refs=Counter()
    for card in CARDS:
        carriers.update(card.get("classes", [])); refs.update(card.get("references", []))
    for value in {"archer","guard","scout","rider","raider","captain"}:
        assert carriers[value] + refs[value] >= 7
    assert carriers["ship"] >= 2
    assert carriers["stronghold"] >= 2
    assert carriers["healer"] >= 2

def test_movement_and_row_locks_remain_minor() -> None:
    movement=[c for c in CARDS if re.search(r"\b(?:move|moves|maneuver|maneuvers)\b", c.get("text",""), re.I)]
    assert len(movement) <= DATA["design_limits"]["max_movement_cards"]
    assert len([c for c in CARDS if c["type"]=="force" and c.get("placement")]) <= DATA["design_limits"]["max_hard_row_restricted_forces"]

def test_no_obsolete_row_or_retreat_language() -> None:
    old=re.compile(r"\b(?:Frontline|Reserve|Retreat|driven off|drive off)\b",re.I)
    assert all(not old.search(c.get("text","")) for c in CARDS)

def test_every_card_has_playtest_tags() -> None:
    assert all(card.get("design_tags") for card in CARDS)

def test_diagnostic_decks_are_legal_34_card_experiments() -> None:
    known={c["id"]:c for c in CARDS}
    assert len(DECKS)==6
    for deck in DECKS:
        assert sum(x["copies"] for x in deck["cards"])==34
        for item in deck["cards"]:
            card=known[item["id"]]
            assert item["copies"] <= (1 if card.get("unique") else 4)


class CardMarkup(HTMLParser):
    def __init__(self, markup: str):
        super().__init__(convert_charrefs=True)
        self.markup = markup
        self.elements: list[dict] = []
        self.stack: list[dict] = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        element = {"tag": tag, "attrs": dict(attrs), "text": "", "ancestors": self.stack.copy()}
        self.elements.append(element)
        if tag not in {"base", "br", "hr", "img", "input", "meta", "link"}:
            self.stack.append(element)

    def handle_endtag(self, tag):
        if self.stack:
            assert self.stack[-1]["tag"] == tag
            self.stack.pop()

    def handle_data(self, value):
        for element in self.stack:
            element["text"] += value

    def all(self, class_name, within=None):
        return [e for e in self.elements if class_name in e["attrs"].get("class", "").split()
                and (within is None or within in e["ancestors"])]

    def one(self, class_name):
        matches = self.all(class_name)
        assert len(matches) == 1, (class_name, matches)
        return matches[0]


def render_cards(cards: list[dict], hero_mode: str = "force") -> list[CardMarkup]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the V2 physical-card renderer checks")
    script = r"""
const fs = require("node:fs");
global.window = {location: {href: "https://example.test/cards-v2.html"}};
global.document = {currentScript: null, getElementById: () => null};
const page = fs.readFileSync("web/cards-v2.html", "utf8");
for (const [, source] of page.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["']/g)) {
  eval(fs.readFileSync("web/" + source.split("?")[0], "utf8"));
}
if (typeof window.V2Cards?.cardArticle !== "function") throw new Error("Missing shared V2Cards.cardArticle renderer");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const before = JSON.stringify(input.cards);
function freeze(value) {
  if (value && typeof value === "object") {
    Object.values(value).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}
const rendered = input.cards.map(card => window.V2Cards.cardArticle(freeze(card), "", {heroMode: input.heroMode}));
if (JSON.stringify(input.cards) !== before) throw new Error("Rendering mutated source card data");
process.stdout.write(JSON.stringify(rendered));
"""
    result = subprocess.run(
        [node, "-e", script], cwd=ROOT, input=json.dumps({"cards": cards, "heroMode": hero_mode}),
        text=True, capture_output=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr
    return [CardMarkup(markup) for markup in json.loads(result.stdout)]


def stat_number(element: dict) -> int:
    numbers = re.findall(r"[+-]?\d+", element["text"])
    assert len(numbers) == 1, element["text"]
    return int(numbers[0])


def assert_stat(output: CardMarkup, class_name: str, value: int) -> None:
    values = {stat_number(element) for element in output.all(class_name)}
    assert values == {value}, (class_name, values)


def test_shared_v2_renderer_preserves_all_120_physical_card_contents() -> None:
    timing_labels = {
        "play": "PLAY", "action": "ACTION", "reaction": "REACTION", "bonded": "BONDED",
        "while_named": "WHILE NAMED", "becomes_named": "BECOMES NAMED",
        "trigger": "TRIGGER", "continuous": "CONTINUOUS", "hidden": "REVEAL",
    }
    for card, output in zip(CARDS, render_cards(CARDS), strict=True):
        outer = output.one("v2-card")
        edge = output.one("stack-edge")
        footer = output.one("card-footer")
        assert outer["attrs"]["data-card-id"] == card["id"]
        assert output.one("card-title")["text"] == card["title"]
        assert card["id"] in footer["text"]
        assert output.one("cost-gem")["text"] == str(card["command_cost"])
        assert footer in output.one("cost-gem")["ancestors"]
        assert edge in output.one("edge-classes")["ancestors"]
        classes = output.one("edge-classes")["text"].lower()
        for value in card.get("classes", []):
            assert value.replace("_", " ").replace("-", " ") in classes
        rule_texts = [e["text"] for e in output.all("effect-text", within=output.one("rules"))]
        assert rule_texts == [e["text"] for e in effects(card)], card["id"]
        assert [e["text"] for e in output.all("effect-label")] == [timing_labels[e["timing"]] for e in effects(card)]
        assert len(output.all("effect-limit")) == sum(e.get("limit") == "once_per_battle" for e in effects(card))
        if card.get("references"):
            byline = output.one("card-byline")["text"]
            assert "Involves " in byline
            for reference in card["references"]:
                assert reference.title() in byline
        if card.get("duration") == "this_battle":
            assert "This Battle" in output.one("card-byline")["text"]
        if card.get("placement"):
            assert card["placement"].upper() in edge["text"].upper()
        if card["type"] == "force":
            assert_stat(output, "stat-force", card["strength"])
        elif card["type"] == "hero":
            assert_stat(output, "stat-force", card["force_strength"])
            assert_stat(output, "stat-name", card["name_strength_modifier"])
        elif card["type"] in {"bond", "name"}:
            assert_stat(output, "stat-" + card["type"], card["strength_modifier"])
        if card["type"] in {"force", "bond", "hero"}:
            live = card.get("modes", {}).get("force", {}).get("effects", []) if card["type"] == "hero" else card["effects"]
            live = [e for e in live if e["timing"] != "play"]
            assert len(output.all("edge-live", within=edge)) == len(live), card["id"]


def test_hero_modes_keep_the_same_complete_physical_card() -> None:
    heroes = [card for card in CARDS if card["type"] == "hero"]
    force_cards = render_cards(heroes, "force")
    name_cards = render_cards(heroes, "name")
    for source, force, name in zip(heroes, force_cards, name_cards, strict=True):
        assert force.one("v2-card")["attrs"]["data-hero-mode"] == "force"
        assert name.one("v2-card")["attrs"]["data-hero-mode"] == "name"
        assert force.markup.replace('data-hero-mode="force"', 'data-hero-mode="name"') == name.markup
        assert force.one("rules")["text"] == name.one("rules")["text"]
        for output in (force, name):
            assert [e["text"] for e in output.all("effect-text")] == [e["text"] for e in effects(source)]
            assert_stat(output, "stat-force", source["force_strength"])
            assert_stat(output, "stat-name", source["name_strength_modifier"])


def test_renderer_preserves_zero_negative_numbers_and_escaped_text() -> None:
    card = copy.deepcopy(next(c for c in CARDS if c["type"] == "hero"))
    hostile = '<img src=x onerror="bad()"> & </script>'
    card.update(id=hostile, title=hostile, command_cost=0, force_strength=0, name_strength_modifier=-2)
    card["modes"]["force"]["effects"] = [{"timing": "play", "text": hostile}]
    output = render_cards([card])[0]
    assert output.one("v2-card")["attrs"]["data-card-id"] == hostile
    assert output.one("card-title")["text"] == hostile
    assert output.all("effect-text")[0]["text"] == hostile
    assert output.one("cost-gem")["text"] == "0"
    assert_stat(output, "stat-force", 0)
    assert_stat(output, "stat-name", -2)
    assert all("+-" not in element["text"] for element in output.all("stat-name"))
    assert not any(e["tag"] in {"img", "script"} for e in output.elements)


def test_unmapped_live_effects_are_never_replaced_with_incomplete_source_hints() -> None:
    card = copy.deepcopy(next(c for c in CARDS if c["type"] == "force"))
    long_text = "Choose another friendly formation in this Front. " * 12 + "It gets +3 Strength this Battle."
    card["effects"] = [
        {"timing": "action", "limit": "once_per_battle", "text": long_text, "exposed": "ACTION 1/B · +3"},
        {"timing": "while_named", "text": "This formation has +2 Strength while in the Rear.", "exposed": "NAMED · +2"},
    ]
    output = render_cards([card])[0]
    reminders = output.all("edge-live", within=output.one("stack-edge"))
    assert len(reminders) == 2
    assert long_text in reminders[0]["text"]
    assert "This formation has +2 Strength while in the Rear." in reminders[1]["text"]


def test_card_lab_loads_v2_cards_and_diagnostic_decks_without_stale_cache() -> None:
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    assert 'cards-v2-redesign.json?v=' in js
    assert 'v2-playtest-decks.json?v=' in js
    assert re.search(r'cache\s*:\s*["\']no-cache["\']', js)
    assert 'id="deck-filter"' in (ROOT / "web" / "cards-v2.html").read_text(encoding="utf-8")


def test_layout_fixture_includes_the_production_print_stamp(tmp_path, monkeypatch) -> None:
    from tools import build_pages
    from tools.check_card_layout import v2_layout_document

    page = tmp_path / "cards-v2.html"
    page.write_text((ROOT / "web" / "cards-v2.html").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(build_pages, "DIST", tmp_path)
    build_pages.stamp_print_version("layout-check")
    built = CardMarkup(page.read_text(encoding="utf-8"))
    fixture = CardMarkup(v2_layout_document(CARDS))
    assert fixture.one("print-version")["text"] == built.one("print-version")["text"]
    assert fixture.one("print-version")["attrs"] == built.one("print-version")["attrs"]
    for output in (built, fixture):
        versions = [element["attrs"]["content"] for element in output.elements
                    if element["tag"] == "meta" and element["attrs"].get("name") == "lw-build-version"]
        assert versions == ["layout-check"]


def test_once_per_battle_is_a_limit_not_a_timing_word() -> None:
    for card in CARDS:
        for effect in effects(card):
            assert effect["timing"] != "once_per_battle", card["title"]
            if effect.get("limit") == "once_per_battle":
                assert effect["timing"] in {"action", "reaction", "trigger"}, card["title"]


def test_buried_activated_abilities_create_an_action_or_reaction_choice() -> None:
    for card in CARDS:
        if card["type"] == "hero":
            source = card["modes"]["force"]["effects"]
        elif card["type"] in {"force", "bond"}:
            source = card["effects"]
        else:
            continue
        for effect in source:
            if effect["timing"] in {"action", "reaction"}:
                assert effect.get("limit") == "once_per_battle", card["title"]
                assert effect.get("exposed"), card["title"]


def test_no_limited_use_is_just_an_automatic_strength_pump() -> None:
    automatic_pump = re.compile(r"^(?:This formation|This Bond|[A-Z][^.]*) (?:gets|has|contributes) [+-]\d+ (?:additional )?Strength this Battle\.?$", re.I)
    for card in CARDS:
        for effect in effects(card):
            if effect.get("limit") == "once_per_battle":
                assert not automatic_pump.match(effect["text"]), (card["title"], effect["text"])


def test_continuous_rules_do_not_track_first_each_battle_or_turn() -> None:
    tracked_first = re.compile(r"\bfirst\b.*\b(?:Battle|turn)\b", re.I)
    for card in CARDS:
        for effect in effects(card):
            if effect["timing"] in {"continuous", "bonded", "while_named"}:
                assert not tracked_first.search(effect["text"]), (card["title"], effect["text"])


def test_v2_recovered_family_art_is_integrated() -> None:
    css = (ROOT / "web" / "cards-v2.css").read_text(encoding="utf-8")
    for asset in (
        "force-march.png", "bond-bound-spears.png", "name-tattered-banner.png",
        "hero-helmet-laurel.png", "tactic-archer-volley.png",
        "stratagem-war-map.png", "narrative-roadside-memorial.png",
    ):
        assert asset in css
        assert (ROOT / "web" / "art" / "v2" / asset).is_file()
    assert not list((ROOT / "web" / "art" / "v2").rglob("exec-*.png"))
    for preview in ("v2-formation-stacks.png", "v2-card-families.png"):
        assert (ROOT / "web" / "art" / "v2" / "previews" / preview).is_file()


def test_v2_stack_lab_includes_force_alone_and_all_compositions() -> None:
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    for case in ("force-alone", "force-bond", "force-name", "hero-force", "hero-name"):
        assert f'"{case}"' in js
    assert re.search(r"\bnamed\s*:", js)


def test_v2_stack_edge_is_one_row_and_generated_art_has_no_overlay() -> None:
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    css = (ROOT / "web" / "cards-v2.css").read_text(encoding="utf-8")
    assert 'data-edge-layout="single-row"' in js
    assert "edge-heading" not in js
    assert "edge-reminders" not in js
    assert "V2Heraldry?.motif" not in js
    assert '<div class="motif-field" aria-hidden="true"></div>' in js
    assert ".motif-field > svg, .motif-field > img" in css
    assert "display: none !important" in css
    assert "grid-template-columns: auto minmax(0, 1fr) auto" in css


def test_v2_rules_and_art_are_separate_layout_regions() -> None:
    css = (ROOT / "web" / "cards-v2.css").read_text(encoding="utf-8")
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    assert ".rules { min-height: 0; flex: 1 1 auto; overflow: hidden;" in css
    assert "art-rules-overlap" in js
    assert "art-overlay" in js
    assert ".very-dense .motif-field" in css


def test_v2_footer_has_no_decorative_product_label() -> None:
    js = (ROOT / "web" / "cards-v2.js").read_text(encoding="utf-8")
    assert "The Long War · V2" not in js
    assert "V2 · Hero · Unique" not in js
