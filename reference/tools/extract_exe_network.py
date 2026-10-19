"""Multiplayer, lobby and Firaxis Live vocabulary of the exe: lobby metadata keys (with the integer/string kind read from the decompiled writers and readers), the fields of the Lua game list entry,
platform lobby keys (Epic Online Services, Steam, Firaxis cloud), connection close reasons, lobby member status codes, Firaxis Live notifications and operations, session fields.
Input : linux_depot/out/strmaps.pkl (strings with referencing functions), findings/data/exe_function_index.json, linux_depot/out/exetrace/network_decomp.txt (DecompList.java on ghi-exe, RVAs in network_rvas.txt),
        the game's Lua files (only counts are kept)
Output: data/exe_network.json (entities exenet:<group>:<name>).
Deliberately skipped: the functions that create the Epic platform and start the Firaxis Live client contain embedded service identifiers; they are not read here and nothing from them is kept."""
import collections, json, os, pickle, re

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Sid Meier's Civilization VI"
ws, ls, wm, lm = pickle.load(open(os.path.join(ROOT, 'linux_depot', 'out', 'strmaps.pkl'), 'rb'))
names, rva_of = {}, {}
for r in json.load(open(os.path.join(ROOT, 'findings', 'data', 'exe_function_index.json'), encoding='utf8'))['rows']:
    for v in (r[2] or '').split(','):
        if v and r[3] in ('high', 'medium'):
            n = re.sub(r'\(.*$', '', r[0])
            names.setdefault(int(v, 16), n)
            rva_of.setdefault(n, '0x' + v)
SKIP_FUNCTIONS = ('App::EOS::CreatePlatform', 'AppFiraxisLiveClient::Startup')   # embedded service identifiers

# decompiled functions: key literal -> accessor slot on the lobby metadata interface
text = open(os.path.join(ROOT, 'linux_depot', 'out', 'exetrace', 'network_decomp.txt'), encoding='utf8').read().replace('\r', '')
chunks = {}
for c in re.split(r'\n?@@@ ', text)[1:]:
    chunks[c.split('\t')[0].lower()] = c
KEY = re.compile(r'FUN_1404ee550\([^,]+,"([A-Za-z_][A-Za-z0-9_]*)",(?:0x[0-9a-f]+|\d+)\)')
SLOT = {'0x148': ('read', 'integer'), '0x150': ('read', 'string'), '0x178': ('write', 'integer'), '0x188': ('write', 'string')}


def accessors(rva):
    c = chunks.get(rva.lower())
    out = {}
    if not c:
        return out
    ks = [(m.start(), m.group(1)) for m in KEY.finditer(c)]
    for i, (pos, k) in enumerate(ks):
        seg = c[pos:ks[i + 1][0] if i + 1 < len(ks) else len(c)]
        for m in re.finditer(r'\+ (0x[0-9a-f]+)\)\)', seg):
            if m.group(1) in SLOT:
                out[k] = SLOT[m.group(1)]
                break
    return out


meta = collections.OrderedDict()          # key -> {'kind', 'written_by': [], 'read_by': []}
for fn, rva in (('Network::Manager::UpdateLobbyGameSettingsMetaData', '0x294ea0'), ('Network::Manager::UpdateLobbyMapMetaData', '0x2956e0'), ('Network::Manager::UpdateLobbyModMetaData', '0x295bb0'),
                ('Network::LuaMatchmakingLibrary::AddLobbyToTable', '0x266980')):
    for k, (way, kind) in accessors(rva).items():
        m = meta.setdefault(k, {'kind': kind, 'written_by': [], 'read_by': []})
        m['written_by' if way == 'write' else 'read_by'].append((fn, rva))
# fields of the Lua entry that are not metadata keys
lua_extra = re.findall(r'hksi_lua_setfield\(param_1,-2,"([A-Za-z_]\w*)"\)', chunks['0x266980'])
lua_fields = list(dict.fromkeys(lua_extra))

# how often the game's Lua reads the entry fields (only in scripts that use the matchmaking table)
files_used = 0
uses = collections.Counter()
for dp, dn, fn in os.walk(GAME):
    for f in fn:
        if f.lower().endswith('.lua'):
            try:
                s = open(os.path.join(dp, f), encoding='utf8', errors='replace').read()
            except Exception:
                continue
            if 'Matchmaking' in s or 'GameListEntry' in s or 'GetGameListEntry' in s:
                files_used += 1
                for k in lua_fields:
                    uses[k] += len(re.findall(r'[.\[]\s*["\']?%s\b' % re.escape(k), s))

ID = re.compile(r'^[A-Za-z_][A-Za-z0-9_:.\-/+= %]{1,60}$')
strings_by_fn = collections.defaultdict(set)
for a, s in ws.items():
    s = s.decode('latin1') if isinstance(s, bytes) else s
    if ID.match(s) and not s.startswith('TXT_KEY'):
        for f in wm.get(a, ()):
            n = names.get(f, '')
            if n and n not in SKIP_FUNCTIONS:
                strings_by_fn[n].add(s)

ents = []


def add(group, name, **kw):
    e = {'id': 'exenet:%s:%s' % (group, name), 'group': group, 'name': name, 'availability': 'exe', 'status': kw.pop('status', 'verified')}
    e.update(kw)
    e.setdefault('evidence', [{'kind': 'exe-string', 'note': 'string literal referenced by %s' % kw.get('function', '')}])
    ents.append(e)


LUA_KIND = {'serverName': ('string', 'lobby name'), 'numPlayers': ('number', 'current player count, from the lobby interface'), 'maxPlayers': ('number', 'maximum players, from the lobby interface'),
            'Players': ('string', 'list of the lobby members, read from the metadata key Members'), 'serverID': ('number', 'index of the entry in the lobby list (the argument of the call)')}
for k in lua_fields:
    m = meta.get(k)
    add('lua-entry', k, lua_kind=(m['kind'] if m else LUA_KIND[k][0]), source=('metadata key ' + k if m else LUA_KIND[k][1]), function='Network::LuaMatchmakingLibrary::AddLobbyToTable', function_rva='0x266980', script_uses=uses[k],
        kind=(m['kind'] if m else LUA_KIND[k][0]), lobby_metadata=bool(m),
        evidence=[{'kind': 'exe-disassembly', 'note': 'field set on the game list entry table by AddLobbyToTable (decompiled)'}])
for k, m in meta.items():
    add('lobby-metadata', k, function='Network::Manager::UpdateLobby*MetaData', function_rva=m['written_by'][0][1] if m['written_by'] else '', kind=m['kind'],
        written_by=['%s (%s)' % x for x in m['written_by']], read_by=['%s (%s)' % x for x in m['read_by']], in_lua_entry=k in lua_fields,
        evidence=[{'kind': 'exe-disassembly', 'note': 'key written through the lobby metadata interface (set integer / set string slot) and read by AddLobbyToTable (get integer / get string slot), decompiled'}])


def take(fn_pat, group, filt=None, **kw):
    found = collections.OrderedDict()
    for fn, ss in sorted(strings_by_fn.items()):
        if re.search(fn_pat, fn):
            for s in sorted(ss):
                if filt is None or filt(s):
                    found.setdefault(s, []).append(fn)
    for s, fns in found.items():
        add(group, s, function=fns[0], function_rva=rva_of.get(fns[0], ''), functions=['%s (%s)' % (f, rva_of.get(f, '?')) for f in fns], **kw)


take(r'^Network::EOS::NetAccessENet::EventHandler::OnConnectionDropped$', 'connection-close-reason', lambda s: s.startswith('CCR_'))
take(r'^Network::EOS::Lobby::EventHandler::OnLobbyMemberStatusReceived$', 'lobby-member-status', lambda s: s.startswith('LMS_'))
take(r'^(Network::EOS::Lobby::EventHandler::(OnLobbyCreated|RequestLobbies|CreateLobbyFromLobbyDetails|SetLobbyPrivacy|SetLobbyData)|FNetLobbyEOS::StartGame|FNetLobbySteam::(OnLobbyEntered|OnLobbyMatchListCallback|RequestLobbies|GetServerCustomString|RegisterServerStringKey))$',
     'platform-lobby-key', lambda s: (s.startswith('_') and s.endswith('_')) or s in ('FXS:879689344', 'CHUNKED_DATA', 'LobbyZone', 'PACK_DATA'))
take(r'^(NetLobbyCloud::(BroadcastGame|RefreshAppServerMetaData|SetCurrentGameName|SetPrivateGame)|Network::Manager::SetCloudJoinsBlocked|GameCore::Serializer::FiraxisCloud::(Write|OnFiraxisLiveKeyDataError|OnFiraxisLiveKeyDataResult))$',
     'cloud-key', lambda s: s in ('MatchName', 'MaxPlayers', 'Metadata', 'PrivateGame', 'JoinsBlocked', '_META', 'C6GAME'))
take(r'^FiraxisLiveClient::CreateFiraxisLive$', 'firaxislive-session-field', lambda s: re.match(r'^[A-Za-z0-9]+$', s) is not None and not s.startswith('Creating'))
take(r'^FiraxisLiveClient::On', 'firaxislive-event', lambda s: s.startswith('FiraxisLive_On'))
take(r'^AppFiraxisLiveClient::(DoDataPushNotify|OnOnlineConfigUpdated|HandleConfigurationUpdates)$', 'firaxislive-config', lambda s: s.startswith('App/') or s.startswith('Send'))
ops = collections.OrderedDict()
for fn, ss in strings_by_fn.items():
    if fn.startswith('FiraxisLiveClient::'):
        for s in ss:
            m = re.match(r'^([A-Za-z0-9]+) failed\\n$', s.replace('\n', '\\n'))
            if m:
                ops[m.group(1)] = fn
for o, fn in sorted(ops.items()):
    add('firaxislive-operation', o, function=fn, function_rva=rva_of.get(fn, ''), evidence=[{'kind': 'exe-string', 'note': 'failure message "%s failed" in %s' % (o, fn)}])
json.dump(ents, open(os.path.join(BASE, 'data', 'exe_network.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(len(ents), 'entries', dict(collections.Counter(e['group'] for e in ents)), 'scripts using matchmaking:', files_used)
print(lua_fields)
