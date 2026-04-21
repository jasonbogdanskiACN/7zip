# Stage 2 — Setup FlaUI Test Project
#
# Creates (or updates) a ready-to-run xUnit + FlaUI test project at:
#   <OutputDir>/FlaUITests/
#
# The project automatically copies app-config.json from <OutputDir> into its build
# output so tests can read it at runtime via AppContext.BaseDirectory.
#
# Usage:
#   .\setup_flaui_project.ps1 -OutputDir docs\7zip\automation-tests
#   .\setup_flaui_project.ps1 -OutputDir docs\myapp\automation-tests -TraceLog C:\Temp\app_trace.log

param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDir,      # path to the automation-tests directory (where app-config.json lives)
    [string]$TraceLog = ""   # optional path to trace log; written into app-config.json
)

$ErrorActionPreference = 'Stop'

# ── Directories ───────────────────────────────────────────────────────────

$TestsDir  = Join-Path $OutputDir 'FlaUITests'
$TestsSubDir = Join-Path $TestsDir 'Tests'

New-Item -ItemType Directory -Force -Path $TestsSubDir | Out-Null
Write-Host "[setup] Test project dir : $TestsDir"

# ── Update app-config.json TraceLog field ─────────────────────────────────

$ConfigPath = Join-Path $OutputDir 'app-config.json'
if ((Test-Path $ConfigPath) -and $TraceLog) {
    $cfg = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    $cfg.TraceLog = $TraceLog
    $cfg | ConvertTo-Json -Depth 5 | Set-Content $ConfigPath -Encoding utf8NoBOM
    Write-Host "[setup] app-config.json  : TraceLog = $TraceLog"
}

# ── FlaUITests.csproj ─────────────────────────────────────────────────────

$CsprojPath = Join-Path $TestsDir 'FlaUITests.csproj'
if (-not (Test-Path $CsprojPath)) {
    @'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net8.0-windows</TargetFramework>
    <IsPackable>false</IsPackable>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
  <ItemGroup>
    <!-- UIA2 for Win32/MFC; UIA3 for WPF/WinUI — driven by UiaBackend in app-config.json -->
    <PackageReference Include="FlaUI.UIA2"                    Version="5.*" />
    <PackageReference Include="FlaUI.UIA3"                    Version="5.*" />
    <PackageReference Include="Microsoft.NET.Test.Sdk"        Version="17.*" />
    <PackageReference Include="xunit"                         Version="2.*" />
    <PackageReference Include="xunit.runner.visualstudio"     Version="2.*" />
    <PackageReference Include="coverlet.collector"            Version="6.*" />
  </ItemGroup>
  <!-- Copy the probe-generated config into the test binary output directory -->
  <ItemGroup>
    <Content Include="..\app-config.json">
      <CopyToOutputDirectory>PreserveNewest</CopyToOutputDirectory>
      <Link>app-config.json</Link>
    </Content>
  </ItemGroup>
</Project>
'@ | Set-Content $CsprojPath -Encoding utf8NoBOM
    Write-Host "[setup] Created          : FlaUITests.csproj"
} else {
    Write-Host "[setup] Skipped (exists) : FlaUITests.csproj"
}

# ── FlaUITestBase.cs ──────────────────────────────────────────────────────

$BasePath = Join-Path $TestsDir 'FlaUITestBase.cs'
if (-not (Test-Path $BasePath)) {
    @'
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

        Automation = Config.UiaBackend == "UIA3"
            ? (AutomationBase)new FlaUI.UIA3.UIA3Automation()
            : new FlaUI.UIA2.UIA2Automation();

        // Clear trace log before each test so assertions are per-test
        if (Config.TraceLog is not null && File.Exists(Config.TraceLog))
            File.WriteAllText(Config.TraceLog, "");

        App = Application.Launch(Config.ExePath);
        Thread.Sleep(1_500);

        Window = App.GetMainWindow(Automation, TimeSpan.FromSeconds(10))
            ?? throw new Exception("Main window not found after 10 s.");

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
        return File.ReadAllLines(Config.TraceLog);
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
        try { App.Close(); } catch { /* swallow if already closed */ }
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
'@ | Set-Content $BasePath -Encoding utf8NoBOM
    Write-Host "[setup] Created          : FlaUITestBase.cs"
} else {
    Write-Host "[setup] Skipped (exists) : FlaUITestBase.cs"
}

# ── Restore NuGet packages ────────────────────────────────────────────────

Write-Host "[setup] Restoring NuGet packages..."
dotnet restore $CsprojPath

Write-Host ""
Write-Host "[setup] Done."
Write-Host "[setup] Add test classes (copy and rename TestWorkflowTemplate.cs) to:"
Write-Host "        $TestsSubDir"
Write-Host "[setup] Run tests:"
Write-Host "        dotnet test $TestsDir"
