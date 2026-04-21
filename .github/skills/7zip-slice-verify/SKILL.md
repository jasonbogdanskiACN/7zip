---
name: 7zip-slice-verify
description: "WORKFLOW SKILL — Test, verify, and improve vertical slice documentation for any Windows GUI project using live FlaUI automation and UX analysis. USE FOR: discovering documented vertical slices; setting up FlaUI automation for a project by probing the live app accessibility tree; building the project if no executable exists; running automation tests against documented workflows and updating docs with new findings; capturing screenshots and producing UX/UI improvement recommendations. TRIGGER PHRASES: test vertical slice, run automation, verify workflow, automate testing, probe window, setup automation, UX analysis, screenshot analysis, improve UI, modernize interface, update documentation from live run, setup FlaUI. DO NOT USE FOR: writing new vertical slice documents from scratch (use the reverse-engineering guide); debugging source code build errors."
argument-hint: "Workflow name to test, or 'all', or 'setup' to only run discovery+probe"
---

# Vertical Slice Verify & UX Improve

Five-stage workflow: **Discover → Build → Probe → Test → UX**.

All stages run in sequence by default. Individual stages can be requested:
- `setup` — Stages 0-2 only (discover + build + probe, no testing)
- `all` — All five stages for every discovered workflow
- `<workflow-name>` — Stages 3-4 for one workflow (assumes setup already done)
- `UX analysis only` — Stage 4 only, using existing screenshots

---

## Stage 0: Project Discovery

**Purpose**: Locate all documented vertical slices and learn what the project is, without any assumptions baked in.

**Procedure**:

1. **Find the docs root.** Search for `session-status.md` under `docs/`. The directory containing it is the project docs root (e.g. `docs/7zip/`). Read it for: project name, current phase, last-completed step.

2. **Find vertical slices.** Glob for `docs/**/vertical-slices/phase-7-workflow-*.md`. Each file is one candidate workflow. For each file:
   - Extract the workflow name from the filename (`phase-7-workflow-<name>.md` → `<name>`)
   - Read Section 1 (Executive Summary) to get a one-line description
   - Read Section 3 (Entry Point) to find the executable path or launch command
   - Note the **Status** marker at the top (`✅ Complete`, `⚠️ Partial`, `🚫 Blocked`)

3. **Build the workflow list.** Sort: Complete first, then Partial, skip Blocked. This replaces any hardcoded list.

4. **Find the executable.** The entry point from Section 3 of any workflow doc names the app. Also check:
   - `phase-4-client-architecture.md` for the launch command
   - `phase-0-prerequisites.md` for system type
   Common locations to check: project root, `bin/`, `out/`, `build/`, `traced-build/`, `x64/`, `Release/`

5. Print a discovery summary:
   ```
   Project: <name>
   Docs root: <path>
   Workflows found: <N> (<list of names>)
   Executable: <path or NOT FOUND>
   ```

---

## Stage 1: Build Setup

**Purpose**: Ensure a runnable executable exists. Skip entirely if the exe was found in Stage 0 and is less than 7 days old.

**Procedure**:

1. **Detect build system.** Scan the project root for these indicators in priority order:

   | Indicator file(s) | Build system | Typical command |
   |---|---|---|
   | `build-traced.ps1` or `build*.ps1` | Custom PowerShell build | `.\<script>.ps1` |
   | `*.sln` | MSBuild / Visual Studio | `msbuild <file>.sln /p:Configuration=Release` |
   | `makefile` or `Makefile` | nmake / make | `nmake PLATFORM=x64` or `make` |
   | `CMakeLists.txt` | CMake | `cmake --build build --config Release` |
   | `Cargo.toml` | Rust / cargo | `cargo build --release` |
   | `package.json` with `"build"` script | Node / Electron | `npm run build` |
   | `*.csproj` / `*.fsproj` (no `.sln`) | dotnet CLI | `dotnet build` |
   | `pyproject.toml` / `setup.py` | Python package | `pip install -e .` |

2. **Check for a tracing/debug variant.** Prefer any build script named `build-traced*`, `build-debug*`, or one that accepts a debug flag. If found, use it — trace output makes automation verification much richer.

3. **Resolve build tool availability.** Before running the build command:
   - For nmake/MSBuild: check if `cl.exe` is on PATH; if not, locate `vcvars64.bat` under `Program Files (x86)\Microsoft Visual Studio` and source it in a wrapper `cmd /c "call vcvars64.bat && <build command>"`
   - For dotnet: `dotnet --version`
   - For cargo: `cargo --version`
   - For npm: `node --version && npm --version`
   If the required tool is missing, report what needs to be installed and stop this stage. Do not guess or substitute.

4. **Check automation prerequisites** (required before Stage 2):
   - .NET SDK 8+: `dotnet --version` — if missing: `winget install Microsoft.DotNet.SDK.8`
   - FlaUI NuGet packages are restored automatically when `setup_flaui_project.ps1` runs.

   **Why FlaUI, not WinAppDriver or pywinauto for tests?**  
   FlaUI (v5.0.0 released Feb 2025, MIT, 2.9k stars) directly wraps the Windows UIA2/UIA3 COM APIs — the same accessibility foundation that screen readers and Windows Accessibility Insights use. It requires no external server process and has no abandoned backend dependency. WinAppDriver has not been maintained by Microsoft since 2021 and its own Appium proxy warns users to migrate away. pywinauto is suitable for the probe-discovery phase but is a scripting library, not an enterprise test framework.

5. **Run the build.** Capture output. On success, verify the executable exists at the expected output path. On failure, display the first compiler error line and stop.

6. **Record** the exe path and build command in session notes for use in Stages 2–4.

---

## Stage 2: Automation Probe

**Purpose**: Discover the live application's accessibility tree so test scripts can reference real element identifiers — not assumed ones. All probing and testing uses FlaUI (C#/.NET).

Read the FlaUI element reference first:  
[FlaUI patterns reference](./references/flaui-patterns.md)

**Procedure**:

1. Run the FlaUI probe application:  
   [probe app](./scripts/ProbeApp/)

   ```
   dotnet run --project .github/skills/7zip-slice-verify/scripts/ProbeApp -- <exe-path> --output docs/<project>/automation-tests [--dialogs]
   ```

   The probe outputs:
   - The application's control tree as `window-map.txt` (ControlType, Name, AutomationId per element)
   - Toolbar button inventory with Name and tooltip label
   - A baseline screenshot (`screenshots/probe/00-probe-idle.png`)
   - Per-dialog control maps for any dialog reachable from toolbar buttons (pass `--screenshot`)

2. Save output to `docs/<project>/automation-tests/`.

3. **Read each workflow's Section 3** and cross-reference: confirm the entry point matches a real element in `window-map.txt`. Note mismatches — they are Stage 3 findings.

4. The probe writes `docs/<project>/automation-tests/app-config.json` with discovered constants:
   ```json
   {
     "ExePath": "<resolved exe path>",
     "MainWindowTitle": "<window title>",
     "UiaBackend": "UIA2",
     "TraceLog": null
   }
   ```
   UIA2 is preferred for Win32/MFC applications. Use UIA3 for WPF/WinUI/UWP.

5. Initialize the FlaUI test project:  
   [FlaUI setup script](./scripts/setup_flaui_project.ps1)  
   This creates `docs/<project>/automation-tests/FlaUITests/` with a pre-configured xUnit + FlaUI solution ready to run.

---

## Stage 3: Automation Test

**Purpose**: Drive the application with FlaUI (C#/.NET) and verify it behaves as each vertical slice document describes.

Read the FlaUI reference for element location and interaction patterns:  
[FlaUI reference](./references/flaui-patterns.md)

**Procedure**:

1. Read the target workflow's vertical slice from the list built in Stage 0. Extract:
   - Section 1: what the workflow does (defines test goals)
   - Section 3: entry point / UI trigger (defines which element to activate — cross-reference `window-map.txt` for the AutomationId or Name)
   - Section 6: state mutations (defines what must change — these become xUnit `Assert` calls)
   - Section 7: error conditions (defines what inputs trigger which errors)

2. Write a C# test class in the FlaUI project at  
   `docs/<project>/automation-tests/FlaUITests/Tests/Test_<Name>.cs`  
   using the test template:  
   [C# test template](./scripts/TestWorkflowTemplate.cs)  
   Use only the `AutomationId` or `Name` values confirmed in `window-map.txt`.

3. Run the tests: `dotnet test docs/<project>/automation-tests/FlaUITests/`. Capture:
   - xUnit test output (pass/fail per assertion)
   - `TraceLog` lines if available (confirms internal code paths were hit)
   - Screenshots written by the test at each key step

4. Compare results against Section 6 assertions. Classify each:
   - **PASS** — observed as documented
   - **PARTIAL** — partially observed (dialog appeared but could not be completed without test data)
   - **FAIL** — behavior contradicts documentation
   - **NOT TRIGGERED** — error condition unreachable in this run (document why)

**Pass criteria**: All Section 6 mutations PASS or PARTIAL with explanation; no FAIL without a doc update in Stage 4.

---

## Stage 4: Documentation Update

**Purpose**: Update the vertical slice document with facts observed in Stage 3. Never infer — only record what was directly observed.

**Procedure**:

1. For each FAIL or discrepancy:
   - If the **doc was wrong**: correct the doc, mark `[VERIFIED: <date>]`
   - If the **doc was incomplete**: add the finding to the relevant section
   - If the **behavior was unexpected**: add to Section 9 (Key Insights)

2. For each PARTIAL with an explanation: add a note to Section 7 clarifying the test precondition needed.

3. Append to Section 10 (Conclusion):
   ```
   ### Automation Test Log
   | Date | Script | Result | Findings |
   |------|--------|--------|----------|
   | YYYY-MM-DD | Test_<Name>.cs | PASS/PARTIAL/FAIL | [summary] |
   ```

4. Update `session-status.md` — add workflow to a "Verified by automation" list.

---

## Stage 5: UX / UI Analysis

**Purpose**: Analyze screenshots from Stage 3 and produce actionable UX/UI improvement recommendations.

Read the UX criteria reference first:  
[UX analysis reference](./references/ux-analysis-criteria.md)

**Procedure**:

1. Screenshots are already in `docs/<project>/screenshots/<workflow-name>/` from Stage 3. If running this stage standalone, capture them now using `probe_window.py --screenshot`.

2. Analyze each screenshot against the five UX criteria categories in the reference. Write one Finding block per issue.

3. Save findings to `docs/<project>/ux-analysis/ux-findings-<workflow-name>.md`.

4. After all workflows: update or create `docs/<project>/ux-analysis/ux-summary.md` with all findings ranked by the Priority Matrix (Impact × Effort).
