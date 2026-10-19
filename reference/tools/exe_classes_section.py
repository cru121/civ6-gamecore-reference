"""Pages for the exe's C++ classes (section execlass/). Called from build.py: exe_classes_section.make(add, classes)
Data: data/exe_classes.json (tools/extract_exe_classes.py)."""
import collections, re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s)


def page_for(ns):
    return 'execlass/%s.md' % ('global' if ns == '(global)' else safe(ns))


def make(add, classes):
    by_ns = collections.OrderedDict()
    for c in classes:
        by_ns.setdefault(c['namespace'], []).append(c)
    names = {c['name'] for c in classes}
    n_slots = sum(c['slot_count'] for c in classes)
    n_mapped = sum(c['mapped_slots'] for c in classes)

    L = ['# Engine classes\n',
         'The C++ classes of the engine executable: who inherits from whom, and the **virtual functions** of each class in vtable order. '
         'The information comes from the run-time type information (RTTI) of the **Linux build**, which the Windows build does not carry, so this is the only place the class structure of the Windows executable can be read from; '
         'the two builds are compiled from the same source, so the structure is expected to match. Windows addresses are given for virtual functions that the [function index](../exefn/index.md) could map (high or medium confidence).\n',
         'Standard-library, third-party and platform-shim classes are left out (ICU, OpenSSL, the shader language, the Direct3D compatibility layer). %d classes remain, with %d virtual slots, %d of them mapped to a Windows address.\n' % (len(classes), n_slots, n_mapped),
         'Verified: class names, base classes, vtable contents (read from the Linux file). Inferred: that the Windows build has the same hierarchy and slot order; for `GameCore::EngineUtility` this was confirmed on the Windows vtable (46 slots, same order).\n',
         '[Inheritance trees](hierarchy.md) | [Namespaces](#namespaces)\n', '## <a id="namespaces"></a>Namespaces\n', '| Namespace | Classes | Virtual slots |', '|---|---|---|']
    for ns, cs in sorted(by_ns.items(), key=lambda kv: -len(kv[1])):
        L.append('| [%s](%s) | %d | %d |' % ('(global namespace)' if ns == '(global)' else ns, page_for(ns)[len('execlass/'):], len(cs), sum(c['slot_count'] for c in cs)))
    add('execlass/index.md', 'Engine classes', '\n'.join(L) + '\n')

    for ns, cs in by_ns.items():
        L = ['# %s\n' % ('Global namespace' if ns == '(global)' else ns), '%d classes. A class lists its base chain (first base only for multiple inheritance), its direct subclasses, and its virtual slots.\n' % len(cs),
             '| Class | Base chain | Subclasses | Virtual slots |', '|---|---|---|---|']
        for c in cs:
            chain = ' > '.join('`%s`' % b.split('::')[-1] for b in c['base_chain'][:4]) or '—'
            label = esc(c['name'].split('::', 1)[-1] if ns != '(global)' else c['name'])
            cell = '[`%s`](#c-%s)' % (label, safe(c['name']).lower()) if c['virtual_slots'] else '`%s`' % label
            L.append('| <a id="%s"></a>%s | %s | %d | %d |' % (safe(c['name']).lower(), cell, chain, len(c['derived']), c['slot_count']))
        L.append('\n## Virtual functions by class\n')
        for c in cs:
            if not c['virtual_slots']:
                continue
            L.append('<details markdown="1"><summary><a id="c-%s"></a>%s (%d slots%s)</summary>\n' % (safe(c['name']).lower(), esc(c['name']), c['slot_count'], ', vtable ' + c['vtable_linux_va'] + ' (Linux)' if c['vtable_linux_va'] else ''))
            L.append('| Slot | Function | Windows RVA |')
            L.append('|---|---|---|')
            for s in c['virtual_slots']:
                L.append('| %d | %s | %s |' % (s['slot'], esc('`%s`' % s['name']) if s['name'] else '—', ('`%s` (%s)' % (s['windows_rva'], s['windows_confidence'])) if s['windows_rva'] else '—'))
            L.append('\n</details>\n')
        add(page_for(ns), ns, '\n'.join(L) + '\n')

    # inheritance trees
    roots = [c for c in classes if not any(b in names for b in c['bases'])]
    kids = collections.defaultdict(list)
    for c in classes:
        for b in c['bases']:
            if b in names:
                kids[b].append(c['name'])
    L = ['# Inheritance trees\n', 'Classes with at least one subclass, grouped under their root. `(n)` is the number of virtual slots; a class with several bases appears under each. '
         'The UI toolkit tree (`ForgeUI`) shows which controls share methods: a method registered on a base class is available on its subclasses.\n']
    def tree(n, depth, seen):
        c = next(x for x in classes if x['name'] == n) if False else cmap[n]
        line = '%s- `%s` (%d)' % ('  ' * depth, n, c['slot_count'])
        out = [line]
        if depth < 8:
            for k in sorted(kids.get(n, [])):
                if k not in seen:
                    out += tree(k, depth + 1, seen | {n})
        return out
    cmap = {c['name']: c for c in classes}
    by_root = collections.OrderedDict()
    for r in sorted(roots, key=lambda c: c['name']):
        if kids.get(r['name']):
            by_root.setdefault(r['namespace'], []).append(r['name'])
    for ns, rs in by_root.items():
        L.append('\n## %s\n' % ('Global namespace' if ns == '(global)' else ns))
        for r in rs:
            L += tree(r, 0, set())
    add('execlass/hierarchy.md', 'Inheritance trees', '\n'.join(L) + '\n')
