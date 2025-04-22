import logging
import time
import tkinter as tk

import keyboard
import pyautogui

CURSOR_CHECK_TIMEOUT = 5000
MIN_KEY_INTERVAL = 0.1
MIN_TOGGLE_INTERVAL = 0.3
HOTKEY_REBIND_INTERVAL = 10000


class ScreenLocker:
    def __init__(self, root, timeout_seconds):
        """
        root - tkinter root object.
        timeout_seconds - inactivity period before the screen is locked.
        """
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()
        self.last_mouse_position = pyautogui.position()
        self.locked = False
        self.locker_window = None

        self.auto_lock_enabled = True
        self.delayed_until: float | None = None
        self.delay_after_id: str | None = None
        self.last_delay_label: str = ""

        self._last_key_time = 0
        self._last_toggle_time = 0

        logging.debug(f"Initial cursor position: {self.last_mouse_position}")
        logging.debug(f"Timeout set to {self.timeout_seconds} seconds")

        self.root.after(0, self.monitor_mouse)
        self.root.after(0, self.monitor_hotkeys)
        keyboard.on_press(self.global_keyboard_event)

    def rebind_hotkeys(self):
        keyboard.unhook_all_hotkeys()
        keyboard.add_hotkey('ctrl+b', lambda: self.root.after(0, self.toggle_lock))
        keyboard.add_hotkey('b+ctrl', lambda: self.root.after(0, self.toggle_lock))
        logging.debug("Hotkeys registered")
        logging.debug("Hotkeys re-initialized")

    def monitor_hotkeys(self):
        self.rebind_hotkeys()
        self.root.after(HOTKEY_REBIND_INTERVAL, self.monitor_hotkeys)

    def global_keyboard_event(self, event):
        if time.time() - self._last_key_time < MIN_KEY_INTERVAL:
            return
        self._last_key_time = time.time()
        if self.auto_lock_enabled:
            self.last_activity_time = time.time()
            logging.debug(f"Keyboard event: {event.name}")

    def toggle_lock(self):
        if time.time() - self._last_toggle_time < MIN_TOGGLE_INTERVAL:
            return
        self._last_toggle_time = time.time()
        if self.locked:
            self.unlock()
        else:
            self.lock_screen()

    def monitor_mouse(self):
        """Monitors mouse movements to detect activity and trigger lock after timeout."""
        if self.auto_lock_enabled:
            current_position = pyautogui.position()
            now = time.time()

            if current_position != self.last_mouse_position:
                logging.debug(f"Mouse moved: {self.last_mouse_position} → {current_position}")
                self.last_activity_time = now
                self.last_mouse_position = current_position
            elif now - self.last_activity_time > self.timeout_seconds:
                # вызываем lock_screen из главного потока
                self.root.after(0, self.lock_screen)

        # повторяем через 2000 мс
        self.root.after(2000, self.monitor_mouse)

    def lock_screen(self):
        """Triggers screen lock."""
        if self.locked:
            return
        self.create_black_screen()

    def create_black_screen(self):
        """Creates fullscreen black window that locks the screen."""
        logging.debug("Activating screen lock...")
        self.locked = True
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.attributes('-topmost', True)
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        window.geometry(f"{screen_width}x{screen_height}+0+0")
        window.config(bg="black")
        window.bind("<Button>", lambda event: self.unlock())
        window.bind("<Key>", self.handle_key)
        window.bind("<Motion>", self.update_activity)
        window.protocol("WM_DELETE_WINDOW", lambda: None)
        window.focus_force()
        window.grab_set()
        window.after(CURSOR_CHECK_TIMEOUT, lambda: self.check_cursor_visibility(window))
        self.locker_window = window
        logging.debug("Lock window created.")

    def update_activity(self, event):
        """Updates activity timestamp and reveals cursor if hidden."""
        self.last_activity_time = time.time()
        if self.locker_window and self.locker_window['cursor'] == 'none':
            self.locker_window.config(cursor='')
            logging.debug("Cursor revealed due to movement.")

    def check_cursor_visibility(self, window):
        """Hides cursor if inactive for a certain period."""
        if window and window.winfo_exists() and window['cursor'] != 'none':
            if time.time() - self.last_activity_time >= CURSOR_CHECK_TIMEOUT / 1000:
                window.config(cursor='none')
                logging.debug("Cursor hidden due to inactivity.")
        window.after(CURSOR_CHECK_TIMEOUT, lambda: self.check_cursor_visibility(window))

    def handle_key(self, event):
        """
        Handles key presses in the lock window.
        Ctrl+B unlocks the screen.
        """
        self.last_activity_time = time.time()
        logging.debug(f"Key pressed: {event.keysym} (state: {event.state})")

    def unlock(self):
        """Unlocks the screen and removes the black window."""
        if self.locked and self.locker_window:
            logging.debug("Unlocking screen...")
            try:
                self.locker_window.grab_release()
            except Exception as e:
                logging.debug(f"Error releasing grab: {e}")
            self.locker_window.destroy()
            self.locker_window = None
            self.locked = False
            self.last_activity_time = time.time()
            logging.debug("Screen unlocked.")

    def _clear_delay(self):
        """Отменить любой запланированный _reenable_auto_lock."""
        if self.delay_after_id is not None:
            try:
                self.root.after_cancel(self.delay_after_id)
            except Exception:
                pass
            self.delay_after_id = None
            self.delayed_until = None

    def toggle_auto_lock(self):
        """Enables or disables auto-lock."""
        self._clear_delay()
        self.auto_lock_enabled = not self.auto_lock_enabled
        logging.debug("Auto-lock " + ("enabled" if self.auto_lock_enabled else "disabled"))

    def disable_auto_lock_for(self, seconds: int):
        """Отключает авто-блок на заданное количество секунд."""
        self._clear_delay()
        self.auto_lock_enabled = False
        self.delayed_until = time.time() + seconds
        logging.debug(f"Auto-lock disabled for {seconds} seconds (until {self.delayed_until})")

        ms = int(seconds * 1000)
        self.delay_after_id = self.root.after(ms, self._reenable_auto_lock)

    def _reenable_auto_lock(self):
        """Внутренний метод — восстанавливает авто-блок."""
        self.auto_lock_enabled = True
        self.delayed_until = None
        self.delay_after_id = None
        logging.debug("Auto-lock re-enabled after delay")
