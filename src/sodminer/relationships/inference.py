"""Evidence-aware relationship inference."""

from __future__ import annotations

from ..models import Evidence, Relationship


def inferred_relationship(source_type: str, source_id: str, relation: str, target_type: str, target_id: str, evidence: list[Evidence]) -> Relationship:
    return Relationship(source_type=source_type, source_id=source_id, relation=relation, target_type=target_type, target_id=target_id, confidence="inferred", evidence=evidence)
