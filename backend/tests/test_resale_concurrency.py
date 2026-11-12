"""Chợ vé bán lại — tranh chấp thật bằng 2 KẾT NỐI CSDL (tests/concurrency.race):
1) hai người cùng mua vé cuối của một tin; 2) người bán gỡ tin đúng lúc có người mua; 3) đăng cùng một vé ở hai tin"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.resale import ResaleListing, ResaleListingTicket
from app.models.sales import Order, Ticket
from app.models.users import User
from app.services import resale
from tests.booking_helpers import make_customer
from tests.concurrency import race, winner_loser
from tests.resale_helpers import BUYER, buy

HOLD = 0.3


def _listing(api_db, seller, n=1, allow_partial=True):
    _o, codes = buy(api_db, seller, n=n)
    lst = resale.create_listing(api_db, seller, codes, 100000, allow_partial)
    api_db.commit()
    return lst.id, codes


def _buyer(api_db, email):
    return make_customer(api_db, email).id


def test_two_buyers_last_ticket(api, api_db, auth_db, engine, monkeypatch):
    seller = make_customer(api_db, "ban-tranh@x.vn")
    lid, codes = _listing(api_db, seller)
    a, b = _buyer(api_db, "mua-a@x.vn"), _buyer(api_db, "mua-b@x.vn")

    def go(uid):
        return lambda s: resale.buy(s, s.get(User, uid), lid, None, None, "qr", BUYER).id

    win, lose = winner_loser(race(engine, go(a), go(b), module=resale, hold=HOLD, monkeypatch=monkeypatch))
    assert lose.value == 409 and lose.detail == "Vé vừa được người khác mua hoặc tin đã đóng"
    assert lose.elapsed >= HOLD - 0.05, f"bên thua không bị chặn ở FOR UPDATE ({lose.elapsed:.3f}s)"
    with Session(engine) as s:
        assert s.scalar(select(Order.id).where(Order.kind == "resale", Order.user_id.in_([a, b]))) == win.value
        assert s.scalars(select(Order.id).where(Order.kind == "resale", Order.user_id.in_([a, b]))).all() == [win.value]
        assert s.get(Ticket, codes[0]).transferred_at is not None


def test_cancel_vs_buy(api, api_db, auth_db, engine, monkeypatch):
    seller = make_customer(api_db, "ban-go-tranh@x.vn")
    lid, codes = _listing(api_db, seller, n=2)
    buyer = _buyer(api_db, "mua-go-tranh@x.vn")

    def cancel(s):
        return resale.cancel_listing(s, s.get(User, seller.id), lid).status

    def purchase(s):
        return resale.buy(s, s.get(User, buyer), lid, None, None, "qr", BUYER).id

    outs = race(engine, cancel, purchase, module=resale, hold=HOLD, monkeypatch=monkeypatch)
    win, lose = winner_loser(outs)
    assert lose.value == 409
    with Session(engine) as s:
        rows = s.scalars(select(ResaleListingTicket.status).where(ResaleListingTicket.listing_id == lid)).all()
        assert len(set(rows)) == 1 and rows[0] in ("sold", "cancelled")  # không vé nào nửa bán nửa gỡ
        assert s.get(ResaleListing, lid).status == ("cancelled" if win.value == "cancelled" else "sold")


def test_same_ticket_listed_twice(api, api_db, auth_db, engine, monkeypatch):
    seller = make_customer(api_db, "dang-trung@x.vn")
    _o, codes = buy(api_db, seller, n=1)

    def go(price):
        return lambda s: resale.create_listing(s, s.get(User, seller.id), codes, price, True).id

    win, lose = winner_loser(race(engine, go(100000), go(90000), module=resale, hold=HOLD, monkeypatch=monkeypatch))
    assert lose.value == 409 and lose.detail == "Vé đã nằm trong tin bán khác"
    with Session(engine) as s:
        listed = s.scalars(select(ResaleListingTicket.listing_id).where(ResaleListingTicket.ticket_code == codes[0],
                                                                        ResaleListingTicket.status == "listed")).all()
        assert listed == [win.value]
