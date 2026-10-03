# Civ VI GameCore findings

Notes on what the game's C++ (`GameCore_XP2_FinalRelease.dll`) does, aimed at modders and Community Extension
contributors. Written to be merged later into public documentation.

## How the pieces fit
- `functions/`: one file per analyzed function. Fixed layout: metadata block, signature, **Verified** (read directly from
  the decompilation), **Inferred** (a guess, with a confidence word), **For modders**, related functions, caveats, and a
  block of script-generated facts.
- `topics/`: explanations that span several functions.
- `leads.md`: functions that look promising but are **not yet analyzed**.
- `index.md`: table of contents.
- Bulk data, one level up (`..`): `old_to_new_offsets.tsv`, `old_to_new_data.tsv`, `lua_registry.tsv`, `gap_list.tsv`,
  `gap_factsheets.tsv`, `gap_shortlist.tsv`, `callgraph_old.tsv`. Tools are in `../tools/`.

## Conventions
- **Two builds.** Names come from an older build that shipped with debug symbols (Steam depot 947510). Every address is given for both that build
  (`rva_symbol_build`) and the installed build 15038592 (`rva_installed_build`). RVAs are relative to the DLL load base.
- **Address mapping is computed, not given.** `address_mapping` says how the installed address was found (`unique`
  byte match, `resolved` by neighbors, `callgraph-*`). Prefer `unique`.
- **Verified vs inferred.** *Verified* means visible in the decompiled code. It does not mean tested in-game.
  Only items under an "Observed in-game" heading have been observed in a running game (via a log-only hook); everything
  else is unobserved. *Inferred* claims carry (Low / Medium) confidence.
- **Struct offsets** (`+0xd8` etc.) come from the symbol build. They carry over for functions whose bytes are identical
  in both builds; re-check them for functions that changed.
- **Script-generated blocks** are marked and can be regenerated with `../tools/factsheet.py`; do not edit them by hand.
- The Lua "exposure" line says whether a Lua method reaches the function, based on the registered wrappers plus the
  call graph. Virtual and indirect calls are invisible to that analysis.

## Provenance and use
Names and layouts are recovered from debug symbols shipped with an older build, following the method in the Community Extension contributor's guide. Analysis is
for modding and understanding only, in line with that guide (no cheating in multiplayer, no circumventing protection).

- **Linux debug-info cross-check.** Struct layouts and member names were cross-checked against the Linux port's DWARF data; see `topics/linux-debug-symbols.md`.
