"""Controller — xử lý request/response cho routers/manage.py: API Ban tổ chức & Quản trị sàn — giống server/manage.js của bản Node"""
import re
from sqlalchemy.orm import Session
from app.middlewares.auth import public_user
from app.models.users import User
from app.middlewares.errors import not_found
from app.services import manage
from app.schemas.manage import OrganizerIn, ReviewIn


def organizer_register(body: OrganizerIn, user: User, db: Session) -> dict:
    # POST /organizer/register
    manage.register_organizer(db, user, body.orgName, body.phone, body.description)
    db.commit()
    return {"user": public_user(user)}


def organizer_me(user: User, db: Session) -> dict:
    # GET /organizer/me
    return manage.organizer_dashboard(db, user)


def organizer_create_event(body: manage.OrgEventIn, user: User, db: Session) -> dict:
    # POST /organizer/events
    try:
        ev = manage.create_org_event(db, user, body)
        result = {"event": manage.event_summaries(db, [ev])[0]}
        db.commit()
    except Exception:
        db.rollback()
        raise
    return result


def admin_overview(_admin: User, db: Session) -> dict:
    # GET /admin/overview
    return manage.overview(db)


def admin_review(event_id: str, body: ReviewIn, _admin: User, db: Session) -> dict:
    # POST /admin/events/{event_id}/review
    if not re.fullmatch(r"[0-9]{1,10}", event_id) or int(event_id) > 2_147_483_647:
        raise not_found(manage.REVIEW_NOT_FOUND)
    result = manage.review(db, int(event_id), body.decision, body.reason)
    db.commit()
    return result


def organizer_stats(days: int, user: User, db: Session) -> dict:
    # GET /organizer/stats
    return {"days": manage.organizer_stats(db, user.id, days)}


def organizer_event(event_id: str, user: User, db: Session) -> dict:
    # GET /organizer/events/{event_id}
    if not re.fullmatch(r"[0-9]{1,10}", event_id) or int(event_id) > 2_147_483_647:
        raise not_found(manage.EVENT_NOT_FOUND)
    return manage.organizer_event_detail(db, user.id, int(event_id))
