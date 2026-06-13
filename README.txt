KINGBOT RENDER FULL ORIGINAL + V30 UPGRADE

Nâng cấp trong bản này:
- Giữ nguyên cấu trúc source gốc, không rút gọn file.
- Fix nhận hash 32 ký tự MD5 và hash HitClub/SHA256 64 ký tự.
- Engine V30: Free Lite < Basic Omni < Pro HitClub SHA512/SHA3/BLAKE.
- Gói mặc định: Gói Thường 1 giờ = 1500, Gói Pro 1 giờ = 3500.
- Admin mobile responsive: có nút Menu, sidebar trượt, bảng cuộn ngang, form không vỡ trên điện thoại.
- Backup Admin: tải kingbot_full_backup.js và import lại để khôi phục full config + database + thuật toán admin.

Chạy Render:
Build command: pip install -r requirements.txt
Start command: python app.py

Lưu ý: Hash/MD5 là một chiều nên không thể có thuật toán đảm bảo 100%; engine chỉ là phân tích tham khảo.


V90 UPDATE:
- Admin có tab /algorithm để dán/upload file thuật toán .py.
- Bot ưu tiên thuật toán admin nếu bật; nếu tắt dùng engine_md5.py.
- Engine đã truyền đúng game gate vào LC79/HitClub/Bet, thêm history gần nhất để bắt cầu.
- HitClub SHA256 64 ký tự có profile riêng V90, advice, real confidence, % T/X.
- File admin_algorithm_hitclub_v90.py có thể tải/dán vào Admin > Thuật toán.
