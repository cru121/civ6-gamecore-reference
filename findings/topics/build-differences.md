# What changed between the symbol build and the current build (232 "changed" functions)

Method: for each function with no exact byte match (`changed_functions.tsv`), old and new bytes were disassembled and aligned by
instruction sequence (`tools/changed_diff.py`, output `changed_layout_diff.tsv`). Operand differences are classified, and struct
offsets are annotated with member names from the Linux debug info (see `linux-debug-symbols.md`). The new address is a fuzzy
guess, so rows with similarity below ~0.6 are unreliable (likely wrong counterpart or heavily rewritten).

## Result (222 functions with a candidate)
| Class | Count | Meaning |
|---|---|---|
| Aligned instructions differ only in absolute data addresses (constant shifts: +0x2000 for 212 operands, +0x1350 for 23) | 158 (134 with similarity >= 0.9) | The data sections moved. **But this class ignored inserted/removed instructions**: a strict re-check (identical instruction sequence, all data operands verified) left only 85 functions at similarity >= 0.9; 58 of those were already mapped by the call graph and 27 were newly mapped (see below) |
| No operand differences but instructions added/removed | 32 | Logic changes (see list below) |
| Struct field offsets differ | 32 | Layout and logic changes |

## Verified: a new combat-modifier flag (one byte) was inserted
`Unit::CombatModifiers` (old layout from the Linux DWARF: ... `m_bCaptureCombatUnits` 0x7f, `m_bCanForceRetreat` 0x80,
`m_bIgnoreRangedVsDistrictPenalty` 0x81, `m_bFightWhileEmbarked` 0x82) has **one more bool in the current build**: its
`Serialization::operator<<`/`>>` and `toString` read offsets 0x80, 0x81, 0x82 in the old build and 0x81, 0x82, 0x83 in the new one.
Everything that reads a unit's flags after it shifts by one byte, e.g. `Unit::Instance+0x821 / 0x822` -> `0x822 / 0x823` in
`GetBaseMoves`, `GetCombat`, `GetMaxMoves`, `Combat::Manager::GetBestDefender/GetBestAntiAir`, `Rules::Combat::Instance::CanAttackTarget`,
`CanPillage`, `CanFightWhileEmbarked`, `GetDefenseStrengthModifier`, `GetAmphibiousAttackPenalty`, `CalculateDamage` and
`Unit::Commands::PriorityTarget::CanStart`, `XP2::PlunderTradeRoute::CanStart`. (A smaller shift 0x216 -> 0x217 appears in `AI::GlobalAi::Initialize`.)
The new byte is identified, see the next section (corrected: it is inserted at struct offset 0x81, after `m_bCanForceRetreat`).
Modder relevance: any external tool or patch that hard-codes CombatModifiers offsets for the current build needs +1 after 0x7f.

## Logic changes without layout changes (Inferred from instruction count; not yet read)
Turn-ending: `Messages::CivicsCommand::Execute`, `Messages::GameTurnComplete::Execute`, `Messages::PlayerTurnComplete::Execute` (offsets also changed),
`Messages::Manager::HandleSendTurnUnready`, `Reporting::Notification::Manager::GetEndTurnBlocking`, `HasEndTurnBlocking`.
Rivers and volcanoes: `Map::Plot::Instance::IsRiverCrossingFlowClockwise`, `UpdateRiverCrossing`, `Map::Feature::Manager::EruptVolcanoNaturalWonders`,
`SpreadNaturalWondersYields`, `WorldBuilder::Map::Manager::EditRiver`.
Religion and cities: `City::Religion::RecomputeFollowers`, `RecomputeFollowersForList`, `City::Instance::CanBuildUnitsOfDomain`.
Improvements: `Map::Improvement::Builder::CanHaveDistrict`, `CanHaveImprovement`.
Combat: `Rules::Combat::Instance::CalculateExperienceEarned`, `GetAirSupportBonus`, `GetAttackStrengthModifier`, `GetDefenseStrengthModifier`,
`Rules::Movement::Instance::GetDiplomaticTerritory`. Others: `Player::Operations::Manager::Process`, `Player::Techs::TriggerBoost`,
`Unit::Instance::Initialize`, `Unit::Commands::XP2::CondemnHeretic::CanStart`, `AI::Espionage::GetUnitOperationType`.
Leads: `Player::Techs::TriggerBoost` and `Player::Operations::Manager::Process` are in our Great-Works/relic area of interest
(`Process` is one of the creation paths of `SetGreatWorkPlayer`), so re-read them before relying on the old-build analysis.

## Caveat
Offsets in `City::Instance::GetManagedPlots`, `Map::River::Manager::TriggerEvent`, `Feature::Manager::TriggerEvent` and similar low-similarity
rows are probably artefacts of a wrong counterpart. Only similarity >= 0.9 rows were treated as findings above.

## Folded into the old->new map (2026-09-30)
Strict rule (`tools/fold_datashift.py`): similarity >= 0.9, identical mnemonic/operand-shape sequence, every differing operand an absolute data
address, no struct-sized displacement change, the new address not already claimed. Result: 15 functions as `datashift-verified`
(data shifts confirmed against `old_to_new_data.tsv`), 12 as `datashift-probable` (sequence identical, data map had no entry to confirm).
Three identical-template clones (`rapidxml::xml_document::parse_element<1029/1092/1093>`) were left out: they map to the same address.
**Four existing call-graph entries had nonsense addresses** (negative or > 16 MB): `Map::Plot::Instance::IsAdjacentNotOwnedByPlayer`,
`Map::Improvement::Builder::ValidAdjacentTerrain`, `Map::Feature::Manager::SpreadYields` (now `datashift-verified`) and
`Builder::InvalidAdjacentFeature` (now `fuzzy-best`, similarity 0.95, sequence differs slightly). The previous map is saved as
`old_to_new_offsets.tsv.bak_before_datashift`.

## Re-check of `Player::Operations::Manager::Process` and `Player::Techs::TriggerBoost` (2026-09-30)
Method: the old function (symbol build RVA 0x30c120, 1789 instructions) and the current one (RVA 0x30d330) were disassembled and aligned
instruction by instruction (no Ghidra import of the current DLL was needed; the two bodies are otherwise byte-for-byte identical in
instruction sequence, apart from the shifted internal call targets, +0x1210).

**Process - Verified:** exactly one code change. After the city lookup in the artifact branch, the current build adds
`test rax, rax / je <end of branch>` before using `city + 0xcb0` (the city's `Buildings`, see `linux-debug-symbols.md`). The old
build dereferenced the result unchecked. So the current build **guards against the city no longer existing** when an artifact is placed.
**Process - Verified, old findings hold:** the branch is unchanged: `Game::Culture::SetGreatWorkPlayer(greatWorkIndex, player)`
(old 0x1c9890, now 0x1c8c80) -> `AddArtifactToBuilding` -> reporting event -> city lookup -> `Buildings::GetFreeSlot`, followed by
the same two `RemoveGreatWork` and two `AddGreatWorkToSlot` calls. Hence `SetGreatWorkPlayer` is still only called on creation paths
(including this artifact operation), not in trades, exactly as recorded in `Culture_SetGreatWorkPlayer.md`.
**Inferred:** `Player::Districts::Find` in the symbol names is identical code to the city lookup (`Player::Cities::Find`); the linker
folded them, so the symbol name is unreliable here (the call reads `[player+0x6d0]`, the Cities object).

**TriggerBoost - Verified:** one change: a `test edi, edi / jle <skip>` guard was added before the code that reads a value at `[this+0xa8]`
(a per-boost value). **Inferred:** a positive-value guard, probably against a zero or negative boost amount. Not relevant to Great Works.

## The new CombatModifiers flag: "no barbarian XP limit" (2026-09-30)
**Layout (Verified by the modifier Apply/Remove stores and by the readers):** in the current build `Unit::CombatModifiers` is
`... m_bCaptureCombatUnits 0x7f, m_bCanForceRetreat 0x80, **NEW 0x81**, m_bIgnoreRangedVsDistrictPenalty 0x82, m_bFightWhileEmbarked 0x83`
(old build: 0x80, 0x81, 0x82). The struct sits at `unit + 0x7a0` (wrapper at `unit + 0x790`), so the new flag is the byte at **unit+0x821**.
Only one function reads it: `Rules::Combat::Instance::CalculateExperienceEarned`; the small modifier-effect function at 0x8f4100
(vtable slot at 0xa6b8d8, `lea rcx,[unit+0x790]` -> `edit()` -> store at +0x81) and its `Remove` at 0x8f49f0 write it. The symbol-build map had
labelled these `AdjustUnitIgnoreRangedVsDistrictPenalty::Apply/Remove` (map category `unique-reordered`): that label is wrong for the
current build, the real IgnoreRanged/FightWhileEmbarked functions now store 0x82/0x83.

**What the flag does (Verified from the diff, reasoning Inferred):** `CalculateExperienceEarned` has a branch for combat against
Barbarians or Free Cities (`Player::IsBarbarian` / `IsFreeCities`). There, if the unit's level is at least
`EXPERIENCE_MAX_BARB_LEVEL` (GlobalParameters +0x314, verified by the Linux layout: `m_EXPERIENCE_MAX_BARB_LEVEL` at 0x314), the
XP result is `EXPERIENCE_BARB_SOFT_CAP` (+0x2fc). The current build inserts `cmp byte [unit+0x821], 0 / jne <normal XP>` for both the
attacking and the defending unit, so **a unit with the flag set skips the barbarian XP limit and earns normal XP**.
**Name (was inferred, now confirmed below):** the only new modifier-effect string in the current DLL is `EFFECT_ADJUST_UNIT_NO_BARB_XP_LIMIT`
(with the new argument string `NoLimit`); no other new string relates to a unit flag. So a modifier effect of that name
sets this flag. Modder relevance: the current game can grant "no barbarian XP limit" through a modifier; earlier game versions cannot.
**Confirmed by the game data (Verified):** `DLC/JuliusCaesar/Data/JuliusCaesar_Leaders.xml` defines the modifier
`TRAIT_CAESAR_NO_XP_LIMIT` with type `MODIFIER_PLAYER_UNITS_ADJUST_UNIT_NO_BARB_XP_LIMIT` (`COLLECTION_PLAYER_UNITS`, effect
`EFFECT_ADJUST_UNIT_NO_BARB_XP_LIMIT`). So the flag is Julius Caesar's ability, and the name is confirmed. Modders can reuse that
modifier type on any player's units.
