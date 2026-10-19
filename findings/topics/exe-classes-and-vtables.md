# C++ classes, inheritance and virtual tables of the engine exe

Method: the Linux `Civ6` carries RTTI (2,483 typeinfo objects, 2,442 vtables). `tools/exe/classes.py` reads each typeinfo (the three cxxabi kinds: class, single-inheritance, virtual-multiple-inheritance) for the base classes and each vtable for its slots (function pointers are stored in the file, the exe is non-PIE).
`docs_proto/tools/extract_exe_classes.py` drops library and platform-shim classes (ICU, OpenSSL, the shader language, Direct3D shims) and keeps 1,207 classes with 16,000+ virtual slots; Windows RVAs are attached to slots whose function the map resolved at high or medium confidence.
Reference pages: `docs_proto/docs/execlass/` (index, one page per namespace, inheritance trees). **Verified**: names, bases and slot contents of the Linux build. **Inferred**: the same hierarchy and slot order on Windows (confirmed for `GameCore::EngineUtility`: 46 slots).
- Windows has no RTTI for these classes, so this is the way to read the Windows class structure.
- ForgeUI: every control derives from `ForgeUI::ControlBase` (54 virtual slots); buttons (ButtonControl, GridButtonControl, SliderControl ...) go through `ButtonControlBase` (58 slots); TextControl, StackControl and ScrollPanelControl (57) derive directly from ControlBase.
  The control type pages in the Lua reference show this base chain; whether the Lua type also exposes inherited methods was not checked.
- Largest namespaces kept: global 368, AssetObjects 177, Firaxis 131, ForgeUI 87, WorldView 54, Synthesis 31, BLP 29, Localization 25, Modding 24, GameCore 23.
- Use: a virtual slot number plus the vtable gives the target of an indirect call (`call qword ptr [rax + 0x58]` is slot 11); the slot name tells you what the call does.
