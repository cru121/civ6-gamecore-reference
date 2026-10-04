'use strict';
// Live-agent core. Loaded once by live_daemon.py; NEVER unloaded (detaching a Frida session crashes Civ VI, see LESSONS.md).
// Everything below is exposed to command files (cmds/*.js) and to evals as globals.
//
//   addr(x) / fn(x, ret, argTypes) / call(x, ret, argTypes, argValues)
//        x = symbol name from the table given with --symbols ('Ns::Class::Func', 'Name#2' for the 2nd overload), '0x1c8250' (RVA) or a number (RVA)
//   sym(text)                 search symbol names (substring, case-insensitive) -> [{name, rva}]
//   hook(id, x, {onEnter,onLeave})   idempotent by id; re-installed automatically if GameCore is reloaded; unhook(id)
//   defcmd(name, help, fn, opts)     register a command: fn(argsArray) -> value.   opts.game = true -> run on the game thread
//   onGame(fn) / onTurn(fn)   run fn on the game thread at the next tick / at the next BeginTurn; both return a Promise
//   onRebase(fn)              called after GameCore was (re)loaded at a new base address
//   log(msg)                  line into the daemon log (also returned to the caller of the command that produced it)
//   state                     plain object that survives re-loading of command files
const G = globalThis;
let MODRE = /^GameCore_(?!.*CE)\w*\.dll$/i;   // default: the game's own GameCore module, not a proxy such as a Community Extension DLL; override with configure({moduleRegex})
let TICK_RVA = null;          // a function called regularly on the game thread, also while the game is idle (set with --tick / configure); without it -g jobs are unavailable
let TURN_RVA = null;          // optional: a once-per-turn function (--turn); also teaches the daemon the game thread

let SYM = {};                 // name -> [rva, ...]
let SYMLIST = null;           // lazy [[nameLower, name, rva]]
let modbase = null, modname = null;
const fcache = new Map();
const hooks = new Map();      // id -> {rva, cb, listener}
const cmds = new Map();       // name -> {help, fn, opts, file}
const rebaseCbs = new Map();  // key -> fn
const jobs = { game: [], turn: [] };
const tickTids = {};
let gameTid = 0, tickCount = 0, turnCount = 0, running = false, calib = null;
G.state = G.state || {};

function log(m) { send({ k: 'log', t: Date.now(), msg: String(m) }); }
G.log = log;

function gc() {
  const m = Process.enumerateModules().find(function (x) { return MODRE.test(x.name); });
  return m || null;
}
function rvaOf(x) {
  if (typeof x === 'number') return x;
  if (typeof x === 'string') {
    if (/^0x[0-9a-f]+$/i.test(x)) return parseInt(x, 16);
    let name = x, nth = 0;
    const m = /^(.*)#(\d+)$/.exec(x);
    if (m) { name = m[1]; nth = parseInt(m[2]) - 1; }
    const r = SYM[name] || SYM['GameCore::' + name];
    if (!r) throw new Error('unknown symbol: ' + x);
    if (nth >= r.length) throw new Error('symbol ' + name + ' has only ' + r.length + ' addresses');
    return r[nth];
  }
  throw new Error('bad address spec: ' + x);
}
G.rvaOf = rvaOf;
G.addr = function (x) { if (!modbase) throw new Error('GameCore is not loaded'); return modbase.add(rvaOf(x)); };
G.base = function () { return modbase; };
G.allsyms = function () { return SYM; };   // name -> [rva, ...] as loaded with --symbols (used by cmds/crash.js)
G.tickRva = function () { return TICK_RVA; };   // the configured tick function (--tick) or null
G.fn = function (x, ret, args) {
  const key = rvaOf(x) + '|' + ret + '|' + (args || []).join(',');
  let f = fcache.get(key);
  if (!f) { f = new NativeFunction(G.addr(x), ret || 'void', args || []); fcache.set(key, f); }
  return f;
};
G.call = function (x, ret, args, vals) { return G.fn(x, ret, args).apply(null, vals || []); };
G.sym = function (text) {
  if (!SYMLIST) {
    SYMLIST = [];
    Object.keys(SYM).forEach(function (n) {
      SYM[n].forEach(function (r, i) { SYMLIST.push([n.toLowerCase(), i ? n + '#' + (i + 1) : n, r]); });
    });
  }
  const t = String(text).toLowerCase();
  const out = [];
  for (let i = 0; i < SYMLIST.length && out.length < 200; i++) {
    if (SYMLIST[i][0].indexOf(t) >= 0) out.push({ name: SYMLIST[i][1], rva: '0x' + SYMLIST[i][2].toString(16) });
  }
  return out;
};

// ---- hooks -----------------------------------------------------------------------------------------------------------
// Listeners are NEVER detached: detaching a hot hook from the Frida thread deadlocked (hung) the game on 2026-10-03.
// unhook() / re-hook only switch the old callback off (the empty trampoline stays; it costs one JS call per hit).
function install(h) {
  h.listener = Interceptor.attach(modbase.add(h.rva), {
    onEnter: function (args) { if (h.active && h.cb.onEnter) h.cb.onEnter.call(this, args); },
    onLeave: function (ret) { if (h.active && h.cb.onLeave) h.cb.onLeave.call(this, ret); }
  });
}
G.hook = function (id, x, cb) {
  if (typeof cb === 'function') cb = { onEnter: cb };
  const rva = rvaOf(x);
  const old = hooks.get(id);
  if (old && old.rva === rva) { old.cb = cb; old.active = true; return; }   // same target: just swap the callback
  if (old) old.active = false;
  const h = { rva: rva, cb: cb, active: true, listener: null };
  hooks.set(id, h);
  if (modbase) install(h);
};
G.unhook = function (id) { const h = hooks.get(id); if (h) { h.active = false; h.cb = {}; } };
G.onRebase = function (fn, key) { rebaseCbs.set(key || fn.toString().slice(0, 80), fn); };

function tick() {
  if (running) return;
  const tid = Process.getCurrentThreadId();
  if (calib) calib[tid] = (calib[tid] || 0) + 1;
  tickCount++;
  if (!gameTid) {                                  // learn the game thread: first thread to reach 60 tick calls (~5 s)
    tickTids[tid] = (tickTids[tid] || 0) + 1;
    if (tickTids[tid] >= 60) { gameTid = tid; log('game thread id = ' + tid + ' (learned from tick hook)'); }
  }
  if (jobs.game.length && gameTid && tid === gameTid) runJobs(jobs.game);
}
function runJobs(list) {
  running = true;
  try {
    while (list.length) {
      const j = list.shift();
      try { j.res(j.fn()); } catch (e) { j.rej(e); }
    }
  } finally { running = false; }
}
function installCore() {
  if (TICK_RVA !== null) G.hook('__tick', TICK_RVA, { onEnter: tick });
  if (TURN_RVA !== null) {
    G.hook('__turn', TURN_RVA, {
      onEnter: function () {
        turnCount++;
        if (!gameTid) { gameTid = Process.getCurrentThreadId(); log('game thread id = ' + gameTid + ' (learned from the turn hook)'); }
        runJobs(jobs.turn);
      }
    });
  }
}

// Called by the daemon about once a second: detects GameCore being (re)loaded (the game unloads it when you load a game from the menu).
G.refresh = function () {
  const m = gc();
  if (!m) {
    if (modbase) { log('GameCore unloaded'); modbase = null; fcache.clear(); hooks.forEach(function (h) { h.listener = null; }); }
    return 'not loaded';
  }
  if (modbase && m.base.equals(modbase)) return 'ok';
  try {   // the module can be mapped before it is initialised (game start-up): do nothing until the hook targets decode
    if (TICK_RVA !== null) Instruction.parse(m.base.add(rvaOf(TICK_RVA)));
    if (TURN_RVA !== null) Instruction.parse(m.base.add(rvaOf(TURN_RVA)));
  } catch (e) { return 'not ready'; }
  const first = !G.__loadedOnce;
  modbase = m.base; modname = m.name; fcache.clear();
  hooks.forEach(function (h) { h.listener = null; });        // old listeners died with the old image: do not detach them
  try {
    installCore();
    hooks.forEach(function (h) { if (!h.listener) install(h); });
  } catch (e) { log('hook install failed, will retry: ' + e.message); modbase = null; return 'retry'; }
  G.__loadedOnce = true;
  if (!first) gameTid = 0;                                   // thread may differ after a reload; BeginTurn / calibrate re-learn it
  log('GameCore ' + modname + ' at ' + modbase + (first ? ' (first load)' : ' (moved): hooks re-installed'));
  rebaseCbs.forEach(function (f) { try { f(modbase); } catch (e) { log('onRebase failed: ' + e); } });
  return first ? 'loaded' : 'rebased';
};

// ---- scheduling ------------------------------------------------------------------------------------------------------
G.onGame = function (fn) {
  return new Promise(function (res, rej) {
    if (!modbase) return rej(new Error('GameCore is not loaded'));
    if (!gameTid) return rej(new Error('game thread unknown: run `calibrate` (needs the game to be running and idle) or end one turn'));
    jobs.game.push({ fn: fn, res: res, rej: rej });
  });
};
G.onTurn = function (fn) { return new Promise(function (res, rej) { jobs.turn.push({ fn: fn, res: res, rej: rej }); }); };

// ---- commands --------------------------------------------------------------------------------------------------------
G.defcmd = function (name, help, fn, opts) { cmds.set(name, { help: help, fn: fn, opts: opts || {}, file: G.__curfile || '' }); };
function tokens(line) {
  const out = []; const re = /"([^"]*)"|'([^']*)'|(\S+)/g; let m;
  while ((m = re.exec(line))) out.push(m[1] !== undefined ? m[1] : m[2] !== undefined ? m[2] : m[3]);
  return out;
}
function ser(v) {
  if (v === undefined) return 'undefined';
  if (typeof v === 'string') return v;
  return JSON.stringify(v, function (k, x) { return typeof x === 'bigint' ? x.toString() : x; }, 2);
}
function exec(mode, fn) {
  let p;
  if (mode === 'game') p = G.onGame(fn);
  else if (mode === 'turn') p = G.onTurn(fn);
  else p = new Promise(function (res, rej) { try { res(fn()); } catch (e) { rej(e); } });
  return p.then(ser);
}
function failure(e) { return Promise.reject(new Error(String(e && e.stack ? e.stack : e))); }

rpc.exports = {
  // line: a registered command ("records limbo") or, if the first word is not a command, JavaScript. mode: now|game|turn|auto
  line: function (line, mode) {
    line = String(line).trim();
    const t = tokens(line); const c = t.length ? cmds.get(t[0]) : null;
    const m = mode && mode !== 'auto' ? mode : null;
    if (c) return exec(m || (c.opts.game ? 'game' : 'now'), function () { return c.fn(t.slice(1)); }).catch(failure);
    return exec(m || 'now', function () { return (0, eval)(line); }).catch(failure);
  },
  loadfile: function (name, code) {
    G.__curfile = name;
    Array.from(cmds).forEach(function (kv) { if (kv[1].file === name) cmds.delete(kv[0]); });   // a reloaded file replaces its own commands
    try { (0, eval)(code + '\n//# sourceURL=' + name); } finally { G.__curfile = ''; }
    return Array.from(cmds).filter(function (kv) { return kv[1].file === name; }).map(function (kv) { return kv[0]; });
  },
  setsymbols: function (obj) { SYM = obj; SYMLIST = null; return Object.keys(SYM).length; },
  refresh: function () { return G.refresh(); },
  configure: function (cfg) {
    if (cfg.moduleRegex) MODRE = new RegExp(cfg.moduleRegex, 'i');
    if (cfg.tick !== undefined && cfg.tick !== null) TICK_RVA = cfg.tick;
    if (cfg.turn !== undefined && cfg.turn !== null) TURN_RVA = cfg.turn;
    if (modbase) { installCore(); }
    return { tick: TICK_RVA, turn: TURN_RVA, moduleRegex: String(MODRE) };
  },
  status: function () {
    return {
      module: modname, base: modbase ? modbase.toString() : null, gameTid: gameTid, tickCount: tickCount, turnCount: turnCount,
      pendingGame: jobs.game.length, hooks: Array.from(hooks.keys()), commands: cmds.size, symbols: Object.keys(SYM).length, pid: Process.id
    };
  },
  help: function () {
    return Array.from(cmds).sort().map(function (kv) { return kv[0] + (kv[1].opts.game ? ' [game]' : '') + '  - ' + kv[1].help; }).join('\n');
  }
};

// ---- built-in commands -----------------------------------------------------------------------------------------------
function rvaArg(s) { return /^0x/i.test(s) ? parseInt(s, 16) : /^\d+$/.test(s) ? parseInt(s) : s; }
G.defcmd('status', 'agent state (base, game thread, hooks, ...)', function () { return rpc.exports.status(); });
G.defcmd('help', 'list commands', function () { return rpc.exports.help(); });
G.defcmd('sym', 'sym TEXT: search symbol names of the loaded symbol table (first 60)', function (a) {
  const r = G.sym(a.join(' '));
  return r.slice(0, 60).map(function (x) { return x.rva + '  ' + x.name; }).join('\n') + (r.length > 60 ? '\n... ' + r.length + '+ matches, refine the text' : '');
});
G.defcmd('calibrate', 'calibrate [ms=3000]: count tick-hook calls per thread and pick the busiest as the game thread', function (a) {
  const ms = a.length ? parseInt(a[0]) : 3000;
  calib = {};
  return new Promise(function (res) {
    setTimeout(function () {
      const c = calib; calib = null;
      const rows = Object.keys(c).map(function (t) { return [t, c[t]]; }).sort(function (x, y) { return y[1] - x[1]; });
      if (rows.length && !gameTid) { gameTid = parseInt(rows[0][0]); log('game thread id = ' + gameTid + ' (busiest in calibrate)'); }
      res({ gameTid: gameTid, calls_per_thread: rows });
    }, ms);
  });
});
G.defcmd('setgametid', 'setgametid TID: force the game thread id', function (a) { gameTid = parseInt(a[0]); return gameTid; });
G.defcmd('peek', 'peek RVA|name [n=64]: hexdump n bytes at a GameCore address', function (a) {
  return hexdump(G.addr(rvaArg(a[0])), { length: a[1] ? parseInt(a[1]) : 64, ansi: false });
});
G.defcmd('prologue', 'prologue NAME|RVA: first 16 bytes of a function (checks a mapped address)', function (a) {
  return Array.from(new Uint8Array(G.addr(rvaArg(a[0])).readByteArray(16))).map(function (b) { return ('0' + b.toString(16)).slice(-2); }).join(' ');
});
