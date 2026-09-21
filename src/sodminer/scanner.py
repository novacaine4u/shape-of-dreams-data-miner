"""Read-only installation scanner."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_IGNORED_DIRS = {".git", "data", "logs", "temp", "cache"}


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def scan_installation(installation: Path, release: str, output: Path) -> dict[str, Any]:
    """Create a deterministic file manifest without modifying the installation."""
    installation = installation.expanduser().resolve()
    if not installation.is_dir():
        raise FileNotFoundError(f"Installation directory does not exist: {installation}")

    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / f"{release}-manifest.json"
    records: list[dict[str, Any]] = []

    for path in sorted(installation.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(installation).parts
        if any(part.lower() in DEFAULT_IGNORED_DIRS for part in relative_parts):
            continue
        stat = path.stat()
        records.append({
            "path": path.relative_to(installation).as_posix(),
            "size": stat.st_size,
            "sha256": _sha256(path),
            "mtime_ns": stat.st_mtime_ns,
            "suffix": path.suffix.lower(),
        })

    payload = {
        "schema_version": 1,
        "release": release,
        "installation": str(installation),
        "file_count": len(records),
        "files": records,
    }
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"release": release, "file_count": len(records), "manifest": str(manifest_path)}
