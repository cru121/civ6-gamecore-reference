# How great works are traded (Deal::Item::GreatWork)

Status: **read from the decompiled game code** (symbol build, 2026-10-02); the in-game test of the hooks built on it is pending. Installed-build addresses are in `gw-archive/native/GWArchive.h`.

## The item
A deal item for a great work is an object of 0x98 bytes: giver player at +0x28, receiver at +0x2c, a "stranded index" at +0x90 (-1 normally), and a value variant (virtual +0x50 reads it, +0x58 writes it) whose type tag at +0 is 2 and whose
great work **list index** is at +8. `GreatWork::Create()` is a static factory for a new item.

## Building the list a player can offer: `CreatePossible(deal, giver, receiver, flags, itemVector)`
Walks the giver's cities and, for each city's slot vector (the `GreatWorkBuilding` copies at city + 0xd78), makes one item per occupied slot. **Works held by no city never appear**, and neither do works in a ghost entry's absence (a work in a ghost
entry does appear, which is how the forum player saw Red Cliff). `SetPossibleTableItems` (the Lua-facing table: `ForType`, `ForTypeName`, `ForTypeDescriptionID`) uses only the list index and the definition, so it works for any index.

## Validation: `IsValid`
1. Base check (`Item::Instance::IsValid`).
2. The giver must hold the work: `Buildings::IsInCity` on one of the giver's cities. If not: result 0 (invalid) with an error string.
3. Unless the item's parent type is `0xd384eeb7`: the **receiver must have room**. `Player::Culture::HasSlotsForGreatWorks(receiverCulture, otherWorksComingIn, worksGoingOut, thisWork)` must be true, else result 2 (error string 0x87150719).
   So in the normal game a player **cannot buy a work without a free slot**; the Red Cliff purchase passed this test only because the dead (ghost) Palace slot counted as room (that check also walks slot vectors).

## Enacting: `Enact(phase)`
Base `Item::Instance::Enact`; skipped if the parent type is `0xd384eeb7` or either player is not alive. Then: find the **giver's city that holds the work**, `RemoveGreatWork` on it (through `edit()`), `ReceiveGreatWork` for the receiver; if that fails the index is kept in +0x90 (retried by `PostEnact`).
Finally the item's value is reset to -1 so it cannot run twice. **If no giver city holds the work nothing is moved**, only the value is reset.

## What it takes to trade archived (unslotted) works
Three things, none needing UI changes: add items for them to the list (`CreatePossible`), let `IsValid` accept them (no holding city; and the receiver need not have room, because the work can simply go to the receiver's archive), and make `Enact` do the
`ReceiveGreatWork` itself. Ownership of an unslotted work is not stored by the game (see `great-works-loss-paths.md`), so a mod must supply it. The relaxed rule "receiver needs no free slot" would, applied to normal works too, let a player buy any work with full slots
(it would land in their archive).
