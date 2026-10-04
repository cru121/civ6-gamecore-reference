#!/usr/bin/env python3
"""Build a strings file for the reference site's "Game text" feature from YOUR copy of Civilization VI.

    python make_strings_file.py "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI" --lang en_US --lang zh_Hans_CN

Writes civ6-strings.json containing only the text of the keys this reference uses (data/strings_keys.json), for the languages you ask for
(default: all found). Load the file on the site ("Load strings file" in the sidebar). The file is for your personal use: it contains game text,
so do not publish or redistribute it. Nothing is sent anywhere. Standard library only.
"""
import argparse, datetime, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROW = re.compile(r'<(?:Row|Replace)\b([^>]*?)>\s*<Text>(.*?)</Text>', re.S)
ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
LANG_DIR = re.compile(r'/text/([a-z]{2}_[A-Za-z_]+)/', re.I)

def decode(s):
    m = re.match(r'^\s*<!\[CDATA\[(.*)\]\]>\s*$', s, re.S)
    return m.group(1) if m else html.unescape(s)

def priority(path):
    p = path.lower().replace('\\', '/')
    if '/expansion2/' in p: return 3
    if '/expansion1/' in p: return 2
    if '/dlc/' in p: return 1
    return 0

def is_text_file(path):
    p = path.replace('\\', '/')
    return p.lower().endswith('.xml') and '/text/' in p.lower() and 'removetext' not in p.lower()

def extract(text, needed, out, path):
    m = LANG_DIR.search(path.replace('\\', '/'))
    default = 'en_US' if re.search(r'<EnglishText[\s>]', text) else (m.group(1) if m else None)
    n = 0
    for r in ROW.finditer(text):
        attrs = dict(ATTR.findall(r.group(1)))
        tag, lang = attrs.get('Tag'), attrs.get('Language') or default
        if tag and lang and tag in needed:
            out.setdefault(lang, {})[tag] = decode(r.group(2))
            n += 1
    return n

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('game', help='Civilization VI folder (the one that contains Base and DLC)')
    ap.add_argument('--lang', action='append', help='language to include, e.g. en_US, zh_Hans_CN (repeatable; default: all found)')
    ap.add_argument('--keys', default=os.path.join(HERE, '..', 'data', 'strings_keys.json'), help='list of text keys to extract')
    ap.add_argument('--out', default='civ6-strings.json')
    a = ap.parse_args()
    needed = {k: True for k in json.load(open(a.keys, encoding='utf-8'))}
    files = []
    for dp, dn, fn in os.walk(a.game):
        for f in fn:
            p = os.path.join(dp, f)
            if is_text_file(p):
                files.append(p)
    if not files:
        sys.exit('No game text files found under %s' % a.game)
    files.sort(key=lambda p: (priority(p), p))
    langs = {}
    for p in files:
        with open(p, encoding='utf-8-sig', errors='replace') as fh:
            extract(fh.read(), needed, langs, p)
    if a.lang:
        missing = [l for l in a.lang if l not in langs]
        if missing:
            sys.exit('Language(s) not found: %s. Found: %s' % (', '.join(missing), ', '.join(sorted(langs))))
        langs = {l: langs[l] for l in a.lang}
    data = {'format': 'civ6-ref-strings', 'version': 1, 'created': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'languages': langs}
    with open(a.out, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, separators=(',', ':'))
    for l in sorted(langs):
        print('%-12s %d of %d keys' % (l, len(langs[l]), len(needed)))
    print('wrote', a.out, '(personal use only, do not redistribute)')

if __name__ == '__main__':
    main()
