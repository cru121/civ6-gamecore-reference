---
function: GameCore::Player::Religion::GetNearestRelicSlot
subsystem: Player / religion / great works
rva_symbol_build: 0x3140e0
rva_installed_build: 0x315270
address_mapping: unique (installed = Steam build 15038592; symbol build = older Steam depot 947510)
lua_exposure: "Not exposed."
analysis: decompiled and read (Ghidra 12.1.4), 2026-09-30
---

# Player::Religion::GetNearestRelicSlot

`City::Instance* __thiscall GetNearestRelicSlot(Religion* this, PlotCoord plot, BuildingTypes* outBuilding, int* outSlot)`

Finds the player's city with a free relic slot that is nearest to a plot. Returns null when the player has no free relic slot anywhere.

## Verified from the decompilation
- Looks up the great work object type `GREATWORKOBJECT_RELIC` and reads its list of building types that can hold relics (list at definition+0x40..+0x48).
- For each of the player's cities (player+0x6d0 city list) that has such a building and a free slot (`Buildings::GetFreeSlot != -1`), it measures the plot distance to `plot` and keeps the nearest. If `plot` is not valid it returns the first city found.
- The two output parameters (building type, slot index) are written **only when a city was found**.

- Verified in game: when `plot` is invalid (the game's own "no plot" value), it returns the first city with room and **does not write the output building/slot**
  (they keep whatever the caller initialised, usually -1). Passing those on to `AddRelic` crashes it (see `Culture_AddRelic.md`).
- Verified in game: the Palace counts as a relic slot holder at the start of a game (relic-holding building types: 1, 12, 13, 62, 82, 87, 95, 109).

## For modders
- "No relic slot" means either no relic-holding building exists yet or all are full. Both return null here.

## Related
- [Player::Religion::CreateRelic](Religion_CreateRelic.md)
- [Game::Culture::AddRelic](Culture_AddRelic.md)
