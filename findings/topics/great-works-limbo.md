# Do great works in "limbo" (exist, but sit in no slot) grant anything?

Status: **observed in a real game, one experiment, single player** (2026-09-29). Tool: `../../frida/gw_limbo.js`.
A "limbo" work here means: a game-wide great work record exists and is assigned to a player, but no city slot holds it.

## Setup
Fresh single-player game, one city (the capital, with the Palace). The Palace has exactly one great-work slot and it accepts
any work object type. Works were created with the game's own functions (`FindOrAddGreatWork`, `SetGreatWorkPlayer`) and
placed with the game's own `ReceiveGreatWork`.

## What was observed
1. Baseline (no works): 0 works in slots, no yields, 0 tourism.
2. Work 0 (a Great Writing) created and placed: it landed in the Palace slot. Per-city getters then read
   **culture +2, tourism +2** (`GetYieldFromGreatWorks`, `GetTourismFromGreatWorks`).
3. Trying to create/place work 0 again: `ReceiveGreatWork` refused ("no room") and no new record was made. The game does not
   place the same work twice (at least within one city).
4. Work 1 (a different Great Writing) created and assigned to the player; `ReceiveGreatWork` returned false (Palace full):
   - `HasGreatWorkBeenCreated(1)` = yes; the game-wide record count went 1 -> 2 (so the work exists independent of any slot);
   - no city's slots held it;
   - the report was unchanged: **still culture +2, tourism +2**, works in slots = 1.

5. **Great Works screen (user screenshot, same session, after the limbo work existed):** header "Providing: culture 2, tourism 2",
   "Great Works 1", "Display Spaces 1"; only the Palace work is shown. The limbo work is neither counted nor displayed.

## Conclusion (so far)
Through the game's own per-city yield and tourism getters, and on the Great Works screen's totals, a limbo work contributes
**nothing**: the record persists, the yields come only from slotted works. The screen also has no place to show it. This supports the archive idea: an unslotted work is "owned but inactive" without extra work.

6. **Save and reload (same session):** after saving and loading, `HasGreatWorkBeenCreated` still said the limbo work exists and
   the report matched the pre-save one. So an unplaced work is part of the saved game state.

## Archive swap experiment (2026-09-30, same save reloaded in a fresh game session)
Start: work 0 in the Palace, work 1 in limbo (culture 2, tourism 2).
1. `RemoveGreatWork` on work 0 through the game's `edit()` accessor (city+0xca0), run at turn start: returned slot 0.
   Report: 0 works in slots, **no yields, 0 tourism**. The work still exists (record kept, player field 0), in no slot.
2. `ReceiveGreatWork` for work 1: placed in the freed Palace slot. Report: culture 2, tourism 2.
So a work can leave a slot, stay owned but inactive, and be placed later on demand, with the game's own functions.
After saving and reloading, the user reported (Great Works screen) that a work is shown in the Palace and the yields are present.
So the placement made by `ReceiveGreatWork` persisted. Identity check (user, tooltip): the Palace holds the second work ("Pratima-nataka", Great Writing, created 950 BC, culture 2 and tourism 2 per turn); the first (created 1000 BC) was the one moved out. Tooltip "Created by" is empty for works made with `FindOrAddGreatWork` alone (see [that note](../functions/Culture_FindOrAddGreatWork.md)). Not yet confirmed with the tool: that
the other work (0) is still a limbo record after this second reload (the tool used a stale module address after the game
reloaded GameCore; it now re-resolves it). Limbo persistence itself was already confirmed in the first reload test.

## Not yet checked
- The top-bar per-turn numbers, score and victory screens, and modifiers that count "great works owned". The getters are
  per-slot by construction, so other code paths could still count a limbo work. (The Great Works screen totals were checked
  and show no effect.)
- Whether it can be placed later once a slot opens (`place T`), and how the Great Works screen shows or ignores it.
- Only Great Writings and one city were tested. Palace-specific rules (e.g. its extra non-unique-person yield) not explored.

## Tool note
`RemoveGreatWork` and `IsInCity` take the work's **list index** (position in the game-wide list), not its type. In the first
experiment the two matched only because works 0 and 1 were created in order. The tool now converts type to list index.
