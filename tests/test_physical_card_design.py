from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tools import check_card_layout

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
CARDS = DATA["cards"]
DECK_DATA = json.loads((ROOT / "cards" / "playtest-decks.json").read_text(encoding="utf-8"))
DECKS = DECK_DATA["decks"]
EXPECTED_COUNTS = {"force":33,"bond":24,"name":20,"hero":11,"tactic":14,"order":6,"stratagem":11,"narrative":12}


def effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return [*card["modes"]["force"]["effects"], *card["modes"]["name"]["effects"]]
    return card.get("effects", [])


def force_mode_effects(card: dict) -> list[dict]:
    if card["type"] == "hero":
        return card["modes"]["force"]["effects"]
    return card.get("effects", [])


def test_pool_shape_and_decks() -> None:
    assert len(CARDS) == 131
    assert Counter(card["type"] for card in CARDS) == EXPECTED_COUNTS
    known = {card["id"]: card for card in CARDS}
    assert DECK_DATA["deck_size"] == 48
    assert DECK_DATA["status"] == "exploratory-combo-playtest-decks"
    assert len(DECKS) == 4
    for deck in DECKS:
        assert sum(item["copies"] for item in deck["cards"]) == DECK_DATA["deck_size"]
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

    buried = {"play", "action", "reaction", "bonded", "while_named", "front", "middle", "rear", "exhausted", "tireless", "mobile", "continuous"}
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


def test_bond_cleanup_leaves_no_dead_limited_ability_targets() -> None:
    bonds = [card for card in CARDS if card["type"] == "bond"]
    assert not any(
        effect.get("limit") == "once_per_battle"
        for card in bonds
        for effect in card.get("effects", [])
    )

    line_wheeled = next(card for card in CARDS if card["id"] == "the-line-wheeled")
    assert "non-PLAY text is ignored" in line_wheeled["text"]
    assert "1/BATTLE ability" not in line_wheeled["text"]


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


def test_press_and_supply_raids_have_canonical_machine_rules() -> None:
    by_id = {card["id"]: card for card in CARDS}
    vocab = DATA["position_vocabulary"]

    assert "opposing Force" in vocab["press"]
    assert "active, unsuppressed SUPPLY" in vocab["supply_raid"]
    assert "not below 1" in vocab["steal_command"]

    assert by_id["the-river-raiders"]["text"] == "CONTINUOUS - PRESS +1."
    assert by_id["the-fifty-men"]["title"] == "The Fifty Men"
    assert not by_id["the-fifty-men"].get("design_rules", {}).get("effects")
    assert by_id["the-ash-bowmen"]["title"] == "The Wolf Skirmishers"
    assert by_id["the-ash-bowmen"]["design_rules"]["effects"][0]["requires_opposing_exhausted_same_front"] is True
    assert by_id["the-black-company"]["title"] == "The Black Pursuers"
    assert by_id["the-black-company"]["effects"][0]["timing"] == "exhausted"

    reavers = by_id["the-unnamed-host"]
    assert reavers["title"] == "The Salt-Road Reavers"
    raid = reavers["design_rules"]["effects"][0]
    assert raid["op"] == "steal_command"
    assert raid["requires_opposing_supply_same_front"] is True
    assert raid["minimum"] == 1

    spoils = by_id["shared-the-spoils-with"]["design_rules"]["effects"][0]
    assert spoils["requires_opposing_supply_same_front"] is True


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
    restricted = [c for c in CARDS if c["type"] == "force" and (c.get("placement") or c.get("allowed_rows"))]
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
global.window={location:{href:"https://example.test/cards.html"}};
global.document={currentScript:null,getElementById:()=>null};
eval(fs.readFileSync("web/card-symbols.js","utf8"));
eval(fs.readFileSync("web/physical-cards.js","utf8"));
if(typeof window.PhysicalCards?.cardArticle!=="function")throw new Error("renderer export missing");
const input=JSON.parse(fs.readFileSync(0,"utf8"));
process.stdout.write(JSON.stringify(input.map(card=>window.PhysicalCards.cardArticle(card))));
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
    live_timings = {
        "action",
        "reaction",
        "bonded",
        "while_named",
        "front",
        "middle",
        "rear",
        "exhausted",
        "tireless",
        "continuous",
        "mobile",
    }

    for card, output in zip(CARDS, rendered, strict=True):
        assert output.one("physical-card")["attrs"]["data-card-id"] == card["id"]
        assert output.one("card-title")["text"] == card["title"]
        cost = output.one("cost-gem")
        assert cost["text"] == str(card["command_cost"])
        assert not output.all("seal-inner", within=cost)
        assert not any(node["tag"] == "svg" and cost in node["ancestors"] for node in output.elements)
        assert [node["text"] for node in output.all("effect-text")] == [e["text"] for e in effects(card)]

        formation = card["type"] in {"force", "bond", "name", "hero"}
        assert bool(output.all("stack-edge")) is formation
        assert bool(output.all("event-crown")) is (not formation)

        if formation:
            edge = output.one("stack-edge")
            assert edge["attrs"].get("data-edge-layout") == "three-zone"
            assert len(output.all("edge-zone", within=edge)) == 3
            stats = output.one("hero-stats" if card["type"] == "hero" else "edge-stats")
            values = [node["text"] for node in output.elements if node["tag"] == "b" and stats in node["ancestors"]]
            if card["type"] == "hero":
                assert values == [str(card["force_strength"]), f"{card['name_strength_modifier']:+d}"]
            elif card["type"] == "force":
                assert values == [str(card["strength"])]
            else:
                assert values == [f"{card['strength_modifier']:+d}"]
            assert len(output.all("class-sigil", within=edge)) == len(card.get("classes", []))
            source = force_mode_effects(card) if card["type"] in {"force", "bond", "hero"} else []
            live = [e for e in source if e["timing"] in live_timings]
            assert len(output.all("edge-mechanic", within=edge)) == len(live)
            assert len(output.all("edge-live-text", within=edge)) == len(live)
        else:
            assert output.one("event-family")["text"] == card["type"].title()

        class_line = output.one("class-line")
        assert card["type"].title() in class_line["text"]
        type_items = output.all("class-type-item", within=class_line)
        assert len(type_items) == 1
        assert type_items[0]["text"] == card["type"].title()

        values = card.get("classes") or card.get("references") or []
        if card["type"] == "tactic":
            assert "Involves" not in class_line["text"]
            inline_refs = output.all("inline-class-ref")
            for value in card.get("references", []):
                label = value.replace("_", " ").replace("-", " ").title()
                assert any(node["attrs"].get("title") == label for node in inline_refs)
        elif values:
            class_text = class_line["text"].lower()
            for value in values:
                assert value.replace("_", " ").replace("-", " ") in class_text


def test_every_current_live_buried_effect_has_a_compact_exposed_reminder() -> None:
    rendered = render_cards([c for c in CARDS if c["type"] in {"force", "bond", "hero"}])
    for output in rendered:
        for mechanic in output.all("edge-mechanic"):
            reminders = output.all("edge-live-text", within=mechanic)
            assert len(reminders) == 1
            assert reminders[0]["text"].strip()


def test_symbol_vocabulary_covers_every_classification() -> None:
    heraldry = (ROOT / "web" / "card-symbols.js").read_text(encoding="utf-8")
    for name in DATA["classification_vocabulary"]:
        assert f"{name}:" in heraldry, name
    assert "function classification(name)" in heraldry
    assert "function row(position)" in heraldry
    assert "function command(value" in heraldry


def test_shared_card_regions_keep_art_clear_and_commands_numeric() -> None:
    for card, output in zip(CARDS, render_cards(CARDS), strict=True):
        art = output.one("motif-field")
        assert not any(art in node["ancestors"] for node in output.elements)
        assert not output.all("command-label")
        assert output.one("cost-gem")["text"] == str(card["command_cost"])
        assert len(output.all("effect-block")) == len(effects(card))




def test_all_per_card_art_is_wired_into_renderer() -> None:
    js = (ROOT / "web" / "physical-cards.js").read_text(encoding="utf-8")
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")

    # Per-card art follows the card-id filename convention rather than a
    # hand-maintained registry. Build validation requires matching artwork.
    assert 'const artBase=options.printArt?"art/cards-print/":"art/cards/"' in js
    assert 'const artExt=options.printArt?".webp":".png"' in js
    assert "const artId=String(card.art_id||card.id);" in js
    assert "--card-art:url(" in js
    assert "CARD_ART" not in js
    assert "var(--card-art,none)" in css

    art_ids = sorted(
        path.stem
        for path in (ROOT / "web" / "art" / "cards").glob("*.png")
    )
    known = {card["id"] for card in CARDS}
    required_art = {card.get("art_id", card["id"]) for card in CARDS}
    assert len(known) == 131
    assert required_art == set(art_ids)
    for card in CARDS:
        if card.get("art_id"):
            assert card["art_id"] in art_ids

def test_multi_effect_heroes_receive_dense_layout() -> None:
    rendered = render_cards([c for c in CARDS if c["type"] == "hero" and len(effects(c)) >= 3])
    for output in rendered:
        classes = output.one("physical-card")["attrs"]["class"].split()
        assert "dense" in classes or "very-dense" in classes


def test_exposed_row_preserves_classification_icons_before_reminder_width() -> None:
    formation = [card for card in CARDS if card["type"] in {"force", "bond", "name", "hero"}]
    for card, output in zip(formation, render_cards(formation), strict=True):
        identity = output.one("edge-identity")
        reminders = output.one("edge-live-group")
        assert output.elements.index(identity) < output.elements.index(reminders)
        assert [node["attrs"]["data-class"] for node in output.all("class-sigil", within=identity)] == card.get("classes", [])



def test_nonformation_header_uses_its_family_symbol_and_name() -> None:
    events = [card for card in CARDS if card["type"] not in {"force", "bond", "name", "hero"}]
    for card, output in zip(events, render_cards(events), strict=True):
        crown = output.one("event-crown")
        assert output.one("event-sigil") in output.all("event-sigil", within=crown)
        assert output.one("event-family")["text"] == card["type"].title()





def test_every_family_uses_shared_art_identity_rules_and_footer_structure() -> None:
    for output in render_cards(CARDS):
        body = output.one("card-body")
        regions = [output.one(name) for name in ("motif-field", "card-identity", "rules")]
        assert [node for node in output.elements if node["ancestors"] and node["ancestors"][-1] is body] == regions
        identity = output.one("card-identity")
        assert identity in output.one("card-title")["ancestors"]
        footer = output.one("card-footer")
        if output.all("class-line"):
            class_line = output.one("class-line")
            assert footer in class_line["ancestors"]
            assert body not in class_line["ancestors"]
            assert identity not in class_line["ancestors"]
        assert footer in output.one("cost-gem")["ancestors"]


def test_shared_raster_decoration_assets_exist() -> None:
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")
    for asset in ("card-shell", "art-window", "title-divider", "command-seal"):
        assert f'art/card-frame/{asset}.png' in css
        assert (ROOT / "web" / "art" / "card-frame" / f"{asset}.png").is_file()


def test_cards_without_effects_do_not_print_placeholder_rules() -> None:
    cards = [{**next(card for card in CARDS if card["type"] == family), "effects": []}
             for family in EXPECTED_COUNTS if family != "hero"]
    for output in render_cards(cards):
        assert output.one("rules")["text"] == ""
        assert not output.all("empty-rules")


@pytest.mark.parametrize(
    ("override", "expected"),
    [("0%", "0%"), ("100%", "100%"), ("37.5%", "37.5%"), (" 12.5% ", "12.5%"),
     (None, "50%"), (0, "50%"), ("-1%", "50%"), ("101%", "50%"),
     ("1e2%", "50%"), ("calc(50%)", "50%"), ('50%;color:red;\" onload=\"bad()', "50%")],
)
def test_art_focus_emits_only_safe_percentages(override, expected: str) -> None:
    force = next(card for card in CARDS if card["type"] == "force")
    output = render_cards([{**force, "art_focus_x": override, "art_focus_y": override}])[0]
    attrs = output.one("physical-card")["attrs"]
    assert attrs["style"].endswith(f";--art-x:{expected};--art-y:{expected}")
    assert "onload" not in attrs


def test_layout_probes_cover_dense_rules_and_long_titles_in_every_family_without_changing_cards() -> None:
    original = json.dumps(CARDS, sort_keys=True)
    probes = check_card_layout.physical_layout_probes(CARDS)
    assert Counter(card["type"] for card in probes) == dict.fromkeys(EXPECTED_COUNTS, 2)
    for card, output in zip(probes, render_cards(probes), strict=True):
        classes = output.one("physical-card")["attrs"]["class"].split()
        if card["id"].startswith("dense-"):
            assert 170 < sum(len(effect["text"]) for effect in effects(card)) <= 250
            assert {"dense", "very-dense"}.intersection(classes)
        else:
            assert len(card["title"]) >= 32
            assert "title-very-long" in classes
        assert [node["text"] for node in output.all("effect-text")] == [effect["text"] for effect in effects(card)]
        assert output.one("card-title")["text"] == card["title"]
    assert json.dumps(CARDS, sort_keys=True) == original


@pytest.mark.parametrize(
    ("override", "failure"),
    [
        (".physical-card .motif-field{height:19mm;min-height:19mm;max-height:19mm;flex-basis:19mm}", "art-height"),
        (".physical-card .motif-field{order:2}", "title-before-art"),
        (".physical-card .class-line{visibility:hidden}", "classification-hidden"),
        (".physical-card .class-body-item>span{visibility:hidden}", "classification-hidden"),
        (".physical-card .class-line{transform:translateX(80mm)}", "classification-outside"),
        (".physical-card .edge-live-text{width:1mm;max-width:1mm;flex:0 0 1mm;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}", "edge-live-text-overflow"),
        (".physical-card .cost-gem{background:none}", "missing-command-seal"),
        (".physical-card .event-crown{height:12mm;flex-basis:12mm}", "edge-height"),
    ],
)
def test_physical_geometry_guard_detects_region_failures_across_families(tmp_path, override: str, failure: str) -> None:
    browser = check_card_layout.browser_path()
    if browser is None:
        pytest.skip("Chrome/Chromium required for geometry guard regression")
    document = check_card_layout.physical_layout_document(CARDS)
    document = document.replace("</head>", f"<style>{override}</style></head>")
    path = tmp_path / "family-region-probe.html"
    path.write_text(document, encoding="utf-8")
    result = check_card_layout.run_browser(browser, path)
    assert result.returncode == 0, result.stderr
    match = re.search(r'<div id="layout-result">([^<]*)</div>', result.stdout)
    assert match is not None, result.stdout[-1000:]
    failures = {entry.split(":", 1)[0] for entry in match.group(1).split(";") if entry.endswith(":" + failure)}
    expected = CARDS
    if failure.startswith("classification-"):
        expected = [card for card in CARDS if card.get("classes") or card.get("references")]
    elif failure == "edge-live-text-overflow":
        expected = [card for card in CARDS if card["type"] in {"force", "bond", "hero"}
                    and any(effect.get("exposed") for effect in force_mode_effects(card))]
    elif failure == "edge-height":
        expected = [card for card in CARDS if card["type"] not in {"force", "bond", "name", "hero"}]
    assert expected
    assert {card["id"] for card in expected} <= failures


def test_force_art_has_an_exact_or_explicit_temporary_source() -> None:
    cards = json.loads((ROOT / "cards" / "cards.json").read_text(encoding="utf-8"))
    cards = cards if isinstance(cards, list) else cards["cards"]
    art_ids = {
        path.stem
        for path in (ROOT / "web" / "art" / "cards").glob("*.png")
    }
    for card in (card for card in cards if card["type"] == "force"):
        assert card.get("art_id", card["id"]) in art_ids


def test_dense_hero_rules_preserve_both_modes() -> None:
    heroes = [card for card in CARDS if card["type"] == "hero"]
    for card, output in zip(heroes, render_cards(heroes), strict=True):
        classes = output.one("physical-card")["attrs"]["class"].split()
        if sum(len(effect["text"]) for effect in effects(card)) > 180:
            assert "very-dense" in classes
        assert [node["attrs"]["data-mode"] for node in output.all("hero-rule-mode")] == ["force", "name"]
        for mode in output.all("hero-rule-mode"):
            assert [node["text"] for node in output.all("effect-text", within=mode)] == [
                effect["text"] for effect in card["modes"][mode["attrs"]["data-mode"]]["effects"]
            ]


def test_doros_is_promoted_to_very_dense_layout() -> None:
    card = next(card for card in CARDS if card["id"] == "doros-the-last-spear")
    es = effects(card)
    chars = sum(len(effect.get("text", "")) for effect in es)
    assert len(es) == 3
    assert chars > 120
    assert "very-dense" in render_cards([card])[0].one("physical-card")["attrs"]["class"].split()


def test_hero_mode_headers_pair_each_mode_with_its_symbol() -> None:
    for output in render_cards([card for card in CARDS if card["type"] == "hero"]):
        modes = output.all("hero-rule-mode")
        for mode, label in zip(modes, ("Force", "Name"), strict=True):
            heading, = output.all("mode-heading", within=mode)
            core, = output.all("mode-heading-core", within=heading)
            assert core["text"].strip().endswith(label)
            assert "As " not in core["text"]
            assert any(node["tag"] == "svg" and core in node["ancestors"] for node in output.elements)


def test_art_focus_defaults_and_overrides() -> None:
    js = (ROOT / "web" / "physical-cards.js").read_text(encoding="utf-8")
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")
    assert "function artFocus(value,fallback)" in js
    assert 'card.type==="force"?"28%":"50%"' not in js
    assert 'const y=artFocus(card.art_focus_y,"50%");' in js
    assert "card.art_focus_x" in js
    assert "card.art_focus_y" in js
    assert "--art-x:" in js and "--art-y:" in js
    assert 'const artExt=options.printArt?".webp":".png"' in js
    assert '+artExt+"?v="+encodeURIComponent(VERSION)' in js
    assert "background-position:var(--art-x,50%) var(--art-y,50%)" in css



def test_runtime_art_crop_is_centered_after_normalization() -> None:
    js = (ROOT / "web" / "physical-cards.js").read_text(encoding="utf-8")
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")
    assert 'const y=artFocus(card.art_focus_y,"50%");' in js
    assert 'card.type==="force"?"28%":"50%"' not in js
    assert "background-position:var(--art-x,50%) var(--art-y,50%)" in css


def test_shared_visual_language_uses_raster_furniture() -> None:
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")
    # The layout guard checks the computed raster decoration for every card.
    assert "radial-gradient(" not in css
    assert "linear-gradient(" not in css
    assert "seal-inner" not in css
    assert "clip-path:" not in css
    assert "@page physicalcards{size:A4 landscape;margin:9mm 12.5mm 6mm}" in css


def test_long_titles_use_print_style_density_classes() -> None:
    for card, output in zip(CARDS, render_cards(CARDS), strict=True):
        classes = output.one("physical-card")["attrs"]["class"].split()
        assert ("title-very-long" in classes) is (len(card["title"]) >= 32)
        assert ("title-long" in classes) is (25 <= len(card["title"]) < 32)


def test_rules_keep_semantic_emphasis_without_changing_authored_text() -> None:
    phrase = "Choose a Human Archer in a Named Formation. It gets +1 Strength this Battle."
    card = {**CARDS[0], "effects": [{"timing": "play", "text": phrase}]}
    output, = render_cards([card])
    assert output.one("effect-text")["text"] == phrase
    assert [node["text"] for node in output.all("rule-term")] == ["Named Formation", "Strength", "Battle"]
    assert [node["text"] for node in output.all("rule-referent")] == ["Human", "Archer"]
    assert all(node["tag"] == "strong" for node in output.all("rule-term"))
    assert all(node["tag"] == "em" for node in output.all("rule-referent"))

def test_tactics_use_inline_class_icons_instead_of_footer_references() -> None:
    tactic = next(card for card in CARDS if card["id"] == "the-line-was-baited")
    output, = render_cards([tactic])
    class_line = output.one("class-line")
    assert class_line["text"] == "Tactic"
    assert output.one("class-type-item", within=class_line)["text"] == "Tactic"
    refs = output.all("inline-class-ref")
    assert [node["attrs"].get("title") for node in refs] == ["Guard", "Spearman", "Skirmisher"]
    assert output.one("effect-text")["text"] == tactic["effects"][0]["text"]


def test_exploratory_decks_keep_broad_card_type_mix() -> None:
    known = {card["id"]: card for card in CARDS}
    for deck in DECKS:
        counts = Counter()
        for item in deck["cards"]:
            counts[known[item["id"]]["type"]] += item["copies"]
        assert counts == {
            "force": 16,
            "bond": 8,
            "name": 6,
            "hero": 3,
            "tactic": 4,
            "stratagem": 4,
            "narrative": 4,
            "order": 3,
        }
        assert deck.get("combo_notes")
        assert deck.get("playstyle")


def test_print_cards_share_cut_seams() -> None:
    css = (ROOT / "web" / "physical-cards.css").read_text(encoding="utf-8")
    assert "width:272mm;height:192mm" in css
    assert "grid-template-columns:repeat(4,68mm)" in css
    assert "grid-template-rows:repeat(2,96mm)" in css
    assert "gap:0" in css
    assert ".print-card{border-radius:0}" in css
    assert ".print-card::before{border-radius:0}" in css


def test_three_rank_positional_support_grammar() -> None:
    by_id = {card["id"]: card for card in CARDS}
    positions = DATA["position_vocabulary"]
    assert "one rank toward the Front row" in positions["directly_ahead"]
    assert "one rank toward the Rear row" in positions["directly_behind"]
    assert "hard occupancy restriction" in positions["row_restriction"]
    assert "Maneuver, Move, or Swap" in positions["row_restriction"]
    assert "SUPPORT +N" in positions["support"]
    assert "SUPPLY" in positions["supply"]

    for timing in ("front", "middle", "rear"):
        assert timing in DATA["timing_vocabulary"]
        assert timing in DATA["card_type_grammar"]["force"]["allowed_timings"]

    for card_id in ("the-white-hands-of-elara", "the-house-of-reed", "the-watchtowers-of-eren"):
        assert by_id[card_id].get("placement") is None
        assert by_id[card_id]["allowed_rows"] == ["middle", "rear"]

    first_spear = by_id["the-first-spear"]
    assert first_spear.get("placement") is None
    assert first_spear["effects"][0]["timing"] == "front"
    assert "directly behind" in first_spear["effects"][0]["text"]

    assert by_id["the-crow-archers"]["effects"][0]["timing"] == "rear"
    assert by_id["the-crow-archers"]["effects"][0]["text"] == "While this formation is in the Rear row, SUPPORT +1."
    assert "SUPPORT +1" in by_id["the-banner-singers"]["text"]


def test_new_positional_bonds_are_short_relationship_cards() -> None:
    by_id = {card["id"]: card for card in CARDS}
    supported = by_id["supported-by"]
    supplied = by_id["supplied-by"]
    assert supported["type"] == supplied["type"] == "bond"
    assert supported["strength_modifier"] == supplied["strength_modifier"] == 0
    assert supported["text"] == "BONDED - While this formation is Bonded, SUPPORT +1."
    assert supplied["text"] == "BONDED - While this formation is Bonded, SUPPLY."
    assert "While this formation is Bonded" in supported["effects"][0]["text"]
    assert "While this formation is Bonded" in supplied["effects"][0]["text"]


def test_middle_only_support_forces_have_distinct_second_line_jobs() -> None:
    by_id = {card["id"]: card for card in CARDS}
    expected = {
        "the-relief-column": ("tireless", "directly_ahead"),
        "the-field-train": ("attach_prepared", "prepared_component_same_front"),
        "the-signal-company": ("maneuver_unnamed", "directly_ahead"),
    }
    for card_id, (op, target) in expected.items():
        card = by_id[card_id]
        assert card["type"] == "force"
        assert card["allowed_rows"] == ["middle"]
        assert "This Force may only occupy the Middle row." in card["text"]
        rule = card["design_rules"]["effects"][0]
        assert rule["op"] == op
        assert rule["target"] == target

    field_train = by_id["the-field-train"]["design_rules"]["effects"][0]
    assert field_train["destination"] == "directly_ahead"
    assert field_train["activation_cost"] == 1


def test_renderer_supports_positional_timings_and_multiple_allowed_rows() -> None:
    restricted = [card for card in CARDS if card.get("allowed_rows")]
    for card, output in zip(restricted, render_cards(restricted), strict=True):
        placement = output.one("edge-placement")
        assert placement["attrs"]["title"] == " / ".join(row.title() for row in card["allowed_rows"]) + " only"
        glyph = output.one("glyph-row", within=placement)
        active = [node for node in output.elements if node["tag"] == "rect" and "row-active" in node["attrs"].get("class", "").split() and glyph in node["ancestors"]]
        assert len(active) == len(card["allowed_rows"])
        body_rule = output.one("placement-rule")
        expected_rows = " or ".join(row.title() for row in card["allowed_rows"])
        assert f"This Force may only occupy the {expected_rows} rows." in body_rule["text"]
        assert "PLACEMENT" in body_rule["text"]
    positional = [card for card in CARDS if any(effect["timing"] in {"front", "middle", "rear"} for effect in effects(card))]
    for card, output in zip(positional, render_cards(positional), strict=True):
        assert [node["text"] for node in output.all("effect-label")] == [effect["timing"].replace("_", " ").upper() for effect in effects(card)]
        assert [node["text"] for node in output.all("effect-text")] == [effect["text"] for effect in effects(card)]


def test_outmatched_reserve_and_exhaustion_card_identities() -> None:
    by_id = {card["id"]: card for card in CARDS}
    positions = DATA["position_vocabulary"]
    assert "OUTMATCHED" in positions["outmatched"]
    assert "tie is not OUTMATCHED" in positions["outmatched"]
    assert "RESERVE +N" in positions["reserve"]
    assert "TIRELESS" in positions["tireless"]
    assert "only the Exhaustion restriction" in positions["tireless"]
    assert "Exhaustion token" in positions["tireless"]
    assert "boolean" in positions["tireless"]
    assert "multiple sources give no additional benefit" in positions["tireless"]
    assert "lose a Front" in positions["exhaustion"]
    assert "orthogonally adjacent active empty position" in positions["move"]
    assert "Never diagonal" in positions["move"]
    assert "up to N legal one-position Moves" in positions["move_multiple"]
    assert "exchange the complete contents" in positions["swap"]
    assert "Maneuver, Move, or Swap" in positions["movement_event"]
    assert "add together" in positions["stacking"]
    assert "each reduce the cost by 1" in positions["stacking"]
    assert "add all applicable increases" in positions["command_modifiers"]
    assert "minimum 0" in positions["command_modifiers"]
    assert "all matching increases apply" in positions["tax_markers"]
    assert "Battle-long Strength penalty" in positions["strength_marker"]
    assert "does not include Exhaustion" in positions["temporary_negative_marker"]
    assert "Tax marker" in positions["temporary_negative_marker"]

    grey = by_id["the-grey-riders"]
    assert grey["text"].startswith("MOBILE")
    assert [effect["timing"] for effect in grey["effects"]] == ["mobile", "tireless"]
    assert "without being Named" in positions["mobile"]

    old_guard = by_id["the-old-guard"]
    assert old_guard["text"] == "MIDDLE - RESERVE +2."
    assert old_guard["effects"][0]["timing"] == "middle"

    damar = by_id["the-damar"]
    assert damar["strength"] == 4
    assert damar["effects"][0]["timing"] == "exhausted"
    assert "+2 Strength" in damar["text"]

    held = by_id["held-the-line-for"]
    assert held["strength_modifier"] == 1
    assert held["text"] == "BONDED - RESERVE +1."

    covered = by_id["covered-the-withdrawal-of"]
    assert "directly ahead is TIRELESS" in covered["text"]

    sela = by_id["sela"]
    assert sela["effects"][1]["timing"] == "while_named"
    assert "TIRELESS" in sela["effects"][1]["text"]

    maelin = by_id["maelin"]
    assert "Remove Exhaustion" in maelin["effects"][0]["text"]


def test_renderer_knows_exhausted_and_tireless_states() -> None:
    original = next(card for card in CARDS if card["type"] == "force")
    cards = [{**original, "effects": [{"timing": timing, "text": "Preserved state reminder.", "exposed": "STATE REMINDER"}]}
             for timing in ("exhausted", "tireless", "mobile")]
    for card, output in zip(cards, render_cards(cards), strict=True):
        timing = card["effects"][0]["timing"]
        assert output.one("effect-label")["text"] == timing.upper()
        assert output.one("edge-mechanic")["attrs"]["data-timing"] == timing
        assert output.one("edge-timing-word")["text"] == timing.upper()
        assert output.one("edge-live-text")["text"] == "STATE REMINDER"
        icon = output.one("effect-timing-icon")
        assert output.all("glyph-utility", within=icon)


def test_buried_force_and_bond_rules_are_memory_light() -> None:
    by_id = {card["id"]: card for card in CARDS}

    # Bonds are the buried middle layer: choices resolve on PLAY; live text is state only.
    for card in CARDS:
        if card["type"] == "bond":
            assert all(effect["timing"] not in {"action", "reaction"} for effect in card["effects"]), card["id"]

    # Only deliberately tiny movement actions remain live on a buried Force layer.
    buried_active = []
    for card in CARDS:
        if card["type"] == "force":
            for effect in card["effects"]:
                if effect["timing"] in {"action", "reaction"}:
                    buried_active.append((card["id"], effect))
        elif card["type"] == "hero":
            for effect in card["modes"]["force"]["effects"]:
                if effect["timing"] in {"action", "reaction"}:
                    buried_active.append((card["id"], effect))

    assert {card_id for card_id, _ in buried_active} == {
        "the-vardai",
        "the-white-hands-of-elara",
        "kael-the-roadless",
        "neris-the-ferryman",
    }
    for card_id, effect in buried_active:
        assert effect["timing"] == "action"
        if card_id in {"kael-the-roadless", "neris-the-ferryman"}:
            assert effect.get("limit") == "once_per_battle"
            assert "used_marker" in effect.get("memory", [])
        else:
            assert effect.get("limit") is None
        assert len(effect["exposed"]) <= 30

    # Live buried state text must always have an exposed-strip representation.
    for card in CARDS:
        if card["type"] in {"force", "bond"}:
            source = card["effects"]
        elif card["type"] == "hero":
            source = card["modes"]["force"]["effects"]
        else:
            continue
        for effect in source:
            if effect["timing"] != "play":
                assert effect.get("exposed"), (card["id"], effect)


def test_no_trivial_once_per_battle_plus_one_bookkeeping() -> None:
    for card in CARDS:
        for effect in effects(card):
            if effect.get("limit") != "once_per_battle":
                continue
            if "+1 Strength" not in effect["text"]:
                continue
            # A limited +1 is acceptable only when the actual decision is something larger.
            assert (
                "Move " in effect["text"]
                or "Each friendly formation" in effect["text"]
            ), (card["id"], effect["text"])


def test_effect_audit_covers_every_current_effect() -> None:
    audit = (ROOT / "cards" / "effect-audit.md").read_text(encoding="utf-8")
    total = sum(len(effects(card)) for card in CARDS)
    assert f"all {total} current card effects" in audit
    assert "Pure `1/BATTLE -> +1 Strength` bookkeeping effects remaining: **0**" in audit
    assert "Bonds with buried ACTION/REACTION abilities: **0**" in audit


def test_wide_balance_cleanup_and_zero_cost_space() -> None:
    by_id = {card["id"]: card for card in CARDS}
    for card in CARDS:
        if card["type"] == "force":
            assert all(effect.get("limit") != "once_per_battle" for effect in card["effects"]), card["id"]
    assert [e["timing"] for e in by_id["the-grey-riders"]["effects"]] == ["mobile", "tireless"]
    assert any(e["timing"] == "action" and "Pay 1 Command" in e["text"] for e in by_id["the-vardai"]["effects"])
    assert by_id["the-dust-riders"]["strength"] == 3
    assert by_id["the-river-raiders"]["strength"] == 4
    assert "directly opposite" in by_id["the-red-duelists"]["text"]
    assert by_id["the-iron-boars"]["strength"] == 5
    assert "Opposing Bonds" in by_id["the-aradai"]["text"]
    assert "directly opposite" in by_id["the-ilyri"]["text"]
    assert by_id["the-thornbow-hunters"]["strength"] == 3
    assert by_id["the-watchtowers-of-eren"]["strength"] == 3
    assert by_id["the-white-hands-of-elara"]["effects"][0]["timing"] == "action"
    assert "has +1 Strength" in by_id["the-first-spear"]["text"]
    assert "has +2 Strength" in by_id["the-damar"]["text"]
    assert "minimum of 0" in by_id["the-salt-road-fleet"]["text"]
    assert "minimum of 0" in DATA["position_vocabulary"]["supply"]
    assert by_id["stood-fast-with"]["strength_modifier"] == 1
    assert by_id["the-baggage-was-abandoned"]["command_cost"] == 2
    assert "-3 Strength" in by_id["all-reserves-forward"]["text"]
    assert by_id["they-were-gathering-there"]["command_cost"] == 0
    assert by_id["namar"]["command_cost"] == 3
    assert by_id["tala"]["command_cost"] == 2
    assert by_id["maelin"]["command_cost"] == 2
    assert "Pay 2 Command" in by_id["sorin"]["text"]
    assert by_id["iven"]["command_cost"] == 3
    assert "minimum of 0" in by_id["iven"]["text"]
    assert "Bonds you play cost 1 less Command, to a minimum of 0" in by_id["tovan-the-quartermaster"]["text"]
    assert by_id["no-one-would-be-first-to-leave"]["command_cost"] == 2


def test_value_model_documents_action_and_condition_costs() -> None:
    model = (ROOT / "cards" / "value-model.md").read_text(encoding="utf-8")
    assert "expected value ~= printed Strength" in model
    assert "Action tax" in model
    assert "MOBILE" in model
    assert "Zero-Command cards" in model
    assert "half of a standard turn" in model


def test_orders_are_conditional_self_support_and_all_cards_are_decked() -> None:
    orders = [card for card in CARDS if card["type"] == "order"]
    assert len(orders) == 6
    assert DATA["card_type_grammar"]["order"]["scope"] == "self"
    assert "Unrestricted 0-Command Orders are not allowed" in DATA["card_type_grammar"]["order"]["zero_cost_rule"]
    zero_orders = [card for card in orders if card["command_cost"] == 0]
    assert {card["id"] for card in zero_orders} == {"fresh-orders","catch-your-breath","re-form-the-line","bind-the-wound","send-a-runner"}
    for card in zero_orders:
        assert card.get("references"), card["id"]
        assert card["effects"][0]["scope"] == "self"
    runner = next(card for card in orders if card["id"] == "send-a-runner")
    assert "Rear row" in runner["text"] and "Draw 2 cards, then discard 1 card" in runner["text"]
    stock = next(card for card in orders if card["id"] == "take-stock")
    assert stock["command_cost"] == 1 and "top 3 cards" in stock["text"]
    decked = {item["id"] for deck in DECKS for item in deck["cards"]}
    assert decked == {card["id"] for card in CARDS}


def test_every_card_has_command_value_audit_row() -> None:
    audit = (ROOT / "cards" / "valuation-audit.md").read_text(encoding="utf-8")
    assert f"every one of the {len(CARDS)} cards" in audit
    for card in CARDS:
        assert f"| {card['title']} |" in audit
    assert "Repeatable ACTION text pays an Action tax" in audit


def test_exploratory_decks_collectively_cover_the_entire_pool() -> None:
    decked = {item["id"] for deck in DECKS for item in deck["cards"]}
    assert decked == {card["id"] for card in CARDS}
    assert DECK_DATA["deck_size"] == 48
    # 48 cards is six full 8-card physical print sheets.
    assert DECK_DATA["deck_size"] % 8 == 0
