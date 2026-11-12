"""event_cancel: huỷ sự kiện (status 'cancelled' + lý do/thời điểm/người huỷ) và thời điểm hoàn tiền của đơn

Chạy trên CSDL ĐÃ CÓ DỮ LIỆU: chỉ thêm cột cho phép NULL + nới ràng buộc trạng thái, không viết lại dòng cũ.
Kiểm tra dữ liệu cũ trước khi đổi (trạng thái lạ → dừng, không sửa âm thầm) và đếm số dòng trước/sau.
Hạ phiên bản bị chặn khi đã có sự kiện bị huỷ (không xoá dữ liệu âm thầm) — xem database/docs/migration-0006.md.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COUNTED = ("events", "orders")


def _count(conn, table: str) -> int:
    return conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar()


def upgrade() -> None:
    conn = op.get_bind()
    bad = conn.execute(sa.text("SELECT count(*) FROM events WHERE status NOT IN ('pending','approved','rejected')")).scalar()
    if bad:
        raise RuntimeError(f"0006: có {bad} sự kiện mang trạng thái lạ — kiểm tra dữ liệu trước khi nâng cấp")
    before = {t: _count(conn, t) for t in COUNTED}

    op.drop_constraint("ck_events_status", "events", type_="check")
    op.create_check_constraint("ck_events_status", "events", "status IN ('pending','approved','rejected','cancelled')")
    op.add_column("events", sa.Column("cancel_reason", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("events", sa.Column("cancelled_by", sa.String(length=10), nullable=True))
    op.create_check_constraint("ck_events_cancelled_by", "events", "cancelled_by IN ('organizer','admin')")
    # Sự kiện đã huỷ ⇔ có thời điểm huỷ + người huỷ + lý do
    op.create_check_constraint(
        "ck_events_cancel_fields", "events",
        "(status = 'cancelled') = (cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL AND cancel_reason IS NOT NULL)")
    op.add_column("orders", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
    # Chỉ đơn đã hoàn mới có thời điểm hoàn (đơn hoàn cũ trước 0006 để NULL)
    op.create_check_constraint("ck_orders_refunded_at", "orders", "refunded_at IS NULL OR status = 'refunded'")

    after = {t: _count(conn, t) for t in COUNTED}
    if after != before:
        raise RuntimeError(f"0006: số dòng thay đổi {before} → {after}")


def downgrade() -> None:
    conn = op.get_bind()
    n = conn.execute(sa.text("SELECT count(*) FROM events WHERE status = 'cancelled'")).scalar()
    if n:
        raise RuntimeError(
            f"0006 downgrade: còn {n} sự kiện 'cancelled' — phiên bản 0005 không biểu diễn được. "
            "Xử lý tay trước (vd. đổi về 'approved' + active = false) rồi hạ lại.")
    op.drop_constraint("ck_orders_refunded_at", "orders", type_="check")
    op.drop_column("orders", "refunded_at")
    op.drop_constraint("ck_events_cancel_fields", "events", type_="check")
    op.drop_constraint("ck_events_cancelled_by", "events", type_="check")
    op.drop_column("events", "cancelled_by")
    op.drop_column("events", "cancelled_at")
    op.drop_column("events", "cancel_reason")
    op.drop_constraint("ck_events_status", "events", type_="check")
    op.create_check_constraint("ck_events_status", "events", "status IN ('pending','approved','rejected')")
