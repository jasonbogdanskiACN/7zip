#!/usr/bin/env python3
"""
probe_window.py — Stage 2 probe for the 7zip-slice-verify-novawindows skill.

Connects to a running Appium server, launches the target application via a
NovaWindows session, dumps the full UIA accessibility tree, and writes:

  <output>/window-map.xml          — raw Appium page_source (UIA XML)
  <output>/window-map.txt          — human-readable element summary
  <output>/app-config.json         — constants for test scripts
  <output>/screenshots/probe/00-probe-idle.png  — baseline screenshot

Usage:
  # Appium server must already be running:
  #   .\\scripts\\start_appium.ps1 -Background
  #
  python probe_window.py --exe "C:\\\\path\\\\to\\\\7zFM.exe" --output "docs/7zip/automation-tests-novawindows"
  python probe_window.py --exe "..." --output "..." --screenshot --port 4724
"""

import argparse
import base64
import io
import json
import os
import sys
import time
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
try:
    from appium import webdriver
    from appium.options.windows import WindowsOptions
    from appium.webdriver.common.appiumby import AppiumBy
except ImportError:
    sys.exit("Appium-Python-Client not installed. Run: pip install Appium-Python-Client")

try:
    import requests
except ImportError:
    sys.exit("requests not installed. Run: pip install requests")

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def wait_for_appium(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/status", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def xml_to_lines(node: ET.Element, depth: int, lines: list[str]) -> None:
    """Recursively walk the UIA XML tree and append human-readable lines."""
    tag    = node.tag
    name   = node.get("Name", "")
    aid    = node.get("AutomationId", "")
    cls    = node.get("ClassName", "")
    bounds = node.get("Bounds", "")

    indent = "  " * depth
    label  = f"{indent}<{tag}>"
    if name:  label += f'  Name="{name}"'
    if aid:   label += f'  AutomationId="{aid}"'
    if cls:   label += f'  ClassName="{cls}"'
    if bounds: label += f"  Bounds={bounds}"
    lines.append(label)

    for child in node:
        xml_to_lines(child, depth + 1, lines)


# ---------------------------------------------------------------------------
# Main probe
# ---------------------------------------------------------------------------
def probe(exe_path: str, output_dir: str, appium_url: str,
          take_screenshot: bool) -> None:

    print(f"[probe] Exe    : {exe_path}")
    print(f"[probe] Appium : {appium_url}")

    # ── Wait for Appium server ────────────────────────────────────────────
    print(f"[probe] Waiting for Appium server...")
    if not wait_for_appium(appium_url, timeout=30):
        sys.exit(f"[probe] Appium server at {appium_url} did not respond within 30 s.\n"
                 "       Start it with: .\\scripts\\start_appium.ps1 -Background")
    print(f"[probe] Appium ready.")

    # ── Create session ────────────────────────────────────────────────────
    opts = WindowsOptions()
    opts.app             = exe_path
    opts.automation_name = "NovaWindows"

    try:
        driver = webdriver.Remote(appium_url, options=opts)
    except Exception as e:
        sys.exit(f"[probe] Session creation failed: {e}")

    print(f"[probe] Session ID: {driver.session_id}")
    time.sleep(1.5)

    # ── Get page source (full UIA XML) ────────────────────────────────────
    try:
        page_xml = driver.page_source
    except Exception as e:
        driver.quit()
        sys.exit(f"[probe] page_source failed: {e}")

    os.makedirs(output_dir, exist_ok=True)

    xml_path = os.path.join(output_dir, "window-map.xml")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(page_xml)
    print(f"[probe] Written : {xml_path}  ({len(page_xml)} bytes)")

    # ── Parse XML to human-readable text ─────────────────────────────────
    lines: list[str] = []
    lines.append("# window-map.txt — NovaWindows probe output")
    lines.append(f"# App    : {exe_path}")
    lines.append(f"# Appium : {appium_url}")
    lines.append("")
    try:
        root = ET.fromstring(page_xml)
        xml_to_lines(root, 0, lines)
    except ET.ParseError as e:
        lines.append(f"[XML parse error: {e}]")

    txt_path = os.path.join(output_dir, "window-map.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[probe] Written : {txt_path}  ({len(lines)} lines)")

    # ── Summary stats ─────────────────────────────────────────────────────
    named    = [l for l in lines if 'Name="' in l and l.strip()]
    with_aid = [l for l in lines if 'AutomationId="' in l and '""' not in l]
    print(f"[probe] Elements: {len(named)} named, {len(with_aid)} with AutomationId")

    # Show toolbar buttons
    buttons = [l for l in lines if "<Button>" in l or "<ToolBar>" in l]
    if buttons:
        print("[probe] Toolbar/Button elements:")
        for b in buttons[:20]:
            print(f"         {b.strip()}")

    # ── app-config.json ───────────────────────────────────────────────────
    config = {
        "ExePath":   exe_path,
        "AppiumUrl": appium_url,
        "TraceLog":  "C:\\Temp\\7z_trace.log",
    }
    cfg_path = os.path.join(output_dir, "app-config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    print(f"[probe] Written : {cfg_path}")

    # ── Screenshot ────────────────────────────────────────────────────────
    if take_screenshot:
        if not HAVE_PIL:
            print("[probe] Skipping screenshot: Pillow not installed (pip install Pillow)")
        else:
            scr_dir = os.path.join(output_dir, "screenshots", "probe")
            os.makedirs(scr_dir, exist_ok=True)
            scr_path = os.path.join(scr_dir, "00-probe-idle.png")
            try:
                b64 = driver.get_screenshot_as_base64()
                img = Image.open(io.BytesIO(base64.b64decode(b64)))
                img.save(scr_path)
                print(f"[probe] Screenshot: {scr_path}")
            except Exception as e:
                print(f"[probe] Screenshot failed: {e}")

    # ── Done ──────────────────────────────────────────────────────────────
    driver.quit()
    print("[probe] Session closed.")
    print()
    print(f"Next steps:")
    print(f"  1. Review {txt_path}")
    print(f"  2. Write tests in {output_dir}/tests/")
    print(f"  3. Run: pytest {output_dir}/tests/ -v --tb=short")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NovaWindows probe — Stage 2 app discovery"
    )
    parser.add_argument("--exe",        required=True,
                        help="Full path to the application executable")
    parser.add_argument("--output",     required=True,
                        help="Directory to write window-map and app-config")
    parser.add_argument("--port",       default=4723, type=int,
                        help="Appium server port (default: 4723)")
    parser.add_argument("--screenshot", action="store_true",
                        help="Capture baseline screenshot")
    args = parser.parse_args()

    probe(
        exe_path       = os.path.abspath(args.exe),
        output_dir     = os.path.abspath(args.output),
        appium_url     = f"http://127.0.0.1:{args.port}",
        take_screenshot= args.screenshot,
    )
