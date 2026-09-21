"""Relationship graph primitives."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Relationship


@dataclass
class RelationshipGraph:
    relationships: list[Relationship] = field(default_factory=list)

    def add(self, relationship: Relationship) -> None:
        if relationship not in self.relationships:
            self.relationships.append(relationship)

    def outgoing(self, source_type: str, source_id: str) -> list[Relationship]:
        return [r for r in self.relationships if r.source_type == source_type and r.source_id == source_id]

    def incoming(self, target_type: str, target_id: str) -> list[Relationship]:
        return [r for r in self.relationships if r.target_type == target_type and r.target_id == target_id]
