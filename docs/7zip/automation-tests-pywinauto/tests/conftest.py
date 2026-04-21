# tests/conftest.py — shared pytest fixtures for pywinauto 7-Zip tests
#
# Provides:
#   app_config  — dict loaded from app-config.json
#   screenshots_dir(workflow_name) — helper, creates dir, returns path

import json
import os
import subprocess
import time

import pytest


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "app-config.json")


@pytest.fixture(scope="session")
def app_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def kill_app(exe_path: str) -> None:
    """Kill all processes matching the exe basename."""
    name = os.path.basename(exe_path)
    subprocess.run(["taskkill", "/F", "/IM", name], capture_output=True, check=False)
    time.sleep(0.4)


def screenshots_dir(output_base: str, workflow_name: str) -> str:
    path = os.path.join(output_base, "screenshots", workflow_name)
    os.makedirs(path, exist_ok=True)
    return path
