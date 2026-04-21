# Phase 4: Client Architecture (UI Layer)

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Interface Type

7-Zip exposes a **graphical user interface** as its primary interface. The application ships two GUI binaries from the same source tree, plus a CLI tool:

| Binary | Interface | When Used |
|---|---|---|
| `7zFM.exe` | GUI — dual-pane file manager | Primary interactive use; launched directly by the user |
| `7zG.exe` | GUI — modal operation dialogs (compress, extract, benchmark, hash) | Invoked by Windows Explorer shell extension context menu, or by `7zFM.exe` for its archive operations |
| `7z.exe` | Console CLI | Scripting, batch processing, server use |

The analysis below focuses on the GUI entry points (`7zFM.exe` and `7zG.exe`).

---

## Main Window: 7zFM.exe File Manager

**Window class**: `L"7-Zip::FM"` (registered in `FM.cpp`)
**Main entry function**: `WinMain` → `CApp::Init()` → Win32 message pump

### Main Window Layout

The file manager window contains:
1. **Main toolbar** (at the top) — three buttons: Add, Extract, Test. Defined in `App.cpp:195-197`.
2. **Up to two `CPanel` instances** — each panel is an independent Win32 child window that occupies one half of the client area, separated by a moveable splitter.
3. **Each `CPanel`** contains:
   - A header toolbar with a "Go Up" button
   - A combo-box path bar (editable address bar)
   - A ListView (`CMyListView`) displaying folder contents
   - A status bar

### Panel Navigation

Each `CPanel` can display:
- A local filesystem directory (`IFolderFolder` type: `"FSFolder"`)
- A network location (`"NetFolder"`)
- A disk drives root (`"FSDrives"`)
- The interior of an archive (`"7-Zip.*"` type prefix — served by the Agent process)
- NTFS alternate streams folder (`"AltStreamsFolder"`)
- A hash results folder

When a user double-clicks an archive file in the panel, the `CPanel` calls `BindToPath()` to navigate inside the archive, which launches the Agent COM sub-process and wraps the archive interior as a virtual folder.

---

## Workflow Trigger Points

### 1. Add to Archive (Compress)

**Toolbar button**: `kMenuCmdID_Toolbar_Add` → `g_App.AddToArchive()`
Source: `CPP/7zip/UI/FileManager/FM.cpp:884`
**Panel method**: `CPanel::AddToArchive()`
Source: `CPP/7zip/UI/FileManager/Panel.cpp:922`

**What happens**: The panel assembles the list of selected items. It constructs a `CompressDialog` (`CCompressDialog`) from `CPP/7zip/UI/GUI/CompressDialog.h`. The dialog shows the archive format, compression level, method, dictionary size, encryption, and path settings. On OK, the panel calls `UpdateGUI()` (in `CPP/7zip/UI/GUI/UpdateGUI.*`) which orchestrates the `UpdateArchive()` function.

**Input controls in `CompressDialog`**:
| Control | Field | Purpose |
|---|---|---|
| Archive path field | `Info.ArcPath` | Output archive file path |
| Format combo | `Info.FormatIndex` | Archive format (7z, Zip, GZip, BZip2, xz, Tar, wim, Hash) |
| Level combo | `Info.Level` | Compression level 0–9 (Store to Ultra) |
| Method combo | `Info.Method` | Compression algorithm (LZMA2, LZMA, PPMd, BZip2, Deflate, Copy, etc.) |
| Dictionary combo | `Info.Dict64` | Dictionary size in bytes |
| Solid block combo | `Info.SolidBlockSize` | Solid archive block size |
| Threads combo | `Info.NumThreads` | Thread count |
| Password fields | `Info.Password` | Encryption password (two-field with confirmation) |
| Encryption method combo | `Info.EncryptionMethod` | AES-256 or ZipCrypto |
| Encrypt headers checkbox | registry `EncryptHeaders` | Encrypt 7z archive headers |
| SFX checkbox | `Info.SFXMode` | Create self-extracting archive |
| Update mode combo | `Info.UpdateMode` | Add / Update / Fresh / Sync |
| Path mode combo | `Info.PathMode` | Relative / Full / Absolute paths |
| Volume size combo | `Info.VolumeSizes` | Volume split size |
| Share checkbox | `Info.OpenShareForWrite` | Open source files with share-for-write |
| Delete-after compress checkbox | `Info.DeleteAfterCompressing` | Delete source files after successful compress |

---

### 2. Extract Archives

**Toolbar button**: `kMenuCmdID_Toolbar_Extract` → `g_App.ExtractArchives()`
Source: `CPP/7zip/UI/FileManager/FM.cpp:885`
**Panel method**: `CPanel::ExtractArchives()`
Source: `CPP/7zip/UI/FileManager/Panel.cpp:1008`

**What happens**: The panel collects selected archive paths and calls the global `::ExtractArchives()` (in `CPP/7zip/UI/GUI/ExtractGUI.*`). This shows the `CExtractDialog`. On OK, it calls the `Extract()` orchestration function.

**Input controls in `ExtractDialog`**:
| Control | Field | Purpose |
|---|---|---|
| Destination path | `DirPath` | Output directory |
| Path mode combo | `PathMode` | Full / current / no paths |
| Overwrite mode combo | `OverwriteMode` | Ask / Overwrite / Skip / Rename |
| Password field | `Password` | Decryption password |
| Keep broken files checkbox | — | Extract even if CRC error |

---

### 3. Test Archives

**Toolbar button**: `kMenuCmdID_Toolbar_Test` → `g_App.TestArchives()`
Source: `CPP/7zip/UI/FileManager/FM.cpp:886`
**Panel method**: `CPanel::TestArchives()`
Source: `CPP/7zip/UI/FileManager/Panel.cpp:1103`

**What happens**: Calls `::TestArchives()` (in `CPP/7zip/UI/GUI/` — shared with extract path). No dialog is shown; operation proceeds immediately. Uses `Extract()` with `CExtractOptions.TestMode = true`. Progress shown in `CProgressDialog2`.

---

### 4. Copy / Extract from Panel (Drag-Copy between Panels)

**Trigger**: F5 / Ctrl+C, or drag-and-drop between panels
**Source**: `CPP/7zip/UI/FileManager/PanelCopy.cpp`

When copying from an archive panel to a filesystem panel, `PanelCopy.cpp` calls `IFolderArchiveFolder::Extract()` on the archive folder interface. This uses the current-paths overwrite mode and no dialog.

---

### 5. Panel Operations (Create Folder, Delete, Rename)

**Trigger**: F7 (Create folder), Delete key / Del menu, F2 / Rename menu
**Source**: `CPP/7zip/UI/FileManager/PanelOperations.cpp`

Operations are handed to `IFolderOperations` — either the filesystem implementation (for disk folders) or the archive handler's implementation (for archive interior pages). Each spawns a `CThreadFolderOperations` background thread with a progress dialog.

---

### 6. Properties Panel

**Trigger**: Alt+Enter / right-click → Properties
**Source**: `CPP/7zip/UI/FileManager/PanelMenu.cpp:172`

For filesystem items, calls the Win32 shell `"properties"` verb. For archive items, reads properties via `IFolderProperties::GetFolderPropertyInfo()` and displays them in a custom dialog.

---

## 7zG.exe GUI Dialogs (Standalone Operation Dialogs)

These dialogs are also invoked from the Windows Explorer shell extension context menu:

| Dialog | Source | Trigger |
|---|---|---|
| `CCompressDialog` | `CPP/7zip/UI/GUI/CompressDialog.*` | "Add to archive…" context menu item or Add button |
| `CExtractDialog` | `CPP/7zip/UI/GUI/ExtractDialog.*` | "Extract files…" or Extract button |
| `CBenchmarkDialog` | `CPP/7zip/UI/GUI/BenchmarkDialog.*` | Tools → Benchmark menu |
| Hash / CRC dialog | `CPP/7zip/UI/GUI/HashGUI.*` | Tools → CRC SHA menu |

`GUI.cpp` is the entry point for `7zG.exe`. It parses command-line flags to decide which dialog to show. The `-ad` flag shows the Add dialog, `-e` or `-x` shows the Extract dialog, `-b` shows the Benchmark dialog.

---

## Phase 4 Checklist

- [x] Interface type confirmed: GUI (Win32, no GUI toolkit)
- [x] Main window structure documented (dual-panel, toolbar, combo-bar)
- [x] All five primary workflow trigger points identified with source file:line
- [x] Input controls for Compress and Extract dialogs inventoried
- [x] Standalone GUI dialog entry points documented
- [x] CLI entry point noted (Console/Main.cpp — not the focus of Phase 4 for this GUI application)
