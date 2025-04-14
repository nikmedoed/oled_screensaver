import logging
import threading
import time
import tkinter as tk

import keyboard
import pyautogui

CURSOR_CHECK_TIMEOUT = 5000  # milliseconds
MIN_KEY_INTERVAL = 0.1  # minimum interval between key events (seconds)
MIN_TOGGLE_INTERVAL = 0.3  # minimum interval between toggling (seconds)


class ScreenLocker:
    def __init__(self, root, timeout_seconds):
        """
        root - tkinter object.
        timeout_seconds - inactivity time (in seconds) before lock is activated.
        """
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()
        self.last_mouse_position = pyautogui.position()
        self.locked = False
        self.locker_window = None
        self.auto_lock_enabled = True
        self._last_key_time = 0
        self._last_toggle_time = 0

        logging.debug(f"Initial cursor position: {self.last_mouse_position}")
        logging.debug(f"Timeout set to {self.timeout_seconds} seconds")

        # Start background thread for mouse monitoring
        threading.Thread(target=self.monitor_mouse, daemon=True).start()

        # Register hotkeys for toggling lock
        self.bind_hotkeys()
        # Start monitoring thread to periodically rebind hotkeys (на случай, если хуки отваливаются)
        threading.Thread(target=self.monitor_hotkeys, daemon=True).start()

        keyboard.on_press(self.global_keyboard_event)

    def bind_hotkeys(self):
        keyboard.add_hotkey('ctrl+b', lambda: self.root.after(0, self.toggle_lock))
        keyboard.add_hotkey('b+ctrl', lambda: self.root.after(0, self.toggle_lock))
        logging.debug("Горячие клавиши привязаны")

    def rebind_hotkeys(self):
        # Сбрасываем все горячие клавиши и привязываем снова
        keyboard.unhook_all_hotkeys()
        self.bind_hotkeys()
        logging.debug("Горячие клавиши переинициализированы")

    def monitor_hotkeys(self):
        # Периодически (каждые 10 секунд) переинициализируем горячие клавиши
        while True:
            time.sleep(10)
            self.rebind_hotkeys()

    def global_keyboard_event(self, event):
        # Игнорируем слишком частые события
        if time.time() - self._last_key_time < MIN_KEY_INTERVAL:
            return
        self._last_key_time = time.time()
        if self.auto_lock_enabled:
            self.last_activity_time = time.time()
            logging.debug(f"Keyboard event received: {event.name}")

    def toggle_lock(self):
        if time.time() - self._last_toggle_time < MIN_TOGGLE_INTERVAL:
            return
        self._last_toggle_time = time.time()
        if self.locked:
            self.unlock()
        else:
            self.lock_screen()

    def monitor_mouse(self):
        """Monitor mouse movements to update activity and trigger lock after timeout."""
        while True:
            if not self.auto_lock_enabled:
                time.sleep(2)
                continue

            current_position = pyautogui.position()
            if current_position != self.last_mouse_position:
                logging.debug(f"Mouse moved from {self.last_mouse_position} to {current_position}")
                self.last_activity_time = time.time()
                self.last_mouse_position = current_position
            else:
                if time.time() - self.last_activity_time > self.timeout_seconds:
                    self.root.after(0, self.lock_screen)
            time.sleep(2)

    def lock_screen(self):
        """Activate the lock mode. If the screen is already locked, simply return."""
        if self.locked:
            return
        self.create_black_screen()

    def create_black_screen(self):
        """Creates a lock window that always stays on top."""
        logging.debug("Activating screen lock...")
        self.locked = True
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        # Set the window to always be on top
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
        logging.debug("Lock window created and set to always be on top.")

    def update_activity(self, event):
        """Mouse movement handler in the locked window: updates activity time and shows the cursor if it is hidden."""
        self.last_activity_time = time.time()
        if self.locker_window and self.locker_window['cursor'] == 'none':
            self.locker_window.config(cursor='')
            logging.debug("Cursor shown due to mouse movement.")

    def check_cursor_visibility(self, window):
        """Hide the cursor if the inactivity duration exceeds the threshold."""
        if window and window.winfo_exists() and window['cursor'] != 'none':
            if time.time() - self.last_activity_time >= CURSOR_CHECK_TIMEOUT / 1000:
                window.config(cursor='none')
                logging.debug("Cursor hidden due to inactivity.")
        window.after(CURSOR_CHECK_TIMEOUT, lambda: self.check_cursor_visibility(window))

    def handle_key(self, event):
        """Handles key press events in the locked window.
        If Ctrl+B is pressed, the screen unlocks.
        """
        self.last_activity_time = time.time()
        logging.debug(f"Key pressed: {event.keysym} (state: {event.state})")
        if (event.state & 0x4) and event.keysym.lower() == "b":
            logging.debug("Ctrl+B pressed - unlocking screen.")
            self.unlock()

    def unlock(self):
        """Unlocks the screen by closing the lock window."""
        if self.locked and self.locker_window is not None:
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

    def toggle_auto_lock(self):
        """Toggles the auto-lock mode."""
        self.auto_lock_enabled = not self.auto_lock_enabled
        logging.info("Auto-lock " + ("enabled" if self.auto_lock_enabled else "disabled"))
