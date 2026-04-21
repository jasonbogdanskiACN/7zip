// Stage 2: FlaUI Window Probe
//
// Launches an application, walks its UIA accessibility tree, captures a screenshot,
// and writes artifacts consumed by the FlaUI test project (Stage 3).
//
// Usage:
//   dotnet run --project scripts/ProbeApp -- <exe-path> [--output <dir>] [--dialogs] [--uia3]
//   dotnet run --project scripts/ProbeApp                  (reads ExePath from app-config.json)
//
// Options:
//   --output <dir>   Where to write window-map.txt and app-config.json
//                    Default: current directory
//   --dialogs        Click each toolbar button, capture the dialog it opens, and write
//                    window-map-<ButtonName>.txt for each dialog
//   --uia3           Use UIA3 backend (default: UIA2 — prefer for Win32 / MFC apps)
//
// Outputs:
//   <output>/window-map.txt                           element tree (ControlType  Name  AutomationId)
//   <output>/window-map-<ButtonName>.txt              per-dialog tree (--dialogs only)
//   <output>/app-config.json                          config for the FlaUI test project
//   <output>/../screenshots/probe/00-probe-idle.png   baseline screenshot
//   <output>/../screenshots/probe/dialog-NN-<name>.png per-dialog screenshot (--dialogs only)

using System.Text;
using System.Text.Json;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Capturing;
using FlaUI.Core.Definitions;
using FlaUI.UIA2;

// ── Parse arguments ───────────────────────────────────────────────────────

string? exePath   = null;
string? outputDir = null;
bool    doDialogs = false;
bool    useUia3   = false;

for (int i = 0; i < args.Length; i++)
{
    if      (args[i] == "--output")     outputDir = args[++i];
    else if (args[i] == "--dialogs")    doDialogs = true;
    else if (args[i] == "--uia3")       useUia3   = true;
    else if (!args[i].StartsWith("--")) exePath   = args[i];
}

outputDir ??= Directory.GetCurrentDirectory();

// Fall back to reading ExePath from an existing app-config.json
if (exePath is null)
{
    var cfgPath = Path.Combine(outputDir, "app-config.json");
    if (File.Exists(cfgPath))
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(cfgPath));
        if (doc.RootElement.TryGetProperty("ExePath", out var ep))
            exePath = ep.GetString();
        Console.WriteLine($"[probe] ExePath from app-config.json: {exePath}");
    }
}

if (exePath is null || !File.Exists(exePath))
{
    Console.Error.WriteLine(
        "Usage: dotnet run --project scripts/ProbeApp -- <exe-path> [--output <dir>] [--dialogs] [--uia3]");
    if (exePath is not null)
        Console.Error.WriteLine($"       Not found: {exePath}");
    return 1;
}

Directory.CreateDirectory(outputDir);
var screenshotDir = Path.Combine(outputDir, "..", "screenshots", "probe");
Directory.CreateDirectory(screenshotDir);

// ── Launch application ────────────────────────────────────────────────────

Console.WriteLine($"[probe] Executable : {exePath}");
Console.WriteLine($"[probe] Backend    : {(useUia3 ? "UIA3" : "UIA2")}");
Console.WriteLine($"[probe] Output     : {Path.GetFullPath(outputDir)}");

using AutomationBase automation = useUia3
    ? (AutomationBase)new FlaUI.UIA3.UIA3Automation()
    : new UIA2Automation();

var app    = Application.Launch(exePath);
Thread.Sleep(2_000);

var window = app.GetMainWindow(automation, TimeSpan.FromSeconds(10))
    ?? throw new Exception("Main window not found after 10 s. Is the application starting correctly?");

var windowTitle = window.Title;
Console.WriteLine($"[probe] Window     : \"{windowTitle}\"");

// ── Walk accessibility tree ───────────────────────────────────────────────

Console.WriteLine("[probe] Walking accessibility tree...");
var treeLines = WalkTree(window);

var mapPath = Path.Combine(outputDir, "window-map.txt");
File.WriteAllLines(mapPath, treeLines, Encoding.UTF8);
Console.WriteLine($"[probe] window-map.txt   -> {treeLines.Count} named element(s)");
PrintPreview(treeLines, 60);

// ── Toolbar inventory ─────────────────────────────────────────────────────

Console.WriteLine("\n[probe] Toolbar buttons:");
var toolbarButtons = new List<(string Name, string AutomationId)>();
try
{
    var toolbars = window.FindAllDescendants(cf => cf.ByControlType(ControlType.ToolBar));
    for (int ti = 0; ti < toolbars.Length; ti++)
    {
        var buttons = toolbars[ti].FindAllDescendants(cf => cf.ByControlType(ControlType.Button));
        Console.WriteLine($"  ToolBar[{ti}]: {buttons.Length} button(s)");
        foreach (var btn in buttons)
        {
            var nm  = TryGet(() => btn.Properties.Name.Value)         ?? "";
            var aid = TryGet(() => btn.Properties.AutomationId.Value) ?? "";
            Console.WriteLine($"    Name={Q(nm),-32}  AutomationId={Q(aid)}");
            toolbarButtons.Add((nm, aid));
        }
    }
}
catch (Exception ex) { Console.WriteLine($"  Toolbar enumeration failed: {ex.Message}"); }

// ── Baseline screenshot ───────────────────────────────────────────────────

Snap(window, Path.Combine(screenshotDir, "00-probe-idle.png"));

// ── Optional: probe each toolbar dialog ───────────────────────────────────

if (doDialogs)
{
    Console.WriteLine("\n[probe] Probing dialogs triggered by toolbar buttons...");
    int idx = 0;
    var mainHandle = TryGet(() => window.Properties.NativeWindowHandle.Value.ToString()) ?? "";

    foreach (var (btnName, _) in toolbarButtons.Where(b => b.Name.Length > 0))
    {
        idx++;
        try
        {
            var btn = window.FindFirstDescendant(cf =>
                cf.ByControlType(ControlType.Button).And(cf.ByName(btnName)));
            if (btn is null) continue;

            btn.AsButton().Click();
            Thread.Sleep(900);

            // Look for a new top-level window (dialog box)
            var allWins = app.GetAllTopLevelWindows(automation);
            var dlg = allWins.FirstOrDefault(w =>
                (TryGet(() => w.Properties.NativeWindowHandle.Value.ToString()) ?? "") != mainHandle);

            string safe = SafeName(btnName);

            if (dlg is not null)
            {
                Snap(dlg, Path.Combine(screenshotDir, $"dialog-{idx:D2}-{safe}.png"));
                var dlgLines = WalkTree(dlg);
                File.WriteAllLines(Path.Combine(outputDir, $"window-map-{safe}.txt"), dlgLines, Encoding.UTF8);
                Console.WriteLine($"  [{idx}] \"{btnName}\" -> dialog captured ({dlgLines.Count} elements)");
            }
            else
            {
                Console.WriteLine($"  [{idx}] \"{btnName}\" -> no new window appeared");
            }

            // Dismiss any open dialog via Escape before moving to next button
            FlaUI.Core.Input.Keyboard.Press(FlaUI.Core.WindowsAPI.VirtualKeyShort.ESCAPE);
            Thread.Sleep(400);
        }
        catch (Exception ex) { Console.WriteLine($"  [{idx}] \"{btnName}\" failed: {ex.Message}"); }
    }
}

// ── Write app-config.json ─────────────────────────────────────────────────

var config = new
{
    ExePath         = Path.GetFullPath(exePath),
    MainWindowTitle = windowTitle,
    UiaBackend      = useUia3 ? "UIA3" : "UIA2",
    TraceLog        = (string?)null          // set by setup_flaui_project.ps1 if tracing is enabled
};

var configPath = Path.Combine(outputDir, "app-config.json");
File.WriteAllText(configPath,
    JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"\n[probe] app-config.json  -> written");
Console.WriteLine("[probe] Done.");

app.Close();
return 0;

// ── Helpers ───────────────────────────────────────────────────────────────

static List<string> WalkTree(AutomationElement root)
{
    var lines = new List<string>();
    WalkRecursive(root, 0, lines);
    return lines;
}

static void WalkRecursive(AutomationElement el, int depth, List<string> lines)
{
    var name   = TryGet(() => el.Properties.Name.Value)          ?? "";
    var autoId = TryGet(() => el.Properties.AutomationId.Value)  ?? "";
    var ctType = TryGet(() => el.Properties.ControlType.Value.ToString()) ?? "Unknown";

    if (name.Length > 0 || autoId.Length > 0)
        lines.Add($"{new string(' ', depth * 2)}{ctType,-20}  Name={Q(name),-40}  AutomationId={Q(autoId)}");

    int nextDepth = depth + (name.Length > 0 || autoId.Length > 0 ? 1 : 0);
    try { foreach (var child in el.FindAllChildren()) WalkRecursive(child, nextDepth, lines); }
    catch { /* element may be destroyed during enumeration */ }
}

static void Snap(AutomationElement el, string filePath)
{
    try
    {
        using var img = Capture.Element(el);
        img.ToFile(filePath);
        Console.WriteLine($"[probe] Screenshot  -> {Path.GetFileName(filePath)}");
    }
    catch (Exception ex) { Console.WriteLine($"[probe] Screenshot failed: {ex.Message}"); }
}

static void PrintPreview(List<string> lines, int max)
{
    foreach (var l in lines.Take(max)) Console.WriteLine("  " + l);
    if (lines.Count > max) Console.WriteLine($"  ... ({lines.Count} total — see window-map.txt)");
}

static string? TryGet<T>(Func<T?> f) { try { return f()?.ToString(); } catch { return null; } }
static string  Q(string s)          => $"\"{s}\"";
static string  SafeName(string s)   => new(s.Take(32).Select(c => char.IsLetterOrDigit(c) ? c : '_').ToArray());
