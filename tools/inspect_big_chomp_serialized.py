from __future__ import annotations

import argparse
import json
import mmap
import re
import shutil
import subprocess
from pathlib import Path


TERM = "St_U_BigChomp"
FIELD_TERMS = ("St_U_BigChomp", "rarity", "excludeFromPool", "isCharacterSkill")
MAX_FOLLOW_OBJECTS = 40


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


def extract_local_path_ids(text: str) -> set[int]:
    ids: set[int] = set()
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if "m_PathID" not in line:
            continue
        match = re.search(r"m_PathID[^-0-9]*(-?\d+)", line)
        if match:
            value = int(match.group(1))
            if value != 0:
                ids.add(value)
    return ids


def dump_object_graph(
    tool: Path,
    serialized_file: Path,
    objects: list[dict],
    seed_ids: list[int],
    out_dir: Path,
) -> list[Path]:
    known_ids = {int(item["id"]) for item in objects if "id" in item}
    queue = list(dict.fromkeys(seed_ids))
    seen: set[int] = set()
    dumps: list[Path] = []

    while queue and len(seen) < MAX_FOLLOW_OBJECTS:
        object_id = queue.pop(0)
        if object_id in seen or object_id not in known_ids:
            continue
        seen.add(object_id)
        safe_file = re.sub(r"[^A-Za-z0-9_.-]+", "_", serialized_file.name)
        dump_path = out_dir / f"{safe_file}.object_{object_id}.txt"
        result = run(
            [str(tool), "dump", str(serialized_file), "--stdout", "-i", str(object_id)],
            stdout_path=dump_path,
        )
        if result.returncode != 0:
            continue
        dumps.append(dump_path)
        for ref_id in extract_local_path_ids(result.stdout):
            if ref_id in known_ids and ref_id not in seen:
                queue.append(ref_id)

    return dumps


def inspect_serialized_file(
    tool: Path,
    serialized_file: Path,
    out_dir: Path,
    report: list[str],
) -> list[Path]:
    occurrences = find_occurrences(serialized_file, TERM)
    if not occurrences:
        return []

    report.append(f"FILE: {serialized_file}")
    for offset, encoding in occurrences:
        report.append(f"  TERM offset={offset} encoding={encoding}")

    metadata_path = out_dir / f"{serialized_file.name}.metadata.txt"
    run([str(tool), "sf", "metadata", str(serialized_file)], stdout_path=metadata_path)

    objects = load_object_list(tool, serialized_file, out_dir)
    if not objects:
        report.append("  Object list unavailable.")
        report.append("")
        return []

    mapped = map_offsets(objects, occurrences)
    seed_ids: list[int] = []
    for offset, encoding, item in mapped:
        object_id = int(item["id"])
        seed_ids.append(object_id)
        report.append(
            "  MAP "
            f"offset={offset} encoding={encoding} -> "
            f"id={object_id} type={item.get('typeName')} "
            f"objectOffset={item.get('offset')} size={item.get('size')}"
        )

    if not seed_ids:
        report.append("  No term occurrence mapped into an object range.")
        report.append("")
        return []

    dump_dir = out_dir / "objects"
    dump_dir.mkdir(parents=True, exist_ok=True)
    dumps = dump_object_graph(tool, serialized_file, objects, seed_ids, dump_dir)
    report.append(f"  Dumped object graph files: {len(dumps)}")
    report.append("")
    return dumps


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
    all_dumps: list[Path] = []

    resources = game_root / "Shape of Dreams_Data" / "resources.assets"
    if resources.exists():
        all_dumps.extend(inspect_serialized_file(tool, resources, out_dir / "resources", report))
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

    if bundle.exists():
        extracted = out_dir / "bundle-extracted"
        extracted.mkdir(parents=True, exist_ok=True)
        extract_result = run(
            [str(tool), "archive", "extract", str(bundle), "-o", str(extracted)],
            stdout_path=out_dir / "bundle-extract.txt",
        )
        if extract_result.returncode == 0:
            for candidate in sorted(p for p in extracted.rglob("*") if p.is_file()):
                try:
                    if find_occurrences(candidate, TERM):
                        all_dumps.extend(
                            inspect_serialized_file(
                                tool,
                                candidate,
                                out_dir / "bundle-objects" / candidate.name,
                                report,
                            )
                        )
                except OSError:
                    continue
        else:
            report.append("Addressables bundle extraction failed; see bundle-extract logs.")
    else:
        report.append(f"Missing: {bundle}")

    report.append("=== Focused field hits ===")
    hit_count = 0
    for dump_path in all_dumps:
        try:
            lines = dump_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, start=1):
            if any(term.lower() in line.lower() for term in FIELD_TERMS):
                report.append(f"{dump_path}:{number}: {line}")
                hit_count += 1

    report.append("")
    report.append(f"Focused hit count: {hit_count}")
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
