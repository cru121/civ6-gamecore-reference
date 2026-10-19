# Civ VI GameCore reference (source)

Structured-data-first reference for the Civ VI GameCore analysis.

```
data/      generated JSON (tools/extract.py) - never hand-edit
curated/   hand-written YAML notes keyed by entity id (summary, usage, notes with status + evidence, related ids)
topics/    narrative pages, markdown with front matter
schema/    JSON Schema for the entity records
tools/     extract.py (artifacts -> data/), build.py (validate + merge + render), quote_yaml.py (helper)
docs/      generated markdown pages (source for any static site generator)
site/      generated self-contained HTML with client-side search (deployable to GitHub Pages as is)
dist/      JSON bundles and compact text digests for AI use (dist/ai/*.txt)
```

Lua signatures: decompile every registered wrapper (Ghidra DecompList.java over `linux_depot/out/wrapper_rvas.txt`), then `python tools/lua_signatures.py` (writes data/lua_signatures.json) and validate with `python tools/sig_validate_lua.py` (compares argument counts with how the game's own Lua calls the methods).

Rebuild: `python tools/lua_signatures.py && python tools/extract.py && python tools/lua_return_usage.py && python tools/lua_return_meanings.py && python tools/lua_arg_meanings.py && python tools/op_params_scan.py && python tools/op_params_build.py && python tools/extract_layouts.py && python tools/extract_ce_native.py && python tools/extract_devce.py && python tools/extract_index.py && python tools/extract_exe.py && python tools/exe_lua_objects.py && python tools/exe_lua_usage.py && python tools/exe_lua_signatures.py && python tools/extract_exe_lua.py && python tools/extract_exe_events.py && python tools/extract_exe_functions.py && python tools/extract_exe_files.py && python tools/extract_exe_sql.py && python tools/extract_exe_modinfo.py && python tools/extract_exe_messages.py && python tools/extract_exe_uixml.py && python tools/extract_exe_telemetry.py && python tools/extract_exe_classes.py && python tools/extract_exe_imports.py && python tools/extract_exe_audio.py && python tools/extract_exe_event_data.py && python tools/extract_exe_enums.py && python tools/extract_exe_network.py && python tools/extract_exe_artdefs.py && python tools/extract_exe_xmlformat.py && python tools/extract_exe_lenses.py && python tools/extract_exe_reflect.py && python tools/extract_exe_loading.py && python tools/extract_exe_input.py && python tools/extract_exe_devtools.py && python tools/extract_exe_gamesummary.py && python tools/build.py && python tools/check_links.py`. The build fails on schema errors, duplicate ids,
dangling `related` links and hash collisions.

Every entity carries an availability (vanilla / needs the Community Extension / engine internals); the site colours sections green / amber / grey. CE methods come from the CE wiki tables and source, native functions from the gap analysis, our function notes and the CE offsets.

Scope: Lua methods (1,920), operations and commands (154), enums (7), class layouts (1,915), globals (1,314), 8 curated notes, 25 checked Windows offsets (curated/_windows_offsets.yaml), 2 topic pages. Lua methods link to the community reference by Sukrit Tan (external) instead of copying its text.
What each argument means comes from the C++ parameter type and from the arguments the game's own Lua passes (tools/lua_arg_meanings.py).
What a returned number means comes from the C++ type the wrapper returns and from how the game's own Lua uses the result (tools/lua_return_usage.py, lua_return_meanings.py).
Return values are reconstructed by replaying the wrapper's pushes on a model stack (tools/lua_returns.py): table fields, array element types, semantic types from the called C++ function.
Known rough edges: function names in "Functions called" are the shortened names from the analysis tables; Lua
signatures are recovered from code (1,724 of 1,920 high confidence; unparsed helpers are flagged); no events or build-difference entity types yet.

The searchable all-functions page (native/all.html) loads function_index.json (8 MB) with fetch(), so view the site through a web server (GitHub Pages, or `python -m http.server --directory site`), not file://.

A generated coverage and confidence page (topics/90-coverage.md) comes from `python tools/coverage.py`; run it before `build.py`.

## Effect traces (touches column)
Pipeline: `tools/TraceBatch.java` (Ghidra headless, see ../tools/README.md) -> `tools/lua_effects.py` -> `data/lua_effects.json`,
run after lua_signatures.py and before extract.py/build.py. Status of the member names is always *inferred* (Windows offsets mapped
through the Linux DWARF layouts). Covers only wrappers with a named C++ callee (812 of 2,281; 608 got effects).
Order for the effects part: `lua_effects.py` -> `extract.py` -> `effects_topic.py` (writes topics/70-state-changes.md) -> `build.py`.
build.py also adds a "Lua methods (inferred)" column to class layout pages (reverse index: member -> methods that write/read it).

## Engine executable section (exe/)
Entities `exeopt:` (option files), `exeswitch:` (command-line switches), `execmd:` (debug console commands), pages `exe/options.md`, `exe/command-line.md`,
`exe/console.md`. Data comes from the exe analysis tables in `../findings/tables/` via `tools/extract_exe.py` (-> `data/exe_*.json`); pages are written by
`tools/exe_section.py`, called from `build.py`. Curated inputs: `curated/_exe_switches.yaml` (hand-written), `curated/_exe_default_options.yaml` (snapshot of the four
option files the game writes: which file holds each key, and comment lines used where the exe scan missed a description). Rebuilding the data from the exe needs
`tools/exe/winopts.py`, `console_cmds.py` and `wincons.py` first (see `../tools/README.md`). Planned next: exe Lua tables (UI, ForgeUI controls, Network, ...) with signatures, engine events, function index.

## Engine Lua tables (exeapi/)
Entities `exelua:` (methods of the Lua tables the exe hosts) and `exetable:`; pages `exeapi/<Table>.md`, `exeapi/controls/<Type>.md`, `exeapi/events.md`. Inputs: `../findings/tables/exe_lua_methods_windows.tsv` (tools/exe/winlua.py),
`exe_lua_forgeui_methods_windows.tsv` (tools/exe/winforge.py), the Ghidra decompile `linux_depot/out/exe_lua_wrappers_decomp.txt` (DecompList.java on ghi-exe, RVAs in `exe_wrapper_rvas.txt`), the game's Lua scripts (read in place,
only short call snippets are kept). Hand-written labels: `curated/_exe_lua_tables.yaml`. Statuses are inferred except the method names and wrapper addresses.

## Engine events (exeevents/)
Entities `exeevt:<Bus>.<id>` (456 events on six buses) and `exebus:`; pages `exeevents/index.md`, one page per bus, `exeevents/systems.md`. Data from `../findings/tables/exe_event_*.tsv`, `worldview_event_subscriptions.tsv`, the Linux scan (translator -> `GameCoreEvent_Template<N>` ids),
and `data/enums.json` (engine event names, Lua event names). Tools: `tools/extract_exe_events.py`, `tools/exe_events_section.py`.

## Engine function index (exefn/)
`exefn/index.md` (confidence guide, categories), `exefn/all.md` (client-side search over `site/exe_function_index.json`, 50,641 rows, about 5 MB, loaded by `tools/exefnsearch.js`), one page per category with the high / medium / export rows.
Data: `data/exe_function_index.json` from `tools/extract_exe_functions.py`: the Linux-keyed index `../findings/data/exe_function_index.json` (tools/exe/build_index.py) plus 1,060 Windows-only rows (Lua wrappers and control thunks from the registration code,
WorldView event handlers, the engine utility vtable, console handlers; blank Linux address). Run `extract_exe_lua.py` and `extract_exe_events.py` first. Tools: `tools/exe_fn_section.py`. Not entities, so no schema and no per-function pages.

## Files and paths (exe/files.md)
Entities `exefile:<kind>:<string>` (251) from `tools/extract_exe_files.py` (needs `linux_depot/out/widestr.pkl` from `tools/exe/widestr.py`); page `exe/files.md` by `tools/exe_files_section.py`. The Logs folder listing of the local install is read (names only) to mark which logs exist in a normal install.

## Database and text access (exedb/)
Entities `exesql:<n>` (191 statements) and `exeloc:<key>` (55 text keys) from `tools/extract_exe_sql.py`; pages `exedb/index.md` (databases, game tables the exe reads), `tables.md`, `statements.md`, `text-keys.md` by `tools/exe_db_section.py`.

## .modinfo vocabulary (exe/modinfo.md)
Entities `exemodinfo:<kind>:<name>` (143) from `tools/extract_exe_modinfo.py` (exe strings of the modding functions + a read-only scan of the .modinfo files shipped in the game folder; only element and attribute names and counts are kept) and `curated/_exe_modinfo.yaml` (handler classes, notes); page by `tools/exe_modinfo_section.py`.

## Log and error messages (exe/messages.md)
Entities `exemsg:<n>` (1,654) from `tools/extract_exe_messages.py`; page by `tools/exe_messages_section.py`. Note: tables inside `<details>` need `markdown="1"` (the build enables `md_in_html`).

## UI XML vocabulary (exe/uixml.md)
Entities `exeui:<ControlType>:<name>` (338) from `tools/extract_exe_uixml.py` (exe strings of the ForgeUI XML readers + a read-only scan of the shipped UI .xml files, names and counts only); `curated/_exe_uixml.yaml` holds the element aliases; page by `tools/exe_uixml_section.py`.

## Telemetry configuration (exe/telemetry.md)
Entities `exetel:event:<name>` (54) and `exetel:counter:<name>` (79) from `tools/extract_exe_telemetry.py` (parses the two XML documents embedded in the exe); page by `tools/exe_telemetry_section.py`. Describes the built-in default only.

## Engine classes (execlass/)
Entities `execlass:<Class>` (1,207) from `tools/extract_exe_classes.py` (needs `linux_depot/out/exe_classes.pkl` from `tools/exe/classes.py`, which reads the RTTI of the Linux exe); pages `execlass/index.md`, one per namespace, `hierarchy.md`, by `tools/exe_classes_section.py`. The ForgeUI control type pages of `exeapi/` show the base chain.

## Imports and dependencies (exe/imports.md)
Entities `exeimp:<dll>:<api>` (890) from `tools/extract_exe_imports.py` (PE import table via pefile, caller counts from `scan_win.pkl`; reads the exe copy `exe_bin/CivilizationVI.exe`); page by `tools/exe_imports_section.py`.

## Audio vocabulary (exe/audio.md)
Entities `exeaudio:<function>:<name>` (209) from `tools/extract_exe_audio.py`; page by `tools/exe_audio_section.py`.

## Event data fields (exe/event-data.md)
Entities `exeevtdata:<event id>` (109) from `tools/extract_exe_event_data.py`, which reads `linux_depot/out/exetrace/event_handlers_trace.jsonl` (TraceBatch.java run on `ghi-exe` over the handler list `event_handlers_input.tsv`, see `findings/topics/exe-event-data-fields.md`); page by `tools/exe_event_data_section.py`.

## Refreshing for a new build
See `../findings/topics/exe-refresh-runbook.md` (driver `../tools/exe/refresh.py`). The counts to compare after a same-source refresh are listed there.

## Lua enum tables of the exe (exe/lua-enums.md)
Entities `exeenum:<Table>` (74 tables, 640 members) from `tools/extract_exe_enums.py` (reads `findings/tables/exe_lua_enums_windows.tsv` from `tools/exe/winenums.py`, counts `Table.MEMBER` uses in the game's Lua files, compares with same-named GameCore enums, recomputes name hashes); page by `tools/exe_enums_section.py`. Backup `tools/build.py.bak_before_exeenums`.

## Multiplayer and lobby vocabulary (exe/network.md)
Entities `exenet:<group>:<name>` (145: Lua game list entry fields, lobby metadata keys with integer/string kind, platform lobby keys, cloud keys, connection close reasons, lobby member status, Firaxis Live session fields, configuration, operations and notifications) from `tools/extract_exe_network.py` (strings + decompile `linux_depot/out/exetrace/network_decomp.txt`, accessor slot 0x148/0x150 get integer/string, 0x178/0x188 set integer/string); page by `tools/exe_network_section.py`. Backup `tools/build.py.bak_before_exenet`. The functions that hold embedded service identifiers are skipped on purpose.

## ArtDef vocabulary (exeart/)
Entities `exeart:<template>` (47 artdef types, 840 parameter names) from `tools/extract_exe_artdefs.py` (strings of the `ConfigureFromArtDefs`-style functions from `linux_depot/out/strmaps.pkl`, matched to the template whose collection and parameter names cover them; names, value classes and counts read from the game's `.artdef` files in place, never values or asset paths); pages `exeart/index.md` and `exeart/<template>.md` by `tools/exe_artdefs_section.py`. 53 of 66 functions are assigned to a type (inferred), the rest are listed. Backup `tools/build.py.bak_before_exeart`.

## Gameplay XML data format (exedb/xml-format.md)
Entities `exexml:<kind>:<name>` (24: root elements, Table/Index/DeleteMissingReferences, the six row operations, Where/Set/Column, the Column attributes) from `tools/extract_exe_xmlformat.py` (semantics read from the decompiled `Database::XMLSerializer` functions, `linux_depot/out/exetrace/xmlser_decomp*.txt`, RVAs in `xmlser_rvas*.txt`; usage counts from the 1,562 shipped data XML files, names only); page by `tools/exe_xmlformat_section.py`. Backup `tools/build.py.bak_before_exexml`.

## Lenses and lens layers (exe/lenses.md)
Entities `exelens:layer:<name>` (70) and `exelens:lens:<name>` (24) from `tools/extract_exe_lenses.py` (56 layer names registered by `LensManager::LensManager` at 0x197000, the `LensLayers` constants from `data/exe_enums.json`, the Lens / LayersList / LensLayers collections of every `Lenses.artdef` (names only), `UILens.SetActive` and `UILens.CreateLensLayerHash` arguments in the game's Lua); page by `tools/exe_lenses_section.py`. Backup `tools/build.py.bak_before_exelens`.

## Reflected data types (exetypes/)
Entities `exetype:<Type>` (264 struct layouts, 1,104 fields) and `exetypeenum:<Enum>` (14) from `tools/extract_exe_reflect.py` (reads `findings/tables/exe_reflected_*_windows.tsv` made by `tools/exe/winreflect.py`; counts shipped `.blp` files and artdef `m_...` element names); pages `exetypes/index.md`, one per larger namespace and `other.md` by `tools/exe_reflect_section.py`. Backup `tools/build.py.bak_before_exereflect`.

## Game start, save and load sequence (exe/loading.md)
Entities `exeload:<kind>:<name>` (33: 8 states of `LoadGameViewState::LaunchNextStage`, 10 gameplay logging options, 6 `UnserializeGameState` steps, 5 save location fields, 4 metadata keys) from `tools/extract_exe_loading.py` (reads the Ghidra decompile `linux_depot/out/exetrace/save_decomp.txt`, RVAs in `save_rvas.txt`); page by `tools/exe_loading_section.py`. Backup `tools/build.py.bak_before_exeload`.

## Input actions (exe/input.md)
Entities `exeinput:<kind>:<id>` (290: 76 actions, 7 categories, 16 contexts, 191 key records) from `tools/extract_exe_input.py` (reads the Input* rows of the game's Configuration XML in place, ids and text keys only; the 18 action names registered by `App::InputAction::Manager::SetupActions` from `strmaps.pkl`; `Input.GetActionId` arguments in the game's Lua); page by `tools/exe_input_section.py`. Backup `tools/build.py.bak_before_exeinput`.

## Developer tools and crash reports (exe/devtools.md)
Entities `exedev:<kind>:<name>` (68: 21 FireTuner commands, 2 AssetCloud commands, 17 bug submission header elements, 22 exception names, 6 automation hooks) from `tools/extract_exe_devtools.py` (reads the Ghidra decompile `linux_depot/out/exetrace/tools_decomp.txt`, RVAs in `tools_rvas.txt`; command words read from the exe image); page by `tools/exe_devtools_section.py`. Backup `tools/build.py.bak_before_exedev`.

## Game summary data model (exe/gamesummary.md)
Entities `exegs:<kind>:<name>` (156: 17 configuration tables, 15 recorded or queried tables, 48 data points, 38 graphs, 5 reports, 8 categories, 25 `PushGameData` fields) from `tools/extract_exe_gamesummary.py` (reads `Configuration/Data/Schema/HallofFame.sql` and `HallofFame.xml` of the game in place, the exe SQL statements in `data/exe_sql.json`, the `PushGameData` strings); page by `tools/exe_gamesummary_section.py`. Backup `tools/build.py.bak_before_exegs`.
