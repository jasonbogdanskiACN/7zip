# test_wf01_add_to_archive.py
#
# WF-01: Add Files to Archive — pywinauto automation test
#
# Vertical slice: docs/7zip/vertical-slice-documentation/vertical-slices/
#                 phase-7-workflow-add-to-archive.md
#
# Section 3 entry point : toolbar button "Add" (toolbar[0] in ToolbarWindow32)
# Section 6 mutations   : "Add to Archive" dialog opens; archive-path Edit is
#                         pre-populated; format ComboBox present; OK and Cancel present.
#
# Test strategy:
#   1. Create a temp dir with one text file.
#   2. Navigate the 7-Zip FM address bar to that directory.
#   3. Ctrl+A to select all items.
#   4. click_input() the Add toolbar button.
#   5. wait_for_new_window() to detect the Add dialog using EnumWindows.
#   6. Assert key dialog controls exist.
#   7. click_input() Cancel — no archive should be created.
#
# Comparison note:
#   FlaUI issue #6 (GetDesktop().FindAllChildren() misses owned dialogs) is
#   avoided here because wait_for_new_window() uses Desktop(backend="win32").windows()
#   which calls EnumWindows() internally.

import os
import time

import pytest
from PIL import ImageGrab
from pywinauto import Desktop
from pywinauto.application import Application

from conftest import kill_app, screenshots_dir

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_DIR      = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "7zip-pw-wf01")
OUTPUT_BASE   = os.path.join(os.path.dirname(__file__), "..")
WORKFLOW_NAME = "wf01-add-to-archive"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def wait_for_app_dialog(app, main_hwnd: int, timeout: float = 8.0, poll: float = 0.2):
    """
    Wait for a secondary window in the same process (a modal dialog).
    Uses app.windows() to stay within the app's own process rather than
    scanning the whole desktop — this is faster and avoids catching
    unrelated system windows.
    """
    import time as _time
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        try:
            wins = app.windows()
            # Look for any visible top-level window that isn't the main FM window
            for w in wins:
                if w.handle != main_hwnd:
                    try:
                        if w.is_visible():
                            return w
                    except Exception:
                        pass
        except Exception:
            pass
        _time.sleep(poll)
    return None


def screenshot(win_or_rect, scr_dir: str, name: str) -> None:
    try:
        if hasattr(win_or_rect, "rectangle"):
            r = win_or_rect.rectangle()
            img = ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom))
        else:
            img = ImageGrab.grab()
        img.save(os.path.join(scr_dir, name))
    except Exception as e:
        print(f"  [screenshot] {name} failed: {e}")


def read_trace(log_path: str, phrase: str, timeout: float = 5.0) -> bool:
    import time as _time
    deadline = _time.time() + timeout
    while _time.time() < deadline:
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                if phrase in f.read():
                    return True
        except FileNotFoundError:
            pass
        _time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
class TestWF01AddToArchive:

    def setup_method(self, _):
        """Kill stale processes and prepare test fixture."""
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "app-config.json")
        import json
        with open(cfg_path) as f:
            self.cfg = json.load(f)

        kill_app(self.cfg["ExePath"])

        # Test fixture: one text file to compress
        os.makedirs(TEST_DIR, exist_ok=True)
        self.hello_txt = os.path.join(TEST_DIR, "hello.txt")
        with open(self.hello_txt, "w") as f:
            f.write("Hello from 7-Zip pywinauto test — WF-01 Add to Archive")
        self.expected_archive = os.path.join(TEST_DIR, "hello.7z")
        if os.path.exists(self.expected_archive):
            os.remove(self.expected_archive)

        self.scr_dir = screenshots_dir(OUTPUT_BASE, WORKFLOW_NAME)

    def teardown_method(self, _):
        try:
            self.app.kill()
        except Exception:
            pass
        kill_app(self.cfg["ExePath"])

    def test_add_button_opens_compress_dialog(self):
        """
        WF-01 Section 6: clicking Add opens 'Add to Archive' dialog with
        pre-populated archive path, format combo, OK and Cancel buttons.
        """
        self.app = Application(backend=self.cfg["Backend"]).start(self.cfg["ExePath"])
        win = self.app.top_window()
        win.wait("visible", timeout=10)
        time.sleep(1.0)

        screenshot(win, self.scr_dir, "00-main-window.png")
        print(f"\n  [window] title='{win.window_text()}'")

        # ── Navigate to test directory via address bar ────────────────────
        # set_edit_text (WM_SETTEXT) sets the text; type_keys("{ENTER}") triggers navigation.
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

        # ── Click Add toolbar button ──────────────────────────────────────
        # Use click_input() — SendInput mouse click, does NOT block on modal dialog
        # (FlaUI issue #5: Invoke() uses WM_COMMAND and deadlocks; click_input avoids this)
        tb = win.children(class_name="ToolbarWindow32")[0]
        add_btn = tb.button("Add")
        screenshot(win, self.scr_dir, "02-before-add.png")
        add_btn.click_input()

        # ── Wait for Add to Archive dialog using app.windows() ───────────
        # Stays within this process — avoids the whole-desktop scan that
        # catches unrelated system windows (improved over Desktop.windows() approach).
        dlg_wrapper = wait_for_app_dialog(self.app, main_hwnd, timeout=8)
        print(f"  [dialog] hwnd=0x{dlg_wrapper.handle:X}" if dlg_wrapper else "  [dialog] NOT FOUND")
        assert dlg_wrapper is not None, "Add to Archive dialog did not appear within 8 seconds"

        dlg_title = dlg_wrapper.window_text()
        print(f"  [dialog] title='{dlg_title}'")
        screenshot(dlg_wrapper, self.scr_dir, "03-dialog-open.png")

        # Section 6: dialog title indicates Add operation
        assert any(kw in dlg_title for kw in ("Add", "Archive", "7-Zip")), \
            f"Dialog title '{dlg_title}' does not indicate an Add-to-Archive operation"

        # Re-wrap through app.window() to get a WindowSpecification with child_window() support.
        # dlg_wrapper from app.windows() is a bare HwndWrapper; app.window(handle=…) gives specs.
        dlg = self.app.window(handle=dlg_wrapper.handle)

        # Section 6: archive path Edit is present and non-empty
        all_edits = dlg_wrapper.children(class_name="Edit")
        print(f"  [dialog] Edit controls: {len(all_edits)}")
        assert len(all_edits) > 0, "Expected at least one Edit control in the Add dialog"

        # At least one Edit should be non-empty (the archive path)
        path_edit = next(
            (e for e in all_edits if e.window_text().strip()),
            None
        )
        assert path_edit is not None, "Archive path Edit appears to be empty"
        print(f"  [dialog] archive path = '{path_edit.window_text()}'")

        # Section 6: format ComboBox exists
        combos = dlg_wrapper.children(class_name="ComboBox")
        print(f"  [dialog] ComboBoxes: {len(combos)}")
        assert len(combos) > 0, "Expected format ComboBox in the Add dialog"

        # Section 6: OK and Cancel buttons exist
        cancel_btn = dlg.child_window(title="Cancel", class_name="Button")
        ok_btn     = dlg.child_window(title="OK",     class_name="Button")
        assert cancel_btn.exists(), "Cancel button not found in Add dialog"
        assert ok_btn.exists(),     "OK button not found in Add dialog"

        # Trace assertion (only if trace log exists)
        trace_log = self.cfg.get("TraceLog", "")
        if trace_log and os.path.exists(os.path.dirname(trace_log)):
            found = read_trace(trace_log, "WF-ADD triggered")
            print(f"  [trace] 'WF-ADD triggered' found: {found}")
            assert found, "Trace phrase 'WF-ADD triggered' not found in log"

        # ── Dismiss without creating archive ─────────────────────────────
        cancel_btn.click_input()
        time.sleep(0.5)
        screenshot(win, self.scr_dir, "04-after-cancel.png")

        assert not os.path.exists(self.expected_archive), \
            "Archive should NOT exist after clicking Cancel"
        print("  [result] no archive created - OK")
