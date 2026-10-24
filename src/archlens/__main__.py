"""Small read-only CLI for trying ArchLens analysis on the local system."""

from __future__ import annotations

import argparse
import sys

from archlens.core.analysis import explain_why, freed_size, orphans, removal_closure
from archlens.core.graph import DependencyGraph
from archlens.infra.local_db import LocalPacmanSource


def main() -> int:
    if len(sys.argv) == 1:
        from PySide6.QtWidgets import QApplication

        from archlens.ui.main_window import MainWindow

        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        return app.exec()
    parser = argparse.ArgumentParser(prog="python -m archlens")
    parser.add_argument("command", choices=("orphans", "explain", "closure", "freed"))
    parser.add_argument("packages", nargs="*")
    args = parser.parse_args()
    if args.command != "orphans" and not args.packages:
        parser.error(f"{args.command} requires at least one package")

    graph = DependencyGraph(LocalPacmanSource().load())
    if args.command == "orphans":
        for item in orphans(graph):
            marker = " optionally-required" if item.optionally_required else ""
            print(f"{item.package.name}{marker}")
    elif args.command == "explain":
        result = explain_why(graph, args.packages[0])
        print(" -> ".join(result) if result else "no explicit root found")
    elif args.command == "closure":
        print("\n".join(sorted(removal_closure(graph, set(args.packages)))))
    else:
        print(freed_size(graph, set(args.packages)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
