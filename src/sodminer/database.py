"""SQLite data dictionary schema and helpers."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

SCHEMA_SQL = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE releases (
    id INTEGER PRIMARY KEY,
    release_key TEXT NOT NULL UNIQUE,
    unity_version TEXT,
    source_root TEXT,
    created_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evidence (
    id INTEGER PRIMARY KEY,
    release_id INTEGER NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    source_path TEXT NOT NULL,
    extractor TEXT NOT NULL,
    location TEXT,
    confidence TEXT NOT NULL CHECK(confidence IN ('explicit', 'inferred', 'unknown')),
    detail TEXT,
    sha256 TEXT
);

CREATE TABLE entities (
    id INTEGER PRIMARY KEY,
    release_id INTEGER NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    internal_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    display_name TEXT,
    rarity_value INTEGER,
    rarity_name TEXT,
    include_in_game INTEGER CHECK(include_in_game IN (0, 1) OR include_in_game IS NULL),
    exclude_from_pool INTEGER CHECK(exclude_from_pool IN (0, 1) OR exclude_from_pool IS NULL),
    is_character_skill INTEGER CHECK(is_character_skill IN (0, 1) OR is_character_skill IS NULL),
    source_asset TEXT,
    UNIQUE(release_id, entity_type, internal_id)
);

CREATE INDEX idx_entities_internal_id ON entities(release_id, internal_id);
CREATE INDEX idx_entities_type_rarity ON entities(release_id, entity_type, rarity_name);

CREATE TABLE entity_evidence (
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    evidence_id INTEGER NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    PRIMARY KEY(entity_id, evidence_id)
);

CREATE TABLE entity_attributes (
    id INTEGER PRIMARY KEY,
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    attribute_name TEXT NOT NULL,
    value_text TEXT,
    value_num REAL,
    value_bool INTEGER CHECK(value_bool IN (0, 1) OR value_bool IS NULL),
    value_json TEXT,
    confidence TEXT NOT NULL CHECK(confidence IN ('explicit', 'inferred', 'unknown')),
    evidence_id INTEGER REFERENCES evidence(id) ON DELETE SET NULL
);

CREATE INDEX idx_entity_attributes_name ON entity_attributes(attribute_name);

CREATE TABLE relationships (
    id INTEGER PRIMARY KEY,
    release_id INTEGER NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    source_entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation TEXT NOT NULL,
    target_entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    target_external_id TEXT,
    confidence TEXT NOT NULL CHECK(confidence IN ('explicit', 'inferred', 'unknown')),
    evidence_id INTEGER REFERENCES evidence(id) ON DELETE SET NULL,
    CHECK(target_entity_id IS NOT NULL OR target_external_id IS NOT NULL)
);

CREATE TABLE raw_records (
    id INTEGER PRIMARY KEY,
    release_id INTEGER NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    source_path TEXT NOT NULL,
    record_key TEXT,
    json_path TEXT,
    payload_json TEXT NOT NULL,
    evidence_id INTEGER REFERENCES evidence(id) ON DELETE SET NULL
);

CREATE TABLE pools (
    id INTEGER PRIMARY KEY,
    release_id INTEGER NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    pool_key TEXT NOT NULL,
    family TEXT NOT NULL,
    rarity_name TEXT,
    context_kind TEXT NOT NULL DEFAULT 'canonical',
    description TEXT,
    UNIQUE(release_id, pool_key, context_kind)
);

CREATE TABLE pool_members (
    pool_id INTEGER NOT NULL REFERENCES pools(id) ON DELETE CASCADE,
    entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    eligibility TEXT NOT NULL DEFAULT 'eligible',
    evidence_id INTEGER REFERENCES evidence(id) ON DELETE SET NULL,
    PRIMARY KEY(pool_id, entity_id)
);

CREATE TABLE rarity_weights (
    id INTEGER PRIMARY KEY,
    release_id INTEGER NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    family TEXT NOT NULL,
    context_key TEXT NOT NULL,
    rarity_name TEXT NOT NULL,
    weight REAL,
    formula_text TEXT,
    evidence_id INTEGER REFERENCES evidence(id) ON DELETE SET NULL,
    UNIQUE(release_id, family, context_key, rarity_name)
);

CREATE TABLE acquisition_methods (
    id INTEGER PRIMARY KEY,
    method_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    family TEXT,
    selection_model TEXT NOT NULL,
    description TEXT
);

CREATE TABLE acquisition_rules (
    id INTEGER PRIMARY KEY,
    release_id INTEGER NOT NULL REFERENCES releases(id) ON DELETE CASCADE,
    entity_id INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    entity_type TEXT,
    method_id INTEGER NOT NULL REFERENCES acquisition_methods(id) ON DELETE CASCADE,
    context_key TEXT NOT NULL DEFAULT 'canonical',
    source_condition TEXT,
    probability_kind TEXT NOT NULL,
    probability_value REAL,
    formula_text TEXT,
    denominator_pool_id INTEGER REFERENCES pools(id) ON DELETE SET NULL,
    notes TEXT,
    evidence_id INTEGER REFERENCES evidence(id) ON DELETE SET NULL
);

CREATE INDEX idx_acquisition_rules_entity ON acquisition_rules(entity_id);
CREATE INDEX idx_acquisition_rules_method ON acquisition_rules(method_id);

CREATE VIEW v_pool_sizes AS
SELECT
    p.id AS pool_id,
    p.release_id,
    p.pool_key,
    p.family,
    p.rarity_name,
    p.context_kind,
    COUNT(pm.entity_id) AS member_count
FROM pools p
LEFT JOIN pool_members pm ON pm.pool_id = p.id
GROUP BY p.id;

CREATE VIEW v_entity_dictionary AS
SELECT
    e.id,
    r.release_key,
    e.entity_type,
    e.internal_id,
    e.display_name,
    e.rarity_value,
    e.rarity_name,
    e.include_in_game,
    e.exclude_from_pool,
    e.is_character_skill,
    e.source_asset
FROM entities e
JOIN releases r ON r.id = e.release_id;

CREATE VIEW v_acquisition_dictionary AS
SELECT
    r.release_key,
    e.entity_type,
    e.internal_id,
    e.display_name,
    m.method_key,
    m.display_name AS method_name,
    m.selection_model,
    ar.context_key,
    ar.source_condition,
    ar.probability_kind,
    ar.probability_value,
    ar.formula_text,
    p.pool_key AS denominator_pool,
    ps.member_count AS denominator_count,
    CASE
        WHEN ar.probability_kind = 'uniform_pool'
             AND ps.member_count > 0
        THEN 1.0 / ps.member_count
        ELSE ar.probability_value
    END AS resolved_probability,
    ar.notes
FROM acquisition_rules ar
JOIN releases r ON r.id = ar.release_id
LEFT JOIN entities e ON e.id = ar.entity_id
JOIN acquisition_methods m ON m.id = ar.method_id
LEFT JOIN pools p ON p.id = ar.denominator_pool_id
LEFT JOIN v_pool_sizes ps ON ps.pool_id = ar.denominator_pool_id;
"""


ACQUISITION_METHODS = [
    (
        "normal_skill_loot",
        "Normal memory loot roll",
        "skill",
        "rarity_then_uniform_pool",
        "Roll skill rarity, then choose uniformly from the eligible skill pool for that rarity.",
    ),
    (
        "normal_gem_loot",
        "Normal essence loot roll",
        "gem",
        "rarity_then_uniform_pool",
        "Roll gem rarity, then choose uniformly from the eligible gem pool for that rarity.",
    ),
    (
        "ascension_skill",
        "Shrine of Ascension — memory",
        "skill",
        "next_rarity_uniform_pool",
        "Map current rarity to next rarity, then choose uniformly from that skill rarity pool.",
    ),
    (
        "ascension_gem",
        "Shrine of Ascension — essence",
        "gem",
        "next_rarity_weighted_not_owned",
        "Map current rarity to next rarity, then choose among eligible gems not already owned by the hero.",
    ),
    (
        "pickup_discovery",
        "Memory pickup discovery",
        "skill",
        "event",
        "Picking up a memory permanently discovers it for the local profile.",
    ),
    (
        "dismantle_discovery",
        "Memory dismantle discovery",
        "skill",
        "event",
        "Dismantling a memory permanently discovers it for the local profile.",
    ),
]


def connect_database(path: Path) -> sqlite3.Connection:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_database(path: Path, *, replace: bool = True) -> sqlite3.Connection:
    path = path.expanduser().resolve()
    if replace and path.exists():
        path.unlink()
    connection = connect_database(path)
    connection.executescript(SCHEMA_SQL)
    connection.execute(
        "INSERT INTO metadata(key, value) VALUES('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    connection.executemany(
        """
        INSERT INTO acquisition_methods(
            method_key, display_name, family, selection_model, description
        ) VALUES(?, ?, ?, ?, ?)
        """,
        ACQUISITION_METHODS,
    )
    connection.commit()
    return connection


def insert_release(
    connection: sqlite3.Connection,
    release_key: str,
    *,
    unity_version: str | None = None,
    source_root: str | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO releases(release_key, unity_version, source_root)
        VALUES(?, ?, ?)
        ON CONFLICT(release_key) DO UPDATE SET
            unity_version = COALESCE(excluded.unity_version, releases.unity_version),
            source_root = COALESCE(excluded.source_root, releases.source_root)
        RETURNING id
        """,
        (release_key, unity_version, source_root),
    )
    row = cursor.fetchone()
    assert row is not None
    return int(row[0])


def insert_evidence(
    connection: sqlite3.Connection,
    release_id: int,
    *,
    source_kind: str,
    source_path: str,
    extractor: str,
    confidence: str = "explicit",
    location: str | None = None,
    detail: str | None = None,
    sha256: str | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO evidence(
            release_id, source_kind, source_path, extractor,
            location, confidence, detail, sha256
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            release_id,
            source_kind,
            source_path,
            extractor,
            location,
            confidence,
            detail,
            sha256,
        ),
    )
    return int(cursor.lastrowid)


def upsert_entity(
    connection: sqlite3.Connection,
    release_id: int,
    *,
    internal_id: str,
    entity_type: str,
    display_name: str | None = None,
    rarity_value: int | None = None,
    rarity_name: str | None = None,
    include_in_game: bool | None = None,
    exclude_from_pool: bool | None = None,
    is_character_skill: bool | None = None,
    source_asset: str | None = None,
) -> int:
    connection.execute(
        """
        INSERT INTO entities(
            release_id, internal_id, entity_type, display_name,
            rarity_value, rarity_name, include_in_game,
            exclude_from_pool, is_character_skill, source_asset
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(release_id, entity_type, internal_id) DO UPDATE SET
            display_name = COALESCE(excluded.display_name, entities.display_name),
            rarity_value = COALESCE(excluded.rarity_value, entities.rarity_value),
            rarity_name = COALESCE(excluded.rarity_name, entities.rarity_name),
            include_in_game = COALESCE(excluded.include_in_game, entities.include_in_game),
            exclude_from_pool = COALESCE(excluded.exclude_from_pool, entities.exclude_from_pool),
            is_character_skill = COALESCE(excluded.is_character_skill, entities.is_character_skill),
            source_asset = COALESCE(excluded.source_asset, entities.source_asset)
        """,
        (
            release_id,
            internal_id,
            entity_type,
            display_name,
            rarity_value,
            rarity_name,
            None if include_in_game is None else int(include_in_game),
            None if exclude_from_pool is None else int(exclude_from_pool),
            None if is_character_skill is None else int(is_character_skill),
            source_asset,
        ),
    )
    row = connection.execute(
        """
        SELECT id FROM entities
        WHERE release_id = ? AND entity_type = ? AND internal_id = ?
        """,
        (release_id, entity_type, internal_id),
    ).fetchone()
    assert row is not None
    return int(row[0])


def insert_attribute(
    connection: sqlite3.Connection,
    entity_id: int,
    name: str,
    value: Any,
    *,
    confidence: str = "explicit",
    evidence_id: int | None = None,
) -> int:
    value_text = value_num = value_bool = value_json = None
    if isinstance(value, bool):
        value_bool = int(value)
        value_text = "true" if value else "false"
    elif isinstance(value, (int, float)):
        value_num = float(value)
        value_text = str(value)
    elif isinstance(value, str):
        value_text = value
    else:
        value_json = json.dumps(value, sort_keys=True, ensure_ascii=False)
    cursor = connection.execute(
        """
        INSERT INTO entity_attributes(
            entity_id, attribute_name, value_text, value_num,
            value_bool, value_json, confidence, evidence_id
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entity_id,
            name,
            value_text,
            value_num,
            value_bool,
            value_json,
            confidence,
            evidence_id,
        ),
    )
    return int(cursor.lastrowid)
