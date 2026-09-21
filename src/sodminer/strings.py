"""Raw printable-string extraction with byte-offset provenance."""

from __future__ import annotations

import json
import mmap
import re
from pathlib import Path
from typing import Any, Iterable, Iterator

_UTF8_CODEPOINT = (
    rb"(?:"
    rb"[\x20-\x7e]"
    rb"|[\xc2-\xdf][\x80-\xbf]"
    rb"|\xe0[\xa0-\xbf][\x80-\xbf]"
    rb"|[\xe1-\xec\xee-\xef][\x80-\xbf]{2}"
    rb"|\xed[\x80-\x9f][\x80-\xbf]"
    rb"|\xf0[\x90-\xbf][\x80-\xbf]{2}"
    rb"|[\xf1-\xf3][\x80-\xbf]{3}"
    rb"|\xf4[\x80-\x8f][\x80-\xbf]{2}"
    rb")"
)


def _patterns(min_length: int) -> tuple[re.Pattern[bytes], re.Pattern[bytes], re.Pattern[bytes]]:
    if min_length < 1:
        raise ValueError("min_length must be at least 1")
    count = str(min_length).encode("ascii")
    ascii_pattern = re.compile(rb"[\x20-\x7e]{" + count + rb",}")
    utf8_pattern = re.compile(_UTF8_CODEPOINT + rb"{" + count + rb",}")
    utf16le_pattern = re.compile(
        rb"(?:[\x20-\x7e]\x00){" + count + rb",}"
    )
    return ascii_pattern, utf8_pattern, utf16le_pattern


def _wanted(text: str, contains: str | None) -> bool:
    return contains is None or contains.casefold() in text.casefold()


def extract_strings(
    path: Path,
    release: str,
    *,
    source_name: str | None = None,
    min_length: int = 4,
    contains: str | None = None,
) -> list[dict[str, Any]]:
    """Extract printable strings from one file without changing it."""
    source = path.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source file does not exist: {source}")
    if source.stat().st_size == 0:
        return []

    ascii_pattern, utf8_pattern, utf16le_pattern = _patterns(min_length)
    records: list[dict[str, Any]] = []
    display_source = source_name or source.name

    with source.open("rb") as handle:
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
            for match in ascii_pattern.finditer(data):
                text = match.group().decode("ascii")
                if _wanted(text, contains):
                    records.append(
                        {
                            "source_file": display_source,
                            "release": release,
                            "offset": match.start(),
                            "encoding": "ascii",
                            "text": text,
                        }
                    )

            for match in utf8_pattern.finditer(data):
                raw = match.group()
                if not any(byte >= 0x80 for byte in raw):
                    continue
                text = raw.decode("utf-8")
                if text.isprintable() and _wanted(text, contains):
                    records.append(
                        {
                            "source_file": display_source,
                            "release": release,
                            "offset": match.start(),
                            "encoding": "utf-8",
                            "text": text,
                        }
                    )

            for match in utf16le_pattern.finditer(data):
                text = match.group().decode("utf-16le")
                if _wanted(text, contains):
                    records.append(
                        {
                            "source_file": display_source,
                            "release": release,
                            "offset": match.start(),
                            "encoding": "utf-16le",
                            "text": text,
                        }
                    )

    records.sort(key=lambda item: (item["offset"], item["encoding"], item["text"]))
    return records


def extract_strings_from_path(
    source: Path,
    release: str,
    *,
    min_length: int = 4,
    contains: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Extract strings from one file or recursively from a directory."""
    if min_length < 1:
        raise ValueError("min_length must be at least 1")

    root = source.expanduser().resolve()
    if root.is_file():
        yield from extract_strings(
            root,
            release,
            source_name=root.name,
            min_length=min_length,
            contains=contains,
        )
        return

    if not root.is_dir():
        raise FileNotFoundError(f"Source path does not exist: {root}")

    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.as_posix().lower(),
    )
    for path in files:
        relative = path.relative_to(root).as_posix()
        try:
            yield from extract_strings(
                path,
                release,
                source_name=relative,
                min_length=min_length,
                contains=contains,
            )
        except OSError:
            continue


def write_string_records(
    records: Iterable[dict[str, Any]],
    output: Path,
) -> tuple[Path, int]:
    """Write extracted string records as deterministic JSON Lines."""
    destination = output.expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False))
            handle.write("\n")
            count += 1
    return destination, count
