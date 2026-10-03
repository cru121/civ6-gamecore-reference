# Leads not yet analyzed

Functions with no Lua wrapper that look gameplay-relevant, from the automated gap analysis (`gap_shortlist.tsv`).
**These are unread.** Only what the scripts could see is listed (event/notification/signal flags, callers, callees).
Addresses are in the installed build (`rva_installed_build`); verify before use.

| # | Function | Installed RVA | Direct callers | Notes from scripts |
|---|---|---|---|---|
| 1 | Player::Governors::UnassignGovernor | 0x2df800 | 7 | event, notification, signal |
| 2 | Trade::Manager::StartRoute | 0x3913f0 | 2 | event, notification, signal, edit() |
| 3 | Rules::Espionage::Instance::CaptureSpy | 0x3726e0 | 13 | event, notification, signal, virtual calls>=4 |
| 4 | Quests::Logic::BaseQuest::CompleteQuest | 0x5a3590 | 8 | event, notification |
| 5 | Player::Diplomacy::SetCanEnforceBorders | 0x2af9f0 | 2 | event, notification |
| 6 | Rules::Espionage::Instance::KillSpy | 0x374720 | 14 | event, notification, virtual calls>=4 |
| 7 | Rules::Espionage::Instance::ResetFailedSpy | 0x374dc0 | 11 | event, notification, virtual calls>=4 |
| 8 | City::Power::RecalculatePower | 0x147e80 | 5 | event, signal |
| 9 | Barbarian::ClansManager::ClearCamp | 0x61f970 | 4 | event, signal, edit() |
| 10 | Player::Espionage::AddReturningSpy | 0x2cf460 | 3 | event, signal, edit() |
| 11 | Player::Instance::SetAlive | 0x2fa9a0 | 3 | event, signal |
| 12 | City::Buildings::RemoveAllBuildings | 0x10cf80 | 2 | event, signal |
| 13 | Game::Eras::SetCurrentEra | 0x1e7eb0 | 2 | event, signal |
| 14 | Player::Governors::PromoteGovernor | 0x2df340 | 2 | event, signal |
| 15 | Player::Influence::ChangeTokensReceivedModifier | 0x2e94c0 | 2 | event, signal, edit() |
| 16 | Player::Influence::ClearAllTokensReceived | 0x2e9730 | 2 | event, signal, edit() |
| 17 | Player::Instance::AddAgenda | 0x2f7400 | 2 | event, signal, edit() |
| 18 | Rules::Appeal::Instance::UpdateOnly | 0x362420 | 2 | event, signal |
| 19 | Unit::Instance::SetProcessedTurn | 0x3a5ee0 | 46 | event |
| 20 | Player::Espionage::AddSpyMission | 0x2cf660 | 14 | event, edit() |
| 21 | Rules::Espionage::Shared::Instance::AwardCounterYield | 0x64e8e0 | 12 | event |
| 22 | Unit::Placement::CompleteMovement | 0x3afd30 | 10 | event |
| 23 | Player::Diplomacy::ApplyGrievancesFromPlayer | 0x29e9d0 | 9 | event |
| 24 | Combat::Manager::AwardJointWarExperience | 0x14fa10 | 8 | event, edit() |
| 25 | Player::Processor::SetTurnActive | 0x5de40 | 7 | event |

## Groups worth reading together
- **Rules::Espionage** (`CaptureSpy`, `KillSpy`, `ResetFailedSpy`, `ResetSpyData`, `AwardCounterYield`, plus `Player::Espionage::AddSpyMission`): spy-outcome logic; large functions with notifications and several virtual calls, so parts of the logic are hidden from the decompiler.
- **Emergency::Manager::StartEmergency**: very large function with many locals; not readable at a glance.
- **Map volcano twins** are analyzed in `functions/`.