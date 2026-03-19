from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from dateutil.parser import isoparse
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.league_config import load_leagues, resolve_season
from app.models import (
    AdvancedStats,
    InjuryItem,
    LineupPlayer,
    MatchItem,
    MatchOdds,
    MatchTeamStats,
    MatchesResponse,
    PlayerHighlight,
    StandingSummary,
    Team,
    TeamLineup,
)
from app.services.api_football import ApiFootballClient
from app.services.cache import TTLCache
from app.services.football_data import FootballDataClient
from app.services.odds import compute_odds
from app.settings import settings

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

cache = TTLCache(settings.cache_ttl_seconds)


def _load_sample_matches() -> list[dict[str, Any]]:
    sample_path = BASE_DIR / "data" / "sample.json"
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    return payload.get("matches", [])


def _parse_match_datetime(value: str) -> datetime:
    return isoparse(value)


def _team_stats_from_matches(matches: list[dict[str, Any]], team_id: int) -> MatchTeamStats:
    goals_for = 0
    goals_against = 0
    points = 0
    played = 0
    form: list[str] = []

    for match in matches:
        score = match.get("score", {}).get("fullTime", {})
        home_team = match.get("homeTeam", {})
        away_team = match.get("awayTeam", {})
        if score.get("home") is None or score.get("away") is None:
            continue

        if home_team.get("id") == team_id:
            gf = int(score.get("home", 0))
            ga = int(score.get("away", 0))
        elif away_team.get("id") == team_id:
            gf = int(score.get("away", 0))
            ga = int(score.get("home", 0))
        else:
            continue

        played += 1
        goals_for += gf
        goals_against += ga
        if gf > ga:
            points += 3
            form.append("W")
        elif gf < ga:
            form.append("L")
        else:
            points += 1
            form.append("D")

    if played == 0:
        return MatchTeamStats(
            goals_for_avg=1.2,
            goals_against_avg=1.2,
            points_per_game=1.3,
            recent_form="",
        )

    goals_for_avg = goals_for / played
    goals_against_avg = goals_against / played
    points_per_game = points / played
    recent_form = "".join(form[-5:])

    return MatchTeamStats(
        goals_for_avg=round(goals_for_avg, 2),
        goals_against_avg=round(goals_against_avg, 2),
        points_per_game=round(points_per_game, 2),
        recent_form=recent_form,
    )


async def _build_match_items(matches: list[dict[str, Any]], client: FootballDataClient | None) -> list[MatchItem]:
    items: list[MatchItem] = []

    for match in matches:
        home_team_data = match.get("homeTeam", {})
        away_team_data = match.get("awayTeam", {})

        if client:
            home_recent, away_recent = await asyncio.gather(
                client.fetch_team_recent_matches(int(home_team_data.get("id"))),
                client.fetch_team_recent_matches(int(away_team_data.get("id"))),
            )
        else:
            home_recent, away_recent = [], []

        home_stats = _team_stats_from_matches(home_recent, int(home_team_data.get("id")))
        away_stats = _team_stats_from_matches(away_recent, int(away_team_data.get("id")))

        home_win, draw, away_win, confidence = compute_odds(
            home_stats.goals_for_avg,
            home_stats.goals_against_avg,
            home_stats.points_per_game,
            away_stats.goals_for_avg,
            away_stats.goals_against_avg,
            away_stats.points_per_game,
        )

        items.append(
            MatchItem(
                id=int(match.get("id")),
                utc_date=_parse_match_datetime(match.get("utcDate")),
                status=match.get("status", "UNKNOWN"),
                home_team=Team(
                    id=int(home_team_data.get("id")),
                    name=home_team_data.get("name", "Unknown"),
                    short_name=home_team_data.get("shortName"),
                    crest=home_team_data.get("crest"),
                ),
                away_team=Team(
                    id=int(away_team_data.get("id")),
                    name=away_team_data.get("name", "Unknown"),
                    short_name=away_team_data.get("shortName"),
                    crest=away_team_data.get("crest"),
                ),
                venue=match.get("venue"),
                competition=match.get("competition", {}).get("name"),
                odds=MatchOdds(
                    home_win=round(home_win, 4),
                    draw=round(draw, 4),
                    away_win=round(away_win, 4),
                    confidence=round(confidence, 4),
                ),
                home_stats=home_stats,
                away_stats=away_stats,
            )
        )

    return items


def _normalize_top_scorers(players: list[dict[str, Any]]) -> dict[int, list[PlayerHighlight]]:
    by_team: dict[int, list[PlayerHighlight]] = {}
    for entry in players:
        player_data = entry.get("player", {})
        stats = (entry.get("statistics") or [{}])[0]
        team = stats.get("team", {})
        goals = stats.get("goals", {})
        assists = goals.get("assists") if isinstance(goals, dict) else None
        rating = stats.get("games", {}).get("rating")

        team_id = team.get("id")
        if team_id is None:
            continue

        highlight = PlayerHighlight(
            name=player_data.get("name", "Unknown"),
            position=stats.get("games", {}).get("position"),
            goals=goals.get("total") if isinstance(goals, dict) else None,
            assists=assists if isinstance(assists, int) else None,
            rating=float(rating) if rating else None,
        )

        by_team.setdefault(int(team_id), []).append(highlight)

    for team_id, items in by_team.items():
        by_team[team_id] = items[:3]
    return by_team


def _team_boost_from_scorers(scorers: list[PlayerHighlight]) -> float:
    total_goals = sum(player.goals or 0 for player in scorers)
    return min(0.6, (total_goals / 30.0) * 0.4)


def _parse_lineups(lineups: list[dict[str, Any]]) -> dict[int, TeamLineup]:
    result: dict[int, TeamLineup] = {}
    for entry in lineups:
        team = entry.get("team", {})
        team_id = team.get("id")
        if team_id is None:
            continue
        start_xi = []
        for player_entry in entry.get("startXI", []):
            player = player_entry.get("player", {})
            start_xi.append(
                LineupPlayer(
                    name=player.get("name", "Unknown"),
                    number=player.get("number"),
                    position=player.get("pos"),
                )
            )
        result[int(team_id)] = TeamLineup(formation=entry.get("formation"), start_xi=start_xi)
    return result


def _parse_injuries(injuries: list[dict[str, Any]]) -> list[InjuryItem]:
    results: list[InjuryItem] = []
    for entry in injuries:
        team = entry.get("team", {})
        player = entry.get("player", {})
        results.append(
            InjuryItem(
                team_id=team.get("id"),
                team_name=team.get("name"),
                player_name=player.get("name", "Unknown"),
                reason=player.get("reason"),
                status=player.get("type"),
            )
        )
    return results


def _parse_standings(standings: list[dict[str, Any]]) -> dict[int, StandingSummary]:
    by_team: dict[int, StandingSummary] = {}
    if not standings:
        return by_team
    for block in standings:
        league = block.get("league", {})
        for group in league.get("standings", []):
            for row in group:
                team = row.get("team", {})
                team_id = team.get("id")
                if team_id is None:
                    continue
                by_team[int(team_id)] = StandingSummary(
                    rank=row.get("rank"),
                    points=row.get("points"),
                    played=row.get("all", {}).get("played"),
                    goal_diff=row.get("goalsDiff"),
                )
    return by_team


def _parse_statistics(stats: list[dict[str, Any]]) -> dict[int, AdvancedStats]:
    by_team: dict[int, AdvancedStats] = {}
    for entry in stats:
        team = entry.get("team", {})
        team_id = team.get("id")
        if team_id is None:
            continue
        metrics = {item.get("type"): item.get("value") for item in entry.get("statistics", [])}
        shots_on_goal = metrics.get("Shots on Goal") or metrics.get("Shots on Target")
        shots_total = metrics.get("Total Shots")
        possession = metrics.get("Ball Possession")
        if isinstance(possession, str) and possession.endswith("%"):
            try:
                possession = float(possession.rstrip("%"))
            except ValueError:
                possession = None

        xg_est = None
        if shots_on_goal is not None or shots_total is not None:
            sog = float(shots_on_goal or 0)
            tot = float(shots_total or 0)
            xg_est = round(sog * 0.12 + tot * 0.04, 2)

        by_team[int(team_id)] = AdvancedStats(
            shots_on_goal=int(shots_on_goal) if shots_on_goal is not None else None,
            shots_total=int(shots_total) if shots_total is not None else None,
            possession=possession if isinstance(possession, (int, float)) else None,
            xg_est=xg_est,
        )
    return by_team


async def _build_match_items_api_football(
    fixtures: list[dict[str, Any]],
    scorers_by_team: dict[int, list[PlayerHighlight]],
    standings_by_team: dict[int, StandingSummary],
    lineups_by_fixture: dict[int, dict[int, TeamLineup]],
    injuries_by_fixture: dict[int, list[InjuryItem]],
    stats_by_fixture: dict[int, dict[int, AdvancedStats]],
) -> list[MatchItem]:
    items: list[MatchItem] = []

    for fixture in fixtures:
        fixture_data = fixture.get("fixture", {})
        teams = fixture.get("teams", {})
        league = fixture.get("league", {})

        home_data = teams.get("home", {})
        away_data = teams.get("away", {})

        home_id = int(home_data.get("id"))
        away_id = int(away_data.get("id"))

        home_scorers = scorers_by_team.get(home_id, [])
        away_scorers = scorers_by_team.get(away_id, [])

        home_boost = _team_boost_from_scorers(home_scorers)
        away_boost = _team_boost_from_scorers(away_scorers)

        home_stats = MatchTeamStats(
            goals_for_avg=round(1.15 + home_boost, 2),
            goals_against_avg=round(1.2 - home_boost * 0.4, 2),
            points_per_game=round(1.3 + home_boost * 0.5, 2),
            recent_form="",
        )
        away_stats = MatchTeamStats(
            goals_for_avg=round(1.05 + away_boost, 2),
            goals_against_avg=round(1.25 - away_boost * 0.4, 2),
            points_per_game=round(1.2 + away_boost * 0.5, 2),
            recent_form="",
        )

        home_win, draw, away_win, confidence = compute_odds(
            home_stats.goals_for_avg,
            home_stats.goals_against_avg,
            home_stats.points_per_game,
            away_stats.goals_for_avg,
            away_stats.goals_against_avg,
            away_stats.points_per_game,
            home_boost=home_boost,
            away_boost=away_boost,
        )

        fixture_id = int(fixture_data.get("id"))
        lineups = lineups_by_fixture.get(fixture_id, {})
        injuries = injuries_by_fixture.get(fixture_id, [])
        stats = stats_by_fixture.get(fixture_id, {})

        items.append(
            MatchItem(
                id=fixture_id,
                utc_date=_parse_match_datetime(fixture_data.get("date")),
                status=fixture_data.get("status", {}).get("short", "UNKNOWN"),
                home_team=Team(
                    id=home_id,
                    name=home_data.get("name", "Unknown"),
                    short_name=home_data.get("name"),
                    crest=home_data.get("logo"),
                ),
                away_team=Team(
                    id=away_id,
                    name=away_data.get("name", "Unknown"),
                    short_name=away_data.get("name"),
                    crest=away_data.get("logo"),
                ),
                venue=fixture_data.get("venue", {}).get("name"),
                competition=league.get("name"),
                odds=MatchOdds(
                    home_win=round(home_win, 4),
                    draw=round(draw, 4),
                    away_win=round(away_win, 4),
                    confidence=round(confidence, 4),
                ),
                home_stats=home_stats,
                away_stats=away_stats,
                home_players=home_scorers,
                away_players=away_scorers,
                home_lineup=lineups.get(home_id),
                away_lineup=lineups.get(away_id),
                injuries=injuries,
                home_standing=standings_by_team.get(home_id),
                away_standing=standings_by_team.get(away_id),
                home_advanced=stats.get(home_id),
                away_advanced=stats.get(away_id),
            )
        )

    return items


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "app_name": settings.app_name})


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/matches", response_model=MatchesResponse)
async def matches_endpoint(match_date: str | None = Query(default=None, alias="date")):
    try:
        target_date = date.today() if not match_date else date.fromisoformat(match_date)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid date format. Use YYYY-MM-DD."})

    cache_key = f"matches:{target_date.isoformat()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    warnings: list[str] = []
    items: list[MatchItem] = []
    source = "sample"

    api_football = ApiFootballClient(settings.api_football_key, settings.api_football_rapidapi_key, cache)
    leagues = load_leagues()

    if api_football.enabled:
        for league in leagues:
            season = resolve_season(target_date, league.season_strategy)
            league_id = league.league_id
            if league_id is None:
                resolved = await api_football.fetch_league_id(league.name, league.country, season)
                if resolved is None:
                    warnings.append(f"League not found: {league.name} ({league.country}).")
                    continue
                league_id = resolved.league_id
                season = resolved.season

            try:
                fixtures = await api_football.fetch_fixtures(target_date, int(league_id), int(season))
                scorers = await api_football.fetch_top_scorers(int(league_id), int(season))
                standings_raw = await api_football.fetch_standings(int(league_id), int(season))
            except Exception:
                warnings.append(f"Failed to load fixtures for {league.name}.")
                continue

            scorers_by_team = _normalize_top_scorers(scorers)
            standings_by_team = _parse_standings(standings_raw)

            fixture_ids = [int(fixture.get("fixture", {}).get("id")) for fixture in fixtures]
            fixture_ids = [fid for fid in fixture_ids if fid]
            if len(fixture_ids) > settings.details_max_fixtures:
                warnings.append(
                    f"Details limited to {settings.details_max_fixtures} fixtures for {league.name}."
                )
                fixture_ids = fixture_ids[: settings.details_max_fixtures]

            lineups_by_fixture: dict[int, dict[int, TeamLineup]] = {}
            injuries_by_fixture: dict[int, list[InjuryItem]] = {}
            stats_by_fixture: dict[int, dict[int, AdvancedStats]] = {}

            for fixture_id in fixture_ids:
                try:
                    lineups_raw, injuries_raw, stats_raw = await asyncio.gather(
                        api_football.fetch_fixture_lineups(fixture_id),
                        api_football.fetch_fixture_injuries(fixture_id),
                        api_football.fetch_fixture_statistics(fixture_id),
                    )
                    lineups_by_fixture[fixture_id] = _parse_lineups(lineups_raw)
                    injuries_by_fixture[fixture_id] = _parse_injuries(injuries_raw)
                    stats_by_fixture[fixture_id] = _parse_statistics(stats_raw)
                except Exception:
                    warnings.append(f"Failed to load details for fixture {fixture_id}.")

            items.extend(
                await _build_match_items_api_football(
                    fixtures,
                    scorers_by_team,
                    standings_by_team,
                    lineups_by_fixture,
                    injuries_by_fixture,
                    stats_by_fixture,
                )
            )
        if items:
            source = "api-football"

    if not items:
        if settings.football_data_api_token:
            client = FootballDataClient(settings.football_data_api_token, cache)
            try:
                raw_matches = await client.fetch_matches(target_date)
            except Exception:
                raw_matches = []
            source = "football-data.org"
        else:
            client = None
            raw_matches = _load_sample_matches()

        items = await _build_match_items(raw_matches, client)

    response = MatchesResponse(
        date=target_date.isoformat(),
        source=source,
        matches=items,
        warnings=warnings,
    )

    cache.set(cache_key, response, ttl=300)
    return JSONResponse(content=response.model_dump(mode="json"))
