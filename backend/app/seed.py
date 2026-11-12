"""Nạp danh mục sự kiện (seed/catalog.json) vào PostgreSQL.

    python -m app.seed            # upsert: chạy lại bao nhiêu lần cũng an toàn
    python -m app.seed --reset    # xoá SẠCH mọi dữ liệu (kể cả người dùng, đơn hàng) rồi nạp lại

Upsert theo khoá tự nhiên (slug, mã suất, mã hạng, mã ghế): giữ nguyên events.id,
số vé đã bán thật (tier_stock.sold, seat_holds có order_id), người dùng, đơn hàng
và sự kiện do Ban tổ chức tạo. Chỉ làm mới thông tin mô tả và số vé "đã bán sẵn".
"""
import argparse
import json
import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path

from sqlalchemy import and_, delete, exists, func, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.config.database import Base, make_engine
from app.models.catalog import Category, Event, HomeSlot, MapGroup, MapSeat, MapZone, Show, TicketTier, VenueMap
from app.models.sales import Coupon, OrderItem, Order, SeatHold, TierStock, Ticket
from app.models.users import User
from app.utils.security import hash_password

CATALOG_FILE = Path(__file__).resolve().parent.parent / "seed" / "catalog.json"
DEV_ADMIN_PASSWORD = "admin123456"


@dataclass
class SeedReport:
    events: int = 0
    shows: int = 0
    tiers: int = 0
    seats: int = 0
    slots: int = 0

    def __str__(self) -> str:
        return f"{self.events} sự kiện · {self.shows} suất · {self.tiers} hạng vé · {self.seats} ghế · {self.slots} vị trí trang chủ"


def _upsert(db: Session, model, rows: list[dict], keys: list[str], update: list[str] | None = None) -> None:
    """INSERT ... ON CONFLICT (keys) DO UPDATE SET <update>"""
    if not rows:
        return
    stmt = insert(model).values(rows)
    cols = update if update is not None else [c for c in rows[0] if c not in keys]
    if cols:
        stmt = stmt.on_conflict_do_update(index_elements=keys, set_={c: stmt.excluded[c] for c in cols})
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=keys)
    db.execute(stmt)


def _load_maps(db: Session, maps: list[dict]) -> int:
    seats = 0
    for m in maps:
        _upsert(db, VenueMap, [dict(id=m["id"], kind=m["kind"], name=m["name"], view_box=m["viewBox"], decor=m["display"])], ["id"])
        groups = [dict(map_id=m["id"], id=g["id"], label=g["label"], color=g["color"], ink=g["ink"],
                       max_per_order=g["maxPerOrder"], perks=g["perks"], sort_order=i) for i, g in enumerate(m["groups"])]
        _upsert(db, MapGroup, groups, ["map_id", "id"])
        zones = [dict(map_id=m["id"], id=z["id"], label=z["label"], group_id=z["groupId"], capacity=z["capacity"],
                      shape=z["shape"], text=z["text"], sort_order=i) for i, z in enumerate(m["zones"])]
        _upsert(db, MapZone, zones, ["map_id", "id"])
        seat_rows = [dict(map_id=m["id"], id=s["id"], section=s["section"], row_label=s["row"], num=s["num"],
                          group_id=s["groupId"], label=s["label"], x=s["x"], y=s["y"], sort_order=i) for i, s in enumerate(m["seats"])]
        for i in range(0, len(seat_rows), 1000):
            _upsert(db, MapSeat, seat_rows[i : i + 1000], ["map_id", "id"])
        # Bỏ khu/ghế/nhóm không còn trong sơ đồ
        db.execute(delete(MapZone).where(MapZone.map_id == m["id"], MapZone.id.not_in([z["id"] for z in m["zones"]] or [""])))
        db.execute(delete(MapSeat).where(MapSeat.map_id == m["id"], MapSeat.id.not_in([s["id"] for s in m["seats"]] or [""])))
        db.execute(delete(MapGroup).where(MapGroup.map_id == m["id"], MapGroup.id.not_in([g["id"] for g in m["groups"]])))
        seats += len(seat_rows)
    return seats


def _upsert_event(db: Session, e: dict) -> int:
    values = dict(
        slug=e["slug"], title=e["title"], search_text=e["searchText"], category_id=e["categoryId"], city=e["city"],
        venue=e["venue"], address=e["address"], layout=e["layout"], map_id=e["mapId"], host_name=e["hostName"],
        host_bio=e["hostBio"], description=e["description"], notes=e["notes"], status="approved",
        sale_start=datetime.fromisoformat(e["saleStart"]) if e["saleStart"] else None,
        active=True,
    )
    stmt = insert(Event).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["slug"],
        set_={c: stmt.excluded[c] for c in values if c != "slug"},
        where=Event.organizer_id.is_(None),  # không bao giờ ghi đè sự kiện của Ban tổ chức
    ).returning(Event.id)
    event_id = db.execute(stmt).scalar()
    if event_id is None:
        raise ValueError(f"Slug “{e['slug']}” đã thuộc về một sự kiện của Ban tổ chức")
    return event_id


def _prune(db: Session, model, event_id: int, keep_col, keep: list[str], referenced) -> None:
    """Xoá dòng không còn trong catalog. Dòng đã có đơn hàng tham chiếu thì giữ lại;
    nếu bảng có cột `active` thì đánh dấu ngừng bán (active = false)"""
    stale = db.execute(select(keep_col).where(model.event_id == event_id, keep_col.not_in(keep))).scalars().all()
    for key in stale:
        where = (model.event_id == event_id, keep_col == key)
        if not db.scalar(select(exists().where(referenced(key)))):
            db.execute(delete(model).where(*where))
        elif hasattr(model, "active"):
            db.execute(update(model).where(*where).values(active=False))


def _load_event(db: Session, e: dict, report: SeedReport) -> None:
    eid = _upsert_event(db, e)
    shows = [dict(event_id=eid, id=s["id"], starts_at=datetime.fromisoformat(s["startsAt"]),
                  end_time=time.fromisoformat(s["endTime"]), active=True) for s in e["shows"]]
    _upsert(db, Show, shows, ["event_id", "id"])
    tiers = [dict(event_id=eid, id=t["id"], name=t["name"], price=t["price"], capacity=t["capacity"],
                  max_per_order=t["maxPerOrder"], perks=t["perks"], group_id=t["groupId"], sort_order=t["sortOrder"],
                  active=True)
             for t in e["tiers"]]
    _upsert(db, TicketTier, tiers, ["event_id", "id"])

    show_ids = [s["id"] for s in e["shows"]]
    tier_ids = [t["id"] for t in e["tiers"]]
    _prune(db, TierStock, eid, TierStock.tier_id, tier_ids,
           lambda k: and_(OrderItem.event_id == eid, OrderItem.tier_id == k))
    _prune(db, TicketTier, eid, TicketTier.id, tier_ids,
           lambda k: and_(OrderItem.event_id == eid, OrderItem.tier_id == k))
    _prune(db, Show, eid, Show.id, show_ids, lambda k: and_(Order.event_id == eid, Order.show_id == k))

    # Kho vé: sự kiện theo loại vé / theo khu. Chỉ cập nhật capacity + presold, KHÔNG đụng sold
    if e["layout"] != "seats":
        presold = {(p["showId"], p["tierId"]): p["qty"] for p in e["presold"]}
        stock = [dict(event_id=eid, show_id=s, tier_id=t["id"], capacity=t["capacity"], presold=presold.get((s, t["id"]), 0))
                 for s in show_ids for t in e["tiers"]]
        _upsert(db, TierStock, stock, ["event_id", "show_id", "tier_id"], update=["capacity", "presold"])
    else:
        holds = [dict(event_id=eid, show_id=p["showId"], seat_id=p["seatId"]) for p in e["presoldSeats"]]
        for i in range(0, len(holds), 1000):
            _upsert(db, SeatHold, holds[i : i + 1000], ["event_id", "show_id", "seat_id"], update=[])
        keep = [(p["showId"], p["seatId"]) for p in e["presoldSeats"]] or [("", "")]
        db.execute(delete(SeatHold).where(SeatHold.event_id == eid, SeatHold.order_id.is_(None),
                                          tuple_(SeatHold.show_id, SeatHold.seat_id).not_in(keep)))

    report.events += 1
    report.shows += len(shows)
    report.tiers += len(tiers)


def _retire_events(db: Session, keep_slugs: list[str]) -> None:
    """Sự kiện của sàn không còn trong catalog: chưa có đơn → xoá; đã có đơn → ngừng bán"""
    stale = db.execute(select(Event.id).where(Event.organizer_id.is_(None), Event.slug.not_in(keep_slugs))).scalars().all()
    for eid in stale:
        if db.scalar(select(exists().where(Order.event_id == eid))):
            db.execute(update(Event).where(Event.id == eid).values(active=False))
        else:
            db.execute(delete(Event).where(Event.id == eid))


def load_catalog(db: Session, catalog: dict) -> SeedReport:
    report = SeedReport()
    _upsert(db, Category, [dict(id=c["id"], label=c["label"], dot=c["dot"], sort_order=c["sortOrder"]) for c in catalog["categories"]], ["id"])
    report.seats = _load_maps(db, catalog["maps"])
    for e in catalog["events"]:
        _load_event(db, e, report)
    _retire_events(db, [e["slug"] for e in catalog["events"]])

    # Vị trí trang chủ: thay toàn bộ (không bảng nào tham chiếu tới)
    ids = dict(db.execute(select(Event.slug, Event.id).where(Event.organizer_id.is_(None))).all())
    db.execute(delete(HomeSlot))
    slots = [dict(section=s["section"], position=s["position"], event_id=ids[s["slug"]], meta=s["meta"]) for s in catalog["homeSlots"]
             if s["section"] != "resale"]  # 0016: khối bán lại giả trên trang chủ đã bỏ
    if slots:
        db.execute(insert(HomeSlot).values(slots))
    report.slots = len(slots)

    _upsert(db, Coupon, [dict(code=c["code"], amount=c["amount"], min_order=c["minOrder"], active=True) for c in catalog["coupons"]], ["code"])
    _mark_seated_tiers(db)
    return report


def _mark_seated_tiers(db: Session) -> None:
    """0014: hạng vé của sự kiện bán theo ghế → ticket_tiers.seated = true. Bỏ qua khi lược đồ chưa có cột
    (test migration nạp catalog vào lược đồ cũ trước khi nâng cấp — migration 0014 tự cập nhật cột này)."""
    has_col = db.scalar(text("SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = current_schema() "
                             "AND table_name = 'ticket_tiers' AND column_name = 'seated')"))
    if has_col:
        db.execute(text("UPDATE ticket_tiers t SET seated = true FROM events e "
                        "WHERE e.id = t.event_id AND e.layout = 'seats' AND NOT t.seated"))


def reset_all(db: Session) -> None:
    """Xoá dữ liệu nghiệp vụ; GIỮ bảng tham chiếu địa giới (nạp ở migration 0010, seed không nạp lại)"""
    from app.models.locations import REFERENCE_TABLES

    names = ", ".join(t.name for t in Base.metadata.sorted_tables if t.name not in REFERENCE_TABLES)
    db.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


def ensure_admin(db: Session) -> None:
    """Giống seedAdmin của server Node: tạo một tài khoản quản trị nếu chưa có"""
    if db.scalar(select(exists().where(User.role == "admin"))):
        return
    email = settings.admin_email.lower()
    password = settings.admin_password or (DEV_ADMIN_PASSWORD if settings.env == "dev" else None)
    if not password:
        print("[admin] Chưa có tài khoản quản trị. Đặt ADMIN_EMAIL và ADMIN_PASSWORD rồi chạy lại.")
        return
    user = db.scalar(select(User).where(User.email == email))
    if user:
        user.role = "admin"
    else:
        db.add(User(name="Quản trị sàn", email=email, password_hash=hash_password(password), role="admin"))
    db.flush()
    note = "" if settings.admin_password else f" / {password}  (mật khẩu mặc định khi phát triển)"
    print(f"[admin] Đã tạo tài khoản quản trị: {email}{note}")




# ---------------------------------------------------------------------------
# --demo: đơn hàng mẫu cho buổi bảo vệ / dashboard (tạo qua chính create_order)
# ---------------------------------------------------------------------------
DEMO_DOMAIN = "@demo.ticketnhip.vn"
DEMO_PASSWORD = "demo123456"
DEMO_NAMES = ["Nguyễn Minh Anh", "Trần Quốc Bảo", "Lê Thu Hà", "Phạm Gia Huy", "Võ Ngọc Lan"]


def _demo_customers(db: Session) -> list[User]:
    users = []
    for i, name in enumerate(DEMO_NAMES, start=1):
        email = f"khach{i}{DEMO_DOMAIN}"
        u = db.scalar(select(User).where(User.email == email))
        if u is None:
            u = User(name=name, email=email, phone=f"09{i:08d}", password_hash=hash_password(DEMO_PASSWORD))
            db.add(u)
            db.flush()
        users.append(u)
    return users


def _clear_demo_orders(db: Session) -> None:
    """Xoá đơn của khách demo và TRẢ LẠI kho tương ứng (ghế giữ tự xoá theo đơn)"""
    demo_orders = select(Order.id).join(User, User.id == Order.user_id).where(User.email.like(f"%{DEMO_DOMAIN}"))
    from app.models.resale import ResaleListing  # 0016: tin bán lại demo đi theo đơn demo

    db.execute(delete(ResaleListing).where(ResaleListing.seller_id.in_(
        select(User.id).where(User.email.like(f"%{DEMO_DOMAIN}")))))
    returned = db.execute(
        select(Order.event_id, Order.show_id, OrderItem.tier_id, func.sum(OrderItem.qty))
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.id.in_(demo_orders), Order.status == "paid")  # đơn đã hoàn / huỷ đã tự trả kho
        .group_by(Order.event_id, Order.show_id, OrderItem.tier_id)
    ).all()
    for event_id, show_id, tier_id, qty in returned:
        db.execute(update(TierStock).where(TierStock.event_id == event_id, TierStock.show_id == show_id,
                                           TierStock.tier_id == tier_id).values(sold=TierStock.sold - qty))
    db.execute(delete(Order).where(Order.id.in_(demo_orders)))


def load_demo(db: Session, *, days: int = 7, orders_per_day: tuple[int, int] = (3, 8), rng_seed: int = 7) -> int:
    """Tạo đơn mẫu rải đều `days` ngày gần nhất (giờ VN, có hôm nay). Chạy lại: thay thế đơn demo cũ.
    Chỉ dùng sự kiện bán theo loại vé / khu, đang mở bán, suất chưa diễn. Trả về số đơn đã tạo."""
    from fastapi import HTTPException

    from app.services.booking import OrderIn, create_order
    from app.services.catalog import public_events_query
    from app.utils.timefmt import VN

    rng = random.Random(rng_seed)
    _clear_demo_orders(db)
    customers = _demo_customers(db)
    now = datetime.now(timezone.utc)
    events = [e for e in db.scalars(public_events_query().where(Event.layout != "seats").order_by(Event.id))
              if e.sale_start is None or e.sale_start <= now]
    choices = []
    for ev in events:
        shows = db.scalars(select(Show).where(Show.event_id == ev.id, Show.active, Show.starts_at > now)
                           .order_by(Show.starts_at, Show.id)).all()
        tiers = db.scalars(select(TicketTier).where(TicketTier.event_id == ev.id, TicketTier.active,
                                                    TicketTier.capacity > 0).order_by(TicketTier.sort_order)).all()
        if shows and tiers:
            choices.append((ev, shows, tiers))
    if not choices:
        return 0

    today = now.astimezone(VN).date()
    created = 0
    for back in range(days - 1, -1, -1):
        day = today - timedelta(days=back)
        for _ in range(rng.randint(*orders_per_day)):
            ev, shows, tiers = rng.choice(choices)
            show, tier = rng.choice(shows), rng.choice(tiers)
            qty = rng.randint(1, min(3, tier.max_per_order))
            buyer = rng.choice(customers)
            coupon = "NHIP50" if tier.price * qty >= 500000 and rng.random() < 0.25 else ""
            body = OrderIn(slug=ev.slug, showId=show.id, items=[{"tierId": tier.id, "qty": qty}], coupon=coupon,
                           method=rng.choice(["qr", "wallet", "card"]),
                           buyer={"name": buyer.name, "email": buyer.email, "phone": buyer.phone})
            nested = db.begin_nested()
            try:
                order = create_order(db, buyer, body)
            except HTTPException:  # hết vé… → bỏ qua đơn này
                nested.rollback()
                continue
            nested.commit()
            when = datetime.combine(day, datetime.min.time(), tzinfo=VN) + timedelta(
                hours=rng.randint(8, 22), minutes=rng.randint(0, 59))
            order.created_at = min(when, now)
            created += 1
    db.flush()
    _demo_resale(db, rng)
    return created


def _demo_resale(db: Session, rng: random.Random, limit: int = 8) -> int:
    """0016: vài tin bán lại THẬT từ đơn demo (qua chính resale.create_listing, giá 85–100% giá gốc).
    Chỉ đăng bán, không tạo đơn mua lại — để số đơn / số vé demo vẫn khớp tồn kho."""
    from fastapi import HTTPException

    from app.services import resale

    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(Order, User).join(User, User.id == Order.user_id)
        .join(Show, (Show.event_id == Order.event_id) & (Show.id == Order.show_id))
        .where(User.email.like(f"%{DEMO_DOMAIN}"), Order.status == "paid", Order.kind == "primary",
               Show.starts_at > now)
        .order_by(Order.id)).all()
    made = 0
    for order, user in rng.sample(rows, min(len(rows), limit * 2)):
        if made >= limit:
            break
        tickets = db.scalars(select(Ticket).where(Ticket.order_id == order.id).order_by(Ticket.code)).all()
        if not tickets:
            continue
        price = max(10_000, min(t.price for t in tickets) * rng.choice((85, 90, 95, 100)) // 100 // 1000 * 1000)
        nested = db.begin_nested()
        try:
            resale.create_listing(db, user, [t.code for t in tickets], price, rng.random() < 0.7)
        except HTTPException:
            nested.rollback()
            continue
        nested.commit()
        made += 1
    return made


def main() -> None:
    parser = argparse.ArgumentParser(description="Nạp danh mục sự kiện vào PostgreSQL")
    parser.add_argument("--reset", action="store_true", help="xoá sạch mọi dữ liệu trước khi nạp")
    parser.add_argument("--demo", action="store_true", help="tạo đơn hàng mẫu rải 7 ngày gần nhất (thay đơn demo cũ)")
    args = parser.parse_args()

    engine = make_engine(settings.database_url)
    engine.echo = False  # hàng nghìn câu INSERT, không in ra
    catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
    with Session(engine) as db:
        if args.reset:
            reset_all(db)
            print("Đã xoá sạch dữ liệu.")
        report = load_catalog(db, catalog)
        ensure_admin(db)
        demo = load_demo(db) if args.demo else None
        db.commit()
    print(f"Đã nạp: {report}")
    if demo is not None:
        print(f"Đơn demo: {demo} đơn trong 7 ngày (khách khach1..5{DEMO_DOMAIN} / {DEMO_PASSWORD})")


if __name__ == "__main__":
    main()
