from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import time

from archlens.core.aur import AurInfo


@dataclass(frozen=True)
class CacheEntry:
    info: AurInfo | None
    fetched_at: int
    not_found: bool = False


class AurCache:
    def __init__(self, path: Path, ttl_seconds: int, clock=time) -> None:
        self.path, self.ttl_seconds, self.clock = path, ttl_seconds, clock
        self.entries: dict[str, CacheEntry] = {}
        self.requests: list[int] = []
        self._rate_limited_until = 0

    def load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.requests = [int(x) for x in data.get("requests", []) if isinstance(x, int)]
            self._rate_limited_until = int(data.get("rate_limited_until", 0))
            for name, value in data.get("entries", {}).items():
                if value.get("not_found"):
                    self.entries[name] = CacheEntry(None, int(value["fetched_at"]), True)
        except (OSError, ValueError, TypeError, KeyError):
            self.entries = {}

    def get(self, name: str) -> CacheEntry | None:
        return self.entries.get(name)

    def is_fresh(self, entry: CacheEntry) -> bool:
        return self.clock() - entry.fetched_at < self.ttl_seconds

    def put_found(self, info: AurInfo) -> None:
        self.entries[info.name] = CacheEntry(info, info.fetched_at)

    def put_not_found(self, name: str) -> None:
        self.entries[name] = CacheEntry(None, int(self.clock()), True)

    def budget_remaining(self, daily_budget: int) -> int:
        day = int(self.clock()) // 86400
        used = sum(1 for stamp in self.requests if stamp // 86400 == day)
        return max(0, daily_budget - used)

    def add_requests(self, count: int) -> None:
        self.requests.extend([int(self.clock())] * count)

    def rate_limited_until(self) -> int:
        return self._rate_limited_until

    def set_rate_limited(self, until: int) -> None:
        self._rate_limited_until = until

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"requests": self.requests, "rate_limited_until": self._rate_limited_until, "entries": {
            name: {"fetched_at": entry.fetched_at, "not_found": entry.not_found}
            for name, entry in self.entries.items()
        }}
        fd, temporary = tempfile.mkstemp(prefix=".aur-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
