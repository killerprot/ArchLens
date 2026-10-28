"""Package origin classification independent of pacman and Qt."""

from collections.abc import Iterable
from enum import Enum


class SourceKind(Enum):
    REPO = "repo"
    FOREIGN = "foreign"
    UNKNOWN = "unknown"


def classify_sources(
    installed: Iterable[str],
    foreign: frozenset[str] | None,
    sync_reliable: bool,
) -> dict[str, SourceKind]:
    names = tuple(installed)
    if foreign is None or not sync_reliable:
        return {name: SourceKind.UNKNOWN for name in names}
    return {name: SourceKind.FOREIGN if name in foreign else SourceKind.REPO for name in names}
