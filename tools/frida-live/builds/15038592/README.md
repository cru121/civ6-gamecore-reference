# Build 15038592

Ready-made settings for the Steam build that `data/old_to_new_offsets.tsv` was made for (`GameCore_XP2_FinalRelease.dll`).

```
tools\frida-live\builds\15038592\run.bat
```
creates `symbols.json` from the TSV on the first run (`tools/tsv_to_symbols.py`) and starts `live_daemon.py` with the right tick and turn hooks.
Then, from `tools\frida-live`:
```
python civ.py crash             # reporter status: symbols loaded? GameCore found?
python civ.py crash test        # simulated report from the game thread
python civ.py sym Culture       # search the symbol table
```
If your build is different (the game was patched, or you play another edition) the addresses are wrong: a hook on a wrong address can crash the game. Check one function first with
`python civ.py prologue Game::Culture::Get` and compare with what you expect, or rebuild the map for your build.

## Example: examples/gw_limbo.js
A larger real command file (about 40 KB) written during our Great Works research. It shows most of what the framework can do in one place: calling native functions by symbol name, reading the game's
internal tables (great work records, city building slot lists, relic slots) with raw memory reads, writing game state on the game thread, and checking a hypothesis with a read-only command before and after a write.
Background: `findings/topics/great-works-limbo.md`, `great-works-loss-paths.md`, `ghost-great-work-slots.md`, `great-work-trading.md`.

```
copy examples\gw_limbo.js ..\..\cmds\          (the daemon loads it within a second; delete the copy to unload it at the next game start)
python civ.py "records limbo"                  READ-ONLY: great works that exist but sit in no slot
python civ.py "ghosts"                         READ-ONLY: works held by a building the city no longer has
python civ.py "slots ROME"                     READ-ONLY: dump one city's great work slots
python civ.py "report"                         READ-ONLY: per-city works, yields, tourism
```
**Read-only first.** `spawn`, `limbo`, `place`, `remove`, `removeraw`, `makeghost`, `unghost`, `rmbuilding`, `hut`, `relicbase`, `reliclimbo`, `propset`, `tag` WRITE game state
(they run on the game thread): use them on a disposable single-player save only. The addresses and struct offsets inside are for build 15038592; on any other build they are wrong.
The header comment of the file describes every command.
