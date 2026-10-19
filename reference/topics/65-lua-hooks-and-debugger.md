---
title: Lua hooks and a Lua debugger (Dev CE)
order: 65
---
# Lua hooks and a Lua debugger (Dev CE)

**Availability: experimental, needs the Dev CE GameCore mod (0.3.0 or newer), Steam builds 15038592 and 15296837.** The retail game ships no usable Lua debugger: the Havok network debugger is compiled out of
`HavokScript_FinalRelease.dll`, `debug.sethook` / `debug.gethook` are missing from mod states, and the VM would ignore the hook even if `lua_sethook` stored one. Dev CE adds working hooks and, on top of them, a debugger
that speaks a small JSON protocol over a loopback socket plus an adapter for the Debug Adapter Protocol. This page is the user view and the facts behind it (everything below is **verified** in the game unless marked).

## `debug.sethook` / `debug.gethook`
```lua
debug.sethook(function(event, line) print(event, line) end, "l")        -- events: "call", "return", "line", "count" (mask letters c, r, l; count as 3rd argument)
debug.sethook()                                                          -- remove
local f, mask, count = debug.gethook()
debug.sethook(coroutine_object, hook, "l")                               -- hooks a coroutine from outside; gethook(thread) reads it
```
* Same meaning as PUC Lua 5.1: a `line` event when the line changes or the pc jumps backwards (one event per iteration of a one-line loop), `call` / `return` also for C functions called from Lua, `count` every N instructions.
  `debug.getinfo(2)` inside the hook describes the function that was hooked, with the hooked line.
* An error inside the hook function does not propagate: it is logged to `DevBridge.log` and the hook is removed.
* C functions called from C code (`pcall`'s callee, metamethods) and tail returns raise no events. Only one of the three interpreter variants of the VM is patched (the one that ran in every measurement).
* `DevCE_ClockMs()` returns a millisecond clock (QueryPerformanceCounter); `os.clock` is too coarse to time Lua code.
* Cost: nothing until the first `debug.sethook` with a mask (that call installs the patch); with the patch and no hook, a tight loop was about 8 % slower; a line event that reaches a Lua hook costs about 0.3 µs.

## The debugger
**Switch on:** a text file `DevCE_Debug.txt` next to the Dev CE DLL (`Mods/<mod>/Binaries/Win64/`), first line the TCP port (default 4320); a second line `demo` also enables the demo script of the `DevCE_DebugDemo` mod.
`DevBridge.log` then says `[LuaDebugger] listening on 127.0.0.1:4320`. **Security:** loopback only, no authentication, anyone who can connect can run Lua in your game; delete the file when not debugging.

**Clients:** `dev-ce/tools/devce_dbg.py` (command line: `break FILE LINE [if COND] [hit N] [log EXPR]`, `continue`, `next`, `step`, `out`, `pause`, `stack`, `vars`, `expand EXPR`, `eval EXPR`, ...) and `dev-ce/tools/devce_dap.py`
(Debug Adapter Protocol over stdio or TCP for editors; conditions, hit conditions, log messages, scopes Locals / Upvalues, hover and repl evaluate). The adapter was only tested with a scripted client, not with an editor.

**What a stop is:** the thread that runs the Lua state blocks inside the VM loop and answers requests itself (Lua is not thread-safe). For gameplay scripts that is the game thread, so the game freezes; it resumes after 120 s without a
request, when the client disconnects, or on `continue`. One stop at a time; a second state that hits a breakpoint meanwhile simply continues. `debug.c_breakpoint()` stops at that call when a client is connected. Dev CE **replaces** the retail function in every Lua state, whether or not the debugger is switched on: the retail one (closure at HavokScript RVA 0x72f0, bytes `nop; int3; xor eax,eax; ret`) executes an `int3`, which breaks into an attached native debugger and ends the game without one; Dev CE's version does nothing when no client is connected and no longer breaks into a native debugger.

**Breakpoints** match by file name or trailing path of the chunk's source (case-insensitive, `/` equals `\`). They apply to every Lua state, also to coroutines created later: each state installs its own hook the first time it runs a
Lua instruction while breakpoints exist, and a hook the VM filters by line only reaches the debugger on breakpoint lines. **Evaluate / conditions:** this game's Lua has **no global `setfenv`** (the retail debug library's function table lists `debug.setfenv` / `debug.getfenv`; not tested), so an expression is compiled as
`local a, b, ... = ...; return <expr>` with the frame's locals and upvalues passed in; globals are the real globals (assignments persist), assignments to frame variables only change the copy.
**Cost** (measured, 3 real end turns): an end turn runs about 1-1.5 million Lua instructions; with the debugger attached and breakpoints set the overhead was roughly 20-40 ms on a turn of about 4 s.

## Protocol (JSON lines, one object per line)
Requests `{"id":N,"cmd":"...", ...}`, replies `{"id":N,"ok":true|false, ...}`, events `{"event":"stopped"|"output"|"mark"|"hello", ...}`.
Commands: `status`, `break` (`file`, `line`, optional `cond`, `hit`, `log`), `clear`, `breaks`, `pause`, `continue`, `step`, `next`, `out` (while stopped), `stack`, `vars` (`level`, optional `expr` for the children of a table), `eval` (`expr`, `level`).
`stopped` carries `reason` (`breakpoint`, `step`, `pause`, `c_breakpoint`).

## How it works (build 15038592; for contributors)
* **Interpreter:** `HavokScript_FinalRelease.dll` section `.interpr` (RVA 0x62000-0x6d964) holds the VM loop in three variants; the one that ran everywhere has its instruction fetch at RVA **0x696aa** (`mov [L+0x30], pc` with `L` in `rdi`,
  `pc` in `rax`, frame base in `rcx`, spilled at `[rbp+0x498]`). A 5-byte `jmp` to a generated stub is written there on first use (all other threads are suspended during the patch, bytes are checked first); the stub tests the state's hook mask,
  calls the C++ side for hooked states and reloads the frame base afterwards because a hook may reallocate the Lua stack.
* **C functions:** the CALL handler runs `inc [L+0x98]` (RVA 0x6b8c6) before `call rbx` and `test eax,eax; js` (RVA 0x6b8f8) after it; those two places are patched for call / return events. **Never patch the instruction at a return address with a `jmp`:**
  the Windows x64 unwinder takes it for an epilogue and an `error()` unwinding through the frame dies with `STATUS_BAD_STACK`.
* **lua_State** (Windows): callinfo base `+0x18`, current entry `+0x28` (24-byte entries), pc `+0x30`, hook pc `+0x38`, hooked frame index `+0x40`, top `+0x48`, base `+0x50`, hook function `+0xc8`, mask `+0xd0` (1 call, 2 return, 4 line, 8 count), count `+0xd4`, counter `+0xd8`.
  `lua_Debug`: event `int` at 0, `currentline` at 0x28, `short_src` at 0x40 (512 bytes). Setting `+0x38` / `+0x40` around a hook makes `getinfo` report the hooked line (the pc lookup is HavokScript +0x28180).
* **Traps found:** `lua_tothread` and `lua_topointer` crash on a thread value (a thread on the stack is a 16-byte slot: type tag 8, then the `lua_State*`); the global `setfenv` does not exist (`debug.setfenv` is listed in the retail debug library table, untested); `lua_close` / state lifetimes are not observable, so the debugger never
  writes into a state from another thread.
* Source: `LuaHooks.cpp`, `LuaDebugger.cpp` in the [Dev CE repository](https://github.com/cru121/civ6-dev-ce); plans and measurements in `dev-ce/DESIGN_LUA_HOOKS.md` and `dev-ce/DESIGN_LUA_DEBUGGER.md`.
