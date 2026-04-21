---
name: 7zip-slice-verify-pywinauto
description: "WORKFLOW SKILL — Test, verify, and improve vertical slice documentation for any Windows GUI project using live pywinauto automation and UX analysis. USE FOR: discovering documented vertical slices; probing the live app accessibility tree with Python; running automation tests against documented workflows and updating docs with new findings; capturing screenshots and producing UX/UI improvement recommendations. TRIGGER PHRASES: test vertical slice pywinauto, pywinauto automation, verify workflow python, automate testing python, probe window python, setup pywinauto, python automation, compare automation. DO NOT USE FOR: writing new vertical slice documents from scratch (use the reverse-engineering guide); debugging source code build errors; FlaUI or C# automation (use the 7zip-slice-verify skill)."
argument-hint: "Workflow name to test, or 'all', or 'setup' to only run discovery+probe"
---

# Vertical Slice Verify & UX Improve — pywinauto Edition

Five-stage workflow: **Discover → Build → Probe → Test → UX**.

All stages run in sequence by default. Individual stages can be requested:
- `setup` — Stages 0-2 only (discover + build + probe, no testing)
- `all` — All five stages for every discovered workflow
- `<workflow-name>` — Stages 3-4 for one workflow (assumes setup already done)
- `UX analysis only` — Stage 4 only, using existing screenshots

> **Toolchain**: Python 3.10+, pywinauto, Pillow, pytest  
> **Comparison document**: See [flaui-issues-log.md](..//7zip-slice-verify/references/flaui-issues-log.md) for known FlaUI issues to watch for — and note whether pywinauto avoids or reproduces them.

---

## Stage 0: Project Discovery

Same as the FlaUI skill — this stage is toolchain-independent.

**Procedure**:

1. **Find the docs root.** Search for `session-status.md` under `docs/`. The directory containing it is the project docs root (e.g. `docs/7zip/`). Read it for: project name, current phase, last-completed step.

2. **Find vertical slices.** Glob for `docs/**/vertical-slices/phase-7-workflow-*.md`. Each file is one candidate workflow. For each file:
   - Extract the workflow name from the filename
   - Read Section 1 (Executive Summary) for a one-line description
   - Read Section 3 (Entry Point) for the executable path or launch command
   - Note the **Status** marker (`✅ Complete`, `⚠️ Partial`, `🚫 Blocked`)

3. **Build the workflow list.** Sort: Complete first, then Partial, skip Blocked.

4. **Find the executable.** Check: project root, `bin/`, `out/`, `build/`, `traced-build/`, `x64/`, `Release/`.

5. **Check Python environment:**
   ```powershell
   python --version                    # need 3.10+
   python -m pip show pywinauto        # need 2.0.x
   python -m pip show Pillow           # needed for screenshots
   python -m pip show pytest           # needed for test runner
   ```
   If any missing: `pip install pywinauto Pillow pytest`

6. Print discovery summary:
   ```
   Project: <name>
   Docs root: <path>
   Workflows found: <N> (<list of names>)
   Executable: <path or NOT FOUND>
   Python: <version>
   pywinauto: <version>
   ```

---

## Stage 1: Build Setup

**Purpose**: Ensure a runnable executable exists. Skip entirely if the exe was found in Stage 0 and is less than 7 days old.

**Procedure**: Identical to the FlaUI skill Stage 1. The build system is project-dependent, not toolchain-dependent. For 7-Zip, use `.\build-traced.ps1 -SkipInstall` to get the trace-instrumented binary.

---

## Stage 2: Automation Probe

**Purpose**: Discover the live application's accessibility tree with pywinauto so test scripts can reference real element identifiers from the running app — not assumed ones.

Read the pywinauto patterns reference first:  
[pywinauto patterns reference](./references/pywinauto-patterns.md)

**Procedure**:

1. Run the pywinauto probe script:  
   [probe script](./scripts/probe_window.py)

   ```powershell
   python .github/skills/7zip-slice-verify-pywinauto/scripts/probe_window.py `
       --exe "<exe-path>" `
       --output "docs/<project>/automation-tests-pywinauto" `
       [--screenshot]
   ```

   The probe outputs:
   - `window-map.txt` — full control tree (control_type, title, auto_id, class_name, rect)
   - `app-config.json` — discovered constants (ExePath, backend, etc.)
   - `screenshots/probe/00-probe-idle.png` — baseline screenshot

2. Read `window-map.txt` and cross-reference each workflow's Section 3 entry point.

3. **Note the backend**. pywinauto supports two backends:
   - `win32` — uses Win32 API (`FindWindow`, `SendMessage`). Better for classic Win32/MFC apps.
   - `uia` — uses Microsoft UIA (same as FlaUI conceptually, but Python wrapper). Slower but richer for WPF/WinUI.
   For 7-Zip (Win32/MFC), try `win32` first. If control enumeration is incomplete, fall back to `uia`.

4. Saved `app-config.json` shape:
   ```json
   {
     "ExePath": "<resolved exe path>",
     "MainWindowTitle": "<window title regex>",
     "Backend": "win32",
     "TraceLog": "C:\\Temp\\7z_trace.log"
   }
   ```

---

## Stage 3: Automation Test

**Purpose**: Drive the application with pywinauto (Python/pytest) and verify it behaves as each vertical slice document describes.

Read the reference for element location and interaction patterns:  
[pywinauto reference](./references/pywinauto-patterns.md)

**Procedure**:

1. Read the target workflow's vertical slice from the Stage 0 list. Extract:
   - Section 1: what the workflow does (test goals)
   - Section 3: entry point / UI trigger (cross-reference `window-map.txt`)
   - Section 6: state mutations (assertions)
   - Section 7: error conditions

2. Write a pytest test file at:  
   `docs/<project>/automation-tests-pywinauto/tests/test_<name>.py`  
   using the test template:  
   [Python test template](./scripts/test_workflow_template.py)  
   Use only `auto_id`, `title`, or `class_name` values confirmed in `window-map.txt`.

3. Run the tests:
   ```powershell
   pytest docs/<project>/automation-tests-pywinauto/tests/ -v --tb=short
   ```
   Capture:
   - pytest pass/fail per assertion
   - Trace log lines (confirms internal code paths hit)
   - Screenshots written at each key step

4. Compare results against Section 6 assertions. Classify each:
   - **PASS** — observed as documented
   - **PARTIAL** — partially observed (dialog appeared but could not be completed without test data)
   - **FAIL** — behavior contradicts documentation
   - **NOT TRIGGERED** — error condition unreachable in this run

**Pass criteria**: All Section 6 mutations PASS or PARTIAL with explanation; no FAIL without a doc update in Stage 4.

---

## Stage 4: Documentation Update

Same procedure as the FlaUI skill Stage 4 — toolchain-independent.

For the automation test log entry, use:
```
### Automation Test Log
| Date | Script | Framework | Result | Findings |
|------|--------|-----------|--------|----------|
| YYYY-MM-DD | test_<name>.py | pywinauto | PASS/PARTIAL/FAIL | [summary] |
```

---

## Stage 5: UX / UI Analysis

Same procedure as the FlaUI skill Stage 5 — screenshots are captured during Stage 3 regardless of toolchain.

Read the UX criteria reference:  
[UX analysis reference](..//7zip-slice-verify/references/ux-analysis-criteria.md)

Save findings to `docs/<project>/ux-analysis/ux-findings-<workflow-name>-pywinauto.md`.

---

## Comparison Tracking

After completing all tests, note which FlaUI issues from [flaui-issues-log.md](..//7zip-slice-verify/references/flaui-issues-log.md) were:  
- **Not applicable** — pywinauto architecture avoids the issue entirely  
- **Same issue, different fix** — same root cause, different API surface  
- **New issue** — a pywinauto-specific problem not seen in FlaUI  

Record this in [comparison-report.md](./references/comparison-report.md) once both toolchains have results.
