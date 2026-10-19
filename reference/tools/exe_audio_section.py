"""Page exe/audio.md: the audio vocabulary of the exe. Called from build.py: exe_audio_section.make(add, entries)
Data: data/exe_audio.json (tools/extract_exe_audio.py)."""
import collections, re

NOTES = {
    'Civ6Audio::RegisterOptions': 'The audio options (`SoundOpts.txt`): one volume per Wwise bus, registered here.',
    'AppLuaOptionsLibrary::lSetAudioOption': '`Options.SetAudioOption` accepts these bus names.',
    'Civ6Audio::PublishSettingsTelemetry': 'Names of the audio settings reported in the telemetry options event.',
    'Audio::ReadSoundBankXML': 'Element names of a sound bank description file (`SoundBanks`, `SoundBank`, `IncludedEvents`, `Event`).',
    'Audio::ReadSoundBankINI': 'Section names of `Banks.ini`: `Global` banks are loaded always, `InGame` banks while a game runs.',
    'StrategicAudio::StartupStrategyGame': 'Names the strategic audio system registers at game start: unit, city and district sounds (`_2D` suffix: sounds without a world position).',
    'AmbientAudio::Startup': 'Music playlists, music state names and the era and view state groups of the ambient audio system.',
    'AudioMiner::RecalculateTerrainVisibility': 'Ambience categories the audio miner derives from what is visible on the map (terrain, features, improvements).',
    'AmbientAudio::StartupStrategyGame': 'Per-civilization music override and playlist randomisation used when a game starts.'}


def esc(v):
    return str(v).replace('|', '\\|').replace('\n', ' ')


def safe(s):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', s).lower()


def make(add, entries):
    by = collections.OrderedDict()
    for e in entries:
        by.setdefault(e['function'], []).append(e)
    L = ['# Audio vocabulary\n',
         'The names the engine executable passes to its audio system (Wwise): sound events, state and switch values, volume parameters, music playlists and the files that list sound banks. '
         'They are string literals referenced by the audio functions (%d names in %d functions). Where a name is an event, a bank loaded by a mod needs an event with the same name for the game to play it; this page lists what the exe asks for, '
         'not what the game\'s own banks contain. **Verified**: the name and the function. **Inferred**: the explanations, from the function names.\n' % (len(entries), len(by)),
         'See also the [volume options](options.md) and [`UI.PlaySound`](../exeapi/UI.md), which takes an event name directly from Lua.\n',
         '## Functions\n', '| Function | Names | Meaning (inferred) |', '|---|---|---|']
    for fn, es in sorted(by.items(), key=lambda kv: -len(kv[1])):
        L.append('| [%s](#%s) | %d | %s |' % (esc(fn), safe(fn), len(es), esc(NOTES.get(fn, ''))))
    for fn, es in sorted(by.items(), key=lambda kv: -len(kv[1])):
        L.append('\n## <a id="%s"></a>%s\n' % (safe(fn), fn))
        if NOTES.get(fn):
            L.append(NOTES[fn] + '\n')
        L.append('<details%s markdown="1"><summary>%d names</summary>\n' % (' open' if len(es) <= 12 else '', len(es)))
        L.append('| Name | Kind |')
        L.append('|---|---|')
        for e in es:
            L.append('| <a id="%s"></a>`%s` | %s |' % (safe(fn + '-' + e['name']), esc(e['name']), esc(e['style'])))
        L.append('\n</details>\n')
    add('exe/audio.md', 'Audio vocabulary', '\n'.join(L) + '\n')
