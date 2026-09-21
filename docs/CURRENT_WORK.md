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

Whole-project ILSpy decompilation remains unreliable because ILSpy 9.1 crashes on unrelated method:

`Shrine_MorasDomain_HerPresence.SpawnRewards`

Failure:

`System.IndexOutOfRangeException` inside ILSpy ILReader / BitSet.

The metadata-scanner path works and is now preferred.

## Active implementation

The .NET 8 metadata-scanner fallback is implemented and is now the preferred managed-code path:

- `tools/MetadataTrace/MetadataTrace.csproj`
- `tools/MetadataTrace/Program.cs`
- `tools/trace-big-chomp-unlock.cmd`
- `tools/trace-big-chomp-metadata-wide.cmd`

The scanner avoids method decompilation entirely.

It now supports:

- filtering to a specific attribute type such as `AchUnlockOnComplete`;
- wildcard scanning of all custom attributes;
- matching-only output for blobs that contain `St_U_BigChomp`;
- reporting matching type definitions, metadata token, base type, interfaces, and type-level custom attributes.

The achievement-only trace writes:

`data/extracted/managed-metadata/big-chomp-achievement-attributes.txt`

The new wide trace scans both `Dew.Contents.dll` and `Dew.Core.dll` and writes:

`data/extracted/managed-metadata/big-chomp-wide-metadata.txt`

## Latest managed-metadata result

The first achievement-unlock metadata trace completed successfully.

It found **94** `AchUnlockOnComplete` attribute instances in `Dew.Contents.dll`.

Result for target `St_U_BigChomp`:

- target matches: **0**
- no achievement class has `AchUnlockOnComplete(typeof(St_U_BigChomp))`
- therefore Big Chomp is **not** directly unlocked by the game's standard achievement→target attribute mapping

This is explicit negative evidence for the achievement path.

## Immediate next actions

1. Add a targeted decompile helper for `AchievementManager`, `DewSave`, and `Shrine_Ascension`.
2. Decompile those types only; do not use whole-project mode.
3. Extract and inspect:
   - `AchievementManager.Dismantled`
   - `AchievementManager.ClientHeroEventOnSkillPickup`
   - `DewSave.CreateProfile`
   - `Shrine_Ascension.UserCode_RpcShowNotice__DewPlayer__String__String__Int32`
4. Determine which paths call `DiscoverSkill` generically and which are content-specific.
5. If `Shrine_Ascension` passes the skill name dynamically, trace the source of that argument and check for `St_U_BigChomp` / Starless Path context.
6. Separately verify whether `St_U_BigChomp` belongs to `Dew.allHeroSkills` / a Hero loadout.
7. Preserve the final acquisition path as explicit evidence.

## Recovery instruction for a new ChatGPT session

Read, in this order:

1. `docs/CURRENT_WORK.md`
2. `HANDOFF.md`
3. `docs/MODDING_RESEARCH.md`

Then inspect the current repository before changing anything.

Resume from the first incomplete item under **Immediate next actions**. Do not repeat completed RawData searches unless the game release changed.


## Windows updater artifact note

The first local build of the .NET metadata scanner created untracked:

- `tools/MetadataTrace/bin/`
- `tools/MetadataTrace/obj/`

These are disposable build artifacts. They were added to `.gitignore` so future scanner runs will not make `update-windows.cmd` report a dirty working tree.

If a Windows checkout was created before that ignore rule arrived, delete those two directories once, then rerun `update-windows.cmd`.


## Wide Big Chomp metadata result

The wide metadata trace completed against both `Dew.Contents.dll` and `Dew.Core.dll`.

Explicit findings:

- `St_U_BigChomp` is defined in `Dew.Contents.dll`.
- Metadata token: `0x02000B83`.
- Base type: `SkillTrigger`.
- Interfaces: none.
- Type-level custom attributes: none.
- `Dew.Contents.dll` custom attributes scanned: 6,122.
- `Dew.Contents.dll` custom-attribute blobs containing `St_U_BigChomp`: 0.
- `Dew.Core.dll` custom attributes scanned: 5,354.
- `Dew.Core.dll` contains no `St_U_BigChomp` type definition and no custom-attribute blob containing that name.

Conclusion: Big Chomp is not wired to acquisition through managed custom-attribute metadata. Combined with the earlier 94-entry `AchUnlockOnComplete` scan, the standard achievement-attribute unlock path is ruled out.

Next investigation layer: targeted single-type decompilation of `St_U_BigChomp`, `SkillTrigger`, and `DewProfile` (including nested `UnlockData`) to inspect constructors/static initialization/profile unlock-status assignment without invoking whole-project decompilation.


## Targeted decompile result: profile state machine

Targeted decompilation completed for:

- `St_U_BigChomp`
- `SkillTrigger`
- `DewProfile`

Key findings:

- `St_U_BigChomp` itself is an empty subclass of `SkillTrigger` apart from Mirror-generated plumbing. It contains no bespoke unlock/acquisition logic.
- `DewProfile.Validate()` builds a set of targets locked by **incomplete achievements**. That set includes direct achievement targets and, when an incomplete achievement unlocks a Hero, that Hero's Q/R/Identity loadout skills.
- Skills not in that locked set are passed to `UnlockSkill(name)`.
- `UnlockSkill(name)` checks whether the skill is a Hero skill and whether `Dew.GetRequiredAchievementOfTarget(name)` returns an achievement.
- If the skill is **not** a Hero skill and has **no** required achievement, `UnlockSkill` sets its state to `UnlockStatus.NotDiscovered` rather than `Complete`.
- `DiscoverSkill(name)` is the observed transition from `NotDiscovered` to `Complete`.

Current Big Chomp evidence already rules out a direct `AchUnlockOnComplete` mapping. Therefore, unless Big Chomp is present in a locked Hero's loadout, its expected profile state is `NotDiscovered` and actual acquisition occurs when some gameplay code calls `DiscoverSkill("St_U_BigChomp")`.

The next high-value question is now: **which methods call `DewProfile.DiscoverSkill`, and under what gameplay condition?**


## DiscoverSkill call-site result

Managed IL scanning found exactly four direct call sites to `DewProfile.DiscoverSkill` across the scanned game assemblies:

`Dew.Core.dll`
- `AchievementManager::Dismantled`
- `AchievementManager::ClientHeroEventOnSkillPickup`
- `DewSave::CreateProfile`

`Dew.Contents.dll`
- `Shrine_Ascension::UserCode_RpcShowNotice__DewPlayer__String__String__Int32`

No direct call sites were found in `Dew.UI.dll` or `Assembly-CSharp.dll`.

Interpretation:

- ordinary skill pickup can permanently discover a `NotDiscovered` skill;
- dismantling a skill can also discover it;
- profile creation has a discovery path that must be inspected to determine whether it seeds defaults;
- `Shrine_Ascension` has a special content-specific discovery path and is currently the strongest lead for a non-generic Big Chomp acquisition mechanic.

The next step is to target-decompile `AchievementManager`, `DewSave`, and `Shrine_Ascension` and inspect only the relevant caller methods.
