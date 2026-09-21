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

The existing serialized inspector has been upgraded to enumerate Big Chomp's attached components through UnityDataTool's analyzer database.

Next:

1. On Windows, run `update-windows.cmd`.
2. Rerun `tools\inspect-big-chomp-serialized.cmd`.
3. Upload:
   - `data\extracted\big-chomp-serialized\summary.txt`
4. The summary should now list every component attached to both `St_U_BigChomp` GameObjects and focused field hits from their dumps.
5. Record the actual serialized values for:
   - `rarity`;
   - `isCharacterSkill`;
   - `excludeFromPool`.
6. If those values are Unique / false / false, record Ascension of a Legendary memory as an explicit acquisition path because:
   - NotDiscovered is available in-game;
   - the skill is admitted to `unlockedGameItems`;
   - LootManager admits it to `poolSkillsByRarity[Unique]`;
   - Shrine_Ascension explicitly rolls Legendary -> Unique;
   - Shrine_Ascension calls `DiscoverSkill` on the resulting skill.
7. If a field still does not appear, use the listed component object id/type to dump only that exact component with a minimal fallback.

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


## DiscoverSkill caller decompile result

The targeted caller decompile established the four direct discovery paths:

### Generic gameplay discovery

`AchievementManager.ClientHeroEventOnSkillPickup(SkillTrigger obj)`
- calls `DewSave.profileMain.DiscoverSkill(obj.GetType().Name)`;
- therefore picking up a previously `NotDiscovered` skill permanently discovers it.

`AchievementManager.Dismantled(Hero hero, NetworkBehaviour item)`
- if the local player's dismantled item is a `SkillTrigger`, calls `DiscoverSkill(item.GetType().Name)`;
- therefore dismantling a previously `NotDiscovered` skill also permanently discovers it.

### Development/build-only path

`DewSave.CreateProfile`
- calls `DiscoverSkill` over all `NotDiscovered` skills only when the active build has `BuildFeatureTag.UnlockEverything`;
- this is not the normal player acquisition path.

### Content-specific path

`Shrine_Ascension.OnActivateEditSkill`
- computes the next rarity;
- selects a random skill name from `LootManager.poolSkillsByRarity[nextRarity]`;
- creates and equips that skill;
- calls `RpcShowNotice(player, fromType, toType, level)`.

For the local player, `Shrine_Ascension.UserCode_RpcShowNotice...` then calls `DiscoverSkill(toType)` whenever the result name begins with `St_`.

Therefore the Ascension shrine is a confirmed mechanism capable of discovering a skill produced from the next-rarity skill pool.

Remaining proof needed for Big Chomp specifically:

1. determine the actual rarity of `St_U_BigChomp`;
2. determine whether `St_U_BigChomp` is included in `LootManager.poolSkillsByRarity` or excluded by pool filters;
3. verify whether it is a Hero/identity/character skill (which would alter profile-state handling).

If Big Chomp is a non-hero Unique skill admitted to the Unique pool, then ascending a Legendary memory at an Ascension shrine is a direct in-game obtain/discovery path.


## LootManager pool eligibility constraint

Targeted decompilation of `LootManager` and `Dew` established how runtime skill pools are built.

`LootManager.OnStartServer()`:
- unions each human player's `unlockedGameItems` into a set;
- removes banned game items;
- if the set is empty, falls back to `DewPlayer.GetLocalUnlockedGameItems()`;
- passes that list to `AddToPool`.

A skill enters `poolSkills` / `poolSkillsByRarity` only when all of these are true:

1. the resource resolves to a `SkillTrigger`;
2. `Dew.IsSkillIncludedInGame(skillType)` is true;
3. `skillTrigger.isCharacterSkill == false`;
4. `skillTrigger.excludeFromPool == false`.

The pool bucket is then selected directly from `skillTrigger.rarity`.

Therefore Big Chomp's Ascension eligibility is not proven merely by being a `SkillTrigger`. We must still establish:
- whether a profile with Big Chomp at `NotDiscovered` includes it in `unlockedGameItems` / `GetLocalUnlockedGameItems()`;
- Big Chomp's serialized `rarity`;
- Big Chomp's serialized `isCharacterSkill`;
- Big Chomp's serialized `excludeFromPool`.

`Dew.allSkills` contains all non-abstract `SkillTrigger` subclasses. `Dew.allHeroSkills` is separately populated from each included Hero's Q/R/Identity loadout skills.


### Unique-rarity routing note

`LootManager.SelectRarity()` only returns Common, Rare, Epic, or Legendary. It never returns `Rarity.Unique`.

Therefore ordinary `SelectSkillRarity()`-based loot generation does not directly roll Unique skills.

`Shrine_Ascension.GetNextRarity()` explicitly maps Legendary -> Unique and then indexes `poolSkillsByRarity[Unique]`.

This makes Ascension a structurally special path to Unique skills. If `St_U_BigChomp` is confirmed as an eligible Unique pool member, Ascension is a strong candidate for its intended discovery path.


## NotDiscovered pool availability proven

Targeted `DewPlayer` decompilation plus the previously decompiled `DewProfile.UnlockData` closes the profile-state gate.

`DewProfile.UnlockData.isAvailableInGame` is explicitly:

`status != UnlockStatus.Locked`

Therefore both `UnlockStatus.NotDiscovered` and `UnlockStatus.Complete` are considered available in-game.

`DewPlayer.GetLocalUnlockedGameItems()` iterates `DewSave.profileMain.skills` and adds a skill when:

1. `skill.Value.isAvailableInGame` is true;
2. `Dew.IsSkillIncludedInGame(skill.Key)` is true;
3. the resource resolves;
4. `excludeFromPool == false`;
5. `isCharacterSkill == false`.

This proves a non-achievement, non-hero skill that has been moved from `Locked` to `NotDiscovered` can already be sent to `DewPlayer.unlockedGameItems` before it has ever been discovered.

For Big Chomp, the remaining unknowns are now strictly serialized resource values:
- `rarity`
- `excludeFromPool`
- `isCharacterSkill`

The RawData override for `St_U_BigChomp` does not override those fields, and the managed class itself is empty, so those values must be obtained from the serialized Unity resource/prefab rather than inferred.


## Serialized Big Chomp locator result

The raw-string locator identified the following explicit asset locations for `St_U_BigChomp`:

- `globalgamemanagers.assets`: offsets 244388 and 244428
- `resources.assets`: eight direct `St_U_BigChomp` string occurrences, including:
  - 250287384 (ASCII)
  - 250567101 (UTF-16LE)
  - 250585597 (UTF-16LE)
  - 299465005 (assembly-qualified type string)
  - 300395340 (UTF-16LE)
  - 300445096 (UTF-16LE)
  - 301204572 (UTF-16LE)
  - 301296872 (UTF-16LE)
- `StreamingAssets/aa/catalog.bin`: `St_U_BigChomp.prefab` at offset 652052
- `StreamingAssets/aa/StandaloneWindows64/defaultlocalgroup_assets_all_f2387b6895a961fa06fa44f1fcd3ded5.bundle`: `St_U_BigChomp` at offset 29175738
- `Managed/Dew.Contents.dll`: source/type-name strings only, already investigated

This proves that Big Chomp has an Addressables prefab entry and serialized Unity asset presence.

### Serialized object inspection tooling

Added a pinned official UnityDataTool v2.2.0 workflow:

- `tools/install-unitydatatool.cmd`
- `tools/inspect_big_chomp_serialized.py`
- `tools/inspect-big-chomp-serialized.cmd`

The inspector:
1. installs UnityDataTool v2.2.0 into ignored `.tools/`;
2. inspects `resources.assets`;
3. maps raw string offsets into serialized object ranges;
4. dumps matching objects and follows local object references;
5. extracts the main Addressables bundle and repeats the search there;
6. reports focused lines containing `St_U_BigChomp`, `rarity`, `excludeFromPool`, or `isCharacterSkill`.

UnityDataTool is read-only for these operations; game files are not modified.


## UnityDataTool v2.2.0 installer URL fix

The first run of `tools/inspect-big-chomp-serialized.cmd` failed during the local UnityDataTool install with HTTP 404.

Root cause:
- the repository path was incorrectly written as `Unity-Technologies/UnityDataTool` instead of `Unity-Technologies/UnityDataTools`;
- v2.2.0 predates the stable release-asset naming introduced in v2.2.1, so its Windows zip is named:
  `v2.2.0-UnityDataTool-windows-x64-release.zip`.

The exact official v2.2.0 Windows asset is now pinned to:

`https://github.com/Unity-Technologies/UnityDataTools/releases/download/v2.2.0/v2.2.0-UnityDataTool-windows-x64-release.zip`

Expected SHA-256:

`0454a2c9db06d15f33ceb2f5b0a9c305353fb225db8afae24fefbba7e7b68997`

The installer now verifies that SHA-256 before extraction.

Next action remains:
1. run `update-windows.cmd`;
2. rerun `tools\inspect-big-chomp-serialized.cmd`;
3. upload `data\extracted\big-chomp-serialized\summary.txt`.


## Big Chomp serialized GameObjects located

The first UnityDataTool serialized inspection succeeded far enough to map Big Chomp to concrete AssetBundle GameObjects:

Bundle serialized file:
`CAB-e5deeeb495f78d76b72c05f70e4c2038`

Two GameObjects named `St_U_BigChomp` were found:

- object id `-8668003336564849786`
- object id `6771284007984103187`

The AssetBundle object also contains both source asset paths:

- `Assets/Dew/Skills/U_BigChomp/St_U_BigChomp.prefab`
- `Assets/Res/LightAssets/St_U_BigChomp.prefab`

The initial object-reference walker failed to follow attached components because its text parsing did not match UnityDataTool's emitted PPtr format. That failure did not invalidate the located GameObjects.

The inspector has now been revised to use UnityDataTool's supported `analyze` SQLite workflow:
- analyze the specific AssetBundle;
- query `object_view` for GameObjects named `St_U_BigChomp`;
- query all component objects whose `game_object` points to those GameObjects;
- dump each component object by Unity object id;
- search component dumps for `rarity`, `excludeFromPool`, and `isCharacterSkill`.

This uses AssetBundle TypeTrees and avoids fragile text reference parsing.
