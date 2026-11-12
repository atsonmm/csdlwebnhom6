"""Giữ vé 15 phút: đơn có thêm trạng thái 'pending' (đang giữ chỗ) và 'expired' (hết hạn / chọn lại)

Luồng mới: chọn vé → giữ chỗ (orders.status = 'pending', expires_at = now() + 15 phút) → câu hỏi → thanh toán →
xác nhận ('paid', lúc đó mới sinh vé). Khi giữ chỗ chưa biết người mua và phương thức → các cột đó cho phép NULL, nhưng
ck_orders_buyer_known bắt buộc đủ khi đơn đã qua giai đoạn giữ (paid / refunded / cancelled).
- orders.expires_at timestamptz NULL; ck_orders_pending_expiry: đơn 'pending' phải có expires_at
- chỉ mục từng phần ix_orders_pending_expiry (expires_at) WHERE status = 'pending' cho việc dọn đơn hết hạn
Chạy trên CSDL có dữ liệu: mọi đơn cũ đều 'paid' / 'refunded' / 'cancelled' và đã đủ thông tin nên thoả các ràng buộc mới.
Hạ phiên bản: xoá cột + ràng buộc, đặt lại NOT NULL — LỖI nếu còn đơn 'pending' / 'expired' (chưa có người mua);
hãy xoá hoặc chờ chúng hết hạn rồi dọn trước khi hạ.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, Sequence[str], None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BUYER_COLUMNS = (("buyer_name", sa.Text()), ("buyer_email", sa.String(254)), ("buyer_phone", sa.String(20)),
                 ("method", sa.String(10)))


def upgrade() -> None:
    op.add_column("orders", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    for name, type_ in BUYER_COLUMNS:
        op.alter_column("orders", name, existing_type=type_, nullable=True)
    op.drop_constraint("ck_orders_status", "orders", type_="check")
    op.create_check_constraint("ck_orders_status", "orders",
                               "status IN ('pending','paid','refunded','cancelled','expired')")
    op.create_check_constraint("ck_orders_pending_expiry", "orders", "status <> 'pending' OR expires_at IS NOT NULL")
    op.create_check_constraint(
        "ck_orders_buyer_known", "orders",
        "status IN ('pending','expired') OR (buyer_name IS NOT NULL AND buyer_email IS NOT NULL "
        "AND buyer_phone IS NOT NULL AND method IS NOT NULL)")
    op.create_index("ix_orders_pending_expiry", "orders", ["expires_at"], postgresql_where=sa.text("status = 'pending'"))


def downgrade() -> None:
    op.drop_index("ix_orders_pending_expiry", table_name="orders")
    op.drop_constraint("ck_orders_buyer_known", "orders", type_="check")
    op.drop_constraint("ck_orders_pending_expiry", "orders", type_="check")
    op.drop_constraint("ck_orders_status", "orders", type_="check")
    op.create_check_constraint("ck_orders_status", "orders", "status IN ('paid','refunded','cancelled')")
    for name, type_ in BUYER_COLUMNS:
        op.alter_column("orders", name, existing_type=type_, nullable=False)
    op.drop_column("orders", "expires_at")
