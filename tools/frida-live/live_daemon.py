#!/usr/bin/env python3
"""Live Frida daemon for Civ VI: attach once, NEVER detach (it crashes the game), take commands from a local TCP port.

    python live_daemon.py            # start (Civ VI must be running); leave it running; close the game to end it
    python civ.py "records limbo"    # in another shell: send a command / JavaScript, print the result

* agent.js is loaded once. Every cmds/*.js file is evaluated into it and re-evaluated whenever the file changes (hot reload,
  no game restart, no script unload - unloading/detaching Frida crashes the game).
* --symbols FILE gives JSON {name: [rva, ...]} so JavaScript can say call('Ns::Class::Func', ...).
* The daemon listens on 127.0.0.1 only and requires the token in live/.token (the client reads it). Anybody who can talk to it can run code
  inside the game process: it is a local development tool.
"""
import argparse, collections, json, os, secrets, socketserver, sys, threading, time
import frida

HERE = os.path.dirname(os.path.abspath(__file__))
CMDS = os.path.join(HERE, "cmds")
LOGFILE = os.path.join(HERE, "live_log.txt")
TOKEN = os.path.join(HERE, ".token")
NAMES = ("CivilizationVI.exe", "CivilizationVI_DX12.exe")
PENDING = "PENDING: waiting for the game thread (it only runs when the game has work: click something or end the turn). The result will be written to the log (civ.py log)."
def load_symbols(path):
    """name -> [rva, ...]. JSON {"Name": [rva, ...]} (ghidra/ExportSymbols.java writes it) or none."""
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Hub:
    """Glue between the frida script and the TCP clients."""

    def __init__(self, script):
        self.script = script
        self.lock = threading.Lock()
        self.logs = collections.deque(maxlen=5000)   # (seq, line)
        self.seq = 0
        self.logf = open(LOGFILE, "a", encoding="utf-8")
        self.stamps = {}

    def add_log(self, line):
        with self.lock:
            self.seq += 1
            self.logs.append((self.seq, line))
            self.logf.write(line + "\n")
            self.logf.flush()

    def on_message(self, message, data):
        if message["type"] == "send":
            p = message["payload"]
            if isinstance(p, dict) and p.get("k") == "log":
                self.add_log(time.strftime("%H:%M:%S", time.localtime(p["t"] / 1000)) + " " + p["msg"])
                return
            self.add_log("send: " + json.dumps(p))
        elif message["type"] == "log":
            self.add_log("console." + message.get("level", "log") + ": " + str(message.get("payload")))
        else:
            self.add_log("SCRIPT ERROR " + json.dumps(message))

    def since(self, seq):
        with self.lock:
            return [l for s, l in self.logs if s > seq], self.seq

    def rpc(self, name, *args):
        return getattr(self.script.exports_sync, name)(*args)

    def rpc_timeout(self, timeout, name, *args):
        """rpc call that stops waiting after `timeout` s. A game-thread job stays queued until the game thread has work (it has no idle tick),
        so on timeout we return PENDING and log the job's result when it eventually runs."""
        box = {}
        done = threading.Event()

        def run():
            try:
                box["r"] = self.rpc(name, *args)
            except Exception as e:
                box["e"] = e
            done.set()
            if box.get("abandoned"):
                self.add_log("queued job finished: " + (str(box["e"]).splitlines()[0] if "e" in box else str(box.get("r"))[:500]))
        threading.Thread(target=run, daemon=True).start()
        if not done.wait(timeout):
            box["abandoned"] = True
            if not done.is_set():
                return PENDING
        if "e" in box:
            raise box["e"]
        return box["r"]

    def load_file(self, path):
        name = os.path.basename(path)
        try:
            with open(path, encoding="utf-8") as f:
                code = f.read()
            cmds = self.rpc("loadfile", name, code)
            self.add_log("loaded %s: %s" % (name, ", ".join(cmds) if cmds else "(no commands)"))
        except Exception as e:
            self.add_log("LOAD FAILED %s: %s" % (name, str(e).splitlines()[0] if str(e) else e))


def watcher(hub, gone):
    mt = {}
    while not gone.is_set():
        try:
            files = sorted(f for f in os.listdir(CMDS) if f.endswith(".js"))
            for f in files:
                p = os.path.join(CMDS, f)
                t = os.path.getmtime(p)
                if mt.get(f) != t:
                    mt[f] = t
                    hub.load_file(p)
            hub.rpc("refresh")
        except Exception as e:
            hub.add_log("watcher: %s" % e)
        gone.wait(0.7)


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        hub = self.server.hub
        try:
            req = json.loads(self.rfile.readline().decode("utf-8"))
        except Exception:
            return
        if req.get("token") != self.server.token:
            self.wfile.write(b'{"ok":false,"error":"bad token"}\n')
            return
        op = req.get("op")
        out = {"ok": True}
        try:
            if op == "line":
                _, before = hub.since(10**12)
                try:
                    out["result"] = hub.rpc_timeout(self.server.timeout, "line", req["line"], req.get("mode", "auto"))
                except Exception as e:
                    out["ok"] = False
                    out["error"] = str(e)
                new, _ = hub.since(before)
                out["log"] = new
            elif op == "log":
                lines, seq = hub.since(req.get("since", 0))
                out["log"] = lines[-req.get("tail", 200):]
                out["seq"] = seq
            elif op == "status":
                out["result"] = hub.rpc("status")
            else:
                out = {"ok": False, "error": "unknown op"}
        except Exception as e:
            out = {"ok": False, "error": str(e)}
        self.wfile.write((json.dumps(out) + "\n").encode("utf-8"))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


ATTACHED = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=27123)
    ap.add_argument("--timeout", type=float, default=8.0, help="seconds a request waits before answering PENDING (game-thread jobs wait for game activity)")
    ap.add_argument("--process", help="attach to this process name instead of Civ VI (for testing the framework)")
    ap.add_argument("--symbols", help="JSON file {\"Qualified::Name\": [rva, ...]} (see ghidra/ExportSymbols.java)")
    ap.add_argument("--tick", help="RVA of a function called regularly on the game thread, also while idle (needed for -g)")
    ap.add_argument("--turn", help="RVA of a once-per-turn function (optional)")
    ap.add_argument("--module-regex", help="regex for the game module name (default: real GameCore, not proxies)")
    ap.add_argument("--wait", action="store_true", help="wait for Civ VI to start instead of failing")
    args = ap.parse_args()

    dev = frida.get_local_device()
    proc = None
    while proc is None:
        proc = next((p for p in dev.enumerate_processes() if p.name in ((args.process,) if args.process else NAMES)), None)
        if proc is None:
            if not args.wait:
                sys.exit("Civ VI is not running (use --wait to wait for it)")
            time.sleep(1)
    print("attaching to", proc.name, proc.pid)
    session = dev.attach(proc.pid)
    global ATTACHED
    ATTACHED = True
    gone = threading.Event()
    session.on("detached", lambda reason, crash: (print("session ended:", reason), gone.set()))
    with open(os.path.join(HERE, "agent.js"), encoding="utf-8") as f:
        script = session.create_script(f.read(), name="live-agent")
    hub = Hub(script)
    script.on("message", hub.on_message)
    script.load()
    syms = load_symbols(args.symbols)
    print("symbols:", hub.rpc("setsymbols", syms))
    cfg = {}
    if args.tick: cfg["tick"] = int(args.tick, 0)
    if args.turn: cfg["turn"] = int(args.turn, 0)
    if args.module_regex: cfg["moduleRegex"] = args.module_regex
    print("configure:", hub.rpc("configure", cfg))
    os.makedirs(os.path.join(HERE, "crashes"), exist_ok=True)
    hub.rpc("line", "state.liveDir = " + json.dumps(HERE), "now")   # cmds/crash.js writes its reports to <this folder>/crashes
    try:
        print("refresh:", hub.rpc("refresh"))
    except Exception as e:      # never exit after attaching: leaving = detaching = the game crashes
        print("first refresh failed, the watcher retries:", e)
    token = secrets.token_hex(8)
    with open(TOKEN, "w") as f:
        f.write("%d %s" % (args.port, token))
    srv = Server(("127.0.0.1", args.port), Handler)
    srv.hub, srv.token, srv.timeout = hub, token, args.timeout
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    threading.Thread(target=watcher, args=(hub, gone), daemon=True).start()
    hub.add_log("daemon up, pid %d, port %d" % (proc.pid, args.port))
    print("ready on 127.0.0.1:%d. Close the game to end this process (never detach)." % args.port)
    try:
        gone.wait()
    except KeyboardInterrupt:
        print("Ctrl+C: leaving the agent in the game (hooks stay). Closing the game is the clean way out.")
        os._exit(0)
    srv.shutdown()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("FATAL:", e)
        if ATTACHED:   # exiting now would detach from the game and crash it: stay alive instead
            print("still attached; staying alive. Close the game to end this process.")
            import threading
            threading.Event().wait()
        raise
