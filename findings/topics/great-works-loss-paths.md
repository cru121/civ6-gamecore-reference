# How great works get lost: city capture, destruction, capital move, building removal

Status: **read from the decompiled game code** (symbol build, Ghidra 12.1.4, 2026-09-30). Nothing below was run in game yet unless stated.
Addresses are symbol-build RVAs; `City::Manager::Transfer` is mapped only through the call graph and is known to have changed between builds.
The in-game check for "building removed" is prepared (`rmbuilding` in `../../frida/gw_limbo.js`) but was not run when this was written.

## Common rule: a work that leaves its slot stays a record
In every path below, the game **clears slots; it never deletes the game-wide great work record**. A work that fits nowhere is simply in no slot ("limbo",
see [great-works-limbo](great-works-limbo.md): it still exists, is saved, and yields nothing). Nothing in these paths sends a notification about it.

## Paths
| Event | What the code does | Where the works end up |
|---|---|---|
| **City captured** (`City::Manager::Transfer`, new owner = param 2) | Snapshots the city's buildings and their slots first. If the city was the old owner's capital, calls `FindandMovetoNewCapital` for the old owner. For each work in the snapshot: `Buildings::RemoveGreatWork` from the city, then `Player::Culture::ReceiveGreatWork(newOwner, index)` | The **new owner's** cities, first one with room (`ReceiveGreatWork` checks `CanAddGreatWork`). If none has room the work is in no slot. |
| **Capital lost or destroyed** (`FindandMovetoNewCapital`) | Picks the old owner's city with the highest value at city+0x268 that is not occupied, makes it capital, adds a Palace, then `AddGreatWork`s every work held by a building whose definition has flag 0x8 at +0x158 (presumably the Palace) into that city | The new capital. `AddGreatWork` has no `CanAddGreatWork` check of its own and silently does nothing if no slot fits. With no cities left nothing is placed. |
| **City destroyed** (`City::Manager::DestroyCity`, `DestroyCityAndMoveCapital`, `Player::Cities::Destroy`) | Only the capital case handles great works (above). No other great work code appears in `Player::Cities::Destroy`. | Non-capital: the city's works are in no slot (records stay). |
| **Building removed** (`City::Buildings::RemoveBuilding`, `RemoveAllBuildings` -> private `RemoveGreatWorkSlots`) | `RemoveGreatWorkSlots` rebuilds the city's per-building slot vector **without** the removed building's entry; it never touches the great work records | The works that were in that building are in no slot, with no notification. |
| **Building replacement** (`Player::Cities::Add/RemoveBuildingReplacementOverride` -> `Rules::...::RelocateBuildingGreatWorks`) | See [that note](../functions/Rules_RelocateBuildingGreatWorks.md): tries the city, then every other city, silently drops what fits nowhere | In no slot. |
| **Trade** | See [great-works-moving](great-works-moving.md): the deal keeps the stranded index and retries | In transit, then placed or stranded. |

## The ownership question (matters for any archive)
`Game::Culture::SetGreatWorkPlayer` is, as far as the callers show, called only where a work is created, so the game-wide record's **player field looks like
the creator**, not the current holder (Inferred; `great-works-moving.md` has the evidence). Consequences for works that end up in no slot:
- Captured overflow or a destroyed building's works keep the **creator** in their record. If the creator is not the last holder (a traded or captured work),
  "owned by me and in no slot" points at the wrong player: the creator could see and re-place a work they gave away.
- Any archive that means "works I lost" needs the record's player field set to the holder at the moment the work leaves its slot.
  Natural hooks: `RemoveGreatWorkSlots` (building removed, city destroyed) and a failed `ReceiveGreatWork` (capture overflow, stranded trade items).
  Both are `this`-based calls from which the owner (city + 0xd8, or the receiving culture's player) is readable.
- **Do not overwrite that field.** The stock UI reads it as the work's *civilization of origin*: `GreatWorksOverview.lua` (around lines 350-365 and 610-620) uses
  `Game.GetGreatWorkPlayer` to decide whether a building's works are all from different civilizations (the theming bonus), and `UnitFlagManager.lua` uses it in
  the archaeology tooltip ("artifact from <player>"). Setting it to the holder would break theme bonuses (two works "from the same player" in one building) and
  the artifact text. Any "who owns this archived work" information therefore needs **separate storage** (for example a game property per work index),
  written when a work leaves its slot and read by the archive panel and `TryPlace`. It must be persisted in the save (a native-only table would not be).
- Not yet checked: what `AddGreatWork`/`ReceiveGreatWork` do with the record when placing, and the exact meaning of city+0x268 and the 0x158 flag.

## For modders
- The game never destroys a great work record in these paths, so nothing is permanently lost at game-rule level; it becomes invisible (no slot, no UI).
  A mod that can list records (UI: `Game.GetGreatWorkPlayer` is bounds-checked, see [ui-great-work-records](ui-great-work-records.md)) can find them again.

## Observed in a real late-game save (2026-10-01, found online, 105 records, `records` command of the Frida tool)
- **15 of 105 records were in no slot**, none with player field 0 (the human). Their creators were AI/other players (7 x8, 5 x3, and 2, 4, 6, 63 once each); several are runs of consecutive turns by one civ (likely AI-created works nobody could place). So limbo is common in real games, mostly for AI-created works.
- **The record player field does not follow the holder**: the human held many works whose field was another player (4, 5, 6, 7, 8), and an AI held works whose field was 0. Confirms the field is the civilization of origin (also used for theming), not the owner.
- **Artifact types can have several records**: types 169, 172, 173, 174, 175 each appear twice (excavation appends a new record each time). Do not assume one record per great work type. Artifact records often have player field 63 (meaning not checked).
- A work bought by trade and stranded with no slot would look the same as an AI-created stranded work (seller as creator, no slot); the record does not say who bought it.

## Live test: removing the Palace that holds a work (2026-10-03, installed build, single player)
`City::Buildings::RemoveBuilding(Palace)` via the live Frida channel (`rmbuilding 1`) on a capital whose Palace slot held a great work: the game did not refuse and did not crash.
The building was gone (`HasBuilding` false), the city's slots were gone with it, the work's record stayed (limbo: in no slot, record player field unchanged),
and the ghost scan found no ghost entries. Matches the earlier static analysis (building removal only clears slots; works survive as records).
