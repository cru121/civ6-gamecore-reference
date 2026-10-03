"""Generate data/ce_methods.json (what the Community Extension adds to Lua) and data/native.json (engine functions that are not
reachable from Lua out of the box: analysed ones, gap-list candidates and the ones the Community Extension wraps)."""
import collections
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs_proto', 'data')
UP = os.path.join(ROOT, 'upstream')
WIKI = os.path.join(ROOT, 'upstream_wiki')


def P(*a):
    return os.path.join(ROOT, *a)


def snake(n):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', n).upper()


# ------------------------------------------------------------------ CE offsets from the source headers
ce_offsets = {}   # header -> {CONSTANT_NAME: rva}
for f in os.listdir(UP):
    if f.endswith('.h'):
        for m in re.finditer(r'constexpr uintptr_t (\w+_OFFSET) = (0x[0-9a-fA-F]+);', open(os.path.join(UP, f), encoding='utf8', errors='replace').read()):
            ce_offsets.setdefault(f, {})[m.group(1)] = m.group(2).lower()

# ------------------------------------------------------------------ symbol map
by_new = {}
by_old = {}
for l in open(P('old_to_new_offsets.tsv'), encoding='utf8'):
    if l[:1] == '#' or l.startswith('old_rva'):
        continue
    p = l.rstrip('\n').split('\t')
    if len(p) >= 5:
        by_old[p[0]] = p
        if p[1] and ',' not in p[1] and not p[1].startswith('-'):
            by_new.setdefault(p[1], p)


def native_id_for(name):
    n = re.sub(r'\(.*', '', name)
    n = n[len('GameCore::'):] if n.startswith('GameCore::') else n
    return 'native:' + n


# ------------------------------------------------------------------ Linux signatures
linux = collections.defaultdict(list)
for i, l in enumerate(open(P('linux_depot', 'out', 'functions.tsv'), encoding='utf8')):
    if i == 0:
        continue
    p = l.rstrip('\n').split('\t')
    if len(p) >= 7 and p[3]:
        linux[p[3]].append({'ret': p[5].replace('GameCore::', ''), 'params': [x.strip().replace('GameCore::', '') for x in p[4].split(';') if x.strip()], 'header': p[6]})


# ------------------------------------------------------------------ CE methods from the wiki
def parse_wiki(path, forced_object=None):
    recs = []
    obj = forced_object
    static = True
    cur = None
    mode = None
    page = os.path.basename(path)[:-3]
    for line in open(path, encoding='utf8'):
        line = line.rstrip('\n')
        m = re.match(r'^# (.+)$', line)
        if m and not forced_object:
            obj = m.group(1).strip()
            continue
        if re.match(r'^## Static Members', line) or re.match(r'^## (Global|Processors)', line):
            static = True
            continue
        if re.match(r'^## Instanced Members', line):
            static = False
            continue
        m = re.match(r'^### (\w+)(?: _#(\d)_)?\s*$', line)
        if m and obj and obj not in ('Events & Processors',) or (m and forced_object):
            if m and m.group(1) in ('RegisterProcessor', 'Mem', 'ObjMem', 'RegisterCallEvent') or (m and not forced_object):
                cur = {'object': forced_object or obj, 'method': m.group(1), 'static': static, 'params': [], 'returns': [], 'wiki_page': page,
                       'anchor': m.group(1).lower()}
                recs.append(cur)
                mode = None
                continue
        if cur is None:
            continue
        if line.startswith('#### Parameters') or line.startswith('#### Parameter'):
            mode = 'params'
            continue
        if line.startswith('#### Returns') or line.startswith('#### Return'):
            mode = 'returns'
            continue
        if line.startswith('#### '):
            mode = None
            continue
        if line.startswith('|') and mode and not re.match(r'^\|\s*-', line):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 2 and cells[0].lower() not in ('parameter', 'parameters', 'return'):
                t = cells[1].strip('`').replace('\\|', '|')
                (cur['params'] if mode == 'params' else cur['returns']).append({'name': cells[0], 'type': t})
    return recs


wiki_recs = []
wiki_recs += parse_wiki(os.path.join(WIKI, 'Singletons-&-Namespaces.md'))
wiki_recs += parse_wiki(os.path.join(WIKI, 'Objects.md'))
wiki_recs += parse_wiki(os.path.join(WIKI, 'Memory-Manipulation.md'), 'Globals')
wiki_recs += parse_wiki(os.path.join(WIKI, 'Events-&-Processors.md'), 'Globals')
wiki_recs = [r for r in wiki_recs if r['object'] and r['method']]

ce = {}
for r in wiki_recs:
    cid = 'ce:%s.%s' % (r['object'], r['method'])
    rec = ce.setdefault(cid, {'id': cid, 'object': r['object'], 'method': r['method'], 'static': r['static'], 'signatures': [],
                              'wiki': {'page': r['wiki_page'], 'anchor': r['anchor']}})
    rec['signatures'].append({'params': r['params'], 'returns': [x['type'] for x in r['returns']]})

# offsets: try the constant named after the method; overloads use _2 etc.
ce_to_native = {}
for cid, rec in ce.items():
    base = snake(rec['method'])
    cands = [base + '_OFFSET'] + [base + '_%d_OFFSET' % i for i in (1, 2, 3)]
    hdrs = ce_offsets.get(rec['object'] + '.h', {})
    found = [(c, (hdrs[c], rec['object'] + '.h')) for c in cands if c in hdrs]
    rec['builds'] = {'current': {'rva': found[0][1][0] if found else None}}
    rec['native_overloads'] = []
    for c, (rva, hdr) in found:
        if rva in by_new:
            nid = native_id_for(by_new[rva][4])
            rec['native_overloads'].append({'rva': rva, 'native': nid, 'constant': c})
            ce_to_native.setdefault(nid, []).append(cid)
    rec['native'] = rec['native_overloads'][0]['native'] if rec['native_overloads'] else None
    rec['status'] = 'verified'
    rec['evidence'] = [{'kind': 'community-reference', 'note': 'Community Extension wiki page "%s"' % rec['wiki']['page']},
                       {'kind': 'static-analysis', 'note': 'registered in the Community Extension source (PushLuaMethod)'}]
    rec['availability'] = 'ce'
json.dump(sorted(ce.values(), key=lambda x: x['id']), open(os.path.join(OUT, 'ce_methods.json'), 'w', encoding='utf8'), indent=1)
print('ce methods', len(ce), 'with native link', sum(1 for r in ce.values() if r['native']))

# ------------------------------------------------------------------ native functions
natives = {}


def sig_list(cls, fn):
    out = []
    for s in linux.get('GameCore::%s::%s' % (cls, fn), [])[:4]:
        out.append(s)
    return out


def add_native(cls, fn, symbol_rva, current_rva, map_cat, extra):
    nid = 'native:%s::%s' % (cls, fn)
    if nid in natives and natives[nid]['builds']['symbol']['rva'] != symbol_rva:
        nid = nid + '@' + symbol_rva
    rec = natives.setdefault(nid, {'id': nid, 'class': cls, 'function': fn, 'builds': {'symbol': {'rva': symbol_rva}, 'current': {'rva': current_rva or None, 'map': map_cat}},
                                   'signatures': sig_list(cls, fn), 'lua_exposure': {'status': 'none'}, 'availability': 'engine', 'tags': [],
                                   'status': 'unknown', 'evidence': [{'kind': 'static-analysis', 'note': 'function found in the symbol build; address mapped to the current build'}]})
    rec.update({k: v for k, v in extra.items() if v not in (None, '', [])})
    return rec


# gap list candidates
hdr = None
for l in open(P('gap_shortlist.tsv'), encoding='utf8'):
    if l[:1] == '#':
        continue
    p = l.rstrip('\n').split('\t')
    if hdr is None:
        hdr = p
        continue
    r = dict(zip(hdr, p))
    cls, fn = r['class'], r['function']
    tags = [k for k in ('edit_call', 'signal', 'notification', 'event', 'writes') if r.get(k)]
    rec = add_native(cls, fn, r['old_rva'], r['new_rva'], r['map_category'],
                     {'size': int(r['size']) if r['size'].isdigit() else None, 'callers': int(r['callers']) if r['callers'].isdigit() else None,
                      'category': r['category'], 'tags': tags})
    rec['lua_exposure'] = {'status': 'none'}
    w = r.get('wrappers_reaching', '')
    if w:
        rec['lua_exposure'] = {'status': 'indirect', 'via': [x.strip() for x in w.split(';') if x.strip()][:6]}

# analysed functions (our own notes)
FN = P('findings', 'functions')
for f in sorted(os.listdir(FN)):
    if not f.endswith('.md'):
        continue
    t = open(os.path.join(FN, f), encoding='utf8').read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', t, re.S)
    fm = {}
    for line in m.group(1).split('\n'):
        k, _, v = line.partition(':')
        fm[k.strip()] = v.strip().strip('"')
    body = m.group(2)
    full = fm['function'].replace('GameCore::', '')
    cls, _, fn = full.rpartition('::')
    rec = add_native(cls, fn, fm['rva_symbol_build'], fm['rva_installed_build'], fm['address_mapping'].split()[0].rstrip(':;('), {})
    # description = first paragraph after the signature line
    paras = [x.strip() for x in body.split('\n\n') if x.strip()]
    desc = ''
    for x in paras[1:4]:
        if not x.startswith(('`', '#', '-')):
            desc = x.replace('\n', ' ')
            break
    notes = []
    for sec, status in (('Verified from the decompilation', 'verified'), ('Inferred (not confirmed in-game)', 'inferred'), ('For modders', 'inferred')):
        sm = re.search(r'## %s\n(.*?)(?=\n## |\Z)' % re.escape(sec), body, re.S)
        if sm:
            for b in re.findall(r'^- (.+)$', sm.group(1), re.M):
                notes.append({'text': re.sub(r'\[([^\]]+)\]\([^)]*\.md[^)]*\)', r'', b.strip()), 'status': status if sec != 'For modders' else 'inferred',
                              'evidence': [{'kind': 'static-analysis', 'note': 'decompilation read in Ghidra'}]})
    # in-game observations: sections titled "Observed in-game ..." (bullets) -> verified notes with runtime evidence
    for sm in re.finditer(r'## (Observed in-game[^\n]*)\n(.*?)(?=\n## |\Z)', body, re.S):
        for b in re.findall(r'^- (.+(?:\n  .+)*)', sm.group(2), re.M):
            notes.append({'text': re.sub(r'\s+', ' ', re.sub(r'\[([^\]]+)\]\([^)]*\.md[^)]*\)', r'\1', b.strip())), 'status': 'verified',
                          'evidence': [{'kind': 'runtime', 'note': sm.group(1).strip()}]})
    rec['analysis'] = {'summary': desc, 'notes': notes}
    rec['status'] = 'verified' if any(n['status'] == 'verified' for n in notes) else 'inferred'
    le = fm.get('lua_exposure', '')
    if le:
        rec['lua_exposure'] = {'status': 'indirect' if 'indirect' in le.lower() or 'side effect' in le.lower() or 'runs when' in le.lower() else 'none', 'note': le}
    rec['tags'] = sorted(set(rec.get('tags', [])) | {'analysed'})

# CE-wrapped natives
for nid, cids in ce_to_native.items():
    if nid not in natives:
        # find the map row again
        for rva, row in by_new.items():
            if native_id_for(row[4]) == nid:
                cls, _, fn = nid[7:].rpartition('::')
                add_native(cls, fn, row[0], row[1], row[2], {})
                break
    if nid in natives:
        natives[nid]['lua_exposure'] = {'status': 'ce', 'via': cids}
        natives[nid]['ce_methods'] = cids

out = sorted(natives.values(), key=lambda x: x['id'])
json.dump(out, open(os.path.join(OUT, 'native.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print('native functions', len(out), 'analysed', sum(1 for n in out if 'analysis' in n), 'ce-wrapped', sum(1 for n in out if n['lua_exposure']['status'] == 'ce'),
      'with linux signature', sum(1 for n in out if n['signatures']))
