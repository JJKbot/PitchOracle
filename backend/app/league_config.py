from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent


@dataclass
class LeagueConfig:
    name: str
    country: str
    provider: str
    league_id: int | None
    season_strategy: str


def load_leagues() -> list[LeagueConfig]:
    payload = json.loads((BASE_DIR / "data" / "leagues.json").read_text(encoding="utf-8"))
    leagues: list[LeagueConfig] = []
    for item in payload.get("leagues", []):
        leagues.append(
            LeagueConfig(
                name=item.get("name", ""),
                country=item.get("country", ""),
                provider=item.get("provider", "api_football"),
                league_id=item.get("league_id"),
                season_strategy=item.get("season_strategy", "european"),
            )
        )
    return leagues


def resolve_season(target_date, strategy: str) -> int:
    if strategy == "calendar":
        return target_date.year
    if target_date.month < 7:
        return target_date.year - 1
    return target_date.year
