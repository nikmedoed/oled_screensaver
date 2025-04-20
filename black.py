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


def toggle_auto_lock(icon, item):
    locker.toggle_auto_lock()


def auto_lock_delay(time):
    logging.debug("Auto lock delay for item {}".format(item))


def format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} minutes"
    hours = minutes // 60
    return f"{hours} hour{'s' if hours > 1 else ''}"


items = [
    item(format_duration(m), lambda icon, item: auto_lock_delay(m * 1000 * (1 if DEV_MODE else 60)))
    for m in durations_in_minutes
]


def setup_tray():
    """
    Sets up tray icon and menu.
    On Windows, binds left click to toggle lock.
    On other systems, uses 'on_clicked'.
    """
    image = create_tray_image()
    menu = Menu(
        item("Toggle Lock", toggle_lock_menu, default=True),
        item(auto_lock_label, toggle_auto_lock),
        Menu.SEPARATOR,
        item("Disable auto-lock on", None, enabled=False),
        *items,
        Menu.SEPARATOR,
        item("Exit", quit_app)
    )
    tray_icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)

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
