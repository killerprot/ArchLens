"""Package source interfaces."""

from abc import ABC, abstractmethod

from archlens.core.models import Package


class PackageSource(ABC):
    """Read-only source of installed package metadata."""

    @abstractmethod
    def load(self) -> tuple[Package, ...]:
        """Load all installed packages."""
