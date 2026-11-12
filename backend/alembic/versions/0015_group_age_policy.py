"""group_age_policy: độ tuổi tối thiểu + chính sách cho từng HẠNG GIÁ của sơ đồ

map_groups.min_age (NULL = không giới hạn, 0–99) và map_groups.policy (văn bản, mặc định rỗng).
Người mua thấy trong hộp thoại chọn vé: "Khu vực dành cho người tham dự từ X tuổi", quyền lợi, chính sách.
Chạy trên CSDL có dữ liệu: cột mới NULL / '' cho mọi nhóm cũ, không đổi dòng nào.
Hạ phiên bản: dừng nếu đã có nhóm khai báo tuổi / chính sách (tránh mất dữ liệu âm thầm).

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, Sequence[str], None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("map_groups", sa.Column("min_age", sa.SmallInteger(), nullable=True))
    op.add_column("map_groups", sa.Column("policy", sa.Text(), nullable=False, server_default=""))
    op.create_check_constraint("ck_map_groups_min_age", "map_groups", "min_age IS NULL OR min_age BETWEEN 0 AND 99")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT count(*) FROM map_groups WHERE min_age IS NOT NULL OR policy <> ''")).scalar():
        raise RuntimeError("Đã có hạng giá khai báo độ tuổi / chính sách — không hạ phiên bản để tránh mất dữ liệu")
    op.drop_constraint("ck_map_groups_min_age", "map_groups", type_="check")
    op.drop_column("map_groups", "policy")
    op.drop_column("map_groups", "min_age")
