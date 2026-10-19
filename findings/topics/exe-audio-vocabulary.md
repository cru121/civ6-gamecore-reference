# Audio vocabulary of the engine exe

Method: identifier string literals referenced by named audio functions (`StrategicAudio`, `AmbientAudio`, `AudioMiner`, `Civ6Audio`, `Audio::ReadSoundBank*`, `AppLuaOptionsLibrary::lSetAudioOption`): 209 names in 39 functions (`docs_proto/tools/extract_exe_audio.py`).
Reference page: `docs_proto/docs/exe/audio.md`. **Verified**: names and the function that uses them. **Inferred**: what they mean (from function names); the page lists what the exe asks Wwise for, not what the game's own banks contain.
- Volume buses (`Civ6Audio::RegisterOptions`, `Options.SetAudioOption`): `AMBIENCE_BUS_VOLUME`, `GAMEMASTER_BUS_VOLUME`, `MASTER_MUSIC_BUS_VOLUME`, `MASTER_SFX_BUS_VOLUME`, `MASTER_SPEECH_BUS_VOLUME` (these are the keys of `SoundOpts.txt`).
- Sound bank files: `Banks.ini` sections `Global` and `InGame` (`Audio::ReadSoundBankINI`), and the sound bank XML elements `SoundBanks`, `SoundBank`, `IncludedEvents`, `Event` (`ReadSoundBankXML`).
- `StrategicAudio::StartupStrategyGame` registers 63 names (unit, city, district and builder sounds, `_2D` variants) and `OnUnitCommandStarted` 22 great-person command sounds (Anansi, Arthur, Hercules, Maui, ...).
- `AmbientAudio::Startup`: music playlists (`Game_Music_Playlist`, `Game_Start_Music`, `End_Music_Snippet`), era names (ANCIENT_ERA, ...), `GAME_LOCATION`, `GAME_VIEWS`; `AmbientAudio::StartupStrategyGame` reads `CivilizationAudioTags.MusicOverride` and `PLAYLIST_RANDOMIZE_ALL_ERAS`.
- `AudioMiner::RecalculateTerrainVisibility`: ambience categories derived from the map (Coast, Desert, FishingBoat, GoodyHut, BarbarianCamp, ...), with `AmbPlay` / `AmbStop`.
- Related notes: the Wwise music modding memory note (`civ6-wwise-music-modding`), `exe-app-options.md`, `exe-lua-tables.md` (`UI.PlaySound` takes an event name).
