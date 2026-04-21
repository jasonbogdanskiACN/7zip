# Phase 2.5: State Change Patterns

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## State Changes: Extract Operation

**Entry point**: `Extract()` in `CPP/7zip/UI/Common/Extract.cpp`
**Triggered by**: User pressing Extract in `7zFM.exe` or `7z.exe e` / `7z.exe x` command

### Before / After State Table

| Structure / File | Field / Path | Before | After | Condition |
|---|---|---|---|---|
| `CDecompressStat` | `NumArchives` | 0 | Count of archives processed | Always |
| `CDecompressStat` | `NumFiles` | 0 | Count of file entries extracted | Always |
| `CDecompressStat` | `NumFolders` | 0 | Count of directory entries extracted | Always |
| `CDecompressStat` | `UnpackSize` | 0 | Total bytes written to output files | Always |
| `CDecompressStat` | `PackSize` | 0 | Total compressed bytes read from archives | Always |
| Disk: output file | Exists? | No (or old version) | Created at `OutputDir + item.Path` | For each matched item, if not test-mode |
| Disk: output file | Timestamps | — | Set to values stored in archive (MTime, CTime, ATime) | After data write succeeds |
| Disk: output file | Attributes | — | Set to archive-stored attributes (read-only, hidden, etc.) | After data write succeeds |
| Intermediate temp buffer | Exists? | — | Used in memory during decompression, released on completion | Per folder/stream |

**Transaction boundary**: Each file is written atomically from the perspective of the callback — if `SetOperationResult()` reports a CRC error, the output file is already closed on disk but marked as having a data error. There is no rollback for partially-extracted files — a failed extract leaves partially written output files on disk. The caller receives an error status but already-extracted files remain.

**Overwrite behavior**: Controlled by `NOverwriteMode::EEnum` in `CExtractOptions`. In `kAsk` mode, the overwrite decision is delegated to the UI callback before each file is opened for writing.

**Code Reference**: `CPP/7zip/UI/Common/Extract.cpp:540-580`, `CPP/7zip/UI/Common/ArchiveExtractCallback.cpp`

---

## State Changes: Compress (Add to Archive)

**Entry point**: `UpdateArchive()` → `Compress()` in `CPP/7zip/UI/Common/Update.cpp`
**Triggered by**: User pressing Add in `7zFM.exe` or `7z.exe a` command

### Before / After State Table — Single Archive, Temp-File Mode

| Structure / File | Field / Path | Before | After | Condition |
|---|---|---|---|---|
| Disk: temp file | Exists? | No | Created at `TempPrefix + Name + ".ext.tmp[N]"` | When updating existing archive (`ap.Temp == true`) |
| Disk: temp file | Content | — | Full new archive written, stream closed | On successful encode |
| Disk: final archive | Content | Old archive bytes (or absent) | Replaced by temp file via `MyMoveFile_with_Progress()` | On successful encode + close |
| Disk: final archive | MTime | Old value | Set to latest MTime among all added items (if `SetArcMTime == true`) | If `SetArcMTime` option is set |
| `CArchivePath.TempPostfix` | Value | Empty string | Numeric suffix (e.g., "1", "2") if temp name collision | If first temp name is already in use |
| `CTempFiles.Paths` | List | Empty | Temp file paths added | Temp files registered for cleanup |
| `CTempFiles.NeedDeleteFiles` | bool | true | false | On successful move to final path (disables cleanup) |
| `CFinishArchiveStat.OutArcFileSize` | Value | 0 | Final archive byte size | After stream close |

**Transaction boundary**: The temp file is written completely and flushed before the move to the final path is attempted. If the move (`MyMoveFile_with_Progress()`) fails, the temp file is preserved on disk and an error is returned. The original archive is not modified if a temp file was used. If the temp file cannot even be created, no disk state changes occur.

**Exception**: When writing directly to the final path (no existing archive, no working-dir override), failure during write leaves a partial archive at the final path. No rollback occurs.

**Code Reference**: `CPP/7zip/UI/Common/Update.cpp:690-710` (temp file creation), `Update.cpp:1628-1660` (move to final path)

---

## State Changes: Delete from Archive

**Entry point**: `UpdateArchive()` with action set `k_ActionSet_Delete`
**Effect**: Items marked `kOnlyInArchive` with action `kCompress` for anti-items, or `kIgnore` for the items to be removed. A new archive is written without the deleted items. Follows the same temp-file pattern as Compress.

No additional state changes beyond the Compress pattern — an item is "deleted" by not being written to the new archive.

---

## State Changes: Rename within Archive

**Entry point**: `UpdateArchive()` with `CRenamePair` list populated
**Additional state**: `CUpdatePair2.NewNameIndex` and `CUpdatePair2.NewProps = true` are set for matching items. The new names are stored in `newNames` (a `UStringVector`). The rename writes a new archive with updated metadata; the packed data streams are copied unchanged.

---

## State Changes: Test (Integrity Check)

**Entry point**: `Extract()` with `CExtractOptions.TestMode == true`
**State changes**: No files written to disk. `CDecompressStat` counters are still incremented. The callback receives `SetOperationResult()` with `NExtract::NOperationResult::kDataError` if the decompressed CRC does not match the stored CRC.

**Transaction boundary**: Stateless — no disk changes, no rollback needed.

---

## Phase 2.5 Checklist

- [x] State changes for Extract documented with before/after pairs
- [x] State changes for Compress (Add/Update) documented with temp-file pattern
- [x] State changes for Delete and Rename documented
- [x] State changes for Test documented
- [x] Transaction boundaries identified for each operation
- [x] Code references provided
