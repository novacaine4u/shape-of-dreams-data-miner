from __future__ import annotations

import unittest

from sodminer.drop_rates import (
    ascension_input_rarity,
    ascension_skill_formula,
    normal_loot_formula,
    rarity_name,
    uniform_pool_rate,
)


class DropRateTests(unittest.TestCase):
    def test_rarity_value_10_is_unique(self) -> None:
        self.assertEqual(rarity_name(10), "Unique")

    def test_unique_has_zero_normal_skill_drop_probability(self) -> None:
        formula = normal_loot_formula("skill", "Unique")
        self.assertEqual(formula.probability_kind, "zero")
        self.assertEqual(formula.probability_value, 0.0)

    def test_unique_ascension_predecessor_is_legendary(self) -> None:
        self.assertEqual(ascension_input_rarity("Unique"), "Legendary")
        formula = ascension_skill_formula("Unique")
        self.assertEqual(formula.probability_kind, "uniform_pool")
        self.assertIn("1 / N_skill_Unique", formula.formula_text)

    def test_uniform_pool_rate(self) -> None:
        self.assertAlmostEqual(uniform_pool_rate(8), 0.125)
        self.assertIsNone(uniform_pool_rate(0))


if __name__ == "__main__":
    unittest.main()
