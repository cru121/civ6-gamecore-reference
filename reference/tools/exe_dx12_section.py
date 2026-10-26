"""Page exe/dx12.md: CivilizationVI_DX12.exe compared with the DX11 exe. Called from build.py: exe_dx12_section.make(add)
Source: findings/topics/exe-dx12-build.md (text written by hand from the analysis), findings/tables/exe_dx12_key_addresses.tsv (table)."""
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ROOT = os.path.abspath(os.path.join(BASE, '..'))


def make(add):
    rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'findings', 'tables', 'exe_dx12_key_addresses.tsv'), encoding='utf8') if l.strip()]
    L = ['# The DirectX 12 executable\n',
         'The game folder holds two engine executables, `CivilizationVI.exe` (DirectX 11) and `CivilizationVI_DX12.exe` (DirectX 12), both in `Base/Binaries/Win64Steam`. Everything else in the [engine executable section](index.md) was read from the DX11 exe. '
         'This page says how far it also applies to the DX12 exe. **Verified** = read from the two files (headers, import tables, function bytes, strings, decompiled code). **Inferred** = a reading of those facts that was not tested in the running game.\n',
         '## Summary\n',
         '- The two exes are the same build with a different renderer: same build date (28 Jul 2024), same image base `0x140000000`, same section layout; `.text` is 0.4% larger in the DX12 exe (0xf94e2c vs 0xfa3fcc bytes). The import table swaps `d3d11.dll` for `d3d12.dll` and has 4 more imports (890 vs 894).',
         '- 98.4% of the 54,524 functions of the DX11 exe have a counterpart in the DX12 exe (53,663 of 54,817 functions there), found by comparing function bytes with address-dependent operands masked, then following call sites. 861 DX11 functions and 1,154 DX12 functions have no counterpart.',
         '- **Everything that comes from strings and data tables applies to both exes**: the Lua enum tables, multiplayer vocabulary, ArtDefs, XML formats, lenses, input actions, developer tools, SQL statements, telemetry rules and audio names. The string literals of the two exes differ only in renderer and driver text (692 only in DX11, 780 only in DX12, all graphics related), plus four console command words.',
         '- The address-based parts (the [function index](../exefn/index.md), RVAs on the other pages) are for the DX11 exe. For the DX12 exe translate an address through the function match (below).\n',
         '## What differs\n',
         '**The renderer** is a different implementation behind the same interface. The DX12-only functions are mostly in one region (RVA `0x93f000` to `0x971000`): device and adapter enumeration (a "Tier 2 Resource Binding" requirement check), `Renderer::Present`, PSO creation and compilation, root signature serialisation, descriptor heaps ("Generic Descriptor Heap", "Per Frame Descriptor Heap"), command list and queue startup (compute and copy queues), a residency manager, a transient resource pool, GPU memory budget messages, mip generation, readback, swap chain handling and a breadcrumb buffer for GPU crash markers. The corresponding DX11 code (constant-buffer rebase, static buffer allocation, surface sets, Intel driver version checks) has no counterpart. '
         'Of the 1,154 DX12-only functions 377 are tiny thunks, about 310 are renderer code by their strings or neighbours, and 185 sit next to functions of other known groups (mostly ForgeUI, Platform and library code). Source paths in the strings are under `CivTech\\Libs\\Graphics` and `CivTech\\Libs\\Platform`; the log file is `Renderer.log` in both builds.\n',
         '**Console.** The DX12 console help has four more command words: `rendermode`, `objectvrs`, `imagevrs` and `multires`. **Inferred**: the names suggest variable rate shading; the commands were not run. The strings `Compute Shading Rate Fill` and `Using RS1.1` appear only in the DX12 exe.\n',
         '**Larger structures, same logic.** Some game-side functions that are otherwise unchanged read members at shifted offsets in the DX12 build: the application object (members after `+0x5400` move by `+0x20`), `RenderGlobals::GraphicsOptions` (fields from `+0x48` move by `+0x18`; `ReflectionsEnabled` reads `+0x78` instead of `+0x60`) and `Graphics::StartupParams` (one more byte and a 4-byte field). **Inferred**: these are new renderer options; the reason was not examined. '
         'The water and terrain command builders (`WaterSystem::Context::BuildCommandStreams`, `BuildOverlayCommandStream`, `BuildReflectionMaskCommandStream`, `TerrainView::SubmitReflectionMask`) read two flag bytes of a view descriptor and set bit `0x200` in the command word; the rest of these functions is unchanged.\n',
         '**Not different.** The 63 functions of the DX11 function map that found no counterpart are mostly not real differences: 21 are mapped addresses that are not function starts, three differ only in a vtable pointer or address, and the rest are the rewritten renderer core (`Renderer::Startup`, `Render`, `SetScreenMode`, the shader create and reload functions) or functions the linker probably merged. The 6,443 other mapped functions (99%) carry across.\n',
         '## Vertex and index buffers\n',
         'Both exes create a buffer through the same two wrappers (`CreateVB`, `CreateIB`): allocate a 16-bit handle from a pool object (handles below 0x2000), then call a creation function with the same seven parameters (usage, format, element count, data and flags). What the handle means differs.\n',
         '- **DX11** (**Verified**, decompiled): the creation function fills a 0x30-byte record, calls `ID3D11Device::CreateBuffer` and stores the `ID3D11Buffer*` in a table indexed by the handle. Usage 0 is static and needs initial data, usage 2 is dynamic. The stride comes from a table indexed by the format code.',
         '- **DX12** (**Verified**, decompiled): a handle indexes two records, a 0x28-byte one with the buffer\'s GPU virtual addresses (two entries, one per GPU node), the backing heap object, stride, size and format, and a 0x70-byte one with the current and previous allocation. There is no separate `ID3D12Resource` per buffer: buffers are sub-allocations of large heaps, and the stored address is the heap resource\'s GPU address plus the offset. The data goes through a sub-allocator with five pools chosen by the usage code. Allocations under 4 MB come out of 4 MB blocks, larger ones get their own resource.',
         '  - usage 0 and 1: heap type DEFAULT (GPU only), one resource per GPU node, initial state `0xac3`; the data is copied through a staging buffer;',
         '  - usage 2 (three times the requested size): heap type UPLOAD, persistently mapped, data written directly;',
         '  - the staging buffers themselves are in an UPLOAD pool; usages 3 and 4 were not followed.',
         '- Calling the creation function again with an existing handle replaces the allocation and the stored GPU addresses and releases the old one; the handle stays. **Inferred**: whether the draw code reads the stored addresses on every use was not examined. The DX11 build has no such path (a new buffer object is stored).',
         '- The terrain cell meshes (`Terrain_Cell_VB`, `Terrain_Cell_Material_VB`, `Terrain_Cell_IB`) are created with usage 0 and the format codes `0x15` and `0x24` in both exes, so in DX12 they are GPU-only buffers. The cell record is 0x3b0 (944) bytes in both exes (`(y * width + x) * 0x3b0 + *(this + 8)`), and all 102 matched functions that use its key offsets use the same offsets in both builds.\n',
         '## Finding things in the DX12 exe\n',
         'Image base and RVA convention are the same as for the DX11 exe (all addresses on this site are RVAs, address minus `0x140000000`). Known objects:\n',
         '| What | DX11 RVA | DX12 RVA | How found |', '|---|---|---|---|']
    for r in rows[1:]:
        if r[0] == '8':
            continue
        L.append('| %s |' % ' | '.join(c.replace('|', '/').replace('*', '\\*') for c in r[1:]))
    L.append('\n"exact" means the function bytes are identical in both exes apart from address-dependent operands; "call-aligned" means the match follows the call sites of an exact match (medium confidence).\n')
    L.append('The full match for every function (DX11 RVA, DX12 RVA, method) is `findings/data/exe_dx12_match.tsv` in the repository. Methods: `exact` (high confidence), `exact-dup` (identical copies such as thunks, paired by order: the code is the same but the name can land on a different copy), `prop` (call-aligned) and `fuzzy` (shared byte patterns), the last two medium confidence. Not every match was checked: a few call-aligned matches are known to be out of order.\n')
    L.append('## Limits\n')
    L.append('- Nothing here was run: the console commands, the buffer behaviour and the claim that cell meshes cannot be written from the CPU are read from code.')
    L.append('- Whether a changed terrain cell is re-built by the game in DX12 (the dirty-bit path) was not tested; the functions involved match the DX11 ones.')
    L.append('- The renderer internals beyond buffer creation (PSOs, descriptor heaps, command lists) were classified by strings and neighbours only, not read.\n')
    add('exe/dx12.md', 'The DirectX 12 executable', '\n'.join(L) + '\n')
