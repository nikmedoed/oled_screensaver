import logging
import threading
import time
import tkinter as tk

import keyboard
import pyautogui

CURSOR_CHECK_TIMEOUT = 5000  # milliseconds
MIN_KEY_INTERVAL = 0.1  # minimum interval between key events (seconds)
MIN_TOGGLE_INTERVAL = 0.3  # minimum interval between lock toggles (seconds)


class ScreenLocker:
    def __init__(self, root, timeout_seconds):
        """
        root - tkinter root object.
        timeout_seconds - inactivity time to activate screen lock.
        """
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()
        self.lock_screen_open_time = None
        self.last_mouse_position = pyautogui.position()
        self.locked = False
        self.locker_window = None
        self.auto_lock_enabled = True
        self._last_key_time = 0
        self._last_toggle_time = 0

        logging.debug(f"Initial mouse position: {self.last_mouse_position}")
        logging.debug(f"Timeout set to {self.timeout_seconds} seconds")
        logging.debug("Auto-lock is enabled by default.")

        # Start background thread for monitoring mouse movement
        self.monitor_thread = threading.Thread(target=self.monitor_mouse, daemon=True)
        self.monitor_thread.start()
        logging.debug("Mouse monitor thread started")

        # Register hotkeys to toggle lock
        keyboard.add_hotkey('ctrl+b', lambda: self.root.after(0, self.toggle_lock))
        keyboard.add_hotkey('b+ctrl', lambda: self.root.after(0, self.toggle_lock))
        logging.debug("Hotkeys registered: ctrl+b and b+ctrl")

        # Register global keyboard press handler
        keyboard.on_press(self.global_keyboard_event)
        logging.debug("Keyboard on_press handler registered.")

    def global_keyboard_event(self, event):
        current_time = time.time()
        if current_time - self._last_key_time < MIN_KEY_INTERVAL:
            return
        self._last_key_time = current_time

        if not self.auto_lock_enabled:
            return

        self.last_activity_time = current_time
        logging.debug(f"Keyboard event received: {event.name}")

    def toggle_lock(self):
        now = time.time()
        if now - self._last_toggle_time < MIN_TOGGLE_INTERVAL:
            return
        self._last_toggle_time = now

        logging.debug("Lock toggle hotkey triggered.")
        if self.locked:
            self.unlock()
        else:
            self.lock_screen()

    def monitor_mouse(self):
        """Monitor mouse movement while unlocked."""
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
                elapsed = time.time() - self.last_activity_time
                if elapsed > self.timeout_seconds:
                    if self.auto_lock_enabled:
                        logging.debug(f"No activity for {elapsed:.1f} seconds. Locking screen.")
                        self.root.after(0, self.lock_screen)
            time.sleep(2)

    def lock_screen(self):
        """
        Display the lock screen window. If it's already active, update its focus.
        If activity occurred after showing, raise the window.
        """
        if self.locked:
            if self.last_activity_time <= self.lock_screen_open_time:
                logging.debug("Lock window already active and no new activity; no update needed.")
                return
            else:
                logging.debug("Activity detected after lock screen was shown; raising window.")
                self.raise_lock_screen()
                self.lock_screen_open_time = time.time()
                return

        self.locker_window = self.create_black_screen()

    def create_black_screen(self):
        logging.debug("Enabling screen lock...")
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
        logging.debug("Lock screen window created and activated.")

        new_window.after(300, lambda: new_window.attributes('-topmost', False))
        new_window.after(CURSOR_CHECK_TIMEOUT, self.check_cursor_visibility)
        self.lock_screen_open_time = time.time()
        new_window.update()
        return new_window

    def raise_lock_screen(self):
        """Raises lock screen window temporarily with topmost enabled."""
        if self.locker_window is None or not self.locker_window.winfo_exists():
            return
        try:
            self.locker_window.attributes("-topmost", True)
            self.locker_window.lift()
            self.locker_window.focus_force()
            logging.debug("Lock screen window raised with temporary topmost.")
            self.locker_window.after(300, lambda: self.locker_window.attributes("-topmost", False))
        except Exception as e:
            logging.debug(f"Error raising lock screen window: {e}")

    def locker_window_destroy(self, new_window=None):
        """Destroys current lock screen window and replaces it if provided."""
        if self.locker_window is not None and self.locker_window.winfo_exists():
            try:
                logging.debug("Destroying old lock screen window.")
                try:
                    self.locker_window.grab_release()
                except Exception as e:
                    logging.debug(f"Error releasing grab: {e}")
                self.locker_window.destroy()
            except Exception as e:
                logging.debug(f"Error destroying lock screen window: {e}")
        self.locker_window = new_window

    def handle_key(self, event):
        """
        Handles key press in locked mode. Updates activity time.
        If Ctrl+B is pressed – unlocks screen.
        """
        self.last_activity_time = time.time()
        logging.debug(f"Key pressed in locked mode: keysym='{event.keysym}', state={event.state}")
        if (event.state & 0x4) and event.keysym.lower() == "b":
            logging.debug("Ctrl+B pressed in lock window – unlocking screen.")
            self.unlock()

    def locked_mouse_motion(self, event):
        """Handles mouse motion in locked mode – updates activity and shows cursor."""
        self.last_activity_time = time.time()
        if self.locker_window and self.locker_window['cursor'] == 'none':
            self.locker_window.config(cursor='')
            logging.debug("Cursor shown due to mouse motion in locked mode.")

    def check_cursor_visibility(self):
        """Hides cursor if inactivity duration exceeds threshold."""
        if self.locker_window is None:
            return
        if self.locker_window['cursor'] != 'none':
            elapsed = time.time() - self.last_activity_time
            if elapsed * 1000 >= CURSOR_CHECK_TIMEOUT:
                self.locker_window.config(cursor='none')
                logging.debug("Cursor hidden due to inactivity.")
        self.locker_window.after(CURSOR_CHECK_TIMEOUT, self.check_cursor_visibility)

    def unlock(self):
        """Unlocks screen by destroying lock window."""
        if self.locked and self.locker_window is not None:
            logging.debug("Unlocking screen...")
            self.locker_window_destroy()
            self.locked = False
            self.last_activity_time = time.time()
            logging.debug("Screen unlocked.")

    def toggle_auto_lock(self):
        """
        Toggles auto-lock. If disabled, input handlers stop updating activity time.
        """
        self.auto_lock_enabled = not self.auto_lock_enabled
        logging.info(f"Auto-lock {'enabled' if self.auto_lock_enabled else 'disabled'}")
