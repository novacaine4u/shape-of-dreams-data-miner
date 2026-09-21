# Shape of Dreams Data Miner

A reusable, provenance-aware data miner for **Shape of Dreams**.

The first acceptance test is the new **Big Chomp** memory from v1.4 / Starless Path, but the architecture is intentionally broader: the goal is to turn each game release into a searchable dataset and eventually a browsable website.

## Design goals

- Scan a local game installation without modifying game files.
- Extract structured entities from Unity assets, assemblies, localization, and supported raw sources.
- Preserve evidence and provenance for every extracted fact.
- Resolve relationships between memories, essences, travelers, identities, artifacts, stars, achievements, and unlock conditions.
- Clearly distinguish explicit, inferred, and unknown information.
- Store normalized data in SQLite and export JSON.
- Compare releases so new and changed content can be identified after updates.
- Provide a foundation for a searchable web UI.

## Status

The project now has an end-to-end proven acquisition trace for Big Chomp plus reusable managed-code, Unity serialized-data, and SQLite dictionary tooling. The read-only scanner, installation inspector, provenance-aware string/JSON search, metadata/call-site tracing, targeted decompilation, UnityDataTool integration, and game-wide SQLite catalog builder are implemented.

Big Chomp is the first regression case: its Unique rarity, pool eligibility, profile discovery state, Shrine of Ascension acquisition path, and context-dependent rate formula are all backed by explicit game data/code evidence.

## Quick start

On Windows, update/deploy/test the checkout in one command:

    update-windows.cmd

Manual install:

    python -m pip install -e .

Inspect the game installation:

    sodminer inspect "C:/Program Files (x86)/Steam/steamapps/common/Shape of Dreams" --output data/extracted/v1.4.0-inspection.json

Search structured JSON for an internal ID or display name:

    sodminer json-search "C:/Program Files (x86)/Steam/steamapps/common/Shape of Dreams/RawData" "St_U_BigChomp" --exact --output data/extracted/v1.4.0-big-chomp-json-refs.jsonl

Extract raw strings when structured JSON is insufficient:

    sodminer strings "C:/Program Files (x86)/Steam/steamapps/common/Shape of Dreams" --release v1.4.0 --contains "Big Chomp" --output data/extracted/v1.4.0-big-chomp-strings.jsonl

Create a release manifest:

    sodminer scan "C:/Program Files (x86)/Steam/steamapps/common/Shape of Dreams" --release v1.4.0

The inspect, json-search, strings, and scan commands treat the game installation as read-only.

## Evidence model

Every extracted fact should carry:

- source file or asset
- release identifier
- extraction method
- confidence: explicit, inferred, or unknown
- optional evidence text or identifier

This is particularly important for unlock-condition research. A relationship inferred from nearby data must never be presented as a confirmed game rule.

## Planned pipeline

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

## Target entity families

- Memories
- Essences
- Travelers
- Identity Memories
- Artifacts
- Way of Stars nodes
- Achievements
- Unlock conditions
- Localization strings
- Internal IDs and cross-references

## Big Chomp acceptance test

The first end-to-end research target is the v1.4 **Big Chomp** memory. The miner should eventually be able to answer:

1. Does Big Chomp exist in the installed release data?
2. What internal identifier represents it?
3. Which asset/database entry defines it?
4. Which display/localization string names it?
5. What entities reference it?
6. Is an unlock condition explicitly encoded?
7. If the condition is inferred, what evidence supports the inference?
8. What changed between releases?

## SQLite data dictionary

Build the current release dictionary on Windows:

    update-windows.cmd
    tools\build-game-data-dictionary.cmd

Default output:

    data\normalized\shape-of-dreams-v1.4.0.sqlite

The database stores every Unity object row from the Addressables analysis, every RawData JSON record, normalized gameplay entities, provenance, pools, acquisition mechanisms, and context-aware drop-rate formulas.

See `docs/DATA_DICTIONARY.md` for schema and rate semantics.

## Release snapshots

Each analyzed release should be kept separately so the project can perform comparisons such as:

    sodminer diff v1.3.x v1.4.0

This makes future game updates useful rather than destructive: a new release becomes another evidence snapshot.

## Repository structure

    src/sodminer/
      scanner.py
      models.py
      cli.py
      extractors/
      relationships/
      output/

    data/
      raw/
      extracted/
      normalized/

    releases/
    website/
    tools/

## License

MIT


## Managed-code research

When RawData does not contain an explicit relationship, the repository includes an optional read-only managed assembly decompilation helper:

    tools\decompile-managed.cmd

It uses the repo-local `ilspycmd` tool manifest, decompiles `Dew.Contents.dll` and `Dew.Core.dll` into ignored `data/extracted/managed-decompile`, then searches the output for Big Chomp and achievement-unlock metadata. It requires `dotnet` 8 or newer on PATH. The pinned ILSpy version is 9.1.0.7988 so the helper remains compatible with .NET 8 rather than requiring the current .NET 10-only ILSpy releases.


### Targeted Big Chomp unlock trace

Whole-project decompilation is not required for the current unlock investigation. Use:

    tools\decompile-big-chomp-targeted.cmd

This decompiles only `St_U_BigChomp`, `SkillTrigger`, and `DewProfile`, then produces a focused unlock trace under `data/extracted/managed-targeted`. This avoids unrelated methods that can trigger ILSpy whole-project decompiler failures.
