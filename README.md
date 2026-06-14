# KingBot Render V100

Build Command:
```
pip install -r requirements.txt
```

Start Command:
```
python app.py
```

Hoặc Render dùng `render.yaml`:
```
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

ENV cần có:
```
BOT_TOKEN=token_bot_telegram
ADMIN_ID=id_admin
```

V100:
- No MD5 dùng API thật từ sadd.zip, bỏ 1.html.
- Reply No MD5 rút gọn theo yêu cầu.
- No MD5 tự edit cùng 1 tin nhắn mỗi 5s, không spam tin mới.
- MD5 giữ flow cũ.
