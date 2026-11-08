"""Task A3 — GET /api/admin/orders: sổ đơn toàn sàn (cùng tham số và JSON với /organizer/orders, thêm organizerId/orgName)
+ GET /api/admin/organizers (danh sách Ban tổ chức cho bộ lọc; B3 thêm số liệu)"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.catalog import Event, Show, TicketTier
from app.models.sales import Order, TierStock
from app.utils.timefmt import VN
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer

ADMIN_ORDERS = "/api/admin/orders"


@pytest.fixture
def floor(c, logged_organizer, api_db, auth_db):
    """BTC đang đăng nhập (mine) + BTC khác (other) + một sự kiện sàn tự bán (catalog), mỗi bên 1 đơn"""
    reviewed = datetime.now(timezone.utc) - timedelta(days=3)
    mine = make_org_event(api_db, slug="so-san-cua-toi", organizer_id=logged_organizer.id, reviewed_at=reviewed)
    other = make_org_event(api_db, slug="so-san-btc-khac", reviewed_at=reviewed)
    platform = api_db.scalar(select(Event).where(Event.organizer_id.is_(None), Event.layout == "list",
                                                 Event.status == "approved").order_by(Event.id))
    p_show = api_db.scalar(select(Show.id).where(Show.event_id == platform.id, Show.active).order_by(Show.starts_at))
    buyer = make_customer(api_db, "mua-toan-san@x.vn")
    tier = api_db.scalar(select(TicketTier.id).where(TicketTier.event_id == platform.id, TicketTier.active)
                         .order_by(TicketTier.sort_order))
    o_mine = insert_order(api_db, buyer, mine.slug, mine._test_show_id, [("ve-1", 1)])
    o_other = insert_order(api_db, buyer, other.slug, other._test_show_id, [("ve-1", 2)])
    o_platform = insert_order(api_db, buyer, platform.slug, p_show, [(tier, 1)],
                              created_at=datetime.now(VN) + timedelta(seconds=1))
    admin = make_customer(api_db, "quantri-so@x.vn")
    admin.role = "admin"
    api_db.commit()
    yield {"mine": mine, "other": other, "org": logged_organizer, "o_mine": o_mine, "o_other": o_other,
           "o_platform": o_platform, "admin_email": admin.email}
    api_db.rollback()
    api_db.execute(Order.__table__.delete().where(Order.id == o_platform.id))
    api_db.execute(update(TierStock).where(TierStock.event_id == platform.id, TierStock.show_id == p_show,
                                           TierStock.tier_id == tier).values(sold=TierStock.sold - 1))
    api_db.commit()
    drop_event(api_db, mine)
    drop_org_event(api_db, other)


def as_admin(c, floor):
    login(c, floor["admin_email"])


def test_admin_sees_all_orgs_and_platform_orders(c, floor):
    as_admin(c, floor)
    body = c.get(ADMIN_ORDERS, params={"pageSize": 100}).json()
    got = {o["id"]: o for o in body["orders"]}
    assert {floor["o_mine"].id, floor["o_other"].id, floor["o_platform"].id} <= set(got)
    assert got[floor["o_mine"].id]["orgName"] == "Công ty Sự kiện Thử"
    assert got[floor["o_other"].id]["orgName"] == "Đơn vị so-san-btc-khac"
    assert got[floor["o_platform"].id]["orgName"] is None  # sàn tự bán


def test_filter_by_organizer(c, floor):
    as_admin(c, floor)
    ids = [o["id"] for o in c.get(ADMIN_ORDERS, params={"organizerId": floor["other"].organizer_id}).json()["orders"]]
    assert ids == [floor["o_other"].id]


def test_same_filters_as_organizer(c, floor):
    params = {"status": "paid", "pageSize": 50}
    own = c.get("/api/organizer/orders", params=params).json()  # c đang là BTC
    as_admin(c, floor)
    adm = c.get(ADMIN_ORDERS, params=params | {"organizerId": floor["org"].id}).json()
    strip = lambda b: [{k: v for k, v in o.items() if k != "orgName"} for o in b["orders"]]  # noqa: E731
    assert strip(adm) == strip(own) and adm["summary"] == own["summary"] and adm["total"] == own["total"]


@pytest.mark.parametrize("bad", ["abc", "-1", "99999999999"])
def test_bad_organizer_id_400(c, floor, bad):
    as_admin(c, floor)
    r = c.get(ADMIN_ORDERS, params={"organizerId": bad})
    assert r.status_code == 400 and r.json() == {"error": "Mã ban tổ chức không hợp lệ"}


def test_requires_admin(c, logged_organizer):
    assert c.get(ADMIN_ORDERS).status_code == 403
    assert c.get("/api/admin/organizers").status_code == 403


def test_organizers_list_for_filter(c, floor):
    as_admin(c, floor)
    rows = {o["userId"]: o for o in c.get("/api/admin/organizers").json()["organizers"]}
    me = rows[floor["org"].id]
    assert me["orgName"] == "Công ty Sự kiện Thử" and me["code"] == f"ORG-{floor['org'].id:05d}"
    assert me["email"] == "btc@x.vn" and me["createdAt"].endswith("+07:00")
    assert floor["other"].organizer_id in rows
