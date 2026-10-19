---
title: Virtual function tables
order: 75
---
# Virtual function tables

Many GameCore classes (`Unit::Instance`, `Map::Instance`, the notification and deal-item classes, the AI jobs and others) have virtual functions. A virtual call in the Windows code looks like `mov rax,[rcx]` followed by `call [rax+0x58]`: the object's first 8 bytes point to a table of function addresses, and `0x58 / 8 = 11` is the **slot** number. The class pages under [Class layouts](layouts/index.md) now list this table in a "Virtual functions" section: slot, byte offset, method name and the function's address in the current build.

## How the tables were built

1. The Linux port keeps its vtables in the data segment with relocations. Reading them gives, for each class, the function in each slot with its full name and signature (8,394 vtables, 2,189 `GameCore::` classes).
2. The Windows build has no RTTI to find its vtables, but the symbol build names them (6,209 `vftable` symbols). Reading the slots there gives code addresses.
3. For the 1,218 classes present on both sides the two tables are aligned slot by slot. The Linux compiler stores two destructor slots where MSVC stores one, and the Linux port merges interface slots into one table, so the alignment is a longest-common-subsequence match on method names rather than a plain index match. 9,560 slots match by name.
4. The new build's own vtable is read from the mapped address and gives the current-build address of each function. These agree with the older function map in 33,000+ slots; the 610 disagreements are folded identical functions (several small functions share the same code and one name wins).

## What you can use it for

- **Resolving a virtual call**: take the class and the offset from `call [rax+off]`, look up the slot on the class page. The listed function is what that class's own vtable holds. The object may be a subclass that overrides the slot, so a call through a base pointer can land elsewhere; classes that share a base list the same slot.
- **Naming Windows functions**: a slot ties an unnamed or folded Windows function to the Linux method name and signature.
- **Mapping functions to the current build**: about 3,500 functions of the symbol build that had no mapping to the installed build got one from their vtable slot (marked `vtable-derived` in the function index).

## Limits (read before relying on it)

- **Inferred**, not verified in a running game. Alignment is by name; it is wrong for the 211 Windows slots that have no Linux counterpart (shown as missing) and can swap overloads that MSVC and Itanium order differently.
- **One table per class.** Classes with several Windows vtables (multiple inheritance, e.g. the volcano feature manager) are not covered; which table `this` points into is not known from the vtable alone.
- **Only the class's own table.** Slots inherited from a base are listed with the owner class, but secondary base-class tables are not.
- **Names of folded functions**: when several functions share identical code the Windows symbol name is an arbitrary one of them; the Linux method name in the table is the reliable one.

## Virtual calls on `this`

For methods of classes with a single vtable, a scan of the Windows code finds calls of the form `call [this->vptr + slot]` and resolves them through the table: 598 call sites in about 420 methods. The same scan on the Linux port gives an independent check: of the 384 sites the Linux code lets us compare, 376 agree (98%); 214 could not be compared because the Linux build inlined the call. This is only about 9% of all indirect calls in those methods; the rest go through other objects, whose type is not known without full data-flow analysis. Edges that agree are included in the call graph used for the function pages.

## Checked in a running game

To see which functions virtual calls really reach, every indirect call site of the game code (13,529 of them) was briefly instrumented in a running game and the call targets were recorded, a few hits per site, over six turns. That gave 2,086 observed caller-to-target pairs; 965 of the targets are functions that sit in a vtable slot, and 137 pairs come from sites that reached more than one target, i.e. real overrides in use. Of the statically inferred `this` calls whose caller ran, 112 of 133 (84%) were confirmed by a recorded target; the rest may simply not have been taken in that short run. The observed pairs are part of the call graph behind the function pages. Coverage is partial: only code the six turns exercised is covered (no combat, religion or diplomacy-heavy turns).
