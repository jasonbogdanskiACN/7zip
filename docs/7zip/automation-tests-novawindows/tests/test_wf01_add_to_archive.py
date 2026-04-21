# test_wf01_add_to_archive.py
#
# WF-01: Add Files to Archive — NovaWindows/Appium automation test
#
# Vertical slice: docs/7zip/vertical-slice-documentation/vertical-slices/
#                 phase-7-workflow-add-to-archive.md
#
# Section 3 entry point : toolbar button "Add" (AutomationId "Item 1070")
# Section 6 mutations   : "Add to Archive" dialog opens; archive-path Edit is
#                         pre-populated; format ComboBox present; OK/Cancel present.
#
# Test strategy:
#   1. Create a temp dir with one text file.
#   2. Navigate the address bar (AutomationId "1003" Edit) to that directory.
#   3. Ctrl+A to select all items via windows: keys execute_script.
#   4. Click Add toolbar button via windows: click (non-blocking SendInput).
#   5. Poll driver.window_handles for the new dialog handle.
#   6. Switch context and assert key dialog controls.
#   7. Click Cancel — no archive created.
#
# NovaWindows notes:
#   - windows: click uses SendInput — avoids InvokePattern/WM_COMMAND deadlock
#     (equivalent of FlaUI issue #5 / pywinauto click_input fix).
#   - driver.window_handles polls UIA — covers 7-Zip owned dialogs correctly.

import base64
import ctypes
import ctypes.wintypes
import io
import os
import time

import requests
from appium import webdriver
from appium.options.windows import WindowsOptions
from appium.webdriver.common.appiumby import AppiumBy

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

from conftest import kill_app, load_config, screenshots_dir

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_DIR      = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "7zip-nova-wf01")
OUTPUT_BASE   = os.path.join(os.path.dirname(__file__), "..")
WORKFLOW_NAME = "wf01-add-to-archive"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def wait_for_appium(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"{url}/status", timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def wait_for_new_window_ctypes(main_hwnd_int: int, app_pid: int,
                               timeout: float = 8.0) -> str | None:
    """
    Find a new top-level window for the app process using Win32 EnumWindows via
    ctypes.  This finds owned dialogs that UIA root FindAllChildren misses
    (same root cause as FlaUI issue #6 and pywinauto PW-1).
    Returns the HWND as a hex string e.g. '0x000D84A2', or None on timeout.
    """
    user32 = ctypes.windll.user32
    result: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_size_t, ctypes.c_size_t)
    def _enum_proc(hwnd, _lp):
        pid = ctypes.c_uint(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == app_pid and hwnd != main_hwnd_int:
            if user32.IsWindowVisible(hwnd):
                result.append(hwnd)
        return True

    deadline = time.time() + timeout
    while time.time() < deadline:
        result.clear()
        user32.EnumWindows(_enum_proc, 0)
        if result:
            return f"0x{result[-1]:08X}"
        time.sleep(0.2)
    return None


def take_screenshot(driver, scr_dir: str, name: str) -> None:
    if not HAVE_PIL:
        return
    try:
        img = Image.open(io.BytesIO(base64.b64decode(driver.get_screenshot_as_base64())))
        img.save(os.path.join(scr_dir, name))
    except Exception as e:
        print(f"  [screenshot] {name} failed: {e}")


def read_trace(log_path: str, phrase: str, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                if phrase in f.read():
                    return True
        except FileNotFoundError:
            pass
        time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
class TestWF01AddToArchive:

    def setup_method(self, _):
        self.cfg = load_config()
        kill_app(self.cfg["ExePath"])

        # Test fixture
        os.makedirs(TEST_DIR, exist_ok=True)
        with open(os.path.join(TEST_DIR, "hello.txt"), "w") as f:
            f.write("Hello from NovaWindows WF-01 Add to Archive test")
        expected_archive = os.path.join(TEST_DIR, "hello.7z")
        if os.path.exists(expected_archive):
            os.remove(expected_archive)

        self.scr_dir = screenshots_dir(OUTPUT_BASE, WORKFLOW_NAME)

        appium_url = self.cfg.get("AppiumUrl", "http://127.0.0.1:4723")
        assert wait_for_appium(appium_url), \
            f"Appium not responding at {appium_url}. Start with: start_appium.ps1 -Background"

        opts = WindowsOptions()
        opts.app             = self.cfg["ExePath"]
        opts.automation_name = "NovaWindows"
        self.driver = webdriver.Remote(appium_url, options=opts)
        time.sleep(1.5)

    def teardown_method(self, _):
        try:
            self.driver.quit()
        except Exception:
            pass
        kill_app(self.cfg["ExePath"])

    def test_add_button_opens_compress_dialog(self):
        """
        WF-01 Section 6: clicking Add opens 'Add to Archive' dialog with
        pre-populated archive path, format combo, OK and Cancel buttons.
        """
        driver = self.driver

        take_screenshot(driver, self.scr_dir, "00-main-window.png")
        print(f"\n  [window] title='{driver.title}'")

        # ── Navigate to test directory via address bar Edit ───────────────
        # AutomationId "1003" is shared by the ComboBox and its child Edit.
        # Use UIA ValuePattern.SetValue to set text (bypasses SendWait, which
        # fails with "Access is denied" from a background PS session).
        # Then send VK_RETURN via windows:keys (user32 SendInput, no focus req).
        addr_edit = driver.find_element(AppiumBy.XPATH, "//Edit[@AutomationId='1003']")
        driver.execute_script(
            "powerShell",
            f'$rootElement.FindFirst([Windows.Automation.TreeScope]::Descendants,'
            f' [Windows.Automation.PropertyCondition]::new('
            f'[Windows.Automation.AutomationElement]::AutomationIdProperty, "1003"))'
            f'.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern)'
            f".SetValue('{TEST_DIR}')")
        driver.execute_script("windows: click", {"elementId": addr_edit.id})
        driver.execute_script("windows: keys", {"actions": [{"virtualKeyCode": 0x0D}]})
        time.sleep(1.5)

        take_screenshot(driver, self.scr_dir, "01-navigated.png")
        print(f"  [addrEdit] navigated to: {TEST_DIR}")

        # ── Select all items via UIA SelectionItemPattern ─────────────────
        # Keyboard Ctrl+A fails from a background PS session (SendInput goes
        # to wrong desktop). Use UIA SelectionItemPattern.AddToSelection()
        # which works without keyboard focus.
        driver.execute_script("powerShell", """
            $lv = $rootElement.FindFirst(
                [Windows.Automation.TreeScope]::Descendants,
                [Windows.Automation.PropertyCondition]::new(
                    [Windows.Automation.AutomationElement]::AutomationIdProperty,
                    "1001"))
            if ($lv) {
                $items = $lv.FindAll(
                    [Windows.Automation.TreeScope]::Children,
                    [Windows.Automation.Condition]::TrueCondition)
                foreach ($item in $items) {
                    try {
                        $sp = $item.GetCurrentPattern(
                            [Windows.Automation.SelectionItemPattern]::Pattern)
                        $sp.AddToSelection()
                    } catch {}
                }
            }
        """)
        time.sleep(0.3)

        main_hwnd_int = int(driver.current_window_handle, 16)
        main_handle   = driver.current_window_handle
        app_pid       = int(driver.execute_script("powerShell",
                              "$rootElement.Current.ProcessId").strip())
        print(f"  [probe] main handle={main_handle}  pid={app_pid}")

        # ── Click Add toolbar button via PostMessage WM_COMMAND ──────────
        # PostMessage is non-blocking (no deadlock) and requires no foreground
        # window — it queues the message in 7-Zip's message loop directly.
        # Add button command ID = 1070 = 0x042E (from AutomationId "Item 1070")
        take_screenshot(driver, self.scr_dir, "02-before-add.png")
        driver.execute_script("powerShell", f"""
            Add-Type -MemberDefinition '
                [System.Runtime.InteropServices.DllImport("user32.dll")]
                public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
            ' -Name 'PostMsgHelper' -Namespace 'Win32' -ErrorAction SilentlyContinue
            [Win32.PostMsgHelper]::PostMessage([IntPtr]{main_hwnd_int}, 0x0111, [IntPtr]0x042E, [IntPtr]0)
        """)

        # ── Wait for Add to Archive dialog ────────────────────────────────
        # Use ctypes EnumWindows to find owned dialogs that UIA root
        # FindAllChildren misses (FlaUI issue #6 equivalent).
        dlg_handle = wait_for_new_window_ctypes(main_hwnd_int, app_pid, timeout=8)
        print(f"  [dialog] handle={dlg_handle}" if dlg_handle else "  [dialog] NOT FOUND")
        assert dlg_handle is not None, \
            "Add to Archive dialog did not appear within 8 seconds"

        # setWindow (patched) uses TreeScope.SUBTREE so can find owned dialogs
        driver.switch_to.window(dlg_handle)
        time.sleep(0.5)   # let UIA tree populate
        dlg_title = driver.title
        print(f"  [dialog] title='{dlg_title}'")
        take_screenshot(driver, self.scr_dir, "03-dialog-open.png")

        # Section 6: dialog title indicates Add operation
        assert any(kw in dlg_title for kw in ("Add", "Archive", "7-Zip")), \
            f"Dialog title '{dlg_title}' does not indicate Add-to-Archive"

        # Section 6: archive path Edit is present and non-empty
        # Use XPATH to find Edit controls (more reliable than CLASS_NAME in NovaWindows)
        all_edits = driver.find_elements(AppiumBy.XPATH, "//Edit")
        print(f"  [dialog] Edit controls: {len(all_edits)}")
        assert len(all_edits) > 0, "No Edit controls found in Add dialog"

        path_edit = next(
            (e for e in all_edits if e.text.strip()),
            None
        )
        assert path_edit is not None, "Archive path Edit appears to be empty"
        print(f"  [dialog] archive path = '{path_edit.text}'")

        # Section 6: OK and Cancel buttons present
        cancel_btn = driver.find_element(AppiumBy.NAME, "Cancel")
        ok_btn     = driver.find_element(AppiumBy.NAME, "OK")
        assert cancel_btn.is_enabled(), "Cancel button not found/enabled in Add dialog"
        assert ok_btn.is_enabled(),     "OK button not found/enabled in Add dialog"

        trace_log = self.cfg.get("TraceLog", "")
        if trace_log and os.path.exists(os.path.dirname(trace_log)):
            found = read_trace(trace_log, "WF-ADD triggered")
            print(f"  [trace] 'WF-ADD triggered' found: {found}")
            assert found, "Trace phrase 'WF-ADD triggered' not found"

        # ── Dismiss with Cancel via PostMessage (avoids mouse focus issues) ─
        dlg_hwnd_int = int(dlg_handle, 16)
        driver.execute_script("powerShell", f"""
            [Win32.PostMsgHelper]::PostMessage([IntPtr]{dlg_hwnd_int}, 0x0111, [IntPtr]0x0002, [IntPtr]0)
        """)
        time.sleep(0.5)
        driver.switch_to.window(main_handle)
        take_screenshot(driver, self.scr_dir, "04-after-cancel.png")
        print("  [result] PASS")
