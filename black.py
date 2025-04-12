import tkinter as tk
import time
import threading
import keyboard
import pyautogui
import sys
import pystray
from pystray import MenuItem as item, Menu
from PIL import Image, ImageDraw

# Режим разработки: если параметр 'dev' передан, активируем вывод отладочной информации и уменьшаем таймаут до 5 секунд.
DEV_MODE = 'dev' in sys.argv
TIMEOUT = 5 if DEV_MODE else 120

def debug_print(message: str):
    """Выводит диагностические сообщения, если активирован режим разработки."""
    if DEV_MODE:
        print(f"[DEBUG] {time.strftime('%Y-%m-%d %H:%M:%S')}: {message}")

class ScreenLocker:
    def __init__(self, root, timeout_seconds=TIMEOUT):
        """
        root - корневой объект tkinter, созданный в главном потоке.
        timeout_seconds - время неактивности (отсутствие движения мыши и ввода с клавиатуры)
                          для активации блокировки.
        """
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()  # для не заблокированного режима
        self.last_mouse_position = pyautogui.position()
        self.locked = False
        self.locker_window = None
        # Для заблокированного режима отслеживаем активность (например, для скрытия курсора и поднятия окна).
        self.last_locked_activity_time = None

        debug_print(f"Initial mouse position: {self.last_mouse_position}")
        debug_print(f"Timeout set to {self.timeout_seconds} seconds")

        # Запуск фонового потока для проверки активности (интервал 2 сек).
        self.monitor_thread = threading.Thread(target=self.monitor_mouse, daemon=True)
        self.monitor_thread.start()
        debug_print("Started monitor_mouse thread")

        # Регистрация глобальной горячей клавиши Ctrl+B для переключения режима блокировки.
        keyboard.add_hotkey('ctrl+b', lambda: self.root.after(0, self.toggle_lock))
        debug_print("Registered hotkey Ctrl+B")

        # Глобальный хук для клавиатуры – при любом вводе обновляем время активности (если не заблокировано).
        keyboard.hook(self.global_keyboard_event)
        debug_print("Registered global keyboard hook for activity monitoring.")

    def global_keyboard_event(self, event):
        """Обработчик глобальных клавиатурных событий: при любом нажатии обновляет время активности, если не заблокирован."""
        if not self.locked:
            self.last_activity_time = time.time()
            debug_print(f"Global keyboard event: {event.name}")

    def toggle_lock(self):
        debug_print("Hotkey Ctrl+B triggered")
        if self.locked:
            self.unlock()
        else:
            self.lock_screen()

    def monitor_mouse(self):
        """Проверяет положение мыши с интервалом 2 секунды.
        Если за время, превышающее timeout_seconds, не зафиксировано ни движения, ни ввода,
        в не заблокированном состоянии вызывается блокировка."""
        while True:
            current_position = pyautogui.position()
            if not self.locked:
                if current_position != self.last_mouse_position:
                    debug_print(f"Mouse moved from {self.last_mouse_position} to {current_position}")
                    self.last_activity_time = time.time()
                    self.last_mouse_position = current_position
                else:
                    elapsed = time.time() - self.last_activity_time
                    if elapsed > self.timeout_seconds:
                        debug_print(f"No input detected for {elapsed:.1f} seconds. Locking screen.")
                        self.root.after(0, self.lock_screen)
            else:
                # Если уже заблокировано, можно (по желанию) добавить проверки, чтобы поднять окно,
                # но поднятие окна будет осуществляться через отложенную проверку в locked-окне.
                pass
            time.sleep(2)

    def lock_screen(self):
        """Создаёт полноэкранное окно с чёрным фоном, если такового ещё нет.
        Если окно уже открыто, то просто поднимает его (raise) наверх."""
        if self.locked:
            if self.locker_window is not None and self.locker_window.winfo_exists():
                debug_print("Lock screen already active; raising it to front.")
                self.locker_window.lift()
            return

        debug_print("Locking screen now...")
        self.locked = True
        self.locker_window = tk.Toplevel(self.root)
        self.locker_window.attributes("-fullscreen", True)
        self.locker_window.config(bg="black")
        # При клике мышью окно разблокируется.
        self.locker_window.bind("<Button>", lambda event: self.unlock())
        # Обработка нажатия клавиш в заблокированном режиме: Ctrl+B разблокирует экран.
        self.locker_window.bind("<Key>", self.handle_key)
        # Отслеживаем движение мыши в заблокированном режиме – обновляем время активности и показываем курсор.
        self.locker_window.bind("<Motion>", self.locked_mouse_motion)
        # Отключаем стандартное закрытие окна.
        self.locker_window.protocol("WM_DELETE_WINDOW", lambda: None)
        self.locker_window.focus_set()
        self.last_locked_activity_time = time.time()
        debug_print("Black screen activated.")

        # Запускаем проверки для скрытия курсора и поднятия окна:
        self.locker_window.after(2000, self.check_cursor_visibility)
        self.locker_window.after(5000, self.check_locked_window_on_top)

    def handle_key(self, event):
        """Обрабатывает нажатия клавиш в заблокированном режиме.
        Обновляет время активности, а при нажатии Ctrl+B – разблокирует экран."""
        self.last_locked_activity_time = time.time()
        debug_print(f"Key pressed in locked mode: keysym='{event.keysym}', state={event.state}")
        if (event.state & 0x4) and event.keysym.lower() == "b":
            debug_print("Detected Ctrl+B in locked screen window. Unlocking screen.")
            self.unlock()

    def locked_mouse_motion(self, event):
        """Обработчик движения мыши в заблокированном режиме:
        обновляет время активности и показывает курсор, если он скрыт."""
        self.last_locked_activity_time = time.time()
        if self.locker_window['cursor'] == 'none':
            self.locker_window.config(cursor='')
            debug_print("Cursor shown due to mouse movement in locked mode.")

    def check_cursor_visibility(self):
        """Проверяет с интервалом 2 секунды, нужно ли скрыть курсор в заблокированном режиме.
        Если с момента последней активности в locked-окне прошло не менее TIMEOUT секунд – скрывает курсор."""
        if self.locker_window is None:
            return
        elapsed = time.time() - self.last_locked_activity_time
        if elapsed >= self.timeout_seconds:
            if self.locker_window['cursor'] != 'none':
                self.locker_window.config(cursor='none')
                debug_print("Cursor hidden due to inactivity in locked mode.")
        else:
            if self.locker_window['cursor'] == 'none':
                self.locker_window.config(cursor='')
                debug_print("Cursor shown due to recent activity in locked mode.")
        self.locker_window.after(2000, self.check_cursor_visibility)

    def check_locked_window_on_top(self):
        """Проверяет с интервалом 5 секунд, нет ли активности в заблокированном режиме.
        Если времени с последнего взаимодействия прошло не менее TIMEOUT секунд, поднимает окно."""
        if self.locker_window is None:
            return
        elapsed = time.time() - self.last_locked_activity_time
        if elapsed >= self.timeout_seconds:
            debug_print("Raising locked screen due to inactivity in locked mode.")
            self.locker_window.lift()
        self.locker_window.after(5000, self.check_locked_window_on_top)

    def unlock(self):
        """Уничтожает окно блокировки и возвращает систему в обычное состояние."""
        if self.locked and self.locker_window is not None:
            debug_print("Unlocking screen...")
            self.locker_window.destroy()
            self.locker_window = None
            self.locked = False
            self.last_activity_time = time.time()
            debug_print("Screen unlocked.")

# --- Функциональность для трей-иконки ---

def create_tray_image():
    """Создаёт простую иконку для трея (например, круг с белой заливкой)."""
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), "black")
    draw = ImageDraw.Draw(image)
    # Рисуем белый круг по центру
    draw.ellipse((8, 8, width - 8, height - 8), fill="white")
    return image

def quit_app(icon, item):
    """Функция закрытия приложения, вызываемая из меню трей-иконки."""
    debug_print("Exiting application via tray icon.")
    icon.stop()
    # Завершаем работу tkinter
    root.after(0, root.destroy)

def setup_tray():
    """Настраивает и запускает иконку в системном трее с меню."""
    image = create_tray_image()
    menu = Menu(item('Выход', quit_app))
    tray_icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)
    tray_icon.run()

# --- Основной блок запуска ---

if __name__ == "__main__":
    if DEV_MODE:
        print("Запущен в режиме разработчика (dev mode)")
    # Создаем корневой объект tkinter в главном потоке и скрываем его (так как работаем через Toplevel).
    root = tk.Tk()
    root.withdraw()
    # Инициализируем блокировку экрана с указанным таймаутом.
    locker = ScreenLocker(root, timeout_seconds=TIMEOUT)
    debug_print("ScreenLocker initialized. Entering mainloop.")

    # Запускаем трей-иконку в отдельном потоке, чтобы она не блокировала главный цикл.
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()

    # Запускаем главный цикл tkinter.
    root.mainloop()
