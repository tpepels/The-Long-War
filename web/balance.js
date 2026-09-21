const pct = (value, digits = 1) =>
  value == null ? "—" : `${(100 * value).toFixed(digits)}%`;

const num = (value, digits = 2) =>
  value == null ? "—" : Number(value).toFixed(digits);

const interval = (pair) =>
  !pair || pair[0] == null ? "—" : `${pct(pair[0])}–${pct(pair[1])}`;

function flagMarkup(flags) {
  if (!flags || !flags.length) return '<span class="muted">—</span>';
  return flags
    .map(
      (flag) =>
        `<span class="flag flag-${flag.severity}" title="${flag.message}">${flag.code.replaceAll("_", " ")}</span>`
    )
    .join(" ");
}

function metric(label, value, note = "") {
  return `
    <article class="metric-card">
      <p>${label}</p>
      <strong>${value}</strong>
      <small>${note}</small>
    </article>
  `;
}

function renderOverview(report) {
  const g = report.global;
  const s = report.summary;
  document.getElementById("overview").innerHTML = [
    metric("Games", report.source.games.toLocaleString(), report.source.agents.join(" vs ")),
    metric("First-player win", pct(g.first_player_win_rate), `95%: ${interval(g.first_player_win_rate_95)}`),
    metric("Mean actions", num(g.mean_actions, 1), `max ${g.max_actions}`),
    metric("First passer wins Battle", pct(g.passes.first_passer_battle_win_rate), "pass timing diagnostic"),
    metric("High flags", s.flags_high, "strong evidence threshold"),
    metric("Watch flags", s.flags_watch, "inspect before changing"),
  ].join("");
}

function renderCards(report) {
  const filter = document.getElementById("card-filter").value;
  let rows = [...report.cards];

  if (["subject", "link", "name", "plot"].includes(filter)) {
    rows = rows.filter((row) => row.type === filter);
  } else if (filter === "flagged") {
    rows.sort((a, b) => b.flags.length - a.flags.length || a.title.localeCompare(b.title));
  }

  document.getElementById("card-table").innerHTML = rows
    .map(
      (row) => `
        <tr class="${row.flags.length ? "flagged-row" : ""}">
          <td><strong>${row.title}</strong></td>
          <td>${row.type}</td>
          <td>${pct(row.play_rate_per_draw)}</td>
          <td>${pct(row.unplayable_turn_rate)}</td>
          <td>${num(row.mean_immediate_front_swing, 1)} <span class="muted">z ${num(row.front_swing_z_within_type, 1)}</span></td>
          <td>${pct(row.win_rate_when_played)} <span class="muted">95% ${interval(row.win_rate_when_played_95)}</span></td>
          <td class="flags-cell">${flagMarkup(row.flags)}</td>
        </tr>
      `
    )
    .join("");
}

function renderLegends(report) {
  const rows = [...report.legends]
    .sort((a, b) => b.flags.length - a.flags.length || b.games_seen - a.games_seen)
    .slice(0, 60);

  document.getElementById("legend-table").innerHTML = rows
    .map(
      (row) => `
        <tr class="${row.flags.length ? "flagged-row" : ""}">
          <td><strong>${row.title}</strong></td>
          <td>${row.completions}</td>
          <td>${row.games_seen}</td>
          <td>${num(row.mean_strength_at_completion, 1)} <span class="muted">z ${num(row.completion_strength_z, 1)}</span></td>
          <td>${pct(row.win_rate_when_seen)} <span class="muted">95% ${interval(row.win_rate_when_seen_95)}</span></td>
          <td class="flags-cell">${flagMarkup(row.flags)}</td>
        </tr>
      `
    )
    .join("");
}

function renderMethod(report) {
  document.getElementById("methodology").innerHTML = `
    <p><strong>Intervals:</strong> ${report.methodology.win_intervals}. Small samples therefore stay visibly uncertain.</p>
    <p><strong>Board swing:</strong> standardized within card type, so Subjects are compared with Subjects rather than with Links or Plots.</p>
    <ul>${report.methodology.notes.map((note) => `<li>${note}</li>`).join("")}</ul>
  `;
}

async function main() {
  const response = await fetch("data/balance-health.json", { cache: "no-store" });
  if (!response.ok) throw new Error("Balance telemetry is not available yet.");
  const report = await response.json();

  renderOverview(report);
  renderCards(report);
  renderLegends(report);
  renderMethod(report);

  document.getElementById("card-filter").addEventListener("change", () => renderCards(report));
}

main().catch((error) => {
  document.getElementById("overview").innerHTML = `<p class="dashboard-error">${error.message}</p>`;
});
