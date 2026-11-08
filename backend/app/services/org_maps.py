"""Ban tổ chức bán theo sơ đồ có sẵn của sàn (Task F1): liệt kê sơ đồ + sinh hạng vé theo đúng quy ước catalog.

Quy ước (giống seed/catalog.json):
- zones: mỗi KHU một hạng vé (id = mã khu, group_id = nhóm của khu, sức chứa = sức chứa khu) + dòng kho tier_stock;
- seats: mỗi NHÓM ghế một hạng vé (id = group_id = mã nhóm, sức chứa = số ghế của nhóm), KHÔNG có tier_stock
  (đã bán = seat_holds — xem stock.tier_stats).
Giá đặt theo nhóm: prices = {mã nhóm: giá}; mọi nhóm có khu / ghế đều phải có giá.
"""
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config.rules import TIER_MAX_PER_ORDER
from app.models.catalog import MapGroup, MapSeat, MapZone, VenueMap

MAP_MSG = "Sơ đồ không hợp lệ"
PRICE_MIN, PRICE_MAX = 10_000, 100_000_000


def _group_capacity(db: Session, map_ids: list[str]) -> dict[tuple[str, str], int]:
    zones = db.execute(select(MapZone.map_id, MapZone.group_id, func.sum(MapZone.capacity))
                       .where(MapZone.map_id.in_(map_ids)).group_by(MapZone.map_id, MapZone.group_id)).all()
    seats = db.execute(select(MapSeat.map_id, MapSeat.group_id, func.count())
                       .where(MapSeat.map_id.in_(map_ids)).group_by(MapSeat.map_id, MapSeat.group_id)).all()
    return {(m, g): int(n) for m, g, n in [*zones, *seats]}


def list_maps(db: Session) -> list[dict]:
    """Mọi sơ đồ kèm nhóm (sắp theo sort_order) và sức chứa từng nhóm — 3 truy vấn cho toàn bộ"""
    maps = db.scalars(select(VenueMap).order_by(VenueMap.kind, VenueMap.id)).all()
    ids = [m.id for m in maps]
    cap = _group_capacity(db, ids)
    groups: dict[str, list[MapGroup]] = {}
    for g in db.scalars(select(MapGroup).where(MapGroup.map_id.in_(ids)).order_by(MapGroup.sort_order, MapGroup.id)):
        groups.setdefault(g.map_id, []).append(g)
    out = []
    for m in maps:
        gs = [{"id": g.id, "label": g.label, "color": g.color, "capacity": cap.get((m.id, g.id), 0),
               "maxPerOrder": g.max_per_order or TIER_MAX_PER_ORDER, "perks": g.perks}
              for g in groups.get(m.id, []) if cap.get((m.id, g.id), 0) > 0]
        out.append({"id": m.id, "kind": m.kind, "name": m.name, "capacity": sum(g["capacity"] for g in gs), "groups": gs})
    return out


def _price(raw: Any) -> int | None:
    from app.services.manage import _int  # import muộn: manage dùng module này

    p = _int(raw)
    return p if p is not None and PRICE_MIN <= p <= PRICE_MAX else None


def tiers_for_map(db: Session, layout: str, map_id: Any, prices: Any) -> list[dict]:
    """Kiểm tra sơ đồ + giá → danh sách hạng vé (dạng dict như _validated_tiers, thêm group_id / max_per_order)"""
    m = db.get(VenueMap, map_id) if isinstance(map_id, str) and map_id else None
    if m is None or m.kind != layout:
        raise HTTPException(400, MAP_MSG)
    prices = prices if isinstance(prices, dict) else {}
    cap = _group_capacity(db, [m.id])
    groups = [g for g in db.scalars(select(MapGroup).where(MapGroup.map_id == m.id)
                                    .order_by(MapGroup.sort_order, MapGroup.id)) if cap.get((m.id, g.id), 0) > 0]
    price_of: dict[str, int] = {}
    for g in groups:
        p = _price(prices.get(g.id))
        if p is None:
            raise HTTPException(400, f"Nhóm “{g.label}”: giá từ 10.000 ₫ đến 100.000.000 ₫")
        price_of[g.id] = p
    by_id = {g.id: g for g in groups}

    def row(tid: str, name: str, group: MapGroup, capacity: int, sort_order: int) -> dict:
        return {"id": tid, "name": name, "price": price_of[group.id], "capacity": capacity, "perks": group.perks,
                "sort_order": sort_order, "group_id": group.id,
                "max_per_order": group.max_per_order or TIER_MAX_PER_ORDER, "given_id": None}

    if layout == "seats":
        return [row(g.id, g.label, g, cap[(m.id, g.id)], i) for i, g in enumerate(groups, start=1)]
    zones = db.scalars(select(MapZone).where(MapZone.map_id == m.id).order_by(MapZone.sort_order, MapZone.id)).all()
    return [row(z.id, z.label, by_id[z.group_id], z.capacity, i) for i, z in enumerate(zones, start=1)
            if z.group_id in by_id]
