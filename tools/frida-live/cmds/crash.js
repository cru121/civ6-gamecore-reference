// crash: in-process crash reporter. Hot-loaded; installs a Frida exception handler (first-chance, ALWAYS passes the exception on, so game behaviour is unchanged).
// On an access violation / illegal instruction / arithmetic / abort ... it writes a named report (daemon log, state.crash.reports, crashes/*.txt):
//   faulting instruction + function name (old->new symbol table), memory operation and address, registers annotated with symbols, accurate backtrace,
//   heuristic call-site scan of the raw stack, and the ring buffer of recent calls to functions you asked to watch (`crash watch TEXT`).
// Limits: a hard fast-fail (heap corruption 0xc0000374, __fastfail) may never reach the handler; use Windows LocalDumps for those (see README).
// First-chance exceptions that the game itself handles (SEH) also show up: the report says "first-chance"; repeated ones are only counted.
const CRASH_DIR = state.liveDir ? state.liveDir + '\\crashes\\' : null;   // set by the daemon; null = reports only go to the daemon log
const GC_RE = /^GameCore_(?!.*CE)\w*\.dll$/i;
const IGNORE = { 'breakpoint': 1, 'single-step': 1, 'guard-page': 1 };
const MAX_FILES = 40, RING = 256, MAX_BT = 24;

const C = state.crash = state.crash || { on: true, reports: [], seen: {}, files: 0, ring: [], ringPos: 0, seq: 0, watched: [], table: null, tableErr: null, total: 0 };

function loadTable() {
  if (C.table) return C.table;
  try {
    const o = globalThis.allsyms ? globalThis.allsyms() : {}; const arr = [];
    Object.keys(o).forEach(function (n) { o[n].forEach(function (r, i) { arr.push([r, i ? n + '#' + (i + 1) : n]); }); });
    arr.sort(function (a, b) { return a[0] - b[0]; });
    C.table = arr; C.tableErr = null;
  } catch (e) { C.table = []; C.tableErr = String(e); }
  return C.table;
}
function lookup(rva) {            // nearest mapped function start at or before rva
  const t = loadTable(); let lo = 0, hi = t.length - 1, best = -1;
  while (lo <= hi) { const mid = (lo + hi) >> 1; if (t[mid][0] <= rva) { best = mid; lo = mid + 1; } else hi = mid - 1; }
  return best < 0 ? null : { name: t[best][1].replace(/^GameCore::/, ''), off: rva - t[best][0] };
}
function hex(n) { return '0x' + n.toString(16); }
function rvaIn(p, m) { return parseInt(p.sub(m.base).toString(), 16); }
function where(p) {               // 'GameCore!Func+0x1c' | 'mod.dll+0x123' | ''
  try {
    p = ptr(p); const m = Process.findModuleByAddress(p); if (!m) return '';
    const rva = rvaIn(p, m);
    if (GC_RE.test(m.name)) {
      const rg = Process.findRangeByAddress(p);
      if (rg && rg.protection.indexOf('x') < 0) return 'GameCore.data+' + hex(rva) + '  (not code: global/static data)';
      const l = lookup(rva); return l ? 'GameCore!' + l.name + '+' + hex(l.off) + (l.off > 0x4000 ? ' (?far: function probably not in the map)' : '') + '  [rva ' + hex(rva) + ']' : 'GameCore+' + hex(rva); }
    let s = m.name + '+' + hex(rva);
    try { const d = DebugSymbol.fromAddress(p); if (d && d.name) s += ' (~nearest export: ' + d.name + ', not necessarily this function)'; } catch (e) { /* no symbols */ }
    return s;
  } catch (e) { return ''; }
}
function gcModule() { return Process.enumerateModules().find(function (x) { return GC_RE.test(x.name); }) || null; }
function describeAddr(p) {
  p = ptr(p); const v = BigInt(p.toString());
  let s = p.toString();
  if (v < 0x10000n) s += '  (null + ' + hex(Number(v)) + ': null-pointer dereference through a member offset)';
  else if (v === 0xddddddddddddddddn || v === 0xfeeefeeefeeefeeen || v === 0xcdcdcdcdcdcdcdcdn) s += '  (debug-heap fill pattern: freed/uninitialised)';
  else {
    const w = where(p); if (w) s += '  = ' + w;
    else {
      const r = Process.findRangeByAddress(p);
      s += r ? '  (in ' + r.protection + ' range ' + r.base + '+' + hex(r.size) + (r.file ? ' ' + r.file.path : '') + ')' : '  (UNMAPPED)';
    }
  }
  return s;
}
function isCallSite(p) {          // return address preceded by a call instruction?
  try {
    const b = new Uint8Array(p.sub(8).readByteArray(8));      // b[7] is the byte right before p
    if (b[3] === 0xE8) return true;                            // call rel32 (5 bytes)
    for (let n = 2; n <= 7; n++) { const i = 8 - n; if (b[i] === 0xFF && ((b[i + 1] >> 3) & 7) === 2) return true; }   // call r/m
  } catch (e) { /* unreadable */ }
  return false;
}
function stackScan(rsp, gc, count) {
  const out = [];
  try {
    const buf = ptr(rsp).readByteArray(count * 8); const q = new BigUint64Array(buf);
    const lo = BigInt(gc.base.toString()), hi = lo + BigInt(gc.size);
    for (let i = 0; i < q.length && out.length < 40; i++) {
      if (q[i] >= lo && q[i] < hi) { const p = ptr(q[i].toString()); if (isCallSite(p)) out.push('  rsp+' + hex(i * 8) + '  ' + where(p)); }
    }
  } catch (e) { out.push('  (stack not readable: ' + e.message + ')'); }
  return out;
}

function buildReport(d, simulated) {
  const L = []; const ctx = d.context; const tid = Process.getCurrentThreadId();
  let gameTid = 0; try { gameTid = rpc.exports.status().gameTid; } catch (e) { /* agent status unavailable */ }
  L.push('=== CRASH REPORT ' + new Date().toISOString() + (simulated ? '  (SIMULATED, nothing actually faulted)' : '') + ' ===');
  L.push('type      : ' + d.type + (IGNORE[d.type] ? '' : '   (first-chance: the game may handle it itself)'));
  L.push('thread    : ' + tid + (gameTid ? (tid === gameTid ? '  (= game thread)' : '  (NOT the game thread ' + gameTid + ')') : ''));
  L.push('fault at  : ' + d.address + '  ' + where(d.address));
  if (d.memory) L.push('memory    : ' + d.memory.operation + ' ' + describeAddr(d.memory.address));
  try {
    const ins = Instruction.parse(ptr(d.address)); const bytes = Array.from(new Uint8Array(ptr(d.address).readByteArray(Math.max(ins.size, 1)))).map(function (x) { return ('0' + x.toString(16)).slice(-2); }).join(' ');
    L.push('instr     : ' + ins.mnemonic + ' ' + ins.opStr + '    [' + bytes + ']');
  } catch (e) { L.push('instr     : (cannot decode at fault address: ' + e.message + ')'); }
  const gc = gcModule(); if (gc) L.push('GameCore  : ' + gc.name + ' base ' + gc.base + ' size ' + hex(gc.size));
  if (ctx) {
    L.push('registers :');
    ['rip', 'rsp', 'rbp', 'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15'].forEach(function (r) {
      try {
        const v = ctx[r]; let note = ''; const bi = BigInt(v.toString());
        if (bi < 0x10000n) note = bi === 0n ? '' : '  (small: could be an enum/index)'; else if (r !== 'rsp' && r !== 'rbp') note = where(v) ? '  ' + where(v) : '';
        L.push('  ' + (r + '   ').slice(0, 4) + ' ' + v + note);
      } catch (e) { /* register missing */ }
    });
    let bt = [];
    try { bt = Thread.backtrace(ctx, Backtracer.ACCURATE); } catch (e1) { try { bt = Thread.backtrace(ctx, Backtracer.FUZZY); L.push('(ACCURATE backtrace failed: ' + e1.message + '; FUZZY used)'); } catch (e2) { L.push('(backtrace failed: ' + e2.message + ')'); } }
    L.push('backtrace : (#0 = faulting instruction, then callers)'); L.push('  #0 ' + d.address + '  ' + where(d.address)); bt.slice(0, MAX_BT).forEach(function (a, i) { L.push('  #' + (i + 1) + ' ' + a + '  ' + where(a)); });
    if (!bt.length) L.push('  (none)');
    try {   // execution went to an address outside any module (bad function pointer / vtable): the caller's return address is at [rsp]
      if (!Process.findModuleByAddress(ptr(d.address))) { const ra = ctx.rsp.readPointer(); L.push('likely caller (return address at [rsp], fault was a jump/call to a bad address): ' + ra + '  ' + where(ra)); }
    } catch (e) { /* stack unreadable */ }
    if (gc) { L.push('stack scan (candidate return addresses in GameCore within 0x800 bytes of rsp; may contain stale entries):'); stackScan(ctx.rsp, gc, 256).forEach(function (s) { L.push(s); }); }
  }
  const ring = C.ring.length < RING ? C.ring.slice() : C.ring.slice(C.ringPos).concat(C.ring.slice(0, C.ringPos));
  if (C.watched.length) {
    L.push('recent watched calls (oldest first, last 40; * = crashing thread): ' + C.watched.length + ' functions watched');
    ring.slice(-40).forEach(function (e) { L.push('  #' + e.seq + ' ' + (e.tid === tid ? '*' : ' ') + 'tid ' + e.tid + ' ' + e.name + '(this=' + e.a0 + ')'); });
  } else L.push('recent calls: none recorded (use `crash watch TEXT` to record calls of functions matching TEXT)');
  if (C.tableErr) L.push('(symbol table failed to load: ' + C.tableErr + ')');
  return L.join('\n');
}

function onException(d) {
  if (!C.on || IGNORE[d.type]) return;
  C.total++;
  const m = Process.findModuleByAddress(ptr(d.address));
  const key = d.type + '@' + (m ? m.name + '+' + hex(rvaIn(ptr(d.address), m)) : d.address);
  const seen = C.seen[key];
  if (seen) { seen.count++; return; }
  const rep = { time: Date.now(), type: d.type, key: key, count: 1, file: null, text: null };
  C.seen[key] = rep;
  rep.text = buildReport(d, false);
  C.reports.push(rep); if (C.reports.length > 30) C.reports.shift();
  if (CRASH_DIR && C.files < MAX_FILES) {
    try {
      const name = CRASH_DIR + new Date().toISOString().replace(/[:.]/g, '-') + '_' + d.type + '.txt';
      const f = new File(name, 'w'); f.write(rep.text + '\n'); f.flush(); f.close(); rep.file = name; C.files++;
    } catch (e) { rep.file = '(not written: ' + e.message + ')'; }
  }
  log('[crash] ' + d.type + ' at ' + where(d.address) + (d.memory ? '  ' + d.memory.operation + ' ' + d.memory.address : '') + (rep.file ? '  -> ' + rep.file : '') + '\n' + rep.text);
}
Process.setExceptionHandler(function (d) { try { onException(d); } catch (e) { try { log('[crash] handler error: ' + e); } catch (e2) { /* nothing more to do */ } } return false; });   // false = pass on, behaviour unchanged

function ringPush(name, a0) {
  const e = { seq: ++C.seq, tid: Process.getCurrentThreadId(), name: name, a0: a0 };
  if (C.ring.length < RING) C.ring.push(e); else { C.ring[C.ringPos] = e; C.ringPos = (C.ringPos + 1) % RING; }
}
if (globalThis.tickRva && globalThis.tickRva() !== null) hook('__crashtest', globalThis.tickRva(), {
  onEnter: function () {
    if (!C.testPending) return;
    C.testPending = false;
    const rep = { time: Date.now(), type: 'simulated', key: 'simulated', count: 1, file: null };
    try { rep.text = buildReport({ type: 'access-violation', address: this.context.rip, memory: { operation: 'read', address: ptr(0x18) }, context: this.context }, true); } catch (e) { rep.text = 'report failed: ' + e.stack; }
    C.testReport = rep.text;
  }
});

defcmd('crash', 'crash [on|off|last [n]|list|watch TEXT|unwatch|ring|sym ADDR..|test|clear]: crash reporter (always on after attach)', function (a) {
  const sub = a[0] || 'status';
  if (sub === 'on') { C.on = true; return 'crash reporting on'; }
  if (sub === 'off') { C.on = false; return 'crash reporting off'; }
  if (sub === 'clear') { C.reports = []; C.seen = {}; C.files = 0; C.ring = []; C.ringPos = 0; return 'cleared'; }
  if (sub === 'list') {
    return C.reports.length ? C.reports.map(function (r, i) { return '#' + i + ' ' + new Date(r.time).toLocaleTimeString() + ' x' + (C.seen[r.key] ? C.seen[r.key].count : 1) + '  ' + r.key + (r.file ? '  ' + r.file : ''); }).join('\n') : 'no exceptions recorded';
  }
  if (sub === 'last') {
    const n = a[1] ? parseInt(a[1]) : 1; const r = C.reports[C.reports.length - n];
    return r ? r.text : 'no such report (' + C.reports.length + ' recorded)';
  }
  if (sub === 'ring') return C.ring.length ? (C.ring.length < RING ? C.ring : C.ring.slice(C.ringPos).concat(C.ring.slice(0, C.ringPos))).map(function (e) { return '#' + e.seq + ' tid ' + e.tid + ' ' + e.name + '(this=' + e.a0 + ')'; }).join('\n') : 'ring empty';
  if (sub === 'watch') {
    const text = a[1]; if (!text) return 'usage: crash watch TEXT   (records calls of up to 40 mapped functions whose name contains TEXT; avoid hot ones)';
    const found = sym(text).slice(0, 40); let n = 0;
    found.forEach(function (f) {
      try { hook('crashwatch:' + f.name, f.name, { onEnter: function (args) { ringPush(f.name.replace(/^GameCore::/, ''), args[0]); } }); if (C.watched.indexOf(f.name) < 0) C.watched.push(f.name); n++; } catch (e) { /* cannot hook */ }
    });
    return 'watching ' + n + ' functions (' + C.watched.length + ' total). Each call costs one JS call; if the game slows down, `crash unwatch`.';
  }
  if (sub === 'unwatch') { C.watched.forEach(function (n) { unhook('crashwatch:' + n); }); const k = C.watched.length; C.watched = []; return 'switched off ' + k + ' watch hooks (hooks stay installed but empty; never detached)'; }
  if (sub === 'sym') {
    if (a.length < 2) return 'usage: crash sym ADDR...   (<= 0x40000000 = GameCore RVA, bigger = absolute address)';
    const gc = gcModule();
    return a.slice(1).map(function (s) {
      const v = BigInt(s); let p;
      if (v <= 0x40000000n) { if (!gc) return s + ': GameCore not loaded (RVA lookup needs the module for where(); showing table only)'; p = gc.base.add(ptr(v.toString())); } else p = ptr(v.toString());
      return s + '  ' + (where(p) || '(not in a module)');
    }).join('\n');
  }
  if (sub === 'test') {
    C.testPending = true; C.testReport = null;
    return new Promise(function (res) {
      let n = 0; const iv = setInterval(function () {
        if (C.testReport || ++n > 40) { clearInterval(iv); res(C.testReport || 'no tick hit within 4 s (is the game running and ticking? `status`)'); }
      }, 100);
    });
  }
  const gc = gcModule();
  return 'crash reporter: ' + (C.on ? 'ON' : 'off') + ', symbols ' + loadTable().length + (C.tableErr ? ' (LOAD ERROR ' + C.tableErr + ')' : '') + ', GameCore ' + (gc ? gc.name : 'not loaded') +
    '\nexceptions seen ' + C.total + ', distinct reports ' + C.reports.length + ', files written ' + C.files + ' (' + CRASH_DIR + '), watched functions ' + C.watched.length +
    '\nsubcommands: last [n] | list | watch TEXT | unwatch | ring | sym ADDR.. | test | on | off | clear';
});
loadTable();
