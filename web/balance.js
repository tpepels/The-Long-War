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

const canonicalType = (card) => card?.type;

function titleCase(value) {
  return String(value ?? "")
    .split(/[-_ ]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function displayCardType(row) {
  const type = canonicalType(row);
  if (type === "narrative") {
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

function annotateMechanicsCoverage(lab, cardData) {
  const meta = new Map((cardData?.cards || []).map((card) => [card.id, card]));
  const pending = [];
  for (const row of lab.health?.cards || []) {
    const card = meta.get(row.id);
    if (card?.engine_sync !== "pending-compulsion-mechanics") continue;
    row.mechanics_implemented = false;
    row.engine_sync = card.engine_sync;
    row.balance_level = "mechanics_pending";
    row.balance_label = "Mechanics pending";
    row.balance_direction = "unimplemented";
    row.balance_evidence_source = "engine_pending";
    row.flags = [];
    pending.push(row);
  }
  lab.mechanics_pending_cards = pending;
  lab.mechanics_implemented_cards = (cardData?.cards || []).length - pending.length;

  const summary = lab.health?.summary;
  if (summary) {
    const rows = lab.health.cards || [];
    summary.cards_mechanics_pending = pending.length;
    summary.flags_high = rows.flatMap((row) => row.flags || []).filter((flag) => flag.severity === "high").length;
    summary.flags_watch = rows.flatMap((row) => row.flags || []).filter((flag) => flag.severity === "watch").length;
    summary.flags_diagnostic = rows.flatMap((row) => row.flags || []).filter((flag) => flag.severity === "diagnostic").length;
    summary.card_levels = rows.reduce((counts, row) => {
      counts[row.balance_level] = (counts[row.balance_level] || 0) + 1;
      return counts;
    }, {});
  }
}

function signedPct(value) {
  if (value == null) return "—";
  return (Number(value) >= 0 ? "+" : "") + pct(value);
}

function signedNum(value, digits = 1) {
  if (value == null) return "—";
  const number = Number(value);
  return (number >= 0 ? "+" : "") + number.toFixed(digits);
}

function renderOverview(lab) {
  const h = lab.health;
  const g = h.global;
  const s = h.summary;
  const verification = lab.verification;
  const suite = lab.mccfr_suite;
  const progression = lab.progression || lab.raw_telemetry?.progression;
  const progressionProfiles = lab.progression_profiles || {};
  const progressionProfileCount = Object.keys(progressionProfiles).length;
  const choice = progression?.mechanical_choice || {};
  const totalGames = Number(h.source.games || 0);
  const censoredGames = Number(h.source.censored_games || 0);
  const decisiveGames = Number(
    h.source.decisive_games ??
    Math.max(
      0,
      totalGames
        - censoredGames
        - Number(h.source.draws || 0)
        - Number(h.source.failed_games || 0)
    )
  );
  document.getElementById("overview").innerHTML = [
    metric(
      "Games",
      totalGames.toLocaleString(),
      `${decisiveGames.toLocaleString()} decisive · ${censoredGames.toLocaleString()} censored · ${h.source.agents.join(" vs ")}`
    ),
    metric(
      "First-player win",
      decisiveGames > 0 ? pct(g.first_player_win_rate) : "—",
      decisiveGames > 0 ? `decisive games · 95% ${interval(g.first_player_win_rate_95)}` : "no decisive games"
    ),
    metric(
      "Cards",
      s.cards_analyzed,
      `${s.cards_observed ?? s.cards_analyzed} observed · ${s.cards_unobserved ?? 0} unobserved · ${s.flags_high} high · ${s.flags_watch} watch`
    ),
    metric(
      "Executable mechanics",
      `${lab.mechanics_implemented_cards ?? s.cards_analyzed}/${s.cards_analyzed}`,
      `${(lab.mechanics_pending_cards || []).length} approved compulsion cards pending native implementation`
    ),
    metric(
      "Progression coverage",
      progressionProfileCount ? `${progressionProfileCount}/6` : (progression ? "1/6" : "—"),
      progressionProfileCount ? "canonical reference-deck profiles" : (progression ? "single current progression profile" : "progression not generated")
    ),
    metric("Forced choice", pct(choice.exactly_one_legal_action_rate), progression ? "decisions with exactly one legal action" : "progression not generated"),
    metric("Broad card screen", lab.counterfactual ? lab.counterfactual.cards.length : "—", lab.counterfactual ? "heuristic paired A/B estimates" : "not generated"),
    metric(
      "Strategic checks",
      lab.targeted_counterfactual ? lab.targeted_counterfactual.targets.length : "—",
      lab.targeted_counterfactual ? "targeted online-MCCFR validations" : "not generated"
    ),
    metric("Offline MCCFR coverage", suite ? `${suite.covered_cards}/${suite.card_pool_size}` : "—", suite ? `${suite.profiles.length} trained deck policies` : "optional research evidence"),
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
  const targeted = lab.targeted_counterfactual;
  const items = [];

  const mechanicsPending = lab.mechanics_pending_cards || [];
  if (mechanicsPending.length) {
    items.push(attentionItem(
      "pending",
      "Approved compulsion mechanics are not executable yet",
      mechanicsPending.map((row) => `<b>${esc(row.title)}</b>`).join(", ") +
        ". Their balance status is suppressed until the native engine implements the approved necessity/compulsion rules."
    ));
  }

  if ((lab.stale_evidence || []).length) {
    items.push(attentionItem(
      "pending",
      "Solver evidence needs a fresh run for this ruleset",
      `Draw and the playtest deck profiles changed. ${lab.stale_evidence.length} restored dynamic/solver artifact${lab.stale_evidence.length === 1 ? "" : "s"} from an older game fingerprint ${lab.stale_evidence.length === 1 ? "is" : "are"} hidden rather than being presented as current evidence.`
    ));
  }

  const unobservedCards = cards.filter((row) => row.observed === false);
  if (unobservedCards.length) {
    items.push(attentionItem(
      "pending",
      `${unobservedCards.length} card${unobservedCards.length === 1 ? "" : "s"} lack self-play evidence`,
      unobservedCards.slice(0, 6).map((row) => `<b>${esc(row.title)}</b>`).join(", ") +
        (unobservedCards.length > 6 ? ` and ${unobservedCards.length - 6} more` : "") +
        ". Their observational status remains Unobserved; independent causal or online evidence is surfaced separately when available."
    ));
  }

  const progression = lab.progression || lab.raw_telemetry?.progression;
  const censoredCollapsePointMatches = Number(
    progression?.match_length?.censored_at_collapse_point_matches || 0
  );
  if (censoredCollapsePointMatches > 0) {
    items.push(attentionItem(
      "high",
      "Collapse-point state reached the simulation horizon",
      `${censoredCollapsePointMatches} censored match${censoredCollapsePointMatches === 1 ? "" : "es"} ended with at least one side at or below the configured Collapse threshold. That state should terminate before recovery, so this indicates stale evidence or an engine/search transition bug.`
    ));
  }

  const censoredGames = Number(lab.health.source.censored_games || 0);
  if (censoredGames > 0) {
    const totalGames = Number(lab.health.source.games || 0);
    items.push(attentionItem(
      "pending",
      "Some simulations reached the action horizon",
      `${censoredGames} of ${totalGames} games were censored at the configured action horizon. They remain progression evidence but are excluded from win-rate and outcome-association denominators.`
    ));
  }

  if (critical.length) {
    const strategicallyResolved = critical.filter(
      (row) => row.balance_evidence_source === "online_mccfr"
    );
    const observationalOnly = critical.filter(
      (row) => row.balance_evidence_source !== "online_mccfr"
    );
    items.push(attentionItem(
      "high",
      `${critical.length} card${critical.length === 1 ? "" : "s"} need direct balance review`,
      critical.slice(0, 6).map((row) => `<b>${esc(row.title)}</b>`).join(", ") +
        (critical.length > 6 ? ` and ${critical.length - 6} more` : "") +
        `. ${strategicallyResolved.length} strategically resolved by online MCCFR; ${observationalOnly.length} currently come from observational evidence and still need strategic confirmation.`
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
      "Broad card screen found candidates",
      `<b>${esc(lead.title)}</b> has heuristic paired ΔWP ${signedPct(lead.delta_win_probability)} with 95% interval ${interval(lead.ci95)}. ${causal.length} card signal${causal.length === 1 ? "" : "s"} currently exclude zero and should be read as screening evidence until MCCFR validation.`
    ));
  } else if (lab.counterfactual) {
    items.push(attentionItem(
      "good",
      "Broad card screen found no resolved outlier",
      "No single-card heuristic A/B interval currently excludes zero at this sample size."
    ));
  }

  if (targeted) {
    const confirmed = targeted.targets.filter((row) => row.confirmation === "confirmed");
    const reversed = targeted.targets.filter((row) => row.confirmation === "reversed");
    const unresolved = targeted.targets.filter((row) =>
      ["direction_agrees", "inconclusive"].includes(row.confirmation)
    );
    if (!targeted.targets.length) {
      items.push(attentionItem(
        "good",
        "No strategic card validation was needed",
        "The broad screen nominated no card above the configured threshold."
      ));
    } else {
      items.push(attentionItem(
        reversed.length ? "watch" : (confirmed.length ? "watch" : "pending"),
        "Online-MCCFR strategic confirmation",
        `${confirmed.length} confirmed · ${reversed.length} reversed · ${unresolved.length} unresolved across ${targeted.targets.length} targeted card checks. A reversal means the stronger online solver found a resolved effect in the opposite direction from the heuristic screen.`
      ));
    }
  } else if (lab.counterfactual) {
    items.push(attentionItem(
      "pending",
      "Strategic confirmation missing",
      "A broad heuristic card screen exists, but targeted online-MCCFR validation has not been generated for this snapshot."
    ));
  }

  const decisiveGames = Number(
    lab.health.source.decisive_games ??
    Math.max(
      0,
      Number(lab.health.source.games || 0)
        - Number(lab.health.source.censored_games || 0)
        - Number(lab.health.source.draws || 0)
        - Number(lab.health.source.failed_games || 0)
    )
  );
  if (decisiveGames > 0) {
    const seatDelta = Math.abs(firstPlayer - 0.5);
    items.push(attentionItem(
      seatDelta > 0.05 ? "watch" : "good",
      "Turn-order check",
      `First player wins ${pct(firstPlayer)} of ${decisiveGames} decisive self-play games${seatDelta > 0.05 ? ", so turn order deserves follow-up." : ", inside the 45–55% working band."}`
    ));
  } else {
    items.push(attentionItem(
      "pending",
      "Turn-order evidence unavailable",
      "No simulated game produced a decisive outcome within the action horizon."
    ));
  }

  if (suite) {
    items.push(attentionItem(
      suite.covered_cards === suite.card_pool_size ? "good" : "watch",
      "Offline solver research available",
      `${suite.profiles.length} trained deck-profile policies cover ${suite.covered_cards}/${suite.card_pool_size} current cards. This is separate from the targeted online-MCCFR card validation above.`
    ));
  }

  document.getElementById("attention-summary").innerHTML = items.join("");
}

function renderEvidencePipeline(lab) {
  const summary = lab.run_summary?.evidence_pipeline || {};
  const structural = summary.structural_play || {};
  const cf = lab.counterfactual;
  const targeted = lab.targeted_counterfactual;
  const suite = lab.mccfr_suite;
  const strength = lab.solver_strength;

  document.getElementById("evidence-pipeline").innerHTML = [
    metric(
      "1 · ISMCTS self-play",
      structural.attempted_games != null
        ? Number(structural.attempted_games).toLocaleString()
        : Number(lab.health.source.games || 0).toLocaleString(),
      `${esc(structural.policy || "ismcts")} · strategic progression, pacing, Command economy`
    ),
    metric(
      "2 · Heuristic paired screen",
      cf ? `${cf.cards.length} cards` : "—",
      cf
        ? `${cf.resolved_paired_samples ?? 0} resolved pairs · ${cf.censored_paired_samples ?? 0} censored`
        : "not generated"
    ),
    metric(
      "3 · Online MCCFR",
      targeted ? `${targeted.targets.length} targeted cards` : "—",
      targeted
        ? `${targeted.online_iterations} iterations · depth ${targeted.online_depth}`
        : "not generated"
    ),
    metric(
      "4 · Offline MCCFR",
      suite ? `${suite.profiles.length} policies` : "—",
      suite
        ? `${suite.covered_cards}/${suite.card_pool_size} card coverage · fallback reported per seat-swapped evaluation`
        : "not generated"
    ),
    metric(
      "5 · Search-strength check",
      strength ? `${strength.overall?.games ?? 0} decisive games` : "—",
      strength
        ? `ISMCTS vs alpha-beta · ${strength.games_per_orientation ?? "—"} games/deck/orientation`
        : "not generated"
    ),
  ].join("");

  const notes = [];
  notes.push(attentionItem(
    "good",
    "ISMCTS self-play is progression evidence",
    "Use canonical ISMCTS self-play to inspect pacing, Command preservation, Battle length and strategic progression. It is not collapsed into a single balance score."
  ));
  notes.push(attentionItem(
    "watch",
    "Broad ΔWP is only a screen",
    "The paired heuristic replacement controls seed, seat and deck context, but remains policy-specific. It nominates suspicious cards rather than resolving their value."
  ));
  notes.push(attentionItem(
    targeted?.targets?.length ? "good" : "pending",
    "Online MCCFR is targeted confirmation",
    targeted?.targets?.length
      ? "Online MCCFR re-solves the nominated paired contexts. Confirmed, reversed and inconclusive outcomes remain distinct."
      : "No targeted online-MCCFR result is present for this snapshot."
  ));
  notes.push(attentionItem(
    suite ? "good" : "pending",
    "Offline MCCFR is learned-policy evidence",
    suite
      ? "Each canonical deck has its own trained policy and seat-swapped evaluation. Policy coverage and heuristic fallback are shown rather than hidden."
      : "The six-profile offline MCCFR suite has not been generated for this snapshot."
  ));
  notes.push(attentionItem(
    strength ? "good" : "pending",
    "Solver strength is a separate sanity check",
    strength
      ? "The mirrored ISMCTS-vs-alpha-beta benchmark reports budgets, censoring, uncertainty and search-resource diagnostics. It does not override card or pacing evidence."
      : "No current solver-strength benchmark is present."
  ));
  document.getElementById("evidence-guidance").innerHTML = notes.join("");
}

function renderCards(lab) {
  const filter = document.getElementById("card-filter").value;
  let rows = [...lab.health.cards];

  if (["force", "bond", "name", "narrative", "stratagem"].includes(filter)) {
    rows = rows.filter((row) => canonicalType(row) === filter);
  } else if (["red", "orange", "yellow", "unobserved", "green", "dark_green"].includes(filter)) {
    rows = rows.filter((row) => row.balance_level === filter);
  }

  const order = { red: 0, orange: 1, yellow: 2, mechanics_pending: 3, unobserved: 4, green: 5, dark_green: 6 };
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
          <strong>${row.observed === false ? "—" : pct(row.play_rate_per_draw)}</strong>
          <span class="muted">${row.observed === false ? "no self-play exposure" : `${row.plays}/${row.draws} plays/draws`}</span>
        </td>
        <td data-label="Structural deadness">${pct(row.structural_dead_on_pass_rate)}<span class="muted">resource ${pct(row.resource_blocked_on_pass_rate)}</span></td>
        <td data-label="Front swing">${num(row.mean_immediate_front_swing, 1)} <span class="muted">z ${num(row.front_swing_z_within_type, 1)}</span></td>
        <td data-label="Screen ΔWP">${causal ? signedPct(causal.delta_win_probability) : "—"}<span class="muted">${causal ? interval(causal.ci95) : ""}</span></td>
        <td data-label="MCCFR validation">${online ? `${signedPct(online.online.effect)}<span class="muted">${esc(online.confirmation.replaceAll("_", " "))}</span>` : "—"}</td>
        <td data-label="Evidence">
          <details class="row-evidence">
            <summary>details</summary>
            <dl>
              <div><dt>Observed</dt><dd>${row.observed === false ? "No self-play exposure" : "Yes"}</dd></div>
              <div><dt>Final status source</dt><dd>${esc((row.balance_evidence_source || "observational").replaceAll("_", " "))}</dd></div>
              <div><dt>Engine sync</dt><dd>${esc(row.engine_sync || "implemented / no known pending marker")}</dd></div>
              <div><dt>Heuristic screen</dt><dd>${causal ? `${signedPct(causal.delta_win_probability)} · ${interval(causal.ci95)} · ${causal.samples ?? 0} resolved pairs` : "—"}</dd></div>
              <div><dt>Strategic validation</dt><dd>${online ? `${esc(online.confirmation.replaceAll("_", " "))} · ${signedPct(online.online.effect)} · ${online.online.samples ?? 0} resolved pairs` : "not targeted"}</dd></div>
              <div><dt>Structural dead turns</dt><dd>${pct(row.structural_unplayable_turn_rate)}</dd></div>
              <div><dt>Resource-blocked turns</dt><dd>${pct(row.resource_blocked_turn_rate)}</dd></div>
              ${row.hero ? `<div><dt>Hero allowance blocked</dt><dd>${pct(row.hero_allowance_blocked_turn_rate)}</dd></div><div><dt>Hero Command blocked</dt><dd>${pct(row.hero_command_blocked_turn_rate)}</dd></div><div><dt>Hero structurally blocked</dt><dd>${pct(row.hero_structural_blocked_turn_rate)}</dd></div>` : ""}
              <div><dt>Structural dead at Pass</dt><dd>${pct(row.structural_dead_on_pass_rate)}</dd></div>
              <div><dt>Unaffordable at Pass</dt><dd>${pct(row.resource_blocked_on_pass_rate)}</dd></div>
              ${row.hero ? `<div><dt>Hero allowance blocked at Pass</dt><dd>${pct(row.hero_allowance_blocked_on_pass_rate)}</dd></div><div><dt>Hero Command blocked at Pass</dt><dd>${pct(row.hero_command_blocked_on_pass_rate)}</dd></div><div><dt>Hero structurally blocked at Pass</dt><dd>${pct(row.hero_structural_blocked_on_pass_rate)}</dd></div>` : ""}
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
    metric("Attempted pairs/card", cf.samples, `${cf.contexts} contexts × ${cf.games_per_context} games`),
    metric("Resolved paired samples", Number(cf.resolved_paired_samples ?? 0).toLocaleString(), `${Number(cf.censored_paired_samples ?? 0).toLocaleString()} censored · ${pct(cf.pair_censor_rate ?? 0)} censor rate`),
    metric("Screening signals", significantCards, `of ${cf.cards.length} cards exclude zero under heuristic play`),
    metric("Screen policy", esc(cf.policy), "common-random-number pairing"),
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
      ${metric("Resolved paired samples", report.resolved_paired_samples ?? 0, `${report.censored_paired_samples ?? 0} censored · ${pct(report.pair_censor_rate ?? 0)} censor rate`)}
      ${metric("Resolver", `${report.online_iterations} iterations`, `depth ${report.online_depth}`)}
      ${metric("Resolved", report.targets.filter((r) => ["confirmed", "reversed"].includes(r.confirmation)).length, "confirmed or strategically reversed")}
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
    || lab.health.formations
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
            <td>
              ${row.games ?? "—"}
              <span class="muted">${row.decisive_games ?? Math.max(0, (row.games ?? 0) - (row.censored_games ?? 0) - (row.draws ?? 0) - (row.failed_games ?? 0))} decisive · ${row.censored_games ?? 0} censored</span>
            </td>
            <td>${
              (row.decisive_games ?? Math.max(0, (row.games ?? 0) - (row.censored_games ?? 0) - (row.draws ?? 0) - (row.failed_games ?? 0))) > 0
                ? (row.win_rates || []).map((v) => pct(v)).join(" / ")
                : "—"
            }</td>
            <td>${
              (row.decisive_games ?? Math.max(0, (row.games ?? 0) - (row.censored_games ?? 0) - (row.draws ?? 0) - (row.failed_games ?? 0))) > 0
                ? pct(row.first_player_win_rate)
                : "—"
            }</td>
            <td>
              <details class="row-evidence">
                <summary>details</summary>
                <dl>
                  <div><dt>Wins</dt><dd>${(row.wins || []).join("–")}</dd></div>
                  <div><dt>Censor rate</dt><dd>${pct(row.censor_rate)}</dd></div>
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

function renderCommandExperiment(lab) {
  const container = document.getElementById("command-experiment");
  const overview = document.getElementById("command-experiment-overview");
  const unavailable = document.getElementById("command-experiment-unavailable");
  if (!container || !overview || !unavailable) return;

  const profiles = lab.balance_comparisons?.profiles || {};
  const rows = Object.entries(profiles);
  if (!rows.length) {
    unavailable.hidden = false;
    overview.innerHTML = "";
    container.innerHTML = "";
    return;
  }
  unavailable.hidden = true;

  const weighted = (deckProfiles, getter) => {
    let total = 0;
    let weight = 0;
    for (const deck of deckProfiles) {
      const result = getter(deck);
      if (!result || result.value == null || !result.weight) continue;
      total += Number(result.value) * Number(result.weight);
      weight += Number(result.weight);
    }
    return weight ? total / weight : null;
  };
  const sum = (deckProfiles, getter) =>
    deckProfiles.reduce((total, deck) => total + Number(getter(deck) || 0), 0);

  const summaries = rows.map(([key, profile]) => {
    const deckProfiles = Object.values(profile.progression_profiles?.profiles || {});
    const games = sum(deckProfiles, (deck) => deck.games);
    const censored = sum(deckProfiles, (deck) => deck.censored_games);
    const firstSignalCommand = weighted(deckProfiles, (deck) => {
      const d = deck.progression?.resources?.command_at_first_signal;
      return { value: d?.mean, weight: d?.count };
    });
    const commandBeforeCollapse = weighted(deckProfiles, (deck) => {
      const d = deck.progression?.resources?.command_before_collapse;
      return { value: d?.mean, weight: d?.count };
    });
    const firstSignalCount = sum(deckProfiles, (deck) => deck.progression?.resources?.command_at_first_signal?.count);
    const passZero = sum(deckProfiles, (deck) => deck.progression?.resources?.first_signal_command_buckets?.["0"]);
    const passFourPlus = sum(deckProfiles, (deck) => deck.progression?.resources?.first_signal_command_buckets?.["4+"]);
    const collapseCount = sum(deckProfiles, (deck) => deck.progression?.resources?.command_before_collapse?.count);
    const matches = sum(deckProfiles, (deck) => deck.progression?.match_length?.matches);
    const reach3 = sum(deckProfiles, (deck) => deck.progression?.match_length?.battle_reach?.["3"]?.matches);
    const reach8 = sum(deckProfiles, (deck) => deck.progression?.match_length?.battle_reach?.["8"]?.matches);
    const reach12 = sum(deckProfiles, (deck) => deck.progression?.match_length?.battle_reach?.["12"]?.matches);
    const meanBattles = weighted(deckProfiles, (deck) => {
      const d = deck.progression?.match_length?.resolved_battles_per_match;
      return { value: d?.mean, weight: d?.count };
    });
    const maxBattle = Math.max(
      0,
      ...deckProfiles.map((deck) =>
        Number(deck.progression?.match_length?.final_battle_number?.max || 0)
      )
    );
    const resolvedBattles = sum(deckProfiles, (deck) => deck.progression?.battlefield_development?.battles);
    const collapsePointStarts = sum(deckProfiles, (deck) =>
      deck.progression?.low_command_stalls?.collapse_point_battle_starts
    );
    const bothCollapsePointStarts = sum(deckProfiles, (deck) =>
      deck.progression?.low_command_stalls?.both_at_collapse_point_battle_starts
    );
    const collapseTerminations = sum(deckProfiles, (deck) =>
      Number(deck.progression?.low_command_stalls?.simultaneous_collapse_terminations || 0)
      + Number(deck.progression?.low_command_stalls?.unequal_collapse_terminations || 0)
    );
    const noPaidOperations = sum(deckProfiles, (deck) =>
      deck.progression?.low_command_stalls?.battles_with_no_paid_operation
    );
    const stallDiagnosticBattles = sum(deckProfiles, (deck) =>
      deck.progression?.low_command_stalls?.diagnostic_battles
    );
    const lateCommand = (bucket) => weighted(deckProfiles, (deck) => {
      const d = deck.progression?.by_battle?.[bucket];
      return { value: d?.command_before_collapse, weight: d?.battles };
    });
    const guardDecisions = sum(deckProfiles, (deck) =>
      deck.decisions?.[profile.agent]?.command_guard_decisions
    );
    const guardOverrides = sum(deckProfiles, (deck) =>
      deck.decisions?.[profile.agent]?.command_guard_overrides
    );
    const agentDecisions = sum(deckProfiles, (deck) =>
      deck.decisions?.[profile.agent]?.decisions
    );
    return {
      key,
      agent: profile.agent || key.split("--")[0],
      recovery: `${profile.recovery_start ?? profile.rules?.command_recovery_start ?? "?"}-${profile.recovery_decrement ?? profile.rules?.command_recovery_decrement ?? "?"}`,
      recoveryFloor: Number(profile.recovery_floor ?? profile.rules?.command_recovery_floor ?? 1),
      games,
      censorRate: games ? censored / games : null,
      collapsePointStartRate: resolvedBattles ? collapsePointStarts / resolvedBattles : null,
      bothCollapsePointStartRate: resolvedBattles ? bothCollapsePointStarts / resolvedBattles : null,
      noPaidOperationRate: stallDiagnosticBattles ? noPaidOperations / stallDiagnosticBattles : null,
      firstSignalCommand,
      passZeroRate: firstSignalCount ? passZero / firstSignalCount : null,
      passFourPlusRate: firstSignalCount ? passFourPlus / firstSignalCount : null,
      guardOpportunityRate: agentDecisions ? guardDecisions / agentDecisions : null,
      guardOverrideRate: guardDecisions ? guardOverrides / guardDecisions : null,
      guardOverrides,
      commandBeforeCollapse,
      collapseTriggerRate: resolvedBattles ? collapseTerminations / resolvedBattles : null,
      reach3: matches ? reach3 / matches : null,
      reach8: matches ? reach8 / matches : null,
      reach12: matches ? reach12 / matches : null,
      meanBattles,
      maxBattle,
      battle47Command: lateCommand("4-7"),
      battle8Command: lateCommand("8+"),
      search: profile.agent_profile || {},
      policyCoverage: profile.summary?.policy_coverage || {},
      policyFingerprints: profile.summary?.policy_fingerprints || [],
    };
  }).sort((a, b) => a.key.localeCompare(b.key));

  const lowCommandMatches = rows.flatMap(([profileKey, profile]) =>
    Object.entries(profile.progression_profiles?.profiles || {}).flatMap(([deckName, deck]) => {
      const stalls = deck.progression?.low_command_stalls || {};
      const battleRecords = stalls.battle_records || [];
      return (stalls.games || []).map((game) => ({
        profileKey,
        deckName,
        agent: profile.agent || profileKey.split("--")[0],
        recovery: `${profile.recovery_start ?? profile.rules?.command_recovery_start ?? "?"}-${profile.recovery_decrement ?? profile.rules?.command_recovery_decrement ?? "?"}`,
        recoveryFloor: Number(profile.recovery_floor ?? profile.rules?.command_recovery_floor ?? 1),
        battleRecords: battleRecords.filter((record) =>
          game.simulation_game_index != null && record.simulation_game_index != null
            ? Number(record.simulation_game_index) === Number(game.simulation_game_index)
            : Number(record.game) === Number(game.game)
        ),
        ...game,
      }));
    })
  ).sort((left, right) =>
    Number(right.censored || 0) - Number(left.censored || 0)
    || Number(right.final_battle || 0) - Number(left.final_battle || 0)
    || String(left.profileKey).localeCompare(String(right.profileKey))
    || String(left.deckName).localeCompare(String(right.deckName))
    || Number(left.simulation_game_index ?? left.game ?? 0) - Number(right.simulation_game_index ?? right.game ?? 0)
  );
  const diagnosticMatches = lowCommandMatches.slice(0, 24);
  const focusMatch = diagnosticMatches[0] || null;
  const focusBattles = focusMatch
    ? [...(focusMatch.battleRecords || [])].sort((left, right) => Number(left.battle) - Number(right.battle))
    : [];
  const pair = (value) => Array.isArray(value) ? value.join(" / ") : "—";
  const operationTrace = (record) => (record.operation_trace || []).map((row) => {
    const alternatives = `${row.playable_card_actions ?? 0} card / ${row.maneuver_actions ?? 0} maneuver`;
    const cost = row.command_cost == null ? "" : ` · cost ${row.command_cost}`;
    const forced = row.forced ? " · forced" : "";
    const changes = [
      row.board_changed_transition ? "board" : null,
      row.strength_changed_transition ? "Strength" : null,
    ].filter(Boolean).join("+") || "no board/Strength change";
    return `P${row.player} ${row.category}${cost}${forced} · ${alternatives} · ${changes}`;
  }).join(" | ");

  overview.innerHTML = [
    metric("Profiles", summaries.length, "agent × recovery × floor conditions retained for this ruleset"),
    metric("Agents", new Set(summaries.map((row) => row.agent)).size, "distinct policies represented"),
    metric("Recovery formulas", new Set(summaries.map((row) => row.recovery)).size, "arithmetic start-decrement candidates"),
    metric("Recovery floors", [...new Set(summaries.map((row) => row.recoveryFloor))].join(", "), "minimum actual recovery after Front-loss penalties"),
    metric("Simulated games", summaries.reduce((n, row) => n + row.games, 0), "same-deck progression games across profiles"),
  ].join("");

  container.innerHTML = `
    <table class="mini-table">
      <thead><tr>
        <th>Agent</th><th>Recovery</th><th>Floor</th><th>Games</th><th>Censored</th>
        <th>Collapse-point start</th><th>Both at Collapse point</th><th>No paid Action</th>
        <th>Pass Command</th><th>Pass at 0</th><th>Pass at 4+</th>
        <th>Guard opportunity</th><th>Guard override</th>
        <th>Command before Collapse</th><th>Collapse trigger rate</th><th>Mean Battles</th><th>Max Battle</th>
        <th>Reach III</th><th>Reach VIII+</th><th>Reach XII+</th>
        <th>Pre-collapse Command IV-VII</th><th>Pre-collapse Command VIII+</th><th>Policy coverage</th><th>Search settings</th>
      </tr></thead>
      <tbody>${summaries.map((row) => `
        <tr>
          <td><strong>${esc(row.agent)}</strong></td>
          <td>${esc(row.recovery)}</td>
          <td>${row.recoveryFloor}</td>
          <td>${row.games}</td>
          <td>${pct(row.censorRate)}</td>
          <td>${pct(row.collapsePointStartRate)}</td>
          <td>${pct(row.bothCollapsePointStartRate)}</td>
          <td>${pct(row.noPaidOperationRate)}</td>
          <td>${num(row.firstSignalCommand, 1)}</td>
          <td>${pct(row.passZeroRate)}</td>
          <td>${pct(row.passFourPlusRate)}</td>
          <td>${pct(row.guardOpportunityRate)}</td>
          <td>${pct(row.guardOverrideRate)}${row.guardOverrides ? ` <span class="muted">(${row.guardOverrides})</span>` : ""}</td>
          <td>${num(row.commandBeforeCollapse, 1)}</td>
          <td>${pct(row.collapseTriggerRate)}</td>
          <td>${num(row.meanBattles, 1)}</td>
          <td>${row.maxBattle || "—"}</td>
          <td>${pct(row.reach3)}</td>
          <td>${pct(row.reach8)}</td>
          <td>${pct(row.reach12)}</td>
          <td>${num(row.battle47Command, 1)}</td>
          <td>${num(row.battle8Command, 1)}</td>
          <td>${row.agent === "mccfr"
            ? `${pct(row.policyCoverage.mccfr_coverage_rate)} MCCFR · ${pct(row.policyCoverage.fallback_rate)} fallback${row.policyFingerprints.length ? ` · <code>${esc(row.policyFingerprints.join(", "))}</code>` : ""}`
            : "—"}</td>
          <td><code>${esc(JSON.stringify(row.search[row.agent] || row.search))}</code></td>
        </tr>
      `).join("")}</tbody>
    </table>
    ${diagnosticMatches.length ? `
      <h3>Longest low-Command matches</h3>
      <p class="dashboard-note">Top 24 diagnostic matches across the retained comparison profiles, ordered by censoring and final Battle. Game index and seed identify the exact simulation.</p>
      <table class="mini-table">
        <thead><tr>
          <th>Agent</th><th>Recovery</th><th>Floor</th><th>Deck</th><th>Game</th><th>Seed</th><th>First</th>
          <th>Final Battle</th><th>Censored</th><th>First low</th>
          <th>Both at Collapse point starts</th><th>No paid op.</th><th>No board change</th>
        </tr></thead>
        <tbody>${diagnosticMatches.map((row) => `
          <tr>
            <td>${esc(row.agent)}</td>
            <td>${esc(row.recovery)}</td>
            <td>${row.recoveryFloor}</td>
            <td>${esc(row.deckName)}</td>
            <td>${row.simulation_game_index ?? row.game ?? "—"}</td>
            <td><code>${row.seed ?? "—"}</code></td>
            <td>${row.first_player ?? "—"}</td>
            <td>${row.final_battle ?? "—"}</td>
            <td>${row.censored ? "yes" : "no"}</td>
            <td>${row.first_low_command_battle ?? "—"}</td>
            <td>${row.both_at_collapse_point_battle_starts ?? 0}</td>
            <td>${row.battles_with_no_paid_operation ?? 0}</td>
            <td>${row.battles_with_no_board_change ?? 0}</td>
          </tr>
        `).join("")}</tbody>
      </table>
      ${focusMatch ? `
        <h3>Focused low-Command Battle trace</h3>
        <p class="dashboard-note">
          ${esc(focusMatch.agent)} · ${esc(focusMatch.recovery)} · floor ${focusMatch.recoveryFloor} ·
          ${esc(focusMatch.deckName)} · game ${focusMatch.simulation_game_index ?? focusMatch.game ?? "—"} ·
          seed <code>${focusMatch.seed ?? "—"}</code>. This is the first row above.
        </p>
        <table class="mini-table">
          <thead><tr>
            <th>Battle</th><th>Command start</th><th>Before Collapse</th><th>Base</th><th>Fronts lost</th>
            <th>Front-loss Command</th><th>Actual</th><th>After recovery</th><th>Collapse</th>
            <th>Operations and alternatives</th><th>Battlefield change</th><th>State</th>
          </tr></thead>
          <tbody>${focusBattles.map((record) => `
            <tr>
              <td>${record.battle ?? "—"}</td>
              <td>${esc(pair(record.command_start))}</td>
              <td>${esc(pair(record.command_before_collapse))}</td>
              <td>${record.recovery_base ?? "—"}</td>
              <td>${esc(pair(record.fronts_lost))}</td>
              <td>${esc(pair(record.front_loss_command_penalty))}</td>
              <td>${esc(pair(record.recovery_actual))}</td>
              <td>${esc(pair(record.command_after_recovery))}</td>
              <td>${record.collapse_comparison?.equal ? "equal" : "unequal"} · ${record.collapse_comparison?.continued ? "continue" : "end"}</td>
              <td><code>${esc(operationTrace(record) || "—")}</code></td>
              <td>board ${record.board_changed_during_battle ? "changed" : "same"} · Strength ${record.strength_changed_during_battle ? "changed" : "same"} · resolution board ${record.board_changed_during_resolution ? "changed" : "same"}</td>
              <td>
                <details><summary>signatures</summary>
                  <code>start ${esc(JSON.stringify(record.board_start_signature))}</code><br>
                  <code>end ${esc(JSON.stringify(record.board_end_signature))}</code><br>
                  <code>next ${esc(JSON.stringify(record.next_battle_board_signature))}</code><br>
                  <code>Strength start ${esc(JSON.stringify(record.strength_start))}</code><br>
                  <code>Strength next ${esc(JSON.stringify(record.next_battle_strength_by_front))}</code>
                </details>
              </td>
            </tr>
          `).join("")}</tbody>
        </table>
      ` : ""}
    ` : ""}
  `;
}


function renderNarrativeAblation(lab) {
  const el = document.getElementById("narrative-ablation");
  if (!el) return;
  const report = lab.narrative_ablation;
  const rows = Object.values(report?.profiles || {});
  if (!rows.length) {
    el.innerHTML = '<p class="muted">Narrative/Command ablation evidence has not been generated for this ruleset.</p>';
    return;
  }
  const dmean = (d) => d?.mean == null ? "—" : num(d.mean, 1);
  const dmax = (d) => d?.max == null ? "—" : num(d.max, 0);
  const commandSources = (summary) => {
    const sources = summary?.command_by_source || {};
    const baggage = sources["the-baggage-was-abandoned"] || {};
    const rallied = sources["rallied-behind"] || {};
    const noRoad = sources["no-road-was-too-long"] || {};
    return "Baggage +" + Number(baggage.command_gained || 0).toLocaleString()
      + " · Rallied saved " + Number(rallied.discount_saved || 0).toLocaleString()
      + " · No Road +" + Number(noRoad.command_gained || 0).toLocaleString();
  };
  let body = "";
  for (const row of rows) {
    const s = row.summary || {};
    const cards = (row.card_overrides || []).map((x) => x.card).join(", ") || "canonical baseline";
    body += "<tr>"
      + "<td><strong>" + esc(row.variant) + "</strong><span class=\"muted\">" + esc(cards) + "</span></td>"
      + "<td>" + (s.decisive_games ?? "—") + " / " + (s.games ?? "—") + "</td>"
      + "<td>" + pct(s.censor_rate) + "</td>"
      + "<td>" + dmean(s.resolved_battles_per_match) + "</td>"
      + "<td>" + dmax(s.final_battle_number) + "</td>"
      + "<td>" + dmean(s.command_before_collapse) + "</td>"
      + "<td>" + dmean(s.command_at_first_signal) + "</td>"
      + "<td>" + esc(commandSources(s)) + "</td>"
      + "<td>" + (s.longest_low_positive_streak ?? "—") + "</td>"
      + "</tr>";
  }
  el.innerHTML =
    "<h3>Narrative / Command ablations</h3>"
    + "<p class=\"dashboard-note\">" + esc(report.methodology || "") + "</p>"
    + "<table class=\"mini-table\"><thead><tr>"
    + "<th>Variant</th><th>Decisive / games</th><th>Censored</th>"
    + "<th>Mean Battles</th><th>Max Battle</th><th>Pre-collapse Command</th>"
    + "<th>Pass Command</th><th>Suspect Command sources</th><th>Longest 1-3 streak</th>"
    + "</tr></thead><tbody>" + body + "</tbody></table>";
}

function renderProgression(lab) {
  const profiles = lab.progression_profiles || {};
  const selector = document.getElementById("progression-profile");
  const profileKeys = Object.keys(profiles);
  let profile = null;

  if (selector && profileKeys.length) {
    if (!selector.options.length) {
      selector.innerHTML = profileKeys.map((key) =>
        '<option value="' + esc(key) + '">' + esc(profiles[key].label || titleCase(key)) + '</option>'
      ).join("");
    }
    selector.hidden = false;
    const selectedKey = selector.value && profiles[selector.value]
      ? selector.value
      : profileKeys[0];
    selector.value = selectedKey;
    profile = profiles[selectedKey];
  } else if (selector) {
    selector.hidden = true;
  }

  const p = profile?.progression || lab.progression || lab.raw_telemetry?.progression;
  const source = profile
    ? {
        label: profile.label,
        games: profile.games,
        decisive_games: profile.decisive_games,
        censored_games: profile.censored_games,
        scope: "One of six canonical same-deck progression profiles.",
      }
    : lab.progression_source;
  const sourceNote = document.getElementById("progression-source-note");
  if (sourceNote) {
    if (source?.label || source?.scope) {
      const counts = source.games == null
        ? ""
        : ` ${source.games} games · ${source.decisive_games ?? source.games} decisive · ${source.censored_games ?? 0} censored.`;
      sourceNote.textContent = ` Detailed panel: ${source.label || "self-play"}.${counts} ${source.scope || ""}`;
    } else {
      sourceNote.textContent = "";
    }
  }
  const unavailable = document.getElementById("progression-unavailable");
  if (!p) {
    unavailable.hidden = false;
    return;
  }
  const currentProgressionSchema = (
    p.mechanical_choice?.effect_resolution_decisions != null
    && Object.prototype.hasOwnProperty.call(
      p.formation_lifecycle || {},
      "incomplete_removed_during_battle"
    )
    && (
      Object.prototype.hasOwnProperty.call(p.by_battle || {}, "4-7")
      || Object.prototype.hasOwnProperty.call(p.by_battle || {}, "8+")
    )
  );
  if (!currentProgressionSchema) {
    unavailable.hidden = false;
    unavailable.textContent =
      "Published progression telemetry predates the corrected measurement semantics. Run a fresh balance simulation to regenerate all six reference-deck profiles.";
    return;
  }
  unavailable.hidden = true;

  const life = p.formation_lifecycle || {};
  const field = p.battlefield_development || {};
  const contest = p.contestability || {};
  const choice = p.mechanical_choice || {};
  const resources = p.resources || {};
  const lowCommand = p.low_command_stalls || {};
  const matchLength = p.match_length || {};
  const trajectory = profile?.trajectory || lab.progression_trajectory || {};
  const trajectoryMetrics = trajectory.metrics || {};
  const trajectoryElement = document.getElementById("progression-trajectory");
  if (trajectoryElement) {
    const label = trajectory.early_battle && trajectory.late_battle
      ? `Battle ${trajectory.early_battle} → ${trajectory.late_battle}`
      : "first → latest observed Battle";
    const trajectoryCard = (title, field, percent = false) => {
      const row = trajectoryMetrics[field] || {};
      const format = percent ? pct : (value) => num(value, 1);
      const delta = percent ? signedPct(row.delta) : signedNum(row.delta, 1);
      return metric(title, `${format(row.early)} → ${format(row.late)}`, `${label} · Δ ${delta}`);
    };
    trajectoryElement.innerHTML = [
      trajectoryCard("Command at Battle end", "command_remaining"),
      trajectoryCard("Pass Command", "first_signal_command"),
      trajectoryCard("Occupied positions", "occupied_positions"),
      trajectoryCard("Contested Fronts", "contested_fronts"),
      trajectoryCard("Completed formations", "completed_formations"),
      trajectoryCard("Force completion rate", "eventual_completion_rate_for_forces_deployed", true),
      trajectoryCard("Legal choices", "legal_actions"),
      trajectoryCard("Deck cards remaining", "deck_size"),
    ].join("");
  }

  document.getElementById("progression-battlefield").innerHTML = [
    metric("Force → Bond", pct(life.force_to_bond_rate), `${life.forces_ever_bonded ?? 0} of ${life.forces ?? 0} Force lifecycles`),
    metric("Force → Name", pct(life.force_to_name_rate), `${life.forces_ever_named ?? 0} eventually Named`),
    progressionMetric("Active Fronts", field.active_fronts, "rules-active Fronts for that Battle"),
    progressionMetric("Developed Fronts", field.developed_fronts, "active Fronts containing at least one Force"),
    progressionMetric("Contested Fronts", field.contested_fronts, "active Fronts with Forces on both sides"),
    progressionMetric("Partial at Battle end", life.partial_at_battle_end_per_player, "persistent partial formations per player-Battle"),
    metric("Incomplete removed during Battle", life.incomplete_removed_during_battle ?? 0, "card effect or explicit Retreat before completion"),
    progressionMetric("Empty Fronts", field.empty_fronts, "median per Battle decision"),
    progressionMetric("Strength concentration", field.strength_concentration, "median strongest-Front share per player"),
    progressionMetric("Force → Name time", life.force_to_name_actions, "median actions"),
  ].join("");

  const reach = matchLength.battle_reach || {};
  document.getElementById("progression-contestability").innerHTML = [
    progressionMetric("Battles resolved / match", matchLength.resolved_battles_per_match, "median per simulated match"),
    metric("Reach Battle III", pct(reach["3"]?.rate), `${reach["3"]?.matches ?? 0} matches`),
    metric("Reach Battle IV+", pct(reach["4"]?.rate), `${reach["4"]?.matches ?? 0} matches`),
    metric("Reach Battle VIII+", pct(reach["8"]?.rate), `${reach["8"]?.matches ?? 0} matches`),
    metric("Collapse-point Battle starts", matchLength.collapse_point_start_battles ?? 0, "Battle starts with at least one side at or below the configured Collapse threshold"),
    metric("Censored at Collapse point", matchLength.censored_at_collapse_point_matches ?? 0, "simulation-horizon matches ending with at least one side at or below the Collapse threshold"),
    progressionMetric("Front-control changes", contest.front_control_changes_per_battle, "median per Battle"),
    progressionMetric("Final |margin|", contest.final_abs_margin, "median total-Strength margin"),
    progressionMetric("Max |margin|", contest.maximum_abs_margin, "median Battle maximum"),
    progressionMetric("Battle length", contest.actions_per_battle, "median Action / turn-control decisions"),
    progressionMetric("Durable lead", contest.durable_lead_action, "median action when measurable"),
    progressionMetric("Actions after durable lead", contest.actions_remaining_after_durable_lead, "median when measurable"),
    metric("No later control change", pct(contest.no_control_change_after_midpoint_rate), "after Battle midpoint"),
  ].join("");

  const passCategories = choice.signal_mechanical_categories || {};
  document.getElementById("progression-choice").innerHTML = [
    progressionMetric("Legal actions", choice.legal_action_count, "median per decision"),
    progressionMetric("Card-play options", choice.card_play_option_count, "median legal card Actions"),
    progressionMetric("Maneuver options", choice.maneuver_option_count, "median legal Maneuvers"),
    metric("Exactly one legal action", pct(choice.exactly_one_legal_action_rate), `${choice.exactly_one_legal_action ?? 0} decisions`),
    metric("Forced Maneuver", pct(choice.forced_maneuver_rate), `${choice.forced_maneuvers ?? 0} decisions`),
    metric("Forced Passes", passCategories.no_alternative ?? 0, "Pass is legal only when no Action is available"),
    metric(
      "Constraint source / active",
      `${pct(choice.constraint_rule_source_rate)} / ${choice.constraint_active_supported ? pct(choice.constraint_active_rate) : "not instrumented"}`,
      choice.constraint_active_supported
        ? "public source present / native next-Action obligation active"
        : "active restriction needs native constraint state"
    ),
    metric(
      "Constraint options removed",
      num(choice.constraint_options_removed?.mean, 1),
      `${choice.constraint_options_removed?.count ?? 0} constrained decisions · max ${num(choice.constraint_options_removed?.max, 0)}`
    ),
    metric(
      "Constraint outcomes",
      `${Object.values(choice.constraint_satisfied || {}).reduce((a, b) => a + b, 0)} satisfied / ${Object.values(choice.constraint_impossible || {}).reduce((a, b) => a + b, 0)} impossible`,
      `${choice.constraint_expired ?? 0} expired · ${choice.constraint_carried_between_battles ?? 0} carried across Battle`
    ),
    metric(
      "Constraint forcing",
      `${choice.constraint_forced_maneuver_decisions ?? 0} Maneuver / ${choice.constraint_forced_front_decisions ?? 0} Front`,
      `${choice.constraint_future_operations_affected ?? 0} future-Action decisions affected`
    ),
    metric("Effect-resolution decisions", choice.effect_resolution_decisions ?? 0, "excluded from ordinary Action-choice metrics"),
  ].join("");

  const commandDist = resources.command_remaining_at_battle_end || {};
  const commandBuckets = resources.command_end_buckets || {};
  const zeroRate = commandDist.count ? (commandBuckets["0"] || 0) / commandDist.count : null;
  document.getElementById("progression-resources").innerHTML = [
    progressionMetric("Command at Battle end", commandDist, "median per player-Battle"),
    progressionMetric("Command at Pass", resources.command_at_first_signal, "median passer"),
    metric("Ends at 0 Command", pct(zeroRate), `${commandBuckets["0"] || 0} player-Battles`),
    metric("Free Maneuvers", resources.free_maneuvers ?? 0, "actual zero-Command Maneuvers"),
    metric("Discounted actions", resources.discount_actions ?? 0, `${resources.discount_command_saved ?? 0} Command saved`),
    metric("Command regained", resources.command_gained_or_refunded ?? 0, "Action gains/refunds; Battle recovery excluded"),
    metric(
      "Card / Maneuver spend",
      `${resources.command_spend?.card_play ?? 0} / ${resources.command_spend?.maneuver ?? 0}`,
      "actual Command paid by category"
    ),
    metric("Free Actions", resources.free_operations ?? 0, "zero-Command card plays or Maneuvers"),
    metric("Collapse-point Battle starts", lowCommand.collapse_point_battle_starts ?? 0, "at least one side begins at or below the configured Collapse threshold"),
    metric("Both at Collapse point", lowCommand.both_at_collapse_point_battle_starts ?? 0, "both sides begin at or below the configured Collapse threshold"),
    metric("Passes at 0 Command", resources.first_signal_command_buckets?.["0"] ?? 0, "forced Pass events at the Collapse threshold"),
    metric("No paid Action", lowCommand.battles_with_no_paid_operation ?? 0, "Battles with no Command-paying card play or Maneuver"),
    metric("No in-Battle board change", lowCommand.battles_with_no_board_change ?? 0, "board unchanged between first and final decision state"),
  ].join("");

  const commandSourceElement = document.getElementById("progression-command-sources");
  if (commandSourceElement) {
    const commandTitles = new Map((lab.health?.cards || []).map((card) => [card.id, card.title]));
    const sourceRows = Object.entries(resources.command_by_source || {})
      .map(([id, stats]) => ({ id, ...stats }))
      .sort((a, b) =>
        Number(b.command_gained || 0) + Number(b.discount_saved || 0) + Number(b.front_loss_command_avoided || 0)
        - Number(a.command_gained || 0) - Number(a.discount_saved || 0) - Number(a.front_loss_command_avoided || 0)
      );
    let sourceBody = "";
    for (const row of sourceRows) {
      sourceBody += "<tr>"
        + "<td><strong>" + esc(commandTitles.get(row.id) || row.id) + "</strong><span class=\"muted\"><code>" + esc(row.id) + "</code></span></td>"
        + "<td>" + (row.triggers ?? 0) + "</td>"
        + "<td>" + (row.command_gained ?? 0) + "</td>"
        + "<td>" + (row.nominal_command_gain ?? row.command_gained ?? 0) + "</td>"
        + "<td>" + (row.discount_saved ?? 0) + "</td>"
        + "<td>" + (row.free_operations ?? 0) + "</td>"
        + "<td>" + (row.front_loss_command_avoided ?? 0) + "</td>"
        + "</tr>";
    }
    commandSourceElement.innerHTML = sourceRows.length
      ? "<h3>Command economy by source</h3>"
        + "<table class=\"mini-table\"><thead><tr>"
        + "<th>Source</th><th>Triggers</th><th>Gained</th><th>Nominal gain</th>"
        + "<th>Discount saved</th><th>Free Actions</th><th>Front-loss Command avoided</th>"
        + "</tr></thead><tbody>" + sourceBody + "</tbody></table>"
      : '<p class="muted">No source-attributed Command events in this profile.</p>';
  }

  const battles = p.by_battle || {};
  document.getElementById("progression-battles").innerHTML = ["1", "2", "3", "4-7", "8+"].map((key) => {
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
          <span class="muted">constraint source/active ${pct(row.constraint_rule_source_rate)} / ${choice.constraint_active_supported ? pct(row.constraint_active_rate) : "not instrumented"}</span>
        </td>
        <td>${num(row.hand_size, 1)} / ${num(row.deck_size, 1)}</td>
        <td>
          cmd ${num(row.first_signal_command, 1)}
          <span class="muted">structural ${num(row.first_signal_structurally_dead_cards, 1)} · unaffordable ${num(row.first_signal_unaffordable_cards, 1)} · card ${num(row.first_signal_playable_card_actions, 1)} · Maneuver ${num(row.first_signal_maneuver_actions, 1)}</span>
        </td>
        <td>
          ${num(row.command_start, 1)} / ${num(row.command_spent, 1)} / ${num(row.command_remaining, 1)}
          <span class="muted">before recovery · next ${num(row.next_battle_command, 1)}</span>
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

  const firstSignal = contest.first_signal_outcomes || {};
  const passRows = [
    ["Already ahead", firstSignal.ahead],
    ["Tied", firstSignal.tied],
    ["Behind", firstSignal.behind],
    ["Playable alternatives", firstSignal.with_playable_alternatives],
    ["No alternative", firstSignal.no_alternative],
  ];
  const cardLifecycle = Object.entries(p.cards || {})
    .sort((a, b) =>
      ((b[1].unplayed_at_match_end || 0) + (b[1].held_across_battle_boundaries || 0) + (b[1].discarded_without_play || 0)) -
      ((a[1].unplayed_at_match_end || 0) + (a[1].held_across_battle_boundaries || 0) + (a[1].discarded_without_play || 0))
    )
    .slice(0, 12);
  const definitions = Object.entries(p.definitions || {});
  const lowCommandGames = [...(lowCommand.games || [])].sort((left, right) =>
    Number(right.censored || 0) - Number(left.censored || 0)
    || Number(right.final_battle || 0) - Number(left.final_battle || 0)
    || Number(left.simulation_game_index ?? left.game ?? 0) - Number(right.simulation_game_index ?? right.game ?? 0)
  );

  document.getElementById("progression-diagnostics").innerHTML = `
    <div class="two-column-tables">
      <div>
        <h3>Pass state and final Front balance</h3>
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
    <div>
      <h3>Low-Command match diagnosis</h3>
      <p class="dashboard-note">Exact simulation identity is retained so a pathological match can be replayed from its seed. Rows are ordered by censoring, final Battle, then equal-low streak length.</p>
      <div class="table-wrap fitted-table">
        <table class="mini-table">
          <thead><tr>
            <th>Game</th><th>Seed</th><th>First</th><th>Final Battle</th><th>Censored</th>
            <th>First low</th><th>First equal-low</th><th>Equal-low</th><th>Longest streak</th>
            <th>0/0 starts</th><th>No paid op.</th><th>No board change</th>
          </tr></thead>
          <tbody>${lowCommandGames.length ? lowCommandGames.map((row) => `
            <tr>
              <td>${row.simulation_game_index ?? row.game ?? "—"}</td>
              <td><code>${row.seed ?? "—"}</code></td>
              <td>${row.first_player ?? "—"}</td>
              <td>${row.final_battle ?? "—"}</td>
              <td>${row.censored ? "yes" : "no"}</td>
              <td>${row.first_low_command_battle ?? "—"}</td>
                    <td>${row.both_at_collapse_point_battle_starts ?? 0}</td>
              <td>${row.battles_with_no_paid_operation ?? 0}</td>
              <td>${row.battles_with_no_board_change ?? 0}</td>
            </tr>
          `).join("") : '<tr><td colspan="12" class="muted">No low-Command diagnostic matches observed.</td></tr>'}</tbody>
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
  const t = lab.dashboard_telemetry || lab.raw_telemetry;
  if (!t) return;
  const p = t.passes || {};
  const b = t.battles || {};
  document.getElementById("telemetry-grid").innerHTML = [
    metric("Battles", b.count ?? "—", `mean actions ${num(b.mean_actions, 1)}`),
    metric("Battle Strength", num(b.mean_total_strength, 1), `mean |margin| ${num(b.mean_abs_total_margin, 1)}`),
    metric("Pass events", p.events ?? "—", `mean hand ${num(p.mean_hand_size, 1)}`),
    metric("Mean Pass Command", num(p.mean_command_at_pass, 1), "Pass is forced once per resolved Battle"),
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


function renderSolverStrength(lab) {
  const el = document.getElementById("solver-strength");
  if (!el) return;
  const report = lab.solver_strength;
  if (!report) {
    el.innerHTML = '<p class="muted">No current ISMCTS vs alpha-beta strength benchmark.</p>';
    return;
  }
  const overall = report.overall || {};
  const ci = overall.paired_uncertainty?.ci95 || [null, null];
  const decks = report.decks || {};
  const censored = Object.values(decks).reduce((n, row) => n + Number(row.censored || 0), 0);
  let rows = "";
  for (const [deck, row] of Object.entries(decks)) {
    rows += "<tr><td><strong>" + esc(titleCase(deck)) + "</strong></td>"
      + "<td>" + (row.mcts ?? 0) + " - " + (row.alpha ?? 0) + "</td>"
      + "<td>" + (row.games ?? 0) + "</td>"
      + "<td>" + (row.censored ?? 0) + "</td></tr>";
  }
  const cutoff = report.ismcts?.rollout_cutoffs || {};
  const reuse = report.ismcts?.tree_reuse || {};
  const mctsResources = report.resources?.ismcts || {};
  const alphaResources = report.resources?.strategic_heuristic || {};
  el.innerHTML =
    "<h3>ISMCTS vs alpha-beta strength sanity check</h3>"
    + "<p class=\"dashboard-note\">" + esc(report.methodology || "") + "</p>"
    + "<div class=\"metric-grid compact-grid\">"
    + metric("Mirrored decisive games", overall.games ?? "—", censored + " censored")
    + metric("ISMCTS win rate", pct(overall.mcts_win_rate), "95% paired " + interval(ci))
    + metric("Equal search budget", (report.ismcts?.time_budget_seconds ?? "—") + " s", "per non-forced searched decision")
    + metric("ISMCTS work ceiling", Number(report.ismcts?.iterations || 0).toLocaleString(), "iterations")
    + metric("Alpha-beta ceiling", Number(report.alpha_beta?.node_budget || 0).toLocaleString(), "nodes")
    + metric("Root reuse", pct(reuse.root_reuse_rate), (reuse.tree_capacity_cutoffs ?? 0) + " capacity cutoffs")
    + metric("Rollout terminal / boundary / depth", pct(cutoff.terminal_rate) + " / " + pct(cutoff.battle_boundary_rate) + " / " + pct(cutoff.depth_rate), "cutoff shares")
    + metric("Mean search time", num(mctsResources.mean_searched_decision_seconds, 3) + " / " + num(alphaResources.mean_searched_decision_seconds, 3) + " s", "ISMCTS / alpha-beta")
    + "</div>"
    + "<table class=\"mini-table\"><thead><tr><th>Deck</th><th>ISMCTS - alpha-beta</th><th>Decisive</th><th>Censored</th></tr></thead><tbody>"
    + rows + "</tbody></table>";
}

function renderMccfr(lab) {
  const suite = lab.mccfr_suite;
  const verification = lab.verification;
  const profiles = document.getElementById("mccfr-profiles");

  if (suite) {
    document.getElementById("mccfr-overview").innerHTML = [
      metric("Card coverage", `${suite.covered_cards}/${suite.card_pool_size}`, pct(suite.coverage_fraction) + " of current pool"),
      metric("Deck profiles", suite.profiles.length, "all canonical reference decks"),
      metric("Policies", suite.profiles.length, "one mirror policy per deck profile"),
      metric("Missing cards", suite.missing_cards.length, suite.missing_cards.length ? suite.missing_cards.join(", ") : "none"),
    ].join("");

    profiles.innerHTML = `
      <table class="balance-table mccfr-table">
        <thead><tr><th>Deck profile</th><th>Unique cards</th><th>Iterations / traversals</th><th>Infosets</th><th>Depth</th><th>MCCFR vs heuristic</th><th>Policy coverage / fallback</th><th>Eval games</th></tr></thead>
        <tbody>
          ${suite.profiles.map((row) => `
            <tr>
              <td><strong>${esc(row.label)}</strong><span class="muted">${esc(row.deck)} · <code>${esc(row.policy.policy_fingerprint || "")}</code></span></td>
              <td>${row.deck_unique_cards}</td>
              <td>${row.policy.iterations ?? "—"}<span class="muted">${Number(row.policy.traversals || row.policy.training_summary?.traversals || 0).toLocaleString()} traversals</span></td>
              <td>${Number(row.policy.information_sets || 0).toLocaleString()}</td>
              <td>${row.policy.max_depth ?? "—"}</td>
              <td><strong>${pct(row.evaluation.seat_swapped_mccfr_win_rate)}</strong><span class="muted">seat-swapped · decisive games</span></td><td><strong>${pct(row.evaluation.seat_swapped_policy_coverage?.mccfr_coverage_rate)}</strong><span class="muted">${Number(row.evaluation.seat_swapped_policy_coverage?.mccfr_decisions || 0).toLocaleString()} MCCFR decisions · ${Number(row.evaluation.seat_swapped_policy_coverage?.heuristic_fallback_decisions || 0).toLocaleString()} heuristic fallbacks (${pct(row.evaluation.seat_swapped_policy_coverage?.heuristic_fallback_rate)})</span></td>
              <td>
                ${row.evaluation.games}
                <span class="muted">${row.evaluation.decisive_games ?? row.evaluation.games} decisive · ${row.evaluation.censored_games ?? 0} censored</span>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
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
        ${rows.map((r) => `<tr><td><code>${esc([r.force,r.bond,r.name].join(" · "))}</code></td><td>${r.static_strength}</td><td>${num(r.z_score,2)}</td></tr>`).join("")}
      </tbody>
    </table>
  `;
}

function renderStatic(lab) {
  const s = lab.static;
  document.getElementById("static-overview").innerHTML = [
    metric("Static combinations", s.formation_count, "Force × Bond × Name"),
    metric("Mean Strength", num(s.static_strength.mean, 2), `σ ${num(s.static_strength.population_sd, 2)}`),
    metric("Range", `${s.static_strength.min}–${s.static_strength.max}`, "static Strength only"),
  ].join("");
  document.getElementById("static-high").innerHTML = staticTable(s.highest_static_formations);
  document.getElementById("static-low").innerHTML = staticTable(s.lowest_static_formations);
}

function renderMethod(lab) {
  const report = lab.health;
  document.getElementById("methodology").innerHTML = `
    <p><strong>Card status:</strong> red = multiple high-confidence issues; orange = one high-confidence or multiple watch issues; yellow = one watch issue; unobserved = no self-play exposure; green = no current issue but thinner evidence; dark green = no issue with strong evidence.</p>
    <p><strong>Intervals:</strong> ${esc(report.methodology.win_intervals)}.</p>
    <p><strong>Board swing:</strong> standardized within card type.</p>
    <p><strong>Screen ΔWP:</strong> heuristic paired win-probability difference between the canonical card and a neutral same-type baseline under identical random seeds. It nominates candidates; it is not strong-play confirmation.</p>
    <p><strong>Online MCCFR validation:</strong> suspicious screen effects are rerun in the same paired contexts with online MCCFR. “Confirmed” means the online interval excludes zero in the same direction; “reversed” means it excludes zero in the opposite direction.</p>
    <p><strong>Censoring:</strong> if either side of a paired A/B comparison reaches the action horizon, that pair is reported as censored and excluded from the effect estimate.</p>
    <p><strong>Card deadness:</strong> current telemetry separates structural illegality while a card is affordable from simple Command shortfall, and excludes pending effect-resolution choices from operation playability.</p>
    <ul>${report.methodology.notes.map((note) => `<li>${esc(note)}</li>`).join("")}</ul>
  `;
}

async function main() {
  const [response, cardsResponse] = await Promise.all([
    fetch("data/lab-report.json", { cache: "no-cache" }),
    fetch("data/cards.json", { cache: "no-cache" }),
  ]);
  if (!response.ok) throw new Error("Full Balance Lab report is not available yet.");
  const lab = await response.json();
  if (lab.schema_version !== 2) {
    throw new Error("Balance Lab data uses an unsupported schema. Regenerate the Lab artifacts.");
  }
  const cardData = cardsResponse.ok ? await cardsResponse.json() : { cards: [] };
  annotateMechanicsCoverage(lab, cardData);

  renderAttention(lab);
  renderOverview(lab);
  renderEvidencePipeline(lab);
  renderCommandExperiment(lab);
  renderNarrativeAblation(lab);
  renderProgression(lab);
  renderCards(lab);
  renderCounterfactual(lab);
  renderTargetedCounterfactual(lab);
  renderSequences(lab);
  renderMatchups(lab);
  renderTelemetry(lab);
  renderSolverStrength(lab);
  renderMccfr(lab);
  renderStatic(lab);
  renderMethod(lab);

  document.getElementById("card-filter").addEventListener("change", () => renderCards(lab));
  const progressionProfile = document.getElementById("progression-profile");
  if (progressionProfile && !progressionProfile.hidden) {
    progressionProfile.addEventListener("change", () => renderProgression(lab));
  }
}

main().catch((error) => {
  document.getElementById("attention-summary").innerHTML =
    attentionItem("high", "Balance Lab unavailable", esc(error.message));
  document.getElementById("overview").innerHTML = "";
});
