from __future__ import annotations

from typing import Any


class Scraper:
    name: str = "base"

    async def enrich_match(self, match: dict[str, Any]) -> dict[str, Any]:
        return {}
