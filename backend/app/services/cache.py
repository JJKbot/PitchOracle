from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheItem:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self, default_ttl: int = 900) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, _CacheItem] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if not item:
            return None
        if item.expires_at < time.time():
            self._store.pop(key, None)
            return None
        return item.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl_value = self._default_ttl if ttl is None else ttl
        self._store[key] = _CacheItem(value=value, expires_at=time.time() + ttl_value)

    def clear(self) -> None:
        self._store.clear()
