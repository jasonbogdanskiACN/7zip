# Phase 2: Entity Model

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Overview

7-Zip does not use a database. All domain entities are in-memory C++ structs, populated by scanning the filesystem or by reading archive metadata. There are no persistent entity stores between sessions — each operation rebuilds its entities from its inputs.

---

## Domain Entities

### CDirItem — Disk File to be Compressed
Represents a single file, directory, or NTFS alternate data stream found during directory scanning.

**Key fields** (source: `CPP/7zip/UI/Common/DirItem.h`):

| Field | Type | Description |
|---|---|---|
| `Name` | `UString` | Item path relative to the enumeration root |
| `Size` | `UInt64` | File size in bytes (0 for directories) |
| `MTime` | `CFiTime` | Last-modified time |
| `CTime` | `CFiTime` | Creation time |
| `ATime` | `CFiTime` | Last-access time |
| `Attrib` | `UInt32` | File system attributes (read-only, hidden, system, etc.) |
| (platform flag) | bool-encoded in Attrib | Whether the item is a directory, an alternate stream, a symlink, a reparse point |
| `SecureIndex` | `int` | Index into the NT security descriptor list (Windows only) |

**How populated**: `EnumerateItems()` in `CPP/7zip/UI/Common/EnumDirItems.*` walks the censor-filtered directory tree, collecting `CDirItem` records into a `CDirItems` container.

---

### CArcItem — Archive Item (existing item in an archive)
Represents a single record from an already-open archive, used when updating an existing archive.

**Key fields** (source: `CPP/7zip/UI/Common/UpdatePair.h`, `Update.cpp`):

| Field | Type | Description |
|---|---|---|
| `Name` | `UString` | Stored path within the archive |
| `IsDir` | `bool` | True if this record represents a folder |
| `IsAltStream` | `bool` | True if this is an NTFS alternate data stream record |
| `MTime` | `CArcTime` | Stored modification time with precision tag |
| `Size` | `UInt64` | Stored uncompressed size |
| `Size_Defined` | `bool` | Whether the size field is valid |
| `IndexInServer` | `UInt32` | 0-based index in the `IInArchive` item list |
| `Censored` | `bool` | Whether this item matched the wildcard censor filter |

**How populated**: `EnumerateInArchiveItems()` in `Update.cpp` calls `IInArchive::GetNumberOfItems()` then iterates with `arc.GetItem(i, ...)` and `arc.GetItem_MTime()` / `arc.GetItem_Size()`.

---

### CUpdatePair — Pairing Decision
Classifies each file for a compress/update operation by comparing the disk state to the archive state.

**Key fields** (source: `CPP/7zip/UI/Common/UpdatePair.h`):

| Field | Type | Description |
|---|---|---|
| `State` | `NPairState::EEnum` | Relationship between disk and archive (see below) |
| `ArcIndex` | `int` | Index into `CArcItem` list (-1 if not in archive) |
| `DirIndex` | `int` | Index into `CDirItem` list (-1 if not on disk) |
| `HostIndex` | `int` | For alt streams: index of the host file pair |

**State values** (source: `UpdateAction.h`):

| State | Meaning |
|---|---|
| `kNotMasked` | Item did not match the censor filter — will be ignored |
| `kOnlyInArchive` | Item is in the archive but not on disk |
| `kOnlyOnDisk` | Item is on disk but not in the archive |
| `kNewInArchive` | Disk version is newer than the archive version |
| `kOldInArchive` | Disk version is older than the archive version |
| `kSameFiles` | Disk and archive timestamps match |
| `kUnknowNewerFiles` | Cannot determine which is newer |

The `CActionSet` table, indexed by `State`, maps each state to one of: `kIgnore`, `kCopy`, `kCompress`, `kCompressAsAnti`. The named action sets (`k_ActionSet_Add`, `k_ActionSet_Update`, `k_ActionSet_Fresh`, `k_ActionSet_Sync`, `k_ActionSet_Delete`) represent the seven standard command modes.

---

### CExtractOptions — Extract Operation Parameters

A plain data struct that carries all user-specified options from the UI layer into the `Extract()` function. Key fields:

| Field | Type | Description |
|---|---|---|
| `OutputDir` | `FString` | Destination root directory for extracted files |
| `PathMode` | `NPathMode::EEnum` | `kFullPaths`, `kCurPaths`, `kNoPaths`, `kAbsPaths`, `kNoPathsAlt` |
| `OverwriteMode` | `NOverwriteMode::EEnum` | `kAsk`, `kOverwrite`, `kSkip`, `kRename`, `kRenameExisting` |
| `ZoneMode` | `NZoneIdMode::EEnum` | Zone identifier setting: `kNone`, `kAll`, `kOffice` |
| `TestMode` | `bool` | If true, no files are created — used for integrity testing |
| `StdInMode` | `bool` | Read archive from stdin |
| `StdOutMode` | `bool` | Write extracted data to stdout |
| `NtOptions` | `CExtractNtOptions` | NT security, symlinks, hard links, alt streams, pre-allocation |

Source: `CPP/7zip/UI/Common/Extract.h`

---

### CDecompressStat — Extract Result Statistics

Accumulates outcome counters during an extract operation and is returned to the caller on completion.

| Field | Type | Description |
|---|---|---|
| `NumArchives` | `UInt64` | Number of archives processed |
| `UnpackSize` | `UInt64` | Total uncompressed bytes written |
| `PackSize` | `UInt64` | Total compressed bytes read |
| `NumFolders` | `UInt64` | Number of directory entries extracted |
| `NumFiles` | `UInt64` | Number of file entries extracted |
| `NumAltStreams` | `UInt64` | Number of alt-stream entries extracted |

Source: `CPP/7zip/UI/Common/Extract.h`

---

### CArchivePath — Output Archive Path Descriptor

Captures the final archive path plus optional temp-file staging location.

| Field | Type | Description |
|---|---|---|
| `OriginalPath` | `UString` | User-supplied path string |
| `Prefix` | `UString` | Directory portion including trailing separator |
| `Name` | `UString` | Base file name without extension |
| `BaseExtension` | `UString` | Archive type extension (e.g., `7z`, `zip`) or `exe` for SFX |
| `VolExtension` | `UString` | Volume extension for multi-volume archives |
| `Temp` | `bool` | Whether to write to a temp file first |
| `TempPrefix` | `FString` | Directory in which to create the temp file |
| `TempPostfix` | `FString` | Collision-avoidance numeric suffix appended to temp name |

The function `GetTempPath()` assembles: `TempPrefix + Name + "." + BaseExtension + ".tmp" + TempPostfix`.
Source: `CPP/7zip/UI/Common/Update.h`, `Update.cpp`

---

### CDirItemsStat — Enumeration Statistics

Counts files, directories, and alt streams found during directory scanning.

| Field | Type | Description |
|---|---|---|
| `NumDirs` | `UInt64` | Directories found |
| `NumFiles` | `UInt64` | Regular files found |
| `NumAltStreams` | `UInt64` | Alternate data streams found |
| `FilesSize` | `UInt64` | Total size of regular files |
| `AltStreamsSize` | `UInt64` | Total size of alt streams |
| `NumErrors` | `UInt64` | Scan errors (access-denied etc.) |

Source: `CPP/7zip/UI/Common/DirItem.h`

---

## Data Access Pattern

7-Zip is entirely **file-based and in-memory**. There is no database or persistent entity store.

| Source | Access Pattern |
|---|---|
| Local filesystem | Win32 `FindFirstFile` / `FindNextFile` via `CPP/Windows/FileFind.*` |
| Archive files | Sequential or seekable byte stream via `IInArchive::Open()` + `GetNumberOfItems()` / `GetItemProperty()` |
| Registry | Used for UI preferences (file associations, plugin paths, window settings) via `CPP/Windows/Registry.*` |
| Settings | Windows Registry at `HKCU\Software\7-Zip` and `HKLM\Software\7-Zip` |

---

## Phase 2 Entity Model Checklist

- [x] Major domain entities documented with fields, types, and relationships
- [x] Data access pattern identified: file-based and in-memory (no database)
- [x] Entity life cycle described (scanning → pairing → operation → statistics)
