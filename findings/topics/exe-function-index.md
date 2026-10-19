# Engine executable function index

Files: `../data/exe_function_index.json` (columns + rows), `../data/exe_function_index.tsv` (same data), built by
`tools/exe/build_index.py`. Like `docs_proto/data/function_index.json` it is a column list plus row arrays, but the
columns are different (this index is about the exe, keyed by the Linux symbol names):

`name`, `linux_va`, `windows_rva` (empty = unmapped), `confidence`, `method`, `category`, `linux_size`, `notes`.

- **name**: demangled Linux export name. Rows are all real, non-template functions plus template instances that
  could be mapped; Windows-only exports (`confidence = export`) carry the undecorated MSVC name.
- **confidence**: `high` (export-name join, string anchor with 2+ strings, curated and checked by disassembly),
  `medium` (single-string or rare-constant anchor, call-graph propagation of a non-trivial function, score-based
  propagation at thr 2.6, curated medium), `low` (tiny propagated functions, thr 2.2, interval alignment ~65 %),
  `unmapped`, `export`. Measured accuracy per method is in `exe-analysis-tooling.md`.
- **notes** collect facts from the other tables: Lua method names (`Lua ControlBase:SetHide`, `Lua IManager`...),
  event handlers (`handles GameCore event 149 ...`), console commands, event translators.
- Addresses: Linux = vaddr in `depot_533502/Civ6`; Windows = RVA in CivilizationVI.exe DX11 (Jul 2024). The DX12 exe has
  different RVAs and is not mapped.

Regenerate: `scan.py win|lin`, `scan_leaf.py`, `strmap.py`, `constmap.py`, `make_extra.py`, `propagate.py`,
`propagate2.py`, `intervals.py`, the extractors (`lua_*.py`, `event_subs.py`, `console_cmds.py`), then `build_index.py`.
Search example: `grep -i "TerrainContext" findings/data/exe_function_index.tsv`.

## Update 2026-10-19: rebuilt with the Lua wrapper anchors
`make_extra.py` now also reads `linux_depot/out/anchors_lua_wrappers.tsv` (492 name-matched pairs from the Windows registration code, see `exe-lua-tables.md`),
then `propagate.py`, `propagate2.py 0 2.2`, `intervals.py`, `build_index.py` were re-run (backup of the previous outputs:
`linux_depot/out/backup_before_lua_anchors/`).
- Mapped functions: 5,118 -> 5,731 strict-propagation set; index rows 49,565 -> 49,581. By confidence: medium 2,504 -> 3,038, high 1,644 (unchanged),
  low 1,262 -> 1,319, unmapped 43,650 -> 43,075.
- 613 functions newly mapped, 37 previously mapped ones dropped, and 25 changed address. All 25 changes were previously `low` rows, which fits the
  independent check that `low` rows were right only 1 time in 19 on Lua wrappers.
- Export-name ground truth agreement is about the same after the merge (35/43 = 81 % before, 40/49 = 82 % after), so the extra anchors added coverage
  without lowering measured precision. The residual disagreements are mostly identical-code-folding pairs.
- Rule of thumb: `high` and `medium` rows are usable; verify `low` rows by disassembly before relying on them.

## Update 2026-10-19 (b): in the reference (`docs_proto/docs/exefn/`)
The index is published as a searchable page and category pages. The reference version adds 1,060 **Windows-only rows** that have no Linux symbol name: the Lua wrappers and control thunks that the registration code names (those not already in the index),
WorldView event handlers (registration-order match, medium), the 46 `IEngineUtility1` vtable slots, and the 12 debug console handlers. Search by Windows RVA works with or without `0x` (for example `547000` finds the WorldView TerrainStateChanged handler).
`low` rows are shown separately and marked unreliable (1 of 19 right on Lua wrappers).
