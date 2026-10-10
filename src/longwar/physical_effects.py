"""Reviewed physical effect translations for the first status/Attack cards.

This is a narrow, explicit, testable bridge. Do not infer executable opcodes
from print prose, and do not silently fall back for further revised cards.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .physical_values import CANONICAL_CARD_IDS

PRINTED_EFFECTS = json.loads(r'''{"the-crow-archers":[{"timing":"play","text":"Give this Force Empowered."},{"timing":"attack","text":"If the opposing Frontline in this Front is empty, this Force's basic Archer Attack may target an opposing Middle Force.","exposed":"ARCHER · May target Middle through gap"}],"the-old-guard":[{"timing":"middle","text":"While in Middle, this Force screens the friendly Rear Force from basic Archer Attacks even while Shaken, but not while Depleted.","exposed":"Screens Rear even if Shaken; not Depleted"}],"the-first-spear":[{"timing":"play","text":"If you play this Force into Frontline, give the friendly Force directly behind it Guarded, if there is one."}],"the-iron-boars":[{"timing":"play","text":"If the opposing Frontline here is empty, choose an opposing Middle or Rear Force here and give it Depleted."}],"the-red-duelists":[{"timing":"play","text":"If an opposing Frontline Force is in this Front, give it Shaken."}],"guarded":[{"timing":"play","text":"Choose a friendly Force in this Front, if any. Give it Guarded."}],"endured-with":[{"timing":"play","text":"Choose a friendly Force in this Front, if any. Give it Inspired."}],"the-baggage-was-abandoned":[{"timing":"play","text":"Choose an opposing Rear Force. Exhaust it, then give it Shaken."}]}''')
PRINTED_EXECUTABLE_EFFECTS = json.loads(r'''{"the-crow-archers":[{"timing":"play","scope":"self","limit":null,"memory":[],"op":"grant_condition","target":"self","status":"empowered"},{"timing":"attack","scope":"self","limit":null,"memory":[],"op":"archer_middle_open_front","target":"self"}],"the-old-guard":[{"timing":"middle","scope":"self","limit":null,"memory":[],"op":"reliable_guard_screen","target":"self"}],"the-first-spear":[{"timing":"play","scope":"self","limit":null,"memory":[],"op":"grant_condition","target":"directly_behind","status":"guarded"}],"the-iron-boars":[{"timing":"play","scope":"opponent","limit":null,"memory":[],"op":"afflict_condition","target":"opposing_support_open_front","status":"depleted"}],"the-red-duelists":[{"timing":"play","scope":"opponent","limit":null,"memory":[],"op":"afflict_condition","target":"opposite","status":"shaken"}],"guarded":[{"timing":"play","scope":"self","limit":null,"memory":[],"op":"grant_condition","target":"friendly_same_front","status":"guarded"}],"endured-with":[{"timing":"play","scope":"self","limit":null,"memory":[],"op":"grant_condition","target":"friendly_same_front","status":"inspired"}],"the-baggage-was-abandoned":[{"timing":"play","scope":"opponent","limit":null,"memory":[],"op":"exhaust_then_shaken","target":"opposing_rear"}]}''')


def apply_reviewed_physical_effects(card_data: dict) -> dict:
    """Translate exactly the reviewed physical effects for canonical cards."""
    cards = card_data.get("cards", ())
    if {card.get("id") for card in cards} != CANONICAL_CARD_IDS:
        return card_data
    updated = deepcopy(card_data)
    for card in updated["cards"]:
        cid = card["id"]
        if cid not in PRINTED_EFFECTS:
            continue
        effects = deepcopy(PRINTED_EFFECTS[cid])
        compiled = deepcopy(PRINTED_EXECUTABLE_EFFECTS[cid])
        assert len(effects) == len(compiled)
        card["effects"] = effects
        card["design_rules"]["effects"] = compiled
        card["text"] = "\\n".join(
            e["timing"].upper()
            + (" · 1/BATTLE" if e.get("limit") == "once_per_battle" else "")
            + " - " + e["text"] for e in effects
        ) or "No special rules."
        card["rule_blocks"] = [
            {
                "kind": "continuous" if e["timing"] in {
                    "attack", "middle", "bonded", "while_named", "action",
                    "reaction", "front", "rear", "continuous", "tireless", "mobile",
                } else "effect",
                "label": e["timing"].upper(),
                "text": e["text"],
            } for e in effects
        ]
    return updated
