# Event ids, hash constants and typed globals (from the Linux debug info)

Sources: enum values, global variables and their types from the Linux port's DWARF (`tools/dwarf_extract.py`, `tools/dwarf_vars.py`),
applied to the Windows DLLs. Tables are in `findings/tables/`.

## The hash function (Verified)
The numeric ids of event, notification, moment and operation types are **`~crc32(NAME)` of the upper-case identifier** (bitwise NOT of the
standard zlib CRC-32), stored as a signed or unsigned 32-bit value. Checked: 351 of 352 events, all 224 notification types, 165 of 166 moment
types, all 63 definition "kinds", and so on (152 enums match in whole or part). The one event that does not fit is `EMERGENCIES_UPDATED`
(value 673022418): its id was evidently derived from a different string. The same function is what `Utilities::MakeHash` computes
(name resolved from the symbol build; not separately disassembled).
Example: `UNIT_MOVED` -> `0xBE121408`.

## Tables
| File | Content |
|---|---|
| `tables/events.tsv` | all 352 `Events::EventTypes` with hash, signed value, and how many functions contain that hash as an immediate (old build) |
| `tables/notifications.tsv` | 224 `Notifications::Types` |
| `tables/moments.tsv` | 166 `MomentTypes` (Historic Moments) |
| `tables/player_operations.tsv`, `tables/unit_operations.tsv` | 40 player and 75 unit operation type hashes |
| `tables/config_keys.tsv` | the 101 `GameConfiguration` key constants (e.g. `KeyName_StartEra` = `GAME_START_ERA`, `KeyName_EnabledMods` ...) with their real string values, read from the Linux data |
| `tables/data_symbols.tsv` | 1,314 named global variables with their **Linux type and size** and the matching Windows old/new RVA |

## Decoding magic constants in the Windows code (Verified)
`tools/decode_hashes.py` scans every 32-bit immediate in `.text` for a known hash. Result: **6,461 constants in about 2,025 functions**
resolve to a name (events 1,415, notifications 556, war types 292, unit-operation results 272, combat types 220, moments 214, diplomatic
statements 190 ...), identical in the symbol build and the current build. So **the current build adds no new event, notification, moment
or operation id in code** (new content like Caesar's ability is data-driven). Output: `linux_depot/out/hash_constants_{old,new}.tsv`
(rva, function, instruction, enum.name).
Examples: in `Player::Operations::Manager::Process` the constants resolve to the operation switch (`ACCEPT_EMERGENCY`,
`WORLD_CONGRESS_RESOLUTION_VOTE`, `PROGRESS_CIVIC`, `FOUND_PANTHEON`, `COMMEMORATE`, ...) and event `PLAYER_OPERATION_COMPLETE`;
`0x9d4424f5` (seen at the artifact event earlier) is `UNIT_ARTIFACT_CHANGED`; in `CalculateExperienceEarned` the two compared ids are
`COMBAT_DISTRICT_VS_UNIT` and `COMBAT_UNIT_VS_DISTRICT` (combat-versus types).

## Events (Inferred usage from counts)
Most referenced in code: `UNIT_OPERATION_STARTED` (46 functions), `CAMERA_LOOKAT_NORMAL` (39), `WORLD_TEXT_MESSAGE` (38),
`UNIT_VISIBILITY_CHANGED` (36), `PLAYER_ERA_SCORE_CHANGED` (35), `UNIT_ACTIVATE` (31). Events with **no hash constant in any function**:
`CITY_OPERATION_STARTED`, `DIPLOMACY_REFUSE_PEACE`, `DIPLOMACY_INCOMING_DEAL`, `EMERGENCIES_UPDATED` (custom id), `RESOURCE_AMOUNT_CHANGED`,
`MONOPOLY_GAINED`, `MONOPOLY_LOST`, `SECRET_SOCIETY_LEFT`, `CULTURAL_IDENTITY_CITIZEN_CONVERTED`, `EVENT_POPUP_REQUEST`, `EVENT_POPUP_RESPONSE`,
`EVENT_SOUND_REQUEST`, `WORLD_CONGRESS_PLAYERS_CHOICE`. They may be sent through a computed id (for example a table or a name hashed at
run time) or are dead; not checked. Modder relevance: names and ids are the vocabulary of `Events.*` / `LuaEvents` and of any event-queue
work; the table gives a stable id for each name.

## Typed globals (Verified names; types from Linux)
`data_symbols.tsv` gives, for each of 1,314 globals, the platform-independent type where it is a pointer or scalar. Examples
(old -> current RVA, all `.data`): `Context::Globals::ms_pkCurrentContext` (`Context::Instance*`) 0xb88a60 -> 0xb8aa60,
`ms_pkCurrentGame` (`Game::Instance*`) 0xb88a68 -> 0xb8aa68, `ms_pkParameters` (`const Game::GlobalParameters*`) 0xb88a70 -> 0xb8aa70,
`ms_pkConfiguration` 0xb88a78 -> 0xb8aa78, `ms_pkEngineUtility` 0xb88a80 -> 0xb8aa80, `ms_pkScriptSystem` 0xb88a88 -> 0xb8aa88,
`ms_pkLoggingManager` 0xb88a90 -> 0xb8aa90. These agree with the offsets the Community Extension already uses. Sizes of STL-based
globals differ between platforms and should not be copied.
