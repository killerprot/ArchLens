"""Package source interfaces."""

from abc import ABC, abstractmethod

from archlens.core.models import Package

MIN_SYNC_PACKAGES = 1000


class PackageSource(ABC):
    """Read-only source of installed package metadata."""

    @abstractmethod
    def load(self) -> tuple[Package, ...]:
        """Load all installed packages."""

    @abstractmethod
    def foreign_names(self) -> frozenset[str] | None:
        """Return names reported by ``pacman -Qmq`` or ``None`` on failure."""

    @abstractmethod
    def sync_reliable(self) -> bool:
        """Whether the local sync databases contain enough package records."""
