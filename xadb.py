import customtkinter as ctk
import subprocess
import threading
import os
import time
import re
import queue
import json
from tkinter import filedialog, messagebox, Canvas

# ==========================================
# 1. CORE CONFIGURATION
# ==========================================
APP_NAME = "Xtreme ADB V9.0"
CONFIG_FILE = "xtreme_config.json"

DEFAULT_CONFIG = {"theme": "Dark", "last_ip": ""}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    except:
        return DEFAULT_CONFIG


def save_config(key, value):
    cfg = load_config()
    cfg[key] = value
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)


CONF = load_config()
ctk.set_appearance_mode(CONF["theme"])
ctk.set_default_color_theme("dark-blue")

# ==========================================
# 2. CONSTANTS & PALETTE
# ==========================================
ADB_PATH = "adb"
FASTBOOT_PATH = "fastboot"
SCRCPY_PATH = "scrcpy"

# Tuple Format: ("Light Mode Color", "Dark Mode Color")
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
}


# ==========================================
# 3. ANIMATED WIDGETS
# ==========================================
class FluentButton(ctk.CTkButton):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.target_color = kwargs.get("fg_color", "transparent")

    def set_active(self, is_active):
        if is_active:
            self.configure(fg_color=C["btn_active"], text_color=C["primary"])
        else:
            self.configure(fg_color="transparent", text_color=C["text_sub"])


class RadialProgress(ctk.CTkFrame):
    def __init__(self, master, title="Usage", size=120, color=C["primary"], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.size = size
        self.color = color
        self.percentage = 0

        # Determine initial background
        initial_bg = "#1C1C1C" if ctk.get_appearance_mode() == "Dark" else "#FFFFFF"

        self.canvas = Canvas(
            self, width=size, height=size, highlightthickness=0, bg=initial_bg
        )
        self.canvas.pack()

        self.label = ctk.CTkLabel(
            self, text="0%", font=("Segoe UI", 18, "bold"), text_color=C["text_main"]
        )
        self.label.place(relx=0.5, rely=0.4, anchor="center")

        ctk.CTkLabel(
            self, text=title, font=("Segoe UI", 12), text_color=C["text_sub"]
        ).pack(pady=5)

        self.bind("<Configure>", self.update_bg)
        self.draw()

    def update_bg(self, event=None):
        mode = ctk.get_appearance_mode()
        bg = "#FFFFFF" if mode == "Light" else "#1C1C1C"
        self.canvas.configure(bg=bg)
        self.label.configure(bg_color=bg)

    def draw(self):
        self.canvas.delete("all")
        w = self.size
        h = self.size
        x = w / 2
        y = h / 2
        r = (w / 2) - 8

        track_col = "#333333" if ctk.get_appearance_mode() == "Dark" else "#E0E0E0"
        self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=track_col, width=8)

        angle = -(360 * (self.percentage / 100))
        if self.percentage > 0:
            self.canvas.create_arc(
                x - r,
                y - r,
                x + r,
                y + r,
                start=90,
                extent=angle,
                style="arc",
                outline=self.color,
                width=8,
            )

    def set(self, val):
        self.percentage = max(0, min(val, 100))
        self.label.configure(text=f"{int(self.percentage)}%")
        self.draw()


# ==========================================
# 4. BACKEND ENGINE
# ==========================================
class Backend:
    @staticmethod
    def run(cmd, timeout=5):
        try:
            startupinfo = subprocess.STARTUPINFO() if os.name == "nt" else None
            if os.name == "nt":
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                timeout=timeout,
            )
            return res.stdout.strip() + res.stderr.strip()
        except subprocess.TimeoutExpired:
            return ""
        except Exception as e:
            return str(e)

    def get_devices(self):
        d = []
        out = self.run([ADB_PATH, "devices"], timeout=2)
        for l in out.split("\n"):
            if "\t" in l and "device" in l:
                d.append(f"{l.split('\t')[0]} (ADB)")
        out_fb = self.run([FASTBOOT_PATH, "devices"], timeout=2)
        for l in out_fb.split("\n"):
            if "\t" in l:
                d.append(f"{l.split('\t')[0]} (FASTBOOT)")
        return d

    def get_stats(self, device_id):
        if "ADB" not in device_id:
            return {}
        clean = device_id.split()[0]
        batt = self.run(
            [ADB_PATH, "-s", clean, "shell", "dumpsys", "battery"], timeout=2
        )
        lvl = 0
        for l in batt.split("\n"):
            if "level:" in l:
                lvl = int(l.split(":")[1].strip())
        mem = self.run(
            [ADB_PATH, "-s", clean, "shell", "cat", "/proc/meminfo"], timeout=2
        )
        tot, av = 1, 1
        for l in mem.split("\n"):
            if "MemTotal" in l:
                tot = int(re.search(r"\d+", l).group())
            if "MemAvailable" in l:
                av = int(re.search(r"\d+", l).group())
        return {"batt": lvl, "ram": ((tot - av) / tot) * 100}


# ==========================================
# 5. MAIN APPLICATION
# ==========================================
class XtremeADB(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1300x850")
        self.configure(fg_color=C["bg_root"])

        self.bk = Backend()
        self.sel_dev = None
        self.cur_path = "/sdcard/"
        self.log_proc = None
        self.log_q = queue.Queue()
        self.nav_buttons = {}
        self.active_radials = []

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.init_ui()
        threading.Thread(target=self.dev_loop, daemon=True).start()
        threading.Thread(target=self.stats_loop, daemon=True).start()

    def run_bg(self, func):
        threading.Thread(target=func, daemon=True).start()

    def init_ui(self):
        # Sidebar
        self.sidebar = ctk.CTkFrame(
            self, width=90, corner_radius=0, fg_color=C["bg_sidebar"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="XA",
            font=("Segoe UI", 28, "bold"),
            text_color=C["primary"],
        ).pack(pady=(30, 20))

        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(fill="x", pady=10)

        items = [
            ("🏠", "Dashboard", self.view_dash),
            ("💻", "Shell", self.view_shell),
            ("📦", "Apps", self.view_apps),
            ("📁", "Files", self.view_files),
            ("📡", "Wireless", self.view_wireless),
            ("⚡", "Fastboot", self.view_fastboot),
            ("🔧", "Tweaks", self.view_tweaks),
            ("🛠", "Backup", self.view_backup),
            ("⚙️", "Settings", self.view_settings),
        ]

        for icon, name, cmd in items:
            btn = FluentButton(
                self.nav_frame,
                text=icon,
                width=50,
                height=50,
                corner_radius=10,
                font=("Segoe UI", 22),
                command=cmd,
                fg_color="transparent",
                text_color=C["text_sub"],
            )
            btn.pack(pady=5, padx=10)
            self.nav_buttons[name] = btn

        self.status_dot = ctk.CTkLabel(
            self.sidebar, text="●", font=("Arial", 24), text_color=C["danger"]
        )
        self.status_dot.pack(side="bottom", pady=(0, 20))

        self.status_lbl = ctk.CTkLabel(
            self.sidebar, text="None", font=("Segoe UI", 10), text_color="gray"
        )
        self.status_lbl.pack(side="bottom", pady=(0, 5))

        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color=C["bg_root"])
        self.main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        self.view_dash()

    def highlight(self, name):
        self.monitor_active = name == "Dashboard"
        for k, btn in self.nav_buttons.items():
            btn.set_active(k == name)

    def clear(self):
        if self.log_proc:
            self.log_proc.terminate()
            self.log_proc = None
        self.active_radials = []
        for w in self.main.winfo_children():
            w.destroy()

    def adb_cmd(self, args, success_msg="Done"):
        if not self.sel_dev:
            messagebox.showerror("Error", "No Device")
            return
        cln = self.sel_dev.split()[0]
        self.run_bg(
            lambda: [
                self.bk.run([ADB_PATH, "-s", cln] + args),
                messagebox.showinfo("ADB", success_msg),
            ]
        )

    def dev_loop(self):
        while True:
            d = self.bk.get_devices()
            if d:
                if self.sel_dev not in d:
                    self.sel_dev = d[0]
                self.status_dot.configure(text_color=C["success"])
                self.status_lbl.configure(text="Ready")
            else:
                self.sel_dev = None
                self.status_dot.configure(text_color=C["danger"])
                self.status_lbl.configure(text="None")
            time.sleep(2)

    def stats_loop(self):
        while True:
            if self.monitor_active and self.sel_dev and "ADB" in self.sel_dev:
                d = self.bk.get_stats(self.sel_dev)
                try:
                    self.rad_batt.set(d.get("batt", 0))
                    self.rad_ram.set(d.get("ram", 0))
                except:
                    pass
            time.sleep(3)

    # ================= VIEWS =================

    def view_dash(self):
        self.clear()
        self.highlight("Dashboard")
        ctk.CTkLabel(
            self.main,
            text="System Dashboard",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 30))

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

        ctk.CTkLabel(
            self.main,
            text="Power Controls",
            font=("Segoe UI", 18, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(30, 10))
        pg = ctk.CTkFrame(self.main, fg_color="transparent")
        pg.pack(fill="x")

        btns = [
            ("Reboot System", ["reboot"], C["primary"]),
            ("Recovery", ["reboot", "recovery"], C["warning"]),
            ("Bootloader", ["reboot", "bootloader"], C["warning"]),
            ("Power Off", ["reboot", "-p"], C["danger"]),
        ]

        for t, c, col in btns:
            ctk.CTkButton(
                pg,
                text=t,
                fg_color=col,
                height=50,
                corner_radius=8,
                font=("Segoe UI", 14, "bold"),
                command=lambda x=c: self.adb_cmd(x),
            ).pack(side="left", fill="x", expand=True, padx=5)

        if self.sel_dev:
            self.run_bg(self.update_stats)

    def update_stats(self):
        d = self.bk.get_stats(self.sel_dev)
        try:
            self.rad_batt.set(d.get("batt", 0))
            self.rad_ram.set(d.get("ram", 0))
        except:
            pass

    # --- APPS ---
    def view_apps(self):
        self.clear()
        self.highlight("Apps")
        ctk.CTkLabel(
            self.main,
            text="App Manager",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 20))

        bar = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        bar.pack(fill="x", pady=(0, 20), ipady=5)
        self.app_search = ctk.CTkEntry(
            bar,
            placeholder_text="Search apps...",
            border_width=0,
            fg_color=C["input_bg"],
            height=40,
            text_color=C["text_main"],
        )
        self.app_search.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        ctk.CTkButton(
            bar, text="Load List", fg_color=C["primary"], command=self.load_apps
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            bar, text="Install APK", fg_color=C["success"], command=self.install_apk
        ).pack(side="left", padx=10)

        split = ctk.CTkFrame(self.main, fg_color="transparent")
        split.pack(fill="both", expand=True)
        self.app_list = ctk.CTkScrollableFrame(
            split, fg_color=C["bg_surface"], corner_radius=15
        )
        self.app_list.pack(side="left", fill="both", expand=True, padx=(0, 10))
        act = ctk.CTkFrame(split, width=250, fg_color=C["bg_surface"], corner_radius=15)
        act.pack(side="right", fill="y")
        ctk.CTkLabel(
            act,
            text="Selected App",
            font=("Segoe UI", 14, "bold"),
            text_color=C["text_main"],
        ).pack(pady=20)
        self.lbl_pkg = ctk.CTkLabel(act, text="None", text_color="gray", wraplength=200)
        self.lbl_pkg.pack(pady=5)
        self.sel_pkg = None
        ctk.CTkButton(
            act, text="Uninstall", fg_color=C["danger"], command=self.do_uninst
        ).pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(
            act, text="Force Stop", fg_color=C["warning"], command=self.do_force
        ).pack(fill="x", padx=20, pady=5)
        ctk.CTkButton(
            act, text="Extract APK", fg_color=C["primary"], command=self.do_extract
        ).pack(fill="x", padx=20, pady=5)

    def load_apps(self):
        if not self.sel_dev:
            return
        cln = self.sel_dev.split()[0]
        for w in self.app_list.winfo_children():
            w.destroy()

        def _t():
            raw = self.bk.run(
                [ADB_PATH, "-s", cln, "shell", "pm", "list", "packages", "-3"]
            )
            pkgs = sorted(
                [
                    x.replace("package:", "").strip()
                    for x in raw.split("\n")
                    if x.strip()
                ]
            )
            for p in pkgs:
                if self.app_search.get().lower() in p.lower():
                    ctk.CTkButton(
                        self.app_list,
                        text=p,
                        anchor="w",
                        fg_color="transparent",
                        hover_color=C["bg_hover"],
                        text_color=C["text_main"],
                        command=lambda x=p: self.set_app(x),
                    ).pack(fill="x")

        self.run_bg(_t)

    def set_app(self, p):
        self.sel_pkg = p
        self.lbl_pkg.configure(text=p)

    def install_apk(self):
        f = filedialog.askopenfilename(filetypes=[("APK", "*.apk")])
        if f:
            self.adb_cmd(["install", f], "Installed")

    def do_uninst(self):
        self.adb_cmd(["uninstall", self.sel_pkg])
        self.load_apps()

    def do_force(self):
        self.adb_cmd(["shell", "am", "force-stop", self.sel_pkg])

    def do_extract(self):
        if self.sel_pkg:
            d = filedialog.askdirectory()
            if d:
                cln = self.sel_dev.split()[0]
                self.run_bg(
                    lambda: self.bk.run(
                        [
                            ADB_PATH,
                            "-s",
                            cln,
                            "pull",
                            self.bk.run(
                                [
                                    ADB_PATH,
                                    "-s",
                                    cln,
                                    "shell",
                                    "pm",
                                    "path",
                                    self.sel_pkg,
                                ]
                            )
                            .replace("package:", "")
                            .strip(),
                            f"{d}/{self.sel_pkg}.apk",
                        ]
                    )
                )

    # ================= FILES =================
    def view_files(self):
        self.clear()
        self.highlight("Files")
        ctk.CTkLabel(
            self.main,
            text="File Explorer",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 20))
        nav = ctk.CTkFrame(self.main, fg_color=C["bg_surface"])
        nav.pack(fill="x", pady=10)
        ctk.CTkButton(
            nav, text="⬆", width=40, command=self.fm_up, fg_color="#333"
        ).pack(side="left", padx=10, pady=10)
        self.fm_ent = ctk.CTkEntry(
            nav,
            border_width=0,
            fg_color=C["input_bg"],
            height=35,
            text_color=C["text_main"],
        )
        self.fm_ent.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            nav, text="Go", width=60, command=self.fm_load, fg_color=C["primary"]
        ).pack(side="left", padx=10)
        bar = ctk.CTkFrame(self.main, fg_color="transparent")
        bar.pack(fill="x", pady=10)
        ops = [
            ("New Folder", self.fm_mkdir),
            ("Delete", self.fm_del),
            ("Rename", self.fm_ren),
            ("Upload", self.fm_upload),
            ("Download", self.fm_download),
        ]
        for t, c in ops:
            ctk.CTkButton(
                bar,
                text=t,
                width=80,
                fg_color=C["input_bg"],
                hover_color=C["bg_hover"],
                text_color=C["text_main"],
                command=c,
            ).pack(side="left", padx=5)
        self.fm_list = ctk.CTkScrollableFrame(
            self.main, fg_color=C["bg_surface"], corner_radius=15
        )
        self.fm_list.pack(fill="both", expand=True)
        self.fm_sel = None
        self.fm_ent.insert(0, self.cur_path)
        self.fm_load()

    def fm_load(self):
        if not self.sel_dev:
            return
        cln = self.sel_dev.split()[0]
        path = self.fm_ent.get()
        self.cur_path = path
        for w in self.fm_list.winfo_children():
            w.destroy()
        self.file_buttons = []

        def _t():
            out = self.bk.run([ADB_PATH, "-s", cln, "shell", "ls", "-1pH", f'"{path}"'])
            for i in [x for x in out.split("\n") if x.strip() and "No such" not in x]:
                is_dir = i.endswith("/")
                col = C["primary"] if is_dir else C["text_main"]
                icon = "📁" if is_dir else "📄"
                b = ctk.CTkButton(
                    self.fm_list,
                    text=f"{icon}  {i}",
                    anchor="w",
                    fg_color="transparent",
                    hover_color=C["bg_hover"],
                    text_color=col,
                )
                b.configure(
                    command=lambda btn=b, name=i: self.fm_select_item(btn, name)
                )
                b.pack(fill="x")
                if is_dir:
                    b.bind("<Double-Button-1>", lambda e, x=i: self.fm_ent_dir(x))
                self.file_buttons.append(b)

        self.run_bg(_t)

    def fm_select_item(self, btn_ref, name):
        self.fm_sel = name
        for b in self.file_buttons:
            b.configure(fg_color="transparent")
        btn_ref.configure(fg_color=C["primary"])

    def fm_ent_dir(self, x):
        self.cur_path = os.path.join(self.cur_path, x).replace("\\", "/")
        self.fm_ent.delete(0, "end")
        self.fm_ent.insert(0, self.cur_path)
        self.fm_load()

    def fm_up(self):
        self.cur_path = os.path.dirname(self.cur_path.rstrip("/")) + "/"
        self.fm_ent.delete(0, "end")
        self.fm_ent.insert(0, self.cur_path)
        self.fm_load()

    def fm_mkdir(self):
        n = ctk.CTkInputDialog(text="Name:", title="New").get_input()
        if n:
            self.adb_cmd(["shell", "mkdir", "-p", f'"{self.cur_path}{n}"'])
            self.after(500, self.fm_load)

    def fm_del(self):
        if self.fm_sel:
            self.adb_cmd(["shell", "rm", "-rf", f'"{self.cur_path}{self.fm_sel}"'])
            self.after(500, self.fm_load)

    def fm_ren(self):
        if self.fm_sel:
            n = ctk.CTkInputDialog(text="Name:", title="Ren").get_input()
            if n:
                self.adb_cmd(
                    [
                        "shell",
                        "mv",
                        f'"{self.cur_path}{self.fm_sel}"',
                        f'"{self.cur_path}{n}"',
                    ]
                )
                self.after(500, self.fm_load)

    def fm_upload(self):
        fs = filedialog.askopenfilenames()
        if fs:
            cln = self.sel_dev.split()[0]
            threading.Thread(
                target=lambda: [
                    self.bk.run([ADB_PATH, "-s", cln, "push", f, self.cur_path])
                    for f in fs
                ]
            ).start()
            self.after(1000, self.fm_load)

    def fm_download(self):
        if self.fm_sel:
            s = filedialog.asksaveasfilename(initialfile=self.fm_sel)
            if s:
                cln = self.sel_dev.split()[0]
                self.run_bg(
                    lambda: self.bk.run(
                        [
                            ADB_PATH,
                            "-s",
                            cln,
                            "pull",
                            f"{self.cur_path}{self.fm_sel}",
                            s,
                        ]
                    )
                )

    # --- SHELL ---
    def view_shell(self):
        self.clear()
        self.highlight("Shell")
        ctk.CTkLabel(
            self.main,
            text="Terminal",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 20))
        self.term_out = ctk.CTkTextbox(
            self.main, font=("Consolas", 12), fg_color="#151515", text_color="#00FF00"
        )
        self.term_out.pack(fill="both", expand=True, pady=(0, 20))
        row = ctk.CTkFrame(self.main, fg_color="transparent")
        row.pack(fill="x")
        self.term_ent = ctk.CTkEntry(
            row,
            border_width=0,
            fg_color="#222",
            placeholder_text="Command...",
            height=40,
            text_color="white",
        )
        self.term_ent.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.term_ent.bind("<Return>", self.run_term)
        ctk.CTkButton(
            row,
            text="RUN",
            width=80,
            height=40,
            fg_color=C["success"],
            command=self.run_term,
        ).pack(side="left")

    def run_term(self, e=None):
        cmd = self.term_ent.get()
        self.term_ent.delete(0, "end")
        if not cmd:
            return
        self.term_out.insert("end", f"\n> {cmd}\n")
        if self.sel_dev:
            self.run_bg(
                lambda: self.term_out.insert(
                    "end",
                    self.bk.run(
                        [ADB_PATH, "-s", self.sel_dev.split()[0], "shell"] + cmd.split()
                    )
                    + "\n",
                )
            )

    # --- FASTBOOT ---
    def view_fastboot(self):
        self.clear()
        self.highlight("Fastboot")
        ctk.CTkLabel(
            self.main,
            text="Fastboot Tools",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 20))
        warn = ctk.CTkFrame(
            self.main,
            fg_color="#4a1010",
            corner_radius=10,
            border_width=1,
            border_color=C["danger"],
        )
        warn.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(
            warn, text="⚠️ ADVANCED: Use with caution.", text_color="#FF9999"
        ).pack(pady=10)
        self.fb_card(
            "Bootloader Status",
            [
                ("Check Info", C["primary"], ["getvar", "all"]),
                ("Unlock OEM", C["danger"], ["oem", "unlock"]),
            ],
        )
        self.fb_card(
            "Live Testing", [("Boot .img (Temp)", C["success"], None, self.fb_boot)]
        )
        self.fb_card(
            "Flashing",
            [
                (
                    "Flash Recovery",
                    C["warning"],
                    None,
                    lambda: self.fb_flash("recovery"),
                ),
                ("Flash Boot", C["warning"], None, lambda: self.fb_flash("boot")),
            ],
        )
        self.fb_card("Sideload", [("Sideload Zip", C["primary"], None, self.sideload)])

    def fb_card(self, title, actions):
        f = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=10)
        f.pack(fill="x", pady=10, ipady=10)
        ctk.CTkLabel(
            f, text=title, font=("Segoe UI", 16, "bold"), text_color=C["text_main"]
        ).pack(side="left", padx=20)
        for label, col, cmd, *fn in actions:
            func = fn[0] if fn else lambda c=cmd: self.fb_run(c)
            ctk.CTkButton(f, text=label, fg_color=col, width=120, command=func).pack(
                side="right", padx=10
            )

    def fb_run(self, a):
        if not self.sel_dev:
            return
        self.run_bg(
            lambda: messagebox.showinfo(
                "Output",
                self.bk.run([FASTBOOT_PATH, "-s", self.sel_dev.split()[0]] + a),
            )
        )

    def fb_boot(self):
        f = filedialog.askopenfilename(filetypes=[("IMG", "*.img")])
        if f:
            self.fb_run(["boot", f])

    def fb_flash(self, p):
        f = filedialog.askopenfilename(filetypes=[("IMG", "*.img")])
        if f:
            self.fb_run(["flash", p, f])

    def sideload(self):
        f = filedialog.askopenfilename(filetypes=[("ZIP", "*.zip")])
        if f:
            self.fb_run(["sideload", f])

    # --- WIRELESS ---
    def view_wireless(self):
        self.clear()
        self.highlight("Wireless")
        ctk.CTkLabel(
            self.main,
            text="Wireless ADB",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 20))
        c1 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c1.pack(fill="x", pady=10)
        ctk.CTkLabel(
            c1,
            text="1. Enable TCP/IP Mode",
            font=("Segoe UI", 14, "bold"),
            text_color=C["text_main"],
        ).pack(side="left", padx=20, pady=20)
        ctk.CTkButton(
            c1,
            text="Enable (5555)",
            fg_color=C["primary"],
            command=lambda: self.adb_cmd(["tcpip", "5555"], "TCP Mode Enabled"),
        ).pack(side="right", padx=20)
        c2 = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c2.pack(fill="x", pady=10)
        ctk.CTkLabel(
            c2,
            text="2. Connect",
            font=("Segoe UI", 14, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", padx=20, pady=(20, 5))
        r = ctk.CTkFrame(c2, fg_color="transparent")
        r.pack(fill="x", padx=20, pady=(0, 20))
        self.ent_ip = ctk.CTkEntry(
            r,
            placeholder_text="IP:PORT",
            height=40,
            fg_color=C["input_bg"],
            border_width=0,
            text_color=C["text_main"],
        )
        self.ent_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        if CONF.get("last_ip"):
            self.ent_ip.insert(0, CONF["last_ip"])
        ctk.CTkButton(
            r,
            text="Connect",
            height=40,
            fg_color=C["success"],
            command=lambda: [
                save_config("last_ip", self.ent_ip.get()),
                self.bk.run([ADB_PATH, "connect", self.ent_ip.get()]),
            ],
        ).pack(side="right")
        c3 = ctk.CTkFrame(
            self.main,
            fg_color="#252525",
            corner_radius=15,
            border_width=1,
            border_color=C["primary"],
        )
        c3.pack(fill="x", pady=20)
        ctk.CTkLabel(
            c3,
            text="3. Pair (Android 11+)",
            font=("Segoe UI", 14, "bold"),
            text_color=C["primary"],
        ).pack(anchor="w", padx=20, pady=(20, 5))
        r2 = ctk.CTkFrame(c3, fg_color="transparent")
        r2.pack(fill="x", padx=20, pady=(0, 20))
        self.pair_ip = ctk.CTkEntry(
            r2,
            placeholder_text="IP:PORT",
            height=45,
            fg_color=C["input_bg"],
            border_width=0,
            text_color=C["text_main"],
        )
        self.pair_ip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.pair_code = ctk.CTkEntry(
            r2,
            placeholder_text="Code",
            height=45,
            width=120,
            fg_color=C["input_bg"],
            border_width=0,
            justify="center",
            text_color=C["text_main"],
        )
        self.pair_code.pack(side="left")
        ctk.CTkButton(
            r2,
            text="PAIR",
            height=45,
            fg_color=C["primary"],
            command=lambda: messagebox.showinfo(
                "Res",
                self.bk.run(
                    [ADB_PATH, "pair", self.pair_ip.get(), self.pair_code.get()]
                ),
            ),
        ).pack(side="right", padx=(10, 0))

    # --- TWEAKS ---
    def view_tweaks(self):
        self.clear()
        self.highlight("Tweaks")
        ctk.CTkLabel(
            self.main,
            text="Tweaks",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 20))
        f = ctk.CTkFrame(self.main, fg_color=C["bg_surface"])
        f.pack(fill="x", padx=30)
        for t, n, k in [
            ("Show Taps", "system", "show_touches"),
            ("Pointer Loc", "system", "pointer_location"),
        ]:
            r = ctk.CTkFrame(f, fg_color="transparent")
            r.pack(fill="x", pady=5)
            ctk.CTkLabel(r, text=t, text_color=C["text_main"]).pack(
                side="left", padx=20
            )
            ctk.CTkButton(
                r,
                text="ON",
                width=60,
                fg_color=C["success"],
                command=lambda nn=n, kk=k: self.adb_cmd(
                    ["shell", "settings", "put", nn, kk, "1"]
                ),
            ).pack(side="right", padx=5)
            ctk.CTkButton(
                r,
                text="OFF",
                width=60,
                fg_color="#333",
                command=lambda nn=n, kk=k: self.adb_cmd(
                    ["shell", "settings", "put", nn, kk, "0"]
                ),
            ).pack(side="right", padx=5)

    # --- BACKUP & RESTORE (FIXED) ---
    def view_backup(self):
        self.clear()
        self.highlight("Backup")
        ctk.CTkLabel(
            self.main,
            text="Backup & Restore",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 20))

        # Split cards
        grid = ctk.CTkFrame(self.main, fg_color="transparent")
        grid.pack(fill="x", padx=30)

        # Backup Card
        b_card = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=15)
        b_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(
            b_card,
            text="Backup Device",
            font=("Segoe UI", 18, "bold"),
            text_color=C["text_main"],
        ).pack(pady=20)
        ctk.CTkButton(
            b_card,
            text="Start Backup",
            height=50,
            fg_color=C["primary"],
            command=self.do_backup,
        ).pack(pady=20, padx=20)

        # Restore Card
        r_card = ctk.CTkFrame(grid, fg_color=C["bg_surface"], corner_radius=15)
        r_card.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ctk.CTkLabel(
            r_card,
            text="Restore Device",
            font=("Segoe UI", 18, "bold"),
            text_color=C["text_main"],
        ).pack(pady=20)
        ctk.CTkButton(
            r_card,
            text="Start Restore",
            height=50,
            fg_color=C["warning"],
            command=self.do_restore,
        ).pack(pady=20, padx=20)

    def do_backup(self):
        f = filedialog.asksaveasfilename(defaultextension=".ab")
        if f:
            cln = self.sel_dev.split()[0]
            self.run_bg(
                lambda: self.bk.run(
                    [ADB_PATH, "-s", cln, "backup", "-all", "-apk", "-shared", "-f", f]
                )
            )

    def do_restore(self):
        f = filedialog.askopenfilename()
        if f:
            cln = self.sel_dev.split()[0]
            self.run_bg(lambda: self.bk.run([ADB_PATH, "-s", cln, "restore", f]))

    # --- SETTINGS ---
    def view_settings(self):
        self.clear()
        self.highlight("Settings")
        ctk.CTkLabel(
            self.main,
            text="Settings",
            font=("Segoe UI", 36, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", pady=(10, 20))

        c = ctk.CTkFrame(self.main, fg_color=C["bg_surface"], corner_radius=15)
        c.pack(fill="x", padx=30, pady=20)

        ctk.CTkLabel(
            c,
            text="Appearance",
            font=("Segoe UI", 16, "bold"),
            text_color=C["text_main"],
        ).pack(anchor="w", padx=20, pady=(20, 10))

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            row,
            text="Light Mode",
            height=50,
            fg_color="#E0E0E0",
            text_color="black",
            command=lambda: [
                ctk.set_appearance_mode("Light"),
                save_config("theme", "Light"),
            ],
        ).pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkButton(
            row,
            text="Dark Mode",
            height=50,
            fg_color="#222222",
            text_color="white",
            command=lambda: [
                ctk.set_appearance_mode("Dark"),
                save_config("theme", "Dark"),
            ],
        ).pack(side="left", fill="x", expand=True, padx=5)


if __name__ == "__main__":
    app = XtremeADB()
    app.mainloop()
