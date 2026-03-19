from __future__ import annotations

from typing import Any

from app.scrapers.base import Scraper


class DummyScraper(Scraper):
    name = "dummy"

    async def enrich_match(self, match: dict[str, Any]) -> dict[str, Any]:
        return {}
