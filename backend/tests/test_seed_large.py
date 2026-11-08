"""Task G1 — bộ sinh dữ liệu lớn (chạy scale nhỏ trên CSDL test): đúng ràng buộc, kho khớp vé, số dư rút tiền hợp lệ,
chạy lại không nhân đôi, không chạm dữ liệu catalog/demo"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import seed_large
from app.services import checkin, manage, withdrawals

SCALE = 0.01
MARK = seed_large.EMAIL_DOMAIN


@pytest.fixture(scope="module")
def big(engine, api_db):
    """api_db đã nạp catalog (có thể loại, mã giảm giá) — sinh một lần cho cả module, dọn khi xong"""
    with Session(engine) as s:
        added = seed_large.generate(s, scale=SCALE, seed=42)
        s.commit()
    yield added
    with Session(engine) as s:
        seed_large.clear(s)
        s.commit()


def q(engine, sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).all()


def test_generate_reports_rows(big):
    assert big["orders"] == round(100_000 * SCALE)
    assert big["users"] >= round(12_000 * SCALE)
    assert big["order_items"] >= big["orders"] and big["tickets"] >= 2 * big["orders"]
    assert big["events"] >= 20 and big["withdrawals"] > 0


def test_constraints_hold(big, engine):
    # mọi CHECK/FK đã được CSDL kiểm khi chèn; kiểm thêm các quy tắc nghiệp vụ không viết được bằng CHECK
    assert q(engine, "SELECT count(*) FROM orders WHERE id LIKE 'TL%' AND total <> subtotal - discount")[0][0] == 0
    assert q(engine, """SELECT count(*) FROM orders o WHERE o.id LIKE 'TL%' AND o.subtotal <>
                        (SELECT sum(i.price * i.qty) FROM order_items i WHERE i.order_id = o.id)""")[0][0] == 0
    assert q(engine, """SELECT count(*) FROM orders o WHERE o.id LIKE 'TL%' AND
                        (SELECT count(*) FROM tickets t WHERE t.order_id = o.id) <>
                        (SELECT sum(i.qty) FROM order_items i WHERE i.order_id = o.id)""")[0][0] == 0
    # mua trước giờ diễn, trong cửa sổ 365 ngày, sau khi sàn duyệt
    assert q(engine, """SELECT count(*) FROM orders o JOIN shows s ON s.event_id = o.event_id AND s.id = o.show_id
                        JOIN events e ON e.id = o.event_id
                        WHERE o.id LIKE 'TL%' AND (o.created_at >= s.starts_at OR o.created_at > now()
                          OR o.created_at < now() - interval '366 days' OR o.created_at < e.reviewed_at)""")[0][0] == 0
    # sự kiện đã huỷ: mọi đơn đã hoàn; hoàn tiền sau khi mua
    assert q(engine, """SELECT count(*) FROM orders o JOIN events e ON e.id = o.event_id
                        WHERE o.id LIKE 'TL%' AND e.status = 'cancelled' AND o.status <> 'refunded'""")[0][0] == 0
    assert q(engine, "SELECT count(*) FROM orders WHERE id LIKE 'TL%' AND status = 'refunded' "
                     "AND (refunded_at IS NULL OR refunded_at < created_at)")[0][0] == 0
    # chưa duyệt / bị trả lại / chưa mở bán thì không có đơn
    assert q(engine, """SELECT count(*) FROM orders o JOIN events e ON e.id = o.event_id
                        WHERE o.id LIKE 'TL%' AND (e.status IN ('pending','rejected')
                          OR coalesce(e.sale_start, e.reviewed_at) > o.created_at)""")[0][0] == 0
    # soát vé chỉ ở sự kiện đã diễn, quanh giờ diễn
    assert q(engine, """SELECT count(*) FROM tickets t JOIN orders o ON o.id = t.order_id
                        JOIN shows s ON s.event_id = o.event_id AND s.id = o.show_id
                        WHERE o.id LIKE 'TL%' AND t.checked_in_at IS NOT NULL
                          AND (s.starts_at > now() OR o.status <> 'paid'
                               OR t.checked_in_at NOT BETWEEN s.starts_at - interval '3 hours' AND s.starts_at + interval '1 hour')""")[0][0] == 0


def test_ticket_codes_scannable(big, engine):
    codes = [r[0] for r in q(engine, "SELECT code FROM tickets WHERE order_id LIKE 'TL%' LIMIT 500")]
    assert codes and all(checkin.CODE_RE.match(c) for c in codes)


def test_all_phases_present(big, engine):
    from app.models.catalog import Event, Show
    from sqlalchemy import func, select

    with Session(engine) as s:
        evs = s.scalars(select(Event).where(Event.slug.like(f"{seed_large.SLUG_PREFIX}%"))).all()
        last = dict(s.execute(select(Show.event_id, func.max(Show.starts_at)).group_by(Show.event_id)).all())
        now = manage.now_utc()
        phases = {manage.phase_of(e, last.get(e.id), now) for e in evs}
    assert {"pending", "rejected", "cancelled", "upcoming-sale", "on-sale", "ended"} <= phases


def test_checked_in_share_of_ended(big, engine):
    total, checked = q(engine, """SELECT count(*), count(t.checked_in_at) FROM tickets t
                                  JOIN orders o ON o.id = t.order_id JOIN shows s ON s.event_id = o.event_id AND s.id = o.show_id
                                  WHERE o.id LIKE 'TL%' AND o.status = 'paid' AND s.starts_at < now() - interval '1 day'""")[0]
    assert total > 0 and 0.55 <= checked / total <= 0.85


def test_stock_matches_sold_tickets(big, engine):
    bad = q(engine, """SELECT st.event_id, st.tier_id, st.sold, coalesce(c.n, 0)
                       FROM tier_stock st JOIN events e ON e.id = st.event_id
                       LEFT JOIN (SELECT t.event_id, t.tier_id, count(*) n FROM tickets t JOIN orders o ON o.id = t.order_id
                                  WHERE o.status IN ('paid','refunded') GROUP BY 1, 2) c
                              ON c.event_id = st.event_id AND c.tier_id = st.tier_id
                       WHERE e.slug LIKE :p AND st.sold <> coalesce(c.n, 0)""", p=f"{seed_large.SLUG_PREFIX}%")
    assert bad == []


def test_withdrawals_never_exceed_settled_net(big, engine):
    with Session(engine) as s:
        orgs = [r[0] for r in s.execute(text("SELECT user_id FROM organizers o JOIN users u ON u.id = o.user_id "
                                             "WHERE u.email LIKE :m"), {"m": f"%{MARK}"})]
        bal = withdrawals.balances(s, orgs)
    assert orgs
    for b in bal.values():
        assert b["pending"] + b["paid"] <= b["settledNet"]
    statuses = {r[0] for r in q(engine, "SELECT DISTINCT w.status FROM withdrawals w JOIN users u ON u.id = w.organizer_id "
                                        "WHERE u.email LIKE :m", m=f"%{MARK}")}
    assert statuses == {"pending", "paid", "rejected"}


def test_rerun_is_idempotent_and_demo_untouched(big, engine):
    def outside():
        return q(engine, f"""SELECT (SELECT count(*) FROM users WHERE email IS NULL OR email NOT LIKE '%{MARK}'),
                                    (SELECT count(*) FROM events WHERE slug NOT LIKE '{seed_large.SLUG_PREFIX}%'),
                                    (SELECT count(*) FROM orders WHERE id NOT LIKE 'TL%'),
                                    (SELECT coalesce(sum(sold), 0) FROM tier_stock st JOIN events e ON e.id = st.event_id
                                     WHERE e.slug NOT LIKE '{seed_large.SLUG_PREFIX}%')""")[0]

    with Session(engine) as s:
        before_all, before_out = seed_large.row_counts(s), outside()
        seed_large.generate(s, scale=SCALE, seed=42)
        s.commit()
        assert seed_large.row_counts(s) == before_all
    assert outside() == before_out


def test_counts_scale_linearly(big, engine):
    with Session(engine) as s:
        double = seed_large.generate(s, scale=2 * SCALE, seed=42)
        s.commit()
    try:
        assert double["orders"] == 2 * big["orders"]
        assert double["users"] - double["organizers"] == 2 * (big["users"] - big["organizers"])  # khách
        assert 1.6 <= double["tickets"] / big["tickets"] <= 2.4
    finally:
        with Session(engine) as s:  # trả về bộ scale gốc cho các test khác (nếu chạy sau)
            seed_large.generate(s, scale=SCALE, seed=42)
            s.commit()
