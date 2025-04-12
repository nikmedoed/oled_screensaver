import logging
import sys
import threading
import tkinter as tk

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item, Menu

from ScreenSaver import ScreenLocker

# Режим разработки: если передан параметр 'dev', включаем отладку и уменьшаем таймаут до 5 секунд.
DEV_MODE = 'dev' in sys.argv
TIMEOUT = 5 if DEV_MODE else 120

# Настройка логгирования
logging.basicConfig(
    level=logging.DEBUG if DEV_MODE else logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def create_tray_image():
    """Создаёт простую иконку для трея (например, круг с белой заливкой)."""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, width - 8, height - 8), fill="white")
    return image


def quit_app(icon, item):
    """Функция закрытия приложения, вызываемая из меню трея."""
    logging.debug("Exiting application via tray icon.")
    icon.stop()
    root.after(0, root.destroy)


def setup_tray():
    """Настраивает и запускает иконку в системном трее с меню."""
    image = create_tray_image()
    menu = Menu(item('Выход', quit_app))
    tray_icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)
    tray_icon.run()


# --- Основной блок запуска приложения ---

if __name__ == "__main__":
    if DEV_MODE:
        logging.info("Запущен в режиме разработчика (dev mode)")
    # Создаём корневой объект tkinter (скрытый, т.к. используем Toplevel для блокировки)
    root = tk.Tk()
    root.withdraw()
    # Инициализируем блокировщик экрана
    locker = ScreenLocker(root, timeout_seconds=TIMEOUT)
    logging.debug("ScreenLocker initialized. Entering mainloop.")

    # Запускаем трей-иконку в отдельном потоке
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    # Запускаем главный цикл tkinter
    root.mainloop()
