---
function: GameCore::Diplomacy::Deal::Item::GreatWork::PostEnact
subsystem: Diplomacy / great works
rva_symbol_build: 0x585460
rva_installed_build: 0x586860
address_mapping: unique (installed = Steam build 15038592; symbol build = older Steam depot 947510)
lua_exposure: "Not registered directly."
analysis: decompiled and read (Ghidra 12.1.4), 2026-09-29
---

# Diplomacy::Deal::Item::GreatWork::PostEnact

`void __thiscall PostEnact(GreatWork* this, uint dealPhase)  [virtual]`

Retries placing a great work that Enact could not place.

## Verified from the decompilation
- If the item's stranded index (this+0x90) is not -1, calls ReceiveGreatWork for the receiver again.

## Inferred (not confirmed in-game)
- The retry likely covers deals where other items (e.g. a building or city) create room for the work first. (Medium.)

## For modders
- Shows the game tolerates a short 'work in no city' state and repairs it afterwards.

## Related
- [Diplomacy::Deal::Item::GreatWork::Enact](DealItemGreatWork_Enact.md)
