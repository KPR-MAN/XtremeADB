import customtkinter as ctk
import subprocess
import threading
import os
import time
import re
import json
import datetime
import sys
import requests
import queue
import shlex
from packaging import version
from tkinter import filedialog, Canvas
from PIL import Image, ImageTk
from pathlib import Path

# ==========================================
# SPLASH SCREEN
# ==========================================
class SplashScreen:
    def __init__(self):
        self.bk = Backend()
        self.root = ctk.CTk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        img = Image.open("splash.png")
        w, h = img.size
        self.photo = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        ctk.CTkLabel(self.root, image=self.photo, text="").pack()
        self.root.update()

    def close(self):
        self.root.withdraw()

# ==========================================
# 1. CORE CONFIGURATION
# ==========================================
APP_NAME = "Xtreme ADB V2.2"
LOG_FILE = None
CURRENT_VERSION = "2.2"
UPDATE_URL = "https://raw.githubusercontent.com/KPR-MAN/XtremeADB/main/version.json"

DEFAULT_CONFIG = {
    "theme": "Dark",
    "last_ip": "",
    "auto_refresh": True,
    "refresh_interval": 3,
    "check_updates": True,
    "scrcpy_args": "--max-size 1024 --video-bit-rate 8M",
    "use_su": False,
    "app_sort": "a_z",
    "file_sort": "a_z",
    "suppress_multi_device_warn": False,
    "device_poll_interval": 2
}

if os.name == 'nt':
    CONFIG_FILE = Path(os.getenv('APPDATA')) / "XtremeADB" / "xtreme_config.json"
elif sys.platform == 'darwin':
    CONFIG_FILE = Path.home() / "Library" / "Application Support" / "XtremeADB" / "xtreme_config.json"
else:
    CONFIG_FILE = Path.home() / ".config" / "XtremeADB" / "xtreme_config.json"

CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE = CONFIG_FILE.parent / "xtreme_log.txt"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        return DEFAULT_CONFIG

def save_config(key, value):
    try:
        cfg = load_config()
        cfg[key] = value
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def log_action(message):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except:
        pass

CONF = load_config()
ctk.set_appearance_mode(CONF["theme"])
ctk.set_default_color_theme("dark-blue")

# --- UPDATE CHECKER FUNCTION ---
def check_for_updates():
    """Check for updates (standalone function)"""
    try:
        response = requests.get(UPDATE_URL, timeout=5)
        data = response.json()
        latest_version = data["version"]
        download_url = data["download_url"]

        if version.parse(latest_version) > version.parse(CURRENT_VERSION):
            return True, latest_version, download_url
        return False, None, None
    except:
        return False, None, None

# ==========================================
# 2. CONSTANTS & PALETTE
# ==========================================
ADB_PATH = "adb"
FASTBOOT_PATH = "fastboot"
SCRCPY_PATH = "scrcpy"

C = {
    "bg_root": ("#F0F2F5", "#090909"),
    "bg_sidebar": ("#FFFFFF", "#111111"),
    "bg_surface": ("#FFFFFF", "#1C1C1C"),
    "bg_hover": ("#E0E0E0", "#2D2D2D"),
    "input_bg": ("#E8E8E8", "#252525"),
    "primary": "#3B8ED0",
    "success": "#00C853",
    "warning": "#FFAB00",
    "danger": "#D50000",
    "text_main": ("#1A1A1A", "#FFFFFF"),
    "text_sub": ("#555555", "#999999"),
    "btn_active": ("#E0E0E0", "#252525"),
    "term_bg": ("#FFFFFF", "#000000"),
    "term_fg": ("#000000", "#00FF00"),
}


# Cross-platform font fallbacks
if sys.platform == "darwin":
    F_UI   = "Helvetica Neue"
    F_MONO = "Menlo"
elif os.name == "nt":
    F_UI   = "Segoe UI"
    F_MONO = "Consolas"
else:  # Linux
    F_UI   = "DejaVu Sans"
    F_MONO = "DejaVu Sans Mono"

RIGHT_CLICK = "<Button-2>" if sys.platform == "darwin" else "<Button-3>"

# ==========================================
# 3. CUSTOM WIDGETS
# ==========================================
class FluentButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.default_color = kwargs.get("fg_color", "transparent")
        self.default_text_color = kwargs.get("text_color", C["text_sub"])


    def set_active(self, is_active):
        if is_active:
            self.configure(fg_color=C["btn_active"], text_color=C["primary"])
        else:
            self.configure(fg_color=self.default_color, text_color=self.default_text_color)

class RadialProgress(ctk.CTkFrame):
    def __init__(self, master, title="Usage", size=120, color=C["primary"], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.size = size
        self.color = color
        self.percentage = 0
        initial_bg = "#1C1C1C" if ctk.get_appearance_mode() == "Dark" else "#FFFFFF"
        self.canvas = Canvas(self, width=size, height=size, highlightthickness=0, bg=initial_bg)
        self.canvas.pack()
        self.label = ctk.CTkLabel(self, text="0%", font=(F_UI, 18, "bold"), text_color=C["text_main"])
        self.label.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(self, text=title, font=(F_UI, 12), text_color=C["text_sub"]).pack(pady=5)
        self.bind("<Configure>", self.update_bg)
        self.draw()

    def update_bg(self, event=None):
        mode = ctk.get_appearance_mode()
        bg = "#FFFFFF" if mode == "Light" else "#1C1C1C"
        self.canvas.configure(bg=bg)
        self.label.configure(bg_color=bg)

    def draw(self):
        self.canvas.delete("all")
        w, h = self.size, self.size
        x, y, r = w / 2, h / 2, (w / 2) - 8
        track_col = "#333333" if ctk.get_appearance_mode() == "Dark" else "#E0E0E0"
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=track_col, width=8)
        angle = -(360 * (self.percentage / 100))
        if self.percentage > 0:
            self.canvas.create_arc(x - r, y - r, x + r, y + r, start=90, extent=angle, style="arc", outline=self.color, width=8)

    def set(self, val):
        self.percentage = max(0, min(val, 100))
        self.label.configure(text=f"{int(self.percentage)}%")
        self.draw()

class LogConsole(ctk.CTkFrame):
    """Read-only terminal box for displaying command output"""
    def __init__(self, master, height=150, **kwargs):
        super().__init__(master, fg_color=C["bg_surface"], corner_radius=10, **kwargs)
        self.pack_propagate(False)
        self.configure(height=height)

        # Header
        header = ctk.CTkFrame(self, height=25, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(header, text="> Terminal Output", font=(F_MONO, 11, "bold"), text_color=C["text_sub"]).pack(side="left")
        ctk.CTkButton(header, text="Clear", width=50, height=20, fg_color=C["input_bg"], text_color=C["text_main"],
                      font=(F_UI, 10), command=self.clear).pack(side="right")

        # Text Area
        self.text_area = ctk.CTkTextbox(
            self,
            font=(F_MONO, 12),
            fg_color=C["term_bg"],
            text_color=C["term_fg"],
            activate_scrollbars=True
        )
        self.text_area.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.text_area.configure(state="disabled")

    def log(self, message):
        self.text_area.configure(state="normal")
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.text_area.insert("end", f"[{ts}] {message}\n")
        self.text_area.see("end")
        self.text_area.configure(state="disabled")

    def clear(self):
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.configure(state="disabled")

# ==========================================
# 3b. CUSTOM DIALOG (replaces CTkMessagebox)
# ==========================================
class CustomDialog:
    """
    Native CTk modal dialog — works reliably in compiled (Nuitka/PyInstaller) apps.

    Usage:
        # Info / alert (one button):
        CustomDialog(parent, title="Done", message="All finished!", icon="info")

        # Confirm (two buttons) — call .get() to get the chosen label:
        dlg = CustomDialog(parent, title="Confirm", message="Delete?",
                           icon="warning", option_1="Yes", option_2="Cancel")
        if dlg.get() == "Yes":
            ...
    """
    _ICON_COLORS = {
        "info":    "#3B8ED0",
        "check":   "#00C853",
        "warning": "#FFAB00",
        "cancel":  "#D50000",
    }
    _ICON_LABELS = {
        "info":    "ℹ",
        "check":   "✔",
        "warning": "⚠",
        "cancel":  "✖",
    }

    def __init__(self, parent, title="", message="", icon="info",
                 option_1="Ok", option_2=None, option_3=None, width=420, height=None):
        self._result = None

        lines    = message.count("\n") + 1
        approx_h = 140 + lines * 22 + (50 if any([option_2, option_3]) else 0)
        height   = height or max(170, approx_h)

        dlg = ctk.CTkToplevel(parent)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()
        self._dlg = dlg

        parent.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - width)  // 2
        y = py + (ph - height) // 2
        dlg.geometry(f"{width}x{height}+{x}+{y}")

        accent = self._ICON_COLORS.get(icon, self._ICON_COLORS["info"])
        symbol = self._ICON_LABELS.get(icon, "ℹ")

        # Coloured accent strip at top
        ctk.CTkFrame(dlg, fg_color=accent, height=6, corner_radius=0).pack(fill="x")

        # Icon + title row
        top_row = ctk.CTkFrame(dlg, fg_color="transparent")
        top_row.pack(fill="x", padx=20, pady=(14, 0))
        ctk.CTkLabel(top_row, text=symbol, font=(F_UI, 22, "bold"),
                     text_color=accent).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(top_row, text=title, font=(F_UI, 15, "bold"),
                     text_color=C["text_main"]).pack(side="left")

        # Message body
        ctk.CTkLabel(dlg, text=message, font=(F_UI, 13),
                     text_color=C["text_main"],
                     wraplength=width - 50, justify="left").pack(padx=24, pady=(10, 16))

        # Buttons
        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 16))

        def _pick(label):
            self._result = label
            dlg.grab_release()
            dlg.destroy()

        options = [o for o in [option_1, option_2, option_3] if o]
        for i, opt in enumerate(options):
            fg = accent if i == 0 else C["input_bg"]
            tc = "white"  if i == 0 else C["text_main"]
            ctk.CTkButton(btn_row, text=opt, fg_color=fg, text_color=tc,
                          command=lambda o=opt: _pick(o)).pack(
                              side="left", expand=True, padx=4)

        # Block caller until dialog is closed (mirrors CTkMessagebox behaviour)
        parent.wait_window(dlg)

    def get(self):
        return self._result


# ==========================================
# 4. BACKEND ENGINE
# ==========================================
class Backend:
    @staticmethod
    def _no_window_kwargs():
        """Return kwargs that suppress terminal windows on all platforms."""
        kwargs = {}
        if os.name == "nt":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs["startupinfo"] = si
        else:
            # On Linux/macOS with Nuitka: ensure no inherited terminal FDs
            kwargs["close_fds"] = True
        return kwargs

    @staticmethod
    def run(cmd, timeout=10):
        if isinstance(cmd, str):
            cmd = cmd.split()
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout, **Backend._no_window_kwargs()
            )
            return res.stdout.strip() + res.stderr.strip()
        except Exception as e:
            return f"[ERROR] {str(e)}"

    @staticmethod
    def run_live(cmd, callback):
        """Run command and stream output to callback function"""
        if isinstance(cmd, str):
            cmd = cmd.split()
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace",
                **Backend._no_window_kwargs()
            )
            for line in iter(process.stdout.readline, ''):
                if line:
                    callback(line.strip())
            process.stdout.close()
            process.wait()
        except Exception as e:
            callback(f"[ERROR] {str(e)}")

    def get_devices(self):
        devices = []
        problem_serials = set()
        try:
            out = self.run([ADB_PATH, "devices"], timeout=5)
            for line in out.split("\n"):
                line = line.strip()
                if "\t" not in line:
                    continue
                serial, status = line.split("\t", 1)
                status = status.strip()
                if status == "device":
                    devices.append(f"{serial} (ADB)")
                elif status == "recovery":
                    devices.append(f"{serial} (RECOVERY)")
                elif status in ("unauthorized", "offline", "no permissions"):
                    problem_serials.add(serial)
            out_fb = self.run([FASTBOOT_PATH, "devices"], timeout=5)
            for line in out_fb.split("\n"):
                line = line.strip()
                if "\t" in line:
                    serial = line.split("\t")[0].strip()
                    if serial:
                        devices.append(f"{serial} (FASTBOOT)")
        except:
            pass
        if problem_serials:
            self._problem_serials = problem_serials
        return devices

    def get_stats(self, device_id):
        if "ADB" not in device_id: return {}
        clean = device_id.split()[0]
        stats = {"batt": 0, "ram": 0}
        try:
            batt = self.run([ADB_PATH, "-s", clean, "shell", "dumpsys", "battery"], timeout=2)

            for line in batt.split("\n"):
                line = line.strip()
                if line.startswith("level:"):
                    try:
                        stats["batt"] = int(line.split(":")[1].strip())
                        break
                    except:
                        pass
        except:
            pass

        try:
            mem = self.run([ADB_PATH, "-s", clean, "shell", "cat", "/proc/meminfo"], timeout=2)
            tot, av = 1, 1
            for line in mem.split("\n"):
                if "MemTotal" in line: tot = int(re.search(r"\d+", line).group())
                if "MemAvailable" in line: av = int(re.search(r"\d+", line).group())
            stats["ram"] = ((tot - av) / tot) * 100 if tot > 0 else 0
        except:
            pass

        return stats

    def get_device_info(self, device_id):
        if "ADB" not in device_id: return "Unknown", "Unknown"
        clean = device_id.split()[0]
        model = self.run([ADB_PATH, "-s", clean, "shell", "getprop", "ro.product.model"])
        android = self.run([ADB_PATH, "-s", clean, "shell", "getprop", "ro.build.version.release"])
        return model.strip(), android.strip()

# ==========================================
# 5. MAIN APPLICATION
# ==========================================
class XtremeADB(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()  # Hide main window during splash

        splash = ctk.CTkToplevel(self)
        splash.overrideredirect(True)
        splash.attributes("-topmost", True)

        img = Image.open("splash.png")
        w, h = img.size
        photo = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        splash.geometry(f"{w}x{h}+{x}+{y}")
        ctk.CTkLabel(splash, image=photo, text="").pack()
        splash.update()

        self.title(APP_NAME)
        self.geometry("1400x900")
        self.configure(fg_color=C["bg_root"])
        self.minsize(1100, 700)

        self.bk = Backend()
        self.sel_dev = None
        self.cur_path = "/sdcard/"
        self.log_proc = None
        self.nav_buttons = {}
        self.active_radials = []
        self.monitor_active = False
        self.file_buttons = []
        self.consoles = {}
        self.ctrl_pressed = False
        self._view_state = {}      # persists state per view across navigation
        self._current_view = None  # name of currently active view

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.init_ui()
        splash.destroy()
        self.deiconify()  # un-withdraw the main window — required on Linux/macOS
        if os.name == "nt":
            self.after(0, lambda: self.state('zoomed'))          # Windows
        elif sys.platform == "darwin":
            self.after(0, lambda: self.attributes('-zoomed', True))  # macOS
        else:
            self.after(0, lambda: self.attributes('-zoomed', True))  # Linux / WSL

        # -------------------------------
        # Set window icon cross-platform
        # -------------------------------
        try:
            if os.name == "nt":
                self.iconbitmap("xadb.ico")  # Windows
            else:
                icon_image = Image.open("xadb.png")
                icon_photo = ImageTk.PhotoImage(icon_image)
                self.iconphoto(True, icon_photo)  # Linux / macOS / WSL
                self._icon_ref = icon_photo
        except Exception as e:
            print(f"Could not set icon: {e}")

        threading.Thread(target=self.dev_loop, daemon=True).start()
        threading.Thread(target=self.stats_loop, daemon=True).start()

        # Check for Updates
        self.after(1000, self.check_updates_async)


    def check_updates_async(self):
        """Check for updates after UI is loaded — runs check in bg thread, shows dialog on main thread"""
        if not CONF["check_updates"]:
            return

        def _check():
            has_update, new_ver, url = check_for_updates()
            if has_update:
                self.after(0, lambda: self._show_update_dialog(new_ver, url))

        self.run_bg(_check)

    def _show_update_dialog(self, new_ver, url):
        """Native CTk update dialog — avoids CTkMessagebox icon-loading issues under Nuitka"""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Update Available")
        dlg.geometry("420x200")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()

        # Centre over main window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 420) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dlg.geometry(f"420x200+{x}+{y}")

        ctk.CTkLabel(dlg, text="Update Available",
                     font=(F_UI, 16, "bold"), text_color=C["primary"]).pack(pady=(20, 5))
        ctk.CTkLabel(dlg, text=f"Version v{new_ver} is available.\nWould you like to download it?",
                     font=(F_UI, 13), text_color=C["text_main"]).pack(pady=(0, 20))

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))

        def _download():
            import webbrowser
            webbrowser.open(url)
            dlg.destroy()

        def _never():
            save_config("check_updates", False)
            dlg.destroy()

        ctk.CTkButton(btn_row, text="Download", fg_color=C["success"],
                      command=_download).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_row, text="Later", fg_color=C["warning"],
                      command=dlg.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_row, text="Never", fg_color=C["danger"],
                      command=_never).pack(side="left", expand=True, padx=5)



    def run_bg(self, func):
        threading.Thread(target=func, daemon=True).start()

    def _bind_scroll(self, widget):
        """Bind mouse wheel scroll for Linux (Button-4/5), Windows/Mac (MouseWheel)."""
        SCROLL_SPEED = 10

        def _on_mousewheel(event):
            if hasattr(widget, '_parent_canvas'):
                canvas = widget._parent_canvas
                if os.name == 'nt' or sys.platform == 'darwin':
                    canvas.yview_scroll(int(-1 * (event.delta / 120)) * SCROLL_SPEED, "units")
                else:
                    if event.num == 4:
                        canvas.yview_scroll(-SCROLL_SPEED, "units")
                    elif event.num == 5:
                        canvas.yview_scroll(SCROLL_SPEED, "units")

        if sys.platform == 'linux':
            widget.bind_all("<Button-4>", _on_mousewheel)
            widget.bind_all("<Button-5>", _on_mousewheel)
        else:
            widget.bind_all("<MouseWheel>", _on_mousewheel)

    def init_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=90, corner_radius=0, fg_color=C["bg_sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="XA", font=(F_UI, 28, "bold"), text_color=C["primary"]).pack(pady=(30, 20))

        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(fill="x", pady=10)

        def _load_nav_icon(name, size=26):
            try:
                img = Image.open(f"menu_icons/{name}.png")
                return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
            except Exception:
                return None

        items = [
            ("home",     "Dashboard", self.view_dash),
            ("screen",   "Screen",    self.view_screen),
            ("apps",     "Apps",      self.view_apps),
            ("files",    "Files",     self.view_files),
            ("shell",    "Shell",     self.view_shell),
            ("logcat",   "Logcat",    self.view_logcat),
            ("connect", "Connection",  self.view_connect),
            ("fastboot", "Fastboot",  self.view_fastboot),
            ("tweaks",   "Tweaks",    self.view_tweaks),
            ("backup",   "Backup",    self.view_backup),
            ("devices",  "Devices",   self.view_devices),
            ("settings", "Settings",  self.view_settings),
        ]

        for icon_name, name, cmd in items:
            img = _load_nav_icon(icon_name)
            btn = FluentButton(
                self.nav_frame,
                image=img if img else None,
                text="" if img else icon_name[:2].upper(),
                width=50, height=50, corner_radius=10,
                font=(F_UI, 13, "bold"), command=cmd,
                fg_color="transparent", text_color=C["text_sub"],
                compound="top"
            )
            btn.pack(pady=5, padx=10)
            self.nav_buttons[name] = btn

        self.status_dot = ctk.CTkLabel(self.sidebar, text="●", font=(F_UI, 24), text_color=C["danger"])
        self.status_dot.pack(side="bottom", pady=(0, 20))
        self.status_lbl = ctk.CTkLabel(self.sidebar, text="None", font=(F_UI, 10), text_color="gray")
        self.status_lbl.pack(side="bottom", pady=(0, 5))

        # Main content
        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg_root"])
        self.main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.bind_all("<Control_L>", lambda e: setattr(self, 'ctrl_pressed', True))
        self.bind_all("<KeyRelease-Control_L>", lambda e: setattr(self, 'ctrl_pressed', False))
        self.bind_all("<Control_R>", lambda e: setattr(self, 'ctrl_pressed', True))
        self.bind_all("<KeyRelease-Control_R>", lambda e: setattr(self, 'ctrl_pressed', False))
        self.view_dash()

    def highlight(self, name):
        self.monitor_active = name == "Dashboard"
        self._current_view = name
        for k, btn in self.nav_buttons.items():
            btn.set_active(k == name)

    def clear(self):
        # Save shell state before leaving
        if self._current_view == "Shell" and hasattr(self, '_shell_history'):
            shell_content = ""
            if hasattr(self, '_shell_text'):
                try:
                    shell_content = self._shell_text.get("1.0", "end")
                except Exception:
                    pass
            self._view_state["Shell"] = {
                "history": list(self._shell_history),
                "cwd": getattr(self, '_shell_cwd', '/'),
                "device_name": getattr(self, '_shell_device_name', 'device'),
                "su": getattr(self, '_shell_su', False),
                "content": shell_content,
            }
        # Save Dashboard labels
        if self._current_view == "Dashboard":
            self._view_state["Dashboard"] = {
                "model": getattr(self, 'lbl_model', None) and self.lbl_model.cget("text") if hasattr(self, 'lbl_model') else "Model: ...",
                "android": getattr(self, 'lbl_android', None) and self.lbl_android.cget("text") if hasattr(self, 'lbl_android') else "Android: ...",
                "console": self.dash_console.text_area.get("1.0", "end") if hasattr(self, 'dash_console') else "",
            }
        # Save Screen console content
        if self._current_view == "Screen" and hasattr(self, 'screen_console'):
            try:
                self._view_state["Screen"] = {
                    "content": self.screen_console.text_area.get("1.0", "end")
                }
            except Exception:
                pass
        # Save App Manager search text and selected packages
        if self._current_view == "Apps":
            self._view_state["Apps"] = {
                "search": self.app_search.get() if hasattr(self, 'app_search') else "",
                "selected": list(self.sel_pkgs) if hasattr(self, 'sel_pkgs') else [],
                "all_apps": list(self.all_apps) if hasattr(self, 'all_apps') else [],
            }
        # Save file manager path
        if self._current_view == "Files" and hasattr(self, 'cur_path'):
            self._view_state["Files"] = {"path": self.cur_path}
        # Save Connection IP fields
        if self._current_view == "Connection":
            self._view_state["Connection"] = {
                "ip": self.ent_ip.get() if hasattr(self, 'ent_ip') else "",
                "pair_ip": self.ent_pair_ip.get() if hasattr(self, 'ent_pair_ip') else "",
            }
        # Save Fastboot console content
        if self._current_view == "Fastboot" and hasattr(self, 'fb_console'):
            try:
                self._view_state["Fastboot"] = {
                    "content": self.fb_console.text_area.get("1.0", "end")
                }
            except Exception:
                pass
        # Save Devices console content
        if self._current_view == "Devices" and hasattr(self, 'dev_console'):
            try:
                self._view_state["Devices"] = {
                    "content": self.dev_console.text_area.get("1.0", "end")
                }
            except Exception:
                pass
        # Save logcat text content
        if self._current_view == "Logcat" and hasattr(self, '_logcat_text'):
            try:
                self._logcat_text.configure(state="normal")
                self._view_state["Logcat"] = {"content": self._logcat_text.get("1.0", "end")}
                self._logcat_text.configure(state="disabled")
            except Exception:
                pass

        if self.log_proc:
            self.log_proc = False
        if hasattr(self, '_shell_alive') and self._shell_alive:
            self._shell_stop()
        self.active_radials = []
        self.file_buttons = []
        for w in self.main.winfo_children():
            w.destroy()

    def get_console(self):
        """Helper to get the current view's console if it exists"""
        for w in self.main.winfo_children():
            if isinstance(w, LogConsole):
                return w
        return None

    def adb_cmd_console(self, args, msg="Executing..."):
        """Run ADB command and stream to current console"""
        console = self.get_console()
        if not self.sel_dev:
            if console: console.log("[ERROR] No device selected")
            return

        clean = self.sel_dev.split()[0]

        if CONF.get("use_su", False) and args[0] == "shell" and len(args) > 1:
            args = ["shell", "su", "-c"] + [" ".join(args[1:])]

        if console: console.log(f"Command: {' '.join(args)}")

        def _exec():
            self.bk.run_live([ADB_PATH, "-s", clean] + args, lambda l: console.log(l) if console else None)
            if console: console.log("[DONE]")

        self.run_bg(_exec)

    def dev_loop(self):
        self._pause_dev_loop = False
        self._last_device_list = []
        self._warned_serials = set()
        while True:
            try:
                if not self._pause_dev_loop:
                    devices = self.bk.get_devices()
                    problem = getattr(self.bk, '_problem_serials', set())
                    self.bk._problem_serials = set()  # reset every cycle
                    new_problems = problem - self._warned_serials
                    if new_problems:
                        self._warned_serials.update(new_problems)
                        serials_str = ", ".join(new_problems)
                        self.after(0, lambda s=serials_str: CustomDialog(
                            self,
                            title="Unauthorized or Offline Device Detected",
                            message=f"Device(s) [{s}] are not ready.\n\nMake sure your phone screen is unlocked and tap 'Allow' on the USB debugging authorization prompt. If you already did, try unplugging and replugging the cable.",
                            icon="warning",
                            option_1="Ok"
                        ))
                    # If a serial is no longer problem, remove from warned so it can warn again if replugged
                    self._warned_serials &= problem                    
                    if devices:
                        if self.sel_dev not in devices:
                            # Try to restore last used device by serial
                            last_serial = CONF.get("last_device", "")
                            restored = next((d for d in devices if d.split()[0] == last_serial), None)
                            if restored:
                                self.sel_dev = restored
                            elif len(devices) == 1:
                                self.sel_dev = devices[0]
                            elif devices != self._last_device_list:
                                self.after(0, lambda d=devices: self.prompt_device_select(d))
                        if devices != self._last_device_list:
                            self.after(0, self._on_device_list_changed)
                        
                        self._last_device_list = devices
                        sel = self.sel_dev
                        self.after(0, lambda: self.status_dot.configure(text_color=C["success"]))
                        
                        # --- NEW LOGIC PROPERLY INDENTED ---
                        if sel:
                            name = self.bk.run([ADB_PATH, "-s", sel.split()[0], "shell", "settings", "get", "global", "device_name"]).strip()
                            self.after(0, lambda n=name: self.status_lbl.configure(text=n))
                        else:
                            self.after(0, lambda: self.status_lbl.configure(text="Ready"))
                        # -----------------------------------
                        
                    else:
                        if self._last_device_list:
                            self.after(0, self._on_device_list_changed)
                        self._last_device_list = []
                        if self.sel_dev is not None:
                            self.sel_dev = None
                            self.after(0, lambda: self.status_dot.configure(text_color=C["danger"]))
                            self.after(0, lambda: self.status_lbl.configure(text="None"))
            except:
                pass
            time.sleep(CONF.get("device_poll_interval", 2))

    def prompt_device_select(self, devices):
        if CONF.get("suppress_multi_device_warn", False):
            self.sel_dev = devices[0]
            return

        dev = devices[0]
        serial = dev.split()[0]
        mode = dev.split("(")[1].replace(")", "") if "(" in dev else ""
        if "ADB" in mode:
            model = self.bk.run([ADB_PATH, "-s", serial, "shell", "getprop", "ro.product.model"]).strip()
            friendly = f"{model or serial} [{serial}]"
        else:
            friendly = f"{serial} ({mode})"
        self.sel_dev = dev

        if hasattr(self, '_multi_dev_banner') and self._multi_dev_banner.winfo_exists():
            self._multi_dev_banner.destroy()

        banner = ctk.CTkFrame(self.main, fg_color="#4a3800", corner_radius=10,
                              border_width=1, border_color=C["warning"])
        banner.pack(fill="x", pady=(0, 10), before=self.main.winfo_children()[0])
        self._multi_dev_banner = banner

        msg = f"Multiple devices detected — Please select one in the Devices menu.\nCurrently active: {friendly}"
        ctk.CTkLabel(banner, text=msg, text_color="#FFD966",
                     font=(F_UI, 12), justify="left").pack(side="left", padx=15, pady=10)

        btn_frame = ctk.CTkFrame(banner, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)

        def dismiss():
            banner.destroy()

        def dont_warn():
            save_config("suppress_multi_device_warn", True)
            global CONF
            CONF = load_config()
            banner.destroy()

        ctk.CTkButton(btn_frame, text="Don't warn me again", width=150, height=28,
                      fg_color="#555", command=dont_warn).pack(side="left", padx=5)

    def stats_loop(self):
        while True:
            try:
                if self.monitor_active and self.sel_dev and "ADB" in self.sel_dev:
                    stats = self.bk.get_stats(self.sel_dev)
                    if hasattr(self, 'rad_batt') and hasattr(self, 'rad_ram'):
                        self.rad_batt.set(stats.get("batt", 0))
                        self.rad_ram.set(stats.get("ram", 0))
                    if hasattr(self, 'lbl_model') and hasattr(self, 'lbl_android'):
                        m, a = self.bk.get_device_info(self.sel_dev)
                        self.lbl_model.configure(text=f"Model: {m}")
                        self.lbl_android.configure(text=f"Android: {a}")
            except:
                pass
            time.sleep(CONF.get("refresh_interval", 3))

    def _on_device_list_changed(self):
        if hasattr(self, 'dev_list_frame') and self.dev_list_frame.winfo_exists():
            self._refresh_device_list()

    # ================= VIEWS =================

    def view_dash(self):
        self.clear()
        self.highlight("Dashboard")

        ctk.CTkLabel(self.main, text="Dashboard", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 10))

        # Info Row
        info_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 20))
        _dash_saved = self._view_state.get("Dashboard", {})
        self.lbl_model = ctk.CTkLabel(info_frame, text=_dash_saved.get("model", "Model: ..."), font=(F_UI, 14), text_color=C["text_sub"])
        self.lbl_model.pack(side="left", padx=10)
        self.lbl_android = ctk.CTkLabel(info_frame, text=_dash_saved.get("android", "Android: ..."), font=(F_UI, 14), text_color=C["text_sub"])
        self.lbl_android.pack(side="left", padx=10)

        # Stats row
        row = ctk.CTkFrame(self.main, fg_color="transparent")
        row.pack(fill="x")
        c1 = ctk.CTkFrame(row, fg_color=C["bg_surface"], corner_radius=15)
        c1.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.rad_ram = RadialProgress(c1, "RAM", color=C["warning"])
        self.rad_ram.pack(pady=20)
        self.active_radials.append(self.rad_ram)

        c2 = ctk.CTkFrame(row, fg_color=C["bg_surface"], corner_radius=15)
        c2.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.rad_batt = RadialProgress(c2, "Battery", color=C["success"])
        self.rad_batt.pack(pady=20)
        self.active_radials.append(self.rad_batt)

        # Power controls
        ctk.CTkLabel(self.main, text="Power Controls", font=(F_UI, 18, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(30, 10))
        pg = ctk.CTkFrame(self.main, fg_color="transparent")
        pg.pack(fill="x")
        btns = [("Reboot System", ["reboot"], C["primary"]), ("Recovery", ["reboot", "recovery"], C["warning"]),
                ("Bootloader", ["reboot", "bootloader"], C["warning"]), ("Power Off", ["reboot", "-p"], C["danger"])]

        button_text_color = "#000000" if ctk.get_appearance_mode() == "Light" else "#FFFFFF" ## Fix For Issue 1

        for label, cmd, color in btns:
            ctk.CTkButton(pg, text=label, text_color=button_text_color, fg_color=color, height=50, corner_radius=8, font=(F_UI, 14, "bold"),
                          command=lambda x=cmd: self.adb_cmd_console(x)).pack(side="left", fill="x", expand=True, padx=5)

        # Console
        ctk.CTkLabel(self.main, text="Activity Log", font=(F_UI, 14, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(20, 5))
        self.dash_console = LogConsole(self.main, height=200)
        self.dash_console.pack(fill="x", pady=(0, 20))
        _dash_console_content = self._view_state.get("Dashboard", {}).get("console", "")
        if _dash_console_content.strip():
            self.dash_console.text_area.configure(state="normal")
            self.dash_console.text_area.insert("1.0", _dash_console_content)
            self.dash_console.text_area.see("end")
            self.dash_console.text_area.configure(state="disabled")

    # --- SCREEN TOOLS ---
    def view_screen(self):
        self.clear()
        self.highlight("Screen")
        ctk.CTkLabel(self.main, text="Screen Tools", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        grid = ctk.CTkFrame(self.main, fg_color="transparent")
        grid.pack(fill="x", pady=10)

        # Scrcpy
        c1 = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=10)
        c1.pack(side="left", fill="both", expand=True, padx=5, ipady=10)
        ctk.CTkLabel(c1, text="Mirroring", font=(F_UI, 16, "bold")).pack(pady=10)
        ctk.CTkButton(c1, text="Launch Scrcpy", fg_color=C["primary"], command=self.launch_scrcpy).pack(pady=10)

        # Screenshot
        c2 = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=10)
        c2.pack(side="left", fill="both", expand=True, padx=5, ipady=10)
        ctk.CTkLabel(c2, text="Capture", font=(F_UI, 16, "bold")).pack(pady=10)
        ctk.CTkButton(c2, text="Take Screenshot", fg_color=C["success"], command=self.take_screenshot).pack(pady=10)

        # Record
        c3 = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=10)
        c3.pack(side="left", fill="both", expand=True, padx=5, ipady=10)
        ctk.CTkLabel(c3, text="Recording", font=(F_UI, 16, "bold")).pack(pady=10)
        self.rec_btn = ctk.CTkButton(c3, text="Start Record (10s)", fg_color=C["danger"], command=self.record_screen)
        self.rec_btn.pack(pady=10)

        self.screen_console = LogConsole(self.main, height=300)
        self.screen_console.pack(fill="both", expand=True, pady=20)
        _screen_saved = self._view_state.get("Screen", {})
        if _screen_saved.get("content", "").strip():
            self.screen_console.text_area.configure(state="normal")
            self.screen_console.text_area.insert("1.0", _screen_saved["content"])
            self.screen_console.text_area.see("end")
            self.screen_console.text_area.configure(state="disabled")

    def launch_scrcpy(self):
        if not self.sel_dev: return
        self.screen_console.log("Launching Scrcpy...")
        clean = self.sel_dev.split()[0]
        def _run():
            try:
                kwargs = Backend._no_window_kwargs()
                kwargs["stdin"] = subprocess.DEVNULL
                subprocess.Popen([SCRCPY_PATH, "-s", clean] + CONF["scrcpy_args"].split(), **kwargs)
                self.screen_console.log("Scrcpy will start.")
            except Exception:
                self.screen_console.log("[ERROR] Scrcpy not found in PATH.")
        self.run_bg(_run)

    def take_screenshot(self):
        if not self.sel_dev: return
        ts = int(time.time())
        remote = f"/sdcard/screen_{ts}.png"
        local = f"screen_{ts}.png"
        clean = self.sel_dev.split()[0]

        def _capture():
            self.screen_console.log("Capturing screenshot...")
            result = self.bk.run([ADB_PATH, "-s", clean, "shell", "screencap", "-p", remote])

            if "[ERROR]" in result:
                self.screen_console.log("[ERROR] Screenshot failed")
                return

            time.sleep(0.5)
            self.screen_console.log(f"Downloading to {local}...")
            self.bk.run_live(
                [ADB_PATH, "-s", clean, "pull", remote, local],
                lambda l: self.screen_console.log(l)
            )

            self.bk.run([ADB_PATH, "-s", clean, "shell", "rm", remote])
            self.screen_console.log(f"✓ Saved to {local}")

        self.run_bg(_capture)

    def record_screen(self):
        if not self.sel_dev: return
        ts = int(time.time())
        remote = f"/sdcard/rec_{ts}.mp4"
        local = f"rec_{ts}.mp4"
        clean = self.sel_dev.split()[0]

        def _record():
            self.screen_console.log("Recording for 10 seconds...")

            result = self.bk.run(
                [ADB_PATH, "-s", clean, "shell", "screenrecord", "--time-limit", "10", remote],
                timeout=15
            )

            if "[ERROR]" in result:
                self.screen_console.log("[ERROR] Recording failed")
                return

            self.screen_console.log(f"Recording complete. Downloading to {local}...")
            self.bk.run_live(
                [ADB_PATH, "-s", clean, "pull", remote, local],
                lambda l: self.screen_console.log(l)
            )

            self.bk.run([ADB_PATH, "-s", clean, "shell", "rm", remote])
            self.screen_console.log(f"✓ Saved to {local}")

        self.run_bg(_record)


    # --- APPS ---
    def view_apps(self):
        self.clear()
        self.highlight("Apps")
        self.sel_pkgs = []
        ctk.CTkLabel(self.main, text="App Manager", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(
            anchor="w", pady=(10, 20))

        bar = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        bar.pack(fill="x", pady=(0, 5), ipady=5)
        self.app_search = ctk.CTkEntry(bar, placeholder_text="Search apps...", border_width=0, fg_color=C["input_bg"],
                                       height=40, text_color=C["text_main"])
        self.app_search.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.app_search.bind("<KeyRelease>",
                             lambda e: self.filter_apps() if e.keysym not in ("Control_L", "Control_R") else None)
        ctk.CTkButton(bar, text="Refresh", fg_color=C["primary"], command=self.load_apps).pack(side="left", padx=5)
        ctk.CTkButton(bar, text="Install APK", fg_color=C["success"], command=self.install_apk).pack(side="left",
                                                                                                     padx=10)

        # Sort bar
        sort_bar = ctk.CTkFrame(self.main, fg_color="transparent")
        sort_bar.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(sort_bar, text="Sort:", font=(F_UI, 11), text_color=C["text_sub"]).pack(side="left",
                                                                                                   padx=(5, 8))
        self._app_sort = ctk.StringVar(value=CONF.get("app_sort", "a_z"))
        for label, val in [("A→Z", "a_z"), ("Z→A", "z_a")]:
            ctk.CTkRadioButton(sort_bar, text=label, variable=self._app_sort, value=val,
                               font=(F_UI, 11), text_color=C["text_sub"],
                               command=self._on_app_sort_change).pack(side="left", padx=6)

        split = ctk.CTkFrame(self.main, fg_color="transparent")
        split.pack(fill="both", expand=True)
        self.app_list = ctk.CTkScrollableFrame(split, fg_color=C["bg_surface"], corner_radius=15)
        self.app_list.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._bind_scroll(self.app_list)

        act = ctk.CTkFrame(split, width=250, fg_color=C["bg_surface"], corner_radius=15)
        act.pack(side="right", fill="y")
        ctk.CTkLabel(act, text="Actions", font=(F_UI, 14, "bold"), text_color=C["text_main"]).pack(pady=(20, 5))
        self.lbl_pkg = ctk.CTkLabel(act, text="None selected", text_color="gray", wraplength=200, font=(F_UI, 11))
        self.lbl_pkg.pack(pady=(0, 15))

        ctk.CTkButton(act, text="Uninstall Selected", fg_color=C["danger"], command=self.do_uninst).pack(fill="x",
                                                                                                         padx=20,
                                                                                                         pady=5)
        ctk.CTkButton(act, text="Force Uninstall", fg_color="#8B0000",
                      command=self.do_force_uninst).pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(act, text="Force Stop", fg_color=C["warning"], command=self.do_force).pack(fill="x", padx=20,
                                                                                                 pady=5)
        ctk.CTkButton(act, text="Clear Data", fg_color="#555", command=self.do_clear).pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(act, text="Extract APK", fg_color=C["primary"], command=self.do_extract).pack(fill="x", padx=20,
                                                                                                    pady=5)
        ctk.CTkButton(act, text="Deselect All", fg_color=C["input_bg"], text_color=C["text_main"],
                      command=self.deselect_all_apps).pack(fill="x", padx=20, pady=(15, 5))

        self.app_console = LogConsole(self.main, height=150)
        self.app_console.pack(fill="x", pady=(10, 0))

        # Restore saved state or load fresh
        _apps_saved = self._view_state.get("Apps", {})
        self.all_apps = list(_apps_saved.get("all_apps", []))
        self.sel_pkgs = list(_apps_saved.get("selected", []))
        _saved_search = _apps_saved.get("search", "")
        if _saved_search:
            self.app_search.insert(0, _saved_search)
        if self.all_apps:
            # Restore from saved state - no network call needed
            self.app_console.log(f"Restored {len(self.all_apps)} apps from last session.")
            self.filter_apps()
        else:
            self.load_apps()

    def load_apps(self):
        if not self.sel_dev: return
        cln = self.sel_dev.split()[0]
        for w in self.app_list.winfo_children(): w.destroy()
        self._app_buttons = {}
        self.app_console.log("Loading packages...")
        def _t():
            raw = self.bk.run([ADB_PATH, "-s", cln, "shell", "pm", "list", "packages", "-3"], timeout=15)
            if not raw or not raw.strip():
                self.app_console.log("[WARNING] No packages found")
                self.all_apps = []
            else:
                self.all_apps = sorted(
                    [x.replace("package:", "").strip() for x in raw.split("\n") if x.strip()],
                    key=str.lower
                )
            self.after(0, lambda: self.filter_apps())
        self.run_bg(_t)
        
    def filter_apps(self):
        search = self.app_search.get().lower()
        filtered = [p for p in self.all_apps if search in p.lower()]
        sort = self._app_sort.get() if hasattr(self, '_app_sort') else CONF.get("app_sort", "a_z")
        if sort == "z_a":
            filtered = list(reversed(filtered))
        self.after(0, lambda: self._populate_app_list(filtered, len(self.all_apps)))

    def _on_app_sort_change(self):
        save_config("app_sort", self._app_sort.get())
        global CONF
        CONF = load_config()
        self.filter_apps()

    def _populate_app_list(self, pkgs, total):
        for w in self.app_list.winfo_children():
            w.destroy()
        self._app_buttons = {}
        CHUNK = 30  # render 30 buttons per frame to keep UI responsive

        def _render_chunk(idx):
            chunk = pkgs[idx:idx + CHUNK]
            for p in chunk:
                btn = ctk.CTkButton(
                    self.app_list,
                    text=p,
                    anchor="w",
                    fg_color="transparent",
                    hover_color=C["bg_hover"],
                    text_color=C["text_main"],
                    command=lambda x=p: self.toggle_app_select(x)
                )
                btn.pack(fill="x")
                self._app_buttons[p] = btn
            if idx + CHUNK < len(pkgs):
                self.after(5, lambda: _render_chunk(idx + CHUNK))
            else:
                self.app_console.log(f"Loaded {total} apps (showing {len(pkgs)}).")

        if pkgs:
            _render_chunk(0)
        else:
            self.app_console.log(f"Loaded {total} apps (showing 0).")
        # Re-apply selection highlights for restored state
        def _restore_selection():
            for pkg in list(self.sel_pkgs):
                if pkg in self._app_buttons:
                    self._app_buttons[pkg].configure(fg_color=C["bg_hover"])
            count = len(self.sel_pkgs)
            if count == 1:
                self.lbl_pkg.configure(text=self.sel_pkgs[0])
            elif count > 1:
                self.lbl_pkg.configure(text=f"{count} packages selected")
        self.after(200, _restore_selection)

    def toggle_app_select(self, p):
        if p in self.sel_pkgs:
            # always allow deselect with normal click
            self.sel_pkgs.remove(p)
            self._app_buttons[p].configure(fg_color="transparent")
        else:
            if not self.ctrl_pressed and len(self.sel_pkgs) > 0:
                # no ctrl = clear previous selection first
                for prev in self.sel_pkgs:
                    if prev in self._app_buttons:
                        self._app_buttons[prev].configure(fg_color="transparent")
                self.sel_pkgs = []
            self.sel_pkgs.append(p)
            self._app_buttons[p].configure(fg_color=C["bg_hover"])

        count = len(self.sel_pkgs)
        if count == 0:
            self.lbl_pkg.configure(text="None selected")
        elif count == 1:
            self.lbl_pkg.configure(text=self.sel_pkgs[0])
        else:
            self.lbl_pkg.configure(text=f"{count} packages selected")

    def deselect_all_apps(self):
        for p in self.sel_pkgs:
            if p in self._app_buttons:
                self._app_buttons[p].configure(fg_color="transparent")
        self.sel_pkgs = []
        self.lbl_pkg.configure(text="None selected")

    def install_apk(self):
        files = filedialog.askopenfilenames(filetypes=[("APK", "*.apk")])  # Note: askopenfileNAMES (plural)
        if files:
            self.app_console.log(f"Installing {len(files)} APK(s)...")
            for i, f in enumerate(files, 1):
                self.app_console.log(f"[{i}/{len(files)}] Installing {os.path.basename(f)}...")
                self.adb_cmd_console(["install", f], f"Installing {os.path.basename(f)}")
            self.app_console.log("All installations queued!")

    def do_uninst(self):
        if not self.sel_pkgs:
            self.app_console.log("[ERROR] No packages selected.")
            return
        pkgs = self.sel_pkgs.copy()

        def _run():
            for pkg in pkgs:
                self.app_console.log(f"Uninstalling {pkg}...")
                self.bk.run_live([ADB_PATH, "-s", self.sel_dev.split()[0], "uninstall", pkg],
                                 lambda l: self.app_console.log(l))
            self.after(500, self.load_apps)
            self.after(500, self.deselect_all_apps)

        self.run_bg(_run)

    def do_force_uninst(self):
        if not self.sel_pkgs:
            self.app_console.log("[ERROR] No packages selected.")
            return
        pkgs = self.sel_pkgs.copy()
        msg = CustomDialog(
            self,
            title="Force Uninstall",
            message=f"Force uninstall {len(pkgs)} package(s)?\nThis uses -k --user 0 and works on system apps.",
            icon="warning",
            option_1="Yes",
            option_2="Cancel"
        )
        if msg.get() != "Yes":
            return

        def _run():
            for pkg in pkgs:
                self.app_console.log(f"Force uninstalling {pkg}...")
                self.bk.run_live(
                    [ADB_PATH, "-s", self.sel_dev.split()[0], "shell", "pm", "uninstall", "-k", "--user", "0", pkg],
                    lambda l: self.app_console.log(l))
            self.after(500, self.load_apps)
            self.after(500, self.deselect_all_apps)

        self.run_bg(_run)

    def do_force(self):
        if not self.sel_pkgs:
            self.app_console.log("[ERROR] No packages selected.")
            return
        for pkg in self.sel_pkgs:
            self.adb_cmd_console(["shell", "am", "force-stop", pkg])

    def do_clear(self):
        if not self.sel_pkgs:
            self.app_console.log("[ERROR] No packages selected.")
            return
        for pkg in self.sel_pkgs:
            self.adb_cmd_console(["shell", "pm", "clear", pkg])

    def do_extract(self):
        pkgs = self.sel_pkgs.copy()
        cln = self.sel_dev.split()[0]
        d = os.path.join(os.path.dirname(os.path.dirname(__file__)), "extracted")
        os.makedirs(d, exist_ok=True)
        def _t():
            for pkg in pkgs:
                path_out = self.bk.run([ADB_PATH, "-s", cln, "shell", "pm", "path", pkg])
                apk_paths = [line.replace("package:", "").strip() for line in path_out.split("\n") if
                "package:" in line]
                if not apk_paths:
                    self.app_console.log(f"[ERROR] Could not find APK path for {pkg}")
                    continue
                pkg_dir = os.path.join(d, pkg)
                os.makedirs(pkg_dir, exist_ok=True)
                for apk_path in apk_paths:
                    filename = os.path.basename(apk_path)
                    local_path = os.path.join(pkg_dir, filename)
                    self.app_console.log(f"Pulling {filename}...")
                    self.bk.run_live(
                        [ADB_PATH, "-s", cln, "pull", apk_path, local_path],
                        lambda l: self.app_console.log(l)
                    )
                    self.app_console.log(f"Extracted {pkg} to {pkg_dir}")
                self.app_console.log("Extraction complete.")
        self.run_bg(_t)

    # --- FILES ---
    def view_files(self):
        self.clear()
        self.highlight("Files")
        # Restore last path if returning to this view
        if "Files" in self._view_state:
            self.cur_path = self._view_state["Files"].get("path", self.cur_path)
        ctk.CTkLabel(self.main, text="File Explorer", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        nav = ctk.CTkFrame(self.main, fg_color=C["bg_surface"])
        nav.pack(fill="x", pady=10)
        ctk.CTkButton(nav, text="⬆", width=40, command=self.fm_up, fg_color="#333").pack(side="left", padx=10, pady=10)
        self.fm_ent = ctk.CTkEntry(nav, border_width=0, fg_color=C["input_bg"], height=35, text_color=C["text_main"])
        self.fm_ent.pack(side="left", fill="x", expand=True)
        self.fm_ent.bind("<Return>", lambda e: self.fm_load())
        ctk.CTkButton(nav, text="Go", width=60, command=self.fm_load, fg_color=C["primary"]).pack(side="left", padx=10)

        bar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        ops = [("New Folder", self.fm_mkdir), ("Delete", self.fm_del), ("Rename", self.fm_ren), ("Upload", self.fm_upload), ("Download", self.fm_download_single)]
        for label, cmd in ops:
            ctk.CTkButton(bar, text=label, width=80, fg_color=C["input_bg"], hover_color=C["bg_hover"], text_color=C["text_main"], command=cmd).pack(side="left", padx=5)

        # Sort bar
        fsort_bar = ctk.CTkFrame(self.main, fg_color="transparent")
        fsort_bar.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(fsort_bar, text="Sort:", font=(F_UI, 11), text_color=C["text_sub"]).pack(side="left", padx=(5, 8))
        self._file_sort = ctk.StringVar(value=CONF.get("file_sort", "a_z"))
        for label, val in [("A→Z", "a_z"), ("Z→A", "z_a"), ("Folders first", "folders_first"), ("Files first", "files_first")]:
            ctk.CTkRadioButton(fsort_bar, text=label, variable=self._file_sort, value=val, font=(F_UI, 11), text_color=C["text_sub"], command=self._on_file_sort_change).pack(side="left", padx=6)

        self.fm_list = ctk.CTkScrollableFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        self.fm_list.pack(fill="both", expand=True)
        self._bind_scroll(self.fm_list)
        self.fm_sel = None
        self.fm_selected = []
        self.ctrl_pressed = False
        self.fm_ent.insert(0, self.cur_path)

        self.fm_console = LogConsole(self.main, height=120)
        self.fm_console.pack(fill="x", pady=(10, 0))
        self.fm_load()


    def fm_load(self):
        if not self.sel_dev: return
        cln = self.sel_dev.split()[0]
        path = self.fm_ent.get()
        self.cur_path = path

        # Increment generation so any in-flight render knows it's stale
        self._fm_gen = getattr(self, '_fm_gen', 0) + 1
        my_gen = self._fm_gen

        for w in self.fm_list.winfo_children():
            w.destroy()
        self.file_buttons = []

        self.fm_console.log(f"Listing {path}...")

        def _t():
            out = self.bk.run([ADB_PATH, "-s", cln, "shell", f"ls -p '{path}'"], timeout=10)
            if "[ERROR]" in out or "No such file" in out or "Permission denied" in out:
                self.after(0, lambda: self.fm_console.log("Error reading directory."))
                return
            items = [x.strip() for x in out.split("\n") if x.strip()]
            if not items:
                self.after(0, lambda: self.fm_console.log("Directory is empty."))
                return
            folder_count = sum(1 for i in items if i.endswith("/"))
            file_count = len(items) - folder_count
            self.after(0, lambda i=items, g=my_gen: self._populate_file_list(i, g))
            self.after(0, lambda: self.fm_console.log(f"Listed: {file_count} file(s), {folder_count} folder(s)"))

        self.run_bg(_t)


    def _populate_file_list(self, items, gen):
        # Bail out if a newer fm_load has already started
        if gen != getattr(self, '_fm_gen', 0):
            return

        sort = self._file_sort.get() if hasattr(self, '_file_sort') else CONF.get("file_sort", "a_z")
        dirs = sorted([i for i in items if i.endswith("/")])
        files = sorted([i for i in items if not i.endswith("/")])

        if sort == "z_a":
            dirs = list(reversed(dirs))
            files = list(reversed(files))
            sorted_items = dirs + files
        elif sort == "files_first":
            sorted_items = files + dirs
        else:  # a_z and folders_first both put dirs first
            sorted_items = dirs + files

        CHUNK = 40

        def _render_chunk(idx, g):
            if g != getattr(self, '_fm_gen', 0):
                return

            if not hasattr(self, '_fm_icons'):
                def _load_icon(name, size=18):
                    try:
                        img = Image.open(f"menu_icons/{name}.png")
                        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
                    except Exception:
                        return None

                self._fm_icons = {
                    'dir':        _load_icon("directory"),
                    # images
                    'png':        _load_icon("img"),
                    'jpg':        _load_icon("img"),
                    'jpeg':       _load_icon("img"),
                    'gif':        _load_icon("img"),
                    'webp':       _load_icon("img"),
                    'bmp':        _load_icon("img"),
                    'ico':        _load_icon("img"),
                    'svg':        _load_icon("img"),
                    'heic':       _load_icon("img"),
                    # video
                    'mp4':        _load_icon("video"),
                    'mkv':        _load_icon("video"),
                    'avi':        _load_icon("video"),
                    'mov':        _load_icon("video"),
                    'wmv':        _load_icon("video"),
                    'flv':        _load_icon("video"),
                    'webm':       _load_icon("video"),
                    '3gp':        _load_icon("video"),
                    'm4v':        _load_icon("video"),
                    # audio
                    'mp3':        _load_icon("audio"),
                    'wav':        _load_icon("audio"),
                    'aac':        _load_icon("audio"),
                    'flac':       _load_icon("audio"),
                    'ogg':        _load_icon("audio"),
                    'm4a':        _load_icon("audio"),
                    'opus':       _load_icon("audio"),
                    # compressed
                    'zip':        _load_icon("compressed"),
                    'rar':        _load_icon("compressed"),
                    '7z':         _load_icon("compressed"),
                    'tar':        _load_icon("compressed"),
                    'gz':         _load_icon("compressed"),
                    'bz2':        _load_icon("compressed"),
                    'xz':         _load_icon("compressed"),
                    'zst':        _load_icon("compressed"),
                    # text
                    'txt':        _load_icon("text"),
                    'log':        _load_icon("text"),
                    'csv':        _load_icon("text"),
                    'json':       _load_icon("text"),
                    'xml':        _load_icon("text"),
                    'yaml':       _load_icon("text"),
                    'yml':        _load_icon("text"),
                    'ini':        _load_icon("text"),
                    'cfg':        _load_icon("text"),
                    'conf':       _load_icon("text"),
                    'sh':         _load_icon("text"),
                    'py':         _load_icon("text"),
                    'js':         _load_icon("text"),
                    'html':       _load_icon("text"),
                    'css':        _load_icon("text"),
                    'md':         _load_icon("text"),
                    # documents
                    'pdf':        _load_icon("document"),
                    'doc':        _load_icon("document"),
                    'docx':       _load_icon("document"),
                    'xls':        _load_icon("document"),
                    'xlsx':       _load_icon("document"),
                    'ppt':        _load_icon("document"),
                    'pptx':       _load_icon("document"),
                    'odt':        _load_icon("document"),
                    'ods':        _load_icon("document"),
                    # apk
                    'apk':        _load_icon("apk"),
                    # fallbacks
                    'none':       _load_icon("none"),
                    'file':       _load_icon("files"),
                }

            chunk = sorted_items[idx:idx + CHUNK]
            for item in chunk:
                is_dir = item.endswith("/")
                col = C["primary"] if is_dir else C["text_main"]
                if is_dir:
                    icon_image = self._fm_icons['dir']
                else:
                    ext = item.rsplit(".", 1)[-1].lower() if "." in item else ""
                    if not ext:
                        icon_image = self._fm_icons['none']
                    else:
                        icon_image = self._fm_icons.get(ext) or self._fm_icons['file']

                btn = ctk.CTkButton(
                    self.fm_list,
                    text=f"  {item}",
                    image=icon_image,
                    compound="left",
                    anchor="w",
                    fg_color="transparent",
                    hover_color=C["bg_hover"],
                    text_color=col,
                    command=lambda n=item: self.fm_click_item(n)
                )
                btn.pack(fill="x")
                if is_dir:
                    btn.bind("<Double-Button-1>", lambda e, x=item: self.fm_ent_dir(x))
                btn.bind(RIGHT_CLICK, lambda e, name=item: self.show_file_context_menu(e, name))
                self.file_buttons.append((btn, item))

            # Force the scrollable frame's canvas to update its scroll region
            self.fm_list.update_idletasks()
            if hasattr(self.fm_list, '_parent_canvas'):
                self.fm_list._parent_canvas.configure(
                    scrollregion=self.fm_list._parent_canvas.bbox("all")
                )

            if idx + CHUNK < len(sorted_items):
                self.after(5, lambda i=idx + CHUNK, g=g: _render_chunk(i, g))

        if sorted_items:
            _render_chunk(0, gen)


    def _on_file_sort_change(self):
        save_config("file_sort", self._file_sort.get())
        global CONF
        CONF = load_config()
        self.fm_load()


    # ==================== FILE SELECTION & NAVIGATION ====================

    def fm_click_item(self, name):
        if self.ctrl_pressed:
            # Ctrl+Click = Toggle selection
            if name in self.fm_selected:
                self.fm_selected.remove(name)
            else:
                self.fm_selected.append(name)
        else:
            # Normal click = Single selection
            self.fm_selected = [name]

        self.fm_sel = name

        # Update highlights
        for btn, item_name in self.file_buttons:
            if item_name in self.fm_selected:
                btn.configure(fg_color=C["bg_hover"])
            else:
                btn.configure(fg_color="transparent")

        if len(self.fm_selected) > 0:
            self.fm_console.log(f"{len(self.fm_selected)} item(s) selected")


    def show_file_context_menu(self, event, name):
        import tkinter as tk
        
        menu = tk.Menu(self, tearoff=0)

        if len(self.fm_selected) > 1:
            # Multi-select menu
            menu.add_command(label=f"Delete {len(self.fm_selected)} items", command=self.fm_del_multiple)
            menu.add_command(label=f"Download (Receive){len(self.fm_selected)} items", command=self.fm_download_multiple)
        else:
            # Single item menu - works for BOTH files AND folders now
            menu.add_command(label="Download (Receive)", command=lambda: self.fm_download_single(name))

            if name.endswith("/"):
                menu.add_separator()
                menu.add_command(label="Upload (Send)", command=lambda: self.fm_upload_to(name))

            menu.add_separator()
            menu.add_command(label="Delete", command=lambda: self.fm_del_single(name))

        menu.post(event.x_root, event.y_root)


    def fm_ent_dir(self, x):
        self.cur_path = (self.cur_path.rstrip("/") + "/" + x).replace("\\", "/")
        self.fm_ent.delete(0, "end")
        self.fm_ent.insert(0, self.cur_path)
        self.fm_load()


    def fm_up(self):
        parts = self.cur_path.rstrip("/").split("/")
        if len(parts) > 1:
            self.cur_path = "/".join(parts[:-1]) + "/"
        self.fm_ent.delete(0, "end")
        self.fm_ent.insert(0, self.cur_path)
        self.fm_load()


    # ==================== FOLDER OPERATIONS ====================

    def fm_mkdir(self):
        dlg = ctk.CTkInputDialog(text="Folder name:", title="New Folder")
        name = dlg.get_input()
        if name:
            # Validate folder name (no spaces or special chars)
            if " " in name or any(c in name for c in '<>:"/\\|?*'):
                self.fm_console.log("Invalid folder name. Use alphanumeric and underscore only.")
                return
            
            cmd = ["shell", "mkdir", "-p", f'"{self.cur_path.rstrip("/")}/{name}"']
            out = self.adb_cmd_console(cmd)
            
            if "[ERROR]" in out or "No such file" in out:
                self.fm_console.log(f"Failed to create folder '{name}'")
                return
            
            self.after(500, self.fm_load)


    def fm_del(self):
        if not self.fm_sel: 
            self.fm_console.log("No item selected.")
            return
        
        msg = CustomDialog(self, title="Confirm", message=f"Delete {self.fm_sel}?", icon="warning", option_1="Yes", option_2="Cancel")
        if msg.get() == "Yes":
            cmd = ["shell", "rm", "-rf", f'"{self.cur_path.rstrip("/")}/{self.fm_sel}"']
            out = self.adb_cmd_console(cmd)
            
            if "[ERROR]" in out or "No such file" in out:
                self.fm_console.log(f"Failed to delete '{self.fm_sel}'")
                return
            
            self.after(500, self.fm_load)


    def fm_del_multiple(self):
        if not self.fm_selected:
            self.fm_console.log("Nothing selected.")
            return
        
        msg = CustomDialog(self, title="Confirm", message=f"Delete {len(self.fm_selected)} items?", icon="warning", option_1="Yes", option_2="Cancel")
        if msg.get() == "Yes":
            if not self.sel_dev: 
                self.fm_console.log("No device connected!")
                return
                
            cln = self.sel_dev.split()[0]
            
            def _del():
                for name in self.fm_selected:
                    path = f"{self.cur_path.rstrip('/')}/{name.rstrip('/')}"
                    cmd = [ADB_PATH, "-s", cln, "shell", "rm", "-rf", f'"{path}"']
                    out = self.bk.run(cmd)
                    
                    if "[ERROR]" in out:
                        self.after(0, lambda n=name: self.fm_console.log(f"✗ Failed to delete {n}"))
                
                self.fm_selected = []
                self.after(500, self.fm_load)
            
            self.run_bg(_del)


    def fm_ren(self):
        if not self.fm_sel: 
            self.fm_console.log("No item selected.")
            return
        
        dlg = ctk.CTkInputDialog(text="New name:", title="Rename")
        new_name = dlg.get_input()
        
        if not new_name or " " in new_name:
            self.fm_console.log("Invalid folder name. Use alphanumeric and underscore only.")
            return
            
        old = f'"{self.cur_path.rstrip("/")}/{self.fm_sel}"'
        new = f'"{self.cur_path.rstrip("/")}/{new_name}"'
        
        cmd = ["shell", "mv", old, new]
        out = self.adb_cmd_console(cmd)
        
        if "[ERROR]" in out or "No such file" in out:
            self.fm_console.log(f"Failed to rename '{self.fm_sel}'")
            return
        
        self.after(500, self.fm_load)


    def fm_upload(self):
        """Upload multiple local files to device with real progress"""
        if not self.sel_dev:
            CustomDialog(self, title="Error", message="No device connected!", icon="cancel", option_1="Ok")
            return
        cln = self.sel_dev.split()[0]

        files = self._select_files()
        files = [f for f in files if f] if files else []
        
        if not files:
            return
        dest_path = self.cur_path.rstrip("/") + "/"
        total_files = len(files)
        pframe, bar, lbl = self._show_progress(f"Uploading 0/{total_files}...")
        def _upload():
            done = 0
            for i, f in enumerate(files):
                fname = os.path.basename(f)
                fsize = os.path.getsize(f) if os.path.exists(f) else 0
                
                self.after(0, lambda n=fname, s=fsize, idx=i:
                    self._update_progress(bar, lbl, idx, total_files,
                        f"Uploading {n} ({idx+1}/{total_files})... {self._fmt(s)}"))
                
                self.after(0, lambda n=fname, s=fsize:
                    self.fm_console.log(f"Uploading {n}... ({self._fmt(s)})"))
                failed = False
                last_line = ""
                
                def _cb(line, n=fname):
                    nonlocal failed, last_line
                    last_line = line
                    if "[ERROR]" in line or "error:" in line.lower():
                        failed = True
                    cur, tot = self._parse_adb_line(line)
                    if cur is not None and tot not in (None, 100):
                        use_tot = fsize if fsize > 0 else tot
                        self.after(0, lambda c=cur, ut=use_tot, n=n:
                            self._update_progress(bar, lbl, c, ut,
                                f"Uploading {n}... {self._fmt(c)} / {self._fmt(ut)}"))
                self.bk.run_live([ADB_PATH, "-s", cln, "push", f, dest_path], _cb)
                if failed:
                    self.after(0, lambda n=fname, l=last_line:
                        self.fm_console.log(f"✗ Failed: {n} — {l}"))
                else:
                    done += 1
                    self.after(0, lambda n=fname: self.fm_console.log(f"✓ Uploaded {n}"))
            msg = f"✓ Done: {done}/{total_files} file(s) uploaded."
            self.after(0, lambda: self._update_progress(bar, lbl, 1, 1, msg))
            self.after(0, lambda: self.fm_console.log(msg))
            self.after(500, self.fm_load)
            self.after(3000, pframe.destroy)
        self.run_bg(_upload)
    def fm_upload_to(self, dest_folder=None):
        """Upload a local folder to device"""
        if not self.sel_dev:
            CustomDialog(self, title="Error", message="No device connected!", icon="cancel", option_1="Ok")
            return
        cln = self.sel_dev.split()[0]

        # ← DYNAMIC FOLDER DIALOG SELECTION BASED ON PLATFORM
        src_folder = self._select_folder()
        
        if not src_folder:
            return
        if dest_folder:
            dest_path = f"{self.cur_path.rstrip('/')}/{dest_folder.rstrip('/')}/{os.path.basename(src_folder)}"
        else:
            dest_path = f"{self.cur_path.rstrip('/')}/{os.path.basename(src_folder)}"
        total_files = sum(len(fs) for _, _, fs in os.walk(src_folder))
        pframe, bar, lbl = self._show_progress(f"Uploading folder '{os.path.basename(src_folder)}'...")
        def _upload():
            self.after(0, lambda: self.fm_console.log(
                f"Uploading folder '{os.path.basename(src_folder)}' ({total_files} files)..."))
            failed = False
            
            def _cb(line):
                nonlocal failed
                if "[ERROR]" in line or "error:" in line.lower():
                    failed = True
                cur, tot = self._parse_adb_line(line)
                if cur is not None and tot == 100:
                    self.after(0, lambda c=cur:
                        self._update_progress(bar, lbl, c, 100, f"Uploading... {c}%"))
            self.bk.run_live([ADB_PATH, "-s", cln, "push", src_folder, dest_path], _cb)
            if failed:
                self.after(0, lambda: self.fm_console.log(
                    f"✗ Failed to upload folder '{os.path.basename(src_folder)}'"))
                self.after(0, lambda: self._update_progress(bar, lbl, 0, 1, "✗ Upload failed"))
            else:
                msg = f"✓ Uploaded {total_files} file(s) successfully."
                self.after(0, lambda: self._update_progress(bar, lbl, 1, 1, msg))
                self.after(0, lambda: self.fm_console.log(msg))
                self.after(3000, pframe.destroy)
            self.after(500, self.fm_load)
        self.run_bg(_upload)
    # ==================== HELPER FUNCTIONS ====================
    def _select_save_dir(self, title="Save to"):
        """Select save directory using crossfiledialog on Linux, tkinter elsewhere."""
        if sys.platform != 'nt':
            try:
                import crossfiledialog
                d = crossfiledialog.choose_folder(title=title)
                if d and os.path.isdir(d):
                    return d
            except Exception as e:
                print(f"crossfiledialog failed ({e}), falling back to tkinter")
        from tkinter import filedialog
        return filedialog.askdirectory(title=title) or None

    def _select_files(self):
        """Select files using platform-appropriate dialog"""
        
        # Try crossfiledialog first on non-Windows systems
        if sys.platform != 'nt':  # Not Windows - could be Linux/Mac
            try:
                import crossfiledialog
                
                filter_dict = {
                    "All Files": ["*.*"],
                }
                files = crossfiledialog.open_multiple(
                    title="Select Files to Upload",
                    start_dir=self.cur_path,
                    filter=filter_dict
                )
                
                # ← FIXED: Check for None AND empty list from cancel
                if files is not None and len(files) > 0:
                    return files
                
            except Exception as e:
                print(f"crossfiledialog failed ({e}), falling back to tkinter")
        
        # ← FALLBACK TO ORIGINAL TKTINER (WORKS ON WINDOWS & LINUX!)
        from tkinter import filedialog
        
        try:
            files = filedialog.askopenfilenames(
                parent=self.master,
                title="Select Files to Upload",
                initialdir=self.cur_path
            )
            
            # ← FIXED: Convert tuple to list and check properly
            if not files or len(files) == 0:
                return []
                
            return list(files)
        except Exception as e:
            CustomDialog(self, title="Error", message=f"File dialog failed: {e}", icon="cancel", option_1="Ok")
            return []
            
    def _select_folder(self):
        """Select folder using platform-appropriate dialog"""
        
        # Try crossfiledialog first on non-Windows systems
        if sys.platform != 'nt':  # Not Windows - could be Linux/Mac
            try:
                import crossfiledialog
                src_folder = crossfiledialog.choose_folder(
                    title="Select Folder to Upload",
                    start_dir=self.cur_path
                )
                
                if src_folder and os.path.isdir(src_folder):
                    return src_folder
                    
            except Exception as e:
                print(f"crossfiledialog failed ({e}), falling back to tkinter")
        
        # ← FALLBACK TO ORIGINAL TKTINER (WORKS ON WINDOWS & LINUX!)
        from tkinter import filedialog
        
        try:
            src_folder = filedialog.askdirectory(
                parent=self.master,
                title="Select Folder to Upload",
                initialdir=self.cur_path
            )
            
            if not src_folder:
                return None
                
            return src_folder
        except Exception as e:
            CustomDialog(self, title="Error", message=f"Folder dialog failed: {e}", icon="cancel", option_1="Ok")
            return None

    # ==================== PROGRESS BAR ====================

    def _show_progress(self, label="Transferring...", anchor_widget=None):
        """Create and pack a progress bar + label above the given console. Returns (frame, bar, lbl)."""
        if anchor_widget is None:
            # Auto-detect: prefer fm_console, then fb_console
            anchor_widget = getattr(self, 'fm_console', None) or getattr(self, 'fb_console', None)
        frame = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        if anchor_widget and anchor_widget.winfo_exists():
            frame.pack(fill="x", pady=(5, 0), before=anchor_widget)
        else:
            frame.pack(fill="x", pady=(5, 0))
        lbl = ctk.CTkLabel(frame, text=label, font=(F_UI, 12), text_color=C["text_main"])
        lbl.pack(anchor="w", padx=12, pady=(8, 2))
        bar = ctk.CTkProgressBar(frame, height=14, corner_radius=7,
                                  fg_color=C["input_bg"], progress_color=C["primary"])
        bar.set(0)
        bar.pack(fill="x", padx=12, pady=(0, 8))
        return frame, bar, lbl

    def _update_progress(self, bar, lbl, current, total, label=""):
        if total > 0:
            bar.set(min(current / total, 1.0))
        if label:
            lbl.configure(text=label)

    def _parse_adb_line(self, line):
        """
        Parse ADB push/pull progress lines.
        ADB prints lines like:
          /sdcard/file.rar: 1 file pulled, 0 skipped. 18.3 MB/s (524288000 bytes in 27.338s)
          [ 23%] /sdcard/file.rar
        Returns (current_bytes, total_bytes) or (None, None) if not a progress line.
        """
        # Final summary line: "(524288000 bytes in 27.338s)"
        m = re.search(r'\((\d+)\s+bytes\s+in\s+[\d.]+s\)', line)
        if m:
            b = int(m.group(1))
            return b, b  # 100% complete

        # Percentage line: "[ 23%] ..."  — ADB only prints this for multi-file pulls
        m = re.search(r'\[\s*(\d+)%\]', line)
        if m:
            pct = int(m.group(1))
            return pct, 100  # treat as percentage units

        return None, None

    # ==================== DOWNLOAD (PULL) OPERATIONS ====================

    def _get_android_file_size(self, cln, path):
        """Get Android device file size using stat command"""
        try:
            out = self.bk.run([ADB_PATH, "-s", cln, "shell", f"stat -c %s '{path}'"])
            return int(out.strip())
        except Exception:
            return 0

    def _fmt(self, b):
        for u in ['B','KB','MB','GB']:
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024
        return f"{b:.1f} TB"

    def fm_download_single(self, name=None):
        """Download single file from device with real progress bar"""
        if not self.sel_dev:
            CustomDialog(self, title="Error", message="No device connected!", icon="cancel", option_1="Ok")
            return

        if name is None:
            name = self.fm_sel

        if not name:
            self.fm_console.log("No item selected.")
            return

        if name.endswith("/"):
            self.fm_console.log("Cannot download a folder. Right-click a file instead.")
            return

        cln = self.sel_dev.split()[0]
        d = self._select_save_dir("Save to")
        if not d:
            return

        src_path = f"{self.cur_path.rstrip('/')}/{name}"

        # Build progress bar on main thread before starting bg thread
        pframe, bar, lbl = self._show_progress(f"Downloading {name}...")

        def _download():
            total = self._get_android_file_size(cln, src_path)
            self.after(0, lambda: self.fm_console.log(
                f"Downloading {name}... ({self._fmt(total)})"))

            failed = False
            last_line = ""

            def _cb(line):
                nonlocal failed, last_line
                last_line = line
                if "[ERROR]" in line or "error:" in line.lower():
                    failed = True
                cur, tot = self._parse_adb_line(line)
                if cur is not None:
                    if tot == 100:  # percentage mode
                        self.after(0, lambda c=cur, t=tot, n=name:
                            self._update_progress(bar, lbl,
                                c, t, f"Downloading {n}... {c}%"))
                    else:  # bytes mode
                        use_total = total if total > 0 else tot
                        self.after(0, lambda c=cur, ut=use_total, n=name:
                            self._update_progress(bar, lbl,
                                c, ut, f"Downloading {n}... {self._fmt(c)} / {self._fmt(ut)}"))

            self.bk.run_live([ADB_PATH, "-s", cln, "pull", src_path, d], _cb)

            if failed:
                self.after(0, lambda: self.fm_console.log(f"✗ Failed: {name} — {last_line}"))
                self.after(0, lambda: self._update_progress(bar, lbl, 0, 1, f"✗ Failed: {name}"))
            else:
                self.after(0, lambda: self._update_progress(bar, lbl, 1, 1, f"✓ Done: {name} ({self._fmt(total)})"))
                self.after(0, lambda: self.fm_console.log(f"✓ Done: {name} ({self._fmt(total)})"))
                self.after(3000, pframe.destroy)  # auto-hide after 3s

        self.run_bg(_download)


    def fm_download_multiple(self):
        """Download multiple selected files with progress"""
        if not self.fm_selected:
            CustomDialog(self, title="Error", message="No items selected!", icon="cancel", option_1="Ok")
            return

        if not self.sel_dev:
            CustomDialog(self, title="Error", message="No device connected!", icon="cancel", option_1="Ok")
            return

        cln = self.sel_dev.split()[0]
        d = self._select_save_dir("Save to")
        if not d:
            return

        selected = list(self.fm_selected)
        total_files = len(selected)
        pframe, bar, lbl = self._show_progress(f"Downloading 0/{total_files}...")

        def _download():
            done = 0
            for i, name in enumerate(selected):
                src_path = f"{self.cur_path.rstrip('/')}/{name.rstrip('/')}"
                self.after(0, lambda n=name, idx=i:
                    self._update_progress(bar, lbl, idx, total_files,
                        f"Downloading {n} ({idx+1}/{total_files})..."))
                self.after(0, lambda n=name: self.fm_console.log(f"Downloading {n}..."))

                failed = False
                def _cb(line, n=name):
                    nonlocal failed
                    if "[ERROR]" in line or "error:" in line.lower():
                        failed = True

                self.bk.run_live([ADB_PATH, "-s", cln, "pull", src_path, d], _cb)

                if failed:
                    self.after(0, lambda n=name: self.fm_console.log(f"✗ Failed: {n}"))
                else:
                    done += 1

            failed_count = total_files - done
            msg = f"✓ Downloaded {done}/{total_files} file(s)."
            if failed_count:
                msg += f" ({failed_count} failed)"
            self.after(0, lambda: self._update_progress(bar, lbl, 1, 1, msg))
            self.after(0, lambda: self.fm_console.log(msg))
            self.after(3000, pframe.destroy)

        self.run_bg(_download)


    # --- SHELL ---
    def view_shell(self):
        self.clear()
        self.highlight("Shell")
        import tkinter as tk

        # Restore state if returning to this view
        _saved = self._view_state.get("Shell", {})
        self._shell_su = _saved.get("su", False)
        self._shell_cwd = _saved.get("cwd", "/")
        self._shell_device_name = _saved.get("device_name", self.sel_dev.split()[0] if self.sel_dev else "device")
        self._shell_input_buf = ""
        self._shell_input_start = "1.0"
        self._shell_history = list(_saved.get("history", []))
        self._shell_history_idx = -1
        self._shell_alive = True

        # Title bar
        title_row = ctk.CTkFrame(self.main, fg_color="transparent")
        title_row.pack(fill="x", pady=(10, 6))
        ctk.CTkLabel(title_row, text="ADB Shell Terminal",
                     font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(side="left")
        ctk.CTkButton(title_row, text="Clear", width=70, height=30,
                      fg_color=C["input_bg"], text_color=C["text_main"],
                      font=(F_UI, 11), command=self._shell_clear).pack(side="right", padx=4)

        # Single full black terminal - no separate input box at all
        term_frame = ctk.CTkFrame(self.main, fg_color="#000000", corner_radius=10)
        term_frame.pack(fill="both", expand=True)

        self._shell_text = tk.Text(
            term_frame,
            font=(F_MONO, 12),
            bg="#000000", fg="#00FF00",
            insertbackground="#00FF00",
            selectbackground="#1a4a1a",
            selectforeground="#00FF00",
            relief="flat", borderwidth=0,
            wrap="char", undo=False,
            state="normal",
        )
        vsb = tk.Scrollbar(term_frame, command=self._shell_text.yview,
                           bg="#111111", troughcolor="#000000",
                           activebackground="#333333", relief="flat", width=10)
        self._shell_text.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._shell_text.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        self._shell_text.tag_configure("err",    foreground="#FF4444")
        self._shell_text.tag_configure("warn",   foreground="#FFD700")
        self._shell_text.tag_configure("ok",     foreground="#00FF00")
        self._shell_text.tag_configure("dim",    foreground="#888888")
        self._shell_text.tag_configure("prompt", foreground="#00FF00")

        # Bind keys - block all default behaviour, handle everything manually
        self._shell_text.bind("<Key>",            self._shell_key)
        self._shell_text.bind("<Return>",         self._shell_on_enter)
        self._shell_text.bind("<BackSpace>",      self._shell_backspace)
        self._shell_text.bind("<Delete>",         lambda e: "break")
        self._shell_text.bind("<Up>",             self._shell_history_up)
        self._shell_text.bind("<Down>",           self._shell_history_down)
        self._shell_text.bind("<Home>",           self._shell_home)
        self._shell_text.bind("<End>",            lambda e: (self._shell_text.mark_set("insert","end"), "break")[1])
        self._shell_text.bind("<Left>",           self._shell_left)
        self._shell_text.bind("<Right>",          self._shell_right)
        self._shell_text.bind("<Control-c>",      self._shell_ctrl_c)
        self._shell_text.bind("<Control-l>",      lambda e: (self._shell_clear(), self._shell_show_prompt(), "break")[2])
        self._shell_text.bind("<Control-a>",      self._shell_select_input)
        self._shell_text.bind("<Control-u>",      self._shell_kill_line)
        self._shell_text.bind("<Tab>",            lambda e: "break")  # block tab for now
        self._shell_text.bind("<Button-1>",       lambda e: self._shell_text.after(1, self._shell_clamp_cursor))
        self._shell_text.bind("<<Paste>>",        self._shell_paste)
        self._shell_text.bind("<Control-v>",      self._shell_paste)
        self._shell_text.bind(RIGHT_CLICK,        self._shell_right_click)
        self._shell_text.focus_set()

        if not self.sel_dev:
            self._shell_raw_write("[No device connected]\n", "err")
        else:
            # If we have a saved cwd (returning to view), restore content and skip pwd fetch
            if _saved.get("cwd"):
                saved_content = _saved.get("content", "")
                if saved_content.strip():
                    self._shell_text.insert("1.0", saved_content)
                    self._shell_text.see("end")
                    # Reposition input_start to after restored content
                    self._shell_input_start = self._shell_text.index("end-1c")
                else:
                    self._shell_raw_write("[Session restored]\n", "dim")
                self.after(0, self._shell_show_prompt)
            else:
                def _init():
                    self._shell_cwd = self._shell_run_cmd("pwd").strip() or "/"
                    result = Backend.run([ADB_PATH, "-s", self.sel_dev.split()[0],
                                          "shell", "getprop", "ro.product.device"]).strip()
                    if result and not result.startswith("[ERROR]"):
                        self._shell_device_name = result
                    self.after(0, self._shell_show_prompt)
                threading.Thread(target=_init, daemon=True).start()

    def _shell_make_prompt(self):
        symbol = "#" if CONF.get("use_su", False) else "$"
        name = getattr(self, "_shell_device_name", "device")
        return f"{name}:{self._shell_cwd} {symbol} "

    def _shell_show_prompt(self):
        """Write a new prompt line and position cursor after it."""
        p = self._shell_make_prompt()
        self._shell_text.insert("end", p, "prompt")
        self._shell_text.see("end")
        self._shell_input_start = self._shell_text.index("end-1c")
        self._shell_input_buf = ""
        self._shell_history_idx = -1
        self._shell_text.mark_set("insert", "end")

    def _shell_raw_write(self, text, tag="ok"):
        """Insert text directly into terminal (never disables the widget)."""
        try:
            self._shell_text.insert("end", text, tag)
            self._shell_text.see("end")
        except Exception:
            pass

    def _shell_clamp_cursor(self):
        """Keep cursor inside the current input area."""
        try:
            if self._shell_text.compare("insert", "<", self._shell_input_start):
                self._shell_text.mark_set("insert", "end")
        except Exception:
            pass

    def _shell_right_click(self, event):
        """Right-click: copy selected text if any, else paste clipboard."""
        try:
            sel = self._shell_text.get("sel.first", "sel.last")
            if sel:
                # Has selection — copy it
                self.clipboard_clear()
                self.clipboard_append(sel)
            else:
                # Nothing selected — paste
                self._shell_paste(event)
        except Exception:
            # No selection tag present — paste
            self._shell_paste(event)
        return "break"

    # ── Input position helpers ─────────────────────────────────────────────
    def _shell_cursor_offset(self):
        """How many chars into _shell_input_buf is the cursor."""
        try:
            cur = self._shell_text.index("insert")
            start = self._shell_input_start
            # count chars between start and cursor
            text = self._shell_text.get(start, cur)
            return len(text)
        except Exception:
            return len(self._shell_input_buf)

    def _shell_left(self, event):
        try:
            if self._shell_text.compare("insert", ">", self._shell_input_start):
                self._shell_text.mark_set("insert", "insert-1c")
        except Exception:
            pass
        return "break"

    def _shell_right(self, event):
        self._shell_text.mark_set("insert", "insert+1c")
        return "break"

    def _shell_home(self, event):
        self._shell_text.mark_set("insert", self._shell_input_start)
        return "break"

    def _shell_select_input(self, event):
        """Ctrl+A: move cursor to start of input."""
        self._shell_text.mark_set("insert", self._shell_input_start)
        return "break"

    def _shell_kill_line(self, event):
        """Ctrl+U: clear current input."""
        try:
            self._shell_text.delete(self._shell_input_start, "end-1c")
            self._shell_input_buf = ""
        except Exception:
            pass
        return "break"

    def _shell_ctrl_c(self, event):
        """Ctrl+C: cancel current input and show new prompt."""
        self._shell_raw_write("^C\n", "err")
        self._shell_input_buf = ""
        self._shell_show_prompt()
        return "break"

    # ── Keystroke handlers ─────────────────────────────────────────────────
    def _shell_key(self, event):
        """Handle printable keystrokes."""
        if event.state & 0x4:  # Ctrl held - let bound shortcuts handle it
            return
        if event.char and event.char.isprintable():
            # Insert at cursor position (which is clamped inside input area)
            self._shell_clamp_cursor()
            cur_offset = self._shell_cursor_offset()
            self._shell_text.insert("insert", event.char, "ok")
            self._shell_input_buf = self._shell_input_buf[:cur_offset] + event.char + self._shell_input_buf[cur_offset:]
            self._shell_text.see("end")
            return "break"

    def _shell_backspace(self, event):
        """Backspace: remove char before cursor if inside input area."""
        try:
            if self._shell_text.compare("insert", ">", self._shell_input_start):
                cur_offset = self._shell_cursor_offset()
                self._shell_text.delete("insert-1c", "insert")
                if cur_offset > 0:
                    self._shell_input_buf = self._shell_input_buf[:cur_offset-1] + self._shell_input_buf[cur_offset:]
        except Exception:
            pass
        return "break"

    def _shell_paste(self, event):
        """Ctrl+V / Paste: insert clipboard at cursor."""
        try:
            text = self._shell_text.clipboard_get()
            # Only use first line to avoid multiline paste chaos
            text = text.split("\n")[0]
            cur_offset = self._shell_cursor_offset()
            for ch in text:
                if ch.isprintable():
                    self._shell_text.insert("insert", ch, "ok")
                    self._shell_input_buf = self._shell_input_buf[:cur_offset] + ch + self._shell_input_buf[cur_offset:]
                    cur_offset += 1
            self._shell_text.see("end")
        except Exception:
            pass
        return "break"

    # ── History ────────────────────────────────────────────────────────────
    def _shell_history_up(self, event):
        if not self._shell_history:
            return "break"
        if self._shell_history_idx < len(self._shell_history) - 1:
            self._shell_history_idx += 1
        self._shell_set_input(self._shell_history[self._shell_history_idx])
        return "break"

    def _shell_history_down(self, event):
        if self._shell_history_idx > 0:
            self._shell_history_idx -= 1
            self._shell_set_input(self._shell_history[self._shell_history_idx])
        else:
            self._shell_history_idx = -1
            self._shell_set_input("")
        return "break"

    def _shell_set_input(self, text):
        """Replace current input line with text."""
        try:
            self._shell_text.delete(self._shell_input_start, "end-1c")
            self._shell_text.insert("end", text, "ok")
            self._shell_input_buf = text
            self._shell_text.mark_set("insert", "end")
        except Exception:
            pass

    # ── Command execution ──────────────────────────────────────────────────
    def _shell_on_enter(self, event=None):
        cmd = self._shell_input_buf.strip()
        self._shell_raw_write("\n")
        self._shell_input_buf = ""

        if not cmd:
            self._shell_show_prompt()
            return "break"

        # Save to history (save raw cmd, before su wrapping)
        if not self._shell_history or self._shell_history[0] != cmd:
            self._shell_history.insert(0, cmd)
            if len(self._shell_history) > 100:
                self._shell_history.pop()

        # Built-ins (handle before any su wrapping)
        if cmd == "clear":
            self._shell_text.delete("1.0", "end")
            self._shell_show_prompt()
            return "break"

        if cmd == "su":
            self._shell_su = True
            self._shell_raw_write("[su mode enabled]\n", "warn")
            self._shell_show_prompt()
            return "break"

        if cmd == "exit":
            if self._shell_su:
                self._shell_su = False
                self._shell_raw_write("[returned to normal shell]\n", "dim")
            self._shell_show_prompt()
            return "break"

        def _run():
            if cmd.startswith("cd") and (len(cmd) == 2 or cmd[2] == " "):
                target = cmd[3:].strip() if len(cmd) > 3 else "$HOME"
                
                # Strip surrounding quotes that the user may have typed
                # Strip surrounding quotes the user may have typed
                if (target.startswith('"') and target.endswith('"')) or \
                   (target.startswith("'") and target.endswith("'")):
                    target = target[1:-1]
                    # Re-quote cleanly after stripping
                    full_target = shlex.quote(f"{self._shell_cwd.rstrip('/')}/{target}" if not target.startswith('/') else target)
                elif any(c in target for c in ('*', '?', '[')):
                    # Glob: prepend cwd but don't quote, let shell expand
                    prefix = "" if target.startswith("/") else f"{self._shell_cwd.rstrip('/')}/"
                    full_target = f"{prefix}{target}"
                else:
                    # Plain path: resolve and quote safely
                    if target.startswith("/"):
                        full_target = shlex.quote(target)
                    else:
                        full_target = shlex.quote(f"{self._shell_cwd.rstrip('/')}/{target}")

                run_cmd = f"cd {full_target} && pwd"

                if self._shell_su:
                    full = [ADB_PATH, "-s", self.sel_dev.split()[0], "shell", "su", "-c", run_cmd]
                else:
                    full = [ADB_PATH, "-s", self.sel_dev.split()[0], "shell", run_cmd]

                try:
                    res = subprocess.run(
                        full, capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=10,
                        **Backend._no_window_kwargs()
                    )
                    stdout = res.stdout.strip()
                    stderr = res.stderr.strip()

                    if stdout.startswith("/"):
                        self._shell_cwd = stdout.split("\n")[-1].strip()
                    else:
                        err_line = stderr or stdout
                        err_line = err_line.split("$")[0].strip()
                        self.after(0, lambda o=err_line: self._shell_raw_write(o + "\n", "err"))

                except Exception as e:
                    self.after(0, lambda err=e: self._shell_raw_write(f"[error: {err}]\n", "err"))
            else:
                output = self._shell_run_cmd(cmd)
                if output:
                    tag = "err" if any(
                        p in output.lower()
                        for p in ("error", "denied", "not found", "exception", "permission")
                    ) else "ok"
                    self.after(0, lambda o=output, t=tag: self._shell_raw_write(o, t))

            self.after(0, self._shell_show_prompt)

        threading.Thread(target=_run, daemon=True).start()  # <-- was missing!
        return "break"

    def _shell_run_cmd(self, cmd):
        if not self.sel_dev:
            return "[No device]\n"
        clean = self.sel_dev.split()[0]
        
        # Prepend cwd since adb shell is stateless (each call is a new session)
        if self._shell_cwd and self._shell_cwd != "/":
            actual_cmd = f"cd {self._shell_cwd} && {cmd}"
        else:
            actual_cmd = cmd
        
        if self._shell_su:
            full_cmd = [ADB_PATH, "-s", clean, "shell", "su", "-c", actual_cmd]
        else:
            full_cmd = [ADB_PATH, "-s", clean, "shell", actual_cmd]
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=15,
                                 **Backend._no_window_kwargs())
            out = res.stdout
            if res.stderr:
                out += res.stderr
            return out
        except subprocess.TimeoutExpired:
            return "[timeout]\n"
        except Exception as e:
            return f"[error: {e}]\n"

    def _shell_write(self, text, tag="ok"):
        self._shell_raw_write(text, tag)

    def _shell_clear(self):
        try:
            self._shell_text.delete("1.0", "end")
            self._shell_show_prompt()
        except Exception:
            pass

    # Legacy stubs
    def _shell_stop(self): self._shell_alive = False
    def _shell_reconnect(self): self.view_shell()
    def start_shell_session(self): pass
    def clear_terminal(self): self._shell_clear()
    def append_shell_output(self, text): self._shell_raw_write(text)
    def _run_shell(self): pass
    def execute_shell_command(self, event): return "break" if event else None
    
    # --- LOGCAT ---
    def view_logcat(self):
        self.clear()
        self.highlight("Logcat")
        import tkinter as tk
        ctk.CTkLabel(self.main, text="Live Logcat", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(
            anchor="w", pady=(10, 20))

        bar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        self.btn_log_start = ctk.CTkButton(bar, text="Start", fg_color=C["success"], command=self.start_logcat)
        self.btn_log_start.pack(side="left", padx=5)
        ctk.CTkButton(bar, text="Stop", fg_color=C["danger"], command=self.stop_logcat).pack(side="left", padx=5)
        ctk.CTkButton(bar, text="Save Log", fg_color=C["primary"], command=self.save_logcat).pack(side="left", padx=5)

        # Colored terminal for logcat (same style as shell)
        term_frame = ctk.CTkFrame(self.main, fg_color="#000000", corner_radius=10)
        term_frame.pack(fill="both", expand=True)

        self._logcat_text = tk.Text(
            term_frame,
            font=(F_MONO, 11),
            bg="#000000", fg="#CCCCCC",
            insertbackground="#CCCCCC",
            selectbackground="#1a3a4a",
            selectforeground="#FFFFFF",
            relief="flat", borderwidth=0,
            wrap="char", undo=False,
            state="disabled",
        )
        vsb = tk.Scrollbar(term_frame, command=self._logcat_text.yview,
                           bg="#111111", troughcolor="#000000",
                           activebackground="#333333", relief="flat", width=10)
        self._logcat_text.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._logcat_text.pack(side="left", fill="both", expand=True, padx=6, pady=6)

        # Right-click to copy selected text in logcat
        def _logcat_right_click(event):
            try:
                sel = self._logcat_text.get("sel.first", "sel.last")
                if sel:
                    self.clipboard_clear()
                    self.clipboard_append(sel)
            except Exception:
                pass
            return "break"
        self._logcat_text.bind(RIGHT_CLICK, _logcat_right_click)

        # Color tags per logcat level
        self._logcat_text.tag_configure("V", foreground="#888888")  # Verbose - gray
        self._logcat_text.tag_configure("D", foreground="#4FC3F7")  # Debug - blue
        self._logcat_text.tag_configure("I", foreground="#81C784")  # Info - green
        self._logcat_text.tag_configure("W", foreground="#FFD54F")  # Warning - yellow
        self._logcat_text.tag_configure("E", foreground="#EF5350")  # Error - red
        self._logcat_text.tag_configure("F", foreground="#FF1744")  # Fatal - bright red
        self._logcat_text.tag_configure("default", foreground="#CCCCCC")

        # Restore saved logcat content if returning to this view
        if "Logcat" in self._view_state:
            saved_content = self._view_state["Logcat"].get("content", "")
            if saved_content.strip():
                self._logcat_text.configure(state="normal")
                self._logcat_text.insert("1.0", saved_content)
                self._logcat_text.see("end")
                self._logcat_text.configure(state="disabled")

    def _logcat_write(self, line):
        """Write a logcat line with color based on log level."""
        try:
            # Logcat format: "MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: message"
            # Level is a single char: V D I W E F
            parts = line.split()
            level = "default"
            if len(parts) >= 5:
                lvl_char = parts[4] if len(parts[4]) == 1 else "default"
                if lvl_char in ("V", "D", "I", "W", "E", "F"):
                    level = lvl_char
            self._logcat_text.configure(state="normal")
            self._logcat_text.insert("end", line + "\n", level)
            self._logcat_text.see("end")
            self._logcat_text.configure(state="disabled")
        except Exception:
            pass

    def start_logcat(self):
        if not self.sel_dev: return

        self.log_proc = True
        self.btn_log_start.configure(state="disabled")
        self._logcat_queue = queue.Queue()
        clean = self.sel_dev.split()[0]

        def _loop():
            kwargs = Backend._no_window_kwargs()
            kwargs["stdin"] = subprocess.DEVNULL

            self.adb_process = subprocess.Popen(
                [ADB_PATH, "-s", clean, "logcat", "-v", "time"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                **kwargs
            )

            for line in self.adb_process.stdout:
                if not self.log_proc:
                    break
                self._logcat_queue.put(line.strip())

            try:
                self.adb_process.kill()
            except Exception:
                pass

        def _drain_queue():
            batch_size = 1000 if self._logcat_queue.qsize() > 1000 else 100

            try:
                for _ in range(batch_size):
                    line = self._logcat_queue.get_nowait()
                    self._logcat_write(line)
            except queue.Empty:
                pass

            if self.log_proc:
                self.after(50, _drain_queue)

        self.thread = threading.Thread(target=_loop, daemon=True)
        self.thread.start()
        _drain_queue()

    def stop_logcat(self):
        self.log_proc = False

        if hasattr(self, 'adb_process'):
            try:
                self.adb_process.kill()
            except Exception:
                pass

        if hasattr(self, '_logcat_queue'):
            with self._logcat_queue.mutex:
                self._logcat_queue.queue.clear()

        self.btn_log_start.configure(state="normal")

    def save_logcat(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile="logcat_output.txt"
        )
        if f:
            self._logcat_text.configure(state="normal")
            content = self._logcat_text.get("1.0", "end")
            self._logcat_text.configure(state="disabled")
            with open(f, "w", encoding="utf-8") as file:
                file.write(content)

    # --- FASTBOOT ---
    def view_fastboot(self):
        self.clear()
        self.highlight("Fastboot")
        ctk.CTkLabel(self.main, text="Fastboot Tools", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(
            anchor="w", pady=(10, 20))

        warn = ctk.CTkFrame(self.main, fg_color="#4a1010", corner_radius=10, border_width=1, border_color=C["danger"])
        warn.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(warn, text="ADVANCED: Use with caution.", text_color="#FF9999").pack(pady=10)

        self.fb_card("Bootloader",
                     [("Check Info", C["primary"], ["getvar", "all"]), ("Unlock OEM", C["danger"], ["oem", "unlock"])])

        # --- Custom Flash Card ---
        flash_card = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        flash_card.pack(fill="x", pady=10, ipady=10)
        ctk.CTkLabel(flash_card, text="Flash Partition", font=(F_UI, 16, "bold"), text_color=C["text_main"]).pack(
            anchor="w", padx=20, pady=(10, 5))

        # Partition selection mode
        self._fb_part_mode = ctk.StringVar(value="select")
        mode_row = ctk.CTkFrame(flash_card, fg_color="transparent")
        mode_row.pack(fill="x", padx=20, pady=(0, 5))
        ctk.CTkRadioButton(mode_row, text="Select partition", variable=self._fb_part_mode, value="select",
                           command=self._fb_toggle_part_mode, text_color=C["text_main"]).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(mode_row, text="Write partition name", variable=self._fb_part_mode, value="write",
                           command=self._fb_toggle_part_mode, text_color=C["text_main"]).pack(side="left")

        # Preset partition dropdown
        self._fb_part_select_frame = ctk.CTkFrame(flash_card, fg_color="transparent")
        self._fb_part_select_frame.pack(fill="x", padx=20, pady=2)
        self._fb_part_dropdown = ctk.CTkOptionMenu(
            self._fb_part_select_frame,
            values=["boot", "recovery", "vbmeta", "system", "vendor", "dtbo", "super", "userdata"],
            fg_color=C["input_bg"], text_color=C["text_main"], width=200
        )
        self._fb_part_dropdown.pack(side="left")

        # Manual partition entry
        self._fb_part_write_frame = ctk.CTkFrame(flash_card, fg_color="transparent")
        self._fb_part_entry = ctk.CTkEntry(
            self._fb_part_write_frame,
            placeholder_text="Write the partition name WITHOUT A/B",
            fg_color=C["input_bg"], border_width=0, text_color=C["text_main"], width=280
        )
        self._fb_part_entry.pack(side="left")
        # starts hidden
        self._fb_part_write_frame.pack_forget()

        # A/B slot selection
        ab_row = ctk.CTkFrame(flash_card, fg_color="transparent")
        ab_row.pack(fill="x", padx=20, pady=(8, 5))
        ctk.CTkLabel(ab_row, text="Slot:", text_color=C["text_sub"], font=(F_UI, 12)).pack(side="left",
                                                                                                 padx=(0, 10))
        self._fb_slot = ctk.StringVar(value="none")
        ctk.CTkRadioButton(ab_row, text="No slot (non-A/B)", variable=self._fb_slot, value="none",
                           text_color=C["text_main"]).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(ab_row, text="_a", variable=self._fb_slot, value="_a",
                           text_color=C["text_main"]).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(ab_row, text="_b", variable=self._fb_slot, value="_b",
                           text_color=C["text_main"]).pack(side="left")

        # Flash button
        ctk.CTkButton(flash_card, text="Choose .img and Flash", fg_color=C["warning"],
                      height=40, command=self.fb_flash_custom).pack(padx=20, pady=(10, 15), anchor="w")

        self.fb_console = LogConsole(self.main, height=200)
        self.fb_console.pack(fill="x", pady=20)
        # Restore saved console content
        _fb_saved = self._view_state.get("Fastboot", {})
        if _fb_saved.get("content", "").strip():
            self.fb_console.text_area.configure(state="normal")
            self.fb_console.text_area.insert("1.0", _fb_saved["content"])
            self.fb_console.text_area.see("end")
            self.fb_console.text_area.configure(state="disabled")

    def fb_card(self, title, actions):
        f = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        f.pack(fill="x", pady=10, ipady=10)
        ctk.CTkLabel(f, text=title, font=(F_UI, 16, "bold"), text_color=C["text_main"]).pack(side="left", padx=20)
        for item in actions:
            label, col = item[0], item[1]
            func = item[3] if len(item) > 3 and item[3] else lambda c=item[2]: self.fb_run(c)
            ctk.CTkButton(f, text=label, fg_color=col, width=120, command=func).pack(side="right", padx=10)

    def fb_run(self, cmd):
        if not self.sel_dev: return
        clean = self.sel_dev.split()[0]
        self.fb_console.log(f"Fastboot: {' '.join(cmd)}")
        pframe, bar, lbl = self._show_progress(f"Running: fastboot {' '.join(cmd)}", self.fb_console)

        def _run():
            self.bk.run_live(
                [FASTBOOT_PATH, "-s", clean] + cmd,
                lambda l: (
                    self.fb_console.log(l),
                    self.after(0, lambda ll=l: lbl.configure(text=ll[:90]))
                )
            )
            self.after(0, lambda: self._update_progress(bar, lbl, 1, 1, "✓ Done"))
            self.after(3000, pframe.destroy)

        self.run_bg(_run)

    def _fb_toggle_part_mode(self):
        if self._fb_part_mode.get() == "select":
            self._fb_part_write_frame.pack_forget()
            self._fb_part_select_frame.pack(fill="x", padx=20, pady=2)
        else:
            self._fb_part_select_frame.pack_forget()
            self._fb_part_write_frame.pack(fill="x", padx=20, pady=2)

    def fb_flash_custom(self):
        if self._fb_part_mode.get() == "select":
            base_partition = self._fb_part_dropdown.get()
        else:
            base_partition = self._fb_part_entry.get().strip()
            if not base_partition:
                CustomDialog(self, title="Error", message="Please enter a partition name.", icon="warning", option_1="Ok")
                return

        slot = self._fb_slot.get()
        partition = base_partition + ("" if slot == "none" else slot)

        f = filedialog.askopenfilename(filetypes=[("IMG files", "*.img")])
        if f:
            msg = CustomDialog(
                self,
                title="Confirm Flash",
                message=f"Flash '{partition}' with:\n{f}\n\nAre you sure?",
                icon="warning",
                option_1="Yes, Flash",
                option_2="Cancel"
            )
            if msg.get() == "Yes, Flash":
                self.fb_run(["flash", partition, f])

    # --- CONNECTION ---
    def view_connect(self):
        self.clear()
        self.highlight("Connection")
        _conn_saved = self._view_state.get("Connection", {})
        ctk.CTkLabel(self.main, text="Connection ADB", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        # Step 1 - TCP/IP
        c1 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c1.pack(fill="x", pady=10)
        ctk.CTkLabel(c1, text="1. Enable TCP/IP Mode", font=(F_UI, 14, "bold")).pack(side="left", padx=20, pady=20)
        ctk.CTkButton(c1, text="Enable (5555)", fg_color=C["primary"], command=lambda: self.adb_cmd_console(["tcpip", "5555"])).pack(side="right", padx=20)

        # Step 2 - Pair (Android 11+)
        c_pair = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c_pair.pack(fill="x", pady=10)
        ctk.CTkLabel(c_pair, text="2. Pair Device (Android 11+)", font=(F_UI, 14, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(c_pair, text="Go to Developer Options → Connection debugging → Pair with pairing code",
                     font=(F_UI, 11), text_color=C["text_sub"]).pack(anchor="w", padx=20, pady=(0, 8))
        r_pair = ctk.CTkFrame(c_pair, fg_color="transparent")
        r_pair.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_pair_ip = ctk.CTkEntry(r_pair, placeholder_text="IP:PAIR_PORT", height=40, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_pair_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        if _conn_saved.get("pair_ip"): self.ent_pair_ip.insert(0, _conn_saved["pair_ip"])
        self.ent_pair_code = ctk.CTkEntry(r_pair, placeholder_text="6-digit code", height=40, width=130, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_pair_code.pack(side="left", padx=(0, 10))
        ctk.CTkButton(r_pair, text="Pair", height=40, fg_color=C["warning"], command=self.do_connect_pair).pack(side="right")

        # Step 3 - Connect
        c2 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c2.pack(fill="x", pady=10)
        ctk.CTkLabel(c2, text="3. Connect", font=(F_UI, 14, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        r = ctk.CTkFrame(c2, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_ip = ctk.CTkEntry(r, placeholder_text="IP:PORT", height=40, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        _saved_ip = _conn_saved.get("ip", "") or CONF.get("last_ip", "")
        if _saved_ip: self.ent_ip.insert(0, _saved_ip)
        ctk.CTkButton(r, text="Connect", height=40, fg_color=C["success"], command=self.do_connect_connect).pack(side="right")

        # Step 4 - Disconnect
        c3 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c3.pack(fill="x", pady=10)
        ctk.CTkLabel(c3, text="4. Disconnect", font=(F_UI, 14, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkButton(c3, text="Disconnect All", height=40, fg_color=C["danger"], command=self.do_connect_disconnect_all).pack(fill="x", padx=20, pady=(0, 10))
        r_disc = ctk.CTkFrame(c3, fg_color="transparent")
        r_disc.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_disc_ip = ctk.CTkEntry(r_disc, placeholder_text="IP:PORT", height=40, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_disc_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(r_disc, text="Disconnect", height=40, fg_color=C["danger"], command=self.do_connect_disconnect).pack(side="right")

        self.connect_console = LogConsole(self.main, height=200)
        self.connect_console.pack(fill="x", pady=20)

    def do_connect_connect(self):
        ip = self.ent_ip.get().strip()
        if not ip:
            self.connect_console.log("[ERROR] Please enter an IP:PORT.")
            return
        save_config("last_ip", ip)
        self.connect_console.log(f"Connecting to {ip}...")
        self._pause_dev_loop = True
        def _connect():
            try:
                result = self.bk.run([ADB_PATH, "connect", ip], timeout=30)
                self.connect_console.log(result)
            finally:
                self._pause_dev_loop = False
        self.run_bg(_connect)

    def do_connect_pair(self):
        ip = self.ent_pair_ip.get().strip()
        code = self.ent_pair_code.get().strip()
        if not ip or not code:
            self.connect_console.log("[ERROR] Please enter both IP:PORT and the pairing code.")
            return
        self.connect_console.log(f"Pairing with {ip}...")
        def _pair():
            self.bk.run_live([ADB_PATH, "pair", ip, code], lambda l: self.connect_console.log(l))
        self.run_bg(_pair)

    def do_connect_disconnect_all(self):
        self.adb_cmd_console(["disconnect"])
        self.connect_console.log("All connect connections disconnected!")

    def do_connect_disconnect(self):
        target = self.ent_disc_ip.get().strip()
        if not target:
            self.connect_console.log("[ERROR] Please enter an IP:PORT to disconnect from!")
            return
        self.adb_cmd_console(["disconnect", target])
        self.connect_console.log(f"Disconnecting from {target}...")

    # --- TWEAKS ---
    def view_tweaks(self):
        self.clear()
        self.highlight("Tweaks")
        ctk.CTkLabel(self.main, text="System Tweaks", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        scroll = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Toggles
        f = ctk.CTkFrame(scroll, fg_color=C["bg_surface"], corner_radius=15)
        f.pack(fill="x", pady=10)
        tweaks = [("Show Taps", "system", "show_touches"), ("Pointer Location", "system", "pointer_location"), ("Stay Awake (USB)", "global", "stay_on_while_plugged_in")]
        for label, ns, key in tweaks:
            r = ctk.CTkFrame(f, fg_color="transparent")
            r.pack(fill="x", pady=8, padx=10)
            ctk.CTkLabel(r, text=label, text_color=C["text_main"], font=(F_UI, 13)).pack(side="left", padx=20)
            ctk.CTkButton(r, text="ON", width=60, fg_color=C["success"], command=lambda nn=ns, kk=key: self.adb_cmd_console(["shell", "settings", "put", nn, kk, "1"])).pack(side="right", padx=5)
            ctk.CTkButton(r, text="OFF", width=60, fg_color="#333", command=lambda nn=ns, kk=key: self.adb_cmd_console(["shell", "settings", "put", nn, kk, "0"])).pack(side="right", padx=5)

        # DPI
        f2 = ctk.CTkFrame(scroll, fg_color=C["bg_surface"], corner_radius=15)
        f2.pack(fill="x", pady=10)
        ctk.CTkLabel(f2, text="DPI Changer", font=(F_UI, 14, "bold")).pack(anchor="w", padx=20, pady=10)
        r2 = ctk.CTkFrame(f2, fg_color="transparent")
        r2.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_dpi = ctk.CTkEntry(r2, placeholder_text="e.g. 400", width=100)
        self.ent_dpi.pack(side="left", padx=5)
        ctk.CTkButton(r2, text="Apply", width=80, command=lambda: self.adb_cmd_console(["shell", "wm", "density", self.ent_dpi.get()])).pack(side="left", padx=5)
        ctk.CTkButton(r2, text="Reset", width=80, fg_color="#333", command=lambda: self.adb_cmd_console(["shell", "wm", "density", "reset"])).pack(side="left", padx=5)

        # Animation
        f3 = ctk.CTkFrame(scroll, fg_color=C["bg_surface"], corner_radius=15)
        f3.pack(fill="x", pady=10)
        ctk.CTkLabel(f3, text="Animation Scale", font=(F_UI, 14, "bold")).pack(anchor="w", padx=20, pady=10)
        r3 = ctk.CTkFrame(f3, fg_color="transparent")
        r3.pack(fill="x", padx=20, pady=(0, 20))
        for scale in ["0.0", "0.5", "1.0", "1.5"]:
            ctk.CTkButton(r3, text=f"{scale}x", width=60, command=lambda s=scale: self.set_anim(s)).pack(side="left", padx=5)

        self.tweaks_console = LogConsole(scroll, height=150)
        self.tweaks_console.pack(fill="x", pady=20)

    def set_anim(self, scale):
        for key in ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]:
            self.adb_cmd_console(["shell", "settings", "put", "global", key, scale])

    # --- BACKUP ---
    def view_backup(self):
        self.clear()
        self.highlight("Backup")
        ctk.CTkLabel(self.main, text="Backup & Restore", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        grid = ctk.CTkFrame(self.main, fg_color="transparent")
        grid.pack(fill="x", padx=30)
        b_card = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=15)
        b_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(b_card, text="Backup Device", font=(F_UI, 18, "bold")).pack(pady=20)
        ctk.CTkButton(b_card, text="Start Backup", height=50, fg_color=C["primary"], command=self.do_backup).pack(pady=20, padx=20)

        r_card = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=15)
        r_card.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(r_card, text="Restore Device", font=(F_UI, 18, "bold")).pack(pady=20)
        ctk.CTkButton(r_card, text="Start Restore", height=50, fg_color=C["warning"], command=self.do_restore).pack(pady=20, padx=20)

        self.backup_console = LogConsole(self.main, height=200)
        self.backup_console.pack(fill="x", pady=20)

    def do_backup(self):
        f = filedialog.asksaveasfilename(defaultextension=".ab", filetypes=[("Backup", "*.ab")])
        if f: self.adb_cmd_console(["backup", "-all", "-apk", "-shared", "-f", f], "Backup Started - Check Device")

    def do_restore(self):
        f = filedialog.askopenfilename(filetypes=[("Backup", "*.ab")])
        if f: self.adb_cmd_console(["restore", f], "Restore Started - Check Device")

    # --- DEVICES ---
    def view_devices(self):
        self.clear()
        self.highlight("Devices")
        ctk.CTkLabel(self.main, text="Device Manager", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        info_card = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        info_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(info_card, text="Active Device", font=(F_UI, 14, "bold"), text_color=C["text_main"]).pack(anchor="w", padx=20, pady=(15, 5))
        self.dev_active_lbl = ctk.CTkLabel(info_card, text=self.sel_dev or "None",
                                           font=(F_UI, 13), text_color=C["primary"])
        self.dev_active_lbl.pack(anchor="w", padx=20, pady=(0, 15))

        list_card = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        list_card.pack(fill="x", pady=(0, 15))
        top = ctk.CTkFrame(list_card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(top, text="Connected Devices", font=(F_UI, 14, "bold"), text_color=C["text_main"]).pack(side="left")
        ctk.CTkButton(top, text="↻", width=32, height=32, font=(F_UI, 18),
                      fg_color="transparent", hover_color=C["bg_hover"],
                      text_color=C["text_sub"], command=self._refresh_device_list).pack(side="right", padx=(0, 5))

        self.dev_list_frame = ctk.CTkScrollableFrame(list_card, fg_color="transparent", height=200)
        self.dev_list_frame.pack(fill="x", padx=20, pady=(0, 15))
        self._refresh_device_list()

        self.dev_console = LogConsole(self.main, height=150)
        self.dev_console.pack(fill="x", pady=10)
        # Restore saved console content
        _dev_saved = self._view_state.get("Devices", {})
        if _dev_saved.get("content", "").strip():
            self.dev_console.text_area.configure(state="normal")
            self.dev_console.text_area.insert("1.0", _dev_saved["content"])
            self.dev_console.text_area.see("end")
            self.dev_console.text_area.configure(state="disabled")

    def _refresh_device_list(self):
        for w in self.dev_list_frame.winfo_children():
            w.destroy()

        devices = self.bk.get_devices()
        if not devices:
            ctk.CTkLabel(self.dev_list_frame, text="No devices found.",
                         text_color=C["text_sub"], font=(F_UI, 12)).pack(pady=10)
            return

        for dev in devices:
            is_selected = dev == self.sel_dev
            serial = dev.split()[0]
            mode = dev.split("(")[1].replace(")", "") if "(" in dev else ""
            if "ADB" in mode:
                model = self.bk.run([ADB_PATH, "-s", serial, "shell", "getprop", "ro.product.model"]).strip()
                label_text = f"  ●  {model or serial}  [{serial}]  ({mode})"
            else:
                label_text = f"  ●  {serial}  ({mode})"

            row = ctk.CTkButton(
                self.dev_list_frame,
                text=label_text,
                anchor="w",
                font=(F_UI, 12),
                fg_color=C["bg_hover"] if is_selected else "transparent",
                hover_color=C["bg_hover"],
                text_color=C["success"] if is_selected else C["text_main"],
                command=lambda d=dev: self._select_device(d)
            )
            row.pack(fill="x", pady=2)

    def _select_device(self, dev):
        self.sel_dev = dev
        save_config("last_device", dev.split()[0])  # save serial for next launch
        if hasattr(self, 'dev_active_lbl') and self.dev_active_lbl.winfo_exists():
            self.dev_active_lbl.configure(text=dev)
        name = self.bk.run([ADB_PATH, "-s", dev.split()[0], "shell", "settings", "get", "global", "device_name"]).strip()
        self.status_lbl.configure(text=name)
        self.status_dot.configure(text_color=C["success"])
        self._refresh_device_list()
        if hasattr(self, 'dev_console'):
            self.dev_console.log(f"Switched to {dev}")

    # --- SETTINGS ---
    def view_settings(self):
        self.clear()
        self.highlight("Settings")
        ctk.CTkLabel(self.main, text="Settings", font=(F_UI, 36, "bold"), text_color=C["text_main"]).pack(
            anchor="w", pady=(10, 20))

        c = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(c, text="Appearance", font=(F_UI, 16, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(row, text="Light Mode", height=50, fg_color="#E0E0E0", text_color="black",
                      command=lambda: [ctk.set_appearance_mode("Light"), save_config("theme", "Light")]).pack(
            side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(row, text="Dark Mode", height=50, fg_color="#222222", text_color="white",
                      command=lambda: [ctk.set_appearance_mode("Dark"), save_config("theme", "Dark")]).pack(side="left",
                                                                                                            fill="x",
                                                                                                            expand=True,
                                                                                                            padx=5)

        c2 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c2.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(c2, text="Advanced", font=(F_UI, 16, "bold")).pack(anchor="w", padx=20, pady=(20, 10))

        # ADB Path picker
        adb_row = ctk.CTkFrame(c2, fg_color="transparent")
        adb_row.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(adb_row, text="ADB Executable Path", text_color=C["text_main"], font=(F_UI, 13)).pack(
            side="left", padx=20)
        self.ent_adb_path = ctk.CTkEntry(adb_row,
                                         placeholder_text="e.g. location_to\\adb leave blank for system PATH",
                                         fg_color=C["input_bg"], border_width=0, text_color=C["text_main"], width=320)
        self.ent_adb_path.pack(side="left", padx=(0, 10))
        if CONF.get("adb_path", ""):
            self.ent_adb_path.insert(0, CONF["adb_path"])
        ctk.CTkButton(adb_row, text="Browse", width=80, fg_color=C["primary"],
                      command=self._browse_adb_path).pack(side="left", padx=(0, 10))
        ctk.CTkButton(adb_row, text="Save", width=70, fg_color=C["success"],
                      command=self._save_adb_path).pack(side="left")

        su_row = ctk.CTkFrame(c2, fg_color="transparent")
        su_row.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(su_row, text="Use Super User (Root)", text_color=C["text_main"], font=(F_UI, 13)).pack(
            side="left", padx=20)

        self.su_switch = ctk.CTkSwitch(
            su_row,
            text="",
            command=self.toggle_su,
            fg_color="#555555",
            progress_color=C["success"],
            button_color=C["text_main"],
            button_hover_color=C["bg_hover"]
        )
        self.su_switch.pack(side="right", padx=20)

        if CONF.get("use_su", False):
            self.su_switch.select()

        refresh_row = ctk.CTkFrame(c2, fg_color="transparent")
        refresh_row.pack(fill="x", padx=20, pady=(10, 20))
        ctk.CTkLabel(refresh_row, text="Dashboard Refresh Interval", text_color=C["text_main"],
                     font=(F_UI, 13)).pack(side="left", padx=20)

        self.refresh_label = ctk.CTkLabel(refresh_row, text=f"{CONF.get('refresh_interval', 3)}s",
                                          text_color=C["primary"], font=(F_UI, 13, "bold"))
        self.refresh_label.pack(side="right", padx=(0, 10))

        self.refresh_slider = ctk.CTkSlider(
            refresh_row,
            from_=1,
            to=10,
            number_of_steps=9,
            command=self.update_refresh_interval,
            fg_color="#555555",
            progress_color=C["primary"],
            button_color=C["primary"],
            button_hover_color=C["success"]
        )
        self.refresh_slider.set(CONF.get("refresh_interval", 3))
        self.refresh_slider.pack(side="right", padx=20, fill="x", expand=True)

        poll_row = ctk.CTkFrame(c2, fg_color="transparent")
        poll_row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(poll_row, text="Device Poll Interval", text_color=C["text_main"],
                     font=(F_UI, 13)).pack(side="left", padx=20)

        self.poll_label = ctk.CTkLabel(poll_row, text=f"{CONF.get('device_poll_interval', 2)}s",
                                       text_color=C["primary"], font=(F_UI, 13, "bold"))
        self.poll_label.pack(side="right", padx=(0, 10))

        self.poll_slider = ctk.CTkSlider(
            poll_row, from_=1, to=10, number_of_steps=9,
            command=self._update_poll_interval,
            fg_color="#555555", progress_color=C["primary"],
            button_color=C["primary"], button_hover_color=C["success"]
        )
        self.poll_slider.set(CONF.get("device_poll_interval", 2))
        self.poll_slider.pack(side="right", padx=20, fill="x", expand=True)

    def update_refresh_interval(self, value):
        global CONF
        interval = int(value)
        self.refresh_label.configure(text=f"{interval}s")
        save_config("refresh_interval", interval)
        CONF = load_config()

    def _update_poll_interval(self, value):
        global CONF
        interval = int(value)
        self.poll_label.configure(text=f"{interval}s")
        save_config("device_poll_interval", interval)
        CONF = load_config()

    def toggle_su(self):
        global CONF
        enabled = self.su_switch.get() == 1
        save_config("use_su", enabled)
        CONF = load_config()

    def _browse_adb_path(self):
        if os.name == "nt":
            f = filedialog.askopenfilename(filetypes=[("ADB Executable", "adb.exe"), ("All files", "*.*")])
        else:
            f = filedialog.askopenfilename(title="Select ADB executable")
        if f:
            self.ent_adb_path.delete(0, "end")
            self.ent_adb_path.insert(0, f)

    def _save_adb_path(self):
        global ADB_PATH
        path = self.ent_adb_path.get().strip()
        ADB_PATH = path if path else "adb"
        save_config("adb_path", path)
        CustomDialog(self, title="Saved", message=f"ADB path updated!\nNow using: {ADB_PATH}", icon="check", option_1="Ok")

if __name__ == "__main__":
    app = XtremeADB()
    app.mainloop()
