        if has_strong and has_weak:
            balance_direction = "mixed"
        elif has_strong:
            balance_direction = "strong"
        elif has_weak:
            balance_direction = "weak"
        else:
            balance_direction = "neutral"

        cards.append({
            "id": card_id,
            "title": card["title"],
            "type": card["type"],
            "strength": card.get("strength"),
            "text": card.get("text", ""),
            "unique": bool(card.get("unique", False)),
            "hero": bool(card.get("hero", False)),
            "hero_name_strength": card.get("hero_name_strength"),
            "classes": list(card.get("classes", [])),
            "role": card.get("role"),
            "story_form": card.get("story_form"),
            "veiled": bool(card.get("veiled", False)),
            "balance_level": balance_level,
            "balance_label": balance_label,
            "balance_direction": balance_direction,
            "evidence_strong": evidence_strong,
            "delayed_utility": delayed_utility,
            "playability_family": family,