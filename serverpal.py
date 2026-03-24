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
# KhÃ´ng tá»± nÃ¢ng quyá»n admin khi má»Ÿ app; cho phÃ©p cháº¡y báº±ng user thÆ°á»ng.
try:
    IS_ADMIN = bool(ctypes.windll.shell32.IsUserAnAdmin())
except Exception:
    IS_ADMIN = False

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  ÄÆ¯á»œNG DáºªN CONFIG/ASSET
#  - .py: dÃ¹ng thÆ° má»¥c source
#  - frozen .exe: config á»Ÿ thÆ° má»¥c .exe, asset/module tá»« bundle táº¡m
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Äá»ŒC manager_config.json (trÆ°á»›c khi khai bÃ¡o constants)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _read_manager_cfg() -> dict:
    """Äá»c manager_config.json, tráº£ vá» dict (rá»—ng náº¿u chÆ°a cÃ³ file)."""
    try:
        if os.path.isfile(MANAGER_CONFIG_FILE):
            with open(MANAGER_CONFIG_FILE, "r", encoding="utf-8") as _f:
                return json.load(_f)
    except Exception:
        pass
    return {}

_CFG = _read_manager_cfg()

def _cfg(key, default):
    """Láº¥y giÃ¡ trá»‹ tá»« config, fallback vá» default náº¿u khÃ´ng cÃ³."""
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
    """Chuáº©n hÃ³a SERVER_EXE tá»« config (nháº­n cáº£ file hoáº·c thÆ° má»¥c)."""
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
    """Láº¥y máº­t kháº©u admin dÃ¹ng chung cho REST/RCON."""
    for key in ("AUTH_PASS", "RCON_PASSWORD", "ADMIN_PASSWORD"):
        v = cfg.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "Admin#123"

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Cáº¤U HÃŒNH SERVER  (tá»± Ä‘á»™ng Ä‘á»c tá»« manager_config.json)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_DEFAULT_SERVER_EXE = r"C:\palwordsteamserver\steamapps\common\PalServer\PalServer.exe"
SERVER_EXE    = _resolve_server_exe_from_cfg(_CFG.get("SERVER_EXE", ""), _DEFAULT_SERVER_EXE)
API_URL       = _cfg("API_URL",       "http://127.0.0.1:8212/v1/api")
_SHARED_ADMIN_PASSWORD = _resolve_shared_admin_password(_CFG)
AUTH          = HTTPBasicAuth("admin", _SHARED_ADMIN_PASSWORD)
RCON_HOST     = _cfg("RCON_HOST",     "127.0.0.1")
RCON_PORT     = int(_cfg("RCON_PORT", 25575))
# Toggle Ä‘á»ƒ báº­t/táº¯t kiá»ƒm tra health sau khá»Ÿi Ä‘á»™ng (theo yÃªu cáº§u cÃ³ thá»ƒ táº¯t háº³n)
STARTUP_HEALTH_CHECK_ENABLED = _cfg_bool("STARTUP_HEALTH_CHECK_ENABLED", False)
STARTUP_LOG_READY_CHECK_ENABLED = _cfg_bool("STARTUP_LOG_READY_CHECK_ENABLED", True)
RCON_PASSWORD = _cfg("RCON_PASSWORD", _SHARED_ADMIN_PASSWORD)
RESET_SCHEDULE = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]
DISCORD_WEBHOOK_URL = _cfg("DISCORD_WEBHOOK_URL", "")

# â”€â”€ Táº¥t cáº£ path tá»± Ä‘á»™ng derive tá»« SERVER_EXE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _derive_paths(server_exe: str) -> tuple:
    """TÃ­nh toÃ n bá»™ Ä‘Æ°á»ng dáº«n PalServer tá»« SERVER_EXE (khÃ´ng cáº§n config thÃªm).
    Tráº£ vá»: (PAL_SETTINGS_INI, SERVER_LOG_FILE, PALDEF_LOG_DIR,
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

# ThÆ° má»¥c SaveGames gá»‘c (ngoÃ i thÆ° má»¥c con quatanthu).
SAVE_GAMES_DIR = os.path.dirname(GIFT_SAVE_DIR)

# â”€â”€ PalDefender token paths (derive tá»« PALDEF_REST_DIR) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
PALDEF_TOKEN_DIR  = os.path.join(PALDEF_REST_DIR, "Tokens")
PALDEF_TOKEN_FILE = os.path.join(PALDEF_TOKEN_DIR, "serverpal_manager.json")

# â”€â”€ Runtime log/data paths (Ä‘áº·t trong Pal/Saved/SaveGames) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ANTIBUG_LOG_FILE  = os.path.join(SAVE_GAMES_DIR, "antibug_log.txt")
ANTIBUG_BAN_FILE  = os.path.join(SAVE_GAMES_DIR, "banlist.txt")
ANTIBUG_WEBHOOK_URL = _cfg("ANTIBUG_WEBHOOK_URL",
    ""
)
ANTIBUG_MAX_KICKS   = int(_cfg("ANTIBUG_MAX_KICKS",   3))
ANTIBUG_KICK_WINDOW = int(_cfg("ANTIBUG_KICK_WINDOW", 300))

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  DISCORD CHAT BRIDGE (2 chiá»u: ingame â†” Discord)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DISCORD_CHAT_WEBHOOK    = _cfg("DISCORD_CHAT_WEBHOOK",
    ""
)
DISCORD_BOT_TOKEN       = _cfg("DISCORD_BOT_TOKEN",
    ""
)
DISCORD_CHAT_CHANNEL_ID = _cfg("DISCORD_CHAT_CHANNEL_ID", "1470301251735392309")

# â”€â”€ Discord Bot 2 (Bot thá»© 2 â€“ Cá» HÃ³) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DISCORD_BOT2_TOKEN       = _cfg("DISCORD_BOT2_TOKEN",
    ""
)
DISCORD_BOT2_CHANNEL_ID  = _cfg("DISCORD_BOT2_CHANNEL_ID", "1466418084352102432")
DISCORD_BOT2_RANKING_CHANNEL_ID = _cfg("DISCORD_BOT2_RANKING_CHANNEL_ID", "1484165199266054277")
DISCORD_BOT2_NAME        = _cfg("DISCORD_BOT2_NAME", "Cá» HÃ³")
DISCORD_BOT2_LIVEMAP_CHANNEL_ID = _cfg("DISCORD_BOT2_LIVEMAP_CHANNEL_ID", "")

# â”€â”€ Ranking Webhook (kÃªnh Báº£ng Xáº¿p Háº¡ng riÃªng) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
RANKING_WEBHOOK_URL = _cfg("RANKING_WEBHOOK_URL",
    ""
)
PLAYER_CONNECT_WEBHOOK_URL = _cfg(
    "PLAYER_CONNECT_WEBHOOK_URL",
    "",
)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  PALDEFENDER REST API
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PALDEF_REST_DIR Ä‘Æ°á»£c derive tá»« SERVER_EXE á»Ÿ khá»‘i _derive_paths bÃªn dÆ°á»›i
# PALDEF_TOKEN_DIR/FILE Ä‘Æ°á»£c gÃ¡n láº¡i sau _derive_paths
PALDEF_API_BASE    = _cfg("PALDEF_API_BASE", "http://127.0.0.1:17993")
_ANTIBUG_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[(?:info|warning)\] '(.+?)' "
    r"\(UserId=(steam_\d+),.+?\) "
    r"(has build a|dismantled) '(.+?)'"
)

# Base (PalBoxV2) placement/removal log â€” dÃ¹ng Ä‘á»ƒ cáº­p nháº­t base tá»a Ä‘á»™ theo thá»i gian thá»±c
# VÃ­ dá»¥:
# [15:29:39][info] 'MityTin' (UserId=steam_..., IP=...) has build a 'PalBoxV2' at 198 -477 919.
# [15:29:34][info] 'MityTin' (...) dismantled 'PalBoxV2' at 198 -477 926 (BuildPlayerUId: ...).
_PALBOXV2_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[(?:info|warning)\] '(.+?)' "
    r"\(UserId=(steam_\d+),.+?\) "
    r"(has build a|dismantled) 'PalBoxV2' at (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)"
)

# â”€â”€ Technology Level Database â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Dá»¯ liá»‡u Ä‘Æ°á»£c chuyá»ƒn sang file _datadb/tech_level_db.py Ä‘á»ƒ dá»… quáº£n lÃ½.
from tech_level_db import TECH_LEVEL_DB # type: ignore

# â”€â”€ Regex 1: NgÆ°á»i chÆ¡i tá»± há»c cÃ´ng nghá»‡ (natural unlock) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# VÃ­ dá»¥: [17:22:56][info] 'MityTin' (UserId=steam_...) unlocking Technology: 'RepairBench'
_TECH_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] '(.+?)' \(UserId=(steam_\d+)[^)]*\) "
    r"unlocking Technology: '(.+?)'",
    re.IGNORECASE
)

# â”€â”€ Regex 2: Admin dÃ¹ng /learntech Ä‘á»ƒ cheat (forced unlock) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# VÃ­ dá»¥: [18:09:26][info] Replying to 'MityTin' (UserId=steam_..., IP=...): "Successfully unlocked technology 'PalFoodBox' for steam_...!"
_TECH_LEARNTECH_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] Replying to '(.+?)' \(UserId=(steam_\d+)[^)]*\): "
    r'"Successfully unlocked technology \'(.+?)\' for',
    re.IGNORECASE
)

# â”€â”€ Regex theo dÃµi admin mode (bá» qua tech-check cho server admin) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

# â”€â”€ Regex chat in-game: PalDefender log format (format thá»±c táº¿) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# VÃ­ dá»¥: [21:01:27][info] [Chat::Global]['MityTin' (UserId=steam_76561199059671788, IP=192.168.1.1)]: hello
_CHAT_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] \[Chat::([^\]]+)\]\['(.+?)' \(UserId=(steam_\d+)[^)]*\)\]:\s*(.+)",
    re.IGNORECASE
)
# Fallback: PalServer.log chat format (náº¿u PalDefender khÃ´ng ghi)
# VÃ­ dá»¥: [2024.01.01-12.00.00:000][  0]LogPalServer: [SteamID] [PlayerName] said: "msg"
_SERVERLOG_CHAT_RE = re.compile(
    r"LogPalServer.*?'(.+?)'\s+(?:said|chat(?:ted)?)[:\s]+\"?(.+?)\"?\s*$",
    re.IGNORECASE
)

# â”€â”€ Pal Capture Tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Format: [HH:MM:SS][info] 'PlayerName' (UserId=steam_XXXX, IP=...) has captured Pal 'PalName' (PalID) at X Y Z.
_PAL_CAPTURE_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] '(.+?)' \(UserId=(steam_\d+)[^)]*\) has captured Pal '(.+?)' \(([^)]+)\)"
    r"(?:\s+at\s+([-\d.]+\s+[-\d.]+\s+[-\d.]+))?",
    re.IGNORECASE
)

# â”€â”€ NPC Attack Tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Format: [HH:MM:SS][info] 'PlayerName' (UserId=steam_XXXX, IP=...) was attacked by a wild 'NPC' (NpcID) at X Y Z.
_NPC_ATTACK_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\[info\] '(.+?)' \(UserId=(steam_\d+)[^)]*\) was attacked by a wild '(.+?)' \(([^)]+)\)"
    r"(?:\s+at\s+([-\d.]+\s+[-\d.]+\s+[-\d.]+))?",
    re.IGNORECASE
)

# â”€â”€ Danh sÃ¡ch NPC ID bá»‹ cáº¥m báº¯t (auto-ban ngay láº­p tá»©c) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PalID xuáº¥t hiá»‡n trong log: has captured Pal 'TÃªn' (PalID)
NPC_BAN_IDS: set = {
    "SalesPerson",          # Wandering Merchant (ThÆ°Æ¡ng nhÃ¢n lang thang)
    "SalesPerson_Desert",   # Desert Merchant
    "SalesPerson_Forest",   # Forest Merchant
    "SalesPerson_Night",    # Night Merchant
    "BlackMarketTrader",    # Black Marketeer (Chá»£ Ä‘en)
    "SalesPerson_Wander",   # Wander Merchant variant
    "PalDealer",            # Pal Dealer / Pal Trader
    "TerrorMail",           # PIDF NPC
    "Trader",               # Generic trader NPC
    "SalesPerson_Boss",     # Boss merchant variant
}

MAP_ASSETS_DIR  = os.path.join(_MANAGER_DIR, "_map_assets")
MAP_JPG         = os.path.join(MAP_ASSETS_DIR, "map.jpg")
MAP_SERVER_PORT = 3333

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  Tá»° Táº O THÆ¯ Má»¤C RUNTIME KHI KHá»žI Äá»˜NG
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _ensure_runtime_dirs() -> None:
    """Táº¡o táº¥t cáº£ thÆ° má»¥c cáº§n ghi trÆ°á»›c khi app cháº¡y.
    Gá»i sau khi táº¥t cáº£ path Ä‘Ã£ Ä‘Æ°á»£c derive xong."""
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
            pass  # á»” Ä‘Ä©a chÆ°a mount hoáº·c khÃ´ng cÃ³ quyá»n â€” bá» qua

_ensure_runtime_dirs()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  SOURCE RCON (Palworld dÃ¹ng giao thá»©c nÃ y)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def rcon_exec(command: str) -> str:
    """Káº¿t ná»‘i RCON, xÃ¡c thá»±c vÃ  thá»±c thi lá»‡nh. Tráº£ vá» response string."""
    def _refresh_rcon_runtime():
        """Äá»“ng bá»™ runtime RCON tá»« manager_config ngay trÆ°á»›c khi gá»­i lá»‡nh."""
        global RCON_HOST, RCON_PORT, RCON_PASSWORD, AUTH
        try:
            cfg = _read_manager_cfg()
            if not isinstance(cfg, dict) or not cfg:
                return
            # Æ¯u tiÃªn máº­t kháº©u admin dÃ¹ng chung Ä‘á»ƒ trÃ¡nh lá»‡ch vá»›i AppConfig má»›i lÆ°u.
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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  DYNAMIC CONFIG (Ä‘á»c tá»« manager_config.json)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def _apply_manager_config(cfg: dict) -> None:
    """Ãp dá»¥ng dict config vÃ o cÃ¡c biáº¿n toÃ n cá»¥c â€” cÃ³ hiá»‡u lá»±c ngay, khÃ´ng cáº§n restart."""
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

    # Toggle báº­t/táº¯t health-check sau khá»Ÿi Ä‘á»™ng
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
        # Re-derive toÃ n bá»™ path tá»« SERVER_EXE má»›i
        (PAL_SETTINGS_INI,
         SERVER_LOG_FILE,
         PALDEF_LOG_DIR,
         PALDEF_CHEATS_DIR,
         PALDEF_REST_DIR,
         GIFT_SAVE_DIR)    = _derive_paths(SERVER_EXE)
        PALDEF_TOKEN_DIR   = os.path.join(PALDEF_REST_DIR, "Tokens")
        PALDEF_TOKEN_FILE  = os.path.join(PALDEF_TOKEN_DIR, "serverpal_manager.json")
        _ensure_runtime_dirs()   # Táº¡o láº¡i thÆ° má»¥c náº¿u root má»›i

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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  PALWORLD ITEMS DATABASE  (Give Item dialog)
#  (category, display_name, blueprint_id, emoji)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from pw_items_db import PW_ITEMS as _PW_ITEMS # type: ignore

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  PALWORLD PALS DATABASE  (Give Pal dialog)
#  Source: paldeck.cc/pals
#  (dex, display_name, pal_id, element, emoji)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from pw_pals_db import PW_PALS as _PW_PALS # type: ignore

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  IV CALCULATOR DATA  (Source: paldb.cc/en/Iv_Calc)
#  Keyed by Pal Blueprint Code (same as _PW_PALS pal_id)
#  Fields: id, name, Hp, ShotAttack, Defense
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from iv_pal_data_db import IV_PAL_DATA as _IV_PAL_DATA # type: ignore

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  IV PASSIVE SKILLS DATA  (Source: paldb.cc/en/Iv_Calc)
#  Keyed by passive skill ID.
#  ShotAttack, Defense, CraftSpeed bonuses in % (integer)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from iv_passive_data_db import IV_PASSIVE_DATA as _IV_PASSIVE_DATA # type: ignore

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  MAIN APP
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class ManagerServerPalApp:

    # â”€â”€ Khá»Ÿi táº¡o â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def __init__(self, root):
        self.root = root
        self.root.title("Manager ServerPal v1.0.2 by MityTinDev")
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

        # Giá»¯ buffer log há»‡ thá»‘ng trong bá»™ nhá»› Ä‘á»ƒ khi chuyá»ƒn tab khÃ´ng máº¥t log
        # LÆ°u dÆ°á»›i dáº¡ng (line, tag) vá»›i tag trong {"system", "warn", "error"}
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
        self.paldef_discord_alert_main = tk.BooleanVar(value=False)  # Alert thÃªm vÃ o main webhook
        self.paldef_log_cleanup_enabled = tk.BooleanVar(value=_cfg_bool("UI_PALDEF_LOG_CLEANUP_ENABLED", True))
        _keep_hours_raw = str(_cfg("UI_PALDEF_LOG_KEEP_HOURS", "24"))
        self.paldef_log_keep_hours = tk.StringVar(value=_keep_hours_raw if _keep_hours_raw in {"24", "12", "6", "4", "2"} else "24")
        self._cheat_dedupe_last_line = ""
        self._cheat_dedupe_count = 0
        self._cheat_alert_last: dict = {}
        # Khá»Ÿi táº¡o vá»‹ trÃ­ Ä‘á»c tá»« cuá»‘i file hiá»‡n táº¡i (chá»‰ nháº­n sá»± kiá»‡n má»›i)
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
        self.STARTUP_HEALTH_RETRY_MAX      = 2  # Retry thÃªm 2 láº§n => tá»‘i Ä‘a 3 lÆ°á»£t khá»Ÿi Ä‘á»™ng
        self._startup_log_check_seq        = 0
        self._startup_log_check_lock       = threading.Lock()

        # Player caches
        self._steamid_to_name:     dict = {}
        self._steamid_to_playerid: dict = {}   # {steamid: playerId hex UUID}
        self._pending_no_steamid:  dict = {}   # {playerId: {"name": str, "since": float}}
        self._online_players_prev: set = set()  # steamids online á»Ÿ láº§n poll trÆ°á»›c

        # â”€â”€ AntiBug System â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.antibug_enabled           = tk.BooleanVar(value=_cfg_bool("UI_ANTIBUG_ENABLED", True))
        self.antibug_max_per_sec       = tk.IntVar(value=_cfg_int("UI_ANTIBUG_MAX_PER_SEC", 2))
        self.antibug_discord_alert     = tk.BooleanVar(value=_cfg_bool("UI_ANTIBUG_DISCORD_ALERT", True))
        self.antibug_buildcheck_enabled = tk.BooleanVar(value=_cfg_bool("UI_ANTIBUG_BUILDCHECK_ENABLED", True))
        self.antibug_techcheck_enabled = tk.BooleanVar(value=_cfg_bool("UI_ANTIBUG_TECHCHECK_ENABLED", True))
        self.techcheck_ban_admin       = tk.BooleanVar(value=_cfg_bool("UI_TECHCHECK_BAN_ADMIN", False))  # ban cáº£ admin
        self.npc_capture_ban_enabled   = tk.BooleanVar(value=_cfg_bool("UI_NPC_CAPTURE_BAN_ENABLED", True))   # ban khi báº¯t NPC
        self.npc_attack_kick_enabled   = tk.BooleanVar(value=_cfg_bool("UI_NPC_ATTACK_KICK_ENABLED", True))   # kick khi táº¥n cÃ´ng NPC
        self._npc_attack_events:   dict         = {}   # {steamid: {"last_kick": float, "count": int}}
        self._antibug_events:      dict         = {}   # {steamid: {...}}
        self._antibug_kick_total:  int          = 0
        self._antibug_ban_total:   int          = 0
        self._antibug_log_queue:   queue.Queue  = queue.Queue()
        self._player_level_cache:  dict         = {}   # {steamid: level}
        self._admin_mode_players:  set          = set() # steamids Ä‘ang á»Ÿ admin mode

        # â”€â”€ PalDefender REST API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._pdapi_token      = self._pdapi_ensure_token()
        self._pdapi_status_ok  = False
        self._pdapi_version    = ""

        # â”€â”€ Discord Chat Bridge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._discord_bridge_status: str   = "â³ ChÆ°a khá»Ÿi Ä‘á»™ng"
        self._discord_bridge_ok:    bool   = False
        self._discord_msg_in:       int    = 0   # Discord â†’ ingame
        self._discord_msg_out:      int    = 0   # ingame â†’ Discord
        self._discord_last_check:   float  = 0.0
        self._discord_log_queue:    queue.Queue = queue.Queue()

        # â”€â”€ Discord Bot 2 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._discord_bot2_status: str   = "â³ ChÆ°a khá»Ÿi Ä‘á»™ng"
        self._discord_bot2_ok:    bool   = False
        self._discord_bot2_client: object = None
        self._discord_bot2_loop: object = None
        # Auto-update message IDs (lÆ°u Ä‘á»ƒ edit thay vÃ¬ gá»­i má»›i)
        self._bot2_status_msg_id:  int = 0
        self._bot2_ranking_msg_id: int = 0
        self._bot2_livemap_msg_id: int = 0
        # File lÆ°u message IDs Ä‘á»ƒ dÃ¹ng láº¡i sau khi restart
        self._bot2_msg_file = os.path.join(SAVE_GAMES_DIR, "bot2_msg_ids.json")
        self._load_bot2_msg_ids()   # Load ngay khi khá»Ÿi Ä‘á»™ng

        # â”€â”€ LiveMap â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._map_node_proc:    object = None
        self._map_players_data: list   = []
        self._map_canvas_photo: object = None   # PIL PhotoImage (anti-GC)
        self._map_guilds_data:  dict   = {}     # {guild_id: {name, members, ...}}
        self._map_guild_player_map: dict = {}   # {playerid/steamid â†’ guild_name}
        self._map_show_guilds   = tk.BooleanVar(value=True)  # Toggle guild layer
        # Guild bases â€” [{guild_name, base_id, loc_x, loc_y, color}]
        self._map_guild_bases:  list   = []
        self._map_show_bases    = tk.BooleanVar(value=True)  # Toggle base layer
        # Base cache tá»« log PalBoxV2 (Æ°u tiÃªn hÆ¡n PD API náº¿u cÃ³)
        self._map_bases_by_guild: dict = {}   # {guild_name: base_dict}

        # â”€â”€ Newbie Gift System â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        # Quá»¹ thÆ°á»Ÿng TOP10/ngÃ y: sáº½ chia cho 10 suáº¥t (random pháº§n dÆ°, ná»n táº£ng váº«n Ä‘á»u).
        self.top10_bonus_pool_items = [
            {"ItemID": "Money", "Count": 1000000},  # tÆ°Æ¡ng Ä‘Æ°Æ¡ng 100k/ngÆ°á»i náº¿u Ä‘á»§ 10 online
            {"ItemID": "DogCoin", "Count": 1000},   # tÆ°Æ¡ng Ä‘Æ°Æ¡ng 100/ngÆ°á»i
        ]

        # ÄÆ°á»ng dáº«n file â€” thÆ° má»¥c quatanthu Ä‘Ã£ Ä‘Æ°á»£c táº¡o á»Ÿ trÃªn
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

        # â”€â”€ Player Ranking System â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.player_stats_file = os.path.join(SAVE_GAMES_DIR, "player_stats.json")
        self.player_time_log_file = os.path.join(SAVE_GAMES_DIR, "player_time_audit.log")
        self.player_stats: dict = {}  # {steamid: {"name": str, "level": int, "pal_count": int, "last_update": float}}
        self._player_stats_last_save_ts: float = 0.0
        self.ranking_enabled = tk.BooleanVar(value=True)
        self.ranking_update_interval = 300  # 5 phÃºt
        self.ranking_last_update = 0.0
        self._load_player_stats()

        # Auto-save tráº¡ng thÃ¡i menu báº­t/táº¯t Ä‘á»ƒ láº§n má»Ÿ sau giá»¯ nguyÃªn.
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

        # â”€â”€ RAM Optimizer config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._ram_auto_opt_var    = tk.BooleanVar(value=True)
        self._ram_opt_threshold   = tk.IntVar(value=80)   # % RAM há»‡ thá»‘ng
        self._ram_opt_interval_ms = 60_000               # 60s kiá»ƒm tra 1 láº§n
        self.root.after(2000, self._ram_monitor_loop)

        # Tá»± lÃ m má»›i tráº¡ng thÃ¡i ONLINE/OFFLINE Ä‘á»‹nh ká»³ (khÃ´ng cáº§n báº¥m "LÃ m má»›i").
        self._status_refresh_interval_ms = 5000
        self.root.after(1500, self._auto_refresh_server_status_loop)

    # â”€â”€ Styles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#111", foreground="white",
                        fieldbackground="#111", borderwidth=0, rowheight=32)
        style.configure("Treeview.Heading", background="#222", foreground="#00ffcc",
                        font=("Segoe UI", 10, "bold"))

    # â”€â”€ Sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def create_sidebar(self):
        sidebar = tk.Frame(self.root, bg="#111", width=240)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="MANAGER SERVERPAL", font=("Segoe UI", 18, "bold"),
                 bg="#111", fg="#00ffcc", pady=24).pack()

        tabs = [
            ("ðŸ“Š Tá»”NG QUAN",    "Overview"),
            ("ðŸ–¥ï¸ ÄIá»€U KHIá»‚N",  "Dash"),
            ("ðŸ‘¥ NGÆ¯á»œI CHÆ I",  "Players"),
            ("ðŸŽ QUÃ€ Táº¶NG",    "NewbieGift"),
            ("ðŸ›¡ï¸ PALDEFENDER", "PalDefender"),
            ("ðŸ—ºï¸ LIVE MAP",    "LiveMap"),
            ("ðŸŸ£ DISCORD CHAT", "Discord"),
            ("âš™ï¸ CÃ€I Äáº¶T",     "Settings"),
        ]
        for text, tag in tabs:
            tk.Button(sidebar, text=text, font=("Segoe UI", 11), bg="#111", fg="#ccc",
                      relief="flat", anchor="w", padx=28, pady=13,
                      command=lambda t=tag: self.switch_tab(t)).pack(fill="x")

        tk.Label(sidebar, text="Tá»° Äá»˜NG HÃ“A", font=("Segoe UI", 8, "bold"),
                 bg="#111", fg="#555", pady=16).pack()
        tk.Checkbutton(sidebar, text="CHáº¾ Äá»˜ AUTO", variable=self.auto_mode,
                       bg="#111", fg="#00ffcc", selectcolor="#111",
                       font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=28)

        self.lbl_status = tk.Label(sidebar, text="â— SERVER ONLINE",
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

    # â”€â”€ Console helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _enqueue_console(self, text: str):
        """Thread-safe: Ä‘Æ°a text vÃ o queue Ä‘á»ƒ main thread hiá»ƒn thá»‹."""
        self._console_queue.put(text)

    def _poll_console_queue(self):
        """Cháº¡y má»—i 150ms trÃªn main thread Ä‘á»ƒ flush queue ra console."""
        try:
            while True:
                msg = self._console_queue.get_nowait()
                self._write_console_direct(msg)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_console_queue)

    def _poll_server_log_queue(self):
        """Cháº¡y má»—i 200ms trÃªn main thread Ä‘á»ƒ flush server log queue ra server_console."""
        try:
            count = 0
            while count < 80:   # tá»‘i Ä‘a 80 dÃ²ng má»—i vÃ²ng Ä‘á»ƒ khÃ´ng Ä‘Ã³ng bÄƒng UI
                line = self._server_log_queue.get_nowait()
                if hasattr(self, "server_console") and self.server_console.winfo_exists():
                    # Ãp dá»¥ng filter náº¿u cÃ³
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
        """Flush PalDefender main log queue â†’ paldef_console (main thread)."""
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
        """Flush PalDefender cheat queue â†’ paldef_cheat_console (main thread)."""
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
        """Flush AntiBug log queue â†’ antibug_console (main thread)."""
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
        """Ghi log ra Ä‘Ãºng pane: chat (ðŸ’¬/ðŸ“¢) â†’ chat_console; cÃ²n láº¡i â†’ system console."""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        is_chat_in  = text.startswith("ðŸ’¬")
        is_chat_out = text.startswith("ðŸ“¢ ADMIN")

        if is_chat_in or is_chat_out:
            # â”€â”€ Ghi vÃ o CHAT pane â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if hasattr(self, "chat_console") and self.chat_console.winfo_exists():
                self.chat_console.configure(state="normal")
                if is_chat_in:
                    # PhÃ¢n tÃ­ch: ðŸ’¬ [HH:MM:SS] [Channel] PlayerName: msg
                    # hoáº·c:     ðŸ’¬ PlayerName: msg  (fallback)
                    import re as _re
                    m = _re.match(
                        r"ðŸ’¬ \[(\d{2}:\d{2}:\d{2})\] \[([^\]]+)\] (.+?):\s*(.+)", text)
                    if m:
                        ts, ch, plr, msg = m.groups()
                        # Lá»c theo kÃªnh
                        flt = getattr(self, "_chat_filter_var", None)
                        if flt and flt.get() not in ("All", ch):
                            self.chat_console.configure(state="disabled")
                            return
                        self.chat_console.insert(tk.END, f"[{ts}] ", "ts")
                        self.chat_console.insert(tk.END, f"[{ch}] ", "channel")
                        self.chat_console.insert(tk.END, f"{plr}: ", "player")
                        self.chat_console.insert(tk.END, f"{msg}\n")
                    else:
                        # fallback khÃ´ng cÃ³ timestamp/channel
                        self.chat_console.insert(
                            tk.END, f"[{now}] {text[2:].strip()}\n", "player")
                else:
                    # Admin broadcast
                    msg = text.replace("ðŸ“¢ ADMIN â†’ ", "", 1)
                    self.chat_console.insert(tk.END, f"[{now}] ", "ts")
                    self.chat_console.insert(tk.END, f"ADMIN: ", "admin")
                    self.chat_console.insert(tk.END, f"{msg}\n")
                self.chat_console.see(tk.END)
                self.chat_console.configure(state="disabled")
        else:
            # â”€â”€ Ghi vÃ o SYSTEM LOG pane â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            tag = "error" if any(x in text for x in ("âŒ","Lá»—i","ERROR")) \
                  else "warn"  if any(x in text for x in ("âš ï¸","WARNING")) \
                  else "system"
            formatted = f"[{now}] {text}\n"
            # LÆ°u vÃ o buffer Ä‘á»ƒ khi quay láº¡i tab váº«n cÃ²n log
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
        """Ghi láº¡i toÃ n bá»™ buffer há»‡ thá»‘ng vÃ o widget má»›i táº¡o (khi Ä‘á»•i tab)."""
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
        """Gá»i tá»« main thread."""
        self._write_console_direct(text)

    # â”€â”€ Discord / Broadcast â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Discord Chat Bridge â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _discord_forward_chat(self, player_name: str, channel: str, message: str):
        """Gá»­i tin nháº¯n ingame â†’ Discord webhook (dÃ¹ng username cá»§a ngÆ°á»i chÆ¡i)."""
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
        # Giá»¯ Ä‘á»ƒ tÆ°Æ¡ng thÃ­ch ngÆ°á»£c náº¿u nÆ¡i khÃ¡c cÃ²n gá»i
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
        """Background thread: cháº¡y Discord bot tháº­t qua Gateway WebSocket.
        Bot sáº½ hiá»ƒn thá»‹ ONLINE trÃªn Discord.
        YÃŠU Cáº¦U: Báº­t 'Message Content Intent' táº¡i
        https://discord.com/developers/applications â†’ Bot â†’ Privileged Gateway Intents
        """
        import asyncio
        import re as _re
        try:
            import discord as _discord
        except ImportError:
            self._discord_bridge_status = "âŒ Thiáº¿u thÆ° viá»‡n discord.py â€” pip install discord.py"
            self._enqueue_console("âŒ Discord: pip install discord.py")
            return

        # â”€â”€ Chá» app khá»Ÿi Ä‘á»™ng xong â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        time.sleep(5)

        if not DISCORD_BOT_TOKEN or not DISCORD_CHAT_CHANNEL_ID:
            self._discord_bridge_status = "âš ï¸ ChÆ°a cáº¥u hÃ¬nh Bot Token / Channel ID"
            self._enqueue_console("âš ï¸ Discord Chat Bridge: chÆ°a cáº¥u hÃ¬nh Bot Token / Channel ID")
            return

        def _dc_log(direction: str, who: str, msg: str):
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._discord_log_queue.put({"dir": direction, "ts": ts, "who": who, "msg": msg})

        # â”€â”€ Táº¡o client factory (cáº§n client má»›i má»—i láº§n reconnect) â”€
        def _make_client():
            intents = _discord.Intents.default()
            intents.message_content = True   # Privileged â€” báº­t trong Developer Portal
            intents.messages        = True
            c = _discord.Client(intents=intents)

            @c.event
            async def on_ready():
                # Äá»•i tÃªn bot thÃ nh "Má»“m LÃ¨o" náº¿u chÆ°a Ä‘Ãºng tÃªn
                desired_name = "Má»“m LÃ¨o"
                if c.user.name != desired_name:
                    try:
                        await c.user.edit(username=desired_name)
                        _dc_log("sys", "", f"âœ… ÄÃ£ Ä‘á»•i tÃªn bot â†’ '{desired_name}'")
                    except _discord.errors.HTTPException as _e:
                        # Rate limit Ä‘á»•i tÃªn: 2 láº§n/giá» â€” bá» qua náº¿u bá»‹ giá»›i háº¡n
                        _dc_log("sys", "", f"âš ï¸ ChÆ°a Ä‘á»•i Ä‘Æ°á»£c tÃªn: {_e} (giá»›i háº¡n 2 láº§n/giá»)")

                self._discord_bridge_ok     = True
                self._discord_bridge_status = f"âœ… {c.user.name} â€” ðŸŸ¢ Online"
                self._discord_last_check    = time.time()
                self._enqueue_console(
                    f"âœ… Discord Bot '{c.user.name}' Ä‘Ã£ káº¿t ná»‘i Gateway â€” Online!")
                _dc_log("sys", "", f"âœ… Bot {c.user.name} Online â€” Gateway WebSocket káº¿t ná»‘i thÃ nh cÃ´ng")

            @c.event
            async def on_disconnect():
                self._discord_bridge_ok     = False
                self._discord_bridge_status = "âš ï¸ Máº¥t káº¿t ná»‘i â€” Ä‘ang reconnect..."
                _dc_log("sys", "", "âš ï¸ Bot máº¥t káº¿t ná»‘i Discord, discord.py Ä‘ang tá»± reconnect...")

            @c.event
            async def on_resumed():
                self._discord_bridge_ok     = True
                self._discord_bridge_status = f"âœ… ÄÃ£ reconnect â€” ðŸŸ¢ Online"
                _dc_log("sys", "", "âœ… Bot Ä‘Ã£ reconnect thÃ nh cÃ´ng")

            @c.event
            async def on_message(message):
                # Chá»‰ xá»­ lÃ½ kÃªnh Ä‘Ã£ cáº¥u hÃ¬nh
                if str(message.channel.id) != str(DISCORD_CHAT_CHANNEL_ID):
                    return
                # Bá» qua bot vÃ  webhook (trÃ¡nh vÃ²ng láº·p ingameâ†’discordâ†’ingame)
                if message.author.bot or message.webhook_id:
                    return
                content = message.content.strip()
                if not content:
                    return
                # Lá»‡nh kiá»ƒm tra Bot 2 tá»« Bot 1
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
                    line1 = f"âœ… Bot 2 OK: {bot2_name}" if ok else "âŒ Bot 2 chÆ°a sáºµn sÃ ng"
                    line2 = (
                        f"â€¢ connected: {'YES' if bot2_connected else 'NO'} | "
                        f"latency: {bot2_latency_ms if bot2_latency_ms >= 0 else 'n/a'} ms"
                    )
                    line3 = f"â€¢ status: {bot2_status}"
                    await message.channel.send(f"{line1}\n{line2}\n{line3}")
                    _dc_log("sys", "Bot1", f"pingbot2 -> ok={ok}, connected={bot2_connected}, latency={bot2_latency_ms}")
                    return
                # XÃ³a mention <@id>
                clean = _re.sub(r"<@!?\d+>", "", content).strip()
                if not clean:
                    return
                username = message.author.display_name or message.author.name
                broadcast_text = f"[Discord] {username}: {clean}"
                self.send_ingame_broadcast(broadcast_text)
                self._enqueue_console(f"ðŸ’¬ [Discord] {username}: {clean}")
                self._discord_msg_in  += 1
                self._discord_last_check = time.time()
                _dc_log("from_dc", username, clean)

            return c

        # â”€â”€ Cháº¡y bot vá»›i auto-reconnect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._discord_bot_loop = loop

        while True:
            client = _make_client()
            self._discord_bot_client = client
            self._discord_bridge_status = "â³ Äang káº¿t ná»‘i Discord Gateway..."
            _dc_log("sys", "", "â³ Äang káº¿t ná»‘i Discord Gateway WebSocket...")
            try:
                loop.run_until_complete(client.start(DISCORD_BOT_TOKEN))
            except _discord.errors.LoginFailure:
                self._discord_bridge_ok     = False
                self._discord_bridge_status = "âŒ Bot Token khÃ´ng há»£p lá»‡"
                self._enqueue_console(
                    "âŒ Discord: Bot Token khÃ´ng há»£p lá»‡ â€” vÃ o CÃ€I Äáº¶T â†’ App Config Ä‘á»ƒ sá»­a")
                _dc_log("sys", "", "âŒ LoginFailure â€” Token sai, dá»«ng háº³n")
                return   # KhÃ´ng retry náº¿u token sai
            except _discord.errors.PrivilegedIntentsRequired:
                self._discord_bridge_ok     = False
                self._discord_bridge_status = "âŒ Cáº§n báº­t Message Content Intent"
                self._enqueue_console(
                    "âŒ Discord: Cáº§n báº­t 'MESSAGE CONTENT INTENT'\n"
                    "   â†’ discord.com/developers/applications â†’ Bot cá»§a báº¡n â†’ Bot\n"
                    "   â†’ Privileged Gateway Intents â†’ MESSAGE CONTENT INTENT âœ…")
                _dc_log("sys", "", "âŒ PrivilegedIntentsRequired â€” báº­t Message Content Intent")
                return
            except KeyboardInterrupt:
                return
            except Exception as e:
                self._discord_bridge_ok     = False
                self._discord_bridge_status = f"âš ï¸ Lá»—i káº¿t ná»‘i â€” thá»­ láº¡i sau 15s"
                _dc_log("sys", "", f"âš ï¸ Lá»—i: {e} â€” thá»­ láº¡i sau 15s...")
            finally:
                try:
                    if not client.is_closed():
                        loop.run_until_complete(client.close())
                except Exception:
                    pass
            time.sleep(15)

    def discord_bot2_poll(self):
        """Background thread: cháº¡y Discord Bot 2 vá»›i commands vÃ  tÃ­nh nÄƒng riÃªng.
        Bot nÃ y cÃ³ thá»ƒ dÃ¹ng cho ranking, stats, server info, vÃ  cÃ¡c commands khÃ¡c.
        """
        import asyncio
        try:
            import discord as _discord
            from discord.ext import commands
        except ImportError:
            self._discord_bot2_status = "âŒ Thiáº¿u thÆ° viá»‡n discord.py â€” pip install discord.py"
            self._enqueue_console("âŒ Discord Bot 2: pip install discord.py")
            return

        # â”€â”€ Chá» app khá»Ÿi Ä‘á»™ng xong â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        time.sleep(10)

        if not DISCORD_BOT2_TOKEN:
            self._discord_bot2_status = "âš ï¸ ChÆ°a cáº¥u hÃ¬nh Bot 2 Token"
            self._enqueue_console("âš ï¸ Discord Bot 2: chÆ°a cáº¥u hÃ¬nh Token")
            return

        # â”€â”€ Táº¡o bot vá»›i commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        intents = _discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        bot = commands.Bot(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # â”€â”€ Capture outer self Ä‘á»ƒ dÃ¹ng trong View closures â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _app = self   # ServerPalApp instance

        def _save_bot2_channel_config(main_channel_id: str | None = None,
                                      ranking_channel_id: str | None = None):
            """LÆ°u channel id cá»§a Bot2 vÃ o manager_config Ä‘á»ƒ giá»¯ sau restart."""
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
                self._enqueue_console(f"âš ï¸ Bot2: KhÃ´ng lÆ°u Ä‘Æ°á»£c channel config: {e}")

        def _save_manager_cfg(cfg: dict) -> bool:
            try:
                with open(MANAGER_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
                return True
            except Exception as e:
                self._enqueue_console(f"âš ï¸ Bot2: KhÃ´ng lÆ°u Ä‘Æ°á»£c manager_config: {e}")
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

        @bot.tree.command(name="pingserver", description="Kiá»ƒm tra káº¿t ná»‘i IP:PORT game (TCP), REST vÃ  RCON")
        async def slash_pingserver(interaction: _discord.Interaction):
            """Slash command: Ping server Ä‘a táº§ng tá»« Discord (TCP/REST/RCON)."""
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
                    content="âš ï¸ ChÆ°a cáº¥u hÃ¬nh profile server active (ip_public/game_port). DÃ¹ng /createserver trÆ°á»›c.",
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
                status  = "âœ… ONLINE (cÃ³ thá»ƒ vÃ o Ä‘Æ°á»£c)" if overall else "âŒ ChÆ°a sáºµn sÃ ng hoáº·c lá»—i"

                msg = (
                    f"â€¢ Profile: `{name or 'N/A'}` â€” `{ip}:{game_port}`\n"
                    f"â€¢ ping: {'OK' if ping_ok else 'FAIL'} | "
                    f"tcp: {'OK' if tcp_ok else 'FAIL'} | "
                    f"rest: {'OK' if rest_ok else 'FAIL'} | "
                    f"rcon: {'OK' if rcon_ok else 'FAIL'}\n"
                    f"â†’ Tráº¡ng thÃ¡i: {status}"
                )
                await interaction.followup.send(content=msg, ephemeral=True)
            except Exception as e:
                await interaction.followup.send(content=f"âš ï¸ Ping lá»—i: {e}", ephemeral=True)

        @bot.tree.command(name="start", description="Khá»Ÿi Ä‘á»™ng server (an toÃ n)")
        async def slash_start(interaction: _discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                if _app._is_server_running():
                    await interaction.followup.send("â„¹ï¸ Server Ä‘ang cháº¡y rá»“i.", ephemeral=True)
                    return
                ok = _app._start_server_safe(source="Discord Start")
                if ok:
                    await interaction.followup.send("âœ… ÄÃ£ gá»­i lá»‡nh khá»Ÿi Ä‘á»™ng â€” vui lÃ²ng chá» server online.", ephemeral=True)
                else:
                    await interaction.followup.send("âŒ KhÃ´ng thá»ƒ khá»Ÿi Ä‘á»™ng server.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i START: {e}", ephemeral=True)

        @bot.tree.command(name="stop", description="Dá»«ng server an toÃ n (cáº£nh bÃ¡o 10s/5s, lÆ°u trÆ°á»›c khi táº¯t)")
        async def slash_stop(interaction: _discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                if not _app._is_server_running():
                    await interaction.followup.send("â„¹ï¸ Server Ä‘ang táº¯t.", ephemeral=True)
                    return
                threading.Thread(target=_app._stop_sequence_discord, args=("Discord",), daemon=True).start()
                await interaction.followup.send("ðŸ›‘ ÄÃ£ báº¯t Ä‘áº§u quy trÃ¬nh dá»«ng server (10s/5s) vÃ  lÆ°u dá»¯ liá»‡u.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i STOP: {e}", ephemeral=True)

        @bot.tree.command(name="reset", description="Reset server 30s nhÆ° giao diá»‡n Ä‘iá»u khiá»ƒn (cÃ³ cáº£nh bÃ¡o)")
        async def slash_reset(interaction: _discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            try:
                threading.Thread(target=_app.reset_sequence, daemon=True).start()
                await interaction.followup.send("ðŸ” ÄÃ£ báº¯t Ä‘áº§u quy trÃ¬nh RESET 30s (cáº£nh bÃ¡o + save).", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i RESET: {e}", ephemeral=True)

        @bot.tree.command(name="livemap", description="LiveMap: vá»‹ trÃ­ ngÆ°á»i chÆ¡i online (tá»a Ä‘á»™ X/Y + guild)")
        async def slash_livemap(interaction: _discord.Interaction, top: int = 25):
            await interaction.response.defer(ephemeral=True)
            try:
                # /livemap: táº¡o 1 card náº¿u chÆ°a cÃ³, sau Ä‘Ã³ chá»‰ edit card nÃ y Ä‘á»ƒ chá»‘ng spam.
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
                    "âœ… LiveMap card Ä‘Ã£ báº­t auto-refresh má»—i 10 giÃ¢y (anti-spam: chá»‰ edit 1 message).",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i LIVEMAP: {e}", ephemeral=True)

        def _is_discord_admin(interaction: _discord.Interaction) -> bool:
            try:
                perms = getattr(interaction.user, "guild_permissions", None)
                return bool(perms and (perms.administrator or perms.manage_guild))
            except Exception:
                return False

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # â”€â”€ Helper: build server-status embed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        async def _build_server_embed():
            """Táº¡o embed thÃ´ng tin server â€” dá»¯ liá»‡u live tá»« REST API."""
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
            description = info.get("description") or info.get("Description") or "Anh Em Bá»‘n PhÆ°Æ¡ng | MÃ¡y Chá»§ HÃ ng Äáº§u Viá»‡t NAm"
            world_guid  = info.get("worldguid")  or info.get("WorldGuid")  or "N/A"
            version     = info.get("version")    or info.get("Version")    or "N/A"

            cur_players = metrics.get("currentplayernum") or len(players)
            max_players = metrics.get("maxplayernum")     or _app._max_players or 2003
            days        = metrics.get("days", "?")
            fps         = round(metrics.get("serverfps", 0), 1) if metrics.get("serverfps") else "?"
            frame_time  = metrics.get("serverframetime", 0)
            latency_ms  = "?"
            if isinstance(frame_time, (int, float)) and frame_time > 0:
                # CÃ³ API tráº£ vá» giÃ¢y, cÃ³ API tráº£ vá» ms -> tá»± nháº­n diá»‡n Ä‘á»ƒ trÃ¡nh ping bá»‹ phÃ³ng Ä‘áº¡i.
                latency_val = frame_time * 1000 if frame_time <= 10 else frame_time
                latency_ms = f"{int(round(latency_val))} ms"
            uptime_sec  = metrics.get("uptime", 0)
            if isinstance(uptime_sec, (int, float)) and uptime_sec > 0:
                uptime_str = f"{int(uptime_sec // 3600)}h {int((uptime_sec % 3600) // 60)}m"
            else:
                uptime_str = "0 phÃºt"

            # Thanh % ngÆ°á»i chÆ¡i
            pct     = min(cur_players / max(max_players, 1), 1.0)
            filled  = round(pct * 12)
            pbar    = "â–ˆ" * filled + "â–‘" * (12 - filled)
            color   = 0x57F287 if cur_players > 0 else 0x5865F2
            is_online = bool(info_ok or metrics_ok or players_ok)
            status_text = "ðŸŸ¢ Online" if is_online else "ðŸ”´ Offline"

            now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            embed = _discord.Embed(
                title=f"ðŸŒ  {server_name}",
                description=f"```{description}```",
                color=color,
                timestamp=datetime.datetime.now(datetime.UTC)
            )
            embed.add_field(name="ðŸ‘¥ NgÆ°á»i chÆ¡i",   value=f"```{cur_players} / {max_players}\n{pbar} {pct*100:.0f}%```", inline=False)
            embed.add_field(name="ðŸ“¶ Tráº¡ng ThÃ¡i", value=f"```{status_text}```", inline=True)
            embed.add_field(name="ðŸ”– PhiÃªn báº£n",   value=f"```{version}```",        inline=True)
            embed.add_field(name="ðŸ“… Sá»‘ ngÃ y ingame",      value=f"```{days}```",           inline=True)
            embed.add_field(name="âš¡ FPS",       value=f"```{fps}```",            inline=True)
            embed.add_field(name="â±ï¸ Uptime",   value=f"```{uptime_str}```",     inline=True)
            embed.add_field(name="ðŸ“¡ Ping",      value=f"```{latency_ms}```",     inline=True)
            embed.add_field(name="ðŸ†” World GUID",value=f"```{world_guid}```",     inline=False)

            if players:
                def _fmt_ping(v):
                    try:
                        if v is None or v == "":
                            return "â€”"
                        val = float(v)
                        # Tá»± nháº­n diá»‡n Ä‘Æ¡n vá»‹ (s -> ms) Ä‘á»ƒ Ä‘á»“ng bá»™ vá»›i ping server.
                        if val <= 10:
                            val *= 1000
                        return f"{int(round(val))} ms"
                    except Exception:
                        return "â€”"
                rows = "\n".join(f"  {i:>2}. {p.get('name','?')[:24]} â€” {_fmt_ping(p.get('ping'))}"
                                 for i, p in enumerate(players[:20], 1))
                if len(players) > 20:
                    rows += f"\n  â€¦ vÃ  {len(players)-20} ngÆ°á»i khÃ¡c"
                embed.add_field(
                    name=f"ðŸŸ¢ Äang Online â€” {cur_players} ngÆ°á»i",
                    value=f"```{rows}```",
                    inline=False
                )
            else:
                embed.add_field(name="ðŸ”´ Server Ä‘ang trá»‘ng", value="```ChÆ°a cÃ³ ngÆ°á»i chÆ¡i nÃ o online```", inline=False)

            embed.set_footer(text=f"ðŸ”„ Tá»± Ä‘á»™ng cáº­p nháº­t â€¢  {now_str}")
            return embed

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # â”€â”€ Helper: build top-10 ranking embed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        def _build_ranking_embed():
            """Táº¡o embed top 10 level, live tá»« player_stats cache."""
            ranking = _app._get_ranking(10)
            total   = len([s for s in _app.player_stats.values()
                           if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])

            now_str  = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            MEDALS   = ["ðŸ¥‡", "ðŸ¥ˆ", "ðŸ¥‰"]
            LVL_ICON = {True: "ðŸ’Ž", False: None}   # placeholder

            embed = _discord.Embed(
                title="ðŸ†  Báº¢NG Xáº¾P Háº NG  â€”  TOP 10 LEVEL",
                color=0xFFD700,
                timestamp=datetime.datetime.now(datetime.UTC)
            )

            if not ranking:
                embed.description = "```ChÆ°a cÃ³ dá»¯ liá»‡u â€” Ä‘ang Ä‘á»“ng bá»™ tá»« server...```"
            else:
                max_level = max(p["level"] for p in ranking) or 1
                rows = ""
                for idx, p in enumerate(ranking, 1):
                    medal = MEDALS[idx-1] if idx <= 3 else f"` {idx:>2}.`"
                    name  = p["name"][:20]
                    lvl   = p["level"]
                    pal   = p["pal_count"]
                    ptime = _app._fmt_playtime(p.get("playtime_sec", 0))

                    # Progress bar 12 kÃ½ tá»±
                    filled = round((lvl / max_level) * 12)
                    bar    = "â–ˆ" * filled + "â–‘" * (12 - filled)

                    if   lvl >= 50: icon = "ðŸ’Ž"
                    elif lvl >= 30: icon = "ðŸ”¥"
                    elif lvl >= 15: icon = "â­"
                    else:           icon = "ðŸŒ±"

                    rows += f"{medal} **{name}**\n"
                    rows += f"    {icon} `Lv.{lvl:>3}`  `{bar}`  ðŸŽ£ `{pal:>4} Pal`  â± `{ptime}`\n\n"
                    if len(rows) > 3600:
                        rows += "â€¦\n"
                        break

                embed.add_field(name="ðŸ… Báº£ng Xáº¿p Háº¡ng", value=rows, inline=False)

                avg_lv  = sum(p["level"]     for p in ranking) / len(ranking)
                avg_pal = sum(p["pal_count"] for p in ranking) / len(ranking)
                top1    = ranking[0]["name"] if ranking else "â€”"
                embed.add_field(name="ðŸ‘‘ Sá»‘ 1",          value=f"```{top1}```",         inline=True)
                embed.add_field(name="ðŸ“ˆ Cáº¥p TB Top10",  value=f"```{avg_lv:.1f}```",   inline=True)
                embed.add_field(name="ðŸ‘¥ Tá»•ng Ä‘Ã£ chÆ¡i",  value=f"```{total}```",         inline=True)

            embed.set_footer(text=f"ðŸ”„ Tá»± Ä‘á»™ng cáº­p nháº­t  â€¢  {now_str}  â€¢  !stats [tÃªn] Ä‘á»ƒ xem chi tiáº¿t")
            return embed

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # â”€â”€ Discord UI Views vá»›i nÃºt Refresh â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        class ServerView(_discord.ui.View):
            """View gáº¯n vÃ o card server status â€” cÃ³ nÃºt ðŸ”„ LÃ m má»›i."""
            def __init__(self_v):
                super().__init__(timeout=None)

            @_discord.ui.button(
                label="ðŸ”„  LÃ m má»›i",
                style=_discord.ButtonStyle.blurple,
                custom_id="btn_sv_refresh"
            )
            async def do_refresh(self_v, interaction: _discord.Interaction,
                                 button: _discord.ui.Button):
                button.disabled = True
                button.label    = "â³  Äang cáº­p nháº­tâ€¦"
                await interaction.response.edit_message(view=self_v)
                try:
                    embed = await _build_server_embed()
                    new_view = ServerView()
                    await interaction.message.edit(embed=embed, view=new_view)
                except Exception as exc:
                    button.disabled = False
                    button.label    = "ðŸ”„  LÃ m má»›i"
                    await interaction.message.edit(view=self_v)

        class RankingView(_discord.ui.View):
            """View gáº¯n vÃ o card ranking â€” cÃ³ nÃºt ðŸ”„ LÃ m má»›i + ðŸ“Š Top 20."""
            def __init__(self_v):
                super().__init__(timeout=None)

            @_discord.ui.button(
                label="ðŸ”„  LÃ m má»›i",
                style=_discord.ButtonStyle.blurple,
                custom_id="btn_rk_refresh"
            )
            async def do_refresh(self_v, interaction: _discord.Interaction,
                                 button: _discord.ui.Button):
                button.disabled = True
                button.label    = "â³  Äang cáº­p nháº­tâ€¦"
                await interaction.response.edit_message(view=self_v)
                try:
                    # Sync levels tá»« API trÆ°á»›c khi build embed
                    _loop = asyncio.get_event_loop()
                    await _loop.run_in_executor(None, _app._update_player_levels)
                    embed = _build_ranking_embed()
                    new_view = RankingView()
                    await interaction.message.edit(embed=embed, view=new_view)
                except Exception as exc:
                    button.disabled = False
                    button.label    = "ðŸ”„  LÃ m má»›i"
                    await interaction.message.edit(view=self_v)

            @_discord.ui.button(
                label="ðŸ“Š  Top 20",
                style=_discord.ButtonStyle.secondary,
                custom_id="btn_rk_top20"
            )
            async def show_top20(self_v, interaction: _discord.Interaction,
                                 button: _discord.ui.Button):
                await interaction.response.defer(ephemeral=True)
                try:
                    r20 = _app._get_ranking(20)
                    if not r20:
                        await interaction.followup.send("ðŸ“Š ChÆ°a cÃ³ dá»¯ liá»‡u.", ephemeral=True)
                        return
                    MEDALS2 = ["ðŸ¥‡", "ðŸ¥ˆ", "ðŸ¥‰"]
                    lines = []
                    for i, p in enumerate(r20, 1):
                        m = MEDALS2[i-1] if i <= 3 else f"`{i:>2}.`"
                        lines.append(f"{m} **{p['name'][:20]}** â€” Lv.`{p['level']}` | ðŸŽ£`{p['pal_count']}`")
                    e = _discord.Embed(
                        title="ðŸ“Š Top 20 Level",
                        description="\n".join(lines),
                        color=0x00ff88,
                        timestamp=datetime.datetime.utcnow()
                    )
                    await interaction.followup.send(embed=e, ephemeral=True)
                except Exception as exc:
                    await interaction.followup.send(f"âŒ Lá»—i: {exc}", ephemeral=True)

        class LiveMapView(_discord.ui.View):
            """View gáº¯n vÃ o card livemap â€” cÃ³ nÃºt ðŸ”„ LÃ m má»›i."""
            def __init__(self_v):
                super().__init__(timeout=None)

            @_discord.ui.button(
                label="ðŸ”„  LÃ m má»›i",
                style=_discord.ButtonStyle.blurple,
                custom_id="btn_lm_refresh"
            )
            async def do_refresh(self_v, interaction: _discord.Interaction,
                                 button: _discord.ui.Button):
                button.disabled = True
                button.label    = "â³  Äang cáº­p nháº­tâ€¦"
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

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # â”€â”€ Helper: upsert message (edit hoáº·c gá»­i má»›i + view) â”€â”€â”€â”€â”€
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        async def _upsert_message(channel, msg_id: int, embed, view=None,
                                  kind: str = ""):
            """Cháº¿ Ä‘á»™ anti-spam: chá»‰ EDIT tin nháº¯n Ä‘Ã£ cÃ³, khÃ´ng tá»± gá»­i má»›i.
            kind = 'server' | 'ranking' Ä‘á»ƒ phÃ¢n loáº¡i log náº¿u cáº§n.
            """
            if msg_id:
                try:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(embed=embed, view=view)
                    return msg_id
                except Exception:
                    # Tin nháº¯n bá»‹ xÃ³a / khÃ´ng cÃ²n quyá»n / sai channel -> reset ID.
                    return 0
            # KhÃ´ng cÃ³ msg_id: bá» qua Ä‘á»ƒ trÃ¡nh tá»± táº¡o thÃªm tin nháº¯n.
            return 0

        # â”€â”€ on_ready â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @bot.event
        async def on_ready():
            try:
                synced = await bot.tree.sync()
                self._enqueue_console(f"âœ… Discord Bot 2: ÄÃ£ sync {len(synced)} slash commands")
                # Sync nhanh theo guild hiá»‡n táº¡i Ä‘á»ƒ lá»‡nh má»›i hiá»‡n ngay (khÃ´ng pháº£i chá» global propagation).
                try:
                    ch = bot.get_channel(int(DISCORD_BOT2_CHANNEL_ID)) if str(DISCORD_BOT2_CHANNEL_ID).strip() else None
                    guild_obj = ch.guild if ch and getattr(ch, "guild", None) else None
                    if guild_obj:
                        bot.tree.copy_global_to(guild=guild_obj)
                        gsynced = await bot.tree.sync(guild=guild_obj)
                        self._enqueue_console(f"âœ… Discord Bot 2: Guild sync {len(gsynced)} lá»‡nh cho guild {guild_obj.id}")
                except Exception as ge:
                    self._enqueue_console(f"âš ï¸ Discord Bot 2: Guild sync lá»—i: {ge}")
            except Exception as e:
                self._enqueue_console(f"âš ï¸ Discord Bot 2: Lá»—i sync: {e}")

            self._discord_bot2_ok     = True
            self._discord_bot2_status = f"âœ… {bot.user.name} â€” ðŸŸ¢ Online"
            self._enqueue_console(f"âœ… Discord Bot 2 '{bot.user.name}' Ä‘Ã£ káº¿t ná»‘i â€” Online!")

            # ÄÄƒng kÃ½ persistent views Ä‘á»ƒ button hoáº¡t Ä‘á»™ng sau restart
            bot.add_view(ServerView())
            bot.add_view(RankingView())
            bot.add_view(LiveMapView())

            # â”€â”€ KhÃ´i phá»¥c message IDs sau restart â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # server card á»Ÿ kÃªnh lá»‡nh chÃ­nh, ranking card á»Ÿ kÃªnh ranking riÃªng.
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
                            self._enqueue_console(f"â™»ï¸ Bot2: TÃ¬m tháº¥y {kind} message #{mid} â€” sáº½ dÃ¹ng láº¡i")
                            return
                        except Exception:
                            setattr(self, attr, 0)
                            self._enqueue_console(f"âš ï¸ Bot2: {kind} message #{mid} khÃ´ng cÃ²n â€” sáº½ tÃ¬m láº¡i")

                    async for old_msg in ch.history(limit=100):
                        if old_msg.author.id != bot.user.id:
                            continue
                        if not old_msg.embeds:
                            continue
                        title = old_msg.embeds[0].title or ""
                        if title_mark in title:
                            setattr(self, attr, old_msg.id)
                            self._enqueue_console(f"â™»ï¸ Bot2: TÃ¬m tháº¥y {kind} card cÅ© #{old_msg.id} â€” dÃ¹ng láº¡i")
                            return

                await _restore_card(main_channel_id, "_bot2_status_msg_id", "server", "ðŸŒ")
                await _restore_card(ranking_channel_id, "_bot2_ranking_msg_id", "ranking", "ðŸ†")
                await _restore_card(main_channel_id, "_bot2_livemap_msg_id", "livemap", "ðŸ—ºï¸")
                self._save_bot2_msg_ids()
            except Exception as scan_err:
                self._enqueue_console(f"âš ï¸ Bot2: Lá»—i khi khÃ´i phá»¥c msg IDs: {scan_err}")

            if not task_update_server.is_running():
                task_update_server.start()
            if not task_update_ranking.is_running():
                task_update_ranking.start()
            if not task_update_livemap.is_running():
                task_update_livemap.start()

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # â”€â”€ Auto-update tasks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        from discord.ext import tasks as _tasks

        _last_level_sync = [0.0]   # dÃ¹ng list Ä‘á»ƒ mutate trong closure

        @_tasks.loop(seconds=10)
        async def task_update_server():
            """Cáº­p nháº­t card server status má»—i 10 giÃ¢y."""
            try:
                # Æ¯u tiÃªn kÃªnh mapping theo server profile active; fallback global.
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
                self._enqueue_console(f"âš ï¸ task_update_server: {exc}")

        @_tasks.loop(seconds=10)
        async def task_update_ranking():
            """Cáº­p nháº­t báº£ng xáº¿p háº¡ng má»—i 10 giÃ¢y.
            Level sync tá»« API má»—i 30 giÃ¢y Ä‘á»ƒ trÃ¡nh overload."""
            _, prof = _get_active_server_profile()
            ranking_channel_id = str(prof.get("ranking_channel_id", "") or DISCORD_BOT2_RANKING_CHANNEL_ID or DISCORD_BOT2_CHANNEL_ID).strip()
            if not ranking_channel_id:
                return
            try:
                channel = bot.get_channel(int(ranking_channel_id))
                if not channel:
                    return

                # Sync levels tá»« API má»—i 30 giÃ¢y
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
                self._enqueue_console(f"âš ï¸ task_update_ranking: {exc}")

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
                    title="ðŸ—ºï¸ LIVE MAP",
                    description=f"ðŸ‘¥ Online hiá»‡n táº¡i: **{len(players)}**",
                    color=0x00DDFF,
                    timestamp=datetime.datetime.now(datetime.UTC)
                )
                if not players:
                    emb.add_field(name="Tráº¡ng thÃ¡i", value="```ChÆ°a cÃ³ ngÆ°á»i chÆ¡i online```", inline=False)
                    return emb, ""
                rows = []
                gpm = getattr(_app, "_map_guild_player_map", {}) or {}
                lim = max(1, min(int(limit or 25), 50))
                for i, p in enumerate(players[:lim], 1):
                    name = str(p.get("name", "?"))[:20]
                    lv = p.get("level", "?")
                    lx = p.get("location_x")
                    ly = p.get("location_y")
                    guild = _app._lookup_guild(p, gpm) or "â€”"
                    if lx is not None and ly is not None:
                        mx = (float(ly) - 157664.55791065) / 462.962962963
                        my = (float(lx) + 123467.1611767) / 462.962962963
                        rows.append(f"{i:>2}. {name} | Lv.{lv} | {guild[:12]} | X:{mx:.0f} Y:{my:.0f}")
                    else:
                        rows.append(f"{i:>2}. {name} | Lv.{lv} | {guild[:12]} | X:â€” Y:â€”")
                if len(players) > lim:
                    rows.append(f"... vÃ  {len(players) - lim} ngÆ°á»i khÃ¡c")
                emb.add_field(
                    name=f"Danh sÃ¡ch (Top {lim})",
                    value=f"```{chr(10).join(rows)[:3900]}```",
                    inline=False
                )
                map_file = _app._render_discord_livemap_image(size=1024)
                if map_file:
                    emb.set_image(url="attachment://discord_livemap.png")
                emb.set_footer(text="Tá»± Ä‘á»™ng cáº­p nháº­t má»—i 10 giÃ¢y â€¢ LiveMap áº£nh + tá»a Ä‘á»™")
                return emb, map_file
            except Exception as e:
                return _discord.Embed(title="ðŸ—ºï¸ LIVE MAP", description=f"âŒ Lá»—i: {e}", color=0xED4245), ""

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
            """Cáº­p nháº­t LiveMap card má»—i 10 giÃ¢y (edit tin nháº¯n cÅ©, trÃ¡nh spam)."""
            try:
                # Æ¯u tiÃªn kÃªnh status cá»§a profile; fallback livemap channel id; cuá»‘i cÃ¹ng dÃ¹ng DISCORD_BOT2_CHANNEL_ID
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
                self._enqueue_console(f"âš ï¸ task_update_livemap: {exc}")

        @task_update_server.before_loop
        @task_update_ranking.before_loop
        @task_update_livemap.before_loop
        async def before_tasks():
            await bot.wait_until_ready()
            await asyncio.sleep(3)   # Chá» 3 giÃ¢y sau ready má»›i báº¯t Ä‘áº§u

        @bot.event
        async def on_disconnect():
            self._discord_bot2_ok = False
            self._discord_bot2_status = "âš ï¸ Máº¥t káº¿t ná»‘i â€” Ä‘ang reconnect..."

        @bot.event
        async def on_resumed():
            self._discord_bot2_ok = True
            self._discord_bot2_status = f"âœ… ÄÃ£ reconnect â€” ðŸŸ¢ Online"

        # â”€â”€ Commands â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @bot.command(name='refresh', aliases=['update', 'capnhat', 'r'])
        async def cmd_refresh(ctx):
            """Cáº­p nháº­t ngay server status + ranking board.
            Usage: !refresh
            """
            msg = await ctx.send("â³ Äang cáº­p nháº­t server status vÃ  báº£ng xáº¿p háº¡ng...")
            try:
                server_channel = bot.get_channel(int(DISCORD_BOT2_CHANNEL_ID)) if DISCORD_BOT2_CHANNEL_ID else ctx.channel
                if not server_channel:
                    server_channel = ctx.channel
                _, prof = _get_active_server_profile()
                ranking_channel_id = str(prof.get("ranking_channel_id", "") or DISCORD_BOT2_RANKING_CHANNEL_ID or DISCORD_BOT2_CHANNEL_ID).strip()
                ranking_channel = bot.get_channel(int(ranking_channel_id)) if ranking_channel_id else server_channel
                if not ranking_channel:
                    ranking_channel = server_channel

                # Sync levels tá»« API
                await asyncio.get_event_loop().run_in_executor(None, self._update_player_levels)
                _last_level_sync[0] = time.time()

                # Upsert server status vá»›i ServerView
                sv_embed = await _build_server_embed()
                self._bot2_status_msg_id = await _upsert_message(
                    server_channel, self._bot2_status_msg_id, sv_embed, ServerView(),
                    kind="server"
                )

                # Upsert ranking vá»›i RankingView
                rk_embed = _build_ranking_embed()
                self._bot2_ranking_msg_id = await _upsert_message(
                    ranking_channel, self._bot2_ranking_msg_id, rk_embed, RankingView(),
                    kind="ranking"
                )
                self._save_bot2_msg_ids()
                if self._bot2_status_msg_id and self._bot2_ranking_msg_id:
                    await msg.edit(content="âœ… ÄÃ£ lÃ m má»›i server status + báº£ng xáº¿p háº¡ng (cháº¿ Ä‘á»™ anti-spam: chá»‰ edit).")
                else:
                    await msg.edit(
                        content=("âš ï¸ ChÆ°a cÃ³ message cá»‘ Ä‘á»‹nh Ä‘á»ƒ edit.\n"
                                 "Admin hÃ£y gá»­i sáºµn card cá»§a bot (hoáº·c Ä‘á»ƒ bot cÃ³ card cÅ©), "
                                 "sau Ä‘Ã³ lÆ°u Ä‘Ãºng message ID Ä‘á»ƒ bot chá»‰ tá»± Ä‘á»™ng lÃ m má»›i.")
                    )
                await asyncio.sleep(3)
                try:
                    await msg.delete()
                except Exception:
                    pass
            except Exception as e:
                await msg.edit(content=f"âŒ Lá»—i: {e}")

        @bot.command(name='ranking', aliases=['rank', 'top', 'leaderboard', 'xephang'])
        async def cmd_ranking(ctx, top: int = 10):
            """Hiá»ƒn thá»‹ báº£ng xáº¿p háº¡ng ngÆ°á»i chÆ¡i.
            Usage: !ranking [sá»‘ lÆ°á»£ng] (máº·c Ä‘á»‹nh: 10, tá»‘i Ä‘a 20)
            """
            try:
                ranking = self._get_ranking(min(top, 20))  # Tá»‘i Ä‘a 20
                
                if not ranking:
                    await ctx.send("ðŸ“Š ChÆ°a cÃ³ dá»¯ liá»‡u xáº¿p háº¡ng.")
                    return

                # TÃ­nh tá»•ng sá»‘ ngÆ°á»i chÆ¡i cÃ³ dá»¯ liá»‡u
                total_players = len([s for s in self.player_stats.values() 
                                   if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])

                # Táº¡o embed Ä‘áº¹p vÃ  chuyÃªn nghiá»‡p
                embed = _discord.Embed(
                    title="ðŸ† Báº¢NG Xáº¾P Háº NG NGÆ¯á»œI CHÆ I",
                    description=f"ðŸ“Š **Top {len(ranking)} ngÆ°á»i chÆ¡i**\nðŸ‘¥ Tá»•ng sá»‘ ngÆ°á»i chÆ¡i cÃ³ dá»¯ liá»‡u: **{total_players}**",
                    color=0x00ff88
                )

                medals = ["ðŸ¥‡", "ðŸ¥ˆ", "ðŸ¥‰"]
                level_icons = ["â­", "ðŸŒŸ", "ðŸ’«"]
                ranking_text = ""
                
                for idx, player in enumerate(ranking, 1):
                    medal = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
                    name = player["name"][:18]
                    level = player["level"]
                    pal_count = player["pal_count"]
                    playtime = self._fmt_playtime(player.get("playtime_sec", 0))
                    
                    # Icon level theo cáº¥p Ä‘á»™
                    if level >= 50:
                        level_icon = level_icons[2]
                    elif level >= 30:
                        level_icon = level_icons[1]
                    else:
                        level_icon = level_icons[0]
                    
                    ranking_text += f"{medal} **{name}**\n"
                    ranking_text += f"   {level_icon} Cáº¥p: `{level:3d}` | ðŸŽ£ Pal: `{pal_count:4d}` | â± `{playtime}`\n\n"
                    if len(ranking_text) > 1800:  # Discord limit
                        break

                embed.add_field(
                    name="ðŸ… TOP NGÆ¯á»œI CHÆ I HÃ€NG Äáº¦U",
                    value=ranking_text or "ChÆ°a cÃ³ dá»¯ liá»‡u",
                    inline=False
                )
                
                # ThÃªm thá»‘ng kÃª tá»•ng quan
                if ranking:
                    avg_level = sum(p["level"] for p in ranking) / len(ranking)
                    avg_pals = sum(p["pal_count"] for p in ranking) / len(ranking)
                    max_level = max(p["level"] for p in ranking)
                    max_pals = max(p["pal_count"] for p in ranking)
                    
                    stats_text = (
                        f"ðŸ“ˆ **Cáº¥p Ä‘á»™ trung bÃ¬nh:** `{avg_level:.1f}`\n"
                        f"ðŸŽ£ **Pal trung bÃ¬nh:** `{avg_pals:.1f}`\n"
                        f"ðŸ”¥ **Cáº¥p cao nháº¥t:** `{max_level}`\n"
                        f"ðŸ’Ž **Nhiá»u Pal nháº¥t:** `{max_pals}`"
                    )
                    
                    embed.add_field(
                        name="ðŸ“Š THá»NG KÃŠ Tá»”NG QUAN",
                        value=stats_text,
                        inline=False
                    )
                
                embed.set_footer(text=f"Palworld Server Ranking â€¢ {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"âŒ Lá»—i: {str(e)}")

        @bot.command(name='stats', aliases=['stat', 'player', 'thongke'])
        async def cmd_stats(ctx, *, player_name: str = None):
            """Xem thá»‘ng kÃª cá»§a ngÆ°á»i chÆ¡i.
            Usage: !stats [tÃªn ngÆ°á»i chÆ¡i]
            """
            try:
                if not player_name:
                    await ctx.send("âŒ Vui lÃ²ng nháº­p tÃªn ngÆ°á»i chÆ¡i: `!stats [tÃªn]`\n"
                                 "ðŸ’¡ VÃ­ dá»¥: `!stats MityTin`")
                    return

                # TÃ¬m player trong stats (tÃ¬m chÃ­nh xÃ¡c hoáº·c gáº§n Ä‘Ãºng)
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
                    await ctx.send(f"âŒ KhÃ´ng tÃ¬m tháº¥y ngÆ°á»i chÆ¡i: `{player_name}`\n"
                                 f"ðŸ’¡ Thá»­ tÃ¬m kiáº¿m: `!search {player_name}`")
                    return

                # TÃ­nh ranking
                ranking = self._get_ranking(1000)  # Láº¥y táº¥t cáº£ Ä‘á»ƒ tÃ¬m vá»‹ trÃ­
                rank_pos = None
                for idx, p in enumerate(ranking, 1):
                    if p.get("steamid") == found.get("steamid"):
                        rank_pos = idx
                        break

                embed = _discord.Embed(
                    title=f"ðŸ“Š Thá»‘ng kÃª: {found['name']}",
                    description=f"ðŸ† **Vá»‹ trÃ­ xáº¿p háº¡ng:** #{rank_pos if rank_pos else 'N/A'}",
                    color=0x00aaff
                )
                embed.add_field(name="â­ Cáº¥p Ä‘á»™", value=f"`{found.get('level', 0)}`", inline=True)
                embed.add_field(name="ðŸŽ£ Pal Ä‘Ã£ báº¯t", value=f"`{found.get('pal_count', 0)}`", inline=True)
                embed.add_field(
                    name="â± Thá»i lÆ°á»£ng chÆ¡i",
                    value=f"`{self._fmt_playtime(self._player_total_playtime_sec(found.get('steamid', '')) )}`",
                    inline=True
                )
                
                # ThÃªm thÃ´ng tin SteamID (áº©n má»™t pháº§n)
                steamid = found.get('steamid', '')
                if steamid:
                    steamid_display = steamid[:10] + "..." if len(steamid) > 10 else steamid
                    embed.add_field(name="ðŸ†” SteamID", value=f"`{steamid_display}`", inline=True)
                
                last_update = found.get('last_update', 0)
                if last_update:
                    last_update_str = datetime.datetime.fromtimestamp(last_update).strftime('%d/%m/%Y %H:%M:%S')
                    embed.add_field(name="ðŸ• Cáº­p nháº­t láº§n cuá»‘i", value=last_update_str, inline=False)
                
                embed.set_footer(text="Palworld Server Bot")
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"âŒ Lá»—i: {str(e)}")

        @bot.command(name='server', aliases=['info', 'serverinfo', 'serverstatus'])
        async def cmd_server(ctx):
            """Xem thÃ´ng tin server.
            Usage: !server
            """
            try:
                res = requests.get(f"{API_URL}/info", auth=AUTH, timeout=5)
                if res.status_code != 200:
                    await ctx.send("âŒ KhÃ´ng thá»ƒ láº¥y thÃ´ng tin server.")
                    return

                info = res.json()
                players_res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                players = []
                if players_res.status_code == 200:
                    players = players_res.json().get("players", [])

                # TÃ­nh thá»‘ng kÃª ngÆ°á»i chÆ¡i
                total_stats_players = len([s for s in self.player_stats.values() 
                                         if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])

                embed = _discord.Embed(
                    title="ðŸ–¥ï¸ THÃ”NG TIN SERVER PALWORLD",
                    description="ðŸ“Š ThÃ´ng tin chi tiáº¿t vá» server",
                    color=0x00aaff
                )
                embed.add_field(name="ðŸ‘¥ NgÆ°á»i chÆ¡i online", value=f"`{len(players)}/{self._max_players}`", inline=True)
                embed.add_field(name="ðŸŒ Version", value=f"`{info.get('version', 'N/A')}`", inline=True)
                embed.add_field(name="ðŸ“Š Uptime", value=f"`{info.get('uptime', 'N/A')}`", inline=True)
                embed.add_field(name="ðŸ“ˆ Tá»•ng ngÆ°á»i chÆ¡i cÃ³ dá»¯ liá»‡u", value=f"`{total_stats_players}`", inline=True)
                
                if players:
                    player_list = ", ".join([p.get("name", "Unknown")[:15] for p in players[:10]])
                    if len(players) > 10:
                        player_list += f" ... vÃ  {len(players) - 10} ngÆ°á»i khÃ¡c"
                    embed.add_field(name="ðŸ‘¤ NgÆ°á»i chÆ¡i Ä‘ang online", value=player_list or "KhÃ´ng cÃ³", inline=False)
                else:
                    embed.add_field(name="ðŸ‘¤ NgÆ°á»i chÆ¡i Ä‘ang online", value="KhÃ´ng cÃ³ ngÆ°á»i chÆ¡i nÃ o", inline=False)

                embed.set_footer(text=f"Cáº­p nháº­t: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"âŒ Lá»—i: {str(e)}")

        @bot.command(name='online', aliases=['players', 'danhsach'])
        async def cmd_online(ctx):
            """Xem danh sÃ¡ch ngÆ°á»i chÆ¡i Ä‘ang online.
            Usage: !online
            """
            try:
                players_res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                if players_res.status_code != 200:
                    await ctx.send("âŒ KhÃ´ng thá»ƒ láº¥y danh sÃ¡ch ngÆ°á»i chÆ¡i.")
                    return

                players = players_res.json().get("players", [])
                
                if not players:
                    await ctx.send("ðŸ‘¤ **KhÃ´ng cÃ³ ngÆ°á»i chÆ¡i nÃ o Ä‘ang online.**")
                    return

                embed = _discord.Embed(
                    title=f"ðŸ‘¥ NGÆ¯á»œI CHÆ I ÄANG ONLINE ({len(players)})",
                    color=0x00ff88
                )

                # Chia thÃ nh cÃ¡c field náº¿u quÃ¡ nhiá»u
                player_text = ""
                for idx, p in enumerate(players, 1):
                    name = p.get("name", "Unknown")
                    playerid = p.get("playerId", "")[:8] + "..." if p.get("playerId") else "N/A"
                    player_text += f"**{idx}.** {name}\n"
                    if len(player_text) > 900:  # Giá»›i háº¡n Ä‘á»™ dÃ i
                        player_text += f"... vÃ  {len(players) - idx} ngÆ°á»i khÃ¡c"
                        break

                embed.add_field(name="ðŸ“‹ Danh sÃ¡ch", value=player_text or "KhÃ´ng cÃ³", inline=False)
                embed.set_footer(text=f"Tá»•ng: {len(players)}/{self._max_players} ngÆ°á»i chÆ¡i")
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"âŒ Lá»—i: {str(e)}")

        @bot.command(name='search', aliases=['tim', 'find'])
        async def cmd_search(ctx, *, query: str = None):
            """TÃ¬m kiáº¿m ngÆ°á»i chÆ¡i theo tÃªn.
            Usage: !search [tá»« khÃ³a]
            """
            try:
                if not query:
                    await ctx.send("âŒ Vui lÃ²ng nháº­p tá»« khÃ³a tÃ¬m kiáº¿m: `!search [tÃªn]`")
                    return

                query_lower = query.lower()
                matches = []
                
                for steamid, stats in self.player_stats.items():
                    name = stats.get("name", "").lower()
                    if query_lower in name:
                        matches.append({"steamid": steamid, **stats})
                        if len(matches) >= 10:  # Giá»›i háº¡n 10 káº¿t quáº£
                            break

                if not matches:
                    await ctx.send(f"âŒ KhÃ´ng tÃ¬m tháº¥y ngÆ°á»i chÆ¡i nÃ o vá»›i tá»« khÃ³a: `{query}`")
                    return

                embed = _discord.Embed(
                    title=f"ðŸ” Káº¾T QUáº¢ TÃŒM KIáº¾M: '{query}'",
                    description=f"TÃ¬m tháº¥y **{len(matches)}** káº¿t quáº£:",
                    color=0x00aaff
                )

                result_text = ""
                for idx, match in enumerate(matches, 1):
                    name = match.get("name", "Unknown")
                    level = match.get("level", 0)
                    pal_count = match.get("pal_count", 0)
                    result_text += f"**{idx}.** {name} - â­{level} | ðŸŽ£{pal_count}\n"

                embed.add_field(name="ðŸ“‹ Káº¿t quáº£", value=result_text, inline=False)
                embed.set_footer(text="Sá»­ dá»¥ng !stats [tÃªn] Ä‘á»ƒ xem chi tiáº¿t")
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"âŒ Lá»—i: {str(e)}")

        @bot.command(name='help', aliases=['h', 'commands', 'trogiup'])
        async def cmd_help(ctx):
            """Hiá»ƒn thá»‹ danh sÃ¡ch commands.
            Usage: !help
            """
            embed = _discord.Embed(
                title="ðŸ¤– DANH SÃCH COMMANDS",
                description="CÃ¡c lá»‡nh cÃ³ sáºµn cho bot Palworld Server:",
                color=0x00ff88
            )
            embed.add_field(
                name="ðŸ“Š Xáº¿p háº¡ng",
                value="`!ranking [sá»‘]` - Xem báº£ng xáº¿p háº¡ng (máº·c Ä‘á»‹nh top 10, tá»‘i Ä‘a 20)\n"
                      "`!rank`, `!top`, `!xephang` - TÆ°Æ¡ng tá»±",
                inline=False
            )
            embed.add_field(
                name="ðŸ“ˆ Thá»‘ng kÃª",
                value="`!stats [tÃªn]` - Xem thá»‘ng kÃª ngÆ°á»i chÆ¡i\n"
                      "`!stat`, `!player`, `!thongke` - TÆ°Æ¡ng tá»±",
                inline=False
            )
            embed.add_field(
                name="ðŸ” TÃ¬m kiáº¿m",
                value="`!search [tá»« khÃ³a]` - TÃ¬m kiáº¿m ngÆ°á»i chÆ¡i\n"
                      "`!tim`, `!find` - TÆ°Æ¡ng tá»±",
                inline=False
            )
            embed.add_field(
                name="ðŸ–¥ï¸ Server",
                value="`!server` - Xem thÃ´ng tin server\n"
                      "`!info`, `!serverinfo`, `!serverstatus` - TÆ°Æ¡ng tá»±",
                inline=False
            )
            embed.add_field(
                name="ðŸ‘¥ NgÆ°á»i chÆ¡i",
                value="`!online` - Xem danh sÃ¡ch ngÆ°á»i chÆ¡i Ä‘ang online\n"
                      "`!players`, `!danhsach` - TÆ°Æ¡ng tá»±",
                inline=False
            )
            embed.add_field(
                name="ðŸ”„ Cáº­p nháº­t",
                value="`!refresh` - Cáº­p nháº­t ngay server status + ranking board\n"
                      "`!update`, `!capnhat`, `!r` - TÆ°Æ¡ng tá»±",
                inline=False
            )
            embed.add_field(
                name="â“ Trá»£ giÃºp",
                value="`!help` - Hiá»ƒn thá»‹ danh sÃ¡ch commands nÃ y",
                inline=False
            )
            embed.set_footer(text="Cá» HÃ³ Bot  â€¢  Auto-update má»—i 3 phÃºt  â€¢  !refresh Ä‘á»ƒ cáº­p nháº­t ngay")
            
            await ctx.send(embed=embed)

        # â”€â”€ Slash Commands (hiá»‡n Ä‘áº¡i hÆ¡n) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        @bot.tree.command(name="ranking", description="Xem báº£ng xáº¿p háº¡ng ngÆ°á»i chÆ¡i")
        async def slash_ranking(interaction: _discord.Interaction, top: int = 10):
            """Slash command: Xem báº£ng xáº¿p háº¡ng."""
            await interaction.response.defer()
            try:
                ranking = self._get_ranking(min(top, 20))
                if not ranking:
                    await interaction.followup.send("ðŸ“Š ChÆ°a cÃ³ dá»¯ liá»‡u xáº¿p háº¡ng.")
                    return

                total_players = len([s for s in self.player_stats.values() 
                                   if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])

                embed = _discord.Embed(
                    title="ðŸ† Báº¢NG Xáº¾P Háº NG NGÆ¯á»œI CHÆ I",
                    description=f"ðŸ“Š **Top {len(ranking)} ngÆ°á»i chÆ¡i**\nðŸ‘¥ Tá»•ng: **{total_players}**",
                    color=0x00ff88
                )

                medals = ["ðŸ¥‡", "ðŸ¥ˆ", "ðŸ¥‰"]
                ranking_text = ""
                for idx, player in enumerate(ranking[:10], 1):
                    medal = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
                    name = player["name"][:18]
                    level = player["level"]
                    pal_count = player["pal_count"]
                    ranking_text += f"{medal} **{name}** - â­{level} | ðŸŽ£{pal_count}\n"

                embed.add_field(name="ðŸ… TOP 10", value=ranking_text, inline=False)
                embed.set_footer(text=f"Cáº­p nháº­t: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
                await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i: {str(e)}")

        @bot.tree.command(name="stats", description="Xem thá»‘ng kÃª ngÆ°á»i chÆ¡i")
        async def slash_stats(interaction: _discord.Interaction, player_name: str):
            """Slash command: Xem thá»‘ng kÃª ngÆ°á»i chÆ¡i."""
            await interaction.response.defer()
            try:
                found = None
                for steamid, stats in self.player_stats.items():
                    if player_name.lower() in stats.get("name", "").lower():
                        found = {"steamid": steamid, **stats}
                        break

                if not found:
                    await interaction.followup.send(f"âŒ KhÃ´ng tÃ¬m tháº¥y: `{player_name}`")
                    return

                embed = _discord.Embed(title=f"ðŸ“Š {found['name']}", color=0x00aaff)
                embed.add_field(name="â­ Cáº¥p Ä‘á»™", value=f"`{found.get('level', 0)}`", inline=True)
                embed.add_field(name="ðŸŽ£ Pal Ä‘Ã£ báº¯t", value=f"`{found.get('pal_count', 0)}`", inline=True)
                await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i: {str(e)}")

        @bot.tree.command(name="server", description="Xem thÃ´ng tin server")
        async def slash_server(interaction: _discord.Interaction):
            """Slash command: Xem thÃ´ng tin server."""
            await interaction.response.defer()
            try:
                res = requests.get(f"{API_URL}/info", auth=AUTH, timeout=5)
                players_res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
                players = players_res.json().get("players", []) if players_res.status_code == 200 else []

                embed = _discord.Embed(title="ðŸ–¥ï¸ THÃ”NG TIN SERVER", color=0x00aaff)
                embed.add_field(name="ðŸ‘¥ Online", value=f"`{len(players)}/{self._max_players}`", inline=True)
                embed.add_field(name="ðŸŒ Version", value=f"`{res.json().get('version', 'N/A') if res.status_code == 200 else 'N/A'}`", inline=True)
                await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i: {str(e)}")

        @bot.tree.command(name="createserver", description="(Admin) ThÃªm/cáº­p nháº­t server profile Ä‘á»ƒ bot quáº£n lÃ½")
        @_discord.app_commands.describe(
            name="TÃªn server (vÃ­ dá»¥: Manager ServerPal)",
            ip_public="IP Public (mÃ¡y chá»§ public)",
            game_port="Cá»•ng Game (vd 8211)",
            rcon_port="Cá»•ng RCON (vd 25575)",
            restapi_port="Cá»•ng REST API (vd 8212)",
            paldefender_port="Cá»•ng PalDefender REST (vd 17993)",
            admin_password="AdminPassword dÃ¹ng chung cho RCON/REST"
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
                await interaction.response.send_message("âŒ Chá»‰ admin Discord má»›i Ä‘Æ°á»£c setup server.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                s_name = (name or "").strip()
                if not s_name:
                    await interaction.followup.send("âŒ TÃªn server khÃ´ng há»£p lá»‡.", ephemeral=True)
                    return
                if not ip_public.strip():
                    await interaction.followup.send("âŒ IP public khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.", ephemeral=True)
                    return
                for p in (game_port, rcon_port, restapi_port, paldefender_port):
                    if p <= 0 or p > 65535:
                        await interaction.followup.send(f"âŒ Port khÃ´ng há»£p lá»‡: {p}", ephemeral=True)
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
                    self._enqueue_console(f"âœ… Bot2 setup server profile: {s_name} ({ip_public}:{game_port})")
                    await interaction.followup.send(
                        f"âœ… ÄÃ£ lÆ°u server `{s_name}`\n"
                        f"â€¢ IP Public: `{ip_public}`\n"
                        f"â€¢ Game: `{game_port}` | RCON: `{rcon_port}` | REST: `{restapi_port}` | PD: `{paldefender_port}`\n"
                        f"â€¢ Tráº¡ng thÃ¡i: Ä‘áº·t lÃ m server active",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send("âŒ KhÃ´ng lÆ°u Ä‘Æ°á»£c server profile.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i /createserver: {e}", ephemeral=True)

        @bot.tree.command(name="delserver", description="(Admin) XÃ³a server profile theo tÃªn")
        @_discord.app_commands.describe(name="TÃªn server (vÃ­ dá»¥: Manager ServerPal)")
        async def slash_del_server(interaction: _discord.Interaction, name: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("âŒ Chá»‰ admin Discord má»›i Ä‘Æ°á»£c xÃ³a server.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                s_name = (name or "").strip()
                cfg = _read_manager_cfg() or {}
                servers = cfg.get("DISCORD_SERVER_PROFILES", {})
                if not isinstance(servers, dict) or s_name not in servers:
                    await interaction.followup.send(f"â„¹ï¸ KhÃ´ng tÃ¬m tháº¥y server `{s_name}`.", ephemeral=True)
                    return
                servers.pop(s_name, None)
                cfg["DISCORD_SERVER_PROFILES"] = servers
                if cfg.get("DISCORD_SERVER_ACTIVE") == s_name:
                    cfg["DISCORD_SERVER_ACTIVE"] = next(iter(servers.keys()), "")
                if _save_manager_cfg(cfg):
                    self._enqueue_console(f"ðŸ—‘ï¸ Bot2 xÃ³a server profile: {s_name}")
                    await interaction.followup.send(f"âœ… ÄÃ£ xÃ³a server `{s_name}`.", ephemeral=True)
                else:
                    await interaction.followup.send("âŒ KhÃ´ng lÆ°u Ä‘Æ°á»£c sau khi xÃ³a server.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i /delserver: {e}", ephemeral=True)

        @bot.tree.command(name="listservers", description="(Admin) Xem danh sÃ¡ch server profile Ä‘Ã£ lÆ°u")
        async def slash_list_servers(interaction: _discord.Interaction):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("âŒ Chá»‰ admin Discord má»›i Ä‘Æ°á»£c xem danh sÃ¡ch setup.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                cfg = _read_manager_cfg() or {}
                servers = cfg.get("DISCORD_SERVER_PROFILES", {})
                active = str(cfg.get("DISCORD_SERVER_ACTIVE", "") or "")
                if not isinstance(servers, dict) or not servers:
                    await interaction.followup.send("â„¹ï¸ ChÆ°a cÃ³ server profile nÃ o. DÃ¹ng `/createserver` Ä‘á»ƒ thÃªm má»›i.", ephemeral=True)
                    return
                lines = []
                for s_name, s in servers.items():
                    marker = "â­" if s_name == active else "â€¢"
                    lines.append(
                        f"{marker} **{s_name}** â€” `{s.get('ip_public','?')}:{s.get('game_port','?')}` "
                        f"(RCON `{s.get('rcon_port','?')}`, REST `{s.get('restapi_port','?')}`, PD `{s.get('paldefender_port','?')}`)"
                    )
                await interaction.followup.send(
                    "Danh sÃ¡ch server profile (â­ = Ä‘ang active):\n" + "\n".join(lines[:20]),
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(f"âŒ Lá»—i /listservers: {e}", ephemeral=True)

        # [Deprecated] áº¨n lá»‡nh Ä‘Æ¡n láº» â€” Ä‘Ã£ thay báº±ng /query setchannel
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

        # â”€â”€ Query group commands: /query setchannel ... â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            description="Quáº£n lÃ½ kÃªnh hiá»ƒn thá»‹ card (START/STATUS & Xáº¾P Háº NG) cho tá»«ng server"
        )

        async def _ensure_status_card_in_channel(target_channel):
            """Äáº£m báº£o cÃ³ status card trong kÃªnh Ä‘Ã­ch; chá»‰ táº¡o khi admin gá»i lá»‡nh setup."""
            # 1) Náº¿u Ä‘ang cÃ³ message id há»£p lá»‡ thÃ¬ Æ°u tiÃªn edit.
            if self._bot2_status_msg_id:
                try:
                    msg_old = await target_channel.fetch_message(self._bot2_status_msg_id)
                    await msg_old.edit(embed=await _build_server_embed(), view=ServerView())
                    return msg_old.id
                except Exception:
                    pass
            # 2) KhÃ´ng cÃ³/khÃ´ng há»£p lá»‡ -> táº¡o má»›i 1 láº§n theo lá»‡nh admin.
            msg_new = await target_channel.send(embed=await _build_server_embed(), view=ServerView())
            self._bot2_status_msg_id = msg_new.id
            self._save_bot2_msg_ids()
            return msg_new.id

        async def _ensure_ranking_card_in_channel(target_channel):
            """Äáº£m báº£o cÃ³ ranking card trong kÃªnh Ä‘Ã­ch; chá»‰ táº¡o khi admin gá»i lá»‡nh setup."""
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

        @query_group.command(name="setchannel", description="(Admin) GÃ¡n kÃªnh START/STATUS cho 1 server")
        @_discord.app_commands.describe(channel="KÃªnh nháº­n card status", server="TÃªn server profile")
        @_discord.app_commands.autocomplete(server=_server_name_autocomplete)
        async def query_setchannel(interaction: _discord.Interaction, channel: _discord.TextChannel, server: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("âŒ Chá»‰ admin Ä‘Æ°á»£c phÃ©p cáº¥u hÃ¬nh.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            cfg = _read_manager_cfg() or {}
            servers = cfg.get("DISCORD_SERVER_PROFILES", {})
            if not isinstance(servers, dict) or server not in servers:
                await interaction.followup.send(f"âŒ KhÃ´ng tÃ¬m tháº¥y server `{server}`.", ephemeral=True)
                return
            servers[server]["status_channel_id"] = str(channel.id)
            cfg["DISCORD_SERVER_PROFILES"] = servers
            if _save_manager_cfg(cfg):
                try:
                    msg_id = await _ensure_status_card_in_channel(channel)
                    await interaction.followup.send(
                        f"âœ… ÄÃ£ gÃ¡n kÃªnh START/STATUS <#{channel.id}> cho server `{server}`.\n"
                        f"ðŸ§© Status card: `msg_id={msg_id}` (tá»« giá» chá»‰ edit, khÃ´ng tá»± gá»­i má»›i).",
                        ephemeral=True
                    )
                except Exception as e:
                    await interaction.followup.send(
                        f"âš ï¸ ÄÃ£ lÆ°u mapping nhÆ°ng chÆ°a táº¡o/Ä‘á»“ng bá»™ status card: {e}",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send("âŒ KhÃ´ng lÆ°u Ä‘Æ°á»£c cáº¥u hÃ¬nh.", ephemeral=True)

        @query_group.command(name="removechannel", description="(Admin) Há»§y gÃ¡n kÃªnh START/STATUS cá»§a 1 server")
        @_discord.app_commands.describe(server="TÃªn server profile cáº§n há»§y")
        @_discord.app_commands.autocomplete(server=_server_name_autocomplete)
        async def query_removechannel(interaction: _discord.Interaction, server: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("âŒ Chá»‰ admin Ä‘Æ°á»£c phÃ©p cáº¥u hÃ¬nh.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            cfg = _read_manager_cfg() or {}
            servers = cfg.get("DISCORD_SERVER_PROFILES", {})
            if not isinstance(servers, dict) or server not in servers:
                await interaction.followup.send(f"âŒ KhÃ´ng tÃ¬m tháº¥y server `{server}`.", ephemeral=True)
                return
            servers[server].pop("status_channel_id", None)
            cfg["DISCORD_SERVER_PROFILES"] = servers
            if _save_manager_cfg(cfg):
                await interaction.followup.send(f"âœ… ÄÃ£ há»§y gÃ¡n kÃªnh START/STATUS cá»§a `{server}`.", ephemeral=True)
            else:
                await interaction.followup.send("âŒ KhÃ´ng lÆ°u Ä‘Æ°á»£c cáº¥u hÃ¬nh.", ephemeral=True)

        @query_group.command(name="setrankingchannel", description="(Admin) GÃ¡n kÃªnh Báº¢NG Xáº¾P Háº NG cho 1 server")
        @_discord.app_commands.describe(channel="KÃªnh nháº­n card xáº¿p háº¡ng", server="TÃªn server profile")
        @_discord.app_commands.autocomplete(server=_server_name_autocomplete)
        async def query_setrankingchannel(interaction: _discord.Interaction, channel: _discord.TextChannel, server: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("âŒ Chá»‰ admin Ä‘Æ°á»£c phÃ©p cáº¥u hÃ¬nh.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            cfg = _read_manager_cfg() or {}
            servers = cfg.get("DISCORD_SERVER_PROFILES", {})
            if not isinstance(servers, dict) or server not in servers:
                await interaction.followup.send(f"âŒ KhÃ´ng tÃ¬m tháº¥y server `{server}`.", ephemeral=True)
                return
            servers[server]["ranking_channel_id"] = str(channel.id)
            cfg["DISCORD_SERVER_PROFILES"] = servers
            if _save_manager_cfg(cfg):
                try:
                    msg_id = await _ensure_ranking_card_in_channel(channel)
                    await interaction.followup.send(
                        f"âœ… ÄÃ£ gÃ¡n kÃªnh Báº¢NG Xáº¾P Háº NG <#{channel.id}> cho server `{server}`.\n"
                        f"ðŸ† Ranking card: `msg_id={msg_id}` (tá»« giá» chá»‰ edit, khÃ´ng tá»± gá»­i má»›i).",
                        ephemeral=True
                    )
                except Exception as e:
                    await interaction.followup.send(
                        f"âš ï¸ ÄÃ£ lÆ°u mapping nhÆ°ng chÆ°a táº¡o/Ä‘á»“ng bá»™ ranking card: {e}",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send("âŒ KhÃ´ng lÆ°u Ä‘Æ°á»£c cáº¥u hÃ¬nh.", ephemeral=True)

        @query_group.command(name="removerankingchannel", description="(Admin) Há»§y gÃ¡n kÃªnh Báº¢NG Xáº¾P Háº NG cá»§a 1 server")
        @_discord.app_commands.describe(server="TÃªn server profile cáº§n há»§y")
        @_discord.app_commands.autocomplete(server=_server_name_autocomplete)
        async def query_removerankingchannel(interaction: _discord.Interaction, server: str):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("âŒ Chá»‰ admin Ä‘Æ°á»£c phÃ©p cáº¥u hÃ¬nh.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            cfg = _read_manager_cfg() or {}
            servers = cfg.get("DISCORD_SERVER_PROFILES", {})
            if not isinstance(servers, dict) or server not in servers:
                await interaction.followup.send(f"âŒ KhÃ´ng tÃ¬m tháº¥y server `{server}`.", ephemeral=True)
                return
            servers[server].pop("ranking_channel_id", None)
            cfg["DISCORD_SERVER_PROFILES"] = servers
            if _save_manager_cfg(cfg):
                await interaction.followup.send(f"âœ… ÄÃ£ há»§y gÃ¡n kÃªnh Báº¢NG Xáº¾P Háº NG cá»§a `{server}`.", ephemeral=True)
            else:
                await interaction.followup.send("âŒ KhÃ´ng lÆ°u Ä‘Æ°á»£c cáº¥u hÃ¬nh.", ephemeral=True)

        bot.tree.add_command(query_group)

        @bot.tree.command(name="synccommands", description="(Admin) Äá»“ng bá»™ ngay slash commands trong guild hiá»‡n táº¡i")
        async def slash_synccommands(interaction: _discord.Interaction):
            if not _is_discord_admin(interaction):
                await interaction.response.send_message("âŒ Chá»‰ admin Ä‘Æ°á»£c phÃ©p sync lá»‡nh.", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            try:
                guild = interaction.guild
                if guild is None:
                    await interaction.followup.send("âŒ Lá»‡nh nÃ y chá»‰ dÃ¹ng trong server Discord.", ephemeral=True)
                    return
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                await interaction.followup.send(f"âœ… ÄÃ£ sync `{len(synced)}` lá»‡nh cho guild `{guild.name}`.\n"
                                                "Gá»£i Ã½: dÃ¹ng `/query setchannel` vÃ  `/query setrankingchannel` Ä‘á»ƒ gáº¯n card, "
                                                "sau Ä‘Ã³ bot chá»‰ edit tin hiá»‡n cÃ³ (khÃ´ng spam).",
                                                ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"âŒ Sync lá»‡nh tháº¥t báº¡i: {e}", ephemeral=True)

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

        @bot.tree.command(name="unban", description="Unban nhanh tá»« danh sÃ¡ch ban AntiBug")
        @_discord.app_commands.describe(target="Chá»n ngÆ°á»i cáº§n unban (TÃªn - steamid)")
        @_discord.app_commands.autocomplete(target=_unban_target_autocomplete)
        async def slash_unban(interaction: _discord.Interaction, target: str):
            await interaction.response.defer(ephemeral=True)
            ok, detail = _app._unban_steamid_common(target, source="DISCORD /unban")
            if ok:
                await interaction.followup.send(f"âœ… {detail}", ephemeral=True)
            else:
                await interaction.followup.send(f"âŒ {detail}", ephemeral=True)

        # â”€â”€ Chat bridge (náº¿u cÃ³ channel ID) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if DISCORD_BOT2_CHANNEL_ID:
            @bot.event
            async def on_message(message):
                # Xá»­ lÃ½ commands trÆ°á»›c
                await bot.process_commands(message)
                
                # Chat bridge (chá»‰ trong channel Ä‘Ã£ cáº¥u hÃ¬nh)
                if str(message.channel.id) == str(DISCORD_BOT2_CHANNEL_ID):
                    if message.author.bot or message.webhook_id:
                        return
                    if message.content.startswith('!'):
                        return  # Bá» qua commands
                    
                    content = message.content.strip()
                    if content:
                        username = message.author.display_name or message.author.name
                        broadcast_text = f"[Discord] {username}: {content}"
                        self.send_ingame_broadcast(broadcast_text)
                        self._enqueue_console(f"ðŸ’¬ [Discord Bot 2] {username}: {content}")

        # â”€â”€ Cháº¡y bot vá»›i auto-reconnect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._discord_bot2_loop = loop

        while True:
            self._discord_bot2_client = bot
            self._discord_bot2_status = "â³ Äang káº¿t ná»‘i Discord Gateway..."
            try:
                loop.run_until_complete(bot.start(DISCORD_BOT2_TOKEN))
            except _discord.errors.LoginFailure:
                self._discord_bot2_ok = False
                self._discord_bot2_status = "âŒ Bot 2 Token khÃ´ng há»£p lá»‡"
                self._enqueue_console("âŒ Discord Bot 2: Token khÃ´ng há»£p lá»‡")
                return
            except _discord.errors.PrivilegedIntentsRequired:
                self._discord_bot2_ok = False
                self._discord_bot2_status = "âŒ Cáº§n báº­t Message Content Intent"
                self._enqueue_console("âŒ Discord Bot 2: Cáº§n báº­t Message Content Intent")
                return
            except KeyboardInterrupt:
                return
            except Exception as e:
                self._discord_bot2_ok = False
                self._discord_bot2_status = f"âš ï¸ Lá»—i káº¿t ná»‘i â€” thá»­ láº¡i sau 15s"
                self._enqueue_console(f"âš ï¸ Discord Bot 2 lá»—i: {e}")
            finally:
                try:
                    if not bot.is_closed():
                        loop.run_until_complete(bot.close())
                except Exception:
                    pass
            time.sleep(15)

    # â”€â”€ Reset sequence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def reset_sequence(self):
        if self.is_processing:
            return
        self.is_processing = True
        self.is_notified_online = False
        try:
            self._enqueue_console("ðŸš€ Khá»Ÿi Ä‘á»™ng Reset 30s (ThÃ´ng bÃ¡o Ä‘á»)...")
            self.send_discord_alert("âš ï¸ **[Manager ServerPal]** MÃ¡y chá»§ Ä‘ang lÆ°u dá»¯ liá»‡u vÃ  sáº½ Restart sau **30 giÃ¢y**!")

            self.send_ingame_broadcast("SERVER RESET TRONG 30S - DANG LUU DU LIEU!")
            threading.Thread(
                target=lambda: requests.post(f"{API_URL}/save", auth=AUTH, timeout=25),
                daemon=True
            ).start()
            self._enqueue_console("ðŸ’¾ Äang Save ngáº§m...")
            time.sleep(10)

            self.send_ingame_broadcast("SERVER RESET TRONG 20S - VUI LONG THOAT NGAY!")
            time.sleep(10)

            self.send_ingame_broadcast("SERVER RESET TRONG 10S - HEN GAP LAI!")
            time.sleep(10)

            self._enqueue_console("ðŸ”Œ Äang Ä‘Ã³ng Server...")
            try:
                requests.post(f"{API_URL}/shutdown",
                              json={"waittime": 0, "message": "Restarting"},
                              auth=AUTH, timeout=5)
            except Exception:
                pass

            time.sleep(2)
            self._stop_server_processes(force=True, source="Auto reset")
            self._enqueue_console("âœ… ÄÃ£ giáº£i phÃ³ng RAM. Chá» khá»Ÿi Ä‘á»™ng láº¡i...")
            time.sleep(3)
            self._start_server_safe(source="Auto reset")
            self.is_notified_online = False

        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i reset: {e}")
        finally:
            time.sleep(10)
            self.is_processing = False

    def _stop_sequence_discord(self, initiated_by: str = "Discord") -> None:
        """Dá»«ng server theo yÃªu cáº§u tá»« Discord: thÃ´ng bÃ¡o 10s, 5s, save, rá»“i táº¯t."""
        try:
            self._enqueue_console(f"ðŸ›‘ {initiated_by}: Khá»Ÿi Ä‘á»™ng quy trÃ¬nh STOP cÃ³ cáº£nh bÃ¡o.")
            # Cá»‘ gáº¯ng save qua REST API trÆ°á»›c
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
                self._enqueue_console("ðŸ’¾ ÄÃ£ gá»­i lá»‡nh Save (REST/RCON).")

            # ThÃ´ng bÃ¡o Ä‘áº¿m ngÆ°á»£c
            self.send_ingame_broadcast("SERVER Sáº¼ Táº®T SAU 10 GIÃ‚Y - ÄANG LÆ¯U Dá»® LIá»†U!")
            time.sleep(5)
            self.send_ingame_broadcast("SERVER Sáº¼ Táº®T SAU 5 GIÃ‚Y - Táº M BIá»†T!")
            time.sleep(5)
            self.send_ingame_broadcast("SERVER ÄANG Táº®T - Háº¸N Gáº¶P Láº I!")

            # Gá»­i shutdown qua REST (náº¿u cÃ³), sau Ä‘Ã³ kill Ä‘á»ƒ cháº¯c cháº¯n
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
            self._enqueue_console("âœ… STOP: Server Ä‘Ã£ táº¯t.")
            self.root.after(0, self._update_ctrl_btn_state)
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i STOP (Discord): {e}")

    def _build_server_launch_cmd(self) -> list:
        """Build command cháº¡y PalServer.exe theo config hiá»‡n táº¡i, trÃ¡nh hardcode cá»©ng."""
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
        """Láº¥y IP/Port game tá»« server profile active; fallback sang PUBLIC_*."""
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
        """Ping 1 gÃ³i Ä‘á»ƒ biáº¿t host cÃ³ reachable á»Ÿ má»©c máº¡ng hay khÃ´ng."""
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
        """Kiá»ƒm tra cá»•ng game cÃ³ nháº­n káº¿t ná»‘i TCP hay chÆ°a."""
        try:
            with socket.create_connection((host, int(port)), timeout=float(timeout_sec)):
                return True
        except Exception:
            return False

    def _has_online_players(self) -> bool:
        """Náº¿u Ä‘Ã£ cÃ³ ngÆ°á»i vÃ o game thÃ¬ coi nhÆ° server usable, khÃ´ng cáº§n tiáº¿p tá»¥c startup check."""
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
        """Láº¥y cá»•ng game ká»³ vá»ng Ä‘á»ƒ khá»›p dÃ²ng log startup."""
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
        """TÃ¬m dáº¥u hiá»‡u server Ä‘Ã£ ready trong log PalDefender/PalServer."""
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
        """Theo dÃµi log startup song song: tháº¥y dÃ²ng ready trong 20s => OK; quÃ¡ 25s => treo."""
        if not STARTUP_LOG_READY_CHECK_ENABLED:
            return
        with self._startup_log_check_lock:
            self._startup_log_check_seq += 1
            seq = self._startup_log_check_seq
            # Reset retry counter cho má»™t phiÃªn start má»›i
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
                    f"âœ… Startup log-check PASS ({source}): tháº¥y 'Running Palworld dedicated server on :{port}' sau ~{elapsed}s."
                )
                return
            if time.time() >= ok_deadline and not seen_after_20:
                seen_after_20 = True
                self._enqueue_console(
                    f"â³ Startup log-check: sau 20s váº«n chÆ°a tháº¥y dÃ²ng ready :{port}, tiáº¿p tá»¥c chá» Ä‘áº¿n 25s..."
                )
            time.sleep(1.0)

        self._enqueue_console(
            f"âŒ Startup log-check FAIL ({source}): quÃ¡ 25s chÆ°a tháº¥y 'Running Palworld dedicated server on :{port}' -> nghi treo."
        )
        # Tá»± khá»Ÿi Ä‘á»™ng láº¡i ngay 1 láº§n Ä‘á»ƒ cá»©u treo (chá»‰ 1 retry, trÃ¡nh vÃ²ng láº·p vÃ´ háº¡n)
        try:
            with self._startup_log_check_lock:
                can_retry = getattr(self, "_startup_log_retry_count", 0) < 1
                if can_retry:
                    self._startup_log_retry_count = getattr(self, "_startup_log_retry_count", 0) + 1
                else:
                    can_retry = False
            if can_retry:
                self._enqueue_console("ðŸ” Startup log-check: nghi treo â†’ khá»Ÿi Ä‘á»™ng láº¡i ngay (retry 1/1).")
                self._stop_server_processes(force=True, source="Startup log-check retry")
                time.sleep(2)
                # Gá»i start an toÃ n; sáº½ tá»± schedule láº¡i log-check cho phiÃªn má»›i
                self._start_server_safe(source="LogReady Retry", run_health_check=False)
        except Exception:
            pass

    def _schedule_startup_health_check(self, source: str = "") -> None:
        """Sau khi start process, kiá»ƒm tra server cÃ³ thá»±c sá»± vÃ o Ä‘Æ°á»£c hay bá»‹ treo."""
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
            self._enqueue_console("âš ï¸ Startup health-check: thiáº¿u IP/PORT trong config, bá» qua kiá»ƒm tra treo.")
            return

        max_retries = max(0, int(self.STARTUP_HEALTH_RETRY_MAX))
        for boot_round in range(0, max_retries + 1):
            with self._startup_check_lock:
                if seq != self._startup_check_seq:
                    return

            round_txt = f"{boot_round + 1}/{max_retries + 1}"
            self._enqueue_console(
                f"ðŸ©º Startup health-check ({source}) lÆ°á»£t {round_txt}: kiá»ƒm tra {ip}:{port} sau khi boot..."
            )
            time.sleep(20)  # Chá» server náº¡p map/plugin trÆ°á»›c khi test káº¿t ná»‘i.

            connected = False
            for attempt in range(1, 9):
                with self._startup_check_lock:
                    if seq != self._startup_check_seq:
                        return
                if not self._is_server_running():
                    self._enqueue_console("âŒ Startup health-check: process PalServer Ä‘Ã£ táº¯t trong lÃºc kiá»ƒm tra.")
                    return

                ping_ok = self._ping_host_once(ip)
                tcp_ok = self._tcp_port_open(ip, port, timeout_sec=3.0)
                # Æ¯u tiÃªn kiá»ƒm tra port trÆ°á»›c; chá»‰ khi port OK má»›i xÃ©t player online.
                if tcp_ok and self._has_online_players():
                    ping_note = "OK" if ping_ok else "khÃ´ng pháº£n há»“i"
                    self._enqueue_console(
                        f"âœ… Startup health-check PASS: port {port} Ä‘Ã£ má»Ÿ vÃ  cÃ³ ngÆ°á»i chÆ¡i online "
                        f"(ping: {ping_note})."
                    )
                    connected = True
                    break

                if tcp_ok:
                    ping_note = "OK" if ping_ok else "khÃ´ng pháº£n há»“i"
                    self._enqueue_console(
                        f"âœ… Startup health-check PASS: {ip}:{port} Ä‘Ã£ vÃ o Ä‘Æ°á»£c (ping: {ping_note})."
                    )
                    connected = True
                    break

                self._enqueue_console(
                    f"âš ï¸ Startup health-check lÆ°á»£t {round_txt} láº§n {attempt}/8: "
                    f"chÆ°a káº¿t ná»‘i Ä‘Æ°á»£c {ip}:{port} "
                    f"(ping={'OK' if ping_ok else 'FAIL'}, tcp={'OK' if tcp_ok else 'FAIL'})."
                )
                time.sleep(10)

            if connected:
                return

            if boot_round < max_retries:
                retry_no = boot_round + 1
                self._enqueue_console(
                    f"ðŸ” KhÃ´ng vÃ o Ä‘Æ°á»£c sau khá»Ÿi Ä‘á»™ng. Tá»± khá»Ÿi Ä‘á»™ng láº¡i láº§n {retry_no}/{max_retries}..."
                )
                self._stop_server_processes(force=True, source=f"Startup health retry {retry_no}")
                time.sleep(2)
                self._start_server_safe(
                    source=f"{source} Retry {retry_no}",
                    run_health_check=False
                )
                continue

        warn_msg = (
            f"âŒ Cáº£nh bÃ¡o treo sau {max_retries + 1} lÆ°á»£t khá»Ÿi Ä‘á»™ng: process cháº¡y nhÆ°ng chÆ°a vÃ o Ä‘Æ°á»£c {ip}:{port}."
        )
        self._enqueue_console(warn_msg)
        try:
            self.send_discord_alert(
                "ðŸš¨ **[Cáº¢NH BÃO STARTUP TREO]**\n"
                f"â€¢ Nguá»“n khá»Ÿi Ä‘á»™ng: `{source}`\n"
                f"â€¢ Endpoint kiá»ƒm tra: `{ip}:{port}`\n"
                f"â€¢ ÄÃ£ thá»­ restart: `{max_retries}` láº§n\n"
                "â€¢ Tráº¡ng thÃ¡i: Process cÃ³ thá»ƒ Ä‘Ã£ lÃªn nhÆ°ng ngÆ°á»i chÆ¡i chÆ°a vÃ o Ä‘Æ°á»£c."
            )
        except Exception:
            pass

    def _refresh_server_exe_runtime(self) -> str:
        """Äá»c láº¡i SERVER_EXE tá»« manager_config Ä‘á»ƒ há»— trá»£ Ä‘á»•i Ä‘Æ°á»ng dáº«n khi app Ä‘ang cháº¡y."""
        global SERVER_EXE
        try:
            cfg = _read_manager_cfg()
            if isinstance(cfg, dict):
                SERVER_EXE = _resolve_server_exe_from_cfg(cfg.get("SERVER_EXE", ""), SERVER_EXE)
        except Exception:
            pass
        return SERVER_EXE

    def _get_palserver_processes(self) -> list:
        """TÃ¬m process PalServer Ä‘ang cháº¡y dá»±a trÃªn exe/name."""
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
        # Äá»“ng bá»™ Ä‘Æ°á»ng dáº«n runtime trÆ°á»›c khi check.
        self._refresh_server_exe_runtime()
        return len(self._get_palserver_processes()) > 0

    def _stop_server_processes(self, force: bool = True, source: str = "") -> bool:
        """Dá»«ng táº¥t cáº£ process PalServer hiá»‡n cÃ³."""
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
            self._enqueue_console(f"â¹ ÄÃ£ dá»«ng PalServer ({source or 'manual'}).")
        return stopped_any

    def _start_server_safe(self, source: str = "", run_health_check: bool = True) -> bool:
        """Khá»Ÿi Ä‘á»™ng PalServer.exe an toÃ n: check path + trÃ¡nh cháº¡y trÃ¹ng."""
        with self._server_op_lock:
            self._refresh_server_exe_runtime()
            if not SERVER_EXE or not os.path.isfile(SERVER_EXE):
                self._enqueue_console(f"âŒ SERVER_EXE khÃ´ng há»£p lá»‡: {SERVER_EXE}")
                return False
            if os.path.basename(SERVER_EXE).lower() != "palserver.exe":
                self._enqueue_console(f"âŒ SERVER_EXE khÃ´ng pháº£i PalServer.exe: {SERVER_EXE}")
                return False
            if self._is_server_running():
                self._enqueue_console(f"â„¹ï¸ Server Ä‘Ã£ cháº¡y ({source or 'safe-start'}), bá» qua start trÃ¹ng.")
                return True
            try:
                # Cháº¡y giá»‘ng má»Ÿ tay PalServer.exe Ä‘á»ƒ trÃ¡nh crash Shipping-Cmd khi launch báº±ng args.
                server_dir = os.path.dirname(SERVER_EXE)
                try:
                    os.startfile(SERVER_EXE)
                    self._enqueue_console(f"â–¶ï¸ Khá»Ÿi Ä‘á»™ng PalServer ({source or 'safe-start'}) báº±ng startfile (user mode).")
                except Exception:
                    subprocess.Popen(
                        [SERVER_EXE],
                        cwd=server_dir,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                    self._enqueue_console(f"â–¶ï¸ Khá»Ÿi Ä‘á»™ng PalServer ({source or 'safe-start'}) khÃ´ng args (user mode).")
                time.sleep(3)
                if self._is_server_running():
                    self._schedule_startup_log_ready_check(source=source or "safe-start")
                    if run_health_check:
                        self._schedule_startup_health_check(source=source or "safe-start")
                    return True
                self._enqueue_console("âŒ Start tháº¥t báº¡i: chÆ°a tháº¥y process PalServer sau khi má»Ÿ file exe.")
                return False
            except Exception as e:
                self._enqueue_console(f"âŒ Lá»—i khá»Ÿi Ä‘á»™ng server ({source or 'safe-start'}): {e}")
                return False

    # â”€â”€ Watchdog â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def watchdog(self):
        while True:
            try:
                if self.auto_mode.get() and not self.is_processing:
                    now_ts = time.time()
                    cooldown_ok = (now_ts - self._watchdog_last_restart_at) > self.WATCHDOG_RESTART_COOLDOWN_SEC
                    if not self._is_server_running():
                        self.root.after(0, lambda: self.lbl_status.config(text="â— SERVER OFFLINE", fg="#ff4444"))
                        if cooldown_ok:
                            self._watchdog_last_restart_at = now_ts
                            self._enqueue_console("ðŸ” Watchdog: khá»Ÿi Ä‘á»™ng láº¡i server an toÃ n...")
                            self._start_server_safe(source="Watchdog")
                            self.is_notified_online = False
                    else:
                        self.root.after(0, lambda: self.lbl_status.config(text="â— SERVER ONLINE", fg="#00ffcc"))
                        if not self.is_notified_online:
                            try:
                                res = requests.get(f"{API_URL}/info", auth=AUTH, timeout=2)
                                if res.status_code == 200:
                                    self.send_discord_alert(
                                        "ðŸš€ **[MÃ¡y Chá»§ Ä‘ang ONLINE]**\n"
                                        "âœ… Vui lÃ²ng káº¿t ná»‘i 27.65.213.42:8211 password lÃ  1111\n"
                                        "VÃ o Chiáº¿n Vá»›i Anh Em Bá»‘n PhÆ°Æ¡ng ThÃ´i"
                                    )
                                    self.is_notified_online = True
                            except Exception:
                                pass
            except Exception:
                pass
            time.sleep(self.WATCHDOG_CHECK_INTERVAL_SEC)

    # â”€â”€ Server log tail â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def server_log_tail(self):
        """Background thread: Ä‘á»c PalServer.log vÃ  Ä‘áº©y dÃ²ng má»›i vÃ o queue."""
        while True:
            try:
                if os.path.isfile(SERVER_LOG_FILE):
                    size = os.path.getsize(SERVER_LOG_FILE)
                    if size < self._server_log_pos:
                        # File bá»‹ reset / rotate
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

                            # â”€â”€ Admin mode tracking tá»« PalServer.log â”€â”€â”€â”€â”€â”€
                            m_on = _ADMIN_ON_RE.search(line)
                            if m_on:
                                self._admin_mode_players.add(m_on.group(3))
                            else:
                                m_off = _ADMIN_OFF_RE.search(line)
                                if m_off:
                                    self._admin_mode_players.discard(
                                        m_off.group(3))

                            # â”€â”€ Tech-Cheat: ngÆ°á»i chÆ¡i tá»± há»c â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                            # Format: 'X' (...) unlocking Technology: 'TechCode'
                            m_tech = _TECH_RE.search(line)
                            if m_tech:
                                _, plr_name, plr_sid, tech_code = m_tech.groups()
                                self._techbug_check_event(
                                    plr_sid, plr_name, tech_code,
                                    source="natural")

                            # â”€â”€ Tech-Cheat: admin dÃ¹ng /learntech â”€â”€â”€â”€â”€â”€â”€â”€
                            # Format: Replying to 'X': "Successfully unlocked technology 'TechCode' for..."
                            m_lt = _TECH_LEARNTECH_RE.search(line)
                            if m_lt:
                                _, plr_name, plr_sid, tech_code = m_lt.groups()
                                self._techbug_check_event(
                                    plr_sid, plr_name, tech_code,
                                    source="learntech")

                            # â”€â”€ Chat in-game tá»« PalServer.log (fallback) â”€â”€
                            m_sc = _SERVERLOG_CHAT_RE.search(line)
                            if m_sc:
                                plr_name2, msg2 = m_sc.group(1), m_sc.group(2)
                                if msg2.strip():
                                    self._enqueue_console(
                                        f"ðŸ’¬ {plr_name2}: {msg2.strip()}")
            except Exception:
                pass
            time.sleep(0.5)

    # â”€â”€ PalDefender helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _find_latest_paldef_log(self) -> str:
        """Tráº£ vá» Ä‘Æ°á»ng dáº«n file log PalDefender má»›i nháº¥t (theo mtime)."""
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
        """Tráº£ vá» Ä‘Æ°á»ng dáº«n file cheat log má»›i nháº¥t."""
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
        """Background thread: theo dÃµi PalDefender main log, tá»± nháº£y sang file má»›i."""
        while True:
            try:
                latest = self._find_latest_paldef_log()
                if latest and latest != self._paldef_log_file:
                    # Server khá»Ÿi Ä‘á»™ng láº¡i â†’ file má»›i
                    self._paldef_log_file = latest
                    self._paldef_log_pos  = 0
                    fname = os.path.basename(latest)
                    self._paldef_log_queue.put("â”€" * 55)
                    self._paldef_log_queue.put(f"ðŸ“‚  Session má»›i: {fname}")
                    self._paldef_log_queue.put("â”€" * 55)

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

                            # â”€â”€ AntiBug: build/dismantle speed â”€â”€â”€â”€â”€â”€â”€â”€
                            ev = self._antibug_parse_line(line)
                            if ev:
                                self._antibug_process_event(ev)

                            # â”€â”€ LiveMap Base: PalBoxV2 build/dismantle (real-time) â”€â”€
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

                            # â”€â”€ Admin mode tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
                            m_on = _ADMIN_ON_RE.search(line)
                            if m_on:
                                self._admin_mode_players.add(m_on.group(3))
                            else:
                                m_off = _ADMIN_OFF_RE.search(line)
                                if m_off:
                                    self._admin_mode_players.discard(
                                        m_off.group(3))

                            # â”€â”€ Tech-Cheat: ngÆ°á»i chÆ¡i tá»± há»c â”€â”€â”€â”€â”€â”€â”€â”€
                            # Format: 'X' (...) unlocking Technology: 'TechCode'
                            m_tech = _TECH_RE.search(line)
                            if m_tech:
                                _, plr_name, plr_sid, tech_code = m_tech.groups()
                                self._techbug_check_event(
                                    plr_sid, plr_name, tech_code,
                                    source="natural")

                            # â”€â”€ Tech-Cheat: admin dÃ¹ng /learntech â”€â”€â”€â”€â”€
                            # Format: Replying to 'X': "Successfully unlocked technology 'TechCode' for..."
                            m_lt = _TECH_LEARNTECH_RE.search(line)
                            if m_lt:
                                _, plr_name, plr_sid, tech_code = m_lt.groups()
                                self._techbug_check_event(
                                    plr_sid, plr_name, tech_code,
                                    source="learntech")

                            # â”€â”€ Chat in-game tá»« PalDefender log â”€â”€â”€â”€â”€â”€â”€
                            # Format: [HH:MM:SS][info] [Chat::Global]['Name' (...)]: msg
                            m_chat = _CHAT_RE.search(line)
                            if m_chat:
                                ts       = m_chat.group(1)   # HH:MM:SS
                                ch_type  = m_chat.group(2)   # Global / Local / ...
                                plr_name = m_chat.group(3)   # TÃªn ngÆ°á»i chÆ¡i
                                msg      = m_chat.group(5)   # Ná»™i dung tin nháº¯n
                                if msg.strip():
                                    self._enqueue_console(
                                        f"ðŸ’¬ [{ts}] [{ch_type}] {plr_name}: {msg.strip()}")
                                    # Forward â†’ Discord (webhook vá»›i tÃªn ngÆ°á»i chÆ¡i)
                                    self._discord_forward_chat(plr_name, ch_type, msg.strip())

                            # â”€â”€ NPC Attack Tracking (kick) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

                            # â”€â”€ Pal Capture Tracking (ban) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        """Background thread: theo dÃµi cheat log, cáº£nh bÃ¡o Discord khi phÃ¡t hiá»‡n."""
        def _flush_dedupe():
            if self._cheat_dedupe_count > 1 and self._cheat_dedupe_last_line:
                self._paldef_cheat_queue.put(f"â†³ (gá»™p {self._cheat_dedupe_count} dÃ²ng trÃ¹ng)")
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
                            # Cáº£nh bÃ¡o manager console + Discord
                            if "cheater" in line.lower() or "[warning]" in line.lower():
                                now_ts = time.time()
                                key = line[:180]
                                prev = float(self._cheat_alert_last.get(key, 0.0))
                                if now_ts - prev < 10.0:
                                    continue
                                self._cheat_alert_last[key] = now_ts
                                self._enqueue_console(f"ðŸš¨ CHEAT DETECTED: {line}")
                                _alert_msg = (
                                    f"ðŸš¨ **[CHEAT DETECTED - PALDEFENDER]**\n"
                                    f"```{line}```"
                                )
                                # â†’ Antibug webhook (admin-only)
                                if self.paldef_discord_alert.get():
                                    threading.Thread(
                                        target=self._send_antibug_discord,
                                        args=(_alert_msg,),
                                        daemon=True
                                    ).start()
                                # â†’ Main Discord webhook (thÃ´ng bÃ¡o cÃ´ng khai)
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
        """XÃ³a file log PalDefender quÃ¡ háº¡n trong Logs vÃ  Logs\\Cheats."""
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
        # Dá»n cáº£ Logs, Logs\Cheats vÃ  Logs\RESTAPI (theo yÃªu cáº§u váº­n hÃ nh).
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
            self._enqueue_console(f"ðŸ§¹ Log cleanup: Ä‘Ã£ xÃ³a {deleted} file cÅ© (> {keep_h}h).")

    def paldef_log_cleanup_loop(self):
        """Dá»n log cÅ© Ä‘á»‹nh ká»³ Ä‘á»ƒ thÆ° má»¥c Logs/Cheats luÃ´n gá»n."""
        while True:
            try:
                self._cleanup_paldef_logs_once()
            except Exception:
                pass
            time.sleep(300)

    # â”€â”€ Scheduler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def scheduler_process(self):
        while True:
            if self.auto_mode.get():
                now = datetime.datetime.now().strftime("%H:%M")
                if now in RESET_SCHEDULE and self.last_reset_minute != now:
                    self.last_reset_minute = now
                    threading.Thread(target=self.reset_sequence, daemon=True).start()
            time.sleep(10)

    # â”€â”€ Stats loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€ Player sync â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                                # Checkpoint playtime online Ä‘á»‹nh ká»³ Ä‘á»ƒ trÃ¡nh máº¥t dá»¯ liá»‡u khi crash
                                sess = float(self.player_stats[steamid].get("session_start", 0.0) or 0.0)
                                if sess > 0 and steamid not in self._online_players_prev:
                                    # vá»«a reconnect session tá»« tráº¡ng thÃ¡i chÆ°a Ä‘á»“ng bá»™
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
                    # Save khi cÃ³ thay Ä‘á»•i hoáº·c má»—i 60s náº¿u Ä‘ang cÃ³ ngÆ°á»i online (Ä‘áº£m báº£o durability)
                    if dirty and (now_ts - self._player_stats_last_save_ts >= 5):
                        self._save_player_stats()
                        self._audit_playtime_event("save", "-", "system", note=f"dirty_save players={len(self.player_stats)}")
                    elif online_now and (now_ts - self._player_stats_last_save_ts >= 60):
                        self._save_player_stats()
                        self._audit_playtime_event("save", "-", "system", note=f"periodic_save players={len(self.player_stats)}")
            except Exception:
                pass
            time.sleep(10)

    # â”€â”€ Player Ranking System â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _normalize_player_stats_record(self, steamid: str, stats: dict) -> dict:
        now_ts = time.time()
        if not isinstance(stats, dict):
            stats = {}
        return {
            "name": str(stats.get("name", self._steamid_to_name.get(steamid, "Unknown")) or "Unknown"),
            "level": int(stats.get("level", 0) or 0),
            "pal_count": int(stats.get("pal_count", 0) or 0),
            "playtime_sec": float(stats.get("playtime_sec", 0.0) or 0.0),
            # session_start chá»‰ giá»¯ khi > 0, cÃ²n láº¡i reset 0.0 Ä‘á»ƒ rÃµ tráº¡ng thÃ¡i offline
            "session_start": float(stats.get("session_start", 0.0) or 0.0),
            "last_update": float(stats.get("last_update", now_ts) or now_ts),
        }

    def _load_player_stats(self):
        """Load player stats tá»« file JSON."""
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
        """LÆ°u player stats vÃ o file JSON."""
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
            title = "ðŸŸ¢ NgÆ°á»i chÆ¡i Ä‘Ã£ tham gia / Ä‘ang káº¿t ná»‘i" if joined else "ðŸ”´ NgÆ°á»i chÆ¡i Ä‘Ã£ rá»i máº¡ng"
            payload = {
                "username": "Connect",
                "embeds": [{
                    "title": title,
                    "color": 0x57F287 if joined else 0xED4245,
                    "fields": [
                        {"name": "ðŸ‘¤ NgÆ°á»i chÆ¡i", "value": f"`{name}`", "inline": True},
                        {"name": "ðŸ†” SteamID", "value": f"`{steamid}`", "inline": True},
                        {"name": "ðŸ‘¥ Online", "value": f"`{online_count}/{max_players}`", "inline": True},
                    ],
                    "footer": {"text": f"Manager ServerPal â€¢ {now_txt}"}
                }]
            }
            requests.post(PLAYER_CONNECT_WEBHOOK_URL, json=payload, timeout=6)
        except Exception:
            pass

    # â”€â”€ Bot 2 message ID persistence â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _load_bot2_msg_ids(self):
        """Load message IDs tá»« file Ä‘á»ƒ dÃ¹ng láº¡i sau restart â€” trÃ¡nh spam."""
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
        """LÆ°u message IDs vÃ o file Ä‘á»ƒ dÃ¹ng láº¡i sau restart."""
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
        """Track khi ngÆ°á»i chÆ¡i báº¯t Ä‘Æ°á»£c Pal.
        Náº¿u Pal bá»‹ báº¯t lÃ  NPC (SalesPerson, BlackMarketTrader, â€¦) â†’ auto-ban ngay láº­p tá»©c.
        """
        if not steamid:
            return
        steamid = self._normalize_steamid(steamid)
        if not steamid:
            return

        # â”€â”€ Kiá»ƒm tra NPC capture â†’ BAN ngay â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if self.npc_capture_ban_enabled.get() and pal_id:
            if pal_id.strip() in NPC_BAN_IDS:
                threading.Thread(
                    target=self._npc_capture_ban_player,
                    args=(steamid, player_name, pal_name, pal_id, coords),
                    daemon=True
                ).start()
                return  # KhÃ´ng cáº§n track stat, ngÆ°á»i chÆ¡i sáº½ bá»‹ ban

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
        """Cáº­p nháº­t level cá»§a táº¥t cáº£ ngÆ°á»i chÆ¡i tá»« REST API hoáº·c cache."""
        try:
            res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
            if res.status_code == 200:
                players = res.json().get("players", [])
                for p in players:
                    steamid = self._normalize_steamid(p.get("userId", ""))
                    name = p.get("name", "")
                    if not steamid:
                        continue
                    
                    # Thá»­ láº¥y level tá»« API response (náº¿u cÃ³)
                    level = p.get("level", 0)
                    if level == 0:
                        # Fallback: dÃ¹ng cache náº¿u cÃ³
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
        """Láº¥y danh sÃ¡ch xáº¿p háº¡ng top N ngÆ°á»i chÆ¡i.
        Sáº¯p xáº¿p theo: level (giáº£m dáº§n), sau Ä‘Ã³ pal_count (giáº£m dáº§n).
        """
        self._update_player_levels()
        
        # Lá»c vÃ  sáº¯p xáº¿p
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
        
        # Sáº¯p xáº¿p: level giáº£m dáº§n, pal_count giáº£m dáº§n, sau Ä‘Ã³ playtime giáº£m dáº§n
        ranked.sort(key=lambda x: (x["level"], x["pal_count"], x["playtime_sec"]), reverse=True)
        return ranked[:top_n]

    def _send_ranking_to_discord(self):
        """Gá»­i báº£ng xáº¿p háº¡ng Ä‘áº¹p lÃªn Discord (kÃªnh Báº£ng Xáº¿p Háº¡ng riÃªng)."""
        webhook = RANKING_WEBHOOK_URL or DISCORD_WEBHOOK_URL
        if not webhook:
            return
        
        try:
            ranking = self._get_ranking(20)  # Top 20
            
            if not ranking:
                return
            
            # TÃ­nh tá»•ng sá»‘ ngÆ°á»i chÆ¡i cÃ³ dá»¯ liá»‡u
            total_players = len([s for s in self.player_stats.values() 
                               if s.get("level", 0) > 0 or s.get("pal_count", 0) > 0])
            
            # Táº¡o embed Ä‘áº¹p vÃ  chuyÃªn nghiá»‡p
            embed = {
                "title": "ðŸ† Báº¢NG Xáº¾P Háº NG NGÆ¯á»œI CHÆ I",
                "description": f"ðŸ“Š **Top ngÆ°á»i chÆ¡i theo cáº¥p Ä‘á»™ vÃ  sá»‘ lÆ°á»£ng Pal Ä‘Ã£ báº¯t**\n"
                              f"ðŸ‘¥ Tá»•ng sá»‘ ngÆ°á»i chÆ¡i cÃ³ dá»¯ liá»‡u: **{total_players}**",
                "color": 0x00ff88,  # MÃ u xanh lÃ¡
                "thumbnail": {
                    "url": "https://i.imgur.com/4M34hi2.png"  # Palworld logo placeholder
                },
                "fields": [],
                "footer": {
                    "text": f"Palworld Server Ranking â€¢ Cáº­p nháº­t: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                    "icon_url": "https://i.imgur.com/4M34hi2.png"
                },
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
            }
            
            # Táº¡o field cho top 10 vá»›i format Ä‘áº¹p
            top_10_text = ""
            medals = ["ðŸ¥‡", "ðŸ¥ˆ", "ðŸ¥‰"]
            level_icons = ["â­", "ðŸŒŸ", "ðŸ’«"]
            
            for idx, player in enumerate(ranking[:10], 1):
                medal = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
                name = player["name"][:18]  # Giá»›i háº¡n Ä‘á»™ dÃ i tÃªn
                level = player["level"]
                pal_count = player["pal_count"]
                playtime = self._fmt_playtime(player.get("playtime_sec", 0))
                
                # ThÃªm padding cho tÃªn Ä‘á»ƒ cÄƒn chá»‰nh Ä‘áº¹p
                name_padded = name.ljust(18)
                
                # Icon level theo cáº¥p Ä‘á»™
                if level >= 50:
                    level_icon = level_icons[2]
                elif level >= 30:
                    level_icon = level_icons[1]
                else:
                    level_icon = level_icons[0]
                
                top_10_text += f"{medal} **{name_padded}**\n"
                top_10_text += f"   {level_icon} Cáº¥p: `{level:3d}` | ðŸŽ£ Pal: `{pal_count:4d}` | â± `{playtime}`\n\n"
            
            embed["fields"].append({
                "name": "ðŸ… TOP 10 NGÆ¯á»œI CHÆ I HÃ€NG Äáº¦U",
                "value": top_10_text or "ChÆ°a cÃ³ dá»¯ liá»‡u",
                "inline": False
            })
            
            # ThÃªm field cho top 11-20 náº¿u cÃ³ (format compact hÆ¡n)
            if len(ranking) > 10:
                top_11_20_text = ""
                for idx, player in enumerate(ranking[10:20], 11):
                    name = player["name"][:16]
                    level = player["level"]
                    pal_count = player["pal_count"]
                    playtime = self._fmt_playtime(player.get("playtime_sec", 0))
                    # Format compact vá»›i emoji
                    top_11_20_text += f"**{idx:2d}.** {name[:16]:<16} â­`{level:3d}` ðŸŽ£`{pal_count:4d}` â±`{playtime}`\n"
                
                embed["fields"].append({
                    "name": "ðŸ“‹ TOP 11-20",
                    "value": top_11_20_text,
                    "inline": False
                })
            
            # ThÃªm thá»‘ng kÃª tá»•ng quan
            if ranking:
                avg_level = sum(p["level"] for p in ranking) / len(ranking)
                avg_pals = sum(p["pal_count"] for p in ranking) / len(ranking)
                max_level = max(p["level"] for p in ranking)
                max_pals = max(p["pal_count"] for p in ranking)
                
                stats_text = (
                    f"ðŸ“ˆ **Cáº¥p Ä‘á»™ trung bÃ¬nh:** `{avg_level:.1f}`\n"
                    f"ðŸŽ£ **Pal trung bÃ¬nh:** `{avg_pals:.1f}`\n"
                    f"ðŸ”¥ **Cáº¥p cao nháº¥t:** `{max_level}`\n"
                    f"ðŸ’Ž **Nhiá»u Pal nháº¥t:** `{max_pals}`"
                )
                
                embed["fields"].append({
                    "name": "ðŸ“Š THá»NG KÃŠ Tá»”NG QUAN",
                    "value": stats_text,
                    "inline": False
                })
            
            # Gá»­i webhook â€” Æ°u tiÃªn RANKING_WEBHOOK_URL, fallback DISCORD_WEBHOOK_URL
            webhook = RANKING_WEBHOOK_URL or DISCORD_WEBHOOK_URL
            payload = {
                "username": "ðŸ† Báº£ng Xáº¿p Háº¡ng",
                "embeds": [embed]
            }
            requests.post(webhook, json=payload, timeout=10)
            self._enqueue_console("âœ… ÄÃ£ gá»­i báº£ng xáº¿p háº¡ng lÃªn Discord (Báº£ng Xáº¿p Háº¡ng)")
            
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i gá»­i ranking Discord: {e}")

    def send_ranking_manual(self):
        """Gá»­i ranking thá»§ cÃ´ng (cÃ³ thá»ƒ gá»i tá»« UI hoáº·c command)."""
        try:
            self._update_player_levels()
            self._send_ranking_to_discord()
            self.ranking_last_update = time.time()
            return True
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i gá»­i ranking thá»§ cÃ´ng: {e}")
            return False

    def ranking_update_loop(self):
        """Background thread: cáº­p nháº­t vÃ  gá»­i ranking Ä‘á»‹nh ká»³."""
        time.sleep(30)  # Chá» server khá»Ÿi Ä‘á»™ng
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
            time.sleep(60)  # Check má»—i phÃºt

    # â”€â”€ Threads start â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
            self.guild_fetch_loop,         # Guild live â€” fetch má»—i 30s
            self._pdapi_status_poll,
            self.discord_to_ingame_poll,   # Discord â†” ingame chat bridge
            self.ranking_update_loop,     # Ranking system â€” cáº­p nháº­t Ä‘á»‹nh ká»³
            self.discord_bot2_poll,        # Discord Bot 2 â€” commands & features
        ]
        for task in tasks:
            threading.Thread(target=task, daemon=True).start()

    # â”€â”€ Player helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _normalize_steamid(self, raw: str) -> str:
        """Chuáº©n hÃ³a steamid: Ä‘áº£m báº£o dáº¡ng steam_XXXX."""
        if not raw:
            return ""
        raw = raw.strip().strip('"').strip("'")
        if raw.startswith("steam_"):
            return raw
        if raw.isdigit():
            return f"steam_{raw}"
        return raw

    def _read_max_players(self) -> int:
        """Äá»c ServerPlayerMaxNum tá»« PalWorldSettings.ini, fallback = 32."""
        try:
            ini = self._settings_parse_ini()
            v = ini.get("ServerPlayerMaxNum", "32")
            return max(1, int(float(v)))
        except Exception:
            return 32

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  RCON GIVE HELPERS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _rcon_give_item(self, playerid: str, steam_number: str, steamid: str,
                         item: str, qty: int) -> bool:
        """Gá»­i lá»‡nh 'give' qua RCON. Thá»­ nhiá»u format identifier."""
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
            self._enqueue_console(f"  ðŸ“¦ [ITEM] {cmd!r} â†’ {out or 'OK'}")
            if "failed" in low or "error" in low or "unknown" in low or \
               "not found" in low or "itemid" in low:
                continue
            return True
        return False

    def _rcon_give_pal(self, playerid: str, steam_number: str, steamid: str,
                        pal_id: str, level: int = 1) -> bool:
        """Gá»­i lá»‡nh 'givepal' qua RCON."""
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
            self._enqueue_console(f"  ðŸ¾ [PAL]  {cmd!r} â†’ {out or 'OK'}")
            if "failed" in low or "error" in low or "unknown" in low or \
               "not found" in low or "itemid" in low:
                continue
            return True
        return False

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  NEWBIE GIFT â€” TRACKING FILES
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _load_newbie_gift_tracking(self):
        """Äá»c danh sÃ¡ch SteamID Ä‘Ã£ nháº­n quÃ  tá»« file."""
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
        """LÆ°u SteamID vÃ o file tracking (append mode)."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)  # Ä‘áº£m báº£o thÆ° má»¥c tá»“n táº¡i
            with open(self.newbie_gift_file, "a", encoding="utf-8") as f:
                f.write(f"{steamid}\n")
            self.newbie_gift_received.add(steamid)
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i lÆ°u tracking quÃ  tÃ¢n thá»§: {e}")

    def _load_daily_checkin_tracking(self):
        """Load danh sÃ¡ch Ä‘Ã£ nháº­n quÃ  Ä‘iá»ƒm danh theo ngÃ y."""
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
        """Load tráº¡ng thÃ¡i tÃ­ch lÅ©y online 60 phÃºt."""
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
        """Äá»c cáº¥u hÃ¬nh quÃ  tá»« manager_config.json, fallback default náº¿u thiáº¿u."""
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
                # backward compatible: náº¿u config cÅ© lÃ  templates -> láº¥y template Ä‘áº§u lÃ m pool máº·c Ä‘á»‹nh
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
        """PhÃ¡t quÃ  theo chuáº©n tab quÃ  tÃ¢n thá»§: Æ°u tiÃªn PD API, fallback RCON item."""
        if log_fn is None:
            log_fn = self._log_gift
        for _ in range(2):
            ok, _ = self._pdapi_give(steamid, payload)
            if ok:
                log_fn(f"ðŸŽ {title}: Ä‘Ã£ phÃ¡t cho {player_name or steamid}")
                return True
            time.sleep(0.3)
        # Fallback: thá»­ phÃ¡t tá»«ng item qua RCON Ä‘á»ƒ giáº£m rá»§i ro lá»‡ch API.
        playerid = self._steamid_to_playerid.get(steamid, "")
        steam_number = steamid.replace("steam_", "") if steamid.startswith("steam_") else steamid
        items = list((payload or {}).get("Item", []) or [])
        if not items:
            self._log_gift(f"âŒ {title}: phÃ¡t tháº¥t báº¡i cho {player_name or steamid}")
            return False
        ok_count = 0
        for it in items:
            iid = str(it.get("ItemID", "") or "").strip()
            cnt = int(it.get("Count", 0) or 0)
            if not iid or cnt <= 0:
                continue
            ok = self._rcon_give_item(playerid, steam_number, steamid, iid, cnt)
            log_fn(f"{'âœ…' if ok else 'âŒ'} {title} fallback RCON: {iid} x{cnt}")
            if ok:
                ok_count += 1
        if ok_count >= max(1, int(len(items) * 0.8)):
            log_fn(f"ðŸŽ {title}: fallback RCON thÃ nh cÃ´ng {ok_count}/{len(items)} cho {player_name or steamid}")
            return True
        log_fn(f"âŒ {title}: tháº¥t báº¡i sau PD API + RCON fallback cho {player_name or steamid}")
        return False

    def _give_bundle_newbie_style(self, steamid: str, player_name: str, items: list, title: str, log_fn=None) -> bool:
        """PhÃ¡t quÃ  giá»‘ng cÆ¡ cháº¿ quÃ  tÃ¢n thá»§: RCON tá»«ng item lÃ  chÃ­nh, fallback PD API."""
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
            log_fn(f"âŒ {title}: danh sÃ¡ch item rá»—ng.")
            return False

        ok_count = 0
        for it in valid_items:
            iid = it["ItemID"]
            cnt = it["Count"]
            ok = self._rcon_give_item(playerid, steam_number, sid, iid, cnt)
            log_fn(f"{'âœ…' if ok else 'âŒ'} {title}: {iid} x{cnt} (RCON)")
            if ok:
                ok_count += 1

        # Chuáº©n giá»‘ng tÃ¢n thá»§: >=80% coi lÃ  Ä‘áº¡t
        if ok_count >= max(1, int(len(valid_items) * 0.8)):
            log_fn(f"ðŸŽ {title}: thÃ nh cÃ´ng {ok_count}/{len(valid_items)} (RCON).")
            return True

        # Fallback PD API Ä‘á»ƒ cá»©u trÆ°á»ng há»£p RCON miss cá»¥c bá»™.
        payload = {"Item": valid_items}
        ok_api = self._give_bundle_pdapi(sid, player_name, payload, f"{title} [fallback API]", log_fn=log_fn)
        if ok_api:
            log_fn(f"ðŸŽ {title}: RCON chÆ°a Ä‘á»§, API fallback Ä‘Ã£ xá»­ lÃ½.")
            return True
        log_fn(f"âŒ {title}: tháº¥t báº¡i (RCON {ok_count}/{len(valid_items)} + API fallback fail).")
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
            sid, player_name, self.daily_checkin_reward_items, "Äiá»ƒm danh háº±ng ngÃ y", log_fn=self._log_daily_gift
        )
        if ok:
            claimed.add(sid)
            self.daily_checkin_claims[today] = sorted(claimed)
            self._save_daily_checkin_tracking()
            self._enqueue_console(f"ðŸ“… Äiá»ƒm danh: {player_name or sid} nháº­n quÃ  ngÃ y {today}.")
            # Clear retry náº¿u cÃ³
            self._daily_retry_state.pop(sid, None)
        else:
            st = self._daily_retry_state.get(sid, {"attempts": 0, "next_ts": 0.0})
            if st["attempts"] < 5:
                st["attempts"] += 1
                st["next_ts"] = time.time() + 60
                self._daily_retry_state[sid] = st
                self._log_daily_gift(f"â³ Äiá»ƒm danh: sáº½ thá»­ láº¡i láº§n {st['attempts']}/5 sau 60s cho {player_name or sid}.")
            else:
                self._log_daily_gift(f"âŒ Äiá»ƒm danh: Ä‘Ã£ thá»­ 5 láº§n váº«n tháº¥t báº¡i cho {player_name or sid}.")

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
            sid, player_name, self.online60_reward_items, "QuÃ  online 60 phÃºt", log_fn=self._log_online_gift
        )
        if ok:
            st["accum_sec"] -= float(self.online60_reward_seconds)
            self._save_online60_tracking()
            self._enqueue_console(f"â±ï¸ QuÃ  60 phÃºt: {player_name or sid} Ä‘Ã£ nháº­n 1 lÆ°á»£t.")
            self._online_retry_state.pop(sid, None)
        else:
            rs = self._online_retry_state.get(sid, {"attempts": 0, "next_ts": 0.0})
            if rs["attempts"] < 5:
                rs["attempts"] += 1
                rs["next_ts"] = time.time() + 60
                self._online_retry_state[sid] = rs
                self._log_online_gift(f"â³ Online60: sáº½ thá»­ láº¡i láº§n {rs['attempts']}/5 sau 60s cho {player_name or sid}.")
            else:
                self._log_online_gift(f"âŒ Online60: Ä‘Ã£ thá»­ 5 láº§n váº«n tháº¥t báº¡i cho {player_name or sid}.")

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
        """Ghi log chi tiáº¿t vÃ o newbie_gift_log.txt."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)  # Ä‘áº£m báº£o thÆ° má»¥c tá»“n táº¡i
            ts     = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = ("âœ… THÃ€NH CÃ”NG" if success
                      else f"âš ï¸ PHáº¦N Lá»šN ({success_count}/{total})"
                      if success_count >= total * 0.8
                      else "âŒ THáº¤T Báº I")
            lines = [
                "=" * 62,
                f"[{ts}]  {status}",
                f"  TÃªn ingame : {name or '(khÃ´ng rÃµ)'}",
                f"  SteamID    : {steamid}",
                f"  PlayerID   : {playerid or '(khÃ´ng cÃ³)'}",
                f"  Káº¿t quáº£    : {success_count}/{total} item thÃ nh cÃ´ng",
                f"  Chi tiáº¿t   :",
            ]
            for r in item_results:
                lines.append(f"    {r}")
            lines.append("")
            with open(self.newbie_gift_log_file, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i ghi gift log file: {e}")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  GIVE NEWBIE GIFT
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _give_newbie_gift(self, steamid: str, player_name: str = ""):
        """PhÃ¡t toÃ n bá»™ quÃ  tÃ¢n thá»§ cho ngÆ°á»i chÆ¡i qua RCON."""
        if steamid in self.newbie_gift_received:
            self._enqueue_console(f"âš ï¸ {player_name or steamid} Ä‘Ã£ nháº­n quÃ  rá»“i, bá» qua.")
            return False

        playerid     = self._steamid_to_playerid.get(steamid, "")
        steam_number = steamid.replace("steam_", "") if steamid.startswith("steam_") else steamid
        tag          = player_name or steamid

        if not playerid:
            self._enqueue_console(f"âš ï¸ KhÃ´ng cÃ³ playerId cho {tag}, thá»­ steam_number...")

        gifts = []
        for g in self.newbie_gift_template:
            typ = str(g.get("Type", "item")).lower().strip()
            gid = str(g.get("ID", "")).strip()
            cnt = int(g.get("Count", 0) or 0)
            if typ in ("item", "pal") and gid and cnt > 0:
                gifts.append((typ, gid, cnt))
        if not gifts:
            self._enqueue_console("âŒ QuÃ  tÃ¢n thá»§ Ä‘ang trá»‘ng hoáº·c sai Ä‘á»‹nh dáº¡ng.")
            return False

        success_count = 0
        item_results  = []

        for gift_type, gift_id, qty in gifts:
            if gift_type == "pal":
                ok    = self._rcon_give_pal(playerid, steam_number, steamid, gift_id, level=qty)
                label = f"ðŸ¾ PAL  {gift_id} lv{qty}"
            else:
                ok    = self._rcon_give_item(playerid, steam_number, steamid, gift_id, qty)
                label = f"ðŸ“¦ ITEM {gift_id} x{qty}"

            if ok:
                success_count += 1
                item_results.append(f"âœ… {label}")
            else:
                item_results.append(f"âŒ {label}")

        ts_ui      = datetime.datetime.now().strftime("%H:%M:%S")
        overall_ok = (success_count == len(gifts) or success_count >= len(gifts) * 0.8)

        if overall_ok:
            self._save_newbie_gift_tracking(steamid)
            if success_count == len(gifts):
                msg = f"âœ… ÄÃ£ phÃ¡t Ä‘á»§ quÃ  tÃ¢n thá»§ cho {tag} ({steamid})"
            else:
                msg = (f"âœ… PhÃ¡t quÃ  tÃ¢n thá»§ {success_count}/{len(gifts)} cho {tag} ({steamid}) "
                       f"â€” thiáº¿u: {[r for r in item_results if r.startswith('âŒ')]}")
            self._enqueue_console(msg)
            self._log_gift(msg)
            self.send_ingame_broadcast(f"ðŸŽ {player_name or 'NgÆ°á»i chÆ¡i má»›i'} Ä‘Ã£ nháº­n quÃ  tÃ¢n thá»§!")
            self._write_gift_log_file(steamid, player_name, playerid, True,
                                      success_count, len(gifts), item_results)
            return True
        else:
            msg = (f"âŒ PhÃ¡t quÃ  tÃ¢n thá»§ tháº¥t báº¡i cho {tag} ({steamid}). "
                   f"ThÃ nh cÃ´ng: {success_count}/{len(gifts)}")
            self._enqueue_console(msg)
            self._log_gift(msg)
            self._write_gift_log_file(steamid, player_name, playerid, False,
                                      success_count, len(gifts), item_results)
            return False

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  NEWBIE GIFT MONITOR (background thread)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def newbie_gift_monitor(self):
        """Theo dÃµi ngÆ°á»i chÆ¡i má»›i vÃ  phÃ¡t quÃ  sau newbie_gift_wait_sec giÃ¢y."""
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

                    # Cáº­p nháº­t cache
                    if steamid and playerid:
                        self._steamid_to_playerid[steamid] = playerid
                    if steamid:
                        self._steamid_to_name[steamid] = name

                    if not steamid:
                        # SteamID chÆ°a resolve â†’ theo dÃµi qua playerId
                        if playerid:
                            online_ids.add(f"pid:{playerid}")
                            if playerid not in self._pending_no_steamid:
                                self._pending_no_steamid[playerid] = {"name": name, "since": now_ts}
                        continue

                    online_ids.add(steamid)

                    # Kiá»ƒm tra náº¿u Ä‘ang pending (tá»« láº§n trÆ°á»›c chÆ°a cÃ³ steamid)
                    if playerid and playerid in self._pending_no_steamid:
                        orig_since = self._pending_no_steamid.pop(playerid)["since"]
                        if steamid not in self.newbie_gift_received and \
                           steamid not in self.newbie_gift_pending:
                            self.newbie_gift_pending[steamid] = orig_since

                    # ThÃªm vÃ o pending náº¿u chÆ°a nháº­n
                    if steamid not in self.newbie_gift_received and \
                       steamid not in self.newbie_gift_pending:
                        self.newbie_gift_pending[steamid] = now_ts
                        self._enqueue_console(
                            f"ðŸ†• NgÆ°á»i chÆ¡i má»›i: {name} ({steamid}) â€” Ä‘ang chá» {self.newbie_gift_wait_sec}s"
                        )

                # PhÃ¡t quÃ  cho nhá»¯ng ai Ä‘Ã£ chá» Ä‘á»§ giá»
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
                # Server chÆ°a cháº¡y â†’ im láº·ng, khÃ´ng spam console
                pass
            except Exception as e:
                self._enqueue_console(f"âŒ Lá»—i monitor quÃ  tÃ¢n thá»§: {e}")

            time.sleep(5)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  LOG HELPER (UI console cá»§a tab quÃ )
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _log_gift(self, message: str):
        """Ghi message vÃ o newbie_gift_log console trong UI."""
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
        """Chia quá»¹ TOP10 thÃ nh N suáº¥t: ngáº«u nhiÃªn â€œÄ‘á»u tÆ°Æ¡ng Ä‘á»‘iâ€.
        Sá»­ dá»¥ng phÃ¢n phá»‘i tá»‰ lá»‡ (Dirichlet xáº¥p xá»‰ báº±ng Gamma) Ä‘á»ƒ táº¡o Ä‘á»™ ngáº«u nhiÃªn
        ngay cáº£ khi total chia háº¿t cho N.
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
            # Táº¡o trá»ng sá»‘ ngáº«u nhiÃªn â€œgáº§n Ä‘á»uâ€: Gamma(k=3, theta=1) cho n slot
            weights = [random.gammavariate(3.0, 1.0) for _ in range(n)]
            sum_w = sum(weights) or 1.0
            # PhÃ¢n bá»• sÆ¡ bá»™ theo tá»‰ lá»‡ vÃ  lÃ m trÃ²n xuá»‘ng
            alloc = [int((w / sum_w) * total) for w in weights]
            used = sum(alloc)
            # BÃ¹ pháº§n dÆ° Ä‘á»ƒ tá»•ng khá»›p total
            rem = max(0, total - used)
            if rem > 0:
                # Chá»n ngáº«u nhiÃªn 'rem' slot Ä‘á»ƒ +1
                for idx in random.sample(range(n), rem if rem <= n else n):
                    alloc[idx] += 1
                # Náº¿u váº«n cÃ²n dÆ° (rem > n), phÃ¢n phá»‘i thÃªm vÃ²ng sau
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
        """Gá»™p 2 map item -> count thÃ nh list payload item."""
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
        """GhÃ©p quÃ  top10 theo quy táº¯c:
        - Náº¿u ItemID trÃ¹ng giá»¯a daily vÃ  bonus -> cá»™ng daily + bonus
        - Náº¿u khÃ´ng trÃ¹ng -> chá»‰ láº¥y bonus (khÃ´ng cá»™ng daily)
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
        """Chá»‘t top20/top10 cá»§a ngÃ y Ä‘á»ƒ trÃ¡nh thay Ä‘á»•i giá»¯a ngÃ y."""
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
        """Top10 nháº­n thÆ°á»Ÿng theo cÃ´ng thá»©c:
        quÃ  cuá»‘i = quÃ  Ä‘iá»ƒm danh máº·c Ä‘á»‹nh + bonus random chia tá»« quá»¹ top10 theo 10 suáº¥t.
        force_test=True: cháº¡y test ngay, khÃ´ng ghi claim theo ngÃ y.
        """
        now_local = datetime.datetime.now()
        # Chá»‰ chá»‘t vÃ  phÃ¡t sau má»‘c 00:00 háº±ng ngÃ y.
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
            # Snapshot cá»‘ Ä‘á»‹nh theo ngÃ y: trÃ¡nh thay Ä‘á»•i top giá»¯a ngÃ y, trÃ¡nh thiáº¿u sÃ³t/trÃ¹ng.
            day_state = self.ranking_bonus_daily_state.get(today) or self._build_top10_bonus_snapshot_for_day(today)

        top20_set = set(self._normalize_steamid(x) for x in day_state.get("top20", []) if self._normalize_steamid(x))
        slots_rows = list(day_state.get("slots", []) or [])
        if not slots_rows:
            return {"awarded": 0, "total_top": 0}

        # Base daily máº·c Ä‘á»‹nh (vÃ­ dá»¥ Money 10000) Ã¡p cho má»—i ngÆ°á»i top10.
        base_daily_map = {}
        for it in (self.daily_checkin_reward_items or []):
            iid = str(it.get("ItemID", "")).strip()
            cnt = int(it.get("Count", 0) or 0)
            if iid and cnt > 0:
                base_daily_map[iid] = base_daily_map.get(iid, 0) + cnt

        online_set = set(getattr(self, "_online_players_prev", set()) or set())
        random.shuffle(slots_rows)  # random thá»© tá»± phÃ¡t, khÃ´ng random táº­p ngÆ°á»i.
        awarded = 0
        title = "TEST TOP10 bonus" if force_test else "ThÆ°á»Ÿng TOP10 Ranking"
        for row in slots_rows:
            sid = self._normalize_steamid(row.get("steamid", ""))
            name = self._steamid_to_name.get(sid, sid)
            if not sid or sid in claimed_today:
                continue
            if sid not in top20_set:
                self._log_ranking_bonus(f"â›” TOP10 bonus: bá» {name} vÃ¬ khÃ´ng thuá»™c top20 snapshot ngÃ y {today}.")
                continue
            if sid not in online_set:
                self._log_ranking_bonus(f"â­ï¸ TOP10 bonus: {name} offline, bá» qua lÆ°á»£t nÃ y.")
                continue
            bonus_items = self._merge_daily_bonus_by_same_code(base_daily_map, row.get("bonus", {}))
            if not bonus_items:
                self._log_ranking_bonus(f"â­ï¸ TOP10 bonus: {name} khÃ´ng cÃ³ suáº¥t item há»£p lá»‡.")
                continue
            ok = self._give_bundle_newbie_style(
                sid, name, bonus_items, title, log_fn=self._log_ranking_bonus
            )
            if ok:
                claimed_today.add(sid)
                awarded += 1
                bonus_txt = ", ".join(f"{it.get('ItemID')}x{it.get('Count')}" for it in bonus_items)
                self._log_ranking_bonus(f"   â†³ {name} nháº­n bonus: {bonus_txt}")

        if awarded > 0 and not force_test:
            self.ranking_bonus_claims[today] = sorted(claimed_today)
            self._save_ranking_bonus_claims()
            self._log_ranking_bonus(f"ðŸ† Bonus TOP10: Ä‘Ã£ phÃ¡t cho {awarded} ngÆ°á»i trong ngÃ y {today}.")
        elif force_test:
            self._log_ranking_bonus(f"ðŸ§ª TEST TOP10 xong: phÃ¡t thÃ nh cÃ´ng {awarded}/{len(slots_rows)} ngÆ°á»i.")
        return {"awarded": awarded, "total_top": len(slots_rows)}

    def _save_all_gift_tabs_config(self):
        newbie = self._newbie_template_from_text(self._newbie_reward_text.get("1.0", tk.END))
        daily = self._reward_items_from_text(self._daily_reward_text.get("1.0", tk.END))
        online = self._reward_items_from_text(self._online_reward_text.get("1.0", tk.END))
        if not newbie or not daily or not online:
            messagebox.showwarning("QuÃ  táº·ng", "Má»™t trong cÃ¡c tab quÃ  Ä‘ang trá»‘ng hoáº·c sai Ä‘á»‹nh dáº¡ng.")
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
            self._enqueue_console(f"âœ… ÄÃ£ lÆ°u cáº¥u hÃ¬nh quÃ : newbie/daily/online, má»‘c online {mins} phÃºt.")
            messagebox.showinfo("QuÃ  táº·ng", "ÄÃ£ lÆ°u cáº¥u hÃ¬nh quÃ  cho cáº£ 3 tab.")
        else:
            messagebox.showerror("QuÃ  táº·ng", "KhÃ´ng lÆ°u Ä‘Æ°á»£c cáº¥u hÃ¬nh.")

    def _gift_retry_loop(self):
        """Background: thá»­ láº¡i phÃ¡t quÃ  (Ä‘iá»ƒm danh/online) má»—i 5s, khi tá»›i háº¡n thÃ¬ attempt.
        Má»—i má»¥c tá»‘i Ä‘a 5 láº§n, cÃ¡ch nhau 60s â€” giá»‘ng cÆ¡ cháº¿ tÃ¢n thá»§."""
        while True:
            now = time.time()
            try:
                # Daily check-in retries
                for sid, st in list(self._daily_retry_state.items()):
                    if now >= float(st.get("next_ts", 0)):
                        name = self._steamid_to_name.get(sid, sid)
                        ok = self._give_bundle_newbie_style(
                            sid, name, self.daily_checkin_reward_items, "Äiá»ƒm danh háº±ng ngÃ y (retry)", log_fn=self._log_daily_gift
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
                                self._log_daily_gift(f"âŒ Äiá»ƒm danh (retry): Ä‘Ã£ Ä‘á»§ 5 láº§n â€” dá»«ng cho {name}.")
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
                            sid, name, self.online60_reward_items, "QuÃ  online 60 phÃºt (retry)", log_fn=self._log_online_gift
                        )
                        if ok:
                            st = self.online60_reward_state.setdefault(sid, {"accum_sec": 0.0, "last_seen": now})
                            st["accum_sec"] = max(0.0, float(st.get("accum_sec", 0.0)) - float(self.online60_reward_seconds))
                            self._save_online60_tracking()
                            self._online_retry_state.pop(sid, None)
                        else:
                            if rs.get("attempts", 0) >= 5:
                                self._log_online_gift(f"âŒ Online60 (retry): Ä‘Ã£ Ä‘á»§ 5 láº§n â€” dá»«ng cho {name}.")
                                self._online_retry_state.pop(sid, None)
                            else:
                                rs["attempts"] = int(rs.get("attempts", 0)) + 1
                                rs["next_ts"] = now + 60
                                self._online_retry_state[sid] = rs
            except Exception:
                pass
            time.sleep(5)

    def _save_online_reward_config_only(self):
        """LÆ°u riÃªng cáº¥u hÃ¬nh quÃ  online vÃ o manager_config.json."""
        online = self._reward_items_from_text(self._online_reward_text.get("1.0", tk.END))
        if not online:
            messagebox.showwarning("QuÃ  online", "Danh sÃ¡ch quÃ  online trá»‘ng hoáº·c sai Ä‘á»‹nh dáº¡ng.")
            return
        try:
            mins = max(1, int(self._online60_minutes_var.get().strip()))
        except Exception:
            mins = 60
        self.online60_reward_items = online
        self.online60_reward_seconds = mins * 60
        if self._save_reward_templates_to_cfg():
            self._enqueue_console(f"âœ… ÄÃ£ lÆ°u RIÃŠNG cáº¥u hÃ¬nh quÃ  online: {mins} phÃºt/lÆ°á»£t.")
            messagebox.showinfo(
                "QuÃ  online",
                "ÄÃ£ cáº­p nháº­t vÃ o manager_config.json:\n"
                "â€¢ ONLINE60_REWARD_ITEMS\n"
                "â€¢ ONLINE60_REWARD_SECONDS"
            )
        else:
            messagebox.showerror("QuÃ  online", "KhÃ´ng lÆ°u Ä‘Æ°á»£c cáº¥u hÃ¬nh quÃ  online.")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  TEST FUNCTIONS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _pick_online_player_for_gift_test(self):
        """Chá»n ngÆ°á»i chÆ¡i cá»¥ thá»ƒ Ä‘á»ƒ test quÃ  theo tÃªn/steamid (fallback ngÆ°á»i Ä‘áº§u tiÃªn)."""
        try:
            res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
            players = res.json().get("players", []) if res.status_code == 200 else []
        except Exception:
            players = []
        if not players:
            messagebox.showwarning("Gift Test", "KhÃ´ng cÃ³ ngÆ°á»i chÆ¡i online!")
            return None

        preview = ", ".join(str(p.get("name", "?")) for p in players[:8])
        q = simpledialog.askstring(
            "Chá»n ngÆ°á»i chÆ¡i test",
            "Nháº­p TÃŠN hoáº·c STEAMID Ä‘á»ƒ test Ä‘Ãºng ngÆ°á»i.\n"
            "Äá»ƒ trá»‘ng = chá»n ngÆ°á»i Ä‘áº§u tiÃªn online.\n\n"
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
            messagebox.showwarning("Gift Test", f"NgÆ°á»i chÆ¡i {name} chÆ°a cÃ³ SteamID há»£p lá»‡!")
            return None
        return {"steamid": steamid, "playerid": playerid, "name": name}

    def test_gift_second_time(self):
        """TEST 1: Kiá»ƒm tra xem ngÆ°á»i chÆ¡i CÃ“ THá»‚ nháº­n quÃ  láº§n 2 khÃ´ng."""
        p = self._pick_online_player_for_gift_test()
        if not p:
            return
        steamid = p["steamid"]
        name = p["name"]

        if steamid not in self.newbie_gift_received:
            ans = messagebox.askyesno("TEST 1",
                f"NgÆ°á»i chÆ¡i {name} ({steamid}) CHÆ¯A nháº­n quÃ .\n"
                f"Thá»­ phÃ¡t quÃ  láº§n Ä‘áº§u (giáº£ láº­p monitor) khÃ´ng?")
            if ans:
                self._log_gift(f"ðŸ§ª TEST 1: PhÃ¡t quÃ  láº§n Ä‘áº§u cho {name} ({steamid})...")
                threading.Thread(target=self._give_newbie_gift, args=(steamid, name), daemon=True).start()
            return

        ans = messagebox.askyesno("TEST 1 - XÃ¡c nháº­n",
            f"NgÆ°á»i chÆ¡i {name} ({steamid}) ÄÃƒ nháº­n quÃ .\n\n"
            f"Táº¡m xÃ³a khá»i tracking Ä‘á»ƒ thá»­ phÃ¡t láº§n 2?\n"
            f"(Sáº½ Tá»° Äá»˜NG khÃ´i phá»¥c sau khi test xong)")
        if not ans:
            return

        self._log_gift(f"ðŸ§ª TEST 1 Báº®T Äáº¦U: Táº¡m xÃ³a {name} ({steamid}) khá»i tracking...")
        self.newbie_gift_received.discard(steamid)

        def _do_test():
            ok = self._give_newbie_gift(steamid, name)
            # KhÃ´i phá»¥c tracking dÃ¹ káº¿t quáº£ tháº¿ nÃ o
            self.newbie_gift_received.add(steamid)
            result = "âœ… THÃ€NH CÃ”NG â€” cÃ³ thá»ƒ nháº­n láº§n 2" if ok else "âŒ THáº¤T Báº I â€” RCON lá»—i"
            self._log_gift(f"ðŸ§ª TEST 1 Káº¾T QUáº¢: {result}")
            self._log_gift(f"   Tracking Ä‘Ã£ khÃ´i phá»¥c cho {steamid}")
            messagebox.showinfo("TEST 1 - Káº¿t quáº£", f"Káº¿t quáº£: {result}")

        threading.Thread(target=_do_test, daemon=True).start()

    def test_gift_give_all(self):
        """TEST 2: Give toÃ n bá»™ item quÃ  tÃ¢n thá»§ vÃ  kiá»ƒm tra tá»«ng item."""
        p = self._pick_online_player_for_gift_test()
        if not p:
            return
        steamid = p["steamid"]
        playerid = p["playerid"]
        name = p["name"]

        already = steamid in self.newbie_gift_received
        ans = messagebox.askyesno("TEST 2 - XÃ¡c nháº­n",
            f"PhÃ¡t TOÃ€N Bá»˜ quÃ  tÃ¢n thá»§ cho:\n"
            f"  TÃªn    : {name}\n"
            f"  Steam  : {steamid}\n"
            f"  Player : {playerid or '(chÆ°a cÃ³)'}\n\n"
            f"{'âš ï¸ NgÆ°á»i chÆ¡i NÃ€Y ÄÃƒ nháº­n quÃ  trÆ°á»›c Ä‘Ã³!' if already else 'ðŸ†• NgÆ°á»i chÆ¡i chÆ°a nháº­n quÃ .'}\n"
            f"Tiáº¿p tá»¥c?")
        if not ans:
            return

        self._log_gift(f"ðŸŽ TEST 2 Báº®T Äáº¦U: Give toÃ n bá»™ cho {name} | steam={steamid} | pid={playerid}")

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
                    label = f"ðŸ¾ PAL  {gift_id} lv{qty}"
                else:
                    ok    = self._rcon_give_item(playerid, steam_number, steamid, gift_id, qty)
                    label = f"ðŸ“¦ ITEM {gift_id} x{qty}"
                ico = "âœ…" if ok else "âŒ"
                results.append(f"{ico} {label}")
                if ok:
                    ok_count += 1
                self._log_gift(f"  {ico} {label}")

            summary = f"{ok_count}/{len(gifts)} thÃ nh cÃ´ng"
            self._log_gift(f"ðŸŽ TEST 2 Káº¾T QUáº¢: {summary}")
            self._write_gift_log_file(steamid, name, playerid,
                                      ok_count == len(gifts), ok_count, len(gifts), results)
            if not already and ok_count >= len(gifts) * 0.8:
                self._save_newbie_gift_tracking(steamid)
                self._log_gift(f"   âœ… ÄÃ£ lÆ°u {steamid} vÃ o tracking")

            detail = "\n".join(results)
            messagebox.showinfo("TEST 2 - Káº¿t quáº£", f"Káº¿t quáº£ {summary}:\n\n{detail}")

        threading.Thread(target=_do_test, daemon=True).start()

    def test_daily_checkin_specific(self):
        """TEST 3: PhÃ¡t quÃ  Ä‘iá»ƒm danh cho ngÆ°á»i chÆ¡i cá»¥ thá»ƒ (bá» qua tráº¡ng thÃ¡i Ä‘Ã£ nháº­n trong ngÃ y)."""
        p = self._pick_online_player_for_gift_test()
        if not p:
            return
        sid = p["steamid"]
        name = p["name"]
        ans = messagebox.askyesno(
            "TEST 3 - Äiá»ƒm danh",
            f"PhÃ¡t TEST quÃ  Ä‘iá»ƒm danh cho:\n  {name} ({sid})\n\n"
            "LÆ°u Ã½: Ä‘Ã¢y lÃ  test thá»§ cÃ´ng, cÃ³ thá»ƒ cáº¥p thÃªm quÃ  ngoÃ i lÆ°á»£t Ä‘iá»ƒm danh tá»± Ä‘á»™ng."
        )
        if not ans:
            return
        threading.Thread(
            target=lambda: self._give_bundle_newbie_style(
                sid, name, self.daily_checkin_reward_items, "TEST Äiá»ƒm danh háº±ng ngÃ y", log_fn=self._log_daily_gift
            ),
            daemon=True
        ).start()

    def test_online60_specific(self):
        """TEST 4: PhÃ¡t quÃ  online 60 phÃºt cho ngÆ°á»i chÆ¡i cá»¥ thá»ƒ."""
        p = self._pick_online_player_for_gift_test()
        if not p:
            return
        sid = p["steamid"]
        name = p["name"]
        ans = messagebox.askyesno(
            "TEST 4 - Online 60 phÃºt",
            f"PhÃ¡t TEST quÃ  online 60 phÃºt cho:\n  {name} ({sid})\n\n"
            "LÆ°u Ã½: Ä‘Ã¢y lÃ  test thá»§ cÃ´ng, khÃ´ng cáº§n Ä‘á»§ 60 phÃºt."
        )
        if not ans:
            return
        threading.Thread(
            target=lambda: self._give_bundle_newbie_style(
                sid, name, self.online60_reward_items, "TEST QuÃ  online 60 phÃºt", log_fn=self._log_online_gift
            ),
            daemon=True
        ).start()

    def test_top10_bonus_now(self):
        """TEST 5: Cháº¡y ngay thÆ°á»Ÿng Top10 bonus chia Ä‘á»u ngáº«u nhiÃªn (khÃ´ng ghi claim ngÃ y)."""
        ans = messagebox.askyesno(
            "TEST 5 - TOP10 Bonus",
            "Cháº¡y TEST TOP10 bonus ngay bÃ¢y giá»?\n\n"
            "- Chá»‰ phÃ¡t cho ngÆ°á»i trong TOP10 Ä‘ang online\n"
            "- Chia quá»¹ top10 theo 10 suáº¥t (ngáº«u nhiÃªn pháº§n dÆ°)\n"
            "- KhÃ´ng ghi claim theo ngÃ y (cháº¿ Ä‘á»™ test)"
        )
        if not ans:
            return

        def _do():
            rs = self._award_top10_bonus_if_due(force_test=True) or {}
            self._log_ranking_bonus(
                f"ðŸ§ª TEST TOP10: káº¿t quáº£ {rs.get('awarded', 0)}/{rs.get('total_top', 0)} ngÆ°á»i nháº­n."
            )

        threading.Thread(target=_do, daemon=True).start()

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  LOG FILE HELPERS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _refresh_gift_stats(self):
        """Cáº­p nháº­t stats label má»—i 3 giÃ¢y."""
        try:
            if hasattr(self, "_lbl_gift_stat_received") and \
               self._lbl_gift_stat_received.winfo_exists():
                self._lbl_gift_stat_received.config(
                    text=f"âœ… ÄÃ£ phÃ¡t: {len(self.newbie_gift_received)} ngÆ°á»i")
                self._lbl_gift_stat_pending.config(
                    text=f"â³ Äang chá»: {len(self.newbie_gift_pending)} ngÆ°á»i")
                self.root.after(3000, self._refresh_gift_stats)
        except Exception:
            pass

    def _open_gift_log_file(self):
        """Má»Ÿ file log chi tiáº¿t báº±ng Notepad (táº¡o file náº¿u chÆ°a cÃ³)."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            if not os.path.isfile(self.newbie_gift_log_file):
                with open(self.newbie_gift_log_file, "w", encoding="utf-8") as f:
                    f.write(f"# LOG QUÃ€ TÃ‚N THá»¦ - MANAGER SERVERPAL\n")
                    f.write(f"# Táº¡o lÃºc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            os.startfile(self.newbie_gift_log_file)
        except Exception as e:
            messagebox.showerror("Lá»—i", f"KhÃ´ng thá»ƒ má»Ÿ file log: {e}")

    def _open_any_log_file(self, path: str, title: str = "LOG"):
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            if not os.path.isfile(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n# Táº¡o lÃºc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Lá»—i", f"KhÃ´ng thá»ƒ má»Ÿ file log: {e}")

    def _open_gift_log_folder(self):
        """Má»Ÿ Explorer táº¡i thÆ° má»¥c quatanthu, highlight file log."""
        try:
            os.makedirs(GIFT_SAVE_DIR, exist_ok=True)
            if os.path.isfile(self.newbie_gift_log_file):
                subprocess.Popen(f'explorer /select,"{self.newbie_gift_log_file}"')
            else:
                subprocess.Popen(f'explorer "{GIFT_SAVE_DIR}"')
        except Exception as e:
            messagebox.showerror("Lá»—i", f"KhÃ´ng thá»ƒ má»Ÿ thÆ° má»¥c: {e}")

    def _load_gift_log_to_ui(self):
        """Táº£i 200 dÃ²ng cuá»‘i cá»§a file log vÃ o console UI."""
        if not hasattr(self, "newbie_gift_log"):
            return
        try:
            if not os.path.isfile(self.newbie_gift_log_file):
                self.newbie_gift_log.insert(tk.END, "(ChÆ°a cÃ³ lá»‹ch sá»­ phÃ¡t quÃ )\n")
                return
            with open(self.newbie_gift_log_file, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-200:] if len(lines) > 200 else lines
            self.newbie_gift_log.delete("1.0", tk.END)
            if len(lines) > 200:
                self.newbie_gift_log.insert(
                    tk.END,
                    f"--- (hiá»ƒn thá»‹ 200 dÃ²ng cuá»‘i / tá»•ng {len(lines)} dÃ²ng) ---\n\n"
                )
            for line in tail:
                self.newbie_gift_log.insert(tk.END, line)
            self.newbie_gift_log.see(tk.END)
        except Exception as e:
            self.newbie_gift_log.insert(tk.END, f"âŒ Lá»—i Ä‘á»c log: {e}\n")

    def _load_any_log_to_ui(self, path: str, target_widget):
        if not target_widget or not target_widget.winfo_exists():
            return
        try:
            if not os.path.isfile(path):
                target_widget.delete("1.0", tk.END)
                target_widget.insert(tk.END, "(ChÆ°a cÃ³ lá»‹ch sá»­)\n")
                return
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-200:] if len(lines) > 200 else lines
            target_widget.delete("1.0", tk.END)
            if len(lines) > 200:
                target_widget.insert(tk.END, f"--- (200 dÃ²ng cuá»‘i / tá»•ng {len(lines)} dÃ²ng) ---\n\n")
            for line in tail:
                target_widget.insert(tk.END, line)
            target_widget.see(tk.END)
        except Exception as e:
            target_widget.insert(tk.END, f"âŒ Lá»—i Ä‘á»c log: {e}\n")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  PLAYER TREE REFRESH
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _refresh_players_tree(self):
        """Láº¥y dá»¯ liá»‡u players tá»« API, cáº­p nháº­t cache vÃ  rebuild tree."""
        if not hasattr(self, "player_tree") or not self.player_tree.winfo_exists():
            return
        try:
            res = requests.get(f"{API_URL}/players", auth=AUTH, timeout=5)
            if res.status_code != 200:
                return
            players = res.json().get("players", [])
            # Cáº­p nháº­t steamid â†’ playerid vÃ  level cache
            for p in players:
                sid = self._normalize_steamid(p.get("userId", ""))
                pid = p.get("playerId", "")
                if sid and pid:
                    self._steamid_to_playerid[sid] = pid
                if sid:
                    lv = int(p.get("level") or 0)
                    if lv > 0:
                        self._player_level_cache[sid] = lv
            # LÆ°u cache
            self._all_players_data = players
            # Cáº­p nháº­t label sá»‘ lÆ°á»£ng
            count = len(players)
            if hasattr(self, "_lbl_player_count") and \
               self._lbl_player_count.winfo_exists():
                if count > 0:
                    self._lbl_player_count.config(
                        text=f"  â¬¤ {count} online", fg="#00ff88")
                else:
                    self._lbl_player_count.config(
                        text="  â¬¤ 0 online", fg="#555")
            # Rebuild tree (Ã¡p dá»¥ng filter + sort hiá»‡n táº¡i)
            self._filter_player_tree()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout):
            # Server chÆ°a cháº¡y â†’ im láº·ng
            pass
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i refresh players: {e}")
        # Auto-refresh
        try:
            if self.player_tree.winfo_exists() and \
               getattr(self, "_player_auto_var",
                       tk.BooleanVar(value=True)).get():
                self.root.after(8000, self._refresh_players_tree)
        except Exception:
            pass

    def _filter_player_tree(self):
        """Lá»c + rebuild Treeview tá»« cache, Ã¡p dá»¥ng search + sort."""
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
            "TÃªn":  lambda p: p.get("name", "").lower(),
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
                ping_disp = f"{float(ping_raw):.0f}" if ping_raw != "" else "â€”"
            except Exception:
                ping_disp = str(ping_raw) if ping_raw else "â€”"

            # Level badge + color tag
            lv_tag = ("lv_max"  if level >= 50 else
                      "lv_high" if level >= 35 else
                      "lv_mid"  if level >= 20 else
                      "lv_new")
            lv_disp = f"Lv.{level}" if level > 0 else "â€”"

            iid = self.player_tree.insert(
                "", tk.END,
                values=(idx, name, lv_disp, ping_disp,
                        steamid or "â³", playerid or "â³", ip_raw or "â€”"),
                tags=(lv_tag,)
            )
            self._players_by_iid[iid] = p

    # â”€â”€ Player tab helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _player_on_select(self, event=None):
        """Cáº­p nháº­t action panel khi chá»n má»™t player."""
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
            coord_txt = f"   ðŸ“ ({loc_x:.0f}, {loc_y:.0f})"
        lv_color = ("#ffcc00" if level >= 50 else
                    "#4499ff" if level >= 35 else
                    "#00cc88" if level >= 20 else "#888")
        self._lbl_selected_player.config(
            text=f"â–¶  {name}   Lv.{level}   â€¢   {sid}{coord_txt}",
            fg=lv_color
        )

    def _player_get_selected(self):
        """Tráº£ vá» dict cá»§a player Ä‘ang Ä‘Æ°á»£c chá»n, hoáº·c None."""
        sel = self.player_tree.selection()
        if not sel:
            return None
        return self._players_by_iid.get(sel[0])

    def _player_kick_selected(self):
        p = self._player_get_selected()
        if not p:
            messagebox.showwarning("Kick", "Chá»n ngÆ°á»i chÆ¡i trong danh sÃ¡ch trÆ°á»›c!")
            return
        name = p.get("name", "?")
        sid  = self._normalize_steamid(p.get("userId", ""))
        lv   = int(p.get("level") or 0)
        if not sid:
            messagebox.showerror("Kick", "KhÃ´ng tÃ¬m tháº¥y SteamID!")
            return
        if not messagebox.askyesno(
                "âš¡ Kick Confirmation",
                f"Kick ngÆ°á»i chÆ¡i:\n\n  {name}  (Lv.{lv})\n  {sid}\n\nXÃ¡c nháº­n?"):
            return

        def _do():
            ok, code = self._api_kick(sid, "Kicked by admin")
            self._enqueue_console(
                f"{'âœ…' if ok else 'âŒ'} KICK {name} [{sid}] â€” HTTP {code}")
        threading.Thread(target=_do, daemon=True).start()

    def _player_ban_selected(self, source: str = "PLAYER_TAB"):
        p = self._player_get_selected()
        if not p:
            messagebox.showwarning("Ban", "Chá»n ngÆ°á»i chÆ¡i trÆ°á»›c!")
            return
        name = p.get("name", "?")
        sid  = self._normalize_steamid(p.get("userId", ""))
        lv   = int(p.get("level") or 0)
        if not sid:
            messagebox.showerror("Ban", "KhÃ´ng tÃ¬m tháº¥y SteamID!")
            return
        reason = simpledialog.askstring(
            "â›” Ban Player",
            f"LÃ½ do ban {name} (Lv.{lv})?\n{sid}",
            initialvalue="Admin ban"
        )
        if reason is None:
            return

        def _do():
            ok, code = self._api_ban(sid, reason)
            ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            api_status = f"âœ… ÄÃ£ XÃ¡c Minh âœ… {code}" if ok else f"âŒ HTTP {code}"

            # Ghi chung vÃ o banlist.txt Ä‘á»ƒ Ä‘á»“ng bá»™ vá»›i luá»“ng AntiBug/Unban.
            try:
                with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                    f.write(
                        f"\n{'â”€'*60}\n"
                        f"  [BAN â€” MANUAL]  {ts_now}\n"
                        f"  Name         : {name}\n"
                        f"  SteamID      : {sid}\n"
                        f"  Level        : {lv}\n"
                        f"  Reason       : {reason}\n"
                        f"  Source       : {source}\n"
                        f"  API Ban      : {api_status}\n"
                        f"{'â”€'*60}\n\n"
                    )
            except Exception as e:
                self._enqueue_console(f"âŒ Lá»—i ghi banlist.txt (manual ban): {e}")

            # LuÃ´n gá»­i Discord khi ban thá»§ cÃ´ng tá»« tab ngÆ°á»i chÆ¡i / click pháº£i.
            threading.Thread(
                target=self._send_antibug_discord,
                args=(f"â›” **[BAN THá»¦ CÃ”NG]**\n"
                      f"ðŸ‘¤ **NgÆ°á»i chÆ¡i:** `{name}`\n"
                      f"ðŸ†” **SteamID:** `{sid}`\n"
                      f"â­ **Cáº¥p Ä‘á»™:** `{lv}`\n"
                      f"ðŸ“ **LÃ½ do:** `{reason}`\n"
                      f"ðŸ“ **Nguá»“n thao tÃ¡c:** `{source}`\n"
                      f"ðŸ• **Thá»i gian:** `{ts_now}`\n"
                      f"ðŸŒ **Káº¿t quáº£ tháº©m phÃ¡n ban:** {api_status}",),
                daemon=True
            ).start()

            self._enqueue_console(
                f"{'âœ…' if ok else 'âŒ'} BAN {name} [{sid}] â€” HTTP {code} â€” LÃ½ do: {reason} â€” Source: {source}")
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

    # â”€â”€ Give Item dialog â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _player_give_item_dialog(self):
        p = self._player_get_selected()
        if not p:
            messagebox.showwarning("Give Item", "Chá»n ngÆ°á»i chÆ¡i trÆ°á»›c!")
            return
        name = p.get("name", "?")
        sid  = self._normalize_steamid(p.get("userId", ""))
        if not sid:
            messagebox.showerror("Give Item", "KhÃ´ng tÃ¬m tháº¥y SteamID!")
            return

        win = tk.Toplevel(self.root)
        win.title(f"ðŸŽ Give Item â†’ {name}")
        win.geometry("780x620")
        win.configure(bg="#0a0a0a")
        win.resizable(True, True)
        win.grab_set()

        # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr = tk.Frame(win, bg="#111827", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸŽ  GIVE ITEM",
                 bg="#111827", fg="#00ffcc",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)
        tk.Label(hdr, text=f"â†’  {name}  [{sid}]",
                 bg="#111827", fg="#888",
                 font=("Segoe UI", 9)).pack(side="left")

        # â”€â”€ Toolbar: search + category â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        bar = tk.Frame(win, bg="#0d1117", pady=6)
        bar.pack(fill="x", padx=8)

        tk.Label(bar, text="ðŸ”", bg="#0d1117", fg="#666",
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
        tk.Label(bar, text="Danh má»¥c:", bg="#0d1117", fg="#888",
                 font=("Segoe UI", 9)).pack(side="left")
        cat_cb = ttk.Combobox(bar, textvariable=cat_var,
                              values=categories, state="readonly",
                              width=14, font=("Segoe UI", 9))
        cat_cb.pack(side="left", padx=(4, 0), ipady=3)

        # â”€â”€ Item list (Treeview) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        item_tree.heading("name", text="TÃªn váº­t pháº©m")
        item_tree.heading("id",   text="Blueprint ID")
        item_tree.heading("cat",  text="Danh má»¥c")
        item_tree.column("icon", width=32,  anchor="center", stretch=False)
        item_tree.column("name", width=210, anchor="w")
        item_tree.column("id",   width=210, anchor="w")
        item_tree.column("cat",  width=110, anchor="center")

        vsb2 = ttk.Scrollbar(list_f, orient="vertical", command=item_tree.yview)
        item_tree.configure(yscrollcommand=vsb2.set)
        item_tree.pack(side="left", fill="both", expand=True)
        vsb2.pack(side="right", fill="y")

        # â”€â”€ Populate function â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        def _populate(query="", cat="All"):
            item_tree.delete(*item_tree.get_children())
            q = query.lower()
            for idx, (c, dn, bid, em) in enumerate(_PW_ITEMS):
                if cat != "All" and c != cat:
                    continue
                if q and q not in dn.lower() and q not in bid.lower():
                    continue
                # iid pháº£i unique; dÃ¹ng bid__idx Ä‘á»ƒ trÃ¡nh crash khi dá»¯ liá»‡u cÃ³ ID trÃ¹ng.
                item_tree.insert("", tk.END, iid=f"{bid}__{idx}",
                                 values=(em, dn, bid, c))

        _populate()

        search_var.trace("w", lambda *_: _populate(search_var.get(), cat_var.get()))
        cat_var.trace("w",    lambda *_: _populate(search_var.get(), cat_var.get()))

        # Double-click â†’ fill ID field below
        def _on_double(event):
            sel = item_tree.selection()
            if sel:
                qty_entry.delete(0, tk.END)
                qty_entry.insert(0, "1")
                manual_id.delete(0, tk.END)
                manual_id.insert(0, item_tree.item(sel[0], "values")[2])  # cá»™t id

        item_tree.bind("<Double-1>", _on_double)
        item_tree.bind("<Return>",   _on_double)

        # â”€â”€ Bottom panel: qty + manual ID + give â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        bot = tk.Frame(win, bg="#0d1117", pady=10)
        bot.pack(fill="x", padx=8, pady=(4, 8))

        tk.Label(bot, text="Blueprint ID:", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 4))
        manual_id = tk.Entry(bot, bg="#1a1a2e", fg="#00ffcc", bd=0,
                             font=("Consolas", 10), insertbackground="#00ffcc",
                             width=26)
        manual_id.grid(row=0, column=1, ipady=5, padx=(0, 12))

        tk.Label(bot, text="Sá»‘ lÆ°á»£ng:", bg="#0d1117", fg="#aaa",
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
            tk.Button(preset_f, text=f"Ã—{qty_val}",
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
                status_lbl.configure(text="âš ï¸ Chá»n váº­t pháº©m hoáº·c nháº­p Blueprint ID!", fg="#ffa500")
                return
            try:
                qty = max(1, int(qty_entry.get().strip() or "1"))
            except ValueError:
                status_lbl.configure(text="âš ï¸ Sá»‘ lÆ°á»£ng khÃ´ng há»£p lá»‡!", fg="#ffa500")
                return

            status_lbl.configure(text=f"â³ Äang gá»­i {bid} Ã— {qty} qua RCON...", fg="#ffa500")
            give_btn.configure(state="disabled")

            def _bg():
                # Láº¥y playerid + steam_number â€” giá»‘ng cÆ¡ cháº¿ quÃ  tÃ¢n thá»§
                playerid     = p.get("playerId", "")
                steam_number = (sid.replace("steam_", "")
                                if sid.startswith("steam_") else sid)

                # BÆ°á»›c 1: RCON give (cÆ¡ cháº¿ Ä‘Ã£ kiá»ƒm chá»©ng qua quÃ  tÃ¢n thá»§)
                rcon_ok = self._rcon_give_item(playerid, steam_number, sid, bid, qty)
                if rcon_ok:
                    msg = f"âœ… Give OK (RCON): {name} â† {bid} Ã— {qty}"
                    self.root.after(0, lambda: status_lbl.configure(text=msg, fg="#00ff88"))
                else:
                    # BÆ°á»›c 2: Fallback PD API
                    pd_ok, data = self._pdapi_give(
                        sid, {"Item": [{"ItemID": bid, "Count": qty}]})
                    if pd_ok:
                        msg = f"âœ… Give OK (PD API): {name} â† {bid} Ã— {qty}"
                        self.root.after(0, lambda: status_lbl.configure(text=msg, fg="#00ff88"))
                    else:
                        errs = data.get("Error", data.get("error", str(data)))
                        msg = f"âŒ Give FAIL (RCON+PD): {bid} Ã— {qty} â€” {errs}"
                        self.root.after(0, lambda: status_lbl.configure(text=msg, fg="#ff5555"))
                self._enqueue_console(f"ðŸŽ {msg}")
                self.root.after(0, lambda: give_btn.configure(state="normal"))
            threading.Thread(target=_bg, daemon=True).start()

        give_btn = tk.Button(bot, text="  ðŸŽ GIVE  ",
                             bg="#00aa55", fg="white", relief="flat",
                             padx=18, pady=6, font=("Segoe UI", 10, "bold"),
                             command=_do_give)
        give_btn.grid(row=0, column=4, padx=(0, 8))

        tk.Button(bot, text="âœ– ÄÃ³ng",
                  bg="#2a0000", fg="#ff7777", relief="flat",
                  padx=10, pady=6, font=("Segoe UI", 9),
                  command=win.destroy).grid(row=0, column=5)

        # Focus search
        search_entry.focus_set()
        # Click row â†’ fill ID
        def _on_select(event):
            sel = item_tree.selection()
            if sel:
                manual_id.delete(0, tk.END)
                manual_id.insert(0, item_tree.item(sel[0], "values")[2])
        item_tree.bind("<<TreeviewSelect>>", _on_select)

    # â”€â”€ Give Pal dialog â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _player_give_pal_dialog(self):
        p = self._player_get_selected()
        if not p:
            messagebox.showwarning("Give Pal", "Chá»n ngÆ°á»i chÆ¡i trÆ°á»›c!")
            return
        name = p.get("name", "?")
        sid  = self._normalize_steamid(p.get("userId", ""))
        if not sid:
            messagebox.showerror("Give Pal", "KhÃ´ng tÃ¬m tháº¥y SteamID!")
            return

        win = tk.Toplevel(self.root)
        win.title(f"ðŸ¾ Give Pal â†’ {name}")
        win.geometry("760x580")
        win.configure(bg="#0a0a0a")
        win.resizable(True, True)
        win.grab_set()

        # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr = tk.Frame(win, bg="#111827", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸ¾  GIVE PAL",
                 bg="#111827", fg="#a78bfa",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)
        tk.Label(hdr, text=f"â†’  {name}  [{sid}]",
                 bg="#111827", fg="#888",
                 font=("Segoe UI", 9)).pack(side="left")

        # â”€â”€ Search + Element filter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        bar = tk.Frame(win, bg="#0d1117", pady=6)
        bar.pack(fill="x", padx=8)

        tk.Label(bar, text="ðŸ”", bg="#0d1117", fg="#666",
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

        # â”€â”€ Pal Treeview â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        pal_tree.heading("name",    text="TÃªn Pal")
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

        # â”€â”€ Bottom: pal_id field + level + give â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                pal_status.configure(text="âš ï¸ Chá»n pal hoáº·c nháº­p Pal ID!", fg="#ffa500")
                return
            try:
                lv = max(1, int(lv_entry.get().strip() or "1"))
            except ValueError:
                pal_status.configure(text="âš ï¸ Level khÃ´ng há»£p lá»‡!", fg="#ffa500")
                return

            pal_status.configure(text=f"â³ Äang gá»­i {pid_val} Lv.{lv} qua RCON...", fg="#ffa500")
            give_pal_btn.configure(state="disabled")

            def _bg():
                # Láº¥y playerid + steam_number â€” giá»‘ng cÆ¡ cháº¿ quÃ  tÃ¢n thá»§
                playerid     = p.get("playerId", "")
                steam_number = (sid.replace("steam_", "")
                                if sid.startswith("steam_") else sid)

                # BÆ°á»›c 1: RCON givepal (cÆ¡ cháº¿ Ä‘Ã£ kiá»ƒm chá»©ng qua quÃ  tÃ¢n thá»§)
                rcon_ok = self._rcon_give_pal(playerid, steam_number, sid, pid_val, lv)
                if rcon_ok:
                    msg = f"âœ… Give Pal OK (RCON): {name} â† {pid_val} Lv.{lv}"
                    self.root.after(0, lambda: pal_status.configure(text=msg, fg="#00ff88"))
                else:
                    # BÆ°á»›c 2: Fallback PD API
                    pd_ok, data = self._pdapi_give(
                        sid, {"Pal": [{"PalID": pid_val, "Level": lv}]})
                    if pd_ok:
                        msg = f"âœ… Give Pal OK (PD API): {name} â† {pid_val} Lv.{lv}"
                        self.root.after(0, lambda: pal_status.configure(text=msg, fg="#00ff88"))
                    else:
                        errs = data.get("Error", data.get("error", str(data)))
                        msg = f"âŒ Give Pal FAIL (RCON+PD): {pid_val} Lv.{lv} â€” {errs}"
                        self.root.after(0, lambda: pal_status.configure(text=msg, fg="#ff5555"))
                self._enqueue_console(f"ðŸ¾ {msg}")
                self.root.after(0, lambda: give_pal_btn.configure(state="normal"))
            threading.Thread(target=_bg, daemon=True).start()

        give_pal_btn = tk.Button(bot2, text="  ðŸ¾ GIVE PAL  ",
                                 bg="#7c3aed", fg="white", relief="flat",
                                 padx=16, pady=6, font=("Segoe UI", 10, "bold"),
                                 command=_do_give_pal)
        give_pal_btn.grid(row=0, column=4, padx=(0, 8))

        tk.Button(bot2, text="âœ– ÄÃ³ng",
                  bg="#2a0000", fg="#ff7777", relief="flat",
                  padx=10, pady=6, font=("Segoe UI", 9),
                  command=win.destroy).grid(row=0, column=5)

        # Select â†’ fill ID
        def _pal_select(event):
            sel = pal_tree.selection()
            if sel:
                vals = pal_tree.item(sel[0], "values")
                if vals:
                    manual_pal.delete(0, tk.END)
                    manual_pal.insert(0, vals[3])   # pal_id column
        pal_tree.bind("<<TreeviewSelect>>", _pal_select)
        pal_tree.bind("<Double-1>", lambda e: _do_give_pal())

        # â”€â”€ IV Calc button â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        def _open_iv_calc():
            pid = manual_pal.get().strip()
            if not pid:
                sel = pal_tree.selection()
                if sel:
                    vals = pal_tree.item(sel[0], "values")
                    pid = vals[3] if vals else ""
            # Truyá»n thÃªm player context Ä‘á»ƒ cho phÃ©p Give Pal with IVs
            player_ctx = {
                "name":         name,
                "steamid":      sid,
                "playerid":     p.get("playerId", ""),
                "steam_number": (sid.replace("steam_", "")
                                 if sid.startswith("steam_") else sid),
            }
            self._iv_calc_dialog(preset_pal_id=pid, player_ctx=player_ctx)

        tk.Button(bot2, text="ðŸ“Š IV Calc",
                  bg="#0e7490", fg="white", relief="flat",
                  padx=10, pady=6, font=("Segoe UI", 9, "bold"),
                  command=_open_iv_calc).grid(row=0, column=6, padx=(8, 0))

        pal_entry.focus_set()

    # â”€â”€ IV Calculator Dialog â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _iv_calc_dialog(self, preset_pal_id: str = "", player_ctx: dict = None):
        """Má»Ÿ cá»­a sá»• IV Calculator (Independent Variable / Chá»‰ sá»‘ cÃ¡ thá»ƒ).
        CÃ´ng thá»©c tá»«: paldb.cc/en/Iv_Calc
        player_ctx: dict vá»›i keys name/steamid/playerid/steam_number (náº¿u má»Ÿ tá»« Give Pal)
        """
        win = tk.Toplevel(self.root)
        _has_player = bool(player_ctx and player_ctx.get("steamid"))
        _title_sfx  = f"  âž¤  {player_ctx['name']}" if _has_player else ""
        win.title(f"ðŸ“Š IV Calculator{_title_sfx}  â€”  paldb.cc/en/Iv_Calc")
        win.geometry("880x800" if _has_player else "860x750")
        win.configure(bg="#0a0a0a")
        win.resizable(True, True)
        win.grab_set()

        # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr = tk.Frame(win, bg="#111827", pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸ“Š  IV CALCULATOR",
                 bg="#111827", fg="#38bdf8",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16)
        tk.Label(hdr, text="â€” Independent Variable (Chá»‰ sá»‘ cÃ¡ thá»ƒ IV 0~100)",
                 bg="#111827", fg="#666",
                 font=("Segoe UI", 9)).pack(side="left")

        # â”€â”€ Scrollable body â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ Build pal list from _IV_PAL_DATA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        pal_entries = sorted(_IV_PAL_DATA.items(),
                             key=lambda x: (x[1]['id'].zfill(5), x[0]))
        pal_display = [f"[{v['id']}] {v['name']} ({k})" for k, v in pal_entries]
        pal_codes   = [k for k, v in pal_entries]

        # â”€â”€ Row 1: Pal + Level â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ Row 2: Current Stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        r2 = tk.Frame(body, bg="#0d1117", pady=8)
        r2.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(r2, text="Chá»‰ sá»‘ hiá»‡n táº¡i cá»§a Pal (Ä‘á»c tá»« game):",
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

        # â”€â”€ Row 3: Condenser â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        r3 = tk.Frame(body, bg="#0d1117", pady=6)
        r3.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(r3, text="Pal Essence Condenser:", bg="#0d1117", fg="#aaa",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="e", padx=(0, 4))
        condenser_var = tk.StringVar(value="0 (+0%)")
        ttk.Combobox(r3, textvariable=condenser_var,
                      values=["0 (+0%)", "1 (+5%)", "2 (+10%)", "3 (+15%)", "4 (+20%)"],
                      state="readonly", width=14, font=("Segoe UI", 9)
                      ).grid(row=0, column=1, padx=(0, 14), ipady=2)

        # â”€â”€ Row 4: Statue of Power â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        r4 = tk.Frame(body, bg="#0d1117", pady=6)
        r4.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(r4, text="Statue of Power (tÆ°á»£ng sá»©c máº¡nh â€” má»—i cáº¥p +3%):",
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

        # â”€â”€ Row 5: Passive Skills â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        r5 = tk.Frame(body, bg="#0d1117", pady=6)
        r5.pack(fill="x", padx=10, pady=(4, 0))
        tk.Label(r5, text="Passive Skills (tá»‘i Ä‘a 4):",
                 bg="#0d1117", fg="#a78bfa",
                 font=("Segoe UI", 9, "bold")).grid(
                     row=0, column=0, columnspan=4, sticky="w", padx=2, pady=(0, 4))
        passive_opts = ["(KhÃ´ng)"] + [pd['name'] for pd in _IV_PASSIVE_DATA.values()]
        passive_vars_iv = [tk.StringVar(value="(KhÃ´ng)") for _ in range(4)]
        for i, pv in enumerate(passive_vars_iv):
            col = i % 2
            row = 1 + i // 2
            ttk.Combobox(r5, textvariable=pv, values=passive_opts,
                          state="readonly", width=36, font=("Segoe UI", 9)
                          ).grid(row=row, column=col, padx=(4, 14), pady=2, ipady=2)

        # â”€â”€ Buttons + Status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        btn_f = tk.Frame(body, bg="#0d1117", pady=8)
        btn_f.pack(fill="x", padx=10, pady=(4, 0))
        calc_btn = tk.Button(btn_f, text="  ðŸ“Š TÃNH IV  ",
                              bg="#0e7490", fg="white", relief="flat",
                              padx=16, pady=6, font=("Segoe UI", 10, "bold"))
        calc_btn.pack(side="left", padx=2)
        tk.Button(btn_f, text="âœ– ÄÃ³ng",
                  bg="#2a0000", fg="#ff7777", relief="flat",
                  padx=10, pady=6, font=("Segoe UI", 9),
                  command=win.destroy).pack(side="left", padx=6)
        calc_status = tk.Label(btn_f, text="", bg="#0d1117", fg="#888",
                                font=("Segoe UI", 9))
        calc_status.pack(side="left", padx=8)

        # â”€â”€ Result Cards â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                if f >= 90: return "S â˜…"
                if f >= 70: return "A"
                if f >= 40: return "B"
                if f >=  0: return "C"
                return "D"
            except Exception:
                return "?"

        result_labels = {}
        card_defs = [
            ("â¤ï¸ HP",          "hp",  "#4ade80",
             ["IV", "Base", "MaxCur(IV100)", "Diff vs Max%", "Max@Lv65"]),
            ("âš”ï¸ ShotAttack",  "atk", "#f87171",
             ["IV", "Base", "MaxCur(IV100)", "Diff vs Max%", "Max@Lv65", "Passive%"]),
            ("ðŸ›¡ï¸ Defense",     "def", "#60a5fa",
             ["IV", "Base", "MaxCur(IV100)", "Diff vs Max%", "Max@Lv65", "Passive%"]),
            ("âš™ï¸ Work Speed",  "ws",  "#facc15",
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
                lbl = tk.Label(rf, text="â€”", bg="#111827", fg="#888",
                               font=("Consolas", 9, "bold"), anchor="e")
                lbl.pack(side="right")
                result_labels[key][fn] = lbl

        # â”€â”€ Legend â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        leg_f = tk.Frame(body, bg="#0a0a0a")
        leg_f.pack(fill="x", padx=12, pady=(0, 8))
        leg_items = [
            ("S â˜… â‰¥90",  "#ffd700"), ("A â‰¥70", "#4ade80"),
            ("B â‰¥40",    "#a78bfa"), ("C â‰¥0",  "#60a5fa"),
            ("D <0",     "#f87171"),
        ]
        tk.Label(leg_f, text="IV Grade: ", bg="#0a0a0a", fg="#555",
                 font=("Segoe UI", 8)).pack(side="left")
        for txt, clr in leg_items:
            tk.Label(leg_f, text=f"  {txt}  ", bg="#0a0a0a", fg=clr,
                     font=("Segoe UI", 8, "bold")).pack(side="left")

        # â”€â”€ Calculation function â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        def _do_calc_iv():
            try:
                pal_idx  = pal_cb.current()
                if pal_idx < 0:
                    calc_status.configure(text="âš ï¸ Chá»n Pal trÆ°á»›c!", fg="#ffa500")
                    return
                pal_code = pal_codes[pal_idx]
                pal_data = _IV_PAL_DATA[pal_code]

                lv = int(lv_var.get())
                if not (1 <= lv <= 65):
                    calc_status.configure(
                        text="âš ï¸ Level pháº£i tá»« 1 Ä‘áº¿n 65!", fg="#ffa500")
                    return

                hp_val  = int(hp_var.get())
                atk_val = int(atk_var.get())
                def_val = int(def_var.get())

                # Condenser: "0 (+0%)" â†’ 0; "1 (+5%)" â†’ 0.05
                condenser = int(condenser_var.get().split()[0]) * 0.05

                # Statue of Power: "N (+X%)" â†’ N * 0.03
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
                    if sel == "(KhÃ´ng)":
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

                # â”€â”€ HP (cÃ´ng thá»©c paldb.cc) â”€â”€
                # HPIv = 100*((HP/(1+condenser)/(1+powerHP)-500-5*Lv)/0.5/HPBase/Lv-1)/PotentialBonus
                hp_iv = round(
                    100 * ((hp_val / (1+condenser) / (1+pw_hp) - 500 - 5*lv)
                           / 0.5 / base_hp / lv - 1) / POTENTIAL, 1)
                hp_max_cur = round(500 + lv*5 + base_hp*lv*0.5*(1+POTENTIAL))
                hp_diff    = round(100*(hp_max_cur - hp_val)/hp_max_cur, 1) if hp_max_cur else 0
                hp_max65   = round(500 + MAX_LV*5 + base_hp*MAX_LV*0.5*(1+POTENTIAL))

                # â”€â”€ ShotAttack â”€â”€
                atk_iv = round(
                    100 * ((atk_val / (1+condenser) / (1+pw_atk) / (1+passive_atk) - 100)
                           / 0.075 / base_atk / lv - 1) / POTENTIAL, 1)
                atk_max_cur = round(100 + base_atk*lv*0.075*(1+POTENTIAL))
                atk_diff    = round(100*(atk_max_cur - atk_val)/atk_max_cur, 1) if atk_max_cur else 0
                atk_max65   = round(100 + base_atk*MAX_LV*0.075*(1+POTENTIAL))

                # â”€â”€ Defense â”€â”€
                def_iv = round(
                    100 * ((def_val / (1+condenser) / (1+pw_def) / (1+passive_def) - 50)
                           / 0.075 / base_def / lv - 1) / POTENTIAL, 1)
                def_max_cur = round(50 + base_def*lv*0.075*(1+POTENTIAL))
                def_diff    = round(100*(def_max_cur - def_val)/def_max_cur, 1) if def_max_cur else 0
                def_max65   = round(50 + base_def*MAX_LV*0.075*(1+POTENTIAL))

                # â”€â”€ Work Speed â”€â”€
                ws_after = int(70 * (1+condenser) * (1+pw_ws) * (1+passive_ws))

                # â”€â”€ Update result cards â”€â”€
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
                    text=f"âœ… {pal_data['name']} Lv.{lv}  |  "
                         f"HP:{hp_iv} {_iv_grade(hp_iv)}  "
                         f"ATK:{atk_iv} {_iv_grade(atk_iv)}  "
                         f"DEF:{def_iv} {_iv_grade(def_iv)}",
                    fg="#00ff88")

            except ValueError as e:
                calc_status.configure(
                    text=f"âš ï¸ Nháº­p sá»‘ nguyÃªn há»£p lá»‡ cho HP/ATK/DEF/Level! ({e})",
                    fg="#ffa500")
            except ZeroDivisionError:
                calc_status.configure(
                    text="âš ï¸ Lá»—i chia 0 â€” Kiá»ƒm tra Level vÃ  Base stats!",
                    fg="#f87171")
            except Exception as e:
                calc_status.configure(text=f"âŒ Lá»—i tÃ­nh toÃ¡n: {e}", fg="#f87171")

        calc_btn.configure(command=_do_calc_iv)
        win.bind("<Return>", lambda e: _do_calc_iv())

        # â”€â”€ SECTION: GÃ¡n IV cho ngÆ°á»i chÆ¡i (chá»‰ hiá»‡n khi cÃ³ player context) â”€â”€
        if _has_player:
            tk.Frame(body, bg="#1c1c1c", height=2).pack(fill="x", padx=6, pady=(10, 0))
            giv_hdr = tk.Frame(body, bg="#0d2137", pady=6)
            giv_hdr.pack(fill="x", padx=6, pady=(0, 0))
            tk.Label(giv_hdr,
                     text=f"ðŸŽ  GÃN IV CHO NGÆ¯á»œI CHÆ I  â–¸  {player_ctx['name']}",
                     bg="#0d2137", fg="#38bdf8",
                     font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
            tk.Label(giv_hdr,
                     text="(Give Pal má»›i vá»›i chá»‰ sá»‘ IV tÃ¹y chá»‰nh qua PD API)",
                     bg="#0d2137", fg="#555",
                     font=("Segoe UI", 8)).pack(side="left")

            giv_body = tk.Frame(body, bg="#0d1117", pady=6)
            giv_body.pack(fill="x", padx=6, pady=(0, 4))

            # â”€â”€ Row A: Target IVs (0-100) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            tk.Label(giv_body, text="Target IVs muá»‘n gÃ¡n (0-100):",
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

            # â”€â”€ Row B: Nickname + Level â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            tk.Label(giv_body, text="Nickname (tÃ¹y chá»n):", bg="#0d1117", fg="#aaa",
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

            # â”€â”€ Row C: Passives for the new Pal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            tk.Label(giv_body, text="Passive Skills cho Pal má»›i (tá»‘i Ä‘a 4):",
                     bg="#0d1117", fg="#a78bfa",
                     font=("Segoe UI", 9, "bold")).grid(
                         row=3, column=0, columnspan=6, sticky="w",
                         padx=4, pady=(8, 4))
            # Build passive list as (display_name, code) pairs
            _giv_passive_opts_disp = ["(KhÃ´ng)"] + [
                f"{pd['name']}  [{pk}]"
                for pk, pd in _IV_PASSIVE_DATA.items()
            ]
            _giv_passive_opts_keys = [None] + list(_IV_PASSIVE_DATA.keys())
            giv_passive_vars = [tk.StringVar(value="(KhÃ´ng)") for _ in range(4)]
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

            # â”€â”€ Row D: Give button + status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            giv_btn_f = tk.Frame(giv_body, bg="#0d1117")
            giv_btn_f.grid(row=6, column=0, columnspan=6,
                            sticky="w", padx=4, pady=(8, 4))
            giv_btn = tk.Button(giv_btn_f,
                                text="  ðŸŽ GIVE PAL WITH IVs  ",
                                bg="#065f46", fg="white", relief="flat",
                                padx=14, pady=7,
                                font=("Segoe UI", 10, "bold"))
            giv_btn.pack(side="left", padx=(0, 8))
            giv_status = tk.Label(giv_btn_f, text="", bg="#0d1117", fg="#888",
                                   font=("Segoe UI", 9))
            giv_status.pack(side="left")

            # â”€â”€ Give logic â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            def _do_give_with_ivs():
                try:
                    # â”€â”€ Láº¥y Pal â”€â”€
                    pal_idx = pal_cb.current()
                    if pal_idx < 0:
                        giv_status.configure(
                            text="âš ï¸ Chá»n Pal trÆ°á»›c!", fg="#ffa500")
                        return
                    pal_code = pal_codes[pal_idx]
                    pal_name = _IV_PAL_DATA[pal_code]['name']

                    lv = int(lv_var.get())
                    if not (1 <= lv <= 65):
                        giv_status.configure(
                            text="âš ï¸ Level pháº£i 1-65!", fg="#ffa500")
                        return

                    # â”€â”€ Target IVs (0-100) â”€â”€
                    hp_iv_t  = max(0, min(100, int(giv_hp_iv.get())))
                    atk_iv_t = max(0, min(100, int(giv_atk_iv.get())))
                    def_iv_t = max(0, min(100, int(giv_def_iv.get())))

                    # â”€â”€ Passives: láº¥y keys â”€â”€
                    passives_keys = []
                    for pv in giv_passive_vars:
                        sel = pv.get()
                        if sel == "(KhÃ´ng)":
                            continue
                        # Format: "Display Name  [key]"
                        m = re.search(r"\[(.+?)\]$", sel)
                        if m:
                            passives_keys.append(m.group(1))

                    # â”€â”€ Build payload â”€â”€
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
                        text=f"â³ Äang gá»­i {pal_name} Lv.{lv} (HP IV:{hp_iv_t} ATK:{atk_iv_t} DEF:{def_iv_t})...",
                        fg="#ffa500")
                    giv_btn.configure(state="disabled")

                    def _bg_give():
                        # Thá»­ PD API trÆ°á»›c (há»— trá»£ IVs)
                        pd_ok, data = self._pdapi_give(
                            steamid, {"Pal": [pal_obj]})
                        if pd_ok:
                            msg = (f"âœ… Give OK (PD API): {pal_name} Lv.{lv} "
                                   f"HP IV:{hp_iv_t} ATK IV:{atk_iv_t} DEF IV:{def_iv_t}")
                            self.root.after(0, lambda: giv_status.configure(
                                text=msg, fg="#00ff88"))
                        else:
                            # Fallback: RCON givepal (khÃ´ng cÃ³ IVs)
                            rcon_ok = self._rcon_give_pal(
                                playerid, steam_number, steamid, pal_code, lv)
                            if rcon_ok:
                                msg = (f"âš ï¸ Give OK (RCON fallback â€” khÃ´ng cÃ³ IV): "
                                       f"{pal_name} Lv.{lv}")
                                self.root.after(0, lambda: giv_status.configure(
                                    text=msg, fg="#facc15"))
                            else:
                                errs = data.get("Error", data.get("error", str(data)))
                                msg = (f"âŒ Give FAIL: {pal_code} Lv.{lv} â€” {errs}")
                                self.root.after(0, lambda: giv_status.configure(
                                    text=msg, fg="#ff5555"))
                        self._enqueue_console(f"ðŸŽ IV-Give: {msg}")
                        self.root.after(0, lambda: giv_btn.configure(state="normal"))

                    threading.Thread(target=_bg_give, daemon=True).start()

                except ValueError as e:
                    giv_status.configure(
                        text=f"âš ï¸ Nháº­p sá»‘ nguyÃªn há»£p lá»‡! ({e})", fg="#ffa500")
                except Exception as e:
                    giv_status.configure(text=f"âŒ Lá»—i: {e}", fg="#f87171")

            giv_btn.configure(command=_do_give_with_ivs)

            # â”€â”€ Tip box â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            tip = tk.Label(body,
                           text="ðŸ’¡  Tip: IV 0-100 tÆ°Æ¡ng á»©ng 0%-30% bonus stats "
                                "â”‚  AttackMelee = AttackShot = ATK IV Ä‘Æ°á»£c set  "
                                "â”‚  PD API pháº£i Online má»›i dÃ¹ng Ä‘Æ°á»£c tÃ­nh nÄƒng nÃ y",
                           bg="#0a0a0a", fg="#444",
                           font=("Segoe UI", 8), wraplength=820, justify="left")
            tip.pack(fill="x", padx=12, pady=(0, 8))

    def _player_ctx_show(self, event):
        """Hiá»‡n context menu right-click."""
        iid = self.player_tree.identify_row(event.y)
        if iid:
            self.player_tree.selection_set(iid)
            self._player_on_select()
            try:
                self._player_ctx.tk_popup(event.x_root, event.y_root)
            finally:
                self._player_ctx.grab_release()

    def _player_sort_by(self, col: str):
        """Click header â†’ sort theo cá»™t, click láº¡i â†’ Ä‘áº£o chiá»u."""
        if self._player_sort_col == col:
            self._player_sort_rev = not self._player_sort_rev
        else:
            self._player_sort_col = col
            self._player_sort_rev = col in ("Lv", "Ping")
        self._filter_player_tree()

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: OVERVIEW
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def draw_overview(self):
        tk.Label(self.container, text="GIÃM SÃT Há»† THá»NG MANAGER SERVERPAL",
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

        # â”€â”€ Live system log ngay trong tab Tá»•ng Quan â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        log_wrap = tk.Frame(self.container, bg="#0a0a0a")
        log_wrap.pack(fill="both", expand=True, pady=(14, 0))

        hdr = tk.Frame(log_wrap, bg="#0a0d1a", pady=4)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸ“‹  LIVE SYSTEM LOG",
                 bg="#0a0d1a", fg="#00ffcc",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        tk.Button(
            hdr, text="ðŸ—‘ XÃ³a",
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
        # Phá»¥c há»“i log Ä‘Ã£ cÃ³ tá»« buffer Ä‘á»ƒ khi quay láº¡i tab khÃ´ng máº¥t log
        self._replay_console_buffer(self.overview_console)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: DASHBOARD
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def draw_dashboard(self):
        # â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
        # â•‘  SECTION 1 â€” STATUS + CONTROL BUTTONS                   â•‘
        # â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        ctrl_outer = tk.Frame(self.container, bg="#0a0a0a")
        ctrl_outer.pack(fill="x", pady=(0, 4))

        # â”€â”€ Status indicator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        status_row = tk.Frame(ctrl_outer, bg="#0a0a0a", pady=4)
        status_row.pack(fill="x", padx=10)

        self._lbl_ctrl_status = tk.Label(
            status_row, text="â— KIá»‚M TRA...",
            bg="#0a0a0a", fg="#888",
            font=("Segoe UI", 13, "bold")
        )
        self._lbl_ctrl_status.pack(side="left")

        tk.Label(status_row,
                 text="  â”‚  Cháº¿ Ä‘á»™ Auto:",
                 bg="#0a0a0a", fg="#555",
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Checkbutton(status_row, text="Watchdog tá»± Ä‘á»™ng khá»Ÿi Ä‘á»™ng",
                       variable=self.auto_mode,
                       bg="#0a0a0a", fg="#888",
                       selectcolor="#0a0a0a",
                       activebackground="#0a0a0a",
                       font=("Segoe UI", 9)).pack(side="left", padx=6)

        # â”€â”€ NÃºt Ä‘iá»u khiá»ƒn chÃ­nh (4 nÃºt lá»›n) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        btn_row = tk.Frame(ctrl_outer, bg="#0a0a0a", pady=6)
        btn_row.pack(fill="x", padx=8)

        btn_cfg = [
            # (attr_name, text, bg_on, bg_off, fg_on, fg_off, command, always_enabled)
        ]

        # START â€” xanh lÃ¡
        self._btn_ctrl_start = tk.Button(
            btn_row,
            text="â–¶   KHá»žI Äá»˜NG",
            bg="#1a5e1a", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat", padx=0, pady=14,
            cursor="hand2",
            command=self.server_start
        )
        self._btn_ctrl_start.pack(side="left", fill="x", expand=True, padx=(0, 4))

        # STOP â€” Ä‘á» Ä‘áº­m
        self._btn_ctrl_stop = tk.Button(
            btn_row,
            text="â¹   Dá»ªNG SERVER",
            bg="#7b0000", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat", padx=0, pady=14,
            cursor="hand2",
            command=self.server_stop
        )
        self._btn_ctrl_stop.pack(side="left", fill="x", expand=True, padx=4)

        # RESET â€” cam
        tk.Button(
            btn_row,
            text="ðŸ”   RESET SERVER",
            bg="#8b4a00", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat", padx=0, pady=14,
            cursor="hand2",
            command=self.manual_test_reset
        ).pack(side="left", fill="x", expand=True, padx=4)

        # SAVE â€” xanh dÆ°Æ¡ng
        tk.Button(
            btn_row,
            text="ðŸ’¾   SAVE SERVER",
            bg="#0d3b6e", fg="white",
            font=("Segoe UI", 13, "bold"),
            relief="flat", padx=0, pady=14,
            cursor="hand2",
            command=self.manual_save
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # â”€â”€ RAM Optimizer controls â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        opt_row = tk.Frame(ctrl_outer, bg="#0a0a0a", pady=4)
        opt_row.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(opt_row, text="ðŸ§¹ Tá»‘i Æ°u RAM:",
                 bg="#0a0a0a", fg="#55ff99",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(opt_row, text="Cháº¡y ngay",
                  bg="#145a32", fg="white",
                  relief="flat", padx=14, pady=6,
                  font=("Segoe UI", 9, "bold"),
                  command=lambda: threading.Thread(target=self.optimize_ram_now, daemon=True).start()
                  ).pack(side="left", padx=(8, 10))
        tk.Checkbutton(opt_row, text="Tá»± Ä‘á»™ng khi RAM há»‡ thá»‘ng â‰¥ 80%",
                       variable=self._ram_auto_opt_var,
                       bg="#0a0a0a", fg="#888", selectcolor="#0a0a0a",
                       activebackground="#0a0a0a",
                       font=("Segoe UI", 9)).pack(side="left")

        # Cáº­p nháº­t tráº¡ng thÃ¡i nÃºt ngay khi váº½
        self.root.after(300, self._update_ctrl_btn_state)

        # â”€â”€ DÃ²ng phÃ¢n cÃ¡ch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sep = tk.Frame(ctrl_outer, bg="#1e1e1e", height=1)
        sep.pack(fill="x", padx=8, pady=(4, 0))

        # â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
        # â•‘  SECTION 2 â€” RCON + BROADCAST                           â•‘
        # â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        input_outer = tk.Frame(self.container, bg="#0a0a0a")
        input_outer.pack(fill="x", padx=8, pady=(4, 0))

        # RCON row
        rcon_f = tk.Frame(input_outer, bg="#0a0a0a", pady=3)
        rcon_f.pack(fill="x")
        tk.Label(rcon_f, text="âš¡ RCON:",
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
        tk.Button(rcon_f, text="Gá»¬I RCON",
                  bg="#7d3c98", fg="white",
                  relief="flat", padx=16, pady=4,
                  font=("Segoe UI", 9, "bold"),
                  command=self.send_rcon_cmd).pack(side="left")

        # â”€â”€ DÃ²ng phÃ¢n cÃ¡ch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sep2 = tk.Frame(self.container, bg="#1e1e1e", height=1)
        sep2.pack(fill="x", padx=8, pady=(4, 0))

        # â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
        # â•‘  SECTION 3 â€” PANED: CHAT INGAME + SYSTEM LOG            â•‘
        # â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        paned = tk.PanedWindow(
            self.container, orient=tk.VERTICAL,
            bg="#1e1e1e", sashwidth=5, sashrelief="flat",
            handlesize=0
        )
        paned.pack(fill="both", expand=True, padx=2, pady=(4, 2))

        # â”€â”€ Pane trÃªn: CHAT INGAME â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        chat_frame = tk.Frame(paned, bg="#050d14")
        paned.add(chat_frame, minsize=120)

        chat_hdr = tk.Frame(chat_frame, bg="#071520", pady=4)
        chat_hdr.pack(fill="x")
        tk.Label(chat_hdr, text="ðŸ’¬  CHAT INGAME",
                 bg="#071520", fg="#00e5ff",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        # Bá»™ lá»c kÃªnh (táº¥t cáº£ / Global / Local)
        self._chat_filter_var = tk.StringVar(value="All")
        for opt, label in [("All","Táº¥t cáº£"),("Global","Global"),("Local","Local")]:
            tk.Radiobutton(
                chat_hdr, text=label,
                variable=self._chat_filter_var, value=opt,
                bg="#071520", fg="#888", selectcolor="#071520",
                activebackground="#071520",
                font=("Segoe UI", 8)
            ).pack(side="left", padx=2)
        tk.Button(chat_hdr, text="ðŸ—‘ XÃ³a",
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

        # â”€â”€ Chat input (gá»­i cho ngÆ°á»i chÆ¡i) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        chat_in_f = tk.Frame(chat_frame, bg="#050d14", pady=3)
        chat_in_f.pack(fill="x", padx=4, pady=(2, 4))
        tk.Label(chat_in_f, text="ðŸ“¢",
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
        tk.Button(chat_in_f, text="Gá»¬I",
                  bg="#1a4a7a", fg="white",
                  relief="flat", padx=18, pady=4,
                  font=("Segoe UI", 9, "bold"),
                  command=self.send_msg).pack(side="left", padx=(0, 2))

        # â”€â”€ Pane dÆ°á»›i: SYSTEM LOG â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        log_frame = tk.Frame(paned, bg="#0a0a0a")
        paned.add(log_frame, minsize=80)

        mgr_hdr = tk.Frame(log_frame, bg="#0a0d1a", pady=4)
        mgr_hdr.pack(fill="x")
        tk.Label(mgr_hdr, text="ðŸ–¥  SYSTEM LOG",
                 bg="#0a0d1a", fg="#00ffcc",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        tk.Button(mgr_hdr, text="ðŸ—‘ XÃ³a",
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
        # Phá»¥c há»“i log Ä‘Ã£ cÃ³ tá»« buffer
        self._replay_console_buffer(self.console)

        # Äáº·t kÃ­ch thÆ°á»›c ban Ä‘áº§u cho 2 pane (60% chat / 40% log)
        self.container.update_idletasks()
        self.root.after(200, lambda: paned.sash_place(0, 0, int(paned.winfo_height() * 0.6)))

        # (Chat Ä‘Æ°á»£c route qua _write_console_direct â†’ _poll_console_queue)

    def _load_server_log_history(self):
        """Táº£i 200 dÃ²ng cuá»‘i cá»§a PalServer.log vÃ o server_console khi má»Ÿ tab."""
        if not hasattr(self, "server_console") or not self.server_console.winfo_exists():
            return
        try:
            if not os.path.isfile(SERVER_LOG_FILE):
                self.server_console.insert(
                    tk.END,
                    f"âš ï¸ ChÆ°a tÃ¬m tháº¥y file log:\n  {SERVER_LOG_FILE}\n"
                    "   Server chÆ°a cháº¡y hoáº·c Ä‘Æ°á»ng dáº«n chÆ°a Ä‘Ãºng.\n"
                )
                return
            with open(SERVER_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-200:] if len(lines) > 200 else lines
            self.server_console.delete("1.0", tk.END)
            if len(lines) > 200:
                self.server_console.insert(
                    tk.END,
                    f"â”€â”€â”€ 200 dÃ²ng cuá»‘i / tá»•ng {len(lines)} dÃ²ng â”€â”€â”€\n\n"
                )
            for line in tail:
                self.server_console.insert(tk.END, line)
            self.server_console.see(tk.END)
        except Exception as e:
            self.server_console.insert(tk.END, f"âŒ Lá»—i Ä‘á»c log: {e}\n")

    def send_rcon_cmd(self):
        """Gá»­i lá»‡nh RCON trá»±c tiáº¿p, hiá»ƒn thá»‹ káº¿t quáº£ trong manager console."""
        if not hasattr(self, "entry_rcon"):
            return
        cmd = self.entry_rcon.get().strip()
        if not cmd:
            return
        self.entry_rcon.delete(0, tk.END)
        self._enqueue_console(f"âš¡ RCON â–¶ {cmd}")
        def _do():
            result = rcon_exec(cmd)
            self._enqueue_console(f"   â†³ {result or '(OK â€” khÃ´ng cÃ³ pháº£n há»“i)'}")
        threading.Thread(target=_do, daemon=True).start()

    def send_msg(self):
        m = self.entry_cmd.get().strip()
        if m:
            self.send_ingame_broadcast(f"ADMIN: {m}")
            self._enqueue_console(f"ðŸ“¢ ADMIN â†’ {m}")
            self.entry_cmd.delete(0, tk.END)

    def manual_test_reset(self):
        if messagebox.askyesno("CONFIRM", "Cháº¡y quy trÃ¬nh Reset 30s ngay?"):
            self.is_processing = False
            threading.Thread(target=self.reset_sequence, daemon=True).start()

    def manual_save(self):
        try:
            requests.post(f"{API_URL}/save", auth=AUTH, timeout=20)
            self.write_console("ðŸ’¾ Manual Save Done.")
        except Exception:
            pass

    def _empty_workingset_pid(self, pid: int) -> bool:
        """Windows-only: gá»i EmptyWorkingSet Ä‘á»ƒ trim RAM process."""
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
        """Tá»‘i Æ°u RAM tá»©c thÃ¬ cho PalServer (vÃ  trÃ¬nh quáº£n lÃ½) mÃ  khÃ´ng cáº§n restart."""
        try:
            procs = self._get_palserver_processes()
            if not procs:
                self._enqueue_console("âš ï¸ KhÃ´ng tÃ¬m tháº¥y PalServer Ä‘á»ƒ tá»‘i Æ°u RAM.")
                return
            total_before = 0
            for p in procs:
                try:
                    total_before += p.memory_info().rss
                except Exception:
                    pass
            self._enqueue_console("ðŸ§¹ Äang tá»‘i Æ°u RAM PalServer (EmptyWorkingSet)...")
            for p in procs:
                self._empty_workingset_pid(p.pid)
            # Trim chÃ­nh app manager Ä‘á»ƒ giáº£m footprint giao diá»‡n
            self._empty_workingset_pid(os.getpid())
            time.sleep(0.5)
            total_after = 0
            for p in self._get_palserver_processes():
                try:
                    total_after += p.memory_info().rss
                except Exception:
                    pass
            diff_mb = max((total_before - total_after) / (1024 * 1024), 0)
            self._enqueue_console(f"âœ… Tá»‘i Æ°u RAM xong. Giáº£i phÃ³ng ~{diff_mb:.1f} MB.")
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i tá»‘i Æ°u RAM: {e}")

    def _ram_monitor_loop(self):
        """Náº¿u báº­t auto vÃ  RAM há»‡ thá»‘ng cao, tá»± trim PalServer."""
        try:
            if self._ram_auto_opt_var.get():
                used = psutil.virtual_memory().percent
                thr = max(min(int(self._ram_opt_threshold.get()), 95), 50)
                if used >= thr and self._is_server_running():
                    self._enqueue_console(f"âš ï¸ RAM há»‡ thá»‘ng {used:.0f}% â‰¥ {thr}% â†’ tá»± tá»‘i Æ°u RAM.")
                    threading.Thread(target=self.optimize_ram_now, daemon=True).start()
        except Exception:
            pass
        finally:
            self.root.after(self._ram_opt_interval_ms, self._ram_monitor_loop)

    def _auto_refresh_server_status_loop(self):
        """Äá»“ng bá»™ tráº¡ng thÃ¡i server lÃªn UI theo chu ká»³, trÃ¡nh pháº£i refresh tay."""
        try:
            running = self._is_server_running()
            if hasattr(self, "lbl_status"):
                self.lbl_status.config(
                    text="â— SERVER ONLINE" if running else "â— SERVER OFFLINE",
                    fg="#00ffcc" if running else "#ff4444"
                )
            # Náº¿u tab Ä‘iá»u khiá»ƒn Ä‘Ã£ má»Ÿ thÃ¬ Ä‘á»“ng bá»™ luÃ´n mÃ u nÃºt Start/Stop.
            self._update_ctrl_btn_state()
        except Exception:
            pass
        finally:
            self.root.after(self._status_refresh_interval_ms, self._auto_refresh_server_status_loop)

    def server_start(self):
        """Khá»Ÿi Ä‘á»™ng PalServer thá»§ cÃ´ng."""
        if self._is_server_running():
            self._enqueue_console("âš ï¸ Server Ä‘ang cháº¡y, khÃ´ng cáº§n khá»Ÿi Ä‘á»™ng láº¡i.")
            messagebox.showinfo("START", "Server Ä‘ang cháº¡y rá»“i!")
            return
        self._enqueue_console("â–¶ï¸ Äang khá»Ÿi Ä‘á»™ng PalServer an toÃ n...")
        try:
            if self._start_server_safe(source="Manual Start"):
                self._enqueue_console("âœ… Lá»‡nh khá»Ÿi Ä‘á»™ng Ä‘Ã£ gá»­i â€” chá» server online...")
                self._update_ctrl_btn_state()
            else:
                messagebox.showerror("START Error", f"KhÃ´ng thá»ƒ khá»Ÿi Ä‘á»™ng server:\n{SERVER_EXE}")
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i khá»Ÿi Ä‘á»™ng: {e}")
            messagebox.showerror("START Error", str(e))

    def server_stop(self):
        """Dá»«ng PalServer ngay láº­p tá»©c (sau khi xÃ¡c nháº­n)."""
        if not messagebox.askyesno(
            "âš ï¸ XÃC NHáº¬N Dá»ªNG SERVER",
            "Dá»ªNG server ngay bÃ¢y giá»?\n\n"
            "âš ï¸ NgÆ°á»i chÆ¡i sáº½ bá»‹ ngáº¯t káº¿t ná»‘i!\n"
            "Dá»¯ liá»‡u chÆ°a save cÃ³ thá»ƒ bá»‹ máº¥t!"
        ):
            return
        self._enqueue_console("ðŸ›‘ Äang dá»«ng PalServer...")

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
            self._enqueue_console("âœ… Server Ä‘Ã£ dá»«ng.")
            self.root.after(0, self._update_ctrl_btn_state)

        threading.Thread(target=_do_stop, daemon=True).start()

    def _update_ctrl_btn_state(self):
        """Cáº­p nháº­t mÃ u sáº¯c / text nÃºt theo tráº¡ng thÃ¡i server."""
        try:
            if not hasattr(self, "_btn_ctrl_start"):
                return
            running = self._is_server_running()
            if running:
                self._btn_ctrl_start.config(
                    state="disabled", bg="#1a4a1a", fg="#336633",
                    text="â–¶  ÄANG CHáº Y"
                )
                self._btn_ctrl_stop.config(
                    state="normal", bg="#7b0000", fg="white",
                    text="â¹  Dá»ªNG SERVER"
                )
                self._lbl_ctrl_status.config(
                    text="â— SERVER ONLINE", fg="#00ff88"
                )
            else:
                self._btn_ctrl_start.config(
                    state="normal", bg="#1a5e1a", fg="white",
                    text="â–¶  KHá»žI Äá»˜NG"
                )
                self._btn_ctrl_stop.config(
                    state="disabled", bg="#2a0000", fg="#553333",
                    text="â¹  Dá»ªNG SERVER"
                )
                self._lbl_ctrl_status.config(
                    text="â— SERVER OFFLINE", fg="#ff4444"
                )
        except Exception:
            pass

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: PLAYERS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def draw_players(self):
        # State
        self._all_players_data: list = []
        self._players_by_iid:   dict = {}
        self._player_sort_col:  str  = "Lv"
        self._player_sort_rev:  bool = True   # máº·c Ä‘á»‹nh: cao â†’ tháº¥p

        # â”€â”€ Title + player count â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        title_f = tk.Frame(self.container, bg="#0a0a0a")
        title_f.pack(fill="x", pady=(0, 4))
        tk.Label(title_f, text="DANH SÃCH NGÆ¯á»œI CHÆ I",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        self._lbl_player_count = tk.Label(
            title_f, text="  â¬¤ 0 online",
            bg="#0a0a0a", fg="#555",
            font=("Segoe UI", 11, "bold")
        )
        self._lbl_player_count.pack(side="left", padx=8)

        # â”€â”€ Toolbar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        toolbar = tk.Frame(self.container, bg="#0a0a0a")
        toolbar.pack(fill="x", pady=(0, 5))

        tk.Button(toolbar, text="ðŸ”„ LÃ€M Má»šI",
                  bg="#1a5276", fg="white", relief="flat", padx=14,
                  command=self._refresh_players_tree).pack(side="left", padx=(0, 6))

        self._player_auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(toolbar, text="â± Auto 8s",
                       variable=self._player_auto_var,
                       bg="#0a0a0a", fg="#666", selectcolor="#0a0a0a",
                       activebackground="#0a0a0a",
                       font=("Segoe UI", 9)).pack(side="left", padx=(0, 12))

        # Level legend
        for lv_txt, lv_clr in [
            ("Lv 1â€“19", "#666"), ("Lv 20â€“34", "#00cc88"),
            ("Lv 35â€“49", "#4499ff"), ("Lv 50+", "#ffcc00"),
        ]:
            tk.Label(toolbar, text=f"â–  {lv_txt}",
                     bg="#0a0a0a", fg=lv_clr,
                     font=("Segoe UI", 8)).pack(side="left", padx=4)

        # Search
        tk.Label(toolbar, text="ðŸ”",
                 bg="#0a0a0a", fg="#888",
                 font=("Segoe UI", 11)).pack(side="right", padx=(8, 0))
        self._player_filter_var = tk.StringVar()
        self._player_filter_var.trace_add("write", lambda *_: self._filter_player_tree())
        tk.Entry(toolbar, textvariable=self._player_filter_var,
                 bg="#111", fg="#ccc", bd=0,
                 font=("Consolas", 10), insertbackground="#ccc",
                 width=20).pack(side="right", ipady=5)
        tk.Label(toolbar, text="TÃ¬m kiáº¿m:",
                 bg="#0a0a0a", fg="#555",
                 font=("Segoe UI", 8)).pack(side="right", padx=(0, 4))

        # â”€â”€ Treeview â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        cols = ("#", "TÃªn", "Lv", "Ping", "SteamID", "PlayerID", "IP")
        col_w = {
            "#":         38,
            "TÃªn":      185,
            "Lv":        58,
            "Ping":      72,
            "SteamID":  215,
            "PlayerID": 255,
            "IP":       128,
        }
        col_anchor = {
            "#": "center", "TÃªn": "w", "Lv": "center",
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
            label="ðŸŽ  Give Item  (PD API)",
            command=self._player_give_item_dialog)
        self._player_ctx.add_command(
            label="ðŸ¾  Give Pal   (PD API)",
            command=self._player_give_pal_dialog)
        self._player_ctx.add_separator()
        self._player_ctx.add_command(
            label="âš¡  Kick player", command=self._player_kick_selected)
        self._player_ctx.add_command(
            label="â›”  Ban player",  command=lambda: self._player_ban_selected(source="RIGHT_CLICK"))
        self._player_ctx.add_separator()
        self._player_ctx.add_command(
            label="ðŸ“‹  Copy SteamID", command=self._player_copy_steamid)
        self._player_ctx.add_command(
            label="ðŸ“‹  Copy PlayerID", command=self._player_copy_playerid)
        self.player_tree.bind("<Button-3>", self._player_ctx_show)

        # â”€â”€ Action panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        action_f = tk.Frame(self.container, bg="#111",
                            highlightthickness=1, highlightbackground="#222",
                            pady=6)
        action_f.pack(fill="x", pady=(4, 0))

        self._lbl_selected_player = tk.Label(
            action_f, text="â–¶  Nháº¥p vÃ o ngÆ°á»i chÆ¡i Ä‘á»ƒ thao tÃ¡c",
            bg="#111", fg="#444", font=("Segoe UI", 9)
        )
        self._lbl_selected_player.pack(side="left", padx=12)

        tk.Button(action_f, text="â›” Ban",
                  bg="#3d0000", fg="#ff4444",
                  relief="flat", padx=14,
                  command=lambda: self._player_ban_selected(source="PLAYER_TAB")).pack(side="right", padx=(4, 8))
        tk.Button(action_f, text="âš¡ Kick",
                  bg="#7d1a00", fg="#ff8866",
                  relief="flat", padx=14,
                  command=self._player_kick_selected).pack(side="right", padx=4)

        # Load ngay
        self.root.after(200, self._refresh_players_tree)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: NEWBIE GIFT
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def draw_newbie_gift(self):
        tk.Label(self.container, text="QUÃ€ Táº¶NG",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 10))

        top = tk.Frame(self.container, bg="#0a0a0a")
        top.pack(fill="x")
        tk.Checkbutton(top, text="CHáº¾ Äá»˜ Tá»° Äá»˜NG",
                       variable=self.newbie_gift_auto,
                       bg="#0a0a0a", fg="#00ffcc", selectcolor="#0a0a0a",
                       font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 16))
        self._lbl_gift_stat_received = tk.Label(
            top, text=f"âœ… ÄÃ£ phÃ¡t quÃ  tÃ¢n thá»§: {len(self.newbie_gift_received)} ngÆ°á»i",
            bg="#0a0a0a", fg="#00ffcc", font=("Segoe UI", 10, "bold"))
        self._lbl_gift_stat_received.pack(side="left")
        self._lbl_gift_stat_pending = tk.Label(
            top, text=f"â³ Äang chá» tÃ¢n thá»§: {len(self.newbie_gift_pending)} ngÆ°á»i",
            bg="#0a0a0a", fg="#ffcc00", font=("Segoe UI", 10, "bold"))
        self._lbl_gift_stat_pending.pack(side="left", padx=20)

        nb = ttk.Notebook(self.container)
        nb.pack(fill="both", expand=True, pady=(10, 0))

        tab_new = tk.Frame(nb, bg="#0a0a0a")
        tab_daily = tk.Frame(nb, bg="#0a0a0a")
        tab_online = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_new, text="ðŸŽ QuÃ  TÃ¢n Thá»§")
        nb.add(tab_daily, text="ðŸ“… QuÃ  Äiá»ƒm Danh")
        nb.add(tab_online, text="â± QuÃ  Online")

        # ----- TAB 1: NEWBIE -----
        row1 = tk.Frame(tab_new, bg="#0a0a0a", pady=6)
        row1.pack(fill="x")
        tk.Label(row1, text="Template (má»—i dÃ²ng: item|pal:ID:Count)", bg="#0a0a0a", fg="#88ccff",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(row1, text="ðŸ§ª TEST 1: Thá»­ nháº­n láº§n 2", bg="#8e44ad", fg="white", relief="flat", padx=10,
                  command=self.test_gift_second_time).pack(side="right", padx=4)
        tk.Button(row1, text="ðŸŽ TEST 2: Give full bá»™ quÃ ", bg="#e67e22", fg="white", relief="flat", padx=10,
                  command=self.test_gift_give_all).pack(side="right", padx=4)
        tk.Button(row1, text="ðŸ’¾ LÆ°u", bg="#145a32", fg="white", relief="flat", padx=10,
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
        tk.Label(row2, text="Äiá»ƒm danh ngÃ y (má»—i dÃ²ng: ItemID:Count)", bg="#0a0a0a", fg="#88ccff",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(row2, text="ðŸ“… TEST: PhÃ¡t 1 lÆ°á»£t Ä‘iá»ƒm danh", bg="#2e86c1", fg="white", relief="flat", padx=10,
                  command=self.test_daily_checkin_specific).pack(side="right", padx=4)
        tk.Button(row2, text="ðŸ† TEST: TOP10 bonus chia Ä‘á»u", bg="#6c3483", fg="white", relief="flat", padx=10,
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
        tk.Label(row3, text="QuÃ  online (má»—i dÃ²ng: ItemID:Count)", bg="#0a0a0a", fg="#88ffcc",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(row3, text="Má»‘c phÃºt:", bg="#0a0a0a", fg="#aaa", font=("Segoe UI", 9)).pack(side="right")
        self._online60_minutes_var = tk.StringVar(value=str(max(1, int(self.online60_reward_seconds // 60))))
        tk.Entry(row3, textvariable=self._online60_minutes_var, width=6, bg="#151515", fg="#ddd", bd=0,
                 font=("Consolas", 10), insertbackground="#ddd").pack(side="right", padx=(6, 10), ipady=3)
        tk.Button(row3, text="â± TEST: PhÃ¡t 1 lÆ°á»£t quÃ  online", bg="#16a085", fg="white", relief="flat", padx=10,
                  command=self.test_online60_specific).pack(side="right", padx=4)
        tk.Button(row3, text="ðŸ’¾ LÆ°u online -> file", bg="#145a32", fg="white", relief="flat", padx=10,
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
        tk.Button(bottom, text="ðŸ’¾ LÆ¯U Táº¤T Cáº¢ Cáº¤U HÃŒNH QUÃ€", bg="#145a32", fg="white",
                  relief="flat", padx=14, pady=6, font=("Segoe UI", 9, "bold"),
                  command=self._save_all_gift_tabs_config).pack(side="left")
        tk.Button(bottom, text="ðŸ“‚ Má»ž THÆ¯ Má»¤C LOG", bg="#1a6e3c", fg="white", relief="flat",
                  padx=12, command=self._open_gift_log_folder).pack(side="left", padx=8)
        tk.Label(bottom, text=f"Config file: {MANAGER_CONFIG_FILE}",
                 bg="#0a0a0a", fg="#555", font=("Consolas", 8)).pack(side="right")

        self.root.after(80, lambda: self._load_any_log_to_ui(self.newbie_gift_log_file, self.newbie_gift_log))
        self.root.after(120, lambda: self._load_any_log_to_ui(self.daily_gift_log_file, self.daily_gift_log))
        self.root.after(160, lambda: self._load_any_log_to_ui(self.online_gift_log_file, self.online_gift_log))
        self.root.after(200, self._refresh_gift_stats)

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  ANTIBUG SYSTEM
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _antibug_log(self, msg: str):
        """Ghi log ra UI queue + file + manager console."""
        antibug_enf.antibug_log(self, msg, ANTIBUG_LOG_FILE)

    def _update_antibug_stats_label(self):
        """Cáº­p nháº­t label thá»‘ng kÃª AntiBug trÃªn UI."""
        antibug_enf.update_antibug_stats_label(self)

    def _antibug_parse_line(self, line: str):
        """Parse dÃ²ng log PalDefender â†’ dict sá»± kiá»‡n build/dismantle, hoáº·c None."""
        return antibug_core.parse_antibug_line(line, _ANTIBUG_RE)

    def _antibug_process_event(self, event: dict):
        """Kiá»ƒm tra tá»‘c Ä‘á»™ build/dismantle, kÃ­ch hoáº¡t cáº£nh bÃ¡o/kick khi vÆ°á»£t ngÆ°á»¡ng."""
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

    # â”€â”€ REST API helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _api_announce(self, message: str) -> bool:
        """Broadcast thÃ´ng bÃ¡o qua REST API /v1/api/announce."""
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
        """Kick ngÆ°á»i chÆ¡i qua REST API /v1/api/kick. Tráº£ vá» (ok, status_code)."""
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
        """Ban ngÆ°á»i chÆ¡i qua REST API /v1/api/ban. Tráº£ vá» (ok, status_code)."""
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
        """Unban ngÆ°á»i chÆ¡i qua REST API /v1/api/unban. Tráº£ vá» (ok, status_code)."""
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
        """Äá»c banlist.txt vÃ  tráº£ vá» danh sÃ¡ch cÃ²n Ä‘ang bá»‹ ban theo thá»© tá»± má»›i nháº¥t trÆ°á»›c."""
        return antibug_core.read_antibug_banlist_entries(ANTIBUG_BAN_FILE)

    def _unban_steamid_common(self, sid: str, source: str = "MANUAL") -> tuple[bool, str]:
        """Luá»“ng unban dÃ¹ng chung cho UI vÃ  Discord bot."""
        sid = self._normalize_steamid((sid or "").strip())
        if not sid:
            return False, "SteamID khÃ´ng há»£p lá»‡"

        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ok, code = self._api_unban(sid)
        status = f"âœ… ÄÃ£ XÃ¡c Minh âœ… {code}" if ok else f"âŒ HTTP {code}"
        msg = (
            f"ðŸ”“ UNBAN  [{ts_now}]\n"
            f"   SteamID       : {sid}\n"
            f"   Káº¿t quáº£ tháº©m phÃ¡n   : {status}\n"
            f"   Nguá»“n thao tÃ¡c: {source}"
        )
        self._antibug_log(msg)

        try:
            with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{'â”€'*60}\n"
                    f"  [UNBAN]  {ts_now}  â€” {source}\n"
                    f"  SteamID  : {sid}\n"
                    f"  API Unban: {status}\n"
                    f"{'â”€'*60}\n\n"
                )
        except Exception:
            pass

        if self.antibug_discord_alert.get():
            threading.Thread(
                target=self._send_antibug_discord,
                args=(f"ðŸ”“ **[ANTIBUG â€” Gá»  BAN]**\n"
                      f"ðŸ†” **SteamID:** `{sid}`\n"
                      f"ðŸ• **Thá»i gian:** `{ts_now}`\n"
                      f"ðŸ“ **Nguá»“n thao tÃ¡c:** `{source}`\n"
                      f"ðŸŒ **Káº¿t quáº£ tháº©m phÃ¡n gá»¡ ban:** {status}",),
                daemon=True
            ).start()

        return ok, f"{status}\nSteamID: {sid}"

    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    #  PALDEFENDER REST API HELPERS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    def _pdapi_ensure_token(self) -> str:
        """Äá»c hoáº·c tá»± táº¡o token cho PalDefender REST API.
        Tráº£ vá» chuá»—i token. Táº¡o file serverpal_manager.json náº¿u chÆ°a cÃ³."""
        try:
            os.makedirs(PALDEF_TOKEN_DIR, exist_ok=True)
            if os.path.isfile(PALDEF_TOKEN_FILE):
                with open(PALDEF_TOKEN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                token = data.get("Token", "").strip()
                if token:
                    return token
            # Táº¡o token má»›i
            token = secrets.token_urlsafe(48)
            with open(PALDEF_TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump({"Token": token}, f, indent=4)
            self._enqueue_console(
                f"ðŸ”‘ [PD-API] ÄÃ£ táº¡o token má»›i â†’ {PALDEF_TOKEN_FILE}"
            )
            return token
        except Exception as e:
            self._enqueue_console(f"âŒ [PD-API] Lá»—i táº¡o token: {e}")
            return ""

    def _pdapi_headers(self) -> dict:
        """Tráº£ vá» Authorization header cho PalDefender API."""
        return {"Authorization": f"Bearer {self._pdapi_token}"}

    def _pdapi_get_version(self) -> dict:
        """GET /v1/pdapi/version â€” Kiá»ƒm tra káº¿t ná»‘i & version PalDefender."""
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
        """GET /v1/pdapi/guilds â€” Láº¥y danh sÃ¡ch táº¥t cáº£ guild."""
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
        """GET /v1/pdapi/guild/<guild_id> â€” Chi tiáº¿t 1 guild."""
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
        """POST /v1/pdapi/give â€” Grant EXP/item/pal/egg (atomic).
        payload vÃ­ dá»¥: {"EXP": 1000, "Item": [{"ItemID": "PalSphere", "Count": 10}]}
        Tráº£ vá» (ok: bool, data: dict)."""
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
        """VÃ²ng láº·p ná»n: cá»© 30s ping PD API 1 láº§n Ä‘á»ƒ cáº­p nháº­t status label."""
        while True:
            try:
                result = self._pdapi_get_version()
                if result["ok"]:
                    d = result["data"]
                    # Version cÃ³ thá»ƒ lÃ  string hoáº·c object {"Major":1,"Minor":7,"Patch":2}
                    ver = d.get("Version", d.get("version", ""))
                    if isinstance(ver, dict):
                        ver = (f"{ver.get('Major','?')}."
                               f"{ver.get('Minor','?')}."
                               f"{ver.get('Patch','?')}")
                    elif not ver:
                        # Thá»­ láº¥y trá»±c tiáº¿p tá»« root object
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
            # Cáº­p nháº­t label trÃªn UI thread
            try:
                self.root.after(0, self._pdapi_update_status_label)
            except Exception:
                pass
            time.sleep(30)

    def _pdapi_update_status_label(self):
        """Cáº­p nháº­t label tráº¡ng thÃ¡i PD API trÃªn UI."""
        try:
            if not hasattr(self, "_lbl_pdapi_status"):
                return
            if self._pdapi_status_ok:
                txt = f"ðŸŸ¢ Káº¿t ná»‘i OK  â”‚  PD v{self._pdapi_version}"
                clr = "#00ff88"
            else:
                txt = "ðŸ”´ KhÃ´ng káº¿t ná»‘i Ä‘Æ°á»£c PalDefender REST API"
                clr = "#ff4444"
            self._lbl_pdapi_status.config(text=txt, fg=clr)
        except Exception:
            pass

    def _send_antibug_discord(self, content: str):
        """Gá»­i cáº£nh bÃ¡o Ä‘áº¿n webhook AntiBug riÃªng biá»‡t (chi tiáº¿t hÆ¡n)."""
        antibug_enf.send_antibug_discord(
            self,
            content,
            _read_manager_cfg,
            ANTIBUG_WEBHOOK_URL,
            DISCORD_WEBHOOK_URL,
        )

    def _write_banlist(self, steamid: str, name: str, kick_count: int,
                       kick_details: list, ts_now: str, api_status: str):
        """Ghi báº£n ghi BAN vÃ o banlist.txt vá»›i Ä‘áº§y Ä‘á»§ thÃ´ng tin chi tiáº¿t."""
        antibug_enf.write_banlist(
            self, steamid, name, kick_count, kick_details, ts_now, api_status,
            ANTIBUG_BAN_FILE, ANTIBUG_MAX_KICKS
        )

    # â”€â”€ Core AntiBug enforcement â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _antibug_kick_player(self, steamid: str, name: str,
                              action_vn: str, count: int, obj: str):
        """PhÃ¡t cáº£nh bÃ¡o (REST API) â†’ Kick (REST API) â†’ theo dÃµi â†’ ban náº¿u cáº§n."""
        antibug_enf.antibug_kick_player(
            self, steamid, name, action_vn, count, obj, ANTIBUG_MAX_KICKS, ANTIBUG_KICK_WINDOW
        )

    def _antibug_ban_player(self, steamid: str, name: str, kick_count: int):
        """Ban vÄ©nh viá»…n qua REST API, ghi banlist.txt chi tiáº¿t, Discord chi tiáº¿t."""
        antibug_enf.antibug_ban_player(self, steamid, name, kick_count)

    # â”€â”€ NPC Attack / Capture Protection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _npc_attack_kick_player(self, steamid: str, player_name: str,
                                npc_name: str, npc_id: str, coords: str):
        """Kick ngÆ°á»i chÆ¡i khi phÃ¡t hiá»‡n táº¥n cÃ´ng NPC.
        Cooldown 60 giÃ¢y / ngÆ°á»i chÆ¡i Ä‘á»ƒ trÃ¡nh kick spam.
        Thá»±c hiá»‡n: thÃ´ng bÃ¡o â†’ kick API â†’ Discord cáº£nh bÃ¡o.
        """
        steamid = self._normalize_steamid(steamid)
        if not steamid:
            return

        now = time.time()
        ev  = self._npc_attack_events.get(steamid, {"last_kick": 0.0, "count": 0})

        # Cooldown 60 giÃ¢y â€” trÃ¡nh kick liÃªn tá»¥c cÃ¹ng 1 ngÆ°á»i
        if now - ev["last_kick"] < 60:
            return

        ev["last_kick"] = now
        ev["count"]    += 1
        self._npc_attack_events[steamid] = ev
        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        loc    = f"`{coords}`" if coords else "*khÃ´ng rÃµ*"

        # 1. Broadcast cáº£nh bÃ¡o toÃ n server
        self._api_announce(
            f"[CANH BAO] {player_name} da tan cong NPC ({npc_name}) va bi KICK!"
        )
        time.sleep(0.3)

        # 2. Kick qua REST API
        kick_reason = f"[NPC-ATTACK] Tan cong NPC '{npc_name}' ({npc_id}) â€” CANH BAO KICK"
        kick_ok, kick_code = self._api_kick(steamid, kick_reason)
        kick_status = f"âœ… ÄÃ£ XÃ¡c Minh âœ… {kick_code}" if kick_ok else f"âŒ HTTP {kick_code}"

        self._antibug_kick_total += 1

        # 3. Log UI console
        msg = (
            f"âš¡ NPC-ATTACK KICK #{self._antibug_kick_total}  [{ts_now}]\n"
            f"   NgÆ°á»i chÆ¡i   : {player_name}  ({steamid})\n"
            f"   NPC bá»‹ táº¥n cÃ´ng: {npc_name}  (ID: {npc_id})\n"
            f"   Tá»a Ä‘á»™       : {coords or 'N/A'}\n"
            f"   Vi pháº¡m láº§n  : {ev['count']}\n"
            f"   API Kick     : {kick_status}"
        )
        self._antibug_log(msg)

        # 4. Discord AntiBug webhook â€” thÃ´ng bÃ¡o Ä‘áº§y Ä‘á»§
        if self.antibug_discord_alert.get():
            disc = (
                f"âš¡ **[Táº¤N CÃ”NG NPC â€” AUTO KICK #{self._antibug_kick_total}]**\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"ðŸ‘¤ **NgÆ°á»i chÆ¡i:** `{player_name}`\n"
                f"ðŸ†” **SteamID:** `{steamid}`\n"
                f"ðŸ• **Thá»i gian:** `{ts_now}`\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"ðŸŽ¯ **NPC bá»‹ táº¥n cÃ´ng:** `{npc_name}`  `({npc_id})`\n"
                f"ðŸ“ **Tá»a Ä‘á»™:** {loc}\n"
                f"ðŸ”¢ **Vi pháº¡m láº§n:** {ev['count']}\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"ðŸ“‹ **HÃ nh vi vi pháº¡m:**\n"
                f"   > NgÆ°á»i chÆ¡i Ä‘Ã£ **cá»‘ Ã½ táº¥n cÃ´ng NPC thÆ°Æ¡ng nhÃ¢n** trÃªn server.\n"
                f"   > NPC nÃ y Ä‘Æ°á»£c báº£o vá»‡ â€” má»i hÃ nh vi táº¥n cÃ´ng / cá»‘ báº¯t Ä‘á»u bá»‹ xá»­ lÃ½.\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"âš–ï¸ **Xá»­ lÃ½:** KICK khá»i server (láº§n {ev['count']})\n"
                f"ðŸŒ **Káº¿t quáº£ tháº©m phÃ¡n kick:** {kick_status}\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"âš ï¸ *Tiáº¿p tá»¥c vi pháº¡m â†’ BAN VÄ¨NH VIá»„N khi báº¯t thÃ nh cÃ´ng NPC!*"
            )
            threading.Thread(
                target=self._send_antibug_discord,
                args=(disc,), daemon=True
            ).start()

    def _npc_capture_ban_player(self, steamid: str, player_name: str,
                                pal_name: str, pal_id: str, coords: str = ""):
        """Ban vÄ©nh viá»…n ngÆ°á»i chÆ¡i Ä‘Ã£ báº¯t thÃ nh cÃ´ng NPC (SalesPerson, BlackMarketTrader, â€¦).
        Thá»±c hiá»‡n: thÃ´ng bÃ¡o â†’ ban API â†’ ghi banlist.txt â†’ Discord Ä‘áº§y Ä‘á»§.
        """
        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        loc    = coords if coords else "N/A"

        # Sá»‘ láº§n Ä‘Ã£ bá»‹ kick trÆ°á»›c Ä‘Ã³ (do táº¥n cÃ´ng NPC)
        prior_kicks = self._npc_attack_events.get(
            self._normalize_steamid(steamid) or steamid, {}
        ).get("count", 0)

        # 1. Broadcast cáº£nh bÃ¡o toÃ n server
        self._api_announce(
            f"[BAN] {player_name} da bi BAN VINH VIEN vi bat NPC ({pal_name})!"
        )

        # 2. Ban qua REST API /ban
        ban_reason = (
            f"[NPC-CAPTURE] Bat NPC '{pal_name}' ({pal_id}) tai {loc} â€” AUTO-BAN VINH VIEN"
        )
        ban_ok, ban_code = self._api_ban(steamid, ban_reason)
        ban_status = f"âœ… ÄÃ£ XÃ¡c Minh âœ… {ban_code}" if ban_ok else f"âŒ HTTP {ban_code}"

        self._antibug_ban_total += 1

        # 3. Ghi banlist.txt chi tiáº¿t
        try:
            sep = "â•" * 72
            lines = [
                sep,
                f"  [BAN #{self._antibug_ban_total}]  {ts_now}  â€” NPC CAPTURE AUTO-BAN",
                sep,
                f"  TÃªn ingame    : {player_name}",
                f"  SteamID       : {steamid}",
                f"  Thá»i gian ban : {ts_now}",
                f"  HÃ nh vi       : Báº¯t thÃ nh cÃ´ng NPC '{pal_name}' (ID: {pal_id})",
                f"  Tá»a Ä‘á»™        : {loc}",
                f"  Kick trÆ°á»›c Ä‘Ã³ : {prior_kicks} láº§n (táº¥n cÃ´ng NPC)",
                f"  LÃ½ do ban     : Vi pháº¡m quy táº¯c báº£o vá»‡ NPC thÆ°Æ¡ng nhÃ¢n",
                f"  API Ban       : {ban_status}",
                f"", sep, "",
            ]
            with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i ghi banlist.txt (NPC ban): {e}")

        # 4. Log UI console
        msg = (
            f"ðŸš« NPC-CAPTURE BAN #{self._antibug_ban_total}  [{ts_now}]\n"
            f"   NgÆ°á»i chÆ¡i   : {player_name}  ({steamid})\n"
            f"   NPC bá»‹ báº¯t   : {pal_name}  (ID: {pal_id})\n"
            f"   Tá»a Ä‘á»™       : {loc}\n"
            f"   Kick trÆ°á»›c Ä‘Ã³: {prior_kicks} láº§n\n"
            f"   API Ban      : {ban_status}\n"
            f"   File         : banlist.txt Ä‘Ã£ Ä‘Æ°á»£c cáº­p nháº­t"
        )
        self._antibug_log(msg)

        # 5. Discord AntiBug webhook â€” thÃ´ng bÃ¡o Ä‘áº§y Ä‘á»§
        if self.antibug_discord_alert.get():
            prior_txt = (f"âš¡ ÄÃ£ bá»‹ kick **{prior_kicks} láº§n** trÆ°á»›c Ä‘Ã³ do táº¥n cÃ´ng NPC"
                         if prior_kicks > 0 else "*(chÆ°a cÃ³ lá»‹ch sá»­ kick NPC)*")
            disc = (
                f"ðŸš« **[Báº®T NPC â€” BAN VÄ¨NH VIá»„N #{self._antibug_ban_total}]**\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"ðŸ‘¤ **NgÆ°á»i chÆ¡i:** `{player_name}`\n"
                f"ðŸ†” **SteamID:** `{steamid}`\n"
                f"ðŸ• **Thá»i gian:** `{ts_now}`\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"ðŸŽ¯ **NPC bá»‹ báº¯t:** `{pal_name}`  `({pal_id})`\n"
                f"ðŸ“ **Tá»a Ä‘á»™:** `{loc}`\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"ðŸ“‹ **HÃ nh vi vi pháº¡m:**\n"
                f"   > NgÆ°á»i chÆ¡i Ä‘Ã£ **báº¯t thÃ nh cÃ´ng NPC thÆ°Æ¡ng nhÃ¢n** báº±ng Palsphere.\n"
                f"   > ÄÃ¢y lÃ  hÃ nh vi phÃ¡ hoáº¡i nghiÃªm trá»ng â€” NPC bá»‹ xÃ³a khá»i tháº¿ giá»›i game.\n"
                f"   > Lá»‹ch sá»­: {prior_txt}\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f"âš–ï¸ **Xá»­ lÃ½:** BAN VÄ¨NH VIá»„N (khÃ´ng thá»ƒ vÃ o server)\n"
                f"ðŸŒ **Káº¿t quáº£ tháº©m phÃ¡n ban:** {ban_status}\n"
                f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                f">>> â›” **ÄÃƒ BAN VÄ¨NH VIá»„N** â€” ghi vÃ o `banlist.txt` <<<"
            )
            threading.Thread(
                target=self._send_antibug_discord,
                args=(disc,), daemon=True
            ).start()

    # â”€â”€ Tech-Cheat System â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _techbug_check_event(self, steamid: str, name: str, tech_raw: str,
                             source: str = "natural"):
        """
        Kiá»ƒm tra tech-cheat khi phÃ¡t hiá»‡n sá»± kiá»‡n má»Ÿ khÃ³a cÃ´ng nghá»‡.

        source = "natural"   â†’ 'X' (...) unlocking Technology: 'Y'  (há»c tá»± nhiÃªn)
        source = "learntech" â†’ Replying to 'X': "Successfully unlocked technology 'Y'"
                               (admin dÃ¹ng /learntech â€” cheat)
        source = "build"     â†’ 'X' (...) has build a 'Y' (xÃ¢y dá»±ng)
        """
        if not self.antibug_techcheck_enabled.get():
            return

        # â”€â”€ XÃ¡c Ä‘á»‹nh Ä‘Ã¢y lÃ  admin cheat (learntech) hay há»c tá»± nhiÃªn â”€â”€â”€â”€â”€â”€â”€â”€â”€
        is_admin = steamid in self._admin_mode_players
        is_learntech = (source == "learntech")
        is_build = (source == "build")

        if is_learntech:
            # /learntech luÃ´n lÃ  hÃ nh vi cheat (admin dÃ¹ng lá»‡nh Ä‘á»ƒ má»Ÿ khÃ³a tá»©c thÃ¬)
            # Chá»‰ bá» qua náº¿u "Ban cáº£ Admin" Táº®T
            if not self.techcheck_ban_admin.get():
                self._antibug_log_queue.put(
                    f"[TECH-CHECK] /learntech '{tech_raw}' â€” {name} admin mode, "
                    f"'Ban Admin' Táº®T â†’ bá» qua."
                )
                return
            # Náº¿u "Ban Admin" Báº¬T â†’ tiáº¿p tá»¥c check vÃ  ban
        else:
            # Há»c tá»± nhiÃªn â€” bá» qua náº¿u Ä‘ang admin mode vÃ  "Ban Admin" Táº®T
            # Há»c tá»± nhiÃªn hoáº·c XÃ¢y dá»±ng â€” bá» qua náº¿u Ä‘ang admin mode vÃ  "Ban Admin" Táº®T
            if is_admin and not self.techcheck_ban_admin.get():
                return

        # â”€â”€ Lookup DB theo internal code (case-insensitive) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tech_key  = tech_raw.lower().strip()
        req_level = TECH_LEVEL_DB.get(tech_key)

        if req_level is None:
            self._antibug_log_queue.put(
                f"[TECH-DB MISS] '{tech_raw}' â€” chÆ°a cÃ³ trong DB, bá» qua ({name})"
            )
            return

        # â”€â”€ Láº¥y level tá»« cache; náº¿u trá»‘ng â†’ fetch API ngay â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        player_level = self._player_level_cache.get(steamid, 0)
        if player_level <= 0:
            self._antibug_log_queue.put(
                f"[TECH-CHECK] Cache miss cho {name} â€” Ä‘ang fetch API..."
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
                    f"[TECH-CHECK] Lá»—i fetch API: {e}"
                )

        if player_level <= 0:
            self._antibug_log_queue.put(
                f"[TECH-CHECK] KhÃ´ng láº¥y Ä‘Æ°á»£c level cá»§a {name} "
                f"({steamid}) â€” bá» qua Ä‘á»ƒ trÃ¡nh false positive"
            )
            return

        # â”€â”€ Log chi tiáº¿t sá»± kiá»‡n Ä‘á»ƒ debug â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        src_label = "ðŸ”§/learntech" if is_learntech else "ðŸ“–Tá»± há»c"
        if is_learntech:
            src_label = "ðŸ”§/learntech"
        elif is_build:
            src_label = "ðŸ”¨XÃ¢y dá»±ng"
        else:
            src_label = "ðŸ“–Tá»± há»c"
            
        self._antibug_log_queue.put(
            f"[TECH-CHECK] [{src_label}] {name} (Lv.{player_level}) â†’ "
            f"'{tech_raw}' (cáº§n Lv.{req_level})"
        )

        if player_level >= req_level:
            return  # Há»£p lá»‡ â€” level Ä‘á»§

        # â”€â”€ Vi pháº¡m! â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        gap    = req_level - player_level
        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cheat_type = "ADMIN /learntech CHEAT" if is_learntech else "TECH-CHEAT tá»± há»c vÆ°á»£t cáº¥p"
        if is_learntech:
            cheat_type = "ADMIN /learntech CHEAT"
        elif is_build:
            cheat_type = "BUILD-CHEAT xÃ¢y dá»±ng vÆ°á»£t cáº¥p"
        else:
            cheat_type = "TECH-CHEAT tá»± há»c vÆ°á»£t cáº¥p"
            
        msg = (
            f"ðŸ”¬ {cheat_type} PHÃT HIá»†N  [{ts_now}]\n"
            f"   NgÆ°á»i chÆ¡i      : {name}  ({steamid})\n"
            f"   Level hiá»‡n táº¡i  : {player_level}\n"
            f"   CÃ´ng nghá»‡       : '{tech_raw}'\n"
            f"   Level cáº§n thiáº¿t : {req_level}\n"
            f"   Nguá»“n phÃ¡t hiá»‡n : {src_label}\n"
            f"   VÆ°á»£t cáº¥p        : +{gap} level â†’ BAN Ä‘ang xá»­ lÃ½..."
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
        """XÃ¡c nháº­n level thá»±c táº¿ tá»« API rá»“i ban ngÆ°á»i chÆ¡i tech-cheat."""

        cheat_label = "ADMIN /learntech CHEAT" if is_learntech else "TECH-CHEAT"
        src_icon    = "ðŸ”§" if is_learntech else "ðŸ”¬"
        is_learntech = (source == "learntech")
        is_build = (source == "build")

        if is_learntech:
            cheat_label = "ADMIN /learntech CHEAT"
            src_icon    = "ðŸ”§"
        elif is_build:
            cheat_label = "BUILD-CHEAT"
            src_icon    = "ðŸ”¨"
        else:
            cheat_label = "TECH-CHEAT"
            src_icon    = "ðŸ”¬"

        # â”€â”€ Vá»›i learntech: KHÃ”NG cáº§n xÃ¡c nháº­n level vÃ¬ Ä‘Ã¢y lÃ  lá»‡nh cheat rÃµ rÃ ng â”€
        # â”€â”€ Vá»›i tá»± há»c: xÃ¡c nháº­n láº¡i Ä‘á»ƒ trÃ¡nh false positive â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # â”€â”€ Vá»›i tá»± há»c/xÃ¢y dá»±ng: xÃ¡c nháº­n láº¡i Ä‘á»ƒ trÃ¡nh false positive â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

            # Há»§y náº¿u level thá»±c táº¿ Ä‘á»§ (false positive)
            if confirmed_level > 0 and confirmed_level >= req_level:
                self._antibug_log(
                    f"âœ… FALSE POSITIVE Há»¦Y: {name} level thá»±c táº¿ "
                    f"{confirmed_level} >= yÃªu cáº§u {req_level} â€” khÃ´ng ban"
                )
                return
        else:
            # /learntech â†’ luÃ´n ban, khÃ´ng cáº§n xÃ¡c nháº­n láº¡i
            # Cá»‘ fetch Ä‘á»ƒ ghi chÃ­nh xÃ¡c level thá»±c táº¿ vÃ o log
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

        # â”€â”€ Ban via REST API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ban_reason = (
            f"[{cheat_label}] '{tech_raw}' can Lv.{req_level}, "
            f"level hien tai {confirmed_level} (+{gap})"
        )
        ban_ok, ban_code = self._api_ban(steamid, ban_reason)
        ban_status = f"âœ… ÄÃ£ XÃ¡c Minh âœ… {ban_code}" if ban_ok else f"âŒ HTTP {ban_code}"

        # â”€â”€ Broadcast toÃ n server â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        # â”€â”€ Ghi banlist.txt chi tiáº¿t â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._antibug_ban_total += 1
        sep = "â•" * 72
        try:
            with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{sep}\n"
                    f"  [BAN #{self._antibug_ban_total} â€” {cheat_label}]  {ts_now}\n"
                    f"{sep}\n"
                    f"  TÃªn ingame        : {name}\n"
                    f"  SteamID           : {steamid}\n"
                    f"  Loáº¡i vi pháº¡m      : {'DÃ¹ng lá»‡nh /learntech má»Ÿ khÃ³a cheat' if is_learntech else 'Má»Ÿ khÃ³a cÃ´ng nghá»‡ vÆ°á»£t cáº¥p (há»c tá»± nhiÃªn)'}\n"
                    f"  Loáº¡i vi pháº¡m      : {'DÃ¹ng lá»‡nh /learntech má»Ÿ khÃ³a cheat' if is_learntech else 'XÃ¢y dá»±ng cÃ´ng trÃ¬nh vÆ°á»£t cáº¥p' if is_build else 'Má»Ÿ khÃ³a cÃ´ng nghá»‡ vÆ°á»£t cáº¥p (há»c tá»± nhiÃªn)'}\n"
                    f"  CÃ´ng nghá»‡ vi pháº¡m : '{tech_raw}'\n"
                    f"  Level cáº§n thiáº¿t   : {req_level}\n"
                    f"  Level thá»±c táº¿     : {confirmed_level}\n"
                    f"  VÆ°á»£t cáº¥p          : +{gap} level\n"
                    f"  Nguá»“n phÃ¡t hiá»‡n   : {'PalServer.log â€” /learntech command' if is_learntech else 'PalServer.log â€” unlocking Technology'}\n"
                    f"  Nguá»“n phÃ¡t hiá»‡n   : {'PalServer.log â€” /learntech command' if is_learntech else 'PalServer.log â€” has build a' if is_build else 'PalServer.log â€” unlocking Technology'}\n"
                    f"  API Ban           : {ban_status}\n"
                    f"  Thá»i gian         : {ts_now}\n"
                    f"  Nguá»“n DB          : https://paldeck.cc/technology\n"
                    f"{sep}\n\n"
                )
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i ghi banlist: {e}")

        # â”€â”€ Log UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._antibug_log(
            f"{src_icon} BAN #{self._antibug_ban_total} [{cheat_label}]  [{ts_now}]\n"
            f"   {name} ({steamid})\n"
            f"   '{tech_raw}'  â”‚  Lv.{confirmed_level} < yÃªu cáº§u Lv.{req_level} "
            f"(+{gap})  â”‚  API: {ban_status}"
        )

        # â”€â”€ Discord chi tiáº¿t â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if self.antibug_discord_alert.get():
            if is_learntech:
                discord_title = f"ðŸ”§ **[ADMIN /learntech CHEAT â€” BAN VÄ¨NH VIá»„N #{self._antibug_ban_total}]**"
                discord_footer = ">>> â›” **ÄÃƒ BAN VÄ¨NH VIá»„N** â€” admin dÃ¹ng /learntech Ä‘á»ƒ cheat cÃ´ng nghá»‡ vÆ°á»£t cáº¥p <<<"
                violation_type = "DÃ¹ng lá»‡nh /learntech (admin command cheat)"
            elif is_build:
                discord_title = f"ðŸ”¨ **[BUILD-CHEAT â€” BAN VÄ¨NH VIá»„N #{self._antibug_ban_total}]**"
                discord_footer = ">>> â›” **ÄÃƒ BAN VÄ¨NH VIá»„N** â€” xÃ¢y dá»±ng cÃ´ng trÃ¬nh vÆ°á»£t cáº¥p <<<"
                violation_type = "XÃ¢y dá»±ng cÃ´ng trÃ¬nh vÆ°á»£t cáº¥p (tool/hack)"
            else:
                discord_title = f"ðŸ”¬ **[TECH-CHEAT â€” BAN VÄ¨NH VIá»„N #{self._antibug_ban_total}]**"
                discord_footer = ">>> â›” **ÄÃƒ BAN VÄ¨NH VIá»„N** â€” dÃ¹ng tool má»Ÿ khÃ³a cÃ´ng nghá»‡ vÆ°á»£t cáº¥p <<<"
                violation_type = "Há»c tá»± nhiÃªn cÃ´ng nghá»‡ vÆ°á»£t cáº¥p (tool/hack)"
            threading.Thread(
                target=self._send_antibug_discord,
                args=(
                    f"{discord_title}\n"
                    f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                    f"ðŸ‘¤ **NgÆ°á»i chÆ¡i:** {name}\n"
                    f"ðŸ†” **SteamID:** `{steamid}`\n"
                    f"ðŸ• **Thá»i gian:** `{ts_now}`\n"
                    f"ðŸ”¬ **CÃ´ng nghá»‡ vi pháº¡m:** `{tech_raw}`\n"
                    f"ðŸ“Š **Level cáº§n thiáº¿t:** `{req_level}`  â”‚  "
                    f"**Level thá»±c táº¿:** `{confirmed_level}`\n"
                    f"âš¡ **VÆ°á»£t cáº¥p:** `+{gap} level`\n"
                    f"âš ï¸ **Loáº¡i vi pháº¡m:** {violation_type}\n"
                    f"ðŸŒ **Káº¿t quáº£ tháº©m phÃ¡n ban:** {ban_status}\n"
                    f"ðŸ“š **DB nguá»“n:** https://paldeck.cc/technology\n"
                    f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                    f"{discord_footer}",
                ),
                daemon=True
            ).start()

    def _buildbug_check_event(self, steamid: str, name: str, item_name: str):
        """
        Kiá»ƒm tra build-cheat khi phÃ¡t hiá»‡n sá»± kiá»‡n xÃ¢y dá»±ng.
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
                    f"[BUILD-CHECK] Lá»—i fetch API: {e}"
                )

        if player_level <= 0:
            self._antibug_log_queue.put(
                f"[BUILD-CHECK] KhÃ´ng láº¥y Ä‘Æ°á»£c level cá»§a {name} ({steamid}) â€” bá» qua"
            )
            return

        self._antibug_log_queue.put(
            f"[BUILD-CHECK] [ðŸ—ï¸XÃ¢y dá»±ng] {name} (Lv.{player_level}) â†’ "
            f"'{item_name}' (cáº§n Lv.{req_level})"
        )

        if player_level >= req_level:
            return  # Há»£p lá»‡

        gap = req_level - player_level
        ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"ðŸ—ï¸ BUILD-CHEAT PHÃT HIá»†N  [{ts_now}]\n"
            f"   NgÆ°á»i chÆ¡i      : {name}  ({steamid})\n"
            f"   Level hiá»‡n táº¡i  : {player_level}\n"
            f"   CÃ´ng trÃ¬nh      : '{item_name}'\n"
            f"   Level cáº§n thiáº¿t : {req_level}\n"
            f"   VÆ°á»£t cáº¥p        : +{gap} level â†’ BAN Ä‘ang xá»­ lÃ½..."
        )
        self._antibug_log(msg)

        threading.Thread(
            target=self._buildbug_ban,
            args=(steamid, name, item_name, player_level, req_level, gap, ts_now),
            daemon=True
        ).start()

    def _buildbug_ban(self, steamid: str, name: str, item_name: str,
                      cached_level: int, req_level: int, gap: int, ts_now: str):
        """XÃ¡c nháº­n level thá»±c táº¿ tá»« API rá»“i ban ngÆ°á»i chÆ¡i build-cheat."""
        
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
                f"âœ… FALSE POSITIVE Há»¦Y: {name} level thá»±c táº¿ "
                f"{confirmed_level} >= yÃªu cáº§u {req_level} â€” khÃ´ng ban"
            )
            return

        ban_reason = (
            f"[BUILD-CHEAT] Built '{item_name}' (req Lv.{req_level}) "
            f"at Lv.{confirmed_level} (+{gap})"
        )
        ban_ok, ban_code = self._api_ban(steamid, ban_reason)
        ban_status = f"âœ… ÄÃ£ XÃ¡c Minh âœ… {ban_code}" if ban_ok else f"âŒ HTTP {ban_code}"

        announce_msg = (
            f"[BUILD-CHEAT] {name} (Lv.{confirmed_level}) bi BAN vi xay dung "
            f"'{item_name}' (can Lv.{req_level}) ma khong can mo khoa!"
        )
        self._api_announce(announce_msg)

        self._antibug_ban_total += 1
        sep = "â•" * 72
        try:
            with open(ANTIBUG_BAN_FILE, "a", encoding="utf-8") as f:
                f.write(
                    f"\n{sep}\n"
                    f"  [BAN #{self._antibug_ban_total} â€” BUILD-CHEAT]  {ts_now}\n"
                    f"{sep}\n"
                    f"  TÃªn ingame        : {name}\n"
                    f"  SteamID           : {steamid}\n"
                    f"  Loáº¡i vi pháº¡m      : XÃ¢y dá»±ng cÃ´ng trÃ¬nh vÆ°á»£t cáº¥p\n"
                    f"  CÃ´ng trÃ¬nh        : '{item_name}'\n"
                    f"  Level cáº§n thiáº¿t   : {req_level}\n"
                    f"  Level thá»±c táº¿     : {confirmed_level}\n"
                    f"  VÆ°á»£t cáº¥p          : +{gap} level\n"
                    f"  API Ban           : {ban_status}\n"
                    f"  Thá»i gian         : {ts_now}\n"
                    f"{sep}\n\n"
                )
        except Exception as e:
            self._enqueue_console(f"âŒ Lá»—i ghi banlist: {e}")

        self._antibug_log(
            f"ðŸ—ï¸ BAN #{self._antibug_ban_total} [BUILD-CHEAT]  [{ts_now}]\n"
            f"   {name} ({steamid})\n"
            f"   '{item_name}'  â”‚  Lv.{confirmed_level} < yÃªu cáº§u Lv.{req_level} "
            f"(+{gap})  â”‚  API: {ban_status}"
        )

        if self.antibug_discord_alert.get():
            discord_title = f"ðŸ—ï¸ **[BUILD-CHEAT â€” BAN VÄ¨NH VIá»„N #{self._antibug_ban_total}]**"
            discord_footer = ">>> â›” **ÄÃƒ BAN VÄ¨NH VIá»„N** â€” xÃ¢y dá»±ng cÃ´ng trÃ¬nh vÆ°á»£t cáº¥p <<<"
            threading.Thread(
                target=self._send_antibug_discord,
                args=(
                    f"{discord_title}\n"
                    f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                    f"ðŸ‘¤ **NgÆ°á»i chÆ¡i:** {name}\n"
                    f"ðŸ†” **SteamID:** `{steamid}`\n"
                    f"ðŸ• **Thá»i gian:** `{ts_now}`\n"
                    f"ðŸ—ï¸ **CÃ´ng trÃ¬nh:** `{item_name}`\n"
                    f"ðŸ“Š **Level cáº§n thiáº¿t:** `{req_level}`  â”‚  "
                    f"**Level thá»±c táº¿:** `{confirmed_level}`\n"
                    f"âš¡ **VÆ°á»£t cáº¥p:** `+{gap} level`\n"
                    f"ðŸŒ **Káº¿t quáº£ tháº©m phÃ¡n ban:** {ban_status}\n"
                    f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
                    f"{discord_footer}",
                ),
                daemon=True
            ).start()

    def _antibug_open_log(self):
        """Má»Ÿ file antibug_log.txt báº±ng Notepad."""
        try:
            antibug_enf.antibug_open_log(ANTIBUG_LOG_FILE)
        except Exception as e:
            messagebox.showerror("Lá»—i", f"KhÃ´ng thá»ƒ má»Ÿ file log: {e}")

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: PALDEFENDER
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _load_paldef_log_history(self):
        """Táº£i 200 dÃ²ng cuá»‘i cá»§a PalDefender session log vÃ o paldef_console."""
        if not hasattr(self, "paldef_console") or not self.paldef_console.winfo_exists():
            return
        try:
            lf = self._find_latest_paldef_log()
            if not lf:
                self.paldef_console.insert(
                    tk.END,
                    f"âš ï¸ KhÃ´ng tÃ¬m tháº¥y file log PalDefender táº¡i:\n  {PALDEF_LOG_DIR}\n"
                )
                return
            fname = os.path.basename(lf)
            # Cáº­p nháº­t label tÃªn file náº¿u cÃ³
            if hasattr(self, "_lbl_paldef_file"):
                self._lbl_paldef_file.config(text=f"ðŸ“‚ {fname}")
            with open(lf, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            tail = lines[-200:] if len(lines) > 200 else lines
            self.paldef_console.delete("1.0", tk.END)
            if len(lines) > 200:
                self.paldef_console.insert(
                    tk.END,
                    f"â”€â”€â”€ 200 dÃ²ng cuá»‘i / tá»•ng {len(lines)} dÃ²ng â€” {fname} â”€â”€â”€\n\n"
                )
            for line in tail:
                self.paldef_console.insert(tk.END, line)
            self.paldef_console.see(tk.END)
        except Exception as e:
            self.paldef_console.insert(tk.END, f"âŒ Lá»—i Ä‘á»c log: {e}\n")

    def _load_paldef_cheat_history(self):
        """Táº£i toÃ n bá»™ ná»™i dung cheat log má»›i nháº¥t vÃ o paldef_cheat_console."""
        if not hasattr(self, "paldef_cheat_console") or \
           not self.paldef_cheat_console.winfo_exists():
            return
        try:
            cf = self._find_latest_paldef_cheat()
            if not cf:
                self.paldef_cheat_console.insert(
                    tk.END, "âœ… ChÆ°a cÃ³ log cheat nÃ o â€” server sáº¡ch!\n"
                )
                return
            fname = os.path.basename(cf)
            with open(cf, "r", encoding="utf-8", errors="replace") as f:
                lines = [ln.rstrip("\n") for ln in f.readlines()]
            self.paldef_cheat_console.delete("1.0", tk.END)
            self.paldef_cheat_console.insert(
                tk.END, f"â”€â”€â”€ {fname} â”€â”€â”€\n\n"
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
                        self.paldef_cheat_console.insert(tk.END, f"â†³ (gá»™p {cnt} dÃ²ng trÃ¹ng)\n")
                prev = line
                cnt = 1
            if prev is not None:
                self.paldef_cheat_console.insert(tk.END, prev + "\n")
                if cnt > 1:
                    self.paldef_cheat_console.insert(tk.END, f"â†³ (gá»™p {cnt} dÃ²ng trÃ¹ng)\n")
            self.paldef_cheat_console.see(tk.END)
        except Exception as e:
            self.paldef_cheat_console.insert(tk.END, f"âŒ Lá»—i Ä‘á»c cheat log: {e}\n")

    def draw_paldefender(self):
        # TiÃªu Ä‘á»
        tk.Label(self.container, text="ðŸ›¡ï¸  PALDEFENDER ANTI-CHEAT",
                 bg="#0a0a0a", fg="#ff9900",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 4))

        # Info bar
        info_bar = tk.Frame(self.container, bg="#0a0a0a")
        info_bar.pack(fill="x", pady=(0, 6))
        self._lbl_paldef_file = tk.Label(
            info_bar, text="ðŸ“‚ (Ä‘ang tÃ¬m file...)",
            bg="#0a0a0a", fg="#666", font=("Consolas", 8)
        )
        self._lbl_paldef_file.pack(side="left")

        # PanedWindow
        paned = tk.PanedWindow(self.container, orient="vertical",
                               bg="#444", sashwidth=6, sashrelief="flat")
        paned.pack(fill="both", expand=True)

        # â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
        # â•‘  TOP â€” SESSION LOG                   â•‘
        # â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        top_f = tk.Frame(paned, bg="#0a0a0a")
        paned.add(top_f, minsize=180)

        # Header
        hdr = tk.Frame(top_f, bg="#1a0e00", pady=5)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ðŸ“‹  SESSION LOG (real-time)",
                 bg="#1a0e00", fg="#ff9900",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
        self._paldef_autoscroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(hdr, text="Auto-scroll",
                       variable=self._paldef_autoscroll_var,
                       bg="#1a0e00", fg="#888", selectcolor="#1a0e00",
                       activebackground="#1a0e00",
                       font=("Segoe UI", 9)).pack(side="left", padx=6)
        tk.Button(hdr, text="ðŸ”„ Táº£i láº¡i",
                  bg="#2a1a00", fg="#ff9900", relief="flat", padx=10,
                  command=self._load_paldef_log_history).pack(side="right", padx=4)
        tk.Button(hdr, text="ðŸ—‘ XÃ³a",
                  bg="#2a1a1a", fg="#ff7777", relief="flat", padx=10,
                  command=lambda: self.paldef_console.delete("1.0", tk.END)
                  ).pack(side="right", padx=4)

        # Filter
        flt_bar = tk.Frame(top_f, bg="#0a0a0a", pady=3)
        flt_bar.pack(fill="x", padx=6)
        tk.Label(flt_bar, text="ðŸ” Lá»c:", bg="#0a0a0a", fg="#666",
                 font=("Segoe UI", 9)).pack(side="left")
        self._paldef_filter_var = tk.StringVar()
        tk.Entry(flt_bar, textvariable=self._paldef_filter_var,
                 bg="#111", fg="#ccc", bd=0, font=("Consolas", 9),
                 insertbackground="#ccc",
                 width=36).pack(side="left", padx=6, ipady=3)
        tk.Label(flt_bar, text="(vÃ­ dá»¥: error, warning, player)",
                 bg="#0a0a0a", fg="#444", font=("Segoe UI", 8)).pack(side="left")

        # Console session log
        self.paldef_console = scrolledtext.ScrolledText(
            top_f, bg="#0f0a00", fg="#ffcc77",
            font=("Consolas", 9), bd=0, insertbackground="#ffcc77"
        )
        self.paldef_console.pack(fill="both", expand=True, padx=2)

        # â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
        # â•‘  BOTTOM â€” NOTEBOOK: Cheats | AntiBug    â•‘
        # â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
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

        # â”€â”€ Tab 1: CHEAT DETECTIONS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        cheat_tab = tk.Frame(nb, bg="#0f0000")
        nb.add(cheat_tab, text="  ðŸš¨ CHEAT DETECTIONS  ")

        cheat_hdr = tk.Frame(cheat_tab, bg="#1a0000", pady=5)
        cheat_hdr.pack(fill="x")
        tk.Label(cheat_hdr, text="ðŸš¨  PALDEFENDER CHEAT LOG",
                 bg="#1a0000", fg="#ff4444",
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
        tk.Checkbutton(
            cheat_hdr, text="ðŸ“£ Antibug Discord",
            variable=self.paldef_discord_alert,
            bg="#1a0000", fg="#ff9900", selectcolor="#1a0000",
            activebackground="#1a0000",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=12)
        tk.Checkbutton(
            cheat_hdr, text="ðŸ“¢ Chat Discord",
            variable=self.paldef_discord_alert_main,
            bg="#1a0000", fg="#7289da", selectcolor="#1a0000",
            activebackground="#1a0000",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=4)
        tk.Checkbutton(
            cheat_hdr, text="ðŸ§¹ Auto dá»n log",
            variable=self.paldef_log_cleanup_enabled,
            bg="#1a0000", fg="#66cc99", selectcolor="#1a0000",
            activebackground="#1a0000",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(8, 2))
        tk.Label(cheat_hdr, text="Giá»¯:",
                 bg="#1a0000", fg="#777", font=("Segoe UI", 8)).pack(side="left")
        ttk.Combobox(
            cheat_hdr, textvariable=self.paldef_log_keep_hours,
            values=["24", "12", "6", "4", "2"],
            state="readonly", width=4
        ).pack(side="left", padx=(4, 4))
        tk.Label(cheat_hdr, text="giá»",
                 bg="#1a0000", fg="#777", font=("Segoe UI", 8)).pack(side="left")
        tk.Button(cheat_hdr, text="ðŸ”„ Táº£i láº¡i",
                  bg="#2a0000", fg="#ff4444", relief="flat", padx=10,
                  command=self._load_paldef_cheat_history).pack(side="right", padx=4)
        tk.Button(cheat_hdr, text="ðŸ§½ Dá»n ngay",
                  bg="#2a2200", fg="#ffcc66", relief="flat", padx=10,
                  command=self._cleanup_paldef_logs_once).pack(side="right", padx=4)
        tk.Button(cheat_hdr, text="ðŸ“‚ Má»Ÿ thÆ° má»¥c",
                  bg="#1a0000", fg="#888", relief="flat", padx=10,
                  command=lambda: subprocess.Popen(
                      f'explorer "{PALDEF_CHEATS_DIR}"')
                  ).pack(side="right", padx=4)
        self.paldef_cheat_console = scrolledtext.ScrolledText(
            cheat_tab, bg="#0f0000", fg="#ff6666",
            font=("Consolas", 9), bd=0, insertbackground="#ff6666"
        )
        self.paldef_cheat_console.pack(fill="both", expand=True, padx=2)

        # â”€â”€ Tab 2: ANTIBUG MONITOR â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        ab_tab = tk.Frame(nb, bg="#0a0a12")
        nb.add(ab_tab, text="  ðŸ¤– ANTIBUG MONITOR  ")

        # Config bar
        ab_cfg = tk.Frame(ab_tab, bg="#0a0a1a", pady=6)
        ab_cfg.pack(fill="x")

        tk.Checkbutton(ab_cfg, text="ðŸ¤– ANTIBUG",
                       variable=self.antibug_enabled,
                       bg="#0a0a1a", fg="#00ffcc", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)

        tk.Label(ab_cfg, text="NgÆ°á»¡ng:",
                 bg="#0a0a1a", fg="#aaa",
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Spinbox(ab_cfg, from_=1, to=20,
                   textvariable=self.antibug_max_per_sec,
                   width=4, bg="#111", fg="#ffcc00",
                   buttonbackground="#222",
                   font=("Consolas", 9, "bold")).pack(side="left", padx=(2, 3))
        tk.Label(ab_cfg, text="cÃ´ng trÃ¬nh/giÃ¢y â†’ kick",
                 bg="#0a0a1a", fg="#666",
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))

        tk.Checkbutton(ab_cfg, text="ðŸ“£ Discord",
                       variable=self.antibug_discord_alert,
                       bg="#0a0a1a", fg="#ff9900", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9)).pack(side="left", padx=4)

        tk.Checkbutton(ab_cfg, text="ðŸ”¬ Tech-Cheat",
                       variable=self.antibug_techcheck_enabled,
                       bg="#0a0a1a", fg="#cc88ff", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        tk.Checkbutton(ab_cfg, text="ðŸ› ï¸ Build-Cheat",
                       variable=self.antibug_buildcheck_enabled,
                       bg="#0a0a1a", fg="#ff77aa", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=4)
        tk.Label(ab_cfg, text=f"({len(TECH_LEVEL_DB)} tech)",
                 bg="#0a0a1a", fg="#554466",
                 font=("Segoe UI", 7)).pack(side="left")

        tk.Checkbutton(ab_cfg, text="ðŸ”´ Ban cáº£ Admin",
                       variable=self.techcheck_ban_admin,
                       bg="#0a0a1a", fg="#ff4444", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 8)).pack(side="left", padx=(6, 2))
        tk.Label(ab_cfg, text="(ká»ƒ cáº£ admin mode)",
                 bg="#0a0a1a", fg="#552222",
                 font=("Segoe UI", 7)).pack(side="left")

        tk.Checkbutton(ab_cfg, text="âš¡ Kick NPC",
                       variable=self.npc_attack_kick_enabled,
                       bg="#0a0a1a", fg="#ffaa00", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 2))
        tk.Checkbutton(ab_cfg, text="ðŸš« Ban NPC",
                       variable=self.npc_capture_ban_enabled,
                       bg="#0a0a1a", fg="#ff6600", selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9, "bold")).pack(side="left", padx=(6, 2))
        tk.Label(ab_cfg, text="(Merchant, BlackMarketâ€¦)",
                 bg="#0a0a1a", fg="#553300",
                 font=("Segoe UI", 7)).pack(side="left")

        tk.Button(ab_cfg, text="ðŸ“„ Má»Ÿ log file",
                  bg="#1a1a2a", fg="#aaaaff", relief="flat", padx=10,
                  command=self._antibug_open_log).pack(side="right", padx=6)
        tk.Button(ab_cfg, text="ðŸ—‘ XÃ³a console",
                  bg="#1a1a2a", fg="#888", relief="flat", padx=10,
                  command=lambda: self.antibug_console.delete("1.0", tk.END)
                  ).pack(side="right", padx=4)

        # Stats bar
        self._lbl_antibug_stats = tk.Label(
            ab_tab,
            text=(f"ðŸŽ¯ GiÃ¡m sÃ¡t: 0 ngÆ°á»i  â”‚  "
                  f"âš¡ Kicked: 0  â”‚  ðŸ”¨ Banned: 0"),
            bg="#0a0a12", fg="#ffcc00",
            font=("Segoe UI", 9, "bold")
        )
        self._lbl_antibug_stats.pack(anchor="w", padx=10, pady=(2, 0))

        # Quy táº¯c
        rule_f = tk.Frame(ab_tab, bg="#0d0d1a", pady=4)
        rule_f.pack(fill="x", padx=6, pady=(2, 2))
        tk.Label(rule_f,
                 text=(f"ðŸ“Œ  Quy táº¯c: > [ngÆ°á»¡ng] cÃ´ng trÃ¬nh/giÃ¢y â†’ Cáº¢NH BÃO + KICK  â”‚  "
                       f"Bá»‹ kick â‰¥ {ANTIBUG_MAX_KICKS} láº§n trong 5 phÃºt â†’ BAN VÄ¨NH VIá»„N"),
                 bg="#0d0d1a", fg="#555",
                 font=("Segoe UI", 8)).pack(side="left", padx=4)

        # â”€â”€ Unban / BanList panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        unban_f = tk.Frame(ab_tab, bg="#071a0f",
                           highlightthickness=1, highlightbackground="#1a4a2a")
        unban_f.pack(fill="x", padx=6, pady=(2, 3))

        tk.Label(unban_f, text="ðŸ”“ UNBAN:",
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
                messagebox.showwarning("Unban", "Chá»n ngÆ°á»i trong danh sÃ¡ch hoáº·c nháº­p SteamID trÆ°á»›c!")
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
        _unban_menu.add_command(label="ðŸ”“ Unban", command=_do_unban)
        _unban_menu.add_command(label="ðŸ”„ Táº£i láº¡i danh sÃ¡ch", command=_refresh_unban_list)
        _refresh_unban_list()

        tk.Button(unban_f, text="ðŸ”„",
                  bg="#0d2a1a", fg="#88ffcc",
                  relief="flat", padx=8,
                  command=_refresh_unban_list).pack(side="left", padx=(0, 6))

        tk.Button(unban_f, text="ðŸ”“ UNBAN",
                  bg="#0d3a1a", fg="#00ff88",
                  relief="flat", padx=14,
                  command=_do_unban).pack(side="left", padx=(0, 8))

        tk.Button(unban_f, text="ðŸ“‹ Xem banlist.txt",
                  bg="#0d0d2a", fg="#aaaaff",
                  relief="flat", padx=10,
                  command=lambda: (
                      os.startfile(ANTIBUG_BAN_FILE)
                      if os.path.isfile(ANTIBUG_BAN_FILE)
                      else messagebox.showinfo("ThÃ´ng bÃ¡o", "ChÆ°a cÃ³ file banlist.txt")
                  )).pack(side="left", padx=(0, 6))

        def _open_banlist_dir():
            subprocess.Popen(
                f'explorer /select,"{ANTIBUG_BAN_FILE}"'
                if os.path.isfile(ANTIBUG_BAN_FILE)
                else f'explorer "{os.path.dirname(ANTIBUG_BAN_FILE)}"'
            )
        tk.Button(unban_f, text="ðŸ“‚ ThÆ° má»¥c",
                  bg="#1a1a1a", fg="#888",
                  relief="flat", padx=10,
                  command=_open_banlist_dir).pack(side="left")

        tk.Label(unban_f,
                 text=(f"ðŸ”— Webhook: AntiBug  â”‚  "
                       f"ðŸ“ banlist.txt  â”‚  "
                       f"â± Kick window: 5 phÃºt"),
                 bg="#071a0f", fg="#2a5a3a",
                 font=("Segoe UI", 8)).pack(side="right", padx=10)

        # Log console
        self.antibug_console = scrolledtext.ScrolledText(
            ab_tab, bg="#05050f", fg="#aaaaff",
            font=("Consolas", 9), bd=0, insertbackground="#aaaaff"
        )
        self.antibug_console.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        # ChÃ¨n header
        self.antibug_console.insert(
            tk.END,
            f"{'â”€'*65}\n"
            f"  ðŸ¤– ANTIBUG MONITOR â€” MANAGER SERVERPAL\n"
            f"  âš’  Build/Dismantle spam : > [ngÆ°á»¡ng]/1s â†’ Cáº¢NH BÃO + KICK\n"
            f"  ðŸ”¬ Tech-Cheat           : má»Ÿ khÃ³a cÃ´ng nghá»‡ vÆ°á»£t cáº¥p â†’ BAN NGAY\n"
            f"  ðŸ”¬ Tech-Cheat           : má»Ÿ khÃ³a/xÃ¢y cÃ´ng nghá»‡ vÆ°á»£t cáº¥p â†’ BAN NGAY\n"
            f"  ðŸ“š Tech Database        : {len(TECH_LEVEL_DB)} cÃ´ng nghá»‡ "
            f"(paldeck.cc/technology)\n"
            f"{'â”€'*65}\n\n"
        )

        # â”€â”€ Tab 3: PALDEFENDER REST API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        api_tab = tk.Frame(nb, bg="#050a14")
        nb.add(api_tab, text="  ðŸŒ PD REST API  ")

        # â”€â”€ Status bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        st_bar = tk.Frame(api_tab, bg="#07101f", pady=6,
                          highlightthickness=1, highlightbackground="#1a3a5a")
        st_bar.pack(fill="x", padx=6, pady=(6, 2))

        tk.Label(st_bar, text="ðŸ“¡ PalDefender API:",
                 bg="#07101f", fg="#5588bb",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 6))

        self._lbl_pdapi_status = tk.Label(
            st_bar, text="â³ Äang kiá»ƒm tra...",
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

        tk.Button(st_bar, text="ðŸ”„ Ping",
                  bg="#0d2a44", fg="#55aaff", relief="flat", padx=10,
                  command=_ping_now).pack(side="left", padx=8)

        tk.Label(st_bar, text=f"Port {PALDEF_API_BASE.split(':')[-1]}",
                 bg="#07101f", fg="#334455",
                 font=("Consolas", 8)).pack(side="right", padx=10)

        # â”€â”€ Token management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tok_bar = tk.Frame(api_tab, bg="#07140f", pady=5,
                           highlightthickness=1, highlightbackground="#1a4a2a")
        tok_bar.pack(fill="x", padx=6, pady=(2, 2))

        tk.Label(tok_bar, text="ðŸ”‘ Token:",
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
            self._enqueue_console("ðŸ“‹ [PD-API] ÄÃ£ copy token vÃ o clipboard!")

        def _regen_token():
            if not messagebox.askyesno(
                "TÃ¡i táº¡o token",
                "XÃ³a token cÅ© vÃ  táº¡o token má»›i?\n"
                "âš ï¸ Cáº§n khá»Ÿi Ä‘á»™ng láº¡i PalDefender Ä‘á»ƒ token má»›i cÃ³ hiá»‡u lá»±c!"
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
                f"ðŸ”‘ [PD-API] Token má»›i Ä‘Ã£ táº¡o â€” "
                f"Khá»Ÿi Ä‘á»™ng láº¡i PalDefender Ä‘á»ƒ Ã¡p dá»¥ng!"
            )
            messagebox.showinfo(
                "Token má»›i",
                f"Token Ä‘Ã£ táº¡o:\n{self._pdapi_token}\n\n"
                f"File: {PALDEF_TOKEN_FILE}\n\n"
                f"âš ï¸ Restart PalDefender Ä‘á»ƒ token cÃ³ hiá»‡u lá»±c!"
            )

        tk.Button(tok_bar, text="ðŸ“‹ Copy",
                  bg="#0d2a1a", fg="#00cc66", relief="flat", padx=8,
                  command=_copy_token).pack(side="left", padx=2)
        tk.Button(tok_bar, text="ðŸ”„ Táº¡o má»›i",
                  bg="#1a1a0d", fg="#ffcc00", relief="flat", padx=8,
                  command=_regen_token).pack(side="left", padx=2)

        tk.Label(tok_bar,
                 text=f"ðŸ“ {PALDEF_TOKEN_FILE}",
                 bg="#07140f", fg="#224433",
                 font=("Consolas", 7)).pack(side="right", padx=10)

        # â”€â”€ Give Rewards Panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        give_f = tk.LabelFrame(
            api_tab, text="  ðŸŽ GIVE REWARDS (PD API â€” Atomic)  ",
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

        # Row 2: Items (JSON array hoáº·c "ItemID x Count" má»—i dÃ²ng)
        r2 = tk.Frame(give_f, bg="#050a14")
        r2.pack(fill="x", padx=6, pady=2)
        tk.Label(r2, text="Items:", bg="#050a14", fg="#aaa",
                 font=("Segoe UI", 9), width=10, anchor="e").pack(side="left")
        tk.Label(r2, text="ItemID  Count  (má»—i dÃ²ng 1 item, vÃ­ dá»¥: PalSphere 10)",
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

        # Log / result area + nÃºt GIVE
        give_btn_row = tk.Frame(give_f, bg="#050a14")
        give_btn_row.pack(fill="x", padx=6, pady=(2, 6))

        def _do_pdapi_give():
            sid = self._pdapi_give_sid.get().strip()
            if not sid:
                messagebox.showwarning("Give", "Nháº­p SteamID trÆ°á»›c!")
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
                messagebox.showwarning("Give", "ChÆ°a nháº­p item/pal/EXP nÃ o!")
                return

            def _do():
                ok, data = self._pdapi_give(sid, payload)
                if ok:
                    msg = f"âœ… [PD-API GIVE] {sid} â†’ {payload}  â†’  Errors=0"
                else:
                    errs = data.get("Error", data.get("error", data))
                    msg = f"âŒ [PD-API GIVE] {sid} â†’ Errors={data.get('Errors','?')}  {errs}"
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

        tk.Button(give_btn_row, text="ðŸŽ  GIVE (PD API)",
                  bg="#1a2a44", fg="#55aaff",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=18,
                  command=_do_pdapi_give).pack(side="left")
        tk.Button(give_btn_row, text="ðŸ—‘ XÃ³a log",
                  bg="#1a1a1a", fg="#666", relief="flat", padx=8,
                  command=lambda: self._pdapi_give_log.delete("1.0", tk.END)
                  ).pack(side="left", padx=6)
        tk.Label(give_btn_row,
                 text="Atomic: all-or-nothing  â”‚  KhÃ´ng cáº§n RCON",
                 bg="#050a14", fg="#223344",
                 font=("Segoe UI", 7)).pack(side="right", padx=6)

        self._pdapi_give_log = scrolledtext.ScrolledText(
            give_f, bg="#03060d", fg="#8899cc",
            font=("Consolas", 8), bd=0, insertbackground="#8899cc",
            height=4
        )
        self._pdapi_give_log.pack(fill="x", padx=6, pady=(0, 4))

        # â”€â”€ Guild Viewer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        guild_f = tk.LabelFrame(
            api_tab, text="  ðŸ° GUILD VIEWER  ",
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
        self._pdapi_guild_tree.heading("name",    text="TÃªn Guild")
        self._pdapi_guild_tree.heading("admin",   text="Admin UID")
        self._pdapi_guild_tree.heading("members", text="ThÃ nh viÃªn")
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
            guild_top, text="(chÆ°a táº£i)",
            bg="#050a14", fg="#555", font=("Segoe UI", 8)
        )
        self._lbl_guild_info.pack(side="left", padx=4)

        def _refresh_guilds():
            self._lbl_guild_info.config(text="â³ Äang táº£i...", fg="#888")
            def _do():
                result = self._pdapi_get_guilds()
                def _update():
                    for row in self._pdapi_guild_tree.get_children():
                        self._pdapi_guild_tree.delete(row)
                    if not result["ok"]:
                        err = result.get("error", result.get("code", "?"))
                        self._lbl_guild_info.config(
                            text=f"âŒ Lá»—i: {err}", fg="#ff4444")
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
                        text=f"âœ… {len(guilds)} guild", fg="#00ff88")
                self.root.after(0, _update)
            threading.Thread(target=_do, daemon=True).start()

        tk.Button(guild_top, text="ðŸ”„ Táº£i guilds",
                  bg="#1a1a00", fg="#ffaa00", relief="flat", padx=10,
                  command=_refresh_guilds).pack(side="left", padx=(0, 6))

        # Ping ngay khi má»Ÿ tab
        self.root.after(500, _ping_now)

        # Load lá»‹ch sá»­
        self.root.after(100, self._load_paldef_log_history)
        self.root.after(150, self._load_paldef_cheat_history)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  LIVE MAP â€” HELPERS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _coord_to_canvas(self, loc_x: float, loc_y: float,
                          canvas_w: int, canvas_h: int):
        """Chuyá»ƒn tá»a Ä‘á»™ game Palworld â†’ pixel trÃªn canvas."""
        map_x = (loc_y - 157664.55791065) / 462.962962963
        map_y = (loc_x + 123467.1611767)  / 462.962962963
        cx = (map_x + 1000) / 2000 * canvas_w
        cy = (1000 - map_y) / 2000 * canvas_h
        return cx, cy

    def _mapcoords_to_world(self, map_x: float, map_y: float) -> tuple:
        """Äáº£o phÃ©p biáº¿n Ä‘á»•i cá»§a _coord_to_canvas (map coords -> world loc_x/loc_y).
        Log PalDefender (PalBoxV2) Ä‘ang cho dáº¡ng 'at X Y Z' giá»‘ng map coords hiá»ƒn thá»‹.
        map_x tÆ°Æ¡ng á»©ng cÃ´ng thá»©c tá»« loc_y, map_y tÆ°Æ¡ng á»©ng tá»« loc_x.
        """
        loc_y = float(map_x) * 462.962962963 + 157664.55791065
        loc_x = float(map_y) * 462.962962963 - 123467.1611767
        return loc_x, loc_y

    def _render_discord_livemap_image(self, size: int = 1024) -> str:
        """Render áº£nh LiveMap cho Discord (PNG) vá»›i marker player/base hiá»‡n táº¡i."""
        if not _PIL_AVAILABLE or not os.path.isfile(MAP_JPG):
            return ""
        try:
            s = max(512, min(int(size or 1024), 2048))
            img = Image.open(MAP_JPG).convert("RGB").resize((s, s), Image.LANCZOS)
            draw = ImageDraw.Draw(img)

            # Váº½ base trÆ°á»›c (layer dÆ°á»›i)
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

            # Váº½ player (layer trÃªn)
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
        """Cáº­p nháº­t base marker theo log PalBoxV2:
        - build: set/update base cá»§a guild táº¡i tá»a Ä‘á»™ má»›i
        - dismantle: remove base cá»§a guild (náº¿u gáº§n tá»a Ä‘á»™ Ä‘Ã³), hoáº·c clear náº¿u chá»‰ cÃ³ 1
        """
        try:
            # tra guild cá»§a ngÆ°á»i chÆ¡i báº±ng báº£ng gpm hiá»‡n táº¡i
            gpm = self._map_guild_player_map or {}
            gname = gpm.get(str(steamid).lower()) or gpm.get(str(steamid).lower().lstrip("steam_")) or ""
            if not gname:
                # fallback theo tÃªn (náº¿u gpm cÃ³ name:)
                key = f"name:{str(player_name).lower().strip()}"
                gname = gpm.get(key, "")
            if not gname:
                return

            # world coords Ä‘á»ƒ váº½ lÃªn canvas
            loc_x, loc_y = self._mapcoords_to_world(map_x, map_y)

            BLUE = "#00ddff"  # icon luÃ´n mÃ u xanh theo yÃªu cáº§u
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
                # dismantle: remove náº¿u base gáº§n tá»a Ä‘á»™ Ä‘Ã³
                cur = self._map_bases_by_guild.get(gname)
                if not cur:
                    return
                # so khoáº£ng cÃ¡ch theo map coords Ä‘á»ƒ dá»… so (dÃ¹ng world cÅ©ng ok)
                try:
                    cur_map_x = (cur["loc_y"] - 157664.55791065) / 462.962962963
                    cur_map_y = (cur["loc_x"] + 123467.1611767)  / 462.962962963
                    dist = ((cur_map_x - float(map_x))**2 + (cur_map_y - float(map_y))**2) ** 0.5
                except Exception:
                    dist = 0.0
                if dist <= 8.0:
                    self._map_bases_by_guild.pop(gname, None)

            # publish list bases cho renderer (Æ°u tiÃªn bases tá»« log)
            self._map_guild_bases = list(self._map_bases_by_guild.values()) or self._map_guild_bases

            # cáº­p nháº­t UI
            try:
                self.root.after(0, lambda: (self._redraw_livemap_canvas(),
                                            self._update_map_player_tree()))
            except Exception:
                pass
        except Exception:
            pass

    def _start_map_node_server(self):
        """Legacy no-op: Live map Ä‘Ã£ cháº¡y embedded, khÃ´ng cáº§n Node.js."""
        self._enqueue_console("â„¹ï¸ Live Map Ä‘Ã£ tÃ­ch há»£p trong app, khÃ´ng cáº§n khá»Ÿi Ä‘á»™ng Node.js.")
        self._update_map_node_status_label()

    def _stop_map_node_server(self):
        """Legacy no-op: giá»¯ Ä‘á»ƒ tÆ°Æ¡ng thÃ­ch UI cÅ©."""
        self._enqueue_console("â„¹ï¸ Live Map embedded khÃ´ng cÃ³ tiáº¿n trÃ¬nh Node Ä‘á»ƒ dá»«ng.")
        self._update_map_node_status_label()

    def _update_map_node_status_label(self):
        """Cáº­p nháº­t label tráº¡ng thÃ¡i map mode (embedded)."""
        if not hasattr(self, "_lbl_map_node_status"):
            return
        try:
            if not self._lbl_map_node_status.winfo_exists():
                return
            self._lbl_map_node_status.config(
                text="ðŸŸ¢ Live Map: EMBEDDED MODE (khÃ´ng cáº§n Node.js)", fg="#00ffcc")
        except Exception:
            pass

    def _api_conn_parts(self) -> tuple:
        """Tráº£ vá» (host, port, password) tá»« API_URL vÃ  AUTH hiá»‡n táº¡i."""
        parsed = urlparse(API_URL)
        host   = parsed.hostname or "127.0.0.1"
        port   = parsed.port or 8212
        passwd = AUTH.password or ""
        return host, port, passwd

    def _open_web_map(self):
        """Má»Ÿ thÆ° má»¥c chá»©a áº£nh map Ä‘á»ƒ tiá»‡n update map.jpg."""
        try:
            os.makedirs(MAP_ASSETS_DIR, exist_ok=True)
            if os.path.isfile(MAP_JPG):
                os.startfile(MAP_JPG)
            else:
                os.startfile(MAP_ASSETS_DIR)
        except Exception as e:
            self._enqueue_console(f"âŒ KhÃ´ng má»Ÿ Ä‘Æ°á»£c thÆ° má»¥c map assets: {e}")

    def _load_map_image(self, w: int, h: int):
        """Táº£i vÃ  scale map.jpg â†’ PhotoImage (Pillow). Tráº£ None náº¿u lá»—i."""
        if not _PIL_AVAILABLE or not os.path.isfile(MAP_JPG):
            return None
        try:
            img   = Image.open(MAP_JPG).convert("RGB")
            img   = img.resize((w, h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            return photo
        except Exception:
            return None

    # MÃ u sáº¯c chuáº©n cho 10 guild Ä‘áº§u (xoay vÃ²ng)
    _GUILD_COLORS = [
        "#00ddff", "#ffcc00", "#ff6600", "#ff44aa",
        "#88ff44", "#cc88ff", "#ff8844", "#44ffcc",
        "#ff4444", "#44aaff",
    ]

    @staticmethod
    def _norm_uid(uid: str) -> str:
        """Chuáº©n hÃ³a UUID/SteamID: lowercase, bá» dáº¥u gáº¡ch, bá» prefix steam_."""
        if not uid:
            return ""
        s = str(uid).lower().strip()
        s_nodash = s.replace("-", "")
        return s_nodash  # primary canonical form

    def _lookup_guild(self, player: dict, gpm: dict) -> str:
        """Tra cá»©u tÃªn guild cá»§a má»™t player tá»« báº£ng gpm.
        Thá»­ táº¥t cáº£ biáº¿n thá»ƒ UUID vÃ  fallback theo tÃªn nhÃ¢n váº­t."""
        if not gpm:
            return ""
        pid  = str(player.get("playerId",  "")).lower().strip()
        uid  = str(player.get("userId",    "")).lower().strip()
        name = str(player.get("name",      "")).lower().strip()

        candidates = set()
        for raw in (pid, uid):
            if raw:
                candidates.add(raw)
                candidates.add(raw.replace("-", ""))          # bá» dash UUID
                no_prefix = raw.lstrip("steam_")
                candidates.add(no_prefix)
                candidates.add(no_prefix.replace("-", ""))

        for c in candidates:
            if c and c in gpm:
                return gpm[c]

        # Fallback: khá»›p theo tÃªn nhÃ¢n váº­t
        if name:
            key = f"name:{name}"
            if key in gpm:
                return gpm[key]
        return ""

    def _build_guild_maps(self, guilds: dict) -> tuple:
        """XÃ¢y dá»±ng:
          - gpm: {normalized_uid â†’ guild_name}  (dÃ¹ng cho player matching)
          - gname_map: {gid â†’ guild_name}
          - guild_color_map: {guild_name â†’ color}
        Sau Ä‘Ã³ fetch chi tiáº¿t tá»«ng guild (song song) Ä‘á»ƒ láº¥y base data.
        Tráº£ vá» (gpm, bases, guild_color_map).
        """
        gpm: dict  = {}
        bases: list = []
        gname_map:  dict = {}
        gcolor_map: dict = {}

        # BÆ°á»›c 1: XÃ¢y gpm tá»« members trong batch response
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
                        # ThÃªm CharacterName Ä‘á»ƒ fallback match by name
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
                        # Táº¥t cáº£ biáº¿n thá»ƒ cÃ³ thá»ƒ gáº·p
                        variants = {
                            s,                                # nguyÃªn gá»‘c
                            s.replace("-", ""),               # bá» dash (UUID)
                            s.lstrip("steam_"),               # bá» prefix
                            s.lstrip("steam_").replace("-",""),
                            "steam_" + s.lstrip("steam_"),    # thÃªm prefix
                        }
                        for v in variants:
                            if v:
                                gpm[v] = gname

            # BÆ°á»›c 1b: Thá»­ parse base tá»« batch response (phÃ²ng trÆ°á»ng há»£p cÃ³ sáºµn)
            batch_bases = self._parse_guild_bases({gid: gdata}, gi, gname, gcol)
            bases.extend(batch_bases)

        # BÆ°á»›c 2: Fetch chi tiáº¿t tá»«ng guild song song Ä‘á»ƒ láº¥y base data
        detail_bases: list = []

        def _fetch_one(args):
            gi2, gid2, gname2, gcol2 = args
            try:
                r = self._pdapi_get_guild(gid2)
                if r["ok"]:
                    detail = r["data"]
                    # CÅ©ng bá»• sung members tá»« detail (cÃ³ thá»ƒ chi tiáº¿t hÆ¡n)
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
                    # Parse bases tá»« detail
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

        # Æ¯u tiÃªn dÃ¹ng bases tá»« detail (cÃ³ thá»ƒ trÃ¹ng vá»›i batch â€” dedupe báº±ng base_id)
        if detail_bases:
            seen = {b["base_id"] for b in bases}
            for b in detail_bases:
                if b["base_id"] not in seen:
                    bases.append(b)
                    seen.add(b["base_id"])
            # Náº¿u detail cÃ³ bases, replace toÃ n bá»™
            if detail_bases:
                bases = detail_bases  # detail luÃ´n Ä‘áº§y Ä‘á»§ hÆ¡n

        return gpm, bases, gcolor_map

    def _parse_guild_bases(self, guilds: dict,
                           gi_offset: int = 0,
                           gname_override: str = "",
                           gcol_override: str = "") -> list:
        """PhÃ¢n tÃ­ch dá»¯ liá»‡u guild tá»« PD API â†’ danh sÃ¡ch base cÃ³ tá»a Ä‘á»™.
        Tráº£ vá» list: [{guild_name, guild_id, base_id, loc_x, loc_y, color}]
        Há»— trá»£ nhiá»u cÃ¡ch Ä‘áº·t tÃªn field cá»§a PalDefender."""
        bases = []
        for gi, (gid, gdata) in enumerate(guilds.items()):
            gname = (gname_override
                     or gdata.get("Name")
                     or gdata.get("GuildName")
                     or gdata.get("name")
                     or gid)
            gcol  = gcol_override or self._GUILD_COLORS[(gi + gi_offset) % len(self._GUILD_COLORS)]

            def _as_base_list(val):
                """Chuáº©n hÃ³a cáº¥u trÃºc base list tá»« PD API:
                - Náº¿u val lÃ  list â†’ tráº£ vá»
                - Náº¿u val lÃ  dict â†’ thá»­ láº¥y list tá»« cÃ¡c key phá»• biáº¿n
                - KhÃ¡c â†’ []
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
                    # Náº¿u dict cÃ³ Ä‘Ãºng 1 value lÃ  list
                    try:
                        only_lists = [v for v in val.values() if isinstance(v, list)]
                        if len(only_lists) == 1:
                            return only_lists[0]
                    except Exception:
                        pass
                return []

            # PalDefender API cÃ³ thá»ƒ dÃ¹ng nhiá»u key khÃ¡c nhau cho danh sÃ¡ch base
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
                # Thá»­ scan toÃ n bá»™ key trong guild detail Ä‘á»ƒ tÃ¬m list cÃ³ váº» lÃ  base
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

                # Tá»a Ä‘á»™ â€” thá»­ táº¥t cáº£ cÃ¡c kiá»ƒu field name thÆ°á»ng gáº·p
                loc = None

                # Kiá»ƒu 0 (PD API cá»§a báº¡n): map_pos {x,y,z} lÃ  "map coords"
                # â†’ convert sang world loc_x/loc_y theo cÃ´ng thá»©c Ä‘áº£o _coord_to_canvas
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

                # Kiá»ƒu 1: BaseCampPoint: {X, Y, Z}
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
                    # UE cÃ³ thá»ƒ dÃ¹ng Z lÃ  trá»¥c ngang cÃ²n Y lÃ  Ä‘á»™ cao (hoáº·c ngÆ°á»£c láº¡i)
                    if bx is not None and by is None:
                        by = (bpt.get("Z") or bpt.get("z")
                              or bpt.get("loc_z") or bpt.get("location_z"))
                    if bx is None and by is not None:
                        bx = (bpt.get("X") or bpt.get("x"))  # giá»¯ nguyÃªn fallback
                    if loc is None and bx is not None and by is not None:
                        loc = (float(bx), float(by))

                # Kiá»ƒu 2: loc_x / loc_y flat trong base dict
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
        """Má»Ÿ cá»­a sá»• debug hiá»ƒn thá»‹ raw JSON tá»« PD API guild endpoints."""
        win = tk.Toplevel(self.root)
        win.title("ðŸ”¬ Debug Guild API Data")
        win.geometry("900x600")
        win.configure(bg="#050505")

        top_f = tk.Frame(win, bg="#0a0a0a")
        top_f.pack(fill="x", padx=8, pady=6)
        tk.Label(top_f, text="ðŸ”¬  Raw Guild API Data  (PalDefender)",
                 bg="#0a0a0a", fg="#cc88ff", font=("Segoe UI", 11, "bold")
                 ).pack(side="left")
        tk.Button(top_f, text="âœ– ÄÃ³ng", bg="#2a0000", fg="#ff7777",
                  relief="flat", command=win.destroy).pack(side="right")
        tk.Button(top_f, text="ðŸ”„ Fetch láº¡i", bg="#0a1a2a", fg="#00ddff",
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
            t.insert(tk.END, "â³ Äang fetch /guilds...\n")
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
                    out.append(f"â†’ {len(guilds)} guild(s) returned")
                    out.append(json.dumps(guilds, indent=2, ensure_ascii=False))

                    # 2. Hiá»‡n táº¡i players tá»« REST API
                    out.append("\n" + "=" * 60)
                    out.append("Current players (_map_players_data):")
                    out.append("=" * 60)
                    for p in self._map_players_data:
                        out.append(f"  name={p.get('name')}  "
                                   f"playerId={p.get('playerId')}  "
                                   f"userId={p.get('userId')}")

                    # 3. Hiá»‡n táº¡i gpm
                    out.append("\n" + "=" * 60)
                    out.append(f"Current gpm ({len(self._map_guild_player_map)} entries):")
                    out.append("=" * 60)
                    for k, v in list(self._map_guild_player_map.items())[:80]:
                        out.append(f"  {k!r:50s} â†’ {v}")

                    # 4. Detail cho guild Ä‘áº§u tiÃªn
                    if guilds:
                        first_gid = next(iter(guilds))
                        out.append("\n" + "=" * 60)
                        out.append(f"GET /v1/pdapi/guild/{first_gid}  (first guild detail)")
                        out.append("=" * 60)
                        rd = self._pdapi_get_guild(first_gid)
                        if rd["ok"]:
                            detail = rd["data"]
                            # Highlight keys liÃªn quan base/camp Ä‘á»ƒ dá»… map field
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
                            out.append(f"âŒ {rd}")
                else:
                    out.append(f"âŒ {r}")

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
        """Gá»i thá»§ cÃ´ng: fetch guild data ngay láº­p tá»©c (background thread)."""
        if hasattr(self, "_lbl_guild_live_status"):
            try:
                self._lbl_guild_live_status.config(
                    text="â³ Äang táº£i guild + base...", fg="#888")
            except Exception:
                pass
        def _do():
            try:
                result = self._pdapi_get_guilds()
                if result["ok"]:
                    guilds = result["data"]
                    self._map_guilds_data = guilds
                    # DÃ¹ng _build_guild_maps: UUID normalized + fetch base tá»« detail endpoint
                    gpm, bases, _ = self._build_guild_maps(guilds)
                    self._map_guild_player_map = gpm
                    # Náº¿u cÃ³ base tá»« log PalBoxV2 thÃ¬ Æ°u tiÃªn hiá»ƒn thá»‹ base theo log
                    log_bases = list(getattr(self, "_map_bases_by_guild", {}).values())
                    self._map_guild_bases = log_bases if log_bases else bases
                    ng = len(guilds)
                    nb = len(self._map_guild_bases)
                    nm = len(gpm)
                    def _ok(n=ng, b=nb, m=nm):
                        try:
                            if hasattr(self, "_lbl_guild_live_status"):
                                self._lbl_guild_live_status.config(
                                    text=f"âœ… {n} guild  â”‚  {b} base  â”‚  {m} uid", fg="#00ff88")
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
                                    text=f"âŒ {err}", fg="#ff4444")
                        except Exception:
                            pass
                    self.root.after(0, _fail)
            except Exception as e:
                def _exc(err=str(e)):
                    try:
                        if hasattr(self, "_lbl_guild_live_status"):
                            self._lbl_guild_live_status.config(
                                text=f"âŒ {err}", fg="#ff4444")
                    except Exception:
                        pass
                self.root.after(0, _exc)
        threading.Thread(target=_do, daemon=True).start()

    def _map_canvas_click(self, event):
        """Xá»­ lÃ½ click trÃªn canvas LiveMap â€” hiá»ƒn thá»‹ popup thÃ´ng tin base / guild."""
        try:
            c  = self.map_canvas
            w  = c.winfo_width()  or 600
            h  = c.winfo_height() or 600
            mx, my = event.x, event.y
            HIT_BASE  = 24   # px hit-test radius cho base icon
            HIT_GUILD = 22   # px hit-test radius cho guild centroid

            # â”€â”€ Æ¯u tiÃªn 1: base icon â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

            # â”€â”€ Æ¯u tiÃªn 2: guild centroid marker â”€â”€â”€â”€â”€
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
        """Popup chi tiáº¿t khi click vÃ o base icon trÃªn báº£n Ä‘á»“."""
        base, bcx, bcy = hit_base
        gname  = base.get("guild_name", "?")
        blevel = base.get("level", 1)
        barea  = base.get("area",  0)
        bid    = base.get("base_id", "?")
        bcol   = base.get("color", "#00ddff")

        # Tá»a Ä‘á»™ map chuáº©n (X, Y hiá»ƒn thá»‹)
        try:
            map_x = (base["loc_y"] - 157664.55791065) / 462.962962963
            map_y = (base["loc_x"] + 123467.1611767)  / 462.962962963
        except Exception:
            map_x = map_y = 0

        popup = tk.Toplevel(self.root)
        popup.title(f"ðŸ”· Base â€” {gname}")
        popup.geometry(f"+{rx + 12}+{ry - 10}")
        popup.configure(bg="#0a0a18")
        popup.resizable(False, False)
        popup.grab_set()

        # Header
        hdr = tk.Frame(popup, bg="#0d1430", pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"ðŸ”·  Base cá»§a Guild: {gname}",
                 bg="#0d1430", fg=bcol,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=12)
        tk.Button(hdr, text="âœ•", bg="#3a0a0a", fg="#ff4444",
                  relief="flat", font=("Segoe UI", 9, "bold"),
                  command=popup.destroy).pack(side="right", padx=8)

        # ThÃ´ng tin
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
        _lrow("Base ID:",     bid[:24] + "â€¦" if len(str(bid)) > 24 else bid, "#aaaaff")
        _lrow("Level:",       blevel, "#ffcc00")
        _lrow("Area:",        barea,  "#88ff88")
        _lrow("Tá»a Ä‘á»™ X:",   f"{map_x:.1f}", "#00ddff")
        _lrow("Tá»a Ä‘á»™ Y:",   f"{map_y:.1f}", "#00ddff")

        # Äáº¿m sá»‘ thÃ nh viÃªn Ä‘ang online cá»§a guild nÃ y
        gpm     = self._map_guild_player_map
        players = self._map_players_data
        online_members = []
        for p in players:
            pg = self._lookup_guild(p, gpm)
            if pg == gname:
                online_members.append(p)

        tk.Frame(popup, bg="#222", height=1).pack(fill="x", padx=10, pady=4)
        tk.Label(popup,
                 text=f"ðŸ‘¥ {len(online_members)} thÃ nh viÃªn Ä‘ang online:",
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
                         text=f"  â–¸ {pm.get('name','?')}  Lv{pm.get('level','?')}{pos_txt}",
                         bg="#0d0d18", fg="#e0e0e0",
                         font=("Segoe UI", 8)).pack(anchor="w")
        else:
            tk.Label(popup, text="  (KhÃ´ng cÃ³ thÃ nh viÃªn nÃ o online)",
                     bg="#0a0a18", fg="#555",
                     font=("Segoe UI", 8)).pack(anchor="w", padx=14, pady=(0, 6))

        # Táº¥t cáº£ bases cá»§a cÃ¹ng guild
        same_guild_bases = [b for b in self._map_guild_bases
                            if b.get("guild_name") == gname]
        if len(same_guild_bases) > 1:
            tk.Frame(popup, bg="#222", height=1).pack(fill="x", padx=10, pady=2)
            tk.Label(popup,
                     text=f"ðŸ”· {len(same_guild_bases)} base cá»§a guild nÃ y:",
                     bg="#0a0a18", fg=bcol,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14)
            for ob in same_guild_bases:
                try:
                    omx = (ob["loc_y"] - 157664.55791065) / 462.962962963
                    omy = (ob["loc_x"] + 123467.1611767)  / 462.962962963
                    is_this = "â—€" if ob["base_id"] == bid else "  "
                    tk.Label(popup,
                             text=f"  {is_this} Base Lv{ob.get('level',1)}"
                                  f"  X:{omx:.0f} Y:{omy:.0f}",
                             bg="#0a0a18",
                             fg=bcol if ob["base_id"] == bid else "#888",
                             font=("Consolas", 8)).pack(anchor="w", padx=14)
                except Exception:
                    pass

        tk.Label(popup,
                 text=f"ðŸ“ Raw: loc_x={base['loc_x']:.0f}  loc_y={base['loc_y']:.0f}",
                 bg="#0a0a18", fg="#333",
                 font=("Consolas", 7)).pack(anchor="w", padx=14, pady=(4, 6))

        popup.after(30000, lambda: popup.destroy() if popup.winfo_exists() else None)

    def _guild_detail_popup(self, hit_guild, rx, ry):
        """Hiá»ƒn thá»‹ cá»­a sá»• popup thÃ´ng tin chi tiáº¿t cá»§a guild khi click."""
        gname, pos_list, cxg, cyg = hit_guild
        # Láº¥y chi tiáº¿t guild tá»« cache
        guilds = self._map_guilds_data
        gdata  = {}
        for gid, gd in guilds.items():
            n = gd.get("Name", gd.get("GuildName", gid))
            if n == gname:
                gdata  = gd
                break

        popup = tk.Toplevel(self.root)
        popup.title(f"ðŸ° Guild: {gname}")
        popup.geometry(f"+{rx + 12}+{ry - 10}")
        popup.configure(bg="#0a0a1a")
        popup.resizable(False, False)
        popup.grab_set()

        # Header
        hdr = tk.Frame(popup, bg="#0d1a2e", pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"ðŸ°  {gname}",
                 bg="#0d1a2e", fg="#ffcc00",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=12)
        tk.Button(hdr, text="âœ•", bg="#3a0a0a", fg="#ff4444",
                  relief="flat", font=("Segoe UI", 9, "bold"),
                  command=popup.destroy).pack(side="right", padx=8)

        # ThÃ´ng tin guild
        info_f = tk.Frame(popup, bg="#0a0a1a", padx=14, pady=6)
        info_f.pack(fill="x")

        admin = gdata.get("AdminPlayerUid", gdata.get("AdminUid", "â€”"))
        total_members = gdata.get("Members", [])
        total_count   = len(total_members) if isinstance(total_members, list) else "?"

        def _lrow(label, val, fg="#e0e0e0"):
            row = tk.Frame(info_f, bg="#0a0a1a")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, bg="#0a0a1a", fg="#888",
                     font=("Segoe UI", 9), width=18, anchor="w").pack(side="left")
            tk.Label(row, text=str(val), bg="#0a0a1a", fg=fg,
                     font=("Segoe UI", 9, "bold")).pack(side="left")

        _lrow("Tá»•ng thÃ nh viÃªn:", total_count, "#00ffcc")
        _lrow("Online hiá»‡n táº¡i:", len(pos_list), "#00ff88")
        _lrow("Admin UID:", admin[:32] + "â€¦" if len(str(admin)) > 32 else admin, "#aaaaff")

        # Separator
        tk.Frame(popup, bg="#222", height=1).pack(fill="x", padx=10, pady=4)

        # Danh sÃ¡ch thÃ nh viÃªn online
        tk.Label(popup, text="ðŸ‘¥ ThÃ nh viÃªn Ä‘ang online:",
                 bg="#0a0a1a", fg="#00ffcc",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(2, 0))

        mem_f = tk.Frame(popup, bg="#0d0d14", padx=6, pady=4)
        mem_f.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        mem_cols = ("TÃªn", "Lv", "X", "Y")
        mem_tree = ttk.Treeview(mem_f, columns=mem_cols,
                                show="headings", height=min(len(pos_list) + 1, 12))
        mem_cw = {"TÃªn": 120, "Lv": 40, "X": 60, "Y": 60}
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
                                        "â€”", "â€”"))

        # Tá»a Ä‘á»™ tÃ¢m guild trÃªn báº£n Ä‘á»“
        cxg_map = (cxg / (self.map_canvas.winfo_width() or 600)) * 2000 - 1000
        cyg_map = 1000 - (cyg / (self.map_canvas.winfo_height() or 600)) * 2000
        tk.Label(popup,
                 text=f"ðŸ“ Trung tÃ¢m guild: Xâ‰ˆ{cxg_map:.0f}  Yâ‰ˆ{cyg_map:.0f}",
                 bg="#0a0a1a", fg="#666",
                 font=("Consolas", 8)).pack(anchor="w", padx=14, pady=(0, 6))

        # Auto-close sau 30s náº¿u khÃ´ng tÆ°Æ¡ng tÃ¡c
        popup.after(30000, lambda: popup.destroy() if popup.winfo_exists() else None)

    def _init_map_canvas_image(self):
        """Gá»i sau khi canvas Ä‘Æ°á»£c render: load áº£nh báº£n Ä‘á»“ theo kÃ­ch thÆ°á»›c thá»±c."""
        if not hasattr(self, "map_canvas") or not self.map_canvas.winfo_exists():
            return
        self.map_canvas.update_idletasks()
        w = self.map_canvas.winfo_width()
        h = self.map_canvas.winfo_height()
        if w > 10 and h > 10:
            self._map_canvas_photo = self._load_map_image(w, h)
        self._redraw_livemap_canvas()

    def _redraw_livemap_canvas(self):
        """Váº½ láº¡i toÃ n bá»™ canvas báº£n Ä‘á»“ vá»›i vá»‹ trÃ­ ngÆ°á»i chÆ¡i hiá»‡n táº¡i."""
        if not hasattr(self, "map_canvas") or not self.map_canvas.winfo_exists():
            return
        try:
            c = self.map_canvas
            w = c.winfo_width()  or 600
            h = c.winfo_height() or 600
            c.delete("all")

            # â”€â”€ Ná»n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if self._map_canvas_photo:
                c.create_image(0, 0, image=self._map_canvas_photo, anchor="nw")
            else:
                # Fallback: lÆ°á»›i tá»‘i
                c.create_rectangle(0, 0, w, h, fill="#071407", outline="")
                step_x, step_y = w // 10, h // 10
                for i in range(0, w + 1, step_x):
                    c.create_line(i, 0, i, h, fill="#112211", width=1)
                for j in range(0, h + 1, step_y):
                    c.create_line(0, j, w, j, fill="#112211", width=1)
                # Trá»¥c tÃ¢m
                c.create_line(w // 2, 0, w // 2, h, fill="#1e3e1e", width=2)
                c.create_line(0, h // 2, w, h // 2, fill="#1e3e1e", width=2)
                c.create_text(w // 2 + 6, h // 2 - 12, text="(0, 0)",
                              fill="#2a6a2a", font=("Consolas", 8))
                # Ghi chÃº thiáº¿u PIL
                if not _PIL_AVAILABLE:
                    c.create_text(w // 2, 18, anchor="n",
                                  text="âš ï¸ CÃ i Pillow Ä‘á»ƒ hiá»‡n báº£n Ä‘á»“:  pip install Pillow",
                                  fill="#ff9900", font=("Segoe UI", 10, "bold"))
                elif not os.path.isfile(MAP_JPG):
                    c.create_text(w // 2, 18, anchor="n",
                                  text=f"âš ï¸ KhÃ´ng tÃ¬m tháº¥y map.jpg táº¡i: {MAP_JPG}",
                                  fill="#ff9900", font=("Segoe UI", 9))

            # â”€â”€ Guild Base Layer (váº½ trÆ°á»›c â€” náº±m dÆ°á»›i player) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if self._map_show_bases.get():
                for base in self._map_guild_bases:
                    try:
                        bx = base["loc_x"]
                        by = base["loc_y"]
                        # Icon base luÃ´n mÃ u xanh theo yÃªu cáº§u (khÃ´ng theo mÃ u guild)
                        bcol  = "#00ddff"
                        bname = base.get("guild_name", "?")
                        bcx, bcy = self._coord_to_canvas(bx, by, w, h)
                        if not (-30 <= bcx <= w + 30 and -30 <= bcy <= h + 30):
                            continue
                        RS = 16   # outer diamond half-size
                        RI = 11   # inner diamond half-size
                        # VÃ²ng glow ngoÃ i
                        c.create_polygon(
                            bcx,      bcy - RS - 4,
                            bcx + RS + 4, bcy,
                            bcx,      bcy + RS + 4,
                            bcx - RS - 4, bcy,
                            fill="", outline=bcol, width=2,
                            tags=("base_glow", f"base:{bname}")
                        )
                        # Outer diamond ná»n tá»‘i
                        c.create_polygon(
                            bcx,      bcy - RS,
                            bcx + RS, bcy,
                            bcx,      bcy + RS,
                            bcx - RS, bcy,
                            fill="#0a1a2a", outline=bcol, width=2,
                            tags=("base_outer", f"base:{bname}")
                        )
                        # Inner diamond mÃ u sÃ¡ng
                        c.create_polygon(
                            bcx,      bcy - RI,
                            bcx + RI, bcy,
                            bcx,      bcy + RI,
                            bcx - RI, bcy,
                            fill=bcol, outline="#ffffff", width=1,
                            tags=("base_inner", f"base:{bname}")
                        )
                        # Castle emoji á»Ÿ giá»¯a
                        c.create_text(bcx, bcy,
                                      text="ðŸ°",
                                      font=("Segoe UI", 9),
                                      tags=("base_icon", f"base:{bname}"))
                        # Label: chá»‰ tÃªn guild
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

            # â”€â”€ NgÆ°á»i chÆ¡i â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
                    # Bá» nhá»¯ng vá»‹ trÃ­ náº±m ngoÃ i canvas
                    if not (-20 <= cx <= w + 20 and -20 <= cy <= h + 20):
                        continue
                    color  = DOT_COLORS[i % len(DOT_COLORS)]
                    name   = p.get("name",  "?")
                    level  = p.get("level", "?")
                    r = 8
                    # VÃ²ng hÃ o quang
                    c.create_oval(cx - r - 3, cy - r - 3,
                                  cx + r + 3, cy + r + 3,
                                  fill="", outline=color, width=2)
                    # Cháº¥m chÃ­nh
                    c.create_oval(cx - r, cy - r, cx + r, cy + r,
                                  fill=color, outline="#ffffff", width=1)
                    # Label tÃªn
                    c.create_text(cx + 1, cy - r - 15,
                                  text=f"Lv{level}  {name}",
                                  fill="white",
                                  font=("Segoe UI", 9, "bold"))
                    # Tá»a Ä‘á»™ nhá»
                    mx = (float(ly) - 157664.55791065) / 462.962962963
                    my = (float(lx) + 123467.1611767)  / 462.962962963
                    c.create_text(cx, cy + r + 13,
                                  text=f"({mx:.0f}, {my:.0f})",
                                  fill="#bbbbbb", font=("Consolas", 7))
                    visible += 1
                except Exception:
                    pass

            # â”€â”€ Guild Live Layer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if self._map_show_guilds.get():
                # NhÃ³m vá»‹ trÃ­ canvas cá»§a ngÆ°á»i chÆ¡i theo guild
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
                        # TÃ¬m guild qua playerId / userId (chuáº©n hÃ³a UUID)
                        gname = self._lookup_guild(p, gpm)
                        if gname:
                            guild_positions.setdefault(gname, []).append(
                                (cx2, cy2, p.get("name", "?")))
                    except Exception:
                        pass

                # MÃ u sáº¯c cho tá»«ng guild (tuáº§n hoÃ n)
                GUILD_COLORS = [
                    "#ffcc00", "#ff6600", "#00ddff", "#ff44aa",
                    "#88ff44", "#cc88ff", "#ff8844", "#44ffcc",
                    "#ff4444", "#44aaff",
                ]
                for gi, (gname, pos_list) in enumerate(guild_positions.items()):
                    gcol = GUILD_COLORS[gi % len(GUILD_COLORS)]
                    if len(pos_list) >= 2:
                        # Váº½ Ä‘Æ°á»ng ná»‘i cÃ¡c thÃ nh viÃªn
                        for k in range(len(pos_list) - 1):
                            x1, y1, _ = pos_list[k]
                            x2, y2, _ = pos_list[k + 1]
                            c.create_line(x1, y1, x2, y2,
                                          fill=gcol, width=2,
                                          dash=(6, 4))
                    # TÃ­nh centroid
                    cxg = sum(pp[0] for pp in pos_list) / len(pos_list)
                    cyg = sum(pp[1] for pp in pos_list) / len(pos_list)
                    # Biá»ƒu tÆ°á»£ng guild (hÃ¬nh thoi nhá»)
                    rg = 7
                    c.create_polygon(
                        cxg, cyg - rg,
                        cxg + rg, cyg,
                        cxg, cyg + rg,
                        cxg - rg, cyg,
                        fill=gcol, outline="#ffffff", width=1,
                        tags=("guild_marker", f"guild:{gname}")
                    )
                    # TÃªn guild + sá»‘ thÃ nh viÃªn online
                    label_txt = f"ðŸ° {gname}  [{len(pos_list)}]"
                    # BÃ³ng Ä‘á»• chá»¯
                    c.create_text(cxg + 1, cyg - rg - 14,
                                  text=label_txt,
                                  fill="#000000",
                                  font=("Segoe UI", 9, "bold"))
                    c.create_text(cxg, cyg - rg - 15,
                                  text=label_txt,
                                  fill=gcol,
                                  font=("Segoe UI", 9, "bold"),
                                  tags=("guild_label", f"guild:{gname}"))

            # â”€â”€ HUD gÃ³c trÃªn trÃ¡i â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            c.create_rectangle(0, 0, 210, 56, fill="#000000", stipple="gray25",
                                outline="")
            # Sá»‘ ngÆ°á»i chÆ¡i
            c.create_text(8, 4, anchor="nw",
                          text=f"ðŸ‘¥ {visible}/{len(players)} ngÆ°á»i chÆ¡i Ä‘ang hiá»ƒn thá»‹",
                          fill="white", font=("Segoe UI", 8, "bold"))
            # Sá»‘ guild Ä‘ang online
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
                              text=f"ðŸ° {ng} guild online  /  {nt} tá»•ng",
                              fill="#ffcc00", font=("Segoe UI", 8))
                hud_y += 14
            if self._map_show_bases.get():
                nb = len(self._map_guild_bases)
                c.create_text(8, hud_y, anchor="nw",
                              text=f"ðŸ”· {nb} base trÃªn báº£n Ä‘á»“",
                              fill="#00ddff", font=("Segoe UI", 8))
        except Exception:
            pass

    def _update_map_player_tree(self):
        """Cáº­p nháº­t báº£ng danh sÃ¡ch ngÆ°á»i chÆ¡i bÃªn pháº£i LiveMap."""
        if not hasattr(self, "_map_player_tree") or \
           not self._map_player_tree.winfo_exists():
            return
        try:
            self._map_player_tree.delete(*self._map_player_tree.get_children())
            gpm = self._map_guild_player_map
            for p in self._map_players_data:
                lx = p.get("location_x")
                ly = p.get("location_y")
                # Tra cá»©u guild cá»§a player (chuáº©n hÃ³a UUID)
                guild = self._lookup_guild(p, gpm) or "â€”"
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
                                "â€”", "â€”")
                    )
        except Exception:
            pass

    def map_player_fetch_loop(self):
        """Background thread: fetch player positions má»—i 3 giÃ¢y cho LiveMap."""
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
        """Background thread: fetch guild data tá»« PD API má»—i 30 giÃ¢y cho LiveMap."""
        while True:
            try:
                result = self._pdapi_get_guilds()
                if result["ok"]:
                    guilds = result["data"]
                    self._map_guilds_data = guilds
                    # DÃ¹ng _build_guild_maps: UUID normalized + fetch base tá»« detail endpoint
                    gpm, bases, _ = self._build_guild_maps(guilds)
                    self._map_guild_player_map = gpm
                    # Náº¿u cÃ³ base tá»« log PalBoxV2 thÃ¬ Æ°u tiÃªn hiá»ƒn thá»‹ base theo log
                    log_bases = list(getattr(self, "_map_bases_by_guild", {}).values())
                    self._map_guild_bases = log_bases if log_bases else bases
                    ng = len(guilds)
                    nb = len(self._map_guild_bases)
                    nm = len(gpm)
                    def _ui_ok(n=ng, b=nb, m=nm):
                        try:
                            if hasattr(self, "_lbl_guild_live_status"):
                                self._lbl_guild_live_status.config(
                                    text=f"âœ… {n} guild  â”‚  {b} base  â”‚  {m} uid", fg="#00ff88")
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

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: LIVE MAP
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def draw_livemap(self):
        # TiÃªu Ä‘á»
        title_bar = tk.Frame(self.container, bg="#0a0a0a")
        title_bar.pack(fill="x", pady=(0, 4))
        tk.Label(title_bar, text="ðŸ—ºï¸  LIVE MAP â€” PALWORLD",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        pil_tag = "âœ… PIL" if _PIL_AVAILABLE else "âŒ PIL (pip install Pillow)"
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
            text="ðŸŸ¢ Live Map: EMBEDDED MODE (khÃ´ng cáº§n Node.js)",
            fg="#00ffcc",
            bg="#111", font=("Segoe UI", 9, "bold")
        )
        self._lbl_map_node_status.pack(side="left", padx=12)

        tk.Button(ctrl, text="ðŸ—‚ Má»Ÿ thÆ° má»¥c map assets",
                  bg="#1a2a3a", fg="#4499ff", relief="flat", padx=12,
                  command=self._open_web_map
                  ).pack(side="left", padx=8)

        # â”€â”€ Guild Live controls â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sep = tk.Frame(ctrl, bg="#333", width=1)
        sep.pack(side="left", fill="y", padx=6)

        tk.Checkbutton(
            ctrl, text="ðŸ° Hiá»‡n Guild",
            variable=self._map_show_guilds,
            bg="#111", fg="#ffcc00",
            selectcolor="#1a1a00",
            activebackground="#111", activeforeground="#ffcc00",
            font=("Segoe UI", 9, "bold"),
            command=self._redraw_livemap_canvas
        ).pack(side="left", padx=4)

        tk.Checkbutton(
            ctrl, text="ðŸ”· Hiá»‡n Base",
            variable=self._map_show_bases,
            bg="#111", fg="#00ddff",
            selectcolor="#001a1a",
            activebackground="#111", activeforeground="#00ddff",
            font=("Segoe UI", 9, "bold"),
            command=self._redraw_livemap_canvas
        ).pack(side="left", padx=4)

        tk.Button(
            ctrl, text="ðŸ”„ Refresh Guild",
            bg="#1a1a00", fg="#ffaa00", relief="flat", padx=10,
            command=self._guild_refresh_now
        ).pack(side="left", padx=4)

        tk.Button(
            ctrl, text="ðŸ”¬ Debug Guild",
            bg="#1a0a2a", fg="#cc88ff", relief="flat", padx=8,
            command=self._debug_guild_data
        ).pack(side="left", padx=2)

        # Label tráº¡ng thÃ¡i guild
        self._lbl_guild_live_status = tk.Label(
            ctrl, text="â³ ChÆ°a táº£i guild",
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

        # â”€â”€ Canvas (trÃ¡i) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        map_outer = tk.Frame(main_f, bg="#071407",
                             highlightthickness=1, highlightbackground="#1e3e1e")
        map_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.map_canvas = tk.Canvas(map_outer, bg="#071407",
                                    bd=0, highlightthickness=0,
                                    cursor="crosshair")
        self.map_canvas.pack(fill="both", expand=True)

        # Hiá»ƒn thá»‹ tá»a Ä‘á»™ khi hover
        self._lbl_map_cursor = tk.Label(
            map_outer, text="X: â€” , Y: â€”",
            bg="#0a1a0a", fg="#666", font=("Consolas", 8)
        )
        self._lbl_map_cursor.place(relx=1.0, rely=1.0, anchor="se")

        def _on_mouse_move(evt):
            try:
                w = self.map_canvas.winfo_width()
                h = self.map_canvas.winfo_height()
                # Canvas â†’ map coords (-1000..1000)
                mx = (evt.x / w) * 2000 - 1000
                my = 1000 - (evt.y / h) * 2000
                self._lbl_map_cursor.config(
                    text=f"X: {mx:.0f} , Y: {my:.0f}")
            except Exception:
                pass

        self.map_canvas.bind("<Motion>", _on_mouse_move)
        self.map_canvas.bind("<Button-1>", self._map_canvas_click)

        # â”€â”€ Player list (pháº£i) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        right_f = tk.Frame(main_f, bg="#0d0d0d",
                           highlightthickness=1, highlightbackground="#222")
        right_f.grid(row=0, column=1, sticky="nsew")

        tk.Label(right_f, text="ðŸ‘¥  ONLINE",
                 bg="#0d0d0d", fg="#00ffcc",
                 font=("Segoe UI", 10, "bold"), pady=6).pack()

        list_cols = ("TÃªn", "Lv", "Guild", "X", "Y")
        self._map_player_tree = ttk.Treeview(
            right_f, columns=list_cols, show="headings", height=28
        )
        col_w = {"TÃªn": 80, "Lv": 28, "Guild": 80, "X": 44, "Y": 44}
        for col in list_cols:
            self._map_player_tree.heading(col, text=col)
            self._map_player_tree.column(col, width=col_w[col], anchor="center")
        self._map_player_tree.pack(fill="both", expand=True, padx=2, pady=2)

        # Load áº£nh sau khi canvas Ä‘Æ°á»£c render (cáº§n kÃ­ch thÆ°á»›c thá»±c)
        self.root.after(250, self._init_map_canvas_image)
        # Váº½ ngay vá»›i dá»¯ liá»‡u cÃ³ sáºµn
        self.root.after(280, self._redraw_livemap_canvas)
        self.root.after(300, self._update_map_player_tree)
        # Fetch guild data ngay khi má»Ÿ tab (náº¿u chÆ°a cÃ³)
        if not self._map_guilds_data:
            self.root.after(400, self._guild_refresh_now)

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: RATES
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  SETTINGS HELPERS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _settings_parse_ini(self, filepath=None) -> dict:
        """Parse PalWorldSettings.ini â†’ dict keyâ†’raw_value (delegated to app_config)."""
        filepath = filepath or PAL_SETTINGS_INI
        return cfgmod.parse_palworld_settings_ini(filepath)

    def _settings_save_ini(self, updates: dict, filepath=None) -> bool:
        """Merge updates into PalWorldSettings.ini and write back."""
        filepath = filepath or PAL_SETTINGS_INI
        try:
            cfgmod.save_palworld_settings_ini(filepath, updates)
            return True
        except ValueError:
            messagebox.showerror("Lá»—i", "KhÃ´ng Ä‘á»c Ä‘Æ°á»£c PalWorldSettings.ini!")
            return False
        except Exception as e:
            messagebox.showerror("Lá»—i ghi INI", str(e))
            return False

    def _settings_manager_cfg_to_ini_updates(self, cfg: dict) -> dict:
        """Map manager_config -> PalWorldSettings OptionSettings."""
        return cfgmod.manager_cfg_to_ini_updates(cfg)

    def _settings_sync_manager_ini_to_game(self) -> bool:
        """Copy manager/PalWorldSettings.ini -> game PalWorldSettings.ini (theo SERVER_EXE hiá»‡n táº¡i)."""
        src = MANAGER_PAL_SETTINGS_INI
        dst = PAL_SETTINGS_INI
        try:
            backup = cfgmod.sync_manager_ini_to_game(src, dst)
            if backup:
                self._enqueue_console(f"ðŸ—‚ï¸ Backup game INI: {backup}")
            self._enqueue_console(f"âœ… Äá»“ng bá»™ INI: {src} -> {dst}")
            return True
        except FileNotFoundError:
            messagebox.showerror("Thiáº¿u file", f"KhÃ´ng tÃ¬m tháº¥y file nguá»“n:\n{src}")
            return False
        except Exception as e:
            messagebox.showerror("Lá»—i Ä‘á»“ng bá»™ INI", str(e))
            return False

    def _settings_make_scrollable(self, parent) -> tk.Frame:
        """Táº¡o canvas scrollable, tráº£ vá» inner Frame Ä‘á»ƒ Ä‘áº·t widgets."""
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
        """Táº¡o nhÃ³m cÃ³ tiÃªu Ä‘á», tráº£ vá» Frame bÃªn trong."""
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
        """Má»™t hÃ ng label + entry/combobox + note trong body."""
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
                    eye_btn.config(text="ðŸ™ˆ" if hidden else "ðŸ‘")
                    is_hidden.set(not hidden)
                eye_btn = tk.Button(parent, text="ðŸ‘",
                                    bg="#1a1a2a", fg="#aaa", relief="flat",
                                    padx=6, command=_toggle_pw)
                eye_btn.grid(row=row, column=2, sticky="w", padx=(6, 0))
        if note:
            tk.Label(parent, text=note,
                     bg="#111", fg="#555",
                     font=("Segoe UI", 8)).grid(row=row, column=3 if show else 2, sticky="w", padx=6)
        parent.grid_columnconfigure(1, weight=1)

    def _settings_load_manager_config(self) -> dict:
        """Äá»c manager_config.json náº¿u cÃ³."""
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
            messagebox.showerror("Lá»—i", str(e))
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

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: DISCORD CHAT BRIDGE
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def draw_discord(self):
        """Tab quáº£n lÃ½ Discord â†” ingame chat bridge."""
        # â”€â”€ TiÃªu Ä‘á» â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr = tk.Frame(self.container, bg="#0a0a0a")
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text="ðŸŸ£  DISCORD CHAT BRIDGE",
                 bg="#0a0a0a", fg="#7289da",
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        # â”€â”€ Status card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        card = tk.Frame(self.container, bg="#12102a", pady=14)
        card.pack(fill="x", padx=2, pady=(0, 8))

        # ÄÃ¨n tráº¡ng thÃ¡i
        self._discord_status_lbl = tk.Label(
            card, text="â— " + self._discord_bridge_status,
            bg="#12102a",
            fg="#00ff88" if self._discord_bridge_ok else "#ff5555",
            font=("Segoe UI", 12, "bold")
        )
        self._discord_status_lbl.pack(side="left", padx=16)

        # NÃºt kiá»ƒm tra thá»§ cÃ´ng
        tk.Button(card, text="ðŸ”„ Kiá»ƒm tra láº¡i",
                  bg="#2c2f6b", fg="white", relief="flat",
                  padx=12, pady=4,
                  font=("Segoe UI", 9),
                  command=self._discord_force_check
                  ).pack(side="right", padx=12)

        # â”€â”€ Thá»‘ng kÃª â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

        _stat(stats, "ðŸ“¨", "Discord â†’ Ingame", "_lbl_dc_in",  0)
        _stat(stats, "ðŸŽ®", "Ingame â†’ Discord", "_lbl_dc_out", 1)
        _stat(stats, "â±ï¸", "Láº§n check cuá»‘i",   "_lbl_dc_ts",  2)
        _stat(stats, "ðŸ”—", "Channel ID",        "_lbl_dc_ch",  3)

        self._lbl_dc_ch.configure(
            text=DISCORD_CHAT_CHANNEL_ID[:10] + "..." if len(DISCORD_CHAT_CHANNEL_ID) > 10
            else DISCORD_CHAT_CHANNEL_ID,
            fg="#7289da", font=("Consolas", 10))

        # Cáº­p nháº­t ngay cÃ¡c counter hiá»‡n táº¡i
        self._discord_refresh_stats()

        # â”€â”€ Cáº¥u hÃ¬nh nhanh â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        cfg_frame = tk.Frame(self.container, bg="#0a0a1a", pady=8)
        cfg_frame.pack(fill="x", padx=2, pady=(0, 8))
        tk.Label(cfg_frame, text="âš™ï¸  Cáº¥u hÃ¬nh nhanh",
                 bg="#0a0a1a", fg="#aaa",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=12)

        # Toggle bridge on/off
        self._discord_bridge_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(cfg_frame,
                       text="Báº­t Discord Bridge",
                       variable=self._discord_bridge_enabled,
                       bg="#0a0a1a", fg="#7289da",
                       selectcolor="#0a0a1a",
                       activebackground="#0a0a1a",
                       font=("Segoe UI", 9)
                       ).pack(side="left", padx=16)

        # Link má»i Bot 1 (Má»“m LÃ¨o)
        invite_url = (f"https://discord.com/oauth2/authorize"
                      f"?client_id=1483506499064954961&scope=bot&permissions=68608")
        def _copy_invite():
            self.root.clipboard_clear()
            self.root.clipboard_append(invite_url)
            self._enqueue_console("ðŸ“‹ ÄÃ£ copy link má»i bot Discord!")
        tk.Button(cfg_frame, text="ðŸ“‹ Copy Link Má»i Bot 1 (Má»“m LÃ¨o)",
                  bg="#5865f2", fg="white", relief="flat",
                  padx=10, pady=3,
                  font=("Segoe UI", 8),
                  command=_copy_invite).pack(side="right", padx=12)

        # â”€â”€ PhÃ¢n tÃ¡ch â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tk.Frame(self.container, bg="#1e1e3a", height=1).pack(fill="x", padx=2, pady=(0, 4))

        # â”€â”€ Log chat bridge (paned: Discord log + System log) â”€â”€â”€â”€â”€â”€
        paned = tk.PanedWindow(self.container, orient=tk.VERTICAL,
                               bg="#1e1e3a", sashwidth=5, handlesize=0)
        paned.pack(fill="both", expand=True, padx=2, pady=(0, 4))

        # Pane trÃªn: Discord chat log
        dc_frame = tk.Frame(paned, bg="#0a0a1a")
        paned.add(dc_frame, minsize=120)

        dc_hdr = tk.Frame(dc_frame, bg="#12102a", pady=4)
        dc_hdr.pack(fill="x")
        tk.Label(dc_hdr, text="ðŸŸ£  DISCORD CHAT LOG  (Discord â†” Ingame)",
                 bg="#12102a", fg="#7289da",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        tk.Button(dc_hdr, text="ðŸ—‘ XÃ³a",
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

        # Pane dÆ°á»›i: gá»­i tin tá»« Ä‘Ã¢y sang Discord
        send_frame = tk.Frame(paned, bg="#0a0a1a")
        paned.add(send_frame, minsize=70)

        tk.Label(send_frame, text="ðŸ“¤  Gá»­i thÃ´ng bÃ¡o lÃªn Discord",
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
        tk.Button(send_row, text="ðŸ“¤ Gá»­i Discord",
                  bg="#5865f2", fg="white", relief="flat",
                  padx=16, pady=4,
                  font=("Segoe UI", 9, "bold"),
                  command=self._discord_send_manual).pack(side="left")

        # â”€â”€ PhÃ¢n tÃ¡ch Bot 2 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        tk.Frame(self.container, bg="#1e1e3a", height=2).pack(fill="x", padx=2, pady=(8, 4))
        
        # â”€â”€ Discord Bot 2 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr2 = tk.Frame(self.container, bg="#0a0a0a")
        hdr2.pack(fill="x", pady=(8, 8))
        tk.Label(hdr2, text="ðŸ¤–  DISCORD BOT 2 (Commands & Features)",
                 bg="#0a0a0a", fg="#00ff88",
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        # Status card Bot 2
        card2 = tk.Frame(self.container, bg="#0a1a0a", pady=14)
        card2.pack(fill="x", padx=2, pady=(0, 8))

        self._discord_bot2_status_lbl = tk.Label(
            card2, text="â— " + self._discord_bot2_status,
            bg="#0a1a0a",
            fg="#00ff88" if self._discord_bot2_ok else "#ff5555",
            font=("Segoe UI", 12, "bold")
        )
        self._discord_bot2_status_lbl.pack(side="left", padx=16)

        # ThÃ´ng tin Bot 2
        info_frame = tk.Frame(card2, bg="#0a1a0a")
        info_frame.pack(side="left", padx=20)
        tk.Label(info_frame, text="ðŸ“‹ Commands: !ranking, !stats, !search, !online, !server, !help",
                 bg="#0a1a0a", fg="#888",
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(info_frame, text="âš¡ Slash Commands: /ranking, /stats, /server (hiá»‡n Ä‘áº¡i hÆ¡n)",
                 bg="#0a1a0a", fg="#888",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))
        tk.Label(info_frame, text=f"ðŸ”— Channel: {DISCORD_BOT2_CHANNEL_ID[:20] + '...' if DISCORD_BOT2_CHANNEL_ID and len(DISCORD_BOT2_CHANNEL_ID) > 20 else (DISCORD_BOT2_CHANNEL_ID or 'ChÆ°a cáº¥u hÃ¬nh')}",
                 bg="#0a1a0a", fg="#888",
                 font=("Consolas", 8)).pack(anchor="w", pady=(2, 0))
        tk.Label(
            info_frame,
            text=f"ðŸ† Ranking Channel: {DISCORD_BOT2_RANKING_CHANNEL_ID[:20] + '...' if DISCORD_BOT2_RANKING_CHANNEL_ID and len(DISCORD_BOT2_RANKING_CHANNEL_ID) > 20 else (DISCORD_BOT2_RANKING_CHANNEL_ID or DISCORD_BOT2_CHANNEL_ID or 'ChÆ°a cáº¥u hÃ¬nh')}",
            bg="#0a1a0a", fg="#66cc99",
            font=("Consolas", 8)
        ).pack(anchor="w", pady=(2, 0))

        # â”€â”€ Cáº¥u hÃ¬nh Bot 2 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        cfg_frame2 = tk.Frame(self.container, bg="#0a0a1a", pady=8)
        cfg_frame2.pack(fill="x", padx=2, pady=(0, 8))
        tk.Label(cfg_frame2, text="âš™ï¸  Cáº¥u hÃ¬nh Bot 2",
                 bg="#0a0a1a", fg="#aaa",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=12)

        tk.Button(cfg_frame2, text="ðŸ“‹ Gá»­i Ranking",
                  bg="#00ff88", fg="#000", relief="flat",
                  padx=10, pady=3,
                  font=("Segoe UI", 8, "bold"),
                  command=lambda: threading.Thread(
                      target=self.send_ranking_manual, daemon=True).start()
                  ).pack(side="right", padx=4)

        # Poll cáº­p nháº­t stats Ä‘á»‹nh ká»³ khi tab Ä‘ang má»Ÿ
        self._discord_tab_open = True
        self._discord_poll_ui()

        # Load log tá»« queue
        self._dc_log_flush()

    def _discord_refresh_stats(self):
        """Cáº­p nháº­t cÃ¡c counter trÃªn tab Discord."""
        try:
            if hasattr(self, "_lbl_dc_in") and self._lbl_dc_in.winfo_exists():
                self._lbl_dc_in.configure(text=str(self._discord_msg_in))
            if hasattr(self, "_lbl_dc_out") and self._lbl_dc_out.winfo_exists():
                self._lbl_dc_out.configure(text=str(self._discord_msg_out))
            if hasattr(self, "_lbl_dc_ts") and self._lbl_dc_ts.winfo_exists():
                ts = datetime.datetime.fromtimestamp(self._discord_last_check).strftime("%H:%M:%S") \
                     if self._discord_last_check > 0 else "â€”"
                self._lbl_dc_ts.configure(text=ts)
        except tk.TclError:
            # Widget Ä‘Ã£ bá»‹ destroy khi Ä‘á»•i tab/Ä‘Ã³ng cá»­a sá»•, dá»«ng poll Ä‘á»ƒ trÃ¡nh traceback.
            self._discord_tab_open = False

    def _discord_poll_ui(self):
        """Refresh stats + flush log má»—i 2s khi tab Discord Ä‘ang má»Ÿ."""
        if not getattr(self, "_discord_tab_open", False):
            return
        self._discord_refresh_stats()
        # Cáº­p nháº­t status label Bot 1
        if hasattr(self, "_discord_status_lbl"):
            try:
                self._discord_status_lbl.configure(
                    text="â— " + self._discord_bridge_status,
                    fg="#00ff88" if self._discord_bridge_ok else
                       ("#ffa500" if "chÆ°a" in self._discord_bridge_status.lower() or
                                     "Ä‘ang" in self._discord_bridge_status.lower()
                        else "#ff5555")
                )
            except tk.TclError:
                self._discord_tab_open = False
                return
        
        # Cáº­p nháº­t status label Bot 2
        if hasattr(self, "_discord_bot2_status_lbl"):
            try:
                self._discord_bot2_status_lbl.configure(
                    text="â— " + self._discord_bot2_status,
                    fg="#00ff88" if self._discord_bot2_ok else
                       ("#ffa500" if "chÆ°a" in self._discord_bot2_status.lower() or
                                     "Ä‘ang" in self._discord_bot2_status.lower()
                        else "#ff5555")
                )
            except tk.TclError:
                pass
        
        self._dc_log_flush()
        self.root.after(2000, self._discord_poll_ui)

    def _dc_log_flush(self):
        """Flush Discord log queue â†’ _dc_log widget."""
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
                            self._dc_log.insert(tk.END, f"ðŸŸ£ {who}", "name")
                            self._dc_log.insert(tk.END, f": {msg}\n", "from_dc")
                        elif direction == "to_dc":
                            self._dc_log.insert(tk.END, f"[{ts}] ", "ts")
                            self._dc_log.insert(tk.END, f"ðŸŽ® {who}", "name")
                            self._dc_log.insert(tk.END, f"â†’ Discord: {msg}\n", "to_dc")
                        else:
                            self._dc_log.insert(tk.END, f"[{ts}] âš™ï¸ {msg}\n", "sys")
                        self._dc_log.see(tk.END)
                        self._dc_log.configure(state="disabled")
                    except tk.TclError:
                        pass
                count += 1
        except queue.Empty:
            pass

    def _discord_send_manual(self):
        """Gá»­i tin nháº¯n thá»§ cÃ´ng lÃªn Discord webhook tá»« tab Discord."""
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
            args=("ðŸ–¥ï¸ Admin", "System", msg),
            daemon=True).start()

    def _discord_force_check(self):
        """Kiá»ƒm tra tráº¡ng thÃ¡i bot Discord Gateway (tháº­t sá»±)."""
        now = datetime.datetime.now().strftime("%H:%M:%S")

        # Náº¿u bot client Ä‘ang cháº¡y qua discord.py Gateway
        client = getattr(self, "_discord_bot_client", None)
        if client is not None:
            try:
                import discord as _discord
                if not client.is_closed() and client.is_ready():
                    self._discord_bridge_ok     = True
                    self._discord_bridge_status = f"âœ… {client.user.name} â€” ðŸŸ¢ Online"
                    self._discord_last_check    = time.time()
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": now,
                        "msg": f"âœ… Bot {client.user} Ä‘ang Online â€” Gateway káº¿t ná»‘i tá»‘t"})
                    return
                elif not client.is_closed() and not client.is_ready():
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = "â³ Bot Ä‘ang káº¿t ná»‘i..."
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": now, "msg": "â³ Bot Ä‘ang trong quÃ¡ trÃ¬nh káº¿t ná»‘i..."})
                    return
                else:
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = "âš ï¸ Bot Ä‘Ã£ Ä‘Ã³ng â€” Ä‘ang chá» reconnect..."
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": now, "msg": "âš ï¸ Client Ä‘Ã£ Ä‘Ã³ng â€” chá» luá»“ng tá»± reconnect"})
                    return
            except ImportError:
                pass

        # Fallback: kiá»ƒm tra REST API náº¿u chÆ°a cÃ³ client
        self._discord_bridge_status = "â³ Äang kiá»ƒm tra..."
        self._discord_bridge_ok = False
        self._discord_log_queue.put({
            "dir": "sys", "ts": now, "msg": "â³ Äang kiá»ƒm tra via REST API..."})

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
                    self._discord_bridge_status = "âœ… Token OK (chá» Gateway káº¿t ná»‘i...)"
                    self._discord_last_check    = time.time()
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": ts,
                        "msg": "âœ… Token há»£p lá»‡ â€” bot thread Ä‘ang khá»Ÿi Ä‘á»™ng Gateway"})
                elif resp.status_code == 401:
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = "âŒ Bot Token khÃ´ng há»£p lá»‡"
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": ts, "msg": "âŒ HTTP 401 â€” Token sai"})
                elif resp.status_code == 403:
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = "âŒ Bot chÆ°a cÃ³ quyá»n Ä‘á»c kÃªnh"
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": ts,
                        "msg": "âŒ HTTP 403 â€” Bot chÆ°a Ä‘Æ°á»£c má»i vÃ o server"})
                else:
                    self._discord_bridge_ok     = False
                    self._discord_bridge_status = f"âš ï¸ HTTP {resp.status_code}"
                    self._discord_log_queue.put({
                        "dir": "sys", "ts": ts,
                        "msg": f"âš ï¸ HTTP {resp.status_code}: {resp.text[:80]}"})
            except Exception as e:
                self._discord_bridge_ok     = False
                self._discord_bridge_status = f"âŒ Lá»—i: {e}"
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                self._discord_log_queue.put({
                    "dir": "sys", "ts": ts, "msg": f"âŒ {e}"})
        threading.Thread(target=_check, daemon=True).start()

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #  DRAW: SETTINGS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def draw_settings(self):
        # â”€â”€ TiÃªu Ä‘á» + toolbar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr = tk.Frame(self.container, bg="#0a0a0a")
        hdr.pack(fill="x", pady=(0, 6))
        tk.Label(hdr, text="âš™ï¸  CÃ€I Äáº¶T SERVER",
                 bg="#0a0a0a", fg="#00ffcc",
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        tk.Label(hdr, text="(Chá»‰nh sá»­a xong nháº¥n ðŸ’¾ LÆ°u bÃªn dÆ°á»›i má»—i tab)",
                 bg="#0a0a0a", fg="#444",
                 font=("Segoe UI", 9)).pack(side="left", padx=12)

        # â”€â”€ Notebook â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        style = ttk.Style()
        style.configure("Dark.TNotebook",          background="#0a0a0a")
        style.configure("Dark.TNotebook.Tab",      background="#161616",
                        foreground="#888", padding=[12, 6])
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", "#1a1a2a")],
                  foreground=[("selected", "#00ffcc")])

        nb = ttk.Notebook(self.container, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, pady=(0, 0))

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # TAB 1 â€” App Config (Manager)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        tab_app = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_app, text="  ðŸ–¥ï¸  App Config  ")
        inner_app = self._settings_make_scrollable(tab_app)

        cfg = self._settings_load_manager_config()

        # Vars â€” App Config
        _av = {}
        def _app_var(key, default=""):
            v = tk.StringVar(value=cfg.get(key, default))
            _av[key] = v
            return v

        # â”€ Server EXE â”€
        sec = self._settings_section(inner_app, "ðŸ“ ÄÆ°á»ng dáº«n Server")
        r = 0
        self._settings_field(sec, r, "SERVER_EXE path",
                              _app_var("SERVER_EXE", SERVER_EXE),
                              note="PalServer.exe", width=60, entry_fg="#aaff77"); r += 1
        # PalWorldSettings.ini â€” tá»± derive tá»« SERVER_EXE, hiá»ƒn thá»‹ read-only
        tk.Label(sec, text="PalWorldSettings.ini",
                 bg="#0d0d0d", fg="#555", font=("Segoe UI", 9),
                 width=24, anchor="e").grid(row=r, column=0, sticky="e",
                                            padx=(0, 8), pady=3)
        tk.Label(sec, text=f"â¬† tá»± tÃ­nh tá»« SERVER_EXE  â†’  {PAL_SETTINGS_INI}",
                 bg="#0d0d0d", fg="#444", font=("Consolas", 8),
                 anchor="w").grid(row=r, column=1, sticky="ew", pady=3)
        r += 1

        # â”€ REST API & RCON â”€
        sec2 = self._settings_section(inner_app, "ðŸŒ Káº¿t ná»‘i API & RCON")
        r = 0
        self._settings_field(sec2, r, "API_URL (REST API game)",
                              _app_var("API_URL", API_URL),
                              note="http://127.0.0.1:8212/v1/api"); r += 1
        self._settings_field(sec2, r, "RCON Host",
                              _app_var("RCON_HOST", RCON_HOST)); r += 1
        self._settings_field(sec2, r, "RCON Port",
                              _app_var("RCON_PORT", str(RCON_PORT)),
                              note="máº·c Ä‘á»‹nh 25575"); r += 1
        self._settings_field(sec2, r, "AdminPassword (REST + RCON)",
                              _app_var("ADMIN_PASSWORD", AUTH.password),
                              show="*", entry_fg="#ffaaaa",
                              note="Má»™t máº­t kháº©u dÃ¹ng chung cho REST API vÃ  RCON"); r += 1
        self._settings_field(sec2, r, "PalDefender API Base URL",
                              _app_var("PALDEF_API_BASE", PALDEF_API_BASE)); r += 1

        # â”€ Discord â”€
        sec3 = self._settings_section(inner_app, "ðŸ’¬ Discord & Chat Bridge")
        r = 0
        self._settings_field(
            sec3, r, "Server Alert Webhook",
            _app_var("DISCORD_WEBHOOK_URL", DISCORD_WEBHOOK_URL),
            width=70, entry_fg="#7289da",
            note="Táº¡o webhook: https://discord.com/developers/docs/resources/webhook"
        ); r += 1
        self._settings_field(
            sec3, r, "AntiBug/Ban Webhook",
            _app_var("ANTIBUG_WEBHOOK_URL", ANTIBUG_WEBHOOK_URL),
            width=70, entry_fg="#7289da",
            note="KÃªnh admin AntiBug + ban/kick (webhook docs): https://discord.com/developers/docs/resources/webhook"
        ); r += 1
        self._settings_field(
            sec3, r, "ðŸ‘¥ Player Connect Webhook",
            _app_var("PLAYER_CONNECT_WEBHOOK_URL", PLAYER_CONNECT_WEBHOOK_URL),
            width=70, entry_fg="#7289da",
            note="Gá»­i join/leave cá»§a ngÆ°á»i chÆ¡i (webhook docs): https://discord.com/developers/docs/resources/webhook"
        ); r += 1

        # â”€â”€ Bot 1 â”€â”€
        tk.Label(
            sec3,
            text="ðŸ¤– Bot 1 (Má»“m LÃ¨o) â€” Chat Bridge 2 chiá»u",
            bg="#111", fg="#00ffcc",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=r, column=0, columnspan=4, sticky="w", pady=(14, 2), padx=(0, 8))
        r += 1
        self._settings_field(
            sec3, r, "Chat Bridge Webhook (Ingame â†’ Discord)",
            _app_var("DISCORD_CHAT_WEBHOOK", DISCORD_CHAT_WEBHOOK),
            width=70, entry_fg="#00e5ff",
            note="Webhook nháº­n chat tá»« ingame (táº¡o webhook): https://discord.com/developers/docs/resources/webhook"
        ); r += 1
        self._settings_field(
            sec3, r, "ðŸ¤– Bot 1 Token (Má»“m LÃ¨o) â€” Discord â†’ Ingame",
            _app_var("DISCORD_BOT_TOKEN", DISCORD_BOT_TOKEN),
            width=70, entry_fg="#ffd700",
            note="Báº­t Message Content Intent (náº¿u dÃ¹ng on_message) táº¡i: https://discord.com/developers/applications"
        ); r += 1
        self._settings_field(
            sec3, r, "Discord Chat Channel ID (Bot 1 - Má»“m LÃ¨o)",
            _app_var("DISCORD_CHAT_CHANNEL_ID", DISCORD_CHAT_CHANNEL_ID),
            note="KÃªnh Bot 1 láº¯ng nghe chat (chuá»™t pháº£i kÃªnh â†’ Copy Channel ID)"
        ); r += 1

        # â”€â”€ Bot 2 â”€â”€
        tk.Label(
            sec3,
            text="ðŸ¤– Bot 2 (Cá» HÃ³) â€” Commands & Features",
            bg="#111", fg="#00ffcc",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=r, column=0, columnspan=4, sticky="w", pady=(14, 2), padx=(0, 8))
        r += 1
        self._settings_field(
            sec3, r, "ðŸ† Ranking Webhook (Bot 2 - Cá» HÃ³)",
            _app_var("RANKING_WEBHOOK_URL", RANKING_WEBHOOK_URL),
            width=70, entry_fg="#00ff88",
            note="Webhook gá»­i báº£ng xáº¿p háº¡ng (webhook docs): https://discord.com/developers/docs/resources/webhook"
        ); r += 1
        self._settings_field(
            sec3, r, "ðŸ¤– Bot 2 Token (Cá» HÃ³)",
            _app_var("DISCORD_BOT2_TOKEN", DISCORD_BOT2_TOKEN),
            width=70, entry_fg="#ff9900",
            note="Bot 2 dÃ¹ng slash/command (báº­t Message Content Intent náº¿u cáº§n): https://discord.com/developers/applications"
        ); r += 1
        self._settings_field(
            sec3, r, "ðŸ¤– Bot 2 Channel ID",
            _app_var("DISCORD_BOT2_CHANNEL_ID", DISCORD_BOT2_CHANNEL_ID),
            note="KÃªnh bot Cá» HÃ³ láº¯ng nghe lá»‡nh (chuá»™t pháº£i kÃªnh â†’ Copy Channel ID)"
        ); r += 1
        self._settings_field(
            sec3, r, "ðŸ† Bot 2 Ranking Channel ID",
            _app_var("DISCORD_BOT2_RANKING_CHANNEL_ID", DISCORD_BOT2_RANKING_CHANNEL_ID),
            note="KÃªnh riÃªng Ä‘á»ƒ Ä‘Äƒng báº£ng xáº¿p háº¡ng Bot 2"
        ); r += 1
        self._settings_field(
            sec3, r, "ðŸ—ºï¸ Bot 2 LiveMap Channel ID (tuá»³ chá»n)",
            _app_var("DISCORD_BOT2_LIVEMAP_CHANNEL_ID", DISCORD_BOT2_LIVEMAP_CHANNEL_ID),
            note="Náº¿u bá» trá»‘ng: bot2 sáº½ fallback vá» DISCORD_BOT2_CHANNEL_ID"
        ); r += 1
        self._settings_field(
            sec3, r, "ðŸ¤– Bot 2 Name",
            _app_var("DISCORD_BOT2_NAME", DISCORD_BOT2_NAME),
            note="TÃªn hiá»ƒn thá»‹ cá»§a Bot 2 trong app"
        ); r += 1

        # â”€ AntiBug â”€
        sec4 = self._settings_section(inner_app, "ðŸ›¡ï¸ AntiBug Settings")
        r = 0
        self._settings_field(sec4, r, "Max Kicks trÆ°á»›c khi Ban",
                              _app_var("ANTIBUG_MAX_KICKS", str(ANTIBUG_MAX_KICKS)),
                              note=f"hiá»‡n táº¡i: {ANTIBUG_MAX_KICKS}"); r += 1
        self._settings_field(sec4, r, "Kick Window (giÃ¢y)",
                              _app_var("ANTIBUG_KICK_WINDOW", str(ANTIBUG_KICK_WINDOW)),
                              note="thá»i gian theo dÃµi kick"); r += 1

        # â”€ Save App Config button â”€
        save_bar = tk.Frame(inner_app, bg="#0a0a0a")
        save_bar.pack(fill="x", padx=14, pady=12)

        def _do_save_app():
            data = {k: v.get() for k, v in _av.items()}
            if self._settings_save_manager_config(data):
                # Ãp dá»¥ng ngay vÃ o globals â€” khÃ´ng cáº§n restart
                _apply_manager_config(data)
                ini_updates = self._settings_manager_cfg_to_ini_updates(data)
                if ini_updates:
                    self._settings_save_ini(ini_updates, PAL_SETTINGS_INI)
                messagebox.showinfo(
                    "âœ… ÄÃ£ lÆ°u & Ãp dá»¥ng App Config",
                    f"ÄÃ£ ghi vÃ o:\n{MANAGER_CONFIG_FILE}\n\n"
                    "âœ… Cáº¥u hÃ¬nh Ä‘Ã£ Ä‘Æ°á»£c Ã¡p dá»¥ng ngay láº­p tá»©c!\n\n"
                    "ðŸ“¡ API URL, RCON, Máº­t kháº©u má»›i sáº½ dÃ¹ng cho\n"
                    "   táº¥t cáº£ lá»‡nh tiáº¿p theo trong phiÃªn nÃ y."
                )

        tk.Button(save_bar,
                  text="ðŸ’¾  LÆ°u & Ãp dá»¥ng ngay  (khÃ´ng cáº§n restart)",
                  bg="#0d3b6e", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=10, cursor="hand2",
                  command=_do_save_app).pack(fill="x")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # TAB 2 â€” Server Info & Network (PalWorldSettings.ini)
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        tab_srv = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_srv, text="  ðŸŽ®  Server & Network  ")
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
                     text=f"âš ï¸  KhÃ´ng tÃ¬m tháº¥y file:\n{PAL_SETTINGS_INI}\n\n"
                          "HÃ£y cháº¡y server Ã­t nháº¥t 1 láº§n Ä‘á»ƒ táº¡o file cÃ i Ä‘áº·t.",
                     bg="#0a0a0a", fg="#ff7777",
                     font=("Segoe UI", 11), justify="left").pack(padx=20, pady=20)
        else:
            # Import INI tá»« file khÃ¡c
            import_bar = tk.Frame(inner_srv, bg="#0a0a0a")
            import_bar.pack(fill="x", padx=14, pady=(8, 0))
            tk.Label(import_bar, text=f"ðŸ“„ {PAL_SETTINGS_INI}",
                     bg="#0a0a0a", fg="#555", font=("Segoe UI", 8)).pack(side="left")

            def _do_import_ini():
                from tkinter import filedialog
                path = filedialog.askopenfilename(
                    title="Chá»n PalWorldSettings.ini",
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
                        messagebox.showinfo("âœ… Import", f"ÄÃ£ import {len(new_ini)} tham sá»‘ tá»«:\n{path}")
                    else:
                        messagebox.showerror("Lá»—i", "KhÃ´ng parse Ä‘Æ°á»£c file INI!")

            tk.Button(import_bar, text="ðŸ“‚ Import INI tá»« file khÃ¡c",
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
                messagebox.showinfo("âœ… Äá»“ng bá»™", f"ÄÃ£ Ä‘á»“ng bá»™ vÃ o:\n{PAL_SETTINGS_INI}")
            tk.Button(import_bar, text="ðŸ“¥ Äá»“ng bá»™ tá»« manager\\PalWorldSettings.ini",
                      bg="#1a2f45", fg="#9fd3ff",
                      relief="flat", padx=10, cursor="hand2",
                      command=_do_sync_manager_ini).pack(side="right", padx=(0, 8))

            # â”€ ThÃ´ng tin Server â”€
            sec_s1 = self._settings_section(inner_srv, "ðŸ·ï¸ ThÃ´ng tin Server")
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
                                  note="Ä‘á»ƒ trá»‘ng = khÃ´ng máº­t kháº©u",
                                  entry_fg="#ffaaaa"); r += 1
            self._settings_field(sec_s1, r, "Region",
                                  _svar("Region","Asia"),
                                  note="Asia / EU / US..."); r += 1

            # â”€ Network & Port â”€
            sec_s2 = self._settings_section(inner_srv, "ðŸŒ Network & Port")
            r = 0
            self._settings_field(sec_s2, r, "Public IP",
                                  _svar("PublicIP",""),
                                  entry_fg="#aaddff",
                                  note="IP public cá»§a server"); r += 1
            self._settings_field(sec_s2, r, "Public Port (Game)",
                                  _svar("PublicPort","8211"),
                                  note="máº·c Ä‘á»‹nh 8211"); r += 1
            self._settings_field(sec_s2, r, "Query Port (Steam)",
                                  _svar("QueryPort","27015"),
                                  note="máº·c Ä‘á»‹nh 27015"); r += 1
            self._settings_field(sec_s2, r, "RCON Enabled",
                                  _svar("RCONEnabled","True")); r += 1
            self._settings_field(sec_s2, r, "RCON Port",
                                  _svar("RCONPort","25575"),
                                  note="máº·c Ä‘á»‹nh 25575"); r += 1
            self._settings_field(sec_s2, r, "REST API Enabled",
                                  _svar("RESTAPIEnabled","True")); r += 1
            self._settings_field(sec_s2, r, "REST API Port",
                                  _svar("RESTAPIPort","8212"),
                                  note="máº·c Ä‘á»‹nh 8212"); r += 1
            self._settings_field(sec_s2, r, "Show Player List",
                                  _svar("bShowPlayerList","True")); r += 1

            # â”€ Player & Guild limits â”€
            sec_s3 = self._settings_section(inner_srv, "ðŸ‘¥ Giá»›i háº¡n NgÆ°á»i chÆ¡i & Guild")
            r = 0
            self._settings_field(sec_s3, r, "Max Players (Server)",
                                  _svar("ServerPlayerMaxNum","32"),
                                  note="sá»‘ ngÆ°á»i tá»‘i Ä‘a"); r += 1
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
            self._settings_field(sec_s3, r, "Guild Reset After (giá»)",
                                  _svar("AutoResetGuildTimeNoOnlinePlayers","72.000000"),
                                  note="sá»‘ giá» khÃ´ng cÃ³ ai online"); r += 1

            # â”€ Misc Server â”€
            sec_s4 = self._settings_section(inner_srv, "âš™ï¸ Cáº¥u hÃ¬nh khÃ¡c")
            r = 0
            self._settings_field(sec_s4, r, "Auto Save má»—i (giÃ¢y)",
                                  _svar("AutoSaveSpan","120.000000"),
                                  note="120 = 2 phÃºt"); r += 1
            self._settings_field(sec_s4, r, "Supply Drop Span (phÃºt)",
                                  _svar("SupplyDropSpan","90")); r += 1
            self._settings_field(sec_s4, r, "Chat Post Limit/phÃºt",
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
                                  note='VÃ­ dá»¥: ("PALBOX","RepairBench")'); r += 1

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
                        "âœ… ÄÃ£ lÆ°u",
                        "PalWorldSettings.ini Ä‘Ã£ Ä‘Æ°á»£c cáº­p nháº­t!\n\n"
                        "âš ï¸ Cáº§n RESTART SERVER Ä‘á»ƒ Ã¡p dá»¥ng thay Ä‘á»•i."
                    )

            save_bar2 = tk.Frame(inner_srv, bg="#0a0a0a")
            save_bar2.pack(fill="x", padx=14, pady=12)
            tk.Button(save_bar2,
                      text="ðŸ’¾  LÆ°u PalWorldSettings.ini  (cáº§n restart server)",
                      bg="#1a5e1a", fg="white",
                      font=("Segoe UI", 10, "bold"),
                      relief="flat", pady=10, cursor="hand2",
                      command=_do_save_server).pack(fill="x")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # TAB 3 â€” Gameplay / Rates
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        tab_gp = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_gp, text="  âš¡  Gameplay & Rates  ")
        inner_gp = self._settings_make_scrollable(tab_gp)

        _gv = {}   # gameplay vars (shared write target same _sv dict)

        def _gvar(key, default="1.000000"):
            raw = ini.get(key, str(default))
            if raw.lower() in ("true", "false"):
                v = tk.BooleanVar(value=(raw.lower() == "true"))
            else:
                v = tk.StringVar(value=raw)
            _sv[key] = v   # same dict â†’ saved by _do_save_server
            _gv[key] = v
            return v

        # â”€ Core Rates â”€
        sec_g1 = self._settings_section(inner_gp, "ðŸ“ˆ Tá»‰ lá»‡ cá»‘t lÃµi")
        r = 0
        self._settings_field(sec_g1, r, "EXP Rate",
                              _gvar("ExpRate","1.000000"),
                              note="1.0 = gá»‘c, 0.3 = 30%", entry_fg="#aaff77"); r += 1
        self._settings_field(sec_g1, r, "Pal Capture Rate",
                              _gvar("PalCaptureRate","1.000000"),
                              note="tá»‰ lá»‡ báº¯t Pal", entry_fg="#aaff77"); r += 1
        self._settings_field(sec_g1, r, "Pal Spawn Rate",
                              _gvar("PalSpawnNumRate","1.000000"),
                              note="sá»‘ lÆ°á»£ng Pal spawn"); r += 1
        self._settings_field(sec_g1, r, "Work Speed Rate",
                              _gvar("WorkSpeedRate","1.000000"),
                              note="tá»‘c Ä‘á»™ lÃ m viá»‡c"); r += 1
        self._settings_field(sec_g1, r, "Item Weight Rate",
                              _gvar("ItemWeightRate","1.000000"),
                              note="0.01 = ráº¥t nháº¹"); r += 1
        self._settings_field(sec_g1, r, "Collection Drop Rate",
                              _gvar("CollectionDropRate","1.000000"),
                              note="tÃ i nguyÃªn khai thÃ¡c"); r += 1
        self._settings_field(sec_g1, r, "Enemy Drop Item Rate",
                              _gvar("EnemyDropItemRate","1.000000"),
                              note="Ä‘á»“ rÆ¡i tá»« káº» thÃ¹"); r += 1

        # â”€ Time â”€
        sec_g2 = self._settings_section(inner_gp, "ðŸ• Thá»i gian & Pal")
        r = 0
        self._settings_field(sec_g2, r, "Day Time Speed Rate",
                              _gvar("DayTimeSpeedRate","1.000000"),
                              note="tá»‘c Ä‘á»™ ban ngÃ y"); r += 1
        self._settings_field(sec_g2, r, "Night Time Speed Rate",
                              _gvar("NightTimeSpeedRate","1.000000"),
                              note="tá»‘c Ä‘á»™ ban Ä‘Ãªm"); r += 1
        self._settings_field(sec_g2, r, "Pal Egg Hatch Time (giá»)",
                              _gvar("PalEggDefaultHatchingTime","6.000000"),
                              note="6h = máº·c Ä‘á»‹nh"); r += 1
        self._settings_field(sec_g2, r, "Drop Item Alive (giá»)",
                              _gvar("DropItemAliveMaxHours","0.046667"),
                              note="0.05h â‰ˆ 3 phÃºt"); r += 1
        self._settings_field(sec_g2, r, "Drop Item Max Num",
                              _gvar("DropItemMaxNum","1000")); r += 1

        # â”€ Pal Survival â”€
        sec_g3 = self._settings_section(inner_gp, "ðŸ¾ Chá»‰ sá»‘ Pal")
        r = 0
        self._settings_field(sec_g3, r, "Pal Stomach Decrease Rate",
                              _gvar("PalStomachDecreaceRate","1.000000"),
                              note="tiÃªu thá»¥ thá»©c Äƒn Pal"); r += 1
        self._settings_field(sec_g3, r, "Pal Stamina Decrease Rate",
                              _gvar("PalStaminaDecreaceRate","1.000000")); r += 1
        self._settings_field(sec_g3, r, "Pal Auto HP Regen Rate",
                              _gvar("PalAutoHPRegeneRate","1.000000")); r += 1
        self._settings_field(sec_g3, r, "Pal HP Regen (khi ngá»§)",
                              _gvar("PalAutoHpRegeneRateInSleep","5.000000")); r += 1

        # â”€ Player Survival â”€
        sec_g4 = self._settings_section(inner_gp, "ðŸ§ Chá»‰ sá»‘ NgÆ°á»i chÆ¡i")
        r = 0
        self._settings_field(sec_g4, r, "Player Stomach Decrease Rate",
                              _gvar("PlayerStomachDecreaceRate","1.000000")); r += 1
        self._settings_field(sec_g4, r, "Player Stamina Decrease Rate",
                              _gvar("PlayerStaminaDecreaceRate","1.000000")); r += 1
        self._settings_field(sec_g4, r, "Player Auto HP Regen Rate",
                              _gvar("PlayerAutoHPRegeneRate","1.000000")); r += 1
        self._settings_field(sec_g4, r, "Player HP Regen (khi ngá»§)",
                              _gvar("PlayerAutoHpRegeneRateInSleep","1.000000")); r += 1

        save_bar3 = tk.Frame(inner_gp, bg="#0a0a0a")
        save_bar3.pack(fill="x", padx=14, pady=12)
        tk.Button(save_bar3,
                  text="ðŸ’¾  LÆ°u Gameplay Rates  (cáº§n restart server)",
                  bg="#1a5e1a", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=10, cursor="hand2",
                  command=_do_save_server if ini else lambda: None
                  ).pack(fill="x")

        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        # TAB 4 â€” Combat & PvP
        # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
        tab_combat = tk.Frame(nb, bg="#0a0a0a")
        nb.add(tab_combat, text="  âš”ï¸  Combat & PvP  ")
        inner_cb = self._settings_make_scrollable(tab_combat)

        # â”€ Damage â”€
        sec_c1 = self._settings_section(inner_cb, "ðŸ’¥ SÃ¡t thÆ°Æ¡ng")
        r = 0
        self._settings_field(sec_c1, r, "Pal Attack Damage Rate",
                              _gvar("PalDamageRateAttack","1.000000"),
                              note="Pal gÃ¢y sÃ¡t thÆ°Æ¡ng"); r += 1
        self._settings_field(sec_c1, r, "Pal Defense Rate",
                              _gvar("PalDamageRateDefense","1.000000"),
                              note="Pal nháº­n sÃ¡t thÆ°Æ¡ng"); r += 1
        self._settings_field(sec_c1, r, "Player Attack Damage Rate",
                              _gvar("PlayerDamageRateAttack","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Player Defense Rate",
                              _gvar("PlayerDamageRateDefense","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Build Object HP Rate",
                              _gvar("BuildObjectHpRate","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Build Object Damage Rate",
                              _gvar("BuildObjectDamageRate","0.000000"),
                              note="0 = khÃ´ng bá»‹ phÃ¡"); r += 1
        self._settings_field(sec_c1, r, "Build Deterioration Rate",
                              _gvar("BuildObjectDeteriorationDamageRate","1.000000"),
                              note="0 = khÃ´ng xuá»‘ng cáº¥p"); r += 1
        self._settings_field(sec_c1, r, "Collection Object HP Rate",
                              _gvar("CollectionObjectHpRate","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Collection Object Respawn Rate",
                              _gvar("CollectionObjectRespawnSpeedRate","1.000000")); r += 1
        self._settings_field(sec_c1, r, "Equipment Durability Damage Rate",
                              _gvar("EquipmentDurabilityDamageRate","1.000000")); r += 1

        # â”€ PvP / Death â”€
        sec_c2 = self._settings_section(inner_cb, "ðŸ´ PvP & Death")
        r = 0
        self._settings_field(sec_c2, r, "PvP Mode",
                              _gvar("bIsPvP","False")); r += 1
        self._settings_field(sec_c2, r, "Player â†’ Player Damage",
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

        # â”€ Respawn â”€
        sec_c3 = self._settings_section(inner_cb, "ðŸ”„ Respawn")
        r = 0
        self._settings_field(sec_c3, r, "Block Respawn Time (giÃ¢y)",
                              _gvar("BlockRespawnTime","5.000000")); r += 1
        self._settings_field(sec_c3, r, "Respawn Penalty Threshold",
                              _gvar("RespawnPenaltyDurationThreshold","0.000000")); r += 1
        self._settings_field(sec_c3, r, "Respawn Penalty Time Scale",
                              _gvar("RespawnPenaltyTimeScale","2.000000")); r += 1

        save_bar4 = tk.Frame(inner_cb, bg="#0a0a0a")
        save_bar4.pack(fill="x", padx=14, pady=12)
        tk.Button(save_bar4,
                  text="ðŸ’¾  LÆ°u Combat & PvP  (cáº§n restart server)",
                  bg="#7b0000", fg="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", pady=10, cursor="hand2",
                  command=_do_save_server if ini else lambda: None
                  ).pack(fill="x")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    root = tk.Tk()
    app  = ManagerServerPalApp(root)
    root.mainloop()

