# Ghost great work slots: a work "held" by a building the city no longer has

Status: **observed in a real save** (forum post, 2026-10-01, read with the Frida `holders` / `palaces` commands); the way the state arises is **not verified**.
Tool: `../../frida/gw_limbo.js` (`records`, `findwork`, `holders`, `palaces`, `unghost`).

## The report
A player traded two statues for "Red Cliff" (`LOC_GREATWORK_YING_3_NAME`, a Landscape work) to theme a museum. The trade was accepted, but the work never appeared in any
museum or in the in-game search; it did show on the player's side of the trade screen.

## What the save contains
- Red Cliff is **not** in limbo. It is record 37 (player field 5 = its creator, turn 282).
- It is referenced by the slot list of **city 1572886**: building type 1 (the Palace), slot 0. `IsInCity` returns true, and the raw slot list holds the index.
- That city is **not the capital and has no Palace** (`HasBuilding(Palace)` false). The Palace and the (empty) Palace slot are in another city, the real capital.
- So a **leftover slot entry** for a building the city no longer has still holds the work. This is why the trade screen lists it (`Deal::Item::GreatWork::CreatePossible`
  walks each city's slot list) while every screen that looks at built buildings shows nothing.

## Why it is invisible, and what it still does
Anything that finds works by walking *buildings* (the Great Works screen, the museum UI, the search) never visits the dead entry: the screen showed 72 works.
Anything that reads the slot list sees the work as held: the trade list, `IsInCity`, and the per-city getters, so the same save counts 73 works.
**Verified on the save (`report`):** the ghost's city has `works in slots=1`, culture 3 and tourism 4 (a Landscape work), and the player total is 73 works in slots,
equal to the trade screen. So the work **still yields culture and tourism**; what is lost is visibility, the ability to move it, and any theming bonus a real museum slot would give.
It also cannot be placed elsewhere, because the game thinks a city holds it.

## Why the UI cannot see it (verified in the UI Lua)
A city keeps two parallel records: which buildings it **has** (location/flag tables, read by `HasBuilding`) and a per-city **slot vector** (Buildings + 0xc8: building type + its slots). The screens that show works
iterate *real buildings* and only then ask for that building's slots: `GreatWorksOverview.lua` (line ~123: `if pCityBldgs:HasBuilding(buildingIndex) then ... GetNumGreatWorkSlots`), `LaunchBar.lua` (unlock check, same pattern),
and the map search / city tooltip use the city's list of buildings. Placement, the trade list (`CreatePossible`), `IsInCity` and the yield getters iterate the slot vector. A slot entry whose building is gone is visible to the second group only.
Nothing here is a building: it is a leftover slot entry.

## How it probably arises (strong lead from the code, not yet observed live)
`AddGreatWorkSlots` creates the entry when a building is added and `RemoveBuilding` removes it through `RemoveGreatWorkSlots`, keeping the two records in step.
`City::Manager::Transfer` (city capture) clears buildings it will not hand over by **calling `SetBuildingLocation(building, -1)` directly**, never `RemoveBuilding`/`RemoveGreatWorkSlots`:
every building whose definition has flag 0x8 at +0x158 (the Palace, which `AddPalace`/`FindandMovetoNewCapital` treat specially) and buildings whose district is not carried over take that branch.
For a captured **capital**, the Palace's works are first moved to the old owner's new capital (`FindandMovetoNewCapital`) and removed from the captured city, then the Palace is cleared the direct way: the
Palace's (now empty) slot entry stays behind in the captured city. That empty entry then accepts the next work placed by `ReceiveGreatWork` (Red Cliff). The forum save fits: exactly one ghost, in a city the player conquered.
Other buildings cleared the same way (district not carried over) may leave ghost entries too, possibly with works in them.

## Detecting and repairing it
- Detect: for each city, for each building entry in its slot list (Buildings + 0xc8, count at +0xd8, 0x20 bytes per entry: building type, slot array at +8, slot count at +0x10,
  8 bytes per slot with the work index at +4), the entry is a ghost when `HasBuilding(type)` is false and a slot holds a work.
- Repair candidate (tested only in design): `RemoveGreatWork` on that city (through `edit()`), then `ReceiveGreatWork` for the same player, exactly the game's own move
  sequence from the trade code. The Frida `unghost` command does this.

## Why works land in a ghost slot (verified from the decompilation, 2026-10-02)
`City::Buildings::CanAddGreatWork`, `AddGreatWork` and `GetFreeSlot` all walk the city's slot vector (Buildings + 0xc8, count at +0xd8) and take the first slot whose work field (slot + 4) is -1 and whose slot type accepts the work. **None of them checks `HasBuilding` for the entry's building type.** So a leftover entry for a building the city no longer has behaves like any other free slot, and `Player::Culture::ReceiveGreatWork` (which only calls `CanAddGreatWork` and `AddGreatWork`) can place a purchased work there. The only thing that makes an entry a "ghost" is the combination: entry present in the slot vector, `HasBuilding(type)` false. There is no flag on the entry itself.

## The exact mechanism (verified from `City::Buildings::SetBuildingLocation(type, int)`, 2026-10-02)
A building "exists" in a city when its **location** (Buildings + 8, one short per building type, -1 = none) is set. `SetBuildingLocation(type, location)` writes that value and, when the new location is not -1, calls `AddGreatWorkSlots(type)` (creates the slot entry; for a building with flag 0x8 at +0x158 it also calls `SetAsCapital(true)`). **Setting the location to -1 never removes the slot entry**; only `RemoveBuilding` does (it calls `RemoveGreatWorkSlots` first). Any code that clears a building through `SetBuildingLocation(type, -1)` alone (city capture in `City::Manager::Transfer` does this for the Palace and for buildings whose district is not carried over) leaves a ghost slot entry. A fix at the source is a hook on `SetBuildingLocation(type, -1)` that also drops the slot entry (not built; needs care inside `Transfer`, which later removes and re-places the snapshot works).
