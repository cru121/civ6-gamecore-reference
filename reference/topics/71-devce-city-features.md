---
title: City features - workable radius, city-centre specialists, district citizens, food to production (Dev CE)
order: 71
---
# City features in Dev CE: workable radius, city-centre specialists, district citizens, food to production

**Availability.** These four features need the **Dev CE GameCore mod 0.9.0-experimental or newer** (Steam build 26595377, single player). They were written by **slothoth** in his branches and merged and ported to Dev CE by **cru121**. Loading Dev CE alone changes nothing: each feature is inert until a mod switches it on.

* City radius, district citizens and food to production need a **game capability** in the database when the game starts (`CAPABILITY_DEVCE_CITY_RADIUS`, `CAPABILITY_DEVCE_DISTRICT_CITIZENS`, `CAPABILITY_DEVCE_FOOD_PRODUCTION`) and then a **property** to do anything per city or district.
* City-centre specialists need no capability: the switch is the GlobalParameter `DEVCE_CITY_CENTER_SPECIALISTS` = 1 plus rows in the `DevCE_Specialists` tables.
* A capability is a `Types` row of `KIND_CAPABILITY` plus a `GameCapabilities` row. Use `INSERT OR IGNORE` so several mods can add it. The answer is read once per game and kept, so a game started without the capability never gets the feature (the save keeps its mods).
* All four set properties with the game's own `EFFECT_ADJUST_CITY_PROPERTY` / `EFFECT_ADJUST_DISTRICT_PROPERTY` (arguments `Key`, `Amount`). The game has no modifier type for them, so the mod adds a `DynamicModifiers` row (as in the examples).

## 1. City workable radius (extra rings)

**What it does.** A city normally works, buys and swaps tiles within 3 of the centre (37 plots). With the capability, a city with the property `DEVCE_CITY_EXTRA_RINGS` uses radius 3 + that value, **capped at 5** (negative values count as 0). Properties add up, so a civ trait with +1 and a wonder with +1 give radius 5, while other cities building the wonder get 4. Culture border growth prefers tiles inside the radius.

**Switch on.** Capability `CAPABILITY_DEVCE_CITY_RADIUS`, then raise the property with `EFFECT_ADJUST_CITY_PROPERTY` (from DevCE_CityRadiusTest):

```sql
INSERT OR IGNORE INTO Types (Type, Kind) VALUES ('CAPABILITY_DEVCE_CITY_RADIUS', 'KIND_CAPABILITY');
INSERT OR IGNORE INTO GameCapabilities (GameCapability) VALUES ('CAPABILITY_DEVCE_CITY_RADIUS');
INSERT INTO DynamicModifiers (ModifierType, CollectionType, EffectType) VALUES
  ('MODIFIER_DEVCE_RADIUS_TEST_PLAYER_CITIES_ADJUST_PROPERTY', 'COLLECTION_PLAYER_CITIES', 'EFFECT_ADJUST_CITY_PROPERTY');
-- Modifier arguments: Key = DEVCE_CITY_EXTRA_RINGS, Amount = 1
INSERT INTO TraitModifiers (TraitType, ModifierId) VALUES ('TRAIT_LEADER_MAJOR_CIV', 'DEVCE_TEST_RADIUS_TRAIT');
INSERT INTO BuildingModifiers (BuildingType, ModifierId) VALUES ('BUILDING_PYRAMIDS', 'DEVCE_TEST_RADIUS_WONDER');
```

**Engine facts the code relies on.**
* Every city's per-tile arrays (citizens, AI plot data) are sized from the plot count when the city is founded. With the capability the count is 91 (radius 5) for **every** city of the game, which is why it is a capability and not a per-city switch.
* `CityHexspace::ComputePlotsFromRadius(2)` (always called as R(2) + 18 by every "plots in radius 3" loop) returns 73, so 91 plots.
* `CityHexspace::Get/EditPlotFromCityIndex` return null beyond the city's radius; ring 5 (indices 61..90) is computed by Dev CE, because the game's tables stop at ring 4 (61 entries). The ring order is the game's; Dev CE rebuilds it and compares it with the game's tables at start-up (a mismatch switches the feature off).
* `CityHexspace::GetCityIndexFromPlot`: ring 5 added to the core function; the per-city overloads give -1 beyond the city's radius.
* `City::Citizens::RemoveAllCitizenWorkers`: before it runs, locked workers beyond the radius are let go (the game reallocates every turn, so a smaller radius takes effect at the next turn). This hook is shared with city-centre specialists (`CitizenWorkersHook.cpp`; MinHook allows one hook per function).
* Three jumps are redirected to small stubs: `City::Gold::GetPlotPurchaseCost` (the "distance > CITY_MAX_BUY_PLOT_RANGE" test), `City::Culture::CanSwapPlotFromCity` ("distance > 3"), `City::Culture::GetBuyablePlotList` ("distance <= 3"). Each now allows distances up to the city's radius.
* City properties are read from the city's `VariantMap` at offset 0x1a0 (vtable +0x60 = get by key hash); only number values count.
* The code checks the bytes of every function and patch site first; any mismatch logs "city radius not available" and nothing is installed.

**Limits and pitfalls (from the code).** District and wonder placement stay at radius 3 (`CanHaveDistrict` / `CanHaveWonder` have their own distance check). The cap is 5. Without the capability at game start the radius stays 3 even if the property is set.

## 2. Specialists worked in the city centre

**What it does.** An alternate citizen mode. Each city has slots per specialist type, and a citizen in a slot gives that type's yields. The game's own auto-assign fills the slots together with tiles (growth, city focus, governors, AI). Mode 0 (default) leaves the game's normal specialists untouched; every hook does nothing in mode 0.

**Switch on.** `UPDATE GlobalParameters SET Value = 1 WHERE Name = 'DEVCE_CITY_CENTER_SPECIALISTS'` (the row is added with value 0 by DevCE_CitySpecialists). It is read when the database loads (hook on `GlobalParameters::Initialize`), so change it only between games. Tables, created by the DevCE_CitySpecialists mod (needs the mod's SQL for the tables to exist):

| Table | Columns |
|---|---|
| `DevCE_Specialists` | `SpecialistType` (key), `Name` (LOC key, UI), `Icon` (UI), `Color` (UI: a colour name or "R,G,B"), `SortIndex` |
| `DevCE_Specialist_Yields` | `SpecialistType`, `YieldType`, `YieldChange` |
| `DevCE_Specialist_GreatPersonPoints` | `SpecialistType`, `GreatPersonClassType`, `PointsPerTurn` |

Types are read ordered by `SortIndex, rowid`. City properties (`<Type>` = the `SpecialistType`):

| Property | Meaning |
|---|---|
| `DEVCE_SPECIALIST_SLOTS_<Type>` | slots; set by modifiers, read only by Dev CE |
| `DEVCE_SPECIALISTS_<Type>` | working specialists (locked and auto); written by Dev CE in a reallocation, read only for mods |
| `DEVCE_SPECIALISTS_LOCKED_<Type>` | the player's lock request, applied at the next reallocation (a raw write alone changes nothing) |
| `DEVCE_SPECIALIST_YIELD_<Type>_<YieldType>` | extra yield per specialist of that type, on top of the table; base yields only |

Example (DevCE_CitySpecialistsTest): five types (Scientist, Engineer, Merchant, Artist, Priest), 2 Scientist and 2 Engineer slots and 1 of each other type per city of every major civ (a `TraitModifiers` row on `TRAIT_LEADER_MAJOR_CIV` per slot modifier), yields such as `('SPECIALIST_SCIENTIST', 'YIELD_SCIENCE', 2)`, and great person points per specialist.

**Gameplay Lua.** `CitySpecialists.SetLocked(playerId, cityId, specialistType, count)` sets the lock request and reallocates the city at once; it returns the working count, or -1 (mode off, unknown type or city). `CitySpecialists.IsEnabled()` returns a boolean. UI scripts read the city properties and send `UI.RequestPlayerOperation(player, PlayerOperations.EXECUTE_SCRIPT, { OnStart = "DevCE_SetSpecialistLock", CityID, SpecialistType, Count })` to a gameplay script that calls `SetLocked`; DevCE_CitySpecialists ships that script and a UI panel.

**Engine facts the code relies on.**
* `RemoveAllCitizenWorkers`: before it, room is computed from locked tiles; after it, the working count restarts from the locked request (trimmed to slots and to population minus locked tiles), taken from the free citizens.
* `TryAssignAllWorkers`: a jump at 0x110f9a replaces the call to the knapsack (`bounded_knapsack<SimpleScoring>`) with Dev CE code that adds one candidate per open slot and applies the chosen specialists. Before it, free citizens are capped (growth skips `RemoveAll`); after it, open slots are filled when the game had no tile candidates.
* `City::GetYieldFromTiles`: after it, adds specialists times their yields.
* `AdjustCityProperty::Apply/Remove`: when a slot key falls below the working count, the city is reallocated at once; slots gained are filled at the next reallocation.
* `GreatPeoplePoints::CalculatePointsPerTurn` (patched at 0x2e23f1, resuming at 0x2e23f8: these are the constants the code installs the patch with; a comment in the header still says 0x2e2a81, which the code does not use): adds the city's specialist points before the city's percent modifier, like `District_CitizenGreatPersonPoints`. The class index is the row position in `GreatPersonClasses` by rowid.
* After a citizen change Dev CE sends the same report event the game's `ManageCitizen` sends, so the UI redraws.

**Limits (from the code).** At most 32 specialist types, 8 yield rows and 16 great person point rows per type, 6 base yields (`YIELD_FOOD` to `YIELD_FAITH`); names must fit the internal buffer. If `DevCE_Specialists` is missing or empty the mode stays off (logged in `DevBridge.log`).

## 3. District citizen slots and yields

**What it does.** Two reserved **district** properties change how many citizens a district tile takes and what each gives:
* `DEVCE_CITIZEN_SLOTS`: the district tile takes that many more citizens (total never below 0).
* `DEVCE_CITIZEN_<YieldType>`, for example `DEVCE_CITIZEN_YIELD_SCIENCE`: each citizen working the district gives that much more of the yield. The six base yields are covered (`YIELD_FOOD`, `PRODUCTION`, `GOLD`, `SCIENCE`, `CULTURE`, `FAITH`).

**Switch on.** Capability `CAPABILITY_DEVCE_DISTRICT_CITIZENS`, then set the properties with `EFFECT_ADJUST_DISTRICT_PROPERTY` (from DevCE_DistrictCitizensTest, which makes a Campus take 1 more citizen, +1 Science and +1 Gold each, via policy `POLICY_GOD_KING` and, for testing, `TRAIT_LEADER_MAJOR_CIV`):

```sql
INSERT INTO DynamicModifiers(ModifierType, CollectionType, EffectType) VALUES
  ('MODIFIER_DEVCE_TEST_PLAYER_DISTRICTS_ADJUST_PROPERTY', 'COLLECTION_PLAYER_DISTRICTS', 'EFFECT_ADJUST_DISTRICT_PROPERTY');
-- Modifier arguments: Key = DEVCE_CITIZEN_SLOTS, Amount = 1; Key = DEVCE_CITIZEN_YIELD_SCIENCE, Amount = 1
```

**Engine facts the code relies on.**
* `Rules::Yields::GetYield`, district branch: the value is `District_CitizenYieldChanges` + the property (then `Building_CitizenYieldChanges`). One jump at 0x37e6c4, after the `District_CitizenYieldChanges` loop.
* `City::Citizens::GetPlotWorkerCapacity`: `Districts.CitizenSlots` + the property (then the buildings' `CitizenSlots`). One jump at 0x110238.
* District properties live at district offset 0x378 (`m_kProperties`), read by the same number test as city properties; the properties are saved with the district.
* Yield indices are not fixed: they are filled when the database loads, so the index to key table is built on first use, once the six names give six different indices.
* Both readers are bytes-checked first; a mismatch switches both off.

**Pitfalls.** In the test mod's own comment, a Campus has no `CitizenSlots` of its own, so before a Library it normally takes no citizens; the slot property is what lets it take one. `GetYield` is a hot path, so the capability test comes first.

## 4. Food to production

**What it does.** While a city whose property `DEVCE_FOOD_TO_PRODUCTION` is >= 1 produces a **unit**, its excess food (food yield minus what the citizens eat) is added to production instead of growth:
* production gets the excess food, added to the base before the modifiers, so city percent and percent-toward-units bonuses apply;
* food is lowered to exactly what the citizens eat (no growth, no starvation).

Both show as their own tooltip lines, `LOC_DEVCE_PRODUCTION_FROM_FOOD` and `LOC_DEVCE_FOOD_TO_PRODUCTION`; the mod must supply the text (the test mod's `Text.sql` has English strings). Buildings and districts are not affected.

**Switch on.** Capability `CAPABILITY_DEVCE_FOOD_PRODUCTION`, then `EFFECT_ADJUST_CITY_PROPERTY` with `Key` = `DEVCE_FOOD_TO_PRODUCTION`, `Amount` = 1. The test mod gives it to every major civ (`TRAIT_LEADER_MAJOR_CIV`) and also through `POLICY_DISCIPLINE`.

**Engine facts the code relies on.**
* `City::Instance::CalculateYield(yield, production kind, track)` computes every city yield; the kind is the current item's, so the build step, `GetYield` (UI, AI, growth) and the tooltips all pass through it. It is hooked for food and production when the kind is "unit" (`GetCurrentProductionKind` = 0x15d11e18).
* The turn runs the build step before growth. `BuildQueue::DoTurnActivate` records whether this turn's food went into a unit; `Growth::DoCityGrowth` / `AddGrowth` then add growth from the unconverted food unless it did (using `GetOverallGrowthModifier`). This also makes growth independent of the city yield cache.
* The food reduction searches for the smallest base whose modified value reaches the citizens' consumption (`Rules::Economic::GetFoodConsumption`), fixed-point (FixedPoint<8>) arithmetic.

## Tested
Lightly tested in game by cru121; no detailed results are recorded, and none of the behaviour above is claimed as verified here. The test mods set up:
* **DevCE_CityRadiusTest:** the capability; +1 ring for every major civ (radius 4); the Pyramids give +1 more to all the owner's cities (radius 5); Pyramids cost 1 production, need no tech and may be placed on grass, plains, desert hills and tundra tiles; the human gets 5000 gold on turn 1 to buy tiles. Needs a new game.
* **DevCE_CitySpecialistsTest** (with DevCE_CitySpecialists): mode on, five types, slots and yields as in section 2, plus Urban Planning (+2 Scientist slots) and Discipline (+3 Science per Scientist) as removable/extra modifiers.
* **DevCE_DistrictCitizensTest:** Campus +1 slot, +1 Science, +1 Gold per citizen; Campus costs 1 and needs no tech.
* **DevCE_FoodProductionTest:** `DEVCE_FOOD_TO_PRODUCTION` = 1 in all major civ cities, plus the two tooltip strings.

*Key addresses (RVAs, build 26595377):* ComputePlotsFromRadius 0x447d0, EditPlotFromCityIndex 0x44980, RemoveAllCitizenWorkers 0x110760, TryAssignAllWorkers 0x110ba0, knapsack patch 0x110f9a, GetYieldFromTiles 0x133780, GetYield patch 0x37e6c4, GetPlotWorkerCapacity patch 0x110238, CalculateYield 0x12ff20, BuildQueue::DoTurnActivate 0xfc690, DoCityGrowth 0x123460.
