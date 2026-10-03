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
