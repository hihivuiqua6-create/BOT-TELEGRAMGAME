KINGBOT RENDER READY

FILES:
- app.py
- requirements.txt
- render.yaml
- data/config.json
- data/database.json

RENDER SETTING:
Build Command:
pip install -r requirements.txt

Start Command:
python app.py

Environment:
BOT_TOKEN = token bot Telegram
ADMIN_PASSWORD = mật khẩu admin web
SHOP_NAME = tên shop

Sau deploy:
1) Mở link .onrender.com
2) Login admin bằng ADMIN_PASSWORD
3) Nhắn /start bot
4) Nếu muốn làm admin Telegram: nhắn /setadmin trong bot

Lưu ý:
- Bản này dùng polling nên không cần webhook.
- Render free có thể sleep, muốn 24/7 ổn cần paid hoặc VPS.
- Data JSON có thể mất khi redeploy/restart nếu không gắn persistent disk/database.
