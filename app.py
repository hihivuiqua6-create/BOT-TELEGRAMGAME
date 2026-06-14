# -*- coding: utf-8 -*-
"""
KINGBOT ULTRA RENDER
Flask Web Admin + Telegram Polling Bot
Start command: python app.py
Build command: pip install -r requirements.txt
"""

import os, json, time, threading, secrets, hashlib, statistics, urllib.parse, random, traceback, html
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
    "gates": {
        "lc79": {"name": "LC79", "icon": "🎲", "enabled": True, "md5": True, "nomd5": True},
        "hitclub": {"name": "HitClub", "icon": "♠️", "enabled": True, "md5": True, "nomd5": True},
        "betvip": {"name": "BetVip", "icon": "💎", "enabled": True, "md5": True, "nomd5": True},
        "sunwin": {"name": "SunWin", "icon": "☀️", "enabled": True, "md5": False, "nomd5": True},
        "b52": {"name": "B52", "icon": "🚀", "enabled": True, "md5": False, "nomd5": True}
    },
    "plans": {
        "basic": {"name": "Gói Thường", "price_per_hour": 1500, "hours": 1, "level": "basic"},
        "pro": {"name": "Gói Pro", "price_per_hour": 3500, "hours": 1, "level": "pro"}
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
    "free_usage": {},
    "free_sessions": []
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
    out = {}
    for k, v in enabled_gates().items():
        if mode == "md5" and v.get("md5", True):
            out[k] = v
        elif mode in ("nomd5", "no_md5", "api") and v.get("nomd5", False):
            out[k] = v
    return out

def mode_title(mode):
    return "Dự đoán MD5" if str(mode or "md5") == "md5" else "Dự đoán No MD5"

def stable_int(*parts, mod=10000):
    raw = "|".join(map(str, parts)).encode("utf-8", "ignore")
    return int(hashlib.sha256(raw).hexdigest()[:12], 16) % mod

def current_game_period(gate):
    ts = int(time.time()) // 45
    prefix = {"sunwin":"SUN", "lc79":"LC", "hitclub":"HC", "b52":"B52", "betvip":"BV"}.get(gate, "TX")
    return f"{prefix}{ts}"

def predict_nomd5(gate="lc79", level="basic", history=None):
    gate = normalize_gate(gate)
    level = str(level or "basic").lower()
    period = current_game_period(gate)
    hb = _history_bits(history)[-80:] if history else []
    seed = f"NO-MD5-V95|{gate}|{level}|{period}|{''.join(map(str, hb))}"
    h = hashlib.sha256(seed.encode()).hexdigest()
    b = [int(h[i:i+2],16) for i in range(0,64,2)]
    base = stable_int(seed, "base", mod=10000)
    runs = _runs(hb) if hb else []
    last_run = runs[-1][1] if runs else 0
    changes = sum(hb[i]!=hb[i-1] for i in range(1,len(hb))) if hb else 0
    markov_boost = 0
    if len(hb) >= 6:
        tail2 = tuple(hb[-2:])
        same = [hb[i+2] for i in range(len(hb)-2) if tuple(hb[i:i+2]) == tail2]
        if same:
            markov_boost = int((sum(same)/len(same)-0.5)*1800)
    gate_bias = {"sunwin":180, "lc79":90, "hitclub":-60, "b52":130, "betvip":-120}.get(gate, 0)
    score = (base + markov_boost + gate_bias + b[0]*7 + b[-1]*11) % 10000
    result = "TÀI" if score >= 5000 else "XỈU"
    break_power = (stable_int(seed,"break") + last_run*777 + changes*131) % 10000
    if len(hb) >= 4 and last_run >= (3 if level == "pro" else 4) and break_power > (6200 if level == "pro" else 7200):
        result = "XỈU" if hb[-1] == 1 else "TÀI"
    conf_base = 52 if level == "free" else 58 if level == "basic" else 64
    distance = abs(score-5000)/100
    hist_bonus = min(12, len(hb)//12)
    agree = min(18, int(distance/5) + hist_bonus + (4 if last_run >= 3 else 0))
    conf = int(_clamp(conf_base + agree, conf_base, 72 if level=="free" else 86 if level=="basic" else 94))
    if len(hb) < 10:
        conf = min(conf, 60 if level != "pro" else 64)
    prob_t = conf if result == "TÀI" else 100-conf
    prob_x = 100-prob_t
    d1 = b[1] % 6 + 1; d2 = b[5] % 6 + 1; d3 = b[9] % 6 + 1
    total = d1+d2+d3
    guard=0
    while result == "TÀI" and total < 11 and guard < 12:
        if d1 < 6: d1 += 1
        elif d2 < 6: d2 += 1
        elif d3 < 6: d3 += 1
        total=d1+d2+d3; guard += 1
    guard=0
    while result == "XỈU" and total > 10 and guard < 12:
        if d1 > 1: d1 -= 1
        elif d2 > 1: d2 -= 1
        elif d3 > 1: d3 -= 1
        total=d1+d2+d3; guard += 1
    risk_score = stable_int(seed,"risk",break_power, mod=100)
    risk = "THẤP" if risk_score < 32 else "TRUNG BÌNH" if risk_score < 68 else "CAO"
    risk_emoji = "🟢" if risk == "THẤP" else "🟡" if risk == "TRUNG BÌNH" else "🔴"
    advice = "✅ NÊN THEO" if conf >= (68 if level!="pro" else 65) and risk != "CAO" else "⚖️ CÂN NHẮC" if conf >= 58 else "⏸️ BỎ QUA"
    stake = 2 if advice.startswith("✅") else 1 if advice.startswith("⚖️") else 0
    trend = "Cầu đẹp, tín hiệu tương đối sạch" if advice.startswith("✅") else "Cầu chưa sạch / ưu tiên quản lý vốn" if advice.startswith("⚖️") else "Kèo yếu / nên bỏ qua"
    details = ["API phiên", "Markov", "Cầu bẻ", "Chu kỳ", "Byte wave", "Entropy", gate_name(gate)]
    return {
        "engine":"Bản Nâng Cấp New", "game":gate.upper(), "period":period, "taixiu":result, "tx_conf":conf,
        "prob_tai":f"{prob_t}%", "prob_xiu":f"{prob_x}%", "dice":f"{d1}-{d2}-{d3}", "total":total,
        "chanle":"CHẴN" if total % 2 == 0 else "LẺ", "score":round(score/100,2), "trend":trend,
        "advice":advice, "stake_level":stake, "risk":risk, "risk_emoji":risk_emoji, "details":details,
        "history_len":len(hb), "vote_agree":round(conf/10,1), "hash_short":"NO-MD5",
        "advice_reason":"Nên theo khi cầu đẹp, đủ lịch sử và tín hiệu đồng thuận."
    }

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
        log("Chưa có group target hoặc link invite không lấy được chat_id. Hãy dùng @group_username hoặc -100chatid.")
        return False
    try:
        bot.send_message(gid, text, parse_mode="HTML")
        return True
    except Exception as e:
        log(f"Không gửi được group {gid}: {e}")
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
    confidence = min(88, 55 + int(abs(score - 50) * 0.55))
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
    confidence = min(97, 61 + int(distance * 0.72) + (chaos % 7))

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
            b.reply_to(m, "📡 Chọn cổng No MD5 trước:", reply_markup=kb)
            return
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Chạy No MD5", callback_data="run_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home"))
        b.reply_to(m, f"📡 No MD5 đã sẵn sàng\n🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>", reply_markup=kb)

    @b.message_handler(commands=["start"])
    def start(m):
        uid, user, username = get_user(m)
        log(f"/start từ {uid}")
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
            hours = int(pending["hours"])
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
            new_exp = int((datetime.fromtimestamp(base_ts) + timedelta(hours=hours)).timestamp())
            db["users"][uid]["plan_expires"][pk] = new_exp
            db["users"][uid]["active_plan"] = pk   # tương thích hiển thị cũ
            db["users"][uid]["selected_plan"] = pk
            db["users"][uid]["active_gate"] = gate
            db["users"][uid]["plan_expire"] = plan_expire_ts(db["users"][uid])
            db["users"][uid]["total_spent"] = int(db["users"][uid].get("total_spent", 0)) + total

            order = {"id": "BUY" + str(int(time.time())) + uid[-4:], "user_id": uid, "username": username, "gate": gate, "plan": pk, "hours": hours, "amount": total, "bonus": bonus, "time": now_str()}
            db["purchases"].append(order)
            db["transactions"].append({"user_id": uid, "type": "purchase", "amount": -total, "bonus": bonus, "plan": pk, "hours": hours, "time": now_str()})
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
                f"{('Gửi MD5 32 ký tự hoặc hash HitClub 64 ký tự để dự đoán ngay.' if db['users'][uid].get('predict_mode','md5') == 'md5' else 'Bấm /nomd5 hoặc nút Chọn Cổng & Gói để chạy dự đoán No MD5.')}",
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

        if data == "back_home":
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
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🔐 Dự đoán MD5", callback_data="mode_md5"))
            kb.add(InlineKeyboardButton("📡 Dự đoán No MD5", callback_data="mode_nomd5"))
            kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
            b.edit_message_text(
                "🔮 <b>CHỌN KIỂU DỰ ĐOÁN</b>\n\n"
                "1️⃣ <b>MD5</b>: nhập hash MD5/HitClub để phân tích.\n"
                "2️⃣ <b>No MD5</b>: bot tự lấy phiên/game API rồi dự đoán.\n\n"
                "Sau đó bạn sẽ chọn cổng và chọn Free / Thường / Pro.",
                chat, mid, reply_markup=kb
            )
            return

        if data in ("mode_md5", "mode_nomd5"):
            mode = "md5" if data == "mode_md5" else "nomd5"
            db["users"][uid]["predict_mode"] = mode
            save_db()
            kb = InlineKeyboardMarkup()
            for gk, gv in gates_by_mode(mode).items():
                kb.add(InlineKeyboardButton(f"{gv.get('icon', '🎮')} {gv.get('name', gk.upper())}", callback_data=f"gate_{gk}"))
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
                    chat, mid, reply_markup=kb_home()
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
                f"{('Gửi MD5 32 ký tự hoặc hash HitClub 64 ký tự để dự đoán ngay.' if db['users'][uid].get('predict_mode','md5') == 'md5' else 'Bấm Chạy No MD5 để dự đoán phiên hiện tại.')}",
                chat, mid, reply_markup=(InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Chạy No MD5", callback_data="run_nomd5"), InlineKeyboardButton("🏠 Menu", callback_data="back_home")) if db['users'][uid].get('predict_mode') == 'nomd5' else kb_home())
            )
            return

        if data == "run_nomd5":
            gate = normalize_gate(db["users"][uid].get("active_gate"))
            if gate not in gates_by_mode("nomd5"):
                b.answer_callback_query(c.id, "Cổng này không hỗ trợ No MD5", show_alert=True)
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
            hist = recent_history_for_gate(gate or "", 500)
            p = predict_nomd5(gate, plan, hist)
            db["predictions"].append({"user_id": uid, "username": username, "gate": gate, "plan": plan, "mode":"nomd5", "md5": "NO-MD5", "period": p.get("period"), "result": p["taixiu"], "confidence": p["tx_conf"], "time": now_str()})
            save_db()
            result_icon = "📈" if p["taixiu"] == "TÀI" else "📉"
            detail = " · ".join(map(str, p.get("details", [])))
            msg = (
                f"🔮 <b>DỰ ĐOÁN NO MD5 TÀI/XỈU</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Phiên bản: <b>Bản Nâng Cấp New</b>\n"
                f"🧾 Phiên: <code>{p.get('period')}</code>\n\n"
                f"🎲 Bộ số mô phỏng: <b>{p['dice']}</b> | Tổng: <b>{p['total']}</b>\n"
                f"{result_icon} Kết luận: <b>{p['taixiu']}</b>\n"
                f"📊 Độ tin cậy thực chiến: <b>{p['tx_conf']}%</b>\n"
                f"🎯 Tài/Xỉu %: <b>T {p.get('prob_tai','')} · X {p.get('prob_xiu','')}</b>\n"
                f"💰 Khuyến nghị: <b>{p.get('advice','THAM KHẢO')}</b> · Vốn: <b>{p.get('stake_level',0)}/2</b>\n"
                f"🔵 Chẵn/Lẻ: <b>{p['chanle']}</b>\n"
                f"🧠 Điểm phiên: <b>{p['score']}/100</b>\n"
                f"🧭 Xu hướng: <b>{p.get('trend','')}</b>\n"
                f"📌 Phân tích: <b>{p.get('advice_reason','Nên theo khi cầu đẹp.')}</b>\n"
                f"📚 History thật: <b>{p.get('history_len',0)}</b> phiên · Vote: <b>{p.get('vote_agree','')}</b>\n"
                f"{p['risk_emoji']} Rủi ro phiên: <b>{p['risk']}</b>\n"
                f"🧬 Lớp phân tích: <i>{detail}</i>\n\n"
                f"🍀✨ Nên theo khi cầu đẹp, tín hiệu sạch và quản lý vốn hợp lý 💎🎯"
            )
            b.edit_message_text(msg, chat, mid, reply_markup=kb_home())
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
            kb = InlineKeyboardMarkup()
            for pk, p in cfg["plans"].items():
                emoji = "💎" if pk == "pro" else ("⭐" if pk == "basic" else "🔥")
                kb.add(InlineKeyboardButton(f"{emoji} {p['name']} - {money(p.get('price_per_hour',0))}/giờ", callback_data=f"buy_{pk}"))
            kb.add(InlineKeyboardButton("🎁 Free dự đoán", callback_data="free_predict"))
            kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
            b.edit_message_text(
                f"🛒 <b>MUA GÓI PHÂN TÍCH</b>\n\n"
                f"Chọn gói rồi nhập số giờ cần mua.\n"
                f"Có gói rồi vẫn mua thêm giờ được, hệ thống tự cộng dồn hạn.\n\n"
                f"⭐ Thường còn: <b>{remaining_time_text(user, 'basic')}</b>\n"
                f"💎 Pro còn: <b>{remaining_time_text(user, 'pro')}</b>\n"
                f"💰 Số dư: <b>{money(user.get('balance',0))}</b>",
                chat, mid, reply_markup=kb
            )
            return

        if data.startswith("buy_"):
            pk = data.replace("buy_", "", 1)
            if pk not in cfg["plans"]:
                return
            p = cfg["plans"][pk]
            user_state[uid] = {"mode": "buy_hours", "plan": pk, "gate": normalize_gate(db["users"][uid].get("active_gate"))}
            b.edit_message_text(
                f"⏳ <b>NHẬP SỐ GIỜ CẦN MUA</b>\n\n"
                f"📦 Gói: <b>{p['name']}</b>\n"
                f"💵 Giá mỗi giờ: <b>{money(p.get('price_per_hour',0))}</b>\n\n"
                f"Nhập số giờ muốn mua, ví dụ: <code>6</code>",
                chat, mid, reply_markup=kb_back()
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
                b.reply_to(m, "❌ Cổng này không hỗ trợ MD5. Bấm /start → Dự đoán No MD5 để chạy theo phiên.")
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
            result_icon = "📈" if p["taixiu"] == "TÀI" else "📉"
            detail = " · ".join(p.get("details", []))
            trend = ("\n🧭 Xu hướng: <b>" + p.get("trend", "") + "</b>") if plan == "pro" else ""
            db["predictions"].append({"user_id": uid, "username": username, "gate": gate, "plan": plan, "md5": p["hash_short"], "result": p["taixiu"], "confidence": p["tx_conf"], "time": now_str()})
            save_db()
            b.reply_to(
                m,
                f"🔮 <b>PHÂN TÍCH MD5 TÀI/XỈU</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Phiên bản: <b>Bản Nâng Cấp New</b>\n"
                f"📝 MD5: <code>{p['hash_short']}</code>\n\n"
                f"🎲 Bộ số mô phỏng: <b>{p['dice']}</b> | Tổng: <b>{p['total']}</b>\n"
                f"{result_icon} Kết luận: <b>{p['taixiu']}</b>\n"
                f"📊 Độ tin cậy thực chiến: <b>{p['tx_conf']}%</b>\n"
                f"🎯 Tài/Xỉu %: <b>T {p.get('prob_tai','')} · X {p.get('prob_xiu','')}</b>\n"
                f"💰 Khuyến nghị: <b>{p.get('advice','THAM KHẢO')}</b> · Vốn: <b>{p.get('stake_level',0)}/2</b>\n"
                f"🔵 Chẵn/Lẻ: <b>{p['chanle']}</b>\n"
                f"🧠 Điểm hash: <b>{p['score']}/100</b>{trend}\n"
                f"📌 Phân tích: <b>{p.get('advice_reason','Đã khóa seed ổn định, cùng mã sẽ ra cùng kết quả.')}</b>\n"
                f"📚 History thật: <b>{p.get('history_len',0)}</b> phiên · Vote: <b>{p.get('vote_agree','')}</b>\n"
                f"{p['risk_emoji']} Rủi ro phiên: <b>{p['risk']}</b>\n"
                f"🧬 Lớp phân tích: <i>{detail}</i>\n"
                f"{('🎁 Free mode còn: <b>' + free_remaining_text() + '</b>\n') if free_used else ''}\n"
                f"🍀✨ Nên theo khi cầu đẹp, tín hiệu sạch và quản lý vốn hợp lý 💎🎯"
            )
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
            fb["status"] = "approved"
            fb["approved_time"] = now_str()
            save_db()
            gid = str(cfg.get("group_chat_id", "")).strip()
            if gid and bot:
                caption = f"📸 <b>FEEDBACK MỚI</b>\n👤 User: <b>{mask_user(fb.get('user_id'), fb.get('username',''))}</b>\n📝 Ghi chú: {fb.get('note','')}"
                try:
                    bot.send_photo(gid, fb["photo_id"], caption=caption, parse_mode="HTML")
                except Exception as e:
                    log(f"Lỗi gửi feedback group: {e}")
            return True, "Đã duyệt feedback."
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
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            bot_running = False
            log(f"LỖI BOT: {repr(e)}")
            time.sleep(5)

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
    # Giao diện HTML tách riêng trong templates/admin.html + static/admin.css.
    # Không cần host web ngoài; Render chạy bot và web admin ngay trong cùng source.
    return render_template("admin.html", title="KingBot Ultra Admin", cfg=cfg, page=page, content=content, msg=msg, bot_running=bot_running, session=session)

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
      <div class="card"><h2>🛒 Gói theo giờ</h2>{plans_html}</div>
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
            with open(os.path.join(ROOT, "engine_md5.py"), "r", encoding="utf-8") as f:
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

@app.route("/users", methods=["GET", "POST"])
def users():
    if not session.get("login"): return render_page("users", "")
    msg = ""
    if request.method == "POST":
        uid = request.form.get("uid","").strip()
        amount = int(request.form.get("amount",0) or 0)
        action = request.form.get("action")
        if uid in db["users"]:
            if action == "add":
                db["users"][uid]["balance"] = int(db["users"][uid].get("balance",0)) + amount
                msg = f"Đã cộng {money(amount)}"
            if action == "set":
                db["users"][uid]["balance"] = amount
                msg = f"Đã set {money(amount)}"
            if action == "delete":
                db["users"].pop(uid, None)
                msg = "Đã xóa user"
            save_db()
    rows = ""
    for u in reversed(list(db["users"].values())):
        uid = u.get("id")
        rows += f"""<tr><td><code>{uid}</code></td><td>@{u.get('username')}</td><td>{money(u.get('balance',0))}</td><td>{u.get('selected_plan') or '-'}</td><td>⭐ {remaining_time_text(u,'basic')}<br>💎 {remaining_time_text(u,'pro')}</td>
        <td><form method="post" class="row"><input type="hidden" name="uid" value="{uid}"><input style="width:130px;margin:0" type="number" name="amount" placeholder="Số tiền"><button name="action" value="add" class="btn green">Cộng</button><button name="action" value="set" class="btn yellow">Set</button><button name="action" value="delete" class="btn red" onclick="return confirm('Xóa user?')">Xóa</button></form></td></tr>"""
    return render_page("users", f"<div class='top'><div class='title'>👥 Users</div></div><div class='card'><table><tr><th>ID</th><th>User</th><th>Số dư</th><th>Gói</th><th>Hạn</th><th>Hành động</th></tr>{rows}</table></div>", msg)


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
            f"<td>{mask_user(o.get('user_id'), o.get('username',''))}</td>"
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

threading.Thread(target=bot_worker, daemon=True).start()
threading.Thread(target=backup_worker, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    log(f"Web admin chạy port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
