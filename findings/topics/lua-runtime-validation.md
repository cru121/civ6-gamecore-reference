# Runtime validation of the Lua API reference (live game, 2026-10-03)

Method: Frida live channel (`frida/live`) runs Lua inside a long-lived UI `lua_State` of the installed build (15038592) on the game thread.
Scripts: `frida/live/luatests/crawl.lua` (object graph + method names by reflection: `getmetatable(obj).__index`), `calltest.py` (calls zero-parameter getters, compares
the returned Lua types/counts with `docs_proto/data/lua_methods.json`). Raw results: `frida/live/luatests/crawl_out.txt`, `calltest_results.tsv`.

## Facts (Verified in the running game)
* Lua objects are tables whose metatable `__index` holds the method functions, so a mod can list the real API of any object at runtime:
  `for k,v in pairs(getmetatable(obj).__index) do ... end`. (`Game` is a plain table: iterate `Game` itself.)
* The runtime method sets of 53 object classes reachable from `Players[0]`, `Game`, `Map`, a city, a unit and a plot match the reference extracted from the DLL
  registration tables: runtime methods missing from the reference are only helpers (`Members`, `__instances`, `TypeName`) and classes not implemented in GameCore
  (Automation, GameConfiguration, MapConfiguration). Methods documented but absent at runtime are the gameplay-only registrations (not visible from a UI state).
* 453 zero-parameter getters were called: 439 returned the documented number of values, 8 returned nothing (legit "no value" cases such as `Game.GetWinningTeam`
  with no winner, `Plot:GetAirUnits` with none), 6 raised errors.
* Documentation errors found by the test (signatures claimed zero parameters): `Game.IsDefeatEnabled` and `Game.IsVictoryEnabled` need an argument ("Expected number or string");
  `Game.GetUnitNamePrefix/Suffix` fail with "Not a valid instance" (need arguments or instance semantics); `Plot:IsNone` and `Area:IsNone` raise "Instance does not exist" on
  an existing object (only valid on a none-instance).

## Safety lessons (Verified the hard way)
* Calling a method with no arguments when it needs some can fault natively (null dereference): `DiplomacyManager.GetDiplomaticActionCost()` raised an access violation inside the
  call. Only call methods whose documented arity is known.
* Running Lua in a `lua_State` that no longer exists corrupts the heap (game crash 0xc0000374). Most states are short-lived coroutines; use only long-lived UI states.

## External tester findings (2026-10, build 15038592, single player, disposable saves)
Reported by an outside tester; not re-run here. Recorded as Inferred on each method page.
* `Game.IsVictoryEnabled` / `Game.IsDefeatEnabled` need a victory/defeat type argument: `IsVictoryEnabled("VICTORY_SCORE")` -> true, `IsDefeatEnabled(...)` -> false (twice each). Signature corrected in the reference (partial confidence). `HallofFame.GetRulesetTypes`: the tester saw 2 vanilla UI call sites passing a ruleset, but the decompiled wrapper reads no stack argument (it only builds a table from the game summary repository), so the no-parameter signature stands.
* Native faults that `pcall` does not catch: `TeamDiplomacy.GetNextEscapingSpyID` (+0xb594a, read 0xb0), `GetNextPursuedSpyID` (+0xb597a, read 0xb0), `CityBuildQueue.CheckActiveProduction` (kills the game, no report file). Faulted at any arity tried.
* Four `CityBuildings` index binders fault with a null result (`GetCreatorNameFromIndex`, `GetGreatWorkTypeFromIndex`, `GetPlayerFromIndex`, `GetTurnFromIndex`). Their recovered parameter is `GreatWorkListIndex` (the game-wide great work list, same as `Game.GetGreatWorkDataFromIndex` which is also unchecked), not a slot inside the city: probable cause is an index with no entry. Untested with a valid index.
* Dev CE side: `IFreeCities::StartRetaliationBehaviorTree` is a C++ function (not a vanilla Lua method), absent on the live object while `SetAlive` answers; already removed from the generated table (1033 entries). Reach list closed 37/41 live by the tester (District 21, Territory 4, Fallout 6, Deal 4, DealItem 1, FreeCities 1); 3 AreaPortal need a save with portals.
* Lesson and fix: the signature extractor missed arguments read straight off the Lua stack through a raw pointer (`p = *(HksObject **)(param_1 + 0x50)`, tested against the stack top, type tag compared, value read with `hks_obj_to*`), as in `Game.IsVictoryEnabled`, and `Lua::Value` table arguments and `IMapPlot::EditPlotInstance` plots. All three patterns are now understood (tools/lua_signatures.py). Result of the re-run over 2281 wrappers: 66 signatures changed (19 gained arguments from none, 26 unknown placeholders resolved, 40 gained at least one argument), 144 low-confidence ones remain (was 170), the share of the game's own Lua calls that agree with the recovered signature went from 89.8% to 90.2%.
  Newly recovered arguments include `Game.IsVictoryEnabled/IsDefeatEnabled` (type), `Game.GetPlayers` and `Game.GetUnits` (optional filter table), `GameRandomEvents.ApplyEvent` (event table), `PlayerCulture.RequestPolicyChanges` (two optional tables, the game's UI calls it with 2), `MapTerrainBuilder.SetTerrainType` (plot + terrain), `WorldBuilderCityManager.SetPlotOwner`, `WorldBuilderManager.SetVisibilityPreviewPlayer`, `WorldBuilderPlayerManager.InitializePlayer`, `UnitManager.GetReachableMovement/GetReachableTargets` (optional argument), and extra trailing optional arguments on others (`Game.GetVictoryRequirements`, `UnitManager.CanStartCommand`, `TradeManager.Calculate*Yields...`). Not changed on purpose: the iterator closures (`MembersAux`, `UnitsAux`, `ResearchQueueAux`, which read their own upvalues) and `Fractal.Destroy` (slot 1 is the object itself).
  Still open: `Game.GetProperty` in the UI state (partial). The extra optional arguments are recovered from code and not tested in the game.
