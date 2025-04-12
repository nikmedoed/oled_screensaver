import logging
import threading
import time
import tkinter as tk

import keyboard
import pyautogui

CURSOR_CHECK_TIMEOUT = 5000  # миллисекунд


class ScreenLocker:
    def __init__(self, root, timeout_seconds):
        """
        root - корневой объект tkinter.
        timeout_seconds - время неактивности для активации блокировки.
        """
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()  # время последней активности (общая для всех режимов)
        self.lock_screen_open_time = None  # время открытия текущего окна блокировки
        self.last_mouse_position = pyautogui.position()
        self.locked = False
        self.locker_window = None

        logging.debug(f"Initial mouse position: {self.last_mouse_position}")
        logging.debug(f"Timeout set to {self.timeout_seconds} seconds")

        # Запуск фонового потока проверки мыши
        self.monitor_thread = threading.Thread(target=self.monitor_mouse, daemon=True)
        self.monitor_thread.start()
        logging.debug("Started monitor_mouse thread")

        # Регистрация горячей клавиши Ctrl+B для переключения блокировки
        keyboard.add_hotkey('ctrl+b', lambda: self.root.after(0, self.toggle_lock))
        logging.debug("Registered hotkey Ctrl+B")

        # Глобальный хук клавиатуры для обновления времени активности
        keyboard.hook(self.global_keyboard_event)
        logging.debug("Registered global keyboard hook for activity monitoring.")

    def global_keyboard_event(self, event):
        self.last_activity_time = time.time()
        logging.debug(f"Global keyboard event: {event.name}")

    def toggle_lock(self):
        logging.debug("Hotkey Ctrl+B triggered")
        if self.locked:
            self.unlock()
        else:
            self.lock_screen()

    def monitor_mouse(self):
        """Проверка перемещения мыши в незаблокированном режиме."""
        while True:
            current_position = pyautogui.position()
            if current_position != self.last_mouse_position:
                logging.debug(f"Mouse moved from {self.last_mouse_position} to {current_position}")
                self.last_activity_time = time.time()
                self.last_mouse_position = current_position
            else:
                elapsed = time.time() - self.last_activity_time
                if elapsed > self.timeout_seconds:
                    logging.debug(f"No input detected for {elapsed:.1f} seconds. Locking screen.")
                    self.root.after(0, self.lock_screen)
            time.sleep(2)

    def lock_screen(self):
        """
        Показывает блокирующее окно. Если окно уже открыто, обновляем фокус.
        Если с момента открытия окна не было активности, ничего не делаем.
        Если же была активность после открытия, пытаемся временно установить topmost.
        """
        if self.locked:
            if self.last_activity_time <= self.lock_screen_open_time:
                logging.debug("Lock screen already active and no new activity detected; no refresh needed.")
                return
            else:
                logging.debug("Activity detected after lock screen was shown; raising lock screen.")
                self.raise_lock_screen()
                self.lock_screen_open_time = time.time()  # обновляем время открытия
                return

        # Если окно еще не создано
        self.locker_window = self.create_black_screen()

    def create_black_screen(self):
        logging.debug("Locking screen now...")
        self.locked = True
        new_window = tk.Toplevel(self.root)
        new_window.attributes("-fullscreen", True)
        new_window.config(bg="black")
        new_window.bind("<Button>", lambda event: self.unlock())
        new_window.bind("<Key>", self.handle_key)
        new_window.bind("<Motion>", self.locked_mouse_motion)
        new_window.protocol("WM_DELETE_WINDOW", lambda: None)
        new_window.focus_force()
        new_window.grab_set()  # Захватываем все события ввода
        logging.debug("Black screen activated.")

        new_window.after(CURSOR_CHECK_TIMEOUT, self.check_cursor_visibility)
        self.lock_screen_open_time = time.time()
        return new_window

    def raise_lock_screen(self):
        """Поднимает уже открытое окно блокировки, используя временный topmost."""
        if self.locker_window is None or not self.locker_window.winfo_exists():
            return
        try:
            # Временно включаем режим всегда сверху
            self.locker_window.attributes("-topmost", True)
            self.locker_window.lift()
            self.locker_window.focus_force()
            logging.debug("Lock screen raised: topmost enabled temporarily.")
            # Через 300 мс сбрасываем атрибут, чтобы окно не оставалось всегда поверх
            self.locker_window.after(300, lambda: self.locker_window.attributes("-topmost", False))
        except Exception as e:
            logging.debug(f"Error raising lock screen: {e}")

    def locker_window_destroy(self, new_window=None):
        """Уничтожает текущее окно блокировки и заменяет его новым (если передано)."""
        if self.locker_window is not None and self.locker_window.winfo_exists():
            try:
                logging.debug("Destroying old lock window.")
                try:
                    self.locker_window.grab_release()
                except Exception as e:
                    logging.debug(f"Error releasing grab: {e}")
                self.locker_window.destroy()
            except Exception as e:
                logging.debug(f"Error destroying old lock window: {e}")
        self.locker_window = new_window

    def handle_key(self, event):
        """
        Обработчик нажатий в заблокированном режиме – обновляет время активности.
        При нажатии Ctrl+B разблокирует экран.
        """
        self.last_activity_time = time.time()
        logging.debug(f"Key pressed in locked mode: keysym='{event.keysym}', state={event.state}")
        if (event.state & 0x4) and event.keysym.lower() == "b":
            logging.debug("Detected Ctrl+B in locked screen window. Unlocking screen.")
            self.unlock()

    def locked_mouse_motion(self, event):
        """
        Обработчик движения мыши в заблокированном режиме – обновляет время активности и показывает курсор.
        """
        self.last_activity_time = time.time()
        if self.locker_window and self.locker_window['cursor'] == 'none':
            self.locker_window.config(cursor='')
            logging.debug("Cursor shown due to mouse movement in locked mode.")

    def check_cursor_visibility(self):
        """
        Скрывает курсор, если с момента последней активности прошло достаточно времени.
        """
        if self.locker_window is None:
            return
        if self.locker_window['cursor'] != 'none':
            elapsed = time.time() - self.last_activity_time
            if elapsed * 1000 >= CURSOR_CHECK_TIMEOUT:
                self.locker_window.config(cursor='none')
                logging.debug("Cursor hidden due to inactivity in locked mode.")
        self.locker_window.after(CURSOR_CHECK_TIMEOUT, self.check_cursor_visibility)

    def unlock(self):
        """Разблокирует экран, уничтожая окно блокировки."""
        if self.locked and self.locker_window is not None:
            logging.debug("Unlocking screen...")
            self.locker_window_destroy()
            self.locked = False
            self.last_activity_time = time.time()
            logging.debug("Screen unlocked.")
