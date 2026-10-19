# Event buses, consumers, notifications and the debug console (engine exe)

Sources: Linux `Civ6` disassembly; extractors `tools/exe/event_subs.py`, `console_cmds.py`. Tables:
`../tables/exe_event_subscriptions_linux.tsv` (732 subscriptions), `../tables/worldview_event_subscriptions.tsv`
(122, with Windows handler RVAs), `../tables/exe_event_translators_linux.tsv` (315),
`../tables/debug_console_commands.tsv` (138 help lines), `../tables/debug_console_command_calls_heuristic.tsv`.
**Verified** from disassembly unless marked.

## 1. The buses
The exe's event system has several buses, distinguished by the container template argument of
`Events::EventTemplate<N, Data, Dispatcher, Container, ...>`. Subscriptions found in static code (not counting the Lua
event libraries, which subscribe dynamically):
| Bus | Subscriptions | Distinct event ids | What it carries |
|---|---|---|---|
| GameCore | 415 | 153 | numbered `GameCoreEvent_Template<N,...>` messages translated from GameCore Reporting events |
| LocalMachine | 126 | 57 | app-local UI events (resolution changed, show leader screen, toggle grid, exit to menu ...) |
| Serial | 109 | 55 | serialized UI/state events (loads, saves, network state) published in order |
| UIEvent | 47 | 14 | input and debug console (`UIE_DebugConsoleInput` is id 15) |
| Sequencer | 28 | 8 | sequencing of animations/events |
| MovieEvent | 7 | 2 | movie playback |

## 2. Who consumes the GameCore bus
Largest subscribers (static handlers): **WorldView** (registration function Linux 0x332ceb0, 122 events; Windows
unsubscribe table 0x54a820, handler list in the worldview table), **StrategicView** (Linux 0x3300fc0, 58),
`StrategicAudio` (51), `Minimap_Startup` (36), a UI event dispatcher at 0x32f4ca0 (25), `AudioMiner` (18),
`GameCoreController` (13: turn begin/end, phase, player turn activated/deactivated, local player changed, player
destroyed, event-queue flushed), `GameViewState` (plot visibility, local player), `Simulation::*` (13), camera,
ambient audio, telemetry (`GameCore::App::Telemetry::Listener`), Network, ForgeUI. The most widely consumed events:
Player_EventData 274 (11 subscribers), CityAddedToMap 87 (8), Improvement 143 (7), DistrictAddedToMap 156 (7),
City 93, DistrictChanged 157, District 160 and BuildingAddedToMap 165 (6 each).
Event ids and data types come from the template arguments; the full pair list is in the table, and
`../tables/exe_gamecore_event_handlers_linux.tsv` lists the named member handlers per id.
Reporting events that have **no** translator never reach this bus (315 hashes do; see the architecture topic). A modder
who needs the renderer or UI to react to a new kind of state change has to emit one of those translated events.

## 3. Notification layer (what the exe does with notifications)
- Notifications are created in GameCore (`GameCore::Reporting::Notification::*`, 224 methods in `Instance`, 78 in `Type`).
- The engine interface has `SendNotification` (IEngineUtility1 slot 25, Linux 0x32b4de0 / Windows 0x1ca870) and
  `SendStatus` (slot 24). **`SendNotification` forwards to `Reporting::Notification::Reader::Receive`, which is a
  single `ret` in the exe (Linux 0x3245480) and a shared empty stub on Windows (0x96f20).** So this path does nothing in
  the exe; the UI learns about notifications through the cache (`Cache::Player` / notification entries) and
  `NotificationActivated` / `NotificationRefreshRequested` events (translators `Translate::NotificationActivated`
  0x3212d00 and `NotificationRefreshRequested` 0x3212c30; event id 257 is consumed by the telemetry listener and Lua).
  `SendStatus` goes to a real receiver (`Reporting::Status::Reader::Receive`, Linux 0x325f7c0, 283 bytes).
- Cloud/Firaxis Live notifications (`Firaxis::Notifications::Process`, `Network::Manager::CheckServerForCloudNotifications`)
  are a separate server-side feature, unrelated to gameplay notifications.

## 4. Debug console
Handlers subscribed to `UIE_DebugConsoleInput` (UIEvent bus id 15): WorldView/render console (Linux 0x3323cd0,
Windows 0x540670, 101 help lines), `GameCoreController::OnConsoleMessage` (Windows 0xf56b0: `explore all`,
`reveal all`, `gamecore profile on/off/depth`, `gamecore message record on/off`, `gamecore message playback`),
`GameViewState::OnConsoleMessage`, `CameraSystem`, `Civ6App`, `MainMenuState` (`loadmap {name}` loads a WorldBuilder
map), `ForgeUI::DebugContext`, the leader screen, minimap, audio and color-key systems. `help all` prints the
combined list. Commands are tokenised (`UIE_DebugConsoleInput::GetToken(n)`), so the table lists the help line, and the
heuristic call table lists the first non-trivial functions called after each token literal. Example (verified earlier
by disassembly of both builds): `terrain rebake` -> `TerrainContext::RebakeCache` (Win 0x609be0), `terrain rebuild` ->
`RebuildTerrainEdits` (0x609ca0), `terrain toggle wireframe` -> `TerrainView::ToggleWireframe`, `terrain toggle cell
wireframe` -> `TerrainContext::ToggleCellWireframe` (0x3799780 Linux). The heuristic table can attribute a neighbouring
token's call to the wrong command; treat it as Inferred, Low-Medium.
The console is reachable on retail builds only if the debug UI is enabled (not tested).

## For modders (Inferred)
- The UIEvent id 15 handlers are a convenient place to hook if you want your own console commands: subscribe to
  `UIE_DebugConsoleInput` and parse `GetString()`.
- The 122-event WorldView list is the definitive answer to "which state changes does the 3D view react to".

## Update 2026-10-19: precise Windows console dispatch (`tools/exe/wincons.py`)
Table: `../tables/debug_console_commands_windows.tsv` (268 command literals in the 12 `UIE_DebugConsoleInput` handlers, with Windows RVAs).
Verified by disassembly of the Windows exe.
- Command matching is uniform: `lea rdx,[literal]; call MATCHER; test eax,eax; jne next`, where MATCHER is `0x983740`
  (whole-phrase, used by the first-level handlers: Civ6App, GameViewState, MainMenu, GameCoreController, Audio, ColorKey, ForgeUI debug)
  or `0x9836e0` (used by the WorldView console 0x540670 and the camera / leader screen / minimap handlers). The exe function map labels
  both as `CPreprocessor::TokenList::*`; that is a wrong propagation (the code is a console token matcher), so ignore that name.
  The help-line printer is `ForgeUI::ConsolePrintf` (0x8d8dc0), not the matcher.
- Commands are matched one token at a time, so subcommands (`rebake`, `rebuild`, `on`, `off`) appear as separate literals after the
  top-level literal (`terrain`), in code order. Check: `rebake` -> `TerrainContext::RebakeCache` (0x609be0) and `rebuild` ->
  `RebuildTerrainEdits` (0x609ca0), matching the earlier hand analysis; this replaces the Linux-side heuristic table for Windows lookups.
- Handlers and literal counts: WorldView 0x540670 (143), Civ6App 0x69f10 (41), GameViewState 0x7d780 (22), 0x1d69c0 camera (10),
  0x1ee760 leader screen (10), 0x8e27a0 ForgeUI debug (10), 0x1f3b20 minimap (6), 0x4ac10 (6), 0xa4f8d0 color key (6),
  GameCoreController 0xf56b0 (8), 0x8aa70 main menu (3), 0x98290 audio (3).
- Limits: only literals matched inline in the handler; a command forwarded to another function is missed. The "calls until next command" column
  lists the first six distinct callees before the next literal test (root RVA plus mapped name if any), so it can mix in calls that belong to
  the check itself (for example the multiplayer guard in `explore all`).

## Update 2026-10-19 (b): events as reference entities (`docs_proto/docs/exeevents/`)
- **The GameCore bus id of an event is readable from its translator.** Each translator calls the constructor/sender of `GameCoreEvent_Template<N,...>` (its callee names in the Linux build), so translator -> N is exact for
  315 translators (313 with exactly one N, 2 with two). That gives names to bus ids that share data types (`Unit_EventData`, `Player_EventData`, ...): 317 ids map to engine events, e.g. 151 = TERRAIN_STATE_CHANGED (translator Windows 0x153ce0, medium),
  149 = TERRAIN_TYPE_CHANGED. 321 GameCore bus events in total, 153 with static exe handlers, 264 with a Lua event name of the Modding Companion list.
- Other buses: LocalMachine 57 events, Serial 55, UIEvent 13, Sequencer 8, MovieEvent 2 (named from their data types; no engine event hash). Handler registrations: 322 / 77 / 91 / 33 / 20 / 5.
- Systems with the most handlers: WorldView 122, StrategicView 58, StrategicAudio 51, Minimap 36, Telemetry listener 32, UI event dispatcher 25, UI manager 20, Network manager 18, AudioMiner 18.
- Pipeline: `docs_proto/tools/extract_exe_events.py` (-> `data/exe_events.json`) and `exe_events_section.py`; handler Windows addresses exist only for the WorldView handlers (registration-order match) and for the few mapped medium/high functions.
