import datetime
import os
import threading
import time
import requests


def antibug_log(app, msg: str, antibug_log_file: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    full = f"[{ts}] {msg}"
    app._antibug_log_queue.put(full)
    app._enqueue_console(msg)
    try:
        with open(antibug_log_file, "a", encoding="utf-8") as f:
            f.write(full + "\n")
    except Exception:
        pass
    app.root.after(0, app._update_antibug_stats_label)


def update_antibug_stats_label(app):
    if hasattr(app, "_lbl_antibug_stats") and app._lbl_antibug_stats.winfo_exists():
        monitored = len(app._antibug_events)
        app._lbl_antibug_stats.config(
            text=(
                f"🎯 Giám sát: {monitored} người  │  "
                f"⚡ Kicked: {app._antibug_kick_total}  │  "
                f"🔨 Banned: {app._antibug_ban_total}"
            )
        )


def send_antibug_discord(app, content: str, read_manager_cfg, antibug_default_url: str, general_default_url: str):
    try:
        cfg = read_manager_cfg()
    except Exception:
        cfg = {}
    antibug_url = str(cfg.get("ANTIBUG_WEBHOOK_URL", "") or antibug_default_url).strip()
    general_url = str(cfg.get("DISCORD_WEBHOOK_URL", "") or general_default_url).strip()

    def _post(url: str, label: str) -> bool:
        if not url:
            return False
        try:
            res = requests.post(url, json={"content": content}, timeout=8)
            if 200 <= res.status_code < 300:
                return True
            app._enqueue_console(f"❌ Discord {label} webhook lỗi HTTP {res.status_code}: {(res.text or '').strip()[:180]}")
            return False
        except Exception as e:
            app._enqueue_console(f"❌ Discord {label} webhook exception: {e}")
            return False

    if _post(antibug_url, "AntiBug"):
        return
    if _post(general_url, "General"):
        return
    app._enqueue_console("❌ Không gửi được Discord thông báo ban: thiếu webhook hoặc webhook lỗi.")


def write_banlist(app, steamid: str, name: str, kick_count: int, kick_details: list, ts_now: str, api_status: str, antibug_ban_file: str, antibug_max_kicks: int):
    try:
        sep = "═" * 72
        lines = [
            sep,
            f"  [BAN #{app._antibug_ban_total}]  {ts_now}  — ANTIBUG AUTO-BAN",
            sep,
            f"  Tên ingame   : {name}",
            f"  SteamID      : {steamid}",
            f"  Thời gian ban: {ts_now}",
            f"  Lý do        : Xây dựng / tháo dỡ công trình quá nhanh (exploit)",
            f"  Số vi phạm   : {kick_count} lần trong 5 phút (ngưỡng kick: {antibug_max_kicks})",
            f"  API Ban      : {api_status}",
            "",
            "  Lịch sử vi phạm:",
        ]
        if kick_details:
            for i, kd in enumerate(kick_details, 1):
                lines.append(f"    [{i:02d}] {kd['time']}  │  {kd['action']} '{kd['obj']}'  │  {kd['count']}/1s (ngưỡng >{kd.get('max_ps', '?')})")
        else:
            lines.append("    (không có chi tiết)")
        lines += ["", sep, ""]
        with open(antibug_ban_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        app._enqueue_console(f"❌ Lỗi ghi banlist.txt: {e}")


def antibug_open_log(antibug_log_file: str):
    if not os.path.isfile(antibug_log_file):
        with open(antibug_log_file, "w", encoding="utf-8") as f:
            f.write(f"# ANTIBUG LOG — MANAGER SERVERPAL\n# Tạo lúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    os.startfile(antibug_log_file)


def antibug_kick_player(app, steamid: str, name: str, action_vn: str, count: int, obj: str, antibug_max_kicks: int, antibug_kick_window: int):
    max_ps = app.antibug_max_per_sec.get()
    ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    warn_msg = f"[ANTIBUG] CANH BAO: {name} {action_vn} qua nhanh ({count}/1s > {max_ps}). Vui long dung lai!"
    app._api_announce(warn_msg)
    time.sleep(0.5)
    kick_reason = f"[ANTIBUG] {action_vn} qua nhanh: {count}/1s (nguong >{max_ps})"
    kick_ok, kick_code = app._api_kick(steamid, kick_reason)
    kick_status = f"✅ Đã Xác Minh ✅ {kick_code}" if kick_ok else f"❌ HTTP {kick_code}"

    d = app._antibug_events.get(steamid)
    if d is None:
        return
    now = time.time()
    d["kicks"].append(now)
    while d["kicks"] and now - d["kicks"][0] > antibug_kick_window:
        d["kicks"].popleft()
    kick_count_5min = len(d["kicks"])
    d.setdefault("kick_details", []).append({
        "time": ts_now, "action": action_vn, "count": count, "obj": obj, "max_ps": max_ps, "api": kick_status
    })
    app._antibug_kick_total += 1
    app._antibug_log(
        f"⚡ KICK #{app._antibug_kick_total}  [{ts_now}]\n"
        f"   Người chơi : {name}  ({steamid})\n"
        f"   Hành động  : {action_vn} '{obj}' — {count}/1s  (ngưỡng >{max_ps})\n"
        f"   API Kick   : {kick_status}\n"
        f"   Vi phạm    : {kick_count_5min}/{antibug_max_kicks} lần trong 5 phút"
    )
    if app.antibug_discord_alert.get():
        disc = (
            f"⚡ **[ANTIBUG — KICK #{app._antibug_kick_total}]**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Người chơi:** {name}\n"
            f"🆔 **SteamID:** `{steamid}`\n"
            f"🕐 **Thời gian:** `{ts_now}`\n"
            f"⚠️ **Lý do:** {action_vn} `{obj}` — **{count}/1s** (ngưỡng >{max_ps})\n"
            f"🌐 **Kết quả thẩm phán kick:** {kick_status}\n"
            f"📊 **Vi phạm:** lần **{kick_count_5min}/{antibug_max_kicks}** trong 5 phút\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        threading.Thread(target=app._send_antibug_discord, args=(disc,), daemon=True).start()
    if kick_count_5min >= antibug_max_kicks:
        app._antibug_ban_player(steamid, name, kick_count_5min)


def antibug_ban_player(app, steamid: str, name: str, kick_count: int):
    ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ban_reason = f"[ANTIBUG] Vi pham build/dismantle bug {kick_count} lan trong 5 phut — AUTO-BAN"
    ban_ok, ban_code = app._api_ban(steamid, ban_reason)
    ban_status = f"✅ Đã Xác Minh ✅ {ban_code}" if ban_ok else f"❌ HTTP {ban_code}"
    app._api_announce(f"[ANTIBUG] {name} da bi BAN vinh vien (vi pham {kick_count} lan trong 5 phut)!")
    app._antibug_ban_total += 1
    d = app._antibug_events.get(steamid, {})
    kick_details = d.get("kick_details", [])
    app._write_banlist(steamid, name, kick_count, kick_details, ts_now, ban_status)
    app._antibug_log(
        f"🔨 BAN #{app._antibug_ban_total}  [{ts_now}]\n"
        f"   Người chơi : {name}  ({steamid})\n"
        f"   Vi phạm    : {kick_count} lần trong 5 phút\n"
        f"   API Ban    : {ban_status}\n"
        f"   File       : banlist.txt đã được cập nhật"
    )
    if app.antibug_discord_alert.get():
        hist_lines = "\n".join(
            f"   `[{i:02d}]` `{kd['time']}` — {kd['action']} **{kd['obj']}** {kd['count']}/1s | {kd['api']}"
            for i, kd in enumerate(kick_details, 1)
        ) or "   *(không có chi tiết)*"
        disc = (
            f"🔨 **[ANTIBUG — BAN VĨNH VIỄN #{app._antibug_ban_total}]**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Người chơi:** {name}\n"
            f"🆔 **SteamID:** `{steamid}`\n"
            f"🕐 **Thời gian ban:** `{ts_now}`\n"
            f"📊 **Tổng vi phạm:** {kick_count} lần trong 5 phút\n"
            f"🌐 **Kết quả thẩm phán ban:** {ban_status}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**📋 Lịch sử vi phạm:**\n{hist_lines}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f">>> ⛔ **ĐÃ BAN VĨNH VIỄN** — ghi vào `banlist.txt` <<<"
        )
        threading.Thread(target=app._send_antibug_discord, args=(disc,), daemon=True).start()

