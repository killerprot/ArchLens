"""Immutable domain models used by ArchLens."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Reason(Enum):
    EXPLICIT = 0
    DEPENDENCY = 1


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    description: str
    installed_size: int
    reason: Reason
    install_date: datetime
    depends: tuple[str, ...] = ()
    optdepends: tuple[str, ...] = ()
    provides: tuple[str, ...] = ()
    is_foreign: bool | None = None


@dataclass(frozen=True)
class Orphan:
    package: Package
    optionally_required: bool
