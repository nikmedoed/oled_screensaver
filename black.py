import logging
import platform
import tkinter as tk
from datetime import datetime

import pystray
from pystray import MenuItem as item, Menu

from ScreenSaver import ScreenLocker
from config import DEV_MODE, TIMEOUT, SECONDS_IN_MINUTE, durations_in_minutes
from utils import format_duration, create_tray_image


def quit_app(icon, item):
    logging.info("Exiting...")
    locker.stop_listeners()
    icon.stop()
    root.after(0, root.destroy)


def make_delay_action(minutes):
    def _action(icon, item):
        locker.last_delay_label = item.text
        locker.disable_auto_lock_for(minutes * SECONDS_IN_MINUTE)
        logging.debug(f"Auto-lock paused for {minutes} minutes")
        icon.update_menu()

    return _action


def _toggle_cb(icon, item=None):
    root.after(0, locker.toggle_lock)


def setup_tray():
    image = create_tray_image()

    delay_items = [item(format_duration(m), make_delay_action(m)) for m in durations_in_minutes]

    menu = Menu(
        item(lambda _: f"Auto-lock {'ENABLED' if locker.auto_lock_enabled else 'DISABLED'}",
             None, enabled=False),
        item(lambda _: (
            f">> until "
            f"{datetime.fromtimestamp(locker.delayed_until).strftime('%H:%M:%S')} "
            f"({locker.last_delay_label})"
        ),
             None, enabled=False, visible=lambda _: locker.delayed_until is not None),
        item("Toggle Lock manually", _toggle_cb, default=True),
        item(lambda _: "Disable auto-lock" if locker.auto_lock_enabled else "Enable auto-lock",
             lambda _,: locker.toggle_auto_lock()),
        Menu.SEPARATOR,
        *delay_items,
        Menu.SEPARATOR,
        item("Exit", quit_app)
    )

    tray_icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)
    if platform.system() == "Windows":
        tray_icon._on_left_up = _toggle_cb
    else:
        tray_icon.on_clicked = _toggle_cb
    tray_icon.run_detached()


if __name__ == "__main__":
    if DEV_MODE:
        logging.info("Running in developer mode")

    root = tk.Tk()
    root.withdraw()

    locker = ScreenLocker(root, timeout_seconds=TIMEOUT)
    logging.debug("ScreenLocker initialized.")

    setup_tray()
    root.mainloop()
