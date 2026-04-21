#!/usr/bin/env python3
"""
probe_window.py — Stage 2 probe for the 7zip-slice-verify-pywinauto skill.

Launches the target application, walks its accessibility tree using pywinauto,
and writes:
  <output>/window-map.txt      — full control tree (class, title, auto_id, rect)
  <output>/app-config.json     — constants for test scripts to read
  <output>/screenshots/probe/00-probe-idle.png  — baseline screenshot (with --screenshot)

Usage:
  python probe_window.py --exe "C:\\path\\to\\7zFM.exe" --output "docs/7zip/automation-tests-pywinauto"
  python probe_window.py --exe "C:\\path\\to\\7zFM.exe" --output "..." --screenshot --backend uia
"""

import argparse
import json
import os
import sys
import time

# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------
try:
    from pywinauto.application import Application
    from pywinauto import Desktop
except ImportError:
    sys.exit("pywinauto is not installed. Run: pip install pywinauto")

try:
    from PIL import ImageGrab
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


# ---------------------------------------------------------------------------
# Tree walking
# ---------------------------------------------------------------------------
def _safe(fn, default=""):
    try:
        return fn()
    except Exception:
        return default


def walk_element(el, depth: int, lines: list[str]) -> None:
    """Recursively walk the control tree and append lines to `lines`."""
    indent = "  " * depth
    ct   = _safe(lambda: el.element_info.control_type, "?")
    name = _safe(lambda: el.element_info.name,         "")
    aid  = _safe(lambda: el.element_info.automation_id,"")
    cls  = _safe(lambda: el.element_info.class_name,   "")
    rect = _safe(lambda: el.element_info.rectangle,    None)
    rect_str = f"({rect.left},{rect.top})-({rect.right},{rect.bottom})" if rect else ""
    label  = f"{indent}{ct}"
    if name:  label += f'  Name="{name}"'
    if aid:   label += f'  AutomationId="{aid}"'
    if cls:   label += f'  ClassName="{cls}"'
    if rect_str: label += f"  Rect={rect_str}"
    lines.append(label)
    try:
        for child in el.children():
            walk_element(child, depth + 1, lines)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main probe
# ---------------------------------------------------------------------------
def probe(exe_path: str, output_dir: str, backend: str, take_screenshot: bool) -> None:
    print(f"[probe] Launching: {exe_path}")
    print(f"[probe] Backend  : {backend}")

    app = Application(backend=backend).start(exe_path)
    time.sleep(2.0)

    # Connect to main window — 7-Zip title contains the current directory
    # We match broadly with a regex to get whatever window the app opens.
    from pywinauto.findwindows import ElementNotFoundError
    try:
        win = app.top_window()
        win.wait("visible", timeout=10)
    except Exception as e:
        app.kill()
        sys.exit(f"[probe] Main window not found: {e}")

    win_title  = _safe(lambda: win.window_text(), "<unknown>")
    win_handle = _safe(lambda: win.handle, 0)
    pid        = app.process

    print(f"[probe] Window   : hwnd=0x{win_handle:X}  title='{win_title}'  pid={pid}")

    # ── Walk control tree ──────────────────────────────────────────────────
    lines: list[str] = []
    lines.append(f"# window-map.txt — pywinauto probe output")
    lines.append(f"# App : {exe_path}")
    lines.append(f"# PID : {pid}   hwnd: 0x{win_handle:X}")
    lines.append(f"# Backend: {backend}")
    lines.append("")

    try:
        walk_element(win.wrapper_object(), 0, lines)
    except Exception as e:
        lines.append(f"[walk error: {e}]")

    os.makedirs(output_dir, exist_ok=True)
    map_path = os.path.join(output_dir, "window-map.txt")
    with open(map_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[probe] Written  : {map_path}  ({len(lines)} lines)")

    # ── Count named elements as summary ──────────────────────────────────
    named = [l for l in lines if 'Name="' in l]
    print(f"[probe] Elements : {len(lines)} total, {len(named)} named")

    # ── Toolbar button inventory ──────────────────────────────────────────
    print("[probe] Toolbar buttons found:")
    for line in lines:
        if "ToolBar" in line or ('Button' in line and 'Name="' in line):
            print(f"         {line.strip()}")

    # ── Write app-config.json ─────────────────────────────────────────────
    config = {
        "ExePath":         exe_path,
        "MainWindowTitle": win_title,
        "Backend":         backend,
        "TraceLog":        "C:\\Temp\\7z_trace.log",
    }
    config_path = os.path.join(output_dir, "app-config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"[probe] Written  : {config_path}")

    # ── Screenshot ────────────────────────────────────────────────────────
    if take_screenshot:
        if not HAVE_PIL:
            print("[probe] Skipping screenshot: Pillow not installed (pip install Pillow)")
        else:
            scr_dir = os.path.join(output_dir, "screenshots", "probe")
            os.makedirs(scr_dir, exist_ok=True)
            scr_path = os.path.join(scr_dir, "00-probe-idle.png")
            try:
                win.set_focus()
                time.sleep(0.2)
                rect = win.rectangle()
                img = ImageGrab.grab(
                    bbox=(rect.left, rect.top, rect.right, rect.bottom)
                )
                img.save(scr_path)
                print(f"[probe] Screenshot: {scr_path}")
            except Exception as e:
                print(f"[probe] Screenshot failed: {e}")

    # ── Done ──────────────────────────────────────────────────────────────
    app.kill()
    print("[probe] Done — app closed.")
    print()
    print("Next step: run setup_pywinauto_tests.py to scaffold the test suite,")
    print(f"           then write tests in {output_dir}/tests/")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="pywinauto probe — Stage 2 app discovery")
    parser.add_argument("--exe",        required=True,  help="Full path to the application executable")
    parser.add_argument("--output",     required=True,  help="Directory to write window-map.txt and app-config.json")
    parser.add_argument("--backend",    default="win32", choices=["win32","uia"], help="pywinauto backend (default: win32)")
    parser.add_argument("--screenshot", action="store_true", help="Capture baseline screenshot")
    args = parser.parse_args()

    probe(
        exe_path      = os.path.abspath(args.exe),
        output_dir    = os.path.abspath(args.output),
        backend       = args.backend,
        take_screenshot = args.screenshot,
    )
