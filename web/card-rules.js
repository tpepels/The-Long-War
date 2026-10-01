(function () {
  "use strict";

  const { cardType: CARD_TYPE, ruleBlockKind: RULE_BLOCK_KIND } = globalThis.LW_PROTOCOL;
  const KINDS = new Set(Object.values(RULE_BLOCK_KIND));
  function fallbackLabel(card, block) {
    if (block?.label) return String(block.label);
    if (block?.kind === RULE_BLOCK_KIND.PROPERTY) return "PLAY";
    if (block?.kind === RULE_BLOCK_KIND.TRIGGER) {
      return card?.type === CARD_TYPE.STRATAGEM ? "REVEAL" : "WHEN";
    }
    if (block?.kind === RULE_BLOCK_KIND.CONTINUOUS) return "WHILE";
    if (block?.kind === RULE_BLOCK_KIND.TIMING) return "TIMING";
    return "EFFECT";
  }

  function markup(card, formatter, emptyMarkup) {
    const blocks = Array.isArray(card?.rule_blocks) ? card.rule_blocks : [];
    if (!blocks.length) {
      if (card?.text) {
        return '<div class="rule-block rule-effect"><span class="rule-label">EFFECT</span><span class="rule-text">' +
          formatter(card.text) + '</span></div>';
      }
      return '<div class="rule-block rule-empty"><span class="rule-text">' +
        (emptyMarkup || "<em>No special rules.</em>") + '</span></div>';
    }
    return blocks.map((block) => {
      const kind = KINDS.has(block.kind) ? block.kind : RULE_BLOCK_KIND.EFFECT;
      const label = fallbackLabel(card, block);
      return '<div class="rule-block rule-' + kind + '">' +
        '<span class="rule-label">' + formatter(label) + '</span>' +
        '<span class="rule-text">' + formatter(block.text) + '</span>' +
      '</div>';
    }).join("");
  }

  window.CardRules = { markup };
})();
