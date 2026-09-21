"""Core normalized data structures."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Confidence = Literal["explicit", "inferred", "unknown"]


@dataclass
class Evidence:
    source_file: str
    release: str
    extractor: str
    confidence: Confidence = "unknown"
    detail: str | None = None
    location: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Entity:
    entity_type: str
    internal_id: str | None = None
    display_name: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "internal_id": self.internal_id,
            "display_name": self.display_name,
            "attributes": self.attributes,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass
class Relationship:
    source_type: str
    source_id: str
    relation: str
    target_type: str
    target_id: str
    confidence: Confidence = "unknown"
    evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "relation": self.relation,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "confidence": self.confidence,
            "evidence": [item.to_dict() for item in self.evidence],
        }
