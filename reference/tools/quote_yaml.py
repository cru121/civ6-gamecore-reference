"""One-off helper: double-quote plain 'text:' / 'summary:' scalars in curated YAML so that ': ' inside them is safe."""
import glob, re, os

base = os.path.join(os.path.dirname(__file__), '..', 'curated')
for f in glob.glob(os.path.join(base, '**', '*.yaml'), recursive=True):
    out = []
    for l in open(f, encoding='utf8').read().split('\n'):
        m = re.match(r'^(\s*(?:- )?(?:text|summary): )(.+)$', l)
        if m and not m.group(2).startswith(('"', '|', '>')):
            v = m.group(2).replace('\\', '\\\\').replace('"', '\\"')
            l = m.group(1) + '"' + v + '"'
        out.append(l)
    open(f, 'w', encoding='utf8').write('\n'.join(out))
print('ok')
