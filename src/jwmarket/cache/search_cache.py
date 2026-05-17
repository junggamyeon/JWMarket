

from __future__ import annotations

import time
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchCacheEntry:
    results: list
    count: int
    timestamp: float = field(default_factory=time.monotonic)


class SearchCache:


    def __init__(self, max_size: int = 200, ttl_seconds: float = 60.0) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, SearchCacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, query_key: str) -> tuple[list, int] | None:
        with self._lock:
            entry = self._cache.get(query_key)
            if entry is None:
                return None
            if (time.monotonic() - entry.timestamp) > self._ttl:
                del self._cache[query_key]
                return None
            self._cache.move_to_end(query_key)
            return entry.results, entry.count

    def set(self, query_key: str, results: list, count: int) -> None:
        with self._lock:
            if query_key in self._cache:
                self._cache[query_key] = SearchCacheEntry(results=results, count=count)
                self._cache.move_to_end(query_key)
            else:
                self._cache[query_key] = SearchCacheEntry(results=results, count=count)
                while len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)

    def invalidate_all(self) -> None:
        with self._lock:
            self._cache.clear()
