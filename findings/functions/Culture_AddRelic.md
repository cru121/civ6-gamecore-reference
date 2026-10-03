---
function: GameCore::Game::Culture::AddRelic
subsystem: Game / relics / great works
rva_symbol_build: 0x1c7760
rva_installed_build: 0x1c6b80
address_mapping: unique (installed = Steam build 15038592; symbol build = older Steam depot 947510)
lua_exposure: "Not exposed."
analysis: decompiled and read (Ghidra 12.1.4), 2026-09-30
---

# Game::Culture::AddRelic

`GreatWorkTypes __thiscall AddRelic(Culture* this, City::Instance* city, BuildingTypes building, int slot, RelicSource source)`

Chooses a relic, creates its game-wide record, places it in a slot, and announces it. Its only caller is `Player::Religion::CreateRelic`.

## Verified from the decompilation
1. **Choosing:** builds a weighted pool from the great work definitions whose object type is `RELIC` and that have no record yet. Some relics tied to a governor are included or excluded depending on `source` (the value 0xb8cd57a7 is special-cased) and on whether the player has that governor.
2. **Creating:** appends a record (type, player = the city's owner, current game turn, a text string such as `LOC_RELIC_GOVERNOR`) directly to the game-wide list at Culture+0x108, through the tracked accessor. (It does not call `FindOrAddGreatWork`.) So relic records carry a "created by" text, unlike works made with `FindOrAddGreatWork` alone.
3. **Placing:** `City::Buildings::AddGreatWorkToSlot(edit(city+0xca0), listIndex, building, slot)`.
4. **Announcing:** dispatches a (player, relic type) signal, then sends a notification (hash 0xae278cfa) whose text names the relic, the building and the city. It looks up the building definition by `building` without a range check for the text (an out-of-range building index would dereference null).

## Observed in-game (2026-09-30, single player)
- Called with a valid city, a relic-holder building type and an out-of-range slot, AddRelic creates the record and notifies, but places the relic in no slot (it ends in limbo). This is what the archive hook relies on; verified with the `hut xN` test command and reload.

## Inferred (not confirmed in-game)
- Selection among the pool is random (weighted). (Medium.)
- Because `AddGreatWorkToSlot` silently does nothing for an unknown building entry or an out-of-range slot (see its note), calling `AddRelic` with a **valid city, a relic-holding building type and an out-of-range slot** should create the record and skip placement. The notification would still say the relic was placed. **Untested.** (Low-medium.)

## Verified in game (2026-09-30, disposable game, Frida)
- `AddRelic(city, building, slot=99, source=0)` with a valid city and a valid relic-holding building type (the Palace, type 1) **created a game-wide record
  for relic type 157 owned by the city's player, placed it in no slot**, and returned the relic type. Yields and tourism stayed at zero. The game still
  showed its "relic found" panel, so the notification is not suppressed by the bad slot. The relic can then be seen only by code that lists records
  (see `topics/ui-great-work-records.md`); the stock Great Works screen does not show it.
- `AddRelic(city, building=-1, slot=-1)` (the result of calling `GetNearestRelicSlot` with an invalid plot) **creates the record and then crashes** at the
  building lookup for the notification text (null dereference, offset 0x68). The record survives. So the order inside the function is: choose, record,
  place (skipped), announce; the crash is in the announce step.
- The Palace (building type 1) counted as a relic-holding building with a free slot at game start. Relic-holding building types in this build:
  1, 12, 13, 62, 82, 87, 95, 109 (type indices, not names).

## Related
- [Player::Religion::CreateRelic](Religion_CreateRelic.md)
- [City::Buildings::AddGreatWorkToSlot](Buildings_AddGreatWorkToSlot.md)
