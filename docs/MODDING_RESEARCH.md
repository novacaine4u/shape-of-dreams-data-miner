# Shape of Dreams Modding/Data Research Notes

## Sources inspected

- LizardSmoothie/ShapeOfDreamsModDocs README
- Shape of Dreams API documentation for `DewResources`, `SkillTrigger`, `DewProfile`, `DewProfile.UnlockData`, `DewLocalization`, and `UnlockStatus`

These notes record documented leads only. They do not prove how every current release stores the corresponding objects on disk.

## Documented installation and modding structure

The official modding guide points mod creators at:

- `<GameFolder>/Mods/ModTemplate`
- game assembly references used by the template
- built-in Harmony support
- `<GameFolder>/RawData/!ModResources/overrides`

This makes `Mods`, managed assemblies, `RawData`, and `!ModResources/overrides` high-priority inspection targets.

## Documented runtime resource model

`DewResources` is the runtime Unity-object resource layer in `Dew.Core.dll`.

Documented capabilities include:

- a resource database
- loaded GUID enumeration
- lookup by GUID
- lookup by name
- lookup by type
- lookup by link type and ID
- name/type substring search
- dependency traversal through `GetAllDependencies`
- obtaining the GUID or link ID of an asset

Implication: the miner should preserve GUIDs, link IDs, names, types, and dependency edges whenever they can be recovered from files or assemblies.

## Memories / skills

The API describes `SkillTrigger` as representing traveler memories / skills / abilities.

`DewProfile.skills` is a dictionary containing all skills in the game, including character-only and pool-excluded entries. Its values are `DewProfile.UnlockData`.

Implication: Big Chomp should eventually be traced as a `SkillTrigger`/skill resource and then connected to the profile unlock structures rather than being treated only as a display string.

## Unlock model

`UnlockStatus` contains:

- `Complete`
- `Locked`
- `NotDiscovered`

The API describes `Locked` as locked by an associated Achievement or Hero, while `NotDiscovered` is available by default but not yet found in-game.

`DewProfile` separately exposes dictionaries for achievements, artifacts, gems, heroes, and skills.

Implication: once a Big Chomp skill key is known, achievement/hero references are especially important candidates for an explicit unlock relationship. This is a research direction, not yet a confirmed Big Chomp condition.

## Localization

`DewLocalization` exposes runtime localization build data and per-language localization data.

Implication: localization should be extracted as a separate evidence layer and joined to resource/internal IDs where possible.

## Current engineering consequence

The first disk-level step is intentionally generic:

    sodminer inspect <game-folder>

It inventories:

- Unity version clues
- Mono vs IL2CPP indicators
- managed assemblies and core assemblies
- `RawData`
- `Mods/ModTemplate`
- `!ModResources/overrides`
- Unity assets/resources/bundles
- localization candidates
- likely structured data files

The next parser decision should be made only after a real current-release inspection report is available.


## Achievement-driven unlocks

The current API documentation adds a stronger documented unlock mechanism:

- `DewProfile.skills` contains all skills in the game and maps each key to `DewProfile.UnlockData`.
- `DewProfile.UnlockData` contains an `UnlockStatus status` field plus `didReadMemory` and `isNewHeroOrHeroSkill`.
- `UnlockStatus.Locked` is documented as "Locked by associated Achievement or Hero."
- `AchUnlockOnComplete` is a class-level attribute with constructor `AchUnlockOnComplete(Type targetType)` and a `targetType` property.

Implication: for a locked memory such as Big Chomp, achievement class metadata is a high-value source of explicit unlock relationships. A class decorated with `[AchUnlockOnComplete(typeof(St_U_BigChomp))]` or equivalent would be direct evidence that the achievement unlocks Big Chomp. This relationship may exist only in managed assembly metadata and therefore may not appear in RawData JSON.

## Big Chomp live structured-data result

The v1.4.0 RawData trace established:

- Big Chomp internal ID: `St_U_BigChomp`
- runtime ability-instance ID: `Ai_U_BigChomp`
- `St_U_BigChomp.json` contains cast/cooldown/level-up configuration only
- `Ai_U_BigChomp.json` contains runtime effect values (damage, healing, shield, boss multiplier, cooldown reduction, etc.) only
- a broad `BigChomp` structured JSON search returned only the two override targets plus localized memory/image references
- no stars, achievements, quests, or other RawData JSON contained a direct Big Chomp reference

Therefore the unlock investigation should now prioritize managed assembly metadata/code, especially achievement classes and profile initialization logic.
