"""vector_maps: sơ đồ VECTOR bán được vé — một sơ đồ có thể gộp khu ĐỨNG và khu NGỒI; bỏ 8 sơ đồ mẫu ảnh

1. venue_maps.kind và events.layout nhận thêm 'mixed' (sơ đồ có cả khu đứng lẫn khu ngồi).
2. map_zones.kind ('standing' | 'seated'): khu đứng bán theo số lượng; khu ngồi bán theo ghế (map_seats.section = id khu).
   Dữ liệu cũ: khu của sơ đồ kind 'seats' → 'seated', còn lại 'standing'.
3. map_seats.seat_type ('standard' | 'accessible'): ghế dành cho xe lăn. Dữ liệu cũ: 'standard'.
4. ticket_tiers.seated: hạng vé bán theo ghế (đã bán = seat_holds) hay theo số lượng (tier_stock).
   Trước đây suy ra từ events.layout = 'seats'; sự kiện 'mixed' có cả hai loại hạng nên phải lưu theo từng hạng.
   Dữ liệu cũ: true cho mọi hạng của sự kiện layout 'seats'.
5. Bỏ 8 sơ đồ mẫu dạng ẢNH (0013, không có khu, không sự kiện nào dùng được): Ban tổ chức tự dựng sơ đồ
   bằng trình dựng vector nên không còn mục "sơ đồ mẫu".

Chạy trên CSDL có dữ liệu: chỉ thêm cột có giá trị mặc định + cập nhật theo dữ liệu cũ, không xoá dòng nào
ngoài 8 mẫu ảnh. Hạ phiên bản: dừng nếu đã có sơ đồ / sự kiện 'mixed' hoặc ghế xe lăn (tránh mất dữ liệu âm thầm).

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, Sequence[str], None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_IMAGE_TEMPLATES = [
    ("mau-quang-ninh-concert", "Quảng Ninh Concert · khu đứng + khu ngồi", "quang-ninh-concert.jpg"),
    ("mau-san-van-dong-chu-u", "Sân vận động hình chữ U · bảng giá CAT", "san-van-dong-chu-u.jpg"),
    ("mau-v-concert", "V Concert · Trung tâm Triển lãm", "v-concert-trien-lam.jpg"),
    ("mau-g-dragon", "Concert G-Dragon · Hà Nội", "g-dragon-ha-noi.jpg"),
    ("mau-anh-trai", "Anh Trai Vượt Ngàn Chông Gai · sân vận động", "anh-trai-vuot-ngan-chong-gai.jpg"),
    ("mau-sao-concert", "SAO Concert · seat map", "sao-concert.jpg"),
    ("mau-hoi-truong-2-tang", "Hội trường 2 tầng · ghế đánh số", "hoi-truong-2-tang.jpg"),
    ("mau-nha-hat-tron", "Nhà hát tròn · sân khấu trung tâm", "nha-hat-tron.jpg"),
]


def upgrade() -> None:
    # 1. 'mixed'
    op.drop_constraint("ck_venue_maps_kind", "venue_maps", type_="check")
    op.create_check_constraint("ck_venue_maps_kind", "venue_maps", "kind IN ('zones','seats','mixed')")
    op.drop_constraint("ck_events_layout", "events", type_="check")
    op.create_check_constraint("ck_events_layout", "events", "layout IN ('list','zones','seats','mixed')")

    # 2. map_zones.kind
    op.add_column("map_zones", sa.Column("kind", sa.String(8), nullable=False, server_default="standing"))
    op.execute("UPDATE map_zones z SET kind = 'seated' FROM venue_maps m WHERE m.id = z.map_id AND m.kind = 'seats'")
    op.create_check_constraint("ck_map_zones_kind", "map_zones", "kind IN ('standing','seated')")

    # 3. map_seats.seat_type
    op.add_column("map_seats", sa.Column("seat_type", sa.String(12), nullable=False, server_default="standard"))
    op.create_check_constraint("ck_map_seats_type", "map_seats", "seat_type IN ('standard','accessible')")

    # 4. ticket_tiers.seated
    op.add_column("ticket_tiers", sa.Column("seated", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE ticket_tiers t SET seated = true FROM events e WHERE e.id = t.event_id AND e.layout = 'seats'")

    # 5. bỏ 8 mẫu ảnh (không có khu nên không sự kiện nào tham chiếu)
    op.get_bind().execute(sa.text("DELETE FROM venue_maps WHERE id = ANY(:ids) AND organizer_id IS NULL AND NOT EXISTS "
                                  "(SELECT 1 FROM events e WHERE e.map_id = venue_maps.id)"),
                          {"ids": [t[0] for t in OLD_IMAGE_TEMPLATES]})


def downgrade() -> None:
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT (SELECT count(*) FROM venue_maps WHERE kind = 'mixed' AND organizer_id IS NOT NULL)"
                            " + (SELECT count(*) FROM events WHERE layout = 'mixed')"
                            " + (SELECT count(*) FROM map_seats s JOIN venue_maps m ON m.id = s.map_id"
                            "    WHERE s.seat_type = 'accessible' AND m.organizer_id IS NOT NULL)")).scalar():
        raise RuntimeError("Đã có sơ đồ/sự kiện gộp đứng + ngồi hoặc ghế xe lăn — không hạ phiên bản để tránh mất dữ liệu")
    maps = sa.table("venue_maps", sa.column("id", sa.String), sa.column("kind", sa.String), sa.column("name", sa.Text),
                    sa.column("decor", postgresql.JSONB), sa.column("image_url", sa.Text))
    op.bulk_insert(maps, [{"id": i, "kind": "zones", "name": n, "decor": {}, "image_url": f"/map-templates/{f}"}
                          for i, n, f in OLD_IMAGE_TEMPLATES])
    op.drop_column("ticket_tiers", "seated")
    op.drop_constraint("ck_map_seats_type", "map_seats", type_="check")
    op.drop_column("map_seats", "seat_type")
    op.drop_constraint("ck_map_zones_kind", "map_zones", type_="check")
    op.drop_column("map_zones", "kind")
    op.drop_constraint("ck_events_layout", "events", type_="check")
    op.create_check_constraint("ck_events_layout", "events", "layout IN ('list','zones','seats')")
    op.drop_constraint("ck_venue_maps_kind", "venue_maps", type_="check")
    op.create_check_constraint("ck_venue_maps_kind", "venue_maps", "kind IN ('zones','seats')")
