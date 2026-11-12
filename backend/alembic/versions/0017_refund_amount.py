"""refund_amount: số tiền thực hoàn của đơn khi huỷ sự kiện (sửa lỗi hoàn hai lần cho vé đã bán lại)

Trước 0017, huỷ sự kiện hoàn đủ `total` cho MỌI đơn 'paid': đơn gốc của người bán được hoàn cả những vé họ đã bán
lại (đã nhận tiền từ người mua lại), đồng thời đơn 'resale' của người mua lại cũng được hoàn → một ghế hoàn hai lần.
- orders.refund_amount INTEGER NULL — NULL = hoàn đủ total (giữ nghĩa cũ cho đơn hoàn trước đây / dữ liệu mẫu)
- CHECK: chỉ đơn 'refunded' mới có refund_amount, và 0 ≤ refund_amount ≤ total
Chạy trên CSDL có dữ liệu: đơn đã hoàn mà có vé đã chuyển nhượng được tính lại
  refund_amount = total × (giá gốc vé còn giữ / giá gốc mọi vé của đơn); các đơn khác giữ NULL.
Hạ phiên bản: bỏ cột (mất số tiền hoàn từng phần — chỉ là số hiển thị, trạng thái đơn không đổi).

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, Sequence[str], None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("refund_amount", sa.Integer(), nullable=True))
    op.execute("""
        UPDATE orders o
           SET refund_amount = (o.total * t.kept) / t.face
          FROM (SELECT order_id,
                       SUM(price) AS face,
                       COALESCE(SUM(price) FILTER (WHERE transferred_at IS NULL), 0) AS kept
                  FROM tickets
                 GROUP BY order_id) t
         WHERE t.order_id = o.id
           AND o.status = 'refunded'
           AND t.face > 0
           AND t.kept < t.face
    """)
    op.create_check_constraint(
        "ck_orders_refund_amount", "orders",
        "refund_amount IS NULL OR (status = 'refunded' AND refund_amount BETWEEN 0 AND total)")


def downgrade() -> None:
    op.drop_constraint("ck_orders_refund_amount", "orders", type_="check")
    op.drop_column("orders", "refund_amount")
