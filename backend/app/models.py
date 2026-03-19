from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class Team(BaseModel):
    id: int
    name: str
    short_name: str | None = None
    crest: str | None = None


class MatchTeamStats(BaseModel):
    goals_for_avg: float = 0.0
    goals_against_avg: float = 0.0
    points_per_game: float = 0.0
    recent_form: str = ""


class MatchOdds(BaseModel):
    home_win: float = Field(..., ge=0.0, le=1.0)
    draw: float = Field(..., ge=0.0, le=1.0)
    away_win: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)


class PlayerHighlight(BaseModel):
    name: str
    position: str | None = None
    goals: int | None = None
    assists: int | None = None
    rating: float | None = None


class LineupPlayer(BaseModel):
    name: str
    number: int | None = None
    position: str | None = None


class TeamLineup(BaseModel):
    formation: str | None = None
    start_xi: list[LineupPlayer] = []


class InjuryItem(BaseModel):
    team_id: int | None = None
    team_name: str | None = None
    player_name: str
    reason: str | None = None
    status: str | None = None


class StandingSummary(BaseModel):
    rank: int | None = None
    points: int | None = None
    played: int | None = None
    goal_diff: int | None = None


class AdvancedStats(BaseModel):
    shots_on_goal: int | None = None
    shots_total: int | None = None
    possession: float | None = None
    xg_est: float | None = None


class MatchItem(BaseModel):
    id: int
    utc_date: datetime
    status: str
    home_team: Team
    away_team: Team
    venue: str | None = None
    competition: str | None = None
    odds: MatchOdds
    home_stats: MatchTeamStats
    away_stats: MatchTeamStats
    home_players: list[PlayerHighlight] = []
    away_players: list[PlayerHighlight] = []
    home_lineup: TeamLineup | None = None
    away_lineup: TeamLineup | None = None
    injuries: list[InjuryItem] = []
    home_standing: StandingSummary | None = None
    away_standing: StandingSummary | None = None
    home_advanced: AdvancedStats | None = None
    away_advanced: AdvancedStats | None = None


class MatchesResponse(BaseModel):
    date: str
    source: str
    matches: list[MatchItem]
    warnings: list[str] = []
