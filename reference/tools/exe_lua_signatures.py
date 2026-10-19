"""Recover Lua signatures of the exe-side wrappers (UI, Network, Modding, Locale, ... tables) from decompiled code.
Input : linux_depot/out/exe_lua_wrappers_decomp.txt   (tools/DecompList.java run on ghi-exe, wrapper RVAs in exe_wrapper_rvas.txt)
Output: data/exe_lua_signatures.json  keyed by wrapper RVA (hex, no prefix):
        {params: [{slot, lua_type, optional, cpp_hint}], nret, returns: [types], arg_counts, unparsed_helpers, callees}
Slots are Lua stack positions (1 = first value). For tables called with `:` slot 1 is the object itself.
All results are inferred from the decompiled stack accesses, never from names (the exe has no parameter names)."""
import json, os, re, collections

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
text = open(os.path.join(ROOT, 'linux_depot', 'out', 'exe_lua_wrappers_decomp.txt'), encoding='utf8', errors='replace').read()
blocks = text.split('\n@@@ ')
blocks[0] = blocks[0][4:] if blocks[0].startswith('@@@ ') else blocks[0]

BASE_RE = re.compile(r'param_1 \+ 0x50\)(?:\s*\+\s*(0x[0-9a-f]+))?')
TAGS = {1: 'boolean', 3: 'number', 4: 'string', 5: 'table', 6: 'function'}
CALL_RE = re.compile(r'\b((?:hks|hksi|lua|luaL)_\w+|FUN_[0-9a-f]+|thunk_FUN_[0-9a-f]+|[A-Za-z_][\w:]*)\s*\(')


def balanced(src, start):
    depth = 0
    for j in range(start, len(src)):
        if src[j] == '(':
            depth += 1
        elif src[j] == ')':
            depth -= 1
            if depth == 0:
                return src[start + 1:j]
    return src[start + 1:]


def parse(block):
    head, _, body = block.partition('\n')
    rva = head.split('\t')[0].replace('0x', '')
    m = re.search(r'\n\{\n(.*)\n\}', body, re.S)
    code = m.group(1) if m else body
    params = {}
    notes = []

    def setp(slot, lt, optional, hint=None):
        cur = params.get(slot)
        rec = {'slot': slot, 'lua_type': lt, 'optional': optional}
        if hint:
            rec['cpp_hint'] = hint
        if cur is None:
            params[slot] = rec
        else:
            if cur['lua_type'] != lt and lt != 'any':
                if cur['lua_type'] == 'any':
                    cur['lua_type'] = lt
                elif {cur['lua_type'], lt} == {'number', 'string'}:
                    cur['lua_type'] = 'number|string'
                elif {cur['lua_type'], lt} == {'integer', 'number'}:
                    cur['lua_type'] = 'integer'
            cur['optional'] = cur['optional'] and optional
            if hint and 'cpp_hint' not in cur:
                cur['cpp_hint'] = hint

    top_guard = 'param_1 + 0x48' in code
    # integer-ness: `iVar = (int)dVar;` where dVar = hks_obj_tonumber(...)
    for im in re.finditer(r'(hks_obj_tonumber|hks_obj_tolstring|hks_obj_isnumber|hks_obj_toboolean)\s*\(', code):
        fn = im.group(1)
        expr = balanced(code, im.end() - 1)
        bm = BASE_RE.search(expr)
        if not bm:
            continue
        slot = (int(bm.group(1), 16) // 16 if bm.group(1) else 0) + 1
        lt = {'hks_obj_tonumber': 'number', 'hks_obj_tolstring': 'string', 'hks_obj_isnumber': 'number', 'hks_obj_toboolean': 'boolean'}[fn]
        hint = None
        if fn == 'hks_obj_tonumber':
            am = re.search(r'(\w+)\s*=\s*$', code[max(0, im.start() - 40):im.start()])
            if am:
                v = am.group(1)
                if re.search(r'\((?:int|uint|longlong|ulonglong|short|ushort|char|byte)\)\s*%s\b' % re.escape(v), code):
                    lt = 'integer'
                elif re.search(r'\(float\)\s*%s\b' % re.escape(v), code):
                    hint = 'float'
        setp(slot, lt, top_guard, hint)
    # raw pointers into the stack, tested for their type tag
    rawvars = {}
    for rm in re.finditer(r'(\w+)\s*=\s*(?:\(\w[\w\s\*]*\)\s*)?\(?\*\(\w[\w\s]*\*\*?\)\(param_1 \+ 0x50\)(?:\s*\+\s*(0x[0-9a-f]+))?\)?\s*;|'
                          r'(\w+)\s*=\s*\(\w[\w\s\*]*\)\(\*\(longlong \*\)\(param_1 \+ 0x50\)\s*\+\s*(0x[0-9a-f]+)\)\s*;', code):
        var = rm.group(1) or rm.group(3)
        off = rm.group(2) or rm.group(4)
        rawvars[var] = (int(off, 16) // 16 if off else 0) + 1
    for var, slot in rawvars.items():
        tags = set()
        for tm in re.finditer(r'\(\*(?:\(uint \*\))?%s\s*&\s*0xf\)\s*==\s*(0x[0-9a-f]+|\d+)|\(\(byte\)\*%s\s*&\s*0xf\)\s*==\s*(0x[0-9a-f]+|\d+)' % (re.escape(var), re.escape(var)), code):
            tags.add(TAGS.get(int(tm.group(1) or tm.group(2), 0)))
        tags.discard(None)
        if tags and len(tags) == 1:
            setp(slot, next(iter(tags)), top_guard)
        elif slot not in params and re.search(r'\b%s\b' % re.escape(var), code[code.find(var) + len(var):]):
            setp(slot, 'any', top_guard)
    # checked arguments (luaL_check*, argument position given directly)
    for km in re.finditer(r'luaL_(checkinteger|checknumber|checklstring|optinteger|optnumber|optlstring)\s*\(\s*param_1\s*,\s*(\d+)', code):
        kind, slot = km.group(1), int(km.group(2))
        lt = {'checkinteger': 'integer', 'optinteger': 'integer', 'checknumber': 'number', 'optnumber': 'number', 'checklstring': 'string', 'optlstring': 'string'}[kind]
        setp(slot, lt, kind.startswith('opt'))
    for km in re.finditer(r'luaL_checktype\s*\(\s*param_1\s*,\s*(\d+)\s*,\s*(\d+)\)', code):
        slot, tag = int(km.group(1)), int(km.group(2))
        t = TAGS.get(tag)
        if t:
            setp(slot, t, False)
    # argument counts from the stack size test
    counts = {int(x) for x in re.findall(r'>> 4\)\s*==\s*(\d+)', code)}
    for vm in re.finditer(r'(\w+)\s*=\s*\(int\)\(\(longlong\)\w+\s*-\s*\(longlong\)\w+\s*>>\s*4\);', code):
        counts |= {int(x) for x in re.findall(r'\(%s == (\d+)\)' % re.escape(vm.group(1)), code)}
    # helpers receiving the Lua state may read arguments we cannot see
    unparsed = sorted({c.group(1) for c in CALL_RE.finditer(code)
                       if re.match(r'(?:thunk_)?FUN_', c.group(1)) and re.match(r'\s*\(\s*param_1\b', code[c.end() - 1:c.end() + 12])})
    # return values
    rets = {int(x) for x in re.findall(r'return (\d+);', code)}
    nret = max(rets) if rets else 0
    pushes = []
    for pm in re.finditer(r'(\*\w+|\w+\[\d+\])\s*=\s*([0-9]);|(hks_obj_newlstringhashed|hksi_lua_pushlstring|lua_pushstring)|(lua_createtable)|(hksi_lua_pushnil)|'
                          r'(hksi_lua_pushinteger|hksi_lua_pushnumber|lua_pushnumber)|(hksi_lua_pushboolean|lua_pushboolean)', code):
        if pm.group(1):
            var = pm.group(1).lstrip('*').split('[')[0]
            if not re.match(r'(?:puVar|plVar|pHVar|pfVar|pdVar|piVar)', var):
                continue
            pushes.append({0: 'nil', 1: 'boolean', 3: 'number'}.get(int(pm.group(2)), 'value'))
        elif pm.group(3):
            pushes.append('string')
        elif pm.group(4):
            pushes.append('table')
        elif pm.group(5):
            pushes.append('nil')
        elif pm.group(6):
            pushes.append('number')
        elif pm.group(7):
            pushes.append('boolean')
    # the highest slot with a gap filled by "any"
    if params:
        for s in range(1, max(params) + 1):
            if s not in params:
                params[s] = {'slot': s, 'lua_type': 'any', 'optional': True, 'unknown': True}
    callees = []
    for c in CALL_RE.finditer(code):
        n = c.group(1)
        if n.startswith(('hks', 'lua', 'luaL')) or n in ('if', 'while', 'return', 'sizeof'):
            continue
        callees.append(n)
    seen = set(); cl = []
    for n in callees:
        if n not in seen:
            seen.add(n); cl.append(n)
    return rva, {'params': [params[k] for k in sorted(params)], 'nret': nret, 'returns': pushes[:6], 'arg_counts': sorted(counts),
                 'unparsed_helpers': unparsed[:6], 'callees': [x for x in cl][:6], 'size': len(code)}


out = {}
for b in blocks:
    if not b.strip() or b.startswith('DECOMPILE'):
        continue
    rva, rec = parse(b)
    out[rva] = rec
json.dump(out, open(os.path.join(BASE, 'data', 'exe_lua_signatures.json'), 'w', encoding='utf8'), indent=0)
n_par = sum(1 for r in out.values() if r['params'])
print(len(out), 'wrappers;', n_par, 'with parameters;', sum(1 for r in out.values() if r['unparsed_helpers']), 'call helpers with the Lua state;',
      collections.Counter(len(r['params']) for r in out.values()).most_common(8))
