---
title: Gates and purchase rules - buildings, techs and civics, gold purchase, founder uniques (Dev CE)
order: 72
---
# Gates and purchase rules: building gates, tech and civic gates, gold purchase, founder uniques

**Availability.** These four natives need the Dev CE GameCore mod **0.9.0-experimental** or newer (Steam build 26595377) and are meant for **single player**. The features were written by **slothoth** (his branches), merged and ported to this build by **cru121**. Without a mod that feeds them they do nothing:
* Building gates and tech/civic gates are inert until a mod inserts rows into `DevCE_BuildingGates`, `DevCE_TechnologyGates` or `DevCE_CivicGates` (the tables are created by the helper mods; the code logs "gates off" when no rows or no table exist).
* Gold purchase is inert until the game capability `CAPABILITY_DEVCE_GOLD_PURCHASE` is on, and then until a city property unlocks an item.
* Founder uniques are inert until a city has the property `DEVCE_BUILD_FOUNDER_UNIQUES` >= 1 (no capability is checked for this feature in the code).

All four read **city or player properties**, which a mod sets with ordinary modifiers (`MODIFIER_SINGLE_CITY_ADJUST_PROPERTY`, or a DynamicModifier of `EFFECT_ADJUST_CITY_PROPERTY` on `COLLECTION_PLAYER_CITIES`; for players `EFFECT_ADJUST_PLAYER_PROPERTY`). A modifier with requirements takes its amount off again when they stop holding, so a gate can open and shut during play. A property counts as set when it holds a number >= 1.

## Building and wonder gates (progress kept)
**What it does.** A row in `DevCE_BuildingGates` makes a building or wonder buildable only in a city whose property is >= 1. Several rows on one building must all hold. While a gate is shut the item is **listed greyed out** in the production panel with the row's `Description` as the reason, and cannot be queued, bought or granted for free.

**Progress is kept.** The game re-checks the front item of the queue every turn (`BuildQueue::AddProgress`) and when an item reaches the front (`OnNewFrontBuilding`). A building that fails is only taken off the queue (`OnRemoveFrontEntry` plus `PopFront`); its progress and a wonder's partly built model on its tile stay. Only `BuildQueue::JustRemoveBuilding` clears them, and the gates never call it (the code comment names `MODIFIER_PLAYER_ADJUST_VALID_BUILDING` and the World Congress production ban as things that do, through `RemoveBuilding`).

**How to switch it on.** Table `DevCE_BuildingGates` (BuildingType, Property, Description; primary key BuildingType plus Property). `Description` is a LOC key, default `LOC_DEVCE_BUILDING_GATE_SHUT`. From the test mod (Monument, Pyramids, Oracle need `DEVCE_TEST_GOD_KING`, set on every city while the God King policy is slotted):
```sql
INSERT INTO DevCE_BuildingGates (BuildingType, Property, Description) VALUES
	('BUILDING_MONUMENT', 'DEVCE_TEST_GOD_KING', 'LOC_DEVCE_TEST_NEEDS_GOD_KING'),
	('BUILDING_ORACLE', 'DEVCE_TEST_GOD_KING', NULL);
-- modifier: EFFECT_ADJUST_CITY_PROPERTY on COLLECTION_PLAYER_CITIES, Key = DEVCE_TEST_GOD_KING, Amount = 1,
-- attached with PolicyModifiers to POLICY_GOD_KING
```
**Engine facts used.**
* The tables are read after `DefinitionCollectionBuilder::BuildCollection<BuildingCondition>` (RVA 0x7554c0) through the builder's database connection; the building index is its position in `Buildings` by rowid. Gates are therefore read when the database loads.
* `BuildQueue::CanConstruct` is hooked twice. Outer (0xf7100; UI, queueing, purchases, free buildings): with the gate shut the listing test (`exclusionTest`) passes, the full test fails and adds the Description to `CityCommandResults.FAILURE_REASONS` (`Reporting::AddString`). Inner (0xf61c0; per-turn check, new front item, AI): returns false, except when called from the outer one (return address 0xf7277), which decides for its callers.
* City properties are read from `City::Instance +0x1a0` (a `Data::VariantMap`, vtable +0x60 = get), the same map Lua `City:GetProperty` uses; the queue's city is at `BuildQueue +0x1e8`.

**Limits.** Hooks are only installed if every checked byte pattern matches (otherwise "building gates not available" in the log). If the localization string constructor is not found, gated buildings show no reason text. Hooks stay installed when Dev CE restarts in the same process.

## Tech and civic gates (player property)
**What it does.** A row in `DevCE_TechnologyGates` (TechnologyType, Property, Description) or `DevCE_CivicGates` (CivicType, Property, Description) adds a condition on top of the normal prereqs: the **player** property must be >= 1. Several rows on one item must all hold. Patterns given in the code comments: policy-locked (a `PolicyModifiers` row adds 1 while slotted), cross-tree (a `CivicModifiers` row adds 1 to a tech's gate, or `TechnologyModifiers` for a civic's), one of several (no prereq rows; each candidate tech adds 1 through `TechnologyModifiers`).

**Openers.** The techs and civics whose `TechnologyModifiers` / `CivicModifiers` add a positive Amount to a gate's key through `EFFECT_ADJUST_PLAYER_PROPERTY` on `COLLECTION_OWNER` are the gate's "openers" (read from the database, no table of their own). Note that the shipped SQL comment and test mod use the base game's `MODIFIER_PLAYER_ADJUST_PROPERTY` (Key, Amount) for the same effect.

**How to switch it on.** From the test mod: Archery needs Discipline slotted; The Wheel loses its Mining prereq and opens with Bronze Working or Astrology; Irrigation needs the civic Craftsmanship; Military Tradition needs the tech Bronze Working.
```sql
INSERT INTO DevCE_TechnologyGates (TechnologyType, Property, Description) VALUES
	('TECH_ARCHERY', 'DEVCE_TEST_GATE_ARCHERY', 'LOC_DEVCE_TEST_GATE_ARCHERY');
INSERT INTO PolicyModifiers (PolicyType, ModifierId) VALUES ('POLICY_DISCIPLINE', 'DEVCE_TEST_GATE_ARCHERY_DISCIPLINE');
```
`Description` is optional (default `LOC_DEVCE_GATE_SHUT`); the helper mod's `ToolTipLoader_DevCE_TechGates.lua` adds the shut gates' lines to tech and civic tooltips.

**Hooks (all pass through when no gate rows exist).**
* `Techs::CanResearch` (0x3325f0) and `Culture::CanProgress` (0x27c320): false while a gate is shut. The AI, choosers, Lua and free techs all ask these.
* `ChangeResearchProgress` (0x332840) / `ChangeCulturalProgress` (0x27c600): if the head item's gate shut (policy unslotted), the queue is cleared instead, so the points go to overflow and the player chooses again. Progress already made stays on the item.
* `SetResearchingTech` / `SetProgressingCivic` (queue and single versions): the queue is cut at the first item whose gate is shut and not opened by an earlier item of the same queue; nothing left means the request is ignored. A queue-changed event is sent afterwards.
* Lua `IPlayerTechs:GetResearchPath` / `IPlayerCulture:GetCivicPath` are **replaced**: prereqs first, a shut gate goes through its cheapest opener in the same tree. With no opener in that tree (only a civic or policy), there is no path and the click in the tree does nothing.
* AI `TechTreeAnalysis::Evaluate` and `CivicAnalysis::Execute`: a target whose next step cannot be taken gets the first step of our path, or is marked unreachable (value INT_MIN/8) so the AI does not fall back to a random tech.

**Engine facts used.** Gate tables are read after `BuildCollection<TechnologyPrereq>` (0x769100); item index = position by rowid in `Technologies` / `Civics`. Player properties live at `Player::Instance +0x518`. Gates are read when the database loads.

## Gold purchase of build-only items
**What it does.** A unit or building without a `PurchaseYield` (build only; **wonders excluded**) can be bought with gold in a city whose property unlocks it, in the way the game's faith purchase effects do. Property keys (prefix `DEVCE_GOLD_PURCHASE_`), each >= 1:
* `DEVCE_GOLD_PURCHASE_<UnitType>` (one unit), `..._<PromotionClass>` (every unit of the class), `DEVCE_GOLD_PURCHASE_ALL_UNITS`.
* `DEVCE_GOLD_PURCHASE_<BuildingType>` (one building), `..._<PrereqDistrict>` (every building of that district), `DEVCE_GOLD_PURCHASE_ALL_BUILDINGS`.

**How to switch it on.** Add the capability, then set a city property. The test mod unlocks Walls, Castle and the other build-only city-centre buildings in every city, and the Spy in the city that has the Palace (a requirement set on the modifier):
```sql
INSERT OR IGNORE INTO Types (Type, Kind) VALUES ('CAPABILITY_DEVCE_GOLD_PURCHASE', 'KIND_CAPABILITY');
INSERT OR IGNORE INTO GameCapabilities (GameCapability) VALUES ('CAPABILITY_DEVCE_GOLD_PURCHASE');
-- modifier Key = DEVCE_GOLD_PURCHASE_DISTRICT_CITY_CENTER, Amount = 1, via TraitModifiers on TRAIT_LEADER_MAJOR_CIV
```
**UI.** The mod `DevCE_GoldPurchase` replaces the `ProductionPanel` context (`LuaReplace`; it includes the base panel and wraps only `GetData`) and adds the unlocked items to `BuildingPurchases` / `UnitPurchases` using the base `ComposeBldgForPurchase` / `ComposeUnitForPurchase` with `YIELD_GOLD`. Its own description warns that it does not work with other `ProductionPanel` replacements (CQUI, BBG, Babylon Heroes mode); copy the wrapper into those instead. The Lua check mirrors the engine rule, but the engine has the last word via `CityManager.CanStartCommand`.

**Engine facts used.** The game does not check `PurchaseYield` when a purchase starts (only the production panel and the AI do), so the native adds the rule:
* `City::Commands::Purchase::CanStart` (base 0x680310, XP1 0x71be60, XP2 0x74ef80), after the original returned true: a gold purchase of a unit or building is allowed only if its PurchaseYield is gold, or it is build-only, not a wonder and unlocked in that city. Faith purchases and other kinds are unchanged. With the capability off, the game's own rule applies.
* `AI::Control::UnitRequestContract::Validate(Economic&)` (0x3fb0a0): the AI also accepts unlocked items, in the contract's city or in any city when it has none; the contract's district must be -1. The purchase itself still only goes through where the item is unlocked.
* Purchase parameters: kind at +0x18 (0 unit, 1 building), type at +0x1c, yield at +0x24; wonder flag is `flags & 0x10` at building def +0x159 ("as the AI tests it"). Property names are hashed with `MakeHash`.

## Founder uniques
**What it does.** A city whose property `DEVCE_BUILD_FOUNDER_UNIQUES` is >= 1 and that was **founded by another player** can also train the units and construct the buildings its founder could, as if its owner were the founder's civilization and leader: the founder's unique units and buildings, and generics the founder has not replaced. Nothing is replaced for the owner: a city founded by a civilization whose unique unit replaces the Swordsman offers that unit and the owner's Swordsman. All other conditions (techs, civics, districts, resources, limits) are the owner's as usual.

**How to switch it on.** Set the city property. The test mod gives every major civ's cities the property (only cities founded by someone else are affected); a real mod would give it to one civilization through its TraitModifiers, or add requirements:
```sql
-- Key = DEVCE_BUILD_FOUNDER_UNIQUES, Amount = 1, EFFECT_ADJUST_CITY_PROPERTY on COLLECTION_PLAYER_CITIES,
INSERT INTO TraitModifiers (TraitType, ModifierId) VALUES ('TRAIT_LEADER_MAJOR_CIV', 'DEVCE_TEST_BUILD_FOUNDER_UNIQUES');
```
**Engine facts used.**
* The engine keeps per player "which version of this unit or building can I ever build" (`Player::Units +0x128`, `Player::Cities +0x150`: the item itself, the player's replacement, or -1 for another civilization's unique). The one test in `City::BuildQueue::CanTrain` (0xf86d0) and in the inner `CanConstruct` (0xf61c0) is `cmp [version + item*4], item` then `jne fail`.
* Both `jne` instructions (0xf8762 and 0xf62c0) are patched to jump to a small generated stub that calls Dev CE first: the city has the property and the founder's table maps the item to itself, then go on as if the owner's did; otherwise the original fail target (0xf979f / 0xf70e5). The founder is read at `City +0xf0` (original owner, Lua `City:GetOriginalOwner`), the owner at `City +0xd8`, founder's player via `EditPlayer` (0x44f00). Every caller of those two functions follows (production panel, queueing, purchase, per-turn check).

**Limits.** The AI does not look for founder uniques by itself, because its unit and building lists use the owner's table. A city whose founder equals its owner is not affected. The patches stay in place when Dev CE restarts in the same process.

## Tested
Lightly tested in game by cru121; **no detailed results were recorded**, so nothing here is claimed as verified. What each test mod sets up:
* `DevCE_BuildingGatesTest`: Monument, Pyramids and Oracle gated by `DEVCE_TEST_GOD_KING`, which every city gets while POLICY_GOD_KING is slotted (Oracle uses the default reason text).
* `DevCE_TechGatesTest`: the four gates described above (policy-locked, one of several, civic to tech, tech to civic); Ancient era tech and civic costs (and Military Tradition) are divided by 5 so the gates can be tried quickly.
* `DevCE_GoldPurchaseTest`: capability on, city-centre buildings unlocked in all cities, Spy unlocked in the Palace city, and a Lua script that gives the human player 1500 gold once at the start of the first turn.
* `DevCE_FounderUniquesTest`: `DEVCE_BUILD_FOUNDER_UNIQUES` = 1 on every major civ's cities.

*Key addresses (named constants in the code, build 26595377): BuildCollection<BuildingCondition> 0x7554c0, BuildQueue::CanConstruct outer 0xf7100 and inner 0xf61c0, BuildCollection<TechnologyPrereq> 0x769100, Purchase::CanStart 0x680310 / 0x71be60 / 0x74ef80, CanTrain 0xf86d0.*
