# Files, folders and paths the engine exe refers to

Method: `tools/exe/widestr.py` (UTF-16 string literals referenced by code; 403) plus the ASCII string map (`strmaps.pkl`), classified by `docs_proto/tools/extract_exe_files.py` into 251 entries.
Reference page: `docs_proto/docs/exe/files.md` (generated). **Verified**: each entry is a string literal in the exe and a function that references it. Meaning is inferred from the name and the user.
- **45 log names** appear in the exe (writer functions where the function map names them: `Engine.log` in `Civ6App::UpdateFrame`, `Startup.log` in `DoGraphicsDeviceSelection`, `Renderer.log` in `Host::ChangeResolution`,
  `Database.log`, `Localization.log`, `Modding.log`, `Lua.log`, `EOS.log`, `Serialization.log`, `MapSearch.log`, `Clutter.log`, `DataErrors.log`, `net_*_debug.log`, `webhooks.log`, `Achievements*.log` ...). 23 of them exist in a normal `Logs` folder.
  Not named by any string: the GameCore logs (`AI_*.csv`, `Game_*.csv`, `GameCore.log`, `UnitOperations.log`, `AStar_*.log`, `RandCalls.csv`...) and `FiraxisLive.log`, `ForgeUI_BLPTextureLoader.log` (built at run time).
- **Option and data files:** `AppOptions.txt`, `UserOptions.txt`, `GraphicsOptions.txt`, `EOSOptions.txt`, `SoundOpts.txt`, `InputSettings.json`, `UserContext.bin`, `Banks.ini`, `WorldBuilderTemp.db`.
- **Databases:** `Base/Assets/Database/Gameplay.sqlite`, `Configuration.sqlite`, `Modding.sqlite` (+ `Modding.sql`), `Base/Assets/Text/Localization.sqlite` with its three `LocalizationDatabase_*.sql`, user folder `Mods.sqlite`, `HallofFame.sqlite`,
  and debug dumps `Cache/DebugConfiguration.sqlite`, `DebugGameplay.sqlite`, `DebugLocalization.sqlite`.
- **Mod discovery masks:** `*.modinfo` and `*.civ6map` (`ModDiscoveryService::DiscoverMods`), `*.modfragment` (`XmlModLoader::Load`), `*.lua`, `*.sql`, `*.xml`, `*.dep`; map/scenario folders `Base/Assets/Maps`, `Mods`, `Scenarios`, `DLC`, `DLC/WeGame`, `WorldBuilder/Data`.
- **Install layout:** `../../../Base/Assets/{Database,Text,UI,Gameplay/Data,Configuration/Data,HallofFame,...}` plus `Platforms/<platform>/{Assets/UI,Audio,BLPs,Movies}` for Windows, MacOS, Linux, iOS, Switch, Orbis, Durango, Stadia (the engine lists platforms that never shipped).
- **Ownership check:** `App::Ownership::Local::Startup` tests the existence of 80 hash-named files `Base/Assets/Civ6_<hash>.xml`, apparently how the exe tells which content packages are installed.
- Limits: names built at run time (`%s.log`, per-game `Game_%02d_GameCoreProfile.csv` is the one pattern kept) and strings in GameCore are not covered.
