# Relics: what happens when there is no slot, and how to keep the relic anyway

Status: **verified in game** (single player, disposable games, 2026-09-30) unless a line says otherwise. Installed build 15038592.
Tools: `../../frida/gw_limbo.js` (`relicinfo`, `relicbase`, `reliclimbo`, `hut`) and the GW Archive prototype in `C:\stuff\claude\gw-archive`.

## 1. The stock behaviour
- Every relic source (combat kills such as an apostle, `ViewPlotContents`, `SpreadDissent`, the `GrantRelic` modifier effect used by the goody hut reward) ends in
  `Player::Religion::CreateRelic` ([note](../functions/Religion_CreateRelic.md)).
- It asks `GetNearestRelicSlot` for a city with a free relic slot. **With none, it does nothing**: no relic is chosen, no record is made, no notification is sent.
  Verified with the stock DLL: record count unchanged. The relic is not "created and thrown away"; it is simply never created, and it stays in the pool for later.
- The relic is chosen, recorded, placed and announced inside `Game::Culture::AddRelic` ([note](../functions/Culture_AddRelic.md)).
- **The Palace counts as a relic slot** (building type 1, one slot, free at game start). Relic-holding building types in this build: 1, 12, 13, 62, 82, 87, 95, 109
  (type indices). So "no relic slot" only happens once the Palace and every temple-like building are full.
- **Goody hut relics need a city**: in `GoodyHuts.xml` the relic reward `GOODYHUT_ONE_RELIC` has `MinOneCity="true"` (as do almost all hut rewards), so a player without a
  city never rolls it. The city-state perk and the `GrantRelic` modifier were not checked for the no-city case.

## 2. Creating a relic that sits in no slot
- Calling `AddRelic(city, relicBuildingType, slot, source)` with a valid city, a valid relic-holding building type and an **out-of-range slot (99)**
  creates the game-wide record (type, owner = the city's player, turn) and skips placement silently. The relic is owned, in no slot, grants nothing (yields and tourism stay 0),
  and the stock Great Works screen does not show it.
- With building = -1 (what you get by calling `GetNearestRelicSlot` with an invalid plot and passing its unwritten outputs on) `AddRelic` creates the record and then
  **crashes in the notification text lookup** (null dereference at offset 0x68). The record survives.
- `GetNearestRelicSlot` with an invalid plot returns the first city with room and does not write its building/slot outputs.
- `AddRelic` announces the relic as placed in the building you passed, so the game's relic popup ("Your civilization has produced a great work!") says
  "Displayed in the Palace, <city>" even though the relic is in no slot. The popup takes that line from the notification's building and city, not from the relic's real location.

## 3. Hooking `CreateRelic` (Community Extension style)
A hook on `CreateRelic` that, when `GetNearestRelicSlot` finds nothing and the player is human, calls `AddRelic` with the out-of-range slot as above, works in game:
a relic that would have been lost becomes an owned, inactive, placeable one. The archive panel can then place it (remove a work from the Palace, click the archived relic).
It needs a city (none: do nothing, as before). Not done: hooking the `Reporting::Event::Send` (0x1a71e9f0) that `CreateRelic` sends after a successful `AddRelic`;
the hook skips it for archived relics (effect unknown).

## 4. Notifications and popups
- The game keeps **at most one `NOTIFICATION_RELIC_CREATED` per player at a time**: a second relic in the same turn gets no notification, and neither does one created while an
  earlier notification is still present. Dismissing the notification (right click) makes the next relic notify. Confirmed by the user.
  (Test artefact worth knowing: Frida jobs ran at `BeginTurn` entry, before the previous turn's notification had expired.)
- The notification is defined with `AutoActivate`, `ExpiresEndOfTurn` (in `Notifications.xml`). The popup is opened by `NotificationPanel.lua` through
  `LuaEvents.NotificationPanel_ShowRelicCreated(player, -1, cityX, cityY, buildingID, greatWorkIndex)`; `GreatWorkShowcase.lua` listens.
- "Created by" is empty in the relic popup for relics made with source 0. The text comes from `AddRelic` (`LOC_RELIC_GOVERNOR` for governor-related relics only, as far as the code shows).
- UI trick, tested: another mod's UI context can rewrite the popup's location line. Listen to the same event and set
  `ContextPtr:LookUpControl("/InGame/GreatWorkShowcase/CreatedPlace")` while `"/InGame/GreatWorkShowcase"` is visible.

## 5. Related facts found on the way (UI side)
- `Game.GetGreatWorkPlayer(index)` is bounds-checked; `Game.GetGreatWorkDataFromIndex` and the other record readers are not (see `ui-great-work-records.md`).
- The EXECUTE_SCRIPT unit command reaches `GameEvents.<PARAM_NAME>` in the gameplay VM and is the multiplayer-safe way for a UI button to ask for a change.
- A UI context added with `AddUserInterfaces` can be re-parented into an existing screen (`ContextPtr:ChangeParent`); frame updates only arrive when that context is shown.
