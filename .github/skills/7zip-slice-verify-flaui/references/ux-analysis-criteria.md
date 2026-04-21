# UX Analysis Criteria — Generic Windows GUI Reference

Reference for evaluating screenshots and producing UX/UI improvement recommendations.
Apply to any Windows desktop application. Platform-specific conventions (Windows 11 Fluent,
WinUI 3, etc.) are noted in Section 7 as optional context \u2014 adapt to the project's actual
target platform.

## Evaluation Framework

Score each criterion 1–5 (1 = major problem, 5 = no issue). Findings are written for any criterion scoring ≤ 2.

---

## 1. Visual Design

| Criterion | What to Look For | Modern Baseline |
|---|---|---|
| **Typography** | Font size, weight hierarchy, readability at 100% and 125% DPI | 14px body, distinct heading sizes |
| **Iconography** | Icon age, style consistency, resolution (crisp at 1x and 2x) | SVG/vector or 32×32+ PNGs, consistent style |
| **Color system** | Is there a coherent palette? Does it follow Windows 11 Fluent conventions? | Accent color + neutral surface tokens |
| **Spacing & density** | Padding inside controls, row height in lists, whitespace between sections | 8px baseline grid; list rows ≥ 28px |
| **Control style** | Are buttons, dropdowns, and toolbars using legacy Win32 look or modern styled controls? | Windows 11 Mica/Acrylic or at minimum flat Fluent styling |
| **Dark mode** | Does the app respond to system dark/light preference? | Honors `HKEY_CURRENT_USER\...\AppsUseLightTheme` |

---

## 2. Information Architecture

| Criterion | What to Look For |
|---|---|
| **Toolbar discoverability** | Are the primary actions (Add, Extract, Test) immediately visible and labelled? |
| **Menu depth** | How many clicks to reach a secondary operation? More than 3 is a problem. |
| **Dialog layout** | In the Add/Extract dialogs: is the most important setting (format, destination) the most prominent? |
| **Progressive disclosure** | Are advanced options hidden until needed, or do they clutter the primary path? |
| **Status communication** | Does the UI clearly communicate: current archive, selected items, operation in progress? |
| **Empty state** | What does the user see when no archive is open / no files are selected? Is it instructional? |

---

## 3. Workflow Efficiency

| Criterion | What to Look For |
|---|---|
| **Steps to complete core task** | Count clicks from launch → archive created. Baseline: ≤ 4 clicks for a simple compress. |
| **Default correctness** | Are default format (7z), compression level (Normal), and destination folder sensible for most users? |
| **Keyboard accessibility** | Can the workflow be completed entirely without a mouse? Are accelerators labelled? |
| **Drag-and-drop** | Can files be dragged onto the window to initiate Add? |
| **Batch operations** | Can multiple archives be extracted in one operation? |
| **Recent archives** | Does the app offer quick access to recently opened archives? |

---

## 4. Accessibility

| Criterion | Standard | What to Check |
|---|---|---|
| **Color contrast** | WCAG AA: 4.5:1 for body text | Check toolbar labels and dialog text against backgrounds |
| **Focus indicators** | Visible keyboard focus ring on all interactive controls | Tab through the dialog — is focus ring visible? |
| **Screen reader labels** | Every button/icon should have an accessible name | Toolbar buttons — do they have tooltip text? |
| **Resize behavior** | Window and dialogs should be resizable without content clipping | Resize main window — does the file list grow? |
| **High DPI** | At 150% scaling, are icons and text crisp, not blurry? | Capture screenshot at 150% system scaling |

---

## 5. Finding Template

Use this format for every finding:

```
**Finding UX-<N>**: [Short title — 5 words max]
- **Screen**: [screenshot filename]
- **Criterion**: [category from above — e.g., Visual Design > Iconography]
- **Current state**: [objective description of what the screenshot shows]
- **Impact**: [who is affected, how severely, and how often]
- **Recommendation**: [specific, actionable change — e.g., "Replace 16×16 BMP toolbar icons with 24×24 SVGs from the Fluent System Icons library"]
- **Effort**: Low / Medium / High
- **Category**: Visual Design | Information Architecture | Workflow Efficiency | Accessibility
```

---

## 6. Priority Matrix

After all findings are written, score each on a 2×2 grid:

| | High Impact | Low Impact |
|---|---|---|
| **Low Effort** | P1 — Do first | P3 — Nice to have |
| **High Effort** | P2 — Plan for milestone | P4 — Defer |

Populate `docs/7zip/ux-analysis/ux-summary.md` with findings ordered P1 → P2 → P3 → P4.

---

## 7. Platform UI Reference Points

When producing recommendations, reference the conventions appropriate to the project's target platform and framework. Examples:

**Windows 11 / WinUI 3**: Mica material, 4px rounded corners, Segoe UI Variable font, Fluent System Icons, `NavigationView`, `CommandBar`, `InfoBar`, `ContentDialog`

**Windows 10 / WPF**: Flat Fluent controls, Segoe UI 9pt, system accent color, `Expander` for progressive disclosure

**Classic Win32 / MFC**: Toolbar bitmaps \u2192 icon fonts or SVGs; modeless task panes instead of blocking dialogs; manifest-declared DPI awareness (`<dpiAwareness>PerMonitorV2</dpiAwareness>`)

**Shell integration (any framework)**: Drag-and-drop targets via `IDropTarget`; Jump Lists for recent items (`ICustomDestinationList`); taskbar progress via `ITaskbarList3`

Tailor recommendations to what is achievable within the project's existing framework before suggesting a full rewrite.
