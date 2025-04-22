# OLED Screensaver

**A lightweight fullscreen black screen utility to protect OLED displays from burn-in.**

This script automatically shows a black fullscreen window after a period of inactivity, with global hotkey support and a tray icon for control. Ideal for OLED monitors or laptops.

---

## ✅ Features

- **Auto-activation** after 2 minutes of inactivity (keyboard & mouse).
- **Global hotkey** `Ctrl+B` to manually toggle the black screen.
- **Unlock by any mouse movement or key press.**
- **Cursor hiding** after 5 seconds of inactivity while locked.
- **System tray menu**:
  - Status (enabled / disabled / paused).
  - Manual toggle.
  - Pause auto-lock (15–720 min).
  - Toggle auto-lock.
  - Exit the app.
- **Developer mode** with a 5-second timeout (`python black.py dev`).
- **Hotkeys are re-registered every 10 seconds** for reliability.
- Cross-platform support via `pystray`, `tkinter`, `keyboard`.

---

## 💻 Usage

- Launch the script:
  ```bash
  python black.py
  ```

- Developer/test mode (5-second timeout):
  ```bash
  python black.py dev
  ```

- Toggle lock manually at any time with `Ctrl+B`.
- Auto-lock activates after 2 minutes by default.
- Click anywhere, press a key, or move the mouse to unlock.
- Control everything via the tray icon.

---

## ⚙️ Installation

1. Make sure Python 3 is installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Or manually:
   ```bash
   pip install keyboard Pillow pyautogui pystray pynput
   ```

---

## 🚀 Autostart on Windows

1. Use `screensaver.bat` or `screensaver dev.bat` from the repository.
2. To autostart:
   - Press `Win + R`, enter `shell:startup`, and press Enter.
   - Copy the appropriate `.bat` file into the opened folder.

   You can also modify the `.bat` file if Python is not in your PATH:
   ```bat
   start "" "C:\path\to\pythonw.exe" "C:\your\project\black.py"
   ```

---

## 📂 File Structure

```
.
├── ScreenSaver.py           # Core screen locking logic
├── black.py                 # App launcher and tray integration
├── README.md                # This file
├── requirements.txt         # Dependencies
├── screensaver.bat          # Batch launcher for regular use
├── screensaver dev.bat      # Batch launcher for dev mode
└── .gitattributes           # Git configuration for line endings
```

---

## 🧠 Ideas & TODO

- [ ] Detect video playback (e.g., full-screen YouTube) to avoid triggering lock.
- [ ] Add a configuration UI to change the timeout or hotkey.
- [ ] Optional: auto-hide the black screen after activity (in auto mode).
- [ ] Custom per-monitor support for multi-screen setups.

---

## 🧪 Dev Notes

- On Windows, you can left-click the tray icon to toggle the screen.
- On Linux/macOS, the tray menu works as expected, but click behavior may vary.
- Test hotkey conflicts with other global shortcuts before using it in production.
- You can change the global hotkey in the `ScreenSaver.py` source.

---

Made with ❤️ to protect your OLED screen and your peace of mind.