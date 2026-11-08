"""Controller — xử lý request/response cho routers/admin.py: API Quản trị sàn (giai đoạn 2): sổ đơn toàn sàn, Ban tổ chức, báo cáo, tra mã vé, xem trước / gỡ sự kiện, rút tiền."""
from sqlalchemy.orm import Session
from app.models.users import User
from app.middlewares.errors import not_found
from app.services import checkin, manage, org_events, org_orders, org_reports, withdrawals
from app.controllers.organizer_controller import parse_event_id
from app.schemas.organizer import CancelIn, DecideWithdrawalIn
from app.services.org_orders import ID_RE


def admin_orders(q: str, eventId: str, organizerId: str, status: str, day_from: str, to: str, page: str, pageSize: str, _admin: User, db: Session) -> dict:
    # GET /admin/orders
    params = org_orders.parse_list_params(q=q, event_id=eventId, status=status, day_from=day_from, day_to=to,
                                          page=page, page_size=pageSize)
    return org_orders.list_orders(db, None, **params, filter_organizer=org_orders.parse_organizer_id(organizerId))


def admin_organizers(_admin: User, db: Session) -> dict:
    # GET /admin/organizers
    return {"organizers": manage.admin_organizers(db)}


def admin_organizer_events(organizer_id: str, _admin: User, db: Session) -> dict:
    # GET /admin/organizers/{organizer_id}/events
    if not ID_RE.match(organizer_id) or int(organizer_id) > 2_147_483_647:
        raise not_found(manage.ORGANIZER_NOT_FOUND)
    return {"events": manage.admin_organizer_events(db, int(organizer_id))}


def admin_reports(day_from: str, to: str, eventId: str, organizerId: str, groupBy: str, _admin: User, db: Session) -> dict:
    # GET /admin/reports
    params = org_reports.parse_report_params(day_from=day_from, day_to=to, event_id=eventId, group_by=groupBy)
    return org_reports.report(db, None, **params, filter_organizer=org_orders.parse_organizer_id(organizerId))


def admin_ticket(code: str, _admin: User, db: Session) -> dict:
    # GET /admin/tickets/{code}
    return checkin.lookup(db, code)


def admin_cancel_event(event_id: str, body: CancelIn | None, _admin: User, db: Session) -> dict:
    # POST /admin/events/{event_id}/cancel — dùng chung org_events.cancel_event với BTC (organizer_id=None = mọi BTC)
    eid = parse_event_id(event_id, manage.EVENT_NOT_FOUND)
    try:
        result = org_events.cancel_event(db, None, eid, (body or CancelIn()).reason, by="admin")
        db.commit()  # một transaction: đổi trạng thái sự kiện + hoàn đơn
    except Exception:
        db.rollback()
        raise
    return result


def admin_withdrawals(status: str, _admin: User, db: Session) -> dict:
    # GET /admin/withdrawals
    return {"withdrawals": withdrawals.admin_list(db, status)}


def admin_decide_withdrawal(withdrawal_id: str, body: DecideWithdrawalIn, admin: User, db: Session) -> dict:
    # POST /admin/withdrawals/{withdrawal_id}/decide — UPDATE có điều kiện trong MỘT transaction
    wid = withdrawals.parse_id(withdrawal_id)
    try:
        result = withdrawals.decide(db, admin, wid, body.decision, body.note)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def admin_stale_events(days: str, _admin: User, db: Session) -> dict:
    # GET /admin/events/stale
    return manage.stale_events(db, days)


def admin_event_preview(event_id: str, _admin: User, db: Session) -> dict:
    # GET /admin/events/{event_id}
    return manage.admin_event_preview(db, parse_event_id(event_id, manage.EVENT_NOT_FOUND))
