---
title: Unit features - upgrade rules, upgrade fallback, command actions, unit property requirement (Dev CE)
order: 73
---
# Unit features in Dev CE: upgrade rules, upgrade fallback, command actions, REQUIREMENT_UNIT_PROPERTY_MATCHES

**Availability.** These natives need the **Dev CE GameCore mod 0.9.0-experimental or newer** (Steam build 26595377), **single player only**. The features are by **slothoth** (his branches), merged and ported by **cru121**. Nothing changes in a game until a mod switches it on:
* Upgrade rules and upgrade fallback act only in a game whose database has their game capability (`CAPABILITY_DEVCE_UPGRADE_RULES`, `CAPABILITY_DEVCE_UPGRADE_FALLBACK`). Without it the hooks pass straight through to the game's own code. The capability must be in the database when the game starts.
* Unit command actions do nothing until a script calls `UnitCommandActions.Define`. `SetGreatPersonType` does nothing until a script calls it.
* `REQUIREMENT_UNIT_PROPERTY_MATCHES` is a new requirement type, registered at startup; it only matters once a requirement row uses it.
* The effect `EFFECT_DEVCE_UNIT_UPGRADE_OUTSIDE_TERRITORY` needs no capability (the code comment says so).

All tables below are **mod-defined** (the shipped mods create them with `CREATE TABLE IF NOT EXISTS`); the DLL only sees what the mod's gameplay Lua pushes through the `UnitUpgradeRules` / `UnitCommandActions` tables.

## 1. Unit upgrade rules
Extra rules for upgrading a unit (gold upgrade, `UnitCommandTypes.UPGRADE`):
1. **Build-disabled targets:** a unit cannot upgrade into a unit type its owner has build-disabled (`MODIFIER_PLAYER_UNIT_BUILD_DISABLED`). Active whenever the capability is on, with or without the shipped mod.
2. **Minimum experience level** per step (unit -> upgrade unit): Lua `unit:GetExperience():GetLevel()` (1 for a new unit, +1 per promotion earned with experience; free promotions do not count).
3. **Building prerequisite:** an upgrade unit with `Unit_BuildingPrereqs` needs the unit to stand inside the borders of one of its owner's cities that has one of those buildings (built, not pillaged, as in `City::BuildQueue::CanTrain`; the `NumSupported` limit is not applied). A foreign, allied or city-state city never counts.
4. **Alternative upgrades:** extra first steps besides the `UnitUpgrades` row.
5. **Upgrade outside territory** by effect (below).

**How to switch on.** Add the capability (`INSERT OR IGNORE INTO Types ... 'CAPABILITY_DEVCE_UPGRADE_RULES', 'KIND_CAPABILITY'` and `INSERT OR IGNORE INTO GameCapabilities`). The mod `DevCE_UnitUpgrades` does this and adds:
* `DevCE_UnitUpgradeRequirements (Unit, UpgradeUnit, MinLevel)`, one row per step. Its Lua pushes it with `UnitUpgradeRules.SetMinLevel(fromIndex, toIndex, level)` (level <= 1 removes a rule). Unique units (`UnitReplaces`) inherit the rule of the unit they replace, on either side, unless they have a row of their own (this is the mod script, not the DLL).
* `DevCE_UnitAltUpgrades (Unit, UpgradeUnit)`, pushed with `UnitUpgradeRules.AddAltUpgrade(fromIndex, toIndex)` (returns whether the feature is available in this build). Unique units get the choices of the unit they replace unless they have their own rows.
* `GlobalParameters` `DEVCE_UPGRADE_NEEDS_PREREQ_BUILDING` (1 = on, the default of the mod), passed to `UnitUpgradeRules.SetBuildingRule(on)`. The building rule is off in the DLL until Lua switches it on.
* Other Lua: `GetMinLevel`, `Clear`, `GetBuildingRule`, `ClearAltUpgrades`, `GetAltUpgrades(fromIndex)`. The rules are forgotten with each game (`ResetForNewGame`), so the script must run at every game start and load.

```sql
INSERT INTO DevCE_UnitUpgradeRequirements (Unit, UpgradeUnit, MinLevel) VALUES ('UNIT_SLTH_ADEPT', 'UNIT_SLTH_MAGE', 5);  -- example in the mod, commented out
INSERT INTO DevCE_UnitAltUpgrades (Unit, UpgradeUnit) VALUES ('UNIT_WARRIOR', 'UNIT_ARCHER');  -- DevCE_UnitAltUpgradeTest
```

**Upgrade outside friendly territory.** The mod SQL defines `MODIFIER_DEVCE_UNIT_UPGRADE_OUTSIDE_TERRITORY` (collection owner, the unit itself) and `MODIFIER_DEVCE_PLAYER_UNITS_UPGRADE_OUTSIDE_TERRITORY` (collection player units; a `SubjectRequirementSetId` may pick some), both on `EFFECT_DEVCE_UNIT_UPGRADE_OUTSIDE_TERRITORY` (a `KIND_EFFECT` Types row is needed, see the test mod). The effect is the game's `EFFECT_ADJUST_UNIT_PROPERTY` with a fixed key and amount: Apply adds 1 to the unit property `DEVCE_UPGRADE_OUTSIDE_TERRITORY`, Remove takes 1 away (a count, so two sources and one removed still leave it on). Unit properties are saved, so it survives save and load. A unit with the property above 0 counts as in its own territory for the upgrade check only; all other rules still apply.

**Behaviour the code shows.**
* The game picks the target in `Rules::Units::GetAvailableUpgrade`. Dev CE walks the same `UnitUpgrades` chain and stops before a step the rules block. A blocked **first** step stays the target, so the panel still shows the upgrade with the reason in red while `CanUpgrade` says no. A blocked later step ends the walk before it (level 5 can reach the Mage, level 7 the Archmage, as in the mod's example).
* Alternative upgrades travel in the UPGRADE command's request int (`PARAM_CHOICE`, request +0x18) as first-step unit index + 1 (0 = default). Both the base and the XP2 Upgrade command `Start` are hooked; `Start` re-checks the target because the game's `Start` removes the unit first. The `UnitUpgrades` row stays the default (and the only one that obsoletes training). The AI takes the allowed option with the best `AI::UnitProduction::GetUnitEfficiency`.
* UI state gets `UnitUpgradeRules.PARAM_CHOICE`, `RESULT_COST`, `RESULT_RESOURCE_COST`; call `UnitManager.CanStartCommand(unit, UnitCommandTypes.UPGRADE, { [UnitUpgradeRules.PARAM_CHOICE] = firstStepIndex + 1 }, testOnly, true)` and `UnitManager.RequestCommand` the same way (header comment; example UI in `DevCE_UnitAltUpgradeTest`).
* Failure reasons use the loc keys `LOC_DEVCE_UPGRADE_UNIT_UNAVAILABLE`, `LOC_DEVCE_UPGRADE_NEEDS_LEVEL`, `LOC_DEVCE_UPGRADE_NEEDS_BUILDING` (and `_2`, `_ANY`); they need the Localization exports, else no reasons are shown.
* Each rule group verifies code bytes at startup; a mismatch switches off just that group (building rule, alternative upgrades, outside-territory effect) and logs to DevBridge.log. `pUnit:GetUpgradeCost()` in Lua knows only the default option (code comment).

## 2. Upgrade fallback
Normally a unit can no longer be built once its upgrade is unlocked (major civs). If the upgrade cannot be built (`MODIFIER_PLAYER_UNIT_BUILD_DISABLED`, or `Unit_BuildingPrereqs`), the unit disappears with no replacement. With the fallback, **the unit stays buildable in a city that cannot train its upgrade**.

**Switch on:** capability `CAPABILITY_DEVCE_UPGRADE_FALLBACK` (mod `DevCE_UpgradeFallback`, SQL only, two INSERTs; start a new game). No Lua API.

**Engine facts.** `City::BuildQueue::CanTrain` runs the check inline in a loop over the unit's upgrades. Per upgrade it calls `Rules::Units::HasAvailableReplacementForUnit` (unique unit swap) and, if unlocked, `Player::Instance::IsMajor`. Dev CE hooks `CanTrain`, those two functions, and acts only when they are called from those two call sites (return addresses are compared). The first hook records which unit the upgrade is; the second answers "not major" (keep the unit) when `CanTrain` for the upgrade returns false.

**Limits.** At most 8 nested `CanTrain` frames per thread; on an upgrade cycle (the upgrade is already on the stack) the game's answer is left alone.

## 3. Unit command actions (and GreatPersonAssign)
Custom unit commands whose effect is a **great person action**. A command (a `UnitCommands` row) is bound to a template `GreatPersonIndividuals` row: it can start when the template's `ActionRequires...` rules pass at the unit's plot; starting it attaches the template's `GreatPersonIndividualActionModifiers` around the unit (as a great person activation does) and ends the unit's moves. No charges, no great person needed, once per turn (needs moves).

**How to set up** (mod `DevCE_UnitCommandActions`, which defines these tables; other mods insert rows and list it as a dependency):
1. Add the command: `Types` (`KIND_UNITCOMMAND`) and `UnitCommands` (VisibleInUI = 1, Icon, Description, Help).
2. Add a template `GreatPersonIndividuals` row (requirements in the `ActionRequires...` columns, text in `ActionNameTextOverride` / `ActionEffectTextOverride`) and its action modifiers. The mod advises a great person class with `AvailableInTimeline = 0` so nobody can recruit it.
3. `DevCE_UnitCommandActions (CommandType, GreatPersonIndividualType, AISearchRadius default 3)` binds them; `DevCE_UnitCommandGrants (CommandType, UnitType or UnitAbilityType or UnitPromotionType)` says who may use it (one column per row).

The mod script calls `UnitCommandActions.Define(commandHash, individualIndex [, aiSearchRadius])`, `Grant(hash, unitTypeIndex)`, `GrantPromotion(hash, promotionIndex)`, `GrantAbility(hash, abilityIndex)`, `Clear()` (removes grants only). Read-only, also in UI: `IsDefined`, `GetCommandHashes`, `GetActivationPlots(hash, playerID)` (UI: only when not `UI.IsGameCoreBusy()`).

```sql
INSERT INTO DevCE_UnitCommandActions (CommandType, GreatPersonIndividualType) VALUES ('UNITCOMMAND_DEVCE_TEST_CRASSUS', 'GREAT_PERSON_INDIVIDUAL_MARCUS_LICINIUS_CRASSUS');
INSERT INTO DevCE_UnitCommandGrants (CommandType, UnitType) VALUES ('UNITCOMMAND_DEVCE_TEST_CRASSUS', 'UNIT_WARRIOR');
```

**Engine facts.** Dev CE builds its own handler objects with the layout of `Unit::Commands::BaseHandler` (vtable, index +8, hash +0xc) and a 9-slot vtable mixing own functions with shared game bodies, then registers them through the `Unit::Commands::Manager` vtable (+0xb8). Requirements are tested with the static `Unit::GreatPerson::CanActivate`; effects are attached with `OnGreatPersonActivated_AttachGameEffects` followed by `FinishMoves`. The unit panel gets the template's action name (only when it has `ActionNameTextOverride`), its effect text and failure reasons, filled as `ActivateGreatPerson::CanStart` fills them. Hovering the button highlights the plots from `Unit::GreatPerson::GetActivationPlots` (mod description).

**AI.** A hook on `AI::Homeland::DoTurnActivate` runs at the start of an AI player's turn (not barbarians, not humans): a unit uses its command where it stands, or moves to the nearest revealed plot within the radius where the requirements pass (move order as `AI::BehaviorTree::MoveUnitNode` gives it), marks the unit processed, and uses the command if moves remain. The first granted command is the unit's goal; choosing among several is not implemented (code comment).

**Limits and pitfalls (from the code).**
* `Define` errors if the hash already has a game handler: only **new** `UnitCommands` rows work. Redefining your own command updates it in place.
* Maximum 256 commands, 1024 grants per command. A `Clear()` keeps the commands registered but no unit can use them. Handlers are forgotten per new game; the script must define them at every start and load.
* `GrantPromotion` indices must be `GameInfo.UnitPromotions` indices: the game's `HasPromotion` has no bounds check.
* The mod description says single player only; every code path is behind SEH guards that log a FAULT line instead of crashing.

**`UnitGreatPerson:SetGreatPersonType(individualIndex)`** (gameplay Lua, `unit:GetGreatPerson():SetGreatPersonType(index)`, from `GreatPersonAssign`): makes an existing unit of any type a great person of that individual, like `Game::GreatPeople::CreatePerson`: `Unit::GreatPerson::Set` (charges left as they are), then the `GreatPersonCreated` signal (birth modifiers, Diplomatic Favor, boosts). It errors if the unit already has an individual (changing it is unsupported because the first passive cannot be removed), on a bad index, or with no game.

## 4. REQUIREMENT_UNIT_PROPERTY_MATCHES
The unit version of `REQUIREMENT_PLOT_PROPERTY_MATCHES`. Arguments `PropertyName` and `PropertyMinimum`; met when the subject unit's property is at least the minimum. A property that is missing counts as 0 in the header comment, but the code returns "not met" for a missing property (as for plots), so a minimum of 0 is also not met for a unit that never had the property (read from the code; the header and code differ here).

```sql
INSERT INTO Requirements(RequirementId, RequirementType) VALUES ('REQ_UNIT_HAS_THREE_OF_PROPERTY', 'REQUIREMENT_UNIT_PROPERTY_MATCHES');
INSERT INTO RequirementArguments(RequirementId, Name, Value) VALUES
  ('REQ_UNIT_HAS_THREE_OF_PROPERTY', 'PropertyName', 'slthtest'), ('REQ_UNIT_HAS_THREE_OF_PROPERTY', 'PropertyMinimum', '3');
```

**Engine facts.** A factory of Dev CE's own is appended to `Registry<IRequirementFactory>` before the game builds its `RequirementLibrary`. It builds the plot requirement's object (same layout, key `MakeHash(PropertyName)` at +0xb8, minimum at +0xbc) with copies of the plot requirement's vtables whose `Test` reads the unit's `Data::VariantMap` (unit +0x1f0) instead. Only numeric variants are read. Plots re-test through a game signal; units have none, so Dev CE re-tests live requirements of a unit (a) right after Lua `Unit:SetProperty` and (b) after `EFFECT_ADJUST_UNIT_PROPERTY` Apply/Remove, deferred to the next `Context::Update` because that runs inside the modifier code. A change made while a re-test is running is queued for the next update. Direct writes by other native code can call `UnitPropertyRequirement::RefreshUnit`.

**Pitfalls.** Only requirements that are active are re-tested. Changing a unit property by any other route than the three above is not noticed until another trigger (inferred from the list of hooks).

## Tested
**Lightly tested in game by cru121; no detailed results are recorded.** Nothing here is verified in detail. What each test mod sets up:
* `DevCE_UnitUpgrades`: the capability, both tables, the building-rule parameter, the two outside-territory modifier types. No rows are active (the examples are commented out).
* `DevCE_UpgradeFallback`: only the capability `CAPABILITY_DEVCE_UPGRADE_FALLBACK`.
* `DevCE_UnitAltUpgradeTest`: the rules capability, the row Warrior -> Archer in `DevCE_UnitAltUpgrades`, an `EFFECT_DEVCE_UNIT_UPGRADE_OUTSIDE_TERRITORY` Types row and a player-units modifier on `TRAIT_LEADER_MAJOR_CIV`, plus an example unit-panel UI (`DevCE_UnitAltUpgrades_UI`).
* `DevCE_UnitCommandActions_Test`: `UNITCOMMAND_DEVCE_TEST_CRASSUS` (Crassus action, granted to `UNIT_WARRIOR`) and `UNITCOMMAND_DEVCE_TEST_COLAEUS` (Colaeus action, granted by `PROMOTION_BATTLECRY`).
* `DevCE_UnitPropertyRequirements` (file `DevCE_Requirement.sql`): requirement `REQ_UNIT_HAS_THREE_OF_PROPERTY` (property `slthtest` at least 3) in a requirement set, used by two player-unit modifiers (movement +1, grant experience -1) attached to `ABILITY_ANTI_SPEAR`. The same file also adds a command test: `UNITCOMMAND_DEVCE_TEST_BOUDICA` (Boudica action, AI radius 3) granted to units with the inactive ability `ABILITY_SLTH_TEST_CAST`. Nothing in that SQL sets the property `slthtest`; it must be set by Lua `SetProperty` or the adjust-property effect.

*RVAs as in the source for Dev CE 0.9.0, build 26595377 (the comments in the headers still say 15038592; the values match the 26595377 address map, for example GetAvailableUpgrade 0x37d4a0 where build 15038592 has 0x37dbe0). Upgrade rules: GetAvailableUpgrade 0x37d4a0, GetNextUpgrade 0x37d560, CanUpgrade 0x3b7130, GetUpgradeUnitType 0x3b78d0, Upgrade::CanStart 0x663260, Upgrade::Start 0x6634a0, XP2 Start 0x7466c0. Fallback: CanTrain 0xf86d0, HasAvailableReplacementForUnit 0x37d9d0, IsMajor 0x2f9870. Command actions: Manager::Get 0x3e6a0, CanActivate 0x3977a0, DoTurnActivate 0x4bafe0. Great person assign: Set 0x398f10. Unit property requirement: Registry GetTypes 0x626770, AdjustUnitProperty Apply 0x8d9d10, Context::Update 0x591940.*
