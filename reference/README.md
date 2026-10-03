# Civ VI GameCore reference (source)

Structured-data-first reference for the Civ VI GameCore analysis.

```
data/      generated JSON (tools/extract.py) - never hand-edit
curated/   hand-written YAML notes keyed by entity id (summary, usage, notes with status + evidence, related ids)
topics/    narrative pages, markdown with front matter
schema/    JSON Schema for the entity records
tools/     extract.py (artifacts -> data/), build.py (validate + merge + render), quote_yaml.py (helper)
docs/      generated markdown pages (source for any static site generator)
site/      generated self-contained HTML with client-side search (deployable to GitHub Pages as is)
dist/      JSON bundles and compact text digests for AI use (dist/ai/*.txt)
```

Lua signatures: decompile every registered wrapper (Ghidra DecompList.java over `linux_depot/out/wrapper_rvas.txt`), then `python tools/lua_signatures.py` (writes data/lua_signatures.json) and validate with `python tools/sig_validate_lua.py` (compares argument counts with how the game's own Lua calls the methods).

Rebuild: `python tools/lua_signatures.py && python tools/extract.py && python tools/lua_return_usage.py && python tools/lua_return_meanings.py && python tools/lua_arg_meanings.py && python tools/op_params_scan.py && python tools/op_params_build.py && python tools/extract_layouts.py && python tools/extract_ce_native.py && python tools/extract_devce.py && python tools/extract_index.py && python tools/build.py && python tools/check_links.py`. The build fails on schema errors, duplicate ids,
dangling `related` links and hash collisions.

Every entity carries an availability (vanilla / needs the Community Extension / engine internals); the site colours sections green / amber / grey. CE methods come from the CE wiki tables and source, native functions from the gap analysis, our function notes and the CE offsets.

Scope: Lua methods (1,920), operations and commands (154), enums (26), class layouts (1,915), globals (1,314), 28 curated notes, 25 checked Windows offsets (curated/_windows_offsets.yaml), 2 topic pages. Lua methods link to the community reference by Sukrit Tan (external) instead of copying its text.
What each argument means comes from the C++ parameter type and from the arguments the game's own Lua passes (tools/lua_arg_meanings.py).
What a returned number means comes from the C++ type the wrapper returns and from how the game's own Lua uses the result (tools/lua_return_usage.py, lua_return_meanings.py).
Return values are reconstructed by replaying the wrapper's pushes on a model stack (tools/lua_returns.py): table fields, array element types, semantic types from the called C++ function.
Known rough edges: function names in "Functions called" are the shortened names from the analysis tables; Lua
signatures are recovered from code (1,724 of 1,920 high confidence; unparsed helpers are flagged); no events or build-difference entity types yet.

The searchable all-functions page (native/all.html) loads function_index.json (8 MB) with fetch(), so view the site through a web server (GitHub Pages, or `python -m http.server --directory site`), not file://.

A generated coverage and confidence page (topics/90-coverage.md) comes from `python tools/coverage.py`; run it before `build.py`.
