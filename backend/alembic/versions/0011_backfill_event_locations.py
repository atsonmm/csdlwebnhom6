"""backfill_event_locations: gán mã tỉnh cho sự kiện tạo trước migration 0010 (chỉ đổi DỮ LIỆU, không đổi lược đồ)

Sự kiện cũ chỉ có city / address dạng chữ. Gán:
- province_code: city khớp provinces.short_name, không phân biệt hoa thường ("Hà nội" = "Hà Nội");
  bí danh sau sáp nhập: "Đà Lạt" → Lâm Đồng;
- street: địa chỉ cũ (cắt 80 ký tự, đúng giới hạn ô "Số nhà, tên đường") để BTC sửa trong wizard không bị chặn;
- ward_code để trống (địa chỉ cũ không có phường đáng tin cậy để suy ra).
Bỏ qua: sự kiện Online, sự kiện đã có mã, city không khớp tỉnh nào (giữ nguyên dạng chữ).
city / address KHÔNG đổi → bộ lọc, tìm kiếm, trang khách giữ nguyên.

Hạ phiên bản: không làm gì (mã đã gán đều hợp lệ với lược đồ 0010; không phân biệt được dòng nào do migration này gán).

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-09
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BACKFILL = """
WITH alias(city, short_name) AS (VALUES ('đà lạt', 'Lâm Đồng'))
UPDATE events e
   SET province_code = p.code,
       street = NULLIF(left(btrim(e.address), 80), '')
  FROM provinces p
 WHERE e.province_code IS NULL
   AND NOT e.is_online
   AND (lower(btrim(e.city)) = lower(p.short_name)
        OR EXISTS (SELECT 1 FROM alias a WHERE a.city = lower(btrim(e.city)) AND a.short_name = p.short_name))
"""


def upgrade() -> None:
    op.execute(BACKFILL)


def downgrade() -> None:
    pass
