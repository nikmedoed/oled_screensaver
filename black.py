import logging
import sys
import threading
import tkinter as tk

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item, Menu

from ScreenSaver import ScreenLocker

# Developer mode: reduce timeout to 5 seconds if 'dev' is in args
DEV_MODE = 'dev' in sys.argv
TIMEOUT = 5 if DEV_MODE else 120

# Logging setup
logging.basicConfig(
    level=logging.DEBUG if DEV_MODE else logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def create_tray_image():
    """Creates a simple tray icon (e.g., a white-filled circle)."""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, width - 8, height - 8), fill="white")
    return image


def quit_app(icon, item):
    """Exits application via tray icon menu."""
    logging.debug("Exiting application via tray icon.")
    icon.stop()
    root.after(0, root.destroy)


def toggle_auto_lock(icon, item):
    """Toggles auto-lock from tray menu."""
    locker.toggle_auto_lock()


def auto_lock_label(_item):
    return "Disable auto-lock" if locker.auto_lock_enabled else "Enable auto-lock"


def setup_tray():
    """Sets up and runs the tray icon with dynamic menu."""
    image = create_tray_image()
    menu = Menu(
        item(auto_lock_label, toggle_auto_lock),
        item('Exit', quit_app)
    )
    tray_icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)
    tray_icon.run()


# --- Application startup ---
if __name__ == "__main__":
    if DEV_MODE:
        logging.info("Running in developer mode")
    root = tk.Tk()
    root.withdraw()
    locker = ScreenLocker(root, timeout_seconds=TIMEOUT)
    logging.debug("ScreenLocker instance created. Starting main loop.")

    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    root.mainloop()
