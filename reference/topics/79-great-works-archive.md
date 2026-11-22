---
title: Great Works Archive - keeping great works that would be lost (Dev CE)
order: 79
---
# Great Works Archive: keeping great works that would be lost (Dev CE)

**Availability: experimental.** Needs the **Dev CE** GameCore mod ([0.9.0-experimental](https://github.com/cru121/civ6-dev-ce/releases/tag/v0.9.0-experimental) or newer, Steam build 26595377, single player) and the mod `DevCE_GreatWorksArchive`. The native part acts **only in a game whose database has the capability `CAPABILITY_DEVCE_GW_ARCHIVE`**; without it every hook passes straight through to the game's own code, so Dev CE alone plays like vanilla. The capability is added by the mod's SQL (`INSERT OR IGNORE` into `Types` and `GameCapabilities`; any mod may add it) and must be present when the game starts. For how great works are recorded, slotted, moved and lost, see the "Great works" topic of this reference.

## The problem
* **A relic with no free slot is not lost, it is never made.** Every relic source ends in `Player::Religion::CreateRelic`, which asks `GetNearestRelicSlot` for a city with room. With none it does nothing: no record, no notification, and the relic stays in the pool. *Verified with the stock library, build 15038592.* The Palace counts as a relic slot (one slot, free at game start), so this only happens once the Palace and every temple-like building are full.
* **A work whose building is removed leaves its slot** (`City::Buildings::RemoveGreatWorkSlots`) and, in stock play, is not shown anywhere.
* **The trade screen lists only works held in city slots,** so a work that sits in no slot cannot be offered.

## How the archive works
* **An archived work is a normal game-wide record that sits in no slot.** *Verified in game (build 15038592):* `Game::Culture::AddRelic(city, relicBuilding, slot, source)` with a valid city, a relic-holding building and an **out-of-range slot (99)** creates the record (type, owner, turn) and skips the placement silently. The work is owned, grants nothing (yields and tourism stay 0) and the stock Great Works screen does not show it. With building -1 `AddRelic` crashes in the notification text lookup (null dereference at +0x68) after creating the record.
* **Relics:** with the capability, `CreateRelic` is hooked: for a **human** player with no free relic slot the hook still calls `AddRelic` with the out-of-range slot, so the relic is chosen, recorded and owned but unslotted. Every other case calls the original. The relic popup then wrongly says "Displayed in the Palace" (it takes the line from the building passed to `AddRelic`).
* **Who owns an unslotted work?** The record's player field is the *creator* (it also drives theming), so the real owner is stored separately: the gameplay script keeps it in the Game property `GWA_OWNERS` and mirrors it into the native side with `GWArchive.SetOwner`.
* **Hooks (six):** `Player::Religion::CreateRelic`, `City::Buildings::RemoveGreatWorkSlots` (a removed building's works become unslotted, not lost), `Player::Culture::ReceiveGreatWork` (a failed placement reports an event), and three on the trade item `Diplomacy::Deal::Item::GreatWork`: `CreatePossible` adds an item for every work the giver owns in the archive, `IsValid` accepts such an item, `Enact` hands the work over with `ReceiveGreatWork`; with no free slot the work lands in the receiver's archive. Archived works are tradable by default (`GWArchive.SetTradeArchived(flag)`)` turns it off).
* **At start-up** the DLL checks the prologues of 23 functions and installs no hook on a mismatch.

## Lua API (gameplay state)
| function | meaning |
|---|---|
| `GWArchive.TryPlace(player, listIndex [, ownerByProperty])` | place an archived work in a city with a free suitable slot. Returns 0 placed, 1 no such record, 2 belongs to another player, 3 already held in a slot, 4 no city has a free suitable slot, 8 internal failure, 9 game state unavailable. A non-zero third argument skips the record-player check (the script has verified ownership). |
| `GWArchive.PopEvent()` | next event as `work, owner, code, turn` (nothing when the queue is empty; events for works that are displayed again by then are dropped) |
| `GWArchive.PurgeGhosts(player)` | manual cleanup of that player's cities: slot entries for buildings the city no longer has are dropped, works inside them become unslotted (event 4). Returns entries, works. |
| `GWArchive.SetOwner(index, player)`, `ClearOwners()` | the script mirrors `GWA_OWNERS` here so the native trade hooks know who owns an archived work |
| `GWArchive.SetTradeArchived(flag)` | flag 0 or 1: archived works are offered in, and accepted by, trades (default 1) |
| `GWArchive.IsHeld(index)` | displayed in a slot of any living player's city |
| `GWArchive.ArchivedRelicCount()` | relics created into the archive this session |

Event codes: 1 the building holding the work was removed, 2 placement for a player failed (trade, capture), 3 relic created into the archive, 4 found in a leftover (ghost) slot entry and moved out of it.

## The mod
`DevCE_GreatWorksArchive` adds the capability, an **Archive** button on the Great Works screen and a panel that lists the player's unslotted works and places one in a city with a free suitable slot ("Fix hidden slots" runs `PurgeGhosts`), plus the gameplay script that keeps the owner table and drains the event queue. The mod adds its context into the existing screen with `ContextPtr:ChangeParent`. A UI button asks for changes through an `EXECUTE_SCRIPT` unit command that reaches `GameEvents.<PARAM_NAME>` in the gameplay VM, which is the multiplayer-safe route.

## Notifications
The game keeps **at most one `NOTIFICATION_RELIC_CREATED` per player at a time**: a second relic in the same turn gets no notification, nor does one created while an earlier notification is still present (dismissing it lets the next one notify). *Confirmed in game.*

## Tested
In game on build 26595377 (DX12, single player): capability off: a relic with no free slot is lost as in vanilla and no archive log lines appear. Capability on: the relic is kept unslotted, the panel lists and places it, save and reload keep it, a gold sale of an archived relic hands it over ("placed in a slot"), relic swaps, and a save with the mod added loads with a working Archive button. **Not tested:** a receiver with no free slot, archived works of AI players offered to the human, city capture with Palace or Theater works (the order of the capital move, the transfer and `RemoveGreatWorkSlots` decides the owner), the spy great-work heist, DX11, the "Fix hidden slots" button, trading with the capability off. **Known gap:** paths with no hook (`RelocateBuildingGreatWorks` drops, destroyed non-capital cities) leave no owner event; the owner then falls back to the record's creator.

*Addresses (RVA in `GameCore_XP2_FinalRelease.dll`, build 26595377, as used by Dev CE 0.9.0): `Player::Religion::CreateRelic` 0x313950, `GetNearestRelicSlot` 0x3144b0, `Game::Culture::AddRelic` 0x1c7240, `City::Buildings::RemoveGreatWorkSlots` 0x10d3e0, `Player::Culture::ReceiveGreatWork` 0x2832f0, `City::Buildings::IsInCity` 0x10cc60, `CanAddGreatWork` 0x109a70, `Diplomacy::Deal::Item::GreatWork::Create` 0x585ba0, `CreatePossible` 0x585bf0, `IsValid` 0x5863f0, `Enact` 0x585f40.*
