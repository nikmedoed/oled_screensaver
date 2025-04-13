# oled screensaver
Auto black screen for OLED displays.
- Press `ctrl+B` to manually activate the black screen.
- Automatically activates after 2 minutes of inactivity (no mouse or keyboard interaction).
- Click or press `ctrl+B` again to hide the black screen.

## Features:
- Hides cursor after inactivity.
- Raises the black screen window if activity is detected after activation.
- Auto-lock feature can be enabled or disabled from the tray menu.
- System tray integration for quick access.
- Developer mode for quicker testing (5-second timeout).
- Supports hotkeys (`ctrl+B`) globally.

## Setup:
Create a `.bat` file linked to your system's autorun to automatically launch the screensaver at startup.

## Ideas:
- [ ] Detect when a video is playing to avoid triggering the screensaver unnecessarily.
- [ ] Experiment with the "topmost" window mode:
  - Automatically displayed screen could hide itself after a while, while manual activation keeps it always on top.
  - Alternatively, require manual deactivation in all cases for more consistent behavior.
- [ ] Allow customizable timeout duration.
- [ ] Add a UI to configure the hotkey for toggling the screensaver.
- [ ] Enable activating the screensaver by clicking on the system tray icon.