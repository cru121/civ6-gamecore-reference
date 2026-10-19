---
title: Playing your own sound files from a mod (Dev CE Audio API)
order: 60
---
# Playing your own sound files from a mod (Dev CE Audio API)

**Availability: experimental, needs the Dev CE GameCore mod.** The game plays sound through Wwise, whose banks have to be authored with Wwise tools. Dev CE adds a small
separate audio player so a mod can ship plain `wav`, `mp3`, `flac` or `ogg` files and play them from Lua. It runs on its own audio device (miniaudio, WASAPI) next to the game's
engine; it does not go through Wwise, because the Wwise functions in the Windows executable are not mapped yet.

## Lua API
A global table `Audio`, available in both the gameplay and the UI Lua state:

| Call | Meaning |
|---|---|
| `Audio.Play(path [, volume=1 [, loop=false [, pan=0 [, bus="sfx"]]]])` | Starts a sound and returns an id. Returns `0` on failure; the reason is in `Audio.GetLastError()`. `pan` is -1 (left) to 1 (right). |
| `Audio.Stop(id)`, `Audio.StopAll()` | Stop one sound or all sounds. |
| `Audio.Pause(id)`, `Audio.Resume(id)` | Pause and resume. |
| `Audio.SetVolume(id, v)` | Volume of one sound (0..1). |
| `Audio.SetMasterVolume(v)`, `Audio.GetMasterVolume()` | Volume of everything this API plays, on top of the game's sliders. |
| `Audio.IsPlaying(id)` | `true` while the sound is playing. A finished sound is forgotten. |
| `Audio.GetDuration(path)` | Length in seconds of any sound file, without playing it. Returns `-1` if the file is missing or unreadable (`Audio.GetLastError()` has the reason). |
| `Audio.GetLength(id)`, `Audio.GetPosition(id)` | Length and current play position, in seconds, of a playing or paused sound. `-1` if the id is not known (finished sounds are forgotten). A looping sound's position wraps back to 0. |
| `Audio.FollowGameVolume(bool)` | Default `true`, see below. |
| `Audio.AddSearchPath(dir)` | Extra folder for relative paths. |
| `Audio.GetLastError()` | Text of the last failed `Audio.Play` (cleared by a successful one). |

## Where files are found
An absolute path is used as it is. A relative path is tried against the Dev CE DLL folder and the three folders above it (the Dev CE mod folder and the `Mods` folder), so
`"MyMod/Audio/click.wav"` finds `Mods/MyMod/Audio/click.wav`. If that fails, the same relative path is tried inside every mod folder, so `"Audio/click.wav"` works when the file
is unique. Put the files in the mod's `<Files>` list as for any other mod file.

## Formats
`wav`, `mp3` and `flac` use the miniaudio decoders (files over 2 MB are streamed from disk, smaller ones are decoded once). `ogg` (Vorbis) is streamed through stb_vorbis.
Opus and AAC are not supported.

## Following the game's volume
Buses: `sfx` (default), `music`, `speech`, `ambience`, `none`. While `FollowGameVolume` is on, each bus is scaled by the matching slider of the game's Sound options
(`Master`, `SFX`, `Music`, `Speech`, `Ambience`), and everything is muted while the game window is not in front when the option "mute when out of focus" is on. The values are read from
`%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VI\SoundOpts.txt` (0-100) and re-read when the file changes, so a slider moved in the game applies to a running tune within about
0.3 seconds. `none` and `FollowGameVolume(false)` ignore the sliders.

## The game's own music
Not possible with this API. The game's music and sounds are Wwise `.wem` files (in `Base/Platforms/Windows/Audio`, with numeric names), referenced by events in the `.bnk` banks.
They are Wwise-specific containers (mostly Wwise Vorbis with a stripped header), which miniaudio cannot decode, and the event-to-file mapping lives in the banks. Starting the game's
own events needs the Wwise engine, which this API deliberately does not use. Converting `.wem` files offline (for example with ww2ogg) and shipping the result in your mod works.

## Caveats
* Tested in the game 2026-10-15 (single player, Dev CE test build): wav, mp3 and ogg playback (ogg was still decoded fully into memory in that run; the streaming ogg reader described above came afterwards and is not yet tested in the game), slider changes, a missing file, `StopAll`. Looping and pausing were not part of a logged test.
* The sound is not part of the game's save or its multiplayer sync: every player's game plays what its own scripts ask for.
* The game option `EnableAudio 0` (in `AppOptions.txt`) switches off the game's own audio; this player is not affected by it.
* The audio engine starts on the first `Audio.Play`; it is never shut down while the game runs.
