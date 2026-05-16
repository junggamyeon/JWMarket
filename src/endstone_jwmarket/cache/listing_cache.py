

from __future__ import annotations

import time
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ListingCacheEntry:
    data: Any
    timestamp: float = field(default_factory=time.monotonic)


class ListingCache:


    def __init__(self, max_size: int = 1000, ttl_seconds: float = 120.0) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, ListingCacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if (time.monotonic() - entry.timestamp) > self._ttl:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return entry.data

    def set(self, key: str, data: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache[key].data = data
                self._cache[key].timestamp = time.monotonic()
                self._cache.move_to_end(key)
            else:
                self._cache[key] = ListingCacheEntry(data=data)
                while len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def invalidate_all(self) -> None:
        with self._lock:
            self._cache.clear()
