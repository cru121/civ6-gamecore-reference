"""Reconstruct what a Lua wrapper returns (types, table shapes) by replaying its pushes on a small model of the Lua stack."""
import re

TAG_RE = re.compile(r'(?:\*\(undefined4 \*\)(?P<v1>\w+)|\*(?P<v2>\w+)|(?P<v3>\w+)\[(?P<i3>\d+)\])\s*=\s*(?P<tag>\d);')
EVENT_RE = re.compile(
    r'(?P<create>lua_createtable\s*\()'
    r'|(?P<setfield>hksi_lua_setfield\s*\(\s*param_1\s*,\s*-2\s*,\s*"(?P<fname>[^"]*)"\s*\))'
    r'|(?P<pushl>(?:hksi_lua_pushlstring|lua_pushstring)\s*\(\s*param_1\s*,\s*(?:"(?P<lit>[^"]*)"|\w+))'
    r'|(?P<hashed>hks_obj_newlstringhashed\s*\([^,]*,[^,]*,\s*(?P<addr>0x[0-9a-f]+)\s*,\s*(?P<len>\d+)\s*\))'
    r'|(?P<settable>hks_obj_settable\s*\(|hks_obj_rawset\s*\()'
    r'|(?P<rawseti>hks_obj_rawseti\s*\(|hksi_lua_rawseti\s*\()'
    r'|(?P<obj>Scoped(?:Virtual)?Instance<(?P<otype>[\w:]+),[^>]*>\s*::\s*Push\s*\()'
    r'|(?P<pushnamed>(?<![\w:])(?:[\w:]+::)?Push(?P<pname>Player|Drought|Storm|Event|RiverInfo|Park|OneOff|MissionToLua|ArifactAtIndex|Artifact|Vector|Object)\s*\(\s*param_1)'
    r'|(?P<pnum>hksi_lua_pushinteger|hksi_lua_pushnumber|lua_pushnumber)'
    r'|(?P<pbool>hksi_lua_pushboolean|lua_pushboolean)'
    r'|(?P<pnil>hksi_lua_pushnil)'
    r'|(?P<closure>hks_pushnamedcclosure)'
    r'|(?P<ret>return\s+(?P<n>\d+)\s*;)'
    r'|(?P<tag>(?:\*\(undefined4 \*\)\w+|\*\w+|\w+\[\d+\])\s*=\s*[0-9]\s*;)')


def lua_obj(t):
    n = t.split('::')[-1]
    return re.sub(r'^I(?=[A-Z])', '', n)


def merge(a, b):
    """Merge two type descriptions (used for alternatives and array elements)."""
    if a == b:
        return a
    if a is None:
        return b
    if b is None:
        return a
    if isinstance(a, dict) and isinstance(b, dict) and a.get('type') == b.get('type') == 'table':
        out = {'type': 'table'}
        fa = {f['name']: f['type'] for f in a.get('fields', [])}
        fb = {f['name']: f['type'] for f in b.get('fields', [])}
        names = list(fa) + [n for n in fb if n not in fa]
        if names:
            out['fields'] = [{'name': n, 'type': merge(fa.get(n), fb.get(n))} for n in names]
        ea, eb = a.get('array_of'), b.get('array_of')
        if ea is not None or eb is not None:
            out['array_of'] = merge(ea, eb)
        return out
    sa = a if isinstance(a, str) else 'table'
    sb = b if isinstance(b, str) else 'table'
    if sa == sb:
        return a if isinstance(a, dict) else b
    return '%s|%s' % (sa, sb) if sa not in sb.split('|') else sb


def analyze(code, read_string, callee_ret=None):
    """Returns (return_types, nothing_possible, consistent). return_types: one description per return position."""
    stack = []
    snapshots = []
    nrets = set()
    consistent = True
    last_str_lit = None

    def push(t, lit=None):
        stack.append({'t': t, 'lit': lit})

    def pop():
        nonlocal consistent
        if not stack:
            consistent = False
            return {'t': 'any', 'lit': None}
        return stack.pop()

    def table_top():
        nonlocal consistent
        if not stack or not (isinstance(stack[-1]['t'], dict) and stack[-1]['t'].get('type') == 'table'):
            consistent = False
            return None
        return stack[-1]['t']

    for m in EVENT_RE.finditer(code):
        if m.group('create'):
            push({'type': 'table', 'fields': [], 'array_of': None})
        elif m.group('setfield'):
            v = pop()
            t = table_top()
            if t is not None:
                t['fields'].append({'name': m.group('fname'), 'type': v['t']})
        elif m.group('pushl'):
            push('string', m.group('lit'))
        elif m.group('hashed'):
            try:
                lit = read_string(int(m.group('addr'), 16), int(m.group('len')))
            except Exception:
                lit = None
            push('string', lit)
        elif m.group('settable'):
            a = pop()
            b = pop()
            # the game rotates the stack so the key ends up below the value; whichever of the two is a string literal is the key
            if a['lit'] is not None and b['lit'] is None:
                k, v = a, b
            else:
                k, v = b, a
            t = table_top()
            if t is not None:
                if k['lit'] is not None:
                    t['fields'].append({'name': k['lit'], 'type': v['t']})
                else:
                    t['array_of'] = merge(t['array_of'], v['t'])
        elif m.group('rawseti'):
            v = pop()
            t = table_top()
            if t is not None:
                t['array_of'] = merge(t['array_of'], v['t'])
        elif m.group('obj'):
            push(lua_obj(m.group('otype')))
        elif m.group('pushnamed'):
            pn = m.group('pname')
            push('table' if pn == 'Vector' else ('object' if pn == 'Object' else pn))
        elif m.group('pnum'):
            push('number')
        elif m.group('pbool'):
            push('boolean')
        elif m.group('pnil'):
            push('nil')
        elif m.group('closure'):
            push('function')
        elif m.group('tag'):
            tm = TAG_RE.search(m.group('tag'))
            if not tm:
                continue
            var = tm.group('v1') or tm.group('v2') or tm.group('v3')
            if not var.startswith(('pu', 'pl', 'pH', 'pf')):
                continue
            if tm.group('v3') is not None and int(tm.group('i3')) % 4 != 0:
                continue          # value slot, not the type tag
            tag = int(tm.group('tag'))
            if tag in (0, 1, 3):
                push({0: 'nil', 1: 'boolean', 3: 'number'}[tag])
        elif m.group('ret'):
            n = int(m.group('n'))
            nrets.add(n)
            if n and len(stack) >= n:
                snapshots.append([e['t'] for e in stack[-n:]])
            elif n:
                consistent = False
    if not nrets:
        return [], False, True
    best = max(nrets)
    types = None
    for snap in snapshots:
        if len(snap) != best:
            continue
        if types is None:
            types = list(snap)
        else:
            types = [merge(a, b) for a, b in zip(types, snap)]
    if types is None:
        return [], 0 in nrets, False
    # a table that never received a field or element is just "table"
    out = []
    for t in types:
        if isinstance(t, dict):
            t = dict(t)
            if not t.get('fields'):
                t.pop('fields', None)
            if t.get('array_of') is None:
                t.pop('array_of', None)
            elif t.get('array_of') == 'nil':
                t['array_of'] = 'any'
        out.append(t)
    return out, (0 in nrets and best > 0), consistent
