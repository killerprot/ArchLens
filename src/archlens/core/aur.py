"""Pure AUR metadata models, sanitization, and derived flags."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from archlens.core.graph import DependencyGraph, dependency_name

VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+~:-]{0,63}$")


class AurMetadataMode(Enum):
    NONE = "none"
    CACHE = "cache"
    ONLINE = "online"


class AurSourceStatus(Enum):
    UNCHECKED = "unchecked"
    FOUND_IN_AUR = "found_in_aur"
    NOT_IN_AUR = "not_in_aur"


@dataclass(frozen=True)
class AurInfo:
    name: str
    package_base: str
    version: str
    description: str
    url: str | None
    num_votes: int | None
    popularity: float | None
    out_of_date: int | None
    maintainer: str | None
    first_submitted: int | None
    last_modified: int | None
    depends: tuple[str, ...]
    make_depends: tuple[str, ...]
    check_depends: tuple[str, ...]
    opt_depends: tuple[str, ...]
    fetched_at: int


@dataclass(frozen=True)
class AurFlags:
    status: AurSourceStatus
    update_available: bool | None
    local_newer: bool | None
    out_of_date: bool | None
    no_maintainer: bool | None
    not_in_aur: bool | None


@dataclass(frozen=True)
class AurSnapshot:
    mode: AurMetadataMode
    infos: dict[str, AurInfo]
    not_found: frozenset[str]
    oldest_entry_at: int | None
    fetched_at: int | None
    stale: bool
    errors: tuple[str, ...]


def sanitize_text(value: object, max_len: int) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = "".join(" " if char in "\n\r\t" else char for char in value
                      if unicodedata.category(char) not in {"Cc", "Cf"})
    cleaned = " ".join(cleaned.split()).strip()
    return cleaned if len(cleaned) <= max_len else cleaned[: max_len - 1].rstrip() + "…"


def sanitize_url(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 500 or any(char.isspace() for char in value):
        return None
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    return value


def valid_version(value: object) -> bool:
    return isinstance(value, str) and VERSION_RE.fullmatch(value) is not None


def derive_flags(installed_version: str, info: AurInfo | None, was_checked: bool, vercmp) -> AurFlags:
    if info is None and not was_checked:
        return AurFlags(AurSourceStatus.UNCHECKED, None, None, None, None, None)
    if info is None:
        return AurFlags(AurSourceStatus.NOT_IN_AUR, None, None, None, None, True)
    comparison = vercmp(info.version, installed_version)
    return AurFlags(
        AurSourceStatus.FOUND_IN_AUR,
        comparison == 1 if comparison is not None else None,
        comparison == -1 if comparison is not None else None,
        info.out_of_date is not None,
        info.maintainer is None,
        False,
    )


def build_dependency_hints(graph: DependencyGraph, aur: AurSnapshot, candidates) -> dict[str, tuple[str, ...]]:
    result: dict[str, set[str]] = {name: set() for name in candidates}
    for package_name, info in aur.infos.items():
        for raw in (*info.make_depends, *info.check_depends):
            for provider in graph.resolved(package_name, dependency_name(raw)):
                if provider in result:
                    result[provider].add(package_name)
    return {name: tuple(sorted(values)) for name, values in result.items() if values}
