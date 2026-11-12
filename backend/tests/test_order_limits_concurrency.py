"""Hạn mức theo tài khoản — tranh chấp thật bằng 2 KẾT NỐI CSDL (tests/concurrency.race):
cùng một người đặt ở 2 tab cùng lúc → chỉ một đơn qua khi tổng vượt hạn mức; hai người khác nhau không chờ nhau"""
from sqlalchemy.orm import Session

from app.models.catalog import TicketTier
from app.models.users import User
from app.schemas.booking import OrderIn
from app.services import booking
from tests.booking_helpers import event_id, make_customer
from tests.concurrency import race, winner_loser
from tests.resale_helpers import BUYER, LIST_EVENT, future_show

HOLD = 0.3


def _place(uid, show, qty):
    def go(s: Session):
        body = OrderIn(slug=LIST_EVENT, showId=show, items=[{"tierId": "thuong", "qty": qty}], buyer=BUYER, method="qr")
        return booking.create_order(s, s.get(User, uid), body).id
    return go


def test_same_user_two_tabs(api, api_db, auth_db, engine, monkeypatch):
    user = make_customer(api_db, "hai-tab@x.vn")
    show = future_show(api_db, LIST_EVENT)
    cap = api_db.get(TicketTier, (event_id(api_db, LIST_EVENT), "thuong")).max_per_order
    qty = cap // 2 + 1  # mỗi đơn hợp lệ một mình, hai đơn cộng lại vượt hạn mức
    win, lose = winner_loser(race(engine, _place(user.id, show, qty), _place(user.id, show, qty),
                                  module=booking, hold=HOLD, monkeypatch=monkeypatch))
    assert lose.value == 409 and lose.detail.startswith(f"Bạn đã có {qty} vé")
    assert lose.elapsed >= HOLD - 0.05, f"bên thua không bị chặn ở khoá dòng users ({lose.elapsed:.3f}s)"
    with Session(engine) as s:
        assert booking.held_by_tier(s, user.id, event_id(s, LIST_EVENT), show) == {"thuong": qty}


def test_two_users_not_blocked(api, api_db, auth_db, engine, monkeypatch):
    a = make_customer(api_db, "nguoi-a-song-song@x.vn")
    b = make_customer(api_db, "nguoi-b-song-song@x.vn")
    show = future_show(api_db, LIST_EVENT, 1)
    outs = race(engine, _place(a.id, show, 1), _place(b.id, show, 1), module=booking, hold=HOLD, monkeypatch=monkeypatch)
    assert all(o.ok for o in outs), outs
    assert min(o.elapsed for o in outs) < HOLD  # bên đến sau không phải chờ khoá của người khác
    assert max(o.elapsed for o in outs) < 2 * HOLD
