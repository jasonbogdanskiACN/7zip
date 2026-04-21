# Phase 3: Service Orchestration

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Overview

7-Zip does not use named service or manager classes in the traditional sense. Orchestration is instead performed by free functions in `CPP/7zip/UI/Common/`, which assemble the codec registry, open archives, and drive encode/decode pipelines. The codec registry itself is populated through static-initialization self-registration — not by any explicit initialization call in the orchestration layer.

---

## CCodecs — Codec Registry

**Location**: `CPP/7zip/UI/Common/LoadCodecs.h`, `LoadCodecs.cpp`

**Purpose**: The central registry that holds all loaded format handlers (archive formats), compression codecs, and hashers. Passed by pointer into every archive operation function.

**Initialization sequence**:

1. When `7zFM.exe`, `7zG.exe`, or `7z.exe` starts, it calls `CCodecs::Load()`.
2. `Load()` first collects all built-in formats that were self-registered at static-init time via `RegisterArc()`.
3. If `Z7_EXTERNAL_CODECS` is defined (which it is for the three main binaries), `Load()` also scans the application directory for DLL files. Each DLL exports a `GetHandlerProperty2()` function and optionally a `SetCodecs()` hook. Matching DLLs have their handlers appended to the registry.
4. The registry is then immutable for the lifetime of the operation.

**What it holds**:
- `Formats`: list of `CArcInfoEx` records — format name, extension list, magic signatures, flag capabilities, and factory functions for `IInArchive` / `IOutArchive`.
- `Codecs`: list of codec descriptors — name, CLSID pairs for encoder and decoder.
- `Hashers`: list of hasher descriptors.

**Source**: `CPP/7zip/UI/Common/LoadCodecs.h:50-120`

---

## OpenArchive — Archive Open Orchestration

**Location**: `CPP/7zip/UI/Common/OpenArchive.h`, `OpenArchive.cpp`

**Entry point**: `CArcLink::Open_Strict(COpenOptions &op, IOpenCallbackUI *callback)`

**Responsibility**: Given a file path and a set of candidate format types, determine which handler can open the archive and return an open `IInArchive` object.

**Process**:

1. Opens the source file as a seekable `IInStream`.
2. Iterates through candidate format handlers from the `CCodecs` registry. The candidate list is built by matching the file extension, then by running magic-byte signature checks for handlers that declare them.
3. For each candidate handler, creates an `IInArchive` instance via the handler's factory function and calls `IInArchive::Open()` with the stream.
4. If `Open()` returns `S_OK`, the handler is accepted and the archive is open.
5. If no handler accepts the stream, returns `S_FALSE`.
6. Password-protected headers: if `IInArchive::Open()` returns a password request, it is forwarded to the `IOpenCallbackUI::Open_CryptoGetTextPassword()` callback. The callback shows a password dialog in GUI mode or reads from stdin in CLI mode.

**Source**: `CPP/7zip/UI/Common/OpenArchive.h`, referenced from `Extract.cpp` and `Update.cpp`

---

## Extract() — Decompression Orchestration

**Location**: `CPP/7zip/UI/Common/Extract.h`, `Extract.cpp`

**Signature**: `HRESULT Extract(CCodecs *codecs, ..., const CExtractOptions &options, IOpenCallbackUI *openCallback, IExtractCallbackUI *extractCallback, ..., CDecompressStat &st)`

**Process**: See Phase 1 Data Flow — Extract. The function is stateless between calls; all per-operation state is held in the callback objects and the `CDecompressStat` output struct.

---

## UpdateArchive() — Compression Orchestration

**Location**: `CPP/7zip/UI/Common/Update.h`, `Update.cpp`

**Signature**: `HRESULT UpdateArchive(CCodecs *codecs, ..., CUpdateOptions &options, CUpdateErrorInfo &errorInfo, IOpenCallbackUI *openCallback, IUpdateCallbackUI2 *callback, bool needSetPath)`

**Process**: See Phase 1 Data Flow — Compress. Delegates to the internal `Compress()` function which builds the `IOutArchive` and drives the codec chain.

---

## Phase 3 Service Orchestration Checklist

- [x] Codec registry initialization sequence documented
- [x] Archive open orchestration documented
- [x] Decompression orchestration entry point identified
- [x] Compression orchestration entry point identified
- [x] No further named Service/Manager/Handler classes found [VERIFIED: 2026-03-26]
