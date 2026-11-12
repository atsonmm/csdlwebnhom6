"""Task E1 — hai yêu cầu rút tiền chạy chồng lấn trên 2 KẾT NỐI CSDL: khoá organizers FOR UPDATE chống rút quá số dư"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payouts import Withdrawal
from app.services import manage, withdrawals
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, make_customer
from tests.concurrency import race, winner_loser

HOLD = 0.3
BANK = {"bankName": "Vietcombank", "accountNo": "0123456789", "accountName": "CONG TY SU KIEN THU"}


@pytest.fixture
def settled(api, api_db, auth_db):
    """BTC có 1 sự kiện đã diễn, 2 đơn đã trả → số dư khả dụng X"""
    ev = make_org_event(api_db, slug="rut-dong-thoi", reviewed_at=datetime.now(timezone.utc) - timedelta(days=20),
                        starts_at=datetime.now(timezone.utc) - timedelta(days=3))
    buyer = make_customer(api_db, "khach-rut-dong-thoi@x.vn")
    for _ in range(2):
        insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", 1)])
    yield ev
    drop_org_event(api_db, ev)


def _available(engine, org_id: int) -> int:
    with Session(engine) as s:
        return withdrawals.balance(s, org_id)["available"]


def test_concurrent_requests_two_connections(settled, engine, monkeypatch):
    org = settled.organizer_id
    x = _available(engine, org)
    assert x == 400000 - manage.fee_of(400000)

    def go(s):
        return withdrawals.to_json(withdrawals.request(s, org, {"amount": x, **BANK}))

    outs = race(engine, go, go, module=withdrawals, hold=HOLD, monkeypatch=monkeypatch)
    win, lose = winner_loser(outs)
    assert lose.value == 409 and lose.detail == "Số dư khả dụng không đủ"
    assert lose.elapsed >= HOLD - 0.05, f"bên thua không bị chặn ở FOR UPDATE ({lose.elapsed:.3f}s)"
    assert win.value["amount"] == x
    with Session(engine) as s:
        rows = s.execute(select(Withdrawal.status, func.count()).where(Withdrawal.organizer_id == org)
                         .group_by(Withdrawal.status)).all()
        assert rows == [("pending", 1)]
    assert _available(engine, org) == 0


def test_concurrent_half_requests_both_succeed(settled, engine, monkeypatch):
    """Khoá không chặn sai: hai yêu cầu mỗi cái một nửa số dư → cả hai thành công (lần lượt nhờ khoá)"""
    org = settled.organizer_id
    x = _available(engine, org)
    half = x // 2

    def go(s):
        return withdrawals.to_json(withdrawals.request(s, org, {"amount": half, **BANK}))

    outs = race(engine, go, go, module=withdrawals, hold=HOLD, monkeypatch=monkeypatch)
    assert all(o.ok for o in outs), outs
    assert max(o.elapsed for o in outs) >= HOLD - 0.05  # bên sau vẫn phải chờ khoá
    assert _available(engine, org) == x - 2 * half
