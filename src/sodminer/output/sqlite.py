"""SQLite storage foundation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    entity_type TEXT NOT NULL,
    internal_id TEXT,
    display_name TEXT,
    attributes_json TEXT NOT NULL,
    PRIMARY KEY (entity_type, internal_id)
);
CREATE TABLE IF NOT EXISTS relationships (
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    confidence TEXT NOT NULL,
    PRIMARY KEY (source_type, source_id, relation, target_type, target_id)
);
CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT,
    entity_id TEXT,
    source_file TEXT NOT NULL,
    release TEXT NOT NULL,
    extractor TEXT NOT NULL,
    confidence TEXT NOT NULL,
    detail TEXT,
    location TEXT
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    return connection
