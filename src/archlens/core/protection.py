"""Protected package rules used by removal workflows."""

DEFAULT_PROTECTED = frozenset({"base", "linux", "pacman", "systemd", "glibc"})


def protected_packages(extra: set[str] | None = None) -> frozenset[str]:
    return DEFAULT_PROTECTED | frozenset(extra or ())
