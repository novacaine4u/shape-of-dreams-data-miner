"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inspector import inspect_installation, write_inspection
from .scanner import scan_installation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sodminer",
        description="Scan Shape of Dreams installations and build research data.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser(
        "inspect",
        help="Inspect the game installation layout and Unity backend.",
    )
    inspect.add_argument("path", type=Path)
    inspect.add_argument(
        "--output",
        type=Path,
        help="Optional JSON report path. If omitted, the report is printed to stdout.",
    )

    scan = sub.add_parser("scan", help="Scan a game installation.")
    scan.add_argument("path", type=Path)
    scan.add_argument("--release", required=True)
    scan.add_argument("--output", type=Path, default=Path("data/raw"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "inspect":
        report = inspect_installation(args.path)
        if args.output:
            destination = write_inspection(report, args.output)
            print(f"Inspection report: {destination}")
        else:
            print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if args.command == "scan":
        result = scan_installation(args.path, args.release, args.output)
        print(f"Scanned {result['file_count']} files.")
        print(f"Manifest: {result['manifest']}")
        return 0
    return 1
