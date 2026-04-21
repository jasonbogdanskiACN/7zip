#!/usr/bin/env python3
"""
test_workflow_template.py — pytest template for the 7zip-slice-verify-novawindows skill.

Copy to docs/<project>/automation-tests-novawindows/tests/
and rename to test_wf<NN>_<name>.py.

Fill in each TODO and remove all instructional comments once working.

Prerequisites:
  - Appium server running: .\\scripts\\start_appium.ps1 -Background
  - pip install Appium-Python-Client pytest Pillow requests
"""

import base64
import io
import json
import os
import subprocess
import time

import pytest
import requests
from appium import webdriver
from appium.options.windows import WindowsOptions
from appium.webdriver.common.appiumby import AppiumBy

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "app-config.json")
OUTPUT_BASE = os.path.join(os.path.dirname(__file__), "..")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def wait_for_appium(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"{url}/status", timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def kill_app(exe_path: str) -> None:
    """Kill all processes matching the exe basename."""
    name = os.path.basename(exe_path)
    subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True, check=False)
    time.sleep(0.4)


def wait_for_new_window(driver, known_handles: set, timeout: float = 8.0) -> str | None:
    """
    Poll driver.window_handles until a new handle appears.
    Returns the first new handle string, or None on timeout.

    If NovaWindows misses owned Win32 dialogs here (same root cause as FlaUI
    issue #6), use wait_for_new_window_powershell() as a fallback.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = set(driver.window_handles)
        new = current - known_handles
        if new:
            return next(iter(new))
        time.sleep(0.2)
    return None


def wait_for_new_window_powershell(driver, main_handle_str: str,
                                    timeout: float = 8.0) -> str | None:
    """
    Fallback dialog detection: enumerate windows in the target process via
    PowerShell, bypassing the UIA FindAllChildren gap.
    Requires Appium server started with --allow-insecure power_shell.
    """
    # Convert Appium window handle (hex string like "0x1A2B3C") to int for comparison
    script = r"""
param([string]$mainHandle)
$mainInt = [Convert]::ToInt64($mainHandle, 16)
$result = @()
foreach ($p in Get-Process 7zFM -ErrorAction SilentlyContinue) {
    if ([int64]$p.MainWindowHandle -ne $mainInt -and
        $p.MainWindowHandle -ne [IntPtr]::Zero) {
        $result += '0x{0:X}' -f [int64]$p.MainWindowHandle
    }
}
$result -join ','
"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            out = driver.execute_script("powerShell", script)
            if out and out.strip():
                handles = [h.strip() for h in out.strip().split(",") if h.strip()]
                if handles:
                    return handles[0]
        except Exception:
            pass
        time.sleep(0.2)
    return None


def take_screenshot(driver, workflow_name: str, filename: str) -> None:
    if not HAVE_PIL:
        return
    try:
        scr_dir = os.path.join(OUTPUT_BASE, "screenshots", workflow_name)
        os.makedirs(scr_dir, exist_ok=True)
        b64 = driver.get_screenshot_as_base64()
        img = Image.open(io.BytesIO(base64.b64decode(b64)))
        img.save(os.path.join(scr_dir, filename))
    except Exception as e:
        print(f"  [screenshot] {filename} failed: {e}")


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
# Test class
# ---------------------------------------------------------------------------
# TODO: rename class to match the vertical slice, e.g. TestWF01AddToArchive

class TestWF00Template:
    """
    Template test class. Each test method creates its own Appium session
    (fresh app launch) for isolation.
    """

    cfg: dict
    driver: webdriver.Remote
    WORKFLOW_NAME = "wf00-template"  # TODO: set to e.g. "wf01-add-to-archive"

    def setup_method(self, _):
        """Kill stale processes, verify Appium, create session."""
        self.cfg = load_config()

        kill_app(self.cfg["ExePath"])

        appium_url = self.cfg.get("AppiumUrl", "http://127.0.0.1:4723")
        assert wait_for_appium(appium_url, timeout=15), \
            f"Appium server at {appium_url} is not responding. " \
            "Start it with: .\\scripts\\start_appium.ps1 -Background"

        opts = WindowsOptions()
        opts.app             = self.cfg["ExePath"]
        opts.automation_name = "NovaWindows"

        self.driver = webdriver.Remote(appium_url, options=opts)
        time.sleep(1.5)

    def teardown_method(self, _):
        """Close the Appium session (kills the app by default)."""
        try:
            self.driver.quit()
        except Exception:
            pass
        kill_app(self.cfg["ExePath"])

    # ── Happy-path test ───────────────────────────────────────────────────
    def test_happy_path(self):
        """
        TODO: Replace with the actual workflow name.

        Standard structure for a toolbar-driven 7-Zip FM workflow:
          1. Navigate via address bar
          2. Select file(s) — Ctrl+A on SysListView32
          3. Snapshot window handles
          4. Click toolbar button (windows: click — non-blocking)
          5. Wait for dialog/result window (driver.window_handles)
          6. Switch context & assert dialog controls
          7. Dismiss (Cancel or Close)
          8. Optional: assert trace log
          9. Screenshot at each step
        """

        take_screenshot(self.driver, self.WORKFLOW_NAME, "00-main-window.png")
        print(f"\n  [window] title='{self.driver.title}'")

        # ── Step 1: Navigate via address bar ─────────────────────────────
        # TODO: set TEST_DIR to a known path with test fixtures
        TEST_DIR = r"C:\Temp\7zip-nova-wf00"
        os.makedirs(TEST_DIR, exist_ok=True)

        # Address bar Edit has AutomationId "1003" in 7-Zip FM
        addr_edit = self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, "1003")
        addr_edit.clear()
        addr_edit.send_keys(TEST_DIR + "\n")
        time.sleep(1.5)

        take_screenshot(self.driver, self.WORKFLOW_NAME, "01-navigated.png")
        print(f"  [addrEdit] navigated to: {TEST_DIR}")

        # ── Step 2: Select all (Ctrl+A on file list) ──────────────────────
        # SysListView32 has no AutomationId in 7-Zip FM; use class name.
        lv = self.driver.find_element(AppiumBy.CLASS_NAME, "SysListView32")
        self.driver.execute_script("windows: setFocus", lv)
        self.driver.execute_script("windows: keys", {
            "actions": [
                {"virtualKeyCode": 0x11, "down": True},   # Ctrl
                {"virtualKeyCode": 0x41},                  # A
                {"virtualKeyCode": 0x11, "down": False},
            ]
        })
        time.sleep(0.3)

        # ── Step 3: Snapshot handles before clicking ──────────────────────
        known_handles = set(self.driver.window_handles)
        main_handle   = self.driver.current_window_handle
        print(f"  [probe] main handle={main_handle}  known windows={len(known_handles)}")

        # ── Step 4: Click toolbar button (non-blocking) ───────────────────
        # CRITICAL: use windows: click (SendInput), NOT element.click()
        # element.click() may use InvokePattern / WM_COMMAND which blocks on
        # modal dialogs — same root cause as FlaUI issue #5.
        #
        # TODO: replace "Add" with the target button name from window-map.txt
        btn = self.driver.find_element(AppiumBy.NAME, "Add")
        take_screenshot(self.driver, self.WORKFLOW_NAME, "02-before-click.png")
        self.driver.execute_script("windows: click", {"elementId": btn.id})

        # ── Step 5: Wait for dialog window ───────────────────────────────
        # Try driver.window_handles first (Appium's UIA enumeration).
        # If it misses the owned dialog, use wait_for_new_window_powershell() below.
        dlg_handle = wait_for_new_window(self.driver, known_handles, timeout=8)

        if dlg_handle is None:
            print("  [dialog] Not found via window_handles — falling back to PowerShell")
            dlg_handle = wait_for_new_window_powershell(
                self.driver, main_handle, timeout=8
            )

        print(f"  [dialog] handle={dlg_handle}" if dlg_handle else "  [dialog] NOT FOUND")
        assert dlg_handle is not None, "Expected dialog/result window did not appear"

        # ── Step 6: Switch context & assert dialog controls ───────────────
        self.driver.switch_to.window(dlg_handle)
        dlg_title = self.driver.title
        print(f"  [dialog] title='{dlg_title}'")
        take_screenshot(self.driver, self.WORKFLOW_NAME, "03-dialog-open.png")

        # TODO: add assertions for dialog controls
        # Examples:
        #   path_edit = self.driver.find_element(AppiumBy.CLASS_NAME, "Edit")
        #   assert path_edit.get_attribute("Value.Value"), "Path Edit is empty"
        #
        #   cancel = self.driver.find_element(AppiumBy.NAME, "Cancel")
        #   ok     = self.driver.find_element(AppiumBy.NAME, "OK")
        #   assert cancel.is_enabled()
        #   assert ok.is_enabled()

        pass  # TODO: add assertions

        # ── Step 7: Dismiss ───────────────────────────────────────────────
        # TODO: click Cancel (or Close) using windows: click
        # cancel = self.driver.find_element(AppiumBy.NAME, "Cancel")
        # self.driver.execute_script("windows: click", {"elementId": cancel.id})
        # time.sleep(0.5)

        # Switch back to main window
        self.driver.switch_to.window(main_handle)
        take_screenshot(self.driver, self.WORKFLOW_NAME, "04-after-dismiss.png")

        # ── Step 8: Trace assertion (optional) ────────────────────────────
        trace_log = self.cfg.get("TraceLog", "")
        if trace_log and os.path.exists(os.path.dirname(trace_log)):
            # TODO: replace with actual trace phrase
            # found = read_trace(trace_log, "WF-ADD triggered")
            # print(f"  [trace] found: {found}")
            # assert found, "Expected trace phrase not found"
            pass

        print("  [result] test complete")
