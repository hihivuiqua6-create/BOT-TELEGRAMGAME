KINGBOT V95 MULTI SOURCE

Render:
- Build Command: pip install -r requirements.txt
- Start Command: python app.py

Root chỉ có 4 folder chính:
1) data        : config/database/log
2) static      : CSS/JS admin
3) templates   : template admin
4) legacy_api  : source api game cũ + bản V93 tham chiếu

Nâng cấp V95:
- Chọn kiểu dự đoán: MD5 hoặc No MD5.
- MD5 chỉ hiện cổng có hỗ trợ MD5: LC79, HitClub, BetVip.
- No MD5 hỗ trợ: SunWin, LC79, HitClub, B52, BetVip.
- Sau khi chọn kiểu dự đoán -> chọn cổng -> chọn Free/Thường/Pro.
- Không khóa cứng 1 gói; mỗi lần có thể đổi gói nếu còn hạn.
- Gói Thường/Pro hiển thị thời gian còn lại.
- /nomd5 để chạy nhanh chế độ No MD5.
- Cùng MD5/cùng phiên No MD5 dùng seed ổn định, không dùng random/time phụ ngoài phiên.
- Tối ưu Render: bỏ node_modules, bỏ token/log thừa trong legacy, giảm file rác.

Lưu ý:
- Không commit .env/token thật lên GitHub.
- Muốn cấu hình token bot thì vào admin hoặc biến môi trường BOT_TOKEN.
