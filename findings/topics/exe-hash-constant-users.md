# Where the engine exe uses GameCore's hashed enum values

Method: `tools/exe/hashsearch.py` searches the Windows exe (`CivilizationVI.exe`, DX11 Jul 2024) for the little-endian `~crc32` constants of
hashed enums (`linux_depot/out/hashed_enums.tsv`, from the Linux DWARF) and attributes each hit to its function. **Verified**: the byte hit exists;
the *meaning* of each use is Inferred from the function name unless stated. Table: `../tables/exe_enum_hash_uses.tsv` (only enum values with a
hit; the event-translator hits are left out). Names resolve only where the function map has them (see `exe-function-index.md` for confidence).

## What the exe special-cases
| Enum | Used in the exe | Where |
|---|---|---|
| `ActionTypes` (15 of 15) | `ACTION_ENDTURN`, `ACTION_RETIRE`, `ACTION_UNREADYTURN` in `GameCore::App::UI::Manager::RequestAction`; `ACTION_GAME_UPDATE` in `GameCoreController::RequestGameCoreUpdate`; the player/host actions (`PLAYER_CONNECT/DISCONNECT/SWAP/SNAPSHOT_*/MOD_STATUS`, `HOST_MIGRATION_*`) in `Network::NetSessionCallbacks` and `NetModStatus::Execute`; `PLAYBYCLOUD_*` in `Network::Manager`; `GAME_PAUSED` in `Network::Manager::UpdatePauseStatus` | UI/network request layer; these are the actions the exe itself sends to GameCore |
| `CapabilityTypes` (8 of 37) | `BARBARIAN_CLANS`, `DRAMATICAGES`, `HEROES`, `MEGADISASTERS`, `MONOPOLIES`, `SECRETSOCIETIES`, `TREE_RANDOMIZER` all in `AppLuaModdingLibrary::lUpdateParameter` (the game-setup parameter update); `TOWERDEFENSE` in the telemetry post-load listener | game setup UI gates these options on capabilities; the other 29 capabilities are not hardcoded in the exe |
| `DefinitionTypes::TypeHash` (kinds) | `CIVILIZATION`, `LEADER`, `IMPROVEMENT`, `UNIT`, `BUILDING`, `FEATURE`, `RESOURCE`, `ROUTE`, `DISTRICT`, `WONDER`: `AppModdingFramework::CheckPostLoadOwnership` and `CheckConfigurationOwnership` (which mod owns which content), `GameCore::App::WorldView::Manager::HasAssetFor` (building/district/resource/wonder art present?), `GameCore::App::UI::Lua::IManager::lPlayLeaderAnimation`, plus two unnamed helpers (0x3ebf0, 0x4df480) | ownership checks and asset lookups; terrain is not on the list |
| `UnitStateTypes` | `UNIT_EMBARKED` (10 sites), `UNIT_DISEMBARKED` (3): `WorldView::UnitSystem::Context::SetUnitStateType`, unit handlers at 0x154c60, 0x4df700, 0x5487b0, 0x548d80, `Simulation::Combat::PhasedCombatInstance::Initialize` | unit visuals switch on embark state |
| `Events::EventTypes` | 320 of 352 appear, almost all only inside `Events::Translate::Register`; exceptions: `PLAYER_INITIALIZED` / `PLAYER_UNINITIALIZED` in `GameCore::App::Configuration::Game::HandleGameCoreEvent`, `PLAYER_VISIBILITY_CHANGED` at two unnamed sites (0x13fa82, 0x145fb2), `DIPLOMACY` in `GameCore::EngineUtility::RequestTurnUnready` | |
| `ConfigurationEvents::EventTypes` | `PLAYER_CHANGED`, `PLAYER_VALUE_CHANGED`, `GAME_VALUE_CHANGED`, `PLAYERS_UNSERIALIZED` in `Configuration::Game::HandleGameCoreEvent` | the exe mirrors the config tables from these events |

## What the exe never special-cases (zero constant hits)
`MomentTypes` (165), `GossipTypes` (66), `KindTypes` (63), `WarTypes` (15), the `InstanceTypes` enums, and all but one of the 224
`Notifications::Types` values (that one hit is a data table entry, `NOTIFICATION_SECRETSOCIETY_LEVEL_UP`, not code). This matches the notification
finding: the exe only forwards notifications, it does not branch on their type. Same for moments and gossip: nothing in the exe reacts to a specific one.
(Some enums contain a zero-valued hash, which matches everywhere; those rows were dropped.)

## For modders (Inferred)
- Adding a **new moment, gossip, notification type or kind** needs no exe support; the exe never looks at the individual values.
- A new **capability** gates only what the exe's game-setup code knows about; custom capabilities are ignored there.
- `CheckPostLoadOwnership` / `CheckConfigurationOwnership` explain why content of the listed kinds is attributed to the mod that defines it.

## Event parameter keys read by the exe (second pass, 2026-10-19)
Enums scanned: `Reporting::Parameters::ParameterTypes` (148 keys), `Events::Combat::Parameters`, `SharedParameters`, `Messages::Parameters`, and the unit / city
operation and command parameter enums. Same-named keys appear in several of these enums (`PARAM_X0`, `UNIT0`...), so a hit proves the *name* is used,
not which enum it came from. Table: `../tables/exe_event_parameter_keys.tsv` (function, keys found; trailing digit variants merged).
- **`GameCore::EngineUtility::SendEvent` (the GameCore-to-exe event funnel) reads 64 parameter-name hashes**: the location (`X`, `Y`, `LOCATION`), the actor
  keys of unit 0/1, city 0/1, district 0/1 and improvement (`<KIND>`, `<KIND>_ID`, `<KIND>_PLAYER`), `DATA0..2`, `MESSAGE`, `SUB_TYPE`. Each exists in a plain and a
  `PARAM_`-prefixed (operation parameter) form. Inferred: this is the set of event parameters the exe packs into its own event structure; a mod that sends
  a custom parameter name through a GameCore event will not have it read here (it can still reach Lua through the generic event path).
- **Only 12 of the 315 event translators read parameters by name; the rest copy data generically.** The 12:

| Translator | Keys read |
|---|---|
| `TerrainStateChanged` | `STATE_CHANGE`, `VISIBILITY_STATE`, `MITIGATION` |
| `UnitMoved` | `FROM_VISIBLE`, `TO_VISIBLE`, `STATE_CHANGE`, `PARENT` |
| `CombatOccurred` | `ATTACKER`, `DEFENDER`, `INTERCEPTOR`, `ANTI_AIR`, `ID`, `COMBAT_TYPE`, `WMD_TYPE` |
| `UnitActivityChanged` | `RESOURCE/IMPROVEMENT/DISTRICT/ROUTE` `_TYPE` |
| `NationalParkVisibilityChanged` | `LOCATION`, `CHANGED_BY`, `COMPONENT_ID`, `VISIBILITY_STATE` |
| `PlayerDiscoveredHero` | `PLAYER`, `TARGET`, `TYPE`, `SUB_TYPE` |
| `CityTransfered` | `FROM_PLAYER`, `TRANSFER_TYPE` |
| `BuildingEffectAdded` | `AMOUNT`, `BUILDING`, `LOCATION` |
| `WorldTextMessage` | `TO_PLAYER`, `VISIBILITY_STATE` |
| `NotificationActivated` | `NOTIFICATION`, `BY_USER` |
| `EventSoundRequest` | `MESSAGE`, `DATA0` |
| `MessageRecorder` | `PAYLOAD`, `SUB_TYPE` |

- **Terrain tie-in:** the `TerrainStateChanged` translator extracts the plot and state hash plus `STATE_CHANGE`, `VISIBILITY_STATE` and `MITIGATION`; the three
  state keys are what the WorldView handler then branches on (`exe-worldview-terrain-pipeline.md`).
- Operation names: only `BUILD_IMPROVEMENT`, `REPAIR` and `PILLAGE` unit operations are special-cased (in `StrategicAudio::OnUnitOperationStarted`;
  `BUILD_IMPROVEMENT` also in `UI::Manager::OnUnitActivityChanged`). Of the 75 unit operation types and 40 player operation types, the exe reads no
  others by hash, so a new operation needs no exe support. `UnitActivateEvent` subtypes `GIVE_RELIGIOUS_HEAL`, `ACCEPT_RELIGIOUS_HEAL`, `PET_THE_DOG` are matched in one
  exe function (0x547390). Diplomacy statement types (`FIRST_MEET_*`) are matched only by the audio systems.
- Not meaningful: `UnitAbilityTypes`, `UnitPromotionClassTypes`, `RandomEventDamageTypes`, `Serializer::Result` contain plain small integers rather than hashes,
  so their hit counts are accidental matches and were ignored.
