# OLED Screensaver

**A lightweight fullscreen black screen utility to protect OLED displays from burn-in.**

This script automatically shows a black fullscreen window after a period of inactivity, with global hotkey support and a
tray icon for control. Ideal for OLED monitors or laptops.

---

## ✅ Features

- **Auto-activation** after 2 minutes of inactivity (keyboard & mouse).
- **Global hotkey** `Ctrl+B` to manually toggle the black screen.
- **Unlock by any mouse movement or key press.**
- **Cursor hiding** after 5 seconds of inactivity while locked.
- **System tray menu**:
    - Status indicator (auto-lock enabled/disabled, paused duration).
    - Manual toggle lock.
    - Pause auto-lock for predefined intervals (15–720 min).
    - Enable/disable auto-lock.
    - Exit application.
- **Developer mode** with a 5-second timeout (`python black.py dev`).
- Cross-platform support via `pystray`, `tkinter`, `pyautogui`, `pynput`.

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

- Toggle lock manually anytime with `Ctrl+B`.
- Auto-lock activates after 2 minutes by default.
- Click anywhere, press a key, or move the mouse to unlock.
- Control via the tray icon.

---

## ⚙️ Installation

1. Ensure Python 3 is installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Or manually:
   ```bash
   pip install Pillow pyautogui pystray pynput
   ```

---

## 🚀 Autostart on Windows

1. Use provided batch scripts (`screensaver.bat` or `screensaver dev.bat`).
2. Autostart setup:
    - Press `Win + R`, type `shell:startup`, press Enter.
    - Copy the desired `.bat` file into the startup folder.

   Modify the `.bat` file if Python isn't in your PATH:
   ```bat
   start "" "C:\path\to\pythonw.exe" "%~dp0black.py"
   ```

---

## 📂 File Structure

```
.
├── src/
│   ├── ScreenSaver.py        # Core screen locking logic
│   └── utils.py              # Helper functions
├── black.py                  # App launcher and tray integration
├── config.py                 # Configuration constants and settings
├── README.md                 # This documentation
├── requirements.txt          # Python dependencies
├── screensaver.bat           # Batch script for regular use
├── screensaver dev.bat       # Batch script for dev mode
└── .gitattributes            # Git line-ending configuration
```

---

## 🧠 Ideas & TODO

- [ ] Detect video playback to avoid unintended locking.
- [ ] Add configuration UI for customizing timeout and hotkey.
- [ ] Optional auto-unlock after detecting user activity.
- [ ] Enhanced multi-monitor support.

---

## 🧪 Developer Notes

- Windows: Left-click tray icon to toggle screen lock.
- Linux/macOS: Tray menu fully functional; click behavior may differ.
- Check for hotkey conflicts on your system.
- Customize global hotkey in `ScreenSaver.py`.

Windows build
```powershell
pyinstaller --clean --onefile --windowed --name oledSaver --icon "$PWD\icon\icon.ico" black.py
```

---

Made with ❤️ to protect your OLED screen and your peace of mind.

