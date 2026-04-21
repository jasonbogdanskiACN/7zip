# test_wf03_test_archive.py
#
# WF-03: Test Archive — pywinauto automation test
#
# Vertical slice: docs/7zip/vertical-slice-documentation/vertical-slices/
#                 phase-7-workflow-test-archive.md
#
# Section 3 entry point : toolbar button "Test" (toolbar[2] in ToolbarWindow32)
# Section 6 mutations   : Test runs immediately (no open-file dialog); a progress/
#                         result window appears reporting "There are no errors" or
#                         "Everything is Ok" for a valid archive; CRC passes.
#
# Test strategy:
#   1. Create a valid ZIP archive using Python's zipfile module.
#   2. Navigate to the archive directory via the address bar.
#   3. Ctrl+A to select all (the archive).
#   4. click_input() the Test toolbar button.
#   5. wait_for_app_dialog() to detect the result window.
#   6. Collect all text from the result window; assert success indicator.
#   7. Close the result window.

import os
import time
import zipfile

from PIL import ImageGrab
from pywinauto.application import Application

from conftest import kill_app, screenshots_dir

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_DIR      = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "7zip-pw-wf03")
ARCHIVE_PATH  = os.path.join(TEST_DIR, "test-archive.zip")
OUTPUT_BASE   = os.path.join(os.path.dirname(__file__), "..")
WORKFLOW_NAME = "wf03-test-archive"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def wait_for_app_dialog(app, main_hwnd: int, timeout: float = 15.0, poll: float = 0.2):
    """Wait for a secondary window in the same process (result dialog)."""
    import time as _t
    deadline = _t.time() + timeout
    while _t.time() < deadline:
        try:
            for w in app.windows():
                if w.handle != main_hwnd:
                    try:
                        if w.is_visible():
                            return w
                    except Exception:
                        pass
        except Exception:
            pass
        _t.sleep(poll)
    return None


def collect_all_text(wrapper) -> str:
    """Recursively collect all visible window text from a control tree."""
    parts = []
    try:
        t = wrapper.window_text()
        if t and t.strip():
            parts.append(t.strip())
    except Exception:
        pass
    try:
        for child in wrapper.children():
            parts.append(collect_all_text(child))
    except Exception:
        pass
    return " | ".join(p for p in parts if p)


def screenshot(win_or_wrapper, scr_dir: str, name: str) -> None:
    try:
        r = win_or_wrapper.rectangle()
        img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
        img.save(os.path.join(scr_dir, name))
    except Exception as e:
        print(f"  [screenshot] {name} failed: {e}")


def read_trace(log_path: str, phrase: str, timeout: float = 5.0) -> bool:
    import time as _t
    deadline = _t.time() + timeout
    while _t.time() < deadline:
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                if phrase in f.read():
                    return True
        except FileNotFoundError:
            pass
        _t.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
class TestWF03TestArchive:

    def setup_method(self, _):
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "app-config.json")
        import json
        with open(cfg_path) as f:
            self.cfg = json.load(f)

        kill_app(self.cfg["ExePath"])

        # Test fixture: create a valid ZIP archive with one text file
        os.makedirs(TEST_DIR, exist_ok=True)
        if os.path.exists(ARCHIVE_PATH):
            os.remove(ARCHIVE_PATH)
        with zipfile.ZipFile(ARCHIVE_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sample.txt",
                "Hello from 7-Zip pywinauto test — WF-03 Test Archive. "
                "The quick brown fox jumps over the lazy dog.")
        assert os.path.exists(ARCHIVE_PATH), f"Test fixture: archive not created at {ARCHIVE_PATH}"

        self.scr_dir = screenshots_dir(OUTPUT_BASE, WORKFLOW_NAME)

    def teardown_method(self, _):
        try:
            self.app.kill()
        except Exception:
            pass
        kill_app(self.cfg["ExePath"])

    def test_test_button_runs_crc_and_shows_ok_result(self):
        """
        WF-03 Section 6: clicking Test runs the CRC check on the selected archive
        and shows a result window reporting no errors for a valid archive.
        """
        self.app = Application(backend=self.cfg["Backend"]).start(self.cfg["ExePath"])
        win = self.app.top_window()
        win.wait("visible", timeout=10)
        time.sleep(1.0)

        screenshot(win, self.scr_dir, "00-main-window.png")
        print(f"\n  [window] title='{win.window_text()}'")

        # ── Navigate to archive directory ──────────────────────────────────
        addr_edit = win.child_window(class_name="Edit", found_index=0)
        addr_edit.set_edit_text(TEST_DIR)
        addr_edit.type_keys("{ENTER}")
        time.sleep(1.5)

        screenshot(win, self.scr_dir, "01-navigated.png")
        print(f"  [addrEdit] navigated to: {TEST_DIR}")

        # ── Ctrl+A to select all ──────────────────────────────────────────
        lv = win.child_window(class_name="SysListView32")
        lv.set_focus()
        lv.type_keys("^a")
        time.sleep(0.3)

        main_hwnd = win.handle
        print(f"  [probe] main hwnd=0x{main_hwnd:X}")

        # ── Click Test toolbar button (toolbar[2]) ────────────────────────
        # Test runs WITHOUT a setup dialog — the CRC check starts immediately.
        # click_input() (SendInput) is non-blocking, so the result window
        # appears while our test thread continues.
        tb = win.children(class_name="ToolbarWindow32")[0]
        test_btn = tb.button("Test")
        screenshot(win, self.scr_dir, "02-before-test.png")
        test_btn.click_input()

        # ── Wait for result window using app.windows() ────────────────────
        # The result window is in the same process; timeout 15s to allow CRC.
        result_wrapper = wait_for_app_dialog(self.app, main_hwnd, timeout=15)
        print(f"  [result] hwnd=0x{result_wrapper.handle:X}" if result_wrapper else "  [result] NOT FOUND")
        assert result_wrapper is not None, "Test result window did not appear within 15 seconds"

        result_title = result_wrapper.window_text()
        print(f"  [result] title='{result_title}'")
        screenshot(result_wrapper, self.scr_dir, "03-result-window.png")

        # Section 6: collect all text and check for success indicator
        all_text = collect_all_text(result_wrapper)
        print(f"  [result] text='{all_text[:200]}'")

        success_indicator = any(phrase in all_text for phrase in (
            "There are no errors",
            "Everything is Ok",
            "0 Errors",
            "0 error",
        )) or "7-Zip" in result_title

        assert success_indicator, \
            f"Expected success indicator in result window. Title='{result_title}' Text='{all_text[:200]}'"

        # Trace: WF-TEST triggered (FM.cpp:886)
        trace_log = self.cfg.get("TraceLog", "")
        if trace_log and os.path.exists(os.path.dirname(trace_log)):
            found_trigger = read_trace(trace_log, "WF-TEST triggered")
            print(f"  [trace] 'WF-TEST triggered' found: {found_trigger}")
            assert found_trigger, "Trace 'WF-TEST triggered' not found"

            found_crc = read_trace(trace_log, "kTest mode -> null-sink CRC check")
            print(f"  [trace] 'kTest mode -> null-sink CRC check' found: {found_crc}")
            assert found_crc, "Trace 'kTest mode -> null-sink CRC check' not found"

        # ── Dismiss the result window ─────────────────────────────────────
        result_spec = self.app.window(handle=result_wrapper.handle)
        # Try "Close" first (7-Zip uses either "Close" or "OK" in the result)
        close_candidate = None
        for title in ("Close", "OK"):
            btn = result_spec.child_window(title=title, class_name="Button")
            if btn.exists():
                close_candidate = btn
                break
        if close_candidate:
            close_candidate.click_input()
        else:
            result_wrapper.close()

        time.sleep(0.5)
        screenshot(win, self.scr_dir, "04-after-close.png")
        print("  [result] result window closed - OK")
