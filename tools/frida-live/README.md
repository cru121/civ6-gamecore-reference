# civ6-frida-live: a live command and code channel into a running Civilization VI

Attach Frida to Civ VI **once**, then send commands or JavaScript from any shell (or from your Claude) and read the result, without typing into a REPL and
without restarting the game when you add code. Built while reverse engineering `GameCore*.dll`, so it is aimed at people who already have (or are building)
a Ghidra project of the game's DLL.

What you get:

* `python live_daemon.py` attaches once and never detaches (see LESSONS.md: **detaching crashes the game**).
* `python civ.py "<command or JavaScript>"` runs it inside the game process and prints the result.
* `cmds/*.js` files are hot-reloaded within a second: add or change commands, hooks and helpers while the game runs.
* Calling native functions by name or RVA, hooks that never get detached, a game-thread dispatcher, a Lua bridge (run Lua inside the game, safely), a Lua object crawler.
* A written record of every crash and hang we caused so you can avoid them (LESSONS.md).

What it is **not**: a cheat tool, a mod loader or a finished product. It is a lab bench: single-player, disposable saves, expect to crash the game now and then.
It contains no game code, no addresses of any build and no symbol data. You bring your own (see "Setting it up for your game build").

## Requirements
* Windows, Civilization VI (we used the Steam build with the Gathering Storm / XP2 `GameCore_XP2_FinalRelease.dll`), single-player.
* Python 3.10+ and `pip install frida frida-tools` (tested with Frida 17.19), Node.js only for `node --check agent.js` (optional).
* A symbol table or at least a few RVAs of your own (below).

## Quick start
```
python live_daemon.py --tick 0xTICKRVA            # Civ VI running AND a game loaded (never attach while the game is starting up!)
python civ.py status
python civ.py "1+1"                               # any non-command line is JavaScript evaluated in the game
python civ.py -n "Process.enumerateModules().length"
python civ.py -g "call(0x1234, 'int', ['pointer'], [ptr(0)])"   # run on the game thread (needs --tick)
python civ.py log 50
```
Close the game to end the daemon. Do NOT press Ctrl+C / kill the daemon while the game should stay alive: that detaches and crashes the game.

### civ.py
```
civ.py help                    list commands                       civ.py -f snippet.js     evaluate a file once
civ.py "records limbo"         run a registered command            civ.py log [N]           last N daemon log lines
civ.py "expr"                  anything else = JavaScript          civ.py log -s SEQ        lines after sequence number SEQ
civ.py -g "..."                on the game thread (waits for it; exit code 2 = PENDING, result goes to the log)
civ.py -t "..."                at the next turn-start hook         civ.py -n "..."          NOW on the Frida thread (race-prone: experiments only)
```

### JavaScript helpers inside the game (see the header of agent.js)
`addr(x)`, `fn(x, ret, argTypes)`, `call(x, ret, argTypes, argValues)` (x = RVA, `'0x...'`, or a symbol name if you loaded a table), `sym(text)`,
`hook(id, x, {onEnter,onLeave})` (idempotent per id, re-installed when the game reloads the DLL, **never detached**: `unhook` only switches the callback off),
`defcmd(name, help, fn, {game:true})`, `onGame(fn)` / `onTurn(fn)`, `onRebase(fn)`, `log(msg)`, `state` (survives reloading of cmd files).
In evals use `var`/function declarations or `globalThis.x = ...`; `let`/`const` do not survive an eval.

### Writing commands
Drop a file in `cmds/`: it is evaluated into the running agent within a second and replaces the commands it registered before.
```js
defcmd('peekplayer', 'peekplayer RVA ID: call an accessor and dump 64 bytes', function (a) {
  const p = call(a[0], 'pointer', ['int'], [parseInt(a[1])]);
  return hexdump(p, { length: 64, ansi: false });
}, { game: true });          // game:true = run on the game thread
```

## Setting it up for your game build
The tool is generic; two things are build-specific and you must supply them:

1. **Symbols (optional but very convenient).** `--symbols FILE` takes JSON `{"Qualified::Name": [rva, ...]}` (RVAs in the loaded DLL). `ghidra/ExportSymbols.java` writes
   that file from a Ghidra project. The game's symbol-carrying depot (Steam depot 947510) is documented in the Community Extension wiki; mapping its names to the current build
   is a byte-pattern matching job (mask relative operands, match old->new, propagate through the call graph). For Steam build 15038592 that map is in this repository (`data/old_to_new_offsets.tsv`, see `data/README.md`) and `builds/15038592/run.bat` wires it up; for any other build you have to make your own.
2. **A tick hook** (a function called regularly on the game thread, also while the game is idle) so `-g` works: `--tick RVA`. We found ours with the `probe` command:
   `probe NAMEPART 2500` hooks up to 40 mapped functions matching the text and reports call counts per thread; or `probe 0xA,0xB,0xC` for explicit RVAs. A function that is called
   ~60 times a second on one thread even when you do nothing is a good tick. Functions that only run when the game has work (accessors like "get player") are NOT: they stay silent while idle
   and your `-g` jobs would wait for your next click. Optionally `--turn RVA` hooks a once-per-turn function (it also teaches the daemon the game thread).

Everything else works with raw RVAs.

## The Lua bridge (cmds/lua_bridge.js)
Civ VI's Lua VM is `HavokScript_FinalRelease.dll`, which exports a full API (C++-mangled names). `cmds/lua_bridge.js` calls `hksL_loadstring` / `lua_pcall` / `lua_tolstring`
directly, so you can run Lua inside the game and read the results: `luastates`, `luaon ADDR`, `state.runLua(L, code)`, `runlua.py file.lua`.
**Read LESSONS.md section 5 before using it**: running Lua in a state that is not alive crashes the game later (heap corruption), most gameplay Lua states are short-lived coroutines, and a
method called with too few arguments can fault natively. `luatests/crawl.lua` shows a safe read-only way to list every method of every Lua object by reflection
(`getmetatable(obj).__index`).

## Files
```
live_daemon.py   attaches, loads agent.js, loads and watches cmds/*.js, serves civ.py on 127.0.0.1 (token in .token)
agent.js         core, loaded once into the game (never unloaded)
civ.py           client                      runlua.py   run a Lua file in the chosen UI Lua state
cmds/            basics.js (example), probe.js (tick finder), lua_bridge.js, crash.js (crash reporter)
luatests/        crawl.lua + notes           ghidra/ExportSymbols.java
LESSONS.md       every crash/hang and what causes it       RECIPES.md   copy-paste Frida recipes       CLAUDE.md   for your AI assistant
```
Security: the daemon listens on 127.0.0.1 only and needs the token from `.token`, but anyone who can read that file can run code inside the game. Local lab tool.

## Crash reporter
`cmds/crash.js` is loaded with the other command files and is on as soon as the daemon is attached. It never changes game behaviour (the handler passes every exception on) and writes a named report
for access violations, illegal instructions and similar faults: faulting instruction and function (names come from `--symbols`; without it you get module+RVA), the memory address that was touched
(`null + offset`, freed-heap fill patterns), annotated registers, a backtrace, and a scan of the raw stack for likely callers. Reports go to the daemon log and to `crashes/*.txt` next to the daemon
(at most 40 per session; a repeated fault is only counted).
```
python civ.py crash                  # status
python civ.py crash test             # a SIMULATED report from the next tick hook: checks symbols, backtrace and thread detection in your game (needs --tick)
python civ.py crash watch NAMEPART   # remember the calls of up to 40 functions matching the text (needs symbols); they appear in the report as "recent calls"
python civ.py crash unwatch | last [n] | list | ring
python civ.py crash sym 0x1c8250 0x7ff6...   # name an RVA (<= 0x40000000) or an absolute address, e.g. one from a Visual Studio session or a crash dump
```
Limits: a hard fast-fail (heap corruption `0xc0000374`, `__fastfail`) can kill the process before the handler runs; for those, let Windows write a dump
(`HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting\LocalDumps`, value `DumpType` = 2, `DumpFolder` = a folder) and look the addresses up with `crash sym`. Faults inside Frida's own
protected calls never reach the handler. See LESSONS.md section 8.

## Licence / provenance
Code: MIT (see `LICENSE-CODE` in the repository this folder lives in). Written by the project's author with Claude (Anthropic). Not affiliated with Firaxis or 2K. Attaching a debugger-like tool to a
game is done at your own risk; use it in single-player on disposable saves.
