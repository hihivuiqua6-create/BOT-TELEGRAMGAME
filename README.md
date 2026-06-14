# KingBot Render V102

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
python app.py
```

V102:
- Đổi Dự đoán No MD5 thành Dự đoán API.
- API live cập nhật cùng 1 tin nhắn mỗi 5 giây, chạy lâu không tự im sau vài phiên.
- MD5 reply cùng style với API, chỉ thêm dòng MD5 hiện tại.
- Giữ đúng 4 folder chính: data, templates, static, legacy_api.
- Giữ app.py, engine_md5.py, requirements.txt, render.yaml ở root.
