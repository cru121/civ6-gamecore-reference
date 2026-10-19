---
title: Veto events in Lua (GameEvents.CanStartOperation and friends)
order: 66
---
# Veto events in Lua: `GameEvents.CanStartOperation` and what could be added

**Availability.** `CanStartOperation` for **unit operations** works in the unmodified game (**verified**, plain gameplay-script mod, 2026-10-15). The city operation and city command versions below do **not** exist in the game: they are **experimental prototypes** that add a native call (done with a live hook, not yet in any shipped mod) and are listed so a DLL mod can implement them.

Credit: the hidden event was found and described by **WildW** (Discord, 2024-07-14). Everything marked verified was re-checked in the game library and at run time.

## The idea
Most `GameEvents.*` are notifications. A few engine call sites instead *ask* Lua whether something is allowed (`CallTestAll`): every handler must say yes, and a single `false` blocks the action. The game's own scripts never use this one, but it works:

```lua
GameEvents.CanStartOperation.Add(function (playerId, unitId, opIndex)
	local op = GameInfo.UnitOperations[opIndex].OperationType
	-- return false to forbid it, true to allow it
	return not (not Players[playerId]:IsHuman() and op == "UNITOPERATION_MOVE_TO")
end)
```

## `CanStartOperation` (unit operations, verified)
* **Where:** `Unit::Operations::Manager::CanStart`. Order of checks: unit busy, tactical commands allowed, human / automation state, `IsOperationDisabled`, **this Lua test**, then the operation handler's own `CanStart`. Veto rule: the result flag starts false; the operation is refused only if `CallTestAll` ran and the flag is still false, so a game with no handler behaves as before.
* **Arguments:** `(playerId, unitId, opIndex)`. `opIndex` is the row index in `GameInfo.UnitOperations` (all indexes seen resolved: 0 `AIR_ATTACK`, 1 `AUTOMATE_EXPLORE`, 2 `BUILD_IMPROVEMENT`, 12 `FORTIFY`, 26 `RANGE_ATTACK`, 36 `SKIP_TURN`, ...).
* **Tested:** a gameplay-script mod (no DLL) blocked `UNITOPERATION_MOVE_TO` for non-human players on turns 5-6 of a new game: 101 checks vetoed, none after turn 6, the AI moved again from turn 7. 3,329 calls over 13 turns.
* **It is polled constantly.** The same check serves the UI ("can this button be pressed"), the AI and real requests, and was seen from up to nine threads. Keep handlers cheap and free of side effects.
* **Pitfalls (verified):**
  * `Player:IsAI()` is **nil in gameplay scripts** (it exists only in the UI-side player cache). Use `not Players[id]:IsHuman()`; that also includes city-states and barbarians (`IsMajor()`, `IsBarbarian()` exist).
  * A handler that throws does **not** block the operation: it fails open and the error is logged every call.
* **The event object** has `Add`, `Remove`, `RemoveAll`, `Call`, `Count`, `TestAll`, `TestAny`, `Accumulate`, `AccumulateINT` (all functions; `TestAll(...)` and `TestAny(...)` poll the registered handlers from Lua and returned `true` with our allowing handler).
* **Unknown event names are created on first access:** `GameEvents.SomethingNew` returned a table with `Add` although nothing defines it. So a native hook only needs to call a dispatcher with a new name to give modders a new event.

## The only test-style events in the game (verified)
Callers of the Lua dispatchers in the shipped library (installed build): `CallTestAll` has **one** caller (`CanStartOperation`); `CallTestAny` has one (the autoplay end-of-turn check); `CallProcessor` has four (World Congress resolution checks and two AI hooks); `SendLuaEvent` two (autoplay, new game); `CallHook` about 37 (the ordinary notification events). There are no other hidden veto events. Dispatch details and thread/lock behaviour: see the findings page on Lua event dispatch.

## Not in the game: city operations and city commands (experimental)
`City::Operations::Manager::CanStart` and `City::Commands::Manager::CanStart` have **no** Lua call. A live hook that calls the game's own `CallTestAll` after the original returns true reproduces the unit behaviour:

| Event (prototype) | Hooked function | Arguments | Result |
|---|---|---|---|
| `GameEvents.CanStartCityOperation` | `City::Operations::Manager::CanStart` | `(playerId, cityId, opType)` | A Lua handler vetoed 63 of 63 city **Build** checks and the production list came up empty. `BUILD` is the only registered city operation (op `0`). |
| `GameEvents.CanStartCityCommand` | `City::Commands::Manager::CanStart` | `(playerId, cityId, commandType)` | Command **0 = Purchase**: vetoing it removed both the gold and faith purchase buttons (39 of 39 checks). **1 = Range Attack** (only seen for city-states with Walls). |

* **Status:** the mechanism and the two numbers above are verified in the game; the other command numbers are **inferred** (enum order: 2 `SET_FOCUS`, 3 `DESTROY`, 4 `MANAGE`, 5 `WMD_STRIKE`, 6 `SWAP_TILE_OWNER`, 7 `NAME_CITY`) and denying 2, 3 or 4 changed nothing visible, so do not rely on them yet. There is no `GameInfo` table for city operations or commands; the numbers are code-side ordinals, not database rows.
* The AI goes through the same checks and the veto applied to it (a city-state's checks were all refused when vetoed).
* **Granularity:** the purchase item (which unit or building) and the build sub-kind (train unit, construct building, zone district, advance project) are **not** among the arguments; a DLL implementation could pass them.
* Rough costs: each passing check now costs one Lua call; AI city checks are sparse, UI checks happen while a city panel is open.

## For modders
* Block or allow specific unit operations per player, per civ or by game state with `GameEvents.CanStartOperation`; check `IsHuman()` rather than `IsAI()`.
* A DLL mod (for example the Community Extension) can add the city versions by adding one `CallTestAll` call to each `CanStart` and choosing the event names and arguments; the addresses and the argument handling are in the analysis notes.
* Because unknown event names are created on demand, any other native check could become a veto event the same way.

## Not yet verified
* A real-mod test of the city events (only the live-hook prototype was run).
* The meaning of city command numbers 2-7.
* Dispatch cost under load, and the behaviour when two mods register opposite answers (`TestAll` semantics say one `false` wins; not exercised).
