"""Task D2 — PATCH /api/organizer/events/{id} + form/editable trong chi tiết sự kiện của Ban tổ chức"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.models.catalog import Event, Show, TicketTier
from app.models.sales import TierStock
from app.utils.timefmt import VN
from tests.api_helpers import drop_org_event, make_org_event
from tests.booking_helpers import insert_order, make_customer

EVENTS = "/api/organizer/events"
DAY = (datetime.now(VN) + timedelta(days=30)).date()
FUTURE = DAY.isoformat()
OK = {
    "title": "Đêm Nhạc Sửa Thử", "category": "nhac-song", "city": "Hà Nội", "venue": "Nhà hát Lớn", "address": "1 Tràng Tiền",
    "date": FUTURE, "startTime": "19:30", "endTime": "22:00",
    "description": "Đêm nhạc mở màn mùa đông với nhiều nghệ sĩ.\n\nCửa mở lúc 18:30.",
    "tiers": [{"name": "Vé thường", "price": 200000, "quantity": 100, "perks": "Ghế ngồi"},
              {"name": "VIP", "price": 500000, "quantity": 20, "perks": ""}],
}
LOCKED = [("title", "Tên khác hẳn", "tên sự kiện"), ("category", "san-khau", "danh mục"), ("city", "Đà Nẵng", "thành phố"),
          ("venue", "Nhà văn hoá", "địa điểm"), ("date", (DAY + timedelta(days=1)).isoformat(), "ngày diễn"),
          ("startTime", "20:00", "giờ bắt đầu"), ("endTime", "23:00", "giờ kết thúc")]


@pytest.fixture(autouse=True)
def drop_created(api_db):
    yield
    api_db.rollback()
    for ev in api_db.scalars(select(Event).where(Event.slug.like("dem-nhac-sua-thu%"))):
        from tests.api_helpers import drop_event

        drop_event(api_db, ev)


def create(c, **over) -> dict:
    r = c.post(EVENTS, json=OK | over)
    assert r.status_code == 201, r.text
    return r.json()["event"]


def approve(api_db, eid, opened=True):
    """Duyệt; opened=False → đặt giờ mở bán ở tương lai (upcoming-sale)"""
    values = {"status": "approved", "reviewed_at": datetime.now(timezone.utc) - timedelta(days=1)}
    if not opened:
        values["sale_start"] = datetime.now(timezone.utc) + timedelta(days=2)
    api_db.execute(update(Event).where(Event.id == eid).values(**values))
    api_db.commit()


def detail(c, eid) -> dict:
    r = c.get(f"{EVENTS}/{eid}")
    assert r.status_code == 200, r.text
    return r.json()


def form_body(c, eid, **over) -> dict:
    """Body PATCH = form hiện tại (có id hạng cũ) + thay đổi"""
    f = detail(c, eid)["form"]
    body = {k: f[k] for k in ("title", "category", "city", "venue", "address", "date", "startTime", "endTime",
                              "description", "saleStart", "layout")}
    body["tiers"] = [{k: t[k] for k in ("id", "name", "price", "quantity", "perks")} for t in f["tiers"]]
    return body | over


def patch(c, eid, body):
    return c.patch(f"{EVENTS}/{eid}", json=body)


# ------------------------------------------------------------------ form + mode
def test_detail_has_form_and_mode(c, logged_organizer, api_db):
    s = create(c, saleStart=f"{(DAY - timedelta(days=3)).isoformat()}T09:00")
    d = detail(c, s["id"])
    assert d["editable"] == {"mode": "full", "saleStart": True}
    f = d["form"]
    assert {k: f[k] for k in ("title", "category", "city", "venue", "address", "date", "startTime", "endTime")} == \
        {k: OK[k] for k in ("title", "category", "city", "venue", "address", "date", "startTime", "endTime")}
    assert f["description"] == OK["description"] and f["saleStart"] == f"{(DAY - timedelta(days=3)).isoformat()}T09:00"
    assert (f["layout"], f["mapId"], f["prices"]) == ("list", None, None)
    assert f["tiers"] == [{"id": "ve-1", "name": "Vé thường", "price": 200000, "quantity": 100, "perks": "Ghế ngồi", "sold": 0},
                          {"id": "ve-2", "name": "VIP", "price": 500000, "quantity": 20, "perks": "", "sold": 0}]
    approve(api_db, s["id"], opened=False)
    assert detail(c, s["id"])["editable"] == {"mode": "limited", "saleStart": True}
    approve(api_db, s["id"], opened=True)
    api_db.execute(update(Event).where(Event.id == s["id"]).values(sale_start=None))
    api_db.commit()
    assert detail(c, s["id"])["editable"] == {"mode": "limited", "saleStart": False}
    api_db.execute(update(Show).where(Show.event_id == s["id"]).values(starts_at=datetime.now(timezone.utc) - timedelta(days=3)))
    api_db.commit()
    assert detail(c, s["id"])["editable"] == {"mode": "none", "saleStart": False}


# ------------------------------------------------------------------ full
def test_full_edit_pending_changes_everything(c, logged_organizer, api_db):
    s = create(c)
    new_day = (DAY + timedelta(days=5)).isoformat()
    body = form_body(c, s["id"], title="Đêm Nhạc Sửa Thử Bản Mới", city="Huế", venue="Cung văn hoá", date=new_day,
                     startTime="20:00", endTime="23:30", tiers=[{"name": "Một giá", "price": 300000, "quantity": 80, "perks": ""}])
    r = patch(c, s["id"], body)
    assert r.status_code == 200, r.text
    out = r.json()["event"]
    assert out["title"] == "Đêm Nhạc Sửa Thử Bản Mới" and out["city"] == "Huế" and out["date"] == new_day
    assert out["startTime"] == "20:00" and out["capacity"] == 80 and out["minPrice"] == 300000
    assert out["slug"] == s["slug"] and out["status"] == "pending"
    api_db.expire_all()
    shows = api_db.scalars(select(Show).where(Show.event_id == s["id"])).all()
    assert [sh.id for sh in shows] == [new_day.replace("-", "") + "-2000"]
    tiers = api_db.scalars(select(TicketTier).where(TicketTier.event_id == s["id"])).all()
    assert [(t.id, t.name, t.capacity) for t in tiers] == [("ve-1", "Một giá", 80)]
    stock = api_db.scalars(select(TierStock).where(TierStock.event_id == s["id"])).all()
    assert [(st.show_id, st.tier_id, st.capacity) for st in stock] == [(shows[0].id, "ve-1", 80)]
    assert "hue" in api_db.get(Event, s["id"]).search_text


def test_full_edit_rejected_back_to_pending(c, logged_organizer, api_db):
    s = create(c)
    api_db.execute(update(Event).where(Event.id == s["id"]).values(status="rejected", reject_reason="Thiếu ảnh",
                                                                  reviewed_at=datetime.now(timezone.utc)))
    api_db.commit()
    assert detail(c, s["id"])["editable"]["mode"] == "full"
    out = patch(c, s["id"], form_body(c, s["id"], description="Giới thiệu đã bổ sung đầy đủ theo yêu cầu của sàn.")).json()["event"]
    assert out["status"] == "pending" and out["rejectReason"] is None and out["reviewedAt"] is None


def test_layout_not_list_400(c, logged_organizer):
    s = create(c)
    r = patch(c, s["id"], form_body(c, s["id"], layout="zones"))
    assert r.status_code == 400 and r.json() == {"error": "Sơ đồ không hợp lệ"}  # F4: đổi sang sơ đồ cần mapId


def test_full_edit_validates_like_create(c, logged_organizer):
    s = create(c)
    r = patch(c, s["id"], form_body(c, s["id"], title="ab"))
    assert r.status_code == 400 and r.json() == {"error": "Tên sự kiện cần từ 3 đến 120 ký tự"}


# ------------------------------------------------------------------ limited
def test_limited_edit_description_address_ok(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])
    r = patch(c, s["id"], form_body(c, s["id"], address="99 Phố Huế, Hà Nội",
                                    description="Giới thiệu mới, dài hơn hai mươi ký tự.\n\nĐoạn hai."))
    assert r.status_code == 200, r.text
    api_db.expire_all()
    ev = api_db.get(Event, s["id"])
    assert ev.status == "approved" and ev.address == "99 Phố Huế, Hà Nội"
    assert ev.description == ["Giới thiệu mới, dài hơn hai mươi ký tự.", "Đoạn hai."]


@pytest.mark.parametrize("field,value,label", LOCKED, ids=[f for f, _, _ in LOCKED])
def test_limited_locked_field_409(c, logged_organizer, api_db, field, value, label):
    s = create(c)
    approve(api_db, s["id"])
    r = patch(c, s["id"], form_body(c, s["id"], **{field: value}))
    assert r.status_code == 409 and r.json() == {"error": f"Sự kiện đã duyệt không thể đổi {label}"}


def _sell(api_db, s, qty, presold=0):
    show_id = FUTURE.replace("-", "") + "-1930"
    api_db.execute(update(TierStock).where(TierStock.event_id == s["id"], TierStock.tier_id == "ve-1").values(presold=presold))
    api_db.commit()
    buyer = make_customer(api_db, f"mua-sua-{qty}-{presold}@x.vn")
    return insert_order(api_db, buyer, s["slug"], show_id, [("ve-1", qty)])


def _tier(body, tid):
    return next(t for t in body["tiers"] if t["id"] == tid)


def test_limited_capacity_below_sold_400_stock_unchanged(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])
    _sell(api_db, s, 3, presold=5)  # đã bán = 5 bán sẵn + 3 vé của đơn
    assert _tier(detail(c, s["id"])["form"], "ve-1")["sold"] == 8
    body = form_body(c, s["id"])
    _tier(body, "ve-1")["quantity"] = 7
    r = patch(c, s["id"], body)
    assert r.status_code == 400 and r.json() == {"error": "Loại vé “Vé thường”: không thể ít hơn 8 vé đã bán"}
    api_db.expire_all()
    assert api_db.scalar(select(TierStock.capacity).where(TierStock.event_id == s["id"], TierStock.tier_id == "ve-1")) == 100
    _tier(body, "ve-1")["quantity"] = 8  # đúng bằng số đã bán → được
    assert patch(c, s["id"], body).status_code == 200
    api_db.expire_all()
    assert api_db.scalar(select(TierStock.capacity).where(TierStock.event_id == s["id"], TierStock.tier_id == "ve-1")) == 8
    assert api_db.get(TicketTier, (s["id"], "ve-1")).capacity == 8


def test_limited_price_change_sold_409(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])
    _sell(api_db, s, 1)
    body = form_body(c, s["id"])
    _tier(body, "ve-1")["price"] = 250000
    r = patch(c, s["id"], body)
    assert r.status_code == 409 and r.json() == {"error": "Loại vé “Vé thường” đã có người mua, không đổi được giá"}
    body = form_body(c, s["id"])
    _tier(body, "ve-2")["price"] = 600000  # VIP chưa ai mua → đổi được
    _tier(body, "ve-1")["name"] = "Vé phổ thông"  # đổi tên / quyền lợi luôn được
    assert patch(c, s["id"], body).status_code == 200
    api_db.expire_all()
    assert api_db.get(TicketTier, (s["id"], "ve-2")).price == 600000
    assert api_db.get(TicketTier, (s["id"], "ve-1")).name == "Vé phổ thông"


def test_limited_add_tier_creates_stock(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])
    body = form_body(c, s["id"])
    body["tiers"].append({"name": "Hạng mới", "price": 150000, "quantity": 30, "perks": "Đứng"})
    out = patch(c, s["id"], body).json()["event"]
    assert out["capacity"] == 150
    api_db.expire_all()
    t = api_db.get(TicketTier, (s["id"], "ve-3"))
    assert (t.name, t.capacity, t.sort_order, t.max_per_order) == ("Hạng mới", 30, 3, 10)
    st = api_db.scalar(select(TierStock).where(TierStock.event_id == s["id"], TierStock.tier_id == "ve-3"))
    assert (st.capacity, st.presold, st.sold) == (30, 0, 0)


def test_limited_remove_unsold_tier_ok_sold_tier_409(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])
    _sell(api_db, s, 2)
    body = form_body(c, s["id"])
    body["tiers"] = [t for t in body["tiers"] if t["id"] != "ve-1"]
    r = patch(c, s["id"], body)
    assert r.status_code == 409 and r.json() == {"error": "Loại vé “Vé thường” đã có người mua, không bỏ được"}
    body = form_body(c, s["id"])
    body["tiers"] = [t for t in body["tiers"] if t["id"] != "ve-2"]
    assert patch(c, s["id"], body).status_code == 200
    api_db.expire_all()
    assert api_db.get(TicketTier, (s["id"], "ve-2")) is None
    assert api_db.scalar(select(TierStock).where(TierStock.event_id == s["id"], TierStock.tier_id == "ve-2")) is None


def test_limited_unknown_tier_id_400(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])
    body = form_body(c, s["id"])
    body["tiers"][0]["id"] = "ve-99"
    r = patch(c, s["id"], body)
    assert r.status_code == 400 and r.json() == {"error": "Loại vé không hợp lệ"}


def test_sale_start_after_open_409(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])  # mở bán ngay khi duyệt
    later = f"{(DAY - timedelta(days=1)).isoformat()}T10:00"
    r = patch(c, s["id"], form_body(c, s["id"], saleStart=later))
    assert r.status_code == 409 and r.json() == {"error": "Đã mở bán, không đổi được giờ mở bán"}
    s2 = create(c, title="Đêm Nhạc Sửa Thử Hai")
    approve(api_db, s2["id"], opened=False)
    past = (datetime.now(VN) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    r = patch(c, s2["id"], form_body(c, s2["id"], saleStart=past))
    assert r.status_code == 400 and r.json() == {"error": "Giờ mở bán phải sau thời điểm hiện tại"}
    assert patch(c, s2["id"], form_body(c, s2["id"], saleStart=later)).status_code == 200
    api_db.expire_all()
    assert api_db.get(Event, s2["id"]).sale_start == datetime.fromisoformat(later).replace(tzinfo=VN)


@pytest.mark.parametrize("state", ["ended", "closed", "cancelled"])
def test_ended_or_cancelled_409(c, logged_organizer, api_db, state):
    s = create(c)
    approve(api_db, s["id"])
    if state == "cancelled":
        api_db.execute(update(Event).where(Event.id == s["id"]).values(
            status="cancelled", cancel_reason="Huỷ thử", cancelled_at=datetime.now(timezone.utc), cancelled_by="organizer"))
    else:
        ago = timedelta(days=3) if state == "ended" else timedelta(minutes=5)
        api_db.execute(update(Show).where(Show.event_id == s["id"]).values(starts_at=datetime.now(timezone.utc) - ago))
    api_db.commit()
    body = form_body(c, s["id"])
    r = patch(c, s["id"], body)
    assert r.status_code == 409 and r.json() == {"error": "Sự kiện này không còn sửa được"}


def test_edit_visible_to_customer(c, logged_organizer, api_db):
    s = create(c)
    approve(api_db, s["id"])
    _sell(api_db, s, 2)
    body = form_body(c, s["id"])
    _tier(body, "ve-1")["quantity"] = 150
    _tier(body, "ve-2")["price"] = 650000
    assert patch(c, s["id"], body).status_code == 200
    pub = c.get(f"/api/events/{s['slug']}").json()
    tiers = {t["id"]: t for t in pub["tiers"]}
    assert tiers["ve-1"]["capacity"] == 150 and tiers["ve-2"]["price"] == 650000
    avail = {t["id"]: t["remaining"] for t in c.get(f"/api/events/{s['slug']}/availability").json()["tiers"]}
    assert avail["ve-1"] == 148


def test_other_org_404(c, logged_organizer, api_db):
    other = make_org_event(api_db, slug="sua-btc-khac")
    try:
        r = c.patch(f"{EVENTS}/{other.id}", json=OK)
        assert r.status_code == 404 and r.json() == {"error": "Sự kiện không tồn tại"}
        assert c.patch(f"{EVENTS}/abc", json=OK).status_code == 404
    finally:
        drop_org_event(api_db, other)
