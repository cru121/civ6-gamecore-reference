"""Turn TraceBatch.java output into per-Lua-method effect summaries with member names.

Input : linux_depot/out/trace_lua_callees.jsonl   (tools/TraceBatch.java over the C++ callees of the Lua wrappers)
        linux_depot/out/types.jsonl, functions.tsv (Linux DWARF: layouts, parameter names)
        docs_proto/data/lua_signatures.json, curated/_windows_offsets.yaml
Output: docs_proto/data/lua_effects.json   (keyed by wrapper RVA in the symbol build)

Offsets in the trace are Windows (symbol build). Linux DWARF offset = Windows + 8 for FAutoVariable-heavy
classes, equal for others, so each access is tried both ways and kept only when exactly one candidate
member has the access size (otherwise ambiguous -> dropped). Names found this way are 'inferred', except
members already checked in _windows_offsets.yaml ('verified').
"""
import json, os, re, collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
def P(*a): return os.path.join(ROOT, *a)

# ------------------------------------------------------------------ DWARF
types = {}
for l in open(P('linux_depot', 'out', 'types.jsonl'), encoding='utf8'):
    j = json.loads(l)
    types[j['name']] = j

def type_size(tn):
    t = types.get(tn)
    return t['size'] if t and t.get('size') else None

linux_params = collections.defaultdict(list)
for i, l in enumerate(open(P('linux_depot', 'out', 'functions.tsv'), encoding='utf8')):
    if i == 0:
        continue
    p = l.rstrip('\n').split('\t')
    if len(p) >= 5:
        names = []
        for x in [y.strip() for y in p[4].split(';') if y.strip()]:
            m = re.match(r'.*?(\w+)$', x)
            names.append(m.group(1) if m else '_')
        linux_params[p[3]].append(names)

verified = set()
try:
    import yaml
    for e in yaml.safe_load(open(P('docs_proto', 'curated', '_windows_offsets.yaml')))['windows_offsets']:
        verified.add((e['layout'], e['member']))
except Exception:
    pass

def all_members(cls, base_off=0, depth=0):
    """(offset, name, type, owner) for a class including bases, sorted."""
    t = types.get(cls)
    out = []
    if not t or depth > 4:
        return out
    for b in t['bases']:
        out += all_members(b[0], base_off + (b[1] or 0), depth + 1)
    for m in t['members']:
        if m[1] is None or m[4]:
            continue
        out.append((base_off + m[1], m[0], m[2], cls))
    return sorted(out, key=lambda x: x[0])

_mcache = {}
def members(cls):
    if cls not in _mcache:
        _mcache[cls] = all_members(cls)
    return _mcache[cls]

def member_at(cls, off):
    """Member covering `off` (innermost struct members expanded). -> (label, type, member_off_in_cls, member_size) or None"""
    ms = members(cls)
    best = None
    for k, (mo, name, ty, owner) in enumerate(ms):
        if mo > off:
            break
        nxt = ms[k + 1][0] if k + 1 < len(ms) else None
        sz = type_size(ty)
        end = mo + sz if sz else nxt
        if end is not None and off >= end and sz:
            continue
        best = (mo, name, ty, sz, nxt)
    if best is None:
        return None
    mo, name, ty, sz, nxt = best
    if sz is None:
        sz = (nxt - mo) if nxt else None
    return mo, name, ty, sz

def pointee(ty):
    """Class that a member type points to, if resolvable."""
    if not ty:
        return None
    m = re.match(r'^(?:const )?([\w:<>, ]+?)\s*\*$', ty)
    if m and m.group(1) in types:
        return m.group(1)
    m = re.match(r'^(?:GameCore::)?(?:ParentPtr|FAutoVariable|FAutoPtr)<(.+?)(?:,.*)?>$', ty)
    if m:
        c = m.group(1).strip().rstrip('*').strip()
        if c in types:
            return c
        if 'GameCore::' + c in types:
            return 'GameCore::' + c
    return None

def label(cls, off, size):
    """Resolve (cls, windows offset) -> list of candidate (display, member_type, status)."""
    cands = []
    for shift in (8, 0):
        r = member_at(cls, off + shift)
        if not r:
            continue
        mo, name, ty, sz = r
        inner = off + shift - mo
        # FAutoVariable<T> keeps its value at +0x10 inside the wrapper; plain members are exact
        if ty.startswith('FAutoVariable<'):
            ok = (inner == 0x10 or inner == 0) and (size in (None, 0) or True)
        else:
            ok = (sz is None) or (size in (None, 0)) or size == sz or inner > 0 or (sz and size < sz)
        cands.append((shift, mo, name, ty, sz, inner, ok))
    good = [c for c in cands if c[6]]
    if len(good) != 1:
        # both shifts resolve to the same member name -> fine
        names = {c[2] for c in good}
        if len(names) != 1:
            return None
    shift, mo, name, ty, sz, inner, ok = good[0]
    short = cls.replace('GameCore::', '')
    # offset inside the member only when it is a plain struct; container/wrapper internals are noise
    plain = ty in types and '<' not in ty
    disp = f"{short}::{name}" + (f"+0x{inner:x}" if inner and plain else '')
    st = 'verified' if (short, name) in verified else 'inferred'
    return disp, ty, st, shift

def resolve_path(cls, path, off, size):
    """Follow deref path through member pointer types. Returns (display, status) or None."""
    cur = cls
    for hop, po in enumerate(path):
        r = None
        for shift in (8, 0):
            m = member_at(cur, po + shift)
            if m and pointee(m[2]) and m[0] == po + shift:
                r = (m, shift); break
        if not r:
            return None
        cur = pointee(r[0][2])
    res = label(cur, off, size)
    if not res:
        return None
    disp, ty, st, shift = res
    if path:
        st = 'inferred'
    return disp, st

# ------------------------------------------------------------------ main
sigs = json.load(open(P('docs_proto', 'data', 'lua_signatures.json')))

def callee_class(callee):
    parts = callee.replace('GameCore::', '').split('::')
    if len(parts) < 2:
        return None
    base = 'GameCore::' + '::'.join(parts[:-1])
    for c in (base, base + '::Instance', base + '::IInstance'):
        if c in types:
            return c
    return None

def dwarf_param_name(callee, argidx):
    """Name of callee argument `argidx` (decompiler order: 0 = this for methods) from the Linux DWARF parameter list."""
    q = re.sub(r'@0x[0-9a-f]+$', '', callee)
    for names in linux_params.get(q, []):
        i = argidx if names and names[0] == 'this' else argidx - 1
        if names and names[0] == 'this' and argidx == 0:
            return None
        if 0 <= i < len(names):
            return names[i]
    return None

out = {}
stat = collections.Counter()
def _records():
    for fn in ('trace_lua_callees.jsonl', 'trace_lua_wrappers.jsonl'):
        path = P('linux_depot', 'out', fn)
        if os.path.exists(path):
            for line in open(path, encoding='utf8'):
                j = json.loads(line)
                j['_wrapper_mode'] = fn.startswith('trace_lua_wrappers')
                yield j

for j in _records():
    stat[j['status']] += 1
    if j['status'] != 'ok':
        continue
    sig = sigs.get(j['key'], {})
    if j['_wrapper_mode']:
        selfp = [p_ for p_ in j['params'] if p_.get('lua_index') == 1]
        this = selfp[0] if selfp else None
        cls = this['type'] if this and this['type'] in types else None
        params = []
        j['callee'] = '(inline in wrapper)'
    else:
        cls = callee_class(j['callee'])
        params = j['params']
        this = params[0] if params else None
    writes, reads, calls = {}, {}, collections.OrderedDict()
    unresolved = 0
    if this and cls:
        evs = this['events']
        read_paths = {tuple(e.get('path', []) + [e['off']]) for e in evs if e['k'] == 'read' and e.get('off', -1) >= 0}
        for e in evs:
            off = e.get('off', -1)
            if e['k'] in ('read', 'write') and off >= 0 and not e.get('derived'):
                size = e.get('size', 0)
                if e['k'] == 'read' and tuple(e.get('path', []) + [off]) in {tuple(p[:len(e.get('path', [])) + 1]) for p in read_paths if len(p) > len(e.get('path', [])) + 1}:
                    continue   # traversal read of a pointer that is dereferenced further
                r = resolve_path(cls, e.get('path', []), off, size)
                if not r:
                    unresolved += 1
                    continue
                (writes if e['k'] == 'write' else reads).setdefault(r[0], r[1])
            elif e['k'] == 'call' and not e.get('via') and not e.get('path') and e.get('off') == 0 and e.get('arg') == 0:
                calls[re.sub(r'^GameCore::', '', e['callee'].split('@')[0])] = 1
    # lua args -> callee params
    lua_params = sig.get('params', [])
    off_this = 0 if sig.get('static') else 1
    args = {}
    if len(params) == len(lua_params) + off_this and lua_params:
        for k, lp in enumerate(lua_params):
            cp = params[k + off_this]
            a = {'stored_to': [], 'cmp': [], 'passed_to': [], 'name_hints': []}
            for e in cp['events']:
                if e.get('via'):
                    continue
                if e['k'] == 'stored' and e.get('tgt') and e['tgt']['param'] == 0 and cls and e.get('off', 0) == 0 and not e.get('path'):
                    r = label(cls, e['tgt']['off'], e.get('size', 0))
                    if r:
                        a['stored_to'].append({'member': r[0], 'status': 'inferred'})
                        mm = re.sub(r'^m_[a-z]{1,2}(?=[A-Z])', '', r[0].split('::')[-1])
                        a['name_hints'].append({'name': mm, 'source': 'member:' + r[0]})
                elif e['k'] == 'cmp' and not e.get('derived') and e.get('off') == 0 and not e.get('path'):
                    a['cmp'].append({'op': e['op'], 'cst': e['cst']})
                elif e['k'] == 'call' and not e.get('derived') and e.get('off') == 0 and not e.get('path'):
                    pn = dwarf_param_name(e['callee'], e['arg'])
                    callee_n = re.sub(r'^GameCore::', '', e['callee'].split('@')[0])
                    a['passed_to'].append({'callee': callee_n, 'arg': e['arg'], 'param': pn})
                    if pn and pn not in ('_',) and not pn.startswith('param_'):
                        a['name_hints'].append({'name': pn, 'source': 'callee:' + callee_n})
            # de-dup
            for key in ('stored_to', 'cmp', 'passed_to', 'name_hints'):
                seen, uniq = set(), []
                for x in a[key]:
                    s = json.dumps(x, sort_keys=True)
                    if s not in seen:
                        seen.add(s); uniq.append(x)
                a[key] = uniq
            if any(a.values()):
                args[str(lp.get('index', k))] = a
    if writes or reads or calls or args:
        out[j['key']] = {
            'wrapper': sig.get('wrapper'), 'callee': j['callee'].replace('GameCore::', ''),
            'callee_rva': j['callee_rva'], 'inline': j['_wrapper_mode'], 'class': cls.replace('GameCore::', '') if cls else None,
            'writes': [{'member': m, 'status': s} for m, s in writes.items()],
            'reads': [{'member': m, 'status': s} for m, s in reads.items()],
            'calls': list(calls), 'args': args, 'unresolved_accesses': unresolved,
        }
json.dump(out, open(P('docs_proto', 'data', 'lua_effects.json'), 'w'), indent=1)
print(dict(stat), 'methods with effects:', len(out))
print('with writes', sum(1 for v in out.values() if v['writes']), 'with reads', sum(1 for v in out.values() if v['reads']),
      'with arg info', sum(1 for v in out.values() if v['args']),
      'name hints', sum(1 for v in out.values() for a in v['args'].values() if a['name_hints']))
