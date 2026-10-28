# Changelog

## Unreleased — ArchLens 2.0.0

### BREAKING

- Orphan detection now follows strict `pacman -Qdt`-style usage semantics.
- Optional-only packages are shown separately and are not safe-removal candidates.
- Reports include usage status, optional reverse dependencies, source, and ambiguity metadata.

### Added

- Repository/foreign/unknown source classification.
- Offline-safe AUR metadata models, sanitization, version comparison, batching, cache, and consent-aware service.
