"""Command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path

from .scanner import scan_installation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sodminer",
        description="Scan Shape of Dreams installations and build research data.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan a game installation.")
    scan.add_argument("path", type=Path)
    scan.add_argument("--release", required=True)
    scan.add_argument("--output", type=Path, default=Path("data/raw"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "scan":
        result = scan_installation(args.path, args.release, args.output)
        print(f"Scanned {result['file_count']} files.")
        print(f"Manifest: {result['manifest']}")
        return 0
    return 1
