# Desktop GUI and Website Architecture

## Product split

The repository should produce three different artifacts from one shared data model.

### 1. Developer miner

Purpose:
- inspect a locally installed game;
- decompile/inspect managed and serialized data;
- build a normalized release snapshot;
- produce the canonical SQLite data dictionary.

This remains a developer/research tool and is **not** shipped to friends.

### 2. Windows desktop viewer

Purpose:
- browse the frozen release data;
- search memories, essences, heroes, achievements, shrines, etc.;
- show acquisition methods and provenance;
- calculate player/party-specific odds.

The desktop distribution should contain:
- compiled GUI executable;
- read-only release SQLite snapshot;
- application resources.

It should **not** contain:
- UnityDataTool;
- ILSpy;
- raw game assets;
- scripts that inspect a user's game installation.

Planned GUI technology: PySide6 / Qt.

Packaging target:
- self-contained Windows executable/application directory;
- later optional installer/signing.

### 3. Website

Purpose:
- expose the same browsing and odds functionality through a web UI;
- consume the same normalized release schema;
- have a separate build/deploy path from the Windows executable.

The web target should share:
- SQL/query layer;
- context-aware odds engine;
- field definitions and labels.

It should not depend on desktop GUI code.

## Player-specific odds

A single static drop-rate percentage is not sufficient for mechanics whose runtime pool changes.

The GUI should have an **Odds Calculator** that asks only for context dimensions known to affect the selected acquisition method.

### Currently proven context dimensions

#### Participating players and their available items

`LootManager` builds runtime pools from the union of human players' `unlockedGameItems`.

The GUI should allow:
- Solo profile.
- Add/remove additional party profiles.
- For each player, select which items are available in that profile.
- Future profile presets generated from achievement/Hero/unlock state once those mappings are fully normalized.

The app computes:

    party pool = union(player available items)

#### Lobby/game bans

Banned game items are removed from the runtime pool.

The GUI should allow a searchable banned-item list and subtract those before displaying odds.

#### Normal vs High rarity context

The game has both:
- `skillRarityChance`
- `skillRarityChanceHigh`
- `gemRarityChance`
- `gemRarityChanceHigh`

Normally this control should be derived automatically from the selected source once all callers are mapped. Until then, an Advanced section may expose the context explicitly.

#### Owned essences for Ascension

The traced essence Ascension path gives already-owned gem types selection weight 0.

When calculating an Ascension essence result, the GUI should ask which essence types the active hero already owns.

### Presentation

For every calculated rate show:

- final percentage;
- exact fraction where useful;
- target rarity;
- rarity-roll chance, when applicable;
- resolved runtime pool size;
- eligible item count;
- which players contributed items;
- banned items removed;
- owned-item exclusions;
- formula;
- source/provenance;
- warning when any required context is unknown.

Example:

    Big Chomp
    Source: Shrine of Ascension
    Input: Legendary memory

    Unique runtime pool: 7
    Big Chomp eligible: Yes

    Chance: 1 / 7 = 14.2857%

    Party contributions:
      Player 1: 6 Unique memories
      Player 2: +2 additional Unique memories

    Bans:
      1 Unique memory removed

The exact numbers above are illustrative only; the application must calculate from the selected release database and player context.

## Data separation

Canonical release facts are immutable:

    shape-of-dreams-v1.4.0.sqlite

Player-entered context belongs in a separate app-local store, for example:

    %LOCALAPPDATA%\ShapeOfDreamsDataMiner\profiles.sqlite

Do not write personal settings into the release database.

The website should likewise keep transient calculator context separate from release data.

## Shared rate engine

`src/sodminer/rate_context.py` is the shared calculation layer.

Current context model:
- `PlayerPoolContext.available_items`
- `RateContext.players`
- `RateContext.banned_items`
- `RateContext.hero_owned_gems`
- `RateContext.rarity_context`

Current calculations:
- normal skill/gem loot;
- Shrine of Ascension memory odds;
- Shrine of Ascension essence odds.

As new managed call-site research discovers additional variables, add them to this shared model first. Both desktop and web UIs should consume the same calculation code/semantics.

## UI rule

Never ask the player for an option merely because it might matter.

A control should only become part of the normal GUI after game-data/code evidence demonstrates that it affects the selected acquisition mechanic. Unknown/unresolved mechanics should be labeled as such rather than represented by invented controls or assumptions.
