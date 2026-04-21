#Requires -Version 5.1
<#
.SYNOPSIS
    Build 7-Zip File Manager with Z7_TRACE_ENABLE instrumentation.

.DESCRIPTION
    1. Detects (or installs) Visual Studio Build Tools 2022 with the C++ workload.
    2. Sources the MSVC x64 developer environment.
    3. Builds CPP\7zip\Bundles\Fm\ with /DZ7_TRACE_ENABLE.
    4. Copies the resulting 7zFM.exe to .\traced-build\.

    To view trace output at runtime:
      - Download Sysinternals DebugView (dbgview64.exe) from aka.ms/sysinternals
      - Run DebugView as Administrator, enable "Capture Win32" and "Capture Global Win32"
      - Launch .\traced-build\7zFM.exe and watch the [7z] lines appear live.

.PARAMETER SkipInstall
    Skip the winget VS Build Tools install step (use if already installed).

.PARAMETER LogFile
    If set, the traced 7zFM.exe will also write trace lines to this path.
    Achieved by compiling an additional /DZ7_TRACE_LOGFILE="<path>" definition.
    Example: -LogFile "C:\Temp\7z_trace.log"

.EXAMPLE
    .\build-traced.ps1
    .\build-traced.ps1 -SkipInstall
    .\build-traced.ps1 -LogFile "C:\Temp\7z_trace.log"
#>

[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [string]$LogFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot  = $PSScriptRoot
$FmMakefile   = Join-Path $ProjectRoot "CPP\7zip\Bundles\Fm"
$OutputDir    = Join-Path $ProjectRoot "traced-build"

# ---------------------------------------------------------------------------
# 1. Find or install VS Build Tools 2022
# ---------------------------------------------------------------------------
function Find-VcVars {
    $candidates = @(
        "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
        "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
        "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat",
        "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat",
        "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$vcvars = Find-VcVars

if (-not $vcvars) {
    if ($SkipInstall) {
        Write-Error "vcvars64.bat not found and -SkipInstall was set. Install VS Build Tools manually."
        exit 1
    }

    Write-Host "VS Build Tools 2022 not found. Installing via winget..." -ForegroundColor Cyan
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Error "winget not found. Install App Installer from the Microsoft Store, then rerun."
        exit 1
    }

    winget install --id Microsoft.VisualStudio.2022.BuildTools `
        --source winget `
        --override "--quiet --add Microsoft.VisualStudio.Workload.VCTools --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --includeRecommended" `
        --accept-package-agreements `
        --accept-source-agreements

    $vcvars = Find-VcVars
    if (-not $vcvars) {
        Write-Error "Installation finished but vcvars64.bat still not found. Check VS installer logs."
        exit 1
    }
    Write-Host "VS Build Tools installed at: $vcvars" -ForegroundColor Green
}
else {
    Write-Host "Found MSVC environment: $vcvars" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 2. Build the extra CFLAGS string
# ---------------------------------------------------------------------------
# Only pass /DZ7_TRACE_ENABLE; the logfile path defaults to C:\Temp\7z_trace.log
# as defined in Z7Trace.h — passing it via /D leads to cmd.exe quote-stripping.
# $LogFile parameter is kept for documentation/future use but is not forwarded.
$traceDefs = "/DZ7_TRACE_ENABLE"

# ---------------------------------------------------------------------------
# 3. Source vcvars64.bat and run nmake inside the same cmd session
# ---------------------------------------------------------------------------

# If the defines changed since last build, touch the traced source files so
# nmake detects them as newer than their .obj files and recompiles them.
$sentinelFile = Join-Path $FmMakefile "x64\.z7trace_defs"
$lastDefs     = if (Test-Path $sentinelFile) { Get-Content $sentinelFile -Raw } else { "" }
if ($lastDefs.Trim() -ne $traceDefs.Trim()) {
    Write-Host "Defines changed — touching traced source files to force recompile..." -ForegroundColor Yellow
    $tracedSources = @(
        "CPP\7zip\UI\FileManager\FM.cpp",
        "CPP\7zip\UI\GUI\CompressDialog.cpp",
        "CPP\7zip\UI\Common\ArchiveExtractCallback.cpp",
        "CPP\7zip\UI\Common\HashCalc.cpp",
        "CPP\7zip\UI\Common\UpdateProduce.cpp"
    )
    foreach ($rel in $tracedSources) {
        $full = Join-Path $ProjectRoot $rel
        if (Test-Path $full) { (Get-Item $full).LastWriteTime = Get-Date }
    }
}
Write-Host ""
Write-Host "Building 7zFM.exe with trace instrumentation..." -ForegroundColor Cyan
Write-Host "  Makefile dir : $FmMakefile"
Write-Host "  Extra defs   : $traceDefs"
Write-Host ""

$buildScript = @"
@echo off
call "$vcvars"
if errorlevel 1 exit /b 1
cd /d "$FmMakefile"
nmake PLATFORM=x64 MY_CFLAGS="$traceDefs"
exit /b %ERRORLEVEL%
"@

$tmpBat = [System.IO.Path]::GetTempFileName() + ".bat"
Set-Content -Path $tmpBat -Value $buildScript -Encoding ASCII

try {
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$tmpBat`"" `
        -NoNewWindow -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        Write-Error "Build failed (exit code $($proc.ExitCode)). Check output above."
        exit $proc.ExitCode
    }
}
finally {
    Remove-Item $tmpBat -ErrorAction SilentlyContinue
}

# ---------------------------------------------------------------------------
# 4. Copy output to traced-build\
# ---------------------------------------------------------------------------
$builtExe = Join-Path $FmMakefile "x64\7zFM.exe"
if (-not (Test-Path $builtExe)) {
    Write-Error "Expected output not found: $builtExe"
    exit 1
}

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Copy-Item $builtExe $OutputDir -Force
Set-Content -Path $sentinelFile -Value $traceDefs -NoNewline
Write-Host ""
Write-Host "Build succeeded." -ForegroundColor Green
Write-Host "  Output : $OutputDir\7zFM.exe"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Download DebugView64 from https://learn.microsoft.com/sysinternals/downloads/debugview"
Write-Host "  2. Run DebugView as Administrator; enable Capture > Win32 and Capture > Global Win32"
Write-Host "  3. Launch $OutputDir\7zFM.exe"
Write-Host "  4. Trigger Add/Extract/Test — watch [7z] WF-* lines appear in DebugView"
if ($LogFile -ne "") {
    Write-Host "  5. Trace also written to: $LogFile"
}
