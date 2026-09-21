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

function renderOverview(lab) {
  const h = lab.health;
  const g = h.global;
  const s = h.summary;
  const verification = lab.verification;
  document.getElementById("overview").innerHTML = [
    metric("Games", Number(h.source.games).toLocaleString(), h.source.agents.join(" vs ")),
    metric("First-player win", pct(g.first_player_win_rate), `95% ${interval(g.first_player_win_rate_95)}`),
    metric("Mean actions", num(g.mean_actions, 1), `max ${g.max_actions}`),
    metric("Cards", s.cards_analyzed, `${s.flags_high} high · ${s.flags_watch} watch flags`),
    metric("Legends observed", s.legends_observed, `of ${lab.static.legend_count} static combinations`),
    metric("MCCFR verification", verification ? (verification.passed ? "PASS" : "FAIL") : "—",
      verification ? `exploitability ${num(verification.exploitability, 4)}` : "not generated"),
  ].join("");
}

function renderCards(lab) {
  const filter = document.getElementById("card-filter").value;
  let rows = [...lab.health.cards];

  if (["subject", "link", "name", "plot"].includes(filter)) {
    rows = rows.filter((row) => row.type === filter);
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
    return `
      <tr class="grade-row grade-row-${row.balance_level}">
        <td>${grade(row)}</td>
        <td>
          <strong>${esc(row.title)}</strong>
          <div class="card-rule-inline">${esc(row.text)}</div>
        </td>
        <td>${esc(row.type)}${row.unique ? ' <span class="muted">unique</span>' : ""}</td>
        <td>${row.strength ?? "—"}</td>
        <td>${row.draws} / ${row.plays}</td>
        <td>${pct(row.play_rate_per_draw)}</td>
        <td>${pct(row.unplayable_turn_rate)}</td>
        <td>${pct(row.dead_on_pass_rate)}</td>
        <td>${num(row.mean_immediate_front_swing, 1)} <span class="muted">z ${num(row.front_swing_z_within_type, 1)}</span></td>
        <td>${num(row.mean_immediate_control_swing, 2)}</td>
        <td>${pct(row.win_rate_when_drawn)} <span class="muted">${interval(row.win_rate_when_drawn_95)}</span></td>
        <td>${pct(row.win_rate_when_played)} <span class="muted">${interval(row.win_rate_when_played_95)}</span></td>
        <td>${staticDelta == null ? "—" : (staticDelta >= 0 ? "+" : "") + num(staticDelta, 2)}</td>
        <td class="flags-cell">${flagMarkup(row.flags)}</td>
      </tr>
    `;
  }).join("");
}

function renderLegends(lab) {
  const rows = [...(lab.all_legends || lab.health.legends)];
  const observed = rows.filter((row) => row.observed !== false).length;
  document.getElementById("legend-count").textContent = `${rows.length} possible · ${observed} observed`;
  document.getElementById("legend-table").innerHTML = rows.map((row) => `
    <tr class="${row.flags.length ? "flagged-row" : ""}">
      <td><strong>${esc(row.title)}</strong></td>
      <td>${row.completions}</td>
      <td>${row.games_seen}</td>
      <td>${num(row.mean_strength_at_completion, 1)}</td>
      <td>${row.static_strength ?? "—"}</td>
      <td>${num(row.static_z, 2)}</td>
      <td>${pct(row.win_rate_when_seen)}</td>
      <td>${interval(row.win_rate_when_seen_95)}</td>
      <td class="flags-cell">${flagMarkup(row.flags)}</td>
    </tr>
  `).join("");
}

function renderMatchups(lab) {
  const rows = Object.entries(lab.matchups || {}).filter(([, value]) => value);
  document.getElementById("matchups").innerHTML = `
    <table class="balance-table">
      <thead><tr><th>Run</th><th>Agents</th><th>Games</th><th>Wins</th><th>Win rates</th><th>First-player win</th><th>Mean actions</th><th>Policy sources</th></tr></thead>
      <tbody>
        ${rows.map(([name, row]) => `
          <tr>
            <td><strong>${esc(name.replaceAll("_", " "))}</strong></td>
            <td>${esc((row.agents || []).join(" vs "))}</td>
            <td>${row.games ?? "—"}</td>
            <td>${(row.wins || []).join("–")}</td>
            <td>${(row.win_rates || []).map((v) => pct(v)).join(" / ")}</td>
            <td>${pct(row.first_player_win_rate)}</td>
            <td>${num(row.mean_turns, 1)}</td>
            <td><code>${esc(JSON.stringify(row.policy_sources || {}))}</code></td>
          </tr>
        `).join("")}
      </tbody>
    </table>
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
    metric("First passer wins", pct(p.first_passer_battle_win_rate), `2-front pass wins ${pct(p.pass_with_two_fronts_battle_win_rate)}`),
  ].join("");

  const actions = Object.entries(t.actions || {});
  const decisions = Object.entries(t.decisions || {});
  document.getElementById("raw-telemetry").innerHTML = `
    <div class="two-column-tables">
      <div>
        <h3>Actions</h3>
        <table class="mini-table"><tbody>
          ${actions.map(([k,v]) => `<tr><td>${esc(k)}</td><td>${v}</td></tr>`).join("")}
        </tbody></table>
      </div>
      <div>
        <h3>Agent decisions</h3>
        <table class="mini-table"><tbody>
          ${decisions.map(([k,v]) => `<tr><td>${esc(k)}</td><td>${v.decisions} decisions · ${num(v.mean_candidate_count,1)} candidates · gap ${num(v.mean_score_gap,2)}</td></tr>`).join("")}
        </tbody></table>
      </div>
    </div>
  `;
}

function renderMccfr(lab) {
  const m = lab.mccfr;
  const v = lab.verification;
  if (!m) {
    document.getElementById("mccfr-overview").innerHTML = metric("MCCFR", "—", "policy not generated");
  } else {
    document.getElementById("mccfr-overview").innerHTML = [
      metric("Iterations", m.iterations ?? "—", `${m.traversals ?? "—"} traversals`),
      metric("Information sets", Number(m.information_sets || 0).toLocaleString(), `depth ${m.max_depth}`),
      metric("Algorithm", "External sampling", m.algorithm || ""),
      metric("Average policy", "Reach weighted", m.average_policy || ""),
    ].join("");
  }

  if (!v) {
    document.getElementById("mccfr-verification").innerHTML = '<p class="verification verification-missing">No formal verification artifact.</p>';
    return;
  }
  document.getElementById("mccfr-verification").innerHTML = `
    <div class="verification ${v.passed ? "verification-pass" : "verification-fail"}">
      <strong>${v.passed ? "VERIFIED" : "FAILED"}</strong>
      <span>${esc(v.benchmark)} · known value ${num(v.known_p0_value, 6)} · learned ${num(v.learned_p0_value, 6)} · error ${num(v.absolute_value_error, 6)} · exploitability ${num(v.exploitability, 6)}</span>
      <span>Thresholds: value error ≤ ${v.thresholds.max_value_error}, exploitability ≤ ${v.thresholds.max_exploitability}</span>
    </div>
  `;
}

function staticTable(rows) {
  return `
    <table class="mini-table">
      <thead><tr><th>Legend IDs</th><th>Strength</th><th>z</th></tr></thead>
      <tbody>
        ${rows.map((r) => `<tr><td><code>${esc([r.subject,r.link,r.name].join(" · "))}</code></td><td>${r.static_strength}</td><td>${num(r.z_score,2)}</td></tr>`).join("")}
      </tbody>
    </table>
  `;
}

function renderStatic(lab) {
  const s = lab.static;
  document.getElementById("static-overview").innerHTML = [
    metric("Static combinations", s.legend_count, "Subject × Link × Name"),
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
    <ul>${report.methodology.notes.map((note) => `<li>${esc(note)}</li>`).join("")}</ul>
  `;
}

async function main() {
  const response = await fetch("data/lab-report.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Full Balance Lab report is not available yet.");
  const lab = await response.json();

  renderOverview(lab);
  renderCards(lab);
  renderLegends(lab);
  renderMatchups(lab);
  renderTelemetry(lab);
  renderMccfr(lab);
  renderStatic(lab);
  renderDownloads(lab);
  renderMethod(lab);

  document.getElementById("card-filter").addEventListener("change", () => renderCards(lab));
}

main().catch((error) => {
  document.getElementById("overview").innerHTML =
    `<p class="dashboard-error">${esc(error.message)}</p>`;
});
