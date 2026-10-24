"""Analysis of packages stored in pacman's cache."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CachedPackage:
    name: str
    filename: str
    size: int
    version: str


def parse_cache_filename(path: Path) -> CachedPackage | None:
    filename = path.name
    suffix = ".pkg.tar."
    if suffix not in filename:
        return None
    stem, compression = filename.rsplit(suffix, maxsplit=1)
    if not compression:
        return None
    parts = stem.rsplit("-", maxsplit=3)
    if len(parts) != 4:
        return None
    name, version, release, architecture = parts
    if not name or not version or not release or not architecture:
        return None
    return CachedPackage(name, filename, path.stat().st_size, f"{version}-{release}")


def scan_cache(path: str | Path = "/var/cache/pacman/pkg") -> tuple[CachedPackage, ...]:
    cache_path = Path(path)
    if not cache_path.is_dir():
        return ()
    entries = []
    for item in sorted(cache_path.iterdir()):
        if item.is_file():
            parsed = parse_cache_filename(item)
            if parsed is not None:
                entries.append(parsed)
    return tuple(entries)


def cache_total(entries: tuple[CachedPackage, ...]) -> int:
    return sum(entry.size for entry in entries)
