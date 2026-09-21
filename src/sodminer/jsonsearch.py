"""Structured JSON search with source and JSON-path provenance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator


def _matches(
    text: str,
    term: str,
    *,
    exact: bool,
    case_sensitive: bool,
) -> bool:
    if case_sensitive:
        candidate = text
        needle = term
    else:
        candidate = text.casefold()
        needle = term.casefold()
    return candidate == needle if exact else needle in candidate


def _child_path(path: str, key: str) -> str:
    return f"{path}[{json.dumps(key, ensure_ascii=False)}]"


def _walk(
    node: Any,
    *,
    term: str,
    path: str = "$",
    top_level_key: str | None = None,
    exact: bool = False,
    case_sensitive: bool = False,
) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            key_text = str(key)
            child_path = _child_path(path, key_text)
            container = top_level_key
            if path == "$":
                container = key_text

            if _matches(
                key_text,
                term,
                exact=exact,
                case_sensitive=case_sensitive,
            ):
                yield {
                    "json_path": child_path,
                    "match_kind": "key",
                    "matched_text": key_text,
                    "top_level_key": container,
                }

            yield from _walk(
                value,
                term=term,
                path=child_path,
                top_level_key=container,
                exact=exact,
                case_sensitive=case_sensitive,
            )
        return

    if isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(
                value,
                term=term,
                path=f"{path}[{index}]",
                top_level_key=top_level_key,
                exact=exact,
                case_sensitive=case_sensitive,
            )
        return

    if isinstance(node, str) and _matches(
        node,
        term,
        exact=exact,
        case_sensitive=case_sensitive,
    ):
        yield {
            "json_path": path,
            "match_kind": "value",
            "matched_text": node,
            "top_level_key": top_level_key,
        }


def search_json_file(
    path: Path,
    term: str,
    *,
    source_name: str | None = None,
    exact: bool = False,
    case_sensitive: bool = False,
) -> list[dict[str, Any]]:
    """Search one JSON file and return provenance-aware match records."""
    source = path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"JSON source file does not exist: {source}")

    data = json.loads(source.read_text(encoding="utf-8-sig"))
    display_source = source_name or source.name
    records: list[dict[str, Any]] = []

    for record in _walk(
        data,
        term=term,
        exact=exact,
        case_sensitive=case_sensitive,
    ):
        records.append({"source_file": display_source, **record})

    return records


def search_json_path(
    source: Path,
    term: str,
    *,
    exact: bool = False,
    case_sensitive: bool = False,
) -> Iterator[dict[str, Any]]:
    """Search one JSON file or all JSON files below a directory."""
    root = source.expanduser().resolve()

    if root.is_file():
        yield from search_json_file(
            root,
            term,
            source_name=root.name,
            exact=exact,
            case_sensitive=case_sensitive,
        )
        return

    if not root.is_dir():
        raise FileNotFoundError(f"JSON source path does not exist: {root}")

    files = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() == ".json"
        ),
        key=lambda path: path.as_posix().lower(),
    )
    for path in files:
        relative = path.relative_to(root).as_posix()
        try:
            yield from search_json_file(
                path,
                term,
                source_name=relative,
                exact=exact,
                case_sensitive=case_sensitive,
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue


def write_json_search_records(
    records: Iterable[dict[str, Any]],
    output: Path,
) -> tuple[Path, int]:
    """Write JSON search matches as deterministic JSON Lines."""
    destination = output.expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
            handle.write("\n")
            count += 1
    return destination, count
