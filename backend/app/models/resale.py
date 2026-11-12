"""Chợ vé bán lại (migration 0016): tin bán của khách + từng vé trong tin.
Một tin = các vé CÙNG suất, CÙNG hạng của một người bán; giá mỗi vé ≤ giá gốc (kiểm ở services/resale.py)."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ResaleListing(Base):
    __tablename__ = "resale_listings"
    __table_args__ = (
        ForeignKeyConstraint(["event_id", "show_id"], ["shows.event_id", "shows.id"], name="fk_resale_listings_show", ondelete="CASCADE"),
        ForeignKeyConstraint(["event_id", "tier_id"], ["ticket_tiers.event_id", "ticket_tiers.id"],
                             name="fk_resale_listings_tier", ondelete="CASCADE"),
        CheckConstraint("status IN ('listed','sold','cancelled')", name="ck_resale_listings_status"),
        CheckConstraint("price > 0", name="ck_resale_listings_price"),
        CheckConstraint("(status = 'listed') = (closed_at IS NULL)", name="ck_resale_listings_closed"),
        # trang "vé bán lại" của một sự kiện: lọc suất + trạng thái, sắp theo giá
        Index("ix_resale_listings_browse", "event_id", "show_id", "status", "price"),
    )

    id: Mapped[str] = mapped_column(String(12), primary_key=True)  # RSL + 9 chữ số
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[int] = mapped_column(Integer)
    show_id: Mapped[str] = mapped_column(String(13))
    tier_id: Mapped[str] = mapped_column(String(60))
    price: Mapped[int] = mapped_column(Integer)
    allow_partial: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    status: Mapped[str] = mapped_column(String(10), default="listed", server_default="listed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ResaleListingTicket(Base):
    __tablename__ = "resale_listing_tickets"
    __table_args__ = (
        CheckConstraint("status IN ('listed','sold','cancelled')", name="ck_resale_listing_tickets_status"),
        CheckConstraint("(status = 'sold') = (buyer_order_id IS NOT NULL AND new_ticket_code IS NOT NULL)",
                        name="ck_resale_listing_tickets_sold"),
        # một vé chỉ nằm trong MỘT tin đang mở — hai lần đăng bán cùng lúc: lần sau vướng index này
        Index("uq_resale_ticket_listed", "ticket_code", unique=True, postgresql_where=text("status = 'listed'")),
    )

    listing_id: Mapped[str] = mapped_column(ForeignKey("resale_listings.id", ondelete="CASCADE"), primary_key=True)
    ticket_code: Mapped[str] = mapped_column(ForeignKey("tickets.code", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(10), default="listed", server_default="listed")
    buyer_order_id: Mapped[str | None] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    new_ticket_code: Mapped[str | None] = mapped_column(ForeignKey("tickets.code", ondelete="CASCADE"))
