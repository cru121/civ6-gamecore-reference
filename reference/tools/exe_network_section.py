"""Page exe/network.md: multiplayer, lobby and Firaxis Live vocabulary. Called from build.py: exe_network_section.make(add, entries)
Data: data/exe_network.json (tools/extract_exe_network.py)."""
import re

MEANING = {
    '_LOBBY_NAME_': 'lobby (room) name', '_LOBBY_PRIVATE_': 'private flag; changed by SetLobbyPrivacy', '_LOBBY_JOIN_CODE_': 'join code players can type to enter a lobby',
    '_LOBBY_MAX_PLAYERS_': 'player limit set when the lobby is created', '_BUCKET_': 'search bucket: lobby searches filter on it', 'FXS:879689344': 'value of the bucket used by the game (matches only lobbies of this game)',
    'CHUNKED_DATA': 'marks lobby data that was split into chunks because one value is limited in size (the exe logs "Meta data too large")', '_GAME_STARTED_': 'set when the host starts the game',
    '_NAME_': 'lobby name key of the Steam lobby', 'LobbyZone': 'Steam lobby search filter', 'PACK_DATA': 'Steam server string key that carries the packed lobby data',
    'MatchName': 'name of the Firaxis cloud match', 'MaxPlayers': 'player limit of the cloud match', 'Metadata': 'match metadata blob (the lobby metadata keys above)', 'PrivateGame': 'private flag of the cloud match',
    'JoinsBlocked': 'cloud match attribute that stops new players from joining', '_META': 'suffix of the cloud key that holds a save file\'s metadata', 'C6GAME': 'key prefix of cloud game data',
    'CCR_ClosedByLocalUser': 'this player closed the connection', 'CCR_ClosedByPeer': 'the other side closed the connection', 'CCR_ConnectionClosed': 'connection closed (no specific reason)',
    'CCR_ConnectionFailed': 'connection could not be established', 'CCR_InvalidData': 'received data failed validation', 'CCR_InvalidMessage': 'received message could not be parsed',
    'CCR_NegotiationFailed': 'handshake failed', 'CCR_TimedOut': 'no data arrived in time', 'CCR_TooManyConnections': 'connection limit reached', 'CCR_UnexpectedError': 'unexpected error', 'CCR_Unknown': 'reason not known',
    'LMS_JOINED': 'a member joined the lobby', 'LMS_LEFT': 'a member left', 'LMS_DISCONNECTED': 'a member dropped', 'LMS_KICKED': 'a member was removed by the host', 'LMS_PROMOTED': 'a member became the host',
    'LMS_CLOSED': 'the lobby was closed',
    'BuildVersion': 'game build reported to the service', 'FiraxisLiveID': 'Firaxis Live account id', 'GamerTag': 'player display name', 'SessionID': 'id of the current session', 'UserID': 'user id',
    'my2KClientID': 'client identifier of the 2K account service', 'my2KLocal': 'local account state of the 2K service', 'my2KSecret': 'name of a credential field (its value is not listed here)',
    'ctpGameDataPath': 'folder of the game data (for the client library)', 'ctpLogPath': 'log folder', 'ctpPermanentPath': 'folder for permanent client data', 'ctpTempPath': 'temporary folder',
    'App/FiraxisLive/Configuration': 'data push topic: online configuration', 'App/FiraxisLive/MarketingMessage': 'data push topic: marketing message for the main menu',
    'App/FiraxisLive/OnlineTelemetryConfiguration.xml': 'online telemetry ruleset document (see the telemetry page)', 'SendAppLogs': 'configuration flag: upload application logs', 'SendAppMinidumps': 'configuration flag: upload crash dumps'}
GROUPS = [
    ('lua-entry', 'Fields of the Lua game list entry', 'The table `Matchmaking.GetGameListEntry` fills for every lobby or cloud game (decompiled `AddLobbyToTable`, `0x266980`). The kind is the Lua type of the value. "Script uses" counts reads of the field in the game\'s own Lua files that use the matchmaking table.'),
    ('lobby-metadata', 'Lobby metadata keys', 'Keys the host writes into the lobby (or cloud match) metadata and clients read back. The kind comes from which accessor slot the code calls on the lobby interface: set/get integer or set/get string (**Verified** from the decompiled code). `GameLaunchReady` is written but not shown in the Lua entry; `Members` is only read.'),
    ('platform-lobby-key', 'Platform lobby keys (Epic Online Services and Steam)', 'Internal attribute names the lobby back ends use. The meaning is **Inferred** from the functions that use the names.'),
    ('cloud-key', 'Firaxis cloud (PlayByCloud) keys', 'Names used for cloud matches and cloud saves. Meaning inferred.'),
    ('connection-close-reason', 'Connection close reasons', 'Names the Epic transport logs when a connection ends (`OnConnectionDropped`). The numeric values are not in the strings.'),
    ('lobby-member-status', 'Lobby member status codes', 'Names logged when the Epic lobby reports a member change (`OnLobbyMemberStatusReceived`).'),
    ('firaxislive-session-field', 'Firaxis Live session fields', 'Field names the client sets when it creates the Firaxis Live client (names only; the values, including any identifiers, are not listed here).'),
    ('firaxislive-config', 'Firaxis Live configuration', 'Data push topics and flags of the online configuration.'),
    ('firaxislive-operation', 'Firaxis Live operations', 'The server calls the client makes, from the "X failed" messages of the client wrapper. These are the cloud-match and account operations behind PlayByCloud and the 2K account link.'),
    ('firaxislive-event', 'Firaxis Live notifications', 'Notification callbacks the client registers (`FiraxisLive_On...`), each handled by one function.')]


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries):
    by = {}
    for e in entries:
        by.setdefault(e['group'], []).append(e)
    L = ['# Multiplayer, lobby and Firaxis Live vocabulary\n',
         'The names the engine executable uses for multiplayer lobbies, connections and the Firaxis Live service (%d names). Most useful for modders: the **Lua game list entry** (what `Matchmaking.GetGameListEntry` returns) and the **lobby metadata keys** behind it, '
         'each with its integer or string type read from the decompiled code. The network Lua functions themselves are on the [`Network`](../exeapi/Network.md) and [`Matchmaking`](../exeapi/Matchmaking.md) pages; the numeric enums (`ServerType`, `KickReason`, `NetworkResult`, ...) are on the [enum tables](lua-enums.md). '
         'Log and error texts are on the [messages](messages.md) page.\n' % len(entries),
         '**Scope and omissions.** Only names and types are listed. The functions that create the Epic platform and start the Firaxis Live client also contain embedded service identifiers; they were deliberately not read for this page and none of those values are reproduced anywhere in this reference. '
         'Nothing here describes what is sent over the network beyond the key names.\n']
    for g, title, intro in GROUPS:
        es = by.get(g, [])
        if not es:
            continue
        L.append('\n## <a id="%s"></a>%s (%d)\n' % (g, title, len(es)))
        L.append(intro + '\n')
        if g == 'lua-entry':
            L.append('| Field | Lua type | Source | Script uses |')
            L.append('|---|---|---|---|')
            for e in es:
                L.append('| <a id="%s"></a>`%s` | %s | %s | %d |' % (safe(g + '-' + e['name']), e['name'], e['kind'], esc(e['source']), e['script_uses']))
        elif g == 'lobby-metadata':
            L.append('| Key | Kind | Written by | Read by | In the Lua entry |')
            L.append('|---|---|---|---|---|')
            for e in es:
                wb = ', '.join('`%s`' % x.split('::')[-1] for x in e['written_by']).replace('MetaData (', ' (') or '—'
                rb = ', '.join('`%s`' % x.split(' (')[0].split('::')[-1] for x in e['read_by']) or '—'
                L.append('| <a id="%s"></a>`%s` | %s | %s | %s | %s |' % (safe(g + '-' + e['name']), e['name'], e['kind'], esc(wb), esc(rb), 'yes' if e['in_lua_entry'] else 'no'))
        elif g in ('firaxislive-event', 'firaxislive-operation'):
            L.append('<details markdown="1"><summary>%d names</summary>\n' % len(es))
            L.append('| Name | Function |')
            L.append('|---|---|')
            for e in es:
                L.append('| <a id="%s"></a>`%s` | `%s` (%s) |' % (safe(g + '-' + e['name']), e['name'], esc(e['function'].split('::')[-1]), e['function_rva'] or '?'))
            L.append('\n</details>\n')
        else:
            L.append('| Name | Meaning (inferred) | Used by |')
            L.append('|---|---|---|')
            for e in es:
                fns = ', '.join('`%s`' % f.split(' (')[0].split('::')[-1] for f in e.get('functions', [e['function']])[:3])
                L.append('| <a id="%s"></a>`%s` | %s | %s |' % (safe(g + '-' + e['name']), esc(e['name']), esc(MEANING.get(e['name'], '')), fns))
    add('exe/network.md', 'Multiplayer and lobby vocabulary', '\n'.join(L) + '\n')
