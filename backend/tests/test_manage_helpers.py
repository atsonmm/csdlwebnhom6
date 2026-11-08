"""Hàm dùng chung cho Ban tổ chức / Quản trị"""
import pytest
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.catalog import Category, Event
from app.models.sales import Order, TierStock
from app.services.manage import event_summaries, unique_slug
from app.utils.textnorm import search_text_for, slugify
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, make_customer

KEYS = {"id", "slug", "title", "category", "city", "venue", "date", "startTime", "status", "rejectReason", "orgName",
        "createdAt", "capacity", "minPrice", "sold", "revenue",
        "phase", "saleOpensAt", "reviewedAt", "cancelReason", "cancelledBy"}  # giai đoạn 7: trạng thái bán cho dashboard


@pytest.mark.parametrize("raw,slug", [
    ("Đêm Nhạc Mùa Đông 2026", "dem-nhac-mua-dong-2026"),
    ("  --Hà Nội!!  ", "ha-noi"),
    ("Nhạc kịch “Phố Đèn Lồng”", "nhac-kich-pho-den-long"),
    ("!!!", ""),
])
def test_slugify_matches_js(raw, slug):
    assert slugify(raw) == slug


def test_search_text_formula_matches_catalog_export(api, api_db):
    labels = dict(api_db.execute(select(Category.id, Category.label)).all())
    for ev in api_db.scalars(select(Event).where(Event.organizer_id.is_(None)).limit(5)):
        assert search_text_for(ev.title, ev.city, ev.venue, labels[ev.category_id]) == ev.search_text


def test_unique_slug_suffixes(api, api_db):
    taken = api_db.scalar(select(Event).where(Event.organizer_id.is_(None)))
    assert unique_slug(api_db, taken.title) == f"{taken.slug}-2"
    ev = make_org_event(api_db, slug=f"{taken.slug}-2")
    try:
        assert unique_slug(api_db, taken.title) == f"{taken.slug}-3"
    finally:
        drop_org_event(api_db, ev)
    assert unique_slug(api_db, "!!!") == "su-kien"
    assert unique_slug(api_db, "Tên mới hoàn toàn") == "ten-moi-hoan-toan"


def test_event_summaries_sales_and_shape(api, api_db, auth_db):
    ev = make_org_event(api_db, slug="btc-tong-hop", status="approved", starts_at=datetime(2026, 12, 20, 12, 30, tzinfo=timezone.utc))
    try:
        api_db.add(TierStock(event_id=ev.id, show_id="20261220-1930", tier_id="ve-1", capacity=50, presold=0, sold=0))
        api_db.commit()
        buyer = make_customer(api_db, "mua@x.vn")
        insert_order(api_db, buyer, "btc-tong-hop", "20261220-1930", [("ve-1", 2)])
        insert_order(api_db, buyer, "btc-tong-hop", "20261220-1930", [("ve-1", 1)])
        refunded = insert_order(api_db, buyer, "btc-tong-hop", "20261220-1930", [("ve-1", 5)])
        refunded.status = "refunded"
        api_db.commit()
        s = event_summaries(api_db, [ev])[0]
        assert set(s) == KEYS
        assert s["slug"] == "btc-tong-hop" and s["status"] == "approved" and s["rejectReason"] is None
        assert s["date"] == "2026-12-20" and s["startTime"] == "19:30"
        assert s["orgName"] == "Đơn vị btc-tong-hop" and s["capacity"] == 50 and s["minPrice"] == 200000
        # "đã bán" = sức chứa − còn lại (kho chung): vé của đơn hoàn không quay lại kho; doanh thu chỉ đơn đã thanh toán
        assert s["sold"] == 8 and s["revenue"] == 3 * 200000
        assert s["createdAt"].endswith("+07:00")
    finally:
        api_db.rollback()
        api_db.execute(Order.__table__.delete().where(Order.event_id == ev.id))
        api_db.commit()
        drop_org_event(api_db, ev)
