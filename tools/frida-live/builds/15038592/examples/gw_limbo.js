// Example for build 15038592 (GameCore_XP2_FinalRelease.dll): great-works "limbo" / relic / ghost-slot experiments as live commands. Copy this file into cmds/ to load it.
// Commands are registered at the bottom; see the long comment for what each one does.
(function () {
// Great-works "limbo" experiment (installed build 15038592; addresses are RVAs of GameCore_XP2_FinalRelease.dll).
//
// Question: does a great work that exists but sits in NO slot grant yields / tourism?
//
// Commands (type them as `python civ.py "<command> ..."`):
//   list                  candidate works (type index, object type, already created?)
//   report [player]       per-city works / yields / tourism, and the global record count
//   exists T              has work type T been created (game-wide record)?  which city holds it?
//   spawn T [player]      create work T, assign it to the player, and let the GAME place it (ReceiveGreatWork)
//   limbo T [player]      create work T and assign it to the player, but do NOT place it
//   place T [player]      try to place an existing work T via ReceiveGreatWork
//   remove T [player]     take work T out of its slot (RemoveGreatWork via edit()); it stays created, in limbo
//   removeraw T [player]  same but WITHOUT the edit() accessor (tests the edit() hypothesis)
//   relicinfo [player]    read-only: relic-holding building types, which city has which and free slots, what
//                         GetNearestRelicSlot answers right now
//   relicbase [player]    RELIC TEST 1 (baseline): call the game's CreateRelic. Fill every relic slot first (or have none);
//                         expect the record count NOT to change
//   hut [xN] [player]     a relic as the goody hut would give it: the game's own CreateRelic with a REAL plot (the capital's).
//                         On the vanilla game this shows what the game itself does with full or free relic slots (a mod that changes CreateRelic would change the outcome). xN repeats it N times.
//   records [onlylimbo]   READ-ONLY, works on any loaded game or save: every record of the game-wide great work list with its type, object type,
//                         'player' field (creator), creation turn, and the city/player that holds it - or LIMBO. 'records limbo' lists only limbo ones.
//   holders IDX           READ-ONLY: for record list index IDX, check EVERY living player's cities two ways: the game's IsInCity answer and a raw scan of each
//                         city's building slot lists (building type, slot number, raw slot words). Finds works that one check sees and the other does not.
//   findwork TEXT         READ-ONLY: list records whose definition name contains TEXT (case-insensitive), e.g. findwork RED_CLIFF
//   ghosts                READ-ONLY: scan every living player's cities for ghost slots (works held by a building the city no longer has) and count slotted works per player
//   slots TEXT|ID         READ-ONLY: full dump of one city's great work slot list. TEXT = part of the city's name key (e.g. ROME) or the numeric city id.
//                         Per building entry: type, name, whether the city HAS it, its map location (x,y), the slot count in the list vs the game's own
//                         GetNumGreatWorkSlots, and every slot (word0, slot type, work index + name). Flags oddities with '<<'.
//   --- OWNERSHIP STORAGE TESTS (where could a mod keep "who owns this archived work"?) ---
//   tag IDX VALUE [edit]  TEST E (queued): write VALUE into the otherwise-unused dword at record+0x0C of record IDX. With 'edit' the write goes through the
//                         tracked accessor (edit() on the record list at Culture+0x108) first, without it plain memory. Then SAVE, RELOAD and run 'tags':
//                         if the value is still there, the game saves that dword.
//   tags                  READ-ONLY: every record whose +0x0C dword is non-zero, plus the raw +0x10 qword of the first records (for comparison)
//   propset NAME VALUE    TEST A (queued): natively write an integer into the GAME property map (key from VariantManager::RegisterKey, value via
//                         VariantMap::SetVariant on the edit() map, like Game:SetProperty does). A Lua script can then read Game.GetProperty(NAME) to see the value (check Lua.log)
//                         from gameplay and UI states. Save/reload and look again to test persistence.
//   makeghost B [player]  WRITE (next turn): create a ghost the way city capture does: SetBuildingLocation(building B, -1) on the first city that has B, WITHOUT removing
//                         its slot entry. Test with B=1 (Palace). Logs HasBuilding before/after and whether the slot entry is still there.
//   unghost [player]      WRITE (runs now on the game thread): for every city of the player, find works sitting in the slot list of a building the
//                         city no longer HAS (a leftover/ghost slot), remove each from that city (via edit()) and re-place it with ReceiveGreatWork
//                         (first city with a free suitable slot; if none, it stays in limbo). Also drops the dead (building-less) slot entries, empty ones
//                         included, with the game's own RemoveGreatWorkSlots, BEFORE re-placing. Logs every step.
//   rmbuilding B [player] remove building type B from the player's first city that has it (City::Buildings::RemoveBuilding via edit()),
//                         like a destroyed building. Logs which works the building held and where they are afterwards.
//                         (Try B=1, the Palace, with a work in it: the game may refuse; any building with great work slots works.)
//   reliclimbo [B=NN] [player]  RELIC TEST 2: call AddRelic with a valid city + relic building (default: first from the relic
//                         list) and an OUT-OF-RANGE slot; expect a new record that no slot holds
// Reads run immediately. Writes (spawn/limbo/place) are queued and run at the start of the NEXT game turn, inside the
// game's own BeginTurn call (game thread). So: type the command, then end your turn.
const RVA = {
    "cultureGet": 0x1c8250,   // Game::Culture::Get
    "editPlayer": 0x44f00,    // Context::Globals::EditPlayer
    "findOrAdd": 0x1c80e0,    // Game::Culture::FindOrAddGreatWork
    "setPlayer": 0x1c8c80,    // Game::Culture::SetGreatWorkPlayer
    "receive": 0x282c20,      // Player::Culture::ReceiveGreatWork
    "has": 0x1c87d0,          // Game::Culture::HasGreatWorkBeenCreated
    "getYield": 0x10c2d0,     // City::Buildings::GetYieldFromGreatWorks
    "getTourism": 0x10bdd0,   // City::Buildings::GetTourismFromGreatWorks
    "getNum": 0x10bc50,       // City::Buildings::GetNumGreatWorks
    "isInCity": 0x10cc60,     // City::Buildings::IsInCity
    "removeGW": 0x10d370,     // City::Buildings::RemoveGreatWork
    "editVar": 0x72a920,      // FAutoVariable<VariantMap,Game::Instance>::edit
    "defs": 0x7d0d80,         // Definitions::GetGreatWorkDefinitions
    "nameToObj": 0x7d8b10,    // Definition::Utility::NameToGreatWorkObjectType
    "objDefs": 0x7d0da0,      // Definitions::GetGreatWorkObjectTypeDefinitions
    "makeHash": 0x606270,     // Utilities::MakeHash
    "hasBuilding": 0x10c450,  // City::Buildings::HasBuilding
    "getFreeSlot": 0x10b7a0,  // City::Buildings::GetFreeSlot
    "nearestRelic": 0x315270, // Player::Religion::GetNearestRelicSlot
    "createRelic": 0x314710,  // Player::Religion::CreateRelic
    "addRelic": 0x1c6b80,     // Game::Culture::AddRelic
    "editMap": 0x44d40,       // Context::Globals::EditMap
    "getLoc": 0x10abf0,       // City::Buildings::GetBuildingLocation
    "removeBuilding": 0x10d1f0,  // City::Buildings::RemoveBuilding
    "playerMgr": 0x306b80,    // Player::Manager::Edit
    "isAlive": 0x307880,      // Player::Manager::IsAlive
    "bldDefs": 0x7d04a0,      // Definitions::GetBuildingDefinitions
    "numSlots": 0x10bc10,     // City::Buildings::GetNumGreatWorkSlots
    "slotType": 0x10b8e0,     // City::Buildings::GetGreatWorkSlotType
    "removeSlots": 0x10d3e0,  // City::Buildings::RemoveGreatWorkSlots (private; installed build)
    "registerKey": 0x9a3f10,  // Data::VariantManager::RegisterKey(const char*)
    "setVariant": 0x9a4380,   // Data::VariantMap::SetVariant(key, const Variant&)
    "currentGame": 0xb8aa68,  // Context::Globals::ms_pkCurrentGame (data)
    "setBldLoc": 0x10e5e0,    // City::Buildings::SetBuildingLocation(type, int location)
    "beginTurn": 0x5c2d0,     // Player::Processor::BeginTurn (anchor: once per game turn)
};
const OBJ = ['SCULPTURE', 'PORTRAIT', 'LANDSCAPE', 'RELIGIOUS', 'ARTIFACT', 'WRITING', 'MUSIC', 'RELIC'];
const YIELDS = ['FOOD', 'PRODUCTION', 'GOLD', 'SCIENCE', 'CULTURE', 'FAITH', 'YIELD6', 'YIELD7'];
let base = null, F = null;
const queue = [];


function nf(name, ret, args) { return new NativeFunction(base.add(RVA[name]), ret, args); }

function setup(mod) {
  base = mod.base;
  F = {
    cultureGet: nf('cultureGet', 'pointer', []),
    editPlayer: nf('editPlayer', 'pointer', ['int']),
    findOrAdd: nf('findOrAdd', 'int', ['pointer', 'uint']),
    setPlayer: nf('setPlayer', 'void', ['pointer', 'int', 'int']),
    receive: nf('receive', 'uint8', ['pointer', 'int']),
    has: nf('has', 'uint8', ['pointer', 'uint']),
    getYield: nf('getYield', 'int', ['pointer', 'int']),
    getTourism: nf('getTourism', 'int', ['pointer', 'uint8']),
    getNum: nf('getNum', 'int', ['pointer', 'int']),
    isInCity: nf('isInCity', 'uint8', ['pointer', 'int']),
    removeGW: nf('removeGW', 'int', ['pointer', 'int']),
    editVar: nf('editVar', 'pointer', ['pointer']),
    defs: nf('defs', 'pointer', []),
    nameToObj: nf('nameToObj', 'int', ['int']),
    objDefs: nf('objDefs', 'pointer', []),
    makeHash: nf('makeHash', 'uint', ['pointer']),
    hasBuilding: nf('hasBuilding', 'uint8', ['pointer', 'int']),
    getFreeSlot: nf('getFreeSlot', 'int', ['pointer', 'int']),
    nearestRelic: nf('nearestRelic', 'pointer', ['pointer', 'pointer', 'pointer', 'pointer']),
    createRelic: nf('createRelic', 'void', ['pointer', 'pointer', 'uint']),
    addRelic: nf('addRelic', 'int', ['pointer', 'pointer', 'int', 'int', 'uint']),
    editMap: nf('editMap', 'pointer', []),
    getLoc: nf('getLoc', 'int', ['pointer', 'int']),
    removeBuilding: nf('removeBuilding', 'void', ['pointer', 'int']),
    playerMgr: nf('playerMgr', 'pointer', []),
    isAlive: nf('isAlive', 'uint8', ['pointer', 'int']),
    bldDefs: nf('bldDefs', 'pointer', []),
    numSlots: nf('numSlots', 'int', ['pointer', 'int']),
    slotType: nf('slotType', 'int', ['pointer', 'int', 'int']),
    removeSlots: nf('removeSlots', 'void', ['pointer', 'int']),
    setBldLoc: nf('setBldLoc', 'void', ['pointer', 'int', 'int']),
    registerKey: nf('registerKey', 'uint', ['pointer', 'pointer']),
    setVariant: nf('setVariant', 'pointer', ['pointer', 'uint', 'pointer'])
  };
}

function cities(pid) {
  const p = F.editPlayer(pid);
  const out = [];
  let node = p.add(0x6d0).readPointer().add(0xd0).readPointer();
  while (!node.isNull()) { out.push(node.readPointer()); node = node.add(0x10).readPointer(); }
  return out;
}
function cityId(c) { return c.add(0xa8).readS32(); }
// City name: the game's own AddRelic gets it with a virtual call (vtable slot 0x28 of the city, returns a C string, usually a LOC key).
function cityName(c) {
  try {
    const fn = new NativeFunction(c.readPointer().add(0x28).readPointer(), 'pointer', ['pointer']);
    const p = fn(c);
    return p.isNull() ? '?' : p.readUtf8String();
  } catch (e) { return '?'; }
}
function blds(c) { return c.add(0xcb0); }
function idxOfType(t) {
  const c = F.cultureGet(); const b = c.add(0x118).readPointer(); const n = recordCount();
  for (let i = 0; i < n; i++) if (b.add(i * 0x18).readU32() === t) return i;
  return -1;
}
function recordCount() { const c = F.cultureGet(); return c.add(0x120).readPointer().sub(c.add(0x118).readPointer()).toInt32() / 0x18; }

function report(pid) {
  const cs = cities(pid);
  log('--- report player ' + pid + ': ' + cs.length + ' cities; game-wide great work records: ' + recordCount());
  let totY = {}, totT = 0, totN = 0;
  cs.forEach(function (c) {
    const b = blds(c);
    const n = F.getNum(b, -1);
    const ys = [];
    for (let y = 0; y < 8; y++) { const v = F.getYield(b, y); if (v !== 0) { ys.push(YIELDS[y] + '=' + v); totY[y] = (totY[y] || 0) + v; } }
    const t0 = F.getTourism(b, 0), t1 = F.getTourism(b, 1);
    totN += n; totT += t0;
    log('city ' + cityId(c) + ': works in slots=' + n + ' yields[' + (ys.join(' ') || 'none') + '] tourism(false)=' + t0 + ' tourism(true)=' + t1);
  });
  log('TOTAL works in slots=' + totN + ' tourism=' + totT + ' yields: ' + Object.keys(totY).map(function (y) { return YIELDS[y] + '=' + totY[y]; }).join(' '));
}

function list() {
  const coll = F.defs();
  const b = coll.readPointer(), e = coll.add(8).readPointer();
  const n = e.sub(b).toInt32() / 8;
  const cul = F.cultureGet();
  log('--- ' + n + ' great work definitions; first candidates not yet created:');
  let shown = 0;
  for (let t = 0; t < n && shown < 10; t++) {
    const d = b.add(t * 8).readPointer();
    const obj = F.nameToObj(d.add(0x18).readS32());
    if (!F.has(cul, t)) { log('  T=' + t + ' object=' + (OBJ[obj] || obj)); shown++; }
  }
}

function exists(t) {
  const cul = F.cultureGet();
  const idx = idxOfType(t);
  log('--- work T=' + t + ': created (game-wide record) = ' + (F.has(cul, t) ? 'YES' : 'no') + '; list index ' + idx +
      (idx >= 0 ? '; record player field = ' + F.cultureGet().add(0x118).readPointer().add(idx * 0x18 + 4).readS32() : ''));
  let held = false;
  if (idx >= 0) for (let pid = 0; pid < 8; pid++) {
    let cs; try { cs = cities(pid); } catch (e) { continue; }
    cs.forEach(function (c) { if (F.isInCity(blds(c), idx)) { held = true; log('    held in a slot of city ' + cityId(c) + ' (player ' + pid + ')'); } });
  }
  if (idx >= 0 && !held) log('    not in any slot (limbo)');
}

function doRemove(job) {
  const idx = idxOfType(job.t);
  if (idx < 0) { log('[write] ' + job.op + ' T=' + job.t + ': no such record'); return; }
  const cs = cities(job.p);
  for (let i = 0; i < cs.length; i++) {
    if (F.isInCity(blds(cs[i]), idx)) {
      const b = job.op === 'remove' ? F.editVar(cs[i].add(0xca0)) : blds(cs[i]);   // 'removeraw' skips edit()
      const slot = F.removeGW(b, idx);
      log('[write] ' + job.op + ' T=' + job.t + ' (list index ' + idx + ') from city ' + cityId(cs[i]) + ': RemoveGreatWork returned slot ' + slot + (job.op === 'removeraw' ? ' (edit() SKIPPED)' : ' (via edit())'));
      return;
    }
  }
  log('[write] ' + job.op + ' T=' + job.t + ': not held by any city of player ' + job.p);
}

// ---- relics ----
const INVALID_PLOT = 0xffffd8f1;   // what the game itself passes for "no plot" (GetNearestRelicSlot then returns the first city with room)
function religionOf(pid) {
  const P = F.editPlayer(pid);
  const R = P.add(0x720).readPointer();
  const back = R.isNull() ? ptr(0) : R.add(0x90).readPointer();
  if (!back.equals(P)) throw new Error('Religion* sanity check failed: player+0x720 -> ' + R + ', its +0x90 = ' + back + ', player = ' + P);
  return R;
}
function plotBuf() { const m = Memory.alloc(8); m.writeU32(INVALID_PLOT); m.add(4).writeU32(INVALID_PLOT); return m; }
function relicBuildings() {
  const hash = F.makeHash(Memory.allocUtf8String('GREATWORKOBJECT_RELIC'));
  const coll = F.objDefs();
  const b = coll.readPointer(), e = coll.add(8).readPointer();
  const n = e.sub(b).toInt32() / 8;
  let def = null;
  for (let i = 0; i < n; i++) { const d = b.add(i * 8).readPointer(); if (d.add(0x18).readU32() === hash) { def = d; break; } }
  if (def === null) { log('  could not find the RELIC object type definition among ' + n + ' (hash ' + hash + ')'); return []; }
  const out = [];
  let q = def.add(0x40).readPointer(); const qe = def.add(0x48).readPointer();
  for (; !q.equals(qe); q = q.add(8)) { const x = q.readPointer(); if (!x.isNull()) out.push(x.add(0x14).readS32()); }
  return out;
}
function relicInfo(pid) {
  const R = religionOf(pid);
  const bl = relicBuildings();
  log('--- relic info player ' + pid + ': Religion* ' + R + '; relic-holding building types: [' + bl.join(', ') + ']');
  cities(pid).forEach(function (c) {
    const b = blds(c);
    bl.forEach(function (t) { if (F.hasBuilding(b, t)) log('  city ' + cityId(c) + ' has building ' + t + ', free relic slot index = ' + F.getFreeSlot(b, t) + ' (-1 = full)'); });
  });
  const ob = Memory.alloc(4), os = Memory.alloc(4);
  ob.writeS32(-1); os.writeS32(-1);
  const city = F.nearestRelic(R, plotBuf(), ob, os);
  log('  GetNearestRelicSlot -> ' + (city.isNull() ? 'NULL (no free relic slot: CreateRelic would do nothing)' : 'city ' + cityId(city) + ' building ' + ob.readS32() + ' slot ' + os.readS32()));
  log('  game-wide great work records: ' + recordCount());
}
function doRelicBase(job) {
  const R = religionOf(job.p);
  const ob = Memory.alloc(4), os = Memory.alloc(4); ob.writeS32(-1); os.writeS32(-1);
  const hadSlot = !F.nearestRelic(R, plotBuf(), ob, os).isNull();
  const before = recordCount();
  F.createRelic(R, plotBuf(), 0);
  const after = recordCount();
  log('[write] relicbase player=' + job.p + ': free relic slot existed=' + hadSlot + '; records ' + before + ' -> ' + after +
      (hadSlot ? ' (a slot existed, so a relic is EXPECTED: this is not the baseline case)' : (after === before ? ': unchanged, as predicted (nothing created)' : ': CHANGED, prediction wrong')));
}
function doRelicLimbo(job) {
  const cs = cities(job.p);
  if (cs.length === 0) { log('[write] reliclimbo: player ' + job.p + ' has no city'); return; }
  const bl = relicBuildings();
  if (job.b === null && bl.length === 0) { log('[write] reliclimbo: no relic building types found; give one explicitly: reliclimbo B=NN'); return; }
  let city = cs[0], B = job.b !== null ? job.b : bl[0];
  if (job.b === null) {
    outer: for (let i = 0; i < cs.length; i++) for (let j = 0; j < bl.length; j++) if (F.hasBuilding(blds(cs[i]), bl[j])) { city = cs[i]; B = bl[j]; break outer; }
  }
  const before = recordCount();
  const BADSLOT = 99;
  log('[write] reliclimbo: calling AddRelic(city ' + cityId(city) + ', building ' + B + ', slot ' + BADSLOT + '); the city has that building: ' + !!F.hasBuilding(blds(city), B));
  const t = F.addRelic(F.cultureGet(), city, B, BADSLOT, 0);
  const after = recordCount();
  const idx = t >= 0 ? idxOfType(t) : -1;
  let held = 'n/a';
  if (idx >= 0) {
    held = 'no';
    for (let pid = 0; pid < 8; pid++) { let cc; try { cc = cities(pid); } catch (e) { continue; } cc.forEach(function (c) { if (F.isInCity(blds(c), idx)) held = 'YES (city ' + cityId(c) + ')'; }); }
  }
  log('[write] reliclimbo: AddRelic returned great work type ' + t + '; records ' + before + ' -> ' + after + '; list index ' + idx + '; held in any slot: ' + held +
      (idx >= 0 ? '; record player field = ' + F.cultureGet().add(0x118).readPointer().add(idx * 0x18 + 4).readS32() : ''));
  log('  now type: report ' + job.p + ' (yields must not include the relic), and check the game for a notification and the Great Works screen.');
}

function doHut(job) {
  const cs = cities(job.p);
  if (cs.length === 0) { log('[write] hut: player ' + job.p + ' has no city'); return; }
  const bl = relicBuildings();
  let city = cs[0], B = bl.length ? bl[0] : 1;
  outer: for (let i = 0; i < cs.length; i++) for (let j = 0; j < bl.length; j++) if (F.hasBuilding(blds(cs[i]), bl[j])) { city = cs[i]; B = bl[j]; break outer; }
  const loc = F.getLoc(blds(city), B);
  const w = F.editMap().add(0x28).readS32();
  const plot = Memory.alloc(8);
  plot.writeS32(loc % w); plot.add(4).writeS32(Math.floor(loc / w));
  const R = religionOf(job.p);
  const ob = Memory.alloc(4), os = Memory.alloc(4); ob.writeS32(-1); os.writeS32(-1);
  const slotFree = !F.nearestRelic(R, plot, ob, os).isNull();
  const before = recordCount();
  F.createRelic(R, plot, 0);
  const after = recordCount();
  let what = 'nothing created';
  if (after > before) {
    const idx = after - 1;
    let held = null;
    for (let pid = 0; pid < 8 && held === null; pid++) { let cc; try { cc = cities(pid); } catch (e) { continue; } cc.forEach(function (c) { if (held === null && F.isInCity(blds(c), idx)) held = cityId(c); }); }
    what = held !== null ? 'relic (list index ' + idx + ') PLACED in a slot of city ' + held : 'relic (list index ' + idx + ') created, in NO slot = archived';
  }
  log('[write] hut player=' + job.p + ' plot=(' + (loc % w) + ',' + Math.floor(loc / w) + '): free relic slot before=' + slotFree + '; records ' + before + ' -> ' + after + ': ' + what);
}

// Great works held by building type B of a city (walks the slot vector: Buildings+0xc8 = data, +0xd8 = count; element 0x20 bytes:
// +0 building type, +8 slot array, +0x10 slot count; slot 8 bytes, work list index at +4, -1 = empty).
function worksOfBuilding(c, B) {
  const b = blds(c);
  const data = b.add(0xc8).readPointer(), n = b.add(0xd8).readU32();
  const out = [];
  for (let i = 0; i < n; i++) {
    const e = data.add(i * 0x20);
    if (e.readS32() !== B) continue;
    const slots = e.add(8).readPointer(), cnt = e.add(0x10).readU32();
    for (let k = 0; k < cnt; k++) { const w = slots.add(k * 8 + 4).readS32(); if (w !== -1) out.push(w); }
  }
  return out;
}
function doRmBuilding(job) {
  const cs = cities(job.p);
  for (let i = 0; i < cs.length; i++) {
    const c = cs[i];
    if (!F.hasBuilding(blds(c), job.b)) continue;
    const works = worksOfBuilding(c, job.b);
    const info = works.map(function (w) { const rec = F.cultureGet().add(0x118).readPointer().add(w * 0x18); return 'index ' + w + ' (type ' + rec.readU32() + ', record player ' + rec.add(4).readS32() + ')'; });
    log('[write] rmbuilding B=' + job.b + ' in city ' + cityId(c) + ': it holds ' + (works.length ? info.join('; ') : 'no works'));
    F.removeBuilding(F.editVar(c.add(0xca0)), job.b);
    log('[write] rmbuilding: RemoveBuilding returned; building still present: ' + !!F.hasBuilding(blds(c), job.b) + '; works in slots of this city now: ' + F.getNum(blds(c), -1));
    works.forEach(function (w) {
      let held = 'no slot (limbo)';
      for (let pid = 0; pid < 8; pid++) { let cc; try { cc = cities(pid); } catch (e) { continue; } cc.forEach(function (x) { if (F.isInCity(blds(x), w)) held = 'held by city ' + cityId(x) + ' (player ' + pid + ')'; }); }
      log('    work index ' + w + ': ' + held + '; record still exists: ' + (w < recordCount()));
    });
    return;
  }
  log('[write] rmbuilding: no city of player ' + job.p + ' has building ' + job.b);
}

function dumpRecords(onlyLimbo) {
  const cul = F.cultureGet();
  const n = recordCount();
  const base0 = cul.add(0x118).readPointer();
  const defs = F.defs(); const db = defs.readPointer(), dn = defs.add(8).readPointer().sub(db).toInt32() / 8;
  // who holds what: one pass over every player's cities
  const holder = {};
  const mgr = F.playerMgr();
  for (let pid = 0; pid < 64; pid++) {
    if (!F.isAlive(mgr, pid)) continue;
    let cs; try { cs = cities(pid); } catch (e) { continue; }
    cs.forEach(function (c) {
      for (let i = 0; i < n; i++) if (F.isInCity(blds(c), i)) holder[i] = 'city ' + cityId(c) + ' (player ' + pid + ')';
    });
  }
  let limbo = 0;
  log('--- ' + n + ' great work records');
  for (let i = 0; i < n; i++) {
    const rec = base0.add(i * 0x18);
    const t = rec.readU32(), pl = rec.add(4).readS32(), turn = rec.add(8).readS32();
    let obj = '?', nm = '';
    if (t < dn) {
      const d = db.add(t * 8).readPointer(); obj = OBJ[F.nameToObj(d.add(0x18).readS32())] || '?';
      try { const np = d.add(0x38).readPointer(); if (!np.isNull()) nm = ' ' + np.readUtf8String(); } catch (e) {}
    }
    const h = holder[i];
    if (!h) limbo++;
    if (onlyLimbo && h) continue;
    log('  [' + i + '] type ' + t + ' ' + obj + nm + ' | player field ' + pl + ' | turn ' + turn + ' | ' + (h ? 'held by ' + h : '*** LIMBO (in no slot)'));
  }
  log('--- ' + limbo + ' of ' + n + ' records are in no slot');
}

function defName(t) {
  try {
    const defs = F.defs(); const db = defs.readPointer(), dn = defs.add(8).readPointer().sub(db).toInt32() / 8;
    if (t >= dn) return '';
    const np = db.add(t * 8).readPointer().add(0x38).readPointer();
    return np.isNull() ? '' : np.readUtf8String();
  } catch (e) { return ''; }
}
function findWork(text) {
  const n = recordCount(), base0 = F.cultureGet().add(0x118).readPointer();
  const q = text.toLowerCase(); let hits = 0;
  for (let i = 0; i < n; i++) {
    const t = base0.add(i * 0x18).readU32(), nm = defName(t);
    if (nm.toLowerCase().indexOf(q) >= 0) { hits++; log('  record [' + i + '] type ' + t + ' ' + nm + ' | player field ' + base0.add(i * 0x18 + 4).readS32() + ' | turn ' + base0.add(i * 0x18 + 8).readS32()); }
  }
  log('--- ' + hits + ' record(s) match "' + text + '"');
}
function holders(idx) {
  const n = recordCount();
  if (idx < 0 || idx >= n) { log('no such record index ' + idx + ' (records: ' + n + ')'); return; }
  const rec = F.cultureGet().add(0x118).readPointer().add(idx * 0x18);
  log('--- record [' + idx + '] type ' + rec.readU32() + ' ' + defName(rec.readU32()) + ' | player field ' + rec.add(4).readS32() + ' | turn ' + rec.add(8).readS32());
  const mgr = F.playerMgr(); let found = 0;
  for (let pid = 0; pid < 64; pid++) {
    if (!F.isAlive(mgr, pid)) continue;
    let cs; try { cs = cities(pid); } catch (e) { continue; }
    cs.forEach(function (c) {
      const b = blds(c);
      const viaGame = !!F.isInCity(b, idx);
      const data = b.add(0xc8).readPointer(), cnt = b.add(0xd8).readU32();
      const raw = [];
      for (let k = 0; k < cnt && k < 200; k++) {
        const e = data.add(k * 0x20), btype = e.readS32(), slots = e.add(8).readPointer(), sc = e.add(0x10).readU32();
        for (let j = 0; j < sc && j < 100; j++) {
          const w0 = slots.add(j * 8).readS32(), w1 = slots.add(j * 8 + 4).readS32();
          if (w1 === idx) raw.push('building type ' + btype + ' slot ' + j + ' (word0=' + w0 + '), city currently HAS that building: ' + !!F.hasBuilding(b, btype));
        }
      }
      if (viaGame || raw.length) { found++; log('  player ' + pid + ' city ' + cityId(c) + ' "' + cityName(c) + '": IsInCity=' + viaGame + '; raw slot scan: ' + (raw.length ? raw.join('; ') : 'not found') + '; city is capital: ' + (c.add(0x280).readU8() !== 0)); }
    });
  }
  log('--- ' + found + ' city(ies) reference this record' + (found === 0 ? ' => it is in no slot by both checks (true limbo)' : ''));
}

function palaces(pid) {
  log('--- palaces of player ' + pid + ' (building type 1; flag 0x280 = capital)');
  cities(pid).forEach(function (c) {
    const has = !!F.hasBuilding(blds(c), 1), cap = c.add(0x280).readU8() !== 0, w = worksOfBuilding(c, 1);
    if (has || cap || w.length) log('  city ' + cityId(c) + ' "' + cityName(c) + '": capital=' + cap + ' has Palace=' + has + ' works in Palace slots=[' + w.join(', ') + ']');
  });
}
function ghostEntries(c) {
  const b = blds(c), data = b.add(0xc8).readPointer(), cnt = b.add(0xd8).readU32(), out = [];
  for (let k = 0; k < cnt && k < 200; k++) {
    const e = data.add(k * 0x20), btype = e.readS32();
    if (F.hasBuilding(b, btype)) continue;
    const slots = e.add(8).readPointer(), sc = e.add(0x10).readU32(), works = [];
    for (let j = 0; j < sc && j < 100; j++) { const w = slots.add(j * 8 + 4).readS32(); if (w !== -1) works.push(w); }
    out.push({ btype: btype, slotCount: sc, works: works });
  }
  return out;
}
function ghostWorks(c) {
  const b = blds(c), data = b.add(0xc8).readPointer(), cnt = b.add(0xd8).readU32(), out = [];
  for (let k = 0; k < cnt && k < 200; k++) {
    const e = data.add(k * 0x20), btype = e.readS32();
    if (F.hasBuilding(b, btype)) continue;
    const slots = e.add(8).readPointer(), sc = e.add(0x10).readU32();
    for (let j = 0; j < sc && j < 100; j++) { const w = slots.add(j * 8 + 4).readS32(); if (w !== -1) out.push({ btype: btype, slot: j, work: w }); }
  }
  return out;
}
function doUnghost(job) {
  const mgr = F.playerMgr(); let total = 0, entries = 0; const pending = [];
  for (let pid = 0; pid < 64; pid++) {
    if (job.p !== null && pid !== job.p) continue;
    if (!F.isAlive(mgr, pid)) continue;
    let cs; try { cs = cities(pid); } catch (e) { continue; }
    cs.forEach(function (c) {
      ghostEntries(c).forEach(function (g) {
        entries++;
        const v = F.editVar(c.add(0xca0));
        // 1. take every work out of the dead entry, 2. drop the entry itself, 3. only then re-place the works (otherwise the freed ghost slot could take them again)
        g.works.forEach(function (w) {
          const slot = F.removeGW(v, w);
          log('[write] unghost: player ' + pid + ' city ' + cityId(c) + ' "' + cityName(c) + '": removed work ' + w + ' from the dead ' + buildingName(g.btype) + ' entry (RemoveGreatWork returned slot ' + slot + ')');
          pending.push({ pid: pid, work: w });
        });
        F.removeSlots(v, g.btype);
        log('[write] unghost: dropped the dead entry for building type ' + g.btype + ' ' + buildingName(g.btype) + ' (' + g.slotCount + ' slot(s)) from city ' + cityId(c));
      });
    });
  }
  pending.forEach(function (x) {
    total++;
    const pc = F.editPlayer(x.pid).add(0x6f0).readPointer();
    const ok = F.receive(pc, x.work);
    log('[write] unghost: work ' + x.work + ' ' + defName(F.cultureGet().add(0x118).readPointer().add(x.work * 0x18).readU32()) + ' -> ReceiveGreatWork for player ' + x.pid + ': ' + (ok ? 'PLACED in a real slot' : 'no room, left in limbo'));
  });
  log('[write] unghost: ' + entries + ' dead entr(ies) dropped, ' + total + ' work(s) re-placed');
}
function ghosts() {
  const mgr = F.playerMgr(); let total = 0, emptyGhosts = 0;
  for (let pid = 0; pid < 64; pid++) {
    if (!F.isAlive(mgr, pid)) continue;
    let cs; try { cs = cities(pid); } catch (e) { continue; }
    let slotted = 0;
    cs.forEach(function (c) {
      slotted += F.getNum(blds(c), -1);   // works counted by the per-city getter
      ghostEntries(c).forEach(function (g) {
        if (g.works.length === 0) {
          emptyGhosts++;
          log('  EMPTY GHOST SLOT ENTRY: player ' + pid + ' city ' + cityId(c) + ' "' + cityName(c) + '": building type ' + g.btype + ' ' + buildingName(g.btype) + ', ' + g.slotCount + ' slot(s), all empty: a work placed by ReceiveGreatWork/AddGreatWork can land there and become invisible');
        }
        g.works.forEach(function (w) {
          total++;
          log('  GHOST: player ' + pid + ' city ' + cityId(c) + ' "' + cityName(c) + '": work ' + w + ' ' + defName(F.cultureGet().add(0x118).readPointer().add(w * 0x18).readU32()) + ' in building type ' + g.btype + ' ' + buildingName(g.btype));
        });
      });
    });
    log('  player ' + pid + ': ' + cs.length + ' cities, ' + slotted + ' works counted by GetNumGreatWorks');
  }
  log('--- ' + total + ' ghost work(s) and ' + emptyGhosts + ' empty ghost slot entr(ies) in total');
}

function buildingName(t) {
  try {
    const coll = F.bldDefs(), b = coll.readPointer(), n = coll.add(8).readPointer().sub(b).toInt32() / 8;
    if (t < 0 || t >= n) return '?';
    const np = b.add(t * 8).readPointer().add(0x68).readPointer();
    return np.isNull() ? '?' : np.readUtf8String();
  } catch (e) { return '?'; }
}

function dumpSlots(query) {
  const mgr = F.playerMgr(); const q = String(query).toLowerCase(); const isNum = /^[0-9]+$/.test(q); let hits = 0;
  const w = F.editMap().add(0x28).readS32();
  for (let pid = 0; pid < 64; pid++) {
    if (!F.isAlive(mgr, pid)) continue;
    let cs; try { cs = cities(pid); } catch (e) { continue; }
    cs.forEach(function (c) {
      const nm = cityName(c);
      if (!(isNum ? cityId(c) === parseInt(q) : nm.toLowerCase().indexOf(q) >= 0)) return;
      hits++;
      const b = blds(c), data = b.add(0xc8).readPointer(), cnt = b.add(0xd8).readU32();
      log('=== player ' + pid + ' city ' + cityId(c) + ' "' + nm + '": ' + cnt + ' building entries in the slot list; works counted: ' + F.getNum(b, -1));
      for (let k = 0; k < cnt && k < 200; k++) {
        const e = data.add(k * 0x20), bt = e.readS32(), slots = e.add(8).readPointer(), sc = e.add(0x10).readU32();
        const has = !!F.hasBuilding(b, bt), loc = F.getLoc(b, bt), game = F.numSlots(b, bt);
        const where = loc >= 0 ? '(' + (loc % w) + ',' + Math.floor(loc / w) + ')' : 'no location';
        const odd = [];
        if (!has) odd.push('city does NOT have this building');
        if (sc !== game) odd.push('slot count ' + sc + ' in list vs GetNumGreatWorkSlots ' + game);
        log('  entry ' + k + ': building ' + bt + ' ' + buildingName(bt) + ' | has=' + has + ' | at ' + where + ' | ' + sc + ' slot(s)' + (odd.length ? '  << ' + odd.join('; ') : ''));
        for (let j = 0; j < sc && j < 100; j++) {
          const w0 = slots.add(j * 8).readS32(), wk = slots.add(j * 8 + 4).readS32();
          let st = '?'; try { st = F.slotType(b, bt, j); } catch (x) {}
          let wn = '';
          if (wk >= 0 && wk < recordCount()) { const t = F.cultureGet().add(0x118).readPointer().add(wk * 0x18).readU32(); wn = ' ' + defName(t) + ' (type ' + t + ')'; }
          log('      slot ' + j + ': word0=' + w0 + ' slotType=' + st + ' work=' + wk + wn);
        }
      }
    });
  }
  if (hits === 0) log('no city matches "' + query + '" (use the numeric id from report, or part of the name key such as ROME)');
}

// ---- ownership storage tests ----
function recBase() { return F.cultureGet().add(0x118).readPointer(); }
function doTag(job) {
  const n = recordCount();
  if (job.idx < 0 || job.idx >= n) { log('[write] tag: no record ' + job.idx + ' (records: ' + n + ')'); return; }
  if (job.edit) F.editVar(F.cultureGet().add(0x108));   // the tracked accessor for the record list; its return value is not needed, the call marks the list changed
  const rec = recBase().add(job.idx * 0x18);
  const before = rec.add(0xc).readU32();
  rec.add(0xc).writeU32(job.value);
  log('[write] tag: record ' + job.idx + ' (+0x0C) ' + before + ' -> ' + rec.add(0xc).readU32() + (job.edit ? ' (after edit() on the record list)' : ' (plain write, no edit())') + '. Now save, reload, run: tags');
}
function dumpTags() {
  const n = recordCount(), base0 = recBase(); let nz = 0;
  log('--- ' + n + ' records; non-zero values at +0x0C:');
  for (let i = 0; i < n; i++) { const v = base0.add(i * 0x18 + 0xc).readU32(); if (v !== 0) { nz++; log('  record [' + i + '] +0x0C = ' + v + ' (0x' + v.toString(16) + ')'); } }
  if (nz === 0) log('  none (all records have 0 there)');
  for (let i = 0; i < Math.min(n, 4); i++) log('  for comparison, record [' + i + '] raw bytes: ' + hexdump(base0.add(i * 0x18), { length: 0x18, header: false, ansi: false }).split('\n')[0]);
}
function gameProps() {
  const game = base.add(RVA.currentGame).readPointer();
  return F.editVar(game.add(0x1a8));      // FAutoVariable<VariantMap,Game::Instance> at Game+0x1a8, same call lSetProperty makes
}
function doPropSet(job) {
  const map = gameProps();
  const mgrFn = new NativeFunction(map.readPointer().add(0x28).readPointer(), 'pointer', ['pointer']);   // container virtual +0x28 = its VariantManager (as in Utility::SetProperty)
  const mgr = mgrFn(map);
  const key = F.registerKey(mgr, Memory.allocUtf8String(job.name));
  const v = Memory.alloc(8); v.writeU32(job.value >>> 0);
  const res = F.setVariant(map, key, v);
  log('[write] propset: Game property "' + job.name + '" key 0x' + key.toString(16) + ' <- ' + job.value + ' (VariantMap ' + map + ', manager ' + mgr + ', SetVariant returned ' + res + '). Lua should now read it; save+reload to test persistence.');
}

function doMakeGhost(job) {
  const cs = cities(job.p);
  for (let i = 0; i < cs.length; i++) {
    const c = cs[i], b = blds(c);
    if (!F.hasBuilding(b, job.b)) continue;
    const works = worksOfBuilding(c, job.b);
    F.setBldLoc(F.editVar(c.add(0xca0)), job.b, -1);
    const stillThere = ghostEntries(c).filter(function (g) { return g.btype === job.b; }).length;
    log('[write] makeghost: city ' + cityId(c) + ' "' + cityName(c) + '": building ' + job.b + ' ' + buildingName(job.b) + ' now HasBuilding=' + !!F.hasBuilding(b, job.b) + '; its slot entry is still in the slot list: ' + (stillThere > 0) + '; works inside: [' + works.join(', ') + ']');
    return;
  }
  log('[write] makeghost: no city of player ' + job.p + ' has building ' + job.b);
}
function doWrite(job) {
  if (job.op === 'tag') { doTag(job); return; }
  if (job.op === 'propset') { doPropSet(job); return; }
  if (job.op === 'rmbuilding') { doRmBuilding(job); return; }
  if (job.op === 'hut') { doHut(job); return; }
  if (job.op === 'unghost') { doUnghost(job); return; }
  if (job.op === 'makeghost') { doMakeGhost(job); return; }
  if (job.op === 'relicbase') { doRelicBase(job); return; }
  if (job.op === 'reliclimbo') { doRelicLimbo(job); return; }
  if (job.op === 'remove' || job.op === 'removeraw') { doRemove(job); return; }
  const cul = F.cultureGet();
  const idx = F.findOrAdd(cul, job.t);
  if (job.op !== 'place') F.setPlayer(cul, idx, job.p);
  let placed = 'not attempted';
  if (job.op !== 'limbo') {
    const pc = F.editPlayer(job.p).add(0x6f0).readPointer();
    placed = F.receive(pc, idx) ? 'PLACED in a slot' : 'NO ROOM: left in limbo';
  }
  log('[write] ' + job.op + ' T=' + job.t + ' player=' + job.p + ' -> list index ' + idx + ', ' + placed + '; records now ' + recordCount());
}

function num(x) { const n = parseInt(String(x).replace(/^T/i, '')); if (isNaN(n)) throw new Error('not a number: ' + x); return n; }

function parse(line) {
  const a = line.trim().split(/\s+/); const c = a[0];
  try {
    if (c === 'list') list();
    else if (c === 'report') report(a.length > 1 ? parseInt(a[1]) : 0);
    else if (c === 'exists') exists(num(a[1]));
    else if (c === 'unghost') { queue.push({ op: c, p: a.length > 1 ? num(a[1]) : null }); log('running: unghost -> runs now on the game thread'); }
    else if (c === 'makeghost') { queue.push({ op: c, b: num(a[1]), p: a.length > 2 ? num(a[2]) : 0 }); log('running: makeghost building ' + num(a[1]) + ' -> runs now on the game thread'); }
    else if (c === 'ghosts') ghosts();
    else if (c === 'slots') dumpSlots(a.slice(1).join(' '));
    else if (c === 'tag') { const e = a[3] === 'edit'; queue.push({ op: 'tag', idx: num(a[1]), value: num(a[2]), edit: e }); log('running: tag record ' + num(a[1]) + ' = ' + num(a[2]) + (e ? ' with edit()' : ' without edit()') + ' -> runs now on the game thread'); }
    else if (c === 'tags') dumpTags();
    else if (c === 'propset') { queue.push({ op: 'propset', name: a[1], value: num(a[2]) }); log('running: propset ' + a[1] + ' = ' + num(a[2]) + ' -> runs now on the game thread'); }
    else if (c === 'palaces') palaces(a.length > 1 ? parseInt(a[1]) : 0);
    else if (c === 'holders') holders(parseInt(a[1]));
    else if (c === 'findwork') findWork(a.slice(1).join(' '));
    else if (c === 'records') dumpRecords(a[1] === 'limbo' || a[1] === 'onlylimbo');
    else if (c === 'rmbuilding') {
      queue.push({ op: c, b: num(a[1]), p: a.length > 2 ? num(a[2]) : 0 });
      log('running: rmbuilding ' + num(a[1]) + ' -> runs now on the game thread');
    }
    else if (c === 'hut') {
      let n = 1, p = 0;
      a.slice(1).forEach(function (x) { if (/^x/i.test(x)) n = parseInt(x.slice(1)); else p = num(x); });
      for (let i = 0; i < n; i++) queue.push({ op: 'hut', p: p });
      log('running: ' + n + ' x hut for player ' + p + ' -> runs now on the game thread');
    }
    else if (c === 'relicinfo') relicInfo(a.length > 1 ? parseInt(a[1]) : 0);
    else if (c === 'relicbase') { queue.push({ op: c, p: a.length > 1 ? num(a[1]) : 0 }); log('running: relicbase -> runs now on the game thread'); }
    else if (c === 'reliclimbo') {
      let b = null, p = 0;
      a.slice(1).forEach(function (x) { if (/^B=/i.test(x)) b = num(x.slice(2)); else p = num(x); });
      queue.push({ op: c, b: b, p: p });
      log('running: reliclimbo building=' + b + ' player=' + p + ' -> runs now on the game thread');
    }
    else if (c === 'spawn' || c === 'limbo' || c === 'place' || c === 'remove' || c === 'removeraw') {
      queue.push({ op: c, t: num(a[1]), p: a.length > 2 ? num(a[2]) : 0 });
      log('running: ' + c + ' T=' + num(a[1]) + ' -> runs now on the game thread');
    } else log('unknown command: ' + line);
  } catch (e) { log('command failed: ' + e); }
}

// ---- adapter to the live framework -------------------------------------------------------------------------------------
// Reads run immediately on the Frida thread; writes (everything that fills `queue`) run on the game thread via onGame().
setup({ base: G.base() || ptr(0) });
onRebase(function (b) { setup({ base: b }); }, 'gw_limbo');
const READS = ['list', 'report', 'exists', 'ghosts', 'slots', 'tags', 'palaces', 'holders', 'findwork', 'records', 'relicinfo'];
const WRITES = ['unghost', 'makeghost', 'tag', 'propset', 'rmbuilding', 'hut', 'relicbase', 'reliclimbo', 'spawn', 'limbo', 'place', 'remove', 'removeraw'];
function needGame() { if (!G.base()) throw new Error('GameCore is not loaded (start or load a game)'); }
function drain() { while (queue.length) { const job = queue.shift(); try { doWrite(job); } catch (e) { log('write failed: ' + e); } } }
READS.forEach(function (c) {
  defcmd(c, 'great-works experiment (read-only), see gw_limbo header', function (a) { needGame(); parse(c + ' ' + a.join(' ')); return ''; });
});
WRITES.forEach(function (c) {
  defcmd(c, 'great-works experiment (WRITE), see gw_limbo header', function (a) { needGame(); parse(c + ' ' + a.join(' ')); drain(); return ''; }, { game: true });
});
})();
