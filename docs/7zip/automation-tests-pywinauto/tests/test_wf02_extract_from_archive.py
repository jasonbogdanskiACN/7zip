# test_wf02_extract_from_archive.py
#
# WF-02: Extract from Archive — pywinauto automation test
#
# Vertical slice: docs/7zip/vertical-slice-documentation/vertical-slices/
#                 phase-7-workflow-extract-from-archive.md
#
# Section 3 entry point : toolbar button "Extract" (toolbar[1] in ToolbarWindow32)
# Section 6 mutations   : "Extract Files" dialog opens; output-directory Edit is
#                         pre-populated; OK and Cancel present.
#
# Test strategy:
#   1. Create a ZIP archive using Python's zipfile module (no 7z.exe required).
#   2. Navigate the 7-Zip FM address bar to the archive's directory.
#   3. Ctrl+A to select all items (the archive).
#   4. click_input() the Extract toolbar button.
#   5. wait_for_app_dialog() to detect the Extract dialog.
#   6. Assert key dialog controls exist.
#   7. click_input() Cancel — no extraction should occur.

import os
import time
import zipfile

from PIL import ImageGrab
from pywinauto.application import Application

from conftest import kill_app, screenshots_dir

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEST_DIR      = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "7zip-pw-wf02")
ARCHIVE_PATH  = os.path.join(TEST_DIR, "test-archive.zip")
OUTPUT_BASE   = os.path.join(os.path.dirname(__file__), "..")
WORKFLOW_NAME = "wf02-extract-from-archive"


# ---------------------------------------------------------------------------
# Shared helpers (mirrors wf01)
# ---------------------------------------------------------------------------
def wait_for_app_dialog(app, main_hwnd: int, timeout: float = 8.0, poll: float = 0.2):
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
class TestWF02ExtractFromArchive:

    def setup_method(self, _):
        cfg_path = os.path.join(os.path.dirname(__file__), "..", "app-config.json")
        import json
        with open(cfg_path) as f:
            self.cfg = json.load(f)

        kill_app(self.cfg["ExePath"])

        # Test fixture: create a ZIP archive with one file inside
        os.makedirs(TEST_DIR, exist_ok=True)
        if os.path.exists(ARCHIVE_PATH):
            os.remove(ARCHIVE_PATH)
        with zipfile.ZipFile(ARCHIVE_PATH, "w") as zf:
            zf.writestr("sample.txt",
                "Hello from 7-Zip pywinauto test — WF-02 Extract from Archive")
        assert os.path.exists(ARCHIVE_PATH), f"Test fixture: archive not created at {ARCHIVE_PATH}"

        self.extract_dir = os.path.join(TEST_DIR, "extracted")
        if os.path.exists(self.extract_dir):
            import shutil
            shutil.rmtree(self.extract_dir)

        self.scr_dir = screenshots_dir(OUTPUT_BASE, WORKFLOW_NAME)

    def teardown_method(self, _):
        try:
            self.app.kill()
        except Exception:
            pass
        kill_app(self.cfg["ExePath"])

    def test_extract_button_opens_extract_dialog(self):
        """
        WF-02 Section 6: clicking Extract opens the Extract dialog with
        an output-directory Edit pre-populated, plus OK and Cancel buttons.
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

        # ── Click Extract toolbar button (toolbar[1]) ─────────────────────
        tb = win.children(class_name="ToolbarWindow32")[0]
        extract_btn = tb.button("Extract")
        screenshot(win, self.scr_dir, "02-before-extract.png")
        extract_btn.click_input()

        # ── Wait for Extract dialog using app.windows() ───────────────────
        dlg_wrapper = wait_for_app_dialog(self.app, main_hwnd, timeout=8)
        print(f"  [dialog] hwnd=0x{dlg_wrapper.handle:X}" if dlg_wrapper else "  [dialog] NOT FOUND")
        assert dlg_wrapper is not None, "Extract dialog did not appear within 8 seconds"

        dlg_title = dlg_wrapper.window_text()
        print(f"  [dialog] title='{dlg_title}'")
        screenshot(dlg_wrapper, self.scr_dir, "03-dialog-open.png")

        # Section 6: dialog title indicates Extract operation
        assert any(kw in dlg_title for kw in ("Extract", "7-Zip")), \
            f"Dialog title '{dlg_title}' does not indicate an Extract operation"

        # Re-wrap for child_window() support
        dlg = self.app.window(handle=dlg_wrapper.handle)

        # Section 6: output directory Edit is present and non-empty
        all_edits = dlg_wrapper.children(class_name="Edit")
        print(f"  [dialog] Edit controls: {len(all_edits)}")
        assert len(all_edits) > 0, "Expected at least one Edit control in the Extract dialog"

        output_edit = next(
            (e for e in all_edits if e.window_text().strip()),
            None
        )
        assert output_edit is not None, "Output directory Edit appears to be empty"
        print(f"  [dialog] output dir = '{output_edit.window_text()}'")

        # Section 6: OK and Cancel buttons exist
        cancel_btn = dlg.child_window(title="Cancel", class_name="Button")
        ok_btn     = dlg.child_window(title="OK",     class_name="Button")
        assert cancel_btn.exists(), "Cancel button not found in Extract dialog"
        assert ok_btn.exists(),     "OK button not found in Extract dialog"

        # Trace assertion
        trace_log = self.cfg.get("TraceLog", "")
        if trace_log and os.path.exists(os.path.dirname(trace_log)):
            found = read_trace(trace_log, "WF-EXTRACT triggered")
            print(f"  [trace] 'WF-EXTRACT triggered' found: {found}")
            assert found, "Trace phrase 'WF-EXTRACT triggered' not found in log"

        # ── Dismiss with Cancel — no extraction should occur ─────────────
        cancel_btn.click_input()
        time.sleep(0.5)
        screenshot(win, self.scr_dir, "04-after-cancel.png")

        assert not os.path.exists(self.extract_dir), \
            "Extract directory should NOT exist after clicking Cancel"
        print("  [result] no extraction occurred - OK")
