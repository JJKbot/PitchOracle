from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from app.services.cache import TTLCache

BASE_URL = "https://api.football-data.org/v4"


class FootballDataClient:
    def __init__(self, token: str, cache: TTLCache) -> None:
        self._token = token
        self._cache = cache

    async def fetch_matches(self, match_date: date) -> list[dict[str, Any]]:
        cache_key = f"fd:matches:{match_date.isoformat()}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        headers = {"X-Auth-Token": self._token}
        params = {"date": match_date.isoformat()}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/matches", headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()

        matches = payload.get("matches", [])
        self._cache.set(cache_key, matches, ttl=300)
        return matches

    async def fetch_team_recent_matches(self, team_id: int, limit: int = 8) -> list[dict[str, Any]]:
        cache_key = f"fd:team:{team_id}:recent:{limit}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        headers = {"X-Auth-Token": self._token}
        params = {"status": "FINISHED", "limit": limit}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/teams/{team_id}/matches", headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()

        matches = payload.get("matches", [])
        self._cache.set(cache_key, matches, ttl=900)
        return matches
