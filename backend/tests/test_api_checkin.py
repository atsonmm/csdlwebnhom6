"""Task C1 — POST /api/organizer/checkin: soát vé tại cổng"""
from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.catalog import Event, MapGroup, MapSeat, TicketTier, VenueMap
from app.models.sales import Ticket
from app.services.checkin import normalize_code
from app.utils.timefmt import VN
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer

CHECKIN = "/api/organizer/checkin"


@pytest.mark.parametrize("raw,code", [
    ("K7QF-29XM", "K7QF-29XM"),
    ("k7qf-29xm", "K7QF-29XM"),
    ("K7QF29XM", "K7QF-29XM"),
    ("  k7qf 29xm ", "K7QF-29XM"),
    ("K7QF-29X", None),
    ("K7QF-29XM1", None),
    ("K7Q!-29XM", None),
    ("", None),
    (None, None),
    (12345678, None),
])
def test_normalize_code(raw, code):
    assert normalize_code(raw) == code


@pytest.fixture
def gate(c, logged_organizer, api_db, auth_db):
    reviewed = datetime.now(timezone.utc) - timedelta(days=3)
    mine = make_org_event(api_db, slug="soat-ve-cua-toi", organizer_id=logged_organizer.id, reviewed_at=reviewed)
    other = make_org_event(api_db, slug="soat-ve-btc-khac", reviewed_at=reviewed)
    buyer = make_customer(api_db, "khach-soat@x.vn")

    def order(ev, qty=1, status="paid"):
        o = insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", qty)])
        o.status, o.buyer_name = status, "Trần Khách"
        api_db.commit()
        return o, api_db.scalars(select(Ticket.code).where(Ticket.order_id == o.id).order_by(Ticket.code)).all()

    yield {"mine": mine, "other": other, "order": order, "buyer": buyer}
    drop_event(api_db, mine)
    drop_org_event(api_db, other)


def test_checkin_ok_then_already_keeps_first_time(c, gate):
    o, codes = gate["order"](gate["mine"])
    r1 = c.post(CHECKIN, json={"code": codes[0].lower().replace("-", "")})
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1["result"] == "checked-in"
    t = b1["ticket"]
    assert t["code"] == codes[0] and t["orderId"] == o.id and t["eventId"] == gate["mine"].id
    assert t["eventTitle"] == gate["mine"].title and t["showId"] == gate["mine"]._test_show_id
    assert t["tierName"] == "Vé thường" and t["seat"] is None and t["buyerName"] == "Trần Khách"
    assert t["startsAt"].endswith("+07:00") and t["checkedInAt"].endswith("+07:00")
    r2 = c.post(CHECKIN, json={"code": codes[0]})
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["result"] == "already" and b2["ticket"]["checkedInAt"] == t["checkedInAt"]


def test_other_org_ticket_404(c, gate):
    _, codes = gate["order"](gate["other"])
    r = c.post(CHECKIN, json={"code": codes[0]})
    assert r.status_code == 404 and r.json() == {"error": "Không tìm thấy vé"}
    assert c.post(CHECKIN, json={"code": "ZZZZ-ZZZZ"}).json() == {"error": "Không tìm thấy vé"}


@pytest.mark.parametrize("status", ["refunded", "cancelled"])
def test_refunded_order_409(c, gate, api_db, status):
    _, codes = gate["order"](gate["mine"], status=status)
    r = c.post(CHECKIN, json={"code": codes[0]})
    assert r.status_code == 409 and r.json() == {"error": "Vé thuộc đơn đã hoàn tiền hoặc đã huỷ"}
    assert api_db.scalar(select(Ticket.checked_in_at).where(Ticket.code == codes[0])) is None


@pytest.mark.parametrize("body", [{"code": "abc"}, {"code": 123}, {}, {"code": ["K7QF-29XM"]}])
def test_bad_code_400(c, logged_organizer, body):
    r = c.post(CHECKIN, json=body)
    assert r.status_code == 400 and r.json() == {"error": "Mã vé không hợp lệ"}


def test_progress_counts(c, gate):
    _, codes = gate["order"](gate["mine"], qty=3)
    gate["order"](gate["mine"], qty=2, status="refunded")  # đơn hoàn không tính
    gate["order"](gate["other"], qty=4)                    # sự kiện khác không tính
    assert c.post(CHECKIN, json={"code": codes[0]}).json()["progress"] == {"checkedIn": 1, "total": 3}
    assert c.post(CHECKIN, json={"code": codes[1]}).json()["progress"] == {"checkedIn": 2, "total": 3}
    assert c.post(CHECKIN, json={"code": codes[1]}).json()["progress"] == {"checkedIn": 2, "total": 3}


def test_show_today_flag(c, gate, api_db):
    _, codes = gate["order"](gate["mine"], qty=2)
    assert c.post(CHECKIN, json={"code": codes[0]}).json()["showToday"] is False  # suất 30 ngày sau
    from app.models.catalog import Show

    later_today = datetime.combine(datetime.now(VN).date(), time(23, 59), tzinfo=VN)
    api_db.execute(update(Show).where(Show.event_id == gate["mine"].id).values(starts_at=later_today))
    api_db.commit()
    assert c.post(CHECKIN, json={"code": codes[1]}).json()["showToday"] is True


def test_seat_label_matches_customer_ticket(c, gate, api_db):
    """Sự kiện bán theo ghế: chữ ghế ở cổng soát == chữ ghế trên vé của khách"""
    vm = api_db.scalar(select(VenueMap).where(VenueMap.kind == "seats").order_by(VenueMap.id))
    group = api_db.scalar(select(MapGroup).where(MapGroup.map_id == vm.id).order_by(MapGroup.sort_order))
    seat = api_db.scalar(select(MapSeat).where(MapSeat.map_id == vm.id, MapSeat.group_id == group.id).order_by(MapSeat.id))
    ev = gate["mine"]
    api_db.execute(update(Event).where(Event.id == ev.id).values(layout="seats", map_id=vm.id))
    api_db.add(TicketTier(event_id=ev.id, id=group.id, name=group.label, price=300000, capacity=10, max_per_order=10,
                          group_id=group.id))
    api_db.commit()
    o = insert_order(api_db, gate["buyer"], ev.slug, ev._test_show_id, seats=[(group.id, seat.id)])
    code = api_db.scalar(select(Ticket.code).where(Ticket.order_id == o.id))
    at_gate = c.post(CHECKIN, json={"code": code}).json()["ticket"]["seat"]
    login(c, gate["buyer"].email)
    mine = next(x for x in c.get("/api/orders").json()["orders"] if x["id"] == o.id)
    assert at_gate == seat.label == mine["tickets"][0]["seat"]
    assert mine["tickets"][0]["checkedInAt"] is not None


def test_requires_organizer(c, logged_customer):
    assert c.post(CHECKIN, json={"code": "K7QF-29XM"}).status_code == 403
