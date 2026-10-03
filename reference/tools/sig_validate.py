"""Compare recovered signatures with the parameter counts in the community signature index (validation only; nothing is copied)."""
import json, re, os, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REF = 'C:/stuff/claude/wheat-gpp/civ6-lua-signature-index.md'
sig = json.load(open(os.path.join(ROOT, 'docs_proto', 'data', 'lua_signatures.json'), encoding='utf8'))
reg = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'lua_registry.tsv'), encoding='utf8') if l[0] != '#' and not l.startswith('interface')]
alias = json.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'lua_compare.json')))['alias']
inv = {v[0]: k for k, v in alias.items()}
ours = {}
for r in reg:
    o = re.sub(r'^I(?=[A-Z])', '', r[0].split('::')[-1]); o = inv.get(o, o)
    if r[4] in sig:
        ours.setdefault((o, r[2]), []).append(sig[r[4]])
ref = {}
obj = None
for l in open(REF, encoding='utf8'):
    m = re.match(r'^## (\S+)', l)
    if m: obj = m.group(1); continue
    m = re.match(r'^- `(\w+)([:.])(\w+)\((.*?)\)(?:\s*->\s*(.*?))?\s+\[(\w+)\]`', l)
    if m:
        args = m.group(4).strip()
        depth = 0; n = 0 if not args else 1
        for ch in args:
            depth += ch in '[(<'; depth -= ch in '])>'
            if ch == ',' and depth == 0: n += 1
        ref[(obj, m.group(3))] = (n, m.group(2), m.group(5) or '')
for l in open('C:/stuff/claude/wheat-gpp/civ6-lua-reference.md', encoding='utf8'):
    m = re.match(r'^\*\*`(\w+)([:.])(\w+)\((.*?)\)(?:\s*->\s*(.*?))?\s+\[(\w+)\]`\*\*', l)
    if m:
        args = m.group(4).strip(); depth = 0; n = 0 if not args else 1
        for ch in args:
            depth += ch in '[(<'; depth -= ch in '])>'
            if ch == ',' and depth == 0: n += 1
        ref[(m.group(1), m.group(3))] = (n, m.group(2), m.group(5) or '')
print('reference entries with arguments:', sum(1 for v in ref.values() if v[0] > 0))
c = collections.Counter(); bad = []
for k, (n, sep, rt) in ref.items():
    if k not in ours or n == 0: continue
    for s in ours[k]:
        mine = len(s['params'])
        c['total'] += 1
        c['count_match'] += (mine == n)
        if s['confidence'] == 'high':
            c['high_total'] += 1; c['high_match'] += (mine == n)
            if mine != n and len(bad) < 400: bad.append((k, n, mine, s['wrapper']))
        c['static_match'] += ((sep == '.') == s['static'])
print(dict(c))
json.dump(bad, open(os.path.join(ROOT, 'linux_depot', 'out', 'sig_mismatch.json'), 'w'))
import random; random.seed(2)
for b in random.sample(bad, min(25, len(bad))): print(b)
