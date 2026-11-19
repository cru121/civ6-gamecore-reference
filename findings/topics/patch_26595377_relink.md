# Patch 2026-11-19 (Steam build 26407122 -> 26595377): same GameCore code, relocated

Update downloaded 2026-11-19 20:44, about 40 MB. No release notes were published with it that this analysis relied on.
Every comparison below is between a copy of build 15296837 (its GameCore code is the same as 26407122) and the new build; no copy of build 26407122 itself was kept. The maps are in `data/` of this repository: `gc_xp2_old_to_new_26595377.tsv` (functions with a `.pdata` entry), `gc_xp2_data_old_to_new_26595377.tsv` (data addresses), `old_to_new_offsets_26595377.tsv` (symbol-build names with their 26595377 address) and `ce_offsets_26595377.tsv` (the constants of the Community Extension source, translated). The binaries are not part of the repository.

## What changed (static, Verified)
- Every binary was relinked with a new PE timestamp (11 Nov 2026): GameCore Base `0x6af3bb2f`, XP1 `0x6af3bbde`, XP2 `0x6af3bcb5`, `CivilizationVI.exe` `0x6af3bd12`, `CivilizationVI_DX12.exe` `0x6af3d91d`, HavokScript `0x6af3ba50`. Also relinked: Localization, DatabaseDLL, SDL2, bink2w64, Civ6ToolHost, FiraxisBugReporter, ShaderAutoGen `.bs` files.
- Data files that changed: `Base\Platforms\Windows\BLPs\VFX_FireFX.blp` and `WonderMovie.blp` (the latter 207 MB), and `Base\Assets\Civ6_9ae5ab5ed97dd296.xml`. That XML is an asset-hash list (nine `blp` items with `NonOwnerAllowance type="host" mode="multiplayer"` and `SteamApp id="512035"`); only its `key` and the first hash of two items changed. It coincides with the two BLP updates, but the match was not confirmed (the SHA-1 of `VFX_FireFX.blp` is neither new value). It holds no gameplay data. `Civ6_a445179b5a244001.xml` changed the same way on 6 Nov.

## GameCore: code is the same, addresses are not (Verified, masked function hash)
- Function-level comparison of `.pdata` functions with rip-relative displacements and branch targets masked, aligned by sequence matching:
  - XP2 FinalRelease: 59,083 functions in both builds; 58,910 identical, 103 differ in a few masked bytes, 66 moved far across the file and were matched by hash, about 8 unmatched.
  - Base (45,437 functions) and XP1 (51,362) have the same function counts, the same function sizes and 46 / 95 unmatched-before-second-pass functions respectively. Not mapped in full.
- **Layout differs from 26407122**: in GameCore Base 26,806 of 45,437 functions start at a different RVA than in 15296837 (typically by tens to a few hundred bytes), although section sizes and the image size (XP2: `0xc60000`) are unchanged. So the statement "every GameCore address applies" that was true for 15038592 / 15296837 / 26407122 does **not** hold for 26595377. Use the old-to-new table.
- Maps (old RVA -> new RVA, per function, status `same` / `changed` / `moved`): `data/gc_xp2_old_to_new_26595377.tsv`. Data: `data/gc_xp2_data_old_to_new_26595377.tsv`. `.data` globals in XP2 did not move (for example `ms_pkScriptSystem` stays at `0xb8aa88`); addresses in `.rdata` did.
- Leaf functions have no `.pdata` entry and are not in the function map. They were carried over by position between their neighbours and confirmed by comparing the first 12 to 14 bytes (ignoring one rip displacement); 193 of 193 in the Dev CE table were found this way.
- A few differences remain unexplained: roughly 100 functions per GameCore DLL differ in masked bytes beyond displacements. Not analysed (Inferred: compiler or link-order effects; no new strings or exports were looked for).

## Exe (Verified for code, Inferred for data)
- Same function-level method against the 15296837 exes: DX11 79,188 of 80,660 functions identical (711 changed, 710 moved), DX12 79,370 of 81,034 (739 changed, 842 moved). Maps: `exe_dx11_old_to_new_26595377.tsv`, `exe_dx12_old_to_new_26595377.tsv`; data maps `exe_dx1?_data_26595377.tsv` from rip-relative references (`.data`/`.bss` globals +0x1000, constants in `.rdata` moved by varying amounts).
- The 14 terrain-view addresses that Dev CE uses were byte-checked at the new locations (all matched).

## Lua VM (HavokScript): more hardening than 26407122 (Verified statically; WildW reported `package.loadlib` is gone, confirmed)
Compared with the 15296837 copy (no 26407122 copy exists, so what is new in 26595377 versus 26407122 is inferred from `patch_26407122_security_update.md`, which found the package library unchanged and the bytecode loader intact):
- **`package.loadlib` is gone**, together with the native-library machinery: the strings `loadlib`, `C loader`, and the imports `LoadLibraryA` / `GetProcAddress` no longer exist in `HavokScript_FinalRelease.dll`. The C-module searchers that used `package.cpath` (old functions at 0xb1a0 and 0xb2e0) are gone; `package.path` / `preload` / `loaded` and Lua-file `require` still exist (`luaopen_package` moved from 0xe7d0 to 0xcdc0).
- **Bytecode loading is removed from the VM itself**: the 3.6 KB bytecode loader (old 0x51280, with the "Header mismatch when loading bytecode", shared/referenced-mode and structure-prototype conflict messages) is replaced by a stub that reports "Attempting to load bytecode is not supported." (new 0x144c0). Text chunks still load. In 26407122 only the exe-side `loadstring` wrapper rejected bytecode; now the VM does too.
- Function count 1,892 -> 1,815 (115 old functions without a counterpart, 38 new), image 0x93000 -> 0x8b000; the io/os removal from 26407122 is part of that difference. Map: `havok_old_to_new_26595377.tsv`.
- Dev CE does not use `package.loadlib` (no reference in `dev-ce/src`) and loads text chunks only; the debugger and hooks were not retested on 26595377.
- For modders: a Lua mod (or a native module loaded through `package.loadlib` / `require` of a DLL) that depends on loading a DLL or precompiled bytecode no longer works on 26595377. A GameCore replacement DLL (the Community Extension, Dev CE) is not affected.

## Dev CE on this build (tested 2026-11-19, disposable single-player games, DX12 exe)
- Needed: the three tables in `DevNativeTable.cpp` (functions, `kRegs` registration functions, `kEdit*`), 19 header and `.cpp` offsets, the exe tables (`kDx11New2` / `kDx12New2`), and the new GameCore timestamp `0x6af3bcb5`. Ported with `tools/gc_map_new.py`, `gc_data_map.py`, `remap_devce_table.py`, `remap_devce_regs.py`, `remap_consts.py`, `remap_exe_table.py`, `remap_symtab.py`.
- First run: a missed table (`kRegs`) made all 39 registration hooks fail with "unexpected bytes"; the per-function prologue check caught it.
- Results: 1033 functions ready, 0 disabled; level 1 993 present / 0 missing, oracle 33 match / 0 mismatch; level 2 (Frida stubs, five chunks) 824 PASS / 0 FAIL / 41 not run (no instance); level 3 115 of 115 Change* functions ran and restored, 0 call errors, 7 with visible effects; terrain view reader, patch and dome self-tests PASS.
- Not retested: DX11 terrain view, Lua debugger and hooks, city veto events, Audio API, custom National Parks, demo mods, object re-placement beyond hooking.

## For modders
- A native mod or Frida script with fixed GameCore RVAs needs new ones for 26595377. Translate with `gc_xp2_old_to_new_26595377.tsv`, then check the function's first bytes; compare after masking relative displacements, because the raw bytes of a function that reads a global change.
- A prologue check that includes a rip-relative displacement (for example `48 8b 05 xx xx xx xx`) fails across builds even for the right function.
- Build-number checks (timestamp plus image size) are not enough to tell the layout: this build has the same XP2 image size as the previous ones.
