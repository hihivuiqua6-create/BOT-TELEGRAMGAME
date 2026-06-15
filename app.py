# -*- coding: utf-8 -*-
"""
KINGBOT ULTRA RENDER
Flask Web Admin + Telegram Polling Bot
Start command: python app.py
Build command: pip install -r core/deploy/requirements.txt
"""

import os, sys, json, time, threading, secrets, hashlib, statistics, urllib.parse, random, traceback, html, re
from datetime import datetime, timedelta

import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, redirect, session, render_template_string, render_template, jsonify, send_file, make_response
try:
    from engine_md5 import predict_basic as engine_predict_basic, predict_pro as engine_predict_pro, predict_free as engine_predict_free
except Exception:
    engine_predict_basic = None
    engine_predict_pro = None
    engine_predict_free = None

ROOT = os.path.dirname(os.path.abspath(__file__))
CORE = os.path.join(ROOT, "core")
if CORE not in sys.path:
    sys.path.insert(0, CORE)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(ROOT, "data"))
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
DB_FILE = os.path.join(DATA_DIR, "database.json")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "bot_token": "",
    "admin_password": "admin123",
    "admin_ids": [],
    "shop_name": "KingBot Luxury",
    "accent": "#8b5cf6",
    "welcome_text": "Hệ thống phân tích MD5 Tài/Xỉu cao cấp",
    "support_url": "https://t.me/",
    "group_chat_id": "",
    "group_link": "",
    "group_link": "",
    "bank_name_key": "MSB",
    "bank_bin": "970426",
    "bank_account": "1234567890",
    "bank_name": "NGUYEN VAN A",
    "payment_note_prefix": "NAP",
    "backup_url": "",
    "backup_secret": "CHANGE_ME_123",
    "backup_interval_seconds": 120,
    "algorithm_enabled": False,
    "algorithm_code": "",
    "algorithm_note": "Paste Python có hàm predict(md5, gate, level) hoặc predict_basic/predict_pro/predict_free.",
    "algorithm_tiers": {
        "free":  {"name": "Free",  "mode": "weak",   "use_admin": True, "history_limit": 30,  "max_conf": 68, "penalty": 8,  "min_entry": 62},
        "basic": {"name": "Thường","mode": "normal", "use_admin": True, "history_limit": 160, "max_conf": 88, "penalty": 2,  "min_entry": 58},
        "pro":   {"name": "Pro",   "mode": "royal",  "use_admin": True, "history_limit": 500, "max_conf": 98, "penalty": 0,  "min_entry": 54}
    },
    "free_mode_enabled": False,
    "free_until": 0,
    "free_duration_hours": 24,
    "free_require_join": True,
    "free_channel": "",
    "free_channel_link": "",
    "deposit_bonus_enabled": True,
    "deposit_bonus_percent": 10,
    "deposit_bonus_min": 50000,
    "purchase_bonus_enabled": True,
    "purchase_bonus_chance": 8,
    "purchase_bonus_percent": 5,
    "api_tools": {
        "lc79_tool": {"enabled": True, "name": "LC79 Tool", "gate": "lc79", "level": "pro", "secret": "", "cors": True},
        "hitclub_tool": {"enabled": True, "name": "HitClub Tool", "gate": "hitclub", "level": "pro", "secret": "", "cors": True},
        "baccarat_tool": {"enabled": True, "name": "Baccarat Tool", "gate": "bcr", "level": "pro", "secret": "", "cors": True}
    },
    "custom_api_urls": {"bcr": [], "lc79": [], "hitclub": [], "betvip": [], "sunwin": [], "b52": [], "sicb52": [], "sichit": []},
    "gates": {
        "lc79": {"name": "LC79", "icon": "🎲", "enabled": True, "md5": True, "nomd5": True},
        "hitclub": {"name": "HitClub", "icon": "♠️", "enabled": True, "md5": True, "nomd5": True},
        "betvip": {"name": "BetVip", "icon": "💎", "enabled": True, "md5": True, "nomd5": True},
        "sunwin": {"name": "SunWin", "icon": "☀️", "enabled": True, "md5": False, "nomd5": True},
        "b52": {"name": "B52", "icon": "🚀", "enabled": True, "md5": False, "nomd5": True},
        "sicb52": {"name": "SicBo B52", "icon": "🎯", "enabled": True, "md5": False, "nomd5": True},
        "sichit": {"name": "SicBo HitClub", "icon": "🎰", "enabled": True, "md5": False, "nomd5": True},
        "bcr": {"name": "Baccarat", "icon": "🃏", "enabled": True, "md5": False, "nomd5": True}
    },
    "plans": {
        "basic": {"name": "Gói Thường", "price_per_hour": 1500, "hours": 1, "level": "basic"},
        "pro": {"name": "Gói Pro", "price_per_hour": 3500, "hours": 1, "level": "pro"}
    },
    "admin_keys": {},
    "child_bots": {},
    "plan_options": {
        "basic": {
            "hour": {"enabled": True, "label": "1 giờ", "seconds": 3600, "price": 1500},
            "day": {"enabled": True, "label": "1 ngày", "seconds": 86400, "price": 25000},
            "week": {"enabled": True, "label": "1 tuần", "seconds": 604800, "price": 120000},
            "month": {"enabled": True, "label": "1 tháng", "seconds": 2592000, "price": 350000},
            "forever": {"enabled": False, "label": "Vĩnh viễn", "seconds": 315360000, "price": 1500000}
        },
        "pro": {
            "hour": {"enabled": True, "label": "1 giờ", "seconds": 3600, "price": 3500},
            "day": {"enabled": True, "label": "1 ngày", "seconds": 86400, "price": 65000},
            "week": {"enabled": True, "label": "1 tuần", "seconds": 604800, "price": 300000},
            "month": {"enabled": True, "label": "1 tháng", "seconds": 2592000, "price": 850000},
            "forever": {"enabled": False, "label": "Vĩnh viễn", "seconds": 315360000, "price": 3500000}
        }
    }
}

DEFAULT_DB = {
    "users": {},
    "transactions": [],
    "announcements": [],
    "deposits": [],
    "feedback": [],
    "purchases": [],
    "predictions": [],
    "prediction_checks": [],
    "api_winloss": {},
    "live_streaks": {},
    "free_usage": {},
    "free_sessions": [],
    "child_bot_data": {},
    "child_admin_sessions": {}
}

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg):
    line = f"[{now_str()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def deep_merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge(a[k], v)
        else:
            a[k] = v

def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
        return json.loads(json.dumps(default, ensure_ascii=False))
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        merged = json.loads(json.dumps(default, ensure_ascii=False))
        if isinstance(d, dict):
            deep_merge(merged, d)
        return merged
    except Exception as e:
        log(f"Lỗi JSON {path}: {e}")
        return json.loads(json.dumps(default, ensure_ascii=False))

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

cfg = load_json(CONFIG_FILE, DEFAULT_CONFIG)
db = load_json(DB_FILE, DEFAULT_DB)

# Ép mặc định giá gói theo yêu cầu mới nếu config cũ còn giá cũ.
try:
    if int(cfg.get("plans",{}).get("basic",{}).get("price_per_hour",0)) in (0, 5000):
        cfg["plans"]["basic"]["price_per_hour"] = 1500
    if int(cfg.get("plans",{}).get("pro",{}).get("price_per_hour",0)) in (0, 12000):
        cfg["plans"]["pro"]["price_per_hour"] = 3500
except Exception:
    pass

# Chuẩn hoá danh sách cổng: config cũ thường thiếu md5/nomd5 nên API chỉ hiện 1 cổng.
def ensure_gate_config():
    default_gates = DEFAULT_CONFIG.get("gates", {})
    cfg.setdefault("gates", {})
    for gk, gv in default_gates.items():
        cur = cfg["gates"].get(gk)
        if not isinstance(cur, dict):
            cfg["gates"][gk] = dict(gv)
        else:
            # giữ tên/icon admin đã sửa, nhưng luôn bổ sung enabled/md5/nomd5 nếu thiếu
            for kk, vv in gv.items():
                cur.setdefault(kk, vv)
    # Loại theo yêu cầu: B52 và SunWin không nằm ở tab MD5, chỉ nằm API
    if "sunwin" in cfg["gates"]:
        cfg["gates"]["sunwin"]["md5"] = False; cfg["gates"]["sunwin"]["nomd5"] = True
    if "b52" in cfg["gates"]:
        cfg["gates"]["b52"]["md5"] = False; cfg["gates"]["b52"]["nomd5"] = True
    for gk in ("sicb52", "sichit", "bcr"):
        if gk in cfg["gates"]:
            cfg["gates"][gk]["md5"] = False; cfg["gates"][gk]["nomd5"] = True
    for gk in ("lc79", "hitclub", "betvip"):
        if gk in cfg["gates"]:
            cfg["gates"][gk]["md5"] = True; cfg["gates"][gk]["nomd5"] = True

ensure_gate_config()

# Chuẩn hoá API Tool để config cũ vẫn hiện đủ LC79/HitClub/Baccarat trong Admin.
def ensure_api_tools_config():
    cfg.setdefault("api_tools", {})
    cfg.setdefault("custom_api_urls", {})
    for slug, tool in DEFAULT_CONFIG.get("api_tools", {}).items():
        cur = cfg["api_tools"].get(slug)
        if not isinstance(cur, dict):
            cfg["api_tools"][slug] = dict(tool)
        else:
            for kk, vv in tool.items():
                cur.setdefault(kk, vv)
    for gk in DEFAULT_CONFIG.get("custom_api_urls", {}).keys():
        cfg["custom_api_urls"].setdefault(gk, [])
    # Alias dễ nhìn nếu admin muốn tạo nhanh baccarat riêng.
    cfg["api_tools"].setdefault("baccarat", {"enabled": True, "name": "Baccarat API", "gate": "bcr", "level": "pro", "secret": "", "cors": True})

ensure_api_tools_config()

# Không ép token/config từ Render ENV.
# Token bot, backup URL/secret và thông số khác được lưu/chỉnh trong Web Admin.
# ENV chỉ còn dùng cho PORT/DATA_DIR/SECRET_KEY hệ thống.
save_json(CONFIG_FILE, cfg)

bot = None
bot_running = False
user_state = {}
algo_cache = {"hash": None, "ns": {}, "error": ""}

def save_cfg(): save_json(CONFIG_FILE, cfg)
def save_db(): save_json(DB_FILE, db)

def bank_bin_from_name(name):
    banks = {
        "MSB": "970426", "VCB": "970436", "VIETCOMBANK": "970436",
        "MB": "970422", "MBBANK": "970422", "ACB": "970416",
        "TECHCOMBANK": "970407", "TCB": "970407", "BIDV": "970418",
        "AGRIBANK": "970405", "VIETINBANK": "970415", "VPBANK": "970432",
        "TPBANK": "970423", "SACOMBANK": "970403", "HDBANK": "970437",
        "VIB": "970441", "SHB": "970443", "OCB": "970448",
        "SEABANK": "970440", "NAMABANK": "970428", "EXIMBANK": "970431"
    }
    k = str(name or "").upper().replace(" ", "")
    return banks.get(k, str(cfg.get("bank_bin", "970426")).strip())

def backup_payload():
    return {"time": now_str(), "config": cfg, "database": db}

def push_backup(reason="auto"):
    url = str(cfg.get("backup_url", "")).strip()
    secret = str(cfg.get("backup_secret", "")).strip()
    if not url or not secret:
        return False, "Chưa cài backup_url/secret"
    try:
        headers = {"User-Agent": "KingBotBackup/1.0", "Accept": "application/json", "Connection": "close"}
        payload_json = json.dumps({"secret": secret, "reason": reason, "payload": backup_payload()}, ensure_ascii=False)
        r = requests.post(url, data=payload_json.encode("utf-8"), headers={**headers, "Content-Type": "application/json; charset=utf-8"}, timeout=25)
        if r.status_code == 200:
            return True, r.text[:200]
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, repr(e)

def pull_backup():
    url = str(cfg.get("backup_url", "")).strip()
    secret = str(cfg.get("backup_secret", "")).strip()
    if not url or not secret:
        return False, "Chưa cài backup_url/secret"
    try:
        sep = "&" if "?" in url else "?"
        headers = {"User-Agent": "KingBotBackup/1.0", "Accept": "application/json", "Connection": "close"}
        r = requests.get(url + sep + "secret=" + urllib.parse.quote(secret), headers=headers, timeout=25)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        data = r.json()
        payload = data.get("payload") or data
        new_cfg = payload.get("config") if isinstance(payload, dict) else None
        new_db = payload.get("database") if isinstance(payload, dict) else None
        if isinstance(new_cfg, dict) and isinstance(new_db, dict):
            cfg.clear(); cfg.update(new_cfg)
            db.clear(); db.update(new_db)
            save_cfg(); save_db()
            return True, "Đã kéo backup mới nhất"
        return False, "Backup không đúng định dạng"
    except Exception as e:
        return False, repr(e)

def backup_worker():
    ok, msg = pull_backup()
    log(f"PULL BACKUP START: {ok} {msg}")
    while True:
        try:
            interval = int(cfg.get("backup_interval_seconds", 120) or 120)
            time.sleep(max(30, interval))
            ok, msg = push_backup("interval")
            log(f"PUSH BACKUP: {ok} {msg}")
        except Exception as e:
            log(f"LỖI BACKUP WORKER: {e}")
            time.sleep(60)

def money(n):
    try: n = int(n)
    except Exception: n = 0
    return f"{n:,}".replace(",", ".") + "đ"

def mask_user(uid, username=""):
    uid = str(uid)
    if username:
        username = str(username)
        if len(username) <= 2:
            return username[0] + "***"
        return username[0] + "***" + username[-1]
    if len(uid) <= 4:
        return uid[:1] + "***"
    return uid[:3] + "***" + uid[-2:]

def display_user_full(uid, username=""):
    """Hiển thị user đầy đủ cho admin web, không che tên."""
    uid = str(uid or "")
    username = str(username or "").strip()
    if username and username.lower() != "none":
        return f"@{username} · {uid}"
    return uid

def first_enabled_gate():
    gates = cfg.get("gates") if isinstance(cfg.get("gates"), dict) else {}
    for gk, gv in gates.items():
        if isinstance(gv, dict) and gv.get("enabled", True):
            return gk
    if gates:
        return next(iter(gates.keys()))
    return "lc79"

def normalize_gate(gate):
    gates = cfg.get("gates") if isinstance(cfg.get("gates"), dict) else {}
    if gate in gates:
        return gate
    return first_enabled_gate()

def is_admin(uid):
    return str(uid) in [str(x) for x in cfg.get("admin_ids", [])]

def get_user(obj):
    u = obj.from_user
    uid = str(u.id)
    username = u.username or u.first_name or "user"
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": uid,
            "username": username,
            "balance": 0,
            "active_plan": None,
            "selected_plan": None,
            "active_gate": None,
            "plan_expire": 0,
            "plan_expires": {"basic": 0, "pro": 0},
            "joined": now_str(),
            "total_deposit": 0,
            "total_spent": 0
        }
    else:
        db["users"][uid]["username"] = username
    # V94: mỗi gói có hạn riêng, không khóa cố định 1 gói.
    if "plan_expires" not in db["users"][uid] or not isinstance(db["users"][uid].get("plan_expires"), dict):
        old_plan = db["users"][uid].get("active_plan")
        old_exp = int(db["users"][uid].get("plan_expire", 0) or 0)
        db["users"][uid]["plan_expires"] = {"basic": 0, "pro": 0}
        if old_plan in ("basic", "pro") and old_exp > int(time.time()):
            db["users"][uid]["plan_expires"][old_plan] = old_exp
    db["users"][uid].setdefault("selected_plan", db["users"][uid].get("active_plan"))
    save_db()
    return uid, db["users"][uid], username

def plan_expire_ts(user, plan_key=None):
    """Hạn dùng riêng từng gói: basic/pro. Giữ tương thích dữ liệu cũ plan_expire."""
    now = int(time.time())
    pe = user.get("plan_expires") if isinstance(user.get("plan_expires"), dict) else {}
    if plan_key in ("basic", "pro"):
        exp = int(pe.get(plan_key, 0) or 0)
        if exp <= 0 and user.get("active_plan") == plan_key:
            exp = int(user.get("plan_expire", 0) or 0)
        return exp
    # trả hạn xa nhất
    vals = [int(pe.get(k, 0) or 0) for k in ("basic", "pro")]
    old = int(user.get("plan_expire", 0) or 0)
    vals.append(old)
    return max(vals or [0])

def active_until_text(user, plan_key=None):
    exp = plan_expire_ts(user, plan_key)
    if exp <= int(time.time()):
        return "Chưa có gói"
    return datetime.fromtimestamp(exp).strftime("%d/%m/%Y %H:%M")

def remaining_time_text(user, plan_key=None):
    exp = plan_expire_ts(user, plan_key)
    left = exp - int(time.time())
    if left <= 0:
        return "0 phút"
    days = left // 86400
    hours = (left % 86400) // 3600
    minutes = (left % 3600) // 60
    parts = []
    if days: parts.append(f"{days} ngày")
    if hours: parts.append(f"{hours} giờ")
    if minutes or not parts: parts.append(f"{minutes} phút")
    return " ".join(parts)

def has_active_plan(user, plan_key=None):
    if plan_key in ("basic", "pro"):
        return plan_expire_ts(user, plan_key) > int(time.time())
    return any(plan_expire_ts(user, k) > int(time.time()) for k in ("basic", "pro"))

def best_available_plan(user):
    # Ưu tiên gói user đã chọn nếu còn hạn, sau đó pro, rồi basic
    sp = user.get("selected_plan")
    if sp in ("basic", "pro") and has_active_plan(user, sp):
        return sp
    if has_active_plan(user, "pro"):
        return "pro"
    if has_active_plan(user, "basic"):
        return "basic"
    return None

def plan_status_line(user):
    return (
        f"⭐ Thường: <b>{remaining_time_text(user, 'basic')}</b>\n"
        f"💎 Pro: <b>{remaining_time_text(user, 'pro')}</b>"
    )

def choose_plan_keyboard(gate_key, user, include_back=True):
    kb = InlineKeyboardMarkup()
    if has_active_plan(user, "basic"):
        kb.add(InlineKeyboardButton(f"⭐ Dùng Gói Thường · còn {remaining_time_text(user,'basic')}", callback_data="useplan_basic"))
    if has_active_plan(user, "pro"):
        kb.add(InlineKeyboardButton(f"💎 Dùng Gói Pro · còn {remaining_time_text(user,'pro')}", callback_data="useplan_pro"))
    if free_is_active():
        kb.add(InlineKeyboardButton(f"🎁 Dùng Free · còn {free_remaining_text()}", callback_data="useplan_free"))
    for pk, p in cfg.get("plans", {}).items():
        emoji = "💎" if pk == "pro" else "⭐"
        kb.add(InlineKeyboardButton(f"{emoji} Mua {p.get('name',pk)} - {money(p.get('price_per_hour',0))}/giờ", callback_data=f"buy_{pk}"))
    if include_back:
        kb.add(InlineKeyboardButton("🔙 Đổi kiểu/cổng", callback_data="choose_type"))
    return kb

def normalize_group_target():
    """
    Nhập được:
    - GROUP_CHAT_ID kiểu -100xxxxxxxxxx
    - @username_group
    - link https://t.me/username_group
    - link https://t.me/+invite hoặc t.me/+invite: loại này Telegram Bot API không gửi được nếu không biết chat_id.
    """
    raw = str(cfg.get("group_chat_id", "") or cfg.get("group_link", "") or "").strip()
    if not raw:
        return ""
    if raw.startswith("-100") or raw.lstrip("-").isdigit():
        return raw
    if raw.startswith("@"):
        return raw
    if "t.me/" in raw:
        tail = raw.split("t.me/", 1)[1].split("?", 1)[0].strip("/")
        if tail.startswith("+") or tail.startswith("joinchat/"):
            return ""  # invite link không đổi được sang chat_id bằng Bot API
        return "@" + tail
    return raw

def free_is_active():
    return bool(cfg.get("free_mode_enabled", False)) and int(cfg.get("free_until", 0) or 0) > int(time.time())

def free_until_text():
    ts = int(cfg.get("free_until", 0) or 0)
    if not cfg.get("free_mode_enabled", False) or ts <= int(time.time()):
        return "Đang tắt"
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def free_remaining_text():
    ts = int(cfg.get("free_until", 0) or 0)
    left = ts - int(time.time())
    if not cfg.get("free_mode_enabled", False) or left <= 0:
        return "0 phút"
    days = left // 86400
    hours = (left % 86400) // 3600
    minutes = (left % 3600) // 60
    parts = []
    if days: parts.append(f"{days} ngày")
    if hours: parts.append(f"{hours} giờ")
    if minutes or not parts: parts.append(f"{minutes} phút")
    return " ".join(parts)

def normalize_channel_target():
    raw = str(cfg.get("free_channel", "") or cfg.get("free_channel_link", "") or "").strip()
    if not raw:
        return ""
    if raw.startswith("@") or raw.startswith("-100") or raw.lstrip("-").isdigit():
        return raw
    if "t.me/" in raw:
        tail = raw.split("t.me/", 1)[1].split("?", 1)[0].strip("/")
        if tail.startswith("+") or tail.startswith("joinchat/"):
            return ""
        return "@" + tail
    return "@" + raw.lstrip("@")

def user_joined_free_channel(uid):
    if not cfg.get("free_require_join", True):
        return True
    target = normalize_channel_target()
    if not target or not bot:
        return True
    try:
        m = bot.get_chat_member(target, int(uid))
        return str(m.status) in ("creator", "administrator", "member")
    except Exception as e:
        log(f"Không kiểm tra được kênh free {target}: {e}")
        return False

def join_channel_message():
    link = str(cfg.get("free_channel_link", "") or cfg.get("free_channel", "") or "").strip()
    if link and not link.startswith("http") and not link.startswith("@") and not link.startswith("-100"):
        link = "https://t.me/" + link.lstrip("@")
    if not link:
        link = "kênh đã cấu hình trong admin"
    return (
        "🚀 <b>FREE MODE đang mở</b> nhưng bạn cần tham gia kênh trước khi dùng.\n\n"
        f"📢 Kênh: {link}\n"
        "✅ Vào kênh xong gửi lại MD5 để bot kiểm tra và dự đoán."
    )

def bonus_deposit_amount(amount):
    if not cfg.get("deposit_bonus_enabled", False):
        return 0
    if int(amount) < int(cfg.get("deposit_bonus_min", 0) or 0):
        return 0
    return int(int(amount) * int(cfg.get("deposit_bonus_percent", 0) or 0) / 100)

def purchase_bonus_amount(total):
    if not cfg.get("purchase_bonus_enabled", False):
        return 0
    chance = int(cfg.get("purchase_bonus_chance", 0) or 0)
    if chance <= 0:
        return 0
    if random.randint(1, 100) > chance:
        return 0
    return int(int(total) * int(cfg.get("purchase_bonus_percent", 0) or 0) / 100)

def plan_price(plan_key):
    p = cfg["plans"][plan_key]
    return int(p.get("price_per_hour", 0)) * int(p.get("hours", 1))

def ensure_plan_options():
    cfg.setdefault("plan_options", {})
    defaults = DEFAULT_CONFIG.get("plan_options", {})
    for pk, opts in defaults.items():
        cfg["plan_options"].setdefault(pk, {})
        for ok, ov in opts.items():
            cur = cfg["plan_options"][pk].get(ok)
            if not isinstance(cur, dict):
                cfg["plan_options"][pk][ok] = dict(ov)
            else:
                for k, v in ov.items():
                    cur.setdefault(k, v)
    return cfg["plan_options"]

def enabled_plan_options(plan_key):
    ensure_plan_options()
    out=[]
    order=["hour","day","week","month","forever"]
    for ok in order:
        op=cfg.get("plan_options",{}).get(plan_key,{}).get(ok)
        if isinstance(op, dict) and op.get("enabled", False):
            out.append((ok, op))
    return out

def duration_label(seconds):
    try: seconds=int(seconds)
    except Exception: seconds=3600
    if seconds >= 315360000: return "Vĩnh viễn"
    if seconds % 2592000 == 0 and seconds >= 2592000: return f"{seconds//2592000} tháng"
    if seconds % 604800 == 0 and seconds >= 604800: return f"{seconds//604800} tuần"
    if seconds % 86400 == 0 and seconds >= 86400: return f"{seconds//86400} ngày"
    if seconds % 3600 == 0: return f"{seconds//3600} giờ"
    return f"{seconds//60} phút"

def plan_option_keyboard(plan_key):
    kb=InlineKeyboardMarkup(row_width=1)
    for ok, op in enabled_plan_options(plan_key):
        kb.add(InlineKeyboardButton(f"⏳ {op.get('label', duration_label(op.get('seconds',3600)))} · {money(op.get('price',0))}", callback_data=f"buydur_{plan_key}_{ok}"))
    if not enabled_plan_options(plan_key):
        kb.add(InlineKeyboardButton("⚠️ Admin chưa bật mốc thời gian", callback_data="noop"))
    kb.add(InlineKeyboardButton("🔙 Chọn gói khác", callback_data="buy_tool"))
    return kb

ensure_plan_options()

def gate_name(gate_key):
    return cfg["gates"].get(gate_key, {}).get("name", gate_key.upper())

def gate_icon(gate_key):
    return cfg["gates"].get(gate_key, {}).get("icon", "🎮")

def enabled_gates():
    return {k:v for k,v in cfg["gates"].items() if v.get("enabled", True)}

def _clamp(v, a, b):
    return max(a, min(b, v))

def _history_bits(history):
    if not history:
        return []
    out=[]
    for x in history:
        t=str(x).strip().upper()
        if t in ("T", "TAI", "TÀI", "1", "BIG", "B"):
            out.append(1)
        elif t in ("X", "XIU", "XỈU", "0", "SMALL", "S"):
            out.append(0)
        elif isinstance(x, dict):
            r=str(x.get("result", x.get("taixiu", ""))).upper()
            if r.startswith("T"): out.append(1)
            elif r.startswith("X"): out.append(0)
    return out

def _runs(bits):
    if not bits: return []
    out=[]; cur=bits[0]; cnt=1
    for x in bits[1:]:
        if x == cur: cnt += 1
        else:
            out.append((cur,cnt)); cur=x; cnt=1
    out.append((cur,cnt))
    return out

def gates_by_mode(mode="md5"):
    mode = str(mode or "md5").lower()
    ensure_gate_config()
    out = {}
    for k, v in enabled_gates().items():
        if mode == "md5" and bool(v.get("md5", False)):
            out[k] = v
        elif mode in ("nomd5", "no_md5", "api") and bool(v.get("nomd5", False)):
            # V111: luôn hiện đủ cổng API trong bot, kể cả Baccarat.
            # Nếu API nguồn đang lỗi thì lúc bấm Chạy API sẽ báo lỗi rõ, không ẩn nút làm admin tưởng chưa có cổng.
            out[k] = v
    return out

def mode_title(mode):
    return "Dự đoán MD5" if str(mode or "md5") == "md5" else "Dự đoán API"

def stable_int(*parts, mod=10000):
    raw = "|".join(map(str, parts)).encode("utf-8", "ignore")
    return int(hashlib.sha256(raw).hexdigest()[:12], 16) % mod

NOMD5_API_MAP = {
    # V100: API lấy từ source sadd.zip, bỏ 1.html/fake phiên.
    # API chỉ dùng các cổng thật có API phiên.
    "lc79": {
        "urls": [
            "https://wtx.tele68.com/v1/tx/sessions",
            "https://laucua79-p7tw.onrender.com/taixiu",
        ],
        "period_keys": ["sid","session","phien","Phien","id","issue","round","gameNum","current_session"],
        "total_keys": ["total","score","tong","Tong","sum","diem"],
        "dice_keys": ["dice","xuc_xac","xucxac","xx","dices"],
        "predict_keys": ["du_doan","prediction","Prediction","predict","result","ket_qua","taixiu","tai_xiu"],
        "confidence_keys": ["do_tin_cay","confidence","Độ Tin Cậy","ti_le","rate","percent"],
    },
    "hitclub": {
        "urls": [
            "https://sun-win.onrender.com/api/history",
            "https://api.wsmt8g.cc/v2/history/getLastResult?gameId=ktrng_3932&size=120&tableId=39321215743193&curPage=1",
            "https://hitclub-foua.onrender.com/taixiu",
        ],
        "period_keys": ["gameNum","sid","session","phien","Phien","id","issue","round","current_session"],
        "total_keys": ["score","total","tong","Tong","sum","diem"],
        "dice_keys": ["dice","xuc_xac","xucxac","xx","dices"],
        "predict_keys": ["du_doan","prediction","Prediction","predict","result","ket_qua","taixiu","tai_xiu"],
        "confidence_keys": ["do_tin_cay","confidence","Độ Tin Cậy","ti_le","rate","percent"],
    },
    "betvip": {
        "urls": [
            "https://wtx.macminim6.online/v1/tx/sessions",
            "https://betvip-b8gk.onrender.com/taixiu",
        ],
        "period_keys": ["sid","session","phien","Phien","id","issue","round","gameNum","current_session"],
        "total_keys": ["total","score","tong","Tong","sum","diem"],
        "dice_keys": ["dice","xuc_xac","xucxac","xx","dices"],
        "predict_keys": ["du_doan","prediction","Prediction","predict","result","ket_qua","taixiu","tai_xiu"],
        "confidence_keys": ["do_tin_cay","confidence","Độ Tin Cậy","ti_le","rate","percent"],
    },
    "sunwin": {
        "urls": [
            "https://api.wsktnus8.net/v2/history/getLastResult?gameId=ktrng_3979&size=100&tableId=39791215743193&curPage=1",
            "https://sun-ls.onrender.com/sunlon",
        ],
        "period_keys": ["gameNum","sid","session","phien","Phien","id","issue","round","current_session"],
        "total_keys": ["score","total","tong","Tong","sum","diem"],
        "dice_keys": ["dice","xuc_xac","xucxac","xx","dices"],
        "predict_keys": ["du_doan","prediction","Prediction","predict","result","ket_qua","taixiu","tai_xiu"],
        "confidence_keys": ["do_tin_cay","confidence","Độ Tin Cậy","ti_le","rate","percent"],
    },
    "b52": {
        "urls": [
            "https://api.wsmt8g.cc/v2/history/getLastResult?gameId=ktrng_3996&size=100&tableId=39961215743193&curPage=1",
            "https://b52-qiw2.onrender.com/api/history",
        ],
        "period_keys": ["gameNum","sid","session","phien","Phien","id","issue","round","current_session"],
        "total_keys": ["score","total","tong","Tong","sum","diem"],
        "dice_keys": ["dice","xuc_xac","xucxac","xx","dices","facesList","keyR"],
        "predict_keys": ["du_doan","prediction","Prediction","predict","result","ket_qua","taixiu","tai_xiu"],
        "confidence_keys": ["do_tin_cay","confidence","Độ Tin Cậy","ti_le","rate","percent"],
    },
    "sicb52": {
        "type":"sicbo",
        "urls": [
            "https://api.wsmt8g.cc/v2/history/getLastResult?gameId=ktrng_3996&size=100&tableId=39961215743193&curPage=1"
        ],
        "period_keys": ["gameNum","sid","session","phien","Phien","id","issue","round","current_session"],
        "total_keys": ["score","total","tong","Tong","sum","diem"],
        "dice_keys": ["facesList","keyR","dice","xuc_xac","xucxac","xx","dices"],
        "predict_keys": ["result","du_doan","prediction","Prediction","predict","ket_qua","taixiu","tai_xiu"],
        "confidence_keys": ["do_tin_cay","confidence","Độ Tin Cậy","ti_le","rate","percent"],
    },
    "sichit": {
        "type":"sicbo",
        "urls": [
            "https://api.wsmt8g.cc/v2/history/getLastResult?gameId=ktrng_3932&size=120&tableId=39321215743193&curPage=1"
        ],
        "period_keys": ["gameNum","sid","session","phien","Phien","id","issue","round","current_session"],
        "total_keys": ["score","total","tong","Tong","sum","diem"],
        "dice_keys": ["facesList","keyR","dice","xuc_xac","xucxac","xx","dices"],
        "predict_keys": ["result","du_doan","prediction","Prediction","predict","ket_qua","taixiu","tai_xiu"],
        "confidence_keys": ["do_tin_cay","confidence","Độ Tin Cậy","ti_le","rate","percent"],
    },
    "bcr": {
        "type":"baccarat",
        "urls": [
            "https://aibcr.me/api/latest",
            "https://aibcr.me/api/baccarat"
        ],
        "period_keys": ["round","shoeId","session","phien","id","issue","gameNum","table_id","table","table_name"],
        "total_keys": ["total","score"],
        "dice_keys": [],
        "predict_keys": ["result","prediction","predict","ket_qua","winner","win","goodRoad"],
        "confidence_keys": ["confidence","rate","percent"],
    },
}
_nomd5_cache = {}
_nomd5_health = {}
NOMD5_HEALTH_TTL = 15

def _deep_find_value(obj, keys):
    """Tìm key trong JSON API kể cả JSON lồng nhau."""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] not in (None, ""):
                return obj[k]
        for v in obj.values():
            got = _deep_find_value(v, keys)
            if got not in (None, ""):
                return got
    elif isinstance(obj, list):
        for it in obj:
            got = _deep_find_value(it, keys)
            if got not in (None, ""):
                return got
    return None

def _norm_tx(v):
    t = str(v or "").strip().upper()
    if not t:
        return ""
    t = t.replace("Ì", "I").replace("Ỉ", "I").replace("À", "A")
    if any(x in t for x in ("TAI", "TÀI", "BIG", "T ")) or t in ("T", "1"):
        return "TÀI"
    if any(x in t for x in ("XIU", "XỈU", "SMALL", "X ")) or t in ("X", "0"):
        return "XỈU"
    return str(v).strip()

def _norm_bcr(v):
    t = str(v or "").strip().upper()
    if not t:
        return ""
    if any(x in t for x in ("BANKER", "BANK", "BAC", "BCR", "NHÀ CÁI", "NHA CAI")) or t in ("B", "1"):
        return "BANKER"
    if any(x in t for x in ("PLAYER", "PLAY", "CON", "NHÀ CON", "NHA CON")) or t in ("P", "0"):
        return "PLAYER"
    if any(x in t for x in ("TIE", "DRAW", "HOA", "HÒA")) or t in ("T", "2"):
        return "TIE"
    return ""


def _num_conf(v, default=55):
    try:
        if isinstance(v, str):
            v = v.replace("%", "").replace(",", ".").strip()
        x = float(v)
        if x <= 1:
            x *= 100
        return int(_clamp(round(x), 35, 95))
    except Exception:
        return default


def get_api_urls_for_gate(gate):
    gate = normalize_gate(gate)
    spec = NOMD5_API_MAP.get(gate, {})
    base = list(spec.get("urls") or [])
    custom = []
    try:
        custom = [u.strip() for u in cfg.get("custom_api_urls", {}).get(gate, []) if str(u).strip()]
    except Exception:
        custom = []
    # Custom đặt trước để thay API Baccarat/LC79 dễ hơn trong admin.
    out=[]
    for u in custom + base:
        if u and u not in out:
            out.append(u)
    return out

def is_nomd5_gate_available(gate):
    """Health check nhẹ cho menu API. Cache 90s để không spam API."""
    gate = normalize_gate(gate)
    if gate not in NOMD5_API_MAP:
        return False
    now = time.time()
    h = _nomd5_health.get(gate)
    if h and now - h.get("time", 0) < NOMD5_HEALTH_TTL:
        return bool(h.get("ok"))
    ok, data = _fetch_nomd5_api(gate, health_only=True)
    _nomd5_health[gate] = {"time": now, "ok": bool(ok), "error": str((data or {}).get("error", ""))[:160]}
    return bool(ok)

def nomd5_gate_status_text():
    rows=[]
    for gk, gv in DEFAULT_CONFIG.get("gates", {}).items():
        if not gv.get("nomd5"):
            continue
        ok = is_nomd5_gate_available(gk)
        rows.append(f"{gate_icon(gk)} {gate_name(gk)}: {'🟢 OK' if ok else '🔒 API lỗi/tạm khóa'}")
    return "\n".join(rows)

def _flatten_recent_items(data):
    """Trả về danh sách item lịch sử từ nhiều dạng API khác nhau."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    # wsmt8g/wsktnus8: data.resultList
    for path in (("data","resultList"), ("data","list"), ("data","items"), ("resultList",), ("history",), ("data",), ("results",), ("list",)):
        cur = data
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, list):
            return cur
    # nếu dict có 1 list lớn bên trong
    for v in data.values():
        if isinstance(v, list) and v:
            return v
        if isinstance(v, dict):
            got = _flatten_recent_items(v)
            if got:
                return got
    return []

def _tx_from_total(total):
    try:
        t = int(float(str(total).replace(",", ".").strip()))
    except Exception:
        return ""
    if 3 <= t <= 10:
        return "XỈU"
    if 11 <= t <= 18:
        return "TÀI"
    return ""

def _parse_dice_value(v):
    """Đọc dice từ API nếu có: list [1,2,3], string '1-2-3', hoặc object."""
    if v in (None, ""):
        return None
    if isinstance(v, (list, tuple)) and len(v) >= 3:
        out=[]
        for x in v[:3]:
            try: out.append(int(float(str(x))))
            except Exception: return None
        if all(1 <= x <= 6 for x in out):
            return out
    if isinstance(v, dict):
        vals=[]
        for k in ("d1","d2","d3","dice1","dice2","dice3","x1","x2","x3"):
            if k in v:
                try: vals.append(int(float(str(v[k]))))
                except Exception: pass
        if len(vals) >= 3 and all(1 <= x <= 6 for x in vals[:3]):
            return vals[:3]
    s = str(v)
    nums = re.findall(r'\d+', s)
    if len(nums) >= 3:
        arr = [int(x) for x in nums[:3]]
        if all(1 <= x <= 6 for x in arr):
            return arr
    return None

def _dice_from_total_seed(total, seed):
    """Tạo bộ số ổn định đúng tổng, dùng khi API chỉ có tổng."""
    try:
        total = int(total)
    except Exception:
        total = None
    rnd = stable_int(seed, "dice-v100", mod=10**9)
    if not total or total < 3 or total > 18:
        return None
    combos = []
    for a in range(1,7):
        for b in range(1,7):
            for c in range(1,7):
                if a+b+c == total:
                    combos.append((a,b,c))
    if not combos:
        return None
    return list(combos[rnd % len(combos)])

def _next_period_value(period):
    """API dự đoán phiên kế tiếp: API thường trả phiên vừa chốt nên cần +1."""
    raw = str(period or "").strip()
    nums = re.findall(r"\d+", raw)
    if not nums:
        return raw or "ĐANG-CẬP-NHẬT"
    last = nums[-1]
    nxt = str(int(last) + 1)
    return raw[:raw.rfind(last)] + nxt + raw[raw.rfind(last)+len(last):]



def _bcr_result_seq_to_bits(v):
    """Đọc chuỗi Baccarat kiểu sexy.js: PBPBBT... -> history bits cũ->mới, bỏ Hòa để cầu không nhiễu."""
    if v in (None, ""):
        return []
    if isinstance(v, (list, tuple)):
        raw = "".join(str(x) for x in v)
    else:
        raw = str(v)
    bits=[]
    tokens = re.findall(r"BANKER|PLAYER|TIE|B|P|T|CÁI|CAI|CON|HÒA|HOA", raw.upper())
    if not tokens and len(raw) <= 300:
        tokens = list(raw.upper())
    for t in tokens:
        if t in ("B", "BANKER", "CÁI", "CAI"):
            bits.append(1)
        elif t in ("P", "PLAYER", "CON"):
            bits.append(0)
        # TIE/Hòa bỏ qua vì không tạo nhịp cầu Banker/Player
    return bits[-500:]

def _extract_baccarat_table_payload(candidates):
    """Hỗ trợ API sexy.js: /api/baccarat trả nhiều bàn {table,result:'PBPB...'} hoặc /api/baccarat/:table."""
    best = None
    best_bits = []
    for item in candidates[:120]:
        if not isinstance(item, dict):
            continue
        seq = item.get('result') or item.get('goodRoad') or item.get('road') or item.get('history')
        bits = _bcr_result_seq_to_bits(seq)
        if len(bits) > len(best_bits):
            best, best_bits = item, bits
    if not best or not best_bits:
        return None
    table = best.get('table') or best.get('table_name') or best.get('table_id') or 'BCR'
    period = f"{table}-{len(best_bits)}"
    latest_side = 'BANKER' if best_bits[-1] == 1 else 'PLAYER'
    return {
        'period': period,
        'total': None,
        'dice': None,
        'prediction': latest_side,
        'confidence': 60,
        'latest': best,
        'history_bits': best_bits[-120:],
        'history_items': [],
        'next_period': f"{table}-{len(best_bits)+1}",
        'table': str(table),
    }

def _extract_one_nomd5_item(item, spec):
    if not isinstance(item, (dict, list)):
        return None
    period = _deep_find_value(item, spec["period_keys"])
    total = _deep_find_value(item, spec.get("total_keys", []))
    dice = _parse_dice_value(_deep_find_value(item, spec.get("dice_keys", [])))
    pred = _deep_find_value(item, spec["predict_keys"])
    conf = _deep_find_value(item, spec["confidence_keys"])
    if dice and total in (None, ""):
        total = sum(dice)
    if spec.get("type") == "baccarat":
        result = _norm_bcr(pred)
    else:
        result = _norm_tx(pred) or _tx_from_total(total)
    try:
        total_i = int(float(total)) if total not in (None, "") else (sum(dice) if dice else None)
    except Exception:
        total_i = sum(dice) if dice else None
    if not period:
        return None
    return {
        "period": str(period),
        "total": total_i,
        "dice": dice,
        "prediction": result,
        "confidence": _num_conf(conf, 55),
        "latest": item,
    }


def _extract_nomd5_payload(data, spec):
    """Chuẩn hóa JSON API thành latest_finished + history. Không dùng phiên đã chốt làm dự đoán hiện tại."""
    items = _flatten_recent_items(data)
    candidates = items if items else ([data] if isinstance(data, dict) else [])
    if spec.get("type") == "baccarat":
        sexy_payload = _extract_baccarat_table_payload(candidates)
        if sexy_payload:
            return sexy_payload
    parsed=[]
    for item in candidates[:80]:
        one = _extract_one_nomd5_item(item, spec)
        if one and one.get("period"):
            parsed.append(one)
    if not parsed:
        return None

    # Chọn phiên mới nhất theo số lớn nhất nếu có; tránh API trả list sort ngược làm chậm 1 phiên.
    def period_num(x):
        nums = re.findall(r"\d+", str(x.get("period", "")))
        return int(nums[-1]) if nums else -1
    parsed.sort(key=period_num, reverse=True)
    latest = parsed[0]
    history_bits=[]
    for it in parsed:
        if spec.get("type") == "baccarat":
            r = _norm_bcr(it.get("prediction"))
            if r == "BANKER": history_bits.append(1)
            elif r == "PLAYER": history_bits.append(0)
        else:
            r = _norm_tx(it.get("prediction")) or _tx_from_total(it.get("total"))
            if r == "TÀI": history_bits.append(1)
            elif r == "XỈU": history_bits.append(0)
    latest["history_bits"] = history_bits[:60]
    latest["history_items"] = parsed[:60]
    latest["next_period"] = _next_period_value(latest.get("period"))
    return latest

def _fetch_nomd5_api(gate, health_only=False):
    gate = normalize_gate(gate)
    spec = NOMD5_API_MAP.get(gate)
    if not spec:
        return False, {"error": "Cổng chưa có API API"}
    ttl = 0.8
    now = time.time()
    ck = _nomd5_cache.get(gate)
    if ck and now - ck.get("time", 0) < ttl:
        return True, ck["data"]
    urls = get_api_urls_for_gate(gate) or (spec.get("urls") or ([spec.get("url")] if spec.get("url") else []))
    errors=[]
    headers={
        "User-Agent":"Mozilla/5.0 KingBot-API/V100 RealAPI",
        "Accept":"application/json,text/plain,*/*",
        "Connection":"close",
        "Cache-Control":"no-cache"
    }
    for url in urls:
        if not url:
            continue
        try:
            r = requests.get(url, headers=headers, timeout=(4, 9))
            if r.status_code != 200:
                errors.append(f"{url} -> HTTP {r.status_code}")
                continue
            body = r.text.strip()
            try:
                data = r.json()
            except Exception:
                try:
                    data = json.loads(body)
                except Exception:
                    errors.append(f"{url} -> không phải JSON")
                    continue
            payload = _extract_nomd5_payload(data, spec)
            if not payload or not payload.get("period"):
                errors.append(f"{url} -> thiếu phiên")
                continue
            payload["raw"] = data
            payload["source_url"] = url
            _nomd5_cache[gate] = {"time": now, "data": payload}
            _nomd5_health[gate] = {"time": now, "ok": True, "error": ""}
            return True, payload
        except Exception as e:
            errors.append(f"{url} -> {type(e).__name__}: {str(e)[:80]}")
    err = " | ".join(errors[-3:]) if errors else "Không có URL API"
    _nomd5_health[gate] = {"time": now, "ok": False, "error": err[:180]}
    return False, {"error": err[:240]}


def _as_old_to_new(bits):
    """Chuẩn hóa history thành cũ -> mới, bỏ giá trị rác."""
    out=[]
    if not bits:
        return out
    for x in bits:
        if x in (1, True, "1", "T", "TAI", "TÀI", "BIG", "B"):
            out.append(1)
        elif x in (0, False, "0", "X", "XIU", "XỈU", "SMALL", "S"):
            out.append(0)
    return out[-600:]

# Bộ cầu dùng cho API/no-MD5: nhiều dạng hơn, tính theo lịch sử thật cũ -> mới.
API_PATTERN_BANK = [
    ("Bệt", [1,1,1,1], 1.18), ("Bệt X", [0,0,0,0], 1.18),
    ("Đảo 1-1", [1,0,1,0,1,0], 1.28), ("Đảo 2 nhịp", [1,1,0,0,1,1,0,0], 1.20),
    ("Cầu 2-1", [1,1,0,1,1,0], 1.15), ("Cầu 1-2", [1,0,0,1,0,0], 1.15),
    ("Cầu 3-1", [1,1,1,0,1,1,1,0], 1.12), ("Cầu 1-3", [1,0,0,0,1,0,0,0], 1.12),
    ("Cầu 3-2", [1,1,1,0,0,1,1,1,0,0], 1.10), ("Cầu 2-3", [1,1,0,0,0,1,1,0,0,0], 1.10),
    ("Cầu 4-1", [1,1,1,1,0,1,1,1,1,0], 1.08), ("Cầu 1-4", [1,0,0,0,0,1,0,0,0,0], 1.08),
    ("Sandwich T", [1,0,1,1,0,1], 1.08), ("Sandwich X", [0,1,0,0,1,0], 1.08),
    ("Sóng", [1,0,1,0,0,1,0,1], 1.06), ("Ngầm 3-3", [1,1,1,0,0,0,1,1,1,0,0,0], 1.12),
    ("Ngầm 2-2", [1,1,0,0,1,1,0,0,1,1,0,0], 1.10),
    ("Lăn", [1,1,0,1,0,1,1,0,1,0], 1.05), ("Lăn X", [0,0,1,0,1,0,0,1,0,1], 1.05),
    ("Cầu 2-1 nối", [1,1,0,1,1,0,1,1,0], 1.08), ("Cầu 3-1 nối", [1,1,1,0,1,1,1,0], 1.07),
    ("Xoay 4-2", [1,1,1,1,0,0,1,1,1,1,0,0], 1.03), ("Xoay 2-4", [1,1,0,0,0,0,1,1,0,0,0,0], 1.03),
    ("Chéo", [1,0,1,0,0,1,0,1,0,0], 1.02), ("Chéo X", [0,1,0,1,1,0,1,0,1,1], 1.02),
    ("Tam đoạn", [1,1,1,0,1,1,0,0,1,0,0,0], 1.07),
    ("Cầu hồi 5", [1,1,1,1,0,1,1,1,1,0], 1.08),
    ("Cầu hồi X5", [0,0,0,0,1,0,0,0,0,1], 1.08),
    ("Cầu 5-1", [1,1,1,1,1,0,1,1,1,1,1,0], 1.06),
    ("Cầu 1-5", [1,0,0,0,0,0,1,0,0,0,0,0], 1.06),
    ("Cầu 4-2", [1,1,1,1,0,0,1,1,1,1,0,0], 1.05),
    ("Cầu 2-4", [1,1,0,0,0,0,1,1,0,0,0,0], 1.05),
    ("SicBo đảo sâu", [1,0,0,1,0,1,1,0,0,1], 1.09),
    ("SicBo bẻ kép", [1,1,0,1,0,0,1,1,0,1,0,0], 1.10),
    ("Baccarat Banker", [1,1,0,1,1,1,0,1], 1.10),
    ("Baccarat Player", [0,0,1,0,0,0,1,0], 1.10),
    ("Cầu 6-1", [1,1,1,1,1,1,0,1,1,1,1,1,1,0], 1.07),
    ("Cầu 1-6", [1,0,0,0,0,0,0,1,0,0,0,0,0,0], 1.07),
    ("Cầu 5-2", [1,1,1,1,1,0,0,1,1,1,1,1,0,0], 1.08),
    ("Cầu 2-5", [1,1,0,0,0,0,0,1,1,0,0,0,0,0], 1.08),
    ("Cầu móc câu", [1,1,0,1,0,0,1,0,1,1,0,1], 1.09),
    ("Cầu bậc thang", [1,0,1,1,0,1,1,1,0,1,1,1,1,0], 1.10),
    ("Cầu hồi đảo", [1,0,1,0,1,1,0,1,0,1,1,1], 1.08),
    ("Cầu kép lệch", [1,1,0,1,0,0,1,1,0,1,0,0], 1.11),
    ("Cầu pingpong", [1,0,0,1,1,0,0,1,1,0,0,1], 1.09),
    ("Cầu rút đuôi", [1,1,1,0,1,1,0,1,0,0], 1.06),
    ("Cầu rồng", [1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,0], 1.06),
    ("Cầu rồng X", [0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1], 1.06),
    ("Cầu đảo kép sâu", [1,0,0,1,1,0,0,1,1,0,0,1], 1.13),
    ("Cầu sóng đôi", [1,0,1,0,1,1,0,1,0,1,1,0], 1.11),
    ("Cầu nén", [1,1,0,1,0,1,0,0,1,1,0,1,0,1,0,0], 1.08),
]

# Sinh tự động full cầu A-B từ 1-1 đến 8-8, cả 2 chiều T/X, để bắt đúng kiểu 1-1, 1-2, 2-2, 1-3...
def _make_run_pattern(a, b, start=1, repeat=4):
    other = 0 if start else 1
    return ([start] * a + [other] * b) * repeat
for _a in range(1, 9):
    for _b in range(1, 9):
        _w = 1.18 if (_a, _b) in ((1,1),(1,2),(2,1),(2,2),(1,3),(3,1)) else 1.05
        API_PATTERN_BANK.append((f"Cầu {_a}-{_b}", _make_run_pattern(_a, _b, 1, 4), _w))
        API_PATTERN_BANK.append((f"Cầu {_a}-{_b} X", _make_run_pattern(_a, _b, 0, 4), _w))
# Cầu tam đoạn hay gặp: 1-2-1, 2-1-2, 1-3-2, 2-3-1...
for _runs3 in ((1,2,1),(2,1,2),(1,3,1),(3,1,3),(1,3,2),(2,3,1),(3,2,1),(1,2,3),(2,2,1),(1,2,2)):
    _pat=[]; _cur=1
    for _n in _runs3*3:
        _pat += [_cur]*_n; _cur = 0 if _cur else 1
    API_PATTERN_BANK.append(("Cầu " + "-".join(map(str,_runs3)), _pat, 1.07))



def _run_cycle_vote(seq):
    """Tự học chu kỳ độ dài cầu kiểu 1-1, 1-2, 2-2, 1-3... từ run-length gần nhất."""
    seq = _as_old_to_new(seq)
    if len(seq) < 10:
        return None, 0.0, ""
    runs = _runs(seq)
    if len(runs) < 5:
        return None, 0.0, ""
    vals = [r[0] for r in runs]
    lens = [r[1] for r in runs]
    last_side = vals[-1]
    last_len = lens[-1]
    # thử cycle độ dài 2..5 run, ưu tiên pattern khớp nhiều lần nhất ở đuôi
    best = (None, 0.0, "")
    for cyc in range(2, min(5, len(lens)//2) + 1):
        tail = lens[-cyc:]
        # so khớp độ dài tương đối, cho phép lệch 1 ở run cuối vì đang chạy dở
        checks = min(5, len(lens)//cyc)
        if checks < 2:
            continue
        ok = 0; total = 0
        for j in range(1, checks):
            block = lens[-cyc*(j+1):-cyc*j]
            if len(block) != cyc:
                continue
            for idx, (a,b) in enumerate(zip(block, tail)):
                total += 1
                tol = 1 if idx == cyc-1 else 0
                if abs(a-b) <= tol:
                    ok += 1
        ratio = ok / max(1, total)
        if ratio < 0.62:
            continue
        expected_current = max(1, tail[-1])
        if last_len < expected_current:
            bit = last_side
            name = "Cầu giữ nhịp " + "-".join(map(str, tail))
        else:
            bit = 0 if last_side else 1
            name = "Cầu bẻ nhịp " + "-".join(map(str, tail))
        strength = min(0.86, 0.35 + ratio*0.45 + min(0.08, checks/80))
        if strength > best[1]:
            best = (bit, strength, name)
    return best

def _tail_backtest_rate(seq, max_checks=40):
    """Ước lượng % thực chiến từ history gần nhất: dùng Markov + pattern đơn giản để backtest các ván đã biết."""
    seq = _as_old_to_new(seq)
    if len(seq) < 18:
        return None, 0
    start = max(8, len(seq) - max_checks)
    hit = 0; total = 0
    for i in range(start, len(seq)):
        train = seq[:i]
        mv, ms = _nomd5_markov_vote(train)
        pv, ps = _nomd5_pattern_vote(train)
        cv, cs, _ = _run_cycle_vote(train)
        score = 0.0
        if mv:
            score += mv * (0.42 + ms)
        if pv:
            score += pv * (0.45 + ps)
        if cv is not None:
            score += (1 if cv else -1) * (0.40 + cs)
        if abs(score) < 0.08:
            continue
        pred = 1 if score >= 0 else 0
        hit += 1 if pred == seq[i] else 0
        total += 1
    if total < 8:
        return None, total
    return hit / total, total

def _nomd5_markov_vote(bits):
    """Markov đa bậc 1..6 trên history cũ -> mới. Trả vote -1/0/1 và độ mạnh 0..1."""
    seq = _as_old_to_new(bits)
    if len(seq) < 8:
        return 0, 0.0
    scores=[]
    max_order = min(6, len(seq)-2)
    for k in range(max_order, 0, -1):
        cur=tuple(seq[-k:])
        nxt=[]
        for i in range(0, len(seq)-k):
            if tuple(seq[i:i+k]) == cur:
                nxt.append(seq[i+k])
        if not nxt:
            continue
        p_t=(sum(nxt)+1)/(len(nxt)+2)
        strength=min(1.0, len(nxt)/18.0) * abs(p_t-0.5)*2
        weight=1.0 + k*0.18
        scores.append(((1 if p_t>=0.5 else -1), strength, weight))
        if len(nxt) >= 4 and strength > 0.18:
            break
    if not scores:
        return 0, 0.0
    score=sum(v*s*w for v,s,w in scores)
    den=sum(w for _,_,w in scores)
    return (1 if score >= 0 else -1), min(1.0, abs(score)/max(0.001, den))

def _pattern_predict_from_tail(seq, pat):
    """So khớp tail với pattern xoay vòng, trả bit kế tiếp + ratio."""
    if not seq or not pat:
        return None, 0.0
    m=len(pat)
    L=min(len(seq), max(m, min(m*3, 36)))
    tail=seq[-L:]
    best=(None, -1)
    for off in range(m):
        ok=sum(1 for i,x in enumerate(tail) if x == pat[(i+off)%m])
        if ok > best[1]:
            nxt=pat[(L+off)%m]
            best=(nxt, ok)
    return best[0], best[1]/max(1,L)

def _nomd5_pattern_vote(bits):
    """Bắt nhiều cầu: bệt, bẻ, đảo, 2-1/1-2, 3-2, 4-1, ngầm, lăn, răng cưa."""
    seq = _as_old_to_new(bits)
    if len(seq) < 5:
        return 0, 0.0
    votes=[]
    runs = _runs(seq)
    last = seq[-1]
    last_run = runs[-1][1] if runs else 1
    # Bệt và bẻ cầu: không flip bừa, dùng ngưỡng theo độ dài.
    if last_run >= 7:
        votes.append((-1 if last else 1, 0.72, 1.35, "Bẻ bệt dài"))
    elif last_run >= 5:
        votes.append((-1 if last else 1, 0.56, 1.10, "Cảnh báo bẻ"))
    elif last_run >= 3:
        votes.append((1 if last else -1, 0.48, 0.90, "Theo bệt"))
    # Đảo liên tục.
    if len(seq) >= 7:
        alt=sum(1 for i in range(1, min(8, len(seq))) if seq[-i] != seq[-i-1])
        if alt >= 6:
            votes.append((-1 if last else 1, 0.78, 1.45, "Đảo 1-1"))
    # Pattern bank.
    for name, pat, w in API_PATTERN_BANK:
        bit, ratio = _pattern_predict_from_tail(seq, pat)
        if bit is None:
            continue
        if ratio >= 0.66:
            votes.append((1 if bit else -1, (ratio-0.48)*1.95, w, name))
    # Tự học cycle độ dài cầu: 1-1, 1-2, 2-2, 1-3, 3-1... không cần đặt tên cứng.
    cbit, cst, cname = _run_cycle_vote(seq)
    if cbit is not None and cst >= 0.48:
        votes.append((1 if cbit else -1, cst, 1.32, cname))
    # Auto discovery: tự tìm đoạn tail từng lặp trong history.
    for L in range(2, min(18, len(seq)//2)+1):
        tail=seq[-L:]
        hits=[]
        for i in range(0, len(seq)-L):
            if seq[i:i+L] == tail and i+L < len(seq):
                hits.append(seq[i+L])
        if len(hits) >= 2:
            p_t=(sum(hits)+1)/(len(hits)+2)
            strength=min(1.0, len(hits)/10.0)*abs(p_t-0.5)*2
            if strength > 0.08:
                votes.append((1 if p_t>=0.5 else -1, strength, 1.0+L/20, f"Auto {L}"))
    if not votes:
        return 0, 0.0
    score=sum(v*st*w for v,st,w,_ in votes)
    den=sum(st*w for _,st,w,_ in votes)
    if den <= 0:
        return 0, 0.0
    return (1 if score >= 0 else -1), min(1.0, abs(score)/den)




def pct_text(v):
    try:
        if isinstance(v, str) and v.strip().endswith('%'):
            return v.strip()
        f=float(v)
        if f <= 1:
            f *= 100
        if abs(f-round(f)) < 0.05:
            return f"{int(round(f))}%"
        return f"{f:.1f}%"
    except Exception:
        return str(v or "0%")
def _live_streak_key(user_id=None, gate=None, plan=None):
    return f"{user_id or 'global'}:{normalize_gate(gate or '')}:{plan or ''}"

def reset_live_streak(user_id=None, gate=None, plan=None):
    """Reset chuỗi phiên live khi user bấm /start hoặc quay lại/menu."""
    db.setdefault("live_streaks", {})
    if user_id is None:
        return
    prefix = f"{user_id}:"
    for k in list(db["live_streaks"].keys()):
        if k.startswith(prefix) and (not gate or f":{normalize_gate(gate)}:" in k):
            db["live_streaks"].pop(k, None)
    save_db()

def update_live_streak(user_id, gate, plan, win):
    """Cộng dồn thắng/thua trong màn live hiện tại. Gãy 1 ván không xóa chuỗi thắng cũ."""
    db.setdefault("live_streaks", {})
    k = _live_streak_key(user_id, gate, plan)
    st = db["live_streaks"].setdefault(k, {"win": 0, "lose": 0, "total": 0, "started": now_str()})
    if win:
        st["win"] = int(st.get("win", 0)) + 1
    else:
        st["lose"] = int(st.get("lose", 0)) + 1
    st["total"] = int(st.get("total", 0)) + 1
    st["updated"] = now_str()
    return st

def current_streak_text(gate=None, plan=None, user_id=None):
    """Hiển thị chuỗi live cộng dồn: chỉ reset khi /start hoặc bấm quay lại/menu."""
    if user_id is not None:
        st = db.setdefault("live_streaks", {}).get(_live_streak_key(user_id, gate, plan))
        if st:
            total = int(st.get("total", 0) or 0)
            wins = int(st.get("win", 0) or 0)
            loses = int(st.get("lose", 0) or 0)
            rate = int(round(wins * 100 / total)) if total else 0
            return f"🔥 Chuỗi thắng: <b>{wins}</b> · ❄️ Chuỗi thua: <b>{loses}</b> · 📈 Tỉ lệ live: <b>{rate}%</b>"
    arr = list(db.get("prediction_checks", []))[-500:]
    if gate:
        arr = [x for x in arr if str(x.get("gate")) == str(gate)]
    if plan:
        arr = [x for x in arr if str(x.get("plan")) == str(plan)]
    if user_id:
        arr = [x for x in arr if str(x.get("user_id")) == str(user_id)]
    total = len(arr)
    wins = sum(1 for x in arr if x.get("win"))
    loses = total - wins
    rate = int(round(wins * 100 / total)) if total else 0
    return f"🔥 Chuỗi thắng: <b>{wins}</b> · ❄️ Chuỗi thua: <b>{loses}</b> · 📈 Tỉ lệ: <b>{rate}%</b>"

def detect_bridge_type(seq, gate=None, predicted=None):
    """Nhận diện loại cầu chính từ history cũ -> mới để hiển thị cho user."""
    seq = _as_old_to_new(seq)[-80:]
    if not seq:
        return "Chưa đủ lịch sử"
    runs = _runs(seq)
    last = seq[-1]
    last_run = runs[-1][1] if runs else 1
    # Baccarat dùng tên cầu riêng.
    if gate == "bcr":
        if last_run >= 4:
            return "Cầu bệt Banker" if last == 1 else "Cầu bệt Player"
        if len(seq) >= 8 and all(seq[-i] != seq[-i-1] for i in range(1, min(7, len(seq)))):
            return "Cầu Ping Pong"
        if len(seq) >= 8:
            tail = ''.join('B' if x else 'P' for x in seq[-8:])
            if tail.endswith('BBPBB') or tail.endswith('PPBPP'):
                return "Cầu 2-1 Baccarat"
        return "Big Road / Bead Plate"
    if last_run >= 6:
        return "Cầu bẻ bệt dài" if predicted is not None and ((predicted == "TÀI") != bool(last)) else "Cầu bệt dài"
    if last_run >= 3:
        return "Cầu bệt"
    if len(seq) >= 8 and all(seq[-i] != seq[-i-1] for i in range(1, min(8, len(seq)))):
        return "Cầu đảo 1-1"
    patterns = [
        ("Cầu 1-1", [1,0,1,0,1,0,1,0]), ("Cầu 2-2", [1,1,0,0,1,1,0,0]),
        ("Cầu 1-2", [1,0,0,1,0,0]), ("Cầu 2-1", [1,1,0,1,1,0]),
        ("Cầu 1-3", [1,0,0,0,1,0,0,0]), ("Cầu 3-1", [1,1,1,0,1,1,1,0]),
        ("Cầu 3-2", [1,1,1,0,0,1,1,1,0,0]), ("Cầu 2-3", [1,1,0,0,0,1,1,0,0,0]),
        ("Cầu 4-1", [1,1,1,1,0,1,1,1,1,0]), ("Cầu 1-4", [1,0,0,0,0,1,0,0,0,0]),
        ("Cầu 5-1", [1,1,1,1,1,0,1,1,1,1,1,0]), ("Cầu 1-5", [1,0,0,0,0,0,1,0,0,0,0,0]),
        ("Cầu lăn 2-1", [1,1,0,1,0,1,1,0,1,0]), ("Cầu ngầm 3-3", [1,1,1,0,0,0,1,1,1,0,0,0]),
        ("Cầu hồi", [1,1,1,1,0,1,1,1,1,0]), ("Cầu móc câu", [1,1,0,1,0,0,1,0,1,1,0,1]),
    ]
    best_name, best_score = "Đa cầu tổng hợp", 0.0
    for name, pat in patterns:
        _, score = _pattern_predict_from_tail(seq, pat)
        if score > best_score:
            best_name, best_score = name, score
    if best_score >= 0.68:
        return best_name
    return "Cầu hỗn hợp / chưa sạch"

def _baccarat_side_vote(hb_old):
    """Dự đoán Tay Cái/Tay Con theo Big Road: bệt, ping-pong, 2-1, 1-2, Markov."""
    seq = _as_old_to_new(hb_old)[-120:]
    if len(seq) < 6:
        return "", 0.0
    votes=[]
    runs=_runs(seq); last=seq[-1]; last_run=runs[-1][1] if runs else 1
    if last_run >= 5:
        votes.append(((0 if last else 1), 0.72, 1.25, "bẻ bệt baccarat"))
    elif last_run >= 3:
        votes.append((last, 0.55, 1.05, "theo bệt baccarat"))
    if len(seq) >= 8:
        alt=sum(1 for i in range(1, min(8,len(seq))) if seq[-i] != seq[-i-1])
        if alt >= 6:
            votes.append((0 if last else 1, 0.82, 1.35, "ping pong"))
    pats=[([1,1,0,1,1,0],1.18),([0,0,1,0,0,1],1.18),([1,0,0,1,0,0],1.16),([0,1,1,0,1,1],1.16),([1,1,1,0,1,1,1,0],1.08),([0,0,0,1,0,0,0,1],1.08)]
    for pat,w in pats:
        bit,ratio=_pattern_predict_from_tail(seq, pat)
        if bit is not None and ratio >= 0.70:
            votes.append((bit, (ratio-0.5)*1.75, w, "mẫu baccarat"))
    cbit, cst, cname = _run_cycle_vote(seq)
    if cbit is not None and cst >= 0.48:
        votes.append((cbit, cst, 1.35, cname + " baccarat"))
    mv,ms=_nomd5_markov_vote(seq)
    if ms > 0.06:
        votes.append((1 if mv > 0 else 0, ms, 1.20, "markov baccarat"))
    if not votes:
        return ("BANKER" if last else "PLAYER"), 0.52
    score=sum((1 if bit else -1)*st*w for bit,st,w,_ in votes)
    den=sum(st*w for _,st,w,_ in votes) or 1
    return ("BANKER" if score >= 0 else "PLAYER"), min(0.96, abs(score)/den)


def _nomd5_api_consensus(api, gate, level, hb_old):
    """Hội đồng API + Markov + cầu + phiên, ổn định theo phiên."""
    last_period = str(api.get("period") or "ĐANG-CẬP-NHẬT")
    period = str(api.get("next_period") or _next_period_value(last_period))
    seed = f"API-V107|{gate}|{level}|next={period}|last={last_period}|hist={''.join(map(str,hb_old[-220:]))}"
    h = hashlib.sha256(seed.encode()).digest()
    hv = 1 if (h[0] + h[7] + h[19] + h[23]) % 100 >= 50 else -1
    mv, ms = _nomd5_markov_vote(hb_old)
    pv, ps, pname, pdetail = _ultra_pattern_vote(hb_old, gate)
    gate_weight = {"hitclub":0.07, "betvip":0.06, "lc79":0.035, "b52":0.025, "sunwin":0.025, "sicb52":0.04, "sichit":0.045, "bcr":0.045}.get(gate,0.0)
    level_boost = {"free":-0.03, "basic":0.00, "pro":0.04}.get(level,0.0)
    # Phiên số cũng tham gia nhẹ để không bị phụ thuộc hoàn toàn history.
    pnum = 0
    try:
        m = re.findall(r"\d+", period)
        pnum = int(m[-1]) if m else 0
    except Exception:
        pnum = 0
    phase = 1 if ((pnum + h[3]*3 + h[11]) % 100) >= 50 else -1
    score = hv*0.16 + mv*(0.44+ms*0.48) + pv*(0.50+ps*0.52) + phase*0.12 + gate_weight + level_boost
    agree = min(1.0, abs(score))
    return ("TÀI" if score >= 0 else "XỈU"), agree, period, last_period, seed, {"markov":ms, "pattern":ps, "hash":hv, "phase":phase}



# ==================== V113 ULTRA ALL-GAME API ENGINE ====================
# Mục tiêu: HitClub/B52/LC79/SunWin/Baccarat dùng chung engine thật theo history,
# tự nhận diện cầu 1-1, 1-2, 2-2 ... 8-8 và trả JSON chuẩn để gắn vào HTML/web.

def _cycle_pattern(a, b, start=1):
    return [start]*a + [1-start]*b

def _auto_run_patterns(max_run=8):
    pats=[]
    for a in range(1, max_run+1):
        for b in range(1, max_run+1):
            name=f"Cầu {a}-{b}"
            # cả 2 chiều T->X và X->T để không lệch cầu.
            base=_cycle_pattern(a,b,1)
            rev=_cycle_pattern(a,b,0)
            weight=1.34 if a<=3 and b<=3 else 1.22 if a<=5 and b<=5 else 1.12
            pats.append((name, base*3, weight))
            pats.append((name, rev*3, weight))
    return pats

ULTRA_RUN_PATTERNS = _auto_run_patterns(8)

GATE_TUNING = {
    'hitclub': {'markov':1.22,'pattern':1.18,'cycle':1.16,'tail':1.08,'cap_pro':83,'cap_basic':75},
    'b52':     {'markov':1.18,'pattern':1.22,'cycle':1.16,'tail':1.10,'cap_pro':83,'cap_basic':75},
    'lc79':    {'markov':1.14,'pattern':1.16,'cycle':1.18,'tail':1.08,'cap_pro':82,'cap_basic':74},
    'sunwin':  {'markov':1.16,'pattern':1.18,'cycle':1.18,'tail':1.10,'cap_pro':82,'cap_basic':74},
    'bcr':     {'markov':1.10,'pattern':1.24,'cycle':1.22,'tail':1.06,'cap_pro':80,'cap_basic':73},
}

def _run_signature(seq, max_tail_runs=8):
    runs=_runs(seq)
    if not runs:
        return "Chưa đủ lịch sử", 0.0, None
    tail=runs[-max_tail_runs:]
    lens=[n for _,n in tail]
    sides=[b for b,_ in tail]
    # Nếu các vế luân phiên và độ dài lặp ABAB -> cầu a-b.
    if len(tail) >= 4 and all(sides[i] != sides[i-1] for i in range(1,len(sides))):
        a=lens[-2]; b=lens[-1]
        pairs=[]
        for i in range(0,len(lens)-1,2):
            pairs.append((lens[i],lens[i+1]))
        recent_pairs=[]
        for i in range(len(lens)-2, -1, -2):
            if i+1 < len(lens): recent_pairs.append((lens[i], lens[i+1]))
        target=(a,b)
        hit=sum(1 for x in recent_pairs[:4] if x==target)
        if 1 <= a <= 8 and 1 <= b <= 8:
            conf=min(0.94, 0.52 + hit*0.12 + min(len(seq),80)/400)
            return f"Cầu {a}-{b}", conf, target
    # Bệt.
    if lens[-1] >= 3:
        return f"Cầu bệt {lens[-1]}", min(0.92, 0.50 + lens[-1]*0.055), (lens[-1],0)
    # Đảo 1-1.
    if len(seq) >= 8 and all(seq[-i] != seq[-i-1] for i in range(1, min(8,len(seq)))):
        return "Cầu 1-1", 0.88, (1,1)
    return "Đa cầu tổng hợp", 0.45, None


def _ultra_pattern_vote(bits, gate=None):
    seq=_as_old_to_new(bits)
    if len(seq) < 5:
        return 0,0.0,"Chưa đủ lịch sử",[]
    gate=normalize_gate(gate or '')
    tune=GATE_TUNING.get(gate, {'markov':1.0,'pattern':1.0,'cycle':1.0,'tail':1.0})
    votes=[]
    detail=[]
    last=seq[-1]
    runs=_runs(seq)
    last_run=runs[-1][1] if runs else 1

    # 1) run-cycle vote: chính xác tên cầu a-b hiện tại.
    cname,cscore,_=_run_signature(seq)
    cbit,cst,auto_name=_run_cycle_vote(seq)
    if cbit is not None and max(cst,cscore) >= 0.42:
        strength=max(cst,cscore)
        votes.append((1 if cbit else -1, strength, 1.38*tune.get('cycle',1), cname if cname!='Đa cầu tổng hợp' else auto_name))
        detail.append((cname if cname!='Đa cầu tổng hợp' else auto_name, strength))

    # 2) bank pattern 1-1 -> 8-8, cả 2 chiều.
    best_pat=(None,0,None)
    for name,pat,w in ULTRA_RUN_PATTERNS:
        bit,ratio=_pattern_predict_from_tail(seq, pat)
        if ratio > best_pat[1]: best_pat=(name,ratio,bit)
        if bit is not None and ratio >= 0.68:
            st=(ratio-0.50)*1.85
            votes.append((1 if bit else -1, st, w*tune.get('pattern',1), name))
    if best_pat[0]:
        detail.append((best_pat[0], best_pat[1]))

    # 3) bệt/bẻ có điều kiện, không tự reset/không bẻ bừa.
    if last_run >= 8:
        votes.append((-1 if last else 1, 0.62, 1.08*tune.get('tail',1), f"Bẻ bệt {last_run}"))
        detail.append((f"Bẻ bệt {last_run}",0.62))
    elif last_run >= 4:
        votes.append((1 if last else -1, 0.50 + min(last_run,7)*0.035, 0.95*tune.get('tail',1), f"Theo bệt {last_run}"))
        detail.append((f"Theo bệt {last_run}",0.55))

    # 4) Markov/tự học đoạn đuôi, mạnh cho HitClub/B52/SunWin.
    mv,ms=_nomd5_markov_vote(seq)
    if ms >= 0.035:
        votes.append((mv, ms, 1.32*tune.get('markov',1), "Markov theo cổng"))
        detail.append(("Markov",ms))

    # 5) lặp đoạn tail trong lịch sử.
    for L in range(2, min(24, len(seq)//2)+1):
        tail=seq[-L:]
        hits=[]
        for i in range(0, len(seq)-L):
            if seq[i:i+L] == tail and i+L < len(seq): hits.append(seq[i+L])
        if len(hits) >= 2:
            p_t=(sum(hits)+1)/(len(hits)+2)
            st=min(1.0, len(hits)/12.0)*abs(p_t-0.5)*2
            if st >= 0.10:
                votes.append((1 if p_t>=0.5 else -1, st, 1.0+min(L,18)/30, f"Tự học L{L}"))

    if not votes:
        return 0,0.0,cname,detail
    score=sum(v*st*w for v,st,w,_ in votes)
    den=sum(st*w for _,st,w,_ in votes) or 1
    side=1 if score >= 0 else -1
    agree=min(1.0, abs(score)/den)
    # tên cầu lấy từ vote cùng chiều mạnh nhất
    same=[(nm,st*w) for v,st,w,nm in votes if v==side]
    if same:
        same.sort(key=lambda x:x[1], reverse=True)
        cname=same[0][0]
    return side,agree,cname,detail[:4]

# Override hàm vote cũ bằng engine mới.
def _nomd5_pattern_vote(bits):
    side,agree,_,_=_ultra_pattern_vote(bits, None)
    return side,agree

# Override hiển thị cầu: luôn trả đúng loại cầu đang bám.
def detect_bridge_type(seq, gate=None, predicted=None):
    seq=_as_old_to_new(seq)[-160:]
    if len(seq) < 5:
        return "Chưa đủ lịch sử"
    gate=normalize_gate(gate or '')
    side,agree,cname,detail=_ultra_pattern_vote(seq, gate)
    if gate == 'bcr':
        cname = cname.replace('Tài','Banker').replace('Xỉu','Player')
        if cname.startswith('Cầu bệt'):
            last = seq[-1]
            cname = f"Cầu bệt {'Banker' if last else 'Player'} {str(cname).split()[-1]}"
        elif cname == 'Cầu 1-1':
            cname = 'Cầu Ping Pong 1-1'
    pct=int(round(max(agree,0)*100))
    if pct >= 42 and cname:
        return f"{cname} · khớp {pct}%"
    return "Đa cầu tổng hợp"


def _api_payload_from_predict(slug, gate, level, p, tool_name=None):
    result=p.get('taixiu')
    gate=normalize_gate(gate)
    label = ({'BANKER':'Tay Cái','PLAYER':'Tay Con','TIE':'Hòa'}.get(str(result).upper(), result) if gate=='bcr' else result)
    return {
        'ok': True,
        'tool': slug,
        'name': tool_name or slug,
        'gate': gate,
        'game': gate_name(gate),
        'level': level,
        'period': p.get('period'),
        'last_period': p.get('last_period'),
        'result': result,
        'prediction': result,
        'side_label': label,
        'confidence': p.get('tx_conf'),
        'percent': p.get('tx_conf'),
        'bridge_type': p.get('bridge_type'),
        'pattern': p.get('bridge_type'),
        'prob_tai': p.get('prob_tai'),
        'prob_xiu': p.get('prob_xiu'),
        'prob_tie': p.get('prob_tie'),
        'dice': p.get('dice'),
        'total': p.get('total'),
        'advice': p.get('advice'),
        'risk': p.get('risk'),
        'backtest_rate': p.get('backtest_rate'),
        'backtest_n': p.get('backtest_n'),
        'streak': re.sub('<[^<]+?>','', str(p.get('streak',''))),
        'engine': 'V113 REAL-AI ALL-GAME',
        'updated_at': now_str()
    }

def predict_nomd5(gate="lc79", level="basic", history=None):
    gate = normalize_gate(gate)
    level = str(level or "basic").lower()
    ok, api = _fetch_nomd5_api(gate)
    external_hb = _as_old_to_new(_history_bits(history))[-500:] if history else []
    if not ok:
        return {
            "engine":"Bản Nâng Cấp New", "game":gate.upper(), "period":"API-LỖI", "taixiu":"ĐANG CHỜ", "tx_conf":0,
            "prob_tai":"0%", "prob_xiu":"0%", "dice":"?-?-?", "total":"?", "chanle":"?", "score":0,
            "trend":"API cổng này đang lỗi", "advice":"⏸️ BỎ QUA", "stake_level":0,
            "risk":"CAO", "risk_emoji":"🔴", "details":["API lỗi", str(api.get("error", ""))[:60]],
            "history_len":len(external_hb), "vote_agree":0, "hash_short":"NO-MD5",
            "advice_reason":"API chưa trả phiên thật, tạm khóa API cho cổng này.", "bridge_type":"API lỗi", "streak": current_streak_text(gate, level)
        }
    # API trả latest first, đổi sang cũ -> mới rồi gộp history thật của bot.
    api_desc = list(api.get("history_bits") or [])
    api_old = list(reversed(api_desc))
    hb = (external_hb + api_old)[-600:]
    latest_actual = ""
    try:
        latest_item = (api.get("history_items") or [{}])[0]
        latest_actual = _norm_bcr(latest_item.get("prediction")) if gate == "bcr" else (_norm_tx(latest_item.get("prediction")) or _tx_from_total(latest_item.get("total")))
    except Exception:
        latest_actual = ""
    result, agreement, period, last_period, seed, meta = _nomd5_api_consensus(api, gate, level, hb)
    if gate == "bcr":
        # Baccarat: BANKER / PLAYER / TIE riêng, không hiện Tài/Xỉu.
        bcr_vote, bcr_strength = _baccarat_side_vote(hb)
        if bcr_vote:
            result = "TÀI" if bcr_vote == "BANKER" else "XỈU"
            agreement = max(agreement, min(0.96, bcr_strength))
        tie_gate = stable_int(seed, "bcr-tie", mod=100)
        if tie_gate < (3 if level == "pro" else 2) and agreement < 0.72:
            result = "TIE"
        else:
            result = "BANKER" if result == "TÀI" else "PLAYER"
    # Dice mô phỏng ổn định theo phiên dự đoán.
    if gate == "bcr":
        total = "-"
        dice_arr = []
    elif result == "TÀI":
        total = 11 + stable_int(seed, "totalT", mod=8)
        dice_arr = _dice_from_total_seed(total, seed) or [4,4,4]
        total = sum(dice_arr)
    else:
        total = 3 + stable_int(seed, "totalX", mod=8)
        dice_arr = _dice_from_total_seed(total, seed) or [2,3,5]
        total = sum(dice_arr)
    guard=0
    while gate != "bcr" and result == "TÀI" and total < 11 and guard < 12:
        idx=guard%3
        if dice_arr[idx] < 6: dice_arr[idx]+=1
        total=sum(dice_arr); guard+=1
    guard=0
    while gate != "bcr" and result == "XỈU" and total > 10 and guard < 12:
        idx=guard%3
        if dice_arr[idx] > 1: dice_arr[idx]-=1
        total=sum(dice_arr); guard+=1
    hist_len=len(api_old)
    # Confidence thực tế: không buff ảo. Ưu tiên backtest trên history gần nhất + đồng thuận hiện tại.
    bt_rate, bt_n = _tail_backtest_rate(hb, 44)
    tune_cap = GATE_TUNING.get(gate, {})
    level_cap={"free":66, "basic":int(tune_cap.get('cap_basic',74)), "pro":int(tune_cap.get('cap_pro',82))}.get(level,74)
    if bt_rate is not None:
        conf = int(round((bt_rate * 100) * 0.72 + (50 + agreement * 26) * 0.28))
        if bt_n < 16:
            conf -= 4
    else:
        conf = int(round(50 + agreement * 22))
    if hist_len < 6:
        conf = min(conf - 10, 58)
    elif hist_len < 15:
        conf = min(conf - 5, 64)
    elif hist_len < 30:
        conf = min(conf - 2, 70)
    conf = int(_clamp(conf, 45 if level=="free" else 48, level_cap))
    prob_tie = ""
    if gate == "bcr":
        tie_pct = 5 if result != "TIE" else max(8, min(18, conf))
        remain = 100 - tie_pct
        if result == "BANKER":
            prob_t = conf
            prob_x = max(1, remain - prob_t)
        elif result == "PLAYER":
            prob_x = conf
            prob_t = max(1, remain - prob_x)
        else:
            prob_t = (remain // 2) + stable_int(seed, "banker", mod=7) - 3
            prob_x = remain - prob_t
        # cân lại tổng 100
        prob_t = int(_clamp(prob_t, 1, 94)); prob_x = int(_clamp(prob_x, 1, 94)); prob_tie = int(_clamp(100-prob_t-prob_x, 3, 20))
        score = round(max(prob_t, prob_x, prob_tie) + stable_int(seed, "score", mod=500)/100, 2)
    elif result == "TÀI":
        prob_t, prob_x = conf, 100-conf
        score = round(prob_t + stable_int(seed, "score", mod=500)/100, 2)
    else:
        prob_x, prob_t = conf, 100-conf
        score = round(prob_x + stable_int(seed, "score", mod=500)/100, 2)
    return {
        "engine":"V113 REAL-AI ALL-GAME", "game":gate.upper(), "period":period, "last_period":last_period, "table": api.get('table'),
        "taixiu":result, "tx_conf":conf,
        "prob_tai":f"{prob_t}%", "prob_xiu":f"{prob_x}%", "prob_tie":(f"{prob_tie}%" if gate == "bcr" else ""), "dice":("-" if gate == "bcr" else "-".join(map(str,dice_arr[:3]))), "total":total,
        "chanle":("-" if gate == "bcr" else ("CHẴN" if isinstance(total,int) and total % 2 == 0 else "LẺ")), "score":score,
        "trend":"API thật + đa cầu Markov/Auto/Pattern", "advice":"✅ NÊN THEO" if conf >= 70 else "⚖️ CÂN NHẮC" if conf >= 58 else "⏸️ BỎ QUA",
        "stake_level":2 if conf >= 70 else 1 if conf >= 58 else 0,
        "risk":"THẤP" if conf >= 66 else "TRUNG BÌNH" if conf >= 56 else "CAO",
        "risk_emoji":"🟢" if conf >= 66 else "🟡" if conf >= 56 else "🔴",
        "details":["API thật", "Markov", "Auto cầu", "Cầu bẻ", gate_name(gate), ("Baccarat" if gate=="bcr" else "SicBo" if gate in ("sicb52","sichit") else "TX")],
        "history_len":hist_len, "vote_agree":round(agreement*10,1), "backtest_rate": (round(bt_rate*100,1) if bt_rate is not None else None), "backtest_n": bt_n, "hash_short":"NO-MD5",
        "advice_reason":"Nên theo khi cầu đẹp, tín hiệu sạch và quản lý vốn hợp lý.",
        "bridge_type": detect_bridge_type(hb, gate, result),
        "streak": current_streak_text(gate, level),
        "level": level,
        "latest_actual": latest_actual
    }

def format_nomd5_reply(gate, p):
    """Reply API gọn + loại cầu + chuỗi thắng/thua."""
    result = str(p.get("taixiu", "")).upper()
    bridge = p.get("bridge_type") or "Đa cầu tổng hợp"
    streak = p.get("streak") or current_streak_text(gate, p.get("level"))
    if gate == "bcr":
        if result == "BANKER":
            line = "👑 Kết luận: <b>🅑 BANKER / TAY CÁI</b>"
        elif result == "PLAYER":
            line = "👤 Kết luận: <b>🅟 PLAYER / TAY CON</b>"
        elif result == "TIE":
            line = "🤝 Kết luận: <b>🅣 TIE / HÒA</b>"
        else:
            line = "⏳ Kết luận: <b>ĐANG CHỜ</b>"
        return (
            f"🃏 <b>DỰ ĐOÁN API BACCARAT</b>\n\n"
            f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
            f"📦 Phiên bản: <b>{p.get('engine','Bản Nâng Cấp New')}</b>\n"
            f"🧾 Phiên: <code>{p.get('period','?')}</code>\n\n"
            f"{line}\n"
            f"🧬 Loại cầu: <b>{bridge}</b>\n"
            f"📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
            f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
            f"🎯 Banker/Player/Tie: B <b>{p.get('prob_tai','0%')}</b> · P <b>{p.get('prob_xiu','0%')}</b> · T <b>{p.get('prob_tie','0%')}</b>\n\n"
            f"{streak}"
        )
    if result == "TÀI":
        line = "📈 Kết luận: <b>🅣 TÀI</b>"
    elif result == "XỈU":
        line = "📉 Kết luận: <b>🅧 XỈU</b>"
    else:
        line = "⏳ Kết luận: <b>ĐANG CHỜ</b>"
    title = "🎯 <b>DỰ ĐOÁN API SICBO</b>" if gate in ("sicb52", "sichit", "sicsun") else "🔮 <b>DỰ ĐOÁN API TÀI/XỈU</b>"
    return (
        f"{title}\n\n"
        f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
        f"📦 Phiên bản: <b>{p.get('engine','Bản Nâng Cấp New')}</b>\n"
        f"🧾 Phiên: <code>{p.get('period','?')}</code>\n\n"
        f"🎲 Bộ số mô phỏng: <b>{p.get('dice','?-?-?')}</b> | Tổng: <b>{p.get('total','?')}</b>\n"
        f"{line}\n"
        f"🧬 Loại cầu: <b>{bridge}</b>\n"
        f"📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
        f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
        f"🎯 Tài/Xỉu %: T <b>{p.get('prob_tai','0%')}</b> · X <b>{p.get('prob_xiu','0%')}</b>\n\n"
        f"{streak}"
    )

def format_md5_reply(gate, p):
    """Reply MD5 gọn đồng bộ với API, thêm mã MD5 hiện tại + loại cầu."""
    result = str(p.get("taixiu", "")).upper()
    if result == "TÀI":
        line = "📈 Kết luận: <b>🅣 TÀI</b>"
    elif result == "XỈU":
        line = "📉 Kết luận: <b>🅧 XỈU</b>"
    else:
        line = "⏳ Kết luận: <b>ĐANG CHỜ</b>"
    bridge = p.get("bridge_type") or p.get("trend") or "Hash đa lớp / cầu tổng hợp"
    return (
        f"🔮 <b>PHÂN TÍCH MD5 TÀI/XỈU</b>\n\n"
        f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
        f"📦 Phiên bản: <b>Bản Nâng Cấp New</b>\n"
        f"📝 MD5 hiện tại: <code>{p.get('hash_short','')}</code>\n\n"
        f"🎲 Bộ số mô phỏng: <b>{p.get('dice','?-?-?')}</b> | Tổng: <b>{p.get('total','?')}</b>\n"
        f"{line}\n"
        f"🧬 Loại cầu: <b>{bridge}</b>\n"
        f"📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
        f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
        f"🎯 Tài/Xỉu %: T <b>{pct_text(p.get('prob_tai','?'))}</b> · X <b>{pct_text(p.get('prob_xiu','?'))}</b>"
    )

_nomd5_live_jobs = {}

def stop_live_message(chat_id, message_id):
    key = f"{chat_id}:{message_id}"
    if key in _nomd5_live_jobs:
        _nomd5_live_jobs[key]["alive"] = False

def start_nomd5_live(bot_obj, chat_id, message_id, uid, gate, plan):
    """Cập nhật cùng 1 tin nhắn mỗi 3s, chạy lâu và không spam tin mới."""
    key = f"{chat_id}:{message_id}"
    _nomd5_live_jobs[key] = {"alive": True, "uid": str(uid), "gate": gate, "plan": plan, "started": time.time()}
    def worker():
        last_text = None
        last_pred = None
        # chạy tối đa 12 giờ/một màn hình; bấm quay lại/menu sẽ thay job khác.
        for _ in range(8640):
            job = _nomd5_live_jobs.get(key)
            if not job or not job.get("alive"):
                break
            try:
                hist = recent_history_for_gate(gate or "", 500)
                p = predict_nomd5(gate, plan, hist)
                # Khi API sang phiên mới, đối chiếu dự đoán phiên trước với kết quả thật mới chốt.
                try:
                    if last_pred and str(p.get("last_period")) == str(last_pred.get("period")):
                        actual = str(p.get("latest_actual") or "").upper()
                        pred = str(last_pred.get("result") or "").upper()
                        if actual and pred and actual in ("TÀI","XỈU","BANKER","PLAYER","TIE"):
                            win = (actual == pred)
                            # V112: KHÔNG cộng chuỗi ngay lúc vừa dò thấy kết quả.
                            # Chỉ khi bot đã hiện thông báo thắng/thua thành công thì mới cộng vào chuỗi.
                            # Nhờ vậy màn live không tự nhảy chuỗi trước khi user thấy thông báo chốt phiên.
                            def _send_result_later(cid, pred_period, predict_result, actual_result, is_win, user_id, gate_key, plan_key):
                                try:
                                    time.sleep(10)
                                    tmp = bot_obj.send_message(
                                        cid,
                                        ("✅ <b>Phiên {}</b> thắng · Dự đoán: <b>{}</b> · KQ: <b>{}</b>" if is_win else "❌ <b>Phiên {}</b> thua · Dự đoán: <b>{}</b> · KQ: <b>{}</b>").format(pred_period, predict_result, actual_result),
                                        parse_mode="HTML"
                                    )
                                    # Chỉ sau khi send_message OK mới chốt lịch sử + cộng chuỗi.
                                    db.setdefault("prediction_checks", []).append({
                                        "user_id": str(user_id), "gate": gate_key, "plan": plan_key,
                                        "period": pred_period, "predict": predict_result, "actual": actual_result,
                                        "win": is_win, "time": now_str()
                                    })
                                    update_live_streak(str(user_id), gate_key, plan_key, is_win)
                                    key_stat=f"{gate_key}:{plan_key}"
                                    st=db.setdefault("api_winloss", {}).setdefault(key_stat, {"win":0,"lose":0})
                                    st["win" if is_win else "lose"] = int(st.get("win" if is_win else "lose",0)) + 1
                                    save_db()
                                    time.sleep(3)
                                    bot_obj.delete_message(cid, tmp.message_id)
                                except Exception as e:
                                    log(f"gửi thông báo thắng/thua lỗi {gate_key}: {e}")
                            threading.Thread(target=_send_result_later, args=(chat_id, last_pred.get("period"), pred, actual, win, uid, gate, plan), daemon=True).start()
                            last_pred = None
                except Exception as e:
                    log(f"check thắng thua lỗi {gate}: {e}")
                p["streak"] = current_streak_text(gate, plan, str(uid))
                text = format_nomd5_reply(gate, p)
                if text != last_text:
                    bot_obj.edit_message_text(text, chat_id, message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Quay lại chọn cổng", callback_data="mode_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home")))
                    last_text = text
                if p.get("period") and p.get("taixiu") not in ("ĐANG CHỜ", ""):
                    last_pred = {"period": p.get("period"), "result": p.get("taixiu")}
            except Exception as e:
                log(f"API live update lỗi {gate}: {e}")
            time.sleep(3)
    t = threading.Thread(target=worker, daemon=True)
    t.start()

def qr_url(amount, note):
    bank_bin = bank_bin_from_name(cfg.get("bank_name_key", cfg.get("bank_bin", "")))
    acc = cfg.get("bank_account", "").strip()
    name = cfg.get("bank_name", "").strip()
    info = urllib.parse.quote(note)
    account_name = urllib.parse.quote(name)
    return f"https://img.vietqr.io/image/{bank_bin}-{acc}-compact2.png?amount={int(amount)}&addInfo={info}&accountName={account_name}"

def notify_group(text):
    gid = normalize_group_target()
    if not gid or not bot:
        log("Chưa có group target hoặc link invite không lấy được chat_id. Hãy dùng @group_username, -100chatid hoặc link public https://t.me/ten_group.")
        return False
    try:
        bot.send_message(gid, text, parse_mode="HTML", disable_web_page_preview=True)
        return True
    except Exception as e:
        log(f"Không gửi được group {gid}: {e}")
        return False

def notify_group_photo(photo_id, caption):
    gid = normalize_group_target()
    if not gid or not bot:
        log("Chưa có group target/link public hoặc bot chưa chạy để gửi feedback.")
        return False
    try:
        bot.send_photo(gid, photo_id, caption=caption, parse_mode="HTML")
        return True
    except Exception as e:
        log(f"Không gửi được feedback vào group {gid}: {e}")
        return False

def notify_admins_deposit(order):
    """Gửi đơn nạp tới các admin Telegram đã add ID."""
    admin_ids = [str(x) for x in cfg.get("admin_ids", []) if str(x).strip()]
    if not admin_ids or not bot:
        return 0
    sent = 0
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Duyệt", callback_data=f"admin_deposit_approve_{order['id']}"),
        InlineKeyboardButton("❌ Từ chối", callback_data=f"admin_deposit_reject_{order['id']}")
    )
    text = (
        f"💰 <b>ĐƠN NẠP MỚI</b>\n\n"
        f"🧾 Mã đơn: <code>{order['id']}</code>\n"
        f"👤 User: <b>{mask_user(order.get('user_id'), order.get('username',''))}</b>\n"
        f"💵 Số tiền: <b>{money(order.get('amount',0))}</b>\n"
        f"📝 Nội dung: <code>{order.get('note','')}</code>\n\n"
        f"Chỉ admin có ID trong web admin mới nhận được thông báo này."
    )
    for aid in admin_ids:
        try:
            bot.send_message(aid, text, parse_mode="HTML", reply_markup=kb)
            sent += 1
            time.sleep(0.03)
        except Exception as e:
            log(f"Không gửi được đơn nạp tới admin {aid}: {e}")
    return sent

def notify_admins_text(text):
    admin_ids = [str(x) for x in cfg.get("admin_ids", []) if str(x).strip()]
    if not admin_ids or not bot:
        return 0
    sent = 0
    for aid in admin_ids:
        try:
            bot.send_message(aid, text, parse_mode="HTML")
            sent += 1
            time.sleep(0.03)
        except Exception as e:
            log(f"Không gửi được tin admin {aid}: {e}")
    return sent

def safe_edit_or_send(b, chat_id, message_id, text, reply_markup=None):
    try:
        b.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup)
    except Exception:
        try:
            b.send_message(chat_id, text, reply_markup=reply_markup)
        except Exception as e:
            log(f"safe_edit_or_send lỗi: {e}")

def kb_home():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎮 Chọn Dự Đoán", callback_data="choose_type"),
        InlineKeyboardButton("💰 Nạp Tiền", callback_data="deposit"),
        InlineKeyboardButton("🛒 Mua Gói", callback_data="buy_tool"),
        InlineKeyboardButton("👤 Tài Khoản", callback_data="account"),
        InlineKeyboardButton("📸 Feedback", callback_data="feedback"),
        InlineKeyboardButton("☎️ Hỗ Trợ", url=cfg.get("support_url", "https://t.me/")),
    )
    return kb

def kb_back():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
    return kb

def home_text(user, username, uid):
    plan_key = user.get("active_plan")
    gate_key = user.get("active_gate")
    plan_label = cfg["plans"].get(plan_key, {}).get("name", "Chưa mua")
    gate_label = gate_name(gate_key) if gate_key else "Chưa chọn"
    return (
        f"👑 <b>{cfg.get('shop_name','KingBot')}</b>\n"
        f"✨ {cfg.get('welcome_text','')}\n\n"
        f"👋 Xin chào, <b>{username}</b>\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"💰 Số dư: <b>{money(user.get('balance',0))}</b>\n"
        f"🎮 Cổng: <b>{gate_icon(gate_key)} {gate_label}</b>\n"
        f"📦 Gói: <b>{plan_label}</b>\n"
        f"⏳ Hạn dùng: <b>{active_until_text(user)}</b>\n"
        f"⌛ Còn lại: <b>{remaining_time_text(user)}</b>\n\n" +
        (f"🎁 Free mode: <b>Đang mở</b> · còn <b>{free_remaining_text()}</b>\n" if free_is_active() else "⚠️ Không có gói miễn phí. Mua gói để phân tích MD5 Tài/Xỉu.")
    )

def legacy_predict_basic(md5_hex: str):
    s = md5_hex.lower().strip()
    if len(s) not in (32, 64):
        return None
    try:
        b = [int(s[i:i+2], 16) for i in range(0, len(s), 2)]
        n = [int(c, 16) for c in s]
    except Exception:
        return None

    xor_all = 0
    for x in b:
        xor_all ^= x

    wave = sum((i + 1) * b[i] for i in range(16)) % 1000
    nib = sum((i + 3) * n[i] for i in range(len(s))) % 1000
    raw = (wave * 17 + nib * 13 + xor_all * 29 + b[0] * 7 + b[15] * 11) % 10000

    score = raw / 100
    result = "TÀI" if score >= 50 else "XỈU"
    confidence = min(78, 50 + int(abs(score - 50) * 0.32))
    d1 = ((b[0] + b[5] + wave) % 6) + 1
    d2 = ((b[7] ^ b[11] ^ xor_all) % 6) + 1
    d3 = ((b[14] + b[2] + nib) % 6) + 1
    total = d1 + d2 + d3

    parity = (raw + total * 31 + xor_all) % 100
    chanle = "CHẴN" if parity >= 50 else "LẺ"
    risk_point = int((statistics.pstdev(b) + abs(sum(b[::2]) - sum(b[1::2])) / 20) % 100)
    risk = "THẤP" if risk_point < 35 else ("TRUNG BÌNH" if risk_point < 70 else "CAO")
    risk_emoji = "🟢" if risk == "THẤP" else ("🟡" if risk == "TRUNG BÌNH" else "🔴")
    return {
        "engine": "BASIC-V4 HASH MATRIX",
        "taixiu": result, "tx_conf": confidence, "chanle": chanle,
        "dice": f"{d1}-{d2}-{d3}", "total": total,
        "risk": risk, "risk_emoji": risk_emoji,
        "score": round(score, 2),
        "hash_short": s[:8].upper() + "..." + s[-6:].upper(),
        "details": ["Byte wave", "Nibble pressure", "XOR entropy", "Mirror seed"]
    }

def legacy_predict_pro(md5_hex: str, gate_key=""):
    s = md5_hex.lower().strip()
    if len(s) not in (32, 64):
        return None
    try:
        b = [int(s[i:i+2], 16) for i in range(0, len(s), 2)]
        n = [int(c, 16) for c in s]
    except Exception:
        return None

    salt = f"KINGBOT|PRO|{gate_key}|{s}|ULTRA"
    sha = hashlib.sha512(salt.encode()).digest()
    sha_b = list(sha[:32])

    xor_all = 0
    rotate = 0
    for i, x in enumerate(b):
        xor_all ^= ((x << (i % 3)) & 255) ^ sha_b[i]

    wave = sum((i + 11) * (b[i] ^ sha_b[i]) for i in range(16)) % 4096
    mirror = sum((17 - i) * ((b[i] + sha_b[15-i]) ^ b[15-i]) for i in range(16)) % 4096
    nibble = sum((i + 7) * (n[i] + (sha_b[i % 32] % 16)) for i in range(len(s))) % 4096
    split_a = sum(b[:8]) * 3 + sum(sha_b[8:16])
    split_b = sum(b[8:]) * 5 + sum(sha_b[16:24])
    chaos = int(abs(split_a - split_b) + statistics.pstdev(b) * 17 + statistics.pstdev(sha_b[:16]) * 9) % 4096

    d1 = ((b[0] + b[5] + sha_b[2] + wave + chaos) % 6) + 1
    d2 = ((b[7] ^ b[11] ^ sha_b[9] ^ mirror ^ xor_all) % 6) + 1
    d3 = ((b[14] + b[3] + sha_b[18] + nibble + split_a) % 6) + 1
    total = d1 + d2 + d3

    raw = (
        wave * 31 + mirror * 23 + nibble * 19 + chaos * 17 +
        xor_all * 29 + total * 37 + split_a * 7 - split_b * 5
    ) % 10000

    score = raw / 100.0
    result = "TÀI" if score >= 50 else "XỈU"
    distance = abs(score - 50)
    confidence = min(86, 54 + int(distance * 0.42) + (chaos % 3))

    parity_score = (raw + total * 47 + xor_all * 13 + sha_b[0] + chaos) % 100
    chanle = "CHẴN" if parity_score >= 50 else "LẺ"

    risk_point = int((chaos / 41 + abs(raw - 5000) / 90 + statistics.pstdev(b)) % 100)
    if risk_point < 34:
        risk, risk_emoji = "THẤP", "🟢"
    elif risk_point < 68:
        risk, risk_emoji = "TRUNG BÌNH", "🟡"
    else:
        risk, risk_emoji = "CAO", "🔴"

    trend = "Cầu nghiêng Tài" if score >= 57 else ("Cầu nghiêng Xỉu" if score <= 43 else "Cầu cân bằng")
    return {
        "engine": "PRO-ULTRA SHA512 CHAOS MATRIX",
        "taixiu": result, "tx_conf": confidence, "chanle": chanle,
        "dice": f"{d1}-{d2}-{d3}", "total": total,
        "risk": risk, "risk_emoji": risk_emoji,
        "score": round(score, 2),
        "hash_short": s[:8].upper() + "..." + s[-6:].upper(),
        "trend": trend,
        "details": ["SHA512 chaos", "Mirror entropy", "Wave pressure", "Gate salt", "XOR rotation"]
    }


def normalize_prediction_result(r, fallback_engine="ADMIN-AI PYTHON"):
    """Chuẩn hóa output thuật toán admin để bot không lỗi dù code trả key khác nhau."""
    if not isinstance(r, dict):
        return None
    taixiu = str(r.get("taixiu") or r.get("result") or r.get("ketqua") or r.get("kq") or "").upper()
    if "TAI" in taixiu: taixiu = "TÀI"
    if "XIU" in taixiu: taixiu = "XỈU"
    if taixiu not in ("TÀI", "XỈU"):
        return None
    try:
        conf = int(float(r.get("tx_conf", r.get("confidence", r.get("conf", 70)))))
    except Exception:
        conf = 70
    conf = max(1, min(99, conf))
    md5_short = r.get("hash_short") or r.get("md5_short") or ""
    dice = r.get("dice") or r.get("bo_so") or r.get("dices") or "1-1-1"
    try:
        total = int(r.get("total") or sum(int(x) for x in str(dice).replace(",","-").split("-") if x.strip().isdigit()))
    except Exception:
        total = 0
    return {
        "engine": str(r.get("engine") or fallback_engine),
        "taixiu": taixiu,
        "tx_conf": conf,
        "chanle": str(r.get("chanle") or r.get("parity") or ("CHẴN" if total % 2 == 0 else "LẺ")),
        "dice": str(dice),
        "total": total,
        "risk": str(r.get("risk") or "TRUNG BÌNH"),
        "risk_emoji": str(r.get("risk_emoji") or "🟡"),
        "score": r.get("score", conf),
        "hash_short": str(md5_short or ""),
        "trend": str(r.get("trend") or "Admin custom"),
        "details": r.get("details") if isinstance(r.get("details"), list) else ["Admin algorithm", "Dynamic code", "HTML config"],
        "advice": str(r.get("advice") or r.get("khuyen_nghi") or "THAM KHẢO"),
        "advice_reason": str(r.get("advice_reason") or r.get("reason") or "Chưa có dữ liệu lịch sử thật để xác thực %"),
        "stake_level": int(r.get("stake_level", 0) or 0),
        "prob_tai": r.get("prob_tai", r.get("tai_percent", "")),
        "prob_xiu": r.get("prob_xiu", r.get("xiu_percent", "")),
        "risk_score": r.get("risk_score", ""),
        "history_quality": r.get("history_quality", ""),
        "history_len": r.get("history_len", ""),
        "vote_agree": r.get("vote_agree", ""),
        "note": str(r.get("note") or "")
    }

def load_admin_algorithm():
    code = str(cfg.get("algorithm_code", "") or "")
    if not cfg.get("algorithm_enabled") or not code.strip():
        algo_cache.update({"hash": None, "ns": {}, "error": ""})
        return None
    h = hashlib.sha256(code.encode("utf-8", "ignore")).hexdigest()
    if algo_cache.get("hash") == h:
        return algo_cache.get("ns")
    ns = {}
    def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        allowed = {"hashlib", "math", "statistics", "collections", "random"}
        root = str(name).split(".")[0]
        if root not in allowed:
            raise ImportError("Module bị chặn để tránh sập Render: " + str(name))
        return __import__(name, globals, locals, fromlist, level)
    safe_builtins = {
        "abs": abs, "min": min, "max": max, "sum": sum, "len": len, "range": range,
        "int": int, "float": float, "str": str, "round": round, "enumerate": enumerate,
        "list": list, "dict": dict, "set": set, "tuple": tuple, "sorted": sorted, "zip": zip,
        "bool": bool, "pow": pow, "isinstance": isinstance, "getattr": getattr, "hasattr": hasattr,
        "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError, "__import__": _safe_import
    }
    from collections import Counter, defaultdict
    forbidden = ("os.", "sys.", "subprocess", "socket", "open(", "eval(", "exec(", "while True", "SystemExit", "KeyboardInterrupt")
    if any(x in code for x in forbidden):
        err = "Thuật toán admin chứa lệnh nguy hiểm/có thể làm sập Render. Đã chặn khi import."
        algo_cache.update({"hash": h, "ns": {}, "error": err})
        log(err)
        return None
    g = {"__builtins__": safe_builtins, "hashlib": hashlib, "statistics": statistics, "random": random, "math": __import__("math"), "Counter": Counter, "defaultdict": defaultdict}
    try:
        compile(code, "<admin_algorithm>", "exec")
        exec(code, g, ns)
        algo_cache.update({"hash": h, "ns": ns, "error": ""})
        return ns
    except BaseException:
        err = traceback.format_exc(limit=3)
        algo_cache.update({"hash": h, "ns": {}, "error": err})
        log("Lỗi thuật toán admin: " + err.replace("\n", " | ")[:500])
        return None

def recent_history_for_gate(gate_key="", limit=500):
    """Lấy lịch sử kết quả thật/đã lưu gần nhất theo cổng để engine có dữ liệu bắt cầu."""
    gate_key = str(gate_key or "").lower().strip()
    out = []
    for item in reversed(db.get("predictions", [])):
        if gate_key and str(item.get("gate", "")).lower().strip() not in ("", gate_key):
            continue
        # CHỐNG LỆCH KẾT QUẢ KHI GỬI CÙNG 1 MD5 NHIỀU LẦN:
        # Chỉ lấy kết quả THẬT do admin/user cập nhật, tuyệt đối không lấy dự đoán cũ làm lịch sử.
        # Bản cũ dùng item["result"] nên mỗi lần gửi MD5 nó tự thêm dự đoán vào history,
        # làm lần 2/lần 3 có thể đổi kết quả.
        r = str(item.get("real") or "").upper()
        if not r:
            continue
        if "T" in r and "X" not in r:
            out.append("T")
        elif "X" in r:
            out.append("X")
        if len(out) >= limit:
            break
    return list(reversed(out))


TIER_MODE_LEVEL = {
    "weak": "free",
    "lite": "free",
    "normal": "basic",
    "strong": "pro",
    "royal": "pro",
}

TIER_MODE_LABEL = {
    "weak": "ĐỂU / LITE",
    "lite": "FREE LITE",
    "normal": "THƯỜNG ỔN",
    "strong": "XỊN",
    "royal": "Bản Nâng Cấp New",
}

def tier_cfg(level="basic"):
    level = str(level or "basic").lower().strip()
    if level not in ("free", "basic", "pro"):
        level = "basic"
    base = {
        "free":  {"mode": "weak",   "use_admin": True, "history_limit": 30,  "max_conf": 68, "penalty": 8, "min_entry": 62},
        "basic": {"mode": "normal", "use_admin": True, "history_limit": 160, "max_conf": 88, "penalty": 2, "min_entry": 58},
        "pro":   {"mode": "royal",  "use_admin": True, "history_limit": 500, "max_conf": 98, "penalty": 0, "min_entry": 54},
    }[level].copy()
    custom = cfg.get("algorithm_tiers", {}).get(level, {}) if isinstance(cfg.get("algorithm_tiers"), dict) else {}
    if isinstance(custom, dict):
        base.update(custom)
    base["mode"] = str(base.get("mode") or "normal").lower().strip()
    if base["mode"] not in TIER_MODE_LEVEL:
        base["mode"] = "normal"
    for k in ("history_limit", "max_conf", "penalty", "min_entry"):
        try: base[k] = int(base.get(k, 0) or 0)
        except Exception: base[k] = 0
    base["use_admin"] = bool(base.get("use_admin", True))
    return base

def effective_level_for_tier(level="basic"):
    tc = tier_cfg(level)
    return TIER_MODE_LEVEL.get(tc.get("mode"), level)

def apply_tier_policy(res, public_level="basic"):
    """Ép chất lượng theo gói: admin có thể cho Free xịn hoặc đểu, Basic/Pro tùy ý."""
    if not isinstance(res, dict):
        return res
    tc = tier_cfg(public_level)
    mode = tc.get("mode", "normal")
    try:
        conf = int(float(res.get("tx_conf", res.get("confidence", 70))))
    except Exception:
        conf = 70
    # weak/lite cố ý giảm confidence để free không ảo; strong/royal giữ gần nguyên.
    conf = conf - max(0, int(tc.get("penalty", 0)))
    max_conf = int(tc.get("max_conf", 99) or 99)
    if max_conf > 0:
        conf = min(conf, max_conf)
    conf = max(1, min(99, conf))
    res["tx_conf"] = conf
    res["tier"] = public_level
    res["tier_mode"] = mode
    res["tier_label"] = TIER_MODE_LABEL.get(mode, mode.upper())
    # Không hiện dòng cũ kiểu: Bản Nâng Cấp New · PRO=SIÊU XỊN / PRO
    res["engine"] = "Bản Nâng Cấp New"
    # Khuyến nghị vào/né kèo theo ngưỡng admin đặt + rủi ro
    risk = str(res.get("risk", "")).upper()
    min_entry = int(tc.get("min_entry", 58) or 58)
    if conf < min_entry or "CAO" in risk:
        advice = "BỎ QUA / KHÔNG NÊN ĐÁNH"
        stake_level = 0
        reason = f"Tin cậy {conf}% dưới ngưỡng {min_entry}% hoặc rủi ro cao."
    elif conf < min_entry + 6:
        advice = "CÓ THỂ ĐI NHỎ"
        stake_level = 1
        reason = f"Kèo vừa đủ ngưỡng, chỉ nên tham khảo/đi nhỏ."
    elif conf < min_entry + 14:
        advice = "CÓ THỂ VÀO"
        stake_level = 2
        reason = f"Đồng thuận thuật toán ổn hơn ngưỡng admin đặt."
    else:
        advice = "KÈO ĐẸP HƠN BÌNH THƯỜNG"
        stake_level = 3
        reason = f"Nhiều lớp đồng thuận, confidence vượt ngưỡng mạnh."
    # Nếu engine custom đã trả advice thì vẫn ưu tiên chặn khi không đạt ngưỡng.
    if not str(res.get("advice", "")).strip() or advice.startswith("BỎ"):
        res["advice"] = advice
    res.setdefault("advice_reason", reason)
    res["entry_threshold"] = min_entry
    res["stake_level"] = int(res.get("stake_level", stake_level) or stake_level)
    # % Tài/Xỉu không giả thắng thật: là xác suất nghiêng nội bộ có cap theo gói.
    try:
        score = float(res.get("score", 50))
    except Exception:
        score = 50.0
    tx = str(res.get("taixiu", "")).upper()
    side_prob = max(50, min(conf, int(50 + abs(score - 50) * 0.65 + (conf - 50) * 0.55)))
    if "T" in tx and "X" not in tx:
        res["prob_tai"] = side_prob
        res["prob_xiu"] = 100 - side_prob
    else:
        res["prob_xiu"] = side_prob
        res["prob_tai"] = 100 - side_prob
    return res

def _call_algo_func(fn, md5_hex, gate_key, level, history):
    """Gọi được nhiều kiểu signature: predict(md5, gate, level, game, history) hoặc bản cũ."""
    tries = [
        lambda: fn(md5_hex, gate_key, level, gate_key, history),
        lambda: fn(md5_hex, gate_key, level, history),
        lambda: fn(md5_hex, gate_key, level),
        lambda: fn(md5_hex, gate_key),
        lambda: fn(md5_hex),
    ]
    for cb in tries:
        try:
            return cb()
        except TypeError:
            continue
    return fn(md5_hex)

def predict_admin(md5_hex: str, gate_key="", level="basic", history=None):
    ns = load_admin_algorithm()
    if not ns:
        return None
    funcs = []
    if level == "free": funcs = ["predict_free", "predict"]
    elif level == "pro": funcs = ["predict_pro", "predict"]
    else: funcs = ["predict_basic", "predict"]
    for name in funcs:
        fn = ns.get(name)
        if callable(fn):
            try:
                # Fix ổn định: cùng hash + cùng cổng + cùng gói + cùng history => cùng kết quả.
                # Nếu thuật toán admin có dùng random thì vẫn bị khóa seed theo dữ liệu đầu vào.
                _stable_seed = int(hashlib.sha256((str(md5_hex).lower().strip()+"|"+str(gate_key)+"|"+str(level)+"|"+"".join(history or [])).encode()).hexdigest()[:16], 16)
                _old_state = random.getstate()
                random.seed(_stable_seed)
                try:
                    r = _call_algo_func(fn, md5_hex, gate_key, level, history)
                finally:
                    random.setstate(_old_state)
                nr = normalize_prediction_result(r)
                if nr:
                    if not nr.get("hash_short"):
                        nr["hash_short"] = md5_hex[:8].upper() + "..." + md5_hex[-6:].upper()
                    return nr
            except BaseException:
                err = traceback.format_exc(limit=3)
                algo_cache["error"] = err
                log("Lỗi chạy thuật toán admin: " + err.replace("\n", " | ")[:500])
                return None
    return None

def _call_engine(fn, md5_hex, level="basic", gate_key="", history=None):
    if not fn:
        return None
    tries = [
        lambda: fn(md5_hex, gate_key, gate_key, history),
        lambda: fn(md5_hex, game=gate_key or "auto", history=history),
        lambda: fn(md5_hex, gate_key),
        lambda: fn(md5_hex),
    ]
    for cb in tries:
        try:
            r = cb()
            if r: return r
        except TypeError:
            continue
        except Exception as e:
            log("Lỗi engine file: " + repr(e))
            return None
    return None

def _predict_by_public_tier(md5_hex: str, gate_key="", public_level="basic", history=None):
    tc = tier_cfg(public_level)
    eff = effective_level_for_tier(public_level)
    hist_limit = max(10, int(tc.get("history_limit", 160) or 160))
    history = history if history is not None else recent_history_for_gate(gate_key, hist_limit)

    # Admin code có thể bật/tắt riêng cho từng gói.
    if tc.get("use_admin", True):
        ar = predict_admin(md5_hex, gate_key, eff, history)
        if ar:
            return apply_tier_policy(ar, public_level)

    fn = engine_predict_free if eff == "free" else engine_predict_pro if eff == "pro" else engine_predict_basic
    r = _call_engine(fn, md5_hex, eff, gate_key, history)
    if r:
        return apply_tier_policy(normalize_prediction_result(r, fallback_engine=f"FILE ENGINE {eff.upper()}") or r, public_level)
    fallback = legacy_predict_pro(md5_hex, gate_key) if eff == "pro" else legacy_predict_basic(md5_hex)
    return apply_tier_policy(fallback, public_level)

def predict_free(md5_hex: str, gate_key="", history=None):
    return _predict_by_public_tier(md5_hex, gate_key, "free", history)

def predict_basic(md5_hex: str, gate_key="", history=None):
    return _predict_by_public_tier(md5_hex, gate_key, "basic", history)

def predict_pro(md5_hex: str, gate_key="", history=None):
    return _predict_by_public_tier(md5_hex, gate_key, "pro", history)

def build_bot():
    global bot
    token = cfg.get("bot_token", "").strip()
    if not token:
        log("Chưa có BOT_TOKEN.")
        return None

    b = telebot.TeleBot(token, parse_mode="HTML")

    @b.message_handler(commands=["nomd5"])
    def nomd5_cmd(m):
        uid, user, username = get_user(m)
        gate = normalize_gate(user.get("active_gate"))
        if gate not in gates_by_mode("nomd5"):
            kb = InlineKeyboardMarkup()
            for gk, gv in gates_by_mode("nomd5").items():
                kb.add(InlineKeyboardButton(f"{gv.get('icon','🎮')} {gv.get('name',gk.upper())}", callback_data=f"gate_{gk}"))
            db["users"][uid]["predict_mode"] = "nomd5"; save_db()
            b.reply_to(m, "📡 Chọn cổng API trước:", reply_markup=kb)
            return
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Chạy API", callback_data="run_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home"))
        b.reply_to(m, f"📡 API đã sẵn sàng\n🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>", reply_markup=kb)

    @b.message_handler(commands=["start"])
    def start(m):
        uid, user, username = get_user(m)
        log(f"/start từ {uid}")
        # /start luôn hủy trạng thái nhập số tiền/nạp tiền/mua gói đang treo để không kẹt form.
        user_state.pop(uid, None)
        stop_all_live_by_user(uid)
        reset_live_streak(uid)
        b.reply_to(m, home_text(user, username, uid), reply_markup=kb_home())

    @b.message_handler(commands=["admin"])
    def admin(m):
        uid, user, username = get_user(m)
        if not is_admin(uid):
            b.reply_to(m, "❌ Bạn không phải admin.")
            return
        b.reply_to(m, "👑 <b>Lệnh admin</b>\n/setadmin USER_ID\n/addbalance USER_ID SOTIEN\n/duyetnap ORDER_ID\n/broadcast nội dung\n/stats")

    @b.message_handler(commands=["setadmin"])
    def setadmin(m):
        uid, user, username = get_user(m)
        if cfg.get("admin_ids") and not is_admin(uid):
            b.reply_to(m, "❌ Không có quyền.")
            return
        p = m.text.split()
        target = p[1] if len(p) > 1 else uid
        if str(target) not in [str(x) for x in cfg["admin_ids"]]:
            cfg["admin_ids"].append(str(target))
            save_cfg()
        b.reply_to(m, f"✅ Đã thêm admin: <code>{target}</code>")

    @b.message_handler(commands=["stats"])
    def stats(m):
        uid, user, username = get_user(m)
        if not is_admin(uid):
            return
        total = len(db["users"])
        bal = sum(int(u.get("balance", 0)) for u in db["users"].values())
        active = sum(1 for u in db["users"].values() if has_active_plan(u))
        b.reply_to(m, f"📊 Users: {total}\n🔥 Đang có gói: {active}\n💰 Tổng số dư: {money(bal)}")

    @b.message_handler(commands=["addbalance"])
    def addbal(m):
        uid, user, username = get_user(m)
        if not is_admin(uid):
            b.reply_to(m, "❌ Không có quyền.")
            return
        p = m.text.split()
        if len(p) != 3 or not p[2].isdigit():
            b.reply_to(m, "Sai cú pháp: <code>/addbalance USER_ID SOTIEN</code>")
            return
        target, amt = p[1], int(p[2])
        if target not in db["users"]:
            b.reply_to(m, "❌ User chưa /start bot.")
            return
        db["users"][target]["balance"] = int(db["users"][target].get("balance", 0)) + amt
        db["transactions"].append({"user_id": target, "type": "admin_add", "amount": amt, "time": now_str()})
        save_db()
        b.reply_to(m, f"✅ Đã cộng {money(amt)} cho <code>{target}</code>")
        try:
            b.send_message(target, f"💰 Bạn vừa được cộng <b>{money(amt)}</b>")
        except Exception:
            pass

    @b.message_handler(commands=["duyetnap"])
    def approve_deposit_cmd(m):
        uid, user, username = get_user(m)
        if not is_admin(uid):
            return
        p = m.text.split()
        if len(p) != 2:
            b.reply_to(m, "Sai cú pháp: <code>/duyetnap ORDER_ID</code>")
            return
        order_id = p[1].strip()
        ok, msg = approve_deposit(order_id, admin_id=uid)
        b.reply_to(m, msg)

    @b.message_handler(commands=["broadcast"])
    def broadcast(m):
        uid, user, username = get_user(m)
        if not is_admin(uid):
            return
        content = m.text.replace("/broadcast", "", 1).strip()
        if not content:
            b.reply_to(m, "Nhập: <code>/broadcast nội dung</code>")
            return
        db["announcements"].append({"message": content, "time": now_str()})
        save_db()
        sent = 0
        for target in list(db["users"].keys()):
            try:
                b.send_message(target, "📣 <b>THÔNG BÁO</b>\n\n" + content)
                sent += 1
                time.sleep(0.04)
            except Exception:
                pass
        b.reply_to(m, f"✅ Đã gửi {sent}/{len(db['users'])}")

    @b.callback_query_handler(func=lambda c: True)
    def cb(c):
        uid, user, username = get_user(c)
        try:
            b.answer_callback_query(c.id)
        except Exception:
            pass
        chat, mid = c.message.chat.id, c.message.message_id
        data = c.data

        if data == "pay_confirm" or data == "pay_cancel":
            pending = user_state.get(uid, {})
            if pending.get("mode") != "confirm_purchase":
                b.answer_callback_query(c.id, "Không có đơn mua đang chờ.", show_alert=True)
                return
            if data == "pay_cancel":
                user_state.pop(uid, None)
                safe_edit_or_send(b, chat, mid, "❌ Đã hủy thanh toán gói.", reply_markup=kb_home())
                return

            pk = pending["plan"]
            gate = pending["gate"]
            seconds = int(pending.get("seconds", int(pending.get("hours",1))*3600))
            hours = max(1, int(seconds // 3600))
            label = pending.get("label") or duration_label(seconds)
            total = int(pending["total"])
            if int(user.get("balance", 0)) < total:
                b.answer_callback_query(c.id, "❌ Số dư không đủ, vui lòng nạp thêm!", show_alert=True)
                return

            p = cfg["plans"][pk]
            bonus = purchase_bonus_amount(total)
            db["users"][uid]["balance"] = int(db["users"][uid].get("balance", 0)) - total + bonus
            db["users"][uid].setdefault("plan_expires", {"basic": 0, "pro": 0})
            current_exp = int(db["users"][uid]["plan_expires"].get(pk, 0) or 0)
            base_ts = max(current_exp, int(time.time()))
            new_exp = int(base_ts + seconds)
            db["users"][uid]["plan_expires"][pk] = new_exp
            db["users"][uid]["active_plan"] = pk   # tương thích hiển thị cũ
            db["users"][uid]["selected_plan"] = pk
            db["users"][uid]["active_gate"] = gate
            db["users"][uid]["plan_expire"] = plan_expire_ts(db["users"][uid])
            db["users"][uid]["total_spent"] = int(db["users"][uid].get("total_spent", 0)) + total

            order = {"id": "BUY" + str(int(time.time())) + uid[-4:], "user_id": uid, "username": username, "gate": gate, "plan": pk, "hours": hours, "seconds": seconds, "label": label, "amount": total, "bonus": bonus, "time": now_str()}
            db["purchases"].append(order)
            db["transactions"].append({"user_id": uid, "type": "purchase", "amount": -total, "bonus": bonus, "plan": pk, "hours": hours, "seconds": seconds, "label": label, "time": now_str()})
            save_db()
            user_state.pop(uid, None)

            notify_group(
                f"🛒 <b>ĐƠN MUA GÓI THÀNH CÔNG</b>\n"
                f"👤 User: <b>{mask_user(uid, username)}</b>\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Gói: <b>{p['name']}</b>\n"
                f"⏳ Số giờ: <b>{hours}</b>\n"
                f"💰 Giá: <b>{money(total)}</b>\n"
                f"🎁 Bonus tiền: <b>{money(bonus)}</b>"
            )
            b.edit_message_text(
                f"✅ <b>THANH TOÁN THÀNH CÔNG!</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Gói: <b>{p['name']}</b>\n"
                f"⏳ Số giờ: <b>{hours}</b>\n"
                f"💰 Đã trừ: <b>{money(total)}</b>\n"
                f"🎁 Bonus tiền: <b>{money(bonus)}</b>\n"
                f"💼 Số dư còn: <b>{money(db['users'][uid].get('balance',0))}</b>\n"
                f"📅 Hạn {p['name']}: <b>{active_until_text(db['users'][uid], pk)}</b>\n"
                f"⭐ Thường còn: <b>{remaining_time_text(db['users'][uid], 'basic')}</b>\n"
                f"💎 Pro còn: <b>{remaining_time_text(db['users'][uid], 'pro')}</b>\n\n"
                f"{('Gửi MD5 32 ký tự hoặc hash HitClub 64 ký tự để dự đoán ngay.' if db['users'][uid].get('predict_mode','md5') == 'md5' else 'Bấm /nomd5 hoặc nút Chọn Cổng & Gói để chạy dự đoán API.')}",
                chat, mid, reply_markup=kb_home()
            )
            return

        if data.startswith("admin_deposit_approve_") or data.startswith("admin_deposit_reject_"):
            if not is_admin(uid):
                b.answer_callback_query(c.id, "Bạn không phải admin!", show_alert=True)
                return
            order_id = data.replace("admin_deposit_approve_", "").replace("admin_deposit_reject_", "")
            if data.startswith("admin_deposit_approve_"):
                ok, msg = approve_deposit(order_id, admin_id=uid)
            else:
                ok, msg = reject_deposit(order_id, admin_id=uid)
            try:
                b.edit_message_reply_markup(chat, mid, reply_markup=None)
            except Exception:
                pass
            b.answer_callback_query(c.id, msg, show_alert=True)
            try:
                b.send_message(uid, ("✅ " if ok else "⚠️ ") + msg)
            except Exception:
                pass
            return

        if data == "noop":
            return

        if data == "back_home":
            stop_live_message(chat, mid)
            reset_live_streak(uid)
            safe_edit_or_send(b, chat, mid, home_text(user, username, uid), reply_markup=kb_home())
            return

        if data == "account":
            txt = (
                f"👤 <b>TÀI KHOẢN</b>\n\n"
                f"🆔 ID: <code>{uid}</code>\n"
                f"💰 Số dư: <b>{money(user.get('balance',0))}</b>\n"
                f"🎮 Cổng: <b>{(gate_icon(user.get('active_gate')) + ' ' + gate_name(user.get('active_gate'))) if user.get('active_gate') else 'Chưa chọn'}</b>\n"
                f"📦 Gói đang chọn: <b>{cfg.get('plans',{}).get(user.get('selected_plan'),{}).get('name', user.get('selected_plan') or 'Chưa chọn')}</b>\n"
                f"⭐ Gói Thường còn: <b>{remaining_time_text(user, 'basic')}</b>\n"
                f"💎 Gói Pro còn: <b>{remaining_time_text(user, 'pro')}</b>\n"
                f"🎁 Free còn: <b>{free_remaining_text()}</b>"
            )
            b.edit_message_text(txt, chat, mid, reply_markup=kb_back())
            return

        if data in ("choose_gate", "choose_type"):
            stop_live_message(chat, mid)
            reset_live_streak(uid)
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🔐 Dự đoán MD5", callback_data="mode_md5"))
            kb.add(InlineKeyboardButton("📡 Dự đoán API", callback_data="mode_nomd5"))
            kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
            b.edit_message_text(
                "🔮 <b>CHỌN KIỂU DỰ ĐOÁN</b>\n\n"
                "1️⃣ <b>MD5</b>: nhập hash MD5/HitClub để phân tích.\n"
                "2️⃣ <b>API</b>: bot tự lấy phiên/game API rồi dự đoán TX, SicBo, Baccarat.\n\n"
                "Sau đó bạn sẽ chọn cổng và chọn Free / Thường / Pro.",
                chat, mid, reply_markup=kb
            )
            return

        if data in ("mode_md5", "mode_nomd5"):
            stop_live_message(chat, mid)
            reset_live_streak(uid)
            mode = "md5" if data == "mode_md5" else "nomd5"
            db["users"][uid]["predict_mode"] = mode
            save_db()
            kb = InlineKeyboardMarkup(row_width=2)
            gate_buttons = []
            for gk, gv in gates_by_mode(mode).items():
                tag = "🔐" if mode == "md5" else "📡"
                gate_buttons.append(InlineKeyboardButton(f"{tag} {gv.get('icon', '🎮')} {gv.get('name', gk.upper())}", callback_data=f"gate_{gk}"))
            if gate_buttons:
                kb.add(*gate_buttons)
            else:
                kb.add(InlineKeyboardButton("⚠️ Chưa bật cổng nào", callback_data="noop"))
            kb.add(InlineKeyboardButton("🔙 Đổi kiểu", callback_data="choose_type"))
            b.edit_message_text(
                f"🎮 <b>{mode_title(mode).upper()}</b>\n\n"
                f"Chọn cổng game hỗ trợ <b>{mode_title(mode)}</b>:",
                chat, mid, reply_markup=kb
            )
            return

        if data.startswith("gate_"):
            gk = data.replace("gate_", "", 1)
            mode = db["users"][uid].get("predict_mode", "md5")
            if gk not in gates_by_mode(mode):
                b.answer_callback_query(c.id, "Cổng này không hỗ trợ kiểu dự đoán đang chọn!", show_alert=True)
                return
            db["users"][uid]["active_gate"] = gk
            save_db()

            b.edit_message_text(
                f"✅ Đã chọn: <b>{mode_title(mode)}</b> · <b>{gate_icon(gk)} {gate_name(gk)}</b>\n\n"
                f"Bây giờ chọn gói muốn dùng. Bạn có thể đổi Free/Thường/Pro từng lần, không bị khóa cố định.\n\n"
                f"⭐ Thường còn: <b>{remaining_time_text(db['users'][uid], 'basic')}</b>\n"
                f"💎 Pro còn: <b>{remaining_time_text(db['users'][uid], 'pro')}</b>\n"
                f"🎁 Free còn: <b>{free_remaining_text()}</b>",
                chat, mid, reply_markup=choose_plan_keyboard(gk, db['users'][uid])
            )
            return

        if data.startswith("useplan_"):
            pk = data.replace("useplan_", "", 1)
            gate = normalize_gate(db["users"][uid].get("active_gate"))
            db["users"][uid]["active_gate"] = gate
            if pk == "free":
                if not free_is_active():
                    b.answer_callback_query(c.id, "Free đang tắt hoặc đã hết hạn", show_alert=True)
                    return
                if not user_joined_free_channel(uid):
                    b.edit_message_text(join_channel_message(), chat, mid, reply_markup=kb_back())
                    return
                db["users"][uid]["selected_plan"] = "free"
                save_db()
                b.edit_message_text(
                    f"🎁 <b>ĐÃ CHỌN FREE</b>\n\n🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n⌛ Free còn: <b>{free_remaining_text()}</b>\n\nGửi MD5 để phân tích.",
                    chat, mid, reply_markup=(InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Chạy API", callback_data="run_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home")) if db['users'][uid].get('predict_mode') == 'nomd5' else kb_home())
                )
                return
            if pk not in ("basic", "pro") or not has_active_plan(db["users"][uid], pk):
                b.answer_callback_query(c.id, "Gói này chưa mua hoặc đã hết hạn", show_alert=True)
                return
            db["users"][uid]["selected_plan"] = pk
            db["users"][uid]["active_plan"] = pk
            save_db()
            b.edit_message_text(
                f"✅ <b>ĐÃ CHỌN GÓI</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Gói: <b>{cfg['plans'].get(pk,{}).get('name',pk)}</b>\n"
                f"⌛ Còn lại: <b>{remaining_time_text(db['users'][uid], pk)}</b>\n\n"
                f"{('Gửi MD5 32 ký tự hoặc hash HitClub 64 ký tự để dự đoán ngay.' if db['users'][uid].get('predict_mode','md5') == 'md5' else 'Bấm Chạy API để dự đoán phiên hiện tại.')}",
                chat, mid, reply_markup=(InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Chạy API", callback_data="run_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home")) if db['users'][uid].get('predict_mode') == 'nomd5' else kb_home())
            )
            return

        if data == "run_nomd5":
            try:
                b.answer_callback_query(c.id, "⚡ Đang khởi động API...", show_alert=False)
            except Exception:
                pass
            gate = normalize_gate(db["users"][uid].get("active_gate"))
            if gate not in gates_by_mode("nomd5"):
                b.answer_callback_query(c.id, "Cổng này đang lỗi API/tạm khóa API", show_alert=True)
                return
            plan = db["users"][uid].get("selected_plan") or best_available_plan(db["users"][uid])
            if plan == "pro" and has_active_plan(db["users"][uid], "pro"):
                pass
            elif plan == "basic" and has_active_plan(db["users"][uid], "basic"):
                pass
            elif plan == "free" or (not has_active_plan(db["users"][uid]) and free_is_active()):
                if not free_is_active():
                    b.answer_callback_query(c.id, "Free đang tắt/hết hạn", show_alert=True)
                    return
                if not user_joined_free_channel(uid):
                    b.edit_message_text(join_channel_message(), chat, mid, reply_markup=kb_back())
                    return
                plan = "free"
            else:
                b.answer_callback_query(c.id, "Bạn chưa có gói hợp lệ", show_alert=True)
                return

            # V129 FAST: không chờ API trả về ở callback. Hiện loading ngay rồi thread live tự update mỗi 3s.
            stop_all_live_by_user(uid)
            loading = (
                f"⚡ <b>ĐANG KHỞI ĐỘNG API</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Gói: <b>{cfg.get('plans',{}).get(plan,{}).get('name',plan)}</b>\n"
                f"⏱️ Tự cập nhật mỗi <b>3s</b>. Nếu API chậm sẽ tự bỏ qua lượt đó, không treo loading."
            )
            b.edit_message_text(loading, chat, mid, parse_mode="HTML", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Quay lại chọn cổng", callback_data="mode_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home")))
            start_nomd5_live(b, chat, mid, uid, gate, plan)
            return

        if data == "free_predict":
            gate = normalize_gate(db["users"][uid].get("active_gate"))
            db["users"][uid]["active_gate"] = gate
            save_db()
            if not free_is_active():
                b.edit_message_text(
                    "🎁 <b>FREE DỰ ĐOÁN</b>\n\n❌ Hiện Free Mode đang tắt hoặc đã hết thời gian. Vui lòng mua gói hoặc chờ admin mở free.",
                    chat, mid, reply_markup=kb_back()
                )
                return
            if not user_joined_free_channel(uid):
                b.edit_message_text(join_channel_message(), chat, mid, reply_markup=kb_back())
                return
            db["users"][uid]["selected_plan"] = "free"
            save_db()
            b.edit_message_text(
                f"🎁 <b>FREE DỰ ĐOÁN ĐÃ SẴN SÀNG</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"⌛ Free còn: <b>{free_remaining_text()}</b>\n\n"
                f"Gửi MD5 32 ký tự hoặc hash HitClub 64 ký tự để bot dự đoán miễn phí.",
                chat, mid, reply_markup=kb_home()
            )
            return

        if data == "deposit":
            user_state[uid] = {"mode": "deposit_amount"}
            b.edit_message_text("💰 <b>NẠP TIỀN</b>\n\nNhập số tiền muốn nạp, ví dụ: <code>50000</code>", chat, mid, reply_markup=kb_back())
            return

        if data == "buy_tool":
            ensure_plan_options()
            kb = InlineKeyboardMarkup(row_width=1)
            if "basic" in cfg.get("plans", {}):
                kb.add(InlineKeyboardButton("⭐ Thuê Gói Thường", callback_data="buy_basic"))
            if "pro" in cfg.get("plans", {}):
                kb.add(InlineKeyboardButton("💎 Thuê Gói Pro", callback_data="buy_pro"))
            kb.add(InlineKeyboardButton("🎁 Free dự đoán", callback_data="free_predict"))
            kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
            b.edit_message_text(
                f"🛒 <b>THUÊ GÓI PHÂN TÍCH</b>\n\n"
                f"Chọn loại gói rồi chọn thời hạn admin đã bật.\n"
                f"Không cần nhập số giờ thủ công nữa để tránh lỗi.\n\n"
                f"⭐ Gói Thường còn: <b>{remaining_time_text(user, 'basic')}</b>\n"
                f"💎 Gói Pro còn: <b>{remaining_time_text(user, 'pro')}</b>\n"
                f"💰 Số dư: <b>{money(user.get('balance',0))}</b>",
                chat, mid, reply_markup=kb
            )
            return

        if data in ("buy_basic", "buy_pro"):
            pk = data.replace("buy_", "", 1)
            if pk not in cfg.get("plans", {}):
                b.answer_callback_query(c.id, "Gói này chưa được cấu hình", show_alert=True)
                return
            p = cfg["plans"][pk]
            b.edit_message_text(
                f"🛒 <b>{p.get('name', pk.upper())}</b>\n\n"
                f"Chọn thời hạn muốn thuê bên dưới.\n"
                f"⏳ Hạn hiện có: <b>{remaining_time_text(user, pk)}</b>\n"
                f"💰 Số dư: <b>{money(user.get('balance',0))}</b>",
                chat, mid, reply_markup=plan_option_keyboard(pk)
            )
            return

        if data.startswith("buydur_"):
            try:
                _, pk, ok = data.split("_", 2)
            except Exception:
                return
            ensure_plan_options()
            if pk not in cfg.get("plans", {}) or ok not in cfg.get("plan_options", {}).get(pk, {}):
                b.answer_callback_query(c.id, "Mốc gói không tồn tại", show_alert=True)
                return
            op = cfg["plan_options"][pk][ok]
            if not op.get("enabled", False):
                b.answer_callback_query(c.id, "Mốc này đang tắt", show_alert=True)
                return
            seconds = int(op.get("seconds", 3600) or 3600)
            label = op.get("label") or duration_label(seconds)
            total = int(op.get("price", 0) or 0)
            gate = normalize_gate(db["users"][uid].get("active_gate")) or first_enabled_gate()
            user_state[uid] = {"mode": "confirm_purchase", "plan": pk, "gate": gate, "seconds": seconds, "label": label, "total": total}
            balance = int(user.get("balance", 0) or 0)
            after = balance - total
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(InlineKeyboardButton("✅ Thanh toán", callback_data="pay_confirm"), InlineKeyboardButton("❌ Hủy", callback_data="pay_cancel"))
            kb.add(InlineKeyboardButton("🔙 Đổi thời hạn", callback_data=f"buy_{pk}"))
            b.edit_message_text(
                f"🧾 <b>XÁC NHẬN THUÊ GÓI</b>\n\n"
                f"📦 Gói: <b>{cfg['plans'][pk].get('name', pk.upper())}</b>\n"
                f"⏳ Thời hạn: <b>{label}</b>\n"
                f"💰 Giá: <b>{money(total)}</b>\n"
                f"💼 Số dư: <b>{money(balance)}</b>\n"
                f"📉 Sau mua: <b>{money(after)}</b>\n\n"
                f"{'✅ Có thể thanh toán.' if after >= 0 else '❌ Không đủ số dư, vui lòng nạp thêm.'}",
                chat, mid, reply_markup=kb
            )
            return

        if data == "feedback":
            user_state[uid] = {"mode": "feedback_note"}
            b.edit_message_text("📸 <b>FEEDBACK</b>\n\nGửi ghi chú feedback trước, sau đó gửi ảnh kèm theo.", chat, mid, reply_markup=kb_back())
            return

    @b.message_handler(content_types=["photo", "text"])
    def allmsg(m):
        uid, user, username = get_user(m)
        state = user_state.get(uid, {})
        text = (m.text or "").strip()

        if state.get("mode") == "buy_hours" and text:
            user_state.pop(uid, None)
            b.reply_to(m, "⚠️ Flow mua gói đã đổi sang chọn nút thời hạn. Bấm <b>/start</b> → <b>Mua Gói</b> để chọn lại.")
            return

        if False and state.get("mode") == "buy_hours" and text:
            if not text.isdigit() or int(text) <= 0 or int(text) > 720:
                b.reply_to(m, "❌ Số giờ không hợp lệ. Nhập số từ 1 đến 720, ví dụ: <code>6</code>")
                return
            hours = int(text)
            pk = state.get("plan")
            gate = normalize_gate(state.get("gate") or user.get("active_gate"))
            plans = cfg.get("plans") if isinstance(cfg.get("plans"), dict) else {}
            if pk not in plans:
                user_state.pop(uid, None)
                b.reply_to(m, "❌ Không tìm thấy gói vừa chọn. Vui lòng bấm /start rồi chọn lại gói.")
                return

            p = plans[pk]
            price_hour = int(p.get("price_per_hour", 0))
            total = price_hour * hours
            balance = int(user.get("balance", 0))
            after = balance - total
            user_state[uid] = {"mode": "confirm_purchase", "plan": pk, "gate": gate, "hours": hours, "total": total}

            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(
                InlineKeyboardButton("✅ Thanh toán", callback_data="pay_confirm"),
                InlineKeyboardButton("❌ Từ chối", callback_data="pay_cancel")
            )
            b.reply_to(
                m,
                f"🧾 <b>XÁC NHẬN THANH TOÁN</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Gói: <b>{p['name']}</b>\n"
                f"⏳ Số giờ: <b>{hours}</b>\n"
                f"💵 Giá mỗi giờ: <b>{money(price_hour)}</b>\n"
                f"💰 Tổng tiền: <b>{money(total)}</b>\n"
                f"💼 Số dư hiện tại: <b>{money(balance)}</b>\n"
                f"📉 Số dư sau mua: <b>{money(after)}</b>\n\n"
                f"{'✅ Có thể thanh toán.' if after >= 0 else '❌ Không đủ số dư, vui lòng nạp thêm.'}",
                reply_markup=kb
            )
            return

        if state.get("mode") == "deposit_amount" and text:
            if not text.isdigit() or int(text) < 1000:
                b.reply_to(m, "❌ Số tiền tối thiểu 1.000đ. Nhập lại số tiền.")
                return

            now_ts = int(time.time())
            for old in reversed(db.get("deposits", [])):
                if str(old.get("user_id")) == uid and old.get("status") == "pending":
                    created_ts = int(old.get("created_ts", 0) or 0)
                    if created_ts and now_ts - created_ts < 180:
                        wait = 180 - (now_ts - created_ts)
                        b.reply_to(m, f"⏳ Bạn vừa tạo hóa đơn rồi. Vui lòng chờ <b>{wait}s</b> nữa mới tạo hóa đơn mới.\n\n🧾 Mã đơn cũ: <code>{old.get('id')}</code>")
                        return

            amount = int(text)
            order_id = "NAP" + str(int(time.time())) + uid[-4:]
            note = f"{cfg.get('payment_note_prefix','NAP')} {uid} {order_id}"
            order = {"id": order_id, "user_id": uid, "username": username, "amount": amount, "note": note, "status": "pending", "time": now_str(), "created_ts": int(time.time())}
            db["deposits"].append(order)
            save_db()
            user_state.pop(uid, None)
            q = qr_url(amount, note)
            caption = (
                f"💰 <b>ĐƠN NẠP TIỀN</b>\n\n"
                f"🧾 Mã đơn: <code>{order_id}</code>\n"
                f"💵 Số tiền: <b>{money(amount)}</b>\n"
                f"🏦 STK: <code>{cfg.get('bank_account')}</code>\n"
                f"👤 Tên: <b>{cfg.get('bank_name')}</b>\n"
                f"📝 Nội dung: <code>{note}</code>\n\n"
                f"Chuyển xong chờ admin duyệt."
            )
            try:
                b.send_photo(m.chat.id, q, caption=caption, parse_mode="HTML", reply_markup=kb_back())
            except Exception:
                b.reply_to(m, caption + "\n\nQR: " + q, reply_markup=kb_back())
            notify_admins_deposit(order)
            return

        if state.get("mode") == "feedback_note" and text:
            user_state[uid] = {"mode": "feedback_photo", "note": text}
            b.reply_to(m, "✅ Đã nhận ghi chú. Bây giờ gửi ảnh feedback.")
            return

        if state.get("mode") == "feedback_photo" and m.photo:
            photo_id = m.photo[-1].file_id
            fb_id = "FB" + str(int(time.time())) + uid[-4:]
            item = {"id": fb_id, "user_id": uid, "username": username, "note": state.get("note", ""), "photo_id": photo_id, "status": "pending", "time": now_str(), "created_ts": int(time.time())}
            db["feedback"].append(item)
            save_db()
            user_state.pop(uid, None)
            b.reply_to(m, f"✅ Feedback đã gửi, chờ admin duyệt.\nMã: <code>{fb_id}</code>")
            return

        if len(text) in (32, 64) and all(c in "0123456789abcdefABCDEF" for c in text):
            gate = normalize_gate(user.get("active_gate"))
            if not gate:
                gate = next(iter(gates_by_mode("md5") or enabled_gates()), first_enabled_gate())
            if gate not in gates_by_mode("md5"):
                b.reply_to(m, "❌ Cổng này không hỗ trợ MD5. Bấm /start → Dự đoán API để chạy theo phiên.")
                return
            user["active_gate"] = gate
            plan = user.get("selected_plan") or best_available_plan(user)
            free_used = False
            hist = recent_history_for_gate(gate or "", 500)
            if plan == "pro" and has_active_plan(user, "pro"):
                p = predict_pro(text, gate, hist)
            elif plan == "basic" and has_active_plan(user, "basic"):
                p = predict_basic(text, gate, hist)
            elif plan == "free" or (not has_active_plan(user) and free_is_active()):
                if not free_is_active():
                    b.reply_to(m, "❌ Free đã tắt/hết hạn. Bấm /start → chọn cổng → mua/chọn gói Thường hoặc Pro.")
                    return
                if not user_joined_free_channel(uid):
                    b.reply_to(m, join_channel_message())
                    return
                free_used = True
                plan = "free"
                user["selected_plan"] = "free"
                p = predict_free(text, gate or "", hist)
            else:
                b.reply_to(m, "❌ Bạn chưa chọn gói hoặc gói đã hết hạn.\n\nBấm /start → 🎮 Chọn Cổng & Gói để chọn Free/Thường/Pro.")
                return
            if not p:
                b.reply_to(m, "❌ MD5 không hợp lệ.")
                return
            if not p.get("bridge_type"):
                det = p.get("details") or []
                p["bridge_type"] = (str(det[0]).split(":")[0] if det else p.get("trend", "Hash đa lớp / cầu tổng hợp"))
            result_icon = "📈" if p["taixiu"] == "TÀI" else "📉"
            detail = " · ".join(p.get("details", []))
            trend = ("\n🧭 Xu hướng: <b>" + p.get("trend", "") + "</b>") if plan == "pro" else ""
            db["predictions"].append({"user_id": uid, "username": username, "gate": gate, "plan": plan, "md5": p["hash_short"], "result": p["taixiu"], "confidence": p["tx_conf"], "time": now_str()})
            save_db()
            b.reply_to(m, format_md5_reply(gate, p))
            return

        b.reply_to(m, "💡 Nhấn /start để mở menu hoặc gửi MD5 32 ký tự hoặc hash HitClub 64 ký tự.")

    return b

def approve_deposit(order_id, admin_id="web"):
    for o in db["deposits"]:
        if str(o.get("id")) == str(order_id):
            if o.get("status") == "approved":
                return False, "Đơn này đã duyệt rồi."
            uid = str(o["user_id"])
            amount = int(o["amount"])
            if uid not in db["users"]:
                return False, "User không tồn tại."
            o["status"] = "approved"
            o["approved_time"] = now_str()
            o["admin_id"] = str(admin_id)
            bonus = bonus_deposit_amount(amount)
            total_add = amount + bonus
            db["users"][uid]["balance"] = int(db["users"][uid].get("balance", 0)) + total_add
            db["users"][uid]["total_deposit"] = int(db["users"][uid].get("total_deposit", 0)) + amount
            db["transactions"].append({"user_id": uid, "type": "deposit", "amount": amount, "bonus": bonus, "time": now_str(), "order_id": order_id})
            save_db()
            try:
                bot.send_message(uid, f"✅ <b>NẠP TIỀN THÀNH CÔNG</b>\n\n💵 Số tiền: <b>{money(amount)}</b>\n🎁 Bonus: <b>{money(bonus)}</b>\n💰 Số dư mới: <b>{money(db['users'][uid]['balance'])}</b>")
            except Exception:
                pass
            notify_group(f"✅ <b>NẠP TIỀN THÀNH CÔNG</b>\n👤 User: <b>{mask_user(uid, o.get('username',''))}</b>\n💵 Số tiền: <b>{money(amount)}</b>\n🧾 Mã: <code>{order_id}</code>")
            return True, "Đã duyệt nạp tiền."
    return False, "Không tìm thấy đơn."

def reject_deposit(order_id, admin_id="web"):
    for o in db["deposits"]:
        if str(o.get("id")) == str(order_id):
            if o.get("status") == "approved":
                return False, "Đơn đã duyệt, không thể từ chối."
            if o.get("status") == "rejected":
                return False, "Đơn này đã bị từ chối rồi."
            uid = str(o.get("user_id"))
            amount = int(o.get("amount", 0))
            o["status"] = "rejected"
            o["rejected_time"] = now_str()
            o["admin_id"] = str(admin_id)
            save_db()
            try:
                bot.send_message(uid, f"❌ <b>ĐƠN NẠP BỊ TỪ CHỐI</b>\n\n🧾 Mã đơn: <code>{order_id}</code>\n💵 Số tiền: <b>{money(amount)}</b>\nVui lòng kiểm tra lại giao dịch hoặc liên hệ hỗ trợ.")
            except Exception:
                pass
            notify_admins_text(f"❌ <b>ADMIN ĐÃ TỪ CHỐI ĐƠN NẠP</b>\n🧾 Mã: <code>{order_id}</code>\n👤 User: <b>{mask_user(uid, o.get('username',''))}</b>\n💵 Số tiền: <b>{money(amount)}</b>")
            return True, "Đã từ chối đơn nạp."
    return False, "Không tìm thấy đơn."

def approve_feedback(fb_id):
    for fb in db["feedback"]:
        if str(fb.get("id")) == str(fb_id):
            if fb.get("status") == "approved":
                return False, "Feedback đã duyệt rồi."
            caption = (
                f"📸 <b>FEEDBACK MỚI</b>\n"
                f"👤 User: <b>{mask_user(fb.get('user_id'), fb.get('username',''))}</b>\n"
                f"📝 Ghi chú: {html.escape(str(fb.get('note','')))}"
            )
            sent = notify_group_photo(fb.get("photo_id"), caption)
            if not sent:
                return False, "Chưa gửi được feedback lên group. Kiểm tra Link group public/@username/-100chatid và thêm bot vào group."
            fb["status"] = "approved"
            fb["approved_time"] = now_str()
            fb["sent_to_group"] = True
            save_db()
            return True, "Đã duyệt và gửi feedback lên group."
    return False, "Không tìm thấy feedback."

def bot_worker():
    global bot_running, bot
    while True:
        try:
            bot = build_bot()
            if bot is None:
                bot_running = False
                time.sleep(10)
                continue
            log("Đang xóa webhook cũ...")
            bot.remove_webhook()
            time.sleep(1)
            bot_running = True
            log("Bot polling đang chạy.")
            bot.infinity_polling(timeout=10, long_polling_timeout=10, skip_pending=True)
        except Exception as e:
            bot_running = False
            log(f"LỖI BOT: {repr(e)}")
            time.sleep(1)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "kingbot-" + secrets.token_hex(16))

BASE_HTML = r"""
<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{title}}</title>
<style>
:root{--a:{{cfg.get('accent','#8b5cf6')}};--bg:#060916;--card:#0f172a;--card2:#17213b;--bd:#263a68;--tx:#edf4ff;--mut:#95a8cd;--g:#21e79a;--r:#ff4d67;--y:#ffb020;--c:#00d5ff}
*{box-sizing:border-box}body{margin:0;min-height:100vh;background:
radial-gradient(circle at 16% -10%,rgba(139,92,246,.45),transparent 32%),
radial-gradient(circle at 88% 0,rgba(0,213,255,.22),transparent 25%),
linear-gradient(180deg,#060916,#0a1022);color:var(--tx);font-family:Segoe UI,Arial,sans-serif}
body:before{content:"";position:fixed;inset:0;background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);background-size:36px 36px;mask-image:linear-gradient(to bottom,black,transparent);pointer-events:none}.wrap{display:flex;min-height:100vh}.side{width:270px;background:rgba(10,16,32,.78);backdrop-filter:blur(18px);border-right:1px solid var(--bd);display:flex;flex-direction:column}.brand{padding:30px 22px;border-bottom:1px solid var(--bd)}.brand h2{margin:0;font-size:23px;letter-spacing:.2px}.brand p{margin:8px 0 0;color:var(--mut);font-size:13px}.nav{padding:14px}.nav a{display:flex;gap:10px;align-items:center;color:#cbd8f5;text-decoration:none;padding:14px 15px;border-radius:14px;margin-bottom:8px;transition:.18s}.nav a:hover,.nav a.on{background:linear-gradient(135deg,rgba(139,92,246,.28),rgba(0,213,255,.13));color:white;transform:translateX(3px)}.main{flex:1;padding:32px;position:relative}.top{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:24px}.title{font-size:32px;font-weight:950;text-shadow:0 0 24px rgba(139,92,246,.45)}.pill{padding:11px 16px;border-radius:99px;background:rgba(33,231,154,.12);border:1px solid rgba(33,231,154,.38);color:#70ffbd}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.card{background:linear-gradient(180deg,rgba(15,23,42,.92),rgba(15,23,42,.76));border:1px solid var(--bd);border-radius:22px;padding:23px;box-shadow:0 24px 70px rgba(0,0,0,.24),inset 0 1px 0 rgba(255,255,255,.05)}.card h2{margin-top:0}.stat{position:relative;overflow:hidden}.stat:after{content:"";position:absolute;right:-25px;top:-25px;width:90px;height:90px;background:var(--a);filter:blur(45px);opacity:.45}.stat b{display:block;font-size:31px;margin-top:10px}.mut{color:var(--mut)}input,textarea,select{width:100%;background:rgba(23,33,59,.95);border:1px solid var(--bd);border-radius:14px;color:var(--tx);padding:13px 15px;margin:7px 0 15px;outline:none}input:focus,textarea:focus{border-color:var(--a);box-shadow:0 0 0 4px rgba(139,92,246,.12)}textarea{min-height:110px}.btn{border:0;border-radius:14px;padding:12px 16px;font-weight:900;text-decoration:none;display:inline-block;cursor:pointer;transition:.16s}.btn:hover{transform:translateY(-1px);filter:brightness(1.08)}.pri{background:linear-gradient(135deg,var(--a),#b15cff);color:white}.green{background:linear-gradient(135deg,#22e29b,#11c9c3);color:#021}.red{background:linear-gradient(135deg,#ff4d67,#ff7a59);color:white}.yellow{background:linear-gradient(135deg,#ffb020,#ffd166);color:#211}.cyan{background:linear-gradient(135deg,#00d5ff,#64f4ff);color:#012}table{width:100%;border-collapse:collapse;overflow:hidden}td,th{padding:13px;border-bottom:1px solid rgba(38,58,104,.75);text-align:left}th{color:var(--mut);font-weight:800}code{color:var(--c)}.alert{padding:14px 17px;border-radius:15px;margin-bottom:17px;background:#063925;border:1px solid #176b4a;color:#55ffaa}.login{min-height:100vh;display:grid;place-items:center}.login .card{width:min(420px,92vw)}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}pre{white-space:pre-wrap;font-family:Consolas,monospace;color:#cfe3ff}.footer{margin-top:auto;padding:18px 22px;color:var(--mut);font-size:12px}.badge{padding:5px 10px;border-radius:999px;background:rgba(139,92,246,.18);border:1px solid rgba(139,92,246,.35)}@media(max-width:980px){.side{display:none}.main{padding:16px}.grid,.grid2,.grid3{grid-template-columns:1fr}.top{display:block}.title{font-size:26px}}
</style></head><body>
{% if not session.get('login') %}
<div class="login"><div class="card"><h1>👑 KingBot Ultra Admin</h1>{% if msg %}<div class="alert">{{msg}}</div>{% endif %}<form method="post" action="/login"><input type="password" name="password" placeholder="Mật khẩu admin"><button class="btn pri" style="width:100%">Đăng nhập</button></form><p class="mut">Mặc định: admin123</p></div></div>
{% else %}
<div class="wrap"><aside class="side"><div class="brand"><h2>👑 {{cfg.get('shop_name')}}</h2><p>Ultra Render Admin</p></div><nav class="nav">
<a class="{{'on' if page=='dashboard' else ''}}" href="/">📊 Dashboard</a>
<a class="{{'on' if page=='settings' else ''}}" href="/settings">⚙️ Cài đặt</a>
<a class="{{'on' if page=='users' else ''}}" href="/users">👥 Users</a>
<a class="{{'on' if page=='admins' else ''}}" href="/admins">👑 Admin IDs</a>
<a class="{{'on' if page=='child_bots' else ''}}" href="/child_bots">🤖 Bot con</a>
<a class="{{'on' if page=='admin_keys' else ''}}" href="/admin_keys">🔑 Admin Keys</a>
<a class="{{'on' if page=='deposits' else ''}}" href="/deposits">💰 Nạp tiền</a>
<a class="{{'on' if page=='feedback' else ''}}" href="/feedback">📸 Feedback</a>
<a class="{{'on' if page=='broadcast' else ''}}" href="/broadcast">📣 Thông báo</a>
<a class="{{'on' if page=='backup' else ''}}" href="/backup">☁️ Backup</a>
<a class="{{'on' if page=='logs' else ''}}" href="/logs">🧾 Logs</a>
<a href="/logout">🚪 Đăng xuất</a>
</nav><div class="footer">Polling · Render Ready</div></aside><main class="main">
{% if msg %}<div class="alert">{{msg}}</div>{% endif %}
{{content|safe}}
</main></div>
{% endif %}
</body></html>
"""

def render_page(page, content, msg=""):
    # Render-safe: ưu tiên templates/admin.html, nếu user upload thiếu template thì dùng BASE_HTML nội bộ để không 500.
    ctx = dict(title="KingBot Ultra Admin", cfg=cfg, page=page, content=content, msg=msg, bot_running=bot_running, session=session)
    try:
        return render_template("admin.html", **ctx)
    except Exception as e:
        try: log(f"render_page fallback do thiếu/lỗi template: {e}")
        except Exception: pass
        return render_template_string(BASE_HTML, **ctx)

@app.route("/login", methods=["POST"])
def login():
    if request.form.get("password") == cfg.get("admin_password", "admin123"):
        session["login"] = True
        return redirect("/")
    return render_page("login", "", "Sai mật khẩu")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/healthz")
def healthz():
    return {"ok": True, "bot_running": bot_running}

@app.route("/")
def dashboard():
    if not session.get("login"): return render_page("dashboard", "")
    total = len(db["users"])
    active = sum(1 for u in db["users"].values() if has_active_plan(u))
    bal = sum(int(u.get("balance", 0)) for u in db["users"].values())
    revenue = sum(int(t.get("amount", 0)) for t in db["transactions"] if t.get("type") == "deposit")
    recent = list(reversed(list(db["users"].values())))[:10]
    rows = "".join([f"<tr><td><code>{u.get('id')}</code></td><td>@{u.get('username')}</td><td>{money(u.get('balance',0))}</td><td>{u.get('selected_plan') or '-'}</td><td>⭐ {remaining_time_text(u,'basic')}<br>💎 {remaining_time_text(u,'pro')}</td></tr>" for u in recent])
    content = f"""
    <div class="top"><div class="title">📊 Dashboard Ultra</div><div class="pill">{'✅ Bot đang chạy' if bot_running else '❌ Bot chưa chạy'}</div></div>
    <div class="grid">
      <div class="card stat"><span class="mut">Tổng users</span><b style="color:var(--c)">{total}</b></div>
      <div class="card stat"><span class="mut">Đang có gói</span><b style="color:var(--g)">{active}</b></div>
      <div class="card stat"><span class="mut">Tổng số dư</span><b style="color:var(--y)">{money(bal)}</b></div>
      <div class="card stat"><span class="mut">Tổng nạp duyệt</span><b style="color:var(--a)">{money(revenue)}</b></div>
    </div><br>
    <div class="grid3">
      <div class="card"><h2>🎮 Cổng game</h2><p class="mut">LC79 · HitClub · BetVip</p></div>
      <div class="card"><h2>🧠 Engine</h2><p class="mut">Free Lite < Basic Omni < Pro V30 HitClub</p></div>
      <div class="card"><h2>📸 Feedback</h2><p class="mut">{len([x for x in db['feedback'] if x.get('status')=='pending'])} chờ duyệt</p></div>
    </div><br>
    <div class="card"><h2>👥 Users mới nhất</h2><table><tr><th>ID</th><th>User</th><th>Số dư</th><th>Gói</th><th>Hạn</th></tr>{rows}</table></div>
    """
    return render_page("dashboard", content)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("login"): return render_page("settings", "")
    msg = ""
    if request.method == "POST":
        cfg["bot_token"] = request.form.get("bot_token","").strip()
        cfg["admin_password"] = request.form.get("admin_password","admin123")
        cfg["shop_name"] = request.form.get("shop_name","KingBot Luxury")
        cfg["accent"] = request.form.get("accent","#8b5cf6")
        cfg["welcome_text"] = request.form.get("welcome_text","")
        cfg["support_url"] = request.form.get("support_url","")
        cfg["group_chat_id"] = request.form.get("group_chat_id","")
        cfg["group_link"] = request.form.get("group_link","")
        cfg["feedback_group_target"] = request.form.get("feedback_group_target", cfg.get("feedback_group_target", ""))
        cfg["bank_name_key"] = request.form.get("bank_name_key","MSB")
        cfg["bank_bin"] = bank_bin_from_name(cfg["bank_name_key"])
        cfg["bank_account"] = request.form.get("bank_account","")
        cfg["bank_name"] = request.form.get("bank_name","")
        cfg["payment_note_prefix"] = request.form.get("payment_note_prefix","NAP")
        cfg["backup_url"] = request.form.get("backup_url","")
        cfg["backup_secret"] = request.form.get("backup_secret","")
        cfg["backup_interval_seconds"] = int(request.form.get("backup_interval_seconds",120) or 120)
        cfg["algorithm_enabled"] = request.form.get("algorithm_enabled") == "on"
        cfg["algorithm_code"] = request.form.get("algorithm_code", "")
        cfg["algorithm_note"] = request.form.get("algorithm_note", "")
        algo_cache.update({"hash": None, "ns": {}, "error": ""})

        cfg["free_mode_enabled"] = request.form.get("free_mode_enabled") == "on"
        cfg["free_duration_hours"] = int(request.form.get("free_duration_hours",24) or 24)
        cfg["free_require_join"] = request.form.get("free_require_join") == "on"
        cfg["free_channel"] = request.form.get("free_channel","").strip()
        cfg["free_channel_link"] = request.form.get("free_channel_link","").strip()
        if request.form.get("free_action") == "open_now":
            cfg["free_until"] = int((datetime.now() + timedelta(hours=int(cfg.get("free_duration_hours", 24) or 24))).timestamp())
            db.setdefault("free_sessions", []).append({"time": now_str(), "hours": int(cfg.get("free_duration_hours",24) or 24), "until": cfg["free_until"]})
            save_db()
        elif request.form.get("free_action") == "close_now":
            cfg["free_until"] = 0
            cfg["free_mode_enabled"] = False
        cfg["deposit_bonus_enabled"] = request.form.get("deposit_bonus_enabled") == "on"
        cfg["deposit_bonus_percent"] = int(request.form.get("deposit_bonus_percent",10) or 0)
        cfg["deposit_bonus_min"] = int(request.form.get("deposit_bonus_min",50000) or 0)
        cfg["purchase_bonus_enabled"] = request.form.get("purchase_bonus_enabled") == "on"
        cfg["purchase_bonus_chance"] = int(request.form.get("purchase_bonus_chance",8) or 0)
        cfg["purchase_bonus_percent"] = int(request.form.get("purchase_bonus_percent",5) or 0)

        for gk in cfg["gates"]:
            cfg["gates"][gk]["name"] = request.form.get(f"gate_{gk}_name", cfg["gates"][gk].get("name", gk.upper()))
            cfg["gates"][gk]["icon"] = request.form.get(f"gate_{gk}_icon", cfg["gates"][gk].get("icon","🎮"))
            cfg["gates"][gk]["enabled"] = request.form.get(f"gate_{gk}_enabled") == "on"
        for pk in cfg["plans"]:
            cfg["plans"][pk]["name"] = request.form.get(f"plan_{pk}_name", cfg["plans"][pk].get("name", pk.upper()))
            cfg["plans"][pk]["price_per_hour"] = int(request.form.get(f"plan_{pk}_price", cfg["plans"][pk].get("price_per_hour",0)) or 0)
        ensure_plan_options()
        for pk, opts in cfg.get("plan_options", {}).items():
            for ok, op in opts.items():
                op["enabled"] = request.form.get(f"opt_{pk}_{ok}_enabled") == "on"
                op["label"] = request.form.get(f"opt_{pk}_{ok}_label", op.get("label", ok))
                try: op["seconds"] = int(request.form.get(f"opt_{pk}_{ok}_seconds", op.get("seconds", 3600)) or 3600)
                except Exception: pass
                try: op["price"] = int(request.form.get(f"opt_{pk}_{ok}_price", op.get("price", 0)) or 0)
                except Exception: pass
        save_cfg()
        msg = "Đã lưu cấu hình. Nếu đổi token bot thì Render sẽ tự chạy lại vòng polling sau vài giây hoặc Manual Deploy để chắc chắn."

    gates_html = ""
    for gk, gv in cfg["gates"].items():
        checked = "checked" if gv.get("enabled") else ""
        gates_html += (
            f"<label>{gk.upper()} tên</label><input name='gate_{gk}_name' value='{gv.get('name','')}'>"
            f"<label>{gk.upper()} icon emoji</label><input name='gate_{gk}_icon' value='{gv.get('icon','🎮')}'>"
            f"<label><input style='width:auto' type='checkbox' name='gate_{gk}_enabled' {checked}> Bật {gk.upper()}</label><br>"
        )

    plans_html = ""
    for pk, p in cfg["plans"].items():
        plans_html += (
            f"<h3>{pk.upper()}</h3>"
            f"<label>Tên gói</label><input name='plan_{pk}_name' value='{p.get('name','')}'>"
            f"<label>Giá mỗi giờ</label><input type='number' name='plan_{pk}_price' value='{p.get('price_per_hour',0)}'>"
        )

    ensure_plan_options()
    plan_options_html = ""
    for pk, opts in cfg.get("plan_options", {}).items():
        title = cfg.get("plans", {}).get(pk, {}).get("name", pk.upper())
        plan_options_html += f"<div class='plan-admin-card'><h3>{html.escape(str(title))}</h3><div class='plan-admin-grid'>"
        for ok, op in opts.items():
            checked = "checked" if op.get("enabled") else ""
            plan_options_html += (
                f"<div class='plan-duration-card'>"
                f"<label class='checkline'><input type='checkbox' name='opt_{pk}_{ok}_enabled' {checked}> Bật mốc <b>{html.escape(str(ok))}</b></label>"
                f"<label>Tên hiển thị</label><input name='opt_{pk}_{ok}_label' value='{html.escape(str(op.get('label','')))}'>"
                f"<label>Số giây hạn dùng</label><input type='number' name='opt_{pk}_{ok}_seconds' value='{int(op.get('seconds',3600) or 3600)}'>"
                f"<label>Giá bán</label><input type='number' name='opt_{pk}_{ok}_price' value='{int(op.get('price',0) or 0)}'>"
                f"</div>"
            )
        plan_options_html += "</div></div>"

    free_checked = "checked" if cfg.get("free_mode_enabled") else ""
    dep_bonus_checked = "checked" if cfg.get("deposit_bonus_enabled") else ""
    buy_bonus_checked = "checked" if cfg.get("purchase_bonus_enabled") else ""

    content = f"""
    <div class="top"><div class="title">⚙️ Cài đặt hệ thống</div></div>
    <form method="post">
    <div class="grid2">
      <div class="card"><h2>🤖 Bot & Giao diện</h2>
        <label>Bot Token</label><input name="bot_token" value="{cfg.get('bot_token','')}">
        <label>Mật khẩu admin web</label><input name="admin_password" value="{cfg.get('admin_password','admin123')}">
        <label>Tên shop</label><input name="shop_name" value="{cfg.get('shop_name','')}">
        <label>Màu chủ đạo</label><input name="accent" value="{cfg.get('accent','#8b5cf6')}">
        <label>Text chào mừng</label><input name="welcome_text" value="{cfg.get('welcome_text','')}">
        <label>Link hỗ trợ</label><input name="support_url" value="{cfg.get('support_url','')}">
        <label>Group Chat ID hoặc @username</label><input name="group_chat_id" value="{cfg.get('group_chat_id','')}" placeholder="-100xxxxxxxxxx hoặc @group_username">
        <label>Link group public</label><input name="group_link" value="{cfg.get('group_link','')}" placeholder="https://t.me/ten_group_public">
        <label>Feedback gửi vào group này</label><input name="feedback_group_target" value="{cfg.get('feedback_group_target','')}" placeholder="https://t.me/ten_group_public hoặc @group hoặc -100...">
      </div>
      <div class="card"><h2>💳 VietQR & Backup</h2>
        <label>Tên ngân hàng</label><input name="bank_name_key" value="{cfg.get('bank_name_key','MSB')}" placeholder="VD: MSB, VCB, MBBANK, ACB">
        <label>Số tài khoản</label><input name="bank_account" value="{cfg.get('bank_account','')}">
        <label>Tên chủ tài khoản</label><input name="bank_name" value="{cfg.get('bank_name','')}">
        <label>Tiền tố nội dung</label><input name="payment_note_prefix" value="{cfg.get('payment_note_prefix','NAP')}">
        <hr style="border-color:var(--bd)">
        <label>Backup URL PHP</label><input name="backup_url" value="{cfg.get('backup_url','')}" placeholder="https://domain.com/backup.php">
        <label>Backup Secret</label><input name="backup_secret" value="{cfg.get('backup_secret','')}">
        <label>Chu kỳ backup giây</label><input type="number" name="backup_interval_seconds" value="{cfg.get('backup_interval_seconds',120)}">
      </div>
    </div><br>
    <div class="grid2">
      <div class="card"><h2>🎮 Cổng Game</h2>{gates_html}</div>
      <div class="card"><h2>🛒 Tên gói chính</h2>{plans_html}</div>
    </div><br>
    <div class="card plan-manager-card">
      <h2>🧾 Quản lý mốc thuê gói</h2>
      <p class="mut">Bật/tắt và set giá từng mốc giờ/ngày/tuần/tháng/vĩnh viễn cho Thường và Pro. User sẽ chọn bằng nút, không cần nhập số giờ.</p>
      {plan_options_html}
    </div><br>
    <div class="card">
      <h2>🧠 Thuật toán Admin HTML</h2>
      <label><input style="width:auto" type="checkbox" name="algorithm_enabled" {('checked' if cfg.get('algorithm_enabled') else '')}> Dùng thuật toán dán trong admin thay cho file Python</label>
      <label>Ghi chú</label><input name="algorithm_note" value="{html.escape(str(cfg.get('algorithm_note','')))}">
      <label>Code Python thuật toán</label>
      <textarea name="algorithm_code" spellcheck="false" style="min-height:320px;font-family:ui-monospace,Consolas,monospace" placeholder="def predict(md5, gate='', level='basic'):
    # return dict: taixiu, tx_conf, dice, total...
    return {{'taixiu':'TÀI','tx_conf':70}}">{html.escape(str(cfg.get('algorithm_code','')))}</textarea>
      <p class="mut">Bot sẽ đọc code này trực tiếp từ config. Có thể định nghĩa <code>predict(md5, gate, level)</code> hoặc riêng <code>predict_basic</code>, <code>predict_pro</code>, <code>predict_free</code>. Lỗi gần nhất: <code>{html.escape(algo_cache.get('error','')[:250])}</code></p>
    </div><br>
    <div class="card">
      <h2>🎁 Free & Bonus</h2>
      <label><input style="width:auto" type="checkbox" name="free_mode_enabled" {free_checked}> Bật Free Mode theo thời gian</label>
      <p class="mut">Trạng thái: <b>{free_until_text()}</b> · còn <b>{free_remaining_text()}</b></p>
      <label>Mở free trong bao lâu (giờ)</label><input type="number" name="free_duration_hours" value="{cfg.get('free_duration_hours',24)}">
      <label><input style="width:auto" type="checkbox" name="free_require_join" {('checked' if cfg.get('free_require_join', True) else '')}> Free Mode bắt buộc vào kênh</label>
      <label>@username kênh / chat_id kênh</label><input name="free_channel" value="{cfg.get('free_channel','')}" placeholder="@kenh_cua_ban">
      <label>Link kênh hiển thị cho user</label><input name="free_channel_link" value="{cfg.get('free_channel_link','')}" placeholder="https://t.me/kenh_cua_ban">
      <div class="row"><button class="btn green" name="free_action" value="open_now">🚀 Mở free ngay</button><button class="btn red" name="free_action" value="close_now">⛔ Tắt free ngay</button></div><br>
      <label><input style="width:auto" type="checkbox" name="deposit_bonus_enabled" {dep_bonus_checked}> Bật bonus nạp tiền</label>
      <label>% bonus nạp</label><input type="number" name="deposit_bonus_percent" value="{cfg.get('deposit_bonus_percent',10)}">
      <label>Nạp tối thiểu để bonus</label><input type="number" name="deposit_bonus_min" value="{cfg.get('deposit_bonus_min',50000)}">
      <label><input style="width:auto" type="checkbox" name="purchase_bonus_enabled" {buy_bonus_checked}> Bật random bonus khi mua gói</label>
      <label>Tỉ lệ trúng bonus mua gói (%)</label><input type="number" name="purchase_bonus_chance" value="{cfg.get('purchase_bonus_chance',8)}">
      <label>% bonus mua gói</label><input type="number" name="purchase_bonus_percent" value="{cfg.get('purchase_bonus_percent',5)}">
    </div><br>
    <button class="btn pri">💾 Lưu tất cả</button>
    </form>
    """
    return render_page("settings", content, msg)



@app.route("/algorithm_manage", methods=["GET", "POST"])
def algorithm_manage():
    if not session.get("login"):
        return render_page("algorithm_manage", "")
    msg = ""
    cfg.setdefault("algorithm_tiers", {})
    defaults = DEFAULT_CONFIG.get("algorithm_tiers", {})
    for lv, dv in defaults.items():
        cfg["algorithm_tiers"].setdefault(lv, dv.copy())
    if request.method == "POST":
        for lv in ("free", "basic", "pro"):
            tc = cfg["algorithm_tiers"].setdefault(lv, {})
            tc["mode"] = request.form.get(f"{lv}_mode", tc.get("mode", "normal"))
            tc["use_admin"] = request.form.get(f"{lv}_use_admin") == "on"
            try: tc["history_limit"] = int(request.form.get(f"{lv}_history_limit", tc.get("history_limit", 100)) or 100)
            except Exception: tc["history_limit"] = defaults.get(lv, {}).get("history_limit", 100)
            try: tc["max_conf"] = int(request.form.get(f"{lv}_max_conf", tc.get("max_conf", 90)) or 90)
            except Exception: tc["max_conf"] = defaults.get(lv, {}).get("max_conf", 90)
            try: tc["penalty"] = int(request.form.get(f"{lv}_penalty", tc.get("penalty", 0)) or 0)
            except Exception: tc["penalty"] = defaults.get(lv, {}).get("penalty", 0)
            try: tc["min_entry"] = int(request.form.get(f"{lv}_min_entry", tc.get("min_entry", 58)) or 58)
            except Exception: tc["min_entry"] = defaults.get(lv, {}).get("min_entry", 58)
        save_cfg()
        algo_cache.update({"hash": None, "ns": {}, "error": ""})
        msg = "Đã lưu quản lí thuật toán theo gói. Free/Thường/Pro giờ chạy đúng mode bạn chọn."

    def option(mode, val, text):
        return f"<option value='{val}' {'selected' if mode==val else ''}>{text}</option>"

    cards = ""
    labels = {"free":"FREE", "basic":"GÓI THƯỜNG", "pro":"GÓI PRO"}
    desc = {
        "weak":"Đểu/lite: ít history, confidence bị trừ, hợp cho free demo.",
        "lite":"Free lite: nhẹ hơn basic nhưng không random bậy.",
        "normal":"Thường: dùng engine basic, history vừa.",
        "strong":"Xịn: gọi engine pro, history dài hơn.",
        "royal":"Siêu xịn: pro full, cap cao, ít phạt confidence."
    }
    for lv in ("free", "basic", "pro"):
        tc = tier_cfg(lv)
        mode = tc.get("mode", "normal")
        use_checked = "checked" if tc.get("use_admin", True) else ""
        cards += f"""
        <div class='tier-card card'>
          <div class='tier-head'><div><b>{labels[lv]}</b><span>{TIER_MODE_LABEL.get(mode, mode)}</span></div><i>{'Bật code admin' if tc.get('use_admin', True) else 'Dùng file engine'}</i></div>
          <label>Chất lượng thuật toán</label>
          <select name='{lv}_mode'>
            {option(mode,'weak','ĐỂU / Lite demo')}
            {option(mode,'lite','FREE Lite ổn')}
            {option(mode,'normal','THƯỜNG / Basic')}
            {option(mode,'strong','XỊN / Pro')}
            {option(mode,'royal','Bản Nâng Cấp New')}
          </select>
          <p class='mut small'>{desc.get(mode,'')}</p>
          <label><input type='checkbox' name='{lv}_use_admin' {use_checked}> Ưu tiên dùng code ở tab Code thuật toán</label>
          <div class='mini-grid'>
            <div><label>History lấy</label><input type='number' name='{lv}_history_limit' value='{tc.get('history_limit',100)}'></div>
            <div><label>Cap % tối đa</label><input type='number' name='{lv}_max_conf' value='{tc.get('max_conf',90)}'></div>
            <div><label>Trừ %</label><input type='number' name='{lv}_penalty' value='{tc.get('penalty',0)}'></div>
            <div><label>Ngưỡng nên đánh</label><input type='number' name='{lv}_min_entry' value='{tc.get('min_entry',58)}'></div>
          </div>
        </div>
        """
    sample = request.args.get("sample", "f3335ef2e7c4f7a8e5b6282938a55ca12fbf53dfc1281aeb2a2bff1745da520f")
    preview_rows = ""
    for lv, fn in (("free", predict_free), ("basic", predict_basic), ("pro", predict_pro)):
        try:
            r = fn(sample, "hitclub", list("TTTXXTXTXXTTXXTTTXXTXXTTXTXTTXXT"))
        except Exception as e:
            r = {"taixiu":"ERR", "tx_conf":0, "advice":repr(e), "tier_label":"ERROR"}
        preview_rows += f"<tr><td>{lv.upper()}</td><td>{html.escape(str(r.get('tier_label','')))}</td><td><b>{html.escape(str(r.get('taixiu','')))}</b></td><td>{r.get('tx_conf','')}%</td><td>{html.escape(str(r.get('advice','')))}</td></tr>"
    content = f"""
    <div class='hero-admin card'>
      <div><span class='eyebrow'>Algorithm Control Center</span><h1>🧠 Quản lí thuật toán theo gói</h1><p class='mut'>Bạn tự quyết Free/Thường/Pro dùng thuật toán xịn hay đểu. Không cần sửa code, chỉ chọn mode rồi lưu.</p></div>
      <a class='btn cyan' href='/algorithm'>Mở tab dán code .py</a>
    </div>
    <form method='post'>
      <div class='tier-grid'>{cards}</div>
      <div class='sticky-save glass'><button class='btn pri' type='submit'>💾 Lưu quản lí thuật toán</button><a class='btn green' href='/algorithm_manage'>↻ Test lại</a></div>
    </form>
    <div class='card'><h2>🎯 Preview HitClub</h2><p class='mut'>Test nhanh với hash mẫu để xem mỗi gói đang khác nhau ra sao.</p><table><tr><th>Gói</th><th>Mode</th><th>Kết luận</th><th>%</th><th>Khuyên</th></tr>{preview_rows}</table></div>
    <div class='grid3'>
      <div class='card'><h2>Free đểu</h2><p class='mut'>Chọn mode ĐỂU/Lite, history 20-40, cap 60-68%, trừ 5-12%.</p></div>
      <div class='card'><h2>Thường cân bằng</h2><p class='mut'>Mode Normal/Strong, history 120-220, cap 82-90%.</p></div>
      <div class='card'><h2>Pro xịn</h2><p class='mut'>Mode Royal, history 300-500, cap 95-98%, penalty 0.</p></div>
    </div>
    """
    return render_page("algorithm_manage", content, msg)

@app.route("/algorithm_download.py")
def algorithm_download_py():
    if not session.get("login"):
        return redirect("/")
    code = str(cfg.get("algorithm_code") or "")
    if not code.strip():
        try:
            with open(os.path.join(CORE, "engine_md5.py"), "r", encoding="utf-8") as f:
                code = f.read()
        except Exception:
            code = "# Không đọc được engine_md5.py\n"
    resp = make_response(code)
    resp.headers["Content-Type"] = "text/x-python; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=admin_algorithm_current.py"
    return resp

@app.route("/algorithm", methods=["GET", "POST"])
def algorithm_page():
    if not session.get("login"):
        return render_page("algorithm", "")
    msg = ""
    test_result = ""
    if request.method == "POST":
        action = request.form.get("action", "save")
        if action == "upload_py":
            f = request.files.get("algo_file")
            if not f:
                msg = "❌ Chưa chọn file .py"
            else:
                raw = f.read().decode("utf-8", "ignore")
                cfg["algorithm_code"] = raw
                cfg["algorithm_enabled"] = True
                cfg["algorithm_note"] = "Upload từ file .py trong Admin > Thuật toán"
                save_cfg(); algo_cache.update({"hash": None, "ns": {}, "error": ""})
                msg = "✅ Đã upload và bật thuật toán admin. Bot sẽ dùng code này ngay."
        elif action == "toggle_builtin":
            cfg["algorithm_enabled"] = False
            save_cfg(); algo_cache.update({"hash": None, "ns": {}, "error": ""})
            msg = "✅ Đã tắt thuật toán admin, quay về engine_md5.py trong source."
        elif action == "test":
            cfg["algorithm_enabled"] = request.form.get("algorithm_enabled") == "on"
            cfg["algorithm_code"] = request.form.get("algorithm_code", "")
            cfg["algorithm_note"] = request.form.get("algorithm_note", "")
            algo_cache.update({"hash": None, "ns": {}, "error": ""})
            sample = request.form.get("test_hash", "").strip() or "f3335ef2e7c4f7a8e5b6282938a55ca12fbf53dfc1281aeb2a2bff1745da520f"
            game = request.form.get("test_game", "hitclub")
            level = request.form.get("test_level", "pro")
            hist = list(request.form.get("test_history", "TTTXXTXTXXTTXXTTTXXTXXTTXTXTTXXTXXTTTXXT").strip())
            r = predict_admin(sample, game, level, hist) if cfg.get("algorithm_enabled") else None
            if not r:
                if level == "free": r = predict_free(sample, game, hist)
                elif level == "pro": r = predict_pro(sample, game, hist)
                else: r = predict_basic(sample, game, hist)
            test_result = "<pre>" + html.escape(json.dumps(r, ensure_ascii=False, indent=2)) + "</pre>"
            msg = "✅ Đã test thuật toán."
        else:
            cfg["algorithm_enabled"] = request.form.get("algorithm_enabled") == "on"
            cfg["algorithm_code"] = request.form.get("algorithm_code", "")
            cfg["algorithm_note"] = request.form.get("algorithm_note", "")
            save_cfg(); algo_cache.update({"hash": None, "ns": {}, "error": ""})
            msg = "✅ Đã lưu thuật toán admin."
    checked = "checked" if cfg.get("algorithm_enabled") else ""
    code = html.escape(str(cfg.get("algorithm_code", "") or ""), quote=True)
    note = html.escape(str(cfg.get("algorithm_note", "") or ""), quote=True)
    err = html.escape(str(algo_cache.get("error", "") or "")[:1200])
    content = f"""
    <div class='top'><div class='title'>🧠 Thuật toán Admin Bot</div><a class='btn cyan' href='/algorithm_download.py'>⬇️ Tải thuật toán hiện tại</a></div>
    <div class='grid2'>
      <div class='card'>
        <h2>✅ Chỗ nâng cấp thuật toán</h2>
        <p class='mut'>Có. Dán code Python hoặc upload file .py tại đây. Khi bật, bot ưu tiên dùng thuật toán admin trước file <code>engine_md5.py</code>.</p>
        <form method='post' enctype='multipart/form-data'>
          <label>Upload file thuật toán .py</label>
          <input type='file' name='algo_file' accept='.py,text/x-python,text/plain'>
          <button class='btn pri' name='action' value='upload_py'>⬆️ Upload & bật ngay</button>
        </form><br>
        <form method='post'><button class='btn yellow' name='action' value='toggle_builtin'>↩️ Dùng engine mặc định trong source</button></form>
        <p class='mut'>Hàm hỗ trợ: <code>predict(md5, gate, level, game, history)</code>, <code>predict_free</code>, <code>predict_basic</code>, <code>predict_pro</code>.</p>
      </div>
      <div class='card'>
        <h2>🎯 Test nhanh HitClub</h2>
        <form method='post'>
          <input type='hidden' name='algorithm_code' value="{code}">
          <input type='hidden' name='algorithm_note' value="{note}">
          <label><input style='width:auto' type='checkbox' name='algorithm_enabled' {checked}> Test bằng thuật toán admin đang dán</label>
          <label>Hash test</label><input name='test_hash' value='f3335ef2e7c4f7a8e5b6282938a55ca12fbf53dfc1281aeb2a2bff1745da520f'>
          <label>Game</label><select name='test_game'><option value='betvip'>betvip</option><option value='hitclub'>hitclub</option><option value='lc79'>lc79</option><option value='bet'>bet</option><option value='auto'>auto</option></select>
          <label>Level</label><select name='test_level'><option value='pro'>pro</option><option value='basic'>basic</option><option value='free'>free</option></select>
          <label>History T/X</label><input name='test_history' value='TTTXXTXTXXTTXXTTTXXTXXTTXTXTTXXTXXTTTXXT'>
          <button class='btn green' name='action' value='test'>🧪 Test</button>
        </form>
      </div>
    </div><br>
    <div class='card'>
      <h2>✍️ Code thuật toán</h2>
      <form method='post'>
        <label><input style='width:auto' type='checkbox' name='algorithm_enabled' {checked}> Bật thuật toán admin</label>
        <label>Ghi chú</label><input name='algorithm_note' value="{note}">
        <textarea name='algorithm_code' spellcheck='false' style='min-height:520px;font-family:ui-monospace,Consolas,monospace'>{code}</textarea>
        <div class='row'><button class='btn pri' name='action' value='save'>💾 Lưu thuật toán</button><button class='btn green' name='action' value='test'>💾 Lưu tạm & test</button></div>
      </form>
      <p class='mut'>Lỗi gần nhất: <code>{err}</code></p>
    </div><br>
    {test_result}
    """
    return render_page("algorithm", content, msg)


def _public_base_url():
    return request.url_root.rstrip("/")

def _tool_slug(x):
    s = re.sub(r"[^a-zA-Z0-9_\-]+", "_", str(x or "tool").strip().lower()).strip("_")
    return s or "tool"


# ===================== V120 ADMIN KEY + BOT CON =====================
def _hash_token(token):
    return hashlib.sha256(str(token or '').encode()).hexdigest()[:16]

def make_admin_key(scope='child', days=30):
    key = 'KB-' + secrets.token_urlsafe(18).replace('-', '').replace('_', '')[:22].upper()
    cfg.setdefault('admin_keys', {})[key] = {
        'scope': scope,
        'enabled': True,
        'created': now_str(),
        'expire': int(time.time()) + int(days)*86400 if int(days or 0) > 0 else 0,
        'used_by': []
    }
    save_cfg()
    return key

def use_admin_key(user_id, key, bot_scope='child'):
    key = str(key or '').strip()
    item = cfg.setdefault('admin_keys', {}).get(key)
    if not item or not item.get('enabled', True):
        return False, '❌ Key admin sai hoặc đã bị tắt.'
    exp = int(item.get('expire') or 0)
    if exp and time.time() > exp:
        return False, '❌ Key admin đã hết hạn.'
    uid = str(user_id)
    if uid not in item.setdefault('used_by', []):
        item['used_by'].append(uid)
    db.setdefault('child_admin_sessions', {})[f'{bot_scope}:{uid}'] = {'ok': True, 'key': key, 'time': now_str()}
    save_cfg(); save_db()
    return True, '✅ Key đúng. Bấm /admin để mở bảng lệnh quản trị.'

def is_child_admin(user_id, bot_scope='child'):
    return bool(db.setdefault('child_admin_sessions', {}).get(f'{bot_scope}:{str(user_id)}', {}).get('ok'))

def _child_scope(bot_id):
    data = db.setdefault('child_bot_data', {})
    return data.setdefault(bot_id, {'users': {}, 'transactions': [], 'settings': {}, 'bank': {}, 'plans': json.loads(json.dumps(cfg.get('plan_options', {}), ensure_ascii=False))})

@app.route('/admin_keys', methods=['GET','POST'])
def admin_keys_page():
    if not session.get('login'): return render_page('admin_keys','')
    msg=''
    cfg.setdefault('admin_keys', {})
    if request.method == 'POST':
        action=request.form.get('action')
        if action == 'create':
            key=make_admin_key(request.form.get('scope','child'), int(request.form.get('days') or 30))
            msg='✅ Đã tạo key: ' + key
        elif action == 'toggle':
            k=request.form.get('key','')
            if k in cfg['admin_keys']:
                cfg['admin_keys'][k]['enabled']=not cfg['admin_keys'][k].get('enabled',True); save_cfg(); msg='✅ Đã đổi trạng thái key.'
        elif action == 'delete':
            cfg['admin_keys'].pop(request.form.get('key',''), None); save_cfg(); msg='✅ Đã xóa key.'
    rows=''
    for k,v in reversed(list(cfg.get('admin_keys',{}).items())):
        exp=v.get('expire') or 0
        exp_txt='Không hết hạn' if not exp else datetime.fromtimestamp(exp).strftime('%Y-%m-%d %H:%M')
        rows += f"<tr><td><code>{html.escape(k)}</code></td><td>{html.escape(str(v.get('scope','child')))}</td><td>{'ON' if v.get('enabled',True) else 'OFF'}</td><td>{exp_txt}</td><td>{len(v.get('used_by',[]))}</td><td><form method='post' class='row'><input type='hidden' name='key' value='{html.escape(k)}'><button class='btn yellow' name='action' value='toggle'>Bật/Tắt</button><button class='btn red' name='action' value='delete'>Xóa</button></form></td></tr>"
    content=f"""<div class='top'><div class='title'>🔑 Admin Keys</div></div><div class='card'><form method='post' class='grid3'><div><label>Scope</label><select name='scope'><option value='child'>Bot con</option><option value='main'>Bot chính</option></select></div><div><label>Số ngày</label><input name='days' type='number' value='30'></div><div><label>&nbsp;</label><button class='btn pri' name='action' value='create'>Tạo key admin</button></div></form></div><div class='card'><table><tr><th>Key</th><th>Scope</th><th>TT</th><th>Hết hạn</th><th>Đã dùng</th><th></th></tr>{rows}</table></div>"""
    return render_page('admin_keys', content, msg)


@app.route('/bots_manager', methods=['GET','POST'])
def bots_manager_page():
    if not session.get('login'):
        return render_page('bots_manager','')
    msg=''
    cfg.setdefault('child_bots', {})
    cfg.setdefault('admin_keys', {})
    if request.method == 'POST':
        action=request.form.get('action','')
        if action == 'add_child_bot':
            token=request.form.get('token','').strip()
            name=request.form.get('name','Bot con').strip() or 'Bot con'
            if not token or ':' not in token:
                msg='❌ Token bot con không hợp lệ.'
            else:
                bid=_hash_token(token)
                cfg['child_bots'][bid]={'enabled':True,'name':name,'token':token,'created':now_str(),'owner':'root_admin'}
                save_cfg(); msg='✅ Đã thêm token bot con. Bot sẽ tự chạy sau 5-10 giây, thử /start lại.'
        elif action == 'toggle_child_bot':
            bid=request.form.get('bid','')
            if bid in cfg['child_bots']:
                cfg['child_bots'][bid]['enabled']=not cfg['child_bots'][bid].get('enabled',True)
                save_cfg(); msg='✅ Đã bật/tắt bot con.'
        elif action == 'delete_child_bot':
            cfg['child_bots'].pop(request.form.get('bid',''), None)
            save_cfg(); msg='✅ Đã xóa bot con.'
        elif action == 'create_admin_key':
            days=int(request.form.get('days') or 30)
            key=make_admin_key('child', days)
            msg=f'✅ Đã tạo key admin bot con: {key}'
        elif action == 'toggle_admin_key':
            k=request.form.get('key','')
            if k in cfg['admin_keys']:
                cfg['admin_keys'][k]['enabled']=not cfg['admin_keys'][k].get('enabled',True)
                save_cfg(); msg='✅ Đã bật/tắt key.'
        elif action == 'delete_admin_key':
            cfg['admin_keys'].pop(request.form.get('key',''), None)
            save_cfg(); msg='✅ Đã xóa key.'
    bot_rows=''
    for bid,v in cfg.get('child_bots',{}).items():
        token=v.get('token','')
        mask=(token[:10]+'...'+token[-6:]) if len(token)>20 else '***'
        bot_rows += f"<tr><td>{html.escape(v.get('name','Bot con'))}</td><td><code>{html.escape(mask)}</code></td><td><code>{html.escape(bid)}</code></td><td>{'ON' if v.get('enabled',True) else 'OFF'}</td><td>{html.escape(v.get('created',''))}</td><td><form method='post' class='row'><input type='hidden' name='bid' value='{html.escape(bid)}'><button class='btn yellow' name='action' value='toggle_child_bot'>Bật/Tắt</button><button class='btn red' name='action' value='delete_child_bot'>Xóa</button></form></td></tr>"
    key_rows=''
    for k,v in reversed(list(cfg.get('admin_keys',{}).items())):
        exp=v.get('expire') or 0
        exp_txt='Không hết hạn' if not exp else datetime.fromtimestamp(exp).strftime('%Y-%m-%d %H:%M')
        key_rows += f"<tr><td><code>{html.escape(k)}</code></td><td>Bot con</td><td>{'ON' if v.get('enabled',True) else 'OFF'}</td><td>{exp_txt}</td><td>{len(v.get('used_by',[]))}</td><td><form method='post' class='row'><input type='hidden' name='key' value='{html.escape(k)}'><button class='btn yellow' name='action' value='toggle_admin_key'>Bật/Tắt</button><button class='btn red' name='action' value='delete_admin_key'>Xóa</button></form></td></tr>"
    content=f"""
    <div class='top'><div class='title'>🤖 Quản lí bot con</div></div>
    <div class='grid2'>
      <div class='card'><h2>➕ Thêm bot con</h2><p class='mut'>Admin gốc add token bot con tại đây. Bot con độc lập data với bot chính.</p>
        <form method='post'><label>Tên bot con</label><input name='name' placeholder='VD: Bot đại lý 1'><label>Token bot con</label><input name='token' placeholder='123456789:AA...'><button class='btn pri' name='action' value='add_child_bot'>Lưu token bot con</button></form>
      </div>
      <div class='card'><h2>🔑 Tạo key admin bot con</h2><p class='mut'>User vào bot con nhập <code>/adminkey KEY</code>. Đúng key mới dùng được <code>/admin</code>. /start thường không hiện lệnh admin.</p>
        <form method='post' class='grid2'><div><label>Số ngày key</label><input name='days' type='number' value='30'></div><div><label>&nbsp;</label><button class='btn green' name='action' value='create_admin_key'>Tạo key admin</button></div></form>
      </div>
    </div>
    <div class='card'><h2>📦 Danh sách bot con</h2><table><tr><th>Tên</th><th>Token</th><th>ID</th><th>TT</th><th>Tạo lúc</th><th></th></tr>{bot_rows or '<tr><td colspan=6 class=mut>Chưa có bot con.</td></tr>'}</table></div>
    <div class='card'><h2>🔐 Key admin bot con</h2><table><tr><th>Key</th><th>Loại</th><th>TT</th><th>Hết hạn</th><th>Đã dùng</th><th></th></tr>{key_rows or '<tr><td colspan=6 class=mut>Chưa có key.</td></tr>'}</table></div>
    """
    return render_page('bots_manager', content, msg)

@app.route('/child_bots', methods=['GET','POST'])
def child_bots_page():
    if not session.get('login'): return render_page('child_bots','')
    msg=''
    cfg.setdefault('child_bots', {})
    if request.method == 'POST':
        action=request.form.get('action')
        if action == 'add':
            token=request.form.get('token','').strip()
            name=request.form.get('name','Bot con').strip() or 'Bot con'
            if token:
                bid=_hash_token(token)
                cfg['child_bots'][bid]={'enabled':True,'name':name,'token':token,'created':now_str()}
                save_cfg(); msg='✅ Đã thêm bot con. Bot sẽ tự chạy sau 5-10 giây, thử /start lại.'
        elif action == 'toggle':
            bid=request.form.get('bid','')
            if bid in cfg['child_bots']:
                cfg['child_bots'][bid]['enabled']=not cfg['child_bots'][bid].get('enabled',True); save_cfg(); msg='✅ Đã đổi trạng thái bot con.'
        elif action == 'delete':
            cfg['child_bots'].pop(request.form.get('bid',''), None); save_cfg(); msg='✅ Đã xóa bot con khỏi config.'
    rows=''
    for bid,v in cfg.get('child_bots',{}).items():
        rows += f"<tr><td>{html.escape(v.get('name','Bot con'))}</td><td><code>{bid}</code></td><td>{'ON' if v.get('enabled',True) else 'OFF'}</td><td>{html.escape(v.get('created',''))}</td><td><form method='post' class='row'><input type='hidden' name='bid' value='{bid}'><button class='btn yellow' name='action' value='toggle'>Bật/Tắt</button><button class='btn red' name='action' value='delete'>Xóa</button></form></td></tr>"
    content=f"""<div class='top'><div class='title'>🤖 Bot con</div></div><div class='card'><p class='mut'>Bot con độc lập với bot chính. User nhập <code>/adminkey KEY</code>, đúng key mới dùng được <code>/admin</code>.</p><form method='post'><label>Tên bot con</label><input name='name' placeholder='VD: Bot đại lý 1'><label>Token bot con</label><input name='token' placeholder='123456:ABC...'><button class='btn pri' name='action' value='add'>Thêm bot con</button></form></div><div class='card'><table><tr><th>Tên</th><th>ID nội bộ</th><th>TT</th><th>Tạo lúc</th><th></th></tr>{rows}</table></div>"""
    return render_page('child_bots', content, msg)

@app.route("/api_tool", methods=["GET", "POST"])
def api_tool_page():
    if not session.get("login"):
        return render_page("api_tool", "")
    msg = ""
    cfg.setdefault("api_tools", {})
    cfg.setdefault("custom_api_urls", {})
    if request.method == "POST":
        action = request.form.get("action", "save_urls")
        if action == "create_tool":
            slug = _tool_slug(request.form.get("slug") or request.form.get("name"))
            cfg["api_tools"][slug] = {
                "enabled": True,
                "name": request.form.get("name", slug).strip() or slug,
                "gate": normalize_gate(request.form.get("gate", "lc79")),
                "level": request.form.get("level", "pro"),
                "secret": request.form.get("secret", "").strip(),
                "cors": request.form.get("cors") == "on"
            }
            msg = "✅ Đã tạo API tool. Copy endpoint bên dưới gắn vào HTML/web."
        elif action == "delete_tool":
            slug = _tool_slug(request.form.get("slug"))
            cfg["api_tools"].pop(slug, None)
            msg = "✅ Đã xóa API tool."
        elif action == "save_tools":
            for slug, t in list(cfg.get("api_tools", {}).items()):
                t["enabled"] = request.form.get(f"tool_{slug}_enabled") == "on"
                t["name"] = request.form.get(f"tool_{slug}_name", t.get("name", slug))
                t["gate"] = normalize_gate(request.form.get(f"tool_{slug}_gate", t.get("gate", "lc79")))
                t["level"] = request.form.get(f"tool_{slug}_level", t.get("level", "pro"))
                t["secret"] = request.form.get(f"tool_{slug}_secret", t.get("secret", ""))
                t["cors"] = request.form.get(f"tool_{slug}_cors") == "on"
            msg = "✅ Đã lưu danh sách API tool."
        else:
            for g in NOMD5_API_MAP.keys():
                raw = request.form.get(f"custom_{g}", "")
                cfg["custom_api_urls"][g] = [u.strip() for u in raw.replace("\r", "").split("\n") if u.strip()]
            _nomd5_health.clear(); _nomd5_cache.clear()
            msg = "✅ Đã lưu API nguồn. Custom URL sẽ được ưu tiên trước API mặc định."
        save_cfg()
    gate_order = ['bcr'] + [k for k in NOMD5_API_MAP.keys() if k != 'bcr']
    gate_opts = ''.join([f"<option value='{k}' {'selected' if k=='bcr' else ''}>{gate_name(k)}</option>" for k in gate_order])
    source_cards = ""
    for g in gate_order:
        val = html.escape("\n".join(cfg.get("custom_api_urls", {}).get(g, [])))
        default = html.escape("\n".join(NOMD5_API_MAP[g].get("urls", [])))
        source_cards += f"""
        <div class='api-source-card'>
          <h3>{gate_icon(g)} {gate_name(g)}</h3>
          <label>API nguồn custom, mỗi dòng 1 URL</label>
          <textarea name='custom_{g}' placeholder='Dán API mới ở đây, ví dụ API Baccarat/sexy.js nếu có endpoint JSON'>{val}</textarea>
          <details><summary>API mặc định</summary><pre>{default}</pre></details>
        </div>"""
    tool_rows = ""
    ensure_api_tools_config()
    for slug, t in cfg.get("api_tools", {}).items():
        url = f"{_public_base_url()}/api/predict/{slug}"
        checked = "checked" if t.get("enabled", True) else ""
        cors = "checked" if t.get("cors", True) else ""
        opts = ''.join([f"<option value='{k}' {'selected' if k==t.get('gate') else ''}>{gate_name(k)}</option>" for k in gate_order])
        lvopts = ''.join([f"<option value='{lv}' {'selected' if lv==t.get('level') else ''}>{lv.upper()}</option>" for lv in ("free","basic","pro")])
        tool_rows += f"""
        <div class='tool-card'>
          <div class='row' style='justify-content:space-between'><h3>🔗 {html.escape(slug)}</h3><code>{html.escape(url)}</code></div>
          <label><input type='checkbox' name='tool_{slug}_enabled' {checked}> Bật API này</label>
          <div class='mini-grid'>
            <div><label>Tên</label><input name='tool_{slug}_name' value='{html.escape(str(t.get('name', slug)), quote=True)}'></div>
            <div><label>Cổng</label><select name='tool_{slug}_gate'>{opts}</select></div>
            <div><label>Gói thuật toán</label><select name='tool_{slug}_level'>{lvopts}</select></div>
            <div><label>Secret tùy chọn</label><input name='tool_{slug}_secret' value='{html.escape(str(t.get('secret','')), quote=True)}' placeholder='bỏ trống = public'></div>
          </div>
          <label><input type='checkbox' name='tool_{slug}_cors' {cors}> Cho HTML/web khác gọi CORS</label>
          <pre>fetch('{html.escape(url)}')
  .then(r=>r.json())
  .then(data=>{{
    document.querySelector('#result').innerText = data.side_label + ' - ' + data.confidence + '%';
  }})</pre>
          <form method='post' onsubmit="return confirm('Xóa API tool này?')"><input type='hidden' name='slug' value='{html.escape(slug)}'><button class='btn red' name='action' value='delete_tool'>Xóa</button></form>
        </div>"""
    content = f"""
    <div class='hero-admin card'><div><span class='eyebrow'>API TOOL BUILDER</span><h1>🔌 Khởi tạo API dự đoán</h1><p class='mut'>Tạo endpoint JSON cho LC79/HitClub/Baccarat hoặc cổng khác để nối thẳng vào HTML/web.</p></div></div>
    <div class='grid2'>
      <div class='card'><h2>➕ Tạo API tool mới</h2><form method='post'>
        <label>Tên API</label><input name='name' value='Baccarat Pro API'>
        <label>Slug endpoint</label><input name='slug' value='baccarat_pro'>
        <label>Cổng</label><select name='gate'>{gate_opts}</select>
        <label>Gói thuật toán</label><select name='level'><option value='pro'>PRO</option><option value='basic'>BASIC</option><option value='free'>FREE</option></select>
        <label>Secret tùy chọn</label><input name='secret' placeholder='bỏ trống để public'>
        <label><input type='checkbox' name='cors' checked> Cho web/HTML khác gọi</label>
        <button class='btn pri' name='action' value='create_tool'>Tạo API</button>
      </form></div>
      <div class='card'><h2>🃏 API game chuẩn để gắn HTML</h2><pre>/api/game/hitclub
/api/game/b52
/api/game/lc79
/api/game/sunwin
/api/game/bcr
/api/predict/baccarat?history=PBPBBP</pre><p class='mut'>Mọi endpoint trả JSON chuẩn: result, side_label, confidence, pattern/bridge_type, period, dice/total. Baccarat trả BANKER/PLAYER/TIE + Tay Cái/Tay Con/Hòa.</p><h2>📌 JS gắn HTML nhanh</h2><pre>&lt;div id="result"&gt;&lt;/div&gt;
&lt;script&gt;
fetch('/api/game/hitclub')
 .then(r=&gt;r.json())
 .then(d=&gt; result.innerHTML = `${{d.side_label}} - ${{d.confidence}}% - ${{d.pattern}}`);
&lt;/script&gt;</pre></div>
    </div>
    <form method='post'><div class='card'><h2>🧩 API tool đang có</h2>{tool_rows or '<p class=mut>Chưa có API tool.</p>'}<button class='btn green' name='action' value='save_tools'>💾 Lưu tool</button></div></form>
    <form method='post'><div class='card'><h2>🌐 Thay API nguồn</h2><p class='mut'>Muốn thay Baccarat bằng API mới thì dán URL vào ô Baccarat. Hệ thống sẽ ưu tiên URL này trước API mặc định.</p><div class='api-source-grid'>{source_cards}</div><button class='btn pri' name='action' value='save_urls'>💾 Lưu API nguồn</button></div></form>
    """
    return render_page("api_tool", content, msg)

@app.route("/api/predict/<slug>")
def public_api_predict(slug):
    cfg.setdefault("api_tools", {})
    t = cfg.get("api_tools", {}).get(_tool_slug(slug))
    if not t or not t.get("enabled", True):
        return jsonify({"ok": False, "error": "API tool disabled or not found"}), 404
    secret = str(t.get("secret") or "").strip()
    if secret and request.args.get("secret", "") != secret:
        return jsonify({"ok": False, "error": "bad secret"}), 403
    gate = normalize_gate(request.args.get("gate") or t.get("gate", "lc79"))
    level = str(request.args.get("level") or t.get("level", "pro")).lower()
    hist = request.args.get("history", "")
    p = predict_nomd5(gate, level, hist)
    result = p.get("taixiu")
    payload = _api_payload_from_predict(_tool_slug(slug), gate, level, p, t.get("name"))
    resp = jsonify(payload)
    if t.get("cors", True):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return resp



@app.route("/api/game/<gate>", methods=["GET", "OPTIONS"])
def api_game_direct(gate):
    if request.method == "OPTIONS":
        resp = jsonify({"ok": True})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        return resp
    gate = normalize_gate(gate)
    level = str(request.args.get("level") or "pro").lower()
    hist = request.args.get("history", "")
    p = predict_nomd5(gate, level, hist)
    payload = _api_payload_from_predict(f"game_{gate}", gate, level, p, gate_name(gate))
    resp = jsonify(payload)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

@app.route("/api/predict", methods=["GET", "OPTIONS"])
def api_predict_by_gate_query():
    if request.method == "OPTIONS":
        resp = jsonify({"ok": True})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        return resp
    gate = normalize_gate(request.args.get("gate") or "hitclub")
    level = str(request.args.get("level") or "pro").lower()
    hist = request.args.get("history", "")
    p = predict_nomd5(gate, level, hist)
    payload = _api_payload_from_predict(f"query_{gate}", gate, level, p, gate_name(gate))
    resp = jsonify(payload)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

@app.route("/api/baccarat", methods=["GET", "OPTIONS"])
def api_baccarat_direct():
    if request.method == "OPTIONS":
        resp = jsonify({"ok": True})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        return resp
    level = str(request.args.get("level") or "pro").lower()
    hist = request.args.get("history", "")
    p = predict_nomd5("bcr", level, hist)
    payload = _api_payload_from_predict("baccarat", "bcr", level, p, "Baccarat")
    resp = jsonify(payload)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

@app.route("/users", methods=["GET", "POST"])
def users():
    if not session.get("login"): return render_page("users", "")
    msg = ""
    if request.method == "POST":
        uid = request.form.get("uid","").strip()
        action = request.form.get("action")
        if uid in db.get("users", {}):
            u = db["users"][uid]
            try: amount = int(request.form.get("amount",0) or 0)
            except Exception: amount = 0
            if action == "add":
                u["balance"] = int(u.get("balance",0)) + amount
                msg = f"Đã cộng {money(amount)}"
            elif action == "set":
                u["balance"] = amount
                msg = f"Đã set {money(amount)}"
            elif action == "delete":
                stop_all_live_by_user(uid)
                db["users"].pop(uid, None)
                msg = "Đã xóa user"
            elif action == "plan_set":
                pk = request.form.get("plan_key", "basic")
                try: seconds = int(request.form.get("plan_seconds",0) or 0)
                except Exception: seconds = 0
                if pk in ("basic","pro"):
                    u.setdefault("plan_expires", {"basic":0,"pro":0})
                    if seconds <= 0:
                        u["plan_expires"][pk] = 0
                        if u.get("selected_plan") == pk: u["selected_plan"] = best_available_plan(u)
                        if u.get("active_plan") == pk: u["active_plan"] = best_available_plan(u)
                        msg = f"Đã tắt gói {pk} của user"
                    else:
                        u["plan_expires"][pk] = int(time.time()) + seconds
                        u["selected_plan"] = pk
                        u["active_plan"] = pk
                        u["plan_expire"] = plan_expire_ts(u)
                        msg = f"Đã set hạn gói {pk}: {duration_label(seconds)}"
                    stop_all_live_by_user(uid)
                    reset_live_streak(uid)
            elif action == "plan_clear_all":
                u["plan_expires"] = {"basic":0,"pro":0}
                u["active_plan"] = None
                u["selected_plan"] = None
                u["plan_expire"] = 0
                stop_all_live_by_user(uid)
                reset_live_streak(uid)
                msg = "Đã xóa toàn bộ gói của user"
            save_db()
    rows = ""
    quick_opts = [(3600,"1 giờ"),(6*3600,"6 giờ"),(24*3600,"1 ngày"),(7*24*3600,"7 ngày"),(30*24*3600,"30 ngày"),(0,"Tắt gói")]
    for u in reversed(list(db.get("users", {}).values())):
        uid = u.get("id")
        opts = ''.join([f"<option value='{sec}'>{lab}</option>" for sec,lab in quick_opts])
        rows += f"""<tr>
        <td><code>{uid}</code></td><td>@{u.get('username')}</td><td>{money(u.get('balance',0))}</td>
        <td>Đang chọn: <b>{u.get('selected_plan') or '-'}</b><br>Active: <b>{u.get('active_plan') or '-'}</b></td>
        <td>⭐ {remaining_time_text(u,'basic')}<br>💎 {remaining_time_text(u,'pro')}</td>
        <td>
          <form method="post" class="row" style="gap:6px;flex-wrap:wrap">
            <input type="hidden" name="uid" value="{uid}">
            <input style="width:120px;margin:0" type="number" name="amount" placeholder="Số tiền">
            <button name="action" value="add" class="btn green">Cộng</button>
            <button name="action" value="set" class="btn yellow">Set tiền</button>
          </form>
          <form method="post" class="row" style="gap:6px;flex-wrap:wrap;margin-top:6px">
            <input type="hidden" name="uid" value="{uid}">
            <select name="plan_key" style="width:110px"><option value="basic">Thường</option><option value="pro">Pro</option></select>
            <select name="plan_seconds" style="width:120px">{opts}</select>
            <button name="action" value="plan_set" class="btn pri">Set gói</button>
            <button name="action" value="plan_clear_all" class="btn red" onclick="return confirm('Xóa toàn bộ gói user này?')">Xóa gói</button>
            <button name="action" value="delete" class="btn red" onclick="return confirm('Xóa user?')">Xóa user</button>
          </form>
        </td></tr>"""
    note = "<p class='mut'>Set/xóa gói sẽ tự tắt mọi phiên phân tích đang chạy của user đó để tránh dính chuỗi/thông báo cũ.</p>"
    return render_page("users", f"<div class='top'><div class='title'>👥 Users & Gói</div></div><div class='card'>{note}<table><tr><th>ID</th><th>User</th><th>Số dư</th><th>Gói</th><th>Hạn</th><th>Hành động</th></tr>{rows}</table></div>", msg)

@app.route("/admins", methods=["GET", "POST"])
def admins_page():
    if not session.get("login"): return render_page("admins", "")
    msg = ""
    if request.method == "POST":
        action = request.form.get("action")
        aid = request.form.get("admin_id", "").strip()
        if action == "add" and aid:
            if aid not in [str(x) for x in cfg.get("admin_ids", [])]:
                cfg.setdefault("admin_ids", []).append(aid)
                save_cfg()
                msg = "Đã thêm admin Telegram ID."
            else:
                msg = "ID này đã tồn tại."
        if action == "remove" and aid:
            cfg["admin_ids"] = [str(x) for x in cfg.get("admin_ids", []) if str(x) != aid]
            save_cfg()
            msg = "Đã xóa admin Telegram ID."
    rows = ""
    for aid in cfg.get("admin_ids", []):
        rows += (
            f"<tr><td><code>{aid}</code></td>"
            f"<td><form method='post'><input type='hidden' name='admin_id' value='{aid}'>"
            f"<button class='btn red' name='action' value='remove' onclick=\"return confirm('Xóa admin này?')\">Xóa</button></form></td></tr>"
        )
    content = f"""
    <div class='top'><div class='title'>👑 Admin Telegram IDs</div></div>
    <div class='grid2'>
      <div class='card'>
        <h2>➕ Thêm admin</h2>
        <form method='post'>
          <label>Telegram User ID</label>
          <input name='admin_id' placeholder='VD: 123456789'>
          <button class='btn pri' name='action' value='add'>Thêm admin</button>
        </form>
        <p class='mut'>Admin ID trong danh sách này mới nhận thông báo đơn nạp và mới bấm được Duyệt/Từ chối trên Telegram.</p>
      </div>
      <div class='card'>
        <h2>📋 Danh sách admin</h2>
        <table><tr><th>ID</th><th>Hành động</th></tr>{rows}</table>
      </div>
    </div>
    """
    return render_page("admins", content, msg)

@app.route("/deposits")
def deposits():
    if not session.get("login"): return render_page("deposits", "")
    msg = request.args.get("msg","")
    rows = ""
    for o in reversed(db["deposits"]):
        action_html = ""
        if o.get("status") == "pending":
            action_html = (
                f"<a class='btn green' href='/approve_deposit/{o.get('id')}'>Duyệt</a> "
                f"<a class='btn red' href='/reject_deposit/{o.get('id')}' onclick=\"return confirm('Từ chối đơn này?')\">Từ chối</a>"
            )
        rows += (
            f"<tr><td><code>{o.get('id')}</code></td>"
            f"<td>{html.escape(display_user_full(o.get('user_id'), o.get('username','')))}</td>"
            f"<td>{money(o.get('amount',0))}</td>"
            f"<td><span class='badge'>{o.get('status')}</span></td>"
            f"<td>{o.get('time')}</td><td>{action_html}</td></tr>"
        )
    return render_page("deposits", f"<div class='top'><div class='title'>💰 Đơn nạp</div></div><div class='card'><table><tr><th>Mã</th><th>User</th><th>Số tiền</th><th>TT</th><th>Thời gian</th><th>Hành động</th></tr>{rows}</table></div>", msg)

@app.route("/approve_deposit/<oid>")
def web_approve_deposit(oid):
    if not session.get("login"): return redirect("/")
    ok, msg = approve_deposit(oid, "web")
    return redirect("/deposits?msg=" + urllib.parse.quote(msg))

@app.route("/reject_deposit/<oid>")
def web_reject_deposit(oid):
    if not session.get("login"): return redirect("/")
    ok, msg = reject_deposit(oid, "web")
    return redirect("/deposits?msg=" + urllib.parse.quote(msg))

@app.route("/feedback")
def feedback_page():
    if not session.get("login"): return render_page("feedback", "")
    msg = request.args.get("msg","")
    rows = ""
    for fb in reversed(db["feedback"]):
        rows += f"<tr><td><code>{fb.get('id')}</code></td><td>{mask_user(fb.get('user_id'), fb.get('username',''))}</td><td>{fb.get('note','')}</td><td><span class='badge'>{fb.get('status')}</span></td><td>{fb.get('time')}</td><td>{'' if fb.get('status')=='approved' else f'<a class=\"btn green\" href=\"/approve_feedback/{fb.get('id')}\">Duyệt gửi nhóm</a>'}</td></tr>"
    return render_page("feedback", f"<div class='top'><div class='title'>📸 Feedback</div></div><div class='card'><table><tr><th>Mã</th><th>User</th><th>Ghi chú</th><th>TT</th><th>Thời gian</th><th></th></tr>{rows}</table></div>", msg)

@app.route("/approve_feedback/<fid>")
def web_approve_feedback(fid):
    if not session.get("login"): return redirect("/")
    ok, msg = approve_feedback(fid)
    return redirect("/feedback?msg=" + urllib.parse.quote(msg))

@app.route("/broadcast", methods=["GET","POST"])
def web_broadcast():
    if not session.get("login"): return render_page("broadcast", "")
    msg = ""
    if request.method == "POST":
        content = request.form.get("message","").strip()
        if content:
            db["announcements"].append({"message": content, "time": now_str()})
            save_db()
            sent = 0
            if bot:
                for uid in list(db["users"].keys()):
                    try:
                        bot.send_message(uid, "📣 <b>THÔNG BÁO</b>\n\n" + content)
                        sent += 1
                        time.sleep(0.04)
                    except Exception:
                        pass
            msg = f"Đã gửi {sent}/{len(db['users'])} users"
    anns = "".join([f"<p><span class='mut'>{a.get('time')}</span><br>{a.get('message')}</p>" for a in reversed(db["announcements"])])
    return render_page("broadcast", f"<div class='top'><div class='title'>📣 Thông báo</div></div><div class='grid2'><div class='card'><form method='post'><textarea name='message' placeholder='Nội dung thông báo'></textarea><button class='btn pri'>Gửi toàn bộ</button></form></div><div class='card'><h2>Lịch sử</h2>{anns}</div></div>", msg)



def export_backup_js_text():
    payload = backup_payload()
    return "// KingBot full backup JS - import trong Admin > Backup\nwindow.KINGBOT_FULL_BACKUP = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"

def parse_backup_upload(raw_text):
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("File backup rỗng")
    if "window.KINGBOT_FULL_BACKUP" in text:
        part = text.split("window.KINGBOT_FULL_BACKUP", 1)[1]
        part = part.split("=", 1)[1].strip()
        if part.endswith(";"):
            part = part[:-1]
        text = part.strip()
    elif "window.KINGBOT_BACKUP" in text:
        part = text.split("window.KINGBOT_BACKUP", 1)[1]
        part = part.split("=", 1)[1].strip()
        if part.endswith(";"):
            part = part[:-1]
        text = part.strip()
    data = json.loads(text)
    payload = data.get("payload") if isinstance(data, dict) and isinstance(data.get("payload"), dict) else data
    new_cfg = payload.get("config") if isinstance(payload, dict) else None
    new_db = payload.get("database") if isinstance(payload, dict) else None
    if not isinstance(new_cfg, dict) or not isinstance(new_db, dict):
        raise ValueError("Backup không đúng định dạng: cần có config và database")
    return new_cfg, new_db

@app.route("/backup_download.js")
def backup_download_js():
    if not session.get("login"):
        return redirect("/")
    resp = make_response(export_backup_js_text())
    resp.headers["Content-Type"] = "application/javascript; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=kingbot_full_backup.js"
    return resp

@app.route("/backup", methods=["GET","POST"])
def backup_page():
    if not session.get("login"): return render_page("backup", "")
    msg = ""
    if request.method == "POST":
        action = request.form.get("action")
        if action == "push":
            ok, msg = push_backup("manual")
            msg = ("✅ " if ok else "❌ ") + msg
        elif action == "pull":
            ok, msg = pull_backup()
            msg = ("✅ " if ok else "❌ ") + msg
        elif action == "import_js":
            f = request.files.get("backup_file")
            if not f:
                msg = "❌ Chưa chọn file backup .js/.json"
            else:
                try:
                    raw = f.read().decode("utf-8", "ignore")
                    new_cfg, new_db = parse_backup_upload(raw)
                    cfg.clear(); cfg.update(new_cfg)
                    db.clear(); db.update(new_db)
                    save_cfg(); save_db()
                    algo_cache.update({"hash": None, "ns": {}, "error": ""})
                    msg = "✅ Đã import backup JS/JSON, toàn bộ config + dữ liệu web đã khôi phục."
                except Exception as e:
                    msg = "❌ Lỗi import backup: " + html.escape(str(e))
    content = f"""
    <div class='top'><div class='title'>☁️ Backup Full Data</div><a class='btn cyan' href='/backup_download.js'>⬇️ Tải file backup JS</a></div>
    <div class='grid2'>
      <div class='card'>
        <h2>Backup JS full web</h2>
        <p class='mut'>Tải file JS để giữ toàn bộ dữ liệu: config, users, nạp tiền, feedback, lịch sử mua, thuật toán admin.</p>
        <div class='row'><a class='btn cyan' href='/backup_download.js'>⬇️ Tải kingbot_full_backup.js</a></div><br>
        <form method='post' enctype='multipart/form-data'>
          <label>Import file backup .js hoặc .json</label><input type='file' name='backup_file' accept='.js,.json,application/json,application/javascript'>
          <button class='btn pri' name='action' value='import_js' onclick="return confirm('Import sẽ ghi đè toàn bộ dữ liệu hiện tại. Tiếp tục?')">⬆️ Import khôi phục toàn bộ</button>
        </form>
      </div>
      <div class='card'>
        <h2>Infinity PHP Backup</h2>
        <p>URL: <code>{cfg.get('backup_url','')}</code></p>
        <p>Chu kỳ: <b>{cfg.get('backup_interval_seconds',120)}s</b></p>
        <form method='post' class='row'>
          <button class='btn green' name='action' value='push'>Đẩy backup ngay</button>
          <button class='btn yellow' name='action' value='pull'>Kéo backup mới nhất</button>
        </form>
        <p class='mut'>Up file backup.php lên Infinity. Điền URL + secret ở Cài đặt nếu muốn auto sync online.</p>
      </div>
    </div>
    """
    return render_page("backup", content, msg)

@app.route("/logs")
def logs():
    if not session.get("login"): return render_page("logs", "")
    txt = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()[-18000:]
    return render_page("logs", f"<div class='top'><div class='title'>🧾 Logs</div><a class='btn red' href='/clearlogs'>Xóa log</a></div><div class='card'><pre>{txt}</pre></div>")

@app.route("/clearlogs")
def clearlogs():
    if session.get("login"):
        open(LOG_FILE, "w", encoding="utf-8").close()
    return redirect("/logs")



# ==================== V114 PATCH: REAL PATTERN + BREAK-ROAD + EXPIRE LOCK + BCR FALLBACK ====================
# Patch này đặt cuối file trước khi bot/web start, override các hàm cũ mà không đổi giao diện bot.

def _history_bits(history):
    """Đọc history đa game: TX/11/1-2..., Baccarat B/P/T. Trả cũ -> mới, bỏ Tie/Hòa."""
    if not history:
        return []
    out=[]
    if isinstance(history, str):
        raw=history.strip().upper()
        # Baccarat/result compact: PBPBBT hoặc B P B P
        if re.fullmatch(r"[BPTHOÀA\s,;|/\-_.]+", raw or "") and any(c in raw for c in "BP"):
            for ch in re.findall(r"BANKER|PLAYER|TIE|B|P|T|HÒA|HOA", raw):
                if ch in ("B","BANKER"):
                    out.append(1)
                elif ch in ("P","PLAYER"):
                    out.append(0)
                # TIE/HÒA bỏ qua để không phá nhịp cầu
            return out[-800:]
        # TX compact: TXXTT hoặc 101001
        for token in re.findall(r"TÀI|TAI|XỈU|XIU|BIG|SMALL|[TX10]", raw):
            if token in ("TÀI","TAI","BIG","T","1"):
                out.append(1)
            elif token in ("XỈU","XIU","SMALL","X","0"):
                out.append(0)
        return out[-800:]
    for x in history:
        if isinstance(x, dict):
            r=str(x.get("result", x.get("taixiu", x.get("prediction", x.get("winner", ""))))).upper()
            b=_history_bits(r)
            if b:
                out += b[-1:]
            continue
        t=str(x).strip().upper()
        if t in ("T", "TAI", "TÀI", "1", "BIG", "B", "BANKER"):
            out.append(1)
        elif t in ("X", "XIU", "XỈU", "0", "SMALL", "S", "P", "PLAYER"):
            out.append(0)
    return out[-800:]


def _run_cycle_vote(seq):
    """Nhận đúng nhịp cầu A-B từ run-length: 1-1, 1-2, 2-2, 1-3... và tự quyết giữ/bẻ."""
    seq=_as_old_to_new(seq)
    if len(seq) < 6:
        return None,0.0,""
    runs=_runs(seq)
    if len(runs) < 3:
        return None,0.0,""
    vals=[x for x,_ in runs]
    lens=[n for _,n in runs]
    last_side=vals[-1]; last_len=lens[-1]
    best=(None,0.0,"")
    # Chu kỳ 2 run là quan trọng nhất: 1-2, 2-2, 1-3, 3-1...
    for cyc in range(2, min(6, len(lens))+1):
        tail=lens[-cyc:]
        if not all(1 <= x <= 12 for x in tail):
            continue
        # check các block phía trước, cho phép run cuối đang dở <= expected
        checks=[]
        max_blocks=min(6, len(lens)//cyc)
        for j in range(1, max_blocks):
            block=lens[-cyc*(j+1):-cyc*j]
            if len(block)==cyc:
                ok=0; tot=0
                for idx,(a,b) in enumerate(zip(block,tail)):
                    tot+=1
                    if a==b or abs(a-b)<=1:
                        ok+=1
                checks.append(ok/max(1,tot))
        if not checks:
            continue
        ratio=sum(checks)/len(checks)
        # nếu chỉ có 1 block trước nhưng tail rõ vẫn nhận, tránh không hiện 1-2/2-2 khi ít lịch sử
        if len(checks)==1 and ratio>=0.50:
            ratio+=0.06
        if ratio < 0.54:
            continue
        expected=tail[-1]
        # Nếu run hiện tại chưa đủ độ dài expected -> giữ. Đủ/vượt expected -> bẻ sang bên kia.
        if last_len < expected:
            bit=last_side
            mode="giữ"
        else:
            bit=0 if last_side else 1
            mode="bẻ"
        name="Cầu " + "-".join(map(str, tail))
        if cyc==2:
            a,b=tail
            if a==1 and b==1:
                name="Cầu 1-1"
            elif 1 <= a <= 8 and 1 <= b <= 8:
                name=f"Cầu {a}-{b}"
        strength=min(0.94, 0.44 + ratio*0.38 + min(len(checks),5)*0.035 + (0.06 if cyc==2 else 0))
        nm=f"{name} · {mode} cầu"
        if strength > best[1]:
            best=(bit,strength,nm)
    # Cầu bệt: chỉ bẻ khi dài quá, còn lại theo bệt; tránh bẻ ảo làm gãy liên tục.
    if len(runs):
        last_len=runs[-1][1]
        if last_len >= 10:
            cand=(0 if last_side else 1, min(0.90,0.55+last_len*0.025), f"Cầu bệt {last_len} · bẻ cầu")
            if cand[1] > best[1]: best=cand
        elif last_len >= 4:
            cand=(last_side, min(0.86,0.48+last_len*0.045), f"Cầu bệt {last_len} · giữ cầu")
            if cand[1] > best[1]: best=cand
    return best


def _run_signature(seq, max_tail_runs=10):
    seq=_as_old_to_new(seq)
    runs=_runs(seq)
    if not runs:
        return "Chưa đủ lịch sử",0.0,None
    lens=[n for _,n in runs[-max_tail_runs:]]
    if len(lens)>=2:
        a,b=lens[-2],lens[-1]
        if 1 <= a <= 12 and 1 <= b <= 12:
            # đo độ lặp cặp a-b ở đuôi
            pairs=[]
            for i in range(max(0,len(lens)-8), len(lens)-1, 2):
                pairs.append((lens[i],lens[i+1]))
            hit=sum(1 for x in pairs if x==(a,b))
            conf=min(0.92, 0.42 + hit*0.12 + min(len(seq),80)/450)
            if a==1 and b==1:
                return "Cầu 1-1", max(conf,0.72), (a,b)
            if hit>=1 or len(lens)<=4:
                return f"Cầu {a}-{b}", conf, (a,b)
    if runs[-1][1] >= 3:
        return f"Cầu bệt {runs[-1][1]}", min(0.88,0.48+runs[-1][1]*0.05), (runs[-1][1],0)
    return "Đa cầu tổng hợp",0.45,None


def _ultra_pattern_vote(bits, gate=None):
    """Engine V114: ưu tiên nhận cầu run-length thật + bẻ cầu có điều kiện + Markov/tail."""
    seq=_as_old_to_new(bits)
    if len(seq)<5:
        return 0,0.0,"Chưa đủ lịch sử",[]
    gate=normalize_gate(gate or '')
    tune=GATE_TUNING.get(gate, {'markov':1.0,'pattern':1.0,'cycle':1.0,'tail':1.0})
    votes=[]; detail=[]
    last=seq[-1]
    runs=_runs(seq); last_run=runs[-1][1] if runs else 1
    cbit,cst,cname=_run_cycle_vote(seq)
    if cbit is not None:
        votes.append((1 if cbit else -1, cst, 1.55*tune.get('cycle',1), cname))
        detail.append((cname,cst))
    # pattern bank full 1-1..8-8, threshold thấp hơn một chút để hiện đúng tên cầu nhưng weight không quá ảo.
    best_pat=(None,0.0,None)
    for name,pat,w in ULTRA_RUN_PATTERNS:
        bit,ratio=_pattern_predict_from_tail(seq,pat)
        if ratio>best_pat[1]: best_pat=(name,ratio,bit)
        if bit is not None and ratio>=0.62:
            st=(ratio-0.50)*1.55
            votes.append((1 if bit else -1, st, w*tune.get('pattern',1), name))
    if best_pat[0]: detail.append((best_pat[0],best_pat[1]))
    # Bẻ cầu: chỉ bẻ khi quá nhịp/run quá dài hoặc vừa có dấu đảo sau chuỗi; không bẻ non.
    if last_run>=10:
        votes.append((-1 if last else 1,0.62,1.15*tune.get('tail',1),f"Bẻ cầu bệt {last_run}"))
        detail.append((f"Bẻ cầu bệt {last_run}",0.62))
    elif last_run>=4:
        votes.append((1 if last else -1,0.44+min(last_run,8)*0.035,0.92*tune.get('tail',1),f"Giữ cầu bệt {last_run}"))
    # Markov
    mv,ms=_nomd5_markov_vote(seq)
    if ms>=0.025:
        votes.append((mv,ms,1.25*tune.get('markov',1),"Markov tự học"))
        detail.append(("Markov",ms))
    # Tail replay: tìm đoạn đuôi từng xuất hiện và xem ván kế tiếp
    best_tail=None
    for L in range(2, min(28,len(seq)//2)+1):
        tail=seq[-L:]
        hits=[]
        for i in range(0,len(seq)-L):
            if seq[i:i+L]==tail and i+L < len(seq): hits.append(seq[i+L])
        if len(hits)>=2:
            p=(sum(hits)+1)/(len(hits)+2)
            st=min(0.95,len(hits)/10)*abs(p-0.5)*2
            if st>=0.08:
                nm=f"Lặp đuôi L{L}"
                votes.append((1 if p>=0.5 else -1,st,1.0+min(L,18)/32,nm))
                if best_tail is None or st>best_tail[1]: best_tail=(nm,st)
    if best_tail: detail.append(best_tail)
    if not votes:
        sig,sc,_=_run_signature(seq)
        return 0,0.0,sig,detail
    score=sum(v*st*w for v,st,w,_ in votes)
    den=sum(st*w for _,st,w,_ in votes) or 1
    side=1 if score>=0 else -1
    agree=min(1.0,abs(score)/den)
    same=[(nm,st*w) for v,st,w,nm in votes if v==side]
    same.sort(key=lambda x:x[1], reverse=True)
    cname=same[0][0] if same else _run_signature(seq)[0]
    return side,agree,cname,detail[:5]


def _tail_backtest_rate(seq, max_checks=60):
    seq=_as_old_to_new(seq)
    if len(seq)<16:
        return None,0
    start=max(8,len(seq)-max_checks)
    hit=0; total=0
    for i in range(start,len(seq)):
        train=seq[:i]
        side,agree,_,_=_ultra_pattern_vote(train,None)
        if not side or agree<0.10:
            continue
        pred=1 if side>0 else 0
        hit += 1 if pred==seq[i] else 0
        total += 1
    if total<8:
        return None,total
    return hit/total,total


def detect_bridge_type(seq, gate=None, predicted=None):
    seq=_as_old_to_new(seq)[-180:]
    if len(seq)<5:
        return "Chưa đủ lịch sử"
    gate=normalize_gate(gate or '')
    side,agree,cname,detail=_ultra_pattern_vote(seq,gate)
    pct=int(round(max(0,agree)*100))
    if gate=='bcr':
        cname=str(cname).replace('TÀI','Banker').replace('XỈU','Player')
        cname=cname.replace('bệt 1','bệt Banker') if False else cname
        if cname.startswith('Cầu 1-1'):
            cname='Cầu Ping Pong 1-1'
    return f"{cname} · khớp {pct}%" if cname else "Đa cầu tổng hợp"


def _build_manual_api_payload(gate, history, level='pro'):
    """Fallback khi API cổng lỗi nhưng HTML truyền history=...; vẫn trả phiên/pattern chuẩn."""
    gate=normalize_gate(gate)
    hb=_bcr_result_seq_to_bits(history) if gate=='bcr' else _history_bits(history)
    hb=_as_old_to_new(hb)
    if len(hb)<5:
        return None
    last_period=f"MANUAL-{len(hb)}"
    return {
        'period': last_period,
        'next_period': f"MANUAL-{len(hb)+1}",
        'last_period': last_period,
        'history_bits': list(reversed(hb[-120:])), # giống API: latest first
        'history_items': [],
        'prediction': ('BANKER' if hb[-1] else 'PLAYER') if gate=='bcr' else ('TÀI' if hb[-1] else 'XỈU'),
        'total': None,
        'dice': None,
        'confidence': 55,
        'table': 'manual',
        'source_url': 'history-param'
    }


def predict_nomd5(gate="lc79", level="basic", history=None):
    gate=normalize_gate(gate)
    level=str(level or 'basic').lower()
    external_hb=(_bcr_result_seq_to_bits(history) if gate=='bcr' else _history_bits(history))[-600:] if history else []
    ok,api=_fetch_nomd5_api(gate)
    if not ok:
        manual=_build_manual_api_payload(gate,history,level) if history else None
        if manual:
            ok=True; api=manual
        else:
            return {
                "engine":"V114 REAL-AI", "game":gate.upper(), "period":"API-LỖI", "taixiu":"ĐANG CHỜ", "tx_conf":0,
                "prob_tai":"0%", "prob_xiu":"0%", "prob_tie":"0%" if gate=='bcr' else "", "dice":"?-?-?", "total":"?", "chanle":"?", "score":0,
                "trend":"API cổng này đang lỗi", "advice":"⏸️ BỎ QUA", "stake_level":0,
                "risk":"CAO", "risk_emoji":"🔴", "details":["API lỗi", str(api.get('error',''))[:80]],
                "history_len":len(external_hb), "vote_agree":0, "hash_short":"NO-MD5",
                "advice_reason":"API chưa trả phiên thật. Với HTML có thể truyền ?history=TXXT hoặc ?history=PBPB để dự đoán fallback.",
                "bridge_type":"API lỗi", "streak":current_streak_text(gate,level), "level":level, "latest_actual":""
            }
    api_desc=list(api.get('history_bits') or [])
    api_old=list(reversed(api_desc))
    hb=(external_hb + api_old)[-700:]
    latest_actual=''
    try:
        latest_item=(api.get('history_items') or [{}])[0]
        latest_actual=_norm_bcr(latest_item.get('prediction')) if gate=='bcr' else (_norm_tx(latest_item.get('prediction')) or _tx_from_total(latest_item.get('total')))
    except Exception:
        latest_actual=''
    # Hội đồng mới: pattern/run-cycle là lõi, consensus cũ chỉ phụ nhẹ theo phiên.
    side,agreement,cname,detail=_ultra_pattern_vote(hb,gate)
    result='TÀI' if side>=0 else 'XỈU'
    period=str(api.get('next_period') or _next_period_value(api.get('period')))
    last_period=str(api.get('period') or api.get('last_period') or 'ĐANG-CẬP-NHẬT')
    seed=f"V114|{gate}|{level}|{period}|{last_period}|{''.join(map(str,hb[-240:]))}"
    # Pha phiên chỉ làm tie-break khi đồng thuận quá yếu, không đảo bừa.
    if agreement < 0.16:
        hv=1 if stable_int(seed,'phase',mod=100)>=50 else -1
        result='TÀI' if hv>0 else 'XỈU'
        agreement=max(agreement,0.12)
        cname='Cầu yếu / phiên hỗn hợp'
    if gate=='bcr':
        bcr_vote,bcr_strength=_baccarat_side_vote(hb)
        if bcr_vote and bcr_strength > agreement:
            result='TÀI' if bcr_vote=='BANKER' else 'XỈU'
            agreement=bcr_strength
        tie_gate=stable_int(seed,'bcr-tie',mod=100)
        if tie_gate < (2 if level=='pro' else 1) and agreement < 0.55:
            result='TIE'
        else:
            result='BANKER' if result=='TÀI' else 'PLAYER'
    if gate=='bcr':
        total='-'; dice_arr=[]
    elif result=='TÀI':
        total=11+stable_int(seed,'totalT',mod=8)
        dice_arr=_dice_from_total_seed(total,seed) or [4,4,4]
        total=sum(dice_arr)
    else:
        total=3+stable_int(seed,'totalX',mod=8)
        dice_arr=_dice_from_total_seed(total,seed) or [2,3,5]
        total=sum(dice_arr)
    bt_rate,bt_n=_tail_backtest_rate(hb,60)
    tune_cap=GATE_TUNING.get(gate,{})
    level_cap={'free':64,'basic':int(tune_cap.get('cap_basic',73)),'pro':int(tune_cap.get('cap_pro',80))}.get(level,73)
    if bt_rate is not None:
        conf=int(round(bt_rate*100*0.70 + (50+agreement*24)*0.30))
        if bt_n<18: conf-=3
    else:
        conf=int(round(50+agreement*22))
    hist_len=len(hb)
    if hist_len<8: conf=min(conf-8,58)
    elif hist_len<20: conf=min(conf-4,64)
    conf=int(_clamp(conf,45 if level=='free' else 48,level_cap))
    if gate=='bcr':
        tie_pct=5 if result!='TIE' else max(8,min(16,conf))
        remain=100-tie_pct
        if result=='BANKER':
            prob_t=conf; prob_x=max(1,remain-prob_t)
        elif result=='PLAYER':
            prob_x=conf; prob_t=max(1,remain-prob_x)
        else:
            prob_t=remain//2; prob_x=remain-prob_t
        prob_t=int(_clamp(prob_t,1,94)); prob_x=int(_clamp(prob_x,1,94)); prob_tie=int(_clamp(100-prob_t-prob_x,3,20))
        score=round(max(prob_t,prob_x,prob_tie)+stable_int(seed,'score',mod=300)/100,2)
    elif result=='TÀI':
        prob_t,prob_x=conf,100-conf; prob_tie=''; score=round(prob_t+stable_int(seed,'score',mod=300)/100,2)
    else:
        prob_x,prob_t=conf,100-conf; prob_tie=''; score=round(prob_x+stable_int(seed,'score',mod=300)/100,2)
    return {
        "engine":"V114 REAL-AI ALL-GAME", "game":gate.upper(), "period":period, "last_period":last_period, "table":api.get('table'),
        "taixiu":result, "tx_conf":conf,
        "prob_tai":f"{prob_t}%", "prob_xiu":f"{prob_x}%", "prob_tie":(f"{prob_tie}%" if gate=='bcr' else ""),
        "dice":("-" if gate=='bcr' else "-".join(map(str,dice_arr[:3]))), "total":total,
        "chanle":("-" if gate=='bcr' else ("CHẴN" if isinstance(total,int) and total%2==0 else "LẺ")), "score":score,
        "trend":"API thật + nhận cầu A-B + bẻ cầu có điều kiện + Markov", "advice":"✅ NÊN THEO" if conf>=70 else "⚖️ CÂN NHẮC" if conf>=58 else "⏸️ BỎ QUA",
        "stake_level":2 if conf>=70 else 1 if conf>=58 else 0,
        "risk":"THẤP" if conf>=66 else "TRUNG BÌNH" if conf>=56 else "CAO",
        "risk_emoji":"🟢" if conf>=66 else "🟡" if conf>=56 else "🔴",
        "details":["API thật" if api.get('source_url')!='history-param' else "History param", "Nhận cầu A-B", "Bẻ cầu", "Markov", gate_name(gate)],
        "history_len":hist_len, "vote_agree":round(agreement*10,1), "backtest_rate":(round(bt_rate*100,1) if bt_rate is not None else None), "backtest_n":bt_n,
        "hash_short":"NO-MD5", "advice_reason":"% là backtest gần nhất + đồng thuận hiện tại; không buff ảo.",
        "bridge_type":detect_bridge_type(hb,gate,result), "streak":current_streak_text(gate,level), "level":level, "latest_actual":latest_actual
    }

# Chặn lỗi hết giờ vẫn dùng: live API tự dừng khi gói hết hạn, không cho refresh tiếp.
_old_start_nomd5_live = start_nomd5_live
def stop_all_live_by_user(uid):
    uid = str(uid)
    try:
        for k, job in list(_nomd5_live_jobs.items()):
            if str(job.get("uid")) == uid:
                job["alive"] = False
    except Exception:
        pass

def start_nomd5_live(bot_obj, chat_id, message_id, uid, gate, plan):
    uid=str(uid); gate=normalize_gate(gate); plan=str(plan or 'basic')
    def worker():
        last_text=None; last_pred=None
        for _ in range(240):
            try:
                user=db.get('users',{}).get(uid,{})
                if plan in ('basic','pro') and not has_active_plan(user,plan):
                    try:
                        bot_obj.edit_message_text("⛔ <b>Gói đã hết hạn</b>\n\nBấm /start để mua/chọn lại gói mới.", chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return
                if plan=='free' and not free_is_active():
                    try:
                        bot_obj.edit_message_text("⛔ <b>Free mode đã hết thời gian</b>\n\nBấm /start để chọn gói khác.", chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return
                hist=recent_history_for_gate(gate or '',500)
                p=predict_nomd5(gate,plan,hist)
                if last_pred and p.get('last_period') and str(p.get('last_period')) == str(last_pred.get('period')):
                    actual=p.get('latest_actual') or p.get('taixiu')
                    pred=last_pred.get('result')
                    if actual and pred and actual not in ('ĐANG CHỜ',''):
                        win=(str(actual).upper()==str(pred).upper())
                        # báo xong mới cộng chuỗi
                        try:
                            tmp=bot_obj.send_message(chat_id, ("✅" if win else "❌") + f" <b>Phiên {last_pred.get('period')}</b> {'thắng' if win else 'thua'} · Dự đoán: <b>{pred}</b> · KQ: <b>{actual}</b>", parse_mode='HTML')
                            db.setdefault('prediction_checks',[]).append({'user_id':uid,'gate':gate,'plan':plan,'period':last_pred.get('period'),'predict':pred,'actual':actual,'win':win,'time':now_str()})
                            update_live_streak(uid,gate,plan,win)
                            save_db()
                        except Exception as e:
                            log(f'gửi/chốt thắng thua lỗi {gate}: {e}')
                        last_pred=None
                p['streak']=current_streak_text(gate,plan,uid)
                text=format_nomd5_reply(gate,p)
                if text!=last_text:
                    bot_obj.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Quay lại chọn cổng", callback_data="mode_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home")))
                    last_text=text
                if p.get('period') and p.get('taixiu') not in ('ĐANG CHỜ',''):
                    last_pred={'period':p.get('period'),'result':p.get('taixiu')}
            except Exception as e:
                log(f'API live update V114 lỗi {gate}: {e}')
            time.sleep(5)
    threading.Thread(target=worker,daemon=True).start()




# ===================== V116 REAL CAU ENGINE + 3S NOTICE DELETE =====================
# Ghi đè phần API/no-MD5 ở cuối file để nâng nhận cầu 1-1, 1-2, 2-2, 1-3..., bẻ cầu có điều kiện,
# tính % theo backtest thật và tự xóa thông báo thắng/thua sau 3 giây.

def _v116_to_old(bits):
    return _as_old_to_new(bits)[-900:]

def _v116_make_run_pattern(a, b, start=1, repeat=8):
    other = 0 if start else 1
    return ([start] * a + [other] * b) * repeat

def _v116_run_patterns(maxn=12):
    pats=[]
    hot={(1,1),(1,2),(2,1),(2,2),(1,3),(3,1),(2,3),(3,2),(1,4),(4,1)}
    for a in range(1,maxn+1):
        for b in range(1,maxn+1):
            w=1.38 if (a,b) in hot else 1.08
            pats.append((f"Cầu {a}-{b}", _v116_make_run_pattern(a,b,1,8), w, (a,b)))
            pats.append((f"Cầu {a}-{b} X", _v116_make_run_pattern(a,b,0,8), w, (a,b)))
    for combo in ((1,2,1),(2,1,2),(1,3,1),(3,1,3),(1,2,2),(2,2,1),(1,3,2),(2,3,1),(3,2,1),(2,3,2),(3,2,3)):
        pat=[]; cur=1
        for n in combo*4:
            pat += [cur]*n; cur = 0 if cur else 1
        pats.append(("Cầu " + "-".join(map(str,combo)), pat, 1.16, combo))
        pat=[]; cur=0
        for n in combo*4:
            pat += [cur]*n; cur = 0 if cur else 1
        pats.append(("Cầu " + "-".join(map(str,combo)) + " X", pat, 1.16, combo))
    return pats

V116_PATTERNS = _v116_run_patterns(12)

V116_GATE_TUNE = {
    'hitclub': {'markov':1.28,'pattern':1.26,'tail':1.10,'cap_pro':82,'cap_basic':74},
    'b52':     {'markov':1.22,'pattern':1.30,'tail':1.12,'cap_pro':82,'cap_basic':74},
    'lc79':    {'markov':1.18,'pattern':1.24,'tail':1.10,'cap_pro':81,'cap_basic':73},
    'sunwin':  {'markov':1.22,'pattern':1.24,'tail':1.12,'cap_pro':81,'cap_basic':73},
    'bcr':     {'markov':1.12,'pattern':1.30,'tail':1.08,'cap_pro':79,'cap_basic':72},
    'sicb52':  {'markov':1.18,'pattern':1.23,'tail':1.08,'cap_pro':80,'cap_basic':72},
    'sichit':  {'markov':1.20,'pattern':1.23,'tail':1.08,'cap_pro':80,'cap_basic':72},
}

def _v116_run_name(seq):
    seq=_v116_to_old(seq)
    runs=_runs(seq)
    if len(runs) < 2:
        return "Chưa đủ lịch sử", 0.0, None
    lens=[n for _,n in runs]
    sides=[b for b,_ in runs]
    last_len=lens[-1]
    if len(runs) >= 8 and all(sides[i] != sides[i-1] for i in range(1,len(sides))):
        # Đọc theo cặp gần nhất, ví dụ ... T X X T X X => 1-2, ... TT XX TT XX => 2-2.
        a,b=lens[-2],lens[-1]
        if 1 <= a <= 12 and 1 <= b <= 12:
            pairs=[]
            for i in range(max(0,len(lens)-10), len(lens)-1, 2):
                pairs.append((lens[i], lens[i+1]))
            target=(a,b)
            hits=sum(1 for x in pairs if x == target)
            near=sum(1 for x,y in pairs if abs(x-a)<=1 and abs(y-b)<=1)
            strength=min(0.95, 0.45 + hits*0.13 + near*0.045 + min(len(seq),120)/700)
            return f"Cầu {a}-{b}", strength, target
    if last_len >= 3:
        return f"Cầu bệt {last_len}", min(0.90, 0.48 + last_len*0.05), (last_len,0)
    if len(seq) >= 8 and all(seq[-i] != seq[-i-1] for i in range(1, min(8,len(seq)))):
        return "Cầu 1-1", 0.88, (1,1)
    return "Đa cầu tổng hợp", 0.42, None

def _v116_tail_repeat_vote(seq):
    seq=_v116_to_old(seq)
    votes=[]
    for L in range(2, min(26, len(seq)//2)+1):
        tail=seq[-L:]
        nxt=[]
        for i in range(0, len(seq)-L):
            if seq[i:i+L] == tail and i+L < len(seq):
                nxt.append(seq[i+L])
        if len(nxt) >= 2:
            p=(sum(nxt)+1)/(len(nxt)+2)
            st=min(1.0, len(nxt)/14.0) * abs(p-0.5)*2
            if st >= 0.075:
                votes.append((1 if p >= 0.5 else -1, st, 1.0+min(L,20)/32, f"Tự học L{L}"))
    return votes

def _v116_bridge_risk(seq, expected_pair=None):
    seq=_v116_to_old(seq)
    runs=_runs(seq)
    if not runs:
        return None
    last=runs[-1][0]; last_len=runs[-1][1]
    if expected_pair and len(expected_pair)>=2:
        exp=int(expected_pair[-1] or 1)
        # Nếu run hiện tại vượt nhịp cầu rõ ràng mới bẻ.
        if last_len >= exp + 2 and last_len >= 4:
            return (0 if last else 1, min(0.74, 0.42 + (last_len-exp)*0.08), f"Bẻ cầu vượt nhịp {exp}->{last_len}")
    if last_len >= 10:
        return (0 if last else 1, 0.66, f"Bẻ cầu bệt quá dài {last_len}")
    return None

def _ultra_pattern_vote(bits, gate=None):
    seq=_v116_to_old(bits)
    if len(seq) < 6:
        return 0,0.0,"Chưa đủ lịch sử",[]
    gate=normalize_gate(gate or '')
    tune=V116_GATE_TUNE.get(gate, {'markov':1.0,'pattern':1.0,'tail':1.0})
    votes=[]; details=[]
    run_name, run_strength, pair = _v116_run_name(seq)

    # Pattern full cầu A-B là lõi chính.
    best=("Đa cầu tổng hợp",0.0,None,None)
    for name,pat,w,pair_pat in V116_PATTERNS:
        bit,ratio=_pattern_predict_from_tail(seq, pat)
        if ratio > best[1]:
            best=(name,ratio,bit,pair_pat)
        if bit is not None and ratio >= 0.60:
            st=(ratio-0.48)*1.45
            bonus=1.18 if any(x in name for x in ("1-1","1-2","2-2","1-3","3-1")) else 1.0
            votes.append((1 if bit else -1, st, w*bonus*tune.get('pattern',1), name))
    details.append((best[0], round(best[1],3)))

    # Run signature đặt tên cầu hiển thị, vote theo nhịp nếu đang chạy dở.
    if pair and pair[1] and run_strength >= 0.48:
        runs=_runs(seq); last=runs[-1][0]; last_len=runs[-1][1]
        expected=pair[-1]
        bit=last if last_len < expected else (0 if last else 1)
        votes.append((1 if bit else -1, run_strength, 1.42*tune.get('pattern',1), run_name))
        details.append((run_name, round(run_strength,3)))

    # Bẻ cầu có điều kiện, không bẻ non.
    br=_v116_bridge_risk(seq, pair or best[3])
    if br:
        bit,st,nm=br
        votes.append((1 if bit else -1, st, 1.20*tune.get('tail',1), nm))
        details.append((nm, round(st,3)))
    else:
        runs=_runs(seq); last=runs[-1][0]; last_len=runs[-1][1]
        if last_len >= 4:
            st=min(0.62, 0.38 + last_len*0.04)
            votes.append((1 if last else -1, st, 0.88*tune.get('tail',1), f"Giữ cầu bệt {last_len}"))

    # Markov theo cổng + tự học đoạn đuôi.
    try:
        mv,ms=_nomd5_markov_vote(seq)
        if ms >= 0.02:
            votes.append((mv, ms, 1.30*tune.get('markov',1), "Markov tự học"))
            details.append(("Markov", round(ms,3)))
    except Exception:
        pass
    votes += _v116_tail_repeat_vote(seq)

    if not votes:
        return 0,0.0,run_name,details[:5]
    score=sum(v*st*w for v,st,w,_ in votes)
    den=sum(st*w for _,st,w,_ in votes) or 1.0
    side=1 if score >= 0 else -1
    agree=min(1.0, abs(score)/den)
    same=[(nm,st*w) for v,st,w,nm in votes if v == side]
    cname=run_name
    if same:
        same.sort(key=lambda x:x[1], reverse=True)
        cname=same[0][0]
    # Nếu best pattern khớp cao, ưu tiên tên cầu dễ hiểu để user thấy đúng 1-2/2-2/1-3.
    if best[1] >= 0.64 and best[0] != "Đa cầu tổng hợp":
        cname=best[0].replace(" X","")
    return side, agree, cname, details[:5]

def detect_bridge_type(seq, gate=None, predicted=None):
    seq=_v116_to_old(seq)[-120:]
    if not seq:
        return "Chưa đủ lịch sử"
    name,score,_=_v116_run_name(seq)
    best_name,best_score,_,_= ("Đa cầu tổng hợp",0.0,None,None)
    for nm,pat,_,_pair in V116_PATTERNS:
        _bit,ratio=_pattern_predict_from_tail(seq, pat)
        if ratio > best_score:
            best_name,best_score=nm,ratio
    if best_score >= 0.60:
        return best_name.replace(" X","")
    if score >= 0.50:
        return name
    return "Cầu hỗn hợp / chờ thêm phiên"

def _v116_backtest_rate(seq, gate=None, max_checks=70):
    seq=_v116_to_old(seq)
    if len(seq) < 18:
        return None,0
    start=max(10, len(seq)-max_checks)
    hit=0; total=0
    for i in range(start, len(seq)):
        side,agree,_,_=_ultra_pattern_vote(seq[:i], gate)
        if abs(agree) < 0.10:
            continue
        pred=1 if side >= 0 else 0
        hit += 1 if pred == seq[i] else 0
        total += 1
    if total < 8:
        return None,total
    return hit/total,total

def predict_nomd5(gate="lc79", level="basic", history=None):
    gate=normalize_gate(gate)
    level=str(level or 'basic').lower()
    external_hb=(_bcr_result_seq_to_bits(history) if gate=='bcr' else _history_bits(history))[-700:] if history else []
    ok,api=_fetch_nomd5_api(gate)
    if not ok:
        manual=_build_manual_api_payload(gate,history,level) if history else None
        if manual:
            ok=True; api=manual
        else:
            return {
                "engine":"V116 REAL-CAU", "game":gate.upper(), "period":"API-LỖI", "last_period":"?", "taixiu":"ĐANG CHỜ", "tx_conf":0,
                "prob_tai":"0%", "prob_xiu":"0%", "prob_tie":"0%" if gate=='bcr' else "", "dice":"?-?-?", "total":"?", "chanle":"?", "score":0,
                "trend":"API cổng lỗi hoặc chưa cấu hình", "advice":"⏸️ BỎ QUA", "stake_level":0, "risk":"CAO", "risk_emoji":"🔴",
                "details":["API lỗi", str(api.get('error',''))[:100]], "history_len":len(external_hb), "vote_agree":0,
                "hash_short":"NO-MD5", "advice_reason":"Cấu hình API gốc hoặc truyền ?history=TXXT / ?history=PBPB để fallback.",
                "bridge_type":"API lỗi", "streak":current_streak_text(gate,level), "level":level, "latest_actual":""
            }
    api_desc=list(api.get('history_bits') or [])
    api_old=list(reversed(api_desc))
    hb=(external_hb + api_old)[-900:]
    latest_actual=''
    try:
        latest_item=(api.get('history_items') or [{}])[0]
        latest_actual=_norm_bcr(latest_item.get('prediction')) if gate=='bcr' else (_norm_tx(latest_item.get('prediction')) or _tx_from_total(latest_item.get('total')))
    except Exception:
        latest_actual=''
    side,agreement,cname,detail=_ultra_pattern_vote(hb,gate)
    result='TÀI' if side>=0 else 'XỈU'
    period=str(api.get('next_period') or _next_period_value(api.get('period')))
    last_period=str(api.get('period') or api.get('last_period') or 'ĐANG-CẬP-NHẬT')
    seed=f"V116|{gate}|{level}|{period}|{last_period}|{''.join(map(str,hb[-260:]))}|{cname}"
    if gate=='bcr':
        # Mapping Baccarat: TÀI = Banker, XỈU = Player trong engine nhị phân.
        if agreement < 0.12:
            result = 'BANKER' if stable_int(seed,'bcr-weak',mod=100) >= 50 else 'PLAYER'
        else:
            result = 'BANKER' if result == 'TÀI' else 'PLAYER'
        if stable_int(seed,'bcr-tie',mod=100) < 1 and agreement < 0.45:
            result='TIE'
        dice_arr=[]; total='-'
    else:
        if result=='TÀI':
            total=11+stable_int(seed,'totalT',mod=8)
        else:
            total=3+stable_int(seed,'totalX',mod=8)
        dice_arr=_dice_from_total_seed(total,seed) or ([4,4,4] if result=='TÀI' else [1,4,5])
        total=sum(dice_arr)
    bt_rate,bt_n=_v116_backtest_rate(hb,gate,70)
    tune=V116_GATE_TUNE.get(gate,{})
    cap={'free':62,'basic':int(tune.get('cap_basic',73)),'pro':int(tune.get('cap_pro',81))}.get(level,73)
    if bt_rate is not None:
        conf=int(round(bt_rate*100*0.76 + (50+agreement*26)*0.24))
        if bt_n < 18: conf -= 3
    else:
        conf=int(round(50+agreement*25))
    if len(hb) < 12: conf=min(conf-8,56)
    elif len(hb) < 25: conf=min(conf-4,64)
    conf=int(_clamp(conf, 44 if level=='free' else 47, cap))
    if gate=='bcr':
        tie_pct=4 if result!='TIE' else max(8,min(15,conf))
        remain=100-tie_pct
        if result=='BANKER':
            prob_t=conf; prob_x=max(1, remain-conf)
        elif result=='PLAYER':
            prob_x=conf; prob_t=max(1, remain-conf)
        else:
            prob_t=remain//2; prob_x=remain-prob_t
        prob_t=int(_clamp(prob_t,1,94)); prob_x=int(_clamp(prob_x,1,94)); prob_tie=int(_clamp(100-prob_t-prob_x,3,20))
        score=max(prob_t,prob_x,prob_tie)
    else:
        if result=='TÀI':
            prob_t,prob_x=conf,100-conf
        else:
            prob_x,prob_t=conf,100-conf
        prob_tie=''; score=max(prob_t,prob_x)
    return {
        "engine":"V116 REAL-CAU ALL-GAME", "game":gate.upper(), "period":period, "last_period":last_period, "table":api.get('table'),
        "taixiu":result, "tx_conf":conf,
        "prob_tai":f"{prob_t}%", "prob_xiu":f"{prob_x}%", "prob_tie":(f"{prob_tie}%" if gate=='bcr' else ""),
        "dice":("-" if gate=='bcr' else "-".join(map(str,dice_arr[:3]))), "total":total,
        "chanle":("-" if gate=='bcr' else ("CHẴN" if isinstance(total,int) and total%2==0 else "LẺ")), "score":round(float(score),2),
        "trend":"Nhận cầu A-B 1-1..12-12 + bẻ cầu có điều kiện + Markov riêng cổng",
        "advice":"✅ NÊN THEO" if conf>=69 else "⚖️ CÂN NHẮC" if conf>=57 else "⏸️ BỎ QUA",
        "stake_level":2 if conf>=69 else 1 if conf>=57 else 0,
        "risk":"THẤP" if conf>=66 else "TRUNG BÌNH" if conf>=56 else "CAO",
        "risk_emoji":"🟢" if conf>=66 else "🟡" if conf>=56 else "🔴",
        "details":["API gốc" if api.get('source_url')!='history-param' else "History param", cname, "Bẻ cầu có điều kiện", gate_name(gate)],
        "history_len":len(hb), "vote_agree":round(agreement*10,1), "backtest_rate":(round(bt_rate*100,1) if bt_rate is not None else None), "backtest_n":bt_n,
        "hash_short":"NO-MD5", "advice_reason":"% là backtest gần nhất + độ đồng thuận; không buff ảo.",
        "bridge_type":cname or detect_bridge_type(hb,gate,result), "streak":current_streak_text(gate,level), "level":level, "latest_actual":latest_actual
    }

def _schedule_delete_message(bot_obj, chat_id, message_id, delay=3):
    def _do_delete():
        try:
            bot_obj.delete_message(chat_id, message_id)
        except Exception as e:
            log(f"auto delete thông báo lỗi: {e}")
    try:
        threading.Timer(delay, _do_delete).start()
    except Exception:
        pass

# Live API: chốt xong gửi thông báo -> cộng chuỗi -> tự xóa sau 3s.
def start_nomd5_live(bot_obj, chat_id, message_id, uid, gate, plan):
    uid=str(uid); gate=normalize_gate(gate); plan=str(plan or 'basic')
    def worker():
        last_text=None; last_pred=None; closed_periods=set()
        for _ in range(360):
            try:
                user=db.get('users',{}).get(uid,{})
                if plan in ('basic','pro') and not has_active_plan(user,plan):
                    try:
                        bot_obj.edit_message_text("⛔ <b>Gói đã hết hạn</b>\n\nBấm /start để mua/chọn lại gói mới.", chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return
                if plan=='free' and not free_is_active():
                    try:
                        bot_obj.edit_message_text("⛔ <b>Free mode đã hết thời gian</b>\n\nBấm /start để chọn gói khác.", chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return
                hist=recent_history_for_gate(gate or '',700)
                p=predict_nomd5(gate,plan,hist)
                # Khi API báo last_period đúng bằng phiên đã dự đoán trước đó => chốt thắng/thua.
                if last_pred and p.get('last_period') and str(p.get('last_period')) == str(last_pred.get('period')):
                    period_key=str(last_pred.get('period'))
                    if period_key not in closed_periods:
                        actual=p.get('latest_actual') or p.get('taixiu')
                        pred=last_pred.get('result')
                        if actual and pred and actual not in ('ĐANG CHỜ',''):
                            win=(str(actual).upper()==str(pred).upper())
                            try:
                                tmp=bot_obj.send_message(chat_id, ("✅" if win else "❌") + f" <b>Phiên {period_key}</b> {'thắng' if win else 'thua'} · Dự đoán: <b>{pred}</b> · KQ: <b>{actual}</b>", parse_mode='HTML')
                                db.setdefault('prediction_checks',[]).append({'user_id':uid,'gate':gate,'plan':plan,'period':period_key,'predict':pred,'actual':actual,'win':win,'time':now_str()})
                                update_live_streak(uid,gate,plan,win)
                                save_db()
                                _schedule_delete_message(bot_obj, chat_id, tmp.message_id, 3)
                                closed_periods.add(period_key)
                            except Exception as e:
                                log(f'gửi/chốt thắng thua lỗi {gate}: {e}')
                    last_pred=None
                p['streak']=current_streak_text(gate,plan,uid)
                text=format_nomd5_reply(gate,p)
                if text != last_text:
                    try:
                        bot_obj.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Quay lại chọn cổng", callback_data="mode_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home")))
                    except Exception as e:
                        log(f'edit live lỗi {gate}: {e}')
                    last_text=text
                if p.get('period') and p.get('taixiu') not in ('ĐANG CHỜ',''):
                    last_pred={'period':p.get('period'),'result':p.get('taixiu')}
            except Exception as e:
                log(f'API live update V116 lỗi {gate}: {e}')
            time.sleep(5)
    threading.Thread(target=worker,daemon=True).start()

# ===================== END V116 OVERRIDE =====================


# ===================== V120 FIX FEEDBACK + UPGRADE CAU + CHILD BOT =====================
# V123: Feedback duyệt gửi theo LINK GROUP PUBLIC / @username / -100chatid.
# Lưu ý: link invite dạng https://t.me/+xxxx không thể gửi trực tiếp bằng Bot API; cần @username public hoặc -100chatid.
def _v123_group_target_for_feedback():
    raw = str(cfg.get('feedback_group_target') or cfg.get('group_link') or cfg.get('group_chat_id') or cfg.get('feedback_group_id') or '').strip()
    if not raw:
        return ''
    if raw.startswith('-100') or raw.lstrip('-').isdigit():
        return raw
    if raw.startswith('@'):
        return raw
    if 't.me/' in raw:
        tail = raw.split('t.me/', 1)[1].split('?', 1)[0].strip('/')
        if tail.startswith('+') or tail.startswith('joinchat/') or tail.startswith('c/'):
            return ''
        return '@' + tail.split('/')[0]
    return raw

def approve_feedback(fb_id):
    for fb in db.setdefault('feedback', []):
        if str(fb.get('id')) == str(fb_id):
            if fb.get('status') == 'approved':
                return False, 'Feedback đã duyệt rồi.'
            gid = _v123_group_target_for_feedback()
            if not gid:
                return False, 'Chưa cấu hình Link group public/@username/-100chatid. Link mời t.me/+... không gửi trực tiếp được.'
            if not bot:
                return False, 'Bot chính chưa chạy nên chưa gửi được feedback.'
            caption = (
                f"📸 <b>FEEDBACK MỚI</b>\n"
                f"👤 User: <b>{mask_user(fb.get('user_id'), fb.get('username',''))}</b>\n"
                f"📝 Ghi chú: {html.escape(str(fb.get('note','')))}"
            )
            try:
                photo_id = fb.get('photo_id') or ''
                if photo_id:
                    try:
                        bot.send_photo(gid, photo_id, caption=caption, parse_mode='HTML')
                    except Exception as e1:
                        log(f'Gửi ảnh feedback lỗi, fallback text {gid}: {e1}')
                        bot.send_message(gid, caption + f"\n🖼 Photo ID: <code>{html.escape(str(photo_id))}</code>", parse_mode='HTML', disable_web_page_preview=True)
                else:
                    bot.send_message(gid, caption, parse_mode='HTML', disable_web_page_preview=True)
                fb['status'] = 'approved'
                fb['approved_time'] = now_str()
                fb['sent_group'] = gid
                save_db()
                return True, f'Đã duyệt và gửi feedback vào group {gid}.'
            except Exception as e:
                log(f'Lỗi gửi feedback group V123 {gid}: {e}')
                return False, 'Không gửi được vào group. Hãy thêm bot vào group, cho quyền gửi tin nhắn/ảnh, dùng @group public hoặc -100chatid.'
    return False, 'Không tìm thấy feedback.'

# Đọc cầu kiểu run-length chuẩn: 1-1, 1-2, 2-2, 1-3... và bẻ cầu chỉ khi quá nhịp.
def _v120_best_run_pattern(seq):
    seq=_v116_to_old(seq)[-300:]
    runs=_runs(seq)
    if len(runs) < 4:
        return None
    lens=[n for _,n in runs]
    sides=[b for b,_ in runs]
    best=None
    # Kiểm tra pattern 2-run A-B, đọc cả 2 phase chẵn/lẻ để không lệch nhịp.
    for a in range(1,13):
        for b in range(1,13):
            pat=[a,b]
            for phase in (0,1):
                sub=lens[phase:]
                if len(sub)<4: continue
                check=sub[-min(len(sub),14):]
                hits=0; total=0; near=0
                for i,x in enumerate(check):
                    exp=pat[i%2]
                    total+=1
                    if x==exp: hits+=1
                    if abs(x-exp)<=1: near+=1
                score=(hits/max(total,1))*0.72 + (near/max(total,1))*0.20 + min(total,14)*0.006
                if total>=4 and (best is None or score>best[0]):
                    best=(score,a,b,phase,total)
    if not best: return None
    score,a,b,phase,total=best
    if score < 0.58:
        return None
    last_side,last_len=runs[-1]
    idx=(len(lens)-phase-1) % 2
    expected=[a,b][idx]
    # Nếu đang trong run chưa đủ nhịp thì giữ bên hiện tại; đủ/vượt nhịp thì đảo bên.
    if last_len < expected:
        pred=last_side
        action=f'giữ nhịp {last_len}/{expected}'
    elif last_len == expected:
        pred=0 if last_side else 1
        action='đủ nhịp, đảo bên'
    else:
        # bẻ cầu: chỉ khi vượt ít nhất 1, mạnh hơn khi vượt 2+
        pred=0 if last_side else 1
        action=f'bẻ cầu vượt nhịp {expected}->{last_len}'
        score=min(0.95, score + min(last_len-expected,3)*0.055)
    return {'name':f'Cầu {a}-{b}', 'score':score, 'pred':pred, 'expected':expected, 'last_len':last_len, 'action':action}

def _ultra_pattern_vote(bits, gate=None):
    seq=_v116_to_old(bits)
    if len(seq) < 8:
        return 0,0.0,'Chưa đủ lịch sử',[]
    gate=normalize_gate(gate or '')
    tune=V116_GATE_TUNE.get(gate, {'markov':1.0,'pattern':1.0,'tail':1.0})
    votes=[]; details=[]
    rp=_v120_best_run_pattern(seq)
    if rp:
        st=float(rp['score'])
        votes.append((1 if rp['pred'] else -1, st, 1.70*tune.get('pattern',1), rp['name'] + ' · ' + rp['action']))
        details.append((rp['name'], round(st,3), rp['action']))
    # cầu bệt thật: chỉ theo khi chưa quá dài; quá dài thì bẻ nhẹ.
    runs=_runs(seq); last_side,last_len=runs[-1]
    if last_len >= 3:
        if last_len <= 7:
            votes.append((1 if last_side else -1, min(0.62,0.34+last_len*0.045), 0.88*tune.get('tail',1), f'Cầu bệt {last_len}'))
        elif last_len >= 9:
            votes.append((1 if (0 if last_side else 1) else -1, min(0.70,0.42+last_len*0.025), 0.70*tune.get('tail',1), f'Bẻ cầu bệt {last_len}'))
    # pattern tail repeat tự học
    for v,st,w,nm in _v116_tail_repeat_vote(seq):
        if st>=0.09:
            votes.append((v,st,0.95*w,nm))
    # markov vừa phải, không cho lấn cầu chính.
    try:
        mv,ms=_nomd5_markov_vote(seq)
        if ms >= 0.035:
            votes.append((mv, min(ms,0.32), 0.85*tune.get('markov',1), 'Markov phụ'))
            details.append(('Markov phụ', round(ms,3)))
    except Exception:
        pass
    if not votes:
        return (1 if seq[-1] else -1),0.12,'Chờ cầu rõ',details
    score=sum(v*st*w for v,st,w,_ in votes)
    den=sum(st*w for _,st,w,_ in votes) or 1
    side=1 if score>=0 else -1
    agree=min(1.0,abs(score)/den)
    same=[(nm,st*w) for v,st,w,nm in votes if v==side]
    same.sort(key=lambda x:x[1], reverse=True)
    cname=same[0][0] if same else 'Đa cầu tổng hợp'
    return side,agree,cname,details[:6]

def detect_bridge_type(seq, gate=None, predicted=None):
    seq=_v116_to_old(seq)[-300:]
    rp=_v120_best_run_pattern(seq)
    if rp and rp['score']>=0.58:
        return rp['name'] + ' · ' + rp['action']
    runs=_runs(seq)
    if runs and runs[-1][1] >= 3:
        return f'Cầu bệt {runs[-1][1]}'
    if len(seq)>=10 and all(seq[-i]!=seq[-i-1] for i in range(1,min(10,len(seq)))):
        return 'Cầu 1-1'
    return 'Cầu hỗn hợp / chờ thêm phiên'

# Bot con độc lập: chỉ hiện admin sau khi nhập /adminkey đúng.
def _child_admin_text(bot_id):
    return ("👑 <b>ADMIN BOT CON</b>\n"
            "/users - xem user bot con\n"
            "/addbalance USER_ID SOTIEN - cộng tiền\n"
            "/setbalance USER_ID SOTIEN - set tiền\n"
            "/bank TEN|STK|CHU_TK - setting bank\n"
            "/plans - xem giá gói\n"
            "/broadcast nội dung - gửi toàn bot con\n"
            "/stats - thống kê bot con")

def _build_child_bot(token, bot_id):
    cb = telebot.TeleBot(token, parse_mode='HTML')
    try:
        cb.remove_webhook()
    except Exception as e:
        log(f'Bot con {bot_id} remove_webhook lỗi: {e}')

    def child_kb_home():
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('🎲 Dự đoán Tài Xỉu', callback_data='c_tx'))
        kb.add(InlineKeyboardButton('📡 API phiên', callback_data='c_api'))
        kb.add(InlineKeyboardButton('💰 Nạp tiền', callback_data='c_deposit'))
        return kb

    def child_user(uid, m=None):
        scope = _child_scope(bot_id)
        users = scope.setdefault('users', {})
        u = users.setdefault(str(uid), {'balance':0, 'joined':now_str()})
        if m is not None:
            u['first_name'] = getattr(m.from_user, 'first_name', '') or u.get('first_name','')
            u['username'] = getattr(m.from_user, 'username', '') or u.get('username','')
        return u

    def child_predict_from_text(raw):
        raw = (raw or '').strip()
        gate = 'hitclub'
        level = 'pro'
        # Hỗ trợ: /tx hitclub TTXTX hoặc /tx TTXTX
        parts = raw.split()
        history = ''
        if len(parts) >= 2:
            if normalize_gate(parts[1]) in cfg.get('gates', {}):
                gate = normalize_gate(parts[1])
                history = ''.join(parts[2:])
            else:
                history = ''.join(parts[1:])
        p = predict_nomd5(gate, level, history)
        return gate, p

    def child_format_predict(gate, p):
        # Bot con dùng chung card/giao diện với bot chính để không bị khác layout.
        try:
            p = dict(p or {})
            p['streak'] = p.get('streak') or '🔥 Chuỗi thắng: <b>0</b> · ❄️ Chuỗi thua: <b>0</b> · 📈 Tỉ lệ live: <b>0%</b>'
            return format_nomd5_reply(gate, p)
        except Exception:
            return (f"🔮 <b>DỰ ĐOÁN API TÀI/XỈU</b>\n\n"
                    f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                    f"📦 Phiên bản: <b>{globals().get('ENGINE_LABEL','Mới Nhất')}</b>\n"
                    f"➡️ Kết luận: <b>{html.escape(str(p.get('taixiu') or p.get('result') or 'ĐANG CHỜ'))}</b>\n"
                    f"🧬 Loại cầu: <b>{html.escape(str(p.get('bridge_type') or 'Đa cầu tổng hợp'))}</b>\n"
                    f"📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf', p.get('confidence', 50))}%</b>")

    @cb.message_handler(commands=['start'])
    def c_start(m):
        uid=str(m.from_user.id)
        child_user(uid, m)
        save_db()
        cb.reply_to(m, '🤖 <b>Bot Tài Xỉu đã sẵn sàng</b>\n\nDùng menu bên dưới hoặc gửi MD5 32 ký tự để dự đoán.\nAdmin nhập <code>/adminkey KEY</code> rồi dùng <code>/admin</code>.', reply_markup=child_kb_home())

    @cb.callback_query_handler(func=lambda c: str(c.data).startswith('c_'))
    def c_cb(c):
        uid=str(c.from_user.id)
        child_user(uid)
        data=c.data
        try:
            if data == 'c_tx':
                cb.answer_callback_query(c.id)
                cb.send_message(c.message.chat.id, '🎲 Gửi lịch sử dạng <code>/tx hitclub TTXTXTTX</code> hoặc gửi MD5 32 ký tự.')
            elif data == 'c_api':
                gate, p = 'hitclub', predict_nomd5('hitclub', 'pro', '')
                cb.answer_callback_query(c.id)
                cb.send_message(c.message.chat.id, child_format_predict(gate, p))
            elif data == 'c_deposit':
                cb.answer_callback_query(c.id)
                cb.send_message(c.message.chat.id, '💰 Tính năng nạp của bot con đang tách riêng data. Admin dùng /bank để set bank bot con.')
        except Exception as e:
            log(f'Bot con callback lỗi {bot_id}: {e}')

    @cb.message_handler(commands=['tx','predict'])
    def c_tx(m):
        child_user(m.from_user.id, m)
        gate, p = child_predict_from_text(m.text)
        save_db()
        cb.reply_to(m, child_format_predict(gate, p))

    @cb.message_handler(commands=['adminkey'])
    def c_key(m):
        uid=str(m.from_user.id); parts=(m.text or '').split(maxsplit=1)
        if len(parts)<2:
            cb.reply_to(m,'Sai cú pháp: <code>/adminkey KEY_ADMIN</code>'); return
        ok,msg=use_admin_key(uid, parts[1].strip(), bot_scope=bot_id)
        cb.reply_to(m,msg)

    @cb.message_handler(commands=['admin'])
    def c_admin(m):
        if not is_child_admin(m.from_user.id, bot_id):
            cb.reply_to(m,'❌ Chưa nhập key admin. Dùng: <code>/adminkey KEY</code>'); return
        cb.reply_to(m,_child_admin_text(bot_id))

    @cb.message_handler(commands=['stats'])
    def c_stats(m):
        if not is_child_admin(m.from_user.id, bot_id): return
        scope=_child_scope(bot_id); users=scope.get('users',{})
        cb.reply_to(m, f"📊 Users bot con: {len(users)}\n💰 Tổng số dư: {money(sum(int(u.get('balance',0)) for u in users.values()))}")

    @cb.message_handler(commands=['users'])
    def c_users(m):
        if not is_child_admin(m.from_user.id, bot_id): return
        users=_child_scope(bot_id).get('users',{})
        text='👥 <b>USERS BOT CON</b>\n'+'\n'.join([f"<code>{uid}</code> · {html.escape(str(u.get('username') or u.get('first_name') or ''))} · {money(u.get('balance',0))}" for uid,u in list(users.items())[:50]])
        cb.reply_to(m, text or 'Chưa có user')

    @cb.message_handler(commands=['addbalance','setbalance'])
    def c_balance(m):
        if not is_child_admin(m.from_user.id, bot_id): return
        p=(m.text or '').split()
        if len(p)!=3 or not p[2].lstrip('-').isdigit():
            cb.reply_to(m,'Sai cú pháp: /addbalance USER_ID SOTIEN hoặc /setbalance USER_ID SOTIEN'); return
        scope=_child_scope(bot_id); users=scope.setdefault('users',{})
        uid,amt=p[1],int(p[2]); users.setdefault(uid, {'balance':0,'joined':now_str()})
        if p[0].endswith('setbalance'):
            users[uid]['balance']=amt
        else:
            users[uid]['balance']=int(users[uid].get('balance',0))+amt
        scope.setdefault('transactions',[]).append({'type':p[0].strip('/'),'user_id':uid,'amount':amt,'time':now_str()}); save_db()
        cb.reply_to(m, f"✅ Số dư <code>{uid}</code>: {money(users[uid]['balance'])}")

    @cb.message_handler(commands=['bank'])
    def c_bank(m):
        if not is_child_admin(m.from_user.id, bot_id): return
        raw=(m.text or '').split(maxsplit=1)
        if len(raw)<2 or raw[1].count('|')<2:
            cb.reply_to(m,'Sai cú pháp: <code>/bank TEN_NGAN_HANG|STK|CHU_TK</code>'); return
        bank,stk,name=[x.strip() for x in raw[1].split('|',2)]
        _child_scope(bot_id)['bank']={'bank':bank,'account':stk,'name':name,'updated':now_str()}; save_db()
        cb.reply_to(m,'✅ Đã lưu bank cho bot con.')

    @cb.message_handler(commands=['plans'])
    def c_plans(m):
        if not is_child_admin(m.from_user.id, bot_id): return
        cb.reply_to(m, '<pre>'+html.escape(json.dumps(_child_scope(bot_id).get('plans', cfg.get('plans',{})), ensure_ascii=False, indent=2)[:3500])+'</pre>')

    @cb.message_handler(commands=['broadcast'])
    def c_bc(m):
        if not is_child_admin(m.from_user.id, bot_id): return
        raw=(m.text or '').split(maxsplit=1)
        if len(raw)<2: cb.reply_to(m,'Sai cú pháp: /broadcast nội dung'); return
        sent=0
        for uid in list(_child_scope(bot_id).get('users',{}).keys()):
            try: cb.send_message(uid, raw[1]); sent+=1
            except Exception: pass
        cb.reply_to(m, f'✅ Đã gửi {sent} user bot con.')

    @cb.message_handler(func=lambda m: True, content_types=['text'])
    def c_text(m):
        child_user(m.from_user.id, m)
        txt=(m.text or '').strip()
        if len(txt)==32 and all(ch in '0123456789abcdefABCDEF' for ch in txt):
            try:
                p = predict_md5(txt, 'pro') if 'predict_md5' in globals() else predict_nomd5('hitclub','pro',txt)
            except Exception:
                p = predict_nomd5('hitclub','pro',txt)
            cb.reply_to(m, child_format_predict('md5', p))
        elif set(txt.upper().replace(' ','')) <= set('TXPB') and len(txt.replace(' ','')) >= 6:
            p = predict_nomd5('hitclub','pro',txt)
            cb.reply_to(m, child_format_predict('hitclub', p))
        else:
            cb.reply_to(m, '💡 Gửi MD5 32 ký tự hoặc dùng <code>/tx hitclub TTXTXTTX</code>.')
    return cb

def child_bots_worker():
    """Chạy nhiều bot con bằng polling. Add token trên admin là worker tự bắt sau vài giây, không cần restart."""
    started = {}
    time.sleep(2)
    while True:
        try:
            active = cfg.setdefault('child_bots', {})
            # bot bị tắt/xóa thì đánh dấu để không start mới; polling cũ sẽ dừng ở vòng lỗi/timeout khi token xóa webhook lần sau
            for bid, info in list(active.items()):
                if not info.get('enabled', True):
                    continue
                token = str(info.get('token','')).strip()
                if not token or bid in started:
                    continue
                cb = _build_child_bot(token, bid)
                def _poll(xbot=cb, xid=bid):
                    try:
                        log(f'Bot con {xid} polling start')
                        try: xbot.remove_webhook()
                        except Exception: pass
                        xbot.infinity_polling(timeout=8, long_polling_timeout=8, skip_pending=True)
                    except Exception as e:
                        log(f'Bot con {xid} lỗi polling: {e}')
                    finally:
                        started.pop(xid, None)
                th = threading.Thread(target=_poll, daemon=True)
                th.start()
                started[bid] = {'thread': th, 'time': now_str()}
                log(f'Đã bật polling bot con {bid}')
        except Exception as e:
            log(f'child_bots_worker lỗi: {e}')
        time.sleep(3)

# ===================== END V120 =====================


# ===================== V124 MỚI NHẤT: ENGINE + PLAN GUARD + RENDER SAFE =====================
ENGINE_LABEL = "Mới Nhất"

# Không để lỗi template/API làm sập Render: log lỗi và trả JSON/text gọn.
try:
    @app.errorhandler(500)
    def _v124_handle_500(e):
        try: log(f"V124 500: {e}")
        except Exception: pass
        if str(getattr(request, 'path', '')).startswith('/api'):
            return jsonify({'ok': False, 'error': 'server_error', 'message': 'API đang bận hoặc cấu hình lỗi, thử lại sau.'}), 500
        return render_page('Lỗi hệ thống', '<div class="card"><h2>⚠️ Lỗi hệ thống</h2><p>Server vừa gặp lỗi nhỏ. Hãy tải lại trang hoặc xem Logs.</p></div>'), 500
except Exception:
    pass

# Chống user bị dính gói ảo: chỉ coi là có gói nếu hạn còn sống và key hợp lệ.
def has_active_plan(user, plan_key=None):
    try:
        if not isinstance(user, dict):
            return False
        now_ts = int(time.time())
        pe = user.get('plan_expires') if isinstance(user.get('plan_expires'), dict) else {}
        if plan_key in ('basic','pro'):
            exp = int(pe.get(plan_key, 0) or 0)
            # Tương thích dữ liệu cũ, nhưng chỉ khi active_plan thật sự trùng.
            if exp <= 0 and user.get('active_plan') == plan_key:
                exp = int(user.get('plan_expire', 0) or 0)
            return exp > now_ts
        return any(int(pe.get(k, 0) or 0) > now_ts for k in ('basic','pro')) or (
            user.get('active_plan') in ('basic','pro') and int(user.get('plan_expire',0) or 0) > now_ts
        )
    except Exception:
        return False

def best_available_plan(user):
    try:
        sp = user.get('selected_plan') if isinstance(user, dict) else None
        if sp in ('basic','pro') and has_active_plan(user, sp):
            return sp
        if has_active_plan(user, 'pro'):
            return 'pro'
        if has_active_plan(user, 'basic'):
            return 'basic'
    except Exception:
        pass
    return None

def plan_option_keyboard(plan_key):
    ensure_plan_options()
    kb = InlineKeyboardMarkup(row_width=1)
    found = False
    for ok, op in enabled_plan_options(plan_key):
        # Không hiện mốc giá 0 để tránh bug chưa mua vẫn có gói.
        if int(op.get('price', 0) or 0) <= 0 or int(op.get('seconds', 0) or 0) <= 0:
            continue
        found = True
        kb.add(InlineKeyboardButton(f"⏳ {op.get('label', duration_label(op.get('seconds',3600)))} · {money(op.get('price',0))}", callback_data=f"buydur_{plan_key}_{ok}"))
    if not found:
        kb.add(InlineKeyboardButton('⚠️ Chưa có mốc gói hợp lệ', callback_data='noop'))
    kb.add(InlineKeyboardButton('🔙 Quay lại', callback_data='buy_tool'))
    return kb

# Engine V124: đọc cầu theo run-length thật, có bẻ cầu nhưng chỉ bẻ khi đủ điều kiện.
def _v124_as_seq(bits):
    return _as_old_to_new(bits)[-1000:]

def _v124_runs(seq):
    seq = _v124_as_seq(seq)
    return _runs(seq)

def _v124_run_pattern(seq):
    seq = _v124_as_seq(seq)
    runs = _runs(seq)
    if len(runs) < 3:
        return None
    sides = [s for s,_ in runs]
    lens = [n for _,n in runs]
    last_side, last_len = runs[-1]
    best = None
    # Cầu 1-1, 1-2, 2-2, 1-3... đọc bằng độ dài các run, không đọc kiểu răng cưa.
    for cycle_len in (2,3,4):
        if len(lens) < cycle_len * 2:
            continue
        for phase in range(cycle_len):
            arr = lens[phase:]
            if len(arr) < cycle_len * 2:
                continue
            tail = arr[-cycle_len:]
            if not all(1 <= x <= 12 for x in tail):
                continue
            checks = []
            blocks = min(6, len(arr)//cycle_len)
            for b in range(2, blocks+1):
                block = arr[-b*cycle_len:-(b-1)*cycle_len]
                if len(block) != cycle_len:
                    continue
                exact = sum(1 for x,y in zip(block, tail) if x == y) / cycle_len
                near = sum(1 for x,y in zip(block, tail) if abs(x-y) <= 1) / cycle_len
                checks.append(exact*0.74 + near*0.22)
            if not checks:
                continue
            repeat_score = sum(checks) / len(checks)
            if cycle_len == 2 and tuple(tail) in ((1,1),(1,2),(2,1),(2,2),(1,3),(3,1),(2,3),(3,2)):
                repeat_score += 0.08
            if repeat_score < 0.50:
                continue
            # vị trí run hiện tại trong cycle tail
            expected_idx = (len(arr)-1) % cycle_len
            expected = max(1, int(tail[expected_idx]))
            if last_len < expected:
                pred = last_side
                action = f"giữ cầu {last_len}/{expected}"
            elif last_len == expected:
                pred = 0 if last_side else 1
                action = "đủ nhịp, đảo bên"
            else:
                pred = 0 if last_side else 1
                action = f"bẻ cầu vượt nhịp {expected}->{last_len}"
                repeat_score += min(0.14, (last_len-expected)*0.045)
            name = 'Cầu ' + '-'.join(map(str, tail))
            strength = min(0.96, 0.35 + repeat_score*0.50 + min(len(checks),5)*0.035)
            cand = {'name': name, 'score': strength, 'pred': pred, 'action': action, 'expected': expected, 'last_len': last_len, 'cycle': tail}
            if best is None or cand['score'] > best['score']:
                best = cand
    # Cầu bệt: theo bệt khi còn đẹp, bẻ khi quá dài.
    if last_len >= 4:
        if last_len <= 8:
            cand = {'name': f'Cầu bệt {last_len}', 'score': min(0.82, 0.45+last_len*0.045), 'pred': last_side, 'action': 'giữ bệt', 'expected': last_len, 'last_len': last_len, 'cycle': [last_len]}
        else:
            cand = {'name': f'Cầu bệt {last_len}', 'score': min(0.86, 0.48+last_len*0.035), 'pred': 0 if last_side else 1, 'action': 'bẻ bệt dài', 'expected': 8, 'last_len': last_len, 'cycle': [last_len]}
        if best is None or cand['score'] > best['score']:
            best = cand
    # Cầu 1-1 ping-pong nếu run toàn 1.
    if len(lens) >= 8 and all(x == 1 for x in lens[-8:]):
        cand = {'name': 'Cầu 1-1', 'score': 0.88, 'pred': 0 if last_side else 1, 'action': 'đảo đều', 'expected': 1, 'last_len': 1, 'cycle': [1,1]}
        if best is None or cand['score'] > best['score']:
            best = cand
    return best

def _v124_tail_repeat_vote(seq):
    seq = _v124_as_seq(seq)
    votes = []
    for L in range(3, min(36, len(seq)//2)+1):
        tail = seq[-L:]
        nxt = []
        for i in range(0, len(seq)-L):
            if seq[i:i+L] == tail and i+L < len(seq):
                nxt.append(seq[i+L])
        if len(nxt) >= 3:
            p = (sum(nxt)+1)/(len(nxt)+2)
            st = min(0.92, len(nxt)/16.0) * abs(p-0.5)*2
            if st >= 0.08:
                votes.append((1 if p >= 0.5 else -1, st, 0.88+min(L,24)/40, f'Tự học đoạn L{L}'))
    return votes

def _ultra_pattern_vote(bits, gate=None):
    seq = _v124_as_seq(bits)
    if len(seq) < 8:
        return 0, 0.0, 'Chưa đủ lịch sử', []
    gate = normalize_gate(gate or '')
    tune = V116_GATE_TUNE.get(gate, {'markov':1.0,'pattern':1.0,'tail':1.0}) if 'V116_GATE_TUNE' in globals() else {'markov':1.0,'pattern':1.0,'tail':1.0}
    votes = []
    details = []
    rp = _v124_run_pattern(seq)
    if rp:
        votes.append((1 if rp['pred'] else -1, rp['score'], 1.85*tune.get('pattern',1), rp['name'] + ' · ' + rp['action']))
        details.append((rp['name'], round(rp['score'],3), rp['action']))
    # Pattern bank cũ vẫn dùng làm phụ, nhưng không được lấn nếu cầu run rõ.
    try:
        best_name, best_ratio, best_bit = 'Đa cầu', 0.0, None
        for name, pat, w, _pair in V116_PATTERNS:
            bit, ratio = _pattern_predict_from_tail(seq, pat)
            if ratio > best_ratio:
                best_name, best_ratio, best_bit = name.replace(' X',''), ratio, bit
            if bit is not None and ratio >= 0.64:
                st = (ratio-0.50)*1.25
                votes.append((1 if bit else -1, st, 0.78*w*tune.get('pattern',1), name.replace(' X','')))
        if best_ratio >= 0.58:
            details.append((best_name, round(best_ratio,3), 'bank cầu'))
    except Exception:
        pass
    # Markov + tự học chỉ là phụ, tránh kéo ngược khi cầu chính rõ.
    try:
        mv, ms = _nomd5_markov_vote(seq)
        if ms >= 0.035:
            votes.append((mv, min(ms,0.30), 0.80*tune.get('markov',1), 'Markov phụ'))
            details.append(('Markov phụ', round(ms,3)))
    except Exception:
        pass
    votes += _v124_tail_repeat_vote(seq)
    if not votes:
        return (1 if seq[-1] else -1), 0.10, 'Chờ cầu rõ', details
    score = sum(v*st*w for v,st,w,_ in votes)
    den = sum(st*w for _,st,w,_ in votes) or 1.0
    side = 1 if score >= 0 else -1
    agree = min(1.0, abs(score)/den)
    same = [(nm, st*w) for v,st,w,nm in votes if v == side]
    same.sort(key=lambda x:x[1], reverse=True)
    cname = same[0][0] if same else (rp['name'] if rp else 'Đa cầu tổng hợp')
    return side, agree, cname, details[:6]

def detect_bridge_type(seq, gate=None, predicted=None):
    seq = _v124_as_seq(seq)[-320:]
    if len(seq) < 8:
        return 'Chưa đủ lịch sử'
    rp = _v124_run_pattern(seq)
    if rp and rp.get('score',0) >= 0.54:
        return f"{rp['name']} · {rp['action']}"
    side, agree, cname, _ = _ultra_pattern_vote(seq, gate)
    pct = int(round(max(0, agree)*100))
    return f"{cname} · khớp {pct}%" if cname else 'Cầu hỗn hợp / chờ thêm phiên'

def _v116_backtest_rate(seq, gate=None, max_checks=90):
    seq = _v124_as_seq(seq)
    if len(seq) < 22:
        return None, 0
    start = max(12, len(seq)-max_checks)
    hit = total = 0
    for i in range(start, len(seq)):
        side, agree, _, _ = _ultra_pattern_vote(seq[:i], gate)
        # V124: tín hiệu yếu thì bỏ qua trong backtest, không cố đoán mọi tay.
        if not side or agree < 0.18:
            continue
        pred = 1 if side >= 0 else 0
        hit += 1 if pred == seq[i] else 0
        total += 1
    if total < 8:
        return None, total
    return hit/total, total

def _v124_fix_probs(p, gate=None):
    try:
        res = str(p.get('taixiu','')).upper()
        conf = int(float(str(p.get('tx_conf', p.get('confidence', 0))).replace('%','') or 0))
        conf = int(_clamp(conf, 0, 99))
        if gate == 'bcr':
            if res == 'BANKER':
                p['prob_tai'] = f'{conf}%'; p['prob_xiu'] = f'{max(1, 95-conf)}%'; p['prob_tie'] = p.get('prob_tie') or '5%'
            elif res == 'PLAYER':
                p['prob_xiu'] = f'{conf}%'; p['prob_tai'] = f'{max(1, 95-conf)}%'; p['prob_tie'] = p.get('prob_tie') or '5%'
            elif res == 'TIE':
                p['prob_tie'] = f'{max(8, min(18, conf))}%'
        elif res == 'TÀI':
            p['prob_tai'] = f'{conf}%'; p['prob_xiu'] = f'{100-conf}%'
        elif res == 'XỈU':
            p['prob_xiu'] = f'{conf}%'; p['prob_tai'] = f'{100-conf}%'
    except Exception:
        pass
    return p

_v124_old_predict_nomd5 = predict_nomd5
def predict_nomd5(gate='lc79', level='basic', history=None):
    p = _v124_old_predict_nomd5(gate, level, history)
    if not isinstance(p, dict):
        return p
    gate = normalize_gate(gate)
    p['engine'] = ENGINE_LABEL
    try:
        # Nếu engine cũ trả bridge mờ, tính lại từ history/API thật.
        ok, api = _fetch_nomd5_api(gate)
        hb = []
        if history:
            hb += (_bcr_result_seq_to_bits(history) if gate=='bcr' else _history_bits(history))
        if ok:
            hb += list(reversed(list(api.get('history_bits') or [])))
        if hb:
            p['bridge_type'] = detect_bridge_type(hb, gate, p.get('taixiu'))
            side, agree, cname, detail = _ultra_pattern_vote(hb, gate)
            if p.get('taixiu') in ('TÀI','XỈU') and side:
                # Chỉ đảo kết luận khi cầu chính đủ mạnh; tránh random theo API cũ làm gãy liên tục.
                if agree >= 0.34:
                    p['taixiu'] = 'TÀI' if side >= 0 else 'XỈU'
                    bt, n = _v116_backtest_rate(hb, gate, 90)
                    cap = {'free':64, 'basic':73, 'pro':82}.get(str(level).lower(), 73)
                    if bt is not None:
                        conf = int(round(bt*100*0.62 + (52+agree*30)*0.38))
                    else:
                        conf = int(round(52 + agree*28))
                    # Không buff ảo, nhưng tín hiệu rất rõ thì vẫn cho cao hơn vừa phải.
                    p['tx_conf'] = int(_clamp(conf, 48, cap))
                    p['vote_agree'] = round(agree*10,1)
                    p['backtest_rate'] = round(bt*100,1) if bt is not None else p.get('backtest_rate')
                    p['backtest_n'] = n if n else p.get('backtest_n')
    except Exception as e:
        try: log(f'V124 predict wrapper lỗi: {e}')
        except Exception: pass
    return _v124_fix_probs(p, gate)

# API HTML cũng trả engine Mới Nhất.
def _api_payload_from_predict(slug, gate, level, p, tool_name=None):
    gate = normalize_gate(gate)
    p = _v124_fix_probs(dict(p or {}), gate)
    result = p.get('taixiu')
    label = ({'BANKER':'Tay Cái','PLAYER':'Tay Con','TIE':'Hòa'}.get(str(result).upper(), result) if gate=='bcr' else result)
    return {
        'ok': True, 'tool': slug, 'name': tool_name or slug, 'gate': gate, 'game': gate_name(gate), 'level': level,
        'period': p.get('period'), 'last_period': p.get('last_period'), 'result': result, 'prediction': result,
        'side_label': label, 'confidence': p.get('tx_conf'), 'percent': p.get('tx_conf'),
        'bridge_type': p.get('bridge_type'), 'pattern': p.get('bridge_type'),
        'prob_tai': p.get('prob_tai'), 'prob_xiu': p.get('prob_xiu'), 'prob_tie': p.get('prob_tie'),
        'dice': p.get('dice'), 'total': p.get('total'), 'advice': p.get('advice'), 'risk': p.get('risk'),
        'backtest_rate': p.get('backtest_rate'), 'backtest_n': p.get('backtest_n'),
        'streak': re.sub('<[^<]+?>','', str(p.get('streak',''))),
        'engine': ENGINE_LABEL, 'updated_at': now_str()
    }

# Hiển thị giữ giao diện cũ, chỉ sửa label phiên bản + Tài/Xỉu% luôn đúng bên dự đoán.
def format_nomd5_reply(gate, p):
    gate = normalize_gate(gate)
    p = _v124_fix_probs(dict(p or {}), gate)
    result = str(p.get('taixiu','')).upper()
    bridge = p.get('bridge_type') or 'Đa cầu tổng hợp'
    streak = p.get('streak') or current_streak_text(gate, p.get('level'))
    if gate == 'bcr':
        if result == 'BANKER': line = '👑 Kết luận: <b>🅑 BANKER / TAY CÁI</b>'
        elif result == 'PLAYER': line = '👤 Kết luận: <b>🅟 PLAYER / TAY CON</b>'
        elif result == 'TIE': line = '🤝 Kết luận: <b>🅣 TIE / HÒA</b>'
        else: line = '⏳ Kết luận: <b>ĐANG CHỜ</b>'
        return (f"🃏 <b>DỰ ĐOÁN API BACCARAT</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Phiên bản: <b>{ENGINE_LABEL}</b>\n"
                f"🧾 Phiên: <code>{p.get('period','?')}</code>\n\n"
                f"{line}\n🧬 Loại cầu: <b>{bridge}</b>\n"
                f"📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
                f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
                f"🎯 Banker/Player/Tie: B <b>{p.get('prob_tai','0%')}</b> · P <b>{p.get('prob_xiu','0%')}</b> · T <b>{p.get('prob_tie','0%')}</b>\n\n{streak}")
    if result == 'TÀI': line = '📈 Kết luận: <b>🅣 TÀI</b>'
    elif result == 'XỈU': line = '📉 Kết luận: <b>🅧 XỈU</b>'
    else: line = '⏳ Kết luận: <b>ĐANG CHỜ</b>'
    title = '🎯 <b>DỰ ĐOÁN API SICBO</b>' if gate in ('sicb52','sichit','sicsun') else '🔮 <b>DỰ ĐOÁN API TÀI/XỈU</b>'
    return (f"{title}\n\n🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
            f"📦 Phiên bản: <b>{ENGINE_LABEL}</b>\n"
            f"🧾 Phiên: <code>{p.get('period','?')}</code>\n\n"
            f"🎲 Bộ số mô phỏng: <b>{p.get('dice','?-?-?')}</b> | Tổng: <b>{p.get('total','?')}</b>\n"
            f"{line}\n🧬 Loại cầu: <b>{bridge}</b>\n"
            f"📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
            f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
            f"🎯 Tài/Xỉu %: T <b>{p.get('prob_tai','0%')}</b> · X <b>{p.get('prob_xiu','0%')}</b>\n\n{streak}")

def format_md5_reply(gate, p):
    gate = normalize_gate(gate)
    p = _v124_fix_probs(dict(p or {}), gate)
    result = str(p.get('taixiu','')).upper()
    line = '📈 Kết luận: <b>🅣 TÀI</b>' if result == 'TÀI' else '📉 Kết luận: <b>🅧 XỈU</b>' if result == 'XỈU' else '⏳ Kết luận: <b>ĐANG CHỜ</b>'
    bridge = p.get('bridge_type') or p.get('trend') or 'Hash đa lớp / cầu tổng hợp'
    return (f"🔮 <b>PHÂN TÍCH MD5 TÀI/XỈU</b>\n\n"
            f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
            f"📦 Phiên bản: <b>{ENGINE_LABEL}</b>\n"
            f"📝 MD5 hiện tại: <code>{p.get('hash_short','')}</code>\n\n"
            f"🎲 Bộ số mô phỏng: <b>{p.get('dice','?-?-?')}</b> | Tổng: <b>{p.get('total','?')}</b>\n"
            f"{line}\n🧬 Loại cầu: <b>{bridge}</b>\n"
            f"📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
            f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
            f"🎯 Tài/Xỉu %: T <b>{p.get('prob_tai','0%')}</b> · X <b>{p.get('prob_xiu','0%')}</b>")

# ===================== END V124 =====================




# ===================== V125 SESSION LOCK + USER PLAN FIX =====================
# Mỗi lần /start/quay lại/chạy API mới sẽ tạo session mới. Thread cũ và thông báo thắng/thua cũ
# tự hủy, không cộng chuỗi và không gửi loạn kết quả từ màn phân tích đã bỏ.
_live_user_sessions = globals().setdefault('_live_user_sessions', {})
_live_session_lock = threading.RLock()

def _new_live_session(uid, gate=None, plan=None):
    uid = str(uid)
    with _live_session_lock:
        # tắt toàn bộ job cũ của user trước khi tạo phiên mới
        for k, job in list(globals().get('_nomd5_live_jobs', {}).items()):
            if str(job.get('uid')) == uid:
                job['alive'] = False
        sid = f"{uid}:{normalize_gate(gate or '')}:{plan or ''}:{int(time.time()*1000)}"
        _live_user_sessions[uid] = sid
        return sid

def _is_live_session(uid, sid):
    return bool(sid) and _live_user_sessions.get(str(uid)) == sid

def stop_all_live_by_user(uid):
    uid = str(uid)
    with _live_session_lock:
        _live_user_sessions[uid] = f"stopped:{int(time.time()*1000)}"
        for k, job in list(globals().get('_nomd5_live_jobs', {}).items()):
            if str(job.get('uid')) == uid:
                job['alive'] = False

def stop_live_message(chat_id, message_id):
    # Nút quay lại/menu chỉ biết chat+message. Tắt mọi job cùng chat để tránh thread cũ vẫn báo đúng/sai.
    chat_id = str(chat_id)
    try:
        for k, job in list(globals().get('_nomd5_live_jobs', {}).items()):
            if k.startswith(chat_id + ':'):
                job['alive'] = False
                u = str(job.get('uid') or '')
                if u:
                    _live_user_sessions[u] = f"stopped:{int(time.time()*1000)}"
    except Exception:
        pass

def start_nomd5_live(bot_obj, chat_id, message_id, uid, gate, plan):
    uid = str(uid); gate = normalize_gate(gate); plan = str(plan or 'basic')
    sid = _new_live_session(uid, gate, plan)
    key = f"{chat_id}:{message_id}:{sid}"
    globals().setdefault('_nomd5_live_jobs', {})[key] = {"alive": True, "uid": uid, "gate": gate, "plan": plan, "session_id": sid, "started": time.time()}

    def _result_notice(cid, pred_period, pred, actual, win, user_id, gate_key, plan_key, session_id):
        try:
            time.sleep(3)
            if not _is_live_session(user_id, session_id):
                return
            tmp = bot_obj.send_message(
                cid,
                ("✅" if win else "❌") + f" <b>Phiên {pred_period}</b> {'thắng' if win else 'thua'} · Dự đoán: <b>{pred}</b> · KQ: <b>{actual}</b>",
                parse_mode='HTML'
            )
            if not _is_live_session(user_id, session_id):
                try: bot_obj.delete_message(cid, tmp.message_id)
                except Exception: pass
                return
            db.setdefault('prediction_checks', []).append({
                'user_id': str(user_id), 'gate': gate_key, 'plan': plan_key, 'period': pred_period,
                'predict': pred, 'actual': actual, 'win': win, 'time': now_str(), 'session_id': session_id
            })
            update_live_streak(str(user_id), gate_key, plan_key, win)
            key_stat = f"{gate_key}:{plan_key}"
            st = db.setdefault('api_winloss', {}).setdefault(key_stat, {'win':0,'lose':0})
            st['win' if win else 'lose'] = int(st.get('win' if win else 'lose', 0)) + 1
            save_db()
            time.sleep(3)
            try: bot_obj.delete_message(cid, tmp.message_id)
            except Exception: pass
        except Exception as e:
            try: log(f'V125 gửi/chốt thắng thua lỗi {gate_key}: {e}')
            except Exception: pass

    def worker():
        last_text = None
        last_pred = None
        for _ in range(8640):
            job = globals().get('_nomd5_live_jobs', {}).get(key)
            if not job or not job.get('alive') or not _is_live_session(uid, sid):
                break
            try:
                user = db.get('users', {}).get(uid, {})
                if plan in ('basic','pro') and not has_active_plan(user, plan):
                    stop_all_live_by_user(uid)
                    try:
                        bot_obj.edit_message_text("⛔ <b>Gói đã hết hạn</b>\n\nBấm /start để mua/chọn lại gói mới.", chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return
                if plan == 'free' and not free_is_active():
                    stop_all_live_by_user(uid)
                    try:
                        bot_obj.edit_message_text("⛔ <b>Free mode đã hết thời gian</b>\n\nBấm /start để chọn gói khác.", chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return

                hist = recent_history_for_gate(gate or '', 500)
                p = predict_nomd5(gate, plan, hist)

                # Chốt kết quả phiên trước chỉ khi cùng session hiện tại.
                try:
                    if last_pred and p.get('last_period') and str(p.get('last_period')) == str(last_pred.get('period')):
                        actual = str(p.get('latest_actual') or p.get('taixiu') or '').upper()
                        pred = str(last_pred.get('result') or '').upper()
                        if actual and pred and actual not in ('ĐANG CHỜ','') and _is_live_session(uid, sid):
                            win = (actual == pred)
                            threading.Thread(target=_result_notice, args=(chat_id, last_pred.get('period'), pred, actual, win, uid, gate, plan, sid), daemon=True).start()
                            last_pred = None
                except Exception as e:
                    try: log(f'V125 check thắng/thua lỗi {gate}: {e}')
                    except Exception: pass

                p['streak'] = current_streak_text(gate, plan, uid)
                text = format_nomd5_reply(gate, p)
                if text != last_text and _is_live_session(uid, sid):
                    bot_obj.edit_message_text(
                        text, chat_id, message_id, parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton("🔙 Quay lại chọn cổng", callback_data="mode_nomd5"),
                            InlineKeyboardButton("🏠 Menu", callback_data="back_home")
                        )
                    )
                    last_text = text
                if p.get('period') and p.get('taixiu') not in ('ĐANG CHỜ',''):
                    last_pred = {'period': p.get('period'), 'result': p.get('taixiu')}
            except Exception as e:
                try: log(f'V125 API live update lỗi {gate}: {e}')
                except Exception: pass
            time.sleep(5)
        try:
            globals().get('_nomd5_live_jobs', {}).pop(key, None)
        except Exception:
            pass

    threading.Thread(target=worker, daemon=True).start()

# /start hiện có gọi stop_all_live_by_user(uid), sau V125 sẽ tắt toàn bộ session cũ.
# Khi bấm chạy API mới, start_nomd5_live tự tắt job cũ trước khi chạy job mới.
# ===================== END V125 =====================


# ===================== V126 ALGO CORE 8-9/10 + FIX % T/X =====================
# Chỉ nâng lõi thuật toán, giữ nguyên giao diện bot. Mục tiêu: nhận cầu A-B rõ hơn,
# bẻ cầu có điều kiện nhiều tầng, và bắt buộc % bên kết luận luôn cao hơn bên còn lại.
ENGINE_LABEL = 'Mới Nhất'

def _v126_side_norm(x):
    s = str(x or '').strip().upper()
    s = s.replace('TAI', 'TÀI').replace('XIU', 'XỈU')
    if 'BANKER' in s or 'TAY CÁI' in s: return 'BANKER'
    if 'PLAYER' in s or 'TAY CON' in s: return 'PLAYER'
    if 'TIE' in s or 'HÒA' in s or 'HOA' in s: return 'TIE'
    if s.startswith('T') or 'TÀI' in s: return 'TÀI'
    if s.startswith('X') or 'XỈU' in s: return 'XỈU'
    return s

def _v126_pat(a, b, start=1, rep=5):
    return ([start] * a + [1-start] * b) * rep

V126_PATTERNS = []
for _a in range(1, 13):
    for _b in range(1, 13):
        _w = 1.54 if _a <= 3 and _b <= 3 else 1.38 if _a <= 6 and _b <= 6 else 1.22
        V126_PATTERNS.append((f'Cầu {_a}-{_b}', _v126_pat(_a, _b, 1), _w))
        V126_PATTERNS.append((f'Cầu {_a}-{_b}', _v126_pat(_a, _b, 0), _w))

def _v126_tail_match(seq, pattern):
    try:
        return _pattern_predict_from_tail(seq, pattern)
    except Exception:
        seq = list(seq or [])
        if not seq or not pattern: return None, 0.0
        best = 0
        for off in range(len(pattern)):
            ok = 0; n = min(len(seq), len(pattern)-1)
            if n <= 0: continue
            tail = seq[-n:]
            view = [pattern[(off+i) % len(pattern)] for i in range(n)]
            ok = sum(1 for a,b in zip(tail, view) if a == b)
            best = max(best, ok/n)
        return pattern[(off+n) % len(pattern)] if best else None, best

def _v126_run_context(seq):
    seq = _as_old_to_new(seq)
    runs = _runs(seq)
    if not runs: return {'name':'Chưa đủ lịch sử','next':None,'score':0,'action':'WAIT'}
    sides = [b for b,_ in runs]
    lens = [n for _,n in runs]
    last_side, last_len = runs[-1]
    # Cầu bệt: giữ đến nhịp dài, bẻ khi quá nóng hoặc có dấu bẻ rõ.
    if last_len >= 9:
        return {'name':f'Bẻ cầu bệt {last_len}', 'next':1-last_side, 'score':0.70, 'action':'BREAK'}
    if last_len >= 4:
        return {'name':f'Giữ cầu bệt {last_len}', 'next':last_side, 'score':0.56 + min(last_len,8)*0.025, 'action':'FOLLOW'}
    # Cầu A-B theo run-length: lấy 2 run gần nhất làm nhịp, kiểm tra lặp ngược lại.
    if len(runs) >= 4 and all(sides[i] != sides[i-1] for i in range(1, len(sides))):
        a, b = lens[-2], lens[-1]
        if 1 <= a <= 12 and 1 <= b <= 12:
            pairs = []
            for i in range(len(lens)-2, -1, -2):
                if i+1 < len(lens): pairs.append((lens[i], lens[i+1]))
            hit = sum(1 for p in pairs[:5] if p == (a,b))
            # Nếu run hiện tại đang đủ b thì chuẩn bị đổi; nếu chưa đủ b thì giữ.
            next_bit = 1-last_side if last_len >= b else last_side
            score = min(0.88, 0.50 + hit*0.10 + min(len(seq),120)/600)
            return {'name':f'Cầu {a}-{b}', 'next':next_bit, 'score':score, 'action':'FOLLOW'}
    # Ping pong 1-1.
    if len(seq) >= 8 and all(seq[-i] != seq[-i-1] for i in range(1, min(9,len(seq)))):
        return {'name':'Cầu 1-1', 'next':1-last_side, 'score':0.82, 'action':'FOLLOW'}
    return {'name':'Đa cầu tổng hợp', 'next':None, 'score':0.40, 'action':'WAIT'}

def _v126_break_votes(seq):
    seq = _as_old_to_new(seq)
    out=[]
    if len(seq) < 12: return out
    runs = _runs(seq); last = seq[-1]
    last_len = runs[-1][1] if runs else 1
    # Bẻ sau bệt quá dài.
    if last_len >= 9:
        out.append((1-last, 0.70, 1.30, f'Bẻ bệt quá nhịp {last_len}'))
    # Bẻ cầu A-B khi chu kỳ lặp nhiều lần nhưng run hiện tại vượt quá nhịp dự kiến.
    if len(runs) >= 6:
        lens=[n for _,n in runs]
        a,b = lens[-4], lens[-3]
        if 1 <= a <= 12 and 1 <= b <= 12:
            expected = b if runs[-1][0] == runs[-3][0] else a
            repeats = sum(1 for i in range(max(0,len(lens)-8), len(lens)-1) if lens[i] in (a,b))
            if last_len >= expected + 1 and repeats >= 4:
                out.append((1-last, 0.62, 1.18, f'Bẻ cầu {a}-{b} lệch nhịp'))
    # Gãy giả: vừa đổi 1 cái sau chuỗi 3-6, thường hồi lại.
    if len(runs) >= 2 and runs[-1][1] == 1 and 3 <= runs[-2][1] <= 6:
        out.append((runs[-2][0], 0.52, 0.92, f'Chống gãy giả sau bệt {runs[-2][1]}'))
    return out

def _ultra_pattern_vote(bits, gate=None):
    seq = _as_old_to_new(bits)
    if len(seq) < 6:
        return 0, 0.0, 'Chưa đủ lịch sử', []
    gate = normalize_gate(gate or '')
    tune = globals().get('GATE_TUNING', {}).get(gate, {'markov':1,'pattern':1,'cycle':1,'tail':1})
    votes=[]; details=[]
    ctx = _v126_run_context(seq)
    if ctx.get('next') is not None and ctx.get('score',0) >= 0.48:
        votes.append((1 if ctx['next'] else -1, ctx['score'], 1.62*tune.get('cycle',1), ctx['name']))
        details.append((ctx['name'], ctx['score']))
    best=(None,0,None)
    for nm,pat,w in V126_PATTERNS:
        bit,ratio = _v126_tail_match(seq, pat)
        if ratio > best[1]: best=(nm,ratio,bit)
        if bit is not None and ratio >= 0.60:
            # Pattern khớp đuôi nhưng không buff quá ảo.
            st = min(0.88, (ratio-0.50)*1.70)
            votes.append((1 if bit else -1, st, w*tune.get('pattern',1), nm))
    if best[0]: details.append((best[0], best[1]))
    for bit,st,w,nm in _v126_break_votes(seq):
        votes.append((1 if bit else -1, st, w*tune.get('tail',1), nm))
        details.append((nm, st))
    try:
        mv,ms = _nomd5_markov_vote(seq)
        if ms >= 0.03:
            votes.append((mv, min(ms,0.72), 1.18*tune.get('markov',1), 'Markov tự học'))
            details.append(('Markov tự học', ms))
    except Exception:
        pass
    # Tail replay dài-ngắn: ưu tiên đoạn từng xuất hiện nhiều lần.
    best_tail=None
    for L in range(3, min(34, len(seq)//2)+1):
        tail=seq[-L:]; hits=[]
        for i in range(0, len(seq)-L):
            if seq[i:i+L] == tail and i+L < len(seq): hits.append(seq[i+L])
        if len(hits) >= 2:
            p=(sum(hits)+1)/(len(hits)+2)
            st=min(0.82, len(hits)/11.0) * abs(p-0.5)*2
            if st >= 0.09:
                nm=f'Lặp đuôi L{L}'
                votes.append((1 if p>=0.5 else -1, st, 1.02+min(L,22)/36, nm))
                if best_tail is None or st > best_tail[1]: best_tail=(nm,st)
    if best_tail: details.append(best_tail)
    if not votes:
        return 0, 0.0, ctx.get('name','Đa cầu tổng hợp'), details[:5]
    score = sum(v*st*w for v,st,w,_ in votes)
    den = sum(st*w for _,st,w,_ in votes) or 1
    side = 1 if score >= 0 else -1
    agree = min(1.0, abs(score)/den)
    same=[(nm, st*w) for v,st,w,nm in votes if v == side]
    same.sort(key=lambda x:x[1], reverse=True)
    cname = same[0][0] if same else ctx.get('name','Đa cầu tổng hợp')
    return side, agree, cname, details[:6]

def detect_bridge_type(seq, gate=None, predicted=None):
    seq = _as_old_to_new(seq)[-220:]
    if len(seq) < 6: return 'Chưa đủ lịch sử'
    side, agree, cname, detail = _ultra_pattern_vote(seq, gate)
    pct = int(round(max(0, agree)*100))
    # Nếu có bẻ cầu trong detail, show rõ để admin biết engine đang bẻ hay giữ.
    br = [n for n,s in detail if 'Bẻ' in str(n) or 'gãy' in str(n).lower()]
    if br and cname not in br:
        cname = f'{cname} + {br[0]}'
    if normalize_gate(gate or '') == 'bcr':
        cname = str(cname).replace('TÀI','Banker').replace('XỈU','Player').replace('Cầu 1-1','Cầu Ping Pong 1-1')
    return f'{cname} · khớp {pct}%' if cname else 'Cầu hỗn hợp / chờ thêm phiên'

def _v126_fix_probs(p, gate=None):
    try:
        res = _v126_side_norm(p.get('taixiu') or p.get('result') or p.get('prediction'))
        conf = int(float(str(p.get('tx_conf', p.get('confidence', 0))).replace('%','').strip() or 0))
        # Bắt buộc bên dự đoán >= 51%, để không còn Xỉu mà T cao hơn X.
        side_pct = int(_clamp(max(conf, 51), 51, 94))
        other = max(1, 100 - side_pct)
        if normalize_gate(gate or '') == 'bcr':
            tie = int(float(str(p.get('prob_tie','5')).replace('%','') or 5)) if res != 'TIE' else max(8, min(18, side_pct))
            remain = max(2, 100 - tie)
            main = min(side_pct, remain-1)
            sec = max(1, remain-main)
            if res == 'BANKER':
                p['prob_tai'] = f'{main}%'; p['prob_xiu'] = f'{sec}%'; p['prob_tie'] = f'{tie}%'
            elif res == 'PLAYER':
                p['prob_xiu'] = f'{main}%'; p['prob_tai'] = f'{sec}%'; p['prob_tie'] = f'{tie}%'
            elif res == 'TIE':
                p['prob_tie'] = f'{side_pct}%'; p['prob_tai'] = f'{(100-side_pct)//2}%'; p['prob_xiu'] = f'{100-side_pct-(100-side_pct)//2}%'
        else:
            if res == 'TÀI':
                p['prob_tai'] = f'{side_pct}%'; p['prob_xiu'] = f'{other}%'
            elif res == 'XỈU':
                p['prob_xiu'] = f'{side_pct}%'; p['prob_tai'] = f'{other}%'
    except Exception:
        pass
    return p

_v126_old_predict_nomd5 = predict_nomd5
def predict_nomd5(gate='lc79', level='basic', history=None):
    p = _v126_old_predict_nomd5(gate, level, history)
    if not isinstance(p, dict): return p
    gate = normalize_gate(gate)
    p['engine'] = ENGINE_LABEL
    try:
        ok, api = _fetch_nomd5_api(gate)
        hb=[]
        if history:
            hb += (_bcr_result_seq_to_bits(history) if gate=='bcr' else _history_bits(history))
        if ok:
            hb += list(reversed(list(api.get('history_bits') or [])))
        hb = _as_old_to_new(hb)[-900:]
        if hb:
            side, agree, cname, detail = _ultra_pattern_vote(hb, gate)
            if side and agree >= 0.22:
                if gate == 'bcr':
                    p['taixiu'] = 'BANKER' if side >= 0 else 'PLAYER'
                else:
                    p['taixiu'] = 'TÀI' if side >= 0 else 'XỈU'
                bt, n = _v116_backtest_rate(hb, gate, 100)
                cap = {'free':64, 'basic':74, 'pro':83}.get(str(level).lower(), 74)
                if bt is not None:
                    conf = int(round(bt*100*0.55 + (52+agree*34)*0.45))
                else:
                    conf = int(round(52 + agree*31))
                # Nếu tín hiệu quá yếu thì không buff; nếu rõ cầu/bẻ thì tăng vừa phải.
                if agree < 0.30: conf = min(conf, 62)
                p['tx_conf'] = int(_clamp(conf, 49, cap))
                p['vote_agree'] = round(agree*10, 1)
                if bt is not None: p['backtest_rate'] = round(bt*100,1)
                if n: p['backtest_n'] = n
                p['bridge_type'] = detect_bridge_type(hb, gate, p.get('taixiu'))
                p['trend'] = 'Nhận cầu A-B 1-1..12-12 + bẻ cầu nhiều tầng + Markov + replay tail'
                p['details'] = ['Engine V126', cname, 'Bẻ cầu nhiều tầng', gate_name(gate)]
    except Exception as e:
        try: log(f'V126 predict wrapper lỗi: {e}')
        except Exception: pass
    return _v126_fix_probs(p, gate)

# Override format lần cuối để chắc chắn % không bao giờ lệch bên dự đoán.
def format_nomd5_reply(gate, p):
    gate = normalize_gate(gate); p = _v126_fix_probs(dict(p or {}), gate)
    result = _v126_side_norm(p.get('taixiu'))
    bridge = p.get('bridge_type') or 'Đa cầu tổng hợp'
    streak = p.get('streak') or current_streak_text(gate, p.get('level'))
    if gate == 'bcr':
        if result == 'BANKER': line = '👑 Kết luận: <b>🅑 BANKER / TAY CÁI</b>'
        elif result == 'PLAYER': line = '👤 Kết luận: <b>🅟 PLAYER / TAY CON</b>'
        elif result == 'TIE': line = '🤝 Kết luận: <b>🅣 TIE / HÒA</b>'
        else: line = '⏳ Kết luận: <b>ĐANG CHỜ</b>'
        return (f"🃏 <b>DỰ ĐOÁN API BACCARAT</b>\n\n🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Phiên bản: <b>{ENGINE_LABEL}</b>\n🧾 Phiên: <code>{p.get('period','?')}</code>\n\n{line}\n"
                f"🧬 Loại cầu: <b>{bridge}</b>\n📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
                f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
                f"🎯 Banker/Player/Tie: B <b>{p.get('prob_tai','0%')}</b> · P <b>{p.get('prob_xiu','0%')}</b> · T <b>{p.get('prob_tie','0%')}</b>\n\n{streak}")
    line = '📈 Kết luận: <b>🅣 TÀI</b>' if result == 'TÀI' else '📉 Kết luận: <b>🅧 XỈU</b>' if result == 'XỈU' else '⏳ Kết luận: <b>ĐANG CHỜ</b>'
    title = '🎯 <b>DỰ ĐOÁN API SICBO</b>' if gate in ('sicb52','sichit','sicsun') else '🔮 <b>DỰ ĐOÁN API TÀI/XỈU</b>'
    return (f"{title}\n\n🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n📦 Phiên bản: <b>{ENGINE_LABEL}</b>\n"
            f"🧾 Phiên: <code>{p.get('period','?')}</code>\n\n🎲 Bộ số mô phỏng: <b>{p.get('dice','?-?-?')}</b> | Tổng: <b>{p.get('total','?')}</b>\n"
            f"{line}\n🧬 Loại cầu: <b>{bridge}</b>\n📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
            f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
            f"🎯 Tài/Xỉu %: T <b>{p.get('prob_tai','0%')}</b> · X <b>{p.get('prob_xiu','0%')}</b>\n\n{streak}")

def format_md5_reply(gate, p):
    gate = normalize_gate(gate); p = _v126_fix_probs(dict(p or {}), gate)
    result = _v126_side_norm(p.get('taixiu'))
    line = '📈 Kết luận: <b>🅣 TÀI</b>' if result == 'TÀI' else '📉 Kết luận: <b>🅧 XỈU</b>' if result == 'XỈU' else '⏳ Kết luận: <b>ĐANG CHỜ</b>'
    bridge = p.get('bridge_type') or p.get('trend') or 'Hash đa lớp / cầu tổng hợp'
    return (f"🔮 <b>PHÂN TÍCH MD5 TÀI/XỈU</b>\n\n🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n📦 Phiên bản: <b>{ENGINE_LABEL}</b>\n"
            f"📝 MD5 hiện tại: <code>{p.get('hash_short','')}</code>\n\n🎲 Bộ số mô phỏng: <b>{p.get('dice','?-?-?')}</b> | Tổng: <b>{p.get('total','?')}</b>\n"
            f"{line}\n🧬 Loại cầu: <b>{bridge}</b>\n📊 Độ tin cậy thực chiến: <b>{p.get('tx_conf',0)}%</b>\n"
            f"🧪 Backtest gần nhất: <b>{p.get('backtest_rate','-')}%</b> ({p.get('backtest_n',0)} mẫu)\n"
            f"🎯 Tài/Xỉu %: T <b>{p.get('prob_tai','0%')}</b> · X <b>{p.get('prob_xiu','0%')}</b>")
# ===================== END V126 =====================



# ===================== V130 SPEED + STABLE HYBRID PATCH =====================
# Fix delay do API bị gọi trùng nhiều lần, giữ thuật toán cầu hiện tại nhưng không bẻ/đè kết quả quá non.
# Fix live không tự refresh, không báo đúng/sai, không hiện phiên mới. Giao diện bot giữ nguyên.
ENGINE_LABEL = 'Mới Nhất'

_api_fetch_cache = globals().setdefault('_api_fetch_cache', {})
_api_fetch_lock = threading.RLock()
try:
    _v130_raw_fetch_nomd5_api = _fetch_nomd5_api
except Exception:
    _v130_raw_fetch_nomd5_api = None

def _fetch_nomd5_api(gate, health_only=False):
    """Cache cực ngắn để 1 lần phân tích không gọi API 2-3 lần gây chậm/sập Render."""
    gate = normalize_gate(gate or '')
    if health_only or _v130_raw_fetch_nomd5_api is None:
        return _v130_raw_fetch_nomd5_api(gate, health_only) if _v130_raw_fetch_nomd5_api else (False, {'error':'missing fetch'})
    now = time.time()
    key = (gate, False)
    with _api_fetch_lock:
        item = _api_fetch_cache.get(key)
        if item and now - item.get('t', 0) < 1.25:
            return item['v']
    try:
        val = _v130_raw_fetch_nomd5_api(gate, health_only)
    except Exception as e:
        val = (False, {'error': str(e)[:160]})
    with _api_fetch_lock:
        _api_fetch_cache[key] = {'t': now, 'v': val}
    return val

def _v130_bits_from_api_and_history(gate, history=None, limit=900):
    gate = normalize_gate(gate or '')
    hb = []
    try:
        if history:
            hb += (_bcr_result_seq_to_bits(history) if gate == 'bcr' else _history_bits(history))
    except Exception:
        pass
    try:
        ok, api = _fetch_nomd5_api(gate)
        if ok:
            hb += list(reversed(list(api.get('history_bits') or [])))
    except Exception:
        pass
    return _as_old_to_new(hb)[-limit:]

def _v130_run_vote(seq):
    seq = _as_old_to_new(seq)[-240:]
    if len(seq) < 8:
        return None, 0.0, 'Chưa đủ lịch sử'
    runs = _runs(seq)
    if not runs:
        return None, 0.0, 'Chưa đủ lịch sử'
    last_side, last_len = runs[-1]
    lens = [n for _, n in runs]
    sides = [b for b, _ in runs]

    # 1-1 pingpong rõ
    if len(seq) >= 10 and all(seq[-i] != seq[-i-1] for i in range(1, min(10, len(seq)))):
        return 1-last_side, 0.78, 'Cầu 1-1'

    # Cầu A-B chuẩn, ưu tiên các nhịp user hay dùng: 1-2, 2-2, 1-3, 3-1, 11...
    if len(runs) >= 5 and all(sides[i] != sides[i-1] for i in range(1, len(sides))):
        # thử nhiều cặp ở tail, chọn cặp lặp tốt nhất
        best = None
        for off in (0,1):
            pairs=[]
            st=max(0, len(lens)-12+off)
            for i in range(st, len(lens)-1, 2):
                a,b = lens[i], lens[i+1]
                if 1 <= a <= 12 and 1 <= b <= 12:
                    pairs.append((a,b))
            if not pairs:
                continue
            cand = pairs[-1]
            hit = sum(1 for x in pairs[-5:] if x == cand)
            near = sum(1 for a,b in pairs[-5:] if abs(a-cand[0]) <= 1 and abs(b-cand[1]) <= 1)
            score = 0.46 + hit*0.105 + near*0.035
            if best is None or score > best[0]:
                best=(score,cand)
        if best:
            score,(a,b)=best
            expected = b
            # đang trong run hiện tại: chưa đủ nhịp thì giữ, đủ/vượt nhịp thì đổi
            nxt = last_side if last_len < expected else 1-last_side
            # Bẻ cầu chỉ khi vượt nhịp đủ xa, không bẻ non
            if last_len >= expected + 2 and last_len >= 4:
                return 1-last_side, min(0.78, score+0.07), f'Bẻ cầu {a}-{b} vượt nhịp'
            return nxt, min(0.82, score), f'Cầu {a}-{b}'

    # bệt: giữ vừa phải, bẻ khi quá dài
    if last_len >= 10:
        return 1-last_side, 0.66, f'Bẻ bệt {last_len}'
    if last_len >= 4:
        return last_side, min(0.70, 0.49 + last_len*0.035), f'Giữ bệt {last_len}'

    return None, 0.0, 'Đa cầu tổng hợp'

def _v130_tail_replay_vote(seq):
    seq = _as_old_to_new(seq)[-420:]
    best = (None, 0.0, '')
    for L in range(3, min(36, len(seq)//2)+1):
        tail = seq[-L:]
        nxt=[]
        for i in range(0, len(seq)-L):
            if seq[i:i+L] == tail and i+L < len(seq):
                nxt.append(seq[i+L])
        if len(nxt) >= 3:
            p = (sum(nxt)+1)/(len(nxt)+2)
            st = min(0.78, len(nxt)/13.0) * abs(p-0.5)*2
            if st > best[1]:
                best = (1 if p >= 0.5 else 0, st, f'Tự học đuôi L{L}')
    return best

def _ultra_pattern_vote(bits, gate=None):
    """Hybrid ổn định: nhận cầu + replay + Markov, nhưng không đè bừa khi tín hiệu yếu."""
    seq = _as_old_to_new(bits)[-900:]
    if len(seq) < 8:
        return 0, 0.0, 'Chưa đủ lịch sử', []
    gate = normalize_gate(gate or '')
    tune = globals().get('GATE_TUNING', {}).get(gate, {'markov':1,'pattern':1,'cycle':1,'tail':1})
    votes=[]; details=[]

    bit, st, name = _v130_run_vote(seq)
    if bit is not None and st >= 0.43:
        votes.append((1 if bit else -1, st, 1.55*tune.get('cycle',1), name))
        details.append((name, round(st,3)))

    # Giữ lại bank pattern v126 nếu có, nhưng nâng ngưỡng để tránh loạn.
    try:
        best=(None,0,None)
        for nm, pat, w in globals().get('V126_PATTERNS', []):
            b, ratio = _v126_tail_match(seq, pat)
            if ratio > best[1]: best=(nm,ratio,b)
            if b is not None and ratio >= 0.66:
                strength = min(0.80, (ratio-0.52)*1.55)
                votes.append((1 if b else -1, strength, w*0.92*tune.get('pattern',1), nm))
        if best[0]: details.append((best[0], round(best[1],3)))
    except Exception:
        pass

    b, st, nm = _v130_tail_replay_vote(seq)
    if b is not None and st >= 0.11:
        votes.append((1 if b else -1, st, 1.12*tune.get('tail',1), nm))
        details.append((nm, round(st,3)))

    try:
        mv, ms = _nomd5_markov_vote(seq)
        if ms >= 0.045:
            votes.append((mv, min(ms,0.62), 1.05*tune.get('markov',1), 'Markov theo cổng'))
            details.append(('Markov theo cổng', round(ms,3)))
    except Exception:
        pass

    if not votes:
        return 0, 0.0, name, details[:5]
    score = sum(v*st*w for v,st,w,_ in votes)
    den = sum(st*w for _,st,w,_ in votes) or 1.0
    side = 1 if score >= 0 else -1
    agree = min(1.0, abs(score)/den)
    same=[(nm,st*w) for v,st,w,nm in votes if v == side]
    same.sort(key=lambda x: x[1], reverse=True)
    cname = same[0][0] if same else (details[0][0] if details else 'Đa cầu tổng hợp')
    return side, agree, cname, details[:6]

def detect_bridge_type(seq, gate=None, predicted=None):
    seq = _as_old_to_new(seq)[-260:]
    if len(seq) < 8:
        return 'Chưa đủ lịch sử'
    side, agree, cname, details = _ultra_pattern_vote(seq, gate)
    pct = int(round(max(0.0, agree)*100))
    return f'{cname} · khớp {pct}%' if cname else 'Đa cầu tổng hợp'

try:
    _v130_base_predict_nomd5 = _v126_old_predict_nomd5
except Exception:
    _v130_base_predict_nomd5 = predict_nomd5

def predict_nomd5(gate='lc79', level='basic', history=None):
    gate = normalize_gate(gate or 'lc79')
    level = str(level or 'basic').lower()
    # dùng base cũ làm nền để không làm thuật toán đang ổn thành loạn
    try:
        p = _v130_base_predict_nomd5(gate, level, history)
    except Exception as e:
        p = {'engine': ENGINE_LABEL, 'game': gate.upper(), 'period':'API-LỖI', 'last_period':'?', 'taixiu':'ĐANG CHỜ', 'tx_conf':0, 'prob_tai':'0%', 'prob_xiu':'0%', 'latest_actual':'', 'details':[str(e)[:80]]}
    if not isinstance(p, dict):
        p = {}
    p['engine'] = ENGINE_LABEL
    hb = _v130_bits_from_api_and_history(gate, history, 900)
    if hb:
        side, agree, cname, detail = _ultra_pattern_vote(hb, gate)
        base_res = _v126_side_norm(p.get('taixiu'))
        # chỉ đè kết quả khi tín hiệu khá mạnh; nếu yếu thì giữ base để tránh gãy loạn
        if side and agree >= 0.40:
            if gate == 'bcr':
                p['taixiu'] = 'BANKER' if side >= 0 else 'PLAYER'
            else:
                p['taixiu'] = 'TÀI' if side >= 0 else 'XỈU'
        elif base_res in ('TÀI','XỈU','BANKER','PLAYER','TIE'):
            pass
        try:
            bt, n = _v116_backtest_rate(hb, gate, 90)
        except Exception:
            bt, n = None, 0
        cap = {'free':62, 'basic':72, 'pro':82}.get(level, 72)
        old_conf = int(float(str(p.get('tx_conf',0)).replace('%','') or 0))
        if bt is not None:
            conf = int(round((bt*100)*0.50 + (52 + agree*32)*0.50))
            p['backtest_rate'] = round(bt*100, 1); p['backtest_n'] = n
        else:
            conf = int(round(51 + agree*30))
        # không để confidence ảo quá, nhưng cũng không tụt khi base đang có tín hiệu
        p['tx_conf'] = int(_clamp(max(min(old_conf, cap), conf), 48, cap))
        p['bridge_type'] = detect_bridge_type(hb, gate, p.get('taixiu'))
        p['trend'] = 'Hybrid cầu A-B + bẻ cầu có điều kiện + tự học đuôi + Markov ổn định'
        p['details'] = ['V130 SPEED HYBRID', cname] + [str(x[0]) for x in detail[:3]]
    return _v126_fix_probs(p, gate)

def _v130_safe_edit(bot_obj, chat_id, message_id, text, markup=None):
    try:
        bot_obj.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
        return True
    except Exception as e:
        if 'message is not modified' not in str(e).lower():
            try: log(f'edit message lỗi: {e}')
            except Exception: pass
        return False

# Live API nhanh, tự refresh 3s, không gửi đúng/sai từ session cũ.
def start_nomd5_live(bot_obj, chat_id, message_id, uid, gate, plan):
    uid = str(uid); gate = normalize_gate(gate); plan = str(plan or 'basic')
    sid = _new_live_session(uid, gate, plan)
    key = f'{chat_id}:{message_id}:{sid}'
    globals().setdefault('_nomd5_live_jobs', {})[key] = {'alive': True, 'uid': uid, 'gate': gate, 'plan': plan, 'session_id': sid, 'started': time.time(), 'last_tick': 0}
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Quay lại chọn cổng', callback_data='mode_nomd5'), InlineKeyboardButton('🏠 Menu', callback_data='back_home'))
    _v130_safe_edit(bot_obj, chat_id, message_id, f'⚡ <b>Đang mở API {gate_name(gate)}</b>\n\nĐang lấy phiên mới, tự cập nhật mỗi 3 giây...', kb)

    def notice(cid, pred_period, pred, actual, win, session_id):
        try:
            if not _is_live_session(uid, session_id): return
            msg = bot_obj.send_message(cid, ('✅' if win else '❌') + f' <b>Phiên {pred_period}</b> {"thắng" if win else "thua"} · Dự đoán: <b>{pred}</b> · KQ: <b>{actual}</b>', parse_mode='HTML')
            if not _is_live_session(uid, session_id):
                try: bot_obj.delete_message(cid, msg.message_id)
                except Exception: pass
                return
            db.setdefault('prediction_checks', []).append({'user_id':uid,'gate':gate,'plan':plan,'period':pred_period,'predict':pred,'actual':actual,'win':win,'time':now_str(),'session_id':session_id})
            update_live_streak(uid, gate, plan, win)
            st = db.setdefault('api_winloss', {}).setdefault(f'{gate}:{plan}', {'win':0,'lose':0})
            st['win' if win else 'lose'] = int(st.get('win' if win else 'lose',0)) + 1
            save_db()
            time.sleep(3)
            try: bot_obj.delete_message(cid, msg.message_id)
            except Exception: pass
        except Exception as e:
            try: log(f'V130 notice lỗi {gate}: {e}')
            except Exception: pass

    def worker():
        last_text = None
        last_pred = None
        last_period_seen = None
        idle_errors = 0
        while True:
            job = globals().get('_nomd5_live_jobs', {}).get(key)
            if not job or not job.get('alive') or not _is_live_session(uid, sid):
                break
            try:
                # check gói thật ở mỗi tick
                user = db.get('users', {}).get(uid, {})
                if plan in ('basic','pro') and not has_active_plan(user, plan):
                    stop_all_live_by_user(uid)
                    _v130_safe_edit(bot_obj, chat_id, message_id, '⛔ <b>Gói đã hết hạn</b>\n\nBấm /start để mua/chọn lại gói mới.', kb_home())
                    return
                if plan == 'free' and not free_is_active():
                    stop_all_live_by_user(uid)
                    _v130_safe_edit(bot_obj, chat_id, message_id, '⛔ <b>Free mode đã hết thời gian</b>\n\nBấm /start để chọn gói khác.', kb_home())
                    return
                hist = recent_history_for_gate(gate or '', 500)
                p = predict_nomd5(gate, plan, hist)
                cur_period = str(p.get('period') or '')
                last_period = str(p.get('last_period') or '')
                latest_actual = _v126_side_norm(p.get('latest_actual'))
                # Chốt phiên cũ khi API xác nhận last_period == phiên đã dự đoán, chỉ dùng latest_actual thật.
                if last_pred and last_period and str(last_pred.get('period')) == last_period and latest_actual in ('TÀI','XỈU','BANKER','PLAYER','TIE'):
                    pred = _v126_side_norm(last_pred.get('result'))
                    if pred in ('TÀI','XỈU','BANKER','PLAYER','TIE') and _is_live_session(uid, sid):
                        threading.Thread(target=notice, args=(chat_id, last_pred.get('period'), pred, latest_actual, pred == latest_actual, sid), daemon=True).start()
                        last_pred = None
                p['streak'] = current_streak_text(gate, plan, uid)
                text = format_nomd5_reply(gate, p)
                # ép edit khi đổi phiên dù text giống một phần
                if text != last_text or cur_period != last_period_seen:
                    if _is_live_session(uid, sid):
                        _v130_safe_edit(bot_obj, chat_id, message_id, text, kb)
                        last_text = text; last_period_seen = cur_period
                if cur_period and _v126_side_norm(p.get('taixiu')) not in ('ĐANG CHỜ',''):
                    last_pred = {'period': cur_period, 'result': p.get('taixiu'), 'session_id': sid}
                idle_errors = 0
                time.sleep(3)
            except Exception as e:
                idle_errors += 1
                try: log(f'V130 live lỗi {gate}: {e}')
                except Exception: pass
                time.sleep(1.5 if idle_errors < 4 else 3)
        try: globals().get('_nomd5_live_jobs', {}).pop(key, None)
        except Exception: pass

    threading.Thread(target=worker, daemon=True).start()

# Child bot dùng chung start_live/format của bot chính; watchdog nhẹ để không chết lặng.
try:
    CHILD_BOT_REFRESH_SECONDS = 3
except Exception:
    pass

# ===================== END V130 SPEED + STABLE HYBRID PATCH =====================



# ===================== V131 PATCH: SELECTIVE LIGHT ENGINE + BCR/API FIX (KEEP MD5) =====================
# Giữ nguyên toàn bộ dự đoán MD5/hash; chỉ lọc engine API live để bớt gãy và vá Baccarat.
ENGINE_LABEL = "Mới Nhất"

# Alias API Baccarat/typo để HTML hoặc admin gọi kiểu nào cũng về bcr.
def normalize_gate(gate):
    g = str(gate or "").strip().lower().replace(" ", "").replace("-", "_")
    alias = {
        "baccarat":"bcr", "bacarat":"bcr", "baccaratapi":"bcr", "bcrapi":"bcr",
        "bai_cao":"bcr", "xocdia":"sicb52", "sicbo_b52":"sicb52", "sicbo_hitclub":"sichit",
        "hit":"hitclub", "hc":"hitclub", "sun":"sunwin", "lc":"lc79"
    }
    return alias.get(g, g or "hitclub")

try:
    _v131_base_predict_nomd5 = predict_nomd5
except Exception:
    _v131_base_predict_nomd5 = None

def _v131_pct_to_int(v, default=0):
    try:
        return int(float(str(v).replace('%','').strip()))
    except Exception:
        return default

def _v131_fix_side_percent(p, gate):
    """Không để dự đoán Xỉu mà Tài % cao hơn; Baccarat B/P/T cũng cân lại."""
    try:
        gate = normalize_gate(gate)
        res = str(p.get('taixiu') or p.get('result') or '').upper()
        conf = int(_clamp(_v131_pct_to_int(p.get('tx_conf'), 0), 0, 99))
        if not conf:
            conf = max(_v131_pct_to_int(p.get('prob_tai'), 0), _v131_pct_to_int(p.get('prob_xiu'), 0), 50)
        if gate == 'bcr':
            tie = _v131_pct_to_int(p.get('prob_tie'), 5)
            tie = int(_clamp(tie, 3, 18))
            main = int(_clamp(conf, 50, 92))
            if main + tie > 98:
                main = 98 - tie
            other = max(1, 100 - main - tie)
            if res in ('BANKER','TÀI','TAI'):
                p['taixiu'] = 'BANKER'; p['prob_tai'] = f'{main}%'; p['prob_xiu'] = f'{other}%'; p['prob_tie'] = f'{tie}%'
            elif res in ('PLAYER','XỈU','XIU'):
                p['taixiu'] = 'PLAYER'; p['prob_xiu'] = f'{main}%'; p['prob_tai'] = f'{other}%'; p['prob_tie'] = f'{tie}%'
            elif res in ('TIE','HÒA','HOA'):
                p['taixiu'] = 'TIE'; p['prob_tie'] = f'{max(main, tie)}%'
            return p
        # TX/Sicbo
        main = int(_clamp(conf, 45, 88))
        other = 100 - main
        if res in ('TÀI','TAI','BIG','B'):
            p['taixiu'] = 'TÀI'; p['prob_tai'] = f'{main}%'; p['prob_xiu'] = f'{other}%'
        elif res in ('XỈU','XIU','SMALL','S'):
            p['taixiu'] = 'XỈU'; p['prob_xiu'] = f'{main}%'; p['prob_tai'] = f'{other}%'
    except Exception:
        pass
    return p

def _v131_signal_quality(p, gate):
    """Ít nhưng chắc: nếu tín hiệu yếu thì BỎ QUA thay vì cố ra lệnh."""
    try:
        conf = _v131_pct_to_int(p.get('tx_conf'), 0)
        agree = float(p.get('vote_agree') or 0)
        hist = int(p.get('history_len') or 0)
        bt = p.get('backtest_rate')
        bt_n = int(p.get('backtest_n') or 0)
        score = 0
        score += (conf - 50) * 1.15
        score += min(agree, 10) * 2.2
        score += min(hist, 80) * 0.08
        if bt is not None and bt_n >= 12:
            score += (float(bt) - 50) * 0.55
        # Nếu cầu quá rối/đa cầu mà conf thấp thì bỏ qua.
        bridge = str(p.get('bridge_type') or '').lower()
        if 'đa cầu' in bridge or 'chưa đủ' in bridge:
            score -= 6
        if normalize_gate(gate) == 'bcr':
            score -= 2  # baccarat hay nhiễu tie hơn, lọc chặt hơn
        return score
    except Exception:
        return 0

# Override nhẹ predict_nomd5: không đụng MD5, chỉ làm API game sạch tín hiệu hơn.
def predict_nomd5(gate="lc79", level="basic", history=None):
    if _v131_base_predict_nomd5 is None:
        return {}
    gate = normalize_gate(gate)
    p = _v131_base_predict_nomd5(gate, level, history)
    if not isinstance(p, dict):
        return p
    p['engine'] = ENGINE_LABEL
    p = _v131_fix_side_percent(p, gate)
    q = _v131_signal_quality(p, gate)
    conf = _v131_pct_to_int(p.get('tx_conf'), 0)
    # Pro vẫn dự đoán, nhưng tín hiệu quá yếu thì khuyến nghị bỏ qua, không fake %.
    if q < 22 or conf < (56 if str(level).lower() != 'pro' else 54):
        p['advice'] = '⏸️ BỎ QUA'
        p['stake_level'] = 0
        p['risk'] = 'CAO'
        p['risk_emoji'] = '🔴'
        p['advice_reason'] = 'Tín hiệu cầu yếu/rối, bỏ qua để giảm gãy.'
    elif q < 34:
        p['advice'] = '⚖️ CÂN NHẮC'
        p['stake_level'] = 1
        p['risk'] = 'TRUNG BÌNH'
        p['risk_emoji'] = '🟡'
    else:
        p['advice'] = '✅ NÊN THEO'
        p['stake_level'] = 2
        p['risk'] = 'THẤP' if conf >= 66 else 'TRUNG BÌNH'
        p['risk_emoji'] = '🟢' if conf >= 66 else '🟡'
    p['details'] = list(dict.fromkeys((p.get('details') or []) + ['Lọc tín hiệu yếu', 'Không bẻ non']))[:8]
    return p

# API route phụ cho các HTML gọi nhầm /api/predict/baccarat hoặc /api/game/baccarat.
@app.route('/api/predict/<gate>', methods=['GET','OPTIONS'])
def api_predict_gate_slug_v131(gate):
    if request.method == 'OPTIONS':
        resp = jsonify({'ok': True})
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = '*'
        return resp
    gate = normalize_gate(gate)
    level = str(request.args.get('level') or 'pro').lower()
    hist = request.args.get('history') or request.args.get('h') or ''
    p = predict_nomd5(gate, level, hist)
    payload = _api_payload_from_predict(f'predict_{gate}', gate, level, p, gate_name(gate))
    resp = jsonify(payload)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

# ===================== END V131 PATCH =====================



# ===================== V133 SPEED / DELAY HARD FIX =====================
# Giữ nguyên thuật toán V131/MD5, chỉ sửa nghẽn phản hồi: timeout API thấp, cache chống spam,
# refresh live 3s thật, bỏ sleep thừa trước khi báo đúng/sai, chống nhiều thread cũ làm bot chậm.
FAST_API_REFRESH = 3
FAST_API_CACHE_TTL = 2.8
FAST_API_STALE_TTL = 30
FAST_API_CONNECT_TIMEOUT = 1.15
FAST_API_READ_TIMEOUT = 2.15
_FETCH_LOCKS = globals().setdefault('_FETCH_LOCKS', {})

try:
    import requests as _requests_v133
    _FAST_SESSION = _requests_v133.Session()
    _FAST_ADAPTER = _requests_v133.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=50, max_retries=0)
    _FAST_SESSION.mount('http://', _FAST_ADAPTER)
    _FAST_SESSION.mount('https://', _FAST_ADAPTER)
except Exception:
    _FAST_SESSION = requests


def _fetch_nomd5_api(gate, health_only=False):
    gate = normalize_gate(gate)
    spec = NOMD5_API_MAP.get(gate)
    if not spec:
        return False, {'error': 'Cổng chưa có API'}
    now = time.time()
    ck = _nomd5_cache.get(gate)
    # Cache ngắn để user PC/đt/bot con không cùng lúc bắn 10 request ra API gốc.
    if ck and now - ck.get('time', 0) < FAST_API_CACHE_TTL:
        return True, ck.get('data')
    lock = _FETCH_LOCKS.setdefault(gate, threading.Lock())
    # Nếu một thread khác đang fetch, trả cache cũ ngay để bot không đứng im.
    if not lock.acquire(blocking=False):
        if ck and now - ck.get('time', 0) < FAST_API_STALE_TTL:
            return True, ck.get('data')
        return False, {'error': 'API đang cập nhật, thử lại sau 1-2s'}
    try:
        # Sau khi lấy lock, check cache lần nữa.
        ck = _nomd5_cache.get(gate)
        now = time.time()
        if ck and now - ck.get('time', 0) < FAST_API_CACHE_TTL:
            return True, ck.get('data')
        urls = get_api_urls_for_gate(gate) or (spec.get('urls') or ([spec.get('url')] if spec.get('url') else []))
        headers = {
            'User-Agent': 'Mozilla/5.0 KingBot-Fast/V133',
            'Accept': 'application/json,text/plain,*/*',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        }
        errors=[]
        deadline = time.time() + (3.2 if not health_only else 1.6)
        for url in urls:
            if not url or time.time() > deadline:
                break
            try:
                r = _FAST_SESSION.get(url, headers=headers, timeout=(FAST_API_CONNECT_TIMEOUT, FAST_API_READ_TIMEOUT))
                if r.status_code != 200:
                    errors.append(f'{url} -> HTTP {r.status_code}')
                    continue
                body = (r.text or '').strip()
                try:
                    data = r.json()
                except Exception:
                    try: data = json.loads(body)
                    except Exception:
                        errors.append(f'{url} -> không phải JSON')
                        continue
                payload = _extract_nomd5_payload(data, spec)
                if not payload or not payload.get('period'):
                    errors.append(f'{url} -> thiếu phiên')
                    continue
                payload['raw'] = data
                payload['source_url'] = url
                _nomd5_cache[gate] = {'time': time.time(), 'data': payload}
                _nomd5_health[gate] = {'time': time.time(), 'ok': True, 'error': ''}
                return True, payload
            except Exception as e:
                errors.append(f'{url} -> {type(e).__name__}: {str(e)[:80]}')
        # API gốc chậm/lỗi: dùng stale cache để màn không loading vô hạn.
        ck = _nomd5_cache.get(gate)
        if ck and time.time() - ck.get('time', 0) < FAST_API_STALE_TTL:
            data = dict(ck.get('data') or {})
            data['stale'] = True
            data['error'] = 'API gốc chậm, dùng cache gần nhất'
            return True, data
        err = ' | '.join(errors[-3:]) if errors else 'Không có URL API'
        _nomd5_health[gate] = {'time': time.time(), 'ok': False, 'error': err[:180]}
        return False, {'error': err[:240]}
    finally:
        try: lock.release()
        except Exception: pass


def start_nomd5_live(bot_obj, chat_id, message_id, uid, gate, plan):
    uid = str(uid); gate = normalize_gate(gate); plan = str(plan or 'basic')
    sid = _new_live_session(uid, gate, plan)
    key = f'{chat_id}:{message_id}:{sid}'
    globals().setdefault('_nomd5_live_jobs', {})[key] = {'alive': True, 'uid': uid, 'gate': gate, 'plan': plan, 'session_id': sid, 'started': time.time()}

    def _result_notice(cid, pred_period, pred, actual, win, user_id, gate_key, plan_key, session_id):
        try:
            if not _is_live_session(user_id, session_id):
                return
            tmp = bot_obj.send_message(
                cid,
                ('✅' if win else '❌') + f" <b>Phiên {pred_period}</b> {('thắng' if win else 'thua')} · Dự đoán: <b>{pred}</b> · KQ: <b>{actual}</b>",
                parse_mode='HTML'
            )
            if not _is_live_session(user_id, session_id):
                try: bot_obj.delete_message(cid, tmp.message_id)
                except Exception: pass
                return
            db.setdefault('prediction_checks', []).append({
                'user_id': str(user_id), 'gate': gate_key, 'plan': plan_key, 'period': pred_period,
                'predict': pred, 'actual': actual, 'win': win, 'time': now_str(), 'session_id': session_id
            })
            update_live_streak(str(user_id), gate_key, plan_key, win)
            key_stat = f'{gate_key}:{plan_key}'
            st = db.setdefault('api_winloss', {}).setdefault(key_stat, {'win':0,'lose':0})
            st['win' if win else 'lose'] = int(st.get('win' if win else 'lose', 0)) + 1
            save_db()
            _schedule_delete_message(bot_obj, cid, tmp.message_id, 3)
        except Exception as e:
            try: log(f'V133 gửi/chốt thắng thua lỗi {gate_key}: {e}')
            except Exception: pass

    def worker():
        last_text = None
        last_pred = None
        closed_periods = set()
        last_edit_time = 0
        # Chạy tới 12h/màn; /start/quay lại/chạy API mới sẽ kill bằng session id.
        for _ in range(14400):
            job = globals().get('_nomd5_live_jobs', {}).get(key)
            if not job or not job.get('alive') or not _is_live_session(uid, sid):
                break
            loop_start = time.time()
            try:
                user = db.get('users', {}).get(uid, {})
                if plan in ('basic','pro') and not has_active_plan(user, plan):
                    stop_all_live_by_user(uid)
                    try:
                        bot_obj.edit_message_text('⛔ <b>Gói đã hết hạn</b>\n\nBấm /start để mua/chọn lại gói mới.', chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return
                if plan == 'free' and not free_is_active():
                    stop_all_live_by_user(uid)
                    try:
                        bot_obj.edit_message_text('⛔ <b>Free mode đã hết thời gian</b>\n\nBấm /start để chọn gói khác.', chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return

                hist = recent_history_for_gate(gate or '', 500)
                p = predict_nomd5(gate, plan, hist)

                # Chốt phiên cũ: chỉ 1 lần, đúng session, không delay trước khi gửi thông báo.
                if last_pred and p.get('last_period') and str(p.get('last_period')) == str(last_pred.get('period')):
                    period_key = str(last_pred.get('period'))
                    if period_key not in closed_periods:
                        actual = str(p.get('latest_actual') or p.get('taixiu') or '').upper()
                        pred = str(last_pred.get('result') or '').upper()
                        if actual and pred and actual not in ('ĐANG CHỜ','') and _is_live_session(uid, sid):
                            closed_periods.add(period_key)
                            win = (actual == pred)
                            threading.Thread(target=_result_notice, args=(chat_id, period_key, pred, actual, win, uid, gate, plan, sid), daemon=True).start()
                    last_pred = None

                p['streak'] = current_streak_text(gate, plan, uid)
                text = format_nomd5_reply(gate, p)
                if text != last_text and _is_live_session(uid, sid) and time.time() - last_edit_time >= 1.0:
                    try:
                        bot_obj.edit_message_text(
                            text, chat_id, message_id, parse_mode='HTML',
                            reply_markup=InlineKeyboardMarkup().add(
                                InlineKeyboardButton('🔙 Quay lại chọn cổng', callback_data='mode_nomd5'),
                                InlineKeyboardButton('🏠 Menu', callback_data='back_home')
                            )
                        )
                        last_text = text
                        last_edit_time = time.time()
                    except Exception as e:
                        # Telegram trả "message is not modified" thì bỏ qua, không để chết vòng live.
                        if 'not modified' not in str(e).lower():
                            log(f'V133 edit live lỗi {gate}: {e}')
                if p.get('period') and p.get('taixiu') not in ('ĐANG CHỜ',''):
                    # Không ghi đè dự đoán đang chờ chốt nếu vẫn cùng phiên.
                    if not last_pred or str(last_pred.get('period')) != str(p.get('period')):
                        last_pred = {'period': p.get('period'), 'result': p.get('taixiu')}
            except Exception as e:
                try: log(f'V133 API live update lỗi {gate}: {e}')
                except Exception: pass
            # Refresh 3s thật, trừ thời gian xử lý để không bị trôi sang 5-10s.
            wait = max(0.35, FAST_API_REFRESH - (time.time() - loop_start))
            time.sleep(wait)
        try:
            globals().get('_nomd5_live_jobs', {}).pop(key, None)
        except Exception:
            pass
    threading.Thread(target=worker, daemon=True).start()

# Child bot scan nhanh hơn, tránh add token xong phải chờ quá lâu.
_CHILD_SCAN_SECONDS = 3
# ===================== END V133 SPEED / DELAY HARD FIX =====================



# ===================== V134 LC79 MD5 TX + FAST START + STREAK KEEP PATCH =====================
# Ghi chú: giữ nguyên MD5 hash analyzer. Phần này chỉ thêm cổng API LC79 MD5 Tài/Xỉu phiên thật
# theo Scr.js và tối ưu khởi động API để không đứng loading lâu.
FAST_API_REFRESH = 3
FAST_API_CACHE_TTL = 2.2
FAST_API_STALE_TTL = 45
FAST_API_CONNECT_TIMEOUT = 0.85
FAST_API_READ_TIMEOUT = 1.85

def _v134_bootstrap_lc79_md5_api():
    try:
        cfg.setdefault('gates', {})
        cfg['gates'].setdefault('lc79md5', {'name':'LC79 MD5 TX', 'icon':'🧬', 'enabled':True, 'md5':False, 'nomd5':True})
        cfg['gates']['lc79md5'].update({'name': cfg['gates']['lc79md5'].get('name','LC79 MD5 TX'), 'icon': cfg['gates']['lc79md5'].get('icon','🧬'), 'enabled': True, 'md5': False, 'nomd5': True})
        cfg.setdefault('custom_api_urls', {}).setdefault('lc79md5', [])
        cfg.setdefault('api_tools', {}).setdefault('lc79md5_tool', {'enabled':True, 'name':'LC79 MD5 TX API', 'gate':'lc79md5', 'level':'pro', 'secret':'', 'cors':True})
        # Bổ sung keys theo Scr.js: item.id, resultTruyenThong, dices, point.
        for g in ('lc79','lc79md5'):
            if g not in NOMD5_API_MAP:
                NOMD5_API_MAP[g] = {}
            spec = NOMD5_API_MAP[g]
            spec.setdefault('urls', [])
            if g == 'lc79md5':
                spec['urls'] = ['https://wtxmd52.tele68.com/v1/txmd5/sessions'] + [u for u in spec.get('urls', []) if 'wtxmd52.tele68.com' not in str(u)]
            spec['period_keys'] = list(dict.fromkeys((spec.get('period_keys') or []) + ['id','sid','session','phien','Phien','issue','round','gameNum']))
            spec['predict_keys'] = list(dict.fromkeys((spec.get('predict_keys') or []) + ['resultTruyenThong','Ket_qua','ket_qua','result','taixiu','tai_xiu']))
            spec['total_keys'] = list(dict.fromkeys((spec.get('total_keys') or []) + ['point','Tong','tong','total','score','sum']))
            spec['dice_keys'] = list(dict.fromkeys((spec.get('dice_keys') or []) + ['dices','dice','xuc_xac','xucxac','xx']))
            spec['confidence_keys'] = list(dict.fromkeys((spec.get('confidence_keys') or []) + ['confidence','do_tin_cay','ti_le','rate','percent']))
        save_cfg()
    except Exception as e:
        try: log(f'V134 bootstrap LC79 MD5 API lỗi: {e}')
        except Exception: pass

_v134_bootstrap_lc79_md5_api()

# Normalize bổ sung alias user hay gõ nhầm.
_old_normalize_gate_v134 = normalize_gate
def normalize_gate(gate):
    g = _old_normalize_gate_v134(gate)
    raw = str(gate or '').lower().strip().replace('-', '').replace('_','')
    if raw in ('lc79md5','lc79nmd5','lc79n','lc79txmd5','txmd5lc79'):
        return 'lc79md5'
    if raw in ('baccarat','bacarat','bcr'):
        return 'bcr'
    return g

# Parser riêng cho API tele68: data.list hoặc list, resultTruyenThong TAI/XIU.
def _v134_extract_tele68_payload(data, spec):
    try:
        items = _flatten_recent_items(data)
        if not items and isinstance(data, dict):
            items = data.get('list') or data.get('data', {}).get('list') or []
        parsed=[]
        for it in (items or [])[:120]:
            if not isinstance(it, dict):
                continue
            period = it.get('id') or it.get('sid') or it.get('session') or it.get('phien') or it.get('Phien')
            raw = it.get('resultTruyenThong') or it.get('result') or it.get('Ket_qua') or it.get('ket_qua')
            result = _norm_tx(raw)
            dice = _parse_dice_value(it.get('dices') or it.get('dice') or it.get('xuc_xac'))
            total = it.get('point') or it.get('total') or it.get('score') or (sum(dice) if dice else None)
            if not result:
                result = _tx_from_total(total)
            if period and result:
                try: total_i = int(float(total)) if total not in (None,'') else (sum(dice) if dice else None)
                except Exception: total_i = sum(dice) if dice else None
                parsed.append({'period':str(period), 'total': total_i, 'dice': dice, 'prediction': result, 'confidence':55, 'latest':it})
        if not parsed:
            return None
        def _pnum(x):
            nums = re.findall(r'\d+', str(x.get('period','')))
            return int(nums[-1]) if nums else -1
        parsed.sort(key=_pnum, reverse=True)
        latest=parsed[0]
        history_bits=[]
        for it in parsed:
            r=_norm_tx(it.get('prediction')) or _tx_from_total(it.get('total'))
            if r == 'TÀI': history_bits.append(1)
            elif r == 'XỈU': history_bits.append(0)
        latest['history_bits'] = history_bits[:90]
        latest['history_items'] = parsed[:90]
        latest['next_period'] = _next_period_value(latest.get('period'))
        return latest
    except Exception:
        return None

_old_extract_nomd5_payload_v134 = _extract_nomd5_payload
def _extract_nomd5_payload(data, spec):
    # Ưu tiên dạng tele68/Scr.js để LC79 MD5 TX không bị nhận nhầm là MD5 hash analyzer.
    tele = _v134_extract_tele68_payload(data, spec)
    if tele:
        return tele
    return _old_extract_nomd5_payload_v134(data, spec)

# Fetch nhanh hơn: timeout thấp, custom URL trước, dùng cache stale để không treo loading.
_FETCH_LOCKS = globals().setdefault('_FETCH_LOCKS', {})
try:
    _FAST_SESSION = requests.Session()
    _FAST_ADAPTER = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=80, max_retries=0)
    _FAST_SESSION.mount('http://', _FAST_ADAPTER)
    _FAST_SESSION.mount('https://', _FAST_ADAPTER)
except Exception:
    _FAST_SESSION = requests

def _fetch_nomd5_api(gate, health_only=False):
    gate = normalize_gate(gate)
    spec = NOMD5_API_MAP.get(gate)
    if not spec:
        return False, {'error': 'Cổng chưa có API'}
    now = time.time()
    ck = _nomd5_cache.get(gate)
    if ck and now - ck.get('time', 0) < FAST_API_CACHE_TTL:
        return True, ck.get('data')
    lock = _FETCH_LOCKS.setdefault(gate, threading.Lock())
    if not lock.acquire(blocking=False):
        if ck and now - ck.get('time', 0) < FAST_API_STALE_TTL:
            data = dict(ck.get('data') or {})
            data['stale'] = True
            return True, data
        return False, {'error': 'API đang cập nhật, thử lại sau 1-2s'}
    try:
        ck = _nomd5_cache.get(gate)
        now = time.time()
        if ck and now - ck.get('time', 0) < FAST_API_CACHE_TTL:
            return True, ck.get('data')
        urls = get_api_urls_for_gate(gate) or (spec.get('urls') or ([spec.get('url')] if spec.get('url') else []))
        # LC79 MD5 TX ưu tiên API gốc trong Scr.js.
        if gate == 'lc79md5':
            urls = ['https://wtxmd52.tele68.com/v1/txmd5/sessions'] + [u for u in urls if 'wtxmd52.tele68.com' not in str(u)]
        headers={
            'User-Agent':'Mozilla/5.0 KingBot-Fast/V134',
            'Accept':'application/json,text/plain,*/*',
            'Connection':'keep-alive',
            'Cache-Control':'no-cache'
        }
        errors=[]
        deadline = time.time() + (2.7 if not health_only else 1.15)
        for url in urls:
            if not url or time.time() > deadline:
                break
            try:
                r = _FAST_SESSION.get(url, headers=headers, timeout=(FAST_API_CONNECT_TIMEOUT, FAST_API_READ_TIMEOUT))
                if r.status_code != 200:
                    errors.append(f'{url} -> HTTP {r.status_code}')
                    continue
                body=(r.text or '').strip()
                try: data=r.json()
                except Exception:
                    try: data=json.loads(body)
                    except Exception:
                        errors.append(f'{url} -> không phải JSON')
                        continue
                payload=_extract_nomd5_payload(data, spec)
                if not payload or not payload.get('period'):
                    errors.append(f'{url} -> thiếu phiên')
                    continue
                payload['raw']=data; payload['source_url']=url
                _nomd5_cache[gate]={'time':time.time(), 'data':payload}
                _nomd5_health[gate]={'time':time.time(), 'ok':True, 'error':''}
                return True, payload
            except Exception as e:
                errors.append(f'{url} -> {type(e).__name__}: {str(e)[:80]}')
        ck=_nomd5_cache.get(gate)
        if ck and time.time() - ck.get('time', 0) < FAST_API_STALE_TTL:
            data=dict(ck.get('data') or {})
            data['stale']=True
            data['error']='API gốc chậm, dùng cache gần nhất'
            return True, data
        err=' | '.join(errors[-3:]) if errors else 'Không có URL API'
        _nomd5_health[gate]={'time':time.time(), 'ok':False, 'error':err[:180]}
        return False, {'error':err[:240]}
    finally:
        try: lock.release()
        except Exception: pass

# Engine API tinh gọn: không nhồi quá nhiều vote; thêm selective/bẻ có xác nhận + LC79 MD5 TX.
_old_consensus_v134 = _nomd5_api_consensus
def _v134_selective_vote(hb_old, gate, level):
    seq=_as_old_to_new(hb_old)[-180:]
    if len(seq) < 6:
        return None
    tune=GATE_TUNING.get(normalize_gate(gate), {'markov':1,'pattern':1,'cycle':1,'tail':1})
    votes=[]
    # 1) Cầu chạy theo block a-b hiện tại.
    cname,cscore,_ = _run_signature(seq)
    cbit,cst,auto_name = _run_cycle_vote(seq)
    if cbit is not None and max(cscore,cst) >= 0.46:
        votes.append((1 if cbit else -1, max(cscore,cst), 1.45*tune.get('cycle',1), cname if cname!='Đa cầu tổng hợp' else auto_name))
    # 2) Bank pattern 1-1 tới 8-8, nhưng chỉ lấy pattern khớp cao nhất để tránh nhiễu.
    best=None
    for name, pat, w in ULTRA_RUN_PATTERNS:
        bit, ratio = _pattern_predict_from_tail(seq, pat)
        if bit is not None and ratio >= 0.70:
            val=(ratio, bit, name, w)
            if best is None or val[0] > best[0]: best=val
    if best:
        ratio, bit, name, w = best
        votes.append((1 if bit else -1, (ratio-0.50)*1.9, w*tune.get('pattern',1), name))
    # 3) Bệt/bẻ: theo bệt 3-6, bẻ khi >=8 hoặc có dấu hiệu gãy giả.
    runs=_runs(seq); last=seq[-1]; last_run=runs[-1][1] if runs else 1
    if last_run >= 8:
        votes.append((-1 if last else 1, 0.64, 1.08*tune.get('tail',1), f'Bẻ bệt {last_run}'))
    elif 3 <= last_run <= 6:
        votes.append((1 if last else -1, 0.52 + last_run*0.032, 0.98*tune.get('tail',1), f'Theo bệt {last_run}'))
    # 4) Markov nhẹ, không để lấn cầu chính.
    mv, ms = _nomd5_markov_vote(seq)
    if ms >= 0.055:
        votes.append((mv, ms, 1.12*tune.get('markov',1), 'Markov sạch'))
    if not votes:
        return None
    score=sum(v*st*w for v,st,w,_ in votes)
    den=sum(st*w for _,st,w,_ in votes) or 1
    side=1 if score >= 0 else -1
    agree=min(0.98, abs(score)/den)
    same=[(nm,st*w) for v,st,w,nm in votes if v==side]
    same.sort(key=lambda x:x[1], reverse=True)
    return ('TÀI' if side > 0 else 'XỈU'), agree, same[0][0] if same else 'Đa cầu tổng hợp'

def _nomd5_api_consensus(api, gate, level, hb_old):
    gate=normalize_gate(gate)
    sel = _v134_selective_vote(hb_old, gate, level)
    old = _old_consensus_v134(api, gate, level, hb_old)
    old_result, old_agree, period, last_period, seed, meta = old
    if sel:
        r,a,name = sel
        # Nếu selective đủ mạnh thì dùng, nếu yếu thì phối nhẹ với engine cũ.
        if a >= 0.55 or old_agree < 0.50:
            meta = dict(meta or {}); meta['pattern_name'] = name; meta['selective'] = a
            return r, a, period, last_period, seed, meta
    return old

# Streak không bị xóa khi chỉ khởi động/chạy lại API. Chỉ /start hoặc back_home/mode theo code cũ mới reset nếu user muốn.
def start_nomd5_live(bot_obj, chat_id, message_id, uid, gate, plan):
    uid = str(uid); gate = normalize_gate(gate); plan = str(plan or 'basic')
    sid = _new_live_session(uid, gate, plan)
    key = f'{chat_id}:{message_id}:{sid}'
    globals().setdefault('_nomd5_live_jobs', {})[key] = {'alive': True, 'uid': uid, 'gate': gate, 'plan': plan, 'session_id': sid, 'started': time.time()}

    def _result_notice(cid, pred_period, pred, actual, win, user_id, gate_key, plan_key, session_id):
        try:
            if not _is_live_session(user_id, session_id):
                return
            tmp = bot_obj.send_message(cid, ('✅' if win else '❌') + f' <b>Phiên {pred_period}</b> {("thắng" if win else "thua")} · Dự đoán: <b>{pred}</b> · KQ: <b>{actual}</b>', parse_mode='HTML')
            if not _is_live_session(user_id, session_id):
                try: bot_obj.delete_message(cid, tmp.message_id)
                except Exception: pass
                return
            db.setdefault('prediction_checks', []).append({'user_id': str(user_id), 'gate': gate_key, 'plan': plan_key, 'period': pred_period, 'predict': pred, 'actual': actual, 'win': win, 'time': now_str(), 'session_id': session_id})
            update_live_streak(str(user_id), gate_key, plan_key, win)
            key_stat=f'{gate_key}:{plan_key}'
            st=db.setdefault('api_winloss', {}).setdefault(key_stat, {'win':0,'lose':0})
            st['win' if win else 'lose'] = int(st.get('win' if win else 'lose', 0)) + 1
            save_db()
            _schedule_delete_message(bot_obj, cid, tmp.message_id, 3)
        except Exception as e:
            try: log(f'V134 gửi/chốt thắng thua lỗi {gate_key}: {e}')
            except Exception: pass

    def worker():
        last_text = None
        last_pred = None
        closed_periods = set()
        last_edit_time = 0
        # Edit màn ngay bằng cache/placeholder, không chờ API dài.
        for _ in range(14400):
            job=globals().get('_nomd5_live_jobs', {}).get(key)
            if not job or not job.get('alive') or not _is_live_session(uid, sid):
                break
            loop_start=time.time()
            try:
                user=db.get('users', {}).get(uid, {})
                if plan in ('basic','pro') and not has_active_plan(user, plan):
                    stop_all_live_by_user(uid)
                    try: bot_obj.edit_message_text('⛔ <b>Gói đã hết hạn</b>\n\nBấm /start để mua/chọn lại gói mới.', chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return
                if plan == 'free' and not free_is_active():
                    stop_all_live_by_user(uid)
                    try: bot_obj.edit_message_text('⛔ <b>Free mode đã hết thời gian</b>\n\nBấm /start để chọn gói khác.', chat_id, message_id, parse_mode='HTML', reply_markup=kb_home())
                    except Exception: pass
                    return
                hist=recent_history_for_gate(gate or '', 500)
                p=predict_nomd5(gate, plan, hist)
                if last_pred and p.get('last_period') and str(p.get('last_period')) == str(last_pred.get('period')):
                    period_key=str(last_pred.get('period'))
                    if period_key not in closed_periods:
                        actual=str(p.get('latest_actual') or '').upper()
                        pred=str(last_pred.get('result') or '').upper()
                        if actual and pred and actual not in ('ĐANG CHỜ','') and _is_live_session(uid, sid):
                            closed_periods.add(period_key)
                            threading.Thread(target=_result_notice, args=(chat_id, period_key, pred, actual, actual==pred, uid, gate, plan, sid), daemon=True).start()
                    last_pred=None
                p['streak']=current_streak_text(gate, plan, uid)
                text=format_nomd5_reply(gate, p)
                if text != last_text and _is_live_session(uid, sid) and time.time() - last_edit_time >= 0.75:
                    try:
                        bot_obj.edit_message_text(text, chat_id, message_id, parse_mode='HTML', reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton('🔙 Quay lại chọn cổng', callback_data='mode_nomd5'), InlineKeyboardButton('🏠 Menu', callback_data='back_home')))
                        last_text=text; last_edit_time=time.time()
                    except Exception as e:
                        if 'not modified' not in str(e).lower(): log(f'V134 edit live lỗi {gate}: {e}')
                if p.get('period') and p.get('taixiu') not in ('ĐANG CHỜ',''):
                    if not last_pred or str(last_pred.get('period')) != str(p.get('period')):
                        last_pred={'period': p.get('period'), 'result': p.get('taixiu')}
            except Exception as e:
                try: log(f'V134 API live update lỗi {gate}: {e}')
                except Exception: pass
            time.sleep(max(0.35, FAST_API_REFRESH - (time.time() - loop_start)))
        try: globals().get('_nomd5_live_jobs', {}).pop(key, None)
        except Exception: pass
    threading.Thread(target=worker, daemon=True).start()

# ===================== END V134 PATCH =====================


# ===================== V135 LC79 MD5 BUTTON + FAST PREWARM PATCH =====================
# Sửa dứt điểm: LC79 MD5 TX phải hiện trong chọn API + API Tool, và khởi động API không đứng chờ lần fetch đầu.
LC79_MD5_GATE_KEY = 'lc79md5'
LC79_MD5_NAME = 'LC79 MD5 TX'
LC79_MD5_URL = 'https://wtxmd52.tele68.com/v1/txmd5/sessions'


def ensure_lc79md5_visible():
    try:
        cfg.setdefault('gates', {})
        cfg['gates'][LC79_MD5_GATE_KEY] = {
            'name': LC79_MD5_NAME,
            'icon': '🧬',
            'enabled': True,
            'md5': False,
            'nomd5': True
        }
        cfg.setdefault('custom_api_urls', {}).setdefault(LC79_MD5_GATE_KEY, [])
        cfg.setdefault('api_tools', {})
        cfg['api_tools'].setdefault('lc79md5_tool', {
            'enabled': True,
            'name': 'LC79 MD5 TX API',
            'gate': LC79_MD5_GATE_KEY,
            'level': 'pro',
            'secret': '',
            'cors': True
        })
        cfg['api_tools'].setdefault('lc79_md5', {
            'enabled': True,
            'name': 'LC79 MD5 TX',
            'gate': LC79_MD5_GATE_KEY,
            'level': 'pro',
            'secret': '',
            'cors': True
        })
        NOMD5_API_MAP.setdefault(LC79_MD5_GATE_KEY, {})
        spec = NOMD5_API_MAP[LC79_MD5_GATE_KEY]
        spec['urls'] = [LC79_MD5_URL] + [u for u in spec.get('urls', []) if LC79_MD5_URL not in str(u)]
        spec['period_keys'] = list(dict.fromkeys((spec.get('period_keys') or []) + ['id','sid','session','Phien','phien']))
        spec['predict_keys'] = list(dict.fromkeys((spec.get('predict_keys') or []) + ['resultTruyenThong','Ket_qua','ket_qua','result']))
        spec['total_keys'] = list(dict.fromkeys((spec.get('total_keys') or []) + ['point','Tong','tong','total']))
        spec['dice_keys'] = list(dict.fromkeys((spec.get('dice_keys') or []) + ['dices','dice','xuc_xac','xucxac']))
        save_cfg()
    except Exception as e:
        try: log(f'V135 ensure LC79 MD5 visible lỗi: {e}')
        except Exception: pass

ensure_lc79md5_visible()

# Override nhẹ gates_by_mode để dù config cũ/persistent bị thiếu vẫn luôn có nút LC79 MD5 TX ở tab API.
_old_gates_by_mode_v135 = gates_by_mode
def gates_by_mode(mode='md5'):
    data = dict(_old_gates_by_mode_v135(mode) or {})
    if str(mode or '').lower() in ('nomd5','no_md5','api'):
        ensure_lc79md5_visible()
        data[LC79_MD5_GATE_KEY] = cfg['gates'][LC79_MD5_GATE_KEY]
    return data

# Override ensure_api_tools_config để Admin API Tool luôn có LC79 MD5 TX.
_old_ensure_api_tools_config_v135 = ensure_api_tools_config
def ensure_api_tools_config():
    try:
        _old_ensure_api_tools_config_v135()
    except Exception:
        pass
    ensure_lc79md5_visible()

# Warm cache nền: lúc bấm Chạy API sẽ có dữ liệu gần nhất sẵn, giảm loading rõ rệt.
def _v135_api_prewarm_worker():
    time.sleep(1.0)
    gates = ['lc79md5','lc79','hitclub','b52','sunwin','bcr']
    while True:
        try:
            for g in gates:
                try:
                    if g in NOMD5_API_MAP:
                        _fetch_nomd5_api(g, health_only=True)
                except Exception:
                    pass
                time.sleep(0.12)
        except Exception as e:
            try: log(f'V135 prewarm lỗi: {e}')
            except Exception: pass
        time.sleep(2.6)

try:
    threading.Thread(target=_v135_api_prewarm_worker, daemon=True).start()
except Exception:
    pass

# Khi format tên cổng, ép LC79 MD5 TX đúng nhãn.
_old_gate_name_v135 = gate_name
def gate_name(g):
    if normalize_gate(g) == LC79_MD5_GATE_KEY:
        return LC79_MD5_NAME
    return _old_gate_name_v135(g)

_old_gate_icon_v135 = gate_icon
def gate_icon(g):
    if normalize_gate(g) == LC79_MD5_GATE_KEY:
        return '🧬'
    return _old_gate_icon_v135(g)

# ===================== END V135 PATCH =====================

threading.Thread(target=bot_worker, daemon=True).start()
threading.Thread(target=backup_worker, daemon=True).start()
threading.Thread(target=child_bots_worker, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    log(f"Web admin chạy port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

