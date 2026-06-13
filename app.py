# -*- coding: utf-8 -*-
"""
KingBot Render Ready
- Flask web admin + Telegram bot polling trong 1 Web Service Render.
- KHÔNG dùng webhook.
- Start command: python app.py
"""

import os, json, time, threading, secrets, hashlib, math, statistics
from datetime import datetime, timedelta

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, redirect, session, render_template_string

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
    "payment_info": "Ngân hàng: VCB\nSTK: 1234567890\nTên: NGUYEN VAN A",
    "welcome_text": "Hệ thống dự đoán MD5 chuyên nghiệp",
    "plans": {
        "basic": {"name": "Gói Thường", "price": 50000, "days": 30, "predictions": 100},
        "pro": {"name": "Gói Pro", "price": 150000, "days": 30, "predictions": -1}
    }
}
DEFAULT_DB = {"users": {}, "transactions": [], "announcements": []}

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
        return json.loads(json.dumps(default, ensure_ascii=False))
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return json.loads(json.dumps(default, ensure_ascii=False))
        merged = json.loads(json.dumps(default, ensure_ascii=False))
        def deep(a, b):
            for k, v in b.items():
                if isinstance(v, dict) and isinstance(a.get(k), dict):
                    deep(a[k], v)
                else:
                    a[k] = v
        deep(merged, d)
        return merged
    except Exception as e:
        log(f"Lỗi đọc JSON {path}: {e}")
        return json.loads(json.dumps(default, ensure_ascii=False))

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

cfg = load_json(CONFIG_FILE, DEFAULT_CONFIG)
db = load_json(DB_FILE, DEFAULT_DB)

# ENV trên Render ưu tiên hơn file config
if os.environ.get("BOT_TOKEN"):
    cfg["bot_token"] = os.environ["BOT_TOKEN"].strip()
if os.environ.get("ADMIN_PASSWORD"):
    cfg["admin_password"] = os.environ["ADMIN_PASSWORD"]
if os.environ.get("SHOP_NAME"):
    cfg["shop_name"] = os.environ["SHOP_NAME"]
save_json(CONFIG_FILE, cfg)

bot = None
bot_running = False

def save_cfg(): save_json(CONFIG_FILE, cfg)
def save_db(): save_json(DB_FILE, db)

def money(n):
    try: n = int(n)
    except Exception: n = 0
    return f"{n:,}".replace(",", ".") + "đ"

def is_admin(uid):
    return str(uid) in [str(x) for x in cfg.get("admin_ids", [])]

def get_user(obj):
    u = obj.from_user
    uid = str(u.id)
    username = u.username or u.first_name or "user"
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": uid, "username": username, "balance": 0, "plan": "free",
            "plan_expire": 0, "predictions_left": 5,
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        db["users"][uid]["username"] = username
    save_db()
    return uid, db["users"][uid], username

def kb_home():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Nạp Tiền", callback_data="deposit"),
        InlineKeyboardButton("👤 Tài Khoản", callback_data="account"),
        InlineKeyboardButton("🛒 Mua Gói", callback_data="buy_tool"),
        InlineKeyboardButton("📊 Dự Đoán MD5", callback_data="how_predict"),
        InlineKeyboardButton("📣 Thông Báo", callback_data="announcements"),
        InlineKeyboardButton("❓ Hướng Dẫn", callback_data="help"),
    )
    return kb

def kb_back():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
    return kb

def home_text(user, username, uid):
    plan = user.get("plan", "free")
    plan_label = "🆓 Miễn phí" if plan == "free" else ("💎 Pro" if plan == "pro" else "⭐ Thường")
    left = "∞" if user.get("predictions_left") == -1 else user.get("predictions_left", 0)
    return (
        f"👑 <b>{cfg.get('shop_name','KingBot')}</b>\n"
        f"✨ {cfg.get('welcome_text','')}\n\n"
        f"👋 Xin chào, <b>{username}</b>\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"💰 Số dư: <b>{money(user.get('balance',0))}</b>\n"
        f"📦 Gói: {plan_label}\n"
        f"🔮 Lượt còn: <b>{left}</b>\n\n"
        "Gửi mã <b>MD5 32 ký tự</b> để dự đoán Tài/Xỉu."
    )

def predict_md5_super(md5_hex: str):
    """
    Thuật toán deterministic từ MD5 hex.
    Không thể đảm bảo thắng game may rủi; chỉ là mô hình phân tích hash.
    """
    s = md5_hex.lower().strip()
    if len(s) != 32:
        return None
    try:
        nums = [int(s[i:i+2], 16) for i in range(0, 32, 2)]
    except ValueError:
        return None

    # Trộn nhiều lớp entropy từ byte, nibble, vị trí chẵn/lẻ, rotate, sha phụ
    nibbles = [int(c, 16) for c in s]
    even_sum = sum(nums[0::2])
    odd_sum = sum(nums[1::2])
    xor_all = 0
    for x in nums:
        xor_all ^= x

    sha = hashlib.sha256(("KINGBOT|" + s + "|TAIXIU").encode()).digest()
    sha_nums = list(sha[:16])

    wave = sum((i + 1) * nums[i] for i in range(16)) % 997
    mirror = sum((16 - i) * (nums[i] ^ nums[15 - i]) for i in range(16)) % 997
    nibble_pressure = sum((i + 3) * nibbles[i] for i in range(32)) % 997
    sha_mix = sum((i + 5) * sha_nums[i] for i in range(16)) % 997

    # Dice pseudo-score 3 xúc xắc 1..6
    d1 = ((nums[0] + nums[5] + sha_nums[2] + wave) % 6) + 1
    d2 = ((nums[7] ^ nums[11] ^ sha_nums[6] ^ mirror) % 6) + 1
    d3 = ((nums[14] + xor_all + sha_nums[10] + nibble_pressure) % 6) + 1
    total = d1 + d2 + d3

    # Score Tài/Xỉu đa nguồn, không chỉ dựa vào total
    raw = (
        wave * 31 +
        mirror * 17 +
        nibble_pressure * 13 +
        sha_mix * 19 +
        even_sum * 7 -
        odd_sum * 5 +
        xor_all * 23 +
        total * 29
    ) % 10000

    tai_score = raw / 100.0
    result = "TÀI" if tai_score >= 50 else "XỈU"

    # Chẵn/lẻ
    parity_score = (raw + total * 37 + xor_all * 11 + sha_nums[0]) % 100
    chanle = "CHẴN" if parity_score >= 50 else "LẺ"

    # Confidence không phóng đại quá 99
    distance = abs(tai_score - 50)
    confidence = min(96, 58 + int(distance * 0.72) + (abs(even_sum - odd_sum) % 9))
    cl_conf = min(95, 57 + abs(parity_score - 50) // 2)

    volatility = statistics.pstdev(nums)
    risk_point = int((volatility + abs(even_sum - odd_sum) / 18 + abs(raw - 5000) / 130) % 100)
    if risk_point < 34:
        risk, risk_emoji = "THẤP", "🟢"
    elif risk_point < 68:
        risk, risk_emoji = "TRUNG BÌNH", "🟡"
    else:
        risk, risk_emoji = "CAO", "🔴"

    return {
        "taixiu": result,
        "tx_conf": confidence,
        "chanle": chanle,
        "cl_conf": cl_conf,
        "dice": f"{d1}-{d2}-{d3}",
        "total": total,
        "risk": risk,
        "risk_emoji": risk_emoji,
        "score": round(tai_score, 2),
        "hash_short": s[:8].upper() + "..." + s[-6:].upper(),
    }

def build_bot():
    global bot
    token = cfg.get("bot_token", "").strip()
    if not token:
        log("Chưa có BOT_TOKEN. Vào Render Environment thêm BOT_TOKEN hoặc vào web admin cài token.")
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
        b.reply_to(m, "👑 <b>Lệnh admin</b>\n/setadmin USER_ID\n/addbalance USER_ID SOTIEN\n/broadcast nội dung\n/stats")

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
        pro = sum(1 for u in db["users"].values() if u.get("plan") == "pro")
        b.reply_to(m, f"📊 Users: {total}\n💎 Pro: {pro}\n💰 Tổng số dư: {money(bal)}")

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
        db["transactions"].append({"user_id": target, "type": "admin_add", "amount": amt, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        save_db()
        b.reply_to(m, f"✅ Đã cộng {money(amt)} cho <code>{target}</code>")
        try:
            b.send_message(target, f"💰 Bạn vừa được cộng <b>{money(amt)}</b>")
        except Exception:
            pass

    @b.message_handler(commands=["broadcast"])
    def broadcast(m):
        uid, user, username = get_user(m)
        if not is_admin(uid):
            return
        content = m.text.replace("/broadcast", "", 1).strip()
        if not content:
            b.reply_to(m, "Nhập: <code>/broadcast nội dung</code>")
            return
        db["announcements"].append({"message": content, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
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

        if data == "back_home":
            b.edit_message_text(home_text(user, username, uid), chat, mid, reply_markup=kb_home())
            return

        if data == "account":
            left = "∞" if user.get("predictions_left") == -1 else user.get("predictions_left", 0)
            b.edit_message_text(
                f"👤 <b>TÀI KHOẢN</b>\n\n🆔 ID: <code>{uid}</code>\n💰 Số dư: <b>{money(user.get('balance',0))}</b>\n📦 Gói: <b>{user.get('plan','free').upper()}</b>\n🔮 Lượt còn: <b>{left}</b>",
                chat, mid, reply_markup=kb_back()
            )
            return

        if data == "deposit":
            b.edit_message_text(
                f"💰 <b>NẠP TIỀN</b>\n\n<pre>{cfg.get('payment_info','')}</pre>\nNội dung CK: <code>NAP {uid}</code>",
                chat, mid, reply_markup=kb_back()
            )
            return

        if data == "buy_tool":
            plans = cfg["plans"]
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton(f"⭐ Gói Thường - {money(plans['basic']['price'])}", callback_data="buy_basic"))
            kb.add(InlineKeyboardButton(f"💎 Gói Pro - {money(plans['pro']['price'])}", callback_data="buy_pro"))
            kb.add(InlineKeyboardButton("🔙 Quay Lại", callback_data="back_home"))
            b.edit_message_text(
                f"🛒 <b>MUA GÓI</b>\n\n⭐ Thường: <b>{money(plans['basic']['price'])}</b>\n💎 Pro: <b>{money(plans['pro']['price'])}</b>\n\n💰 Số dư: <b>{money(user.get('balance',0))}</b>",
                chat, mid, reply_markup=kb
            )
            return

        if data in ("buy_basic", "buy_pro"):
            key = "basic" if data == "buy_basic" else "pro"
            plan = cfg["plans"][key]
            if int(user.get("balance", 0)) < int(plan["price"]):
                b.answer_callback_query(c.id, "❌ Số dư không đủ!", show_alert=True)
                return
            db["users"][uid]["balance"] -= int(plan["price"])
            db["users"][uid]["plan"] = key
            db["users"][uid]["plan_expire"] = int((datetime.now() + timedelta(days=int(plan["days"]))).timestamp())
            db["users"][uid]["predictions_left"] = int(plan["predictions"])
            db["transactions"].append({"user_id": uid, "type": "purchase", "amount": -int(plan["price"]), "plan": key, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            save_db()
            b.edit_message_text(f"✅ <b>MUA THÀNH CÔNG!</b>\n📦 Gói: <b>{plan['name']}</b>", chat, mid, reply_markup=kb_back())
            return

        if data == "how_predict":
            b.edit_message_text(
                "🔮 <b>HƯỚNG DẪN</b>\n\nGửi mã MD5 32 ký tự.\nVí dụ:\n<code>f435a026b649fd115a4f8316bef17bc8</code>",
                chat, mid, reply_markup=kb_back()
            )
            return

        if data == "announcements":
            arr = list(reversed(db.get("announcements", [])))[:5]
            txt = "📣 <b>THÔNG BÁO</b>\n\n" + ("\n\n".join([f"🕒 {a.get('time')}\n{a.get('message')}" for a in arr]) if arr else "Chưa có thông báo.")
            b.edit_message_text(txt, chat, mid, reply_markup=kb_back())
            return

        if data == "help":
            b.edit_message_text("❓ <b>HƯỚNG DẪN</b>\n/start mở menu\n/admin xem lệnh admin\nGửi MD5 để dự đoán.", chat, mid, reply_markup=kb_back())
            return

    @b.message_handler(func=lambda m: True)
    def allmsg(m):
        uid, user, username = get_user(m)
        text = (m.text or "").strip().lower()
        if len(text) == 32:
            p = predict_md5_super(text)
            if not p:
                b.reply_to(m, "❌ MD5 không hợp lệ.")
                return
            if user.get("plan") == "free" and int(user.get("predictions_left", 0)) <= 0:
                b.reply_to(m, "❌ Hết lượt miễn phí, vui lòng mua gói.")
                return
            if int(user.get("predictions_left", 0)) > 0:
                db["users"][uid]["predictions_left"] -= 1
                save_db()
            left = "∞" if db["users"][uid].get("predictions_left") == -1 else db["users"][uid].get("predictions_left", 0)
            result_icon = "📈" if p["taixiu"] == "TÀI" else "📉"
            b.reply_to(
                m,
                f"🔮 <b>KẾT QUẢ DỰ ĐOÁN TÀI XỈU</b>\n\n"
                f"📝 MD5: <code>{p['hash_short']}</code>\n"
                f"🎲 Bộ số mô phỏng: <b>{p['dice']}</b> | Tổng: <b>{p['total']}</b>\n\n"
                f"{result_icon} Tài/Xỉu: <b>{p['taixiu']}</b>\n"
                f"📊 Độ tin cậy: <b>{p['tx_conf']}%</b>\n"
                f"🔵 Chẵn/Lẻ: <b>{p['chanle']}</b> ({p['cl_conf']}%)\n"
                f"🧠 Điểm hash: <b>{p['score']}/100</b>\n"
                f"{p['risk_emoji']} Rủi ro phiên: <b>{p['risk']}</b>\n"
                f"🔮 Lượt còn: <b>{left}</b>\n\n"
                f"⚠️ Kết quả chỉ mang tính tham khảo từ phân tích hash."
            )
        else:
            b.reply_to(m, "💡 Nhấn /start hoặc gửi MD5 32 ký tự.")

    return b

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
:root{--a:{{cfg.get('accent','#8b5cf6')}};--bg:#070b16;--card:#111827;--card2:#1b2440;--bd:#23355e;--tx:#eaf1ff;--mut:#91a4c9;--g:#1dd68b;--r:#ff4d67;--y:#ffb020;--c:#00d4ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#162042,transparent 35%),linear-gradient(180deg,#070b16,#0b1020);color:var(--tx);font-family:Segoe UI,Arial,sans-serif}.wrap{display:flex;min-height:100vh}.side{width:250px;background:rgba(14,22,39,.96);border-right:1px solid var(--bd);display:flex;flex-direction:column}.brand{padding:28px 22px;border-bottom:1px solid var(--bd)}.brand h2{margin:0;font-size:22px}.brand p{margin:7px 0 0;color:var(--mut);font-size:13px}.nav{padding:14px}.nav a{display:block;color:#c9d7f5;text-decoration:none;padding:13px 15px;border-radius:12px;margin-bottom:7px}.nav a:hover,.nav a.on{background:linear-gradient(135deg,rgba(139,92,246,.25),rgba(0,212,255,.12));color:white}.main{flex:1;padding:30px}.top{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:22px}.title{font-size:30px;font-weight:900}.pill{padding:10px 14px;border-radius:99px;background:rgba(29,214,139,.12);border:1px solid rgba(29,214,139,.35);color:#55ffaa}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{background:rgba(17,24,39,.94);border:1px solid var(--bd);border-radius:18px;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.22)}.stat b{display:block;font-size:29px;margin-top:10px}.mut{color:var(--mut)}input,textarea{width:100%;background:var(--card2);border:1px solid var(--bd);border-radius:12px;color:var(--tx);padding:12px 14px;margin:7px 0 15px}textarea{min-height:110px}.btn{border:0;border-radius:12px;padding:12px 16px;font-weight:800;text-decoration:none;display:inline-block;cursor:pointer}.pri{background:linear-gradient(135deg,var(--a),#9b5cff);color:white}.green{background:var(--g);color:#021}.red{background:var(--r);color:white}.yellow{background:var(--y);color:#211}.cyan{background:var(--c);color:#012}table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid var(--bd);text-align:left}th{color:var(--mut)}code{color:var(--c)}.alert{padding:13px 16px;border-radius:13px;margin-bottom:16px;background:#063925;border:1px solid #176b4a;color:#55ffaa}.login{min-height:100vh;display:grid;place-items:center}.login .card{width:390px}.row{display:flex;gap:10px;flex-wrap:wrap}pre{white-space:pre-wrap;font-family:Consolas,monospace;color:#cfe3ff}.footer{margin-top:auto;padding:18px 22px;color:var(--mut);font-size:12px}@media(max-width:900px){.side{display:none}.main{padding:16px}.grid,.grid2{grid-template-columns:1fr}.top{display:block}}
</style></head><body>
{% if not session.get('login') %}
<div class="login"><div class="card"><h1>👑 KingBot Admin</h1>{% if msg %}<div class="alert">{{msg}}</div>{% endif %}<form method="post" action="/login"><input type="password" name="password" placeholder="Mật khẩu admin"><button class="btn pri" style="width:100%">Đăng nhập</button></form><p class="mut">Mật khẩu lấy từ ADMIN_PASSWORD trên Render, mặc định admin123</p></div></div>
{% else %}
<div class="wrap"><aside class="side"><div class="brand"><h2>👑 {{cfg.get('shop_name')}}</h2><p>Render Web Admin</p></div><nav class="nav">
<a class="{{'on' if page=='dashboard' else ''}}" href="/">📊 Dashboard</a>
<a class="{{'on' if page=='settings' else ''}}" href="/settings">⚙️ Cài đặt</a>
<a class="{{'on' if page=='users' else ''}}" href="/users">👥 Users</a>
<a class="{{'on' if page=='broadcast' else ''}}" href="/broadcast">📣 Thông báo</a>
<a class="{{'on' if page=='logs' else ''}}" href="/logs">🧾 Logs</a>
<a href="/logout">🚪 Đăng xuất</a>
</nav><div class="footer">Polling · không cần webhook</div></aside><main class="main">
{% if msg %}<div class="alert">{{msg}}</div>{% endif %}
{{content|safe}}
</main></div>
{% endif %}
</body></html>
"""

def render_page(page, content, msg=""):
    return render_template_string(BASE_HTML, title="KingBot Admin", cfg=cfg, page=page, content=content, msg=msg)

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
    if not session.get("login"):
        return render_page("dashboard", "")
    total = len(db["users"])
    bal = sum(int(u.get("balance", 0)) for u in db["users"].values())
    pro = sum(1 for u in db["users"].values() if u.get("plan") == "pro")
    basic = sum(1 for u in db["users"].values() if u.get("plan") == "basic")
    recent = list(reversed(list(db["users"].values())))[:10]
    rows = "".join([f"<tr><td><code>{u.get('id')}</code></td><td>@{u.get('username')}</td><td>{money(u.get('balance',0))}</td><td>{u.get('plan')}</td><td>{u.get('joined')}</td></tr>" for u in recent])
    content = f"""
    <div class="top"><div class="title">📊 Dashboard</div><div class="pill">{'✅ Bot đang chạy' if bot_running else '❌ Bot chưa chạy'}</div></div>
    <div class="grid">
      <div class="card stat"><span class="mut">Tổng users</span><b style="color:var(--c)">{total}</b></div>
      <div class="card stat"><span class="mut">Gói Pro</span><b style="color:var(--a)">{pro}</b></div>
      <div class="card stat"><span class="mut">Gói Thường</span><b style="color:var(--y)">{basic}</b></div>
      <div class="card stat"><span class="mut">Tổng số dư</span><b style="color:var(--g)">{money(bal)}</b></div>
    </div><br>
    <div class="card"><h2>👥 Users mới nhất</h2><table><tr><th>ID</th><th>Username</th><th>Số dư</th><th>Gói</th><th>Join</th></tr>{rows}</table></div>
    """
    return render_page("dashboard", content)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("login"):
        return render_page("settings", "")
    msg = ""
    if request.method == "POST":
        # Lưu ý BOT_TOKEN từ ENV vẫn ưu tiên sau restart
        cfg["bot_token"] = request.form.get("bot_token", "").strip()
        cfg["admin_password"] = request.form.get("admin_password", "admin123")
        cfg["shop_name"] = request.form.get("shop_name", "KingBot Luxury")
        cfg["accent"] = request.form.get("accent", "#8b5cf6")
        cfg["welcome_text"] = request.form.get("welcome_text", "")
        cfg["payment_info"] = request.form.get("payment_info", "")
        cfg["plans"]["basic"]["price"] = int(request.form.get("basic_price", 50000) or 50000)
        cfg["plans"]["basic"]["predictions"] = int(request.form.get("basic_predictions", 100) or 100)
        cfg["plans"]["pro"]["price"] = int(request.form.get("pro_price", 150000) or 150000)
        save_cfg()
        msg = "Đã lưu cấu hình. Nếu đổi token, vào Render bấm Manual Deploy/Restart để chắc chắn."
    content = f"""
    <div class="top"><div class="title">⚙️ Cài đặt</div></div>
    <form method="post"><div class="grid2">
      <div class="card"><h2>🤖 Bot</h2>
        <label>Bot Token</label><input name="bot_token" value="{cfg.get('bot_token','')}">
        <label>Mật khẩu web admin</label><input name="admin_password" value="{cfg.get('admin_password','admin123')}">
        <label>Tên shop/bot</label><input name="shop_name" value="{cfg.get('shop_name','')}">
        <label>Màu chủ đạo</label><input name="accent" value="{cfg.get('accent','#8b5cf6')}">
        <label>Text chào mừng</label><input name="welcome_text" value="{cfg.get('welcome_text','')}">
      </div>
      <div class="card"><h2>💳 Thanh toán & gói</h2>
        <label>Thông tin thanh toán</label><textarea name="payment_info">{cfg.get('payment_info','')}</textarea>
        <label>Giá gói thường</label><input type="number" name="basic_price" value="{cfg['plans']['basic']['price']}">
        <label>Lượt gói thường</label><input type="number" name="basic_predictions" value="{cfg['plans']['basic']['predictions']}">
        <label>Giá gói Pro</label><input type="number" name="pro_price" value="{cfg['plans']['pro']['price']}">
      </div>
    </div><br><button class="btn pri">💾 Lưu cấu hình</button></form>
    """
    return render_page("settings", content, msg)

@app.route("/users", methods=["GET", "POST"])
def users():
    if not session.get("login"):
        return render_page("users", "")
    msg = ""
    if request.method == "POST":
        uid = request.form.get("uid", "").strip()
        amount = int(request.form.get("amount", 0) or 0)
        action = request.form.get("action")
        if uid in db["users"]:
            if action == "add":
                db["users"][uid]["balance"] = int(db["users"][uid].get("balance", 0)) + amount
                msg = f"Đã cộng {money(amount)}"
            if action == "set":
                db["users"][uid]["balance"] = amount
                msg = f"Đã set số dư {money(amount)}"
            if action == "delete":
                db["users"].pop(uid, None)
                msg = "Đã xóa user"
            save_db()
    rows = ""
    for u in reversed(list(db["users"].values())):
        uid = u.get("id")
        rows += f"""<tr><td><code>{uid}</code></td><td>@{u.get('username')}</td><td>{money(u.get('balance',0))}</td><td>{u.get('plan')}</td>
        <td><form method="post" class="row"><input type="hidden" name="uid" value="{uid}"><input style="width:130px;margin:0" type="number" name="amount" placeholder="Số tiền"><button name="action" value="add" class="btn green">Cộng</button><button name="action" value="set" class="btn yellow">Set</button><button name="action" value="delete" class="btn red" onclick="return confirm('Xóa user?')">Xóa</button></form></td></tr>"""
    return render_page("users", f"<div class='top'><div class='title'>👥 Users</div></div><div class='card'><table><tr><th>ID</th><th>User</th><th>Số dư</th><th>Gói</th><th>Hành động</th></tr>{rows}</table></div>", msg)

@app.route("/broadcast", methods=["GET", "POST"])
def web_broadcast():
    if not session.get("login"):
        return render_page("broadcast", "")
    msg = ""
    if request.method == "POST":
        content = request.form.get("message", "").strip()
        if content:
            db["announcements"].append({"message": content, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
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
    content = f"<div class='top'><div class='title'>📣 Thông báo</div></div><div class='grid2'><div class='card'><form method='post'><textarea name='message' placeholder='Nội dung thông báo'></textarea><button class='btn pri'>Gửi toàn bộ</button></form></div><div class='card'><h2>Lịch sử</h2>{anns}</div></div>"
    return render_page("broadcast", content, msg)

@app.route("/logs")
def logs():
    if not session.get("login"):
        return render_page("logs", "")
    txt = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()[-16000:]
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
