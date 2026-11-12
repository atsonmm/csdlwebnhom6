"""image_maps: sơ đồ của Ban tổ chức là ẢNH tải lên (+ vùng bấm từng khu) và 8 sơ đồ mẫu dạng ảnh

1. venue_maps.image_url — ảnh sơ đồ: /api/uploads/… (BTC tải lên) hoặc /map-templates/… (mẫu, ảnh tĩnh của frontend).
   Vùng bấm của khu nằm ở map_zones.shape ({"type": "rect", x, y, w, h, rotate} theo hệ toạ độ ảnh rộng 1000,
   hoặc {"type": "none"}) — không đổi lược đồ map_zones.
2. Nạp 8 sơ đồ MẪU dạng ảnh (organizer_id NULL, kind zones, không có khu — chỉ để tham khảo). 5 mẫu vẽ tay giữ nguyên.

Chạy trên CSDL có dữ liệu: cột mới NULL cho mọi sơ đồ cũ. Hạ phiên bản: xoá 8 mẫu ảnh (không sự kiện nào dùng được
mẫu) rồi bỏ cột; dừng nếu còn sơ đồ ảnh của BTC (tránh mất ảnh sơ đồ âm thầm).

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, Sequence[str], None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TEMPLATES = [
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
    op.add_column("venue_maps", sa.Column("image_url", sa.Text(), nullable=True))
    maps = sa.table("venue_maps", sa.column("id", sa.String), sa.column("kind", sa.String), sa.column("name", sa.Text),
                    sa.column("decor", postgresql.JSONB), sa.column("image_url", sa.Text))
    op.bulk_insert(maps, [{"id": i, "kind": "zones", "name": n, "decor": {}, "image_url": f"/map-templates/{f}"}
                          for i, n, f in TEMPLATES])


def downgrade() -> None:
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT count(*) FROM venue_maps WHERE organizer_id IS NOT NULL AND image_url IS NOT NULL")).scalar():
        raise RuntimeError("Còn sơ đồ ảnh do Ban tổ chức tạo — không hạ phiên bản để tránh mất dữ liệu")
    op.execute(sa.text("DELETE FROM venue_maps WHERE id = ANY(:ids)").bindparams(ids=[t[0] for t in TEMPLATES]))
    op.drop_column("venue_maps", "image_url")
