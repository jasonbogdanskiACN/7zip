# Phase 1: Data Flow

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Overview

7-Zip has three primary data flows corresponding to its three main operations, all sharing the same codec and archive-handler infrastructure. The two entry-point families are the GUI file manager (`7zFM.exe`) and the CLI tool (`7z.exe`); both ultimately converge on the same `Extract()` / `Update()` orchestration functions in `CPP/7zip/UI/Common/`.

---

## Data Flow 1: Extract (Decompress)

From user action to files on disk:

1. **User trigger** — In `7zFM.exe`: user selects files in `CPanel` and presses Extract, invoking `PanelOperations.cpp`. In `7z.exe`: `Main.cpp` parses command-line arguments into a `CArcCmdLineOptions` struct with `CommandType = NCommandType::kExtract` or `kExtractFull`.

2. **Archive open** — `CCodecs::Load()` builds the list of all registered format handlers. `OpenArchive()` (in `CPP/7zip/UI/Common/OpenArchive.*`) iterates through handlers, matching each by file signature or extension. The matching handler creates an `IInArchive` object and opens the stream.

3. **Option assembly** — The extracted operation parameters are packaged into a `CExtractOptions` struct (output directory, overwrite mode, path mode, NT security flags). Password, if needed, is requested via the `IOpenCallbackUI` callback — in the GUI this shows a password dialog; in the CLI this reads from stdin.

4. **Item enumeration** — `IInArchive::GetNumberOfItems()` and `IInArchive::GetProperty()` are called for each archive entry to obtain name, size, attributes, and CRC. The wildcard censor (`NWildcard::CCensor`) filters the item list to those matching the user's selection.

5. **Stream routing** — For each item to extract, the archive handler calls `IArchiveExtractCallback::GetStream()` to obtain an output stream for the target path. The callback creates the destination file on disk (with overwrite logic applied first).

6. **Decompression** — The archive handler drives a codec chain internally. For a 7z archive this means: the handler reads the folder's packed stream, directs it through the codec sequence stored in the archive headers (e.g., LZMA2 decoder → BCJ filter → output stream). The codec sequence and properties are read from the archive metadata, not hardcoded.

7. **Completion** — The callback receives `SetOperationResult()` after each file with a status (OK / data error / CRC error / unsupported method). The UI reports progress and any errors. On success, file attributes and timestamps are written to the extracted files.

**Code references**: `CPP/7zip/UI/Common/Extract.h`, `CPP/7zip/UI/Common/ArchiveExtractCallback.h`, `CPP/7zip/Archive/IArchive.h`

---

## Data Flow 2: Compress (Add / Update)

From files on disk to an archive:

1. **User trigger** — In `7zFM.exe`: user selects files and presses Add, showing the `CompressDialog`. In `7z.exe`: command-line parses to `NCommandType::kAdd` or `kUpdate` with archive path and file wildcards.

2. **Option assembly** — The GUI dialog or CLI parser populates a `CUpdateOptions` struct: archive format (type), compression level, method (LZMA2, Deflate, etc.), dictionary size, thread count, volume size, password, and the list of files to include. An `EArcNameMode` value determines how the output path is derived.

3. **File enumeration** — `EnumDirItems()` walks the source directories applying wildcard filters. The result is a flat list of `CDirItem` records with paths, sizes, and attributes.

4. **Archive path resolution** — `CArchivePath::ParseFromPath()` determines the final archive path, optional `.tmp` staging location, and volume extension. If the archive already exists (update mode), its existing items and packed streams are preserved where unchanged.

5. **Stream construction** — The codec chain is assembled from the compression method properties. For LZMA2: `CLzmaEncoder` → optional `CBcjCoder` filter → `COutBuffer` → destination file stream. Property negotiation happens via `ICompressSetCoderProperties`.

6. **Encoding** — Each source file stream is pushed through the codec chain. The archive handler collects the packed bytes and writes the archive headers (metadata: names, sizes, timestamps, CRCs, method records) at the end.

7. **Finalization** — On success, the temporary file (if used) is moved to the final path. The `IUpdateCallbackUI` reports per-file progress and any read errors.

**Code references**: `CPP/7zip/UI/Common/Update.h`, `CPP/7zip/UI/Common/UpdateCallback.h`, `CPP/7zip/Archive/7z/`

---

## Data Flow 3: List / Test

These operations follow the same archive-open path as Extract (steps 1–4 above), but:

- **List**: calls `IInArchive::GetNumberOfItems()` and `GetProperty()` for each item, formats the results as text or a ListView, and returns. No output streams are created.
- **Test**: extract callback returns a `COutStreamWithCRC` (a null sink that computes CRC only) instead of a real file stream. After extraction the computed CRC is compared to the stored CRC from the archive metadata; a mismatch is reported as a data error.

---

## Shared Infrastructure Used by All Flows

| Component | Role in data flows |
|---|---|
| `CCodecs` | Holds all registered handlers, codecs, hashers; dispatched at open-time |
| `ISequentialInStream` / `ISequentialOutStream` | Universal byte-pipe abstraction between all layers |
| `IArchiveOpenCallback` / `IArchiveExtractCallback` / `IArchiveUpdateCallback` | Decouple the archive handler from the UI layer for password, progress, and overwrite decisions |
| `NWildcard::CCensor` | File inclusion/exclusion filter applied at item enumeration |
| `CExtractOptions` / `CUpdateOptions` | Plain data structs that carry all operation parameters from UI layer to orchestration layer |

---

## Phase 1 Data Flow Checklist

- [x] Extract flow traced from UI trigger to output file
- [x] Compress flow traced from UI trigger to output archive
- [x] List/Test flows identified as variants of the Extract open path
- [x] Shared infrastructure components identified
- [x] All major transformation points named
