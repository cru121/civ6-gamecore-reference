"""Page exe/devtools.md: FireTuner commands, asset hot loading, automation, bug report header, exception names. Called from build.py: exe_devtools_section.make(add, entries)
Data: data/exe_devtools.json (tools/extract_exe_devtools.py)."""
import re


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries):
    by = {}
    for e in entries:
        by.setdefault(e['kind'], []).append(e)
    L = ['# Developer tools and crash reports\n',
         'The exe contains the remote tools Firaxis used to develop the game and the code that writes crash reports. They are off in a normal game; the tuner needs the `EnableTuner` option of the [Debug section](options.md). '
         'This page lists the **command words** the tuner listeners accept, the asset hot-load commands, the automation hooks, the elements of the bug submission header and the exception names the crash handler prints. '
         '**Verified**: the command words (read from the exe), the dispatch order, handler addresses and strings. **Inferred**: what each command does (from the handler names and reply strings). Nothing here was tried against a running tuner.\n',
         '## FireTuner (AppTuner2) commands\n',
         'The listener `Tuner::AppTuner2::Listener::ProcessInput` (`0x4f5bf0`) receives text messages with an 8-byte header followed by `COMMAND:arguments`. The **application commands** are compared first. '
         'Any other message is read as `<state index>:COMMAND:arguments`: the number picks one of the registered Lua states (the main state and threads, `AddLuaState`) and the command is one of the **Lua state commands**. '
         '`HOTLOAD` takes a kind as its first argument (`ARTDEF`, `UI`, anything else is a blueprint reload).\n']
    for scope, title in (('application', 'Application commands'), ('lua-state', 'Lua state commands')):
        es = [e for e in by.get('tuner-command', []) if e['scope'] == scope]
        L.append('\n### %s\n' % title)
        L.append('| Command | Handler | Address | Strings of the handler | Meaning (inferred) |')
        L.append('|---|---|---|---|---|')
        for e in es:
            L.append('| <a id="tuner-command-%s"></a>`%s` | `%s` | %s | %s | %s |' % (safe(e['name']), e['name'], esc(e['handler'].split('::')[-1]), e['handler_rva'], ', '.join('`%s`' % esc(s) for s in e['strings'][:4]) or '—', esc(e['meaning'])))
    L.append('\n## Asset hot loading (AssetCloud)\n')
    L.append('A second listener, `AssetCloud::Listener::ProcessInput` (`0x4ef4f0`), accepts `CLOSE` and `HOTLOAD` and logs to `AssetCloudTuner.log`. The hot loader keeps a queue of `ARTDEF:` and `DEPENDENCY:` entries and a temporary workspace folder that it removes when it closes.\n')
    L.append('| Command | Meaning |')
    L.append('|---|---|')
    for e in by.get('assetcloud-command', []):
        L.append('| <a id="assetcloud-command-%s"></a>`%s` | %s |' % (safe(e['name']), e['name'], esc(e['meaning'])))
    L.append('\n## Automation hooks\n')
    L.append('The automation manager (switches `-autoscript`, `-autoparams`, `-autojson` on the [command line](command-line.md); Lua table [`Automation`](../exeapi/Automation.md)) raises these events and uses these tags in output file names:\n')
    L.append('| Name | Meaning |')
    L.append('|---|---|')
    for e in by.get('automation', []):
        L.append('| <a id="automation-%s"></a>`%s` | %s |' % (safe(e['name']), esc(e['name']), esc(e['meaning'])))
    L.append('\n## Bug submission header\n')
    L.append('`AppHost::BugSubmissionPackager::GenerateHeaderInSubmissionFolder` (`0x705e70`) writes a header document into the submission folder (a folder with the log, the dump and attachments). Elements in the order they are written (the grouping under a parent is inferred from the order of repeated names):\n')
    L.append('| # | Element | Notes |')
    L.append('|---|---|---|')
    for k, e in enumerate(by.get('bug-header', []), 1):
        L.append('| %d | <a id="bug-header-%s"></a>`%s` | %s |' % (k, safe(e['name']), e['name'], esc(e['strings'][0]) if e['strings'] else ''))
    L.append('\nCollection is switched by the `EnableBugCollection` option and the `-NoAssertCollection` switch (see the [options](options.md) and [command line](command-line.md) pages).\n')
    L.append('## Exception names\n')
    L.append('`FDebugHelperNS::GetExceptionDescription` (`0x986d20`) turns a Windows exception code into the text of the crash dialog (`Unhandled Exception / Code: <name>`, `Error reading|writing address 0x...`, followed by `Call Stack`). Code values are the documented Windows constants.\n')
    L.append('| Name | Code |')
    L.append('|---|---|')
    for e in by.get('exception', []):
        L.append('| <a id="exception-%s"></a>`%s` | %s |' % (safe(e['name']), e['name'], e['strings'][0] or '—'))
    add('exe/devtools.md', 'Developer tools and crash reports', '\n'.join(L) + '\n')
