import logging
import sys
import threading
import tkinter as tk

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item, Menu

from ScreenSaver import ScreenLocker

# Режим разработки: если передан параметр 'dev', уменьшаем таймаут до 5 секунд.
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
    """Закрытие приложения по выбору из меню трея."""
    logging.debug("Выход из приложения через трей-иконку.")
    icon.stop()
    root.after(0, root.destroy)


def toggle_auto_lock(icon, item):
    """Переключает автоблокировку через меню трея."""
    locker.toggle_auto_lock()


def auto_lock_label(_item):
    return "Отключить автоблокировку" if locker.auto_lock_enabled else "Включить автоблокировку"


def setup_tray():
    """Настраивает и запускает иконку трея с динамичным меню."""
    image = create_tray_image()
    menu = Menu(
        item(auto_lock_label, toggle_auto_lock),
        item('Выход', quit_app)
    )
    tray_icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)
    tray_icon.run()


# --- Запуск приложения ---

if __name__ == "__main__":
    if DEV_MODE:
        logging.info("Запущен в режиме разработчика (dev mode)")
    # Создаём скрытый корневой объект tkinter
    root = tk.Tk()
    root.withdraw()
    # Инициализируем блокировщик экрана
    locker = ScreenLocker(root, timeout_seconds=TIMEOUT)
    logging.debug("Экземпляр ScreenLocker создан. Запуск главного цикла.")

    # Запускаем трей-иконку в отдельном потоке
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    # Запуск основного цикла tkinter
    root.mainloop()
