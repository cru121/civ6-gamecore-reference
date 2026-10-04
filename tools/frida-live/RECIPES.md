# Recipes (copy-paste, all tested in this tool)

## Call a native function
```
civ.py -g "call(0xRVA, 'pointer', ['int'], [0]).toString()"
```
Integer-class arguments (ints, bools, enums, pointers) all travel as 64-bit slots on Windows x64. Return `'pointer'`, `'int'`, `'uint8'` (bool), `'void'`. Floats need `'float'/'double'` in the right slot.

## Count which threads call which functions (find a tick hook, find the game thread)
`cmds/probe.js`: `civ.py probe PartOfName 2500` or `civ.py probe 0xA,0xB,0xC 2500`. Hooks are switched off afterwards, never detached. Cap is 40 functions per call.

## Observe calls of a function with its arguments
```js
// cmds/observe.js
hook('observe:foo', 0xRVA, { onEnter: function (args) { log('foo(' + args[0] + ', ' + args[1].toInt32() + ')'); } });
```
Idempotent: saving the file again replaces the callback. Keep hooks on cold functions.

## Replace a function by a recording stub, forwarding when switched off
```js
const T = ['uint64','uint64','uint64','uint64','uint64','uint64','uint64','uint64'];
const target = addr(0xRVA), orig = new NativeFunction(target, 'uint64', T);
const rec = { on: false, calls: [] };
Interceptor.replace(target, new NativeCallback(function (a0,a1,a2,a3,a4,a5,a6,a7) {
  if (rec.on) { rec.calls.push([a0,a1,a2,a3].map(String)); return 0; }   // swallow + record
  return orig(a0,a1,a2,a3,a4,a5,a6,a7);                                  // normal behaviour
}, 'uint64', T));
```
Calling `orig` from inside the replacement is the documented way to reach the original. Use it to test wrappers without changing game state. Keep a reference to the callback (leave it alive).
Safety pattern for destructive tests: the script that makes the calls must be **told by the tool** that the stubs are active (marker call + handshake value) and refuse otherwise.

## Run Lua in a UI state
```
civ.py luastates 3000                      # candidates seen calling the property getter, with call counts per thread
civ.py luaon 0xADDR_OF_THE_BUSIEST
python runlua.py file.lua                  # runs the file in that state on the game thread
```
Only long-lived UI states; re-run `luastates` right before. See LESSONS.md section 5.

## List every method of a Lua object (read-only reflection)
```lua
local mt = getmetatable(obj); local idx = mt and mt.__index
for k, v in pairs(idx) do if type(v) == 'function' then print(k) end end
```
`luatests/crawl.lua` walks from `Players[0]`, `Game`, `Map`, a city, a unit and a plot and prints one line per class. It only *calls* the zero-argument getters listed in its `ZERO` table: fill that
table with methods you know take no arguments (we generated ours from decompiled wrapper signatures).

## Export symbols from Ghidra
Run `ghidra/ExportSymbols.java` as a post-script on your project: `analyzeHeadless <projdir> <proj> -process <program> -noanalysis -readOnly -scriptPath ghidra -postScript ExportSymbols.java out.json`.
Then `live_daemon.py --symbols out.json`. Names may be ambiguous (overloads): `Name#2` selects the second address.

## Find the Lua VM's API
`Process.findModuleByName('HavokScript_FinalRelease.dll').enumerateExports()` has ~700 exports with C++-mangled names (`?hksi_lua_pcall@@...`, `?hksi_hksL_loadstring@@...`). `lua_bridge.js` resolves
them by prefix.
