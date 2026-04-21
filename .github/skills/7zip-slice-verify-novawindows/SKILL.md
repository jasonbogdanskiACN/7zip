---
name: 7zip-slice-verify-novawindows
description: "WORKFLOW SKILL — Test, verify, and improve vertical slice documentation for any Windows GUI project using live Appium/NovaWindows Driver automation and UX analysis. USE FOR: discovering documented vertical slices; setting up Appium NovaWindows automation for a project by probing the live app accessibility tree; running automation tests against documented workflows and updating docs with new findings; capturing screenshots and producing UX/UI improvement recommendations. TRIGGER PHRASES: test vertical slice novawindows, novawindows automation, appium automation, verify workflow appium, automate testing appium, probe window appium, setup novawindows, setup appium, appium driver, novawindows driver, compare automation novawindows. DO NOT USE FOR: writing new vertical slice documents from scratch (use the reverse-engineering guide); debugging source code build errors; FlaUI or C# automation (use the 7zip-slice-verify skill); pywinauto automation (use the 7zip-slice-verify-pywinauto skill)."
argument-hint: "Workflow name to test, or 'all', or 'setup' to only run discovery+probe"
---

# Vertical Slice Verify & UX Improve — NovaWindows Driver Edition

Five-stage workflow: **Discover → Build → Probe → Test → UX**.

All stages run in sequence by default. Individual stages can be requested:
- `setup` — Stages 0-2 only (discover + build + probe, no testing)
- `all` — All five stages for every discovered workflow
- `<workflow-name>` — Stages 3-4 for one workflow (assumes setup already done)
- `UX analysis only` — Stage 4 only, using existing screenshots

> **Toolchain**: Node.js, Appium 2/3, appium-novawindows-driver (npm), Python 3.10+, Appium-Python-Client, pytest  
> **Comparison documents**:
> - [flaui-issues-log.md](../7zip-slice-verify/references/flaui-issues-log.md) — 14 FlaUI issues
> - [comparison-report-pywinauto.md](../7zip-slice-verify-pywinauto/references/comparison-report.md) — FlaUI vs pywinauto

---

## Stage 0: Project Discovery

Same as the FlaUI and pywinauto skills — toolchain-independent.

**Procedure**:

1. **Find the docs root.** Search for `session-status.md` under `docs/`. The directory containing it is the project docs root (e.g. `docs/7zip/`). Read it for: project name, current phase, last-completed step.

2. **Find vertical slices.** Glob for `docs/**/vertical-slices/phase-7-workflow-*.md`. For each file:
   - Extract workflow name from filename
   - Read Section 1 for a one-line description
   - Read Section 3 for the entry point / executable path
   - Note the **Status** marker (`✅ Complete`, `⚠️ Partial`, `🚫 Blocked`)

3. **Build the workflow list.** Sort: Complete first, Partial next, skip Blocked.

4. **Find the executable.** Check: project root, `traced-build/`, `bin/`, `out/`, `build/`, `x64/`, `Release/`.

5. **Check the toolchain:**

   ```powershell
   # Node / Appium
   node --version                          # need 18+
   appium --version                        # need 2.x or 3.x
   appium driver list --installed          # must include novawindows

   # Python client
   python --version                        # need 3.10+
   python -m pip show Appium-Python-Client # need 3.x+
   python -m pip show pytest
   python -m pip show Pillow
   ```

   If Appium is missing:
   ```powershell
   npm install -g appium
   ```
   If the driver is missing:
   ```powershell
   appium driver install --source=npm appium-novawindows-driver
   ```
   If Python packages are missing:
   ```powershell
   pip install Appium-Python-Client pytest Pillow
   ```

6. Print discovery summary:
   ```
   Project  : <name>
   Docs root: <path>
   Workflows: <N> (<list>)
   Executable: <path or NOT FOUND>
   Node   : <version>
   Appium : <version>
   Driver : novawindows <version or NOT INSTALLED>
   Python : <version>
   Appium-Python-Client: <version>
   ```

---

## Stage 1: Build Setup

**Purpose**: Ensure a runnable executable exists. Skip entirely if the exe was found in Stage 0 and is less than 7 days old.

**Procedure**: Identical to the FlaUI and pywinauto skill Stage 1. The build system does not depend on the automation toolchain. For 7-Zip, run `.\build-traced.ps1 -SkipInstall` to get the trace-instrumented binary.

---

## Stage 2: Automation Probe

**Purpose**: Discover the live application's accessibility tree through the Appium/NovaWindows server so test scripts can reference real element locators.

Read the NovaWindows patterns reference first:
[novawindows-patterns.md](./references/novawindows-patterns.md)

**Procedure**:

1. Start the Appium server using the helper script:
   [start_appium.ps1](./scripts/start_appium.ps1)

   ```powershell
   # In a separate terminal (background process):
   .\scripts\start_appium.ps1
   # Wait for "Appium REST http interface listener started" in output
   ```

2. Run the NovaWindows probe script:
   [probe_window.py](./scripts/probe_window.py)

   ```powershell
   python .github/skills/7zip-slice-verify-novawindows/scripts/probe_window.py `
       --exe "<exe-path>" `
       --output "docs/<project>/automation-tests-novawindows" `
       [--screenshot]
   ```

   The probe outputs:
   - `window-map.xml` — the raw Appium `page_source` (full UIA accessibility tree as XML)
   - `window-map.txt` — human-readable summary (element name, AutomationId, ClassName, tag)
   - `app-config.json` — discovered constants (ExePath, AppiumUrl, TraceLog)
   - `screenshots/probe/00-probe-idle.png` — baseline screenshot

3. Read `window-map.xml` / `window-map.txt` and cross-reference each workflow's Section 3 entry point.

4. **Note element locator strategy**. NovaWindows supports:
   - `accessibility id` — UIA AutomationId (from `window-map.xml` attribute `AutomationId`)
   - `class name` — ClassName (e.g. `ToolbarWindow32`, `SysListView32`)
   - `name` — element Name attribute
   - `xpath` — XPath 1.0 on any attribute in the UIA tree

   For 7-Zip (Win32/MFC), toolbar buttons have no AutomationId — use `name` or `xpath`.

5. Saved `app-config.json` shape:
   ```json
   {
     "ExePath":   "<resolved exe path>",
     "AppiumUrl": "http://127.0.0.1:4723",
     "TraceLog":  "C:\\Temp\\7z_trace.log"
   }
   ```

---

## Stage 3: Automation Test

**Purpose**: Drive the application through Appium/NovaWindows and verify it behaves as each vertical slice document describes.

Read the patterns reference for element location, interaction and known pitfalls:
[novawindows-patterns.md](./references/novawindows-patterns.md)

**Procedure**:

1. Ensure the Appium server is running (see Stage 2 step 1).

2. Read the target workflow's vertical slice. Extract:
   - Section 1: what it does (test goals)
   - Section 3: UI trigger (cross-reference `window-map.txt`)
   - Section 6: state mutations (assertions)
   - Section 7: error conditions

3. Write a pytest test file at:
   `docs/<project>/automation-tests-novawindows/tests/test_<name>.py`
   using the test template:
   [Python test template](./scripts/test_workflow_template.py)

   Use only locators confirmed in `window-map.txt`.

   **Critical interaction rules** (learned from FlaUI and pywinauto comparisons):
   - Use `driver.execute_script("windows: click", {"elementId": el.id})` for toolbar buttons — NOT `el.click()`. The W3C `element.click()` may use `InvokePattern` internally which **deadlocks** if the click opens a modal dialog on the same thread (FlaUI issue #5 equivalent).
   - For modal dialogs: after clicking, poll `driver.window_handles` until a new handle appears. Do NOT use `driver.find_element` on the main session — the dialog is a different window.
   - Switch context with `driver.switch_to.window(new_handle)` before interacting with the dialog.
   - Switch back with `driver.switch_to.window(main_handle)` before interacting with the main window again.

4. Run the tests:
   ```powershell
   pytest docs/<project>/automation-tests-novawindows/tests/ -v --tb=short
   ```
   Capture:
   - pytest pass/fail per assertion
   - Trace log lines (confirms internal code paths)
   - Screenshots at key steps

5. Compare against Section 6 assertions. Classify each:
   - **PASS** — observed as documented
   - **PARTIAL** — partially observed (dialog appeared but could not be completed without test data)
   - **FAIL** — contradicts documentation
   - **NOT TRIGGERED** — error condition unreachable

**Pass criteria**: All Section 6 mutations PASS or PARTIAL with explanation; no FAIL without a doc update.

---

## Stage 4: Documentation Update

Same procedure as the FlaUI and pywinauto skills. Append to the vertical slice's **Automation Test Log** section:

```markdown
### Automation Test Log
| Date | Script | Framework | Result | Findings |
|------|--------|-----------|--------|----------|
| YYYY-MM-DD | test_<name>.py | NovaWindows/Appium | PASS/PARTIAL/FAIL | [summary] |
```

---

## Stage 5: UX / UI Analysis

Same procedure as the other skills — screenshots captured during Stage 3 are toolchain-independent.

Read the UX criteria reference:
[UX analysis reference](../7zip-slice-verify/references/ux-analysis-criteria.md)

Save findings to `docs/<project>/ux-analysis/ux-findings-<workflow-name>-novawindows.md`.

---

## Comparison Tracking

After completing all tests, record in [comparison-report.md](./references/comparison-report.md):
- Which FlaUI issues were **not applicable** (toolchain-specific)
- Which were **avoided** by the Appium/UIA architecture
- Which were **reproduced** with the same or different root cause
- Any **new issues** specific to the Appium/NovaWindows layer (server startup, session creation, window handle switching)

Cross-reference also with the pywinauto comparison: [pywinauto comparison-report.md](../7zip-slice-verify-pywinauto/references/comparison-report.md).
