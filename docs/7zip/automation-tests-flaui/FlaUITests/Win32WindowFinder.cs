// Win32 helper for finding top-level windows belonging to a process.
//
// Uses EnumWindows (OS-level enumeration) instead of UIA tree walking.
// This finds ALL visible top-level windows for a given PID — including
// modal dialogs that may not appear in UIA's desktop FindAllChildren().
//
// Usage:
//   var hwnd = Win32WindowFinder.FindNewWindow(appPid, excludedHwnds, timeout);
//   var el   = automation.FromHandle(hwnd);

using System.Runtime.InteropServices;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;

namespace FlaUITests;

internal static class Win32WindowFinder
{
    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);

    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    /// <summary>
    /// Returns a snapshot of all visible top-level window handles owned by <paramref name="pid"/>.
    /// </summary>
    public static HashSet<IntPtr> SnapshotProcessWindows(int pid)
    {
        var result = new HashSet<IntPtr>();
        EnumWindows((hwnd, _) =>
        {
            if (IsWindowVisible(hwnd))
            {
                GetWindowThreadProcessId(hwnd, out uint wPid);
                if ((int)wPid == pid) result.Add(hwnd);
            }
            return true;   // continue enumeration
        }, IntPtr.Zero);
        return result;
    }

    /// <summary>
    /// Polls until a new visible window belonging to <paramref name="pid"/> appears
    /// that was not in <paramref name="beforeHwnds"/>. Returns <c>IntPtr.Zero</c> on timeout.
    /// </summary>
    public static IntPtr WaitForNewWindow(int pid, HashSet<IntPtr> beforeHwnds,
        TimeSpan timeout, int pollMs = 300)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            EnumWindows((hwnd, _) =>
            {
                if (IsWindowVisible(hwnd) && !beforeHwnds.Contains(hwnd))
                {
                    GetWindowThreadProcessId(hwnd, out uint wPid);
                    if ((int)wPid == pid)
                    {
                        // Signal via "found" HWND stored in the outer scope
                        _foundHwnd = hwnd;
                        return false;   // stop enumeration
                    }
                }
                return true;
            }, IntPtr.Zero);

            if (_foundHwnd != IntPtr.Zero)
            {
                var result = _foundHwnd;
                _foundHwnd = IntPtr.Zero;
                return result;
            }
            Thread.Sleep(pollMs);
        }
        return IntPtr.Zero;
    }

    [ThreadStatic]
    private static IntPtr _foundHwnd;

    /// <summary>Get the window title of a given HWND.</summary>
    public static string GetWindowTitle(IntPtr hwnd)
    {
        var sb = new System.Text.StringBuilder(256);
        GetWindowText(hwnd, sb, sb.Capacity);
        return sb.ToString();
    }

    /// <summary>
    /// Polls until a visible top-level window belonging to <paramref name="pid"/> whose
    /// title CONTAINS <paramref name="titleSubstring"/> appears.
    /// Returns <c>IntPtr.Zero</c> on timeout.
    /// </summary>
    public static IntPtr WaitForWindowWithTitle(int pid, string titleSubstring,
        TimeSpan timeout, int pollMs = 300)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            EnumWindows((hwnd, _) =>
            {
                if (IsWindowVisible(hwnd))
                {
                    GetWindowThreadProcessId(hwnd, out uint wPid);
                    if ((int)wPid == pid)
                    {
                        var title = GetWindowTitle(hwnd);
                        if (title.Contains(titleSubstring, StringComparison.OrdinalIgnoreCase))
                        {
                            _foundHwnd = hwnd;
                            return false;
                        }
                    }
                }
                return true;
            }, IntPtr.Zero);

            if (_foundHwnd != IntPtr.Zero)
            {
                var result = _foundHwnd;
                _foundHwnd = IntPtr.Zero;
                return result;
            }
            Thread.Sleep(pollMs);
        }
        return IntPtr.Zero;
    }

    /// <summary>Wrap a raw HWND as a FlaUI AutomationElement.</summary>
    public static AutomationElement? FromHandle(AutomationBase automation, IntPtr hwnd)
    {
        try { return automation.FromHandle(hwnd); }
        catch { return null; }
    }
}
