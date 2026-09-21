"""Context-aware runtime probability calculations.

The release database contains immutable game facts. Player/party/run context is
supplied separately so a desktop GUI and a website can share the same odds engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import sqlite3
from typing import Iterable


@dataclass(frozen=True)
class PlayerPoolContext:
    """Items a participating player contributes to LootManager.unlockedGameItems."""

    label: str
    available_items: frozenset[str]


@dataclass(frozen=True)
class RateContext:
    """Runtime values known to affect currently traced acquisition mechanics."""

    players: tuple[PlayerPoolContext, ...] = ()
    banned_items: frozenset[str] = frozenset()
    hero_owned_gems: frozenset[str] = frozenset()
    rarity_context: str = "normal"


@dataclass(frozen=True)
class OddsResult:
    internal_id: str
    method_key: str
    probability: float | None
    numerator_weight: float | None
    denominator_count: int | None
    eligible: bool
    formula: str
    notes: tuple[str, ...] = ()


def _entity(
    db: sqlite3.Connection, internal_id: str
) -> sqlite3.Row | None:
    return db.execute(
        """
        SELECT *
        FROM v_entity_dictionary
        WHERE internal_id = ?
        ORDER BY id
        LIMIT 1
        """,
        (internal_id,),
    ).fetchone()


def _content_pool_ids(
    db: sqlite3.Connection,
    *,
    family: str,
    rarity_name: str,
) -> set[str]:
    rows = db.execute(
        """
        SELECT e.internal_id
        FROM pools p
        JOIN pool_members pm ON pm.pool_id = p.id
        JOIN entities e ON e.id = pm.entity_id
        WHERE p.family = ?
          AND p.rarity_name = ?
          AND p.context_kind = 'content_eligible'
        """,
        (family, rarity_name),
    )
    return {str(row[0]) for row in rows}


def runtime_pool_ids(
    db: sqlite3.Connection,
    *,
    family: str,
    rarity_name: str,
    context: RateContext,
) -> set[str]:
    """Resolve the runtime pool from content eligibility + party contributions + bans."""

    content = _content_pool_ids(
        db,
        family=family,
        rarity_name=rarity_name,
    )

    if context.players:
        contributed: set[str] = set()
        for player in context.players:
            contributed.update(player.available_items)
        content.intersection_update(contributed)

    content.difference_update(context.banned_items)
    return content


def _rarity_weight(
    db: sqlite3.Connection,
    *,
    family: str,
    rarity_name: str,
    context_key: str,
) -> float | None:
    row = db.execute(
        """
        SELECT weight
        FROM rarity_weights
        WHERE family = ?
          AND rarity_name = ?
          AND context_key = ?
        ORDER BY id
        LIMIT 1
        """,
        (family, rarity_name, context_key),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    return float(row[0])


def calculate_normal_loot_odds(
    db: sqlite3.Connection,
    *,
    internal_id: str,
    context: RateContext,
) -> OddsResult:
    entity = _entity(db, internal_id)
    if entity is None:
        return OddsResult(
            internal_id=internal_id,
            method_key="normal_loot",
            probability=None,
            numerator_weight=None,
            denominator_count=None,
            eligible=False,
            formula="unknown entity",
        )

    family = str(entity["entity_type"])
    rarity = entity["rarity_name"]
    if family not in {"skill", "gem"} or rarity is None:
        return OddsResult(
            internal_id=internal_id,
            method_key="normal_loot",
            probability=None,
            numerator_weight=None,
            denominator_count=None,
            eligible=False,
            formula="normal loot model only applies to skill/gem entities with known rarity",
        )

    if rarity in {"Unique", "Character", "Identity"}:
        return OddsResult(
            internal_id=internal_id,
            method_key=f"normal_{family}_loot",
            probability=0.0,
            numerator_weight=0.0,
            denominator_count=None,
            eligible=False,
            formula=f"0 — normal rarity selection never returns {rarity}",
        )

    pool = runtime_pool_ids(
        db,
        family=family,
        rarity_name=str(rarity),
        context=context,
    )
    if internal_id not in pool:
        return OddsResult(
            internal_id=internal_id,
            method_key=f"normal_{family}_loot",
            probability=0.0,
            numerator_weight=0.0,
            denominator_count=len(pool),
            eligible=False,
            formula="0 — item is not in the resolved runtime pool",
        )

    weight = _rarity_weight(
        db,
        family=family,
        rarity_name=str(rarity),
        context_key=context.rarity_context,
    )
    probability = None if weight is None or not pool else weight / len(pool)
    return OddsResult(
        internal_id=internal_id,
        method_key=f"normal_{family}_loot",
        probability=probability,
        numerator_weight=weight,
        denominator_count=len(pool),
        eligible=True,
        formula=(
            f"P({rarity} | {context.rarity_context}) / "
            f"N_runtime_{family}_{rarity}"
        ),
        notes=(
            "Runtime pool is the union of participating players' available items minus bans.",
        ),
    )


def calculate_ascension_skill_odds(
    db: sqlite3.Connection,
    *,
    internal_id: str,
    context: RateContext,
) -> OddsResult:
    entity = _entity(db, internal_id)
    if entity is None or entity["entity_type"] != "skill":
        return OddsResult(
            internal_id=internal_id,
            method_key="ascension_skill",
            probability=None,
            numerator_weight=None,
            denominator_count=None,
            eligible=False,
            formula="Ascension skill model requires a known skill entity",
        )

    rarity = str(entity["rarity_name"])
    pool = runtime_pool_ids(
        db,
        family="skill",
        rarity_name=rarity,
        context=context,
    )
    eligible = internal_id in pool
    probability = (1.0 / len(pool)) if eligible and pool else 0.0
    return OddsResult(
        internal_id=internal_id,
        method_key="ascension_skill",
        probability=probability,
        numerator_weight=1.0 if eligible else 0.0,
        denominator_count=len(pool),
        eligible=eligible,
        formula=f"1 / N_runtime_skill_{rarity}" if eligible else "0 — item not in runtime pool",
        notes=(
            "The caller must also supply an input memory whose next rarity is the target rarity.",
        ),
    )


def calculate_ascension_gem_odds(
    db: sqlite3.Connection,
    *,
    internal_id: str,
    context: RateContext,
) -> OddsResult:
    entity = _entity(db, internal_id)
    if entity is None or entity["entity_type"] != "gem":
        return OddsResult(
            internal_id=internal_id,
            method_key="ascension_gem",
            probability=None,
            numerator_weight=None,
            denominator_count=None,
            eligible=False,
            formula="Ascension gem model requires a known gem entity",
        )

    rarity = str(entity["rarity_name"])
    pool = runtime_pool_ids(
        db,
        family="gem",
        rarity_name=rarity,
        context=context,
    )
    pool.difference_update(context.hero_owned_gems)

    eligible = internal_id in pool
    probability = (1.0 / len(pool)) if eligible and pool else 0.0
    return OddsResult(
        internal_id=internal_id,
        method_key="ascension_gem",
        probability=probability,
        numerator_weight=1.0 if eligible else 0.0,
        denominator_count=len(pool),
        eligible=eligible,
        formula=f"1 / N_runtime_unowned_gem_{rarity}" if eligible else "0 — gem excluded/owned",
        notes=(
            "Owned gem types receive zero selection weight in the traced Ascension path.",
        ),
    )
