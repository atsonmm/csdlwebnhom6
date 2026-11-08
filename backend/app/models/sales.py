"""Bán vé: mã giảm giá, kho vé theo suất, ghế đã giữ, đơn hàng, dòng đơn, vé"""
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
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_coupons_amount"),
        CheckConstraint("min_order >= 0", name="ck_coupons_min_order"),
    )

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    amount: Mapped[int] = mapped_column(Integer)
    min_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class TierStock(Base):
    """Kho vé theo suất + hạng (sự kiện bán theo loại vé hoặc theo khu)"""

    __tablename__ = "tier_stock"
    __table_args__ = (
        ForeignKeyConstraint(["event_id", "show_id"], ["shows.event_id", "shows.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["event_id", "tier_id"], ["ticket_tiers.event_id", "ticket_tiers.id"], ondelete="CASCADE"),
        CheckConstraint("presold >= 0 AND sold >= 0", name="ck_tier_stock_nonneg"),
        CheckConstraint("presold + sold <= capacity", name="ck_tier_stock_capacity"),
    )

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    show_id: Mapped[str] = mapped_column(String(13), primary_key=True)
    tier_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    capacity: Mapped[int] = mapped_column(Integer)
    presold: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sold: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class SeatHold(Base):
    """Ghế đã bán theo suất. order_id NULL = đã bán sẵn trước khi hệ thống chạy"""

    __tablename__ = "seat_holds"
    __table_args__ = (
        ForeignKeyConstraint(["event_id", "show_id"], ["shows.event_id", "shows.id"], ondelete="CASCADE"),
        # Ghế giữ cho một đơn phải cùng sự kiện với đơn đó
        ForeignKeyConstraint(["order_id", "event_id"], ["orders.id", "orders.event_id"], ondelete="CASCADE", name="fk_seat_holds_order_event"),
    )

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    show_id: Mapped[str] = mapped_column(String(13), primary_key=True)
    seat_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    order_id: Mapped[str | None] = mapped_column(String(20), index=True)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        ForeignKeyConstraint(["event_id", "show_id"], ["shows.event_id", "shows.id"]),
        CheckConstraint("method IN ('qr','wallet','card')", name="ck_orders_method"),
        CheckConstraint("status IN ('paid','refunded','cancelled')", name="ck_orders_status"),
        CheckConstraint("refunded_at IS NULL OR status = 'refunded'", name="ck_orders_refunded_at"),
        CheckConstraint("total = subtotal - discount AND discount >= 0 AND total >= 0", name="ck_orders_total"),
        Index("ix_orders_event_created", "event_id", "created_at"),
        # migration 0008: báo cáo doanh thu theo khoảng ngày + ô tìm sổ đơn (GIN trigram trên biểu thức gộp)
        Index("ix_orders_status_created", "status", "created_at", postgresql_include=["event_id", "total"]),
        Index("ix_orders_buyer_trgm",
              text("lower(id || ' ' || buyer_name || ' ' || buyer_email || ' ' || buyer_phone) gin_trgm_ops"),
              postgresql_using="gin"),
        UniqueConstraint("id", "event_id", name="uq_orders_id_event"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[int] = mapped_column(Integer)
    show_id: Mapped[str] = mapped_column(String(13))
    subtotal: Mapped[int] = mapped_column(Integer)
    discount: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    coupon_code: Mapped[str | None] = mapped_column(ForeignKey("coupons.code"))
    total: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(10))
    buyer_name: Mapped[str] = mapped_column(Text)
    buyer_email: Mapped[str] = mapped_column(String(254))
    buyer_phone: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(10), default="paid", server_default="paid")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # migration 0006


class OrderItem(Base):
    """Một dòng của đơn: hạng vé × số lượng, price = giá tại thời điểm mua"""

    __tablename__ = "order_items"
    __table_args__ = (
        ForeignKeyConstraint(["event_id", "tier_id"], ["ticket_tiers.event_id", "ticket_tiers.id"]),
        ForeignKeyConstraint(["order_id", "event_id"], ["orders.id", "orders.event_id"], ondelete="CASCADE", name="fk_order_items_order_event"),
        CheckConstraint("price >= 0", name="ck_order_items_price"),
        CheckConstraint("qty > 0", name="ck_order_items_qty"),
    )

    order_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    tier_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    event_id: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)


class Ticket(Base):
    """Mỗi vé một mã check-in riêng"""

    __tablename__ = "tickets"
    __table_args__ = (
        ForeignKeyConstraint(["event_id", "tier_id"], ["ticket_tiers.event_id", "ticket_tiers.id"]),
        ForeignKeyConstraint(["order_id", "event_id"], ["orders.id", "orders.event_id"], ondelete="CASCADE", name="fk_tickets_order_event"),
        CheckConstraint("price >= 0", name="ck_tickets_price"),
    )

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(20), index=True)
    event_id: Mapped[int] = mapped_column(Integer)
    tier_id: Mapped[str] = mapped_column(String(60))
    price: Mapped[int] = mapped_column(Integer)
    seat_id: Mapped[str | None] = mapped_column(String(30))
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
