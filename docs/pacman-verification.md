# Verified pacman behavior

The checks below were run read-only on the development machine on 2026-10-25.

- `pacman --help` exposes the operation-specific help commands.
- `pacman -R --help` documents `-p/--print`, `-n/--nosave`, and `-s/--recursive`.
- `pacman -Rns --print <package>` does **not** work with this pacman: it reports
  `invalid option: '--nosave' and '--print' may not be used together`.
- `pacman -R --print <package>` and `pacman -Rs --print <package>` work without
  root. For a removable orphan, the output is one `name-version-release` line,
  for example `argagg-0.4.7-4`.
- Therefore the verification script uses the working `pacman -Rs --print` form
  and records that it cannot perform the exact `-Rns --print` probe on this
  machine. No extra flags were needed.
- `pacman -Qmq` returns foreign package names; a command failure is represented
  as unknown by the source adapter.
- On this machine, current pacman stores `%DEPENDS%`, `%OPTDEPENDS%`, and
  `%PROVIDES%` in each package's `desc`; no separate `depends` file is present.
  The parser supports that format and the separate `depends` file used by the
  fixture specification.
- `pacman -Qdt` excludes optional-only packages, while `pacman -Qdtt` includes
  them. The analysis API calls these `unrequired(..., ignore_optional=False)` and
  `unrequired(..., ignore_optional=True)` respectively.

The MVP deliberately ignores version constraints after parsing the dependency
name. It also treats all installed providers of a virtual dependency as needed
edges, while removal blocking requires all providers to be in the removal set.
