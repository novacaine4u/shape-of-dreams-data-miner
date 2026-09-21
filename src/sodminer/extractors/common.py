"""Shared helpers for extractors."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from ..models import Evidence


def evidence(source_file: Path, release: str, extractor: str, *, confidence: str = "unknown", detail: str | None = None, location: str | None = None) -> Evidence:
    return Evidence(source_file=source_file.as_posix(), release=release, extractor=extractor, confidence=confidence, detail=detail, location=location)  # type: ignore[arg-type]


def unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
