from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sodminer.database import create_database, insert_release, upsert_entity


class DatabaseTests(unittest.TestCase):
    def test_schema_and_uniform_pool_view(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.sqlite"
            db = create_database(path)
            try:
                release_id = insert_release(db, "test")
                entity_id = upsert_entity(
                    db,
                    release_id,
                    internal_id="St_U_BigChomp",
                    entity_type="skill",
                    rarity_value=10,
                    rarity_name="Unique",
                    exclude_from_pool=False,
                    is_character_skill=False,
                )
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
                pool_id = db.execute(
                    "SELECT id FROM pools WHERE pool_key = 'skill:Unique'"
                ).fetchone()[0]
                db.execute(
                    "INSERT INTO pool_members(pool_id, entity_id) VALUES(?, ?)",
                    (pool_id, entity_id),
                )
                method_id = db.execute(
                    """
                    SELECT id FROM acquisition_methods
                    WHERE method_key = 'ascension_skill'
                    """
                ).fetchone()[0]
                db.execute(
                    """
                    INSERT INTO acquisition_rules(
                        release_id, entity_id, entity_type, method_id,
                        context_key, probability_kind, formula_text,
                        denominator_pool_id
                    ) VALUES(?, ?, 'skill', ?, 'runtime',
                             'uniform_pool', '1 / N_skill_Unique', ?)
                    """,
                    (release_id, entity_id, method_id, pool_id),
                )
                db.commit()

                row = db.execute(
                    """
                    SELECT resolved_probability, denominator_count
                    FROM v_acquisition_dictionary
                    WHERE internal_id = 'St_U_BigChomp'
                    """
                ).fetchone()
                self.assertEqual(row["denominator_count"], 1)
                self.assertEqual(row["resolved_probability"], 1.0)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
