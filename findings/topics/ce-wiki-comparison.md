# Comparison with the Community Extension wiki (cloned 2026-09-30 to `upstream_wiki`, last wiki edit 2025-07-17)

## What the wiki documents
* Pages: Home, Contributor's Guide (marked "Under construction"), Memory Manipulation, Events & Processors, Objects, Singletons & Namespaces, Configurations.
* Format per Lua method: one-line description, Parameters table (name, type, description), Returns table, optional example. Uncertainty is admitted in plain words
  ("Unknown", "Estimated use", "needs more testing").
* The Contributor's Guide only covers: install Ghidra, download the older symbol-bearing depot (`download_depot 289070 947510 <manifest>`), import the DLL and the `.map`, run
  `DemangleAll`. It ends with "to map these symbols to the latest version of GameCore you need the Version Control Manager. Tutorial available soon."
* "Known offsets" (Memory Manipulation page) lists five instanced offsets for `ObjMem`.

## The wiki's five known offsets, checked against the Linux layout (Verified)
| Wiki | Linux DWARF member | Result |
|---|---|---|
| Plot `0x4a` appeal (short) | `Plot::Instance.m_kVariants` 0x3c + `Variants1.m_iPlotAppeal` 0xe = 0x4a | exact; plain class, no shift |
| PlayerInfluence `0xb8` points x 256 | `Influence.m_xPointsEarned` wrapper 0xb0, value 0xc0 | exact after the -8 rule; the field is `m_xPointsEarned` (FixedPoint, x256) |
| Player `0xd8` "unknown" | `Player::IInstance`... `m_id` wrapper 0xd0, value 0xe0 | after -8: **the player id** (`m_id`) |
| UnitExperience `0xc` xp, `0x10` level | `Experience.m_iExperience` 0xc, `m_iLevel` 0x10 | exact; also `0x14 m_iStoredPromotions`, `0x8 m_bCanPromote` |
| Unit `0x128` owner | `Unit::IInstance.m_eOwner` wrapper 0x120, value 0x130 | exact after -8 |
All five match, and the rule "Windows = Linux - 8 for tracked-variable members, unchanged for plain classes" held for every one.

## Where we are equal or ahead
* The wiki's offset table has 5 entries; the Linux layouts give named members for every class (for example 140k types). The generated offsets in
  `linux-debug-symbols.md` are the same kind of information, larger and named.
* Uncertain semantics: the wiki says "Unknown" for `Player 0xd8`, `GetNeutralizedIndefinitely`, `ChangeNeutralizedIndefinitely` and the unknown booleans of
  `UnitManager.ChangeOwner`/`UnassignGovernor`. The Linux parameter and member names can name several of them (not yet done; see below).
* The missing tutorial ("map the symbols to the latest version"): our old->new map and method (76 % of functions, plus the verification steps) is exactly that
  missing part.
* The Linux depot (533502) with full DWARF is not mentioned in the guide.

## Where we are not there yet
* No Lua-facing API beyond the `ChangeBuildCharges` proof of concept and the archive prototype; the wiki is mostly Lua API pages.
* No per-method Parameters/Returns pages in the wiki format; our function notes are analysis notes (what the code does), not Lua reference.

## Possible cheap deliverables in the wiki's own format
1. A "Known offsets" table generated from DWARF for the classes `ObjMem` users meet (Plot, Unit, City, Player, Culture, Buildings, Unit experience ...).
2. The filled-in "map to the latest version" tutorial, with the map file as data.
3. Named answers for the wiki's "Unknown" entries.
