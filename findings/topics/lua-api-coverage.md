# Lua API: what the DLL registers vs the community reference (Sukritact knowledge base, `wheat-gpp/civ6-lua-*.md`)

Sources: `lua_registry.tsv` (2,320 registrations read from GameCore's registration tables, symbol build, 95 % mapped to the current build) and
`civ6-lua-signature-index.md` (82 objects, 1,689 methods; parsed 81 objects, 1,607 methods). Script: `tools/lua_compare.py`.

## Verified
* The DLL side is complete for GameCore: every `l*` wrapper is registered (no dormant ones), and **the current build adds no Lua method names**: the only strings
  new in the current DLL are the New Frontier Pass leaders, achievements and one effect (see `build-differences.md`).
* After aliasing the object names (the DLL calls `Plot` `MapPlot`, `CongressManager` `WorldCongress`, `TeamDiplomacy` `PlayerDiplomacy`, ...):
  1,499 (object, method) pairs are in both; 421 only in the DLL; 97 only in the reference.
* The 97 reference-only entries: 90 are `GameConfiguration` (73) and `MapConfiguration` (17), which live outside GameCore (not in our data); 7 are registered in
  the DLL through another path that our scan missed (`AiDiplomacy.GetDealItemDesirability[String]`, `CityDistricts/PlayerCities/PlayerUnits.Members`,
  `DealManager.RequestUpdate`, `Game.WriteHistoryLog`: their names are present as strings in the DLL).
* 421 DLL-only methods: 61 have the same method name on another reference object (object-name mismatch) and **360 are not in the reference at all**
  (`tables/lua_methods_not_in_reference.tsv`). Largest groups: `DealItem` 33, `WorldBuilderPlayerManager` 25, `Deal` 22, `NotificationInstance` 22, `HallofFame` 20,
  `WorldBuilderManager` 20, `WorldBuilderMapManager` 17, `PlayerConfiguration` 16, `GameEconomicManager` 13, `MapStartPositioner` 13, `Barbarians` 12, `CityPower` 12,
  `PlayerVisibility` 11, `AutoplayManager` 10, `GameHeroesManager` 9, `GameSummary` 9.
  Whether a modder can reach each object depends on a getter that returns it (not checked).
* Lua constant tables used by the game's own UI scripts all exist in the Linux enums: `PlayerOperations` 64/66 names (missing: `DIPLOMACY_DECLARE_WAR`, `DIPLOMACY_MAKE_PEACE`),
  `UnitOperationTypes` 33/33, `UnitCommandTypes` 27/28 (`RAID_CLAN`), `CityOperationTypes` 17/18, `CityCommandTypes` 27/27. The reference has no `PlayerOperations`/`PARAM_*` tables.

## Not reliable / not checked
* The `side` field (UI cache vs gameplay interface) is which interface class registered a method, not proof of which Lua state can call it. 283 methods the reference
  flags `[UIS]` appear only on the gameplay interface (mostly `Map*`, `GameEffects`, `Combat`); the reference flag is more trustworthy for availability.
* Signatures (argument counts and types) and return values are not recovered; the reference has them for its methods and we have nothing for the 360.
* Objects implemented outside GameCore (UI controls, `Events`, `Network`, `Locale`, configuration, `Input`, ...) are not covered by our data.
* Events (`Events.*` names and parameters) were not compared.
