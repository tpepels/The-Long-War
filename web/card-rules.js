(function () {
  "use strict";

  const KINDS = new Set(["property", "timing", "trigger", "effect", "continuous"]);

  function markup(card, formatter, emptyMarkup) {
    const blocks = Array.isArray(card?.rule_blocks) ? card.rule_blocks : [];
    if (!blocks.length) {
      if (card?.text) {
        return '<div class="rule-block rule-effect">' + formatter(card.text) + '</div>';
      }
      return '<div class="rule-block rule-empty">' + (emptyMarkup || "&nbsp;") + '</div>';
    }
    return blocks.map((block) => {
      const kind = KINDS.has(block.kind) ? block.kind : "effect";
      return '<div class="rule-block rule-' + kind + '">' + formatter(block.text) + '</div>';
    }).join("");
  }

  window.CardRules = { markup };
})();
