"""Build a release-scoped SQLite data dictionary from game data."""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Iterable

from .database import (
    create_database,
    insert_attribute,
    insert_evidence,
    insert_release,
    upsert_entity,
)
from .drop_rates import (
    RARITY_VALUE_BY_NAME,
    ascension_gem_formula,
    ascension_input_rarity,
    ascension_skill_formula,
    normal_loot_formula,
    rarity_name,
)

_FIELD_RE = re.compile(
    r"^(?P<indent>\s*)(?P<name>[^()]+?)\s+\((?P<type>[^)]+)\)(?:\s+(?P<value>.*))?$"
)


def infer_entity_type(internal_id: str, source_path: str | None = None) -> str:
    if internal_id.startswith("St_"):
        return "skill"
    if internal_id.startswith("Gem_"):
        return "gem"
    if internal_id.startswith("Hero_"):
        return "hero"
    if internal_id.startswith("Shrine_"):
        return "shrine"
    if internal_id.startswith("Ach_"):
        return "achievement"
    if internal_id.startswith("Skin_"):
        return "skin"
    if internal_id.startswith("Acc_"):
        return "accessory"
    if internal_id.startswith("Nametag_"):
        return "nametag"
    if internal_id.startswith("Emote_"):
        return "emote"
    if internal_id.startswith("Se_"):
        return "status_effect"
    if internal_id.startswith("Ai_"):
        return "skill_ai"
    if source_path:
        lower = source_path.lower()
        if "memories" in lower:
            return "skill"
        if "achievement" in lower:
            return "achievement"
        if "heroes" in lower or "travelers" in lower:
            return "hero"
    return "game_object"


def _parse_scalar(raw: str | None, type_name: str) -> Any:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    if type_name in {
        "SInt8", "UInt8", "SInt16", "UInt16", "SInt32", "UInt32",
        "SInt64", "UInt64", "int", "unsigned int", "short", "long long",
    }:
        try:
            return int(text, 0)
        except ValueError:
            return text
    if type_name in {"float", "double"}:
        try:
            return float(text)
        except ValueError:
            return text
    if type_name in {"bool", "Boolean"}:
        return text.lower() in {"1", "true"}
    return text


def parse_unity_dump(text: str) -> dict[str, Any]:
    """Flatten scalar UnityDataTool dump fields into dotted property paths."""
    result: dict[str, Any] = {}
    stack: list[tuple[int, str]] = []

    for line in text.splitlines():
        match = _FIELD_RE.match(line)
        if not match:
            continue
        indent = len(match.group("indent").expandtabs(4))
        name = match.group("name").strip()
        type_name = match.group("type").strip()
        raw_value = match.group("value")

        while stack and stack[-1][0] >= indent:
            stack.pop()

        path = ".".join([item[1] for item in stack] + [name])
        value = _parse_scalar(raw_value, type_name)
        if value is not None:
            result[path] = value

        if raw_value is None or raw_value.strip() == "":
            stack.append((indent, name))

    return result


def _first_by_leaf(fields: dict[str, Any], leaf: str) -> Any:
    for path, value in fields.items():
        if path == leaf or path.endswith("." + leaf):
            return value
    return None


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )


def _bundle_index(bundle_root: Path) -> dict[str, Path]:
    return {
        path.name: path
        for path in bundle_root.rglob("*.bundle")
        if path.is_file()
    }


def _serialized_file_from_bundle(
    unity_tool: Path,
    bundle_path: Path,
    serialized_name: str,
    cache_root: Path,
) -> Path | None:
    cache_dir = cache_root / bundle_path.stem
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        result = _run(
            [
                str(unity_tool),
                "archive",
                "extract",
                str(bundle_path),
                "-o",
                str(cache_dir),
            ]
        )
        if result.returncode != 0:
            return None

    matches = [
        path for path in cache_dir.rglob(serialized_name)
        if path.is_file()
    ]
    if not matches:
        return None
    return sorted(matches, key=lambda item: (len(item.parts), str(item)))[0]


def _dump_component(
    unity_tool: Path,
    serialized_file: Path,
    object_id: int,
) -> str | None:
    result = _run(
        [
            str(unity_tool),
            "dump",
            str(serialized_file),
            "--stdout",
            "-i",
            str(object_id),
        ]
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _insert_rawdata(
    connection: sqlite3.Connection,
    release_id: int,
    rawdata_root: Path,
) -> int:
    count = 0
    if not rawdata_root.exists():
        return count

    for path in sorted(rawdata_root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue

        relative = path.relative_to(rawdata_root).as_posix()
        evidence_id = insert_evidence(
            connection,
            release_id,
            source_kind="raw_json",
            source_path=relative,
            extractor="catalog.rawdata",
            confidence="explicit",
        )

        if isinstance(payload, dict):
            records: Iterable[tuple[str | None, Any]] = payload.items()
        else:
            records = [(None, payload)]

        for key, value in records:
            connection.execute(
                """
                INSERT INTO raw_records(
                    release_id, source_path, record_key, json_path,
                    payload_json, evidence_id
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    release_id,
                    relative,
                    key,
                    None if key is None else f'$["{key}"]',
                    json.dumps(value, sort_keys=True, ensure_ascii=False),
                    evidence_id,
                ),
            )
            count += 1

            if not isinstance(key, str):
                continue
            entity_type = infer_entity_type(key, relative)
            display_name = None
            if isinstance(value, dict):
                for name_key in ("name", "displayName", "display_name", "title"):
                    candidate = value.get(name_key)
                    if isinstance(candidate, str) and candidate:
                        display_name = candidate
                        break

            entity_id = upsert_entity(
                connection,
                release_id,
                internal_id=key,
                entity_type=entity_type,
                display_name=display_name,
                source_asset=relative,
            )
            connection.execute(
                "INSERT OR IGNORE INTO entity_evidence(entity_id, evidence_id) VALUES(?, ?)",
                (entity_id, evidence_id),
            )
            if isinstance(value, dict):
                for attr_name, attr_value in value.items():
                    if isinstance(attr_value, (str, int, float, bool)) or attr_value is None:
                        insert_attribute(
                            connection,
                            entity_id,
                            f"raw.{attr_name}",
                            attr_value,
                            evidence_id=evidence_id,
                        )

    return count


def _entity_component_fields(
    analysis: sqlite3.Connection,
    *,
    analyzer_game_object_id: int,
    archive_name: str,
    serialized_name: str,
    unity_tool: Path,
    bundle_paths: dict[str, Path],
    cache_root: Path,
) -> list[tuple[int, dict[str, Any], str]]:
    bundle_path = bundle_paths.get(archive_name)
    if bundle_path is None:
        return []
    serialized_file = _serialized_file_from_bundle(
        unity_tool,
        bundle_path,
        serialized_name,
        cache_root,
    )
    if serialized_file is None:
        return []

    rows = analysis.execute(
        """
        SELECT object_id, type
        FROM object_view
        WHERE game_object = ? AND type = 'MonoBehaviour'
        ORDER BY object_id
        """,
        (analyzer_game_object_id,),
    ).fetchall()

    output: list[tuple[int, dict[str, Any], str]] = []
    for row in rows:
        text = _dump_component(unity_tool, serialized_file, int(row["object_id"]))
        if text is None:
            continue
        output.append((int(row["object_id"]), parse_unity_dump(text), text))
    return output


def _find_primary_item_fields(
    component_fields: list[tuple[int, dict[str, Any], str]],
) -> tuple[int, dict[str, Any], str] | None:
    for item in component_fields:
        _, fields, _ = item
        if _first_by_leaf(fields, "rarity") is not None and (
            _first_by_leaf(fields, "excludeFromPool") is not None
            or _first_by_leaf(fields, "tags") is not None
        ):
            return item
    return None


def _pool(
    connection: sqlite3.Connection,
    release_id: int,
    family: str,
    rarity: str,
) -> int:
    key = f"{family}:{rarity}"
    connection.execute(
        """
        INSERT INTO pools(
            release_id, pool_key, family, rarity_name, context_kind, description
        ) VALUES(?, ?, ?, ?, 'content_eligible', ?)
        ON CONFLICT(release_id, pool_key, context_kind) DO NOTHING
        """,
        (
            release_id,
            key,
            family,
            rarity,
            f"Serialized pool-eligible {family} content of rarity {rarity}. "
            "Runtime pools are further constrained by player unlock state and bans.",
        ),
    )
    row = connection.execute(
        """
        SELECT id FROM pools
        WHERE release_id = ? AND pool_key = ? AND context_kind = 'content_eligible'
        """,
        (release_id, key),
    ).fetchone()
    assert row is not None
    return int(row[0])


def _method_id(connection: sqlite3.Connection, key: str) -> int:
    row = connection.execute(
        "SELECT id FROM acquisition_methods WHERE method_key = ?",
        (key,),
    ).fetchone()
    assert row is not None
    return int(row[0])


def _add_rules_for_item(
    connection: sqlite3.Connection,
    release_id: int,
    entity_id: int,
    entity_type: str,
    rarity: str,
    pool_id: int | None,
    evidence_id: int | None,
) -> None:
    if entity_type == "skill":
        normal = normal_loot_formula("skill", rarity)
        for rarity_context in ("normal", "high"):
            connection.execute(
                """
                INSERT INTO acquisition_rules(
                    release_id, entity_id, entity_type, method_id, context_key,
                    probability_kind, probability_value, formula_text,
                    denominator_pool_id, notes, evidence_id
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    release_id,
                    entity_id,
                    entity_type,
                    _method_id(connection, "normal_skill_loot"),
                    rarity_context,
                    normal.probability_kind,
                    normal.probability_value,
                    normal.formula_text,
                    pool_id if normal.probability_kind != "zero" else None,
                    "Pool size shown by the canonical database is the all-content eligible pool; "
                    "actual runtime pool is the union of players' unlockedGameItems minus bans.",
                    evidence_id,
                ),
            )

        ascension = ascension_skill_formula(rarity)
        source = ascension_input_rarity(rarity)
        connection.execute(
            """
            INSERT INTO acquisition_rules(
                release_id, entity_id, entity_type, method_id, context_key,
                source_condition, probability_kind, probability_value,
                formula_text, denominator_pool_id, notes, evidence_id
            ) VALUES(?, ?, ?, ?, 'runtime', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                release_id,
                entity_id,
                entity_type,
                _method_id(connection, "ascension_skill"),
                None if source is None else f"ascend {source} memory",
                ascension.probability_kind,
                ascension.probability_value,
                ascension.formula_text,
                pool_id,
                "Uniform Random.Range selection within the next-rarity runtime skill pool.",
                evidence_id,
            ),
        )

        for method_key in ("pickup_discovery", "dismantle_discovery"):
            connection.execute(
                """
                INSERT INTO acquisition_rules(
                    release_id, entity_id, entity_type, method_id, context_key,
                    probability_kind, formula_text, notes, evidence_id
                ) VALUES(?, ?, ?, ?, 'profile', 'event', ?, ?, ?)
                """,
                (
                    release_id,
                    entity_id,
                    entity_type,
                    _method_id(connection, method_key),
                    "Discovery event, not a random drop probability.",
                    "Transitions NotDiscovered to Complete when this event occurs.",
                    evidence_id,
                ),
            )

    elif entity_type == "gem":
        normal = normal_loot_formula("gem", rarity)
        for rarity_context in ("normal", "high"):
            connection.execute(
                """
                INSERT INTO acquisition_rules(
                    release_id, entity_id, entity_type, method_id, context_key,
                    probability_kind, probability_value, formula_text,
                    denominator_pool_id, notes, evidence_id
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    release_id,
                    entity_id,
                    entity_type,
                    _method_id(connection, "normal_gem_loot"),
                    rarity_context,
                    normal.probability_kind,
                    normal.probability_value,
                    normal.formula_text,
                    pool_id if normal.probability_kind != "zero" else None,
                    "Pool size shown by the canonical database is the all-content eligible pool; "
                    "actual runtime pool is the union of players' unlockedGameItems minus bans.",
                    evidence_id,
                ),
            )

        ascension = ascension_gem_formula(rarity)
        source = ascension_input_rarity(rarity)
        connection.execute(
            """
            INSERT INTO acquisition_rules(
                release_id, entity_id, entity_type, method_id, context_key,
                source_condition, probability_kind, formula_text,
                denominator_pool_id, notes, evidence_id
            ) VALUES(?, ?, ?, ?, 'runtime', ?, ?, ?, ?, ?, ?)
            """,
            (
                release_id,
                entity_id,
                entity_type,
                _method_id(connection, "ascension_gem"),
                None if source is None else f"ascend {source} essence",
                ascension.probability_kind,
                ascension.formula_text,
                pool_id,
                "Owned gem types receive weight 0, so the denominator is hero-state dependent.",
                evidence_id,
            ),
        )


def _extract_loot_manager_weights(
    connection: sqlite3.Connection,
    release_id: int,
    analysis: sqlite3.Connection,
    unity_tool: Path,
    bundle_paths: dict[str, Path],
    cache_root: Path,
) -> int:
    rows = analysis.execute(
        """
        SELECT id, object_id, archive, serialized_file, name
        FROM object_view
        WHERE type = 'GameObject' AND name = 'LootManager'
        ORDER BY id
        """
    ).fetchall()

    inserted = 0
    for row in rows:
        archive = row["archive"]
        if not archive:
            continue
        components = _entity_component_fields(
            analysis,
            analyzer_game_object_id=int(row["id"]),
            archive_name=str(archive),
            serialized_name=str(row["serialized_file"]),
            unity_tool=unity_tool,
            bundle_paths=bundle_paths,
            cache_root=cache_root,
        )
        for object_id, fields, _ in components:
            relevant = {
                path: value
                for path, value in fields.items()
                if "skillRarityChance" in path or "gemRarityChance" in path
            }
            if not relevant:
                continue
            evidence_id = insert_evidence(
                connection,
                release_id,
                source_kind="unity_serialized",
                source_path=str(archive),
                extractor="catalog.unitydatatool",
                location=f"{row['serialized_file']} object_id={object_id}",
                confidence="explicit",
                detail="LootManager serialized rarity chances",
            )
            for family, prefix in (
                ("skill", "skillRarityChance"),
                ("skill", "skillRarityChanceHigh"),
                ("gem", "gemRarityChance"),
                ("gem", "gemRarityChanceHigh"),
            ):
                context = "high" if prefix.endswith("High") else "normal"
                weights: dict[str, float] = {}
                for rarity in ("Rare", "Epic", "Legendary"):
                    leaf = rarity.lower()
                    value = None
                    for path, candidate in fields.items():
                        if prefix in path and path.endswith("." + leaf):
                            value = candidate
                            break
                    if isinstance(value, (int, float)):
                        weights[rarity] = float(value)

                if len(weights) == 3:
                    weights["Common"] = max(
                        0.0,
                        1.0 - weights["Rare"] - weights["Epic"] - weights["Legendary"],
                    )

                for rarity, value in weights.items():
                    connection.execute(
                        """
                        INSERT INTO rarity_weights(
                            release_id, family, context_key, rarity_name,
                            weight, formula_text, evidence_id
                        ) VALUES(?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(
                            release_id, family, context_key, rarity_name
                        ) DO UPDATE SET
                            weight = excluded.weight,
                            formula_text = excluded.formula_text,
                            evidence_id = excluded.evidence_id
                        """,
                        (
                            release_id,
                            family,
                            context,
                            rarity,
                            value,
                            (
                                "1 - legendary - epic - rare"
                                if rarity == "Common"
                                else None
                            ),
                            evidence_id,
                        ),
                    )
                    inserted += 1
    return inserted


def build_data_dictionary(
    *,
    analysis_db: Path,
    bundle_root: Path,
    rawdata_root: Path,
    unity_tool: Path,
    release: str,
    output: Path,
    source_root: Path | None = None,
    cache_root: Path | None = None,
) -> dict[str, int | str]:
    """Build a provenance-aware SQLite release dictionary."""
    analysis_db = analysis_db.resolve()
    bundle_root = bundle_root.resolve()
    rawdata_root = rawdata_root.resolve()
    unity_tool = unity_tool.resolve()
    output = output.resolve()
    cache_root = (
        cache_root.resolve()
        if cache_root
        else output.parent / f".{output.stem}-bundle-cache"
    )

    if cache_root.exists():
        shutil.rmtree(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)

    connection = create_database(output, replace=True)
    analysis = sqlite3.connect(analysis_db)
    analysis.row_factory = sqlite3.Row

    try:
        release_id = insert_release(
            connection,
            release,
            source_root=str(source_root.resolve()) if source_root else None,
        )
        raw_records = _insert_rawdata(connection, release_id, rawdata_root)
        bundle_paths = _bundle_index(bundle_root)

        all_unity_rows = analysis.execute(
            """
            SELECT id, object_id, archive, serialized_file, type, name, game_object, size
            FROM object_view
            ORDER BY id
            """
        ).fetchall()
        connection.executemany(
            """
            INSERT INTO unity_objects(
                release_id, analyzer_id, object_id, archive, serialized_file,
                unity_type, name, game_object_analyzer_id, size
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    release_id,
                    int(item["id"]),
                    int(item["object_id"]),
                    item["archive"],
                    str(item["serialized_file"]),
                    str(item["type"]),
                    item["name"],
                    None if item["game_object"] in (None, "") else int(item["game_object"]),
                    None if item["size"] is None else int(item["size"]),
                )
                for item in all_unity_rows
            ],
        )
        unity_object_count = len(all_unity_rows)

        rows = analysis.execute(
            """
            SELECT id, object_id, archive, serialized_file, name
            FROM object_view
            WHERE type = 'GameObject' AND name <> ''
            ORDER BY name, archive, serialized_file, object_id
            """
        ).fetchall()

        processed_item_ids: set[tuple[str, str]] = set()
        serialized_items = 0

        for row in rows:
            internal_id = str(row["name"])
            entity_type = infer_entity_type(internal_id)
            source_asset = (
                f"{row['archive']}::{row['serialized_file']}"
                if row["archive"]
                else str(row["serialized_file"])
            )
            entity_id = upsert_entity(
                connection,
                release_id,
                internal_id=internal_id,
                entity_type=entity_type,
                source_asset=source_asset,
            )

            if entity_type not in {"skill", "gem"}:
                continue

            key = (entity_type, internal_id)
            if key in processed_item_ids:
                continue

            archive = row["archive"]
            if not archive:
                continue
            components = _entity_component_fields(
                analysis,
                analyzer_game_object_id=int(row["id"]),
                archive_name=str(archive),
                serialized_name=str(row["serialized_file"]),
                unity_tool=unity_tool,
                bundle_paths=bundle_paths,
                cache_root=cache_root,
            )
            primary = _find_primary_item_fields(components)
            if primary is None:
                continue

            object_id, fields, _ = primary
            rarity_value = _first_by_leaf(fields, "rarity")
            exclude = _first_by_leaf(fields, "excludeFromPool")
            tags = _first_by_leaf(fields, "tags")
            if not isinstance(rarity_value, int):
                continue

            rarity = rarity_name(rarity_value)
            is_character = rarity == "Character"
            exclude_bool = bool(exclude) if isinstance(exclude, (bool, int)) else None

            evidence_id = insert_evidence(
                connection,
                release_id,
                source_kind="unity_serialized",
                source_path=str(archive),
                extractor="catalog.unitydatatool",
                location=f"{row['serialized_file']} object_id={object_id}",
                confidence="explicit",
                detail=f"Serialized {entity_type} component for {internal_id}",
            )
            entity_id = upsert_entity(
                connection,
                release_id,
                internal_id=internal_id,
                entity_type=entity_type,
                rarity_value=rarity_value,
                rarity_name=rarity,
                exclude_from_pool=exclude_bool,
                is_character_skill=is_character if entity_type == "skill" else None,
                source_asset=source_asset,
            )
            connection.execute(
                "INSERT OR IGNORE INTO entity_evidence(entity_id, evidence_id) VALUES(?, ?)",
                (entity_id, evidence_id),
            )

            insert_attribute(
                connection,
                entity_id,
                "rarity",
                rarity,
                evidence_id=evidence_id,
            )
            insert_attribute(
                connection,
                entity_id,
                "rarity_value",
                rarity_value,
                evidence_id=evidence_id,
            )
            if exclude_bool is not None:
                insert_attribute(
                    connection,
                    entity_id,
                    "excludeFromPool",
                    exclude_bool,
                    evidence_id=evidence_id,
                )
            if entity_type == "skill":
                insert_attribute(
                    connection,
                    entity_id,
                    "isCharacterSkill",
                    is_character,
                    evidence_id=evidence_id,
                )
            if tags is not None:
                insert_attribute(
                    connection,
                    entity_id,
                    "tags",
                    tags,
                    evidence_id=evidence_id,
                )

            pool_id = None
            pool_eligible = (
                exclude_bool is False
                and (entity_type != "skill" or not is_character)
                and rarity not in {None, "Identity"}
            )
            if pool_eligible:
                pool_id = _pool(connection, release_id, entity_type, str(rarity))
                connection.execute(
                    """
                    INSERT OR IGNORE INTO pool_members(
                        pool_id, entity_id, eligibility, evidence_id
                    ) VALUES(?, ?, 'serialized_eligible', ?)
                    """,
                    (pool_id, entity_id, evidence_id),
                )

            _add_rules_for_item(
                connection,
                release_id,
                entity_id,
                entity_type,
                str(rarity),
                pool_id,
                evidence_id,
            )
            processed_item_ids.add(key)
            serialized_items += 1

        rarity_weights = _extract_loot_manager_weights(
            connection,
            release_id,
            analysis,
            unity_tool,
            bundle_paths,
            cache_root,
        )

        connection.commit()

        entity_count = connection.execute(
            "SELECT COUNT(*) FROM entities WHERE release_id = ?",
            (release_id,),
        ).fetchone()[0]
        pool_member_count = connection.execute(
            """
            SELECT COUNT(*) FROM pool_members pm
            JOIN pools p ON p.id = pm.pool_id
            WHERE p.release_id = ?
            """,
            (release_id,),
        ).fetchone()[0]
        rule_count = connection.execute(
            "SELECT COUNT(*) FROM acquisition_rules WHERE release_id = ?",
            (release_id,),
        ).fetchone()[0]

        return {
            "output": str(output),
            "entities": int(entity_count),
            "unity_objects": int(unity_object_count),
            "raw_records": int(raw_records),
            "serialized_items": int(serialized_items),
            "pool_members": int(pool_member_count),
            "acquisition_rules": int(rule_count),
            "rarity_weights": int(rarity_weights),
        }
    finally:
        analysis.close()
        connection.close()
