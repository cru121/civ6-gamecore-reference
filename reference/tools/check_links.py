"""Check that every relative markdown link in docs/ points at an existing page (and anchor, for <a id> / headings)."""
import os, re, sys

base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs'))
pages = {}
for root, _, files in os.walk(base):
    for f in files:
        if f.endswith('.md'):
            pages[os.path.relpath(os.path.join(root, f), base).replace('\\', '/')] = open(os.path.join(root, f), encoding='utf8').read()

link = re.compile(r'\]\(([^)\s]+)\)')
bad = []
n = 0
for p, text in pages.items():
    anchors_cache = {}
    for m in link.finditer(text):
        href = m.group(1)
        if href.startswith(('http://', 'https://', 'mailto:')):
            continue
        n += 1
        target, _, anchor = href.partition('#')
        tp = os.path.normpath(os.path.join(os.path.dirname(p), target)).replace('\\', '/') if target else p
        if tp not in pages:
            bad.append((p, href, 'missing page'))
            continue
        if anchor:
            t = pages[tp]
            ids = set(a.lower() for a in re.findall(r'<a id="([^"]+)"', t)) | set(a.lower() for a in re.findall(r'{#([A-Za-z0-9_-]+)}', t))
            heads = set(re.sub(r'[^a-z0-9_ -]', '', h.lower()).strip().replace(' ', '-') for h in re.findall(r'^#+ (.+)$', t, re.M))
            if anchor.lower() not in ids and anchor.lower() not in heads:
                bad.append((p, href, 'missing anchor'))
print('checked %d relative links, %d problems' % (n, len(bad)))
for b in bad[:20]:
    print('  ', b)
sys.exit(1 if bad else 0)
