<p align="center">
  <img src="xadb.ico" alt="Xtreme ADB Icon" width="128">
</p>

<h1 align="center">Xtreme ADB V1</h1>

<p align="center">
  <a href="https://github.com/KPR-MAN/XtremeADB"><img src="https://img.shields.io/badge/Repo-GitHub-blueviolet" alt="Repo"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey" alt="Platform">
  <img src="https://img.shields.io/badge/License-Attribution%20Required-orange" alt="License">
</p>

**The Ultimate All-in-One Android Toolkit.**
Xtreme ADB is a powerful, multi-threaded GUI for managing Android devices. It combines advanced features like Fastboot flashing, Wireless Pairing, and App Management into a sleek, modern interface.

---

## DISCLAIMER & WARNINGS

**PLEASE READ THIS CAREFULLY BEFORE USING THIS TOOL.**

```text
I am not responsible for bricked devices, dead SD cards, thermonuclear war, 
or you getting fired because the alarm app failed. 

YOU are choosing to make these modifications, and if you point the finger at me 
for messing up your device, I will laugh at you.
```

### Critical Warnings:
1.  **Fastboot Mode:** The "Fastboot Tools" section allows you to flash images (`recovery.img`, `boot.img`) and unlock your bootloader. **Improper use of these features CAN brick your device.** Do not use these buttons unless you understand exactly what you are doing.
2.  **Root Features:** Some features (like extracting protected APKs or modifying system flags) may require Root access.
3.  **Data Loss:** Unlocking a bootloader usually wipes all user data. **Always backup your data** before performing advanced operations.
4.  **Drivers:** Ensure you have the correct USB Drivers installed for your specific phone brand.

---

## Features

*   **Modern UI:** A clean "Material Glass" design with full Light/Dark mode support.
*   **Live Dashboard:** Real-time monitoring of Battery and RAM.
*   **App Manager:** Bulk install APKs, uninstall system apps, force stop, and extract APKs to PC.
*   **File Explorer:** Full GUI file manager to Copy, Paste, Rename, Delete, Upload, and Download files.
*   **Fastboot & Recovery:** Boot live images without flashing, flash recovery/boot, and sideload ZIPs.
*   **Wireless ADB:** Built-in pairing tool for Android 11+ (Pairing Code support) and TCP/IP toggler.
*   **Tweaks:** Change DPI, Resolution, Animation Scales, and toggle visual pointers.
*   **Backup & Restore:** Create full system backups (`.ab` files) and restore them.
*   **Logcat:** Color-coded real-time log stream to easily spot errors.

---

## Screenshots

<p align="center">
  <img src="screenshots/ss1.png" alt="Dashboard View" width="75%">
</p>
<p align="center">
  <img src="screenshots/ss2.png" alt="App Manager View" width="75%">
</p>

---

## Installation & Usage

### Prerequisites
1.  **Python 3.10+**: [Download Here](https://www.python.org/)
2.  **ADB & Fastboot**: Must be installed and added to your system `PATH`. [Google Platform Tools](https://developer.android.com/studio/releases/platform-tools)

### Setup
1.  Open your terminal/command prompt.
2.  Install the required UI library:
    ```bash
    pip install customtkinter
    ```
3.  Run the tool:
    ```bash
    python xadb.py
    ```

---

## Troubleshooting

*   **"No Device" is shown:**
    *   Ensure your cable is good.
    *   Ensure ADB drivers are installed for your specific phone.
    *   Try running `adb kill-server` and `adb start-server` in a separate terminal.
*   **App Freezes:**
    *   The app has a timeout to prevent freezing, but if it hangs, the ADB connection might be unstable. Reconnect the USB cable.

---

## License & Credits

**License: MIT (Modified for Attribution)**

You are free to:
*   Use this software for personal or commercial use.
*   Modify the source code.
*   Distribute or Fork this project.

**Under the following condition:**
*   **Attribution Required:** You **MUST** give appropriate credit to the original author in your software, documentation, or repository. For example: `Based on Xtreme ADB by KPR-MAN (https://github.com/KPR-MAN/XtremeADB)`.

---

**Made With ❤️ By [KPR-MAN](https://github.com/KPR-MAN/XtremeADB).**
