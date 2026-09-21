from __future__ import annotations

import unittest

from sodminer.catalog import infer_entity_type, parse_unity_dump


class CatalogParsingTests(unittest.TestCase):
    def test_infer_core_entity_types(self) -> None:
        self.assertEqual(infer_entity_type("St_U_BigChomp"), "skill")
        self.assertEqual(infer_entity_type("Gem_Test"), "gem")
        self.assertEqual(infer_entity_type("Hero_Test"), "hero")
        self.assertEqual(infer_entity_type("Shrine_Ascension"), "shrine")

    def test_parse_big_chomp_serialized_fields(self) -> None:
        fields = parse_unity_dump(
            """
MonoBehaviour Base
 rarity (UInt8) 10
 excludeFromPool (UInt8) 0
 nested (SomeStruct)
  rare (float) 0.25
"""
        )
        self.assertEqual(fields["rarity"], 10)
        self.assertEqual(fields["excludeFromPool"], 0)
        self.assertEqual(fields["nested.rare"], 0.25)


if __name__ == "__main__":
    unittest.main()
