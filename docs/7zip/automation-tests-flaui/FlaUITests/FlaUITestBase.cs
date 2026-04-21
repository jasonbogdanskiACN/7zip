// Base class for all FlaUI xUnit tests.
//
// Reads app-config.json (written by the probe) from the test output directory,
// launches the application, exposes Window and helper methods, then disposes
// everything after each test.
//
// Usage: inherit from FlaUITestBase in every test class.

using System.Text.Json;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Capturing;
using Xunit;

namespace FlaUITests;

public abstract class FlaUITestBase : IDisposable
{
    // ── Config loaded from app-config.json ────────────────────────────────

    private static readonly AppConfig Config = LoadConfig();

    private static AppConfig LoadConfig()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "app-config.json");
        if (!File.Exists(path))
            throw new FileNotFoundException(
                $"app-config.json not found at {path}. " +
                "Run Stage 2 (Probe) first: dotnet run --project scripts/ProbeApp -- <exe-path> ...");
        return JsonSerializer.Deserialize<AppConfig>(File.ReadAllText(path))
            ?? throw new InvalidOperationException("app-config.json could not be parsed.");
    }

    // ── Automation objects (per test) ─────────────────────────────────────

    protected Application     App        { get; }
    protected AutomationBase  Automation { get; }
    protected AutomationElement Window   { get; }

    protected string WorkflowName { get; set; } = "workflow";

    private readonly string _screenshotDir;

    protected FlaUITestBase()
    {
        if (!File.Exists(Config.ExePath))
            throw new FileNotFoundException($"Executable not found: {Config.ExePath}");

        // Kill existing 7zFM processes FIRST — before creating the Automation object
        // so we start with a fresh COM/UIA state (no stale references from killed processes).
        var exeName = Path.GetFileNameWithoutExtension(Config.ExePath);
        foreach (var p in System.Diagnostics.Process.GetProcessesByName(exeName))
        {
            try { p.Kill(); p.WaitForExit(3_000); } catch { /* best effort */ }
        }
        Thread.Sleep(800); // let the OS fully release COM / file handles

        // Create Automation AFTER killing old processes (fresh COM state)
        Automation = Config.UiaBackend == "UIA3"
            ? (AutomationBase)new FlaUI.UIA3.UIA3Automation()
            : new FlaUI.UIA2.UIA2Automation();

        // Clear trace log before each test so assertions are per-test
        if (Config.TraceLog is not null)
            try { File.WriteAllText(Config.TraceLog, ""); }
            catch { /* ignore if locked */ }

        App = Application.Launch(Config.ExePath);
        Thread.Sleep(2_000); // extra time for window to fully render

        // Use Win32WindowFinder to find the new process's main window.
        // We can't rely on App.GetMainWindow() (returns stale/intermediate windows)
        // or WaitForWindowWithTitle (7-Zip's title bar shows the current path, not "7-Zip").
        // Strategy: wait for a visible window belonging to the new PID.
        // Poll with retry so the window has time to appear.
        AutomationElement? foundWindow = null;
        var windowDeadline = DateTime.UtcNow.AddSeconds(15);
        while (DateTime.UtcNow < windowDeadline && foundWindow == null)
        {
            var snapshot = Win32WindowFinder.SnapshotProcessWindows(App.ProcessId);
            foreach (var hwnd in snapshot)
            {
                var title = Win32WindowFinder.GetWindowTitle(hwnd);
                if (!string.IsNullOrEmpty(title))
                {
                    foundWindow = Win32WindowFinder.FromHandle(Automation, hwnd);
                    if (foundWindow != null)
                    {
                        Console.WriteLine($"  [window] hwnd=0x{hwnd:X} name='{title}' pid={App.ProcessId}");
                        break;
                    }
                }
            }
            if (foundWindow == null) Thread.Sleep(300);
        }
        Window = foundWindow
            ?? throw new Exception($"No titled window found for PID {App.ProcessId} within 15 s.");

        _screenshotDir = Path.Combine(
            AppContext.BaseDirectory, "..", "..", "..", "..", "screenshots", WorkflowName);
    }

    // ── Helpers ───────────────────────────────────────────────────────────

    /// <summary>Capture the main window (or a given element) to a PNG file.</summary>
    protected void Screenshot(string fileName, AutomationElement? element = null)
    {
        var dir = Path.Combine(
            AppContext.BaseDirectory, "..", "..", "..", "..", "screenshots", WorkflowName);
        Directory.CreateDirectory(dir);
        var path = Path.Combine(dir, fileName);
        try
        {
            using var img = Capture.Element(element ?? Window);
            img.ToFile(path);
            Console.WriteLine($"  [screenshot] {fileName}");
        }
        catch (Exception ex) { Console.WriteLine($"  [screenshot failed] {ex.Message}"); }
    }

    /// <summary>Read all lines from the trace log (empty list if not configured).</summary>
    protected IReadOnlyList<string> ReadTrace()
    {
        if (Config.TraceLog is null || !File.Exists(Config.TraceLog))
            return Array.Empty<string>();
        // Use FileShare.ReadWrite so we can read while 7zFM still holds the file
        // open for appending (Z7Trace.h uses a static FILE* in _SH_DENYNO mode).
        using var fs = new FileStream(
            Config.TraceLog, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        using var sr = new StreamReader(fs, System.Text.Encoding.UTF8);
        return sr.ReadToEnd().Split('\n', StringSplitOptions.RemoveEmptyEntries);
    }

    /// <summary>Assert that at least one trace line contains <paramref name="pattern"/>.</summary>
    protected void AssertTrace(string pattern)
    {
        var lines = ReadTrace();
        var hits  = lines.Where(l => l.Contains(pattern)).ToList();
        Assert.True(hits.Count > 0,
            $"Expected trace line containing '{pattern}' but none found.\n" +
            $"Last 10 lines:\n{string.Join("\n", lines.TakeLast(10))}");
        Console.WriteLine($"  [trace ✓] '{pattern}'");
    }

    // ── Dispose ───────────────────────────────────────────────────────────

    public void Dispose()
    {
        try { App.Close(); } catch { /* swallow */ }
        // Force-kill if Close() didn't work (e.g., blocked by a modal dialog).
        try
        {
            if (!App.HasExited)
            {
                App.Kill();
                App.WaitWhileMainHandleIsMissing(TimeSpan.FromSeconds(3));
            }
        }
        catch { /* best effort */ }
        try { Automation.Dispose(); } catch { }
        GC.SuppressFinalize(this);
    }

    // ── Config record ─────────────────────────────────────────────────────

    private sealed class AppConfig
    {
        public string  ExePath         { get; init; } = "";
        public string  MainWindowTitle { get; init; } = "";
        public string  UiaBackend      { get; init; } = "UIA2";
        public string? TraceLog        { get; init; }
    }
}
