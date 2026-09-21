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
