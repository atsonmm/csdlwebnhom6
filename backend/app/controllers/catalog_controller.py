"""Controller — xử lý request/response cho routers/catalog.py: API đọc danh mục: sự kiện, suất, hạng vé, sơ đồ, trang chủ, vé còn lại"""
from typing import Literal
from sqlalchemy.orm import Session
from app.middlewares.errors import not_found
from app.schemas.catalog import Availability, CategoryList, CouponOut, EventDetail, EventList, HomeOut
from app.services import catalog as svc


def categories(db: Session) -> CategoryList:
    # GET /categories
    return CategoryList(categories=svc.list_categories(db))


def coupon(code: str, db: Session) -> CouponOut:
    # GET /coupons/{code}
    found = svc.get_coupon(db, code)
    if found is None:
        raise not_found("Mã giảm giá không hợp lệ")
    return found


def event_list(q: str | None, category: str | None, city: str | None, organizer: bool, sort: Literal["start", "reviewed"], limit: int, db: Session) -> EventList:
    # GET /events
    return EventList(events=svc.list_events(db, q=q, category=category, city=city, organizer=organizer,
                                            sort=sort, limit=limit))


def event_availability(slug: str, show: str | None, db: Session) -> Availability:
    # GET /events/{slug}/availability
    try:
        return svc.availability(db, slug, show)
    except svc.EventNotFound:
        raise not_found("Sự kiện không tồn tại") from None
    except svc.ShowNotFound:
        raise not_found("Suất diễn không tồn tại") from None


def event_detail(slug: str, db: Session) -> EventDetail:
    # GET /events/{slug}
    found = svc.get_event_detail(db, slug)
    if found is None:
        raise not_found("Sự kiện không tồn tại")
    return found


def home(db: Session) -> HomeOut:
    # GET /home
    return HomeOut(sections=svc.home_sections(db))


def venue_map(map_id: str, db: Session) -> dict:
    # GET /maps/{map_id}
    found = svc.get_map(db, map_id)
    if found is None:
        raise not_found("Sơ đồ không tồn tại")
    return found
