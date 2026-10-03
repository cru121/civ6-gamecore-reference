# Operations and commands: hash -> handler map

The game identifies every unit operation, unit command, city operation, city command and **player operation** by a 32-bit hash
(`~crc32` of the upper-case name, see `events-hashes-and-data-symbols.md`). Names come from the Linux enums, handlers from the
symbol-build functions. Tools: `tools/op_handlers.py`, `tools/player_op_cases.py`.
Tables: `tables/operation_handlers.tsv` (unit/city operations and commands), `tables/player_operation_cases.tsv` (player operations).

## Unit and city handlers (Verified for 108 by hash, Inferred for 16 by name)
Each handler class has a static `Register` function that allocates the handler, stores its hash in the handler at +0xc, and registers it with
the manager. Reading that immediate gives hash -> class for **108 of 124 handlers**; 16 more (the Hero commands, clan commands and two
XP-specific city commands) store the hash differently and were matched by class name (`HeroAreaDamageHeal` -> `AREA_DAMAGE_HEAL`, ...), which
is a naming convention, not a proof. Registered: 70 unit operations, 44 unit commands, 8 city commands, 2 city operations.
Per handler the table lists `CanStart`, `Start`, `MakeParameters`, `SetParameters` (and `ResolveOperation` for spy operations) with old and
current RVAs.
Enum names without a registered handler (not registered in the symbol build): unit operations `BUILD_CAMPUS`, `BUILD_HOLY_SITE`, `BUILD_ENCAMPMENT`,
`BUILD_ENTERTAINMENT_COMPLEX`, `BUILD_THEATER_DISTRICT`, `BUILD_HARBOR` (old per-district names, superseded by `BUILD_DISTRICT`), `INTERCEPT`;
unit commands `AUTOMATE`, `STOP_AUTOMATION`, `GIFT`, `ESTABLISH_INDUSTRY`, `FOUND_CORPORATION`, `CREATE_RANDOM_RESOURCE` (not found; may use a
different registration); city commands `PURCHASE`, `DESTROY` (XP-specific classes, matched by name).

## Player operations are a switch inside one function (Verified)
Player operations are not classes. `Player::Operations::Manager::Process` (old 0x30c120, current 0x30d330, 6.8 KB) is a binary decision tree on
the operation hash with one inline case per operation. **32 of the 40 enum values** have a case (in both builds, same order):
`RESEARCH`, `DECLARE_WAR`, `MAKE_PEACE`, `PROGRESS_CIVIC`, `FOUND_PANTHEON`, `FOUND_RELIGION`, `ADD_BELIEF`, `GIVE_INFLUENCE_TOKEN`,
`RECRUIT_GREAT_PERSON`, `REJECT_GREAT_PERSON`, `PATRONIZE_GREAT_PERSON`, `UNLOCK_POLICIES`, `LEVY_MILITARY`, `RETURN_LEVIED_MILITARY`,
`SET_ESCAPE_ROUTE`, `CHOOSE_ARTIFACT_PLAYER`, `MOVE_GREAT_WORK`, `NAME_CORPORATION`, `APPOINT/ASSIGN/PROMOTE_GOVERNOR`, `COMMEMORATE`,
`COMPLIMENT_PRIDE_MOMENT`, `REJECT_EMERGENCY` and `ACCEPT_EMERGENCY` (one shared 9-instruction body), six World Congress operations.
Six more are separate handler classes: `EXECUTE_SCRIPT`, `START_OBSERVER_MODE`, `HIRE_CLAN`, `BRIBE_CLAN`, `RANSOM_CLAN`, `INCITE_CLAN`.
`WORLD_CONGRESS_RESOLUTION_BID` has no case and no class found. The table gives, per case: start address (old/current), size, the
parameter ids it reads (`PARAM_*`), events it sends and the named functions it calls.

### Great-works relevance (Verified)
* **`MOVE_GREAT_WORK`** (case old 0x30d4dd, 263 instructions) reads `PARAM_PLAYER_ONE`, `PARAM_CITY_SRC`, `PARAM_CITY_DEST`, `PARAM_BUILDING_SRC`,
  `PARAM_BUILDING_DEST`, `PARAM_GREAT_WORK_INDEX`, `PARAM_SLOT`; calls `Buildings::GetGreatWorkInSlot`, `RemoveGreatWork`, `AddGreatWorkToSlot`,
  dispatches a signal and sends event `GREAT_WORK_MOVED`. The vanilla Great Works screen calls it from Lua:
  `UI.RequestPlayerOperation(Game.GetLocalPlayer(), PlayerOperations.MOVE_GREAT_WORK, tParameters)` with exactly those seven parameters
  (`Base/Assets/UI/GreatWorksOverview.lua`, line ~914). So moving a work between two buildings the player owns **needs no DLL patch**.
  Because it starts with `GetGreatWorkInSlot` on the source building, it cannot pick up a work that sits in no building (a limbo/archived work).
* **`CHOOSE_ARTIFACT_PLAYER`** (case old 0x30cff9, 106 instructions) is the branch that calls `Culture::SetGreatWorkPlayer` and
  `AddArtifactToBuilding`; it sends `UNIT_ARTIFACT_CHANGED` and `UNIT_VISIBILITY_CHANGED` and destroys the archaeologist
  (`Units::DelayedDestroy`). This is the branch whose city lookup got a null check in the current build (see `build-differences.md`).
* The six remaining Great-Works-neutral cases are unchanged between the two builds in structure (32 cases found in each).

## Open points
* How Lua reaches unit operations/commands (`UnitManager.RequestOperation`, `RequestCommand`) was not re-checked here; the registry is in `lua_registry.tsv`.
* The 16 name-matched hash assignments should be confirmed if a tool depends on them.
