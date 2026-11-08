"""Task D4 — POST /api/admin/events/{id}/cancel: Admin gỡ sự kiện vi phạm (luôn huỷ mềm, luôn cần lý do)"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Event
from app.models.sales import Order
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer

REASON = "Sự kiện vi phạm điều khoản của sàn"


@pytest.fixture
def desk(c, api, api_db, auth_db):
    made = []

    def event(slug, **kw):
        kw.setdefault("reviewed_at", datetime.now(timezone.utc) - timedelta(days=2))
        ev = make_org_event(api_db, slug=slug, **kw)
        made.append(ev)
        return ev

    buyer = make_customer(api_db, "khach-go@x.vn")
    admin = make_customer(api_db, "quantri-go@x.vn")
    admin.role = "admin"
    api_db.commit()
    login(c, admin.email)
    yield {"event": event, "buyer": buyer}
    api_db.rollback()
    for ev in made:
        api_db.expire_all()
        if api_db.scalar(select(Event.id).where(Event.id == ev.id)) is not None:
            drop_org_event(api_db, ev)


def admin_cancel(c, eid, reason=REASON):
    return c.post(f"/api/admin/events/{eid}/cancel", json={"reason": reason})


def test_admin_cancel_refunds_and_keeps_event(c, desk, api_db, engine):
    ev = desk["event"]("go-co-don")
    o1 = insert_order(api_db, desk["buyer"], ev.slug, ev._test_show_id, [("ve-1", 2)])
    o2 = insert_order(api_db, desk["buyer"], ev.slug, ev._test_show_id, [("ve-1", 1)])
    r = admin_cancel(c, ev.id)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted"] is False and body["refundedOrders"] == 2 and body["refundedAmount"] == o1.total + o2.total
    assert body["event"]["phase"] == "cancelled" and body["event"]["cancelledBy"] == "admin"
    with Session(engine) as s:
        e = s.get(Event, ev.id)
        assert (e.status, e.cancel_reason, e.cancelled_by) == ("cancelled", REASON, "admin")
        assert set(s.scalars(select(Order.status).where(Order.event_id == ev.id))) == {"refunded"}


def test_admin_cancel_without_orders_soft_cancels(c, desk, engine):
    ev = desk["event"]("go-chua-co-don")
    r = admin_cancel(c, ev.id)
    assert r.status_code == 200, r.text
    assert r.json()["deleted"] is False and r.json()["refundedOrders"] == 0
    with Session(engine) as s:
        assert s.get(Event, ev.id).status == "cancelled"  # vẫn còn dấu vết


@pytest.mark.parametrize("reason", [None, "", "ab", "x" * 301, 123])
def test_admin_cancel_requires_reason_even_without_orders(c, desk, engine, reason):
    ev = desk["event"]("go-thieu-ly-do")
    r = admin_cancel(c, ev.id, reason)
    assert r.status_code == 400 and r.json() == {"error": "Vui lòng nhập lý do huỷ (5–300 ký tự)"}
    with Session(engine) as s:
        assert s.get(Event, ev.id).status == "approved"


def test_admin_cancel_pending_event_ok(c, desk):
    ev = desk["event"]("go-cho-duyet", status="pending", reviewed_at=None)
    r = admin_cancel(c, ev.id)
    assert r.status_code == 200 and r.json()["event"]["phase"] == "cancelled"


def test_admin_cancel_ended_409(c, desk):
    ev = desk["event"]("go-da-dien", starts_at=datetime.now(timezone.utc) - timedelta(days=1))
    r = admin_cancel(c, ev.id)
    assert r.status_code == 409 and r.json() == {"error": "Sự kiện đã diễn ra, không thể huỷ"}


def test_admin_then_org_cancel_409_single_refund(c, desk, api_db, engine):
    ev = desk["event"]("go-roi-btc-huy")
    insert_order(api_db, desk["buyer"], ev.slug, ev._test_show_id, [("ve-1", 1)])
    assert admin_cancel(c, ev.id).status_code == 200
    from fastapi import HTTPException

    from app.services import org_events

    with Session(engine) as s, pytest.raises(HTTPException) as e:
        org_events.cancel_event(s, ev.organizer_id, ev.id, "BTC cũng muốn huỷ")
    assert e.value.status_code == 409 and e.value.detail == "Sự kiện đã được huỷ trước đó"
    assert admin_cancel(c, ev.id).status_code == 409
    with Session(engine) as s:
        refunded_at = s.scalars(select(Order.refunded_at).where(Order.event_id == ev.id)).all()
        assert len(refunded_at) == 1 and refunded_at[0] is not None
        assert s.get(Event, ev.id).cancelled_by == "admin"


@pytest.mark.parametrize("eid", ["0", "999999999", "abc", "12345678901", "2147483648"])
def test_admin_cancel_unknown_404(c, desk, eid):
    r = admin_cancel(c, eid)
    assert r.status_code == 404


def test_admin_cancel_needs_admin(c, desk, api_db):
    ev = desk["event"]("go-khong-quyen")
    login(c, desk["buyer"].email)
    assert admin_cancel(c, ev.id).status_code == 403


def test_org_sees_cancelled_by_admin(c, desk, api_db):
    ev = desk["event"]("go-btc-thay")
    insert_order(api_db, desk["buyer"], ev.slug, ev._test_show_id, [("ve-1", 1)])
    assert admin_cancel(c, ev.id).status_code == 200
    events = {e["id"]: e for e in c.get(f"/api/admin/organizers/{ev.organizer_id}/events").json()["events"]}
    assert events[ev.id]["cancelledBy"] == "admin" and events[ev.id]["cancelReason"] == REASON


def test_customer_sees_cancelled_by_admin(c, desk, api_db):
    ev = desk["event"]("go-khach-thay")
    o = insert_order(api_db, desk["buyer"], ev.slug, ev._test_show_id, [("ve-1", 1)])
    assert admin_cancel(c, ev.id).status_code == 200
    login(c, desk["buyer"].email)
    mine = {x["id"]: x for x in c.get("/api/orders").json()["orders"]}
    got = mine[o.id]
    assert got["status"] == "refunded" and got["eventStatus"] == "cancelled"
    assert got["cancelledBy"] == "admin" and got["cancelReason"] == REASON and got["refundedAt"]
