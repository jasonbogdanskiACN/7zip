# NovaWindows Driver Patterns Reference

API and interaction patterns for the `appium-novawindows-driver` used in the
7zip-slice-verify-novawindows skill.

**Driver repo**: https://github.com/AutomateThePlanet/appium-novawindows-driver  
**Appium docs**: https://appium.io/docs/en/latest/  
**Version in use**: 1.3.x (Appium 2/3, PowerShell backend)

---

## 1. Prerequisites

```powershell
# Install Appium globally (requires Node.js 18+)
npm install -g appium

# Install the NovaWindows driver
appium driver install --source=npm appium-novawindows-driver

# Verify
appium driver list --installed    # should list novawindows with version

# Python client
pip install Appium-Python-Client pytest Pillow
```

---

## 2. Starting the Appium Server

```powershell
# Foreground (for debugging)
appium --port 4723

# Background (for CI / test runs)
Start-Process -NoNewWindow -FilePath "appium" -ArgumentList "--port 4723" -RedirectStandardOutput "appium.log"
```

The server is ready when its log shows:
```
Appium REST http interface listener started on 0.0.0.0:4723
```

Poll for readiness in Python:
```python
import requests, time

def wait_for_appium(url="http://127.0.0.1:4723", timeout=30.0):
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
```

---

## 3. Session Creation

```python
from appium import webdriver
from appium.options.windows import WindowsOptions

opts = WindowsOptions()
opts.app               = r"C:\dev\7zip\traced-build\7zFM.exe"
opts.automation_name   = "NovaWindows"    # required
# opts.app_top_level_window = hex(hwnd)  # attach to existing window

driver = webdriver.Remote("http://127.0.0.1:4723", options=opts)
```

**Capabilities reference** (key subset):

| Capability | Value | Notes |
|---|---|---|
| `platformName` | `Windows` | Case-insensitive |
| `automationName` | `NovaWindows` | Case-insensitive |
| `app` | absolute exe path | Or AUMID for UWP |
| `appTopLevelWindow` | `hex(hwnd)` | Attach to running window |
| `shouldCloseApp` | `true` / `false` | Close on `driver.quit()` (default true) |
| `appArguments` | `"arg1 arg2"` | Optional launch args |
| `appWorkingDir` | `r"C:\path"` | Optional working dir |

---

## 4. Element Location

NovaWindows (like WinAppDriver) uses UI Automation under the hood.

```python
from appium.webdriver.common.appiumby import AppiumBy

# By AutomationId (most stable — matches UIA AutomationId property)
el = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "1003")

# By ClassName
toolbar = driver.find_element(AppiumBy.CLASS_NAME, "ToolbarWindow32")

# By Name (window text)
btn = driver.find_element(AppiumBy.NAME, "Add")

# By XPath (UIA tree attributes — XPath 1.0 only)
btn = driver.find_element(AppiumBy.XPATH, '//Button[@Name="Add"]')

# Find multiple elements
all_btns = driver.find_elements(AppiumBy.XPATH, '//Button')

# Wait for element
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
el = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((AppiumBy.NAME, "Add to Archive"))
)
```

**7-Zip FM locators** (from window-map.xml probe output):

| Control | Locator strategy | Value |
|---|---|---|
| Main window | `name` | (contains current directory path) |
| Address bar Edit | `accessibility id` | `1003` |
| Main toolbar | `class name` | `ToolbarWindow32` |
| Add button | `name` | `Add` |
| Extract button | `name` | `Extract` |
| Test button | `name` | `Test` |
| File list | `class name` | `SysListView32` |
| Status bar | `class name` | `msctls_statusbar32` |

---

## 5. Interactions

### 5.1 Safe (non-blocking) click for toolbar buttons

**Critical**: `element.click()` may use `InvokePattern` internally which sends
`WM_COMMAND` — this **blocks** the calling thread when the target button opens a
modal dialog on the UI thread. This is the same deadlock as FlaUI issue #5.

Use `windows: click` execute_script instead — it calls `SendInput` (mouse injection)
which is non-blocking:

```python
# NON-BLOCKING — use this for toolbar buttons that open dialogs
driver.execute_script("windows: click", {"elementId": el.id})

# EQUIVALENT with coordinates (if element ID is unavailable)
rect = el.rect   # {"x": 10, "y": 100, "width": 42, "height": 46}
cx   = rect["x"] + rect["width"] // 2
cy   = rect["y"] + rect["height"] // 2
driver.execute_script("windows: click", {"x": cx, "y": cy})
```

### 5.2 Keyboard input

```python
# Type text into a focused element
el.send_keys("C:\\path\\to\\dir")
el.send_keys("\n")               # Enter key

# Key combinations via windows: keys execute_script
driver.execute_script("windows: keys", {
    "actions": [
        {"virtualKeyCode": 0x11, "down": True},    # Ctrl down
        {"virtualKeyCode": 0x41},                   # A
        {"virtualKeyCode": 0x11, "down": False},   # Ctrl up
    ]
})
```

Common virtual key codes:
| Key | Code |
|---|---|
| Enter | `0x0D` |
| Ctrl | `0x11` |
| Shift | `0x10` |
| Alt | `0x12` |
| A | `0x41` |
| F5 | `0x74` |

### 5.3 Other interactions

```python
# Windows UIA patterns via execute_script
driver.execute_script("windows: invoke",       element)        # InvokePattern
driver.execute_script("windows: setFocus",     element)        # SetFocus
driver.execute_script("windows: setValue",     element, "txt") # ValuePattern
driver.execute_script("windows: expand",       element)        # ExpandPattern
driver.execute_script("windows: toggle",       element)        # TogglePattern
driver.execute_script("windows: select",       element)        # SelectionPattern
```

---

## 6. Window / Dialog Handling

Modal dialogs appear as **new window handles** in `driver.window_handles`. The
Appium session keeps a list of top-level UIA windows.

```python
import time

def wait_for_new_window(driver, known_handles: set, timeout: float = 8.0) -> str | None:
    """
    Poll driver.window_handles until a new handle appears.
    Returns the new handle string, or None on timeout.

    Note: driver.window_handles uses UIA GetDesktop().FindAllChildren() internally.
    For owned modal dialogs in Win32/MFC apps, they *should* appear here because
    NovaWindows registers them as top-level windows. However, if they are missed,
    fall back to wait_for_new_window_powershell() below.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = set(driver.window_handles)
        new = current - known_handles
        if new:
            return next(iter(new))
        time.sleep(0.2)
    return None


def wait_for_new_window_powershell(driver, main_hwnd_hex: str,
                                    timeout: float = 8.0) -> str | None:
    """
    Fallback: use a PowerShell script via execute_script to enumerate windows
    in the target process and find a new HWND. Returns the hex HWND string.

    Use this if wait_for_new_window() misses owned dialogs (same root cause as
    FlaUI issue #6 — UIA FindAllChildren misses some owned windows).
    """
    import time as _t
    script = f"""
$mainHandle = [IntPtr]{main_hwnd_hex}
$pid = (Get-Process | Where-Object {{ $_.MainWindowHandle -eq $mainHandle }}).Id
if (-not $pid) {{ return $null }}
$result = @()
[System.Diagnostics.Process]::GetProcessById($pid).Refresh()
foreach ($p in Get-Process -Id $pid) {{
    if ($p.MainWindowHandle -ne [IntPtr]::Zero -and
        $p.MainWindowHandle -ne $mainHandle) {{
        $result += [string][int]$p.MainWindowHandle
    }}
}}
$result -join ','
"""
    deadline = _t.time() + timeout
    while _t.time() < deadline:
        try:
            out = driver.execute_script("powerShell", script)
            if out and out.strip():
                return out.strip().split(",")[0]
        except Exception:
            pass
        _t.sleep(0.2)
    return None


# --- Usage pattern ---
main_handle = driver.current_window_handle
known_handles = set(driver.window_handles)

# Click toolbar button (non-blocking)
driver.execute_script("windows: click", {"elementId": add_btn.id})

# Wait for dialog
dlg_handle = wait_for_new_window(driver, known_handles, timeout=8)
assert dlg_handle, "Dialog did not appear"

# Switch to dialog
driver.switch_to.window(dlg_handle)
# ... interact with dialog controls ...
cancel = driver.find_element(AppiumBy.NAME, "Cancel")
driver.execute_script("windows: click", {"elementId": cancel.id})

# Switch back to main window
driver.switch_to.window(main_handle)
```

---

## 7. Screenshots

```python
from PIL import Image
import io, base64

def take_screenshot(driver, path: str) -> None:
    b64 = driver.get_screenshot_as_base64()
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    img.save(path)
```

---

## 8. Trace Log Reading

```python
def read_trace(log_path: str, phrase: str, timeout: float = 5.0) -> bool:
    import time
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
```

Python's `open()` uses shared-read by default — no special flags needed even while
7zFM.exe has the file open for writing (same advantage as pywinauto).

---

## 9. PowerShell Execution (via driver)

```python
# Run arbitrary PowerShell and get stdout back
result = driver.execute_script("powerShell", "Get-Date -Format 'yyyy-MM-dd'")

# Kill process by name
driver.execute_script("powerShell", "Stop-Process -Name 7zFM -Force -ErrorAction SilentlyContinue")

# Read a file
content = driver.execute_script("powerShell", r"Get-Content C:\Temp\7z_trace.log -Raw")
```

> **Note**: PowerShell execution must be explicitly enabled in Appium server with
> `--allow-insecure power_shell`. The `start_appium.ps1` helper enables this flag.

---

## 10. Known Failure Modes

| # | Symptom | Root Cause | Fix |
|---|---|---|---|
| 1 | `element.click()` blocks / hangs on toolbar button | `InvokePattern` / `WM_COMMAND` deadlock (FlaUI issue #5 equivalent) | Use `driver.execute_script("windows: click", {"elementId": el.id})` |
| 2 | `driver.window_handles` doesn't see the new dialog | UIA `FindAllChildren` may miss owned Win32 dialogs (FlaUI issue #6 equivalent) | Fallback to `wait_for_new_window_powershell()` |
| 3 | `ConnectionRefusedError` connecting to Appium | Appium server not running or not yet ready | Wait for `appium.log` to contain "listener started"; use `wait_for_appium()` |
| 4 | `SessionNotCreatedException: Could not find app` | Relative path passed to `app` capability | Always use absolute path |
| 5 | Old session leaks; new session can't start | Previous test left app running | `driver.quit()` in teardown; or PowerShell `Stop-Process` before session create |
| 6 | `StaleElementReferenceException` after navigation | UIA tree rebuilt after directory change | Re-find elements after each navigation |
| 7 | `send_keys` drops characters or wrong layout | Keyboard layout mismatch in PowerShell backend | Use `windows: keys` with `forceUnicode: true` for non-ASCII, or set text via `windows: setValue` |
| 8 | Dialog found but `find_element` returns wrong element | Session still on main window context | `driver.switch_to.window(dlg_handle)` before querying dialog elements |
