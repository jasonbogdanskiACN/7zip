# Phase 1: Architecture Patterns

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Primary Architectural Pattern: COM-Inspired Plugin Architecture

7-Zip's central design pattern is a **COM-inspired plugin architecture** using custom IUnknown-derived interfaces. The system does not use the Windows COM registry — instead it implements the same interface-query mechanism (`QueryInterface` / `AddRef` / `Release`) in pure C++.

The three primary plugin extension points are:

| Extension Point | Interface | Registry Mechanism |
|---|---|---|
| Archive format handlers | `IInArchive`, `IOutArchive` (from `IArchive.h`) | `RegisterArc()` called at static init |
| Compression codecs | `ICompressCoder`, `ICompressCoder2` (from `ICoder.h`) | `RegisterCodec()` called at static init |
| Hash calculators | `IHasher` | `RegisterHasher()` called at static init |

Each archive handler and codec declares a `CRegisterArc` or `CRegisterCodec` static-duration object whose constructor calls the corresponding registration function. This means format support and codec support are registered automatically when the translation unit is linked in — no explicit initialization lists required.

When `Z7_EXTERNAL_CODECS` is defined (in `7z.exe`, `7zG.exe`, `7zFM.exe`), the `CCodecs` class additionally scans for external DLL plugins at startup and loads them dynamically.

---

## Design Patterns Present

### Self-Registration Pattern
Each format handler (e.g., `CPP/7zip/Archive/ZipHandler.cpp`) links a static `CRegisterArc` object whose constructor calls `RegisterArc(&g_ArcInfo)`. The `g_ArcInfo` record contains: format name, extension, magic-byte signature, creation factory functions, and capability flags. No central factory switch statement exists — the registry is built purely from what is linked.
Source: `CPP/7zip/Common/RegisterArc.h`, `CPP/7zip/Archive/*/` handlers.

### Interface Segregation (COM-style)
All cross-layer communication passes through narrow interfaces: `ISequentialInStream`, `ISequentialOutStream`, `IInStream`, `IOutStream`, `IArchiveOpenCallback`, `IArchiveExtractCallback`, `IArchiveUpdateCallback`, `ICompressProgressInfo`. This allows the UI layer to be completely decoupled from the codec implementations.
Source: `CPP/7zip/IStream.h`, `Archive/IArchive.h`, `ICoder.h`.

### Layered Stream Composition
Codec operations are composed by chaining stream objects. A compress operation, for example, routes bytes through: a source file stream → an optional filter (BCJ branch converter) → a compression coder (`ICompressCoder`) → an optional encryption filter → a destination archive stream. Each element in the chain implements `ISequentialInStream` or `ISequentialOutStream`.
Source: `CPP/7zip/Common/FilterCoder.*`, `CPP/7zip/Compress/`.

### Dual-Panel File Manager with Plugin-Backed Folders
The file manager (`CApp`) owns two `CPanel` instances, each of which can navigate any folder source implementing the `IFolderFolder` interface. When a panel enters an archive, it creates an Agent process (the out-of-process COM server from `UI/Agent/`) and wraps the archive as a virtual folder. This means the `CPanel` class treats the local filesystem and archive interiors with the same code paths.
Source: `CPP/7zip/UI/FileManager/App.h`, `Panel.h`, `IFolder.h`.

### Agent (Out-of-Process) Pattern
`7zFM.exe` hosts archive operations in the `Agent` sub-process rather than in-process. The agent is a COM server that receives stream references and executes format-handler logic in isolation. This protects the file manager from crashes caused by broken archive files.
Source: `CPP/7zip/UI/Agent/`.

### Callback Interfaces for Progress and Overwrite Decisions
Long-running operations (open, extract, update) accept callback interfaces (`IOpenCallbackUI`, `IExtractCallbackUI`, `IUpdateCallbackUI`) that the UI layer implements. The business logic calls back into the UI for user decisions (overwrite? password?) and progress updates without taking a direct dependency on any UI class.
Source: `CPP/7zip/UI/Common/ArchiveOpenCallback.h`, `ArchiveExtractCallback.h`, `UpdateCallback.h`.

---

## Naming Conventions Observed

| Suffix / Prefix | Meaning |
|---|---|
| `I*` (pure abstract class) | Interface definition (e.g., `IInArchive`) |
| `C*` (concrete class) | Implementation class (e.g., `CHandler`, `CApp`, `CPanel`) |
| `*Handler` | Archive format handler implementing `IInArchive` / `IOutArchive` |
| `*Coder` / `*Decoder` / `*Encoder` | Compression codec (e.g., `LzmaDecoder`, `DeflateEncoder`) |
| `*Callback` | Progress or decision callback implementation |
| `*Register.*` | Static-init registration translation unit for a handler or codec |
| `N*` namespace | Utility namespace (e.g., `NFile`, `NWindows`, `NCommandType`) |
| `k*` constant | Named constant (e.g., `kNumPanelsMax`, `kParentFolderID`) |

---

## Phase 1 Architecture Patterns Checklist

- [x] Primary architecture pattern identified and described
- [x] Plugin registration mechanism documented
- [x] Stream composition pattern documented
- [x] Agent out-of-process isolation pattern documented
- [x] Callback interface pattern documented
- [x] Naming conventions observed and recorded
