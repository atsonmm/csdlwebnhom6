"""Nạp catalog.json vào PostgreSQL. Các test này COMMIT thật nên dọn sạch trước và sau mỗi test."""
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import Event, HomeSlot, MapSeat, Show
from app.models.sales import SeatHold, TierStock
from app.models.users import Organizer, User
from app.seed import ensure_admin, load_catalog, reset_all
from tests.conftest import event_kwargs

CAT = json.loads((Path(__file__).resolve().parent.parent / "seed/catalog.json").read_text(encoding="utf-8"))
TINH_HA = "concert-dem-4-hen-giua-tinh-ha"


@pytest.fixture
def sdb(engine, schema):
    with Session(engine) as s:
        reset_all(s)
        s.commit()
        yield s
        s.rollback()
        reset_all(s)
        s.commit()


@pytest.fixture
def seeded(sdb):
    load_catalog(sdb, CAT)
    sdb.commit()
    return sdb


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def make_org_event(db) -> Event:
    u = User(name="BTC", email="btc@x.vn", password_hash="h", role="organizer")
    db.add(u)
    db.flush()
    db.add(Organizer(user_id=u.id, org_name="Đơn vị BTC", phone="0912345678"))
    db.flush()
    e = Event(**event_kwargs("nhac-song", slug="su-kien-cua-btc", organizer_id=u.id, status="pending"))
    db.add(e)
    db.flush()
    return e


def test_counts_match_catalog(seeded):
    assert count(seeded, Event) == len(CAT["events"])
    assert count(seeded, HomeSlot) == len(CAT["homeSlots"])
    assert count(seeded, MapSeat) == sum(len(m["seats"]) for m in CAT["maps"])
    assert count(seeded, SeatHold) == sum(len(e["presoldSeats"]) for e in CAT["events"])


def test_vietnamese_text_round_trips(seeded):
    titles = set(seeded.scalars(select(Event.title)))
    assert "Concert Đêm 4: Hẹn Giữa Tinh Hà" in titles
    assert "Nhạc kịch “Phố Đèn Lồng”" in titles


def test_show_time_is_stored_as_correct_instant(seeded):
    s = seeded.scalars(select(Show).join(Event, Event.id == Show.event_id).where(Event.slug == TINH_HA)).first()
    local = s.starts_at.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    assert s.id == local.strftime("%Y%m%d-%H%M")


def test_reseed_preserves_ids_and_real_sales(seeded):
    ev = seeded.scalar(select(Event).where(Event.slug == TINH_HA))
    ev_id = ev.id
    stock = seeded.scalars(select(TierStock).where(TierStock.event_id == ev_id)).first()
    key = (stock.event_id, stock.show_id, stock.tier_id)
    stock.sold = min(3, stock.capacity - stock.presold)
    sold = stock.sold
    org_ev = make_org_event(seeded)
    org_id = org_ev.id
    seeded.commit()

    load_catalog(seeded, CAT)
    seeded.commit()
    seeded.expire_all()
    assert seeded.scalar(select(Event.id).where(Event.slug == TINH_HA)) == ev_id
    assert seeded.get(TierStock, key).sold == sold
    assert seeded.get(Event, org_id) is not None
    assert count(seeded, Event) == len(CAT["events"]) + 1


def test_sale_start_loaded_for_coming_events(seeded):
    coming = [e for e in CAT["events"] if e["saleStart"]]
    assert coming, "catalog phải có sự kiện sắp mở bán"
    ev = seeded.scalar(select(Event).where(Event.slug == coming[0]["slug"]))
    assert ev.sale_start is not None


def test_reset_all_empties_everything(seeded):
    reset_all(seeded)
    seeded.commit()
    assert count(seeded, Event) == 0
    assert count(seeded, SeatHold) == 0


def test_admin_created_once(sdb):
    ensure_admin(sdb)
    ensure_admin(sdb)
    sdb.commit()
    assert sdb.scalar(select(func.count()).select_from(User).where(User.role == "admin")) == 1


# ---------------------------------------------------------------------------
# Dòng bị bỏ khỏi catalog: chưa ai mua → xoá; đã có đơn → giữ lại nhưng ngừng bán (active = false)
# ---------------------------------------------------------------------------
import copy  # noqa: E402

from app.models.catalog import TicketTier  # noqa: E402
from app.models.sales import Order, OrderItem  # noqa: E402

MULTI_SHOW = next(e for e in CAT["events"] if len(e["shows"]) >= 2 and len(e["tiers"]) >= 2 and e["layout"] != "seats")


def paid_order(db, slug: str, show_id: str, tier_id: str) -> None:
    u = User(name="Khách", email=f"{slug[:20]}-{show_id}@x.vn", password_hash="h")
    db.add(u)
    db.flush()
    eid = db.scalar(select(Event.id).where(Event.slug == slug))
    price = db.get(TicketTier, (eid, tier_id)).price
    o = Order(id=f"TN-{abs(hash((slug, show_id))) % 10**7:07d}", user_id=u.id, event_id=eid, show_id=show_id,
              subtotal=price, discount=0, total=price, method="qr", buyer_name="B", buyer_email="b@x.vn",
              buyer_phone="0912345678")
    db.add(o)
    db.flush()
    db.add(OrderItem(order_id=o.id, event_id=eid, tier_id=tier_id, price=price, qty=1))
    db.commit()


def without_event(slug: str) -> dict:
    cat = copy.deepcopy(CAT)
    cat["events"] = [e for e in cat["events"] if e["slug"] != slug]
    cat["homeSlots"] = [s for s in cat["homeSlots"] if s["slug"] != slug]
    return cat


def test_removed_event_without_orders_is_deleted(seeded):
    slug = MULTI_SHOW["slug"]
    load_catalog(seeded, without_event(slug))
    seeded.commit()
    assert seeded.scalar(select(Event).where(Event.slug == slug)) is None


def test_removed_event_with_orders_is_kept_inactive(seeded):
    slug = MULTI_SHOW["slug"]
    paid_order(seeded, slug, MULTI_SHOW["shows"][0]["id"], MULTI_SHOW["tiers"][0]["id"])
    load_catalog(seeded, without_event(slug))
    seeded.commit()
    ev = seeded.scalar(select(Event).where(Event.slug == slug))
    assert ev is not None and ev.active is False


def test_removed_show_and_tier_with_orders_are_inactive_until_restored(seeded):
    slug, show_id, tier_id = MULTI_SHOW["slug"], MULTI_SHOW["shows"][0]["id"], MULTI_SHOW["tiers"][0]["id"]
    paid_order(seeded, slug, show_id, tier_id)
    cat = copy.deepcopy(CAT)
    ev_json = next(e for e in cat["events"] if e["slug"] == slug)
    ev_json["shows"] = ev_json["shows"][1:]
    ev_json["tiers"] = ev_json["tiers"][1:]
    ev_json["presold"] = [p for p in ev_json["presold"] if p["showId"] != show_id and p["tierId"] != tier_id]
    load_catalog(seeded, cat)
    seeded.commit()
    eid = seeded.scalar(select(Event.id).where(Event.slug == slug))
    assert seeded.get(Show, (eid, show_id)).active is False
    assert seeded.get(TicketTier, (eid, tier_id)).active is False

    load_catalog(seeded, CAT)  # đưa trở lại catalog → bán tiếp
    seeded.commit()
    seeded.expire_all()
    assert seeded.get(Show, (eid, show_id)).active is True
    assert seeded.get(TicketTier, (eid, tier_id)).active is True


# ---------------------------------------------------------------------------
# --demo: đơn mẫu rải trong 7 ngày (tạo qua chính create_order), chạy lại thì thay thế
# ---------------------------------------------------------------------------
from sqlalchemy import text  # noqa: E402

from app.models.sales import Ticket  # noqa: E402
from app.seed import load_demo  # noqa: E402


def test_demo_orders_spread_over_7_days_and_rerun_replaces(seeded):
    n = load_demo(seeded)
    seeded.commit()
    days = {d for (d,) in seeded.execute(text("SELECT DISTINCT day FROM v_daily_revenue"))}
    assert n > 0 and len(days) == 7
    sold = seeded.scalar(select(func.sum(TierStock.sold)))
    assert sold > 0

    assert load_demo(seeded) == n
    seeded.commit()
    assert count(seeded, Order) == n                                  # không nhân đôi
    assert seeded.scalar(select(func.sum(TierStock.sold))) == sold    # kho trả lại rồi trừ lại đúng bằng nhau


def test_demo_orders_are_consistent(seeded):
    load_demo(seeded)
    seeded.commit()
    for o in seeded.scalars(select(Order)):
        assert o.total == o.subtotal - o.discount
        qty = seeded.scalar(select(func.sum(OrderItem.qty)).where(OrderItem.order_id == o.id))
        assert seeded.scalar(select(func.count()).select_from(Ticket).where(Ticket.order_id == o.id)) == qty
    sold_total = seeded.scalar(select(func.sum(TierStock.sold)))
    items_total = seeded.scalar(select(func.sum(OrderItem.qty)))
    assert sold_total == items_total  # đơn demo chỉ ở sự kiện bán theo loại vé / khu


def test_demo_does_not_touch_real_customer_orders(seeded):
    load_demo(seeded)
    seeded.commit()
    real = User(name="Khách thật", email="that@khach.vn", password_hash="h")
    seeded.add(real)
    seeded.flush()
    o = seeded.scalars(select(Order)).first()
    keep = Order(id="TNREAL0001", user_id=real.id, event_id=o.event_id, show_id=o.show_id, subtotal=0, discount=0,
                 total=0, method="qr", buyer_name="B", buyer_email="b@x.vn", buyer_phone="0912345678")
    seeded.add(keep)
    seeded.commit()
    load_demo(seeded)
    seeded.commit()
    assert seeded.get(Order, "TNREAL0001") is not None


def test_demo_rerun_does_not_return_stock_twice_for_refunded_orders(seeded):
    """Đơn đã hoàn tiền đã tự trả kho — --demo chạy lại không được trả kho lần nữa"""
    load_demo(seeded)
    seeded.commit()
    refunded = seeded.scalars(select(Order).order_by(Order.id)).first()
    for it in seeded.scalars(select(OrderItem).where(OrderItem.order_id == refunded.id)):
        stock = seeded.get(TierStock, (refunded.event_id, refunded.show_id, it.tier_id))
        stock.sold -= it.qty  # mô phỏng hoàn tiền: trả kho
    refunded.status = "refunded"
    seeded.commit()

    load_demo(seeded)
    seeded.commit()
    paid_qty = seeded.scalar(select(func.sum(OrderItem.qty)).join(Order, Order.id == OrderItem.order_id)
                             .where(Order.status == "paid"))
    assert seeded.scalar(select(func.sum(TierStock.sold))) == paid_qty
