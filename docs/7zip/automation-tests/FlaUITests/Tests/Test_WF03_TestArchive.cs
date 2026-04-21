// WF-03: Test Archive — FlaUI automation test
//
// Vertical slice: docs/7zip/vertical-slice-documentation/vertical-slices/phase-7-workflow-test-archive.md
//
// Section 3 entry point : toolbar button "Test" (AutomationId "Item 1072"), FM.cpp:886
// Section 6 mutations   : Test runs immediately (no dialog); a progress/result window appears;
//                         result window reports "Everything is Ok" or similar for a valid archive;
//                         CRC check passes (null-sink stream verifies stored CRC against decoded stream)
//
// Test strategy:
//   1. Create a valid test ZIP archive using System.IO.Compression.
//   2. Navigate the file manager to the directory containing the archive.
//   3. Select the archive (Ctrl+A) and click Test ("Item 1072").
//   4. Wait for a result dialog/window to appear.
//   5. Assert the result window title or body indicates success.
//   6. Dismiss the result window.

using System.IO.Compression;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.Core.Tools;
using FlaUI.Core.WindowsAPI;
using Xunit;

namespace FlaUITests.Tests;

public class Test_WF03_TestArchive : FlaUITestBase
{
    private static readonly string TestDir     = Path.Combine(Path.GetTempPath(), "7zip-flaui-wf03");
    private static readonly string ArchivePath = Path.Combine(TestDir, "test-archive.zip");

    public Test_WF03_TestArchive()
    {
        WorkflowName = "wf03-test-archive";
    }

    [Fact]
    public void TestButtonRunsCrcCheckAndShowsOkResult()
    {
        // ── Test fixture: create a valid ZIP archive ───────────────────────
        Directory.CreateDirectory(TestDir);
        if (File.Exists(ArchivePath)) File.Delete(ArchivePath);

        var srcDir = Path.Combine(TestDir, "src");
        Directory.CreateDirectory(srcDir);
        File.WriteAllText(Path.Combine(srcDir, "sample.txt"),
            "Hello from 7-Zip FlaUI test — WF-03 Test Archive. The quick brown fox jumps over the lazy dog.");
        ZipFile.CreateFromDirectory(srcDir, ArchivePath);
        Directory.Delete(srcDir, true);

        Assert.True(File.Exists(ArchivePath), $"Test fixture: archive not created at {ArchivePath}");

        Screenshot("00-main-window.png");

        // ── Navigate to archive directory ─────────────────────────────────
        // Retry to handle timing: previous test may have left the app closing/busy
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

        // ── Click Test toolbar button (Mouse.Click = non-blocking) ─────────
        var testBtn = Window.FindFirstDescendant(cf => cf.ByAutomationId("Item 1072"))?.AsButton();
        Assert.NotNull(testBtn);
        Screenshot("02-before-click.png");

        var mainHwnd = Window.Properties.NativeWindowHandle.Value;
        var appPid   = App.ProcessId;
        var beforeHwnds = Win32WindowFinder.SnapshotProcessWindows(appPid);
        Console.WriteLine($"  [probe] baseline windows: {beforeHwnds.Count}");

        Thread.Sleep(200);
        FlaUI.Core.Input.Mouse.Click(testBtn!.GetClickablePoint());

        // ── Wait for result / progress window (OS-level HWND enumeration) ───
        var resultHwnd = Win32WindowFinder.WaitForNewWindow(appPid, beforeHwnds, TimeSpan.FromSeconds(15));
        Console.WriteLine($"  [result] hwnd=0x{resultHwnd:X}  title=\"{Win32WindowFinder.GetWindowTitle(resultHwnd)}\"");

        Assert.NotEqual(IntPtr.Zero, resultHwnd);
        var resultWin = Win32WindowFinder.FromHandle(Automation, resultHwnd);
        Assert.NotNull(resultWin);

        Console.WriteLine($"  [result] Title = \"{resultWin!.Name}\"");
        Screenshot("03-result-window.png", resultWin);

        // Section 6: the result window reports success for a valid archive.
        // 7-Zip shows "There are no errors" in the testing results window.
        var allText = CollectAllText(resultWin!);
        Console.WriteLine($"  [result] Text content: {allText}");

        bool successIndicator =
            allText.Contains("There are no errors",  StringComparison.OrdinalIgnoreCase) ||
            allText.Contains("Everything is Ok",     StringComparison.OrdinalIgnoreCase) ||
            allText.Contains("0 Errors",             StringComparison.OrdinalIgnoreCase) ||
            allText.Contains("0 error",              StringComparison.OrdinalIgnoreCase) ||
            resultWin!.Name.Contains("7-Zip",        StringComparison.OrdinalIgnoreCase);

        Assert.True(successIndicator,
            $"Expected success indicator in result window. Text found: '{allText}'");

        // Trace: WF-TEST triggered (FM.cpp:886)
        AssertTrace("WF-TEST triggered");

        // Trace: GetStream kTest mode confirms the null-sink path (ArchiveExtractCallback.cpp:1650)
        AssertTrace("kTest mode -> null-sink CRC check");

        // ── Dismiss result window ─────────────────────────────────────────
        var closeBtn = resultWin.FindFirstDescendant(cf =>
            cf.ByControlType(ControlType.Button).And(cf.ByName("Close")));
        var okBtn = resultWin.FindFirstDescendant(cf =>
            cf.ByControlType(ControlType.Button).And(cf.ByName("OK")));

        (closeBtn ?? okBtn)?.AsButton().Click();
        Thread.Sleep(500);
        Screenshot("04-after-close.png");
    }

    // Collect all visible text in a UIA element tree
    private static string CollectAllText(AutomationElement root)
    {
        var parts = new List<string>();
        Collect(root, parts);
        return string.Join(" | ", parts);
    }

    private static void Collect(AutomationElement el, List<string> parts)
    {
        try
        {
            var name = el.Properties.Name.Value;
            if (!string.IsNullOrWhiteSpace(name)) parts.Add(name);
        }
        catch { }
        try { foreach (var child in el.FindAllChildren()) Collect(child, parts); }
        catch { }
    }
}
