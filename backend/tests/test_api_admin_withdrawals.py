"""Task E2 — Admin duyệt rút tiền: GET /api/admin/withdrawals, POST /api/admin/withdrawals/{id}/decide"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payouts import Withdrawal
from app.models.users import User
from app.services import withdrawals
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer
from tests.concurrency import race, winner_loser

BANK = {"bankName": "Vietcombank", "accountNo": "0123456789", "accountName": "CONG TY SU KIEN THU"}
HOLD = 0.3


@pytest.fixture
def desk(c, api, api_db, auth_db):
    """1 BTC có sự kiện đã diễn (2 đơn) + 1 yêu cầu rút đang chờ; Admin đang đăng nhập trên c"""
    ev = make_org_event(api_db, slug="duyet-rut", reviewed_at=datetime.now(timezone.utc) - timedelta(days=20),
                        starts_at=datetime.now(timezone.utc) - timedelta(days=3))
    buyer = make_customer(api_db, "khach-duyet-rut@x.vn")
    for _ in range(2):
        insert_order(api_db, buyer, ev.slug, ev._test_show_id, [("ve-1", 1)])
    w = withdrawals.request(api_db, ev.organizer_id, {"amount": 100000, **BANK})
    api_db.commit()
    admin = make_customer(api_db, "quantri-rut@x.vn")
    admin.role = "admin"
    api_db.commit()
    login(c, admin.email)
    yield {"ev": ev, "w": w, "admin": admin, "buyer": buyer}
    drop_org_event(api_db, ev)


def decide(c, wid, decision, note=None):
    return c.post(f"/api/admin/withdrawals/{wid}/decide", json={"decision": decision, "note": note})


def test_admin_lists_pending_with_org_name(c, desk, engine):
    body = c.get("/api/admin/withdrawals").json()
    got = {w["id"]: w for w in body["withdrawals"]}[desk["w"].id]
    assert got["orgName"] == "Đơn vị duyet-rut" and got["status"] == "pending" and got["amount"] == 100000
    assert got["organizerId"] == desk["ev"].organizer_id
    with Session(engine) as s:
        org_view = withdrawals.balance(s, desk["ev"].organizer_id)
    assert got["orgAvailable"] == org_view["available"]
    assert all(w["status"] == "pending" for w in body["withdrawals"])
    assert c.get("/api/admin/withdrawals", params={"status": "paid"}).json()["withdrawals"] == []
    assert len(c.get("/api/admin/withdrawals", params={"status": "all"}).json()["withdrawals"]) >= 1
    r = c.get("/api/admin/withdrawals", params={"status": "x"})
    assert r.status_code == 400 and r.json() == {"error": "Trạng thái không hợp lệ"}


def test_mark_paid_sets_processed(c, desk, engine):
    r = decide(c, desk["w"].id, "paid")
    assert r.status_code == 200, r.text
    w = r.json()["withdrawal"]
    assert w["status"] == "paid" and w["processedAt"].endswith("+07:00") and w["orgName"] == "Đơn vị duyet-rut"
    with Session(engine) as s:
        row = s.get(Withdrawal, desk["w"].id)
        assert row.status == "paid" and row.processed_by == desk["admin"].id and row.processed_at is not None
    assert c.get("/api/admin/withdrawals", params={"status": "paid"}).json()["withdrawals"][0]["id"] == desk["w"].id


@pytest.mark.parametrize("note", [None, "", "ab", "x" * 301, 12])
def test_reject_requires_note(c, desk, engine, note):
    r = decide(c, desk["w"].id, "rejected", note)
    assert r.status_code == 400 and r.json() == {"error": "Vui lòng nhập lý do từ chối (3–300 ký tự)"}
    with Session(engine) as s:
        assert s.get(Withdrawal, desk["w"].id).status == "pending"


def test_reject_with_note_returns_money(c, desk, engine):
    r = decide(c, desk["w"].id, "rejected", "Sai số tài khoản")
    assert r.status_code == 200 and r.json()["withdrawal"]["note"] == "Sai số tài khoản"
    with Session(engine) as s:
        assert withdrawals.balance(s, desk["ev"].organizer_id)["pending"] == 0


def test_bad_decision_400(c, desk):
    r = decide(c, desk["w"].id, "approve")
    assert r.status_code == 400 and r.json() == {"error": "Quyết định không hợp lệ"}


def test_decide_twice_409(c, desk):
    assert decide(c, desk["w"].id, "paid").status_code == 200
    r = decide(c, desk["w"].id, "rejected", "Đổi ý")
    assert r.status_code == 409 and r.json() == {"error": "Yêu cầu này đã được xử lý"}


@pytest.mark.parametrize("wid", ["0", "99999999", "abc", "12345678901", "2147483648"])
def test_unknown_404(c, desk, wid):
    r = decide(c, wid, "paid")
    assert r.status_code == 404 and r.json() == {"error": "Không tìm thấy yêu cầu rút tiền"}


def test_not_admin_403(c, desk):
    login(c, desk["buyer"].email)
    assert c.get("/api/admin/withdrawals").status_code == 403
    assert decide(c, desk["w"].id, "paid").status_code == 403


def test_overview_counts_pending(c, desk):
    assert c.get("/api/admin/overview").json()["pendingWithdrawals"] == 1
    decide(c, desk["w"].id, "paid")
    assert c.get("/api/admin/overview").json()["pendingWithdrawals"] == 0


def test_admin_organizers_balance_matches_org_view(c, desk, api_db):
    org_id = desk["ev"].organizer_id
    row = {o["userId"]: o for o in c.get("/api/admin/organizers").json()["organizers"]}[org_id]
    org_user = api_db.get(User, org_id)
    org_user.password_hash = desk["buyer"].password_hash  # đăng nhập bằng mật khẩu thử của helper
    api_db.commit()
    login(c, org_user.email)
    mine = c.get("/api/organizer/withdrawals").json()["balance"]
    assert (row["available"], row["held"], row["pendingWithdrawals"]) == (mine["available"], mine["held"], mine["pending"])
    assert row["pendingWithdrawals"] == 100000


def test_two_admins_decide_concurrently(desk, api_db, engine, monkeypatch):
    other = make_customer(api_db, "quantri-rut-2@x.vn")
    other.role = "admin"
    api_db.commit()
    a, b, wid = desk["admin"].id, other.id, desk["w"].id  # lấy id trước: luồng không được chạm session của test

    def by_a(s):
        return withdrawals.decide(s, s.get(User, a), wid, "paid", None)

    def by_b(s):
        return withdrawals.decide(s, s.get(User, b), wid, "rejected", "Sai số tài khoản")

    outs = race(engine, by_a, by_b, module=withdrawals, hold=HOLD, monkeypatch=monkeypatch)
    win, lose = winner_loser(outs)
    assert lose.value == 409 and lose.detail == "Yêu cầu này đã được xử lý"
    assert lose.elapsed >= HOLD - 0.05, f"bên thua không bị chặn ở khoá dòng ({lose.elapsed:.3f}s)"
    winner = a if outs[0].ok else b
    with Session(engine) as s:
        row = s.get(Withdrawal, wid)
        assert row.status == win.value["withdrawal"]["status"] and row.processed_by == winner


def test_decide_rollback_on_midway_error(c, desk, engine, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("mất kết nối giữa chừng")

    monkeypatch.setattr(withdrawals, "to_json", boom)  # chạy SAU câu UPDATE
    with pytest.raises(RuntimeError):
        decide(c, desk["w"].id, "paid")
    monkeypatch.undo()
    with Session(engine) as s:  # kết nối khác
        row = s.get(Withdrawal, desk["w"].id)
        assert row.status == "pending" and row.processed_at is None and row.processed_by is None
