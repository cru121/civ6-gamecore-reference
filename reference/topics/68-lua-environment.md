---
title: The Lua environment after the 2026-11-06 patch (io, os, loadstring)
order: 68
---
# The Lua environment after the 2026-11-06 patch (`io`, `os`, `loadstring`)

**Availability: Steam build 26407122 and newer. Status: *inferred* from a static comparison of the old and new binaries; the individual behaviours below were not each tested in the game (the game and Dev CE do start and run normally on the new build).**

Steam build 26407122 (2026-11-06) is a "targeted update to improve security protections". Gameplay data, saves and the GameCore code are unchanged (the GameCore DLL differs from the old one only in its PE timestamp and embedded build-path strings). The security changes are in the Lua virtual machine and in the engine code that sets it up. Gameplay and UI scripts of normal mods are not affected; a mod that depended on Lua file access, process access or precompiled Lua is.

## What the game's Lua no longer has
| script-visible item | before | after |
|---|---|---|
| `io` library (`io.open`, `io.lines`, `io.popen`, `io.tmpfile`, `io.read`, `io.write`, `io.stdout` ...) | present in the VM but not opened by the game; a native mod could open it by calling the VM's `luaopen_io` (Dev CE's `GetIO()` did that) | the library's code is removed from the VM: `luaopen_io` still exists but builds an empty table, so `io.open` is `nil`; the exe also sets the `io` global to `nil` |
| `os.execute`, `os.getenv`, `os.remove`, `os.rename`, `os.setlocale`, `os.sleep`, `os.exit` | `os.execute`, `os.getenv` etc. existed in the VM's `os` table | removed from the VM's `os` table; the exe also sets each to `nil` at start |
| `os.clock`, `os.date`, `os.time`, `os.difftime`, `os.rawclock`, `os.clockpersecond`, `os.tmpname` | present | unchanged |
| `loadstring` | compiles text or precompiled bytecode | replaced by a native function (`lSafeLoadString`) that **rejects precompiled bytecode** (a chunk whose first byte is `0x1B`) and returns `nil, "invalid"`; ordinary source text loads as before |
| the other libraries (`base`, `string`, `table`, `math`, `coroutine`, `debug`, `package`) | | unchanged: no other removed registration, no added string or export was found in the VM |

## Why it matters for modders
- A mod cannot read or write files from Lua any more (it could not before either, because the game never opened `io`; only native GameCore mods such as Dev CE could add it). A native mod can still do its own file access in C++, but that works around a protection the publisher added on purpose, so Dev CE does not ship it (the code is kept, switched off, in the source).
- Mods that ship precompiled Lua (`luac` output) and load it through `loadstring` stop working. Text Lua is unaffected.
- Code that tests for these functions (`if io then ...`, `os.getenv`) sees `nil` where it saw a table or function.

## Where this was found
- VM: `HavokScript_FinalRelease.dll` shrank by about 15 KB (1,892 to 1,843 functions): 50 functions are gone (the `io` library and the removed `os` functions), two are rewritten (`luaopen_io` and the `os` table builder), about 1,700 are byte-identical and about 70 differ only in displacement bytes. Exports are unchanged (728).
- Engine: the exe functions that build the script environment were split into seven; the new ones set `io`, `loadstring`, `os.exit`, `os.execute`, `os.getenv`, `os.remove`, `os.rename`, `os.setlocale` and `os.sleep` to `nil` and register the safe `loadstring`.
- Everything else in the two exes is the same code, relocated: function addresses moved individually, so exe addresses of the older builds do not apply.
