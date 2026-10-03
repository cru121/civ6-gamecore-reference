# Lua methods whose gameplay wrapper calls a constant-zero stub

**Status:** Verified in the symbol-build DLL (disassembly) and, for TradeManager, in the Linux build (function sizes). Not tested in game.

The compiler folds identical functions, so a function that only returns zero shows up under one arbitrary name in the symbol build: `Cache::City::CulturalIdentity::GetIdentityPerTurnFromNearbyOwnedCities` at old rva `0x36f090` is `mov dword ptr [rdx],0 ; mov rax,rdx ; ret` (returns a FixedPoint 0). That label is meaningless for the methods that call it, and it is what mislabelled the gameplay-state `TradeManager` signatures.

## Verified
Wrappers (symbol build) whose direct callee is a zero-returning stub (scan of every registered wrapper against the call graph, `docs_proto/tools/lua_signatures.py: stub_callee`):

| Lua method (state) | Stub |
|---|---|
| TradeManager.CalculateDestinationYieldFromPath, ...FromPotentialRoute, ...FromAttachingResource (gameplay) | returns FixedPoint 0 |
| TradeManager.CalculateOriginYieldFromAttachingResource (gameplay) | returns FixedPoint 0 |
| TradeManager.CalculateDestinationYieldsFromPath, ...FromPotentialRoute, ...FromAttachingResource and CalculateOriginYieldsFromAttachingResource (gameplay, one shared wrapper body) | returns a table of zeros, one per yield type (the callee, old rva `0x3889f0`, builds a zero and calls `Types::Vector<FixedPointT<8>>::assign(count of Definitions::GetYieldDefinitions, 0)`) |
| PlayerCulture.GetIncrementingBonus, GetIncrementingBonusIncrement (UI) | returns 0 (callee `xor eax,eax; ret`; 3 bytes in Linux) |
| PlayerCulture.GetIncrementingBonusInterval, GetIncrementingBonusTurnsUntilNext (UI) | returns 1 (`mov eax,1; ret`; 6 bytes in Linux) |
| Plot.IsCanyon (gameplay) | returns false (`xor al,al; ret`; 3 bytes in Linux) |

The government-screen "heritage" meter (`GovernmentScreen.lua` lines 394-397, 437, 442) reads exactly the four PlayerCulture values above. With bonus 0 and interval and turns-until-next both 1 the `> 0` branch never shows an incrementing bonus: the feature is switched off in the engine.

In the Linux build the matching gameplay `Trade::Manager` functions (`CalculateDestinationYieldFromPath`, `...FromPotentialRoute`, `...FromAttachingResource`, `CalculateOriginYieldFromAttachingResource`) are 16 bytes long, the same size as a stub, while their `Origin...FromPath` / `FromPotentialRoute` / `...FromModifiers` siblings are 237 to 1071 bytes.

### Checked and not stubs
The first scan also flagged `Plot.IsOpenGround`, `Plot.IsRoughGround` and `CityCulturalIdentity.GetIdentitySourcesBreakdown` / `GetIdentitySourcesDetailedBreakdown`. Those are real: `IsOpenGround` and `IsRoughGround` call the always-false `IsCanyon` as one term of a larger condition (hills, terrain mask, flag bit), and the identity breakdown wrappers (12 KB of code) call several folded zero functions (nearby owned cities / governors) as terms of a longer sum, so only those terms are constant. The generator now ignores a stub whose result is branched on or that sits in a wrapper with more than 16 callees.

## For modders (inferred)
From a gameplay script, `TradeManager:CalculateDestinationYieldFromPath/PotentialRoute/AttachingResource` and `CalculateOriginYieldFromAttachingResource` probably always return 0; the Modifiers variants are real. The UI-state registrations call the `Cache::` implementation and do compute values. If a script needs the destination yield of a route, use the UI-side function or the Modifiers variant. Not run in game. The plural variants (`CalculateDestinationYieldsFromPath/PotentialRoute/AttachingResource`, `CalculateOriginYieldsFromAttachingResource`) were checked in the symbol build: the gameplay callee fills a result table with one 0 per yield type, so they return all-zero yields. They are 63 bytes in Linux, consistent. `CalculateOriginYieldsFromPath/PotentialRoute/Modifiers` and `CalculateDestinationYieldsFromModifiers` are real implementations (471 to 4235 bytes).

## Whole-index scan (all 43,803 functions)

Tools: `tools/const_stub_index.py` (symbol-build DLL), `tools/const_stubs.py` and `tools/const_stub_users.py` (Linux build with names), `tools/const_stub_lua2.py` (wrapper to helper to stub). Tables: `findings/tables/constant_return_stubs.tsv`, `constant_return_lua_methods.tsv`, `constant_return_functions_linux.tsv`.

### Verified (symbol-build DLL)
- Only **68** functions of the index have a body of 12 bytes or less that returns a constant. The compiler merged identical ones, so each body carries one arbitrary label. 59 of them return a hash-like value (type ids from `GetType`/`GetOperationHash` style functions), which are framework, not disabled features.
- The shared bodies with real callers: `0x478f10` returns 0 (9 callers), `0x852e70` returns false (16 callers), `0x36f090` returns FixedPoint 0 (13 callers), `0x8801d0` returns true and `0x53c780` returns 1 (used everywhere as predicate defaults and CRT helpers, not meaningful).
- A second Lua method found by looking one level deeper: **`PlayerCulture:GetEnactPolicyCost(policy)`** (UI state). `Cache::Player::Culture::GetEnactPolicyCost` resolves the policy and returns the zero stub (also returns 0 when the policy is unknown), and the Linux `Player::Culture::GetEnactPolicyCost` is a 3-byte `return 0`. The game's own `CivicsTree.lua:2046` and `GovernmentScreen.lua:2404` have the call commented out. So policy enact cost is always 0.
- Callers of the false stub `0x852e70` include `Map::Improvement::Builder::CanHaveDistrict/CanHaveImprovement/CanHaveWonder`, `City::Manager::CreateUnit`, `City::Gold::CanPlaceUnit`, `Formation::Movement::PathCost`, `Map::Area::Builder::Calculate` and `AI::CityPlotEvaluation::Execute`. Because the stub body is shared with other always-false functions (for example `Plot::IsCanyon` and virtual "no" defaults) we cannot say which logical function each one calls, only that those functions test something that is always false in this build. `Cache::Player::Culture::CanPolicyBeSlotted`, `IsPolicyUnlocked` and `IsGovernmentUnlocked` begin with a test of the always-true stub; the branch that depends on it is dead code, the real check always runs.

### Cross-check of the Linux candidates against the Windows build
Method: the Ghidra project keeps every symbol of a merged function (`tools/AliasSymbols.java` writes them to `linux_depot/out/alias_symbols.tsv`; the function index only shows one name per address). `tools/const_stub_cross.py` matches each Linux constant-return function to its Windows symbol by mangled name and reads the Windows body. Result for all 927 non-framework Linux candidates is in `findings/tables/constant_return_linux_vs_windows.tsv`: 328 rows are a constant in the Windows build too (about 60 of them are type-id getters), 14 are not constant there, and 585 have no Windows function of that name (the compiler inlined them, or the function does not exist there).

**Verified in both builds** (Windows body is `xor eax,eax; ret` / `xor al,al; ret` / `mov al,1; ret` and so on):

| Function | Returns |
|---|---|
| `Map::Plot::Instance::IsCanyon`, `HasSpecialImprovement` | false |
| `Player::Culture::GetEnactPolicyCost`, `Cache::Player::Culture::GetIncrementingBonus` and `...Increment` | 0 |
| `Cache::Player::Culture::GetIncrementingBonusInterval` and `...TurnsUntilNext` | 1 |
| `Game::HeroesManager::IsHeroUnitSpawnAtHolySite` | false |
| `Congress::Policy::IsVotingAllowed` | false |
| `Unit::Operations::MakeTradeRoute::CanBeInterrupted`, `Unit::Operations::Manager::IsDoingPartialMove` | false |
| `Diplomacy::Deal::Item::Instance::GetAmount`, `GetMinAmount`, `GetMaxAmount` (base defaults) | 0 |
| `Diplomacy::Deal::Item::Instance::IsMutuallyExclusiveWith` | false |
| `Congress::Policy::GetPolicyType` | -1 |
| `Exports::GameReligion` `HasBeenFounded`, `HasBeliefEachType`, `IsInSomePantheon`, `IsInSomeReligion`, `IsNewTypeForReligion`, `IsTooManyForReligion` (all false), `GetReligionsSize` (0) | the export interface of the religion data is empty |
| `Exports::GameGreatPeople::GetTimelineSize` | 0 |
| `Exports::Unit::GetGender`, `GetCulture` | -1 |

The `Exports::` classes look like an external query interface (not the Lua API); they are stubs in both builds.

**Linux only (no Windows function of that name; inlined or absent), so not confirmed:** `Unit::Instance::IsSuicide`, `IsCargo`, `GetNoDefensiveBonusCount`; `Unit::Placement::CanShareLocation`; `Trade::Manager::IsInstantRoadPlacement`; `Map::Plot::Instance::IsAllowImpassableMovement`; `Game::Eras::GetThresholdShiftFromGovernment`; `Player::Religion::CanAffordPlot` (Windows only has `Player::Treasury::CanAffordPlot`, a different function); `Quests::Logic::ClearBarbarianCamp::GetMaximumCampDistance` (5); `Map::River::Manager::GetDefaultFloodDuration` (1); `Game::NameManager::CanUseUnusedCivilizationCityNames` (true); and the `CalculateScore` of the Kublai and Trieu agendas (their classes exist in Windows, but there is no `CalculateScore` function for them there, so the base behaviour applies).

None of the confirmed functions other than the ones in the first table has a Lua registration under the same name. Treat all of this as leads: not run in game.
