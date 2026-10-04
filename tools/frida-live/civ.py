#!/usr/bin/env python3
"""Client for live_daemon.py.

    civ.py help                       list commands
    civ.py "records limbo"            a registered command (see `help`)
    civ.py "1+1"                      anything else is JavaScript evaluated in the game process (use `var`/functions or globalThis.x = to keep things)
    civ.py -g "Game_x()"              run on the game thread (-t: at the next BeginTurn). The game thread only runs when the game has work,
                                      so this may answer PENDING (exit 2) until you click something; the result then appears in `civ.py log`.
    civ.py -n "..."                   OPT-IN fast path: run NOW on the Frida thread even for write commands. Fine while the game is idle on your turn,
                                      but can collide with the game thread: experiments on disposable saves only
    civ.py -f snippet.js [-g]         evaluate a whole file once (not registered, not watched)
    civ.py log [N]                    last N daemon log lines (default 50);  civ.py log -s SEQ  = lines after SEQ
Exit code 1 when the command failed, 2 when it is still pending.
"""
import json, os, socket, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def ask(req):
    try:
        port, token = open(os.path.join(HERE, ".token")).read().split()
    except OSError:
        sys.exit("daemon is not running (no .token): python live_daemon.py")
    req["token"] = token
    try:
        s = socket.create_connection(("127.0.0.1", int(port)), timeout=None)
    except OSError:
        sys.exit("daemon is not reachable on port %s (stale .token?)" % port)
    s.sendall((json.dumps(req) + "\n").encode("utf-8"))
    buf = b""
    while not buf.endswith(b"\n"):
        c = s.recv(65536)
        if not c:
            break
        buf += c
    return json.loads(buf.decode("utf-8"))


def main():
    a = sys.argv[1:]
    mode, fromfile = "auto", None
    while a and a[0] in ("-g", "-t", "-n", "-f"):
        if a[0] == "-f":
            fromfile = a[1]; a = a[2:]
        else:
            mode = {"-g": "game", "-t": "turn", "-n": "now"}[a[0]]; a = a[1:]
    if not a and not fromfile:
        print(__doc__); return 0
    if not fromfile and a[0] == "log":
        req = {"op": "log"}
        if len(a) > 2 and a[1] == "-s":
            req["since"] = int(a[2])
        else:
            req["since"] = 0; req["tail"] = int(a[1]) if len(a) > 1 else 50
        r = ask(req)
        print("\n".join(r.get("log", [])))
        print("# seq", r.get("seq"))
        return 0
    line = open(fromfile, encoding="utf-8").read() if fromfile else " ".join(a)
    if fromfile and mode == "auto":
        mode = "now"
    r = ask({"op": "line", "line": line, "mode": mode})
    for l in r.get("log", []):
        print(l)
    if mode == "now" and a and a[0].split()[:1] and not fromfile:
        print("note: -n ran on the Frida thread, not the game thread", file=sys.stderr)
    err = str(r.get("error") or "")
    if not r.get("ok") and err.startswith("timed out"):       # daemons started before the PENDING change
        print("PENDING: waiting for the game thread; click something in the game, then see `civ.py log`", file=sys.stderr)
        return 2
    if r.get("ok") and str(r.get("result", "")).startswith("PENDING:"):
        print(r["result"], file=sys.stderr)
        return 2
    if r.get("ok"):
        if r.get("result") not in (None, "undefined"):
            print(r["result"])
        return 0
    print("ERROR:", r.get("error"), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
