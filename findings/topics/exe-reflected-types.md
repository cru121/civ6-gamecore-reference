# Reflected data types

Source: `tools/exe/winreflect.py` over the 296 `*::GetTypeInfo` functions and 15 `GetEnumInfo` functions of the Windows exe (the reflection system that describes serialized structures). Tables: `findings/tables/exe_reflected_types_windows.tsv` (264 types with fields, 1,104 fields), `exe_reflected_enums_windows.tsv` (14 enums, 123 members). Reference: `docs_proto/docs/exetypes/`.

- A type function builds, per field, `call TypeDescription<T>::GetTypeInfo` (the field type), `lea rdx,["name"]` + string constructor, then a dword offset (stored in a stack temp and reloaded as a qword). The first string is the type name; the size is a constant stored after it. Enum members are 0x18-byte records (value at +0, string at +8).
- Field type labels: the Linux function map names the primitive and template type functions (`TypeDescription<float>`, `uint32` ...); the rest are labelled with the first string of the target function; 51 of 1,104 stay unresolved. The first enum member's zero is filled in when the next value is 1.
- Namespaces: AssetObjects (111 types, the artdef object model: `ArtDefSet`, `ArtDefCollection`, `ArtDefElement`, values), BLP (blueprint packages, 775 shipped `.blp` files), LeaderHeadPackageEntry / LeaderPackageEntryV2 (hair 'wig passes'), FOWMeshVisSystem, FGXModelFramework, ModelMaterialData_VFX, DecalDesc/DecalDesc2, FireFX/FireVM, TerrainEditDesc 1-3, TimelineSet, LandmarkPackageEntry.
- Cross-check: 29 of the 32 distinct `m_...` element names in the shipped `.artdef` XML are field names of reflected types (not matched: `m_r`, `m_g`, `m_b`, the colour channels).
- Limits: layouts are in-memory (x64) layouts, not on-disk byte layouts; type usage is inferred from names; 145 types have no size constant recognised.
