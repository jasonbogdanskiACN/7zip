# Workflow: List Archive Contents

**Status**: ✅ Complete  
**Priority**: 2  
**Last Updated**: 2026-03-26  

---

## 1. Executive Summary

**Status**: ✅

**What This Workflow Does**: The List Archive Contents workflow opens one or more archives, reads item metadata from archive headers, and displays a table of file names, sizes, compressed sizes, timestamps, attributes, and CRC values. No decompression occurs. No files are created on disk. It is the fastest read operation in 7-Zip — all information comes directly from the header structures the archive handler parses into memory.

**Key Differentiator**: List is the only core workflow that does not invoke any codec. The archive handler parses its binary format, populates property values via `IInArchive::GetProperty()`, and the caller reads those values directly. There is no stream pipeline, no decode loop, and no output file management. It is also the workflow that drives the File Manager panel view — browsing an archive's interior in 7zFM is a continuous List operation.

**Reference Case**: CLI: `7z.exe l archive.7z`. FM: double-click any archive to open it; the panel shows a List of all items. Both use an identical code path after archive open.

**Comparison to Related Workflows**:

| Metric | List | Test | Extract |
|---|---|---|---|
| Opens archive | Yes | Yes | Yes |
| Decompresses data | No | Yes | Yes |
| Validates CRC | No | Yes | Yes (per item) |
| Writes files to disk | No | No | Yes |
| Output | Metadata table | Pass/fail per item | Files on disk |
| Speed | Very fast (header read only) | Full decode speed | Full decode + disk write speed |

---

## 2. Workflow Overview

**Status**: ✅

**Conceptual Dataflow**:

```mermaid
flowchart LR
    A[Archive Path(s)\nor Panel Selection] --> B[CCodecs / CArcLink\nFormat Detection & Open]
    B --> C[IInArchive::GetNumberOfItems]
    C --> D[Per-Item Property Loop\nGetProperty for each column]
    D --> E[Format & Display\nTable Row or Panel Entry]
    E --> F{More Archives?}
    F -->|Yes| B
    F -->|No| G[Print Totals\nFiles / Dirs / Size / Packed]
```

**Stage Descriptions**:

1. **Archive Path(s)**: From CLI (`7z l *.zip`) the archive paths are enumerated via the wildcard censor. From FM, the panel's current selection is used. Multiple archives can be listed in sequence.

2. **Format Detection and Open**: `CArcLink::Open_Strict()` detects the archive format from file signature bytes (or extension fallback) and creates the matching `IInArchive` handler. Identical to the open path in Extract and Test. The archive is opened in read-only mode.

3. **GetNumberOfItems**: `IInArchive::GetNumberOfItems(&numItems)` returns the total count of items (files + dirs + anti-items) in the archive.

4. **Per-Item Property Loop**: For each item index `i` from `0` to `numItems-1`, `IInArchive::GetProperty(i, propID, &prop)` is called for each column to display. The standard column set is: `kpidMTime` (modification time), `kpidAttrib` (attributes), `kpidSize` (uncompressed size), `kpidPackSize` (compressed size), `kpidPath` (name).  In Technical mode (`-slt`), all available property IDs are enumerated via `GetPropertyInfo()` and all are printed.

5. **Format and Display**: Each property `PROPVARIANT` is converted to a string and placed in the output table. The standard format for CLI output is: `DateTime  Attr  UnpackSize  PackSize  Name` (see `kStandardFieldTable` in `List.cpp:196`).

6. **Print Totals**: After all items, summary counters (total files, total dirs, total uncompressed size, total packed size) are printed.

**Key Concepts**:

- **No codec involvement**: The codec registry (`CCodecs`) is only used for format detection and handler creation. No `IComp ressDec oder` is instantiated.
- **GetProperty is format-polymorphic**: Each archive handler implements `GetProperty()` to return format-specific data. The 7z handler reads from its in-memory header structures; ZIP reads from central directory records; TAR reads from POSIX header blocks. The caller code in `List.cpp` is identical regardless of format.
- **Technical mode** (`-slt`): Lists all available properties for each item, not just the standard five. Useful for inspecting internal archive metadata (solid flag, method, dictionary size, etc.).
- **FM panel = continuous List**: In 7zFM, the interior of an open archive is a live `IFolderFolder` view backed by the same `IInArchive` handle. Navigating into a directory calls `GetProperty(kpidPath, …)` for sub-items. The panel is not a cached snapshot — it re-queries the handler on each paint event.

---

## 3. Entry Point Analysis

**Status**: ✅

**Entry Points**:

| Interface | Entry | Code Reference |
|---|---|---|
| CLI | `7z.exe l archive...` → `Main.cpp` → `ListArchives()` | `CPP/7zip/UI/Console/List.cpp:1073` |
| FM panel navigation | Double-click archive → `CPanel` opens via `IFolderFolder` | `CPP/7zip/UI/FileManager/Panel.cpp` |
| FM "List" view | Archive interior rendered by CPanel using `IInArchive::GetProperty()` | Same `IInArchive` handle, queried per paint |

**Class / Module Hierarchy (CLI path)**:

| Layer | Class / Module | Responsibility | Code Reference |
|---|---|---|---|
| Entry | `Main.cpp` | Dispatches `kList` command type | `Main.cpp:1272` |
| List driver | `ListArchives()` free function | Iterates archive paths; opens each; calls per-archive list | `List.cpp:1073` |
| Archive opener | `CArcLink::Open_Strict()` | Format detection; creates `IInArchive` | `OpenArchive.cpp` |
| Property loop | `ListArchives()` inner loop | Calls `GetNumberOfItems()` then `GetProperty()` per item | `List.cpp:1293` |
| Format renderer | `PrintItemRow()` / `ConvertPropertyToString()` | PROPVARIANT → display string | `List.cpp` |
| Archive handler | e.g. `C7zHandler`, `CZipHandler` | Implements `GetProperty()` from in-memory header | Per-format handler |

---

## 4. Data Structures

**Status**: ✅

| Field / Object | Type | Description |
|---|---|---|
| `CListOptions` | struct | Options for list operation: `TechMode`, `ExcludeDirItems`, `ExcludeFileItems`, `DisablePercents` |
| `kStandardFieldTable` | `CFieldInfoInit[]` | Defines 5 standard columns: `kpidMTime`, `kpidAttrib`, `kpidSize`, `kpidPackSize`, `kpidPath` |
| `PROPVARIANT` | Win32 COM type | One value slot per `GetProperty()` call; cleared after use |
| `numItems` | `UInt32` | Total item count from `GetNumberOfItems()` |
| Stats accumulators | `UInt64` | Per-archive: `numFiles`, `numDirs`, `totalSize`, `totalPackSize` |

**No archive handler internal structures are exposed** — all data crosses the `IInArchive` interface boundary as `PROPVARIANT` values.

---

## 5. Algorithm Deep Dive

**Status**: ✅

**Algorithm**: Single-pass header read. There is no iterative convergence step.

1. For each archive path (sorted and deduped):
   1. Open archive with `CArcLink::Open_Strict()`.
   2. If TechMode: call `GetArchivePropertyInfo()` + `GetArchiveProperty()` to print volume-level properties (format, physical size, headers size, method, solid flag, etc.).
   3. Call `GetNumberOfItems(&numItems)`.
   4. For each item `i` in `[0, numItems)`:
      - Determine if item passes `NWildcard::CCensor` filter. If not, skip.
      - For each column in `kStandardFieldTable` (or all properties in TechMode): call `GetProperty(i, propID, &prop)`, convert to string, add to output row.
      - Accumulate `totalSize += kpidSize`, `totalPackSize += kpidPackSize`, `numFiles++` / `numDirs++` based on `kpidIsDir`.
   5. Print per-archive totals.
2. Print grand totals across all archives.

**Technical Mode Additional Properties** (from `kPropIdToName[]` in `List.cpp:28`): Path, Name, Extension, Folder, Size, Packed Size, Attributes, Created, Accessed, Modified, Solid, Encrypted, CRC, Type, Method, Dictionary Size, Block, and many more — 70+ named properties in the table.

**Property type conversion**: `PROPVARIANT` `vt` field determines how to render the value:
- `VT_UI8` / `VT_UI4`: decimal integer (sizes, CRC shown as hex)
- `VT_FILETIME`: converted to local date-time string
- `VT_BSTR`: UTF-16LE string, converted to display encoding
- `VT_BOOL`: `+` / `-` flag character
- `VT_EMPTY`: field is absent — shows blank or format-specific placeholder

---

## 6. State Mutations

**Status**: ✅

**No disk state is modified.**

| Step | In-Memory Change |
|---|---|
| Archive open | Handler's in-memory header structures populated |
| `GetProperty()` call | `PROPVARIANT` created, used, then `VariantClear()`ed |
| Stat accumulation | Local counters (`numFiles`, `totalSize`, etc.) incremented |
| Output | Written to stdout or displayed in panel; not persisted |

The archive file on disk is opened read-only. The handler's internal state is created in memory and released when the `IInArchive` handle goes out of scope.

---

## 7. Error Handling

**Status**: ✅

**Error: Cannot Open Archive**
- Handler fails to recognize format or file cannot be read.
- `ListArchives()` records the error, increments `numErrors`, and continues with remaining archives.
- CLI reports: `"ERROR: ...archive path... : Can not open file as archive"`.

**Error: Password Required for Encrypted Headers**
- Some 7z archives encrypt headers. `GetNumberOfItems()` may fail or return 0 without the password.
- The open callback prompts for a password. If no password is supplied the archive is skipped with an error.

**Error: Incomplete/Corrupted Archive**
- If header parsing fails mid-way, the handler may return partial results (items read before the corruption) plus an error code.
- The list output shows what was readable; an error is reported for the archive.

**No CRC errors possible** — List never reads compressed data; it cannot encounter data corruption in the payload stream.

---

## 8. Integration Points

**Status**: ✅

| Component | Role |
|---|---|
| `CCodecs` | Format detection and `IInArchive` handler creation |
| `IInArchive` | `GetNumberOfItems()`, `GetProperty(i, propID, …)`, `GetPropertyInfo()` |
| `NWildcard::CCensor` | Filters which items are shown (from CLI wildcard arguments) |
| `CStdOutStream` (CLI) / CPanel (FM) | Output destination — stdout for CLI, panel grid for FM |
| `CArcLink` | Handles nested archive chains (e.g., .tar inside .gz) |

No codec, no stream pipeline, no file write API.

---

## 9. Key Insights

**Status**: ✅

**Design Philosophy**: `GetProperty()` is 7-Zip's universal metadata bus. Every archive handler must implement `GetProperty(index, propID, *value)`, which makes List a single implementation that works across all 50+ supported formats. A new archive format requires only that its handler correctly populate `GetProperty()` — the display logic in `List.cpp` does not change.

**FM Panel Architecture**: The File Manager panel treats the archive interior identically to a filesystem directory. The `IFolderFolder` abstraction wraps `IInArchive` so that navigation (cd into subdirectory), sorting (by size, name, date), and column display all use exactly the same `GetProperty()` calls as the CLI list command. This means the "browsing" experience in FM has zero additional archive-specific code.

**Technical Mode as Diagnostic Tool**: `7z l -slt archive.7z` dumps every property the handler knows for every item. This is the fastest way to inspect format internals — method parameters, solid block boundaries, encrypted flags, host OS, and any handler-specific properties — without writing any extraction code.

---

## 10. Conclusion

**Status**: ✅

**Summary**:
1. List is the simplest archive workflow — one archive open, one `GetNumberOfItems()`, then a `GetProperty()` loop with no codec, no stream, and no disk write.
2. `GetProperty()` is completely polymorphic — the identical list driver works across all archive formats.
3. The FM panel view is architecturally identical to CLI list — both consume the `IInArchive` interface directly.
4. No CRC or data integrity check is possible from List alone — use Test (WF-03) to validate archive contents.
5. Technical mode (`-slt`) exposes all handler-level metadata, making it the primary diagnostic command for archive inspection.

**Documentation Completeness**:
- ✅ `kStandardFieldTable` five-column layout extracted from source
- ✅ Technical mode behavior documented
- ✅ FM panel = IFolderFolder wrapping IInArchive connection documented
- ✅ Property type conversion rules documented
