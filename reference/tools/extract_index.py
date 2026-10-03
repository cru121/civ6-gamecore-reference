"""Generate data/function_index.json: every function of the symbol build (43,803) with its mapping to the current build, a category,
the Linux signature where the name matches, and links to curated entries. Used by the searchable native-function index."""
import collections
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs_proto', 'data')


def P(*a):
    return os.path.join(ROOT, *a)


# Lua wrappers: symbol rva -> "Object.Method" (first registration)
lua_wrap = {}
for l in open(P('lua_registry.tsv'), encoding='utf8'):
    if l[:1] == '#' or l.startswith('interface'):
        continue
    p = l.rstrip('\n').split('\t')
    if len(p) >= 5:
        lua_wrap.setdefault(p[4], p[0].split('::')[-1].lstrip('I') + '.' + p[2])

# curated entries
natives = json.load(open(os.path.join(OUT, 'native.json'), encoding='utf8'))
nat_by_sym = {n['builds']['symbol']['rva']: n for n in natives}
ce = json.load(open(os.path.join(OUT, 'ce_methods.json'), encoding='utf8'))
ce_native = {m['native'] for m in ce if m['native']}

# Linux signatures
linux = {}
for i, l in enumerate(open(P('linux_depot', 'out', 'functions.tsv'), encoding='utf8')):
    if i == 0:
        continue
    p = l.rstrip('\n').split('\t')
    if len(p) >= 7 and p[3] and '<' not in p[3]:
        linux.setdefault(p[3], (p[5], p[4]))

CATS = ['lua-wrapper', 'game-logic', 'ai', 'ui-cache', 'database-definitions', 'effects', 'lua-glue', 'template-instance', 'library', 'compiler-generated']


def categorize(name, rva):
    base = name.split('(')[0]
    if rva in lua_wrap:
        return 'lua-wrapper'
    if '`' in base or 'dynamic_initializer' in base or 'dynamic_atexit' in base or "deleting_destructor" in base:
        return 'compiler-generated'
    if base.startswith(('hks', 'lua', 'rapidxml', 'sqlite', 'std::', 'eastl::', 'rapidjson', 'boost', 'ASL::', 'Concurrency', 'EA::', 'tbb')):
        return 'library'
    if '<' in base:
        return 'template-instance'
    if base.startswith('GameEffects::'):
        return 'effects'
    if base.startswith('GameCore::Definition'):
        return 'database-definitions'
    if base.startswith('GameCore::Cache::'):
        return 'ui-cache'
    if base.startswith('GameCore::AI::'):
        return 'ai'
    if base.startswith('GameCore::Lua::'):
        return 'lua-glue'
    if base.startswith('GameCore::'):
        return 'game-logic'
    return 'library'


rows = []
cnt = collections.Counter()
cnt_map = collections.Counter()
for l in open(P('old_to_new_offsets.tsv'), encoding='utf8'):
    if l[:1] == '#' or l.startswith('old_rva'):
        continue
    p = l.rstrip('\n').split('\t')
    if len(p) < 5:
        continue
    old, new, mcat, size, name = p[:5]
    cur = new if (new and ',' not in new and not new.startswith('-')) else ''
    cat = categorize(name, old)
    cnt[cat] += 1
    cnt_map[cat] += bool(cur)
    base = name.split('(')[0]
    short = base[len('GameCore::'):] if base.startswith('GameCore::') else base
    cls, _, fn = short.rpartition('::')
    sig = ''
    q = 'GameCore::' + short if base.startswith('GameCore::') else base
    if q in linux:
        r, ps = linux[q]
        sig = '%s(%s)' % (r.replace('GameCore::', ''), ps.replace('GameCore::', '').replace('; ', ', '))
    nat = nat_by_sym.get(old)
    rows.append([short, old, cur, int(size) if size.isdigit() else 0, cat, lua_wrap.get(old, ''), mcat, sig,
                 nat['id'] if nat else '', 1 if (nat and nat['id'] in ce_native) else 0])
json.dump({'cats': CATS, 'rows': rows}, open(os.path.join(OUT, 'function_index.json'), 'w', encoding='utf8'), separators=(',', ':'), ensure_ascii=False)
print(len(rows), 'functions')
for c in CATS:
    print('%-22s %6d  mapped %6d (%.0f%%)' % (c, cnt[c], cnt_map[c], 100.0 * cnt_map[c] / max(cnt[c], 1)))
print('total mapped', sum(cnt_map.values()))
print('with linux signature', sum(1 for r in rows if r[7]))
print('size MB', os.path.getsize(os.path.join(OUT, 'function_index.json')) / 1e6)
