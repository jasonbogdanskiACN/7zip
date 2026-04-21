# Phase 3.4: Calculation Engine Analysis

**Status**: ✅ Complete (primary codec documented; supporting codecs listed)
**Date**: 2026-03-26

---

## Primary Calculation Engine: LZMA Encoder

**Type**: Custom C implementation
**Location**: `C/LzmaEnc.c`, `C/LzmaEnc.h`
**C++ wrapper**: `CPP/7zip/Compress/LzmaEncoder.h`, `LzmaEncoder.cpp`
**Documentation**: ✅ Available — in-source header comments and `DOC/lzma.txt`

**Purpose**: The LZMA (Lempel–Ziv–Markov chain Algorithm) encoder compresses an input byte stream by finding repeated patterns using a variable-length dictionary and encoding match references using range coding (an entropy coding method). It is the primary algorithm used by the 7z format at levels 3–9.

---

### Algorithm (plain English)

1. **Initialization**: The encoder allocates two main memory regions: the dictionary buffer (size = `dictSize` bytes) and the match-finder data structures (either a hash chain or binary tree, controlled by `btMode`).

2. **Match finding**: For each input position, the match finder searches the dictionary for the longest sequence of bytes that matches the bytes at the current position. The search depth is controlled by the fast-bytes parameter (`fb`) and the maximum match count (`mc`). In binary-tree mode (`btMode = 1`), the search uses a balanced binary tree per hash bucket, finding longer matches at higher CPU cost. In hash-chain mode (`btMode = 0`), the search is faster but finds shorter matches.

3. **Literal / match decision**: For each input symbol, the encoder chooses between encoding a literal byte (sending the byte through the range coder with context-based probabilities) and encoding a match reference (distance, length pair). The choice is governed by the probability model state (`lc` context bits from previous literal, `lp` low bits of current position, `pb` low bits of current position for the position state).

4. **Range coding**: The selected symbol (literal or match) is entropy coded using range coding. The probability model is adaptive — probabilities for all symbols are stored in a table and updated after each symbol is encoded.

5. **End-of-stream marker**: If `writeEndMark` is set, a special end-of-payload marker token is written after all input is processed. Otherwise, the decoder relies on the known uncompressed size stored in the archive metadata.

6. **Output**: Compressed bytes are written to the output stream via the `ISeqOutStream` callback.

---

### LZMA Encoder Parameters

All parameters are set via `LzmaEnc_SetProps()` / `ICompressSetCoderProperties` before encoding begins.

| Parameter | Range | Default | Description |
|---|---|---|---|
| `level` | 0–9 | — | Convenience preset; 0 = Store, 1 = Fastest … 9 = Ultra. Sets other parameters implicitly when not overridden individually. |
| `dictSize` | 4096 – 16 GB (64-bit) | 16 MB (1 << 24) | Dictionary buffer size in bytes. Larger values improve compression on large files at higher RAM cost. Source: `C/LzmaEnc.h` |
| `lc` | 0–8 | 3 | Number of high bits of the previous literal byte used as context for literal coding. |
| `lp` | 0–4 | 0 | Number of low bits of the current position used as context for literal coding. |
| `pb` | 0–4 | 2 | Number of low bits of the current position used as context for match/literal decision and match length coding. |
| `algo` | 0 or 1 | 1 | Compression algorithm: 0 = fast (hash chain), 1 = normal (binary tree). Overrides `btMode`. |
| `fb` | 5–273 | 32 | Maximum number of fast bytes; controls the minimum match length the encoder prefers. |
| `btMode` | 0 or 1 | 1 | Match finder mode: 0 = hash chain, 1 = binary tree. |
| `numHashBytes` | 2, 3, or 4 | 4 | Number of bytes used to compute the initial hash key for the match finder. |
| `mc` | 1 – 2^30 | 32 | Maximum number of match candidates the match finder examines per position. |
| `numThreads` | 1 or 2 | 2 | Thread count. When 2, the match finder runs on a second thread. |
| `reduceSize` | any | (Int64)-1 = unset | Estimated input size. When set, allows the encoder to reduce the dictionary to the input size, saving memory. |
| `writeEndMark` | 0 or 1 | 0 | Whether to write an end-of-payload marker at the end of the stream. |

**Parameter constraint**: `lc + lp` must be ≤ 4 [VERIFIED: 2026-03-26 — enforced in `LzmaEncProps_Normalize()`].

Source: `C/LzmaEnc.h:12-38`

---

### Convergence / Termination

LZMA is a single-pass encoder — it terminates when all input bytes have been processed. There is no iterative convergence step.

- **Dictionary underrun**: If the input is smaller than `dictSize`, the encoder uses only as much dictionary as needed.
- **Match finder exhaustion**: The match finder is bounded by `mc` (maximum candidate count) and `fb` (fast-bytes threshold).
- **Thread failure**: If multithreading fails initialization, `LzmaEnc_Encode()` returns `SZ_ERROR_THREAD`.

---

### Result / Output

The encoder produces two outputs:
1. **Properties blob** (5 bytes) — written by `LzmaEnc_WriteProperties()`. Contains `lc`, `lp`, `pb` packed in byte 0, and `dictSize` in bytes 1–4 (little-endian 32-bit). This blob is stored in the archive header and must be passed to the decoder.
2. **Compressed byte stream** — written to the output stream. The compressed size is not known in advance.

Source: `C/LzmaEnc.h:52-55`; `DOC/lzma.txt`

---

### Dependencies

| Dependency | Type | Access |
|---|---|---|
| `C/Alloc.c` | Memory allocator (custom) | ✅ Available |
| `C/LzFind.c`, `LzFindMt.c` | Match finder (single- and multi-threaded) | ✅ Available |
| `C/Threads.c` | Threading abstraction | ✅ Available |
| Platform C runtime (malloc/free) | Memory allocation | ✅ Available |

No external libraries required.

---

## Supporting Codecs

| Codec | Location | Type | Usage |
|---|---|---|---|
| LZMA2 | `CPP/7zip/Compress/Lzma2Encoder.*` | Wraps LZMA with independent-segment multi-threaded encoding | Default for 7z format |
| Deflate | `CPP/7zip/Compress/DeflateEncoder.*` | LZ77 + Huffman | ZIP, GZip formats |
| BZip2 | `CPP/7zip/Compress/BZip2Encoder.*` | Burrows–Wheeler + Huffman | .bz2, .tar.bz2 |
| PPMd | `CPP/7zip/Compress/PpmdEncoder.*` | Prediction by partial matching (PPMd variant H) | 7z optional, ZIP optional |
| Zstd | `C/ZstdDec.c` (decode only) | Zstandard | Read-only; decompression only in this version |
| BCJ filters | `CPP/7zip/Compress/BcjCoder.*`, `Bcj2Coder.*` | Branch/call/jump converter for x86, x64, ARM, IA64, PPC, SPARC | Pre-filter before LZMA to improve compression of executable code |
| AES-256 | `CPP/7zip/Crypto/MyAes.*`, `C/Aes.c` | AES-256 CBC encryption | 7z encryption, ZIP/WinZip AES, RAR5 |

**LZMA2 vs LZMA** (the key distinction for Phase 7 workflow selection):
LZMA2 encodes each "chunk" of input independently, which enables multi-threaded encoding (each thread encodes a separate chunk). It falls back to incompressible (literal pass-through) mode when compression does not help. The stored properties are a superset of LZMA properties; the decoder always reconstructs each chunk with its own dictionary state. LZMA2 is the default method for new 7z archives since version 9.x.

---

## Phase 3.4 Calculation Engine Checklist

- [x] LZMA encoder identified as the primary calculation engine
- [x] Algorithm documented as a numbered plain English sequence
- [x] All parameters extracted with names, ranges, defaults, and descriptions
- [x] Parameter source verified in code (`C/LzmaEnc.h`)
- [x] No external library dependencies — fully self-contained [VERIFIED: 2026-03-26]
- [x] Supporting codecs listed with locations and usage contexts
- [x] LZMA2 vs LZMA distinction documented (key for Phase 7)
