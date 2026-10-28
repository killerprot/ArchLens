"""User configuration for protected packages and cache policy."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    protected: frozenset[str] = frozenset()
    keep_versions: int = 2
    config_version: int = 3
    aur_enabled: bool = False
    aur_consent_version: int = 0
    aur_mode: str = "none"
    aur_cache_ttl_hours: int = 24
    aur_daily_request_budget: int = 100


def config_path() -> Path:
    return Path.home() / ".config" / "archlens" / "config.toml"


def load_config(path: str | Path | None = None) -> AppConfig:
    config_file = Path(path) if path is not None else config_path()
    try:
        data = tomllib.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return AppConfig()
    protected_data = data.get("protected", {}).get("packages", [])
    cache_data = data.get("cache", {})
    protected = frozenset(item for item in protected_data if isinstance(item, str))
    keep_versions = cache_data.get("keep_versions", 2)
    if not isinstance(keep_versions, int) or keep_versions < 1:
        keep_versions = 2
    aur = data.get("aur", {})
    ttl = aur.get("cache_ttl_hours", 24)
    budget = aur.get("daily_request_budget", 100)
    if not isinstance(ttl, int) or not 1 <= ttl <= 720:
        ttl = 24
    if not isinstance(budget, int) or not 10 <= budget <= 1000:
        budget = 100
    return AppConfig(
        protected=protected, keep_versions=keep_versions,
        aur_enabled=aur.get("enabled") is True,
        aur_consent_version=aur.get("consent_version", 0) if isinstance(aur.get("consent_version", 0), int) else 0,
        aur_mode=aur.get("mode", "none") if aur.get("mode") in {"none", "cache", "online"} else "none",
        aur_cache_ttl_hours=ttl, aur_daily_request_budget=budget,
    )
