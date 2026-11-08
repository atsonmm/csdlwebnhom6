"""Task A1 — GET /api/organizer/orders: sổ đơn của Ban tổ chức (lọc, tìm, phân trang, tổng hợp)"""
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import update

from app.models.sales import Ticket
from app.utils.timefmt import VN
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import insert_order, make_customer

ORDERS = "/api/organizer/orders"
KEYS = {"id", "createdAt", "eventId", "eventTitle", "showId", "startsAt", "buyerName", "buyerEmail", "buyerPhone",
        "items", "tickets", "checkedIn", "subtotal", "discount", "total", "method", "status", "refundedAt"}
TODAY = datetime.now(VN).date()
D1, D2 = TODAY - timedelta(days=2), TODAY - timedelta(days=1)


def at(day, hh=10) -> datetime:
    return datetime.combine(day, time(hh, 0), tzinfo=VN)


@pytest.fixture
def shop(c, logged_organizer, api_db, auth_db):
    reviewed = datetime.now(timezone.utc) - timedelta(days=5)
    mine = make_org_event(api_db, slug="so-don-cua-toi", organizer_id=logged_organizer.id, reviewed_at=reviewed)
    mine2 = make_org_event(api_db, slug="so-don-cua-toi-2", organizer_id=logged_organizer.id, reviewed_at=reviewed)
    other = make_org_event(api_db, slug="so-don-btc-khac", reviewed_at=reviewed)
    buyer = make_customer(api_db, "nguoi-mua-sodon@x.vn")

    def order(ev, qty=1, created=None, status="paid", name="Người nhận", email="nhan@x.vn", phone="0912345678"):
        o = insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", qty)], created_at=created or at(D1))
        o.status, o.buyer_name, o.buyer_email, o.buyer_phone = status, name, email, phone
        api_db.commit()
        return o

    yield SimpleNamespace(mine=mine, mine2=mine2, other=other, order=order)
    drop_event(api_db, mine)
    drop_event(api_db, mine2)
    drop_org_event(api_db, other)


def ids(r) -> list[str]:
    assert r.status_code == 200, r.text
    return [o["id"] for o in r.json()["orders"]]


def test_lists_only_own_orders_newest_first(c, shop, api_db):
    o1 = shop.order(shop.mine, qty=2, created=at(D1))
    o2 = shop.order(shop.mine2, created=at(D2))
    shop.order(shop.other, created=at(D2, 11))
    api_db.execute(update(Ticket).where(Ticket.order_id == o1.id).values(checked_in_at=datetime.now(timezone.utc)))
    api_db.commit()
    body = c.get(ORDERS).json()
    assert body["total"] == 2 and [o["id"] for o in body["orders"]] == [o2.id, o1.id]
    first = body["orders"][1]
    assert set(first) == KEYS
    assert first["eventId"] == shop.mine.id and first["eventTitle"] == shop.mine.title
    assert first["showId"] == shop.mine._test_show_id and first["startsAt"].endswith("+07:00")
    assert first["items"] == "Vé thường ×2" and first["tickets"] == 2 and first["checkedIn"] == 2
    assert first["total"] == 400000 and first["subtotal"] == 400000 and first["discount"] == 0
    assert first["method"] == "qr" and first["status"] == "paid" and first["refundedAt"] is None
    assert first["createdAt"].startswith(D1.isoformat())


def test_filter_status_event_and_date_range(c, shop):
    o1 = shop.order(shop.mine, created=at(D1))
    o2 = shop.order(shop.mine2, created=at(D2), status="refunded")
    assert ids(c.get(ORDERS, params={"status": "refunded"})) == [o2.id]
    assert ids(c.get(ORDERS, params={"status": "paid"})) == [o1.id]
    assert ids(c.get(ORDERS, params={"eventId": shop.mine.id})) == [o1.id]
    assert c.get(ORDERS, params={"eventId": shop.other.id}).json()["total"] == 0
    assert ids(c.get(ORDERS, params={"from": D1.isoformat(), "to": D1.isoformat()})) == [o1.id]
    assert ids(c.get(ORDERS, params={"from": D2.isoformat()})) == [o2.id]
    assert ids(c.get(ORDERS, params={"to": D1.isoformat()})) == [o1.id]


def test_date_filter_uses_vietnam_day(c, shop):
    # 23:30 giờ VN ngày D1 = 16:30 UTC ngày D1; 00:30 VN ngày D2 = 17:30 UTC ngày D1
    late = shop.order(shop.mine, created=datetime.combine(D1, time(23, 30), tzinfo=VN))
    early = shop.order(shop.mine, created=datetime.combine(D2, time(0, 30), tzinfo=VN))
    assert ids(c.get(ORDERS, params={"from": D1.isoformat(), "to": D1.isoformat()})) == [late.id]
    assert ids(c.get(ORDERS, params={"from": D2.isoformat(), "to": D2.isoformat()})) == [early.id]


def test_search_by_order_id_name_email_phone(c, shop):
    o1 = shop.order(shop.mine, name="Trần Thị Mai", email="mai.tran@x.vn", phone="0987000111")
    o2 = shop.order(shop.mine2, name="Lê Văn Hùng", email="hung.le@x.vn", phone="0911222333")
    assert ids(c.get(ORDERS, params={"q": o1.id.lower()})) == [o1.id]
    assert ids(c.get(ORDERS, params={"q": "thị mai"})) == [o1.id]
    assert ids(c.get(ORDERS, params={"q": "HUNG.LE"})) == [o2.id]
    assert ids(c.get(ORDERS, params={"q": "0911222"})) == [o2.id]
    assert sorted(ids(c.get(ORDERS, params={"q": "tn"}))) == sorted([o1.id, o2.id])
    assert ids(c.get(ORDERS, params={"q": o1.id[2:]})) == []  # mã đơn: khớp từ đầu, không phải "chứa"


@pytest.mark.parametrize("q", ["%", "_", "'", "\\", "a" * 500])
def test_search_special_chars_no_500(c, shop, q):
    shop.order(shop.mine)
    r = c.get(ORDERS, params={"q": q})
    assert r.status_code == 200 and r.json()["total"] == 0


def test_pagination_and_summary(c, shop):
    a = shop.order(shop.mine, qty=1, created=at(D1, 9))
    b = shop.order(shop.mine, qty=2, created=at(D1, 10))
    d = shop.order(shop.mine2, qty=3, created=at(D1, 11))
    refunded = shop.order(shop.mine2, qty=4, created=at(D1, 12), status="refunded")
    body = c.get(ORDERS, params={"pageSize": 2, "page": 2}).json()
    assert body["page"] == 2 and body["pageSize"] == 2 and body["total"] == 4
    assert [o["id"] for o in body["orders"]] == [b.id, a.id]
    assert body["summary"] == {"paidOrders": 3, "paidRevenue": a.total + b.total + d.total, "tickets": 6}
    assert refunded.total > 0
    defaults = c.get(ORDERS).json()
    assert defaults["page"] == 1 and defaults["pageSize"] == 20


@pytest.mark.parametrize("params,msg", [
    ({"status": "x"}, "Trạng thái đơn không hợp lệ"),
    ({"from": "2026-13-01"}, "Ngày from không hợp lệ"),
    ({"to": "07/11/2026"}, "Ngày to không hợp lệ"),
    ({"from": "2026-11-08", "to": "2026-11-01"}, "Khoảng ngày không hợp lệ"),
    ({"pageSize": 0}, "Kích thước trang không hợp lệ"),
    ({"pageSize": 101}, "Kích thước trang không hợp lệ"),
    ({"page": 0}, "Số trang không hợp lệ"),
    ({"page": "abc"}, "Số trang không hợp lệ"),
    ({"eventId": "abc"}, "Mã sự kiện không hợp lệ"),
    ({"eventId": "99999999999"}, "Mã sự kiện không hợp lệ"),
])
def test_bad_params_400(c, logged_organizer, params, msg):
    r = c.get(ORDERS, params=params)
    assert r.status_code == 400 and r.json() == {"error": msg}


def test_requires_organizer(c, logged_customer):
    assert c.get(ORDERS).status_code == 403


def test_requires_login(api):
    api.cookies.clear()
    assert api.get(ORDERS).status_code == 401
