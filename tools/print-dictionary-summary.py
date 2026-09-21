from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def pct(value: float | None) -> str:
    if value is None:
        return "<formula/context dependent>"
    return f"{value * 100:.6f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    args = parser.parse_args()

    db = sqlite3.connect(args.database)
    db.row_factory = sqlite3.Row
    try:
        release = db.execute(
            "SELECT release_key FROM releases ORDER BY id LIMIT 1"
        ).fetchone()
        print("=== Shape of Dreams data dictionary ===")
        print(f"Database: {args.database.resolve()}")
        print(f"Release: {release['release_key'] if release else '<unknown>'}")
        print()

        unity_count = db.execute("SELECT COUNT(*) FROM unity_objects").fetchone()[0]
        raw_count = db.execute("SELECT COUNT(*) FROM raw_records").fetchone()[0]
        entity_count = db.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        rule_count = db.execute("SELECT COUNT(*) FROM acquisition_rules").fetchone()[0]
        print(f"Unity objects: {unity_count}")
        print(f"Raw JSON records: {raw_count}")
        print(f"Normalized entities: {entity_count}")
        print(f"Acquisition/drop rules: {rule_count}")
        print()

        print("=== Normalized entities by type ===")
        for row in db.execute(
            """
            SELECT entity_type, COUNT(*) AS count
            FROM entities
            GROUP BY entity_type
            ORDER BY count DESC, entity_type
            """
        ):
            print(f"{row['entity_type']}: {row['count']}")
        print()

        print("=== Content-eligible pool sizes ===")
        for row in db.execute(
            """
            SELECT family, rarity_name, member_count
            FROM v_pool_sizes
            ORDER BY family,
                CASE rarity_name
                    WHEN 'Common' THEN 0
                    WHEN 'Rare' THEN 1
                    WHEN 'Epic' THEN 2
                    WHEN 'Legendary' THEN 3
                    WHEN 'Character' THEN 4
                    WHEN 'Identity' THEN 5
                    WHEN 'Unique' THEN 10
                    ELSE 99
                END
            """
        ):
            print(f"{row['family']} {row['rarity_name']}: {row['member_count']}")
        print()

        print("=== Serialized rarity weights ===")
        weights = list(
            db.execute(
                """
                SELECT family, context_key, rarity_name, weight, formula_text
                FROM rarity_weights
                ORDER BY family, context_key,
                    CASE rarity_name
                        WHEN 'Common' THEN 0
                        WHEN 'Rare' THEN 1
                        WHEN 'Epic' THEN 2
                        WHEN 'Legendary' THEN 3
                        ELSE 99
                    END
                """
            )
        )
        if not weights:
            print("<LootManager rarity weights not yet recovered from analyzed bundles>")
        else:
            for row in weights:
                suffix = f" [{row['formula_text']}]" if row["formula_text"] else ""
                print(
                    f"{row['family']} {row['context_key']} {row['rarity_name']}: "
                    f"{row['weight']:.8f}{suffix}"
                )
        print()

        print("=== Big Chomp acquisition/drop rows ===")
        rows = list(
            db.execute(
                """
                SELECT method_key, context_key, source_condition,
                       probability_kind, formula_text,
                       denominator_pool, denominator_count,
                       rarity_weight, resolved_probability,
                       denominator_context
                FROM v_acquisition_dictionary
                WHERE internal_id = 'St_U_BigChomp'
                ORDER BY method_key, context_key
                """
            )
        )
        if not rows:
            print("<St_U_BigChomp not present in normalized dictionary>")
        else:
            for row in rows:
                print(
                    f"{row['method_key']} [{row['context_key']}]: "
                    f"{pct(row['resolved_probability'])}"
                )
                if row["source_condition"]:
                    print(f"  condition: {row['source_condition']}")
                if row["denominator_pool"]:
                    print(
                        f"  pool: {row['denominator_pool']} "
                        f"(content-eligible count={row['denominator_count']}, "
                        f"context={row['denominator_context']})"
                    )
                if row["rarity_weight"] is not None:
                    print(f"  rarity weight: {row['rarity_weight']:.8f}")
                if row["formula_text"]:
                    print(f"  formula: {row['formula_text']}")
        print()

        print("NOTE: content-eligible pool counts are static release facts.")
        print(
            "Actual runtime pools can be smaller because they are the union of "
            "players' available/unlocked items minus lobby bans."
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
