// Lua bridge (work in progress). The Lua VM is HavokScript_FinalRelease.dll, which exports a C++-mangled API we can call directly
// (loadstring, pcall, tolstring, settop, ...). lua_State pointers are discovered by watching a frequently called function that takes the state (luagetprop).
//
//   luastates [ms=3000]   which lua_State* values call GetProperty, from which thread, how often (read-only discovery)
//   lua CODE              run Lua CODE in the lua_State of the game thread (see state.luaL), on the game thread; prints returned values
(function () {
  const HS = 'HavokScript_FinalRelease.dll';
  let exportsByName = null;
  function hsExport(sub) {
    if (!exportsByName) { exportsByName = {}; Process.getModuleByName(HS).enumerateExports().forEach(function (e) { exportsByName[e.name] = e.address; }); }
    const k = Object.keys(exportsByName).filter(function (n) { return n.indexOf(sub) === 0; });
    if (k.length !== 1) throw new Error('export ' + sub + ' matches ' + k.length + ': ' + k.slice(0, 5).join(' | '));
    return exportsByName[k[0]];
  }
  state.hsExport = hsExport;

  const seen = state.luaSeen || (state.luaSeen = {});   // L -> {threads: {tid: n}}
  state.luaCapture = false;
  // A function that receives the lua_State* as its first argument and is called very often by UI Lua (in our build a property getter, ~1,800 calls/s).
  // Give its RVA with `luagetprop RVA`, or a symbol name if you loaded a table. Every live UI state shows up here with its call count.
  function installGetProp(x) {
    hook('lua_getprop', x, { onEnter: function (args) {
      if (!state.luaCapture) return;
      const L = args[0].toString();
      const e = seen[L] || (seen[L] = { threads: {} });
      const t = Process.getCurrentThreadId();
      e.threads[t] = (e.threads[t] || 0) + 1;
    } });
  }
  defcmd('luagetprop', 'luagetprop RVA|name: the very frequently called function that takes lua_State* as first argument (needed by luastates)', function (a) {
    installGetProp(/^0x/i.test(a[0]) ? parseInt(a[0], 16) : a[0]);
    return 'hooked ' + a[0];
  });

  defcmd('luastates', 'luastates [ms=3000]: lua_State* values seen in GetProperty, with threads and counts', function (a) {
    const ms = a.length ? parseInt(a[0]) : 3000;
    Object.keys(seen).forEach(function (k) { delete seen[k]; });
    state.luaCapture = true;
    return new Promise(function (res) {
      setTimeout(function () {
        state.luaCapture = false;
        res(Object.keys(seen).map(function (L) { return L + '  threads ' + JSON.stringify(seen[L].threads); }).join('\n') || 'no GetProperty calls seen');
      }, ms);
    });
  });

  // ---- running Lua ----------------------------------------------------------------------------------------------------
  const nfs = {};
  function hs(prefix, ret, args) {
    const k = prefix + '|' + ret + args.join(',');
    return nfs[k] || (nfs[k] = new NativeFunction(hsExport(prefix), ret, args));
  }
  // Runs `code` in lua_State L (must be called on the thread that owns L = game thread); returns {ok, values:[...]} with every result converted by lua_tolstring
  // (so numbers/strings work; wrap other values in tostring() inside the Lua code).
  function runLua(L, code) {
    const gettop = hs('?hksi_lua_gettop@', 'int', ['pointer']);
    const settop = hs('?hksi_lua_settop@', 'void', ['pointer', 'int']);
    const tolstring = hs('?hksi_lua_tolstring@', 'pointer', ['pointer', 'int', 'pointer']);
    const pcall = hs('?hksi_lua_pcall@', 'int', ['pointer', 'int', 'int', 'int']);
    const load = hs('?hksi_hksL_loadstring@', 'int', ['pointer', 'pointer', 'pointer']);
    const defSettings = hs('?getDefaultCompilerSettings@HksStateSettings@@', 'pointer', []);
    const top0 = gettop(L);
    const src = Memory.allocUtf8String(code);
    let rc = load(L, defSettings(), src);
    const str = function (i) { const p = tolstring(L, i, ptr(0)); return p.isNull() ? '<' + 'non-string>' : p.readUtf8String(); };
    if (rc !== 0) { const m = str(-1); settop(L, top0); return { ok: false, stage: 'load', error: m }; }
    rc = pcall(L, 0, -1, 0);
    const top = gettop(L);
    const vals = [];
    for (let i = top0 + 1; i <= top; i++) vals.push(str(i));
    settop(L, top0);
    return rc === 0 ? { ok: true, values: vals } : { ok: false, stage: 'run', error: vals.join(' | ') };
  }
  state.runLua = runLua;
  defcmd('luaon', 'luaon ADDR: choose the lua_State* used by `lua`', function (a) { state.luaL = ptr(a[0]); return 'lua state = ' + state.luaL; });
  defcmd('lua', 'lua CODE: run Lua in the chosen lua_State (see luastates/luaon) on the game thread; use `return ...`', function (a) {
    if (!state.luaL) throw new Error('no lua state chosen: luastates, then luaon ADDR');
    const r = runLua(state.luaL, a.join(' '));
    if (!r.ok) throw new Error('lua ' + r.stage + ' error: ' + r.error);
    return r.values.join('\t');
  }, { game: true });
  defcmd('luaprobe', 'luaprobe ADDR: identify the context of a lua_State (gameplay/UI) with a few harmless global checks', function (a) {
    const L = ptr(a[0]);
    return runLua(L, "return tostring(GameEvents~=nil)..' '..tostring(Events~=nil)..' '..tostring(ContextPtr~=nil)..' '..tostring(UI~=nil)..' '..tostring(Game~=nil and Game.GetCurrentGameTurn and Game.GetCurrentGameTurn())");
  }, { game: true });
})();

// ---- state discovery: opt-in, READ-ONLY. NEVER run Lua in a state you only know from an old recording: most states are short-lived coroutines;
// pushing onto a freed lua_State corrupts the heap (crashed the game with heap corruption 0xc0000374 on 2026-10-03). Only use states that call into
// GetProperty over and over (long-lived UI contexts), and re-check with `luastates` right before using one.
(function () {
  if (!state.pcallHooked) {
    state.pcallHooked = true; state.pcallOn = false; state.pcallSeen = {};
    Interceptor.attach(state.hsExport('?hksi_lua_pcall@'), { onEnter: function (args) {
      if (!state.pcallOn) return;
      const L = args[0].toString(); const t = Process.getCurrentThreadId();
      const e = state.pcallSeen[L] || (state.pcallSeen[L] = {}); e[t] = (e[t] || 0) + 1;
    } });
  }
  defcmd('luapcalls', 'luapcalls [ms=3000]: READ-ONLY count of lua_State* values calling lua_pcall, by thread (slows the game while running; short windows only)', function (a) {
    const ms = Math.min(a.length ? parseInt(a[0]) : 3000, 5000);
    state.pcallSeen = {}; state.pcallOn = true;
    return new Promise(function (res) { setTimeout(function () {
      state.pcallOn = false;
      const rows = Object.keys(state.pcallSeen).map(function (L) { const t = state.pcallSeen[L]; return [L, Object.keys(t).reduce(function (n, k) { return n + t[k]; }, 0), JSON.stringify(t)]; });
      rows.sort(function (x, y) { return y[1] - x[1]; });
      res(rows.slice(0, 30).map(function (r) { return r[0] + '  ' + r[1] + '  ' + r[2]; }).join('\n') + '\n(' + rows.length + ' states total, top 30 shown)');
    }, ms); });
  });
})();
