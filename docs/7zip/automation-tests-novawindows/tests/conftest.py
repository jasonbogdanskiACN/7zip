# tests/conftest.py — shared helpers for NovaWindows 7-Zip tests

import json
import os
import subprocess
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "app-config.json")


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def kill_app(exe_path: str) -> None:
    name = os.path.basename(exe_path)
    subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True, check=False)
    time.sleep(0.4)


def screenshots_dir(output_base: str, workflow_name: str) -> str:
    path = os.path.join(output_base, "screenshots", workflow_name)
    os.makedirs(path, exist_ok=True)
    return path
