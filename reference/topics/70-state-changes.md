---
title: Lua methods that change game state
order: 70
---
# Lua methods that change game state

Generated from a static trace of the code behind each Lua method: which class members the method (and the functions it calls) writes directly. **Everything here is inferred**: offsets come from the Windows build and are mapped to member names through the Linux debug info (Windows offset + 8 or equal, kept only when exactly one member fits).

Read the lists with these limits in mind:

- Many mutators change state by calling game functions that wrap the write (tracked variables, containers). Those show no direct write here, so this list is **incomplete**, not a list of every mutator.
- Virtual calls, writes through aliases and values stored and loaded back are not followed.
- Members shown as `m_x` are the member of the class in the first column; `Other::m_y` is a member reached through a pointer.
- UI-side (`Cache::`) twins of these methods are left out.

Where a method name suggests a different effect than the member list, trust the code reading: the trace only says *what is written*, not *when*.

## AI::Military

| Lua method | Writes | Also reads |
|---|---|---|
| `AiMilitary:AllowUnitConstruction` | `m_allowUnitConstruction` | — |
| `AiMilitary:StartScriptedOperation` | `m_activeOperations`, `m_opEvaluators` | `m_perWarOperationTypes`, `m_allowedOperationTypes`, `m_currentOperationTypes`, `Player::Instance::m_id` |

## AI::Religious

| Lua method | Writes | Also reads |
|---|---|---|
| `AiReligious:SetFavoredReligion` | `m_favoredReligion` | — |

## Barbarian::Manager

| Lua method | Writes | Also reads |
|---|---|---|
| `BarbarianTribes:CreateSpecificTribe` | `m_managingCampsDirectly` | `m_campImprovement` |
| `BarbarianTribes:CreateTribeOfType` | `m_managingCampsDirectly` | `m_campImprovement` |

## City::Buildings

| Lua method | Writes | Also reads |
|---|---|---|
| `CityBuildings:RemoveBuilding` | `m_aGreatWorkBuildings` | `m_aExtraGreatWorks` |
| `CityBuildings:SetBuildingLocation` | `m_aGreatWorkBuildings`, `City::Instance::m_bCapital` | `m_aiBuildingLoc`, `City::Instance::m_eOwner`, `City::Instance::m_id` |

## City::Instance

| Lua method | Writes | Also reads |
|---|---|---|
| `City:ChangeLoyalty` | `m_kCulturalIdentity+0x200`, `m_kCulturalIdentity+0x204` | `m_kCulturalIdentity+0xe0`, `m_kCulturalIdentity+0x1b0`, `m_kCulturalIdentity+0xa8` |
| `City:ChangePopulation` | `m_iPopulation` | `m_eOwner`, `m_id` |
| `City:SetName` | `m_szName` | `m_kLocation`, `m_eOwner`, `m_id` |
| `CityManager:SetAsCapital` | `m_bCapital` | `m_eOwner`, `m_id` |
| `CityManager:SetAsOriginalCapital` | `m_bOriginalCapital` | `m_eOwner`, `m_id` |

## City::Religion

| Lua method | Writes | Also reads |
|---|---|---|
| `CityReligion:RemoveOtherReligions` | `m_ReligionStatus` | — |

## Diplomacy::Deal::Instance

| Lua method | Writes | Also reads |
|---|---|---|
| `Deal:AddItemOfType` | `m_Items` | — |
| `Deal:ClearItemsByType` | `m_Items` | — |
| `Deal:ClearItemsByValue` | `m_Items` | — |
| `Deal:RemoveItem` | `m_Items` | — |
| `Deal:RemoveItemByID` | `m_Items` | — |
| `Deal:Validate` | `m_Items` | — |

## District::Instance

| Lua method | Writes | Also reads |
|---|---|---|
| `District:ChangeDamage` | `m_iGarrisonDamage`, `m_iOuterDefensesDamage`, `m_iLastTurnDamaged` | `m_iCityID`, `m_kLocation`, `m_eDistrictType`, `m_id` |
| `District:SetDamage` | `m_iGarrisonDamage`, `m_iOuterDefensesDamage` | `m_iCityID`, `m_eDistrictType`, `m_id` |

## Fractal::Instance

| Lua method | Writes | Also reads |
|---|---|---|
| `Fractal:BuildRidges` | `m_aaiFrac` | — |

## Game::DiplomaticRelations

| Lua method | Writes | Also reads |
|---|---|---|
| `GameDiplomacy:SetAlliesShareVisFlag` | `m_alliesShareVis` | — |

## Game::Fallout::Manager

| Lua method | Writes | Also reads |
|---|---|---|
| `GameFalloutManager:SetFalloutDamageOverride` | `m_damageOverride` | — |

## Game::Instance

| Lua method | Writes | Also reads |
|---|---|---|
| `Game:SetCurrentGameTurn` | `m_iCurrentTurn` | — |

## GameSummary::Instance

| Lua method | Writes | Also reads |
|---|---|---|
| `HallofFame:GetPlayerObject` | `m_Repository+0x10` | `m_Repository+0x58`, `m_Repository+0x60`, `m_Repository+0xb8` |

## Map::StartPositioner

| Lua method | Writes | Also reads |
|---|---|---|
| `MapStartPositioner:DivideMapIntoMajorRegions` | `m_StartPositions`, `m_ContinentInfo`, `m_MajorStartRegions`, `m_MinorStartRegions`, `m_aOceanStartTiles` | — |
| `MapStartPositioner:PlaceOceanStartCivs` | `m_aOceanStartTiles` | — |

## Player::Cities

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerCities:Create` | `m_kCities`, `m_eHomeContinent` | `Player::Instance::m_id` |
| `PlayerCities:Destroy` | `m_kCities` | — |

## Player::Congress

| Lua method | Writes | Also reads |
|---|---|---|
| `TeamDiplomacy:ChangeFavor` | `m_iPlayerFavor`, `m_iLifetimeFavor` | `Player::Instance::m_id` |

## Player::Culture

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerCulture:Reset` | `m_eCurrentGovernment`, `m_ePostAnarchyGovernment`, `m_iTurnAdopted`, `m_iAnarchyEndTurn`, `m_uiCivicArraySize`, `m_xCulturalOverflow` … | — |
| `PlayerCulture:ReverseBoost` | `m_iNumCivicsRepeated`, `m_xLifetimeCulture`, `m_iStaycationers`, `m_bCivicCompletedThisTurn`, `m_eCivicCompletedThisTurn` | `Player::Instance::m_id`, `m_abHasCivic`, `Player::EventManager::m_governmentRevokedHandle+0x8`, `Player::EventManager::m_pPlayer` … |
| `PlayerCulture:SetCivic` | `m_iNumCivicsRepeated` | `m_abHasCivic`, `Player::Instance::m_id`, `Player::EventManager::m_governmentRevokedHandle+0x8`, `Player::Units::m_aCurrentUnitCost` … |
| `PlayerCulture:SetCivicCompletedThisTurn` | `m_bCivicCompletedThisTurn` | `Player::Instance::m_id` |
| `PlayerCulture:TriggerBoost` | `m_iNumCivicsRepeated`, `m_xLifetimeCulture`, `m_iStaycationers`, `m_bCivicCompletedThisTurn`, `m_eCivicCompletedThisTurn`, `m_xCulturalOverflow` | `m_abBoostTriggered`, `m_abHasCivic`, `m_axCulturalProgress`, `Player::Instance::m_id` |

## Player::Eras

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerEras:SetEra` | `m_eEra` | `Player::Instance::m_id`, `Player::EventManager::m_tradePostToBeCreatedHandle+0x8`, `Player::Cities::m_kCities` |
| `PlayerEras:SetStartingEra` | `m_eEra` | `Player::Instance::m_id`, `Player::EventManager::m_tradePostToBeCreatedHandle+0x8`, `Player::Cities::m_kCities` |

## Player::Influence

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerInfluence:ChangeTokensToGive` | `m_iTokensToGive` | `Player::Instance::m_id` |

## Player::Manager

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerManager:SetLocalObserverTo` | `m_kDefaultProperties` | — |
| `PlayerManager:SetLocalPlayerAndObserver` | `m_kDefaultProperties` | `m_aIDToPlayer` |

## Player::Religion

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerReligion:ChangeFaithBalance` | `m_xFaithBalance` | `Player::Instance::m_id` |
| `PlayerReligion:ChangeNumBeliefsEarned` | `m_iNumBeliefsEarned` | `Player::Instance::m_id`, `Game::Religion::m_kReligions` |
| `PlayerReligion:SetFaithBalance` | `m_xFaithBalance` | `Player::Instance::m_id` |
| `PlayerReligion:SetHolyCity` | `m_kHolyCityCoord` | — |

## Player::Stats

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerStats:ChangeScienceVictoryPoints` | `m_xScienceVictoryPoints` | `Player::Instance::m_id` |
| `PlayerStats:UpdateMaxBombardStrengthTrained` | `m_iMaxBombardStrengthTrained` | — |
| `PlayerStats:UpdateMaxMeleeStrengthTrained` | `m_iMaxMeleeStrengthTrained` | — |
| `PlayerStats:UpdateMaxRangedStrengthTrained` | `m_iMaxRangedStrengthTrained` | — |

## Player::Techs

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerTechs:ReverseBoost` | `m_iNumTechsRepeated` | `m_abHasTech`, `Player::Instance::m_id`, `Player::Units::m_kUnits`, `Player::EventManager::m_pPlayer` … |
| `PlayerTechs:SetTech` | `m_iNumTechsRepeated` | `m_abHasTech`, `Player::Instance::m_id`, `Player::Units::m_aCurrentUnitCost`, `Player::Units::m_aiCurrentUnitResourceCost` … |
| `PlayerTechs:TriggerBoost` | `m_iNumTechsRepeated`, `m_xResearchOverflow` | `m_axResearchProgress`, `m_abHasTech`, `Player::Instance::m_id`, `m_abBoostTriggered` … |

## Player::Treasury

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerTreasury:ChangeGoldBalance` | `m_xGoldBalance` | `Player::Instance::m_id` |
| `PlayerTreasury:ChangeGoldBalanceByPercentage` | `m_xGoldBalance` | `Player::Instance::m_id` |
| `PlayerTreasury:SetGoldBalance` | `m_xGoldBalance` | `Player::Instance::m_id` |

## Player::Units

| Lua method | Writes | Also reads |
|---|---|---|
| `PlayerUnits:Create` | `m_kUnits` | — |
| `PlayerUnits:Destroy` | `m_kUnits`, `Player::Formations::m_kFormations` | `Player::Instance::m_id` |

## Unit::Experience

| Lua method | Writes | Also reads |
|---|---|---|
| `UnitExperience:ChangeExperience` | `m_iLevel` | `Unit::Instance::m_eOwner`, `Unit::Instance::m_iDamage`, `Unit::Instance::m_eTypeIndex`, `Unit::Instance::m_id` |
| `UnitExperience:SetVeteranName` | `m_sVeteranName` | `Unit::Instance::m_id`, `Unit::Instance::m_eOwner` |

## Unit::Instance

| Lua method | Writes | Also reads |
|---|---|---|
| `Unit:ChangeActionCharges` | `m_iActionCharges` | `m_eOwner`, `m_id` |
| `Unit:ChangeDamage` | `m_iDamage` | `m_eOwner`, `m_id`, `m_kHero` |
| `Unit:SetDamage` | `m_iDamage` | `m_eOwner`, `m_id`, `m_kHero` |
| `Unit:SetFortifyTurns` | `m_iFortifyTurns` | — |
| `Unit:SetMilitaryFormation` | `m_eMilitaryFormation` | `m_eOwner`, `m_id` |

## Unit::Religion

| Lua method | Writes | Also reads |
|---|---|---|
| `UnitReligion:ChangeEvictPercent` | `m_iEvictPercent` | — |
| `UnitReligion:SetEvictPercent` | `m_iEvictPercent` | — |

## WorldBuilder::Mod::LocalizationStringTable

| Lua method | Writes | Also reads |
|---|---|---|
| `WorldBuilderModManager:SetString` | `m_kList` | — |
