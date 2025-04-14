import logging
import platform
import sys
import threading
import tkinter as tk

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item, Menu

from ScreenSaver import ScreenLocker

# Developer mode: уменьшенный таймаут для разработки
DEV_MODE = 'dev' in sys.argv
TIMEOUT = 5 if DEV_MODE else 120

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if DEV_MODE else logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def create_tray_image():
    """Создаёт иконку для трея (белый круг на чёрном фоне)."""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), "black")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, width - 8, height - 8), fill="white")
    return image


def quit_app(icon, item):
    """Выход из приложения через пункт меню."""
    logging.debug("Exiting application via tray icon.")
    icon.stop()
    root.after(0, root.destroy)


def toggle_auto_lock(icon, item):
    """Переключает режим авто-блокировки."""
    locker.toggle_auto_lock()


def toggle_lock_menu(icon, item):
    """Пункт меню для ручного вызова блокировки (toggle_lock)."""
    root.after(0, locker.toggle_lock)


def auto_lock_label(_item):
    return "Disable auto-lock" if locker.auto_lock_enabled else "Enable auto-lock"


def setup_tray():
    """
    Создаёт и запускает трей-иконку с контекстным меню.
    Обрабатывается клик на иконку:
      - На Windows переопределяется метод _on_left_up для срабатывания toggle_lock.
      - Для других ОС используется атрибут on_clicked.
    """
    image = create_tray_image()
    # Создаем контекстное меню с пунктами
    menu = Menu(
        item("Toggle Lock", toggle_lock_menu, default=True),
        item(auto_lock_label, toggle_auto_lock),
        item("Exit", quit_app)
    )
    tray_icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)

    if platform.system() == "Windows":
        # Переопределяем обработчик левого клика (отпускание кнопки)
        def on_left_up(hwnd, msg, wparam, lparam):
            # При отпускании левой кнопки вызываем функцию toggle_lock
            root.after(0, locker.toggle_lock)

        tray_icon._on_left_up = on_left_up
    else:
        # Для других ОС пытаемся назначить on_clicked
        tray_icon.on_clicked = lambda icon: root.after(0, locker.toggle_lock)

    tray_icon.run()


if __name__ == "__main__":
    if DEV_MODE:
        logging.info("Running in developer mode")
    # Инициализация корневого окна Tkinter (скрываем окно)
    root = tk.Tk()
    root.withdraw()
    # Создаем экземпляр ScreenLocker
    locker = ScreenLocker(root, timeout_seconds=TIMEOUT)
    logging.debug("ScreenLocker instance created. Starting main loop.")

    # Запускаем трей-иконку в отдельном потоке
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    # Основной цикл приложения Tkinter
    root.mainloop()
