"""perf_indexes: 2 chỉ mục phục vụ 2 truy vấn thật (đo trước/sau ở database/docs/hieu-nang.md)

1. ix_orders_buyer_trgm — GIN pg_trgm trên lower(mã đơn ' ' tên ' ' email ' ' SĐT): ô tìm của sổ đơn (A1/A3)
   dùng LIKE '%…%' → B-tree không dùng được, trigram thì được.
2. ix_orders_status_created — B-tree (status, created_at) INCLUDE (event_id, total): báo cáo doanh thu theo
   khoảng ngày chỉ lấy đơn 'paid' (B1/B3) → quét đúng khoảng, đọc tổng tiền ngay trên chỉ mục (index-only scan).

Chỉ thêm chỉ mục (không đổi dữ liệu). Hạ phiên bản: xoá 2 chỉ mục, GIỮ extension pg_trgm (có thể đang được
dùng ở nơi khác; giữ lại vô hại).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Phải TRÙNG KHỚP biểu thức tìm trong app/services/org_orders.py (SEARCH_EXPR) thì planner mới dùng chỉ mục
SEARCH_EXPR = "lower(id || ' ' || buyer_name || ' ' || buyer_email || ' ' || buyer_phone)"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # opclass nằm ở schema cài extension (thường là public) — ghi rõ schema để chạy được cả khi search_path khác
    ext_schema = op.get_bind().execute(sa.text(
        "SELECT extnamespace::regnamespace::text FROM pg_extension WHERE extname = 'pg_trgm'")).scalar()
    op.execute(f"CREATE INDEX ix_orders_buyer_trgm ON orders USING gin (({SEARCH_EXPR}) {ext_schema}.gin_trgm_ops)")
    op.create_index("ix_orders_status_created", "orders", ["status", "created_at"],
                    postgresql_include=["event_id", "total"])


def downgrade() -> None:
    op.drop_index("ix_orders_status_created", table_name="orders")
    op.execute("DROP INDEX ix_orders_buyer_trgm")
