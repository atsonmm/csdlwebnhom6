"""Controller — xử lý request/response cho routers/organizer.py: API vận hành của Ban tổ chức (giai đoạn 2): sổ đơn, báo cáo, soát vé, sửa/huỷ sự kiện, rút tiền"""
import re
from sqlalchemy.orm import Session
from app.middlewares.errors import not_found
from app.models.users import User
from app.services import checkin, manage, org_events, org_maps, org_orders, org_reports, withdrawals
from app.schemas.organizer import CheckinIn, CancelIn, WithdrawalIn


def parse_event_id(raw: str, message: str) -> int:
    """Mã trên URL: chỉ chữ số ASCII, 1–10 ký tự, trong giới hạn integer của PostgreSQL; sai → 404"""
    if not re.fullmatch(r"[0-9]{1,10}", raw) or int(raw) > 2_147_483_647:
        raise not_found(message)
    return int(raw)


def organizer_orders(q: str, eventId: str, status: str, day_from: str, to: str, page: str, pageSize: str, user: User, db: Session) -> dict:
    # GET /organizer/orders
    params = org_orders.parse_list_params(q=q, event_id=eventId, status=status, day_from=day_from, day_to=to,
                                          page=page, page_size=pageSize)
    return org_orders.list_orders(db, user.id, **params)


def organizer_reports(day_from: str, to: str, eventId: str, groupBy: str, user: User, db: Session) -> dict:
    # GET /organizer/reports
    params = org_reports.parse_report_params(day_from=day_from, day_to=to, event_id=eventId, group_by=groupBy)
    return org_reports.report(db, user.id, **params)


def organizer_checkin(body: CheckinIn, user: User, db: Session) -> dict:
    # POST /organizer/checkin
    try:
        result = checkin.check_in(db, user.id, body.code)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def organizer_cancel_event(event_id: str, body: CancelIn | None, user: User, db: Session) -> dict:
    # DELETE /organizer/events/{event_id}
    eid = parse_event_id(event_id, manage.EVENT_NOT_FOUND)
    try:
        result = org_events.cancel_event(db, user.id, eid, (body or CancelIn()).reason)
        db.commit()  # một transaction: đổi trạng thái sự kiện + hoàn đơn
    except Exception:
        db.rollback()
        raise
    return result


def organizer_update_event(event_id: str, body: manage.OrgEventIn, user: User, db: Session) -> dict:
    # PATCH /organizer/events/{event_id}
    eid = parse_event_id(event_id, manage.EVENT_NOT_FOUND)
    try:
        ev = org_events.update_event(db, user.id, eid, body)
        result = {"event": manage.event_summaries(db, [ev])[0]}
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def organizer_withdrawals(user: User, db: Session) -> dict:
    # GET /organizer/withdrawals
    return {"balance": withdrawals.balance(db, user.id),
            "withdrawals": [withdrawals.to_json(w) for w in withdrawals.list_for(db, user.id)]}


def organizer_request_withdrawal(body: WithdrawalIn, user: User, db: Session) -> dict:
    # POST /organizer/withdrawals — khoá organizers + INSERT withdrawals trong MỘT transaction
    try:
        w = withdrawals.request(db, user.id, body)
        result = {"withdrawal": withdrawals.to_json(w), "balance": withdrawals.balance(db, user.id)}
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def organizer_top_customers(day_from: str, to: str, user: User, db: Session) -> dict:
    # GET /organizer/top-customers — khoảng ngày như /organizer/reports (mặc định 30 ngày đến hôm nay)
    params = org_reports.parse_report_params(day_from=day_from, day_to=to, event_id="", group_by="day")
    rows = org_reports.top_customers(db, user.id, day_from=params["day_from"], day_to=params["day_to"])
    return {"range": {"from": params["day_from"].isoformat(), "to": params["day_to"].isoformat()},
            "customers": [{k: v for k, v in r.items() if k != "organizerId"} for r in rows]}


def organizer_venue_maps(user: User, db: Session) -> dict:
    # GET /organizer/venue-maps
    return {"maps": org_maps.list_maps(db)}
