"""Read-only inspection of a Shape of Dreams installation layout."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

UNITY_VERSION_RE = re.compile(
    rb"(?<!\d)((?:\d{4}|\d)\.\d+\.\d+[abfp]\d+)(?!\d)",
    re.IGNORECASE,
)

BUNDLE_SUFFIXES = {".bundle", ".unity3d", ".assets", ".resource", ".ress"}
DATA_SUFFIXES = {".json", ".csv", ".tsv", ".yaml", ".yml", ".db", ".sqlite", ".sqlite3"}
LOCALIZATION_MARKERS = {
    "localization",
    "localizations",
    "locale",
    "locales",
    "language",
    "languages",
    "i18n",
    "l10n",
}
ASSEMBLY_NAMES_OF_INTEREST = {
    "assembly-csharp.dll",
    "dew.core.dll",
    "dew.internal.dll",
    "unityengine.dll",
    "unityengine.coremodule.dll",
}


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": _relative(path, root),
        "size": stat.st_size,
        "suffix": path.suffix.lower(),
    }


def _find_unity_version(candidates: list[Path]) -> str | None:
    for path in candidates:
        try:
            with path.open("rb") as handle:
                chunk = handle.read(2 * 1024 * 1024)
        except OSError:
            continue
        match = UNITY_VERSION_RE.search(chunk)
        if match:
            return match.group(1).decode("ascii", errors="replace")
    return None


def inspect_installation(installation: Path) -> dict[str, Any]:
    """Inspect likely Unity/data-mining structures without modifying the installation."""
    root = installation.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Installation directory does not exist: {root}")

    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.as_posix().lower(),
    )
    dirs = sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: path.as_posix().lower(),
    )

    unity_data_dirs = [path for path in dirs if path.name.lower().endswith("_data")]
    managed_dirs = [path for path in dirs if path.name.lower() == "managed"]
    raw_data_dirs = [path for path in dirs if path.name.lower() == "rawdata"]
    mod_template_dirs = [
        path
        for path in dirs
        if path.name.lower() == "modtemplate"
        and any(parent.name.lower() == "mods" for parent in path.parents)
    ]
    override_dirs = [
        path
        for path in dirs
        if path.name.lower() == "overrides"
        and any(parent.name.lower() == "!modresources" for parent in path.parents)
    ]

    managed_assemblies = [
        _file_record(path, root)
        for path in files
        if path.suffix.lower() == ".dll"
        and any(parent in managed_dirs for parent in path.parents)
    ]
    core_assemblies = [
        record
        for record in managed_assemblies
        if Path(record["path"]).name.lower() in ASSEMBLY_NAMES_OF_INTEREST
    ]

    il2cpp_metadata = [
        _file_record(path, root)
        for path in files
        if path.name.lower() == "global-metadata.dat"
    ]
    game_assembly = [
        _file_record(path, root)
        for path in files
        if path.name.lower() == "gameassembly.dll"
    ]

    mono_indicators: list[str] = []
    if managed_assemblies:
        mono_indicators.append("managed assemblies present")
    if any(path.name.lower() == "monobleedingedge" for path in dirs):
        mono_indicators.append("MonoBleedingEdge directory present")
    if any(
        Path(item["path"]).name.lower() == "assembly-csharp.dll"
        for item in managed_assemblies
    ):
        mono_indicators.append("Assembly-CSharp.dll present")

    il2cpp_indicators: list[str] = []
    if game_assembly:
        il2cpp_indicators.append("GameAssembly.dll present")
    if il2cpp_metadata:
        il2cpp_indicators.append("global-metadata.dat present")

    if mono_indicators and il2cpp_indicators:
        scripting_backend = "mixed-or-ambiguous"
    elif il2cpp_indicators:
        scripting_backend = "il2cpp"
    elif mono_indicators:
        scripting_backend = "mono"
    else:
        scripting_backend = "unknown"

    version_candidates = [
        path
        for path in files
        if path.name.lower() in {"globalgamemanagers", "globalgamemanagers.assets"}
    ]
    version_candidates.extend(
        path
        for path in files
        if path.name.lower() in {"unityplayer.dll", "unityplayer.so"}
    )
    unity_version = _find_unity_version(version_candidates)

    resource_files: list[dict[str, Any]] = []
    for path in files:
        lower_name = path.name.lower()
        suffix = path.suffix.lower()
        if (
            suffix in BUNDLE_SUFFIXES
            or lower_name == "globalgamemanagers"
            or (lower_name.startswith("sharedassets") and suffix == ".assets")
            or lower_name == "resources.assets"
        ):
            resource_files.append(_file_record(path, root))

    localization_files: list[dict[str, Any]] = []
    likely_data_files: list[dict[str, Any]] = []
    raw_data_files: list[dict[str, Any]] = []
    for path in files:
        lower_parts = {part.lower() for part in path.parts}
        suffix = path.suffix.lower()

        if any(raw_dir in path.parents for raw_dir in raw_data_dirs):
            raw_data_files.append(_file_record(path, root))

        if lower_parts & LOCALIZATION_MARKERS:
            localization_files.append(_file_record(path, root))
        elif any(marker in path.name.lower() for marker in LOCALIZATION_MARKERS):
            localization_files.append(_file_record(path, root))

        if suffix in DATA_SUFFIXES and (
            any(raw_dir in path.parents for raw_dir in raw_data_dirs)
            or bool(lower_parts & LOCALIZATION_MARKERS)
            or "config" in path.name.lower()
            or "database" in path.name.lower()
        ):
            likely_data_files.append(_file_record(path, root))

    executables = [
        _file_record(path, root)
        for path in files
        if path.suffix.lower() == ".exe"
    ]

    return {
        "schema_version": 1,
        "installation": str(root),
        "engine": {
            "unity_version": unity_version,
            "scripting_backend": scripting_backend,
            "mono_indicators": mono_indicators,
            "il2cpp_indicators": il2cpp_indicators,
        },
        "layout": {
            "unity_data_directories": [_relative(path, root) for path in unity_data_dirs],
            "raw_data_directories": [_relative(path, root) for path in raw_data_dirs],
            "mod_template_directories": [_relative(path, root) for path in mod_template_dirs],
            "override_directories": [_relative(path, root) for path in override_dirs],
            "executables": executables,
        },
        "assemblies": {
            "managed_directory_count": len(managed_dirs),
            "managed_assembly_count": len(managed_assemblies),
            "managed": managed_assemblies,
            "core": core_assemblies,
            "game_assembly": game_assembly,
            "il2cpp_metadata": il2cpp_metadata,
        },
        "resources": {
            "count": len(resource_files),
            "files": resource_files,
        },
        "raw_data": {
            "count": len(raw_data_files),
            "files": raw_data_files,
        },
        "localization_candidates": {
            "count": len(localization_files),
            "files": localization_files,
        },
        "likely_data_files": {
            "count": len(likely_data_files),
            "files": likely_data_files,
        },
    }


def write_inspection(report: dict[str, Any], output: Path) -> Path:
    """Write an inspection report as deterministic, human-readable JSON."""
    destination = output.expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return destination
