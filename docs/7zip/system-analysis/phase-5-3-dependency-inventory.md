# Phase 5.3 — Dependency Inventory (Critical Gate Item for Phase 7)

**System**: 7-Zip 26.00  
**Date**: 2026-03-26  
**Status**: Complete — Phase 7 gate item satisfied  

---

## Purpose

This document provides the complete inventory of external dependencies required before proceeding to Phase 7 (Vertical Slice Documentation). It enumerates every system or service 7-Zip integrates with, the direction of the contract, and the failure behaviour when the dependency is unavailable.

---

## Dependency Inventory

### DEP-01: Windows Registry

| Field | Value |
|---|---|
| **Name** | Windows Registry |
| **Type** | OS key-value store |
| **Direction** | Read + Write |
| **API / Protocol** | Win32 Registry API (`RegCreateKeyEx`, `RegOpenKeyEx`, `RegSetValueEx`, `RegQueryValueEx`) |
| **Root path** | `HKCU\Software\7-Zip\` (user prefs) · `HKCU/HKLM\Software\7-Zip\Path*` (plugin discovery) |
| **Data written** | Compression and extraction dialog settings, file manager UI state, MRU path lists, language file path, editor / viewer / diff tool paths |
| **Criticality** | Non-critical — all keys have compiled-in defaults |
| **Failure mode** | If keys are absent, defaults apply. Registry write failures are silently ignored. No crash. |
| **Source** | `CPP/7zip/UI/Common/ZipRegistry.cpp`, `CPP/7zip/UI/FileManager/RegistryUtils.cpp` |

---

### DEP-02: Windows Shell Extension COM (7-zip.dll)

| Field | Value |
|---|---|
| **Name** | Windows Explorer Shell Extension |
| **Type** | In-process COM server |
| **Direction** | Inbound (Windows Shell calls into 7-Zip) |
| **API / Protocol** | `IShellExtInit`, `IContextMenu`, `IContextMenu2`, `IContextMenu3` |
| **CLSID** | `CLSID_CZipContextMenu` |
| **Registration** | `DllRegisterServer()` → `HKLM\Software\Classes\CLSID\{...}` + `Shell Extensions\Approved` |
| **Criticality** | Non-critical — context menu integration only; 7zFM and 7z.exe unaffected if unregistered |
| **Failure mode** | If DLL is not registered: right-click menu entries absent; no error to user. If `Initialize()` receives null `IDataObject`: returns `E_INVALIDARG` immediately. |
| **Source** | `CPP/7zip/UI/Explorer/ContextMenu.cpp`, `DllExportsExplorer.cpp` |

---

### DEP-03: Windows MAPI (Mapi32.dll)

| Field | Value |
|---|---|
| **Name** | Windows MAPI (Simple MAPI) |
| **Type** | OS optional service DLL |
| **Direction** | Outbound (7-Zip invokes default email client) |
| **API / Protocol** | `MAPISendMailW` (Unicode) / `MAPISendMail` (ANSI fallback); `MAPI_DIALOG` flag — compose UI shown |
| **Loaded** | Dynamically via `LoadLibrary("Mapi32.dll")` only when `CUpdateOptions::EMailMode == true` |
| **Criticality** | Non-critical — only invoked by explicit "Send by email" option |
| **Failure mode** | `Mapi32.dll` not found → HRESULT error returned; archive already written to disk. Both proc-addresses absent → error "7-Zip cannot find MAPISendMail function". User cancel → S_OK; no error. Not available on Windows CE. |
| **Source** | `CPP/7zip/UI/Common/Update.cpp` lines 1700–1800 |

---

### DEP-04: comctl32.dll (Common Controls Library)

| Field | Value |
|---|---|
| **Name** | Windows Common Controls |
| **Type** | System DLL |
| **Direction** | Inbound (controls hosted in 7-zip windows) |
| **API / Protocol** | Win32 Common Controls API (ListView, TreeView, ToolBar, StatusBar, ImageList) |
| **Version check** | `GetDllVersion("comctl32.dll")` at startup; stored in `g_ComCtl32Version`. Version ≥ 4.71 required for `LVN_ITEMACTIVATE`. |
| **Criticality** | Required — UI panels depend on common controls |
| **Failure mode** | If version < 4.71: `LVN_ITEMACTIVATE` events not dispatched (double-click activation degrades). If DLL missing: application fails to start. |
| **Source** | `CPP/7zip/UI/GUI/GUI.cpp:425`, `CPP/7zip/UI/FileManager/FM.cpp` |

---

### DEP-05: shell32.dll (Windows Shell Library)

| Field | Value |
|---|---|
| **Name** | Windows Shell |
| **Type** | System DLL |
| **Direction** | Inbound (folder picker UI) |
| **API / Protocol** | `SHBrowseForFolder` / `SHBrowseForFolderW`, `SHGetPathFromIDList`, `SHGetSpecialFolderPath` / `SHGetSpecialFolderPathW` |
| **Loaded** | `GetModuleHandle(L"shell32.dll")` then `GetProcAddress` (runtime resolution to handle version differences) |
| **Criticality** | Required — folder browse dialogs and panel root folder enumeration |
| **Failure mode** | If `SHBrowseForFolderW` unavailable: falls back to ANSI `SHBrowseForFolderA`. If `SHGetSpecialFolderPath` unavailable: special folder paths (Desktop, Documents) not shown in panel root. |
| **Source** | `CPP/Windows/Shell.cpp`, `CPP/7zip/UI/FileManager/RootFolder.cpp` |

---

### DEP-06: advapi32.dll (Advanced Windows Services)

| Field | Value |
|---|---|
| **Name** | Windows Advanced Services |
| **Type** | System DLL |
| **Direction** | Inbound (services provided to 7-Zip) |
| **API / Protocol** | Registry API (see DEP-01 for key list); `RtlGenRandom` / `SystemFunction036` for CSPRNG; `AdjustTokenPrivileges` for backup/restore privileges |
| **Loaded** | Registry: statically linked. `RtlGenRandom`: `LoadLibrary("advapi32.dll")` then `GetProcAddress("SystemFunction036")`. |
| **Criticality** | Required for registry access. CSPRNG: required for AES encryption. Privilege adjustment: optional. |
| **Failure mode** | `SystemFunction036` absent → `RandGen.cpp` falls back to `GetSystemTimeAsFileTime`-seeded PRNG (weaker, but does not crash). Privilege adjustment failure: silently ignored; backup mode operation not available. |
| **Source** | `CPP/Windows/Registry.cpp`, `CPP/7zip/Crypto/RandGen.cpp`, `CPP/Windows/SecurityUtils.cpp` |

---

### DEP-07: shlwapi.dll (Shell Light-weight API)

| Field | Value |
|---|---|
| **Name** | Windows Shell Light-weight API |
| **Type** | System DLL |
| **Direction** | Inbound |
| **API / Protocol** | Path string functions (`PathFindFileName`, `PathRemoveFileSpec`, etc.) |
| **Loaded** | Statically linked via `#include <shlwapi.h>` in `SfxWin.cpp` and `GUI.cpp` |
| **Criticality** | Required for GUI and SFX binaries |
| **Failure mode** | DLL missing → application fails to start (static import) |
| **Source** | `CPP/7zip/Bundles/SFXWin/SfxWin.cpp`, `CPP/7zip/UI/GUI/GUI.cpp` |

---

### DEP-08: UxTheme.dll (Visual Styles) — Optional

| Field | Value |
|---|---|
| **Name** | Windows UxTheme (Visual Styles) |
| **Type** | System DLL |
| **Direction** | Inbound |
| **API / Protocol** | `EnableThemeDialogTexture`, `SetWindowTheme` and related theming APIs |
| **Loaded** | `LoadLibrary("UxTheme.dll")` at FM startup (`FM.cpp:334`) |
| **Criticality** | Non-critical — graceful degradation |
| **Failure mode** | If absent: application runs with unthemed (classic) common controls. No error to user. |
| **Source** | `CPP/7zip/UI/FileManager/FM.cpp:334` |

---

### DEP-09: Dwmapi.dll (Desktop Window Manager) — Optional

| Field | Value |
|---|---|
| **Name** | Windows Desktop Window Manager API |
| **Type** | System DLL |
| **Direction** | Inbound |
| **API / Protocol** | `DwmIsCompositionEnabled`, `DwmExtendFrameIntoClientArea` and related DWM APIs |
| **Loaded** | `LoadLibrary("Dwmapi.dll")` at FM startup (`FM.cpp:374`) |
| **Criticality** | Non-critical — graceful degradation |
| **Failure mode** | If absent (pre-Vista or DWM disabled): window composition effects not applied. No error. |
| **Source** | `CPP/7zip/UI/FileManager/FM.cpp:374` |

---

### DEP-10: Psapi.dll (Process Status API) — Optional

| Field | Value |
|---|---|
| **Name** | Windows Process Status API |
| **Type** | System DLL |
| **Direction** | Inbound |
| **API / Protocol** | `GetProcessMemoryInfo` |
| **Loaded** | `LoadLibraryW(L"Psapi.dll")` on demand (`CPP/7zip/UI/Console/Main.cpp:640`, `PanelItemOpen.cpp:201,232`) |
| **Criticality** | Non-critical — memory stats only |
| **Failure mode** | If absent: memory information columns / benchmark output not displayed. No error. |
| **Source** | `CPP/7zip/UI/Console/Main.cpp:640`, `CPP/7zip/UI/FileManager/PanelItemOpen.cpp:201` |

---

### DEP-11: Windows File System

| Field | Value |
|---|---|
| **Name** | Windows NTFS / FAT File System |
| **Type** | OS storage |
| **Direction** | Read + Write |
| **API / Protocol** | Win32 file API: `CreateFileW`, `ReadFile`, `WriteFile`, `SetFilePointer`, `GetTempFileName`, `MoveFileExW`, `SetFileTime`, `SetFileAttributes`, `GetFullPathNameW` |
| **Wrapper** | `NWindows::NFile::NIO::CInFile` / `COutFile` in `CPP/Windows/FileIO.h` |
| **Criticality** | Required — primary data store for all archive I/O |
| **Failure mode** | `CreateFileW` failure → HRESULT error propagated to progress dialog. Disk-full during compress → temp file preserved, final path not created. Permissions error during extract → per-file error recorded; operation continues for remaining items (configurable). |
| **Source** | `CPP/Windows/FileIO.h`, `CPP/7zip/UI/Common/Update.cpp`, `CPP/7zip/UI/Common/Extract.cpp` |

---

## Dependency Risk Summary

| ID | Name | Required | If Missing |
|---|---|---|---|
| DEP-01 | Windows Registry | No | Default settings used |
| DEP-02 | Shell Extension COM | No | Context menus absent |
| DEP-03 | MAPI Email | No | "Send by email" unavailable |
| DEP-04 | comctl32.dll | **Yes** | App fails to start |
| DEP-05 | shell32.dll | **Yes** | Folder browser / panel root degraded |
| DEP-06 | advapi32.dll | **Yes** (Registry + CSPRNG) | Registry unusable; AES key generation weakened |
| DEP-07 | shlwapi.dll | **Yes** (GUI + SFX binaries) | App fails to start |
| DEP-08 | UxTheme.dll | No | Unthemed UI |
| DEP-09 | Dwmapi.dll | No | No DWM effects |
| DEP-10 | Psapi.dll | No | No memory stats |
| DEP-11 | Windows File System | **Yes** | No archive I/O possible |

**Required dependencies**: DEP-04, DEP-05, DEP-06, DEP-07, DEP-11 (all provided by Windows OS ≥ XP).  
**Optional dependencies**: DEP-01 (no user prefs), DEP-02 (no context menus), DEP-03 (no email), DEP-08 / DEP-09 / DEP-10 (visual/stats degradation).

---

## Phase 7 Gate Confirmation

This document satisfies the **Phase 5.3 Dependency Inventory** gate item required before proceeding to Phase 7.  

- No network dependencies found ✅  
- No database dependencies found ✅  
- No third-party library dependencies found ✅  
- All external OS integrations enumerated ✅  
- Failure modes documented for all dependencies ✅  
