"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inspector import inspect_installation, write_inspection
from .jsonsearch import search_json_path, write_json_search_records
from .scanner import scan_installation
from .strings import extract_strings_from_path, write_string_records


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

    strings = sub.add_parser(
        "strings",
        help="Extract printable strings with byte-offset provenance.",
    )
    strings.add_argument("path", type=Path)
    strings.add_argument("--release", required=True)
    strings.add_argument("--contains", help="Only keep strings containing this text.")
    strings.add_argument("--min-length", type=int, default=4)
    strings.add_argument(
        "--output",
        type=Path,
        help="Optional JSONL output path. If omitted, records are printed to stdout.",
    )

    json_search = sub.add_parser(
        "json-search",
        help="Search structured JSON files and preserve JSON-path provenance.",
    )
    json_search.add_argument("path", type=Path)
    json_search.add_argument("term")
    json_search.add_argument(
        "--exact",
        action="store_true",
        help="Require an exact key/value match instead of a substring match.",
    )
    json_search.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Use case-sensitive matching.",
    )
    json_search.add_argument(
        "--output",
        type=Path,
        help="Optional JSONL output path. If omitted, records are printed to stdout.",
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

    if args.command == "strings":
        records = extract_strings_from_path(
            args.path,
            args.release,
            min_length=args.min_length,
            contains=args.contains,
        )
        if args.output:
            destination, count = write_string_records(records, args.output)
            print(f"Extracted {count} strings.")
            print(f"Output: {destination}")
        else:
            for record in records:
                print(json.dumps(record, sort_keys=True, ensure_ascii=False))
        return 0

    if args.command == "json-search":
        records = search_json_path(
            args.path,
            args.term,
            exact=args.exact,
            case_sensitive=args.case_sensitive,
        )
        if args.output:
            destination, count = write_json_search_records(records, args.output)
            print(f"Found {count} JSON matches.")
            print(f"Output: {destination}")
        else:
            for record in records:
                print(json.dumps(record, sort_keys=True, ensure_ascii=False))
        return 0

    if args.command == "scan":
        result = scan_installation(args.path, args.release, args.output)
        print(f"Scanned {result['file_count']} files.")
        print(f"Manifest: {result['manifest']}")
        return 0

    return 1
