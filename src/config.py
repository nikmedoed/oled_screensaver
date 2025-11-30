import json
import logging
import os
import platform
import signal
import sys
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any

from src.localization import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    detect_system_language,
    normalize_language_code,
)

CURSOR_HIDE_CHECK_TIMEOUT = 5000  # ms
MIN_TOGGLE_INTERVAL = 0.3  # s Prevents back-to-back toggles when detecting activity to avoid visible flicker
DEV_MODE = 'dev' in sys.argv
TIMEOUT = 5 if DEV_MODE else 120
SECONDS_IN_MINUTE = 1 if DEV_MODE else 60
durations_in_minutes = [15, 30, 60, 120, 180, 240, 480, 720]

# Visual activity detection (screenshots)
VISUAL_START_DELAY = max(1, TIMEOUT // 2)  # seconds before first snapshot after inactivity
VISUAL_CHECK_INTERVAL = VISUAL_START_DELAY  # seconds between snapshots while idle
VISUAL_CHANGE_THRESHOLD = 0.015  # 1.5% difference counts as movement
# Percentage offsets for screenshot region; allows excluding taskbar or title areas
VISUAL_SAMPLE_MARGINS = {
    "top": 0.06,
    "bottom": 0.08,
    "left": 0.05,
    "right": 0.05,
}

logging.basicConfig(
    level=logging.DEBUG if DEV_MODE else logging.INFO,
    format='%(asctime)s: %(message)s',
    datefmt='%H:%M:%S'
)
logging.getLogger("PIL").setLevel(logging.WARNING)

signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGBREAK, signal.SIG_IGN)
MOUSE_CHECK_TIMEOUT = 2000
PID_FILE = os.path.expanduser("~/.screensaver_tray.pid")


class SettingsStore:
    """Simple JSON-backed settings registry with sane defaults."""

    timeout_seconds = TIMEOUT
    mouse_check_ms = MOUSE_CHECK_TIMEOUT
    cursor_hide_ms = CURSOR_HIDE_CHECK_TIMEOUT
    pause_minutes = list(durations_in_minutes)
    visual_threshold = VISUAL_CHANGE_THRESHOLD
    visual_margins = deepcopy(VISUAL_SAMPLE_MARGINS)
    visual_monitor_enabled = True
    language = DEFAULT_LANGUAGE

    def __init__(self):
        self.path = Path(os.environ.get(
            "APPDATA",
            Path.home() / ("AppData/Roaming" if platform.system() == "Windows" else ".config"))
        ) / f"black_screensaver{'_dev' if DEV_MODE else ''}" / "settings.json"

        settings_data: Dict[str, Any] | None = None
        file_exists = self.path.exists()
        try:
            if file_exists:
                with self.path.open("r", encoding="utf-8") as fh:
                    settings_data = json.load(fh)
                if isinstance(settings_data, dict):
                    self.update(settings_data)
        except FileNotFoundError:
            pass
        except Exception as exc:
            print(f"Failed to load settings file {self.path}: {exc}")

        if not file_exists:
            self.language = detect_system_language(DEFAULT_LANGUAGE)

    def save(self) -> None:
        """Persists current settings to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump({
                "timeout_seconds": self.timeout_seconds,
                "mouse_check_ms": self.mouse_check_ms,
                "cursor_hide_ms": self.cursor_hide_ms,
                "pause_minutes": list(self.pause_minutes),
                "visual_threshold": self.visual_threshold,
                "visual_margins": self.visual_margins,
                "visual_monitor_enabled": self.visual_monitor_enabled,
                "language": self.language,
            }, fh, indent=2, ensure_ascii=True)

    def update(self, values: Dict[str, Any]) -> None:
        if not isinstance(values, dict):
            return
        for key, value in values.items():
            if not hasattr(self, key):
                continue
            if key == "language":
                normalized = normalize_language_code(value if isinstance(value, str) else None)
                setattr(self, key, normalized if normalized in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE)
            else:
                setattr(self, key, value)
