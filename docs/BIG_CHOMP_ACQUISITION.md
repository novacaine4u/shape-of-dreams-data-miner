# Big Chomp acquisition trace

## Conclusion

`St_U_BigChomp` is a **Unique** memory that is eligible for the runtime skill pool and can be obtained by using a **Shrine of Ascension** on a **Legendary** memory, then rolling Big Chomp from the eligible Unique pool.

Receiving Big Chomp through that Ascension result calls `DewProfile.DiscoverSkill("St_U_BigChomp")`, which transitions it from `NotDiscovered` to `Complete`.

## Evidence chain

1. **No direct achievement unlock**
   - The complete `AchUnlockOnComplete` scan in `Dew.Contents.dll` found 94 mappings and zero targets for `St_U_BigChomp`.

2. **No Big-Chomp-specific custom unlock attribute**
   - Wide custom-attribute scanning across `Dew.Contents.dll` and `Dew.Core.dll` found no attribute blob referencing `St_U_BigChomp`.

3. **Profile state**
   - `DewProfile.UnlockSkill` places a normal non-hero/non-achievement skill into `UnlockStatus.NotDiscovered`.
   - `DewProfile.DiscoverSkill` transitions `NotDiscovered -> Complete`.

4. **NotDiscovered is already runtime-available**
   - `DewProfile.UnlockData.isAvailableInGame` is `status != UnlockStatus.Locked`.
   - Therefore `NotDiscovered` is available in-game.

5. **Runtime item-list eligibility**
   - `DewPlayer.GetLocalUnlockedGameItems()` includes a skill if:
     - `isAvailableInGame` is true;
     - it is included in the build;
     - `excludeFromPool == false`;
     - `isCharacterSkill == false`.

6. **Big Chomp serialized prefab values**
   - `rarity = 10`;
   - `excludeFromPool = 0`.

7. **Rarity enum**
   - `Rarity.Unique = 10`.
   - `Rarity.Character = 4`.
   - `SkillTrigger.isCharacterSkill` is computed as `rarity == Rarity.Character`.
   - Therefore Big Chomp is Unique, not excluded from the pool, and not a character skill.

8. **LootManager**
   - Eligible skills are placed in `poolSkillsByRarity[skill.rarity]`.
   - Normal rarity selection only returns Common, Rare, Epic, or Legendary; it does not select Unique.

9. **Shrine of Ascension**
   - `Shrine_Ascension` explicitly maps Legendary -> Unique.
   - It chooses a random skill from `LootManager.poolSkillsByRarity[Unique]`.
   - It creates/equips the selected skill.
   - For the local player, the result path calls `DewSave.profileMain.DiscoverSkill(toType)`.

10. **Prefab reference check**
    - Incoming-reference analysis for both `St_U_BigChomp` prefab copies found only AssetBundle container/preload and normal GameObject/component/Transform relationships.
    - No Hero/loadout reference was found in the analyzed bundle.

## Practical interpretation

To discover Big Chomp through the explicit acquisition mechanism identified in code:

1. obtain a Legendary memory;
2. use it at a Shrine of Ascension;
3. the shrine promotes the rarity target to Unique;
4. the shrine randomly selects an eligible Unique skill from the runtime Unique pool;
5. if the roll is Big Chomp, Big Chomp is created/equipped and permanently marked discovered.

The selection is random among eligible Unique skills contributed by the players' combined unlocked-game-item set, so Big Chomp is not guaranteed on any single Ascension attempt.

Generic pickup and dismantle handlers also call `DiscoverSkill`, so any other runtime source that produces Big Chomp would likewise permanently discover it.
