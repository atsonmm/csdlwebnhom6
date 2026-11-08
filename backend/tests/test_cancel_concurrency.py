"""Task D1 — huỷ cùng một sự kiện từ 2 kết nối CSDL chạy chồng lấn: chỉ một bên thành công, đơn chỉ hoàn một lần"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Event
from app.models.sales import Order
from app.services import org_events
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, make_customer
from tests.concurrency import race, winner_loser

HOLD = 0.3
REASON = "Địa điểm bị thu hồi giấy phép"


def test_concurrent_cancel_two_connections(api, api_db, auth_db, engine, monkeypatch):
    ev = make_org_event(api_db, slug="huy-dong-thoi", reviewed_at=datetime.now(timezone.utc) - timedelta(days=2))
    try:
        buyer = make_customer(api_db, "khach-dong-thoi@x.vn")
        orders = [insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", q)]) for q in (1, 2, 3)]
        org = ev.organizer_id

        def go(s):
            return org_events.cancel_event(s, org, ev.id, REASON)

        outs = race(engine, go, go, module=org_events, hold=HOLD, monkeypatch=monkeypatch)
        win, lose = winner_loser(outs)
        assert lose.value == 409 and lose.detail == "Sự kiện đã được huỷ trước đó"
        assert lose.elapsed >= HOLD - 0.05, f"bên thua không bị chặn ở FOR UPDATE ({lose.elapsed:.3f}s)"
        assert win.value["refundedOrders"] == 3 and win.value["refundedAmount"] == sum(o.total for o in orders)
        with Session(engine) as s:
            assert s.get(Event, ev.id).status == "cancelled"
            refunds = s.execute(select(Order.status, Order.refunded_at).where(Order.event_id == ev.id)).all()
            assert [st for st, _ in refunds] == ["refunded"] * 3
            assert len({at for _, at in refunds}) == 1  # cùng một lần hoàn (một transaction)
    finally:
        drop_org_event(api_db, ev)


def test_without_lock_hook_sequential_still_single_refund(api, api_db, auth_db, engine):
    """Đối chứng: gọi lần lượt cũng cho đúng 1 thành công (chỉ để so sánh, KHÔNG tính là kiểm thử đồng thời)"""
    ev = make_org_event(api_db, slug="huy-tuan-tu", reviewed_at=datetime.now(timezone.utc) - timedelta(days=2))
    try:
        buyer = make_customer(api_db, "khach-tuan-tu@x.vn")
        insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", 1)])
        with Session(engine) as s1:
            assert org_events.cancel_event(s1, ev.organizer_id, ev.id, REASON)["refundedOrders"] == 1
            s1.commit()
        with Session(engine) as s2:
            import pytest
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as e:
                org_events.cancel_event(s2, ev.organizer_id, ev.id, REASON)
            assert e.value.status_code == 409
    finally:
        drop_org_event(api_db, ev)


def test_admin_org_cancel_concurrent_single_refund(api, api_db, auth_db, engine, monkeypatch):
    """Task D4 — Admin gỡ và BTC huỷ cùng một sự kiện trên 2 kết nối: 1 thắng, 1 bị chặn ở FOR UPDATE rồi 409"""
    ev = make_org_event(api_db, slug="go-va-huy-dong-thoi", reviewed_at=datetime.now(timezone.utc) - timedelta(days=2))
    try:
        buyer = make_customer(api_db, "khach-go-dong-thoi@x.vn")
        orders = [insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", q)]) for q in (1, 2)]
        org = ev.organizer_id

        def by_admin(s):
            return org_events.cancel_event(s, None, ev.id, "Sàn gỡ vì vi phạm", by="admin")

        def by_org(s):
            return org_events.cancel_event(s, org, ev.id, REASON)

        outs = race(engine, by_admin, by_org, module=org_events, hold=HOLD, monkeypatch=monkeypatch)
        win, lose = winner_loser(outs)
        assert lose.value == 409 and lose.detail == "Sự kiện đã được huỷ trước đó"
        assert lose.elapsed >= HOLD - 0.05, f"bên thua không bị chặn ở FOR UPDATE ({lose.elapsed:.3f}s)"
        assert win.value["refundedOrders"] == 2 and win.value["refundedAmount"] == sum(o.total for o in orders)
        winner_by = "admin" if outs[0].ok else "organizer"
        with Session(engine) as s:
            e = s.get(Event, ev.id)
            assert e.status == "cancelled" and e.cancelled_by == winner_by
            refunds = s.execute(select(Order.status, Order.refunded_at).where(Order.event_id == ev.id)).all()
            assert [st for st, _ in refunds] == ["refunded"] * 2
            assert len({at for _, at in refunds}) == 1
    finally:
        drop_org_event(api_db, ev)
