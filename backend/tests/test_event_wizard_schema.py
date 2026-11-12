"""Migration 0009 (wizard tạo sự kiện): cột mới của events / organizers và 2 ràng buộc CHECK"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.catalog import Event
from app.models.users import Organizer, User
from tests.conftest import event_kwargs


def test_new_event_columns_have_defaults(db, make_category):
    ev = Event(**event_kwargs(make_category.id))
    db.add(ev)
    db.flush()
    db.refresh(ev)
    assert ev.is_online is False
    assert ev.poster_url is None and ev.banner_url is None
    assert ev.terms_and_conditions is None and ev.ticket_sale_end_at is None


def test_sale_window_check(db, make_category):
    start = datetime.now(timezone.utc) + timedelta(days=1)
    db.add(Event(**event_kwargs(make_category.id, sale_start=start, ticket_sale_end_at=start)))
    with pytest.raises(IntegrityError, match="ck_events_sale_window"):
        db.flush()


def test_bank_account_check(db):
    u = User(name="BTC", email="ngan-hang@btc.vn", password_hash="h", role="organizer")
    db.add(u)
    db.flush()
    db.add(Organizer(user_id=u.id, org_name="BTC", phone="0912345678", bank_name="VCB",
                     bank_account_number="12ab", bank_account_holder="A", bank_branch=None))
    with pytest.raises(IntegrityError, match="ck_organizers_bank_account"):
        db.flush()
