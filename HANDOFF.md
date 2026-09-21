# Shape of Dreams Data Miner — Conversation Handoff

## Purpose

This document is the handoff for continuing the Shape of Dreams Data Miner project in a new ChatGPT conversation.

The project began as an investigation into how the new Big Chomp ability is obtained in Shape of Dreams v1.4 / Starless Path. It has intentionally expanded into a reusable game-data mining and relationship-analysis system so future releases can be scanned, compared, and explored through a website.

Core rule: never turn an inference into a confirmed fact. Preserve the underlying evidence and label relationships as explicit, inferred, or unknown.

## Repository

GitHub repository: novacaine4u/shape-of-dreams-data-miner
Default branch: main
Public repository: https://github.com/novacaine4u/shape-of-dreams-data-miner

## Current status

The repository was initially empty. It now contains the first Python project scaffold, documentation, evidence model, scanner, relationship foundation, JSON output, SQLite schema foundation, and website output boundary.

Important commits created so far:

- d3d3daf555e1737ff15240aef0e95e4eaa439a1d — initial README
- 46d77a20d170133049a93f9bb48ea90e29e366f3 — pyproject.toml
- 6ca94f43d3f9445d2f4f43d29bd6792cb31ace4a — package initializer
- 03b603910851fdd2e54f573c9607cef98afd0caa — normalized data models
- c52c3fe3c4b49f2bd049ae53a5fe71c3f6ee6ab4 — read-only scanner
- 600a541bf896ae2ba0118235face03d9e01d58ec — CLI
- 77d49c7e3236debaf2dd05a9a95d527ff36f3d79 — extractor package
- 16cff813b4d713130d2b65b81cf1ed931ceb5966 — relationship package
- 1249af5763e188343e58137dad7ef26fbb2f06b4 — output package
- 7fc5a0f4a332725df47f898e2604bf1e015d83a8 — MIT license
- fe1eb268e5f451a0256620ff3cb32fa949be505c — .gitignore
- c8dbc8d994f9b914868ba9f67c21529022359119 — extractor helpers
- 81ec24540fa83aa05fffec2a7049d0f4009d1fe7 — relationship graph
- ad258bc634c7a3c8ecf3480cf762f3e5483efc6d — conservative inference helper
- 15f9a53676a2647dd2dcf0ee23799ced8a2e1e1a — relationship deduplication
- a91dd338b05007df62106e55ee0f644790efa1d5 — tooling README
- 526c9e264905ae05bbb6b17634d3078de7386b96 — JSON output helper
- acbdb51cc2af57bbe21eb073bcd3ae0de305eca1 — SQLite schema foundation
- 4a7ff17b34fa2efe1765c2caabb68914d75ba696 — website output boundary
- 8f066e54e38472a0bb26e5160a01f5789e45992c — expanded README and architecture documentation

Before making more changes, inspect the current repository because the file tree will evolve.

## Progress update — 2026-09-21

The recommended documentation/inspection stage has begun.

New implementation:
- `src/sodminer/inspector.py`
- `src/sodminer/strings.py`
- `tests/test_inspector.py`
- `tests/test_strings.py`
- `sodminer inspect <path> [--output <file>]`
- `sodminer strings <path> --release <release> [--contains <text>] [--min-length <n>] [--output <file>]`
- `docs/MODDING_RESEARCH.md`

The inspector is dependency-free and read-only. It inventories Unity version clues, Mono vs IL2CPP indicators, managed/core assemblies, RawData, Mods/ModTemplate, !ModResources/overrides, Unity resources/bundles, localization candidates, and likely structured data files. The raw string extractor uses memory-mapped reads and records source file, release, byte offset, encoding, and text for ASCII, UTF-8, and UTF-16LE findings.

Modding/API research established several important documented leads:
- the official mod template references game assemblies and Harmony is built in;
- JSON overrides live under `RawData/!ModResources/overrides`;
- `DewResources` exposes a resource database with GUID/name/type lookup and dependency traversal;
- `SkillTrigger` represents memories/skills/abilities;
- `DewProfile.skills` contains all skills and maps them to `UnlockData`;
- `UnlockStatus.Locked` is documented as locked by an associated Achievement or Hero;
- `DewLocalization` exposes localization data/build data.

Immediate next action: run `sodminer inspect` against the current Shape of Dreams installation and preserve that report, then run `sodminer strings` filtered for `Big Chomp`. Use the observed layout and raw hits to choose the parser/extraction path, then trace Big Chomp through resource IDs, dependencies, localization, and unlock references.



## Live Windows validation and Big Chomp discovery — 2026-09-21

Windows development checkout:

    C:\GitHub\shape-of-dreams-data-miner

Validated interpreter:

    Python 3.12.10

A one-command Windows updater/deployer now exists at repository root:

    update-windows.cmd

It refuses to overwrite a dirty working tree, fetches and fast-forwards `main`, creates a Python 3.12 `.venv` if needed, installs the checkout editable, runs the full test suite, and prints the deployed commit.

The Unity-version regex bug discovered during the first Windows test run was fixed. Before the structured JSON search work, all 7 then-existing tests passed on Windows.

Live inspection of the installed game at:

    C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams

established:

- Unity version: `6000.0.77f1`
- scripting backend: Mono
- managed assemblies: 241
- `Assembly-CSharp.dll`, `Dew.Core.dll`, `Dew.Contents.dll`, and other managed game assemblies are directly available
- no IL2CPP indicators were found
- `RawData` exists
- `RawData/!ModResources/overrides` exists
- `Mods/ModTemplate` exists
- the inspection found 2,168 likely structured data files, heavily dominated by JSON override data

Direct search of `RawData/en-US/memories.json` established the first Big Chomp acceptance-test facts:

- old Chomp internal ID: `St_R_Chomp`
- Big Chomp internal ID: `St_U_BigChomp`
- display name: `Big Chomp`
- image: `St_U_BigChomp.png`

This is explicit game-data evidence. Do not conflate `St_R_Chomp` with `St_U_BigChomp`.

A new dependency-free command is being added for structured tracing:

    sodminer json-search <file-or-directory> <term> [--exact] [--case-sensitive] [--output <jsonl>]

It recursively searches JSON keys and string values and preserves:

- source file
- JSON path
- match kind (key or value)
- matched text
- containing top-level object key

Immediate next action after updating the Windows checkout:

    sodminer json-search "C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams\RawData" "St_U_BigChomp" --exact --output data\extracted\v1.4.0-big-chomp-json-refs.jsonl

Then inspect every returned top-level object, especially references in progression, stars, achievements, quests, profile/unlock data, or Starless Path content. Only move into managed assembly decompilation or Unity asset parsing if the structured JSON does not encode the unlock relationship.

## Existing implemented components

src/sodminer/models.py

Defines:
- Confidence = explicit | inferred | unknown
- Evidence
- Entity
- Relationship

Evidence stores source file, release, extractor, confidence, optional detail, and optional location.

Entity stores entity type, internal ID, display name, attributes, and evidence.

Relationship stores source type/ID, relation, target type/ID, confidence, and evidence.

src/sodminer/scanner.py

Read-only installation scanner. It recursively scans a game installation, ignores common transient directories, records relative path, size, SHA-256, modification time, and suffix, then writes a release manifest JSON file.

src/sodminer/cli.py

Current commands:

    sodminer inspect <path> [--output <file>]
    sodminer strings <path> --release <release> [--contains <text>] [--min-length <n>] [--output <file>]
    sodminer scan <path> --release <release> [--output <directory>]

src/sodminer/extractors/common.py

Shared helpers for evidence creation and unique strings.

src/sodminer/relationships/

graph.py provides relationship storage and incoming/outgoing traversal.
resolver.py deduplicates normalized relationships.
inference.py provides a conservative way to create inferred relationships while keeping evidence attached.

src/sodminer/output/

json.py provides basic JSON serialization.
sqlite.py contains the initial SQLite schema for entities, relationships, and evidence.
website.py is the placeholder boundary for the future website generator.

## Planned repository structure

    shape-of-dreams-data-miner/
    ├── README.md
    ├── HANDOFF.md
    ├── LICENSE
    ├── pyproject.toml
    ├── .gitignore
    ├── src/sodminer/
    │   ├── __init__.py
    │   ├── scanner.py
    │   ├── unity.py
    │   ├── il2cpp.py
    │   ├── strings.py
    │   ├── cli.py
    │   ├── models.py
    │   ├── extractors/
    │   │   ├── memories.py
    │   │   ├── essences.py
    │   │   ├── travelers.py
    │   │   ├── identities.py
    │   │   ├── artifacts.py
    │   │   ├── stars.py
    │   │   ├── achievements.py
    │   │   └── unlocks.py
    │   ├── relationships/
    │   └── output/
    ├── data/
    ├── releases/
    ├── website/
    └── tools/

Some paths above are planned only and may not exist yet.

## Original research problem: Big Chomp

The motivating question is how the new Big Chomp ability is obtained in v1.4 / Starless Path.

Important distinction: Shape of Dreams already has an older Chomp. Do not treat findings about ordinary Chomp as evidence about Big Chomp.

Earlier public research found official v1.4 / Starless Path material describing Way of Stars progression, new Universal/Common Identity Memories, six Artifacts obtained through special methods, other new Memories and Essences, and Starving Beast content. Publicly indexed material did not establish a definitive Big Chomp unlock trigger.

That uncertainty is the reason to inspect actual game data.

## Data-mining strategy

Target pipeline:

    Shape of Dreams installation
              |
              v
         raw file scan
              |
        +-----+------+
        |            |
     Unity data   assemblies
        |            |
        +-----+------+
              |
              v
       entity extraction
              |
              v
      relationship resolver
              |
              v
          SQLite/JSON
          /          \
         v            v
    release diff   website/API

The major improvement over the earlier one-off PowerShell search is that the Python system must trace relationships between data objects rather than merely listing files that contain a string.

## Entity families to support

At minimum:

- Memories
- Essences
- Travelers
- Identity Memories
- Artifacts
- Way of Stars nodes
- Achievements
- Unlock conditions
- Localization strings
- Internal IDs
- Cross-references

Keep the extractor architecture extensible for additional entity types.

## Big Chomp acceptance test

The first end-to-end run should answer:

1. Does Big Chomp exist in the installed release data?
2. What internal identifier represents it?
3. Which asset/database entry defines it?
4. Which localization or display string names it?
5. What entities reference it?
6. Is an unlock condition explicitly encoded?
7. If not explicit, what evidence supports an inferred condition?
8. What changed between relevant releases?

Ideally the graph begins with Big Chomp and follows its memory ID, localization, ability/effect definition, progression references, and unlock condition.

## Evidence rules

Every important fact should preserve provenance.

Explicit: the game data directly contains the relationship or requirement.

Inferred: evidence strongly suggests the relationship but no direct encoded reference was found.

Unknown: available evidence is insufficient.

Do not fill gaps merely because a pattern seems plausible.

## Release-diff goal

Each analyzed release should become a separate evidence snapshot.

Future command:

    sodminer diff <release-a> <release-b>

The diff should eventually report new, removed, and changed entities; localization changes; relationship changes; unlock-reference changes; asset changes; and detectable internal-ID changes.

## Website goal

Eventually build a searchable game-data explorer with:

- global entity search
- entity detail pages
- relationship graph visualization
- source/evidence view
- release selector
- release diff pages
- entity-type filters
- explicit/inferred/unknown indicators
- internal IDs and asset names
- localization display
- unlock-condition evidence

The website should make it possible to start at Big Chomp and traverse to the progression structures that reference it.

## Important external research lead

Earlier research identified the GitHub repository LizardSmoothie/ShapeOfDreamsModDocs as official or closely related Shape of Dreams modding documentation.

Inspect it before implementing custom parsers. Look specifically for Unity asset access, ScriptableObject patterns, game database structures, assembly names, serialization formats, localization, and mod APIs exposing memories, progression, artifacts, stars, or unlock logic.

Do not assume undocumented structures when documented formats or APIs exist.

## Previous one-off tool

A PowerShell reconnaissance script named Find-BigChomp.ps1 was previously designed. It searched text/config files, Unity/game binaries, ASCII and UTF-16 strings, raw byte sequences, unlock terminology, and relevant DLLs.

It was useful reconnaissance but insufficient for establishing object relationships or an exact unlock condition. The Python project is intended to replace it.

## Recommended next implementation stage

Do not immediately implement dozens of game-specific extractors. First understand how the current Shape of Dreams build stores its data.

1. Inspect the ShapeOfDreamsModDocs repository and related documentation.
2. Add sodminer inspect <path> to detect Unity version, Mono vs IL2CPP, major assemblies, Unity data directories, resource/bundle files, localization files, executable metadata, and likely database/config files.
3. Add a reusable raw string extractor supporting ASCII, UTF-8, and UTF-16LE with file, offset, encoding, string, and release provenance.
4. Identify the actual Unity data format used by the game and select appropriate parsing libraries/tools.
5. Implement Unity-aware extraction before writing game-specific extractors.
6. Locate Big Chomp and collect every relevant internal ID, localization key, asset reference, and cross-reference.
7. Follow references into progression, achievements, Way of Stars, artifacts, identities, and unlock logic.
8. Generalize successful extraction logic to Memories, Essences, Artifacts, Travelers, and other entities.

## Future CLI direction

Current:

    sodminer scan <path> --release <release>

Likely future commands:

    sodminer inspect <path>
    sodminer scan <path> --release <release>
    sodminer extract <snapshot>
    sodminer build-db <snapshot>
    sodminer search <term>
    sodminer show <entity-id>
    sodminer graph <entity-id>
    sodminer diff <release-a> <release-b>
    sodminer build-site

Keep stages composable so expensive scanning does not have to be repeated unnecessarily.

## Engineering requirements

- Python 3.10+
- Prefer standard library where practical.
- Keep the game installation read-only.
- Avoid committing large extracted game datasets to Git.
- Preserve hashes and release identifiers.
- Preserve source locations for findings.
- Use explicit/inferred/unknown confidence everywhere the relationship layer needs it.
- Add tests for parsing and normalization logic.
- Keep extraction adapters separate from normalized domain models.
- Keep the website independent from raw Unity formats.

## Starting a new conversation

Point the new conversation at this repository and provide this instruction:

Continue the Shape of Dreams Data Miner project from HANDOFF.md. Inspect the current repository before changing anything. The immediate goal is to identify the Unity/game data format used by the current Shape of Dreams release, then build the first extraction pipeline capable of locating Big Chomp and tracing its references. Preserve provenance and distinguish explicit, inferred, and unknown relationships. Do not recreate the existing scaffold unless the repository actually lacks it.

## Definition of success

The long-term goal is a reusable Shape of Dreams data explorer. After a new game release, it should be possible to scan the installation and answer questions such as:

- What is Big Chomp?
- What internal object defines it?
- When was it introduced?
- What progression system references it?
- What exactly unlocks it?
- What evidence proves that?
- What changed since the previous release?

The project should ultimately make those answers reproducible from extracted game data rather than from guesswork or scattered web searches.
