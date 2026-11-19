# data/

## old_to_new_offsets.tsv

A map from function addresses in one build of Civ VI's `GameCore_XP2_FinalRelease.dll` (the "symbol build", an older build that still carried function names) to the same functions in the
current Steam build (**15038592**). It lets you attach names to addresses of the game you actually play, for example in a debugger, in Ghidra, or in the Frida tools of this repository
(`tools/frida-live`).

Columns (tab separated, `#` lines are comments): `old_rva  new_rva  category  size  name`
* `old_rva` / `new_rva`: offset from the module base (RVA) in the symbol build / in the current build. Empty when no counterpart was found.
* `size`: function size in bytes in the symbol build.
* `name`: the qualified C++ name from the symbol build (e.g. `GameCore::Player::Culture::GetCultureYield`). Overloads share a name.
* `category`: how the counterpart was found:

| category | functions | meaning |
|---|---:|---|
| unique | 20,894 | exactly one function in the current build has matching bytes (relative operands masked) |
| unique-reordered | 1,776 | a single match after allowing for moved or reordered code |
| resolved | 5,336 | an initial ambiguity settled by further evidence (neighbouring functions, order) |
| callgraph-callee | 2,224 | inferred from the call sites of functions that are already mapped (the callee) |
| callgraph-caller | 3,013 | inferred the same way, the caller (candidates filtered by agreement with mapped callees) |
| vtable-derived | 3,538 | read from the same slot of the same class in the current build's own vtable (the old function sits in a vtable slot; see the "Virtual function tables" topic of the reference) |
| datashift-verified / -probable / fuzzy-best | 15 / 12 / 1 | functions whose code is identical apart from moved data addresses, or the best fuzzy match |
| ambiguous | 3,595 | **several candidate addresses** (a comma separated list, cut at six entries with `...`); cannot be told apart from the bytes |
| unmatchable | 3,387 | no counterpart found; together only 42 KB (compiler-generated initialisers and stubs) |
| none | 12 | no counterpart found |

That is 43,803 functions, 40,404 of them (92.2%) with an address and nearly all of the code bytes. The ambiguous group is mostly tiny functions (median 71 bytes): the MSVC linker
folds functions with identical code into one copy (identical code folding, `/OPT:ICF`), templates instantiated for same-layout types compile to the same bytes, and compiler-generated
initialisers look alike. In such a case one address honestly has several names.

The matching scripts are not part of this repository, so the category descriptions above are summaries, not a specification.

### Trust
* **unique / unique-reordered / resolved**: very likely right. **callgraph-*** : inferred, checked against already mapped neighbours, still an inference. datashift / fuzzy: look at them before relying on them.
* Names come from debug symbols that shipped with an older build (the method described in the Community Extension contributor's guide). Where the current build changed a function, the
  name still describes the old function; `findings/topics/build-differences.md` lists what is known to differ.
* The map is only valid for build 15038592. After a game update the new addresses move and the file has to be rebuilt.

### Using it
`python tools/tsv_to_symbols.py` turns it into `symbols.json` (`{"Qualified::Name": [rva, ...]}`), which `tools/frida-live` reads. That script keeps only rows with a single address from the
trustworthy categories (about 31,000 names) and leaves out the ambiguous ones. For a quick lookup: `grep -P "\tGameCore::Player::Culture::" data/old_to_new_offsets.tsv`.

### Licence and provenance
The compilation (the matching work and this file) is released under [CC BY 4.0](../LICENSE). The names themselves are Firaxis' identifiers; the file contains no game code or binaries.
Not affiliated with or endorsed by Firaxis or 2K.

## Build 26595377 (2026-11-19)

The Steam update of 2026-11-19 kept the GameCore code but relinked it, so most addresses moved (see `findings/topics/patch_26595377_relink.md`). The files below carry the maps over to the new build. They were derived by matching functions of the old and new `GameCore_XP2_FinalRelease.dll` (relative operands masked); leaf functions and thunks without a `.pdata` entry were found by position and bytes. `.data` globals of the XP2 DLL did not move, `.rdata` addresses did. Status: addresses verified against the bytes of the new DLL where a check is named; behaviour in the running game was tested for the addresses Dev CE uses, not for the rest.

* **`old_to_new_offsets_26595377.tsv`**: the same table as `old_to_new_offsets.tsv` (same columns, same 43,803 rows, same names) but `new_rva` is the address in build 26595377. 36,516 rows have a single address; about 300 rows that had one in the 15038592 table are blank here because the position could not be confirmed (no guess). Use it to find a function by its C++ name in the current game.
* **`ce_offsets_26595377.tsv`**: every hard-coded GameCore address (5 to 7 hex digits) of the Community Extension source (the constants of `AI.h`, `Main.cpp`, `GameProcessor.cpp` and so on), with its location, constant name, the 15038592 address, the 26595377 address, how it was found, and the symbol name(s) at the old address. 70 literals: 62 through the function map, 6 leaf functions or thunks (position plus bytes), 1 data address, 1 that is a comment inside a function (no translation).
* **`gc_xp2_old_to_new_26595377.tsv`**: the function map itself, `old_rva new_rva size status` for each of the 59,083 functions with a `.pdata` entry in the XP2 DLL (15038592/15296837/26407122 RVA -> 26595377 RVA; status `same`, `changed` = a few masked bytes differ, `moved` = relocated far, matched by hash, `unmatched` / `new` = no counterpart).
* **`gc_xp2_data_old_to_new_26595377.tsv`**: data addresses (rows `old new votes`) found through rip-relative references inside matched functions; `votes` is the number of references that agreed.

The 15038592 table above is for builds 15038592, 15296837 and 26407122 only; for 26595377 use the files in this section.
