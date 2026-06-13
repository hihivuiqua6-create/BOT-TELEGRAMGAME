KINGBOT ULTRA RENDER

Render:
Build Command:
pip install -r requirements.txt

Start Command:
python app.py

Environment:
BOT_TOKEN=8692584207:AAFlXH1Rt2z4vLWLvgQySwj33dV20LqGk3k
ADMIN_PASSWORD=admin123
SHOP_NAME=KingBot Luxury
GROUP_CHAT_ID=-100xxxxxxxxxx

Chức năng:
- Web admin siêu đẹp
- LC79 / HitClub / BetVip
- Gói Thường / Pro theo giờ
- Không có free, phải mua gói mới dự đoán
- Nạp tiền nhập số tiền -> VietQR
- Admin duyệt nạp web hoặc /duyetnap ORDER_ID
- Feedback: user gửi ghi chú + ảnh, admin duyệt để gửi lên group
- Thông báo mua gói / nạp thành công lên group, có che thông tin user
- Basic engine và Pro engine khác nhau

Lưu ý:
Kết quả phân tích MD5 chỉ mang tính tham khảo, không bảo đảm thắng.
Render free có thể sleep và data JSON có thể mất nếu redeploy/restart.


UPDATE:
- Web admin có tab Admin IDs.
- Chỉ Telegram ID đã add trong Admin IDs mới nhận thông báo đơn nạp.
- Khi user tạo đơn nạp, admin nhận nút ✅ Duyệt / ❌ Từ chối ngay trên Telegram.
- Web admin mục Nạp tiền cũng có Duyệt / Từ chối.

UPDATE FLOW:
- Mỗi cổng game có icon emoji riêng, chỉnh được trong Admin > Cài đặt.
- User bấm Chọn Cổng & Gói -> chọn cổng -> hiện ngay danh sách gói.
- Nếu đã mua gói còn hạn, gửi MD5 là dự đoán ngay.
- Nếu chưa mua/hết hạn, bot bắt mua gói trước.

UPDATE HOURS + COOLDOWN:
- Chọn gói xong bot yêu cầu nhập số giờ cần mua.
- User nhập ví dụ 6 -> bot tính tổng tiền, số dư còn lại, rồi hiện nút Thanh toán/Từ chối.
- Thanh toán xong mới kích hoạt gói đúng số giờ.
- Tạo hóa đơn nạp tiền: mỗi user 3 phút mới tạo được 1 hóa đơn pending.

FIX FINAL:
- Mua gói rồi chọn cổng sẽ không bắt mua lại, chọn cổng xong gửi MD5 đánh luôn.
- Hiển thị giờ còn lại trong bot.
- Sửa nút Quay lại bằng safe edit/send, tránh lỗi message cũ không edit được.
- Tách thuật toán ra file engine_md5.py để nâng cấp riêng.
- Admin có ô nhập Group Chat ID / @username / link group public; add bot vào group là gửi được.
  Lưu ý: link invite t.me/+... không lấy chat_id tự động được bằng Bot API, nên dùng group public @username hoặc -100chatid.

UPDATE BACKUP + FLOW:
- Không cần chọn cổng trước khi mua gói.
- Mua gói Thường/Pro trước, nhập số giờ, thanh toán.
- Sau khi có gói, user chọn cổng game rồi gửi MD5 đánh luôn.
- Gói Thường và Pro dùng engine khác nhau trong engine_md5.py.
- Không cần nhập BIN ngân hàng, nhập tên bank như MSB, VCB, MBBANK, ACB...
- Có PHP backup cho Infinity tại thư mục php_backup_infinity/backup.php.
- Bot tự pull backup khi start và push backup theo chu kỳ để giữ full dữ liệu.

UPDATE FREE/BONUS:
- Admin bật/tắt dự đoán free, set lượt free/ngày.
- Free dùng engine riêng predict_free trong engine_md5.py, yếu hơn Basic/Pro.
- Admin bật/tắt bonus nạp tiền: nạp đủ mức sẽ cộng thêm % tiền.
- Admin bật/tắt random bonus khi mua gói: có tỉ lệ nhận bonus tiền.
- User có thể mua thêm giờ bất cứ lúc nào; hạn dùng tự cộng dồn.
- Backup chỉ backup dữ liệu/config JSON, không ghi đè code hay engine_md5.py nên nâng cấp thuật toán không bị mất.

RENDER FIX ALL:
- Sửa route Settings dễ gây crash runtime.
- Thêm Procfile.
- Đảm bảo requests trong requirements.
- Backup pull không đè BOT_TOKEN/ADMIN_PASSWORD/SHOP_NAME từ Render ENV.
- Nếu deploy vẫn đỏ: vào Logs gửi dòng Traceback cuối.
- Render Start Command: python app.py
- Build Command: pip install -r requirements.txt
