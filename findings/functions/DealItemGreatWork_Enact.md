---
function: GameCore::Diplomacy::Deal::Item::GreatWork::Enact
subsystem: Diplomacy / great works
rva_symbol_build: 0x584b10
rva_installed_build: 0x585f00
address_mapping: unique (installed = Steam build 15038592; symbol build = older Steam depot 947510)
lua_exposure: "Not registered directly; runs when a deal containing a great work is enacted."
analysis: decompiled and read (Ghidra 12.1.4), 2026-09-29
---

# Diplomacy::Deal::Item::GreatWork::Enact

`void __thiscall Enact(GreatWork* this, uint dealPhase)  [virtual]`

Executes a great-work trade item: takes the work out of the giver's city and gives it to the receiver.

## Verified from the decompilation
- Skips if the item's parent type is a particular constant (0xd384eeb7) or either player is not alive.
- Finds the giver's city that holds the work (IsInCity), calls RemoveGreatWork on it via edit(), then Player::Culture::ReceiveGreatWork for the receiver.
- If ReceiveGreatWork fails, it stores the stranded index in the deal item (this+0x90) instead of losing it, then fires a virtual notification callback.
- Giver player is at item+0x28, receiver at item+0x2c.

## Inferred (not confirmed in-game)
- The constant 0xd384eeb7 is probably a deal-type hash. (Low.)

## For modders
- This is the reference implementation of moving a great work between players; a custom mover should follow its order of operations.

## Related
- [Diplomacy::Deal::Item::GreatWork::PostEnact](DealItemGreatWork_PostEnact.md)
- [City::Buildings::RemoveGreatWork](Buildings_RemoveGreatWork.md)
- [Player::Culture::ReceiveGreatWork](Culture_ReceiveGreatWork.md)
