"""Task D1 — DELETE /api/organizer/events/{id}: huỷ sự kiện (xoá hẳn khi chưa có đơn, có đơn → huỷ mềm + hoàn tiền)"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.catalog import Event, Show
from app.models.sales import Order, Ticket
from app.services import org_events
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer

REASON = "Ca sĩ ốm, ban tổ chức xin lỗi khán giả"


def cancel(c, ev_id, reason=REASON):
    return c.request("DELETE", f"/api/organizer/events/{ev_id}", json={"reason": reason})  # API chỉ nhận JSON (chống CSRF)


@pytest.fixture
def stage(c, logged_organizer, api_db, auth_db):
    reviewed = datetime.now(timezone.utc) - timedelta(days=3)
    made = []

    def event(slug, **kw):
        ev = make_org_event(api_db, slug=slug, organizer_id=logged_organizer.id, reviewed_at=reviewed, **kw)
        made.append((ev.id, ev))
        return ev

    buyer = make_customer(api_db, "khach-huy@x.vn")

    def order(ev, qty=1, status="paid"):
        o = insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", qty)])
        o.status = status
        api_db.commit()
        return o

    yield {"event": event, "order": order, "buyer": buyer, "org": logged_organizer}
    api_db.rollback()
    for eid, ev in made:
        api_db.expire_all()
        if api_db.scalar(select(Event.id).where(Event.id == eid)) is not None:
            drop_event(api_db, ev)


def fresh(engine):
    """Đọc lại bằng một kết nối khác (không dùng session của test)"""
    return Session(engine)


def test_delete_without_orders_removes_event(c, stage, api_db, engine):
    ev = stage["event"]("huy-chua-co-don")
    r = cancel(c, ev.id, reason=None)
    assert r.status_code == 200 and r.json() == {"deleted": True}
    with fresh(engine) as s:
        assert s.get(Event, ev.id) is None
        assert s.scalar(select(Show).where(Show.event_id == ev.id)) is None


def test_cancel_with_orders_refunds_all(c, stage, engine):
    ev = stage["event"]("huy-co-don")
    o1, o2 = stage["order"](ev, 2), stage["order"](ev, 1)
    already = stage["order"](ev, 1, status="refunded")
    r = cancel(c, ev.id)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["deleted"] is False and body["refundedOrders"] == 2 and body["refundedAmount"] == o1.total + o2.total
    assert body["event"]["phase"] == "cancelled" and body["event"]["cancelReason"] == REASON
    with fresh(engine) as s:
        e = s.get(Event, ev.id)
        assert (e.status, e.cancel_reason, e.cancelled_by) == ("cancelled", REASON, "organizer") and e.cancelled_at
        rows = {o.id: o for o in s.scalars(select(Order).where(Order.event_id == ev.id))}
        assert rows[o1.id].status == rows[o2.id].status == "refunded" and rows[o1.id].refunded_at is not None
        assert rows[already.id].refunded_at is None  # đã hoàn trước đó, không đụng tới
    listed = {o["id"]: o for o in c.get("/api/organizer/orders", params={"eventId": ev.id}).json()["orders"]}
    assert listed[o1.id]["status"] == "refunded" and listed[o1.id]["refundedAt"].endswith("+07:00")


@pytest.mark.parametrize("reason", [None, "", "ab", "x" * 301, 123])
def test_cancel_requires_reason(c, stage, reason):
    ev = stage["event"]("huy-thieu-ly-do")
    stage["order"](ev)
    r = cancel(c, ev.id, reason=reason)
    assert r.status_code == 400 and r.json() == {"error": "Vui lòng nhập lý do huỷ (5–300 ký tự)"}


def test_cancelled_hidden_and_not_bookable(c, stage):
    ev = stage["event"]("huy-an-khoi-trang")
    stage["order"](ev)
    assert c.get(f"/api/events/{ev.slug}").status_code == 200
    assert cancel(c, ev.id).status_code == 200
    assert all(e["slug"] != ev.slug for e in c.get("/api/events", params={"limit": 200}).json()["events"])
    assert c.get(f"/api/events/{ev.slug}").status_code == 404
    r = c.post("/api/orders", json={"slug": ev.slug, "items": [{"tierId": "ve-1", "qty": 1}], "method": "qr",
                                    "buyer": {"name": "Khách A", "email": "a@x.vn", "phone": "0912345678"}})
    assert r.status_code == 404


def test_cancel_ended_409(c, stage, api_db):
    ev = stage["event"]("huy-da-dien", starts_at=datetime.now(timezone.utc) - timedelta(days=3))
    stage["order"](ev)
    r = cancel(c, ev.id)
    assert r.status_code == 409 and r.json() == {"error": "Sự kiện đã diễn ra, không thể huỷ"}
    api_db.execute(update(Show).where(Show.event_id == ev.id).values(starts_at=datetime.now(timezone.utc) - timedelta(minutes=5)))
    api_db.commit()  # phase closed (đang diễn)
    assert cancel(c, ev.id).status_code == 409


def test_cancel_twice_409(c, stage):
    ev = stage["event"]("huy-hai-lan")
    stage["order"](ev)
    assert cancel(c, ev.id).status_code == 200
    r = cancel(c, ev.id)
    assert r.status_code == 409 and r.json() == {"error": "Sự kiện đã được huỷ trước đó"}


def test_cancel_pending_without_orders_deletes(c, stage):
    ev = stage["event"]("huy-cho-duyet", status="pending")
    assert cancel(c, ev.id, reason=None).json() == {"deleted": True}


@pytest.mark.parametrize("bad", ["abc", "99999999999", "0"])
def test_other_org_404(c, stage, api_db, bad):
    other = make_org_event(api_db, slug="huy-btc-khac")
    try:
        for target in (str(other.id), bad):
            r = c.request("DELETE", f"/api/organizer/events/{target}", json={"reason": REASON})
            assert r.status_code == 404 and r.json() == {"error": "Sự kiện không tồn tại"}
        assert api_db.get(Event, other.id).status == "approved"
    finally:
        drop_org_event(api_db, other)


def test_checkin_after_cancel_409(c, stage, api_db):
    ev = stage["event"]("huy-roi-soat")
    o = stage["order"](ev)
    code = api_db.scalar(select(Ticket.code).where(Ticket.order_id == o.id))
    cancel(c, ev.id)
    r = c.post("/api/organizer/checkin", json={"code": code})
    assert r.status_code == 409 and r.json() == {"error": "Vé thuộc đơn đã hoàn tiền hoặc đã huỷ"}


def test_phase_cancelled_in_summary(c, stage):
    ev = stage["event"]("huy-tom-tat")
    stage["order"](ev)
    cancel(c, ev.id)
    me = next(e for e in c.get("/api/organizer/me").json()["events"] if e["id"] == ev.id)
    assert me["status"] == "cancelled" and me["phase"] == "cancelled"
    assert me["cancelReason"] == REASON and me["cancelledBy"] == "organizer"


def test_customer_orders_show_refund(c, stage):
    ev = stage["event"]("huy-khach-thay")
    o = stage["order"](ev)
    cancel(c, ev.id)
    login(c, stage["buyer"].email)
    mine = next(x for x in c.get("/api/orders").json()["orders"] if x["id"] == o.id)
    assert mine["status"] == "refunded" and mine["eventStatus"] == "cancelled"
    assert mine["cancelReason"] == REASON and mine["cancelledBy"] == "organizer"
    assert mine["refundedAt"].endswith("+07:00")


def test_admin_overview_survives_cancelled(c, stage, api_db):
    ev = stage["event"]("huy-overview")
    stage["order"](ev)
    cancel(c, ev.id)
    admin = make_customer(api_db, "quantri-huy@x.vn")
    admin.role = "admin"
    api_db.commit()
    login(c, admin.email)
    assert c.get("/api/admin/overview").status_code == 200
    assert c.get("/api/admin/organizers").status_code == 200


# ------------------------------------------------------------------ transaction: lỗi giữa chừng → không ghi dở
def test_cancel_rollback_on_midway_error(c, stage, engine, monkeypatch):
    ev = stage["event"]("huy-loi-giua-chung")
    o = stage["order"](ev, 2)

    def boom(db, event_id):
        raise RuntimeError("mất kết nối giữa chừng")

    monkeypatch.setattr(org_events, "_refund_paid_orders", boom)
    with pytest.raises(RuntimeError):
        cancel(c, ev.id)
    with fresh(engine) as s:
        e = s.get(Event, ev.id)
        assert e.status == "approved" and e.cancel_reason is None and e.cancelled_at is None and e.cancelled_by is None
        order = s.get(Order, o.id)
        assert order.status == "paid" and order.refunded_at is None
