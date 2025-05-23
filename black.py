from src.error_logging import init_error_logging

init_error_logging()

import logging
import os

LOG_FILE = os.path.expanduser('~/.screensaver_full.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger('pystray').setLevel(logging.DEBUG)

import platform
import tkinter as tk
from datetime import datetime

import pystray
from pystray import MenuItem as item, Menu
from config import DEV_MODE, TIMEOUT, SECONDS_IN_MINUTE, durations_in_minutes, PID_FILE
from src.ScreenSaver import ScreenLocker
from src.utils import format_duration, create_tray_image, kill_previous_instance


class TrayApp:
    def __init__(self):
        if DEV_MODE:
            logging.info("Running in developer mode")

        self.last_delay_label: str = ""
        self.root = tk.Tk()
        self.root.withdraw()
        self.locker = ScreenLocker(self.root, timeout_seconds=TIMEOUT)
        logging.debug("ScreenLocker initialized.")

        self.icon: pystray.Icon | None = None

        self._setup_tray()
        self.icon.run_detached()

    def _setup_tray(self):
        image = create_tray_image()

        delay_items = [item(format_duration(m), self._make_delay_action(m))
                       for m in durations_in_minutes]

        menu = Menu(
            item(lambda _: f"Auto-lock {'ENABLED' if self.locker.auto_lock_enabled else 'DISABLED'}",
                 None, enabled=False),
            item(lambda _: (
                f">> until "
                f"{datetime.fromtimestamp(self.locker.delayed_until).strftime('%H:%M:%S')} "
                f"({self.last_delay_label})"
            ), None, enabled=False, visible=lambda _: self.locker.delayed_until is not None),
            item("Toggle Lock manually", self._toggle, default=True),
            item(lambda _: "Disable auto-lock" if self.locker.auto_lock_enabled else "Enable auto-lock",
                 lambda _,: self.locker.toggle_auto_lock()),
            Menu.SEPARATOR,
            *delay_items,
            Menu.SEPARATOR,
            item("Exit", self._quit)
        )

        self.icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)
        if platform.system() == "Windows":
            self.icon._on_left_up = self._toggle
        else:
            self.icon.on_clicked = self._toggle


    def _make_delay_action(self, minutes):
        def _action(icon, item):
            self.last_delay_label = item.text
            self.locker.disable_auto_lock_for(minutes * SECONDS_IN_MINUTE)
            logging.debug(f"Auto-lock paused for {minutes} minutes")

        return _action

    def _toggle(self, icon, item=None):
        self.root.after(0, self.locker.toggle_lock)

    def _quit(self, icon, item):
        logging.info("Exiting...")
        self.locker.stop_listeners()
        icon.stop()
        self.root.after(0, self.root.destroy)
        # cleanup PID file
        try:
            os.remove(PID_FILE)
        except Exception:
            pass


if __name__ == "__main__":
    kill_previous_instance()
    app = TrayApp()
    app.root.mainloop()
