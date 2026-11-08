"""Chú thích tiếng Việt cho từng bảng (khớp với migration 0002; hiện trong pgAdmin/ERD)"""

TABLE_COMMENTS = {
    "categories": "Thể loại sự kiện (Nhạc sống, Sân khấu…)",
    "venue_maps": "Sơ đồ địa điểm: sơ đồ khu vực (zones) hoặc sơ đồ ghế (seats)",
    "map_groups": "Nhóm khu / hạng ghế trong một sơ đồ (màu, quyền lợi, số vé tối đa mỗi đơn)",
    "map_zones": "Khu vực trên sơ đồ khu (sức chứa, hình vẽ)",
    "map_seats": "Ghế trên sơ đồ ghế (hàng, số, toạ độ)",
    "events": "Sự kiện: của sàn (organizer_id NULL) hoặc do Ban tổ chức tạo (chờ duyệt → đã duyệt / bị trả lại)",
    "shows": "Suất diễn của sự kiện; id dạng YYYYMMDD-HHMM theo giờ Việt Nam",
    "ticket_tiers": "Hạng vé của sự kiện (với sơ đồ khu/ghế: mỗi khu hoặc hạng ghế là một hạng)",
    "home_slots": "Vị trí sự kiện trên các khu của trang chủ; meta chỉ chứa phần trang trí",
    "users": "Tài khoản: khách (customer), Ban tổ chức (organizer), quản trị sàn (admin)",
    "sessions": "Phiên đăng nhập; chỉ lưu SHA-256 của token, không lưu token gốc",
    "password_resets": "Yêu cầu đặt lại mật khẩu (token băm, hạn dùng, đã dùng chưa)",
    "organizers": "Hồ sơ Ban tổ chức; 1 tài khoản = 1 đơn vị tổ chức",
    "coupons": "Mã giảm giá: số tiền giảm và giá trị đơn tối thiểu",
    "tier_stock": "Kho vé theo suất + hạng: presold (bán sẵn trước khi hệ thống chạy) + sold (bán qua hệ thống) ≤ capacity",
    "seat_holds": "Ghế đã bán theo suất; order_id NULL = đã bán sẵn. Khoá chính chặn bán trùng ghế",
    "orders": "Đơn hàng; total = subtotal − discount (Ban tổ chức chịu giảm giá)",
    "order_items": "Dòng đơn hàng: hạng vé × số lượng, price là giá tại thời điểm mua",
    "tickets": "Vé điện tử; mỗi vé một mã check-in riêng",
    "withdrawals": "Yêu cầu rút tiền của Ban tổ chức: chờ xử lý → Admin đánh dấu đã chuyển hoặc từ chối (kèm lý do)",
}
