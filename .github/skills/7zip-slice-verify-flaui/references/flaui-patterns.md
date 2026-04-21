# FlaUI Patterns — Generic Reference

FlaUI is a .NET library (MIT, v5.0.0 Feb 2025) that directly wraps the Windows UIA2 and UIA3
COM accessibility APIs. It requires no external server process. NuGet packages:
`FlaUI.UIA2` (Win32/MFC/WinForms) or `FlaUI.UIA3` (WPF/WinUI/UWP).

Project-specific identifiers (AutomationId, Name, ControlType) come from the **probe output**
(`window-map.txt`) generated in Stage 2. Never assume them — always read the map first.

---

## 1. Backend Selection

| Backend NuGet | Use when | Notes |
|---|---|---|
| `FlaUI.UIA2` | Win32, MFC, WTL, classic WinForms | More reliable for legacy apps; no touch support |
| `FlaUI.UIA3` | WPF, WinUI 3, UWP, modern WinForms | Better feature coverage; occasional quirks with older WinForms |

Use **UIA2** for 7-Zip (Win32/MFC). The README notes UIA3 can have bugs with WinForms.

---

## 2. Project Setup

```xml
<!-- FlaUITests.csproj -->
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <IsPackable>false</IsPackable>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="FlaUI.UIA2"           Version="5.*" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.*" />
    <PackageReference Include="xunit"                 Version="2.*" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.*" />
  </ItemGroup>
</Project>
```

Run tests: `dotnet test`  
Run single test: `dotnet test --filter "FullyQualifiedName~TestClassName"`

---

## 3. Launch and Connect

```csharp
using FlaUI.Core;
using FlaUI.UIA2;

// Launch new instance
var app = Application.Launch(@"C:\path\to\app.exe");
using var automation = new UIA2Automation();
var window = app.GetMainWindow(automation);

// Attach to already-running instance
var app = Application.Attach("processName");  // by process name without .exe
var app = Application.Attach(processId);      // by PID
```

---

## 4. Finding Elements

Always prefer **AutomationId** — it is stable across UI changes. Fall back to Name, then ControlType.

```csharp
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Conditions;

// By AutomationId (most stable — use value from window-map.txt)
var btn = window.FindFirstDescendant(cf => cf.ByAutomationId("btnAdd"))?.AsButton();

// By Name (tooltip text for toolbar buttons)
var btn = window.FindFirstDescendant(cf => cf.ByName("Add"))?.AsButton();

// By ControlType
var toolbar = window.FindFirstDescendant(cf => cf.ByControlType(ControlType.ToolBar));

// Chained: toolbar button by name within toolbar
var btn = toolbar.FindFirstDescendant(cf => cf.ByName("Extract"))?.AsButton();

// By class name (Win32)
var list = window.FindFirstDescendant(cf => cf.ByClassName("SysListView32"))?.AsListBox();

// Combined condition
var el = window.FindFirstDescendant(cf =>
    cf.ByControlType(ControlType.Edit).And(cf.ByName("Archive:")));
```

---

## 5. Interactions

```csharp
// Button
btn.Click();
btn.DoubleClick();

// Edit / text box
var edit = dlg.FindFirstDescendant(cf => cf.ByAutomationId("txtOutput"))?.AsTextBox();
edit.Text = "new value";         // set text directly
edit.Enter("typed text");        // simulates keyboard input then Tab

// ComboBox
var combo = dlg.FindFirstDescendant(cf => cf.ByAutomationId("cmbFormat"))?.AsComboBox();
combo.Select("7z");
combo.Select(0);                 // by index

// ListView / ListBox
var list = window.FindFirstDescendant(cf => cf.ByClassName("SysListView32"))?.AsListBox();
list.Items[0].Select();
list.Items[0].Click();

// Menu
window.FindFirstDescendant(cf => cf.ByName("File"))?.AsMenuItem().Click();
// Then click sub-item:
app.GetMainWindow(automation)
   .FindFirstDescendant(cf => cf.ByName("Exit"))?.AsMenuItem().Click();
```

---

## 6. Waiting

FlaUI does not have a built-in `wait` mechanism like pywinauto. Use `Retry` or `Thread.Sleep`:

```csharp
using FlaUI.Core.Tools;

// Wait up to 5 seconds for an element to appear
var el = Retry.WhileNull(
    () => window.FindFirstDescendant(cf => cf.ByName("Add to Archive")),
    TimeSpan.FromSeconds(5)
).Result;

// Wait for a dialog window by title
var dlg = Retry.WhileNull(
    () => app.GetAllTopLevelWindows(automation)
              .FirstOrDefault(w => w.Title.Contains("Add to Archive")),
    TimeSpan.FromSeconds(8)
).Result;
```

---

## 7. Screenshots

FlaUI does not include built-in screenshot capture. Use `System.Drawing` or the Windows Graphics API:

```csharp
using System.Drawing;
using System.Drawing.Imaging;

void Screenshot(AutomationElement element, string path)
{
    var rect = element.BoundingRectangle;
    using var bmp = new Bitmap((int)rect.Width, (int)rect.Height);
    using var g = Graphics.FromImage(bmp);
    g.CopyFromScreen((int)rect.Left, (int)rect.Top, 0, 0, bmp.Size);
    bmp.Save(path, ImageFormat.Png);
}
```

---

## 8. Accessibility Inspection Tool

Use **Accessibility Insights for Windows** (free, from Microsoft):  
`winget install Microsoft.AccessibilityInsights`

This shows the live UIA tree with AutomationId, Name, ControlType, and BoundingRectangle —
the same values FlaUI uses. Essential for writing accurate locators.

Also available: `inspect.exe` (ships with Windows SDK) — older but always present.

---

## 9. Common Failure Modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `FindFirstDescendant` returns null | Wrong AutomationId or element not yet visible | Re-check window-map.txt; add `Retry.WhileNull` wait |
| `Click()` has no effect | Element not focusable (Win32 owner-draw) | Use `Patterns.Invoke.Pattern.Invoke()` instead |
| UIA2 vs UIA3 mismatch | Wrong NuGet for the app framework | Switch backend; see Section 1 |
| `BoundingRectangle` is empty | Element is off-screen or virtualized | Scroll the parent into view first |
| Tests pass solo but fail in sequence | Stale app handle (window re-created) | Re-fetch `GetMainWindow` after each dialog closes |
