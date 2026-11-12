"""locations_logo: đơn vị hành chính sau sáp nhập + địa chỉ chi tiết của sự kiện + logo Ban tổ chức

1. provinces (34 dòng) và wards (3.321 dòng) — NẠP DỮ LIỆU ngay trong migration từ backend/seed/locations_2025.json
   (bản chụp provinces.open-api.vn/api/v2, đơn vị hành chính 2 cấp từ 01/07/2025).
2. events: province_code, ward_code, street + khoá ngoại GHÉP (province_code, ward_code) → wards(province_code, code)
   → CSDL tự chặn "phường không thuộc tỉnh đã chọn"; CHECK ward_code cần province_code (MATCH SIMPLE sẽ bỏ qua
   khoá ngoại ghép khi một cột NULL).
3. organizers.logo_url (logo 275×275 của Ban tổ chức, upload kind=logo).

Chạy trên CSDL ĐÃ CÓ DỮ LIỆU: cột mới của events / organizers đều NULL → sự kiện cũ giữ city / address dạng chữ.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-09
"""
import json
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, Sequence[str], None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SNAPSHOT = Path(__file__).resolve().parents[2] / "seed" / "locations_2025.json"


def upgrade() -> None:
    provinces = op.create_table(
        "provinces",
        sa.Column("code", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("short_name", sa.Text(), nullable=False),
        sa.Column("division_type", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("code"),
        sa.UniqueConstraint("short_name"),
        comment="Tỉnh / thành phố sau sáp nhập 01/07/2025; short_name chính là events.city",
    )
    wards = op.create_table(
        "wards",
        sa.Column("code", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("province_code", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("division_type", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["province_code"], ["provinces.code"]),
        sa.PrimaryKeyConstraint("code"),
        sa.UniqueConstraint("province_code", "code", name="uq_wards_province_code"),
        comment="Phường / xã / đặc khu sau sáp nhập 01/07/2025, thuộc một tỉnh",
    )
    op.create_index("ix_wards_province_name", "wards", ["province_code", "name"])

    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["provinces"]
    op.bulk_insert(provinces, [{k: p[k] for k in ("code", "name", "short_name", "division_type")} for p in data])
    op.bulk_insert(wards, [{"code": w["code"], "province_code": p["code"], "name": w["name"],
                            "division_type": w["division_type"]} for p in data for w in p["wards"]])

    op.add_column("events", sa.Column("province_code", sa.SmallInteger(), nullable=True))
    op.add_column("events", sa.Column("ward_code", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("street", sa.Text(), nullable=True))
    op.create_foreign_key("fk_events_province", "events", "provinces", ["province_code"], ["code"])
    op.create_foreign_key("fk_events_ward", "events", "wards", ["province_code", "ward_code"], ["province_code", "code"])
    op.create_check_constraint("ck_events_ward_needs_province", "events", "ward_code IS NULL OR province_code IS NOT NULL")
    op.add_column("organizers", sa.Column("logo_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizers", "logo_url")
    op.drop_constraint("ck_events_ward_needs_province", "events", type_="check")
    op.drop_constraint("fk_events_ward", "events", type_="foreignkey")
    op.drop_constraint("fk_events_province", "events", type_="foreignkey")
    for col in ("street", "ward_code", "province_code"):
        op.drop_column("events", col)
    op.drop_index("ix_wards_province_name", table_name="wards")
    op.drop_table("wards")
    op.drop_table("provinces")
