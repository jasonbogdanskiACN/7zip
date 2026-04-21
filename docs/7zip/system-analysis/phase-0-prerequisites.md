# Phase 0: Prerequisites

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Resource Inventory

| Resource               | Status | Location / Notes                                                                    |
|------------------------|--------|-------------------------------------------------------------------------------------|
| Source code            | ✅     | `C:\dev\7zip` — full C and C++ source available                                    |
| Config files           | ✅     | Build configuration via MSVC makefiles (`CPP/7zip/makefile`, per-module `.mak`)    |
| External libraries     | ✅     | None — 7-Zip is fully self-contained; no external package manager used             |
| Build environment      | ⚠️     | Requires MSVC + MASM (ml.exe / ml64.exe); not confirmed buildable in this session  |
| Domain expert          | ✅     | User is present for clarification                                                  |
| Test / sample data     | ⚠️     | No dedicated test fixtures found in source tree; DOC/ has text documentation only  |

---

## System Type

**GUI application** — 7-Zip is a Windows file archiver that ships multiple binaries from one source tree:

| Binary    | Purpose                                                         | Primary Source Directory               |
|-----------|-----------------------------------------------------------------|----------------------------------------|
| `7zFM.exe`| GUI dual-pane file manager (primary GUI)                        | `CPP/7zip/UI/FileManager/`             |
| `7zG.exe` | GUI dialogs for compress / extract invoked from Explorer/CLI    | `CPP/7zip/UI/GUI/`                     |
| `7z.exe`  | CLI tool (all operations via command-line flags)                | `CPP/7zip/UI/Console/`                 |
| `7z.dll`  | COM-based codec DLL (archive handlers + codecs)                 | `CPP/7zip/Bundles/Format7zF/`          |
| Shell ext | Windows Explorer context menu / property sheet integration      | `CPP/7zip/UI/Explorer/`                |

The analysis focal point for the "GUI application" designation is `7zFM.exe` (file manager) and `7zG.exe` (GUI dialogs).

---

## Top-Level Project Structure

```
C:\dev\7zip\
├── Asm/          — Platform-specific assembly optimizations (x86, x64, arm, arm64)
│   ├── arm/          CRC optimizations (ARMv8 CRC instruction)
│   ├── arm64/        LZMA decoder and assembly bootstrap
│   └── x86/          CRC, AES, SHA, LZMA decoder, LzFind, XZ-CRC64, Sort
├── C/            — Pure C library (LZMA SDK + 7-Zip C layer)
│   ├── 7zArcIn.c etc.  7z archive reader in C
│   ├── LzmaDec.c etc.  LZMA/LZMA2 decoder
│   ├── Ppmd*.c         PPMd compression
│   ├── Sha*.c          SHA-1, SHA-256, SHA-512 implementations
│   ├── Threads.c       Platform threading abstraction
│   └── Util/           C-layer utility programs (standalone LZMA, SFX setup)
├── CPP/          — Main C++ application
│   ├── Common/         Core utilities: strings, XML, CRC, command-line parser
│   ├── Windows/        Windows API wrapper classes (File, Registry, Sync, etc.)
│   └── 7zip/           Application core
│       ├── Archive/    Format handlers: 7z, Zip, Tar, GZip, BZip2, RAR, ISO, etc.
│       ├── Bundles/    Executable bundle targets (Alone, Fm, GUI, SFX variants)
│       ├── Common/     Shared codec infrastructure (streams, filters, coder registry)
│       ├── Compress/   Compression codecs: LZMA, Deflate, BZip2, PPMd, Zstd, etc.
│       ├── Crypto/     Encryption: AES, SHA1/256 HMAC, PBKDF2, ZipCrypto
│       └── UI/
│           ├── Agent/       COM out-of-process agent server (process isolation)
│           ├── Client7z/    Programmatic client (IArchive interface)
│           ├── Common/      Shared UI utilities (archive cmd-line, callbacks, etc.)
│           ├── Console/     CLI tool (Main.cpp, command dispatcher)
│           ├── Explorer/    Windows Explorer shell extension
│           ├── Far/         Far Manager plugin
│           ├── FileManager/ GUI file manager — 7zFM.exe (primary GUI application)
│           └── GUI/         GUI dialogs — 7zG.exe (compress/extract/benchmark)
├── DOC/          — User documentation (readme, format specs, license)
└── docs/         — Reverse engineering methodology (this project)
```

---

## Version Information

- **Product**: 7-Zip
- **Version**: 26.00
- **Release Date**: 2026-02-12
- **Author**: Igor Pavlov
- **Copyright**: 1999–2026 Igor Pavlov
- **License**: GNU LGPL (unRAR code: unRAR license; some code: BSD 3-clause)
- **Version constant source**: `C/7zVersion.h`

---

## Build System

- **Platform**: Windows (primary); Linux/macOS via GCC/Clang makefiles
- **Windows build**: MSVC nmake (`CPP/7zip/makefile`), also `.dsp`/`.dsw` for VS IDE
- **Linux/macOS build**: GCC / Clang makefiles (`var_gcc*.mak`, `var_clang*.mak`, `var_mac*.mak`)
- **Assembly**: MASM (`ml.exe` for x86, `ml64.exe` for x64); GAS (`.S` files for ARM)
- **Target platforms**: x86, x64, arm, arm64, ia64
- **No external package manager** (no CMakeLists.txt, no vcpkg.json, no conanfile.txt)

---

## NO GUESSING Policy

**Confirmed.** All documentation in this project follows the NO GUESSING policy:

| Forbidden                              | Required instead                                         |
|----------------------------------------|----------------------------------------------------------|
| Guess a validation rule                | Verify in code or mark `[NEEDS CLARIFICATION]`           |
| Assume a calculation formula           | Extract exact formula or mark `[NEEDS CLARIFICATION]`    |
| Infer a default value                  | Find source in config/code or mark `[NOT AVAILABLE]`     |
| Make up an error message               | Quote it exactly from code or mark `[NEEDS CLARIFICATION]`|
| Assume a state change                  | Trace exact field mutation or mark `[NEEDS CLARIFICATION]`|

**Status markers used consistently throughout**:
- `[NEEDS CLARIFICATION]` — information exists but is unclear
- `[NOT AVAILABLE]` — dependency confirmed unavailable
- `[BLOCKED]` — cannot proceed without missing information
- `[VERIFIED: YYYY-MM-DD]` — confirmed with code, data, or domain expert

---

## Documentation Standards

**Confirmed.** All Phase documentation follows the Documentation Contract:

**Allowed in backtick blocks**: file paths, function signatures, enum values, formulas, constants.

**Forbidden in backtick blocks**: C++ function/method bodies, pointer operations, template code, class definitions, preprocessor chains, pseudocode mirroring code structure.

---

## Analysis Scope

Phases 1–6 are **system-wide** — they document the full architecture, all shared components, and all patterns. The first Phase 7 workflow will be chosen during Phase 6.3 sign-off after the candidate workflow inventory (Phase 6.2) is complete.
