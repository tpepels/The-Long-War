(function () {
  "use strict";

  const KINDS = new Set(["property", "timing", "trigger", "effect", "continuous"]);
  function fallbackLabel(card, block) {
    if (block?.label) return String(block.label);
    if (block?.kind === "property") return "PLAY";
    if (block?.kind === "trigger") {
      return card?.veiled || card?.type === "stratagem" ? "REVEAL" : "WHEN";
    }
    if (block?.kind === "continuous") return "WHILE";
    if (block?.kind === "timing") return "TIMING";
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
      const kind = KINDS.has(block.kind) ? block.kind : "effect";
      const label = fallbackLabel(card, block);
      return '<div class="rule-block rule-' + kind + '">' +
        '<span class="rule-label">' + formatter(label) + '</span>' +
        '<span class="rule-text">' + formatter(block.text) + '</span>' +
      '</div>';
    }).join("");
  }

  window.CardRules = { markup };
})();
