"""Drop-rate models recovered from managed game code."""

from __future__ import annotations

from dataclasses import dataclass

RARITY_BY_VALUE = {
    0: "Common",
    1: "Rare",
    2: "Epic",
    3: "Legendary",
    4: "Character",
    5: "Identity",
    10: "Unique",
}

RARITY_VALUE_BY_NAME = {name: value for value, name in RARITY_BY_VALUE.items()}

NORMAL_LOOT_RARITIES = ("Common", "Rare", "Epic", "Legendary")

ASCENSION_NEXT_RARITY = {
    "Common": "Rare",
    "Rare": "Epic",
    "Epic": "Legendary",
    "Legendary": "Unique",
    "Unique": "Common",
}


@dataclass(frozen=True)
class RateFormula:
    probability_kind: str
    formula_text: str
    probability_value: float | None = None


def rarity_name(value: int | None) -> str | None:
    if value is None:
        return None
    return RARITY_BY_VALUE.get(value, f"Unknown({value})")


def uniform_pool_rate(pool_size: int) -> float | None:
    if pool_size <= 0:
        return None
    return 1.0 / pool_size


def normal_loot_formula(family: str, rarity: str) -> RateFormula:
    if rarity not in NORMAL_LOOT_RARITIES:
        return RateFormula(
            probability_kind="zero",
            probability_value=0.0,
            formula_text=(
                f"0 — normal {family} rarity selection never returns {rarity}"
            ),
        )
    return RateFormula(
        probability_kind="rarity_then_uniform_pool",
        formula_text=(
            f"P({rarity} {family}) / N_{family}_{rarity}; "
            "rarity chance is a serialized LootManager runtime constant"
        ),
    )


def ascension_input_rarity(target_rarity: str) -> str | None:
    for source, target in ASCENSION_NEXT_RARITY.items():
        if target == target_rarity:
            return source
    return None


def ascension_skill_formula(target_rarity: str) -> RateFormula:
    source = ascension_input_rarity(target_rarity)
    if source is None:
        return RateFormula(
            probability_kind="unknown",
            formula_text=f"No known Ascension predecessor for {target_rarity}",
        )
    return RateFormula(
        probability_kind="uniform_pool",
        formula_text=(
            f"1 / N_skill_{target_rarity} conditional on ascending a {source} memory"
        ),
    )


def ascension_gem_formula(target_rarity: str) -> RateFormula:
    source = ascension_input_rarity(target_rarity)
    if source is None:
        return RateFormula(
            probability_kind="unknown",
            formula_text=f"No known Ascension predecessor for {target_rarity}",
        )
    return RateFormula(
        probability_kind="contextual_weighted_pool",
        formula_text=(
            f"1 / N_gem_{target_rarity}_not_owned conditional on ascending "
            f"a {source} essence; already-owned gem types receive weight 0"
        ),
    )
