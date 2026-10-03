(() => {
  "use strict";
  const scriptURL = typeof document === "undefined" ? "" : document.currentScript?.src || "";
  const VERSION = (() => { try { return new URL(scriptURL, window.location.href).searchParams.get("v") || "dev"; } catch (_) { return "dev"; } })();
  const esc = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  const titleCase = value => String(value ?? "").split(/[-_ ]+/).filter(Boolean).map(part => part[0].toUpperCase() + part.slice(1)).join(" ");
  const TYPE = { force: "Force", bond: "Bond", name: "Name", hero: "Hero", tactic: "Tactic", stratagem: "Stratagem", narrative: "Narrative" };
  const LABEL = { play: "PLAY", action: "ACTION", reaction: "REACTION", bonded: "BONDED", while_named: "WHILE NAMED", becomes_named: "BECOMES NAMED", trigger: "TRIGGER", continuous: "CONTINUOUS", hidden: "REVEAL" };
  const LIVE = new Set(["action", "reaction", "bonded", "while_named"]);
  const signed = value => (Number(value) >= 0 ? "+" : "") + String(value ?? 0);
  const modeEffects = (card, mode) => card.modes?.[mode]?.effects || [];
  const effects = card => card.type === "hero" ? [...modeEffects(card, "force"), ...modeEffects(card, "name")] : card.effects || [];
  const symbol = type => window.V2Heraldry?.symbol(type) || "";

  function stat(value, type) {
    return '<span class="stat-' + type + '" aria-label="' + esc(TYPE[type] || type) + ' Strength ' + esc(value) + '"><span class="stat-symbol" aria-hidden="true">' + symbol(type) + '</span><b>' + esc(value) + '</b></span>';
  }
  function liveEffects(card, heroMode) {
    if (card.type === "hero") return modeEffects(card, "force").filter(e => LIVE.has(e.timing));
    return ["force", "bond"].includes(card.type) ? (card.effects || []).filter(e => LIVE.has(e.timing)) : [];
  }
  function reminder(effect) {
    // Presentation copy is keyed by the exact source sentence. A changed or new
    // rule falls back to its full text and is flagged if it no longer fits.
    return window.V2Reminders?.[effect.text] || effect.text;
  }
  function edge(card, heroMode) {
    const type = card.type === "hero" ? "force" : card.type;
    const value = card.type === "hero" ? card.force_strength
      : card.type === "force" ? card.strength : ["bond", "name"].includes(card.type) ? signed(card.strength_modifier) : null;
    const mark = value === null ? '<span class="edge-emblem" aria-hidden="true">' + symbol(type) + '</span>' : stat(value, type);
    const live = liveEffects(card, heroMode).map(effect => '<div class="edge-live" data-timing="' + esc(effect.timing) + '"><strong>' + (card.type === 'hero' ? 'FORCE · ' : '') + (effect.limit === "once_per_battle" ? (LABEL[effect.timing] + " 1/B") : LABEL[effect.timing]) + '</strong> <span>' + esc(reminder(effect)) + '</span></div>').join("");
    return '<header class="stack-edge"><div class="edge-heading">' + mark +
      (card.type === 'hero' ? stat(signed(card.name_strength_modifier), 'name') : '<span class="edge-type">' + esc(TYPE[type]) + '</span>') +
      '<span class="edge-classes">' + (card.classes || []).map(titleCase).map(esc).join(" · ") + '</span>' +
      (card.placement ? '<span class="edge-placement">' + esc(titleCase(card.placement)) + ' only</span>' : '') +
      '</div><div class="edge-reminders">' + live + '</div></header>';
  }
  function block(effect) {
    const kind = ["bonded", "while_named", "continuous"].includes(effect.timing) ? "state" : ["becomes_named", "trigger", "reaction", "hidden"].includes(effect.timing) ? "event" : "operation";
    return '<section class="effect-block timing-' + kind + '"><div class="effect-head"><span class="effect-label" data-timing="' + esc(effect.timing) + '">' + esc(LABEL[effect.timing] || effect.timing) + '</span>' +
      (effect.limit === "once_per_battle" ? '<em class="effect-limit">once per Battle</em>' : '') +
      '</div><div class="effect-text">' + esc(effect.text) + '</div></section>';
  }
  function rules(card) {
    if (card.type === "hero") {
      return '<section class="hero-rule-mode" data-mode="force"><h4 class="mode-heading">As Force</h4>' + modeEffects(card, "force").map(block).join("") +
        '</section><section class="hero-rule-mode" data-mode="name"><h4 class="mode-heading">As Name</h4>' + modeEffects(card, "name").map(block).join("") + '</section>';
    }
    return effects(card).length ? effects(card).map(block).join("") : '<p class="empty-rules">No special rules.</p>';
  }
  function cardArticle(card, extra = "", options = {}) {
    const heroMode = options.heroMode === "name" ? "name" : "force";
    const count = effects(card).reduce((n, e) => n + e.text.length, 0);
    const density = card.type === "hero" || count > 190 ? " dense" : count < 105 ? " sparse" : "";
    const references = card.references?.length ? "Involves " + card.references.map(titleCase).join(" · ") : "";
    const status = [card.type === "stratagem" ? "Play face down" : "", card.duration === "this_battle" ? "This Battle" : "", references].filter(Boolean).join(" · ");
    const modes = card.type === "hero" ? '<div class="hero-values"><span>' + stat(card.force_strength, "force") + '<small>Force</small></span><i>or</i><span>' + stat(signed(card.name_strength_modifier), "name") + '<small>Name</small></span></div>' : '';
    return '<article class="v2-card card-' + esc(card.type) + density + (extra ? ' ' + esc(extra) : '') + '" data-card-id="' + esc(card.id) + '"' +
      (card.type === "hero" ? ' data-hero-mode="' + heroMode + '"' : '') + '>' + edge(card, heroMode) +
      '<div class="card-body"><h3 class="card-title">' + esc(card.title) + '</h3>' +
      (status ? '<p class="card-byline">' + esc(status) + '</p>' : '') + modes +
      '<div class="motif-field" aria-hidden="true">' + (window.V2Heraldry?.motif(card) || '') + '</div>' +
      '<div class="rules">' + rules(card) + '</div></div>' +
      '<footer class="card-footer"><span class="footer-mark">' + (card.type === 'hero' ? 'V2 · Hero · Unique' : card.unique ? 'V2 · Unique' : 'The Long War · V2') + '</span><span class="footer-id">' + esc(card.id) + '</span>' +
      '<span class="cost-gem" aria-label="Command cost ' + esc(card.command_cost) + '"><svg viewBox="0 0 40 40" aria-hidden="true"><path d="M12 2H28L38 12V28L28 38H12L2 28V12Z"/><path class="seal-inner" d="M14 6H26L34 14V26L26 34H14L6 26V14Z"/></svg><b>' + esc(card.command_cost) + '</b></span></footer></article>';
  }
  const STACK_CASES = {
    "force-bond": { title: "Force + Bond", state: "Bonded", ids: ["the-crow-archers", "watched-the-skies-for"] },
    "force-name": { title: "Force + Name", state: "Formation · not Named", ids: ["the-red-shields", "corin-of-the-high-wall"] },
    named: { title: "Force + Bond + Name", state: "Named · also Bonded", ids: ["the-ash-bowmen", "watched-the-skies-for", "corin-of-the-high-wall"] },
    "hero-force": { title: "Hero as Force", state: "Named · also Bonded", ids: ["serai-queen-of-crows", "followed", "namar"], heroMode: "force" },
    "hero-name": { title: "Hero as Name", state: "Named · also Bonded", ids: ["the-house-of-reed", "carried-messages-for", "alda-keeper-of-the-ford"], heroMode: "name" },
  };
  function stackMarkup(cards, caseName) {
    const entry = STACK_CASES[caseName];
    if (!entry) return "";
    return '<div class="stack-demo" data-stack-case="' + esc(caseName) + '" data-layers="' + entry.ids.length + '">' + entry.ids.map((id, index) => {
      const card = cards.find(c => c.id === id);
      return card ? '<div class="stack-card" data-stack-layer="' + index + '">' + cardArticle(card, '', { heroMode: entry.heroMode }) + '</div>' : '';
    }).join('') + '</div>';
  }
  function renderStacks(cards) {
    document.getElementById("stack-tests").innerHTML = Object.entries(STACK_CASES).map(([key, entry]) => '<figure class="stack-case"><figcaption><h3>' + entry.title + '</h3><p>' + entry.state + '</p></figcaption>' + stackMarkup(cards, key) + '</figure>').join('');
  }
  function norm(card) { return [card.title, card.type, ...(card.classes || []), ...(card.references || []), ...(card.design_tags || []), card.text].join(" ").toLowerCase(); }
  function render(cards, decks) {
    const value = id => document.getElementById(id).value;
    const deck = decks.find(d => d.id === value("deck-filter"));
    const copies = new Map((deck?.cards || []).map(c => [c.id, c.copies]));
    const query = value("search").trim().toLowerCase();
    const filtered = cards.filter(card => (value("type-filter") === "all" || card.type === value("type-filter")) &&
      (value("class-filter") === "all" || [...(card.classes || []), ...(card.references || [])].includes(value("class-filter"))) &&
      (value("mechanic-filter") === "all" || (card.design_tags || []).includes(value("mechanic-filter"))) &&
      (!deck || copies.has(card.id)) && (!query || norm(card).includes(query)));
    document.getElementById("count").textContent = filtered.length + " / " + cards.length + " designs";
    document.getElementById("cards").innerHTML = filtered.map(card => '<div class="card-wrap">' + cardArticle(card) +
      (copies.has(card.id) ? '<span class="copy-chip">' + copies.get(card.id) + ' in deck</span>' : '') + '</div>').join('');
    scheduleCheck();
  }
  function inspect(root = document) {
    const failures = [];
    const mm = 96 / 25.4;
    root.querySelectorAll('.v2-card').forEach(card => {
      const box = card.getBoundingClientRect();
      if (!box.width || !box.height) return;
      const problems = [];
      for (const node of card.querySelectorAll('.stack-edge, .edge-classes, .edge-placement, .edge-live, .card-title, .rules, .card-footer')) {
        if (node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1) problems.push(node.classList[0] + '-overflow');
      }
      for (const node of card.querySelectorAll('.edge-heading, .edge-live')) {
        if (node.getBoundingClientRect().bottom > box.top + 10.5 * mm + .5) problems.push('covered-edge');
      }
      const footer = card.querySelector('.card-footer').getBoundingClientRect();
      for (const node of card.querySelectorAll('.effect-text, .empty-rules')) {
        if (node.getBoundingClientRect().bottom > footer.top + .5) problems.push('rules-footer-overlap');
      }
      card.classList.toggle('layout-overflow', problems.length > 0);
      if (problems.length) failures.push({ id: card.dataset.cardId, problems: [...new Set(problems)] });
    });
    return failures;
  }
  function scheduleCheck() {
    const run = () => {
      const failures = inspect();
      window.V2Cards.layoutFailures = failures;
      const status = document.getElementById('layout-status');
      if (status) { status.hidden = !failures.length; status.textContent = failures.length ? 'Print review needed: ' + [...new Set(failures.map(f => f.id))].join(', ') : ''; }
    };
    requestAnimationFrame(run);
    document.fonts?.ready.then(run);
  }
  async function main() {
    const [cr, dr] = await Promise.all([
      fetch('data/cards-v2-redesign.json?v=' + encodeURIComponent(VERSION), { cache: "no-cache" }),
      fetch('data/v2-playtest-decks.json?v=' + encodeURIComponent(VERSION), { cache: "no-cache" }),
    ]);
    if (!cr.ok || !dr.ok) throw new Error('Could not load V2 cards and diagnostic decks');
    const cards = (await cr.json()).cards, decks = (await dr.json()).decks;
    const options = (items, text) => '<option value="all">' + text + '</option>' + items.map(([id, title]) => '<option value="' + esc(id) + '">' + esc(title) + '</option>').join('');
    document.getElementById('class-filter').innerHTML = options([...new Set(cards.flatMap(c => [...(c.classes || []), ...(c.references || [])]))].sort().map(v => [v, titleCase(v)]), 'All classes');
    document.getElementById('mechanic-filter').innerHTML = options([...new Set(cards.flatMap(c => c.design_tags || []))].sort().map(v => [v, titleCase(v)]), 'All mechanics');
    document.getElementById('deck-filter').innerHTML = options(decks.map(d => [d.id, d.title]), 'All cards');
    renderStacks(cards); render(cards, decks);
    for (const id of ['type-filter', 'class-filter', 'mechanic-filter', 'deck-filter']) document.getElementById(id).addEventListener('change', () => render(cards, decks));
    document.getElementById('search').addEventListener('input', () => render(cards, decks));
    document.getElementById('stack-toggle').addEventListener('click', () => {
      const panel = document.getElementById('stack-lab'); panel.hidden = !panel.hidden;
      document.getElementById('stack-toggle').setAttribute('aria-expanded', String(!panel.hidden)); scheduleCheck();
    });
    document.getElementById('print-cards').addEventListener('click', async () => { await document.fonts.ready; window.print(); });
  }
  window.V2Cards = { cardArticle, stackMarkup, inspect, liveEffects, reminder };
  if (typeof document !== "undefined" && document.getElementById('cards')) main().catch(error => { document.getElementById('cards').textContent = error.message; });
})();
