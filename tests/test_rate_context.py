from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sodminer.database import create_database, insert_release, upsert_entity
from sodminer.rate_context import (
    PlayerPoolContext,
    RateContext,
    calculate_ascension_skill_odds,
    calculate_normal_loot_odds,
)


class ContextRateTests(unittest.TestCase):
    def _db(self):
        tmp = tempfile.TemporaryDirectory()
        db = create_database(Path(tmp.name) / "rates.sqlite")
        release_id = insert_release(db, "test")

        unique_pool = None
        for internal_id in ("St_U_BigChomp", "St_U_Other", "St_U_Third"):
            entity_id = upsert_entity(
                db,
                release_id,
                internal_id=internal_id,
                entity_type="skill",
                rarity_value=10,
                rarity_name="Unique",
                exclude_from_pool=False,
                is_character_skill=False,
            )
            if unique_pool is None:
                db.execute(
                    """
                    INSERT INTO pools(
                        release_id, pool_key, family, rarity_name,
                        context_kind, description
                    ) VALUES(?, 'skill:Unique', 'skill', 'Unique',
                             'content_eligible', 'test')
                    """,
                    (release_id,),
                )
                unique_pool = db.execute(
                    "SELECT id FROM pools WHERE pool_key = 'skill:Unique'"
                ).fetchone()[0]
            db.execute(
                "INSERT INTO pool_members(pool_id, entity_id) VALUES(?, ?)",
                (unique_pool, entity_id),
            )

        rare_id = upsert_entity(
            db,
            release_id,
            internal_id="St_R_Test",
            entity_type="skill",
            rarity_value=1,
            rarity_name="Rare",
            exclude_from_pool=False,
            is_character_skill=False,
        )
        db.execute(
            """
            INSERT INTO pools(
                release_id, pool_key, family, rarity_name,
                context_kind, description
            ) VALUES(?, 'skill:Rare', 'skill', 'Rare',
                     'content_eligible', 'test')
            """,
            (release_id,),
        )
        rare_pool = db.execute(
            "SELECT id FROM pools WHERE pool_key = 'skill:Rare'"
        ).fetchone()[0]
        db.execute(
            "INSERT INTO pool_members(pool_id, entity_id) VALUES(?, ?)",
            (rare_pool, rare_id),
        )
        db.execute(
            """
            INSERT INTO rarity_weights(
                release_id, family, context_key, rarity_name, weight
            ) VALUES(?, 'skill', 'normal', 'Rare', 0.2)
            """,
            (release_id,),
        )
        db.commit()
        return tmp, db

    def test_big_chomp_ascension_respects_party_union_and_bans(self) -> None:
        tmp, db = self._db()
        try:
            context = RateContext(
                players=(
                    PlayerPoolContext(
                        "P1",
                        frozenset({"St_U_BigChomp", "St_U_Other"}),
                    ),
                    PlayerPoolContext(
                        "P2",
                        frozenset({"St_U_Third"}),
                    ),
                ),
                banned_items=frozenset({"St_U_Other"}),
            )
            result = calculate_ascension_skill_odds(
                db,
                internal_id="St_U_BigChomp",
                context=context,
            )
            self.assertEqual(result.denominator_count, 2)
            self.assertAlmostEqual(result.probability or 0.0, 0.5)
        finally:
            db.close()
            tmp.cleanup()

    def test_normal_rate_uses_rarity_weight_and_runtime_pool(self) -> None:
        tmp, db = self._db()
        try:
            context = RateContext(
                players=(
                    PlayerPoolContext("P1", frozenset({"St_R_Test"})),
                ),
                rarity_context="normal",
            )
            result = calculate_normal_loot_odds(
                db,
                internal_id="St_R_Test",
                context=context,
            )
            self.assertEqual(result.denominator_count, 1)
            self.assertAlmostEqual(result.probability or 0.0, 0.2)
        finally:
            db.close()
            tmp.cleanup()

    def test_unique_normal_drop_is_zero(self) -> None:
        tmp, db = self._db()
        try:
            result = calculate_normal_loot_odds(
                db,
                internal_id="St_U_BigChomp",
                context=RateContext(),
            )
            self.assertEqual(result.probability, 0.0)
        finally:
            db.close()
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
