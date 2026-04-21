# NovaWindows Driver — Framework Comparison Report

**Project**: 7-Zip File Manager (`7zFM.exe`)
**Skill**: `7zip-slice-verify-novawindows`
**NovaWindows Driver version**: 1.3.1 (npm: `appium-novawindows-driver`)
**Date run**: 2026-03-28
**Environment**: Windows 10, Appium 3.2.2, novawindows@1.3.1, Python 3.14.2, Appium-Python-Client 5.2.7

---

## Executive Summary

| Status | Count |
|--------|-------|
| Tests run | 3 |
| PASS | 3 |
| FAIL | 0 |
| Duration | ~1m 45s (WF01+WF02+WF03 sequential) |
| Issues reproduced from FlaUI | 3 (FUI-05, FUI-06, FUI-12) |
| New NovaWindows-specific issues | 7 (NW-1 through NW-7) |

All 3 vertical-slice workflows passed. See Issue table for the substantial setup effort required.

---

## Test Results

| Workflow | Result | Duration | Notes |
|----------|--------|----------|-------|
| WF01 Add to archive | ✅ PASS | ~48s | `[dialog] title='Add to Archive'`, 5 Edit controls found |
| WF02 Extract archive | ✅ PASS | ~38s | `[dialog] title='Extract : ...test-archive.zip'`, 3 Edit controls |
| WF03 Test archive | ✅ PASS | ~37s | `[result] text: 'There are no errors'` confirmed |

---

## Issue Reproduction Matrix

Comparison against the 14 FlaUI issues (`flaui-issues-log.md`) and 2 pywinauto issues.

### FlaUI Issues

| ID | Title | FlaUI | pywinauto | NovaWindows | Notes |
|----|-------|-------|-----------|-------------|-------|
| FUI-01 | `.sln` file not loading in VS | ✅ Resolved | N/A | N/A | Build-time only |
| FUI-02 | FlaUI NuGet version mismatch (UIA3 vs UIA2) | ✅ Resolved | N/A | N/A | Build-time only |
| FUI-03 | `Application.Launch()` vs `Application.Attach()` | ✅ Resolved | N/A | N/A | FlaUI-specific |
| FUI-04 | `WaitWhileBusy()` timeout on exe start | ✅ Resolved | N/A | ✅ Not applicable — `wait_for_appium()` pattern used |
| FUI-05 | **`Invoke()` deadlocks modal dialogs** | ⚠️ Hit (fixed: `click_input`) | ⚠️ Hit (fixed: `click_input()`) | ⚠️ Hit — `windows: click` SendInput also unusable in background session; fixed with `PostMessage WM_COMMAND` |
| FUI-06 | **UIA `FindAllChildren()` misses owned Win32 dialogs** | ⚠️ Hit (fixed: `Application.GetAllTopLevelWindows()`) | ✅ Avoided (`app.windows()`) | ⚠️ Hit — `driver.window_handles` uses UIA Children, misses dialogs; fixed: `ctypes EnumWindows` + `setWindow` SUBTREE patch |
| FUI-07 | `AutomationElement.IsOffscreen` unreliable | ℹ️ Observed | N/A | ✅ Not encountered |
| FUI-08 | FlaUI `TogglePattern.Toggle()` needed for checkboxes | ℹ️ Noted | ✅ Handled natively | ✅ Not tested (not needed for WF01-03) |
| FUI-09 | FlaUI `GridItem.Row/Column` 0-indexed | ℹ️ Noted | ✅ Not applicable | ✅ Not applicable |
| FUI-10 | `System.IO.IOException` on shared trace log read | ⚠️ Hit (fixed: FileShare.ReadWrite) | ✅ Avoided (Python `open()`) | ✅ Safe: Python `open()` |
| FUI-11 | Progress dialog appear/disappear race | ⚠️ Hit (fixed: sleep + retry) | ✅ Handled | ✅ Not encountered (dialogs stable) |
| FUI-12 | Orphaned `7zFM.exe` processes across test runs | ⚠️ Hit | ⚠️ Hit | ⚠️ Hit — fixed: `driver.quit()` + `kill_app()` in teardown |
| FUI-13 | `ConditionFactory.ByName()` case-sensitive | ℹ️ FlaUI-only | N/A | N/A |
| FUI-14 | FlaUI `Keyboard.TypeText()` locale-dependent | ⚠️ Noted | ✅ `type_keys` sends raw chars | ⚠️ `send_keys` uses `SendWait` which fails with "Access is denied" from background PS; fixed: UIA `ValuePattern.SetValue` |

### pywinauto Issues

| ID | Title | pywinauto | NovaWindows | Notes |
|----|-------|-----------|-------------|-------|
| PW-1 | `Desktop.windows()` catches wrong hwnd during rapid window transition | ⚠️ Hit (worked around: `time.sleep`) | ✅ Avoided — `ctypes EnumWindows` with PID+visible filter is reliable |
| PW-2 | `DialogWrapper` has no `child_window()` method — must use `WindowWrapper` | ⚠️ Hit (fixed: cast to `WindowWrapper`) | N/A — WebDriver has no wrapper class distinction |

---

## NovaWindows-Specific Issues Found

| ID | Issue | Fix Applied |
|----|-------|-------------|
| NW-1 | `start_appium.ps1`: `$driverList -notmatch` is array filter not bool | `Select-String` check |
| NW-2 | `start_appium.ps1`: can't redirect stdout + stderr to same file | Split to `appium.log` + `appium-err.log` |
| NW-3 | `start_appium.ps1`: `Start-Process -FilePath "appium"` fails for `.cmd` | Wrap with `cmd.exe /c appium` |
| NW-4 | `start_appium.ps1`: `--allow-insecure power_shell` invalid in Appium 3.x | Use `--allow-insecure novawindows:power_shell` |
| NW-5 | User PS profile (posh-git) crashes driver PS session | Added `-NoProfile` to `powershell.js` `spawn` calls |
| NW-6 | `driver.window_handles` uses UIA `FindAll(Children)` — misses 7-Zip owned Win32 dialogs (= FUI-06) | Patched `app.js:98` `setWindow` to `TreeScope.SUBTREE`; dialog detection via `ctypes EnumWindows` |
| NW-7 | `send_keys(path)` uses `SendWait` which throws "Access is denied" from background PS | Set address bar via `UIA ValuePattern.SetValue` via `execute_script("powerShell", ...)` |
| NW-8 | Session creation fails: `element.SetFocus()` throws "Target element cannot receive focus" when calling process lacks foreground permission | Patched `app.js` `attachToApplicationWindow` to swallow `focusElement` error — window IS present, focus failure is non-fatal |
| NW-9 | Keyboard simulation (`SendInput` / `windows: keys`) doesn't reach 7-Zip when window is not foreground: Ctrl+A, toolbar clicks | Replace toolbar clicks with `PostMessage WM_COMMAND`; replace Ctrl+A with `UIA SelectionItemPattern.AddToSelection()` |
| NW-10 | `getScreenshot` fails with "CopyFromScreen: handle is invalid" when screen is not active | Non-fatal — wrapped in try/except in `take_screenshot()` |

---

## Session Configuration

```python
opts = WindowsOptions()
opts.app             = "<exe_path>"
opts.automation_name = "NovaWindows"
opts.platform_name   = "Windows"
```

**Appium server start**:
```powershell
.\scripts\start_appium.ps1 -Background -Port 4723
# starts with: --allow-insecure power_shell
```

---

## Developer Experience Notes

### Setup Complexity

| Aspect | FlaUI | pywinauto | NovaWindows |
|--------|-------|-----------|-------------|
| Language | C# / .NET | Python | Python (Appium WebDriver) |
| Dependencies | NuGet (FlaUI.Core, FlaUI.UIA3) | pip (pywinauto) | Node.js + Appium + npm driver + pip Appium-Python-Client |
| Server needed | No | No | Yes (Appium on port 4723) |
| Session model | In-process | In-process | HTTP/WebDriver (out-of-process) |
| Dialog detection | `.GetAllTopLevelWindows()` | `.windows()` | `ctypes EnumWindows` + `setWindow` SUBTREE patch |
| Toolbar click | `button.Click()` mouse simulation | `button.click_input()` | `PostMessage WM_COMMAND(ID)` (SendInput fails in background) |
| Address bar set | `textbox.Enter(path)` | `set_edit_text(path)` | `UIA ValuePattern.SetValue` via `execute_script("powerShell", ...)` |
| Select all | `Keyboard.TypeSimultaneously(ctrl+A)` | `listview.type_keys("^a")` | `SelectionItemPattern.AddToSelection()` per item |
| Driver patches needed | 0 | 0 | 3 patches to `app.js` + `powershell.js` |

### Strengths

- **Standard Python/WebDriver model**: same `find_element`, `execute_script` API familiar to web automation engineers
- **PowerShell execute_script**: direct access to .NET UIA APIs enables operations not exposed in the WebDriver protocol (e.g., `ValuePattern.SetValue`, `PostMessage`)
- **Cross-platform skill**: knowledge transfers to other Appium-based Windows automation

### Weaknesses / Friction Points

- **High setup overhead**: requires Appium server, Node.js, driver installation — 4x more steps than FlaUI or pywinauto for initial setup
- **Driver requires patching**: 3 driver source-file patches needed just to get session creation and dialog detection working; any `npm update` wipes all patches
- **Background process restrictions**: `SendInput`, `SetForegroundWindow`, `GetScreenshot` all fail when the calling process can't reach the interactive desktop — requires workarounds for every simulated user action
- **`add_type` in per-test PS session**: `Add-Type -MemberDefinition` compiles C# JIT every session; minor overhead but reliable
- **`send_keys` is unusable**: `[Windows.Forms.SendKeys]::SendWait` fails with "Access is denied" from the hidden PS session for all text input

---

## Conclusion

NovaWindows/Appium successfully drives the same 3 vertical-slice workflows as FlaUI (C#) and pywinauto. The WebDriver abstraction is portable, but the Windows-specific restrictions (foreground keyboard/mouse, GDI screenshot) create a higher friction level than the other two frameworks for a Win32 desktop app like 7-Zip.

**Recommendation**: NovaWindows is suitable when a standard Appium/WebDriver infrastructure is already in place (e.g., Selenium Grid for Windows). For greenfield Win32 desktop automation, pywinauto (Python) or FlaUI (C#) require significantly less effort.

---

## References

- FlaUI issues log: `.github/skills/7zip-slice-verify/references/flaui-issues-log.md`
- pywinauto comparison: `.github/skills/7zip-slice-verify-pywinauto/references/comparison-report.md`
- NovaWindows patterns: `.github/skills/7zip-slice-verify-novawindows/references/novawindows-patterns.md`
- NovaWindows Driver repo: https://github.com/AutomateThePlanet/appium-novawindows-driver
