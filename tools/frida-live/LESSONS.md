# Lessons: how this tool crashed or hung Civ VI, and the rules that came out of it

Everything below happened for real (single-player, Frida 17.19, Windows 11). Windows Application-log events are quoted so you can recognise them.

## 1. Detaching crashes the game (the big one)
* Detaching a Frida **session** (closing it, killing the daemon, Ctrl+C, an unhandled Python exception ending the process) crashes Civ VI immediately:
  `Application Error`, module `frida-agent.dll_unloaded` or an unknown module, exception `0xc0000005`. Reproduced even with a second session while the first stayed attached.
* `script.unload()` **alone** did not crash (tested: unload, create another script, 8 s later alive). The crash comes with the session detach. Untested: unloading a script that has hot hooks.
* Rules: the daemon never exits after attaching (an `ATTACHED` flag and a catch-all keep it alive); to end the session close the game normally. Syntax-check agent code **before** attaching
  (`node --check agent.js`), because a failed first load ends the process = detach = crash.

## 2. Never detach hot hooks
Detaching 171 busy hooks from the Frida thread **hung** the game (window "not responding"; it recovered by itself). Likely a lock held while another thread was inside the JS callbacks.
`hook()`/`unhook()` therefore only switch a callback on and off; the listeners stay installed until the game exits. Prefer few, cold hooks. A hook on `lua_pcall` (a JS call per Lua call)
made end-of-turn painfully slow: keep such recordings opt-in and short.

## 3. Attach timing
Attaching while the game is still starting: the module is mapped but not initialised, `Interceptor.attach` throws "no instruction could be decoded", the daemon dies, the game crashes (rule 1).
The agent now checks `Instruction.parse` at the hook targets and does nothing until they decode. Still: **only attach when a game is loaded.**

## 4. Threads and the idle game
* The game logic thread is event driven: a function such as "get player by id" is only called while the game has work. If your tick hook is one of those, `-g` jobs wait until you click.
  Use a function that runs ~60 times per second when idle (find it with `probe`).
* UI Lua runs on the game thread; **gameplay Lua runs on a different worker thread**, with one short-lived coroutine state per callback (a new `lua_State*` every turn).
* Writing game state from the Frida thread (`-n`) can race the game thread. Fine on an idle disposable save; not a habit.

## 5. Running Lua from outside
* Lua in a `lua_State` that no longer exists corrupts the heap and the game dies minutes later: `Application Error`, `ntdll.dll`, exception `0xc0000374` (heap corruption), while you are just reading.
  We did this by classifying ~1,300 states we had recorded earlier. **Never run Lua in a state you only know from an old recording.** Use long-lived UI states (the one that calls a
  property getter hundreds of times per second is a good candidate), re-verify with `luastates` right before use, and check that its first dword equals the type tag all live states share
  in your build.
* A pointer passed to a "register script data" function was not a usable `lua_State` (running Lua there raised an access violation, caught by Frida, game survived).
* Calling a Lua method with too few arguments can fault natively inside the game (null dereference, e.g. a diplomacy "action cost" getter). Frida turns it into an exception and the game
  survived, but the Lua stack/state is then in doubt. Only call methods whose parameter list you know; `luatests/crawl.lua` has an allow-list for that reason.
* For tests that must run **inside** gameplay Lua use a handshake design: the gameplay script asks the tool (through a marker call) whether native stubs are active and refuses to call
  destructive functions otherwise. See RECIPES.md "stubs".

## 6. Mods
Only **one** GameCore-replacing mod (a mod that ships `Binaries/Win64/GameCore_*.dll` and updates the `GameCores` table) may be enabled. With two enabled the game silently loads one of them: our
first test of a new DLL ran against the other mod's DLL and "found nothing". Check which DLL is loaded: `(Get-Process CivilizationVI).Modules | ? ModuleName -match GameCore`.
Also: the module with `CE` in its name is a proxy; its base address and RVAs differ from the real `GameCore_XP2_FinalRelease.dll`. The agent's module regex excludes it by default.

## 7. Small things
* A log file that your injected DLL keeps open with the default C runtime sharing is unreadable from other processes while the game runs: open it with `_fsopen(..., _SH_DENYNO)`.
* The game reloads the DLL when you load a game from the menu: bases move. `refresh()` re-resolves bases and re-installs hooks within a second; code that cached addresses must use `addr()` per call.
* Shell here-documents with backslashes can silently turn `\n` inside generated source into real newlines: write generated code with a proper file API.

## 8. Crash reporter (cmds/crash.js)
* It installs a Frida exception handler that **always returns false** (the exception continues exactly as it would without Frida) and writes a report: fault address and function, memory operation, registers, backtrace, a heuristic scan of the raw stack, and the last calls you recorded with `crash watch TEXT`.
* Faults that happen inside Frida's own protected calls (`NativeFunction`, `try { ptr.readU8() }`) are caught by Frida first and never reach the handler. A fast-fail such as heap corruption (`0xc0000374`, `__fastfail`) may kill the process before any handler runs: for those turn on Windows LocalDumps (see README) and look the addresses up with `crash sym`.
* `DebugSymbol.fromAddress` in modules without symbols (the game exe) only returns the nearest *export*, which can be far from the real function: the report labels it that way. Without a symbol table (`--symbols`) the report still gives module+RVA for every frame.
* The handler also sees first-chance exceptions that the game handles itself. Repeats of the same fault are only counted; a maximum of 40 report files per session.
