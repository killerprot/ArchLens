"""Small read-only CLI for trying ArchLens analysis on the local system."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from archlens.core.analysis import explain_why, freed_size, removal_closure
from archlens.core.graph import DependencyGraph
from archlens.core.report import render_markdown, report_data
from archlens.core.usage import orphans
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
    parser.add_argument("command", choices=("orphans", "explain", "closure", "freed", "export"))
    parser.add_argument("--format", choices=("json", "md"), default="json")
    parser.add_argument("--out", default="-")
    parser.add_argument("--aur-metadata", choices=("none", "cache", "online"), default="none")
    parser.add_argument("packages", nargs="*")
    args = parser.parse_args()
    if args.command not in {"orphans", "export"} and not args.packages:
        parser.error(f"{args.command} requires at least one package")

    graph = DependencyGraph(LocalPacmanSource().load())
    if args.command == "orphans":
        for name in orphans(graph):
            print(name)
    elif args.command == "export":
        data = report_data(graph, {}, {})
        rendered = render_markdown(data) if args.format == "md" else json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if args.out == "-":
            print(rendered, end="")
        else:
            Path(args.out).write_text(rendered, encoding="utf-8")
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
