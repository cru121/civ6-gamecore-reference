#!/usr/bin/env python3
"""Turn data/old_to_new_offsets.tsv into the symbol table the Frida tools read: {"Qualified::Name": [rva, ...]}.

    python tools/tsv_to_symbols.py [TSV] [OUT.json]
    default TSV  = ../data/old_to_new_offsets.tsv      default OUT = symbols.json in the current folder

Only rows whose address is a single value from a trustworthy category are kept (see data/README.md). Ambiguous rows (several candidate
addresses) and unmatchable/none rows are left out on purpose: a wrong name in a crash report is worse than no name.
Several overloads of one name give several addresses in order of appearance; the tools address them as `Name#2`, `Name#3`...
"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GOOD = {"unique", "unique-reordered", "resolved", "callgraph-callee", "callgraph-caller",
        "datashift-verified", "datashift-probable", "fuzzy-best"}


def main():
    tsv = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "data", "old_to_new_offsets.tsv")
    out = sys.argv[2] if len(sys.argv) > 2 else "symbols.json"
    syms = collections.defaultdict(list)
    skipped = collections.Counter()
    with open(tsv, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("old_rva"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 5:
                continue
            if p[2] not in GOOD or not p[1].startswith("0x") or "," in p[1]:
                skipped[p[2]] += 1
                continue
            syms[p[4]].append(int(p[1], 16))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(syms, f)
    print("wrote %s: %d names, %d addresses" % (out, len(syms), sum(len(v) for v in syms.values())))
    print("left out:", dict(skipped))


if __name__ == "__main__":
    main()
