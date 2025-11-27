import logging
import time
import tkinter as tk
from typing import Optional, Callable

import pyautogui
from pynput import keyboard

from src.config import (
    CURSOR_HIDE_CHECK_TIMEOUT,
    MIN_TOGGLE_INTERVAL,
    MOUSE_CHECK_TIMEOUT,
    VISUAL_START_DELAY,
    VISUAL_CHECK_INTERVAL,
    VISUAL_CHANGE_THRESHOLD,
    VISUAL_SAMPLE_MARGINS,
)
from .utils import is_taskbar_focused, calc_change_ratio


class ScreenLocker:
    def __init__(
            self,
            root: tk.Tk,
            timeout_seconds: int,
            on_unlock: Optional[Callable[[], None]] = None
    ):
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
        self._visual_check_id: str | None = None
        self._visual_baseline = None
        self._visual_start_delay = VISUAL_START_DELAY
        self._visual_interval = VISUAL_CHECK_INTERVAL
        self._visual_change_threshold = VISUAL_CHANGE_THRESHOLD
        self._visual_margins = VISUAL_SAMPLE_MARGINS
        self.visual_detection_enabled = True
        self._last_toggle_time = 0.0
        self._on_unlock = on_unlock  # ← callback

        self.ctrl_pressed = False
        self.shift_pressed = False
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
        elif key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift_pressed = True
        else:
            vk = getattr(key, 'vk', None)
            if self.ctrl_pressed and self.shift_pressed and vk == 0x42:
                self.root.after(0, self.toggle_lock)

        if self.auto_lock_enabled and not self.locked:
            self._mark_activity()
            logging.debug(f"Key event: {key}")

    def _on_release(self, key):
        if key in {keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}:
            self.ctrl_pressed = False
        elif key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            self.shift_pressed = False

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
            self._mark_activity(now)
        else:
            elapsed = now - self.last_activity_time
            if elapsed >= self.timeout_seconds:
                if self._visual_check(force=True):
                    self.start_mouse_monitor()
                    return
                self.root.after(0, self.lock_screen)
                return
            self._maybe_schedule_visual_check(now)

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
        win.after(CURSOR_HIDE_CHECK_TIMEOUT, self.check_cursor_visibility)
        self.locker_window = win
        logging.debug("Lock window created.")

    def locked_mouse_motion(self, event):
        """Handles mouse motion in locked mode – updates activity and shows cursor."""
        self._mark_activity()
        if self.locker_window and self.locker_window['cursor'] == 'none':
            self.locker_window.config(cursor='')
            logging.debug("Cursor shown due to mouse motion in locked mode.")

    def check_cursor_visibility(self):
        """Hides cursor if inactivity duration exceeds threshold."""
        if self.locker_window is None:
            return
        if self.locker_window['cursor'] != 'none':
            elapsed = time.time() - self.last_activity_time
            if elapsed * 1000 >= CURSOR_HIDE_CHECK_TIMEOUT:
                self.locker_window.config(cursor='none')
                logging.debug("Cursor hidden due to inactivity.")
        self.locker_window.after(CURSOR_HIDE_CHECK_TIMEOUT, self.check_cursor_visibility)

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
        self._mark_activity()
        logging.debug("Screen unlocked.")

        if self._on_unlock:
            try:
                self._on_unlock()
            except Exception as e:
                logging.debug(f"on_unlock callback error: {e}")

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
        self._clear_visual_monitor()

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

    def _mark_activity(self, now: float | None = None):
        """Resets inactivity timers and cancels visual checks."""
        self.last_activity_time = now if now is not None else time.time()
        self._clear_visual_monitor()

    def _clear_visual_monitor(self):
        """Cancels scheduled visual detection and drops baseline."""
        self._visual_baseline = None
        if self._visual_check_id:
            try:
                self.root.after_cancel(self._visual_check_id)
            except Exception:
                pass
            self._visual_check_id = None

    def _maybe_schedule_visual_check(self, now: float):
        """Schedules a visual snapshot if inactivity exceeded the start delay."""
        if (self._visual_check_id or self.locked or not self.auto_lock_enabled or
                not self.visual_detection_enabled):
            return
        if now - self.last_activity_time >= self._visual_start_delay:
            self._visual_check_id = self.root.after(0, self._scheduled_visual_check)

    def _scheduled_visual_check(self):
        """Runs visual detection and reschedules if still idle."""
        self._visual_check_id = None
        detected = self._visual_check()
        if detected:
            return

        if not self.locked and self.auto_lock_enabled:
            elapsed = time.time() - self.last_activity_time
            if elapsed >= self._visual_start_delay:
                self._visual_check_id = self.root.after(
                    int(self._visual_interval * 1000),
                    self._scheduled_visual_check
                )

    def _visual_check(self, force: bool = False) -> bool:
        """Compares screenshots to detect motion; returns True if activity detected."""
        if (self.locked or not self.auto_lock_enabled or
                not self.visual_detection_enabled):
            self._clear_visual_monitor()
            return False

        now = time.time()
        elapsed = now - self.last_activity_time
        if not force and elapsed < self._visual_start_delay:
            return False

        snapshot = self._capture_sample()
        if snapshot is None:
            return False

        if self._visual_baseline is None:
            self._visual_baseline = snapshot
            logging.debug("Visual baseline captured.")
            return False

        change_ratio = calc_change_ratio(self._visual_baseline, snapshot)
        self._visual_baseline = snapshot
        logging.debug(f"Visual change ratio: {change_ratio:.4f}")

        if change_ratio >= self._visual_change_threshold:
            logging.debug(f"Visual activity detected ({change_ratio * 100:.2f}% change)")
            self._mark_activity(now)
            return True
        return False

    def _capture_sample(self):
        """Takes a downscaled grayscale screenshot of the configured area to reduce CPU use."""
        try:
            width = self.root.winfo_screenwidth()
            height = self.root.winfo_screenheight()
            margins = self._visual_margins or {}

            def _ratio(key: str) -> float:
                value = margins.get(key, 0.0)
                try:
                    return max(0.0, min(1.0, float(value)))
                except (TypeError, ValueError):
                    return 0.0

            left_px = int(width * _ratio("left"))
            right_px = int(width * _ratio("right"))
            top_px = int(height * _ratio("top"))
            bottom_px = int(height * _ratio("bottom"))

            if left_px + right_px >= width:
                left_px = 0
                right_px = 0
            if top_px + bottom_px >= height:
                top_px = 0
                bottom_px = 0

            box_w = max(1, width - left_px - right_px)
            box_h = max(1, height - top_px - bottom_px)
            img = pyautogui.screenshot(region=(left_px, top_px, box_w, box_h))
            scaled_w = 320 if box_w >= 320 else box_w
            scaled_h = max(90, int(box_h * scaled_w / max(box_w, 1)))
            return img.resize((scaled_w, scaled_h)).convert("L")
        except Exception as e:
            logging.debug(f"Visual sample failed: {e}")
            return None

    def update_visual_settings(self, enabled: bool, margins: dict | None, threshold: float | None):
        """Updates runtime parameters for visual detection."""
        self.visual_detection_enabled = bool(enabled)
        if margins:
            try:
                self._visual_margins = {key: float(value) for key, value in margins.items()}
            except Exception:
                self._visual_margins = VISUAL_SAMPLE_MARGINS
        else:
            self._visual_margins = VISUAL_SAMPLE_MARGINS

        try:
            self._visual_change_threshold = max(0.0, float(threshold))
        except (TypeError, ValueError):
            self._visual_change_threshold = VISUAL_CHANGE_THRESHOLD

        if not self.visual_detection_enabled:
            self._clear_visual_monitor()
