# Phase 3: Validation Logic

**Status**: ✅ Complete
**Date**: 2026-03-26

---

## Overview

Validation in 7-Zip occurs at two distinct layers: the GUI dialog layer (immediate user-facing feedback before the operation starts) and the archive-handler layer (deep validation during decompression, such as CRC checks).

---

## GUI Layer Validation — Compress Dialog

**Location**: `CPP/7zip/UI/GUI/CompressDialog.cpp`

These rules are enforced when the user clicks OK on the Compress dialog. The dialog does not close until all rules pass.

| Rule | Condition | Error Shown | Location |
|---|---|---|---|
| Archive path must be resolvable | `GetFinalPath_Smart()` returns false | `L"Incorrect archive path"` | `CompressDialog.cpp:884`, `CompressDialog.cpp:1129` |
| Volume size must be valid | The volume size string cannot be parsed | String resource `IDS_INCORRECT_VOLUME_SIZE` | `CompressDialog.cpp:1220` |
| Password must be ASCII only | Any character has code below 0x20 or above 0x7F | String resource `IDS_PASSWORD_USE_ASCII` | `CompressDialog.cpp:1073` |
| Password must not be too long | Password exceeds the format's maximum length | String resource `IDS_PASSWORD_TOO_LONG` | `CompressDialog.cpp:1081` |
| Passwords must match | The two password fields contain different text | String resource `IDS_PASSWORD_NOT_MATCH` | `CompressDialog.cpp:1092` |
| Memory usage must not exceed limit | Calculated encoder memory > RAM limit threshold | String resource `IDS_MEM_OPERATION_BLOCKED` with `IDS_MEM_REQUIRES_BIG_MEM`, size details, and RAM limit | `CompressDialog.cpp:1115` |

**Note**: The exact text for the string resource IDs (`IDS_PASSWORD_USE_ASCII`, `IDS_PASSWORD_NOT_MATCH`, etc.) is not available from source code analysis — they are stored in the language resource files (`.lng` files) which are not present in the source tree. [NOT AVAILABLE] — will require access to compiled resource strings or the 7-Zip language files.

---

## GUI Layer Validation — SFX Method Gate

**Location**: `CompressDialog.cpp — CheckSFXControlsEnable()`

When the user selects an archive format, the SFX checkbox is disabled and unchecked if:
- The selected format does not have the `kFF_SFX` capability flag, OR
- The selected compression method is not in the supported-by-SFX list (`g_7zSfxMethods`: Copy, LZMA, LZMA2, PPMd)

No error message is shown — the checkbox is simply disabled.

---

## Archive-Handler Layer Validation — CRC Integrity Check

**Location**: `CPP/7zip/UI/Common/ArchiveExtractCallback.cpp`

During extraction, for each decompressed item the archive handler compares the CRC-32 of the decompressed bytes against the CRC-32 value stored in the archive metadata. This check is always performed when the archive records a CRC.

The result is communicated back via `IArchiveExtractCallback::SetOperationResult()` with one of:
- `NExtract::NOperationResult::kOK` — data is intact
- `NExtract::NOperationResult::kDataError` — decompressed data does not match stored CRC
- `NExtract::NOperationResult::kCRCError` — explicit CRC mismatch reported by handler
- `NExtract::NOperationResult::kUnsupportedMethod` — the compression method is not available

The file is written to disk even when a CRC error occurs — the callback marks the result as an error in its status tracking. The caller sees a non-OK result code.

---

## Archive Open Validation — Password Request

**Location**: `CPP/7zip/UI/Common/OpenArchive.cpp`, `ArchiveOpenCallback.h`

When an archive's headers are encrypted (e.g., 7z with header encryption enabled), the handler cannot read item metadata without the password. The handler requests the password by calling `IArchiveOpenCallback::CryptoGetTextPassword()`. The callback either:
- Shows a GUI password dialog and returns the typed string, OR
- Returns the password already supplied via command-line (`-p` flag), OR
- Returns `E_ABORT` if the user cancels, causing the open operation to fail

---

## Codec Parameter Validation — Property Parsing

**Location**: `CPP/7zip/Common/MethodProps.cpp`

When compression method properties are parsed from string form (e.g., from the CLI `-m` flag or the compress dialog parameters field), the following validations are applied:

| Property | Validation | Error |
|---|---|---|
| Dictionary size suffix | Must be one of `b`, `k`, `m`, `g` or a bare number | Returns `E_INVALIDARG` |
| Dictionary log size | Must be 0–63 | Returns `E_INVALIDARG` |
| Thread count string | Must be a valid unsigned integer, optionally prefixed with `d`/`u` or `p`(percent) | Returns `E_INVALIDARG` |
| Boolean property | Must be `"on"`, `"off"`, `"true"`, `"false"`, or `VT_BOOL` | Returns `E_INVALIDARG` |
| Unsigned integer property | Must parse fully to an unsigned integer | Returns `E_INVALIDARG` |

Source: `CPP/7zip/Common/MethodProps.cpp`

---

## Phase 3 Validation Checklist

- [x] Compress dialog validation rules identified with error identifiers
- [x] SFX method gate rule documented
- [x] CRC integrity check during extraction documented
- [x] Password request during archive open documented
- [x] Codec property parsing validation documented
- [⚠️] Exact text for `IDS_PASSWORD_USE_ASCII`, `IDS_PASSWORD_NOT_MATCH`, `IDS_PASSWORD_TOO_LONG`, `IDS_INCORRECT_VOLUME_SIZE`, `IDS_MEM_OPERATION_BLOCKED` — [NOT AVAILABLE] — language files not in source tree
