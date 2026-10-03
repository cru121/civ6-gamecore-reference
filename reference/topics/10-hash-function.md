---
title: The identifier hash
order: 10
---
# The identifier hash

Operations, commands, events, notifications, moments and many other types are identified by a 32-bit value that is the **bitwise NOT of the standard CRC-32 of the upper-case name** (zlib `crc32`, then `~`).

```python
import zlib
def civ_hash(name): return (~zlib.crc32(name.encode())) & 0xffffffff
civ_hash("UNIT_MOVED")   # 0xBE121408
```

**Verified** on 351 of 352 events, all 224 notification types, 165 of 166 moment types and 152 enums in whole or part. Values are stored as signed 32-bit integers in the enums; the tables show both forms.

Use it to read magic numbers in disassembly (`cmp eax, 0x291d387e` is `MOVE_GREAT_WORK`) or to compute the id of a name without a lookup.
