# Event data fields as read by the exe handlers

Method: Ghidra headless run of `tools/TraceBatch.java` on `ghi-exe` for 165 handler functions with known Windows RVAs (WorldView registration-order matches plus the other systems' mapped handlers); 152 traced, 138 gave direct field reads, 109 events.
`docs_proto/tools/extract_exe_event_data.py` picks the event data parameter (parameter 0 for WorldView handlers, parameter 1 for member handlers) and merges the reads per event. Reference page: `docs_proto/docs/exe/event-data.md`.
Raw trace: `linux_depot/out/exetrace/event_handlers_trace.jsonl`. **Inferred** throughout; checked against a hand disassembly of `TERRAIN_STATE_CHANGED` (plot at +4 and +8, state hash +0xc, flag +0x10).
- 376 fields over 109 events. The field count equals the Lua parameter count for 9 events (e.g. `UNIT_CAPTURED` four 4-byte fields at 0, 8, 0xc, 0x10 = currentUnitPlayerID, unitID, owningPlayerID, capturingPlayerID; `RESOURCE_VISIBILITY_CHANGED` plot at 8, resource at 0x10, visibility type at 0x14);
  for the others the page only shows both lists.
- Limits: the WorldView handler addresses are inferred by registration order; a wrong match shows another event's fields; reads through unresolved indirect calls and aliasing are missed; no field names exist in the exe; member handlers of non-WorldView systems may take the event in another parameter.
- Reuse: add handlers to `event_handlers_input.tsv` (`ev<id>|<rva>|<system>` TAB `rva:<rva>`) and re-run TraceBatch with `GHIDRA_HEADLESS_MAXMEM=8G` (see `tools/README.md`).
