"""
Manager ServerPal â€” Setup & Launcher
Chá»©c nÄƒng:
  â€¢ Äá»c / ghi manager_config.json (tÆ°Æ¡ng Ä‘Æ°Æ¡ng AppConfig)
  â€¢ Táº¡o config má»›i tá»« template
  â€¢ Khá»Ÿi cháº¡y serverpal.py
  â€¢ Cáº­p nháº­t PalServer qua SteamCMD (App ID 2394010)
  â€¢ CÃ i Ä‘áº·t Python + Node.js packages
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
from urllib.parse import urlparse
import os
import sys
import subprocess
import threading
import datetime
import time
import ctypes
import tempfile
import shutil
import zipfile
import urllib.request
import urllib.error
import re
import glob
import traceback
import hashlib
import webbrowser

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Hide console window when launched via `python.exe`
# (e.g. double-click `setup.py` on Windows).
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _hide_console_if_present() -> None:
    try:
        import ctypes as _ctypes
        kernel32 = _ctypes.windll.kernel32
        user32 = _ctypes.windll.user32
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            # 0 = SW_HIDE
            user32.ShowWindow(hwnd, 0)
    except Exception:
        pass

_hide_console_if_present()

try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# Optional: py7zr (7z), rarfile (rar) â€” cÃ i qua pip install -r requirements.txt
try:
    import py7zr as _py7zr; HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False
try:
    import rarfile as _rarfile; HAS_RAR = True
except ImportError:
    HAS_RAR = False

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  ADMIN CHECK (khÃ´ng tá»± nÃ¢ng quyá»n)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
try:
    IS_ADMIN = bool(ctypes.windll.shell32.IsUserAnAdmin())
except Exception:
    IS_ADMIN = False

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  ÄÆ¯á»œNG DáºªN
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Khi cháº¡y dáº¡ng .py: APP_DIR = thÆ° má»¥c source.
# Khi cháº¡y dáº¡ng PyInstaller one-file: APP_DIR = thÆ° má»¥c chá»©a .exe, cÃ²n BUNDLE_DIR = thÆ° má»¥c táº¡m giáº£i nÃ©n.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
    BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR

BASE_DIR    = APP_DIR
IS_FROZEN_APP = bool(getattr(sys, "frozen", False))
CONFIG_FILE = os.path.join(APP_DIR, "manager_config.json")
SERVERPAL_PY = os.path.join(APP_DIR, "serverpal.py")
SERVERPAL_EXE = os.path.join(APP_DIR, "Manager_ServerPal_App.exe")
REQ_FILE    = os.path.join(BUNDLE_DIR, "requirements.txt")
MAP_DIR     = os.path.join(APP_DIR, "palserver-online-map-main")
VENV_DIR    = os.path.join(APP_DIR, ".venv")
VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
VENV_PYTHONW = os.path.join(VENV_DIR, "Scripts", "pythonw.exe")
NPM_CACHE_DIR = os.path.join(BASE_DIR, ".npm-cache")
UI_ASSETS_DIR = os.path.join(BUNDLE_DIR, "_ui_assets")
UI_ICON_PNG = os.path.join(UI_ASSETS_DIR, "app_icon.png")
UI_BG_JPG   = os.path.join(UI_ASSETS_DIR, "app_background.jpg")
MANAGER_PAL_SETTINGS_INI = os.path.join(BUNDLE_DIR, "PalWorldSettings.ini")

# App ID Palworld Dedicated Server trÃªn Steam
PALWORLD_APPID = "2394010"
APP_VERSION = "1.0.2"
DEFAULT_SERVER_ROOT = r"C:\palwordsteamserver"
DEFAULT_SERVER_EXE = os.path.join(DEFAULT_SERVER_ROOT, "steamapps", "common", "PalServer", "PalServer.exe")

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  CONFIG TEMPLATE (dÃ¹ng khi táº¡o config má»›i)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CONFIG_TEMPLATE = {
    "_":                    "Manager ServerPal â€” v1.0.2 by MityTinDev. Chá»‰nh giÃ¡ trá»‹ bÃªn dÆ°á»›i rá»“i cháº¡y: python serverpal.py",
    "SERVER_EXE":           DEFAULT_SERVER_EXE,
    "API_URL":              "http://127.0.0.1:8212/v1/api",
    "ADMIN_PASSWORD":       "Admin#123",
    "AUTH_PASS":            "Admin#123",
    "RCON_HOST":            "127.0.0.1",
    "RCON_PORT":            "25575",
    "PUBLIC_PORT":          "8211",
    "QUERY_PORT":           "27015",
    "RCON_ENABLED":         "true",
    "RESTAPI_ENABLED":      "true",
    "SHOW_PLAYER_LIST":     "true",
    "RCON_PASSWORD":        "Admin#123",
    "PALDEF_API_BASE":      "http://127.0.0.1:17993",
    "DISCORD_WEBHOOK_URL":  "",
    "ANTIBUG_WEBHOOK_URL":  "",
    "DISCORD_CHAT_WEBHOOK": "",
    "DISCORD_BOT_TOKEN":    "",
    "DISCORD_CHAT_CHANNEL_ID": "",
    "PLAYER_CONNECT_WEBHOOK_URL": "",
    "RANKING_WEBHOOK_URL": "",
    "DISCORD_BOT2_TOKEN":   "",
    "DISCORD_BOT2_CHANNEL_ID": "",
    "DISCORD_BOT2_RANKING_CHANNEL_ID": "",
    "DISCORD_BOT2_LIVEMAP_CHANNEL_ID": "",
    "DISCORD_BOT2_NAME":    "Cá» HÃ³",
    "ANTIBUG_MAX_KICKS":    "3",
    "ANTIBUG_KICK_WINDOW":  "300",
    "STEAMCMD_EXE":         r"C:\steamcmd\steamcmd.exe",
    "GITHUB_REPO":          "MityTin/manager-serverpal",
    "AUTO_UPDATE_CHECK":    "true",
}

def _normalize_shared_admin_password(data: dict) -> dict:
    """Äá»“ng bá»™ máº­t kháº©u admin dÃ¹ng chung cho REST/RCON."""
    result = dict(data or {})
    pwd = ""
    for key in ("AUTH_PASS", "RCON_PASSWORD", "ADMIN_PASSWORD"):
        val = result.get(key, "")
        if isinstance(val, str) and val.strip():
            pwd = val.strip()
            break
    if not pwd:
        pwd = "Admin#123"
    result["AUTH_PASS"] = pwd
    result["RCON_PASSWORD"] = pwd
    result["ADMIN_PASSWORD"] = pwd
    return result

def _resolve_server_exe_path(path_hint: str) -> str:
    """Chuáº©n hÃ³a SERVER_EXE tá»« file hoáº·c thÆ° má»¥c Ä‘Ã£ chá»n."""
    if not path_hint:
        return ""
    p = os.path.abspath(str(path_hint).strip().strip('"'))
    if not p:
        return ""
    if os.path.isfile(p):
        if os.path.basename(p).lower() == "palserver.exe":
            return p
        # Náº¿u user chá»n nháº§m file exe khÃ¡c, thá»­ dÃ² PalServer.exe quanh thÆ° má»¥c Ä‘Ã³.
        base_dir = os.path.dirname(p)
        direct = os.path.join(base_dir, "PalServer.exe")
        if os.path.isfile(direct):
            return direct
        for root, _, files in os.walk(base_dir):
            for fn in files:
                if fn.lower() == "palserver.exe":
                    return os.path.join(root, fn)
        return ""
    if os.path.isdir(p):
        direct = os.path.join(p, "PalServer.exe")
        if os.path.isfile(direct):
            return direct
        for root, _, files in os.walk(p):
            for fn in files:
                if fn.lower() == "palserver.exe":
                    return os.path.join(root, fn)
    return ""

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  MODS CATALOG
#  target   : Ä‘Æ°á»ng dáº«n tÆ°Æ¡ng Ä‘á»‘i tá»« PalServer root (SERVER_EXE dir)
#  probe    : file/folder Ä‘á»ƒ kiá»ƒm tra Ä‘Ã£ cÃ i chÆ°a (relative to PalServer root)
#  toggle   : file rename Ä‘á»ƒ báº­t/táº¯t (relative to PalServer root), None = khÃ´ng há»— trá»£ toggle
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MODS_CATALOG = [
    {
        "id":      "paldefender",
        "icon":    "ðŸ›¡",
        "name":    "PalDefender",
        "desc":    "Anti-cheat, cheat detection & server protection plugin",
        "version": "Latest",
        "url":     "https://drive.google.com/file/d/1dzp683jr_lPB6aTDmhOMtXq1elwga947/view?usp=sharing",
        "target":  os.path.join("Pal", "Binaries", "Win64"),
        "probe":   os.path.join("Pal", "Binaries", "Win64", "PalDefender.dll"),
        "toggle":  os.path.join("Pal", "Binaries", "Win64", "PalDefender.dll"),
        # Nháº­n diá»‡n/gá»¡ rÃµ theo bá»™ file PalDefender thá»±c táº¿.
        "uninstall_files": [
            os.path.join("Pal", "Binaries", "Win64", "PalDefender.dll"),
            os.path.join("Pal", "Binaries", "Win64", "PalDefender"),
            os.path.join("Pal", "Binaries", "Win64", "d3d9.dll"),
            os.path.join("Pal", "Binaries", "Win64", "d3d9_config.json"),
        ],
        "default_on": True,
    },
    {
        "id":      "ue4ss",
        "icon":    "ðŸ”§",
        "name":    "UE4SS v3.0.1",
        "desc":    "Unreal Engine Script System â€” mod loading framework",
        "version": "3.0.1-938",
        "url":     "https://drive.google.com/file/d/1zSvqZKi1V6akVFZCs20DkceU-RP--ZSV/view?usp=sharing",
        "target":  os.path.join("Pal", "Binaries", "Win64"),
        # UE4SS quáº£n lÃ½ Ä‘á»™c láº­p theo dwmapi.dll.
        "probe":   os.path.join("Pal", "Binaries", "Win64", "dwmapi.dll"),
        "toggle":  os.path.join("Pal", "Binaries", "Win64", "dwmapi.dll"),
        # Theo yÃªu cáº§u: gá»¡ UE4SS chá»‰ cáº§n xÃ³a dwmapi.dll, khÃ´ng xÃ³a thÆ° má»¥c khÃ¡c.
        "uninstall_files": [
            os.path.join("Pal", "Binaries", "Win64", "dwmapi.dll"),
        ],
        "default_on": True,
    },
]

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  HELPER: Ä‘á»c / ghi config
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def load_config() -> dict:
    try:
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Lá»c bá» comment key
            clean = {k: v for k, v in raw.items()
                    if not k.startswith("//") and k != "_"}
            if "SERVER_EXE" in clean:
                clean["SERVER_EXE"] = _resolve_server_exe_path(clean.get("SERVER_EXE", ""))
            return _normalize_shared_admin_password(clean)
    except Exception as e:
        messagebox.showerror("Lá»—i Ä‘á»c config", str(e))
    return {}

def save_config(data: dict) -> bool:
    try:
        data = _normalize_shared_admin_password(data)
        if "SERVER_EXE" in data:
            data["SERVER_EXE"] = _resolve_server_exe_path(data.get("SERVER_EXE", ""))
        # Äá»c file gá»‘c Ä‘á»ƒ giá»¯ láº¡i comment keys
        existing = {}
        if os.path.isfile(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        # Cáº­p nháº­t chá»‰ cÃ¡c key tháº­t
        for k, v in data.items():
            existing[k] = v
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        messagebox.showerror("Lá»—i ghi config", str(e))
        return False

def create_new_config():
    path = filedialog.asksaveasfilename(
        initialdir=BASE_DIR,
        initialfile="manager_config.json",
        defaultextension=".json",
        filetypes=[("JSON", "*.json"), ("All", "*.*")],
        title="Táº¡o file config má»›i"
    )
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(CONFIG_TEMPLATE, f, ensure_ascii=False, indent=4)
        messagebox.showinfo("ThÃ nh cÃ´ng", f"ÄÃ£ táº¡o config má»›i:\n{path}")
    except Exception as e:
        messagebox.showerror("Lá»—i", str(e))

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  INSTALLER WINDOW (TÃ­ch há»£p create_server)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class InstallerWindow(tk.Toplevel):
    def __init__(self, parent, on_success=None):
        super().__init__(parent)
        self.on_success = on_success
        self.title("Manager ServerPal â€” Server Installer Wizard")
        self.geometry("720x550")
        self.configure(bg="#0a0a0a")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file = os.path.join(self.base_dir, "manager_config.json")

        self.steamcmd_dir = tk.StringVar(value=r"C:\steamcmd")
        self.install_dir  = tk.StringVar(value=DEFAULT_SERVER_ROOT)
        self.is_installing = False
        try:
            cfg = load_config()
            cur_exe = _resolve_server_exe_path(cfg.get("SERVER_EXE", ""))
            if cur_exe and os.path.isfile(cur_exe):
                self.install_dir.set(os.path.dirname(cur_exe))
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg="#111", pady=15)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸš€  MANAGER SERVERPAL INSTALLER", bg="#111", fg="#00ffcc",
                 font=("Segoe UI", 16, "bold")).pack()

        body = tk.Frame(self, bg="#0a0a0a", padx=20, pady=20)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="1. ThÆ° má»¥c cÃ i SteamCMD:", bg="#0a0a0a", fg="#aaa", font=("Segoe UI", 9)).pack(anchor="w")
        f1 = tk.Frame(body, bg="#0a0a0a")
        f1.pack(fill="x", pady=(2, 10))
        tk.Entry(f1, textvariable=self.steamcmd_dir, bg="#161616", fg="white",
                 bd=0, font=("Consolas", 10), insertbackground="white").pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 5))
        tk.Button(f1, text="ðŸ“‚", bg="#222", fg="white", relief="flat",
                  command=lambda: self._browse(self.steamcmd_dir)).pack(side="left")

        tk.Label(body, text="2. ThÆ° má»¥c cÃ i PalServer:", bg="#0a0a0a", fg="#aaa", font=("Segoe UI", 9)).pack(anchor="w")
        f2 = tk.Frame(body, bg="#0a0a0a")
        f2.pack(fill="x", pady=(2, 15))
        tk.Entry(f2, textvariable=self.install_dir, bg="#161616", fg="white",
                 bd=0, font=("Consolas", 10), insertbackground="white").pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 5))
        tk.Button(f2, text="ðŸ“‚", bg="#222", fg="white", relief="flat",
                  command=lambda: self._browse(self.install_dir)).pack(side="left")

        self.btn_install = tk.Button(body, text="â¬‡  Báº®T Äáº¦U CÃ€I Äáº¶T", bg="#006644", fg="white",
                                     font=("Segoe UI", 11, "bold"), relief="flat", pady=10,
                                     cursor="hand2", command=self._start_install)
        self.btn_install.pack(fill="x", pady=(0, 15))

        tk.Label(body, text="Tiáº¿n trÃ¬nh:", bg="#0a0a0a", fg="#666", font=("Segoe UI", 9)).pack(anchor="w")
        self.console = scrolledtext.ScrolledText(body, bg="#050505", fg="#00ff88",
                                                 font=("Consolas", 9), bd=0, height=12)
        self.console.pack(fill="both", expand=True)

    def _browse(self, var):
        d = filedialog.askdirectory()
        if d: var.set(d)

    def _log(self, msg):
        self.console.insert(tk.END, msg + "\n")
        self.console.see(tk.END)

    def _log_update(self, msg):
        """Cáº­p nháº­t dÃ²ng cuá»‘i (cho hiá»‡u á»©ng progress bar)."""
        if self.console.index("end-1c") != "1.0":
            # XÃ³a dÃ²ng cuá»‘i cÅ©
            self.console.delete("end-2l linestart", "end-1c")
        self.console.insert(tk.END, msg + "\n")
        self.console.see(tk.END)

    def _start_install(self):
        if self.is_installing: return
        self.is_installing = True
        self.btn_install.config(state="disabled", bg="#333")
        self._spin_idx = 0
        self._animate_spin()
        threading.Thread(target=self._process, daemon=True).start()

    def _animate_spin(self):
        if not self.is_installing: return
        chars = ["|", "/", "-", "\\"]
        c = chars[self._spin_idx % 4]
        self.btn_install.config(text=f"â³ {c} ÄANG CÃ€I Äáº¶T...")
        self._spin_idx += 1
        self.after(100, self._animate_spin)

    def _process(self):
        s_dir, p_dir = self.steamcmd_dir.get().strip(), self.install_dir.get().strip()
        s_exe = os.path.join(s_dir, "steamcmd.exe")
        try:
            os.makedirs(s_dir, exist_ok=True); os.makedirs(p_dir, exist_ok=True)
            if not os.path.isfile(s_exe):
                self._log(f"â¬‡ Báº¯t Ä‘áº§u táº£i SteamCMD...")
                zip_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
                zip_path = os.path.join(s_dir, "steamcmd.zip")
                
                # Download with progress
                with urllib.request.urlopen(zip_url) as resp, open(zip_path, 'wb') as f:
                    total = int(resp.info().get('Content-Length', 0))
                    downloaded = 0
                    bs = 8192
                    while True:
                        chunk = resp.read(bs)
                        if not chunk: break
                        downloaded += len(chunk)
                        f.write(chunk)
                        if total:
                            pct = int(downloaded * 100 / total)
                            if pct % 5 == 0: # Update UI every 5%
                                self._log_update(f"â³ Downloading SteamCMD: {pct}%")
                
                self._log("ðŸ“¦ Äang giáº£i nÃ©n SteamCMD...")
                with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(s_dir)
                os.remove(zip_path)
            
            self._log("ðŸš€ Äang cháº¡y SteamCMD Ä‘á»ƒ cÃ i PalServer (2394010)...")
            cmd = [s_exe, "+login", "anonymous", "+force_install_dir", p_dir, "+app_update", "2394010", "validate", "+quit"]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW, bufsize=1)
            
            # Read output real-time char-by-char to capture progress
            cur_line = ""
            while True:
                char = proc.stdout.read(1)
                if not char and proc.poll() is not None: break
                if char == '\n':
                    self._log(cur_line); cur_line = ""
                elif char == '\r':
                    self._log_update(cur_line); cur_line = ""
                else:
                    cur_line += char
            if cur_line: self._log(cur_line)
            proc.wait()
            
            if proc.returncode == 0:
                final_exe = os.path.join(p_dir, "PalServer.exe")
                if not os.path.isfile(final_exe):
                    for r, d, f in os.walk(p_dir):
                        if "PalServer.exe" in f: final_exe = os.path.join(r, "PalServer.exe"); break
                if os.path.isfile(final_exe):
                    self._import_default_palworld_settings(p_dir, final_exe)
                    self._update_config(final_exe, s_exe)
                    self.is_installing = False
                    self.btn_install.config(text="âœ… HOÃ€N Táº¤T - ÄÃ“NG", bg="#004400", command=self.destroy, state="normal")
                    self._log("\n" + "â•"*40)
                    self._log("ðŸŽ‰  CÃ€I Äáº¶T THÃ€NH CÃ”NG!  ðŸŽ‰")
                    self._log(f"ðŸ“‚  Server: {final_exe}")
                    self._log("â•"*40 + "\n")
                    if self.on_success: self.on_success()
                    messagebox.showinfo("ThÃ nh cÃ´ng", "CÃ i Ä‘áº·t vÃ  cáº¥u hÃ¬nh hoÃ n táº¥t!")
                else: self._log("âš ï¸ KhÃ´ng tÃ¬m tháº¥y PalServer.exe!")
            else: self._log(f"âŒ Lá»—i code {proc.returncode}")
        except Exception as e: self._log(f"âŒ Lá»—i: {e}")
        self.is_installing = False
        if self.btn_install['state'] == 'disabled' and self.btn_install['text'] != "âœ… HOÃ€N Táº¤T - ÄÃ“NG":
             self.btn_install.config(text="âŒ THá»¬ Láº I", bg="#660000", state="normal")

    def _update_config(self, exe, steam):
        cfg = load_config(); cfg["SERVER_EXE"] = exe; cfg["STEAMCMD_EXE"] = steam
        save_config(cfg); self._log("âœ… ÄÃ£ cáº­p nháº­t config")

    def _find_default_palworld_settings(self, install_dir: str, server_exe: str) -> str:
        """TÃ¬m DefaultPalWorldSettings.ini trong thÆ° má»¥c cÃ i game."""
        exe_dir = os.path.dirname(server_exe)
        candidates = [
            os.path.join(exe_dir, "Pal", "Saved", "Config", "WindowsServer", "DefaultPalWorldSettings.ini"),
            os.path.join(install_dir, "Pal", "Saved", "Config", "WindowsServer", "DefaultPalWorldSettings.ini"),
            os.path.join(install_dir, "DefaultPalWorldSettings.ini"),
        ]
        for p in candidates:
            if os.path.isfile(p):
                return p
        for root, _, files in os.walk(install_dir):
            if "DefaultPalWorldSettings.ini" in files:
                return os.path.join(root, "DefaultPalWorldSettings.ini")
        return ""

    def _import_default_palworld_settings(self, install_dir: str, server_exe: str) -> bool:
        """Copy DefaultPalWorldSettings.ini -> PalWorldSettings.ini lÃ m cáº¥u hÃ¬nh máº·c Ä‘á»‹nh."""
        src = self._find_default_palworld_settings(install_dir, server_exe)
        if not src:
            self._log("âš ï¸ KhÃ´ng tÃ¬m tháº¥y DefaultPalWorldSettings.ini, bá» qua bÆ°á»›c import máº·c Ä‘á»‹nh.")
            return False

        dst = os.path.join(
            os.path.dirname(server_exe),
            "Pal", "Saved", "Config", "WindowsServer", "PalWorldSettings.ini"
        )
        os.makedirs(os.path.dirname(dst), exist_ok=True)

        if os.path.isfile(dst):
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = f"{dst}.bak_{ts}"
            shutil.copy2(dst, backup)
            self._log(f"ðŸ—‚ï¸ ÄÃ£ backup PalWorldSettings.ini -> {backup}")

        shutil.copy2(src, dst)
        self._log(f"âœ… ÄÃ£ import cáº¥u hÃ¬nh máº·c Ä‘á»‹nh:\n   {src}\n   -> {dst}")
        return True

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  MAIN APP
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class SetupApp:
    BG       = "#0c120d"
    BG2      = "#121a14"
    BG3      = "#17221a"
    ACCENT   = "#66ff88"
    FG       = "#e0e0e0"
    FG_DIM   = "#666"
    ENTRY_BG = "#16213e"
    BTN_OK   = "#0f4c75"
    BTN_WARN = "#7b2d00"
    BTN_RED  = "#5a0000"
    BTN_GRN  = "#003d2e"
    TAB_ACTIVE_GREEN = "#1f6f36"
    TAB_SELECTED_GREEN = "#2f9e44"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Manager ServerPal â€” Setup & Launcher")
        self.root.geometry("920x700")
        self.root.minsize(900, 620)
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)
        self._icon_img = None
        self._bg_photo = None
        self._bg_label = None
        self._bg_source_img = None
        self._tab_bg_refs = {}
        self._apply_window_branding()
        self._serverpal_proc = None
        self._vars: dict[str, tk.StringVar] = {}
        self._auto_pip_running = False
        self._build_ui()
        self._load_to_ui()
        self._latest_update_payload = None
        self._last_ui_bucket = None
        self.root.bind("<Configure>", self._on_root_resize, add="+")
        # Láº§n Ä‘áº§u má»Ÿ setup: tá»± kiá»ƒm tra requirements vÃ  chá»‰ cÃ i cÃ¡c gÃ³i cÃ²n thiáº¿u.
        self.root.after(400, self._auto_install_requirements_if_needed)
        # Auto-check update app (GitHub Releases) náº¿u ngÆ°á»i dÃ¹ng báº­t.
        self.root.after(1600, self._auto_check_app_update_once)

    def _apply_window_branding(self):
        """Náº¡p icon cho app; background image Ä‘ang táº¯t Ä‘á»ƒ giáº£m lag."""
        try:
            if os.path.isfile(UI_ICON_PNG):
                self._icon_img = tk.PhotoImage(file=UI_ICON_PNG)
                self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass
        # Táº¯t ná»n áº£nh Ä‘á»ƒ startup nháº¹ vÃ  á»•n Ä‘á»‹nh hÆ¡n.
        self._bg_source_img = None
        self._bg_photo = None
        self._bg_label = None

    def _attach_tab_background(self, tab_frame):
        """Äáº·t background image trá»±c tiáº¿p vÃ o tá»«ng tab Ä‘á»ƒ luÃ´n nhÃ¬n tháº¥y."""
        # Background image Ä‘Ã£ táº¯t.
        return
        bg_lbl = tk.Label(tab_frame, bd=0)
        bg_lbl.place(x=0, y=0, relwidth=1, relheight=1)
        bg_lbl.lower()
        # Debounce Ä‘á»ƒ trÃ¡nh resize PIL quÃ¡ nhiá»u láº§n khi window/tab Ä‘ang "nhÃºc nhÃ­ch".
        self._tab_bg_refs[tab_frame] = {
            "label": bg_lbl,
            "photo": None,
            "after_id": None,
            "last_size": (0, 0),
        }

        def _refresh_bg(f=tab_frame):
            try:
                if not f.winfo_exists():
                    return
                w = max(int(f.winfo_width()), 200)
                h = max(int(f.winfo_height()), 200)
                # Giá»›i háº¡n size Ä‘á»ƒ giáº£m táº£i khi cá»­a sá»• lá»›n / resize nhiá»u láº§n.
                w = min(w, 1000)
                h = min(h, 800)
                # Skip náº¿u kÃ­ch thÆ°á»›c gáº§n nhÆ° khÃ´ng Ä‘á»•i.
                last_w, last_h = self._tab_bg_refs.get(f, {}).get("last_size", (0, 0))
                if abs(w - last_w) < 20 and abs(h - last_h) < 20:
                    return

                # DÃ¹ng resample nhanh hÆ¡n cho UI (giáº£m lag Ä‘Ã¡ng ká»ƒ).
                img = self._bg_source_img.resize((w, h), Image.BILINEAR)
                ph = ImageTk.PhotoImage(img)
                ref = self._tab_bg_refs.get(f)
                if ref:
                    ref["photo"] = ph
                    ref["label"].config(image=ph)
                    ref["last_size"] = (w, h)
            except Exception:
                pass

        def _on_configure(_e=None, f=tab_frame):
            try:
                ref = self._tab_bg_refs.get(f)
                if not ref:
                    return
                # Cancel previous debounce if exists
                after_id = ref.get("after_id")
                if after_id is not None:
                    try:
                        self.root.after_cancel(after_id)
                    except Exception:
                        pass
                ref["after_id"] = self.root.after(250, _refresh_bg)
            except Exception:
                pass

        tab_frame.bind("<Configure>", _on_configure, add="+")
        # Refresh láº§n Ä‘áº§u (khÃ´ng cáº§n debounce)
        self.root.after(50, _refresh_bg)


    def _parse_requirements(self) -> list[tuple[str, str]]:
        """Tráº£ vá» list (package_name, full_spec) tá»« requirements.txt."""
        reqs: list[tuple[str, str]] = []
        if not os.path.isfile(REQ_FILE):
            return reqs
        try:
            with open(REQ_FILE, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Cáº¯t pháº§n marker/comment inline Ä‘Æ¡n giáº£n.
                    line = line.split(" #", 1)[0].strip()
                    # TÃ¡ch tÃªn package trÆ°á»›c version operators.
                    pkg = re.split(r"[<>=!~\[\];\s]", line, maxsplit=1)[0].strip()
                    if pkg:
                        reqs.append((pkg, line))
        except Exception as e:
            self._log(f"âš ï¸ KhÃ´ng Ä‘á»c Ä‘Æ°á»£c requirements.txt: {e}")
        return reqs

    def _get_python_exec(self, ensure_venv: bool = False) -> str:
        """Æ¯u tiÃªn Python trong .venv cá»§a project; fallback sys.executable."""
        is_frozen = bool(getattr(sys, "frozen", False))
        if os.path.isfile(VENV_PYTHON):
            # VENV_PYTHON cÃ³ thá»ƒ lÃ  venv "há»ng" (trá» vá» base python Ä‘Ã£ bá»‹ xoÃ¡/di chuyá»ƒn),
            # vÃ­ dá»¥ khi cháº¡y sáº½ in "No Python at '...'" vÃ  exit code != 0.
            try:
                r = subprocess.run(
                    [VENV_PYTHON, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                if r.returncode == 0:
                    return VENV_PYTHON
            except Exception:
                pass
            # Náº¿u venv python khÃ´ng cháº¡y Ä‘Æ°á»£c: dá»n venv cÅ© Ä‘á»ƒ táº¡o láº¡i.
            try:
                self._log("âš ï¸ .venv cÅ© khÃ´ng há»£p lá»‡ â€” Ä‘ang xÃ³a vÃ  táº¡o láº¡i...")
            except Exception:
                pass
            try:
                shutil.rmtree(VENV_DIR, ignore_errors=True)
            except Exception:
                pass

        def _norm(p: str) -> str:
            return str(p).strip().strip('"').strip("'")

        def _resolve_base_python_exec() -> str:
            cand = []
            # 1) sys.executable chá»‰ dÃ¹ng khi cháº¡y dáº¡ng .py (khÃ´ng dÃ¹ng khi frozen .exe)
            if not is_frozen:
                cand.append(_norm(sys.executable))
            # 2) python.exe trong PATH
            try:
                p = shutil.which("python")
                if p:
                    cand.append(_norm(p))
            except Exception:
                pass

            # 3) CÃ¡c Ä‘Æ°á»ng dáº«n cÃ i Ä‘áº·t Python thÃ´ng dá»¥ng (Windows)
            try:
                cand.extend(glob.glob(r"C:\Program Files\Python*\python.exe"))
            except Exception:
                pass
            try:
                # VÃ­ dá»¥: C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe
                cand.extend(glob.glob(r"C:\Users\*\AppData\Local\Programs\Python\Python*\python.exe"))
            except Exception:
                pass

            # Pick first existing
            for p in cand:
                if p and os.path.isfile(p):
                    return p
            # Fallback cuá»‘i:
            # - cháº¡y .py: giá»¯ sys.executable
            # - cháº¡y .exe: tráº£ rá»—ng Ä‘á»ƒ caller xá»­ lÃ½ (trÃ¡nh tá»± gá»i láº¡i chÃ­nh file .exe)
            if not is_frozen:
                return _norm(sys.executable)
            return ""

        base_python = _resolve_base_python_exec()

        if not ensure_venv:
            return base_python
        if not base_python:
            self._log("âŒ KhÃ´ng tÃ¬m tháº¥y Python interpreter há»‡ thá»‘ng Ä‘á»ƒ táº¡o .venv.")
            return ""
        try:
            self._log("ðŸ Äang táº¡o Python virtual environment (.venv)...")
            # DÃ¹ng base_python Ä‘Ã£ dÃ² Ä‘Æ°á»£c Ä‘á»ƒ trÃ¡nh trÆ°á»ng há»£p sys.executable trá» tá»›i path Ä‘Ã£ bá»‹ xÃ³a.
            subprocess.run([base_python, "-m", "venv", VENV_DIR], check=True, timeout=180)
            if os.path.isfile(VENV_PYTHON):
                self._log(f"âœ… ÄÃ£ táº¡o venv: {VENV_DIR}")
                return VENV_PYTHON
        except Exception as e:
            self._log(f"âš ï¸ Táº¡o venv lá»—i, fallback Python base: {e}")
        return base_python

    def _get_missing_requirements(self, python_exec: str) -> list[str]:
        """Láº¥y danh sÃ¡ch requirement specs cÃ²n thiáº¿u cÃ i Ä‘áº·t."""
        missing: list[str] = []
        for pkg_name, full_spec in self._parse_requirements():
            try:
                r = subprocess.run(
                    [python_exec, "-m", "pip", "show", pkg_name],
                    capture_output=True, text=True, timeout=10
                )
                if r.returncode != 0:
                    missing.append(full_spec)
            except Exception:
                # Náº¿u lá»—i kiá»ƒm tra, váº«n xem nhÆ° thiáº¿u Ä‘á»ƒ pip xá»­ lÃ½.
                missing.append(full_spec)
        return missing

    def _auto_install_requirements_if_needed(self):
        """Auto cÃ i pip packages cÃ²n thiáº¿u khi má»Ÿ setup.py láº§n Ä‘áº§u."""
        if IS_FROZEN_APP:
            # Báº£n phÃ¡t hÃ nh EXE cho end-user: khÃ´ng yÃªu cáº§u Python/pip trÃªn mÃ¡y Ä‘Ã­ch.
            self._log("â„¹ï¸ Báº£n Ä‘Ã³ng gÃ³i: bá» qua auto-install Python packages.")
            return
        if self._auto_pip_running:
            return
        if not os.path.isfile(REQ_FILE):
            return

        py_exec = self._get_python_exec(ensure_venv=True)
        # TrÃ¡nh lá»—i do quote/whitespace láº¡ trong Ä‘Æ°á»ng dáº«n python
        py_exec = str(py_exec).strip().strip('"').strip("'")
        if not py_exec:
            self._log("âš ï¸ Bá» qua auto-install: chÆ°a tÃ¬m tháº¥y Python há»‡ thá»‘ng.")
            return
        missing = self._get_missing_requirements(py_exec)
        if not missing:
            self._log("âœ… Python packages Ä‘Ã£ Ä‘á»§, bá» qua auto-install.")
            return

        self._auto_pip_running = True
        self._log("ðŸ“¦ PhÃ¡t hiá»‡n package cÃ²n thiáº¿u, báº¯t Ä‘áº§u auto-install...")
        self._log("   Missing: " + ", ".join(missing))

        cmd = [py_exec, "-m", "pip", "install", "--disable-pip-version-check", *missing]
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"

        def _run():
            try:
                self._run_cmd_bg(cmd, env=env)
            finally:
                self._auto_pip_running = False

        threading.Thread(target=_run, daemon=True).start()

    # â”€â”€ Build UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg="#0d0d1a", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="âš™  Manager ServerPal â€” Setup & Launcher",
                 bg="#0d0d1a", fg=self.ACCENT,
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)
        tk.Label(hdr, text="PhiÃªn báº£n v1.0.2 by MityTinDev",
                 bg="#0d0d1a", fg=self.FG_DIM,
                 font=("Segoe UI", 9)).pack(side="right", padx=16)

        # Notebook
        self._style = ttk.Style()
        self._style.configure("S.TNotebook",     background=self.BG, borderwidth=0)
        self._style.configure("S.TNotebook.Tab", background="#eef3ee",
                        foreground="#111111", padding=[16, 7],
                        font=("Segoe UI", 10, "bold"))
        self._style.map("S.TNotebook.Tab",
                  background=[
                      ("selected", self.TAB_SELECTED_GREEN),
                      ("active", self.TAB_ACTIVE_GREEN),
                  ],
                  foreground=[
                      ("selected", "#101010"),
                      ("active", "#101010"),
                  ])
        self._style.configure("Green.Vertical.TScrollbar",
                        background="#2f9e44",
                        troughcolor="#111",
                        arrowcolor="#d8ffe0",
                        bordercolor="#1b5e20",
                        lightcolor="#2f9e44",
                        darkcolor="#1f6f36")
        self._style.map("Green.Vertical.TScrollbar",
                  background=[("active", "#66bb6a"), ("!active", "#2f9e44")])

        nb = ttk.Notebook(self.root, style="S.TNotebook")
        nb.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        # â”€â”€ Tab 1: Khá»Ÿi cháº¡y (báº£ng Ä‘iá»u khiá»ƒn) â”€
        tab_run = tk.Frame(nb, bg=self.BG)
        self._attach_tab_background(tab_run)
        nb.add(tab_run, text="  Khá»Ÿi cháº¡y  ")
        self._build_tab_with_scroll(tab_run, self._build_launch_tab)

        # â”€â”€ Tab 2: Táº¡o server (tab chÃ­nh, chá»©a tab con) â”€
        tab_setup_main = tk.Frame(nb, bg=self.BG)
        self._attach_tab_background(tab_setup_main)
        nb.add(tab_setup_main, text="  Táº¡o server & Cáº¥u HÃ¬nh ")

        sub_style = ttk.Style()
        sub_style.configure("Sub.TNotebook", background=self.BG2, borderwidth=0)
        sub_style.configure("Sub.TNotebook.Tab",
                            background="#d7e5d7", foreground="#111111",
                            padding=[12, 5], font=("Segoe UI", 9, "bold"))
        sub_style.map("Sub.TNotebook.Tab",
                      background=[("selected", "#86d89f"), ("active", "#bfeecb")],
                      foreground=[("selected", "#101010"), ("active", "#101010")])

        sub_nb = ttk.Notebook(tab_setup_main, style="Sub.TNotebook")
        sub_nb.pack(fill="both", expand=True, padx=8, pady=8)

        sub_tab_setup = tk.Frame(sub_nb, bg=self.BG)
        self._attach_tab_background(sub_tab_setup)
        sub_nb.add(sub_tab_setup, text="  Táº¡o server  ")
        self._build_tab_with_scroll(sub_tab_setup, self._build_server_setup_tab)

        sub_tab_cfg = tk.Frame(sub_nb, bg=self.BG)
        self._attach_tab_background(sub_tab_cfg)
        sub_nb.add(sub_tab_cfg, text="  Cáº¥u hÃ¬nh  ")
        self._build_tab_with_scroll(sub_tab_cfg, self._build_config_tab)

        sub_tab_mods = tk.Frame(sub_nb, bg=self.BG)
        self._attach_tab_background(sub_tab_mods)
        sub_nb.add(sub_tab_mods, text="  Mods  ")
        self._build_tab_with_scroll(sub_tab_mods, self._build_mods_tab)

        sub_tab_upd = tk.Frame(sub_nb, bg=self.BG)
        self._attach_tab_background(sub_tab_upd)
        sub_nb.add(sub_tab_upd, text="  Cáº­p nháº­t  ")
        self._build_tab_with_scroll(sub_tab_upd, self._build_update_tab)

        # â”€â”€ Tab 3: CÃ i Ä‘áº·t (Ä‘áº·t cuá»‘i) â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tab_ins = tk.Frame(nb, bg=self.BG)
        self._attach_tab_background(tab_ins)
        nb.add(tab_ins, text="  CÃ i Ä‘áº·t  ")
        self._build_tab_with_scroll(tab_ins, self._build_install_tab)

        # Console chung (bottom)
        self._build_console()

    def _on_root_resize(self, _event=None):
        """Responsive tab menu: giá»¯ tab luÃ´n dá»… Ä‘á»c khi Ä‘á»•i kÃ­ch thÆ°á»›c cá»­a sá»•."""
        try:
            w = self.root.winfo_width()
        except Exception:
            return
        # Chia theo bucket Ä‘á»ƒ trÃ¡nh reconfigure quÃ¡ nhiá»u láº§n khi drag resize.
        if w >= 1200:
            bucket = "lg"
            font = ("Segoe UI", 10, "bold")
            pad = [16, 7]
        elif w >= 980:
            bucket = "md"
            font = ("Segoe UI", 9, "bold")
            pad = [12, 6]
        else:
            bucket = "sm"
            font = ("Segoe UI", 8, "bold")
            pad = [8, 4]
        if bucket == self._last_ui_bucket:
            return
        self._last_ui_bucket = bucket
        try:
            self._style.configure("S.TNotebook.Tab", font=font, padding=pad)
            self._style.configure("Sub.TNotebook.Tab", font=font, padding=pad)
        except Exception:
            pass

    # â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _scrollable(self, parent) -> tk.Frame:
        wrap = tk.Frame(parent, bg=self.BG)
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, bg=self.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview,
                            style="Green.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=self.BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(
            win_id, width=e.width))
        inner.bind("<MouseWheel>", lambda e: canvas.yview_scroll(
            -1 if e.delta > 0 else 1, "units"))
        return inner

    def _build_tab_with_scroll(self, parent, build_fn):
        """Bá»c toÃ n bá»™ tab trong vÃ¹ng cuá»™n Ä‘á»ƒ dÃ¹ng Ä‘Æ°á»£c khi cá»­a sá»• thu nhá»."""
        wrap = tk.Frame(parent, bg=self.BG)
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, bg=self.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview,
                            style="Green.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=self.BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        # Cuá»™n chuá»™t chá»‰ khi con trá» Ä‘ang á»Ÿ trong tab Ä‘Ã³.
        def _bind_wheel(_e=None):
            canvas.bind_all("<MouseWheel>", _on_wheel)
        def _unbind_wheel(_e=None):
            canvas.unbind_all("<MouseWheel>")
        def _on_wheel(e):
            canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")

        canvas.bind("<Enter>", _bind_wheel)
        canvas.bind("<Leave>", _unbind_wheel)
        inner.bind("<Enter>", _bind_wheel)
        inner.bind("<Leave>", _unbind_wheel)

        build_fn(inner)

    def _section(self, parent, title: str) -> tk.Frame:
        tk.Label(parent, text=title, bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=14, pady=(14, 2))
        sep = tk.Frame(parent, bg="#1a2a3a", height=1)
        sep.pack(fill="x", padx=14, pady=(0, 6))
        f = tk.Frame(parent, bg=self.BG2, padx=14, pady=10)
        f.pack(fill="x", padx=14, pady=(0, 4))
        return f

    def _field(self, parent, row: int, key: str, label: str,
               note: str = "", show: str = "", browse: str = ""):
        tk.Label(parent, text=label, bg=self.BG2, fg=self.FG,
                 font=("Segoe UI", 9), width=28, anchor="e"
                 ).grid(row=row, column=0, sticky="e", padx=(0, 8), pady=3)
        var = tk.StringVar()
        self._vars[key] = var
        entry_kw = dict(textvariable=var, bg=self.ENTRY_BG, fg=self.FG,
                        bd=0, font=("Consolas", 9),
                        insertbackground=self.ACCENT,
                        relief="flat")
        if show:
            entry_kw["show"] = show
        e = tk.Entry(parent, **entry_kw, width=52)
        e.grid(row=row, column=1, sticky="ew", ipady=5, padx=(0, 4))
        if show:
            is_hidden = tk.BooleanVar(value=True)
            def _toggle_pw():
                hidden = is_hidden.get()
                e.config(show="" if hidden else show)
                eye_btn.config(text="ðŸ™ˆ" if hidden else "ðŸ‘")
                is_hidden.set(not hidden)
            eye_btn = tk.Button(parent, text="ðŸ‘", bg="#1a1a2e", fg="#aaa",
                                relief="flat", padx=6, command=_toggle_pw)
            eye_btn.grid(row=row, column=2, padx=(0, 4))
        parent.columnconfigure(1, weight=1)
        if browse:
            def _browse(b=browse, v=var):
                if b == "file":
                    p = filedialog.askopenfilename()
                else:
                    p = filedialog.askdirectory()
                if p:
                    v.set(p)
            tk.Button(parent, text="ðŸ“‚", bg="#1a1a2e", fg="#aaa",
                      relief="flat", padx=6, command=_browse
                      ).grid(row=row, column=3 if show else 2, padx=(0, 4))
        if note:
            tk.Label(parent, text=note, bg=self.BG2, fg=self.FG_DIM,
                     font=("Segoe UI", 8)
                     ).grid(row=row, column=(4 if (browse and show) else
                                              3 if (browse or show) else 2),
                            sticky="w", padx=4)

    # â”€â”€ Tab Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_config_tab(self, parent):
        toolbar = tk.Frame(parent, bg=self.BG, pady=6)
        toolbar.pack(fill="x", padx=14)
        tk.Button(toolbar, text="ðŸ’¾  LÆ°u cáº¥u hÃ¬nh",
                  bg=self.BTN_OK, fg="white", relief="flat",
                  padx=16, pady=6, font=("Segoe UI", 10, "bold"),
                  cursor="hand2", command=self._save
                  ).pack(side="left", padx=(0, 8))
        tk.Button(toolbar, text="ðŸ”„  Táº£i láº¡i tá»« file",
                  bg="#2a2a2a", fg="#aaa", relief="flat",
                  padx=12, pady=6, font=("Segoe UI", 9),
                  cursor="hand2", command=self._load_to_ui
                  ).pack(side="left", padx=(0, 8))
        tk.Button(toolbar, text="ðŸ†•  Táº¡o config má»›i",
                  bg="#2a1a0a", fg="#ff9900", relief="flat",
                  padx=12, pady=6, font=("Segoe UI", 9),
                  cursor="hand2", command=create_new_config
                  ).pack(side="left")
        tk.Button(toolbar, text="ðŸ“¥  Äá»“ng bá»™ INI tá»« manager",
                  bg="#1a3a1a", fg="#aaff77", relief="flat",
                  padx=12, pady=6, font=("Segoe UI", 9),
                  cursor="hand2", command=self._sync_manager_ini_to_game
                  ).pack(side="left", padx=(8, 0))

        # Tab Ä‘Ã£ Ä‘Æ°á»£c bá»c scroll tá»« ngoÃ i, trÃ¡nh scroll lá»“ng nhau.
        inner = parent

        # [1] Server
        s = self._section(inner, "  [1]  ðŸ–¥ï¸  Server")
        self._field(s, 0, "SERVER_EXE", "PalServer.exe", browse="file",
                    note="Táº¥t cáº£ path PalServer tá»± tÃ­nh tá»« Ä‘Ã¢y")
        # PalWorldSettings.ini â€” tá»± derive, hiá»ƒn thá»‹ read-only
        tk.Label(s, text="PalWorldSettings.ini", bg=self.BG2, fg=self.FG_DIM,
                 font=("Segoe UI", 9), width=28, anchor="e"
                 ).grid(row=1, column=0, sticky="e", padx=(0, 8), pady=3)
        self._lbl_ini_path = tk.Label(s,
                 text="â¬† tá»± tÃ­nh: <SERVER_EXE_DIR>\\Pal\\Saved\\Config\\WindowsServer\\PalWorldSettings.ini",
                 bg=self.BG2, fg="#444", font=("Consolas", 7), anchor="w")
        self._lbl_ini_path.grid(row=1, column=1, sticky="ew", columnspan=3, pady=3)
        # Cáº­p nháº­t label khi SERVER_EXE thay Ä‘á»•i
        self._vars["SERVER_EXE"].trace_add("write", lambda *_: self._update_ini_label())

        # [2] REST API
        s = self._section(inner, "  [2]  ðŸŒ  REST API")
        self._field(s, 0, "API_URL",   "API URL",        note="Máº·c Ä‘á»‹nh: http://127.0.0.1:8212/v1/api")
        self._field(s, 1, "ADMIN_PASSWORD", "Admin Password", show="*",
                    note="DÃ¹ng chung cho REST API + RCON")
        self._field(s, 2, "RESTAPI_ENABLED", "REST API Enabled",
                    note="true/false (Ä‘á»“ng bá»™ vÃ o RESTAPIEnabled)")

        # [3] RCON
        s = self._section(inner, "  [3]  ðŸ”Œ  RCON")
        self._field(s, 0, "RCON_HOST",     "Host",     note="127.0.0.1 náº¿u local")
        self._field(s, 1, "RCON_PORT",     "Port",     note="RCONPort (máº·c Ä‘á»‹nh 25575)")
        self._field(s, 2, "RCON_ENABLED",  "RCON Enabled",
                    note="true/false (Ä‘á»“ng bá»™ vÃ o RCONEnabled)")
        self._field(s, 3, "PUBLIC_PORT",   "Public Port",
                    note="PublicPort community server (máº·c Ä‘á»‹nh 8211)")
        self._field(s, 4, "QUERY_PORT",    "Query Port",
                    note="QueryPort (máº·c Ä‘á»‹nh 27015)")
        tk.Label(s, text="RCON Password",
                 bg=self.BG2, fg=self.FG_DIM,
                 font=("Segoe UI", 9), width=28, anchor="e"
                 ).grid(row=5, column=0, sticky="e", padx=(0, 8), pady=3)
        tk.Label(s, text="â†³ dÃ¹ng chung vá»›i AdminPassword á»Ÿ má»¥c REST API",
                 bg=self.BG2, fg="#777", font=("Segoe UI", 8), anchor="w"
                 ).grid(row=5, column=1, sticky="w", pady=3)
        self._field(s, 6, "SHOW_PLAYER_LIST", "Show Player List",
                    note="true/false (Ä‘á»“ng bá»™ vÃ o bShowPlayerList)")

        # [4] PalDefender
        s = self._section(inner, "  [4]  ðŸ›¡ï¸  PalDefender API")
        self._field(s, 0, "PALDEF_API_BASE", "API Base URL",
                    note="Máº·c Ä‘á»‹nh: http://127.0.0.1:17993")

        # [5] Discord Webhooks
        s = self._section(inner, "  [5]  ðŸŸ£  Discord â€” Webhooks")
        self._field(s, 0, "DISCORD_WEBHOOK_URL",  "General Webhook",  note="ThÃ´ng bÃ¡o chung (Ä‘á»ƒ trá»‘ng = táº¯t)")
        self._field(s, 1, "ANTIBUG_WEBHOOK_URL",  "Antibug Webhook",  note="KÃªnh admin: AntiBug + Cheat alert")
        self._field(s, 2, "PLAYER_CONNECT_WEBHOOK_URL", "Player Connect Webhook",
                    note="Gá»­i join/leave ngÆ°á»i chÆ¡i (webhook docs): https://discord.com/developers/docs/resources/webhook")

        # [6] Bot 1
        s = self._section(inner, "  [6]  ðŸ¤–  Bot 1 (Má»“m LÃ¨o) â€” Chat Bridge 2 chiá»u")
        self._field(s, 0, "DISCORD_CHAT_WEBHOOK", "Chat Webhook (Ingame â†’ Discord)",
                    note="Webhook nháº­n chat tá»« ingame (webhook docs): https://discord.com/developers/docs/resources/webhook")
        self._field(s, 1, "DISCORD_BOT_TOKEN", "Bot 1 Token (Má»“m LÃ¨o)", show="*",
                    note="discord.com/developers â†’ Applications â†’ Bot â†’ Token (báº­t Message Content Intent náº¿u cáº§n): https://discord.com/developers/applications")
        self._field(s, 2, "DISCORD_CHAT_CHANNEL_ID", "Channel ID (Bot 1 - Má»“m LÃ¨o)",
                    note="Chuá»™t pháº£i kÃªnh Discord â†’ Copy Channel ID")

        # [7] Bot 2
        s = self._section(inner, "  [7]  ðŸ¤–  Bot 2 (Cá» HÃ³) â€” Commands & Features")
        self._field(s, 0, "RANKING_WEBHOOK_URL", "ðŸ† Ranking Webhook (Bot 2)",
                    note="Webhook gá»­i báº£ng xáº¿p háº¡ng (webhook docs): https://discord.com/developers/docs/resources/webhook")
        self._field(s, 1, "DISCORD_BOT2_TOKEN", "Bot 2 Token (Cá» HÃ³)", show="*",
                    note="Báº­t Message Content Intent náº¿u bot cÃ³ xá»­ lÃ½ message: https://discord.com/developers/applications")
        self._field(s, 2, "DISCORD_BOT2_CHANNEL_ID", "Bot 2 Channel ID",
                    note="Chuá»™t pháº£i kÃªnh Discord â†’ Copy Channel ID")
        self._field(s, 3, "DISCORD_BOT2_RANKING_CHANNEL_ID", "Bot 2 Ranking Channel ID",
                    note="KÃªnh riÃªng Ä‘á»ƒ Ä‘Äƒng báº£ng xáº¿p háº¡ng Bot 2")
        self._field(s, 4, "DISCORD_BOT2_LIVEMAP_CHANNEL_ID", "Bot 2 LiveMap Channel ID (tuá»³ chá»n)",
                    note="Náº¿u bá» trá»‘ng: bot2 fallback vá» DISCORD_BOT2_CHANNEL_ID")
        self._field(s, 5, "DISCORD_BOT2_NAME", "Bot 2 Name",
                    note="TÃªn hiá»ƒn thá»‹ cá»§a Bot 2 trong app (máº·c Ä‘á»‹nh: Cá» HÃ³)")

        # [8] AntiBug
        s = self._section(inner, "  [8]  ðŸ¤–  AntiBug Auto-Kick / Ban")
        self._field(s, 0, "ANTIBUG_MAX_KICKS",   "Max Kicks",      note="Sá»‘ vi pháº¡m â†’ BAN vÄ©nh viá»…n (máº·c Ä‘á»‹nh: 3)")
        self._field(s, 1, "ANTIBUG_KICK_WINDOW", "Kick Window (s)", note="Cá»­a sá»• thá»i gian giÃ¢y (máº·c Ä‘á»‹nh: 300)")

        # [8] SteamCMD
        s = self._section(inner, "  [8]  ðŸ”§  SteamCMD (Update Server)")
        self._field(s, 0, "STEAMCMD_EXE", "SteamCMD.exe", browse="file",
                    note="ÄÆ°á»ng dáº«n Ä‘áº¿n steamcmd.exe")

        # [9] App Update
        s = self._section(inner, "  [9]  ðŸ§©  App Update (GitHub)")
        self._field(s, 0, "GITHUB_REPO", "GitHub Repo (owner/repo)",
                    note="VÃ­ dá»¥: mitytindev/manager-serverpal")
        self._field(s, 1, "AUTO_UPDATE_CHECK", "Auto Check Update",
                    note="true/false (chá»‰ tá»± kiá»ƒm tra phiÃªn báº£n, khÃ´ng tá»± táº£i/cÃ i)")

    # â”€â”€ Tab Launch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_launch_tab(self, parent):
        center = tk.Frame(parent, bg=self.BG)
        center.pack(expand=True, fill="both", padx=40, pady=20)

        tk.Label(
            center,
            text="â–¶ KHá»žI Äá»˜NG SERVERPAL",
            bg=self.BG,
            fg=self.ACCENT,
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(20, 6))
        tk.Label(
            center,
            text="Pháº§n má»m quáº£n lÃ½ server Palworld â€¢ Manager ServerPal â€¢ v1.0.2 by MityTinDev",
            bg=self.BG,
            fg=self.FG_DIM,
            font=("Segoe UI", 9),
        ).pack(pady=(0, 14))

        # Card: ThÃ´ng tin + tráº¡ng thÃ¡i
        info_card = tk.Frame(center, bg="#0a0f1a", padx=16, pady=14)
        info_card.pack(fill="x", padx=10, pady=(0, 18))

        self._lbl_run_status = tk.Label(
            info_card, text="â— ChÆ°a cháº¡y",
            bg="#0a0f1a", fg="#ff5555",
            font=("Segoe UI", 11, "bold"),
        )
        self._lbl_run_status.pack(anchor="w")

        tk.Label(
            info_card,
            text="Tiáº¿n trÃ¬nh Ä‘iá»u khiá»ƒn: Controller ServerPal",
            bg="#0a0f1a",
            fg="#93c5fd",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(10, 0))

        # Card: NÃºt Ä‘iá»u khiá»ƒn
        btn_card = tk.Frame(center, bg="#0a0a0a", padx=12, pady=12)
        btn_card.pack(fill="x", padx=10, pady=(0, 16))

        btn_card.grid_columnconfigure(0, weight=1)
        btn_card.grid_columnconfigure(1, weight=1)
        btn_card.grid_columnconfigure(2, weight=1)

        self._btn_start = tk.Button(
            btn_card,
            text="â–¶ Start",
            bg="#003d2e",
            fg="#00ffcc",
            relief="flat",
            padx=0,
            pady=12,
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            command=self._launch_serverpal,
        )
        self._btn_start.grid(row=0, column=0, sticky="ew", padx=8)

        self._btn_restart = tk.Button(
            btn_card,
            text="ðŸ”„ Restart",
            bg="#2a2a2a",
            fg="#ff9900",
            relief="flat",
            padx=0,
            pady=12,
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            command=self._restart_serverpal,
        )
        self._btn_restart.grid(row=0, column=1, sticky="ew", padx=8)

        self._btn_stop = tk.Button(
            btn_card,
            text="â¹ Stop",
            bg=self.BTN_RED,
            fg="#ff6666",
            relief="flat",
            padx=0,
            pady=12,
            font=("Segoe UI", 12, "bold"),
            cursor="hand2",
            state="disabled",
            command=self._stop_serverpal,
        )
        self._btn_stop.grid(row=0, column=2, sticky="ew", padx=8)

        # Giá»›i thiá»‡u chá»©c nÄƒng app
        tk.Label(
            center,
            text="á»¨ng dá»¥ng quáº£n lÃ½ server Palworld: khá»Ÿi cháº¡y báº£ng Ä‘iá»u khiá»ƒn, cáº¥u hÃ¬nh nhanh App/INI, cÃ i mÃ´i trÆ°á»ng vÃ  cáº­p nháº­t SteamCMD.",
            bg=self.BG,
            fg=self.FG_DIM,
            font=("Segoe UI", 9),
            justify="center",
            wraplength=820,
        ).pack(pady=(6, 6))
        tk.Label(
            center,
            text="PhÃ¡t triá»ƒn bá»Ÿi láº­p trÃ¬nh viÃªn MityTinDev â€¢ PhiÃªn báº£n v1.0.2 by MityTinDev",
            bg=self.BG,
            fg="#9aa0a6",
            font=("Segoe UI", 9, "italic"),
        ).pack(pady=(0, 6))

    # â”€â”€ Tab Update â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_update_tab(self, parent):
        inner = tk.Frame(parent, bg=self.BG)
        inner.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(inner, text="â¬†  Cáº­p Nháº­t RiÃªng Biá»‡t",
                 bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 16, "bold")).pack(pady=(10, 4))
        tk.Label(inner,
                 text="TÃ¡ch riÃªng: Update game PalServer vÃ  Update SteamCMD",
                 bg=self.BG, fg=self.FG_DIM,
                 font=("Segoe UI", 9)).pack(pady=(0, 20))

        # Game update info
        info = tk.Frame(inner, bg=self.BG3, padx=16, pady=12)
        info.pack(fill="x", pady=(0, 16))
        tk.Label(info, text="App ID Palworld Dedicated Server:  2394010",
                 bg=self.BG3, fg=self.FG, font=("Consolas", 10)).pack(anchor="w")
        tk.Label(info,
                 text="Lá»‡nh: steamcmd.exe +login anonymous +app_update 2394010 validate +quit",
                 bg=self.BG3, fg="#888", font=("Consolas", 8)).pack(anchor="w", pady=(4, 0))

        # Buttons
        btn_f = tk.Frame(inner, bg=self.BG)
        btn_f.pack(pady=10)

        tk.Button(btn_f, text="ðŸŽ®  Update Game PalServer",
                  bg="#1a0050", fg="#aa88ff",
                  relief="flat", padx=20, pady=10,
                  font=("Segoe UI", 11, "bold"), cursor="hand2",
                  command=self._run_game_update
                  ).grid(row=0, column=0, padx=8, pady=4)

        tk.Button(btn_f, text="ðŸ”„  Validate / Sá»­a file há»ng",
                  bg="#2a1a00", fg="#ff9900",
                  relief="flat", padx=20, pady=10,
                  font=("Segoe UI", 10), cursor="hand2",
                  command=self._run_game_validate
                  ).grid(row=0, column=1, padx=8, pady=4)

        tk.Button(btn_f, text="ðŸ“‚  Má»Ÿ thÆ° má»¥c SteamCMD",
                  bg="#1a1a1a", fg="#aaa",
                  relief="flat", padx=20, pady=10,
                  font=("Segoe UI", 10), cursor="hand2",
                  command=self._open_steamcmd_dir
                  ).grid(row=1, column=0, padx=8, pady=4)

        tk.Button(btn_f, text="ðŸ“¥  Táº£i SteamCMD (má»Ÿ web)",
                  bg="#1a1a1a", fg="#7289da",
                  relief="flat", padx=20, pady=10,
                  font=("Segoe UI", 10), cursor="hand2",
                  command=lambda: __import__("webbrowser").open(
                      "https://developer.valvesoftware.com/wiki/SteamCMD")
                  ).grid(row=1, column=1, padx=8, pady=4)

        tk.Button(btn_f, text="ðŸ›   Update SteamCMD tá»± Ä‘á»™ng",
                  bg="#003355", fg="#66ccff",
                  relief="flat", padx=20, pady=10,
                  font=("Segoe UI", 10, "bold"), cursor="hand2",
                  command=self._run_steamcmd_update
                  ).grid(row=2, column=0, columnspan=2, padx=8, pady=(10, 4), sticky="ew")

        tk.Frame(inner, bg="#2a2a2a", height=1).pack(fill="x", pady=16)
        tk.Label(inner, text="ðŸ§©  Cáº­p nháº­t á»©ng dá»¥ng (GitHub Releases)",
                 bg=self.BG, fg=self.ACCENT, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(inner,
                 text="Nháº­p repo dáº¡ng owner/repo, vÃ­ dá»¥: mitytindev/manager-serverpal",
                 bg=self.BG, fg=self.FG_DIM, font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 8))

        repo_row = tk.Frame(inner, bg=self.BG)
        repo_row.pack(fill="x", pady=(0, 8))
        tk.Label(repo_row, text="GitHub repo:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9), width=14, anchor="e").pack(side="left")
        if "GITHUB_REPO" not in self._vars:
            self._vars["GITHUB_REPO"] = tk.StringVar()
        tk.Entry(repo_row, textvariable=self._vars["GITHUB_REPO"], bg=self.ENTRY_BG, fg=self.FG,
                 bd=0, font=("Consolas", 9), insertbackground=self.ACCENT).pack(
                    side="left", fill="x", expand=True, ipady=5, padx=(6, 0))

        up_btn = tk.Frame(inner, bg=self.BG)
        up_btn.pack(fill="x", pady=(0, 6))
        tk.Button(up_btn, text="ðŸ”Ž Kiá»ƒm tra update app",
                  bg="#1f3b66", fg="#9dd1ff",
                  relief="flat", padx=14, pady=8,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  command=self._check_app_update
                  ).pack(side="left", padx=(0, 8))
        tk.Button(up_btn, text="â¬‡ Táº£i & cÃ i báº£n má»›i",
                  bg="#0f4c75", fg="white",
                  relief="flat", padx=14, pady=8,
                  font=("Segoe UI", 9, "bold"), cursor="hand2",
                  command=self._install_latest_update
                  ).pack(side="left", padx=(0, 8))
        tk.Button(up_btn, text="ðŸŒ Má»Ÿ trang Releases",
                  bg="#2a2a2a", fg="#aaa",
                  relief="flat", padx=14, pady=8,
                  font=("Segoe UI", 9), cursor="hand2",
                  command=self._open_repo_releases
                  ).pack(side="left")

        self._lbl_update_status = tk.Label(inner, text=f"PhiÃªn báº£n hiá»‡n táº¡i: {APP_VERSION}",
                                           bg=self.BG, fg="#8ab4f8",
                                           font=("Consolas", 9))
        self._lbl_update_status.pack(anchor="w", pady=(4, 0))

        tk.Frame(inner, bg="#222", height=1).pack(fill="x", pady=16)
        tk.Label(inner, text="SteamCMD.exe Ä‘ang dÃ¹ng:",
                 bg=self.BG, fg=self.FG_DIM, font=("Segoe UI", 9)).pack(anchor="w")
        self._lbl_steamcmd_path = tk.Label(inner, text="(chÆ°a cáº¥u hÃ¬nh)",
                                           bg=self.BG, fg="#888",
                                           font=("Consolas", 8))
        self._lbl_steamcmd_path.pack(anchor="w", pady=(2, 0))

    # â”€â”€ Tab Install â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_install_tab(self, parent):
        inner = tk.Frame(parent, bg=self.BG)
        inner.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(inner, text="ðŸ“¦  CÃ i Äáº·t MÃ´i TrÆ°á»ng",
                 bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 16, "bold")).pack(pady=(10, 4))
        tk.Label(inner,
                 text="CÃ i Python packages vÃ  Node.js packages cáº§n thiáº¿t Ä‘á»ƒ cháº¡y app",
                 bg=self.BG, fg=self.FG_DIM,
                 font=("Segoe UI", 9)).pack(pady=(0, 20))

        btn_f = tk.Frame(inner, bg=self.BG)
        btn_f.pack(pady=10)

        self._btn_pip_install = tk.Button(
            btn_f, text="ðŸ  CÃ i Python packages\n(pip install -r requirements.txt)",
            bg=self.BTN_OK, fg="white",
            relief="flat", padx=24, pady=12,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
            command=self._pip_install
        )
        self._btn_pip_install.grid(row=0, column=0, padx=12, pady=6, sticky="ew")

        self._btn_npm_install = tk.Button(
            btn_f, text="ðŸŸ©  CÃ i Node.js packages\n(npm install â€” Live Map)",
            bg="#1a3a1a", fg="#88ff88",
            relief="flat", padx=24, pady=12,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
            command=self._npm_install
        )
        self._btn_npm_install.grid(row=0, column=1, padx=12, pady=6, sticky="ew")

        tk.Button(btn_f, text="ðŸ”  Kiá»ƒm tra phiÃªn báº£n\n(Python / Node.js / npm)",
                  bg="#1a1a1a", fg="#aaa",
                  relief="flat", padx=24, pady=12,
                  font=("Segoe UI", 10), cursor="hand2",
                  command=self._check_versions
                  ).grid(row=1, column=0, padx=12, pady=6, sticky="ew")

        tk.Button(btn_f, text="ðŸ“„  Xem requirements.txt",
                  bg="#1a1a1a", fg="#aaa",
                  relief="flat", padx=24, pady=12,
                  font=("Segoe UI", 10), cursor="hand2",
                  command=self._show_requirements
                  ).grid(row=1, column=1, padx=12, pady=6, sticky="ew")

        if IS_FROZEN_APP:
            self._btn_pip_install.config(state="disabled", bg="#333", fg="#777", cursor="")
            self._btn_npm_install.config(state="disabled", bg="#333", fg="#777", cursor="")
            tk.Label(
                inner,
                text="Báº£n phÃ¡t hÃ nh EXE: Ä‘Ã£ Ä‘Ã³ng gÃ³i sáºµn runtime, khÃ´ng cáº§n cÃ i Python/Node trÃªn mÃ¡y ngÆ°á»i dÃ¹ng.",
                bg=self.BG, fg="#88ccaa", font=("Segoe UI", 9, "italic")
            ).pack(pady=(8, 0))

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  TAB MODS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _pal_root(self) -> str:
        """Tráº£ vá» thÆ° má»¥c gá»‘c PalServer (dirname cá»§a SERVER_EXE)."""
        exe = self._vars.get("SERVER_EXE", tk.StringVar()).get().strip()
        if not exe:
            cfg = load_config()
            exe = cfg.get("SERVER_EXE", "")
        exe = _resolve_server_exe_path(exe)
        return os.path.dirname(exe) if exe else ""

    def _get_installed_ver(self, mod_id: str) -> str:
        cfg = load_config()
        return cfg.get("INSTALLED_MODS", {}).get(mod_id, "")

    def _set_installed_ver(self, mod_id: str, version: str):
        cfg = load_config()
        if "INSTALLED_MODS" not in cfg:
            cfg["INSTALLED_MODS"] = {}
        cfg["INSTALLED_MODS"][mod_id] = version
        save_config(cfg)

    def _remove_installed_ver(self, mod_id: str):
        cfg = load_config()
        mods = cfg.get("INSTALLED_MODS", {})
        if isinstance(mods, dict) and mod_id in mods:
            mods.pop(mod_id, None)
            cfg["INSTALLED_MODS"] = mods
        save_config(cfg)

    def _mod_status(self, mod: dict) -> str:
        """'not_installed' | 'enabled' | 'disabled'"""
        root = self._pal_root()
        if not root:
            return "no_root"
        if mod.get("id") == "paldefender":
            paldef_dll = os.path.join(root, "Pal", "Binaries", "Win64", "PalDefender.dll")
            d3d9_dll = os.path.join(root, "Pal", "Binaries", "Win64", "d3d9.dll")
            # Rule cá»©ng: pháº£i cÃ³ cáº£ 2 file má»›i coi lÃ  Ä‘ang báº­t.
            if os.path.exists(paldef_dll) and os.path.exists(d3d9_dll):
                return "enabled"
            if os.path.exists(paldef_dll + ".disabled") or os.path.exists(d3d9_dll + ".disabled"):
                return "disabled"
            return "not_installed"
        probe    = os.path.join(root, mod["probe"])
        disabled = probe + ".disabled"
        if os.path.exists(probe):
            return "enabled"
        if os.path.exists(disabled):
            return "disabled"
        return "not_installed"

    def _mod_files_for_manage(self, mod: dict) -> list[str]:
        """Danh sÃ¡ch file/folder cá»§a mod cáº§n quáº£n lÃ½ khi báº­t/táº¯t/gá»¡."""
        root = self._pal_root()
        if not root:
            return []
        rels = []
        for key in ("toggle", "probe"):
            v = mod.get(key)
            if isinstance(v, str) and v.strip() and v not in rels:
                rels.append(v)
        for v in (mod.get("extra_files") or []):
            if isinstance(v, str) and v.strip() and v not in rels:
                rels.append(v)
        return [os.path.join(root, r) for r in rels]

    def _mod_files_for_uninstall(self, mod: dict) -> list[str]:
        """Danh sÃ¡ch file/folder dÃ¹ng riÃªng cho thao tÃ¡c gá»¡ mod."""
        root = self._pal_root()
        if not root:
            return []
        rels = []
        for p in self._mod_files_for_manage(mod):
            rel = os.path.relpath(p, root)
            if rel not in rels:
                rels.append(rel)
        for v in (mod.get("uninstall_files") or []):
            if isinstance(v, str) and v.strip() and v not in rels:
                rels.append(v)
        return [os.path.join(root, r) for r in rels]

    def _mod_toggle(self, mod: dict):
        """Báº­t/táº¯t mod báº±ng cÃ¡ch Ä‘á»•i tÃªn file/folder toggle."""
        root = self._pal_root()
        if not root:
            messagebox.showerror("Lá»—i", "ChÆ°a cáº¥u hÃ¬nh SERVER_EXE trong tab Cáº¥u HÃ¬nh!")
            return
        tgl      = os.path.join(root, mod["toggle"])
        disabled = tgl + ".disabled"
        try:
            if os.path.exists(tgl):
                os.rename(tgl, disabled)
                self._log(f"ðŸ”´ ÄÃ£ táº¯t {mod['name']} â†’ Ä‘á»•i tÃªn thÃ nh .disabled")
            elif os.path.exists(disabled):
                os.rename(disabled, tgl)
                self._log(f"ðŸŸ¢ ÄÃ£ báº­t {mod['name']} â†’ khÃ´i phá»¥c tÃªn gá»‘c")
            else:
                self._log(f"âš ï¸ {mod['name']}: khÃ´ng tÃ¬m tháº¥y file/folder toggle")
        except Exception as e:
            self._log(f"âŒ Toggle {mod['name']}: {e}")
        self._refresh_mod_cards()

    def _mod_enable(self, mod: dict):
        """Chá»‰ báº­t mod (rename .disabled â†’ gá»‘c). KhÃ´ng táº£i láº¡i."""
        root = self._pal_root()
        if not root:
            messagebox.showerror("Lá»—i", "ChÆ°a cáº¥u hÃ¬nh SERVER_EXE trong tab Cáº¥u HÃ¬nh!")
            return
        files = self._mod_files_for_manage(mod)
        changed = 0
        for tgl in files:
            disabled = tgl + ".disabled"
            if os.path.exists(disabled):
                try:
                    os.rename(disabled, tgl)
                    changed += 1
                except Exception as e:
                    self._log(f"âŒ Báº­t {mod['name']} ({os.path.basename(tgl)}): {e}")
        if changed:
            self._log(f"ðŸŸ¢ ÄÃ£ báº­t {mod['name']} ({changed} file).")
        else:
            self._log(f"âš ï¸ {mod['name']}: khÃ´ng tÃ¬m tháº¥y file .disabled")
        self._refresh_mod_cards()

    def _mod_disable(self, mod: dict):
        """Chá»‰ táº¯t mod (rename gá»‘c â†’ .disabled). KhÃ´ng xÃ³a file."""
        root = self._pal_root()
        if not root:
            messagebox.showerror("Lá»—i", "ChÆ°a cáº¥u hÃ¬nh SERVER_EXE trong tab Cáº¥u HÃ¬nh!")
            return
        files = self._mod_files_for_manage(mod)
        changed = 0
        for tgl in files:
            disabled = tgl + ".disabled"
            if os.path.exists(tgl):
                try:
                    os.rename(tgl, disabled)
                    changed += 1
                except Exception as e:
                    self._log(f"âŒ Táº¯t {mod['name']} ({os.path.basename(tgl)}): {e}")
        if changed:
            self._log(f"ðŸ”´ ÄÃ£ táº¯t {mod['name']} ({changed} file).")
        else:
            self._log(f"âš ï¸ {mod['name']}: khÃ´ng tÃ¬m tháº¥y file/folder Ä‘ang báº­t")
        self._refresh_mod_cards()

    def _mod_uninstall(self, mod: dict):
        """Gá»¡ cÃ i Ä‘áº·t mod: xÃ³a file/folder toggle(probe) an toÃ n + báº£n .disabled náº¿u cÃ³."""
        root = self._pal_root()
        if not root:
            messagebox.showerror("Lá»—i", "ChÆ°a cáº¥u hÃ¬nh SERVER_EXE trong tab Cáº¥u HÃ¬nh!")
            return

        candidates = self._mod_files_for_uninstall(mod)
        # LuÃ´n thá»­ dá»n cáº£ file/folder .disabled tÆ°Æ¡ng á»©ng.
        candidates_with_disabled = []
        for p in candidates:
            candidates_with_disabled.append(p)
            candidates_with_disabled.append(p + ".disabled")

        # Chá»‰ cho phÃ©p xÃ³a trong root PalServer Ä‘á»ƒ trÃ¡nh xÃ³a nháº§m.
        root_abs = os.path.abspath(root)
        targets = []
        for p in candidates_with_disabled:
            p_abs = os.path.abspath(p)
            if p_abs.startswith(root_abs) and os.path.exists(p_abs):
                targets.append(p_abs)

        if not targets:
            self._log(f"âš ï¸ [{mod['name']}] KhÃ´ng tÃ¬m tháº¥y file mod Ä‘á»ƒ gá»¡.")
            self._remove_installed_ver(mod.get("id"))
            self._refresh_mod_cards()
            return

        txt = "Báº¡n cÃ³ cháº¯c muá»‘n gá»¡ cÃ i Ä‘áº·t mod nÃ y?\n\n" + "\n".join(f"- {t}" for t in targets)
        if not messagebox.askyesno("XÃ¡c nháº­n gá»¡ mod", txt):
            return

        errs = []
        removed = 0
        for t in targets:
            try:
                if os.path.isdir(t):
                    shutil.rmtree(t)
                else:
                    os.remove(t)
                removed += 1
            except Exception as e:
                errs.append(f"{os.path.basename(t)}: {e}")

        self._remove_installed_ver(mod.get("id"))
        if errs:
            self._log(f"âš ï¸ Gá»¡ {mod['name']} xong má»™t pháº§n ({removed}/{len(targets)}).")
            for e in errs:
                self._log(f"   - {e}")
        else:
            self._log(f"ðŸ—‘ï¸ ÄÃ£ gá»¡ cÃ i Ä‘áº·t {mod['name']} ({removed} má»¥c).")
        self._refresh_mod_cards()

    def _smart_action(self, mod: dict, url_override: str = ""):
        """HÃ nh Ä‘á»™ng thÃ´ng minh theo tráº¡ng thÃ¡i:
           â€¢ not_installed â†’ táº£i + cÃ i Ä‘áº·t (tá»± Ä‘á»™ng báº­t sau khi cÃ i)
           â€¢ disabled      â†’ chá»‰ báº­t láº¡i (KHÃ”NG táº£i láº¡i)
           â€¢ enabled       â†’ thÃ´ng bÃ¡o Ä‘Ã£ hoáº¡t Ä‘á»™ng rá»“i
        """
        status = self._mod_status(mod)
        if status == "no_root":
            messagebox.showerror("Lá»—i", "ChÆ°a cáº¥u hÃ¬nh SERVER_EXE trong tab Cáº¥u HÃ¬nh!")
            return
        if status == "enabled":
            self._log(f"âœ… {mod['name']} Ä‘ang hoáº¡t Ä‘á»™ng â€” khÃ´ng cáº§n lÃ m gÃ¬ thÃªm!")
            return

        # Kiá»ƒm tra náº¿u cáº§n update
        installed_ver = self._get_installed_ver(mod.get("id"))
        if installed_ver and installed_ver != mod["version"]:
             self._log(f"â¬‡ [{mod['name']}] CÃ³ báº£n má»›i ({mod['version']}) â€” Ä‘ang cáº­p nháº­t...")
             self._mod_install(mod, url_override)
             return

        if status == "disabled":
            # ÄÃ£ cÃ i sáºµn, chá»‰ cáº§n báº­t láº¡i (khÃ´ng táº£i/giáº£i nÃ©n láº¡i)
            self._log(f"ðŸŸ¢ [{mod['name']}] ÄÃ£ cÃ i sáºµn â€” báº­t láº¡i khÃ´ng cáº§n táº£i...")
            self._mod_enable(mod)
            return
        # not_installed â†’ táº£i + cÃ i
        self._log(f"â¬‡ [{mod['name']}] ChÆ°a cÃ i â€” báº¯t Ä‘áº§u táº£i vÃ  cÃ i Ä‘áº·t...")
        self._mod_install(mod, url_override)

    def _find_mod(self, mod_id: str) -> dict | None:
        for m in MODS_CATALOG:
            if m.get("id") == mod_id:
                return m
        return None

    def _bootstrap_server_once_for_paldefender(self, run_seconds: int = 10) -> bool:
        """Cháº¡y PalServer.exe trong vÃ i giÃ¢y rá»“i tá»± táº¯t Ä‘á»ƒ bootstrap trÆ°á»›c khi cÃ i PalDefender."""
        cfg = load_config()
        server_exe = _resolve_server_exe_path(cfg.get("SERVER_EXE", ""))
        if not server_exe or not os.path.isfile(server_exe):
            self.root.after(0, lambda: self._log("âŒ KhÃ´ng tÃ¬m tháº¥y PalServer.exe Ä‘á»ƒ bootstrap PalDefender."))
            return False

        cmd = [server_exe, "-port=8211", "-RESTAPIPort=8212", "-log"]
        self.root.after(0, lambda: self._log(f"ðŸš€ Äang cháº¡y PalServer.exe {run_seconds}s Ä‘á»ƒ bootstrap PalDefender..."))
        proc = None
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NEW_CONSOLE, bufsize=1
            )
            deadline = time.time() + max(1, int(run_seconds))
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                time.sleep(0.2)
            self.root.after(0, lambda: self._log("â¹ï¸ Háº¿t thá»i gian bootstrap, Ä‘ang táº¯t PalServer.exe..."))
            return True
        except Exception as e:
            self.root.after(0, lambda e=e: self._log(f"âŒ Lá»—i bootstrap server: {e}"))
            return False
        finally:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    time.sleep(2)
                    if proc.poll() is None:
                        proc.kill()
                except Exception:
                    pass

    def _install_paldefender_with_bootstrap(self, paldef_mod: dict, url_override: str = ""):
        """Flow cÃ i PalDefender: Ä‘áº£m báº£o UE4SS -> bootstrap server 1 láº§n -> cÃ i PalDefender."""
        root = self._pal_root()
        if not root:
            messagebox.showerror("Lá»—i", "ChÆ°a cáº¥u hÃ¬nh SERVER_EXE trong tab Cáº¥u HÃ¬nh!")
            return

        ue4ss_mod = self._find_mod("ue4ss")
        if not ue4ss_mod:
            self._log("âŒ KhÃ´ng tÃ¬m tháº¥y cáº¥u hÃ¬nh mod UE4SS trong MODS_CATALOG.")
            return

        # Náº¿u UE4SS Ä‘ang disabled thÃ¬ báº­t ngay (main thread, nhanh).
        ue4ss_status = self._mod_status(ue4ss_mod)
        if ue4ss_status == "disabled":
            self._log("ðŸŸ¢ [UE4SS] Äang báº­t láº¡i trÆ°á»›c khi cÃ i PalDefender...")
            self._mod_enable(ue4ss_mod)

        paldef_url = (url_override or paldef_mod["url"]).strip()

        def _worker():
            # 1) Náº¿u UE4SS chÆ°a cÃ i thÃ¬ cÃ i trÆ°á»›c
            st = self._mod_status(ue4ss_mod)
            if st == "not_installed":
                self.root.after(0, lambda: self._log("â¬‡ [UE4SS] CÃ i trÆ°á»›c Ä‘á»ƒ há»— trá»£ PalDefender..."))
                ok_ue4ss = self._do_download_install(
                    ue4ss_mod["url"],
                    os.path.join(root, ue4ss_mod["target"]),
                    ue4ss_mod["name"],
                    ue4ss_mod,
                    success_cb=lambda: self._set_installed_ver(ue4ss_mod.get("id"), ue4ss_mod.get("version", "custom"))
                )
                if not ok_ue4ss:
                    self.root.after(0, lambda: self._log("âŒ [UE4SS] CÃ i tháº¥t báº¡i. Dá»«ng cÃ i PalDefender."))
                    self.root.after(300, self._refresh_mod_cards)
                    return

            # 2) Bootstrap server 1 láº§n
            if not self._bootstrap_server_once_for_paldefender():
                self.root.after(0, lambda: self._log("âŒ Bootstrap server tháº¥t báº¡i. Dá»«ng cÃ i PalDefender."))
                self.root.after(300, self._refresh_mod_cards)
                return

            # 3) CÃ i PalDefender
            self.root.after(0, lambda: self._log("â¬‡ [PalDefender] Báº¯t Ä‘áº§u cÃ i sau bootstrap..."))
            ok_paldef = self._do_download_install(
                paldef_url,
                os.path.join(root, paldef_mod["target"]),
                paldef_mod["name"],
                paldef_mod,
                success_cb=lambda: self._set_installed_ver(paldef_mod.get("id"), paldef_mod.get("version", "custom"))
            )
            if not ok_paldef:
                self.root.after(0, lambda: self._log("âŒ [PalDefender] CÃ i tháº¥t báº¡i sau bootstrap."))
            self.root.after(300, self._refresh_mod_cards)

        threading.Thread(target=_worker, daemon=True).start()

    def _mod_install(self, mod: dict, url_override: str = ""):
        """Download + giáº£i nÃ©n mod vÃ o Ä‘Ãºng thÆ° má»¥c target."""
        root = self._pal_root()
        if not root:
            messagebox.showerror("Lá»—i", "ChÆ°a cáº¥u hÃ¬nh SERVER_EXE trong tab Cáº¥u HÃ¬nh!")
            return
        url = (url_override or mod["url"]).strip()
        if not url:
            messagebox.showerror("Lá»—i", "URL rá»—ng â€” khÃ´ng thá»ƒ táº£i!")
            return
        target_dir = os.path.join(root, mod["target"])
        threading.Thread(
            target=self._do_download_install,
            args=(url, target_dir, mod["name"], mod),
            kwargs={"success_cb": lambda: self._set_installed_ver(mod.get("id"), mod.get("version", "custom"))},
            daemon=True
        ).start()

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  CÆ  CHáº¾: Táº¢I â†’ GIáº¢I NÃ‰N â†’ CÃ€I Äáº¶T  (3 giai Ä‘oáº¡n tÃ¡ch biá»‡t)
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _do_download_install(self, url: str, target_dir: str, label: str, mod: dict = None, success_cb=None):
        """(Cháº¡y trong thread) 3 giai Ä‘oáº¡n:
           1. DOWNLOAD  â€” táº£i archive vá» thÆ° má»¥c táº¡m, bÃ¡o tiáº¿n Ä‘á»™ %
           2. EXTRACT   â€” giáº£i nÃ©n vÃ o thÆ° má»¥c táº¡m riÃªng (khÃ´ng Ä‘á»¥ng target)
           3. INSTALL   â€” smart-copy: phÃ¡t hiá»‡n cáº¥u trÃºc archive, copy Ä‘Ãºng chá»—
        Dá»n sáº¡ch temp sau má»—i trÆ°á»ng há»£p (thÃ nh cÃ´ng láº«n tháº¥t báº¡i).
        """
        tmp_root = tempfile.mkdtemp(prefix="palmod_")   # thÆ° má»¥c táº¡m chÃ­nh
        done_ok = False
        try:
            # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # GIAI ÄOáº N 1 â€” DOWNLOAD
            # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            import requests as _req
            import re as _re

            # [Auto-convert] Google Drive View Link -> Direct Link
            if "drive.google.com" in url and "/view" in url:
                m = _re.search(r"/d/([-\w]{25,})", url)
                if m:
                    url = f"https://drive.google.com/uc?export=download&id={m.group(1)}"
                    self.root.after(0, lambda: self._log(f"ðŸ”„  Google Drive link detected -> Direct Download..."))

            self.root.after(0, lambda: self._log(
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"â¬‡  [{label}]  Äang káº¿t ná»‘i..."))

            try:
                # ThÃªm User-Agent Ä‘á»ƒ trÃ¡nh bá»‹ cháº·n bá»Ÿi má»™t sá»‘ CDN
                resp = _req.get(url, stream=True, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
                resp.raise_for_status()

                # [Check] NgÄƒn táº£i trang web (HTML) thay vÃ¬ file mod
                ctype = resp.headers.get("Content-Type", "").lower()
                if "text/html" in ctype:
                    self.root.after(0, lambda: self._log(f"âŒ  Lá»—i: URL nÃ y lÃ  trang web (HTML), khÃ´ng pháº£i file mod.\n   HÃ£y láº¥y Direct Link (chuá»™t pháº£i nÃºt Download -> Copy Link)."))
                    return False

                # [Auto-detect] Láº¥y tÃªn file vÃ  Ä‘uÃ´i file tá»« Header (há»— trá»£ .rar tá»« Drive)
                fname = ""
                if "Content-Disposition" in resp.headers:
                    cd = resp.headers["Content-Disposition"]
                    m = _re.search(r'filename\*?=([^;]+)', cd)
                    if m:
                        fname = m.group(1).strip().strip('"\'')
                        if "utf-8''" in fname.lower(): fname = fname.split("''")[-1]
                
                if not fname:
                    fname = url.split("?")[0].rstrip("/").split("/")[-1] or "archive"

                ext = os.path.splitext(fname)[1].lower()
                if ext not in (".7z", ".zip", ".rar"): ext = ".rar" # Fallback Æ°u tiÃªn rar cho trÆ°á»ng há»£p nÃ y
                archive_path = os.path.join(tmp_root, f"archive{ext}")

                self.root.after(0, lambda: self._log(f"â¬‡  Äang táº£i: {fname}"))
                total     = int(resp.headers.get("content-length", 0))
                done      = 0
                last_pct  = -1
                with open(archive_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            done += len(chunk)
                            if total:
                                pct = min(100, done * 100 // total)
                                if pct >= last_pct + 10:
                                    last_pct = pct
                                    self.root.after(0, lambda p=pct, d=done, t=total:
                                        self._log(f"   {p:3d}%  ({d//1024:,} KB / {t//1024:,} KB)"))
                size_kb = os.path.getsize(archive_path) // 1024
                self.root.after(0, lambda s=size_kb: self._log(
                    f"âœ…  Táº£i xong â€” {s:,} KB"))

            except Exception as e:
                code = getattr(getattr(e, "response", None), "status_code", "")
                if code == 403:
                    self.root.after(0, lambda: self._log(f"âŒ  Lá»—i 403 Forbidden: Link táº£i Ä‘Ã£ háº¿t háº¡n hoáº·c bá»‹ cháº·n.\n   HÃ£y cáº­p nháº­t URL má»›i trong code hoáº·c Mod Manager."))
                else:
                    self.root.after(0, lambda: self._log(f"âŒ  Lá»—i táº£i ({code}): {e}"))
                return False

            # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # GIAI ÄOáº N 2 â€” EXTRACT vÃ o thÆ° má»¥c táº¡m riÃªng
            # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            extract_dir = os.path.join(tmp_root, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            self.root.after(0, lambda: self._log(f"ðŸ“¦  Äang giáº£i nÃ©n ({ext})..."))
            try:
                if ext == ".7z":
                    if not HAS_PY7ZR:
                        self.root.after(0, lambda: self._log(
                            "âŒ  Thiáº¿u py7zr â€” cháº¡y: pip install py7zr"))
                        return False
                    import py7zr
                    with py7zr.SevenZipFile(archive_path, mode="r") as z:
                        z.extractall(path=extract_dir)

                elif ext == ".zip":
                    with zipfile.ZipFile(archive_path, "r") as z:
                        z.extractall(path=extract_dir)

                elif ext == ".rar":
                    if not HAS_RAR:
                        self.root.after(0, lambda: self._log(
                            "âŒ  Thiáº¿u rarfile â€” cháº¡y: pip install rarfile\n"
                            "   Cáº§n cÃ i thÃªm unrar.exe: https://www.rarlab.com/rar_add.htm"))
                        return False
                    import rarfile
                    with rarfile.RarFile(archive_path) as rf:
                        rf.extractall(path=extract_dir)

            except Exception as e:
                self.root.after(0, lambda: self._log(f"âŒ  Lá»—i giáº£i nÃ©n: {e}"))
                return False

            # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # GIAI ÄOáº N 3 â€” INSTALL: smart-copy Ä‘Ãºng Ä‘Æ°á»ng dáº«n
            # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # PhÃ¡t hiá»‡n cáº¥u trÃºc archive:
            #   â€¢ Náº¿u cÃ³ duy nháº¥t 1 thÆ° má»¥c con á»Ÿ root â†’ copy Ná»˜I DUNG thÆ° má»¥c Ä‘Ã³
            #   â€¢ NgÆ°á»£c láº¡i (nhiá»u file/folder) â†’ copy Táº¤T Cáº¢ vÃ o target
            top_items = os.listdir(extract_dir)
            if (len(top_items) == 1
                    and os.path.isdir(os.path.join(extract_dir, top_items[0]))):
                source_dir = os.path.join(extract_dir, top_items[0])
                self.root.after(0, lambda n=top_items[0]: self._log(
                    f"   PhÃ¡t hiá»‡n thÆ° má»¥c gá»‘c trong archive: [{n}] â†’ dÃ¹ng ná»™i dung bÃªn trong"))
            else:
                source_dir = extract_dir
                self.root.after(0, lambda: self._log(
                    "   Archive khÃ´ng cÃ³ thÆ° má»¥c gá»‘c â†’ copy tháº³ng vÃ o target"))

            os.makedirs(target_dir, exist_ok=True)
            items   = os.listdir(source_dir)
            total_i = len(items)
            if mod and mod.get("id") == "paldefender":
                self.root.after(0, lambda: self._log(
                    "â™»ï¸ [PalDefender] Náº¿u tá»‡p Ä‘Ã£ tá»“n táº¡i sáº½ tá»± thay tháº¿ báº±ng báº£n má»›i."))
            self.root.after(0, lambda t=total_i, d=target_dir: self._log(
                f"ðŸ“‹  Sao chÃ©p {t} má»¥c â†’ {d}"))

            for i, item in enumerate(items, 1):
                src = os.path.join(source_dir, item)
                dst = os.path.join(target_dir, item)
                try:
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        if os.path.exists(dst):
                            if os.path.isdir(dst):
                                shutil.rmtree(dst)
                            else:
                                os.remove(dst)
                        shutil.copy2(src, dst)
                    self.root.after(0, lambda n=item, idx=i, t=total_i:
                        self._log(f"   [{idx}/{t}]  {n}"))
                except Exception as e:
                    self.root.after(0, lambda n=item, e=e:
                        self._log(f"   âš ï¸  {n}: {e}"))

            # XÃ¡c nháº­n cÃ i thÃ nh cÃ´ng báº±ng "probe" (náº¿u mod cÃ³ khai bÃ¡o).
            install_ok = True
            if mod and mod.get("probe"):
                root_dir = self._pal_root()
                probe_path = os.path.join(root_dir, mod["probe"]) if root_dir else ""
                disabled_probe = probe_path + ".disabled" if probe_path else ""
                install_ok = bool(probe_path and os.path.exists(probe_path) and not os.path.exists(disabled_probe))

            if install_ok:
                self.root.after(0, lambda: self._log(
                    f"âœ…  [{label}]  CÃ i Ä‘áº·t hoÃ n táº¥t!\n"
                    f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"))
                if success_cb:
                    self.root.after(0, success_cb)
                done_ok = True
            else:
                self.root.after(0, lambda: self._log(
                    f"âš ï¸  [{label}] Giáº£i nÃ©n xong nhÆ°ng chÆ°a xÃ¡c nháº­n Ä‘Æ°á»£c probe mod.\n"
                    f"   ChÆ°a Ä‘Ã¡nh dáº¥u 'Äang báº­t'. HÃ£y kiá»ƒm tra láº¡i thÆ° má»¥c cÃ i Ä‘áº·t."))
            self.root.after(300, self._refresh_mod_cards)

        except Exception as e:
            self.root.after(0, lambda: self._log(f"âŒ  [{label}]  Lá»—i khÃ´ng xÃ¡c Ä‘á»‹nh: {e}"))
        finally:
            # Dá»n sáº¡ch temp dÃ¹ thÃ nh cÃ´ng hay tháº¥t báº¡i
            shutil.rmtree(tmp_root, ignore_errors=True)
        return done_ok

    def _build_mods_tab(self, parent):
        # â”€â”€ Toolbar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        bar = tk.Frame(parent, bg=self.BG, pady=6)
        bar.pack(fill="x", padx=14)
        tk.Label(bar, text="ðŸŽ®  Mod Manager",
                 bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(bar,
                 text="Táº£i & quáº£n lÃ½ mods â€” báº­t/táº¯t khÃ´ng cáº§n xÃ³a file",
                 bg=self.BG, fg=self.FG_DIM,
                 font=("Segoe UI", 9)).pack(side="left", padx=12)
        tk.Button(bar, text="ðŸ”„  LÃ m má»›i",
                  bg="#1a1a1a", fg="#aaa", relief="flat",
                  padx=10, pady=4, cursor="hand2",
                  command=self._refresh_mod_cards
                  ).pack(side="right")

        # â”€â”€ Scrollable area â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._mod_cards_frame = self._scrollable(parent)

        # â”€â”€ Custom mod section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sep_f = tk.Frame(parent, bg=self.BG)
        sep_f.pack(fill="x", padx=14, pady=(6, 0))
        tk.Frame(sep_f, bg="#222", height=1).pack(fill="x", pady=(0, 8))
        tk.Label(sep_f, text="âž•  CÃ i mod tá»« link tÃ¹y chá»‰nh",
                 bg=self.BG, fg="#888",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        cust = tk.Frame(parent, bg=self.BG2, padx=12, pady=8)
        cust.pack(fill="x", padx=14, pady=(4, 8))

        tk.Label(cust, text="TÃªn:", bg=self.BG2, fg=self.FG,
                 font=("Segoe UI", 9), width=8, anchor="e"
                 ).grid(row=0, column=0, sticky="e", padx=(0, 6), pady=3)
        self._custom_name = tk.Entry(cust, bg=self.ENTRY_BG, fg=self.FG,
                                     bd=0, font=("Consolas", 9), width=22,
                                     insertbackground=self.ACCENT)
        self._custom_name.insert(0, "My Mod")
        self._custom_name.grid(row=0, column=1, sticky="ew", ipady=4, padx=(0, 8))

        tk.Label(cust, text="Giáº£i nÃ©n vÃ o:", bg=self.BG2, fg=self.FG,
                 font=("Segoe UI", 9), width=12, anchor="e"
                 ).grid(row=0, column=2, sticky="e", padx=(0, 6))
        self._custom_target = tk.Entry(cust, bg=self.ENTRY_BG, fg=self.FG,
                                       bd=0, font=("Consolas", 9), width=28,
                                       insertbackground=self.ACCENT)
        self._custom_target.insert(0, os.path.join("Pal", "Binaries", "Win64"))
        self._custom_target.grid(row=0, column=3, sticky="ew", ipady=4, columnspan=2)
        cust.columnconfigure(3, weight=1)

        tk.Label(cust, text="URL:", bg=self.BG2, fg=self.FG,
                 font=("Segoe UI", 9), width=8, anchor="e"
                 ).grid(row=1, column=0, sticky="e", padx=(0, 6), pady=(4, 0))
        self._custom_url = tk.Entry(cust, bg=self.ENTRY_BG, fg="#aaa",
                                    bd=0, font=("Consolas", 8),
                                    insertbackground=self.ACCENT)
        self._custom_url.insert(0, "https://...")
        self._custom_url.grid(row=1, column=1, columnspan=3, sticky="ew",
                               ipady=4, pady=(4, 0))
        tk.Button(cust, text="â¬‡ CÃ i",
                  bg=self.BTN_OK, fg="white", relief="flat",
                  padx=12, pady=4, cursor="hand2",
                  command=self._install_custom_mod
                  ).grid(row=1, column=4, padx=(8, 0), pady=(4, 0))

        # Render cards ngay
        self._refresh_mod_cards()

    def _build_server_setup_tab(self, parent):
        # â”€â”€ Toolbar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        bar = tk.Frame(parent, bg=self.BG, pady=6)
        bar.pack(fill="x", padx=14)
        tk.Label(bar, text="ðŸ—ï¸  Server Setup",
                 bg=self.BG, fg=self.ACCENT,
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(bar,
                 text="Táº¡o server má»›i hoáº·c import Ä‘Æ°á»ng dáº«n server hiá»‡n cÃ³",
                 bg=self.BG, fg=self.FG_DIM,
                 font=("Segoe UI", 9)).pack(side="left", padx=12)

        # â”€â”€ Main content â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        main = tk.Frame(parent, bg=self.BG)
        main.pack(fill="both", expand=True, padx=14, pady=(10, 0))

        # Táº¡o Server Má»›i
        create_f = tk.Frame(main, bg=self.BG2, padx=20, pady=20)
        create_f.pack(fill="x", pady=(0, 20))
        tk.Label(create_f, text="ðŸš€  Táº¡o Server Má»›i",
                 bg=self.BG2, fg="#00ff88",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        tk.Label(create_f,
                 text="Tá»± Ä‘á»™ng táº£i SteamCMD vÃ  cÃ i Ä‘áº·t Palworld Dedicated Server má»›i nháº¥t.\n"
                     "Server sáº½ cÃ i theo thÆ° má»¥c báº¡n chá»n á»Ÿ cá»­a sá»• cÃ i Ä‘áº·t.",
                 bg=self.BG2, fg=self.FG, font=("Segoe UI", 9), justify="left").pack(anchor="w", pady=(0, 15))
        tk.Button(create_f, text="â¬‡  Táº£i & CÃ i Äáº·t Server",
                  bg=self.BTN_OK, fg="white", relief="flat",
                  padx=20, pady=12, font=("Segoe UI", 10, "bold"), cursor="hand2",
                  command=self._create_new_server).pack(anchor="w")

        # Inline installer (áº©n máº·c Ä‘á»‹nh, báº¥m "Táº¡o Server Má»›i" sáº½ má»Ÿ táº¡i Ä‘Ã¢y)
        self._inline_installer_open = False
        self._inline_installer_host = main
        self._inline_installer_frame = tk.Frame(main, bg="#0a0a0a", padx=16, pady=12)
        self._inline_installer_frame.pack(fill="x", pady=(0, 20))
        self._inline_installer_frame.pack_forget()

        self._inline_steamcmd_dir = tk.StringVar(value=r"C:\steamcmd")
        self._inline_install_dir = tk.StringVar(value=DEFAULT_SERVER_ROOT)
        self._inline_installing = False
        try:
            cfg = load_config()
            cur_exe = _resolve_server_exe_path(cfg.get("SERVER_EXE", ""))
            if cur_exe and os.path.isfile(cur_exe):
                self._inline_install_dir.set(os.path.dirname(cur_exe))
        except Exception:
            pass
        self._build_inline_installer_ui(self._inline_installer_frame)

        # Import ÄÆ°á»ng Dáº«n
        import_f = tk.Frame(main, bg=self.BG2, padx=20, pady=20)
        import_f.pack(fill="x")
        tk.Label(import_f, text="ðŸ“‚  Import ÄÆ°á»ng Dáº«n Server",
                 bg=self.BG2, fg="#00ccff",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        tk.Label(import_f,
                 text="Chá»n file PalServer.exe tá»« server Ä‘Ã£ cÃ i Ä‘áº·t Ä‘á»ƒ cáº¥u hÃ¬nh.\n"
                      "ÄÆ°á»ng dáº«n sáº½ Ä‘Æ°á»£c lÆ°u vÃ o manager_config.json.",
                 bg=self.BG2, fg=self.FG, font=("Segoe UI", 9), justify="left").pack(anchor="w", pady=(0, 15))
        tk.Button(import_f, text="ðŸ“‚  Chá»n PalServer.exe",
                  bg=self.BTN_OK, fg="white", relief="flat",
                  padx=20, pady=12, font=("Segoe UI", 10, "bold"), cursor="hand2",
                  command=self._import_server_path).pack(anchor="w")

    def _create_new_server(self):
        """Báº­t/táº¯t inline Manager ServerPal Installer ngay trong tab Táº¡o server."""
        if not hasattr(self, "_inline_installer_frame"):
            return
        if self._inline_installer_open:
            self._inline_installer_frame.pack_forget()
            self._inline_installer_open = False
            self._log("â„¹ï¸ ÄÃ£ áº©n Manager ServerPal Installer.")
        else:
            self._inline_installer_frame.pack(fill="x", pady=(0, 20))
            self._inline_installer_open = True
            self._log("â„¹ï¸ ÄÃ£ má»Ÿ Manager ServerPal Installer ngay trong tab Táº¡o server.")

    def _build_inline_installer_ui(self, host):
        tk.Label(host, text="ðŸš€  MANAGER SERVERPAL INSTALLER",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 14, "bold")).pack(anchor="center", pady=(0, 10))

        tk.Label(host, text="1. ThÆ° má»¥c cÃ i SteamCMD:", bg="#0a0a0a", fg="#aaa",
                 font=("Segoe UI", 9)).pack(anchor="w")
        f1 = tk.Frame(host, bg="#0a0a0a")
        f1.pack(fill="x", pady=(2, 8))
        tk.Entry(f1, textvariable=self._inline_steamcmd_dir, bg="#161616", fg="white",
                 bd=0, font=("Consolas", 10), insertbackground="white").pack(
                    side="left", fill="x", expand=True, ipady=6, padx=(0, 5))
        tk.Button(f1, text="ðŸ“‚", bg="#222", fg="white", relief="flat",
                  command=lambda: self._inline_browse(self._inline_steamcmd_dir)).pack(side="left")

        tk.Label(host, text="2. ThÆ° má»¥c cÃ i PalServer:", bg="#0a0a0a", fg="#aaa",
                 font=("Segoe UI", 9)).pack(anchor="w")
        f2 = tk.Frame(host, bg="#0a0a0a")
        f2.pack(fill="x", pady=(2, 10))
        tk.Entry(f2, textvariable=self._inline_install_dir, bg="#161616", fg="white",
                 bd=0, font=("Consolas", 10), insertbackground="white").pack(
                    side="left", fill="x", expand=True, ipady=6, padx=(0, 5))
        tk.Button(f2, text="ðŸ“‚", bg="#222", fg="white", relief="flat",
                  command=lambda: self._inline_browse(self._inline_install_dir)).pack(side="left")

        self._btn_inline_install = tk.Button(
            host, text="â¬‡  Báº®T Äáº¦U CÃ€I Äáº¶T",
            bg="#006644", fg="white", relief="flat", pady=10,
            font=("Segoe UI", 11, "bold"), cursor="hand2",
            command=self._start_inline_install
        )
        self._btn_inline_install.pack(fill="x", pady=(0, 10))

        tk.Label(host, text="Tiáº¿n trÃ¬nh:", bg="#0a0a0a", fg="#666", font=("Segoe UI", 9)).pack(anchor="w")
        self._inline_console = scrolledtext.ScrolledText(
            host, bg="#050505", fg="#00ff88", font=("Consolas", 9), bd=0, height=10
        )
        self._inline_console.pack(fill="both", expand=True)

    def _inline_browse(self, var):
        d = filedialog.askdirectory()
        if d:
            var.set(d)

    def _inline_log(self, msg: str):
        if not hasattr(self, "_inline_console"):
            return
        self._inline_console.insert(tk.END, msg + "\n")
        self._inline_console.see(tk.END)

    def _inline_log_update(self, msg: str):
        if not hasattr(self, "_inline_console"):
            return
        if self._inline_console.index("end-1c") != "1.0":
            self._inline_console.delete("end-2l linestart", "end-1c")
        self._inline_console.insert(tk.END, msg + "\n")
        self._inline_console.see(tk.END)

    def _start_inline_install(self):
        if self._inline_installing:
            return
        self._inline_installing = True
        self._btn_inline_install.config(state="disabled", bg="#333")
        self._inline_spin_idx = 0
        self._animate_inline_spin()
        threading.Thread(target=self._process_inline_install, daemon=True).start()

    def _animate_inline_spin(self):
        if not self._inline_installing:
            return
        chars = ["|", "/", "-", "\\"]
        c = chars[self._inline_spin_idx % 4]
        self._btn_inline_install.config(text=f"â³ {c} ÄANG CÃ€I Äáº¶T...")
        self._inline_spin_idx += 1
        self.root.after(100, self._animate_inline_spin)

    def _process_inline_install(self):
        s_dir = self._inline_steamcmd_dir.get().strip()
        p_dir = self._inline_install_dir.get().strip()
        s_exe = os.path.join(s_dir, "steamcmd.exe")
        try:
            os.makedirs(s_dir, exist_ok=True)
            os.makedirs(p_dir, exist_ok=True)
            if not os.path.isfile(s_exe):
                self._inline_log("â¬‡ Báº¯t Ä‘áº§u táº£i SteamCMD...")
                zip_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
                zip_path = os.path.join(s_dir, "steamcmd.zip")
                with urllib.request.urlopen(zip_url) as resp, open(zip_path, "wb") as f:
                    total = int(resp.info().get("Content-Length", 0))
                    downloaded = 0
                    bs = 8192
                    while True:
                        chunk = resp.read(bs)
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        f.write(chunk)
                        if total:
                            pct = int(downloaded * 100 / total)
                            if pct % 5 == 0:
                                self._inline_log_update(f"â³ Downloading SteamCMD: {pct}%")
                self._inline_log("ðŸ“¦ Äang giáº£i nÃ©n SteamCMD...")
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(s_dir)
                os.remove(zip_path)

            self._inline_log("ðŸš€ Äang cháº¡y SteamCMD Ä‘á»ƒ cÃ i PalServer (2394010)...")
            cmd = [s_exe, "+login", "anonymous", "+force_install_dir", p_dir, "+app_update", "2394010", "validate", "+quit"]
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW, bufsize=1
            )
            cur_line = ""
            while True:
                ch = proc.stdout.read(1)
                if not ch and proc.poll() is not None:
                    break
                if ch == "\n":
                    self._inline_log(cur_line)
                    cur_line = ""
                elif ch == "\r":
                    self._inline_log_update(cur_line)
                    cur_line = ""
                else:
                    cur_line += ch
            if cur_line:
                self._inline_log(cur_line)
            proc.wait()

            if proc.returncode == 0:
                final_exe = os.path.join(p_dir, "PalServer.exe")
                if not os.path.isfile(final_exe):
                    for r, _, files in os.walk(p_dir):
                        if "PalServer.exe" in files:
                            final_exe = os.path.join(r, "PalServer.exe")
                            break
                if os.path.isfile(final_exe):
                    self._import_default_palworld_settings(p_dir, final_exe)
                    cfg = load_config()
                    cfg["SERVER_EXE"] = _resolve_server_exe_path(final_exe)
                    cfg["STEAMCMD_EXE"] = s_exe
                    save_config(cfg)
                    self._inline_log("âœ… CÃ i Ä‘áº·t server thÃ nh cÃ´ng.")
                    self._inline_log(f"ðŸ“‚ Server: {final_exe}")
                    self.root.after(0, self._load_to_ui)
                else:
                    self._inline_log("âš ï¸ KhÃ´ng tÃ¬m tháº¥y PalServer.exe!")
            else:
                self._inline_log(f"âŒ Lá»—i code {proc.returncode}")
        except Exception as e:
            self._inline_log(f"âŒ Lá»—i: {e}")
        self._inline_installing = False
        self.root.after(0, lambda: self._btn_inline_install.config(
            text="â¬‡  Báº®T Äáº¦U CÃ€I Äáº¶T", bg="#006644", state="normal"))

    def _import_server_path(self):
        """Import Ä‘Æ°á»ng dáº«n PalServer.exe."""
        file_path = filedialog.askopenfilename(
            title="Chá»n file PalServer.exe",
            filetypes=[("Executable files", "*.exe")],
            initialdir="C:/"
        )
        if file_path and "palserver.exe" in os.path.basename(file_path).lower():
            cfg = load_config()
            cfg["SERVER_EXE"] = _resolve_server_exe_path(file_path)
            save_config(cfg)
            self._load_to_ui()  # Refresh UI
            self._log(f"âœ… ÄÃ£ import Ä‘Æ°á»ng dáº«n: {file_path}")
            messagebox.showinfo("ThÃ nh cÃ´ng", f"ÄÃ£ cáº­p nháº­t Ä‘Æ°á»ng dáº«n server:\n{file_path}")
        elif file_path:
            messagebox.showerror("Lá»—i", "Vui lÃ²ng chá»n file PalServer.exe")
        # Náº¿u cancel, khÃ´ng lÃ m gÃ¬

    def _refresh_mod_cards(self):
        """Váº½ láº¡i cÃ¡c mod card vá»›i tráº¡ng thÃ¡i hiá»‡n táº¡i."""
        for w in self._mod_cards_frame.winfo_children():
            w.destroy()

        for mod in MODS_CATALOG:
            self._draw_mod_card(self._mod_cards_frame, mod)

    def _draw_mod_card(self, parent, mod: dict):
        status = self._mod_status(mod)
        
        # Check version
        installed_ver = self._get_installed_ver(mod.get("id"))
        has_update = (installed_ver and installed_ver != mod["version"])

        # MÃ u + nhÃ£n theo tráº¡ng thÃ¡i
        status_meta = {
            "enabled":       ("#00ff88", "ðŸŸ¢ Äang báº­t",   "#0d2a1a"),
            "disabled":      ("#ff9900", "ðŸŸ¡ Äang táº¯t",   "#2a1e00"),
            "not_installed": ("#555555", "âš« ChÆ°a cÃ i",    "#111120"),
            "no_root":       ("#ff5555", "âŒ ChÆ°a cáº¥u hÃ¬nh","#2a0000"),
        }
        s_color, s_text, card_bg = status_meta.get(status, ("#888", "?", "#111120"))

        # Viá»n ná»•i báº­t theo tráº¡ng thÃ¡i
        border_colors = {
            "enabled": "#1a5a38", "disabled": "#5a3a00",
            "not_installed": "#2a2a4a", "no_root": "#5a0000",
        }
        border_c = border_colors.get(status, "#2a2a4a")

        card = tk.Frame(parent, bg=card_bg,
                        highlightbackground=border_c, highlightthickness=1)
        card.pack(fill="x", padx=14, pady=5)

        # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr = tk.Frame(card, bg=card_bg, padx=12, pady=8)
        hdr.pack(fill="x")

        tk.Label(hdr, text=f"{mod['icon']}  {mod['name']}",
                 bg=card_bg, fg="#e0e0ff",
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        
        ver_txt = f"v{mod['version']}"
        if installed_ver:
            ver_txt += f" (Äang cÃ i: {installed_ver})"
        tk.Label(hdr, text=ver_txt,
                 bg=card_bg, fg="#555",
                 font=("Consolas", 8)).pack(side="left", padx=8)
        tk.Label(hdr, text=s_text, bg=card_bg, fg=s_color,
                 font=("Segoe UI", 9, "bold")).pack(side="right")

        # â”€â”€ Description â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tk.Label(card, text=mod["desc"],
                 bg=card_bg, fg="#777",
                 font=("Segoe UI", 9), anchor="w"
                 ).pack(fill="x", padx=14, pady=(0, 4))

        # â”€â”€ URL row (áº©n vá»›i 2 mod máº·c Ä‘á»‹nh Ä‘á»ƒ UI gá»n) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        url_var = tk.StringVar(value=mod["url"])
        hide_url_for_default = mod.get("id") in {"paldefender", "ue4ss"}
        if not hide_url_for_default:
            url_f = tk.Frame(card, bg="#0d0d18", padx=12, pady=4)
            url_f.pack(fill="x")
            tk.Label(url_f, text="URL:", bg="#0d0d18", fg="#444",
                     font=("Segoe UI", 8), width=4, anchor="e"
                     ).pack(side="left")
            url_e = tk.Entry(url_f, textvariable=url_var,
                             bg="#0a0a12", fg="#555",
                             bd=0, font=("Consolas", 7),
                             insertbackground=self.ACCENT)
            url_e.pack(side="left", fill="x", expand=True, ipady=3, padx=(6, 0))

        # â”€â”€ Buttons â€” bá»‘ cá»¥c thÃ´ng minh theo tráº¡ng thÃ¡i â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        btn_f = tk.Frame(card, bg=card_bg, padx=12, pady=8)
        btn_f.pack(fill="x")

        if status == "no_root":
            # ChÆ°a cÃ³ Ä‘Æ°á»ng dáº«n server â†’ hiá»ƒn thá»‹ hÆ°á»›ng dáº«n
            tk.Label(btn_f,
                     text="â†’ VÃ o tab Cáº¥u HÃ¬nh, Ä‘iá»n SERVER_EXE rá»“i nháº¥n LÆ°u",
                     bg=card_bg, fg="#ff5555",
                     font=("Segoe UI", 9)).pack(side="left")

        elif status == "not_installed":
            # ChÆ°a cÃ i â†’ nÃºt chÃ­nh: táº£i + cÃ i + tá»± báº­t
            tk.Button(btn_f, text="â¬‡  Táº£i & CÃ i Ä‘áº·t",
                      bg=self.BTN_OK, fg="white",
                      relief="flat", padx=16, pady=7,
                      font=("Segoe UI", 10, "bold"), cursor="hand2",
                      command=lambda m=mod, uv=url_var: self._smart_action(m, uv.get())
                      ).pack(side="left", padx=(0, 6))
            tk.Label(btn_f,
                     text="â† Nháº¥n Ä‘á»ƒ táº£i vÃ  cÃ i tá»± Ä‘á»™ng",
                     bg=card_bg, fg="#444",
                     font=("Segoe UI", 8)).pack(side="left")

        elif has_update:
            # CÃ³ update -> NÃºt Cáº­p nháº­t
            tk.Button(btn_f, text=f"â¬†  Cáº­p nháº­t (v{mod['version']})",
                      bg="#0044cc", fg="white",
                      relief="flat", padx=16, pady=7,
                      font=("Segoe UI", 10, "bold"), cursor="hand2",
                      command=lambda m=mod, uv=url_var: self._mod_install(m, uv.get())
                      ).pack(side="left", padx=(0, 6))

        elif status == "disabled":
            # ÄÃ£ cÃ i nhÆ°ng Ä‘ang táº¯t â†’ nÃºt chÃ­nh: Báº­t (khÃ´ng táº£i láº¡i)
            tk.Button(btn_f, text="ðŸŸ¢  Báº­t mod",
                      bg=self.BTN_GRN, fg="#00ff88",
                      relief="flat", padx=16, pady=7,
                      font=("Segoe UI", 10, "bold"), cursor="hand2",
                      command=lambda m=mod: self._smart_action(m)
                      ).pack(side="left", padx=(0, 6))
            # NÃºt phá»¥: CÃ i láº¡i (náº¿u muá»‘n cáº­p nháº­t)
            tk.Button(btn_f, text="ðŸ”„  CÃ i láº¡i",
                      bg="#1c1c2e", fg="#888",
                      relief="flat", padx=10, pady=7,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda m=mod, uv=url_var: self._mod_install(m, uv.get())
                      ).pack(side="left", padx=(0, 6))
            tk.Button(btn_f, text="ðŸ—‘  Gá»¡ cÃ i Ä‘áº·t",
                      bg="#2a0000", fg="#ff8888",
                      relief="flat", padx=10, pady=7,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda m=mod: self._mod_uninstall(m)
                      ).pack(side="left", padx=(0, 6))
            tk.Label(btn_f,
                     text="â† ÄÃ£ cÃ i sáºµn, chá»‰ báº­t láº¡i (khÃ´ng táº£i láº¡i)",
                     bg=card_bg, fg="#555",
                     font=("Segoe UI", 8)).pack(side="left")

        elif status == "enabled":
            # Äang cháº¡y â†’ nÃºt táº¯t + nÃºt cÃ i láº¡i (phá»¥)
            tk.Button(btn_f, text="ðŸ”´  Táº¯t mod",
                      bg=self.BTN_RED, fg="#ff8888",
                      relief="flat", padx=16, pady=7,
                      font=("Segoe UI", 10, "bold"), cursor="hand2",
                      command=lambda m=mod: self._mod_disable(m)
                      ).pack(side="left", padx=(0, 6))
            tk.Button(btn_f, text="ðŸ”„  CÃ i láº¡i",
                      bg="#1c1c2e", fg="#888",
                      relief="flat", padx=10, pady=7,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda m=mod, uv=url_var: self._mod_install(m, uv.get())
                      ).pack(side="left", padx=(0, 6))
            tk.Button(btn_f, text="ðŸ—‘  Gá»¡ cÃ i Ä‘áº·t",
                      bg="#2a0000", fg="#ff8888",
                      relief="flat", padx=10, pady=7,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda m=mod: self._mod_uninstall(m)
                      ).pack(side="left", padx=(0, 6))

        # NÃºt má»Ÿ thÆ° má»¥c â€” luÃ´n hiá»‡n náº¿u target tá»“n táº¡i
        target_abs = os.path.join(self._pal_root() or "", mod["target"])
        if os.path.isdir(target_abs):
            tk.Button(btn_f, text="ðŸ“‚  Má»Ÿ thÆ° má»¥c",
                      bg="#1a1a1a", fg="#666",
                      relief="flat", padx=10, pady=7,
                      font=("Segoe UI", 9), cursor="hand2",
                      command=lambda p=target_abs: os.startfile(p)
                      ).pack(side="right")

    def _install_custom_mod(self):
        """CÃ i mod tá»« URL tÃ¹y chá»‰nh."""
        root = self._pal_root()
        if not root:
            messagebox.showerror("Lá»—i", "ChÆ°a cáº¥u hÃ¬nh SERVER_EXE!")
            return
        url    = self._custom_url.get().strip()
        name   = self._custom_name.get().strip() or "Custom Mod"
        target = self._custom_target.get().strip()
        if not url or url == "https://...":
            messagebox.showwarning("Thiáº¿u URL", "Nháº­p URL archive vÃ o Ã´ URL!")
            return
        target_abs = os.path.join(root, target)
        fake_mod = {"id": f"custom_{name}", "url": url, "name": name, "target": target, 
                    "version": datetime.datetime.now().strftime("%Y%m%d-%H%M")}
        self._mod_install(fake_mod, url)

    # â”€â”€ Console chung (bottom) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_console(self):
        con_frame = tk.Frame(self.root, bg="#0a0a0a", pady=2)
        con_frame.pack(fill="x", padx=8, pady=(0, 6))

        hdr = tk.Frame(con_frame, bg="#0d0d1a")
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸ“‹  Console / Log",
                 bg="#0d0d1a", fg="#666",
                 font=("Segoe UI", 8, "bold")).pack(side="left", padx=10, pady=3)
        tk.Button(hdr, text="ðŸ—‘ XÃ³a", bg="#0d0d1a", fg="#555",
                  relief="flat", font=("Segoe UI", 8),
                  command=lambda: self._console.delete("1.0", tk.END)
                  ).pack(side="right", padx=6, pady=2)

        self._console = scrolledtext.ScrolledText(
            con_frame, height=8, bg="#050505", fg="#00cc88",
            font=("Consolas", 8), bd=0, insertbackground="#00cc88",
            state="disabled"
        )
        self._console.pack(fill="x")

    # â”€â”€ Console write â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _log(self, text: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {text}\n"
        self._console.configure(state="normal")
        self._console.insert(tk.END, line)
        self._console.see(tk.END)
        self._console.configure(state="disabled")

    def _run_cmd_realtime(self, cmd: list, cwd: str = None) -> int:
        """Cháº¡y command vÃ  Ä‘áº©y log stdout/stderr vÃ o console thá»i gian thá»±c."""
        self._log(f"â–¶ Cháº¡y: {' '.join(cmd)}")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            assert proc.stdout is not None

            partial = ""
            while True:
                chunk = proc.stdout.read(1)
                if not chunk:
                    break
                if chunk == '\r':
                    # SteamCMD in progress qua carriage return; show ná»™i dung hiá»‡n táº¡i
                    progress_line = partial.strip()
                    if progress_line:
                        self.root.after(0, lambda l=progress_line: self._log(l))
                        # cáº­p nháº­t progress tá»« Ä‘á»‹nh dáº¡ng [ 42%]
                        m = re.search(r"\[(\s*\d{1,3})%\]", progress_line)
                        if m and hasattr(self, '_progress_var'):
                            pct = m.group(1).strip()
                            self.root.after(0, lambda p=pct: self._progress_var.set(f"Tiáº¿n trÃ¬nh: {p}%"))
                    partial = ""
                    continue
                if chunk == '\n':
                    line = partial.strip()
                    if line:
                        self.root.after(0, lambda l=line: self._log(l))
                        m = re.search(r"\[(\s*\d{1,3})%\]", line)
                        if m and hasattr(self, '_progress_var'):
                            pct = m.group(1).strip()
                            self.root.after(0, lambda p=pct: self._progress_var.set(f"Tiáº¿n trÃ¬nh: {p}%"))
                    partial = ""
                else:
                    partial += chunk
                    # Náº¿u output Ä‘ang cÃ³ % á»Ÿ giá»¯a dÃ²ng
                    if hasattr(self, '_progress_var'):
                        m = re.search(r"\[(\s*\d{1,3})%\]", partial)
                        if m:
                            pct = m.group(1).strip()
                            self.root.after(0, lambda p=pct: self._progress_var.set(f"Tiáº¿n trÃ¬nh: {p}%"))

            # Flush last chunk náº¿u khÃ´ng cÃ³ newline
            last_line = partial.strip()
            if last_line:
                self.root.after(0, lambda l=last_line: self._log(l))
                if hasattr(self, '_progress_var'):
                    m = re.search(r"\[(\s*\d{1,3})%\]", last_line)
                    if m:
                        pct = m.group(1).strip()
                        self.root.after(0, lambda p=pct: self._progress_var.set(f"Tiáº¿n trÃ¬nh: {p}%"))

            proc.wait()
            self._log(f"â¹ï¸ Hiá»‡n trÆ°á»ng lá»‡nh káº¿t thÃºc. Exit code: {proc.returncode}")
            return proc.returncode
        except Exception as e:
            self._log(f"âŒ Lá»—i cháº¡y lá»‡nh: {e}")
            return -1

    # â”€â”€ Derive PalWorldSettings.ini path â”€â”€â”€â”€â”€â”€
    def _derive_game_ini_path(self, server_exe: str) -> str:
        exe = _resolve_server_exe_path(server_exe)
        if not exe:
            return ""
        return os.path.join(
            os.path.dirname(exe),
            "Pal", "Saved", "Config", "WindowsServer", "PalWorldSettings.ini"
        )

    def _sync_manager_ini_to_game(self, show_popup: bool = True):
        """Äá»“ng bá»™ C:\\manager\\PalWorldSettings.ini vÃ o thÆ° má»¥c game theo SERVER_EXE."""
        src = MANAGER_PAL_SETTINGS_INI
        if not os.path.isfile(src):
            if show_popup:
                messagebox.showerror("Thiáº¿u file", f"KhÃ´ng tÃ¬m tháº¥y file nguá»“n:\n{src}")
            return False
        exe = self._vars.get("SERVER_EXE", tk.StringVar()).get().strip()
        dst = self._derive_game_ini_path(exe)
        if not dst:
            if show_popup:
                messagebox.showerror("Thiáº¿u Ä‘Æ°á»ng dáº«n", "SERVER_EXE chÆ°a há»£p lá»‡. Vui lÃ²ng chá»n Ä‘Ãºng PalServer.exe.")
            return False
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.isfile(dst):
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = f"{dst}.bak_{ts}"
                shutil.copy2(dst, backup)
                self._log(f"ðŸ—‚ï¸ Backup game INI: {backup}")
            shutil.copy2(src, dst)
            self._log(f"âœ… Äá»“ng bá»™ INI: {src} -> {dst}")
            if show_popup:
                messagebox.showinfo("ThÃ nh cÃ´ng", f"ÄÃ£ Ä‘á»“ng bá»™:\n{src}\n\nâ†’\n{dst}")
            return True
        except Exception as e:
            if show_popup:
                messagebox.showerror("Lá»—i Ä‘á»“ng bá»™ INI", str(e))
            self._log(f"âŒ Lá»—i Ä‘á»“ng bá»™ INI: {e}")
            return False

    def _manager_cfg_to_ini_updates(self, cfg: dict) -> dict:
        """Map manager_config fields -> PalWorldSettings OptionSettings keys."""
        updates = {}
        def _as_bool(v):
            s = str(v or "").strip().lower()
            if s in ("1", "true", "yes", "on"):
                return "True"
            if s in ("0", "false", "no", "off"):
                return "False"
            return ""
        admin_pw = ""
        for k in ("ADMIN_PASSWORD", "AUTH_PASS", "RCON_PASSWORD"):
            v = str(cfg.get(k, "") or "").strip()
            if v:
                admin_pw = v
                break
        if admin_pw:
            updates["AdminPassword"] = admin_pw
        rcon_enabled = _as_bool(cfg.get("RCON_ENABLED", ""))
        rest_enabled = _as_bool(cfg.get("RESTAPI_ENABLED", ""))
        show_player = _as_bool(cfg.get("SHOW_PLAYER_LIST", ""))
        if rcon_enabled:
            updates["RCONEnabled"] = rcon_enabled
        if rest_enabled:
            updates["RESTAPIEnabled"] = rest_enabled
        if show_player:
            updates["bShowPlayerList"] = show_player
        if admin_pw:
            updates.setdefault("RCONEnabled", "True")
            updates.setdefault("RESTAPIEnabled", "True")
        rcon_port = str(cfg.get("RCON_PORT", "") or "").strip()
        if rcon_port.isdigit():
            updates["RCONPort"] = rcon_port
            updates.setdefault("RCONEnabled", "True")
        public_port = str(cfg.get("PUBLIC_PORT", "") or "").strip()
        if public_port.isdigit():
            updates["PublicPort"] = public_port
        query_port = str(cfg.get("QUERY_PORT", "") or "").strip()
        if query_port.isdigit():
            updates["QueryPort"] = query_port
        api_url = str(cfg.get("API_URL", "") or "").strip()
        if api_url:
            try:
                p = urlparse(api_url)
                if p.port:
                    updates["RESTAPIPort"] = str(p.port)
                    updates.setdefault("RESTAPIEnabled", "True")
                host_from_api = (p.hostname or "").strip()
                if host_from_api and host_from_api.lower() not in ("127.0.0.1", "localhost"):
                    updates["PublicIP"] = host_from_api
            except Exception:
                pass
        host = str(cfg.get("RCON_HOST", "") or "").strip()
        if host and host.lower() not in ("127.0.0.1", "localhost"):
            updates["PublicIP"] = host
        return updates

    def _update_game_ini_from_manager_cfg(self, cfg: dict) -> bool:
        """Merge cÃ¡c field AppConfig quan trá»ng vÃ o PalWorldSettings.ini cá»§a game."""
        exe = self._vars.get("SERVER_EXE", tk.StringVar()).get().strip()
        ini_path = self._derive_game_ini_path(exe)
        if not ini_path or not os.path.isfile(ini_path):
            return False
        updates = self._manager_cfg_to_ini_updates(cfg)
        if not updates:
            return False
        try:
            with open(ini_path, "r", encoding="utf-8") as f:
                content = f.read()
            m = re.search(r'OptionSettings=\((.+)\)', content, re.DOTALL)
            if not m:
                return False
            inner = m.group(1)
            data = {}
            i, n = 0, len(inner)
            while i < n:
                j = i
                while j < n and inner[j] != '=':
                    j += 1
                if j >= n:
                    break
                key = inner[i:j].strip()
                i = j + 1
                if i >= n:
                    break
                if inner[i] == '"':
                    j = i + 1
                    while j < n and inner[j] != '"':
                        if inner[j] == '\\':
                            j += 1
                        j += 1
                    value = inner[i + 1:j]
                    i = j + 1
                elif inner[i] == '(':
                    depth, j = 0, i
                    while j < n:
                        if inner[j] == '(':
                            depth += 1
                        elif inner[j] == ')':
                            depth -= 1
                            if depth == 0:
                                break
                        j += 1
                    value = inner[i:j + 1]
                    i = j + 1
                else:
                    j = i
                    while j < n and inner[j] not in (',',):
                        j += 1
                    value = inner[i:j].strip()
                    i = j
                data[key] = value
                if i < n and inner[i] == ',':
                    i += 1

            data.update(updates)
            str_keys = {
                "ServerName", "ServerDescription", "AdminPassword", "ServerPassword",
                "PublicIP", "Region", "RandomizerSeed", "BanListURL",
                "AdditionalDropItemWhenPlayerKillingInPvPMode"
            }
            parts = []
            for k, v in data.items():
                if k in str_keys:
                    parts.append(f'{k}="{str(v).replace("\"", "\\\"")}"')
                else:
                    parts.append(f"{k}={v}")
            new_opt = "OptionSettings=(" + ",".join(parts) + ")"
            content = re.sub(r'OptionSettings=\(.+\)', new_opt, content, flags=re.DOTALL)
            with open(ini_path, "w", encoding="utf-8") as f:
                f.write(content)
            self._log(f"âœ… ÄÃ£ map AppConfig -> INI game: {ini_path}")
            return True
        except Exception as e:
            self._log(f"âš ï¸ KhÃ´ng thá»ƒ map AppConfig vÃ o INI game: {e}")
            return False

    def _update_ini_label(self):
        exe = self._vars.get("SERVER_EXE", tk.StringVar()).get().strip()
        if exe:
            derived = self._derive_game_ini_path(exe)
            if hasattr(self, "_lbl_ini_path"):
                self._lbl_ini_path.config(text=f"â¬† tá»± tÃ­nh â†’ {derived}")

    # â”€â”€ Load config â†’ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _load_to_ui(self):
        cfg = load_config()
        for key, var in self._vars.items():
            var.set(cfg.get(key, CONFIG_TEMPLATE.get(key, "")))
        # Update steamcmd label if tab already built
        if hasattr(self, "_lbl_steamcmd_path"):
            self._lbl_steamcmd_path.config(
                text=cfg.get("STEAMCMD_EXE", "(chÆ°a cáº¥u hÃ¬nh)"))
        self._update_ini_label()
        self._log("ÄÃ£ táº£i cáº¥u hÃ¬nh tá»« " + CONFIG_FILE)

    # â”€â”€ Save UI â†’ config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _save(self):
        data = {k: v.get().strip() for k, v in self._vars.items()}
        if save_config(data):
            if hasattr(self, "_lbl_steamcmd_path"):
                self._lbl_steamcmd_path.config(
                    text=data.get("STEAMCMD_EXE", "(chÆ°a cáº¥u hÃ¬nh)"))
            # Tá»± Ä‘á»“ng bá»™ INI náº¿u cÃ³ file máº«u trong thÆ° má»¥c manager.
            if os.path.isfile(MANAGER_PAL_SETTINGS_INI):
                self._sync_manager_ini_to_game(show_popup=False)
            self._update_game_ini_from_manager_cfg(data)
            self._log("âœ… ÄÃ£ lÆ°u cáº¥u hÃ¬nh")
            messagebox.showinfo("ThÃ nh cÃ´ng", "ÄÃ£ lÆ°u manager_config.json!")

    # â”€â”€ Launch serverpal.py â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _launch_serverpal(self):
        # TrÃ¡nh khá»Ÿi Ä‘á»™ng serverpal trong lÃºc auto-install requirements Ä‘ang cháº¡y.
        if getattr(self, "_auto_pip_running", False):
            messagebox.showwarning(
                "Äang cÃ i packages",
                "setup.py Ä‘ang auto-install dependencies. Äá»£i cÃ i xong rá»“i hÃ£y Start serverpal.py."
            )
            return

        if self._serverpal_proc and self._serverpal_proc.poll() is None:
            messagebox.showwarning("Äang cháº¡y", "Báº£ng Ä‘iá»u khiá»ƒn Ä‘Ã£ Ä‘ang cháº¡y!")
            return
        target_serverpal = SERVERPAL_EXE if os.path.isfile(SERVERPAL_EXE) else SERVERPAL_PY
        if not os.path.isfile(target_serverpal):
            messagebox.showerror("Lá»—i", f"KhÃ´ng tÃ¬m tháº¥y:\n{SERVERPAL_EXE}\nhoáº·c\n{SERVERPAL_PY}")
            return
        try:
            # Báº£n phÃ¡t hÃ nh full dÃ¹ng Manager_ServerPal_App.exe (khÃ´ng cáº§n Python trÃªn mÃ¡y ngÆ°á»i dÃ¹ng).
            # Náº¿u chÆ°a cÃ³ exe thÃ¬ fallback cháº¡y serverpal.py qua pythonw/.venv.
            if target_serverpal.lower().endswith(".exe"):
                self._serverpal_proc = subprocess.Popen(
                    [target_serverpal],
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            else:
                py_exec = VENV_PYTHONW if os.path.isfile(VENV_PYTHONW) else self._get_python_exec(ensure_venv=True)
                py_exec = str(py_exec).strip().strip('"').strip("'")
                if not py_exec:
                    messagebox.showerror("Thiáº¿u Python", "KhÃ´ng tÃ¬m tháº¥y Python Ä‘á»ƒ cháº¡y serverpal.py")
                    return
                self._serverpal_proc = subprocess.Popen(
                    [py_exec, target_serverpal],
                    cwd=BASE_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            self._lbl_run_status.config(text="â— Äang cháº¡y", fg="#00ff88")
            self._btn_start.config(state="disabled")
            if hasattr(self, "_btn_restart"):
                self._btn_restart.config(state="normal")
            self._btn_stop.config(state="normal")
            self._log(f"â–¶ Start ServerPal: {target_serverpal} (PID {self._serverpal_proc.pid})")

            def _stream():
                try:
                    if not self._serverpal_proc or not self._serverpal_proc.stdout:
                        return
                    for line in self._serverpal_proc.stdout:
                        stripped = (line or "").rstrip()
                        if stripped:
                            self.root.after(0, lambda l=stripped: self._log(l))
                except Exception as e:
                    self.root.after(0, lambda: self._log(f"âŒ Stream serverpal stdout lá»—i: {e}"))

            threading.Thread(target=_stream, daemon=True).start()

            # Poll khi process káº¿t thÃºc
            self.root.after(1000, self._poll_serverpal)
        except Exception as e:
            messagebox.showerror("Lá»—i", str(e))

    def _poll_serverpal(self):
        if self._serverpal_proc and self._serverpal_proc.poll() is not None:
            code = self._serverpal_proc.returncode
            self._lbl_run_status.config(text=f"â— ÄÃ£ dá»«ng (exit {code})", fg="#ff5555")
            self._btn_start.config(state="normal")
            self._btn_stop.config(state="disabled")
            if hasattr(self, "_btn_restart"):
                self._btn_restart.config(state="normal")
            self._log(f"â¹ ServerPal Ä‘Ã£ dá»«ng (exit code {code})")
        else:
            self.root.after(1000, self._poll_serverpal)

    def _stop_serverpal(self):
        if self._serverpal_proc and self._serverpal_proc.poll() is None:
            self._serverpal_proc.terminate()
            self._log("â¹ ÄÃ£ gá»­i lá»‡nh táº¯t báº£ng Ä‘iá»u khiá»ƒn")

    def _restart_serverpal(self):
        """Restart serverpal.py without blocking the UI thread."""
        def _do_restart():
            try:
                if self._serverpal_proc and self._serverpal_proc.poll() is None:
                    self._log("â³ Restart serverpal.py: Ä‘ang dá»«ng tiáº¿n trÃ¬nh cÅ©...")
                    try:
                        self._serverpal_proc.terminate()
                    except Exception:
                        pass
                    # Chá» tá»‘i Ä‘a ~5s Ä‘á»ƒ tiáº¿n trÃ¬nh táº¯t háº³n
                    deadline = time.time() + 5
                    while time.time() < deadline:
                        if self._serverpal_proc.poll() is not None:
                            break
                        time.sleep(0.1)
            finally:
                self._serverpal_proc = None
                self.root.after(0, self._launch_serverpal)

        threading.Thread(target=_do_restart, daemon=True).start()

    # â”€â”€ Update helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _resolve_steamcmd_exe(self) -> str:
        steamcmd = self._vars.get("STEAMCMD_EXE", tk.StringVar()).get().strip()
        if not steamcmd:
            cfg = load_config()
            steamcmd = cfg.get("STEAMCMD_EXE", "")
        return steamcmd

    def _get_repo_slug(self) -> str:
        repo = self._vars.get("GITHUB_REPO", tk.StringVar()).get().strip()
        if not repo:
            cfg = load_config()
            repo = str(cfg.get("GITHUB_REPO", "") or "").strip()
        repo = repo.replace("https://github.com/", "").strip().strip("/")
        return repo

    def _is_truthy(self, value) -> bool:
        return str(value or "").strip().lower() in ("1", "true", "yes", "on")

    def _version_tuple(self, s: str) -> tuple[int, int, int]:
        txt = str(s or "").strip().lower().lstrip("v")
        nums = re.findall(r"\d+", txt)
        if not nums:
            return (0, 0, 0)
        parts = [int(x) for x in nums[:3]]
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts)  # type: ignore[return-value]

    def _open_repo_releases(self):
        repo = self._get_repo_slug()
        if not repo:
            messagebox.showwarning("Thiáº¿u repo", "Äiá»n GITHUB_REPO trÆ°á»›c, vÃ­ dá»¥: owner/repo")
            return
        webbrowser.open(f"https://github.com/{repo}/releases")

    def _auto_check_app_update_once(self):
        try:
            auto_check = self._vars.get("AUTO_UPDATE_CHECK", tk.StringVar(value="true")).get()
            if self._is_truthy(auto_check):
                self._check_app_update(silent=True)
        except Exception:
            pass

    def _fetch_latest_release_payload(self, repo: str) -> dict | None:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "ManagerServerPal-Updater/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        tag = str(data.get("tag_name", "") or "").strip().lstrip("v")
        assets = data.get("assets", []) or []
        installer_url = ""
        for a in assets:
            name = str(a.get("name", "") or "").lower()
            dl = str(a.get("browser_download_url", "") or "").strip()
            if name.startswith("manager_serverpal_setup_") and name.endswith(".exe") and dl:
                installer_url = dl
                break
        if not installer_url:
            for a in assets:
                name = str(a.get("name", "") or "").lower()
                dl = str(a.get("browser_download_url", "") or "").strip()
                if name.endswith(".exe") and dl:
                    installer_url = dl
                    break
        # Fallback chuyÃªn dá»¥ng: láº¥y installer tá»« source repo (khÃ´ng phá»¥ thuá»™c release asset).
        if not installer_url and tag:
            raw_url = f"https://github.com/{repo}/raw/main/release/Manager_ServerPal_Setup_v{tag}.exe"
            try:
                req = urllib.request.Request(
                    raw_url,
                    method="HEAD",
                    headers={"User-Agent": "ManagerServerPal-Updater/1.0"},
                )
                with urllib.request.urlopen(req, timeout=15) as _:
                    installer_url = raw_url
            except Exception:
                pass
        body = str(data.get("body", "") or "").strip()
        return {
            "version": tag,
            "installer_url": installer_url,
            "release_url": str(data.get("html_url", "") or "").strip(),
            "notes": body,
        }

    def _check_app_update(self, silent: bool = False):
        repo = self._get_repo_slug()
        if not repo:
            if not silent:
                messagebox.showwarning("Thiáº¿u repo", "Äiá»n GITHUB_REPO trÆ°á»›c, vÃ­ dá»¥: owner/repo")
            return

        self._log(f"ðŸ”Ž Äang kiá»ƒm tra báº£n má»›i tá»« GitHub: {repo}")

        def _worker():
            try:
                payload = self._fetch_latest_release_payload(repo)
                if not payload:
                    raise RuntimeError("KhÃ´ng Ä‘á»c Ä‘Æ°á»£c thÃ´ng tin release.")
                latest = str(payload.get("version", "") or "")
                if not latest:
                    raise RuntimeError("Release khÃ´ng cÃ³ tag version.")
                cur_v = self._version_tuple(APP_VERSION)
                new_v = self._version_tuple(latest)
                if new_v > cur_v:
                    self._latest_update_payload = payload
                    msg = f"CÃ³ báº£n má»›i: v{latest} (hiá»‡n táº¡i v{APP_VERSION})"
                    self.root.after(0, lambda m=msg: self._lbl_update_status.config(text=m, fg="#66ff88"))
                    self.root.after(0, lambda m=msg: self._log(f"âœ… {m}"))
                    if silent:
                        self.root.after(
                            0,
                            lambda: self._log("â„¹ï¸ Auto-check chá»‰ phÃ¡t hiá»‡n phiÃªn báº£n má»›i; táº£i/cÃ i do báº¡n báº¥m nÃºt 'Táº£i & cÃ i báº£n má»›i'.")
                        )
                    if not silent:
                        note = payload.get("notes", "") or "(khÃ´ng cÃ³ release notes)"
                        preview = note[:800] + ("..." if len(note) > 800 else "")
                        self.root.after(0, lambda: messagebox.showinfo("CÃ³ báº£n má»›i", f"{msg}\n\n{preview}"))
                else:
                    msg = f"ÄÃ£ má»›i nháº¥t: v{APP_VERSION}"
                    self.root.after(0, lambda m=msg: self._lbl_update_status.config(text=m, fg="#8ab4f8"))
                    if not silent:
                        self.root.after(0, lambda: messagebox.showinfo("Update", msg))
                    self.root.after(0, lambda m=msg: self._log(f"â„¹ï¸ {m}"))
            except Exception as e:
                self.root.after(0, lambda e=e: self._lbl_update_status.config(
                    text=f"Lá»—i check update: {e}", fg="#ff6666"))
                self.root.after(0, lambda e=e: self._log(f"âŒ Check update lá»—i: {e}"))
                if not silent:
                    self.root.after(0, lambda e=e: messagebox.showerror("Lá»—i update", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _install_latest_update(self):
        payload = self._latest_update_payload
        if not payload:
            if messagebox.askyesno("ChÆ°a cÃ³ dá»¯ liá»‡u", "ChÆ°a check update. Kiá»ƒm tra ngay bÃ¢y giá»?"):
                self._check_app_update(silent=False)
            return
        installer_url = str(payload.get("installer_url", "") or "").strip()
        release_url = str(payload.get("release_url", "") or "").strip()
        latest = str(payload.get("version", "") or "").strip()
        if not installer_url:
            if release_url:
                if messagebox.askyesno("KhÃ´ng cÃ³ link installer", "Release khÃ´ng cÃ³ file setup .exe. Má»Ÿ trang release?"):
                    webbrowser.open(release_url)
            else:
                messagebox.showerror("Lá»—i", "KhÃ´ng tÃ¬m tháº¥y installer_url trong GitHub release.")
            return

        if not messagebox.askyesno("XÃ¡c nháº­n cáº­p nháº­t", f"Táº£i vÃ  cÃ i v{latest} ngay bÃ¢y giá»?"):
            return

        def _worker():
            try:
                fn = os.path.basename(urlparse(installer_url).path) or f"Manager_ServerPal_Setup_v{latest}.exe"
                dst = os.path.join(tempfile.gettempdir(), fn)
                self.root.after(0, lambda: self._log(f"â¬‡ Äang táº£i installer: {installer_url}"))
                urllib.request.urlretrieve(installer_url, dst)
                if not os.path.isfile(dst):
                    raise RuntimeError("Táº£i installer tháº¥t báº¡i.")

                # Hash Ä‘á»ƒ log kiá»ƒm chá»©ng táº£i file (khÃ´ng cÃ³ manifest checksum thÃ¬ váº«n log local SHA256).
                h = hashlib.sha256()
                with open(dst, "rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
                sha = h.hexdigest()
                self.root.after(0, lambda sha=sha: self._log(f"ðŸ” SHA256 installer: {sha}"))

                self.root.after(0, lambda p=dst: self._log(f"ðŸš€ Má»Ÿ installer: {p}"))
                subprocess.Popen([dst], cwd=os.path.dirname(dst))
                self.root.after(0, self.root.destroy)
            except Exception as e:
                self.root.after(0, lambda e=e: self._log(f"âŒ Cáº­p nháº­t tháº¥t báº¡i: {e}"))
                self.root.after(0, lambda e=e: messagebox.showerror("Lá»—i cáº­p nháº­t", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _ensure_steamcmd_ready(self) -> str:
        steamcmd = self._resolve_steamcmd_exe()
        if not os.path.isfile(steamcmd):
            messagebox.showerror(
                "Thiáº¿u SteamCMD",
                f"KhÃ´ng tÃ¬m tháº¥y SteamCMD.exe táº¡i:\n{steamcmd}\n\n"
                "Vui lÃ²ng:\n"
                "1. Táº£i SteamCMD tá»« link trong tab Update\n"
                "2. Cáº­p nháº­t Ä‘Æ°á»ng dáº«n trong tab Cáº¥u HÃ¬nh â†’ STEAMCMD_EXE\n"
                "3. Nháº¥n LÆ°u cáº¥u hÃ¬nh rá»“i thá»­ láº¡i"
            )
            return ""
        return steamcmd

    def _run_preflight_check(self, require_steamcmd: bool = True) -> tuple[bool, str]:
        """Preflight trÆ°á»›c update: Python, pip, internet, steamcmd.exe."""
        self._log("ðŸ”Ž Preflight check trÆ°á»›c khi update...")
        ok = True

        # 1) Python version
        if IS_FROZEN_APP:
            self._log("â„¹ï¸ Báº£n Ä‘Ã³ng gÃ³i EXE: bá» qua check Python/pip.")
        else:
            py_ok = sys.version_info >= (3, 10)
            self._log(f"{'âœ…' if py_ok else 'âŒ'} Python >= 3.10: {sys.version.split()[0]}")
            ok = ok and py_ok

            # 2) pip
            pip_ok = False
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "pip", "--version"],
                    capture_output=True, text=True, timeout=10
                )
                pip_ok = (r.returncode == 0)
                pip_txt = (r.stdout or r.stderr).strip()
                self._log(f"{'âœ…' if pip_ok else 'âŒ'} pip: {pip_txt or 'khÃ´ng xÃ¡c Ä‘á»‹nh'}")
            except Exception as e:
                self._log(f"âŒ pip check lá»—i: {e}")
            ok = ok and pip_ok

        # 3) Admin quyá»n (khÃ´ng báº¯t buá»™c)
        admin_ok = False
        try:
            admin_ok = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            admin_ok = False
        if admin_ok:
            self._log("âœ… Quyá»n hiá»‡n táº¡i: Administrator")
        else:
            self._log("â„¹ï¸ Quyá»n hiá»‡n táº¡i: User thÆ°á»ng (khÃ´ng cáº§n admin Ä‘á»ƒ cháº¡y app)")

        # 4) Internet
        net_ok = False
        try:
            urllib.request.urlopen("https://steamcdn-a.akamaihd.net", timeout=6)
            net_ok = True
        except Exception as e:
            self._log(f"âŒ Internet check lá»—i: {e}")
        if net_ok:
            self._log("âœ… Internet káº¿t ná»‘i OK")
        ok = ok and net_ok

        # 5) steamcmd.exe
        steamcmd = self._resolve_steamcmd_exe()
        steam_ok = os.path.isfile(steamcmd) if steamcmd else False
        if steam_ok:
            self._log(f"âœ… steamcmd.exe: {steamcmd}")
        else:
            self._log("âŒ steamcmd.exe: chÆ°a cáº¥u hÃ¬nh hoáº·c file khÃ´ng tá»“n táº¡i")
            if not require_steamcmd:
                self._log("â„¹ï¸ Sáº½ tiáº¿p tá»¥c vÃ¬ cháº¿ Ä‘á»™ update SteamCMD cÃ³ thá»ƒ tá»± táº£i má»›i.")
                steam_ok = True
        ok = ok and steam_ok

        self._log("âœ… Preflight PASS" if ok else "âŒ Preflight FAIL")
        return ok, steamcmd

    def _run_game_update(self):
        pre_ok, _ = self._run_preflight_check(require_steamcmd=True)
        if not pre_ok:
            messagebox.showerror("Preflight tháº¥t báº¡i", "Preflight check tháº¥t báº¡i. Xem log Ä‘á»ƒ sá»­a lá»—i rá»“i thá»­ láº¡i.")
            return
        self._run_update_game(validate=False)

    def _run_game_validate(self):
        pre_ok, _ = self._run_preflight_check(require_steamcmd=True)
        if not pre_ok:
            messagebox.showerror("Preflight tháº¥t báº¡i", "Preflight check tháº¥t báº¡i. Xem log Ä‘á»ƒ sá»­a lá»—i rá»“i thá»­ láº¡i.")
            return
        self._run_update_game(validate=True)

    def _run_update_game(self, validate: bool):
        steamcmd = self._ensure_steamcmd_ready()
        if not steamcmd:
            return
        cmd = [
            steamcmd,
            "+login", "anonymous",
            "+app_update", PALWORLD_APPID,
            "+quit"
        ]
        if validate:
            cmd.insert(-1, "validate")
        self._log(f"ðŸŽ® Báº¯t Ä‘áº§u update game PalServer (App ID {PALWORLD_APPID})...")
        self._log("   " + " ".join(cmd))
        threading.Thread(target=self._run_cmd_bg, args=(cmd,), daemon=True).start()

    def _run_steamcmd_update(self):
        """Cáº­p nháº­t riÃªng SteamCMD (khÃ´ng Ä‘á»¥ng game files)."""
        pre_ok, _ = self._run_preflight_check(require_steamcmd=False)
        if not pre_ok:
            messagebox.showerror("Preflight tháº¥t báº¡i", "Preflight check tháº¥t báº¡i. Xem log Ä‘á»ƒ sá»­a lá»—i rá»“i thá»­ láº¡i.")
            return
        steamcmd = self._resolve_steamcmd_exe()
        steamcmd_dir = os.path.dirname(steamcmd) if steamcmd else ""
        if not steamcmd_dir:
            cfg = load_config()
            steamcmd = cfg.get("STEAMCMD_EXE", "")
            steamcmd_dir = os.path.dirname(steamcmd) if steamcmd else ""
        if not steamcmd_dir:
            steamcmd_dir = r"C:\steamcmd"

        def _do():
            try:
                os.makedirs(steamcmd_dir, exist_ok=True)
                zip_url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
                zip_path = os.path.join(steamcmd_dir, "steamcmd_update.zip")
                self.root.after(0, lambda: self._log("ðŸ›  Äang táº£i báº£n SteamCMD má»›i nháº¥t..."))
                urllib.request.urlretrieve(zip_url, zip_path)
                self.root.after(0, lambda: self._log("ðŸ“¦ Äang giáº£i nÃ©n cáº­p nháº­t SteamCMD..."))
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(steamcmd_dir)
                try:
                    os.remove(zip_path)
                except Exception:
                    pass
                steamcmd_exe = os.path.join(steamcmd_dir, "steamcmd.exe")
                cfg = load_config()
                cfg["STEAMCMD_EXE"] = steamcmd_exe
                save_config(cfg)
                self.root.after(0, lambda p=steamcmd_exe: self._log(f"âœ… SteamCMD Ä‘Ã£ cáº­p nháº­t: {p}"))
                if hasattr(self, "_lbl_steamcmd_path"):
                    self.root.after(0, lambda p=steamcmd_exe: self._lbl_steamcmd_path.config(text=p))
            except Exception as e:
                self.root.after(0, lambda e=e: self._log(f"âŒ Update SteamCMD lá»—i: {e}"))

        threading.Thread(target=_do, daemon=True).start()

    def _open_steamcmd_dir(self):
        steamcmd = self._vars.get("STEAMCMD_EXE", tk.StringVar()).get().strip()
        if steamcmd and os.path.dirname(steamcmd):
            d = os.path.dirname(steamcmd)
            if os.path.isdir(d):
                os.startfile(d)
                return
        messagebox.showinfo("ThÃ´ng bÃ¡o", "ChÆ°a cáº¥u hÃ¬nh Ä‘Æ°á»ng dáº«n STEAMCMD_EXE")

    # â”€â”€ Install packages â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _pip_install(self):
        if IS_FROZEN_APP:
            messagebox.showinfo("ÄÃ£ khÃ³a runtime", "Báº£n EXE phÃ¡t hÃ nh khÃ´ng cáº§n vÃ  khÃ´ng há»— trá»£ cÃ i pip runtime.")
            return
        if not os.path.isfile(REQ_FILE):
            messagebox.showerror("Lá»—i", f"KhÃ´ng tÃ¬m tháº¥y:\n{REQ_FILE}")
            return
        py_exec = self._get_python_exec(ensure_venv=True)
        py_exec = str(py_exec).strip().strip('"').strip("'")
        if not py_exec:
            messagebox.showerror("Thiáº¿u Python", "KhÃ´ng tÃ¬m tháº¥y Python há»‡ thá»‘ng Ä‘á»ƒ táº¡o .venv vÃ  cÃ i packages.")
            return
        cmd = [py_exec, "-m", "pip", "install",
               "-r", REQ_FILE, "--disable-pip-version-check"]
        self._log("ðŸ Báº¯t Ä‘áº§u pip install -r requirements.txt vÃ o .venv ...")
        # Force UTF-8 Ä‘á»ƒ pip Ä‘á»c Ä‘Æ°á»£c file requirements.txt chá»©a kÃ½ tá»± Ä‘áº·c biá»‡t
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        threading.Thread(target=self._run_cmd_bg, args=(cmd,), kwargs={"env": env}, daemon=True).start()

    def _npm_install(self):
        if IS_FROZEN_APP:
            messagebox.showinfo("ÄÃ£ khÃ³a runtime", "Báº£n EXE phÃ¡t hÃ nh khÃ´ng cáº§n vÃ  khÃ´ng há»— trá»£ npm runtime.")
            return
        if not os.path.isdir(MAP_DIR):
            self._log("â„¹ï¸ KhÃ´ng tháº¥y palserver-online-map-main. Bá» qua npm install (khÃ´ng cáº§n cho Live Map embedded).")
            return
        npm_exec = "npm.cmd" if os.name == "nt" else "npm"
        self._log("ðŸŸ© Báº¯t Ä‘áº§u npm install trong palserver-online-map-main ...")
        os.makedirs(NPM_CACHE_DIR, exist_ok=True)
        env = os.environ.copy()
        env["npm_config_cache"] = NPM_CACHE_DIR
        threading.Thread(
            target=self._run_cmd_bg,
            args=([npm_exec, "install"],),
            kwargs={"cwd": MAP_DIR, "env": env},
            daemon=True
        ).start()

    def _check_versions(self):
        def _do():
            npm_exec = "npm.cmd" if os.name == "nt" else "npm"
            for cmd, label in [
                ([sys.executable, "--version"], "Python"),
                (["node", "--version"],         "Node.js"),
                ([npm_exec, "--version"],        "npm"),
            ]:
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    v = (r.stdout or r.stderr).strip()
                    self.root.after(0, lambda l=label, v=v: self._log(f"  {l}: {v}"))
                except Exception as e:
                    self.root.after(0, lambda l=label, e=e: self._log(f"  {l}: âŒ {e}"))
        self._log("ðŸ” Kiá»ƒm tra phiÃªn báº£n...")
        threading.Thread(target=_do, daemon=True).start()

    def _show_requirements(self):
        if os.path.isfile(REQ_FILE):
            with open(REQ_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            win = tk.Toplevel(self.root)
            win.title("requirements.txt")
            win.configure(bg=self.BG)
            win.geometry("500x300")
            t = scrolledtext.ScrolledText(win, bg="#050505", fg="#00cc88",
                                          font=("Consolas", 9), bd=0)
            t.pack(fill="both", expand=True, padx=8, pady=8)
            t.insert(tk.END, content)
            t.configure(state="disabled")

    # â”€â”€ Run command in background â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _run_cmd_bg(self, cmd: list, cwd: str = None, **kwargs):
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                cwd=cwd or BASE_DIR,
                **kwargs
            )
            for line in proc.stdout:
                stripped = line.rstrip()
                if stripped:
                    self.root.after(0, lambda l=stripped: self._log(l))
            proc.wait()
            code = proc.returncode
            msg = "âœ… HoÃ n thÃ nh" if code == 0 else f"âš ï¸ Káº¿t thÃºc (exit {code})"
            self.root.after(0, lambda m=msg: self._log(m))
        except FileNotFoundError as e:
            self.root.after(0, lambda: self._log(f"âŒ Lá»‡nh khÃ´ng tá»“n táº¡i: {e}"))
        except Exception as e:
            self.root.after(0, lambda: self._log(f"âŒ Lá»—i: {e}"))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    root = tk.Tk()
    app  = SetupApp(root)
    root.mainloop()

