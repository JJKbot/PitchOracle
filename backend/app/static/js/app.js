const matchList = document.getElementById("matches-list");
const matchCount = document.getElementById("match-count");
const dateInput = document.getElementById("match-date");
const todayBtn = document.getElementById("today-btn");
const sourceLine = document.getElementById("source-line");
const warningsBox = document.getElementById("warnings");

const formatPercent = (value) => `${Math.round(value * 100)}%`;

const formatDateTime = (iso) => {
  const dt = new Date(iso);
  return dt.toLocaleString(undefined, {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const badgeForConfidence = (confidence) => {
  if (confidence >= 0.6) return { label: "High confidence", cls: "high" };
  if (confidence >= 0.5) return { label: "Mid confidence", cls: "mid" };
  return { label: "Low confidence", cls: "low" };
};

const formatForm = (form) => {
  if (!form) return "N/A";
  return form.split("").join(" ");
};

const renderMatch = (match) => {
  const badge = badgeForConfidence(match.odds.confidence);
  const card = document.createElement("div");
  card.className = "match-card";

  const renderPlayers = (title, players) => {
    if (!players.length) {
      return `<div class="player-list"><h4>${title}</h4><div class="player-meta">No player data</div></div>`;
    }

    const items = players
      .map((player) => {
        const stats = [
          player.goals != null ? `G${player.goals}` : null,
          player.assists != null ? `A${player.assists}` : null,
        ]
          .filter(Boolean)
          .join(" · ");
        return `<li><span>${player.name}</span><span class="player-meta">${stats || "-"}</span></li>`;
      })
      .join("");

    return `<div class="player-list"><h4>${title}</h4><ul>${items}</ul></div>`;
  };

  const renderLineup = (lineup) => {
    if (!lineup || !lineup.start_xi || !lineup.start_xi.length) {
      return `<div class="player-meta">Lineup unavailable</div>`;
    }
    const players = lineup.start_xi
      .map((player) => `${player.number || ""} ${player.name}`.trim())
      .join(", ");
    return `<div class="player-meta">${players}</div>`;
  };

  const renderInjuries = (injuries) => {
    if (!injuries || !injuries.length) {
      return `<div class="player-meta">No injuries reported</div>`;
    }
    return injuries
      .map((injury) => `<div>${injury.player_name}${injury.reason ? ` · ${injury.reason}` : ""}</div>`)
      .join("");
  };

  const renderStanding = (standing) => {
    if (!standing || standing.rank == null) return "N/A";
    return `#${standing.rank} · ${standing.points ?? "-"} pts`;
  };

  const renderAdvanced = (stats) => {
    if (!stats) return "N/A";
    const parts = [];
    if (stats.shots_on_goal != null) parts.push(`SOG ${stats.shots_on_goal}`);
    if (stats.shots_total != null) parts.push(`Shots ${stats.shots_total}`);
    if (stats.possession != null) parts.push(`Poss ${stats.possession}%`);
    if (stats.xg_est != null) parts.push(`xG~ ${stats.xg_est}`);
    return parts.join(" · ") || "N/A";
  };

  card.innerHTML = `
    <div class="match-top">
      <div>
        <div class="match-title">${match.home_team.name} vs ${match.away_team.name}</div>
        <div class="meta">${match.competition || "Friendly"} · ${formatDateTime(match.utc_date)}</div>
      </div>
      <div class="badge ${badge.cls}">${badge.label}</div>
    </div>
    <div class="odds-grid">
      <div class="odds-box">
        Home win
        <span>${formatPercent(match.odds.home_win)}</span>
      </div>
      <div class="odds-box">
        Draw
        <span>${formatPercent(match.odds.draw)}</span>
      </div>
      <div class="odds-box">
        Away win
        <span>${formatPercent(match.odds.away_win)}</span>
      </div>
    </div>
    <div class="team-stats">
      <div>
        <strong>${match.home_team.short_name || match.home_team.name}</strong>
        <div>Avg GF: ${match.home_stats.goals_for_avg}</div>
        <div>Avg GA: ${match.home_stats.goals_against_avg}</div>
        <div>PPG: ${match.home_stats.points_per_game}</div>
        <div>Form: ${formatForm(match.home_stats.recent_form)}</div>
        <div>Standing: ${renderStanding(match.home_standing)}</div>
        <div>Advanced: ${renderAdvanced(match.home_advanced)}</div>
      </div>
      <div>
        <strong>${match.away_team.short_name || match.away_team.name}</strong>
        <div>Avg GF: ${match.away_stats.goals_for_avg}</div>
        <div>Avg GA: ${match.away_stats.goals_against_avg}</div>
        <div>PPG: ${match.away_stats.points_per_game}</div>
        <div>Form: ${formatForm(match.away_stats.recent_form)}</div>
        <div>Standing: ${renderStanding(match.away_standing)}</div>
        <div>Advanced: ${renderAdvanced(match.away_advanced)}</div>
      </div>
    </div>
    <div class="players-grid">
      ${renderPlayers(
        `${match.home_team.short_name || match.home_team.name} top scorers`,
        match.home_players
      )}
      ${renderPlayers(
        `${match.away_team.short_name || match.away_team.name} top scorers`,
        match.away_players
      )}
    </div>
    <div class="players-grid">
      <div class="player-list">
        <h4>${match.home_team.short_name || match.home_team.name} lineup</h4>
        ${renderLineup(match.home_lineup)}
      </div>
      <div class="player-list">
        <h4>${match.away_team.short_name || match.away_team.name} lineup</h4>
        ${renderLineup(match.away_lineup)}
      </div>
    </div>
    <div class="player-list">
      <h4>Injuries</h4>
      ${renderInjuries(match.injuries)}
    </div>
  `;

  return card;
};

const renderMatches = (payload) => {
  matchList.innerHTML = "";
  sourceLine.textContent = `Source: ${payload.source}`;
  warningsBox.innerHTML = "";
  if (payload.warnings && payload.warnings.length) {
    payload.warnings.forEach((warning) => {
      const item = document.createElement("span");
      item.textContent = warning;
      warningsBox.appendChild(item);
    });
  }

  if (!payload.matches.length) {
    const empty = document.createElement("div");
    empty.className = "match-card";
    empty.innerHTML = "No matches found for this date.";
    matchList.appendChild(empty);
  } else {
    payload.matches.forEach((match) => matchList.appendChild(renderMatch(match)));
  }

  matchCount.textContent = `${payload.matches.length} fixtures`;
};

const loadMatches = async (targetDate) => {
  matchList.innerHTML = "";
  const loading = document.createElement("div");
  loading.className = "match-card";
  loading.textContent = "Loading matches...";
  matchList.appendChild(loading);

  const response = await fetch(`/api/matches?date=${targetDate}`);
  const payload = await response.json();
  renderMatches(payload);
};

const today = new Date();
const todayIso = today.toISOString().slice(0, 10);

dateInput.value = todayIso;
loadMatches(todayIso);

dateInput.addEventListener("change", (event) => {
  const value = event.target.value;
  if (value) {
    loadMatches(value);
  }
});

todayBtn.addEventListener("click", () => {
  dateInput.value = todayIso;
  loadMatches(todayIso);
});
