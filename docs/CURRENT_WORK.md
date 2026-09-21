# CURRENT WORK CHECKPOINT

This file is the canonical interruption/time-out recovery point for active development.

Update this file whenever a meaningful development step completes, a blocking failure is discovered, or the immediate next action changes.

## Project

Shape of Dreams Data Miner

Repository: `novacaine4u/shape-of-dreams-data-miner`
Branch: `main`

## Active objective

Determine exactly how the v1.4 / Starless Path memory **Big Chomp** is unlocked, using reproducible evidence from the installed game data.

## Confirmed evidence

- Big Chomp exists in current game data.
- Internal memory ID: `St_U_BigChomp`
- Runtime ability/effect ID: `Ai_U_BigChomp`
- Old Chomp is separate: `St_R_Chomp`
- Big Chomp display name: `Big Chomp`
- Big Chomp image: `St_U_BigChomp.png`
- Game install inspected at:
  `C:\Program Files (x86)\Steam\steamapps\common\Shape of Dreams`
- Unity version: `6000.0.77f1`
- Scripting backend: Mono
- Managed assemblies: 241
- Relevant assemblies include `Dew.Core.dll`, `Dew.Contents.dll`, and `Assembly-CSharp.dll`
- RawData structured search found no direct Big Chomp reference in stars, achievements, quests, or other exposed JSON.
- The two Big Chomp override files describe gameplay mechanics only, not acquisition/unlock logic.

## Unlock-model lead

Documented API behavior establishes:

- `DewProfile.skills` stores all skills as `DewProfile.UnlockData`
- `UnlockStatus.Locked` means locked by an associated Achievement or Hero
- `AchUnlockOnComplete(Type targetType)` associates an achievement class with the type it unlocks

Current hypothesis to test, not yet confirmed:

An achievement class in managed metadata may carry an `AchUnlockOnComplete` attribute whose target type is `St_U_BigChomp`.

## Windows environment status

- Python: 3.12.10
- `.venv` working
- `update-windows.cmd` working
- Last validated Python suite: 11/11 passing
- .NET SDK: 8.0.425
- Repo-local NuGet source configured
- Repo-local ILSpyCmd version: 9.1.0.7988

## Current blocker

`tools\decompile-managed.cmd` successfully restores ILSpy but whole-project decompilation of `Dew.Contents.dll` fails inside ILSpy 9.1 on unrelated method:

`Shrine_MorasDomain_HerPresence.SpawnRewards`

Failure:

`System.IndexOutOfRangeException` inside ILSpy ILReader / BitSet while decompiling that method.

This is a decompiler failure, not evidence that the DLL itself is invalid.

## Active implementation

The .NET 8 metadata-scanner fallback is now implemented and committed:

- `tools/MetadataTrace/MetadataTrace.csproj`
- `tools/MetadataTrace/Program.cs`
- `tools/trace-big-chomp-unlock.cmd`

The scanner avoids method decompilation entirely. It:

1. enumerates managed custom attributes;
2. resolves attributes whose constructor type contains `AchUnlockOnComplete`;
3. identifies the owning metadata type;
4. inspects the raw custom-attribute blob for `St_U_BigChomp`;
5. prints any owner whose attribute targets Big Chomp.

The CMD wrapper builds the scanner with .NET 8 and scans `Dew.Contents.dll`, writing:

`data/extracted/managed-metadata/big-chomp-achievement-attributes.txt`

## Immediate next actions

1. On Windows, run `update-windows.cmd`.
2. Run `tools\trace-big-chomp-unlock.cmd`.
3. Upload or inspect `data\extracted\managed-metadata\big-chomp-achievement-attributes.txt`.
4. If a class maps to `St_U_BigChomp`, inspect/decompile only that class and record the relationship as explicit evidence.
5. If no achievement attribute targets Big Chomp, extend the metadata trace to Hero-based unlock relationships and `DewProfile.skills` initialization.
6. Keep whole-project ILSpy decompilation as a secondary/fallback technique only; it currently fails on unrelated method `Shrine_MorasDomain_HerPresence.SpawnRewards`.

## Recovery instruction for a new ChatGPT session

Read, in this order:

1. `docs/CURRENT_WORK.md`
2. `HANDOFF.md`
3. `docs/MODDING_RESEARCH.md`

Then inspect the current repository before changing anything.

Resume from the first incomplete item under **Immediate next actions**. Do not repeat completed RawData searches unless the game release changed.
