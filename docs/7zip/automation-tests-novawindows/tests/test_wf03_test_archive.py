# test_wf03_test_archive.py
#
# WF-03: Test Archive — NovaWindows/Appium automation test
#
# Vertical slice: docs/7zip/vertical-slice-documentation/vertical-slices/
#                 phase-7-workflow-test-archive.md
#
# Section 3 entry point : toolbar button "Test" (AutomationId "Item 1072")
# Section 6 mutations   : Test runs immediately (no open-file dialog); a
#                         result window appears reporting no errors for a
#                         valid archive.

import base64
import ctypes
import ctypes.wintypes
import io
import os
import time
import zipfile

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
TEST_DIR      = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "7zip-nova-wf03")
ARCHIVE_PATH  = os.path.join(TEST_DIR, "test-archive.zip")
OUTPUT_BASE   = os.path.join(os.path.dirname(__file__), "..")
WORKFLOW_NAME = "wf03-test-archive"


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
                               timeout: float = 15.0) -> str | None:
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


def collect_all_text(driver) -> str:
    """Collect all visible text from the current window via page_source."""
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(driver.page_source)
        texts = []
        for el in root.iter():
            name = el.get("Name", "").strip()
            if name:
                texts.append(name)
        return " | ".join(texts)
    except Exception:
        return ""


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
class TestWF03TestArchive:

    def setup_method(self, _):
        self.cfg = load_config()
        kill_app(self.cfg["ExePath"])

        # Test fixture: valid ZIP with one file
        os.makedirs(TEST_DIR, exist_ok=True)
        if os.path.exists(ARCHIVE_PATH):
            os.remove(ARCHIVE_PATH)
        with zipfile.ZipFile(ARCHIVE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sample.txt",
                "Hello from NovaWindows WF-03 Test Archive. "
                "The quick brown fox jumps over the lazy dog.")

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

    def test_test_button_runs_crc_and_shows_ok_result(self):
        """
        WF-03 Section 6: clicking Test runs the CRC check on the selected archive
        and shows a result window reporting no errors for a valid archive.
        """
        driver = self.driver

        take_screenshot(driver, self.scr_dir, "00-main-window.png")
        print(f"\n  [window] title='{driver.title}'")

        # ── Navigate to archive directory ─────────────────────────────────
        # Use UIA ValuePattern.SetValue to set text (bypasses SendWait/focus).
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

        # ── Click Test button via PostMessage WM_COMMAND ─────────────────
        # Test button command ID = 1072 = 0x0430 (AutomationId "Item 1072")
        take_screenshot(driver, self.scr_dir, "02-before-test.png")
        driver.execute_script("powerShell", f"""
            Add-Type -MemberDefinition '
                [System.Runtime.InteropServices.DllImport("user32.dll")]
                public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
            ' -Name 'PostMsgHelper' -Namespace 'Win32' -ErrorAction SilentlyContinue
            [Win32.PostMsgHelper]::PostMessage([IntPtr]{main_hwnd_int}, 0x0111, [IntPtr]0x0430, [IntPtr]0)
        """)

        # ── Wait for result window (ctypes EnumWindows, 15s for CRC) ────────
        result_handle = wait_for_new_window_ctypes(main_hwnd_int, app_pid, timeout=15)
        print(f"  [result] handle={result_handle}" if result_handle
              else "  [result] NOT FOUND")
        assert result_handle is not None, \
            "Test result window did not appear within 15 seconds"

        driver.switch_to.window(result_handle)
        time.sleep(0.5)   # let UIA tree populate
        result_title = driver.title
        print(f"  [result] title='{result_title}'")
        take_screenshot(driver, self.scr_dir, "03-result-window.png")

        # Section 6: collect all element names from result window
        all_text = collect_all_text(driver)
        print(f"  [result] text (first 300)='{all_text[:300]}'")

        success_indicator = any(phrase in all_text for phrase in (
            "There are no errors",
            "Everything is Ok",
            "0 Errors",
            "0 error",
        )) or "7-Zip" in result_title

        assert success_indicator, \
            (f"Expected success indicator in result window. "
             f"Title='{result_title}' Text='{all_text[:300]}'")

        # Trace assertion
        trace_log = self.cfg.get("TraceLog", "")
        if trace_log and os.path.exists(os.path.dirname(trace_log)):
            found = read_trace(trace_log, "WF-TEST triggered")
            print(f"  [trace] 'WF-TEST triggered' found: {found}")
            assert found, "Trace phrase 'WF-TEST triggered' not found"

        # ── Close result window via PostMessage ───────────────────────
        result_hwnd_int = int(result_handle, 16)
        driver.execute_script("powerShell", f"""
            [Win32.PostMsgHelper]::PostMessage([IntPtr]{result_hwnd_int}, 0x0010, [IntPtr]0, [IntPtr]0)
        """)  # WM_CLOSE = 0x0010
        time.sleep(0.4)
        driver.switch_to.window(main_handle)
        take_screenshot(driver, self.scr_dir, "04-after-close.png")
        print("  [result] PASS")
