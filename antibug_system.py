import re
import time
from collections import deque


def parse_antibug_line(line: str, antibug_re) -> dict | None:
    """Parse dòng log PalDefender -> event build/dismantle hoặc None."""
    m = antibug_re.search(line)
    if not m:
        return None
    ts_str, name, steamid, action_raw, obj = m.groups()
    try:
        h, mi, s = map(int, ts_str.split(":"))
        log_ts = h * 3600 + mi * 60 + s
    except Exception:
        log_ts = int(time.time()) % 86400
    return {
        "name": name,
        "steamid": steamid,
        "action": "build" if "build" in action_raw else "dismantle",
        "object": obj,
        "log_ts": log_ts,
    }


def process_antibug_event(
    event: dict,
    *,
    antibug_enabled: bool,
    buildcheck_enabled: bool,
    max_per_sec: int,
    events_store: dict,
    run_buildcheck,
    run_techcheck,
    run_kick,
) -> None:
    """Core AntiBug xử lý tốc độ event, trigger callbacks check/kick."""
    if not antibug_enabled:
        return

    steamid = event["steamid"]
    name = event["name"]
    action = event["action"]
    obj = event["object"]
    log_ts = event["log_ts"]

    if buildcheck_enabled and action == "build":
        run_buildcheck(steamid, name, obj)
    if action == "build":
        run_techcheck(steamid, name, obj)

    if not antibug_enabled:
        return

    if steamid not in events_store:
        events_store[steamid] = {
            "name": name,
            "build": deque(),
            "dismantle": deque(),
            "kicks": deque(),
            "cooldown_until": 0.0,
        }
    d = events_store[steamid]
    d["name"] = name

    d[action].append(log_ts)
    while d[action] and log_ts - d[action][0] > 10:
        d[action].popleft()

    count_1s = sum(1 for t in d[action] if log_ts - t <= 1)
    if count_1s > max_per_sec:
        now_real = time.time()
        if now_real < d["cooldown_until"]:
            return
        d["cooldown_until"] = now_real + 15
        action_vn = "xây dựng" if action == "build" else "tháo dỡ"
        run_kick(steamid, name, action_vn, count_1s, obj)


def read_antibug_banlist_entries(ban_file_path: str) -> list[dict]:
    """Đọc banlist.txt và trả về danh sách còn đang bị ban (mới nhất trước)."""
    import os

    if not os.path.isfile(ban_file_path):
        return []
    try:
        with open(ban_file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return []

    sid_re = re.compile(r"(steam_\d+)", re.IGNORECASE)
    name_re = re.compile(r"(?:Name|Player|Tên)\s*:\s*(.+)$", re.IGNORECASE)
    unban_re = re.compile(r"\[UNBAN\]", re.IGNORECASE)

    by_sid = {}
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue

        sid_match = sid_re.search(line)
        if not sid_match:
            continue
        sid = sid_match.group(1)

        lookback = "\n".join(lines[max(0, i - 3): i + 1])
        if unban_re.search(lookback):
            by_sid.pop(sid, None)
            continue

        name = ""
        for j in range(i, max(-1, i - 10), -1):
            m_name = name_re.search(lines[j].strip())
            if m_name:
                name = m_name.group(1).strip()
                break
        if not name:
            name = "Unknown"

        by_sid[sid] = {
            "steamid": sid,
            "name": name,
            "label": f"{name} - {sid}",
        }

    return list(reversed(list(by_sid.values())))

