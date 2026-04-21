# Phase 6 — Implementation Details and Known Limitations

**System**: 7-Zip 26.00  
**Date**: 2026-03-26  
**Status**: Complete  

---

## 6.1 Code Style and Build Conventions

### Language Standard (Pre-C++11)

7-Zip uses a strict pre-C++11 C++ dialect throughout:

- **No STL containers**: All collections are custom (`CObjectVector<T>`, `CRecordVector<T>`, `CObjArray<T>`, `CMyComPtr<T>`)
- **No `auto` keyword**: All types are explicit
- **No range-for loops**: Classic index-based `for` everywhere
- **No `nullptr`**: `NULL` / `0` used
- **No `override` keyword (native)**: Uses `Z7_override` macro (defined as `override` on MSVC, empty otherwise for older compilers)
- **No `= delete`**: Assignments and copy constructors prevented by `Z7_CLASS_NO_COPY` macro
- **Custom RAII macros**: `COM_TRY_BEGIN` / `COM_TRY_END`, `Z7_COMWF_B`, `RINOK` macro

### Custom HRESULT Propagation Pattern

```cpp
#define RINOK(x) { HRESULT __result_ = (x); \
  if (__result_ != S_OK) return __result_; }
```

Used pervasively. Functions return `HRESULT`; callers chain with `RINOK`. This is the primary error-propagation mechanism — no exceptions in the codec layer.

### COM-style Interface Macros

The Z7_ macro family (Z7_IFACE_COM7_IMP, Z7_COM7F_IMF, Z7_COMWF_B, etc.) wrap the interface method boilerplate. These are defined in `CPP/Common/MyCom.h` and `CPP/7zip/7zip.mak`. All interface methods return `HRESULT`.

### Naming Conventions

| Convention | Example |
|---|---|
| Class names: PascalCase prefixed `C` | `CPanel`, `CZipContextMenu` |
| Interface names: PascalCase prefixed `I` | `IInArchive`, `ICoder` |
| Member variables: prefixed `_` or `m_` | `_hashCalc`, `m_Dictionary` |
| Constants: `k` prefix or `ALL_CAPS` | `kMenuCmdID_Toolbar_Add` |
| Namespaces: NNamespace pattern | `NWindows::NFile::NIO` |
| Enums: `EEnum` typedef | `NCommandType::EEnum` |
| Error strings: `IDS_` prefix | `IDS_PASSWORD_USE_ASCII` |

---

## 6.2 Build Variants and Compile-Time Gates

| Macro | Effect |
|---|---|
| `Z7_EXTRACT_ONLY` | Disables all update/compress commands; compile-time throws `"update commands are not implemented"` if called (`Main.cpp:1540`) — produces a read-only extract-only binary |
| `Z7_EXTERNAL_CODECS` | Enables `CCodecs::Load()` DLL scanner to find and load external plugin DLLs (7z.dll, Codecs/*.dll) |
| `Z7_NO_CRYPTO` | Removes all cryptographic code (AES, password support) from the build |
| `Z7_ST` | Single-threaded build; removes multithreaded LZMA encoder paths |
| `Z7_LARGE_PAGES` | Enables `VirtualAlloc` with `MEM_LARGE_PAGES` flag for decoder dictionary |
| `Z7_LANG` | Enables runtime language file loading from `.lng` files |
| `Z7_USE_DYN_ComCtl32Version` | Enables dynamic detection of `comctl32.dll` version at startup |
| `Z7_OLD_WIN_SDK` | Compatibility mode for very old Windows SDK (substitutes missing `PROCESS_MEMORY_COUNTERS` typedef) |
| `UNDER_CE` | Windows CE / Windows Mobile target — removes several Win32 API calls not available on CE |

---

## 6.3 Known FIXME and Stub Patterns

The following `FIXME` / `TODO` / `not implemented` markers were found in the source. None blocks core archive operations; all are minor limitations in specific handlers or optional features.

### FIXME: APFS Handler — Extra Fields Not Parsed

- **File**: `CPP/7zip/Archive/ApfsHandler.cpp:2223`, line 2958  
- **Comment**: `// fixme` / `// fixme: parse extra fields;`  
- **Impact**: Some APFS volume metadata fields are not fully parsed; displayed properties for APFS archives may be incomplete.  
- **Workaround**: None required for extraction; data content extraction is not affected.

### FIXME: 7z Solid Archive — External Filter Status Not Checked

- **File**: `CPP/7zip/Archive/7z/7zUpdate.cpp:1972`  
- **Comment**: `/* FIXME: we should check IsFilter status for external filters too */`  
- **Impact**: When a plugin-supplied external filter codec is used in a solid 7z archive, the filter status flag may not be set correctly in the update logic. Affects multi-codec solid archive recompression edge cases.  
- **Workaround**: Built-in filters (BCJ, BCJ2, Delta) are not affected.

### FIXME: Far Manager Panel — No Refresh After F7 Folder Creation

- **File**: `CPP/7zip/UI/Far/Far.cpp:560`  
- **Comment**: `/* FIXME: after folder creation with F7, it doesn't reload new file list`  
- **Impact**: In the Far Manager plugin, creating a new folder with F7 does not immediately refresh the panel to show the new folder. User must manually reload.  
- **Workaround**: Press F5 (refresh) in Far Manager.

### FIXME: ISO Handler — Rock Ridge Extension Not Fully Supported

- **File**: `CPP/7zip/Archive/Iso/IsoIn.cpp:598`  
- **Comment**: `/* FIXME: some volume can contain Rock Ridge, that is better than`  
- **Impact**: ISO 9660 archives containing Rock Ridge extensions (common on Linux/Unix ISOs for long filenames and Unix permissions) may not display or extract Rock Ridge metadata. Basic extraction still works.  
- **Workaround**: Extract file contents normally; symlink/permission metadata may be lost.

### FIXME: ZIP Update — XZ Thread Count Not Validated

- **File**: `CPP/7zip/Archive/Zip/ZipUpdate.cpp:1096`  
- **Comment**: `// fixme: we should check the number of threads for xz method also`  
- **Impact**: When compressing a ZIP archive using the XZ method, the number of threads is not bounded the same way as for other methods. May lead to over-allocation in extreme thread-count configurations.

### FIXME: ZIP Item — UTF-8 Name Priority

- **File**: `CPP/7zip/Archive/Zip/ZipItem.cpp:276`  
- **Comment**: `// FIXME: we can check InfoZip UTF-8 name at first.`  
- **Impact**: When a ZIP item has both a legacy (non-UTF-8) name and an InfoZip UTF-8 extra field, the UTF-8 version may not always be preferred first.

### FIXME: Windows FileDir — Symbolic Link Handling

- **File**: `CPP/Windows/FileFind.cpp:1275`, line 1284  
- **Comment**: `// FIXME for symbolic links.`  
- **Impact**: Symbolic link traversal and attribute reporting on Windows have known edge cases that are not fully handled. Affects archives containing symlinks.

### Not Implemented: Update Commands in Z7_EXTRACT_ONLY Builds

- **File**: `CPP/7zip/UI/Console/Main.cpp:1540`  
- **Code**: `throw "update commands are not implemented";`  
- **Guarded by**: `#ifdef Z7_EXTRACT_ONLY`  
- **Impact**: Intentional — the extract-only build (`SFXCon`, `SFXWin` bundles) throws a hard error if archive creation is attempted. This is correct behaviour for shipment as a self-extracting archive runtime.

### Incomplete: VT_BSTR PropVariant Comparison

- **File**: `CPP/Windows/PropVariant.cpp:388`  
- **Comment**: `case VT_BSTR: return 0; // Not implemented`  
- **Impact**: When comparing `PROPVARIANT` values of type `VT_BSTR` (BSTR strings), the comparison always returns 0 (equal). Only affects sorting by BSTR-typed archive properties, which is not exposed in normal use.

---

## 6.4 Language File Architecture (Strings Not in Source)

7-Zip externalises virtually all user-visible strings to `.lng` language files (located in the install directory, not in the source tree). In the source:

- String resource IDs use `IDS_*` macros defined in `*Res.h` header files
- At runtime, `LangString(IDS_*, result)` loads the localised string from the loaded `.lng` file
- If no language file is loaded, the compiled-in English RC string is used
- **Effect on this documentation**: Exact error message text for validation rules (e.g., `IDS_PASSWORD_USE_ASCII`, `IDS_PASSWORD_TOO_LONG`) is **not available** from source — only the resource ID and call site are documented

---

## 6.5 Thread Safety Model

| Component | Thread Safety |
|---|---|
| Registry access (`ZipRegistry.cpp`) | Protected by `g_CS` (`NSynchronization::CCriticalSection`); all reads and writes are inside `CS_LOCK` |
| Codec registry (`RegisterArc`) | Static initialisation at startup before any threads; read-only after init |
| Archive open/extract/compress | Single operation at a time per `CCodecs` instance; no global lock |
| LZMA encoder | Multi-threaded internally (match finder runs in separate thread when `numThreads == 2`); external callers are single-threaded |
| Benchmark | Runs compression/decompression in a dedicated `CThreadBenchmark` thread; communicates with GUI via `CBenchProgressSync` / `CCriticalSection` |

---

## References

| File | Relevance |
|---|---|
| `CPP/7zip/UI/Console/Main.cpp:1540` | `Z7_EXTRACT_ONLY` stub |
| `CPP/7zip/Archive/ApfsHandler.cpp:2223` | APFS FIXME |
| `CPP/7zip/Archive/7z/7zUpdate.cpp:1972` | 7z solid filter FIXME |
| `CPP/7zip/Archive/Iso/IsoIn.cpp:598` | ISO Rock Ridge FIXME |
| `CPP/7zip/Archive/Zip/ZipUpdate.cpp:1096` | ZIP XZ thread FIXME |
| `CPP/Windows/FileFind.cpp:1275` | Symlink FIXME |
| `CPP/Windows/PropVariant.cpp:388` | VT_BSTR not implemented |
| `CPP/Common/MyCom.h` | COM macro definitions |
| `CPP/7zip/UI/GUI/BenchmarkDialog.cpp` | Benchmark thread + dialog |
