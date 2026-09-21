"""Resolve extracted references into relationships."""

from __future__ import annotations

from collections.abc import Iterable

from ..models import Relationship


def deduplicate_relationships(relationships: Iterable[Relationship]) -> list[Relationship]:
    result: list[Relationship] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for relationship in relationships:
        key = (relationship.source_type, relationship.source_id, relationship.relation, relationship.target_type, relationship.target_id)
        if key not in seen:
            seen.add(key)
            result.append(relationship)
    return result
