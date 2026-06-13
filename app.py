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
from flask import Flask, request, redirect, session, render_template_string, render_template, jsonify, Response
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
FALLBACK_ALGO_FILE = os.path.join(ROOT, "algorithm_fallback_md5_400kb.txt")
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
        "lc79": {"name": "LC79", "icon": "🎲", "enabled": True},
        "hitclub": {"name": "HitClub", "icon": "♠️", "enabled": True},
        "betvip": {"name": "BetVip", "icon": "💎", "enabled": True}
    },
    "plans": {
        "basic": {"name": "Gói Thường", "price_per_hour": 5000, "hours": 1, "level": "basic"},
        "pro": {"name": "Gói Pro", "price_per_hour": 12000, "hours": 1, "level": "pro"}
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

# Không ép token/config từ Render ENV.
# Token bot, backup URL/secret và thông số khác được lưu/chỉnh trong Web Admin.
# ENV chỉ còn dùng cho PORT/DATA_DIR/SECRET_KEY hệ thống.
save_json(CONFIG_FILE, cfg)

bot = None
bot_running = False
user_state = {}
algo_cache = {"hash": None, "ns": {}, "error": ""}
fallback_algo_cache = {"hash": None, "ns": {}, "error": ""}

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
            "active_gate": None,
            "plan_expire": 0,
            "joined": now_str(),
            "total_deposit": 0,
            "total_spent": 0
        }
    else:
        db["users"][uid]["username"] = username
    save_db()
    return uid, db["users"][uid], username

def active_until_text(user):
    exp = int(user.get("plan_expire", 0) or 0)
    if exp <= int(time.time()):
        return "Chưa có gói"
    return datetime.fromtimestamp(exp).strftime("%d/%m/%Y %H:%M")

def remaining_time_text(user):
    exp = int(user.get("plan_expire", 0) or 0)
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

def has_active_plan(user):
    return int(user.get("plan_expire", 0) or 0) > int(time.time()) and user.get("active_plan") in cfg["plans"]

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
        InlineKeyboardButton("🎮 Chọn Cổng & Gói", callback_data="choose_gate"),
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
    if len(s) != 32:
        return None
    try:
        b = [int(s[i:i+2], 16) for i in range(0, 32, 2)]
        n = [int(c, 16) for c in s]
    except Exception:
        return None

    xor_all = 0
    for x in b:
        xor_all ^= x

    wave = sum((i + 1) * b[i] for i in range(16)) % 1000
    nib = sum((i + 3) * n[i] for i in range(32)) % 1000
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
    if len(s) != 32:
        return None
    try:
        b = [int(s[i:i+2], 16) for i in range(0, 32, 2)]
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
    nibble = sum((i + 7) * (n[i] + (sha_b[i % 32] % 16)) for i in range(32)) % 4096
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
        "details": r.get("details") if isinstance(r.get("details"), list) else ["Admin algorithm", "Dynamic code", "HTML config"]
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
    safe_builtins = {
        "abs": abs, "min": min, "max": max, "sum": sum, "len": len, "range": range,
        "int": int, "float": float, "str": str, "round": round, "enumerate": enumerate,
        "list": list, "dict": dict, "set": set, "tuple": tuple, "sorted": sorted, "zip": zip,
        "bool": bool, "pow": pow
    }
    g = {"__builtins__": safe_builtins, "hashlib": hashlib, "statistics": statistics, "random": random, "math": __import__("math")}
    try:
        exec(code, g, g)
        ns = g
        algo_cache.update({"hash": h, "ns": ns, "error": ""})
        return ns
    except Exception:
        err = traceback.format_exc(limit=3)
        algo_cache.update({"hash": h, "ns": {}, "error": err})
        log("Lỗi thuật toán admin: " + err.replace("\n", " | ")[:500])
        return None

def predict_admin(md5_hex: str, gate_key="", level="basic"):
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
                try:
                    r = fn(md5_hex, gate_key, level)
                except TypeError:
                    try: r = fn(md5_hex, gate_key)
                    except TypeError: r = fn(md5_hex)
                nr = normalize_prediction_result(r)
                if nr:
                    if not nr.get("hash_short"):
                        nr["hash_short"] = md5_hex[:8].upper() + "..." + md5_hex[-6:].upper()
                    return nr
            except Exception:
                err = traceback.format_exc(limit=3)
                algo_cache["error"] = err
                log("Lỗi chạy thuật toán admin: " + err.replace("\n", " | ")[:500])
                return None
    return None

def load_fallback_algorithm():
    try:
        with open(FALLBACK_ALGO_FILE, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        fallback_algo_cache.update({"hash": None, "ns": {}, "error": str(e)})
        return None
    if not code.strip():
        fallback_algo_cache.update({"hash": None, "ns": {}, "error": "File TXT rỗng"})
        return None
    h = hashlib.sha256(code.encode("utf-8", "ignore")).hexdigest()
    if fallback_algo_cache.get("hash") == h:
        return fallback_algo_cache.get("ns")
    safe_builtins = {"abs": abs, "min": min, "max": max, "sum": sum, "len": len, "range": range, "int": int, "float": float, "str": str, "round": round, "enumerate": enumerate, "list": list, "dict": dict, "set": set, "tuple": tuple, "sorted": sorted, "zip": zip, "bool": bool, "pow": pow, "isinstance": isinstance}
    g = {"__builtins__": safe_builtins, "hashlib": hashlib, "statistics": statistics, "random": random, "math": __import__("math")}
    ns = {}
    try:
        exec(code, g, g)
        ns = g
        fallback_algo_cache.update({"hash": h, "ns": ns, "error": ""})
        return ns
    except Exception:
        err = traceback.format_exc(limit=3)
        fallback_algo_cache.update({"hash": h, "ns": {}, "error": err})
        log("Lỗi thuật toán TXT dự phòng: " + err.replace("\n", " | ")[:500])
        return None

def predict_from_namespace(ns, md5_hex: str, gate_key="", level="basic", engine_label="TXT-FALLBACK"):
    if not ns:
        return None
    funcs = ["predict_free", "predict"] if level == "free" else (["predict_pro", "predict"] if level == "pro" else ["predict_basic", "predict"])
    for name in funcs:
        fn = ns.get(name)
        if callable(fn):
            try:
                try:
                    r = fn(md5_hex, gate_key, level)
                except TypeError:
                    try: r = fn(md5_hex, gate_key)
                    except TypeError: r = fn(md5_hex)
                nr = normalize_prediction_result(r, engine_label)
                if nr:
                    if not nr.get("hash_short"):
                        nr["hash_short"] = md5_hex[:8].upper() + "..." + md5_hex[-6:].upper()
                    return nr
            except Exception:
                log(f"Lỗi chạy {engine_label}: " + traceback.format_exc(limit=3).replace("\n", " | ")[:500])
                return None
    return None

def no_algorithm_result(md5_hex: str):
    return {"engine": "NO-ALGORITHM", "taixiu": "XỈU", "tx_conf": 1, "chanle": "-", "dice": "0-0-0", "total": 0, "risk": "CHƯA CẤU HÌNH", "risk_emoji": "⚠️", "score": 0, "hash_short": md5_hex[:8].upper() + "..." + md5_hex[-6:].upper(), "trend": "Chưa có thuật toán admin/TXT", "details": ["Chưa cấu hình thuật toán"]}

def predict_free(md5_hex: str, gate_key=""):
    ar = predict_admin(md5_hex, gate_key, "free")
    if ar: return ar
    tr = predict_from_namespace(load_fallback_algorithm(), md5_hex, gate_key, "free", "TXT-DỰ-PHÒNG-MD5-400KB")
    if tr: return tr
    return no_algorithm_result(md5_hex)

def predict_basic(md5_hex: str):
    ar = predict_admin(md5_hex, "", "basic")
    if ar: return ar
    tr = predict_from_namespace(load_fallback_algorithm(), md5_hex, "", "basic", "TXT-DỰ-PHÒNG-MD5-400KB")
    if tr: return tr
    return no_algorithm_result(md5_hex)

def predict_pro(md5_hex: str, gate_key=""):
    ar = predict_admin(md5_hex, gate_key, "pro")
    if ar: return ar
    tr = predict_from_namespace(load_fallback_algorithm(), md5_hex, gate_key, "pro", "TXT-DỰ-PHÒNG-MD5-400KB")
    if tr: return tr
    return no_algorithm_result(md5_hex)

def build_bot():
    global bot
    token = cfg.get("bot_token", "").strip()
    if not token:
        log("Chưa có BOT_TOKEN.")
        return None

    b = telebot.TeleBot(token, parse_mode="HTML")

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
            db["users"][uid]["active_plan"] = pk
            db["users"][uid]["active_gate"] = gate
            current_exp = int(db["users"][uid].get("plan_expire", 0) or 0)
            base_ts = max(current_exp, int(time.time()))
            db["users"][uid]["plan_expire"] = int((datetime.fromtimestamp(base_ts) + timedelta(hours=hours)).timestamp())
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
                f"📅 Hạn dùng: <b>{active_until_text(db['users'][uid])}</b>\n\n"
                f"Gửi MD5 32 ký tự để dự đoán ngay.",
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
                f"📦 Gói: <b>{cfg['plans'].get(user.get('active_plan'),{}).get('name','Chưa mua')}</b>\n"
                f"⏳ Hạn: <b>{active_until_text(user)}</b>\n⌛ Còn lại: <b>{remaining_time_text(user)}</b>"
            )
            b.edit_message_text(txt, chat, mid, reply_markup=kb_back())
            return

        if data == "choose_gate":
            kb = InlineKeyboardMarkup()
            for gk, gv in enabled_gates().items():
                kb.add(InlineKeyboardButton(f"{gv.get('icon', '🎮')} {gv.get('name', gk.upper())}", callback_data=f"gate_{gk}"))
            kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
            b.edit_message_text("🎮 <b>CHỌN CỔNG GAME</b>\n\nChọn cổng bạn muốn phân tích:", chat, mid, reply_markup=kb)
            return

        if data.startswith("gate_"):
            gk = data.replace("gate_", "", 1)
            if gk not in enabled_gates():
                b.answer_callback_query(c.id, "Cổng này đang tắt!", show_alert=True)
                return
            db["users"][uid]["active_gate"] = gk
            save_db()

            if has_active_plan(db["users"][uid]):
                b.edit_message_text(
                    f"✅ Đã chọn cổng: <b>{gate_icon(gk)} {gate_name(gk)}</b>\n\n"
                    f"📦 Gói đang dùng: <b>{cfg['plans'].get(db['users'][uid].get('active_plan'),{}).get('name','')}</b>\n"
                    f"⌛ Còn lại: <b>{remaining_time_text(db['users'][uid])}</b>\n\n"
                    f"Gửi MD5 32 ký tự để dự đoán ngay.",
                    chat, mid, reply_markup=kb_home()
                )
                return

            kb = InlineKeyboardMarkup()
            for pk, p in cfg["plans"].items():
                emoji = "💎" if pk == "pro" else ("⭐" if pk == "basic" else "🔥")
                kb.add(InlineKeyboardButton(f"{emoji} {p['name']} - {money(p.get('price_per_hour',0))}/giờ", callback_data=f"buy_{pk}"))
            kb.add(InlineKeyboardButton("🎁 Free dự đoán", callback_data="free_predict"))
            kb.add(InlineKeyboardButton("🔙 Đổi cổng", callback_data="choose_gate"))
            b.edit_message_text(
                f"✅ Đã chọn cổng: <b>{gate_icon(gk)} {gate_name(gk)}</b>\n\n📦 Bạn chưa có gói/hết hạn, chọn gói muốn mua:",
                chat, mid, reply_markup=kb
            )
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
            b.edit_message_text(
                f"🎁 <b>FREE DỰ ĐOÁN ĐÃ SẴN SÀNG</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"⌛ Free còn: <b>{free_remaining_text()}</b>\n\n"
                f"Gửi MD5 32 ký tự để bot dự đoán miễn phí.",
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
                f"⏳ Hạn hiện tại: <b>{active_until_text(user)}</b>\n"
                f"⌛ Còn lại: <b>{remaining_time_text(user)}</b>\n"
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

        if len(text) == 32:
            gate = user.get("active_gate")
            plan = user.get("active_plan")
            free_used = False
            if not has_active_plan(user):
                if not free_is_active():
                    b.reply_to(m, "❌ Bạn chưa có gói đang hoạt động.\n\nBấm /start → 🛒 Mua Gói rồi chọn cổng để dự đoán.")
                    return
                if not user_joined_free_channel(uid):
                    b.reply_to(m, join_channel_message())
                    return
                free_used = True
                plan = "free"
                p = predict_free(text, gate or "")
            elif plan == "pro":
                p = predict_pro(text, gate)
            else:
                p = predict_basic(text)
            if not p:
                b.reply_to(m, "❌ MD5 không hợp lệ.")
                return
            result_icon = "📈" if p["taixiu"] == "TÀI" else "📉"
            detail = " · ".join(p.get("details", []))
            trend = ("\n🧭 Bắt cầu/Xu hướng: <b>" + p.get("trend", "") + "</b>") if p.get("trend") else ""
            db["predictions"].append({"user_id": uid, "username": username, "gate": gate, "plan": plan, "md5": p["hash_short"], "result": p["taixiu"], "confidence": p["tx_conf"], "time": now_str()})
            save_db()
            b.reply_to(
                m,
                f"🔮 <b>PHÂN TÍCH MD5 TÀI/XỈU</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Engine: <b>{p['engine']}</b>\n"
                f"📝 MD5: <code>{p['hash_short']}</code>\n\n"
                f"🎲 Bộ số mô phỏng: <b>{p['dice']}</b> | Tổng: <b>{p['total']}</b>\n"
                f"{result_icon} Kết luận: <b>{p['taixiu']}</b>\n"
                f"📊 Độ tin cậy: <b>{p['tx_conf']}%</b>\n"
                f"🔵 Chẵn/Lẻ: <b>{p['chanle']}</b>\n"
                f"🧠 Điểm hash: <b>{p['score']}/100</b>{trend}\n"
                f"{p['risk_emoji']} Rủi ro phiên: <b>{p['risk']}</b>\n"
                f"🧬 Lớp phân tích: <i>{detail}</i>\n"
                f"{('🎁 Free mode còn: <b>' + free_remaining_text() + '</b>\n') if free_used else ''}\n"
                f"⚠️ Kết quả chỉ mang tính tham khảo từ phân tích hash."
            )
            return

        b.reply_to(m, "💡 Nhấn /start để mở menu hoặc gửi MD5 32 ký tự.")

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
<a class="{{'on' if page=='backupjs' else ''}}" href="/backup-js">🧩 Backup JS</a>
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
    rows = "".join([f"<tr><td><code>{u.get('id')}</code></td><td>@{u.get('username')}</td><td>{money(u.get('balance',0))}</td><td>{u.get('active_plan') or '-'}</td><td>{active_until_text(u)}</td></tr>" for u in recent])
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
      <div class="card"><h2>🧠 Engine</h2><p class="mut">Basic Matrix + Pro SHA512 Chaos</p></div>
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
        rows += f"""<tr><td><code>{uid}</code></td><td>@{u.get('username')}</td><td>{money(u.get('balance',0))}</td><td>{u.get('active_plan') or '-'}</td><td>{active_until_text(u)}</td>
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
    content = f"""
    <div class='top'><div class='title'>☁️ Backup Infinity PHP</div></div>
    <div class='grid2'>
      <div class='card'>
        <h2>Trạng thái</h2>
        <p>URL: <code>{cfg.get('backup_url','')}</code></p>
        <p>Chu kỳ: <b>{cfg.get('backup_interval_seconds',120)}s</b></p>
        <form method='post' class='row'>
          <button class='btn green' name='action' value='push'>Đẩy backup ngay</button>
          <button class='btn yellow' name='action' value='pull'>Kéo backup mới nhất</button>
        </form>
      </div>
      <div class='card'>
        <h2>Hướng dẫn</h2>
        <p class='mut'>Up file backup.php lên Infinity. Điền URL + secret ở Cài đặt. Bot sẽ tự kéo backup lúc start và tự đẩy backup theo chu kỳ.</p>
      </div>
    </div>
    """
    return render_page("backup", content, msg)

@app.route("/backup-js", methods=["GET", "POST"])
def backup_js_page():
    if not session.get("login"): return render_page("backupjs", "")
    msg = ""
    if request.method == "POST":
        raw = ""
        f = request.files.get("js_file")
        if f:
            raw = f.read().decode("utf-8", "ignore")
        else:
            raw = request.form.get("js_text", "")
        try:
            if "window.KINGBOT_BACKUP" in raw:
                raw = raw.split("=", 1)[1].strip()
                if raw.endswith(";"): raw = raw[:-1]
            data = json.loads(raw)
            payload = data.get("payload", data)
            new_cfg = payload.get("config")
            new_db = payload.get("database")
            if not isinstance(new_cfg, dict) or not isinstance(new_db, dict):
                raise ValueError("File JS không có payload.config/database")
            cfg.clear(); cfg.update(new_cfg)
            db.clear(); db.update(new_db)
            save_cfg(); save_db()
            msg = "✅ Đã khôi phục dữ liệu từ Backup JS."
        except Exception as e:
            msg = "❌ Lỗi restore JS: " + html.escape(repr(e))
    content = """
    <div class="top"><div class="title">🧩 Backup JS</div></div>
    <div class="grid2">
      <div class="card"><h2>📥 Tải backup dạng JS</h2><p class="mut">File JS chứa config + database hiện tại. Sập host thì upload lại file JS là khôi phục.</p><a class="btn pri" href="/backup-js/download">⬇️ Tải backup_data.js</a></div>
      <div class="card"><h2>📤 Khôi phục từ JS</h2><form method="post" enctype="multipart/form-data"><label>Chọn file backup_data.js</label><input type="file" name="js_file" accept=".js,.json,.txt"><label>Hoặc dán nội dung JS/JSON</label><textarea name="js_text" placeholder="window.KINGBOT_BACKUP = ..."></textarea><button class="btn green">♻️ Restore dữ liệu</button></form></div>
    </div><div class="card"><h2>✅ Ghi chú</h2><p class="mut">Backup JS là bản cứu hộ thủ công, không phụ thuộc PHP backup.</p></div>
    """
    return render_page("backupjs", content, msg)

@app.route("/backup-js/download")
def backup_js_download():
    if not session.get("login"): return redirect("/login")
    payload = {"version":"kingbot-js-backup-v1", "created_at": now_str(), "payload": backup_payload()}
    js = "window.KINGBOT_BACKUP = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    return Response(js, mimetype="application/javascript; charset=utf-8", headers={"Content-Disposition":"attachment; filename=backup_data.js"})

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
