"""Task E1 — GET/POST /api/organizer/withdrawals: số dư (đã quyết toán / tạm giữ) và yêu cầu rút tiền"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.catalog import Event
from app.models.payouts import Withdrawal
from app.services import manage, org_events, withdrawals
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer

BANK = {"bankName": "Vietcombank", "accountNo": "0123456789", "accountName": "CONG TY SU KIEN THU"}


def net(revenue: int) -> int:
    return revenue - manage.fee_of(revenue)


@pytest.fixture
def money(c, logged_organizer, api_db, auth_db):
    """Sự kiện của BTC đang đăng nhập: ended(...) đã diễn 3 ngày trước, live(...) đang bán"""
    made = []
    buyer = make_customer(api_db, "khach-rut@x.vn")
    reviewed = datetime.now(timezone.utc) - timedelta(days=20)

    def event(slug, *, ended: bool, revenues: list[int]):
        starts = datetime.now(timezone.utc) + (timedelta(days=-3) if ended else timedelta(days=30))
        ev = make_org_event(api_db, slug=slug, organizer_id=logged_organizer.id, reviewed_at=reviewed, starts_at=starts)
        made.append(ev)
        for r in revenues:
            o = insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", 1)])
            o.discount, o.total = o.subtotal - r, r  # doanh thu tuỳ ý (BTC chịu giảm giá)
        api_db.commit()
        return ev

    yield {"event": event, "org": logged_organizer, "buyer": buyer}
    api_db.rollback()
    for ev in made:
        api_db.expire_all()
        if api_db.scalar(select(Event.id).where(Event.id == ev.id)) is not None:
            drop_event(api_db, ev)


def get(c):
    r = c.get("/api/organizer/withdrawals")
    assert r.status_code == 200, r.text
    return r.json()


def post(c, amount, **over):
    return c.post("/api/organizer/withdrawals", json={"amount": amount, **BANK, **over})


def test_balance_settled_vs_held(c, money):
    money["event"]("rut-da-dien-a", ended=True, revenues=[10010])
    money["event"]("rut-da-dien-b", ended=True, revenues=[10010, 200000])
    money["event"]("rut-dang-ban", ended=False, revenues=[200000])
    body = get(c)
    # phí tính theo TỪNG sự kiện rồi cộng lại
    assert body["balance"] == {"settledNet": net(10010) + net(210010), "held": net(200000), "pending": 0, "paid": 0,
                               "available": net(10010) + net(210010)}
    assert body["withdrawals"] == []


def test_held_money_not_withdrawable(c, money):
    money["event"]("rut-chi-dang-ban", ended=False, revenues=[200000])
    assert get(c)["balance"]["available"] == 0
    r = post(c, 50000)
    assert r.status_code == 409 and r.json() == {"error": "Số dư khả dụng không đủ"}


def test_request_reduces_available(c, money):
    money["event"]("rut-giam-kha-dung", ended=True, revenues=[200000])
    r = post(c, 100000)
    assert r.status_code == 201, r.text
    body = r.json()
    w = body["withdrawal"]
    assert set(w) == {"id", "amount", "bankName", "accountNo", "accountName", "status", "note", "createdAt", "processedAt"}
    assert (w["amount"], w["status"], w["note"], w["processedAt"]) == (100000, "pending", None, None)
    assert w["bankName"] == BANK["bankName"] and w["createdAt"].endswith("+07:00")
    assert body["balance"]["pending"] == 100000 and body["balance"]["available"] == net(200000) - 100000
    listed = get(c)
    assert [x["id"] for x in listed["withdrawals"]] == [w["id"]] and listed["balance"] == body["balance"]


def test_request_over_balance_409(c, money, engine):
    money["event"]("rut-qua-so-du", ended=True, revenues=[200000])
    r = post(c, net(200000) + 1)
    assert r.status_code == 409 and r.json() == {"error": "Số dư khả dụng không đủ"}
    with Session(engine) as s:
        assert s.scalar(select(Withdrawal.id).where(Withdrawal.organizer_id == money["org"].id)) is None


def test_two_requests_each_full_balance_second_409(c, money):
    money["event"]("rut-hai-lan", ended=True, revenues=[200000])
    full = net(200000)
    assert post(c, full).status_code == 201
    r = post(c, full)
    assert r.status_code == 409 and r.json() == {"error": "Số dư khả dụng không đủ"}
    assert get(c)["balance"]["available"] == 0


@pytest.mark.parametrize("over, message", [
    ({"amount": 49999}, "Số tiền rút tối thiểu 50.000 ₫"),
    ({"amount": "abc"}, "Số tiền rút tối thiểu 50.000 ₫"),
    ({"amount": 60000.5}, "Số tiền rút tối thiểu 50.000 ₫"),
    ({"amount": True}, "Số tiền rút tối thiểu 50.000 ₫"),
    ({"bankName": "V"}, "Vui lòng nhập tên ngân hàng"),
    ({"bankName": None}, "Vui lòng nhập tên ngân hàng"),
    ({"bankName": "x" * 61}, "Vui lòng nhập tên ngân hàng"),
    ({"accountNo": "12345"}, "Số tài khoản chỉ gồm 6–20 chữ số"),
    ({"accountNo": "12345a78"}, "Số tài khoản chỉ gồm 6–20 chữ số"),
    ({"accountNo": "1" * 21}, "Số tài khoản chỉ gồm 6–20 chữ số"),
    ({"accountNo": "１２３４５６７"}, "Số tài khoản chỉ gồm 6–20 chữ số"),
    ({"accountName": " "}, "Vui lòng nhập tên chủ tài khoản"),
    ({"accountName": 12}, "Vui lòng nhập tên chủ tài khoản"),
])
def test_validation_400(c, money, over, message):
    money["event"]("rut-du-lieu-sai", ended=True, revenues=[200000])
    body = {"amount": 60000, **BANK, **over}
    r = c.post("/api/organizer/withdrawals", json=body)
    assert r.status_code == 400 and r.json() == {"error": message}


def test_rejected_returns_money_paid_does_not(c, money, api_db):
    money["event"]("rut-tu-choi", ended=True, revenues=[200000])
    a = post(c, 60000).json()["withdrawal"]["id"]
    b = post(c, 70000).json()["withdrawal"]["id"]
    now = datetime.now(timezone.utc)
    api_db.execute(update(Withdrawal).where(Withdrawal.id == a).values(status="rejected", note="Sai số TK", processed_at=now))
    api_db.execute(update(Withdrawal).where(Withdrawal.id == b).values(status="paid", processed_at=now))
    api_db.commit()
    body = get(c)
    assert body["balance"]["pending"] == 0 and body["balance"]["paid"] == 70000
    assert body["balance"]["available"] == net(200000) - 70000
    by_id = {w["id"]: w for w in body["withdrawals"]}
    assert by_id[a]["status"] == "rejected" and by_id[a]["note"] == "Sai số TK" and by_id[a]["processedAt"]
    assert [w["id"] for w in body["withdrawals"]] == [b, a]  # mới trước


def test_cancel_only_reduces_held(c, money, api_db):
    money["event"]("rut-huy-da-dien", ended=True, revenues=[200000])
    live = money["event"]("rut-huy-dang-ban", ended=False, revenues=[200000])
    before = get(c)["balance"]
    org_events.cancel_event(api_db, money["org"].id, live.id, "Ca sĩ ốm, xin lỗi khán giả")
    api_db.commit()
    after = get(c)["balance"]
    assert after["held"] == before["held"] - net(200000) == 0
    assert after["available"] == before["available"] == net(200000)


def test_only_own_withdrawals(c, money, api_db, engine):
    money["event"]("rut-cua-minh", ended=True, revenues=[200000])
    mine = post(c, 60000).json()["withdrawal"]["id"]
    other = make_org_event(api_db, slug="rut-btc-khac", reviewed_at=datetime.now(timezone.utc) - timedelta(days=20),
                           starts_at=datetime.now(timezone.utc) - timedelta(days=3))
    try:
        insert_order(api_db, money["buyer"], other.slug, other._test_show_id, [("ve-1", 1)])
        api_db.add(Withdrawal(organizer_id=other.organizer_id, amount=50000, **{
            "bank_name": "ACB", "account_no": "999999", "account_name": "KHAC"}))
        api_db.commit()
        body = get(c)
        assert [w["id"] for w in body["withdrawals"]] == [mine]
        assert body["balance"]["settledNet"] == net(200000)  # không cộng tiền của BTC khác
    finally:
        drop_org_event(api_db, other)


def test_not_organizer_403(c, money, api_db):
    login(c, money["buyer"].email)
    assert c.get("/api/organizer/withdrawals").status_code == 403
    assert post(c, 60000).status_code == 403


def test_request_rollback_on_midway_error(c, money, engine, monkeypatch):
    money["event"]("rut-loi-giua-chung", ended=True, revenues=[200000])
    before = get(c)["balance"]

    def boom(*a, **kw):
        raise RuntimeError("mất kết nối giữa chừng")

    monkeypatch.setattr(withdrawals, "to_json", boom)  # chạy SAU khi đã INSERT withdrawals
    with pytest.raises(RuntimeError):
        post(c, 60000)
    monkeypatch.undo()
    with Session(engine) as s:  # kết nối khác
        assert s.scalar(select(Withdrawal.id).where(Withdrawal.organizer_id == money["org"].id)) is None
    assert get(c)["balance"] == before
