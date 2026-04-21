# Framework Comparison Report: FlaUI (C#) vs pywinauto (Python)

> **Status**: Complete — pywinauto WF01/WF02/WF03 all PASS (2026-03-27).

## Purpose

This document compares the development experience and runtime behaviour of two GUI automation toolchains applied to the same 7-Zip vertical slice workflows:

| | FlaUI | pywinauto |
|---|---|---|
| Language | C# | Python |
| Backend | UIA (Microsoft UI Automation COM) | `win32` (EnumWindows / SendMessage) |
| Test runner | xUnit | pytest |
| Status | ✅ WF01/WF02/WF03 all PASS | ✅ WF01/WF02/WF03 all PASS |
| Total run time (3 tests) | ~36 s | ~24 s |
| Iterations to first green | WF01: 9 iterations; WF02: 3; WF03: 2 | WF01: 4 iterations; WF02: 1; WF03: 1 |

Reference: [flaui-issues-log.md](../../../7zip-slice-verify/references/flaui-issues-log.md) (14 issues documented during FlaUI development).

---

## Issue-by-Issue Comparison

| # | FlaUI Issue | pywinauto Status | Notes |
|---|---|---|---|
| 1 | XML comment `--` breaks .csproj | ✅ N/A — Python, no .csproj | Toolchain-specific; pywinauto has no project file |
| 2 | `net8.0` → `net8.0-windows` TFM | ✅ N/A — Python, no TFM | Toolchain-specific |
| 3 | `Keyboard.Down/Up` absent in FlaUI v5 | ✅ Avoided — `type_keys("{VK_DOWN}")` works | pywinauto keyboard API is stable and complete |
| 4 | xUnit parallelism sends keys to wrong window | ✅ Avoided — pytest runs sequentially by default | No `DisableParallelization` attribute needed |
| 5 | `Invoke()` deadlocks modal dialogs | ⚠️ Same risk, different name — `click()` uses WM_COMMAND | Mitigated by using `click_input()` (SendInput) throughout |
| 6 | `GetDesktop().FindAllChildren()` misses owned dialogs | ✅ Avoided — `app.windows()` uses in-process enumeration | All 3 dialogs found immediately; no P/Invoke workaround required |
| 7 | `MY_CFLAGS` silently ignored by nmake | ✅ N/A — same traced build used | Build system is toolchain-independent |
| 8 | `fopen` C4996 + log-path quote stripping | ✅ N/A — same traced build used | |
| 9 | PCH mismatch after adding defines | ✅ N/A — same traced build used | |
| 10 | `IOException` reading log while app holds it | ✅ Avoided — Python `open()` uses shared-read by default | No `FileShare.ReadWrite` workaround needed |
| 11 | `GetMainWindow()` returns stale/small window | ✅ Avoided — `app.top_window()` works reliably | No PID-filtered retry loop required |
| 12 | Orphaned processes contaminate next test | ⚠️ Same risk — mitigated by `kill_app()` in `teardown_method` | Same pattern as FlaUI; required same belt-and-suspenders fix |
| 13 | `Window.Focus()` deselects ListView item | ✅ Not encountered — `lv.set_focus()` + `lv.type_keys("^a")` worked | pywinauto focus semantics different from UIA `Focus()` |
| 14 | `kTest` trace path missing | ✅ N/A — same traced build used | |

**New pywinauto-specific issues encountered**:

| # | Issue | Symptom | Fix |
|---|---|---|---|
| PW-1 | `Desktop(backend="win32").windows()` catches main-window hwnd after navigation | `wait_for_new_window()` detected the 7-Zip FM main window (new hwnd after dir change) instead of the Add dialog | Switched to `app.windows()` (in-process) filtered to exclude main window hwnd |
| PW-2 | `DialogWrapper` returned from `app.windows()` has no `child_window()` | `AttributeError: 'DialogWrapper' object has no attribute 'child_window'` | Re-wrap via `app.window(handle=dlg_wrapper.handle)` which returns a `WindowSpecification` |

---

## Summary Statistics

| Category | FlaUI issues | Same in pywinauto | Avoided by pywinauto | New in pywinauto |
|---|---|---|---|---|
| Build / toolchain | 4 | 0 | 4 (N/A) | 0 |
| FlaUI API misuse | 3 | 1 (#5 click deadlock risk) | 2 (#3 keyboard, #11 main window) | 2 (PW-1, PW-2) |
| Win32 / UIA gaps | 2 | 0 | 2 (#6 dialog enum, #13 focus deselect) | 0 |
| Test isolation | 2 | 1 (#12 orphan processes) | 1 (#4 xUnit parallelism) | 0 |
| Trace / instrumentation | 2 | 0 | 2 (N/A, same build) | 0 |
| **Total** | **13** | **2** | **9** | **2** |

---

## Developer Experience Notes

| Dimension | FlaUI | pywinauto |
|---|---|---|
| Setup time | Moderate — .csproj, NuGet, TFM quirks, 2 build errors before first run | Fast — `pip install pywinauto Pillow pytest` (< 30 s) |
| API discoverability | C# IntelliSense + strong types; mismatched FlaUI v5 API caused 2 extra iterations | Python REPL probing; method errors clear but no IntelliSense |
| Modal dialog handling | Required P/Invoke `EnumWindows` workaround (+ 2 days debugging) | `app.windows()` (in-process) found all dialogs immediately |
| Log file access | Required `FileShare.ReadWrite` workaround | Python `open()` shared-read by default — just works |
| Custom wrapper split | `HwndWrapper` vs `WindowSpecification` — separate concepts causing PW-2 | Had to re-wrap via `app.window(handle=…)` after `app.windows()` |
| Error messages | Verbose .NET stack traces; COM-level errors hard to read | Concise Python tracebacks; AttributeError messages pinpoint problem |
| Test execution speed | ~36 s for 3 tests (launch + UIA COM warmup) | ~24 s for 3 tests (faster win32 API, no COM marshaling) |
| Iterations to first green | 14 total (WF01: 9, WF02: 3, WF03: 2) | 6 total (WF01: 4, WF02: 1, WF03: 1) |

---

## Conclusion

**pywinauto (Python/win32) is the better first-choice toolchain for classic Win32/MFC applications** like 7-Zip:

1. **Setup is trivial** — one `pip install` line vs a .csproj with two non-obvious fixups.
2. **Modal dialog detection just works** — `app.windows()` stays in-process and finds all owned windows without any P/Invoke bypass.
3. **Fewer iterations to first green** — 6 vs 14; the `win32` backend's simpler API surface produced fewer surprises.
4. **Faster tests** — 24 s vs 36 s for the same 3 workflows (win32 API vs UIA COM).
5. **Trace log reading is simpler** — Python's default `open()` already uses shared-read; no `FileShare.ReadWrite` workaround needed.

**FlaUI remains valuable when**:
- You need UIA automation properties (AutomationId, ControlType) for WPF/WinUI apps where `win32` is insufficient.
- Your team is primarily C# and cannot add a Python dependency.
- You need the stronger type safety of a compiled language to catch API errors at build time.

**Recommendation**: Use pywinauto as the primary toolchain for 7-Zip FM automation. Keep the FlaUI suite as a secondary validation pass for UIA-specific properties (if needed in future).

