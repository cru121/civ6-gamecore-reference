---
title: Event order and patterns from a large mod
order: 20
---
# Event order and patterns from a large mod

> **Source and credit.** Everything on this page comes from reading **Gedemon's Civilization Overhaul** (GCO), a large gameplay mod by **Gedemon** ([github.com/Gedemon/Civ6-GCO](https://github.com/Gedemon/Civ6-GCO), the state of 2021-05-20, Gathering Storm era). GCO listens to, chains and invents many events, and the author left comments about what crashes, what fires too early and what fires in which order. Those comments are the valuable part. We read the code, checked the line references below against the repository, and wrote the prose ourselves; we did not copy code. The repository has no license file, so please read the original for the full context and credit Gedemon if you reuse an idea.
>
> **Status.** Nothing here was run by us. Claims marked *author's comment* are what GCO's code says, not something re-tested on the current game. File references are relative to the repository (`Scripts/GCO_X.lua` is written `X.lua`).

## Which kind of event is it?

| Family | Meaning | Lua state |
|---|---|---|
| `Events.X` | The engine reports that something **already happened**; a handler sees the changed world. See [Lua events](enums/LuaEvents.md). | gameplay and UI, each state sees its own set |
| `GameEvents.X` | Two things share the name: engine **hooks** (such as `OnGameTurnStarted`) and **names a mod invents** (`GameEvents.Foo.Add(fn)`, `GameEvents.Foo.Call(...)`; no declaration needed). | gameplay only |
| `LuaEvents.X` | Plain publish/subscribe inside **one** Lua state. Nothing is declared. | one state |

The UI state cannot see the gameplay `GameEvents` unless a script exports the table (GCO: `ExposedMembers.GameEvents = GameEvents`, ModUtils.lua:137), and gameplay cannot see UI `LuaEvents` unless the UI exports them (ContextFunctions.lua:846). The author's rule of thumb (comment at UI/CityBannerManager.lua:4188): **gameplay to UI = `LuaEvents`; UI to gameplay = a player operation.** For the second, GCO uses [`EXECUTE_SCRIPT`](operations/player-operation/EXECUTE_SCRIPT.md) with an `OnStart` name, which makes the engine fire `GameEvents.<OnStart>(playerID, parameters)` on the gameplay side.

## Starting a mod safely

- `GameCoreEventPublishComplete` fires very often and is used by GCO as a **scheduler tick**: it polls "is every script loaded?" (ModUtils.lua:444-460), resumes coroutines and runs timers. It is not in the engine event list on this site, which covers GameCore only. *Author's comment:* "called frequently, keep it clean".
- Readiness pattern: every script sets a flag in `ExposedMembers` when it finishes loading; one poll waits for all flags (including UI ones), removes itself and fires a single custom `GameEvents.InitializeGCO`. This avoids relying on load order across states.
- `LoadGameViewStateDone` is the "game is loaded" moment (GameScript.lua:106). `LeaveGameComplete` is the unload; `ExposedMembers` **survives** an unload, so tables stored there must be cleared by hand (ModUtils.lua:2070-2106).
- Map events (`ImprovementAddedToMap`, `FeatureAddedToMap`, `RouteAddedToMap`...) fire during map generation, before your mod has initialised. Every plot handler in GCO starts with an "initialised?" check.

## A per-player "turn started" that does not crash

The engine hooks `GameEvents.PlayerTurnStarted`, `PlayerTurnStartComplete` and `OnGameTurnStarted` are **unsafe for work that touches units or unit flags**. *Author's comments:* PlayerScript.lua:1333 ("makes the game crash" in the unit flag manager), UnitScript.lua:819-824 and :5427, and GameScript.lua:278 (tested 2017-10-25). GCO works around it in two ways:

1. It builds its own "player turn started" from four real events: `LocalPlayerTurnBegin`, `RemotePlayerTurnBegin(playerID)`, `RemotePlayerTurnEnd(playerID)` and `LocalPlayerTurnEnd(playerID)` (PlayerScript.lua:1338-1408, 1615-1618). Single player: when one player's turn ends, start the next ever-alive player's. Network multiplayer: every player's turn is started from the local begin event, to avoid desyncs. A stored "current turn" number per player makes it run once even if several of the four fire.
2. A flag turned unsafe on `OnGameTurnStarted` (ModUtils.lua:812) and safe again on its own turn-start event; UI refreshes of unit flags are skipped while it is unsafe.

GCO tried other triggers and kept the dead experiments in ModUtils.lua:2129-2151. *Author's comments:* the `GameCoreEventPublishComplete` + `IsTurnActive()` poll is "first to fire, but not early enough", and `player:IsTurnActive()` is always false for player 0 under automation.

## Ordering facts (all author's comments unless noted)

| Fact | Where |
|---|---|
| **Combat is resolved before any Lua event.** By the time `Combat`, `UnitAddedToMap` or a turn event runs, `unit:GetDamage()` already reflects all queued fights. GCO keeps its own virtual hit points and reconciles in `UnitDamageChanged` (it reverts healing it did not ask for: the engine hard-heals pillagers). | UnitScript.lua:612-624, 5470 |
| **`CityAddedToMap` comes before `CityInitialized`.** Create data on the first; do anything that needs the city's plots on the second (the plots are not initialised at the first). | CityScript.lua:582-583, 8111-8115; ModUtils.lua:1731 |
| **`UnitAddedToMap` comes before `CityProductionCompleted`** for a unit built in a city, so work that needs the production result must wait. `PlayerTurnActivated` is "the first general event called after all `CityProductionCompleted` for a player". | UnitScript.lua:928 |
| **`GovernmentChanged` / `GovernmentPolicyChanged` fire before the change is visible** to policy queries; GCO delays the recalculation with a delayed coroutine instead of reading it in the handler. | CityScript.lua:8117-8150 |
| **`UnitOperationStarted` for `REMOVE_FEATURE` fires after the world changed**: the feature is already gone and the builder may be off the map. GCO reads the feature from a cache it keeps per plot. | UnitScript.lua:6821-6823 |
| **`UnitMoved` is once per step, `UnitMoveComplete` once per command.** Do not change state in `UnitMoved` (multiplayer desync warning). | UnitScript.lua:6921-6950 |
| **`UnitTeleported` also fires when a unit steps onto the tile of a unit it just killed.** | AltHistScript.lua:123 |
| Same-turn, same-plot correlation is fragile: every synthetic event below assumes the engine's event order never changes. | CityScript.lua:664 |

## Recipes: events the engine does not give you

The engine has no "city captured", "unit captured (with the new unit id)", "settler founded a city" or "feature removed" event. GCO reconstructs them by matching events that do exist.

**City captured** (ModUtils.lua:1257-1316). When a city changes hands its city-centre district is removed from the old owner: `DistrictRemovedFromMap(playerID, districtID, cityID, x, y)`. Store `{turn, playerID, cityID}` under the key `"x,y"`. Then `CityAddedToMap` on the same plot, same turn, with `city:GetOriginalOwner()` equal to the stored player, means a capture, not a new city.

**Unit captured, with the new id** (ModUtils.lua:1646-1688). `UnitCaptured` gives the old unit but not the new one. Remember the id from `UnitRemovedFromMap`, count the `UnitAddedToMap` events that follow, and in `UnitCaptured` accept it only if the removed unit matches, the added unit belongs to the capturing player, and exactly one unit was added. This relies on the removal firing first (author's comment "first called").

**Settler founded a city** (ModUtils.lua:1690-1731). On `UnitOperationStarted` with `FOUND_CITY` remember the settler; remember any feature removed at the site; complete in `CityInitialized` by checking the founder equals the city owner.

**Feature removed.** `FeatureAddedToMap` and `FeatureRemovedFromMap` carry only `x, y`. Keep the last known feature type per plot (GCO: `plot:SetCached("FeatureType", ...)`) and compare on each event: previous set and now none means it was removed (PlotScript.lua:3954-3967).

**Learn the order yourself.** GCO binds about 18 engine events (`AppInitComplete`, `GameViewStateDone`, `LoadScreenContentReady`, `MainMenuStateDone`, `RequestSave`, `EndGameView`...) to functions that only print their name, then reads the log (ModUtils.lua:2153-2187). The list also shows which names exist on the UI side.

## Parameters seen in use

The Modding Companion list used for the [Lua events](enums/LuaEvents.md) page disagrees with real handlers in a few places. Where the vanilla game's own Lua uses the same event with more parameters, that is stronger evidence than a third-party mod; the table says which applies. The per-event notes are on the Lua events page, section "Notes from real use".

## What was left out

The original write-up (kept by the project, not published) also lists GCO's own custom events, its dead code and its wiring bugs. Those describe GCO, not the game, so they are not reproduced here. One is worth knowing as a trap: `GameEvents.X.Add(...)` written where `.Call(...)` was meant fails silently when nothing else subscribes (GCO's `CapturedCityInitialized`, ModUtils.lua:1308), and `Events.SaveComplete(handler)` without `.Add` (UnitScript.lua:918) never subscribes.
