---
title: National Parks - the tile rule, custom shapes and park rules as data (Dev CE)
order: 69
---
# National Parks: the tile rule, custom shapes and park rules as data (Dev CE)

**Availability.** The engine facts below come from the game library (decompiled; the live results are marked). The Lua functions and the mod need the **Dev CE** GameCore mod ([0.9.0-experimental](https://github.com/cru121/civ6-dev-ce/releases/tag/v0.9.0-experimental) or newer), Steam build 26595377, single player. Nothing here is possible from plain Lua: the rule and the park shape are fixed in the engine.

## What the game does
* **A park is a record, not a shape.** `Game::NationalParks` keeps a vector of `ParkData` (0x30 bytes): founder, turn, a `vector<int>` of plot indices, the name. Every consumer (`FindPark`, `IsNationalPark`, `RemovePark`, visibility, the UI cache copy) just iterates the plot list, so any plot set works at the data level. The parks vector is a tracked variable (`FAutoVariable`, edited through its `edit` accessor so that saving and syncing see the change). The record is serialised with its plot count, so a park of any size saves and loads.
* **`DesignatePark(player, base plot)` hard-codes the shape**: the base plot, two direction-offset neighbours and the neighbour's neighbour, a 4-plot rhombus. It fails if one of the four plots does not exist; it does **not** check tile rules. Its only direct caller is the unit operation `DesignatePark::Start`, which uses only the unit's own plot and asks `GetAssociatedBaseTile` for the park that contains it.
* **The owner of a park is the city that owns plot #1**: tourism (`GetParkTourismForCity`, `RecordTourismFromParks`), amenities and `RemoveParks(city)` all look at the first plot. Tourism of a park sums over **all** its plots.
* **One rule decides every tile:** `IsValidParkTile(plot, player)` (RVA 0x237840 in build 26595377). All must hold: the plot is owned by the player; no improvement; no district on the plot (this is what excludes districts and world wonders); and either a mountain terrain (mask `0x4924` over the terrain index), a natural wonder, or an appeal value (plot virtual function +0x28) of **2 or more**; and the plot is not already in a park. Its one direct caller is `GetPossibleParks`, which builds the candidate rhombi (all four plots valid, same owning city, not all four impassable), scores them by the sum of the four appeal values and sorts. The UI cache version delegates to the same function, so **the highlight, the vanilla Designate action and the AI** (`AI::Homeland::PlotFoundNationalPark` moves a Naturalist to `CultureAi::GetBestParkSpot` and issues the vanilla request) all share this single rule.
* **Fences and the green border are additive.** The `NATIONAL_PARK_ADDED_TO_MAP` event makes the exe add a `NATIONAL_PARK_FENCE` for every plot in the event (up to 32) and extend the border overlay; nothing removes older plots, and the event carries the plot list read from the *current game state*. *Verified in game (build 15038592):* re-sending ADDED after editing a park's plots in place drew the union of old and new plots. A new park whose list is final before its single ADDED event gets exactly the right fences and border; `RemovePark` clears everything.
* **Wonder on a tile:** `Plot:GetWonderType()` is `*(short*)(plot->vtable[0x30](plot) + 0x1e)`, a `Buildings` index (-1 = none) held in the plot's city-attributes record, the same record that gives the owning player (+0x1c) and `GetDistrictType`.

## Dev CE API
Gameplay state unless noted.

| function | what it does |
|---|---|
| `NationalParks.DesignateCustom(player, {plot, ...})` | creates a park on 1 to 32 arbitrary plots (the exe reads at most 32). Checks only what keeps the game safe: plots exist, no duplicates, none already in a park; **no tile rules**. Plot #1 must be inside a city's borders (it becomes the owner). Returns 0, or 1 bad count, 2 outside the map, 3 duplicate, 4 already in a park, 5 no temporary record could be made (map edge), 6 internal, 7 first plot not in a city's borders. |
| `NationalParks.IsValidParkTile(player, plot)` | the rule currently in force (also in the UI state, read-only) |
| `NationalParks.IsValidParkTileEx(player, plot, flags)` | the vanilla rule re-implemented; flag 1 ignores the district check, flag 2 the terrain/appeal requirement |
| `NationalParks.SetRules(minTiles, maxTiles, minAppeal, maxAppeal, flags, {districtIndex, ...} [, {wonderBuildingIndex, ...}])` | replaces the tile rule everywhere while active. Flags: 1 improved tiles allowed, 2 mountains always fit, 4 natural wonders always fit. A tile with a world wonder is valid only if its wonder is in the 7th argument; a district tile only if its district is listed; **appeal must be in `[minAppeal, maxAppeal]` for every tile** (plain mountain and natural wonder tiles are exempt when their flag is set). Cleared at every game load. |
| `NationalParks.ClearRules()`, `GetRules()` | `GetRules()` returns active, minTiles, maxTiles, minAppeal, maxAppeal, flags (vanilla values when inactive; also in the UI state) |
| `RegisterProcessor("NationalParkTileValid", fn)` | optional Lua override of a tile (`map.PlotIndex`, `PlayerId`, `Valid`; set `Valid` and `Handled = 1`). Runs only on the simulation thread holding the GameCore lock and for tiles owned by the player; the UI highlight uses the native rules only. Not tested in game. |

`DesignateCustom` works by letting the game's own `DesignatePark` create the record with the events suppressed (`Map::Player::Visibility::Manager` byte +0x2b), overwriting the plot list in place, appending further plots, restoring the flag and sending one `RestoreVisualState`.

## Pitfalls found while building it
* **Growing the plot vector:** the game calls `eastl::vector<int>::DoInsertValue` only when the vector is full (it then reallocates); with spare room it appends inline. Calling it at the end position with spare room does a `memmove` of size -4 and corrupts the heap (*seen live: crash 0xc0000374 when appending the sixth plot*). Append inline when there is room, call the game's function only when full, so that its allocator owns the buffer.
* **HavokScript raises on `tonumber(nil)` and `tostring(nil)`** instead of returning nil: guard values that may be unset (property reads, configuration values).
* **`UI` can be nil inside a button callback** of a control that was re-parented into another screen (seen with the picker's button in the unit panel): capture the globals the callbacks use as locals when the script loads.
* The UI thread must never enter gameplay Lua; the rule hook therefore only calls a processor when it holds the GameCore lock.

## The mod: Better National Parks
`BetterNationalParks` (in the Dev CE release zip; replaces the earlier `DevCE_ParkRules` + `DevCE_ParkPicker`) puts this on top of the natives:
* **Rules as data:** tables `NationalParkTypes` (min/max tiles, min/max appeal, allow improvements, mountains, natural wonders), `NationalPark_ValidDistricts` and `NationalPark_ValidWonders`, read for the row `NATIONAL_PARK_DEFAULT` by a gameplay script that calls `SetRules`. District and wonder names are stored as plain text and resolved in Lua at run time; do not `SELECT` them from `Buildings` or `Districts` in SQL, because content that loads later (a DLC wonder, a mod's wonder) would be silently missing. Defaults: appeal 2 or more, Preserve and six landmark wonders. The rule also changes the vanilla action and the AI.
* **Custom shapes (human player):** a second button for Naturalists, Mountie-like units and any unit with `ParkCharges`; click 1 to 32 touching tiles of one city; the picker sends the choice to the gameplay script (`UnitManager.RequestCommand`, `EXECUTE_SCRIPT`), which re-checks everything and calls `DesignateCustom`.
* **Setup-screen options** (Advanced Setup): custom shapes on/off, min/max tiles, World Wonders (Landmark / All / None / Custom multi-select) and Districts (Preserve / None / Custom multi-select). Front-end parameters are defined in the Config database through `FrontEndActions`; a parameter with `Array=1` opens the game's multi-select window, whose items come from `DomainValues` rows. The expansion text is not loaded in the setup screen, so the item names need their own text rows. The values reach the gameplay script through `GameConfiguration.GetValue`.

## Tested
In game on build 26595377 (single player): setup options reaching the rules, vanilla action and custom button, parks of 1, 2, 5, 6 and 12 tiles, Preserve and wonder tiles in a park, appeal gating of wonder and district tiles, a non-Canada Mountie with both buttons, end turn, save and reload. **Not tested:** the AI with relaxed rules, tourism numbers of big parks, parks across several cities, multiplayer, the processor override, other builds.

*Addresses (RVA in `GameCore_XP2_FinalRelease.dll`, build 26595377, as used by Dev CE 0.9.0): `GetNationalParks` 0x2363c0, `DesignatePark` 0x235810, `FindPark` 0x2362a0, `RestoreVisualState` 0x2389d0, `IsValidParkTile` 0x237840, `Plot::CityAttributes::GetDistrictType` 0x5e720, `Plot::IsNaturalWonder` 0x60280, vector `DoInsertValue` 0x34df40.*
