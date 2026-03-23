import datetime
import json
import os
import re
import shutil
from urllib.parse import urlparse


def resolve_shared_admin_password(cfg: dict) -> str:
    for key in ("AUTH_PASS", "RCON_PASSWORD", "ADMIN_PASSWORD"):
        v = cfg.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "Admin#123"


def load_manager_config(manager_config_file: str) -> dict:
    try:
        if os.path.isfile(manager_config_file):
            with open(manager_config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                pwd = resolve_shared_admin_password(cfg)
                cfg["AUTH_PASS"] = pwd
                cfg["RCON_PASSWORD"] = pwd
                cfg["ADMIN_PASSWORD"] = pwd
                return cfg
    except Exception:
        pass
    return {}


def save_manager_config(manager_config_file: str, data: dict) -> None:
    pwd = resolve_shared_admin_password(data)
    data["AUTH_PASS"] = pwd
    data["RCON_PASSWORD"] = pwd
    data["ADMIN_PASSWORD"] = pwd
    os.makedirs(os.path.dirname(manager_config_file), exist_ok=True)
    with open(manager_config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def parse_palworld_settings_ini(filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        m = re.search(r"OptionSettings=\((.+)\)", content, re.DOTALL)
        if not m:
            return {}
        inner = m.group(1)
        result = {}
        i, n = 0, len(inner)
        while i < n:
            j = i
            while j < n and inner[j] != "=":
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
                    if inner[j] == "\\":
                        j += 1
                    j += 1
                value = inner[i + 1:j]
                i = j + 1
            elif inner[i] == "(":
                depth, j = 0, i
                while j < n:
                    if inner[j] == "(":
                        depth += 1
                    elif inner[j] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                value = inner[i:j + 1]
                i = j + 1
            else:
                j = i
                while j < n and inner[j] not in (",",):
                    j += 1
                value = inner[i:j].strip()
                i = j
            result[key] = value
            if i < n and inner[i] == ",":
                i += 1
        return result
    except Exception:
        return {}


def save_palworld_settings_ini(filepath: str, updates: dict) -> None:
    data = parse_palworld_settings_ini(filepath)
    if not data:
        raise ValueError("Không đọc được PalWorldSettings.ini")
    data.update(updates)
    parts = []
    str_keys = {
        "ServerName", "ServerDescription", "AdminPassword", "ServerPassword",
        "PublicIP", "Region", "RandomizerSeed", "BanListURL",
        "AdditionalDropItemWhenPlayerKillingInPvPMode",
    }
    for k, v in data.items():
        if k in str_keys:
            v_esc = str(v).replace('"', '\\"')
            parts.append(f'{k}="{v_esc}"')
        elif isinstance(v, bool):
            parts.append(f'{k}={"True" if v else "False"}')
        else:
            parts.append(f"{k}={v}")
    opt_str = "OptionSettings=(" + ",".join(parts) + ")"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    content = re.sub(r"OptionSettings=\(.+\)", opt_str, content, flags=re.DOTALL)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def manager_cfg_to_ini_updates(cfg: dict) -> dict:
    updates = {}

    def _as_bool(v):
        s = str(v or "").strip().lower()
        if s in ("1", "true", "yes", "on"):
            return "True"
        if s in ("0", "false", "no", "off"):
            return "False"
        return ""

    admin_pw = resolve_shared_admin_password(cfg)
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


def sync_manager_ini_to_game(manager_ini_path: str, game_ini_path: str) -> str:
    if not os.path.isfile(manager_ini_path):
        raise FileNotFoundError(f"Không tìm thấy file nguồn: {manager_ini_path}")
    os.makedirs(os.path.dirname(game_ini_path), exist_ok=True)
    backup = ""
    if os.path.isfile(game_ini_path):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"{game_ini_path}.bak_{ts}"
        shutil.copy2(game_ini_path, backup)
    shutil.copy2(manager_ini_path, game_ini_path)
    return backup

