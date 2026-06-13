# -*- coding: utf-8 -*-
"""
KINGBOT ULTRA RENDER
Flask Web Admin + Telegram Polling Bot
Start command: python app.py
Build command: pip install -r requirements.txt
"""

import os, json, time, threading, secrets, hashlib, statistics, urllib.parse
from datetime import datetime, timedelta

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, redirect, session, render_template_string, jsonify

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(ROOT, "data"))
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
DB_FILE = os.path.join(DATA_DIR, "database.json")
LOG_FILE = os.path.join(DATA_DIR, "bot.log")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "bot_token": "8692584207:AAFlXH1Rt2z4vLWLvgQySwj33dV20LqGk3k",
    "admin_password": "admin123",
    "admin_ids": [],
    "shop_name": "KingBot Luxury",
    "accent": "#8b5cf6",
    "welcome_text": "Hệ thống phân tích MD5 Tài/Xỉu cao cấp",
    "support_url": "https://t.me/",
    "group_chat_id": "",
    "bank_bin": "970436",
    "bank_account": "1234567890",
    "bank_name": "NGUYEN VAN A",
    "payment_note_prefix": "NAP",
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
    "predictions": []
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

# Render Environment ưu tiên nếu có
for env_key, cfg_key in [
    ("BOT_TOKEN", "bot_token"),
    ("ADMIN_PASSWORD", "admin_password"),
    ("SHOP_NAME", "shop_name"),
    ("GROUP_CHAT_ID", "group_chat_id"),
]:
    if os.environ.get(env_key):
        cfg[cfg_key] = os.environ[env_key].strip()
save_json(CONFIG_FILE, cfg)

bot = None
bot_running = False
user_state = {}

def save_cfg(): save_json(CONFIG_FILE, cfg)
def save_db(): save_json(DB_FILE, db)

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

def has_active_plan(user):
    return int(user.get("plan_expire", 0) or 0) > int(time.time()) and user.get("active_plan") in cfg["plans"]

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
    bank_bin = cfg.get("bank_bin", "").strip()
    acc = cfg.get("bank_account", "").strip()
    name = cfg.get("bank_name", "").strip()
    info = urllib.parse.quote(note)
    account_name = urllib.parse.quote(name)
    return f"https://img.vietqr.io/image/{bank_bin}-{acc}-compact2.png?amount={int(amount)}&addInfo={info}&accountName={account_name}"

def notify_group(text):
    gid = str(cfg.get("group_chat_id", "")).strip()
    if not gid or not bot:
        return False
    try:
        bot.send_message(gid, text, parse_mode="HTML")
        return True
    except Exception as e:
        log(f"Không gửi được group: {e}")
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
        f"⏳ Hạn dùng: <b>{active_until_text(user)}</b>\n\n"
        "⚠️ Không có gói miễn phí. Mua gói để phân tích MD5 Tài/Xỉu."
    )

def predict_basic(md5_hex: str):
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

def predict_pro(md5_hex: str, gate_key=""):
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
                b.edit_message_text("❌ Đã hủy thanh toán gói.", chat, mid, reply_markup=kb_home())
                return

            pk = pending["plan"]
            gate = pending["gate"]
            hours = int(pending["hours"])
            total = int(pending["total"])
            if int(user.get("balance", 0)) < total:
                b.answer_callback_query(c.id, "❌ Số dư không đủ, vui lòng nạp thêm!", show_alert=True)
                return

            p = cfg["plans"][pk]
            db["users"][uid]["balance"] = int(db["users"][uid].get("balance", 0)) - total
            db["users"][uid]["active_plan"] = pk
            db["users"][uid]["active_gate"] = gate
            current_exp = int(db["users"][uid].get("plan_expire", 0) or 0)
            base_ts = max(current_exp, int(time.time()))
            db["users"][uid]["plan_expire"] = int((datetime.fromtimestamp(base_ts) + timedelta(hours=hours)).timestamp())
            db["users"][uid]["total_spent"] = int(db["users"][uid].get("total_spent", 0)) + total

            order = {"id": "BUY" + str(int(time.time())) + uid[-4:], "user_id": uid, "username": username, "gate": gate, "plan": pk, "hours": hours, "amount": total, "time": now_str()}
            db["purchases"].append(order)
            db["transactions"].append({"user_id": uid, "type": "purchase", "amount": -total, "plan": pk, "hours": hours, "time": now_str()})
            save_db()
            user_state.pop(uid, None)

            notify_group(
                f"🛒 <b>ĐƠN MUA GÓI THÀNH CÔNG</b>\n"
                f"👤 User: <b>{mask_user(uid, username)}</b>\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Gói: <b>{p['name']}</b>\n"
                f"⏳ Số giờ: <b>{hours}</b>\n"
                f"💰 Giá: <b>{money(total)}</b>"
            )
            b.edit_message_text(
                f"✅ <b>THANH TOÁN THÀNH CÔNG!</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(gate)} {gate_name(gate)}</b>\n"
                f"📦 Gói: <b>{p['name']}</b>\n"
                f"⏳ Số giờ: <b>{hours}</b>\n"
                f"💰 Đã trừ: <b>{money(total)}</b>\n"
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
            b.edit_message_text(home_text(user, username, uid), chat, mid, reply_markup=kb_home())
            return

        if data == "account":
            txt = (
                f"👤 <b>TÀI KHOẢN</b>\n\n"
                f"🆔 ID: <code>{uid}</code>\n"
                f"💰 Số dư: <b>{money(user.get('balance',0))}</b>\n"
                f"🎮 Cổng: <b>{(gate_icon(user.get('active_gate')) + ' ' + gate_name(user.get('active_gate'))) if user.get('active_gate') else 'Chưa chọn'}</b>\n"
                f"📦 Gói: <b>{cfg['plans'].get(user.get('active_plan'),{}).get('name','Chưa mua')}</b>\n"
                f"⏳ Hạn: <b>{active_until_text(user)}</b>"
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
            kb = InlineKeyboardMarkup()
            for pk, p in cfg["plans"].items():
                price = plan_price(pk)
                emoji = "💎" if pk == "pro" else ("⭐" if pk == "basic" else "🔥")
                kb.add(InlineKeyboardButton(f"{emoji} {p['name']} - {money(p.get('price_per_hour',0))}/giờ", callback_data=f"buy_{pk}"))
            kb.add(InlineKeyboardButton("🔙 Đổi cổng", callback_data="choose_gate"))
            b.edit_message_text(
                f"✅ Đã chọn cổng: <b>{gate_icon(gk)} {gate_name(gk)}</b>\n\n📦 Chọn gói muốn mua:",
                chat, mid, reply_markup=kb
            )
            return

        if data == "deposit":
            user_state[uid] = {"mode": "deposit_amount"}
            b.edit_message_text("💰 <b>NẠP TIỀN</b>\n\nNhập số tiền muốn nạp, ví dụ: <code>50000</code>", chat, mid, reply_markup=kb_back())
            return

        if data == "buy_tool":
            if not user.get("active_gate"):
                b.answer_callback_query(c.id, "Vui lòng chọn cổng game trước!", show_alert=True)
                return
            if has_active_plan(user):
                b.edit_message_text(
                    f"✅ <b>BẠN ĐÃ CÓ GÓI ĐANG HOẠT ĐỘNG</b>\n\n🎮 Cổng: <b>{gate_icon(user.get('active_gate'))} {gate_name(user.get('active_gate'))}</b>\n📦 Gói: <b>{cfg['plans'].get(user.get('active_plan'),{}).get('name','')}</b>\n⏳ Hạn: <b>{active_until_text(user)}</b>\n\nGửi mã MD5 32 ký tự vào bot để dự đoán ngay.",
                    chat, mid, reply_markup=kb_home()
                )
                return
            kb = InlineKeyboardMarkup()
            for pk, p in cfg["plans"].items():
                price = plan_price(pk)
                emoji = "💎" if pk == "pro" else ("⭐" if pk == "basic" else "🔥")
                kb.add(InlineKeyboardButton(f"{emoji} {p['name']} - {money(p.get('price_per_hour',0))}/giờ", callback_data=f"buy_{pk}"))
            kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
            b.edit_message_text(
                f"🛒 <b>MUA GÓI PHÂN TÍCH</b>\n\n🎮 Cổng: <b>{gate_icon(user.get('active_gate'))} {gate_name(user.get('active_gate'))}</b>\n💰 Số dư: <b>{money(user.get('balance',0))}</b>",
                chat, mid, reply_markup=kb
            )
            return

        if data.startswith("buy_"):
            pk = data.replace("buy_", "", 1)
            if pk not in cfg["plans"]:
                return
            if not user.get("active_gate"):
                b.answer_callback_query(c.id, "Chưa chọn cổng game!", show_alert=True)
                return
            p = cfg["plans"][pk]
            user_state[uid] = {"mode": "buy_hours", "plan": pk, "gate": user.get("active_gate")}
            b.edit_message_text(
                f"⏳ <b>NHẬP SỐ GIỜ CẦN MUA</b>\n\n"
                f"🎮 Cổng: <b>{gate_icon(user.get('active_gate'))} {gate_name(user.get('active_gate'))}</b>\n"
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
            gate = state.get("gate")
            if pk not in cfg["plans"] or gate not in cfg["gates"]:
                user_state.pop(uid, None)
                b.reply_to(m, "❌ Đơn mua lỗi, vui lòng chọn lại gói.")
                return

            p = cfg["plans"][pk]
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
            item = {"id": fb_id, "user_id": uid, "username": username, "note": state.get("note", ""), "photo_id": photo_id, "status": "pending", "time": now_str()}
            db["feedback"].append(item)
            save_db()
            user_state.pop(uid, None)
            b.reply_to(m, f"✅ Feedback đã gửi, chờ admin duyệt.\nMã: <code>{fb_id}</code>")
            return

        if len(text) == 32:
            if not has_active_plan(user):
                b.reply_to(m, "❌ Bạn chưa có gói đang hoạt động.\n\nBấm /start → 🎮 Chọn Cổng & Gói → chọn LC79/HitClub/BetVip → mua gói rồi gửi MD5 để dự đoán.")
                return
            gate = user.get("active_gate")
            plan = user.get("active_plan")
            if plan == "pro":
                p = predict_pro(text, gate)
            else:
                p = predict_basic(text)
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
                f"📦 Engine: <b>{p['engine']}</b>\n"
                f"📝 MD5: <code>{p['hash_short']}</code>\n\n"
                f"🎲 Bộ số mô phỏng: <b>{p['dice']}</b> | Tổng: <b>{p['total']}</b>\n"
                f"{result_icon} Kết luận: <b>{p['taixiu']}</b>\n"
                f"📊 Độ tin cậy: <b>{p['tx_conf']}%</b>\n"
                f"🔵 Chẵn/Lẻ: <b>{p['chanle']}</b>\n"
                f"🧠 Điểm hash: <b>{p['score']}/100</b>{trend}\n"
                f"{p['risk_emoji']} Rủi ro phiên: <b>{p['risk']}</b>\n"
                f"🧬 Lớp phân tích: <i>{detail}</i>\n\n"
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
            db["users"][uid]["balance"] = int(db["users"][uid].get("balance", 0)) + amount
            db["users"][uid]["total_deposit"] = int(db["users"][uid].get("total_deposit", 0)) + amount
            db["transactions"].append({"user_id": uid, "type": "deposit", "amount": amount, "time": now_str(), "order_id": order_id})
            save_db()
            try:
                bot.send_message(uid, f"✅ <b>NẠP TIỀN THÀNH CÔNG</b>\n\n💵 Số tiền: <b>{money(amount)}</b>\n💰 Số dư mới: <b>{money(db['users'][uid]['balance'])}</b>")
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
    return render_template_string(BASE_HTML, title="KingBot Ultra Admin", cfg=cfg, page=page, content=content, msg=msg)

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
        cfg["bank_bin"] = request.form.get("bank_bin","")
        cfg["bank_account"] = request.form.get("bank_account","")
        cfg["bank_name"] = request.form.get("bank_name","")
        cfg["payment_note_prefix"] = request.form.get("payment_note_prefix","NAP")
        for gk in cfg["gates"]:
            cfg["gates"][gk]["name"] = request.form.get(f"gate_{gk}_name", cfg["gates"][gk]["name"])
            cfg["gates"][gk]["icon"] = request.form.get(f"gate_{gk}_icon", cfg["gates"][gk].get("icon","🎮"))
            cfg["gates"][gk]["enabled"] = request.form.get(f"gate_{gk}_enabled") == "on"
        for pk in cfg["plans"]:
            cfg["plans"][pk]["name"] = request.form.get(f"plan_{pk}_name", cfg["plans"][pk]["name"])
            cfg["plans"][pk]["price_per_hour"] = int(request.form.get(f"plan_{pk}_price", cfg["plans"][pk]["price_per_hour"]) or 0)
            cfg["plans"][pk]["hours"] = int(request.form.get(f"plan_{pk}_hours", cfg["plans"][pk]["hours"]) or 1)
        save_cfg()
        msg = "Đã lưu cấu hình. Nếu đổi token ENV trên Render thì restart service."
    gates_html = ""
    for gk, gv in cfg["gates"].items():
        gates_html += f"<label>{gk.upper()} tên</label><input name='gate_{gk}_name' value='{gv.get('name','')}'><label>{gk.upper()} icon emoji</label><input name='gate_{gk}_icon' value='{gv.get('icon','🎮')}'><label><input style='width:auto' type='checkbox' name='gate_{gk}_enabled' {'checked' if gv.get('enabled') else ''}> Bật {gk.upper()}</label><br>"
    plans_html = ""
    for pk, p in cfg["plans"].items():
        plans_html += f"<h3>{pk.upper()}</h3><label>Tên gói</label><input name='plan_{pk}_name' value='{p.get('name','')}'><label>Giá mỗi giờ</label><input type='number' name='plan_{pk}_price' value='{p.get('price_per_hour',0)}'><label>Số giờ</label><input type='number' name='plan_{pk}_hours' value='{p.get('hours',1)}'>"
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
        <label>Group Chat ID nhận thông báo</label><input name="group_chat_id" value="{cfg.get('group_chat_id','')}" placeholder="-100xxxxxxxxxx">
      </div>
      <div class="card"><h2>💳 VietQR</h2>
        <label>Mã ngân hàng BIN</label><input name="bank_bin" value="{cfg.get('bank_bin','')}">
        <label>Số tài khoản</label><input name="bank_account" value="{cfg.get('bank_account','')}">
        <label>Tên chủ tài khoản</label><input name="bank_name" value="{cfg.get('bank_name','')}">
        <label>Tiền tố nội dung</label><input name="payment_note_prefix" value="{cfg.get('payment_note_prefix','NAP')}">
      </div>
    </div><br>
    <div class="grid2">
      <div class="card"><h2>🎮 Cổng Game</h2>{gates_html}</div>
      <div class="card"><h2>🛒 Gói theo giờ</h2>{plans_html}</div>
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    log(f"Web admin chạy port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
