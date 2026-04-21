// Template: FlaUI xUnit test for one vertical slice workflow.
//
// Before using this template:
//   1. Stage 2 (Probe) must have run and produced:
//        docs/<project>/automation-tests/app-config.json  (ExePath, MainWindowTitle, UiaBackend)
//        docs/<project>/automation-tests/window-map.txt   (element identifiers)
//   2. setup_flaui_project.ps1 must have been run to create this project + FlaUITestBase.
//   3. Read window-map.txt to find the real AutomationId / Name values for this workflow.
//      Do NOT guess identifiers — use only what the probe reported.
//
// Usage (from the FlaUITests project directory):
//   dotnet test --filter "FullyQualifiedName~Test_<WorkflowName>"
//
// Replace all <PLACEHOLDER> sections with workflow-specific logic drawn from:
//   Section 3 of the vertical slice doc  — which element to activate
//   Section 6 of the vertical slice doc  — what state must change (assertions)
//   Section 7 of the vertical slice doc  — which error inputs trigger which messages

using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.Core.Tools;
using Xunit;

namespace FlaUITests.Tests;

// Rename class and file to Test_<WorkflowName>.cs
public class Test_WorkflowTemplate : FlaUITestBase
{
    // ── Entry point ───────────────────────────────────────────────────────

    [Fact]
    public void WorkflowOpensExpectedDialog()
    {
        // Step 1 — Locate the trigger control.
        // Use AutomationId from window-map.txt (preferred) or Name as fallback.
        //
        // Example: toolbar button by Name
        //   var toolbar = Window.FindFirstDescendant(cf => cf.ByControlType(ControlType.ToolBar));
        //   var btn     = toolbar?.FindFirstDescendant(cf => cf.ByName("<from window-map.txt>"))?.AsButton();
        //   Assert.NotNull(btn);
        //
        // <PLACEHOLDER: locate trigger element>
        AutomationElement? triggerElement = null; // replace with real locator

        Assert.NotNull(triggerElement);
        Screenshot("01-before-trigger.png");

        // Step 2 — Activate the trigger.
        triggerElement!.AsButton().Click();

        // Step 3 — Wait for the expected dialog / state change.
        //   Replace "Dialog Title" with the window title from window-map.txt.
        //
        //   var dlg = Retry.WhileNull(
        //       () => App.GetAllTopLevelWindows(Automation)
        //                .FirstOrDefault(w => w.Title.Contains("<dialog title>")),
        //       TimeSpan.FromSeconds(8)
        //   ).Result;
        //   Assert.NotNull(dlg);
        //   Screenshot(dlg, "02-dialog-open.png");
        //
        // <PLACEHOLDER: wait for dialog or state change>

        // Step 4 — Assert Section 6 state mutations.
        //
        //   Example: output path field is pre-populated
        //   var outEdit = dlg?.FindFirstDescendant(cf => cf.ByAutomationId("<from window-map.txt>"))?.AsTextBox();
        //   Assert.NotNull(outEdit);
        //   Assert.False(string.IsNullOrEmpty(outEdit!.Text), "Output path should be pre-populated");
        //
        //   Example: format combo defaults to expected value
        //   var fmt = dlg?.FindFirstDescendant(cf => cf.ByAutomationId("<from window-map.txt>"))?.AsComboBox();
        //   Assert.Equal("7z", fmt?.SelectedItem?.Text);
        //
        // <PLACEHOLDER: assertions from Section 6>

        // Step 5 — Optional trace verification (confirms the internal code path ran).
        //   AssertTrace("WF-ADD triggered");   // uncomment and set for this workflow
        Screenshot("99-final-state.png");

        // Step 6 — Dismiss / cleanup.
        //   dlg?.FindFirstDescendant(cf => cf.ByName("Cancel"))?.AsButton()?.Click();
        // <PLACEHOLDER: close dialog / reset state>
    }

    // ── Error condition tests (Section 7) ─────────────────────────────────

    [Fact]
    public void ErrorCondition_ShowsExpectedMessage()
    {
        // <PLACEHOLDER>
        // Example pattern:
        //   Trigger the workflow, enter an invalid input, click OK,
        //   then assert the error message text matches Section 7.
        //
        //   var dlg = OpenWorkflowDialog();
        //   dlg.FindFirstDescendant(cf => cf.ByAutomationId("txtPassword"))?.AsTextBox()
        //      .Enter("bad");
        //   dlg.FindFirstDescendant(cf => cf.ByName("OK"))?.AsButton()?.Click();
        //   var msg = Retry.WhileNull(
        //       () => App.GetAllTopLevelWindows(Automation)
        //                .FirstOrDefault(w => w.Title.Contains("Error")),
        //       TimeSpan.FromSeconds(4)
        //   ).Result;
        //   Assert.NotNull(msg);
        //   dlg.FindFirstDescendant(cf => cf.ByName("Cancel"))?.AsButton()?.Click();
        Assert.True(true, "Replace this placeholder with a real error-condition test.");
    }
}
