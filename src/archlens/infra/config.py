"""User configuration for protected packages and cache policy."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    protected: frozenset[str] = frozenset()
    keep_versions: int = 2


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
    return AppConfig(protected=protected, keep_versions=keep_versions)
