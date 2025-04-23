import sys

from PIL import Image, ImageDraw


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
