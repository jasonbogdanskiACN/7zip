# Phase 1: Project Structure

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Module Breakdown

The 7-Zip source tree is organized into four top-level directories:

| Directory | Language | Purpose |
|-----------|----------|---------|
| `Asm/`    | Assembly (MASM / GAS) | Platform-optimized routines for CRC, AES, SHA, LZMA decode, LzFind, and Sort — called by the C layer |
| `C/`      | C         | Self-contained LZMA SDK: archive reader (`7z`), LZMA/LZMA2 decoders, PPMd, SHA, Zstd, thread abstraction. Used by both C and C++ layers. |
| `CPP/`    | C++       | Full application — see module tree below |
| `DOC/`    | Text      | User documentation, format specs, license |

### CPP/ Module Tree

```
CPP/
├── Common/          Core utility classes — strings, XML, CRC registration, command-line parser,
│                    UTF-8/16 conversion, wildcard matching. No platform-specific APIs.
├── Windows/         Win32 API wrapper classes — files, registry, threads, COM property variants,
│                    security, shell operations, UI controls. Isolates Win32 surface from logic.
└── 7zip/
    ├── Archive/     One handler class per archive format (7z, Zip, Tar, GZip, BZip2, RAR,
    │                ISO, NTFS, ELF, PE, Wim, CAB, DMG, VHD, VMDK, QCOW, GPT, and 30+ others).
    │                Each handler registers itself at static init time via RegisterArc().
    ├── Bundles/     Build targets — wires together Archive, Compress, Crypto, and UI modules
    │                into specific executables or DLLs.
    ├── Common/      Codec infrastructure — stream wrappers, filter chain, coder registry,
    │                property management, progress reporting, multi-threaded streaming.
    ├── Compress/    Compression codec implementations — LZMA, LZMA2, Deflate, BZip2, PPMd,
    │                Zstd, XZ, BCJ transforms, Rar decoders, LZX, Quantum, and others.
    ├── Crypto/      Encryption — AES-256 (hardware-accelerated), ZipCrypto, WinZip AES,
    │                RAR2/5 crypto, HMAC-SHA1/256, PBKDF2.
    └── UI/
        ├── Agent/       COM out-of-process agent server. Runs in a separate process to provide
        │                format-handler isolation; communicates via COM streams.
        ├── Client7z/    Low-level programmatic client to the IArchive COM interface.
        ├── Common/      Shared UI infrastructure — archive open/update/extract orchestration,
        │                command-line parsing, callback interfaces, codec loading.
        ├── Console/     CLI tool (7z.exe) — full command dispatcher for all operations.
        ├── Explorer/    Windows Explorer shell extension — context menus, property pages,
        │                drag-and-drop handlers.
        ├── Far/         Far Manager plugin.
        ├── FileManager/ GUI file manager — 7zFM.exe. Dual-pane Win32 window, folder tree,
        │                list view, toolbar, and orchestrates all user-facing operations.
        └── GUI/         GUI dialogs — 7zG.exe. Compress, Extract, Benchmark, Hash dialogs;
                         invoked by Explorer shell extension and by 7zFM.
```

---

## Build Targets

| Target       | Source Bundle Directory       | Key Binaries       |
|--------------|-------------------------------|--------------------|
| File manager | `Bundles/Fm/`                 | `7zFM.exe`         |
| GUI dialogs  | `Bundles/SFXWin/` + `UI/GUI/` | `7zG.exe`          |
| CLI tool     | `Bundles/Alone2/`             | `7z.exe`           |
| Codec DLL    | `Bundles/Format7zF/`          | `7z.dll`           |
| Standalone   | `Bundles/Alone/`              | `7za.exe`          |
| SFX stub     | `Bundles/SFXWin/`             | `7z.sfx`           |
| Console SFX  | `Bundles/SFXCon/`             | `7zCon.sfx`        |

---

## Phase 1 Project Structure Checklist

- [x] Module structure documented with purpose for each top-level directory
- [x] Build targets identified and mapped to source directories
- [x] C / C++ / Assembly layer boundaries described
