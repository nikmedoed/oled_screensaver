import logging
import os
import platform
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox

import pystray
from PIL import ImageTk
from pystray import MenuItem as item, Menu

from src.ScreenSaver import ScreenLocker
from src.config import (
    DEV_MODE,
    SECONDS_IN_MINUTE,
    PID_FILE,
    SettingsStore,
)
from src.utils import format_duration, create_tray_image, kill_previous_instance


class TrayApp:
    def __init__(self):
        if DEV_MODE:
            logging.info("Running in developer mode")

        self.last_delay_label: str = ""
        self.root = tk.Tk()
        self.root.withdraw()
        self.settings_icon_image: ImageTk.PhotoImage | None = None
        self.settings = SettingsStore()
        self._init_settings_state()
        self.zone_overlay: tk.Toplevel | None = None

        self.locker = ScreenLocker(
            self.root,
            timeout_seconds=self.settings.timeout_seconds,
            on_unlock=self._recreate_icon_after_unlock
        )
        if hasattr(self.locker, "update_visual_settings"):
            self.locker.update_visual_settings(
                self.settings.visual_monitor_enabled,
                self.settings.visual_margins,
                self.settings.visual_threshold
            )

        self.icon: pystray.Icon | None = None
        self._icon_thread = None
        self.settings_window: tk.Toplevel | None = None
        self._setup_tray()

    def _init_settings_state(self):
        self._parsed_minutes_cache: list[int] | None = None
        self.timeout_var = tk.StringVar(value=str(self.settings.timeout_seconds))
        self.mouse_check_var = tk.StringVar(value=str(self.settings.mouse_check_ms))
        self.cursor_hide_var = tk.StringVar(value=str(self.settings.cursor_hide_ms))
        pause_values = self.settings.pause_minutes
        self.pause_minutes_var = tk.StringVar(
            value=", ".join(str(n) for n in pause_values)
        )
        self.visual_threshold_var = tk.StringVar(
            value=str(round(self.settings.visual_threshold * 100, 3))
        )
        self.visual_zone_order = ("top", "bottom", "left", "right")
        self.visual_zone_vars = {}
        self._zone_pairs = {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}
        self._zone_update_in_progress = False
        visual_margins = self.settings.visual_margins
        for key in self.visual_zone_order:
            raw_value = visual_margins.get(key, 0.0)
            percent_value = raw_value * 100
            percent_str = f"{percent_value:.3f}".rstrip("0").rstrip(".")
            var = tk.StringVar(value=percent_str or "0")
            var.trace_add("write", self._make_zone_trace_callback(key))
            self.visual_zone_vars[key] = var
        self.visual_detection_var = tk.BooleanVar(value=self.settings.visual_monitor_enabled)
        self.show_zone_var = tk.BooleanVar(value=True)
        self.show_zone_var.trace_add("write", lambda *_: self._toggle_visual_zone_overlay())

        self.settings_icon_image = ImageTk.PhotoImage(create_tray_image())
        self.pause_minutes_error = tk.StringVar(value="")
        self.pause_minutes_entry = None
        self.pause_minutes_entry_default_bg = None
        self.pause_minutes_error_label = None
        self.pause_minutes_var.trace_add("write", lambda *_: self._validate_minutes_list())

    def _setup_tray(self):
        image = create_tray_image()

        delay_items = [
            item(format_duration(minutes), self._make_delay_action(minutes))
            for minutes in self.settings.pause_minutes
        ]

        menu = Menu(
            item(lambda _:
                 f"Auto-lock {'ENABLED' if self.locker.auto_lock_enabled else 'DISABLED'}",
                 None, enabled=False),
            item(lambda _:
                 f">> until "
                 f"{datetime.fromtimestamp(self.locker.delayed_until).strftime('%H:%M:%S')} "
                 f"({self.last_delay_label})",
                 None, enabled=False,
                 visible=lambda _:
                 self.locker.delayed_until is not None),
            item("Toggle Lock manually", self._toggle, default=True),
            item(lambda _:
                 "Disable auto-lock" if self.locker.auto_lock_enabled else "Enable auto-lock",
                 lambda _,: self.locker.toggle_auto_lock()),
            Menu.SEPARATOR,
            *delay_items,
            Menu.SEPARATOR,
            item("Settings", self._open_settings),
            Menu.SEPARATOR,
            item("Exit", self._quit)
        )

        self.icon = pystray.Icon("ScreenLocker", image, "ScreenLocker", menu)
        if platform.system() == "Windows":
            self.icon._on_left_up = self._toggle
        else:
            self.icon.on_clicked = self._toggle

    def _start_icon(self):
        self.icon.run_detached()
        self._icon_thread = getattr(self.icon, "_thread", None)

    def _recreate_icon_after_unlock(self):
        """Вызывается ScreenLocker'ом сразу после разблокировки."""
        try:
            if self.icon:
                self.icon.stop()
            if self._icon_thread and self._icon_thread.is_alive():
                self._icon_thread.join(timeout=1)
        except Exception as e:
            logging.debug(f"Error stopping old icon: {e}")

        self._setup_tray()
        self._start_icon()
        logging.debug("Tray icon recreated after unlock")

    def _make_delay_action(self, minutes):
        def _action(icon, item):
            self.last_delay_label = item.text
            self.locker.disable_auto_lock_for(minutes * SECONDS_IN_MINUTE)
            logging.debug(f"Auto-lock paused for {minutes} minutes")

        return _action

    def _toggle(self, icon, item=None):
        self.root.after(0, self.locker.toggle_lock)

    def _open_settings(self, icon, item):
        self.root.after(0, self._show_settings_window)

    def _show_settings_window(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        self.settings_window = tk.Toplevel(self.root)
        self.settings_window.title("Settings")
        self.settings_window.resizable(True, False)
        self.settings_window.protocol("WM_DELETE_WINDOW", self._close_settings_window)
        if self.settings_icon_image:
            self.settings_window.iconphoto(False, self.settings_icon_image)

        content = ttk.Frame(self.settings_window, padding=(20, 16, 20, 16))
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=1)

        form_frame = ttk.Frame(content)
        form_frame.grid(row=0, column=0, sticky="nwe")
        self._build_settings_form(form_frame)

        buttons = ttk.Frame(content)
        buttons.grid(row=1, column=0, sticky="e", pady=(10, 0))

        cancel_btn = ttk.Button(buttons, text="Cancel", command=self._close_settings_window)
        cancel_btn.grid(row=0, column=0, padx=(0, 10))

        save_btn = ttk.Button(buttons, text="Save", command=self._on_save_settings)
        save_btn.grid(row=0, column=1)
        self._center_window(self.settings_window)
        self._update_visual_zone_overlay()

    def _build_settings_form(self, container):
        container.columnconfigure(1, weight=1, minsize=360)
        row = 0

        self._add_labeled_entry(container, "Таймаут бездействия для лока (сек)", self.timeout_var, row)
        row += 1

        self._add_labeled_entry(container, "Частота проверки курсора (мс)", self.mouse_check_var, row)
        row += 1

        self._add_labeled_entry(container, "Скрывать курсор через (мс, 0 = не скрывать)", self.cursor_hide_var, row)
        row += 1

        self.pause_minutes_entry = self._add_labeled_entry(container, "Минуты для паузы автолока (через запятую)",
                                                           self.pause_minutes_var, row)
        if self.pause_minutes_entry_default_bg is None:
            self.pause_minutes_entry_default_bg = self.pause_minutes_entry.cget("background")
        row += 1

        error = tk.Label(
            container,
            textvariable=self.pause_minutes_error,
            anchor="w",
            fg="red",
        )
        error.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.pause_minutes_error_label = error
        row += 1

        zones_label = ttk.Label(
            container,
            text="Зона отслеживания визуальной активности",
            anchor="w"
        )
        zones_label.grid(row=row, column=0, sticky="w", pady=(10, 4))
        controls = ttk.Frame(container)
        controls.grid(row=row, column=1, sticky="ew", pady=(10, 4))
        controls.columnconfigure(0, weight=1)
        detect_toggle = ttk.Checkbutton(
            controls,
            text="Отслеживать",
            variable=self.visual_detection_var
        )
        detect_toggle.grid(row=0, column=0, sticky="w")
        show_toggle = ttk.Checkbutton(
            controls,
            text="Показать",
            variable=self.show_zone_var
        )
        show_toggle.grid(row=0, column=1, sticky="e")
        row += 1

        zone_titles = {
            "top": "сверху",
            "bottom": "снизу",
            "left": "слева",
            "right": "справа",
        }
        for zone in self.visual_zone_order:
            var = self.visual_zone_vars.get(zone)
            label_text = f"Отступ {zone_titles.get(zone, zone)} (%)"
            self._add_percent_entry(container, label_text, var, row)
            row += 1

        self._add_labeled_entry(
            container,
            "Порог визуальной активности (%)",
            self.visual_threshold_var,
            row,
        )
        row += 1

        self._validate_minutes_list()

    def _add_labeled_entry(self, container, label_text, text_var, row, **entry_kwargs):
        label = ttk.Label(container, text=label_text, anchor="w")
        label.grid(row=row, column=0, sticky="w", pady=(0, 6), padx=(0, 12))
        entry = tk.Entry(container, textvariable=text_var, **entry_kwargs)
        entry.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        return entry

    def _add_percent_entry(self, container, label_text, text_var, row):
        label = ttk.Label(container, text=label_text, anchor="w")
        label.grid(row=row, column=0, sticky="w", pady=(0, 6), padx=(0, 12))
        spin = tk.Spinbox(
            container,
            from_=0,
            to=100,
            increment=0.5,
            textvariable=text_var,
            width=10
        )
        spin.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        return spin

    def _on_save_settings(self):
        if not self._save_settings():
            return
        self._close_settings_window()

    def _parse_minutes_input(self) -> list[int]:
        value = self.pause_minutes_var.get().strip()
        if not value:
            raise ValueError("empty")
        parts = [part.strip() for part in value.split(",")]
        parsed: list[int] = []
        for part in parts:
            if not part:
                raise ValueError("invalid")
            parsed.append(int(part))
        if not parsed:
            raise ValueError("invalid")
        return parsed

    def _validate_minutes_list(self):
        try:
            parsed = self._parse_minutes_input()
        except ValueError as exc:
            if str(exc) == "empty":
                self.pause_minutes_error.set("Укажите хотя бы одно значение.")
            else:
                self.pause_minutes_error.set("Введите целые числа через запятую.")
            self._parsed_minutes_cache = None
            self._set_minutes_entry_state(invalid=True)
            self._update_minutes_error_visibility()
            return False

        self._parsed_minutes_cache = parsed
        self.pause_minutes_error.set("")
        self._set_minutes_entry_state(invalid=False)
        self._update_minutes_error_visibility()
        return True

    def _set_minutes_entry_state(self, invalid):
        if not self.pause_minutes_entry:
            return
        if self.pause_minutes_entry_default_bg is None:
            self.pause_minutes_entry_default_bg = self.pause_minutes_entry.cget("background")
        self.pause_minutes_entry.configure(
            background="#ffe6e6" if invalid else self.pause_minutes_entry_default_bg
        )

    def _update_minutes_error_visibility(self):
        if not self.pause_minutes_error_label:
            return
        if self.pause_minutes_error.get():
            self.pause_minutes_error_label.grid()
        else:
            self.pause_minutes_error_label.grid_remove()

    def _save_settings(self) -> bool:
        if not self._validate_minutes_list():
            messagebox.showerror("Settings", "Исправьте список минут перед сохранением.")
            return False

        try:
            timeout_seconds = max(1, int(self.timeout_var.get()))
            mouse_check_ms = max(1, int(self.mouse_check_var.get()))
            cursor_hide_ms = max(0, int(self.cursor_hide_var.get()))
            minutes_list = self._parsed_minutes_cache or self._parse_minutes_input()
            threshold_percent = float(self.visual_threshold_var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Settings", "Проверьте числовые значения.")
            return False

        visual_margins = {}
        for zone, var in self.visual_zone_vars.items():
            pct_value = self._parse_percent(var.get())
            if pct_value is None or pct_value < 0.0 or pct_value > 100.0:
                messagebox.showerror("Settings", f"Неверное значение для зоны '{zone}'.")
                return False
            visual_margins[zone] = pct_value / 100.0

        if visual_margins["top"] + visual_margins["bottom"] > 1.0:
            messagebox.showerror("Settings", "Сумма верхнего и нижнего отступов не должна превышать 100%.")
            return False
        if visual_margins["left"] + visual_margins["right"] > 1.0:
            messagebox.showerror("Settings", "Сумма левого и правого отступов не должна превышать 100%.")
            return False

        visual_threshold = max(0.0, threshold_percent / 100.0)
        visual_monitor_enabled = self.visual_detection_var.get()

        self.settings.update({
            "timeout_seconds": timeout_seconds,
            "mouse_check_ms": mouse_check_ms,
            "cursor_hide_ms": cursor_hide_ms,
            "pause_minutes": minutes_list,
            "visual_threshold": visual_threshold,
            "visual_margins": visual_margins,
            "visual_monitor_enabled": visual_monitor_enabled,
        })
        self.settings.save()

        if hasattr(self.locker, "update_timeout"):
            self.locker.update_timeout(timeout_seconds)
        else:
            self.locker.timeout_seconds = timeout_seconds
        if hasattr(self.locker, "update_visual_settings"):
            self.locker.update_visual_settings(
                visual_monitor_enabled,
                visual_margins,
                visual_threshold
            )
        self._parsed_minutes_cache = minutes_list
        self._recreate_icon_after_unlock()
        logging.info("Settings saved to %s", self.settings.path)
        return True

    def _close_settings_window(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.settings_window = None
        self._destroy_visual_zone_overlay()

    def _quit(self, icon, item):
        logging.info("Exiting...")
        self.locker.stop_listeners()
        icon.stop()
        self.root.after(0, self.root.destroy)
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

    def _schedule_icon_check(self):
        try:
            if self._icon_thread and not self._icon_thread.is_alive():
                logging.warning("Tray icon thread died — restarting...")
                self._recreate_icon_after_unlock()
        except Exception as e:
            logging.debug(f"Error checking tray thread: {e}")
        finally:
            self.root.after(10_000, self._schedule_icon_check)

    def run(self):
        self._start_icon()
        self._schedule_icon_check()
        self.root.mainloop()

    def _center_window(self, window: tk.Toplevel):
        try:
            window.update_idletasks()
            width = window.winfo_width()
            height = window.winfo_height()
            screen_w = window.winfo_screenwidth()
            screen_h = window.winfo_screenheight()
            x = max((screen_w - width) // 2, 0)
            y = max((screen_h - height) // 2, 0)
            window.geometry(f"{width}x{height}+{x}+{y}")
        except tk.TclError:
            pass

    def _toggle_visual_zone_overlay(self):
        if self.show_zone_var.get():
            self._update_visual_zone_overlay()
        else:
            self._destroy_visual_zone_overlay()

    def _destroy_visual_zone_overlay(self):
        if self.zone_overlay and self.zone_overlay.winfo_exists():
            try:
                self.zone_overlay.destroy()
            except tk.TclError:
                pass
        self.zone_overlay = None

    def _update_visual_zone_overlay(self):
        if not (self.settings_window and self.settings_window.winfo_exists() and self.show_zone_var.get()):
            self._destroy_visual_zone_overlay()
            return

        if not self.zone_overlay or not self.zone_overlay.winfo_exists():
            overlay = tk.Toplevel(self.root)
            overlay.withdraw()
            overlay.overrideredirect(True)
            try:
                overlay.attributes("-alpha", 0.25)
            except tk.TclError:
                pass
            overlay.configure(background="#00bcd4")
            self.zone_overlay = overlay

        margins = self._current_visual_margins()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        left = int(screen_w * margins.get("left", 0.0))
        right = int(screen_w * margins.get("right", 0.0))
        top = int(screen_h * margins.get("top", 0.0))
        bottom = int(screen_h * margins.get("bottom", 0.0))

        width = max(10, screen_w - left - right)
        height = max(10, screen_h - top - bottom)
        x = max(left, 0)
        y = max(top, 0)

        geometry = f"{width}x{height}+{x}+{y}"
        self.zone_overlay.geometry(geometry)
        try:
            self.zone_overlay.deiconify()
            if self.settings_window and self.settings_window.winfo_exists():
                self.zone_overlay.lift()
                self.zone_overlay.lower(self.settings_window)
                self.settings_window.lift()
        except tk.TclError:
            pass

    def _current_visual_margins(self):
        margins = {}
        for zone, var in self.visual_zone_vars.items():
            pct = self._parse_percent(var.get())
            if pct is None:
                pct = self.settings.visual_margins.get(zone, 0.0) * 100
            margins[zone] = max(0.0, min(100.0, pct)) / 100.0
        return margins

    def _make_zone_trace_callback(self, zone):
        def _callback(*_):
            if self._zone_update_in_progress:
                return
            self._zone_update_in_progress = True
            try:
                self._enforce_zone_constraints(zone)
            finally:
                self._zone_update_in_progress = False
            self._update_visual_zone_overlay()

        return _callback

    def _enforce_zone_constraints(self, zone):
        var = self.visual_zone_vars.get(zone)
        if not var:
            return
        current = self._parse_percent(var.get())
        if current is None:
            return
        current = max(0.0, min(100.0, current))
        var.set(self._format_percent(current))

        pair_zone = self._zone_pairs.get(zone)
        if not pair_zone:
            return
        pair_var = self.visual_zone_vars.get(pair_zone)
        if not pair_var:
            return
        pair_value = self._parse_percent(pair_var.get())
        if pair_value is None:
            pair_value = 0.0
        pair_value = max(0.0, min(100.0, pair_value))
        if current + pair_value > 100.0:
            pair_value = max(0.0, 100.0 - current)
            pair_var.set(self._format_percent(pair_value))

    def _parse_percent(self, raw: str | None):
        if raw is None:
            return None
        text = raw.strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _format_percent(self, value: float):
        text = f"{value:.3f}".rstrip("0").rstrip(".")
        return text or "0"


if __name__ == "__main__":
    kill_previous_instance()
    TrayApp().run()
