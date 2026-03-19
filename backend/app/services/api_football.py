from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from app.services.cache import TTLCache

BASE_URL = "https://v3.football.api-sports.io"


@dataclass
class ApiFootballLeague:
    league_id: int
    season: int


class ApiFootballClient:
    def __init__(self, api_key: str | None, rapidapi_key: str | None, cache: TTLCache) -> None:
        self._api_key = api_key
        self._rapidapi_key = rapidapi_key
        self._cache = cache

    @property
    def enabled(self) -> bool:
        return bool(self._api_key or self._rapidapi_key)

    def _headers(self) -> dict[str, str]:
        if self._rapidapi_key:
            return {
                "x-rapidapi-key": self._rapidapi_key,
                "x-rapidapi-host": "v3.football.api-sports.io",
            }
        return {"x-apisports-key": self._api_key or ""}

    async def fetch_league_id(self, name: str, country: str, season: int) -> ApiFootballLeague | None:
        cache_key = f"af:league:{name}:{country}:{season}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"name": name, "country": country, "season": season}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/leagues", headers=self._headers(), params=params)
            if response.status_code >= 400:
                return None
            payload = response.json()

        league_data = None
        for entry in payload.get("response", []):
            league_data = entry
            break

        if not league_data:
            return None

        league_id = league_data.get("league", {}).get("id")
        season_value = season
        if league_data.get("seasons"):
            season_value = league_data["seasons"][0].get("year", season)

        result = ApiFootballLeague(league_id=int(league_id), season=int(season_value)) if league_id else None
        if result:
            self._cache.set(cache_key, result, ttl=86400)
        return result

    async def fetch_fixtures(self, target_date: date, league_id: int, season: int) -> list[dict[str, Any]]:
        cache_key = f"af:fixtures:{target_date.isoformat()}:{league_id}:{season}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"date": target_date.isoformat(), "league": league_id, "season": season}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/fixtures", headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()

        fixtures = payload.get("response", [])
        self._cache.set(cache_key, fixtures, ttl=300)
        return fixtures

    async def fetch_top_scorers(self, league_id: int, season: int) -> list[dict[str, Any]]:
        cache_key = f"af:topscorers:{league_id}:{season}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"league": league_id, "season": season}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{BASE_URL}/players/topscorers", headers=self._headers(), params=params
            )
            response.raise_for_status()
            payload = response.json()

        players = payload.get("response", [])
        self._cache.set(cache_key, players, ttl=1800)
        return players

    async def fetch_standings(self, league_id: int, season: int) -> list[dict[str, Any]]:
        cache_key = f"af:standings:{league_id}:{season}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"league": league_id, "season": season}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/standings", headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()

        standings = payload.get("response", [])
        self._cache.set(cache_key, standings, ttl=1800)
        return standings

    async def fetch_fixture_lineups(self, fixture_id: int) -> list[dict[str, Any]]:
        cache_key = f"af:lineups:{fixture_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"fixture": fixture_id}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/fixtures/lineups", headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("response", [])
        self._cache.set(cache_key, data, ttl=300)
        return data

    async def fetch_fixture_injuries(self, fixture_id: int) -> list[dict[str, Any]]:
        cache_key = f"af:injuries:{fixture_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"fixture": fixture_id}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/fixtures/injuries", headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("response", [])
        self._cache.set(cache_key, data, ttl=300)
        return data

    async def fetch_fixture_statistics(self, fixture_id: int) -> list[dict[str, Any]]:
        cache_key = f"af:stats:{fixture_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"fixture": fixture_id}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/fixtures/statistics", headers=self._headers(), params=params)
            response.raise_for_status()
            payload = response.json()

        data = payload.get("response", [])
        self._cache.set(cache_key, data, ttl=300)
        return data
