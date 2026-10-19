# Developer tools and crash reports

Sources: Ghidra decompile of `Tuner::AppTuner2::Listener::ProcessInput` (0x4f5bf0), `AssetCloud::Listener::ProcessInput` (0x4ef4f0), `AppHost::BugSubmissionPackager::GenerateHeaderInSubmissionFolder` (0x705e70); strings of the handlers; `FDebugHelperNS::GetExceptionDescription` (0x986d20). Reference: `docs_proto/docs/exe/devtools.md`, data `docs_proto/data/exe_devtools.json`.

- FireTuner message: 8-byte header + `COMMAND:args`; application commands `LSQ`, `APP`, `CLOSE`, `TREE`, `STRACKERS`, `START_TRACKER`, `STOP_TRACKER`, `LOAD`, `HOTLOAD:<ARTDEF|UI|other>:<name>`; any other message is `<Lua state index>:COMMAND:args` with `CMD`, `HELP`, `HELPT`, `VAL`, `QRY`, `KILLQRY`, `TABLE`, `CUSTOM_TABLE`, `CUSTOM_TABLE_SEL`, `LIST`, `LISTSEL`, `MLIST` (12). Handler names are `Tuner::AppTuner2::Listener::Handle*` (HandleSetValueRequest, HandleQueryRequest, HandleTableInfoRequest, HandlePopulateListRequest ...). Needs `EnableTuner` (AppOptions Debug section).
- AssetCloud listener: `CLOSE`, `HOTLOAD`; log `AssetCloudTuner.log`; hot load queue entries `ARTDEF:` / `DEPENDENCY:`.
- Bug submission header (17 element names: GUID, Application, SubmissionType, Host, Time, File, Line, Message, Callstack, Catalog, Log, Dump, Attachments, Exception, ModuleInfo, Version, Session) and the 22 `EXCEPTION_*` names.
- Not tried against a running tuner; meanings of LSQ, APP, LOAD, START_TRACKER, STOP_TRACKER are guesses from the words (handlers unnamed).
