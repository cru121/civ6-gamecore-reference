# CivilizationVI.exe analysis: tooling and mapping feasibility

Scope: the engine executable that hosts GameCore (Windows `CivilizationVI.exe` DX11, Jul 2024, MSVC, no symbols) and the
Linux `Civ6` binary (clang, stripped, ~200k names in `.dynsym`). Addresses: Windows = RVA from image base 0x140000000,
Linux = ELF vaddr.

## Verified facts about the binaries
- **Windows exe has no useful RTTI.** Only 115 type descriptors exist, all lambdas and `std::default_delete`; there are
  no `.?AV<GameClass>` names, so vtables cannot be named from RTTI. (Verified by scanning the whole file.)
- **Windows exe exports 1058 named symbols**: 877 `ForgeUI::*` (UIManager, ControlBase, ContextBase, ...) and about
  180 Havok Script API names (`hks*`, `hksi_lua_*`). No WorldView/Terrain exports. (Verified.)
- Linux exe exports ~199k names (classes, methods, 2442 vtables, 2483 typeinfos); about 1.2 % of the demangled names are
  plain-C `WorldView_*` style entry points.
- Windows function boundaries must be taken from `.pdata` **with unwind chaining followed**: MSVC splits one function
  into several RUNTIME_FUNCTION entries (prologue / body / epilogue chained by UNW_FLAG_CHAININFO). 80,660 raw entries
  merge to 46,821 functions. (Example: `TerrainContext::RebakeCache` 0x609be0 is three entries.)
- Linux function boundaries come from `.eh_frame_hdr` (212,367 functions in `.text`).
- The Linux binary has an extra executable section `__TEXT,interpreter_loop` (Lua VM loop).

## Mapping method and measured quality
1. **Export names**: 808 Windows exports map 1:1 by qualified name to a Linux name (used as ground truth).
2. **String anchors**: a string with identical text referenced by at most 3 functions on each side; best mutual pair
   by vote. 3,228 mutual pairs; 26/26 agree with the export ground truth.
3. **Call-graph propagation** (callee order alignment with mapped callees as sync points, size / callee-count /
   string-compatibility gates): +726 pairs. Hold-out test (hide 30 % of string anchors, recover them): 34 recovered,
   32 correct (94 % precision, low recall). Loose gates gave only 4/10 correct, so the strict version is kept.
Current table: `linux_depot/out/map_funcs.tsv` (win_rva, lin_va, tier, via). Tier 0 = string anchor, 1 = propagated.

Not found / not feasible: byte matching across compilers; class-name recovery from Windows RTTI; automatic vtable naming
(requires constructor/vtable-store matching, planned in later phases).

## Tools (tools/exe/)
`demangle_dynsym.py` (Ghidra's bundled GNU demangler, no extra install), `pelib.py` (PE loader + dbghelp undecorate),
`scan.py` (per-function call/ref/constant index for both binaries), `strmap.py` (strings + anchors),
`propagate.py` (call-graph propagation, optional hold-out argument), `match_exports.py`, `win_rtti.py`,
`xdis.py` (annotated disassembly: `python xdis.py win|lin <hex addr>`), `ghidra_import_exe.ps1`
(project `ghi-exe/civ6exe`, separate from `ghi-proj`). The launcher .bat of Ghidra cannot take the Steam path
(parentheses and apostrophe), so the exe is imported from a copy in `exe_bin/`.

## Update after Phase 4 (mapping method and quality)
- **Windows function list fixed**: `.pdata` does not cover frame-less leaf functions and CRT stubs (e.g. the cell manager's
  `GetNumCells`). 5,280 call targets were outside every `.pdata` range; `tools/exe/scan_leaf.py` adds them
  (Windows functions now 52,101). Allocation helpers such as 0x982060 are among them.
- **Anchor sources and measured quality** (hold-out = hide 30 % of string anchors, try to recover them):
  string anchors 3,270 pairs (26/26 vs export ground truth); rare-constant anchors (hashes/magic numbers shared by 1-3
  functions per side, `constmap.py`): 139 pairs with 2+ constants, 97 % agreement with string anchors on overlap;
  strict callee-order propagation (`propagate.py`): 55/57 correct on hold-out; score-based neighbour propagation
  (`propagate2.py`): thr 2.6 gives 143/148 (97 %), thr 2.2 gives 171/181 (94 %), thr 3.0 gives 50/50; order alignment
  between anchors (`intervals.py`) only reaches about 65 % and is listed as low only.
- **Caveats**: propagated pairs for tiny functions (< 64 bytes) are unreliable (the export ground truth, mostly tiny
  ForgeUI getters, agrees only about half the time); several Linux functions can map to one Windows address when the
  MSVC linker folded identical code (`windows function shared by N names` in the index notes).
- Final tally in `../data/exe_function_index.tsv`: about 49,500 rows (all 50,123 non-template Linux functions that are real
  functions, plus mapped template instances and Windows-only exports): 1,644 high, 2,504 medium, 1,262 low, 43,650 unmapped,
  505 Windows-only exports. Coverage is low outside the subsystems worked by hand (WorldView 140/2,293 at high+medium).
