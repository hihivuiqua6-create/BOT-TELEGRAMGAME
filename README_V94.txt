KINGBOT V94 - Multi Plan + Render Stable

Điểm mới:
- Mỗi user có hạn riêng cho Gói Thường và Gói Pro.
- User chọn cổng xong sẽ chọn Free / Thường / Pro để dùng, không bị khóa cố định một gói.
- Mua thêm giờ gói nào cộng dồn vào đúng gói đó.
- /start và Tài khoản hiển thị: Thường còn bao lâu, Pro còn bao lâu, Free còn bao lâu.
- Bỏ dòng "🔎 Chi tiết: Ổn định seed + BetVip V93".
- Dòng cảnh báo cuối đổi thành: "🍀✨ Nên theo khi cầu đẹp...".
- Admin CSS làm lại glass/luxury, mobile responsive hơn.
- Render ổn định hơn: dùng gunicorn 1 worker + threads + timeout + max-requests để hạn chế sập/treo.

Deploy Render/GitHub:
1. Up toàn bộ file trong zip lên root repo GitHub.
2. Render dùng Build Command: pip install -r requirements.txt
3. Start Command đã có trong render.yaml/Procfile bằng gunicorn.
4. Không thêm token bot vào ENV nếu muốn quản lý trong Admin Web.
5. Vào /settings để dán token bot, bank, giá gói, cổng game, thuật toán.
