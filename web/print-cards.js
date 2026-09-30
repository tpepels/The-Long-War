(function () {
  "use strict";

  const TYPE_LABELS = { force: "Force", bond: "Bond", name: "Name", story: "Narrative", stratagem: "Stratagem" };
  const BUILD_VERSION = typeof document === "undefined"
    ? "dev"
    : document.querySelector('meta[name="lw-build-version"]')?.getAttribute("content") || "dev";
  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  const titleCase = (value) => String(value ?? "").split(/[-_ ]+/).filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
  const format = (value) => esc(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");

  function typeMarkup(card) {
    const type = card.hero ? "Hero" : TYPE_LABELS[card.type] || card.type;
    const detail = card.type === "story"
      ? [titleCase(card.narrative_form), card.ongoing ? "Ongoing" : ""].filter(Boolean).join(" · ")
      : card.hero ? "Force / Name" : "";
    return '<span class="card-type">' + esc(type) +
      (detail ? '<small>' + esc(detail) + '</small>' : '') + '</span>';
  }

  function commandMarkup(card) {
    if (!Number.isInteger(card.command_cost)) return "";
    return '<div class="command-cost" aria-label="Command cost ' + card.command_cost + '">' +
      '<small>Command</small><span class="command-seal"><b>' +
      card.command_cost + '</b></span></div>';
  }

  function statsMarkup(card) {
    if (card.hero) {
      return '<div class="card-stats hero-modes" aria-label="Strength when played as Force or Name">' +
        '<span class="hero-mode mode-force"><span class="stat-label">Force <small>strength</small></span>' +
        '<b class="stat-value">' + esc(card.strength) + '</b></span>' +
        '<span class="hero-mode mode-name"><span class="stat-label">Name <small>strength</small></span>' +
        '<b class="stat-value">' + esc(card.hero_name_strength) + '</b></span></div>';
    }
    if (!Number.isInteger(card.strength)) return "";
    return '<div class="card-stats"><span class="strength" aria-label="Strength ' + card.strength + '">' +
      card.strength + '</span><span class="stat-label">Strength</span></div>';
  }

  function propertiesMarkup(card) {
    const role = card.type === "force" && card.role ? titleCase(card.role) : "";
    const classes = (card.classes || []).filter((value) => value !== "hero" && value !== card.role);
    return '<div class="card-properties">' +
      (role ? '<strong class="card-role">' + esc(role) + '</strong>' : '') +
      (classes.length ? '<em class="card-classes">' + classes.map((v) => esc(titleCase(v))).join(" · ") + '</em>' : '') +
      '</div>';
  }

  function rulesMarkup(card) {
    // Preserve canonical labels, copy and order. Mode styling follows explicit
    // FORCE / NAME headings, including any following timing/trigger blocks.
    if (!card.rule_blocks?.length) {
      return card.text ? window.CardRules.markup(card, format, "") : "";
    }
    const renderBlock = (block) => {
      const rendered = window.CardRules.markup({ ...card, rule_blocks: [block] }, format);
      return (block.label || "").length > 20
        ? rendered.replace('class="rule-label"', 'class="rule-label rule-label-long"') : rendered;
    };
    if (!card.hero) return card.rule_blocks.map(renderBlock).join("");
    let mode = "";
    return card.rule_blocks.map((block) => {
      const nextMode = /^FORCE\b/i.test(block.label || "") ? "force"
        : /^NAME\b/i.test(block.label || "") ? "name" : mode;
      const start = nextMode && nextMode !== mode;
      mode = nextMode;
      const markup = renderBlock(block);
      return '<div class="hero-rule' + (mode ? ' rule-mode-' + mode : ' hero-trait') +
        (start ? ' rule-mode-start' : '') + '">' + markup + '</div>';
    }).join("");
  }

  function layoutClasses(card) {
    const blocks = card.rule_blocks || [];
    const rulesLength = blocks.length
      ? blocks.reduce((length, block) =>
          length + (block.label || "").length + (block.text || "").length, 0)
      : (card.text || "").length;
    const titleLength = String(card.title || "").length;
    return [
      titleLength >= 33 ? "title-very-long" : titleLength >= 25 ? "title-long" : "",
      rulesLength >= 310 ? "card-very-dense" : rulesLength >= 235 ? "card-dense" : "",
      !card.hero && blocks.length <= 2 && rulesLength <= 130 ? "card-brief" : "",
    ].filter(Boolean);
  }

  function markup(card, deckLabel) {
    const empty = !card.rule_blocks?.length && !card.text;
    const layout = layoutClasses(card);
    const brief = layout.includes("card-brief");
    return '<article class="game-card card-' + esc(card.type) +
      (card.hero ? ' card-hero' : '') + (empty ? ' card-vanilla' : '') +
      (layout.length ? ' ' + layout.join(' ') : '') +
      (deckLabel ? ' deck-card' : '') + '" data-card-id="' + esc(card.id) + '">' +
      '<div class="card-meta">' + typeMarkup(card) + commandMarkup(card) + '</div>' +
      '<h2 class="card-title">' + esc(card.title) + '</h2>' +
      statsMarkup(card) + propertiesMarkup(card) +
      '<div class="card-rule">' + rulesMarkup(card) + '</div>' +
      (brief ? '<div class="card-ornament" aria-hidden="true"><svg viewBox="0 0 120 32"><path d="M2 16H40M80 16H118M60 5L71 16L60 27L49 16Z"/></svg></div>' : '') +
      '<footer class="card-footer"><span>' + (card.unique ? '<em class="unique">Unique</em>' : 'The Long War') +
      '</span><span class="card-version">v' + esc(BUILD_VERSION) + '</span>' +
      '<span class="card-id">' + esc(deckLabel || card.id) + '</span></footer></article>';
  }

  window.PrintCards = { markup, version: BUILD_VERSION };
})();
