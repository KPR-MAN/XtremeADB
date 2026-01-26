import customtkinter as ctk
import subprocess
import threading
import os
import time
import re
import json
import datetime
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageTk
import sys

if getattr(sys, "frozen", False):
    import pyi_splash
else:
    pyi_splash = None


# ==========================================
# 1. CORE CONFIGURATION
# ==========================================
APP_NAME = "Xtreme ADB V1.2"
CONFIG_FILE = "xtreme_config.json"
LOG_FILE = "xtreme_log.txt"

DEFAULT_CONFIG = {
    "theme": "Dark",
    "last_ip": "",
    "auto_refresh": True,
    "refresh_interval": 3,
    "check_updates": True,
    "scrcpy_args": "--max-size 1024 --video-bit-rate 8M",
    "use_su": False
}

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
        try:
            out = self.run([ADB_PATH, "devices"], timeout=2)
            for line in out.split("\n"):
                if "\t" in line and "device" in line:
                    devices.append(f"{line.split()[0]} (ADB)")
            
            out_fb = self.run([FASTBOOT_PATH, "devices"], timeout=2)
            for line in out_fb.split("\n"):
                if "\t" in line:
                    devices.append(f"{line.split()[0]} (FASTBOOT)")
        except: pass
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

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.init_ui()
        
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

        # Close PyInstaller splash when main window is ready
        if pyi_splash:
            self.after(500, pyi_splash.close)


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
        while True:
            try:
                devices = self.bk.get_devices()
                if devices:
                    if self.sel_dev not in devices:
                        self.sel_dev = devices[0]
                    self.status_dot.configure(text_color=C["success"])
                    self.status_lbl.configure(text="Ready")
                else:
                    self.sel_dev = None
                    self.status_dot.configure(text_color=C["danger"])
                    self.status_lbl.configure(text="None")
            except: pass
            time.sleep(2)

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
        ctk.CTkLabel(self.main, text="App Manager", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(
            anchor="w", pady=(10, 20))

        bar = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        bar.pack(fill="x", pady=(0, 10), ipady=5)
        self.app_search = ctk.CTkEntry(bar, placeholder_text="Search apps...", border_width=0, fg_color=C["input_bg"],
                                       height=40, text_color=C["text_main"])
        self.app_search.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.app_search.bind("<KeyRelease>", lambda e: self.filter_apps())
        ctk.CTkButton(bar, text="Refresh", fg_color=C["primary"], command=self.load_apps).pack(side="left", padx=5)
        ctk.CTkButton(bar, text="Install APK", fg_color=C["success"], command=self.install_apk).pack(side="left",
                                                                                                     padx=10)

        split = ctk.CTkFrame(self.main, fg_color="transparent")
        split.pack(fill="both", expand=True)
        self.app_list = ctk.CTkScrollableFrame(split, fg_color=C["bg_surface"], corner_radius=15)
        self.app_list.pack(side="left", fill="both", expand=True, padx=(0, 10))

        act = ctk.CTkFrame(split, width=250, fg_color=C["bg_surface"], corner_radius=15)
        act.pack(side="right", fill="y")
        ctk.CTkLabel(act, text="Selected App", font=("Segoe UI", 14, "bold"), text_color=C["text_main"]).pack(pady=20)
        self.lbl_pkg = ctk.CTkLabel(act, text="None", text_color="gray", wraplength=200)
        self.lbl_pkg.pack(pady=5)
        self.sel_pkg = None

        ctk.CTkButton(act, text="Uninstall", fg_color=C["danger"], command=self.do_uninst).pack(fill="x", padx=20,
                                                                                                pady=5)
        ctk.CTkButton(act, text="Force Stop", fg_color=C["warning"], command=self.do_force).pack(fill="x", padx=20,
                                                                                                 pady=5)
        ctk.CTkButton(act, text="Clear Data", fg_color="#555", command=self.do_clear).pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(act, text="Extract APK", fg_color=C["primary"], command=self.do_extract).pack(fill="x", padx=20,
                                                                                                    pady=5)

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
        self.after(0, lambda: self._populate_app_list(filtered, len(self.all_apps)))

    def _populate_app_list(self, pkgs, total):
        for w in self.app_list.winfo_children(): w.destroy()
        for p in pkgs:
            ctk.CTkButton(
                self.app_list,
                text=p,
                anchor="w",
                fg_color="transparent",
                hover_color=C["bg_hover"],
                text_color=C["text_main"],
                command=lambda x=p: self.set_app(x)
            ).pack(fill="x")
        self.app_console.log(f"Loaded {total} apps (showing {len(pkgs)}).")

    def set_app(self, p):
        self.sel_pkg = p
        self.lbl_pkg.configure(text=p)

    def install_apk(self):
        f = filedialog.askopenfilename(filetypes=[("APK", "*.apk")])
        if f: self.adb_cmd_console(["install", f], "Install Started")

    def do_uninst(self):
        if self.sel_pkg: 
            self.adb_cmd_console(["uninstall", self.sel_pkg])
            self.after(1000, self.load_apps)

    def do_force(self):
        if self.sel_pkg: self.adb_cmd_console(["shell", "am", "force-stop", self.sel_pkg])

    def do_clear(self):
        if self.sel_pkg: self.adb_cmd_console(["shell", "pm", "clear", self.sel_pkg])

    def do_extract(self):
        if not self.sel_pkg: return
        d = filedialog.askdirectory()
        if d:
            cln = self.sel_dev.split()[0]
            def _t():
                path_out = self.bk.run([ADB_PATH, "-s", cln, "shell", "pm", "path", self.sel_pkg])
                if "package:" in path_out:
                    apk_path = path_out.replace("package:", "").strip()
                    self.app_console.log(f"Pulling {apk_path}...")
                    self.bk.run_live([ADB_PATH, "-s", cln, "pull", apk_path, f"{d}/{self.sel_pkg}.apk"], lambda l: self.app_console.log(l))
                    self.app_console.log("Extraction Complete.")
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
        ops = [("New Folder", self.fm_mkdir), ("Delete", self.fm_del), ("Rename", self.fm_ren), ("Upload", self.fm_upload), ("Download", self.fm_download)]
        for label, cmd in ops:
            ctk.CTkButton(bar, text=label, width=80, fg_color=C["input_bg"], hover_color=C["bg_hover"], text_color=C["text_main"], command=cmd).pack(side="left", padx=5)
        
        self.fm_list = ctk.CTkScrollableFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        self.fm_list.pack(fill="both", expand=True)
        self.fm_sel = None
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
            out = self.bk.run([ADB_PATH, "-s", cln, "shell", "ls", "-1pH", f'"{path}"'])
            if "[ERROR]" in out:
                self.after(0, lambda: self.fm_console.log("Error reading directory."))
                return
            items = [x for x in out.split("\n") if x.strip()]
            self.after(0, lambda: self._populate_file_list(items))

        self.run_bg(_t)

    def _populate_file_list(self, items):
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
                command=lambda n=item: self.fm_select_item(n)
            )
            btn.pack(fill="x")
            if is_dir:
                btn.bind("<Double-Button-1>", lambda e, x=item: self.fm_ent_dir(x))
            self.file_buttons.append(btn)

    def fm_select_item(self, name):
        self.fm_sel = name
        for btn in self.file_buttons: btn.configure(fg_color="transparent")

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

    def fm_download(self):
        if not self.fm_sel: return
        save_path = filedialog.asksaveasfilename(initialfile=self.fm_sel)
        if save_path:
            remote = self.cur_path.rstrip("/") + "/" + self.fm_sel
            self.adb_cmd_console(["pull", remote, save_path])

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
        ctk.CTkLabel(header, text="> ADB Shell", font=("Consolas", 12, "bold"), text_color=C["text_sub"]).pack(
            side="left")
        ctk.CTkButton(header, text="Clear", width=60, height=25, fg_color=C["input_bg"], text_color=C["text_main"],
                      font=("Segoe UI", 10), command=self.clear_terminal).pack(side="right", padx=5)

        self.shell_output = ctk.CTkTextbox(
            terminal_container,
            font=("Consolas", 12),
            fg_color=C["term_bg"],
            text_color=C["term_fg"],
            activate_scrollbars=True
        )
        self.shell_output.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.shell_output.bind("<Key>", self.handle_terminal_input)
        self.shell_output.bind("<Return>", self.execute_terminal_command)
        self.shell_output.bind("<BackSpace>", self.handle_backspace)
        self.shell_output.bind("<Control-c>", self.handle_ctrl_c)
        self.shell_output.focus()

        self.shell_prompt = "$ "
        self.command_buffer = ""
        self.shell_running = False

        if self.sel_dev:
            self.run_bg(self.get_shell_prompt)

    def clear_terminal(self):
        self.shell_output.delete("1.0", "end")
        self.shell_output.insert("end", self.shell_prompt)
        self.prompt_index = self.shell_output.index("end-1c linestart")
        self.command_buffer = ""

    def get_shell_prompt(self):
        if not self.sel_dev: return
        clean = self.sel_dev.split()[0]

        whoami = self.bk.run([ADB_PATH, "-s", clean, "shell", "whoami"]).strip()
        hostname = self.bk.run([ADB_PATH, "-s", clean, "shell", "getprop", "ro.product.device"]).strip()

        if whoami == "root":
            self.shell_prompt = f"{hostname}:/ # "
        else:
            self.shell_prompt = f"{hostname}:/ $ "

        self.shell_output.insert("end", f"Connected to {hostname}\n")
        self.shell_output.insert("end", self.shell_prompt)
        self.shell_output.see("end")
        self.prompt_index = self.shell_output.index("end-1c linestart")

    def handle_terminal_input(self, event):
        if event.keysym in ["Return", "BackSpace", "Left", "Right", "Up", "Down"]:
            return

        if event.state & 0x4:
            return

        current_pos = self.shell_output.index("insert")
        if self.shell_output.compare(current_pos, "<", self.prompt_index):
            return "break"

        if len(event.char) == 1 and event.char.isprintable():
            self.command_buffer += event.char

    def handle_backspace(self, event):
        current_pos = self.shell_output.index("insert")
        if self.shell_output.compare(current_pos, "<=", self.prompt_index):
            return "break"

        if self.command_buffer:
            self.command_buffer = self.command_buffer[:-1]

    def handle_ctrl_c(self, event):
        if self.shell_running:
            self.shell_running = False
            self.shell_output.insert("end", "\n^C\n")
            self.shell_output.insert("end", self.shell_prompt)
            self.prompt_index = self.shell_output.index("end-1c linestart")
            self.shell_output.see("end")
        else:
            self.command_buffer = ""
            current_line_start = self.shell_output.index("insert linestart")
            self.shell_output.delete(current_line_start, "end")
            self.shell_output.insert("end", "\n^C\n")
            self.shell_output.insert("end", self.shell_prompt)
            self.prompt_index = self.shell_output.index("end-1c linestart")
            self.shell_output.see("end")
        return "break"

    def execute_terminal_command(self, event):
        cmd = self.command_buffer.strip()
        self.command_buffer = ""

        self.shell_output.insert("end", "\n")

        if cmd == "clear":
            self.clear_terminal()
            return "break"

        if cmd == "exit":
            self.shell_output.insert("end", "Use the navigation menu to exit.\n")
            self.shell_output.insert("end", self.shell_prompt)
            self.prompt_index = self.shell_output.index("end-1c linestart")
            self.shell_output.see("end")
            return "break"

        if not cmd:
            self.shell_output.insert("end", self.shell_prompt)
            self.prompt_index = self.shell_output.index("end-1c linestart")
            self.shell_output.see("end")
            return "break"

        if not self.sel_dev:
            self.shell_output.insert("end", "[ERROR] No device selected\n")
            self.shell_output.insert("end", self.shell_prompt)
            self.prompt_index = self.shell_output.index("end-1c linestart")
            self.shell_output.see("end")
            return "break"

        clean = self.sel_dev.split()[0]
        self.shell_running = True

        def _exec():
            try:
                self.bk.run_live(
                    [ADB_PATH, "-s", clean, "shell", cmd],
                    lambda l: self.after(0, lambda line=l: self.append_output(line) if self.shell_running else None)
                )
            finally:
                self.shell_running = False
                self.after(0, self.show_new_prompt)

        self.run_bg(_exec)
        return "break"

    def append_output(self, line):
        if self.shell_running:
            self.shell_output.insert("end", line + "\n")
            self.shell_output.see("end")

    def show_new_prompt(self):
        self.shell_output.insert("end", self.shell_prompt)
        self.prompt_index = self.shell_output.index("end-1c linestart")
        self.shell_output.see("end")

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
            proc = subprocess.Popen([ADB_PATH, "-s", clean, "logcat", "-v", "time"], 
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                    startupinfo=subprocess.STARTUPINFO() if os.name=="nt" else None)
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
        ctk.CTkLabel(self.main, text="Fastboot Tools", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))
        
        warn = ctk.CTkFrame(self.main, fg_color="#4a1010", corner_radius=10, border_width=1, border_color=C["danger"])
        warn.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(warn, text="⚠️ ADVANCED: Use with caution.", text_color="#FF9999").pack(pady=10)
        
        self.fb_card("Bootloader", [("Check Info", C["primary"], ["getvar", "all"]), ("Unlock OEM", C["danger"], ["oem", "unlock"])])
        self.fb_card("Flashing", [("Flash Recovery", C["warning"], None, lambda: self.fb_flash("recovery")),
                                  ("Flash Boot", C["warning"], None, lambda: self.fb_flash("boot")),
                                  ("Flash Vbmeta", C["warning"], None, lambda: self.fb_flash("vbmeta"))])
        
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
        self.bk.run_live([FASTBOOT_PATH, "-s", clean] + cmd, lambda l: self.fb_console.log(l))

    def fb_flash(self, partition):
        f = filedialog.askopenfilename(filetypes=[("IMG", "*.img")])
        if f and messagebox.askyesno("Confirm", f"Flash {partition}?"):
            self.fb_run(["flash", partition, f])

    # --- WIRELESS ---
    def view_wireless(self):
        self.clear()
        self.highlight("Wireless")
        ctk.CTkLabel(self.main, text="Wireless ADB", font=("Segoe UI", 36, "bold"), text_color=C["text_main"]).pack(anchor="w", pady=(10, 20))
        
        c1 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c1.pack(fill="x", pady=10)
        ctk.CTkLabel(c1, text="1. Enable TCP/IP Mode", font=("Segoe UI", 14, "bold")).pack(side="left", padx=20, pady=20)
        ctk.CTkButton(c1, text="Enable (5555)", fg_color=C["primary"], command=lambda: self.adb_cmd_console(["tcpip", "5555"])).pack(side="right", padx=20)
        
        c2 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c2.pack(fill="x", pady=10)
        ctk.CTkLabel(c2, text="2. Connect", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        r = ctk.CTkFrame(c2, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_ip = ctk.CTkEntry(r, placeholder_text="IP:PORT", height=40, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        if CONF.get("last_ip"): self.ent_ip.insert(0, CONF["last_ip"])
        ctk.CTkButton(r, text="Connect", height=40, fg_color=C["success"], command=self.do_wireless_connect).pack(side="right")
        
        c3 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c3.pack(fill="x", pady=10)
        ctk.CTkLabel(c3, text="3. Disconnect", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        ctk.CTkButton(c3, text="Disconnect All", height=40, fg_color=C["danger"], command=self.do_wireless_disconnect_all).pack(fill="x", padx=20, pady=(0, 10))
        
        r_disc = ctk.CTkFrame(c3, fg_color="transparent")
        r_disc.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_disc_ip = ctk.CTkEntry(r_disc, placeholder_text="IP : PORT", height=40, fg_color=C["input_bg"], border_width=0, text_color=C["text_main"])
        self.ent_disc_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(r_disc, text="Disconnect", height=40, fg_color=C["danger"], command=self.do_wireless_disconnect).pack(side="right")
        
        self.wireless_console = LogConsole(self.main, height=200)
        self.wireless_console.pack(fill="x", pady=20)

    def do_wireless_connect(self):
        ip = self.ent_ip.get()
        if ip:
            save_config("last_ip", ip)
            self.wireless_console.log(f"Connecting to {ip}...")
            self.bk.run_live([ADB_PATH, "connect", ip], lambda l: self.wireless_console.log(l))
            
    def do_wireless_disconnect_all(self):
        self.adb_cmd_console(["disconnect"])
        self.wireless_console.write("All wireless connections disconnected!", "success")

    def do_wireless_disconnect(self):
        target = self.ent_disc_ip.get().strip()
        if not target:
            self.wireless_console.write("Error: Please enter an IP:PORT to disconnect from!", "error")
            return
        self.adb_cmd_console(["disconnect", target])
        self.wireless_console.write(f"Disconnecting from {target}...", "info")

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

    def update_refresh_interval(self, value):
        global CONF
        interval = int(value)
        self.refresh_label.configure(text=f"{interval}s")
        save_config("refresh_interval", interval)
        CONF = load_config()

    def toggle_su(self):
        global CONF
        enabled = self.su_switch.get() == 1
        save_config("use_su", enabled)
        CONF = load_config()

if __name__ == "__main__":
    app = XtremeADB()
    app.mainloop()
