from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.catalog import Event
from app.models.users import Organizer, User, UserSession
from tests.conftest import event_kwargs


def now_plus(**kw) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**kw)


def test_user_needs_email_or_phone(db):
    db.add(User(name="A", password_hash="h"))
    with pytest.raises(IntegrityError, match="ck_users_contact"):
        db.flush()


def test_role_is_restricted(db):
    db.add(User(name="A", email="a@x.vn", password_hash="h", role="root"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_deleting_user_cascades_sessions_and_organizer(db):
    u = User(name="A", email="a@x.vn", password_hash="h")
    db.add(u)
    db.flush()
    db.add_all([UserSession(token_hash="t", user_id=u.id, expires_at=now_plus(days=1)),
                Organizer(user_id=u.id, org_name="Org", phone="0912345678")])
    db.flush()
    db.delete(u)
    db.flush()
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0
    assert db.scalar(select(func.count()).select_from(Organizer)) == 0


def test_event_organizer_must_exist(db, make_category):
    db.add(Event(**event_kwargs(make_category.id, organizer_id=999999)))
    with pytest.raises(IntegrityError):
        db.flush()
