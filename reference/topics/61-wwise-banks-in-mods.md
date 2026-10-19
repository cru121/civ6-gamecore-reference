---
title: Shipping your own Wwise soundbank in a mod (how the game loads it, and bnktool)
order: 61
---
# Shipping your own Wwise soundbank in a mod

**Availability: experimental.** Findings from the Windows game (2026-10-16) and tests in the game with a bank built without Wwise. For plain `wav`/`mp3`/`ogg` playback without a bank see the Dev CE Audio API (topic 60).

## How the game finds and loads a mod's bank
* A mod lists its audio files in an `<UpdateAudio>` action of the `.modinfo`: a `...Banks.ini`, the `.bnk` files (the DLCs also list `.txt` and `.xml`; the game does not need them).
* The ini has the sections `[Global]`, `[Menu]`, `[InGame]`, `[2D]`, `[3D]`, `[FMV]`; a leading `!` on a bank name means "load once even if several inis list it". The game opens every mod's ini at start and the `.bnk` files of the section when that section is loaded: `[InGame]` when a game starts.
* `[FMV]` is bank group 5. The game's own scripts load it on demand with `UI.LoadSoundBankGroup(5)` and `UI.UnloadSoundBankGroup(5)` (UI Lua only). A bank listed in `[FMV]` is read from disk at each `LoadSoundBankGroup(5)`, so a rebuilt bank can be tried without restarting the game.
* The event is started with `UI.PlaySound("Event_Name")` (UI state only). Wwise ids are the FNV-1 32-bit hash of the lower-cased name; the event name does not have to be stored in the bank.
* The game has to run with `EnableAudio 1` in `AppOptions.txt` (found in `%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VI`).
* Banks use `SoundbankVersion 113`, the same as the game's own banks.

## What a bank made without Wwise has to look like
Found by comparing with official banks; each point made a silent bank play:
1. The `DATA` payload starts at a file offset that is a multiple of 16. Wwise pads the `BKHD` chunk to get there.
2. The `DIDX` media index is sorted by media id.
3. `HIRC` objects are written children first: sounds, then actor-mixers from the bottom up, then actions, then events. (A parent that is read before its child cannot attach it, and the sound is silently never played.)
4. Sounds hang under real actor-mixers that end in a real bus. Copying the parent chain of an official event works.
5. PCM media is a RIFF/WAVE file with an extensible `fmt ` chunk (as the game's own PCM `.wem`); the sound object keeps the official layout with the codec id 0x00010001.

## The tool
`dev-ce/tools/bnktool.py` (Python, no dependencies) hashes names, dumps banks and builds banks like the above from a wav file and an official bank for the parent chain (`make-sfx`), plus two bisecting aids (`clone-bank`, `extract`). The test mod `DevCE_BankTest` (a soundboard panel) uses it.

## Extending the game's own music tree does not work
The `Civilization`, `Game_Location` and `Leader_Screen_Civilization` switch groups are defined inside the music switch containers of the base `Music_Bank.bnk` (decision tree: root, 4 era nodes, 67 civilization leaves per era, siblings sorted by key hash). `bnktool add-civ` writes a mod bank with a changed copy of such a container (a new civilization leaf, or an existing leaf pointing at other music). Tested in the game: **the base game's object keeps priority**. A bank loaded later (mod bank) that contains an object with the same id is ignored for that object; the game kept playing the original music. So a mod cannot add a civilization to the game's own containers.

What does work: events and objects with new ids in your own bank (see above), for example the per-civilization events the game's engineers describe for civilizations it does not know (`Play_Music_NAME`, `Start_Music_NAME`, `Stop_`/`Pause_`/`Resume_Music_NAME`, `Play_Leader_Music_NAME`, `Stop_Leader_Music_NAME`, with NAME the civilization name from the database). Your own music container can still read the game's global `Game_Location` switch (set from Lua with `UI.SetSoundSwitchValue`), so era-dependent music is possible without touching the base containers. Not built yet.

### Own switch container by era (tested)
A bank with a new-id switch container keyed by the game's global `Game_Location` switch works: `bnktool make-switch` builds one (one sound per era value, own event). In the game, `UI.SetSoundSwitchValue("Game_Location", "Medieval_Era")` followed by `UI.PlaySound("Play_DevCE_EraTest")` played the Medieval sound, and likewise for Ancient, Industrial and Modern (era switch values are the hashes of `Ancient_Era`, `Medieval_Era`, `Industrial_Era`, `Modern_Era`). The switch value is global and persists: playing the event again without setting it repeats the last era. Tested: the game does **not** keep this switch current for scripts: after the player's era advanced (Playground Era +1, turns ended) the event still played the Ancient sound. The game's own diplomacy script sets it explicitly (`UI.SetSoundSwitchValue("Game_Location", UI.GetNormalEraSoundSwitchValue(playerID))`), so a mod keeps its own era container in sync with a small UI script that does the same on era or turn changes before posting its events. A gotcha: a switch container copied from an official bank carried a volume of -96 dB; set the container's volume property to 0.

Driving the game's leader music from Lua works: `UI.SetSoundSwitchValue("LEADER_SCREEN_CIVILIZATION", "Egypt")`, `UI.SetSoundSwitchValue("Game_Location", "Ancient_Era")`, `UI.PlaySound("Play_Leader_Music")`; `Stop_Leader_Music` ends it and resumes the normal game music.
