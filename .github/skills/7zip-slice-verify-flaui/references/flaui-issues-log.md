# FlaUI Automation Issues Log — 7-Zip Vertical Slice Testing

**Project**: 7-Zip 26.00 (Win32/MFC, nmake build, MSVC)  
**Framework**: FlaUI v5.0.0 (UIA2 backend), xUnit 2.x, .NET 8.0, C#  
**Date range**: March 2026  
**Outcome**: All 3 tests eventually passing after iterative debugging

---

## Issue 1 — ProbeApp XML comment caused build failure

**Symptom**: `dotnet build` failed with "The ':' character, hexadecimal value 0x3A, cannot be included in a name."  
**Root cause**: An XML comment inside `ProbeApp.csproj` contained `--uia3)` which is illegal in XML (double-dash in comments).  
**Fix**: Changed `--uia3)` to `-uia3)` in the comment text.  
**Lesson**: XML comment content cannot contain `--`. Even documentation strings inside `.csproj` need to be XML-safe.

---

## Issue 2 — Wrong TargetFramework for FlaUI (net8.0 vs net8.0-windows)

**Symptom**: Build succeeded but runtime `DllNotFoundException` for `UIAutomationClient`.  
**Root cause**: The `.csproj` used `<TargetFramework>net8.0</TargetFramework>`. FlaUI calls `UIAutomationClient` COM interop which requires the Windows TFM.  
**Fix**: Changed to `<TargetFramework>net8.0-windows</TargetFramework>` in both `ProbeApp.csproj` and the test project template.  
**Lesson**: Any .NET library that wraps Win32/COM (FlaUI, WinForms, PInvoke) requires the `-windows` TFM suffix.

---

## Issue 3 — Keyboard.Down/Up API does not exist in FlaUI v5

**Symptom**: Compile error `'Keyboard' does not contain a definition for 'Down'`.  
**Root cause**: Generated test code assumed `FlaUI.Core.Input.Keyboard.Down(VirtualKeyShort.CONTROL)` but FlaUI v5 API uses `Keyboard.Press()` for single keys and `Keyboard.TypeSimultaneously()` for key combos.  
**Fix**: Replaced with `Keyboard.TypeSimultaneously(VirtualKeyShort.CTRL, VirtualKeyShort.KEY_A)`.  
**Lesson**: FlaUI v5 keyboard API is different from v4. Read the FlaUI changelog before writing input code. Also, Ctrl+A on a Win32 SysListView32 did not work at all — had to use UIA DataItem click instead.

---

## Issue 4 — Test parallelism sent keyboard/mouse events to wrong windows

**Symptom**: All three xUnit tests ran simultaneously and sent keyboard input to whatever window was focused — not the intended 7zFM window.  
**Root cause**: xUnit v2 parallelizes tests across classes by default.  
**Fix**: Added `DisableParallelization.cs`:
```csharp
[assembly: CollectionBehavior(DisableTestParallelization = true)]
```
**Lesson**: GUI automation tests must always run serially. Add anti-parallelization assembly attribute from day one.

---

## Issue 5 — UIA `element.Invoke()` deadlocks with modal dialogs

**Symptom**: `addBtn.Invoke()` on the toolbar Add button hung the test for 30+ seconds, then threw a COM timeout. The dialog sometimes appeared but UIA couldn't reach it.  
**Root cause**: FlaUI's `Invoke()` sends a UIA `WM_COMMAND` via COM cross-process `SendMessage`. When the button handler calls `DoModal()` (Win32 modal dialog loop), `SendMessage` blocks until the dialog closes — deadlock.  
**Fix**: Use `FlaUI.Core.Input.Mouse.Click(element.GetClickablePoint())` which sends a Windows `SendInput` message (non-blocking). The mouse click dispatches through the message queue without waiting for a reply.  
**Lesson**: Never use `element.Invoke()` for buttons that open modal dialogs. Always use `Mouse.Click()` for GUI triggers in Win32/MFC apps.

---

## Issue 6 — `GetDesktop().FindAllChildren()` misses owned modal dialogs

**Symptom**: After clicking Extract, the UIA desktop search loop timed out without finding the "Extract" dialog, even though the dialog was visually open.  
**Root cause**: Win32 modal dialogs created with `DoModal()` are owned windows (set `WS_EX_NOACTIVATE` style). `GetDesktop().FindAllChildren()` and `App.GetAllTopLevelWindows()` do not enumerate owned dialog windows — they only see root-level top-level windows.  
**Fix**: Created `Win32WindowFinder.cs` — a P/Invoke wrapper around `EnumWindows` + `GetWindowThreadProcessId`. `EnumWindows` is an OS-level call that sees ALL top-level windows including owned dialogs. Polled until a new HWND appeared for the process PID.  
**Lesson**: For Win32/MFC apps, use OS-level `EnumWindows` for dialog detection. UIA tree-walking misses owned windows registered with `CreateDialog`/`DoModal`.

---

## Issue 7 — `MY_CFLAGS` parameter silently ignored by nmake

**Symptom**: `build-traced.ps1` passed `MY_CFLAGS="/DZ7_TRACE_ENABLE"` to nmake, but binary search on the output exe found "WF-EXTRACT" **not present** — confirming the define was never compiled in.  
**Root cause**: The 7-Zip nmake `Build.mak` had no reference to `$(MY_CFLAGS)` anywhere in its CFLAGS construction chain. nmake silently ignores variables that aren't referenced in any makefile rule.  
**Fix**: Added to `CPP/Build.mak` immediately before `CFLAGS_O1`/`CFLAGS_O2` are derived:
```makefile
!IFDEF MY_CFLAGS
CFLAGS = $(CFLAGS) $(MY_CFLAGS)
!ENDIF
```
**Lesson**: nmake does not warn about unused command-line variables. Always verify a define was actually compiled in by binary-searching the output exe for a unique string that the define enables.

---

## Issue 8 — `fopen` deprecated; `/DZ7_TRACE_LOGFILE="path"` quote stripping

**Symptom**: Build failed with `C4996: 'fopen': This function or variable may be unsafe` (promoted to error by `-WX`).  
**Secondary symptom**: Passing the log path as `/DZ7_TRACE_LOGFILE="C:\\Temp\\7z_trace.log"` through `cmd.exe` batch → nmake → cl.exe caused the outer quotes to be stripped, resulting in parse errors in `Z7Trace.h` at line 35 (`error C2065: 'C': undeclared identifier`).  
**Fix**: (a) Changed `fopen()` to `_fsopen(..., _SH_DENYNO)` (safe, and allows shared read). (b) Abandoned passing the log path as a `/D` define through the command line. Instead hardcoded `C:\Temp\7z_trace.log` as a default value directly in `Z7Trace.h` using `#ifndef Z7_TRACE_LOGFILE`.  
**Lesson**: Never try to pass Windows path strings (backslashes, quotes) through the `cmd.exe` → nmake → cl `/D` define pipeline. Nested quote escaping is fragile across shells. Use `#ifndef` defaults in the header instead.

---

## Issue 9 — PCH mismatch after adding new compile-time defines

**Symptom**: After adding `Z7_TRACE_ENABLE` to `MY_CFLAGS` and deleting `a.pch`, other source files compiled with `/Yu"StdAfx.h"` failed: `C4605: '/DZ7_TRACE_ENABLE' was not specified when precompiled header was built`.  
**Root cause**: nmake compiled the `.cpp` files that were freshly `touch`-ed (to force recompile) BEFORE `StdAfx.cpp` (which creates the PCH). The touched files used `/Yu` (use PCH) and the stale PCH didn't have the new define.  
**Fix**: Explicitly delete `StdAfx.obj` in addition to `a.pch`. This forces nmake to rebuild `StdAfx.cpp` first (since it's the PCH creation target `/Yc`) before any `/Yu` consumers.  
**Lesson**: When adding a new compile-time define to a PCH-based MSVC project, always delete BOTH the `.pch` file AND `StdAfx.obj`. Deleting only the `.pch` is insufficient.

---

## Issue 10 — Trace log `IOException` while app holds file open

**Symptom**: `ReadTrace()` in `FlaUITestBase` threw `System.IO.IOException: The process cannot access the file 'C:\Temp\7z_trace.log' because it is being used by another process.`  
**Root cause**: `Z7Trace.h` holds a `static FILE*` open for the entire lifetime of the 7zFM process (append mode). C#'s `File.ReadAllLines()` opens with exclusive access by default.  
**Fix (C++ side)**: Changed from `fopen_s()` to `_fsopen(..., "a", _SH_DENYNO)` — the `_SH_DENYNO` share mode allows other processes to read the file while 7zFM has it open for writing.  
**Fix (C# side)**: Changed `ReadTrace()` to use `new FileStream(..., FileAccess.Read, FileShare.ReadWrite)` so the reader explicitly allows the writer to keep the file open.  
**Lesson**: When a long-lived process keeps a log file open, both the writer (C++) must use `_SH_DENYNO` and the reader (C#) must use `FileShare.ReadWrite`. Either fix alone is insufficient.

---

## Issue 11 — `App.GetMainWindow()` returned wrong/stale window

**Symptom**: `Window` captured a tiny element titled "Test" or an empty-titled element. Screen­shots showed a 20×15 pixel fragment. `addrEdit` (AutomationId "1003") was always null because the wrong element was captured.  
**Root cause**: `Application.GetMainWindow()` in FlaUI uses `Process.MainWindowHandle` which can race — especially after the previous test killed a process, `Process.MainWindowHandle` may return a handle from the Windows shell or a transient initialization window before the app's `SetWindowText()` call fires.  
**Fix**: Replaced `App.GetMainWindow()` with a polling loop that calls `Win32WindowFinder.SnapshotProcessWindows(App.ProcessId)` and picks the first window belonging to the new PID that has a non-empty `GetWindowTitle()`.  
**Lesson**: Do not rely on `App.GetMainWindow()` for Win32 apps that remember their last directory in the title bar — the title is never just "AppName" and the handle race is real. Use PID-filtered `EnumWindows` with a non-empty title check.

---

## Issue 12 — Orphaned 7zFM processes contaminated subsequent tests

**Symptom**: When a test failed mid-way (e.g. while the Extract dialog was open), `App.Close()` in `Dispose()` failed silently. The next test's `Application.Launch()` started a new process, but `Win32WindowFinder.WaitForNewWindow()` with an empty exclusion set returned the HWND from the still-running orphaned process.  
**Fix**: Added kill-before-launch in `FlaUITestBase` constructor: enumerate `Process.GetProcessesByName(exeName)`, kill all, wait 800ms for OS to release handles. Also added force-kill in `Dispose()`: if `App.HasExited` is false after `App.Close()`, call `App.Kill()`.  
**Secondary fix**: Create the `AutomationBase` (UIA2Automation) **after** the kill, not before — COM state from a killed process can be cached in the Automation object.  
**Lesson**: GUI test infrastructure must kill orphans at setup. Never assume `Dispose()` cleaned up successfully — always kill by process name at the start of the next test.

---

## Issue 13 — `Window.Focus()` deselected the archive before toolbar click

**Symptom**: WF02 (Extract) failed with "You must select one or more files" dialog. Screenshot showed the error. The archive item had been clicked and selected, but Extract launched with nothing selected.  
**Root cause**: After `archiveItem.Click()`, the code called `Window.Focus()` before `Mouse.Click(extractBtn)`. `Window.Focus()` sends a Win32 `SetForegroundWindow` which internally redirected keyboard focus to the window frame, deselecting the SysListView32 item.  
**Fix**: Removed the redundant `Window.Focus()` call immediately before clicking toolbar buttons. `Window.Focus()` is already called once before `archiveItem.Click()` — that is sufficient.  
**Lesson**: Do not call `Window.Focus()` between selecting an item and clicking a toolbar button. Focus change in Win32 SysListView32 can deselect items.

---

## Issue 14 — `testMode=true` trace not emitted for Test button path

**Symptom**: WF03 passed all UI assertions but failed on `AssertTrace("testMode=true")`. The trace log contained "WF-TEST triggered" but no testMode line.  
**Root cause**: The `Z7TRACE("testMode=true -> null-sink")` was inside the `case NArchive::NExtract::NAskMode::kExtract: if (_testMode)` block. When the toolbar Test button is used, 7-Zip passes `askExtractMode = kTest` directly — the `kExtract` branch is never entered.  
**Fix**: Added a new trace to the `kTest` case: `Z7TRACE("GetStream[%u] kTest mode -> null-sink CRC check", index)`.  
**Lesson**: Trace a code path by examining what value is actually passed to the function, not by assuming the "test mode" flag is set inside a different branch.

---

## Summary Statistics

| Category | Count |
|---|---|
| Build/toolchain issues | 4 (Issues 1, 2, 7, 8, 9) |
| FlaUI API misuse | 3 (Issues 3, 5, 11) |
| Win32/MFC-specific UIA gaps | 2 (Issues 6, 13) |
| Test isolation / cleanup | 2 (Issues 4, 12) |
| Trace/instrumentation | 2 (Issues 10, 14) |
| **Total** | **14** |

---

## Time to First Passing Test

- WF02 first partial pass (dialog found, no trace): ~6 debug iterations over one session  
- WF01, WF02, WF03 all passing with trace: ~12 total debug iterations  
- Dominant time sinks: Issue 7 (MY_CFLAGS silent failure), Issue 6 (UIA modal dialog gap), Issue 12 (orphan contamination)
