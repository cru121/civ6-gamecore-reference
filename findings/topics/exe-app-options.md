# Option files: every option the engine exe registers

Source: Windows `CivilizationVI.exe` (DX11, Jul 2024), found with `tools/exe/winopts.py` (call sites that load two string literals
before a call: `RegisterOption(this, section, key, default, description)`). Table: `../tables/exe_app_options_windows.tsv`
(194 registrations, plus 29 later reads of the same section/key pairs; `kind` = `register` or `access`).

## Correction (2026-10-19, same day)
An earlier version of this note said 136 of the 194 options were "hidden" because they were not in `AppOptions.txt`. **That was wrong.** The game writes
**four** option files into `%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VI\`, and all 194 registered options are present in them (read only, checked):
| File | Options | Sections |
|---|---|---|
| `AppOptions.txt` | 58 | Language, Video (8), Performance, Debug (22), Misc, UI |
| `UserOptions.txt` | 83 | Gameplay, Interface, Tutorial, Multiplayer, Logging |
| `GraphicsOptions.txt` | 43 | General, Video (12), Terrain, Leaders, Shadows, AO, Bloom, CloudShadows, DynamicLighting, Debug (1: `UIOnlyRendering`) |
| `EOSOptions.txt` | 10 | EOS_Logging, Lobby |
Every key is in exactly one file; descriptions in the files match the exe where the exe scan could read them (183 of 194; the other 11 are options whose
description argument the scan missed, filled from the file's comment line, and 8 EOS options that have "No description"). So the useful content of this
table is the merged list, the type, the command-line override and the file each key lives in, not secret options. The earlier "hidden options" statements in
other notes and in chat were incorrect for the same reason.

## What the table adds over reading the files
- One merged, searchable list with the type (integer vs string), the registration address, and which file holds each key.
- Which options accept the command-line override (`-Key value`, integer options only; see `exe-command-line.md`).
- Descriptions for options whose file comment is "No description".

## Worth knowing (descriptions from the exe)
- `[Debug]` (AppOptions): `EnableDebugMenu`, `EnableTuner` (FireTuner), `EnableWorldBuilder`, `EnableDebugPlotInfo`, `EnableGameCoreEventLog` ("Log all game core events"),
  `EnableTerrainLogging`, `EnableLandmarkLogging`, `EnableAsserts`, `EnableMemoryTracker`, `EnableArbitraryWindowSizing` (debug console `setres`), `SuppressInfoPopups`,
  `PlayNowSave`, `TutorialState`, `EndGameState`, `Remarks`. `UIOnlyRendering` is in GraphicsOptions.
- `[General] AvailableViews` (GraphicsOptions): 0 = strategic only, 1 = 3D only, 2 = both (see `world-view-redraw.md`).
- `[Gameplay]` / `[Interface]` (UserOptions): AI logging levels (`AICityBuildPlotLog`, `AIOperationEvalLog`, `AISettlementEvaluationLog`, `AiDiplomaticActionLog`,
  `AI_MasterLogging`), `AutoSaveFrequency`, `AutoSaveKeepCount` (10), `AutoEndTurn`, `AutoUnitCycle`, camera look-at tuning.
- `[Terrain]` (GraphicsOptions): `TerrainQuality` (0..4), `TerrainSynthesisDetailLevel` (1 full, 2 low), `ReducedTerrainMaterials`, `LowQualityTerrainShader`.
- `[Multiplayer]` (UserOptions): `AutoModDownload`, `TurnWebHookURL` / `TurnWebHookFrequency`, `LANPlayerName`.

## Notes and limits
- A blank `default` column means the default was not a constant the scan could read, most often 0 (set by `xor`) or computed; it is not "none".
- Registration types: 172 int/bool, 12 string, 10 `RegisterOption` integer variants; floating-point options use another register convention and are not in this scan,
  so the list may miss a few (the files contain 194 keys, the same number, so none is evidently missing).
- `access` rows show where the exe reads a registered pair later (function RVAs, unmapped except where the function map has a name).
- Reference page: `docs_proto/docs/exe/options.md` (generated).
