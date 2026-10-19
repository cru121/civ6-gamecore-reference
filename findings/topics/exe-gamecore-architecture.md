# How the engine executable and GameCore fit together

Sources: Linux `Civ6` (names), `libGameCore_XP2.so` (DWARF names), Windows `CivilizationVI.exe` and
`GameCore_*_FinalRelease.dll`. Linux addresses are ELF vaddrs, Windows are RVAs. Items are **Verified** (read in
disassembly), **Inferred** or **Open**. Tables: `../tables/interface_IContext1_gamecore_vtable.txt`,
`../tables/interfaces_exe_implements.txt`, `../tables/EngineUtility_vtable_windows.tsv`,
`../tables/exe_event_translators_linux.tsv`, `../tables/exe_function_map.tsv`.

## 1. The two halves
- The **exe** is the host: window, renderer (WorldView), UI (ForgeUI + Lua), audio, network, mods, the game-state
  machines (`LoadGameViewState`, `GameViewState`), and a `GameCoreSupport` layer (source files
  `Civ6/Src/App/GameCoreSupport/GameCore_*.cpp`, `GameCoreController.cpp`, `GameCoreSupport.cpp`).
- **GameCore** (`GameCore_Base/XP1/XP2`) is the simulation: rules, map, players, AI, gameplay Lua. It is a separate
  library the exe loads at runtime.
- Everything crosses a narrow, COM-like boundary: reference-counted interface objects (`GameCore::Interfaces::I*1`)
  found with `QueryInterface(guid)`.

## 2. Bootstrap (Verified)
1. `GameCore::LoadDLL(path)` (Linux 0x31dd330, Windows 0xf8510) loads the library and resolves two exports by name:
   `DllCreateGameContext` and `DllDestroyGameContext`. The Base/XP1/XP2 choice is made in
   `AppModdingFramework::LoadGameCore` (path strings `libGameCore_*.so`).
2. `DllCreateGameContext` is a one-instruction jump to `GameCore::Exports::Context::Create()` (Linux 0x2c7c880), which
   creates a `GameCore::Exports::Context` (the implementation of **IContext1**, wrapping
   `GameCore::XP2::Context::Instance`). The exe caches the pointer in `GameCore::s_pActiveContext`;
   `GameCore::GetContext()` (Linux 0x31dd790, 80 callers) lazily creates it.
3. `AppModdingFramework::LoadGameCore` / `InitializeGameCore` (Linux 0x3382dd0 / 0x3381690, Windows 0x24b150):
   `new GameCore::EngineUtility()` (ctor Linux 0x32b3b90, Windows 0x1c9240), then
   `context->SetEngineInterface(engineUtility)` (IContext1 slot 12, vtable +0x60), `context->Initialize()` (+0x28),
   `GetScriptSystemUtility()` (+0x68), `SetProfileParameter(hash, value)` (+0x1e8) for Gameplay/ProfileEnabled and
   ProfileDepth taken from the options database, then `GameCoreController::SetContext(context)`.
   The vtable offsets are identical in the Windows build.

## 3. Interfaces
**Exe calls GameCore: IContext1** (80 slots; full list in the table). Groups: lifecycle (Initialize, StartupGame,
ShutdownGame, Save/Load, OnSaveComplete); accessors for the roughly 75 `I*1` interfaces (GetGame, GetMap,
GetPlayer(n), GetDefinitions, GetWorldBuilder, read-only GetCache* views); game setup (InitializeNewGame,
Set/ResolveConfiguration values, SetCivilizationDefaults, InitializeSyncRandomSeed); frame and cache (Update(bool),
UpdateCache x2, EnableCacheUpdates, CachingEventPlaybackComplete); requests (RequestAction,
RequestUnit/City/PlayerOperation, CanStartPlayerOperation); the message queue (ReceiveMessage, QueueMessage,
ProcessMessages, HasPendingMessages, Set/IsMessageRecording and Playback, LoadMessageRecorderState); tuner and profile
hooks. The concrete classes are `GameCore::Exports::*` (about 75 families, for example Exports::Plot with 65 methods,
Exports::Definitions with 192).

**GameCore calls the exe: IEngineUtility1** (46 slots, implemented by `GameCore::EngineUtility`, Linux vtable
0x53a6c80, Windows 0xfc79d0): GetScriptSystem / GetLoggingManager / GetAchievements / GetHallofFame; the game-core lock
(Has/Release/Get/TryGameCoreLock, IsGameCoreThread, IsGameCoreExecuting, IsAppThread); RequestTurnUnready;
SendMessage / SendMessageToLocal (network); RegisterEvent(+Parameter); **SendEvent** (two overloads);
**SendCacheUpdate** (two); SendStatus; SendNotification; GetNetworkLocalPlayerID; GetPathList / GetFolder;
Begin/EndReportingBlock; player colour type lookups; GetGameSyncManager; GetAutoArchiveFactory; ActionProcessed;
SetConfiguration / SendConfigurationEvent; database URIs; IsModPath / ResolveModPath; GetLocalOptions;
GetCapabilityAllowance. Other exe-implemented interfaces: IScriptSystem1 (+Args, Arg), IAchievements1, IHallofFame1,
ILoggingManager1, ILogFile1, IErrorResults1.
GameCore also imports about 2,041 plain symbols from the exe (shared base library: `Data::TypedVariant*`, `String::*`,
`Lua::*`, rapidjson, eastl, `Platform::*`, `Localization::*`, `Types::*`). That is the engine's base library, not
gameplay callbacks (Verified: GameCore's imports resolved against the exe's exports).
Overload note: MSVC can reverse the vtable order of overloaded virtuals, so the Windows slot names for pairs 14/15,
16/17, 20/21, 22/23 and 43/44 are Inferred from the Linux order.

## 4. Event paths (Verified on Linux)
**Gameplay events (Reporting).** GameCore code calls `Reporting::Event::Send(Type(hash), ...)` (Linux 0x2d49430
family). Each send (a) gives a `TypedVariantMap` to `Cache::Dispatcher::Send` inside GameCore and (b) calls
`EngineUtility::SendEvent` (IEngineUtility1 +0xa8). On the exe side `SendEvent` (Linux 0x32b4260) looks up the event's
parameter usage and fills a `GameCore::Events::EventData`; `GameCore::Events::Translate::Register()` (Linux 0x3206b00)
holds an `eastl::map` of **315 Reporting hashes to translator functions** (for example TERRAIN_TYPE_CHANGED 0x13ae3a55
to `Translate::TerrainTypeChanged`, 0x320ee90). The result is the numbered `GameCoreEvent_Template<N, ...>` messages
(ids up to 383) on the exe's `g_EventSystemGameCore` queue (`GameCoreEventManager<GameCoreEvent_Queue<EventStream>, ...>`).
Subscribers use `Events::SubscribeToMessage<GameCoreEvent_Template<N,...>>`: the Lua event libraries (`Events.*`),
WorldView (122 events, see the terrain topic), Minimap, StrategicView, AudioMiner, telemetry, GameCoreController (turn
begin/end, phase, player turn activated, local player changed). Queue features: event sequencing, conflict detection
(`IsConflictingEvent`), a pre-dispatch handler for cache updates, immediate publishing (`PublishImmediateEvent`).

**Cache path (for UI and renderer reads).** In GameCore, `GameCore::Cache::<System>::EventStream::Manager` classes
(City has 55 methods, plus Map, Player, Unit and about 60 other systems) listen to Reporting events and publish cache
entries. `EngineUtility::SendCacheUpdate` posts a `CacheUpdate` event (id 275); the exe calls
`IContext1::UpdateCache` / `EnableCacheUpdates` / `CachingEventPlaybackComplete` and reads through the read-only
`GetCache*` interfaces (the exe's `GameCore::App::Cache::Map::GetPlot` etc. are thin wrappers). The terrain cache
manager (`Cache::Map::Terrain::EventStream::Manager`) handles `PlotTerrainStateChanged`, `PlotTerrainSubTypeChanged`
and `MapPlotCacheUpdate`.

**Messages (network and commands).** `IContext1::QueueMessage / ReceiveMessage / ProcessMessages`. Turn requests use
`RequestAction*` with hashed ids (for example `RequestGameCoreUpdate` sends action 0xb186b9fb).

## 5. Threads and locks (Verified unless marked)
- **Main/app thread**: `Civ6App::UpdateFrame` (Linux 0x2f97470, Windows 0x76c00): input, UI, Lua, `UIPublishEvents`,
  audio job, render, then near the end `Network::Signal`, `UpdateNetwork`, `HasPendingMessages` /
  `SendProcessingComplete`, `RecordGameCoreMessages`, **`GameCoreController::ExecuteGameCoreUpdate`**, then
  `UpdateLuaGarbageCollect`. `GameViewState::UpdateGameCore` (Linux 0x2fbca10) runs the per-frame GameCore handshake
  (turn synchronization barrier, event queue playback, `RequestGameCoreUpdate`).
- **"Game Core" thread** (`GameCoreThread`, created with `Platform::CreateThread`, name string "Game Core", ctor Linux
  0x31d1150 / Windows 0xf4650): a suspend/resume worker. Each pass (`GameCoreThread::Run`, Linux 0x31d11d0): enter the
  controller's critical section, `GameCore::EditGame()`, mark executing, and unless updates are suspended call
  `IContext1::ProcessMessages()` (+0x238), mark complete, leave the section, then suspend itself.
  `ExecuteGameCoreUpdate` resumes it (controller flag +4 = threaded mode; when off, it takes the lock and calls
  `IGame::Update` (slot +0x30) inline on the caller). `Synchronize()` / `JoinOnPassComplete()` block the caller until a
  pass completes; `DestroyGameCoreThread` synchronizes, resumes if suspended, then joins.
  Whether threaded mode is the shipping default: **Open** (the setter `SetGameCoreThreadState` has no direct callers).
- **Lock**: `GameCoreController::GetLock/TryLock/ReleaseLock/HasLock` wrap a `Platform::CriticalSection` (GetLock Linux
  0x31d2440, Windows 0xf4be0). Long waits are logged with `Platform::LogEvent`:
  "**** MAIN THREAD stalled on GC lock for %.2f ms", "**** GC thread stalled on GC lock ...",
  "**** Thread: %u stalled on GC lock ...". GameCore reaches the same lock through
  `IEngineUtility1::Get/Try/ReleaseGameCoreLock`.
- **Other threads**: only three `Platform::CreateThread` callers exist: GameCoreThread, `Network::NetworkWorker::Start`
  and `TransportThreadBase::Start`. Other parallelism is `Platform::JobManager` (job lists, `ParallelFor`; libtbb ships
  with the Linux build; jobs appear in profiler strings such as 'WorldView_Update', 'Terrain Context Render').
  The renderer submits from the main thread (`Graphics::Renderer::Render`, with `WaitForPresent`). Whether the DX
  renderer has a separate render thread: **Open**.
- **Lua states**: the exe's `AppLuaScriptSystem` / `AppLuaThread` build the UI-side Lua threads and register the
  `AppLua*Library` tables (Achievements, DB, Event, GameSummary, Input, Locale, Modding, Options, Path, Search,
  UIEnums, FiraxisLive) plus `GameCore::LuaGameCoreLibrary`. GameCore's registrations split into a **Game side** (1,305
  methods, run in the simulation) and a **UI side** (1,015, backed by the cache interfaces); see `../../lua_registry.tsv`.
  Gameplay Lua runs through `IScriptSystem1`, implemented in the exe by `GameCore::ScriptSystem` (the exe provides the
  Lua VM and thread objects, GameCore supplies the tables).

## 6. Ownership summary
The exe owns: process, window, renderer and WorldView state, UI/Lua VMs, the event queue, network, mod loading, the
controller and the GameCore thread object, files, logging, achievements.
GameCore owns: all simulation state (Game, Map, Players, Cities, Units), the definitions, the Reporting and Cache event
producers, command/operation processing, World Builder logic, save/load serialization (`IContext1::Save/Load`).

## For modders (Inferred, untested)
- Anything that must show in the 3D view has to be announced through an event WorldView subscribes to (list in
  `worldview_event_subscriptions.tsv`) or through cache updates. Silent GameCore state changes are invisible to the
  renderer.
- The IContext1 and EngineUtility slot tables are stable entry points: both builds use the same vtable offsets, so a
  hook can reach `UpdateCache`, `EnableCacheUpdates` or `ProcessMessages` through the vtable without function addresses.
- Long stalls on the GameCore lock are logged with the exact strings above, a quick way to find lock problems in a mod
  hook.
