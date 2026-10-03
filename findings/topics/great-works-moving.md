# Moving a great work between cities and players

Status: analysis of the decompiled game code (symbol build, Ghidra 12.1.4). **Nothing here was tested in-game.**
Function-level detail is in `../functions/`.

## What modders can do today
Lua exposes 14 great-work methods and all are read-only getters (for example `CityBuildings:GetGreatWorkInSlot`,
`Game.GetGreatWorkPlayer`, `PlayerCulture:GetGreatWorksInCity`). There is no gameplay-side method to add, remove or move a
great work. The only Lua path that ends up removing one is a side effect: `TransferCity` and `TransferCityToFreeCities`.

## How the game itself moves one (trade path)
1. **Find the holder.** A great work belongs to whichever city has its index in a building slot (`Buildings::IsInCity`).
2. **Get the city's Buildings through the tracked-state accessor** `edit(city + 0xca0)` (see "Tracked state" below).
3. **Clear the slot:** `Buildings::RemoveGreatWork(index)`.
4. **Place it:** `Player::Culture::ReceiveGreatWork(receiver, index)` tries each of the receiver's cities in order
   (`edit()` + `CanAddGreatWork`), then `Buildings::AddGreatWork`, which picks the first empty slot whose slot type
   accepts the work's object type. Returns false if no city has room.
5. **If placing failed,** the deal item keeps the stranded index and `PostEnact` retries.

The same remove-then-receive pair appears in the city-transfer code (`City::Manager::Transfer`).

## Facts that matter for anyone building on this
- `RemoveGreatWork` does no recalculation: tourism and yields look like on-demand getters, and the theme check is a
  computed yes/no, so nothing appears to go stale after removal. *(Inferred.)*
- Between remove and place the work is in no city. The game tolerates and repairs that state.
- `AddGreatWork` returns nothing and silently does nothing if no slot fits; check `CanAddGreatWork` first.
- `AddGreatWorkToSlot` places precisely (building type + slot) but does no slot-type check of its own.
- **Ownership in the game-wide list is not updated by trades.** `Game::Culture::SetGreatWorkPlayer` is called only where
  works are created, so `Game.GetGreatWorkPlayer` is probably the *creator*. *(Inferred from callers.)* The current
  holder is whichever city contains the work.
- Relics use the same slot machinery (`Religion::CreateRelic` -> `Game::Culture::AddRelic` -> slot placement).

## Tracked state (`FAutoVariable<...>::edit`)
Many game objects keep their state in `FAutoVariable<VariantMap, Game::Instance>` members. Code that changes them calls
`edit()` first. The accessor registers the variable in its owner's set (a std::set at owner+0x38) and returns the value.
This looks like change tracking for save/load or multiplayer sync, but that purpose is **inferred, not confirmed**.
Anyone writing to such state directly, bypassing `edit()`, risks lost changes or desync.

## Open questions
- Does skipping `edit()` actually cause a visible problem, and in single-player as well as multiplayer?
- What is the constant `0xd384eeb7` that makes `Enact` skip? (probably a deal-type hash)
- Are struct offsets stable across the installed build? Functions listed in `functions/` have identical bytes, but
  `City::Manager::Transfer` changed between builds and was not verified.
