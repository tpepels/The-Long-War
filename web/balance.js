const pct = (value, digits = 1) =>
  value == null ? "—" : `${(100 * Number(value)).toFixed(digits)}%`;

const num = (value, digits = 2) =>
  value == null ? "—" : Number(value).toFixed(digits);

const interval = (pair) =>
  !pair || pair[0] == null ? "—" : `${pct(pair[0])}–${pct(pair[1])}`;

const esc = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

function formatGameText(value) {
  return esc(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

const canonicalType = (card) => ({
  subject: "force",
  link: "bond",
  plot: "story",
}[card?.type] || card?.type);

const cssCardType = (card) => ({
  force: "subject",
  bond: "link",
  story: "plot",
}[canonicalType(card)] || canonicalType(card));

function titleCase(value) {
  return String(value ?? "")
    .split(/[-_ ]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function displayCardType(row) {
  const type = canonicalType(row);
  if (type === "story") {
    const form = titleCase(row.narrative_form);
    const ongoing = row.ongoing ?? false;
    return form ? form + (ongoing ? " · Ongoing Narrative" : " · Narrative") : (ongoing ? "Ongoing Narrative" : "Narrative");
  }
  if (type === "bond") return "Bond";
  if (type === "force") return row.hero ? "Hero · Force" : "Force";
  return titleCase(type);
}

function displayProperties(row) {
  const values = [];
  if (row.role) values.push(titleCase(row.role));
  for (const value of row.classes || []) {
    if (value === "hero") continue;
    const label = titleCase(value);
    if (!values.includes(label)) values.push(label);
  }
  if (!values.length) return "";
  return '<div class="muted">' +
    values.map((value) => "<em>" + esc(value) + "</em>").join(" · ") +
    "</div>";
}

function flagMarkup(flags) {
  if (!flags || !flags.length) return '<span class="muted">—</span>';
  return flags.map((flag) =>
    `<span class="flag flag-${esc(flag.severity)}" title="${esc(flag.message)}">${esc(flag.code.replaceAll("_", " "))}</span>`
  ).join(" ");
}

function metric(label, value, note = "") {
  return `
    <article class="metric-card">
      <p>${esc(label)}</p>
      <strong>${value}</strong>
      <small>${note}</small>
    </article>
  `;
}

function grade(row) {
  return `<span class="grade grade-${row.balance_level}" title="${esc(row.balance_direction)}">${esc(row.balance_label)}</span>`;
}

function signedPct(value) {
  if (value == null) return "—";
  return (Number(value) >= 0 ? "+" : "") + pct(value);
}

function renderOverview(lab) {
  const h = lab.health;
  const g = h.global;
  const s = h.summary;
  const verification = lab.verification;
  const suite = lab.mccfr_suite;
  const progression = lab.progression || lab.raw_telemetry?.progression;
  const lifecycle = progression?.formation_lifecycle || {};
  const choice = progression?.mechanical_choice || {};
  document.getElementById("overview").innerHTML = [
    metric("Games", Number(h.source.games).toLocaleString(), h.source.agents.join(" vs ")),
    metric("First-player win", pct(g.first_player_win_rate), `95% ${interval(g.first_player_win_rate_95)}`),
    metric("Cards", s.cards_analyzed, `${s.flags_high} high · ${s.flags_watch} watch flags`),
    metric("Forces becoming Named", pct(lifecycle.force_to_name_rate), progression ? `${lifecycle.forces_ever_named ?? 0} / ${lifecycle.forces ?? 0} Force lifecycles` : "progression not generated"),
    metric("Forced choice", pct(choice.exactly_one_legal_action_rate), progression ? "decisions with exactly one legal action" : "progression not generated"),
    metric("Causal coverage", lab.counterfactual ? lab.counterfactual.cards.length : "—", lab.counterfactual ? "paired card estimates" : "not generated"),
    metric("MCCFR card coverage", suite ? `${suite.covered_cards}/${suite.card_pool_size}` : "—", suite ? `${suite.profiles.length} deck profiles` : "not generated"),
    metric("Solver verification", verification ? (verification.passed ? "PASS" : "FAIL") : "—",
      verification ? `exploitability ${num(verification.exploitability, 4)}` : "not generated"),
  ].join("");
}

function attentionItem(level, title, body) {
  return `<article class="attention-item attention-${level}"><strong>${esc(title)}</strong><p>${body}</p></article>`;
}

function renderAttention(lab) {
  const cards = lab.health.cards || [];
  const critical = cards.filter((row) => ["red", "orange"].includes(row.balance_level));
  const watch = cards.filter((row) => row.balance_level === "yellow");
  const causal = [...(lab.counterfactual?.cards || [])]
    .filter((row) => row.confidence_excludes_zero)
    .sort((a, b) => Math.abs(b.delta_win_probability) - Math.abs(a.delta_win_probability));
  const firstPlayer = Number(lab.health.global.first_player_win_rate);
  const suite = lab.mccfr_suite;
  const items = [];

  if ((lab.stale_evidence || []).length) {
    items.push(attentionItem(
      "pending",
      "Solver evidence needs a fresh run for this ruleset",
      `Draw and the playtest deck profiles changed. ${lab.stale_evidence.length} restored dynamic/solver artifact${lab.stale_evidence.length === 1 ? "" : "s"} from an older game fingerprint ${lab.stale_evidence.length === 1 ? "is" : "are"} hidden rather than being presented as current evidence.`
    ));
  }

  if (critical.length) {
    items.push(attentionItem(
      "high",
      `${critical.length} card${critical.length === 1 ? "" : "s"} need direct balance review`,
      critical.slice(0, 6).map((row) => `<b>${esc(row.title)}</b>`).join(", ") +
        (critical.length > 6 ? ` and ${critical.length - 6} more` : "") + "."
    ));
  } else {
    items.push(attentionItem(
      "good",
      "No red or orange card flags",
      watch.length
        ? `${watch.length} yellow watch item${watch.length === 1 ? "" : "s"} remain; treat them as leads, not confirmed imbalance.`
        : "The current health pass has no high-confidence card-level balance flags."
    ));
  }

  if (causal.length) {
    const lead = causal[0];
    items.push(attentionItem(
      "watch",
      "Strongest current causal signal",
      `<b>${esc(lead.title)}</b> has paired ΔWP ${signedPct(lead.delta_win_probability)} with 95% interval ${interval(lead.ci95)}. ${causal.length} card signal${causal.length === 1 ? "" : "s"} currently exclude zero.`
    ));
  } else {
    items.push(attentionItem(
      "good",
      "No paired card effect currently excludes zero",
      "The counterfactual sweep is not identifying a high-confidence single-card causal outlier at its current sample size."
    ));
  }

  const seatDelta = Math.abs(firstPlayer - 0.5);
  items.push(attentionItem(
    seatDelta > 0.05 ? "watch" : "good",
    "Turn-order check",
    `First player wins ${pct(firstPlayer)} of the current self-play sample${seatDelta > 0.05 ? ", so turn order deserves follow-up." : ", inside the 45–55% working band."}`
  ));

  if (suite) {
    items.push(attentionItem(
      suite.covered_cards === suite.card_pool_size ? "good" : "watch",
      "MCCFR coverage",
      `${suite.profiles.length} deck-profile policies cover ${suite.covered_cards}/${suite.card_pool_size} current cards. Use the profile table below to compare solver/heuristic behavior by deck.`
    ));
  } else {
    items.push(attentionItem(
      "pending",
      "MCCFR suite not generated yet",
      "The card and heuristic reports are available, but there is no current-card MCCFR suite in this build."
    ));
  }

  document.getElementById("attention-summary").innerHTML = items.join("");
}

function renderCards(lab) {
  const filter = document.getElementById("card-filter").value;
  let rows = [...lab.health.cards];

  if (["force", "bond", "name", "story", "stratagem"].includes(filter)) {
    rows = rows.filter((row) => canonicalType(row) === filter);
  } else if (["red", "orange", "yellow", "green", "dark_green"].includes(filter)) {
    rows = rows.filter((row) => row.balance_level === filter);
  }

  const order = { red: 0, orange: 1, yellow: 2, green: 3, dark_green: 4 };
  rows.sort((a, b) =>
    order[a.balance_level] - order[b.balance_level] ||
    a.title.localeCompare(b.title)
  );

  document.getElementById("card-table").innerHTML = rows.map((row) => {
    const staticDelta = row.static?.delta_from_global_mean;
    const causal = row.counterfactual;
    const online = row.targeted_online;
    return `
      <tr class="grade-row grade-row-${row.balance_level}">
        <td data-label="Status">${grade(row)}</td>
        <td data-label="Card" class="card-name-cell">
          <strong>${esc(row.title)}</strong>
          ${displayProperties(row)}
          <div class="card-rule-inline">${formatGameText(row.text)}</div>
        </td>
        <td data-label="Type / Strength">
          ${esc(displayCardType(row))}
          <span class="metric-inline">${row.strength ?? "—"} Str</span>
          ${row.unique ? '<span class="muted"><em>Unique</em></span>' : ""}
        </td>
        <td data-label="Use">
          <strong>${pct(row.play_rate_per_draw)}</strong>
          <span class="muted">${row.plays}/${row.draws} plays/draws</span>
        </td>
        <td data-label="Dead on pass">${pct(row.dead_on_pass_rate)}</td>
        <td data-label="Front swing">${num(row.mean_immediate_front_swing, 1)} <span class="muted">z ${num(row.front_swing_z_within_type, 1)}</span></td>
        <td data-label="Causal ΔWP">${causal ? signedPct(causal.delta_win_probability) : "—"}<span class="muted">${causal ? interval(causal.ci95) : ""}</span></td>
        <td data-label="Online check">${online ? `${signedPct(online.online.effect)}<span class="muted">${esc(online.confirmation.replaceAll("_", " "))}</span>` : "—"}</td>
        <td data-label="Evidence">
          <details class="row-evidence">
            <summary>details</summary>
            <dl>
              <div><dt>Dead turns</dt><dd>${pct(row.unplayable_turn_rate)}</dd></div>
              <div><dt>Control swing</dt><dd>${num(row.mean_immediate_control_swing, 2)}</dd></div>
              <div><dt>Win when drawn</dt><dd>${pct(row.win_rate_when_drawn)} · ${interval(row.win_rate_when_drawn_95)}</dd></div>
              <div><dt>Win when played</dt><dd>${pct(row.win_rate_when_played)} · ${interval(row.win_rate_when_played_95)}</dd></div>
              <div><dt>Static Δ</dt><dd>${staticDelta == null ? "—" : (staticDelta >= 0 ? "+" : "") + num(staticDelta, 2)}</dd></div>
              <div><dt>Flags</dt><dd>${flagMarkup(row.flags)}</dd></div>
            </dl>
          </details>
        </td>
      </tr>
    `;
  }).join("");
}

function interactionTable(rows) {
  return `
    <table class="mini-table fitted-mini-table">
      <thead><tr><th>Cards</th><th>Interaction</th><th>95% interval</th><th>Level</th></tr></thead>
      <tbody>
        ${rows.map((row) => `
          <tr>
            <td><strong>${esc(row.title)}</strong></td>
            <td>${signedPct(row.interaction_delta)}</td>
            <td>${interval(row.ci95)}</td>
            <td><span class="grade grade-${row.level}">${esc(row.level.replace("_", " "))}</span></td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderCounterfactual(lab) {
  const cf = lab.counterfactual;
  if (!cf) {
    document.getElementById("counterfactual-overview").innerHTML =
      metric("Counterfactual", "—", "report not generated");
    document.getElementById("counterfactual-pairs").innerHTML = "";
    document.getElementById("counterfactual-triples").innerHTML = "";
    return;
  }

  const significantCards = cf.cards.filter((row) => row.confidence_excludes_zero).length;
  document.getElementById("counterfactual-overview").innerHTML = [
    metric("Paired samples", cf.samples, `${cf.contexts} contexts × ${cf.games_per_context} games`),
    metric("Matches", Number(cf.total_matches).toLocaleString(), `${cf.conditions_evaluated_per_sample} intervention states/sample`),
    metric("Causal card signals", significantCards, `of ${cf.cards.length} cards exclude zero`),
    metric("Policy", esc(cf.policy), "common-random-number pairing"),
  ].join("");

  document.getElementById("counterfactual-pairs").innerHTML =
    interactionTable((cf.pairs || []).slice(0, 20));
  document.getElementById("counterfactual-triples").innerHTML =
    interactionTable((cf.triples || []).slice(0, 20));
}

function renderTargetedCounterfactual(lab) {
  const report = lab.targeted_counterfactual;
  const el = document.getElementById("targeted-counterfactual");
  if (!report) {
    el.innerHTML = '<p class="muted">No targeted online-MCCFR validation report.</p>';
    return;
  }
  if (!report.targets.length) {
    el.innerHTML = '<p class="muted">The broad sweep nominated no suspicious targets at the configured threshold.</p>';
    return;
  }

  el.innerHTML = `
    <h3>Targeted online-MCCFR validation</h3>
    <div class="metric-grid compact-grid">
      ${metric("Targets", report.targets.length, `${report.total_matches} online matches`)}
      ${metric("Samples / target", report.samples, `${report.contexts} contexts × ${report.games_per_context} games`)}
      ${metric("Resolver", `${report.online_iterations} iterations`, `depth ${report.online_depth}`)}
      ${metric("Confirmed", report.targets.filter((r) => r.confirmation === "confirmed").length, "same-direction online CI excludes zero")}
    </div>
    <div class="table-wrap fitted-table">
      <table class="balance-table targeted-table">
        <thead><tr><th>Target</th><th>Heuristic</th><th>Online MCCFR</th><th>95%</th><th>Result</th></tr></thead>
        <tbody>
          ${report.targets.map((row) => `
            <tr>
              <td><strong>${esc(row.title)}</strong><span class="muted">${esc(row.kind)}</span></td>
              <td>${signedPct(row.broad.effect)} <span class="muted">${interval(row.broad.ci95)}</span></td>
              <td>${signedPct(row.online.effect)}</td>
              <td>${interval(row.online.ci95)}</td>
              <td><strong>${esc(row.confirmation.replaceAll("_", " "))}</strong></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderSequences(lab) {
  const rows = [...(
    lab.all_formations
    || lab.all_legends
    || lab.health.formations
    || lab.health.legends
    || []
  )];
  const observed = rows.filter((row) => row.observed !== false).length;
  document.getElementById("formation-count").textContent = `${rows.length} possible · ${observed} observed`;
  document.getElementById("formation-table").innerHTML = rows.map((row) => `
    <tr class="${row.flags.length ? "flagged-row" : ""}">
      <td><strong>${esc(row.title)}</strong></td>
      <td>${row.completions} / ${row.games_seen}</td>
      <td>${num(row.mean_strength_at_completion, 1)} / ${row.static_strength ?? "—"} <span class="muted">z ${num(row.static_z, 2)}</span></td>
      <td>${pct(row.win_rate_when_seen)}</td>
      <td>${interval(row.win_rate_when_seen_95)}</td>
      <td class="flags-cell">${flagMarkup(row.flags)}</td>
    </tr>
  `).join("");
}

function renderMatchups(lab) {
  const rows = Object.entries(lab.matchups || {}).filter(([, value]) => value);
  document.getElementById("matchups").innerHTML = `
    <table class="balance-table matchup-table">
      <thead><tr><th>Run</th><th>Agents</th><th>Games</th><th>Win rates</th><th>First player</th><th>Details</th></tr></thead>
      <tbody>
        ${rows.map(([name, row]) => `
          <tr>
            <td><strong>${esc(name.replaceAll("_", " "))}</strong></td>
            <td>${esc((row.agents || []).join(" vs "))}</td>
            <td>${row.games ?? "—"}</td>
            <td>${(row.win_rates || []).map((v) => pct(v)).join(" / ")}</td>
            <td>${pct(row.first_player_win_rate)}</td>
            <td>
              <details class="row-evidence">
                <summary>details</summary>
                <dl>
                  <div><dt>Wins</dt><dd>${(row.wins || []).join("–")}</dd></div>
                  <div><dt>Mean actions</dt><dd>${num(row.mean_turns, 1)}</dd></div>
                  <div><dt>Policy sources</dt><dd><code>${esc(JSON.stringify(row.policy_sources || {}))}</code></dd></div>
                </dl>
              </details>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function distributionValue(distribution, field = "median", digits = 1) {
  if (!distribution || distribution[field] == null) return "—";
  return num(distribution[field], digits);
}

function progressionMetric(label, distribution, note) {
  return metric(label, distributionValue(distribution), note || `median · n=${distribution?.count ?? 0}`);
}

function renderProgression(lab) {
  const p = lab.progression || lab.raw_telemetry?.progression;
  const unavailable = document.getElementById("progression-unavailable");
  if (!p) {
    unavailable.hidden = false;
    return;
  }
  unavailable.hidden = true;

  const life = p.formation_lifecycle || {};
  const field = p.battlefield_development || {};
  const contest = p.contestability || {};
  const choice = p.mechanical_choice || {};
  const resources = p.resources || {};

  document.getElementById("progression-battlefield").innerHTML = [
    metric("Force → Bond", pct(life.force_to_bond_rate), `${life.forces_ever_bonded ?? 0} of ${life.forces ?? 0} Force lifecycles`),
    metric("Force → Name", pct(life.force_to_name_rate), `${life.forces_ever_named ?? 0} eventually Named`),
    progressionMetric("Active Fronts", field.active_fronts, "median per Battle decision"),
    progressionMetric("Contested Fronts", field.contested_fronts, "median per Battle decision"),
    progressionMetric("Partial at Battle end", life.partial_at_battle_end_per_player, "median per player-Battle"),
    progressionMetric("Empty Fronts", field.empty_fronts, "median per Battle decision"),
    progressionMetric("Strength concentration", field.strength_concentration, "median strongest-Front share per player"),
    progressionMetric("Force → Name time", life.force_to_name_actions, "median actions"),
  ].join("");

  document.getElementById("progression-contestability").innerHTML = [
    progressionMetric("Front-control changes", contest.front_control_changes_per_battle, "median per Battle"),
    progressionMetric("Final |margin|", contest.final_abs_margin, "median total-Strength margin"),
    progressionMetric("Max |margin|", contest.maximum_abs_margin, "median Battle maximum"),
    progressionMetric("Battle length", contest.actions_per_battle, "median operation decisions"),
    progressionMetric("Durable lead", contest.durable_lead_action, "median action when measurable"),
    progressionMetric("Actions after durable lead", contest.actions_remaining_after_durable_lead, "median when measurable"),
    metric("No later control change", pct(contest.no_control_change_after_midpoint_rate), "after Battle midpoint"),
  ].join("");

  const passCategories = choice.pass_mechanical_categories || {};
  document.getElementById("progression-choice").innerHTML = [
    progressionMetric("Legal actions", choice.legal_action_count, "median per operation decision"),
    progressionMetric("Card-play options", choice.card_play_option_count, "median legal card actions"),
    progressionMetric("Maneuver options", choice.maneuver_option_count, "median legal Maneuvers"),
    metric("Exactly one legal action", pct(choice.exactly_one_legal_action_rate), `${choice.exactly_one_legal_action ?? 0} decisions`),
    metric("Forced Maneuver", pct(choice.forced_maneuver_rate), `${choice.forced_maneuvers ?? 0} decisions`),
    metric("Pass with no alternative", passCategories.no_alternative ?? 0, "mechanically no non-Pass action"),
    metric(
      "Constraint source / active",
      `${pct(choice.constraint_rule_source_rate)} / ${pct(choice.constraint_active_rate)}`,
      "source present is not the same as engine-enforced restriction"
    ),
  ].join("");

  const commandDist = resources.command_remaining_at_battle_end || {};
  const commandBuckets = resources.command_end_buckets || {};
  const zeroRate = commandDist.count ? (commandBuckets["0"] || 0) / commandDist.count : null;
  document.getElementById("progression-resources").innerHTML = [
    progressionMetric("Command at Battle end", commandDist, "median per player-Battle"),
    progressionMetric("Command at first pass", resources.command_at_first_pass, "median first passer"),
    metric("Ends at 0 Command", pct(zeroRate), `${commandBuckets["0"] || 0} player-Battles`),
    metric("Free Maneuvers", resources.free_maneuvers ?? 0, "actual zero-Command Maneuvers"),
    metric("Discounted actions", resources.discount_actions ?? 0, `${resources.discount_command_saved ?? 0} Command saved`),
    metric("Command regained", resources.command_gained_or_refunded ?? 0, "operation gains/refunds; Battle recovery excluded"),
    metric(
      "Card / Maneuver spend",
      `${resources.command_spend?.card_play ?? 0} / ${resources.command_spend?.maneuver ?? 0}`,
      "actual Command paid by category"
    ),
    metric("Free operations", resources.free_operations ?? 0, "zero-Command card plays or Maneuvers"),
  ].join("");

  const battles = p.by_battle || {};
  document.getElementById("progression-battles").innerHTML = ["1", "2", "3", "4+"].map((key) => {
    const row = battles[key] || { battles: 0 };
    if (!row.battles) {
      return `<tr><td><strong>${esc(key)}</strong></td><td colspan="13" class="muted">No observations</td></tr>`;
    }
    return `
      <tr>
        <td><strong>${esc(key)}</strong><span class="muted">n=${row.battles}</span></td>
        <td>${num(row.forces_played, 1)}</td>
        <td>${num(row.bonds_played, 1)}</td>
        <td>${num(row.names_played, 1)}</td>
        <td>${num(row.cards_played, 1)}</td>
        <td>${num(row.completed_formations, 1)}<span class="muted">${pct(row.eventual_completion_rate_for_forces_deployed)} eventual / deployed</span></td>
        <td>${num(row.incomplete_formations_end, 1)}</td>
        <td>${num(row.occupied_positions, 1)}</td>
        <td>${num(row.active_fronts, 1)} / ${num(row.contested_fronts, 1)}</td>
        <td>${num(row.front_control_changes, 1)}</td>
        <td>
          ${num(row.legal_actions, 1)}
          <span class="muted">constraint source/active ${pct(row.constraint_rule_source_rate)} / ${pct(row.constraint_active_rate)}</span>
        </td>
        <td>${num(row.hand_size, 1)} / ${num(row.deck_size, 1)}</td>
        <td>
          cmd ${num(row.first_pass_command, 1)}
          <span class="muted">unplayable ${num(row.first_pass_unplayable_cards, 1)} · card ${num(row.first_pass_playable_card_actions, 1)} · Maneuver ${num(row.first_pass_maneuver_actions, 1)} · alternatives ${num(row.first_pass_legal_alternatives, 1)}</span>
        </td>
        <td>
          ${num(row.command_start, 1)} / ${num(row.command_spent, 1)} / ${num(row.command_remaining, 1)}
          <span class="muted">next ${num(row.next_battle_command, 1)}</span>
        </td>
      </tr>
    `;
  }).join("");

  const titles = new Map((lab.health.cards || []).map((card) => [card.id, card.title]));
  const heroes = Object.entries(p.hero_modes || {}).sort((a, b) =>
    (titles.get(a[0]) || a[0]).localeCompare(titles.get(b[0]) || b[0])
  );
  document.getElementById("hero-mode-table").innerHTML = heroes.length
    ? heroes.map(([cardId, row]) => `
      <tr>
        <td><strong>${esc(titles.get(cardId) || cardId)}</strong></td>
        <td>${row.force_plays ?? 0}</td>
        <td>${row.name_plays ?? 0}</td>
        <td>${pct(row.force_usage_rate)}</td>
        <td>${pct(row.name_usage_rate)}</td>
        <td>${row.force_completions ?? 0} / ${row.name_completions ?? 0}<span class="muted">Force / Name</span></td>
        <td>
          ${num(row.mean_force_front_swing, 1)} / ${num(row.mean_name_front_swing, 1)}
          <span class="muted">Front swing</span>
        </td>
        <td>${row.force_battle_end_presence ?? 0} / ${row.name_battle_end_presence ?? 0}</td>
      </tr>
    `).join("")
    : '<tr><td colspan="8" class="muted">No Hero plays observed.</td></tr>';

  const firstPass = contest.first_pass_outcomes || {};
  const passRows = [
    ["Already ahead", firstPass.ahead],
    ["Tied", firstPass.tied],
    ["Behind", firstPass.behind],
    ["Playable alternatives", firstPass.with_playable_alternatives],
    ["No alternative", firstPass.no_alternative],
  ];
  const cardLifecycle = Object.entries(p.cards || {})
    .sort((a, b) =>
      ((b[1].unplayed_at_match_end || 0) + (b[1].held_across_battle_boundaries || 0) + (b[1].discarded_without_play || 0)) -
      ((a[1].unplayed_at_match_end || 0) + (a[1].held_across_battle_boundaries || 0) + (a[1].discarded_without_play || 0))
    )
    .slice(0, 12);
  const definitions = Object.entries(p.definitions || {});

  document.getElementById("progression-diagnostics").innerHTML = `
    <div class="two-column-tables">
      <div>
        <h3>First-pass state and final Front balance</h3>
        <table class="mini-table">
          <thead><tr><th>State</th><th>Events</th><th>Resolved</th><th>Mean final Front balance</th><th>Positive balance</th></tr></thead>
          <tbody>${passRows.map(([label, row]) => `
            <tr>
              <td>${esc(label)}</td>
              <td>${row?.events ?? 0}</td>
              <td>${row?.resolved ?? 0}</td>
              <td>${num(row?.mean_final_front_balance, 2)}</td>
              <td>${pct(row?.positive_final_front_balance_rate)}</td>
            </tr>
          `).join("")}</tbody>
        </table>
      </div>
      <div>
        <h3>Card lifecycle pressure</h3>
        <table class="mini-table">
          <thead><tr><th>Card</th><th>Draw → play</th><th>Held across Battles</th><th>Discarded unplayed</th><th>In hand at match end</th></tr></thead>
          <tbody>${cardLifecycle.map(([cardId, row]) => `
            <tr>
              <td>${esc(titles.get(cardId) || cardId)}</td>
              <td>${distributionValue(row.draw_to_play_actions)}</td>
              <td>${row.held_across_battle_boundaries ?? 0}</td>
              <td>${row.discarded_without_play ?? 0}</td>
              <td>${row.unplayed_at_match_end ?? 0}</td>
            </tr>
          `).join("")}</tbody>
        </table>
      </div>
    </div>
    <div class="progression-definitions">
      <h3>Exact definitions</h3>
      <dl>${definitions.map(([key, value]) => `<div><dt>${esc(key.replaceAll("_", " "))}</dt><dd>${esc(value)}</dd></div>`).join("")}</dl>
    </div>
  `;
}

function renderTelemetry(lab) {
  const t = lab.raw_telemetry;
  if (!t) return;
  const p = t.passes || {};
  const b = t.battles || {};
  document.getElementById("telemetry-grid").innerHTML = [
    metric("Battles", b.count ?? "—", `mean actions ${num(b.mean_actions, 1)}`),
    metric("Battle Strength", num(b.mean_total_strength, 1), `mean |margin| ${num(b.mean_abs_total_margin, 1)}`),
    metric("Pass events", p.events ?? "—", `mean hand ${num(p.mean_hand_size, 1)}`),
    metric("First Pass share", pct(p.first_pass_rate), "share of Pass events that opened a pass sequence"),
  ].join("");

  const actions = Object.entries(t.actions || {});
  const decisions = Object.entries(t.decisions || {});
  document.getElementById("raw-telemetry").innerHTML = `
    <div class="two-column-tables">
      <div>
        <h3>Actions</h3>
        <table class="mini-table fitted-mini-table"><tbody>
          ${actions.map(([k,v]) => `<tr><td>${esc(k)}</td><td>${v}</td></tr>`).join("")}
        </tbody></table>
      </div>
      <div>
        <h3>Agent decisions</h3>
        <table class="mini-table fitted-mini-table"><tbody>
          ${decisions.map(([k,v]) => `<tr><td>${esc(k)}</td><td>${v.decisions} · ${num(v.mean_candidate_count,1)} candidates · gap ${num(v.mean_score_gap,2)}</td></tr>`).join("")}
        </tbody></table>
      </div>
    </div>
  `;
}

function renderMccfr(lab) {
  const suite = lab.mccfr_suite;
  const fallback = lab.mccfr;
  const verification = lab.verification;
  const profiles = document.getElementById("mccfr-profiles");

  if (suite) {
    document.getElementById("mccfr-overview").innerHTML = [
      metric("Card coverage", `${suite.covered_cards}/${suite.card_pool_size}`, pct(suite.coverage_fraction) + " of current pool"),
      metric("Deck profiles", suite.profiles.length, "Reference · Avaros · Mara · Sera"),
      metric("Policies", suite.profiles.length, "one mirror policy per deck profile"),
      metric("Missing cards", suite.missing_cards.length, suite.missing_cards.length ? suite.missing_cards.join(", ") : "none"),
    ].join("");

    profiles.innerHTML = `
      <table class="balance-table mccfr-table">
        <thead><tr><th>Deck profile</th><th>Unique cards</th><th>Iterations</th><th>Infosets</th><th>Depth</th><th>MCCFR vs heuristic</th><th>Eval games</th></tr></thead>
        <tbody>
          ${suite.profiles.map((row) => `
            <tr>
              <td><strong>${esc(row.label)}</strong><span class="muted">${esc(row.deck)}</span></td>
              <td>${row.deck_unique_cards}</td>
              <td>${row.policy.iterations ?? "—"}</td>
              <td>${Number(row.policy.information_sets || 0).toLocaleString()}</td>
              <td>${row.policy.max_depth ?? "—"}</td>
              <td><strong>${pct(row.evaluation.seat_swapped_mccfr_win_rate)}</strong><span class="muted">seat-swapped</span></td>
              <td>${row.evaluation.games}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } else if (fallback) {
    document.getElementById("mccfr-overview").innerHTML = [
      metric("Iterations", fallback.iterations ?? "—", `${fallback.traversals ?? "—"} traversals`),
      metric("Information sets", Number(fallback.information_sets || 0).toLocaleString(), `depth ${fallback.max_depth}`),
      metric("Algorithm", "External sampling", fallback.algorithm || ""),
      metric("Coverage", "Reference only", "legacy single-policy artifact"),
    ].join("");
    profiles.innerHTML = '<p class="muted">This build contains the older single reference-deck MCCFR artifact.</p>';
  } else {
    document.getElementById("mccfr-overview").innerHTML = metric("MCCFR", "—", "policy suite not generated");
    profiles.innerHTML = "";
  }

  if (!verification) {
    document.getElementById("mccfr-verification").innerHTML = '<p class="verification verification-missing">No formal verification artifact.</p>';
    return;
  }
  document.getElementById("mccfr-verification").innerHTML = `
    <div class="verification ${verification.passed ? "verification-pass" : "verification-fail"}">
      <strong>${verification.passed ? "VERIFIED" : "FAILED"}</strong>
      <span>${esc(verification.benchmark)} · known ${num(verification.known_p0_value, 6)} · learned ${num(verification.learned_p0_value, 6)} · error ${num(verification.absolute_value_error, 6)} · exploitability ${num(verification.exploitability, 6)}</span>
      <span>Thresholds: value error ≤ ${verification.thresholds.max_value_error}, exploitability ≤ ${verification.thresholds.max_exploitability}</span>
    </div>
  `;
}

function staticTable(rows) {
  return `
    <table class="mini-table fitted-mini-table">
      <thead><tr><th>Force · Bond · Name</th><th>Strength</th><th>z</th></tr></thead>
      <tbody>
        ${rows.map((r) => `<tr><td><code>${esc([r.subject,r.link,r.name].join(" · "))}</code></td><td>${r.static_strength}</td><td>${num(r.z_score,2)}</td></tr>`).join("")}
      </tbody>
    </table>
  `;
}

function renderStatic(lab) {
  const s = lab.static;
  document.getElementById("static-overview").innerHTML = [
    metric("Static combinations", s.legend_count, "Force × Bond × Name"),
    metric("Mean Strength", num(s.static_strength.mean, 2), `σ ${num(s.static_strength.population_sd, 2)}`),
    metric("Range", `${s.static_strength.min}–${s.static_strength.max}`, "static Strength only"),
  ].join("");
  document.getElementById("static-high").innerHTML = staticTable(s.highest_static_legends);
  document.getElementById("static-low").innerHTML = staticTable(s.lowest_static_legends);
}

function renderDownloads(lab) {
  document.getElementById("downloads").innerHTML = (lab.downloads || []).map((file) =>
    `<a class="artifact-link" href="data/${encodeURIComponent(file)}">${esc(file)}</a>`
  ).join("");
}

function renderMethod(lab) {
  const report = lab.health;
  document.getElementById("methodology").innerHTML = `
    <p><strong>Card status:</strong> red = multiple high-confidence issues; orange = one high-confidence or multiple watch issues; yellow = one watch issue; green = no current issue but thinner evidence; dark green = no issue with strong evidence.</p>
    <p><strong>Intervals:</strong> ${esc(report.methodology.win_intervals)}.</p>
    <p><strong>Board swing:</strong> standardized within card type.</p>
    <p><strong>Causal ΔWP:</strong> paired win-probability difference between the canonical card and a neutral same-type baseline under identical random seeds.</p>
    <p><strong>Targeted online validation:</strong> suspicious heuristic effects are rerun with online MCCFR. “Confirmed” means the online interval excludes zero in the same direction.</p>
    <ul>${report.methodology.notes.map((note) => `<li>${esc(note)}</li>`).join("")}</ul>
  `;
}

async function main() {
  const response = await fetch("data/lab-report.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Full Balance Lab report is not available yet.");
  const lab = await response.json();

  renderAttention(lab);
  renderOverview(lab);
  renderProgression(lab);
  renderCards(lab);
  renderCounterfactual(lab);
  renderTargetedCounterfactual(lab);
  renderSequences(lab);
  renderMatchups(lab);
  renderTelemetry(lab);
  renderMccfr(lab);
  renderStatic(lab);
  renderDownloads(lab);
  renderMethod(lab);

  document.getElementById("card-filter").addEventListener("change", () => renderCards(lab));
}

main().catch((error) => {
  document.getElementById("attention-summary").innerHTML =
    attentionItem("high", "Balance Lab unavailable", esc(error.message));
  document.getElementById("overview").innerHTML = "";
});
