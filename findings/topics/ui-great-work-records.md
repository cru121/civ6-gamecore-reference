# Reading great work records from UI Lua: what is safe, and when the screen is reachable

Status: the code facts are **read from the decompilation**; the crash was **observed in a real game** (2026-09-30).

## Record getters (UI side, `Game.*`)
| Function | Bounds check on the index? | Notes |
|---|---|---|
| `Game.GetGreatWorkPlayer(i)` | **Yes**: returns -1 when `i` is past the end of the game-wide list (also -1 for a record whose player is unset) | Safe to call with any index. Its result is the record's player field. |
| `Game.GetGreatWorkDataFromIndex(i)` | **No**: reads `record[i]` blindly | Returns a table with `TurnCreated`, `GreatWorkType`, `CreatorName`. For artifacts and hero works `CreatorName` comes from the record's player. |
| `Game.GetGreatWorkTypeFromIndex(i)` | not read in detail | Only used by the base UI with real indexes. |

**Observed:** a UI script that looped `i = 0, 1, 2, ...` calling `GetGreatWorkDataFromIndex(i)` until it returned nil crashed the
game (`EXCEPTION_ACCESS_VIOLATION`, "Error reading address 0x15") the first time `i` went past the last record. `pcall` does not
help: it is a native fault, not a Lua error. There is no record-count getter in the UI API.

**Safe pattern:** for each index call only `Game.GetGreatWorkPlayer(i)`; call the other readers only when it returns a player you
care about (which proves the record exists).

## When can the player reach the Great Works screen? (a minor point in practice)
The launch bar shows the Great Works button only once `m_isGreatWorksUnlocked` is true. It becomes true when the game raises the
great-work-created event, or when a refresh (after a deal or a city capture) finds a work in one of the local player's city slots.
A work that exists only as an unplaced record triggers neither. **Observed:** with two unplaced works and nothing in any slot, the
button did not appear until a work had been placed in a slot and a turn had passed.

The screen itself opens whenever `LuaEvents.LaunchBar_OpenGreatWorksOverview()` is raised, so a mod can open it without the button.

## Related
- [Do great works in limbo grant anything?](great-works-limbo.md)
- Archive design: `C:\stuff\claude\gw-archive\DESIGN.md`

In practice this rarely matters: a work is lost only when every slot is full, so a work is normally already slotted and the screen is
already unlocked. The gap is an early relic before any relic building exists (see the archive design notes).
