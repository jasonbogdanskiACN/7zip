# Phase 5 — Integration Points

**System**: 7-Zip 26.00  
**Date**: 2026-03-26  
**Status**: Complete  

---

## 5.1 Integration Inventory

7-Zip has **no network integrations**, **no database layer**, and **no external compression libraries**. All integrations are local Windows OS integrations (registry, file system, shell, optional OS services).

### Summary Table

| Integration | System | Direction | Type | Runtime-Optional |
|---|---|---|---|---|
| Windows Registry | OS | R/W | Settings store | No |
| Windows Shell Extension | OS | Inbound | COM context menu | No (core feature) |
| Windows MAPI | OS | Outbound | Email compose | Yes |
| comctl32.dll | OS | Inbound | UI common controls | No |
| shell32.dll | OS | Inbound | Shell folder browser + pidl | No |
| shlwapi.dll | OS | Inbound | Path string utilities | No |
| advapi32.dll | OS | Inbound | Registry API + CryptGenRandom | No |
| UxTheme.dll | OS | Inbound | Visual styles | Yes (degraded) |
| Dwmapi.dll | OS | Inbound | DWM window composition | Yes (degraded) |
| Psapi.dll | OS | Inbound | Process memory info | Yes (degraded) |
| Windows File System | OS | R/W | Archive + extracted file I/O | No |

---

## 5.2 Integration Details

### 5.2.1 Windows Registry

**Purpose**: Persist all user preferences and operating parameters across sessions.  
**Direction**: Read and write.  
**API**: `RegOpenKeyEx`, `RegCreateKeyEx`, `RegQueryValueEx`, `RegSetValueEx`, `RegDeleteValue` — wrapped by `CPP/Windows/Registry.cpp` (`NWindows::NRegistry::CKey`).  
**Hive / Key structure**:

```
HKEY_CURRENT_USER
└── Software\
    └── 7-Zip\
        │  Lang               [REG_SZ]   – path to .lng language file
        │  LargePages         [REG_DWORD] – 0/1 mem large-pages feature
        │  ShowDots           [REG_DWORD]
        │  ShowRealFileIcons  [REG_DWORD]
        │  FullRow            [REG_DWORD]
        │  ShowGrid           [REG_DWORD]
        │  SingleClick        [REG_DWORD]
        │  AlternativeSelection [REG_DWORD]
        │  ShowSystemMenu     [REG_DWORD]
        │  FlatViewArc        [REG_DWORD]
        ├── Extraction\
        │      ExtractMode    [REG_DWORD] – NPathMode::EEnum
        │      OverwriteMode  [REG_DWORD] – NOverwriteMode::EEnum
        │      SplitDest      [REG_DWORD]
        │      ElimDup        [REG_DWORD]
        │      Security       [REG_DWORD]
        │      ShowPassword   [REG_DWORD]
        │      MemLimit       [REG_DWORD] – memory limit in GB
        │      PathHistory    [multi-REG_SZ] – MRU extract paths
        ├── Compression\
        │      ArcHistory     [multi-REG_SZ] – MRU archive paths
        │      Archiver       [REG_SZ]    – last-used archive format
        │      Level          [REG_DWORD]
        │      Dictionary     [REG_DWORD]
        │      Order          [REG_DWORD]
        │      BlockSize      [REG_DWORD]
        │      NumThreads     [REG_DWORD]
        │      Method         [REG_SZ]
        │      Options        [REG_SZ]
        │      EncryptionMethod [REG_SZ]
        │      EncryptHeaders [REG_DWORD]
        │      ShowPassword   [REG_DWORD]
        │      Security       [REG_DWORD]
        │      AltStreams     [REG_DWORD]
        │      HardLinks      [REG_DWORD]
        │      SymLinks       [REG_DWORD]
        │      PreserveATime  [REG_DWORD]
        │      TimePrec       [REG_DWORD]
        │      MTime/ATime/CTime [REG_DWORD]
        │      SetArcMTime    [REG_DWORD]
        │      MemUse         [REG_SZ]    – memory-use limit string
        └── FM\
               Viewer         [REG_SZ]   – custom viewer exe path
               Editor         [REG_SZ]   – custom editor exe path
               Diff           [REG_SZ]   – diff tool exe path
               7vc            [REG_SZ]   – version-control tool path

HKEY_CURRENT_USER / HKEY_LOCAL_MACHINE
└── Software\7-Zip\
        Path     [REG_SZ]   – install dir (for plugin discovery)
        Path32   [REG_SZ]   – 32-bit install dir
        Path64   [REG_SZ]   – 64-bit install dir
```

**Sources**: `CPP/7zip/UI/Common/ZipRegistry.cpp`, `CPP/7zip/UI/FileManager/RegistryUtils.cpp`, `CPP/7zip/UI/Common/LoadCodecs.cpp`.  
**Failure mode**: If the registry key does not exist, all settings revert to compiled-in defaults. No crash; no error dialog set. Registry writes wrapped in `CS_LOCK` critical section for thread-safety.

---

### 5.2.2 Windows Shell Extension (7-zip.dll / 7-zip32.dll)

**Purpose**: Expose a 7-Zip context menu when the user right-clicks selected files in Windows Explorer.  
**Direction**: Inbound — Windows Shell invokes 7-Zip's COM object.  
**API**: Standard Windows Shell extension COM interfaces.  
**COM interfaces implemented**:
- `IShellExtInit::Initialize()` — receives `IDataObject` with selected file paths; populates `_fileNames`
- `IContextMenu::QueryContextMenu()` — inserts 7-Zip submenu entries (Open / Extract Here / Extract To / Test / Add to archive…)
- `IContextMenu::InvokeCommand()` — dispatches chosen command (calls into same `UpdateGUI()` / `Extract()` free functions used by 7zFM and 7zG)
- `IContextMenu2/3` — owner-draw icon and menu nesting extensions

**COM CLSID**: `CLSID_CZipContextMenu` (defined in `CPP/7zip/UI/Explorer/ContextMenu.h`).  
**Registration**: `DllRegisterServer()` in `DllExportsExplorer.cpp` writes `CLSID_CZipContextMenu` to `HKLM\Software\Classes\CLSID\{...}` and adds the handler to `HKLM\Software\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved`.  
**Source**: `CPP/7zip/UI/Explorer/ContextMenu.cpp`, `DllExportsExplorer.cpp`, `RegistryContextMenu.cpp`.  
**Failure mode**: If the shell extension DLL is not registered, context menus are absent but 7zFM.exe and 7z.exe work normally. If `Initialize()` receives a null `IDataObject`, it returns `E_INVALIDARG` and the command is not queued.

---

### 5.2.3 Windows MAPI — Email Attachment (optional)

**Purpose**: After compression, optionally open the system email client with the newly created archives attached (the "Send by email" workflow).  
**Direction**: Outbound — 7-Zip initiates a compose message via the default MAPI client (Outlook, Thunderbird with MAPI shim, etc.).  
**API**: `MAPISendMailW` (Unicode, preferred) / `MAPISendMail` (ANSI fallback).  
**Loading**: `Mapi32.dll` is loaded dynamically with `NDLL::CLibrary::Load()` only when `CUpdateOptions::EMailMode == true`. Not loaded during normal compress/extract.  
**Call signature**:
```cpp
MAPISendMailW((LHANDLE)0, 0, &mapiMessage, MAPI_DIALOG, 0);
// MAPI_DIALOG flag = shows compose UI; user can edit/cancel before send
```
**Address**: If `EMailAddress` is non-empty, a `MAPI_TO` recipient is pre-filled; otherwise the compose window opens with no recipient.  
**Current-directory preservation**: 7-Zip wraps the MAPI call with `CCurrentDirRestorer` because `MAPISendDocuments` is documented to change the working directory.  
**Source**: `CPP/7zip/UI/Common/Update.cpp` lines 1700–1800 (inside `#if defined(_WIN32) && !defined(UNDER_CE)`).  
**Failure mode**:
- If `Mapi32.dll` fails to load: returns `HRESULT` error; archive was already written; email not sent.
- If `MAPISendMailW` and `MAPISendMail` are both absent: error "7-Zip cannot find MAPISendMail function"; same outcome.
- If user cancels the compose dialog: no error; compress result is still successful.
- Not available on Windows CE.

---

### 5.2.4 Windows System DLLs

7-Zip uses several Windows system DLLs. Some are statically linked (implied by the import table via `#include <windows.h>` and the MSVC linker defaults); others are loaded at runtime to allow graceful degradation on older Windows versions.

#### comctl32.dll (Common Controls)
- **Purpose**: ListView (`SysListView32`), TreeView, ToolBar, Status Bar, Image Lists — all UI panels use these controls.
- **Version probed at startup**: `GetDllVersion("comctl32.dll")` — stored in `g_ComCtl32Version`; controls behaviour of `LVN_ITEMACTIVATE` (requires ≥ 4.71).
- **Source**: `GUI.cpp:425`, `SfxWin.cpp:104`, `FM.cpp`.

#### shell32.dll
- **Purpose**: Folder picker dialog (`SHBrowseForFolder`/`SHBrowseForFolderW`), PIDL → path conversion (`SHGetPathFromIDList`), special folder paths (`SHGetSpecialFolderPath`).
- **Loaded via**: `GetModuleHandle(L"shell32.dll")` then `GetProcAddress` — runtime resolved to handle Shell32 version differences.
- **Source**: `CPP/Windows/Shell.cpp`, `CPP/7zip/UI/FileManager/RootFolder.cpp`.

#### shlwapi.dll (Shell Light-weight API)
- **Purpose**: Path string manipulation. Included in `SfxWin.cpp` and `GUI.cpp`.
- **Statically linked** (via `#include <shlwapi.h>`).

#### advapi32.dll (Advanced Services)
- **Purpose 1 – Registry**: All `RegCreateKeyEx` / `RegOpenKeyEx` / `RegSetValueEx` / `RegQueryValueEx` calls route through this DLL.
- **Purpose 2 – Cryptographic RNG**: `RtlGenRandom` (exported as `SystemFunction036`) used in `CPP/7zip/Crypto/RandGen.cpp` for seeding the AES key-generation RNG. `advapi32.dll` handle obtained via `LoadLibrary("advapi32.dll")` and `GetProcAddress`.
- **Purpose 3 – Privilege**: `AdjustTokenPrivileges` for `SeBackupPrivilege` / `SeRestorePrivilege` to access files without permission (optional, silent failure).
- **Source**: `CPP/Windows/Registry.cpp`, `CPP/7zip/Crypto/RandGen.cpp`, `CPP/Windows/SecurityUtils.cpp`, `CPP/Windows/MemoryLock.cpp`.

#### UxTheme.dll (Visual Styles)
- **Purpose**: Enable themed common controls when Windows visual styles are active.
- **Loaded at FM startup**: `LoadLibrary("UxTheme.dll")` — `FM.cpp:334`. If absent, the application runs without themed visuals.
- **Runtime-optional**: Yes (graceful degradation).

#### Dwmapi.dll (Desktop Window Manager)
- **Purpose**: DWM window composition features (glass/transparency effects on Vista+).
- **Loaded at FM startup**: `LoadLibrary("Dwmapi.dll")` — `FM.cpp:374`. If absent, DWM features silently disabled.
- **Runtime-optional**: Yes.

#### Psapi.dll (Process Status API)
- **Purpose**: `GetProcessMemoryInfo` for memory usage reporting in the console benchmark output and in `PanelItemOpen.cpp` for process introspection.
- **Loaded on demand**: `LoadLibraryW(L"Psapi.dll")` — only when memory info is requested.
- **Runtime-optional**: Yes; if absent, memory stats are not shown.

---

### 5.2.5 Windows File System

**Purpose**: Primary data store — reading source archives and writing extracted or compressed output files.  
**Direction**: Read and write.  
**API**: Win32 file API (`CreateFileW`, `ReadFile`, `WriteFile`, `SetFilePointer`, `CloseHandle`, `SetFileTime`, `SetFileAttributes`, `MoveFileExW`, `GetTempFileName`).  
**Wrapper classes**: `NWindows::NFile::NIO::CInFile` / `COutFile` in `CPP/Windows/FileIO.h`.  
**Temp-file pattern**: Output archives are written to a temp file (`GetTempFileName`) and then moved to the final path with `MyMoveFile_with_Progress()` — see Phase 2.5 state change documentation.  
**Failure mode**: Win32 errors propagated as `HRESULT`; reported to the user via the progress dialog error text. Short-reads treated as end-of-stream; file creation errors abort the operation.

---

## 5.3 Confirmed Absent Integrations

The following integration categories were searched and found **absent**:

| Category | Search Pattern | Result |
|---|---|---|
| Network sockets | `socket` in CPP/**/*.cpp | No matches |
| HTTP clients | `http`, `curl`, `WinHttp`, `WinInet` | No matches |
| Database (SQL) | `sqlite`, `odbc`, `sql` | No matches |
| External compression libs | `openssl`, `zlib`, `bzip2.h`, `zstd.h` | No matches |
| MPI / HPC frameworks | `MPI_Init`, `LAPACK`, `BLAS` | No matches |
| Cloud storage SDKs | `AWS`, `Azure`, `GoogleCloud` | No matches |

**Conclusion**: 7-Zip is a fully local, self-contained application. All compression, cryptographic, and hashing algorithms are implemented in source (`C/` and `CPP/7zip/Compress/`, `CPP/7zip/Crypto/`). The only external systems are the Windows OS itself and (optionally) a MAPI email client.

---

## References

| File | Relevance |
|---|---|
| `CPP/7zip/UI/Common/ZipRegistry.cpp` | All compression/extraction preference keys |
| `CPP/7zip/UI/FileManager/RegistryUtils.cpp` | File manager UI preference keys |
| `CPP/7zip/UI/Common/LoadCodecs.cpp` | Plugin discovery via Registry Path key |
| `CPP/7zip/UI/Explorer/ContextMenu.cpp` | Shell extension COM object |
| `CPP/7zip/UI/Explorer/DllExportsExplorer.cpp` | DLL registration / COM class factory |
| `CPP/7zip/UI/Common/Update.cpp` (lines 1700–1800) | MAPI email send integration |
| `CPP/Windows/Registry.cpp` | Registry abstraction wrapper |
| `CPP/Windows/Shell.cpp` | shell32.dll wrapper functions |
| `CPP/7zip/Crypto/RandGen.cpp` | advapi32 CryptGenRandom usage |
| `CPP/Windows/SecurityUtils.cpp` | advapi32 AdjustTokenPrivileges |
| `CPP/7zip/UI/FileManager/FM.cpp` (lines 334, 374) | UxTheme + Dwmapi dynamic load |
