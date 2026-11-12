"""resale: chợ vé bán lại thật (thay số giả events.resale_count + khối "resale" trên trang chủ)

- resale_listings / resale_listing_tickets (tin bán + từng vé trong tin; một vé chỉ ở một tin đang mở)
- orders.kind 'primary' | 'resale' (đơn cũ = primary) — doanh thu ban tổ chức chỉ tính primary
- tickets.transferred_at — vé đã bán lại, hết hiệu lực (người mua nhận vé mã mới)
- bỏ events.resale_count và vị trí trang chủ section 'resale'
Chạy trên CSDL có dữ liệu: mọi đơn cũ thành kind = 'primary', không vé nào bị đổi.
Hạ phiên bản: dừng nếu đã có tin bán lại / đơn bán lại (tránh mất dữ liệu âm thầm).

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_SECTIONS = ("hero", "featured-upcoming", "featured-new", "trending", "posters", "resale", "schedule-weekend",
                "schedule-month", "catalog")
NEW_SECTIONS = tuple(s for s in OLD_SECTIONS if s != "resale")


VIEWS = {  # 0002 → 0016: chỉ đơn mua từ ban tổ chức (kind = 'primary') là doanh thu
    "v_event_sales": """
SELECT o.event_id,
       o.show_id,
       i.tier_id,
       SUM(i.qty)::bigint           AS sold,
       SUM(i.price * i.qty)::bigint AS revenue
FROM order_items i
JOIN orders o ON o.id = i.order_id
WHERE o.status = 'paid'{kind}
GROUP BY o.event_id, o.show_id, i.tier_id
""",
    "v_daily_revenue": """
SELECT e.organizer_id,
       (o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date AS day,
       SUM(o.total)::bigint AS revenue,
       SUM((SELECT COALESCE(SUM(i.qty), 0) FROM order_items i WHERE i.order_id = o.id))::bigint AS tickets
FROM orders o
JOIN events e ON e.id = o.event_id
WHERE o.status = 'paid'{kind}
GROUP BY e.organizer_id, (o.created_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::date
""",
}


def _views(with_kind: bool) -> None:
    for name, body in VIEWS.items():
        op.execute(f"CREATE OR REPLACE VIEW {name} AS" + body.format(kind=" AND o.kind = 'primary'" if with_kind else ""))


def _section_check(sections) -> str:
    return "section IN (" + ",".join(f"'{s}'" for s in sections) + ")"


def upgrade() -> None:
    op.add_column("orders", sa.Column("kind", sa.String(10), nullable=False, server_default="primary"))
    op.create_check_constraint("ck_orders_kind", "orders", "kind IN ('primary','resale')")
    op.add_column("tickets", sa.Column("transferred_at", sa.DateTime(timezone=True), nullable=True))
    _views(with_kind=True)

    op.create_table(
        "resale_listings",
        sa.Column("id", sa.String(12), primary_key=True),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("show_id", sa.String(13), nullable=False),
        sa.Column("tier_id", sa.String(60), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("allow_partial", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(10), nullable=False, server_default="listed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id", "show_id"], ["shows.event_id", "shows.id"], name="fk_resale_listings_show", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id", "tier_id"], ["ticket_tiers.event_id", "ticket_tiers.id"],
                                name="fk_resale_listings_tier", ondelete="CASCADE"),
        sa.CheckConstraint("status IN ('listed','sold','cancelled')", name="ck_resale_listings_status"),
        sa.CheckConstraint("price > 0", name="ck_resale_listings_price"),
        sa.CheckConstraint("(status = 'listed') = (closed_at IS NULL)", name="ck_resale_listings_closed"),
        comment="Tin bán lại vé của khách: các vé cùng suất, cùng hạng; giá mỗi vé không cao hơn giá gốc",
    )
    op.create_index("ix_resale_listings_seller_id", "resale_listings", ["seller_id"])
    op.create_index("ix_resale_listings_browse", "resale_listings", ["event_id", "show_id", "status", "price"])

    op.create_table(
        "resale_listing_tickets",
        sa.Column("listing_id", sa.String(12), sa.ForeignKey("resale_listings.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("ticket_code", sa.String(20), sa.ForeignKey("tickets.code", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="listed"),
        sa.Column("buyer_order_id", sa.String(20), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("new_ticket_code", sa.String(20), sa.ForeignKey("tickets.code", ondelete="CASCADE"), nullable=True),
        sa.CheckConstraint("status IN ('listed','sold','cancelled')", name="ck_resale_listing_tickets_status"),
        sa.CheckConstraint("(status = 'sold') = (buyer_order_id IS NOT NULL AND new_ticket_code IS NOT NULL)",
                           name="ck_resale_listing_tickets_sold"),
        comment="Từng vé trong tin bán lại: đang bán / đã bán (đơn + vé mới của người mua) / đã gỡ",
    )
    op.create_index("uq_resale_ticket_listed", "resale_listing_tickets", ["ticket_code"], unique=True,
                    postgresql_where=sa.text("status = 'listed'"))

    op.execute("DELETE FROM home_slots WHERE section = 'resale'")
    op.drop_constraint("ck_home_slots_section", "home_slots", type_="check")
    op.create_check_constraint("ck_home_slots_section", "home_slots", _section_check(NEW_SECTIONS))
    op.drop_constraint("ck_events_resale", "events", type_="check")
    op.drop_column("events", "resale_count")


def downgrade() -> None:
    conn = op.get_bind()
    if conn.execute(sa.text("SELECT (SELECT count(*) FROM resale_listings) + "
                            "(SELECT count(*) FROM orders WHERE kind = 'resale')")).scalar():
        raise RuntimeError("Đã có tin / đơn bán lại — không hạ phiên bản để tránh mất dữ liệu")
    op.add_column("events", sa.Column("resale_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_check_constraint("ck_events_resale", "events", "resale_count >= 0")
    op.drop_constraint("ck_home_slots_section", "home_slots", type_="check")
    op.create_check_constraint("ck_home_slots_section", "home_slots", _section_check(OLD_SECTIONS))
    op.drop_index("uq_resale_ticket_listed", table_name="resale_listing_tickets")
    op.drop_table("resale_listing_tickets")
    op.drop_index("ix_resale_listings_browse", table_name="resale_listings")
    op.drop_index("ix_resale_listings_seller_id", table_name="resale_listings")
    op.drop_table("resale_listings")
    op.drop_column("tickets", "transferred_at")
    _views(with_kind=False)  # bỏ điều kiện kind trước khi xoá cột
    op.drop_constraint("ck_orders_kind", "orders", type_="check")
    op.drop_column("orders", "kind")
