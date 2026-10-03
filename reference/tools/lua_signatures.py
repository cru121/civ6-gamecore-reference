"""Recover Lua method signatures from the decompiled l* wrapper functions.

Input : linux_depot/out/lua_wrappers_decomp.txt  (DecompList.java output for every registered wrapper, symbol build)
        linux_depot/out/functions.tsv            (Linux DWARF functions: parameter names for the C++ callee)
Output: docs_proto/data/lua_signatures.json      (keyed by wrapper RVA in the symbol build)
"""
import json
import os
import re
import collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
def P(*a): return os.path.join(ROOT, *a)

# ------------------------------------------------------------------ Linux parameter names
linux = collections.defaultdict(list)
linux_ret = {}
for i, l in enumerate(open(P('linux_depot', 'out', 'functions.tsv'), encoding='utf8')):
    if i == 0:
        continue
    p = l.rstrip('\n').split('\t')
    if len(p) >= 5 and p[3]:
        params = []
        for x in [y.strip() for y in p[4].split(';') if y.strip()]:
            m = re.match(r'(.*?)(\w+)$', x)
            params.append((m.group(1).strip(), m.group(2)) if m else (x, '_'))
        linux[p[3]].append(params)
        linux_ret.setdefault(p[3], p[5])

# ------------------------------------------------------------------ parsing helpers
text = open(P('linux_depot', 'out', 'lua_wrappers_decomp.txt'), encoding='utf8', errors='replace').read()
blocks = text.split('\n@@@ ')
blocks[0] = blocks[0][4:] if blocks[0].startswith('@@@ ') else blocks[0]

HELPERS = {  # helper name -> (kind, lua type, optional?)
    'GetNumberOrHash': ('number-or-hash', 'number|string', False),
    'GetNumberOrHashArray': ('number-or-hash-array', 'table', False),
    'GetTypeHash': ('type-hash', 'string|number', False),
    'GetPlayerInstance': ('player-instance', 'Player', False),
    'GetPlayerID': ('player-id', 'integer|Player', False),
    'GetUnitInstance': ('unit-instance', 'Unit', False),
    'GetDistrictInstance': ('district-instance', 'District', False),
    'GetCityInstance': ('city-instance', 'City', False),
    'GetItemType': ('item-type', 'string|number', False),
    'GetCommandType': ('command-type', 'string|number', False),
    'GetOperationType': ('operation-type', 'string|number', False),
    'GetItemValueType': ('item-value-type', 'string|number', False),
    'GetFractalFlags': ('fractal-flags', 'number', False),
    'GetFeatureParameters': ('feature-parameters', 'table', False),
    'TableToTypedVariantMap': ('table', 'table', False),
    'luaL_checkinteger': ('integer', 'integer', False),
    'luaL_optinteger': ('integer', 'integer', True),
    'luaL_checknumber': ('number', 'number', False),
    'luaL_optnumber': ('number', 'number', True),
    'luaL_checklstring': ('string', 'string', False),
    'luaL_optlstring': ('string', 'string', True),
    'luaL_optbool': ('boolean', 'boolean', True),
    'hksi_lua_tointeger': ('integer', 'integer', False),
    'hksi_lua_tonumber': ('number', 'number', False),
    'hksi_lua_toboolean': ('boolean', 'boolean', False),
    'hksi_lua_tostring': ('string', 'string', False),
}
HELP_RE = re.compile(r'(?:(\w+)\s*=\s*)?(?:\([\w\s\*]+\))?((?:[\w:]+::)?(' + '|'.join(HELPERS) + r'))\s*\(\s*param_1\s*,\s*(\d+)')
INST_RE = re.compile(r'(?:(\w+)\s*=\s*)?((?:[\w:]*::)?(?:Scoped(?:Virtual)?Instance)<([\w:]+),[^>]*>\s*::\s*GetInstance)\s*\(\s*param_1\s*,\s*(\d+)', re.S)
INL_RE = re.compile(r'(hks_obj_tonumber|hks_obj_tolstring|hks_obj_isnumber|hks_obj_toboolean)\s*\(\s*param_1\s*,\s*([^;]*?)\)\s*;?', re.S)
BASE_RE = re.compile(r'param_1 \+ 0x50\)(?:\s*\+\s*(0x[0-9a-f]+))?')
PUSH_OBJ_RE = re.compile(r'(?:[\w:]+::)*Scoped(?:Virtual)?Instance<([\w:]+),[^>]*>\s*::\s*Push\s*\(\s*param_1', re.S)
DECL_RE = re.compile(r'^\s+([A-Za-z_][\w:<>,\* ]*?)\s+\**(\w+)(?:\[\d+\])?;$', re.M)
SIMPLE = {'int', 'uint', 'bool', 'double', 'float', 'char', 'longlong', 'ulonglong', 'undefined4', 'undefined8', 'undefined', 'byte', 'short', 'ushort', 'undefined2', 'undefined1', 'char *', 'void *'}


def lua_obj(iface):
    n = iface.split('::')[-1]
    return re.sub(r'^I(?=[A-Z])', '', n)


def parse(block):
    head, _, body = block.partition('\n')
    rva, name = head.split('\t')[:2]
    m = re.search(r'\n\{\n(.*)\n\}', body, re.S)
    code = m.group(1) if m else body
    decls = {}
    for dm in DECL_RE.finditer(code.split('\n\n')[0] if '\n\n' in code else code):
        decls[dm.group(2)] = dm.group(1).strip()
    sig = {'self': False, 'params': {}, 'returns': [], 'nret': 0, 'notes': []}
    params = sig['params']
    vars_by_idx = {}

    def setp(idx, kind, ltype, optional, var=None, obj=None):
        cur = params.get(idx)
        rec = {'index': idx, 'kind': kind, 'lua_type': ltype, 'optional': optional}
        if var: rec['var'] = var
        if obj: rec['object'] = obj
        if cur is None or (cur.get('kind') in ('unknown',) and kind != 'unknown'):
            params[idx] = rec
        if var: vars_by_idx[var] = idx

    # instances
    for im in INST_RE.finditer(code):
        var, _, tmpl, idx = im.group(1), im.group(2), im.group(3), int(im.group(4))
        if idx in (0, 1):
            sig['self'] = True
            sig['self_object'] = lua_obj(tmpl)
            if var: vars_by_idx[var] = 1
        else:
            setp(idx, 'object', lua_obj(tmpl), False, var, lua_obj(tmpl))
    # helpers (explicit index)
    for hm in HELP_RE.finditer(code):
        var, _, hname, idx = hm.group(1), hm.group(2), hm.group(3), int(hm.group(4))
        kind, lt, opt = HELPERS[hname]
        setp(idx, kind, lt, opt, var)
    # inline stack reads (balanced-parenthesis scan)
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
    for im in re.finditer(r'(hks_obj_tonumber|hks_obj_tolstring|hks_obj_isnumber|hks_obj_toboolean)\s*\(', code):
        fn = im.group(1)
        expr = balanced(code, im.end() - 1)
        bm = BASE_RE.search(expr)
        if not bm:
            continue
        k = int(bm.group(1), 16) // 16 if bm.group(1) else 0
        idx = k + 1
        pre = code[max(0, im.start() - 200):im.start()]
        opt = bool(re.search(r'if \([^{]*param_1 \+ 0x48', pre)) and '}' not in pre.split('if (')[-1]
        kind, lt = {'hks_obj_tonumber': ('number', 'number'), 'hks_obj_tolstring': ('string', 'string'),
                    'hks_obj_isnumber': ('number', 'number'), 'hks_obj_toboolean': ('boolean', 'boolean')}[fn]
        am = re.search(r'(\w+)\s*=\s*(?:\([\w\s\*]+\))?\s*$', code[max(0, im.start() - 40):im.start()])
        setp(idx, kind, lt, opt, am.group(1) if am else None)
    # stack pointer variables compared with the stack top: an optional argument read through a raw pointer
    for pm in re.finditer(r'(\w+)\s*=\s*\([\w\s\*]+\)\(\*\(longlong \*\)\(param_1 \+ 0x50\)\s*\+\s*(0x[0-9a-f]+)\);', code):
        var, off = pm.group(1), int(pm.group(2), 16)
        idx = off // 16 + 1
        if idx in params:
            continue
        rest = code[pm.end():pm.end() + 400]
        if re.search(r'if \(%s < \*' % re.escape(var), rest):
            is_bool = bool(re.search(r'& 0xf', rest)) and bool(re.search(r'== 1', rest))
            setp(idx, 'boolean' if is_bool else 'value', 'boolean' if is_bool else 'any', True, var)
    # plot location helpers: (x, y) or a plot index starting at the given argument
    for qm in re.finditer(r'Utility::(GetPlotLocation|GetPlotIndex|GetPlotInstance)\s*\(\s*param_1\s*,[^,]*,\s*(\d+)', code):
        start = int(qm.group(2))
        label = {'GetPlotLocation': 'plot location', 'GetPlotIndex': 'plot index', 'GetPlotInstance': 'plot'}[qm.group(1)]
        setp(start, 'plot-x', 'integer|Plot', False)
        params[start]['name'] = 'x' if qm.group(1) != 'GetPlotInstance' else 'plot'
        params[start]['note'] = label + ' given as (x, y)' + ('' if qm.group(1) == 'GetPlotInstance' else ', or as a single plot index') + ' (inferred from the helper name)'
        if qm.group(1) != 'GetPlotInstance':
            setp(start + 1, 'plot-y', 'integer', True)
            params[start + 1]['name'] = 'y'
            sig['plot_start'] = start
    # argument index taken from a variable (follows a helper that consumed 1 or 2 arguments)
    for dm in re.finditer(r'hksi_lua_tointeger\(param_1,(?!\d)', code):
        start = sig.get('plot_start')
        if start:
            setp(start + 2, 'integer', 'integer', True)
    # any other helper that receives the Lua state may read arguments we do not understand
    known = set(HELPERS) | {'GetPlotLocation', 'GetPlotIndex', 'GetPlotInstance', 'GetInstance', 'Push', 'PushVector', 'PushObject', 'CheckScopedInstanceType',
                            'GetProperty', 'SetProperty', 'argerror'}
    unparsed = set()
    for um in re.finditer(r'((?:[A-Za-z_]\w*::)*[A-Za-z_~]\w*)\s*\(\s*param_1\s*[,)]', code):
        fn = um.group(1).split('::')[-1]
        if fn in known or fn.startswith(('hks', 'lua', 'luaL')) or fn.startswith('Push') or fn.startswith(('Get', 'Push')) and 'Instance' in um.group(1):
            continue
        unparsed.add(fn)
    sig['unparsed'] = sorted(unparsed)
    counts = {int(x) for x in re.findall(r'>> 4\)\s*==\s*(\d+)', code)}
    for vm in re.finditer(r'(\w+)\s*=\s*\(int\)\(\(longlong\)\w+\s*-\s*\(longlong\)\w+\s*>>\s*4\);', code):
        counts |= {int(x) for x in re.findall(r'\(%s == (\d+)\)' % re.escape(vm.group(1)), code)}
    sig['arg_counts'] = sorted(counts)
    # wrapper templates: MethodWrapper<Iface,Class>::BasicLuaMethod<Ret, Arg1, Arg2...>(L, Callee)
    wm = re.search(r'MethodWrapper<[^>]*>\s*::\s*BasicLuaMethod\s*<([^;]*?)>\s*\(\s*param_1\s*,\s*([\w:]+)\s*\)', code, re.S)
    if wm:
        targs = [a.strip() for a in re.split(r',(?![^<]*>)', re.sub(r'\s+', ' ', wm.group(1)))]
        sig['self'] = True
        sig['template_return'] = targs[0]
        callee_fn = wm.group(2)
        cands = linux.get('GameCore::' + callee_fn) or linux.get(callee_fn) or []
        nonthis = lambda c: [x for x in c if x[1] != 'this']
        pl_all = None
        for c in cands:
            if len(nonthis(c)) in (len(targs), len(targs) - 1):
                pl_all = c
                break
        pl = nonthis(pl_all) if pl_all else []
        if pl_all is not None and len(pl) == len(targs):
            sig['template_return'] = 'void'
            arg_types = targs
        else:
            arg_types = targs[1:]
        for i, ta in enumerate(arg_types):
            ta = ta.replace('___ptr64', '').strip()
            if ta in ('int', 'uint', 'unsigned int', 'short', 'char', 'longlong'):
                lt = 'integer'
            elif ta == 'bool':
                lt = 'boolean'
            elif ta.startswith('char const') or 'char_const' in ta or 'string' in ta:
                lt = 'string'
            elif ta in ('float', 'double'):
                lt = 'number'
            elif ta.startswith('GameCore::') and ta.endswith('Types'):
                lt = 'integer'
            else:
                lt = 'any'
            rec = {'index': i + 2, 'kind': lt, 'lua_type': lt, 'optional': True, 'note': 'wrapper template: omitted arguments are read as defaults (inferred from script usage)'}
            if lt == 'integer' and ta.startswith('GameCore::'):
                rec['cpp_type'] = ta.replace('GameCore::', '')
            if i < len(pl) and pl[i][1] not in ('this', '_'):
                rec['name'] = pl[i][1]
            params[i + 2] = rec
        sig['callee'] = callee_fn
        sig['template_wrapper'] = True
    # return values
    rets = set(int(x) for x in re.findall(r'return (\d+);', code))
    sig['nret'] = max(rets) if rets else 0
    pushes = []
    for pm in re.finditer(r'(\*\w+|\w+\[\d+\])\s*=\s*([0-9]);|(hksi_lua_pushlstring|lua_pushstring|hks_obj_newlstringhashed)|(lua_createtable)|'
                          r'(?:[\w:]+::)*Scoped(?:Virtual)?Instance<([\w:]+),[^>]*>\s*::\s*Push\s*\(|(hksi_lua_pushnil)|'
                          r'(hksi_lua_pushinteger|hksi_lua_pushnumber|lua_pushnumber)|(hksi_lua_pushboolean|lua_pushboolean)|'
                          r'(?<![\w:])(?:[\w:]+::)?Push(Player|Drought|Storm|Event|RiverInfo|Park|OneOff|MissionToLua|ArifactAtIndex|Artifact|\w+)\s*\(\s*param_1|'
                          r'(hks_pushnamedcclosure)', code):
        pos = pm.start()
        if pm.group(1):
            var = pm.group(1).lstrip('*').split('[')[0]
            if not var.startswith(('puVar', 'plVar', 'pHVar', 'pfVar')):
                continue
            tag = int(pm.group(2))
            pushes.append(({0: 'nil', 1: 'boolean', 3: 'number'}.get(tag, 'value%d' % tag), pos))
        elif pm.group(3):
            pushes.append(('string', pos))
        elif pm.group(4):
            pushes.append(('table', pos))
        elif pm.group(5):
            pushes.append((lua_obj(pm.group(5)), pos))
        elif pm.group(6):
            pushes.append(('nil', pos))
        elif pm.group(7):
            pushes.append(('number', pos))
        elif pm.group(8):
            pushes.append(('boolean', pos))
        elif pm.group(9) and pm.group(9) not in ('Vector', 'Object'):
            pushes.append((pm.group(9), pos))
        elif pm.group(9):
            pushes.append(('table' if pm.group(9) == 'Vector' else 'object', pos))
        elif pm.group(10):
            pushes.append(('iterator', pos))
    sig['pushes'] = [p[0] for p in pushes]
    # semantic C++ type per argument variable (from the declaration of the variable that receives the value)
    for v, idx in vars_by_idx.items():
        t = decls.get(v)
        if t and idx in params and t not in SIMPLE and params[idx]['kind'] != 'object' and not t.startswith('Instance'):
            params[idx]['cpp_type'] = t
    # gaps between the first and the last recognised argument are arguments we could not classify
    if params:
        lo = 2 if sig['self'] else 1
        for idx in range(lo, max(params) + 1):
            if idx not in params:
                params[idx] = {'index': idx, 'kind': 'unknown', 'lua_type': 'any', 'optional': True, 'unknown': True}
    for idx in [i for i in params if i < (2 if sig['self'] else 1)]:
        rec = params.pop(idx)
        rec['index'] = 2 if sig['self'] else 1
        rec['note'] = 'the code reads stack slot %d (the object itself); a value passed here is probably ignored (inferred)' % idx
        params.setdefault(rec['index'], rec)
    # callee parameter names
    def argvar(a):
        a2 = re.sub(r'^\([\w\s\*:]+\)', '', a).strip('() ')
        if a2 in vars_by_idx:
            return a2
        dm = re.match(r'^\*\([\w\s\*:]+\)\(\s*(\w+)\s*\+\s*0x[0-9a-f]+\s*\)$', a.strip())      # a field read from an object argument
        return dm.group(1) if dm else a2
    callee = None
    for cm in re.finditer(r'(?:\w+\s*=\s*)?((?:[A-Za-z_]\w*::)+[A-Za-z_~]\w*)\s*\(([^;]*)\)\s*;', code, re.S):
        fn, args = cm.group(1), cm.group(2)
        if fn.startswith(('hks', 'lua', 'std::', 'GameCore::Lua', 'Utility::')) or 'ScopedInstance' in fn or 'ScopedVirtual' in fn or 'GetInstance' in fn or '::Push' in fn:
            continue
        al = [a.strip() for a in re.split(r',(?![^(<]*[)>])', args.replace('\n', ' '))]
        if any(argvar(a) in vars_by_idx for a in al):
            callee = (fn, al)
    if callee:
        fn, al = callee
        cands = linux.get('GameCore::' + fn) or linux.get(fn) or []
        cands = [c for c in cands if abs(len(c) - len(al)) <= 1] or cands
        if cands:
            pl = cands[0]
            off = 0 if pl and pl[0][1] == 'this' else 0
            for pos, a in enumerate(al):
                idx = vars_by_idx.get(argvar(a))
                if idx and idx in params and pos < len(pl):
                    nm = pl[pos][1]
                    if nm not in ('this', '_'):
                        params[idx].setdefault('name', nm)
                        if pl[pos][0] and 'cpp_type' not in params[idx] and params[idx]['kind'] != 'object' and not re.match(r'^(int|uint|bool|float|double|unsigned int)$', pl[pos][0]):
                            params[idx]['cpp_type'] = pl[pos][0].replace('GameCore::', '').strip(' *&')
        sig['callee'] = fn
    sig['_code'] = code
    return rva, name, sig


import sys
sys.path.insert(0, os.path.dirname(__file__))
from lua_returns import analyze
import pefile
_pe = pefile.PE('C:/Program Files (x86)/Steam/steamapps/content/app_289070/depot_947510/DLC/Expansion2/Binaries/Win64/GameCore_XP2_FinalRelease.dll', fast_load=True)
_img = _pe.get_memory_mapped_image()
IMAGE_BASE = _pe.OPTIONAL_HEADER.ImageBase
BASIC = {'int', 'uint', 'bool', 'float', 'double', 'unsigned int', 'void', 'int32', 'uint32', 'char', 'short', 'int64', 'uint64'}


def read_string(addr, n):
    o = addr - IMAGE_BASE
    return bytes(_img[o:o + n]).decode('latin1')


by_tail = collections.defaultdict(list)       # unqualified function name -> [(qualname, params)]
for q, lists in linux.items():
    for pl_ in lists:
        by_tail[q.rsplit('::', 1)[-1]].append((q, pl_))


def type_ok(lua_type, cpp):
    cpp = cpp.replace('GameCore::', '').replace('const ', '').strip(' *&')
    if lua_type == 'integer':
        return cpp in ('int', 'uint', 'unsigned int', 'short', 'char', 'int64', 'uint64', 'int32', 'uint32') or cpp.endswith('Types') or cpp.endswith('Index')
    if lua_type == 'boolean':
        return cpp == 'bool'
    if lua_type == 'number':
        return cpp in ('float', 'double', 'int', 'uint', 'unsigned int', 'short', 'int64', 'uint64', 'int32', 'uint32') or cpp.startswith('FixedPoint') or cpp.endswith('Types')
    if lua_type == 'string':
        return 'char' in cpp or 'String' in cpp
    return True


def name_fallback(ps, sig, wrapper_name):
    """Name arguments the callee match left unnamed: (1) by position when the callee has as many parameters as the Lua
    method and the types agree; (2) when no callee was found, by looking for a Linux function with the method's own name."""
    todo = [p for p in ps if not p.get('name')]
    if not todo:
        return
    cands = []
    src = 'callee-position'
    callee = sig.get('callee')
    if callee and '_vcall' not in callee:
        cands = linux.get('GameCore::' + callee) or linux.get(callee) or []
    elif not callee:
        src = 'method-name'
        meth = wrapper_name.split('::')[-1]
        meth = meth[1:] if re.match(r'^l[A-Z]', meth) else meth
        obj = (sig.get('self_object') or wrapper_name.split('::')[-2] if '::' in wrapper_name else '') or ''
        toks = [t[:5].lower() for t in re.findall(r'[A-Z][a-z]+|[A-Z]+(?![a-z])', re.sub(r'^I(?=[A-Z])', '', obj.split('::')[-1])) if len(t) >= 4]
        cands = [pl_ for q, pl_ in by_tail.get(meth, []) if toks and any(t in q.rsplit('::', 1)[0].lower() for t in toks)]
    hits = []
    for c in cands:
        nt = [x for x in c if x[1] != 'this']
        if len(nt) != len(ps) or any(x[1] in ('_', '') for x in nt):
            continue
        if all(type_ok(p['lua_type'], x[0]) and p.get('name', x[1]) == x[1] for p, x in zip(ps, nt)):
            hits.append(nt)
    uniq = {tuple(x[1] for x in h) for h in hits}
    if len(uniq) != 1:
        return
    names = list(uniq)[0]
    if len(set(names)) != len(names):
        return
    for p, n in zip(ps, names):
        if not p.get('name'):
            p['name'] = n
            p['name_source'] = src


# ------------------------------------------------------------------ constant-return stubs
# The compiler merges identical functions, so a stub that only returns zero carries one arbitrary name in the symbol build
# (here Cache::City::CulturalIdentity::GetIdentityPerTurnFromNearbyOwnedCities). A wrapper that calls one has no usable callee name.
import capstone
_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
_cg = {}
for _l in open(P('callgraph_old.tsv')):
    if not _l.startswith('#'):
        _a, _b = _l.rstrip('\n').split('\t')
        _cg[int(_a, 16)] = [int(x, 16) for x in _b.split(',') if x]
ZERO_STUBS = {'xor eax, eax ; ret', 'mov dword ptr [rdx], 0 ; mov rax, rdx ; ret', 'mov eax, 0 ; ret', 'xor al, al ; ret', 'mov al, 0 ; ret',
              'mov qword ptr [rdx], 0 ; mov rax, rdx ; ret'}


def _result_used_in_branch(wrapper_rva, target):
    """True when the wrapper tests the stub's result and jumps (the stub is one term of a larger condition, like IsCanyon inside
    IsOpenGround), or when the wrapper is large (a stub used as one term among many, as in GetIdentitySourcesBreakdown)."""
    w = int(wrapper_rva, 16)
    ins = list(_md.disasm(bytes(_img[w:w + 700]), w))
    for k, i in enumerate(ins):
        if i.mnemonic == 'call' and i.op_str == hex(target):
            if any(j.mnemonic.startswith('j') and j.mnemonic != 'jmp' for j in ins[k + 1:k + 5]):
                return True
    return False


_fsize = {}
for _r in json.load(open(P('docs_proto', 'data', 'function_index.json')))['rows']:
    _fsize[int(_r[1], 16)] = _r[3]


def _shape_of(c):
    ins = []
    for i in _md.disasm(bytes(_img[c:c + 24]), c):
        ins.append(('%s %s' % (i.mnemonic, i.op_str)).strip())
        if i.mnemonic in ('ret', 'jmp') or len(ins) >= 3:
            break
    return ' ; '.join(ins)


def _two_level_stub(wrapper_rva):
    """Wrapper -> small function -> zero stub whose result is returned untested (Cache::Player::Culture::GetEnactPolicyCost).
    Only zero/false results count: a stub returning 1 is a common tag argument, not a result."""
    for c1 in _cg.get(int(wrapper_rva, 16), []):
        size = _fsize.get(c1, 0)
        if not size or size > 160 or _shape_of(c1) in ZERO_STUBS:
            continue
        for c2 in _cg.get(c1, []):
            if _shape_of(c2) in ZERO_STUBS and _fsize.get(c2, 99) <= 12:
                ins = list(_md.disasm(bytes(_img[c1:c1 + size]), c1))
                for k, i in enumerate(ins):
                    if i.mnemonic == 'call' and i.op_str == hex(c2):
                        if not any((j.mnemonic.startswith('j') and j.mnemonic != 'jmp') or j.mnemonic == 'test' for j in ins[k + 1:k + 5]):
                            return _shape_of(c2) + ' (via a helper)'
    return None


def stub_callee(wrapper_rva):
    """Return the shape of a zero-returning stub the wrapper calls directly, else None."""
    callees = _cg.get(int(wrapper_rva, 16), [])
    two = _two_level_stub(wrapper_rva)
    if two:
        return two
    if len(callees) > 16:       # a big wrapper that happens to call a stub among many other things
        return None
    for c in callees:
        ins = []
        for i in _md.disasm(bytes(_img[c:c + 24]), c):
            ins.append('%s %s' % (i.mnemonic, i.op_str))
            if i.mnemonic in ('ret', 'jmp') or len(ins) >= 4:
                break
        shape = ' ; '.join(ins).strip()
        if shape in ZERO_STUBS or shape == 'mov eax, 1 ; ret':
            if _result_used_in_branch(wrapper_rva, c):
                continue
            return shape
        # zero-filled result vector: stores 0 on the stack, asks for the yield definitions (0x7d1520) and assigns that many zeros (0x36f150)
        long_ins = [('%s %s' % (i.mnemonic, i.op_str)) for i in _md.disasm(bytes(_img[c:c + 64]), c)][:16]
        if any(x.startswith('mov dword ptr [rsp') and x.endswith(', 0') for x in long_ins) and 'call 0x7d1520' in long_ins and 'call 0x36f150' in long_ins:
            return 'zero-filled vector, one 0 per yield type'
    return None


COMPOSITE = {'Player::CityID'}      # one C++ value built from two Lua arguments (player id + city id)


def repair_composite(ps, sig, wrapper_name):
    """The callee match pairs Lua arguments with C++ parameters by position. When the callee takes a composite value
    (a CityID made of a player id and a city id) that pairing is shifted and gives wrong names (an Origin* method with
    a parameter called destinationCity). Use the Cache:: twin of the callee, which takes the pieces separately, when it
    fits; otherwise drop the names and types that came from the composite or contradict the method's direction."""
    callee = sig.get('callee')
    bad = [p for p in ps if p.get('cpp_type') in COMPOSITE]
    meth = wrapper_name.split('::')[-1].lower()
    for p in ps:
        n = (p.get('name') or '').lower()
        if n and (('destination' in n and 'origin' in meth and 'destination' not in meth) or ('origin' in n and 'destination' in meth and 'origin' not in meth)):
            bad.append(p)
    if not bad:
        return
    twin = None
    if callee and not callee.startswith('Cache::'):
        for c in linux.get('GameCore::Cache::' + callee) or []:
            nt = [x for x in c if x[1] != 'this']
            if len(nt) >= len(ps) and all(type_ok(p['lua_type'], x[0]) and x[1] not in ('_', '') for p, x in zip(ps, nt)):
                twin = nt[:len(ps)]
                break
    for i, p in enumerate(ps):
        if p in bad or twin:
            if p.get('cpp_type') in COMPOSITE:
                del p['cpp_type']
            if twin:
                p['name'], p['name_source'] = twin[i][1], 'cache-twin'
                t = twin[i][0].replace('GameCore::', '').strip(' *&')
                if t.endswith('Types') and p['lua_type'] in ('integer', 'number'):
                    p['cpp_type'] = t
            elif p in bad:
                p.pop('name', None)
                p.pop('name_source', None)


out = {}
stats = collections.Counter()
for b in blocks:
    if not b.strip():
        continue
    rva, name, sig = parse(b)
    ps = [sig['params'][k] for k in sorted(sig['params'])]
    stub = stub_callee(rva)
    if stub:
        # names and types borrowed from the merged function's label would be wrong
        sig['callee'] = None
        for p in ps:
            for k in ('name', 'name_source', 'cpp_type'):
                p.pop(k, None)
    else:
        name_fallback(ps, sig, name)
        repair_composite(ps, sig, name)
    # arguments must be contiguous from index 2 (instance) or 1 (static)
    first = 2 if sig['self'] else 1
    contiguous = [p['index'] for p in ps] == list(range(first, first + len(ps)))
    n_push = len(sig['pushes'])
    conf = 'high'
    if any(p.get('unknown') for p in ps):
        conf = 'partial'
    elif not contiguous:
        conf = 'low'
    elif sig['nret'] and n_push < sig['nret']:
        conf = 'partial'
    elif 'luaL_argerror' in b or sig['unparsed']:
        conf = 'partial'
    # collapse branch duplicates: keep the last nret pushes
    returns = sig['pushes'][-sig['nret']:] if sig['nret'] and n_push >= sig['nret'] else sig['pushes'][:sig['nret']]
    if sig.get('template_wrapper'):
        tr = sig['template_return'].replace('___ptr64', '').strip()
        rmap = 'none' if tr == 'void' else ('boolean' if tr == 'bool' else ('integer' if tr in ('int', 'uint', 'unsigned int') or tr.endswith('Types') else ('number' if tr in ('float', 'double') else ('string' if 'char' in tr else tr.replace('GameCore::', '')))))
        returns = [] if rmap == 'none' else [rmap]
        conf = 'high'
    details, nothing, consistent = ([], False, False)
    if not sig.get('template_wrapper'):
        details, nothing, consistent = analyze(sig['_code'], read_string)
    rd = []
    if consistent and details and len(details) == sig['nret']:
        for d in details:
            rd.append(d if isinstance(d, dict) else {'type': d})
        cret = None
        if sig.get('callee'):
            cret = linux_ret.get('GameCore::' + sig['callee'])
        if cret and len(rd) == 1 and rd[0]['type'] in ('number', 'boolean') and cret.replace('GameCore::', '') not in BASIC:
            rd[0]['cpp_type'] = cret.replace('GameCore::', '').strip(' *&')
        returns = [r['type'] if isinstance(r['type'], str) else 'table' for r in rd]
    out[rva] = {'wrapper': name.split('::')[-1], 'cpp_class': name.rsplit('::', 1)[0], 'static': not sig['self'], 'self_object': sig.get('self_object'),
                'params': ps, 'nret': sig['nret'], 'returns': returns, 'callee': sig.get('callee'), **({'returns_constant_stub': stub} if stub else {}), **({'unparsed_helpers': sig['unparsed']} if sig['unparsed'] else {}), **({'arg_counts': sig['arg_counts']} if len(sig.get('arg_counts', [])) > 1 else {}), 'confidence': conf, **({'return_details': rd} if rd else {}), **({'may_return_nothing': True} if nothing else {})}
    stats[conf] += 1
    stats['params=%d' % min(len(ps), 6)] += 1
json.dump(out, open(P('docs_proto', 'data', 'lua_signatures.json'), 'w', encoding='utf8'), indent=1)
print(len(out), dict(stats))
