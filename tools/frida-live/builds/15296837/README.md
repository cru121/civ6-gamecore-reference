# Build 15296837

Steam build 15296837 (August 2024) changed only two intro movies. `GameCore_XP2_FinalRelease.dll` is byte-identical to the one in build 15038592
(12,940,384 bytes, SHA-256 `324C51E9EA3531758842E16C69E6CDDBEFBB226C5B675C3D6E60111646C2E98C`), so every address, hook and struct offset in this repository applies unchanged.

```
tools\frida-live\builds\15296837\run.bat
```
just calls `builds\15038592\run.bat`. See that folder's README and `examples/`.
Compare your own DLL's SHA-256 with the one above before you trust any address; the hash, not the build number, is what matters.
