---
title: AI behavior trees
order: 76
---
# AI behavior trees: the data-driven node graph and its Lua nodes

Gap addressed: "AI behavior tree nodes" in the reference TODO (87 `GameCore::AI::BehaviorTree::*` classes, node semantics unknown, unclear whether trees are authorable from data).

## Verified (read from files and static code, plus the in-game tests described below)
* The trees are game data. `Base/Assets/Gameplay/Data/BehaviorTrees.xml` (194 KB) has seven sections: `ShapeDefinitions` (5), `NodeDefinitions` (72), `NodeDataDefinitions`, `DataTypes` (12), `BehaviorTrees` (29 trees), `BehaviorTreeNodes` (583 rows: tree, node id, `NodeType`, `JumpTo`), `TreeData` (per-node parameter values: `DefnId`, `Tag`, `DefaultData`).
  Schema tables: `BehaviorTrees`, `BehaviorTreeNodes`, `Beliefs`, `TriggeredBehaviorTrees(TriggerType, TreeName, OperationName, AIEvent, Priority)`.
* Engine side (Linux DWARF names): `Factory::RegisterComponent(id, CreateFunc)`, `Factory::CreateBehaviorTree`, `Factory::FactoryNodeDefinition(IDatabaseQuery1*)`, `Factory::InitializeData`, `Factory::CopyBehaviorTree`. The Factory is a game component (vtable slots Initialize/Uninitialize/Reset + component interface).
* Node classes have no vtables. Each node is a static function set (`Update`, sometimes `Execute`/`Initialize`) registered by name; 75 classes have an `Update`. Only helper classes have vtables: `Factory`, `NearestCityJob`, `BarbarianRecruiter` and the `*Evaluator` family (`FindUnits`, `OpRecruit`, `NavalEscort`, `SpyAtCity`), which are in `vtable_slots.tsv`.
* `NODE_SHAPE`: parent (3 types: Concurrent, Priority, Sequence), leaf/action (38), decision (23, never return running, may output data), decorator (7, exactly one child), subtree (1, "Run Behavior Tree"). The `NODE_TYPE` enum in DWARF is only Aspyr dummy values with no names; the names come from the XML.
* `LuaScriptNode::Update` returns the numeric state 1 when the Lua call produced a positive number or true, 3 otherwise, and 4 when its node data is missing (names of the `ACTION_STATE` values not checked; 1 = success, 3 = failure is a guess).
* The full node list is in the [Node reference](#node-reference) below and as `findings/tables/behavior_tree_nodes.tsv` in the repository (node id, type, shape, class, Linux `Update` address, use count, trees using it, parameters, XML description).

## The two Lua nodes
* **LUA Script Condition** (node 70, decision, one parameter "Script Function": string). `LuaScriptNode::Update` (old RVA 0x554dd0) calls `Lua::Utility::CallProcessor(scriptSystem, name, args, resultMap)`. That is the `GameEvents.<name>` processor mechanism (see lua-event-dispatch.md), so the "function name" is a GameEvents event and the handler is registered with `GameEvents.<name>.Add(fn)`. The handler gets a table (`targetInfo`) and writes the result into it: the node reads the field `Extra` (hash 0x7301dd9e = ~crc32("Extra"), verified), and a number/boolean greater than 0 gives success; call failed, field missing, 0 or wrong type gives failure. The Civ Royale DLC does exactly this: `CivRoyale_SmallSafeZone(targetInfo)` sets `targetInfo.Extra = 1/0` (DLC/CivRoyaleScenario/Scripts/CivRoyaleScenario_StartScript.lua:781, registered at :1608). Only the Civ Royale tree uses the node (`CivRoyale_SmallSafeZone`).
* **Use Scripted Command** (node 72, action). `UseScriptedCommand::Execute` (old RVA 0x577990) loops over a per-player list of script command names (player +0x670 -> +0x4a0, 16-byte entries). For each of the AI control's own units it builds a `Unit::Commands::ExecuteScript` request with that name, asks the command manager whether it can start (vtable +0x48), and starts it (vtable +0x58). So the AI can run `UnitCommandTypes.EXECUTE_SCRIPT` commands on its units.
* Related Lua API (lua_api.txt): `AiMilitary:StartScriptedOperation`, `AddUnitToScriptedOperation`, `SetScriptedOperationReady`, `SetScriptedTargetAndRally`.

## Inferred (not tested)
* Node name -> class mapping is by name (some by hand: e.g. "Build Unit" -> `BuildFromCityNode`, "Find Unit Targets" -> `FindTargetsNode`, "Operation Air Assault" -> `OperationAirstrikeCityNode`). Five classes have no XML node (`GatherBuildingsNode` and the four evaluators); the evaluators are probably helpers chosen by other nodes, `GatherBuildingsNode` unknown.
* Where the player's script command list is filled is not traced yet.

## For modders
* Edit or add rows in `BehaviorTrees`, `BehaviorTreeNodes`, `TreeData` (via the XML/SQL tables) to change what the AI does; the node vocabulary is fixed (72 types), only their combination and parameters are data.
* A new tree reaches the AI through `TriggeredBehaviorTrees` (AI event -> tree) plus an `AiFavoredItems` entry in `DefaultTriggeredTrees` (and `MinorCivTriggeredTrees`) that arms it, or through operations (`AiOperationDefs.BehaviorTree`) that reference tree names. Only one trigger is active per AI event, so to take over an event, delete the base entry from the list (verified for `AI_EVENT_GAIN_TECH`).
* `LUA Script Condition` is the hook for custom logic: register `GameEvents.<Name>.Add(fn)`, put `<Name>` in the node's "Script Function" TreeData, and have `fn(targetInfo)` set `targetInfo.Extra = 1` for success (0 for failure).

## First in-game test (2026-10-30, mod BTTreeTest, run 1)
* Verified in game: a mod's `BehaviorTrees`/`BehaviorTreeNodes`/`TreeData`/`TriggeredBehaviorTrees` rows reach the live gameplay DB (checked in Cache/DebugGameplay.sqlite), the mod's Lua script loaded and registered its `GameEvents` handler.
* Verified in game: a `TriggeredBehaviorTrees` row alone does NOT arm a trigger. With `AI_EVENT_GAIN_TECH` firing for 3 AIs, only the base `Upgrade Units` tree ran; the mod's tree never did (0 rows in `Logs/AI_Behavior_Trees.csv`, no handler call). The base game arms triggers through the AI lists: `AiFavoredItems(ListType="DefaultTriggeredTrees" / "MinorCivTriggeredTrees", Item="<TriggerType>")`. Engine side: `Lists::Handler<TriggeredTreeInfo>::ExecuteLeaderQuery/ExecuteAgendaQuery`, `Manager::OnAiEvent`.
* Run 2 (list entry added, new game): still no run. `Manager::OnAiEvent` (old RVA 0x563110) indexes a per-player array (this+0x338, 0x18-byte entries: tree name, operation name, priority) by AI event index, so there is ONE trigger slot per event. A second trigger on `AI_EVENT_GAIN_TECH` loses to the base `Upgrade Units` (which of the two wins, first row or priority, is not determined). If the entry has no operation name it copies the tree (`Factory::CopyBehaviorTree`) and adds it to the AI control; with an operation name it starts that military operation instead.
* Run 3 (base `TRIGGER_TECH_UPGRADE` removed from both lists, so the mod's trigger is the only one for the event): **works**. On turn 10, players 6, 8 and 11 ran "BTTest Tree" (`AI_Behavior_Trees.csv`: Sequence SUCCESS, LUA Script Condition SUCCESS) and `GameEvents.BTTest_Condition` was called 3 times (`Lua.log`). The handler's argument was an empty table (`fields={}`), and setting `targetInfo.Extra = 1` made the node return SUCCESS. So a mod-added tree, its trigger, and a Lua condition node all work end to end; the node's "Script Function" is a `GameEvents` name.
* Still open: which trigger wins when two share an event (first row or priority), and whether a failing handler (Extra = 0) shows FAILURE in the log.
* `Logs/AI_Behavior_Trees.csv` (columns: Game Turn, Player, System, Tree, Node, Result, Data) logs every node of every tree run; it is the main observation tool for tree tests.

## Open
* Per-node semantics beyond the XML description (what each reads from the blackboard).
* The 17 AI control contract/operation classes are separate and not covered here.

## Node reference

The 72 node types of `BehaviorTrees.xml` (base game, build 15038592). Class names are matched by name to the `GameCore::AI::BehaviorTree` classes (inferred, see above). Parameter flags: R required, G one of a required group, U user-settable, O output.

| Id | Node | Shape | Class | Used | Parameters | What the game's XML says |
|---|---|---|---|---|---|---|
| 0 | Concurrent | Selector | `ConcurrentNode` | 72 | Max Failures:int[U]; Exit on Success:bool[U] | Logical And node. Runs all children until it reaches a FAILURE (can allow multiple failures if desired.) |
| 1 | Priority | Selector | `PriorityNode` | 37 | - | Logical Or node. Runs all children until it reaches a SUCCESS or RUNNING |
| 2 | Sequence | Selector | `SequenceNode` | 46 | Looping:bool[U] | Special logical And node. Stops on FAILURE, but also stops on RUNNING. Resumes next turn on RUNNING node. |
| 3 | Add Goal Tech | Action | `AddGoalTechNode` | 14 | Desired Units:UnitTypesList[R]; Desired Buildings:BuildingTypesList[R]; Desired Improvements:ImprovementList[R]; Goal Plot to work:Map Point[R]; Desired Techs:TechTypeList[R]; Add Techs For All:bool[U]; Desired Civics:CivicsList[R]; Contract ID:ID List[O]; Tech Value:int | Given a list of units, buildings, or techs, asks Research AI to work on them |
| 4 | Build Unit | Action | `BuildFromCityNode` | 18 | Desired Units:UnitTypesList[R]; Desired Buildings:BuildingTypesList[R]; Required City(-1 for any city):int[U]; Release Unit When Built:bool[U]; Contract ID:int[O]; Build Priority:int[U]; Desired Districts:DistrictList[R]; Desired Location:Map Point; Unit Value:int | Given a list of units and/or buildings and a city, builds 'best' unit at the city when queue is availble. |
| 5 | Find Available Unit | Decision | `FindAvailableUnitNode` | 12 | Desired Units:UnitTypesList[R]; Desired Location:Map Point; Found Unit:ID List[O]; Upgradeable Units:bool[RU]; Unit Type:string[RU] | Given a list of units, finds first unit of matching type that can get to location |
| 6 | Notify Owner | Action | `NotifyOwnerNode` | 3 | Data Payload:int | Sends notice back to the owning player or any other listener, with an optional integral payload. |
| 7 | Barbarian Spawn Change | Action | `BarbarianSpawnRateNode` | 6 | Tribe:int; Spawn Rate:int[U]; Raiding Party:bool[U] | Change the spawn rate of a barbarian tribe to prepare for raid/invasion. |
| 8 | Run Behavior Tree | Sub-tree | `RunBehaviorTreeNode` | 0 | Behavior Tree:string[U]; Behavior Tree Parent Tag:string | DEPRECATED - DO NOT USE. Runs a behavior tree defined elsewhere. You can change data for that sub-tree, but not its structure. |
| 9 | Operation Move | Action | `OperationMoveNode` | 37 | Move To (enum):int[U]; Range to goal:int[U]; Validate new units:bool[U]; Unit distance:int[U]; Leader Tag:string[U]; AlwaysRunning:bool[U]; Can Explore:bool[U] | Moves operation to the rally point. |
| 10 | Decode Trigger | Decision | `DecodeTriggerNode` | 22 | Trigger Units:UnitTypesList[RO]; Trigger Buildings:BuildingTypesList[RO]; Trigger Improvements:ImprovementList[RO]; Trigger District:DistrictList[RO]; Trigger City:int[RO]; Trigger Location:Map Point[RO]; Trigger Tech:TechTypeList[RO]; Trigger Civic:CivicsList[RO]; Trigger Value:int[O] | For temporary trees only. Take the trigger you want to meet and extract information for use elsewhere. |
| 11 | Choose City | Decision | `ChooseCityForBuildingNode` | 1 | Building List:BuildingTypesList; City ID:int[O]; Needed District:DistrictList[O]; District Location:Map Point[O]; Building Location:Map Point[O] | Given a list of buildings, pick the best city to make a building. Output city and needed improvement. |
| 12 | Build Improvement | Action | `BuildImprovementNode` | 2 | Worker List:ID List; Goal Plot:Map Point; Improvements:ImprovementList; Release when done:bool[U]; Builder Plot:Map Point | Given a worker, location, and improvement, build the improvement. |
| 13 | Move Unit | Action | `MoveUnitNode` | 12 | Unit ID List:ID List; Location:Map Point; Release when done:bool[U]; Allow Danger:bool[U]; To Range:int[U] | Given a unit ID and a location, give the unit a move order. Report RUNNING until it reaches destination. |
| 14 | Operation Attack | Action | `OperationAttackTarget` | 1 | - | As part of an operation, attack the target. |
| 15 | Not | Decorator | `NotNode` | 5 | - | Decorator that turns SUCCESS and RUNNING to FAILURE and vice versa. Does not reverse ERROR. |
| 16 | Purchase Plot | Action | `PurchasePlotNode` | 4 | Required City:int; Plot:Map Point; Contract:int[O] | Purchase a plot for a city. |
| 17 | Recruit Units | Decision | `RecruitUnitsNode` | 26 | Already in progress:bool[U]; Contract ID:int; Recruit Range:int[U]; Allow creation:bool[U]; Recruit Value:int; Time Limit:int[U]; Allow Stealing:bool[U]; Allow Levying:bool[U] | Recruit units for a defined operation. OPERATION USE ONLY. |
| 18 | Operation Attack Units | Action | `OperationAttackUnits` | 36 | Attack Nearby Units:bool[U]; Attack Along March:bool[U]; Allow Unequal Attacks:bool[U]; Always Running:bool[U]; Attack Near Target:bool[U] | As part of an operation, attack enemy units during a move. |
| 19 | Choose Improvement | Decision | `ChooseImprovementNode` | 1 | Input Improvements:ImprovementList; Builder List:UnitTypesList[O]; Location:Map Point[O]; Output Improvement:ImprovementList[O] | Given a list of improvement types, chooses a specific improvement to build, preferably around a city |
| 20 | Barbarian Raid Check | Decision | `BarbarianRaidingScoreNode` | 1 | Tribe Number:int; Score:int[U]; Signal At Start:bool[U] | Check the score of a barbarian raid |
| 21 | In Difficulty Range | Decorator | `DifficultyDecorator` | 1 | Low Difficulty:string[RU]; High Difficulty:string[RU]; Apply to opponent:bool[U]; Fail if Outside:bool[U] | Decorator that runs if owner's difficulty is within range. Optionally target difficulty, optionally fail if outside. |
| 22 | Settle | Action | `SettleActionNode` | 2 | Settler Unit:ID List | Tells a unit to perform the settle action. FAILS if no unit is able to do so. |
| 23 | Check Plot | Decision | `CheckPlotNode` | 6 | Plot To Check:Map Point; Building Districts:DistrictList[R]; Building Wonders:BuildingTypesList[R]; Building Improvements:ImprovementList[R]; Resource Harvesting:bool[O]; Builder List:UnitTypesList[O]; Plot To Move:Map Point[O] | Checks if you can build the requested building or district on that location. Outputs an offending resource or feature if it fails |
| 24 | Clear Plot | Action | `ClearPlotNode` | 4 | Builder List:ID List; Release on Complete:bool[U]; Plot To Clear:Map Point; Resource Harvesting:bool | Orders a unit to clear the current tile. FAILS if no unit is able to do so. |
| 25 | Barbarian Recruit | Decision | `BarbarianRecruitNode` | 2 | Tribe:int; Num Melee:int[RU]; Num Ranged:int[RU]; Num Siege:int[RU]; Num Support:int[RU]; Raiding Party:bool[U] | Recruit members from a tribe for a raid or invasion. |
| 26 | Interval | Decorator | `IntervalDecorator` | 0 | Turns to Run:int[U] | Lets a child run for n turns before rechecking it |
| 27 | Operation Defend Units | Action | `OperationProtectUnits` | 15 | AutoProtect Percentage:int[U]; Protect Outside Range:int[U] | As part of an operation, protect your units that might otherwise be destroyed. |
| 28 | Turn Limiter | Decorator | `TurnLimitDecorator` | 12 | Turns to Run:int[U]; Fail at Limit:bool[U]; Limit Is Min:bool[U] | Only lets a child node run for a limited number of turns before failing. |
| 29 | Operation Change Target | Action | `OperationChangeTarget` | 20 | Backup Amount:float[U]; Failure Amount:float[U]; Fail on Invalid Team:bool[U]; Required Tag:string[U]; Always Swap:bool[U] | As part of an operation, if you can't take the current target, find a new one or give up. |
| 30 | Contract Manager Decorator | Decorator | `ContractManagerDecorator` | 43 | Contract:int[R]; Multi-Contracts:ID List[R]; Turn Limit:int[U]; Block While Running:bool[U]; Turns Remaining:int[U] | Manages a contract, can limit turns until it is run. |
| 31 | Operation Attack City | Action | `OperationAttackCityNode` | 9 | Unused:int[U] | As part of an operation, attack a city |
| 32 | Make Formation | Action | `MakeFormationNode` | 10 | Destroy Formations:bool[U]; Combat Unit:string[RU]; Civilian Unit:string[RU]; Support Unit:string[RU]; Naval Unit:string[RU] | Create (or destroy) a formation of units |
| 33 | Protect Unit | Action | `ProtectUnitNode` | 8 | Unit List:ID List; Damage Percentage:float[U] | Keep a non-operation unit safe if its health is below specified fraction |
| 34 | City Attack | Action | `CityAttackUnitsNode` | 1 | Preferred Type:string[U] | Cities attack enemy units within range, with preferences as described (none required) |
| 35 | Reserve Plot | Decision | `ReservePlotNode` | 6 | Plot to reserve:Map Point; City:int; Value:int; Tag:string[U] | Reserve a city plot so that other trees will leave it alone |
| 36 | Operation Pillage | Action | `OperationPillageCityNode` | 13 | Pillage Districts:bool[U]; Pillage Improvements:bool[U]; Get Goody Huts:bool[U] | Pillage nearby improvements and districts |
| 37 | Operation Siege City | Action | `OperationSiegeCityNode` | 7 | Unused:int | Pillage nearby improvements and districts |
| 38 | Garrison City | Action | `OperationGarrisonCityNode` | 1 | Unused:int | As part of an operation, garrison a unit in a friendly city |
| 39 | Is City Threatened | Decision | `IsCityThreatenedNode` | 2 | Unused:int | Tell if city that is operation target is still threatened |
| 40 | Is At War | Decision | `IsAtWarNode` | 5 | Minimum Number:int[U]; Include Barbarian:bool[U]; With Operation Target:bool[U]; Skip For Minors:bool[U] | Tell if player is at war |
| 41 | Find Unit Targets | Decision | `FindTargetsNode` | 2 | Nearest Owned City:bool[U]; Needed District:DistrictList; Needs Buildings:BuildingTypesList; Contract Value:int | Find places for all owned units to go |
| 42 | Upgrade Units | Action | `UpgradeUnitsNode` | 2 | Can Delete:bool | Upgrade any upgradeable units |
| 43 | Has Great Person | Decision | `HasGreatPersonNode` | 1 | Great Person Type:string[U] | Succeeds if the tree has a great person of the appropriate type |
| 44 | Use Great Person | Action | `UseGreatPersonNode` | 1 | Unused:string | Uses the great person ability, including founding a religion |
| 45 | Cancel Contract | Decision | `CancelContractNode` | 4 | Contract:int | Cancel a tagged contract |
| 46 | Lock Units | Decision | `LockUnitsNode` | 6 | Lock Units:bool[U]; Signal Readiness:bool[U] | Allow / disallow units to be recruited off the team |
| 47 | Operation Diplomacy | Action | `OperationDiplomacy` | 4 | Desires Denouncement:bool[RU]; Had Denounced:bool[RU]; Desires War:bool[RU]; Is At War:bool[RU]; Present Value:int; Contract:int | Diplomatic actions and tests |
| 48 | SPY: Choose Mission | Decision | `SpyChooseMissionNode` | 1 | Operation:int; Minimum Odds:int[U] | Choose a spy mission for the spy's current city |
| 49 | SPY: Do Operation | Action | `SpyDoOperationNode` | 1 | Operation:int; Allow Gain Sources:bool[U]; Minimum Odds:int[U] | Execute the spy's current mission |
| 50 | SPY: Travel | Action | `SpyMoveToCityNode` | 2 | Destination:Map Point[R]; Go Home:bool[RU] | Move the spy to the chosen city (or home) |
| 51 | ARCHAEOLOGY: Dig | Action | `ArcheologistDigNode` | 1 | Relic Plot:Map Point | Have an archaeologist dig at the specified location |
| 52 | ARCHAEOLOGY: Donate | Action | `ArchaeologistDonateNode` | 1 | - | An archaeologist moves to his home and donates any carried artifact to his museum |
| 53 | Operation Naval Escort | Action | `OperationNavalEscort` | 2 | Move Point enum:int[U] | Recruit naval escorts to an operation and ferry units across the waters |
| 54 | Has Player Ability | Decorator | `HasPlayerAbilityDecorator` | 2 | Fail if none:bool[U]; Builders make wonders:bool[RU]; Builders make districts:bool[RU] | Decorator that checks for player ability before handing control to child |
| 55 | Build Production | Action | `BuildProductionNode` | 2 | Location:Map Point; Release When Done:bool | Use a builder charge to accelerate a wonder or district (if allowed) |
| 56 | Has Inquisition | Decision | `HasInquisitionNode` | 1 | Unused:int | Returns true if the specified player has launched an inquisition |
| 57 | Launch Inquisition | Action | `LaunchInquisitionNode` | 1 | Apostle:ID List | Launches an inquisition using an attached unit, if possible |
| 58 | Will use nukes | Decision | `WillUseNukesNode` | 1 | - | Checks if the AI is willing to use nukes against his opponent (Gandhi always will) |
| 59 | Operation Launch nuke | Action | `LaunchNukesNode` | 3 | Target Units:bool[U] | Launch nuke at target |
| 60 | Operation Is Ready | Decision | `OperationIsReadyNode` | 5 | Unused:int | Checks if the associated operation is ready |
| 61 | Build Military Improvement | Action | `BuildMilitaryImprovementNode` | 2 | Defensive Improvement:bool[U]; Specific Improvement:string[U] | Build an improvement outside your own territory (usually in an operation) |
| 62 | Operation Air Assault | Action | `OperationAirstrikeCityNode` | 2 | Improvement Priority (1-3):int[U]; Combat District Priority (1-3):int[U]; Passive District Priority (1-3):int[U]; Bomber Unit Type:string[U]; Present Value:int | Launcher bombers against target city |
| 63 | Naval Choose Target | Decorator | `NavalChooseTargetDecorator` | 1 | Target Domain:string[U]; Fail for no target:bool[U] | Choose a naval superiority target. If none available, don't run child. |
| 64 | Naval Patrol | Action | `NavalPatrolNode` | 1 | - | Choose a naval patrol target and move accordingly. |
| 65 | Naval Pillage | Action | `NavalPillageNode` | 1 | Unused:string[U] | Opportunistically attack districts and land units (naval raiding to come). |
| 66 | Has Valid Target | Decision | `HasValidTargetNode` | 1 | - | Checks that unit assigned target remains valid. Removes units with invalid targets from tree. |
| 67 | Can Alpha City | Decision | `CanAlphaStrikeCityNode` | 5 | - | For shortcutting a city attack. Check if you can do 50%+ garrison damage or defense units are worth ignoring. |
| 69 | Is Near Fallout | Decision | `IsNearFalloutNode` | 1 | Range:int[U] | Returns true if any unit is within range of fallout and puts all such members in the Endangered list (if there is an operation) |
| 70 | LUA Script Condition | Decision | `LuaScriptNode` | 1 | Script Function:string[U] | Run a lua script function that returns a boolean value. Only the player is passed in to the script |
| 71 | Operation Military Formation | Action | `OperationMakeFormation` | 0 | Unused:string[U] | Within an operation, attempt to combine units into corps and armies |
| 72 | Use Scripted Command | Action | `UseScriptedCommand` | 2 | Unused:string[U] | If they have an available scripted command, try to use it |

## Reproducing the test (mod sources)

The first test as a plain mod. Add two `InGameActions` to a `.modinfo`: `UpdateDatabase` for the XML and `AddGameplayScripts` for the Lua. Look for `BTTEST:` lines in `Lua.log` and for "BTTest Tree" in `AI_Behavior_Trees.csv`. It also removes the base game's `TRIGGER_TECH_UPGRADE` entries (the AIs stop upgrading units on tech while it is enabled), because only one trigger per event is active.

**BTTreeTest.xml**

```xml
<?xml version="1.0" encoding="utf-8"?>
<GameInfo>
  <BehaviorTrees>
    <Row TreeName="BTTest Tree"/>
  </BehaviorTrees>
  <BehaviorTreeNodes>
    <Row NodeType="Sequence" NodeId="0" TreeName="BTTest Tree" JumpTo="2"/>
    <Row NodeType="LUA Script Condition" NodeId="1" TreeName="BTTest Tree"/>
  </BehaviorTreeNodes>
  <TreeData>
    <Row DefnId="0" NodeId="1" TreeName="BTTest Tree" DefaultData="BTTest_Condition"/>
  </TreeData>
  <TriggeredBehaviorTrees>
    <Row TriggerType="TRIGGER_BTTEST_TECH" TreeName="BTTest Tree" AIEvent="AI_EVENT_GAIN_TECH" Priority="3"/>
  </TriggeredBehaviorTrees>
  <AiFavoredItems>
    <!-- one tree per AI event: drop the base trigger for AI_EVENT_GAIN_TECH so ours is the only one (test only) -->
    <Delete ListType="DefaultTriggeredTrees" Item="TRIGGER_TECH_UPGRADE"/>
    <Delete ListType="MinorCivTriggeredTrees" Item="TRIGGER_TECH_UPGRADE"/>
    <Row ListType="DefaultTriggeredTrees" Item="TRIGGER_BTTEST_TECH"/>
    <Row ListType="MinorCivTriggeredTrees" Item="TRIGGER_BTTEST_TECH"/>
  </AiFavoredItems>
</GameInfo>
```

**Scripts/BTTreeTest.lua**

```lua
-- BT Tree Test: proves a mod-added behavior tree runs and its LUA Script Condition node calls GameEvents.BTTest_Condition
print("BTTEST: script loaded");
local callCount = 0;

function BTTest_Condition(targetInfo)
	callCount = callCount + 1;
	local keys = {};
	if type(targetInfo) == "table" then
		for k, v in pairs(targetInfo) do table.insert(keys, tostring(k) .. "=" .. tostring(v)); end
	end
	print("BTTEST: condition called #" .. callCount .. " arg type=" .. type(targetInfo) .. " fields={" .. table.concat(keys, ",") .. "} turn=" .. tostring(Game.GetCurrentGameTurn()));
	if type(targetInfo) == "table" then targetInfo.Extra = 1; end
	return true;
end

GameEvents.BTTest_Condition.Add(BTTest_Condition);
print("BTTEST: handler registered");
```
