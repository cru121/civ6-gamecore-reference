# Game / Player properties: where `SetProperty` data lives

Status: **read from the decompiled game code** (symbol build, 2026-10-02). The native-write test (`propset` in `../../frida/gw_limbo.js`) was prepared but not yet run when this was written.

## What the code shows
- `Game:SetProperty(key, value)` (`Lua::IGame::lSetProperty`) calls `FAutoVariable<VariantMap,Game::Instance>::edit` on the member at **Game + 0x1a8** (the tracked-state accessor, so
  the change is registered) and passes the returned map to the shared helper `Lua::Utility::SetProperty`. Reading (`lGetProperty`) uses the same data at Game + 0x1b8.
- `Player:SetProperty` does the same on the member at **Player + 0x518** (read at + 0x528). Cities, districts, plots, units and the player manager have their own equivalents.
- `Utility::SetProperty(lua_State, argIndex, container, outKey)`: a string key is turned into an id with `Data::VariantManager::RegisterKey(const char*)` (the manager comes from
  the container's virtual at +0x28); the Lua value is converted into the container's variant by the script system. Setting a property also sends a reporting event
  (Game: 0x4082a91e, Player: 0x153e72c2) when a value was created or changed.
- `Data::VariantMap::SetVariant(uint key, const Variant&)` is the low-level setter: a red-black tree of key -> 4-byte value (node key at +0x20, value at +0x24). The value's *type*
  is registered per key in the `VariantManager` (`RegisterKey(key, name, VariantValueType, VariantModifierType)`).

## Why it matters
Properties are the normal save-game storage for mods (they go through `edit()`, so they are saved and synchronised). A native hook that wants to store extra data (for example "who owns this
archived great work") can either write them directly with `RegisterKey` + `SetVariant` on the `edit()` map, or hand the data to a Lua script that calls `SetProperty`.

## Open
- Which `VariantValueType` a plain `RegisterKey(name)` gives and how an integer must be encoded in the 4-byte value so that `GetProperty` reads it back as a number.
- Whether a natively written property is saved and reloaded the same as a Lua-written one.

## First test results (2026-10-02, Frida `propset` / `tag` in a disposable game)
- **Native property write**: `RegisterKey("GWA_TEST")` + `VariantMap::SetVariant(key, &42)` on the `edit()` map made `Game.GetProperty("GWA_TEST")` return **0 (a number)** in both the gameplay and UI contexts (it was nil before). So the key exists and reads as a number, but the written value 42 did not arrive: the 4 bytes SetVariant copies are not simply the integer. Do not write properties this way until the encoding is understood.
- **The game crashed on loading the save** made after that test (the save contained the half-valid property, and two writes into the record dword at +0x0C). The cause was not isolated (needs one test per write).
- **Record dword +0x0C** held leftover memory before the test (bytes "AYER" in record 0 and "S\0RT" in record 1), i.e. it is uninitialised padding, not a zeroed field.

## Second test (2026-10-02): the record dword is NOT saved; the native property write is what crashed the load
- Writing a value at record+0x0C (record 0 through the `edit()` accessor of the record list, record 1 by plain write), then save and reload: **both values were gone after the reload** (the dword read 0 again). The game loads such a save normally. So this dword is not part of the saved record; it cannot carry ownership data.
- The earlier crash on loading came from the other write of that run, the native `RegisterKey` + `SetVariant` property write (which had also given a wrong value). Treat a hand-written `VariantMap::SetVariant` as unsafe for save games.
- Remaining safe storage: properties written by Lua `SetProperty` (the engine path), or data kept in the game objects that the engine already saves.
