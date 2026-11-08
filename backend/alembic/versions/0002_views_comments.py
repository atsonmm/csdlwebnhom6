"""VIEW thống kê + chú thích tiếng Việt cho mọi bảng

Revision ID: 0002
Revises: 0001
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
}

V_EVENT_SALES = """
CREATE VIEW v_event_sales AS
SELECT o.event_id,
       o.show_id,
       i.tier_id,
       SUM(i.qty)::bigint           AS sold,
       SUM(i.price * i.qty)::bigint AS revenue
FROM order_items i
JOIN orders o ON o.id = i.order_id
WHERE o.status = 'paid'
GROUP BY o.event_id, o.show_id, i.tier_id
"""

# Mỗi đơn đóng góp đúng một lần vào revenue; số vé lấy bằng truy vấn con
# để total không bị cộng lặp theo số dòng order_items.
V_DAILY_REVENUE = """
CREATE VIEW v_daily_revenue AS
SELECT e.organizer_id,
       (o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS day,
       SUM(o.total)::bigint AS revenue,
       SUM((SELECT COALESCE(SUM(i.qty), 0) FROM order_items i WHERE i.order_id = o.id))::bigint AS tickets
FROM orders o
JOIN events e ON e.id = o.event_id
WHERE o.status = 'paid'
GROUP BY e.organizer_id, (o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
"""


def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def upgrade() -> None:
    op.execute(V_EVENT_SALES)
    op.execute(V_DAILY_REVENUE)
    for table, comment in TABLE_COMMENTS.items():
        op.execute(f"COMMENT ON TABLE {table} IS {_q(comment)}")
    op.execute(f"COMMENT ON VIEW v_event_sales IS {_q('Số vé đã bán và doanh thu (giá × số lượng) theo sự kiện, suất, hạng — chỉ đơn đã thanh toán')}")
    op.execute(f"COMMENT ON VIEW v_daily_revenue IS {_q('Doanh thu (tiền khách trả) và số vé theo ngày giờ Việt Nam, theo Ban tổ chức (NULL = sự kiện của sàn)')}")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_daily_revenue")
    op.execute("DROP VIEW IF EXISTS v_event_sales")
    for table in TABLE_COMMENTS:
        op.execute(f"COMMENT ON TABLE {table} IS NULL")
