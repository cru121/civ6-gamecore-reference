---
title: "Great works: records, slots, loss paths and relics"
order: 78
---
# Great works: records, slots, loss paths and relics

**What this page is.** How the game stores great works, what happens when one does not fit anywhere, how a work moves between cities and players, and what a relic does when every relic slot is full. It is engine behaviour, found by reading the game library and by experiments in disposable single-player games. Nothing here needs a mod to be true; where a mod (Community Extension or Dev CE) is needed to *use* a fact, the text says so.

**Status marks.** **verified** = seen in a running game. **code** = read from the decompiled game library, not run. **inferred** = follows from verified or code facts. Builds: observed on build 15038592; the GameCore code is the same in later builds (see [How to read this reference](conventions.md) for build 26595377, which moved the addresses).

## 1. Two separate things: records and slots
- **The game-wide record list.** Every great work that has been created has one record in a list in `Game::Culture`. A record holds the work type, the turn it was created, and a player id. Records are never deleted by any of the paths below. The list is saved with the game (**verified**).
- **Slots.** A city's `City::Buildings` holds, per building, a list of great-work slots. A slot holds a *list index* (the position of a record in the game-wide list), not a type. `Buildings::IsInCity(index)` asks whether a city holds it.
- A work is **displayed** when some city slot holds its index. A record that no slot holds is in **limbo**.
- Artifact types can have several records each: excavating appends a new record every time. Do not assume one record per type (**verified**, late-game save, 105 records).

## 2. What a work in limbo does (verified)
A limbo work exists, is saved, and grants **nothing**: per-city yield and tourism getters, the Great Works screen totals and the screen's list all ignore it. A work moved out of a slot with the game's own functions behaves the same, and `ReceiveGreatWork` can place it again later: yields and tourism return when it is back in a slot.

| Test (single player, one city, the Palace's one slot) | Result |
|---|---|
| Place work 0 | Culture +2, tourism +2 |
| Try to place work 0 again | Refused, no new record: the game does not place the same work twice |
| Create work 1 while the Palace is full | Record exists (count 1 to 2), in no slot, **totals unchanged**, not shown on the screen |
| Save and reload | The limbo record is still there; totals as before |
| `RemoveGreatWork` on work 0, then `ReceiveGreatWork` on work 1 | Palace empty: 0 yields, 0 tourism. After placing work 1: +2 / +2. Persisted through save and reload |
| `RemoveBuilding(Palace)` while it holds a work | No refusal, no crash; the work's record stays, in no slot |

Not checked: the top-bar per-turn numbers, score and victory screens, and modifiers that count "great works owned" (the getters are per slot by construction, so another code path could count a limbo work). Only Great Writings and relics were tried.

## 3. How limbo happens: the loss paths (code, one verified)
In every path below the game **clears slots and never deletes the record**, and none of them sends a notification about the work.

| Event | What the game does | Where the works end up |
|---|---|---|
| **City captured** (`City::Manager::Transfer`) | Snapshots the city's buildings and slots. For each work: `RemoveGreatWork` from the city, then `Player::Culture::ReceiveGreatWork(newOwner, index)` | The new owner's first city with a suitable free slot; if none, no slot (limbo) |
| **Capital lost** (`FindandMovetoNewCapital`) | Picks a new capital, adds a Palace, and `AddGreatWork`s every work held by the old Palace-flagged building into it | The new capital. `AddGreatWork` silently does nothing if no slot fits |
| **City destroyed** | Only the capital case handles great works; no other great-work code runs | Non-capital: the city's works are in no slot |
| **Building removed** (`RemoveBuilding`, `RemoveAllBuildings`, private `RemoveGreatWorkSlots`) | Rebuilds the city's slot vector without the building's entry | The works that were in it are in no slot (the Palace case is **verified**) |
| **Building replaced** (`RelocateBuildingGreatWorks`) | Tries the same city, then every other city; drops what fits nowhere | In no slot |
| **Trade** | The deal keeps the stranded index and retries (see section 4) | In transit, then placed or stranded |

So limbo is common in real games. In one late-game save, 15 of 105 records were in no slot, mostly works created by AI players that nobody could place (**verified**).

## 4. How the game moves a work
This is the trade path; the capture code uses the same remove-then-receive pair.
1. Find the holder: the city whose slots contain the index (`Buildings::IsInCity`).
2. Get that city's `Buildings` through the tracked-state accessor `edit(city + 0xca0)`.
3. `Buildings::RemoveGreatWork(index)` clears the slot.
4. `Player::Culture::ReceiveGreatWork(receiver, index)` tries each of the receiver's cities in order (`CanAddGreatWork`, then `Buildings::AddGreatWork`, which takes the first empty slot whose slot type accepts the work's object type). It returns false when no city has room.
5. If placing failed, the deal item keeps the stranded index and `PostEnact` retries.

Facts that matter if you build on this (**code** unless marked):
- `RemoveGreatWork` does no recalculation; tourism and yields are computed on demand, so nothing goes stale (**inferred**).
- `AddGreatWork` returns nothing and does nothing when no slot fits: check `CanAddGreatWork` first. `AddGreatWorkToSlot` places precisely (building type plus slot) but does no slot-type check.
- Tracked state: many objects keep state in `FAutoVariable<...>` members, and code that changes them calls `edit()` first. Writing around `edit()` risks lost changes or desync (purpose **inferred**, not confirmed).
- The trade screen builds a player's list of works from city slots only, so a limbo work is never offered in a deal by the stock game.

## 5. The record's player field is the creator, not the holder
`Game::Culture::SetGreatWorkPlayer` is called only where a work is created (**code**). In a real save the human held many works whose player field was another player, and an AI held works whose field was 0 (**verified**). The field is the work's **civilization of origin**:
- the Great Works screen uses it for the theming bonus (a building whose works all come from different civilizations);
- the artifact tooltip uses it ("artifact from <player>").

Consequences: it cannot tell you who owns a work that sits in no slot, and **it must not be overwritten** to mean "holder" (it would break themed buildings and the artifact text). A mod that wants to track the holder of unslotted works needs its own storage, saved with the game (for example a game property per record index).

## 6. Relics
A relic is a great work of object type `GREATWORKOBJECT_RELIC` and uses the same slot machinery.
- **Every relic source** (combat kills such as an apostle, map discoveries through `ViewPlotContents`, `SpreadDissent`, and the `GrantRelic` modifier effect used by the goody-hut reward) ends in `Player::Religion::CreateRelic` (**code**).
- **With no free relic slot it does nothing at all** (**verified**, stock DLL): no relic is chosen, no record is made, no notification is sent, and the relic stays in the pool for later. It is not "created and thrown away".
- The relic is chosen, recorded, placed and announced inside `Game::Culture::AddRelic`, which needs a city, a relic-holding building type and a slot.
- **The Palace counts as a relic slot** (one slot, free at game start). In this build the relic-holding building types are indices 1, 12, 13, 62, 82, 87, 95, 109. "No relic slot" therefore only happens when the Palace and every such building are full.
- Goody-hut relics need a city (`MinOneCity="true"` on `GOODYHUT_ONE_RELIC`).
- At most one `NOTIFICATION_RELIC_CREATED` exists per player at a time; a second relic the same turn gets none until the first is dismissed (**verified**).

**Keeping a relic that would be lost (needs a native hook, so Community Extension or Dev CE).** Calling `AddRelic` with a valid city, a valid relic-holding building type and an **out-of-range slot** (99 worked) creates the record and skips placement silently: the relic is owned, in no slot, grants nothing, and is not shown on the Great Works screen (**verified**). Pitfalls found on the way:
- With building = -1 `AddRelic` creates the record and then crashes in the notification text lookup. Always pass a real building type.
- `AddRelic` announces the relic as placed in the building you passed, so the popup says "Displayed in the Palace" for a relic that is in no slot.
- It needs a city; a player with none has nothing to anchor the relic to.

## 7. Reading records from Lua
| Function (UI side) | Bounds-checked? | Notes |
|---|---|---|
| `Game.GetGreatWorkPlayer(i)` | Yes: returns -1 past the end of the list | Safe with any index. Result is the record's player field |
| `Game.GetGreatWorkDataFromIndex(i)` | **No** | Returns `TurnCreated`, `GreatWorkType`, `CreatorName` |
| `Game.GetGreatWorkTypeFromIndex(i)` | **No** (only -1 is special-cased: returns -1) | Read from the shared cache function `Cache::Game::Instance::GetGreatWorkTypeFromIndex`, which the `CityBuildings` binder below also calls; the `Game` binder itself was not read |
| `CityBuildings:GetGreatWorkTypeFromIndex(i)` | **No** | Same cache function as above |
| `CityBuildings:GetPlayerFromIndex(i)` | **No** (not even -1) | Reads the record's player (the creator) |
| `CityBuildings:GetTurnFromIndex(i)` | **No** (not even -1) | Reads the record's turn |
| `CityBuildings:GetCreatorNameFromIndex(i)` | **No** | Reads the type, then looks it up in the definitions and dereferences the result |

- **Why the unchecked readers crash (code, build 15038592; read from the decompile, reproduced as crash reports by Klear2012 in [issue 5](https://github.com/cru121/civ6-gamecore-reference/issues/5)).** The four `CityBuildings` binders (UI cache state; `lGetCreatorNameFromIndex`, `lGetGreatWorkTypeFromIndex`, `lGetPlayerFromIndex`, `lGetTurnFromIndex`) only convert argument 2 with `lua_tointeger` (nil or a non-number becomes **0**) and call a `Cache::...` function. Those functions take `Game::Culture::Get()`, read the great work record vector (`m_kGreatWorks`, data pointer at Culture+0x118) and index it as `base + index * 0x18` (record: +0 type, +4 player, +8 turn, +0x10 pointer to the creator name) with **no bounds check**. In a game where no work has been created yet the vector is empty and its data pointer is null, so even index 0 reads address 0, +4 or +8 (the four access violations seen at the first load of each function). Past the end of a non-empty list the readers return garbage (`GetCreatorNameFromIndex` then dereferences a lookup of the garbage type and crashes), and index -1 is far outside the heap for the three that do not special-case it. The crash happens inside the function, so `pcall` cannot catch it. The register `rcx` in the dumps is `this`, which none of the four functions dereferences.
- **Safe shapes.** A call is safe exactly when the index is a real record index (`0 <= i < number of records`). The practical source is the result of `CityBuildings:GetGreatWorkInSlot(building, slot)` when it is not -1; the stock UI checks for -1 first. `GetGreatWorkTypeFromIndex(-1)` is safe. With no record-count getter in the UI API, do not call these four in a game that has no great works yet, and never with a guessed index. So the family does not need a permanent block, only an index you got from a slot (or from a `Game.GetGreatWorkPlayer(i)` that returned a real player).
- **Do not loop until the reader returns nil.** That crashed the game (`EXCEPTION_ACCESS_VIOLATION`) the first time the index passed the last record; `pcall` does not help because it is a native fault (**verified**). There is no record-count getter in the UI API. Safe pattern: call only `Game.GetGreatWorkPlayer(i)` and use the other readers when it returns a real player.
- The 14 great-work methods exposed to gameplay Lua are all read-only getters. There is no stock method to add, remove or move a work; `TransferCity` is the only Lua path that moves one, as a side effect.
- The Great Works launch-bar button appears only after the great-work-created event or when a refresh finds a work in a local city slot. A work that exists only as an unplaced record does not unlock it (**verified**). The screen itself opens whenever `LuaEvents.LaunchBar_OpenGreatWorksOverview()` is raised, so a mod can open it without the button.
- To put a work from limbo into a city, or to take one out of a slot, a mod needs native code: the Community Extension exposes `Player.Cities:AddGreatWork(listIndex)` to gameplay scripts. Dev CE adds more (see the Dev CE method pages for `PlayerCulture` and `CityBuildings`).

## 8. Open questions
- Does skipping `edit()` cause a visible problem, in single player and in multiplayer?
- What is the constant `0xd384eeb7` that makes the trade item's `Enact` skip? (Probably a deal-type hash.)
- The exact meaning of the city value at +0x268 and the 0x158 flag that `FindandMovetoNewCapital` uses.
- Whether the era score, achievements or other systems react to the signal `AddRelic` sends (effects unknown).
- Which of the 13 `CreateRelic` callers is the goody hut, an apostle death or the city-state perk is **inferred** from names, not verified.
