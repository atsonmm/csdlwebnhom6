"""Task G3 — 8 truy vấn SQL thuần (backend/sql/queries): mỗi truy vấn so với cách tính độc lập bằng Python"""
import re
from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Event, Show, TicketTier
from app.models.payouts import Withdrawal
from app.models.sales import Order
from app.services import manage, org_orders, org_reports, sql_queries, withdrawals
from app.services.stock import tier_stats
from app.utils.timefmt import VN, iso_vn
from tests.api_helpers import drop_event, drop_org_event, make_org_event
from tests.booking_helpers import insert_order, login, make_customer


def vn(d: date, hour: int = 12) -> datetime:
    return datetime.combine(d, time(hour, 0), tzinfo=VN)


TODAY = datetime.now(VN).date()


@pytest.fixture
def lab(c, api, api_db, auth_db):
    """Dựng sự kiện + khách + đơn cho từng test; dọn sạch khi xong"""
    made, made_own = [], []
    buyers = [make_customer(api_db, f"khach-sql-{i}@x.vn") for i in range(4)]

    class Lab:
        db = api_db
        customers = buyers

        def event(self, slug, *, organizer_id=None, days=30, reviewed_days_ago=20, **kw):
            ev = make_org_event(api_db, slug=slug, organizer_id=organizer_id,
                                reviewed_at=datetime.now(timezone.utc) - timedelta(days=reviewed_days_ago),
                                starts_at=vn(TODAY + timedelta(days=days), 19), **kw)
            (made_own if organizer_id is not None else made).append(ev)
            return ev

        def order(self, ev, when: datetime, qty=1, buyer=0, status="paid", tier="ve-1", name=None):
            o = insert_order(api_db, buyers[buyer], ev.slug, ev._test_show_id, [(tier, qty)], created_at=when)
            o.status = status
            if name:
                o.buyer_name = name
            api_db.commit()
            return o

    yield Lab()
    api_db.rollback()
    for ev in made_own:
        api_db.expire_all()
        if api_db.get(Event, ev.id) is not None:
            drop_event(api_db, ev)
    for ev in made:
        drop_org_event(api_db, ev)


def test_queries_are_parameterized():
    for name in sql_queries.NAMES:
        body = (sql_queries.QUERIES_DIR / f"{name}.sql").read_text(encoding="utf-8")
        assert body.startswith("-- Q"), name  # có phần chú thích mục đích / đầu vào / API
        sql = sql_queries.load(name)
        assert "{" not in sql and "%s" not in sql and "%(" not in sql, name
        assert re.search(r"(?<!:):[a-z_]+", sql), name  # có tham số bind


def test_q1_order_ledger_matches_python(lab, logged_organizer):
    org = logged_organizer.id
    a, b = lab.event("sql-so-don-a", organizer_id=org), lab.event("sql-so-don-b", organizer_id=org)
    other = lab.event("sql-so-don-khac")
    base = vn(TODAY - timedelta(days=3))
    orders = [lab.order(a, base + timedelta(hours=i), qty=1 + i % 3, buyer=i % 4,
                        status=("refunded" if i == 2 else "paid"), name=f"Nguyễn Văn {i}") for i in range(6)]
    orders += [lab.order(b, base + timedelta(hours=10 + i), qty=2, buyer=1) for i in range(3)]
    lab.order(other, base, qty=5)  # của BTC khác — không được lẫn vào
    mine = sorted(orders, key=lambda o: (o.created_at, o.id), reverse=True)

    def call(**kw):
        p = {"q": "", "event_id": None, "status": "all", "day_from": None, "day_to": None, "page": 1, "page_size": 4} | kw
        with Session(lab.db.get_bind()) as s:
            return org_orders.list_orders(s, org, **p)

    got = call()
    assert got["total"] == len(mine) and [o["id"] for o in got["orders"]] == [o.id for o in mine[:4]]
    assert [o["id"] for o in call(page=3)["orders"]] == [o.id for o in mine[8:]]
    paid = [o for o in mine if o.status == "paid"]
    assert got["summary"] == {"paidOrders": len(paid), "paidRevenue": sum(o.total for o in paid),
                              "tickets": sum(o.subtotal // 200000 for o in paid)}
    assert call(event_id=b.id)["total"] == 3
    assert call(status="refunded")["total"] == 1
    assert [o["id"] for o in call(q="văn 4")["orders"]] == [orders[4].id]
    assert call(q=orders[0].id[2:])["total"] == 0  # mã đơn: khớp tiền tố
    assert call(page=99)["orders"] == [] and call(page=99)["total"] == len(mine)  # trang rỗng vẫn có tổng
    first = got["orders"][0]
    assert first["tickets"] == mine[0].subtotal // 200000 and first["checkedIn"] == 0


def test_q2_q3_series_cumulative_change(lab, logged_organizer):
    org = logged_organizer.id
    ev = lab.event("sql-chuoi", organizer_id=org)
    d0 = TODAY - timedelta(days=6)
    plan = {0: [1], 1: [], 2: [2, 1], 3: [3], 4: [], 5: [], 6: [1]}  # ngày → số vé từng đơn
    for k, qtys in plan.items():
        for q in qtys:
            lab.order(ev, vn(d0 + timedelta(days=k), 10), qty=q)
    with Session(lab.db.get_bind()) as s:
        rep = org_reports.report(s, org, day_from=d0, day_to=TODAY, event_id=None, group_by="day")
    rev = [sum(plan[k]) * 200000 for k in range(7)]
    assert [x["revenue"] for x in rep["series"]] == rev
    assert [x["orders"] for x in rep["series"]] == [len(plan[k]) for k in range(7)]
    running = [sum(rev[:i + 1]) for i in range(7)]
    assert [x["cumulative"] for x in rep["series"]] == running
    expect = [None] + [round(100 * (rev[i] - rev[i - 1]) / rev[i - 1], 1) if rev[i - 1] else None for i in range(1, 7)]
    assert [x["changePct"] for x in rep["series"]] == expect


def test_q4_event_ranking_ties(lab, logged_organizer):
    org = logged_organizer.id
    evs = [lab.event(f"sql-hang-{i}", organizer_id=org) for i in range(3)]
    when = vn(TODAY - timedelta(days=1))
    for ev, qty in zip(evs, (2, 2, 1)):
        lab.order(ev, when, qty=qty)
    with Session(lab.db.get_bind()) as s:
        rep = org_reports.report(s, org, day_from=TODAY - timedelta(days=7), day_to=TODAY, event_id=None, group_by="day")
    rows = {e["eventId"]: e for e in rep["byEvent"]}
    assert [rows[e.id]["rank"] for e in evs] == [1, 1, 3]  # RANK: bằng nhau cùng hạng, hạng sau nhảy
    assert [rows[e.id]["percentRank"] for e in evs] == [0.0, 0.0, 1.0]
    assert rows[evs[0].id]["fee"] == manage.fee_of(400000) and rows[evs[0].id]["net"] == 400000 - manage.fee_of(400000)


def test_q5_tier_revenue_share_and_fill(lab, logged_organizer):
    org = logged_organizer.id
    ev = lab.event("sql-hang-ve", organizer_id=org)
    lab.db.add(TicketTier(event_id=ev.id, id="ve-2", name="VIP", price=600000, capacity=20, max_per_order=10,
                          sort_order=2))
    lab.db.commit()
    when = vn(TODAY - timedelta(days=1))
    lab.order(ev, when, qty=3)  # 600 000
    lab.order(ev, when, qty=1, tier="ve-2")  # 600 000
    with Session(lab.db.get_bind()) as s:
        rep = org_reports.report(s, org, day_from=TODAY - timedelta(days=7), day_to=TODAY, event_id=ev.id, group_by="day")
        stats = tier_stats(s, [s.get(Event, ev.id)])
    tiers = {t["tierId"]: t for t in rep["byTier"]}
    assert tiers["ve-1"]["revenueShare"] == tiers["ve-2"]["revenueShare"] == 50.0
    for tid in ("ve-1", "ve-2"):
        st = stats[(ev.id, tid)]
        assert tiers[tid]["capacity"] == st.capacity
        assert tiers[tid]["fillRate"] == round(100 * (st.presold + st.sold) / st.capacity, 1)


def test_q6_top_customers_dense_rank(lab, logged_organizer, c):
    org = logged_organizer.id
    mine, other = lab.event("sql-khach-top", organizer_id=org), lab.event("sql-khach-top-khac")
    when = vn(TODAY - timedelta(days=2))
    lab.order(mine, when, qty=3, buyer=0)
    lab.order(mine, when, qty=3, buyer=1)
    lab.order(mine, when, qty=1, buyer=2)
    lab.order(mine, when, qty=1, buyer=2)
    lab.order(other, when, qty=9, buyer=3)  # BTC khác — bảng xếp hạng riêng
    r = c.get("/api/organizer/top-customers")
    assert r.status_code == 200, r.text
    rows = r.json()["customers"]
    by_email = {x["email"]: x for x in rows}
    em = [b.email for b in lab.customers]
    assert by_email[em[0]]["rank"] == by_email[em[1]]["rank"] == 1 and by_email[em[2]]["rank"] == 2  # DENSE_RANK
    assert by_email[em[2]]["orders"] == 2 and by_email[em[2]]["spent"] == 400000
    assert em[3] not in by_email
    with Session(lab.db.get_bind()) as s:
        allp = org_reports.top_customers(s, None, day_from=TODAY - timedelta(days=7), day_to=TODAY)
    other_rows = [x for x in allp if x["organizerId"] == other.organizer_id]
    assert [x["rank"] for x in other_rows] == [1]  # mỗi BTC xếp hạng từ 1
    assert c.get("/api/organizer/top-customers", params={"from": "2026-13-01"}).status_code == 400


def test_q7_stale_events(lab, logged_admin, c):
    now = datetime.now(timezone.utc)
    recent = lab.event("sql-dung-ban-gan")
    lab.order(recent, now - timedelta(days=2))
    old = lab.event("sql-dung-ban-cu")
    old_order = lab.order(old, now - timedelta(days=10))
    none = lab.event("sql-dung-chua-ban")
    ended = lab.event("sql-dung-da-dien", days=-3)
    upcoming = lab.event("sql-dung-sap-mo")
    upcoming_ev = lab.db.get(Event, upcoming.id)
    upcoming_ev.sale_start = now + timedelta(days=2)
    cancelled = lab.db.get(Event, lab.event("sql-dung-da-huy").id)
    cancelled.status, cancelled.cancel_reason, cancelled.cancelled_at, cancelled.cancelled_by = "cancelled", "x", now, "admin"
    lab.db.commit()
    r = c.get("/api/admin/events/stale", params={"days": 7})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["days"] == 7
    got = [e for e in body["events"] if e["slug"].startswith("sql-dung-")]
    assert [e["slug"] for e in got] == ["sql-dung-chua-ban", "sql-dung-ban-cu"]  # chưa bán lần nào lên đầu
    assert got[0]["lastSaleAt"] is None and got[1]["lastSaleAt"] == iso_vn(old_order.created_at)
    assert set(got[0]) >= {"id", "slug", "title", "orgName", "saleOpensAt", "startsAt", "lastSaleAt"}
    for bad in ("0", "91", "abc"):
        r = c.get("/api/admin/events/stale", params={"days": bad})
        assert r.status_code == 400 and r.json() == {"error": "Số ngày không hợp lệ"}
    _ = (recent, none, ended)


def _python_balances(db: Session, org_ids: list[int]) -> dict[int, dict]:
    """Cách tính độc lập (bản Python của Task E1) để đối chiếu Q8"""
    from sqlalchemy import func

    out = {o: {"settledNet": 0, "held": 0, "pending": 0, "paid": 0} for o in org_ids}
    now = manage.now_utc()
    for e in db.scalars(select(Event).where(Event.organizer_id.in_(org_ids))):
        r = int(db.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.event_id == e.id,
                                                                               Order.status == "paid")))
        last = db.scalar(select(func.max(Show.starts_at)).where(Show.event_id == e.id))
        phase = manage.phase_of(e, last, now)
        if not r:
            continue
        net = r - manage.fee_of(r)
        if phase == "ended":
            out[e.organizer_id]["settledNet"] += net
        elif phase != "cancelled":
            out[e.organizer_id]["held"] += net
    for w in db.scalars(select(Withdrawal).where(Withdrawal.organizer_id.in_(org_ids))):
        if w.status in ("pending", "paid"):
            out[w.organizer_id][w.status] += w.amount
    for b in out.values():
        b["available"] = max(b["settledNet"] - b["pending"] - b["paid"], 0)
    return out


def test_q8_balance_matches_python(lab):
    e1 = lab.event("sql-so-du-1", days=-5)
    e2 = lab.event("sql-so-du-2", organizer_id=e1.organizer_id, days=10)
    e3 = lab.event("sql-so-du-3", days=-2)
    now = datetime.now(timezone.utc)
    for ev, q in ((e1, 3), (e2, 2), (e3, 1)):
        lab.order(ev, now - timedelta(days=8), qty=q)
        lab.order(ev, now - timedelta(days=9), qty=1, status="refunded")
    o = lab.db
    o.add_all([Withdrawal(organizer_id=e1.organizer_id, amount=100000, bank_name="ACB", account_no="123456", account_name="A"),
               Withdrawal(organizer_id=e1.organizer_id, amount=50000, bank_name="ACB", account_no="123456",
                          account_name="A", status="paid", processed_at=now),
               Withdrawal(organizer_id=e1.organizer_id, amount=70000, bank_name="ACB", account_no="123456",
                          account_name="A", status="rejected", processed_at=now, note="Sai")])
    o.commit()
    orgs = [e1.organizer_id, e3.organizer_id]
    with Session(lab.db.get_bind()) as s:
        assert withdrawals.balances(s, orgs) == _python_balances(s, orgs)
        assert withdrawals.balances(s, None)[e3.organizer_id] == _python_balances(s, orgs)[e3.organizer_id]
