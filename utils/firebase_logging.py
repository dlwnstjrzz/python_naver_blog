"""Utility helpers to append Firebase-related diagnostics to a shared log file."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Final

_LOG_FILENAME: Final[str] = "firebase_debug.log"


def _resolve_logs_dir() -> str:
    """Return absolute path to the logs directory for dev and frozen builds."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(__file__))
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def append_firebase_log(message: str) -> None:
    """Append a timestamped log line to firebase_debug.log."""
    logs_dir = _resolve_logs_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(logs_dir, _LOG_FILENAME)
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] {message}\n")
