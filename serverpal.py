import tkinter as tk
import concurrent.futures
from tkinter import scrolledtext, messagebox, ttk, simpledialog
import requests
from requests.auth import HTTPBasicAuth
import threading
import time
import datetime
import subprocess
import os
import shutil
import psutil
import sys
import ctypes
import socket
import struct
import queue
import webbrowser
import re
import json
import secrets
import random
from collections import deque
from urllib.parse import urlparse
import app_config as cfgmod
import antibug_system as antibug_core
import antibug_enforcer as antibug_enf

try:
    from PIL import Image, ImageTk, ImageDraw
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# --- ADMIN CHECK ---
# Không tự nâng quyền admin khi mở app; cho phép chạy bằng user thường.
try:
    IS_ADMIN = bool(ctypes.windll.shell32.IsUserAnAdmin())
except Exception:
    IS_ADMIN = False

# ─────────────────────────────────────────────
#  ĐƯỜNG DẪN CONFIG/ASSET
#  - .py: dùng thư mục source
#  - frozen .exe: config ở thư mục .exe, asset/module từ bundle tạm
# ─────────────────────────────────────────────
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
    _BUNDLE_DIR = getattr(sys, "_MEIPASS", _APP_DIR)
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))
    _BUNDLE_DIR = _APP_DIR

_MANAGER_DIR        = _APP_DIR
sys.path.insert(0, os.path.join(_BUNDLE_DIR, '_datadb'))
UI_ASSETS_DIR       = os.path.join(_BUNDLE_DIR, "_ui_assets")
UI_ICON_PNG         = os.path.join(UI_ASSETS_DIR, "app_icon.png")
MANAGER_CONFIG_FILE = os.path.join(_MANAGER_DIR, "manager_config.json")
MANAGER_PAL_SETTINGS_INI = os.path.join(_MANAGER_DIR, "PalWorldSettings.ini")

# ─────────────────────────────────────────────
#  ĐỌC manager_config.json (trước khi khai báo constants)
# ─────────────────────────────────────────────
def _read_manager_cfg() -> dict:
    """Đọc manager_config.json, trả về dict (rỗng nếu chưa có file)."""
    try:
        if os.path.isfile(MANAGER_CONFIG_FILE):
            with open(MANAGER_CONFIG_FILE, "r", encoding="utf-8") as _f:
                return json.load(_f)
    except Exception:
        pass
    return {}

_CFG = _read_manager_cfg()

def _cfg(key, default):
    """Lấy giá trị từ config, fallback về default nếu không có."""
    v = _CFG.get(key)
    if v is None or (isinstance(v, str) and not v.strip()):
        return default
    return v.strip() if isinstance(v, str) else v

def _cfg_bool(key: str, default: bool) -> bool:
    v = _CFG.get(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    return default

def _cfg_int(key: str, default: int) -> int:
    v = _CFG.get(key, default)
    try:
        return int(str(v).strip())
    except Exception:
        return default

def _resolve_server_exe_from_cfg(path_hint: str, fallback: str) -> str:
    """Chuẩn hóa SERVER_EXE từ config (nhận cả file hoặc thư mục)."""
    p = (path_hint or "").strip().strip('"') if isinstance(path_hint, str) else ""
    if not p:
        return fallback
    p = os.path.abspath(p)
    if os.path.isfile(p):
        if os.path.basename(p).lower() == "palserver.exe":
            return p
        base_dir = os.path.dirname(p)
        direct = os.path.join(base_dir, "PalServer.exe")
        if os.path.isfile(direct):
            return direct
        for root, _, files in os.walk(base_dir):
            for fn in files:
                if fn.lower() == "palserver.exe":
                    return os.path.join(root, fn)
        return fallback
    if os.path.isdir(p):
        direct = os.path.join(p, "PalServer.exe")
        if os.path.isfile(direct):
            return direct
        for root, _, files in os.walk(p):
            for fn in files:
                if fn.lower() == "palserver.exe":
                    return os.path.join(root, fn)
    return fallback

def _resolve_shared_admin_password(cfg: dict) -> str:
    """Lấy mật khẩu admin dùng chung cho REST/RCON."""
    for key in ("AUTH_PASS", "RCON_PASSWORD", "ADMIN_PASSWORD"):
        v = cfg.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "Admin#123"

# ─────────────────────────────────────────────
#  CẤU HÌNH SERVER  (tự động đọc từ manager_config.json)
# ─────────────────────────────────────────────
_DEFAULT_SERVER_EXE = r"C:\palwordsteamserver\steamapps\common\PalServer\PalServer.exe"
SERVER_EXE    = _resolve_server_exe_from_cfg(_CFG.get("SERVER_EXE", ""), _DEFAULT_SERVER_EXE)
API_URL       = _cfg("API_URL",       "http://127.0.0.1:8212/v1/api")
_SHARED_ADMIN_PASSWORD = _resolve_shared_admin_password(_CFG)
AUTH          = HTTPBasicAuth("admin", _SHARED_ADMIN_PASSWORD)
RCON_HOST     = _cfg("RCON_HOST",     "127.0.0.1")
RCON_PORT     = int(_cfg("RCON_PORT", 25575))
# Toggle để bật/tắt kiểm tra health sau khởi động (theo yêu cầu có thể tắt hẳn)
STARTUP_HEALTH_CHECK_ENABLED = _cfg_bool("STARTUP_HEALTH_CHECK_ENABLED", False)
STARTUP_LOG_READY_CHECK_ENABLED = _cfg_bool("STARTUP_LOG_READY_CHECK_ENABLED", True)
RCON_PASSWORD = _cfg("RCON_PASSWORD", _SHARED_ADMIN_PASSWORD)
RESET_SCHEDULE = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]
DISCORD_WEBHOOK_URL = _cfg("DISCORD_WEBHOOK_URL", "")

# ── Tất cả path tự động derive từ SERVER_EXE ──────────────────────────
def _derive_paths(server_exe: str) -> tuple:
    """Tính toàn bộ đường dẫn PalServer từ SERVER_EXE (không cần config thêm).
    Trả về: (PAL_SETTINGS_INI, SERVER_LOG_FILE, PALDEF_LOG_DIR,
              PALDEF_CHEATS_DIR, PALDEF_REST_DIR, GIFT_SAVE_DIR)
    """
    root = os.path.dirname(server_exe)
    pal  = os.path.join(root, "Pal")
    return (
        os.path.join(pal, "Saved", "Config", "WindowsServer", "PalWorldSettings.ini"),
        os.path.join(pal, "Saved", "Logs", "PalServer.log"),
        os.path.join(pal, "Binaries", "Win64", "PalDefender", "Logs"),
        os.path.join(pal, "Binaries", "Win64", "PalDefender", "Logs", "Cheats"),
        os.path.join(pal, "Binaries", "Win64", "PalDefender", "RESTAPI"),
        os.path.join(pal, "Saved",    "SaveGames", "quatanthu"),
    )

(PAL_SETTINGS_INI,
 SERVER_LOG_FILE,
 PALDEF_LOG_DIR,
 PALDEF_CHEATS_DIR,
 PALDEF_REST_DIR,
 GIFT_SAVE_DIR)       = _derive_paths(SERVER_EXE)

# Thư mục SaveGames gốc (ngoài thư mục con quatanthu).
SAVE_GAMES_DIR = os.path.dirname(GIFT_SAVE_DIR)

# ── PalDefender token paths (derive từ PALDEF_REST_DIR) ──────────────
PALDEF_TOKEN_DIR  = os.path.join(PALDEF_REST_DIR, "Tokens")
PALDEF_TOKEN_FILE = os.path.join(PALDEF_TOKEN_DIR, "serverpal_manager.json")

# ── Runtime log/data paths (đặt trong Pal/Saved/SaveGames) ────────────
ANTIBUG_LOG_FILE  = os.path.join(SAVE_GAMES_DIR, "antibug_log.txt")
ANTIBUG_BAN_FILE  = os.path.join(SAVE_GAMES_DIR, "banlist.txt")
ANTIBUG_WEBHOOK_URL = _cfg("ANTIBUG_WEBHOOK_URL",
    ""
)
ANTIBUG_MAX_KICKS   = int(_cfg("ANTIBUG_MAX_KICKS",   3))
ANTIBUG_KICK_WINDOW = int(_cfg("ANTIBUG_KICK_WINDOW", 300))

# ─────────────────────────────────────────────
#  DISCORD CHAT BRIDGE (2 chiều: ingame ↔ Discord)
# ─────────────────────────────────────────────
DISCORD_CHAT_WEBHOOK    = _cfg("DISCORD_CHAT_WEBHOOK",
    ""
)
DISCORD_BOT_TOKEN       = _cfg("DISCORD_BOT_TOKEN",
    ""
)
DISCORD_CHAT_CHANNEL_ID = _cfg("DISCORD_CHAT_CHANNEL_ID", "1470301251735392309")

# ── Discord Bot 2 (Bot thứ 2 – Cờ Hó) ──────────────────────────────────────
DISCORD_BOT2_TOKEN       = _cfg("DISCORD_BOT2_TOKEN",
    ""
)
DISCORD_BOT2_CHANNEL_ID  = _cfg("DISCORD_BOT2_CHANNEL_ID", "1466418084352102432")
DISCORD_BOT2_RANKING_CHANNEL_ID = _cfg("DISCORD_BOT2_RANKING_CHANNEL_ID", "1484165199266054277")
DISCORD_BOT2_NAME        = _cfg("DISCORD_BOT2_NAME", "Cờ Hó")
DISCORD_BOT2_LIVEMAP_CHANNEL_ID = _cfg("DISCORD_BOT2_LIVEMAP_CHANNEL_ID", "")

# ── Ranking Webhook (kênh Bảng Xếp Hạng riêng) ───────────────────────────
RANKING_WEBHOOK_URL = _cfg("RANKING_WEBHOOK_URL",
    ""
)
PLAYER_CONNECT_WEBHOOK_URL = _cfg(
    "PLAYER_CONNECT_WEBHOOK_URL",
    "",
)

# ─────────────────────────────────────────────
#  PALDEFENDER REST API
# ─────────────────────────────────────────────
# PALDEF_REST_DIR được derive từ SERVER_EXE ở khối _derive_paths bên dưới
# PALDEF_TOKEN_DIR/FILE được gán lại sau _derive_paths
PALDEF_API_BASE    = _cfg("PALDEF_API_BASE", "http://127.0.0.1:17993")
_ANTIBUG_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[(?:info|warning)\] '(.+?)' "
    r"\(UserId=(steam_\d+),.+?\) "
    r"(has build a|dismantled) '(.+?)'"
)

# Base (PalBoxV2) placement/removal log — dùng để cập nhật base tọa độ theo thời gian thực
# Ví dụ:
# [15:29:39][info] 'MityTin' (UserId=steam_..., IP=...) has build a 'PalBoxV2' at 198 -477 919.
# [15:29:34][info] 'MityTin' (...) dismantled 'PalBoxV2' at 198 -477 926 (BuildPlayerUId: ...).
_PALBOXV2_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[(?:info|warning)\] '(.+?)' "
    r"\(UserId=(steam_\d+),.+?\) "
    r"(has build a|dismantled) 'PalBoxV2' at (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)"
)

# ── Technology Level Database ─────────────────────────────────────────────────
# Dữ liệu được chuyển sang file _datadb/tech_level_db.py để dễ quản lý.
from tech_level_db import TECH_LEVEL_DB # type: ignore

# ── Regex 1: Người chơi tự học công nghệ (natural unlock) ────────────────────
# Ví dụ: [17:22:56][info] 'MityTin' (UserId=steam_...) unlocking Technology: 'RepairBench'
_TECH_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] '(.+?)' \(UserId=(steam_\d+)[^)]*\) "
    r"unlocking Technology: '(.+?)'",
    re.IGNORECASE
)

# ── Regex 2: Admin dùng /learntech để cheat (forced unlock) ──────────────────
# Ví dụ: [18:09:26][info] Replying to 'MityTin' (UserId=steam_..., IP=...): "Successfully unlocked technology 'PalFoodBox' for steam_...!"
_TECH_LEARNTECH_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] Replying to '(.+?)' \(UserId=(steam_\d+)[^)]*\): "
    r'"Successfully unlocked technology \'(.+?)\' for',
    re.IGNORECASE
)

# ── Regex theo dõi admin mode (bỏ qua tech-check cho server admin) ────────────
_ADMIN_ON_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] '(.+?)' \(UserId=(steam_\d+),.+?\) "
    r"turned on admin mode",
    re.IGNORECASE
)
_ADMIN_OFF_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] '(.+?)' \(UserId=(steam_\d+),.+?\) "
    r"turned off admin mode",
    re.IGNORECASE
)

# ── Regex chat in-game: PalDefender log format (format thực tế) ──────────────
# Ví dụ: [21:01:27][info] [Chat::Global]['MityTin' (UserId=steam_76561199059671788, IP=192.168.1.1)]: hello
_CHAT_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] \[Chat::([^\]]+)\]\['(.+?)' \(UserId=(steam_\d+)[^)]*\)\]:\s*(.+)",
    re.IGNORECASE
)
# Fallback: PalServer.log chat format (nếu PalDefender không ghi)
# Ví dụ: [2024.01.01-12.00.00:000][  0]LogPalServer: [SteamID] [PlayerName] said: "msg"
_SERVERLOG_CHAT_RE = re.compile(
    r"LogPalServer.*?'(.+?)'\s+(?:said|chat(?:ted)?)[:\s]+\"?(.+?)\"?\s*$",
    re.IGNORECASE
)

# ── Pal Capture Tracking ─────────────────────────────────────────────────
# Format: [HH:MM:SS][info] 'PlayerName' (UserId=steam_XXXX, IP=...) has captured Pal 'PalName' (PalID) at X Y Z.
_PAL_CAPTURE_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] '(.+?)' \(UserId=(steam_\d+)[^)]*\) has captured Pal '(.+?)' \(([^)]+)\)"
    r"(?:\s+at\s+([-\d.]+\s+[-\d.]+\s+[-\d.]+))?",
    re.IGNORECASE
)

# ── NPC Attack Tracking ───────────────────────────────────────────────────
# Format: [HH:MM:SS][info] 'PlayerName' (UserId=steam_XXXX, IP=...) was attacked by a wild 'NPC' (NpcID) at X Y Z.
_NPC_ATTACK_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] '(.+?)' \(UserId=(steam_\d+)[^)]*\) was attacked by a wild '(.+?)' \(([^)]+)\)"
    r"(?:\s+at\s+([-\d.]+\s+[-\d.]+\s+[-\d.]+))?",
    re.IGNORECASE
)

# ── Danh sách NPC ID bị cấm bắt (auto-ban ngay lập tức) ─────────────────
# PalID xuất hiện trong log: has captured Pal 'Tên' (PalID)
NPC_BAN_IDS: set = {
    "SalesPerson",          # Wandering Merchant (Thương nhân lang thang)
    "SalesPerson_Desert",   # Desert Merchant
    "SalesPerson_Forest",   # Forest Merchant
    "SalesPerson_Night",    # Night Merchant
    "BlackMarketTrader",    # Black Marketeer (Chợ đen)
    "SalesPerson_Wander",   # Wander Merchant variant
    "PalDealer",            # Pal Dealer / Pal Trader
    "TerrorMail",           # PIDF NPC
    "Trader",               # Generic trader NPC
    "SalesPerson_Boss",     # Boss merchant variant
}

MAP_ASSETS_DIR  = os.path.join(_MANAGER_DIR, "_map_assets")
MAP_JPG         = os.path.join(MAP_ASSETS_DIR, "map.jpg")
MAP_SERVER_PORT = 3333

# ─────────────────────────────────────────────
#  TỰ TẠO THƯ MỤC RUNTIME KHI KHỞI ĐỘNG
# ─────────────────────────────────────────────
def _ensure_runtime_dirs() -> None:
    """Tạo tất cả thư mục cần ghi trước khi app chạy.
    Gọi sau khi tất cả path đã được derive xong."""
    dirs = [
        SAVE_GAMES_DIR,                         # antibug_log.txt, banlist.txt, stats, bot2 ids
        GIFT_SAVE_DIR,                          # newbie_gift_received.txt, log
        PALDEF_TOKEN_DIR,                       # serverpal_manager.json
        MAP_ASSETS_DIR,                         # map.jpg (local asset)
    ]
    for d in dirs:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            pass  # Ổ đĩa chưa mount hoặc không có quyền — bỏ qua

_ensure_runtime_dirs()


# ─────────────────────────────────────────────
#  SOURCE RCON (Palworld dùng giao thức này)
# ─────────────────────────────────────────────
def rcon_exec(command: str) -> str:
    """Kết nối RCON, xác thực và thực thi lệnh. Trả về response string."""
    def _refresh_rcon_runtime():
        """Đồng bộ runtime RCON từ manager_config ngay trước khi gửi lệnh."""
        global RCON_HOST, RCON_PORT, RCON_PASSWORD, AUTH
        try:
            cfg = _read_manager_cfg()
            if not isinstance(cfg, dict) or not cfg:
                return
            # Ưu tiên mật khẩu admin dùng chung để tránh lệch với AppConfig mới lưu.
            shared_pass = _resolve_shared_admin_password(cfg)
            if shared_pass:
                RCON_PASSWORD = shared_pass
                AUTH = HTTPBasicAuth("admin", shared_pass)
            host = cfg.get("RCON_HOST")
            if isinstance(host, str) and host.strip():
                RCON_HOST = host.strip()
            port = str(cfg.get("RCON_PORT", "")).strip()
            if port.isdigit():
                RCON_PORT = int(port)
        except Exception:
            pass

    try:
        _refresh_rcon_runtime()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(6)
        s.connect((RCON_HOST, RCON_PORT))

        def _pack(req_id: int, cmd_type: int, body: str) -> bytes:
            enc = body.encode("utf-8") + b"\x00\x00"
            size = 4 + 4 + len(enc)
            return struct.pack("<III", size, req_id, cmd_type) + enc

        def _recv() -> tuple:
            data = b""
            while len(data) < 4:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            if len(data) < 4:
                return 0, 0, ""
            size = struct.unpack("<I", data[:4])[0]
            while len(data) < size + 4:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
            rid = struct.unpack("<I", data[4:8])[0]
            body = data[12: 4 + size - 2].decode("utf-8", errors="replace")
            return rid, 0, body

        # Authenticate
        s.sendall(_pack(1, 3, RCON_PASSWORD))
        _recv()
        # Execute command
        s.sendall(_pack(2, 2, command))
        _, _, body = _recv()
        s.close()
        return body.strip()
    except Exception as e:
        return f"RCON Error: {e}"


# ─────────────────────────────────────────────
#  DYNAMIC CONFIG (đọc từ manager_config.json)
# ─────────────────────────────────────────────
def _apply_manager_config(cfg: dict) -> None:
    """Áp dụng dict config vào các biến toàn cục — có hiệu lực ngay, không cần restart."""
    global API_URL, AUTH, RCON_HOST, RCON_PORT, RCON_PASSWORD
    global SERVER_EXE, DISCORD_WEBHOOK_URL, ANTIBUG_WEBHOOK_URL
    global ANTIBUG_MAX_KICKS, ANTIBUG_KICK_WINDOW
    global PALDEF_API_BASE
    global PAL_SETTINGS_INI, SERVER_LOG_FILE, PALDEF_LOG_DIR, PALDEF_CHEATS_DIR
    global PALDEF_REST_DIR, GIFT_SAVE_DIR, PALDEF_TOKEN_DIR, PALDEF_TOKEN_FILE
    global DISCORD_CHAT_WEBHOOK, DISCORD_BOT_TOKEN, DISCORD_CHAT_CHANNEL_ID
    global DISCORD_BOT2_TOKEN, DISCORD_BOT2_CHANNEL_ID, DISCORD_BOT2_RANKING_CHANNEL_ID, DISCORD_BOT2_NAME
    global DISCORD_BOT2_LIVEMAP_CHANNEL_ID
    global RANKING_WEBHOOK_URL, PLAYER_CONNECT_WEBHOOK_URL
    global STARTUP_HEALTH_CHECK_ENABLED
    global STARTUP_LOG_READY_CHECK_ENABLED

    def _s(key):
        v = cfg.get(key, "")
        return v.strip() if isinstance(v, str) else v

    if _s("API_URL"):
        API_URL = _s("API_URL")

    shared_pass = _resolve_shared_admin_password(cfg)
    if shared_pass:
        AUTH = HTTPBasicAuth("admin", shared_pass)
        RCON_PASSWORD = shared_pass

    if _s("RCON_HOST"):
        RCON_HOST = _s("RCON_HOST")

    if _s("RCON_PORT"):
        try:
            RCON_PORT = int(_s("RCON_PORT"))
        except (ValueError, TypeError):
            pass

    # Toggle bật/tắt health-check sau khởi động
    try:
        if "STARTUP_HEALTH_CHECK_ENABLED" in cfg:
            val = cfg.get("STARTUP_HEALTH_CHECK_ENABLED")
            STARTUP_HEALTH_CHECK_ENABLED = bool(val) if isinstance(val, bool) else str(val).strip().lower() in {"1","true","yes","on"}
    except Exception:
        pass
    try:
        if "STARTUP_LOG_READY_CHECK_ENABLED" in cfg:
            val = cfg.get("STARTUP_LOG_READY_CHECK_ENABLED")
            STARTUP_LOG_READY_CHECK_ENABLED = bool(val) if isinstance(val, bool) else str(val).strip().lower() in {"1","true","yes","on"}
    except Exception:
        pass

    if _s("SERVER_EXE"):
        SERVER_EXE = _resolve_server_exe_from_cfg(_s("SERVER_EXE"), SERVER_EXE)
        # Re-derive toàn bộ path từ SERVER_EXE mới
        (PAL_SETTINGS_INI,
         SERVER_LOG_FILE,
         PALDEF_LOG_DIR,
         PALDEF_CHEATS_DIR,
         PALDEF_REST_DIR,
         GIFT_SAVE_DIR)    = _derive_paths(SERVER_EXE)
        PALDEF_TOKEN_DIR   = os.path.join(PALDEF_REST_DIR, "Tokens")
        PALDEF_TOKEN_FILE  = os.path.join(PALDEF_TOKEN_DIR, "serverpal_manager.json")
        _ensure_runtime_dirs()   # Tạo lại thư mục nếu root mới

    if _s("DISCORD_WEBHOOK_URL"):
        DISCORD_WEBHOOK_URL = _s("DISCORD_WEBHOOK_URL")

    if _s("ANTIBUG_WEBHOOK_URL"):
        ANTIBUG_WEBHOOK_URL = _s("ANTIBUG_WEBHOOK_URL")

    if _s("ANTIBUG_MAX_KICKS"):
        try:
            ANTIBUG_MAX_KICKS = int(_s("ANTIBUG_MAX_KICKS"))
        except (ValueError, TypeError):
            pass

    if _s("ANTIBUG_KICK_WINDOW"):
        try:
            ANTIBUG_KICK_WINDOW = int(_s("ANTIBUG_KICK_WINDOW"))
        except (ValueError, TypeError):
            pass

    if _s("PALDEF_API_BASE"):
        PALDEF_API_BASE = _s("PALDEF_API_BASE")

    if _s("DISCORD_CHAT_WEBHOOK"):
        DISCORD_CHAT_WEBHOOK = _s("DISCORD_CHAT_WEBHOOK")

    if _s("DISCORD_BOT_TOKEN"):
        DISCORD_BOT_TOKEN = _s("DISCORD_BOT_TOKEN")

    if _s("DISCORD_CHAT_CHANNEL_ID"):
        DISCORD_CHAT_CHANNEL_ID = _s("DISCORD_CHAT_CHANNEL_ID")

    if _s("DISCORD_BOT2_TOKEN"):
        DISCORD_BOT2_TOKEN = _s("DISCORD_BOT2_TOKEN")

    if _s("DISCORD_BOT2_CHANNEL_ID"):
        DISCORD_BOT2_CHANNEL_ID = _s("DISCORD_BOT2_CHANNEL_ID")

    if _s("DISCORD_BOT2_RANKING_CHANNEL_ID"):
        DISCORD_BOT2_RANKING_CHANNEL_ID = _s("DISCORD_BOT2_RANKING_CHANNEL_ID")

    if _s("DISCORD_BOT2_NAME"):
        DISCORD_BOT2_NAME = _s("DISCORD_BOT2_NAME")

    if _s("DISCORD_BOT2_LIVEMAP_CHANNEL_ID"):
        DISCORD_BOT2_LIVEMAP_CHANNEL_ID = _s("DISCORD_BOT2_LIVEMAP_CHANNEL_ID")

    if _s("RANKING_WEBHOOK_URL"):
        RANKING_WEBHOOK_URL = _s("RANKING_WEBHOOK_URL")
    if _s("PLAYER_CONNECT_WEBHOOK_URL"):
        PLAYER_CONNECT_WEBHOOK_URL = _s("PLAYER_CONNECT_WEBHOOK_URL")


# ─────────────────────────────────────────────
#  PALWORLD ITEMS DATABASE  (Give Item dialog)
#  (category, display_name, blueprint_id, emoji)
# ─────────────────────────────────────────────
from pw_items_db import PW_ITEMS as _PW_ITEMS # type: ignore

# ─────────────────────────────────────────────
#  PALWORLD PALS DATABASE  (Give Pal dialog)
#  Source: paldeck.cc/pals
#  (dex, display_name, pal_id, element, emoji)
# ─────────────────────────────────────────────
from pw_pals_db import PW_PALS as _PW_PALS # type: ignore

# ─────────────────────────────────────────────
#  IV CALCULATOR DATA  (Source: paldb.cc/en/Iv_Calc)
#  Keyed by Pal Blueprint Code (same as _PW_PALS pal_id)
#  Fields: id, name, Hp, ShotAttack, Defense
# ─────────────────────────────────────────────
from iv_pal_data_db import IV_PAL_DATA as _IV_PAL_DATA # type: ignore

# ─────────────────────────────────────────────
#  IV PASSIVE SKILLS DATA  (Source: paldb.cc/en/Iv_Calc)
#  Keyed by passive skill ID.
#  ShotAttack, Defense, CraftSpeed bonuses in % (integer)
# ─────────────────────────────────────────────
from iv_passive_data_db import IV_PASSIVE_DATA as _IV_PASSIVE_DATA # type: ignore

# ─────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────
class ManagerServerPalApp:

    # ── Khởi tạo ──────────────────────────────
    def __init__(self, root):
        self.root = root
        self.root.title("Manager ServerPal v1.0.1 by MityTinDev")
        self.root.geometry("1400x900")
        self.root.configure(bg="#0a0a0a")
        self._icon_img = None
        try:
            if os.path.isfile(UI_ICON_PNG):
                self._icon_img = tk.PhotoImage(file=UI_ICON_PNG)
                self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass

        self.auto_mode           = tk.BooleanVar(value=True)
        self.is_processing       = False
        self.last_reset_minute   = ""
        self._max_players        = self._read_max_players()
        self.player_count_str    = f"0/{self._max_players}"
        self.overview_widgets    = {}

        # Giữ buffer log hệ thống trong bộ nhớ để khi chuyển tab không mất log
        # Lưu dưới dạng (line, tag) với tag trong {"system", "warn", "error"}
        from collections import deque as _deque  # local import to avoid polluting top
        self._console_buffer: _deque = _deque(maxlen=5000)
        self.is_notified_online  = False

        # Thread-safe console queue
        self._console_queue: queue.Queue = queue.Queue()

        # Server log tail
        self._server_log_queue: queue.Queue = queue.Queue()
        self._server_log_pos: int = 0
        try:
            if os.path.isfile(SERVER_LOG_FILE):
                self._server_log_pos = os.path.getsize(SERVER_LOG_FILE)
        except Exception:
            pass

        # PalDefender log tail
        self._paldef_log_queue:   queue.Queue = queue.Queue()
        self._paldef_cheat_queue: queue.Queue = queue.Queue()
        self._paldef_log_file:    str = ""
        self._paldef_log_pos:     int = 0
        self._paldef_cheat_file:  str = ""
        self._paldef_cheat_pos:   int = 0
        self.paldef_discord_alert      = tk.BooleanVar(value=True)
        self.paldef_discord_alert_main = tk.BooleanVar(value=False)  # Alert thêm vào main webhook
        self.paldef_log_cleanup_enabled = tk.BooleanVar(value=_cfg_bool("UI_PALDEF_LOG_CLEANUP_ENABLED", True))
        _keep_hours_raw = str(_cfg("UI_PALDEF_LOG_KEEP_HOURS", "24"))
        self.paldef_log_keep_hours = tk.StringVar(value=_keep_hours_raw if _keep_hours_raw in {"24", "12", "6", "4", "2"} else "24")
        self._cheat_dedupe_last_line = ""
        self._cheat_dedupe_count = 0
        self._cheat_alert_last: dict = {}
        # Khởi tạo vị trí đọc từ cuối file hiện tại (chỉ nhận sự kiện mới)
        try:
            _lf = max(
                (os.path.join(PALDEF_LOG_DIR, f) for f in os.listdir(PALDEF_LOG_DIR)
                 if f.endswith(".log") and
                 os.path.isfile(os.path.join(PALDEF_LOG_DIR, f))),
                key=os.path.getmtime, default=""
            )
            if _lf:
                self._paldef_log_file = _lf
                self._paldef_log_pos  = os.path.getsize(_lf)
        except Exception:
            pass
        try:
            _cf = max(
                (os.path.join(PALDEF_CHEATS_DIR, f) for f in os.listdir(PALDEF_CHEATS_DIR)
                 if f.endswith("-cheats.log") and
                 os.path.isfile(os.path.join(PALDEF_CHEATS_DIR, f))),
                key=os.path.getmtime, default=""
            )
            if _cf:
                self._paldef_cheat_file = _cf
                self._paldef_cheat_pos  = os.path.getsize(_cf)
        except Exception:
            pass

        # Watchdog
        self.WATCHDOG_CHECK_INTERVAL_SEC   = 10
        self.WATCHDOG_RESTART_COOLDOWN_SEC = 60
        self._watchdog_last_restart_at     = 0.0
        self._server_op_lock               = threading.Lock()
        self._startup_check_seq            = 0
        self._startup_check_lock           = threading.Lock()
        self.STARTUP_HEALTH_RETRY_MAX      = 2  # Retry thêm 2 lần => tối đa 3 lượt khởi động
        self._startup_log_check_seq        = 0
        self._startup_log_check_lock       = threading.Lock()

        # Player caches
        self._steamid_to_name:     dict = {}
        self._steamid_to_playerid: dict = {}   # {steamid: playerId hex UUID}
        self._pending_no_steamid:  dict = {}   # {playerId: {"name": str, "since": float}}
        self._online_players_prev: set = set()  # steamids online ở lần poll trước

        # ── AntiBug System ─────────────────────
        self.antibug_enabled           = tk.BooleanVar(value=_cfg_bool("UI_ANTIBUG_ENABLED", True))
        self.antibug_max_per_sec       = tk.IntVar(value=_cfg_int("UI_ANTIBUG_MAX_PER_SEC", 2))
        self.antibug_discord_alert     = tk.BooleanVar(value=_cfg_bool("UI_ANTIBUG_DISCORD_ALERT", True))
        self.antibug_buildcheck_enabled = tk.BooleanVar(value=_cfg_bool("UI_ANTIBUG_BUILDCHECK_ENABLED", True))
        self.antibug_techcheck_enabled = tk.BooleanVar(value=_cfg_bool("UI_ANTIBUG_TECHCHECK_ENABLED", True))
        self.techcheck_ban_admin       = tk.BooleanVar(value=_cfg_bool("UI_TECHCHECK_BAN_ADMIN", False))  # ban cả admin
        self.npc_capture_ban_enabled   = tk.BooleanVar(value=_cfg_bool("UI_NPC_CAPTURE_BAN_ENABLED", True))   # ban khi bắt NPC
        self.npc_attack_kick_enabled   = tk.BooleanVar(value=_cfg_bool("UI_NPC_ATTACK_KICK_ENABLED", True))   # kick khi tấn công NPC
        self._npc_attack_events:   dict         = {}   # {steamid: {"last_kick": float, "count": int}}
        self._antibug_events:      dict         = {}   # {steamid: {...}}
        self._antibug_kick_total:  int          = 0
        self._antibug_ban_total:   int          = 0
        self._antibug_log_queue:   queue.Queue  = queue.Queue()
        self._player_level_cache:  dict         = {}   # {steamid: level}
        self._admin_mode_players:  set          = set() # steamids đang ở admin mode

        # ── PalDefender REST API ───────────────
        self._pdapi_token      = self._pdapi_ensure_token()
        self._pdapi_status_ok  = False
        self._pdapi_version    = ""

        # ── Discord Chat Bridge ────────────────
        self._discord_bridge_status: str   = "⏳ Chưa khởi động"
        self._discord_bridge_ok:    bool   = False
        self._discord_msg_in:       int    = 0   # Discord → ingame
        self._discord_msg_out:      int    = 0   # ingame → Discord
        self._discord_last_check:   float  = 0.0
        self._discord_log_queue:    queue.Queue = queue.Queue()

        # ── Discord Bot 2 ────────────────────────
        self._discord_bot2_status: str   = "⏳ Chưa khởi động"
        self._discord_bot2_ok:    bool   = False
        self._discord_bot2_client: object = None
        self._discord_bot2_loop: object = None
        # Auto-update message IDs (lưu để edit thay vì gửi mới)
        self._bot2_status_msg_id:  int = 0
        self._bot2_ranking_msg_id: int = 0
        self._bot2_livemap_msg_id: int = 0
        # File lưu message IDs để dùng lại sau khi restart
        self._bot2_msg_file = os.path.join(SAVE_GAMES_DIR, "bot2_msg_ids.json")
        self._load_bot2_msg_ids()   # Load ngay khi khởi động

        # ── LiveMap ────────────────────────────
        self._map_node_proc:    object = None
        self._map_players_data: list   = []
        self._map_canvas_photo: object = None   # PIL PhotoImage (anti-GC)
        self._map_guilds_data:  dict   = {}     # {guild_id: {name, members, ...}}
        self._map_guild_player_map: dict = {}   # {playerid/steamid → guild_name}
        self._map_show_guilds   = tk.BooleanVar(value=True)  # Toggle guild layer
        # Guild bases — [{guild_name, base_id, loc_x, loc_y, color}]
        self._map_guild_bases:  list   = []
        self._map_show_bases    = tk.BooleanVar(value=True)  # Toggle base layer
        # Base cache từ log PalBoxV2 (ưu tiên hơn PD API nếu có)
        self._map_bases_by_guild: dict = {}   # {guild_name: base_dict}

        # ── Newbie Gift System ─────────────────
        self.newbie_gift_auto      = tk.BooleanVar(value=True)
        self.newbie_gift_wait_sec  = 60
        self.newbie_gift_received: set  = set()
        self.newbie_gift_pending:  dict = {}   # {steamid: login_time}
        self.daily_checkin_reward_items = [
            {"ItemID": "Money", "Count": 10000},
            {"ItemID": "DogCoin", "Count": 20},
            {"ItemID": "PalSummon_NightLady_Parts", "Count": 2},
            {"ItemID": "Blueprint_YakushimaLantern001", "Count": 1},
            {"ItemID": "FishingBait_3_A", "Count": 10},
            {"ItemID": "PalSphere_Exotic", "Count": 1},
        ]
        self.online60_reward_items = [
            {"ItemID": "Money", "Count": 15000},
            {"ItemID": "DogCoin", "Count": 10},
        ]
        self.online60_reward_seconds = 3600
        # Quỹ thưởng TOP10/ngày: sẽ chia cho 10 suất (random phần dư, nền tảng vẫn đều).
        self.top10_bonus_pool_items = [
            {"ItemID": "Money", "Count": 1000000},  # tương đương 100k/người nếu đủ 10 online
            {"ItemID": "DogCoin", "Count": 1000},   # tương đương 100/người
        ]

        # Đường dẫn file — thư mục quatanthu đã được tạo ở trên
        self.newbie_gift_file     = os.path.join(GIFT_SAVE_DIR, "newbie_gift_received.txt")
        self.newbie_gift_log_file = os.path.join(GIFT_SAVE_DIR, "newbie_gift_log.txt")
        self.daily_gift_log_file  = os.path.join(GIFT_SAVE_DIR, "daily_gift_log.txt")
        self.online_gift_log_file = os.path.join(GIFT_SAVE_DIR, "online_gift_log.txt")
        self.ranking_bonus_log_file = os.path.join(GIFT_SAVE_DIR, "ranking_bonus_log.txt")
        self.ranking_bonus_claim_file = os.path.join(GIFT_SAVE_DIR, "ranking_bonus_claims.json")
        self.ranking_bonus_state_file = os.path.join(GIFT_SAVE_DIR, "ranking_bonus_daily_state.json")
        self.daily_checkin_file   = os.path.join(GIFT_SAVE_DIR, "daily_checkin_claims.json")
        self.online60_file        = os.path.join(GIFT_SAVE_DIR, "online60_reward_state.json")
        self._load_newbie_gift_tracking()
        self.daily_checkin_claims: dict = {}   # {yyyy-mm-dd: [steamid,...]}
        self.online60_reward_state: dict = {}  # {steamid: {"accum_sec": float, "last_seen": float}}
        self.newbie_gift_template = [
            {"Type": "pal", "ID": "FengyunDeeper_Electric", "Count": 1},
            {"Type": "item", "ID": "SkillUnlock_FengyunDeeper_Electric", "Count": 1},
            {"Type": "item", "ID": "Accessory_HeatColdResist_3", "Count": 1},
            {"Type": "item", "ID": "Spear_ForestBoss_5", "Count": 1},
            {"Type": "item", "ID": "PalSphere", "Count": 10},
        ]
        self._load_daily_checkin_tracking()
        self._load_online60_tracking()
        self._load_reward_templates_from_cfg()
        self.ranking_bonus_claims: dict = {}  # {yyyy-mm-dd: [steamid, ...]}
        self._load_ranking_bonus_claims()
        self.ranking_bonus_daily_state: dict = {}  # {yyyy-mm-dd: {"top20":[sid], "slots":[{"steamid":sid,"bonus":{...}}]}}
        self._load_ranking_bonus_daily_state()
        # Retry states for daily/online gifts (RCON-first style)
        self._daily_retry_state: dict = {}   # {steamid: {"attempts": int, "next_ts": float}}
        self._online_retry_state: dict = {}  # {steamid: {"attempts": int, "next_ts": float}}

        # ── Player Ranking System ─────────────────
        self.player_stats_file = os.path.join(SAVE_GAMES_DIR, "player_stats.json")
        self.player_time_log_file = os.path.join(SAVE_GAMES_DIR, "player_time_audit.log")
        self.player_stats: dict = {}  # {steamid: {"name": str, "level": int, "pal_count": int, "last_update": float}}
        self._player_stats_last_save_ts: float = 0.0
        self.ranking_enabled = tk.BooleanVar(value=True)
        self.ranking_update_interval = 300  # 5 phút
        self.ranking_last_update = 0.0
        self._load_player_stats()

        # Auto-save trạng thái menu bật/tắt để lần mở sau giữ nguyên.
        self._menu_pref_after_id = None
        self._bind_menu_pref_autosave()

        self.setup_styles()
        self.create_sidebar()
        self.create_main_container()
        self.start_threads()
        self._poll_console_queue()
        self._poll_server_log_queue()
        self._poll_paldef_log_queue()
        self._poll_paldef_cheat_queue()
        self._poll_antibug_log_queue()

        # ── RAM Optimizer config ─────────────────
        self._ram_auto_opt_var    = tk.BooleanVar(value=True)
        self._ram_opt_threshold   = tk.IntVar(value=80)   # % RAM hệ thống
        self._ram_opt_interval_ms = 60_000               # 60s kiểm tra 1 lần
        self.root.after(2000, self._ram_monitor_loop)

        # Tự làm mới trạng thái ONLINE/OFFLINE định kỳ (không cần bấm "Làm mới").
        self._status_refresh_interval_ms = 5000
        self.root.after(1500, self._auto_refresh_server_status_loop)

    # ── Styles ────────────────────────────────
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#111", foreground="white",
                        fieldbackground="#111", borderwidth=0, rowheight=32)
        style.configure("Treeview.Heading", background="#222", foreground="#00ffcc",
                        font=("Segoe UI", 10, "bold"))

    # ── Sidebar ───────────────────────────────
    def create_sidebar(self):
        sidebar = tk.Frame(self.root, bg="#111", width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="MANAGER SERVERPAL", font=("Segoe UI", 18, "bold"),
                 bg="#111", fg="#00ffcc", pady=24).pack()

        tabs = [
            ("📊 TỔNG QUAN",    "Overview"),
            ("🖥️ ĐIỀU KHIỂN",  "Dash"),
            ("👥 NGƯỜI CHƠI",  "Players"),
            ("🎁 QUÀ TẶNG",    "NewbieGift"),
            ("🛡️ PALDEFENDER", "PalDefender"),
            ("🗺️ LIVE MAP",    "LiveMap"),
            ("🟣 DISCORD CHAT", "Discord"),
            ("⚙️ CÀI ĐẶT",     "Settings"),
        ]
        for text, tag in tabs:
            tk.Button(sidebar, text=text, font=("Segoe UI", 11), bg="#111", fg="#ccc",
                      relief="flat", anchor="w", padx=28, pady=13,
                      command=lambda t=tag: self.switch_tab(t)).pack(fill="x")

        tk.Label(sidebar, text="TỰ ĐỘNG HÓA", font=("Segoe UI", 8, "bold"),
                 bg="#111", fg="#555", pady=16).pack()
        tk.Checkbutton(sidebar, text="CHẾ ĐỘ AUTO", variable=self.auto_mode,
                       bg="#111", fg="#00ffcc", selectcolor="#111",
                       font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=28)

        self.lbl_status = tk.Label(sidebar, text="● SERVER ONLINE",
                                   bg="#111", fg="#00ffcc",
                                   font=("Segoe UI", 9, "bold"), pady=24)
        self.lbl_status.pack(side="bottom")

    def create_main_container(self):
        self.container = tk.Frame(self.root, bg="#0a0a0a")
        self.container.pack(side="right", fill="both", expand=True, padx=22, pady=22)
        self.switch_tab("Overview")

    def switch_tab(self, tag):
        self.overview_widgets = {}
        for w in self.container.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        mapping = {
            "Overview":    self.draw_overview,
            "Dash":        self.draw_dashboard,
            "Players":     self.draw_players,
            "NewbieGift":  self.draw_newbie_gift,
            "PalDefender": self.draw_paldefender,
            "LiveMap":     self.draw_livemap,
            "Discord":     self.draw_discord,
            "Settings":    self.draw_settings,
        }
        if tag in mapping:
            mapping[tag]()

    # ── Console helpers ───────────────────────
    def _enqueue_console(self, text: str):
        """Thread-safe: đưa text vào queue để main thread hiển thị."""
        self._console_queue.put(text)

    def _poll_console_queue(self):
        """Chạy mỗi 150ms trên main thread để flush queue ra console."""
        try:
            while True:
                msg = self._console_queue.get_nowait()
                self._write_console_direct(msg)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_console_queue)

    def _poll_server_log_queue(self):
        """Chạy mỗi 200ms trên main thread để flush server log queue ra server_console."""
        try:
            count = 0
            while count < 80:   # tối đa 80 dòng mỗi vòng để không đóng băng UI
                line = self._server_log_queue.get_nowait()
                if hasattr(self, "server_console") and self.server_console.winfo_exists():
                    # Áp dụng filter nếu có
                    flt_var = getattr(self, "_srv_filter_var", None)
                    flt = flt_var.get().strip().lower() if flt_var else ""
                    if flt and flt not in line.lower():
                        count += 1
                        continue
                    self.server_console.insert(tk.END, line + "\n")
                    asc = getattr(self, "_srv_autoscroll_var", None)
                    if asc is None or asc.get():
                        self.server_console.see(tk.END)
                count += 1
        except queue.Empty:
            pass
        self.root.after(200, self._poll_server_log_queue)

    def _poll_paldef_log_queue(self):
        """Flush PalDefender main log queue → paldef_console (main thread)."""
        try:
            count = 0
            while count < 80:
                line = self._paldef_log_queue.get_nowait()
                if hasattr(self, "paldef_console") and self.paldef_console.winfo_exists():
                    flt_var = getattr(self, "_paldef_filter_var", None)
                    flt = flt_var.get().strip().lower() if flt_var else ""
                    if flt and flt not in line.lower():
                        count += 1
                        continue
                    self.paldef_console.insert(tk.END, line + "\n")
                    asc = getattr(self, "_paldef_autoscroll_var", None)
                    if asc is None or asc.get():
                        self.paldef_console.see(tk.END)
                count += 1
        except queue.Empty:
            pass
        self.root.after(200, self._poll_paldef_log_queue)

    def _poll_paldef_cheat_queue(self):
        """Flush PalDefender cheat queue → paldef_cheat_console (main thread)."""
        try:
            count = 0
            while count < 50:
                line = self._paldef_cheat_queue.get_nowait()
                if hasattr(self, "paldef_cheat_console") and \
                   self.paldef_cheat_console.winfo_exists():
                    self.paldef_cheat_console.insert(tk.END, line + "\n")
                    self.paldef_cheat_console.see(tk.END)
                count += 1
        except queue.Empty:
            pass
        self.root.after(300, self._poll_paldef_cheat_queue)

    def _poll_antibug_log_queue(self):
        """Flush AntiBug log queue → antibug_console (main thread)."""
        try:
            count = 0
            while count < 50:
                msg = self._antibug_log_queue.get_nowait()
                if hasattr(self, "antibug_console") and \
                   self.antibug_console.winfo_exists():
                    self.antibug_console.insert(tk.END, msg + "\n")
                    self.antibug_console.see(tk.END)
                count += 1
        except queue.Empty:
            pass
        self.root.after(200, self._poll_antibug_log_queue)

    def _write_console_direct(self, text: str):
        """Ghi log ra đúng pane: chat (💬/📢) → chat_console; còn lại → system console."""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        is_chat_in  = text.startswith("💬")
        is_chat_out = text.startswith("📢 ADMIN")

        if is_chat_in or is_chat_out:
            # ── Ghi vào CHAT pane ──────────────────────────────────
            if hasattr(self, "chat_console") and self.chat_console.winfo_exists():
                self.chat_console.configure(state="normal")
                if is_chat_in:
                    # Phân tích: 💬 [HH:MM:SS] [Channel] PlayerName: msg
                    # hoặc:     💬 PlayerName: msg  (fallback)
                    import re as _re
                    m = _re.match(
                        r"💬 \[(\d{2}:\d{2}:\d{2})\] \[([^\]]+)\] (.+?):\s*(.+)", text)
                    if m:
                        ts, ch, plr, msg = m.groups()
                        # Lọc theo kênh
                        flt = getattr(self, "_chat_filter_var", None)
                        if flt and flt.get() not in ("All", ch):
                            self.chat_console.configure(state="disabled")
                            return
                        self.chat_console.insert(tk.END, f"[{ts}] ", "ts")
                        self.chat_console.insert(tk.END, f"[{ch}] ", "channel")
                        self.chat_console.insert(tk.END, f"{plr}: ", "player")
                        self.chat_console.insert(tk.END, f"{msg}\n")
                    else:
                        # fallback không có timestamp/channel
                        self.chat_console.insert(
                            tk.END, f"[{now}] {text[2:].strip()}\n", "player")
                else:
                    # Admin broadcast
                    msg = text.replace("📢 ADMIN → ", "", 1)
                    self.chat_console.insert(tk.END, f"[{now}] ", "ts")
                    self.chat_console.insert(tk.END, f"ADMIN: ", "admin")
                    self.chat_console.insert(tk.END, f"{msg}\n")
                self.chat_console.see(tk.END)
                self.chat_console.configure(state="disabled")
        else:
            # ── Ghi vào SYSTEM LOG pane ────────────────────────────
            tag = "error" if any(x in text for x in ("❌","Lỗi","ERROR")) \
                  else "warn"  if any(x in text for x in ("⚠️","WARNING")) \
                  else "system"
            formatted = f"[{now}] {text}\n"
            # Lưu vào buffer để khi quay lại tab vẫn còn log
            try:
                self._console_buffer.append((formatted, tag))
            except Exception:
                pass
            if hasattr(self, "console") and self.console.winfo_exists():
                self.console.insert(tk.END, formatted, tag)
                self.console.see(tk.END)
            if hasattr(self, "overview_console") and self.overview_console.winfo_exists():
                self.overview_console.insert(tk.END, formatted, tag)
                self.overview_console.see(tk.END)

    def _replay_console_buffer(self, widget):
        """Ghi lại toàn bộ buffer hệ thống vào widget mới tạo (khi đổi tab)."""
        try:
            for line, tag in list(self._console_buffer):
                try:
                    widget.insert(tk.END, line, tag)
                except Exception:
                    widget.insert(tk.END, line)
            widget.see(tk.END)
        except Exception:
            pass

    def write_console(self, text: str):
        """Gọi từ main thread."""
        self._write_console_direct(text)

    # ── Discord / Broadcast ───────────────────
    def send_discord_alert(self, message: str):
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": message}, timeout=5)
        except Exception:
            pass

    def send_ingame_broadcast(self, text: str):
        try:
            requests.post(f"{API_URL}/announce", json={"message": text},
                          auth=AUTH, timeout=3)
        except Exception:
            pass

    # ── Discord Chat Bridge ───────────────────
    def _discord_forward_chat(self, player_name: str, channel: str, message: str):
        """Gửi tin nhắn ingame → Discord webhook (dùng username của người chơi)."""
        if not DISCORD_CHAT_WEBHOOK:
            return
        def _send():
            try:
                from discord_bridge import forward_chat_to_discord
                forward_chat_to_discord(player_name, channel, message, DISCORD_CHAT_WEBHOOK)
                self._discord_msg_out += 1
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self._discord_log_queue.put({
                    "dir": "to_dc", "ts": ts,
                    "who": f"{player_name} [{channel}]", "msg": message})
            except Exception:
                pass
        threading.Thread(target=_send, daemon=True).start()

    def __discord_send_webhook(self, player_name: str, channel: str, message: str):
        # Giữ để tương thích ngược nếu nơi khác còn gọi
        try:
            from discord_bridge import forward_chat_to_discord
            forward_chat_to_discord(player_name, channel, message, DISCORD_CHAT_WEBHOOK)
            self._discord_msg_out += 1
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._discord_log_queue.put({
                "dir": "to_dc", "ts": ts,
                "who": f"{player_name} [{channel}]", "msg": message})
        except Exception:
            pass

    def discord_to_ingame_poll(self):
        """Background thread: chạy Discord bot thật qua Gateway WebSocket.
        Bot sẽ hiển thị ONLINE trên Discord.
        YÊU CẦU: Bật 'Message Content Intent' tại
        https://discord.com/developers/applications → Bot → Privileged Gateway Intents
        """
        import asyncio
        import re as _re
        try:
            import discord as _discord
        except ImportError:
            self._discord_bridge_status = "❌ Thiếu thư viện discord.py — pip install discord.py"
            self._enqueue_console("❌ Discord: pip install discord.py")
            return

        # ── Chờ app khởi động xong ───────────────────────────────
        time.sleep(5)

        if not DISCORD_BOT_TOKEN or not DISCORD_CHAT_CHANNEL_ID:
            self._discord_bridge_status = "⚠️ Chưa cấu hình Bot Token / Channel ID"
            self._enqueue_console("⚠️ Discord Chat Bridge: chưa cấu hình Bot Token / Channel ID")
            return

        def _dc_log(direction: str, who: str, msg: str):
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._discord_log_queue.put({"dir": direction, "ts": ts, "who": who, "msg": msg})

        # ── Tạo client factory (cần client mới mỗi lần reconnect) ─
        def _make_client():
            intents = _discord.Intents.default()
            intents.message_content = True   # Privileged — bật trong Developer Portal
            intents.messages        = True
            c = _discord.Client(intents=intents)

            @c.event
            async def on_ready():
                # Đổi tên bot thành "Mồm Lèo" nếu chưa đúng tên
                desired_name = "Mồm Lèo"
                if c.user.name != desired_name:
                    try:
                        await c.user.edit(username=desired_name)
                        _dc_log("sys", "", f"✅ Đã đổi tên bot → '{desired_name}'")
                    except _discord.errors.HTTPException as _e:
                        # Rate limit đổi tên: 2 lần/giờ — bỏ qua nếu bị giới hạn
                        _dc_log("sys", "", f"⚠️ Chưa đổi được tên: {_e} (giới hạn 2 lần/giờ)")

                self._discord_bridge_ok     = True
                self._discord_bridge_status = f"✅ {c.user.name} — 🟢 Online"
                self._discord_last_check    = time.time()
                self._enqueue_console(
                    f"✅ Discord Bot '{c.user.name}' đã kết nối Gateway — Online!")
                _dc_log("sys", "", f"✅ Bot {c.user.name} Online — Gateway WebSocket kết nối thành công")

            @c.event
            async def on_disconnect():
                self._discord_bridge_ok     = False
                self._discord_bridge_status = "⚠️ Mất kết nối — đang reconnect..."
                _dc_log("sys", "", "⚠️ Bot mất kết nối Discord, discord.py đang tự reconnect...")

            @c.event
            async def on_resumed():
                self._discord_bridge_ok     = True
                self._discord_bridge_status = f"✅ Đã reconnect — 🟢 Online"
                _dc_log("sys", "", "✅ Bot đã reconnect thành công")

            @c.event
            async def on_message(message):
                # Chỉ xử lý kênh đã cấu hình
                if str(message.channel.id) != str(DISCORD_CHAT_CHANNEL_ID):
                    return
                # Bỏ qua bot và webhook (tránh vòng lặp ingame→discord→ingame)
                if message.author.bot or message.webhook_id:
                    return
                content = message.content.strip()
                if not content:
                    return
                # Lệnh kiểm tra Bot 2 từ Bot 1
                cmd = content.lower()
                if cmd in {"!pingbot2", "!ping2"}:
                    bot2_ok = bool(getattr(self, "_discord_bot2_ok", False))
                    bot2_status = str(getattr(self, "_discord_bot2_status", "unknown"))
                    bot2_client = getattr(self, "_discord_bot2_client", None)
                    bot2_connected = False
                    bot2_latency_ms = -1
                    bot2_name = "Bot2"
                    try:
                        if bot2_client is not None:
                            bot2_connected = not bool(bot2_client.is_closed())
                            if getattr(bot2_client, "user", None):
                                bot2_name = bot2_client.user.name
                            lat = float(getattr(bot2_client, "latency", 0.0) or 0.0)
                            if lat > 0:
                                bot2_latency_ms = int(lat * 1000)
                    except Exception:
                        pass

                    ok = bot2_ok and bot2_connected
                    line1 = f"✅ Bot 2 OK: {bot2_name}" if ok else "❌ Bot 2 chưa sẵn sàng"
                    line2 = (
                        f"• connected: {'YES' if bot2_connected else 'NO'} | "
                        f"latency: {bot2_latency_ms if bot2_latency_ms >= 0 else 'n/a'} ms"
                    )
                    line3 = f"• status: {bot2_status}"
                    await message.channel.send(f"{line1}\n{line2}\n{line3}")
                    _dc_log("sys", "Bot1", f"pingbot2 -> ok={ok}, connected={bot2_connected}, latency={bot2_latency_ms}")
                    return
                # Xóa mention <@id>
                clean = _re.sub(r"<@!?\d+>", "", content).strip()
                if not clean:
                    return
                username = message.author.display_name or message.author.name
                broadcast_text = f"[Discord] {username}: {clean}"
                self.send_ingame_broadcast(broadcast_text)
                self._enqueue_console(f"💬 [Discord] {username}: {clean}")
                self._discord_msg_in  += 1
                self._discord_last_check = time.time()
                _dc_log("from_dc", username, clean)

            return c

        # ── Chạy bot với auto-reconnect ───────────────────────────
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._discord_bot_loop = loop

        while True:
            client = _make_client()
            self._discord_bot_client = client
            self._discord_bridge_status = "⏳ Đang kết nối Discord Gateway..."
            _dc_log("sys", "", "⏳ Đang kết nối Discord Gateway WebSocket...")
            try:
                loop.run_until_complete(client.start(DISCORD_BOT_TOKEN))
            except _discord.errors.LoginFailure:
                self._discord_bridge_ok     = False
                self._discord_bridge_status = "❌ Bot Token không hợp lệ"
                self._enqueue_console(
                    "❌ Discord: Bot Token không hợp lệ — vào CÀI ĐẶT → App Config để sửa")
                _dc_log("sys", "", "❌ LoginFailure — Token sai, dừng hẳn")
                return   # Không retry nếu token sai
            except _discord.errors.PrivilegedIntentsRequired:
                self._discord_bridge_ok     = False
                self._discord_bridge_status = "❌ Cần bật Message Content Intent"
                self._enqueue_console(
                    "❌ Discord: Cần bật 'MESSAGE CONTENT INTENT'\n"
                    "   → discord.com/developers/applications → Bot của bạn → Bot\n"
                    "   → Privileged Gateway Intents → MESSAGE CONTENT INTENT ✅")
                _dc_log("sys", "", "❌ PrivilegedIntentsRequired — bật Message Content Intent")
                return
            except KeyboardInterrupt:
                return
            except Exception as e:
                self._discord_bridge_ok     = False
                self._discord_bridge_status = f"⚠️ Lỗi kết nối — thử lại sau 15s"
                _dc_log("sys", "", f"⚠️ Lỗi: {e} — thử lại sau 15s...")
            finally:
                try:
                    if not client.is_closed():
                        loop.run_until_complete(client.close())
                except Exception:
                    pass
            time.sleep(15)

    def discord_bot2_poll(self):
        """Background thread: chạy Discord Bot 2 với commands và tính năng riêng.
        Bot này có thể dùng cho ranking, stats, server info, và các commands khác.
        """
        import asyncio
        try:
            import discord as _discord
            from discord.ext import commands
        except ImportError:
            self._discord_bot2_status = "❌ Thiếu thư viện discord.py — pip install discord.py"
            self._enqueue_console("❌ Discord Bot 2: pip install discord.py")
            return

        # ── Chờ app khởi động xong ───────────────────────────────
        time.sleep(10)

        if not DISCORD_BOT2_TOKEN:
            self._discord_bot2_status = "⚠️ Chưa cấu hình Bot 2 Token"
            self._enqueue_console("⚠️ Discord Bot 2: chưa cấu hình Token")
            return

        # ── Tạo bot với commands ────────────────────────────────
        intents = _discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        bot = commands.Bot(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # ── Capture outer self để dùng trong View closures ─────────
        _app = self   # ServerPalApp instance

        def _save_bot2_channel_config(main_channel_id: str | None = None,
                                      ranking_channel_id: str | None = None):
            """Lưu channel id của Bot2 vào manager_config để giữ sau restart."""
            global DISCORD_BOT2_CHANNEL_ID, DISCORD_BOT2_RANKING_CHANNEL_ID
            try:
                cfg = _read_manager_cfg()
                if not isinstance(cfg, dict):
                    cfg = {}
                if main_channel_id is not None:
                    DISCORD_BOT2_CHANNEL_ID = str(main_channel_id).strip()
                    cfg["DISCORD_BOT2_CHANNEL_ID"] = DISCORD_BOT2_CHANNEL_ID
                if ranking_channel_id is not None:
                    DISCORD_BOT2_RANKING_CHANNEL_ID = str(ranking_channel_id).strip()
                    cfg["DISCORD_BOT2_RANKING_CHANNEL_ID"] = DISCORD_BOT2_RANKING_CHANNEL_ID
                with open(MANAGER_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
            except Exception as e:
                self._enqueue_console(f"⚠️ Bot2: Không lưu được channel config: {e}")

        def _save_manager_cfg(cfg: dict) -> bool:
            try:
                with open(MANAGER_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
                return True
            except Exception as e:
                self._enqueue_console(f"⚠️ Bot2: Không lưu được manager_config: {e}")
                return False

        def _read_server_profiles() -> dict:
            try:
                cfg = _read_manager_cfg()
                servers = cfg.get("DISCORD_SERVER_PROFILES", {})
                return servers if isinstance(servers, dict) else {}
            except Exception:
                return {}
        def _get_active_server_name() -> str:
            try:
                cfg = _read_manager_cfg() or {}
                name = str(cfg.get("DISCORD_SERVER_ACTIVE", "") or "").strip()
                return name
            except Exception:
                return ""
        def _get_active_server_profile() -> tuple[str, dict]:
            name = _get_active_server_name()
            profiles = _read_server_profiles()
            prof = profiles.get(name, {}) if name and isinstance(profiles, dict) else {}
            return name, prof

        @bot.tree.command(name="pingserver", description="Kiểm tra kết nối IP:PORT game (TCP), REST và RCON")
        async def slash_pingserver(interaction: _discord.Interaction):
            """Slash command: Ping server đa tầng từ Discord (TCP/REST/RCON)."""
            await interaction.response.defer(thinking=True, ephemeral=True)

            def _tcp_check(host: str, port: int, timeout_sec: float = 3.0) -> bool:
                try:
                    with socket.create_connection((host, int(port)), timeout=float(timeout_sec)):
                        return True
                except Exception:
                    return False

            def _ping_once(host: str, timeout_ms: int = 1200) -> bool:
                try:
                    cp = subprocess.run(
                        ["ping", "-n", "1", "-w", str(int(timeout_ms)), host],
                        capture_output=True, text=True,
                        timeout=max(2, int(timeout_ms / 1000) + 2)
                    )
                    return cp.returncode == 0
                except Exception:
                    return False

            name, prof = _get_active_server_profile()
            ip = str(prof.get("ip_public", "") or "").strip()
            game_port = int(str(prof.get("game_port", "") or "0") or 0) if prof else 0

            if not ip or not game_port:
                await interaction.followup.send(
                    content="⚠️ Chưa cấu hình profile server active (ip_public/game_port). Dùng /createserver trước.",
                    ephemeral=True
                )
                return

            loop = asyncio.get_event_loop()
            try:
                ping_ok = await loop.run_in_executor(None, lambda: _ping_once(ip))
                tcp_ok  = await loop.run_in_executor(None, lambda: _tcp_check(ip, game_port, 3.0))

                def _rest_ok() -> bool:
                    try:
                        res = requests.get(f"{API_URL}/info", auth=AUTH, timeout=4)
                        return res.status_code == 200
                    except Exception:
                        return False

                def _rcon_ok() -> bool:
                    try:
                        res = rcon_exec("ShowPlayers")
                        return isinstance(res, str) and bool(res.strip()) and not res.startswith("RCON Error:")
                    except Exception:
                        return False

                rest_ok = await loop.run_in_executor(None, _rest_ok)
                rcon_ok = await loop.run_in_executor(None, _rcon_ok)

                overall = tcp_ok and (rest_ok or rcon_ok)
                status  = "✅ ONLINE (có thể vào được)" if overall else "❌ Chưa sẵn sàng hoặc lỗi"

                msg = (
                    f"• Profile: `{name or 'N/A'}` — `{ip}:{game_port}`\n"
                    f"• ping: {'OK' if ping_ok else 'FAIL'} | "
                    f"tcp: {'OK' if tcp_ok else 'FAIL'} | "
                    f"rest: {'OK' if rest_ok else 'FAIL'} | "
                    f"rcon: {'OK' if rcon_ok else 'FAIL'}\n"
                    f"→ Trạng thái: {status}"
                )
                await interaction.followup.send(content=msg, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(content=f"⚠️ Ping lỗi: {e}", ephemeral=True)

        @bot.tree.command(name="start", description="Khởi động server (an toàn)")
        async def slash_start(interaction: _discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                if _app._is_server_running():
                    await interaction.followup.send("ℹ️ Server đang chạy rồi.", ephemeral=True)
                    return
                ok = _app._start_server_safe(source="Discord Start")
                if ok:
                    await interaction.followup.send("✅ Đã gửi lệnh khởi động — vui lòng chờ server online.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Không thể khởi động server.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi START: {e}", ephemeral=True)

        @bot.tree.command(name="stop", description="Dừng server an toàn (cảnh báo 10s/5s, lưu trước khi tắt)")
        async def slash_stop(interaction: _discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                if not _app._is_server_running():
                    await interaction.followup.send("ℹ️ Server đang tắt.", ephemeral=True)
                    return
                threading.Thread(target=_app._stop_sequence_discord, args=("Discord",), daemon=True).start()
                await interaction.followup.send("🛑 Đã bắt đầu quy trình dừng server (10s/5s) và lưu dữ liệu.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi STOP: {e}", ephemeral=True)

        @bot.tree.command(name="reset", description="Reset server 30s như giao diện điều khiển (có cảnh báo)")
        async def slash_reset(interaction: _discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                threading.Thread(target=_app.reset_sequence, daemon=True).start()
                await interaction.followup.send("🔁 Đã bắt đầu quy trình RESET 30s (cảnh báo + save).", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi RESET: {e}", ephemeral=True)

        @bot.tree.command(name="livemap", description="LiveMap: vị trí người chơi online (tọa độ X/Y + guild)")
        async def slash_livemap(interaction: _discord.Interaction, top: int = 25):
            await interaction.response.defer(ephemeral=True)
            try:
                # /livemap: tạo 1 card nếu chưa có, sau đó chỉ edit card này để chống spam.
                lim = max(1, min(int(top or 25), 50))
                _, prof = _get_active_server_profile()
                ch_id = str(
                    prof.get("status_channel_id", "")
                    or DISCORD_BOT2_LIVEMAP_CHANNEL_ID
                    or DISCORD_BOT2_CHANNEL_ID
                    or interaction.channel_id
                ).strip()
                target_ch = bot.get_channel(int(ch_id)) if ch_id else interaction.channel
                if not target_ch:
                    target_ch = interaction.channel

                emb, map_file = await _build_livemap_embed(limit=lim)
                if self._bot2_livemap_msg_id:
                    self._bot2_livemap_msg_id = await _upsert_livemap_message(
                        target_ch, self._bot2_livemap_msg_id, emb, map_file
                    )
                if not self._bot2_livemap_msg_id:
                    if map_file and os.path.isfile(map_file):
                        dfile = _discord.File(map_file, filename="discord_livemap.png")
                        m = await target_ch.send(embed=emb, file=dfile, view=LiveMapView())
                    else:
                        m = await target_ch.send(embed=emb, view=LiveMapView())
                    self._bot2_livemap_msg_id = m.id
                    self._save_bot2_msg_ids()

                await interaction.followup.send(
                    "✅ LiveMap card đã bật auto-refresh mỗi 10 giây (anti-spam: chỉ edit 1 message).",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi LIVEMAP: {e}", ephemeral=True)

        def _is_discord_admin(interaction: _discord.Interaction) -> bool:
            try:
                perms = getattr(interaction.user, "guild_permissions", None)
                return bool(perms and (perms.administrator or perms.manage_guild))
            except Exception:
                return False

        # ══════════════════════════════════════════════════════════
        # ── Helper: build server-status embed ─────────────────────
        # ══════════════════════════════════════════════════════════
        async def _build_server_embed():
            """Tạo embed thông tin server — dữ liệu live từ REST API."""
            _loop = asyncio.get_event_loop()
            info_ok = False
            metrics_ok = False
            players_ok = False
            try:
                info_res    = await _loop.run_in_executor(None, lambda: requests.get(f"{API_URL}/info",    auth=AUTH, timeout=5))
                metrics_res = await _loop.run_in_executor(None, lambda: requests.get(f"{API_URL}/metrics", auth=AUTH, timeout=5))
                players_res = await _loop.run_in_executor(None, lambda: requests.get(f"{API_URL}/players", auth=AUTH, timeout=5))
                info_ok = info_res.status_code == 200
                metrics_ok = metrics_res.status_code == 200
                players_ok = players_res.status_code == 200
                info    = info_res.json()    if info_ok else {}
                metrics = metrics_res.json() if metrics_ok else {}
                players = players_res.json().get("players", []) if players_ok else []
            except Exception:
                info = {}; metrics = {}; players = []

            server_name = info.get("servername") or info.get("ServerName") or "Manager ServerPal"
            description = info.get("description") or info.get("Description") or "Anh Em Bốn Phương | Máy Chủ Hàng Đầu Việt NAm"
            world_guid  = info.get("worldguid")  or info.get("WorldGuid")  or "N/A"
            version     = info.get("version")    or info.get("Version")    or "N/A"

            cur_players = metrics.get("currentplayernum") or len(players)
            max_players = metrics.get("maxplayernum")     or _app._max_players or 2003
            days        = metrics.get("days", "?")
            fps         = round(metrics.get("serverfps", 0), 1) if metrics.get("serverfps") else "?"
            frame_time  = metrics.get("serverframetime", 0)
            latency_ms  = "?"
            if isinstance(frame_time, (int, float)) and frame_time > 0:
                # Có API trả về giây, có API trả về ms -> tự nhận diện để tránh ping bị phóng đại.
                latency_val = frame_time * 1000 if frame_time <= 10 else frame_time
                latency_ms = f"{int(round(latency_val))} ms"
            uptime_sec  = metrics.get("uptime", 0)
            if isinstance(uptime_sec, (int, float)) and uptime_sec > 0:
                uptime_str = f"{int(uptime_sec // 3600)}h {int((uptime_sec % 3600) // 60)}m"
            else:
                uptime_str = "0 phút"

            # Thanh % người chơi
            pct     = min(cur_players / max(max_players, 1), 1.0)
            filled  = round(pct * 12)
            pbar    = "█" * filled + "░" * (12 - filled)
            color   = 0x57F287 if cur_players > 0 else 0x5865F2
            is_online = bool(info_ok or metrics_ok or players_ok)
            status_text = "🟢 Online" if is_online else "🔴 Offline"

            now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            embed = _discord.Embed(
                title=f"🌐  {server_name}",
                description=f"```{description}```",
                color=color,
                timestamp=datetime.datetime.now(datetime.UTC)
            )
            embed.add_field(name="👥 Người chơi",   value=f"```{cur_players} / {max_players}\n{pbar} {pct*100:.0f}%```", inline=False)
            embed.add_field(name="📶 Trạng Thái", value=f"```{status_text}```", inline=True)
            embed.add_field(name="🔖 Phiên bản",   value=f"```{version}```",        inline=True)
            embed.add_field(name="📅 Số ngày ingame",      value=f"```{days}```",           inline=True)
            embed.add_field(name="⚡ FPS",       value=f"```{fps}```",            inline=True)
            embed.add_field(name="⏱️ Uptime",   value=f"```{uptime_str}```",     inline=True)
            embed.add_field(name="📡 Ping",      value=f"```{latency_ms}```",     inline=True)
            embed.add_field(name="🆔 World GUID",value=f"```{world_guid}```",     inline=False)

            if players:
                def _fmt_ping(v):
                    try:
                        if v is None or v == "":
                            return "—"
                        val = float(v)
                        # Tự nhận diện đơn vị (s -> ms) để đồng bộ với ping server.
                        if val <= 10:
                            val *= 1000
                        return f"{int(round(val))} ms"
                    except Exception:
                        return "—"
                rows = "\n".join(f"  {i:>2}. {p.get('name','?')[:24]} — {_fmt_ping(p.get('ping'))}"
                                 for i, p in enumerate(players[:20], 1))
                if len(players) > 20:
                    rows += f"\n  … và {len(players)-20} người khác"
                embed.add_field(
                    name=f"🟢 Đang Online — {cur_players} người",
                    value=f"```{rows}```",
                    inline=False
                )
            else:
                embed.add_field(name="🔴 Server đang trống", value="```Chưa có người chơi nào online```", inline=False)

            embed.set_footer(text=f"🔄 Tự động cập nhật •  {now_str}")
            return embed

        # ══════════════════════════════════════════════════════════
        # ── Helper: build top-10 ranking embed ────────────────────
        # ══════════════════════════════════════════════════════════
        def _build_ranking_embed():
            """Tạo embed top 10 level, live từ player_stats cache."""
            ranking = _app._get_ranking(10)
            total   = len([s for s in _app.player_stats.values()
                           if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])

            now_str  = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            MEDALS   = ["🥇", "🥈", "🥉"]
            LVL_ICON = {True: "💎", False: None}   # placeholder

            embed = _discord.Embed(
                title="🏆  BẢNG XẾP HẠNG  —  TOP 10 LEVEL",
                color=0xFFD700,
                timestamp=datetime.datetime.now(datetime.UTC)
            )

            if not ranking:
                embed.description = "```Chưa có dữ liệu — đang đồng bộ từ server...```"
            else:
                max_level = max(p["level"] for p in ranking) or 1
                rows = ""
                for idx, p in enumerate(ranking, 1):
                    medal = MEDALS[idx-1] if idx <= 3 else f"` {idx:>2}.`"
                    name  = p["name"][:20]
                    lvl   = p["level"]
                    pal   = p["pal_count"]
                    ptime = _app._fmt_playtime(p.get("playtime_sec", 0))

                    # Progress bar 12 ký tự
                    filled = round((lvl / max_level) * 12)
                    bar    = "█" * filled + "░" * (12 - filled)

                    if   lvl >= 50: icon = "💎"
                    elif lvl >= 30: icon = "🔥"
                    elif lvl >= 15: icon = "⭐"
                    else:           icon = "🌱"

                    rows += f"{medal} **{name}**\n"
                    rows += f"    {icon} `Lv.{lvl:>3}`  `{bar}`  🎣 `{pal:>4} Pal`  ⏱ `{ptime}`\n\n"
                    if len(rows) > 3600:
                        rows += "…\n"
                        break

                embed.add_field(name="🏅 Bảng Xếp Hạng", value=rows, inline=False)

                avg_lv  = sum(p["level"]     for p in ranking) / len(ranking)
                avg_pal = sum(p["pal_count"] for p in ranking) / len(ranking)
                top1    = ranking[0]["name"] if ranking else "—"
                embed.add_field(name="👑 Số 1",          value=f"```{top1}```",         inline=True)
                embed.add_field(name="📈 Cấp TB Top10",  value=f"```{avg_lv:.1f}```",   inline=True)
                embed.add_field(name="👥 Tổng đã chơi",  value=f"```{total}```",         inline=True)

            embed.set_footer(text=f"🔄 Tự động cập nhật  •  {now_str}  •  !stats [tên] để xem chi tiết")
            return embed

        # ══════════════════════════════════════════════════════════
        # ── Discord UI Views với nút Refresh ──────────────────────
        # ══════════════════════════════════════════════════════════
        class ServerView(_discord.ui.View):
            """View gắn vào card server status — có nút 🔄 Làm mới."""
            def __init__(self_v):
                super().__init__(timeout=None)

            @_discord.ui.button(
                label="🔄  Làm mới",
                style=_discord.ButtonStyle.blurple,
                custom_id="btn_sv_refresh"
            )
            async def do_refresh(self_v, interaction: _discord.Interaction,
                                 button: _discord.ui.Button):
                button.disabled = True
                button.label    = "⏳  Đang cập nhật…"
                await interaction.response.edit_message(view=self_v)
                try:
                    embed = await _build_server_embed()
                    new_view = ServerView()
                    await interaction.message.edit(embed=embed, view=new_view)
                except Exception as exc:
                    button.disabled = False
                    button.label    = "🔄  Làm mới"
                    await interaction.message.edit(view=self_v)

        class RankingView(_discord.ui.View):
            """View gắn vào card ranking — có nút 🔄 Làm mới + 📊 Top 20."""
            def __init__(self_v):
                super().__init__(timeout=None)

            @_discord.ui.button(
                label="🔄  Làm mới",
                style=_discord.ButtonStyle.blurple,
                custom_id="btn_rk_refresh"
            )
            async def do_refresh(self_v, interaction: _discord.Interaction,
                                 button: _discord.ui.Button):
                button.disabled = True
                button.label    = "⏳  Đang cập nhật…"
                await interaction.response.edit_message(view=self_v)
                try:
                    # Sync levels từ API trước khi build embed
                    _loop = asyncio.get_event_loop()
                    await _loop.run_in_executor(None, _app._update_player_levels)
                    embed = _build_ranking_embed()
                    new_view = RankingView()
                    await interaction.message.edit(embed=embed, view=new_view)
                except Exception as exc:
                    button.disabled = False
                    button.label    = "🔄  Làm mới"
                    await interaction.message.edit(view=self_v)

            @_discord.ui.button(
                label="📊  Top 20",
                style=_discord.ButtonStyle.secondary,
                custom_id="btn_rk_top20"
            )
            async def show_top20(self_v, interaction: _discord.Interaction,
                                 button: _discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                try:
                    r20 = _app._get_ranking(20)
                    if not r20:
                        await interaction.followup.send("📊 Chưa có dữ liệu.", ephemeral=True)
                        return
                    MEDALS2 = ["🥇", "🥈", "🥉"]
                    lines = []
                    for i, p in enumerate(r20, 1):
                        m = MEDALS2[i-1] if i <= 3 else f"`{i:>2}.`"
                        lines.append(f"{m} **{p['name'][:20]}** — Lv.`{p['level']}` | 🎣`{p['pal_count']}`")
                    e = _discord.Embed(
                        title="📊 Top 20 Level",
                        description="\n".join(lines),
                        color=0x00ff88,
                        timestamp=datetime.datetime.utcnow()
                    )
                    await interaction.followup.send(embed=e, ephemeral=True)
                except Exception as exc:
                    await interaction.followup.send(f"❌ Lỗi: {exc}", ephemeral=True)

        class LiveMapView(_discord.ui.View):
            """View gắn vào card livemap — có nút 🔄 Làm mới."""
            def __init__(self_v):
                super().__init__(timeout=None)

            @_discord.ui.button(
                label="🔄  Làm mới",
                style=_discord.ButtonStyle.blurple,
                custom_id="btn_lm_refresh"
            )
            async def do_refresh(self_v, interaction: _discord.Interaction,
                                 button: _discord.ui.Button):
                button.disabled = True
                button.label    = "⏳  Đang cập nhật…"
                await interaction.response.edit_message(view=self_v)
                try:
                    emb, map_file = await _build_livemap_embed(limit=25)
                    new_view = LiveMapView()
                    if map_file and os.path.isfile(map_file):
                        dfile = _discord.File(map_file, filename="discord_livemap.png")
                        await interaction.message.edit(embed=emb, attachments=[dfile], view=new_view)
                    else:
                        await interaction.message.edit(embed=emb, view=new_view)
                finally:
                    pass

        # ══════════════════════════════════════════════════════════
        # ── Helper: upsert message (edit hoặc gửi mới + view) ─────
        # ══════════════════════════════════════════════════════════
        async def _upsert_message(channel, msg_id: int, embed, view=None,
                                  kind: str = ""):
            """Chế độ anti-spam: chỉ EDIT tin nhắn đã có, không tự gửi mới.
            kind = 'server' | 'ranking' để phân loại log nếu cần.
            """
            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(embed=embed, view=view)
                    return msg_id
                except Exception:
                    # Tin nhắn bị xóa / không còn quyền / sai channel -> reset ID.
                    return 0
            # Không có msg_id: bỏ qua để tránh tự tạo thêm tin nhắn.
            return 0

        # ── on_ready ────────────────────────────────────────────────
        @bot.event
        async def on_ready():
            try:
                synced = await bot.tree.sync()
                self._enqueue_console(f"✅ Discord Bot 2: Đã sync {len(synced)} slash commands")
                # Sync nhanh theo guild hiện tại để lệnh mới hiện ngay (không phải chờ global propagation).
                try:
                    ch = bot.get_channel(int(DISCORD_BOT2_CHANNEL_ID)) if str(DISCORD_BOT2_CHANNEL_ID).strip() else None
                    guild_obj = ch.guild if ch and getattr(ch, "guild", None) else None
                    if guild_obj:
                        bot.tree.copy_global_to(guild=guild_obj)
                        gsynced = await bot.tree.sync(guild=guild_obj)
                        self._enqueue_console(f"✅ Discord Bot 2: Guild sync {len(gsynced)} lệnh cho guild {guild_obj.id}")
                except Exception as ge:
                    self._enqueue_console(f"⚠️ Discord Bot 2: Guild sync lỗi: {ge}")
            except Exception as e:
                self._enqueue_console(f"⚠️ Discord Bot 2: Lỗi sync: {e}")

            self._discord_bot2_ok     = True
            self._discord_bot2_status = f"✅ {bot.user.name} — 🟢 Online"
            self._enqueue_console(f"✅ Discord Bot 2 '{bot.user.name}' đã kết nối — Online!")

            # Đăng ký persistent views để button hoạt động sau restart
            bot.add_view(ServerView())
            bot.add_view(RankingView())
            bot.add_view(LiveMapView())

            # ── Khôi phục message IDs sau restart ──────────────────────
            # server card ở kênh lệnh chính, ranking card ở kênh ranking riêng.
            try:
                main_channel_id = (str(DISCORD_BOT2_CHANNEL_ID or "").strip() or "")
                ranking_channel_id = (str(DISCORD_BOT2_RANKING_CHANNEL_ID or "").strip() or main_channel_id)

                async def _restore_card(channel_id: str, attr: str, kind: str, title_mark: str):
                    if not channel_id:
                        setattr(self, attr, 0)
                        return
                    ch = bot.get_channel(int(channel_id))
                    if not ch:
                        setattr(self, attr, 0)
                        return

                    mid = getattr(self, attr, 0)
                    if mid:
                        try:
                            await ch.fetch_message(mid)
                            self._enqueue_console(f"♻️ Bot2: Tìm thấy {kind} message #{mid} — sẽ dùng lại")
                            return
                        except Exception:
                            setattr(self, attr, 0)
                            self._enqueue_console(f"⚠️ Bot2: {kind} message #{mid} không còn — sẽ tìm lại")

                    async for old_msg in ch.history(limit=100):
                        if old_msg.author.id != bot.user.id:
                            continue
                        if not old_msg.embeds:
                            continue
                        title = old_msg.embeds[0].title or ""
                        if title_mark in title:
                            setattr(self, attr, old_msg.id)
                            self._enqueue_console(f"♻️ Bot2: Tìm thấy {kind} card cũ #{old_msg.id} — dùng lại")
                            return

                await _restore_card(main_channel_id, "_bot2_status_msg_id", "server", "🌐")
                await _restore_card(ranking_channel_id, "_bot2_ranking_msg_id", "ranking", "🏆")
                await _restore_card(main_channel_id, "_bot2_livemap_msg_id", "livemap", "🗺️")
                self._save_bot2_msg_ids()
            except Exception as scan_err:
                self._enqueue_console(f"⚠️ Bot2: Lỗi khi khôi phục msg IDs: {scan_err}")

            if not task_update_server.is_running():
                task_update_server.start()
            if not task_update_ranking.is_running():
                task_update_ranking.start()
            if not task_update_livemap.is_running():
                task_update_livemap.start()

        # ══════════════════════════════════════════════════════════
        # ── Auto-update tasks ──────────────────────────────────────
        # ══════════════════════════════════════════════════════════
        from discord.ext import tasks as _tasks

        _last_level_sync = [0.0]   # dùng list để mutate trong closure

        @_tasks.loop(seconds=10)
        async def task_update_server():
            """Cập nhật card server status mỗi 10 giây."""
            try:
                # Ưu tiên kênh mapping theo server profile active; fallback global.
                _, prof = _get_active_server_profile()
                ch_id = str(prof.get("status_channel_id", "") or DISCORD_BOT2_CHANNEL_ID).strip()
                if not ch_id:
                    return
                channel = bot.get_channel(int(ch_id))
                if not channel:
                    return
                embed = await _build_server_embed()
                self._bot2_status_msg_id = await _upsert_message(
                    channel, self._bot2_status_msg_id, embed, ServerView(),
                    kind="server"
                )
            except Exception as exc:
                self._enqueue_console(f"⚠️ task_update_server: {exc}")

        @_tasks.loop(seconds=10)
        async def task_update_ranking():
            """Cập nhật bảng xếp hạng mỗi 10 giây.
            Level sync từ API mỗi 30 giây để tránh overload."""
            _, prof = _get_active_server_profile()
            ranking_channel_id = str(prof.get("ranking_channel_id", "") or DISCORD_BOT2_RANKING_CHANNEL_ID or DISCORD_BOT2_CHANNEL_ID).strip()
            if not ranking_channel_id:
                return
            try:
                channel = bot.get_channel(int(ranking_channel_id))
                if not channel:
                    return

                # Sync levels từ API mỗi 30 giây
                now = time.time()
                if now - _last_level_sync[0] >= 30:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._update_player_levels
                    )
                    _last_level_sync[0] = now

                embed = _build_ranking_embed()
                self._bot2_ranking_msg_id = await _upsert_message(
                    channel, self._bot2_ranking_msg_id, embed, RankingView(),
                    kind="ranking"
                )
            except Exception as exc:
                self._enqueue_console(f"⚠️ task_update_ranking: {exc}")

        async def _build_livemap_embed(limit: int = 25):
            try:
                players = list(_app._map_players_data) if getattr(_app, "_map_players_data", None) else []
                if not players:
                    loop = asyncio.get_event_loop()
                    res = await loop.run_in_executor(None, lambda: requests.get(f"{API_URL}/players", auth=AUTH, timeout=5))
                    if res.status_code == 200:
                        players = res.json().get("players", [])
                        try:
                            _app._map_players_data = players
                        except Exception:
                            pass
                emb = _discord.Embed(
                    title="🗺️ LIVE MAP",
                    description=f"👥 Online hiện tại: **{len(players)}**",
                    color=0x00DDFF,
                    timestamp=datetime.datetime.now(datetime.UTC)
                )
                if not players:
                    emb.add_field(name="Trạng thái", value="```Chưa có người chơi online```", inline=False)
                    return emb, ""
                rows = []
                gpm = getattr(_app, "_map_guild_player_map", {}) or {}
                lim = max(1, min(int(limit or 25), 50))
                for i, p in enumerate(players[:lim], 1):
                    name = str(p.get("name", "?"))[:20]
                    lv = p.get("level", "?")
                    lx = p.get("location_x")
                    ly = p.get("location_y")
                    guild = _app._lookup_guild(p, gpm) or "—"
                    if lx is not None and ly is not None:
                        mx = (float(ly) - 157664.55791065) / 462.962962963
                        my = (float(lx) + 123467.1611767) / 462.962962963
                        rows.append(f"{i:>2}. {name} | Lv.{lv} | {guild[:12]} | X:{mx:.0f} Y:{my:.0f}")
                    else:
                        rows.append(f"{i:>2}. {name} | Lv.{lv} | {guild[:12]} | X:— Y:—")
                if len(players) > lim:
                    rows.append(f"... và {len(players) - lim} người khác")
                emb.add_field(
                    name=f"Danh sách (Top {lim})",
                    value=f"```{chr(10).join(rows)[:3900]}```",
                    inline=False
                )
                map_file = _app._render_discord_livemap_image(size=1024)
                if map_file:
                    emb.set_image(url="attachment://discord_livemap.png")
                emb.set_footer(text="Tự động cập nhật mỗi 10 giây • LiveMap ảnh + tọa độ")
                return emb, map_file
            except Exception as e:
                return _discord.Embed(title="🗺️ LIVE MAP", description=f"❌ Lỗi: {e}", color=0xED4245), ""

        async def _upsert_livemap_message(channel, msg_id: int, embed, map_file: str):
            if not msg_id:
                return 0
            try:
                msg = await channel.fetch_message(msg_id)
                if map_file and os.path.isfile(map_file):
                    dfile = _discord.File(map_file, filename="discord_livemap.png")
                    await msg.edit(embed=embed, attachments=[dfile], view=LiveMapView())
                else:
                    await msg.edit(embed=embed, view=LiveMapView())
                return msg_id
            except Exception:
                return 0

        @_tasks.loop(seconds=10)
        async def task_update_livemap():
            """Cập nhật LiveMap card mỗi 10 giây (edit tin nhắn cũ, tránh spam)."""
            try:
                # Ưu tiên kênh status của profile; fallback livemap channel id; cuối cùng dùng DISCORD_BOT2_CHANNEL_ID
                _, prof = _get_active_server_profile()
                ch_id = str(
                    prof.get("status_channel_id", "")
                    or DISCORD_BOT2_LIVEMAP_CHANNEL_ID
                    or DISCORD_BOT2_CHANNEL_ID
                ).strip()
                if not ch_id:
                    return
                channel = bot.get_channel(int(ch_id))
                if not channel:
                    return
                embed, map_file = await _build_livemap_embed(limit=25)
                self._bot2_livemap_msg_id = await _upsert_livemap_message(
                    channel, self._bot2_livemap_msg_id, embed, map_file
                )
                if self._bot2_livemap_msg_id:
                    self._save_bot2_msg_ids()
            except Exception as exc:
                self._enqueue_console(f"⚠️ task_update_livemap: {exc}")

        @task_update_server.before_loop
        @task_update_ranking.before_loop
        @task_update_livemap.before_loop
        async def before_tasks():
            await bot.wait_until_ready()
            await asyncio.sleep(3)   # Chờ 3 giây sau ready mới bắt đầu

        @bot.event
        async def on_disconnect():
            self._discord_bot2_ok = False
            self._discord_bot2_status = "⚠️ Mất kết nối — đang reconnect..."

        @bot.event
        async def on_resumed():
            self._discord_bot2_ok = True
            self._discord_bot2_status = f"✅ Đã reconnect — 🟢 Online"

        # ── Commands ──────────────────────────────────────────────
        @bot.command(name='refresh', aliases=['update', 'capnhat', 'r'])
        async def cmd_refresh(ctx):
            """Cập nhật ngay server status + ranking board.
            Usage: !refresh
            """
            msg = await ctx.send("⏳ Đang cập nhật server status và bảng xếp hạng...")
            try:
                server_channel = bot.get_channel(int(DISCORD_BOT2_CHANNEL_ID)) if DISCORD_BOT2_CHANNEL_ID else ctx.channel
                if not server_channel:
                    server_channel = ctx.channel
                _, prof = _get_active_server_profile()
                ranking_channel_id = str(prof.get("ranking_channel_id", "") or DISCORD_BOT2_RANKING_CHANNEL_ID or DISCORD_BOT2_CHANNEL_ID).strip()
                ranking_channel = bot.get_channel(int(ranking_channel_id)) if ranking_channel_id else server_channel
                if not ranking_channel:
                    ranking_channel = server_channel

                # Sync levels từ API
                await asyncio.get_event_loop().run_in_executor(None, self._update_player_levels)
                _last_level_sync[0] = time.time()

                # Upsert server status với ServerView
                sv_embed = await _build_server_embed()
                self._bot2_status_msg_id = await _upsert_message(
                    server_channel, self._bot2_status_msg_id, sv_embed, ServerView(),
                    kind="server"
                )

                # Upsert ranking với RankingView
                rk_embed = _build_ranking_embed()
                self._bot2_ranking_msg_id = await _upsert_message(
                    ranking_channel, self._bot2_ranking_msg_id, rk_embed, RankingView(),
                    kind="ranking"
                )
                self._save_bot2_msg_ids()
                if self._bot2_status_msg_id and self._bot2_ranking_msg_id:
                    await msg.edit(content="✅ Đã làm mới server status + bảng xếp hạng (chế độ anti-spam: chỉ edit).")
                else:
                    await msg.edit(
                        content=("⚠️ Chưa có message cố định để edit.\n"
                                 "Admin hãy gửi sẵn card của bot (hoặc để bot có card cũ), "
                                 "sau đó lưu đúng message ID để bot chỉ tự động làm mới.")
                    )
                await asyncio.sleep(3)
                try:
                    await msg.delete()
                except Exception:
                    pass
            except Exception as e:
                await msg.edit(content=f"❌ Lỗi: {e}")

        @bot.command(name='ranking', aliases=['rank', 'top', 'leaderboard', 'xephang'])
        async def cmd_ranking(ctx, top: int = 10):
            """Hiển thị bảng xếp hạng người chơi.
            Usage: !ranking [số lượng] (mặc định: 10, tối đa 20)
            """
            try:
                ranking = self._get_ranking(min(top, 20))  # Tối đa 20
                
                if not ranking:
                    await ctx.send("📊 Chưa có dữ liệu xếp hạng.")
                    return

                # Tính tổng số người chơi có dữ liệu
                total_players = len([s for s in self.player_stats.values() 
                                   if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])

                # Tạo embed đẹp và chuyên nghiệp
                embed = _discord.Embed(
                    title="🏆 BẢNG XẾP HẠNG NGƯỜI CHƠI",
                    description=f"📊 **Top {len(ranking)} người chơi**\n👥 Tổng số người chơi có dữ liệu: **{total_players}**",
                    color=0x00ff88
                )

                medals = ["🥇", "🥈", "🥉"]
                level_icons = ["⭐", "🌟", "💫"]
                ranking_text = ""
                
                for idx, player in enumerate(ranking, 1):
                    medal = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
                    name = player["name"][:18]
                    level = player["level"]
                    pal_count = player["pal_count"]
                    playtime = self._fmt_playtime(player.get("playtime_sec", 0))
                    
                    # Icon level theo cấp độ
                    if level >= 50:
                        level_icon = level_icons[2]
                    elif level >= 30:
                        level_icon = level_icons[1]
                    else:
                        level_icon = level_icons[0]
                    
                    ranking_text += f"{medal} **{name}**\n"
                    ranking_text += f"   {level_icon} Cấp: `{level:3d}` | 🎣 Pal: `{pal_count:4d}` | ⏱ `{playtime}`\n\n"
                    if len(ranking_text) > 1800:  # Discord limit
                        break

                embed.add_field(
                    name="🏅 TOP NGƯỜI CHƠI HÀNG ĐẦU",
                    value=ranking_text or "Chưa có dữ liệu",
                    inline=False
                )
                
                # Thêm thống kê tổng quan
                if ranking:
                    avg_level = sum(p["level"] for p in ranking) / len(ranking)
                    avg_pals = sum(p["pal_count"] for p in ranking) / len(ranking)
                    max_level = max(p["level"] for p in ranking)
                    max_pals = max(p["pal_count"] for p in ranking)
                    
                    stats_text = (
                        f"📈 **Cấp độ trung bình:** `{avg_level:.1f}`\n"
                        f"🎣 **Pal trung bình:** `{avg_pals:.1f}`\n"
                        f"🔥 **Cấp cao nhất:** `{max_level}`\n"
                        f"💎 **Nhiều Pal nhất:** `{max_pals}`"
                    )
                    
                    embed.add_field(
                        name="📊 THỐNG KÊ TỔNG QUAN",
                        value=stats_text,
                        inline=False
                    )
                
                embed.set_footer(text=f"Palworld Server Ranking • {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ Lỗi: {str(e)}")

        @bot.command(name='stats', aliases=['stat', 'player', 'thongke'])
        async def cmd_stats(ctx, *, player_name: str = None):
            """Xem thống kê của người chơi.
            Usage: !stats [tên người chơi]
            """
            try:
                if not player_name:
                    await ctx.send("❌ Vui lòng nhập tên người chơi: `!stats [tên]`\n"
                                 "💡 Ví dụ: `!stats MityTin`")
                    return

                # Tìm player trong stats (tìm chính xác hoặc gần đúng)
                found = None
                exact_match = None
                partial_matches = []
                
                for steamid, stats in self.player_stats.items():
                    name = stats.get("name", "").lower()
                    search_name = player_name.lower()
                    if name == search_name:
                        exact_match = {"steamid": steamid, **stats}
                    elif search_name in name:
                        partial_matches.append({"steamid": steamid, **stats})
                
                found = exact_match or (partial_matches[0] if partial_matches else None)

                if not found:
                    await ctx.send(f"❌ Không tìm thấy người chơi: `{player_name}`\n"
                                 f"💡 Thử tìm kiếm: `!search {player_name}`")
                    return

                # Tính ranking
                ranking = self._get_ranking(1000)  # Lấy tất cả để tìm vị trí
                rank_pos = None
                for idx, p in enumerate(ranking, 1):
                    if p.get("steamid") == found.get("steamid"):
                        rank_pos = idx
                        break

                embed = _discord.Embed(
                    title=f"📊 Thống kê: {found['name']}",
                    description=f"🏆 **Vị trí xếp hạng:** #{rank_pos if rank_pos else 'N/A'}",
                    color=0x00aaff
                )
                embed.add_field(name="⭐ Cấp độ", value=f"`{found.get('level', 0)}`", inline=True)
                embed.add_field(name="🎣 Pal đã bắt", value=f"`{found.get('pal_count', 0)}`", inline=True)
                embed.add_field(
                    name="⏱ Thời lượng chơi",
                    value=f"`{self._fmt_playtime(self._player_total_playtime_sec(found.get('steamid', '')) )}`",
                    inline=True
                )
                
                # Thêm thông tin SteamID (ẩn một phần)
                steamid = found.get('steamid', '')
                if steamid:
                    steamid_display = steamid[:10] + "..." if len(steamid) > 10 else steamid
                    embed.add_field(name="🆔 SteamID", value=f"`{steamid_display}`", inline=True)
                
                last_update = found.get('last_update', 0)
                if last_update:
                    last_update_str = datetime.datetime.fromtimestamp(last_update).strftime('%d/%m/%Y %H:%M:%S')
                    embed.add_field(name="🕐 Cập nhật lần cuối", value=last_update_str, inline=False)
                
                embed.set_footer(text="Palworld Server Bot")
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ Lỗi: {str(e)}")

        @bot.command(name='server', aliases=['info', 'serverinfo', 'serverstatus'])
        async def cmd_server(ctx):
            """Xem thông tin server.
            Usage: !server
            """
            try:
                res = requests.get(f"{API_URL}/info", auth=AUTH, timeout=5)
                if res.status_code != 200:
                    await ctx.send("❌ Không thể lấy thông tin server.")
                    return

                info = res.json()
                players_res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                players = []
                if players_res.status_code == 200:
                    players = players_res.json().get("players", [])

                # Tính thống kê người chơi
                total_stats_players = len([s for s in self.player_stats.values() 
                                         if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])

                embed = _discord.Embed(
                    title="🖥️ THÔNG TIN SERVER PALWORLD",
                    description="📊 Thông tin chi tiết về server",
                    color=0x00aaff
                )
                embed.add_field(name="👥 Người chơi online", value=f"`{len(players)}/{self._max_players}`", inline=True)
                embed.add_field(name="🌐 Version", value=f"`{info.get('version', 'N/A')}`", inline=True)
                embed.add_field(name="📊 Uptime", value=f"`{info.get('uptime', 'N/A')}`", inline=True)
                embed.add_field(name="📈 Tổng người chơi có dữ liệu", value=f"`{total_stats_players}`", inline=True)
                
                if players:
                    player_list = ", ".join([p.get("name", "Unknown")[:15] for p in players[:10]])
                    if len(players) > 10:
                        player_list += f" ... và {len(players) - 10} người khác"
                    embed.add_field(name="👤 Người chơi đang online", value=player_list or "Không có", inline=False)
                else:
                    embed.add_field(name="👤 Người chơi đang online", value="Không có người chơi nào", inline=False)

                embed.set_footer(text=f"Cập nhật: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ Lỗi: {str(e)}")

        @bot.command(name='online', aliases=['players', 'danhsach'])
        async def cmd_online(ctx):
            """Xem danh sách người chơi đang online.
            Usage: !online
            """
            try:
                players_res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if players_res.status_code != 200:
                    await ctx.send("❌ Không thể lấy danh sách người chơi.")
                    return

                players = players_res.json().get("players", [])
                
                if not players:
                    await ctx.send("👤 **Không có người chơi nào đang online.**")
                    return

                embed = _discord.Embed(
                    title=f"👥 NGƯỜI CHƠI ĐANG ONLINE ({len(players)})",
                    color=0x00ff88
                )

                # Chia thành các field nếu quá nhiều
                player_text = ""
                for idx, p in enumerate(players, 1):
                    name = p.get("name", "Unknown")
                    playerid = p.get("playerId", "")[:8] + "..." if p.get("playerId") else "N/A"
                    player_text += f"**{idx}.** {name}\n"
                    if len(player_text) > 900:  # Giới hạn độ dài
                        player_text += f"... và {len(players) - idx} người khác"
                        break

                embed.add_field(name="📋 Danh sách", value=player_text or "Không có", inline=False)
                embed.set_footer(text=f"Tổng: {len(players)}/{self._max_players} người chơi")
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ Lỗi: {str(e)}")

        @bot.command(name='search', aliases=['tim', 'find'])
        async def cmd_search(ctx, *, query: str = None):
            """Tìm kiếm người chơi theo tên.
            Usage: !search [từ khóa]
            """
            try:
                if not query:
                    await ctx.send("❌ Vui lòng nhập từ khóa tìm kiếm: `!search [tên]`")
                    return

                query_lower = query.lower()
                matches = []
                
                for steamid, stats in self.player_stats.items():
                    name = stats.get("name", "").lower()
                    if query_lower in name:
                        matches.append({"steamid": steamid, **stats})
                        if len(matches) >= 10:  # Giới hạn 10 kết quả
                            break

                if not matches:
                    await ctx.send(f"❌ Không tìm thấy người chơi nào với từ khóa: `{query}`")
                    return

                embed = _discord.Embed(
                    title=f"🔍 KẾT QUẢ TÌM KIẾM: '{query}'",
                    description=f"Tìm thấy **{len(matches)}** kết quả:",
                    color=0x00aaff
                )

                result_text = ""
                for idx, match in enumerate(matches, 1):
                    name = match.get("name", "Unknown")
                    level = match.get("level", 0)
                    pal_count = match.get("pal_count", 0)
                    result_text += f"**{idx}.** {name} - ⭐{level} | 🎣{pal_count}\n"

                embed.add_field(name="📋 Kết quả", value=result_text, inline=False)
                embed.set_footer(text="Sử dụng !stats [tên] để xem chi tiết")
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ Lỗi: {str(e)}")

        @bot.command(name='help', aliases=['h', 'commands', 'trogiup'])
        async def cmd_help(ctx):
            """Hiển thị danh sách commands.
            Usage: !help
            """
            embed = _discord.Embed(
                title="🤖 DANH SÁCH COMMANDS",
                description="Các lệnh có sẵn cho bot Palworld Server:",
                color=0x00ff88
            )
            embed.add_field(
                name="📊 Xếp hạng",
                value="`!ranking [số]` - Xem bảng xếp hạng (mặc định top 10, tối đa 20)\n"
                      "`!rank`, `!top`, `!xephang` - Tương tự",
                inline=False
            )
            embed.add_field(
                name="📈 Thống kê",
                value="`!stats [tên]` - Xem thống kê người chơi\n"
                      "`!stat`, `!player`, `!thongke` - Tương tự",
                inline=False
            )
            embed.add_field(
                name="🔍 Tìm kiếm",
                value="`!search [từ khóa]` - Tìm kiếm người chơi\n"
                      "`!tim`, `!find` - Tương tự",
                inline=False
            )
            embed.add_field(
                name="🖥️ Server",
                value="`!server` - Xem thông tin server\n"
                      "`!info`, `!serverinfo`, `!serverstatus` - Tương tự",
                inline=False
            )
            embed.add_field(
                name="👥 Người chơi",
                value="`!online` - Xem danh sách người chơi đang online\n"
                      "`!players`, `!danhsach` - Tương tự",
                inline=False
            )
            embed.add_field(
                name="🔄 Cập nhật",
                value="`!refresh` - Cập nhật ngay server status + ranking board\n"
                      "`!update`, `!capnhat`, `!r` - Tương tự",
                inline=False
            )
            embed.add_field(
                name="❓ Trợ giúp",
                value="`!help` - Hiển thị danh sách commands này",
                inline=False
            )
            embed.set_footer(text="Cờ Hó Bot  •  Auto-update mỗi 3 phút  •  !refresh để cập nhật ngay")
            
            await ctx.send(embed=embed)

        # ── Slash Commands (hiện đại hơn) ───────────────────────────
        @bot.tree.command(name="ranking", description="Xem bảng xếp hạng người chơi")
        async def slash_ranking(interaction: _discord.Interaction, top: int = 10):
            """Slash command: Xem bảng xếp hạng."""
            await interaction.response.defer()
            try:
                ranking = self._get_ranking(min(top, 20))
                if not ranking:
                    await interaction.followup.send("📊 Chưa có dữ liệu xếp hạng.")
                    return

                total_players = len([s for s in self.player_stats.values() 
                                   if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])

                embed = _discord.Embed(
                    title="🏆 BẢNG XẾP HẠNG NGƯỜI CHƠI",
                    description=f"📊 **Top {len(ranking)} người chơi**\n👥 Tổng: **{total_players}**",
                    color=0x00ff88
                )

                medals = ["🥇", "🥈", "🥉"]
                ranking_text = ""
                for idx, player in enumerate(ranking[:10], 1):
                    medal = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
                    name = player["name"][:18]
                    level = player["level"]
                    pal_count = player["pal_count"]
                    ranking_text += f"{medal} **{name}** - ⭐{level} | 🎣{pal_count}\n"

                embed.add_field(name="🏅 TOP 10", value=ranking_text, inline=False)
                embed.set_footer(text=f"Cập nhật: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi: {str(e)}")

        @bot.tree.command(name="stats", description="Xem thống kê người chơi")
        async def slash_stats(interaction: _discord.Interaction, player_name: str):
            """Slash command: Xem thống kê người chơi."""
            await interaction.response.defer()
            try:
                found = None
                for steamid, stats in self.player_stats.items():
                    if player_name.lower() in stats.get("name", "").lower():
                        found = {"steamid": steamid, **stats}
                        break

                if not found:
                    await interaction.followup.send(f"❌ Không tìm thấy: `{player_name}`")
                    return

                embed = _discord.Embed(title=f"📊 {found['name']}", color=0x00aaff)
                embed.add_field(name="⭐ Cấp độ", value=f"`{found.get('level', 0)}`", inline=True)
                embed.add_field(name="🎣 Pal đã bắt", value=f"`{found.get('pal_count', 0)}`", inline=True)
                await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi: {str(e)}")

        @bot.tree.command(name="server", description="Xem thông tin server")
        async def slash_server(interaction: _discord.Interaction):
            """Slash command: Xem thông tin server."""
            await interaction.response.defer()
            try:
                res = requests.get(f"{API_URL}/info", auth=AUTH, timeout=5)
                players_res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                players = players_res.json().get("players", []) if players_res.status_code == 200 else []

                embed = _discord.Embed(title="🖥️ THÔNG TIN SERVER", color=0x00aaff)
                embed.add_field(name="👥 Online", value=f"`{len(players)}/{self._max_players}`", inline=True)
                embed.add_field(name="🌐 Version", value=f"`{res.json().get('version', 'N/A') if res.status_code == 200 else 'N/A'}`", inline=True)
                await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi: {str(e)}")

        @bot.tree.command(name="createserver", description="(Admin) Thêm/cập nhật server profile để bot quản lý")
        @_discord.app_commands.describe(
            name="Tên server (ví dụ: Manager ServerPal)",
            ip_public="IP Public (máy chủ public)",
            game_port="Cổng Game (vd 8211)",
            rcon_port="Cổng RCON (vd 25575)",
            restapi_port="Cổng REST API (vd 8212)",
            paldefender_port="Cổng PalDefender REST (vd 17993)",
            admin_password="AdminPassword dùng chung cho RCON/REST"
        )
        async def slash_create_server(
            interaction: _discord.Interaction,
            name: str,
            ip_public: str,
            game_port: int,
            rcon_port: int,
            restapi_port: int,
            paldefender_port: int,
            admin_password: str,
        ):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("❌ Chỉ admin Discord mới được setup server.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                s_name = (name or "").strip()
                if not s_name:
                    await interaction.followup.send("❌ Tên server không hợp lệ.", ephemeral=True)
                    return
                if not ip_public.strip():
                    await interaction.followup.send("❌ IP public không được để trống.", ephemeral=True)
                    return
                for p in (game_port, rcon_port, restapi_port, paldefender_port):
                    if p <= 0 or p > 65535:
                        await interaction.followup.send(f"❌ Port không hợp lệ: {p}", ephemeral=True)
                        return

                cfg = _read_manager_cfg() or {}
                servers = cfg.get("DISCORD_SERVER_PROFILES", {})
                if not isinstance(servers, dict):
                    servers = {}
                servers[s_name] = {
                    "name": s_name,
                    "ip_public": ip_public.strip(),
                    "game_port": int(game_port),
                    "rcon_port": int(rcon_port),
                    "restapi_port": int(restapi_port),
                    "paldefender_port": int(paldefender_port),
                    "admin_password": admin_password,
                    "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                cfg["DISCORD_SERVER_PROFILES"] = servers
                cfg["DISCORD_SERVER_ACTIVE"] = s_name
                if _save_manager_cfg(cfg):
                    self._enqueue_console(f"✅ Bot2 setup server profile: {s_name} ({ip_public}:{game_port})")
                    await interaction.followup.send(
                        f"✅ Đã lưu server `{s_name}`\n"
                        f"• IP Public: `{ip_public}`\n"
                        f"• Game: `{game_port}` | RCON: `{rcon_port}` | REST: `{restapi_port}` | PD: `{paldefender_port}`\n"
                        f"• Trạng thái: đặt làm server active",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send("❌ Không lưu được server profile.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi /createserver: {e}", ephemeral=True)

        @bot.tree.command(name="delserver", description="(Admin) Xóa server profile theo tên")
        @_discord.app_commands.describe(name="Tên server (ví dụ: Manager ServerPal)")
        async def slash_del_server(interaction: _discord.Interaction, name: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("❌ Chỉ admin Discord mới được xóa server.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                s_name = (name or "").strip()
                cfg = _read_manager_cfg() or {}
                servers = cfg.get("DISCORD_SERVER_PROFILES", {})
                if not isinstance(servers, dict) or s_name not in servers:
                    await interaction.followup.send(f"ℹ️ Không tìm thấy server `{s_name}`.", ephemeral=True)
                    return
                servers.pop(s_name, None)
                cfg["DISCORD_SERVER_PROFILES"] = servers
                if cfg.get("DISCORD_SERVER_ACTIVE") == s_name:
                    cfg["DISCORD_SERVER_ACTIVE"] = next(iter(servers.keys()), "")
                if _save_manager_cfg(cfg):
                    self._enqueue_console(f"🗑️ Bot2 xóa server profile: {s_name}")
                    await interaction.followup.send(f"✅ Đã xóa server `{s_name}`.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Không lưu được sau khi xóa server.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi /delserver: {e}", ephemeral=True)

        @bot.tree.command(name="listservers", description="(Admin) Xem danh sách server profile đã lưu")
        async def slash_list_servers(interaction: _discord.Interaction):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("❌ Chỉ admin Discord mới được xem danh sách setup.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                cfg = _read_manager_cfg() or {}
                servers = cfg.get("DISCORD_SERVER_PROFILES", {})
                active = str(cfg.get("DISCORD_SERVER_ACTIVE", "") or "")
                if not isinstance(servers, dict) or not servers:
                    await interaction.followup.send("ℹ️ Chưa có server profile nào. Dùng `/createserver` để thêm mới.", ephemeral=True)
                    return
                lines = []
                for s_name, s in servers.items():
                    marker = "⭐" if s_name == active else "•"
                    lines.append(
                        f"{marker} **{s_name}** — `{s.get('ip_public','?')}:{s.get('game_port','?')}` "
                        f"(RCON `{s.get('rcon_port','?')}`, REST `{s.get('restapi_port','?')}`, PD `{s.get('paldefender_port','?')}`)"
                    )
                await interaction.followup.send(
                    "Danh sách server profile (⭐ = đang active):\n" + "\n".join(lines[:20]),
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi /listservers: {e}", ephemeral=True)

        # [Deprecated] Ẩn lệnh đơn lẻ — đã thay bằng /query setchannel
        if False:
            pass

        if False:
            pass

        if False:
            pass

        if False:
            pass

        if False:
            pass

        if False:
            pass

        # ── Query group commands: /query setchannel ... ──────────────────────
        async def _server_name_autocomplete(interaction: _discord.Interaction, current: str):
            current_l = (current or "").lower().strip()
            names = list(_read_server_profiles().keys())
            out = []
            for n in names:
                if current_l and current_l not in n.lower():
                    continue
                out.append(_discord.app_commands.Choice(name=n[:100], value=n))
                if len(out) >= 25:
                    break
            return out

        query_group = _discord.app_commands.Group(
            name="query",
            description="Quản lý kênh hiển thị card (START/STATUS & XẾP HẠNG) cho từng server"
        )

        async def _ensure_status_card_in_channel(target_channel):
            """Đảm bảo có status card trong kênh đích; chỉ tạo khi admin gọi lệnh setup."""
            # 1) Nếu đang có message id hợp lệ thì ưu tiên edit.
            if self._bot2_status_msg_id:
                try:
                    msg_old = await target_channel.fetch_message(self._bot2_status_msg_id)
                    await msg_old.edit(embed=await _build_server_embed(), view=ServerView())
                    return msg_old.id
                except Exception:
                    pass
            # 2) Không có/không hợp lệ -> tạo mới 1 lần theo lệnh admin.
            msg_new = await target_channel.send(embed=await _build_server_embed(), view=ServerView())
            self._bot2_status_msg_id = msg_new.id
            self._save_bot2_msg_ids()
            return msg_new.id

        async def _ensure_ranking_card_in_channel(target_channel):
            """Đảm bảo có ranking card trong kênh đích; chỉ tạo khi admin gọi lệnh setup."""
            if self._bot2_ranking_msg_id:
                try:
                    msg_old = await target_channel.fetch_message(self._bot2_ranking_msg_id)
                    await msg_old.edit(embed=_build_ranking_embed(), view=RankingView())
                    return msg_old.id
                except Exception:
                    pass
            msg_new = await target_channel.send(embed=_build_ranking_embed(), view=RankingView())
            self._bot2_ranking_msg_id = msg_new.id
            self._save_bot2_msg_ids()
            return msg_new.id

        @query_group.command(name="setchannel", description="(Admin) Gán kênh START/STATUS cho 1 server")
        @_discord.app_commands.describe(channel="Kênh nhận card status", server="Tên server profile")
        @_discord.app_commands.autocomplete(server=_server_name_autocomplete)
        async def query_setchannel(interaction: _discord.Interaction, channel: _discord.TextChannel, server: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("❌ Chỉ admin được phép cấu hình.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            cfg = _read_manager_cfg() or {}
            servers = cfg.get("DISCORD_SERVER_PROFILES", {})
            if not isinstance(servers, dict) or server not in servers:
                await interaction.followup.send(f"❌ Không tìm thấy server `{server}`.", ephemeral=True)
                return
            servers[server]["status_channel_id"] = str(channel.id)
            cfg["DISCORD_SERVER_PROFILES"] = servers
            if _save_manager_cfg(cfg):
                try:
                    msg_id = await _ensure_status_card_in_channel(channel)
                    await interaction.followup.send(
                        f"✅ Đã gán kênh START/STATUS <#{channel.id}> cho server `{server}`.\n"
                        f"🧩 Status card: `msg_id={msg_id}` (từ giờ chỉ edit, không tự gửi mới).",
                        ephemeral=True
                    )
                except Exception as e:
                    await interaction.followup.send(
                        f"⚠️ Đã lưu mapping nhưng chưa tạo/đồng bộ status card: {e}",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send("❌ Không lưu được cấu hình.", ephemeral=True)

        @query_group.command(name="removechannel", description="(Admin) Hủy gán kênh START/STATUS của 1 server")
        @_discord.app_commands.describe(server="Tên server profile cần hủy")
        @_discord.app_commands.autocomplete(server=_server_name_autocomplete)
        async def query_removechannel(interaction: _discord.Interaction, server: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("❌ Chỉ admin được phép cấu hình.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            cfg = _read_manager_cfg() or {}
            servers = cfg.get("DISCORD_SERVER_PROFILES", {})
            if not isinstance(servers, dict) or server not in servers:
                await interaction.followup.send(f"❌ Không tìm thấy server `{server}`.", ephemeral=True)
                return
            servers[server].pop("status_channel_id", None)
            cfg["DISCORD_SERVER_PROFILES"] = servers
            if _save_manager_cfg(cfg):
                await interaction.followup.send(f"✅ Đã hủy gán kênh START/STATUS của `{server}`.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Không lưu được cấu hình.", ephemeral=True)

        @query_group.command(name="setrankingchannel", description="(Admin) Gán kênh BẢNG XẾP HẠNG cho 1 server")
        @_discord.app_commands.describe(channel="Kênh nhận card xếp hạng", server="Tên server profile")
        @_discord.app_commands.autocomplete(server=_server_name_autocomplete)
        async def query_setrankingchannel(interaction: _discord.Interaction, channel: _discord.TextChannel, server: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("❌ Chỉ admin được phép cấu hình.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            cfg = _read_manager_cfg() or {}
            servers = cfg.get("DISCORD_SERVER_PROFILES", {})
            if not isinstance(servers, dict) or server not in servers:
                await interaction.followup.send(f"❌ Không tìm thấy server `{server}`.", ephemeral=True)
                return
            servers[server]["ranking_channel_id"] = str(channel.id)
            cfg["DISCORD_SERVER_PROFILES"] = servers
            if _save_manager_cfg(cfg):
                try:
                    msg_id = await _ensure_ranking_card_in_channel(channel)
                    await interaction.followup.send(
                        f"✅ Đã gán kênh BẢNG XẾP HẠNG <#{channel.id}> cho server `{server}`.\n"
                        f"🏆 Ranking card: `msg_id={msg_id}` (từ giờ chỉ edit, không tự gửi mới).",
                        ephemeral=True
                    )
                except Exception as e:
                    await interaction.followup.send(
                        f"⚠️ Đã lưu mapping nhưng chưa tạo/đồng bộ ranking card: {e}",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send("❌ Không lưu được cấu hình.", ephemeral=True)

        @query_group.command(name="removerankingchannel", description="(Admin) Hủy gán kênh BẢNG XẾP HẠNG của 1 server")
        @_discord.app_commands.describe(server="Tên server profile cần hủy")
        @_discord.app_commands.autocomplete(server=_server_name_autocomplete)
        async def query_removerankingchannel(interaction: _discord.Interaction, server: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("❌ Chỉ admin được phép cấu hình.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            cfg = _read_manager_cfg() or {}
            servers = cfg.get("DISCORD_SERVER_PROFILES", {})
            if not isinstance(servers, dict) or server not in servers:
                await interaction.followup.send(f"❌ Không tìm thấy server `{server}`.", ephemeral=True)
                return
            servers[server].pop("ranking_channel_id", None)
            cfg["DISCORD_SERVER_PROFILES"] = servers
            if _save_manager_cfg(cfg):
                await interaction.followup.send(f"✅ Đã hủy gán kênh BẢNG XẾP HẠNG của `{server}`.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Không lưu được cấu hình.", ephemeral=True)

        bot.tree.add_command(query_group)

        @bot.tree.command(name="synccommands", description="(Admin) Đồng bộ ngay slash commands trong guild hiện tại")
        async def slash_synccommands(interaction: _discord.Interaction):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("❌ Chỉ admin được phép sync lệnh.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                guild = interaction.guild
                if guild is None:
                    await interaction.followup.send("❌ Lệnh này chỉ dùng trong server Discord.", ephemeral=True)
                    return
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                await interaction.followup.send(f"✅ Đã sync `{len(synced)}` lệnh cho guild `{guild.name}`.\n"
                                                "Gợi ý: dùng `/query setchannel` và `/query setrankingchannel` để gắn card, "
                                                "sau đó bot chỉ edit tin hiện có (không spam).",
                                                ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Sync lệnh thất bại: {e}", ephemeral=True)

        async def _unban_target_autocomplete(
            interaction: _discord.Interaction,
            current: str
        ):
            try:
                current_l = (current or "").lower().strip()
                rows = _app._read_antibug_banlist_entries()
                out = []
                for r in rows:
                    label = r.get("label", "")
                    sid = r.get("steamid", "")
                    if current_l and current_l not in label.lower() and current_l not in sid.lower():
                        continue
                    out.append(_discord.app_commands.Choice(name=label[:100], value=sid))
                    if len(out) >= 25:
                        break
                return out
            except Exception:
                return []

        @bot.tree.command(name="unban", description="Unban nhanh từ danh sách ban AntiBug")
        @_discord.app_commands.describe(target="Chọn người cần unban (Tên - steamid)")
        @_discord.app_commands.autocomplete(target=_unban_target_autocomplete)
        async def slash_unban(interaction: _discord.Interaction, target: str):
            await interaction.response.defer(ephemeral=True)
            ok, detail = _app._unban_steamid_common(target, source="DISCORD /unban")
            if ok:
                await interaction.followup.send(f"✅ {detail}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {detail}", ephemeral=True)

        # ── Chat bridge (nếu có channel ID) ────────────────────────
        if DISCORD_BOT2_CHANNEL_ID:
            @bot.event
            async def on_message(message):
                # Xử lý commands trước
                await bot.process_commands(message)
                
                # Chat bridge (chỉ trong channel đã cấu hình)
                if str(message.channel.id) == str(DISCORD_BOT2_CHANNEL_ID):
                    if message.author.bot or message.webhook_id:
                        return
                    if message.content.startswith('!'):
                        return  # Bỏ qua commands
                    
                    content = message.content.strip()
                    if content:
                        username = message.author.display_name or message.author.name
                        broadcast_text = f"[Discord] {username}: {content}"
                        self.send_ingame_broadcast(broadcast_text)
                        self._enqueue_console(f"💬 [Discord Bot 2] {username}: {content}")

        # ── Chạy bot với auto-reconnect ───────────────────────────
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._discord_bot2_loop = loop

        while True:
            self._discord_bot2_client = bot
            self._discord_bot2_status = "⏳ Đang kết nối Discord Gateway..."
            try:
                loop.run_until_complete(bot.start(DISCORD_BOT2_TOKEN))
            except _discord.errors.LoginFailure:
                self._discord_bot2_ok = False
                self._discord_bot2_status = "❌ Bot 2 Token không hợp lệ"
                self._enqueue_console("❌ Discord Bot 2: Token không hợp lệ")
                return
            except _discord.errors.PrivilegedIntentsRequired:
                self._discord_bot2_ok = False
                self._discord_bot2_status = "❌ Cần bật Message Content Intent"
                self._enqueue_console("❌ Discord Bot 2: Cần bật Message Content Intent")
                return
            except KeyboardInterrupt:
                return
            except Exception as e:
                self._discord_bot2_ok = False
                self._discord_bot2_status = f"⚠️ Lỗi kết nối — thử lại sau 15s"
                self._enqueue_console(f"⚠️ Discord Bot 2 lỗi: {e}")
            finally:
                try:
                    if not bot.is_closed():
                        loop.run_until_complete(bot.close())
                except Exception:
                    pass
            time.sleep(15)

    # ── Reset sequence ────────────────────────
    def reset_sequence(self):
        if self.is_processing:
            return
        self.is_processing = True
        self.is_notified_online = False
        try:
            self._enqueue_console("🚀 Khởi động Reset 30s (Thông báo đỏ)...")
            self.send_discord_alert("⚠️ **[Manager ServerPal]** Máy chủ đang lưu dữ liệu và sẽ Restart sau **30 giây**!")

            self.send_ingame_broadcast("SERVER RESET TRONG 30S - DANG LUU DU LIEU!")
            threading.Thread(
                target=lambda: requests.post(f"{API_URL}/save", auth=AUTH, timeout=25),
                daemon=True
            ).start()
            self._enqueue_console("💾 Đang Save ngầm...")
            time.sleep(10)

            self.send_ingame_broadcast("SERVER RESET TRONG 20S - VUI LONG THOAT NGAY!")
            time.sleep(10)

            self.send_ingame_broadcast("SERVER RESET TRONG 10S - HEN GAP LAI!")
            time.sleep(10)

            self._enqueue_console("🔌 Đang đóng Server...")
            try:
                requests.post(f"{API_URL}/shutdown",
                              json={"waittime": 0, "message": "Restarting"},
                              auth=AUTH, timeout=5)
            except Exception:
                pass

            time.sleep(2)
            self._stop_server_processes(force=True, source="Auto reset")
            self._enqueue_console("✅ Đã giải phóng RAM. Chờ khởi động lại...")
            time.sleep(3)
            self._start_server_safe(source="Auto reset")
            self.is_notified_online = False

        except Exception as e:
            self._enqueue_console(f"❌ Lỗi reset: {e}")
        finally:
            time.sleep(10)
            self.is_processing = False

    def _stop_sequence_discord(self, initiated_by: str = "Discord") -> None:
        """Dừng server theo yêu cầu từ Discord: thông báo 10s, 5s, save, rồi tắt."""
        try:
            self._enqueue_console(f"🛑 {initiated_by}: Khởi động quy trình STOP có cảnh báo.")
            # Cố gắng save qua REST API trước
            saved = False
            try:
                requests.post(f"{API_URL}/save", auth=AUTH, timeout=25)
                saved = True
            except Exception:
                pass
            if not saved:
                try:
                    rcon_exec("Save")
                    saved = True
                except Exception:
                    pass
            if saved:
                self._enqueue_console("💾 Đã gửi lệnh Save (REST/RCON).")

            # Thông báo đếm ngược
            self.send_ingame_broadcast("SERVER SẼ TẮT SAU 10 GIÂY - ĐANG LƯU DỮ LIỆU!")
            time.sleep(5)
            self.send_ingame_broadcast("SERVER SẼ TẮT SAU 5 GIÂY - TẠM BIỆT!")
            time.sleep(5)
            self.send_ingame_broadcast("SERVER ĐANG TẮT - HẸN GẶP LẠI!")

            # Gửi shutdown qua REST (nếu có), sau đó kill để chắc chắn
            try:
                requests.post(
                    f"{API_URL}/shutdown",
                    json={"waittime": 0, "message": "Server shutting down"},
                    auth=AUTH, timeout=5
                )
            except Exception:
                pass
            time.sleep(2)
            self._stop_server_processes(force=True, source=f"{initiated_by} Stop")
            self._enqueue_console("✅ STOP: Server đã tắt.")
            self.root.after(0, self._update_ctrl_btn_state)
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi STOP (Discord): {e}")

    def _build_server_launch_cmd(self) -> list:
        """Build command chạy PalServer.exe theo config hiện tại, tránh hardcode cứng."""
        game_port = "8211"
        rest_port = "8212"
        try:
            ini = self._settings_parse_ini(PAL_SETTINGS_INI)
            gp = str(ini.get("PublicPort", "")).strip()
            rp = str(ini.get("RESTAPIPort", "")).strip()
            if gp.isdigit():
                game_port = gp
            if rp.isdigit():
                rest_port = rp
        except Exception:
            pass
        return [SERVER_EXE, f"-port={game_port}", f"-RESTAPIPort={rest_port}", "-log"]

    def _resolve_active_game_endpoint(self) -> tuple[str, int] | tuple[None, None]:
        """Lấy IP/Port game từ server profile active; fallback sang PUBLIC_*."""
        try:
            cfg = _read_manager_cfg() or {}
            profiles = cfg.get("DISCORD_SERVER_PROFILES", {})
            active = str(cfg.get("DISCORD_SERVER_ACTIVE", "") or "").strip()

            ip = ""
            port_raw = ""
            if isinstance(profiles, dict) and active and isinstance(profiles.get(active), dict):
                prof = profiles.get(active, {})
                ip = str(prof.get("ip_public", "") or "").strip()
                port_raw = str(prof.get("game_port", "") or "").strip()

            if not ip:
                ip = str(cfg.get("PUBLIC_IP", "") or "").strip()
            if not port_raw:
                port_raw = str(cfg.get("PUBLIC_PORT", "") or "").strip()

            if not ip or not port_raw.isdigit():
                return None, None
            return ip, int(port_raw)
        except Exception:
            return None, None

    def _ping_host_once(self, host: str, timeout_ms: int = 1200) -> bool:
        """Ping 1 gói để biết host có reachable ở mức mạng hay không."""
        try:
            cp = subprocess.run(
                ["ping", "-n", "1", "-w", str(int(timeout_ms)), host],
                capture_output=True,
                text=True,
                timeout=max(2, int(timeout_ms / 1000) + 2)
            )
            return cp.returncode == 0
        except Exception:
            return False

    def _tcp_port_open(self, host: str, port: int, timeout_sec: float = 2.5) -> bool:
        """Kiểm tra cổng game có nhận kết nối TCP hay chưa."""
        try:
            with socket.create_connection((host, int(port)), timeout=float(timeout_sec)):
                return True
        except Exception:
            return False

    def _has_online_players(self) -> bool:
        """Nếu đã có người vào game thì coi như server usable, không cần tiếp tục startup check."""
        try:
            res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=4)
            if res.status_code != 200:
                return False
            data = res.json() if isinstance(res.json(), dict) else {}
            players = data.get("players", [])
            return isinstance(players, list) and len(players) > 0
        except Exception:
            return False

    def _expected_startup_port(self) -> int:
        """Lấy cổng game kỳ vọng để khớp dòng log startup."""
        try:
            _, p = self._resolve_active_game_endpoint()
            if isinstance(p, int) and p > 0:
                return p
        except Exception:
            pass
        try:
            ini = self._settings_parse_ini(PAL_SETTINGS_INI)
            gp = str(ini.get("PublicPort", "")).strip()
            if gp.isdigit():
                return int(gp)
        except Exception:
            pass
        return 8211

    def _startup_running_log_seen(self, port: int) -> bool:
        """Tìm dấu hiệu server đã ready trong log PalDefender/PalServer."""
        needle = f"Running Palworld dedicated server on :{int(port)}".lower()
        try:
            latest = self._find_latest_paldef_log()
            if latest and os.path.isfile(latest):
                with open(latest, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    sz = f.tell()
                    f.seek(max(0, sz - 64 * 1024), os.SEEK_SET)
                    chunk = f.read().decode("utf-8", errors="replace").lower()
                if needle in chunk:
                    return True
        except Exception:
            pass
        try:
            if os.path.isfile(SERVER_LOG_FILE):
                with open(SERVER_LOG_FILE, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    sz = f.tell()
                    f.seek(max(0, sz - 64 * 1024), os.SEEK_SET)
                    chunk = f.read().decode("utf-8", errors="replace").lower()
                if needle in chunk:
                    return True
        except Exception:
            pass
        return False

    def _schedule_startup_log_ready_check(self, source: str = "") -> None:
        """Theo dõi log startup song song: thấy dòng ready trong 20s => OK; quá 25s => treo."""
        if not STARTUP_LOG_READY_CHECK_ENABLED:
            return
        with self._startup_log_check_lock:
            self._startup_log_check_seq += 1
            seq = self._startup_log_check_seq
            # Reset retry counter cho một phiên start mới
            self._startup_log_retry_count = 0
        threading.Thread(
            target=self._startup_log_ready_worker,
            args=(seq, source or "safe-start"),
            daemon=True
        ).start()

    def _startup_log_ready_worker(self, seq: int, source: str) -> None:
        if not STARTUP_LOG_READY_CHECK_ENABLED:
            return
        port = self._expected_startup_port()
        t0 = time.time()
        ok_deadline = t0 + 20.0
        fail_deadline = t0 + 25.0
        seen_after_20 = False

        while time.time() < fail_deadline:
            with self._startup_log_check_lock:
                if seq != self._startup_log_check_seq:
                    return
            if not self._is_server_running():
                return
            if self._startup_running_log_seen(port):
                elapsed = int(time.time() - t0)
                self._enqueue_console(
                    f"✅ Startup log-check PASS ({source}): thấy 'Running Palworld dedicated server on :{port}' sau ~{elapsed}s."
                )
                return
            if time.time() >= ok_deadline and not seen_after_20:
                seen_after_20 = True
                self._enqueue_console(
                    f"⏳ Startup log-check: sau 20s vẫn chưa thấy dòng ready :{port}, tiếp tục chờ đến 25s..."
                )
            time.sleep(1.0)

        self._enqueue_console(
            f"❌ Startup log-check FAIL ({source}): quá 25s chưa thấy 'Running Palworld dedicated server on :{port}' -> nghi treo."
        )
        # Tự khởi động lại ngay 1 lần để cứu treo (chỉ 1 retry, tránh vòng lặp vô hạn)
        try:
            with self._startup_log_check_lock:
                can_retry = getattr(self, "_startup_log_retry_count", 0) < 1
                if can_retry:
                    self._startup_log_retry_count = getattr(self, "_startup_log_retry_count", 0) + 1
                else:
                    can_retry = False
            if can_retry:
                self._enqueue_console("🔁 Startup log-check: nghi treo → khởi động lại ngay (retry 1/1).")
                self._stop_server_processes(force=True, source="Startup log-check retry")
                time.sleep(2)
                # Gọi start an toàn; sẽ tự schedule lại log-check cho phiên mới
                self._start_server_safe(source="LogReady Retry", run_health_check=False)
        except Exception:
            pass

    def _schedule_startup_health_check(self, source: str = "") -> None:
        """Sau khi start process, kiểm tra server có thực sự vào được hay bị treo."""
        if not STARTUP_HEALTH_CHECK_ENABLED:
            return
        with self._startup_check_lock:
            self._startup_check_seq += 1
            seq = self._startup_check_seq
        t = threading.Thread(
            target=self._startup_health_check_worker,
            args=(seq, source or "Startup"),
            daemon=True
        )
        t.start()

    def _startup_health_check_worker(self, seq: int, source: str) -> None:
        if not STARTUP_HEALTH_CHECK_ENABLED:
            return
        ip, port = self._resolve_active_game_endpoint()
        if not ip or not port:
            self._enqueue_console("⚠️ Startup health-check: thiếu IP/PORT trong config, bỏ qua kiểm tra treo.")
            return

        max_retries = max(0, int(self.STARTUP_HEALTH_RETRY_MAX))
        for boot_round in range(0, max_retries + 1):
            with self._startup_check_lock:
                if seq != self._startup_check_seq:
                    return

            round_txt = f"{boot_round + 1}/{max_retries + 1}"
            self._enqueue_console(
                f"🩺 Startup health-check ({source}) lượt {round_txt}: kiểm tra {ip}:{port} sau khi boot..."
            )
            time.sleep(20)  # Chờ server nạp map/plugin trước khi test kết nối.

            connected = False
            for attempt in range(1, 9):
                with self._startup_check_lock:
                    if seq != self._startup_check_seq:
                        return
                if not self._is_server_running():
                    self._enqueue_console("❌ Startup health-check: process PalServer đã tắt trong lúc kiểm tra.")
                    return

                ping_ok = self._ping_host_once(ip)
                tcp_ok = self._tcp_port_open(ip, port, timeout_sec=3.0)
                # Ưu tiên kiểm tra port trước; chỉ khi port OK mới xét player online.
                if tcp_ok and self._has_online_players():
                    ping_note = "OK" if ping_ok else "không phản hồi"
                    self._enqueue_console(
                        f"✅ Startup health-check PASS: port {port} đã mở và có người chơi online "
                        f"(ping: {ping_note})."
                    )
                    connected = True
                    break

                if tcp_ok:
                    ping_note = "OK" if ping_ok else "không phản hồi"
                    self._enqueue_console(
                        f"✅ Startup health-check PASS: {ip}:{port} đã vào được (ping: {ping_note})."
                    )
                    connected = True
                    break

                self._enqueue_console(
                    f"⚠️ Startup health-check lượt {round_txt} lần {attempt}/8: "
                    f"chưa kết nối được {ip}:{port} "
                    f"(ping={'OK' if ping_ok else 'FAIL'}, tcp={'OK' if tcp_ok else 'FAIL'})."
                )
                time.sleep(10)

            if connected:
                return

            if boot_round < max_retries:
                retry_no = boot_round + 1
                self._enqueue_console(
                    f"🔁 Không vào được sau khởi động. Tự khởi động lại lần {retry_no}/{max_retries}..."
                )
                self._stop_server_processes(force=True, source=f"Startup health retry {retry_no}")
                time.sleep(2)
                self._start_server_safe(
                    source=f"{source} Retry {retry_no}",
                    run_health_check=False
                )
                continue

        warn_msg = (
            f"❌ Cảnh báo treo sau {max_retries + 1} lượt khởi động: process chạy nhưng chưa vào được {ip}:{port}."
        )
        self._enqueue_console(warn_msg)
        try:
            self.send_discord_alert(
                "🚨 **[CẢNH BÁO STARTUP TREO]**\n"
                f"• Nguồn khởi động: `{source}`\n"
                f"• Endpoint kiểm tra: `{ip}:{port}`\n"
                f"• Đã thử restart: `{max_retries}` lần\n"
                "• Trạng thái: Process có thể đã lên nhưng người chơi chưa vào được."
            )
        except Exception:
            pass

    def _refresh_server_exe_runtime(self) -> str:
        """Đọc lại SERVER_EXE từ manager_config để hỗ trợ đổi đường dẫn khi app đang chạy."""
        global SERVER_EXE
        try:
            cfg = _read_manager_cfg()
            if isinstance(cfg, dict):
                SERVER_EXE = _resolve_server_exe_from_cfg(cfg.get("SERVER_EXE", ""), SERVER_EXE)
        except Exception:
            pass
        return SERVER_EXE

    def _get_palserver_processes(self) -> list:
        """Tìm process PalServer đang chạy dựa trên exe/name."""
        procs = []
        try:
            server_exe_abs = os.path.abspath(SERVER_EXE).lower()
            for p in psutil.process_iter(["pid", "name", "exe"]):
                try:
                    name = (p.info.get("name") or "").lower()
                    exe  = (p.info.get("exe") or "").lower()
                    if name.startswith("palserver-win64"):
                        procs.append(p)
                    elif exe and exe == server_exe_abs:
                        procs.append(p)
                    elif exe and os.path.basename(exe) == "palserver.exe":
                        procs.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return procs

    def _is_server_running(self) -> bool:
        # Đồng bộ đường dẫn runtime trước khi check.
        self._refresh_server_exe_runtime()
        return len(self._get_palserver_processes()) > 0

    def _stop_server_processes(self, force: bool = True, source: str = "") -> bool:
        """Dừng tất cả process PalServer hiện có."""
        stopped_any = False
        for p in self._get_palserver_processes():
            try:
                if force:
                    p.kill()
                else:
                    p.terminate()
                stopped_any = True
            except Exception:
                pass
        if stopped_any:
            self._enqueue_console(f"⏹ Đã dừng PalServer ({source or 'manual'}).")
        return stopped_any

    def _start_server_safe(self, source: str = "", run_health_check: bool = True) -> bool:
        """Khởi động PalServer.exe an toàn: check path + tránh chạy trùng."""
        with self._server_op_lock:
            self._refresh_server_exe_runtime()
            if not SERVER_EXE or not os.path.isfile(SERVER_EXE):
                self._enqueue_console(f"❌ SERVER_EXE không hợp lệ: {SERVER_EXE}")
                return False
            if os.path.basename(SERVER_EXE).lower() != "palserver.exe":
                self._enqueue_console(f"❌ SERVER_EXE không phải PalServer.exe: {SERVER_EXE}")
                return False
            if self._is_server_running():
                self._enqueue_console(f"ℹ️ Server đã chạy ({source or 'safe-start'}), bỏ qua start trùng.")
                return True
            try:
                # Chạy giống mở tay PalServer.exe để tránh crash Shipping-Cmd khi launch bằng args.
                server_dir = os.path.dirname(SERVER_EXE)
                try:
                    os.startfile(SERVER_EXE)
                    self._enqueue_console(f"▶️ Khởi động PalServer ({source or 'safe-start'}) bằng startfile (user mode).")
                except Exception:
                    subprocess.Popen(
                        [SERVER_EXE],
                        cwd=server_dir,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                    self._enqueue_console(f"▶️ Khởi động PalServer ({source or 'safe-start'}) không args (user mode).")
                time.sleep(3)
                if self._is_server_running():
                    self._schedule_startup_log_ready_check(source=source or "safe-start")
                    if run_health_check:
                        self._schedule_startup_health_check(source=source or "safe-start")
                    return True
                self._enqueue_console("❌ Start thất bại: chưa thấy process PalServer sau khi mở file exe.")
                return False
            except Exception as e:
                self._enqueue_console(f"❌ Lỗi khởi động server ({source or 'safe-start'}): {e}")
                return False

    # ── Watchdog ──────────────────────────────
    def watchdog(self):
        while True:
            try:
                if self.auto_mode.get() and not self.is_processing:
                    now_ts = time.time()
                    cooldown_ok = (now_ts - self._watchdog_last_restart_at) > self.WATCHDOG_RESTART_COOLDOWN_SEC
                    if not self._is_server_running():
                        self.root.after(0, lambda: self.lbl_status.config(text="● SERVER OFFLINE", fg="#ff4444"))
                        if cooldown_ok:
                            self._watchdog_last_restart_at = now_ts
                            self._enqueue_console("🔁 Watchdog: khởi động lại server an toàn...")
                            self._start_server_safe(source="Watchdog")
                            self.is_notified_online = False
                    else:
                        self.root.after(0, lambda: self.lbl_status.config(text="● SERVER ONLINE", fg="#00ffcc"))
                        if not self.is_notified_online:
                            try:
                                res = requests.get(f"{API_URL}/info", auth=AUTH, timeout=2)
                                if res.status_code == 200:
                                    self.send_discord_alert(
                                        "🚀 **[Máy Chủ đang ONLINE]**\n"
                                        "✅ Vui lòng kết nối 27.65.213.42:8211 password là 1111\n"
                                        "Vào Chiến Với Anh Em Bốn Phương Thôi"
                                    )
                                    self.is_notified_online = True
                            except Exception:
                                pass
            except Exception:
                pass
            time.sleep(self.WATCHDOG_CHECK_INTERVAL_SEC)

    # ── Server log tail ───────────────────────
    def server_log_tail(self):
        """Background thread: đọc PalServer.log và đẩy dòng mới vào queue."""
        while True:
            try:
                if os.path.isfile(SERVER_LOG_FILE):
                    size = os.path.getsize(SERVER_LOG_FILE)
                    if size < self._server_log_pos:
                        # File bị reset / rotate
                        self._server_log_pos = 0
                    if size > self._server_log_pos:
                        with open(SERVER_LOG_FILE, "r",
                                  encoding="utf-8", errors="replace") as f:
                            f.seek(self._server_log_pos)
                            chunk = f.read(size - self._server_log_pos)
                            self._server_log_pos = f.tell()
                        for line in chunk.splitlines():
                            if not line.strip():
                                continue
                            self._server_log_queue.put(line)

                            # ── Admin mode tracking từ PalServer.log ──────
                            m_on = _ADMIN_ON_RE.search(line)
                            if m_on:
                                self._admin_mode_players.add(m_on.group(3))
                            else:
                                m_off = _ADMIN_OFF_RE.search(line)
                                if m_off:
                                    self._admin_mode_players.discard(
                                        m_off.group(3))

                            # ── Tech-Cheat: người chơi tự học ────────────
                            # Format: 'X' (...) unlocking Technology: 'TechCode'
                            m_tech = _TECH_RE.search(line)
                            if m_tech:
                                _, plr_name, plr_sid, tech_code = m_tech.groups()
                                self._techbug_check_event(
                                    plr_sid, plr_name, tech_code,
                                    source="natural")

                            # ── Tech-Cheat: admin dùng /learntech ────────
                            # Format: Replying to 'X': "Successfully unlocked technology 'TechCode' for..."
                            m_lt = _TECH_LEARNTECH_RE.search(line)
                            if m_lt:
                                _, plr_name, plr_sid, tech_code = m_lt.groups()
                                self._techbug_check_event(
                                    plr_sid, plr_name, tech_code,
                                    source="learntech")

                            # ── Chat in-game từ PalServer.log (fallback) ──
                            m_sc = _SERVERLOG_CHAT_RE.search(line)
                            if m_sc:
                                plr_name2, msg2 = m_sc.group(1), m_sc.group(2)
                                if msg2.strip():
                                    self._enqueue_console(
                                        f"💬 {plr_name2}: {msg2.strip()}")
            except Exception:
                pass
            time.sleep(0.5)

    # ── PalDefender helpers ───────────────────
    def _find_latest_paldef_log(self) -> str:
        """Trả về đường dẫn file log PalDefender mới nhất (theo mtime)."""
        try:
            candidates = [
                os.path.join(PALDEF_LOG_DIR, f)
                for f in os.listdir(PALDEF_LOG_DIR)
                if f.endswith(".log") and
                os.path.isfile(os.path.join(PALDEF_LOG_DIR, f))
            ]
            return max(candidates, key=os.path.getmtime) if candidates else ""
        except Exception:
            return ""

    def _find_latest_paldef_cheat(self) -> str:
        """Trả về đường dẫn file cheat log mới nhất."""
        try:
            candidates = [
                os.path.join(PALDEF_CHEATS_DIR, f)
                for f in os.listdir(PALDEF_CHEATS_DIR)
                if f.endswith("-cheats.log") and
                os.path.isfile(os.path.join(PALDEF_CHEATS_DIR, f))
            ]
            return max(candidates, key=os.path.getmtime) if candidates else ""
        except Exception:
            return ""

    def paldef_log_tail(self):
        """Background thread: theo dõi PalDefender main log, tự nhảy sang file mới."""
        while True:
            try:
                latest = self._find_latest_paldef_log()
                if latest and latest != self._paldef_log_file:
                    # Server khởi động lại → file mới
                    self._paldef_log_file = latest
                    self._paldef_log_pos  = 0
                    fname = os.path.basename(latest)
                    self._paldef_log_queue.put("─" * 55)
                    self._paldef_log_queue.put(f"📂  Session mới: {fname}")
                    self._paldef_log_queue.put("─" * 55)

                if self._paldef_log_file and os.path.isfile(self._paldef_log_file):
                    size = os.path.getsize(self._paldef_log_file)
                    if size < self._paldef_log_pos:
                        self._paldef_log_pos = 0
                    if size > self._paldef_log_pos:
                        with open(self._paldef_log_file, "r",
                                  encoding="utf-8", errors="replace") as f:
                            f.seek(self._paldef_log_pos)
                            chunk = f.read(size - self._paldef_log_pos)
                            self._paldef_log_pos = f.tell()
                        for line in chunk.splitlines():
                            if not line.strip():
                                continue
                            self._paldef_log_queue.put(line)

                            # ── AntiBug: build/dismantle speed ────────
                            ev = self._antibug_parse_line(line)
                            if ev:
                                self._antibug_process_event(ev)

                            # ── LiveMap Base: PalBoxV2 build/dismantle (real-time) ──
                            m_box = _PALBOXV2_RE.search(line)
                            if m_box:
                                _ts, _pname, _sid, _act, mx, my, mz = m_box.groups()
                                try:
                                    self._map_apply_base_event(
                                        _sid, _pname, _act,
                                        float(mx), float(my), float(mz)
                                    )
                                except Exception:
                                    pass

                            # ── Admin mode tracking ───────────────────
                            m_on = _ADMIN_ON_RE.search(line)
                            if m_on:
                                self._admin_mode_players.add(m_on.group(3))
                            else:
                                m_off = _ADMIN_OFF_RE.search(line)
                                if m_off:
                                    self._admin_mode_players.discard(
                                        m_off.group(3))

                            # ── Tech-Cheat: người chơi tự học ────────
                            # Format: 'X' (...) unlocking Technology: 'TechCode'
                            m_tech = _TECH_RE.search(line)
                            if m_tech:
                                _, plr_name, plr_sid, tech_code = m_tech.groups()
                                self._techbug_check_event(
                                    plr_sid, plr_name, tech_code,
                                    source="natural")

                            # ── Tech-Cheat: admin dùng /learntech ─────
                            # Format: Replying to 'X': "Successfully unlocked technology 'TechCode' for..."
                            m_lt = _TECH_LEARNTECH_RE.search(line)
                            if m_lt:
                                _, plr_name, plr_sid, tech_code = m_lt.groups()
                                self._techbug_check_event(
                                    plr_sid, plr_name, tech_code,
                                    source="learntech")

                            # ── Chat in-game từ PalDefender log ───────
                            # Format: [HH:MM:SS][info] [Chat::Global]['Name' (...)]: msg
                            m_chat = _CHAT_RE.search(line)
                            if m_chat:
                                ts       = m_chat.group(1)   # HH:MM:SS
                                ch_type  = m_chat.group(2)   # Global / Local / ...
                                plr_name = m_chat.group(3)   # Tên người chơi
                                msg      = m_chat.group(5)   # Nội dung tin nhắn
                                if msg.strip():
                                    self._enqueue_console(
                                        f"💬 [{ts}] [{ch_type}] {plr_name}: {msg.strip()}")
                                    # Forward → Discord (webhook với tên người chơi)
                                    self._discord_forward_chat(plr_name, ch_type, msg.strip())

                            # ── NPC Attack Tracking (kick) ─────────────
                            # Format: 'PlayerName' (...) was attacked by a wild 'NPC' (ID) at X Y Z
                            m_attack = _NPC_ATTACK_RE.search(line)
                            if m_attack:
                                _ts2, atk_name, atk_sid, npc_name, npc_id, atk_coords = m_attack.groups()
                                if npc_id and npc_id.strip() in NPC_BAN_IDS:
                                    if self.npc_attack_kick_enabled.get():
                                        threading.Thread(
                                            target=self._npc_attack_kick_player,
                                            args=(atk_sid, atk_name, npc_name,
                                                  npc_id, atk_coords or ""),
                                            daemon=True
                                        ).start()

                            # ── Pal Capture Tracking (ban) ─────────────
                            # Format: [HH:MM:SS][info] 'PlayerName' (UserId=steam_...) has captured Pal 'PalName' (PalID) at ...
                            m_capture = _PAL_CAPTURE_RE.search(line)
                            if m_capture:
                                _ts, plr_name, plr_sid, pal_name, pal_id, cap_coords = m_capture.groups()
                                self._track_pal_capture(plr_sid, plr_name, pal_name, pal_id,
                                                        cap_coords or "")
            except Exception:
                pass
            time.sleep(0.5)

    def paldef_cheat_tail(self):
        """Background thread: theo dõi cheat log, cảnh báo Discord khi phát hiện."""
        def _flush_dedupe():
            if self._cheat_dedupe_count > 1 and self._cheat_dedupe_last_line:
                self._paldef_cheat_queue.put(f"↳ (gộp {self._cheat_dedupe_count} dòng trùng)")
            self._cheat_dedupe_last_line = ""
            self._cheat_dedupe_count = 0

        while True:
            try:
                latest = self._find_latest_paldef_cheat()
                if latest and latest != self._paldef_cheat_file:
                    _flush_dedupe()
                    self._paldef_cheat_file = latest
                    self._paldef_cheat_pos  = 0

                if self._paldef_cheat_file and os.path.isfile(self._paldef_cheat_file):
                    size = os.path.getsize(self._paldef_cheat_file)
                    if size < self._paldef_cheat_pos:
                        self._paldef_cheat_pos = 0
                    if size > self._paldef_cheat_pos:
                        with open(self._paldef_cheat_file, "r",
                                  encoding="utf-8", errors="replace") as f:
                            f.seek(self._paldef_cheat_pos)
                            chunk = f.read(size - self._paldef_cheat_pos)
                            self._paldef_cheat_pos = f.tell()
                        for line in chunk.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            if line == self._cheat_dedupe_last_line:
                                self._cheat_dedupe_count += 1
                                continue
                            _flush_dedupe()
                            self._cheat_dedupe_last_line = line
                            self._cheat_dedupe_count = 1
                            self._paldef_cheat_queue.put(line)
                            # Cảnh báo manager console + Discord
                            if "cheater" in line.lower() or "[warning]" in line.lower():
                                now_ts = time.time()
                                key = line[:180]
                                prev = float(self._cheat_alert_last.get(key, 0.0))
                                if now_ts - prev < 10.0:
                                    continue
                                self._cheat_alert_last[key] = now_ts
                                self._enqueue_console(f"🚨 CHEAT DETECTED: {line}")
                                _alert_msg = (
                                    f"🚨 **[CHEAT DETECTED - PALDEFENDER]**\n"
                                    f"```{line}```"
                                )
                                # → Antibug webhook (admin-only)
                                if self.paldef_discord_alert.get():
                                    threading.Thread(
                                        target=self._send_antibug_discord,
                                        args=(_alert_msg,),
                                        daemon=True
                                    ).start()
                                # → Main Discord webhook (thông báo công khai)
                                if self.paldef_discord_alert_main.get():
                                    threading.Thread(
                                        target=self.send_discord_alert,
                                        args=(_alert_msg,),
                                        daemon=True
                                    ).start()
                        _flush_dedupe()
            except Exception:
                pass
            time.sleep(1)

    def _cleanup_paldef_logs_once(self):
        """Xóa file log PalDefender quá hạn trong Logs và Logs\\Cheats."""
        if not self.paldef_log_cleanup_enabled.get():
            return
        try:
            keep_h = int(self.paldef_log_keep_hours.get())
        except Exception:
            keep_h = 24
        keep_h = keep_h if keep_h in (24, 12, 6, 4, 2) else 24
        cutoff = time.time() - (keep_h * 3600)
        deleted = 0
        skipped = {os.path.abspath(self._paldef_log_file), os.path.abspath(self._paldef_cheat_file)}
        # Dọn cả Logs, Logs\Cheats và Logs\RESTAPI (theo yêu cầu vận hành).
        restapi_log_dir = os.path.join(PALDEF_LOG_DIR, "RESTAPI")
        for base in {PALDEF_LOG_DIR, PALDEF_CHEATS_DIR, restapi_log_dir, PALDEF_REST_DIR}:
            try:
                if not os.path.isdir(base):
                    continue
                for fn in os.listdir(base):
                    if not fn.lower().endswith(".log"):
                        continue
                    p = os.path.abspath(os.path.join(base, fn))
                    if p in skipped:
                        continue
                    try:
                        if os.path.getmtime(p) < cutoff:
                            os.remove(p)
                            deleted += 1
                    except Exception:
                        continue
            except Exception:
                continue
        if deleted > 0:
            self._enqueue_console(f"🧹 Log cleanup: đã xóa {deleted} file cũ (> {keep_h}h).")

    def paldef_log_cleanup_loop(self):
        """Dọn log cũ định kỳ để thư mục Logs/Cheats luôn gọn."""
        while True:
            try:
                self._cleanup_paldef_logs_once()
            except Exception:
                pass
            time.sleep(300)

    # ── Scheduler ─────────────────────────────
    def scheduler_process(self):
        while True:
            if self.auto_mode.get():
                now = datetime.datetime.now().strftime("%H:%M")
                if now in RESET_SCHEDULE and self.last_reset_minute != now:
                    self.last_reset_minute = now
                    threading.Thread(target=self.reset_sequence, daemon=True).start()
            time.sleep(10)

    # ── Stats loop ────────────────────────────
    def update_stats_loop(self):
        while True:
            try:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                if "CPU USAGE" in self.overview_widgets and \
                   self.overview_widgets["CPU USAGE"].winfo_exists():
                    self.overview_widgets["CPU USAGE"].config(text=f"{cpu}%")
                    self.overview_widgets["RAM USAGE"].config(text=f"{ram}%")
                    self.overview_widgets["PLAYERS ONLINE"].config(text=self.player_count_str)
            except Exception:
                pass
            time.sleep(2)

    # ── Player sync ───────────────────────────
    def player_sync(self):
        while True:
            try:
                res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if res.status_code == 200:
                    players = res.json().get("players", [])
                    self.player_count_str = f"{len(players)}/{self._max_players}"
                    now_ts = time.time()
                    online_now = set()
                    dirty = False
                    for p in players:
                        steamid  = self._normalize_steamid(p.get("userId", ""))
                        playerid = p.get("playerId", "")
                        name     = p.get("name", "")
                        if steamid:
                            online_now.add(steamid)
                            self._steamid_to_name[steamid] = name
                            if steamid not in self.player_stats:
                                self.player_stats[steamid] = {
                                    "name": name,
                                    "level": int(p.get("level", 0) or 0),
                                    "pal_count": 0,
                                    "playtime_sec": 0.0,
                                    "session_start": now_ts,
                                    "last_update": now_ts,
                                }
                            else:
                                self.player_stats[steamid]["name"] = name
                                self.player_stats[steamid].setdefault("playtime_sec", 0.0)
                                self.player_stats[steamid].setdefault("session_start", now_ts)
                                self.player_stats[steamid]["last_update"] = now_ts
                                # Checkpoint playtime online định kỳ để tránh mất dữ liệu khi crash
                                sess = float(self.player_stats[steamid].get("session_start", 0.0) or 0.0)
                                if sess > 0 and steamid not in self._online_players_prev:
                                    # vừa reconnect session từ trạng thái chưa đồng bộ
                                    self.player_stats[steamid]["session_start"] = now_ts
                                elif sess > 0:
                                    delta = max(0.0, now_ts - sess)
                                    if delta >= 1.0:
                                        self.player_stats[steamid]["playtime_sec"] = float(
                                            self.player_stats[steamid].get("playtime_sec", 0.0) or 0.0
                                        ) + delta
                                        self.player_stats[steamid]["session_start"] = now_ts
                                        dirty = True
                        if steamid and playerid:
                            self._steamid_to_playerid[steamid] = playerid

                    joined = online_now - self._online_players_prev
                    left = self._online_players_prev - online_now

                    for sid in joined:
                        st = self.player_stats.setdefault(
                            sid,
                            {"name": self._steamid_to_name.get(sid, sid), "level": 0, "pal_count": 0,
                             "playtime_sec": 0.0, "session_start": now_ts, "last_update": now_ts}
                        )
                        st["session_start"] = now_ts
                        st["last_update"] = now_ts
                        dirty = True
                        self._audit_playtime_event("join", sid, st.get("name", self._steamid_to_name.get(sid, sid)),
                                                   note=f"online={len(online_now)}/{self._max_players}")
                        self._send_player_connect_webhook(
                            sid, st.get("name", self._steamid_to_name.get(sid, sid)),
                            event="join", online_count=len(online_now), max_players=self._max_players
                        )
                        try:
                            self._try_daily_checkin_reward(sid, st.get("name", ""))
                        except Exception:
                            pass

                    for sid in left:
                        st = self.player_stats.get(sid, {})
                        sess = float(st.get("session_start", 0) or 0)
                        if sess > 0:
                            st["playtime_sec"] = float(st.get("playtime_sec", 0.0) or 0.0) + max(0.0, now_ts - sess)
                        st["session_start"] = 0.0
                        st["last_update"] = now_ts
                        dirty = True
                        self._audit_playtime_event(
                            "leave", sid, st.get("name", self._steamid_to_name.get(sid, sid)),
                            note=f"total={self._fmt_playtime(st.get('playtime_sec', 0.0))} online={len(online_now)}/{self._max_players}"
                        )
                        self._send_player_connect_webhook(
                            sid, st.get("name", self._steamid_to_name.get(sid, sid)),
                            event="leave", online_count=len(online_now), max_players=self._max_players
                        )
                        try:
                            self._mark_online60_leave(sid)
                        except Exception:
                            pass

                    self._online_players_prev = online_now
                    for sid in online_now:
                        try:
                            self._tick_online60_reward(sid, self._steamid_to_name.get(sid, sid), now_ts)
                        except Exception:
                            pass
                    # Save khi có thay đổi hoặc mỗi 60s nếu đang có người online (đảm bảo durability)
                    if dirty and (now_ts - self._player_stats_last_save_ts >= 5):
                        self._save_player_stats()
                        self._audit_playtime_event("save", "-", "system", note=f"dirty_save players={len(self.player_stats)}")
                    elif online_now and (now_ts - self._player_stats_last_save_ts >= 60):
                        self._save_player_stats()
                        self._audit_playtime_event("save", "-", "system", note=f"periodic_save players={len(self.player_stats)}")
            except Exception:
                pass
            time.sleep(10)

    # ── Player Ranking System ─────────────────────────
    def _normalize_player_stats_record(self, steamid: str, stats: dict) -> dict:
        now_ts = time.time()
        if not isinstance(stats, dict):
            stats = {}
        return {
            "name": str(stats.get("name", self._steamid_to_name.get(steamid, "Unknown")) or "Unknown"),
            "level": int(stats.get("level", 0) or 0),
            "pal_count": int(stats.get("pal_count", 0) or 0),
            "playtime_sec": float(stats.get("playtime_sec", 0.0) or 0.0),
            # session_start chỉ giữ khi > 0, còn lại reset 0.0 để rõ trạng thái offline
            "session_start": float(stats.get("session_start", 0.0) or 0.0),
            "last_update": float(stats.get("last_update", now_ts) or now_ts),
        }

    def _load_player_stats(self):
        """Load player stats từ file JSON."""
        try:
            if os.path.isfile(self.player_stats_file):
                with open(self.player_stats_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    normalized = {}
                    for sid, st in raw.items():
                        sid_n = self._normalize_steamid(str(sid))
                        if not sid_n:
                            continue
                        normalized[sid_n] = self._normalize_player_stats_record(sid_n, st)
                    self.player_stats = normalized
                else:
                    self.player_stats = {}
        except Exception:
            self.player_stats = {}

    def _save_player_stats(self):
        """Lưu player stats vào file JSON."""
        try:
            os.makedirs(os.path.dirname(self.player_stats_file), exist_ok=True)
            with open(self.player_stats_file, "w", encoding="utf-8") as f:
                json.dump(self.player_stats, f, indent=2, ensure_ascii=False)
            self._player_stats_last_save_ts = time.time()
        except Exception:
            pass

    def _audit_playtime_event(self, event: str, steamid: str, name: str, note: str = "") -> None:
        try:
            os.makedirs(os.path.dirname(self.player_time_log_file), exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{ts}] {event.upper():<10} {steamid} | {name}"
            if note:
                line += f" | {note}"
            with open(self.player_time_log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _fmt_playtime(self, total_sec: float) -> str:
        total = int(max(0, float(total_sec or 0)))
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h}h {m:02d}m"

    def _player_total_playtime_sec(self, steamid: str, now_ts: float | None = None) -> float:
        st = self.player_stats.get(steamid, {})
        base = float(st.get("playtime_sec", 0.0) or 0.0)
        sess = float(st.get("session_start", 0.0) or 0.0)
        if sess > 0:
            t_now = float(now_ts if now_ts is not None else time.time())
            base += max(0.0, t_now - sess)
        return base

    def _send_player_connect_webhook(self, steamid: str, name: str, event: str,
                                     online_count: int, max_players: int) -> None:
        if not PLAYER_CONNECT_WEBHOOK_URL:
            return
        try:
            now_txt = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            joined = (event == "join")
            title = "🟢 Người chơi đã tham gia / đang kết nối" if joined else "🔴 Người chơi đã rời mạng"
            payload = {
                "username": "Connect",
                "embeds": [{
                    "title": title,
                    "color": 0x57F287 if joined else 0xED4245,
                    "fields": [
                        {"name": "👤 Người chơi", "value": f"`{name}`", "inline": True},
                        {"name": "🆔 SteamID", "value": f"`{steamid}`", "inline": True},
                        {"name": "👥 Online", "value": f"`{online_count}/{max_players}`", "inline": True},
                    ],
                    "footer": {"text": f"Manager ServerPal • {now_txt}"}
                }]
            }
            requests.post(PLAYER_CONNECT_WEBHOOK_URL, json=payload, timeout=6)
        except Exception:
            pass

    # ── Bot 2 message ID persistence ──────────────────────────────────
    def _load_bot2_msg_ids(self):
        """Load message IDs từ file để dùng lại sau restart — tránh spam."""
        try:
            if os.path.isfile(self._bot2_msg_file):
                with open(self._bot2_msg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._bot2_status_msg_id  = int(data.get("status_msg_id",  0) or 0)
                self._bot2_ranking_msg_id = int(data.get("ranking_msg_id", 0) or 0)
                self._bot2_livemap_msg_id = int(data.get("livemap_msg_id", 0) or 0)
        except Exception:
            self._bot2_status_msg_id  = 0
            self._bot2_ranking_msg_id = 0
            self._bot2_livemap_msg_id = 0

    def _save_bot2_msg_ids(self):
        """Lưu message IDs vào file để dùng lại sau restart."""
        try:
            os.makedirs(os.path.dirname(self._bot2_msg_file), exist_ok=True)
            with open(self._bot2_msg_file, "w", encoding="utf-8") as f:
                json.dump({
                    "status_msg_id":  self._bot2_status_msg_id,
                    "ranking_msg_id": self._bot2_ranking_msg_id,
                    "livemap_msg_id": self._bot2_livemap_msg_id
                }, f)
        except Exception:
            pass

    def _track_pal_capture(self, steamid: str, player_name: str,
                           pal_name: str = "", pal_id: str = "",
                           coords: str = ""):
        """Track khi người chơi bắt được Pal.
        Nếu Pal bị bắt là NPC (SalesPerson, BlackMarketTrader, …) → auto-ban ngay lập tức.
        """
        if not steamid:
            return
        steamid = self._normalize_steamid(steamid)
        if not steamid:
            return

        # ── Kiểm tra NPC capture → BAN ngay ──────────────────────────────
        if self.npc_capture_ban_enabled.get() and pal_id:
            if pal_id.strip() in NPC_BAN_IDS:
                threading.Thread(
                    target=self._npc_capture_ban_player,
                    args=(steamid, player_name, pal_name, pal_id, coords),
                    daemon=True
                ).start()
                return  # Không cần track stat, người chơi sẽ bị ban

        if steamid not in self.player_stats:
            self.player_stats[steamid] = {
                "name": player_name,
                "level": 0,
                "pal_count": 0,
                "last_update": time.time()
            }

        self.player_stats[steamid]["name"] = player_name
        self.player_stats[steamid]["pal_count"] = self.player_stats[steamid].get("pal_count", 0) + 1
        self.player_stats[steamid]["last_update"] = time.time()
        self._save_player_stats()

    def _update_player_levels(self):
        """Cập nhật level của tất cả người chơi từ REST API hoặc cache."""
        try:
            res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
            if res.status_code == 200:
                players = res.json().get("players", [])
                for p in players:
                    steamid = self._normalize_steamid(p.get("userId", ""))
                    name = p.get("name", "")
                    if not steamid:
                        continue
                    
                    # Thử lấy level từ API response (nếu có)
                    level = p.get("level", 0)
                    if level == 0:
                        # Fallback: dùng cache nếu có
                        level = self._player_level_cache.get(steamid, 0)
                    
                    if steamid not in self.player_stats:
                        self.player_stats[steamid] = {
                            "name": name,
                            "level": level,
                            "pal_count": 0,
                            "playtime_sec": 0.0,
                            "session_start": 0.0,
                            "last_update": time.time()
                        }
                    else:
                        self.player_stats[steamid]["name"] = name
                        self.player_stats[steamid]["level"] = level
                        self.player_stats[steamid].setdefault("playtime_sec", 0.0)
                        self.player_stats[steamid].setdefault("session_start", 0.0)
                        self.player_stats[steamid]["last_update"] = time.time()
        except Exception:
            pass

    def _get_ranking(self, top_n: int = 10) -> list:
        """Lấy danh sách xếp hạng top N người chơi.
        Sắp xếp theo: level (giảm dần), sau đó pal_count (giảm dần).
        """
        self._update_player_levels()
        
        # Lọc và sắp xếp
        ranked = []
        for steamid, stats in self.player_stats.items():
            if stats.get("level", 0) > 0 or stats.get("pal_count", 0) > 0:
                ranked.append({
                    "steamid": steamid,
                    "name": stats.get("name", "Unknown"),
                    "level": stats.get("level", 0),
                    "pal_count": stats.get("pal_count", 0),
                    "playtime_sec": self._player_total_playtime_sec(steamid)
                })
        
        # Sắp xếp: level giảm dần, pal_count giảm dần, sau đó playtime giảm dần
        ranked.sort(key=lambda x: (x["level"], x["pal_count"], x["playtime_sec"]), reverse=True)
        return ranked[:top_n]

    def _send_ranking_to_discord(self):
        """Gửi bảng xếp hạng đẹp lên Discord (kênh Bảng Xếp Hạng riêng)."""
        webhook = RANKING_WEBHOOK_URL or DISCORD_WEBHOOK_URL
        if not webhook:
            return
        
        try:
            ranking = self._get_ranking(20)  # Top 20
            
            if not ranking:
                return
            
            # Tính tổng số người chơi có dữ liệu
            total_players = len([s for s in self.player_stats.values() 
                               if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])
            
            # Tạo embed đẹp và chuyên nghiệp
            embed = {
                "title": "🏆 BẢNG XẾP HẠNG NGƯỜI CHƠI",
                "description": f"📊 **Top người chơi theo cấp độ và số lượng Pal đã bắt**\n"
                              f"👥 Tổng số người chơi có dữ liệu: **{total_players}**",
                "color": 0x00ff88,  # Màu xanh lá
                "thumbnail": {
                    "url": "https://i.imgur.com/4M34hi2.png"  # Palworld logo placeholder
                },
                "fields": [],
                "footer": {
                    "text": f"Palworld Server Ranking • Cập nhật: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                    "icon_url": "https://i.imgur.com/4M34hi2.png"
                },
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
            }
            
            # Tạo field cho top 10 với format đẹp
            top_10_text = ""
            medals = ["🥇", "🥈", "🥉"]
            level_icons = ["⭐", "🌟", "💫"]
            
            for idx, player in enumerate(ranking[:10], 1):
                medal = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
                name = player["name"][:18]  # Giới hạn độ dài tên
                level = player["level"]
                pal_count = player["pal_count"]
                playtime = self._fmt_playtime(player.get("playtime_sec", 0))
                
                # Thêm padding cho tên để căn chỉnh đẹp
                name_padded = name.ljust(18)
                
                # Icon level theo cấp độ
                if level >= 50:
                    level_icon = level_icons[2]
                elif level >= 30:
                    level_icon = level_icons[1]
                else:
                    level_icon = level_icons[0]
                
                top_10_text += f"{medal} **{name_padded}**\n"
                top_10_text += f"   {level_icon} Cấp: `{level:3d}` | 🎣 Pal: `{pal_count:4d}` | ⏱ `{playtime}`\n\n"
            
            embed["fields"].append({
                "name": "🏅 TOP 10 NGƯỜI CHƠI HÀNG ĐẦU",
                "value": top_10_text or "Chưa có dữ liệu",
                "inline": False
            })
            
            # Thêm field cho top 11-20 nếu có (format compact hơn)
            if len(ranking) > 10:
                top_11_20_text = ""
                for idx, player in enumerate(ranking[10:20], 11):
                    name = player["name"][:16]
                    level = player["level"]
                    pal_count = player["pal_count"]
                    playtime = self._fmt_playtime(player.get("playtime_sec", 0))
                    # Format compact với emoji
                    top_11_20_text += f"**{idx:2d}.** {name[:16]:<16} ⭐`{level:3d}` 🎣`{pal_count:4d}` ⏱`{playtime}`\n"
                
                embed["fields"].append({
                    "name": "📋 TOP 11-20",
                    "value": top_11_20_text,
                    "inline": False
                })
            
            # Thêm thống kê tổng quan
            if ranking:
                avg_level = sum(p["level"] for p in ranking) / len(ranking)
                avg_pals = sum(p["pal_count"] for p in ranking) / len(ranking)
                max_level = max(p["level"] for p in ranking)
                max_pals = max(p["pal_count"] for p in ranking)
                
                stats_text = (
                    f"📈 **Cấp độ trung bình:** `{avg_level:.1f}`\n"
                    f"🎣 **Pal trung bình:** `{avg_pals:.1f}`\n"
                    f"🔥 **Cấp cao nhất:** `{max_level}`\n"
                    f"💎 **Nhiều Pal nhất:** `{max_pals}`"
                )
                
                embed["fields"].append({
                    "name": "📊 THỐNG KÊ TỔNG QUAN",
                    "value": stats_text,
                    "inline": False
                })
            
            # Gửi webhook — ưu tiên RANKING_WEBHOOK_URL, fallback DISCORD_WEBHOOK_URL
            webhook = RANKING_WEBHOOK_URL or DISCORD_WEBHOOK_URL
            payload = {
                "username": "🏆 Bảng Xếp Hạng",
                "embeds": [embed]
            }
            requests.post(webhook, json=payload, timeout=10)
            self._enqueue_console("✅ Đã gửi bảng xếp hạng lên Discord (Bảng Xếp Hạng)")
            
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi gửi ranking Discord: {e}")

    def send_ranking_manual(self):
        """Gửi ranking thủ công (có thể gọi từ UI hoặc command)."""
        try:
            self._update_player_levels()
            self._send_ranking_to_discord()
            self.ranking_last_update = time.time()
            return True
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi gửi ranking thủ công: {e}")
            return False

    def ranking_update_loop(self):
        """Background thread: cập nhật và gửi ranking định kỳ."""
        time.sleep(30)  # Chờ server khởi động
        while True:
            try:
                if self.ranking_enabled.get():
                    now = time.time()
                    if now - self.ranking_last_update >= self.ranking_update_interval:
                        self._update_player_levels()
                        self._send_ranking_to_discord()
                        self._award_top10_bonus_if_due()
                        self.ranking_last_update = now
            except Exception:
                pass
            time.sleep(60)  # Check mỗi phút

    # ── Threads start ─────────────────────────
    def start_threads(self):
        tasks = [
            self.watchdog,
            self.update_stats_loop,
            self.player_sync,
            self.scheduler_process,
            self.newbie_gift_monitor,
            self._gift_retry_loop,
            self.server_log_tail,
            self.paldef_log_tail,
            self.paldef_cheat_tail,
            self.paldef_log_cleanup_loop,
            self.map_player_fetch_loop,
            self.guild_fetch_loop,         # Guild live — fetch mỗi 30s
            self._pdapi_status_poll,
            self.discord_to_ingame_poll,   # Discord ↔ ingame chat bridge
            self.ranking_update_loop,     # Ranking system — cập nhật định kỳ
            self.discord_bot2_poll,        # Discord Bot 2 — commands & features
        ]
        for task in tasks:
            threading.Thread(target=task, daemon=True).start()

    # ── Player helpers ────────────────────────
    def _normalize_steamid(self, raw: str) -> str:
        """Chuẩn hóa steamid: đảm bảo dạng steam_XXXX."""
        if not raw:
            return ""
        raw = raw.strip().strip('"').strip("'")
        if raw.startswith("steam_"):
            return raw
        if raw.isdigit():
            return f"steam_{raw}"
        return raw

    def _read_max_players(self) -> int:
        """Đọc ServerPlayerMaxNum từ PalWorldSettings.ini, fallback = 32."""
        try:
            ini = self._settings_parse_ini()
            v = ini.get("ServerPlayerMaxNum", "32")
            return max(1, int(float(v)))
        except Exception:
            return 32

    # ─────────────────────────────────────────
    #  RCON GIVE HELPERS
    # ─────────────────────────────────────────
    def _rcon_give_item(self, playerid: str, steam_number: str, steamid: str,
                         item: str, qty: int) -> bool:
        """Gửi lệnh 'give' qua RCON. Thử nhiều format identifier."""
        candidates = []
        if playerid:
            candidates.append(f"give {playerid} {item} {qty}")
        if steam_number:
            candidates.append(f"give {steam_number} {item} {qty}")
        if steamid:
            candidates.append(f"give {steamid} {item} {qty}")

        for cmd in candidates:
            out = rcon_exec(cmd)
            low = (out or "").lower()
            self._enqueue_console(f"  📦 [ITEM] {cmd!r} → {out or 'OK'}")
            if "failed" in low or "error" in low or "unknown" in low or \
               "not found" in low or "itemid" in low:
                continue
            return True
        return False

    def _rcon_give_pal(self, playerid: str, steam_number: str, steamid: str,
                        pal_id: str, level: int = 1) -> bool:
        """Gửi lệnh 'givepal' qua RCON."""
        candidates = []
        if playerid:
            candidates.append(f"givepal {playerid} {pal_id} {level}")
        if steam_number:
            candidates.append(f"givepal {steam_number} {pal_id} {level}")
        if steamid:
            candidates.append(f"givepal {steamid} {pal_id} {level}")

        for cmd in candidates:
            out = rcon_exec(cmd)
            low = (out or "").lower()
            self._enqueue_console(f"  🐾 [PAL]  {cmd!r} → {out or 'OK'}")
            if "failed" in low or "error" in low or "unknown" in low or \
               "not found" in low or "itemid" in low:
                continue
            return True
        return False

    # ─────────────────────────────────────────
    #  NEWBIE GIFT — TRACKING FILES
    # ─────────────────────────────────────────
    def _load_newbie_gift_tracking(self):
        """Đọc danh sách SteamID đã nhận quà từ file."""
        try:
            if os.path.isfile(self.newbie_gift_file):
                with open(self.newbie_gift_file, "r", encoding="utf-8") as f:
                    for line in f:
                        sid = line.strip()
                        if sid:
                            self.newbie_gift_received.add(sid)
        except Exception:
            pass

    def _save_newbie_gift_tracking(self, steamid: str):
        """Lưu SteamID vào file tracking (append mode)."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)  # đảm bảo thư mục tồn tại
            with open(self.newbie_gift_file, "a", encoding="utf-8") as f:
                f.write(f"{steamid}\n")
            self.newbie_gift_received.add(steamid)
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi lưu tracking quà tân thủ: {e}")

    def _load_daily_checkin_tracking(self):
        """Load danh sách đã nhận quà điểm danh theo ngày."""
        try:
            if os.path.isfile(self.daily_checkin_file):
                with open(self.daily_checkin_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    out = {}
                    for d, ids in data.items():
                        if isinstance(ids, list):
                            out[str(d)] = [self._normalize_steamid(str(x)) for x in ids if self._normalize_steamid(str(x))]
                    self.daily_checkin_claims = out
        except Exception:
            self.daily_checkin_claims = {}

    def _save_daily_checkin_tracking(self):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            with open(self.daily_checkin_file, "w", encoding="utf-8") as f:
                json.dump(self.daily_checkin_claims, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_online60_tracking(self):
        """Load trạng thái tích lũy online 60 phút."""
        try:
            if os.path.isfile(self.online60_file):
                with open(self.online60_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    out = {}
                    for sid, st in data.items():
                        sid_n = self._normalize_steamid(str(sid))
                        if not sid_n or not isinstance(st, dict):
                            continue
                        out[sid_n] = {
                            "accum_sec": float(st.get("accum_sec", 0.0) or 0.0),
                            "last_seen": float(st.get("last_seen", 0.0) or 0.0),
                        }
                    self.online60_reward_state = out
        except Exception:
            self.online60_reward_state = {}

    def _save_online60_tracking(self):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            with open(self.online60_file, "w", encoding="utf-8") as f:
                json.dump(self.online60_reward_state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_ranking_bonus_claims(self):
        try:
            if os.path.isfile(self.ranking_bonus_claim_file):
                with open(self.ranking_bonus_claim_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    out = {}
                    for d, ids in data.items():
                        if isinstance(ids, list):
                            out[str(d)] = [self._normalize_steamid(str(x)) for x in ids if self._normalize_steamid(str(x))]
                    self.ranking_bonus_claims = out
        except Exception:
            self.ranking_bonus_claims = {}

    def _save_ranking_bonus_claims(self):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            with open(self.ranking_bonus_claim_file, "w", encoding="utf-8") as f:
                json.dump(self.ranking_bonus_claims, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_ranking_bonus_daily_state(self):
        try:
            if os.path.isfile(self.ranking_bonus_state_file):
                with open(self.ranking_bonus_state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self.ranking_bonus_daily_state = data
        except Exception:
            self.ranking_bonus_daily_state = {}

    def _save_ranking_bonus_daily_state(self):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            with open(self.ranking_bonus_state_file, "w", encoding="utf-8") as f:
                json.dump(self.ranking_bonus_daily_state, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _reward_items_to_text(self, items: list) -> str:
        out = []
        for it in (items or []):
            iid = str(it.get("ItemID", "")).strip()
            cnt = int(it.get("Count", 0) or 0)
            if iid and cnt > 0:
                out.append(f"{iid}: {cnt}")
        return "\n".join(out)

    def _reward_items_from_text(self, text: str) -> list:
        items = []
        for raw in (text or "").splitlines():
            ln = raw.strip()
            if not ln or ln.startswith("#"):
                continue
            if ":" not in ln:
                continue
            iid, cnt_txt = ln.split(":", 1)
            iid = iid.strip()
            try:
                cnt = int(cnt_txt.strip())
            except Exception:
                cnt = 0
            if iid and cnt > 0:
                items.append({"ItemID": iid, "Count": cnt})
        return items

    def _newbie_template_to_text(self, gifts: list) -> str:
        out = []
        for g in (gifts or []):
            typ = str(g.get("Type", "item")).strip().lower()
            gid = str(g.get("ID", "")).strip()
            cnt = int(g.get("Count", 0) or 0)
            if typ in ("item", "pal") and gid and cnt > 0:
                out.append(f"{typ}:{gid}:{cnt}")
        return "\n".join(out)

    def _newbie_template_from_text(self, text: str) -> list:
        out = []
        for raw in (text or "").splitlines():
            ln = raw.strip()
            if not ln or ln.startswith("#"):
                continue
            parts = [x.strip() for x in ln.split(":")]
            if len(parts) != 3:
                continue
            typ, gid, cnt_txt = parts
            typ = typ.lower()
            try:
                cnt = int(cnt_txt)
            except Exception:
                cnt = 0
            if typ in ("item", "pal") and gid and cnt > 0:
                out.append({"Type": typ, "ID": gid, "Count": cnt})
        return out

    def _load_reward_templates_from_cfg(self):
        """Đọc cấu hình quà từ manager_config.json, fallback default nếu thiếu."""
        try:
            data = self._settings_load_manager_config() or {}
            daily = data.get("DAILY_CHECKIN_REWARD_ITEMS")
            online = data.get("ONLINE60_REWARD_ITEMS")
            sec = data.get("ONLINE60_REWARD_SECONDS")
            top10 = data.get("TOP10_BONUS_TEMPLATES")
            top10_pool = data.get("TOP10_BONUS_POOL_ITEMS")
            newbie = data.get("NEWBIE_GIFT_TEMPLATE")
            if isinstance(newbie, list) and newbie:
                txt = self._newbie_template_to_text(newbie)
                parsed = self._newbie_template_from_text(txt)
                if parsed:
                    self.newbie_gift_template = parsed
            if isinstance(daily, list) and daily:
                self.daily_checkin_reward_items = self._reward_items_from_text(
                    self._reward_items_to_text(daily)
                ) or self.daily_checkin_reward_items
            if isinstance(online, list) and online:
                self.online60_reward_items = self._reward_items_from_text(
                    self._reward_items_to_text(online)
                ) or self.online60_reward_items
            if isinstance(top10_pool, list) and top10_pool:
                parsed_pool = self._reward_items_from_text(self._reward_items_to_text(top10_pool))
                if parsed_pool:
                    self.top10_bonus_pool_items = parsed_pool
            elif isinstance(top10, list) and top10:
                # backward compatible: nếu config cũ là templates -> lấy template đầu làm pool mặc định
                first_tpl = top10[0] if top10 and isinstance(top10[0], list) else []
                parsed_pool = self._reward_items_from_text(self._reward_items_to_text(first_tpl))
                if parsed_pool:
                    self.top10_bonus_pool_items = parsed_pool
            try:
                sec_i = int(sec) if sec is not None else self.online60_reward_seconds
                if sec_i >= 60:
                    self.online60_reward_seconds = sec_i
            except Exception:
                pass
        except Exception:
            pass

    def _save_reward_templates_to_cfg(self) -> bool:
        try:
            data = self._settings_load_manager_config() or {}
            data["NEWBIE_GIFT_TEMPLATE"] = self.newbie_gift_template
            data["DAILY_CHECKIN_REWARD_ITEMS"] = self.daily_checkin_reward_items
            data["ONLINE60_REWARD_ITEMS"] = self.online60_reward_items
            data["ONLINE60_REWARD_SECONDS"] = int(self.online60_reward_seconds)
            data["TOP10_BONUS_POOL_ITEMS"] = self.top10_bonus_pool_items
            return self._settings_save_manager_config(data)
        except Exception:
            return False

    def _build_item_payload(self, items: list) -> dict:
        return {"Item": list(items or [])}

    def _give_bundle_pdapi(self, steamid: str, player_name: str, payload: dict, title: str, log_fn=None) -> bool:
        """Phát quà theo chuẩn tab quà tân thủ: ưu tiên PD API, fallback RCON item."""
        if log_fn is None:
            log_fn = self._log_gift
        for _ in range(2):
            ok, _ = self._pdapi_give(steamid, payload)
            if ok:
                log_fn(f"🎁 {title}: đã phát cho {player_name or steamid}")
                return True
            time.sleep(0.3)
        # Fallback: thử phát từng item qua RCON để giảm rủi ro lệch API.
        playerid = self._steamid_to_playerid.get(steamid, "")
        steam_number = steamid.replace("steam_", "") if steamid.startswith("steam_") else steamid
        items = list((payload or {}).get("Item", []) or [])
        if not items:
            self._log_gift(f"❌ {title}: phát thất bại cho {player_name or steamid}")
            return False
        ok_count = 0
        for it in items:
            iid = str(it.get("ItemID", "") or "").strip()
            cnt = int(it.get("Count", 0) or 0)
            if not iid or cnt <= 0:
                continue
            ok = self._rcon_give_item(playerid, steam_number, steamid, iid, cnt)
            log_fn(f"{'✅' if ok else '❌'} {title} fallback RCON: {iid} x{cnt}")
            if ok:
                ok_count += 1
        if ok_count >= max(1, int(len(items) * 0.8)):
            log_fn(f"🎁 {title}: fallback RCON thành công {ok_count}/{len(items)} cho {player_name or steamid}")
            return True
        log_fn(f"❌ {title}: thất bại sau PD API + RCON fallback cho {player_name or steamid}")
        return False

    def _give_bundle_newbie_style(self, steamid: str, player_name: str, items: list, title: str, log_fn=None) -> bool:
        """Phát quà giống cơ chế quà tân thủ: RCON từng item là chính, fallback PD API."""
        if log_fn is None:
            log_fn = self._log_gift
        sid = self._normalize_steamid(steamid)
        if not sid:
            return False
        playerid = self._steamid_to_playerid.get(sid, "")
        steam_number = sid.replace("steam_", "") if sid.startswith("steam_") else sid

        valid_items = []
        for it in (items or []):
            iid = str(it.get("ItemID", "")).strip()
            cnt = int(it.get("Count", 0) or 0)
            if iid and cnt > 0:
                valid_items.append({"ItemID": iid, "Count": cnt})
        if not valid_items:
            log_fn(f"❌ {title}: danh sách item rỗng.")
            return False

        ok_count = 0
        for it in valid_items:
            iid = it["ItemID"]
            cnt = it["Count"]
            ok = self._rcon_give_item(playerid, steam_number, sid, iid, cnt)
            log_fn(f"{'✅' if ok else '❌'} {title}: {iid} x{cnt} (RCON)")
            if ok:
                ok_count += 1

        # Chuẩn giống tân thủ: >=80% coi là đạt
        if ok_count >= max(1, int(len(valid_items) * 0.8)):
            log_fn(f"🎁 {title}: thành công {ok_count}/{len(valid_items)} (RCON).")
            return True

        # Fallback PD API để cứu trường hợp RCON miss cục bộ.
        payload = {"Item": valid_items}
        ok_api = self._give_bundle_pdapi(sid, player_name, payload, f"{title} [fallback API]", log_fn=log_fn)
        if ok_api:
            log_fn(f"🎁 {title}: RCON chưa đủ, API fallback đã xử lý.")
            return True
        log_fn(f"❌ {title}: thất bại (RCON {ok_count}/{len(valid_items)} + API fallback fail).")
        return False

    def _try_daily_checkin_reward(self, steamid: str, player_name: str):
        sid = self._normalize_steamid(steamid)
        if not sid:
            return
        today = datetime.date.today().isoformat()
        claimed = set(self.daily_checkin_claims.get(today, []))
        if sid in claimed:
            return
        ok = self._give_bundle_newbie_style(
            sid, player_name, self.daily_checkin_reward_items, "Điểm danh hằng ngày", log_fn=self._log_daily_gift
        )
        if ok:
            claimed.add(sid)
            self.daily_checkin_claims[today] = sorted(claimed)
            self._save_daily_checkin_tracking()
            self._enqueue_console(f"📅 Điểm danh: {player_name or sid} nhận quà ngày {today}.")
            # Clear retry nếu có
            self._daily_retry_state.pop(sid, None)
        else:
            st = self._daily_retry_state.get(sid, {"attempts": 0, "next_ts": 0.0})
            if st["attempts"] < 5:
                st["attempts"] += 1
                st["next_ts"] = time.time() + 60
                self._daily_retry_state[sid] = st
                self._log_daily_gift(f"⏳ Điểm danh: sẽ thử lại lần {st['attempts']}/5 sau 60s cho {player_name or sid}.")
            else:
                self._log_daily_gift(f"❌ Điểm danh: đã thử 5 lần vẫn thất bại cho {player_name or sid}.")

    def _tick_online60_reward(self, steamid: str, player_name: str, now_ts: float):
        sid = self._normalize_steamid(steamid)
        if not sid:
            return
        st = self.online60_reward_state.setdefault(sid, {"accum_sec": 0.0, "last_seen": now_ts})
        last_seen = float(st.get("last_seen", now_ts) or now_ts)
        delta = max(0.0, now_ts - last_seen)
        st["last_seen"] = now_ts
        st["accum_sec"] = float(st.get("accum_sec", 0.0) or 0.0) + delta

        if st["accum_sec"] < float(self.online60_reward_seconds):
            return
        ok = self._give_bundle_newbie_style(
            sid, player_name, self.online60_reward_items, "Quà online 60 phút", log_fn=self._log_online_gift
        )
        if ok:
            st["accum_sec"] -= float(self.online60_reward_seconds)
            self._save_online60_tracking()
            self._enqueue_console(f"⏱️ Quà 60 phút: {player_name or sid} đã nhận 1 lượt.")
            self._online_retry_state.pop(sid, None)
        else:
            rs = self._online_retry_state.get(sid, {"attempts": 0, "next_ts": 0.0})
            if rs["attempts"] < 5:
                rs["attempts"] += 1
                rs["next_ts"] = time.time() + 60
                self._online_retry_state[sid] = rs
                self._log_online_gift(f"⏳ Online60: sẽ thử lại lần {rs['attempts']}/5 sau 60s cho {player_name or sid}.")
            else:
                self._log_online_gift(f"❌ Online60: đã thử 5 lần vẫn thất bại cho {player_name or sid}.")

    def _mark_online60_leave(self, steamid: str):
        sid = self._normalize_steamid(steamid)
        if not sid:
            return
        st = self.online60_reward_state.get(sid)
        if not st:
            return
        st["last_seen"] = 0.0
        self._save_online60_tracking()

    def _write_gift_log_file(self, steamid: str, name: str, playerid: str,
                              success: bool, success_count: int, total: int,
                              item_results: list):
        """Ghi log chi tiết vào newbie_gift_log.txt."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)  # đảm bảo thư mục tồn tại
            ts     = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = ("✅ THÀNH CÔNG" if success
                      else f"⚠️ PHẦN LỚN ({success_count}/{total})"
                      if success_count >= total * 0.8
                      else "❌ THẤT BẠI")
            lines = [
                "=" * 62,
                f"[{ts}]  {status}",
                f"  Tên ingame : {name or '(không rõ)'}",
                f"  SteamID    : {steamid}",
                f"  PlayerID   : {playerid or '(không có)'}",
                f"  Kết quả    : {success_count}/{total} item thành công",
                f"  Chi tiết   :",
            ]
            for r in item_results:
                lines.append(f"    {r}")
            lines.append("")
            with open(self.newbie_gift_log_file, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi ghi gift log file: {e}")

    # ─────────────────────────────────────────
    #  GIVE NEWBIE GIFT
    # ─────────────────────────────────────────
    def _give_newbie_gift(self, steamid: str, player_name: str = ""):
        """Phát toàn bộ quà tân thủ cho người chơi qua RCON."""
        if steamid in self.newbie_gift_received:
            self._enqueue_console(f"⚠️ {player_name or steamid} đã nhận quà rồi, bỏ qua.")
            return False

        playerid     = self._steamid_to_playerid.get(steamid, "")
        steam_number = steamid.replace("steam_", "") if steamid.startswith("steam_") else steamid
        tag          = player_name or steamid

        if not playerid:
            self._enqueue_console(f"⚠️ Không có playerId cho {tag}, thử steam_number...")

        gifts = []
        for g in self.newbie_gift_template:
            typ = str(g.get("Type", "item")).lower().strip()
            gid = str(g.get("ID", "")).strip()
            cnt = int(g.get("Count", 0) or 0)
            if typ in ("item", "pal") and gid and cnt > 0:
                gifts.append((typ, gid, cnt))
        if not gifts:
            self._enqueue_console("❌ Quà tân thủ đang trống hoặc sai định dạng.")
            return False

        success_count = 0
        item_results  = []

        for gift_type, gift_id, qty in gifts:
            if gift_type == "pal":
                ok    = self._rcon_give_pal(playerid, steam_number, steamid, gift_id, level=qty)
                label = f"🐾 PAL  {gift_id} lv{qty}"
            else:
                ok    = self._rcon_give_item(playerid, steam_number, steamid, gift_id, qty)
                label = f"📦 ITEM {gift_id} x{qty}"

            if ok:
                success_count += 1
                item_results.append(f"✅ {label}")
            else:
                item_results.append(f"❌ {label}")

        ts_ui      = datetime.datetime.now().strftime("%H:%M:%S")
        overall_ok = (success_count == len(gifts) or success_count >= len(gifts) * 0.8)

        if overall_ok:
            self._save_newbie_gift_tracking(steamid)
            if success_count == len(gifts):
                msg = f"✅ Đã phát đủ quà tân thủ cho {tag} ({steamid})"
            else:
                msg = (f"✅ Phát quà tân thủ {success_count}/{len(gifts)} cho {tag} ({steamid}) "
                       f"— thiếu: {[r for r in item_results if r.startswith('❌')]}")
            self._enqueue_console(msg)
            self._log_gift(msg)
            self.send_ingame_broadcast(f"🎁 {player_name or 'Người chơi mới'} đã nhận quà tân thủ!")
            self._write_gift_log_file(steamid, player_name, playerid, True,
                                      success_count, len(gifts), item_results)
            return True
        else:
            msg = (f"❌ Phát quà tân thủ thất bại cho {tag} ({steamid}). "
                   f"Thành công: {success_count}/{len(gifts)}")
            self._enqueue_console(msg)
            self._log_gift(msg)
            self._write_gift_log_file(steamid, player_name, playerid, False,
                                      success_count, len(gifts), item_results)
            return False

    # ─────────────────────────────────────────
    #  NEWBIE GIFT MONITOR (background thread)
    # ─────────────────────────────────────────
    def newbie_gift_monitor(self):
        """Theo dõi người chơi mới và phát quà sau newbie_gift_wait_sec giây."""
        while True:
            try:
                if not self.newbie_gift_auto.get():
                    time.sleep(5)
                    continue

                res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if res.status_code != 200:
                    time.sleep(5)
                    continue

                players    = res.json().get("players", [])
                online_ids = set()

                for p in players:
                    steamid  = self._normalize_steamid(p.get("userId", ""))
                    playerid = p.get("playerId", "")
                    name     = p.get("name", "Unknown")
                    now_ts   = time.time()

                    # Cập nhật cache
                    if steamid and playerid:
                        self._steamid_to_playerid[steamid] = playerid
                    if steamid:
                        self._steamid_to_name[steamid] = name

                    if not steamid:
                        # SteamID chưa resolve → theo dõi qua playerId
                        if playerid:
                            online_ids.add(f"pid:{playerid}")
                            if playerid not in self._pending_no_steamid:
                                self._pending_no_steamid[playerid] = {"name": name, "since": now_ts}
                        continue

                    online_ids.add(steamid)

                    # Kiểm tra nếu đang pending (từ lần trước chưa có steamid)
                    if playerid and playerid in self._pending_no_steamid:
                        orig_since = self._pending_no_steamid.pop(playerid)["since"]
                        if steamid not in self.newbie_gift_received and \
                           steamid not in self.newbie_gift_pending:
                            self.newbie_gift_pending[steamid] = orig_since

                    # Thêm vào pending nếu chưa nhận
                    if steamid not in self.newbie_gift_received and \
                       steamid not in self.newbie_gift_pending:
                        self.newbie_gift_pending[steamid] = now_ts
                        self._enqueue_console(
                            f"🆕 Người chơi mới: {name} ({steamid}) — đang chờ {self.newbie_gift_wait_sec}s"
                        )

                # Phát quà cho những ai đã chờ đủ giờ
                to_give = []
                for sid, login_time in list(self.newbie_gift_pending.items()):
                    if time.time() - login_time >= self.newbie_gift_wait_sec:
                        if sid in online_ids or sid in self._steamid_to_playerid:
                            to_give.append(sid)

                for sid in to_give:
                    self.newbie_gift_pending.pop(sid, None)
                    pname = self._steamid_to_name.get(sid, "")
                    threading.Thread(
                        target=self._give_newbie_gift,
                        args=(sid, pname),
                        daemon=True
                    ).start()

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout):
                # Server chưa chạy → im lặng, không spam console
                pass
            except Exception as e:
                self._enqueue_console(f"❌ Lỗi monitor quà tân thủ: {e}")

            time.sleep(5)

    # ─────────────────────────────────────────
    #  LOG HELPER (UI console của tab quà)
    # ─────────────────────────────────────────
    def _log_gift(self, message: str):
        """Ghi message vào newbie_gift_log console trong UI."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            with open(self.newbie_gift_log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass
        if hasattr(self, "newbie_gift_log") and self.newbie_gift_log.winfo_exists():
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.newbie_gift_log.insert(tk.END, f"[{ts}] {message}\n")
            self.newbie_gift_log.see(tk.END)

    def _log_daily_gift(self, message: str):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            with open(self.daily_gift_log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass
        if hasattr(self, "daily_gift_log") and self.daily_gift_log.winfo_exists():
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.daily_gift_log.insert(tk.END, f"[{ts}] {message}\n")
            self.daily_gift_log.see(tk.END)

    def _log_online_gift(self, message: str):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            with open(self.online_gift_log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass
        if hasattr(self, "online_gift_log") and self.online_gift_log.winfo_exists():
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.online_gift_log.insert(tk.END, f"[{ts}] {message}\n")
            self.online_gift_log.see(tk.END)

    def _log_ranking_bonus(self, message: str):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            with open(self.ranking_bonus_log_file, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
        except Exception:
            pass
        self._enqueue_console(message)

    def _build_top10_bonus_slots(self, slots: int = 10) -> list[dict]:
        """Chia quỹ TOP10 thành N suất: ngẫu nhiên “đều tương đối”.
        Sử dụng phân phối tỉ lệ (Dirichlet xấp xỉ bằng Gamma) để tạo độ ngẫu nhiên
        ngay cả khi total chia hết cho N.
        """
        n = max(1, int(slots or 10))
        out = [dict() for _ in range(n)]
        pool = list(self.top10_bonus_pool_items or [])
        if not pool:
            return out
        for it in pool:
            iid = str(it.get("ItemID", "")).strip()
            total = int(it.get("Count", 0) or 0)
            if not iid or total <= 0:
                continue
            # Tạo trọng số ngẫu nhiên “gần đều”: Gamma(k=3, theta=1) cho n slot
            weights = [random.gammavariate(3.0, 1.0) for _ in range(n)]
            sum_w = sum(weights) or 1.0
            # Phân bổ sơ bộ theo tỉ lệ và làm tròn xuống
            alloc = [int((w / sum_w) * total) for w in weights]
            used = sum(alloc)
            # Bù phần dư để tổng khớp total
            rem = max(0, total - used)
            if rem > 0:
                # Chọn ngẫu nhiên 'rem' slot để +1
                for idx in random.sample(range(n), rem if rem <= n else n):
                    alloc[idx] += 1
                # Nếu vẫn còn dư (rem > n), phân phối thêm vòng sau
                extra = rem - min(rem, n)
                while extra > 0:
                    step = min(extra, n)
                    for idx in random.sample(range(n), step):
                        alloc[idx] += 1
                    extra -= step
            # Ghi ra map
            for idx, amt in enumerate(alloc):
                if amt > 0:
                    out[idx][iid] = out[idx].get(iid, 0) + amt
        return out

    def _merge_item_maps(self, a: dict, b: dict) -> list[dict]:
        """Gộp 2 map item -> count thành list payload item."""
        merged = {}
        for src in (a or {}, b or {}):
            for k, v in src.items():
                try:
                    vv = int(v or 0)
                except Exception:
                    vv = 0
                if vv > 0:
                    merged[k] = merged.get(k, 0) + vv
        return [{"ItemID": k, "Count": v} for k, v in merged.items() if v > 0]

    def _merge_daily_bonus_by_same_code(self, daily_map: dict, bonus_map: dict) -> list[dict]:
        """Ghép quà top10 theo quy tắc:
        - Nếu ItemID trùng giữa daily và bonus -> cộng daily + bonus
        - Nếu không trùng -> chỉ lấy bonus (không cộng daily)
        """
        out = []
        bmap = bonus_map or {}
        dmap = daily_map or {}
        for k, v in bmap.items():
            try:
                bcnt = int(v or 0)
            except Exception:
                bcnt = 0
            if bcnt <= 0:
                continue
            dcnt = int(dmap.get(k, 0) or 0)
            total = bcnt + dcnt if dcnt > 0 else bcnt
            if total > 0:
                out.append({"ItemID": k, "Count": total})
        return out

    def _build_top10_bonus_snapshot_for_day(self, day_key: str) -> dict:
        """Chốt top20/top10 của ngày để tránh thay đổi giữa ngày."""
        ranking20 = self._get_ranking(20) or []
        top20 = [self._normalize_steamid(p.get("steamid", "")) for p in ranking20 if p.get("steamid")]
        top20 = [x for x in top20 if x]
        ranking10 = ranking20[:10]
        slots = self._build_top10_bonus_slots(10)
        slot_rows = []
        for idx, p in enumerate(ranking10):
            sid = self._normalize_steamid(p.get("steamid", ""))
            if not sid:
                continue
            slot_rows.append({"steamid": sid, "bonus": slots[idx] if idx < len(slots) else {}})
        snap = {"top20": top20, "slots": slot_rows, "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        self.ranking_bonus_daily_state[day_key] = snap
        self._save_ranking_bonus_daily_state()
        return snap

    def _award_top10_bonus_if_due(self, force_test: bool = False):
        """Top10 nhận thưởng theo công thức:
        quà cuối = quà điểm danh mặc định + bonus random chia từ quỹ top10 theo 10 suất.
        force_test=True: chạy test ngay, không ghi claim theo ngày.
        """
        now_local = datetime.datetime.now()
        # Chỉ chốt và phát sau mốc 00:00 hằng ngày.
        if (not force_test) and now_local.time() < datetime.time(0, 0):
            return {"awarded": 0, "total_top": 0}

        today = now_local.date().isoformat()
        claimed_today = set() if force_test else set(self.ranking_bonus_claims.get(today, []))

        if force_test:
            ranking20 = self._get_ranking(20) or []
            top20 = [self._normalize_steamid(p.get("steamid", "")) for p in ranking20 if p.get("steamid")]
            top20 = [x for x in top20 if x]
            ranking10 = ranking20[:10]
            slots = self._build_top10_bonus_slots(10)
            slots_rows = []
            for idx, p in enumerate(ranking10):
                sid = self._normalize_steamid(p.get("steamid", ""))
                if sid:
                    slots_rows.append({"steamid": sid, "bonus": slots[idx] if idx < len(slots) else {}})
            day_state = {"top20": top20, "slots": slots_rows}
        else:
            # Snapshot cố định theo ngày: tránh thay đổi top giữa ngày, tránh thiếu sót/trùng.
            day_state = self.ranking_bonus_daily_state.get(today) or self._build_top10_bonus_snapshot_for_day(today)

        top20_set = set(self._normalize_steamid(x) for x in day_state.get("top20", []) if self._normalize_steamid(x))
        slots_rows = list(day_state.get("slots", []) or [])
        if not slots_rows:
            return {"awarded": 0, "total_top": 0}

        # Base daily mặc định (ví dụ Money 10000) áp cho mỗi người top10.
        base_daily_map = {}
        for it in (self.daily_checkin_reward_items or []):
            iid = str(it.get("ItemID", "")).strip()
            cnt = int(it.get("Count", 0) or 0)
            if iid and cnt > 0:
                base_daily_map[iid] = base_daily_map.get(iid, 0) + cnt

        online_set = set(getattr(self, "_online_players_prev", set()) or set())
        random.shuffle(slots_rows)  # random thứ tự phát, không random tập người.
        awarded = 0
        title = "TEST TOP10 bonus" if force_test else "Thưởng TOP10 Ranking"
        for row in slots_rows:
            sid = self._normalize_steamid(row.get("steamid", ""))
            name = self._steamid_to_name.get(sid, sid)
            if not sid or sid in claimed_today:
                continue
            if sid not in top20_set:
                self._log_ranking_bonus(f"⛔ TOP10 bonus: bỏ {name} vì không thuộc top20 snapshot ngày {today}.")
                continue
            if sid not in online_set:
                self._log_ranking_bonus(f"⏭️ TOP10 bonus: {name} offline, bỏ qua lượt này.")
                continue
            bonus_items = self._merge_daily_bonus_by_same_code(base_daily_map, row.get("bonus", {}))
            if not bonus_items:
                self._log_ranking_bonus(f"⏭️ TOP10 bonus: {name} không có suất item hợp lệ.")
                continue
            ok = self._give_bundle_newbie_style(
                sid, name, bonus_items, title, log_fn=self._log_ranking_bonus
            )
            if ok:
                claimed_today.add(sid)
                awarded += 1
                bonus_txt = ", ".join(f"{it.get('ItemID')}x{it.get('Count')}" for it in bonus_items)
                self._log_ranking_bonus(f"   ↳ {name} nhận bonus: {bonus_txt}")

        if awarded > 0 and not force_test:
            self.ranking_bonus_claims[today] = sorted(claimed_today)
            self._save_ranking_bonus_claims()
            self._log_ranking_bonus(f"🏆 Bonus TOP10: đã phát cho {awarded} người trong ngày {today}.")
        elif force_test:
            self._log_ranking_bonus(f"🧪 TEST TOP10 xong: phát thành công {awarded}/{len(slots_rows)} người.")
        return {"awarded": awarded, "total_top": len(slots_rows)}

    def _save_all_gift_tabs_config(self):
        newbie = self._newbie_template_from_text(self._newbie_reward_text.get("1.0", tk.END))
        daily = self._reward_items_from_text(self._daily_reward_text.get("1.0", tk.END))
        online = self._reward_items_from_text(self._online_reward_text.get("1.0", tk.END))
        if not newbie or not daily or not online:
            messagebox.showwarning("Quà tặng", "Một trong các tab quà đang trống hoặc sai định dạng.")
            return
        try:
            mins = max(1, int(self._online60_minutes_var.get().strip()))
        except Exception:
            mins = 60
        self.newbie_gift_template = newbie
        self.daily_checkin_reward_items = daily
        self.online60_reward_items = online
        self.online60_reward_seconds = mins * 60
        if self._save_reward_templates_to_cfg():
            self._enqueue_console(f"✅ Đã lưu cấu hình quà: newbie/daily/online, mốc online {mins} phút.")
            messagebox.showinfo("Quà tặng", "Đã lưu cấu hình quà cho cả 3 tab.")
        else:
            messagebox.showerror("Quà tặng", "Không lưu được cấu hình.")

    def _gift_retry_loop(self):
        """Background: thử lại phát quà (điểm danh/online) mỗi 5s, khi tới hạn thì attempt.
        Mỗi mục tối đa 5 lần, cách nhau 60s — giống cơ chế tân thủ."""
        while True:
            now = time.time()
            try:
                # Daily check-in retries
                for sid, st in list(self._daily_retry_state.items()):
                    if now >= float(st.get("next_ts", 0)):
                        name = self._steamid_to_name.get(sid, sid)
                        ok = self._give_bundle_newbie_style(
                            sid, name, self.daily_checkin_reward_items, "Điểm danh hằng ngày (retry)", log_fn=self._log_daily_gift
                        )
                        if ok:
                            today = datetime.date.today().isoformat()
                            claimed = set(self.daily_checkin_claims.get(today, []))
                            claimed.add(sid)
                            self.daily_checkin_claims[today] = sorted(claimed)
                            self._save_daily_checkin_tracking()
                            self._daily_retry_state.pop(sid, None)
                        else:
                            if st.get("attempts", 0) >= 5:
                                self._log_daily_gift(f"❌ Điểm danh (retry): đã đủ 5 lần — dừng cho {name}.")
                                self._daily_retry_state.pop(sid, None)
                            else:
                                st["attempts"] = int(st.get("attempts", 0)) + 1
                                st["next_ts"] = now + 60
                                self._daily_retry_state[sid] = st

                # Online 60 retries
                for sid, rs in list(self._online_retry_state.items()):
                    if now >= float(rs.get("next_ts", 0)):
                        name = self._steamid_to_name.get(sid, sid)
                        ok = self._give_bundle_newbie_style(
                            sid, name, self.online60_reward_items, "Quà online 60 phút (retry)", log_fn=self._log_online_gift
                        )
                        if ok:
                            st = self.online60_reward_state.setdefault(sid, {"accum_sec": 0.0, "last_seen": now})
                            st["accum_sec"] = max(0.0, float(st.get("accum_sec", 0.0)) - float(self.online60_reward_seconds))
                            self._save_online60_tracking()
                            self._online_retry_state.pop(sid, None)
                        else:
                            if rs.get("attempts", 0) >= 5:
                                self._log_online_gift(f"❌ Online60 (retry): đã đủ 5 lần — dừng cho {name}.")
                                self._online_retry_state.pop(sid, None)
                            else:
                                rs["attempts"] = int(rs.get("attempts", 0)) + 1
                                rs["next_ts"] = now + 60
                                self._online_retry_state[sid] = rs
            except Exception:
                pass
            time.sleep(5)

    def _save_online_reward_config_only(self):
        """Lưu riêng cấu hình quà online vào manager_config.json."""
        online = self._reward_items_from_text(self._online_reward_text.get("1.0", tk.END))
        if not online:
            messagebox.showwarning("Quà online", "Danh sách quà online trống hoặc sai định dạng.")
            return
        try:
            mins = max(1, int(self._online60_minutes_var.get().strip()))
        except Exception:
            mins = 60
        self.online60_reward_items = online
        self.online60_reward_seconds = mins * 60
        if self._save_reward_templates_to_cfg():
            self._enqueue_console(f"✅ Đã lưu RIÊNG cấu hình quà online: {mins} phút/lượt.")
            messagebox.showinfo(
                "Quà online",
                "Đã cập nhật vào manager_config.json:\n"
                "• ONLINE60_REWARD_ITEMS\n"
                "• ONLINE60_REWARD_SECONDS"
            )
        else:
            messagebox.showerror("Quà online", "Không lưu được cấu hình quà online.")

    # ─────────────────────────────────────────
    #  TEST FUNCTIONS
    # ─────────────────────────────────────────
    def _pick_online_player_for_gift_test(self):
        """Chọn người chơi cụ thể để test quà theo tên/steamid (fallback người đầu tiên)."""
        try:
            res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
            players = res.json().get("players", []) if res.status_code == 200 else []
        except Exception:
            players = []
        if not players:
            messagebox.showwarning("Gift Test", "Không có người chơi online!")
            return None

        preview = ", ".join(str(p.get("name", "?")) for p in players[:8])
        q = simpledialog.askstring(
            "Chọn người chơi test",
            "Nhập TÊN hoặc STEAMID để test đúng người.\n"
            "Để trống = chọn người đầu tiên online.\n\n"
            f"Online: {preview}",
        )
        q_l = (q or "").strip().lower()
        picked = players[0]
        if q_l:
            exact = None
            partial = None
            for p in players:
                sid = self._normalize_steamid(p.get("userId", ""))
                name = str(p.get("name", "")).strip()
                if sid and (q_l == sid.lower()):
                    exact = p
                    break
                if q_l == name.lower():
                    exact = p
                    break
                if q_l in name.lower() and partial is None:
                    partial = p
            picked = exact or partial or players[0]

        steamid = self._normalize_steamid(picked.get("userId", ""))
        playerid = picked.get("playerId", "")
        name = picked.get("name", "Unknown")
        if steamid and playerid:
            self._steamid_to_playerid[steamid] = playerid
        if steamid:
            self._steamid_to_name[steamid] = name
        if not steamid:
            messagebox.showwarning("Gift Test", f"Người chơi {name} chưa có SteamID hợp lệ!")
            return None
        return {"steamid": steamid, "playerid": playerid, "name": name}

    def test_gift_second_time(self):
        """TEST 1: Kiểm tra xem người chơi CÓ THỂ nhận quà lần 2 không."""
        p = self._pick_online_player_for_gift_test()
        if not p:
            return
        steamid = p["steamid"]
        name = p["name"]

        if steamid not in self.newbie_gift_received:
            ans = messagebox.askyesno("TEST 1",
                f"Người chơi {name} ({steamid}) CHƯA nhận quà.\n"
                f"Thử phát quà lần đầu (giả lập monitor) không?")
            if ans:
                self._log_gift(f"🧪 TEST 1: Phát quà lần đầu cho {name} ({steamid})...")
                threading.Thread(target=self._give_newbie_gift, args=(steamid, name), daemon=True).start()
            return

        ans = messagebox.askyesno("TEST 1 - Xác nhận",
            f"Người chơi {name} ({steamid}) ĐÃ nhận quà.\n\n"
            f"Tạm xóa khỏi tracking để thử phát lần 2?\n"
            f"(Sẽ TỰ ĐỘNG khôi phục sau khi test xong)")
        if not ans:
            return

        self._log_gift(f"🧪 TEST 1 BẮT ĐẦU: Tạm xóa {name} ({steamid}) khỏi tracking...")
        self.newbie_gift_received.discard(steamid)

        def _do_test():
            ok = self._give_newbie_gift(steamid, name)
            # Khôi phục tracking dù kết quả thế nào
            self.newbie_gift_received.add(steamid)
            result = "✅ THÀNH CÔNG — có thể nhận lần 2" if ok else "❌ THẤT BẠI — RCON lỗi"
            self._log_gift(f"🧪 TEST 1 KẾT QUẢ: {result}")
            self._log_gift(f"   Tracking đã khôi phục cho {steamid}")
            messagebox.showinfo("TEST 1 - Kết quả", f"Kết quả: {result}")

        threading.Thread(target=_do_test, daemon=True).start()

    def test_gift_give_all(self):
        """TEST 2: Give toàn bộ item quà tân thủ và kiểm tra từng item."""
        p = self._pick_online_player_for_gift_test()
        if not p:
            return
        steamid = p["steamid"]
        playerid = p["playerid"]
        name = p["name"]

        already = steamid in self.newbie_gift_received
        ans = messagebox.askyesno("TEST 2 - Xác nhận",
            f"Phát TOÀN BỘ quà tân thủ cho:\n"
            f"  Tên    : {name}\n"
            f"  Steam  : {steamid}\n"
            f"  Player : {playerid or '(chưa có)'}\n\n"
            f"{'⚠️ Người chơi NÀY ĐÃ nhận quà trước đó!' if already else '🆕 Người chơi chưa nhận quà.'}\n"
            f"Tiếp tục?")
        if not ans:
            return

        self._log_gift(f"🎁 TEST 2 BẮT ĐẦU: Give toàn bộ cho {name} | steam={steamid} | pid={playerid}")

        def _do_test():
            steam_number = steamid.replace("steam_", "") if steamid.startswith("steam_") else steamid
            gifts = [
                ("pal",  "FengyunDeeper_Electric",           1),
                ("item", "SkillUnlock_FengyunDeeper_Electric", 1),
                ("item", "Accessory_HeatColdResist_3",        1),
                ("item", "Spear_ForestBoss_5",                1),
                ("item", "PalSphere",                         10),
            ]
            results = []
            ok_count = 0
            for gift_type, gift_id, qty in gifts:
                if gift_type == "pal":
                    ok    = self._rcon_give_pal(playerid, steam_number, steamid, gift_id, level=qty)
                    label = f"🐾 PAL  {gift_id} lv{qty}"
                else:
                    ok    = self._rcon_give_item(playerid, steam_number, steamid, gift_id, qty)
                    label = f"📦 ITEM {gift_id} x{qty}"
                ico = "✅" if ok else "❌"
                results.append(f"{ico} {label}")
                if ok:
                    ok_count += 1
                self._log_gift(f"  {ico} {label}")

            summary = f"{ok_count}/{len(gifts)} thành công"
            self._log_gift(f"🎁 TEST 2 KẾT QUẢ: {summary}")
            self._write_gift_log_file(steamid, name, playerid,
                                      ok_count == len(gifts), ok_count, len(gifts), results)
            if not already and ok_count >= len(gifts) * 0.8:
                self._save_newbie_gift_tracking(steamid)
                self._log_gift(f"   ✅ Đã lưu {steamid} vào tracking")

            detail = "\n".join(results)
            messagebox.showinfo("TEST 2 - Kết quả", f"Kết quả {summary}:\n\n{detail}")

        threading.Thread(target=_do_test, daemon=True).start()

    def test_daily_checkin_specific(self):
        """TEST 3: Phát quà điểm danh cho người chơi cụ thể (bỏ qua trạng thái đã nhận trong ngày)."""
        p = self._pick_online_player_for_gift_test()
        if not p:
            return
        sid = p["steamid"]
        name = p["name"]
        ans = messagebox.askyesno(
            "TEST 3 - Điểm danh",
            f"Phát TEST quà điểm danh cho:\n  {name} ({sid})\n\n"
            "Lưu ý: đây là test thủ công, có thể cấp thêm quà ngoài lượt điểm danh tự động."
        )
        if not ans:
            return
        threading.Thread(
            target=lambda: self._give_bundle_newbie_style(
                sid, name, self.daily_checkin_reward_items, "TEST Điểm danh hằng ngày", log_fn=self._log_daily_gift
            ),
            daemon=True
        ).start()

    def test_online60_specific(self):
        """TEST 4: Phát quà online 60 phút cho người chơi cụ thể."""
        p = self._pick_online_player_for_gift_test()
        if not p:
            return
        sid = p["steamid"]
        name = p["name"]
        ans = messagebox.askyesno(
            "TEST 4 - Online 60 phút",
            f"Phát TEST quà online 60 phút cho:\n  {name} ({sid})\n\n"
            "Lưu ý: đây là test thủ công, không cần đủ 60 phút."
        )
        if not ans:
            return
        threading.Thread(
            target=lambda: self._give_bundle_newbie_style(
                sid, name, self.online60_reward_items, "TEST Quà online 60 phút", log_fn=self._log_online_gift
            ),
            daemon=True
        ).start()

    def test_top10_bonus_now(self):
        """TEST 5: Chạy ngay thưởng Top10 bonus chia đều ngẫu nhiên (không ghi claim ngày)."""
        ans = messagebox.askyesno(
            "TEST 5 - TOP10 Bonus",
            "Chạy TEST TOP10 bonus ngay bây giờ?\n\n"
            "- Chỉ phát cho người trong TOP10 đang online\n"
            "- Chia quỹ top10 theo 10 suất (ngẫu nhiên phần dư)\n"
            "- Không ghi claim theo ngày (chế độ test)"
        )
        if not ans:
            return

        def _do():
            rs = self._award_top10_bonus_if_due(force_test=True) or {}
            self._log_ranking_bonus(
                f"🧪 TEST TOP10: kết quả {rs.get('awarded', 0)}/{rs.get('total_top', 0)} người nhận."
            )

        threading.Thread(target=_do, daemon=True).start()

    # ─────────────────────────────────────────
    #  LOG FILE HELPERS
    # ─────────────────────────────────────────
    def _refresh_gift_stats(self):
        """Cập nhật stats label mỗi 3 giây."""
        try:
            if hasattr(self, "_lbl_gift_stat_received") and \
               self._lbl_gift_stat_received.winfo_exists():
                self._lbl_gift_stat_received.config(
                    text=f"✅ Đã phát: {len(self.newbie_gift_received)} người")
                self._lbl_gift_stat_pending.config(
                    text=f"⏳ Đang chờ: {len(self.newbie_gift_pending)} người")
                self.root.after(3000, self._refresh_gift_stats)
        except Exception:
            pass

    def _open_gift_log_file(self):
        """Mở file log chi tiết bằng Notepad (tạo file nếu chưa có)."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            if not os.path.isfile(self.newbie_gift_log_file):
                with open(self.newbie_gift_log_file, "w", encoding="utf-8") as f:
                    f.write(f"# LOG QUÀ TÂN THỦ - MANAGER SERVERPAL\n")
                    f.write(f"# Tạo lúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            os.startfile(self.newbie_gift_log_file)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở file log: {e}")

    def _open_any_log_file(self, path: str, title: str = "LOG"):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            if not os.path.isfile(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n# Tạo lúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở file log: {e}")

    def _open_gift_log_folder(self):
        """Mở Explorer tại thư mục quatanthu, highlight file log."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            if os.path.isfile(self.newbie_gift_log_file):
                subprocess.Popen(f'explorer /select,"{self.newbie_gift_log_file}"')
            else:
                subprocess.Popen(f'explorer "{GIFT_SAVE_DIR}"')
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}")

    def _load_gift_log_to_ui(self):
        """Tải 200 dòng cuối của file log vào console UI."""
        if not hasattr(self, "newbie_gift_log"):
            return
        try:
            if not os.path.isfile(self.newbie_gift_log_file):
                self.newbie_gift_log.insert(tk.END, "(Chưa có lịch sử phát quà)\n")
                return
            with open(self.newbie_gift_log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-200:] if len(lines) > 200 else lines
            self.newbie_gift_log.delete("1.0", tk.END)
            if len(lines) > 200:
                self.newbie_gift_log.insert(
                    tk.END,
                    f"--- (hiển thị 200 dòng cuối / tổng {len(lines)} dòng) ---\n\n"
                )
            for line in tail:
                self.newbie_gift_log.insert(tk.END, line)
            self.newbie_gift_log.see(tk.END)
        except Exception as e:
            self.newbie_gift_log.insert(tk.END, f"❌ Lỗi đọc log: {e}\n")

    def _load_any_log_to_ui(self, path: str, target_widget):
        if not target_widget or not target_widget.winfo_exists():
            return
        try:
            if not os.path.isfile(path):
                target_widget.delete("1.0", tk.END)
                target_widget.insert(tk.END, "(Chưa có lịch sử)\n")
                return
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-200:] if len(lines) > 200 else lines
            target_widget.delete("1.0", tk.END)
            if len(lines) > 200:
                target_widget.insert(tk.END, f"--- (200 dòng cuối / tổng {len(lines)} dòng) ---\n\n")
            for line in tail:
                target_widget.insert(tk.END, line)
            target_widget.see(tk.END)
        except Exception as e:
            target_widget.insert(tk.END, f"❌ Lỗi đọc log: {e}\n")

    # ─────────────────────────────────────────
    #  PLAYER TREE REFRESH
    # ─────────────────────────────────────────
    def _refresh_players_tree(self):
        """Lấy dữ liệu players từ API, cập nhật cache và rebuild tree."""
        if not hasattr(self, "player_tree") or not self.player_tree.winfo_exists():
            return
        try:
            res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
            if res.status_code != 200:
                return
            players = res.json().get("players", [])
            # Cập nhật steamid → playerid và level cache
            for p in players:
                sid = self._normalize_steamid(p.get("userId", ""))
                pid = p.get("playerId", "")
                if sid and pid:
                    self._steamid_to_playerid[sid] = pid
                if sid:
                    lv = int(p.get("level") or 0)
                    if lv > 0:
                        self._player_level_cache[sid] = lv
            # Lưu cache
            self._all_players_data = players
            # Cập nhật label số lượng
            count = len(players)
            if hasattr(self, "_lbl_player_count") and \
               self._lbl_player_count.winfo_exists():
                if count > 0:
                    self._lbl_player_count.config(
                        text=f"  ⬤ {count} online", fg="#00ff88")
                else:
                    self._lbl_player_count.config(
                        text="  ⬤ 0 online", fg="#555")
            # Rebuild tree (áp dụng filter + sort hiện tại)
            self._filter_player_tree()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            # Server chưa chạy → im lặng
            pass
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi refresh players: {e}")
        # Auto-refresh
        try:
            if self.player_tree.winfo_exists() and \
               getattr(self, "_player_auto_var",
                       tk.BooleanVar(value=True)).get():
                self.root.after(8000, self._refresh_players_tree)
        except Exception:
            pass

    def _filter_player_tree(self):
        """Lọc + rebuild Treeview từ cache, áp dụng search + sort."""
        if not hasattr(self, "player_tree") or not self.player_tree.winfo_exists():
            return
        query    = getattr(self, "_player_filter_var",
                           tk.StringVar()).get().lower().strip()
        sort_col = getattr(self, "_player_sort_col", "Lv")
        sort_rev = getattr(self, "_player_sort_rev", True)
        data     = list(getattr(self, "_all_players_data", []))

        # Filter
        if query:
            data = [
                p for p in data
                if query in p.get("name", "").lower()
                or query in self._normalize_steamid(
                    p.get("userId", "")).lower()
            ]

        # Sort
        _sort_key = {
            "Lv":   lambda p: int(p.get("level") or 0),
            "Tên":  lambda p: p.get("name", "").lower(),
            "Ping": lambda p: float(p.get("ping") or 0),
            "#":    lambda p: 0,  # keep order
        }
        key_fn = _sort_key.get(sort_col, lambda p: p.get("name", "").lower())
        data.sort(key=key_fn, reverse=sort_rev)

        self.player_tree.delete(*self.player_tree.get_children())
        self._players_by_iid.clear()

        for idx, p in enumerate(data, 1):
            name     = p.get("name", "Unknown")
            steamid  = self._normalize_steamid(p.get("userId", ""))
            playerid = p.get("playerId", "")
            level    = int(p.get("level") or 0)
            ping_raw = p.get("ping", "")
            ip_raw   = p.get("ip", "")

            try:
                ping_disp = f"{float(ping_raw):.0f}" if ping_raw != "" else "—"
            except Exception:
                ping_disp = str(ping_raw) if ping_raw else "—"

            # Level badge + color tag
            lv_tag = ("lv_max"  if level >= 50 else
                      "lv_high" if level >= 35 else
                      "lv_mid"  if level >= 20 else
                      "lv_new")
            lv_disp = f"Lv.{level}" if level > 0 else "—"

            iid = self.player_tree.insert(
                "", tk.END,
                values=(idx, name, lv_disp, ping_disp,
                        steamid or "⏳", playerid or "⏳", ip_raw or "—"),
                tags=(lv_tag,)
            )
            self._players_by_iid[iid] = p

    # ── Player tab helpers ─────────────────────────────────────────────

    def _player_on_select(self, event=None):
        """Cập nhật action panel khi chọn một player."""
        sel = self.player_tree.selection()
        if not sel:
            return
        p     = self._players_by_iid.get(sel[0], {})
        name  = p.get("name", "?")
        level = int(p.get("level") or 0)
        sid   = self._normalize_steamid(p.get("userId", ""))
        loc_x = p.get("location_x")
        loc_y = p.get("location_y")
        coord_txt = ""
        if loc_x is not None and loc_y is not None:
            coord_txt = f"   📍 ({loc_x:.0f}, {loc_y:.0f})"
        lv_color = ("#ffcc00" if level >= 50 else
                    "#4499ff" if level >= 35 else
                    "#00cc88" if level >= 20 else "#888")
        self._lbl_selected_player.config(
            text=f"▶  {name}   Lv.{level}   •   {sid}{coord_txt}",
            fg=lv_color
        )

    def _player_get_selected(self):
        """Trả về dict của player đang được chọn, hoặc None."""
        sel = self.player_tree.selection()
        if not sel:
            return None
        return self._players_by_iid.get(sel[0])

    def _player_kick_selected(self):
        p = self._player_get_selected()
        if not p:
            messagebox.showwarning("Kick", "Chọn người chơi trong danh sách trước!")
            return
        name = p.get("name", "?")
        sid  = self._normalize_steamid(p.get("userId", ""))
        lv   = int(p.get("level") or 0)
        if not sid:
            messagebox.showerror("Kick", "Không tìm thấy SteamID!")
            return
        if not messagebox.askyesno(
                "⚡ Kick Confirmation",
                f"Kick người chơi:\n\n  {name}  (Lv.{lv})\n  {sid}\n\nXác nhận?"):
            return

        def _do():
            ok, code = self._api_kick(sid, "Kicked by admin")
            self._enqueue_console(
                f"{'✅' if ok else '❌'} KICK {name} [{sid}] — HTTP {code}")
        threading.Thread(target=_do, daemon=True).start()

    def _player_ban_selected(self, source: str = "PLAYER_TAB"):
        p = self._player_get_selected()
        if not p:
            messagebox.showwarning("Ban", "Chọn người chơi trước!")
            return
        name = p.get("name", "?")
        sid  = self._normalize_steamid(p.get("userId", ""))
        lv   = int(p.get("level") or 0)
        if not sid:
            messagebox.showerror("Ban", "Không tìm thấy SteamID!")
            return
        reason = simpledialog.askstring(
            "⛔ Ban Player",
            f"Lý do ban {name} (Lv.{lv})?\n{sid}",
            initialvalue="Admin ban"
        )
        if reason is None:
            return

        def _do():
            ok, code = self._api_ban(sid, reason)
            ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            api_status = f"✅ Đã Xác Minh ✅ {code}" if ok else f"❌ HTTP {code}"

            # Ghi chung vào banlist.txt để đồng bộ với luồng AntiBug/Unban.
            try:
                with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                    f.write(
                        f"\n{'─'*60}\n"
                        f"  [BAN — MANUAL]  {ts_now}\n"
                        f"  Name         : {name}\n"
                        f"  SteamID      : {sid}\n"
                        f"  Level        : {lv}\n"
                        f"  Reason       : {reason}\n"
                        f"  Source       : {source}\n"
                        f"  API Ban      : {api_status}\n"
                        f"{'─'*60}\n\n"
                    )
            except Exception as e:
                self._enqueue_console(f"❌ Lỗi ghi banlist.txt (manual ban): {e}")

            # Luôn gửi Discord khi ban thủ công từ tab người chơi / click phải.
            threading.Thread(
                target=self._send_antibug_discord,
                args=(f"⛔ **[BAN THỦ CÔNG]**\n"
                      f"👤 **Người chơi:** `{name}`\n"
                      f"🆔 **SteamID:** `{sid}`\n"
                      f"⭐ **Cấp độ:** `{lv}`\n"
                      f"📝 **Lý do:** `{reason}`\n"
                      f"📍 **Nguồn thao tác:** `{source}`\n"
                      f"🕐 **Thời gian:** `{ts_now}`\n"
                      f"🌐 **Kết quả thẩm phán ban:** {api_status}",),
                daemon=True
            ).start()

            self._enqueue_console(
                f"{'✅' if ok else '❌'} BAN {name} [{sid}] — HTTP {code} — Lý do: {reason} — Source: {source}")
        threading.Thread(target=_do, daemon=True).start()

    def _player_copy_steamid(self):
        p = self._player_get_selected()
        if not p:
            return
        sid = self._normalize_steamid(p.get("userId", ""))
        self.root.clipboard_clear()
        self.root.clipboard_append(sid)

    def _player_copy_playerid(self):
        p = self._player_get_selected()
        if not p:
            return
        pid = p.get("playerId", "")
        self.root.clipboard_clear()
        self.root.clipboard_append(pid)

    # ── Give Item dialog ──────────────────────────────────────────
    def _player_give_item_dialog(self):
        p = self._player_get_selected()
        if not p:
            messagebox.showwarning("Give Item", "Chọn người chơi trước!")
            return
        name = p.get("name", "?")
        sid  = self._normalize_steamid(p.get("userId", ""))
        if not sid:
            messagebox.showerror("Give Item", "Không tìm thấy SteamID!")
            return

        win = tk.Toplevel(self.root)
        win.title(f"🎁 Give Item → {name}")
        win.geometry("780x620")
        win.configure(bg="#0a0a0a")
        win.resizable(True, True)
        win.grab_set()

        # ── Header ───────────────────────────────────────────────
        hdr = tk.Frame(win, bg="#111827", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🎁  GIVE ITEM",
                 bg="#111827", fg="#00ffcc",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)
        tk.Label(hdr, text=f"→  {name}  [{sid}]",
                 bg="#111827", fg="#888",
                 font=("Segoe UI", 9)).pack(side="left")

        # ── Toolbar: search + category ────────────────────────────
        bar = tk.Frame(win, bg="#0d1117", pady=6)
        bar.pack(fill="x", padx=8)

        tk.Label(bar, text="🔍", bg="#0d1117", fg="#666",
                 font=("Segoe UI", 11)).pack(side="left")
        search_var = tk.StringVar()
        search_entry = tk.Entry(bar, textvariable=search_var,
                                bg="#1a1a2e", fg="#ccc", bd=0,
                                font=("Consolas", 10), insertbackground="#ccc",
                                width=22)
        search_entry.pack(side="left", ipady=5, padx=(4, 14))

        # Category filter
        categories = ["All"] + sorted({it[0] for it in _PW_ITEMS})
        cat_var = tk.StringVar(value="All")
        tk.Label(bar, text="Danh mục:", bg="#0d1117", fg="#888",
                 font=("Segoe UI", 9)).pack(side="left")
        cat_cb = ttk.Combobox(bar, textvariable=cat_var,
                              values=categories, state="readonly",
                              width=14, font=("Segoe UI", 9))
        cat_cb.pack(side="left", padx=(4, 0), ipady=3)

        # ── Item list (Treeview) ──────────────────────────────────
        list_f = tk.Frame(win, bg="#0a0a0a")
        list_f.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        _style = ttk.Style()
        _style.configure("GiveItem.Treeview",
                         background="#0d0d0d", foreground="#ccc",
                         fieldbackground="#0d0d0d", rowheight=22,
                         font=("Consolas", 9))
        _style.configure("GiveItem.Treeview.Heading",
                         background="#161616", foreground="#00ffcc",
                         font=("Segoe UI", 9, "bold"))
        _style.map("GiveItem.Treeview",
                   background=[("selected", "#1a2a3a")],
                   foreground=[("selected", "#00ffcc")])

        item_tree = ttk.Treeview(list_f,
                                 columns=("icon", "name", "id", "cat"),
                                 show="headings",
                                 selectmode="browse",
                                 style="GiveItem.Treeview",
                                 height=16)
        item_tree.heading("icon", text="")
        item_tree.heading("name", text="Tên vật phẩm")
        item_tree.heading("id",   text="Blueprint ID")
        item_tree.heading("cat",  text="Danh mục")
        item_tree.column("icon", width=32,  anchor="center", stretch=False)
        item_tree.column("name", width=210, anchor="w")
        item_tree.column("id",   width=210, anchor="w")
        item_tree.column("cat",  width=110, anchor="center")

        vsb2 = ttk.Scrollbar(list_f, orient="vertical", command=item_tree.yview)
        item_tree.configure(yscrollcommand=vsb2.set)
        item_tree.pack(side="left", fill="both", expand=True)
        vsb2.pack(side="right", fill="y")

        # ── Populate function ─────────────────────────────────────
        def _populate(query="", cat="All"):
            item_tree.delete(*item_tree.get_children())
            q = query.lower()
            for idx, (c, dn, bid, em) in enumerate(_PW_ITEMS):
                if cat != "All" and c != cat:
                    continue
                if q and q not in dn.lower() and q not in bid.lower():
                    continue
                # iid phải unique; dùng bid__idx để tránh crash khi dữ liệu có ID trùng.
                item_tree.insert("", tk.END, iid=f"{bid}__{idx}",
                                 values=(em, dn, bid, c))

        _populate()

        search_var.trace("w", lambda *_: _populate(search_var.get(), cat_var.get()))
        cat_var.trace("w",    lambda *_: _populate(search_var.get(), cat_var.get()))

        # Double-click → fill ID field below
        def _on_double(event):
            sel = item_tree.selection()
            if sel:
                qty_entry.delete(0, tk.END)
                qty_entry.insert(0, "1")
                manual_id.delete(0, tk.END)
                manual_id.insert(0, item_tree.item(sel[0], "values")[2])  # cột id

        item_tree.bind("<Double-1>", _on_double)
        item_tree.bind("<Return>",   _on_double)

        # ── Bottom panel: qty + manual ID + give ─────────────────
        bot = tk.Frame(win, bg="#0d1117", pady=10)
        bot.pack(fill="x", padx=8, pady=(4, 8))

        tk.Label(bot, text="Blueprint ID:", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 4))
        manual_id = tk.Entry(bot, bg="#1a1a2e", fg="#00ffcc", bd=0,
                             font=("Consolas", 10), insertbackground="#00ffcc",
                             width=26)
        manual_id.grid(row=0, column=1, ipady=5, padx=(0, 12))

        tk.Label(bot, text="Số lượng:", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="e", padx=(0, 4))
        qty_entry = tk.Entry(bot, bg="#1a1a2e", fg="#ffd700", bd=0,
                             font=("Consolas", 11, "bold"), insertbackground="#ffd700",
                             width=8)
        qty_entry.insert(0, "1")
        qty_entry.grid(row=0, column=3, ipady=5, padx=(0, 12))

        # Preset quantity buttons
        preset_f = tk.Frame(win, bg="#0d1117")
        preset_f.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(preset_f, text="Nhanh:", bg="#0d1117", fg="#666",
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))
        for qty_val in (1, 10, 50, 100, 500, 999):
            tk.Button(preset_f, text=f"×{qty_val}",
                      bg="#1a2a3a", fg="#7ec8e3", relief="flat",
                      padx=8, pady=2, font=("Segoe UI", 8),
                      command=lambda v=qty_val: (qty_entry.delete(0, tk.END),
                                                 qty_entry.insert(0, str(v)))
                      ).pack(side="left", padx=2)

        # Status label
        status_lbl = tk.Label(win, text="", bg="#0a0a0a", fg="#888",
                              font=("Segoe UI", 9))
        status_lbl.pack(pady=(0, 4))

        # Give button
        def _do_give():
            bid = manual_id.get().strip()
            if not bid:
                sel = item_tree.selection()
                if sel:
                    bid = sel[0]
            if not bid:
                status_lbl.configure(text="⚠️ Chọn vật phẩm hoặc nhập Blueprint ID!", fg="#ffa500")
                return
            try:
                qty = max(1, int(qty_entry.get().strip() or "1"))
            except ValueError:
                status_lbl.configure(text="⚠️ Số lượng không hợp lệ!", fg="#ffa500")
                return

            status_lbl.configure(text=f"⏳ Đang gửi {bid} × {qty} qua RCON...", fg="#ffa500")
            give_btn.configure(state="disabled")

            def _bg():
                # Lấy playerid + steam_number — giống cơ chế quà tân thủ
                playerid     = p.get("playerId", "")
                steam_number = (sid.replace("steam_", "")
                                if sid.startswith("steam_") else sid)

                # Bước 1: RCON give (cơ chế đã kiểm chứng qua quà tân thủ)
                rcon_ok = self._rcon_give_item(playerid, steam_number, sid, bid, qty)
                if rcon_ok:
                    msg = f"✅ Give OK (RCON): {name} ← {bid} × {qty}"
                    self.root.after(0, lambda: status_lbl.configure(text=msg, fg="#00ff88"))
                else:
                    # Bước 2: Fallback PD API
                    pd_ok, data = self._pdapi_give(
                        sid, {"Item": [{"ItemID": bid, "Count": qty}]})
                    if pd_ok:
                        msg = f"✅ Give OK (PD API): {name} ← {bid} × {qty}"
                        self.root.after(0, lambda: status_lbl.configure(text=msg, fg="#00ff88"))
                    else:
                        errs = data.get("Error", data.get("error", str(data)))
                        msg = f"❌ Give FAIL (RCON+PD): {bid} × {qty} — {errs}"
                        self.root.after(0, lambda: status_lbl.configure(text=msg, fg="#ff5555"))
                self._enqueue_console(f"🎁 {msg}")
                self.root.after(0, lambda: give_btn.configure(state="normal"))
            threading.Thread(target=_bg, daemon=True).start()

        give_btn = tk.Button(bot, text="  🎁 GIVE  ",
                             bg="#00aa55", fg="white", relief="flat",
                             padx=18, pady=6, font=("Segoe UI", 10, "bold"),
                             command=_do_give)
        give_btn.grid(row=0, column=4, padx=(0, 8))

        tk.Button(bot, text="✖ Đóng",
                  bg="#2a0000", fg="#ff7777", relief="flat",
                  padx=10, pady=6, font=("Segoe UI", 9),
                  command=win.destroy).grid(row=0, column=5)

        # Focus search
        search_entry.focus_set()
        # Click row → fill ID
        def _on_select(event):
            sel = item_tree.selection()
            if sel:
                manual_id.delete(0, tk.END)
                manual_id.insert(0, item_tree.item(sel[0], "values")[2])
        item_tree.bind("<<TreeviewSelect>>", _on_select)

    # ── Give Pal dialog ───────────────────────────────────────────
    def _player_give_pal_dialog(self):
        p = self._player_get_selected()
        if not p:
            messagebox.showwarning("Give Pal", "Chọn người chơi trước!")
            return
        name = p.get("name", "?")
        sid  = self._normalize_steamid(p.get("userId", ""))
        if not sid:
            messagebox.showerror("Give Pal", "Không tìm thấy SteamID!")
            return

        win = tk.Toplevel(self.root)
        win.title(f"🐾 Give Pal → {name}")
        win.geometry("760x580")
        win.configure(bg="#0a0a0a")
        win.resizable(True, True)
        win.grab_set()

        # ── Header ───────────────────────────────────────────────
        hdr = tk.Frame(win, bg="#111827", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🐾  GIVE PAL",
                 bg="#111827", fg="#a78bfa",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)
        tk.Label(hdr, text=f"→  {name}  [{sid}]",
                 bg="#111827", fg="#888",
                 font=("Segoe UI", 9)).pack(side="left")

        # ── Search + Element filter ───────────────────────────────
        bar = tk.Frame(win, bg="#0d1117", pady=6)
        bar.pack(fill="x", padx=8)

        tk.Label(bar, text="🔍", bg="#0d1117", fg="#666",
                 font=("Segoe UI", 11)).pack(side="left")
        pal_search = tk.StringVar()
        pal_entry = tk.Entry(bar, textvariable=pal_search,
                             bg="#1a1a2e", fg="#ccc", bd=0,
                             font=("Consolas", 10), insertbackground="#ccc",
                             width=20)
        pal_entry.pack(side="left", ipady=5, padx=(4, 14))

        elements = ["All"] + sorted({r[3] for r in _PW_PALS})
        elem_var = tk.StringVar(value="All")
        tk.Label(bar, text="Element:", bg="#0d1117", fg="#888",
                 font=("Segoe UI", 9)).pack(side="left")
        ttk.Combobox(bar, textvariable=elem_var,
                     values=elements, state="readonly",
                     width=12, font=("Segoe UI", 9)
                     ).pack(side="left", padx=(4, 0), ipady=3)

        # ── Pal Treeview ──────────────────────────────────────────
        list_f = tk.Frame(win, bg="#0a0a0a")
        list_f.pack(fill="both", expand=True, padx=8, pady=4)

        _style2 = ttk.Style()
        _style2.configure("GivePal.Treeview",
                          background="#0d0d0d", foreground="#ccc",
                          fieldbackground="#0d0d0d", rowheight=22,
                          font=("Consolas", 9))
        _style2.configure("GivePal.Treeview.Heading",
                          background="#161616", foreground="#a78bfa",
                          font=("Segoe UI", 9, "bold"))
        _style2.map("GivePal.Treeview",
                    background=[("selected", "#1a1a3a")],
                    foreground=[("selected", "#a78bfa")])

        pal_tree = ttk.Treeview(list_f,
                                columns=("em", "dex", "name", "pal_id", "element"),
                                show="headings",
                                selectmode="browse",
                                style="GivePal.Treeview",
                                height=16)
        pal_tree.heading("em",      text="")
        pal_tree.heading("dex",     text="#")
        pal_tree.heading("name",    text="Tên Pal")
        pal_tree.heading("pal_id",  text="Pal ID (Blueprint)")
        pal_tree.heading("element", text="Element")
        pal_tree.column("em",      width=32,  anchor="center", stretch=False)
        pal_tree.column("dex",     width=46,  anchor="center", stretch=False)
        pal_tree.column("name",    width=170, anchor="w")
        pal_tree.column("pal_id",  width=200, anchor="w")
        pal_tree.column("element", width=90,  anchor="center")

        vsb3 = ttk.Scrollbar(list_f, orient="vertical", command=pal_tree.yview)
        pal_tree.configure(yscrollcommand=vsb3.set)
        pal_tree.pack(side="left", fill="both", expand=True)
        vsb3.pack(side="right", fill="y")

        def _pop_pals(query="", elem="All"):
            pal_tree.delete(*pal_tree.get_children())
            q = query.lower()
            for (dex, dn, pid, el, em) in _PW_PALS:
                if elem != "All" and el != elem:
                    continue
                if q and q not in dn.lower() and q not in pid.lower() and q not in dex:
                    continue
                pal_tree.insert("", tk.END, iid=f"{pid}_{dex}",
                                values=(em, dex, dn, pid, el))

        _pop_pals()
        pal_search.trace_add("write", lambda *_: _pop_pals(pal_search.get(), elem_var.get()))
        elem_var.trace_add("write",   lambda *_: _pop_pals(pal_search.get(), elem_var.get()))

        # ── Bottom: pal_id field + level + give ──────────────────
        bot2 = tk.Frame(win, bg="#0d1117", pady=10)
        bot2.pack(fill="x", padx=8, pady=(0, 4))

        tk.Label(bot2, text="Pal ID:", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 4))
        manual_pal = tk.Entry(bot2, bg="#1a1a2e", fg="#a78bfa", bd=0,
                              font=("Consolas", 10), insertbackground="#a78bfa",
                              width=22)
        manual_pal.grid(row=0, column=1, ipady=5, padx=(0, 12))

        tk.Label(bot2, text="Level:", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="e", padx=(0, 4))
        lv_entry = tk.Entry(bot2, bg="#1a1a2e", fg="#ffd700", bd=0,
                            font=("Consolas", 11, "bold"), insertbackground="#ffd700",
                            width=6)
        lv_entry.insert(0, "1")
        lv_entry.grid(row=0, column=3, ipady=5, padx=(0, 12))

        # Level presets
        pre_f = tk.Frame(win, bg="#0d1117")
        pre_f.pack(fill="x", padx=8, pady=(0, 4))
        tk.Label(pre_f, text="Level nhanh:", bg="#0d1117", fg="#666",
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 6))
        for lv_val in (1, 10, 20, 30, 40, 50):
            tk.Button(pre_f, text=f"Lv.{lv_val}",
                      bg="#1a1a2e", fg="#a78bfa", relief="flat",
                      padx=8, pady=2, font=("Segoe UI", 8),
                      command=lambda v=lv_val: (lv_entry.delete(0, tk.END),
                                               lv_entry.insert(0, str(v)))
                      ).pack(side="left", padx=2)

        pal_status = tk.Label(win, text="", bg="#0a0a0a", fg="#888",
                              font=("Segoe UI", 9))
        pal_status.pack(pady=(0, 4))

        def _do_give_pal():
            pid_val = manual_pal.get().strip()
            if not pid_val:
                sel = pal_tree.selection()
                if sel:
                    iid_str = sel[0]
                    vals = pal_tree.item(iid_str, "values")
                    pid_val = vals[3] if vals else ""
            if not pid_val:
                pal_status.configure(text="⚠️ Chọn pal hoặc nhập Pal ID!", fg="#ffa500")
                return
            try:
                lv = max(1, int(lv_entry.get().strip() or "1"))
            except ValueError:
                pal_status.configure(text="⚠️ Level không hợp lệ!", fg="#ffa500")
                return

            pal_status.configure(text=f"⏳ Đang gửi {pid_val} Lv.{lv} qua RCON...", fg="#ffa500")
            give_pal_btn.configure(state="disabled")

            def _bg():
                # Lấy playerid + steam_number — giống cơ chế quà tân thủ
                playerid     = p.get("playerId", "")
                steam_number = (sid.replace("steam_", "")
                                if sid.startswith("steam_") else sid)

                # Bước 1: RCON givepal (cơ chế đã kiểm chứng qua quà tân thủ)
                rcon_ok = self._rcon_give_pal(playerid, steam_number, sid, pid_val, lv)
                if rcon_ok:
                    msg = f"✅ Give Pal OK (RCON): {name} ← {pid_val} Lv.{lv}"
                    self.root.after(0, lambda: pal_status.configure(text=msg, fg="#00ff88"))
                else:
                    # Bước 2: Fallback PD API
                    pd_ok, data = self._pdapi_give(
                        sid, {"Pal": [{"PalID": pid_val, "Level": lv}]})
                    if pd_ok:
                        msg = f"✅ Give Pal OK (PD API): {name} ← {pid_val} Lv.{lv}"
                        self.root.after(0, lambda: pal_status.configure(text=msg, fg="#00ff88"))
                    else:
                        errs = data.get("Error", data.get("error", str(data)))
                        msg = f"❌ Give Pal FAIL (RCON+PD): {pid_val} Lv.{lv} — {errs}"
                        self.root.after(0, lambda: pal_status.configure(text=msg, fg="#ff5555"))
                self._enqueue_console(f"🐾 {msg}")
                self.root.after(0, lambda: give_pal_btn.configure(state="normal"))
            threading.Thread(target=_bg, daemon=True).start()

        give_pal_btn = tk.Button(bot2, text="  🐾 GIVE PAL  ",
                                 bg="#7c3aed", fg="white", relief="flat",
                                 padx=16, pady=6, font=("Segoe UI", 10, "bold"),
                                 command=_do_give_pal)
        give_pal_btn.grid(row=0, column=4, padx=(0, 8))

        tk.Button(bot2, text="✖ Đóng",
                  bg="#2a0000", fg="#ff7777", relief="flat",
                  padx=10, pady=6, font=("Segoe UI", 9),
                  command=win.destroy).grid(row=0, column=5)

        # Select → fill ID
        def _pal_select(event):
            sel = pal_tree.selection()
            if sel:
                vals = pal_tree.item(sel[0], "values")
                if vals:
                    manual_pal.delete(0, tk.END)
                    manual_pal.insert(0, vals[3])   # pal_id column
        pal_tree.bind("<<TreeviewSelect>>", _pal_select)
        pal_tree.bind("<Double-1>", lambda e: _do_give_pal())

        # ── IV Calc button ────────────────────────────────────
        def _open_iv_calc():
            pid = manual_pal.get().strip()
            if not pid:
                sel = pal_tree.selection()
                if sel:
                    vals = pal_tree.item(sel[0], "values")
                    pid = vals[3] if vals else ""
            # Truyền thêm player context để cho phép Give Pal with IVs
            player_ctx = {
                "name":         name,
                "steamid":      sid,
                "playerid":     p.get("playerId", ""),
                "steam_number": (sid.replace("steam_", "")
                                 if sid.startswith("steam_") else sid),
            }
            self._iv_calc_dialog(preset_pal_id=pid, player_ctx=player_ctx)

        tk.Button(bot2, text="📊 IV Calc",
                  bg="#0e7490", fg="white", relief="flat",
                  padx=10, pady=6, font=("Segoe UI", 9, "bold"),
                  command=_open_iv_calc).grid(row=0, column=6, padx=(8, 0))

        pal_entry.focus_set()

    # ── IV Calculator Dialog ───────────────────────────────────
    def _iv_calc_dialog(self, preset_pal_id: str = "", player_ctx: dict = None):
        """Mở cửa sổ IV Calculator (Independent Variable / Chỉ số cá thể).
        Công thức từ: paldb.cc/en/Iv_Calc
        player_ctx: dict với keys name/steamid/playerid/steam_number (nếu mở từ Give Pal)
        """
        win = tk.Toplevel(self.root)
        _has_player = bool(player_ctx and player_ctx.get("steamid"))
        _title_sfx  = f"  ➤  {player_ctx['name']}" if _has_player else ""
        win.title(f"📊 IV Calculator{_title_sfx}  —  paldb.cc/en/Iv_Calc")
        win.geometry("880x800" if _has_player else "860x750")
        win.configure(bg="#0a0a0a")
        win.resizable(True, True)
        win.grab_set()

        # ── Header ───────────────────────────────────────────────
        hdr = tk.Frame(win, bg="#111827", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📊  IV CALCULATOR",
                 bg="#111827", fg="#38bdf8",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)
        tk.Label(hdr, text="— Independent Variable (Chỉ số cá thể IV 0~100)",
                 bg="#111827", fg="#666",
                 font=("Segoe UI", 9)).pack(side="left")

        # ── Scrollable body ───────────────────────────────────────
        canvas_iv = tk.Canvas(win, bg="#0a0a0a", highlightthickness=0)
        vsb_iv = ttk.Scrollbar(win, orient="vertical", command=canvas_iv.yview)
        canvas_iv.configure(yscrollcommand=vsb_iv.set)
        vsb_iv.pack(side="right", fill="y")
        canvas_iv.pack(fill="both", expand=True)
        body = tk.Frame(canvas_iv, bg="#0a0a0a")
        _bw = canvas_iv.create_window((0, 0), window=body, anchor="nw")
        def _cfg_scroll(e=None):
            canvas_iv.configure(scrollregion=canvas_iv.bbox("all"))
        def _cfg_width(e):
            canvas_iv.itemconfig(_bw, width=e.width)
        body.bind("<Configure>", _cfg_scroll)
        canvas_iv.bind("<Configure>", _cfg_width)
        canvas_iv.bind_all("<MouseWheel>",
            lambda e: canvas_iv.yview_scroll(-1*(e.delta//120), "units"))

        # ── Build pal list from _IV_PAL_DATA ─────────────────────
        pal_entries = sorted(_IV_PAL_DATA.items(),
                             key=lambda x: (x[1]['id'].zfill(5), x[0]))
        pal_display = [f"[{v['id']}] {v['name']} ({k})" for k, v in pal_entries]
        pal_codes   = [k for k, v in pal_entries]

        # ── Row 1: Pal + Level ────────────────────────────────────
        r1 = tk.Frame(body, bg="#0d1117", pady=8)
        r1.pack(fill="x", padx=10, pady=(8, 0))
        tk.Label(r1, text="Pal:", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 4))
        pal_var = tk.StringVar()
        pal_cb = ttk.Combobox(r1, textvariable=pal_var, values=pal_display,
                               state="readonly", width=40, font=("Consolas", 9))
        pal_cb.grid(row=0, column=1, padx=(0, 14), ipady=3)
        # Pre-fill
        if preset_pal_id and preset_pal_id in pal_codes:
            pal_cb.current(pal_codes.index(preset_pal_id))
        elif pal_codes:
            pal_cb.current(0)

        tk.Label(r1, text="Level (1-65):", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="e", padx=(0, 4))
        lv_var = tk.StringVar(value="1")
        lv_sp = tk.Spinbox(r1, from_=1, to=65, textvariable=lv_var, width=5,
                            bg="#1a1a2e", fg="#ffd700", font=("Consolas", 11, "bold"),
                            bd=0, insertbackground="#ffd700",
                            buttonbackground="#1a1a2e")
        lv_sp.grid(row=0, column=3, ipady=3)

        # ── Row 2: Current Stats ──────────────────────────────────
        r2 = tk.Frame(body, bg="#0d1117", pady=8)
        r2.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(r2, text="Chỉ số hiện tại của Pal (đọc từ game):",
                 bg="#0d1117", fg="#a78bfa",
                 font=("Segoe UI", 9, "bold")).grid(
                     row=0, column=0, columnspan=6, sticky="w", padx=2, pady=(0, 4))
        hp_var  = tk.StringVar()
        atk_var = tk.StringVar()
        def_var = tk.StringVar()
        for ci, (lbl, var, clr) in enumerate([
            ("HP",          hp_var,  "#4ade80"),
            ("ShotAttack",  atk_var, "#f87171"),
            ("Defense",     def_var, "#60a5fa"),
        ]):
            tk.Label(r2, text=f"{lbl}:", bg="#0d1117", fg="#aaa",
                     font=("Segoe UI", 9)).grid(row=1, column=ci*2, sticky="e",
                                                  padx=(6, 4))
            tk.Entry(r2, textvariable=var, width=9, bg="#1a1a2e", fg=clr,
                     font=("Consolas", 10), bd=0, insertbackground=clr
                     ).grid(row=1, column=ci*2+1, padx=(0, 14), ipady=4)

        # ── Row 3: Condenser ──────────────────────────────────────
        r3 = tk.Frame(body, bg="#0d1117", pady=6)
        r3.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(r3, text="Pal Essence Condenser:", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 4))
        condenser_var = tk.StringVar(value="0 (+0%)")
        ttk.Combobox(r3, textvariable=condenser_var,
                      values=["0 (+0%)", "1 (+5%)", "2 (+10%)", "3 (+15%)", "4 (+20%)"],
                      state="readonly", width=14, font=("Segoe UI", 9)
                      ).grid(row=0, column=1, padx=(0, 14), ipady=2)

        # ── Row 4: Statue of Power ────────────────────────────────
        r4 = tk.Frame(body, bg="#0d1117", pady=6)
        r4.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(r4, text="Statue of Power (tượng sức mạnh — mỗi cấp +3%):",
                 bg="#0d1117", fg="#a78bfa",
                 font=("Segoe UI", 9, "bold")).grid(
                     row=0, column=0, columnspan=8, sticky="w", padx=2, pady=(0, 4))
        statue_opts = [f"{i} (+{i*3}%)" for i in range(21)]
        statue_hp_var  = tk.StringVar(value="0 (+0%)")
        statue_atk_var = tk.StringVar(value="0 (+0%)")
        statue_def_var = tk.StringVar(value="0 (+0%)")
        statue_ws_var  = tk.StringVar(value="0 (+0%)")
        for ci, (lbl, sv) in enumerate([
            ("HP",      statue_hp_var),
            ("Attack",  statue_atk_var),
            ("Defense", statue_def_var),
            ("Speed",   statue_ws_var),
        ]):
            tk.Label(r4, text=f"{lbl}:", bg="#0d1117", fg="#aaa",
                     font=("Segoe UI", 9)).grid(row=1, column=ci*2, sticky="e",
                                                  padx=(6, 4))
            ttk.Combobox(r4, textvariable=sv, values=statue_opts,
                          state="readonly", width=11, font=("Segoe UI", 9)
                          ).grid(row=1, column=ci*2+1, padx=(0, 8), ipady=2)

        # ── Row 5: Passive Skills ─────────────────────────────────
        r5 = tk.Frame(body, bg="#0d1117", pady=6)
        r5.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(r5, text="Passive Skills (tối đa 4):",
                 bg="#0d1117", fg="#a78bfa",
                 font=("Segoe UI", 9, "bold")).grid(
                     row=0, column=0, columnspan=4, sticky="w", padx=2, pady=(0, 4))
        passive_opts = ["(Không)"] + [pd['name'] for pd in _IV_PASSIVE_DATA.values()]
        passive_vars_iv = [tk.StringVar(value="(Không)") for _ in range(4)]
        for i, pv in enumerate(passive_vars_iv):
            col = i % 2
            row = 1 + i // 2
            ttk.Combobox(r5, textvariable=pv, values=passive_opts,
                          state="readonly", width=36, font=("Segoe UI", 9)
                          ).grid(row=row, column=col, padx=(4, 14), pady=2, ipady=2)

        # ── Buttons + Status ──────────────────────────────────────
        btn_f = tk.Frame(body, bg="#0d1117", pady=8)
        btn_f.pack(fill="x", padx=10, pady=(4, 0))
        calc_btn = tk.Button(btn_f, text="  📊 TÍNH IV  ",
                              bg="#0e7490", fg="white", relief="flat",
                              padx=16, pady=6, font=("Segoe UI", 10, "bold"))
        calc_btn.pack(side="left", padx=2)
        tk.Button(btn_f, text="✖ Đóng",
                  bg="#2a0000", fg="#ff7777", relief="flat",
                  padx=10, pady=6, font=("Segoe UI", 9),
                  command=win.destroy).pack(side="left", padx=6)
        calc_status = tk.Label(btn_f, text="", bg="#0d1117", fg="#888",
                                font=("Segoe UI", 9))
        calc_status.pack(side="left", padx=8)

        # ── Result Cards ──────────────────────────────────────────
        res_f = tk.Frame(body, bg="#0a0a0a")
        res_f.pack(fill="x", padx=10, pady=(10, 8))

        def _iv_color(v):
            try:
                f = float(v)
                if f >= 90: return "#ffd700"
                if f >= 70: return "#4ade80"
                if f >= 40: return "#a78bfa"
                if f >=  0: return "#60a5fa"
                return "#f87171"
            except Exception:
                return "#888"

        def _iv_grade(v):
            try:
                f = float(v)
                if f >= 90: return "S ★"
                if f >= 70: return "A"
                if f >= 40: return "B"
                if f >=  0: return "C"
                return "D"
            except Exception:
                return "?"

        result_labels = {}
        card_defs = [
            ("❤️ HP",          "hp",  "#4ade80",
             ["IV", "Base", "MaxCur(IV100)", "Diff vs Max%", "Max@Lv65"]),
            ("⚔️ ShotAttack",  "atk", "#f87171",
             ["IV", "Base", "MaxCur(IV100)", "Diff vs Max%", "Max@Lv65", "Passive%"]),
            ("🛡️ Defense",     "def", "#60a5fa",
             ["IV", "Base", "MaxCur(IV100)", "Diff vs Max%", "Max@Lv65", "Passive%"]),
            ("⚙️ Work Speed",  "ws",  "#facc15",
             ["Base", "After Bonuses", "Passive%"]),
        ]
        for ci, (title, key, color, fields) in enumerate(card_defs):
            cf = tk.Frame(res_f, bg="#111827", padx=6, pady=6,
                          bd=1, relief="groove")
            cf.grid(row=0, column=ci, padx=4, pady=4, sticky="nsew")
            res_f.columnconfigure(ci, weight=1)
            tk.Label(cf, text=title, bg="#111827", fg=color,
                     font=("Segoe UI", 10, "bold"), pady=4).pack()
            tk.Frame(cf, bg=color, height=2).pack(fill="x", pady=(0, 6))
            result_labels[key] = {}
            for fn in fields:
                rf = tk.Frame(cf, bg="#111827")
                rf.pack(fill="x", pady=1)
                tk.Label(rf, text=fn + ":", bg="#111827", fg="#555",
                         font=("Segoe UI", 8), anchor="w", width=14).pack(side="left")
                lbl = tk.Label(rf, text="—", bg="#111827", fg="#888",
                               font=("Consolas", 9, "bold"), anchor="e")
                lbl.pack(side="right")
                result_labels[key][fn] = lbl

        # ── Legend ────────────────────────────────────────────────
        leg_f = tk.Frame(body, bg="#0a0a0a")
        leg_f.pack(fill="x", padx=12, pady=(0, 8))
        leg_items = [
            ("S ★ ≥90",  "#ffd700"), ("A ≥70", "#4ade80"),
            ("B ≥40",    "#a78bfa"), ("C ≥0",  "#60a5fa"),
            ("D <0",     "#f87171"),
        ]
        tk.Label(leg_f, text="IV Grade: ", bg="#0a0a0a", fg="#555",
                 font=("Segoe UI", 8)).pack(side="left")
        for txt, clr in leg_items:
            tk.Label(leg_f, text=f"  {txt}  ", bg="#0a0a0a", fg=clr,
                     font=("Segoe UI", 8, "bold")).pack(side="left")

        # ── Calculation function ──────────────────────────────────
        def _do_calc_iv():
            try:
                pal_idx  = pal_cb.current()
                if pal_idx < 0:
                    calc_status.configure(text="⚠️ Chọn Pal trước!", fg="#ffa500")
                    return
                pal_code = pal_codes[pal_idx]
                pal_data = _IV_PAL_DATA[pal_code]

                lv = int(lv_var.get())
                if not (1 <= lv <= 65):
                    calc_status.configure(
                        text="⚠️ Level phải từ 1 đến 65!", fg="#ffa500")
                    return

                hp_val  = int(hp_var.get())
                atk_val = int(atk_var.get())
                def_val = int(def_var.get())

                # Condenser: "0 (+0%)" → 0; "1 (+5%)" → 0.05
                condenser = int(condenser_var.get().split()[0]) * 0.05

                # Statue of Power: "N (+X%)" → N * 0.03
                pw_hp  = int(statue_hp_var.get().split()[0]) * 0.03
                pw_atk = int(statue_atk_var.get().split()[0]) * 0.03
                pw_def = int(statue_def_var.get().split()[0]) * 0.03
                pw_ws  = int(statue_ws_var.get().split()[0]) * 0.03

                # Passive skill bonuses
                passive_atk = 0.0
                passive_def = 0.0
                passive_ws  = 0.0
                for pv in passive_vars_iv:
                    sel = pv.get()
                    if sel == "(Không)":
                        continue
                    for pk, pd in _IV_PASSIVE_DATA.items():
                        if pd['name'] == sel:
                            passive_atk += pd.get('ShotAttack', 0) / 100
                            passive_def += pd.get('Defense', 0) / 100
                            passive_ws  += pd.get('CraftSpeed', 0) / 100
                            break

                base_hp  = pal_data['Hp']
                base_atk = pal_data['ShotAttack']
                base_def = pal_data['Defense']
                POTENTIAL  = 0.3   # IV 100 = +30%
                MAX_LV = 65

                # ── HP (công thức paldb.cc) ──
                # HPIv = 100*((HP/(1+condenser)/(1+powerHP)-500-5*Lv)/0.5/HPBase/Lv-1)/PotentialBonus
                hp_iv = round(
                    100 * ((hp_val / (1+condenser) / (1+pw_hp) - 500 - 5*lv)
                           / 0.5 / base_hp / lv - 1) / POTENTIAL, 1)
                hp_max_cur = round(500 + lv*5 + base_hp*lv*0.5*(1+POTENTIAL))
                hp_diff    = round(100*(hp_max_cur - hp_val)/hp_max_cur, 1) if hp_max_cur else 0
                hp_max65   = round(500 + MAX_LV*5 + base_hp*MAX_LV*0.5*(1+POTENTIAL))

                # ── ShotAttack ──
                atk_iv = round(
                    100 * ((atk_val / (1+condenser) / (1+pw_atk) / (1+passive_atk) - 100)
                           / 0.075 / base_atk / lv - 1) / POTENTIAL, 1)
                atk_max_cur = round(100 + base_atk*lv*0.075*(1+POTENTIAL))
                atk_diff    = round(100*(atk_max_cur - atk_val)/atk_max_cur, 1) if atk_max_cur else 0
                atk_max65   = round(100 + base_atk*MAX_LV*0.075*(1+POTENTIAL))

                # ── Defense ──
                def_iv = round(
                    100 * ((def_val / (1+condenser) / (1+pw_def) / (1+passive_def) - 50)
                           / 0.075 / base_def / lv - 1) / POTENTIAL, 1)
                def_max_cur = round(50 + base_def*lv*0.075*(1+POTENTIAL))
                def_diff    = round(100*(def_max_cur - def_val)/def_max_cur, 1) if def_max_cur else 0
                def_max65   = round(50 + base_def*MAX_LV*0.075*(1+POTENTIAL))

                # ── Work Speed ──
                ws_after = int(70 * (1+condenser) * (1+pw_ws) * (1+passive_ws))

                # ── Update result cards ──
                c, g = _iv_color(hp_iv), _iv_grade(hp_iv)
                result_labels['hp']['IV'].configure(
                    text=f"{hp_iv}  [{g}]", fg=c)
                result_labels['hp']['Base'].configure(
                    text=str(base_hp), fg="#aaa")
                result_labels['hp']['MaxCur(IV100)'].configure(
                    text=str(hp_max_cur), fg="#888")
                result_labels['hp']['Diff vs Max%'].configure(
                    text=f"-{hp_diff}%",
                    fg="#f87171" if hp_diff > 5 else "#4ade80")
                result_labels['hp']['Max@Lv65'].configure(
                    text=str(hp_max65), fg="#888")

                c, g = _iv_color(atk_iv), _iv_grade(atk_iv)
                result_labels['atk']['IV'].configure(
                    text=f"{atk_iv}  [{g}]", fg=c)
                result_labels['atk']['Base'].configure(
                    text=str(base_atk), fg="#aaa")
                result_labels['atk']['MaxCur(IV100)'].configure(
                    text=str(atk_max_cur), fg="#888")
                result_labels['atk']['Diff vs Max%'].configure(
                    text=f"-{atk_diff}%",
                    fg="#f87171" if atk_diff > 5 else "#4ade80")
                result_labels['atk']['Max@Lv65'].configure(
                    text=str(atk_max65), fg="#888")
                result_labels['atk']['Passive%'].configure(
                    text=f"+{round(passive_atk*100)}%" if passive_atk >= 0
                         else f"{round(passive_atk*100)}%",
                    fg="#facc15" if passive_atk != 0 else "#888")

                c, g = _iv_color(def_iv), _iv_grade(def_iv)
                result_labels['def']['IV'].configure(
                    text=f"{def_iv}  [{g}]", fg=c)
                result_labels['def']['Base'].configure(
                    text=str(base_def), fg="#aaa")
                result_labels['def']['MaxCur(IV100)'].configure(
                    text=str(def_max_cur), fg="#888")
                result_labels['def']['Diff vs Max%'].configure(
                    text=f"-{def_diff}%",
                    fg="#f87171" if def_diff > 5 else "#4ade80")
                result_labels['def']['Max@Lv65'].configure(
                    text=str(def_max65), fg="#888")
                result_labels['def']['Passive%'].configure(
                    text=f"+{round(passive_def*100)}%" if passive_def >= 0
                         else f"{round(passive_def*100)}%",
                    fg="#facc15" if passive_def != 0 else "#888")

                result_labels['ws']['Base'].configure(text="70", fg="#aaa")
                result_labels['ws']['After Bonuses'].configure(
                    text=str(ws_after), fg="#facc15")
                result_labels['ws']['Passive%'].configure(
                    text=f"+{round(passive_ws*100)}%" if passive_ws >= 0
                         else f"{round(passive_ws*100)}%",
                    fg="#facc15" if passive_ws != 0 else "#888")

                calc_status.configure(
                    text=f"✅ {pal_data['name']} Lv.{lv}  |  "
                         f"HP:{hp_iv} {_iv_grade(hp_iv)}  "
                         f"ATK:{atk_iv} {_iv_grade(atk_iv)}  "
                         f"DEF:{def_iv} {_iv_grade(def_iv)}",
                    fg="#00ff88")

            except ValueError as e:
                calc_status.configure(
                    text=f"⚠️ Nhập số nguyên hợp lệ cho HP/ATK/DEF/Level! ({e})",
                    fg="#ffa500")
            except ZeroDivisionError:
                calc_status.configure(
                    text="⚠️ Lỗi chia 0 — Kiểm tra Level và Base stats!",
                    fg="#f87171")
            except Exception as e:
                calc_status.configure(text=f"❌ Lỗi tính toán: {e}", fg="#f87171")

        calc_btn.configure(command=_do_calc_iv)
        win.bind("<Return>", lambda e: _do_calc_iv())

        # ── SECTION: Gán IV cho người chơi (chỉ hiện khi có player context) ──
        if _has_player:
            tk.Frame(body, bg="#1c1c1c", height=2).pack(fill="x", padx=6, pady=(10, 0))
            giv_hdr = tk.Frame(body, bg="#0d2137", pady=6)
            giv_hdr.pack(fill="x", padx=6, pady=(0, 0))
            tk.Label(giv_hdr,
                     text=f"🎁  GÁN IV CHO NGƯỜI CHƠI  ▸  {player_ctx['name']}",
                     bg="#0d2137", fg="#38bdf8",
                     font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
            tk.Label(giv_hdr,
                     text="(Give Pal mới với chỉ số IV tùy chỉnh qua PD API)",
                     bg="#0d2137", fg="#555",
                     font=("Segoe UI", 8)).pack(side="left")

            giv_body = tk.Frame(body, bg="#0d1117", pady=6)
            giv_body.pack(fill="x", padx=6, pady=(0, 4))

            # ── Row A: Target IVs (0-100) ──────────────────────────
            tk.Label(giv_body, text="Target IVs muốn gán (0-100):",
                     bg="#0d1117", fg="#a78bfa",
                     font=("Segoe UI", 9, "bold")).grid(
                         row=0, column=0, columnspan=6, sticky="w", padx=4, pady=(2, 4))
            giv_hp_iv  = tk.StringVar(value="100")
            giv_atk_iv = tk.StringVar(value="100")
            giv_def_iv = tk.StringVar(value="100")
            for ci, (lbl, sv, clr) in enumerate([
                ("HP IV",  giv_hp_iv,  "#4ade80"),
                ("ATK IV", giv_atk_iv, "#f87171"),
                ("DEF IV", giv_def_iv, "#60a5fa"),
            ]):
                tk.Label(giv_body, text=f"{lbl}:", bg="#0d1117", fg="#aaa",
                         font=("Segoe UI", 9)).grid(
                             row=1, column=ci*2, sticky="e", padx=(8, 4))
                tk.Spinbox(giv_body, from_=0, to=100,
                           textvariable=sv, width=6,
                           bg="#1a1a2e", fg=clr, font=("Consolas", 10, "bold"),
                           bd=0, insertbackground=clr,
                           buttonbackground="#1a1a2e"
                           ).grid(row=1, column=ci*2+1, padx=(0, 16), ipady=3)

            # ── Row B: Nickname + Level ───────────────────────────
            tk.Label(giv_body, text="Nickname (tùy chọn):", bg="#0d1117", fg="#aaa",
                     font=("Segoe UI", 9)).grid(
                         row=2, column=0, sticky="e", padx=(8, 4), pady=(6, 0))
            giv_nick = tk.StringVar()
            tk.Entry(giv_body, textvariable=giv_nick, width=20,
                     bg="#1a1a2e", fg="#ffd700", bd=0,
                     font=("Consolas", 9), insertbackground="#ffd700"
                     ).grid(row=2, column=1, columnspan=2, padx=(0, 14),
                            ipady=3, pady=(6, 0), sticky="w")
            tk.Label(giv_body, text="Shiny:", bg="#0d1117", fg="#aaa",
                     font=("Segoe UI", 9)).grid(
                         row=2, column=3, sticky="e", padx=(0, 4), pady=(6, 0))
            giv_shiny = tk.BooleanVar(value=False)
            tk.Checkbutton(giv_body, variable=giv_shiny,
                           bg="#0d1117", fg="#facc15",
                           activebackground="#0d1117",
                           selectcolor="#0d1117").grid(
                               row=2, column=4, pady=(6, 0), sticky="w")

            # ── Row C: Passives for the new Pal ──────────────────
            tk.Label(giv_body, text="Passive Skills cho Pal mới (tối đa 4):",
                     bg="#0d1117", fg="#a78bfa",
                     font=("Segoe UI", 9, "bold")).grid(
                         row=3, column=0, columnspan=6, sticky="w",
                         padx=4, pady=(8, 4))
            # Build passive list as (display_name, code) pairs
            _giv_passive_opts_disp = ["(Không)"] + [
                f"{pd['name']}  [{pk}]"
                for pk, pd in _IV_PASSIVE_DATA.items()
            ]
            _giv_passive_opts_keys = [None] + list(_IV_PASSIVE_DATA.keys())
            giv_passive_vars = [tk.StringVar(value="(Không)") for _ in range(4)]
            for i, pv in enumerate(giv_passive_vars):
                col = i % 2
                row = 4 + i // 2
                ttk.Combobox(giv_body, textvariable=pv,
                              values=_giv_passive_opts_disp,
                              state="readonly", width=34,
                              font=("Segoe UI", 9)
                              ).grid(row=row, column=col*3,
                                     columnspan=3, padx=(4, 10),
                                     pady=2, ipady=2, sticky="w")

            # ── Row D: Give button + status ───────────────────────
            giv_btn_f = tk.Frame(giv_body, bg="#0d1117")
            giv_btn_f.grid(row=6, column=0, columnspan=6,
                            sticky="w", padx=4, pady=(8, 4))
            giv_btn = tk.Button(giv_btn_f,
                                text="  🎁 GIVE PAL WITH IVs  ",
                                bg="#065f46", fg="white", relief="flat",
                                padx=14, pady=7,
                                font=("Segoe UI", 10, "bold"))
            giv_btn.pack(side="left", padx=(0, 8))
            giv_status = tk.Label(giv_btn_f, text="", bg="#0d1117", fg="#888",
                                   font=("Segoe UI", 9))
            giv_status.pack(side="left")

            # ── Give logic ────────────────────────────────────────
            def _do_give_with_ivs():
                try:
                    # ── Lấy Pal ──
                    pal_idx = pal_cb.current()
                    if pal_idx < 0:
                        giv_status.configure(
                            text="⚠️ Chọn Pal trước!", fg="#ffa500")
                        return
                    pal_code = pal_codes[pal_idx]
                    pal_name = _IV_PAL_DATA[pal_code]['name']

                    lv = int(lv_var.get())
                    if not (1 <= lv <= 65):
                        giv_status.configure(
                            text="⚠️ Level phải 1-65!", fg="#ffa500")
                        return

                    # ── Target IVs (0-100) ──
                    hp_iv_t  = max(0, min(100, int(giv_hp_iv.get())))
                    atk_iv_t = max(0, min(100, int(giv_atk_iv.get())))
                    def_iv_t = max(0, min(100, int(giv_def_iv.get())))

                    # ── Passives: lấy keys ──
                    passives_keys = []
                    for pv in giv_passive_vars:
                        sel = pv.get()
                        if sel == "(Không)":
                            continue
                        # Format: "Display Name  [key]"
                        m = re.search(r"\[(.+?)\]$", sel)
                        if m:
                            passives_keys.append(m.group(1))

                    # ── Build payload ──
                    pal_obj: dict = {
                        "PalID": pal_code,
                        "Level": lv,
                        "IVs": {
                            "Health":      hp_iv_t,
                            "AttackMelee": atk_iv_t,
                            "AttackShot":  atk_iv_t,
                            "Defense":     def_iv_t,
                        },
                    }
                    if giv_nick.get().strip():
                        pal_obj["Nickname"] = giv_nick.get().strip()
                    if giv_shiny.get():
                        pal_obj["Shiny"] = True
                    if passives_keys:
                        pal_obj["Passives"] = passives_keys

                    steamid      = player_ctx["steamid"]
                    playerid     = player_ctx["playerid"]
                    steam_number = player_ctx["steam_number"]

                    giv_status.configure(
                        text=f"⏳ Đang gửi {pal_name} Lv.{lv} (HP IV:{hp_iv_t} ATK:{atk_iv_t} DEF:{def_iv_t})...",
                        fg="#ffa500")
                    giv_btn.configure(state="disabled")

                    def _bg_give():
                        # Thử PD API trước (hỗ trợ IVs)
                        pd_ok, data = self._pdapi_give(
                            steamid, {"Pal": [pal_obj]})
                        if pd_ok:
                            msg = (f"✅ Give OK (PD API): {pal_name} Lv.{lv} "
                                   f"HP IV:{hp_iv_t} ATK IV:{atk_iv_t} DEF IV:{def_iv_t}")
                            self.root.after(0, lambda: giv_status.configure(
                                text=msg, fg="#00ff88"))
                        else:
                            # Fallback: RCON givepal (không có IVs)
                            rcon_ok = self._rcon_give_pal(
                                playerid, steam_number, steamid, pal_code, lv)
                            if rcon_ok:
                                msg = (f"⚠️ Give OK (RCON fallback — không có IV): "
                                       f"{pal_name} Lv.{lv}")
                                self.root.after(0, lambda: giv_status.configure(
                                    text=msg, fg="#facc15"))
                            else:
                                errs = data.get("Error", data.get("error", str(data)))
                                msg = (f"❌ Give FAIL: {pal_code} Lv.{lv} — {errs}")
                                self.root.after(0, lambda: giv_status.configure(
                                    text=msg, fg="#ff5555"))
                        self._enqueue_console(f"🎁 IV-Give: {msg}")
                        self.root.after(0, lambda: giv_btn.configure(state="normal"))

                    threading.Thread(target=_bg_give, daemon=True).start()

                except ValueError as e:
                    giv_status.configure(
                        text=f"⚠️ Nhập số nguyên hợp lệ! ({e})", fg="#ffa500")
                except Exception as e:
                    giv_status.configure(text=f"❌ Lỗi: {e}", fg="#f87171")

            giv_btn.configure(command=_do_give_with_ivs)

            # ── Tip box ───────────────────────────────────────────
            tip = tk.Label(body,
                           text="💡  Tip: IV 0-100 tương ứng 0%-30% bonus stats "
                                "│  AttackMelee = AttackShot = ATK IV được set  "
                                "│  PD API phải Online mới dùng được tính năng này",
                           bg="#0a0a0a", fg="#444",
                           font=("Segoe UI", 8), wraplength=820, justify="left")
            tip.pack(fill="x", padx=12, pady=(0, 8))

    def _player_ctx_show(self, event):
        """Hiện context menu right-click."""
        iid = self.player_tree.identify_row(event.y)
        if iid:
            self.player_tree.selection_set(iid)
            self._player_on_select()
            try:
                self._player_ctx.tk_popup(event.x_root, event.y_root)
            finally:
                self._player_ctx.grab_release()

    def _player_sort_by(self, col: str):
        """Click header → sort theo cột, click lại → đảo chiều."""
        if self._player_sort_col == col:
            self._player_sort_rev = not self._player_sort_rev
        else:
            self._player_sort_col = col
            self._player_sort_rev = col in ("Lv", "Ping")
        self._filter_player_tree()

    # ─────────────────────────────────────────
    #  DRAW: OVERVIEW
    # ─────────────────────────────────────────
    def draw_overview(self):
        tk.Label(self.container, text="GIÁM SÁT HỆ THỐNG MANAGER SERVERPAL",
                 bg="#0a0a0a", fg="white",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 36))

        grid = tk.Frame(self.container, bg="#0a0a0a")
        grid.pack(fill="both", expand=True)

        cards = [
            ("PLAYERS ONLINE", self.player_count_str, "#00ffcc", 0),
            ("CPU USAGE",      "0%",                  "#ffcc00", 1),
            ("RAM USAGE",      "0%",                  "#ff5555", 2),
        ]
        for title, val, color, col in cards:
            card = tk.Frame(grid, bg="#161616", padx=30, pady=55,
                            highlightthickness=1, highlightbackground="#333")
            card.grid(row=0, column=col, padx=15, sticky="nsew")
            grid.grid_columnconfigure(col, weight=1)
            tk.Label(card, text=title, bg="#161616", fg="#888",
                     font=("Segoe UI", 13, "bold")).pack()
            lbl = tk.Label(card, text=val, bg="#161616", fg=color,
                           font=("Consolas", 56, "bold"))
            lbl.pack(pady=16)
            self.overview_widgets[title] = lbl

        # ── Live system log ngay trong tab Tổng Quan ─────────────────────
        log_wrap = tk.Frame(self.container, bg="#0a0a0a")
        log_wrap.pack(fill="both", expand=True, pady=(14, 0))

        hdr = tk.Frame(log_wrap, bg="#0a0d1a", pady=4)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋  LIVE SYSTEM LOG",
                 bg="#0a0d1a", fg="#00ffcc",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        tk.Button(
            hdr, text="🗑 Xóa",
            bg="#1a1a2a", fg="#ff7777",
            relief="flat", padx=10,
            command=lambda: self.overview_console.delete("1.0", tk.END)
        ).pack(side="right", padx=4)

        self.overview_console = scrolledtext.ScrolledText(
            log_wrap,
            bg="#000", fg="#33ff33",
            font=("Consolas", 9), bd=0,
            insertbackground="#33ff33",
            state="normal"
        )
        self.overview_console.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        self.overview_console.tag_configure("system", foreground="#33ff33")
        self.overview_console.tag_configure("warn",   foreground="#ffaa00")
        self.overview_console.tag_configure("error",  foreground="#ff5555")
        # Phục hồi log đã có từ buffer để khi quay lại tab không mất log
        self._replay_console_buffer(self.overview_console)

    # ─────────────────────────────────────────
    #  DRAW: DASHBOARD
    # ─────────────────────────────────────────
    def draw_dashboard(self):
        # ╔══════════════════════════════════════════════════════════╗
        # ║  SECTION 1 — STATUS + CONTROL BUTTONS                   ║
        # ╚══════════════════════════════════════════════════════════╝
        ctrl_outer = tk.Frame(self.container, bg="#0a0a0a")
        ctrl_outer.pack(fill="x", pady=(0, 4))

        # ── Status indicator ──────────────────────────────────────
        status_row = tk.Frame(ctrl_outer, bg="#0a0a0a", pady=4)
        status_row.pack(fill="x", padx=10)

        self._lbl_ctrl_status = tk.Label(
            status_row, text="● KIỂM TRA...",
            bg="#0a0a0a", fg="#888",
            font=("Segoe UI", 13, "bold")
        )
        self._lbl_ctrl_status.pack(side="left")

        tk.Label(status_row,
                 text="  │  Chế độ Auto:",
                 bg="#0a0a0a", fg="#555",
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Checkbutton(status_row, text="Watchdog tự động khởi động",
                       variable=self.auto_mode,
                       bg="#0a0a0a", fg="#888",
                       selectcolor="#0a0a0a",
                       activebackground="#0a0a0a",
                       font=("Segoe UI", 9)).pack(side="left", padx=6)

        # ── Nút điều khiển chính (4 nút lớn) ─────────────────────
        btn_row = tk.Frame(ctrl_outer, bg="#0a0a0a", pady=6)
        btn_row.pack(fill="x", padx=8)

        btn_cfg = [
            # (attr_name, text, bg_on, bg_off, fg_on, fg_off, command, always_enabled)
        ]

        # START — xanh lá
        self._btn_ctrl_start = tk.Button(
            btn_row,
            text="▶   KHỞI ĐỘNG",
            bg="#1a5e1a", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat", padx=0, pady=14,
            cursor="hand2",
            command=self.server_start
        )
        self._btn_ctrl_start.pack(side="left", fill="x", expand=True, padx=(0, 4))

        # STOP — đỏ đậm
        self._btn_ctrl_stop = tk.Button(
            btn_row,
            text="⏹   DỪNG SERVER",
            bg="#7b0000", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat", padx=0, pady=14,
            cursor="hand2",
            command=self.server_stop
        )
        self._btn_ctrl_stop.pack(side="left", fill="x", expand=True, padx=4)

        # RESET — cam
        tk.Button(
            btn_row,
            text="🔁   RESET SERVER",
            bg="#8b4a00", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat", padx=0, pady=14,
            cursor="hand2",
            command=self.manual_test_reset
        ).pack(side="left", fill="x", expand=True, padx=4)

        # SAVE — xanh dương
        tk.Button(
            btn_row,
            text="💾   SAVE SERVER",
            bg="#0d3b6e", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat", padx=0, pady=14,
            cursor="hand2",
            command=self.manual_save
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # ── RAM Optimizer controls ─────────────────────────────────
        opt_row = tk.Frame(ctrl_outer, bg="#0a0a0a", pady=4)
        opt_row.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(opt_row, text="🧹 Tối ưu RAM:",
                 bg="#0a0a0a", fg="#55ff99",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(opt_row, text="Chạy ngay",
                  bg="#145a32", fg="white",
                  relief="flat", padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"),
                  command=lambda: threading.Thread(target=self.optimize_ram_now, daemon=True).start()
                  ).pack(side="left", padx=(8, 10))
        tk.Checkbutton(opt_row, text="Tự động khi RAM hệ thống ≥ 80%",
                       variable=self._ram_auto_opt_var,
                       bg="#0a0a0a", fg="#888", selectcolor="#0a0a0a",
                       activebackground="#0a0a0a",
                       font=("Segoe UI", 9)).pack(side="left")

        # Cập nhật trạng thái nút ngay khi vẽ
        self.root.after(300, self._update_ctrl_btn_state)

        # ── Dòng phân cách ────────────────────────────────────────
        sep = tk.Frame(ctrl_outer, bg="#1e1e1e", height=1)
        sep.pack(fill="x", padx=8, pady=(4, 0))

        # ╔══════════════════════════════════════════════════════════╗
        # ║  SECTION 2 — RCON + BROADCAST                           ║
        # ╚══════════════════════════════════════════════════════════╝
        input_outer = tk.Frame(self.container, bg="#0a0a0a")
        input_outer.pack(fill="x", padx=8, pady=(4, 0))

        # RCON row
        rcon_f = tk.Frame(input_outer, bg="#0a0a0a", pady=3)
        rcon_f.pack(fill="x")
        tk.Label(rcon_f, text="⚡ RCON:",
                 bg="#0a0a0a", fg="#ff9900",
                 font=("Segoe UI", 9, "bold"), width=11,
                 anchor="e").pack(side="left")
        self.entry_rcon = tk.Entry(
            rcon_f, bg="#151515", fg="#ffcc77",
            bd=0, font=("Consolas", 10),
            insertbackground="#ffcc77"
        )
        self.entry_rcon.pack(side="left", fill="x", expand=True,
                             padx=(6, 8), ipady=7)
        self.entry_rcon.bind("<Return>", lambda _: self.send_rcon_cmd())
        tk.Button(rcon_f, text="GỬI RCON",
                  bg="#7d3c98", fg="white",
                  relief="flat", padx=16, pady=4,
                  font=("Segoe UI", 9, "bold"),
                  command=self.send_rcon_cmd).pack(side="left")

        # ── Dòng phân cách ────────────────────────────────────────
        sep2 = tk.Frame(self.container, bg="#1e1e1e", height=1)
        sep2.pack(fill="x", padx=8, pady=(4, 0))

        # ╔══════════════════════════════════════════════════════════╗
        # ║  SECTION 3 — PANED: CHAT INGAME + SYSTEM LOG            ║
        # ╚══════════════════════════════════════════════════════════╝
        paned = tk.PanedWindow(
            self.container, orient=tk.VERTICAL,
            bg="#1e1e1e", sashwidth=5, sashrelief="flat",
            handlesize=0
        )
        paned.pack(fill="both", expand=True, padx=2, pady=(4, 2))

        # ── Pane trên: CHAT INGAME ─────────────────────────────────
        chat_frame = tk.Frame(paned, bg="#050d14")
        paned.add(chat_frame, minsize=120)

        chat_hdr = tk.Frame(chat_frame, bg="#071520", pady=4)
        chat_hdr.pack(fill="x")
        tk.Label(chat_hdr, text="💬  CHAT INGAME",
                 bg="#071520", fg="#00e5ff",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        # Bộ lọc kênh (tất cả / Global / Local)
        self._chat_filter_var = tk.StringVar(value="All")
        for opt, label in [("All","Tất cả"),("Global","Global"),("Local","Local")]:
            tk.Radiobutton(
                chat_hdr, text=label,
                variable=self._chat_filter_var, value=opt,
                bg="#071520", fg="#888", selectcolor="#071520",
                activebackground="#071520",
                font=("Segoe UI", 8)
            ).pack(side="left", padx=2)
        tk.Button(chat_hdr, text="🗑 Xóa",
                  bg="#071520", fg="#ff7777", relief="flat", padx=8,
                  command=lambda: self.chat_console.delete("1.0", tk.END)
                  ).pack(side="right", padx=4)

        self.chat_console = scrolledtext.ScrolledText(
            chat_frame,
            bg="#040f18", fg="#00e5ff",
            font=("Consolas", 9), bd=0,
            insertbackground="#00e5ff",
            state="disabled"
        )
        self.chat_console.pack(fill="both", expand=True)
        self.chat_console.tag_configure("player", foreground="#00e5ff", font=("Consolas", 9, "bold"))
        self.chat_console.tag_configure("admin",  foreground="#ffd700", font=("Consolas", 9, "bold"))
        self.chat_console.tag_configure("ts",     foreground="#555577")
        self.chat_console.tag_configure("channel",foreground="#336688")

        # ── Chat input (gửi cho người chơi) ────────────────────────
        chat_in_f = tk.Frame(chat_frame, bg="#050d14", pady=3)
        chat_in_f.pack(fill="x", padx=4, pady=(2, 4))
        tk.Label(chat_in_f, text="📢",
                 bg="#050d14", fg="#ffd700",
                 font=("Segoe UI", 12)).pack(side="left", padx=(4, 2))
        self.entry_cmd = tk.Entry(
            chat_in_f, bg="#0a1a28", fg="#ffe066",
            bd=0, font=("Segoe UI", 10),
            insertbackground="#ffe066",
            relief="flat"
        )
        self.entry_cmd.pack(side="left", fill="x", expand=True, ipady=7, padx=4)
        self.entry_cmd.bind("<Return>", lambda _: self.send_msg())
        tk.Button(chat_in_f, text="GỬI",
                  bg="#1a4a7a", fg="white",
                  relief="flat", padx=18, pady=4,
                  font=("Segoe UI", 9, "bold"),
                  command=self.send_msg).pack(side="left", padx=(0, 2))

        # ── Pane dưới: SYSTEM LOG ──────────────────────────────────
        log_frame = tk.Frame(paned, bg="#0a0a0a")
        paned.add(log_frame, minsize=80)

        mgr_hdr = tk.Frame(log_frame, bg="#0a0d1a", pady=4)
        mgr_hdr.pack(fill="x")
        tk.Label(mgr_hdr, text="🖥  SYSTEM LOG",
                 bg="#0a0d1a", fg="#00ffcc",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        tk.Button(mgr_hdr, text="🗑 Xóa",
                  bg="#1a1a2a", fg="#ff7777", relief="flat", padx=10,
                  command=lambda: self.console.delete("1.0", tk.END)
                  ).pack(side="right", padx=4)

        self.console = scrolledtext.ScrolledText(
            log_frame,
            bg="#000", fg="#33ff33",
            font=("Consolas", 9), bd=0,
            insertbackground="#33ff33"
        )
        self.console.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        self.console.tag_configure("system", foreground="#33ff33")
        self.console.tag_configure("warn",   foreground="#ffaa00")
        self.console.tag_configure("error",  foreground="#ff5555")
        # Phục hồi log đã có từ buffer
        self._replay_console_buffer(self.console)

        # Đặt kích thước ban đầu cho 2 pane (60% chat / 40% log)
        self.container.update_idletasks()
        self.root.after(200, lambda: paned.sash_place(0, 0, int(paned.winfo_height() * 0.6)))

        # (Chat được route qua _write_console_direct → _poll_console_queue)

    def _load_server_log_history(self):
        """Tải 200 dòng cuối của PalServer.log vào server_console khi mở tab."""
        if not hasattr(self, "server_console") or not self.server_console.winfo_exists():
            return
        try:
            if not os.path.isfile(SERVER_LOG_FILE):
                self.server_console.insert(
                    tk.END,
                    f"⚠️ Chưa tìm thấy file log:\n  {SERVER_LOG_FILE}\n"
                    "   Server chưa chạy hoặc đường dẫn chưa đúng.\n"
                )
                return
            with open(SERVER_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-200:] if len(lines) > 200 else lines
            self.server_console.delete("1.0", tk.END)
            if len(lines) > 200:
                self.server_console.insert(
                    tk.END,
                    f"─── 200 dòng cuối / tổng {len(lines)} dòng ───\n\n"
                )
            for line in tail:
                self.server_console.insert(tk.END, line)
            self.server_console.see(tk.END)
        except Exception as e:
            self.server_console.insert(tk.END, f"❌ Lỗi đọc log: {e}\n")

    def send_rcon_cmd(self):
        """Gửi lệnh RCON trực tiếp, hiển thị kết quả trong manager console."""
        if not hasattr(self, "entry_rcon"):
            return
        cmd = self.entry_rcon.get().strip()
        if not cmd:
            return
        self.entry_rcon.delete(0, tk.END)
        self._enqueue_console(f"⚡ RCON ▶ {cmd}")
        def _do():
            result = rcon_exec(cmd)
            self._enqueue_console(f"   ↳ {result or '(OK — không có phản hồi)'}")
        threading.Thread(target=_do, daemon=True).start()

    def send_msg(self):
        m = self.entry_cmd.get().strip()
        if m:
            self.send_ingame_broadcast(f"ADMIN: {m}")
            self._enqueue_console(f"📢 ADMIN → {m}")
            self.entry_cmd.delete(0, tk.END)

    def manual_test_reset(self):
        if messagebox.askyesno("CONFIRM", "Chạy quy trình Reset 30s ngay?"):
            self.is_processing = False
            threading.Thread(target=self.reset_sequence, daemon=True).start()

    def manual_save(self):
        try:
            requests.post(f"{API_URL}/save", auth=AUTH, timeout=20)
            self.write_console("💾 Manual Save Done.")
        except Exception:
            pass

    def _empty_workingset_pid(self, pid: int) -> bool:
        """Windows-only: gọi EmptyWorkingSet để trim RAM process."""
        try:
            k32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            PROCESS_ALL_ACCESS = 0x1F0FFF
            h = k32.OpenProcess(PROCESS_ALL_ACCESS, False, int(pid))
            if not h:
                return False
            try:
                ok = bool(psapi.EmptyWorkingSet(h))
            finally:
                k32.CloseHandle(h)
            return ok
        except Exception:
            return False

    def optimize_ram_now(self):
        """Tối ưu RAM tức thì cho PalServer (và trình quản lý) mà không cần restart."""
        try:
            procs = self._get_palserver_processes()
            if not procs:
                self._enqueue_console("⚠️ Không tìm thấy PalServer để tối ưu RAM.")
                return
            total_before = 0
            for p in procs:
                try:
                    total_before += p.memory_info().rss
                except Exception:
                    pass
            self._enqueue_console("🧹 Đang tối ưu RAM PalServer (EmptyWorkingSet)...")
            for p in procs:
                self._empty_workingset_pid(p.pid)
            # Trim chính app manager để giảm footprint giao diện
            self._empty_workingset_pid(os.getpid())
            time.sleep(0.5)
            total_after = 0
            for p in self._get_palserver_processes():
                try:
                    total_after += p.memory_info().rss
                except Exception:
                    pass
            diff_mb = max((total_before - total_after) / (1024 * 1024), 0)
            self._enqueue_console(f"✅ Tối ưu RAM xong. Giải phóng ~{diff_mb:.1f} MB.")
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi tối ưu RAM: {e}")

    def _ram_monitor_loop(self):
        """Nếu bật auto và RAM hệ thống cao, tự trim PalServer."""
        try:
            if self._ram_auto_opt_var.get():
                used = psutil.virtual_memory().percent
                thr = max(min(int(self._ram_opt_threshold.get()), 95), 50)
                if used >= thr and self._is_server_running():
                    self._enqueue_console(f"⚠️ RAM hệ thống {used:.0f}% ≥ {thr}% → tự tối ưu RAM.")
                    threading.Thread(target=self.optimize_ram_now, daemon=True).start()
        except Exception:
            pass
        finally:
            self.root.after(self._ram_opt_interval_ms, self._ram_monitor_loop)

    def _auto_refresh_server_status_loop(self):
        """Đồng bộ trạng thái server lên UI theo chu kỳ, tránh phải refresh tay."""
        try:
            running = self._is_server_running()
            if hasattr(self, "lbl_status"):
                self.lbl_status.config(
                    text="● SERVER ONLINE" if running else "● SERVER OFFLINE",
                    fg="#00ffcc" if running else "#ff4444"
                )
            # Nếu tab điều khiển đã mở thì đồng bộ luôn màu nút Start/Stop.
            self._update_ctrl_btn_state()
        except Exception:
            pass
        finally:
            self.root.after(self._status_refresh_interval_ms, self._auto_refresh_server_status_loop)

    def server_start(self):
        """Khởi động PalServer thủ công."""
        if self._is_server_running():
            self._enqueue_console("⚠️ Server đang chạy, không cần khởi động lại.")
            messagebox.showinfo("START", "Server đang chạy rồi!")
            return
        self._enqueue_console("▶️ Đang khởi động PalServer an toàn...")
        try:
            if self._start_server_safe(source="Manual Start"):
                self._enqueue_console("✅ Lệnh khởi động đã gửi — chờ server online...")
                self._update_ctrl_btn_state()
            else:
                messagebox.showerror("START Error", f"Không thể khởi động server:\n{SERVER_EXE}")
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi khởi động: {e}")
            messagebox.showerror("START Error", str(e))

    def server_stop(self):
        """Dừng PalServer ngay lập tức (sau khi xác nhận)."""
        if not messagebox.askyesno(
            "⚠️ XÁC NHẬN DỪNG SERVER",
            "DỪNG server ngay bây giờ?\n\n"
            "⚠️ Người chơi sẽ bị ngắt kết nối!\n"
            "Dữ liệu chưa save có thể bị mất!"
        ):
            return
        self._enqueue_console("🛑 Đang dừng PalServer...")

        def _do_stop():
            try:
                requests.post(
                    f"{API_URL}/shutdown",
                    json={"waittime": 0, "message": "Server shutting down"},
                    auth=AUTH, timeout=5
                )
            except Exception:
                pass
            time.sleep(2)
            self._stop_server_processes(force=True, source="Manual Stop")
            self._enqueue_console("✅ Server đã dừng.")
            self.root.after(0, self._update_ctrl_btn_state)

        threading.Thread(target=_do_stop, daemon=True).start()

    def _update_ctrl_btn_state(self):
        """Cập nhật màu sắc / text nút theo trạng thái server."""
        try:
            if not hasattr(self, "_btn_ctrl_start"):
                return
            running = self._is_server_running()
            if running:
                self._btn_ctrl_start.config(
                    state="disabled", bg="#1a4a1a", fg="#336633",
                    text="▶  ĐANG CHẠY"
                )
                self._btn_ctrl_stop.config(
                    state="normal", bg="#7b0000", fg="white",
                    text="⏹  DỪNG SERVER"
                )
                self._lbl_ctrl_status.config(
                    text="● SERVER ONLINE", fg="#00ff88"
                )
            else:
                self._btn_ctrl_start.config(
                    state="normal", bg="#1a5e1a", fg="white",
                    text="▶  KHỞI ĐỘNG"
                )
                self._btn_ctrl_stop.config(
                    state="disabled", bg="#2a0000", fg="#553333",
                    text="⏹  DỪNG SERVER"
                )
                self._lbl_ctrl_status.config(
                    text="● SERVER OFFLINE", fg="#ff4444"
                )
        except Exception:
            pass

    # ─────────────────────────────────────────
    #  DRAW: PLAYERS
    # ─────────────────────────────────────────
    def draw_players(self):
        # State
        self._all_players_data: list = []
        self._players_by_iid:   dict = {}
        self._player_sort_col:  str  = "Lv"
        self._player_sort_rev:  bool = True   # mặc định: cao → thấp

        # ── Title + player count ──────────────────────────────────────
        title_f = tk.Frame(self.container, bg="#0a0a0a")
        title_f.pack(fill="x", pady=(0, 4))
        tk.Label(title_f, text="DANH SÁCH NGƯỜI CHƠI",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        self._lbl_player_count = tk.Label(
            title_f, text="  ⬤ 0 online",
            bg="#0a0a0a", fg="#555",
            font=("Segoe UI", 11, "bold")
        )
        self._lbl_player_count.pack(side="left", padx=8)

        # ── Toolbar ───────────────────────────────────────────────────
        toolbar = tk.Frame(self.container, bg="#0a0a0a")
        toolbar.pack(fill="x", pady=(0, 5))

        tk.Button(toolbar, text="🔄 LÀM MỚI",
                  bg="#1a5276", fg="white", relief="flat", padx=14,
                  command=self._refresh_players_tree).pack(side="left", padx=(0, 6))

        self._player_auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text="⏱ Auto 8s",
                       variable=self._player_auto_var,
                       bg="#0a0a0a", fg="#666", selectcolor="#0a0a0a",
                       activebackground="#0a0a0a",
                       font=("Segoe UI", 9)).pack(side="left", padx=(0, 12))

        # Level legend
        for lv_txt, lv_clr in [
            ("Lv 1–19", "#666"), ("Lv 20–34", "#00cc88"),
            ("Lv 35–49", "#4499ff"), ("Lv 50+", "#ffcc00"),
        ]:
            tk.Label(toolbar, text=f"■ {lv_txt}",
                     bg="#0a0a0a", fg=lv_clr,
                     font=("Segoe UI", 8)).pack(side="left", padx=4)

        # Search
        tk.Label(toolbar, text="🔍",
                 bg="#0a0a0a", fg="#888",
                 font=("Segoe UI", 11)).pack(side="right", padx=(8, 0))
        self._player_filter_var = tk.StringVar()
        self._player_filter_var.trace_add("write", lambda *_: self._filter_player_tree())
        tk.Entry(toolbar, textvariable=self._player_filter_var,
                 bg="#111", fg="#ccc", bd=0,
                 font=("Consolas", 10), insertbackground="#ccc",
                 width=20).pack(side="right", ipady=5)
        tk.Label(toolbar, text="Tìm kiếm:",
                 bg="#0a0a0a", fg="#555",
                 font=("Segoe UI", 8)).pack(side="right", padx=(0, 4))

        # ── Treeview ──────────────────────────────────────────────────
        cols = ("#", "Tên", "Lv", "Ping", "SteamID", "PlayerID", "IP")
        col_w = {
            "#":         38,
            "Tên":      185,
            "Lv":        58,
            "Ping":      72,
            "SteamID":  215,
            "PlayerID": 255,
            "IP":       128,
        }
        col_anchor = {
            "#": "center", "Tên": "w", "Lv": "center",
            "Ping": "center", "SteamID": "center",
            "PlayerID": "center", "IP": "center",
        }

        tree_f = tk.Frame(self.container, bg="#0a0a0a")
        tree_f.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Players.Treeview",
                         background="#0d0d0d", foreground="#ccc",
                         fieldbackground="#0d0d0d", rowheight=24,
                         font=("Consolas", 9))
        style.configure("Players.Treeview.Heading",
                         background="#161616", foreground="#00ffcc",
                         font=("Segoe UI", 9, "bold"))
        style.map("Players.Treeview",
                  background=[("selected", "#1a3a2a")],
                  foreground=[("selected", "#00ffcc")])

        self.player_tree = ttk.Treeview(
            tree_f, columns=cols, show="headings",
            selectmode="browse", style="Players.Treeview"
        )
        for col in cols:
            self.player_tree.heading(
                col, text=col,
                command=lambda c=col: self._player_sort_by(c)
            )
            self.player_tree.column(
                col, width=col_w.get(col, 130),
                anchor=col_anchor.get(col, "center")
            )

        # Level color tags
        self.player_tree.tag_configure("lv_new",  foreground="#666666")
        self.player_tree.tag_configure("lv_mid",  foreground="#00cc88")
        self.player_tree.tag_configure("lv_high", foreground="#4499ff")
        self.player_tree.tag_configure("lv_max",  foreground="#ffcc00")

        vsb = ttk.Scrollbar(tree_f, orient="vertical",
                             command=self.player_tree.yview)
        self.player_tree.configure(yscrollcommand=vsb.set)
        self.player_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Events
        self.player_tree.bind("<<TreeviewSelect>>", self._player_on_select)

        # Right-click context menu
        self._player_ctx = tk.Menu(
            self.root, tearoff=0,
            bg="#1a1a1a", fg="white",
            activebackground="#2a2a2a", activeforeground="#00ffcc"
        )
        self._player_ctx.add_command(
            label="🎁  Give Item  (PD API)",
            command=self._player_give_item_dialog)
        self._player_ctx.add_command(
            label="🐾  Give Pal   (PD API)",
            command=self._player_give_pal_dialog)
        self._player_ctx.add_separator()
        self._player_ctx.add_command(
            label="⚡  Kick player", command=self._player_kick_selected)
        self._player_ctx.add_command(
            label="⛔  Ban player",  command=lambda: self._player_ban_selected(source="RIGHT_CLICK"))
        self._player_ctx.add_separator()
        self._player_ctx.add_command(
            label="📋  Copy SteamID", command=self._player_copy_steamid)
        self._player_ctx.add_command(
            label="📋  Copy PlayerID", command=self._player_copy_playerid)
        self.player_tree.bind("<Button-3>", self._player_ctx_show)

        # ── Action panel ──────────────────────────────────────────────
        action_f = tk.Frame(self.container, bg="#111",
                            highlightthickness=1, highlightbackground="#222",
                            pady=6)
        action_f.pack(fill="x", pady=(4, 0))

        self._lbl_selected_player = tk.Label(
            action_f, text="▶  Nhấp vào người chơi để thao tác",
            bg="#111", fg="#444", font=("Segoe UI", 9)
        )
        self._lbl_selected_player.pack(side="left", padx=12)

        tk.Button(action_f, text="⛔ Ban",
                  bg="#3d0000", fg="#ff4444",
                  relief="flat", padx=14,
                  command=lambda: self._player_ban_selected(source="PLAYER_TAB")).pack(side="right", padx=(4, 8))
        tk.Button(action_f, text="⚡ Kick",
                  bg="#7d1a00", fg="#ff8866",
                  relief="flat", padx=14,
                  command=self._player_kick_selected).pack(side="right", padx=4)

        # Load ngay
        self.root.after(200, self._refresh_players_tree)

    # ─────────────────────────────────────────
    #  DRAW: NEWBIE GIFT
    # ─────────────────────────────────────────
    def draw_newbie_gift(self):
        tk.Label(self.container, text="QUÀ TẶNG",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 10))

        top = tk.Frame(self.container, bg="#0a0a0a")
        top.pack(fill="x")
        tk.Checkbutton(top, text="CHẾ ĐỘ TỰ ĐỘNG",
                       variable=self.newbie_gift_auto,
                       bg="#0a0a0a", fg="#00ffcc", selectcolor="#0a0a0a",
                       font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 16))
        self._lbl_gift_stat_received = tk.Label(
            top, text=f"✅ Đã phát quà tân thủ: {len(self.newbie_gift_received)} người",
            bg="#0a0a0a", fg="#00ffcc", font=("Segoe UI", 10, "bold"))
        self._lbl_gift_stat_received.pack(side="left")
        self._lbl_gift_stat_pending = tk.Label(
            top, text=f"⏳ Đang chờ tân thủ: {len(self.newbie_gift_pending)} người",
            bg="#0a0a0a", fg="#ffcc00", font=("Segoe UI", 10, "bold"))
        self._lbl_gift_stat_pending.pack(side="left", padx=20)

        nb = ttk.Notebook(self.container)
        nb.pack(fill="both", expand=True, pady=(10, 0))

        tab_new = tk.Frame(nb, bg="#0a0a0a")
        tab_daily = tk.Frame(nb, bg="#0a0a0a")
        tab_online = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_new, text="🎁 Quà Tân Thủ")
        nb.add(tab_daily, text="📅 Quà Điểm Danh")
        nb.add(tab_online, text="⏱ Quà Online")

        # ----- TAB 1: NEWBIE -----
        row1 = tk.Frame(tab_new, bg="#0a0a0a", pady=6)
        row1.pack(fill="x")
        tk.Label(row1, text="Template (mỗi dòng: item|pal:ID:Count)", bg="#0a0a0a", fg="#88ccff",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(row1, text="🧪 TEST 1: Thử nhận lần 2", bg="#8e44ad", fg="white", relief="flat", padx=10,
                  command=self.test_gift_second_time).pack(side="right", padx=4)
        tk.Button(row1, text="🎁 TEST 2: Give full bộ quà", bg="#e67e22", fg="white", relief="flat", padx=10,
                  command=self.test_gift_give_all).pack(side="right", padx=4)
        tk.Button(row1, text="💾 Lưu", bg="#145a32", fg="white", relief="flat", padx=10,
                  command=self._save_reward_templates_to_cfg).pack(side="right", padx=4)
        self._newbie_reward_text = scrolledtext.ScrolledText(
            tab_new, height=7, bg="#111", fg="#ddd", bd=0, font=("Consolas", 9), insertbackground="#ddd"
        )
        self._newbie_reward_text.pack(fill="x", pady=(0, 6))
        self._newbie_reward_text.delete("1.0", tk.END)
        self._newbie_reward_text.insert(tk.END, self._newbie_template_to_text(self.newbie_gift_template))

        self.newbie_gift_log = scrolledtext.ScrolledText(
            tab_new, bg="#0d0d0d", fg="#33ff33", font=("Consolas", 9), bd=0, insertbackground="#33ff33"
        )
        self.newbie_gift_log.pack(fill="both", expand=True)

        # ----- TAB 2: DAILY -----
        row2 = tk.Frame(tab_daily, bg="#0a0a0a", pady=6)
        row2.pack(fill="x")
        tk.Label(row2, text="Điểm danh ngày (mỗi dòng: ItemID:Count)", bg="#0a0a0a", fg="#88ccff",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(row2, text="📅 TEST: Phát 1 lượt điểm danh", bg="#2e86c1", fg="white", relief="flat", padx=10,
                  command=self.test_daily_checkin_specific).pack(side="right", padx=4)
        tk.Button(row2, text="🏆 TEST: TOP10 bonus chia đều", bg="#6c3483", fg="white", relief="flat", padx=10,
                  command=self.test_top10_bonus_now).pack(side="right", padx=4)
        self._daily_reward_text = scrolledtext.ScrolledText(
            tab_daily, height=8, bg="#111", fg="#ddd", bd=0, font=("Consolas", 9), insertbackground="#ddd"
        )
        self._daily_reward_text.pack(fill="x", pady=(0, 6))
        self._daily_reward_text.delete("1.0", tk.END)
        self._daily_reward_text.insert(tk.END, self._reward_items_to_text(self.daily_checkin_reward_items))
        self.daily_gift_log = scrolledtext.ScrolledText(
            tab_daily, bg="#0d0d0d", fg="#33ffcc", font=("Consolas", 9), bd=0, insertbackground="#33ffcc"
        )
        self.daily_gift_log.pack(fill="both", expand=True)

        # ----- TAB 3: ONLINE -----
        row3 = tk.Frame(tab_online, bg="#0a0a0a", pady=6)
        row3.pack(fill="x")
        tk.Label(row3, text="Quà online (mỗi dòng: ItemID:Count)", bg="#0a0a0a", fg="#88ffcc",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(row3, text="Mốc phút:", bg="#0a0a0a", fg="#aaa", font=("Segoe UI", 9)).pack(side="right")
        self._online60_minutes_var = tk.StringVar(value=str(max(1, int(self.online60_reward_seconds // 60))))
        tk.Entry(row3, textvariable=self._online60_minutes_var, width=6, bg="#151515", fg="#ddd", bd=0,
                 font=("Consolas", 10), insertbackground="#ddd").pack(side="right", padx=(6, 10), ipady=3)
        tk.Button(row3, text="⏱ TEST: Phát 1 lượt quà online", bg="#16a085", fg="white", relief="flat", padx=10,
                  command=self.test_online60_specific).pack(side="right", padx=4)
        tk.Button(row3, text="💾 Lưu online -> file", bg="#145a32", fg="white", relief="flat", padx=10,
                  command=self._save_online_reward_config_only).pack(side="right", padx=4)
        self._online_reward_text = scrolledtext.ScrolledText(
            tab_online, height=8, bg="#111", fg="#ddd", bd=0, font=("Consolas", 9), insertbackground="#ddd"
        )
        self._online_reward_text.pack(fill="x", pady=(0, 6))
        self._online_reward_text.delete("1.0", tk.END)
        self._online_reward_text.insert(tk.END, self._reward_items_to_text(self.online60_reward_items))
        self.online_gift_log = scrolledtext.ScrolledText(
            tab_online, bg="#0d0d0d", fg="#66ff99", font=("Consolas", 9), bd=0, insertbackground="#66ff99"
        )
        self.online_gift_log.pack(fill="both", expand=True)

        bottom = tk.Frame(self.container, bg="#0a0a0a", pady=6)
        bottom.pack(fill="x")
        tk.Button(bottom, text="💾 LƯU TẤT CẢ CẤU HÌNH QUÀ", bg="#145a32", fg="white",
                  relief="flat", padx=14, pady=6, font=("Segoe UI", 9, "bold"),
                  command=self._save_all_gift_tabs_config).pack(side="left")
        tk.Button(bottom, text="📂 MỞ THƯ MỤC LOG", bg="#1a6e3c", fg="white", relief="flat",
                  padx=12, command=self._open_gift_log_folder).pack(side="left", padx=8)
        tk.Label(bottom, text=f"Config file: {MANAGER_CONFIG_FILE}",
                 bg="#0a0a0a", fg="#555", font=("Consolas", 8)).pack(side="right")

        self.root.after(80, lambda: self._load_any_log_to_ui(self.newbie_gift_log_file, self.newbie_gift_log))
        self.root.after(120, lambda: self._load_any_log_to_ui(self.daily_gift_log_file, self.daily_gift_log))
        self.root.after(160, lambda: self._load_any_log_to_ui(self.online_gift_log_file, self.online_gift_log))
        self.root.after(200, self._refresh_gift_stats)

    # ═════════════════════════════════════════
    #  ANTIBUG SYSTEM
    # ═════════════════════════════════════════

    def _antibug_log(self, msg: str):
        """Ghi log ra UI queue + file + manager console."""
        antibug_enf.antibug_log(self, msg, ANTIBUG_LOG_FILE)

    def _update_antibug_stats_label(self):
        """Cập nhật label thống kê AntiBug trên UI."""
        antibug_enf.update_antibug_stats_label(self)

    def _antibug_parse_line(self, line: str):
        """Parse dòng log PalDefender → dict sự kiện build/dismantle, hoặc None."""
        return antibug_core.parse_antibug_line(line, _ANTIBUG_RE)

    def _antibug_process_event(self, event: dict):
        """Kiểm tra tốc độ build/dismantle, kích hoạt cảnh báo/kick khi vượt ngưỡng."""
        def _run_buildcheck(steamid: str, name: str, obj: str):
            threading.Thread(
                target=self._buildbug_check_event,
                args=(steamid, name, obj),
                daemon=True
            ).start()

        def _run_techcheck(steamid: str, name: str, obj: str):
            self._techbug_check_event(steamid, name, obj, source="build")

        def _run_kick(steamid: str, name: str, action_vn: str, count_1s: int, obj: str):
            threading.Thread(
                target=self._antibug_kick_player,
                args=(steamid, name, action_vn, count_1s, obj),
                daemon=True
            ).start()

        antibug_core.process_antibug_event(
            event,
            antibug_enabled=self.antibug_enabled.get(),
            buildcheck_enabled=self.antibug_buildcheck_enabled.get(),
            max_per_sec=self.antibug_max_per_sec.get(),
            events_store=self._antibug_events,
            run_buildcheck=_run_buildcheck,
            run_techcheck=_run_techcheck,
            run_kick=_run_kick,
        )

    # ── REST API helpers ──────────────────────────────────────────────
    def _api_announce(self, message: str) -> bool:
        """Broadcast thông báo qua REST API /v1/api/announce."""
        try:
            res = requests.post(
                f"{API_URL}/announce",
                json={"message": message},
                auth=AUTH, timeout=5
            )
            return res.status_code == 200
        except Exception:
            return False

    def _api_kick(self, steamid: str, reason: str) -> tuple:
        """Kick người chơi qua REST API /v1/api/kick. Trả về (ok, status_code)."""
        try:
            res = requests.post(
                f"{API_URL}/kick",
                json={"userid": steamid, "message": reason},
                auth=AUTH, timeout=5
            )
            return res.status_code == 200, res.status_code
        except Exception as e:
            return False, str(e)

    def _api_ban(self, steamid: str, reason: str) -> tuple:
        """Ban người chơi qua REST API /v1/api/ban. Trả về (ok, status_code)."""
        try:
            res = requests.post(
                f"{API_URL}/ban",
                json={"userid": steamid, "message": reason},
                auth=AUTH, timeout=5
            )
            return res.status_code == 200, res.status_code
        except Exception as e:
            return False, str(e)

    def _api_unban(self, steamid: str) -> tuple:
        """Unban người chơi qua REST API /v1/api/unban. Trả về (ok, status_code)."""
        try:
            res = requests.post(
                f"{API_URL}/unban",
                json={"userid": steamid},
                auth=AUTH, timeout=5
            )
            return res.status_code == 200, res.status_code
        except Exception as e:
            return False, str(e)

    def _read_antibug_banlist_entries(self) -> list[dict]:
        """Đọc banlist.txt và trả về danh sách còn đang bị ban theo thứ tự mới nhất trước."""
        return antibug_core.read_antibug_banlist_entries(ANTIBUG_BAN_FILE)

    def _unban_steamid_common(self, sid: str, source: str = "MANUAL") -> tuple[bool, str]:
        """Luồng unban dùng chung cho UI và Discord bot."""
        sid = self._normalize_steamid((sid or "").strip())
        if not sid:
            return False, "SteamID không hợp lệ"

        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ok, code = self._api_unban(sid)
        status = f"✅ Đã Xác Minh ✅ {code}" if ok else f"❌ HTTP {code}"
        msg = (
            f"🔓 UNBAN  [{ts_now}]\n"
            f"   SteamID       : {sid}\n"
            f"   Kết quả thẩm phán   : {status}\n"
            f"   Nguồn thao tác: {source}"
        )
        self._antibug_log(msg)

        try:
            with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{'─'*60}\n"
                    f"  [UNBAN]  {ts_now}  — {source}\n"
                    f"  SteamID  : {sid}\n"
                    f"  API Unban: {status}\n"
                    f"{'─'*60}\n\n"
                )
        except Exception:
            pass

        if self.antibug_discord_alert.get():
            threading.Thread(
                target=self._send_antibug_discord,
                args=(f"🔓 **[ANTIBUG — GỠ BAN]**\n"
                      f"🆔 **SteamID:** `{sid}`\n"
                      f"🕐 **Thời gian:** `{ts_now}`\n"
                      f"📍 **Nguồn thao tác:** `{source}`\n"
                      f"🌐 **Kết quả thẩm phán gỡ ban:** {status}",),
                daemon=True
            ).start()

        return ok, f"{status}\nSteamID: {sid}"

    # ══════════════════════════════════════════════════════════════════════
    #  PALDEFENDER REST API HELPERS
    # ══════════════════════════════════════════════════════════════════════

    def _pdapi_ensure_token(self) -> str:
        """Đọc hoặc tự tạo token cho PalDefender REST API.
        Trả về chuỗi token. Tạo file serverpal_manager.json nếu chưa có."""
        try:
            os.makedirs(PALDEF_TOKEN_DIR, exist_ok=True)
            if os.path.isfile(PALDEF_TOKEN_FILE):
                with open(PALDEF_TOKEN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                token = data.get("Token", "").strip()
                if token:
                    return token
            # Tạo token mới
            token = secrets.token_urlsafe(48)
            with open(PALDEF_TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump({"Token": token}, f, indent=4)
            self._enqueue_console(
                f"🔑 [PD-API] Đã tạo token mới → {PALDEF_TOKEN_FILE}"
            )
            return token
        except Exception as e:
            self._enqueue_console(f"❌ [PD-API] Lỗi tạo token: {e}")
            return ""

    def _pdapi_headers(self) -> dict:
        """Trả về Authorization header cho PalDefender API."""
        return {"Authorization": f"Bearer {self._pdapi_token}"}

    def _pdapi_get_version(self) -> dict:
        """GET /v1/pdapi/version — Kiểm tra kết nối & version PalDefender."""
        try:
            res = requests.get(
                f"{PALDEF_API_BASE}/v1/pdapi/version",
                headers=self._pdapi_headers(), timeout=4
            )
            if res.status_code == 200:
                return {"ok": True, "data": res.json()}
            return {"ok": False, "code": res.status_code, "data": {}}
        except Exception as e:
            return {"ok": False, "error": str(e), "data": {}}

    def _pdapi_get_guilds(self) -> dict:
        """GET /v1/pdapi/guilds — Lấy danh sách tất cả guild."""
        try:
            res = requests.get(
                f"{PALDEF_API_BASE}/v1/pdapi/guilds",
                headers=self._pdapi_headers(), timeout=6
            )
            if res.status_code == 200:
                return {"ok": True, "data": res.json()}
            return {"ok": False, "code": res.status_code, "data": {}}
        except Exception as e:
            return {"ok": False, "error": str(e), "data": {}}

    def _pdapi_get_guild(self, guild_id: str) -> dict:
        """GET /v1/pdapi/guild/<guild_id> — Chi tiết 1 guild."""
        try:
            res = requests.get(
                f"{PALDEF_API_BASE}/v1/pdapi/guild/{guild_id}",
                headers=self._pdapi_headers(), timeout=6
            )
            if res.status_code == 200:
                return {"ok": True, "data": res.json()}
            return {"ok": False, "code": res.status_code, "data": {}}
        except Exception as e:
            return {"ok": False, "error": str(e), "data": {}}

    def _pdapi_give(self, steamid: str, payload: dict) -> tuple:
        """POST /v1/pdapi/give — Grant EXP/item/pal/egg (atomic).
        payload ví dụ: {"EXP": 1000, "Item": [{"ItemID": "PalSphere", "Count": 10}]}
        Trả về (ok: bool, data: dict)."""
        try:
            body = {"UserID": steamid, **payload}
            res = requests.post(
                f"{PALDEF_API_BASE}/v1/pdapi/give",
                json=body,
                headers=self._pdapi_headers(), timeout=8
            )
            data = {}
            try:
                data = res.json()
            except Exception:
                pass
            ok = (res.status_code == 200 and data.get("Errors", 1) == 0)
            return ok, data
        except Exception as e:
            return False, {"error": str(e)}

    def _pdapi_status_poll(self):
        """Vòng lặp nền: cứ 30s ping PD API 1 lần để cập nhật status label."""
        while True:
            try:
                result = self._pdapi_get_version()
                if result["ok"]:
                    d = result["data"]
                    # Version có thể là string hoặc object {"Major":1,"Minor":7,"Patch":2}
                    ver = d.get("Version", d.get("version", ""))
                    if isinstance(ver, dict):
                        ver = (f"{ver.get('Major','?')}."
                               f"{ver.get('Minor','?')}."
                               f"{ver.get('Patch','?')}")
                    elif not ver:
                        # Thử lấy trực tiếp từ root object
                        maj = d.get("Major", "")
                        if maj:
                            ver = (f"{d.get('Major','?')}."
                                   f"{d.get('Minor','?')}."
                                   f"{d.get('Patch','?')}")
                        else:
                            ver = "OK"
                    self._pdapi_status_ok  = True
                    self._pdapi_version    = str(ver)
                else:
                    self._pdapi_status_ok = False
                    self._pdapi_version   = ""
            except Exception:
                self._pdapi_status_ok = False
                self._pdapi_version   = ""
            # Cập nhật label trên UI thread
            try:
                self.root.after(0, self._pdapi_update_status_label)
            except Exception:
                pass
            time.sleep(30)

    def _pdapi_update_status_label(self):
        """Cập nhật label trạng thái PD API trên UI."""
        try:
            if not hasattr(self, "_lbl_pdapi_status"):
                return
            if self._pdapi_status_ok:
                txt = f"🟢 Kết nối OK  │  PD v{self._pdapi_version}"
                clr = "#00ff88"
            else:
                txt = "🔴 Không kết nối được PalDefender REST API"
                clr = "#ff4444"
            self._lbl_pdapi_status.config(text=txt, fg=clr)
        except Exception:
            pass

    def _send_antibug_discord(self, content: str):
        """Gửi cảnh báo đến webhook AntiBug riêng biệt (chi tiết hơn)."""
        antibug_enf.send_antibug_discord(
            self,
            content,
            _read_manager_cfg,
            ANTIBUG_WEBHOOK_URL,
            DISCORD_WEBHOOK_URL,
        )

    def _write_banlist(self, steamid: str, name: str, kick_count: int,
                       kick_details: list, ts_now: str, api_status: str):
        """Ghi bản ghi BAN vào banlist.txt với đầy đủ thông tin chi tiết."""
        antibug_enf.write_banlist(
            self, steamid, name, kick_count, kick_details, ts_now, api_status,
            ANTIBUG_BAN_FILE, ANTIBUG_MAX_KICKS
        )

    # ── Core AntiBug enforcement ───────────────────────────────────────
    def _antibug_kick_player(self, steamid: str, name: str,
                              action_vn: str, count: int, obj: str):
        """Phát cảnh báo (REST API) → Kick (REST API) → theo dõi → ban nếu cần."""
        antibug_enf.antibug_kick_player(
            self, steamid, name, action_vn, count, obj, ANTIBUG_MAX_KICKS, ANTIBUG_KICK_WINDOW
        )

    def _antibug_ban_player(self, steamid: str, name: str, kick_count: int):
        """Ban vĩnh viễn qua REST API, ghi banlist.txt chi tiết, Discord chi tiết."""
        antibug_enf.antibug_ban_player(self, steamid, name, kick_count)

    # ── NPC Attack / Capture Protection ───────────────────────────────────────

    def _npc_attack_kick_player(self, steamid: str, player_name: str,
                                npc_name: str, npc_id: str, coords: str):
        """Kick người chơi khi phát hiện tấn công NPC.
        Cooldown 60 giây / người chơi để tránh kick spam.
        Thực hiện: thông báo → kick API → Discord cảnh báo.
        """
        steamid = self._normalize_steamid(steamid)
        if not steamid:
            return

        now = time.time()
        ev  = self._npc_attack_events.get(steamid, {"last_kick": 0.0, "count": 0})

        # Cooldown 60 giây — tránh kick liên tục cùng 1 người
        if now - ev["last_kick"] < 60:
            return

        ev["last_kick"] = now
        ev["count"]    += 1
        self._npc_attack_events[steamid] = ev
        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        loc    = f"`{coords}`" if coords else "*không rõ*"

        # 1. Broadcast cảnh báo toàn server
        self._api_announce(
            f"[CANH BAO] {player_name} da tan cong NPC ({npc_name}) va bi KICK!"
        )
        time.sleep(0.3)

        # 2. Kick qua REST API
        kick_reason = f"[NPC-ATTACK] Tan cong NPC '{npc_name}' ({npc_id}) — CANH BAO KICK"
        kick_ok, kick_code = self._api_kick(steamid, kick_reason)
        kick_status = f"✅ Đã Xác Minh ✅ {kick_code}" if kick_ok else f"❌ HTTP {kick_code}"

        self._antibug_kick_total += 1

        # 3. Log UI console
        msg = (
            f"⚡ NPC-ATTACK KICK #{self._antibug_kick_total}  [{ts_now}]\n"
            f"   Người chơi   : {player_name}  ({steamid})\n"
            f"   NPC bị tấn công: {npc_name}  (ID: {npc_id})\n"
            f"   Tọa độ       : {coords or 'N/A'}\n"
            f"   Vi phạm lần  : {ev['count']}\n"
            f"   API Kick     : {kick_status}"
        )
        self._antibug_log(msg)

        # 4. Discord AntiBug webhook — thông báo đầy đủ
        if self.antibug_discord_alert.get():
            disc = (
                f"⚡ **[TẤN CÔNG NPC — AUTO KICK #{self._antibug_kick_total}]**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Người chơi:** `{player_name}`\n"
                f"🆔 **SteamID:** `{steamid}`\n"
                f"🕐 **Thời gian:** `{ts_now}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 **NPC bị tấn công:** `{npc_name}`  `({npc_id})`\n"
                f"📍 **Tọa độ:** {loc}\n"
                f"🔢 **Vi phạm lần:** {ev['count']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 **Hành vi vi phạm:**\n"
                f"   > Người chơi đã **cố ý tấn công NPC thương nhân** trên server.\n"
                f"   > NPC này được bảo vệ — mọi hành vi tấn công / cố bắt đều bị xử lý.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚖️ **Xử lý:** KICK khỏi server (lần {ev['count']})\n"
                f"🌐 **Kết quả thẩm phán kick:** {kick_status}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ *Tiếp tục vi phạm → BAN VĨNH VIỄN khi bắt thành công NPC!*"
            )
            threading.Thread(
                target=self._send_antibug_discord,
                args=(disc,), daemon=True
            ).start()

    def _npc_capture_ban_player(self, steamid: str, player_name: str,
                                pal_name: str, pal_id: str, coords: str = ""):
        """Ban vĩnh viễn người chơi đã bắt thành công NPC (SalesPerson, BlackMarketTrader, …).
        Thực hiện: thông báo → ban API → ghi banlist.txt → Discord đầy đủ.
        """
        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        loc    = coords if coords else "N/A"

        # Số lần đã bị kick trước đó (do tấn công NPC)
        prior_kicks = self._npc_attack_events.get(
            self._normalize_steamid(steamid) or steamid, {}
        ).get("count", 0)

        # 1. Broadcast cảnh báo toàn server
        self._api_announce(
            f"[BAN] {player_name} da bi BAN VINH VIEN vi bat NPC ({pal_name})!"
        )

        # 2. Ban qua REST API /ban
        ban_reason = (
            f"[NPC-CAPTURE] Bat NPC '{pal_name}' ({pal_id}) tai {loc} — AUTO-BAN VINH VIEN"
        )
        ban_ok, ban_code = self._api_ban(steamid, ban_reason)
        ban_status = f"✅ Đã Xác Minh ✅ {ban_code}" if ban_ok else f"❌ HTTP {ban_code}"

        self._antibug_ban_total += 1

        # 3. Ghi banlist.txt chi tiết
        try:
            sep = "═" * 72
            lines = [
                sep,
                f"  [BAN #{self._antibug_ban_total}]  {ts_now}  — NPC CAPTURE AUTO-BAN",
                sep,
                f"  Tên ingame    : {player_name}",
                f"  SteamID       : {steamid}",
                f"  Thời gian ban : {ts_now}",
                f"  Hành vi       : Bắt thành công NPC '{pal_name}' (ID: {pal_id})",
                f"  Tọa độ        : {loc}",
                f"  Kick trước đó : {prior_kicks} lần (tấn công NPC)",
                f"  Lý do ban     : Vi phạm quy tắc bảo vệ NPC thương nhân",
                f"  API Ban       : {ban_status}",
                f"", sep, "",
            ]
            with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi ghi banlist.txt (NPC ban): {e}")

        # 4. Log UI console
        msg = (
            f"🚫 NPC-CAPTURE BAN #{self._antibug_ban_total}  [{ts_now}]\n"
            f"   Người chơi   : {player_name}  ({steamid})\n"
            f"   NPC bị bắt   : {pal_name}  (ID: {pal_id})\n"
            f"   Tọa độ       : {loc}\n"
            f"   Kick trước đó: {prior_kicks} lần\n"
            f"   API Ban      : {ban_status}\n"
            f"   File         : banlist.txt đã được cập nhật"
        )
        self._antibug_log(msg)

        # 5. Discord AntiBug webhook — thông báo đầy đủ
        if self.antibug_discord_alert.get():
            prior_txt = (f"⚡ Đã bị kick **{prior_kicks} lần** trước đó do tấn công NPC"
                         if prior_kicks > 0 else "*(chưa có lịch sử kick NPC)*")
            disc = (
                f"🚫 **[BẮT NPC — BAN VĨNH VIỄN #{self._antibug_ban_total}]**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Người chơi:** `{player_name}`\n"
                f"🆔 **SteamID:** `{steamid}`\n"
                f"🕐 **Thời gian:** `{ts_now}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 **NPC bị bắt:** `{pal_name}`  `({pal_id})`\n"
                f"📍 **Tọa độ:** `{loc}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 **Hành vi vi phạm:**\n"
                f"   > Người chơi đã **bắt thành công NPC thương nhân** bằng Palsphere.\n"
                f"   > Đây là hành vi phá hoại nghiêm trọng — NPC bị xóa khỏi thế giới game.\n"
                f"   > Lịch sử: {prior_txt}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚖️ **Xử lý:** BAN VĨNH VIỄN (không thể vào server)\n"
                f"🌐 **Kết quả thẩm phán ban:** {ban_status}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f">>> ⛔ **ĐÃ BAN VĨNH VIỄN** — ghi vào `banlist.txt` <<<"
            )
            threading.Thread(
                target=self._send_antibug_discord,
                args=(disc,), daemon=True
            ).start()

    # ── Tech-Cheat System ──────────────────────────────────────────────────────

    def _techbug_check_event(self, steamid: str, name: str, tech_raw: str,
                             source: str = "natural"):
        """
        Kiểm tra tech-cheat khi phát hiện sự kiện mở khóa công nghệ.

        source = "natural"   → 'X' (...) unlocking Technology: 'Y'  (học tự nhiên)
        source = "learntech" → Replying to 'X': "Successfully unlocked technology 'Y'"
                               (admin dùng /learntech — cheat)
        source = "build"     → 'X' (...) has build a 'Y' (xây dựng)
        """
        if not self.antibug_techcheck_enabled.get():
            return

        # ── Xác định đây là admin cheat (learntech) hay học tự nhiên ─────────
        is_admin = steamid in self._admin_mode_players
        is_learntech = (source == "learntech")
        is_build = (source == "build")

        if is_learntech:
            # /learntech luôn là hành vi cheat (admin dùng lệnh để mở khóa tức thì)
            # Chỉ bỏ qua nếu "Ban cả Admin" TẮT
            if not self.techcheck_ban_admin.get():
                self._antibug_log_queue.put(
                    f"[TECH-CHECK] /learntech '{tech_raw}' — {name} admin mode, "
                    f"'Ban Admin' TẮT → bỏ qua."
                )
                return
            # Nếu "Ban Admin" BẬT → tiếp tục check và ban
        else:
            # Học tự nhiên — bỏ qua nếu đang admin mode và "Ban Admin" TẮT
            # Học tự nhiên hoặc Xây dựng — bỏ qua nếu đang admin mode và "Ban Admin" TẮT
            if is_admin and not self.techcheck_ban_admin.get():
                return

        # ── Lookup DB theo internal code (case-insensitive) ──────────────────
        tech_key  = tech_raw.lower().strip()
        req_level = TECH_LEVEL_DB.get(tech_key)

        if req_level is None:
            self._antibug_log_queue.put(
                f"[TECH-DB MISS] '{tech_raw}' — chưa có trong DB, bỏ qua ({name})"
            )
            return

        # ── Lấy level từ cache; nếu trống → fetch API ngay ──────────────────
        player_level = self._player_level_cache.get(steamid, 0)
        if player_level <= 0:
            self._antibug_log_queue.put(
                f"[TECH-CHECK] Cache miss cho {name} — đang fetch API..."
            )
            try:
                res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if res.status_code == 200:
                    for p in res.json().get("players", []):
                        sid = self._normalize_steamid(p.get("userId", ""))
                        if sid == steamid:
                            lv = int(p.get("level") or 0)
                            if lv > 0:
                                player_level = lv
                                self._player_level_cache[steamid] = lv
                            break
            except Exception as e:
                self._antibug_log_queue.put(
                    f"[TECH-CHECK] Lỗi fetch API: {e}"
                )

        if player_level <= 0:
            self._antibug_log_queue.put(
                f"[TECH-CHECK] Không lấy được level của {name} "
                f"({steamid}) — bỏ qua để tránh false positive"
            )
            return

        # ── Log chi tiết sự kiện để debug ────────────────────────────────────
        src_label = "🔧/learntech" if is_learntech else "📖Tự học"
        if is_learntech:
            src_label = "🔧/learntech"
        elif is_build:
            src_label = "🔨Xây dựng"
        else:
            src_label = "📖Tự học"
            
        self._antibug_log_queue.put(
            f"[TECH-CHECK] [{src_label}] {name} (Lv.{player_level}) → "
            f"'{tech_raw}' (cần Lv.{req_level})"
        )

        if player_level >= req_level:
            return  # Hợp lệ — level đủ

        # ── Vi phạm! ──────────────────────────────────────────────────────────
        gap    = req_level - player_level
        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cheat_type = "ADMIN /learntech CHEAT" if is_learntech else "TECH-CHEAT tự học vượt cấp"
        if is_learntech:
            cheat_type = "ADMIN /learntech CHEAT"
        elif is_build:
            cheat_type = "BUILD-CHEAT xây dựng vượt cấp"
        else:
            cheat_type = "TECH-CHEAT tự học vượt cấp"
            
        msg = (
            f"🔬 {cheat_type} PHÁT HIỆN  [{ts_now}]\n"
            f"   Người chơi      : {name}  ({steamid})\n"
            f"   Level hiện tại  : {player_level}\n"
            f"   Công nghệ       : '{tech_raw}'\n"
            f"   Level cần thiết : {req_level}\n"
            f"   Nguồn phát hiện : {src_label}\n"
            f"   Vượt cấp        : +{gap} level → BAN đang xử lý..."
        )
        self._antibug_log(msg)

        threading.Thread(
            target=self._techbug_ban,
            args=(steamid, name, tech_raw, player_level, req_level, gap,
                  ts_now, is_learntech, source),
            daemon=True
        ).start()

    def _techbug_ban(self, steamid: str, name: str, tech_raw: str,
                     cached_level: int, req_level: int, gap: int, ts_now: str,
                     is_learntech: bool = False, source: str = "natural"):
        """Xác nhận level thực tế từ API rồi ban người chơi tech-cheat."""

        cheat_label = "ADMIN /learntech CHEAT" if is_learntech else "TECH-CHEAT"
        src_icon    = "🔧" if is_learntech else "🔬"
        is_learntech = (source == "learntech")
        is_build = (source == "build")

        if is_learntech:
            cheat_label = "ADMIN /learntech CHEAT"
            src_icon    = "🔧"
        elif is_build:
            cheat_label = "BUILD-CHEAT"
            src_icon    = "🔨"
        else:
            cheat_label = "TECH-CHEAT"
            src_icon    = "🔬"

        # ── Với learntech: KHÔNG cần xác nhận level vì đây là lệnh cheat rõ ràng ─
        # ── Với tự học: xác nhận lại để tránh false positive ─────────────────────
        # ── Với tự học/xây dựng: xác nhận lại để tránh false positive ─────────────────────
        confirmed_level = cached_level
        if not is_learntech:
            try:
                res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if res.status_code == 200:
                    for p in res.json().get("players", []):
                        sid = self._normalize_steamid(p.get("userId", ""))
                        if sid == steamid:
                            real_lv = int(p.get("level") or 0)
                            if real_lv > 0:
                                confirmed_level = real_lv
                            break
            except Exception:
                pass

            if confirmed_level <= 0:
                confirmed_level = cached_level

            # Hủy nếu level thực tế đủ (false positive)
            if confirmed_level > 0 and confirmed_level >= req_level:
                self._antibug_log(
                    f"✅ FALSE POSITIVE HỦY: {name} level thực tế "
                    f"{confirmed_level} >= yêu cầu {req_level} — không ban"
                )
                return
        else:
            # /learntech → luôn ban, không cần xác nhận lại
            # Cố fetch để ghi chính xác level thực tế vào log
            try:
                res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if res.status_code == 200:
                    for p in res.json().get("players", []):
                        sid = self._normalize_steamid(p.get("userId", ""))
                        if sid == steamid:
                            real_lv = int(p.get("level") or 0)
                            if real_lv > 0:
                                confirmed_level = real_lv
                            break
            except Exception:
                pass

        # ── Ban via REST API ─────────────────────────────────────────────────
        ban_reason = (
            f"[{cheat_label}] '{tech_raw}' can Lv.{req_level}, "
            f"level hien tai {confirmed_level} (+{gap})"
        )
        ban_ok, ban_code = self._api_ban(steamid, ban_reason)
        ban_status = f"✅ Đã Xác Minh ✅ {ban_code}" if ban_ok else f"❌ HTTP {ban_code}"

        # ── Broadcast toàn server ────────────────────────────────────────────
        if is_learntech:
            announce_msg = (
                f"[ADMIN CHEAT] {name} (Lv.{confirmed_level}) bi BAN vi dung "
                f"/learntech mo '{tech_raw}' (can Lv.{req_level})!"
            )
        elif is_build:
            announce_msg = (
                f"[BUILD-CHEAT] {name} (Lv.{confirmed_level}) bi BAN vi xay dung "
                f"'{tech_raw}' (can Lv.{req_level}) bang tool!"
            )
        else:
            announce_msg = (
                f"[TECH-CHEAT] {name} (Lv.{confirmed_level}) bi BAN vi mo khoa "
                f"'{tech_raw}' (can Lv.{req_level}) bang tool!"
            )
        self._api_announce(announce_msg)

        # ── Ghi banlist.txt chi tiết ─────────────────────────────────────────
        self._antibug_ban_total += 1
        sep = "═" * 72
        try:
            with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{sep}\n"
                    f"  [BAN #{self._antibug_ban_total} — {cheat_label}]  {ts_now}\n"
                    f"{sep}\n"
                    f"  Tên ingame        : {name}\n"
                    f"  SteamID           : {steamid}\n"
                    f"  Loại vi phạm      : {'Dùng lệnh /learntech mở khóa cheat' if is_learntech else 'Mở khóa công nghệ vượt cấp (học tự nhiên)'}\n"
                    f"  Loại vi phạm      : {'Dùng lệnh /learntech mở khóa cheat' if is_learntech else 'Xây dựng công trình vượt cấp' if is_build else 'Mở khóa công nghệ vượt cấp (học tự nhiên)'}\n"
                    f"  Công nghệ vi phạm : '{tech_raw}'\n"
                    f"  Level cần thiết   : {req_level}\n"
                    f"  Level thực tế     : {confirmed_level}\n"
                    f"  Vượt cấp          : +{gap} level\n"
                    f"  Nguồn phát hiện   : {'PalServer.log — /learntech command' if is_learntech else 'PalServer.log — unlocking Technology'}\n"
                    f"  Nguồn phát hiện   : {'PalServer.log — /learntech command' if is_learntech else 'PalServer.log — has build a' if is_build else 'PalServer.log — unlocking Technology'}\n"
                    f"  API Ban           : {ban_status}\n"
                    f"  Thời gian         : {ts_now}\n"
                    f"  Nguồn DB          : https://paldeck.cc/technology\n"
                    f"{sep}\n\n"
                )
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi ghi banlist: {e}")

        # ── Log UI ───────────────────────────────────────────────────────────
        self._antibug_log(
            f"{src_icon} BAN #{self._antibug_ban_total} [{cheat_label}]  [{ts_now}]\n"
            f"   {name} ({steamid})\n"
            f"   '{tech_raw}'  │  Lv.{confirmed_level} < yêu cầu Lv.{req_level} "
            f"(+{gap})  │  API: {ban_status}"
        )

        # ── Discord chi tiết ─────────────────────────────────────────────────
        if self.antibug_discord_alert.get():
            if is_learntech:
                discord_title = f"🔧 **[ADMIN /learntech CHEAT — BAN VĨNH VIỄN #{self._antibug_ban_total}]**"
                discord_footer = ">>> ⛔ **ĐÃ BAN VĨNH VIỄN** — admin dùng /learntech để cheat công nghệ vượt cấp <<<"
                violation_type = "Dùng lệnh /learntech (admin command cheat)"
            elif is_build:
                discord_title = f"🔨 **[BUILD-CHEAT — BAN VĨNH VIỄN #{self._antibug_ban_total}]**"
                discord_footer = ">>> ⛔ **ĐÃ BAN VĨNH VIỄN** — xây dựng công trình vượt cấp <<<"
                violation_type = "Xây dựng công trình vượt cấp (tool/hack)"
            else:
                discord_title = f"🔬 **[TECH-CHEAT — BAN VĨNH VIỄN #{self._antibug_ban_total}]**"
                discord_footer = ">>> ⛔ **ĐÃ BAN VĨNH VIỄN** — dùng tool mở khóa công nghệ vượt cấp <<<"
                violation_type = "Học tự nhiên công nghệ vượt cấp (tool/hack)"
            threading.Thread(
                target=self._send_antibug_discord,
                args=(
                    f"{discord_title}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **Người chơi:** {name}\n"
                    f"🆔 **SteamID:** `{steamid}`\n"
                    f"🕐 **Thời gian:** `{ts_now}`\n"
                    f"🔬 **Công nghệ vi phạm:** `{tech_raw}`\n"
                    f"📊 **Level cần thiết:** `{req_level}`  │  "
                    f"**Level thực tế:** `{confirmed_level}`\n"
                    f"⚡ **Vượt cấp:** `+{gap} level`\n"
                    f"⚠️ **Loại vi phạm:** {violation_type}\n"
                    f"🌐 **Kết quả thẩm phán ban:** {ban_status}\n"
                    f"📚 **DB nguồn:** https://paldeck.cc/technology\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{discord_footer}",
                ),
                daemon=True
            ).start()

    def _buildbug_check_event(self, steamid: str, name: str, item_name: str):
        """
        Kiểm tra build-cheat khi phát hiện sự kiện xây dựng.
        """
        if not self.antibug_buildcheck_enabled.get():
            return

        is_admin = steamid in self._admin_mode_players
        if is_admin and not self.techcheck_ban_admin.get():
            return

        item_key = item_name.lower().strip()
        req_level = TECH_LEVEL_DB.get(item_key)

        if req_level is None:
            # Not all buildable items are in the tech DB, so we don't log this
            return

        player_level = self._player_level_cache.get(steamid, 0)
        if player_level <= 0:
            try:
                res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if res.status_code == 200:
                    for p in res.json().get("players", []):
                        sid = self._normalize_steamid(p.get("userId", ""))
                        if sid == steamid:
                            lv = int(p.get("level") or 0)
                            if lv > 0:
                                player_level = lv
                                self._player_level_cache[steamid] = lv
                            break
            except Exception as e:
                self._antibug_log_queue.put(
                    f"[BUILD-CHECK] Lỗi fetch API: {e}"
                )

        if player_level <= 0:
            self._antibug_log_queue.put(
                f"[BUILD-CHECK] Không lấy được level của {name} ({steamid}) — bỏ qua"
            )
            return

        self._antibug_log_queue.put(
            f"[BUILD-CHECK] [🏗️Xây dựng] {name} (Lv.{player_level}) → "
            f"'{item_name}' (cần Lv.{req_level})"
        )

        if player_level >= req_level:
            return  # Hợp lệ

        gap = req_level - player_level
        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"🏗️ BUILD-CHEAT PHÁT HIỆN  [{ts_now}]\n"
            f"   Người chơi      : {name}  ({steamid})\n"
            f"   Level hiện tại  : {player_level}\n"
            f"   Công trình      : '{item_name}'\n"
            f"   Level cần thiết : {req_level}\n"
            f"   Vượt cấp        : +{gap} level → BAN đang xử lý..."
        )
        self._antibug_log(msg)

        threading.Thread(
            target=self._buildbug_ban,
            args=(steamid, name, item_name, player_level, req_level, gap, ts_now),
            daemon=True
        ).start()

    def _buildbug_ban(self, steamid: str, name: str, item_name: str,
                      cached_level: int, req_level: int, gap: int, ts_now: str):
        """Xác nhận level thực tế từ API rồi ban người chơi build-cheat."""
        
        confirmed_level = cached_level
        try:
            res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
            if res.status_code == 200:
                for p in res.json().get("players", []):
                    sid = self._normalize_steamid(p.get("userId", ""))
                    if sid == steamid:
                        real_lv = int(p.get("level") or 0)
                        if real_lv > 0:
                            confirmed_level = real_lv
                        break
        except Exception:
            pass

        if confirmed_level > 0 and confirmed_level >= req_level:
            self._antibug_log(
                f"✅ FALSE POSITIVE HỦY: {name} level thực tế "
                f"{confirmed_level} >= yêu cầu {req_level} — không ban"
            )
            return

        ban_reason = (
            f"[BUILD-CHEAT] Built '{item_name}' (req Lv.{req_level}) "
            f"at Lv.{confirmed_level} (+{gap})"
        )
        ban_ok, ban_code = self._api_ban(steamid, ban_reason)
        ban_status = f"✅ Đã Xác Minh ✅ {ban_code}" if ban_ok else f"❌ HTTP {ban_code}"

        announce_msg = (
            f"[BUILD-CHEAT] {name} (Lv.{confirmed_level}) bi BAN vi xay dung "
            f"'{item_name}' (can Lv.{req_level}) ma khong can mo khoa!"
        )
        self._api_announce(announce_msg)

        self._antibug_ban_total += 1
        sep = "═" * 72
        try:
            with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{sep}\n"
                    f"  [BAN #{self._antibug_ban_total} — BUILD-CHEAT]  {ts_now}\n"
                    f"{sep}\n"
                    f"  Tên ingame        : {name}\n"
                    f"  SteamID           : {steamid}\n"
                    f"  Loại vi phạm      : Xây dựng công trình vượt cấp\n"
                    f"  Công trình        : '{item_name}'\n"
                    f"  Level cần thiết   : {req_level}\n"
                    f"  Level thực tế     : {confirmed_level}\n"
                    f"  Vượt cấp          : +{gap} level\n"
                    f"  API Ban           : {ban_status}\n"
                    f"  Thời gian         : {ts_now}\n"
                    f"{sep}\n\n"
                )
        except Exception as e:
            self._enqueue_console(f"❌ Lỗi ghi banlist: {e}")

        self._antibug_log(
            f"🏗️ BAN #{self._antibug_ban_total} [BUILD-CHEAT]  [{ts_now}]\n"
            f"   {name} ({steamid})\n"
            f"   '{item_name}'  │  Lv.{confirmed_level} < yêu cầu Lv.{req_level} "
            f"(+{gap})  │  API: {ban_status}"
        )

        if self.antibug_discord_alert.get():
            discord_title = f"🏗️ **[BUILD-CHEAT — BAN VĨNH VIỄN #{self._antibug_ban_total}]**"
            discord_footer = ">>> ⛔ **ĐÃ BAN VĨNH VIỄN** — xây dựng công trình vượt cấp <<<"
            threading.Thread(
                target=self._send_antibug_discord,
                args=(
                    f"{discord_title}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"👤 **Người chơi:** {name}\n"
                    f"🆔 **SteamID:** `{steamid}`\n"
                    f"🕐 **Thời gian:** `{ts_now}`\n"
                    f"🏗️ **Công trình:** `{item_name}`\n"
                    f"📊 **Level cần thiết:** `{req_level}`  │  "
                    f"**Level thực tế:** `{confirmed_level}`\n"
                    f"⚡ **Vượt cấp:** `+{gap} level`\n"
                    f"🌐 **Kết quả thẩm phán ban:** {ban_status}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"{discord_footer}",
                ),
                daemon=True
            ).start()

    def _antibug_open_log(self):
        """Mở file antibug_log.txt bằng Notepad."""
        try:
            antibug_enf.antibug_open_log(ANTIBUG_LOG_FILE)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở file log: {e}")

    # ─────────────────────────────────────────
    #  DRAW: PALDEFENDER
    # ─────────────────────────────────────────
    def _load_paldef_log_history(self):
        """Tải 200 dòng cuối của PalDefender session log vào paldef_console."""
        if not hasattr(self, "paldef_console") or not self.paldef_console.winfo_exists():
            return
        try:
            lf = self._find_latest_paldef_log()
            if not lf:
                self.paldef_console.insert(
                    tk.END,
                    f"⚠️ Không tìm thấy file log PalDefender tại:\n  {PALDEF_LOG_DIR}\n"
                )
                return
            fname = os.path.basename(lf)
            # Cập nhật label tên file nếu có
            if hasattr(self, "_lbl_paldef_file"):
                self._lbl_paldef_file.config(text=f"📂 {fname}")
            with open(lf, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-200:] if len(lines) > 200 else lines
            self.paldef_console.delete("1.0", tk.END)
            if len(lines) > 200:
                self.paldef_console.insert(
                    tk.END,
                    f"─── 200 dòng cuối / tổng {len(lines)} dòng — {fname} ───\n\n"
                )
            for line in tail:
                self.paldef_console.insert(tk.END, line)
            self.paldef_console.see(tk.END)
        except Exception as e:
            self.paldef_console.insert(tk.END, f"❌ Lỗi đọc log: {e}\n")

    def _load_paldef_cheat_history(self):
        """Tải toàn bộ nội dung cheat log mới nhất vào paldef_cheat_console."""
        if not hasattr(self, "paldef_cheat_console") or \
           not self.paldef_cheat_console.winfo_exists():
            return
        try:
            cf = self._find_latest_paldef_cheat()
            if not cf:
                self.paldef_cheat_console.insert(
                    tk.END, "✅ Chưa có log cheat nào — server sạch!\n"
                )
                return
            fname = os.path.basename(cf)
            with open(cf, "r", encoding="utf-8", errors="replace") as f:
                lines = [ln.rstrip("\n") for ln in f.readlines()]
            self.paldef_cheat_console.delete("1.0", tk.END)
            self.paldef_cheat_console.insert(
                tk.END, f"─── {fname} ───\n\n"
            )
            prev = None
            cnt = 0
            for line in lines:
                if not line.strip():
                    continue
                if line == prev:
                    cnt += 1
                    continue
                if prev is not None:
                    self.paldef_cheat_console.insert(tk.END, prev + "\n")
                    if cnt > 1:
                        self.paldef_cheat_console.insert(tk.END, f"↳ (gộp {cnt} dòng trùng)\n")
                prev = line
                cnt = 1
            if prev is not None:
                self.paldef_cheat_console.insert(tk.END, prev + "\n")
                if cnt > 1:
                    self.paldef_cheat_console.insert(tk.END, f"↳ (gộp {cnt} dòng trùng)\n")
            self.paldef_cheat_console.see(tk.END)
        except Exception as e:
            self.paldef_cheat_console.insert(tk.END, f"❌ Lỗi đọc cheat log: {e}\n")

    def draw_paldefender(self):
        # Tiêu đề
        tk.Label(self.container, text="🛡️  PALDEFENDER ANTI-CHEAT",
                 bg="#0a0a0a", fg="#ff9900",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 4))

        # Info bar
        info_bar = tk.Frame(self.container, bg="#0a0a0a")
        info_bar.pack(fill="x", pady=(0, 6))
        self._lbl_paldef_file = tk.Label(
            info_bar, text="📂 (đang tìm file...)",
            bg="#0a0a0a", fg="#666", font=("Consolas", 8)
        )
        self._lbl_paldef_file.pack(side="left")

        # PanedWindow
        paned = tk.PanedWindow(self.container, orient="vertical",
                               bg="#444", sashwidth=6, sashrelief="flat")
        paned.pack(fill="both", expand=True)

        # ╔══════════════════════════════════════╗
        # ║  TOP — SESSION LOG                   ║
        # ╚══════════════════════════════════════╝
        top_f = tk.Frame(paned, bg="#0a0a0a")
        paned.add(top_f, minsize=180)

        # Header
        hdr = tk.Frame(top_f, bg="#1a0e00", pady=5)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📋  SESSION LOG (real-time)",
                 bg="#1a0e00", fg="#ff9900",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
        self._paldef_autoscroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(hdr, text="Auto-scroll",
                       variable=self._paldef_autoscroll_var,
                       bg="#1a0e00", fg="#888", selectcolor="#1a0e00",
                       activebackground="#1a0e00",
                       font=("Segoe UI", 9)).pack(side="left", padx=6)
        tk.Button(hdr, text="🔄 Tải lại",
                  bg="#2a1a00", fg="#ff9900", relief="flat", padx=10,
                  command=self._load_paldef_log_history).pack(side="right", padx=4)
        tk.Button(hdr, text="🗑 Xóa",
                  bg="#2a1a1a", fg="#ff7777", relief="flat", padx=10,
                  command=lambda: self.paldef_console.delete("1.0", tk.END)
                  ).pack(side="right", padx=4)

        # Filter
        flt_bar = tk.Frame(top_f, bg="#0a0a0a", pady=3)
        flt_bar.pack(fill="x", padx=6)
        tk.Label(flt_bar, text="🔍 Lọc:", bg="#0a0a0a", fg="#666",
                 font=("Segoe UI", 9)).pack(side="left")
        self._paldef_filter_var = tk.StringVar()
        tk.Entry(flt_bar, textvariable=self._paldef_filter_var,
                 bg="#111", fg="#ccc", bd=0, font=("Consolas", 9),
                 insertbackground="#ccc",
                 width=36).pack(side="left", padx=6, ipady=3)
        tk.Label(flt_bar, text="(ví dụ: error, warning, player)",
                 bg="#0a0a0a", fg="#444", font=("Segoe UI", 8)).pack(side="left")

        # Console session log
        self.paldef_console = scrolledtext.ScrolledText(
            top_f, bg="#0f0a00", fg="#ffcc77",
            font=("Consolas", 9), bd=0, insertbackground="#ffcc77"
        )
        self.paldef_console.pack(fill="both", expand=True, padx=2)

        # ╔══════════════════════════════════════════╗
        # ║  BOTTOM — NOTEBOOK: Cheats | AntiBug    ║
        # ╚══════════════════════════════════════════╝
        bot_f = tk.Frame(paned, bg="#0a0a0a")
        paned.add(bot_f, minsize=160)

        # Style notebook
        nb_style = ttk.Style()
        nb_style.configure("Pd.TNotebook",        background="#0a0a0a", borderwidth=0)
        nb_style.configure("Pd.TNotebook.Tab",
                           background="#1a0a0a", foreground="#aaa",
                           padding=[12, 5], font=("Segoe UI", 9, "bold"))
        nb_style.map("Pd.TNotebook.Tab",
                     background=[("selected", "#2a0a0a")],
                     foreground=[("selected", "#ff6666")])

        nb = ttk.Notebook(bot_f, style="Pd.TNotebook")
        nb.pack(fill="both", expand=True)

        # ── Tab 1: CHEAT DETECTIONS ──────────────────────────────
        cheat_tab = tk.Frame(nb, bg="#0f0000")
        nb.add(cheat_tab, text="  🚨 CHEAT DETECTIONS  ")

        cheat_hdr = tk.Frame(cheat_tab, bg="#1a0000", pady=5)
        cheat_hdr.pack(fill="x")
        tk.Label(cheat_hdr, text="🚨  PALDEFENDER CHEAT LOG",
                 bg="#1a0000", fg="#ff4444",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
        tk.Checkbutton(
            cheat_hdr, text="📣 Antibug Discord",
            variable=self.paldef_discord_alert,
            bg="#1a0000", fg="#ff9900", selectcolor="#1a0000",
            activebackground="#1a0000",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=12)
        tk.Checkbutton(
            cheat_hdr, text="📢 Chat Discord",
            variable=self.paldef_discord_alert_main,
            bg="#1a0000", fg="#7289da", selectcolor="#1a0000",
            activebackground="#1a0000",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=4)
        tk.Checkbutton(
            cheat_hdr, text="🧹 Auto dọn log",
            variable=self.paldef_log_cleanup_enabled,
            bg="#1a0000", fg="#66cc99", selectcolor="#1a0000",
            activebackground="#1a0000",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(8, 2))
        tk.Label(cheat_hdr, text="Giữ:",
                 bg="#1a0000", fg="#777", font=("Segoe UI", 8)).pack(side="left")
        ttk.Combobox(
            cheat_hdr, textvariable=self.paldef_log_keep_hours,
            values=["24", "12", "6", "4", "2"],
            state="readonly", width=4
        ).pack(side="left", padx=(4, 4))
        tk.Label(cheat_hdr, text="giờ",
                 bg="#1a0000", fg="#777", font=("Segoe UI", 8)).pack(side="left")
        tk.Button(cheat_hdr, text="🔄 Tải lại",
                  bg="#2a0000", fg="#ff4444", relief="flat", padx=10,
                  command=self._load_paldef_cheat_history).pack(side="right", padx=4)
        tk.Button(cheat_hdr, text="🧽 Dọn ngay",
                  bg="#2a2200", fg="#ffcc66", relief="flat", padx=10,
                  command=self._cleanup_paldef_logs_once).pack(side="right", padx=4)
        tk.Button(cheat_hdr, text="📂 Mở thư mục",
                  bg="#1a0000", fg="#888", relief="flat", padx=10,
                  command=lambda: subprocess.Popen(
                      f'explorer "{PALDEF_CHEATS_DIR}"')
                  ).pack(side="right", padx=4)
        self.paldef_cheat_console = scrolledtext.ScrolledText(
            cheat_tab, bg="#0f0000", fg="#ff6666",
            font=("Consolas", 9), bd=0, insertbackground="#ff6666"
        )
        self.paldef_cheat_console.pack(fill="both", expand=True, padx=2)

        # ── Tab 2: ANTIBUG MONITOR ──────────────────────────────
        ab_tab = tk.Frame(nb, bg="#0a0a12")
        nb.add(ab_tab, text="  🤖 ANTIBUG MONITOR  ")

        # Config bar
        ab_cfg = tk.Frame(ab_tab, bg="#0a0a1a", pady=6)
        ab_cfg.pack(fill="x")

        tk.Checkbutton(ab_cfg, text="🤖 ANTIBUG",
                       variable=self.antibug_enabled,
                       bg="#0a0a1a", fg="#00ffcc", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)

        tk.Label(ab_cfg, text="Ngưỡng:",
                 bg="#0a0a1a", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Spinbox(ab_cfg, from_=1, to=20,
                   textvariable=self.antibug_max_per_sec,
                   width=4, bg="#111", fg="#ffcc00",
                   buttonbackground="#222",
                   font=("Consolas", 9, "bold")).pack(side="left", padx=(2, 3))
        tk.Label(ab_cfg, text="công trình/giây → kick",
                 bg="#0a0a1a", fg="#666",
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))

        tk.Checkbutton(ab_cfg, text="📣 Discord",
                       variable=self.antibug_discord_alert,
                       bg="#0a0a1a", fg="#ff9900", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9)).pack(side="left", padx=4)

        tk.Checkbutton(ab_cfg, text="🔬 Tech-Cheat",
                       variable=self.antibug_techcheck_enabled,
                       bg="#0a0a1a", fg="#cc88ff", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        tk.Checkbutton(ab_cfg, text="🛠️ Build-Cheat",
                       variable=self.antibug_buildcheck_enabled,
                       bg="#0a0a1a", fg="#ff77aa", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        tk.Label(ab_cfg, text=f"({len(TECH_LEVEL_DB)} tech)",
                 bg="#0a0a1a", fg="#554466",
                 font=("Segoe UI", 7)).pack(side="left")

        tk.Checkbutton(ab_cfg, text="🔴 Ban cả Admin",
                       variable=self.techcheck_ban_admin,
                       bg="#0a0a1a", fg="#ff4444", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 8)).pack(side="left", padx=(6, 2))
        tk.Label(ab_cfg, text="(kể cả admin mode)",
                 bg="#0a0a1a", fg="#552222",
                 font=("Segoe UI", 7)).pack(side="left")

        tk.Checkbutton(ab_cfg, text="⚡ Kick NPC",
                       variable=self.npc_attack_kick_enabled,
                       bg="#0a0a1a", fg="#ffaa00", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 2))
        tk.Checkbutton(ab_cfg, text="🚫 Ban NPC",
                       variable=self.npc_capture_ban_enabled,
                       bg="#0a0a1a", fg="#ff6600", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=(6, 2))
        tk.Label(ab_cfg, text="(Merchant, BlackMarket…)",
                 bg="#0a0a1a", fg="#553300",
                 font=("Segoe UI", 7)).pack(side="left")

        tk.Button(ab_cfg, text="📄 Mở log file",
                  bg="#1a1a2a", fg="#aaaaff", relief="flat", padx=10,
                  command=self._antibug_open_log).pack(side="right", padx=6)
        tk.Button(ab_cfg, text="🗑 Xóa console",
                  bg="#1a1a2a", fg="#888", relief="flat", padx=10,
                  command=lambda: self.antibug_console.delete("1.0", tk.END)
                  ).pack(side="right", padx=4)

        # Stats bar
        self._lbl_antibug_stats = tk.Label(
            ab_tab,
            text=(f"🎯 Giám sát: 0 người  │  "
                  f"⚡ Kicked: 0  │  🔨 Banned: 0"),
            bg="#0a0a12", fg="#ffcc00",
            font=("Segoe UI", 9, "bold")
        )
        self._lbl_antibug_stats.pack(anchor="w", padx=10, pady=(2, 0))

        # Quy tắc
        rule_f = tk.Frame(ab_tab, bg="#0d0d1a", pady=4)
        rule_f.pack(fill="x", padx=6, pady=(2, 2))
        tk.Label(rule_f,
                 text=(f"📌  Quy tắc: > [ngưỡng] công trình/giây → CẢNH BÁO + KICK  │  "
                       f"Bị kick ≥ {ANTIBUG_MAX_KICKS} lần trong 5 phút → BAN VĨNH VIỄN"),
                 bg="#0d0d1a", fg="#555",
                 font=("Segoe UI", 8)).pack(side="left", padx=4)

        # ── Unban / BanList panel ────────────────────────────────────
        unban_f = tk.Frame(ab_tab, bg="#071a0f",
                           highlightthickness=1, highlightbackground="#1a4a2a")
        unban_f.pack(fill="x", padx=6, pady=(2, 3))

        tk.Label(unban_f, text="🔓 UNBAN:",
                 bg="#071a0f", fg="#00ff88",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 4))

        list_wrap = tk.Frame(unban_f, bg="#071a0f")
        list_wrap.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=4)
        self._lb_unban = tk.Listbox(
            list_wrap,
            height=3,
            bg="#0d2a1a", fg="#00ff88",
            selectbackground="#0f4a2a", selectforeground="#ccffdd",
            font=("Consolas", 10),
            relief="flat", highlightthickness=0
        )
        self._lb_unban.pack(side="left", fill="x", expand=True)
        lb_scroll = tk.Scrollbar(list_wrap, orient="vertical", command=self._lb_unban.yview)
        lb_scroll.pack(side="right", fill="y")
        self._lb_unban.config(yscrollcommand=lb_scroll.set)

        self._entry_unban_id = tk.Entry(
            unban_f, bg="#0d2a1a", fg="#00ff88",
            bd=0, font=("Consolas", 10), insertbackground="#00ff88",
            width=24
        )
        self._entry_unban_id.pack(side="left", padx=(0, 6), ipady=5, pady=4)
        self._entry_unban_id.insert(0, "steam_XXXXXXXXXXXXXXXXX")
        self._entry_unban_id.bind(
            "<FocusIn>",
            lambda e: (self._entry_unban_id.delete(0, tk.END)
                       if self._entry_unban_id.get() == "steam_XXXXXXXXXXXXXXXXX"
                       else None)
        )

        self._unban_candidates = []

        def _refresh_unban_list():
            self._unban_candidates = self._read_antibug_banlist_entries()
            self._lb_unban.delete(0, tk.END)
            for row in self._unban_candidates[:300]:
                self._lb_unban.insert(tk.END, row.get("label", ""))

        def _selected_unban_sid() -> str:
            sel = self._lb_unban.curselection()
            if sel:
                idx = sel[0]
                if 0 <= idx < len(self._unban_candidates):
                    return self._unban_candidates[idx].get("steamid", "")
            sid = self._entry_unban_id.get().strip()
            if sid and sid != "steam_XXXXXXXXXXXXXXXXX":
                return sid
            return ""

        def _do_unban():
            sid = _selected_unban_sid()
            if not sid:
                messagebox.showwarning("Unban", "Chọn người trong danh sách hoặc nhập SteamID trước!")
                return
            ok, detail = self._unban_steamid_common(sid, source="MANUAL UNBAN")
            if ok:
                _refresh_unban_list()
            messagebox.showinfo("Unban", detail)

        def _on_unban_right_click(event):
            try:
                idx = self._lb_unban.nearest(event.y)
                if idx >= 0:
                    self._lb_unban.selection_clear(0, tk.END)
                    self._lb_unban.selection_set(idx)
                    self._lb_unban.activate(idx)
            except Exception:
                pass
            try:
                _unban_menu.tk_popup(event.x_root, event.y_root)
            finally:
                _unban_menu.grab_release()

        self._lb_unban.bind("<Double-Button-1>", lambda _e: _do_unban())
        self._lb_unban.bind("<Button-3>", _on_unban_right_click)
        _unban_menu = tk.Menu(self.root, tearoff=0, bg="#0d1a12", fg="#00ff88")
        _unban_menu.add_command(label="🔓 Unban", command=_do_unban)
        _unban_menu.add_command(label="🔄 Tải lại danh sách", command=_refresh_unban_list)
        _refresh_unban_list()

        tk.Button(unban_f, text="🔄",
                  bg="#0d2a1a", fg="#88ffcc",
                  relief="flat", padx=8,
                  command=_refresh_unban_list).pack(side="left", padx=(0, 6))

        tk.Button(unban_f, text="🔓 UNBAN",
                  bg="#0d3a1a", fg="#00ff88",
                  relief="flat", padx=14,
                  command=_do_unban).pack(side="left", padx=(0, 8))

        tk.Button(unban_f, text="📋 Xem banlist.txt",
                  bg="#0d0d2a", fg="#aaaaff",
                  relief="flat", padx=10,
                  command=lambda: (
                      os.startfile(ANTIBUG_BAN_FILE)
                      if os.path.isfile(ANTIBUG_BAN_FILE)
                      else messagebox.showinfo("Thông báo", "Chưa có file banlist.txt")
                  )).pack(side="left", padx=(0, 6))

        def _open_banlist_dir():
            subprocess.Popen(
                f'explorer /select,"{ANTIBUG_BAN_FILE}"'
                if os.path.isfile(ANTIBUG_BAN_FILE)
                else f'explorer "{os.path.dirname(ANTIBUG_BAN_FILE)}"'
            )
        tk.Button(unban_f, text="📂 Thư mục",
                  bg="#1a1a1a", fg="#888",
                  relief="flat", padx=10,
                  command=_open_banlist_dir).pack(side="left")

        tk.Label(unban_f,
                 text=(f"🔗 Webhook: AntiBug  │  "
                       f"📁 banlist.txt  │  "
                       f"⏱ Kick window: 5 phút"),
                 bg="#071a0f", fg="#2a5a3a",
                 font=("Segoe UI", 8)).pack(side="right", padx=10)

        # Log console
        self.antibug_console = scrolledtext.ScrolledText(
            ab_tab, bg="#05050f", fg="#aaaaff",
            font=("Consolas", 9), bd=0, insertbackground="#aaaaff"
        )
        self.antibug_console.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        # Chèn header
        self.antibug_console.insert(
            tk.END,
            f"{'─'*65}\n"
            f"  🤖 ANTIBUG MONITOR — MANAGER SERVERPAL\n"
            f"  ⚒  Build/Dismantle spam : > [ngưỡng]/1s → CẢNH BÁO + KICK\n"
            f"  🔬 Tech-Cheat           : mở khóa công nghệ vượt cấp → BAN NGAY\n"
            f"  🔬 Tech-Cheat           : mở khóa/xây công nghệ vượt cấp → BAN NGAY\n"
            f"  📚 Tech Database        : {len(TECH_LEVEL_DB)} công nghệ "
            f"(paldeck.cc/technology)\n"
            f"{'─'*65}\n\n"
        )

        # ── Tab 3: PALDEFENDER REST API ──────────────────────────────
        api_tab = tk.Frame(nb, bg="#050a14")
        nb.add(api_tab, text="  🌐 PD REST API  ")

        # ── Status bar ─────────────────────────────────────────────
        st_bar = tk.Frame(api_tab, bg="#07101f", pady=6,
                          highlightthickness=1, highlightbackground="#1a3a5a")
        st_bar.pack(fill="x", padx=6, pady=(6, 2))

        tk.Label(st_bar, text="📡 PalDefender API:",
                 bg="#07101f", fg="#5588bb",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 6))

        self._lbl_pdapi_status = tk.Label(
            st_bar, text="⏳ Đang kiểm tra...",
            bg="#07101f", fg="#888",
            font=("Segoe UI", 9, "bold")
        )
        self._lbl_pdapi_status.pack(side="left")

        def _ping_now():
            def _do():
                r = self._pdapi_get_version()
                self._pdapi_status_ok = r["ok"]
                if r["ok"]:
                    d = r["data"]
                    ver2 = d.get("Version", d.get("version", ""))
                    if isinstance(ver2, dict):
                        ver2 = (f"{ver2.get('Major','?')}."
                                f"{ver2.get('Minor','?')}."
                                f"{ver2.get('Patch','?')}")
                    elif not ver2:
                        maj = d.get("Major", "")
                        ver2 = (f"{d.get('Major','?')}.{d.get('Minor','?')}.{d.get('Patch','?')}"
                                if maj else "OK")
                    self._pdapi_version = str(ver2)
                else:
                    self._pdapi_version = ""
                self.root.after(0, self._pdapi_update_status_label)
            threading.Thread(target=_do, daemon=True).start()

        tk.Button(st_bar, text="🔄 Ping",
                  bg="#0d2a44", fg="#55aaff", relief="flat", padx=10,
                  command=_ping_now).pack(side="left", padx=8)

        tk.Label(st_bar, text=f"Port {PALDEF_API_BASE.split(':')[-1]}",
                 bg="#07101f", fg="#334455",
                 font=("Consolas", 8)).pack(side="right", padx=10)

        # ── Token management ───────────────────────────────────────
        tok_bar = tk.Frame(api_tab, bg="#07140f", pady=5,
                           highlightthickness=1, highlightbackground="#1a4a2a")
        tok_bar.pack(fill="x", padx=6, pady=(2, 2))

        tk.Label(tok_bar, text="🔑 Token:",
                 bg="#07140f", fg="#00cc66",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 6))

        self._var_pdapi_token_disp = tk.StringVar(
            value=self._pdapi_token[:18] + "..." if len(self._pdapi_token) > 18
            else self._pdapi_token
        )
        tok_entry = tk.Entry(
            tok_bar, textvariable=self._var_pdapi_token_disp,
            bg="#0d2a1a", fg="#00ff88", bd=0,
            font=("Consolas", 9), width=28,
            state="readonly", readonlybackground="#0d2a1a",
            insertbackground="#00ff88"
        )
        tok_entry.pack(side="left", padx=(0, 6), ipady=4)

        def _copy_token():
            self.root.clipboard_clear()
            self.root.clipboard_append(self._pdapi_token)
            self._enqueue_console("📋 [PD-API] Đã copy token vào clipboard!")

        def _regen_token():
            if not messagebox.askyesno(
                "Tái tạo token",
                "Xóa token cũ và tạo token mới?\n"
                "⚠️ Cần khởi động lại PalDefender để token mới có hiệu lực!"
            ):
                return
            try:
                os.remove(PALDEF_TOKEN_FILE)
            except Exception:
                pass
            self._pdapi_token = self._pdapi_ensure_token()
            short = (self._pdapi_token[:18] + "..."
                     if len(self._pdapi_token) > 18
                     else self._pdapi_token)
            self._var_pdapi_token_disp.set(short)
            self._enqueue_console(
                f"🔑 [PD-API] Token mới đã tạo — "
                f"Khởi động lại PalDefender để áp dụng!"
            )
            messagebox.showinfo(
                "Token mới",
                f"Token đã tạo:\n{self._pdapi_token}\n\n"
                f"File: {PALDEF_TOKEN_FILE}\n\n"
                f"⚠️ Restart PalDefender để token có hiệu lực!"
            )

        tk.Button(tok_bar, text="📋 Copy",
                  bg="#0d2a1a", fg="#00cc66", relief="flat", padx=8,
                  command=_copy_token).pack(side="left", padx=2)
        tk.Button(tok_bar, text="🔄 Tạo mới",
                  bg="#1a1a0d", fg="#ffcc00", relief="flat", padx=8,
                  command=_regen_token).pack(side="left", padx=2)

        tk.Label(tok_bar,
                 text=f"📁 {PALDEF_TOKEN_FILE}",
                 bg="#07140f", fg="#224433",
                 font=("Consolas", 7)).pack(side="right", padx=10)

        # ── Give Rewards Panel ─────────────────────────────────────
        give_f = tk.LabelFrame(
            api_tab, text="  🎁 GIVE REWARDS (PD API — Atomic)  ",
            bg="#050a14", fg="#55aaff",
            font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove"
        )
        give_f.pack(fill="x", padx=8, pady=(4, 2))

        # Row 1: SteamID
        r1 = tk.Frame(give_f, bg="#050a14")
        r1.pack(fill="x", padx=6, pady=(4, 2))
        tk.Label(r1, text="SteamID:", bg="#050a14", fg="#aaa",
                 font=("Segoe UI", 9), width=10, anchor="e").pack(side="left")
        self._pdapi_give_sid = tk.Entry(
            r1, bg="#0a0a1a", fg="#aaddff", bd=0,
            font=("Consolas", 10), insertbackground="#aaddff"
        )
        self._pdapi_give_sid.pack(side="left", fill="x", expand=True,
                                   padx=(6, 0), ipady=5)

        # Row 2: Items (JSON array hoặc "ItemID x Count" mỗi dòng)
        r2 = tk.Frame(give_f, bg="#050a14")
        r2.pack(fill="x", padx=6, pady=2)
        tk.Label(r2, text="Items:", bg="#050a14", fg="#aaa",
                 font=("Segoe UI", 9), width=10, anchor="e").pack(side="left")
        tk.Label(r2, text="ItemID  Count  (mỗi dòng 1 item, ví dụ: PalSphere 10)",
                 bg="#050a14", fg="#445566",
                 font=("Segoe UI", 7)).pack(side="left", padx=6)

        self._pdapi_give_items = tk.Text(
            give_f, bg="#0a0a1a", fg="#aaddff", bd=0,
            font=("Consolas", 9), insertbackground="#aaddff",
            height=3
        )
        self._pdapi_give_items.pack(fill="x", padx=10, pady=(0, 2))

        # Row 3: Pal + EXP
        r3 = tk.Frame(give_f, bg="#050a14")
        r3.pack(fill="x", padx=6, pady=2)

        tk.Label(r3, text="Pal ID:", bg="#050a14", fg="#aaa",
                 font=("Segoe UI", 9), width=10, anchor="e").pack(side="left")
        self._pdapi_give_pal = tk.Entry(
            r3, bg="#0a0a1a", fg="#ddaaff", bd=0,
            font=("Consolas", 10), insertbackground="#ddaaff", width=24
        )
        self._pdapi_give_pal.pack(side="left", padx=(6, 10), ipady=4)

        tk.Label(r3, text="Lv:", bg="#050a14", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side="left")
        self._pdapi_give_pal_lv = tk.Entry(
            r3, bg="#0a0a1a", fg="#ddaaff", bd=0,
            font=("Consolas", 10), insertbackground="#ddaaff", width=5
        )
        self._pdapi_give_pal_lv.insert(0, "1")
        self._pdapi_give_pal_lv.pack(side="left", padx=(4, 14), ipady=4)

        tk.Label(r3, text="EXP:", bg="#050a14", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side="left")
        self._pdapi_give_exp = tk.Entry(
            r3, bg="#0a0a1a", fg="#ffdd88", bd=0,
            font=("Consolas", 10), insertbackground="#ffdd88", width=10
        )
        self._pdapi_give_exp.pack(side="left", padx=(4, 0), ipady=4)

        # Log / result area + nút GIVE
        give_btn_row = tk.Frame(give_f, bg="#050a14")
        give_btn_row.pack(fill="x", padx=6, pady=(2, 6))

        def _do_pdapi_give():
            sid = self._pdapi_give_sid.get().strip()
            if not sid:
                messagebox.showwarning("Give", "Nhập SteamID trước!")
                return
            sid = self._normalize_steamid(sid)
            payload: dict = {}

            # Parse items
            raw_items = self._pdapi_give_items.get("1.0", tk.END).strip()
            if raw_items:
                items = []
                for line in raw_items.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            items.append({"ItemID": parts[0], "Count": int(parts[1])})
                        except ValueError:
                            pass
                    elif len(parts) == 1:
                        items.append({"ItemID": parts[0], "Count": 1})
                if items:
                    payload["Item"] = items

            # Parse pal
            pal_id = self._pdapi_give_pal.get().strip()
            if pal_id:
                try:
                    lv = int(self._pdapi_give_pal_lv.get().strip() or "1")
                except ValueError:
                    lv = 1
                payload["Pal"] = [{"PalID": pal_id, "Level": lv}]

            # Parse EXP
            exp_str = self._pdapi_give_exp.get().strip()
            if exp_str:
                try:
                    payload["EXP"] = int(exp_str)
                except ValueError:
                    pass

            if not payload:
                messagebox.showwarning("Give", "Chưa nhập item/pal/EXP nào!")
                return

            def _do():
                ok, data = self._pdapi_give(sid, payload)
                if ok:
                    msg = f"✅ [PD-API GIVE] {sid} → {payload}  →  Errors=0"
                else:
                    errs = data.get("Error", data.get("error", data))
                    msg = f"❌ [PD-API GIVE] {sid} → Errors={data.get('Errors','?')}  {errs}"
                self._enqueue_console(msg)
                self.root.after(
                    0,
                    lambda: self._pdapi_give_log.insert(tk.END, msg + "\n")
                )
                self.root.after(
                    0,
                    lambda: self._pdapi_give_log.see(tk.END)
                )
            threading.Thread(target=_do, daemon=True).start()

        tk.Button(give_btn_row, text="🎁  GIVE (PD API)",
                  bg="#1a2a44", fg="#55aaff",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=18,
                  command=_do_pdapi_give).pack(side="left")
        tk.Button(give_btn_row, text="🗑 Xóa log",
                  bg="#1a1a1a", fg="#666", relief="flat", padx=8,
                  command=lambda: self._pdapi_give_log.delete("1.0", tk.END)
                  ).pack(side="left", padx=6)
        tk.Label(give_btn_row,
                 text="Atomic: all-or-nothing  │  Không cần RCON",
                 bg="#050a14", fg="#223344",
                 font=("Segoe UI", 7)).pack(side="right", padx=6)

        self._pdapi_give_log = scrolledtext.ScrolledText(
            give_f, bg="#03060d", fg="#8899cc",
            font=("Consolas", 8), bd=0, insertbackground="#8899cc",
            height=4
        )
        self._pdapi_give_log.pack(fill="x", padx=6, pady=(0, 4))

        # ── Guild Viewer ───────────────────────────────────────────
        guild_f = tk.LabelFrame(
            api_tab, text="  🏰 GUILD VIEWER  ",
            bg="#050a14", fg="#ff9900",
            font=("Segoe UI", 9, "bold"),
            bd=1, relief="groove"
        )
        guild_f.pack(fill="both", expand=True, padx=8, pady=(2, 6))

        guild_top = tk.Frame(guild_f, bg="#050a14")
        guild_top.pack(fill="x", padx=6, pady=(4, 2))

        self._pdapi_guild_tree = ttk.Treeview(
            guild_f,
            columns=("name", "admin", "members"),
            show="headings", height=5
        )
        self._pdapi_guild_tree.heading("name",    text="Tên Guild")
        self._pdapi_guild_tree.heading("admin",   text="Admin UID")
        self._pdapi_guild_tree.heading("members", text="Thành viên")
        self._pdapi_guild_tree.column("name",    width=220, anchor="w")
        self._pdapi_guild_tree.column("admin",   width=280, anchor="w")
        self._pdapi_guild_tree.column("members", width=80,  anchor="center")

        style_guild = ttk.Style()
        style_guild.configure("Guild.Treeview",
                              background="#050a14", foreground="#ffcc77",
                              fieldbackground="#050a14", rowheight=22,
                              font=("Consolas", 8))
        style_guild.configure("Guild.Treeview.Heading",
                              background="#0a1a2a", foreground="#ff9900",
                              font=("Segoe UI", 8, "bold"))
        self._pdapi_guild_tree.configure(style="Guild.Treeview")

        sb_guild = ttk.Scrollbar(guild_f, orient="vertical",
                                  command=self._pdapi_guild_tree.yview)
        self._pdapi_guild_tree.configure(yscrollcommand=sb_guild.set)
        sb_guild.pack(side="right", fill="y", padx=(0, 2))
        self._pdapi_guild_tree.pack(fill="both", expand=True, padx=(6, 0), pady=(0, 4))

        self._lbl_guild_info = tk.Label(
            guild_top, text="(chưa tải)",
            bg="#050a14", fg="#555", font=("Segoe UI", 8)
        )
        self._lbl_guild_info.pack(side="left", padx=4)

        def _refresh_guilds():
            self._lbl_guild_info.config(text="⏳ Đang tải...", fg="#888")
            def _do():
                result = self._pdapi_get_guilds()
                def _update():
                    for row in self._pdapi_guild_tree.get_children():
                        self._pdapi_guild_tree.delete(row)
                    if not result["ok"]:
                        err = result.get("error", result.get("code", "?"))
                        self._lbl_guild_info.config(
                            text=f"❌ Lỗi: {err}", fg="#ff4444")
                        return
                    guilds = result["data"]
                    for gid, gdata in guilds.items():
                        name    = gdata.get("Name", gdata.get("GuildName", gid))
                        admin   = gdata.get("AdminPlayerUid",
                                            gdata.get("AdminUid", ""))
                        members = gdata.get("Members", [])
                        m_count = len(members) if isinstance(members, list) else "?"
                        self._pdapi_guild_tree.insert(
                            "", tk.END,
                            iid=gid,
                            values=(name, admin, m_count)
                        )
                    self._lbl_guild_info.config(
                        text=f"✅ {len(guilds)} guild", fg="#00ff88")
                self.root.after(0, _update)
            threading.Thread(target=_do, daemon=True).start()

        tk.Button(guild_top, text="🔄 Tải guilds",
                  bg="#1a1a00", fg="#ffaa00", relief="flat", padx=10,
                  command=_refresh_guilds).pack(side="left", padx=(0, 6))

        # Ping ngay khi mở tab
        self.root.after(500, _ping_now)

        # Load lịch sử
        self.root.after(100, self._load_paldef_log_history)
        self.root.after(150, self._load_paldef_cheat_history)

    # ─────────────────────────────────────────
    #  LIVE MAP — HELPERS
    # ─────────────────────────────────────────
    def _coord_to_canvas(self, loc_x: float, loc_y: float,
                          canvas_w: int, canvas_h: int):
        """Chuyển tọa độ game Palworld → pixel trên canvas."""
        map_x = (loc_y - 157664.55791065) / 462.962962963
        map_y = (loc_x + 123467.1611767)  / 462.962962963
        cx = (map_x + 1000) / 2000 * canvas_w
        cy = (1000 - map_y) / 2000 * canvas_h
        return cx, cy

    def _mapcoords_to_world(self, map_x: float, map_y: float) -> tuple:
        """Đảo phép biến đổi của _coord_to_canvas (map coords -> world loc_x/loc_y).
        Log PalDefender (PalBoxV2) đang cho dạng 'at X Y Z' giống map coords hiển thị.
        map_x tương ứng công thức từ loc_y, map_y tương ứng từ loc_x.
        """
        loc_y = float(map_x) * 462.962962963 + 157664.55791065
        loc_x = float(map_y) * 462.962962963 - 123467.1611767
        return loc_x, loc_y

    def _render_discord_livemap_image(self, size: int = 1024) -> str:
        """Render ảnh LiveMap cho Discord (PNG) với marker player/base hiện tại."""
        if not _PIL_AVAILABLE or not os.path.isfile(MAP_JPG):
            return ""
        try:
            s = max(512, min(int(size or 1024), 2048))
            img = Image.open(MAP_JPG).convert("RGB").resize((s, s), Image.LANCZOS)
            draw = ImageDraw.Draw(img)

            # Vẽ base trước (layer dưới)
            for base in (self._map_guild_bases or []):
                try:
                    bx = float(base.get("loc_x"))
                    by = float(base.get("loc_y"))
                    cx, cy = self._coord_to_canvas(bx, by, s, s)
                    if not (-20 <= cx <= s + 20 and -20 <= cy <= s + 20):
                        continue
                    r = 10
                    poly = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
                    draw.polygon(poly, outline="#00ddff", fill="#0a1a2a", width=2)
                except Exception:
                    continue

            # Vẽ player (layer trên)
            dot_colors = ["#ff6ec7", "#00ffcc", "#ffdd00", "#ff5555",
                          "#88ff44", "#4499ff", "#ff9900", "#cc44ff",
                          "#00ddff", "#ffaaaa"]
            for i, p in enumerate(self._map_players_data or []):
                try:
                    lx = p.get("location_x")
                    ly = p.get("location_y")
                    if lx is None or ly is None:
                        continue
                    cx, cy = self._coord_to_canvas(float(lx), float(ly), s, s)
                    if not (-20 <= cx <= s + 20 and -20 <= cy <= s + 20):
                        continue
                    col = dot_colors[i % len(dot_colors)]
                    r = 8
                    draw.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), outline=col, width=2)
                    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col, outline="white", width=1)
                    nm = str(p.get("name", "?"))[:14]
                    lv = p.get("level", "?")
                    draw.text((cx + 10, cy - 12), f"Lv{lv} {nm}", fill="white")
                except Exception:
                    continue

            out_file = os.path.join(SAVE_GAMES_DIR, "discord_livemap.png")
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            img.save(out_file, format="PNG")
            return out_file
        except Exception:
            return ""

    def _map_apply_base_event(self, steamid: str, player_name: str,
                              action: str, map_x: float, map_y: float, map_z: float):
        """Cập nhật base marker theo log PalBoxV2:
        - build: set/update base của guild tại tọa độ mới
        - dismantle: remove base của guild (nếu gần tọa độ đó), hoặc clear nếu chỉ có 1
        """
        try:
            # tra guild của người chơi bằng bảng gpm hiện tại
            gpm = self._map_guild_player_map or {}
            gname = gpm.get(str(steamid).lower()) or gpm.get(str(steamid).lower().lstrip("steam_")) or ""
            if not gname:
                # fallback theo tên (nếu gpm có name:)
                key = f"name:{str(player_name).lower().strip()}"
                gname = gpm.get(key, "")
            if not gname:
                return

            # world coords để vẽ lên canvas
            loc_x, loc_y = self._mapcoords_to_world(map_x, map_y)

            BLUE = "#00ddff"  # icon luôn màu xanh theo yêu cầu
            base_obj = {
                "guild_name": gname,
                "guild_id":   f"log:{gname}",
                "base_id":    f"log:{gname}",
                "loc_x":      float(loc_x),
                "loc_y":      float(loc_y),
                "color":      BLUE,
                "level":      1,
                "area":       0,
                "src":        "log",
                "last_action": action,
                "last_by":    str(player_name),
                "last_sid":   str(steamid),
                "map_z":      float(map_z),
            }

            if "build" in action:
                self._map_bases_by_guild[gname] = base_obj
            else:
                # dismantle: remove nếu base gần tọa độ đó
                cur = self._map_bases_by_guild.get(gname)
                if not cur:
                    return
                # so khoảng cách theo map coords để dễ so (dùng world cũng ok)
                try:
                    cur_map_x = (cur["loc_y"] - 157664.55791065) / 462.962962963
                    cur_map_y = (cur["loc_x"] + 123467.1611767)  / 462.962962963
                    dist = ((cur_map_x - float(map_x))**2 + (cur_map_y - float(map_y))**2) ** 0.5
                except Exception:
                    dist = 0.0
                if dist <= 8.0:
                    self._map_bases_by_guild.pop(gname, None)

            # publish list bases cho renderer (ưu tiên bases từ log)
            self._map_guild_bases = list(self._map_bases_by_guild.values()) or self._map_guild_bases

            # cập nhật UI
            try:
                self.root.after(0, lambda: (self._redraw_livemap_canvas(),
                                            self._update_map_player_tree()))
            except Exception:
                pass
        except Exception:
            pass

    def _start_map_node_server(self):
        """Legacy no-op: Live map đã chạy embedded, không cần Node.js."""
        self._enqueue_console("ℹ️ Live Map đã tích hợp trong app, không cần khởi động Node.js.")
        self._update_map_node_status_label()

    def _stop_map_node_server(self):
        """Legacy no-op: giữ để tương thích UI cũ."""
        self._enqueue_console("ℹ️ Live Map embedded không có tiến trình Node để dừng.")
        self._update_map_node_status_label()

    def _update_map_node_status_label(self):
        """Cập nhật label trạng thái map mode (embedded)."""
        if not hasattr(self, "_lbl_map_node_status"):
            return
        try:
            if not self._lbl_map_node_status.winfo_exists():
                return
            self._lbl_map_node_status.config(
                text="🟢 Live Map: EMBEDDED MODE (không cần Node.js)", fg="#00ffcc")
        except Exception:
            pass

    def _api_conn_parts(self) -> tuple:
        """Trả về (host, port, password) từ API_URL và AUTH hiện tại."""
        parsed = urlparse(API_URL)
        host   = parsed.hostname or "127.0.0.1"
        port   = parsed.port or 8212
        passwd = AUTH.password or ""
        return host, port, passwd

    def _open_web_map(self):
        """Mở thư mục chứa ảnh map để tiện update map.jpg."""
        try:
            os.makedirs(MAP_ASSETS_DIR, exist_ok=True)
            if os.path.isfile(MAP_JPG):
                os.startfile(MAP_JPG)
            else:
                os.startfile(MAP_ASSETS_DIR)
        except Exception as e:
            self._enqueue_console(f"❌ Không mở được thư mục map assets: {e}")

    def _load_map_image(self, w: int, h: int):
        """Tải và scale map.jpg → PhotoImage (Pillow). Trả None nếu lỗi."""
        if not _PIL_AVAILABLE or not os.path.isfile(MAP_JPG):
            return None
        try:
            img   = Image.open(MAP_JPG).convert("RGB")
            img   = img.resize((w, h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            return photo
        except Exception:
            return None

    # Màu sắc chuẩn cho 10 guild đầu (xoay vòng)
    _GUILD_COLORS = [
        "#00ddff", "#ffcc00", "#ff6600", "#ff44aa",
        "#88ff44", "#cc88ff", "#ff8844", "#44ffcc",
        "#ff4444", "#44aaff",
    ]

    @staticmethod
    def _norm_uid(uid: str) -> str:
        """Chuẩn hóa UUID/SteamID: lowercase, bỏ dấu gạch, bỏ prefix steam_."""
        if not uid:
            return ""
        s = str(uid).lower().strip()
        s_nodash = s.replace("-", "")
        return s_nodash  # primary canonical form

    def _lookup_guild(self, player: dict, gpm: dict) -> str:
        """Tra cứu tên guild của một player từ bảng gpm.
        Thử tất cả biến thể UUID và fallback theo tên nhân vật."""
        if not gpm:
            return ""
        pid  = str(player.get("playerId",  "")).lower().strip()
        uid  = str(player.get("userId",    "")).lower().strip()
        name = str(player.get("name",      "")).lower().strip()

        candidates = set()
        for raw in (pid, uid):
            if raw:
                candidates.add(raw)
                candidates.add(raw.replace("-", ""))          # bỏ dash UUID
                no_prefix = raw.lstrip("steam_")
                candidates.add(no_prefix)
                candidates.add(no_prefix.replace("-", ""))

        for c in candidates:
            if c and c in gpm:
                return gpm[c]

        # Fallback: khớp theo tên nhân vật
        if name:
            key = f"name:{name}"
            if key in gpm:
                return gpm[key]
        return ""

    def _build_guild_maps(self, guilds: dict) -> tuple:
        """Xây dựng:
          - gpm: {normalized_uid → guild_name}  (dùng cho player matching)
          - gname_map: {gid → guild_name}
          - guild_color_map: {guild_name → color}
        Sau đó fetch chi tiết từng guild (song song) để lấy base data.
        Trả về (gpm, bases, guild_color_map).
        """
        gpm: dict  = {}
        bases: list = []
        gname_map:  dict = {}
        gcolor_map: dict = {}

        # Bước 1: Xây gpm từ members trong batch response
        for gi, (gid, gdata) in enumerate(guilds.items()):
            gname = (gdata.get("Name")
                     or gdata.get("GuildName")
                     or gdata.get("name")
                     or gid)
            gcol  = self._GUILD_COLORS[gi % len(self._GUILD_COLORS)]
            gname_map[gid]   = gname
            gcolor_map[gname] = gcol

            members = (gdata.get("Members")
                       or gdata.get("members")
                       or gdata.get("Players")
                       or gdata.get("players")
                       or [])
            if isinstance(members, list):
                for m in members:
                    uids = []
                    if isinstance(m, dict):
                        raw = (m.get("PlayerUid")
                               or m.get("UserId")
                               or m.get("Uid")
                               or m.get("SteamId")
                               or m.get("playerId")
                               or m.get("CharacterId")
                               or "")
                        if raw:
                            uids.append(str(raw))
                        # Thêm CharacterName để fallback match by name
                        nm = (m.get("CharacterName")
                              or m.get("PlayerName")
                              or m.get("Name")
                              or m.get("name")
                              or "")
                        if nm:
                            gpm[f"name:{nm.lower()}"] = gname
                    elif isinstance(m, str) and m:
                        uids.append(m)

                    for uid_raw in uids:
                        s = uid_raw.lower().strip()
                        # Tất cả biến thể có thể gặp
                        variants = {
                            s,                                # nguyên gốc
                            s.replace("-", ""),               # bỏ dash (UUID)
                            s.lstrip("steam_"),               # bỏ prefix
                            s.lstrip("steam_").replace("-",""),
                            "steam_" + s.lstrip("steam_"),    # thêm prefix
                        }
                        for v in variants:
                            if v:
                                gpm[v] = gname

            # Bước 1b: Thử parse base từ batch response (phòng trường hợp có sẵn)
            batch_bases = self._parse_guild_bases({gid: gdata}, gi, gname, gcol)
            bases.extend(batch_bases)

        # Bước 2: Fetch chi tiết từng guild song song để lấy base data
        detail_bases: list = []

        def _fetch_one(args):
            gi2, gid2, gname2, gcol2 = args
            try:
                r = self._pdapi_get_guild(gid2)
                if r["ok"]:
                    detail = r["data"]
                    # Cũng bổ sung members từ detail (có thể chi tiết hơn)
                    det_members = (detail.get("Members")
                                   or detail.get("members")
                                   or detail.get("Players")
                                   or detail.get("players")
                                   or [])
                    local_gpm = {}
                    if isinstance(det_members, list):
                        for m in det_members:
                            uids = []
                            if isinstance(m, dict):
                                raw = (m.get("PlayerUid")
                                       or m.get("UserId")
                                       or m.get("Uid")
                                       or m.get("SteamId")
                                       or m.get("playerId")
                                       or m.get("CharacterId")
                                       or "")
                                if raw:
                                    uids.append(str(raw))
                                nm = (m.get("CharacterName")
                                      or m.get("PlayerName")
                                      or m.get("Name")
                                      or m.get("name")
                                      or "")
                                if nm:
                                    local_gpm[f"name:{nm.lower()}"] = gname2
                            elif isinstance(m, str) and m:
                                uids.append(m)
                            for uid_raw in uids:
                                s = uid_raw.lower().strip()
                                for v in {s, s.replace("-",""),
                                          s.lstrip("steam_"),
                                          s.lstrip("steam_").replace("-",""),
                                          "steam_"+s.lstrip("steam_")}:
                                    if v:
                                        local_gpm[v] = gname2
                    # Parse bases từ detail
                    det_b = self._parse_guild_bases(
                        {gid2: detail}, gi2, gname2, gcol2)
                    return local_gpm, det_b
            except Exception:
                pass
            return {}, []

        args_list = [(gi, gid, gname_map.get(gid, gid),
                      self._GUILD_COLORS[gi % len(self._GUILD_COLORS)])
                     for gi, gid in enumerate(guilds.keys())]

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
                for lgpm, lb in ex.map(_fetch_one, args_list):
                    gpm.update(lgpm)
                    detail_bases.extend(lb)
        except Exception:
            pass

        # Ưu tiên dùng bases từ detail (có thể trùng với batch — dedupe bằng base_id)
        if detail_bases:
            seen = {b["base_id"] for b in bases}
            for b in detail_bases:
                if b["base_id"] not in seen:
                    bases.append(b)
                    seen.add(b["base_id"])
            # Nếu detail có bases, replace toàn bộ
            if detail_bases:
                bases = detail_bases  # detail luôn đầy đủ hơn

        return gpm, bases, gcolor_map

    def _parse_guild_bases(self, guilds: dict,
                           gi_offset: int = 0,
                           gname_override: str = "",
                           gcol_override: str = "") -> list:
        """Phân tích dữ liệu guild từ PD API → danh sách base có tọa độ.
        Trả về list: [{guild_name, guild_id, base_id, loc_x, loc_y, color}]
        Hỗ trợ nhiều cách đặt tên field của PalDefender."""
        bases = []
        for gi, (gid, gdata) in enumerate(guilds.items()):
            gname = (gname_override
                     or gdata.get("Name")
                     or gdata.get("GuildName")
                     or gdata.get("name")
                     or gid)
            gcol  = gcol_override or self._GUILD_COLORS[(gi + gi_offset) % len(self._GUILD_COLORS)]

            def _as_base_list(val):
                """Chuẩn hóa cấu trúc base list từ PD API:
                - Nếu val là list → trả về
                - Nếu val là dict → thử lấy list từ các key phổ biến
                - Khác → []
                """
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    for kk in ("BaseCamp", "baseCamp", "BaseCamps", "baseCamps",
                               "Bases", "bases", "Camps", "camps", "Items", "items",
                               "Data", "data", "Value", "value"):
                        vv = val.get(kk)
                        if isinstance(vv, list):
                            return vv
                    # Nếu dict có đúng 1 value là list
                    try:
                        only_lists = [v for v in val.values() if isinstance(v, list)]
                        if len(only_lists) == 1:
                            return only_lists[0]
                    except Exception:
                        pass
                return []

            # PalDefender API có thể dùng nhiều key khác nhau cho danh sách base
            raw_bases = (gdata.get("Bases")
                         or gdata.get("bases")
                         or gdata.get("Camps")
                         or gdata.get("camps")
                         or gdata.get("BaseCamp")
                         or gdata.get("baseCamp")
                         or gdata.get("Basecamp")
                         or gdata.get("BaseCamps")
                         or gdata.get("baseCamps")
                         or gdata.get("basecamp")
                         or gdata.get("base_camp")
                         or gdata.get("base_camps")
                         or [])
            raw_bases = _as_base_list(raw_bases)
            if not raw_bases:
                # Thử scan toàn bộ key trong guild detail để tìm list có vẻ là base
                try:
                    for k, v in gdata.items():
                        lk = str(k).lower()
                        if "base" in lk or "camp" in lk:
                            cand = _as_base_list(v)
                            if cand:
                                raw_bases = cand
                                break
                except Exception:
                    pass
            if not raw_bases:
                continue

            for bi, b in enumerate(raw_bases):
                if not isinstance(b, dict):
                    continue
                # Base ID
                bid = (b.get("BaseCampId")
                       or b.get("id")
                       or b.get("Id")
                       or b.get("CampId")
                       or f"{gid}_base{bi}")

                # Tọa độ — thử tất cả các kiểu field name thường gặp
                loc = None

                # Kiểu 0 (PD API của bạn): map_pos {x,y,z} là "map coords"
                # → convert sang world loc_x/loc_y theo công thức đảo _coord_to_canvas
                try:
                    mp = b.get("map_pos") or b.get("MapPos") or b.get("mapPos")
                    if isinstance(mp, dict):
                        mx = mp.get("x") if mp.get("x") is not None else mp.get("X")
                        my = mp.get("y") if mp.get("y") is not None else mp.get("Y")
                        if mx is not None and my is not None:
                            wx, wy = self._mapcoords_to_world(float(mx), float(my))
                            loc = (float(wx), float(wy))
                except Exception:
                    pass

                # Kiểu 1: BaseCampPoint: {X, Y, Z}
                bpt = (b.get("BaseCampPoint")
                       or b.get("Location")
                       or b.get("location")
                       or b.get("Pos")
                       or b.get("pos")
                       or b.get("Position")
                       or b.get("position")
                       or None)
                if isinstance(bpt, dict):
                    bx = (bpt.get("X") or bpt.get("x")
                          or bpt.get("loc_x") or bpt.get("location_x"))
                    by = (bpt.get("Y") or bpt.get("y")
                          or bpt.get("loc_y") or bpt.get("location_y"))
                    # UE có thể dùng Z là trục ngang còn Y là độ cao (hoặc ngược lại)
                    if bx is not None and by is None:
                        by = (bpt.get("Z") or bpt.get("z")
                              or bpt.get("loc_z") or bpt.get("location_z"))
                    if bx is None and by is not None:
                        bx = (bpt.get("X") or bpt.get("x"))  # giữ nguyên fallback
                    if loc is None and bx is not None and by is not None:
                        loc = (float(bx), float(by))

                # Kiểu 2: loc_x / loc_y flat trong base dict
                if loc is None:
                    bx = (b.get("X") or b.get("x")
                          or b.get("loc_x") or b.get("location_x")
                          or b.get("PosX") or b.get("posX"))
                    by = (b.get("Y") or b.get("y")
                          or b.get("loc_y") or b.get("location_y")
                          or b.get("PosY") or b.get("posY"))
                    if bx is not None and by is None:
                        by = (b.get("Z") or b.get("z")
                              or b.get("loc_z") or b.get("location_z")
                              or b.get("PosZ") or b.get("posZ"))
                    if bx is not None and by is not None:
                        loc = (float(bx), float(by))

                if loc is None:
                    continue

                bases.append({
                    "guild_name": gname,
                    "guild_id":   gid,
                    "base_id":    str(bid),
                    "loc_x":      loc[0],
                    "loc_y":      loc[1],
                    "color":      gcol,
                    "level":      b.get("Level", b.get("level", 1)),
                    "area":       b.get("Area",  b.get("area",  0)),
                })
        return bases

    def _debug_guild_data(self):
        """Mở cửa sổ debug hiển thị raw JSON từ PD API guild endpoints."""
        win = tk.Toplevel(self.root)
        win.title("🔬 Debug Guild API Data")
        win.geometry("900x600")
        win.configure(bg="#050505")

        top_f = tk.Frame(win, bg="#0a0a0a")
        top_f.pack(fill="x", padx=8, pady=6)
        tk.Label(top_f, text="🔬  Raw Guild API Data  (PalDefender)",
                 bg="#0a0a0a", fg="#cc88ff", font=("Segoe UI", 11, "bold")
                 ).pack(side="left")
        tk.Button(top_f, text="✖ Đóng", bg="#2a0000", fg="#ff7777",
                  relief="flat", command=win.destroy).pack(side="right")
        tk.Button(top_f, text="🔄 Fetch lại", bg="#0a1a2a", fg="#00ddff",
                  relief="flat", command=lambda: _do_fetch(txt)).pack(side="right", padx=4)

        txt_f = tk.Frame(win, bg="#050505")
        txt_f.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        sb  = tk.Scrollbar(txt_f)
        sb.pack(side="right", fill="y")
        txt = tk.Text(txt_f, bg="#0a0a0a", fg="#e0e0e0",
                      font=("Consolas", 9), wrap="none",
                      yscrollcommand=sb.set)
        txt.pack(fill="both", expand=True)
        sb.config(command=txt.yview)

        def _do_fetch(t):
            t.delete("1.0", tk.END)
            t.insert(tk.END, "⏳ Đang fetch /guilds...\n")
            win.update_idletasks()

            def _bg():
                out = []
                # 1. Batch guilds
                r = self._pdapi_get_guilds()
                out.append("=" * 60)
                out.append("GET /v1/pdapi/guilds")
                out.append("=" * 60)
                if r["ok"]:
                    guilds = r["data"]
                    out.append(f"→ {len(guilds)} guild(s) returned")
                    out.append(json.dumps(guilds, indent=2, ensure_ascii=False))

                    # 2. Hiện tại players từ REST API
                    out.append("\n" + "=" * 60)
                    out.append("Current players (_map_players_data):")
                    out.append("=" * 60)
                    for p in self._map_players_data:
                        out.append(f"  name={p.get('name')}  "
                                   f"playerId={p.get('playerId')}  "
                                   f"userId={p.get('userId')}")

                    # 3. Hiện tại gpm
                    out.append("\n" + "=" * 60)
                    out.append(f"Current gpm ({len(self._map_guild_player_map)} entries):")
                    out.append("=" * 60)
                    for k, v in list(self._map_guild_player_map.items())[:80]:
                        out.append(f"  {k!r:50s} → {v}")

                    # 4. Detail cho guild đầu tiên
                    if guilds:
                        first_gid = next(iter(guilds))
                        out.append("\n" + "=" * 60)
                        out.append(f"GET /v1/pdapi/guild/{first_gid}  (first guild detail)")
                        out.append("=" * 60)
                        rd = self._pdapi_get_guild(first_gid)
                        if rd["ok"]:
                            detail = rd["data"]
                            # Highlight keys liên quan base/camp để dễ map field
                            try:
                                out.append("\n" + "-" * 60)
                                out.append("Keys containing 'base'/'camp' in guild detail:")
                                out.append("-" * 60)
                                for k in sorted(detail.keys(), key=lambda x: str(x).lower()):
                                    lk = str(k).lower()
                                    if "base" in lk or "camp" in lk:
                                        v = detail.get(k)
                                        vtype = type(v).__name__
                                        vlen = len(v) if hasattr(v, "__len__") else "?"
                                        out.append(f"  {k!r}: type={vtype} len={vlen}")
                            except Exception:
                                pass
                            out.append("\n" + "-" * 60)
                            out.append("FULL DETAIL JSON:")
                            out.append("-" * 60)
                            out.append(json.dumps(detail, indent=2, ensure_ascii=False))
                        else:
                            out.append(f"❌ {rd}")
                else:
                    out.append(f"❌ {r}")

                text_out = "\n".join(out)
                def _ui():
                    t.delete("1.0", tk.END)
                    t.insert(tk.END, text_out)
                try:
                    self.root.after(0, _ui)
                except Exception:
                    pass

            threading.Thread(target=_bg, daemon=True).start()

        _do_fetch(txt)

    def _guild_refresh_now(self):
        """Gọi thủ công: fetch guild data ngay lập tức (background thread)."""
        if hasattr(self, "_lbl_guild_live_status"):
            try:
                self._lbl_guild_live_status.config(
                    text="⏳ Đang tải guild + base...", fg="#888")
            except Exception:
                pass
        def _do():
            try:
                result = self._pdapi_get_guilds()
                if result["ok"]:
                    guilds = result["data"]
                    self._map_guilds_data = guilds
                    # Dùng _build_guild_maps: UUID normalized + fetch base từ detail endpoint
                    gpm, bases, _ = self._build_guild_maps(guilds)
                    self._map_guild_player_map = gpm
                    # Nếu có base từ log PalBoxV2 thì ưu tiên hiển thị base theo log
                    log_bases = list(getattr(self, "_map_bases_by_guild", {}).values())
                    self._map_guild_bases = log_bases if log_bases else bases
                    ng = len(guilds)
                    nb = len(self._map_guild_bases)
                    nm = len(gpm)
                    def _ok(n=ng, b=nb, m=nm):
                        try:
                            if hasattr(self, "_lbl_guild_live_status"):
                                self._lbl_guild_live_status.config(
                                    text=f"✅ {n} guild  │  {b} base  │  {m} uid", fg="#00ff88")
                        except Exception:
                            pass
                        self._redraw_livemap_canvas()
                        self._update_map_player_tree()
                    self.root.after(0, _ok)
                else:
                    err = result.get("error", result.get("code", "?"))
                    def _fail():
                        try:
                            if hasattr(self, "_lbl_guild_live_status"):
                                self._lbl_guild_live_status.config(
                                    text=f"❌ {err}", fg="#ff4444")
                        except Exception:
                            pass
                    self.root.after(0, _fail)
            except Exception as e:
                def _exc(err=str(e)):
                    try:
                        if hasattr(self, "_lbl_guild_live_status"):
                            self._lbl_guild_live_status.config(
                                text=f"❌ {err}", fg="#ff4444")
                    except Exception:
                        pass
                self.root.after(0, _exc)
        threading.Thread(target=_do, daemon=True).start()

    def _map_canvas_click(self, event):
        """Xử lý click trên canvas LiveMap — hiển thị popup thông tin base / guild."""
        try:
            c  = self.map_canvas
            w  = c.winfo_width()  or 600
            h  = c.winfo_height() or 600
            mx, my = event.x, event.y
            HIT_BASE  = 24   # px hit-test radius cho base icon
            HIT_GUILD = 22   # px hit-test radius cho guild centroid

            # ── Ưu tiên 1: base icon ─────────────────
            if self._map_show_bases.get():
                hit_base  = None
                hit_bdist = HIT_BASE + 1
                for base in self._map_guild_bases:
                    try:
                        bcx, bcy = self._coord_to_canvas(
                            base["loc_x"], base["loc_y"], w, h)
                        dist = ((mx - bcx) ** 2 + (my - bcy) ** 2) ** 0.5
                        if dist < hit_bdist:
                            hit_bdist = dist
                            hit_base  = (base, bcx, bcy)
                    except Exception:
                        pass
                if hit_base:
                    self._base_detail_popup(hit_base, event.x_root, event.y_root)
                    return

            # ── Ưu tiên 2: guild centroid marker ─────
            if self._map_show_guilds.get():
                players = self._map_players_data
                gpm = self._map_guild_player_map
                guild_positions: dict = {}
                for p in players:
                    lx = p.get("location_x")
                    ly = p.get("location_y")
                    if lx is None or ly is None:
                        continue
                    cx2, cy2 = self._coord_to_canvas(float(lx), float(ly), w, h)
                    gname = self._lookup_guild(p, gpm)
                    if gname:
                        guild_positions.setdefault(gname, []).append((cx2, cy2, p))

                hit_guild = None
                hit_gdist = HIT_GUILD + 1
                for gname, pos_list in guild_positions.items():
                    cxg = sum(pp[0] for pp in pos_list) / len(pos_list)
                    cyg = sum(pp[1] for pp in pos_list) / len(pos_list)
                    dist = ((mx - cxg) ** 2 + (my - cyg) ** 2) ** 0.5
                    if dist < hit_gdist:
                        hit_gdist = dist
                        hit_guild = (gname, pos_list, cxg, cyg)

                if hit_guild:
                    self._guild_detail_popup(hit_guild, event.x_root, event.y_root)
        except Exception:
            pass

    def _base_detail_popup(self, hit_base, rx, ry):
        """Popup chi tiết khi click vào base icon trên bản đồ."""
        base, bcx, bcy = hit_base
        gname  = base.get("guild_name", "?")
        blevel = base.get("level", 1)
        barea  = base.get("area",  0)
        bid    = base.get("base_id", "?")
        bcol   = base.get("color", "#00ddff")

        # Tọa độ map chuẩn (X, Y hiển thị)
        try:
            map_x = (base["loc_y"] - 157664.55791065) / 462.962962963
            map_y = (base["loc_x"] + 123467.1611767)  / 462.962962963
        except Exception:
            map_x = map_y = 0

        popup = tk.Toplevel(self.root)
        popup.title(f"🔷 Base — {gname}")
        popup.geometry(f"+{rx + 12}+{ry - 10}")
        popup.configure(bg="#0a0a18")
        popup.resizable(False, False)
        popup.grab_set()

        # Header
        hdr = tk.Frame(popup, bg="#0d1430", pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"🔷  Base của Guild: {gname}",
                 bg="#0d1430", fg=bcol,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=12)
        tk.Button(hdr, text="✕", bg="#3a0a0a", fg="#ff4444",
                  relief="flat", font=("Segoe UI", 9, "bold"),
                  command=popup.destroy).pack(side="right", padx=8)

        # Thông tin
        info_f = tk.Frame(popup, bg="#0a0a18", padx=16, pady=8)
        info_f.pack(fill="x")

        def _lrow(label, val, fg="#e0e0e0"):
            row = tk.Frame(info_f, bg="#0a0a18")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, bg="#0a0a18", fg="#888",
                     font=("Segoe UI", 9), width=16, anchor="w").pack(side="left")
            tk.Label(row, text=str(val), bg="#0a0a18", fg=fg,
                     font=("Segoe UI", 9, "bold")).pack(side="left")

        _lrow("Guild:",       gname, bcol)
        _lrow("Base ID:",     bid[:24] + "…" if len(str(bid)) > 24 else bid, "#aaaaff")
        _lrow("Level:",       blevel, "#ffcc00")
        _lrow("Area:",        barea,  "#88ff88")
        _lrow("Tọa độ X:",   f"{map_x:.1f}", "#00ddff")
        _lrow("Tọa độ Y:",   f"{map_y:.1f}", "#00ddff")

        # Đếm số thành viên đang online của guild này
        gpm     = self._map_guild_player_map
        players = self._map_players_data
        online_members = []
        for p in players:
            pg = self._lookup_guild(p, gpm)
            if pg == gname:
                online_members.append(p)

        tk.Frame(popup, bg="#222", height=1).pack(fill="x", padx=10, pady=4)
        tk.Label(popup,
                 text=f"👥 {len(online_members)} thành viên đang online:",
                 bg="#0a0a18", fg="#00ffcc",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(0, 2))

        if online_members:
            mem_f = tk.Frame(popup, bg="#0d0d18", padx=4, pady=2)
            mem_f.pack(fill="x", padx=10, pady=(0, 6))
            for pm in online_members:
                lx2 = pm.get("location_x")
                ly2 = pm.get("location_y")
                pos_txt = ""
                if lx2 is not None and ly2 is not None:
                    mx2 = (float(ly2) - 157664.55791065) / 462.962962963
                    my2 = (float(lx2) + 123467.1611767)  / 462.962962963
                    pos_txt = f"  ({mx2:.0f},{my2:.0f})"
                tk.Label(mem_f,
                         text=f"  ▸ {pm.get('name','?')}  Lv{pm.get('level','?')}{pos_txt}",
                         bg="#0d0d18", fg="#e0e0e0",
                         font=("Segoe UI", 8)).pack(anchor="w")
        else:
            tk.Label(popup, text="  (Không có thành viên nào online)",
                     bg="#0a0a18", fg="#555",
                     font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(0, 6))

        # Tất cả bases của cùng guild
        same_guild_bases = [b for b in self._map_guild_bases
                            if b.get("guild_name") == gname]
        if len(same_guild_bases) > 1:
            tk.Frame(popup, bg="#222", height=1).pack(fill="x", padx=10, pady=2)
            tk.Label(popup,
                     text=f"🔷 {len(same_guild_bases)} base của guild này:",
                     bg="#0a0a18", fg=bcol,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14)
            for ob in same_guild_bases:
                try:
                    omx = (ob["loc_y"] - 157664.55791065) / 462.962962963
                    omy = (ob["loc_x"] + 123467.1611767)  / 462.962962963
                    is_this = "◀" if ob["base_id"] == bid else "  "
                    tk.Label(popup,
                             text=f"  {is_this} Base Lv{ob.get('level',1)}"
                                  f"  X:{omx:.0f} Y:{omy:.0f}",
                             bg="#0a0a18",
                             fg=bcol if ob["base_id"] == bid else "#888",
                             font=("Consolas", 8)).pack(anchor="w", padx=14)
                except Exception:
                    pass

        tk.Label(popup,
                 text=f"📍 Raw: loc_x={base['loc_x']:.0f}  loc_y={base['loc_y']:.0f}",
                 bg="#0a0a18", fg="#333",
                 font=("Consolas", 7)).pack(anchor="w", padx=14, pady=(4, 6))

        popup.after(30000, lambda: popup.destroy() if popup.winfo_exists() else None)

    def _guild_detail_popup(self, hit_guild, rx, ry):
        """Hiển thị cửa sổ popup thông tin chi tiết của guild khi click."""
        gname, pos_list, cxg, cyg = hit_guild
        # Lấy chi tiết guild từ cache
        guilds = self._map_guilds_data
        gdata  = {}
        for gid, gd in guilds.items():
            n = gd.get("Name", gd.get("GuildName", gid))
            if n == gname:
                gdata  = gd
                break

        popup = tk.Toplevel(self.root)
        popup.title(f"🏰 Guild: {gname}")
        popup.geometry(f"+{rx + 12}+{ry - 10}")
        popup.configure(bg="#0a0a1a")
        popup.resizable(False, False)
        popup.grab_set()

        # Header
        hdr = tk.Frame(popup, bg="#0d1a2e", pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"🏰  {gname}",
                 bg="#0d1a2e", fg="#ffcc00",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=12)
        tk.Button(hdr, text="✕", bg="#3a0a0a", fg="#ff4444",
                  relief="flat", font=("Segoe UI", 9, "bold"),
                  command=popup.destroy).pack(side="right", padx=8)

        # Thông tin guild
        info_f = tk.Frame(popup, bg="#0a0a1a", padx=14, pady=6)
        info_f.pack(fill="x")

        admin = gdata.get("AdminPlayerUid", gdata.get("AdminUid", "—"))
        total_members = gdata.get("Members", [])
        total_count   = len(total_members) if isinstance(total_members, list) else "?"

        def _lrow(label, val, fg="#e0e0e0"):
            row = tk.Frame(info_f, bg="#0a0a1a")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, bg="#0a0a1a", fg="#888",
                     font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
            tk.Label(row, text=str(val), bg="#0a0a1a", fg=fg,
                     font=("Segoe UI", 9, "bold")).pack(side="left")

        _lrow("Tổng thành viên:", total_count, "#00ffcc")
        _lrow("Online hiện tại:", len(pos_list), "#00ff88")
        _lrow("Admin UID:", admin[:32] + "…" if len(str(admin)) > 32 else admin, "#aaaaff")

        # Separator
        tk.Frame(popup, bg="#222", height=1).pack(fill="x", padx=10, pady=4)

        # Danh sách thành viên online
        tk.Label(popup, text="👥 Thành viên đang online:",
                 bg="#0a0a1a", fg="#00ffcc",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(2, 0))

        mem_f = tk.Frame(popup, bg="#0d0d14", padx=6, pady=4)
        mem_f.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        mem_cols = ("Tên", "Lv", "X", "Y")
        mem_tree = ttk.Treeview(mem_f, columns=mem_cols,
                                show="headings", height=min(len(pos_list) + 1, 12))
        mem_cw = {"Tên": 120, "Lv": 40, "X": 60, "Y": 60}
        for col in mem_cols:
            mem_tree.heading(col, text=col)
            mem_tree.column(col, width=mem_cw[col], anchor="center")
        mem_tree.pack(fill="both", expand=True)

        for (cx2, cy2, p) in pos_list:
            lx = p.get("location_x")
            ly = p.get("location_y")
            if lx is not None and ly is not None:
                map_x = (float(ly) - 157664.55791065) / 462.962962963
                map_y = (float(lx) + 123467.1611767)  / 462.962962963
                mem_tree.insert("", tk.END,
                                values=(p.get("name", "?"),
                                        p.get("level", "?"),
                                        f"{map_x:.0f}",
                                        f"{map_y:.0f}"))
            else:
                mem_tree.insert("", tk.END,
                                values=(p.get("name", "?"),
                                        p.get("level", "?"),
                                        "—", "—"))

        # Tọa độ tâm guild trên bản đồ
        cxg_map = (cxg / (self.map_canvas.winfo_width() or 600)) * 2000 - 1000
        cyg_map = 1000 - (cyg / (self.map_canvas.winfo_height() or 600)) * 2000
        tk.Label(popup,
                 text=f"📍 Trung tâm guild: X≈{cxg_map:.0f}  Y≈{cyg_map:.0f}",
                 bg="#0a0a1a", fg="#666",
                 font=("Consolas", 8)).pack(anchor="w", padx=14, pady=(0, 6))

        # Auto-close sau 30s nếu không tương tác
        popup.after(30000, lambda: popup.destroy() if popup.winfo_exists() else None)

    def _init_map_canvas_image(self):
        """Gọi sau khi canvas được render: load ảnh bản đồ theo kích thước thực."""
        if not hasattr(self, "map_canvas") or not self.map_canvas.winfo_exists():
            return
        self.map_canvas.update_idletasks()
        w = self.map_canvas.winfo_width()
        h = self.map_canvas.winfo_height()
        if w > 10 and h > 10:
            self._map_canvas_photo = self._load_map_image(w, h)
        self._redraw_livemap_canvas()

    def _redraw_livemap_canvas(self):
        """Vẽ lại toàn bộ canvas bản đồ với vị trí người chơi hiện tại."""
        if not hasattr(self, "map_canvas") or not self.map_canvas.winfo_exists():
            return
        try:
            c = self.map_canvas
            w = c.winfo_width()  or 600
            h = c.winfo_height() or 600
            c.delete("all")

            # ── Nền ──────────────────────────────────
            if self._map_canvas_photo:
                c.create_image(0, 0, image=self._map_canvas_photo, anchor="nw")
            else:
                # Fallback: lưới tối
                c.create_rectangle(0, 0, w, h, fill="#071407", outline="")
                step_x, step_y = w // 10, h // 10
                for i in range(0, w + 1, step_x):
                    c.create_line(i, 0, i, h, fill="#112211", width=1)
                for j in range(0, h + 1, step_y):
                    c.create_line(0, j, w, j, fill="#112211", width=1)
                # Trục tâm
                c.create_line(w // 2, 0, w // 2, h, fill="#1e3e1e", width=2)
                c.create_line(0, h // 2, w, h // 2, fill="#1e3e1e", width=2)
                c.create_text(w // 2 + 6, h // 2 - 12, text="(0, 0)",
                              fill="#2a6a2a", font=("Consolas", 8))
                # Ghi chú thiếu PIL
                if not _PIL_AVAILABLE:
                    c.create_text(w // 2, 18, anchor="n",
                                  text="⚠️ Cài Pillow để hiện bản đồ:  pip install Pillow",
                                  fill="#ff9900", font=("Segoe UI", 10, "bold"))
                elif not os.path.isfile(MAP_JPG):
                    c.create_text(w // 2, 18, anchor="n",
                                  text=f"⚠️ Không tìm thấy map.jpg tại: {MAP_JPG}",
                                  fill="#ff9900", font=("Segoe UI", 9))

            # ── Guild Base Layer (vẽ trước — nằm dưới player) ────────────
            if self._map_show_bases.get():
                for base in self._map_guild_bases:
                    try:
                        bx = base["loc_x"]
                        by = base["loc_y"]
                        # Icon base luôn màu xanh theo yêu cầu (không theo màu guild)
                        bcol  = "#00ddff"
                        bname = base.get("guild_name", "?")
                        bcx, bcy = self._coord_to_canvas(bx, by, w, h)
                        if not (-30 <= bcx <= w + 30 and -30 <= bcy <= h + 30):
                            continue
                        RS = 16   # outer diamond half-size
                        RI = 11   # inner diamond half-size
                        # Vòng glow ngoài
                        c.create_polygon(
                            bcx,      bcy - RS - 4,
                            bcx + RS + 4, bcy,
                            bcx,      bcy + RS + 4,
                            bcx - RS - 4, bcy,
                            fill="", outline=bcol, width=2,
                            tags=("base_glow", f"base:{bname}")
                        )
                        # Outer diamond nền tối
                        c.create_polygon(
                            bcx,      bcy - RS,
                            bcx + RS, bcy,
                            bcx,      bcy + RS,
                            bcx - RS, bcy,
                            fill="#0a1a2a", outline=bcol, width=2,
                            tags=("base_outer", f"base:{bname}")
                        )
                        # Inner diamond màu sáng
                        c.create_polygon(
                            bcx,      bcy - RI,
                            bcx + RI, bcy,
                            bcx,      bcy + RI,
                            bcx - RI, bcy,
                            fill=bcol, outline="#ffffff", width=1,
                            tags=("base_inner", f"base:{bname}")
                        )
                        # Castle emoji ở giữa
                        c.create_text(bcx, bcy,
                                      text="🏰",
                                      font=("Segoe UI", 9),
                                      tags=("base_icon", f"base:{bname}"))
                        # Label: chỉ tên guild
                        lbl = f"{bname}"
                        c.create_text(bcx + 1, bcy + RS + 13,
                                      text=lbl,
                                      fill="#000000",
                                      font=("Segoe UI", 8, "bold"))
                        c.create_text(bcx, bcy + RS + 12,
                                      text=lbl,
                                      fill=bcol,
                                      font=("Segoe UI", 8, "bold"),
                                      tags=("base_label", f"base:{bname}"))
                    except Exception:
                        pass

            # ── Người chơi ────────────────────────────
            DOT_COLORS = ["#ff6ec7", "#00ffcc", "#ffdd00", "#ff5555",
                          "#88ff44", "#4499ff", "#ff9900", "#cc44ff",
                          "#00ddff", "#ffaaaa"]
            players = self._map_players_data
            visible = 0
            for i, p in enumerate(players):
                try:
                    lx = p.get("location_x")
                    ly = p.get("location_y")
                    if lx is None or ly is None:
                        continue
                    cx, cy = self._coord_to_canvas(float(lx), float(ly), w, h)
                    # Bỏ những vị trí nằm ngoài canvas
                    if not (-20 <= cx <= w + 20 and -20 <= cy <= h + 20):
                        continue
                    color  = DOT_COLORS[i % len(DOT_COLORS)]
                    name   = p.get("name",  "?")
                    level  = p.get("level", "?")
                    r = 8
                    # Vòng hào quang
                    c.create_oval(cx - r - 3, cy - r - 3,
                                  cx + r + 3, cy + r + 3,
                                  fill="", outline=color, width=2)
                    # Chấm chính
                    c.create_oval(cx - r, cy - r, cx + r, cy + r,
                                  fill=color, outline="#ffffff", width=1)
                    # Label tên
                    c.create_text(cx + 1, cy - r - 15,
                                  text=f"Lv{level}  {name}",
                                  fill="white",
                                  font=("Segoe UI", 9, "bold"))
                    # Tọa độ nhỏ
                    mx = (float(ly) - 157664.55791065) / 462.962962963
                    my = (float(lx) + 123467.1611767)  / 462.962962963
                    c.create_text(cx, cy + r + 13,
                                  text=f"({mx:.0f}, {my:.0f})",
                                  fill="#bbbbbb", font=("Consolas", 7))
                    visible += 1
                except Exception:
                    pass

            # ── Guild Live Layer ──────────────────────
            if self._map_show_guilds.get():
                # Nhóm vị trí canvas của người chơi theo guild
                guild_positions: dict = {}   # {guild_name: [(cx, cy, name), ...]}
                gpm = self._map_guild_player_map
                for i, p in enumerate(players):
                    try:
                        lx = p.get("location_x")
                        ly = p.get("location_y")
                        if lx is None or ly is None:
                            continue
                        cx2, cy2 = self._coord_to_canvas(float(lx), float(ly), w, h)
                        if not (-20 <= cx2 <= w + 20 and -20 <= cy2 <= h + 20):
                            continue
                        # Tìm guild qua playerId / userId (chuẩn hóa UUID)
                        gname = self._lookup_guild(p, gpm)
                        if gname:
                            guild_positions.setdefault(gname, []).append(
                                (cx2, cy2, p.get("name", "?")))
                    except Exception:
                        pass

                # Màu sắc cho từng guild (tuần hoàn)
                GUILD_COLORS = [
                    "#ffcc00", "#ff6600", "#00ddff", "#ff44aa",
                    "#88ff44", "#cc88ff", "#ff8844", "#44ffcc",
                    "#ff4444", "#44aaff",
                ]
                for gi, (gname, pos_list) in enumerate(guild_positions.items()):
                    gcol = GUILD_COLORS[gi % len(GUILD_COLORS)]
                    if len(pos_list) >= 2:
                        # Vẽ đường nối các thành viên
                        for k in range(len(pos_list) - 1):
                            x1, y1, _ = pos_list[k]
                            x2, y2, _ = pos_list[k + 1]
                            c.create_line(x1, y1, x2, y2,
                                          fill=gcol, width=2,
                                          dash=(6, 4))
                    # Tính centroid
                    cxg = sum(pp[0] for pp in pos_list) / len(pos_list)
                    cyg = sum(pp[1] for pp in pos_list) / len(pos_list)
                    # Biểu tượng guild (hình thoi nhỏ)
                    rg = 7
                    c.create_polygon(
                        cxg, cyg - rg,
                        cxg + rg, cyg,
                        cxg, cyg + rg,
                        cxg - rg, cyg,
                        fill=gcol, outline="#ffffff", width=1,
                        tags=("guild_marker", f"guild:{gname}")
                    )
                    # Tên guild + số thành viên online
                    label_txt = f"🏰 {gname}  [{len(pos_list)}]"
                    # Bóng đổ chữ
                    c.create_text(cxg + 1, cyg - rg - 14,
                                  text=label_txt,
                                  fill="#000000",
                                  font=("Segoe UI", 9, "bold"))
                    c.create_text(cxg, cyg - rg - 15,
                                  text=label_txt,
                                  fill=gcol,
                                  font=("Segoe UI", 9, "bold"),
                                  tags=("guild_label", f"guild:{gname}"))

            # ── HUD góc trên trái ────────────────────
            c.create_rectangle(0, 0, 210, 56, fill="#000000", stipple="gray25",
                                outline="")
            # Số người chơi
            c.create_text(8, 4, anchor="nw",
                          text=f"👥 {visible}/{len(players)} người chơi đang hiển thị",
                          fill="white", font=("Segoe UI", 8, "bold"))
            # Số guild đang online
            hud_y = 22
            if self._map_show_guilds.get():
                guild_positions_local = {}
                gpm2 = self._map_guild_player_map
                for p in players:
                    pid  = str(p.get("playerId",  "")).lower()
                    uid  = str(p.get("userId",    "")).lower()
                    uid2 = uid.lstrip("steam_")
                    g2   = gpm2.get(pid) or gpm2.get(uid) or gpm2.get(uid2) or ""
                    if g2:
                        guild_positions_local[g2] = True
                ng = len(guild_positions_local)
                nt = len(self._map_guilds_data)
                c.create_text(8, hud_y, anchor="nw",
                              text=f"🏰 {ng} guild online  /  {nt} tổng",
                              fill="#ffcc00", font=("Segoe UI", 8))
                hud_y += 14
            if self._map_show_bases.get():
                nb = len(self._map_guild_bases)
                c.create_text(8, hud_y, anchor="nw",
                              text=f"🔷 {nb} base trên bản đồ",
                              fill="#00ddff", font=("Segoe UI", 8))
        except Exception:
            pass

    def _update_map_player_tree(self):
        """Cập nhật bảng danh sách người chơi bên phải LiveMap."""
        if not hasattr(self, "_map_player_tree") or \
           not self._map_player_tree.winfo_exists():
            return
        try:
            self._map_player_tree.delete(*self._map_player_tree.get_children())
            gpm = self._map_guild_player_map
            for p in self._map_players_data:
                lx = p.get("location_x")
                ly = p.get("location_y")
                # Tra cứu guild của player (chuẩn hóa UUID)
                guild = self._lookup_guild(p, gpm) or "—"
                if lx is not None and ly is not None:
                    mx = (float(ly) - 157664.55791065) / 462.962962963
                    my = (float(lx) + 123467.1611767)  / 462.962962963
                    self._map_player_tree.insert(
                        "", tk.END,
                        values=(p.get("name", "?"),
                                p.get("level", "?"),
                                guild,
                                f"{mx:.0f}", f"{my:.0f}")
                    )
                else:
                    self._map_player_tree.insert(
                        "", tk.END,
                        values=(p.get("name", "?"),
                                p.get("level", "?"),
                                guild,
                                "—", "—")
                    )
        except Exception:
            pass

    def map_player_fetch_loop(self):
        """Background thread: fetch player positions mỗi 3 giây cho LiveMap."""
        while True:
            try:
                res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if res.status_code == 200:
                    self._map_players_data = res.json().get("players", [])
                    self.root.after(0, self._redraw_livemap_canvas)
                    self.root.after(0, self._update_map_player_tree)
            except Exception:
                pass
            time.sleep(3)

    def guild_fetch_loop(self):
        """Background thread: fetch guild data từ PD API mỗi 30 giây cho LiveMap."""
        while True:
            try:
                result = self._pdapi_get_guilds()
                if result["ok"]:
                    guilds = result["data"]
                    self._map_guilds_data = guilds
                    # Dùng _build_guild_maps: UUID normalized + fetch base từ detail endpoint
                    gpm, bases, _ = self._build_guild_maps(guilds)
                    self._map_guild_player_map = gpm
                    # Nếu có base từ log PalBoxV2 thì ưu tiên hiển thị base theo log
                    log_bases = list(getattr(self, "_map_bases_by_guild", {}).values())
                    self._map_guild_bases = log_bases if log_bases else bases
                    ng = len(guilds)
                    nb = len(self._map_guild_bases)
                    nm = len(gpm)
                    def _ui_ok(n=ng, b=nb, m=nm):
                        try:
                            if hasattr(self, "_lbl_guild_live_status"):
                                self._lbl_guild_live_status.config(
                                    text=f"✅ {n} guild  │  {b} base  │  {m} uid", fg="#00ff88")
                        except Exception:
                            pass
                        self._redraw_livemap_canvas()
                        self._update_map_player_tree()
                    try:
                        self.root.after(0, _ui_ok)
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(30)

    # ─────────────────────────────────────────
    #  DRAW: LIVE MAP
    # ─────────────────────────────────────────
    def draw_livemap(self):
        # Tiêu đề
        title_bar = tk.Frame(self.container, bg="#0a0a0a")
        title_bar.pack(fill="x", pady=(0, 4))
        tk.Label(title_bar, text="🗺️  LIVE MAP — PALWORLD",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        pil_tag = "✅ PIL" if _PIL_AVAILABLE else "❌ PIL (pip install Pillow)"
        tk.Label(title_bar, text=pil_tag,
                 bg="#0a0a0a",
                 fg="#00ffcc" if _PIL_AVAILABLE else "#ff9900",
                 font=("Segoe UI", 9)).pack(side="right", padx=8)

        # Control bar
        ctrl = tk.Frame(self.container, bg="#111",
                        highlightthickness=1, highlightbackground="#222",
                        pady=6)
        ctrl.pack(fill="x", pady=(0, 8))

        self._lbl_map_node_status = tk.Label(
            ctrl,
            text="🟢 Live Map: EMBEDDED MODE (không cần Node.js)",
            fg="#00ffcc",
            bg="#111", font=("Segoe UI", 9, "bold")
        )
        self._lbl_map_node_status.pack(side="left", padx=12)

        tk.Button(ctrl, text="🗂 Mở thư mục map assets",
                  bg="#1a2a3a", fg="#4499ff", relief="flat", padx=12,
                  command=self._open_web_map
                  ).pack(side="left", padx=8)

        # ── Guild Live controls ─────────────────
        sep = tk.Frame(ctrl, bg="#333", width=1)
        sep.pack(side="left", fill="y", padx=6)

        tk.Checkbutton(
            ctrl, text="🏰 Hiện Guild",
            variable=self._map_show_guilds,
            bg="#111", fg="#ffcc00",
            selectcolor="#1a1a00",
            activebackground="#111", activeforeground="#ffcc00",
            font=("Segoe UI", 9, "bold"),
            command=self._redraw_livemap_canvas
        ).pack(side="left", padx=4)

        tk.Checkbutton(
            ctrl, text="🔷 Hiện Base",
            variable=self._map_show_bases,
            bg="#111", fg="#00ddff",
            selectcolor="#001a1a",
            activebackground="#111", activeforeground="#00ddff",
            font=("Segoe UI", 9, "bold"),
            command=self._redraw_livemap_canvas
        ).pack(side="left", padx=4)

        tk.Button(
            ctrl, text="🔄 Refresh Guild",
            bg="#1a1a00", fg="#ffaa00", relief="flat", padx=10,
            command=self._guild_refresh_now
        ).pack(side="left", padx=4)

        tk.Button(
            ctrl, text="🔬 Debug Guild",
            bg="#1a0a2a", fg="#cc88ff", relief="flat", padx=8,
            command=self._debug_guild_data
        ).pack(side="left", padx=2)

        # Label trạng thái guild
        self._lbl_guild_live_status = tk.Label(
            ctrl, text="⏳ Chưa tải guild",
            bg="#111", fg="#666", font=("Segoe UI", 8)
        )
        self._lbl_guild_live_status.pack(side="left", padx=6)

        _h, _p, _pw = self._api_conn_parts()
        tk.Label(ctrl,
                 text=f"URL: http://127.0.0.1:{MAP_SERVER_PORT}"
                      f"?ip={_h}&port={_p}&password={_pw}",
                 bg="#111", fg="#555", font=("Consolas", 8)
                 ).pack(side="left")

        # Main content area
        main_f = tk.Frame(self.container, bg="#0a0a0a")
        main_f.pack(fill="both", expand=True)
        main_f.grid_columnconfigure(0, weight=4)
        main_f.grid_columnconfigure(1, weight=1)
        main_f.grid_rowconfigure(0, weight=1)

        # ── Canvas (trái) ─────────────────────────
        map_outer = tk.Frame(main_f, bg="#071407",
                             highlightthickness=1, highlightbackground="#1e3e1e")
        map_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.map_canvas = tk.Canvas(map_outer, bg="#071407",
                                    bd=0, highlightthickness=0,
                                    cursor="crosshair")
        self.map_canvas.pack(fill="both", expand=True)

        # Hiển thị tọa độ khi hover
        self._lbl_map_cursor = tk.Label(
            map_outer, text="X: — , Y: —",
            bg="#0a1a0a", fg="#666", font=("Consolas", 8)
        )
        self._lbl_map_cursor.place(relx=1.0, rely=1.0, anchor="se")

        def _on_mouse_move(evt):
            try:
                w = self.map_canvas.winfo_width()
                h = self.map_canvas.winfo_height()
                # Canvas → map coords (-1000..1000)
                mx = (evt.x / w) * 2000 - 1000
                my = 1000 - (evt.y / h) * 2000
                self._lbl_map_cursor.config(
                    text=f"X: {mx:.0f} , Y: {my:.0f}")
            except Exception:
                pass

        self.map_canvas.bind("<Motion>", _on_mouse_move)
        self.map_canvas.bind("<Button-1>", self._map_canvas_click)

        # ── Player list (phải) ────────────────────
        right_f = tk.Frame(main_f, bg="#0d0d0d",
                           highlightthickness=1, highlightbackground="#222")
        right_f.grid(row=0, column=1, sticky="nsew")

        tk.Label(right_f, text="👥  ONLINE",
                 bg="#0d0d0d", fg="#00ffcc",
                 font=("Segoe UI", 10, "bold"), pady=6).pack()

        list_cols = ("Tên", "Lv", "Guild", "X", "Y")
        self._map_player_tree = ttk.Treeview(
            right_f, columns=list_cols, show="headings", height=28
        )
        col_w = {"Tên": 80, "Lv": 28, "Guild": 80, "X": 44, "Y": 44}
        for col in list_cols:
            self._map_player_tree.heading(col, text=col)
            self._map_player_tree.column(col, width=col_w[col], anchor="center")
        self._map_player_tree.pack(fill="both", expand=True, padx=2, pady=2)

        # Load ảnh sau khi canvas được render (cần kích thước thực)
        self.root.after(250, self._init_map_canvas_image)
        # Vẽ ngay với dữ liệu có sẵn
        self.root.after(280, self._redraw_livemap_canvas)
        self.root.after(300, self._update_map_player_tree)
        # Fetch guild data ngay khi mở tab (nếu chưa có)
        if not self._map_guilds_data:
            self.root.after(400, self._guild_refresh_now)

    # ─────────────────────────────────────────
    #  DRAW: RATES
    # ─────────────────────────────────────────
    # ─────────────────────────────────────────
    #  SETTINGS HELPERS
    # ─────────────────────────────────────────
    def _settings_parse_ini(self, filepath=None) -> dict:
        """Parse PalWorldSettings.ini → dict key→raw_value (delegated to app_config)."""
        filepath = filepath or PAL_SETTINGS_INI
        return cfgmod.parse_palworld_settings_ini(filepath)

    def _settings_save_ini(self, updates: dict, filepath=None) -> bool:
        """Merge updates into PalWorldSettings.ini and write back."""
        filepath = filepath or PAL_SETTINGS_INI
        try:
            cfgmod.save_palworld_settings_ini(filepath, updates)
            return True
        except ValueError:
            messagebox.showerror("Lỗi", "Không đọc được PalWorldSettings.ini!")
            return False
        except Exception as e:
            messagebox.showerror("Lỗi ghi INI", str(e))
            return False

    def _settings_manager_cfg_to_ini_updates(self, cfg: dict) -> dict:
        """Map manager_config -> PalWorldSettings OptionSettings."""
        return cfgmod.manager_cfg_to_ini_updates(cfg)

    def _settings_sync_manager_ini_to_game(self) -> bool:
        """Copy manager/PalWorldSettings.ini -> game PalWorldSettings.ini (theo SERVER_EXE hiện tại)."""
        src = MANAGER_PAL_SETTINGS_INI
        dst = PAL_SETTINGS_INI
        try:
            backup = cfgmod.sync_manager_ini_to_game(src, dst)
            if backup:
                self._enqueue_console(f"🗂️ Backup game INI: {backup}")
            self._enqueue_console(f"✅ Đồng bộ INI: {src} -> {dst}")
            return True
        except FileNotFoundError:
            messagebox.showerror("Thiếu file", f"Không tìm thấy file nguồn:\n{src}")
            return False
        except Exception as e:
            messagebox.showerror("Lỗi đồng bộ INI", str(e))
            return False

    def _settings_make_scrollable(self, parent) -> tk.Frame:
        """Tạo canvas scrollable, trả về inner Frame để đặt widgets."""
        wrap = tk.Frame(parent, bg="#0a0a0a")
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, bg="#0a0a0a", highlightthickness=0)
        vsb   = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg="#0a0a0a")
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        return inner

    def _settings_section(self, parent, title: str) -> tk.Frame:
        """Tạo nhóm có tiêu đề, trả về Frame bên trong."""
        outer = tk.Frame(parent, bg="#111", bd=0,
                         highlightthickness=1, highlightbackground="#2a2a2a")
        outer.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(outer, text=f"  {title}",
                 bg="#161626", fg="#00ffcc",
                 font=("Segoe UI", 10, "bold"), anchor="w", pady=5
                 ).pack(fill="x")
        body = tk.Frame(outer, bg="#111")
        body.pack(fill="x", padx=12, pady=(4, 10))
        return body

    def _settings_field(self, parent, row: int, label: str,
                        var, note: str = "", width: int = 38,
                        show: str = "",
                        entry_fg: str = "#e0e0e0",
                        options: list = None) -> None:
        """Một hàng label + entry/combobox + note trong body."""
        tk.Label(parent, text=label,
                 bg="#111", fg="#aaa",
                 font=("Segoe UI", 9), anchor="w",
                 width=36).grid(row=row, column=0, sticky="w", pady=3, padx=(0, 8))
        if isinstance(var, tk.BooleanVar):
            cb = tk.Checkbutton(parent, variable=var,
                                bg="#111", fg="#ccc",
                                selectcolor="#111",
                                activebackground="#111")
            cb.grid(row=row, column=1, sticky="w")
        elif options:
            cb = ttk.Combobox(parent, textvariable=var,
                              values=options, state="readonly", width=width-2)
            cb.grid(row=row, column=1, sticky="ew")
        else:
            e = tk.Entry(parent, textvariable=var,
                         bg="#1a1a2a", fg=entry_fg,
                         bd=0, font=("Consolas", 10),
                         insertbackground=entry_fg, width=width)
            if show:
                e.config(show=show)
            e.grid(row=row, column=1, sticky="ew", ipady=4)
            if show:
                is_hidden = tk.BooleanVar(value=True)
                def _toggle_pw():
                    hidden = is_hidden.get()
                    e.config(show="" if hidden else show)
                    eye_btn.config(text="🙈" if hidden else "👁")
                    is_hidden.set(not hidden)
                eye_btn = tk.Button(parent, text="👁",
                                    bg="#1a1a2a", fg="#aaa", relief="flat",
                                    padx=6, command=_toggle_pw)
                eye_btn.grid(row=row, column=2, sticky="w", padx=(6, 0))
        if note:
            tk.Label(parent, text=note,
                     bg="#111", fg="#555",
                     font=("Segoe UI", 8)).grid(row=row, column=3 if show else 2, sticky="w", padx=6)
        parent.grid_columnconfigure(1, weight=1)

    def _settings_load_manager_config(self) -> dict:
        """Đọc manager_config.json nếu có."""
        try:
            return cfgmod.load_manager_config(MANAGER_CONFIG_FILE)
        except Exception:
            pass
        return {}

    def _settings_save_manager_config(self, data: dict) -> bool:
        try:
            cfgmod.save_manager_config(MANAGER_CONFIG_FILE, data)
            return True
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
            return False

    def _menu_pref_snapshot(self) -> dict:
        return {
            "UI_ANTIBUG_ENABLED": "true" if self.antibug_enabled.get() else "false",
            "UI_ANTIBUG_MAX_PER_SEC": str(self.antibug_max_per_sec.get()),
            "UI_ANTIBUG_DISCORD_ALERT": "true" if self.antibug_discord_alert.get() else "false",
            "UI_ANTIBUG_BUILDCHECK_ENABLED": "true" if self.antibug_buildcheck_enabled.get() else "false",
            "UI_ANTIBUG_TECHCHECK_ENABLED": "true" if self.antibug_techcheck_enabled.get() else "false",
            "UI_TECHCHECK_BAN_ADMIN": "true" if self.techcheck_ban_admin.get() else "false",
            "UI_NPC_CAPTURE_BAN_ENABLED": "true" if self.npc_capture_ban_enabled.get() else "false",
            "UI_NPC_ATTACK_KICK_ENABLED": "true" if self.npc_attack_kick_enabled.get() else "false",
            "UI_PALDEF_LOG_CLEANUP_ENABLED": "true" if self.paldef_log_cleanup_enabled.get() else "false",
            "UI_PALDEF_LOG_KEEP_HOURS": str(self.paldef_log_keep_hours.get()),
        }

    def _save_menu_prefs_now(self):
        try:
            data = self._settings_load_manager_config() or {}
            data.update(self._menu_pref_snapshot())
            self._settings_save_manager_config(data)
        except Exception:
            pass

    def _schedule_menu_pref_save(self, *_):
        try:
            if self._menu_pref_after_id is not None:
                self.root.after_cancel(self._menu_pref_after_id)
        except Exception:
            pass
        self._menu_pref_after_id = self.root.after(350, self._save_menu_prefs_now)

    def _bind_menu_pref_autosave(self):
        vars_to_watch = [
            self.antibug_enabled,
            self.antibug_max_per_sec,
            self.antibug_discord_alert,
            self.antibug_buildcheck_enabled,
            self.antibug_techcheck_enabled,
            self.techcheck_ban_admin,
            self.npc_capture_ban_enabled,
            self.npc_attack_kick_enabled,
            self.paldef_log_cleanup_enabled,
            self.paldef_log_keep_hours,
        ]
        for v in vars_to_watch:
            try:
                v.trace_add("write", self._schedule_menu_pref_save)
            except Exception:
                pass

    # ─────────────────────────────────────────
    #  DRAW: DISCORD CHAT BRIDGE
    # ─────────────────────────────────────────
    def draw_discord(self):
        """Tab quản lý Discord ↔ ingame chat bridge."""
        # ── Tiêu đề ───────────────────────────────────────────────
        hdr = tk.Frame(self.container, bg="#0a0a0a")
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="🟣  DISCORD CHAT BRIDGE",
                 bg="#0a0a0a", fg="#7289da",
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        # ── Status card ────────────────────────────────────────────
        card = tk.Frame(self.container, bg="#12102a", pady=14)
        card.pack(fill="x", padx=2, pady=(0, 8))

        # Đèn trạng thái
        self._discord_status_lbl = tk.Label(
            card, text="● " + self._discord_bridge_status,
            bg="#12102a",
            fg="#00ff88" if self._discord_bridge_ok else "#ff5555",
            font=("Segoe UI", 12, "bold")
        )
        self._discord_status_lbl.pack(side="left", padx=16)

        # Nút kiểm tra thủ công
        tk.Button(card, text="🔄 Kiểm tra lại",
                  bg="#2c2f6b", fg="white", relief="flat",
                  padx=12, pady=4,
                  font=("Segoe UI", 9),
                  command=self._discord_force_check
                  ).pack(side="right", padx=12)

        # ── Thống kê ───────────────────────────────────────────────
        stats = tk.Frame(self.container, bg="#0d0f1f")
        stats.pack(fill="x", padx=2, pady=(0, 8))

        def _stat(parent, icon, label, varname, col):
            f = tk.Frame(parent, bg="#0d0f1f", padx=18, pady=10)
            f.grid(row=0, column=col, sticky="ew")
            parent.columnconfigure(col, weight=1)
            tk.Label(f, text=icon, bg="#0d0f1f", fg="#7289da",
                     font=("Segoe UI", 20)).pack()
            tk.Label(f, text=label, bg="#0d0f1f", fg="#888",
                     font=("Segoe UI", 8)).pack()
            lbl = tk.Label(f, text="0", bg="#0d0f1f", fg="white",
                           font=("Segoe UI", 14, "bold"))
            lbl.pack()
            setattr(self, varname, lbl)

        _stat(stats, "📨", "Discord → Ingame", "_lbl_dc_in",  0)
        _stat(stats, "🎮", "Ingame → Discord", "_lbl_dc_out", 1)
        _stat(stats, "⏱️", "Lần check cuối",   "_lbl_dc_ts",  2)
        _stat(stats, "🔗", "Channel ID",        "_lbl_dc_ch",  3)

        self._lbl_dc_ch.configure(
            text=DISCORD_CHAT_CHANNEL_ID[:10] + "..." if len(DISCORD_CHAT_CHANNEL_ID) > 10
            else DISCORD_CHAT_CHANNEL_ID,
            fg="#7289da", font=("Consolas", 10))

        # Cập nhật ngay các counter hiện tại
        self._discord_refresh_stats()

        # ── Cấu hình nhanh ─────────────────────────────────────────
        cfg_frame = tk.Frame(self.container, bg="#0a0a1a", pady=8)
        cfg_frame.pack(fill="x", padx=2, pady=(0, 8))
        tk.Label(cfg_frame, text="⚙️  Cấu hình nhanh",
                 bg="#0a0a1a", fg="#aaa",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=12)

        # Toggle bridge on/off
        self._discord_bridge_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(cfg_frame,
                       text="Bật Discord Bridge",
                       variable=self._discord_bridge_enabled,
                       bg="#0a0a1a", fg="#7289da",
                       selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9)
                       ).pack(side="left", padx=16)

        # Link mời Bot 1 (Mồm Lèo)
        invite_url = (f"https://discord.com/oauth2/authorize"
                      f"?client_id=1483506499064954961&scope=bot&permissions=68608")
        def _copy_invite():
            self.root.clipboard_clear()
            self.root.clipboard_append(invite_url)
            self._enqueue_console("📋 Đã copy link mời bot Discord!")
        tk.Button(cfg_frame, text="📋 Copy Link Mời Bot 1 (Mồm Lèo)",
                  bg="#5865f2", fg="white", relief="flat",
                  padx=10, pady=3,
                  font=("Segoe UI", 8),
                  command=_copy_invite).pack(side="right", padx=12)

        # ── Phân tách ──────────────────────────────────────────────
        tk.Frame(self.container, bg="#1e1e3a", height=1).pack(fill="x", padx=2, pady=(0, 4))

        # ── Log chat bridge (paned: Discord log + System log) ──────
        paned = tk.PanedWindow(self.container, orient=tk.VERTICAL,
                               bg="#1e1e3a", sashwidth=5, handlesize=0)
        paned.pack(fill="both", expand=True, padx=2, pady=(0, 4))

        # Pane trên: Discord chat log
        dc_frame = tk.Frame(paned, bg="#0a0a1a")
        paned.add(dc_frame, minsize=120)

        dc_hdr = tk.Frame(dc_frame, bg="#12102a", pady=4)
        dc_hdr.pack(fill="x")
        tk.Label(dc_hdr, text="🟣  DISCORD CHAT LOG  (Discord ↔ Ingame)",
                 bg="#12102a", fg="#7289da",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        tk.Button(dc_hdr, text="🗑 Xóa",
                  bg="#12102a", fg="#ff7777", relief="flat", padx=8,
                  command=lambda: self._dc_log.delete("1.0", tk.END)
                  ).pack(side="right", padx=4)

        self._dc_log = scrolledtext.ScrolledText(
            dc_frame, bg="#0a0a1a", fg="#7289da",
            font=("Consolas", 9), bd=0,
            insertbackground="#7289da", state="disabled"
        )
        self._dc_log.pack(fill="both", expand=True)
        self._dc_log.tag_configure("from_dc",   foreground="#7289da", font=("Consolas", 9, "bold"))
        self._dc_log.tag_configure("to_dc",     foreground="#57f287", font=("Consolas", 9, "bold"))
        self._dc_log.tag_configure("ts",        foreground="#444466")
        self._dc_log.tag_configure("name",      foreground="#eb459e")
        self._dc_log.tag_configure("sys",       foreground="#faa61a")

        # Pane dưới: gửi tin từ đây sang Discord
        send_frame = tk.Frame(paned, bg="#0a0a1a")
        paned.add(send_frame, minsize=70)

        tk.Label(send_frame, text="📤  Gửi thông báo lên Discord",
                 bg="#0a0a1a", fg="#aaa",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(6, 2))

        send_row = tk.Frame(send_frame, bg="#0a0a1a")
        send_row.pack(fill="x", padx=8, pady=4)
        self._dc_send_entry = tk.Entry(send_row,
                                       bg="#12102a", fg="#fff",
                                       bd=0, font=("Segoe UI", 10),
                                       insertbackground="#fff")
        self._dc_send_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
        self._dc_send_entry.bind("<Return>", lambda _: self._discord_send_manual())
        tk.Button(send_row, text="📤 Gửi Discord",
                  bg="#5865f2", fg="white", relief="flat",
                  padx=16, pady=4,
                  font=("Segoe UI", 9, "bold"),
                  command=self._discord_send_manual).pack(side="left")

        # ── Phân tách Bot 2 ──────────────────────────────────────────────
        tk.Frame(self.container, bg="#1e1e3a", height=2).pack(fill="x", padx=2, pady=(8, 4))
        
        # ── Discord Bot 2 ────────────────────────────────────────────────
        hdr2 = tk.Frame(self.container, bg="#0a0a0a")
        hdr2.pack(fill="x", pady=(8, 8))
        tk.Label(hdr2, text="🤖  DISCORD BOT 2 (Commands & Features)",
                 bg="#0a0a0a", fg="#00ff88",
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        # Status card Bot 2
        card2 = tk.Frame(self.container, bg="#0a1a0a", pady=14)
        card2.pack(fill="x", padx=2, pady=(0, 8))

        self._discord_bot2_status_lbl = tk.Label(
            card2, text="● " + self._discord_bot2_status,
            bg="#0a1a0a",
            fg="#00ff88" if self._discord_bot2_ok else "#ff5555",
            font=("Segoe UI", 12, "bold")
        )
        self._discord_bot2_status_lbl.pack(side="left", padx=16)

        # Thông tin Bot 2
        info_frame = tk.Frame(card2, bg="#0a1a0a")
        info_frame.pack(side="left", padx=20)
        tk.Label(info_frame, text="📋 Commands: !ranking, !stats, !search, !online, !server, !help",
                 bg="#0a1a0a", fg="#888",
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(info_frame, text="⚡ Slash Commands: /ranking, /stats, /server (hiện đại hơn)",
                 bg="#0a1a0a", fg="#888",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))
        tk.Label(info_frame, text=f"🔗 Channel: {DISCORD_BOT2_CHANNEL_ID[:20] + '...' if DISCORD_BOT2_CHANNEL_ID and len(DISCORD_BOT2_CHANNEL_ID) > 20 else (DISCORD_BOT2_CHANNEL_ID or 'Chưa cấu hình')}",
                 bg="#0a1a0a", fg="#888",
                 font=("Consolas", 8)).pack(anchor="w", pady=(2, 0))
        tk.Label(
            info_frame,
            text=f"🏆 Ranking Channel: {DISCORD_BOT2_RANKING_CHANNEL_ID[:20] + '...' if DISCORD_BOT2_RANKING_CHANNEL_ID and len(DISCORD_BOT2_RANKING_CHANNEL_ID) > 20 else (DISCORD_BOT2_RANKING_CHANNEL_ID or DISCORD_BOT2_CHANNEL_ID or 'Chưa cấu hình')}",
            bg="#0a1a0a", fg="#66cc99",
            font=("Consolas", 8)
        ).pack(anchor="w", pady=(2, 0))

        # ── Cấu hình Bot 2 ────────────────────────────────────────────────
        cfg_frame2 = tk.Frame(self.container, bg="#0a0a1a", pady=8)
        cfg_frame2.pack(fill="x", padx=2, pady=(0, 8))
        tk.Label(cfg_frame2, text="⚙️  Cấu hình Bot 2",
                 bg="#0a0a1a", fg="#aaa",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=12)

        tk.Button(cfg_frame2, text="📋 Gửi Ranking",
                  bg="#00ff88", fg="#000", relief="flat",
                  padx=10, pady=3,
                  font=("Segoe UI", 8, "bold"),
                  command=lambda: threading.Thread(
                      target=self.send_ranking_manual, daemon=True).start()
                  ).pack(side="right", padx=4)

        # Poll cập nhật stats định kỳ khi tab đang mở
        self._discord_tab_open = True
        self._discord_poll_ui()

        # Load log từ queue
        self._dc_log_flush()

    def _discord_refresh_stats(self):
        """Cập nhật các counter trên tab Discord."""
        try:
            if hasattr(self, "_lbl_dc_in") and self._lbl_dc_in.winfo_exists():
                self._lbl_dc_in.configure(text=str(self._discord_msg_in))
            if hasattr(self, "_lbl_dc_out") and self._lbl_dc_out.winfo_exists():
                self._lbl_dc_out.configure(text=str(self._discord_msg_out))
            if hasattr(self, "_lbl_dc_ts") and self._lbl_dc_ts.winfo_exists():
                ts = datetime.datetime.fromtimestamp(self._discord_last_check).strftime("%H:%M:%S") \
                     if self._discord_last_check > 0 else "—"
                self._lbl_dc_ts.configure(text=ts)
        except tk.TclError:
            # Widget đã bị destroy khi đổi tab/đóng cửa sổ, dừng poll để tránh traceback.
            self._discord_tab_open = False

    def _discord_poll_ui(self):
        """Refresh stats + flush log mỗi 2s khi tab Discord đang mở."""
        if not getattr(self, "_discord_tab_open", False):
            return
        self._discord_refresh_stats()
        # Cập nhật status label Bot 1
        if hasattr(self, "_discord_status_lbl"):
            try:
                self._discord_status_lbl.configure(
                    text="● " + self._discord_bridge_status,
                    fg="#00ff88" if self._discord_bridge_ok else
                       ("#ffa500" if "chưa" in self._discord_bridge_status.lower() or
                                     "đang" in self._discord_bridge_status.lower()
                        else "#ff5555")
                )
            except tk.TclError:
                self._discord_tab_open = False
                return
        
        # Cập nhật status label Bot 2
        if hasattr(self, "_discord_bot2_status_lbl"):
            try:
                self._discord_bot2_status_lbl.configure(
                    text="● " + self._discord_bot2_status,
                    fg="#00ff88" if self._discord_bot2_ok else
                       ("#ffa500" if "chưa" in self._discord_bot2_status.lower() or
                                     "đang" in self._discord_bot2_status.lower()
                        else "#ff5555")
                )
            except tk.TclError:
                pass
        
        self._dc_log_flush()
        self.root.after(2000, self._discord_poll_ui)

    def _dc_log_flush(self):
        """Flush Discord log queue → _dc_log widget."""
        try:
            count = 0
            while count < 50:
                entry = self._discord_log_queue.get_nowait()
                if hasattr(self, "_dc_log"):
                    try:
                        self._dc_log.configure(state="normal")
                        direction = entry.get("dir", "sys")
                        ts  = entry.get("ts",   "")
                        who = entry.get("who",  "")
                        msg = entry.get("msg",  "")
                        if direction == "from_dc":
                            self._dc_log.insert(tk.END, f"[{ts}] ", "ts")
                            self._dc_log.insert(tk.END, f"🟣 {who}", "name")
                            self._dc_log.insert(tk.END, f": {msg}\n", "from_dc")
                        elif direction == "to_dc":
                            self._dc_log.insert(tk.END, f"[{ts}] ", "ts")
                            self._dc_log.insert(tk.END, f"🎮 {who}", "name")
                            self._dc_log.insert(tk.END, f"→ Discord: {msg}\n", "to_dc")
                        else:
                            self._dc_log.insert(tk.END, f"[{ts}] ⚙️ {msg}\n", "sys")
                        self._dc_log.see(tk.END)
                        self._dc_log.configure(state="disabled")
                    except tk.TclError:
                        pass
                count += 1
        except queue.Empty:
            pass

    def _discord_send_manual(self):
        """Gửi tin nhắn thủ công lên Discord webhook từ tab Discord."""
        if not hasattr(self, "_dc_send_entry"):
            return
        msg = self._dc_send_entry.get().strip()
        if not msg:
            return
        self._dc_send_entry.delete(0, tk.END)
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self._discord_log_queue.put({
            "dir": "to_dc", "ts": now, "who": "ADMIN", "msg": msg})
        threading.Thread(
            target=self.__discord_send_webhook,
            args=("🖥️ Admin", "System", msg),
            daemon=True).start()

    def _discord_force_check(self):
        """Kiểm tra trạng thái bot Discord Gateway (thật sự)."""
        now = datetime.datetime.now().strftime("%H:%M:%S")

        # Nếu bot client đang chạy qua discord.py Gateway
        client = getattr(self, "_discord_bot_client", None)
        if client is not None:
            try:
                import discord as _discord
                if not client.is_closed() and client.is_ready():
                    self._discord_bridge_ok     = True
                    self._discord_bridge_status = f"✅ {client.user.name} — 🟢 Online"
                    self._discord_last_check    = time.time()
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": now,
                        "msg": f"✅ Bot {client.user} đang Online — Gateway kết nối tốt"})
                    return
                elif not client.is_closed() and not client.is_ready():
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = "⏳ Bot đang kết nối..."
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": now, "msg": "⏳ Bot đang trong quá trình kết nối..."})
                    return
                else:
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = "⚠️ Bot đã đóng — đang chờ reconnect..."
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": now, "msg": "⚠️ Client đã đóng — chờ luồng tự reconnect"})
                    return
            except ImportError:
                pass

        # Fallback: kiểm tra REST API nếu chưa có client
        self._discord_bridge_status = "⏳ Đang kiểm tra..."
        self._discord_bridge_ok = False
        self._discord_log_queue.put({
            "dir": "sys", "ts": now, "msg": "⏳ Đang kiểm tra via REST API..."})

        def _check():
            try:
                headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
                resp = requests.get(
                    f"https://discord.com/api/v10/channels/{DISCORD_CHAT_CHANNEL_ID}/messages",
                    headers=headers, params={"limit": 1}, timeout=8
                )
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                if resp.status_code == 200:
                    self._discord_bridge_ok     = True
                    self._discord_bridge_status = "✅ Token OK (chờ Gateway kết nối...)"
                    self._discord_last_check    = time.time()
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": ts,
                        "msg": "✅ Token hợp lệ — bot thread đang khởi động Gateway"})
                elif resp.status_code == 401:
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = "❌ Bot Token không hợp lệ"
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": ts, "msg": "❌ HTTP 401 — Token sai"})
                elif resp.status_code == 403:
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = "❌ Bot chưa có quyền đọc kênh"
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": ts,
                        "msg": "❌ HTTP 403 — Bot chưa được mời vào server"})
                else:
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = f"⚠️ HTTP {resp.status_code}"
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": ts,
                        "msg": f"⚠️ HTTP {resp.status_code}: {resp.text[:80]}"})
            except Exception as e:
                self._discord_bridge_ok     = False
                self._discord_bridge_status = f"❌ Lỗi: {e}"
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self._discord_log_queue.put({
                    "dir": "sys", "ts": ts, "msg": f"❌ {e}"})
        threading.Thread(target=_check, daemon=True).start()

    # ─────────────────────────────────────────
    #  DRAW: SETTINGS
    # ─────────────────────────────────────────
    def draw_settings(self):
        # ── Tiêu đề + toolbar ───────────────────────────────────────
        hdr = tk.Frame(self.container, bg="#0a0a0a")
        hdr.pack(fill="x", pady=(0, 6))
        tk.Label(hdr, text="⚙️  CÀI ĐẶT SERVER",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(hdr, text="(Chỉnh sửa xong nhấn 💾 Lưu bên dưới mỗi tab)",
                 bg="#0a0a0a", fg="#444",
                 font=("Segoe UI", 9)).pack(side="left", padx=12)

        # ── Notebook ────────────────────────────────────────────────
        style = ttk.Style()
        style.configure("Dark.TNotebook",          background="#0a0a0a")
        style.configure("Dark.TNotebook.Tab",      background="#161616",
                        foreground="#888", padding=[12, 6])
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", "#1a1a2a")],
                  foreground=[("selected", "#00ffcc")])

        nb = ttk.Notebook(self.container, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, pady=(0, 0))

        # ════════════════════════════════════════════════════════════
        # TAB 1 — App Config (Manager)
        # ════════════════════════════════════════════════════════════
        tab_app = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_app, text="  🖥️  App Config  ")
        inner_app = self._settings_make_scrollable(tab_app)

        cfg = self._settings_load_manager_config()

        # Vars — App Config
        _av = {}
        def _app_var(key, default=""):
            v = tk.StringVar(value=cfg.get(key, default))
            _av[key] = v
            return v

        # ─ Server EXE ─
        sec = self._settings_section(inner_app, "📁 Đường dẫn Server")
        r = 0
        self._settings_field(sec, r, "SERVER_EXE path",
                              _app_var("SERVER_EXE", SERVER_EXE),
                              note="PalServer.exe", width=60, entry_fg="#aaff77"); r += 1
        # PalWorldSettings.ini — tự derive từ SERVER_EXE, hiển thị read-only
        tk.Label(sec, text="PalWorldSettings.ini",
                 bg="#0d0d0d", fg="#555", font=("Segoe UI", 9),
                 width=24, anchor="e").grid(row=r, column=0, sticky="e",
                                            padx=(0, 8), pady=3)
        tk.Label(sec, text=f"⬆ tự tính từ SERVER_EXE  →  {PAL_SETTINGS_INI}",
                 bg="#0d0d0d", fg="#444", font=("Consolas", 8),
                 anchor="w").grid(row=r, column=1, sticky="ew", pady=3)
        r += 1

        # ─ REST API & RCON ─
        sec2 = self._settings_section(inner_app, "🌐 Kết nối API & RCON")
        r = 0
        self._settings_field(sec2, r, "API_URL (REST API game)",
                              _app_var("API_URL", API_URL),
                              note="http://127.0.0.1:8212/v1/api"); r += 1
        self._settings_field(sec2, r, "RCON Host",
                              _app_var("RCON_HOST", RCON_HOST)); r += 1
        self._settings_field(sec2, r, "RCON Port",
                              _app_var("RCON_PORT", str(RCON_PORT)),
                              note="mặc định 25575"); r += 1
        self._settings_field(sec2, r, "AdminPassword (REST + RCON)",
                              _app_var("ADMIN_PASSWORD", AUTH.password),
                              show="*", entry_fg="#ffaaaa",
                              note="Một mật khẩu dùng chung cho REST API và RCON"); r += 1
        self._settings_field(sec2, r, "PalDefender API Base URL",
                              _app_var("PALDEF_API_BASE", PALDEF_API_BASE)); r += 1

        # ─ Discord ─
        sec3 = self._settings_section(inner_app, "💬 Discord & Chat Bridge")
        r = 0
        self._settings_field(
            sec3, r, "Server Alert Webhook",
            _app_var("DISCORD_WEBHOOK_URL", DISCORD_WEBHOOK_URL),
            width=70, entry_fg="#7289da",
            note="Tạo webhook: https://discord.com/developers/docs/resources/webhook"
        ); r += 1
        self._settings_field(
            sec3, r, "AntiBug/Ban Webhook",
            _app_var("ANTIBUG_WEBHOOK_URL", ANTIBUG_WEBHOOK_URL),
            width=70, entry_fg="#7289da",
            note="Kênh admin AntiBug + ban/kick (webhook docs): https://discord.com/developers/docs/resources/webhook"
        ); r += 1
        self._settings_field(
            sec3, r, "👥 Player Connect Webhook",
            _app_var("PLAYER_CONNECT_WEBHOOK_URL", PLAYER_CONNECT_WEBHOOK_URL),
            width=70, entry_fg="#7289da",
            note="Gửi join/leave của người chơi (webhook docs): https://discord.com/developers/docs/resources/webhook"
        ); r += 1

        # ── Bot 1 ──
        tk.Label(
            sec3,
            text="🤖 Bot 1 (Mồm Lèo) — Chat Bridge 2 chiều",
            bg="#111", fg="#00ffcc",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=r, column=0, columnspan=4, sticky="w", pady=(14, 2), padx=(0, 8))
        r += 1
        self._settings_field(
            sec3, r, "Chat Bridge Webhook (Ingame → Discord)",
            _app_var("DISCORD_CHAT_WEBHOOK", DISCORD_CHAT_WEBHOOK),
            width=70, entry_fg="#00e5ff",
            note="Webhook nhận chat từ ingame (tạo webhook): https://discord.com/developers/docs/resources/webhook"
        ); r += 1
        self._settings_field(
            sec3, r, "🤖 Bot 1 Token (Mồm Lèo) — Discord → Ingame",
            _app_var("DISCORD_BOT_TOKEN", DISCORD_BOT_TOKEN),
            width=70, entry_fg="#ffd700",
            note="Bật Message Content Intent (nếu dùng on_message) tại: https://discord.com/developers/applications"
        ); r += 1
        self._settings_field(
            sec3, r, "Discord Chat Channel ID (Bot 1 - Mồm Lèo)",
            _app_var("DISCORD_CHAT_CHANNEL_ID", DISCORD_CHAT_CHANNEL_ID),
            note="Kênh Bot 1 lắng nghe chat (chuột phải kênh → Copy Channel ID)"
        ); r += 1

        # ── Bot 2 ──
        tk.Label(
            sec3,
            text="🤖 Bot 2 (Cờ Hó) — Commands & Features",
            bg="#111", fg="#00ffcc",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=r, column=0, columnspan=4, sticky="w", pady=(14, 2), padx=(0, 8))
        r += 1
        self._settings_field(
            sec3, r, "🏆 Ranking Webhook (Bot 2 - Cờ Hó)",
            _app_var("RANKING_WEBHOOK_URL", RANKING_WEBHOOK_URL),
            width=70, entry_fg="#00ff88",
            note="Webhook gửi bảng xếp hạng (webhook docs): https://discord.com/developers/docs/resources/webhook"
        ); r += 1
        self._settings_field(
            sec3, r, "🤖 Bot 2 Token (Cờ Hó)",
            _app_var("DISCORD_BOT2_TOKEN", DISCORD_BOT2_TOKEN),
            width=70, entry_fg="#ff9900",
            note="Bot 2 dùng slash/command (bật Message Content Intent nếu cần): https://discord.com/developers/applications"
        ); r += 1
        self._settings_field(
            sec3, r, "🤖 Bot 2 Channel ID",
            _app_var("DISCORD_BOT2_CHANNEL_ID", DISCORD_BOT2_CHANNEL_ID),
            note="Kênh bot Cờ Hó lắng nghe lệnh (chuột phải kênh → Copy Channel ID)"
        ); r += 1
        self._settings_field(
            sec3, r, "🏆 Bot 2 Ranking Channel ID",
            _app_var("DISCORD_BOT2_RANKING_CHANNEL_ID", DISCORD_BOT2_RANKING_CHANNEL_ID),
            note="Kênh riêng để đăng bảng xếp hạng Bot 2"
        ); r += 1
        self._settings_field(
            sec3, r, "🗺️ Bot 2 LiveMap Channel ID (tuỳ chọn)",
            _app_var("DISCORD_BOT2_LIVEMAP_CHANNEL_ID", DISCORD_BOT2_LIVEMAP_CHANNEL_ID),
            note="Nếu bỏ trống: bot2 sẽ fallback về DISCORD_BOT2_CHANNEL_ID"
        ); r += 1
        self._settings_field(
            sec3, r, "🤖 Bot 2 Name",
            _app_var("DISCORD_BOT2_NAME", DISCORD_BOT2_NAME),
            note="Tên hiển thị của Bot 2 trong app"
        ); r += 1

        # ─ AntiBug ─
        sec4 = self._settings_section(inner_app, "🛡️ AntiBug Settings")
        r = 0
        self._settings_field(sec4, r, "Max Kicks trước khi Ban",
                              _app_var("ANTIBUG_MAX_KICKS", str(ANTIBUG_MAX_KICKS)),
                              note=f"hiện tại: {ANTIBUG_MAX_KICKS}"); r += 1
        self._settings_field(sec4, r, "Kick Window (giây)",
                              _app_var("ANTIBUG_KICK_WINDOW", str(ANTIBUG_KICK_WINDOW)),
                              note="thời gian theo dõi kick"); r += 1

        # ─ Save App Config button ─
        save_bar = tk.Frame(inner_app, bg="#0a0a0a")
        save_bar.pack(fill="x", padx=14, pady=12)

        def _do_save_app():
            data = {k: v.get() for k, v in _av.items()}
            if self._settings_save_manager_config(data):
                # Áp dụng ngay vào globals — không cần restart
                _apply_manager_config(data)
                ini_updates = self._settings_manager_cfg_to_ini_updates(data)
                if ini_updates:
                    self._settings_save_ini(ini_updates, PAL_SETTINGS_INI)
                messagebox.showinfo(
                    "✅ Đã lưu & Áp dụng App Config",
                    f"Đã ghi vào:\n{MANAGER_CONFIG_FILE}\n\n"
                    "✅ Cấu hình đã được áp dụng ngay lập tức!\n\n"
                    "📡 API URL, RCON, Mật khẩu mới sẽ dùng cho\n"
                    "   tất cả lệnh tiếp theo trong phiên này."
                )

        tk.Button(save_bar,
                  text="💾  Lưu & Áp dụng ngay  (không cần restart)",
                  bg="#0d3b6e", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=10, cursor="hand2",
                  command=_do_save_app).pack(fill="x")

        # ════════════════════════════════════════════════════════════
        # TAB 2 — Server Info & Network (PalWorldSettings.ini)
        # ════════════════════════════════════════════════════════════
        tab_srv = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_srv, text="  🎮  Server & Network  ")
        inner_srv = self._settings_make_scrollable(tab_srv)

        ini = self._settings_parse_ini()
        _sv = {}   # ini StringVar/BooleanVar

        def _svar(key, default=""):
            raw = ini.get(key, str(default))
            if raw.lower() in ("true", "false"):
                v = tk.BooleanVar(value=(raw.lower() == "true"))
            else:
                v = tk.StringVar(value=raw)
            _sv[key] = v
            return v

        if not ini:
            tk.Label(inner_srv,
                     text=f"⚠️  Không tìm thấy file:\n{PAL_SETTINGS_INI}\n\n"
                          "Hãy chạy server ít nhất 1 lần để tạo file cài đặt.",
                     bg="#0a0a0a", fg="#ff7777",
                     font=("Segoe UI", 11), justify="left").pack(padx=20, pady=20)
        else:
            # Import INI từ file khác
            import_bar = tk.Frame(inner_srv, bg="#0a0a0a")
            import_bar.pack(fill="x", padx=14, pady=(8, 0))
            tk.Label(import_bar, text=f"📄 {PAL_SETTINGS_INI}",
                     bg="#0a0a0a", fg="#555", font=("Segoe UI", 8)).pack(side="left")

            def _do_import_ini():
                from tkinter import filedialog
                path = filedialog.askopenfilename(
                    title="Chọn PalWorldSettings.ini",
                    filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
                )
                if path:
                    new_ini = self._settings_parse_ini(path)
                    if new_ini:
                        for k, v in _sv.items():
                            if k in new_ini:
                                raw = new_ini[k]
                                if isinstance(v, tk.BooleanVar):
                                    v.set(raw.lower() == "true")
                                else:
                                    v.set(raw)
                        messagebox.showinfo("✅ Import", f"Đã import {len(new_ini)} tham số từ:\n{path}")
                    else:
                        messagebox.showerror("Lỗi", "Không parse được file INI!")

            tk.Button(import_bar, text="📂 Import INI từ file khác",
                      bg="#1a3a1a", fg="#aaff77",
                      relief="flat", padx=10, cursor="hand2",
                      command=_do_import_ini).pack(side="right")
            def _do_sync_manager_ini():
                if not self._settings_sync_manager_ini_to_game():
                    return
                new_ini = self._settings_parse_ini(PAL_SETTINGS_INI)
                if new_ini:
                    for k, v in _sv.items():
                        if k in new_ini:
                            raw = new_ini[k]
                            if isinstance(v, tk.BooleanVar):
                                v.set(raw.lower() == "true")
                            else:
                                v.set(raw)
                messagebox.showinfo("✅ Đồng bộ", f"Đã đồng bộ vào:\n{PAL_SETTINGS_INI}")
            tk.Button(import_bar, text="📥 Đồng bộ từ manager\\PalWorldSettings.ini",
                      bg="#1a2f45", fg="#9fd3ff",
                      relief="flat", padx=10, cursor="hand2",
                      command=_do_sync_manager_ini).pack(side="right", padx=(0, 8))

            # ─ Thông tin Server ─
            sec_s1 = self._settings_section(inner_srv, "🏷️ Thông tin Server")
            r = 0
            self._settings_field(sec_s1, r, "Server Name",
                                  _svar("ServerName","Manager ServerPal"),
                                  width=50, entry_fg="#aaff77"); r += 1
            self._settings_field(sec_s1, r, "Server Description",
                                  _svar("ServerDescription",""),
                                  width=50, entry_fg="#ccc"); r += 1
            self._settings_field(sec_s1, r, "Admin Password",
                                  _svar("AdminPassword",""),
                                  entry_fg="#ffaaaa"); r += 1
            self._settings_field(sec_s1, r, "Server Password",
                                  _svar("ServerPassword",""),
                                  note="để trống = không mật khẩu",
                                  entry_fg="#ffaaaa"); r += 1
            self._settings_field(sec_s1, r, "Region",
                                  _svar("Region","Asia"),
                                  note="Asia / EU / US..."); r += 1

            # ─ Network & Port ─
            sec_s2 = self._settings_section(inner_srv, "🌐 Network & Port")
            r = 0
            self._settings_field(sec_s2, r, "Public IP",
                                  _svar("PublicIP",""),
                                  entry_fg="#aaddff",
                                  note="IP public của server"); r += 1
            self._settings_field(sec_s2, r, "Public Port (Game)",
                                  _svar("PublicPort","8211"),
                                  note="mặc định 8211"); r += 1
            self._settings_field(sec_s2, r, "Query Port (Steam)",
                                  _svar("QueryPort","27015"),
                                  note="mặc định 27015"); r += 1
            self._settings_field(sec_s2, r, "RCON Enabled",
                                  _svar("RCONEnabled","True")); r += 1
            self._settings_field(sec_s2, r, "RCON Port",
                                  _svar("RCONPort","25575"),
                                  note="mặc định 25575"); r += 1
            self._settings_field(sec_s2, r, "REST API Enabled",
                                  _svar("RESTAPIEnabled","True")); r += 1
            self._settings_field(sec_s2, r, "REST API Port",
                                  _svar("RESTAPIPort","8212"),
                                  note="mặc định 8212"); r += 1
            self._settings_field(sec_s2, r, "Show Player List",
                                  _svar("bShowPlayerList","True")); r += 1

            # ─ Player & Guild limits ─
            sec_s3 = self._settings_section(inner_srv, "👥 Giới hạn Người chơi & Guild")
            r = 0
            self._settings_field(sec_s3, r, "Max Players (Server)",
                                  _svar("ServerPlayerMaxNum","32"),
                                  note="số người tối đa"); r += 1
            self._settings_field(sec_s3, r, "Max Players (Coop)",
                                  _svar("CoopPlayerMaxNum","4")); r += 1
            self._settings_field(sec_s3, r, "Guild Max Members",
                                  _svar("GuildPlayerMaxNum","20")); r += 1
            self._settings_field(sec_s3, r, "BaseCamp Max (Global)",
                                  _svar("BaseCampMaxNum","150")); r += 1
            self._settings_field(sec_s3, r, "BaseCamp Max/Guild",
                                  _svar("BaseCampMaxNumInGuild","1")); r += 1
            self._settings_field(sec_s3, r, "BaseCamp Workers Max",
                                  _svar("BaseCampWorkerMaxNum","20")); r += 1
            self._settings_field(sec_s3, r, "Max Buildings",
                                  _svar("MaxBuildingLimitNum","1500")); r += 1
            self._settings_field(sec_s3, r, "Auto-Reset Guild (no players)",
                                  _svar("bAutoResetGuildNoOnlinePlayers","True")); r += 1
            self._settings_field(sec_s3, r, "Guild Reset After (giờ)",
                                  _svar("AutoResetGuildTimeNoOnlinePlayers","72.000000"),
                                  note="số giờ không có ai online"); r += 1

            # ─ Misc Server ─
            sec_s4 = self._settings_section(inner_srv, "⚙️ Cấu hình khác")
            r = 0
            self._settings_field(sec_s4, r, "Auto Save mỗi (giây)",
                                  _svar("AutoSaveSpan","120.000000"),
                                  note="120 = 2 phút"); r += 1
            self._settings_field(sec_s4, r, "Supply Drop Span (phút)",
                                  _svar("SupplyDropSpan","90")); r += 1
            self._settings_field(sec_s4, r, "Chat Post Limit/phút",
                                  _svar("ChatPostLimitPerMinute","30")); r += 1
            self._settings_field(sec_s4, r, "Allow Client Mod",
                                  _svar("bAllowClientMod","False")); r += 1
            self._settings_field(sec_s4, r, "Use Backup Save Data",
                                  _svar("bIsUseBackupSaveData","True")); r += 1
            self._settings_field(sec_s4, r, "Allow Global Palbox Export",
                                  _svar("bAllowGlobalPalboxExport","True")); r += 1
            self._settings_field(sec_s4, r, "Allow Global Palbox Import",
                                  _svar("bAllowGlobalPalboxImport","False")); r += 1
            self._settings_field(sec_s4, r, "Enable Predator Boss Pal",
                                  _svar("EnablePredatorBossPal","True")); r += 1
            self._settings_field(sec_s4, r, "Show Join/Left Message",
                                  _svar("bIsShowJoinLeftMessage","True")); r += 1
            self._settings_field(sec_s4, r, "Fast Travel Enabled",
                                  _svar("bEnableFastTravel","True")); r += 1
            self._settings_field(sec_s4, r, "DenyTechnologyList",
                                  _svar("DenyTechnologyList",""),
                                  note='Ví dụ: ("PALBOX","RepairBench")'); r += 1

            # Save Server & Network
            def _do_save_server():
                updates = {}
                for k, v in _sv.items():
                    if isinstance(v, tk.BooleanVar):
                        updates[k] = "True" if v.get() else "False"
                    else:
                        updates[k] = v.get()
                if self._settings_save_ini(updates):
                    messagebox.showinfo(
                        "✅ Đã lưu",
                        "PalWorldSettings.ini đã được cập nhật!\n\n"
                        "⚠️ Cần RESTART SERVER để áp dụng thay đổi."
                    )

            save_bar2 = tk.Frame(inner_srv, bg="#0a0a0a")
            save_bar2.pack(fill="x", padx=14, pady=12)
            tk.Button(save_bar2,
                      text="💾  Lưu PalWorldSettings.ini  (cần restart server)",
                      bg="#1a5e1a", fg="white",
                      font=("Segoe UI", 10, "bold"),
                      relief="flat", pady=10, cursor="hand2",
                      command=_do_save_server).pack(fill="x")

        # ════════════════════════════════════════════════════════════
        # TAB 3 — Gameplay / Rates
        # ════════════════════════════════════════════════════════════
        tab_gp = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_gp, text="  ⚡  Gameplay & Rates  ")
        inner_gp = self._settings_make_scrollable(tab_gp)

        _gv = {}   # gameplay vars (shared write target same _sv dict)

        def _gvar(key, default="1.000000"):
            raw = ini.get(key, str(default))
            if raw.lower() in ("true", "false"):
                v = tk.BooleanVar(value=(raw.lower() == "true"))
            else:
                v = tk.StringVar(value=raw)
            _sv[key] = v   # same dict → saved by _do_save_server
            _gv[key] = v
            return v

        # ─ Core Rates ─
        sec_g1 = self._settings_section(inner_gp, "📈 Tỉ lệ cốt lõi")
        r = 0
        self._settings_field(sec_g1, r, "EXP Rate",
                              _gvar("ExpRate","1.000000"),
                              note="1.0 = gốc, 0.3 = 30%", entry_fg="#aaff77"); r += 1
        self._settings_field(sec_g1, r, "Pal Capture Rate",
                              _gvar("PalCaptureRate","1.000000"),
                              note="tỉ lệ bắt Pal", entry_fg="#aaff77"); r += 1
        self._settings_field(sec_g1, r, "Pal Spawn Rate",
                              _gvar("PalSpawnNumRate","1.000000"),
                              note="số lượng Pal spawn"); r += 1
        self._settings_field(sec_g1, r, "Work Speed Rate",
                              _gvar("WorkSpeedRate","1.000000"),
                              note="tốc độ làm việc"); r += 1
        self._settings_field(sec_g1, r, "Item Weight Rate",
                              _gvar("ItemWeightRate","1.000000"),
                              note="0.01 = rất nhẹ"); r += 1
        self._settings_field(sec_g1, r, "Collection Drop Rate",
                              _gvar("CollectionDropRate","1.000000"),
                              note="tài nguyên khai thác"); r += 1
        self._settings_field(sec_g1, r, "Enemy Drop Item Rate",
                              _gvar("EnemyDropItemRate","1.000000"),
                              note="đồ rơi từ kẻ thù"); r += 1

        # ─ Time ─
        sec_g2 = self._settings_section(inner_gp, "🕐 Thời gian & Pal")
        r = 0
        self._settings_field(sec_g2, r, "Day Time Speed Rate",
                              _gvar("DayTimeSpeedRate","1.000000"),
                              note="tốc độ ban ngày"); r += 1
        self._settings_field(sec_g2, r, "Night Time Speed Rate",
                              _gvar("NightTimeSpeedRate","1.000000"),
                              note="tốc độ ban đêm"); r += 1
        self._settings_field(sec_g2, r, "Pal Egg Hatch Time (giờ)",
                              _gvar("PalEggDefaultHatchingTime","6.000000"),
                              note="6h = mặc định"); r += 1
        self._settings_field(sec_g2, r, "Drop Item Alive (giờ)",
                              _gvar("DropItemAliveMaxHours","0.046667"),
                              note="0.05h ≈ 3 phút"); r += 1
        self._settings_field(sec_g2, r, "Drop Item Max Num",
                              _gvar("DropItemMaxNum","1000")); r += 1

        # ─ Pal Survival ─
        sec_g3 = self._settings_section(inner_gp, "🐾 Chỉ số Pal")
        r = 0
        self._settings_field(sec_g3, r, "Pal Stomach Decrease Rate",
                              _gvar("PalStomachDecreaceRate","1.000000"),
                              note="tiêu thụ thức ăn Pal"); r += 1
        self._settings_field(sec_g3, r, "Pal Stamina Decrease Rate",
                              _gvar("PalStaminaDecreaceRate","1.000000")); r += 1
        self._settings_field(sec_g3, r, "Pal Auto HP Regen Rate",
                              _gvar("PalAutoHPRegeneRate","1.000000")); r += 1
        self._settings_field(sec_g3, r, "Pal HP Regen (khi ngủ)",
                              _gvar("PalAutoHpRegeneRateInSleep","5.000000")); r += 1

        # ─ Player Survival ─
        sec_g4 = self._settings_section(inner_gp, "🧍 Chỉ số Người chơi")
        r = 0
        self._settings_field(sec_g4, r, "Player Stomach Decrease Rate",
                              _gvar("PlayerStomachDecreaceRate","1.000000")); r += 1
        self._settings_field(sec_g4, r, "Player Stamina Decrease Rate",
                              _gvar("PlayerStaminaDecreaceRate","1.000000")); r += 1
        self._settings_field(sec_g4, r, "Player Auto HP Regen Rate",
                              _gvar("PlayerAutoHPRegeneRate","1.000000")); r += 1
        self._settings_field(sec_g4, r, "Player HP Regen (khi ngủ)",
                              _gvar("PlayerAutoHpRegeneRateInSleep","1.000000")); r += 1

        save_bar3 = tk.Frame(inner_gp, bg="#0a0a0a")
        save_bar3.pack(fill="x", padx=14, pady=12)
        tk.Button(save_bar3,
                  text="💾  Lưu Gameplay Rates  (cần restart server)",
                  bg="#1a5e1a", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=10, cursor="hand2",
                  command=_do_save_server if ini else lambda: None
                  ).pack(fill="x")

        # ════════════════════════════════════════════════════════════
        # TAB 4 — Combat & PvP
        # ════════════════════════════════════════════════════════════
        tab_combat = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_combat, text="  ⚔️  Combat & PvP  ")
        inner_cb = self._settings_make_scrollable(tab_combat)

        # ─ Damage ─
        sec_c1 = self._settings_section(inner_cb, "💥 Sát thương")
        r = 0
        self._settings_field(sec_c1, r, "Pal Attack Damage Rate",
                              _gvar("PalDamageRateAttack","1.000000"),
                              note="Pal gây sát thương"); r += 1
        self._settings_field(sec_c1, r, "Pal Defense Rate",
                              _gvar("PalDamageRateDefense","1.000000"),
                              note="Pal nhận sát thương"); r += 1
        self._settings_field(sec_c1, r, "Player Attack Damage Rate",
                              _gvar("PlayerDamageRateAttack","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Player Defense Rate",
                              _gvar("PlayerDamageRateDefense","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Build Object HP Rate",
                              _gvar("BuildObjectHpRate","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Build Object Damage Rate",
                              _gvar("BuildObjectDamageRate","0.000000"),
                              note="0 = không bị phá"); r += 1
        self._settings_field(sec_c1, r, "Build Deterioration Rate",
                              _gvar("BuildObjectDeteriorationDamageRate","1.000000"),
                              note="0 = không xuống cấp"); r += 1
        self._settings_field(sec_c1, r, "Collection Object HP Rate",
                              _gvar("CollectionObjectHpRate","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Collection Object Respawn Rate",
                              _gvar("CollectionObjectRespawnSpeedRate","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Equipment Durability Damage Rate",
                              _gvar("EquipmentDurabilityDamageRate","1.000000")); r += 1

        # ─ PvP / Death ─
        sec_c2 = self._settings_section(inner_cb, "🏴 PvP & Death")
        r = 0
        self._settings_field(sec_c2, r, "PvP Mode",
                              _gvar("bIsPvP","False")); r += 1
        self._settings_field(sec_c2, r, "Player → Player Damage",
                              _gvar("bEnablePlayerToPlayerDamage","False")); r += 1
        self._settings_field(sec_c2, r, "Friendly Fire",
                              _gvar("bEnableFriendlyFire","False")); r += 1
        self._settings_field(sec_c2, r, "Hardcore Mode",
                              _gvar("bHardcore","False")); r += 1
        self._settings_field(sec_c2, r, "Pal Lost on Death",
                              _gvar("bPalLost","False")); r += 1
        self._settings_field(sec_c2, r, "Death Penalty",
                              _gvar("DeathPenalty","Item"),
                              options=["None","Item","ItemAndEquipment","All"]); r += 1
        self._settings_field(sec_c2, r, "Non Login Penalty",
                              _gvar("bEnableNonLoginPenalty","True")); r += 1
        self._settings_field(sec_c2, r, "Invader Enemy (NPC raid)",
                              _gvar("bEnableInvaderEnemy","True")); r += 1
        self._settings_field(sec_c2, r, "Can Pickup Enemy Guild Drop",
                              _gvar("bCanPickupOtherGuildDeathPenaltyDrop","False")); r += 1
        self._settings_field(sec_c2, r, "Aim Assist (Pad)",
                              _gvar("bEnableAimAssistPad","True")); r += 1
        self._settings_field(sec_c2, r, "Aim Assist (Keyboard)",
                              _gvar("bEnableAimAssistKeyboard","False")); r += 1

        # ─ Respawn ─
        sec_c3 = self._settings_section(inner_cb, "🔄 Respawn")
        r = 0
        self._settings_field(sec_c3, r, "Block Respawn Time (giây)",
                              _gvar("BlockRespawnTime","5.000000")); r += 1
        self._settings_field(sec_c3, r, "Respawn Penalty Threshold",
                              _gvar("RespawnPenaltyDurationThreshold","0.000000")); r += 1
        self._settings_field(sec_c3, r, "Respawn Penalty Time Scale",
                              _gvar("RespawnPenaltyTimeScale","2.000000")); r += 1

        save_bar4 = tk.Frame(inner_cb, bg="#0a0a0a")
        save_bar4.pack(fill="x", padx=14, pady=12)
        tk.Button(save_bar4,
                  text="💾  Lưu Combat & PvP  (cần restart server)",
                  bg="#7b0000", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=10, cursor="hand2",
                  command=_do_save_server if ini else lambda: None
                  ).pack(fill="x")


# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = ManagerServerPalApp(root)
    root.mainloop()
