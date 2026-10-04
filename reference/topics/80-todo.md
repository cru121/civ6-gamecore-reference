---
title: Not yet covered
order: 80
---
# Not yet covered: ripe for analysis

The game library contains more than this reference describes. These are the groups of engine classes we have seen in the function index, counted from the symbol build, that have little or no coverage here. They are leads, not results: **the descriptions below are guesses from class names** and nothing here has been read in detail.

Most of them follow the same pattern as the [modifier effects](effects/index.md) did before they were covered: one class per named type, a small fixed set of functions each, and engine calls that can be followed. If you want to pick one up, see [how to read this reference](conventions.md), then open the group's functions on the [All functions](native/all.md) page; corrections and contributions are welcome.

| Group | Classes in the DLL | What it is (inferred) | In this reference today |
|---|---|---|---|
| [AI behavior tree nodes](#ai-behavior-tree-nodes) | 87 | The building blocks of the computer players' decision trees: one class per node type (`UseGreatPersonNode`, `SpyChooseMissionNode`, `BarbarianSpawnRateNode`, ...) plus the tree and factory plumbing. | Only mentioned in passing. No per-node entries. |
| [AI control contracts and operations](#ai-control-contracts-and-operations) | 17 | How AI subsystems hand work to each other: contracts such as `CivicResearchContract`, `DiplomaticActionContract`, `UnitRequestContract`, and the AI operation, operation team and operation definition classes. | Not covered. (Player and unit operations are covered under Operations and commands; these AI-side classes are separate.) |
| [Gossip types](#gossip-types) | 64 | One class per gossip event (`Denounced`, `CityFounded`, `ReligionFounded`, `SpyCaptured`, ...) and the manager that collects them. | The Lua object `GameGossipManager` is documented; the individual gossip types, their triggers and parameters are not. |
| [Historic moments](#historic-moments) | 54 | The `...MomentDispatcher` classes that decide when a historic moment is awarded, and the moment manager. | The Lua object `GameHistoryManager` is documented. The moment names and hashes are in `findings/tables/moments.tsv` but have no pages here. |
| [Notification types](#notification-types) | 42 | One class per notification type (`BoostTech`, `ChooseCivic`, `ChooseArtifactPlayer`, ...) and the notification manager and pools. | A name and hash table exists in `findings/tables/notifications.tsv`. Not a section of this site. |
| [Diplomacy statements and actions](#diplomacy-statements-and-actions) | 29 | The diplomatic statements (`DeclareFriend`, `DeclareWar`, `Denounce`, `Embassy`, `Delegation`, ...) and the actions that apply their outcome (`SetAllied`, `SetDelegation`, `RenewAlliance`, ...). | Barely covered. Some diplomacy Lua methods are documented; the statement and action classes are not. |
| [Quests](#quests) | 9 | The quest logic classes (`ClearBarbarianCamp`, `SendTradeRoute`, `TrainUnitType`, `RecruitGreatPersonClass`, `TriggerCivicBoost`, ...). | One native function entry; nothing else. |
| [Climate events](#climate-events) | 6 | The climate classes (`Drought`, `Storm`, `OneOff`, `ClimateData`). | Mentioned only as parts of other pages. |
| [Modifier objects](#modifier-objects) | 20 | The kinds of object a modifier can be attached to or can iterate (`Improvement`, `Alliance`, `ArtifactExtraction`, `Belief`, `PlotYields`, `CombatResults`, ...). | The modifier effects, requirements and collections are covered; this object layer is not. |

## Details

### AI behavior tree nodes {#ai-behavior-tree-nodes}

The building blocks of the computer players' decision trees: one class per node type (`UseGreatPersonNode`, `SpyChooseMissionNode`, `BarbarianSpawnRateNode`, ...) plus the tree and factory plumbing.

**Why it looks ripe.** Node names are the part of AI behaviour a modder can see; what each node reads, decides and calls is undocumented. Each class has a small, regular set of functions, so the method that worked for modifier effects (type name, subject, engine calls) should work here too. Whether the trees and their node parameters can be authored from game data is still to be confirmed.

<details><summary>87 classes with their function counts (symbol build)</summary>

`AddGoalTechNode` (3), `ArchaeologistDonateNode` (3), `ArcheologistDigNode` (3), `BarbarianRaidingScoreNode` (2), `BarbarianRecruitNode` (2), `BarbarianRecruiter` (1), `BarbarianSpawnRateNode` (2), `BehaviorTree` (33), `BehaviorTreeControlCallbacks` (1), `Blackboard` (8), `BuildFromCityNode` (3), `BuildImprovementNode` (3), `BuildMilitaryImprovementNode` (3), `BuildProductionNode` (3), `CanAlphaStrikeCityNode` (2), `CancelContractNode` (3), `CheckPlotNode` (2), `ChooseCityForBuildingNode` (2), `ChooseImprovementNode` (2), `ChooseRailroadTarget` (2), `CityAttackUnitsNode` (3), `ClearPlotNode` (3), `ConcurrentNode` (2), `ContractManagerDecorator` (4), `DataEntry` (2), `DecodeTriggerNode` (2), `DifficultyDecorator` (3), `Factory` (9), `FindAvailableUnitNode` (2), `FindTargetsNode` (1), `FindUnitsEvaluator` (1), `HasGreatPersonNode` (2), `HasInquisitionNode` (2), `HasPlayerAbilityDecorator` (2), `HasValidTargetNode` (1), `IntervalDecorator` (4), `IsAtWarNode` (2), `IsCityThreatenedNode` (2), `IsNearFalloutNode` (1), `LaunchInquisitionNode` (3), `LaunchNukesNode` (2), `LockUnitsNode` (2), `LuaScriptNode` (1), `MakeFormationNode` (3), `Manager` (23), `MoveUnitNode` (3), `NavalChooseTargetDecorator` (1), `NavalEscortEvaluator` (1), `NavalPatrolNode` (2), `NavalPillageNode` (1), `NearestCityJob` (1), `NodeData` (5), `NotNode` (1), `NotifyOwnerNode` (2), `OpRecruitEvaluator` (1), `OperationAirstrikeCityNode` (3), `OperationAttackCityNode` (2), `OperationAttackTarget` (2), `OperationAttackUnits` (2), `OperationChangeTarget` (2), `OperationDiplomacy` (3), `OperationGarrisonCityNode` (1), `OperationIsReadyNode` (3), `OperationMakeFormation` (2), `OperationMoveNode` (3), `OperationNavalEscort` (3), `OperationPillageCityNode` (3), `OperationProtectUnits` (2), `OperationSiegeCityNode` (2), `PriorityNode` (1), `ProtectUnitNode` (3), `PurchasePlotNode` (3), `RecruitUnitsNode` (3), `ReservePlotNode` (2), `RunBehaviorTreeNode` (2), `SequenceNode` (2), `SettleActionNode` (3), `SpyAtCityEvaluator` (1), `SpyChooseMissionNode` (2), `SpyDoOperationNode` (3), `SpyMoveToCityNode` (3), `StringTable` (3), `TurnLimitDecorator` (3), `UpgradeUnitsNode` (2), `UseGreatPersonNode` (3), `UseScriptedCommand` (1), `WillUseNukesNode` (2)

</details>

### AI control contracts and operations {#ai-control-contracts-and-operations}

How AI subsystems hand work to each other: contracts such as `CivicResearchContract`, `DiplomaticActionContract`, `UnitRequestContract`, and the AI operation, operation team and operation definition classes.

**Why it looks ripe.** Small groups with descriptive names. They explain how the AI turns a goal into a request, which is useful to anyone changing AI behaviour.

<details><summary>17 classes with their function counts (symbol build)</summary>

`Callbacks` (1), `CivicResearchContract` (8), `Contract` (8), `DiplomaticActionContract` (8), `Factory` (6), `Handle` (13), `Instance` (3), `Manager` (28), `PurchasePlotContract` (7), `TechResearchContract` (9), `UnitRequestContract` (19), `Operation` (30), `OperationConditionFunctions` (4), `OperationDef` (5), `OperationEvaluator` (8), `OperationTeam` (17), `OperationsListReader` (1)

</details>

### Gossip types {#gossip-types}

One class per gossip event (`Denounced`, `CityFounded`, `ReligionFounded`, `SpyCaptured`, ...) and the manager that collects them.

**Why it looks ripe.** Each type has a name hash and a handler. Listing every type with the code that raises it would show exactly when gossip fires and what it carries.

<details><summary>64 classes with their function counts (symbol build)</summary>

`AgendaKudos` (4), `AgendaWarning` (4), `Allied` (4), `AnarchyBegins` (4), `ArtifactExtracted` (4), `BarbarianInvasionStarted` (4), `BarbarianRaidStarted` (4), `BeachResortCreated` (4), `BuildingConstructed` (4), `CampDestroyed` (4), `CityBesieged` (4), `CityFounded` (4), `CityLiberated` (4), `CityRazed` (4), `CityStateInfluence` (4), `ConquerCity` (4), `CulturevateCivic` (4), `DOWMade` (4), `DOWReceived` (4), `DeclaredFriendship` (4), `Delegation` (4), `Denounced` (4), `DistrictConstructed` (4), `Embassy` (4), `EraChanged` (4), `GovernmentChanged` (4), `GreatPersonCreated` (4), `InquisitionLaunched` (4), `LandUnitPromoted` (4), `LaunchingAttack` (4), `Manager` (17), `NationalParkCreated` (4), `NaturalWonderFound` (4), `NavalUnitPromoted` (4), `NewReligiousMajority` (4), `Occurrence` (1), `PantheonCreated` (4), `Pillage` (4), `PolicyEnacted` (4), `PoweredCity` (4), `ProjectStarted` (4), `RandomEvent` (4), `RelicReceived` (4), `ReligionFounded` (4), `ResearchAgreement` (4), `ResearchedTech` (4), `RockConcert` (4), `SettlerCreated` (4), `SpaceRaceProjectCompleted` (4), `SpyBreachDam` (4), `SpyDisruptRocketry` (4), `SpyGreatWorkHeist` (4), `SpyRecruitPartisans` (4), `SpySabotageProduction` (4), `SpySiphonFunds` (4), `SpyStealTechBoost` (4), `TradeDeal` (4), `TradeRenege` (4), `UnitCreated` (4), `VictoryStrategyChanged` (4), `WMDCityStrike` (4), `WMDStrike` (4), `WarPreparation` (4), `WonderStarted` (4)

</details>

### Historic moments {#historic-moments}

The `...MomentDispatcher` classes that decide when a historic moment is awarded, and the moment manager.

**Why it looks ripe.** The trigger conditions are in the dispatcher code. A page per moment (trigger, parameters, engine calls) would answer the most common modder question about moments: why did it (not) fire.

<details><summary>54 classes with their function counts (symbol build)</summary>

`ArtifactExtracted` (2), `BeliefAddedToReligionMomentDispatcher` (2), `BuildingConstructedMomentDispatcher` (1), `CityBuiltMomentDispatcher` (2), `CityChangesReligionMomentDispatcher` (2), `CityPopulationChangedMomentDispatcher` (2), `CityPowerGeneratedFromResource` (2), `CityTransferredMomentDispatcher` (2), `CivicCompletedMomentDispatcher` (2), `CoastalFloodMitigated` (2), `CombatOccurredMomentDispatcher` (1), `DiplomaticVPChanged` (2), `DisloyalCityKeptMomentDispatcher` (2), `DistrictConstructedMomentDispatcher` (1), `EmergencyEndedMomentDispatcher` (2), `GameEraChangedMomentDispatcher` (2), `GovernmentEnactedMomentDispatcher` (1), `GovernorAppointedMomentDispatcher` (2), `GovernorPromotedMomentDispatcher` (2), `HeroCreated` (2), `HeroExpired` (2), `IHistoricMomentDispatcher` (4), `ImprovementConstructedMomentDispatcher` (1), `InquisitionLaunchedMomentDispatcher` (2), `Manager` (16), `Moment` (15), `NationalParkCreatedDispatcher` (2), `OnFindNewContinent` (2), `OnFindWonder` (2), `OnGreatPersonCreated` (2), `OnImprovementDestroyedByUnit` (2), `OnPantheonFounded` (2), `OnPlayerGaveInfluenceToken` (2), `OnPlayerLevyMilitary` (2), `OnPlayersMet` (2), `OnPlotTriggerGoodyHut` (2), `OnUnitTriggerGoodyHut` (2), `OnWarDeclared` (2), `OnWorldCircumnavigated` (2), `ProjectCompletedMomentDispatcher` (1), `RandomEventSeaLevelDispatcher` (2), `ReligionFoundedMomentDispatcher` (2), `ResourceMonopolyGained` (2), `RiverFloodMitigated` (2), `RouteChangedDispatched` (1), `TechCompletedMomentDispatcher` (2), `TradingPostChangedDispatcher` (2), `UnitArmyFormedMomentDispatcher` (2), `UnitCorpsFormedMomentDispatcher` (2), `UnitCreatedMomentDispatcher` (2), `UnitPromotedMomentDispatcher` (1), `UnitTourismBombMomentDispatcher` (2), `WorldCongressResolutionBidSuccessful` (2), `WorldCongressResolutionVoteSuccessful` (2)

</details>

### Notification types {#notification-types}

One class per notification type (`BoostTech`, `ChooseCivic`, `ChooseArtifactPlayer`, ...) and the notification manager and pools.

**Why it looks ripe.** Which engine events raise which notification, and what each one carries, is readable from the classes.

<details><summary>42 classes with their function counts (symbol build)</summary>

`AcknowledgeEmergency` (5), `BoostCivic` (3), `BoostTech` (4), `ChooseArtifactPlayer` (5), `ChooseBelief` (5), `ChooseCityProduction` (6), `ChooseCivic` (5), `ChooseDragnetPriority` (5), `ChooseEscapeRoute` (5), `ChoosePantheon` (5), `ChooseReligion` (5), `ChooseTech` (5), `CityRangeAttack` (5), `CivicDiscovered` (4), `ClaimGreatPerson` (5), `CommandUnits` (5), `CommemorationAvailable` (5), `CongressInSession` (5), `CongressResults` (4), `ConsiderCongress` (5), `ConsiderDisloyalCity` (5), `ConsiderGovernmentChange` (6), `ConsiderRazeCity` (6), `DedicationQuest` (3), `DiplomacySession` (16), `EmergencyHappenings` (4), `FillCivicSlot` (6), `ForeignCityBecameFreeCity` (4), `GiveInfluenceToken` (5), `GovernorAppointment` (5), `GovernorIdleNotification` (5), `GovernorOpportunity` (4), `GovernorPromotionNotification` (4), `Instance` (30), `Manager` (34), `PlayerDefeated` (7), `PlayerNotifications` (15), `PoolType` (1), `PrideMomentRecorded` (4), `PromoteUnit` (8), `ReciprocalPlayer` (4), `TechDiscovered` (3)

</details>

### Diplomacy statements and actions {#diplomacy-statements-and-actions}

The diplomatic statements (`DeclareFriend`, `DeclareWar`, `Denounce`, `Embassy`, `Delegation`, ...) and the actions that apply their outcome (`SetAllied`, `SetDelegation`, `RenewAlliance`, ...).

**Why it looks ripe.** Shows what a statement does when accepted and which state changes follow. Matches the AI and Dev CE diplomacy functions already listed.

<details><summary>29 classes with their function counts (symbol build)</summary>

`Instance` (6), `RenewAlliance` (5), `SetAllied` (3), `SetDelegation` (6), `SetDenounced` (5), `SetEmbassy` (5), `SetFriend` (7), `SetOpenBorders` (4), `SetPromise` (6), `SetWarState` (7), `StatementResult` (6), `DeclareFriend` (5), `DeclareWar` (6), `Defeat` (4), `Delegation` (5), `Denounce` (6), `Embassy` (5), `FirstMeeting` (9), `Greeting` (6), `Instance` (15), `MakeAlliance` (4), `MakeDeal` (17), `MakeDemand` (3), `MakePeace` (5), `OpenBorders` (5), `ProposeAction` (9), `RenewAlliance` (5), `Response` (2), `Warning` (7)

</details>

### Quests {#quests}

The quest logic classes (`ClearBarbarianCamp`, `SendTradeRoute`, `TrainUnitType`, `RecruitGreatPersonClass`, `TriggerCivicBoost`, ...).

**Why it looks ripe.** Nine classes; the conditions that complete a quest and what it rewards are all in code.

<details><summary>9 classes with their function counts (symbol build)</summary>

`BaseQuest` (13), `ClearBarbarianCamp` (6), `ConvertCapitalToReligion` (7), `RecruitGreatPersonClass` (12), `SendTradeRoute` (4), `TrainUnitType` (15), `TriggerCivicBoost` (12), `TriggerTechBoost` (12), `ZoneDistrictType` (11)

</details>

### Climate events {#climate-events}

The climate classes (`Drought`, `Storm`, `OneOff`, `ClimateData`).

**Why it looks ripe.** Small, and tied to the Gathering Storm disaster and climate systems, which have few written explanations.

<details><summary>6 classes with their function counts (symbol build)</summary>

`ClimateData` (50), `ClimateDataHandler` (3), `Drought` (3), `Manager` (48), `OneOff` (2), `Storm` (4)

</details>

### Modifier objects {#modifier-objects}

The kinds of object a modifier can be attached to or can iterate (`Improvement`, `Alliance`, `ArtifactExtraction`, `Belief`, `PlotYields`, `CombatResults`, ...).

**Why it looks ripe.** It is the data model behind collections and requirements, and explains the arguments they receive.

<details><summary>20 classes with their function counts (symbol build)</summary>

`Alliance` (8), `ArtifactExtraction` (11), `Belief` (8), `City` (16), `CombatResults` (12), `Congress` (6), `District` (15), `Emergency` (11), `Game` (6), `Governor` (18), `Improvement` (15), `ModifierObject` (15), `Player` (11), `PlotYields` (15), `PotentialTradeRoute` (10), `ProposedCombat` (11), `Team` (8), `TradeRoute` (12), `Unit` (13), `UnitDeath` (11)

</details>

## Covered, but needs verification

These have pages here, but the pages rest on inference. A contributor can add a verified result without starting from scratch.

| Item | What is inferred | How to verify |
|---|---|---|
| World Builder command classes (41 classes) | The undo model on [World Builder from Lua](worldbuilder.md) is read from function names and the call graph; the `Apply`, `Redo` and `Undo` bodies were not read. | Read the functions of each command in the decompiler and replace the "probably" entries; test undo of one method of each kind in game. |
| Modifier effect links | Which engine functions an effect calls comes from the static call graph of the symbol build ([effects](effects/index.md)). Calls through helpers or pointers are missing. | Hook one engine function and apply a modifier that uses it; compare with the page. |
| Dev CE functions | The descriptions on the [Dev CE](devce/index.md) pages were written by an AI assistant from decompiled code and are not human-reviewed; most behaviour is untested in game. | Review a description against the code, or run the function in a scratch game and report what changed. |
| World Builder method behaviour | Argument forms, return values and silent-failure paths are read from wrappers whose helper functions were not decompiled. | Call the method in a scratch game with each argument form and note the result. |
