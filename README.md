# Civ6-GameCore-reference

A reference for what Civilization VI's GameCore contains, for Lua modders and Community Extension contributors.

**Browse it:** https://cru121.github.io/civ6-gamecore-reference/ (GitHub Pages, served from `docs/`)

## What is in it
- **Lua API**: 1,920 methods on 124 objects, with recovered signatures, argument and return meanings.
- **Operations, commands, enums, events**: identified with handlers, parameters and hashes.
- **Class layouts and globals**: member offsets and typed global addresses, for raw memory access (`Mem`, `ObjMem`) via the Community Extension.
- **Native functions** that have no Lua route today, and a **Dev CE (experimental)** section describing engine functions that could be exposed.
- **findings/**: per-function analysis notes and topic pages (great works, events, the identifier hash, build differences).

Every entry is labelled by how you can use it: available in the vanilla game, needs the Community Extension, or engine internals.

## How much to trust it
Everything is derived from static analysis. *Verified* means read from the decompiled code, not tested in a running game. *Inferred* entries carry a confidence word. Descriptions written by an AI assistant are flagged as such. Only items under an "Observed in-game" heading were seen in a running game. Corrections are very welcome, please open an issue or pull request.

## Layout
```
docs/        the generated static site (open docs/index.html through a web server, not file://)
reference/   source of the site: data/ (generated JSON), curated/ (hand-written notes), topics/, schema/, tools/
findings/    function-level notes and tables
```
`python reference/tools/build.py` regenerates the site from `reference/data`. The extraction scripts in `reference/tools` need the original analysis workspace and are included for transparency, not as a one-command build.

## Sources and credits
Built on the work of Sukrit Tan (Civilization VI Modding Wiki), ChimpanG and WildW (Modding Companion 2.0), and Wild-W and contributors (Civilization VI Community Extension). See the site's home page for the full list. Names and layouts are recovered from debug symbols shipped with an older build, following the method in the Community Extension contributor's guide, and cross-checked against the Linux port's DWARF data.

## Disclaimer
Unofficial fan research. Not affiliated with or endorsed by Firaxis Games, 2K or Take-Two. This repository contains no game binaries, assets or scripts, only notes, addresses and short call-site snippets. Intended for modding and understanding the game; do not use it to cheat in multiplayer or circumvent protection.

## License
Documentation and data: [CC BY 4.0](LICENSE). Tools and scripts (`reference/tools`): [MIT](LICENSE-CODE).
