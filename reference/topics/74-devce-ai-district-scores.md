---
title: AI district scores - CE_AI* policy API (Dev CE, by henno)
order: 74
---
# AI district scores: the `CE_AI*` policy API in Dev CE

**Availability.** Needs the **Dev CE** GameCore mod **0.9.0-experimental or newer** (Steam build **26595377**, Windows, Gathering Storm), single player. The work is **henno's** (hennogous, repository `hennogous/CivilizationVI_CommunityExtension`, branch `csc-dev`, used by his Civ Supply Chains mod). It was grafted into Dev CE by cru121 and released in 0.9.0-experimental. It is **inert until a mod publishes a policy**: no shipped mod uses it yet. Nothing on this page was run in game by this reference (see "Tested").

## What the engine does (as far as the code shows)
The AI keeps, per city, a matrix of district values per candidate plot. The module hooks six native functions around that machinery (names are the module's own labels):
* **District NetValue**: the per-plot value of one district. Early policy entries add a delta to its result, but only for the caller whose return address is the plot-analysis row code.
* **CalculateDistrictValues**: aggregates the per-plot values after building forecasts. Late and final entries are written here.
* **GetBestDistrict**, **District PresentValueOf**: read-only observers (winner and plot-specific value), used for the trace journal (inferred from the code and comments).
* **District Location** and **Quarter Request Value**: used by managed types (below) to place and re-price new-district requests (inferred from the code and comments).
The engine keeps legality, reservations and production competition. CE only changes numbers in cells the engine already considers eligible (owned, district-eligible, unreserved), and re-checks the publication generation after the original routine returns. Hooks never call Lua. How the stock AI weighs the numbers is not described by the module (it only states that "Civ owns legal locations, reservations and production competition").

## The Lua API
All are globals on the gameplay Lua state. Mutating calls return 1 on success, 0 on rejection (from the graft docs). Values are **Q8 utility**: 256 Q8 = 1 utility, not yields. Plot index is y*width+x.

| Function | Arguments | Meaning |
|---|---|---|
| `CE_AIDistrictScoresBegin` | version, width, height, districtCount | Disable the old policy, open empty staging. Version must exceed the published one |
| `CE_AIDistrictScoresAllow` | player | Admit one AI player (0-63) |
| `CE_AIDistrictScoresEntry` | player, city, district, plot, deltaQ8 | Early additive adjustment (NetValue hook) |
| `CE_AIDistrictScoresLateEntry` | player, city, district, plot, expectedBeforeQ8, expectedFinalQ8, deltaQ8 | Additive adjustment after aggregation, guarded by the expected scores |
| `CE_AIDistrictScoresFinalEntry` | player, city, district, plot, valueQ8 | Replace the whole eligible cell with a complete value (-4096..4096 utility) |
| `CE_AIDistrictScoresManagedType` | player, district, defaultQ8 | Declare that this type's new-district valuation is fully managed; default -4096..0 utility |
| `CE_AIDistrictScoresCommit` | none | Publish the staged table atomically |
| `CE_AIDistrictScoresDisable` | none | Retire policy and staging, advance generation |
| `CE_AIDistrictScoresStatus` | none | JSON: readiness, counters, first 64 samples, trace metadata |
| `CE_AIDistrictScoresReceipt` | version, player, city, district, plot | Read one key's outcome |
| `CE_AIDistrictScoresManagedReceipt` | version, player, district | Counters for one managed type |
| `CE_AIDistrictScoresTraceCount` / `TraceRead` | none / offset, limit, expectedGeneration | Page through the native journal (capacity 16384) |
| `CE_AIDistrictDeclineStage` / `Status` / `Receipt` | player, city, district, plot / none / version, player, city, district, plot | Withhold one exact cell from a fresh joint district comparison (capacity 4096) |
| `CE_AIDistrictRepairStage` / `Status` | player, city, district, plot / none | Offer one existing footprint for repair admission (up to 256) |
| `CE_AISupplierExclusionStage` / `Status` | player, city, plot / none | Exclude a site from the stock selector (up to 256) |
| `CE_AIDistrictPurchaseCompletionStage` / `Status` / `Receipt` | player, city, district / none / version, player, city, district | Numeric scope that acknowledges purchase completion; no purchase or score |
| `CE_AIBuilderProtectionAllow` / `Bid` / `Status` | player, city, plot, improvement (, deltaQ8) / none | Keep an improvement eligible at a protected site, optionally with a 0..64 unit bid |
| `CE_AIBuilderHarvestProtectionStage` / `Status`, `CE_AISupplierWonderProtectionStage` / `Status` | none | Opt staged supplier sites into harvest or wonder protection |
| `CE_AIWonderPlacementOffer` | player, city, building, plot, deltaQ8 | Site preference for an exact wonder (max 512, positive up to 6144 Q8) |
| `CE_AIBuildingNominationBid` / `QueueBid` / `Status` / `Receipt` | player, city, building, deltaQ8 (, queueDeltaQ8) | Building nomination bids (max 512 utility) |
| `CE_AIMaterialResearchBid`, `CE_AIMaterialBuilderRequestBid`, `CE_AIMaterialWorkerFinishOffer`, `CE_AIMaterialWorkerLoanOffer`, `CE_AIMaterialDevelopmentStatus` | see native README | Research, builder-request and worker offers (four per AI player) |
| `CE_AIEconomyStatus`, `CE_AIEvaluationContext` | none | JSON readiness and the AI's horizon and discount |
| `CE_AIYieldStreamValue`, `CE_AIYieldIntervalValue`, `CE_AIYieldFixedValue`, `CE_AIAmenityStreamValue`, `CE_AIAmenityIntervalValue`, `CE_AIPseudoYieldIntervalValue`, `CE_AIGrowthIntervalValue` | player, city, ... timing and discount | Read-only quotes in Q8 utility using the engine's own pricing; nil when unavailable |
| `CE_AIDistrictSiteAdjustment` | player, city, district, x, y, ready, horizon, discountQ8 | Read-only: native NetValue minus intrinsic value, as JSON |
| `CE_AIMonotonicSeconds` | none | Read-only fractional seconds, for timing a policy pass |

The registration list is in `RegisterLua`; argument lists for the less central functions are only summarised here, the exact ones are in the module's `native/README.md`.

## How a policy is published and what it can change
1. `Begin(version, width, height, districtCount)` then `Allow(player)` for each AI, then entries, then `Commit()`. Staging is atomic: a rejected Allow or entry **poisons** the batch and Commit then fails; start again with Begin.
2. Per pair (player, city, district, plot) there can be one entry of any kind (early, late or final). At most 4096 entries. Early/late deltas are -262144..+1048576 Q8 and nonzero. A managed type cannot also have early or late entries.
3. Early entries adjust the native NetValue; late entries need expected before/after scores and apply only if the engine's value matches; final entries replace the cell (zero and negative allowed). Native sentinel values (at or below -2559744 Q8) are never revived, and reservations are not created or changed.
4. Managed types give a whole district type a conservative default plus sparse complete bids, so cities without a quote still get a value; non-positive managed placements are masked only during selection and restored.
5. What it cannot do: it does not build, order, buy or place anything. The native selector still decides; a write is not a selection. The consuming mod owns valuation and excludes original humans (the allowlist does not discover them).

## Engine facts and offsets the code relies on
The module qualifies the exact image before installing anything: SHA-256 of the GameCore image (prefix `092abfbb2176f8df`, as given in the module's README; the exact file name is not established), PE timestamp, image size 12976128, and byte-prefix fingerprints of every hooked function; the aggregation call site must still be a rel32 CALL to our hook. Any mismatch leaves the API unavailable and the hooks uninstalled. Hook groups use `Runtime::InstallHookGroup`: all trampolines are created before any hook is enabled, and a failure rolls the group back. The NetValue detour uses an assembly shim (`hook_entry.asm`) that preserves R12 (the caller's plot-analysis row) and the seven original arguments.

| RVA | Function (module label) |
|---|---|
| `3df7a0` | CalculateDistrictValues |
| `3e21fc` | aggregation call site inside DoTurnActivate (return address named in the code) |
| `3e4310` | GetBestDistrict |
| `3e4e10` | District Location |
| `3e7800` | District PresentValueOf |
| `3fa5c0` | Quarter Request Value (RequestUpdate) |
| `52a420` | District NetValue |
| `5bdb00` | RegisterScriptData (fingerprint only; CE's own hook) |

Other RVAs (pricing helpers, builder, wonder, repair hooks) are named constants in `native/target_identity.h`. The native README quotes older XP2 addresses in dated sections (for example `52a440` for NetValue); the constants above come from the current `target_identity.h`.

## Pitfalls and limits
* Argument conversion can longjmp out of a Lua call; the docs say callers must catch the error and call `Disable` after any partial or rejected publication.
* Versions must increase within a game context. Width and height 1-256, districtCount 1-4096, player 0-63.
* `Reset` runs at game-context boundaries: the policy is dropped, but hooks stay installed (they are process-owned and the DLL is pinned). Engine caches and requests already in a save are not undone.
* Optional parts (pricing, builder, wonder, repair, ownership) disable independently if their own fingerprint fails; the district scores can stay available.
* Presence of a function does not mean readiness: read `Status` / `CE_AIEconomyStatus`. Quotes return nil when unavailable; never treat nil as zero.
* The module's README states its support as Windows, DX11, Gathering Storm, build 26595377; other platforms and builds are outside it, and whether the DX12 exe matters for it is not established here.
* Writes are bounded by a journal and a 4096 change budget; exhausting them fails closed.

## Tested
* **Inert by default** (code: `enabled` stays false until a Commit succeeds; hooks fall through to the original).
* Ported to Steam build **26595377** and builds into Dev CE. Whether the module's image check passed on a given install and which of its hooks installed was **not checked by this reference**; look for the module's lines in `DevBridge.log` and read `CE_AIDistrictScoresStatus`.
* **Its behaviour with a published policy was not tested here.** The native README reports henno's own synthetic checks and in-game smoke runs with his mod; this reference did not reproduce them, and those results say transport works, not that AI placement improves.

*Key addresses (named constants in `native/target_identity.h`): `DistrictNetValueRva` 0x52a420, `CalculateDistrictValuesRva` 0x3df7a0, `DistrictAggregationCallRva` 0x3e21fc, `GetBestDistrictRva` 0x3e4310, `DistrictPresentValueRva` 0x3e7800, `DistrictLocationRva` 0x3e4e10, `RequestUpdateRva` 0x3fa5c0.*
