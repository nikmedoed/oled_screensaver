import logging
import platform
import sys
import threading
import tkinter as tk

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item, Menu

from ScreenSaver import ScreenLocker

DEV_MODE = 'dev' in sys.argv
TIMEOUT = 5 if DEV_MODE else 120
SECONDS_IN_MINUTE = 1 if DEV_MODE else 60

logging.basicConfig(
    level=logging.DEBUG if DEV_MODE else logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

durations_in_minutes = [15, 30, 60, 120, 180, 240, 480, 720]


def create_tray_image():
    """Creates tray icon image (white circle on black background)."""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, width - 8, height - 8), fill="white")
    return image


def quit_app(icon, item):
    logging.debug("Exiting via tray menu")
    icon.stop()
    root.after(0, root.destroy)


def toggle_lock_menu(icon, item):
    root.after(0, locker.toggle_lock)


def auto_lock_label(_item):
    return "Disable auto-lock" if locker.auto_lock_enabled else "Enable auto-lock"


def delay_label(item):
    state = locker.get_delay_label()
    if isinstance(state, bool):
        return "Auto-lock ENABLED" if state else "Auto-lock DISABLED"

    if not isinstance(state, int):
        return "N/A"
    hh = state // 3600
    mm = (state % 3600) // 60
    ss = state % 60
    return f"Auto-lock DISABLED for {hh:02d}:{mm:02d}:{ss:02d}"


def toggle_auto_lock(icon, item):
    locker.toggle_auto_lock()


def format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes // 60
    return f"{hours} hour{'s' if hours > 1 else ''}"


def auto_lock_delay(seconds: int):
    locker.disable_auto_lock_for(seconds)
    logging.debug(f"Auto lock delay for item {seconds}")


def setup_tray():
    image = create_tray_image()

    def make_delay_action(minutes):
        def action(icon, item):
            locker.disable_auto_lock_for(minutes * SECONDS_IN_MINUTE)
            logging.debug(f"Auto lock delay for {minutes} minutes")
            icon.update_menu()

        return action

    delays = [
        item(
            format_duration(m),
            make_delay_action(m)
        )
        for m in durations_in_minutes
    ]

    menu = Menu(
        item(delay_label, None,
             enabled=False, checked=lambda item: locker.auto_lock_enabled),
        item("Toggle Lock manually", toggle_lock_menu, default=True),
        item(auto_lock_label, toggle_auto_lock),
        Menu.SEPARATOR,
        *delays,
        Menu.SEPARATOR,
        item("Exit", quit_app)
    )
    tray_icon = locker.tray_icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)

    if platform.system() == "Windows":
        def on_left_up(hwnd, msg, wparam, lparam):
            root.after(0, locker.toggle_lock)

        tray_icon._on_left_up = on_left_up
    else:
        tray_icon.on_clicked = lambda icon: root.after(0, locker.toggle_lock)

    tray_icon.run()


if __name__ == "__main__":
    if DEV_MODE:
        logging.info("Running in developer mode")

    root = tk.Tk()
    root.withdraw()

    locker = ScreenLocker(root, timeout_seconds=TIMEOUT)
    logging.debug("ScreenLocker initialized.")

    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    root.mainloop()
