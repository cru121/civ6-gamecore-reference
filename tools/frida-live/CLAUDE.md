# Instructions for an AI assistant using civ6-frida-live

You are helping a human reverse engineer Civilization VI's GameCore DLL with a live Frida channel. Read README.md and LESSONS.md first; this file is the short version of the rules.

## How to talk to the game
* The human starts `python live_daemon.py ...` (or you do, **only after they tell you a game is loaded**). Then every interaction is `python civ.py "<command or JavaScript>"` from this folder; output is plain text, exit code
  0 = ok, 1 = error, 2 = PENDING (game-thread job still waiting; the result is written to the daemon log, read it with `civ.py log`).
* Add capability by writing files in `cmds/` (hot reloaded in about a second, no restart). Prefer that over long one-off evals. Check JavaScript with `node --check file.js` before saving.

## Hard rules (each one cost a crashed game)
1. **Never detach, kill or restart the daemon while the game should stay alive.** Detaching crashes Civ VI. Ending the session = closing the game normally.
2. **Never attach while the game is starting or in the main menu.** Ask the human to confirm that a game is loaded.
3. **Never detach hooks.** `unhook()` only disables a callback. Do not put hooks on functions called thousands of times per second unless it is a short, deliberate recording.
4. **Never run Lua in a lua_State you have not just verified is a long-lived UI state.** Do not iterate over recorded states and call into them. Do not run Lua in a gameplay state captured earlier
   (they are short-lived coroutines).
5. **Never call a native or Lua function with a guessed argument list.** Wrong arity can fault natively. Use only signatures you have evidence for.
6. State-changing experiments only on a **disposable single-player save**. Say before you write game state. Prefer stubs/recording over real execution when you only want to verify plumbing.
7. If a command times out or returns PENDING, **do not retry in a loop**: check `civ.py status` and tell the human what you see.
8. Only one GameCore-replacing mod may be enabled. Verify which `GameCore*.dll` the game actually loaded before blaming your code.

## Working style
* Record facts as **verified** (seen in the running game or in the code) or **inferred**. Keep a log of what you ran and what happened; crashes are data: look at the Windows Application event log
  (`Application Error`, faulting module, exception code) and compare with LESSONS.md.
* Ask the human to restart the game when a change needs it (new DLL, new agent.js), and say exactly what to do afterwards (load a game, found a city, end a turn...).
* Do not commit or share the `.token` file, daemon logs, symbol tables or any data derived from game files.
