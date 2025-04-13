import logging
import threading
import time
import tkinter as tk

import keyboard
import pyautogui

CURSOR_CHECK_TIMEOUT = 5000  # миллисекунд
MIN_KEY_INTERVAL = 0.1  # минимальный интервал между реакциями на клавишу (в секундах)
MIN_TOGGLE_INTERVAL = 0.3  # минимальный интервал между вызовами toggle_lock (в секундах)


class ScreenLocker:
    def __init__(self, root, timeout_seconds):
        """
        root - корневой объект tkinter.
        timeout_seconds - время неактивности для активации блокировки.
        """
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()  # время последней активности
        self.lock_screen_open_time = None  # время открытия окна блокировки
        self.last_mouse_position = pyautogui.position()
        self.locked = False
        self.locker_window = None
        self.auto_lock_enabled = True  # автоблокировка включена по умолчанию
        self._last_key_time = 0  # время последнего события клавиатуры
        self._last_toggle_time = 0  # время последнего переключения блокировки

        logging.debug(f"Начальная позиция мыши: {self.last_mouse_position}")
        logging.debug(f"Таймаут установлен в {self.timeout_seconds} секунд")
        logging.debug("Автоблокировка включена по умолчанию.")

        # Запуск фонового потока мониторинга мыши
        self.monitor_thread = threading.Thread(target=self.monitor_mouse, daemon=True)
        self.monitor_thread.start()
        logging.debug("Запущен поток мониторинга мыши")

        # Регистрация горячих клавиш для переключения блокировки
        keyboard.add_hotkey('ctrl+b', lambda: self.root.after(0, self.toggle_lock))
        keyboard.add_hotkey('b+ctrl', lambda: self.root.after(0, self.toggle_lock))
        logging.debug("Зарегистрированы хоткеи: ctrl+b и b+ctrl")

        # Обработчик нажатий клавиш: реагируем только на on_press и учитываем минимальный интервал
        keyboard.on_press(self.global_keyboard_event)
        logging.debug("Зарегистрирован обработчик on_press для клавиатуры.")

    def global_keyboard_event(self, event):
        current_time = time.time()
        if current_time - self._last_key_time < MIN_KEY_INTERVAL:
            return  # пропускаем событие, если прошло мало времени с предыдущего
        self._last_key_time = current_time

        if not self.auto_lock_enabled:
            return

        self.last_activity_time = current_time
        logging.debug(f"Получено событие клавиатуры: {event.name}")

    def toggle_lock(self):
        now = time.time()
        if now - self._last_toggle_time < MIN_TOGGLE_INTERVAL:
            # Если событие произошло слишком быстро подряд, игнорируем его.
            return
        self._last_toggle_time = now

        logging.debug("Горячая клавиша для переключения блокировки сработала.")
        if self.locked:
            self.unlock()
        else:
            self.lock_screen()

    def monitor_mouse(self):
        """Мониторинг перемещения мыши в незаблокированном режиме."""
        while True:
            if not self.auto_lock_enabled:
                time.sleep(2)
                continue

            current_position = pyautogui.position()
            if current_position != self.last_mouse_position:
                logging.debug(f"Мышь сместилась с {self.last_mouse_position} на {current_position}")
                self.last_activity_time = time.time()
                self.last_mouse_position = current_position
            else:
                elapsed = time.time() - self.last_activity_time
                if elapsed > self.timeout_seconds:
                    if self.auto_lock_enabled:
                        logging.debug(f"Нет активности {elapsed:.1f} секунд. Блокировка экрана.")
                        self.root.after(0, self.lock_screen)
            time.sleep(2)

    def lock_screen(self):
        """
        Отображает окно блокировки. Если окно уже активно, обновляем фокус.
        Если активность появилась после показа окна – поднимаем окно поверх остальных.
        """
        if self.locked:
            if self.last_activity_time <= self.lock_screen_open_time:
                logging.debug("Окно блокировки уже активно и активность не изменялась; обновление не требуется.")
                return
            else:
                logging.debug("Обнаружена активность после показа окна блокировки; поднимаем окно.")
                self.raise_lock_screen()
                self.lock_screen_open_time = time.time()
                return

        # Создаём окно блокировки
        self.locker_window = self.create_black_screen()

    def create_black_screen(self):
        logging.debug("Включение блокировки экрана...")
        self.locked = True
        new_window = tk.Toplevel(self.root)
        new_window.overrideredirect(True)
        new_window.lift()
        new_window.attributes('-topmost', True)
        screen_width = new_window.winfo_screenwidth()
        screen_height = new_window.winfo_screenheight()
        new_window.geometry(f"{screen_width}x{screen_height}+0+0")
        new_window.config(bg="black")
        new_window.bind("<Button>", lambda event: self.unlock())
        new_window.bind("<Key>", self.handle_key)
        new_window.bind("<Motion>", self.locked_mouse_motion)
        new_window.protocol("WM_DELETE_WINDOW", lambda: None)
        new_window.focus_force()
        new_window.grab_set()
        logging.debug("Окно блокировки создано и активировано.")

        # Через короткое время отключаем принудительный topmost
        new_window.after(300, lambda: new_window.attributes('-topmost', False))
        new_window.after(CURSOR_CHECK_TIMEOUT, self.check_cursor_visibility)
        self.lock_screen_open_time = time.time()
        # Явное обновление окна (на случай, если окно не отображается сразу)
        new_window.update()
        return new_window

    def raise_lock_screen(self):
        """Поднимает окно блокировки поверх остальных с кратковременным включением topmost."""
        if self.locker_window is None or not self.locker_window.winfo_exists():
            return
        try:
            self.locker_window.attributes("-topmost", True)
            self.locker_window.lift()
            self.locker_window.focus_force()
            logging.debug("Окно блокировки поднято с временным topmost.")
            self.locker_window.after(300, lambda: self.locker_window.attributes("-topmost", False))
        except Exception as e:
            logging.debug(f"Ошибка при подъёме окна блокировки: {e}")

    def locker_window_destroy(self, new_window=None):
        """Уничтожает текущее окно блокировки и устанавливает новое, если передано."""
        if self.locker_window is not None and self.locker_window.winfo_exists():
            try:
                logging.debug("Уничтожаем старое окно блокировки.")
                try:
                    self.locker_window.grab_release()
                except Exception as e:
                    logging.debug(f"Ошибка при освобождении grab: {e}")
                self.locker_window.destroy()
            except Exception as e:
                logging.debug(f"Ошибка при уничтожении окна блокировки: {e}")
        self.locker_window = new_window

    def handle_key(self, event):
        """
        Обработка нажатий в заблокированном режиме – обновляем время активности.
        При нажатии Ctrl+B окно разблокируется.
        """
        self.last_activity_time = time.time()
        logging.debug(f"Нажата клавиша в заблокированном режиме: keysym='{event.keysym}', state={event.state}")
        if (event.state & 0x4) and event.keysym.lower() == "b":
            logging.debug("Нажат Ctrl+B в окне блокировки – разблокировка экрана.")
            self.unlock()

    def locked_mouse_motion(self, event):
        """
        Обработка движения мыши в заблокированном режиме – обновляем активность и показываем курсор.
        """
        self.last_activity_time = time.time()
        if self.locker_window and self.locker_window['cursor'] == 'none':
            self.locker_window.config(cursor='')
            logging.debug("Курсор отображён вслед за движением мыши в заблокированном режиме.")

    def check_cursor_visibility(self):
        """
        Скрывает курсор, если с момента последней активности прошло достаточное время.
        """
        if self.locker_window is None:
            return
        if self.locker_window['cursor'] != 'none':
            elapsed = time.time() - self.last_activity_time
            if elapsed * 1000 >= CURSOR_CHECK_TIMEOUT:
                self.locker_window.config(cursor='none')
                logging.debug("Курсор скрыт из-за бездействия.")
        self.locker_window.after(CURSOR_CHECK_TIMEOUT, self.check_cursor_visibility)

    def unlock(self):
        """Разблокирует экран, уничтожая окно блокировки."""
        if self.locked and self.locker_window is not None:
            logging.debug("Разблокировка экрана...")
            self.locker_window_destroy()
            self.locked = False
            self.last_activity_time = time.time()
            logging.debug("Экран разблокирован.")

    def toggle_auto_lock(self):
        """
        Переключает состояние автоблокировки. При отключении обработчики не обновляют таймер активности.
        """
        self.auto_lock_enabled = not self.auto_lock_enabled
        logging.info(f"Автоблокировка {'включена' if self.auto_lock_enabled else 'отключена'}")
