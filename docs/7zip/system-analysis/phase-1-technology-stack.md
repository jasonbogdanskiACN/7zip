# Phase 1: Technology Stack

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Language and Standards

| Layer     | Language        | Standard / Notes                                              |
|-----------|-----------------|---------------------------------------------------------------|
| Core      | C               | C99; used for LZMA SDK, SHA, PPMd, threading abstraction      |
| Main app  | C++             | Pre-C++11 style; no STL containers (uses custom `CObjectVector`, `UString`, `AString`); no exceptions in hot paths |
| Assembly  | x86/x64 MASM    | Targeted for MSVC (`ml.exe` / `ml64.exe`)                     |
| Assembly  | ARM/ARM64 GAS   | `.S` files for Clang/GCC builds                               |

---

## Platform and Compiler Support

| Platform | Compiler               | Notes                                        |
|----------|------------------------|----------------------------------------------|
| Windows  | MSVC (2017/2019/2022)  | Primary; makefiles produce optimized binaries |
| Windows  | MSVC 6.0 (legacy)      | Supported via `OLD_COMPILER` flag             |
| Linux    | GCC                    | Via `var_gcc*.mak` makefiles                  |
| macOS    | Clang                  | Via `var_mac*.mak` and `warn_clang_mac.mak`   |
| ARM/ARM64| GCC / Clang            | Via `var_gcc_arm*.mak` / `var_clang_arm*.mak` |

Target platforms declared in the build system: x86, x64, arm, arm64, ia64.

---

## Key Internal Libraries (no external packages)

7-Zip has **no external third-party package dependencies**. All components are implemented in-tree.

| Component              | Location                   | Role                                                          |
|------------------------|----------------------------|---------------------------------------------------------------|
| LZMA SDK (C layer)     | `C/`                       | Reference LZMA/LZMA2/XZ decoder, 7z C reader, PPMd, SHA, Zstd |
| Custom string classes  | `CPP/Common/MyString.*`    | `UString` (wide char) and `AString` (narrow char) — no STL string |
| Custom containers      | `CPP/Common/MyVector.*`    | `CObjectVector<T>` and `CRecordVector<T>` — no STL vector  |
| COM-style interfaces   | `CPP/7zip/IStream.h`, `ICoder.h`, `IArchive.h` | Custom `IUnknown`-derived interfaces mimicking COM without the registry |
| Windows wrappers       | `CPP/Windows/`             | Thin C++ wrappers over Win32: file I/O, registry, threads, controls |
| Codec registration     | `CPP/7zip/Common/RegisterArc.h`, `RegisterCodec.h` | Static-init self-registration — each archive handler and codec registers itself via a `CRegisterArc` static object |

---

## UI Framework

| Component  | Framework                                   |
|------------|---------------------------------------------|
| `7zFM.exe` | Plain Win32 API — custom window class (`7-Zip::FM`), ListView, ToolBar, StatusBar, ReBar |
| `7zG.exe`  | Plain Win32 dialog boxes                    |
| `7z.exe`   | Console (no UI framework)                   |
| Shell ext  | Win32 COM shell extension (`IContextMenu`, `IShellExtInit`, etc.) |

No MFC, Qt, wxWidgets, or other UI toolkit used.

---

## Cryptographic Algorithms

| Algorithm            | Implementation source                       | Notes                                 |
|----------------------|---------------------------------------------|---------------------------------------|
| AES-256 CBC          | `CPP/7zip/Crypto/MyAes.*`, `C/Aes.*`        | Hardware-accelerated via AES-NI where available |
| ZipCrypto            | `CPP/7zip/Crypto/ZipCrypto.*`               | Legacy Zip encryption                 |
| WinZip AES (AE-1/2)  | `CPP/7zip/Crypto/WzAes.*`                   | AES + HMAC-SHA1 password auth         |
| RAR 2.0 crypto       | `CPP/7zip/Crypto/Rar20Crypto.*`             | —                                     |
| RAR 5 AES            | `CPP/7zip/Crypto/Rar5Aes.*`                 | AES-256 + PBKDF2                      |
| SHA-1                | `C/Sha1.c`, `Sha1Opt.c`; `CPP/Common/Sha1Reg.cpp` | Hardware-accelerated variant available |
| SHA-256              | `C/Sha256.c`, `Sha256Opt.c`                 | Hardware-accelerated variant available |
| SHA-512              | `C/Sha512.c`, `Sha512Opt.c`                 | —                                     |
| PBKDF2-HMAC-SHA1     | `CPP/7zip/Crypto/Pbkdf2HmacSha1.*`          | Used for WinZip AES key derivation    |

---

## Hash / Checksum Algorithms

CRC-32, CRC-64, SHA-1, SHA-256, SHA-512, SHA-3, MD-5, XXH-64, BLAKE2s — all in `C/` and registered via `CPP/Common/*Reg.cpp` files.

---

## Phase 1 Technology Stack Checklist

- [x] C++ standard and style documented
- [x] Platform and compiler matrix identified
- [x] Key internal libraries listed (no external dependencies confirmed)
- [x] UI framework identified (plain Win32)
- [x] Cryptographic and hash algorithm inventory produced
