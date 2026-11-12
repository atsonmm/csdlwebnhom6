"""Ảnh phần Giới thiệu của sự kiện (nhiều ảnh)

events.intro_images (TEXT[] , mặc định rỗng): danh sách URL ảnh đã upload (/api/uploads/…), hiện theo thứ tự trong khối
"Giới thiệu" ở trang sự kiện. Dữ liệu cũ nguyên vẹn (mảng rỗng → không hiện ảnh trong khối này).

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: Union[str, Sequence[str], None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("intro_images", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("events", "intro_images")
