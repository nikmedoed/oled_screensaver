import logging
import os
import platform
import signal
import sys
import time

from PIL import Image, ImageDraw

from config import PID_FILE


def format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    return f"{hours} hour{'s' if hours != 1 else ''}"


_cached_tray_image = None


def create_tray_image():
    global _cached_tray_image
    if _cached_tray_image is None:
        width = height = 64
        img = Image.new('RGB', (width, height), "gray")
        draw = ImageDraw.Draw(img)
        draw.ellipse((8, 8, width - 8, height - 8), fill="black")
        _cached_tray_image = img
    return _cached_tray_image


if sys.platform == 'win32':
    import ctypes

    user32 = ctypes.WinDLL('user32', use_last_error=True)
    GetForegroundWindow = user32.GetForegroundWindow
    GetClassNameW = user32.GetClassNameW


    def is_taskbar_focused() -> bool:
        hwnd = GetForegroundWindow()
        if not hwnd:
            return False
        buf = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, buf, 256)
        cls = buf.value
        return cls in {"Shell_TrayWnd", "TrayStartWnd", "DV2ControlHost"}

else:
    def is_taskbar_focused() -> bool:
        return False


def terminate_pid(pid: int):
    """Terminate the given PID: SIGTERM on POSIX, TerminateProcess on Windows."""
    try:
        if platform.system() == "Windows":
            PROCESS_TERMINATE = 0x0001
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if handle:
                ctypes.windll.kernel32.TerminateProcess(handle, -1)
                ctypes.windll.kernel32.CloseHandle(handle)
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception as e:
        logging.debug(f"Failed to terminate old instance {pid}: {e}")


def kill_previous_instance():
    """Kill previous running instance if exists and write our PID."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            terminate_pid(old_pid)
            time.sleep(0.5)
        except Exception as ex:
            logging.debug(f"Error reading/killing previous PID: {ex}")
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception as ex:
        logging.debug(f"Error writing PID file: {ex}")
