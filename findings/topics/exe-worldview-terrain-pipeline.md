# Engine side of terrain: why Lua terrain changes do not redraw, and what does update

Covers the engine executable (WorldView / renderer), not GameCore. Addresses: Linux `Civ6` = ELF vaddr (names from its
exports), Windows `CivilizationVI.exe` DX11 Jul 2024 = RVA. Mapping tables: `../tables/exe_function_map.tsv`,
`../tables/worldview_event_subscriptions.tsv`, `../tables/exe_gamecore_event_handlers_linux.tsv`.

## Short answer
- A terrain change made by Lua (`TerrainBuilder.SetTerrainType`) or by World Builder ends in the same GameCore function,
  `Map::Terrain::Builder::SetTerrainType`, which writes the plot and sends `TERRAIN_TYPE_CHANGED` (hash 0x13ae3a55).
- **The 3D world renderer (WorldView) does not subscribe to that event.** Verified on Linux: the exe subscribes to
  `TerrainTypeChanged` (event id 149) in exactly two places, `Minimap_Startup` (0x32e14b0) and `StrategicView_StartupGame`
  (0x32ff9c0), both 2D map views. The 122 events WorldView subscribes to are listed in
  `worldview_event_subscriptions.tsv`; 149 is not among them.
- The terrain cell bake reads a per-plot grid (`Hex::HexGridData<Synthesis::TerrainHexCell>`) that is **filled only in
  `WorldView_StartupGame`** (Linux 0x33287f0, Windows 0x551980), plus the structure generator that runs at
  `TerrainContext::Startup`. Nothing at runtime writes that grid again (only two callers of its SetValue exist on Linux:
  StartupGame and `TerrainStyle::Default::Generator::GenerateStructures`).
- `TerrainContext::RebakeCache` only marks cells dirty; the re-bake then re-reads the same stale grid. (Also observed
  live: tile stayed green.)
- I found **no World Builder specific refresh** in either binary. In GameCore the WB command is
  `CommandSetTerrain::Undo/Redo` (0x2d5ec60) which calls `Builder::SetTerrainType(plot, terrain, continent)` and, when the
  terrain is unchanged, sends TERRAIN_TYPE_CHANGED itself. The only WB-specific difference in `_SetTerrainType`
  (0x2d14770) is that `WorldBuilder::Manager::IsActive()` skips the neighbour river/cliff edge-removal events. The WB
  Lua UI (WorldBuilderPlotEditor.lua, WorldBuilderPlacement.lua) calls `WorldBuilder.MapManager():SetTerrainType` and
  nothing else. **Open: the premise that WB edits redraw the 3D terrain live has not been observed by me.** It should be
  checked in a running World Builder (paint grass to plains and watch the 3D tile); if it does redraw, the mechanism is
  not in any code path I could find statically.

## Data flow (verified on Linux, Windows structure inferred equal)
GameCore plot (+0x2c terrain) -> `App::Cache::Map::GetPlot` (exe-side wrapper, vtable call +0x58 = terrain type) ->
`WorldView_StartupGame` loop over all plots -> `Synthesis::TerrainHexCell` per plot (translated by
`WorldView::Translate::GetTerrainTypeForTerrain` / `GetTerrainSubTypeForTerrain`) and
`LandmarkManager::Plot_SetTerrain` (0x3757df0, called only from StartupGame) -> `TerrainContext::Startup` synthesis
(ridgelines, mountain featurelines, rivers, coast splines) -> cell bake (`TerrainBakeUpdate`, `ProcessUpdates`) per frame
for cells whose state byte has bit 1 set.

TerrainHexCell fields as written by the StartupGame loop (Inferred, Medium): +0x00 translated terrain type,
+0x04 sub-type/shape class (values 0xb..0xf are set for edge conditions), +0x08 feature name hash (compared against
FEATURE_MARSH / FLOODPLAINS* / ICE hashes), +0x0d and +0x0e flag bytes (river/edge bits, bit 0 of +0x0e set when the plot
reports a flag through vtable +0x98).

## What does update incrementally
Handlers WorldView registers (examples; full list in the table):
- `TerrainStateChanged` (151): Linux 0x3337e60, Windows 0x547000 (inferred by registration order). Calls
  `ScriptTracker::TerrainState_Changed`, `WaterSystem::Context::SetWaterType(plot, ...)`, `LandmarkManager::Plot_StateChanged`,
  `ClutterLayerManager::SetClutterVisibility/SetClutterSuppressed`, `FeatureGrid::SetFakeWater`. This is the coastal
  lowland / flooding path. It changes water layer, clutter and fake water, not the terrain mesh or texture.
- Features, resources, improvements, routes, districts, buildings, fallout, appeal, ownership: per-plot handlers into
  `LandmarkManager` / `LandmarkContext` / clutter.
- `TerrainEdits` (`UpdateTerrainEdits`, per frame): height edits for wonders via `HeightEdit::TerrainEditAsyncJob`
  (Linux 0x37a5de0), which marks `Terrain::UpdateGrid` dirty. Not a terrain-type path.

## For modders (Inferred, untested)
- To make a terrain type change visible you need either a full WorldView restart (`GameViewState::ShutdownGame` +
  `StartupGame`, the same code a game load runs) or per-plot replacement of the TerrainHexCell and landmark grid state
  followed by a re-run of the structure synthesis; the second is not available as a single function.
- Sending `TERRAIN_STATE_CHANGED` for a plot would refresh water type, fake water and clutter suppression for it. That
  could fix the "land became water" and "water became land" clutter artifacts even though the mesh stays. Not tested.

## Related
- [TerrainContext::RebakeCache](../functions/TerrainContext_RebakeCache.md)

## Update 2026-10-18 (live tests, see `world-view-redraw.md`)
- The "full WorldView restart" suggested above works, but it is **not** `GameViewState::ShutdownGame` + `StartupGame`: `GameViewState::Shutdown` (Windows 0x7ee30) unloads the whole game and
  crashed it. The working pair is `WorldView_ShutdownGame()` (Windows 0x550e00) + `WorldView_StartupGame(info, flag)` (0x551980) with a copy of the info struct a real load built.
  5.5-21 s, terrain redraws correctly; the yield-icon lens layer must be re-initialised afterwards.
- World Builder: its view is the 2D strategic view (the player cannot leave it), which updates per tile; it does not show a live 3D refresh, which settles the open point above.

## Update 2026-10-19 (value traces on the exe, `tools/TraceValue.java` + `tools/bytesearch.py --map exe`)
Raw trace output: `linux_depot/out/exetrace/` (startupgame.txt, terrainstatechanged.txt, shutdowngame.txt). Handler addresses are
Windows RVAs of the DX11 Jul 2024 exe.
- **`TerrainStateChanged` handler (0x547000) event data layout - Verified (disassembly)**: `+0x04` plot x, `+0x08` plot y (an
  int pair, passed on as `TFGXInt2`), `+0x0c` state-type hash, `+0x10` bool (state set/cleared). Always runs, whatever the state:
  `0x601330`, `0x64a960` (`WaterSystem::Context::SetWaterType`, medium) and `LandmarkManager::Plot_StateChanged` (0x5bd6f0).
  Then it branches on the hash:
  - `TERRAIN_FLOOD_STATE` (0x1c8fa8d7): looks up the plot through the cache and writes the fake-water layer (calls 0x56c400 /
    0x56ca20 on the feature grid for layer 4 and layer 5, then 0x56c8d0 with the flag).
  - `TERRAIN_SUBMERGED_STATE` (0x9fa0d089): calls 0x599d70 and 0x56c8d0 with the flag.
  - Any other state type (eruption, active, flood protection) only gets the unconditional calls.
  So the doc's "sending TERRAIN_STATE_CHANGED refreshes water/fake water/clutter" holds only for flood and submerged states.
- **`WorldView_StartupGame(GameInfo const&, bool)` (0x551980) only reads the first int of the info struct itself** (`*(info)`,
  five times). The remaining fields are read by seven callees (0x601e50, 0x60e390, 0x574280, 0x56cbd0, 0x59a070, 0x57f100,
  0x1ea470): a block of 16-bit values at `+0x02..+0x26` (20 bytes) and bytes at `+0x24..+0x2f`; the object is at least 0x30
  bytes of plain data with no embedded pointers visible in the trace. Meaning of the fields is Not determined (Inferred only
  that it is a small POD, which is why a copied struct from a real load works for the live restart).
- `WorldView_ShutdownGame` (0x550e00) takes no arguments (trace shows nothing read).
- Method note: the decompiler shows both functions as `(void)`; the trace uses the inferred parameter counts (2 and 1), so
  offsets are reliable but names are not.

## Update 2026-10-19 (b): who uses the terrain state-type hashes (`bytesearch.py --map exe`, 4-byte immediate search over all sections)
Searched the little-endian constants of `GameCore::Events::TerrainEvent::StateTypes` and `TERRAIN_TYPE_CHANGED` in the exe (Verified: byte hits).
| Constant | Hits (Windows RVA: function) |
|---|---|
| TERRAIN_FLOOD_STATE 0x1c8fa8d7 | 0x93e92 (0x93e10), 0x2073ae (0x207300), 0x54705d (WorldView handler 0x547000), 0x1897a6 (Telemetry config parser) |
| TERRAIN_SUBMERGED_STATE 0x9fa0d089 | 0x5471d9 (WorldView), 0x2073c5 (0x207300), 0x1897c9 (config parser) |
| TERRAIN_ERUPTION_STATE 0x280f6a6f | 0x93eb2 (0x93e10), 0x2073dc (0x207300), 0x1897ec (config parser) |
| TERRAIN_ACTIVE_STATE 0x43086f87 | 0x189813 (config parser only) |
| TERRAIN_FLOOD_PROTECTION_STATE 0xc86a06f6 | none (never referenced in the exe) |
| TERRAIN_TYPE_CHANGED 0x13ae3a55 | 0x1502d8 (inside `Events::Translate::Register`: the GameCore-to-exe event translator) |
- TerrainStateChanged (event 151) has four static subscribers on Linux: WorldView (0x3337e60), StrategicView (0x33027d0),
  AudioMiner::OnTerrainStateChanged (0x2fe4490) and Telemetry::Listener::OnTerrainStateChanged (0x3263e90).
  Matching Windows functions: WorldView = 0x547000; **0x93e10 reads the same event data (`+4/+8` plot, `+0xc` hash, `+0x10` bool)
  and writes per-plot records (0x38 bytes each, plot index with horizontal wrap): flood sets a flag value in the record at `+0x28`,
  eruption is handled separately. Inferred (medium) that this is the AudioMiner handler**; 0x207300 (84 bytes, no name) is the
  Telemetry handler (Inferred). The config parser hits are the XML name-to-hash table for telemetry settings.
- StrategicView's handler (Linux 0x33027d0) matches none of these constants, so it reacts to any state type, which fits the 2D
  strategic map refreshing a plot per change.
- Practical for modders: only the flood, submerged and eruption states change anything in the 3D view or audio; `ACTIVE` is
  only mapped for telemetry and `FLOOD_PROTECTION` is unused by the exe.

## Update 2026-10-19 (c): feature / terrain-type hashes in the exe (negative result, Verified)
Searched the exe for the precomputed `~crc32` hashes of 31 `FeatureTypes`, 7 `TerrainClassTypes`, the `Map::Properties` and
`Map::Feature::Properties` keys, `VisibilityLayerTypes`, and the 18 vanilla `TERRAIN_*` database names (GRASS, GRASS_HILLS,
..., COAST, OCEAN, LAKE): **zero hits** in the Windows exe (the check method works: the terrain state hashes are found the same way).
- The exe does not compare plots against terrain-type or terrain-class hash constants at all. Terrain type reaches the renderer as
  the translated enum via `WorldView::Translate::GetTerrainTypeForTerrain` / `GetTerrainSubTypeForTerrain`, not by DB name.
- Features are the exception: the strings `FEATURE_ICE`, `FEATURE_MARSH`, `FEATURE_FLOODPLAINS`, `FEATURE_FLOODPLAINS_GRASSLAND`
  and `FEATURE_FLOODPLAINS_PLAINS` exist in the exe (`.rdata`) and are referenced from exactly one function,
  `WorldView_StartupGame` (0x551980); the hash is computed at runtime from the string (no immediate). No other `FEATURE_*`,
  `TERRAIN_*` or `VISIBILITY_LAYER_*` string is referenced by any exe function.
- Consequence for modders: a new feature or terrain type needs no exe support; only marsh, ice and the floodplains variants get special
  handling in the TerrainHexCell fill. A mod feature named like one of these five is not special-cased (matching is by exact name).
- Tool: `tools/exe/hashsearch.py <enum filter | NAMES=A,B> ...` prints hit counts and containing functions for `~crc32` constants.
