// WF-02: Extract from Archive — FlaUI automation test
//
// Vertical slice: docs/7zip/vertical-slice-documentation/vertical-slices/phase-7-workflow-extract-from-archive.md
//
// Section 3 entry point : toolbar button "Extract" (AutomationId "Item 1071"), FM.cpp:885
// Section 6 mutations   : Extract dialog opens; output directory field is pre-populated;
//                         path mode and overwrite controls exist; OK/Cancel present
//
// Test strategy:
//   1. Create a test ZIP archive using System.IO.Compression (no 7z.exe required).
//   2. Navigate the file manager to the directory containing the archive.
//   3. Select the archive (it should be the only item, or use Ctrl+A).
//   4. Click Extract ("Item 1071").
//   5. Assert the Extract dialog opens with an output-directory field.
//   6. Dismiss with Cancel; verify no extraction occurred.

using System.IO.Compression;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.Core.Tools;
using FlaUI.Core.WindowsAPI;
using Xunit;

namespace FlaUITests.Tests;

public class Test_WF02_ExtractFromArchive : FlaUITestBase
{
    private static readonly string TestDir     = Path.Combine(Path.GetTempPath(), "7zip-flaui-wf02");
    private static readonly string ArchivePath = Path.Combine(TestDir, "test-archive.zip");
    private static readonly string ExtractDir  = Path.Combine(TestDir, "extracted");

    public Test_WF02_ExtractFromArchive()
    {
        WorkflowName = "wf02-extract-from-archive";
    }

    [Fact]
    public void ExtractButtonOpensExtractDialogWithPrePopulatedOutputDir()
    {
        // ── Test fixture: create a ZIP archive ────────────────────────────
        Directory.CreateDirectory(TestDir);
        if (Directory.Exists(ExtractDir)) Directory.Delete(ExtractDir, true);
        if (File.Exists(ArchivePath)) File.Delete(ArchivePath);

        // Stage the source file, create zip, remove source
        var srcDir = Path.Combine(TestDir, "src");
        Directory.CreateDirectory(srcDir);
        File.WriteAllText(Path.Combine(srcDir, "sample.txt"),
            "Hello from 7-Zip FlaUI test — WF-02 Extract");
        ZipFile.CreateFromDirectory(srcDir, ArchivePath);
        Directory.Delete(srcDir, true);

        Assert.True(File.Exists(ArchivePath), $"Test fixture: archive not created at {ArchivePath}");

        Screenshot("00-main-window.png");

        // ── Navigate to archive directory ─────────────────────────────────
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

        // ── Select the archive by clicking its DataItem ──────────────────
        Thread.Sleep(1_200);
        Window.Focus();
        var archiveItem = Retry.WhileNull(
            () => Window.FindAllDescendants(cf => cf.ByControlType(ControlType.DataItem))
                        .FirstOrDefault(e =>
                        {
                            try { return e.Name.Contains("test-archive.zip", StringComparison.OrdinalIgnoreCase); }
                            catch { return false; }
                        }),
            TimeSpan.FromSeconds(6)
        ).Result;
        Assert.NotNull(archiveItem);
        archiveItem!.Click();
        Thread.Sleep(200);

        // ── Click Extract toolbar button (Mouse.Click = non-blocking) ───────
        var extractBtn = Window.FindFirstDescendant(cf => cf.ByAutomationId("Item 1071"))?.AsButton();
        Assert.NotNull(extractBtn);
        Screenshot("02-before-click.png");

        var mainHwnd = Window.Properties.NativeWindowHandle.Value;
        var appPid   = App.ProcessId;
        var beforeHwnds = Win32WindowFinder.SnapshotProcessWindows(appPid);
        Console.WriteLine($"  [probe] baseline windows: {beforeHwnds.Count}");

        Thread.Sleep(200);
        FlaUI.Core.Input.Mouse.Click(extractBtn!.GetClickablePoint());

        // ── Wait for Extract dialog (OS-level HWND enumeration) ──────────────
        var dlgHwnd = Win32WindowFinder.WaitForNewWindow(appPid, beforeHwnds, TimeSpan.FromSeconds(10));
        Console.WriteLine($"  [dialog] hwnd=0x{dlgHwnd:X}  title=\"{Win32WindowFinder.GetWindowTitle(dlgHwnd)}\"");

        Assert.NotEqual(IntPtr.Zero, dlgHwnd);
        var dlg = Win32WindowFinder.FromHandle(Automation, dlgHwnd);
        Assert.NotNull(dlg);

        Console.WriteLine($"  [dialog] Title = \"{dlg!.Name}\"");
        Screenshot("03-dialog-open.png", dlg);

        // Section 6: dialog title indicates an Extract / open-archive operation
        Assert.True(
            dlg.Name.Contains("Extract", StringComparison.OrdinalIgnoreCase) ||
            dlg.Name.Contains("7-Zip", StringComparison.OrdinalIgnoreCase),
            $"Dialog title '{dlg.Name}' does not indicate an Extract operation.");

        // Section 6: output directory field exists and is pre-populated
        var allEdits = dlg.FindAllDescendants(cf => cf.ByControlType(ControlType.Edit));
        Console.WriteLine($"  [dialog] Edit controls: {allEdits.Length}");
        Assert.True(allEdits.Length > 0, "Expected at least one Edit control (output dir) in the Extract dialog.");

        var outputDirEdit = allEdits.FirstOrDefault(e =>
        {
            try { return !string.IsNullOrEmpty(e.AsTextBox().Text); } catch { return false; }
        });
        Assert.NotNull(outputDirEdit);
        Console.WriteLine($"  [dialog] Output dir = \"{outputDirEdit!.AsTextBox().Text}\"");

        // Section 6: path mode controls (radio buttons or combo) present
        var combos  = dlg.FindAllDescendants(cf => cf.ByControlType(ControlType.ComboBox));
        var radios  = dlg.FindAllDescendants(cf => cf.ByControlType(ControlType.RadioButton));
        Console.WriteLine($"  [dialog] ComboBoxes: {combos.Length}  RadioButtons: {radios.Length}");
        Assert.True(combos.Length > 0 || radios.Length > 0,
            "Expected path mode or overwrite controls in the Extract dialog.");

        // OK and Cancel must exist
        var cancelBtn = dlg.FindFirstDescendant(cf =>
            cf.ByControlType(ControlType.Button).And(cf.ByName("Cancel")));
        Assert.NotNull(cancelBtn);

        var okBtn = dlg.FindFirstDescendant(cf =>
            cf.ByControlType(ControlType.Button).And(cf.ByName("OK")));
        Assert.NotNull(okBtn);

        // Trace: FM.cpp:885 emits WF-EXTRACT triggered
        AssertTrace("WF-EXTRACT triggered");

        // ── Dismiss without extracting ────────────────────────────────────
        cancelBtn!.AsButton().Click();
        Thread.Sleep(500);

        // Section 6: extracted directory must NOT exist after Cancel
        Assert.False(Directory.Exists(ExtractDir),
            "Extracted directory should not be created after clicking Cancel.");

        Screenshot("04-after-cancel.png");
    }
}
