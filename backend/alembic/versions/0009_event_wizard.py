"""event_wizard: trường của wizard tạo sự kiện 4 bước (kiểu Ticketbox)

events:     poster_url, banner_url (ảnh đã upload, /api/uploads/…), is_online, terms_and_conditions,
            ticket_sale_end_at (giờ đóng bán) + CHECK ck_events_sale_window (đóng bán sau mở bán)
organizers: bank_name, bank_account_number, bank_account_holder, bank_branch (thông tin nhận tiền)
            + CHECK ck_organizers_bank_account (6–20 chữ số)

Chạy được trên CSDL ĐÃ CÓ DỮ LIỆU: cột mới đều NULL hoặc có mặc định (is_online = false) → không phải điền lại
dữ liệu cũ; hai CHECK đều đúng với mọi dòng cũ (cột mới NULL). ticket_tiers.max_per_order ĐÃ CÓ từ 0001.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("poster_url", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("banner_url", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("is_online", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("events", sa.Column("terms_and_conditions", sa.Text(), nullable=True))
    op.add_column("events", sa.Column("ticket_sale_end_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_events_sale_window", "events",
        "ticket_sale_end_at IS NULL OR sale_start IS NULL OR ticket_sale_end_at > sale_start")
    for col in ("bank_name", "bank_account_number", "bank_account_holder", "bank_branch"):
        op.add_column("organizers", sa.Column(col, sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_organizers_bank_account", "organizers",
        "bank_account_number IS NULL OR bank_account_number ~ '^[0-9]{6,20}$'")


def downgrade() -> None:
    op.drop_constraint("ck_organizers_bank_account", "organizers", type_="check")
    for col in ("bank_branch", "bank_account_holder", "bank_account_number", "bank_name"):
        op.drop_column("organizers", col)
    op.drop_constraint("ck_events_sale_window", "events", type_="check")
    for col in ("ticket_sale_end_at", "terms_and_conditions", "is_online", "banner_url", "poster_url"):
        op.drop_column("events", col)
