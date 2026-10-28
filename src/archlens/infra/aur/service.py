from __future__ import annotations

from threading import Event
from time import time

from archlens.core.aur import AurMetadataMode, AurSnapshot

from .cache import AurCache
from .client import AurClient


class AurService:
    def __init__(self, client: AurClient, cache: AurCache, *, enabled: bool = False, consent_version: int = 0, daily_budget: int = 100) -> None:
        self.client, self.cache = client, cache
        self.enabled, self.consent_version, self.daily_budget = enabled, consent_version, daily_budget

    def refresh(self, names, mode: AurMetadataMode, *, force: bool = False, cancel: Event | None = None) -> AurSnapshot:
        self.cache.load()
        if mode is AurMetadataMode.NONE:
            return AurSnapshot(mode, {}, frozenset(), None, None, False, ())
        now = int(time())
        if mode is AurMetadataMode.CACHE or not (self.enabled and self.consent_version == 1):
            infos = {name: entry.info for name in names if (entry := self.cache.get(name)) and entry.info}
            times = [entry.fetched_at for entry in self.cache.entries.values()]
            errors = ("AUR data disabled",) if mode is AurMetadataMode.ONLINE else ()
            return AurSnapshot(AurMetadataMode.CACHE, infos, frozenset(), min(times) if times else None, max(times) if times else None, any(not self.cache.is_fresh(entry) for entry in self.cache.entries.values()), errors)
        if self.cache.rate_limited_until() > now:
            return AurSnapshot(AurMetadataMode.CACHE, {}, frozenset(), None, None, True, ("Too many requests; try later",))
        pending = [name for name in sorted(set(names)) if force or not (self.cache.get(name) and self.cache.is_fresh(self.cache.get(name)))]
        if self.cache.budget_remaining(self.daily_budget) <= 0:
            return AurSnapshot(AurMetadataMode.CACHE, {}, frozenset(), None, None, True, ("Daily request budget exhausted",))
        if cancel and cancel.is_set():
            pending = []
        result = self.client.fetch_info(pending)
        for info in result.infos.values():
            self.cache.put_found(info)
        for name in result.not_found:
            self.cache.put_not_found(name)
        self.cache.add_requests(result.requests_made)
        if result.rate_limited:
            self.cache.set_rate_limited(now + 3600)
        self.cache.save()
        infos = {name: entry.info for name in names if (entry := self.cache.get(name)) and entry.info}
        return AurSnapshot(AurMetadataMode.ONLINE, infos, result.not_found, None, now, False, result.errors)
