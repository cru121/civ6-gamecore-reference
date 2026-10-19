# SQL and text keys the engine exe refers to

Method: ASCII string literals of the Windows exe that contain SQL (191 distinct statements) or look like `LOC_` keys (55), with the functions that reference them (`docs_proto/tools/extract_exe_sql.py`).
Reference pages: `docs_proto/docs/exedb/` (generated). **Verified**: the statement text and the referencing function. **Inferred**: which database a statement runs against (from its table names and function).
- 92 statements belong to the **mod framework** (`Mods.sqlite`): tables Mods, ModGroups, ModGroupItems, ModFiles, Components, Settings, Criteria, ComponentCriteria, SettingCriteria, ModProperties, ModDependencies,
  ModRelationships, ModCompatibilityWhitelist, ScannedFiles, AdditionalScannedFiles, Migrations, MetaData. Functions: `Modding::Framework`, `ModLoaderService`, `XmlModLoader`, `ModDiscoveryService`, `FileService`, `PropertyService`, `ModAssociationsService`.
- 22 statements are the **game summary database** (`HallofFame.sqlite`): Games, GameObjects, GamePlayers, ObjectDataPointValues, GameDataPointValues, DataSets, DataSetValues, ChallengeGames.
- About 77 statements **read the game database for the exe's own use**. Tables and columns the exe consumes (a mod adding columns elsewhere is invisible to it): `Features` (FeatureType, Name, AddsFreshWater; read by `WorldView_StartupGame`), `Colors` / `PlayerColors` (read and written by the color manager),
  `Eras`, `GlobalParameters`, `Rulesets` (GameCore, VictoryDomain), `Victories`, `Maps` (Domain, File), `CivilizationAudioTags` (MusicOverride), `Languages` (SupportsSmallCaps), `FontStyleSheets`, `DefaultAudioLanguages`, `SteamLanguages`, `AudioLanguages`,
  `Icon*` tables (icon atlases), `Input*` tables (actions, categories, contexts, key data, default gestures), `NavigationProperties` (Lua database registration), and the game summary tables (`Graphs`, `GraphQueries`, `Reports`, `ReportQueries`, `ReportColumns`, `StatisticCategories` ...).
- 55 `LOC_` keys are literals in the exe: map and scenario names (`LOC_MAP_*`, `LOC_*_SCENARIO_*`), city names, a confirm-exit text. All other texts come from the database.
- Limits: SQL built from parts at run time is not seen; table-per-database attribution is a guess for the game databases (Gameplay vs Configuration vs Localization).
