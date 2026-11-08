"""API đọc danh mục: sự kiện, suất, hạng vé, sơ đồ, trang chủ, vé còn lại
Router chỉ khai báo đường dẫn + quyền; xử lý nằm ở app/controllers/catalog_controller.py"""
from typing import Literal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.schemas.catalog import Availability, CategoryList, CouponOut, EventDetail, EventList, HomeOut
from app.controllers import catalog_controller as ctrl

router = APIRouter(tags=["Danh mục"])


@router.get("/categories", response_model=CategoryList, response_model_by_alias=True)
def categories(db: Session = Depends(get_db)) -> CategoryList:
    return ctrl.categories(db)


@router.get("/coupons/{code}", response_model=CouponOut, response_model_by_alias=True)
def coupon(code: str, db: Session = Depends(get_db)) -> CouponOut:
    return ctrl.coupon(code, db)


@router.get("/events", response_model=EventList, response_model_by_alias=True)
def event_list(
    q: str | None = Query(None, max_length=100, description="Tìm không dấu theo tên, thành phố, địa điểm, thể loại"),
    category: str | None = None,
    city: str | None = None,
    organizer: bool = Query(False, description="Chỉ sự kiện do Ban tổ chức tạo"),
    sort: Literal["start", "reviewed"] = "start",
    limit: int = Query(60, ge=1, le=200),
    db: Session = Depends(get_db),
) -> EventList:
    return ctrl.event_list(q, category, city, organizer, sort, limit, db)


@router.get("/events/{slug}/availability", response_model=Availability, response_model_by_alias=True,
            response_model_exclude_none=True)
def event_availability(slug: str, show: str | None = None, db: Session = Depends(get_db)) -> Availability:
    return ctrl.event_availability(slug, show, db)


@router.get("/events/{slug}", response_model=EventDetail, response_model_by_alias=True)
def event_detail(slug: str, db: Session = Depends(get_db)) -> EventDetail:
    return ctrl.event_detail(slug, db)


@router.get("/home", response_model=HomeOut, response_model_by_alias=True)
def home(db: Session = Depends(get_db)) -> HomeOut:
    return ctrl.home(db)


@router.get("/maps/{map_id}")
def venue_map(map_id: str, db: Session = Depends(get_db)) -> dict:
    return ctrl.venue_map(map_id, db)
