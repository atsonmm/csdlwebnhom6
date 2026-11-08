"""Tiện ích cho test API: tạo sự kiện của Ban tổ chức trong CSDL test đã nạp"""
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.catalog import Event, Show, TicketTier
from app.models.users import Organizer, User


def default_starts_at() -> datetime:
    """19:30 giờ VN, 30 ngày sau hôm nay — test không bị "hết hạn" theo lịch"""
    from app.utils.timefmt import VN

    day = (datetime.now(VN) + timedelta(days=30)).date()
    return datetime.combine(day, time(19, 30), tzinfo=VN)


def org_show_id(ev: Event, db: Session | None = None) -> str:
    """Mã suất duy nhất của sự kiện tạo bằng make_org_event"""
    return ev._test_show_id


def make_org_event(db: Session, *, slug: str, status: str = "approved", org_description: str | None = None,
                   reviewed_at: datetime | None = None, title: str | None = None,
                   starts_at: datetime | None = None, organizer_id: int | None = None) -> Event:
    """User + Ban tổ chức + 1 sự kiện (1 suất, 1 hạng vé). Xoá bằng drop_org_event(db, ev).
    starts_at mặc định: 19:30 VN, 30 ngày sau hôm nay.
    organizer_id: gắn vào Ban tổ chức có sẵn (không tạo user mới) — xoá bằng drop_event(db, ev)."""
    if organizer_id is None:
        u = User(name="BTC thử", email=f"{slug}@btc.vn", password_hash="h", role="organizer")
        db.add(u)
        db.flush()
        db.add(Organizer(user_id=u.id, org_name=f"Đơn vị {slug}", phone="0912345678", description=org_description))
        db.flush()
        organizer_id = u.id
    ev = Event(slug=slug, title=title or f"Sự kiện {slug}", search_text=slug.replace("-", " "), category_id="nhac-song",
               city="Hà Nội", venue="Nhà hát Lớn", address="1 Tràng Tiền", layout="list", description=["Giới thiệu"],
               notes=[], status=status, organizer_id=organizer_id, reviewed_at=reviewed_at)
    db.add(ev)
    db.flush()
    from app.utils.timefmt import VN

    starts = starts_at or default_starts_at()
    local = starts.astimezone(VN)
    show_id = local.strftime("%Y%m%d-%H%M")
    db.add_all([Show(event_id=ev.id, id=show_id, starts_at=starts, end_time=time(22, 0)),
                TicketTier(event_id=ev.id, id="ve-1", name="Vé thường", price=200000, capacity=50, max_per_order=10)])
    db.commit()
    ev._test_show_id = show_id
    return ev


def drop_event(db: Session, ev: Event) -> None:
    """Xoá một sự kiện (và đơn của nó) nhưng giữ Ban tổ chức"""
    from app.models.sales import Order

    db.rollback()
    db.execute(delete(Order).where(Order.event_id == ev.id))
    db.execute(delete(Event).where(Event.id == ev.id))
    db.commit()


def drop_org_event(db: Session, ev: Event) -> None:
    from app.models.sales import Order

    db.rollback()
    # Đơn tham chiếu suất diễn (FK không cascade — cố ý) nên xoá đơn trước
    db.execute(delete(Order).where(Order.event_id == ev.id))
    db.execute(delete(User).where(User.id == ev.organizer_id))
    db.commit()
