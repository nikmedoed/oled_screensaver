import logging
import os
import signal
import sys

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
    "top": 0.02,
    "bottom": 0.02,
    "left": 0.02,
    "right": 0.035,
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
