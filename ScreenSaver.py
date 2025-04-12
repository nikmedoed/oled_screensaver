import threading
import time
import tkinter as tk
import logging

import keyboard
import pyautogui


class ScreenLocker:
    def __init__(self, root, timeout_seconds):
        """
        root - корневой объект tkinter.
        timeout_seconds - время неактивности для активации блокировки.
        """
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()  # время последней активности (общая для всех режимов)
        self.lock_screen_open_time = None      # время открытия текущего окна блокировки
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
        if not self.locked:
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
            if not self.locked:
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
        """Показывает блокирующее окно. Если окно уже открыто, обновляем или пропускаем."""
        if self.locked:
            if self.last_activity_time <= self.lock_screen_open_time:
                logging.debug("Lock screen already active and no new activity detected; no refresh needed.")
                return
            else:
                logging.debug("Activity detected after lock screen was shown; refreshing lock screen.")
                self.refresh_lock_screen()
                return

        logging.debug("Locking screen now...")
        self.locked = True
        self.locker_window = tk.Toplevel(self.root)
        self.locker_window.attributes("-fullscreen", True)
        self.locker_window.config(bg="black")
        self.locker_window.bind("<Button>", lambda event: self.unlock())
        self.locker_window.bind("<Key>", self.handle_key)
        self.locker_window.bind("<Motion>", self.locked_mouse_motion)
        self.locker_window.protocol("WM_DELETE_WINDOW", lambda: None)
        self.locker_window.focus_set()

        # Фиксируем время показа экрана блокировки
        self.lock_screen_open_time = time.time()
        self.last_activity_time = time.time()
        logging.debug("Black screen activated.")

        self.locker_window.after(2000, self.check_cursor_visibility)
        self.locker_window.after(5000, self.check_locked_window_refresh)

    def handle_key(self, event):
        """Обработчик нажатий в заблокированном режиме – обновляет время активности."""
        self.last_activity_time = time.time()
        logging.debug(f"Key pressed in locked mode: keysym='{event.keysym}', state={event.state}")
        if (event.state & 0x4) and event.keysym.lower() == "b":
            logging.debug("Detected Ctrl+B in locked screen window. Unlocking screen.")
            self.unlock()

    def locked_mouse_motion(self, event):
        """Обработчик движения мыши в заблокированном режиме."""
        self.last_activity_time = time.time()
        if self.locker_window['cursor'] == 'none':
            self.locker_window.config(cursor='')
            logging.debug("Cursor shown due to mouse movement in locked mode.")

    def check_cursor_visibility(self):
        """Показывает или скрывает курсор в зависимости от активности."""
        if self.locker_window is None:
            return
        elapsed = time.time() - self.last_activity_time
        if elapsed >= self.timeout_seconds:
            if self.locker_window['cursor'] != 'none':
                self.locker_window.config(cursor='none')
                logging.debug("Cursor hidden due to inactivity in locked mode.")
        else:
            if self.locker_window['cursor'] == 'none':
                self.locker_window.config(cursor='')
                logging.debug("Cursor shown due to recent activity in locked mode.")
        self.locker_window.after(2000, self.check_cursor_visibility)

    def check_locked_window_refresh(self):
        """Проверяет, нужно ли обновить окно блокировки."""
        if self.locker_window is None:
            return
        if self.last_activity_time > self.lock_screen_open_time:
            elapsed = time.time() - self.last_activity_time
            if elapsed >= self.timeout_seconds:
                logging.debug(
                    "Refreshing locked screen due to detected activity after display and subsequent inactivity.")
                self.refresh_lock_screen()
        self.locker_window.after(5000, self.check_locked_window_refresh)

    def refresh_lock_screen(self):
        """Создаёт новое окно поверх текущего и уничтожает старое."""
        logging.debug("Refreshing lock screen: creating new lock window.")
        new_window = tk.Toplevel(self.root)
        new_window.attributes("-fullscreen", True)
        new_window.config(bg="black")
        new_window.bind("<Button>", lambda event: self.unlock())
        new_window.bind("<Key>", self.handle_key)
        new_window.bind("<Motion>", self.locked_mouse_motion)
        new_window.protocol("WM_DELETE_WINDOW", lambda: None)
        new_window.focus_set()

        # Обновляем время показа нового окна блокировки
        self.lock_screen_open_time = time.time()
        self.last_activity_time = time.time()
        new_window.after(2000, self.check_cursor_visibility)
        new_window.after(5000, self.check_locked_window_refresh)

        # Задержка для плавного перехода, затем уничтожаем старое окно
        self.root.after(100, lambda: self.destroy_old_window(new_window))

    def destroy_old_window(self, new_window):
        """Уничтожает текущее окно блокировки и заменяет его новым."""
        if self.locker_window is not None and self.locker_window.winfo_exists():
            try:
                logging.debug("Destroying old lock window.")
                self.locker_window.destroy()
            except Exception as e:
                logging.debug(f"Error destroying old lock window: {e}")
        self.locker_window = new_window

    def unlock(self):
        """Разблокирует экран, уничтожая окно блокировки."""
        if self.locked and self.locker_window is not None:
            logging.debug("Unlocking screen...")
            self.locker_window.destroy()
            self.locker_window = None
            self.locked = False
            self.last_activity_time = time.time()
            logging.debug("Screen unlocked.")
