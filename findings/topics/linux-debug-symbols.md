# Linux build with DWARF debug info: layout cross-check

Steam depot 533502 (`download_depot 289070 533502` in the Steam console, no manifest needed) is the Linux port of Civ VI. Its
`libGameCore_XP2.so` still carries full DWARF debug info (clang 6, about 1,100 source files, ~140k types, ~109k functions with
parameter names). It is built from the same era as the symbol-bearing Windows build (depot 947510), i.e. **before** the New Frontier
Pass additions: strings such as `LEADER_LUDWIG`, `LEADER_NADER_SHAH` and `NEB_ACHIEVEMENT_01` exist in the current Windows DLL but in
neither the Linux library nor the symbol build.

Extraction: `tools/dwarf_extract.py` -> `linux_depot/out/{functions.tsv,types.jsonl,enums.jsonl}`; lookup: `tools/layout.py <Class> [lo hi]`.
Linux addresses are Linux virtual addresses and cannot be compared with Windows RVAs. Only **struct layouts, member names,
parameter names and header file names** carry over.

## Cross-platform layout rule (Verified on ~12 fields)
For game classes built from `FAutoVariable<T, Owner>` members, **Windows offsets are the Linux offsets minus 8** in the classes
checked (Player::Instance, City::Instance, Game::Culture, Unit::Instance, Player::Diplomacy, Feature::Manager). Types containing
STL/EASTL containers can differ in size (see the Deal item row), so the rule must be checked per class. An `FAutoVariable` wrapper
starts at the member offset and its value is at wrapper+0x10 (this is what `edit()` returns).

## Offsets recorded in earlier findings, checked against the Linux layout
| Recorded (Windows, symbol build) | Linux DWARF member | Result |
|---|---|---|
| Player +0x6d0 -> Cities; +0x6f0 -> Culture; +0x6e0 -> Diplomacy | `m_pkCities` 0x6d8, `m_pkCulture` 0x6f8, `m_pkDiplomacy` 0x6e8 | match (-8) |
| City +0xca0 edit wrapper, Buildings at +0xcb0 | `m_kBuildings` (FAutoVariable) 0xca8 | match (-8) |
| City owner at +0xd8 | `City::IInstance::m_eOwner` wrapper 0xd0, value 0xe0 | match (-8) |
| City +0x268 "highest value" used to choose the new capital | `m_iPopulation` wrapper 0x260, value 0x270 | match: **it is the city's population** |
| Buildings +0xc8 array, 0x20 bytes per entry, slots pointer at entry+0x8, slot 8 bytes, great-work index at slot+4 | `m_aGreatWorkBuildings` 0xc8; `GreatWorkBuilding` size 0x20 {`m_eBuilding` 0, `m_kSlots` 8}; `GreatWorkSlot` size 8 {`m_eSlotType` 0, `m_eGreatWorkIndex` 4} | match |
| Game::Culture record list: wrapper +0x108, begin +0x118 | `Game::Culture::m_kGreatWorks` 0x110 (vector at 0x120) | match (-8) |
| Game great-work record, 0x18 bytes: type +0, player +4, turn +8, text +0x10 | `Game::GreatWork` size 0x18: `m_eType` 0, `m_ePlayer` 4, `m_iTurnCreated` 8, `m_szGreatPersonName` 0x10 | match; **+4 is the creator-side player field named `m_ePlayer`** |
| Unit build charges: wrapper +0x528, value +0x538 | `Unit::Instance::m_iBuildCharges` wrapper 0x530 | match (-8) |
| Diplomacy open-borders counter at +0x490 + player*4 | `m_iOpenBordersFromCount` (StaticArray<int,64>) wrapper 0x488 | match (-8) |
| Diplomacy "turn it ended" at +0x590 + player*4 | `m_iOpenBordersEndedTurn` wrapper 0x598 (value at wrapper+0x10) | **earlier note imprecise**: 0x590 is the wrapper (Windows), the array itself is at +0x5a0. Name: `m_iOpenBordersEndedTurn` |
| Volcano state field at +0x14 (turn stored when activated); tracked list at Feature manager +0x110 | `Volcano::m_iTurnActive` 0x14; `Feature::Manager::m_aVolcanoes` wrapper 0x118 | match; **the field is the turn the volcano became active** |
| Building definition flag 0x8 at +0x158 (capital-move logic) | `Definition::Building` bit-field byte 0x158, alphabetical bits: AdjacentCapital, AdjacentToMountain, AllowsHolyCity, **Capital** (0x8), EnabledByReligion, InternalOnly, IsWonder (0x40), MustBeAdjacentLand | match: **flag 0x8 = `m_Capital`** (the Palace) |
| Great work object type definition +0x40..0x48 = building list | `GreatWorkObjectType::m_BuildingCollection` 0x40 | match |
| Deal item: giver +0x28, receiver +0x2c | `Deal::Item::Instance::m_eFromPlayer` 0x28, `m_eToPlayer` 0x2c | match |
| Deal great-work item: stranded index at +0x90 | `Deal::Item::GreatWork::m_iHeldGreatWork` at 0x8c (object size 0x90) | **differs by +4**: the Windows object is larger (an STL-based member differs); field identified as `m_iHeldGreatWork` |
| Player::Cities list head "+0xd0" (Windows) | `Cities::m_kCities` (`CityList`) at 0xa0, size 0x48 | not comparable: the list type is STL-based and differs |

New field names worth using in docs: `Game::Culture::m_kGreatWorks`, `City::Buildings::m_aGreatWorkBuildings`,
`m_aExtraGreatWorks`, `m_abPillaged`, `m_aeEraCreated`, `Unit::m_iBuildCharges`, `m_iParkCharges`, `m_iActionCharges`.
