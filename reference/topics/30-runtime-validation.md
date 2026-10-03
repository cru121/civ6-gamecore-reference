---
title: Checking the reference against a running game
order: 30
---
# Checking the reference against a running game

The Lua signatures, return types and object method lists in this reference are recovered from the game code. To find out how accurate they are, they were compared with
the real game: Lua was run inside a running Civilization VI (installed build 15038592, single player, disposable game, 2026-10-03) and the results were compared with this reference.
A method row marked **✓ called in the game** was called once in the UI Lua state and returned the documented number of values; **⚠ test call raised …** means the call raised an error
with the quoted message; **✓ exists at runtime** means the method is present on the live object but was not called.

## What was checked
* **Which methods exist.** Every Lua object is a table whose metatable `__index` holds its methods, so the real API of an object can be listed at runtime:
  `for name, f in pairs(getmetatable(obj).__index) do ... end` (the global `Game` is a plain table: iterate `Game` itself).
  53 object classes reachable from `Players[0]`, `Game`, `Map`, a city, a unit and a plot were listed and matched against this reference. Methods that exist at runtime but are
  missing here are helpers (`Members`, `__instances`, `TypeName`) and classes that are not part of GameCore (`Automation`, `GameConfiguration`, `MapConfiguration`).
  Methods documented here but absent at runtime are registered only for the gameplay state, which a UI state cannot see.
* **What zero-parameter getters return.** 453 methods documented with no parameters (`Get…`, `Is…`, `Has…`, `Can…`) were called: 439 returned the documented number of values,
  8 returned nothing (a legitimate "no value" case, for example no winner yet), 6 raised errors. The errors show reference problems, each recorded on the method's own page:
  `Game.IsDefeatEnabled`, `Game.IsVictoryEnabled` (need an argument), `Game.GetUnitNamePrefix`, `Game.GetUnitNameSuffix` (not callable without an instance or argument),
  `Plot.IsNone`, `Area.IsNone` (only valid on a "none" instance). Documented return counts are therefore reliable for getters; documented parameter lists are the weaker part.
* **The engine functions behind some of this.** Function pages marked with observed behavior (great-work removal, relic creation, the Palace) were exercised by calling the
  native functions directly in the running game; see their "Observed in-game" notes.

## Pitfalls found while testing
* **Calling a method with the wrong number of arguments can fault natively, not just raise a Lua error.** `DiplomacyManager.GetDiplomaticActionCost()` called with no arguments dereferenced
  a null pointer inside the game. Only call methods whose parameter list is known.
* **Lua states are not all long-lived.** The game creates hundreds of short-lived coroutine states per turn (the AI). Running code in a state that no longer exists corrupts the heap and
  crashes the game later. Use a context that lives as long as the UI (for example the one that polls `GetProperty` continuously).
* **UI state versus gameplay state.** Only the UI state was checked. "Where" in the method tables says which registration table lists a method, not which state can call it; checking the
  gameplay state is open work.

## Limits
One build, single player, getters only, zero-parameter methods only. Mutating methods, methods with arguments, the gameplay state and multiplayer are not covered by these checks.
