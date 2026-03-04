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
import json
from packaging import version
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageTk
from pathlib import Path
from CTkMessagebox import CTkMessagebox

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
APP_NAME = "Xtreme ADB V2.0"
LOG_FILE = "xtreme_log.txt"
CURRENT_VERSION = "2.0"
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
    CONFIG_FILE.parent.mkdir(exist_ok=True)
else:
    CONFIG_FILE = Path("xtreme_config.json")

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
        self.label = ctk.CTkLabel(self, text="0%", font=("Segoe UI", 18, "bold"), text_color=C["text_main"])
        self.label.place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 12), text_color=C["text_sub"]).pack(pady=5)
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
        ctk.CTkLabel(header, text="> Terminal Output", font=("Consolas", 11, "bold"), text_color=C["text_sub"]).pack(side="left")
        ctk.CTkButton(header, text="Clear", width=50, height=20, fg_color=C["input_bg"], text_color=C["text_main"],
                      font=("Segoe UI", 10), command=self.clear).pack(side="right")

        # Text Area
        self.text_area = ctk.CTkTextbox(
            self,
            font=("Consolas", 12),
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
# 4. BACKEND ENGINE
# ==========================================
class Backend:
    @staticmethod
    def run(cmd, timeout=10):
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            res = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                startupinfo=startupinfo, timeout=timeout
            )
            return res.stdout.strip() + res.stderr.strip()
        except Exception as e:
            return f"[ERROR] {str(e)}"

    @staticmethod
    def run_live(cmd, callback):
        """Run command and stream output to callback function"""
        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", startupinfo=startupinfo
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

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.init_ui()
        splash.destroy() # Stop showing the splash screen
        if os.name == "nt":
            self.after(0, lambda: self.state('zoomed'))  # Windows
        else:
            self.after(0, lambda: self.state('normal'))  # Linux / macOS / WSL (Setting as Normal Because There is no Full Screen)

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
        """Check for updates after UI is loaded"""
        if not CONF["check_updates"]:
            return

        has_update, new_ver, url = check_for_updates()
        if has_update:
            msg = CTkMessagebox(
                title="Update Available",
                message=f"A update is available (v{new_ver}) !\n\nWould you like to download it?",
                icon="info",
                option_1="Download",
                option_2="Remind me later",
                option_3="Never remind"
            )
            # Manually color the buttons after creation
            msg.button_1.configure(fg_color="green", hover_color="darkgreen")
            msg.button_2.configure(fg_color="orange", hover_color="darkorange")
            msg.button_3.configure(fg_color="red", hover_color="darkred")

            response = msg.get()
            if response == "Download":
                import webbrowser
                webbrowser.open(url)
            elif response == "Never remind":
                save_config("check_updates", False)



    def run_bg(self, func):
        threading.Thread(target=func, daemon=True).start()

    def init_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=90, corner_radius=0, fg_color=C["bg_sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="XA", font=("Segoe UI", 28, "bold"), text_color=C["primary"]).pack(pady=(30, 20))

        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(fill="x", pady=10)

        items = [
            ("🏠", "Dashboard", self.view_dash),
            ("📱", "Screen", self.view_screen),
            ("📦", "Apps", self.view_apps),
            ("📁", "Files", self.view_files),
            (">_", "Shell", self.view_shell),
            ("LC", "Logcat", self.view_logcat),
            ("🔌", "Wireless", self.view_wireless),
            ("⚡", "Fastboot", self.view_fastboot),
            ("🔧", "Tweaks", self.view_tweaks),
            ("🔄", "Backup", self.view_backup),
            ("📲", "Devices", self.view_devices),
            ("⚙️", "Settings", self.view_settings),
        ]

        for icon, name, cmd in items:
            btn = FluentButton(
                self.nav_frame, text=icon, width=50, height=50, corner_radius=10,
                font=("Segoe UI", 22), command=cmd, fg_color="transparent", text_color=C["text_sub"]
            )
            btn.pack(pady=5, padx=10)
            self.nav_buttons[name] = btn

        self.status_dot = ctk.CTkLabel(self.sidebar, text="●", font=("Arial", 24), text_color=C["danger"])
        self.status_dot.pack(side="bottom", pady=(0, 20))
        self.status_lbl = ctk.CTkLabel(self.sidebar, text="None", font=("Segoe UI", 10), text_color="gray")
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
        for k, btn in self.nav_buttons.items():
            btn.set_active(k == name)

    def clear(self):
        if self.log_proc:
            self.log_proc = False # Signal to stop loops
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
                        self.after(0, lambda s=serials_str: CTkMessagebox(
                            title="Unauthorized or Offline Device Detected",
                            message=f"Device(s) [{s}] are not ready.\n\nMake sure your phone screen is unlocked and tap 'Allow' on the USB debugging authorization prompt. If you already did, try unplugging and replugging the cable.",
                            icon="warning",
                            option_1="Ok"
                        ))
                    # If a serial is no longer problem, remove from warned so it can warn again if replugged
                    self._warned_serials &= problem                    
                    if devices:
                        if self.sel_dev not in devices:
                            if len(devices) == 1:
                                self.sel_dev = devices[0]
                            elif devices != self._last_device_list:
                                self.after(0, lambda d=devices: self.prompt_device_select(d))
                        if devices != self._last_device_list:
                            self.after(0, self._on_device_list_changed)
                        self._last_device_list = devices
                        sel = self.sel_dev
                        self.after(0, lambda: self.status_dot.configure(text_color=C["success"]))
                        self.after(0, lambda s=sel: self.status_lbl.configure(text=s.split()[0] if s else "Ready"))
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

        msg = f"⚠  Multiple devices detected — Please select one in the Devices menu.\nCurrently active: {friendly}"
        ctk.CTkLabel(banner, text=msg, text_color="#FFD966",
                     font=("Segoe UI", 12), justify="left").pack(side="left", padx=15, pady=10)

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

        ctk.CTkLabel(self.main, text="Dashboard", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 10))

        # Info Row
        info_frame = ctk.CTkFrame(self.main, fg_color="transparent")
        info_frame.pack(fill="x", pady=(0, 20))
        self.lbl_model = ctk.CTkLabel(info_frame, text="Model: ...", font=("Segoe UI", 14), text_color=C["text_sub"])
        self.lbl_model.pack(side="left", padx=10)
        self.lbl_android = ctk.CTkLabel(info_frame, text="Android: ...", font=("Segoe UI", 14), text_color=C["text_sub"])
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
        ctk.CTkLabel(self.main, text="Power Controls", font=("Segoe UI", 18, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(30, 10))
        pg = ctk.CTkFrame(self.main, fg_color="transparent")
        pg.pack(fill="x")
        btns = [("Reboot System", ["reboot"], C["primary"]), ("Recovery", ["reboot", "recovery"], C["warning"]),
                ("Bootloader", ["reboot", "bootloader"], C["warning"]), ("Power Off", ["reboot", "-p"], C["danger"])]

        button_text_color = "#000000" if ctk.get_appearance_mode() == "Light" else "#FFFFFF" ## Fix For Issue 1

        for label, cmd, color in btns:
            ctk.CTkButton(pg, text=label, text_color=button_text_color, fg_color=color, height=50, corner_radius=8, font=("Segoe UI", 14, "bold"),
                          command=lambda x=cmd: self.adb_cmd_console(x)).pack(side="left", fill="x", expand=True, padx=5)

        # Console
        ctk.CTkLabel(self.main, text="Activity Log", font=("Segoe UI", 14, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(20, 5))
        self.dash_console = LogConsole(self.main, height=200)
        self.dash_console.pack(fill="x", pady=(0, 20))

    # --- SCREEN TOOLS ---
    def view_screen(self):
        self.clear()
        self.highlight("Screen")
        ctk.CTkLabel(self.main, text="Screen Tools", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        grid = ctk.CTkFrame(self.main, fg_color="transparent")
        grid.pack(fill="x", pady=10)

        # Scrcpy
        c1 = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=10)
        c1.pack(side="left", fill="both", expand=True, padx=5, ipady=10)
        ctk.CTkLabel(c1, text="Mirroring", font=("Segoe UI", 16, "bold")).pack(pady=10)
        ctk.CTkButton(c1, text="Launch Scrcpy", fg_color=C["primary"], command=self.launch_scrcpy).pack(pady=10)

        # Screenshot
        c2 = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=10)
        c2.pack(side="left", fill="both", expand=True, padx=5, ipady=10)
        ctk.CTkLabel(c2, text="Capture", font=("Segoe UI", 16, "bold")).pack(pady=10)
        ctk.CTkButton(c2, text="Take Screenshot", fg_color=C["success"], command=self.take_screenshot).pack(pady=10)

        # Record
        c3 = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=10)
        c3.pack(side="left", fill="both", expand=True, padx=5, ipady=10)
        ctk.CTkLabel(c3, text="Recording", font=("Segoe UI", 16, "bold")).pack(pady=10)
        self.rec_btn = ctk.CTkButton(c3, text="Start Record (10s)", fg_color=C["danger"], command=self.record_screen)
        self.rec_btn.pack(pady=10)

        self.screen_console = LogConsole(self.main, height=300)
        self.screen_console.pack(fill="both", expand=True, pady=20)

    def launch_scrcpy(self):
        if not self.sel_dev: return
        self.screen_console.log("Launching Scrcpy...")
        clean = self.sel_dev.split()[0]
        def _run():
            try:
                subprocess.Popen([SCRCPY_PATH, "-s", clean] + CONF["scrcpy_args"].split())
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
        ctk.CTkLabel(self.main, text="App Manager", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(
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
        ctk.CTkLabel(sort_bar, text="Sort:", font=("Segoe UI", 11), text_color=C["text_sub"]).pack(side="left",
                                                                                                   padx=(5, 8))
        self._app_sort = ctk.StringVar(value=CONF.get("app_sort", "a_z"))
        for label, val in [("A→Z", "a_z"), ("Z→A", "z_a")]:
            ctk.CTkRadioButton(sort_bar, text=label, variable=self._app_sort, value=val,
                               font=("Segoe UI", 11), text_color=C["text_sub"],
                               command=self._on_app_sort_change).pack(side="left", padx=6)

        split = ctk.CTkFrame(self.main, fg_color="transparent")
        split.pack(fill="both", expand=True)
        self.app_list = ctk.CTkScrollableFrame(split, fg_color=C["bg_surface"], corner_radius=15)
        self.app_list.pack(side="left", fill="both", expand=True, padx=(0, 10))

        act = ctk.CTkFrame(split, width=250, fg_color=C["bg_surface"], corner_radius=15)
        act.pack(side="right", fill="y")
        ctk.CTkLabel(act, text="Actions", font=("Segoe UI", 14, "bold"), text_color=C["text_main"]).pack(pady=(20, 5))
        self.lbl_pkg = ctk.CTkLabel(act, text="None selected", text_color="gray", wraplength=200, font=("Segoe UI", 11))
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

        self.all_apps = []
        self.load_apps()

    def load_apps(self):
        if not self.sel_dev: return
        cln = self.sel_dev.split()[0]
        for w in self.app_list.winfo_children(): w.destroy()
        self.app_console.log("Loading packages...")

        def _t():
            raw = self.bk.run([ADB_PATH, "-s", cln, "shell", "pm", "list", "packages", "-3"])
            self.all_apps = sorted([x.replace("package:", "").strip() for x in raw.split("\n") if x.strip()])
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
        for p in pkgs:
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
        self.app_console.log(f"Loaded {total} apps (showing {len(pkgs)}).")

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
        if not messagebox.askyesno("Force Uninstall",
                                   f"Force uninstall {len(pkgs)} package(s)?\nThis uses -k --user 0 and works on system apps."):
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
        if not self.sel_pkgs:
            self.app_console.log("[ERROR] No packages selected.")
            return
        d = filedialog.askdirectory()
        if not d:
            return
        pkgs = self.sel_pkgs.copy()
        cln = self.sel_dev.split()[0]

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
                self.app_console.log(f"✓ {pkg} → {pkg_dir}")
            self.app_console.log("Extraction complete.")

        self.run_bg(_t)

    # --- FILES ---
    def view_files(self):
        self.clear()
        self.highlight("Files")
        ctk.CTkLabel(self.main, text="File Explorer", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

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
        ctk.CTkLabel(fsort_bar, text="Sort:", font=("Segoe UI", 11), text_color=C["text_sub"]).pack(side="left",
                                                                                                        padx=(5, 8))
        self._file_sort = ctk.StringVar(value=CONF.get("file_sort", "a_z"))
        for label, val in [("A→Z", "a_z"), ("Z→A", "z_a"), ("Folders first", "folders_first"),
                            ("Files first", "files_first")]:
            ctk.CTkRadioButton(fsort_bar, text=label, variable=self._file_sort, value=val,
                                font=("Segoe UI", 11), text_color=C["text_sub"],
                                command=self._on_file_sort_change).pack(side="left", padx=6)

        self.fm_list = ctk.CTkScrollableFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        self.fm_list.pack(fill="both", expand=True)
        self.fm_sel = None
        self.fm_selected = []  # Track multiple selections
        self.ctrl_pressed = False  # Track Ctrl key
        self.fm_ent.insert(0, self.cur_path)

        self.fm_console = LogConsole(self.main, height=120)
        self.fm_console.pack(fill="x", pady=(10, 0))
        self.fm_load()

    def fm_load(self):
        if not self.sel_dev: return
        cln = self.sel_dev.split()[0]
        path = self.fm_ent.get()
        self.cur_path = path
        for w in self.fm_list.winfo_children(): w.destroy()
        self.file_buttons = []
        self.fm_console.log(f"Listing {path}...")

        def _t():
            out = self.bk.run([ADB_PATH, "-s", cln, "shell", f"ls {path}"])
            if "[ERROR]" in out or "No such file" in out:
                self.after(0, lambda: self.fm_console.log("Error reading directory."))
                return
            items = [x.strip() for x in out.split("\n") if x.strip()]

            if not items:
                self.after(0, lambda: self.fm_console.log("Directory is empty."))
                return

            items_with_type = []
            folder_count = 0
            file_count = 0

            for item in items:
                test_cmd = f"[ -d '{path.rstrip('/')}/{item}' ] && echo DIR || echo FILE"
                result = self.bk.run([ADB_PATH, "-s", cln, "shell", test_cmd]).strip()
                is_dir = "DIR" in result
                display_name = f"{item}/" if is_dir else item
                items_with_type.append(display_name)

                if is_dir:
                    folder_count += 1
                else:
                    file_count += 1

            self.after(0, lambda: self._populate_file_list(items_with_type))
            self.after(0, lambda: self.fm_console.log(f"Listed: {file_count} file(s), {folder_count} folder(s)"))

        self.run_bg(_t)

    def _populate_file_list(self, items):
        sort = self._file_sort.get() if hasattr(self, '_file_sort') else CONF.get("file_sort", "a_z")
        dirs = [i for i in items if i.endswith("/")]
        files = [i for i in items if not i.endswith("/")]
        if sort == "a_z":
            dirs.sort();
            files.sort()
            items = dirs + files
        elif sort == "z_a":
            dirs.sort(reverse=True);
            files.sort(reverse=True)
            items = dirs + files
        elif sort == "folders_first":
            dirs.sort();
            files.sort()
            items = dirs + files
        elif sort == "files_first":
            files.sort();
            dirs.sort()
            items = files + dirs

        for item in items:
            is_dir = item.endswith("/")
            col = C["primary"] if is_dir else C["text_main"]
            icon = "📁" if is_dir else "📄"
            btn = ctk.CTkButton(
                self.fm_list,
                text=f"{icon}  {item}",
                anchor="w",
                fg_color="transparent",
                hover_color=C["bg_hover"],
                text_color=col,
                command=lambda n=item: self.fm_click_item(n)
            )
            btn.pack(fill="x")
            if is_dir:
                btn.bind("<Double-Button-1>", lambda e, x=item: self.fm_ent_dir(x))
            btn.bind("<Button-3>", lambda e, name=item: self.show_file_context_menu(e, name))
            self.file_buttons.append((btn, item))

    def _on_file_sort_change(self):
        save_config("file_sort", self._file_sort.get())
        global CONF
        CONF = load_config()
        self.fm_load()

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

    def fm_mkdir(self):
        dlg = ctk.CTkInputDialog(text="Folder name:", title="New Folder")
        name = dlg.get_input()
        if name:
            self.adb_cmd_console(["shell", "mkdir", "-p", f'"{self.cur_path.rstrip("/")}/{name}"'])
            self.after(500, self.fm_load)

    def fm_del(self):
        if self.fm_sel and messagebox.askyesno("Confirm", f"Delete {self.fm_sel}?"):
            self.adb_cmd_console(["shell", "rm", "-rf", f'"{self.cur_path.rstrip("/")}/{self.fm_sel}"'])
            self.after(500, self.fm_load)

    def fm_del_multiple(self):
        if not self.fm_selected:
            return
        if messagebox.askyesno("Confirm", f"Delete {len(self.fm_selected)} items?"):
            if not self.sel_dev: return
            cln = self.sel_dev.split()[0]
            for name in self.fm_selected:
                path = f"{self.cur_path.rstrip('/')}/{name.rstrip('/')}"
                self.fm_console.log(f"Deleting {name}...")
                self.bk.run([ADB_PATH, "-s", cln, "shell", "rm", "-rf", f'"{path}"'])
            self.fm_selected = []
            self.after(500, self.fm_load)

    def fm_ren(self):
        if not self.fm_sel: return
        dlg = ctk.CTkInputDialog(text="New name:", title="Rename")
        new_name = dlg.get_input()
        if new_name:
            old = f'"{self.cur_path.rstrip("/")}/{self.fm_sel}"'
            new = f'"{self.cur_path.rstrip("/")}/{new_name}"'
            self.adb_cmd_console(["shell", "mv", old, new])
            self.after(500, self.fm_load)

    def fm_upload(self):
        files = filedialog.askopenfilenames()
        if files:
            for f in files: self.adb_cmd_console(["push", f, self.cur_path.rstrip("/") + "/"])
            self.after(1000, self.fm_load)

    def fm_download_single(self, name):
        if not self.sel_dev: return
        cln = self.sel_dev.split()[0]
        d = filedialog.askdirectory(title="Save to")
        if d:
            src = f"{self.cur_path.rstrip('/')}/{name.rstrip('/')}"
            self.fm_console.log(f"Downloading {name}...")
            # Use pull with recursive flag for folders
            self.bk.run_live([ADB_PATH, "-s", cln, "pull", src, d], lambda l: self.fm_console.log(l))

    def fm_download_multiple(self):
        if not self.fm_selected:
            return
        if not self.sel_dev: return
        cln = self.sel_dev.split()[0]
        d = filedialog.askdirectory(title="Save to")
        if d:
            for name in self.fm_selected:
                src = f"{self.cur_path.rstrip('/')}/{name.rstrip('/')}"
                self.fm_console.log(f"Downloading {name}...")
                self.bk.run_live([ADB_PATH, "-s", cln, "pull", src, d], lambda l: self.fm_console.log(l))
            self.fm_selected = []

    # --- SHELL ---
    def view_shell(self):
        self.clear()
        self.highlight("Shell")
        ctk.CTkLabel(self.main, text="ADB Shell Terminal", font=("Segoe UI", 36, "bold"),
                     text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        terminal_container = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        terminal_container.pack(fill="both", expand=True)

        header = ctk.CTkFrame(terminal_container, height=35, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text="> ADB Shell", font=("Consolas", 12, "bold"), text_color=C["text_sub"]).pack(side="left")
        ctk.CTkButton(header, text="Clear", width=60, height=25, fg_color=C["input_bg"], text_color=C["text_main"],
                      font=("Segoe UI", 10), command=self.clear_terminal).pack(side="right", padx=5)

        # Output box (read-only)
        self.shell_output = ctk.CTkTextbox(
            terminal_container,
            font=("Consolas", 12),
            fg_color=C["term_bg"],
            text_color=C["term_fg"],
            activate_scrollbars=True
        )
        self.shell_output.pack(fill="both", expand=True, padx=10, pady=(0, 5))
        self.shell_output.configure(state="disabled")

        # Input box
        input_frame = ctk.CTkFrame(terminal_container, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(input_frame, text="$", font=("Consolas", 14, "bold"), text_color=C["success"]).pack(side="left", padx=(5, 5))

        self.shell_input = ctk.CTkEntry(
            input_frame,
            font=("Consolas", 12),
            fg_color=C["input_bg"],
            border_width=0,
            text_color=C["text_main"]
        )
        self.shell_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.shell_input.bind("<Return>", self.execute_shell_command)
        self.shell_input.focus()

        ctk.CTkButton(
            input_frame,
            text="Run",
            width=60,
            fg_color=C["primary"],
            command=lambda: self.execute_shell_command(None)
        ).pack(side="right")

        # Start persistent shell
        self.shell_proc = None
        if self.sel_dev:
            self.run_bg(self.start_shell_session)

    def start_shell_session(self):
        """Start background shell process"""
        if not self.sel_dev:
            return

        clean = self.sel_dev.split()[0]

        try:
            # Start interactive shell with unbuffered output
            self.shell_proc = subprocess.Popen(
                [ADB_PATH, "-s", clean, "shell"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0
            )

            self.after(0, lambda: self.append_shell_output("Shell connected. Type commands below.\n"))
        except Exception as e:
            self.after(0, lambda: self.append_shell_output(f"Error: {e}\n"))

    def clear_terminal(self):
        self.shell_output.configure(state="normal")
        self.shell_output.delete("1.0", "end")
        self.shell_output.configure(state="disabled")

    def append_shell_output(self, text):
        self.shell_output.configure(state="normal")
        self.shell_output.insert("end", text)
        self.shell_output.see("end")
        self.shell_output.configure(state="disabled")

    def execute_shell_command(self, event):
        cmd = self.shell_input.get().strip()

        if not cmd:
            return "break" if event else None

        # Clear input
        self.shell_input.delete(0, "end")

        # Show command in output
        self.append_shell_output(f"$ {cmd}\n")

        if cmd == "clear":
            self.clear_terminal()
            return "break" if event else None

        if cmd == "exit":
            if self.shell_proc:
                self.shell_proc.terminate()
                self.shell_proc = None
            self.append_shell_output("Shell closed.\n")
            return "break" if event else None

        if not self.shell_proc or self.shell_proc.poll() is not None:
            self.append_shell_output("[ERROR] Shell not connected\n")
            return "break" if event else None

        def _run():
            try:
                # Send command
                self.shell_proc.stdin.write(f"{cmd}\n")
                self.shell_proc.stdin.flush()

                # Send end marker
                marker = f"__END_CMD_{time.time()}__"
                self.shell_proc.stdin.write(f"echo '{marker}'\n")
                self.shell_proc.stdin.flush()

                # Read until marker
                output_lines = []
                while True:
                    line = self.shell_proc.stdout.readline()
                    if not line or marker in line:
                        break
                    output_lines.append(line)

                # Show output
                output = ''.join(output_lines)
                if output.strip():
                    self.after(0, lambda: self.append_shell_output(output))

            except Exception as e:
                self.after(0, lambda: self.append_shell_output(f"Error: {e}\n"))

        self.run_bg(_run)
        return "break" if event else None

    # --- LOGCAT ---
    def view_logcat(self):
        self.clear()
        self.highlight("Logcat")
        ctk.CTkLabel(self.main, text="Live Logcat", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(
            anchor="w", pady=(10, 20))

        bar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        self.btn_log_start = ctk.CTkButton(bar, text="Start", fg_color=C["success"], command=self.start_logcat)
        self.btn_log_start.pack(side="left", padx=5)
        ctk.CTkButton(bar, text="Stop", fg_color=C["danger"], command=self.stop_logcat).pack(side="left", padx=5)
        ctk.CTkButton(bar, text="Save Log", fg_color=C["primary"], command=self.save_logcat).pack(side="left", padx=5)

        self.logcat_console = LogConsole(self.main, height=500)
        self.logcat_console.pack(fill="both", expand=True)

    def start_logcat(self):
        if not self.sel_dev: return
        self.log_proc = True
        self.btn_log_start.configure(state="disabled")
        clean = self.sel_dev.split()[0]
        def _loop():
            # Using Popen to stream
            _si = {}
            if os.name == "nt":
                _startupinfo = subprocess.STARTUPINFO()
                _startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                _si["startupinfo"] = _startupinfo
            proc = subprocess.Popen([ADB_PATH, "-s", clean, "logcat", "-v", "time"],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace", **_si)
            while self.log_proc:
                line = proc.stdout.readline()
                if line: self.logcat_console.log(line.strip())
                else: break
            proc.terminate()
        self.run_bg(_loop)

    def stop_logcat(self):
        self.log_proc = False
        self.btn_log_start.configure(state="normal")

    def save_logcat(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile="logcat_output.txt"
        )
        if f:
            with open(f, "w", encoding="utf-8") as file:
                file.write(self.logcat_console.text_area.get("1.0", "end"))

    # --- FASTBOOT ---
    def view_fastboot(self):
        self.clear()
        self.highlight("Fastboot")
        ctk.CTkLabel(self.main, text="Fastboot Tools", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(
            anchor="w", pady=(10, 20))

        warn = ctk.CTkFrame(self.main, fg_color="#4a1010", corner_radius=10, border_width=1, border_color=C["danger"])
        warn.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(warn, text="⚠️ ADVANCED: Use with caution.", text_color="#FF9999").pack(pady=10)

        self.fb_card("Bootloader",
                     [("Check Info", C["primary"], ["getvar", "all"]), ("Unlock OEM", C["danger"], ["oem", "unlock"])])

        # --- Custom Flash Card ---
        flash_card = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        flash_card.pack(fill="x", pady=10, ipady=10)
        ctk.CTkLabel(flash_card, text="Flash Partition", font=("Segoe UI", 16, "bold"), text_color=C["text_main"]).pack(
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
        ctk.CTkLabel(ab_row, text="Slot:", text_color=C["text_sub"], font=("Segoe UI", 12)).pack(side="left",
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

    def fb_card(self, title, actions):
        f = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        f.pack(fill="x", pady=10, ipady=10)
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 16, "bold"), text_color=C["text_main"]).pack(side="left", padx=20)
        for item in actions:
            label, col = item[0], item[1]
            func = item[3] if len(item) > 3 and item[3] else lambda c=item[2]: self.fb_run(c)
            ctk.CTkButton(f, text=label, fg_color=col, width=120, command=func).pack(side="right", padx=10)

    def fb_run(self, cmd):
        if not self.sel_dev: return
        clean = self.sel_dev.split()[0]
        self.fb_console.log(f"Fastboot: {' '.join(cmd)}")

        def _run():
            self.bk.run_live([FASTBOOT_PATH, "-s", clean] + cmd, lambda l: self.fb_console.log(l))

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
                CTkMessagebox(title="Error", message="Please enter a partition name.", icon="warning")
                return

        slot = self._fb_slot.get()
        partition = base_partition + ("" if slot == "none" else slot)

        f = filedialog.askopenfilename(filetypes=[("IMG files", "*.img")])
        if f and messagebox.askyesno("Confirm Flash", f"Flash '{partition}' with:\n{f}\n\nAre you sure?"):
            self.fb_run(["flash", partition, f])

    # --- WIRELESS ---
    def view_wireless(self):
        self.clear()
        self.highlight("Wireless")
        ctk.CTkLabel(self.main, text="Wireless ADB", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        # Step 1 - TCP/IP
        c1 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c1.pack(fill="x", pady=10)
        ctk.CTkLabel(c1, text="1. Enable TCP/IP Mode", font=("Segoe UI", 14, "bold")).pack(side="left", padx=20, pady=20)
        ctk.CTkButton(c1, text="Enable (5555)", fg_color=C["primary"], command=lambda: self.adb_cmd_console(["tcpip", "5555"])).pack(side="right", padx=20)

        # Step 2 - Pair (Android 11+)
        c_pair = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c_pair.pack(fill="x", pady=10)
        ctk.CTkLabel(c_pair, text="2. Pair Device (Android 11+)", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(c_pair, text="Go to Developer Options → Wireless debugging → Pair with pairing code",
                     font=("Segoe UI", 11), text_color=C["text_sub"]).pack(anchor="w", padx=20, pady=(0, 8))
        r_pair = ctk.CTkFrame(c_pair, fg_color="transparent")
        r_pair.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_pair_ip = ctk.CTkEntry(r_pair, placeholder_text="IP:PAIR_PORT", height=40, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_pair_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.ent_pair_code = ctk.CTkEntry(r_pair, placeholder_text="6-digit code", height=40, width=130, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_pair_code.pack(side="left", padx=(0, 10))
        ctk.CTkButton(r_pair, text="Pair", height=40, fg_color=C["warning"], command=self.do_wireless_pair).pack(side="right")

        # Step 3 - Connect
        c2 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c2.pack(fill="x", pady=10)
        ctk.CTkLabel(c2, text="3. Connect", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        r = ctk.CTkFrame(c2, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_ip = ctk.CTkEntry(r, placeholder_text="IP:PORT", height=40, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        if CONF.get("last_ip"): self.ent_ip.insert(0, CONF["last_ip"])
        ctk.CTkButton(r, text="Connect", height=40, fg_color=C["success"], command=self.do_wireless_connect).pack(side="right")

        # Step 4 - Disconnect
        c3 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c3.pack(fill="x", pady=10)
        ctk.CTkLabel(c3, text="4. Disconnect", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkButton(c3, text="Disconnect All", height=40, fg_color=C["danger"], command=self.do_wireless_disconnect_all).pack(fill="x", padx=20, pady=(0, 10))
        r_disc = ctk.CTkFrame(c3, fg_color="transparent")
        r_disc.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_disc_ip = ctk.CTkEntry(r_disc, placeholder_text="IP:PORT", height=40, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_disc_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(r_disc, text="Disconnect", height=40, fg_color=C["danger"], command=self.do_wireless_disconnect).pack(side="right")

        self.wireless_console = LogConsole(self.main, height=200)
        self.wireless_console.pack(fill="x", pady=20)

    def do_wireless_connect(self):
        ip = self.ent_ip.get().strip()
        if not ip:
            self.wireless_console.log("[ERROR] Please enter an IP:PORT.")
            return
        save_config("last_ip", ip)
        self.wireless_console.log(f"Connecting to {ip}...")
        self._pause_dev_loop = True
        def _connect():
            try:
                result = self.bk.run([ADB_PATH, "connect", ip], timeout=30)
                self.wireless_console.log(result)
            finally:
                self._pause_dev_loop = False
        self.run_bg(_connect)

    def do_wireless_pair(self):
        ip = self.ent_pair_ip.get().strip()
        code = self.ent_pair_code.get().strip()
        if not ip or not code:
            self.wireless_console.log("[ERROR] Please enter both IP:PORT and the pairing code.")
            return
        self.wireless_console.log(f"Pairing with {ip}...")
        def _pair():
            self.bk.run_live([ADB_PATH, "pair", ip, code], lambda l: self.wireless_console.log(l))
        self.run_bg(_pair)

    def do_wireless_disconnect_all(self):
        self.adb_cmd_console(["disconnect"])
        self.wireless_console.log("All wireless connections disconnected!")

    def do_wireless_disconnect(self):
        target = self.ent_disc_ip.get().strip()
        if not target:
            self.wireless_console.log("[ERROR] Please enter an IP:PORT to disconnect from!")
            return
        self.adb_cmd_console(["disconnect", target])
        self.wireless_console.log(f"Disconnecting from {target}...")

    # --- TWEAKS ---
    def view_tweaks(self):
        self.clear()
        self.highlight("Tweaks")
        ctk.CTkLabel(self.main, text="System Tweaks", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        scroll = ctk.CTkScrollableFrame(self.main, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # Toggles
        f = ctk.CTkFrame(scroll, fg_color=C["bg_surface"], corner_radius=15)
        f.pack(fill="x", pady=10)
        tweaks = [("Show Taps", "system", "show_touches"), ("Pointer Location", "system", "pointer_location"), ("Stay Awake (USB)", "global", "stay_on_while_plugged_in")]
        for label, ns, key in tweaks:
            r = ctk.CTkFrame(f, fg_color="transparent")
            r.pack(fill="x", pady=8, padx=10)
            ctk.CTkLabel(r, text=label, text_color=C["text_main"], font=("Segoe UI", 13)).pack(side="left", padx=20)
            ctk.CTkButton(r, text="ON", width=60, fg_color=C["success"], command=lambda nn=ns, kk=key: self.adb_cmd_console(["shell", "settings", "put", nn, kk, "1"])).pack(side="right", padx=5)
            ctk.CTkButton(r, text="OFF", width=60, fg_color="#333", command=lambda nn=ns, kk=key: self.adb_cmd_console(["shell", "settings", "put", nn, kk, "0"])).pack(side="right", padx=5)

        # DPI
        f2 = ctk.CTkFrame(scroll, fg_color=C["bg_surface"], corner_radius=15)
        f2.pack(fill="x", pady=10)
        ctk.CTkLabel(f2, text="DPI Changer", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=10)
        r2 = ctk.CTkFrame(f2, fg_color="transparent")
        r2.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_dpi = ctk.CTkEntry(r2, placeholder_text="e.g. 400", width=100)
        self.ent_dpi.pack(side="left", padx=5)
        ctk.CTkButton(r2, text="Apply", width=80, command=lambda: self.adb_cmd_console(["shell", "wm", "density", self.ent_dpi.get()])).pack(side="left", padx=5)
        ctk.CTkButton(r2, text="Reset", width=80, fg_color="#333", command=lambda: self.adb_cmd_console(["shell", "wm", "density", "reset"])).pack(side="left", padx=5)

        # Animation
        f3 = ctk.CTkFrame(scroll, fg_color=C["bg_surface"], corner_radius=15)
        f3.pack(fill="x", pady=10)
        ctk.CTkLabel(f3, text="Animation Scale", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=10)
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
        ctk.CTkLabel(self.main, text="Backup & Restore", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        grid = ctk.CTkFrame(self.main, fg_color="transparent")
        grid.pack(fill="x", padx=30)
        b_card = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=15)
        b_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(b_card, text="Backup Device", font=("Segoe UI", 18, "bold")).pack(pady=20)
        ctk.CTkButton(b_card, text="Start Backup", height=50, fg_color=C["primary"], command=self.do_backup).pack(pady=20, padx=20)

        r_card = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=15)
        r_card.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(r_card, text="Restore Device", font=("Segoe UI", 18, "bold")).pack(pady=20)
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
        ctk.CTkLabel(self.main, text="Device Manager", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))

        info_card = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        info_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(info_card, text="Active Device", font=("Segoe UI", 14, "bold"), text_color=C["text_main"]).pack(anchor="w", padx=20, pady=(15, 5))
        self.dev_active_lbl = ctk.CTkLabel(info_card, text=self.sel_dev or "None",
                                           font=("Segoe UI", 13), text_color=C["primary"])
        self.dev_active_lbl.pack(anchor="w", padx=20, pady=(0, 15))

        list_card = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        list_card.pack(fill="x", pady=(0, 15))
        top = ctk.CTkFrame(list_card, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(top, text="Connected Devices", font=("Segoe UI", 14, "bold"), text_color=C["text_main"]).pack(side="left")
        ctk.CTkButton(top, text="↻", width=32, height=32, font=("Segoe UI", 18),
                      fg_color="transparent", hover_color=C["bg_hover"],
                      text_color=C["text_sub"], command=self._refresh_device_list).pack(side="right", padx=(0, 5))

        self.dev_list_frame = ctk.CTkScrollableFrame(list_card, fg_color="transparent", height=200)
        self.dev_list_frame.pack(fill="x", padx=20, pady=(0, 15))
        self._refresh_device_list()

        self.dev_console = LogConsole(self.main, height=150)
        self.dev_console.pack(fill="x", pady=10)

    def _refresh_device_list(self):
        for w in self.dev_list_frame.winfo_children():
            w.destroy()

        devices = self.bk.get_devices()
        if not devices:
            ctk.CTkLabel(self.dev_list_frame, text="No devices found.",
                         text_color=C["text_sub"], font=("Segoe UI", 12)).pack(pady=10)
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
                font=("Segoe UI", 12),
                fg_color=C["bg_hover"] if is_selected else "transparent",
                hover_color=C["bg_hover"],
                text_color=C["success"] if is_selected else C["text_main"],
                command=lambda d=dev: self._select_device(d)
            )
            row.pack(fill="x", pady=2)

    def _select_device(self, dev):
        self.sel_dev = dev
        if hasattr(self, 'dev_active_lbl') and self.dev_active_lbl.winfo_exists():
            self.dev_active_lbl.configure(text=dev)
        self.status_lbl.configure(text=dev.split()[0])
        self.status_dot.configure(text_color=C["success"])
        self._refresh_device_list()
        if hasattr(self, 'dev_console'):
            self.dev_console.log(f"Switched to {dev}")

    # --- SETTINGS ---
    def view_settings(self):
        self.clear()
        self.highlight("Settings")
        ctk.CTkLabel(self.main, text="Settings", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(
            anchor="w", pady=(10, 20))

        c = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(c, text="Appearance", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
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
        ctk.CTkLabel(c2, text="Advanced", font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(20, 10))

        # ADB Path picker
        adb_row = ctk.CTkFrame(c2, fg_color="transparent")
        adb_row.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(adb_row, text="ADB Executable Path", text_color=C["text_main"], font=("Segoe UI", 13)).pack(
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
        ctk.CTkLabel(su_row, text="Use Super User (Root)", text_color=C["text_main"], font=("Segoe UI", 13)).pack(
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
                     font=("Segoe UI", 13)).pack(side="left", padx=20)

        self.refresh_label = ctk.CTkLabel(refresh_row, text=f"{CONF.get('refresh_interval', 3)}s",
                                          text_color=C["primary"], font=("Segoe UI", 13, "bold"))
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
                     font=("Segoe UI", 13)).pack(side="left", padx=20)

        self.poll_label = ctk.CTkLabel(poll_row, text=f"{CONF.get('device_poll_interval', 2)}s",
                                       text_color=C["primary"], font=("Segoe UI", 13, "bold"))
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
        CTkMessagebox(title="Saved", message=f"ADB path updated!\nNow using: {ADB_PATH}", icon="check", option_1="Ok")

if __name__ == "__main__":
    app = XtremeADB()
    app.mainloop()
