# Imports and dependencies of the Windows exe

Method: the PE import table of `CivilizationVI.exe` (DX11, Jul 2024) via pefile, with the number of exe functions that reference each import address table slot (`docs_proto/tools/extract_exe_imports.py`). Reference page: `docs_proto/docs/exe/imports.md`. **Verified**: the imports and caller counts. **Inferred**: the role of each DLL (from its name and functions).
- 890 imports from 38 DLLs; 874 are called. Not monolithic: game libraries next to the exe in `Base/Binaries/Win64Steam` are `HavokScript_FinalRelease.dll` (71 imports, the Lua VM), `DatabaseDLL_FinalRelease.dll` (4: `Database::Initialize`, `Shutdown`, `CreateConnection(char const*, int, IDatabaseLogger*)`, `SetDefaultLogger`),
  `Localization_FinalRelease.dll` (45: `Localization::GetCurrentLanguage`, `StringDictionary::GetLanguageCoverage`, ...), plus `bink2w64.dll` (22, video). Platform SDKs: `steam_api64.dll` (17) and `EOSSDK-Win64-Shipping.dll` (70).
- System imports by purpose: file system 39, network 52 (WS2_32, WINHTTP, IPHLPAPI), registry and system info 32, processes/threads/modules 32, windowing and input 33, debugging and crash handling 21 (dbghelp mini dumps).
- Use: a hook on Lua VM or database calls can be placed in the game DLLs instead of the exe; the exe-side Lua API names (`hks*`, `lua*`) resolve to `HavokScript_FinalRelease.dll`.
