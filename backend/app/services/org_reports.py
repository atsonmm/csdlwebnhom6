"""Báo cáo doanh thu: Ban tổ chức (organizer_id) hoặc toàn sàn (organizer_id=None, dùng cho Admin).
Doanh thu = tổng orders.total của đơn 'paid', gom theo NGÀY MUA giờ VN. Đơn hoàn đếm riêng theo ngày mua."""
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.services import sql_queries

from app.models.catalog import Event, TicketTier
from app.models.sales import Order, OrderItem, Ticket
from app.models.users import Organizer
from app.services.manage import fee_of
from app.services.org_orders import ID_RE, own_event, parse_day, vn_start
from app.services.stock import tier_stats
from app.utils.timefmt import VN, iso_vn
from app.utils.validators import as_str

GROUPS = ("day", "week", "month")
MAX_DAYS = 366
DEFAULT_DAYS = 30


def parse_report_params(*, day_from: Any, day_to: Any, event_id: Any, group_by: Any) -> dict:
    group = as_str(group_by).strip() or "day"
    if group not in GROUPS:
        raise HTTPException(400, "Kiểu gom nhóm không hợp lệ")
    d0, d1 = parse_day(day_from, "from"), parse_day(day_to, "to")
    eid = as_str(event_id).strip()
    if eid and (not ID_RE.match(eid) or int(eid) > 2_147_483_647):
        raise HTTPException(400, "Mã sự kiện không hợp lệ")
    today = datetime.now(VN).date()
    d1 = d1 or (today if d0 is None or d0 <= today else d0)
    d0 = d0 or d1 - timedelta(days=DEFAULT_DAYS - 1)
    if d0 > d1:
        raise HTTPException(400, "Khoảng ngày không hợp lệ")
    if (d1 - d0).days + 1 > MAX_DAYS:
        raise HTTPException(400, f"Khoảng báo cáo tối đa {MAX_DAYS} ngày")
    return {"day_from": d0, "day_to": d1, "event_id": int(eid) if eid else None, "group_by": group}


def _bucket_start(d: date, group: str) -> date:
    if group == "week":
        return d - timedelta(days=d.weekday())
    if group == "month":
        return d.replace(day=1)
    return d


def _next(d: date, group: str) -> date:
    if group == "day":
        return d + timedelta(days=1)
    if group == "week":
        return d + timedelta(days=7)
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def _key_label(d: date, group: str) -> tuple[str, str]:
    if group == "month":
        return d.strftime("%Y-%m"), d.strftime("%m/%Y")
    if group == "week":
        return d.isoformat(), f"T {d.strftime('%d/%m')}"
    return d.isoformat(), d.strftime("%d/%m")


PLATFORM_NAME = "Sàn TicketNhịp"


def report(db: Session, organizer_id: int | None, *, day_from: date, day_to: date, event_id: int | None,
           group_by: str, filter_organizer: int | None = None) -> dict:
    """organizer_id=None → toàn sàn (Admin): thêm byOrganizer + totals.platformRevenue; filter_organizer lọc một BTC"""
    platform = organizer_id is None
    if event_id is not None and not platform:
        own_event(db, organizer_id, event_id)
    scope = [Order.created_at >= vn_start(day_from), Order.created_at < vn_start(day_to + timedelta(days=1))]
    owner = filter_organizer if platform else organizer_id
    if owner is not None:
        scope.append(Event.organizer_id == owner)
    if event_id is not None:
        scope.append(Order.event_id == event_id)
    paid = [*scope, Order.status == "paid"]

    def orders_q(*cols):
        return select(*cols).select_from(Order).join(Event, Event.id == Order.event_id)

    params = {"t0": vn_start(day_from), "t1": vn_start(day_to + timedelta(days=1)), "org": owner, "event": event_id}

    # ---- theo sự kiện, kèm thứ hạng (Q4 event_ranking.sql: RANK / PERCENT_RANK)
    by_event = []
    gross = discount = 0
    for r in sql_queries.run(db, "event_ranking", **params):
        rev = int(r["revenue"])
        fee = fee_of(rev) if r["organizer_id"] is not None else 0  # sự kiện sàn tự bán không thu phí
        gross += int(r["gross"])
        discount += int(r["discount"])
        by_event.append({"eventId": r["event_id"], "title": r["title"], "organizerId": r["organizer_id"],
                         "revenue": rev, "tickets": int(r["tickets"]), "orders": int(r["orders"]), "fee": fee,
                         "net": rev - fee, "rank": int(r["rank"]), "percentRank": float(r["percent_rank"])})
    revenue = sum(e["revenue"] for e in by_event)
    fee = sum(e["fee"] for e in by_event)
    refunded_orders, refunded_amount = db.execute(
        orders_q(func.count(), func.coalesce(func.sum(Order.total), 0)).where(*scope, Order.status == "refunded")).one()

    # ---- theo thời gian: mốc lấp đủ (Q2 revenue_series.sql) + luỹ kế / so với kỳ trước (Q3 revenue_running.sql)
    span = {"unit": group_by, "d0": day_from, "d1": day_to, **params}
    running = {r["bucket"]: r for r in sql_queries.run(db, "revenue_running", **span)}
    series = []
    for r in sql_queries.run(db, "revenue_series", **span):
        key, label = _key_label(r["bucket"], group_by)
        run_row = running[r["bucket"]]
        series.append({"key": key, "label": label, "revenue": int(r["revenue"]), "tickets": int(r["tickets"]),
                       "orders": int(r["orders"]), "cumulative": int(run_row["cumulative"]),
                       "changePct": float(run_row["change_pct"]) if run_row["change_pct"] is not None else None})

    # ---- theo hạng vé (Q5 tier_sell_through.sql); sức chứa / lấp đầy từ kho chung stock.tier_stats
    tier_rows = sql_queries.run(db, "tier_sell_through", **params)
    events = db.scalars(select(Event).where(Event.id.in_({r["event_id"] for r in tier_rows} or {-1}))).all()
    stats = tier_stats(db, list(events))
    by_tier = []
    for r in tier_rows:
        st = stats.get((r["event_id"], r["tier_id"]))
        cap = st.capacity if st else 0
        by_tier.append({
            "eventId": r["event_id"], "eventTitle": r["event_title"], "tierId": r["tier_id"], "tierName": r["tier_name"],
            "price": r["price"], "capacity": cap, "sold": int(r["sold"]), "revenue": int(r["revenue"]),
            "revenueShare": float(r["revenue_share"]) if r["revenue_share"] is not None else 0.0,
            "fillRate": round(100 * (st.presold + st.sold) / cap, 1) if st and cap else 0.0,
        })

    out = {
        "range": {"from": day_from.isoformat(), "to": day_to.isoformat(), "groupBy": group_by},
        "totals": {"gross": gross, "discount": discount, "revenue": revenue, "fee": fee, "net": revenue - fee,
                   "orders": sum(e["orders"] for e in by_event), "tickets": sum(e["tickets"] for e in by_event),
                   "refundedOrders": int(refunded_orders), "refundedAmount": int(refunded_amount)},
        "series": series,
        "byEvent": [{k: v for k, v in e.items() if k != "organizerId"} for e in by_event],
        "byTier": by_tier,
    }
    if platform:
        out["byOrganizer"] = _by_organizer(db, by_event)
        out["totals"]["platformRevenue"] = sum(e["revenue"] for e in by_event if e["organizerId"] is None)
    return out


def _by_organizer(db: Session, by_event: list[dict]) -> list[dict]:
    """Gom byEvent theo Ban tổ chức; sự kiện sàn tự bán là một dòng organizerId=None, phí 0"""
    agg: dict[int | None, dict] = {}
    for e in by_event:
        a = agg.setdefault(e["organizerId"], {"revenue": 0, "fee": 0, "tickets": 0, "orders": 0})
        for k in a:
            a[k] += e[k]
    names = dict(db.execute(select(Organizer.user_id, Organizer.org_name)
                            .where(Organizer.user_id.in_([k for k in agg if k is not None] or [-1]))).all())
    rows = [{"organizerId": k, "orgName": names.get(k) if k is not None else PLATFORM_NAME, **a,
             "net": a["revenue"] - a["fee"]} for k, a in agg.items()]
    return sorted(rows, key=lambda r: (-r["revenue"], r["organizerId"] is None, r["organizerId"] or 0))


TOP_CUSTOMERS = 10


def top_customers(db: Session, organizer_id: int | None, *, day_from: date, day_to: date,
                  top: int = TOP_CUSTOMERS) -> list[dict]:
    """Khách chi nhiều nhất cho từng BTC (Q6 top_customers.sql, DENSE_RANK theo từng BTC); organizer_id=None → mọi BTC"""
    rows = sql_queries.run(db, "top_customers", t0=vn_start(day_from), t1=vn_start(day_to + timedelta(days=1)),
                           org=organizer_id, top=top)
    return [{"organizerId": r["organizer_id"], "rank": int(r["rank"]), "userId": r["user_id"], "name": r["name"],
             "email": r["email"], "phone": r["phone"], "orders": int(r["orders"]), "tickets": int(r["tickets"]),
             "spent": int(r["spent"]), "lastOrderAt": iso_vn(r["last_order_at"])} for r in rows]
