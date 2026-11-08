"""withdrawals: yêu cầu rút tiền của Ban tổ chức (chờ xử lý → đã chuyển / từ chối)

Chạy trên CSDL ĐÃ CÓ DỮ LIỆU: chỉ tạo bảng mới (rỗng), không đụng dòng nào của bảng cũ — đếm số dòng trước/sau.
Hạ phiên bản bị chặn khi bảng đã có yêu cầu rút tiền (không xoá dữ liệu tiền âm thầm).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COUNTED = ("users", "organizers", "events", "orders")
COMMENT = "Yêu cầu rút tiền của Ban tổ chức: chờ xử lý → Admin đánh dấu đã chuyển hoặc từ chối (kèm lý do)"


def _count(conn, table: str) -> int:
    return conn.execute(sa.text(f"SELECT count(*) FROM {table}")).scalar()


def upgrade() -> None:
    conn = op.get_bind()
    before = {t: _count(conn, t) for t in COUNTED}
    op.create_table(
        "withdrawals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organizer_id", sa.Integer(), sa.ForeignKey("organizers.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("bank_name", sa.Text(), nullable=False),
        sa.Column("account_no", sa.String(length=20), nullable=False),
        sa.Column("account_name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=10), server_default="pending", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_withdrawals_amount"),
        sa.CheckConstraint("status IN ('pending','paid','rejected')", name="ck_withdrawals_status"),
        sa.CheckConstraint("(status = 'pending') = (processed_at IS NULL)", name="ck_withdrawals_processed"),
        sa.CheckConstraint("status <> 'rejected' OR note IS NOT NULL", name="ck_withdrawals_reject_note"),
        comment=COMMENT,
    )
    op.create_index("ix_withdrawals_organizer_created", "withdrawals", ["organizer_id", "created_at"])
    after = {t: _count(conn, t) for t in COUNTED}
    if after != before:
        raise RuntimeError(f"0007: số dòng thay đổi {before} → {after}")


def downgrade() -> None:
    conn = op.get_bind()
    n = _count(conn, "withdrawals")
    if n:
        raise RuntimeError(f"0007 downgrade: bảng withdrawals còn {n} yêu cầu rút tiền — sao lưu/xử lý tay trước rồi hạ lại")
    op.drop_index("ix_withdrawals_organizer_created", table_name="withdrawals")
    op.drop_table("withdrawals")
