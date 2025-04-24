import logging
import time
import tkinter as tk

import pyautogui
from pynput import keyboard

from config import CURSOR_CHECK_TIMEOUT, MIN_TOGGLE_INTERVAL, MOUSE_CHECK_TIMEOUT
from .utils import is_taskbar_focused


class ScreenLocker:
    def __init__(self, root: tk.Tk, timeout_seconds: int):
        """
        root - tkinter root object.
        timeout_seconds - inactivity period before the screen is locked.
        """
        self.root = root
        self.timeout_seconds = timeout_seconds
        self.last_activity_time = time.time()
        self.last_mouse_position = pyautogui.position()
        self.locked = False
        self.locker_window: tk.Toplevel | None = None

        self.auto_lock_enabled = True
        self.delayed_until: float | None = None
        self.delay_after_id: str | None = None

        self.monitor_id: str | None = None
        self._last_toggle_time = 0.0

        logging.debug(f"Initial cursor position: {self.last_mouse_position}")
        logging.debug(f"Timeout set to {self.timeout_seconds} seconds")

        self.ctrl_pressed = False
        self._key_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self._key_listener.start()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.start_mouse_monitor()

    def _on_press(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_pressed = True
        else:
            vk = getattr(key, 'vk', None)
            if self.ctrl_pressed and vk == 0x42:
                self.root.after(0, self.toggle_lock)

        if self.auto_lock_enabled and not self.locked:
            self.last_activity_time = time.time()
            logging.debug(f"Key event: {key}")

    def _on_release(self, key):
        if key in {keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}:
            self.ctrl_pressed = False

    def start_mouse_monitor(self):
        if self.monitor_id is None and self.auto_lock_enabled:
            self.monitor_id = self.root.after(MOUSE_CHECK_TIMEOUT, self._monitor_mouse)

    def _monitor_mouse(self):
        self.monitor_id = None
        if not self.auto_lock_enabled or self.locked:
            return

        now = time.time()
        pos = pyautogui.position()

        if pos != self.last_mouse_position:
            logging.debug(f"Mouse moved: {self.last_mouse_position} → {pos}")
            self.last_mouse_position = pos
            self.last_activity_time = now
        elif now - self.last_activity_time >= self.timeout_seconds:
            self.root.after(0, self.lock_screen)
            return

        self.start_mouse_monitor()

    def toggle_lock(self):
        """Triggers screen lock."""
        now = time.time()
        if now - self._last_toggle_time < MIN_TOGGLE_INTERVAL:
            return
        self._last_toggle_time = now
        if self.locked:
            self.unlock()
        else:
            self.lock_screen()

    def lock_screen(self):
        """Creates fullscreen black window that locks the screen."""
        if self.locked:
            return
        self._cancel_monitor()
        logging.debug("Activating screen lock...")
        self.locked = True
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes('-topmost', True)
        win.config(bg="black")
        win.bind("<Button>", lambda e: self.unlock())
        win.geometry(f"{win.winfo_screenwidth()}x{win.winfo_screenheight()}+0+0")
        win.protocol("WM_DELETE_WINDOW", lambda: None)
        win.bind('<Motion>', self.locked_mouse_motion)
        win.grab_set()
        if is_taskbar_focused():
            win.focus_force()
        win.after(CURSOR_CHECK_TIMEOUT, self.check_cursor_visibility)
        self.locker_window = win
        logging.debug("Lock window created.")

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
        """Unlocks the screen and removes the black window."""
        if not self.locker_window:
            return
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

        self.start_mouse_monitor()

    def _clear_delay(self):
        """Cancels any scheduled _reenable_auto_lock."""
        if self.delay_after_id:
            try:
                self.root.after_cancel(self.delay_after_id)
            except Exception:
                pass
            self.delay_after_id = None
        self.delayed_until = None

    def _cancel_monitor(self):
        if self.monitor_id:
            self.root.after_cancel(self.monitor_id)
            self.monitor_id = None

    def toggle_auto_lock(self):
        """Enables or disables auto-lock."""
        self._clear_delay()
        self.auto_lock_enabled = not self.auto_lock_enabled
        logging.debug(f"Auto-lock {'enabled' if self.auto_lock_enabled else 'disabled'}")

        if self.auto_lock_enabled:
            self.start_mouse_monitor()
        else:
            self._cancel_monitor()

    def disable_auto_lock_for(self, seconds: int):
        """Disables auto-lock for the given number of seconds."""
        self._clear_delay()
        self.auto_lock_enabled = False
        self.delayed_until = time.time() + seconds
        self._cancel_monitor()

        self.delay_after_id = self.root.after(seconds * 1000, self._reenable_auto_lock)
        logging.debug(f"Auto-lock DISABLED for {seconds} s")

    def _reenable_auto_lock(self):
        """Internal method — re-enables auto-lock."""
        self.auto_lock_enabled = True
        self.delayed_until = None
        self.delay_after_id = None
        logging.debug("Auto-lock re-enabled after delay")
        self.start_mouse_monitor()

    def stop_listeners(self):
        self._key_listener.stop()

    def _on_close(self):
        self.stop_listeners()
        self.root.destroy()
