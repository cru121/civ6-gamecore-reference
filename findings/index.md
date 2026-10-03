# Findings index

One file per analyzed function in `functions/`; longer explanations in `topics/`.

## Topics
- [Moving a great work between cities and players](topics/great-works-moving.md)
- [Do great works in limbo grant anything?](topics/great-works-limbo.md) (observed in game)
- [Linux debug info: struct layout cross-check](topics/linux-debug-symbols.md)
- [Event ids, hash constants, config keys, typed globals](topics/events-hashes-and-data-symbols.md)
- [Operations and commands: hash -> handler map](topics/operations-and-handlers.md)
- [Lua API coverage vs community reference](topics/lua-api-coverage.md)
- [Comparison with the Community Extension wiki](topics/ce-wiki-comparison.md)
- [Build differences: what changed in the current build](topics/build-differences.md)
- [Relics with no slot, and keeping them anyway](topics/relics-and-archive.md) (verified in game)
- [How great works get lost: capture, destruction, capital move, building removal](topics/great-works-loss-paths.md) (from the code)
- [Ghost slots: a work held by a building the city no longer has](topics/ghost-great-work-slots.md) (observed in a real save)
- [Game/Player properties: where SetProperty data lives](topics/game-properties-storage.md) (from the code)
- [How great works are traded (deal items, validation, enact)](topics/great-work-trading.md) (from the code)
- [Reading great work records from UI Lua: what is safe](topics/ui-great-work-records.md) (crash observed)
- [Leads not yet analyzed](leads.md)

## Functions

### City / great works
- [Rules::Cities::Shared::Instance::RelocateBuildingGreatWorks](functions/Rules_RelocateBuildingGreatWorks.md) `0x64d980` - Re-homes great works after a building replacement; drops them silently if nothing fits.

- [City::Buildings::RemoveGreatWork](functions/Buildings_RemoveGreatWork.md) `0x10d370` - Clears the slot that holds a given great work in a city. Returns the slot number it was in, or -1 if this city does not hold it.
- [City::Buildings::IsInCity](functions/Buildings_IsInCity.md) `0x10cc60` - True if a great work with this index sits in any slot of any building in this city.
- [City::Buildings::AddGreatWork](functions/Buildings_AddGreatWork.md) `0x109290` - Places a great work into the first empty slot in the city that accepts its object type.
- [City::Buildings::AddGreatWorkToSlot](functions/Buildings_AddGreatWorkToSlot.md) `0x1099b0` - Places a great work into a specific building's slot. A negative slot means 'first empty slot in that building'.

### Diplomacy / great works

- [Diplomacy::Deal::Item::GreatWork::Enact](functions/DealItemGreatWork_Enact.md) `0x585f00` - Executes a great-work trade item: takes the work out of the giver's city and gives it to the receiver.
- [Diplomacy::Deal::Item::GreatWork::PostEnact](functions/DealItemGreatWork_PostEnact.md) `0x586860` - Retries placing a great work that Enact could not place.

### Game / great works
- [Game::Culture::AddRelic](functions/Culture_AddRelic.md) `0x1c6b80` - Chooses, creates, places and announces a relic.
- [Game::Culture::FindOrAddGreatWork](functions/Culture_FindOrAddGreatWork.md) `0x1c80e0` - Finds or creates the game-wide record for a great work; documents the 0x18-byte record layout.

- [Game::Culture::SetGreatWorkPlayer](functions/Culture_SetGreatWorkPlayer.md) `0x1c8c80` - Writes a player id into the game-wide great work record.

### Map / volcanoes

- [Map::Feature::Manager::SetVolcanoActive](functions/Feature_SetVolcanoActive.md) `0x7271e0` - Randomly activates one dormant volcano, if fewer are active than intended. It does not take a target volcano.
- [Map::Feature::Manager::SetVolcanoInactive](functions/Feature_SetVolcanoInactive.md) `0x727540` - Randomly deactivates one active volcano. Mirror of SetVolcanoActive.

### Player / diplomacy

- [Player::Diplomacy::SetHasOpenBordersFrom](functions/Diplomacy_SetHasOpenBordersFrom.md) `0x2b0360` - Grants (+1) or revokes (-1) open borders from another player. It is a counter, not a flag.

### Player / great works

- [Player::Culture::ReceiveGreatWork](functions/Culture_ReceiveGreatWork.md) `0x282c20` - Gives a great work to a player by placing it in the first of their cities that can hold it. Returns false if no city has room.

### Player / religion / great works
- [Player::Religion::GetNearestRelicSlot](functions/Religion_GetNearestRelicSlot.md) `0x315270` - Finds the city with a free relic slot nearest a plot; null when none.

- [Player::Religion::CreateRelic](functions/Religion_CreateRelic.md) `0x314710` - Creates a relic near a plot and places it in the nearest relic slot.

### Unit

- [Unit::Instance::ChangeBuildCharges](functions/Unit_ChangeBuildCharges.md) `0x3a2980` - Adds a (possibly negative) amount to a unit's remaining build charges, never going below 0.
