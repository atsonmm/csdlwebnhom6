"""Task B1 — GET /api/organizer/reports: doanh thu theo ngày/tuần/tháng, theo sự kiện, theo hạng vé"""
from datetime import date, datetime, time, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models.catalog import TicketTier
from app.models.sales import TierStock
from app.services.manage import fee_of
from app.utils.timefmt import VN
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import insert_order, make_customer

REPORTS = "/api/organizer/reports"
TODAY = datetime.now(VN).date()


def at(day: date, hh: int = 10) -> datetime:
    return datetime.combine(day, time(hh, 0), tzinfo=VN)


@pytest.fixture
def books(c, logged_organizer, api_db, auth_db):
    reviewed = datetime.now(timezone.utc) - timedelta(days=60)
    a = make_org_event(api_db, slug="bao-cao-a", organizer_id=logged_organizer.id, reviewed_at=reviewed)
    b = make_org_event(api_db, slug="bao-cao-b", organizer_id=logged_organizer.id, reviewed_at=reviewed)
    other = make_org_event(api_db, slug="bao-cao-btc-khac", reviewed_at=reviewed)
    api_db.add(TicketTier(event_id=a.id, id="ve-2", name="VIP", price=500000, capacity=20, max_per_order=10, sort_order=2))
    api_db.add_all([TierStock(event_id=a.id, show_id=a._test_show_id, tier_id="ve-1", capacity=50, presold=5, sold=0),
                    TierStock(event_id=a.id, show_id=a._test_show_id, tier_id="ve-2", capacity=20, presold=0, sold=0)])
    api_db.commit()
    buyer = make_customer(api_db, "mua-bao-cao@x.vn")

    def order(ev, items, day, status="paid", discount=0):
        o = insert_order(api_db, buyer, ev.slug, ev._test_show_id, items, created_at=at(day))
        o.status, o.discount, o.total = status, discount, o.subtotal - discount
        api_db.commit()
        return o

    yield SimpleNamespace(a=a, b=b, other=other, order=order)
    drop_event(api_db, a)
    drop_event(api_db, b)
    drop_org_event(api_db, other)


def get(c, **params):
    r = c.get(REPORTS, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_totals_match_orders_in_range(c, books):
    d = TODAY - timedelta(days=3)
    o1 = books.order(books.a, [("ve-1", 2)], d, discount=50000)       # 400k − 50k
    o2 = books.order(books.b, [("ve-1", 1)], d)                       # 200k
    books.order(books.a, [("ve-1", 1)], TODAY - timedelta(days=40))   # ngoài khoảng 30 ngày
    books.order(books.other, [("ve-1", 3)], d)                        # BTC khác
    body = get(c)
    assert body["range"] == {"from": (TODAY - timedelta(days=29)).isoformat(), "to": TODAY.isoformat(), "groupBy": "day"}
    t = body["totals"]
    revenue = o1.total + o2.total
    fee = fee_of(o1.total) + fee_of(o2.total)  # phí tính theo từng sự kiện rồi cộng
    assert t == {"gross": 600000, "discount": 50000, "revenue": revenue, "fee": fee, "net": revenue - fee,
                 "orders": 2, "tickets": 3, "refundedOrders": 0, "refundedAmount": 0}


def test_series_continuous_day_week_month(c, books):
    d0 = TODAY - timedelta(days=6)
    books.order(books.a, [("ve-1", 1)], d0)
    books.order(books.a, [("ve-1", 2)], TODAY)
    s = get(c, **{"from": d0.isoformat(), "to": TODAY.isoformat()})["series"]
    assert [x["key"] for x in s] == [(d0 + timedelta(days=i)).isoformat() for i in range(7)]
    assert s[0]["label"] == d0.strftime("%d/%m") and s[0] == s[0] | {"revenue": 200000, "tickets": 1, "orders": 1}
    assert s[-1]["tickets"] == 2 and all(x["revenue"] == 0 for x in s[1:-1])

    month = get(c, **{"from": "2026-10-01", "to": "2026-11-30", "groupBy": "month"})["series"]
    assert [(x["key"], x["label"]) for x in month] == [("2026-10", "10/2026"), ("2026-11", "11/2026")]

    week = get(c, **{"from": "2026-11-04", "to": "2026-11-17", "groupBy": "week"})["series"]  # thứ Tư → thứ Ba
    assert [(x["key"], x["label"]) for x in week] == [("2026-11-02", "T 02/11"), ("2026-11-09", "T 09/11"),
                                                      ("2026-11-16", "T 16/11")]


def test_by_event_and_tier(c, books, api_db):
    d = TODAY - timedelta(days=1)
    books.order(books.a, [("ve-1", 2), ("ve-2", 1)], d)  # 900k
    books.order(books.b, [("ve-1", 1)], d)               # 200k
    body = get(c)
    assert [(e["eventId"], e["revenue"], e["tickets"], e["orders"]) for e in body["byEvent"]] == [
        (books.a.id, 900000, 3, 1), (books.b.id, 200000, 1, 1)]
    ea = body["byEvent"][0]
    assert ea["title"] == books.a.title and ea["fee"] == fee_of(900000) and ea["net"] == 900000 - fee_of(900000)
    tiers = {(t["eventId"], t["tierId"]): t for t in body["byTier"]}
    vip = tiers[(books.a.id, "ve-2")]
    assert vip == {"eventId": books.a.id, "eventTitle": books.a.title, "tierId": "ve-2", "tierName": "VIP",
                   "price": 500000, "capacity": 20, "sold": 1, "revenue": 500000,
                   "revenueShare": 55.6, "fillRate": 5.0}  # G3: Q5 tỉ trọng doanh thu + lấp đầy
    assert tiers[(books.a.id, "ve-1")]["capacity"] == 50 and tiers[(books.a.id, "ve-1")]["sold"] == 2
    only_a = get(c, eventId=books.a.id)
    assert [e["eventId"] for e in only_a["byEvent"]] == [books.a.id]
    assert {t["tierId"] for t in only_a["byTier"]} == {"ve-1", "ve-2"}


def test_event_filter_lists_unsold_tiers(c, books):
    body = get(c, eventId=books.a.id)
    assert {t["tierId"]: t["sold"] for t in body["byTier"]} == {"ve-1": 0, "ve-2": 0}
    assert body["byEvent"] == [] and body["totals"]["revenue"] == 0


def test_refunded_counted_separately(c, books):
    d = TODAY - timedelta(days=2)
    books.order(books.a, [("ve-1", 1)], d)
    r = books.order(books.a, [("ve-1", 3)], d, status="refunded")
    books.order(books.a, [("ve-1", 1)], d, status="cancelled")
    t = get(c)["totals"]
    assert t["revenue"] == 200000 and t["orders"] == 1
    assert t["refundedOrders"] == 1 and t["refundedAmount"] == r.total


def test_event_filter_other_org_404(c, books):
    r = c.get(REPORTS, params={"eventId": books.other.id})
    assert r.status_code == 404 and r.json() == {"error": "Sự kiện không tồn tại"}


def test_range_too_long_400(c, logged_organizer):
    r = c.get(REPORTS, params={"from": "2025-01-01", "to": "2026-01-02"})
    assert r.status_code == 400 and r.json() == {"error": "Khoảng báo cáo tối đa 366 ngày"}
    assert c.get(REPORTS, params={"from": "2025-01-01", "to": "2026-01-01"}).status_code == 200  # đúng 366 ngày


@pytest.mark.parametrize("params,msg", [
    ({"groupBy": "year"}, "Kiểu gom nhóm không hợp lệ"),
    ({"from": "2026-02-30"}, "Ngày from không hợp lệ"),
    ({"from": "2026-11-08", "to": "2026-11-01"}, "Khoảng ngày không hợp lệ"),
    ({"eventId": "abc"}, "Mã sự kiện không hợp lệ"),
])
def test_bad_params_400(c, logged_organizer, params, msg):
    r = c.get(REPORTS, params=params)
    assert r.status_code == 400 and r.json() == {"error": msg}


def test_requires_organizer(c, logged_customer):
    assert c.get(REPORTS).status_code == 403
