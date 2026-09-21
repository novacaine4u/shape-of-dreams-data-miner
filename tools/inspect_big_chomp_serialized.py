from __future__ import annotations

import argparse
import json
import mmap
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path


TERM = "St_U_BigChomp"
FIELD_TERMS = ("St_U_BigChomp", "rarity", "excludeFromPool", "isCharacterSkill")


def run(cmd: list[str], *, stdout_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if stdout_path is not None:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(result.stdout, encoding="utf-8")
        if result.stderr:
            stdout_path.with_suffix(stdout_path.suffix + ".stderr.txt").write_text(
                result.stderr, encoding="utf-8"
            )
    return result


def find_occurrences(path: Path, term: str) -> list[tuple[int, str]]:
    needles = [
        (term.encode("ascii"), "ascii"),
        (term.encode("utf-16le"), "utf-16le"),
    ]
    found: set[tuple[int, str]] = set()
    with path.open("rb") as handle:
        with mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for needle, encoding in needles:
                start = 0
                while True:
                    pos = mm.find(needle, start)
                    if pos < 0:
                        break
                    found.add((pos, encoding))
                    start = pos + 1
    return sorted(found)


def load_object_list(tool: Path, serialized_file: Path, out_dir: Path) -> list[dict]:
    json_path = out_dir / f"{serialized_file.name}.objectlist.json"
    result = run(
        [str(tool), "sf", "objectlist", str(serialized_file), "-f", "json"],
        stdout_path=json_path,
    )
    if result.returncode != 0:
        return []
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def map_offsets(objects: list[dict], occurrences: list[tuple[int, str]]) -> list[tuple[int, str, dict]]:
    ordered = sorted(objects, key=lambda item: int(item.get("offset", -1)))
    matches: list[tuple[int, str, dict]] = []
    for offset, encoding in occurrences:
        for item in ordered:
            start = int(item.get("offset", -1))
            size = int(item.get("size", 0))
            if start <= offset < start + size:
                matches.append((offset, encoding, item))
                break
    return matches


def inspect_serialized_file(
    tool: Path,
    serialized_file: Path,
    out_dir: Path,
    report: list[str],
) -> None:
    occurrences = find_occurrences(serialized_file, TERM)
    if not occurrences:
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    report.append(f"FILE: {serialized_file}")
    for offset, encoding in occurrences:
        report.append(f"  TERM offset={offset} encoding={encoding}")

    metadata_path = out_dir / f"{serialized_file.name}.metadata.txt"
    run([str(tool), "sf", "metadata", str(serialized_file)], stdout_path=metadata_path)

    objects = load_object_list(tool, serialized_file, out_dir)
    if not objects:
        report.append("  Object list unavailable.")
        report.append("")
        return

    mapped = map_offsets(objects, occurrences)
    for offset, encoding, item in mapped:
        report.append(
            "  MAP "
            f"offset={offset} encoding={encoding} -> "
            f"id={item.get('id')} type={item.get('typeName')} "
            f"objectOffset={item.get('offset')} size={item.get('size')}"
        )
    report.append("")


def find_extracted_serialized_file(root: Path, name: str) -> Path | None:
    matches = [p for p in root.rglob(name) if p.is_file()]
    if not matches:
        return None
    return sorted(matches, key=lambda p: (len(p.parts), str(p)))[0]


def dict_row(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


def analyze_big_chomp_components(
    tool: Path,
    bundle: Path,
    out_dir: Path,
    report: list[str],
) -> list[Path]:
    report.append("=== AssetBundle analyzer component trace ===")

    db_path = out_dir / "big-chomp-bundle-analysis.db"
    analyze_log = out_dir / "bundle-analyze.txt"
    result = run(
        [str(tool), "analyze", str(bundle), "-o", str(db_path), "--skip-crc"],
        stdout_path=analyze_log,
    )
    if result.returncode != 0 or not db_path.exists():
        report.append("Bundle analyze failed; see bundle-analyze logs.")
        report.append("")
        return []

    extracted = out_dir / "bundle-extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    extract_result = run(
        [str(tool), "archive", "extract", str(bundle), "-o", str(extracted)],
        stdout_path=out_dir / "bundle-extract.txt",
    )
    if extract_result.returncode != 0:
        report.append("Bundle extraction failed; see bundle-extract logs.")
        report.append("")
        return []

    dumps_dir = out_dir / "component-dumps"
    dumps_dir.mkdir(parents=True, exist_ok=True)
    dump_paths: list[Path] = []

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        game_objects = connection.execute(
            """
            SELECT *
            FROM object_view
            WHERE type = 'GameObject' AND name = ?
            ORDER BY serialized_file, object_id
            """,
            (TERM,),
        ).fetchall()

        report.append(f"Named GameObjects found: {len(game_objects)}")

        for index, game_object in enumerate(game_objects, start=1):
            go = dict_row(game_object)
            report.append(
                f"GAMEOBJECT[{index}]: analyzer_id={go['id']} "
                f"object_id={go['object_id']} serialized_file={go['serialized_file']} "
                f"archive={go['archive']}"
            )

            components = connection.execute(
                """
                SELECT *
                FROM object_view
                WHERE game_object = ?
                ORDER BY type, object_id
                """,
                (go["id"],),
            ).fetchall()

            report.append(f"  Components: {len(components)}")

            for component in components:
                comp = dict_row(component)
                precise_script: dict[str, object] | None = None
                try:
                    script_row = connection.execute(
                        "SELECT * FROM script_object_view WHERE id = ?",
                        (comp["id"],),
                    ).fetchone()
                    if script_row is not None:
                        precise_script = dict_row(script_row)
                except sqlite3.DatabaseError:
                    precise_script = None

                script_bits = ""
                if precise_script:
                    interesting = []
                    for key, value in precise_script.items():
                        if key in {
                            "namespace",
                            "class",
                            "class_name",
                            "script",
                            "script_name",
                            "assembly",
                            "assembly_name",
                            "type_name",
                            "full_name",
                        } and value not in (None, ""):
                            interesting.append(f"{key}={value}")
                    if interesting:
                        script_bits = " [" + ", ".join(interesting) + "]"

                report.append(
                    f"  COMPONENT analyzer_id={comp['id']} "
                    f"object_id={comp['object_id']} type={comp['type']} "
                    f"serialized_file={comp['serialized_file']}{script_bits}"
                )

                serialized_path = find_extracted_serialized_file(
                    extracted, str(comp["serialized_file"])
                )
                if serialized_path is None:
                    report.append(
                        f"    WARNING: extracted serialized file not found: {comp['serialized_file']}"
                    )
                    continue

                safe_type = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(comp["type"]))
                dump_path = (
                    dumps_dir
                    / f"go{index}_component_{comp['object_id']}_{safe_type}.txt"
                )
                dump_result = run(
                    [
                        str(tool),
                        "dump",
                        str(serialized_path),
                        "--stdout",
                        "-i",
                        str(comp["object_id"]),
                    ],
                    stdout_path=dump_path,
                )
                if dump_result.returncode == 0:
                    dump_paths.append(dump_path)
                else:
                    report.append(
                        f"    WARNING: dump failed for object_id={comp['object_id']}"
                    )

            report.append("")

        target_ids = []
        target_rows = connection.execute(
            """
            SELECT id, object_id, type, name, game_object, serialized_file
            FROM object_view
            WHERE (type = 'GameObject' AND name = ?)
               OR game_object IN (
                    SELECT id FROM object_view
                    WHERE type = 'GameObject' AND name = ?
               )
            ORDER BY id
            """,
            (TERM, TERM),
        ).fetchall()
        target_ids = [row["id"] for row in target_rows]

        report.append("=== Incoming references to Big Chomp objects ===")
        if not target_ids:
            report.append("No target analyzer ids found.")
        else:
            placeholders = ",".join("?" for _ in target_ids)
            ref_rows = connection.execute(
                f"""
                SELECT
                    rv.object AS source_id,
                    rv.referenced_object AS target_id,
                    rv.property_path,
                    rv.property_type,
                    ov.object_id AS source_object_id,
                    ov.type AS source_type,
                    ov.name AS source_name,
                    ov.game_object AS source_game_object,
                    ov.serialized_file AS source_serialized_file
                FROM refs_view rv
                JOIN object_view ov ON ov.id = rv.object
                WHERE rv.referenced_object IN ({placeholders})
                ORDER BY rv.referenced_object, ov.type, ov.object_id, rv.property_path
                """,
                target_ids,
            ).fetchall()

            report.append(f"Incoming reference count: {len(ref_rows)}")
            for row in ref_rows:
                script_info = ""
                try:
                    sr = connection.execute(
                        "SELECT * FROM script_object_view WHERE id = ?",
                        (row["source_id"],),
                    ).fetchone()
                    if sr is not None:
                        values = []
                        for key in sr.keys():
                            value = sr[key]
                            if value not in (None, "") and key not in {
                                "id", "object_id", "size", "crc32", "game_object"
                            }:
                                values.append(f"{key}={value}")
                        if values:
                            script_info = " [" + ", ".join(values) + "]"
                except sqlite3.DatabaseError:
                    pass

                report.append(
                    "REF "
                    f"source_id={row['source_id']} "
                    f"source_object_id={row['source_object_id']} "
                    f"source_type={row['source_type']} "
                    f"source_name={row['source_name']!r} "
                    f"source_file={row['source_serialized_file']} "
                    f"property={row['property_path']} "
                    f"property_type={row['property_type']} "
                    f"target_id={row['target_id']}"
                    f"{script_info}"
                )
        report.append("")
    finally:
        connection.close()

    return dump_paths


def append_rarity_enum_trace(game_root: Path, out_dir: Path, report: list[str]) -> None:
    report.append("=== Rarity enum trace ===")
    assembly = game_root / "Shape of Dreams_Data" / "Managed" / "Dew.Core.dll"
    if not assembly.exists():
        report.append(f"Missing: {assembly}")
        report.append("")
        return

    repo_root = Path(__file__).resolve().parents[1]
    restore = run(
        ["dotnet", "tool", "restore", "--configfile", str(repo_root / "NuGet.config")],
        stdout_path=out_dir / "ilspy-tool-restore.txt",
    )
    if restore.returncode != 0:
        report.append("ILSpy tool restore failed; see ilspy-tool-restore logs.")
        report.append("")
        return

    rarity_path = out_dir / "Rarity.cs"
    result = run(
        ["dotnet", "tool", "run", "ilspycmd", "-t", "Rarity", str(assembly)],
        stdout_path=rarity_path,
    )
    if result.returncode != 0:
        report.append("Rarity decompile failed; see Rarity.cs stderr log.")
        report.append("")
        return

    enum_lines = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if any(name in stripped for name in (
            "Common", "Rare", "Epic", "Legendary", "Character", "Identity", "Unique"
        )):
            enum_lines.append(stripped)

    for line in enum_lines:
        report.append(f"  {line}")
    report.append("")


def append_focused_hits(dump_paths: list[Path], report: list[str]) -> int:
    report.append("=== Focused component field hits ===")
    hit_count = 0
    for dump_path in dump_paths:
        try:
            lines = dump_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, start=1):
            if any(term.lower() in line.lower() for term in FIELD_TERMS):
                report.append(f"{dump_path}:{number}: {line}")
                hit_count += 1
    report.append("")
    report.append(f"Focused component hit count: {hit_count}")
    return hit_count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--tool", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/extracted/big-chomp-serialized"),
    )
    args = parser.parse_args()

    game_root = args.game_root.resolve()
    tool = args.tool.resolve()
    out_dir = args.output.resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    report: list[str] = [
        "=== Big Chomp serialized resource inspection ===",
        f"Game root: {game_root}",
        f"UnityDataTool: {tool}",
        "",
    ]

    resources = game_root / "Shape of Dreams_Data" / "resources.assets"
    if resources.exists():
        inspect_serialized_file(tool, resources, out_dir / "resources", report)
    else:
        report.append(f"Missing: {resources}")

    bundle = (
        game_root
        / "Shape of Dreams_Data"
        / "StreamingAssets"
        / "aa"
        / "StandaloneWindows64"
        / "defaultlocalgroup_assets_all_f2387b6895a961fa06fa44f1fcd3ded5.bundle"
    )

    dump_paths: list[Path] = []
    if bundle.exists():
        dump_paths = analyze_big_chomp_components(tool, bundle, out_dir, report)
    else:
        report.append(f"Missing: {bundle}")

    append_focused_hits(dump_paths, report)
    append_rarity_enum_trace(game_root, out_dir, report)
    report.append(
        "Needed final fields: rarity, excludeFromPool, isCharacterSkill for St_U_BigChomp."
    )

    summary = out_dir / "summary.txt"
    summary.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(summary.read_text(encoding="utf-8"))
    print(f"Output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
