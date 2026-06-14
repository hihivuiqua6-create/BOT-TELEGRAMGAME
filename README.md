# KingBot Render V101

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
python app.py
```

V101 fix:
- No MD5 dùng API thật, dự đoán phiên kế tiếp để tránh chậm 1 phiên.
- Live No MD5 cập nhật cùng 1 tin nhắn mỗi 1 giây.
- Chỉ chọn đúng 1 cổng; muốn đổi cổng bấm Quay lại chọn cổng.
- HitClub ưu tiên API từ source sadd.
- Giữ MD5 như cũ, nâng logic No MD5.
