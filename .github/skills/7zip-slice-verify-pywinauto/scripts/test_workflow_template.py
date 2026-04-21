#!/usr/bin/env python3
"""
test_workflow_template.py — pytest template for the 7zip-slice-verify-pywinauto skill.

Copy this file to docs/<project>/automation-tests-pywinauto/tests/
and rename it to test_wf<NN>_<name>.py.

Fill in the TODOs and remove all comments once the test is working.
"""

import json
import os
import time
import pytest

from pywinauto.application import Application
from pywinauto import Desktop

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "app-config.json")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def wait_for_new_window(known_handles: set[int], timeout: float = 5.0, poll: float = 0.2) -> object | None:
    """
    Poll Desktop(backend='win32').windows() until a new hwnd appears.
    Returns the first new window wrapper, or None on timeout.

    Uses EnumWindows internally — finds owned (modal) dialogs that UIA misses.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = {w.handle: w for w in Desktop(backend="win32").windows()}
        new = {h: w for h, w in current.items() if h not in known_handles}
        if new:
            return next(iter(new.values()))
        time.sleep(poll)
    return None


def kill_all(exe_name: str) -> None:
    """Kill all processes matching exe_name (basename, case-insensitive)."""
    import subprocess
    subprocess.run(
        ["taskkill", "/F", "/IM", exe_name],
        capture_output=True,
        check=False,
    )


def read_trace(log_path: str, expected_phrase: str, timeout: float = 5.0, poll: float = 0.2) -> bool:
    """
    Return True if expected_phrase appears in the trace log within timeout seconds.
    Python open() uses shared-read by default — no special FileShare needed.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                if expected_phrase in f.read():
                    return True
        except FileNotFoundError:
            pass
        time.sleep(poll)
    return False


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------
class TestWF00Template:
    """
    TODO: Rename this class to match the vertical slice, e.g. TestWF01AddFiles.

    This template covers the happy path for one vertical slice workflow.
    Each test method is independent; setup_method relaunches the app fresh.
    """

    cfg: dict
    app: Application
    win: object        # pywinauto WindowSpecification for the main window
    _baseline_handles: set[int]

    def setup_method(self, _method):
        """Launch app and acquire main window."""
        self.cfg = load_config()
        exe = self.cfg["ExePath"]
        exe_name = os.path.basename(exe)

        # Kill any stale processes from a previous failed run
        kill_all(exe_name)
        time.sleep(0.3)

        self.app = Application(backend=self.cfg["Backend"]).start(exe)
        self.win = self.app.top_window()
        self.win.wait("visible", timeout=10)

        # Snapshot handles BEFORE taking any action — used by wait_for_new_window
        self._baseline_handles = {w.handle for w in Desktop(backend="win32").windows()}

    def teardown_method(self, _method):
        """Kill the app regardless of test outcome."""
        try:
            self.app.kill()
        except Exception:
            pass
        # Belt-and-suspenders: force-kill by name
        kill_all(os.path.basename(self.cfg["ExePath"]))

    # ── Happy-path test ───────────────────────────────────────────────────
    def test_happy_path(self):
        """
        TODO: Replace with the actual workflow name from the vertical slice doc.

        Typical structure for a toolbar-driven workflow:
          1. Navigate to a folder / select file(s) in the ListView
          2. Click a toolbar button (use click_input(), NOT click())
          3. Interact with any dialog that appears
          4. Assert a result (new archive present, output file, etc.)
          5. Assert trace log phrase (optional)
        """

        # ── Step 1: Navigate / select items ──────────────────────────────
        # TODO: navigate to a known folder via AddressBar or menu
        # Example — type a path in the address bar:
        #
        #   addr = self.win.child_window(class_name="Edit", found_index=0)
        #   addr.set_edit_text(r"C:\TestFiles")
        #   addr.type_keys("{ENTER}")
        #   time.sleep(0.5)
        #
        # Example — click an item in the file list:
        #
        #   listview = self.win.child_window(class_name="SysListView32")
        #   listview.item("myfile.txt").click_input()

        pass   # <-- remove once step 1 is written

        # ── Step 2: Click toolbar button ─────────────────────────────────
        # IMPORTANT: always use click_input(), never click().
        # click() uses WM_COMMAND which blocks the test thread when a modal
        # dialog is shown on the same thread (same issue as FlaUI Invoke()).
        #
        # Example:
        #   toolbar = self.win.child_window(class_name="ToolbarWindow32")
        #   btn = toolbar.child_window(title="Add")   # exact title from window-map.txt
        #   btn.click_input()

        pass   # <-- remove once step 2 is written

        # ── Step 3: Handle dialog ─────────────────────────────────────────
        # Wait for a new modal dialog to appear using wait_for_new_window().
        # This uses EnumWindows and finds owned dialogs that UIA misses.
        #
        # Example:
        #   dlg_wrapper = wait_for_new_window(self._baseline_handles, timeout=5)
        #   assert dlg_wrapper is not None, "Expected dialog did not appear"
        #   dlg = Application(backend=self.cfg["Backend"]).connect(handle=dlg_wrapper.handle)
        #   dlg_win = dlg.top_window()
        #
        #   # Fill in dialog fields
        #   dlg_win.child_window(class_name="Edit").set_edit_text("output.7z")
        #   # Click OK using click_input()
        #   dlg_win.child_window(title="OK").click_input()

        pass   # <-- remove once step 3 is written

        # ── Step 4: Assert result ─────────────────────────────────────────
        # TODO: assert whatever the workflow is supposed to produce
        #
        # Examples:
        #   assert os.path.exists(r"C:\TestFiles\output.7z")
        #   assert listview.item_count() > 0

        pass   # <-- remove once step 4 is written

        # ── Step 5: Assert trace log (optional) ──────────────────────────
        # Only add this if Z7_TRACE_ENABLE was compiled in.
        #
        # Example:
        #   trace_log = self.cfg.get("TraceLog", "")
        #   if trace_log and os.path.exists(os.path.dirname(trace_log)):
        #       assert read_trace(trace_log, "CApp::OnButtonAdd"), \
        #           "Expected trace phrase not found in log"

        pass   # <-- remove once step 5 is written
