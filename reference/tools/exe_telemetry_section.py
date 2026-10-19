"""Page exe/telemetry.md: the telemetry configuration compiled into the exe. Called from build.py: exe_telemetry_section.make(add, entries, meta)
Data: data/exe_telemetry.json, data/exe_telemetry_meta.json (tools/extract_exe_telemetry.py)."""
import collections, re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries, meta):
    events = [e for e in entries if e['kind'] == 'event']
    counters = [e for e in entries if e['kind'] == 'counter']
    on = [e for e in events if e['enabled']]
    L = ['# Telemetry configuration\n',
         'The engine executable ships with a **default telemetry configuration**: two XML documents embedded in the code that say which events the game can report and which usage counters it keeps. '
         'This page lists them as written. It describes the built-in configuration only: the game can also download a configuration from the Firaxis Live service '
         '(`App/FiraxisLive/OnlineTelemetryConfiguration.xml`, fetched through a service discovery step), which can replace it, so what an individual game reports today may differ. '
         'This analysis did not look for a way to switch reporting off and makes no claim about what is actually sent on a given machine.\n',
         '**Verified:** the event names, flags and counters are literals in the exe. **Not determined:** what the `SendFlags` values 4 and 8 mean, and the data fields of each event.\n',
         '## What the code does with it\n',
         'From the messages in the telemetry code: events are put in queues with a priority, can be rejected by sampling or by priority, are flushed periodically (and on shutdown) to a `/telemetry/v2` service endpoint with retries, '
         'and the configuration entries are fetched with retries as well. The game logs a line such as `Sending Telemetry: OrgEvent=... Type=... SendFlags=...` (function `GameCore::App::Telemetry::Listener::OnTelemetryTag`). '
         'There is one related entry in the option files: `[Misc] TelemetryUploadNecessary` (see [the option files](options.md)).\n',
         '## Events of the default ruleset\n',
         'The default ruleset (flagged `IsBlacklist` in the XML) lists %d events, %d of them enabled. Two derived rulesets, `Elite Player Ruleset` and `New Player Ruleset`, inherit from it and change the update interval of a few events. '
         '`TurnInterval` means the event is repeated every that many turns.\n' % (len(events), len(on)),
         '| Event | Enabled | SendFlags | TurnInterval |', '|---|---|---|---|']
    for e in events:
        L.append('| <a id="%s"></a>`%s` | %s | %s | %s |' % (safe('event-' + e['name']), esc(e['name']), 'yes' if e['enabled'] else 'no', e['send_flags'], e['turn_interval'] or '—'))
    L.append('\n## Counter tables\n')
    L.append('Seven tables of counters are kept during a game and reported as events (`ScreenBreakdown`, `LensBreakdown`, `EnvBreakdown`, `PrjFrequency`, `PowerStats`, `WorldCongress`, `GameLevel`). '
             '`Kind` says what is counted (a UI context, a lens, a terrain state change, a building or district type, or a free-form value), `Type` how (a count, seconds, or a value that is set).\n')
    by = collections.OrderedDict()
    for c in counters:
        by.setdefault(c['table'], []).append(c)
    for t, cs in by.items():
        L.append('\n### %s (%d)\n' % (esc(t), len(cs)))
        L.append('| Counter | Kind | Context | Type | Per session |')
        L.append('|---|---|---|---|---|')
        for c in cs:
            a = c['attributes']
            L.append('| <a id="%s"></a>`%s` | %s | %s | %s | %s |' % (safe('counter-' + c['name']), esc(c['name']), esc(a.get('Kind', '')), esc(a.get('Context', '')), esc(a.get('Type', '')), esc(a.get('Session', ''))))
    add('exe/telemetry.md', 'Telemetry configuration', '\n'.join(L) + '\n')
