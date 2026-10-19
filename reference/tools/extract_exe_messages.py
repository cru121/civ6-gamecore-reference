"""Log and error messages of the engine exe, for the subsystems modders meet (mods, database, text, Lua, UI, assets, game core bridge, application, network).
Input : linux_depot/out/strmaps.pkl (ASCII strings with referencing functions), findings/data/exe_function_index.json (function names)
Output: data/exe_messages.json (entities exemsg:<n>).  Library code (OpenSSL, curl, zlib, the shader language) is excluded; strings whose function is not named are not attributed."""
import collections, json, os, pickle, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
O = os.path.join(ROOT, 'linux_depot', 'out')
ws, ls, wm, lm = pickle.load(open(os.path.join(O, 'strmaps.pkl'), 'rb'))
names = {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            names.setdefault(int(v, 16), re.sub(r'\(.*$', '', r[0]))

SUBSYSTEMS = [   # (label, regex on function name, likely log)
    ('Modding', r'^(Modding|AppModdingFramework|AppLuaModdingLibrary|ModdingComponent|ModdingSetting|Modding\w+)', 'Modding.log'),
    ('Database', r'^(Database::|Application::Data::(Gameplay|Configuration|Database)|AppLuaDBLibrary|Application::Data::DatabaseLogger)', 'Database.log'),
    ('Localization', r'^(Application::Data::Localization|LocalizationLogger|AppLuaLocaleLibrary)', 'Localization.log'),
    ('Lua libraries', r'^(AppLua|Lua::|LuaGameCoreLibrary|GameCore::Lua|App::Lua)', 'Lua.log'),
    ('UI (ForgeUI)', r'^(ForgeUI|AppUI|CivTech::Input)', 'UserInterface.log'),
    ('Assets and art definitions', r'^(AssetObjects|ArtDefProvider|AssetCloud|DatabaseIconProvider|Assets::)', 'ArtDef.log'),
    ('World view (3D map)', r'^(WorldView|Simulation::|OverlaySystem|VisualEffectSystem)', None),
    ('GameCore bridge', r'^(GameCore::|GameCoreController|GameViewState)', None),
    ('Application and startup', r'^(Civ6App|AppHost|App::|IntroState|MainMenuState|LoadGameViewState|BenchmarkSystem|Civ6Audio|Application::)', None),
    ('Network and multiplayer', r'^(Network::|FNet|NetLobby|MatchMaking|NetSession)', None),
    ('Firaxis Live', r'^(FiraxisLive|AppFiraxisLive|App::FiraxisLive)', 'FiraxisLive.log')]
EXCLUDE = r'^(FSL|CISL|FireFX|ASLCPP|X509|CPreprocessor|CRYPTO|SSL|OPENSSL|FGameSync|Curl|curl|zlib|inflate|deflate)'
sentence = re.compile(r"^[A-Za-z\"'\[<(%]")
ents = []
seen = set()
for a, s in sorted(ws.items()):
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if not (12 <= len(s) < 300 and len(s.split()) >= 3 and sentence.match(s) and not s.startswith('<?xml')):
        continue
    if re.search(r'\b(SELECT|INSERT INTO|UPDATE|DELETE FROM|CREATE TABLE|PRAGMA)\b', s, re.I) or re.search(r'^\s*(-- |   )', s):
        continue
    if s in seen:
        continue
    fs = sorted(wm.get(a, ()))
    fn = next((names[f] for f in fs if f in names), None)
    if not fn or re.match(EXCLUDE, fn):
        continue
    sub = next(((lab, log) for lab, rx, log in SUBSYSTEMS if re.match(rx, fn)), None)
    if not sub:
        continue
    seen.add(s)
    ents.append({'id': 'exemsg:%04d' % (len(ents) + 1), 'text': s.strip(), 'subsystem': sub[0], 'likely_log': sub[1],
                 'format_args': re.findall(r'%[-+ #0]*\d*(?:\.\d+)?(?:ll|l|h|I64)?[diuxXfsc]', s),
                 'functions': [{'name': names.get(f), 'rva': '0x%x' % f} for f in fs if f in names][:3], 'function_count': len(fs),
                 'availability': 'exe', 'status': 'verified',
                 'evidence': [{'kind': 'exe-string', 'note': 'string literal referenced by %s' % fn}]})
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_messages.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'messages;', collections.Counter(e['subsystem'] for e in ents).most_common())
