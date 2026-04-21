# UX Findings — WF-01/02/03 (pywinauto run) — 2026-03-27

**Project**: 7-Zip 26.00  
**Framework**: pywinauto (win32 backend)  
**Screenshots**: `docs/7zip/automation-tests-pywinauto/screenshots/`  
**Workflows analysed**: WF-01 Add to Archive, WF-02 Extract from Archive, WF-03 Test Archive  
**Reference criteria**: [ux-analysis-criteria.md](../../.github/skills/7zip-slice-verify/references/ux-analysis-criteria.md)

---

## Score Summary

| Criterion | Score (1–5) | Notes |
|---|---|---|
| Visual Design > Typography | 3 | Functional but dated Win32 font stack; no hierarchy |
| Visual Design > Iconography | 3 | Color BMP icons — not crisp at 125% DPI |
| Visual Design > Spacing & density | 2 | Dialog rows tightly packed; no visual breathing room |
| Visual Design > Control style | 1 | Classic Win32 `BUTTON`/`ComboBox` — no Fluent styling |
| Visual Design > Dark mode | 1 | No dark mode support observed |
| Information Architecture > Toolbar | 5 | Add, Extract, Test clearly labelled with icons ✓ |
| Information Architecture > Dialog layout | 3 | Key setting (archive path) is at top; advanced settings clutter view |
| Information Architecture > Progressive disclosure | 2 | All settings visible at once; no collapsible sections |
| Information Architecture > Status communication | 4 | Status bar accurate; progress dialogs clear |
| Workflow Efficiency > Steps to complete | 4 | Launch → Add → dialog: 2 clicks ✓ |
| Workflow Efficiency > Defaults | 4 | 7z format, Normal compression, correct destination ✓ |
| Workflow Efficiency > Keyboard accessibility | 3 | Accelerators present but not always visible |
| Accessibility > Color contrast | 3 | White-on-light-grey text in result window needs checking |
| Accessibility > Resize behavior | 2 | Add dialog is fixed-size; does not resize |

---

## Findings

---

**Finding UX-01**: Classic Win32 control styling
- **Screen**: `wf01-add-to-archive/03-dialog-open.png`
- **Criterion**: Visual Design > Control style
- **Current state**: The Add to Archive dialog uses standard Win32 `#32770` dialog class with classic COMCTL32 buttons, combo boxes, and checkboxes. The visual appearance matches Windows XP / 7 era styling — beveled buttons, 3D border combo boxes.
- **Impact**: Every user on Windows 10/11. The app looks visibly outdated compared to native OS dialogs (File Explorer, Notepad, Paint). First-time users may perceive it as lower quality.
- **Recommendation**: Migrate the dialog to WTL with Fluent theming, or apply visual styles manifest (`comctl32.dll` v6 via `<dependency>` in .manifest) and add WM_CTLCOLORDLG handling for accent-aware backgrounds. Minimum viable: add `<trustInfo>` + `<dependency>` to the manifest to enable COMCTL32 v6 rendering on all dialogs.
- **Effort**: Low (manifest-only) → High (full WinUI 3 rewrite)
- **Category**: Visual Design

---

**Finding UX-02**: No dark mode support
- **Screen**: `probe/00-probe-idle.png`
- **Criterion**: Visual Design > Color system
- **Current state**: The application uses hardcoded `RGB(255,255,255)` background for all list views and dialogs; it does not check `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize\AppsUseLightTheme`. On a Windows 11 system configured to dark mode, the titlebar turns dark but the client area remains white, creating a jarring split.
- **Impact**: Users with dark mode enabled (a majority on modern Windows). Causes eye strain in low-light conditions.
- **Recommendation**: Handle `WM_SETTINGCHANGE` for `ImmersiveColorSet`; use `ShouldAppsUseDarkMode()` (uxtheme.dll ordinal 132) to select a dark color scheme; replace hardcoded `GetStockObject(WHITE_BRUSH)` with `GetSysColorBrush(COLOR_WINDOW)`.
- **Effort**: Medium
- **Category**: Visual Design

---

**Finding UX-03**: Add dialog not resizable; settings clutter primary path
- **Screen**: `wf01-add-to-archive/03-dialog-open.png`
- **Criterion**: Visual Design > Spacing & density; Information Architecture > Progressive disclosure
- **Current state**: The "Add to Archive" dialog is a fixed-size Win32 dialog (~640 × 500 px). All settings — from the common (format, compression level) to the advanced (dictionary size, word size, solid block size, CPU thread count, memory usage breakdowns, volume splitting, parameters) — are visible simultaneously. A typical user compressing files to share only needs: destination path, format, and compression level. The remaining 10+ controls are rarely used but occupy 60% of the dialog.
- **Impact**: New users are overwhelmed. Power users on high-DPI displays cannot widen the path field or see long filenames.
- **Recommendation**: (1) Collapse the advanced section (dictionary, word size, solid block, threads, memory) behind an "Advanced…" expander or a second tab. (2) Make the dialog resizable with a minimum size. (3) Move the archive path field to occupy the full dialog width.
- **Effort**: Medium
- **Category**: Information Architecture

---

**Finding UX-04**: Archive path shows filename only, source path truncated
- **Screen**: `wf01-add-to-archive/03-dialog-open.png`
- **Criterion**: Information Architecture > Status communication
- **Current state**: The "Archive:" field shows `hello.7z` (filename only), while the greyed-out header shows the truncated source path `C:\Users\JASON~1.BOG\AppData\Local\Temp\7zip-pw-wf01\` in 8.3 (short) path format. Users cannot see both the full source and destination paths simultaneously. The 8.3 path format (`JASON~1.BOG`) is a legacy artefact that exposes internal OS details and is harder to read than the full path.
- **Impact**: Users compressing files to a different destination may not notice they're saving to the source directory by default. 8.3 paths cause confusion.
- **Recommendation**: (1) Display the full destination path in the Archive field, not just the filename. (2) Use `GetLongPathName()` to resolve 8.3 paths before displaying in the title bar. (3) Make the Archive path field wide enough to show the full path.
- **Effort**: Low
- **Category**: Information Architecture

---

**Finding UX-05**: Asterisk prefix on settings has no legend
- **Screen**: `wf01-add-to-archive/03-dialog-open.png`
- **Criterion**: Information Architecture > Status communication
- **Current state**: Several combo boxes in the Add dialog have values prefixed with `*` (e.g., `* LZMA2`, `* 32 MB`, `* 32`, `* 8 GB`, `* 16`, `* 80%`). The meaning of `*` is not explained anywhere in the dialog, in a tooltip, or in a legend.
- **Impact**: All users. The `*` likely marks the default/auto-selected value, but without documentation this is invisible communication. Experienced users may know; new users cannot tell.
- **Recommendation**: Add a static text label below the advanced settings section or a `(?)` button tooltip: `* denotes the recommended default for the current archive format.` Alternatively, remove the asterisk and use a placeholder/hint text in the combo box or a "(default)" suffix.
- **Effort**: Low
- **Category**: Information Architecture

---

**Finding UX-06**: Test result dialog lacks visual success/failure indicator
- **Screen**: `wf03-test-archive/03-result-window.png`
- **Criterion**: Information Architecture > Status communication
- **Current state**: The "Testing" result window displays a plain-text message `There are no errors` in a small, non-highlighted paragraph. There is no color coding (green for success, red for failure), no icon (checkmark, warning triangle), and no visual hierarchy that separates the result from the statistics.
- **Impact**: Users who run a test to verify archive integrity cannot immediately see whether the result is pass or fail without reading the entire text. On failure, the error message would appear in the same unstyled format.
- **Recommendation**: Add a status row at the top of the result window with: (success) a green checkmark icon + bold "OK — No errors" text, or (failure) a red × icon + bold "ERRORS FOUND" text. This follows the pattern used by Windows Disk Check, scandisk, and similar integrity-reporting tools.
- **Effort**: Low
- **Category**: Information Architecture

---

**Finding UX-07**: Extract dialog title uses 8.3 (short) path format
- **Screen**: `wf02-extract-from-archive/03-dialog-open.png`
- **Criterion**: Information Architecture > Status communication
- **Current state**: The Extract dialog title bar reads `Extract : C:\Users\JASON~1.BOG\AppData\Local\Temp\7zip-pw-wf02\test-archive.zip`. The path contains `JASON~1.BOG` — the 8.3 short-name encoding of the username. This is a legacy NTFS artifact; the correct path is `jason.bogdanski`.
- **Impact**: Affects any user whose username, folder name, or archive path length triggers 8.3 encoding. Looks like a bug to inexperienced users.
- **Recommendation**: Pass all display paths through `GetLongPathName()` before assigning to dialog titles and static text controls. This is a one-line fix at every point where a path is placed into a display string.
- **Effort**: Low
- **Category**: Visual Design

---

**Finding UX-08**: Extract dialog layout unbalanced; empty password section prominent
- **Screen**: `wf02-extract-from-archive/03-dialog-open.png`
- **Criterion**: Visual Design > Spacing & density
- **Current state**: The Extract dialog has two columns. The left column (output path, filename filter, path mode, eliminate duplication, overwrite mode) is dense with controls. The right column has only "Password" + text field + "Show Password" checkbox + "Restore file security" checkbox, with a large whitespace block between them. The asymmetry gives the impression the right column is placeholder content.
- **Impact**: Visual impression of an unfinished layout; the empty space distracts from the key setting ("Extract to"). Moderate impact; mostly aesthetic.
- **Recommendation**: Move Password and "Restore file security" to a collapsible "Advanced" section or to a small secondary tab, so the primary path (just the destination folder + overwrite mode) fills the full width cleanly.
- **Effort**: Low–Medium
- **Category**: Visual Design

---

## Summary Table

| ID | Title | Category | Effort | Priority |
|---|---|---|---|---|
| UX-01 | Classic Win32 control styling | Visual Design | L–H | P3 |
| UX-02 | No dark mode support | Visual Design | Medium | P2 |
| UX-03 | Add dialog fixed-size + clutter | IA + Visual | Medium | P2 |
| UX-04 | Archive path incomplete; 8.3 source path | IA | Low | P1 |
| UX-05 | Asterisk prefix has no legend | IA | Low | P1 |
| UX-06 | Test result lacks visual pass/fail indicator | IA | Low | P1 |
| UX-07 | Extract title uses 8.3 path | Visual Design | Low | P1 |
| UX-08 | Extract layout unbalanced | Visual Design | Low–Med | P3 |

**P1 = Low effort, high clarity gain. Ship first.**  
**P2 = Medium effort, visible modernisation.**  
**P3 = Larger effort; address in a dedicated UI modernisation milestone.**
