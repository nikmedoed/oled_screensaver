import logging
import platform
import sys
import threading
import tkinter as tk
from datetime import datetime

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
last_delay_label = None


def create_tray_image():
    width = height = 64
    img = Image.new('RGB', (width, height), "black")
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, width - 8, height - 8), fill="white")
    return img


def quit_app(icon, item):
    icon.stop()
    root.after(0, root.destroy)


def format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''}"


def make_delay_action(minutes):
    def _action(icon, item):
        global last_delay_label
        last_delay_label = item.text
        locker.disable_auto_lock_for(minutes * SECONDS_IN_MINUTE)
        logging.debug(f"Auto-lock paused for {minutes} minutes")
        icon.update_menu()

    return _action


def setup_tray():
    image = create_tray_image()

    delay_items = [
        item(format_duration(m), make_delay_action(m))
        for m in durations_in_minutes
    ]

    menu = Menu(
        item(
            lambda _: f"Auto-lock {'ENABLED' if locker.auto_lock_enabled else 'DISABLED'}",
            None,
            enabled=False
        ),
        item(
            lambda _: (
                f">> until "
                f"{datetime.fromtimestamp(locker.delayed_until).strftime('%H:%M:%S')} "
                f"({last_delay_label})"
            ),
            None,
            enabled=False,
            visible=lambda _: locker.delayed_until is not None
        ),
        item("Toggle Lock manually", lambda _,: root.after(0, locker.toggle_lock), default=True),
        item(lambda _: "Disable auto-lock" if locker.auto_lock_enabled else "Enable auto-lock",
             lambda _,: locker.toggle_auto_lock()),
        Menu.SEPARATOR,
        *delay_items,
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

    threading.Thread(target=setup_tray, daemon=True).start()
    root.mainloop()
