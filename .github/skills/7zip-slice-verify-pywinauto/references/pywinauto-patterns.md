# pywinauto Patterns — Generic Reference

pywinauto is a Python library (Apache 2.0, v0.6.x) for automating Windows GUI applications.
It wraps both Win32 API (`win32` backend) and Microsoft UIA (`uia` backend).

Project-specific identifiers (auto_id, title, class_name) come from the **probe output**
(`window-map.txt`) generated in Stage 2. Never assume them — always read the map first.

---

## 1. Backend Selection

| Backend | Use when | Notes |
|---|---|---|
| `win32` | Win32, MFC, WTL, classic WinForms, VB6 | Uses `FindWindow` / `SendMessage`; fastest for legacy apps |
| `uia` | WPF, WinUI 3, UWP, modern .NET WinForms | Uses Microsoft UIA COM; slower but richer property access |

For 7-Zip (Win32/MFC): try `win32` first. If toolbar buttons or list items are not found, try `uia`.

**Choosing between backends at runtime:**
```python
import pywinauto
from pywinauto.application import Application

# Try win32 first
app = Application(backend="win32").start(r"C:\path\to\app.exe")
# OR
app = Application(backend="uia").start(r"C:\path\to\app.exe")
```

---

## 2. Launch and Connect

```python
from pywinauto.application import Application
import time

# Launch a new instance
app = Application(backend="win32").start(r"C:\path\to\7zFM.exe")
time.sleep(1.5)   # wait for window to appear

# Connect to main window by title substring (regex supported)
win = app.window(title_re=".*7-Zip.*")
win.wait("visible", timeout=10)

# Attach to an already-running process
app = Application(backend="win32").connect(path=r"C:\path\to\7zFM.exe")

# Kill process on exit
app.kill()   # force kill
```

---

## 3. Finding Elements

Always prefer **auto_id** (AutomationId in UIA, control ID in win32). Fall back to `title`, then `class_name`.

```python
# By AutomationId / control ID (use value from window-map.txt)
btn = win.child_window(auto_id="Item 1070")        # win32 + uia

# By title (button label or tooltip)
btn = win.child_window(title="Add", control_type="Button")   # uia only
btn = win.child_window(title="Add", class_name="Button")     # win32

# By class name
listview = win.child_window(class_name="SysListView32")      # win32

# By control type (uia backend only)
from pywinauto.controls.uia_controls import ButtonWrapper
buttons = win.children(control_type="Button")

# Chain searches
toolbar = win.child_window(class_name="ToolbarWindow32")
add_btn = toolbar.child_window(title="Add")
```

---

## 4. Interacting with Controls

### Buttons
```python
btn = win.child_window(auto_id="Item 1070")
btn.click()          # left click (synchronous for win32 modal-safe variant)
btn.click_input()    # simulates real mouse input (non-blocking, like FlaUI Mouse.Click)
```

> **Important — modal dialogs**: `btn.click()` on win32 backend uses `WM_COMMAND` which
> can block on modal dialogs identically to FlaUI's `Invoke()`. Use `btn.click_input()` or
> `win32api.PostMessage()` for buttons that open dialogs. `click_input()` uses `SendInput`.

### Text / Address Bar
```python
addr = win.child_window(auto_id="1003", class_name="Edit")
addr.set_text(r"C:\Users\test\desktop")
addr.type_keys("{ENTER}")
```

### List View (SysListView32)
```python
lv = win.child_window(class_name="SysListView32")
# Select item by name (win32 backend)
lv.get_item("hello.txt").click()
# Or by index
lv.item(0).click()
```

### ComboBox
```python
cb = win.child_window(class_name="ComboBox", found_index=0)
cb.select("7z")      # select by text
cb.texts()           # list all items
```

### Keyboard
```python
from pywinauto.keyboard import send_keys
win.set_focus()
send_keys("^a")       # Ctrl+A
send_keys("{ENTER}")
send_keys("{ESC}")
```

---

## 5. Waiting

```python
# Wait for window to become visible
win.wait("visible", timeout=10)

# Wait for control to exist
ctrl = win.child_window(title_re=".*Extract.*")
ctrl.wait("visible exists", timeout=8)

# Wait for dialog (new top-level window)
import time
from pywinauto import Desktop
def wait_for_new_window(pid, before_hwnds, timeout=10, poll=0.3):
    deadline = time.time() + timeout
    while time.time() < deadline:
        desktop = Desktop(backend="win32")
        all_wins = desktop.windows()
        for w in all_wins:
            try:
                if w.process_id() == pid and w.handle not in before_hwnds:
                    return w
            except Exception:
                pass
        time.sleep(poll)
    return None
```

> **Note on modal dialog detection**: Unlike FlaUI, pywinauto's `Desktop.windows()` on the
> `win32` backend uses `EnumWindows` internally — it finds owned windows (modal dialogs) that
> UIA `GetDesktop().FindAllChildren()` misses. This is an advantage over FlaUI's UIA approach.

---

## 6. Screenshots

```python
from PIL import ImageGrab   # Pillow
import os

def screenshot(path: str, element=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if element is not None:
        rect = element.rectangle()
        img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
    else:
        img = ImageGrab.grab()
    img.save(path)
```

---

## 7. Reading the Trace Log

```python
def read_trace(log_path: str) -> list[str]:
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        return f.readlines()

def assert_trace(log_path: str, pattern: str):
    lines = read_trace(log_path)
    hits = [l for l in lines if pattern in l]
    assert hits, f"Expected trace line containing '{pattern}' — not found.\nLast 10 lines:\n" + "".join(lines[-10:])
```

> **Shared-read requirement**: 7zFM keeps `C:\Temp\7z_trace.log` open for appending. Python's
> `open()` uses `FILE_SHARE_READ | FILE_SHARE_WRITE` by default on Windows, so no special
> handling is needed. This is simpler than the C# `FileShare.ReadWrite` workaround needed in FlaUI.

---

## 8. Known Failure Modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `ElementNotFoundError` on toolbar button | Wrong backend (UIA didn't enumrate Win32 toolbar) | Switch to `win32` backend |
| `btn.click()` hangs on modal-dialog trigger | Uses `WM_COMMAND` internally — same as FlaUI `Invoke()` | Use `btn.click_input()` instead |
| `Desktop.windows()` returns empty list | pywinauto 0.6 requires `backend="win32"` in Desktop() | `Desktop(backend="win32").windows()` |
| `Application.connect()` fails after kill | Process handle not fully released | `time.sleep(1)` after `app.kill()` |
| `SysListView32` item not found by name | Title includes trailing spaces or hidden chars | Use partial match: `lv.get_item(title_re=".*hello.*")` |
| `set_text()` on address bar ignored | 7-Zip uses owner-draw ComboBox; Edit is a child | Find the Edit child of the ComboBox directly |
| Keyboard input goes to wrong window | Focus stolen between `type_keys` calls | Call `win.set_focus()` immediately before `type_keys` |
| Screenshots are black | App lost focus during capture | Call `win.set_focus()` then wait 100ms before screenshot |
