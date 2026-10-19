# Command-line switches of the engine exe

Source: string literals with a leading dash that are referenced by exe functions (`strmaps.pkl`), plus disassembly of the Linux
`AppHost::OptionSet::SetFromCommandLine` (the Windows copy is unmapped in the function index). Windows RVAs are for `CivilizationVI.exe`
(DX11 Jul 2024). **Verified** = literal string and the function that uses it; behaviour descriptions are Inferred from the function name unless stated.

## Fixed switches
| Switch | Function (Windows RVA) | Effect (Inferred) |
|---|---|---|
| `-NoAsserts`, `-NoAssertPopups`, `-NoAssertCallstack`, `-NoAssertLogging`, `-NoAssertCollection`, `-NoAssertAnything` | `Civ6App::SetupErrorHandling` (0x721f0) | switch off assertion popups, call stacks, logging, bug collection |
| `-FullDump` | `Civ6App::SetupErrorHandling` | write full crash dumps |
| `-autoscript`, `-autoparams`, `-autojson` | `App::Automation::Manager::Startup` (0x29c060) | automation harness: script file, parameters, json output (Lua `Automation` interface, see `exe-lua-tables.md`) |
| `-benchmark` | `BenchmarkSystem::ParseArguments` (0x560b0) | run the benchmark mode |
| `-gameviewscript` | `GameViewState::SetFromCommandLine` (0x7ec80) | run a script in the game view |
| `-PlatformContent` | `App::ContentPath::Local::SetupCommandLineOverrides` (0x2ea70) | content path override |
| `-appFolder="` | `AppHost::StartBugHelper` (0x709c90) | passes the app folder to the bug-report helper process |
| `--rail_connect_to_railid=`, `--rail_connect_cmd=` | `Network::Manager::SetupFromCommandLine` (0x290db0) | Rail (Chinese platform) join-by-invite arguments, not used on Steam |

## Generic option override (Verified on Linux disassembly)
`AppHost::OptionSet::SetFromCommandLine(argc, argv)` (Linux 0x42b6820): for every argument that starts with `-` it hashes the text after the dash
(`OptionSet::StringHash`, a `memhash` of the string) and looks that hash up in the option table. If the option exists and is an **integer** option, the next
argument is read as a number (`atoi`) and stored as the option's override value; string and floating options are not given a value (the switch is skipped).
- **The option id is the hash of the key name only, without the section.** `RegisterHelper` hashes just the key, and all 194 registered keys in
  `../tables/exe_app_options_windows.tsv` are unique, so there are no clashes. Any registered integer option can therefore be set as
  `-EnableTerrainLogging 1` or `-AvailableViews 1` (key name exactly as in the table, case matters because it is hashed).
- Not tested in game; the Windows build has the same option registrations and is expected to behave the same. The override is a per-launch value,
  not written to `AppOptions.txt` by this function (the file is written by `OptionSet::SaveOptions`, Windows 0x702240).
- Useful for modders: debug options such as `EnableGameCoreEventLog`, `EnableTuner`, `EnableDebugMenu` (see `exe-app-options.md`) can be
  enabled from a shortcut or Steam launch options without editing `AppOptions.txt`.
