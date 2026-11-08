"""Danh mục: thể loại, sơ đồ địa điểm, sự kiện, suất diễn, hạng vé, vị trí trên trang chủ"""
from datetime import datetime, time

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base

HOME_SECTIONS = (
    "hero",
    "featured-upcoming",
    "featured-new",
    "trending",
    "posters",
    "resale",
    "schedule-weekend",
    "schedule-month",
    "catalog",
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    dot: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class VenueMap(Base):
    __tablename__ = "venue_maps"
    __table_args__ = (CheckConstraint("kind IN ('zones','seats')", name="ck_venue_maps_kind"),)

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(Text)
    view_box: Mapped[str | None] = mapped_column(Text)
    decor: Mapped[dict] = mapped_column(JSONB, default=dict)


class MapGroup(Base):
    __tablename__ = "map_groups"
    __table_args__ = (CheckConstraint("max_per_order IS NULL OR max_per_order > 0", name="ck_map_groups_max"),)

    map_id: Mapped[str] = mapped_column(ForeignKey("venue_maps.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    color: Mapped[str] = mapped_column(Text)
    ink: Mapped[bool] = mapped_column(Boolean, default=False)
    max_per_order: Mapped[int | None] = mapped_column(Integer)
    perks: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # thứ tự vẽ / hiển thị


class MapZone(Base):
    __tablename__ = "map_zones"
    __table_args__ = (
        ForeignKeyConstraint(["map_id", "group_id"], ["map_groups.map_id", "map_groups.id"], ondelete="CASCADE"),
        CheckConstraint("capacity > 0", name="ck_map_zones_capacity"),
    )

    map_id: Mapped[str] = mapped_column(ForeignKey("venue_maps.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    group_id: Mapped[str] = mapped_column(String(60))
    capacity: Mapped[int] = mapped_column(Integer)
    shape: Mapped[dict] = mapped_column(JSONB)
    text: Mapped[list] = mapped_column(JSONB, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # thứ tự vẽ / hiển thị


class MapSeat(Base):
    __tablename__ = "map_seats"
    __table_args__ = (
        ForeignKeyConstraint(["map_id", "group_id"], ["map_groups.map_id", "map_groups.id"], ondelete="CASCADE"),
    )

    map_id: Mapped[str] = mapped_column(ForeignKey("venue_maps.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    section: Mapped[str] = mapped_column(String(20))
    row_label: Mapped[str] = mapped_column(String(10))
    num: Mapped[int] = mapped_column(Integer)
    group_id: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(Text)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # thứ tự vẽ / hiển thị


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("layout IN ('list','zones','seats')", name="ck_events_layout"),
        CheckConstraint("(layout = 'list') = (map_id IS NULL)", name="ck_events_layout_map"),
        CheckConstraint("status IN ('pending','approved','rejected','cancelled')", name="ck_events_status"),
        CheckConstraint("cancelled_by IN ('organizer','admin')", name="ck_events_cancelled_by"),
        CheckConstraint("(status = 'cancelled') = (cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL "
                        "AND cancel_reason IS NOT NULL)", name="ck_events_cancel_fields"),
        CheckConstraint("resale_count >= 0", name="ck_events_resale"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True)
    title: Mapped[str] = mapped_column(Text)
    search_text: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"))
    city: Mapped[str] = mapped_column(Text)
    venue: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(Text)
    layout: Mapped[str] = mapped_column(String(10), default="list")
    map_id: Mapped[str | None] = mapped_column(ForeignKey("venue_maps.id"))
    organizer_id: Mapped[int | None] = mapped_column(ForeignKey("organizers.user_id", ondelete="CASCADE"), index=True)
    host_name: Mapped[str | None] = mapped_column(Text)
    host_bio: Mapped[str | None] = mapped_column(Text)
    description: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    notes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    status: Mapped[str] = mapped_column(String(10), default="approved", server_default="approved")
    reject_reason: Mapped[str | None] = mapped_column(Text)
    sale_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resale_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Huỷ sự kiện (migration 0006): lý do hiện cho khách, thời điểm, ai huỷ (Ban tổ chức / sàn gỡ)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[str | None] = mapped_column(String(10))
    # false = đã bỏ khỏi danh mục nhưng còn đơn hàng tham chiếu → giữ lại, ngừng bán
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Show(Base):
    __tablename__ = "shows"

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(String(13), primary_key=True)  # YYYYMMDD-HHMM
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[time] = mapped_column(Time)
    # false = đã bỏ khỏi danh mục nhưng còn đơn hàng tham chiếu → giữ lại, ngừng bán
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class TicketTier(Base):
    __tablename__ = "ticket_tiers"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_ticket_tiers_price"),
        CheckConstraint("capacity >= 0", name="ck_ticket_tiers_capacity"),
        CheckConstraint("max_per_order > 0", name="ck_ticket_tiers_max"),
    )

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    max_per_order: Mapped[int] = mapped_column(Integer, default=6)
    perks: Mapped[str] = mapped_column(Text, default="")
    group_id: Mapped[str | None] = mapped_column(String(60))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # false = đã bỏ khỏi danh mục nhưng còn đơn hàng tham chiếu → giữ lại, ngừng bán
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class HomeSlot(Base):
    __tablename__ = "home_slots"
    __table_args__ = (
        CheckConstraint(
            "section IN (" + ",".join(f"'{s}'" for s in HOME_SECTIONS) + ")",
            name="ck_home_slots_section",
        ),
    )

    section: Mapped[str] = mapped_column(String(30), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
