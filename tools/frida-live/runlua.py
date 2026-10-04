#!/usr/bin/env python3
"""Run a Lua file in the chosen UI lua_State on the game thread (via the daemon) and print the result.

    python runlua.py file.lua            # uses state.luaL (set with `civ.py luaon ADDR`)
Only use a long-lived UI state (see `civ.py luastates`): Lua in a dead/freed state corrupts the heap and crashes the game.
"""
import json, sys
import civ


def run_lua(code, timeout_note=True):
    r = civ.ask({"op": "line", "line": "state.runLua(state.luaL, %s)" % json.dumps(code), "mode": "game"})
    if not r.get("ok"):
        raise RuntimeError(r.get("error"))
    res = r["result"]
    if res.startswith("PENDING"):
        raise RuntimeError(res)
    return json.loads(res)


if __name__ == "__main__":
    out = run_lua(open(sys.argv[1], encoding="utf-8").read())
    if out["ok"]:
        print("\n".join(out["values"]))
    else:
        print("LUA ERROR (%s): %s" % (out["stage"], out["error"]))
        sys.exit(1)
