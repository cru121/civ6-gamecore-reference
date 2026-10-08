# Civ6-GameCore-reference

A searchable reference for Civilization VI's GameCore, for Lua modders and Community Extension contributors: look up any Lua method and see its signature, what its arguments and results mean, and which engine function it calls underneath. It also lists the engine functions that have no Lua route at all.

I made it because the engine knows far more than the Lua API shows, and the existing community references stop at the Lua surface. It is a work in progress and I would like help checking it.

**Browse it:** https://cru121.github.io/civ6-gamecore-reference/ (GitHub Pages, served from `docs/`)

## What is in it
- **Lua API**: 1,920 methods on 124 objects, with recovered signatures, argument and return meanings.
- **Operations, commands, enums, events**: identified with handlers, parameters and hashes.
- **Modifier effects, requirements and collections**: the database side (`EFFECT_...`, `REQUIREMENT_...`, `COLLECTION_...`), with the engine class, addresses and the engine functions each one calls.
- **Class layouts and globals**: member offsets and typed global addresses, for raw memory access (`Mem`, `ObjMem`) via the Community Extension.
- **Native functions** that have no Lua route today, and a **Dev CE (experimental)** section describing engine functions that [Dev CE](https://github.com/cru121/civ6-dev-ce), an experimental fork of the Community Extension, adds to Lua (997 methods on 43 objects, with test status per method). Dev CE has a release zip with the DLL and the source (v0.2.0-experimental), it is single-player only and has known unsafe functions; read its README first.
- **Game text (bring your own)**: each modifier effect has a "where the game uses it" page. Build a strings file from your own copy of the game and the pages show the in-game wording, in your language, and search finds entries by it. Nothing is uploaded and no game text is published.
- **World Builder from Lua**: all 99 World Builder methods grouped by manager, with call forms, return values and undo behaviour.
- **findings/**: per-function analysis notes and topic pages (great works, events, the identifier hash, build differences).

Every entry is labelled by how you can use it: available in the vanilla game, needs the Community Extension, or engine internals.

## How much to trust it
**Much of the text is AI-assisted and mostly untested in a running game.** Everything is derived from static analysis, and descriptions written by an AI assistant are flagged as such on the page. *Verified* means read from the decompiled code, not tested in a running game. *Inferred* entries carry a confidence word. Only items under an "Observed in-game" heading were seen in a running game. Corrections are very welcome, please open an issue or pull request.

## Layout
```
docs/        the generated static site (open docs/index.html through a web server, not file://)
reference/   source of the site: data/ (generated JSON), curated/ (hand-written notes), topics/, schema/, tools/
findings/    function-level notes and tables
```
`python reference/tools/build.py` regenerates the site from `reference/data` and `reference/curated` (needs `jsonschema`). It writes to `reference/site`; copy that folder over `docs/` to update the published pages. `python reference/tools/check_links.py` checks the result. The extraction scripts in `reference/tools` need the original analysis workspace and are included for transparency, not as a one-command build.

## Data and tools
- **`data/old_to_new_offsets.tsv`**: function names of an older, symbol-carrying build mapped to addresses in the current Steam build (15038592; build 15296837 has the byte-identical GameCore DLL): 38,412 of 43,803 functions, nearly all code bytes. How it was made and how far to trust it: [`data/README.md`](data/README.md).
- **`tools/frida-live`**: attach Frida once to a running Civ VI and send it commands or JavaScript, call native functions by name, run Lua inside the game, and get a **named crash report** (function, registers, backtrace) when the game faults. Single-player lab tool, read [`tools/frida-live/README.md`](tools/frida-live/README.md) and `LESSONS.md` first: detaching Frida crashes the game. Ready-made settings for builds 15038592 and 15296837 (same GameCore DLL): `tools/frida-live/builds/15038592/run.bat`.
- Attaching a debugging tool to a game is at your own risk. Use it in single-player on disposable saves.

## Contributing and known gaps
- Spotted a wrong signature, meaning or address? Open an issue or pull request. Reports of what you observed in a running game are the most valuable.
- Offsets and addresses are for the installed Windows build the analysis used; a game update can shift them.
- Only a small share of entries have hand-written notes (28 curated); the rest are generated.
- Dev CE functions: the descriptions are AI-written from decompiled code and not human-reviewed; 25 of 997 methods have an effect confirmed in the running game, for most of the rest nobody has seen what they do.

## Sources and credits
Built on the work of Sukrit Tan (Civilization VI Modding Wiki), ChimpanG and WildW (Modding Companion 2.0), and Wild-W and contributors (Civilization VI Community Extension). See the site's home page for the full list. Names and layouts are recovered from debug symbols shipped with an older build, following the method in the Community Extension contributor's guide, and cross-checked against the Linux port's DWARF data.

## Disclaimer
Unofficial fan research. Not affiliated with or endorsed by Firaxis Games, 2K or Take-Two. This repository contains no game binaries, assets or scripts, only notes, addresses and short call-site snippets. Intended for modding and understanding the game; do not use it to cheat in multiplayer or circumvent protection.

## License
Documentation and data: [CC BY 4.0](LICENSE). Tools and scripts (`reference/tools`, `tools/`): [MIT](LICENSE-CODE).
