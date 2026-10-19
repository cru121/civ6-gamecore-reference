# Lua tables that live in the engine executable (not in GameCore)

Sources: Linux `Civ6` disassembly of the Lua registration code; extractors in `tools/exe/` (`lua_members.py`,
`lua_tables.py`, `lua_types.py`). Method tables: `../tables/exe_lua_interface_methods_linux.tsv` (516 rows),
`../tables/exe_lua_registrations_linux.tsv` (397), `../tables/exe_lua_type_methods_linux.tsv` (736),
`../tables/exe_lua_type_names_linux.tsv`. Windows addresses of these methods are in the function index
(`../data/exe_function_index.tsv`, column `notes` carries the Lua name) wherever the function could be mapped.
Everything here is **Verified** from disassembly (names are string literals in the registration code) unless marked.

## Where the UI Lua state gets its tables
`AppLuaScriptSystem::RegisterThreadLibraries` (Linux 0x36aee40) builds each Lua thread by calling, in order:
`LuaExposureLibrary`, the **exe-side GameCore interfaces** (`GameCore::App::UI::Lua::IManager`, `ILenses`, `ITree`,
`IUnitSystem`, `IWorldView`, `IGenericObjectContext`, `GameCore::Network::Lua::IManager`,
`GameCore::App::Configuration::Lua::IGame/IMap/IUser/IPlayer`, `GameCore::App::Cache::Lua::IEnums`,
`IDirtyComponentsManager`), the Lua-only events and enum libraries, then the `AppLua*` libraries
(Search, Achievements, GameSummary, Input, Locale, Modding, DB, Path, Options), Network (Matchmaking, Network),
BenchmarkSystem, AutoProfilerSystem, Steam, Automation, FiraxisLive. After that, if GameCore is loaded, the cache
interfaces from `IContext1` are added (the 1,015 "UI side" methods of `lua_registry.tsv` come from GameCore).

## Exe-defined interface tables (RegisterMembers)
| Interface (C++) | Lua name | Methods | Notes |
|---|---|---|---|
| `GameCore::App::UI::Lua::IManager` | `UI` (inferred from script use: UI.ToggleGrid, UI.PlaySound ...) | 243 | e.g. IsInGame, IsInFrontEnd, ToggleGrid, ToggleMovementPath, Set/GetWorldRenderView |
| `GameCore::App::Configuration::Lua::IGame` | game configuration table (inferred name GameConfiguration) | 82 | includes IsWorldBuilder, SetWorldBuilder, IsWorldBuilderEditor |
| `GameCore::App::Configuration::Lua::IUser` | user options table (inferred) | 52 | |
| `GameCore::App::UI::Lua::IGenericObjectContext` | | 40 | generic world objects |
| `GameCore::App::UI::Lua::ILenses` | `UILens` (verified string) | 28 | |
| `App::Automation::Lua::IManager` | | 24 | automation/test harness |
| `GameCore::App::Configuration::Lua::IMap` | map configuration (inferred) | 18 | |
| `GameCore::App::UI::Lua::IUnitSystem` | | 15 | |
| `GameCore::App::WorldView::Lua::IWorldView` | | 9 | WorldView entry points for Lua |
| `GameCore::App::UI::Lua::ITree` | `UITree` (verified) | 3 | |
| `GameCore::Utility::Lua::IDirtyComponentsManager` | | 2 | |
Also `PlayerConfigurations` (IPlayer::pRegister), `MapPinConfiguration`, `NetGameCore` (verified strings).

## Library tables registered with lua_setfield (397 rows)
Network (95 methods), Modding (52), Locale (30), Input (25), GameSummary (22), Options (21), Steam (18), Friends
instance (16), typed data variant (14 + 4), Matchmaking (11), Achievements (8), Search (7), Path (6), GameCenter (5),
DB (4). The Lua global name for each is set by the `Register` wrapper from the library class name (Inferred, Medium).
The exe also creates `GameInfo_Data`, `GlobalParameters_Data`, `GameCore`, `EventFactories`, `GameEventFactory` and
`GameEvents` globals (verified `lua_setglobal` strings).

## ForgeUI control types (736 methods in 61 types)
`Lua::TypeExposure<T>` static initializers register each control's methods (the API behind `Controls.X:Method()`):
ControlBase 106, ForgeUI_UIManager 52, LuaContext 32, AnimControl 28, EditBoxControl 27, ImageControl 27,
MovieControl 24, ButtonControlBase 22, GraphControl 22, ScrollPanelControl 21, InputStruct 21, PullDownControl 18,
TextControl 17, TouchManager 17, LineControl 16, DragStruct 16, SimplePullDownControl 15, CheckBoxControl 14,
TutorialManager 12, ToolTipManager 11, plus overlay layers (IOverlayLayer, Border/HexGrid/HexHighlight/Path/Pressure/
Sprite/TextOverlayLayer) and animations. The Windows exe **exports** the ForgeUI classes by name (877 exports), so for
those, Windows RVAs are known exactly (confidence high in the index).

## For modders (Inferred)
- Anything a UI script calls on a control, on `UI`, on `UILens`/`UITree`, or on the configuration tables is
  implemented in the exe, not in GameCore. GameCore-side hooks (CE, Frida) never see these calls.
- `UI` methods such as Set/GetWorldRenderView reach the renderer directly; `GameCore::App::WorldView::Lua::IWorldView`
  (9 methods) is the small Lua surface of WorldView.

## Update 2026-10-19: Windows-side method tables (`tools/exe/winlua.py`, table `../tables/exe_lua_methods_windows.tsv`)
Extracted directly from the Windows registration code (pattern: `lea rdx,[wrapper]; call pushnamedcclosure; lea r8,[name]; call setfield`),
no Linux mapping involved, so each row is **Verified**: Lua method name -> wrapper RVA, plus the first non-Lua calls inside the wrapper
(usually the real implementation; names only where the function map has them). 490+ registering functions, 4,259 method rows.
- Interface labels come from the mapped `RegisterMembers` name, else from a method-set match against the Linux table (>= 0.5 Jaccard); the rest
  are `unlabelled_<rva>`. Coverage of the Linux interface table: 509 of 516 methods found (UI::IManager 236 of 243; the rest are probably
  registered through a different code shape).
- Beyond the interfaces: the same extraction also yields the library tables and the ForgeUI control types (groups of 7 at a 0x210 stride are
  `TypeExposure` initializers). Largest unlabelled groups (labels Inferred from the method names): 0x26ce30 Network/matchmaking (94),
  0x4d0d70 Modding (57), 0x10f4b0 map pins / configuration values (53), 0x4cb5b0 Locale (30), 0x4c8ab0 Input actions (25), 0xb74a0 challenges
  (26), 0x4c7b30 game summary / saved games (23), 0x4c0e20 platform login / FiraxisLive (22), 0x4d3c70 Options / display (21),
  0x503bb0 and 0x2694a0 platform overlays (Steam / other store, 18 / 17).
- **Calibration of the Linux-to-Windows function map (new ground truth, 36 Lua wrappers that the map had mapped):** high 5/5 correct, medium
  12/12 correct, **low 1/19 correct**. So treat `low` rows of the function index as unreliable; `medium` and `high` held up on independent data.
- 15 Windows wrappers are shared by several Lua names (identical code folded by the linker); the Windows RVA is then the same for those methods.
- Anchor file for a later map rebuild: `linux_depot/out/anchors_lua_wrappers.tsv` (windows_rva, linux_va, tier 3), only unique pairs; merged into the map on 2026-10-19 (see `exe-function-index.md`).

## Update 2026-10-19 (b): signatures, table names, ForgeUI types (now in the reference: `docs_proto/docs/exeapi/`)
Pipeline (all in `docs_proto/tools/`, tools in `tools/exe/`): `winlua.py` (registration code) -> Ghidra `DecompList.java` on `ghi-exe` for 3,750 wrappers (3,713 decompiled, 0 failed, ~2 min) ->
`exe_lua_signatures.py` (stack reads, type tags, pushes) + `exe_lua_objects.py` / `exe_lua_usage.py` (game scripts) -> `extract_exe_lua.py` -> `exe_lua_section.py` pages.
- **Table names verified from the game's own Lua** (distinct methods of each group called as `Name.method(` in 646 scripts): `UI` (175 of 236 methods called), `Network` (76/94),
  `GameConfiguration` (51/82), `UserConfiguration`, `MapConfiguration`, `Modding` (42/57), `Locale` (19/30), `UILens` (27/28), `Challenges`, `Input`, `Automation`, `HallofFame` (not GameSummary),
  `FiraxisLive`, `Options` (21/21), `Matchmaking`, `Search`, `Benchmark`, `AutoProfiler`, `AssetPreview` (= `IGenericObjectContext`), `WorldView` (4/9). Object types (called with `:` on a value):
  player configuration (53 methods), map pin configuration, Friends objects (Steam and a second platform), variant containers. Hand-written labels: `docs_proto/curated/_exe_lua_tables.yaml`.
- **465 of the 490 registration groups are Lua event objects** (`Events.X`, `LuaEvents.X`) with the same seven methods `Add(function,[dispatch_count])`, `Remove(function)`, `RemoveAll`, `Call`, `CallImmediate`, `Dispatch`, `Count`.
  They carry no per-event data, so the event list itself is not in this table.
- **ForgeUI control methods carry their own signatures.** Each method has a 40-byte registry record `[+0x48]=name, [+0x58]=Lua thunk, [+0x60]=describe function`; the describe function formats
  `"%s%s %s( %s%s )"` style strings (7 variants for 0..5 arguments, const) into a help text such as `void SetHide( bool )`. `winforge.py` reads 733 records and 475 describe functions
  (matches the 736 methods of the Linux table); **584 have a full C++ signature**, 149 print only `CFunction: name` and fall back to the decompiled thunk. Class-name arguments such as `ControlBase*` are read from
  globals set by static initializers. Owners of a method are matched to the Linux types: 476 by unique method name, 211 more by the neighbouring methods in thunk address order (**inferred**), 46 left unassigned.
- **Validation of the decompiled argument counts** against how the game scripts call the 661 static-table and object methods that scripts also use: 526 agree (80%), 115 under-counted (17%, a helper hides the read), 20 over-counted (3%). The reference shows the larger of code and scripts.
- Parameter names come only from game scripts when one variable name covers at least 60% of at least 5 calls (many get none); the exe has no parameter names.
- Gotchas: leaf thunks without `.pdata` are missing from the function scan (443 ForgeUI thunks), so type grouping by first callee failed; use name sets plus thunk address neighbours instead.
