# Lua enum tables registered by the exe

Source: `tools/exe/winenums.py` over the Windows registration functions `LuaUIEnumsLibrary::RegisterEnums` (0x8ef560), `AppLuaUIEnumsLibrary::RegisterEnums` (0x4d7c30), `Network::LuaNetworkEnumsLibrary::RegisterEnums` (0x268250) and `GameCore::App::Cache::Lua::IEnums::pRegister` (0x15e0b0). Table: `findings/tables/exe_lua_enums_windows.tsv`; reference page `docs_proto/docs/exe/lua-enums.md`.

- **74 tables, 640 members.** Each member is a constant double stored into the Lua stack before `lua_setfield`; tables start with `lea rdx,["TableName"]` plus a helper call (hashed and plain enums use different helpers). Every value is **Verified** as a stored constant.
- **Cross-check:** 10 of the tables also exist as GameCore enums (`SlotStatus`, `DiplomaticTrustTypes`, `BoostSources`, `DirectionTypes`, ...); all 57 shared members have equal values, which also confirms the signed handling of hash values.
- **Hash values:** `InterfaceModeTypes` (43 members, `~crc32("INTERFACEMODE_" + name)`), `CombatTypes` (`COMBAT_`), `TurnLimitTypes`, `CursorTypes` (`CURSOR_`) and others are 32-bit hashes; the page lists the prefix that reproduces them (at least 80 percent of members).
- Largest tables: `Keys` (205 key codes), `LensLayers` (60), `InterfaceModeTypes` (44), `MouseEvents` (18). The game's Lua uses 60 of the 74 tables.
- `Network::LuaMatchmakingEnumsLibrary::RegisterEnums` is an empty function (16 bytes on Linux), so it has no enums. The other GameCore enums that the exe does not register itself come from GameCore (see the GameCore enum pages).
- Gaps: enums whose members are filled from database rows at runtime (type tables such as `UnitTypes`) are not in this static list; tables built by other shapes of code would be missed (a scan of all functions found no further enum registrar).
