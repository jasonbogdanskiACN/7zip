# Phase 6.2 + 6.3 — Candidate Workflow Inventory and Readiness Assessment

**System**: 7-Zip 26.00  
**Date**: 2026-03-26  
**Status**: Complete — Phase 7 gate items 6.2 and 6.3 satisfied  

---

## Phase 6.2 — Candidate Workflow Inventory

This section enumerates every distinct user-facing workflow in 7-Zip. Each entry includes the triggering surface, the primary code path, and a readiness verdict for full vertical-slice documentation in Phase 7.

---

### WF-01: Add Files to Archive (Compress)

| Field | Value |
|---|---|
| **Surface** | 7zFM Add toolbar button · right-click context menu "Add to archive…" · 7zG.exe invocation · `7z.exe a` |
| **Entry points** | `FM.cpp:884`, `Panel.cpp:922` → `CCompressDialog` → `UpdateGUI()` → `UpdateArchive()` → `Compress()` |
| **Key code** | `CPP/7zip/UI/GUI/UpdateGUI.cpp`, `CPP/7zip/UI/Common/Update.cpp` |
| **Parameters** | Archive path, format, compression level, method, dictionary, solid block, threads, password, encryption method, encrypt-headers, SFX module, update mode, path mode, volume size, share flag, delete-after-compress, send-by-email |
| **State change** | New archive file at `CArchivePath.GetFinalPath()` created (via temp file and atomic move) |
| **Gate items covered** | Phase 2 (CDirItem, CUpdatePair), Phase 2.5 (temp-file state), Phase 3 (validation), Phase 3.4 (LZMA engine), Phase 4 (CompressDialog) |
| **Phase 7 readiness** | **READY** — all layers fully documented |

---

### WF-02: Extract Files from Archive

| Field | Value |
|---|---|
| **Surface** | 7zFM Extract toolbar button · right-click "Extract Files…" / "Extract Here" / "Extract to folder\" · 7zG.exe · `7z.exe x` / `7z.exe e` |
| **Entry points** | `FM.cpp:885`, `Panel.cpp:1008` → `CExtractDialog` → `Extract()` |
| **Key code** | `CPP/7zip/UI/Common/Extract.cpp`, `CPP/7zip/UI/FileManager/ExtractCallback.cpp` |
| **Parameters** | Output directory, path mode (full/no paths/absolute), overwrite mode (ask/always/skip/rename/rename-existing), password, keep broken files, NTFS security streams, zone mark (Mark-of-the-Web) |
| **State change** | Files created at `OutputDir + item path`; timestamps, attributes, NTFS streams set after data write |
| **Gate items covered** | Phase 2 (CExtractOptions, CArcItem), Phase 2.5 (no rollback on CRC error), Phase 3 (archive open + codec chain), Phase 4 (ExtractDialog) |
| **Phase 7 readiness** | **READY** — all layers fully documented |

---

### WF-03: Test Archive Integrity

| Field | Value |
|---|---|
| **Surface** | 7zFM Test toolbar button · right-click "Test archive" · `7z.exe t` |
| **Entry points** | `FM.cpp:886`, `Panel.cpp:1103` → no dialog → `Extract()` with `TestMode = true` |
| **Key code** | `CPP/7zip/UI/Common/Extract.cpp` (same path as WF-02; output stream is a null-sink CRC stream) |
| **Parameters** | Optional password |
| **State change** | No files written; `CDecompressStat` counters accumulated; CRC errors reported in progress dialog |
| **Gate items covered** | Phase 2.5 (stateless — no disk change), Phase 3 (codec chain), Phase 4 (Test trigger) |
| **Phase 7 readiness** | **READY** — all layers documented (mostly shared with WF-02) |

---

### WF-04: List Archive Contents

| Field | Value |
|---|---|
| **Surface** | 7zFM panel navigation (open archive, browse interior) · `7z.exe l` |
| **Entry points** | `CPanel` opens via `IFolderFolder` interface → `FolderItems` enumeration via `IInArchive::GetProperty()` |
| **Key code** | `CPP/7zip/UI/FileManager/Panel.cpp`, `CPP/7zip/UI/Common/LoadCodecs.cpp`, each archive handler's `GetProperty()` |
| **Parameters** | Archive path (implicit); optional password for encrypted archives |
| **State change** | No disk changes; archive item properties displayed in panel / console |
| **Phase 7 readiness** | READY (shared with Extract open path; no unique code path requiring separate slice) |

---

### WF-05: Update / Delete Files in Existing Archive

| Field | Value |
|---|---|
| **Surface** | 7zFM panel operations (Delete F8, Rename F2) inside archive interior · `7z.exe u` / `7z.exe d` / `7z.exe rn` |
| **Entry points** | `PanelOperations.cpp` → `IFolderOperations::CopyTo()` / `Delete()` / `Rename()` → `UpdateArchive()` |
| **Key code** | `CPP/7zip/UI/Common/Update.cpp`, `CPP/7zip/UI/FileManager/PanelOperations.cpp` |
| **State change** | Archive rewritten via temp-file + atomic move (same pattern as WF-01) |
| **Phase 7 readiness** | READY (Update path is documented; same compress pipeline as WF-01 with `kUpdate` action set) |

---

### WF-06: Benchmark (LZMA Performance Test)

| Field | Value |
|---|---|
| **Surface** | 7zFM Tools → Benchmark · `7z.exe b` |
| **Entry points** | GUI: Menu → `CBenchmarkDialog::StartBenchmark()` → `CThreadBenchmark::Process()` runs LZMA encode/decode in background thread |
| **Key code** | `CPP/7zip/UI/GUI/BenchmarkDialog.cpp`, LZMA encode/decode called via codec interfaces |
| **Output** | Compression speed (KB/s), decompression speed (KB/s), LZMA rating (MIPS/GIPS), CPU/RAM info, clock frequency (where available) |
| **Parameters** | Dictionary size (256 KB – max), number of threads, number of passes |
| **State change** | No disk changes; results displayed in dialog or stdout |
| **Phase 7 readiness** | SECONDARY — shared codec path with WF-01; no unique data flow. Include in Phase 7 only if benchmark workflow is a priority. |

---

### WF-07: Compute File Hash / CRC

| Field | Value |
|---|---|
| **Surface** | 7zFM Tools → CRC SHA → (CRC32 / CRC64 / SHA-1 / SHA-256 / SHA-512 / BLAKE2sp / XXH64 / MD5 / all) · `7z.exe h` |
| **Entry points** | GUI: `GUI.cpp:379` → `HashCalcGUI()` → `HashCalc()` free function; presents results in `HashDialog` |
| **Key code** | `CPP/7zip/UI/GUI/HashGUI.cpp`, `CPP/7zip/UI/Common/HashCalc.cpp` |
| **Parameters** | Selected files, hash algorithm(s) |
| **State change** | No disk changes; digest values displayed in dialog or panel columns |
| **Phase 7 readiness** | SECONDARY — unique workflow with simple data flow (read → hash → display). Include in Phase 7 if hash workflow is a priority. |

---

### WF-08: Shell Extension Context Menu (Explorer Integration)

| Field | Value |
|---|---|
| **Surface** | Right-click on files in Windows Explorer → 7-Zip submenu |
| **Entry points** | `CZipContextMenu::InvokeCommand()` → dispatches to same `UpdateGUI()` / `Extract()` calls as GUI workflows |
| **Key code** | `CPP/7zip/UI/Explorer/ContextMenu.cpp` |
| **State change** | Delegates entirely to WF-01 (Add) or WF-02 (Extract) code paths |
| **Phase 7 readiness** | Not a separate vertical slice — it is a trigger surface for WF-01/WF-02. Document as an entry-point variant if needed. |

---

### WF-09: Console (7z.exe) — Full CLI Mode

| Field | Value |
|---|---|
| **Surface** | `7z.exe` invoked from terminal |
| **Entry points** | `CPP/7zip/UI/Console/Main.cpp` — `ParseCommandLine()` → dispatches to WF-01 through WF-07 code pathss |
| **Unique aspect** | Console provides stdout/stderr progress streams; percent display; `--stdin`/`--stdout` pipe mode |
| **Phase 7 readiness** | Shares all core logic with GUI workflows. A separate vertical slice for CLI Add (WF-01) covers the unique console callback path. |

---

### Phase 7 Priority Ranking

Based on architectural significance, user-facing impact, and uniqueness of code path:

| Priority | Workflow | Reason |
|---|---|---|
| 1 | **WF-01: Add to Archive (Compress)** | Most complex workflow; exercises entire codec stack, validation, temp-file state management |
| 2 | **WF-02: Extract from Archive** | Second most complex; unique output file creation + attribute/timestamp restore path |
| 3 | **WF-03: Test Archive Integrity** | Shares Extract path; short vertical slice with high value for correctness testing |
| 4 | **WF-07: Compute File Hash** | Unique sub-system (HashCalc); simple and clean vertical slice |
| 5 | WF-06: Benchmark | Interesting LZMA path reuse; lower priority than data workflows |

---

## Phase 6.3 — Readiness Assessment (Sign-Off)

### Gate Item Checklist

| Gate Item | Required Document | Status |
|---|---|---|
| Phase 2.5 — State Change Patterns | `phase-2-5-state-changes.md` | ✅ Complete |
| Phase 3.4 — Calculation Engine Analysis | `phase-3-4-calculation-engines.md` | ✅ Complete |
| Phase 5.3 — Dependency Inventory | `phase-5-3-dependency-inventory.md` | ✅ Complete |
| Phase 6.2 — Candidate Workflow Inventory | This document (section above) | ✅ Complete |
| Phase 6.3 — Readiness Assessment Sign-Off | This section | ✅ |

All four required gate items are satisfied.

---

### Readiness Assessment

#### What we know with high confidence

1. **Core architecture**: COM-inspired plugin system, self-registration pattern, layered stream composition — fully documented (Phase 1)
2. **Data entities**: `CDirItem`, `CArcItem`, `CUpdatePair`, `CExtractOptions`, `CArchivePath`, `CDecompressStat` — all fields, types, and relationships documented (Phase 2)
3. **State changes**: The temp-file atomic-move compress pattern, the no-rollback extract behaviour, and the stateless test path are all documented with exact source line references (Phase 2.5)
4. **Business rules**: All validation rules in `CompressDialog.cpp` (password policy, memory limit, SFX gate, codec property bounds) confirmed with source locations (Phase 3)
5. **Calculation engine**: LZMA parameter space fully documented with verified parameter constraints (`lc+lp ≤ 4`, `dictSize` 4096–1.5 GB, etc.) (Phase 3.4)
6. **UI layer**: All three binary surfaces (7zFM, 7zG, 7z.exe), complete CompressDialog and ExtractDialog control inventory, all workflow trigger chains (Phase 4)
7. **Dependencies**: All external integrations confirmed and inventoried — no surprises (Phase 5.3)
8. **Known limitations**: FIXME inventory complete; no blockers to core workflows (Phase 6)

#### Identified gaps

| Gap | Severity | Impact on Phase 7 |
|---|---|---|
| Language file (.lng) string text unavailable | Low | Error message text marked `[NOT AVAILABLE]`; resource IDs are documented |
| Exact ZIP, TAR, GZ, BZ2 handler internals not read | Low — Low-priority formats | WF-01/02 documentation can focus on 7z format; multi-format coverage deferred |
| SFX module path and bundle structure not detailed | Low | SFX variant of WF-01 can note the `kDefaultSfxModule` path without detailing the PE stub |
| Far Manager plugin not fully read | Negligible | Far.cpp is a secondary UI surface |

None of these gaps affect the ability to write accurate vertical slice documentation for WF-01, WF-02, WF-03, or WF-07.

#### Decision

> **PROCEED TO PHASE 7.**  
> All phase 7 gate items are satisfied. The codebase has been sufficiently explored to write accurate, code-verified vertical slice documentation for the four priority workflows: Add to Archive (WF-01), Extract from Archive (WF-02), Test Archive Integrity (WF-03), and Compute File Hash (WF-07).  
> No external dependencies will surprise the implementation; no significant unimplemented stubs affect the primary workflows; the calculation engine is fully understood.  
> Recommended first vertical slice: **WF-01 — Add Files to a New 7z Archive**.
