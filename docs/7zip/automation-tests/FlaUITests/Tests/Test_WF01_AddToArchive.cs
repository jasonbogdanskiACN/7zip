// WF-01: Add to Archive  — FlaUI automation test
//
// Vertical slice: docs/7zip/vertical-slice-documentation/vertical-slices/phase-7-workflow-add-to-archive.md
//
// Section 3 entry point : toolbar button "Add" (AutomationId "Item 1070"), FM.cpp:884
// Section 6 mutations   : dialog opens with pre-populated archive path; format combo present; OK/Cancel present
//
// Test strategy:
//   1. Create a temp directory with one text file.
//   2. Navigate the file manager to that directory via the address bar (AutomationId "1003").
//   3. Select all items (Ctrl+A on the DataGrid "1001").
//   4. Click the Add toolbar button ("Item 1070").
//   5. Wait for the "Add to Archive" dialog to appear as a new top-level window.
//   6. Assert the dialog's key controls exist (archive path field non-empty, format combo, buttons).
//   7. Dismiss with Cancel; verify no archive file was written.

using FlaUI.Core.AutomationElements;
using FlaUI.Core.Conditions;
using FlaUI.Core.Definitions;
using FlaUI.Core.Tools;
using FlaUI.Core.WindowsAPI;
using Xunit;

namespace FlaUITests.Tests;

public class Test_WF01_AddToArchive : FlaUITestBase
{
    private static readonly string TestDir = Path.Combine(
        Path.GetTempPath(), "7zip-flaui-wf01");

    public Test_WF01_AddToArchive()
    {
        WorkflowName = "wf01-add-to-archive";
    }

    [Fact]
    public void AddButtonOpensCompressDialogWithPrePopulatedPath()
    {
        // ── Test fixture setup ────────────────────────────────────────────
        Directory.CreateDirectory(TestDir);
        File.WriteAllText(Path.Combine(TestDir, "hello.txt"),
            "Hello from 7-Zip FlaUI test — WF-01 Add to Archive");
        var expectedArchive = Path.Combine(TestDir, "hello.7z");
        if (File.Exists(expectedArchive)) File.Delete(expectedArchive);

        Screenshot("00-main-window.png");

        // ── Navigate to test directory ────────────────────────────────────
        // Address bar: Edit child of ComboBox, both share AutomationId "1003"
        Window.Focus();
        AutomationElement? addrEdit = null;
        var addrDeadline = DateTime.UtcNow.AddSeconds(10);
        while (DateTime.UtcNow < addrDeadline && addrEdit == null)
        {
            try
            {
                addrEdit = Window.FindFirstDescendant(cf =>
                    cf.ByAutomationId("1003").And(cf.ByControlType(ControlType.Edit)));
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  [addrEdit retry] {ex.GetType().Name}: {ex.Message.Split('\n')[0]}");
            }
            if (addrEdit == null) Thread.Sleep(300);
        }
        Console.WriteLine($"  [addrEdit] {(addrEdit != null ? addrEdit.AutomationId : "null")}");
        Assert.NotNull(addrEdit);

        addrEdit!.AsTextBox().Text = TestDir;
        FlaUI.Core.Input.Keyboard.Press(VirtualKeyShort.RETURN);
        Thread.Sleep(1_500);
        Screenshot("01-navigated.png");

        // ── Select the test file by clicking its DataItem ─────────────────
        // Wait for the directory to load — items appear as DataItem elements
        Thread.Sleep(1_200);
        Window.Focus();
        var fileItem = Retry.WhileNull(
            () => Window.FindAllDescendants(cf => cf.ByControlType(ControlType.DataItem))
                        .FirstOrDefault(e =>
                        {
                            try { return e.Name.Contains("hello.txt", StringComparison.OrdinalIgnoreCase); }
                            catch { return false; }
                        }),
            TimeSpan.FromSeconds(6)
        ).Result;
        Assert.NotNull(fileItem);
        fileItem!.Click();
        Thread.Sleep(200);

        // Verify selection reflected in status bar
        var statusBar = Window.FindFirstDescendant(cf => cf.ByAutomationId("StatusBar.Pane0"));
        Console.WriteLine($"  [status] {statusBar?.Name ?? "(null)"}");

        // ── Click Add toolbar button ──────────────────────────────────────
        var addBtn = Window.FindFirstDescendant(cf => cf.ByAutomationId("Item 1070"))?.AsButton();
        Assert.NotNull(addBtn);
        Screenshot("02-before-click.png");

        var appPid      = App.ProcessId;
        var beforeHwnds = Win32WindowFinder.SnapshotProcessWindows(appPid);
        Console.WriteLine($"  [probe] baseline windows: {beforeHwnds.Count}");

        Thread.Sleep(200);
        FlaUI.Core.Input.Mouse.Click(addBtn!.GetClickablePoint());

        // ── Wait for "Add to Archive" dialog (OS-level HWND enumeration) ──
        var dlgHwnd = Win32WindowFinder.WaitForNewWindow(appPid, beforeHwnds, TimeSpan.FromSeconds(10));
        Console.WriteLine($"  [dialog] hwnd=0x{dlgHwnd:X}  title=\"{Win32WindowFinder.GetWindowTitle(dlgHwnd)}\"");

        Assert.NotEqual(IntPtr.Zero, dlgHwnd);
        var dlg = Win32WindowFinder.FromHandle(Automation, dlgHwnd);
        Assert.NotNull(dlg);
        Console.WriteLine($"  [dialog] Title = \"{dlg!.Name}\"");
        Screenshot("03-dialog-open.png", dlg);

        // Section 6: dialog title indicates Add operation
        Assert.True(
            dlg.Name.Contains("Add", StringComparison.OrdinalIgnoreCase) ||
            dlg.Name.Contains("Archive", StringComparison.OrdinalIgnoreCase) ||
            dlg.Name.Contains("7-Zip", StringComparison.OrdinalIgnoreCase),
            $"Dialog title '{dlg.Name}' does not indicate an Add-to-Archive operation.");

        // Section 6: archive path field is pre-populated (non-empty)
        // The archive path is in the first Edit control in the dialog
        var allEdits = dlg.FindAllDescendants(cf => cf.ByControlType(ControlType.Edit));
        Console.WriteLine($"  [dialog] Edit controls: {allEdits.Length}");
        Assert.True(allEdits.Length > 0, "Expected at least one Edit control in the Add dialog.");

        var archivePathEdit = allEdits.FirstOrDefault(e =>
        {
            try { return !string.IsNullOrEmpty(e.AsTextBox().Text); } catch { return false; }
        });
        Assert.NotNull(archivePathEdit);
        Console.WriteLine($"  [dialog] Archive path = \"{archivePathEdit!.AsTextBox().Text}\"");

        // Section 6: format ComboBox exists (7z, ZIP, etc.)
        var combos = dlg.FindAllDescendants(cf => cf.ByControlType(ControlType.ComboBox));
        Console.WriteLine($"  [dialog] ComboBoxes: {combos.Length}");
        Assert.True(combos.Length > 0, "Expected format ComboBox in the Add dialog.");

        // Section 6: OK and Cancel buttons exist
        var cancelBtn = dlg.FindFirstDescendant(cf =>
            cf.ByControlType(ControlType.Button).And(cf.ByName("Cancel")));
        Assert.NotNull(cancelBtn);

        var okBtn = dlg.FindFirstDescendant(cf =>
            cf.ByControlType(ControlType.Button).And(cf.ByName("OK")));
        Assert.NotNull(okBtn);

        // Trace verification: FM.cpp:884 should have emitted WF-ADD trace
        AssertTrace("WF-ADD triggered");

        // ── Dismiss without creating archive ─────────────────────────────
        cancelBtn!.AsButton().Click();
        Thread.Sleep(500);

        // Section 6 / cleanup: archive must NOT exist after Cancel
        Assert.False(File.Exists(expectedArchive),
            "Archive file should not be created after clicking Cancel.");

        Screenshot("04-after-cancel.png");
    }
}
