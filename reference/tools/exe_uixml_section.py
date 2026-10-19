"""Page exe/uixml.md: the ForgeUI XML vocabulary. Called from build.py: exe_uixml_section.make(add, entries, meta)
Data: data/exe_uixml.json, data/exe_uixml_types.json (tools/extract_exe_uixml.py)."""
import collections, re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries, meta):
    types = meta['types']
    by = collections.OrderedDict()
    for e in entries:
        by.setdefault(e['control_type'], []).append(e)
    n_used = sum(1 for e in entries if e['shipped_uses'])
    L = ['# UI XML vocabulary (ForgeUI)\n',
         'The XML files that define the game\'s user interface are read by the exe\'s UI toolkit, ForgeUI. Each control type has code that reads its attributes and child names; this page lists them straight from that code, '
         'so it shows **every attribute a control type understands**, including ones the game\'s own files never use. The shipped column counts how often the attribute appears on that element in the %d UI XML files that come with the game.\n' % meta['shipped_files'],
         'Of the %d names found in the exe, %d are used in shipped files (the rest are supported but not used by the game, or are child element and style names). '
         'Verified: the name is a literal in the control\'s XML-reading code and the shipped counts. Inferred: the element name of each control type (checked against the tags in the shipped files) and the short explanations.\n' % (len(entries), n_used),
         'Most control types inherit the attributes of `ControlBase` (the `Container` element: `Anchor`, `Size`, `Offset`, `Hidden`, mouse handling, ...); each type section below lists the names its own code reads in addition and marks those that are also in the base list.\n',
         '## Control types\n', '| Control type (C++) | XML element | Element uses in shipped files | Names read |', '|---|---|---|---|']
    for t in types:
        L.append('| [%s](#%s) | %s | %s | %d |' % (t['control_type'], safe(t['control_type']), ('`<%s>`' % t['xml_element']) if t['xml_element'] else 'base class, no element', t['shipped_uses'] or '—', t['attributes']))
    for t in types:
        es = by.get(t['control_type'], [])
        L.append('\n## <a id="%s"></a>%s\n' % (safe(t['control_type']), t['control_type']))
        L.append('XML element: %s (%s).\n' % (('`<%s>`' % t['xml_element']) if t['xml_element'] else 'none, this is a base class of other controls', t['element_basis']))
        open_ = ' open' if t['control_type'] == 'ControlBase' else ''
        L.append('<details%s markdown="1"><summary>%d names</summary>\n' % (open_, len(es)))
        L.append('| Name | Shipped | Also on ControlBase | Note |')
        L.append('|---|---|---|---|')
        for e in sorted(es, key=lambda e: (-e['shipped_uses'], e['name'].lower())):
            L.append('| <a id="%s"></a>`%s` | %s | %s | %s |' % (safe(e['control_type'] + '-' + e['name']), esc(e['name']), e['shipped_uses'] or '—', 'yes' if e['also_on_base'] else '', esc(e['note'] or '')))
        L.append('\n</details>\n')
        if t.get('shipped_only'):
            L.append('Used 10 or more times on this element in shipped files but **not found as a literal** in this type\'s own code (so they are read by shared code, for example `ID` and `Size`, or by a parent type): ' + ', '.join('`%s` (%d)' % (a, n) for a, n in t['shipped_only']) + '.\n')
    add('exe/uixml.md', 'UI XML vocabulary', '\n'.join(L) + '\n')
