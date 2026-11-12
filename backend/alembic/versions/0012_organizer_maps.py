"""organizer_maps: Ban tổ chức tự tạo sơ đồ khu / ghế

venue_maps thêm:
- organizer_id (FK organizers, ON DELETE CASCADE) — NULL = sơ đồ MẪU của sàn (5 sơ đồ có sẵn: chỉ để tham khảo,
  sự kiện mới không chọn được; sự kiện cũ đang dùng vẫn chạy);
- created_at;
- spec (jsonb) — input của trình tạo (hạng giá + khu / khu ghế) để mở lại sửa; sơ đồ mẫu vẽ tay = NULL.
map_groups / map_zones / map_seats giữ nguyên → trang khách và luồng đặt vé không đổi.

Chạy trên CSDL có dữ liệu: 5 sơ đồ hiện có nhận organizer_id = NULL (thành mẫu), created_at = now().

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("venue_maps", sa.Column("organizer_id", sa.Integer(), nullable=True))
    op.add_column("venue_maps", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"),
                                          nullable=False))
    op.add_column("venue_maps", sa.Column("spec", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_foreign_key("fk_venue_maps_organizer", "venue_maps", "organizers", ["organizer_id"], ["user_id"],
                          ondelete="CASCADE")
    op.create_index("ix_venue_maps_organizer_id", "venue_maps", ["organizer_id"])


def downgrade() -> None:
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT count(*) FROM venue_maps WHERE organizer_id IS NOT NULL")).scalar():
        raise RuntimeError("Còn sơ đồ do Ban tổ chức tạo — không hạ phiên bản để tránh mất dữ liệu")
    op.drop_index("ix_venue_maps_organizer_id", table_name="venue_maps")
    op.drop_constraint("fk_venue_maps_organizer", "venue_maps", type_="foreignkey")
    for col in ("spec", "created_at", "organizer_id"):
        op.drop_column("venue_maps", col)
