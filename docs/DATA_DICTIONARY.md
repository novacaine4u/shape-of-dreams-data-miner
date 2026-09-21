# SQLite Game Data Dictionary

The project now builds a release-scoped SQLite data dictionary from the installed game.

## Goals

The database is intentionally split into raw/forensic and normalized gameplay layers:

- every Unity object reported by UnityDataTool's Addressables analysis;
- every RawData JSON record;
- normalized gameplay entities such as memories, essences, heroes, shrines, achievements, cosmetics, and other named resources;
- serialized item facts such as rarity and pool exclusion;
- provenance/evidence for extracted facts;
- runtime pool definitions;
- acquisition mechanisms and probability formulas;
- serialized rarity weights when a readable LootManager object is present.

The first end-to-end regression item is `St_U_BigChomp`.

## Build on Windows

From the repository root:

    update-windows.cmd
    tools\build-game-data-dictionary.cmd

Optional arguments:

    tools\build-game-data-dictionary.cmd "D:\Games\Shape of Dreams" v1.4.0

Default output:

    data\normalized\shape-of-dreams-v1.4.0.sqlite

The build is read-only with respect to the installed game.

## Important drop-rate model

There is not one universal static "drop rate" for each item.

Normal skill and gem loot is a two-stage selection:

1. roll rarity;
2. choose uniformly from the eligible pool of that rarity.

Therefore for a normal skill roll:

    P(item | runtime context)
      = P(item rarity | normal/high context)
        / N(runtime eligible skills of that rarity)

`LootManager.SelectRarity` uses explicit Rare/Epic/Legendary chances and Common as the residual:

    P(Common) = 1 - P(Rare) - P(Epic) - P(Legendary)

Unique is never selected by normal rarity selection.

Shrine of Ascension skill selection is different:

    P(item | Ascension from predecessor rarity)
      = 1 / N(runtime eligible skills of target rarity)

For Big Chomp specifically:

    P(Big Chomp | ascend Legendary memory)
      = 1 / N(runtime eligible Unique memories)

The static database can resolve a **content-eligible reference rate** from all serialized eligible items. The actual run-time denominator can be smaller because `LootManager` builds its pool from the union of human players' `unlockedGameItems`, then removes banned items.

Ascension for gems is also context-dependent because gem types already owned by the hero receive selection weight 0.

## Core tables and views

Important tables:

- `releases`
- `unity_objects`
- `raw_records`
- `entities`
- `entity_attributes`
- `evidence`
- `relationships`
- `pools`
- `pool_members`
- `rarity_weights`
- `acquisition_methods`
- `acquisition_rules`

Useful views:

- `v_entity_dictionary`
- `v_pool_sizes`
- `v_acquisition_dictionary`

Example query:

    SELECT *
    FROM v_acquisition_dictionary
    WHERE internal_id = 'St_U_BigChomp';

## Current scope

The first automated pass normalizes all named Unity GameObjects and RawData top-level records, with deep serialized extraction for `St_*` memories and `Gem_*` essences.

The schema is broader than the first extractor. Subsequent passes should add:

- managed achievement-to-target mappings;
- Hero loadout membership;
- all call sites that create/drop/select skills and gems;
- source-specific drop counts/chances;
- shops, bosses, rooms, monsters, artifacts, Way of Stars, and other gameplay families;
- release-to-release diffs.

All derived probabilities must retain the source formula and context instead of collapsing context-dependent mechanics into a single misleading percentage.
